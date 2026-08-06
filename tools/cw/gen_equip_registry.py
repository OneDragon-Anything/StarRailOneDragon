"""解析 docs equipment.md → 生成 cw_equipment.py 全量 EQUIPMENTS 注册表(避免手抄错)。

D-70「参考数据补全:装备代码注册表全量」。equipment.md(米游社🟢,已由 cw_shots OCR 校验
与数据银行一致)是权威源;本脚本把它的分类表解析成 _eq() 行,贴入 cw_equipment.py 替换
现 12 key 的部分。stacking 由效果文本推断(含「可叠加/叠加N层」→True)。

== 用法 ==
    uv run python tools/cw/gen_equip_registry.py
    → 打印 _eq() 行 + 统计(按 category),人工核对后贴入 cw_equipment.py。
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs/game/currency_war/data/equipment.md"

# section 标题关键词 → category 标签(代码用)
SECTION_CATEGORY: list[tuple[str, str]] = [
    ("简易装备", "简易"),
    ("进阶装备", "进阶"),
    ("特权装备", "特权"),
    ("阵营/流派星徽", "星徽"),
    ("白昼装备", "白昼"),
    ("命运改件", "命运"),
    ("骇客改件", "骇客"),
    ("特殊/财富", "特殊"),
    ("工具/消耗品", "工具"),
]


def _stacking(effect: str) -> bool:
    """效果可叠加:含「可叠加」「叠加N层」→ True。"""
    return ("可叠加" in effect) or bool(re.search(r"叠加\s*\d+\s*层", effect))


def _norm_source(raw: str) -> str:
    """统一 source:去 ``content/`` 前缀(简易表带,其它不带)。"""
    return raw.strip().replace("content/", "")


def _clean_name(raw: str) -> list[str]:
    """清理装备名:拆「A/B」→ [A, B];保留括注(别名如「列车同行星徽(命运圣杯星徽)」、
    变体如「财富(基础)/(强化)」都保留,避免去括号撞名)。"""
    raw = raw.strip()
    if "/" in raw:
        return [p.strip() for p in raw.split("/") if p.strip()]
    return [raw]


def parse() -> list[dict]:
    """解析 equipment.md → [{name, category, effect, stacking, source}, ...]。"""
    lines = DOC.read_text(encoding="utf-8").splitlines()
    entries: list[dict] = []
    category: str | None = None
    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            category = None
            for kw, cat in SECTION_CATEGORY:
                if kw in s:
                    category = cat
                    break
            continue
        if category is None or not s.startswith("|") or "---" in s:
            continue
        cells = [c.strip() for c in s.split("|")]
        cells = [c for c in cells if c != ""]  # 去首尾空(管道符两侧)
        # 跳表头:含「效果原文/source」标记,或首格恰为「装备/道具/星徽」(精确匹配,避免误跳
        # 含「星徽」的数据行如「仙舟星徽」)
        if any(mark in s for mark in ("效果原文", "source")) or cells[0] in ("装备", "道具", "星徽"):
            continue
        if len(cells) == 2:
            # 简易表:name, source(无效果)
            names = _clean_name(cells[0])
            for nm in names:
                entries.append({"name": nm, "category": category, "effect": "",
                                "stacking": False, "source": _norm_source(cells[1])})
        elif len(cells) >= 3:
            names = _clean_name(cells[0])
            effect = cells[1].strip()
            source = _norm_source(cells[2])
            # 占位效果(「见图鉴 content/xxx」)→ 留空
            if "见图鉴" in effect:
                effect = ""
            stk = _stacking(effect)
            for nm in names:
                entries.append({"name": nm, "category": category, "effect": effect,
                                "stacking": stk, "source": source})
    return entries


def main() -> None:
    entries = parse()
    by_cat: dict[str, list[dict]] = {}
    for e in entries:
        by_cat.setdefault(e["category"], []).append(e)

    # _eq() 行(按 category 分组)
    eq_lines: list[str] = []
    counts: list[str] = []
    total = 0
    for cat, es in by_cat.items():
        counts.append(f"# {cat}: {len(es)}")
        total += len(es)
        eq_lines.append(f"    # —— {cat}({len(es)}) ——")
        for e in es:
            eff = e["effect"].replace('"', '\\"')
            stk = "True" if e["stacking"] else "False"
            eq_lines.append(f'    _eq("{e["name"]}", "{e["category"]}", "{eff}", {stk}, "{e["source"]}"),')
        eq_lines.append("")

    count_summary = " / ".join(f"{c.split(': ')[0]} {c.split(': ')[1]}" for c in counts)
    module = (_MODULE_TEMPLATE
              .replace("__ENTRIES__", "\n".join(eq_lines))
              .replace("__TOTAL__", str(total))
              .replace("__COUNTS__", count_summary))
    out_path = REPO / "src/sr_od/application/currency_war/cw_equipment.py"
    out_path.write_text(module, encoding="utf-8")
    print(f"写全量注册表 → {out_path}({total} 件)")


# 模块模板(生成器用 __ENTRIES__/__TOTAL__/__COUNTS__ 占位,.replace 填充;
# 字面花括号(dict comprehension)无需转义。勿手改生成产物 —— 改 docs 后重跑生成器)
_MODULE_TEMPLATE = '''"""货币战争 装备领域模型(Equipment + EQUIPMENTS 全量注册表;meta 层,V4.4)。

**来源**:数据银行装备图鉴(权威)+ 米游社图鉴对齐。2026-08-06 经 ``harvest_equip_codex``
op 采 154 件图标 + cw_shots OCR 校验,效果正文与 docs(米游社)一致 → 数据银行权威性确认。
本注册表由 ``tools/cw/gen_equip_registry.py`` 从 ``docs/game/currency_war/data/equipment.md``
解析生成(**勿手改** —— 改 docs 后重跑生成器)。

**用途**:装备规范名单一真相源 —— COMP_LIBRARY.key_equips / 补给决策 / equip_fit 引用规范装备名。
装备身份默认 bot 跟踪(部署/备战栏),视觉库(``assets/template/cw_equip/*.png``,154 件)作恢复旁路。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Equipment:
    """单件装备(图鉴规范数据)。"""
    name: str           # 规范名
    category: str       # "简易"/"进阶"/"特权"/"星徽"/"白昼"/"命运"/"骇客"/"特殊"/"工具"
    effect: str         # 效果原文(简易只基础属性→空)
    stacking: bool      # 效果可叠加("可叠加"/"叠加N层"→True)
    source: str = ""    # 米游社 content_id


def _eq(name: str, category: str, effect: str, stacking: bool, source: str = "") -> Equipment:
    return Equipment(name=name, category=category, effect=effect, stacking=stacking, source=source)


# ===== EQUIPMENTS 全量注册表(__TOTAL__ 件;__COUNTS__)=====
EQUIPMENTS: dict[str, Equipment] = {e.name: e for e in [
__ENTRIES__]}

EQUIPMENT_ROSTER: frozenset[str] = frozenset(EQUIPMENTS.keys())


def get_equip(name: str) -> Equipment | None:
    """按规范名取 Equipment;无则 None。"""
    return EQUIPMENTS.get(name)
'''


if __name__ == "__main__":
    main()

