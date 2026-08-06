"""货币战争 · 装备图鉴图标采集(CV 形状检测 → 紧贴裁切,可复用工具)。

游戏版本更新装备后,重跑本脚本自动补采/更新图标库。

== 采集流程(人机协作:MCP 驱动滚动/截图/OCR + 本脚本裁切)==
1. 进数据银行 → 装备图鉴(从备战右上角「数据银行」;非破坏性 overlay,对局保留)。
2. 每页(MCP):
   a. ``analyze_screen`` 读当前可见装备名 + 各行名 top-y(reading order:行内左→右,行间上→下)。
      **只取图标完整可见的行**(顶/底行图标若被面板裁切 → 名在但图标残,跳过该行)。
   b. ``capture_game_screen`` 截当前页 → 本地 png。
   c. 大距离快拖(``drag`` y900→200 duration 0.25)翻下页(约 3 行/次),sleep 1.2s。
   d. 重复到 ``analyze`` 无新名 = 采全(125/155 已解锁;锁定项暗,跳过)。
3. 每页跑本脚本(用法见下)。

== 用法 ==
    uv run python tools/cw/harvest_equip_icons.py <截图.png> "<r1的7名|r2的7名>" --row-ys <r1名topY,r2名topY> [--out <目录>] [--page <N>]
    例:
    uv run python tools/cw/harvest_equip_icons.py .debug/.../xxx.png \
        "轮滑鞋,折叠小刀,...|光能电池,..." --row-ys 425,659,891

== 方法(od-dev-ui-region-detect §形状轮廓法 squares + 位置对齐)==
图标 = 紫色边框方块(程序绘制几何形)→ CV 形状检测判几何不判颜色:
1. 灰度多阈值扫描(BINARY/INV)→ 每图标在某层成干净 4 顶点矩形(亮紫边框成环,内部深色是洞 →
   ``drawContours FILLED`` 填实再判)。``approxPolyDP`` 4 顶点凸 + 面积/长宽比 + IoU 去重。
2. **召回 ~50%**(图标内容差异大)但检出覆盖全 7 列 → **聚类出列中心 + 尺寸**。
3. **位置对齐(非索引)**:OCR 名 top-y(可靠)+ CV 校准偏移(图标中心 = 名 top + offset;
   offset 从检出图标中心 vs 最近名 y 中位校准)→ 图标 y。**列 x 用 CV 列中心(非名字中心 ——
   名字长短不一偏心)**。顶/底行图标越出面坂可见区 → 自动跳过(避免裁残 + 索引错位)。
   ⚠️ 别按"检测行索引 ↔ 名行索引"对齐:滚动后顶行图标被裁切→CV 漏检→索引整行错位贴错标签。

输出:<out>/<名>.png(跨页同名覆盖=去重;默认 assets/template/cw_equip/)+ <out>/_debug/annot·montage。
"""
from __future__ import annotations

import argparse
from pathlib import Path
from statistics import median

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
# 装备图鉴列表面板区(shot 全图坐标;放宽 Y 覆盖整个面板,适配任意滚动位置)
GRID_X0, GRID_Y0, GRID_X1, GRID_Y1 = 30, 230, 1270, 970
# 图标"完整可见"的 y 范围(超出=被面板顶/底裁切,跳过)
ICON_VISIBLE_TOP, ICON_VISIBLE_BOT = 240, 960

# ===== CV 确立的网格常量(2026-08-06 全部视图 page-1 检测 + vision 验证 21/21 干净;网格固定,跨分类 tab / 滚动不变)=====
# 7 列中心 x(图标紫框方块中心,非名字中心)、图标 size、图标中心相对名 top 的偏移。
# ⚠️ 版本更新若改网格 → 跑 ``--calibrate``(CV squares 检测)重确立(见 detect_squares)。
COLS_CV: list[int] = [130, 306, 482, 656, 832, 1006, 1176]
HALF_CV: int = 46            # size 92 / 2
OFFSET_CV: int = -78         # icon 中心 = 名 top + OFFSET_CV

AREA_MIN, AREA_MAX = 5000, 18000
ASPECT_LO, ASPECT_HI = 0.65, 1.5
CLOSE_KERN = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))


def save_png(img, path: Path) -> None:
    """中文路径安全存图(cv2.imwrite 在 Windows 中文路径会挂/损坏文件名 → imencode+tofile)。"""
    ok, buf = cv2.imencode(".png", img)
    assert ok, f"imencode 失败: {path}"
    buf.tofile(str(path))


def _iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    return inter / ((ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter + 1e-9)


def _collect(bw):
    closed = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, CLOSE_KERN)
    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(closed)
    cv2.drawContours(filled, cnts, -1, 255, cv2.FILLED)
    cnts2, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cnts2:
        peri = cv2.arcLength(c, True)
        if peri < 20:
            continue
        ap = cv2.approxPolyDP(c, 0.05 * peri, True)
        if len(ap) != 4 or not cv2.isContourConvex(ap):
            continue
        x, y, w, h = cv2.boundingRect(ap)
        if AREA_MIN <= w * h <= AREA_MAX and ASPECT_LO <= w / h <= ASPECT_HI:
            out.append((x, y, x + w, y + h))
    return out


def detect_squares(gray):
    boxes = []
    for t in range(20, 240, 4):
        for mode in (cv2.THRESH_BINARY, cv2.THRESH_BINARY_INV):
            _, bw = cv2.threshold(gray, t, 255, mode)
            for b in _collect(bw):
                if all(_iou(b, x) < 0.3 for x in boxes):
                    boxes.append(b)
    return boxes


def cluster(vals, gap):
    vals = sorted(vals)
    groups = [[vals[0]]]
    for v in vals[1:]:
        if v - groups[-1][-1] <= gap:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [int(np.mean(g)) for g in groups]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shot", help="装备图鉴截图 png")
    ap.add_argument("names", help='21 名,行内逗号、行间 | 分隔(reading order)')
    ap.add_argument("--row-ys", required=True, help="各行名 top-y(OCR),逗号分隔,行数需与 names 行数一致")
    ap.add_argument("--out", default="assets/template/cw_equip")
    ap.add_argument("--page", default="1")
    ap.add_argument("--half", type=int, default=HALF_CV, help="裁切半边(基型 tier=46 无V;升级 tier=58 含V 徽)")
    ap.add_argument("--calibrate", action="store_true", help="不裁切,只跑 CV 检测打印列中心/size,用于版本更新后核对常量")
    args = ap.parse_args()

    shot = cv2.imread(args.shot)
    assert shot is not None, f"读图失败: {args.shot}"
    grid = shot[GRID_Y0:GRID_Y1, GRID_X0:GRID_X1]
    gray = cv2.cvtColor(grid, cv2.COLOR_BGR2GRAY)
    if args.calibrate:
        boxes = detect_squares(gray)
        cxs = cluster([round((b[0] + b[2]) / 2) + GRID_X0 for b in boxes], 25)
        size = int(median([b[2] - b[0] for b in boxes])) if boxes else 92
        print(f"--calibrate: 检出 {len(boxes)} 方块 → 列中心 {cxs}  size={size}")
        print(f"  对照常量 COLS_CV={COLS_CV} HALF_CV={HALF_CV}(检测 size/2={size // 2});")
        print("  不符 = 版本改了网格 → 更新常量后重跑。偏移(icon center vs 名 top)手测。")
        return

    cols_full, half, offset = COLS_CV, args.half, OFFSET_CV
    print(f"用 CV 常量 cols={cols_full} half={half} offset={offset}(网格变则 --calibrate 重确立)")

    row_ys = [int(y) for y in args.row_ys.split(",")]
    rows = [r.split(",") for r in args.names.split("|")]
    assert len(row_ys) == len(rows), f"--row-ys 行数 {len(row_ys)} ≠ names 行数 {len(rows)}"

    out_dir = REPO / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    dbg = out_dir / "_debug"
    dbg.mkdir(exist_ok=True)
    annot = shot.copy()
    saved = 0
    for ri, ry in enumerate(row_ys):
        icon_cy = ry + offset
        if not (ICON_VISIBLE_TOP + half <= icon_cy <= ICON_VISIBLE_BOT - half):
            print(f"  跳过行 {ri}(名 y={ry}→图标 y={icon_cy} 被面板裁切,图标不完整)")
            continue
        for ci, cx in enumerate(cols_full):
            if ci >= len(rows[ri]):
                continue
            nm = rows[ri][ci].strip()
            crop = shot[icon_cy - half:icon_cy + half, cx - half:cx + half]
            save_png(crop, out_dir / f"{nm}.png")
            saved += 1
            cv2.rectangle(annot, (cx - half, icon_cy - half), (cx + half, icon_cy + half), (0, 255, 0), 2)
            cv2.putText(annot, nm, (cx - half, icon_cy - half - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    save_png(annot, dbg / f"annot_p{args.page}.png")
    print(f"裁 {saved} 图标 → {out_dir} (跳过的行图标不完整;+ _debug/annot_p{args.page}.png)")


if __name__ == "__main__":
    main()
