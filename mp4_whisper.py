from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from faster_whisper import WhisperModel


def format_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours = ms // 3_600_000
    ms %= 3_600_000
    minutes = ms // 60_000
    ms %= 60_000
    secs = ms // 1000
    ms %= 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def format_seconds(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def write_srt(segments, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig") as f:
        srt_index = 1
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            f.write(f"{srt_index}\n")
            f.write(f"{format_timestamp(seg.start)} --> {format_timestamp(seg.end)}\n")
            f.write(f"{text}\n\n")
            srt_index += 1


def write_txt(segments, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig") as f:
        for seg in segments:
            text = seg.text.strip()
            if text:
                f.write(text + "\n")


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


def build_progress_bar(percent: int, width: int = 30) -> str:
    filled = int(width * percent / 100)
    return "█" * filled + "-" * (width - filled)


def transcribe_with_progress(model: WhisperModel, mp4_file: Path):
    total_duration = get_media_duration_seconds(mp4_file)

    segments_generator, info = model.transcribe(
        str(mp4_file),
        language="ko",
        vad_filter=True,
        beam_size=5,
    )

    collected_segments = []
    last_printed_percent = -1
    start_time = time.time()

    print(f"총 길이: {total_duration:.1f}초 ({format_seconds(total_duration)})")

    for seg in segments_generator:
        collected_segments.append(seg)

        processed_audio = max(0.0, min(seg.end, total_duration))

        if total_duration > 0:
            percent = min(int((processed_audio / total_duration) * 100), 100)
        else:
            percent = 0

        if percent != last_printed_percent:
            elapsed = time.time() - start_time

            # 오디오 처리 속도(배속): 예) 2.5x = 1초 처리에 실제 0.4초
            speed = (processed_audio / elapsed) if elapsed > 0 else 0.0

            remaining_audio = max(total_duration - processed_audio, 0.0)
            eta = (remaining_audio / speed) if speed > 0 else 0.0

            bar = build_progress_bar(percent, width=30)

            print(
                f"\r[{bar}] {percent:3d}% | "
                f"{format_seconds(processed_audio)} / {format_seconds(total_duration)} | "
                f"경과 {format_seconds(elapsed)} | "
                f"ETA {format_seconds(eta)} | "
                f"{speed:.2f}x",
                end="",
                flush=True,
            )
            last_printed_percent = percent

    total_elapsed = time.time() - start_time
    print(
        f"\r[{'█' * 30}] 100% | "
        f"{format_seconds(total_duration)} / {format_seconds(total_duration)} | "
        f"총 {format_seconds(total_elapsed)}"
    )

    return collected_segments, info


def main() -> None:
    input_dir = Path("downloads")
    output_dir = Path("subtitles")
    output_dir.mkdir(exist_ok=True)

    model = WhisperModel(
        "small",
        device="cpu",
        compute_type="int8",
    )

    mp4_files = sorted(input_dir.glob("*.mp4"))
    if not mp4_files:
        print("MP4 파일이 없습니다.")
        return

    total_files = len(mp4_files)

    for idx, mp4_file in enumerate(mp4_files, start=1):
        print(f"\n[{idx}/{total_files}] 처리중: {mp4_file.name}")

        try:
            segments, info = transcribe_with_progress(model, mp4_file)

            srt_path = output_dir / f"{mp4_file.stem}.srt"
            txt_path = output_dir / f"{mp4_file.stem}.txt"

            write_srt(segments, srt_path)
            write_txt(segments, txt_path)

            print(f"완료: {srt_path.name}, {txt_path.name}")
            print(f"감지 언어: {info.language} / 확률: {info.language_probability:.3f}")

        except Exception as e:
            print(f"\n오류: {mp4_file.name} -> {e}")


if __name__ == "__main__":
    main()