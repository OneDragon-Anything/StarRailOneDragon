"""货币战争 · 羁绊(traits)对拍器(官方 traits.json vs cw_factions/cw_chars 注册表)。

数据源:.debug/temp/currency_war/plaza/trait_detail.json(子代理采集,lineup/index 按羁绊筛,
V4.4 过滤;采集器 .debug/temp/cw_trait_probe_14*.py 版本更新重跑)
+ plaza config_v*.json 的 role_property_list(property type → 中文名映射表)。

产出(只输出 stdout,**不再写任何 src 文件**):
  1. **tiers 对拍**:traits.json 的激活阈值逐键比 `cw_factions.FACTIONS[name].tiers`
     (键空间 33↔33,含命运圣杯);不一致打印 diff 并**非零退出**。
  2. **成员对拍**:官方成员名单逐键比 `chars_by_faction(name)` 集合(成员关系单一源 =
     CHARACTERS 自报 factions/flows;命运圣杯官方未提供 roles,以 FACTIONS 为准跳过);
     不一致打印 diff 并**非零退出**。
  3. **stdout 效果对拍输出**:逐羁绊渲染 effect_rich 全文,供版本更新时人工
     对拍 `cw_factions.FACTIONS` 的 desc(效果全文单一源在注册表 desc 字段)。

⚖️ 原「src/cw_factions_data.py 数据模块(TRAIT_TIERS/TRAIT_ROLES)」与
「docs/game/currency_war/data/traits/ 每羁绊一档文档层」均已删(数据单一源收敛:
tiers/成员/效果全文只在 cw_factions + cw_chars 注册表);本脚本由生成器改为纯对拍器,
重跑不复活任何平行数据层。

效果文本渲染(官方纯文本 effect 字段对 display=all 属性同样丢词,不可直接用,须从
effect_rich 自行渲染):
  - <property type=X display=all>  → 替换为 role_property_list[X].name(属性中文名);
  - <property type=X display=icon> → 删除(纯图标,文本语义在其后文字里);
  - <color=...>...</color>         → 删除(纯高亮,无语义)。
未知 property type / 空 name:保留原标签并打印警告(提醒补档),不静默吞。

分工(同角色域):**判断层手维护,官方数据走本对拍器** —— cw_factions.FACTIONS 的
category/note/desc/tiers 与 cw_chars 的成员关系是人判+单一源;版本更新重跑本脚本,
官方 traits.json 与注册表漂移即非零退出(替代已删的 cw_factions_data 平行数据层)。

用法: uv run python tools/cw/gen_factions.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))  # 对拍 import sr_od 注册表
PLAZA_DIR = REPO / ".debug/temp/currency_war/plaza"
SRC_JSON = PLAZA_DIR / "trait_detail.json"

ISOLATED = {"师徒"}  # 旧赛季遗留(V4.4 无持有者),不生成

# 成员对拍已知例外(官方 roles 含、注册表不含),值 = 裁决理由(注册表为单一源):
#  - 布洛妮娅 ∈ 官方「贝洛伯格」:来自隐藏变体条目 11011;注册表按可见条目 11012
#    (燃血+大守护者,去贝洛伯格,2026-08-15 plaza 对齐裁决,见 cw_chars.py 行内注)。
#  - 开拓者·记忆 ∈ 官方「欢愉」:来自隐藏共享壳条目 8007;注册表按记忆页(列车同行+能量,
#    无欢愉,同 2026-08-15 裁决)。
MEMBER_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("贝洛伯格", "布洛妮娅"): "官方含隐藏变体 11011,注册表按可见条目 11012",
    ("欢愉", "开拓者·记忆"): "官方含隐藏共享壳 8007,注册表按记忆页无欢愉",
}

PROP_TAG_RE = re.compile(r"<property\s+type=(\S+?)(?:\s+display=(\S+?))?>")
COLOR_TAG_RE = re.compile(r"</?color(?:=[^>]*)?>")
ANY_TAG_RE = re.compile(r"<[^>]+>")


def load_prop_map(version: str) -> dict[str, str]:
    """从 plaza config 读 property type → 中文名映射表。"""
    cfg_path = PLAZA_DIR / f"config_v{version}.json"
    if not cfg_path.exists():  # 采集器版本命名变化时兜底:取目录内最新 config_v*.json
        cands = sorted(PLAZA_DIR.glob("config_v*.json"))
        if not cands:
            raise FileNotFoundError(f"plaza config not found under {PLAZA_DIR}")
        cfg_path = cands[-1]
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    prop_map: dict[str, str] = {}
    for p in cfg.get("role_property_list") or []:
        if p.get("property_type") and p.get("name"):
            prop_map[p["property_type"]] = p["name"]
    return prop_map


def render_rich(rich: str, prop_map: dict[str, str]) -> tuple[str, list[str]]:
    """effect_rich → 可读纯文本。返回 (渲染文本, 警告列表)。"""
    warns: list[str] = []

    def _prop(m: re.Match[str]) -> str:
        ptype, display = m.group(1), m.group(2)
        if display == "icon":
            return ""  # 纯图标,无文本
        name = prop_map.get(ptype)
        if not name:  # display=all 但映射缺失:保留原标签提醒补档
            warns.append(f"unknown property type={ptype}")
            return m.group(0)
        return name

    out = COLOR_TAG_RE.sub("", rich)
    out = PROP_TAG_RE.sub(_prop, out)
    out = out.replace("\\n", "\n")  # \n 字面还原为真换行
    for m in ANY_TAG_RE.finditer(out):  # 渲染后仍残留的未知标签
        warns.append(f"unknown tag {m.group(0)[:40]}")
    return out.strip(), warns


def main() -> None:
    raw = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    version = raw.get("version", "?")
    traits = [t for t in raw.get("traits", []) if t["name"] not in ISOLATED]
    prop_map = load_prop_map(version)
    print(f"traits: {len(traits)}(排除旧赛季 {sorted(ISOLATED)});prop_map: {len(prop_map)} 项")

    def effect_text(t: dict) -> str:
        """羁绊总效果:优先 effect_rich 渲染,回退纯文本。"""
        rich = t.get("effect_rich") or ""
        if rich:
            txt, ws = render_rich(rich, prop_map)
            warns.extend(f"{t['name']}(总效果): {w}" for w in ws)
            return txt
        return (t.get("effect") or "").strip()

    warns: list[str] = []

    # ---- 1) tiers 对拍:官方 traits.json vs cw_factions.FACTIONS(单一源)----
    from sr_od.application.currency_war.data.cw_factions import FACTIONS

    print("\n[tiers] 官方激活阈值 vs FACTIONS[name].tiers(逐键):")
    tier_diffs: list[str] = []
    official_names = {t["name"] for t in traits}
    for t in sorted(traits, key=lambda x: (x.get("trait_type") or 0, x["name"])):
        name = t["name"]
        lt = tuple(int(lr["layer"]) for lr in (t.get("layers") or []))
        fa = FACTIONS.get(name)
        if fa is None:
            tier_diffs.append(f"{name}: 官方 tiers={lt},FACTIONS 无此羁绊(新羁绊?需同步注册表)")
        elif fa.tiers != lt:
            tier_diffs.append(f"{name}: 官方 tiers={lt} vs FACTIONS={fa.tiers}")
    for name in sorted(set(FACTIONS) - official_names):
        tier_diffs.append(f"{name}: FACTIONS 有此羁绊(tiers={FACTIONS[name].tiers}),官方 traits.json 无")
    if tier_diffs:
        for d in tier_diffs:
            print(f"  ✗ {d}")
    else:
        print(f"  ✓ 一致({len(official_names)} 键逐键全等)")

    # ---- 2) 成员对拍:官方 roles vs chars_by_faction 派生(成员单一源 = CHARACTERS)----
    from sr_od.application.currency_war.data.cw_chars import chars_by_faction

    print("\n[roles] 官方成员名单 vs chars_by_faction(name) 集合(逐键):")
    role_diffs: list[str] = []
    n_roles = 0
    for t in sorted(traits, key=lambda x: (x.get("trait_type") or 0, x["name"])):
        name = t["name"]
        official = set(t.get("roles") or [])
        if not official:
            # 官方未提供该羁绊的成员名单(如命运圣杯):以 FACTIONS/CHARACTERS 为准,跳过
            print(f"  - {name}: 官方无 roles,以注册表为准({', '.join(c.name for c in chars_by_faction(name)) or '空'})")
            continue
        n_roles += 1
        # 派生集合 = 阵营/流派成员(chars_by_faction)+ 独立羁绊成员(Character.independent,
        # 独立羁绊不在 factions/flows 里,chars_by_faction 覆盖不到)
        from sr_od.application.currency_war.data.cw_chars import CHARACTERS
        derived = {c.name for c in chars_by_faction(name)}
        derived |= {c.name for c in CHARACTERS.values() if c.independent == name}
        extra = official - derived
        missing = derived - official
        for m in sorted(extra):
            if (name, m) in MEMBER_EXCEPTIONS:
                print(f"  - {name} ⊃ {m}: 例外放行({MEMBER_EXCEPTIONS[(name, m)]})")
            else:
                role_diffs.append(f"{name}: 官方成员 {m} 不在注册表派生集合")
        for m in sorted(missing):
            if (name, m) in MEMBER_EXCEPTIONS:
                print(f"  - {name} ⊅ {m}: 例外放行({MEMBER_EXCEPTIONS[(name, m)]})")
            else:
                role_diffs.append(f"{name}: 注册表派生成员 {m} 不在官方名单")
    if role_diffs:
        for d in role_diffs:
            print(f"  ✗ {d}")
    else:
        print(f"  ✓ 一致({n_roles} 个有官方名单的羁绊,成员集合全等,含 {len(MEMBER_EXCEPTIONS)} 条已裁决例外)")

    # ---- 3) 效果对拍输出(stdout,不写文件) ----
    # 版本更新时人工对拍 cw_factions.FACTIONS 的 desc 是否需同步(单一源在注册表)。
    print("\n[effects] 逐羁绊效果全文(对拍 FACTIONS.desc 用):")
    for t in sorted(traits, key=lambda x: (x.get("trait_type") or 0, x["name"])):
        print(f"--- {t['name']} ---")
        print(effect_text(t) or "(无总效果文本)")

    if warns:
        print(f"\n[warn] {len(warns)} 条渲染警告(未知标签/属性,需补档):")
        for w in sorted(set(warns)):
            print(f"  - {w}")
    else:
        print("[warn] 无渲染警告,全部 property tag 已解析")

    if tier_diffs or role_diffs:
        total = len(tier_diffs) + len(role_diffs)
        print(f"\n[result] 对拍不一致 {total} 条(tiers {len(tier_diffs)} + 成员 {len(role_diffs)}),注册表需同步")
        raise SystemExit(1)
    print("\n[result] tiers 与成员对拍全部一致")


if __name__ == "__main__":
    main()

