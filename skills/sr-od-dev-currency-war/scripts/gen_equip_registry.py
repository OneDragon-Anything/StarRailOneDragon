"""生成 cw_equipment_data.py 全量 EQUIPMENTS 注册表(单源 = plaza 官方 API config)。

**数据源裁定**:装备数据采集 = 攻略广场 plaza config ``equipment_list`` 单一源;
旧「游戏内图鉴 OCR 实机采集」与 ``equipment.md`` 兜底两源退役(生成器不再消费,
采集链文件删留另账)。单源依据:config 全量覆盖且每条含效果全文(desc 富文本)、
结构化基础属性(properties)、合成配方链(compose_list 含子件全文);社区 wiki
(米游社词条过期/国际服 CW 未建/BWIKI 为旧赛季快照)均不能作当版本数值源,
config 是唯一当版本官方数据。

**「简易装备」派生层**:官方 API 无简易件条目(合成材料层),从全部条目的
compose_list 子件展开去重派生注册表条目(category 落「简易装备」,条目自带
子件 id 与 desc/properties)。特权条目独立登记(「XX·特权」自带数值翻倍
properties,名字不同不撞键,全部入表);模板段的特权去重是
``gen_plaza_chars.py`` 的事,不在本脚本。

**流程**:读缓存最新 config(glob ``config_v*.json`` 后按解析出的版本数字比较
取最大,禁字符串词序——``v4.10`` 词序小于 ``v4.7``)→ collect(官方分类直落
+ 简易装备派生)→ **先对拍旧基准再覆盖写**(stdout 掉出/新增清单,供模板
清理与消费方迁移参考;旧基准经 importlib 动态加载,加载前须注册
``sys.modules``——dataclass 装饰器回查 ``cls.__module__``,不注册报
'NoneType' object has no attribute '__dict__')。

== 用法 ==
    uv run python skills/sr-od-dev-currency-war/scripts/gen_equip_registry.py
    → 对拍报告(stdout)→ 覆盖写 cw_equipment_data.py。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLAZA_DIR = REPO / ".debug/game_data/currency_war/plaza"
OUT_PATH = REPO / "src/sr_od/application/currency_war/data/cw_equipment_data.py"

#: 派生简易装备的类别名(官方 API 无简易件条目,派生层专用值,用户裁定命名)
DERIVED_CATEGORY: str = "简易装备"


def _norm_name(raw: str) -> str:
    """装备名规范形:• 统一 ·(机械规则,与角色域同款)。"""
    return raw.replace(chr(0x2022), chr(0x00B7))


def _strip_tags(desc: str) -> str:
    """剥富文本标签保纯文本。desc 里的 ``\\n`` 是转义字面,**保留字面**
    (还原成真换行会破坏生成产物的 Python 字符串字面量语法)。"""
    return re.sub(r"<[^>]+>", "", desc)


def _stacking(effect: str) -> bool:
    """效果可叠加:含「可叠加」「叠加N层」→ True(文本推断;实机抽检另账)。"""
    return ("可叠加" in effect) or bool(re.search(r"叠加\s*\d+\s*层", effect))


def _props(pe: dict) -> tuple[tuple[str, str], ...]:
    """plaza equipment 条目 → 结构化数值 ((属性名, 数值), ...)。"""
    return tuple((p["name"], p.get("num") or "") for p in (pe.get("properties") or []))


def _recipes(pe: dict) -> tuple[tuple[str, ...], ...]:
    """plaza compose_list → 官方合成路线 (((材料名), ...), ...);多路线全收(宝钻 3 路)。"""
    routes: list[tuple[str, ...]] = []
    for c in pe.get("compose_list") or []:
        ch = tuple(_norm_name(x["name"]) for x in (c.get("childrens") or []))
        if len(ch) >= 2:
            routes.append(ch)
    return tuple(routes)


def latest_config_path() -> Path:
    """缓存目录最新版 config:glob 后按解析出的版本数字比较取最大
    (禁字符串词序比较——``config_v4.10`` 词序小于 ``config_v4.7`` 的陷阱)。"""
    candidates: list[tuple[tuple[int, ...], Path]] = []
    for p in PLAZA_DIR.glob("config_v*.json"):
        m = re.fullmatch(r"config_v(\d+(?:\.\d+)*)\.json", p.name)
        if m:
            candidates.append((tuple(int(x) for x in m.group(1).split(".")), p))
    if not candidates:
        raise FileNotFoundError(f"{PLAZA_DIR} 下无 config_v*.json 快照")
    return max(candidates, key=lambda pair: pair[0])[1]


def collect_official(cfg: dict) -> list[dict]:
    """官方条目直灌:category_name 原样直落(不自造归类);effect = desc 剥
    富文本标签;source = plaza 数字 id(溯源主键;icon URL 带资源 hash 会变,
    不可作键)。特权条目独立登记(自带翻倍 properties,名字不同不撞键)。
    API 字段 ``ability_name``(全空)、``priority``(类别级排序码,条目级无
    信息量)、数字码 ``category`` 不登记。"""
    entries: list[dict] = []
    for pe in cfg["equipment_list"]:
        desc = _strip_tags(pe.get("desc") or "")
        entries.append({"name": _norm_name(pe["name"]),
                        "category": pe.get("category_name") or "",
                        "effect": desc,
                        "stacking": _stacking(desc),
                        "source": str(pe["id"]),
                        "recipes": _recipes(pe),
                        "props": _props(pe)})
    return entries


def derive_simples(cfg: dict) -> list[dict]:
    """compose_list 子件展开去重 → 简易装备派生条目(category 落
    「简易装备」,条目自带子件 id 与 desc/properties;子件为合成材料层,
    官方名单无对应条目)。"""
    seen: dict[str, dict] = {}
    for pe in cfg["equipment_list"]:
        for route in pe.get("compose_list") or []:
            for ch in route.get("childrens") or []:
                nm = _norm_name(ch["name"])
                if nm in seen:
                    continue
                desc = _strip_tags(ch.get("desc") or "")
                seen[nm] = {"name": nm,
                            "category": DERIVED_CATEGORY,
                            "effect": desc,
                            "stacking": _stacking(desc),
                            "source": str(ch["id"]),
                            "recipes": _recipes(ch),
                            "props": _props(ch)}
    return list(seen.values())


def load_baseline() -> dict[str, object]:
    """importlib 动态加载现有注册表文件作对拍基准。加载前必须先注册
    ``sys.modules``(dataclass 装饰器回查 ``cls.__module__`` 的既有坑)。"""
    import importlib.util

    mod_name = "cw_equipment_data_baseline"
    spec = importlib.util.spec_from_file_location(mod_name, OUT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(mod_name, None)
    return {e.name: e for e in mod.EQUIPMENTS.values()}


def render_module(entries: list[dict], season: str) -> str:
    """entries → 模块全文(_MODULE_TEMPLATE 占位填充)。分组按首现序
    (官方条目 config 序在前,派生简易装备收尾),确定性输出。"""
    by_cat: dict[str, list[dict]] = {}
    for e in entries:
        by_cat.setdefault(e["category"], []).append(e)

    eq_lines: list[str] = []
    counts: list[str] = []
    for cat, es in by_cat.items():
        counts.append(f"{cat} {len(es)}")
        eq_lines.append(f"    # —— {cat}({len(es)}) ——")
        for e in es:
            eff = e["effect"].replace('"', '\\"')
            stk = "True" if e["stacking"] else "False"
            extra = ""
            if e["recipes"]:
                extra += f", recipes={e['recipes']!r}"
            if e["props"]:
                extra += f", props={e['props']!r}"
            eq_lines.append(
                f'    _eq("{e["name"]}", "{e["category"]}", "{eff}", '
                f'{stk}, "{e["source"]}"{extra}),')
        eq_lines.append("")

    return (_MODULE_TEMPLATE
            .replace("__ENTRIES__", "\n".join(eq_lines))
            .replace("__TOTAL__", str(len(entries)))
            .replace("__COUNTS__", " / ".join(counts))
            .replace("__SEASON__", season))


def main() -> None:
    cfg_path = latest_config_path()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    cfg = cfg.get("data", cfg)
    season = cfg_path.stem.removeprefix("config_")

    official = collect_official(cfg)
    simples = derive_simples(cfg)
    entries = official + simples
    names = [e["name"] for e in entries]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise ValueError(f"注册表重名(dict 键会静默覆盖): {dup}")

    old = load_baseline()
    old_set, new_set = set(old), set(names)
    official_set = {e["name"] for e in official}
    dropped = sorted(old_set - new_set)
    added = sorted(new_set - old_set)
    kept = old_set & new_set
    print(f"[对拍] 基准 {cfg_path.name}:旧注册表 {len(old)} 件 vs 新注册表 {len(entries)} 件")
    print(f"[对拍] 保留 {len(kept)}(官方侧 {len(kept & official_set)}"
          f" + 派生回归 {len(kept - official_set)})"
          f" / 掉出 {len(dropped)} / 新增 {len(added)}")
    if dropped:
        print("[掉出清单](供模板清理与消费方迁移参考):")
        for n in dropped:
            print(f"  - {n}")
    if added:
        print("[新增清单]:")
        for n in added:
            print(f"  + {n}")

    OUT_PATH.write_text(render_module(entries, season), encoding="utf-8")
    print(f"写全量注册表 → {OUT_PATH}({len(entries)} 件,基准 {season})")


# 模块模板(生成器用占位符 .replace 填充;字面花括号无需转义。
# 勿手改生成产物 —— 改模板/重跑生成器再落盘)
_MODULE_TEMPLATE = '''"""货币战争 装备领域模型(Equipment + EQUIPMENTS 全量注册表;meta 层,数据基准 __SEASON__)。

**生成**:本文件由 ``skills/sr-od-dev-currency-war/scripts/gen_equip_registry.py`` 生成(**勿手改**;
重跑 ``uv run python skills/sr-od-dev-currency-war/scripts/gen_equip_registry.py``,
数据源 = 攻略广场 plaza config 快照 ``.debug/game_data/currency_war/plaza/config_v*.json``
最新版(当前基准 __SEASON__);覆盖写前先对拍旧文件,stdout 掉出/新增清单)。

**数据源(单源)**:plaza 官方 API ``equipment_list`` 直灌——每条含效果全文
(desc 富文本剥标签)、结构化基础属性(properties)、合成配方链(compose_list
含子件全文)。旧三源(图鉴 OCR 校正/``equipment.md`` 兜底)已退役,生成器
不再消费。

**「简易装备」派生层**:官方 API 无简易件条目(合成材料层),从全部条目的
compose_list 子件展开去重派生(category 落「简易装备」,条目自带子件 id 与
desc/properties)。特权条目独立登记(「XX·特权」自带数值翻倍 properties,
名字不同不撞键);模板段特权去重归 ``gen_plaza_chars.py`` 管辖,不在本文件。

**用途**:装备规范名单一真相源 —— COMP_LIBRARY.key_equips / 补给决策 / equip_fit 引用规范装备名。
装备身份默认 bot 跟踪(部署/备战栏),视觉库作恢复旁路。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Equipment:
    """单件装备(官方规范数据)。"""
    name: str           # 规范名(• 统一 ·)
    category: str       # 官方分类名直落:进阶装备/特权装备/星徽/餐品改件/列车改件/宝钻/固有装备;另含派生值「简易装备」
    effect: str         # 效果纯文本(desc 剥富文本标签;\\n 为字面换行)
    stacking: bool      # 效果可叠加(「可叠加/叠加N层」→True;文本推断,实机抽检另账)
    source: str = ""    # plaza 稳定数字 id(溯源主键;icon URL 带资源 hash 会变,不可作键)
    recipes: tuple[tuple[str, ...], ...] = ()   # 官方合成路线(材料名组),多路线全收;空 = 该条无 compose(特权/固有等)
    props: tuple[tuple[str, str], ...] = ()     # 结构化基础属性 (属性名, 数值) —— plaza properties 直取


def _eq(name: str, category: str, effect: str, stacking: bool, source: str = "",
        recipes: tuple[tuple[str, ...], ...] = (),
        props: tuple[tuple[str, str], ...] = ()) -> Equipment:
    return Equipment(name=name, category=category, effect=effect, stacking=stacking,
                     source=source, recipes=recipes, props=props)


EQUIP_TOOL_CATEGORY: str = '工具'
"""注册表装备分类学里的「工具」类名(不可 drag 穿戴,只能拖到装备/角色上
消耗使用)。分类全集单一源 = 本文件 ``Equipment.category`` 字段注释;
消费 = kernel 判据面(`cw_equip_wear_plan` 穿戴候选过滤,import 本常量)
与执行边定位读(`prep_actions._owned_grid_locate`,全库模板按名定位);
工具消费 = `CwActionToolUseOp`;禁再写本地平行定义。

[v4.7 待裁] v4.7 官方 7 类(进阶装备/特权装备/星徽/餐品改件/列车改件/
宝钻/固有装备)无「工具」类,旧工具 7 件全部不在官方名单——本常量判据
失效。暂保留旧值防断裂消费面(cw_equip_env / cw_equip_wear_plan /
cw_gain_chain / cw_investments / mandate.py);实机确认 v4.7 消耗品形态
后重裁迁移。"""


CONSUMABLE_EQUIP_CATEGORIES: frozenset[str] = frozenset(
    {EQUIP_TOOL_CATEGORY, '特殊'})
"""消耗品类别判据单一源(「工具」= 本文件 EQUIP_TOOL_CATEGORY 常量引名,
零第二字面量;「特殊」字面只在此写一次)。口径出处 = 识别侧 owned 装备栏
采集的混排判据(obs/recognizers/battle_prep_recognizer:命中 = 消耗品,
其余 = 装备)。消费 = kernel 判据面(空仓经验条件谓词
check_strategy_empty_equip_xp 的「消耗品除外」豁免);禁再写本地平行定义。

[v4.7 待裁] 官方 7 类无「工具」「特殊」类(旧工具 7 件不在官方名单;宝钻
1 件单列且可穿戴非消耗品)——两键判据失效。暂保留旧值防断裂消费面
(同 EQUIP_TOOL_CATEGORY 消费面);实机确认 v4.7 消耗品形态后重裁迁移。"""


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
