"""MR Studio v1 — 유튜브 주소나 내 음원 → 보컬 제거 MR + 키 조절(-5~+5) → mp3/wav 내보내기."""
import functools
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import gradio as gr
import numpy as np
import soundfile as sf
from audio_separator.separator import Separator

ROOT = Path(__file__).parent
MODELS = ROOT / "models"  # 분리 모델(첫 실행 때 자동 다운로드)
CACHE = ROOT / "cache"    # 곡별 분리 결과 — 같은 곡은 다시 분리하지 않음
OUT = ROOT / "output"

# UI 라벨 → stem 파일명
STEMS = {"메인 보컬": "lead", "코러스": "backing", "드럼": "drums", "베이스": "bass",
         "기타": "guitar", "피아노": "piano", "관악기": "wind", "그 외 악기": "other"}
DEMUCS = "htdemucs_6s.yaml"
KARAOKE = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
WIND = "17_HP-Wind_Inst-UVR.pth"  # 트럼펫·호른·색소폰·플루트 등 관악기 전체 (트럼펫 단독 모델은 없음)


@functools.lru_cache  # 미리듣기 갱신마다 유튜브에 다시 접속하지 않게
def download(url):
    if not re.search(r"(youtube\.com|youtu\.be)/", url):
        raise gr.Error("유튜브 주소만 지원합니다. 아마존 뮤직은 DRM 보호로 추출할 수 없으니, 갖고 있는 음원 파일을 올려주세요.")
    r = subprocess.run(
        ["yt-dlp", "-x", "--audio-format", "wav", "--no-playlist", "--encoding", "utf-8",
         "-o", str(CACHE / "dl" / "%(title)s [%(id)s].%(ext)s"), "--print", "after_move:filepath", url],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise gr.Error("다운로드 실패: " + (r.stderr.strip().splitlines() or ["알 수 없는 오류"])[-1])
    return Path(r.stdout.strip().splitlines()[-1])


def separate(src, progress, wind):
    d = CACHE / (hashlib.sha1(src.read_bytes()).hexdigest()[:16] + ("-wind" if wind else ""))
    if (d / "done").exists():  # 완료 표시가 있을 때만 캐시 사용 (중간에 꺼져 반쯤 쓴 파일 방지)
        return d
    d.mkdir(parents=True, exist_ok=True)
    # normalization_threshold=1.0: stem별 음량 보정을 끄고 원래 밸런스 그대로 믹스
    sep = Separator(model_file_dir=str(MODELS), output_dir=str(d), normalization_threshold=1.0)
    stages = [("악기 분리", DEMUCS, None, {"Vocals": "vocals", "Drums": "drums", "Bass": "bass",
                                          "Guitar": "guitar", "Piano": "piano", "Other": "other"}),
              ("메인 보컬 / 코러스 분리", KARAOKE, d / "vocals.wav", {"Vocals": "lead", "Instrumental": "backing"})]
    if wind:  # 관악기를 먼저 떼어내고, 나머지를 파트별로 분리
        stages.insert(0, ("관악기 분리", WIND, src, {"Woodwinds": "wind", "No Woodwinds": "nowind"}))
        src = d / "nowind.wav"
    tq = progress.tqdm
    for i, (name, model, path, names) in enumerate(stages, 1):
        desc = f"{i}/{len(stages)} {name} 중…"
        progress(0, desc=desc)
        # 모델 내부 tqdm(이름 없음)은 track_tqdm으로 progress.tqdm에 전달됨 → 여기서 단계 이름을 붙여 한 줄로 표시
        progress.tqdm = lambda it=None, _desc=None, *a, desc=desc, **k: tq(it, _desc or desc, *a, **k)
        sep.load_model(model)
        sep.separate(str(path or src), names)
    progress.tqdm = tq
    (d / "done").touch()
    return d


def mix(d, keep):
    tracks = [sf.read(d / f"{STEMS[k]}.wav", dtype="float32") for k in keep]
    n = min(len(a) for a, _ in tracks)
    audio = sum(a[:n] for a, _ in tracks)
    return audio / max(1.0, float(np.abs(audio).max())), tracks[0][1]  # 클리핑 방지


def encode(inp, semitones, out):
    # 키를 바꾸면 피크가 최대 ~30% 커져 풀스케일 음원이 클리핑됨 → 리미터로 피크만 잡음(자동 음량 보정 off)
    af = ["-af", f"rubberband=pitch={2 ** (semitones / 12)}:pitchq=quality,"
                 "alimiter=limit=0.97:level=0:latency=1"] if semitones else []
    br = ["-b:a", "320k"] if out.suffix == ".mp3" else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(inp), "-vn", *af, *br, str(out)], check=True)
    return out


def render(url, file, keep, semitones, fmt, out_dir, progress):
    if not shutil.which("ffmpeg"):
        raise gr.Error("ffmpeg가 없습니다: winget install --id Gyan.FFmpeg --exact")
    if not keep:
        raise gr.Error("남길 파트를 하나 이상 선택하세요.")
    if file:
        src = Path(file)
    elif url.strip():
        progress(0, desc="유튜브에서 가져오는 중…")
        src = download(url.strip())
    else:
        raise gr.Error("유튜브 주소를 넣거나 음원 파일을 올려주세요.")

    semitones = int(semitones)
    if set(keep) == set(STEMS):  # 전부 남김 = 키만 조절, 분리 불필요
        inp, label = src, "key"
    else:
        # 관악기는 분리 전엔 주로 '그 외 악기'에 섞여 있음 → 둘 중 하나라도 빼면 관악기 분리를 먼저 돌림
        wind = not {"관악기", "그 외 악기"} <= set(keep)
        d = separate(src, progress, wind)
        audio, sr = mix(d, [k for k in keep if wind or k != "관악기"])
        inp = d / "mix.wav"
        sf.write(inp, audio, sr, subtype="FLOAT")  # PCM_16은 정확히 1.0에서 넘쳐 부호가 뒤집힘
        # 파일명에 조합을 드러내 서로 덮어쓰지 않게: MR / no-wind / only-wind …
        kept = [STEMS[k] for k in STEMS if k in keep]
        cut = [STEMS[k] for k in STEMS if k not in keep]
        label = "MR" if cut == ["lead"] else "only-" + "-".join(kept) if len(kept) < len(cut) else "no-" + "-".join(cut)

    progress(0.9, desc="키 조절 중…")
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(encode(inp, semitones, out_dir / f"{src.stem}_{label}_key{semitones:+d}.{fmt}"))


def preview(url, file, keep, semitones, progress=gr.Progress(track_tqdm=True)):
    return render(url, file, keep, semitones, "mp3", CACHE / "preview", progress)


def auto_preview(url, file, keep, semitones, progress=gr.Progress(track_tqdm=True)):
    # 파트/키를 바꾸면 미리듣기에 바로 반영 (음원이 아직 없으면 조용히 건너뜀)
    if not keep or not (file or url.strip()):
        return gr.skip()
    return preview(url, file, keep, semitones, progress)


def export(url, file, keep, semitones, fmt, progress=gr.Progress(track_tqdm=True)):
    return render(url, file, keep, semitones, fmt, OUT, progress)


def key_view(v):
    return f'<div class="key-val">{"원키" if v == 0 else f"{v:+d}"}</div><div class="key-sub">반음 · 템포 유지</div>'


THEME = gr.themes.Base(
    primary_hue=gr.themes.colors.orange, neutral_hue=gr.themes.colors.zinc, radius_size="lg",
    font=[gr.themes.GoogleFont("Noto Sans KR"), "Malgun Gothic", "sans-serif"],
)
CSS = """
:root, .dark { --accent: #ff6b35; --accent-2: #ff9a5c; --panel: #15171d; --line: #262932; --muted: #8b90a0; }
html, body { background: radial-gradient(1200px 520px at 20% -8%, #2b1a11 0%, #0c0d11 60%) fixed #0c0d11 !important; }
.gradio-container, .gradio-container .main, .gradio-container .wrap.contain { background: transparent !important; }
.gradio-container { max-width: 1120px !important; margin: 0 auto !important; }
footer { display: none !important; }

#hero { padding: 28px 4px 8px; }
#hero h1 { font-size: 34px; font-weight: 800; letter-spacing: -0.02em; margin: 0; color: #f4f4f6; }
#hero h1 span { color: var(--accent); }
#hero p { color: var(--muted); margin: 6px 0 0; font-size: 15px; }

.card { background: var(--panel) !important; border: 1px solid var(--line) !important; border-radius: 18px !important;
        padding: 18px !important; gap: 12px !important; }
.step { font-size: 13px; font-weight: 700; letter-spacing: .04em; color: var(--accent); margin: 0 0 2px; }
.step b { color: #eceef3; font-size: 16px; margin-left: 6px; letter-spacing: 0; }
.hint { color: var(--muted); font-size: 13px; margin: 0; }

/* 파트 = 알약 토글 */
#parts .wrap { gap: 8px !important; }
#parts label { border: 1px solid var(--line) !important; background: #1c1f27 !important; border-radius: 999px !important;
               padding: 8px 16px !important; transition: all .15s; color: var(--muted) !important; cursor: pointer; }
#parts label input { display: none !important; }
#parts label:has(input:checked) { background: rgba(255,107,53,.14) !important; border-color: var(--accent) !important; color: #fff !important; }
#parts label:has(input:checked)::before { content: "●"; color: var(--accent); margin-right: 6px; font-size: 10px; }
#parts label:not(:has(input:checked)) span { text-decoration: line-through; opacity: .7; }

/* 키 − 값 + */
#keyrow { align-items: center !important; justify-content: center !important; gap: 20px !important; }
#keyrow button { font-size: 28px !important; font-weight: 700; height: 64px; width: 72px !important; min-width: 72px !important; flex: 0 0 72px !important; border-radius: 16px !important;
                 background: #1c1f27 !important; border: 1px solid var(--line) !important; color: #eceef3 !important; }
#keyrow button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }
#keyval { text-align: center; flex: 0 0 140px !important; }
.key-val { font-size: 40px; font-weight: 800; color: #fff; line-height: 1.1; font-variant-numeric: tabular-nums; }
.key-sub { font-size: 12px; color: var(--muted); }

/* 버튼 */
#listen { background: transparent !important; border: 1.5px solid var(--accent) !important; color: var(--accent) !important;
          font-size: 16px !important; font-weight: 700; height: 52px; }
#listen:hover { background: rgba(255,107,53,.1) !important; }
#make { background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important; border: none !important; color: #1a0d05 !important;
        font-size: 16px !important; font-weight: 800; height: 52px; box-shadow: 0 8px 24px rgba(255,107,53,.25); }

/* 진행 막대 — 미리듣기 플레이어 위에 표시되므로 비어 있어도 높이 확보 */
#player { min-height: 150px; border: 1px dashed var(--line) !important; border-radius: 14px !important; }
.meta-text { display: none !important; }
.progress-level-inner, .progress-text { color: #eceef3 !important; font-size: 13px !important; }
.progress-bar-wrap { width: 85% !important; height: 10px !important; border: none !important; border-radius: 999px !important; background: #2a2d36 !important; }
.progress-bar { background: linear-gradient(90deg, var(--accent), var(--accent-2)) !important; border-radius: 999px !important; }
.eta-bar { background: rgba(255,107,53,.12) !important; }
"""
DARK = "() => { const u = new URL(location); if (u.searchParams.get('__theme') !== 'dark') { u.searchParams.set('__theme', 'dark'); location.replace(u); } }"

with gr.Blocks(title="MR Studio") as demo:
    gr.HTML('<div id="hero"><h1>MR <span>Studio</span></h1><p>유튜브·내 음원에서 보컬을 지우고, 키를 맞추고, 바로 MR로.</p></div>')
    with gr.Row(equal_height=False):
        with gr.Column(scale=3):
            with gr.Column(elem_classes="card"):
                gr.HTML('<p class="step">STEP 1<b>음원 넣기</b></p>')
                url = gr.Textbox(label="유튜브 주소", placeholder="https://www.youtube.com/watch?v=…")
                file = gr.Audio(label="또는 내 음원 가져오기 (파일이 있으면 우선)", type="filepath", sources=["upload"])
            with gr.Column(elem_classes="card"):
                gr.HTML('<p class="step">STEP 2<b>남길 파트</b></p><p class="hint">켜진 파트만 남아요. 기본값은 메인 보컬만 뺀 MR · 전부 켜면 원곡 키만 조절</p>')
                keep = gr.CheckboxGroup(list(STEMS), value=[k for k in STEMS if k != "메인 보컬"], show_label=False, elem_id="parts")
            with gr.Column(elem_classes="card"):
                gr.HTML('<p class="step">STEP 3<b>키 조절</b></p>')
                semitones = gr.State(0)
                with gr.Row(elem_id="keyrow"):
                    down = gr.Button("−", scale=0, min_width=72)
                    view = gr.HTML(key_view(0), elem_id="keyval")
                    up = gr.Button("+", scale=0, min_width=72)
        with gr.Column(scale=2):
            with gr.Column(elem_classes="card"):
                gr.HTML('<p class="step">STEP 4<b>미리듣기</b></p><p class="hint">파트·키를 바꾸면 자동으로 다시 만들어져요</p>')
                listen = gr.Button("▶  미리듣기", elem_id="listen")
                player = gr.Audio(show_label=False, type="filepath", interactive=False, elem_id="player")
            with gr.Column(elem_classes="card"):
                gr.HTML('<p class="step">STEP 5<b>만들기</b></p>')
                fmt = gr.Radio(["mp3", "wav"], value="mp3", label="형식")
                make = gr.Button("⬇  만들기 (내보내기)", elem_id="make")
                dl = gr.File(label="다운로드", visible=False)

    args = [url, file, keep, semitones]
    # 분리·렌더링은 GPU 하나를 쓰므로 모든 작업을 한 줄로 세움 (같은 곡을 동시에 분리하지 않게)
    job = dict(concurrency_id="render", concurrency_limit=1)
    listen.click(preview, args, player, **job)
    keep.change(auto_preview, args, player, trigger_mode="always_last", **job)
    for btn, d in ((down, -1), (up, 1)):
        btn.click(lambda v, d=d: max(-5, min(5, v + d)), semitones, semitones)
    semitones.change(key_view, semitones, view).then(auto_preview, args, player, trigger_mode="always_last", **job)
    make.click(export, [*args, fmt], dl, **job).success(lambda: gr.File(visible=True), None, dl)

if __name__ == "__main__":
    demo.launch(inbrowser=True, theme=THEME, css=CSS, js=DARK)
