"""텍스트를 한국어 여성 내레이션 MP3로 변환한다."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import edge_tts


DEFAULT_VOICE = "ko-KR-SunHiNeural"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="입력한 텍스트를 여성 내레이션 MP3 파일로 만듭니다."
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "text",
        nargs="?",
        help='음성으로 변환할 텍스트 (예: "안녕하세요")',
    )
    input_group.add_argument(
        "-f",
        "--file",
        type=Path,
        help="읽을 UTF-8 텍스트 파일",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("narration.mp3"),
        help="저장할 MP3 경로 (기본값: narration.mp3)",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Edge TTS 음성 이름 (기본값: {DEFAULT_VOICE})",
    )
    parser.add_argument(
        "--rate",
        default="+0%",
        help='말하기 속도 (예: "-10%%", "+20%%"; 기본값: +0%%)',
    )
    parser.add_argument(
        "--pitch",
        default="+0Hz",
        help='음높이 (예: "-5Hz", "+10Hz"; 기본값: +0Hz)',
    )
    parser.add_argument(
        "--volume",
        default="+0%",
        help='음량 (예: "-10%%", "+20%%"; 기본값: +0%%)',
    )
    return parser


def get_text(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    if args.file is not None:
        try:
            text = args.file.read_text(encoding="utf-8")
        except OSError as exc:
            parser.error(f"텍스트 파일을 읽을 수 없습니다: {exc}")
    elif args.text is not None:
        text = args.text
    else:
        try:
            text = input("내레이션으로 만들 텍스트를 입력하세요: ")
        except EOFError:
            parser.error("텍스트를 입력하거나 --file 옵션을 사용하세요.")

    text = text.strip()
    if not text:
        parser.error("변환할 텍스트가 비어 있습니다.")
    return text


async def create_mp3(
    text: str,
    output: Path,
    voice: str,
    rate: str,
    pitch: str,
    volume: str,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
    )
    await communicate.save(str(output))


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    text = get_text(args, parser)

    output = args.output.expanduser()
    if output.suffix.lower() != ".mp3":
        output = output.with_suffix(".mp3")

    try:
        asyncio.run(
            create_mp3(
                text=text,
                output=output,
                voice=args.voice,
                rate=args.rate,
                pitch=args.pitch,
                volume=args.volume,
            )
        )
    except (edge_tts.exceptions.EdgeTTSException, OSError) as exc:
        parser.exit(1, f"MP3 생성 실패: {exc}\n")

    print(f"MP3 생성 완료: {output.resolve()}")


if __name__ == "__main__":
    main()
