"""货币战争 · plaza 实战阵容统计生成器(match_hard 高难帖聚合;版本更新重跑)。

数据源(免登录公开 API,同 plaza_fetch.py):
  POST {BASE}/game/lineup/index  body 含 match_hard=true(高难/A8 实战筛选)
  BASE = https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game
  (必需 header x-rpc-currencywar-tourn: tourn;cursor 分页;Recommend 排序空返回,只支持 Hot)

产出(**同源双产物,双向链接,均勿手编**):
  1. ``src/sr_od/application/currency_war/cw_plaza_comps.py`` —— 代码侧(机器消费):
     ``PLAZA_CARRY_CLUSTERS``(按 carry 聚类 n≥5 的实战统计:羁绊/常驻角色/carry 装备/
     节奏标签/投资策略/环境偏好/3星率/样本量/use 权重)+ ``PLAZA_GLOBAL``(全局 meta:
     羁绊频次/装备频次/合成首选/过渡单位池/星级费用档/label 词表/开拓者形态)。
  2. ``docs/game/currency_war/data/plaza_meta.md`` —— 人读版(表格,供 COMP_LIBRARY 手判层校准)。

两层架构(同 gen_plaza_invest.py ADR-0150 模式):本生成器只管 **base 事实层**(784 篇玩家帖
聚合的客观频次);手判层(strength/form_difficulty/star_goals 曲线取舍)在 ``cw_comps.py``
COMP_LIBRARY 手维护 —— 代码 ``plaza_carry`` 字段是两层的对拍锚点。

过滤规则(防污染):
  - ``rpg_game_big_version == "4.4"``(列表混旧版帖);
  - ``create_by_env != "TournLineupEnv_KOLSandbox"``(官方演示非玩家实战);
  - ``is_expired / is_sub_expired`` 剔除。
canon 规则(同 gen_plaza_chars.py):plaza 名 ``•``(U+2022)→``·``(U+00B7);开拓者
8009=开拓者·欢愉 / 8007=开拓者·记忆;换形态按 ``switch_role_map`` 映射(终局 8009→8007)。
召唤物 id(12041/12042 景元神君变体)只入羁绊计数不入 roster —— 本聚合只消费 role_stages
roster 字段,天然隔离;神君不计 carry/units。

用法(项目根):
  uv run python tools/cw/gen_plaza_comps.py            # 在线拉取 + 生成
  uv run python tools/cw/gen_plaza_comps.py --cache    # 用本地最新 jsonl 缓存(离线)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[2]
DATA_PY = REPO / "src/sr_od/application/currency_war/cw_plaza_comps.py"
DOC_MD = REPO / "docs/game/currency_war/data/plaza_meta.md"
CACHE = Path(".debug/temp/currency_war/plaza/lineups_HotHard.jsonl")
CONFIG_GLOB = ".debug/temp/currency_war/plaza/config_v*.json"

BASE = "https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game"
HEADERS = {
    "Content-Type": "application/json",
    "x-rpc-currencywar-tourn": "tourn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://act.miyoushe.com/",
    "Origin": "https://act.miyoushe.com",
}
GEN_CMD = "uv run python tools/cw/gen_plaza_comps.py"
MIN_CLUSTER_N = 5   # carry 聚类最小样本量(低于不入库,长尾见 doc 汇总)

TRAILBLAZER = {"8009": "开拓者·欢愉", "8007": "开拓者·记忆"}


def canon(r: dict) -> str:
    rid = str(r.get("id") or "")
    if rid in TRAILBLAZER:
        return TRAILBLAZER[rid]
    return (r.get("name") or "").replace(chr(0x2022), chr(0x00B7))


# ===== 采集 =====

def fetch_pages(pages: int = 200, sleep_s: float = 0.4) -> list:
    """在线拉取 match_hard 攻略列表(cursor 分页拉到尽,去重)。"""
    items: list = []
    token = ""
    seen: set = set()
    for page in range(1, pages + 1):
        body = {
            "game": "hkrpg", "page": str(page), "limit": "10",
            "lineup_type": "Tourn", "next_page_token": token,
            "role_ids": [], "trait_ids": [], "match_change_job": False,
            "match_hard": True, "order": "Hot",
        }
        req = urllib.request.Request(f"{BASE}/lineup/index", data=json.dumps(body).encode(), headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            d = json.loads(resp.read())
        if d.get("retcode") != 0:
            raise RuntimeError(f"lineup/index p{page} retcode={d.get('retcode')} msg={d.get('message')}")
        data = d["data"]
        got = data.get("list") or []
        new = [x for x in got if x["id"] not in seen]
        seen.update(x["id"] for x in new)
        items.extend(new)
        token = data.get("next_page_token") or ""
        if not new or not token:
            break
        time.sleep(sleep_s)
    print(f"[fetch] {len(items)} 篇(高难 Hot)")
    return items


def filter_valid(items: list) -> tuple[list, str]:
    """版本/KOL/过期过滤(规则见模块 docstring)。

    版本目标**从官方 config 缓存推导**(``config_v*.json`` 的 ``rpg_game_big_version``),
    非硬编码 —— 版本更新重跑 config 子命令后本生成器自动对齐新版本,旧版帖(3.7-4.3 等)
    全部拦截,防静默污染。
    """
    cands = sorted(REPO.glob(CONFIG_GLOB))
    if not cands:
        raise RuntimeError("无 config 缓存(先跑 plaza_fetch.py config),版本目标无从推导")
    version = json.loads(cands[-1].read_text(encoding="utf-8")).get("rpg_game_big_version")
    if not version:
        raise RuntimeError(f"config 缓存 {cands[-1].name} 无 rpg_game_big_version 字段")
    out = []
    dropped_ver = dropped_kol = dropped_exp = 0
    for x in items:
        td = x.get("tourn_detail") or {}
        if td.get("rpg_game_big_version") != version:
            dropped_ver += 1
            continue
        if td.get("create_by_env") == "TournLineupEnv_KOLSandbox":
            dropped_kol += 1
            continue
        if td.get("is_expired") or td.get("is_sub_expired"):
            dropped_exp += 1
            continue
        out.append(x)
    print(f"[filter] 目标版本 V{version}(config 推导): {len(items)} -> {len(out)} 有效"
          f"(弃 旧版{dropped_ver} KOL{dropped_kol} 过期{dropped_exp})")
    return out, version


# ===== 聚合 =====

def use_of(x: dict) -> int:
    return int((x.get("game_data") or {}).get("recent_interact", {}).get("use") or 0)


def final_stage(td: dict) -> dict:
    for st in td["role_stages"]:
        if st["stage"] == "Final":
            return st
    return td["role_stages"][-1]


def stage_units(st: dict, switch: dict) -> list:
    units = []
    for pos_key, pos in (("front", st.get("front_roles") or []), ("back", st.get("back_roles") or [])):
        for r in pos:
            rid = str(r.get("id") or "")
            rid_sw = switch.get(rid, rid)
            name = TRAILBLAZER.get(rid_sw) or canon(r)
            units.append({"name": name, "star": r.get("star", 1), "is_carry": bool(r.get("is_carry")),
                          "rarity": int(r.get("rarity") or 0), "pos": pos_key})
    return units


def post_record(x: dict) -> dict:
    """单帖 → 聚合字段(Final 视角 + 全阶段)。"""
    td = x["tourn_detail"]
    switch: dict = {}
    for st in td["role_stages"]:
        switch.update({str(k): str(v) for k, v in (st.get("switch_role_map") or {}).items()})
    fin = final_stage(td)
    units = stage_units(fin, switch)
    traits = []
    for t in fin.get("traits") or []:
        acts = [ly.get("layer") for ly in t.get("layers", []) if ly.get("is_activated")]
        if acts and max(acts) >= 2:
            traits.append(t["trait_name"])
    equips: dict[str, list[str]] = defaultdict(list)
    for r in [*(fin.get("front_roles") or []), *(fin.get("back_roles") or [])]:
        for key in ("first_equipments", "second_equipments"):
            for e in r.get(key) or []:
                equips[canon(r)].append((e.get("name") or "").replace(chr(0x2022), chr(0x00B7)))
    return {
        "use": use_of(x),
        "units": units, "traits": traits, "equips": dict(equips),
        "augs": [a.get("name", "").replace(chr(0x2022), chr(0x00B7))
                 for a in [*(td.get("first_fight_augments") or []), *(td.get("second_fight_augments") or [])]],
        "portals": [p.get("title", "") for p in td.get("portals") or []],
        "labels": [lb.get("text", "") for lb in td.get("labels") or []],
        "switch": switch,
        "early": [u["name"] for u in stage_units(td["role_stages"][0], switch)],
        "craft_first": (td.get("order_compose") or [{}])[0].get("name", ""),
        "basic_first": (td.get("order_basic") or [{}])[0].get("name", ""),
    }


def aggregate(posts: list) -> tuple[list, dict]:
    """按 carry 聚类(n≥MIN_CLUSTER_N)+ 全局统计。"""
    recs = [post_record(x) for x in posts]
    clusters: dict[str, list] = defaultdict(list)
    for p in recs:
        for u in p["units"]:
            if u["is_carry"]:
                clusters[u["name"]].append(p)

    out = []
    for carry, ps in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        if len(ps) < MIN_CLUSTER_N:
            continue
        trait_c = Counter(t for p in ps for t in p["traits"])
        unit_c = Counter(u["name"] for p in ps for u in p["units"])
        carry_eq = Counter(e for p in ps for e in p["equips"].get(carry, []))
        aug_c = Counter(a for p in ps for a in p["augs"])
        label_c = Counter(lb for p in ps for lb in p["labels"])
        portal_c = Counter(pt for p in ps for pt in p["portals"])
        carry_units = [u for p in ps for u in p["units"] if u["name"] == carry]
        out.append({
            "carry": carry, "n_posts": len(ps), "total_use": sum(p["use"] for p in ps),
            "carry_star3_rate": round(sum(1 for u in carry_units if u["star"] >= 3) / max(len(carry_units), 1), 2),
            "traits": trait_c.most_common(10),
            "units": [(k, v) for k, v in unit_c.most_common(12) if k != carry],
            "carry_equips": carry_eq.most_common(8),
            "augs": aug_c.most_common(8),
            "labels": label_c.most_common(5),
            "portals": portal_c.most_common(5),
        })

    star_by_cost: dict[int, list] = defaultdict(lambda: [0, 0])
    for p in recs:
        for u in p["units"]:
            if not u["is_carry"] or not u["rarity"]:
                continue
            star_by_cost[u["rarity"]][1] += 1
            if u["star"] >= 3:
                star_by_cost[u["rarity"]][0] += 1
    switch_c = Counter(f"{TRAILBLAZER.get(k, k)}->{TRAILBLAZER.get(v, v)}" for p in recs for k, v in p["switch"].items())
    glob = {
        "n_posts": len(posts),
        "trait_freq": Counter(t for p in recs for t in p["traits"]).most_common(),
        "equip_freq": Counter(e for p in recs for es in p["equips"].values() for e in es).most_common(50),
        "craft_first": Counter(p["craft_first"] for p in recs if p["craft_first"]).most_common(20),
        "basic_first": Counter(p["basic_first"] for p in recs if p["basic_first"]).most_common(15),
        "early_units": Counter(u for p in recs for u in p["early"]).most_common(25),
        "label_freq": Counter(lb for p in recs for lb in p["labels"]).most_common(),
        "switch_freq": switch_c.most_common(6),
        "star3_by_cost": {str(c): round(s / max(n, 1), 2) for c, (s, n) in sorted(star_by_cost.items())},
        "n_clusters": len(out),
    }
    return out, glob


# ===== 渲染 =====

def _tup(pairs: list) -> str:
    return "(" + ", ".join(f"({k!r}, {v})" for k, v in pairs) + ",)" if pairs else "()"


def render_data(version_tag: str, clusters: list, glob: dict) -> str:
    lines = [
        f"# 警告:本文件由 tools/cw/gen_plaza_comps.py 生成(plaza lineup/index match_hard,{version_tag}),勿手编。",
        f"# 重跑: {GEN_CMD}",
        "# 同源产物(人读版,COMP_LIBRARY 手判层校准用): docs/game/currency_war/data/plaza_meta.md",
        '# 手判层(勿混): src/sr_od/application/currency_war/cw_comps.py COMP_LIBRARY(strength/form_difficulty/level_plan)。',
        '"""货币战争 plaza 实战 comp 统计(高难玩家帖聚合,gen_plaza_comps.py 生成)。',
        "",
        f"{glob['n_posts']} 篇 V4.4 高难帖(v4.4 + 非KOL沙盒 + 未过期过滤),按 Final 阶段 carry 聚类 {glob['n_clusters']} 个(n≥{MIN_CLUSTER_N})。",
        "频次字段语义:X×N = N 篇帖中出现;star3_by_cost = carry 费用档 3 星率(星级目标先验)。",
        '装备只记 Final 阶段(编辑器 UI 限制,非玩法事实——目标套装);合成时序看 PLAZA_GLOBAL["craft_first"]。',
        '"""',
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True)",
        "class PlazaCarryCluster:",
        '    """单个 carry 主C的实战聚类(base 事实层;判断语义在 cw_comps.py 手判层)。"""',
        "    carry: str",
        "    n_posts: int",
        "    total_use: int                       # 被使用次数合计(可信度权重;头部帖才有计数)",
        "    carry_star3_rate: float              # carry 终局 3 星率(星级目标先验)",
        "    traits: tuple[tuple[str, int], ...]      # Final 激活羁绊频次(核心+次要混排)",
        "    units: tuple[tuple[str, int], ...]       # 常驻角色频次(不含 carry)",
        "    carry_equips: tuple[tuple[str, int], ...]  # carry 装备频次(Final 目标套装)",
        "    augs: tuple[tuple[str, int], ...]        # 投资策略实选频次(两轮合并)",
        "    labels: tuple[tuple[str, int], ...]      # 节奏标签(5/6/7级搜牌/速升8/9)",
        "    portals: tuple[tuple[str, int], ...]     # 投资环境偏好",
        "",
        "",
        "PLAZA_CARRY_CLUSTERS: tuple[PlazaCarryCluster, ...] = (",
    ]
    for c in clusters:
        lines.append(
            f"    PlazaCarryCluster(carry={c['carry']!r}, n_posts={c['n_posts']}, total_use={c['total_use']},\n"
            f"        carry_star3_rate={c['carry_star3_rate']},\n"
            f"        traits={_tup(c['traits'])},\n"
            f"        units={_tup(c['units'])},\n"
            f"        carry_equips={_tup(c['carry_equips'])},\n"
            f"        augs={_tup(c['augs'])},\n"
            f"        labels={_tup(c['labels'])},\n"
            f"        portals={_tup(c['portals'])}),"
        )
    lines += [")", "", "PLAZA_GLOBAL: dict = {"]
    for key in ("n_posts", "n_clusters", "trait_freq", "equip_freq", "craft_first", "basic_first",
                "early_units", "label_freq", "switch_freq", "star3_by_cost"):
        lines.append(f"    {key!r}: {glob[key]!r},")
    lines += [
        "}",
        "",
        "",
        "def cluster_by_carry() -> dict[str, PlazaCarryCluster]:",
        '    """carry 名 → 聚类(n≥5)。"""',
        "    return {c.carry: c for c in PLAZA_CARRY_CLUSTERS}",
        "",
        "",
        "def early_transition_pool() -> dict[str, int]:",
        '    """Early(位面1)阶段单位频次 —— 全局过渡池先验(ADR-0149 消费)。"""',
        '    return dict(PLAZA_GLOBAL["early_units"])',
        "",
        "",
        "def default_star_goal(cost: int) -> int:",
        '    """费用档默认星目标(plaza carry 3星率:1费~0.76 / 2费~0.81 / 3费~0.87 / 4费~0.58 / 5费~0.37)。"""',
        "    return 3 if cost <= 3 else 2",
        "",
    ]
    return "\n".join(lines)


def render_doc(version_tag: str, clusters: list, glob: dict) -> str:
    lines = [
        "---",
        f"version: {version_tag}",
        "generated_by: tools/cw/gen_plaza_comps.py",
        "related_code: src/sr_od/application/currency_war/cw_plaza_comps.py",
        "---",
        "",
        "# 货币战争 plaza 实战 meta(人读版)",
        "",
        f"> **由 `tools/cw/gen_plaza_comps.py` 生成,勿手编**(plaza lineup/index match_hard 高难帖,重跑:`{GEN_CMD}`)。",
        "> 代码侧(机器消费):`src/sr_od/application/currency_war/cw_plaza_comps.py` —— 同源生成、双向链接。",
        "> 用途:`cw_comps.py COMP_LIBRARY` 手判层(strength/form_difficulty/level_plan)的校准对拍源。",
        "",
        f"{glob['n_posts']} 篇 V4.4 高难玩家帖(过滤 v4.4 + 非KOL沙盒 + 未过期),{glob['n_clusters']} 个 carry 聚类(n≥{MIN_CLUSTER_N})。",
        "",
        "## carry 聚类总表",
        "",
        "| carry | 篇数 | use合计 | 3星率 | 核心羁绊(频次) | carry 装备 top | 主节奏 |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in clusters:
        traits = "、".join(f"{k}×{v}" for k, v in c["traits"][:4])
        eqs = "、".join(f"{k}×{v}" for k, v in c["carry_equips"][:4])
        label = c["labels"][0][0] if c["labels"] else "-"
        lines.append(f"| {c['carry']} | {c['n_posts']} | {c['total_use']} | {c['carry_star3_rate']} | {traits} | {eqs} | {label} |")
    lines += [
        "",
        "## 全局统计",
        "",
        "### 羁绊频次(Final 激活)",
        "",
    ]
    lines.append("、".join(f"{k}×{v}" for k, v in glob["trait_freq"]))
    lines += ["", "### 装备频次(Final 目标套装;时序见合成首选)", ""]
    lines.append("、".join(f"{k}×{v}" for k, v in glob["equip_freq"][:30]))
    lines += ["", "### 合成首选(order_compose[0])", ""]
    lines.append("、".join(f"{k}×{v}" for k, v in glob["craft_first"]))
    lines += ["", "### 基础件首选(order_basic[0])", ""]
    lines.append("、".join(f"{k}×{v}" for k, v in glob["basic_first"]))
    lines += ["", "### Early(位面1)过渡单位池", ""]
    lines.append("、".join(f"{k}×{v}" for k, v in glob["early_units"]))
    lines += ["", "### 节奏标签词表", ""]
    lines.append("、".join(f"{k}×{v}" for k, v in glob["label_freq"]))
    lines += ["", "### carry 费用档 3 星率(星级目标先验)", ""]
    lines.append("、".join(f"{c}费={r}" for c, r in glob["star3_by_cost"].items()))
    lines += ["", "### 开拓者终局形态(switch)", ""]
    lines.append("、".join(f"{k}×{v}" for k, v in glob["switch_freq"]))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 plaza 实战 comp 统计(数据层)")
    parser.add_argument("--cache", action="store_true", help="用本地 lineups_HotHard.jsonl(离线)")
    args = parser.parse_args()

    if args.cache:
        if not CACHE.exists():
            raise RuntimeError("无本地缓存,去掉 --cache 在线拉")
        items = [json.loads(ln) for ln in CACHE.open(encoding="utf-8")]
        print(f"[cache] {len(items)} 篇")
    else:
        items = fetch_pages()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE.open("w", encoding="utf-8") as f:
            for x in items:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")

    posts, version = filter_valid(items)
    if not posts:
        raise RuntimeError("过滤后为空,检查数据源")
    clusters, glob = aggregate(posts)
    version_tag = f"V{version}"
    DATA_PY.write_text(render_data(version_tag, clusters, glob), encoding="utf-8")
    DOC_MD.write_text(render_doc(version_tag, clusters, glob), encoding="utf-8")
    print(f"[data] {len(clusters)} 聚类 <- {DATA_PY.relative_to(REPO)}")
    print(f"[doc ] -> {DOC_MD.relative_to(REPO)}")


if __name__ == "__main__":
    main()
