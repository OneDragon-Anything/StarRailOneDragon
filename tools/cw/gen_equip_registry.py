"""解析 docs equipment.md → 生成 cw_equipment_data.py 全量 EQUIPMENTS 注册表(P0-1 拆分:数据独立文件,SIFT 在 cw_equipment.py 手维护)。

D-70「参考数据补全:装备代码注册表全量」。equipment.md(米游社🟢,已由 cw_shots OCR 校验
与数据银行一致)是权威源;本脚本把它的分类表(+合成配方段)解析成 _eq() 行,生成
cw_equipment_data.py(P0-1:数据独立;SIFT 在 cw_equipment.py 手维护)。stacking 由效果文本
推断(含「可叠加/叠加N层」→True);recipe 解析「进阶合成配方」段。

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


def parse_recipes() -> dict[str, tuple[str, str]]:
    """解析 equipment.md「进阶合成配方」段 → {进阶名: (简易A, 简易B)}。

    只收 2 件全的(``A + B``);同件×2 / off-screen / 幸运星漏检 待核不计(留 doc 待核区)。
    """
    recipes: dict[str, tuple[str, str]] = {}
    in_section = False
    for line in DOC.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("##"):
            in_section = "合成配方" in s
            continue
        if not in_section or not s.startswith("|") or "---" in s:
            continue
        cells = [c.strip() for c in s.split("|") if c.strip()]
        if len(cells) != 2 or cells[0] == "进阶":
            continue  # 跳表头(| 进阶 | = 简易A + 简易B |)
        name, formula = cells
        if " + " in formula:
            parts = [p.strip() for p in formula.split(" + ")]
            if len(parts) == 2 and parts[0] and parts[1]:
                recipes[name] = (parts[0], parts[1])
    return recipes


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


def merge_codex(entries: list[dict]) -> list[dict]:
    """合并图鉴抽取补丁(权威:数据银行 > 米游社 md;2026-08-15)。

    - md effect 空(简易基础属性/占位)→ 图鉴抽取填;
    - md 没有的条目(数据银行有而米游社无:穿刺死棘之枪/管理员手套ProMax/诅咒·干将莫邪/财富)
      → 图鉴抽取新增(category 按截图 tier 映射,合集→按效果语义归类)。
    图鉴抽取产物: .debug/temp/cw_equip_data.json(extract_equip_data.py 跑 cw_shots)。
    """
    import json

    codex_path = REPO / ".debug/temp/cw_equip_data.json"
    if not codex_path.exists():
        return entries
    codex = json.loads(codex_path.read_text(encoding="utf-8"))
    TIER_CAT = {"简易": "简易", "进阶": "进阶", "特权": "特权", "星徽": "星徽", "消耗品": "工具"}
    # 合集 tab 混多类,按效果语义归:卡带→骇客 / 圣杯·王冠·死棘→命运 / 财富·垃圾袋→特殊 / 白昼前缀→白昼
    def guess_cat(nm: str, eff: str) -> str:
        if nm.startswith("白昼·") or nm.startswith("极·白昼·"):
            return "白昼"
        if "卡带" in nm:
            return "骇客"
        if any(k in nm for k in ("圣杯", "王冠", "死棘", "阿瓦隆", "宝石剑", "开辟之星", "干将莫邪")):
            return "命运"
        if any(k in eff for k in ("金币", "扑满", "病毒", "投影", "防火墙", "芯片", "手套", "墨镜", "拷贝仪", "扳手")):
            return "骇客"
        return "特殊"

    # 进阶配方:图鉴 icon 反查产物(36/36,方案 b)覆盖 md 配方(21 条,仅 1 条用户确认过)
    for e in entries:
        rec = (codex.get(e["name"]) or {}).get("recipe")
        if rec and len(rec) >= 2:
            e["recipe"] = tuple(rec[:2])
    filled = 0
    for e in entries:
        if not e["effect"] and e["name"] in codex:
            eff = " ".join(codex[e["name"]].get("effect") or [])
            if eff:
                e["effect"] = eff
                e["stacking"] = _stacking(eff)
                filled += 1
    added = 0
    known = {e["name"] for e in entries}
    for nm, v in codex.items():
        if nm in known:
            continue
        eff = " ".join(v.get("effect") or [])
        cat = TIER_CAT.get(v.get("tier") or "") or guess_cat(nm, eff)
        entries.append({"name": nm, "category": cat, "effect": eff,
                        "stacking": _stacking(eff), "source": "", "recipe": None})
        added += 1
    print(f"[codex-merge] effect 填 {filled} 条,新增 {added} 条(图鉴权威)")
    return entries


def main() -> None:
    entries = merge_codex(parse())
    recipes = parse_recipes()
    for e in entries:
        # 配方优先级:图鉴 icon 反查(merge_codex 注入,36/36)> md 文字(21 条,仅 1 条用户确认);
        # 图鉴无配方条目才回落 md
        if not e.get("recipe"):
            e["recipe"] = recipes.get(e["name"])
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
            rec = e.get("recipe")
            rec_arg = f", recipe={rec!r}" if rec else ""
            eq_lines.append(f'    _eq("{e["name"]}", "{e["category"]}", "{eff}", {stk}, "{e["source"]}"{rec_arg}),')
        eq_lines.append("")

    count_summary = " / ".join(f"{c.split(': ')[0]} {c.split(': ')[1]}" for c in counts)
    module = (_MODULE_TEMPLATE
              .replace("__ENTRIES__", "\n".join(eq_lines))
              .replace("__TOTAL__", str(total))
              .replace("__COUNTS__", count_summary))
    out_path = REPO / "src/sr_od/application/currency_war/cw_equipment_data.py"  # P0-1:只写数据;SIFT 在 cw_equipment.py(手维护,不被覆盖)
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
    recipe: tuple[str, str] | None = None  # 进阶合成配方(2 简易);非进阶/待核→None


def _eq(name: str, category: str, effect: str, stacking: bool, source: str = "",
        recipe: tuple[str, str] | None = None) -> Equipment:
    return Equipment(name=name, category=category, effect=effect, stacking=stacking, source=source, recipe=recipe)


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
