"""货币战争 备战阶段 CV 检测工具(传统 cv2)。

deploy 的两要素:备战栏角色头像(拖拽源)+ 舞台空槽(拖拽目标)。两者都无文字,
OCR 看不见,用颜色/饱和度 CV 检测,返回 1080p 坐标。

- 备战栏头像:底部一行,饱和度高(角色立绘有色)。
- 舞台空槽:浅青描边 RGB(173,216,230)≈ HSV(97,63,230);被占用后无描边 → 只检测空槽。

运行时纯代码路径用 cv2(不依赖 LLM/vision);vision(GLM-4.5V grounding)用于建档/验证坐标,
见 ``.debug/temp/currency_war/article_01_vision_grounding.md``。检测「全部槽位(含空)」
另见 skill ``od-dev-ui-region-detect`` 的逐列标准差投影法(本文件饱和度法只找有角色的填充槽)。
"""

import cv2
import numpy as np
from cv2.typing import MatLike

# 备战栏头像所在行(y 范围,1080p)—— 排除上方的购买经验面板
BENCH_Y0, BENCH_Y1 = 880, 990
BENCH_X0, BENCH_X1 = 410, 1050  # x>=410 排除左侧「购买经验」面板的硬币/F 图标假阳性
# 舞台槽位所在区
STAGE_Y0, STAGE_Y1 = 300, 680
STAGE_X0, STAGE_X1 = 680, 1200
# 前排/后排分界 y(前排 < 此值)
FRONT_BACK_SPLIT_Y = 510

Point = tuple[int, int]


def detect_bench_avatars(screen: MatLike) -> list[Point]:
    """检测备战栏角色头像中心(从左到右)。返回 1080p (x,y) 列表。"""
    roi = screen[BENCH_Y0:BENCH_Y1, BENCH_X0:BENCH_X1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # 角色立绘饱和度高;背景偏暗/灰
    sat = (hsv[:, :, 1] > 70) & (hsv[:, :, 2] > 60)
    mask = (sat.astype(np.uint8)) * 255
    kern = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kern)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    pts: list[Point] = []
    for c in cnts:
        a = cv2.contourArea(c)
        if not (2000 <= a <= 20000):  # 滤掉小块 + 购买经验大面板
            continue
        M = cv2.moments(c)
        if M["m00"] <= 0:
            continue
        cx = int(M["m10"] / M["m00"]) + BENCH_X0
        cy = int(M["m01"] / M["m00"]) + BENCH_Y0
        pts.append((cx, cy))
    pts.sort(key=lambda p: p[0])
    return pts


def detect_empty_slots(screen: MatLike) -> tuple[list[Point], list[Point]]:
    """检测舞台空槽,返回 (前排列表, 后排列表),均 1080p (x,y)。空槽才有浅青描边。"""
    roi = screen[STAGE_Y0:STAGE_Y1, STAGE_X0:STAGE_X1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([85, 20, 150]), np.array([105, 170, 255]))
    kern = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kern)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    front: list[Point] = []
    back: list[Point] = []
    for c in cnts:
        a = cv2.contourArea(c)
        if not (80 <= a <= 4000):  # 单个槽位描边面积;过大是合并 blob,过小是噪点
            continue
        M = cv2.moments(c)
        if M["m00"] <= 0:
            continue
        cx = int(M["m10"] / M["m00"]) + STAGE_X0
        cy = int(M["m01"] / M["m00"]) + STAGE_Y0
        if cy < (STAGE_Y0 + FRONT_BACK_SPLIT_Y - STAGE_Y0):
            front.append((cx, cy))
        else:
            back.append((cx, cy))
    front.sort(key=lambda p: p[0])
    back.sort(key=lambda p: p[0])
    return front, back


if __name__ == "__main__":
    import os
    import sys

    # 读最新截图(默认)/ 传路径
    scr_dir = r"D:\code\workspace\StarRailOneDragon\.debug\sr_od_mcp\screenshot"
    path = sys.argv[1] if len(sys.argv) > 1 else max(
        os.path.join(scr_dir, f) for f in os.listdir(scr_dir) if f.endswith(".png")
    )
    img = cv2.imread(path)
    print(f"screenshot: {os.path.basename(path)}  size={img.shape[1]}x{img.shape[0]}")
    bench = detect_bench_avatars(img)
    front, back = detect_empty_slots(img)
    print(f"bench avatars ({len(bench)}): {bench}")
    print(f"front empty slots ({len(front)}): {front}")
    print(f"back empty slots ({len(back)}): {back}")
    # 标注保存
    annot = img.copy()
    for p in bench:
        cv2.circle(annot, p, 16, (0, 0, 255), 4)
    for p in front + back:
        cv2.circle(annot, p, 14, (0, 255, 255), 4)
    out = r"D:\code\workspace\StarRailOneDragon\.debug\temp\currency_war\shots\cv_annot_latest.png"
    cv2.imwrite(out, annot)
    print(f"annot -> {out}")
