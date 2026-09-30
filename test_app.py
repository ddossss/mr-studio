"""모델 없이 믹스/키 조절 로직만 검증: python test_app.py"""
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from app import STEMS, encode, mix

SR = 44100
t = np.arange(6 * SR) / SR


def peak_hz(a):  # 앞뒤 1초(rubberband 과도 구간) 제외 + 창 함수
    a = (a.mean(axis=1) if a.ndim > 1 else a)[SR:-SR]
    return np.argmax(np.abs(np.fft.rfft(a * np.hanning(len(a))))) * SR / len(a)


with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    for name in STEMS.values():  # 메인 보컬 = 1000Hz, 나머지 = 440Hz
        f = 1000 if name == "lead" else 440
        sf.write(d / f"{name}.wav", np.stack([0.3 * np.sin(2 * np.pi * f * t)] * 2, axis=1), SR)

    audio, sr = mix(d, [k for k in STEMS if k != "메인 보컬"])
    assert np.abs(audio).max() <= 1.0, "클리핑"
    assert abs(peak_hz(audio) - 440) < 2, "메인 보컬이 남아 있음"

    sf.write(d / "mix.wav", audio, sr, subtype="FLOAT")
    out, _ = sf.read(encode(d / "mix.wav", 5, d / "out.wav"))
    assert abs(peak_hz(out) - 440 * 2 ** (5 / 12)) < 1, f"키 +5 실패: {peak_hz(out):.1f}Hz"
    assert np.abs(out).max() < 0.99, f"키 조절 후 클리핑: {np.abs(out).max():.3f}"

print("OK")
