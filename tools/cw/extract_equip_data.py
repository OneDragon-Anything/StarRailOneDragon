"""离线 OCR cw_shots 全屏图 → 提取每件装备的「效果正文 + 合成公式」(数据银行权威)。

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
            out[name] = {
                "tier": tier_dir.name,
                "effect": ocr_region(img, EFFECT_REGION),
                "formula": ocr_region(img, FORMULA_REGION),
            }

    out_path = REPO / ".debug/temp/cw_equip_data.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OCR {len(out)} 件装备 -> {out_path}")
    # 抽样打印几条
    for nm in list(out)[:5]:
        print(f"  {nm}: effect={out[nm]['effect'][:2]} formula={out[nm]['formula'][:3]}")


if __name__ == "__main__":
    main()
