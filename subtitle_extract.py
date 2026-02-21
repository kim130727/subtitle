import subprocess
import re
from pathlib import Path

# ==========================
# 👇 여기에 유튜브 주소 입력
# ==========================
url = "https://www.youtube.com/watch?v=MECMVYnkV-o4"

out_dir = Path("subs")
out_dir.mkdir(exist_ok=True)

def vtt_to_text(vtt_path: Path) -> str:
    s = vtt_path.read_text(encoding="utf-8", errors="ignore")
    s = re.sub(r"WEBVTT.*\n", "", s)
    s = re.sub(r"\n\d+\n", "\n", s)  # cue 번호
    s = re.sub(
        r"\d{2}:\d{2}:\d{2}\.\d{3}\s-->\s\d{2}:\d{2}:\d{2}\.\d{3}.*\n",
        "",
        s,
    )
    s = re.sub(r"<[^>]+>", "", s)  # 태그 제거

    lines = [ln.strip() for ln in s.splitlines()]
    lines = [ln for ln in lines if ln]

    cleaned = []
    for ln in lines:
        if not cleaned or cleaned[-1] != ln:
            cleaned.append(ln)

    return "\n".join(cleaned)

def run_yt_dlp_subs(lang_pattern: str) -> int:
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", lang_pattern,
        "--sub-format", "vtt",
        "-o", str(out_dir / "%(title)s.%(ext)s"),
        url,
    ]
    print(f"자막 다운로드 시도: {lang_pattern}")
    # ✅ check=False 로 실패해도 계속 진행
    p = subprocess.run(cmd, check=False)
    return p.returncode

# 1) ✅ 한국어만 먼저 받기 (가장 안전)
rc_ko = run_yt_dlp_subs("ko.*")
# 2) (옵션) 영어도 시도하되, 실패해도 무시
_ = run_yt_dlp_subs("en.*")

# 3) ✅ 지금 다운로드된 vtt 중에서 한국어 vtt 선택
vtt_files = sorted(out_dir.glob("*.vtt"))
if not vtt_files:
    raise SystemExit("❌ vtt 파일이 없습니다. (자막이 없는 영상일 수 있음)")

# ko 관련 파일 우선 선택: ko-orig > ko
ko_candidates = [p for p in vtt_files if ".ko-orig.vtt" in p.name or ".ko.vtt" in p.name]
target_vtt = None
if ko_candidates:
    # ko-orig 먼저, 없으면 ko
    ko_orig = [p for p in ko_candidates if ".ko-orig.vtt" in p.name]
    target_vtt = sorted(ko_orig)[-1] if ko_orig else sorted(ko_candidates)[-1]
else:
    # 한국어가 없으면 그냥 마지막 vtt라도 변환
    target_vtt = vtt_files[-1]

# 4) txt 저장
text = vtt_to_text(target_vtt)
txt_path = target_vtt.with_suffix(".txt")
txt_path.write_text(text, encoding="utf-8")

print("\n완료 ✔")
print("변환 대상 VTT:", target_vtt)
print("TXT 파일:", txt_path)
print(f"(참고) ko 다운로드 returncode={rc_ko}")