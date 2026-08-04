"""密集规则网格槽位检测(本 skill 的 CV 实现,可复用)。

用法:
    from detect_grid import detect_grid_row
    centers = detect_grid_row(img, y1=845, y2=979, x1=360, x2=1520, slot_w=113)
    # centers = 每个槽中心的 x 坐标(全图坐标)列表

方法:逐列灰度标准差(槽内有立绘=大,缝隙=小)→ 轻平滑 → median 阈值 →
局部极大 + NMS(限距 slot_w*0.7)→ 一个槽一个峰。内容无关,空槽也能抓。
"""
from __future__ import annotations

import cv2
import numpy as np


def _find_peaks_1d(signal: np.ndarray, slot_w: int) -> list[int]:
    """1D 信号 → 局部极大 + NMS,返回峰 index(限距 slot_w*0.7)。"""
    signal = np.asarray(signal, dtype=float)
    k = max(3, slot_w // 4) | 1  # 轻平滑;重了桥接相邻密集槽
    signal = np.convolve(signal, np.ones(k) / k, mode="same")
    thr = np.median(signal)  # 低阈值,保留空槽微弱峰
    rad = int(slot_w * 0.4)
    cands: list[tuple[int, float]] = []
    for i in range(rad, len(signal) - rad):
        if signal[i] >= signal[i - rad:i + rad + 1].max() and signal[i] > thr:
            cands.append((i, float(signal[i])))
    cands.sort(key=lambda t: -t[1])  # 按高度降序 NMS
    accepted: list[int] = []
    for idx, _v in cands:
        if all(abs(idx - a) > slot_w * 0.7 for a in accepted):
            accepted.append(idx)
    accepted.sort()
    return accepted


def detect_grid_row(
    img: np.ndarray,
    y1: int, y2: int, x1: int, x2: int,
    slot_w: int,
    signal: str = "std",
) -> list[int]:
    """检测一行等距槽位的中心 x 坐标。

    Args:
        img: BGR 截图(1080p 原生,与 screen_info 坐标一致)。
        y1, y2: 槽位的 y 范围(裁行带)。
        x1, x2: 搜索 x 范围(两侧留余量)。
        slot_w: 单槽预估宽度(px)。
        signal: "std"=逐列灰度标准差(默认,内容存在性);"color"=框色存在(需配 HSV,
            本函数未含,自行 inRange 后传 mask 列求和)。
    Returns:
        各槽中心 x(全图坐标)列表,升序。
    """
    band = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
    sig = gray.std(axis=0)
    return [p + x1 for p in _find_peaks_1d(sig, slot_w)]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python detect_grid.py <截图.png> [y1 y2 x1 x2 slot_w]")
        raise SystemExit(0)
    img = cv2.imread(sys.argv[1])
    if img is None:
        raise SystemExit(f"读图失败: {sys.argv[1]}")
    if len(sys.argv) >= 7:
        y1, y2, x1, x2, w = map(int, sys.argv[2:7])
    else:
        # demo 默认值(仅占位;实参请按目标行带传)
        y1, y2, x1, x2, w = 845, 979, 360, 1520, 113
    centers = detect_grid_row(img, y1, y2, x1, x2, w)
    print(f"检测到 {len(centers)} 个槽中心 x: {centers}")
