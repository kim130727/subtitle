import argparse
import re
import time
from html import unescape
from json import loads
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import YouTubeTranscriptApiException


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] or "subtitle"


def video_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.strip("/")
    qs = parse_qs(parsed.query)
    return qs.get("v", ["unknown"])[0]


def get_title_via_oembed(vid: str) -> str | None:
    watch_url = f"https://www.youtube.com/watch?v={vid}"
    api = f"https://www.youtube.com/oembed?url={quote(watch_url, safe=':/?=&')}&format=json"
    req = Request(api, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=8) as res:
            data = loads(res.read().decode("utf-8", errors="ignore"))
            title = str(data.get("title", "")).strip()
            return title or None
    except Exception:
        return None


def get_title_via_watch_page(vid: str) -> str | None:
    url = f"https://www.youtube.com/watch?v={vid}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=8) as res:
            html = res.read().decode("utf-8", errors="ignore")
        m = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        title = unescape(m.group(1)).replace("- YouTube", "").strip()
        return title or None
    except Exception:
        return None


def get_video_title(vid: str) -> str:
    for getter in (get_title_via_oembed, get_title_via_watch_page):
        title = getter(vid)
        if title:
            return title
    return vid


def load_urls(path: Path) -> list[str]:
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        url = line.strip().lstrip("\ufeff")
        if not url or url.startswith("#"):
            continue
        urls.append(url)
    return urls


def fetch_and_save(url: str, out_dir: Path, languages: list[str]) -> tuple[bool, str, str]:
    vid = video_id_from_url(url)
    try:
        transcript = YouTubeTranscriptApi().fetch(vid, languages=languages)
    except YouTubeTranscriptApiException as e:
        detail = str(e).strip() or repr(e)
        first_line = detail.splitlines()[0].strip() if detail else e.__class__.__name__
        return False, vid, f"{e.__class__.__name__}: {first_line}"
    except Exception as e:
        detail = str(e).strip() or repr(e)
        return False, vid, f"{e.__class__.__name__}: {detail}"

    title = sanitize_filename(get_video_title(vid))
    out_path = out_dir / f"{title}.txt"

    with out_path.open("w", encoding="utf-8") as f:
        for item in transcript:
            f.write(item.text.strip() + "\n")

    return True, vid, out_path.name


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Extract YouTube transcripts from URL list using youtube-transcript-api only."
    )
    p.add_argument("--url-file", default="channel_UCOwc__o7u25JDCfqCHK5qaQ_urls.txt")
    p.add_argument("--out-dir", default="subs")
    p.add_argument("--between-delay", type=float, default=1.0)
    p.add_argument("--report-file", default="subs/extract_report_api.txt")
    p.add_argument("--languages", default="ko,en", help="Priority order, comma-separated (default: ko,en)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    url_file = Path(args.url_file)
    out_dir = Path(args.out_dir)
    report_file = Path(args.report_file)
    languages = [x.strip() for x in args.languages.split(",") if x.strip()]

    out_dir.mkdir(parents=True, exist_ok=True)
    report_file.parent.mkdir(parents=True, exist_ok=True)

    urls = load_urls(url_file)
    total = len(urls)
    if total == 0:
        print(f"No URLs found in {url_file}")
        return 1

    success = 0
    failed = 0
    failures: list[tuple[str, str, str]] = []

    print(f"Start: {total} urls")
    start = time.time()

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{total}] processing {url}")
        ok, vid, msg = fetch_and_save(url, out_dir, languages)
        if ok:
            success += 1
            print(f"  OK    id={vid} -> {msg}")
        else:
            failed += 1
            failures.append((url, vid, msg))
            print(f"  FAIL  id={vid} -> {msg}")

        if args.between_delay > 0:
            time.sleep(args.between_delay)

    elapsed = time.time() - start
    lines = [
        f"total={total}",
        f"success={success}",
        f"failed={failed}",
        f"elapsed_sec={elapsed:.1f}",
        "",
        "[failed items]",
    ]
    for url, vid, reason in failures:
        lines.append(f"{vid}\t{url}\t{reason}")
    report_file.write_text("\n".join(lines), encoding="utf-8")

    print("\nDone")
    print(f"  total={total}, success={success}, failed={failed}, elapsed={elapsed:.1f}s")
    print(f"  report={report_file.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
