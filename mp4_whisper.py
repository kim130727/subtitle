from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from faster_whisper import WhisperModel
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

load_dotenv()

# Hugging Face 관련 경고 완화
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def format_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours = ms // 3_600_000
    ms %= 3_600_000
    minutes = ms // 60_000
    ms %= 60_000
    secs = ms // 1000
    ms %= 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?…])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"[·•▪■□]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def should_skip_segment(text: str, duration: float) -> bool:
    cleaned = normalize_text(text)

    if not cleaned:
        return True

    if len(cleaned) <= 1 and duration < 1.0:
        return True

    if re.fullmatch(r"[ㅋㅎㅠㅜ~.\-!?]+", cleaned):
        return True

    return False


def merge_lines_for_txt(segments) -> list[str]:
    lines: list[str] = []
    buffer = ""

    for seg in segments:
        text = normalize_text(seg.text)
        duration = max(0.0, float(seg.end - seg.start))

        if should_skip_segment(text, duration):
            continue

        if not buffer:
            buffer = text
            continue

        if buffer.endswith((".", "!", "?", "…")):
            lines.append(buffer)
            buffer = text
            continue

        if len(text) <= 12:
            buffer += " " + text
            continue

        if len(buffer) <= 20:
            buffer += " " + text
            continue

        lines.append(buffer)
        buffer = text

    if buffer:
        lines.append(buffer)

    cleaned_lines = []
    for line in lines:
        line = normalize_text(line)
        if line:
            cleaned_lines.append(line)

    return cleaned_lines


def write_srt(segments, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig") as f:
        srt_index = 1
        for seg in segments:
            text = normalize_text(seg.text)
            duration = max(0.0, float(seg.end - seg.start))

            if should_skip_segment(text, duration):
                continue

            f.write(f"{srt_index}\n")
            f.write(f"{format_timestamp(seg.start)} --> {format_timestamp(seg.end)}\n")
            f.write(f"{text}\n\n")
            srt_index += 1


def write_txt(segments, output_path: Path) -> None:
    lines = merge_lines_for_txt(segments)
    with output_path.open("w", encoding="utf-8-sig") as f:
        for line in lines:
            f.write(line + "\n")


def get_media_duration_seconds(file_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(file_path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def build_model() -> WhisperModel:
    model_name = os.getenv("WHISPER_MODEL", "large-v3-turbo")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    print(f"모델 로딩: {model_name} / device={device} / compute_type={compute_type}")

    return WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )


def transcribe_with_progress(
    model: WhisperModel,
    mp4_file: Path,
    progress: Progress,
    task_id: int,
):
    total_duration = get_media_duration_seconds(mp4_file)

    progress.update(
        task_id,
        total=total_duration if total_duration > 0 else 100,
        completed=0,
        filename=mp4_file.name,
        status="처리중",
    )

    segments_generator, info = model.transcribe(
        str(mp4_file),
        language="ko",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        beam_size=5,
        best_of=5,
        condition_on_previous_text=True,
        word_timestamps=False,
        temperature=0.0,
    )

    collected_segments = []

    for seg in segments_generator:
        collected_segments.append(seg)
        processed_audio = max(0.0, min(seg.end, total_duration))

        progress.update(
            task_id,
            completed=processed_audio,
            status="처리중",
        )

    progress.update(
        task_id,
        completed=total_duration,
        status="저장중",
    )

    return collected_segments, info


def main() -> None:
    input_dir = Path("downloads")
    output_dir = Path("subtitles")
    output_dir.mkdir(exist_ok=True)

    if not input_dir.exists():
        print("downloads 폴더가 없습니다.")
        return

    mp4_files = sorted(input_dir.glob("*.mp4"))
    if not mp4_files:
        print("MP4 파일이 없습니다.")
        return

    try:
        model = build_model()
    except Exception as e:
        print(f"모델 로딩 실패: {e}")
        return

    console = Console()

    progress = Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="left"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        TextColumn("{task.completed:.0f}/{task.total:.0f}초"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        TextColumn("{task.fields[status]}"),
        console=console,
        transient=False,
    )

    task_map: dict[Path, int] = {}

    for mp4_file in mp4_files:
        duration = 100.0
        try:
            duration = get_media_duration_seconds(mp4_file)
        except Exception:
            pass

        task_id = progress.add_task(
            "transcribe",
            total=duration if duration > 0 else 100,
            completed=0,
            filename=mp4_file.name,
            status="대기중",
        )
        task_map[mp4_file] = task_id

    with progress:
        for mp4_file in mp4_files:
            task_id = task_map[mp4_file]

            try:
                progress.update(task_id, status="시작")

                segments, info = transcribe_with_progress(
                    model=model,
                    mp4_file=mp4_file,
                    progress=progress,
                    task_id=task_id,
                )

                srt_path = output_dir / f"{mp4_file.stem}.srt"
                txt_path = output_dir / f"{mp4_file.stem}.txt"

                write_srt(segments, srt_path)
                write_txt(segments, txt_path)

                progress.update(
                    task_id,
                    completed=progress.tasks[task_id].total,
                    status=f"완료 ({info.language}/{info.language_probability:.3f})",
                )

            except subprocess.CalledProcessError as e:
                progress.update(task_id, status="ffprobe 오류")
                console.print(f"[red]{mp4_file.name} ffprobe 오류:[/red] {e}")

            except Exception as e:
                progress.update(task_id, status=f"오류: {type(e).__name__}")
                console.print(f"[red]{mp4_file.name} 실패:[/red] {e}")


if __name__ == "__main__":
    main()