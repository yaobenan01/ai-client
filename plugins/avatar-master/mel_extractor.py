#!/usr/bin/env python3
"""纯 NumPy 高性能 80 维 Mel 频谱特征提取器（免装庞大 librosa/scipy，纯离线极速运行）。

针对 Wav2Lip 唇形同步标准：
- 采样率: 16000 Hz
- FFT 窗口大小: 800 (50ms)
- 帧移 Hop: 200 (12.5ms, 即每秒 80 帧 Mel 频谱)
- 频带数: 80 维 Log-Mel
- 频率范围: 55 Hz ~ 7600 Hz
"""
from __future__ import annotations

import math
from pathlib import Path
import numpy as np


def hz_to_mel(hz: float | np.ndarray) -> float | np.ndarray:
    return 2595.0 * np.log10(1.0 + hz / 700.0)


def mel_to_hz(mel: float | np.ndarray) -> float | np.ndarray:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def build_mel_basis(
    sr: int = 16000,
    n_fft: int = 800,
    n_mels: int = 80,
    fmin: float = 55.0,
    fmax: float = 7600.0,
) -> np.ndarray:
    """构建 80 维三角 Mel 滤波器组权重矩阵 [n_mels, 1 + n_fft//2]。"""
    num_bins = 1 + n_fft // 2
    weights = np.zeros((n_mels, num_bins), dtype=np.float32)

    min_mel = hz_to_mel(fmin)
    max_mel = hz_to_mel(fmax)
    mels = np.linspace(min_mel, max_mel, n_mels + 2)
    hz_points = mel_to_hz(mels)

    fft_freqs = np.linspace(0.0, sr / 2.0, num_bins)

    for i in range(n_mels):
        lower = hz_points[i]
        center = hz_points[i + 1]
        upper = hz_points[i + 2]

        # 上升沿
        up_idx = np.where((fft_freqs >= lower) & (fft_freqs <= center))[0]
        if center > lower:
            weights[i, up_idx] = (fft_freqs[up_idx] - lower) / (center - lower)

        # 下降沿
        down_idx = np.where((fft_freqs >= center) & (fft_freqs <= upper))[0]
        if upper > center:
            weights[i, down_idx] = (upper - fft_freqs[down_idx]) / (upper - center)

        # Slaney 面积归一化
        enorm = 2.0 / (upper - lower)
        weights[i, :] *= enorm

    return weights


_CACHED_MEL_BASIS = None


def get_mel_basis() -> np.ndarray:
    global _CACHED_MEL_BASIS
    if _CACHED_MEL_BASIS is None:
        _CACHED_MEL_BASIS = build_mel_basis()
    return _CACHED_MEL_BASIS


def stft_melspectrogram(
    y: np.ndarray,
    sr: int = 16000,
    n_fft: int = 800,
    hop_length: int = 200,
    win_length: int = 800,
    n_mels: int = 80,
) -> np.ndarray:
    """计算短时傅里叶变换并投影到 80 维 Log-Mel 空间。

    返回 shape: [80, T]
    """
    if y.ndim > 1:
        y = np.mean(y, axis=-1)
    y = y.astype(np.float32)

    # 左右反射填充
    pad_len = n_fft // 2
    y_padded = np.pad(y, pad_len, mode="reflect")

    # 分帧
    num_frames = 1 + (len(y_padded) - n_fft) // hop_length
    frames = np.lib.stride_tricks.as_strided(
        y_padded,
        shape=(num_frames, n_fft),
        strides=(y_padded.strides[0] * hop_length, y_padded.strides[0]),
    ).copy()

    # Hann 窗加权
    window = np.hanning(win_length).astype(np.float32)
    frames *= window

    # 实数快速傅里叶变换
    stft_res = np.fft.rfft(frames, n=n_fft, axis=-1)
    mag = np.abs(stft_res).T  # [num_bins, num_frames]

    # Mel 投影
    basis = get_mel_basis()
    mel = np.dot(basis, mag)  # [n_mels, num_frames]

    # 对数动态压缩与归一化
    mel_db = np.log(np.clip(mel, a_min=1e-5, a_max=None))
    return mel_db


def extract_mel_chunks(
    audio_path: str | Path,
    fps: float = 25.0,
    mel_step_size: int = 16,
    silence_thresh: float = 0.006,
) -> tuple[list[np.ndarray], list[float], float]:
    """从 16kHz WAV 音频中提取逐视频帧对齐的 Mel 频谱块与 RMS 能量。

    返回:
    - mel_chunks: 每帧对应的 Mel 张量，shape 为 [1, 80, 16]
    - rms_energies: 每帧对应的有效能量值（用于静音帧快速直通）
    - duration_sec: 音频总时长（秒）
    """
    import wave

    with wave.open(str(audio_path), "rb") as wf:
        sr = wf.getframerate()
        channels = wf.getnchannels()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    # 解析 PCM 16bit
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)

    duration_sec = len(audio) / float(sr)
    total_video_frames = int(math.ceil(duration_sec * fps))

    # 计算全局 Mel 频谱 (shape: [80, T_mel])
    mel = stft_melspectrogram(audio, sr=sr)
    t_mels = mel.shape[1]

    mel_chunks: list[np.ndarray] = []
    rms_energies: list[float] = []

    samples_per_frame = int(sr / fps)

    for i in range(total_video_frames):
        # 计算第 i 个视频帧对应的 Mel 起始时间步 (按 80Hz mel 帧率换算)
        start_idx = int(round(i * (80.0 / fps)))
        end_idx = start_idx + mel_step_size

        if end_idx <= t_mels:
            chunk = mel[:, start_idx:end_idx]
        else:
            # 音频末尾补零/边缘镜像填充
            chunk = np.zeros((80, mel_step_size), dtype=np.float32)
            valid = mel[:, start_idx:t_mels]
            valid_len = valid.shape[1]
            if valid_len > 0:
                chunk[:, :valid_len] = valid
                chunk[:, valid_len:] = valid[:, -1:]
            else:
                chunk[:, :] = -11.51  # np.log(1e-5) 静音底噪值

        # 转换为 Wav2Lip 期望的标准输入格式: [1, 80, 16]
        mel_chunks.append(np.expand_dims(chunk, axis=0))

        # 计算当前视频帧时间窗的 RMS 能量
        start_sample = i * samples_per_frame
        end_sample = min(len(audio), (i + 1) * samples_per_frame)
        if start_sample < len(audio) and end_sample > start_sample:
            seg = audio[start_sample:end_sample]
            rms = float(np.sqrt(np.mean(seg ** 2)))
        else:
            rms = 0.0
        rms_energies.append(rms)

    return mel_chunks, rms_energies, duration_sec


if __name__ == "__main__":
    print("Mel 提取器自检...")
    fake_audio = np.random.randn(16000 * 2).astype(np.float32) * 0.1
    m = stft_melspectrogram(fake_audio)
    print("测试 Mel shape:", m.shape)
    assert m.shape[0] == 80
    print("[OK] Mel 特征提取器数学矩阵校验通过！")
