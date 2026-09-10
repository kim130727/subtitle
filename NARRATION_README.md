# 여성 내레이션 MP3 만들기

`text_to_speech.py`는 입력한 텍스트를 한국어 여성 음성 MP3로 변환합니다.
Microsoft Edge 온라인 음성 서비스를 사용하므로 실행할 때 인터넷 연결이 필요합니다.

## 설치

프로젝트 폴더에서 다음 명령을 실행합니다.

```powershell
uv sync
```

`uv`를 사용하지 않는 경우에는 다음과 같이 설치할 수 있습니다.

```powershell
pip install edge-tts
```

## 사용법

텍스트를 명령줄에서 바로 입력:

```powershell
uv run python .\text_to_speech.py "수많은 수학 문제는 아직 이미지와 문서 형태로 존재합니다."
```

출력 파일 이름 지정:

```powershell
uv run python .\text_to_speech.py "안녕하세요." -o .\output\intro.mp3
uv run python .\text_to_speech.py "수많은 수학 문제는 아직 이미지와 문서 형태로 존재합니다." -o .\output\a0001.mp3
uv run python .\text_to_speech.py "모두의 수학은 수학 문제를 전용 DSL 코드로 구조화합니다." -o .\output\a0002.mp3
uv run python .\text_to_speech.py "코드로 한 번 만든 문제는 웹에디터에서 쉽게 수정하고 다시 만들어낼 수 있습니다." -o .\output\a0003.mp3
uv run python .\text_to_speech.py "문제의 구조는 그대로 두고 언어만 바꾸면 같은 문제를 여러 언어로 만들 수 있습니다." -o .\output\a0004.mp3
uv run python .\text_to_speech.py "하나의 문제 코드로 여러 언어와 여러 화면을 만드는 것. 이것이 모두의 수학의 핵심입니다." -o .\output\a0005.mp3
uv run python .\text_to_speech.py "문제 제작부터 다국어 변환, 실제 학습 앱까지 하나의 구조로 연결됩니다." -o .\output\a0006.mp3
uv run python .\text_to_speech.py "수학 문제를 한 번 코드로 만들고, 세계의 언어로 확장합니다. 모두의 수학입니다" -o .\output\a0007.mp3
```

UTF-8 텍스트 파일 읽기:

```powershell
uv run python .\text_to_speech.py --file .\script.txt --output .\narration.mp3
```

인수 없이 실행하면 화면에서 텍스트를 입력받습니다.

```powershell
uv run python .\text_to_speech.py
```

속도와 음높이 조절:

```powershell
uv run python .\text_to_speech.py "조금 느리고 차분한 목소리입니다." --rate=-10% --pitch=-5Hz
```

기본 음성은 한국어 여성 음성 `ko-KR-SunHiNeural`입니다. 다른 Edge TTS 음성을
사용하려면 `--voice` 옵션에 해당 음성 이름을 지정하면 됩니다.
