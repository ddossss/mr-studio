[English](README.md) | 한국어 | [日本語](README.ja.md)

# MR Studio

유튜브 주소나 내 음원 → 보컬 제거 · 키 조절(-5~+5 반음) → MR로 내보내기.

## 실행

`run.bat` 더블클릭 → 브라우저에 앱이 열림 (http://127.0.0.1:7860)

## 기능

순서: ① 음원 넣기 → ② 파트·키 설정 → ③ **미리듣기** → ④ **만들기(내보내기)**  
음원을 넣은 뒤에는 파트·키를 바꿀 때마다 미리듣기가 자동 갱신됩니다 (새 곡의 첫 분리만 1~2분).

- **가져오기**: 유튜브 주소, 또는 내 음원 파일(mp3/wav/flac 등). 파일이 있으면 파일 우선.
- **남길 파트**: 메인 보컬 / 코러스 / 드럼 / 베이스 / 기타 / 피아노 / 관악기 / 그 외 악기를 각각 on/off.
  - 기본값 = 메인 보컬만 끔 → 코러스 포함 MR
  - 전부 켬 → 분리 없이 원곡 키만 조절
  - 관악기(오케스트라용): 트럼펫·호른·트롬본·색소폰·플루트 등을 **한꺼번에** 분리. 트럼펫만 따로 분리하는 모델은 없음.
    관악기나 그 외 악기를 끌 때만 관악기 분리 단계가 추가로 돌아감(첫 처리 +수십 초).
- **키 조절**: 반음 단위 -5~+5 (템포 유지, rubberband)
- **만들기(내보내기)**: 미리듣기로 확인한 설정 그대로 mp3(320k) 또는 wav → `output/` 폴더에도 저장

한 번 분리한 곡은 `cache/`에 저장되어, 파트/키만 바꿔 다시 만들면 몇 초면 끝납니다.

## 구조

- 분리 1단계: Demucs `htdemucs_6s` → 보컬 / 드럼 / 베이스 / 기타 / 피아노 / 그 외
- 분리 2단계: Mel-Roformer Karaoke → 보컬을 메인 보컬 / 코러스로
- (관악기 on/off 시) 분리 0단계: UVR `17_HP-Wind_Inst` → 관악기 / 나머지, 나머지를 1·2단계로
- 믹스(numpy) → 키 조절 + 리미터 + 인코딩(ffmpeg)
- UI: Gradio (v2.0 웹 버전도 같은 앱을 서버에 올리는 방식으로 확장 가능)

## 제한

- **아마존 뮤직은 지원 안 함**: DRM 보호 스트림이라 추출 불가. 구매/보유한 음원 파일을 가져오기로 사용.
- 유튜브 음원은 개인 연습용으로만 사용하세요 (저작권).

## 새 PC에 설치

```bat
winget install --id Gyan.FFmpeg --exact
winget install --id yt-dlp.yt-dlp --exact
winget install --id DenoLand.Deno --exact
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

NVIDIA GPU 권장 (CPU만 있으면 곡당 수 분). 첫 실행 때 분리 모델(~0.9GB)을 `models/`에 자동 다운로드.

## 테스트

`.venv\Scripts\python test_app.py` → `OK`

## Made by

[Perch Creative](https://perch-creative.com) — 웹사이트 · 브랜딩 · 툴 제작
