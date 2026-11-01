#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: speakers.py
ROLE: Engine
DESCRIPTION:
Finds the second speaker of an interview (usually the interviewer, often off-mic) sentence by
sentence. Two clues are combined: how quiet the sentence is compared with the main speaker, and
how far its voice is from the main voice (CAM++ speaker embeddings from 3D-Speaker, Apache-2.0,
run with onnxruntime; ~30 MB model downloaded on first use). No PyTorch.
"""

import os
import subprocess
import sys
import urllib.request

import numpy as np

MODEL_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/"
             "3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx")
MODEL_FILE = "campplus_sv_en_voxceleb_16k.onnx"
SR = 16000
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


HF_REPO = "csukuangfj/speaker-embedding-models"
HF_FILE = "3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx"


def ensure_model(models_dir, progress=None):
    """Path of the speaker model, downloaded once into models_dir/speakers/.
    Tries Hugging Face (same client as the Whisper models), then GitHub with certifi's
    certificates, then curl (system certificates): some Python installs have no CA bundle."""
    folder = os.path.join(models_dir, "speakers")
    path = os.path.join(folder, MODEL_FILE)
    if os.path.isfile(path) and os.path.getsize(path) > 1_000_000:
        return path
    os.makedirs(folder, exist_ok=True)
    tmp = path + ".part"
    errors = []
    try:
        from huggingface_hub import hf_hub_download
        got = hf_hub_download(repo_id=HF_REPO, filename=HF_FILE, local_dir=folder)
        os.replace(got, path)
        return path
    except Exception as e:
        errors.append(f"huggingface: {e}")
    try:
        import ssl
        ctx = None
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            pass
        with urllib.request.urlopen(MODEL_URL, timeout=60, context=ctx) as resp, open(tmp, "wb") as f:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done / total)
        os.replace(tmp, path)
        return path
    except Exception as e:
        errors.append(f"github: {e}")
    try:
        subprocess.run(["curl", "-sfL", "-o", tmp, MODEL_URL], check=True, creationflags=_NO_WINDOW, timeout=300)
        os.replace(tmp, path)
        return path
    except Exception as e:
        errors.append(f"curl: {e}")
    raise RuntimeError("speaker model download failed: " + " | ".join(errors))


def load_audio(ffmpeg, path):
    """Any audio/video file -> mono float32 at 16 kHz (through ffmpeg)."""
    cmd = [ffmpeg or "ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    out = subprocess.run(cmd, capture_output=True, creationflags=_NO_WINDOW, check=True).stdout
    return np.frombuffer(out, dtype="<i2").astype(np.float32) / 32768.0


def fbank(x, n_mels=80):
    """Kaldi-style log mel filter bank (25 ms / 10 ms, povey window, pre-emphasis 0.97), mean-normalised."""
    x = x.astype(np.float64) * 32768.0
    flen, shift, nfft = 400, 160, 512
    if len(x) < flen:
        x = np.pad(x, (0, flen - len(x)))
    n = 1 + (len(x) - flen) // shift
    idx = np.arange(flen)[None, :] + shift * np.arange(n)[:, None]
    fr = x[idx]
    fr = fr - fr.mean(axis=1, keepdims=True)
    fr = np.concatenate([fr[:, :1] - 0.97 * fr[:, :1], fr[:, 1:] - 0.97 * fr[:, :-1]], axis=1)
    win = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(flen) / (flen - 1))) ** 0.85
    spec = np.abs(np.fft.rfft(fr * win, nfft)) ** 2
    mel = lambda f: 1127.0 * np.log(1 + f / 700.0)
    pts = np.linspace(mel(20.0), mel(SR / 2), n_mels + 2)
    fbins = mel(np.arange(nfft // 2 + 1) * SR / nfft)
    W = np.zeros((n_mels, nfft // 2 + 1))
    for m in range(n_mels):
        lo, c, hi = pts[m], pts[m + 1], pts[m + 2]
        W[m] = np.maximum(0, np.minimum((fbins - lo) / (c - lo), (hi - fbins) / (hi - c)))
    feats = np.log(np.maximum(spec @ W.T, np.finfo(float).eps))
    return (feats - feats.mean(axis=0)).astype(np.float32)


def sentences(words):
    """Group spoken words into sentences: [(first index, last index), ...]."""
    out, first = [], None
    for i, w in enumerate(words):
        if w.get("type") in ("silence", "inaudible") or w.get("is_inaudible") or not (w.get("text") or "").strip():
            continue
        if first is None:
            first = i
        last = i
        if (w.get("text") or "").strip()[-1:] in ".?!" :
            out.append((first, last))
            first = None
    if first is not None:
        out.append((first, last))
    return out


def _robust_z(v):
    med = np.median(v)
    mad = np.median(np.abs(v - med)) * 1.4826 + 1e-9
    return (v - med) / mad


def find_second_speaker(audio, words, model_path, threshold=6.0, cancel=None):
    """Word indices said by the second speaker, plus how many sentences were looked at.
    A sentence counts when it is clearly quieter than the main speaker and/or in a different voice."""
    import onnxruntime as ort
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    sents = sentences(words)
    if len(sents) < 4:
        return [], len(sents)
    levels, embs = [], []
    for a, b in sents:
        if cancel and cancel():
            return [], 0
        t0, t1 = float(words[a].get("start", 0.0)), float(words[b].get("end", 0.0))
        seg = audio[int(max(0.0, t0) * SR):int(t1 * SR)]
        if len(seg) >= 800:
            fr = seg[:len(seg) // 800 * 800].reshape(-1, 800)
            e = np.sqrt((fr ** 2).mean(axis=1) + 1e-12)
            levels.append(20 * np.log10(np.quantile(e, 0.9)))
        else:
            levels.append(-90.0)
        if t1 - t0 >= 0.6:
            pad = audio[int(max(0.0, t0 - 0.05) * SR):int((t1 + 0.05) * SR)]
            v = sess.run(None, {"x": fbank(pad)[None]})[0][0]
            embs.append(v / (np.linalg.norm(v) + 1e-9))
        else:
            embs.append(None)
    E = np.stack([e for e in embs if e is not None])
    cen = E.mean(axis=0)
    cen /= np.linalg.norm(cen)
    for _ in range(3):  # the main voice: centroid of the 70% most typical sentences
        s = E @ cen
        cen = E[s >= np.quantile(s, 0.3)].mean(axis=0)
        cen /= np.linalg.norm(cen)
    sims = np.array([float(e @ cen) if e is not None else np.nan for e in embs])
    sims = np.where(np.isnan(sims), np.nanmedian(sims), sims)
    score = -_robust_z(np.array(levels)) - _robust_z(sims)
    picked = []
    for (a, b), sc in zip(sents, score):
        if sc > threshold:
            picked.extend(i for i in range(a, b + 1)
                          if not (words[i].get("type") in ("silence", "inaudible") or words[i].get("is_inaudible")))
    return picked, len(sents)
