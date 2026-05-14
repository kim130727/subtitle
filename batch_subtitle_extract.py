import argparse
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def video_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith('youtu.be'):
        return parsed.path.strip('/')
    qs = parse_qs(parsed.query)
    return qs.get('v', ['unknown'])[0]


def vtt_to_text(vtt_path: Path) -> str:
    s = vtt_path.read_text(encoding='utf-8', errors='ignore')
    s = re.sub(r'^WEBVTT.*$', '', s, flags=re.MULTILINE)
    s = re.sub(r'^\d+$', '', s, flags=re.MULTILINE)
    s = re.sub(
        r'^\d{2}:\d{2}:\d{2}\.\d{3}\s-->\s\d{2}:\d{2}:\d{2}\.\d{3}.*$',
        '',
        s,
        flags=re.MULTILINE,
    )
    s = re.sub(r'<[^>]+>', '', s)

    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    dedup = []
    for ln in lines:
        if not dedup or dedup[-1] != ln:
            dedup.append(ln)
    return '\n'.join(dedup)


def run_yt_dlp(url: str, out_dir: Path, lang_pattern: str, cookies_file: str | None) -> int:
    cmd = [
        'yt-dlp',
        '--skip-download',
        '--write-subs',
        '--write-auto-subs',
        '--sub-langs',
        lang_pattern,
        '--sub-format',
        'vtt',
        '--no-playlist',
        '-o',
        str(out_dir / '%(title).180B [%(id)s].%(ext)s'),
        url,
    ]
    if cookies_file:
        cmd[1:1] = ['--cookies', cookies_file]
    p = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return p.returncode


def run_yt_dlp_with_retry(
    url: str,
    out_dir: Path,
    lang_pattern: str,
    retries: int,
    retry_delay: float,
    cookies_file: str | None,
) -> int:
    attempts = retries + 1
    last_rc = 1
    for i in range(attempts):
        last_rc = run_yt_dlp(url, out_dir, lang_pattern, cookies_file)
        if last_rc == 0:
            return 0
        if i < attempts - 1 and retry_delay > 0:
            time.sleep(retry_delay)
    return last_rc


def choose_vtt_for_video(vtt_files: list[Path], vid: str) -> Path | None:
    candidates = [p for p in vtt_files if f'[{vid}]' in p.name]
    if not candidates:
        return None

    priorities = [
        '.ko-orig.vtt',
        '.ko.vtt',
        '.en-orig.vtt',
        '.en.vtt',
        '.live_chat.vtt',
    ]

    for suffix in priorities:
        filtered = [p for p in candidates if p.name.endswith(suffix)]
        if filtered:
            return sorted(filtered)[-1]

    return sorted(candidates)[-1]


def cleanup_vtt_for_video(out_dir: Path, vid: str) -> None:
    for p in out_dir.glob('*.vtt'):
        if f'[{vid}]' in p.name:
            p.unlink(missing_ok=True)


def to_txt(vtt_path: Path) -> Path:
    text = vtt_to_text(vtt_path)

    stem = vtt_path.stem
    for suffix in ('.ko-orig', '.ko', '.en-orig', '.en', '.live_chat'):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break

    txt_path = vtt_path.with_name(f'{stem}.txt')
    txt_path.write_text(text, encoding='utf-8')
    return txt_path


def extract_one(
    url: str,
    out_dir: Path,
    retries: int,
    retry_delay: float,
    cookies_file: str | None,
) -> tuple[bool, str, str]:
    vid = video_id_from_url(url)

    run_yt_dlp_with_retry(url, out_dir, 'ko.*', retries, retry_delay, cookies_file)
    run_yt_dlp_with_retry(url, out_dir, 'en.*', retries, retry_delay, cookies_file)

    vtt = choose_vtt_for_video(sorted(out_dir.glob('*.vtt')), vid)
    if vtt is None:
        return False, vid, 'subtitle not found (private/unavailable/no caption/429 possible)'

    txt_path = to_txt(vtt)
    cleanup_vtt_for_video(out_dir, vid)
    return True, vid, txt_path.name


def load_urls(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding='utf-8').splitlines():
        url = line.strip()
        if not url or url.startswith('#'):
            continue
        urls.append(url)
    return urls


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Extract transcript txt files from a URL list.')
    p.add_argument('--url-file', default='channel_UCOwc__o7u25JDCfqCHK5qaQ_urls.txt')
    p.add_argument('--out-dir', default='subs')
    p.add_argument('--between-delay', type=float, default=2.0)
    p.add_argument('--retries', type=int, default=1)
    p.add_argument('--retry-delay', type=float, default=4.0)
    p.add_argument('--report-file', default='subs/extract_report.txt')
    p.add_argument(
        '--cookies-file',
        default=None,
        help='Path to cookies.txt for private/unlisted/age-restricted videos',
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    url_file = Path(args.url_file)
    out_dir = Path(args.out_dir)
    report_file = Path(args.report_file)

    out_dir.mkdir(parents=True, exist_ok=True)
    report_file.parent.mkdir(parents=True, exist_ok=True)

    urls = load_urls(url_file)
    total = len(urls)
    if total == 0:
        print(f'No URLs found in {url_file}')
        return 1

    success = 0
    failed = 0
    failures: list[tuple[str, str, str]] = []

    print(f'Start: {total} urls')
    start = time.time()

    for i, url in enumerate(urls, start=1):
        print(f'[{i}/{total}] processing {url}')
        ok, vid, msg = extract_one(
            url=url,
            out_dir=out_dir,
            retries=max(args.retries, 0),
            retry_delay=max(args.retry_delay, 0.0),
            cookies_file=args.cookies_file,
        )

        if ok:
            success += 1
            print(f'  OK    id={vid} -> {msg}')
        else:
            failed += 1
            failures.append((url, vid, msg))
            print(f'  FAIL  id={vid} -> {msg}')

        if args.between_delay > 0:
            time.sleep(args.between_delay)

        print(f'  Progress: success={success}, failed={failed}')

    elapsed = time.time() - start
    lines = [
        f'total={total}',
        f'success={success}',
        f'failed={failed}',
        f'elapsed_sec={elapsed:.1f}',
        '',
        '[failed items]',
    ]
    for url, vid, reason in failures:
        lines.append(f'{vid}\t{url}\t{reason}')

    report_file.write_text('\n'.join(lines), encoding='utf-8')

    print('\nDone')
    print(f'  total={total}, success={success}, failed={failed}, elapsed={elapsed:.1f}s')
    print(f'  report={report_file.resolve()}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
