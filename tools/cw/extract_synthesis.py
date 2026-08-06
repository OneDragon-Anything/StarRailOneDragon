"""OCR 简易装备 cw_shots → 提取「合成公式」(每简易 → 可合成的进阶列表)→ 派生 进阶=(简易_a,简易_b) 图谱。

D-73「cw_equipment 建基础件×2→进阶配方」。数据银行图鉴:每件简易的合成公式列出它能合成的
进阶(= 含它作组件的所有进阶)。每件进阶 = 恰好 2 件简易的组件 → 进阶名出现在那 2 件简易的
列表交集里。本脚本 OCR 7-8 件简易的合成区 → 派生 EQUIP_RECIPES: dict[进阶名, (简易_a, 简易_b)]。

== 用法 ==
    uv run python tools/cw/extract_synthesis.py
    → 打印每简易列表 + 派生进阶配方;落 .debug/temp/equip_recipes.json。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

# 简易右侧合成公式区(进阶名列表;y~370-880;x~1655)。避开 stat(249)/合成公式 label(302)。
SIMPLE_FORMULA_REGION = (1430, 360, 1900, 890)


def imread_cn(p: Path) -> np.ndarray:
    return cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR)


def main() -> None:
    from sr_od.context.sr_context import SrContext
    ctx = SrContext()
    ctx.init()  # Session 0 只为 OCR 模型(controller 找不到窗口,容错)
    ocr = ctx.ocr_service

    simple_dir = REPO / ".debug/temp/cw_shots/简易"
    if not simple_dir.exists():
        print(f"无 {simple_dir}(先跑 harvest_equip_codex op 采简易)")
        sys.exit(1)

    lists: dict[str, list[str]] = {}
    for shot in sorted(simple_dir.glob("*.png")):
        img = imread_cn(shot)
        x0, y0, x1, y1 = SIMPLE_FORMULA_REGION
        crop = img[y0:y1, x0:x1]
        res = ocr.get_ocr_result_list(image=crop, crop_first=False)
        names = [r.data.strip() for r in res if r.data and r.w > 20]
        lists[shot.stem] = names

    # 派生:进阶 = 恰好出现在 2 件简易列表里的名字(那 2 件即组件)
    from collections import defaultdict
    adv_to_simples: dict[str, list[str]] = defaultdict(list)
    for simple, advs in lists.items():
        for adv in advs:
            adv_to_simples[adv].append(simple)

    recipes: dict[str, list[str]] = {}
    ambiguous: dict[str, list[str]] = {}
    for adv, simples in adv_to_simples.items():
        if len(simples) == 2:
            recipes[adv] = simples
        else:
            ambiguous[adv] = simples  # 非 2(0/1/3+)→ OCR 漏或非合成

    out = {"simple_lists": lists, "recipes": recipes, "ambiguous": ambiguous}
    out_path = REPO / ".debug/temp/equip_recipes.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"简易 {len(lists)} 件,派生 {len(recipes)} 个进阶配方,模糊 {len(ambiguous)} 个")
    print("\n=== 简易 → 进阶列表 ===")
    for s, advs in lists.items():
        print(f"  {s}: {advs}")
    print(f"\n=== 进阶配方(2-组件)→ {out_path} ===")
    for adv, (a, b) in sorted(recipes.items()):
        print(f"  {adv} = {a} + {b}")
    if ambiguous:
        print("\n=== 模糊(非 2 组件,需查)===")
        for adv, ss in ambiguous.items():
            print(f"  {adv}: {ss}")


if __name__ == "__main__":
    main()
