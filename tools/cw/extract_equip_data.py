"""离线抽取 cw_shots 全屏图 → 每件装备「效果正文 + 合成配方」(数据银行权威,图鉴单源)。

== 作用 ==
装备图鉴采集 op(harvest_equip_codex)存了每件装备的整屏截图到 ``.debug/temp/cw_shots/<tier>/<名>.png``,
含右侧详情面板的完整效果正文 + 合成公式。本脚本离线 OCR 这些截图,抽出结构化数据,
供①校验 docs equipment.md(米游社版)②补合成公式(文档无逐件配方)③扩充 cw_equipment.py 全量注册表。

== 前提 ==
- cw_shots 已由 harvest_equip_codex op 采好(经 run_operation,Session 1)。
- 本脚本在 Session 0 跑 OK —— 只用 SrContext.init() 加载 OCR 模型,不碰游戏窗口
  (controller 在 Session 0 找不到窗口,但 init 容错,OCR 模型照常加载)。

== 用法 ==
    uv run python tools/cw/extract_equip_data.py
    → 输出 .debug/temp/cw_equip_data.json ({名: {tier, effect[], formula[]}})
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

# 右侧详情面板区域(1080p 游戏坐标;图标在 1443-1541/125-223,本脚本裁图标以下的正文)
EFFECT_REGION = (1430, 240, 1900, 560)    # 效果正文(属性数值 + 效果描述;简易只基础属性)
FORMULA_REGION = (1430, 790, 1900, 960)   # 合成公式(组件名;简易显示可合成的进阶)


def imread_cn(p: Path) -> np.ndarray:
    return cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR)



def _recipe_from_icons(img: np.ndarray) -> list[str] | None:
    """进阶详情配方区 icon+icon → 组件名(TM 反查 cw_equip 模板库;方案 b 图鉴单源)。

    icon 约 66-73px(Canny 外框),模板 98px 缩放匹配;crop 加 BORDER_REPLICATE 防浮点边界
    (int(k*98)==crop 宽时 >= 判定全 skip 的坑,2026-08-16 实测)。
    """
    import cv2  # noqa: F811 (函数内引用顶层 cv2)

    rg = cv2.cvtColor(img[790:960, 1430:1900], cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(rg, 40, 120)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if 40 <= w <= 90 and 40 <= h <= 90 and abs(w - h) <= 15:
            boxes.append((x, y, w, h))
    boxes.sort(key=lambda b: (b[0] // 20, b[1] // 20, -(b[2] * b[3])))
    kept: list[tuple[int, int, int, int]] = []
    for b in boxes:
        if not any(abs(b[0] - k[0]) < 10 and abs(b[1] - k[1]) < 10 for k in kept):
            kept.append(b)
    kept.sort()
    if len(kept) < 2:
        return None
    grays = {}
    for png in sorted((REPO / "assets/template/cw_equip").glob("*.png")):
        t = cv2.imdecode(np.fromfile(str(png), np.uint8), cv2.IMREAD_GRAYSCALE)
        if t is not None:
            grays[png.stem] = t
    comps: list[str] = []
    for x, y, w, h in kept[:2]:
        crop = rg[y + 4:y + h - 4, x + 4:x + w - 4]
        if crop.size == 0:
            comps.append("")
            continue
        crop2 = cv2.copyMakeBorder(crop, 4, 4, 4, 4, cv2.BORDER_REPLICATE)
        best = ("", 0.0)
        for name, t in grays.items():
            th, tw = t.shape[:2]
            k = min(crop.shape[0] / th, crop.shape[1] / tw, 0.95)
            nw, nh = int(tw * k), int(th * k)
            if nw < 12 or nh < 12:
                continue
            tt = cv2.resize(t, (nw, nh), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(crop2, tt, cv2.TM_CCOEFF_NORMED)
            mx = float(res.max())
            if mx > best[1]:
                best = (name, mx)
        comps.append(best[0])
    return comps if all(comps) else None


def main() -> None:
    from sr_od.context.sr_context import SrContext
    ctx = SrContext()
    ctx.init()  # 加载 OCR 模型(controller 在 Session 0 找不到窗口,容错跳过,不影响 OCR)
    ocr = ctx.ocr_service

    def ocr_region(img: np.ndarray, reg: tuple[int, int, int, int]) -> list[str]:
        x0, y0, x1, y1 = reg
        crop = img[y0:y1, x0:x1]
        res = ocr.get_ocr_result_list(image=crop, crop_first=False)
        return [r.data.strip() for r in res if r.data and r.data.strip()]

    shots_dir = REPO / ".debug/temp/cw_shots"
    if not shots_dir.exists():
        print(f"无 cw_shots 目录: {shots_dir}(先跑 harvest_equip_codex op 采图)")
        sys.exit(1)

    out: dict[str, dict] = {}
    for tier_dir in sorted(shots_dir.iterdir()):
        if not tier_dir.is_dir():
            continue
        for shot in sorted(tier_dir.glob("*.png")):
            name = shot.stem
            img = imread_cn(shot)
            if img is None:
                continue
            eff_lines = ocr_region(img, EFFECT_REGION)
            # 简易件效果区带「合成公式」分节标题+可合成进阶名 → 截断(非效果正文)
            if "合成公式" in eff_lines:
                eff_lines = eff_lines[:eff_lines.index("合成公式")]
            out[name] = {
                "tier": tier_dir.name,
                "effect": eff_lines,
                "formula": ocr_region(img, FORMULA_REGION),
                # 进阶配方:详情区配方是 icon+icon 非文字 → 模板 TM 反查(方案 b 图鉴单源)
                "recipe": _recipe_from_icons(img) if tier_dir.name == "进阶" else None,
            }

    out_path = REPO / ".debug/temp/cw_equip_data.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OCR {len(out)} 件装备 -> {out_path}")
    # 抽样打印几条
    for nm in list(out)[:5]:
        print(f"  {nm}: effect={out[nm]['effect'][:2]} formula={out[nm]['formula'][:3]}")


if __name__ == "__main__":
    main()
