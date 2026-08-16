"""货币战争 · 装备图鉴图标采集(可复用工具,版本更新重跑)。

== 方法(用户 2026-08-06,优于网格裁切)==
装备图鉴**选中一件装备** → 右侧详情面板在**固定位置**显示该装备大图标(98×98,
所有 tier 统一,无 V 徽 / 名截断 / 滚动偏移问题)+ 名 / tier / 效果 / 合成公式。
固定图标框经 **CV squares 检测 + 点选验证**(点不同格 → 框位置不变、内容变):
``ICON_BOX = (1443,125,1541,223)``,跨 tab / 选中内容不变(同一图鉴画面布局)。

== 采集流程(MCP 驱动;本脚本只做固定框裁切,点击由 MCP 完成)==
1. 进数据银行 → 装备图鉴。逐格 ``click_game`` 选中 → ``capture_game_screen`` 截图
   → ``analyze_screen``(OCR 取名 / tier / 合成公式)→ 本脚本裁固定框存 ``<名>.png``。
2. tab 内滚屏(大距离 ``drag`` y900→200 翻页)后继续逐格,直到无新名。
3. 切下一个分类 tab,重复(右侧框位置不变,无需重定)。

== 用法 ==
    # 单件:截图 + 规范名
    uv run python harvest_equip_icons.py <截图.png> <装备名>
    # 批量:名 截图 成对
    uv run python harvest_equip_icons.py 轮滑鞋 s1.png 折叠小刀 s2.png ...
    # 版本更新 / 校验:重新检测右侧图标框(CV squares),看是否漂移
    uv run python harvest_equip_icons.py --detect-box <截图.png>

== 为什么固定框优于网格裁切 ==
- 网格裁切:每图重检格 → 格位置漂移;升级 tier 有 V 徽(右下角)需 --v-ext;名截断;
  滚动后行 y 变需 --y-offset。问题多。
- 固定框:右侧详情面板图标位置由画面布局决定,与 tab / tier / 滚动无关 → 一框通吃,
  图标还更大更干净(细白边 + 居中 art,无角标)。合成公式等正文也都在右侧固定区,
  一次 OCR 全拿到。
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "assets/template/currency_war/equip_legacy"
# 右侧详情面板「选中装备图标」固定框(CV squares 检测 + 点选验证,2026-08-06 简易 tab)。
# 跨 tab / 选中内容不变;版本更新画面布局变了 → 跑 --detect-box 重测后更新此常量。
ICON_BOX = (1443, 125, 1541, 223)  # (x0, y0, x1, y1),98×98
# 检测用:右侧面板顶部图标所在大致区(缩小搜索范围,滤假阳)
DETECT_X0, DETECT_X1, DETECT_Y0, DETECT_Y1 = 1380, 1600, 80, 280


def save_png(img: np.ndarray, path: Path) -> None:
    """中文路径安全存图(cv2.imwrite 在 Windows 中文路径挂 → imencode+tofile)。"""
    ok, buf = cv2.imencode(".png", img)
    assert ok, f"imencode 失败: {path}"
    buf.tofile(str(path))


def detect_icon_box(shot: np.ndarray) -> tuple[int, int, int, int] | None:
    """CV squares 检测右侧详情面板的选中装备图标框(多阈值扫 4 顶点矩形)。

    用于版本更新后校验固定框是否漂移;正常裁切直接用 ICON_BOX 常量。
    """
    reg = shot[DETECT_Y0:DETECT_Y1, DETECT_X0:DETECT_X1]
    gray = cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY)
    boxes = []
    for thr in range(40, 220, 20):
        for inv in (False, True):
            _, bw = cv2.threshold(gray, thr, 255, cv2.THRESH_BINARY if not inv else cv2.THRESH_BINARY_INV)
            bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
            cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                x, y, w, h = cv2.boundingRect(c)
                if 3000 < w * h < 30000 and 0.7 < w / h < 1.4:
                    boxes.append((x + DETECT_X0, y + DETECT_Y0, x + DETECT_X0 + w, y + DETECT_Y0 + h))
    # 去重(IoU<0.3 合并)
    uniq: list[tuple[int, int, int, int]] = []
    for b in boxes:
        if all(_iou(b, u) < 0.3 for u in uniq):
            uniq.append(b)
    # 取最大(图标框是面板顶部最显眼的方框)
    return max(uniq, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])) if uniq else None


def _iou(a, b) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + 1e-6)


def crop_icon(shot_path: str, name: str) -> tuple[int, int]:
    """裁固定框 ICON_BOX → 存 <name>.png;返回 (w, h)。"""
    shot = cv2.imread(shot_path)
    assert shot is not None, f"读图失败: {shot_path}"
    x0, y0, x1, y1 = ICON_BOX
    crop = shot[y0:y1, x0:x1]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    save_png(crop, OUT_DIR / f"{name}.png")
    return crop.shape[1], crop.shape[0]


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    # --detect-box:校验 / 重测固定框
    if args[0] == "--detect-box":
        shot = cv2.imread(args[1])
        assert shot is not None, f"读图失败: {args[1]}"
        box = detect_icon_box(shot)
        annot = shot.copy()
        if box:
            cv2.rectangle(annot, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
            print(f"检测到图标框: {box}  ({box[2]-box[0]}×{box[3]-box[1]})")
            print(f"当前常量 ICON_BOX = {ICON_BOX}")
            print(f"漂移: {'否(一致)' if box == ICON_BOX else '是 → 更新 ICON_BOX 常量'}")
        else:
            print("未检测到图标框(检查 DETECT 区 / 阈值)")
        save_png(annot, REPO / ".debug/temp/currency_war/box_detect.png")
        print("标注 → .debug/temp/currency_war/box_detect.png")
        return

    # 默认:裁固定框(单件 或 名×截图 成对)
    pairs = args
    assert len(pairs) % 2 == 0, "参数需「名 截图」成对"
    for i in range(0, len(pairs), 2):
        name, shot = pairs[i], pairs[i + 1]
        w, h = crop_icon(shot, name)
        print(f"裁 {name} → {OUT_DIR / f'{name}.png'}  ({w}×{h})")
    print(f"共 {len(pairs) // 2} 图标 → {OUT_DIR}")


if __name__ == "__main__":
    main()
