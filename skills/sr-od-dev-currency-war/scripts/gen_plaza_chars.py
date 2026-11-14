"""货币战争 · plaza 官方接口 → 角色数据产物生成器(自包含,版本更新重跑)。

数据源:攻略广场 game/config API **直连**(免登录公开接口,无本地依赖):
  GET https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config?game=hkrpg
  (必需 header x-rpc-currencywar-tourn: tourn)

产出(只写 assets/docs 产物与 .debug 片段,**不写任何 src 文件**):
  1. docs/game/currency_war/data/characters/<规范名>.md — 每角色一档(同名多档合并,
     档位节列出全部官方 id 与费用;技能星级效果全文/trait 官方描述);
  2. 官方立绘模板库 assets/template/currency_war/character_avatar/(立绘图源 =
     plaza 接口 role_list[].big_icon 烘焙;**角色粒度单模板**——同名多档共用一目录,
     官方多档 icon URL 全同视觉同图,底色取起始档 rarity);
  3. 官方装备模板库 equip_plaza(混合:plaza 进阶 art + 手工简易/特权);
  4. 注册表段片段 .debug/game_data/currency_war/plaza/registry_chars_v<版本>.py —
     官方逐条 `_ch(...)` 调用文本(参数序 = cw_chars._ch 工厂签名),版本更新时组装进
     cw_chars.py 官方段(两侧生成段标记注释;首次组装人工,标记建立后按标记重写);
  5. 掉出名单 diff 报告 .debug/game_data/currency_war/plaza/dropped_v<版本>.md —
     旧注册表名单 − 新官方名单,分「纯角色掉出(文档删除清单)」与「系统单位迁出
     (转 SYSTEM_UNITS,非删除)」两类;**掉出方向的唯一出口**。

名字归一口径:官方 name U+2022(•)统一为 U+00B7(·)——全仓规范名均为间隔号,
canon() 为归一单一源;守卫加严:产出段名字含 • 直接报错(防归一被绕过)。

对拍(--check-only):注册表段片段 vs config 快照逐字段对拍(63=63 归零才算过);
main 默认产段**不跑对拍**(注册表重建落地前无对拍对象),对拍显式传参触发:
  uv run python skills/sr-od-dev-currency-war/scripts/gen_plaza_chars.py --check-only

用法(项目根,一个命令全完成):
  uv run python skills/sr-od-dev-currency-war/scripts/gen_plaza_chars.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))  # 供掉出 diff 报告 import 现役注册表(cw_chars)
DOC_DIR = REPO / "docs/game/currency_war/data/characters"
TPL_DIR = REPO / "assets/template/currency_war/character_avatar"  # 官方立绘模板库(替代手采库)
EQUIP_TPL_DIR = REPO / "assets/template/currency_war/equip_plaza"  # 官方装备模板库(混合:plaza进阶art+手工简易/特权)
PLAZA_DIR = REPO / ".debug/game_data/currency_war/plaza"  # 拉取缓存与生成片段统一落点(与 plaza_fetch.OUT_DIR 同目录)

CONFIG_URL = "https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config?game=hkrpg"
HEADERS = {
    "x-rpc-currencywar-tourn": "tourn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://act.miyoushe.com/",
}

# plaza 站位 → 注册表站位(Character.position 词汇:front/back/common);未知值报错。
POSITION_MAP = {"Front": "front", "Back": "back", "Common": "common"}

# category_tags 首技能口径的已知多技能不一致例外(按官方 id):首技能 ('输出',)、
# 另一技能 ('输出','辅助')——首技能口径与手写注册表值一致,放行并打印;其余不一致
# 条目报错人工裁定。
CATEGORY_TAG_EXCEPTIONS: frozenset[str] = frozenset({"140402", "122102", "140802", "110702"})

# is_hide 条目行内注:当前唯一隐藏条目为腾荒(语义依据 =
# docs/game/currency_war/research/v47_tenghuang_binding.md);未来版本出现其他
# 隐藏条目时按当期语义修订本注。
HIDE_INLINE_NOTE = "# 官方隐藏态:饮月绑定随从(双龙吟召唤,星级随饮月),非独立入池员工"

# 费用档底色(BGR,imdecode 采样空间;烘焙合成用,与现库已烘底色逐像素一致)。
# 来源:2026-08-17 冻结自旧手采库 character_cw_portrait 角块中位数(原 gen_templates 运行时采样;
# 该库已删,plaza 库转唯一库)。显示 RGB:1灰#6C6E78/2绿#488278/3蓝#59709E/4紫#8F6DEE/5金#C09B5D。
COST_BG: dict[int, tuple[int, int, int]] = {
    1: (120, 110, 108),
    2: (120, 130, 72),
    3: (158, 112, 89),
    4: (238, 109, 143),
    5: (93, 155, 192),
}


def fetch_config() -> dict:
    """直连 plaza config API(免登录公开;header 缺 retcode!=0)。"""
    req = urllib.request.Request(CONFIG_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        d = json.loads(resp.read())
    if d.get("retcode") != 0:
        raise RuntimeError("config retcode={} msg={}".format(d.get("retcode"), d.get("message")))
    return d["data"]


def canon(name: str) -> str:
    """plaza 名 → 规范名(U+2022 • 统一 U+00B7 ·;归一规则单一源)。"""
    return name.replace(chr(0x2022), chr(0x00B7))


def trait_map(cfg: dict) -> dict[str, tuple[int, str]]:
    """顶层 trait_info_list → {trait_id: (trait_type, trait_name)}。

    role_list[].trait_details 条目只带 {id, name, desc, icon},不含 trait_type
    ——羁绊类型必须经本表 join 取得。
    """
    return {t["trait_id"]: (int(t["trait_type"]), t["trait_name"]) for t in cfg["trait_info_list"]}


def derive_fields(role: dict, tmap: dict[str, tuple[int, str]]) -> dict:
    """官方 role_list 条目 → 注册表段字段 dict(字段口径 = Character dataclass 字段表)。

    守卫(报错即停,不产残数据):
    - 名字归一:产出段规范名含 • 即报错(归一失效 = bug);
    - 站位映射:front_back_type 非 POSITION_MAP 三值报错;
    - category_tags:取首技能口径;多技能不一致时,已知例外(CATEGORY_TAG_EXCEPTIONS)
      放行并打印,其余报错人工裁定;
    - trait join:trait_details[].id join trait_info_list 按 trait_type 分拣——
      0→factions / 1→schools / 2→independent(多值报错,单值口径)/ 3→丢弃
      (主角光环专属效果,非牌池羁绊,注册表不承载);join 不命中或未知 type 报错。
    """
    cname = canon(role["name"])
    if chr(0x2022) in cname:
        raise RuntimeError(f"规范名含 bullet U+2022(归一失效):{role['id']} {cname!r}")
    pos = POSITION_MAP.get(role["front_back_type"])
    if pos is None:
        raise RuntimeError(f"{role['id']} {cname}: 未知站位值 {role['front_back_type']!r}")
    skills = role.get("skills") or []
    if not skills:
        raise RuntimeError(f"{role['id']} {cname}: 无技能数据,category_tags 无锚")
    tags0 = tuple(skills[0].get("category_tags") or [])
    tag_sets = {tuple(s.get("category_tags") or ()) for s in skills}
    if len(tag_sets) > 1:
        if role["id"] in CATEGORY_TAG_EXCEPTIONS:
            print(f"[guard] {role['id']} {cname}: category_tags 多技能不一致,已知例外放行"
                  f"(取首技能 {list(tags0)},其余 {[list(t) for t in tag_sets - {tags0}]})")
        else:
            raise RuntimeError(f"{role['id']} {cname}: category_tags 多技能不一致 "
                               f"{[list(t) for t in tag_sets]},需人工裁定(当前口径 = 首技能)")
    factions: list[str] = []
    schools: list[str] = []
    independent = ""
    for t in role.get("trait_details") or []:
        info = tmap.get(t["id"])
        if info is None:
            raise RuntimeError(f"{role['id']} {cname}: trait {t['id']}({t['name']})不在顶层 "
                               f"trait_info_list,join 失败")
        ttype, tname = info
        if ttype == 0:
            factions.append(tname)
        elif ttype == 1:
            schools.append(tname)
        elif ttype == 2:
            if independent:
                raise RuntimeError(f"{role['id']} {cname}: 独立羁绊多值({independent}/{tname}),"
                                   f"单值口径破坏,需人工裁定")
            independent = tname
        elif ttype == 3:
            pass  # 主角光环专属效果,非牌池羁绊——注册表不承载,丢弃
        else:
            raise RuntimeError(f"{role['id']} {cname}: trait {t['id']}({tname})未知 "
                               f"trait_type={ttype},需人工裁定")
    return {
        "name": cname,
        "cost": int(role["rarity"]),
        "position": pos,
        "category_tags": tags0,
        "factions": tuple(factions),
        "schools": tuple(schools),
        "independent": independent,
        "source": str(role["id"]),
        "is_expert": bool(role.get("is_expert")),
        "is_hide": bool(role.get("is_hide")),
    }


def derive_all(roles: list, tmap: dict[str, tuple[int, str]]) -> list[dict]:
    """全量条目派生(逐条 derive_fields)+ 同名多档一致性守卫,按官方 id 排序。

    多档守卫:同名多档条目除 id/rarity 外字段须全同(官方多档 = 同角色升星升费,
    现仅星神★阿哈 4/5/7 一组),不一致报错人工裁定。
    """
    fields = [derive_fields(r, tmap) for r in roles]
    fields.sort(key=lambda f: int(f["source"]))
    by_name: dict[str, list[dict]] = {}
    for f in fields:
        by_name.setdefault(f["name"], []).append(f)

    def _sig(f: dict) -> tuple:
        return (f["position"], f["category_tags"], f["factions"], f["schools"],
                f["independent"], f["is_expert"], f["is_hide"])

    for cname, group in by_name.items():
        if len(group) > 1 and len({_sig(f) for f in group}) > 1:
            raise RuntimeError(f"{cname}: 同名多档({len(group)} 档)除 id/rarity 外字段不一致,"
                               f"{[_sig(f) for f in group]},需人工裁定")
    return fields


def _py_tuple(vals: tuple[str, ...]) -> str:
    """str 元组 → Python 字面量(单元组带尾逗号,空元组 ())。"""
    if not vals:
        return "()"
    inner = ", ".join(repr(v) for v in vals)
    return f"({inner},)" if len(vals) == 1 else f"({inner})"


def _ch_line(f: dict) -> str:
    """单条注册表段行:_ch(位置参数 name/cost/position/category_tags, 关键字参数按签名序)。

    与默认值同形的实参省略(factions/schools 空、independent 空、is_expert/is_hide
    False);source 恒非空恒输出。is_hide=True 附行内注(HIDE_INLINE_NOTE)。
    """
    parts = [repr(f["name"]), str(f["cost"]), repr(f["position"]), _py_tuple(f["category_tags"])]
    if f["factions"]:
        parts.append(f"factions={_py_tuple(f['factions'])}")
    if f["schools"]:
        parts.append(f"schools={_py_tuple(f['schools'])}")
    if f["independent"]:
        parts.append(f"independent={f['independent']!r}")
    parts.append(f"source={f['source']!r}")
    if f["is_expert"]:
        parts.append("is_expert=True")
    if f["is_hide"]:
        parts.append("is_hide=True")
    line = "_ch(" + ", ".join(parts) + ")"
    if f["is_hide"]:
        line += "  " + HIDE_INLINE_NOTE
    return line


def gen_registry_fragment(fields: list[dict], version: str, n_bullet: int) -> Path:
    """产物4:官方注册表段片段(registry_chars_v<版本>.py,每条一行 _ch 调用)。

    片段 = 组装原料:版本更新时人工拼进 cw_chars.py 官方段(两侧生成段标记注释),
    骨架与系统单位人工段不动;标记建立后按标记自动重写。
    """
    PLAZA_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# -*- coding: utf-8 -*-",
        f"# CW v{version} 官方注册表段(生成器产,勿手改)。重生成:",
        "#   uv run python skills/sr-od-dev-currency-war/scripts/gen_plaza_chars.py",
        f"# 数据源:攻略广场 game/config API role_list({len(fields)} 条);名字已归一"
        f"(U+2022→U+00B7,{n_bullet} 名 bullet 角色);_ch 参数序 = cw_chars._ch 工厂签名;"
        "is_hide 条目语义见行内注。",
    ]
    lines += [_ch_line(f) for f in fields]
    path = PLAZA_DIR / f"registry_chars_v{version}.py"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[frag] 官方注册表段 {len(fields)} 条(归一 {n_bullet} 名 bullet 角色) -> {path}")
    return path


def gen_diff_report(roles: list, version: str) -> Path:
    """产物5:掉出名单 diff 报告(dropped_v<版本>.md;掉出方向的唯一出口)。

    口径:旧注册表名单(现役 cw_chars.CHARACTERS) − 新官方名单(canon 规范名)。
    系统单位识别 = cost==0(旧注册表借形登记的 cost=0 条目)。分两类:
    - 纯角色掉出 = 文档删除清单(下一阶段执行删除;本生成器对文档只增不删);
    - 系统单位迁出 = 转 SYSTEM_UNITS 人工段(非删除)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS

    new_names = {canon(r["name"]) for r in roles}
    old = CHARACTERS.values() if hasattr(CHARACTERS, "values") else CHARACTERS
    old_entries = list(old)
    old_sys = [c for c in old_entries if c.cost == 0]
    old_pure = {c.name for c in old_entries} - {c.name for c in old_sys}
    dropped = sorted(old_pure - new_names)
    migrated = sorted((c for c in old_sys if c.name not in new_names), key=lambda c: c.name)
    lines = [
        f"# CW v{version} 掉出名单 diff 报告",
        "",
        "生成器:skills/sr-od-dev-currency-war/scripts/gen_plaza_chars.py(掉出方向唯一出口)。",
        f"口径:旧注册表名单({len(old_entries)} 条,含 {len(old_sys)} 系统单位) "
        f"− 新官方名单({len(new_names)} 名)。",
        "",
        f"## A. 纯角色掉出({len(dropped)} 名)= 文档删除清单(下一阶段执行删除;生成器只增不删)",
        "",
    ]
    lines += [f"- {n}(docs/game/currency_war/data/characters/{n}.md)" for n in dropped]
    lines += [
        "",
        f"## B. 系统单位迁出({len(migrated)} 名)= 转 SYSTEM_UNITS 人工段(非删除)",
        "",
    ]
    lines += [f"- {c.name}(旧 source={c.source!r})" for c in migrated]
    PLAZA_DIR.mkdir(parents=True, exist_ok=True)
    path = PLAZA_DIR / f"dropped_v{version}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[diff] 掉出报告:纯角色掉出 {len(dropped)}(文档删除清单)/ "
          f"系统单位迁出 {len(migrated)}(转 SYSTEM_UNITS) -> {path}")
    return path


def strip_rich(s: str) -> str:
    """去富文本标签(<color>/<property>),保可读正文。"""
    s = re.sub(r"<color=[^>]*>|</color>", "", s)
    s = re.sub(r"<property[^>]*>|</property>", "", s)
    return s.replace("\n", " ").strip()


def skill_block(e: dict) -> list[str]:
    """单条目技能/trait 文档行。"""
    out: list[str] = []
    for t in e.get("trait_details") or []:
        out.append("- 羁绊【{}】:{}".format(t["name"], strip_rich(t.get("desc") or "")))
    for sk in e.get("skills") or []:
        tags = "、".join(sk.get("category_tags") or [])
        out.append("")
        out.append("#### 技能 {}({})".format(sk["name"], tags))
        out.append("")
        for ss in sk.get("skill_stars") or []:
            out.append("- {} {}".format("★" * int(ss["star"]), strip_rich(ss.get("desc") or "")))
    return out


def gen_docs(roles: list, version: str) -> int:
    """产物1:每角色一档 markdown(同名多档按名合并,档位节列全部官方 id/费用)。"""
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    by_name: dict = {}
    for r in roles:
        by_name.setdefault(canon(r["name"]), []).append(r)
    for cname, entries in sorted(by_name.items()):
        ids = ", ".join(e["id"] for e in entries)
        costs = "/".join(e["rarity"] for e in entries)
        lines = [
            "---",
            f"name: {cname}",
            f"plaza_ids: {ids}",
            f"cost: {costs}",
            "position: {}".format(entries[0]["front_back_type"]),
            f"version: {version}",
            "generated_by: skills/sr-od-dev-currency-war/scripts/gen_plaza_chars.py",
            "---",
            "",
            f"# {cname}",
            "",
        ]
        for e in entries:
            hide = " · is_hide 隐藏条目" if e.get("is_hide") else ""
            expert = " · 专家顾问" if e.get("is_expert") else ""
            lines.append("## 档位 id={} {}费 {}{}{}".format(e["id"], e["rarity"], e["front_back_type"], hide, expert))
            lines.append("")
            lines.append("![icon]({})".format(e["icon"]))
            lines.append("")
            lines.extend(skill_block(e))
            lines.append("")
        (DOC_DIR / (f"{cname}.md")).write_text("\n".join(lines), encoding="utf-8")
    return len(by_name)


def check_fragment_vs_config(config_path: Path) -> None:
    """对拍:注册表段片段 vs config 快照,逐字段(63=63 归零才算过,不一致非零退出)。

    校验面:①片段文件往返解析完整(exec 收集 _ch 调用,防手改/截断);②片段与快照
    逐字段一致(name〔归一口径〕/cost/position/category_tags/羁绊三字段〔join
    trait_info_list,type-3 丢弃〕/is_hide/is_expert/source);③条数与 id 集合相等。
    由 --check-only 显式触发;main 默认产段不跑。
    """
    data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    data = data.get("data", data)
    version = data["rpg_game_big_version"]
    frag_path = PLAZA_DIR / f"registry_chars_v{version}.py"
    if not frag_path.exists():
        raise SystemExit(f"[check] 片段不存在:{frag_path}(先跑默认产段流程)")
    records: list[dict] = []

    def _ch(name: str, cost: int, position: str, category_tags: tuple[str, ...],
            factions: tuple[str, ...] = (), schools: tuple[str, ...] = (),
            independent: str = "", source: str = "", is_expert: bool = False,
            is_hide: bool = False) -> None:
        records.append({
            "name": name, "cost": cost, "position": position,
            "category_tags": tuple(category_tags), "factions": tuple(factions),
            "schools": tuple(schools), "independent": independent, "source": source,
            "is_expert": is_expert, "is_hide": is_hide,
        })

    exec(compile(frag_path.read_text(encoding="utf-8"), str(frag_path), "exec"), {"_ch": _ch})
    expected = derive_all(data["role_list"], trait_map(data))
    diffs: list[str] = []
    if len({r["source"] for r in records}) != len(records):
        diffs.append("片段存在重复 source 条目")
    by_src = {r["source"]: r for r in records}
    if len(records) != len(expected):
        diffs.append(f"条数不一致:片段 {len(records)} vs config {len(expected)}")
    for exp in expected:
        rec = by_src.get(exp["source"])
        if rec is None:
            diffs.append(f"{exp['source']} {exp['name']}: 片段缺此条")
            continue
        for k in ("name", "cost", "position", "category_tags", "factions", "schools",
                  "independent", "source", "is_expert", "is_hide"):
            if rec[k] != exp[k]:
                diffs.append(f"{exp['source']} {exp['name']}: {k} 片段={rec[k]!r} vs config={exp[k]!r}")
    for src in sorted(set(by_src) - {e["source"] for e in expected}):
        diffs.append(f"{src}: 片段多出而 config 无此条")
    print(f"\n[check] 片段({frag_path.name}) vs {config_path.name}(v{version}):")
    if diffs:
        print(f"[check] 不一致 {len(diffs)} 条:")
        for d in diffs:
            print(f"  - {d}")
        raise SystemExit(1)
    print(f"[check] 一致({len(records)}={len(expected)} 条,逐字段归零)")


def _config_ver_key(p: Path) -> tuple[int, int]:
    """config 快照文件名的版本序(数值比较,防 v4.10 字典序误排在 v4.7 前)。"""
    m = re.search(r"config_v(\d+)\.(\d+)", p.name)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def latest_config_path() -> Path:
    """plaza 缓存目录内最新版本 config 快照(--check-only 默认对拍锚)。"""
    cfgs = sorted(PLAZA_DIR.glob("config_v*.json"))
    if not cfgs:
        raise SystemExit(f"[check] 无 config 快照({PLAZA_DIR});先跑 plaza_fetch.py 或显式传 --config")
    return max(cfgs, key=_config_ver_key)


def gen_templates(roles: list) -> None:
    """产物2:官方立绘 SIFT 模板库(<规范名>/raw.png),**角色粒度单模板**。

    同名多档(升星升费)共用一目录:官方多档 icon URL 全同(视觉同图,档位归
    game state 职责);**底色取起始档 rarity**(升格档无独立模板,7 费缺 COST_BG
    档的问题随粒度裁定消解)。big_icon(RGBA 透明底 512x376)→ 烘焙成合成图:
    - 背景色 = 起始档费用色(常量见 ``COST_BG``,来源见其注释);
    - alpha>=128 掩码下 SIFT 只在角色本体提特征(生产 loader 同步支持 mask.png);
    - bbox 裁剪到角色本体。
    同步存 mask.png(alpha 二值)供 loader 用;源 RGBA 存 src.png 便重烘。
    幂等 = 官方图未变(src.png 字节比对)**且**重烘结果与现 raw.png 一致才跳过
    ——底色口径调整时下次重跑原位自愈重烘,无需删库。
    """
    import cv2
    import numpy as np

    TPL_DIR.mkdir(parents=True, exist_ok=True)
    start_tier: dict[str, dict] = {}
    for r in roles:
        cname = canon(r["name"])
        cur = start_tier.get(cname)
        if cur is None or int(r["rarity"]) < int(cur["rarity"]):
            start_tier[cname] = r  # 起始档 = rarity 最小的档(模板底色锚)
    n = 0
    n_skip = 0
    for r in start_tier.values():
        cname = canon(r["name"])
        big = r.get("big_icon") or ""
        if not big:
            continue
        dst = TPL_DIR / cname
        req = urllib.request.Request(big, headers={"User-Agent": HEADERS["User-Agent"], "Referer": HEADERS["Referer"]})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        rgba = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if rgba is None or rgba.ndim != 3 or rgba.shape[2] != 4:
            continue
        bg = COST_BG.get(int(r["rarity"]), COST_BG.get(3))
        if bg is None:
            continue
        a = rgba[:, :, 3:4].astype(np.float32) / 255.0
        rgb = (rgba[:, :, :3].astype(np.float32) * a + np.array(bg, dtype=np.float32).reshape(1, 1, 3) * (1 - a)).astype(np.uint8)
        mask = ((rgba[:, :, 3] >= 128) * 255).astype(np.uint8)
        ys, xs = np.where(mask > 0)
        if len(xs):
            rgb = rgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        raw_buf = cv2.imencode(".png", rgb)[1]
        src_png = dst / "src.png"
        raw_png = dst / "raw.png"
        if (src_png.exists() and src_png.read_bytes() == data
                and raw_png.exists() and raw_png.read_bytes() == bytes(raw_buf)):
            n_skip += 1  # 幂等:官方图未变且烘焙结果一致,跳过
            continue
        dst.mkdir(exist_ok=True)
        raw_buf.tofile(str(raw_png))
        cv2.imencode(".png", mask)[1].tofile(str(dst / "mask.png"))
        cv2.imencode(".png", rgba)[1].tofile(str(src_png))
        n += 1
    print(f"[tpl] 烘焙 {n} / 未变跳过 {n_skip} 角色(角色粒度 {len(start_tier)} 目录,"
          f"底色取起始档;费用色 {sorted(COST_BG.keys())})")


def gen_equip_templates(cfg: dict) -> None:
    """产物3:装备模板库 cw_equip_plaza(混合库,单 png <名>.png 与手工 cw_equip 同构)。

    组成:
    - plaza 进阶装备**普通版** art(去特权重复:特权 36 对与普通完全同图,SIFT 无法区分,
      特权靠 codex 金框 → 用手工模板):RGBA 透明底 → 深底合成,**保持原始分辨率不 resize**
      (用户 2026-08-15:烘焙缩放没必要,匹配时 multi-scale TM/SIFT 自适应;below-avatar
      的 scale 档按模板实际尺寸换算即可);
    - 手工 cw_equip 中名字不在 plaza 普通名集合的全部拷贝(简易装备 53 + 特权 36 等,
      plaza 无此数据/同图不可分)。

    匹配证据(2026-08-15):装备追踪弹窗 GT 3/3(内点 43/18/33 vs 手工 28/16/24);
    owned 列实拍进阶件 plaza≥手工(多检出列车同行星徽);简易件 plaza 无数据靠手工。
    """
    import shutil

    import cv2
    import numpy as np

    manual_dir = REPO / "assets/template/currency_war/equip_legacy"
    EQUIP_TPL_DIR.mkdir(parents=True, exist_ok=True)
    seen_url: dict = {}
    plaza_normal_names: set = set()
    failed: set = set()   # 下载/解码失败的 plaza 名(手工段 fallback 补)
    n_skip = 0
    for e in cfg["equipment_list"]:
        name = e["name"].replace(chr(0x2022), chr(0x00B7))
        is_priv = name.endswith(chr(0x00B7) + "特权")
        if is_priv:
            continue  # 特权与普通同 art(36 对实测同 icon URL),不进 plaza 集
        if e["icon"] in seen_url:
            continue
        seen_url[e["icon"]] = name
        plaza_normal_names.add(name)
        dst = EQUIP_TPL_DIR / (name + ".png")
        try:
            req = urllib.request.Request(e["icon"], headers={"User-Agent": HEADERS["User-Agent"], "Referer": HEADERS["Referer"]})
            with urllib.request.urlopen(req, timeout=20) as resp:
                rgba = cv2.imdecode(np.frombuffer(resp.read(), np.uint8), cv2.IMREAD_UNCHANGED)
        except Exception:
            failed.add(name)
            continue
        if rgba is None or rgba.ndim != 3:
            failed.add(name)
            continue
        if rgba.shape[2] == 4:
            a = rgba[:, :, 3:4].astype(np.float32) / 255.0
            rgb = (rgba[:, :, :3].astype(np.float32) * a + np.array((30, 30, 34), np.float32) * (1 - a)).astype(np.uint8)
            m = (rgba[:, :, 3] >= 128)
        else:
            # 少数官方 icon 本就无 alpha(治疗/持续伤害星徽,128x128x3 不透明)——直通,掩码全开
            rgb = rgba.copy()
            m = np.ones(rgba.shape[:2], bool)
        ys, xs = np.where(m)
        if len(xs):
            rgb = rgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        h, w = rgb.shape[:2]
        s = 98 / max(h, w)
        rgb = cv2.resize(rgb, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
        canvas = np.full((98, 98, 3), (30, 30, 34), np.uint8)
        oh, ow = rgb.shape[:2]
        canvas[(98 - oh) // 2:(98 - oh) // 2 + oh, (98 - ow) // 2:(98 - ow) // 2 + ow] = rgb
        ok, buf = cv2.imencode(".png", canvas)
        if ok and dst.exists() and dst.read_bytes() == bytes(buf):
            n_skip += 1  # 幂等:官方图未变,合成结果与现文件一致
            continue
        buf.tofile(dst)
    # 手工补充:名字不在 plaza 普通名的全部(简易/特权/合成件)
    # 命名对齐(2026-08-15):registry 的 财富(基础)/(强化) 共用手工 财富.png 两份拷贝;
    # plaza 的 诅咒·干将莫邪 为 registry 漏项(cw_equipment_data 生成器待补),模板照收。
    n_copy = 0
    alias: dict[str, str] = {"财富(基础)": "财富", "财富(强化)": "财富"}
    for png in sorted(manual_dir.glob("*.png")):
        if png.stem in plaza_normal_names or png.stem in alias.values():
            continue
        dst = EQUIP_TPL_DIR / png.name
        if not dst.exists():
            shutil.copyfile(png, dst)
            n_copy += 1
    for reg_name, manual_name in alias.items():
        src = manual_dir / (manual_name + ".png")
        dst = EQUIP_TPL_DIR / (reg_name + ".png")
        if src.exists() and not dst.exists():
            shutil.copyfile(src, dst)
            n_copy += 1
    if failed:
        raise RuntimeError(f"plaza 装备下载失败(保持统一官方,不 fallback 手工):{sorted(failed)}")
    print(f"[eqtpl] plaza {len(plaza_normal_names)} art(未变跳过 {n_skip}) + 手工补充 {n_copy} -> 共 {len(list(EQUIP_TPL_DIR.glob('*.png')))}")


def main() -> None:
    ap = argparse.ArgumentParser(description="CW plaza 官方接口 → 角色数据产物生成器")
    ap.add_argument("--check-only", action="store_true",
                    help="只跑「注册表段片段 vs config 快照」逐字段对拍,不产任何数据")
    ap.add_argument("--config", default="",
                    help="对拍用 config 快照路径(默认 = plaza 缓存目录最新 config_v*.json)")
    args = ap.parse_args()
    if args.check_only:
        cfg_path = Path(args.config) if args.config else latest_config_path()
        check_fragment_vs_config(cfg_path)
        return
    cfg = fetch_config()
    version = cfg.get("rpg_game_big_version", "?")
    roles = cfg["role_list"]
    fields = derive_all(roles, trait_map(cfg))
    n_bullet = sum(1 for r in roles if chr(0x2022) in r["name"])
    n = gen_docs(roles, version)
    print(f"[docs] {n} 角色 -> {DOC_DIR}")
    gen_templates(roles)
    print(f"[tpl] -> {TPL_DIR}")
    gen_equip_templates(cfg)
    print(f"[eqtpl] -> {EQUIP_TPL_DIR}")
    gen_registry_fragment(fields, version, n_bullet)
    gen_diff_report(roles, version)


if __name__ == "__main__":
    main()
