# subtitle

`downloads` 폴더의 MP4 파일을 Whisper로 받아쓰기해서 자막 파일(`.srt`)과 텍스트 파일(`.txt`)로 저장하는 프로젝트입니다.

## 기능

- `downloads/*.mp4` 파일 일괄 처리
- `faster-whisper` 기반 음성 인식
- 진행률(퍼센트, ETA, 처리 속도) 출력
- 결과 파일 자동 생성
  - `subtitles/<파일명>.srt`
  - `subtitles/<파일명>.txt`

## 요구 사항

- Python 3.11 이상
- `ffprobe` (FFmpeg 패키지에 포함)
- CPU 실행 환경 (기본 설정)

## 설치

### 1) 가상환경 생성 및 활성화

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) 의존성 설치

```powershell
pip install -U pip
pip install faster-whisper
```

또는 `uv`를 사용한다면:

```powershell
uv sync
```

## 사용 방법

### 1) 변환할 MP4 파일 넣기

`downloads` 폴더에 MP4 파일을 넣습니다.

예시:

```text
downloads/
  lecture1.mp4
  lecture2.mp4
```

### 2) 스크립트 실행

```powershell
python .\mp4_whisper.py
uv run mp4_whisper.py
uv add rich python-dotenv faster-whisper
```

### 3) 결과 확인

실행 후 `subtitles` 폴더에 결과가 생성됩니다.

```text
subtitles/
  lecture1.srt
  lecture1.txt
  lecture2.srt
  lecture2.txt
```

## 현재 기본 설정

`mp4_whisper.py` 기준:

- 모델: `small`
- 언어: `ko` (한국어 고정)
- 디바이스: `cpu`
- 연산 타입: `int8`
- VAD 필터: 활성화

필요하면 코드에서 모델 크기, 언어, 디바이스를 변경할 수 있습니다.

## 문제 해결

- `ffprobe` 관련 오류가 나면 FFmpeg를 설치하고 환경 변수(PATH)에 추가했는지 확인하세요.
- `downloads` 폴더에 MP4가 없으면 처리할 파일이 없다는 메시지가 출력됩니다.
- 첫 실행 시 모델 다운로드로 시간이 오래 걸릴 수 있습니다.
