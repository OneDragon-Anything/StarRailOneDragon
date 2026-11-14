"""货币战争 · 羁绊(trait)聚合生成器(config 骨架 + 帖子聚合 + 翻译对拍 + wiki 交叉)。

数据源(全部免登录,版本更新重跑前先重采到 .debug/game_data/currency_war/plaza/):
  1. plaza config 快照 config_v<版本>.json:
     - trait_info_list 34 条骨架(trait_id/trait_name/trait_icon/trait_type 有值,
       layers/role_ids/simple_desc 恒空——服务端刻意只下发骨架,参数变体实测无效,
       勿再试);过滤 trait_type in (0,1,2) = 29 条基座(type 3 = 400xxx 五条为
       主角光环专属效果,不进本数据域);
     - role_property_list: property type → 属性中文名(富文本渲染映射表);
     - role_list[].trait_details[]: 羁绊 desc 引文源(count_mode 校验用;
       trait_info_list 的 simple_desc 实测空串不可用)。
  2. lineups_Hot.jsonl: 攻略广场 Hot 帖聚合——帖内 tourn_detail.role_stages[]
     .traits[] 是唯一全结构源(layers/role_ids/simple_desc 有值);is_activated/
     current_role_count 为帖相对值、remarks 为术语注释,均无消费面,不采。
  3. 米游社 wiki 频道 240(羁绊) 27 词条: 社区维护,交叉验证只出报告不落数据。

聚合规则:
  - 按 trait_id 分桶;去重 = len(layers) 最大的帖,并列取 created_at 新者——
    旧帖降级快照实测存在(v4.7 千星商会旧帖仅 1 层且 desc 空串:发帖时刻服务端存
    当时配置快照,游戏数据更新后旧帖不回填);
  - role_ids 取各帖并集(成员名单跨帖互补);
  - layers[].trait_desc / simple_desc 富文本渲染为纯文本,管线沿用旧
    gen_factions.py 的 render_rich:<property type=X display=all> → 属性中文名 /
    display=icon 删除 / <color> 删除;未知标签保留原文 + 警告不静默。

count_mode 判定(建模不接线):29 条默认 TOTAL;覆盖表仅千星商会 = STAR3(官方 desc
「每上场1位3星【千星商会】角色,将激活1级羁绊效果」);覆盖表逐条带 desc 引文校验,
文案漂移即非零退出。板面计数接线归策略批,本脚本只落数据字段。

翻译与成员对拍(查表契约 = 派生形态,design.md §2.3):
  - 运行期从角色注册表 CHARACTERS 派生 plaza id → 规范名映射({c.source: c.name}),
    只读注册表不落数据文件,禁建脱离注册表的平行索引(手工表/独立数据源/硬编码
    名单);覆盖对拍守卫:派生映射键 ⊇ config role_list 全部条目 id(含升格高费
    档等例外档,B1),不符非零退出;
  - role_ids → 规范名:同名多档合并(成员是「角色」非「档位」);is_hide 条目
    过滤(members = 可组队员口径,召唤物不算成员——预裁 B2;被过滤 id 进报告);
    fail-closed:任一 id 翻不出 → 打印该 id 并非零退出,禁静默丢弃;
  - 成员对拍(集合全等):trait.members vs 注册表自报派生(factions+schools+
    independent 含该羁绊名的角色集合);差异两类(官方多出/自报多出)逐条人裁
    ——放行进例外清单(键 = (trait_id, role_id),首版为空待人裁)或修注册表。

产出:
  - plaza 目录 traits_intermediate_v<版本>.json: 29 条 id 形态 Trait 全量
    (member_ids = role_ids 并集原始形态;members 名字形态是运行期派生字段,
    唯一出口 = 渲染产物,不回写中间产物);
  - cw_traits_data.py 全文: 默认 dry-run -> .debug/temp/currency_war/ 预览
    (子进程 uv run 按真实模块名 import 烟测,失败非零退出);--land 落库
    src/sr_od/application/currency_war/data/cw_traits_data.py(同一渲染函数
    产物,与预览逐字一致;烟测按 src 真身完整模块名导入);
  - 三源交叉报告 + 成员对拍报告(stdout,样本落 .debug/temp/currency_war/);
  - wiki 拉取缓存落 plaza 目录(重跑免网络;--refresh-wiki 强制重拉)。

对拍非零退出语义:骨架对拍(聚合 trait_name/trait_type vs config 逐键相等;基座有
而聚合无 layers = 覆盖报警)、全覆盖对拍(聚合条数与 id 集合 = config 34 − type3(5))、
count_mode 引文校验、查表覆盖守卫、翻译 fail-closed、成员对拍未裁决差异、is_hide
口径漂移——任一不一致退出码 1。

用法(项目根):
  uv run python skills/sr-od-dev-currency-war/scripts/gen_traits.py [--land] [--refresh-wiki]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))  # 翻译/成员对拍查角色注册表(先例 gen_factions.py)
PLAZA_DIR = REPO / ".debug/game_data/currency_war/plaza"
REPORT_SAMPLE_DIR = REPO / ".debug/temp/currency_war"
# 落库目标(--land):src 数据层真身;模块导入路径 = sr_od.application.currency_war.data
LAND_TARGET = REPO / "src/sr_od/application/currency_war/data/cw_traits_data.py"

from sr_od.application.currency_war.data.cw_chars import CHARACTERS  # noqa: E402

TRAIT_TYPES_IN_SCOPE = (0, 1, 2)  # 0 阵营 / 1 流派 / 2 独立;type 3 不进本数据域
COUNT_MODE_DEFAULT = "TOTAL"
# count_mode 覆盖表(依据 = 官方 desc 三星计数句式;接线归策略批,此处只建模):
# 新增 STAR3 羁绊时人工裁定后在此补行,引文校验会同步核对 desc 文案。
COUNT_MODE_OVERRIDES: dict[str, str] = {"千星商会": "STAR3"}
STAR3_DESC_ANCHOR = "每上场1位3星"  # 三星计数句式锚,覆盖表与全集双向校验共用

# 成员对拍例外清单(键 = (trait_id, role_id),值 = 裁决理由;同旧 gen_factions
# MEMBER_EXCEPTIONS 模式)。首版为空待人裁——差异逐条人工裁决后才补行,禁自行填充:
#   - 官方多出(role_id 翻译名不在注册表自报集合):键 = 译出该名的非隐藏 role_id
#     全集,放行 = 该名从 members 排除(理由须声明非成员依据,如召唤物);
#   - 自报多出(注册表自报含、帖 role_ids 未含):键 = 该名全部档位 id,放行 =
#     members 不变;
#   - 同名多档角色须逐档 id 各补一行,全档在清单才放行(部分裁决 = 未裁决);
#   - 修注册表路线 = 改 cw_chars.py 后重跑本脚本(不走例外清单)。
MEMBER_EXCEPTIONS: dict[tuple[str, str], str] = {}

WIKI_LIST_URL = (
    "https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1"
    "/home/content/list?app_sn=sr_wiki&channel_id=240&lang=zh-cn"
)
WIKI_INFO_URL = (
    "https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1"
    "/content/info?app_sn=sr_wiki&content_id={cid}"
)
WIKI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://bbs.mihoyo.com/sr/wiki/",
}

PROP_TAG_RE = re.compile(r"<property\s+type=(\S+?)(?:\s+display=(\S+?))?>")
# variableproperty 标签族(v4.7 出现,如召唤羁绊的召唤力图标):自闭合无闭合标签,
# display=icon 语义与 property 同(纯图标,文本语义在其后文字里)
VARPROP_TAG_RE = re.compile(r"<variableproperty\s+name=(\S+?)(?:\s+display=(\S+?))?>")
COLOR_TAG_RE = re.compile(r"</?color(?:=[^>]*)?>")
ANY_TAG_RE = re.compile(r"<[^>]+>")

# wiki「羁绊分级效果」节:每层行以「<层数>：」开头(层数序号是结构标记非效果数值,
# 数值词比对前剥除,防聚合侧报缺);冒号全角半角混用实测存在(千星商会全用半角、
# 开拓银轨首行全角余行半角),字符类兼容
WIKI_GRADE_SECTION_RE = re.compile(r"<h2>羁绊分级效果</h2>(.*?)(?:<h2>|$)", re.S)
WIKI_GRADE_LINE_RE = re.compile(r"^(\d+)[：:]", re.M)
NUM_WORD_RE = re.compile(r"\d+(?:\.\d+)?%?")


def canon(name: str) -> str:
    """名字归一(U+2022 • 统一 U+00B7 ·),wiki 词条名与官方名的对齐规则。"""
    return name.replace(chr(0x2022), chr(0x00B7))


def render_rich(rich: str, prop_map: dict[str, str]) -> tuple[str, list[str]]:
    """富文本 → 可读纯文本。返回 (渲染文本, 警告列表);警告调用方须打印不静默。"""
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

    def _varprop(m: re.Match[str]) -> str:
        display = m.group(2)
        if display == "icon":
            return ""  # 纯图标,语义同 property display=icon
        warns.append(f"unknown variableproperty name={m.group(1)} display={display}")
        return m.group(0)

    out = COLOR_TAG_RE.sub("", rich)
    out = PROP_TAG_RE.sub(_prop, out)
    out = VARPROP_TAG_RE.sub(_varprop, out)
    out = out.replace("\\n", "\n")  # 帖内 JSON 的字面 \n 还原为真换行
    for m in ANY_TAG_RE.finditer(out):  # 渲染后仍残留的未知标签
        warns.append(f"unknown tag {m.group(0)[:40]}")
    return out.strip(), warns


def load_prop_map(cfg: dict) -> dict[str, str]:
    """config role_property_list → property type → 属性中文名映射表。"""
    prop_map: dict[str, str] = {}
    for p in cfg.get("role_property_list") or []:
        if p.get("property_type") and p.get("name"):
            prop_map[p["property_type"]] = p["name"]
    return prop_map


def build_skeleton(cfg: dict) -> dict[str, dict]:
    """骨架基座:trait_info_list 过滤 type 0/1/2,官方字段零转写直接采用。"""
    skeleton: dict[str, dict] = {}
    for t in cfg["trait_info_list"]:
        if int(t["trait_type"]) not in TRAIT_TYPES_IN_SCOPE:
            continue
        skeleton[t["trait_id"]] = {
            "trait_id": t["trait_id"],
            "trait_name": t["trait_name"],
            "trait_type": int(t["trait_type"]),
            "trait_icon": t["trait_icon"],
        }
    return skeleton


def aggregate_posts(
    lineups_path: Path, skeleton: dict[str, dict], prop_map: dict[str, str],
) -> tuple[dict[str, dict], list[str]]:
    """帖内 traits 按 trait_id 聚合。

    返回 ({trait_id: 聚合记录}, 警告列表)。去重 = len(layers) 最大,并列取
    created_at 新者;role_ids 并集;layers/simple_desc 富文本渲染为纯文本。
    帖内 trait_name/trait_icon/trait_type 不采——骨架对拍另行校验一致性,
    产物字段单一源自 config 骨架。
    """
    warns: list[str] = []
    best: dict[str, tuple[int, int, list, str]] = {}  # tid -> (层数, created_at, layers, simple_desc)
    role_ids_all: dict[str, set[str]] = {}
    n_posts = 0
    with lineups_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            post = json.loads(line)
            n_posts += 1
            created_at = int(post.get("created_at") or 0)
            stages = (post.get("tourn_detail") or {}).get("role_stages") or []
            for stage in stages:
                for t in stage.get("traits") or []:
                    tid = t["trait_id"]
                    role_ids_all.setdefault(tid, set()).update(t.get("role_ids") or [])
                    if tid not in skeleton:
                        # 帖内出现骨架外 id = 数据异常(如 type 3 出帖),报警不采
                        warns.append(f"帖内 trait {tid}({t.get('trait_name')}) 不在骨架过滤集,跳过")
                        continue
                    layers = t.get("layers") or []
                    key = (len(layers), created_at)
                    cur = best.get(tid)
                    if cur is None or key > (cur[0], cur[1]):
                        best[tid] = (len(layers), created_at, layers, t.get("simple_desc") or "")

    products: dict[str, dict] = {}
    for tid, base in skeleton.items():
        rec = best.get(tid)
        if rec is None:
            # 基座有而聚合无 = 覆盖不足,骨架对拍报警;此处仍产出无 layers 条目占位
            products[tid] = {**base, "layers": [], "member_ids": [], "simple_desc": ""}
            continue
        _, _, layers_raw, simple_desc_raw = rec
        layers_out: list[dict] = []
        for lr in layers_raw:
            desc, ws = render_rich(lr.get("trait_desc") or "", prop_map)
            warns.extend(f"{base['trait_name']}(layer {lr.get('layer')}): {w}" for w in ws)
            layers_out.append({
                "layer": int(lr["layer"]),
                "quality": int(lr.get("quality") or 0),
                "trait_desc": desc,
            })
        layers_out.sort(key=lambda x: x["layer"])
        simple_desc, ws = render_rich(simple_desc_raw, prop_map)
        warns.extend(f"{base['trait_name']}(simple_desc): {w}" for w in ws)
        products[tid] = {
            **base,
            "layers": layers_out,
            "member_ids": sorted(role_ids_all.get(tid) or set()),
            "simple_desc": simple_desc,
        }
    print(f"[聚合] {n_posts} 帖 → {len(products)} trait 分桶(骨架 {len(skeleton)} 条)"
          f";layers 覆盖 {sum(1 for p in products.values() if p['layers'])}/{len(products)}")
    return products, warns


def collect_trait_descs(cfg: dict, prop_map: dict[str, str]) -> dict[str, set[str]]:
    """config role_list[].trait_details[] → {trait_id: {渲染后 desc}}。

    同一 trait 被多个角色条目引用,desc 同源;集合形态容忍空串重复。
    """
    descs: dict[str, set[str]] = {}
    for r in cfg.get("role_list") or []:
        for td in r.get("trait_details") or []:
            tid = td["id"]
            text, _ = render_rich(td.get("desc") or "", prop_map)
            descs.setdefault(tid, set()).add(text)
    return descs


def check_count_mode(
    skeleton: dict[str, dict], descs_by_tid: dict[str, set[str]],
) -> None:
    """count_mode 覆盖表双向引文校验,不符即非零退出(防版本文案漂移后口径过期)。

    - 覆盖表内名字:骨架必须有此羁绊,且其 desc 含三星计数句式锚;
    - 其余羁绊:desc 不得出现三星计数句式——出现即新 STAR3 候选,人裁后补覆盖表。
    """
    id_by_name = {b["trait_name"]: tid for tid, b in skeleton.items()}
    for name, mode in COUNT_MODE_OVERRIDES.items():
        tid = id_by_name.get(name)
        if tid is None:
            raise SystemExit(f"[count_mode] 覆盖表条目 {name!r} 不在骨架 {len(skeleton)} 条内"
                             f"(改名/消失?人工复核覆盖表)")
        if mode != "STAR3":
            raise SystemExit(f"[count_mode] 覆盖表 {name}: 未知口径 {mode!r}(合法值 TOTAL/STAR3)")
        descs = descs_by_tid.get(tid) or set()
        if not any(STAR3_DESC_ANCHOR in d for d in descs):
            raise SystemExit(f"[count_mode] {name}: desc 引文校验失败——未命中句式"
                             f"「{STAR3_DESC_ANCHOR}」(版本文案可能已变,人工复核)")
    for tid, base in skeleton.items():
        if base["trait_name"] in COUNT_MODE_OVERRIDES:
            continue
        if any(STAR3_DESC_ANCHOR in d for d in descs_by_tid.get(tid) or set()):
            raise SystemExit(f"[count_mode] {base['trait_name']}: desc 出现三星计数句式"
                             f"「{STAR3_DESC_ANCHOR}」但不在覆盖表——新 STAR3 候选,人工裁定")


def apply_count_mode(products: dict[str, dict]) -> None:
    """产物落 count_mode 字段:默认 TOTAL,覆盖表逐名显式覆盖。"""
    for p in products.values():
        p["count_mode"] = COUNT_MODE_OVERRIDES.get(p["trait_name"], COUNT_MODE_DEFAULT)


def crosscheck_skeleton(products: dict[str, dict], skeleton: dict[str, dict]) -> list[str]:
    """骨架对拍:聚合产物 trait_name/trait_type vs config 逐键相等;无 layers = 覆盖报警。"""
    diffs: list[str] = []
    for tid, base in skeleton.items():
        p = products.get(tid)
        if p is None:
            diffs.append(f"{tid} {base['trait_name']}: 基座有而聚合无")
            continue
        if p["trait_name"] != base["trait_name"]:
            diffs.append(f"{tid}: trait_name 聚合={p['trait_name']!r} vs 骨架={base['trait_name']!r}")
        if p["trait_type"] != base["trait_type"]:
            diffs.append(f"{tid}: trait_type 聚合={p['trait_type']} vs 骨架={base['trait_type']}")
        if not p["layers"]:
            diffs.append(f"{tid} {base['trait_name']}: 基座有而聚合无 layers(帖子覆盖报警)")
    return diffs


def crosscheck_full_coverage(products: dict[str, dict], cfg: dict) -> list[str]:
    """全覆盖对拍:聚合条数与 id 集合 = config 34 − type3(5)。"""
    scope_ids = {t["trait_id"] for t in cfg["trait_info_list"]
                 if int(t["trait_type"]) in TRAIT_TYPES_IN_SCOPE}
    product_ids = set(products)
    diffs: list[str] = []
    if len(products) != len(scope_ids):
        diffs.append(f"条数不等:聚合 {len(products)} vs config 过滤后 {len(scope_ids)}")
    for tid in sorted(scope_ids - product_ids):
        diffs.append(f"{tid}: config 有而聚合缺")
    for tid in sorted(product_ids - scope_ids):
        diffs.append(f"{tid}: 聚合有而 config 无")
    return diffs


# ===== 翻译与成员对拍(3.2;查表契约 = 派生形态,design.md §2.3)=====


def derive_source_map() -> tuple[dict[str, str], set[str]]:
    """运行期从角色注册表派生 plaza id → 规范名映射与隐藏 id 集。

    查表契约 = 派生形态:只读 CHARACTERS、不落数据文件(映射与注册表本体信息量
    相同,角色批不交付索引符号);禁建脱离注册表的平行索引。隐藏集 = is_hide=True
    条目(members 可组队员口径的过滤锚,B2)。
    """
    source_map = {c.source: c.name for c in CHARACTERS}
    hidden_ids = {c.source for c in CHARACTERS if c.is_hide}
    return source_map, hidden_ids


def check_source_coverage(
    source_map: dict[str, str], cfg: dict,
) -> tuple[list[str], list[str]]:
    """覆盖对拍守卫(B1):派生映射键 ⊇ config role_list 全部条目 id。

    缺失行非空 = 调用方非零退出——例外档 id(升格高费档等)缺失会使帖聚合
    role_ids 翻译漏员,与翻译 fail-closed 同语义;注册表多出 id 只报告不拦
    (注册表超前 config 快照的版本倾斜信号,不影响翻译)。
    返回 (缺失差异行, 注册表多出 id 清单)。
    """
    cfg_ids = {str(r["id"]) for r in cfg.get("role_list") or []}
    missing = sorted(cfg_ids - set(source_map))
    rows = [f"config role_list id {rid} 不在注册表派生映射(角色批未同步?)"
            for rid in missing]
    return rows, sorted(set(source_map) - cfg_ids)


def translate_members(
    products: dict[str, dict], source_map: dict[str, str], hidden_ids: set[str],
) -> tuple[list[tuple[str, str, str]], dict[str, list[str]], str]:
    """role_ids → 规范名翻译,产物落 products[tid]['members'](名字升序 list)。

    - fail-closed:任一 id 翻不出 → 记入 unknown 供调用方打印并非零退出,禁
      静默丢弃(成员缺失 = 对拍与策略双双失真);
    - is_hide 过滤 = 可组队员口径(B2 预裁:召唤物不算成员),被过滤 id 记入
      hidden_filtered 供对拍报告列证据;
    - 同名多档合并:翻译后按名去重(成员是「角色」非「档位」)。
    返回 (hidden_filtered[(trait_id, role_id, 规范名)],
          unknown{trait_id: [id]}, 合并事件报告句)。
    """
    hidden_filtered: list[tuple[str, str, str]] = []
    unknown: dict[str, list[str]] = {}
    merge_names: set[str] = set()
    for tid, p in products.items():
        names: set[str] = set()
        by_name: dict[str, set[str]] = {}
        for rid in p["member_ids"]:
            name = source_map.get(rid)
            if name is None:
                unknown.setdefault(tid, []).append(rid)
                continue
            by_name.setdefault(name, set()).add(rid)
            if rid in hidden_ids:
                hidden_filtered.append((tid, rid, name))
                continue  # 可组队员口径:隐藏条目不入 members
            names.add(name)
        p["members"] = sorted(names)
        merge_names.update(n for n, rids in by_name.items() if len(rids) > 1)
    note = (f"同名多档合并 {len(merge_names)} 名: {sorted(merge_names)}"
            if merge_names else "无多档 id 合并事件")
    return hidden_filtered, unknown, note


def check_hidden_consistency(
    cfg: dict, hidden_ids: set[str], source_map: dict[str, str],
) -> tuple[list[str], set[str]]:
    """is_hide 口径一致性:注册表派生隐藏集 vs config role_list is_hide 集。

    members 过滤锚取注册表(查表契约 = 派生形态);config 侧为同源官方字段,
    交叉核对防两份数据版本漂移——漂移时隐藏口径含糊会静默污染 members,差异
    行归成员对拍硬差异面(非零退出待人裁)。
    返回 (差异行, config 隐藏 id 集)。
    """
    cfg_hidden = {str(r["id"]) for r in cfg.get("role_list") or [] if r.get("is_hide")}
    rows = [f"config is_hide {rid}({source_map.get(rid, '?')}) 注册表 is_hide=False——隐藏口径漂移"
            for rid in sorted(cfg_hidden - hidden_ids)]
    rows += [f"注册表 is_hide {rid}({source_map.get(rid, '?')}) config is_hide=False——隐藏口径漂移"
             for rid in sorted(hidden_ids - cfg_hidden)]
    return rows, cfg_hidden


def derive_bond_index(
    hidden_ids: set[str],
) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    """注册表自报派生:羁绊名 → 成员名集合(factions+schools+independent 含该名)。

    is_hide 同滤(可组队员口径对对拍两侧对称,B2);name_sources = 名字 → 全部
    档位 source id(自报多出差异的例外键候选域,只含非隐藏条目——隐藏 id 的
    成员差集已由 B2 预裁,不进例外清单键空间)。
    """
    bond_index: dict[str, set[str]] = {}
    name_sources: dict[str, list[str]] = {}
    for c in CHARACTERS:
        if c.source in hidden_ids:
            continue
        name_sources.setdefault(c.name, []).append(c.source)
        born = set(c.factions) | set(c.schools)
        if c.independent:
            born.add(c.independent)
        for b in born:
            bond_index.setdefault(b, set()).add(c.name)
    return bond_index, name_sources


def crosscheck_members(
    products: dict[str, dict], source_map: dict[str, str], hidden_ids: set[str],
    bond_index: dict[str, set[str]], name_sources: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """成员对拍(集合全等,trait-data-layer.md §3):members vs 注册表自报派生。

    差异两类,例外清单键 = (trait_id, role_id),放行须同名全部键皆在清单
    (部分裁决 = 未裁决,差异保持可见):
    - 官方多出(members 有、自报无):键 = 译出该名的非隐藏 role_id 全集;放行
      = 该名从 members 排除(理由须声明非成员依据);
    - 自报多出(自报有、members 无):键 = 该名全部档位 id;放行 = members 不变。
    返回 (报告行, 未裁决差异行);未裁决差异非空 = 调用方非零退出待人裁。
    """
    info_rows: list[str] = []
    hard_rows: list[str] = []
    for tid, p in sorted(products.items()):
        name = p["trait_name"]
        left, right = set(p["members"]), bond_index.get(name, set())
        for m in sorted(left - right):
            rids = sorted(rid for rid in p["member_ids"]
                          if source_map.get(rid) == m and rid not in hidden_ids)
            if rids and all((tid, rid) in MEMBER_EXCEPTIONS for rid in rids):
                p["members"] = [x for x in p["members"] if x != m]
                reasons = sorted({MEMBER_EXCEPTIONS[(tid, rid)] for rid in rids})
                info_rows.append(f"{name} ⊃ {m}: 例外放行({' / '.join(reasons)};members 已排除)")
            else:
                hard_rows.append(f"{tid} {name}: 官方成员 {m}(role_ids {rids})不在注册表自报集合")
        for m in sorted(right - left):
            rids = sorted(name_sources.get(m) or [])
            if rids and all((tid, rid) in MEMBER_EXCEPTIONS for rid in rids):
                reasons = sorted({MEMBER_EXCEPTIONS[(tid, rid)] for rid in rids})
                info_rows.append(f"{name} ⊅ {m}: 例外放行({' / '.join(reasons)})")
            else:
                hard_rows.append(f"{tid} {name}: 注册表自报成员 {m}(ids {rids})不在帖聚合 members")
    return info_rows, hard_rows


def fetch_wiki(refresh: bool, version: str) -> tuple[list[dict], dict[str, str]]:
    """wiki 频道 240 清单 + 逐词条「羁绊分级效果」纯文本,带本地缓存。

    返回 ([{content_id, title}], {title: grading_text})。缓存落 plaza 目录,
    重跑免网络;refresh=True 强制重拉。
    """
    list_cache = PLAZA_DIR / f"wiki_trait_list_v{version}.json"
    details_cache = PLAZA_DIR / f"wiki_trait_details_v{version}.json"
    if not refresh and list_cache.exists() and details_cache.exists():
        items = json.loads(list_cache.read_text(encoding="utf-8"))
        details = json.loads(details_cache.read_text(encoding="utf-8"))
        print(f"[wiki] 缓存命中 {len(items)} 词条({list_cache.name});--refresh-wiki 可强制重拉")
        return items, details

    def _get(url: str) -> dict:
        req = urllib.request.Request(url, headers=WIKI_HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            d = json.loads(resp.read())
        if d.get("retcode") != 0:
            raise RuntimeError(f"wiki retcode={d.get('retcode')} msg={d.get('message')}")
        return d["data"]

    raw = _get(WIKI_LIST_URL)
    items: list[dict] = []
    for sub in raw.get("list") or []:
        for it in sub.get("list") or []:
            items.append({"content_id": int(it["content_id"]), "title": canon(it["title"])})
    items.sort(key=lambda x: x["content_id"])
    details: dict[str, str] = {}
    for it in items:
        data = _get(WIKI_INFO_URL.format(cid=it["content_id"]))
        contents = ((data.get("content") or {}).get("contents")) or []
        grading = ""
        for c in contents:
            grading = parse_wiki_grading(c.get("text") or "")
            if grading:
                break
        details[it["title"]] = grading
        if not grading:
            print(f"[wiki] ⚠ 词条 {it['title']}({it['content_id']}) 未解析到「羁绊分级效果」节")
    PLAZA_DIR.mkdir(parents=True, exist_ok=True)
    list_cache.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    details_cache.write_text(json.dumps(details, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[wiki] 拉取 {len(items)} 词条详情(缓存 -> {list_cache.name} / {details_cache.name})")
    return items, details


def parse_wiki_grading(text: str) -> str:
    """词条详情 HTML → 「羁绊分级效果」节纯文本(按 <p> 分行,剥标签)。"""
    m = WIKI_GRADE_SECTION_RE.search(text)
    if not m:
        return ""
    paras = re.findall(r"<p[^>]*>(.*?)</p>", m.group(1), re.S)
    lines = []
    for p in paras:
        s = re.sub(r"<br\s*/?>", "\n", p)
        s = re.sub(r"<[^>]+>", "", s)
        s = s.strip()
        if s:
            lines.append(s)
    return "\n".join(lines)


def compare_wiki(
    products: dict[str, dict], items: list[dict], details: dict[str, str],
) -> tuple[list[str], list[str]]:
    """wiki 交叉验证(包含性比对,差异只进报告供人裁,不判失败不落数据)。

    比对维度 = 档数一致 + 数值词命中;数值词 = 双方文本中「数字(含小数)+ 可选
    百分号」串的集合(wiki 为社区改写,不要求逐字相等)。返回 (缺收清单, 比对差异行)。
    """
    product_by_name = {p["trait_name"]: p for p in products.values()}
    wiki_names = {it["title"] for it in items}
    missing_in_wiki = sorted(set(product_by_name) - wiki_names)  # wiki 缺收
    only_in_wiki = sorted(wiki_names - set(product_by_name))  # wiki 独有(帖聚合外词条)
    rows: list[str] = []
    n_diff = 0
    for it in items:
        title = it["title"]
        p = product_by_name.get(title)
        wiki_text = details.get(title) or ""
        if p is None:
            rows.append(f"- {title}: wiki 独有词条(帖聚合无此羁绊,共 {len(only_in_wiki)} 个),人工核对归属")
            n_diff += 1
            continue
        if not wiki_text:
            rows.append(f"- {title}: wiki 无分级效果文本,跳过比对")
            n_diff += 1
            continue
        agg_layers = p["layers"]
        wiki_grades = WIKI_GRADE_LINE_RE.findall(wiki_text)
        if len(agg_layers) != len(wiki_grades):
            rows.append(f"- {title}: 档数 聚合={len(agg_layers)} vs wiki={len(wiki_grades)}")
            n_diff += 1
        # 数值词差集:剥 wiki 分级行首层数序号(结构标记,聚合侧在 layers[].layer)
        wiki_nums = set(NUM_WORD_RE.findall(WIKI_GRADE_LINE_RE.sub("", wiki_text)))
        agg_text = "\n".join(lr["trait_desc"] for lr in agg_layers)
        agg_nums = set(NUM_WORD_RE.findall(agg_text))
        agg_missing = sorted(agg_nums - wiki_nums, key=lambda x: (len(x), x))
        wiki_missing = sorted(wiki_nums - agg_nums, key=lambda x: (len(x), x))
        if agg_missing or wiki_missing:
            parts = []
            if agg_missing:
                parts.append(f"聚合有 wiki 缺 {agg_missing}")
            if wiki_missing:
                parts.append(f"wiki 有聚合缺 {wiki_missing}")
            rows.append(f"- {title}: 数值词差集({'; '.join(parts)})")
            n_diff += 1
    return missing_in_wiki, rows


def write_intermediate(products: dict[str, dict], version: str) -> Path:
    """中间产物:29 条 id 形态 Trait 全量 JSON。

    id 形态契约:member_ids = role_ids 并集原始形态;members(翻译名字形态)是
    运行期派生字段,不回写中间产物——名字形态唯一出口 = 渲染预览/落库文件。
    """
    PLAZA_DIR.mkdir(parents=True, exist_ok=True)
    path = PLAZA_DIR / f"traits_intermediate_v{version}.json"
    ordered = [{k: v for k, v in products[tid].items() if k != "members"}
               for tid in sorted(products)]
    payload = {
        "version": version,
        "generated_by": "skills/sr-od-dev-currency-war/scripts/gen_traits.py",
        "count": len(ordered),
        "traits": ordered,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[产物] 中间产物 {len(ordered)} 条(id 形态,含 count_mode) -> {path}")
    return path


# ===== cw_traits_data.py 全文渲染与落库(dry-run 预览 / --land 落库)=====


def _tuple_lit(items: list[str]) -> str:
    """字符串字面量清单 → 单行元组字面量(单元素补尾逗号,空集为 ())。"""
    if not items:
        return "()"
    inner = ", ".join(items)
    return f"({inner},)" if len(items) == 1 else f"({inner})"


def render_traits_module(products: dict[str, dict], version: str) -> str:
    """cw_traits_data.py 全文渲染(纯字符串拼装,无副作用;落盘调用方定)。

    结构契约 = trait-data-layer.md §1:Trait/TraitLayer dataclass + TRAITS
    (trait_id 键)+ trait_by_name(名字键,模块级派生不复制数据);members =
    可组队员口径(已翻译/合并/过滤)。desc 类全文用 repr() 产字面量——官方文本
    含换行与引号,repr 保证字面量合法且不可注入;键序 = trait_id 升序(重跑
    确定性)。E501 已豁免(pyproject extend-ignore),长行沿 cw_invest_data
    生成文件惯例。
    """
    dq = '"""'
    entries: list[str] = []
    for tid in sorted(products):
        p = products[tid]
        if p["layers"]:
            layer_body = ",\n".join(
                f"            TraitLayer(layer={lr['layer']}, quality={lr['quality']},"
                f" trait_desc={lr['trait_desc']!r})"
                for lr in p["layers"]
            )
            layers_lit = f"layers=(\n{layer_body},\n        )"
        else:
            layers_lit = "layers=()"
        members_lit = _tuple_lit([repr(m) for m in p["members"]])
        entries.append(
            f"    {tid!r}: Trait(\n"
            f"        trait_id={tid!r},\n"
            f"        trait_name={p['trait_name']!r},\n"
            f"        trait_type={p['trait_type']},\n"
            f"        {layers_lit},\n"
            f"        members={members_lit},\n"
            f"        simple_desc={p['simple_desc']!r},\n"
            f"        trait_icon={p['trait_icon']!r},\n"
            f"        count_mode={p['count_mode']!r},\n"
            f"    ),"
        )
    body = "\n".join(entries)
    return (
        "# 警告:本文件由 skills/sr-od-dev-currency-war/scripts/gen_traits.py 生成"
        f"(v{version} 帖子聚合 + config 骨架 + wiki 交叉),勿手编;\n"
        "# 版本更新重跑生成。重跑: uv run python"
        " skills/sr-od-dev-currency-war/scripts/gen_traits.py\n"
        f"{dq}货币战争 羁绊(trait)数据(官方口径镜像;生成器产物,勿手编)。\n"
        "\n"
        f"{len(products)} 条(trait_type 0/1/2;type 3 主角光环专属不进本域)。\n"
        "TRAITS 键 = trait_id(稳定机器键:跨版本 diff/对拍/资产映射);\n"
        "trait_by_name 键 = trait_name(消费侧标签键型)。\n"
        f"{dq}\n"
        "from __future__ import annotations\n"
        "\n"
        "from dataclasses import dataclass\n"
        "\n"
        "\n"
        "@dataclass(frozen=True)\n"
        "class TraitLayer:\n"
        '    """羁绊分层效果条目(官方 layers[] 镜像)。"""\n'
        "    layer: int        # 官方 layers[].layer:激活所需人数档\n"
        "    quality: int      # 官方 layers[].quality:档品质\n"
        "    trait_desc: str   # 官方 layers[].trait_desc:分层效果全文(富文本已渲染为纯文本)\n"
        "\n"
        "\n"
        "@dataclass(frozen=True)\n"
        "class Trait:\n"
        '    """单个羁绊条目(官方口径镜像;生成器产物,修正进设计后重跑生成器)。"""\n'
        "    trait_id: str                  # 官方 trait_id(稳定机器键:跨版本 diff/对拍/资产映射)\n"
        "    trait_name: str                # 官方 trait_name(消费侧标签键型)\n"
        "    trait_type: int                # 官方 trait_type:0 阵营 / 1 流派 / 2 独立\n"
        "    layers: tuple[TraitLayer, ...] # 官方 layers[] 投影(layer 升序)\n"
        "    members: tuple[str, ...]       # 成员角色规范名(官方 role_ids 经角色注册表翻译;同名多档合并)\n"
        "    simple_desc: str               # 官方总效果简述\n"
        "    trait_icon: str                # 官方 trait_icon URL\n"
        '    count_mode: str = "TOTAL"      # 激活计数控:TOTAL=总上场人数 / STAR3=三星上场人数\n'
        "\n"
        "    @property\n"
        "    def tiers(self) -> tuple[int, ...]:\n"
        '        """激活阈值投影(官方 layers[].layer;兼容既有激活判定消费键型)。"""\n'
        "        return tuple(layer.layer for layer in self.layers)\n"
        "\n"
        "\n"
        "TRAITS: dict[str, Trait] = {\n"
        f"{body}\n"
        "}\n"
        "\n"
        "# members 口径(可组队员,B2):官方 role_ids 经角色注册表翻译,is_hide=True\n"
        "# 条目过滤(召唤物不算成员——腾荒类隐藏随从帖内 role_ids 有名但不入玩家\n"
        "# 编队),同名多档合并为角色;与官方 role_ids 的差集进成员对拍例外清单人裁。\n"
        "# 召唤型激活特例(双龙吟类激活 = 上场成员 + 后台召唤物,通用人数计数不适用)\n"
        "# 与 count_mode 接线同批归策略批,板面计数接线批须按羁绊特例处理。\n"
        "trait_by_name: dict[str, Trait] = {t.trait_name: t for t in TRAITS.values()}\n"
    )


def write_traits_preview(text: str) -> Path:
    """dry-run 预览落盘(文件名与目标模块一致,烟测按顶层模块名导入;不落 src)。

    落库真身 = land_traits_module(--land):同一渲染函数产物,与预览逐字一致。
    """
    path = REPORT_SAMPLE_DIR / "cw_traits_data.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[产物] cw_traits_data.py 全文预览({len(text)} 字符,dry-run 不落 src) -> {path}")
    return path


def land_traits_module(text: str) -> Path:
    """--land 落库:渲染全文写入 src 数据层真身。

    纯写入不做内容加工——落库内容 = 渲染产物本身,幂等性由渲染确定性保证
    (键序 trait_id 升序、无时间戳):连续落库两次字节一致;落库后由调用方
    以 src 真身完整模块名跑 import 烟测。
    """
    path = LAND_TARGET
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[落库] cw_traits_data.py 全文落 src({len(text)} 字符) -> {path}")
    return path


def smoke_import_data_module(sys_path: Path, module: str) -> None:
    """数据模块 import 烟测:子进程 uv run 按真实模块名导入,验证数据层合法可导入。

    sys_path/module 显式传入:dry-run 传预览目录 + 顶层模块名(预览目录插
    sys.path[0],src 落了同名模块也先命中预览,烟测对象恒为本跑产物);落库传
    src 根 + 完整包路径(烟测对象 = 落库真身,连带校验父包导入链)。
    断言 = TRAITS 与 trait_by_name 键数一致 + 名字索引回指同对象 + tiers 投影
    自洽(结构不变量守卫测试落仓
    sr-od-test/test/sr_od/application/currency_war/data/test_cw_traits_data.py)。
    """
    code = (
        "import sys\n"
        f"sys.path.insert(0, r'{sys_path}')\n"
        f"import {module} as m\n"
        "assert len(m.TRAITS) == len(m.trait_by_name)\n"
        "assert all(t.trait_name == n and m.TRAITS[t.trait_id] is t"
        " for n, t in m.trait_by_name.items())\n"
        "assert all(t.tiers == tuple(l.layer for l in t.layers)"
        " for t in m.TRAITS.values())\n"
        "print('import OK: TRAITS=%d trait_by_name=%d' % (len(m.TRAITS), len(m.trait_by_name)))\n"
    )
    proc = subprocess.run(
        ["uv", "run", "python", "-c", code], cwd=REPO,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit(f"[烟测] {module} import 失败({sys_path}):\n{proc.stdout}\n{proc.stderr}")


def _config_ver_key(p: Path) -> tuple[int, int]:
    """config 快照文件名的版本序(数值比较,防 v4.10 字典序误排在 v4.7 前)。"""
    m = re.search(r"config_v(\d+)\.(\d+)", p.name)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def latest_config_path() -> Path:
    """plaza 缓存目录内最新版本 config 快照。"""
    cfgs = sorted(PLAZA_DIR.glob("config_v*.json"))
    if not cfgs:
        raise SystemExit(f"无 config 快照({PLAZA_DIR});先重采或显式传 --config")
    return max(cfgs, key=_config_ver_key)


class Report:
    """stdout 同步收行的报告器(收行落样本文件,验收凭据)。"""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def line(self, text: str = "") -> None:
        print(text)
        self.lines.append(text)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        print(f"[报告] 样本 -> {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="CW 羁绊聚合生成器(config 骨架 + 帖子聚合 + 翻译对拍 + wiki 交叉)")
    ap.add_argument("--config", default="", help="config 快照路径(默认 plaza 目录最新 config_v*.json)")
    ap.add_argument("--lineups", default="", help="帖 jsonl 路径(默认 plaza 目录 lineups_Hot.jsonl)")
    ap.add_argument("--refresh-wiki", action="store_true", help="强制重拉 wiki(默认缓存命中即用)")
    ap.add_argument("--land", action="store_true",
                    help="落库:全文写入 src/sr_od/application/currency_war/data/cw_traits_data.py"
                         "(默认 dry-run 只落 temp 预览,不碰 src)")
    args = ap.parse_args()

    cfg_path = Path(args.config) if args.config else latest_config_path()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    cfg = cfg.get("data", cfg)
    version = cfg["rpg_game_big_version"]
    lineups_path = Path(args.lineups) if args.lineups else PLAZA_DIR / "lineups_Hot.jsonl"
    report = Report()

    skeleton = build_skeleton(cfg)
    prop_map = load_prop_map(cfg)
    report.line(f"[骨架] {cfg_path.name} trait_info_list 34 条,过滤 type {TRAIT_TYPES_IN_SCOPE}"
                f" → {len(skeleton)} 条基座;prop_map {len(prop_map)} 项")

    products, render_warns = aggregate_posts(lineups_path, skeleton, prop_map)

    descs_by_tid = collect_trait_descs(cfg, prop_map)
    check_count_mode(skeleton, descs_by_tid)
    apply_count_mode(products)
    star3 = [p["trait_name"] for p in products.values() if p["count_mode"] == "STAR3"]
    report.line(f"[count_mode] 覆盖表 {len(COUNT_MODE_OVERRIDES)} 条引文校验通过;STAR3 = {star3},"
                f"其余 {len(products) - len(star3)} 条 TOTAL")

    skel_diffs = crosscheck_skeleton(products, skeleton)
    report.line("[对拍-骨架] 聚合 trait_name/trait_type vs config 逐键:")
    if skel_diffs:
        for d in skel_diffs:
            report.line(f"  ✗ {d}")
    else:
        report.line(f"  ✓ 一致({len(skeleton)} 键,layers 覆盖无报警)")

    cov_diffs = crosscheck_full_coverage(products, cfg)
    report.line("[对拍-全覆盖] 聚合条数与 id 集合 vs config 34 − type3(5):")
    if cov_diffs:
        for d in cov_diffs:
            report.line(f"  ✗ {d}")
    else:
        report.line(f"  ✓ 一致({len(products)} = {len(skeleton)} 条)")

    # ---- 翻译与成员对拍(3.2):查表契约派生形态 ----
    source_map, hidden_ids = derive_source_map()
    guard_rows, reg_extra_ids = check_source_coverage(source_map, cfg)
    n_cfg_roles = len(cfg.get("role_list") or [])
    report.line(f"[查表] 覆盖守卫:注册表派生映射 {len(source_map)} id vs config role_list {n_cfg_roles} id:")
    for d in guard_rows:
        report.line(f"  ✗ {d}")
    if reg_extra_ids:
        report.line(f"  - 注册表多出(config 无,版本倾斜仅报告): {reg_extra_ids}")
    if guard_rows:
        report.line("[result] FAIL——查表覆盖守卫不符")
        write_intermediate(products, version)
        report.save(REPORT_SAMPLE_DIR / f"gen_traits_report_v{version}.txt")
        raise SystemExit(1)
    report.line("  ✓ 派生映射 ⊇ config role_list 全部 id")

    hidden_rows, cfg_hidden = check_hidden_consistency(cfg, hidden_ids, source_map)
    hidden_filtered, unknown_by_tid, merge_note = translate_members(products, source_map, hidden_ids)
    if unknown_by_tid:
        report.line("[翻译] FAIL-CLOSED——以下 role_id 翻译失败(角色未建/已删?),禁静默丢弃:")
        for tid, rids in sorted(unknown_by_tid.items()):
            report.line(f"  ✗ {products[tid]['trait_name']}({tid}): {rids}")
        write_intermediate(products, version)
        report.save(REPORT_SAMPLE_DIR / f"gen_traits_report_v{version}.txt")
        raise SystemExit(1)
    report.line(f"[翻译] {len(products)} 条 role_ids → 规范名;{merge_note};"
                f"is_hide 过滤 {len(hidden_filtered)} 处:")
    for tid, rid, name in hidden_filtered:
        report.line(f"  - {products[tid]['trait_name']}({tid}): 过滤 {rid} {name}"
                    "(is_hide=True,可组队员口径;B2 预裁=召唤物不算成员)")
    if not hidden_filtered:
        report.line("  - 无")
    report.line(f"[查表] is_hide 口径核对(注册表派生 {sorted(hidden_ids)} vs config {sorted(cfg_hidden)}):")
    if hidden_rows:
        for d in hidden_rows:
            report.line(f"  ✗ {d}")
    else:
        report.line("  ✓ 一致")

    bond_index, name_sources = derive_bond_index(hidden_ids)
    member_info_rows, member_hard_rows = crosscheck_members(
        products, source_map, hidden_ids, bond_index, name_sources)
    report.line("[对拍-成员] trait.members vs 注册表自报派生(factions+schools+independent;集合全等):")
    for r in member_info_rows:
        report.line(f"  {r}")
    if member_hard_rows:
        for d in member_hard_rows:
            report.line(f"  ✗ {d}")
    else:
        report.line(f"  ✓ 一致({len(products)} 键;例外清单 {len(MEMBER_EXCEPTIONS)} 条,首版待人裁)")

    items, details = fetch_wiki(args.refresh_wiki, version)
    ids = [it["content_id"] for it in items]
    contiguous = ids == list(range(ids[0], ids[-1] + 1)) if ids else False
    report.line(f"[wiki] 频道 240 共 {len(items)} 词条,content_id {ids[0]}-{ids[-1]}"
                f"({'连续' if contiguous else '不连续,人工复核'})")
    missing_in_wiki, wiki_rows = compare_wiki(products, items, details)
    report.line(f"[wiki] 缺收清单(聚合有 wiki 无,共 {len(missing_in_wiki)} 条):")
    for name in missing_in_wiki:
        report.line(f"  - {name}")
    report.line(f"[wiki] 比对差异 {sum(1 for r in wiki_rows if r)} 行(社区改写,人裁不落数据):")
    for r in wiki_rows:
        if r:
            report.line(f"  {r}")

    if render_warns:
        uniq = sorted(set(render_warns))
        report.line(f"[渲染] 警告 {len(render_warns)} 处(去重 {len(uniq)} 种,未知标签/属性需补档):")
        for w in uniq:
            report.line(f"  - {w}")
    else:
        report.line("[渲染] 无警告,全部富文本标签已解析")

    hard_diffs = skel_diffs + cov_diffs + hidden_rows + member_hard_rows
    if hard_diffs:
        report.line(f"[result] FAIL——对拍不一致 {len(hard_diffs)} 条(骨架 {len(skel_diffs)}"
                    f"/全覆盖 {len(cov_diffs)}/隐藏口径 {len(hidden_rows)}"
                    f"/成员 {len(member_hard_rows)})")
        write_intermediate(products, version)
        report.save(REPORT_SAMPLE_DIR / f"gen_traits_report_v{version}.txt")
        raise SystemExit(1)
    write_intermediate(products, version)
    module_text = render_traits_module(products, version)
    preview_path = write_traits_preview(module_text)
    smoke_import_data_module(preview_path.parent, "cw_traits_data")
    report.line(f"[烟测] cw_traits_data.py 预览 import 通过 -> {preview_path}")
    if args.land:
        land_path = land_traits_module(module_text)
        smoke_import_data_module(REPO / "src", "sr_od.application.currency_war.data.cw_traits_data")
        report.line(f"[落库] {land_path}(src 真身完整模块名 import 烟测通过)")
    report.line("[result] PASS——骨架/全覆盖/成员对拍零 diff,count_mode 引文校验通过;"
                "wiki 差异见上(报告供人裁,不落数据);"
                + ("已落库 src 数据层,预览落 temp 供比对"
                   if args.land else "预览 dry-run 落 temp(--land 落库 src)"))
    report.save(REPORT_SAMPLE_DIR / f"gen_traits_report_v{version}.txt")


if __name__ == "__main__":
    main()
