from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


def parse_ffmpeg_out_time_to_seconds(value: str) -> float:
    try:
        hh, mm, ss = value.strip().split(":")
        return int(hh) * 3600 + int(mm) * 60 + float(ss)
    except Exception:
        return 0.0


def get_duration_seconds(src: Path) -> Optional[float]:
    if shutil.which("ffprobe") is None:
        return None

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(src),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return None

    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return None
    return duration if duration > 0 else None


def convert_file_with_progress(
    src: Path,
    dst: Path,
    overwrite: bool,
    progress: Progress,
    task_id: int,
    total_seconds: float,
) -> None:
    if dst.exists() and not overwrite:
        progress.update(task_id, completed=total_seconds, status="SKIP")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y" if overwrite else "-n",
        "-i",
        str(src),
        "-vn",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-progress",
        "pipe:1",
        "-nostats",
        "-loglevel",
        "error",
        str(dst),
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    latest_error_lines: list[str] = []
    if process.stdout is not None:
        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line:
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                if key == "out_time":
                    seconds = min(parse_ffmpeg_out_time_to_seconds(value), total_seconds)
                    progress.update(task_id, completed=seconds, status="RUN")
                elif key == "progress" and value == "end":
                    progress.update(task_id, completed=total_seconds, status="DONE")
            else:
                latest_error_lines.append(line)
                if len(latest_error_lines) > 5:
                    latest_error_lines.pop(0)

    return_code = process.wait()
    if return_code == 0:
        progress.update(task_id, completed=total_seconds, status="DONE")
    else:
        progress.update(task_id, status="FAIL")
        if latest_error_lines:
            progress.console.print(f"[FAIL] {src.name}")
            for err in latest_error_lines:
                progress.console.print(f"  {err}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert MP4 files in downloads/ to M4A files in m4a/."
    )
    parser.add_argument("--input-dir", default="downloads", help="Input folder (default: downloads)")
    parser.add_argument("--output-dir", default="m4a", help="Output folder (default: m4a)")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output files if they already exist.",
    )
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found. Please install FFmpeg and add it to PATH.")
        return 1

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Input folder not found: {input_dir}")
        return 1

    raw_files = sorted(input_dir.glob("*.mp4")) + sorted(input_dir.glob("*.MP4"))
    # Windows is case-insensitive, so "*.mp4" and "*.MP4" can return duplicates.
    unique_by_path: dict[str, Path] = {}
    for p in raw_files:
        unique_by_path[str(p.resolve()).lower()] = p
    mp4_files = sorted(unique_by_path.values(), key=lambda p: p.name.lower())
    if not mp4_files:
        print(f"No MP4 files found in: {input_dir}")
        return 0

    console = Console()
    console.print(f"Found {len(mp4_files)} file(s).")

    progress = Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="left"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        TextColumn("{task.completed:.0f}/{task.total:.0f}s"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        TextColumn("{task.fields[status]}"),
        console=console,
        transient=False,
    )

    with progress:
        task_map: dict[Path, int] = {}

        for mp4_path in mp4_files:
            duration = get_duration_seconds(mp4_path) or 100.0
            task_id = progress.add_task(
                "convert",
                filename=mp4_path.name,
                total=duration,
                completed=0,
                status="WAIT",
            )
            task_map[mp4_path] = task_id

        for mp4_path in mp4_files:
            out_path = output_dir / f"{mp4_path.stem}.m4a"
            task_id = task_map[mp4_path]
            total = progress.tasks[task_id].total or 100.0
            convert_file_with_progress(
                src=mp4_path,
                dst=out_path,
                overwrite=args.overwrite,
                progress=progress,
                task_id=task_id,
                total_seconds=float(total),
            )

    console.print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
