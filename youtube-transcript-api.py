import re
import subprocess
from html import unescape
from json import loads
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import YouTubeTranscriptApiException

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] or "subtitle"


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


def get_title_via_ytdlp(vid: str) -> str | None:
    cmd = ["yt-dlp", "--print", "%(title)s", "--no-playlist", f"https://www.youtube.com/watch?v={vid}"]
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    title = (p.stdout or "").strip()
    if p.returncode == 0 and title:
        return title.splitlines()[-1].strip()
    return None


def get_video_title(vid: str) -> str:
    for getter in (get_title_via_oembed, get_title_via_ytdlp, get_title_via_watch_page):
        title = getter(vid)
        if title:
            return title
    return vid


def extract_video_id(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    m = re.search(r"(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})", value)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    return None


def dedup_consecutive(lines: list[str]) -> list[str]:
    out: list[str] = []
    prev = None
    for line in lines:
        cur = line.strip()
        if not cur:
            continue
        if cur != prev:
            out.append(cur)
            prev = cur
    return out


def main() -> None:
    input_path = Path("text.txt")
    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} not found")

    raw_lines = input_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    ids: list[str] = []
    seen = set()
    for line in raw_lines:
        vid = extract_video_id(line)
        if not vid:
            continue
        if vid in seen:
            continue
        seen.add(vid)
        ids.append(vid)

    out_dir = Path("subs")
    out_dir.mkdir(parents=True, exist_ok=True)

    api = YouTubeTranscriptApi()
    failures: list[str] = []
    success = 0
    for idx, vid in enumerate(ids, start=1):
        try:
            transcript = api.fetch(vid, languages=["ko", "en"])
            title = sanitize_filename(get_video_title(vid))
            out_path = out_dir / f"{title}.txt"

            lines = [item.text for item in transcript]
            lines = dedup_consecutive(lines)
            out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            success += 1
            print(f"[{idx}/{len(ids)}] OK  {vid} -> {out_path.name}")
        except YouTubeTranscriptApiException as e:
            msg = f"[{idx}/{len(ids)}] FAIL {vid} | {type(e).__name__}: {e}"
            failures.append(msg)
            print(msg)
        except Exception as e:
            msg = f"[{idx}/{len(ids)}] FAIL {vid} | {type(e).__name__}: {e}"
            failures.append(msg)
            print(msg)

    if failures:
        fail_path = out_dir / "_failed_ids.log"
        fail_path.write_text("\n".join(failures) + "\n", encoding="utf-8")
        print(f"\nDone. success={success}, failed={len(failures)}")
        print(f"Failure log: {fail_path}")
    else:
        print(f"\nDone. success={success}, failed=0")


out_dir = Path("subs")
if __name__ == "__main__":
    main()
