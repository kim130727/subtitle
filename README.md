# subtitle

`downloads` 폴더의 MP4 파일을 처리하는 간단한 스크립트 모음입니다.

- `mp4_to_m4a.py`: MP4에서 오디오를 추출해 M4A로 변환
- `mp4_whisper.py`: MP4 음성을 인식해 자막(`.srt`)과 텍스트(`.txt`) 생성

## 요구 사항

- Python 3.11 이상
- FFmpeg (`ffmpeg`, `ffprobe` 명령이 PATH에 있어야 함)

## 설치

### 1) 가상환경 생성 및 활성화

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) 의존성 설치

`uv` 사용 시:

```powershell
uv sync
```

`pip` 사용 시:

```powershell
pip install -U pip
pip install faster-whisper python-dotenv rich
```

## 폴더 구조

```text
downloads/   # 입력 MP4 파일
m4a/         # 오디오 변환 결과(.m4a)
subtitles/   # 자막/텍스트 결과(.srt, .txt)
```

## 사용 방법

### 1) MP4 -> M4A 변환

```powershell
python .\mp4_to_m4a.py
```

옵션:

- `--input-dir` 입력 폴더 (기본값: `downloads`)
- `--output-dir` 출력 폴더 (기본값: `m4a`)
- `--overwrite` 기존 파일 덮어쓰기

예시:

```powershell
python .\mp4_to_m4a.py --input-dir downloads --output-dir m4a --overwrite
```

### 2) MP4 -> 자막(SRT/TXT) 생성

```powershell
python .\mp4_whisper.py
```

실행 후 `subtitles` 폴더에 아래 파일이 생성됩니다.

```text
subtitles/
  sample.srt
  sample.txt
```

## 환경 변수 (`.env`)

`mp4_whisper.py`는 아래 환경 변수를 지원합니다.

```env
WHISPER_MODEL=large-v3-turbo
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

언어는 현재 코드에서 한국어(`ko`)로 고정되어 있습니다.

## 문제 해결

- `ffmpeg not found` 또는 `ffprobe` 오류:
  FFmpeg를 설치하고 PATH 설정을 확인하세요.
- `No MP4 files found`:
  `downloads` 폴더에 `.mp4` 파일이 있는지 확인하세요.
- 첫 실행이 느린 경우:
  Whisper 모델 다운로드가 진행되기 때문입니다.
