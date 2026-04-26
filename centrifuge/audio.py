"""
Audio feature extraction using librosa.

Produces a JSON-serialisable dict that can be injected as context
into the Sound Design Expert prompt.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_features(path: Path) -> dict[str, Any]:
    """
    Analyse an audio file and return a feature dict.

    Returned keys:
      duration_s, sample_rate, rms_db, peak_db,
      spectral_centroid_hz, spectral_bandwidth_hz,
      spectral_rolloff_hz, zero_crossing_rate,
      attack_time_ms, onset_count,
      pitch_hz (median fundamental), harmonicity,
      mfcc (list of 13 mean values),
      brightness (0-1 normalized centroid),
      is_percussive (bool heuristic)
    """
    import librosa
    import numpy as np
    import soundfile as sf

    p = Path(path)
    y, sr = librosa.load(str(p), sr=None, mono=True)

    duration = float(librosa.get_duration(y=y, sr=sr))
    rms = float(np.sqrt(np.mean(y**2)))
    peak = float(np.max(np.abs(y)))
    rms_db = float(librosa.amplitude_to_db(rms)) if rms > 0 else -120.0
    peak_db = float(librosa.amplitude_to_db(peak)) if peak > 0 else -120.0

    # Spectral features
    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    centroid = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
    bandwidth = librosa.feature.spectral_bandwidth(S=S, sr=sr)[0]
    rolloff = librosa.feature.spectral_rolloff(S=S, sr=sr)[0]
    zcr = librosa.feature.zero_crossing_rate(y)[0]

    centroid_hz = float(np.median(centroid))
    bandwidth_hz = float(np.median(bandwidth))
    rolloff_hz = float(np.median(rolloff))
    zcr_mean = float(np.mean(zcr))

    # Normalize centroid brightness to 0-1 (nyquist = 1)
    nyquist = sr / 2
    brightness = float(min(centroid_hz / nyquist, 1.0))

    # Onset / attack detection
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
    onset_count = int(len(onset_frames))
    if len(onset_frames) > 0:
        onset_time_s = float(librosa.frames_to_time(onset_frames[0], sr=sr))
        # Rough attack: rise from onset to peak within the first 500 ms
        start_idx = librosa.frames_to_samples(onset_frames[0])
        window = y[start_idx: start_idx + int(sr * 0.5)]
        if len(window) > 0:
            peak_idx = int(np.argmax(np.abs(window)))
            attack_time_ms = float(peak_idx / sr * 1000)
        else:
            attack_time_ms = 0.0
    else:
        onset_time_s = 0.0
        attack_time_ms = 0.0

    # Fundamental pitch (median)
    f0, voiced, _ = librosa.pyin(
        y, fmin=float(librosa.note_to_hz("C1")), fmax=float(librosa.note_to_hz("C8"))
    )
    voiced_f0 = f0[voiced] if voiced is not None else np.array([])
    pitch_hz = float(np.median(voiced_f0)) if len(voiced_f0) > 0 else 0.0

    # Harmonicity: ratio of energy in harmonic partials vs noise
    if pitch_hz > 0:
        y_harm, y_perc = librosa.effects.hpss(y)
        harm_energy = float(np.mean(y_harm**2))
        perc_energy = float(np.mean(y_perc**2))
        total = harm_energy + perc_energy
        harmonicity = float(harm_energy / total) if total > 0 else 0.0
    else:
        harmonicity = 0.0

    # MFCC — 13 coefficients, mean per coefficient
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_means = [round(float(v), 2) for v in np.mean(mfcc, axis=1)]

    # Percussive heuristic: short, high ZCR, fast attack
    is_percussive = bool(attack_time_ms < 20 and zcr_mean > 0.1 and duration < 2.0)

    return {
        "duration_s": round(duration, 3),
        "sample_rate": sr,
        "rms_db": round(rms_db, 1),
        "peak_db": round(peak_db, 1),
        "spectral_centroid_hz": round(centroid_hz, 1),
        "spectral_bandwidth_hz": round(bandwidth_hz, 1),
        "spectral_rolloff_hz": round(rolloff_hz, 1),
        "zero_crossing_rate": round(zcr_mean, 4),
        "attack_time_ms": round(attack_time_ms, 1),
        "onset_count": onset_count,
        "pitch_hz": round(pitch_hz, 1),
        "harmonicity": round(harmonicity, 3),
        "mfcc": mfcc_means,
        "brightness": round(brightness, 3),
        "is_percussive": is_percussive,
    }
