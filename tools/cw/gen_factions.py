"""货币战争 · 羁绊(traits)数据生成器(官方 traits.json → 注册表数据层 + 明细文档)。

数据源:.debug/temp/currency_war/plaza/trait_detail.json(子代理采集,lineup/index 按羁绊筛,
V4.4 过滤;采集器 .debug/temp/cw_trait_probe_14*.py 版本更新重跑)。

产出:
  1. src/sr_od/application/currency_war/cw_factions_data.py —— TRAIT_TIERS(官方 tiers:
     name → 激活阈值序列)+ TRAIT_EFFECT(官方效果全文)+ TRAIT_ROLES(官方成员名单);
  2. docs/game/currency_war/data/traits/<名>.md —— 每羁绊一档(tiers 逐层/效果/成员)。

分工(同角色域):**数据层生成,判断层手维护** —— cw_factions.FACTIONS 的
category(combat/economy/support)与 note(策略注记)是人判,不在生成范围;
生成器产 TRAIT_* 数据模块供 FACTIONS 对拍校验(tiers 漂移检测)+ 策略层直查官方效果。

用法: uv run python tools/cw/gen_factions.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[2]
SRC_JSON = REPO / ".debug/temp/currency_war/plaza/trait_detail.json"
DATA_PY = REPO / "src/sr_od/application/currency_war/cw_factions_data.py"
DOC_DIR = REPO / "docs/game/currency_war/data/traits"

ISOLATED = {"师徒"}   # 旧赛季遗留(V4.4 无持有者),不生成


def strip_rich(s: str) -> str:
    """去富文本标签。"""
    return re.sub(r"<[^>]+>", "", s).replace("\n", " ").strip()


def main() -> None:
    raw = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    version = raw.get("version", "?")
    traits = [t for t in raw.get("traits", []) if t["name"] not in ISOLATED]
    print(f"traits: {len(traits)}(排除旧赛季 {sorted(ISOLATED)})")

    # ---- 1) 数据模块 ----
    lines = [
        "# 警告:本文件由 tools/cw/gen_factions.py 生成(traits.json V" + version + "),勿手编;版本更新重跑。",
        '"""羁绊官方数据(V' + version + "):tiers(激活阈值)/effect(效果全文)/roles(成员)。",
        "",
        "来源:lineup/index 按羁绊筛采集(V4.4 过滤);采集器与过程见 .debug 工作区。",
        "分工:数据层(本模块)生成;category/note 等人判层在 cw_factions.FACTIONS 手维护。",
        '"""',
        "from __future__ import annotations",
        "",
        "",
        "# {羁绊名: 激活阈值序列(第 N 层需几人)}",
        "TRAIT_TIERS: dict[str, tuple[int, ...]] = {",
    ]
    for t in sorted(traits, key=lambda x: (x.get("trait_type") or 0, x["name"])):
        lt = tuple(int(lr["layer"]) for lr in (t.get("layers") or []))
        lines.append(f"    {t['name']!r}: {lt!r},")
    lines += [
        "}",
        "",
        "",
        "# {羁绊名: 官方效果全文(富文本已清)}",
        "TRAIT_EFFECT: dict[str, str] = {",
    ]
    for t in sorted(traits, key=lambda x: (x.get("trait_type") or 0, x["name"])):
        eff = strip_rich(t.get("effect") or "")
        eff = eff.replace(chr(39), "")
        lines.append(f"    {t['name']!r}: {eff!r},")
    lines += [
        "}",
        "",
        "",
        "# {羁绊名: 官方成员名单(规范名;含隐藏条目变体去重后)}",
        "TRAIT_ROLES: dict[str, tuple[str, ...]] = {",
    ]
    for t in sorted(traits, key=lambda x: (x.get("trait_type") or 0, x["name"])):
        roles = sorted(set(t.get("roles") or []))
        lines.append(f"    {t['name']!r}: {tuple(roles)!r},")
    lines += ["}", "", ""]
    DATA_PY.write_text("\n".join(lines), encoding="utf-8")
    print(f"[data] -> {DATA_PY}")

    # ---- 2) 明细文档 ----
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    for t in traits:
        nm = t["name"]
        lt = [int(lr["layer"]) for lr in (t.get("layers") or [])]
        quals = [lr.get("quality") for lr in (t.get("layers") or [])]
        roles = sorted(set(t.get("roles") or []))
        doc = [
            "---",
            f"name: {nm}",
            f"trait_id: {t.get('trait_id')}",
            f"trait_type: {t.get('trait_type')}  # 0=阵营/流派 1=? 2=独立",
            f"tiers: {lt}",
            f"version: {version}",
            "---",
            "",
            f"# {nm}",
            "",
            f"![]({t.get('icon_url') or ''})",
            "",
            "## 激活档位",
            "",
            "| 层 | 所需人数 | 档色 |",
            "|---|---|---|",
        ]
        for idx, (lv, q) in enumerate(zip(lt, quals, strict=False)):
            doc.append(f"| {idx + 1} | {lv} | {q} |")
        doc += [
            "",
            "## 效果(官方全文)",
            "",
            strip_rich(t.get("effect") or "") or "(见 remarks)",
            "",
            "## 成员(官方名单)",
            "",
            " / ".join(roles) or "(无)",
            "",
        ]
        for rm in t.get("remarks") or []:
            doc.append(f"> {rm.get('remark', '')}".strip())
        (DOC_DIR / f"{nm}.md").write_text("\n".join(doc), encoding="utf-8")
    print(f"[docs] {len(traits)} 羁绊 -> {DOC_DIR}")


if __name__ == "__main__":
    main()
