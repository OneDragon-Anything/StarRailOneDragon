"""货币战争 · 羁绊(traits)数据生成器(官方 traits.json → 注册表数据层 + 明细文档)。

数据源:.debug/temp/currency_war/plaza/trait_detail.json(子代理采集,lineup/index 按羁绊筛,
V4.4 过滤;采集器 .debug/temp/cw_trait_probe_14*.py 版本更新重跑)
+ plaza config_v*.json 的 role_property_list(property type → 中文名映射表)。

产出:
  1. src/sr_od/application/currency_war/cw_factions_data.py —— TRAIT_TIERS(官方 tiers:
     name → 激活阈值序列)+ TRAIT_ROLES(官方成员名单);
     效果全文不放代码(无代码消费方,策略层用结构化字段),在文档层(下)。
  2. docs/game/currency_war/data/traits/<名>.md —— 每羁绊一档(tiers 逐层/效果/成员)。

效果文本渲染(官方纯文本 effect 字段对 display=all 属性同样丢词,不可直接用,须从
effect_rich 自行渲染):
  - <property type=X display=all>  → 替换为 role_property_list[X].name(属性中文名);
  - <property type=X display=icon> → 删除(纯图标,文本语义在其后文字里);
  - <color=...>...</color>         → 删除(纯高亮,无语义)。
未知 property type / 空 name:保留原标签并打印警告(提醒补档),不静默吞。

分工(同角色域):**数据层生成,判断层手维护** —— cw_factions.FACTIONS 的
category(combat/economy/support)与 note(策略注记)是人判,不在生成范围;
生成器产 TRAIT_* 数据模块供 FACTIONS 对拍校验(tiers 漂移检测)。

用法: uv run python tools/cw/gen_factions.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[2]
PLAZA_DIR = REPO / ".debug/temp/currency_war/plaza"
SRC_JSON = PLAZA_DIR / "trait_detail.json"
DATA_PY = REPO / "src/sr_od/application/currency_war/cw_factions_data.py"
DOC_DIR = REPO / "docs/game/currency_war/data/traits"
# r156 写目标白名单守卫:生成器**只允许**写以下路径(数据层+文档层);
# 判断层(cw_factions.py 等)永不在此列——若有人改动 DATA_PY/DOC_DIR
# 指向判断层文件,此处断言拦截(防误覆盖人工维护的注册表)。
WRITABLE_TARGETS = (DATA_PY, DOC_DIR)


def _assert_writable_targets() -> None:
    for t in WRITABLE_TARGETS:
        if 'cw_factions.py' in t.name or (
                t.suffix == '.py' and not t.name.endswith('_data.py')):
            raise RuntimeError(
                f'生成器写目标非法: {t}(判断层/非 _data.py 数据层文件;'
                f'本生成器只写 {WRITABLE_TARGETS})')


_assert_writable_targets()

ISOLATED = {"师徒"}  # 旧赛季遗留(V4.4 无持有者),不生成

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

    def layer_text(t: dict, lr: dict) -> str:
        """分层效果:优先 layer.effect_rich 渲染,回退纯文本。"""
        rich = lr.get("effect_rich") or ""
        if rich:
            txt, ws = render_rich(rich, prop_map)
            warns.extend(f"{t['name']}(第{lr.get('layer')}层): {w}" for w in ws)
            return txt
        return (lr.get("effect") or "").strip()

    warns: list[str] = []

    # ---- 1) 数据模块 ----
    lines = [
        "# 警告:本文件由 tools/cw/gen_factions.py 生成(traits.json V" + version + "),勿手编;版本更新重跑。",
        "# 重跑: uv run python tools/cw/gen_factions.py",
        "# 同源产物(人读文档层,效果全文在此): docs/game/currency_war/data/traits/<羁绊名>.md",
        '"""羁绊官方数据(V' + version + "):tiers(激活阈值)/roles(成员)。",
        "",
        "来源:lineup/index 按羁绊筛采集(V4.4 过滤);采集器与过程见 .debug 工作区。",
        "分工:数据层(本模块)生成;category/note 等人判层在 cw_factions.FACTIONS 手维护。",
        "效果全文不入代码(无代码消费方),在 docs/game/currency_war/data/traits/ 文档层。",
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
        layers = t.get("layers") or []
        lt = [int(lr["layer"]) for lr in layers]
        quals = [lr.get("quality") for lr in layers]
        roles = sorted(set(t.get("roles") or []))
        doc = [
            "---",
            f"name: {nm}",
            f"trait_id: {t.get('trait_id')}",
            f"trait_type: {t.get('trait_type')}  # 0=阵营/流派 1=? 2=独立",
            f"tiers: {lt}",
            f"version: {version}",
            "generated_by: tools/cw/gen_factions.py",
            "related_code: src/sr_od/application/currency_war/cw_factions_data.py",
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
        doc += ["", "## 效果(官方全文,自 effect_rich 渲染)", "", effect_text(t) or "(见分层效果)"]
        if layers:
            doc += ["", "## 分层效果", ""]
            for lr in layers:
                doc.append(f"- **第{lr.get('layer')}人**:{layer_text(t, lr)}")
        doc += [
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

    if warns:
        print(f"\n[warn] {len(warns)} 条渲染警告(未知标签/属性,需补档):")
        for w in sorted(set(warns)):
            print(f"  - {w}")
    else:
        print("[warn] 无渲染警告,全部 property tag 已解析")


if __name__ == "__main__":
    main()

