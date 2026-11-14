"""货币战争 · 羁绊(trait)聚合生成器(config 骨架 + 帖子聚合 + wiki 交叉验证)。

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

产出(中间产物,不落 src 数据层):
  - plaza 目录 traits_intermediate_v<版本>.json: 29 条 id 形态 Trait 全量
    (member_ids = role_ids 并集,未翻译;members 名字翻译与落库 cw_traits_data.py
    归生成器后续阶段);
  - 三源交叉报告(stdout,样本落 .debug/temp/currency_war/);
  - wiki 拉取缓存落 plaza 目录(重跑免网络;--refresh-wiki 强制重拉)。

对拍非零退出语义:骨架对拍(聚合 trait_name/trait_type vs config 逐键相等;基座有
而聚合无 layers = 覆盖报警)、全覆盖对拍(聚合条数与 id 集合 = config 34 − type3(5))、
count_mode 引文校验——任一不一致退出码 1。成员对拍(role_ids → 角色注册表翻译)归
翻译阶段,依赖 plaza id 查表契约,不在本脚本当前能力面。

用法(项目根):
  uv run python skills/sr-od-dev-currency-war/scripts/gen_traits.py [--refresh-wiki]
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
PLAZA_DIR = REPO / ".debug/game_data/currency_war/plaza"
REPORT_SAMPLE_DIR = REPO / ".debug/temp/currency_war"

TRAIT_TYPES_IN_SCOPE = (0, 1, 2)  # 0 阵营 / 1 流派 / 2 独立;type 3 不进本数据域
COUNT_MODE_DEFAULT = "TOTAL"
# count_mode 覆盖表(依据 = 官方 desc 三星计数句式;接线归策略批,此处只建模):
# 新增 STAR3 羁绊时人工裁定后在此补行,引文校验会同步核对 desc 文案。
COUNT_MODE_OVERRIDES: dict[str, str] = {"千星商会": "STAR3"}
STAR3_DESC_ANCHOR = "每上场1位3星"  # 三星计数句式锚,覆盖表与全集双向校验共用

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
    """中间产物:29 条 id 形态 Trait 全量 JSON(3.1 形态;翻译/落库归后续阶段)。"""
    PLAZA_DIR.mkdir(parents=True, exist_ok=True)
    path = PLAZA_DIR / f"traits_intermediate_v{version}.json"
    ordered = [products[tid] for tid in sorted(products)]
    payload = {
        "version": version,
        "generated_by": "skills/sr-od-dev-currency-war/scripts/gen_traits.py",
        "count": len(ordered),
        "traits": ordered,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[产物] 中间产物 {len(ordered)} 条(id 形态,含 count_mode) -> {path}")
    return path


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
    ap = argparse.ArgumentParser(description="CW 羁绊聚合生成器(config 骨架 + 帖子聚合 + wiki 交叉)")
    ap.add_argument("--config", default="", help="config 快照路径(默认 plaza 目录最新 config_v*.json)")
    ap.add_argument("--lineups", default="", help="帖 jsonl 路径(默认 plaza 目录 lineups_Hot.jsonl)")
    ap.add_argument("--refresh-wiki", action="store_true", help="强制重拉 wiki(默认缓存命中即用)")
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

    hard_diffs = skel_diffs + cov_diffs
    if hard_diffs:
        report.line(f"[result] FAIL——对拍不一致 {len(hard_diffs)} 条")
        write_intermediate(products, version)
        report.save(REPORT_SAMPLE_DIR / f"gen_traits_report_v{version}.txt")
        raise SystemExit(1)
    write_intermediate(products, version)
    report.line("[result] PASS——骨架/全覆盖对拍零 diff,count_mode 引文校验通过;"
                "wiki 差异见上(报告供人裁,不落数据)")
    report.save(REPORT_SAMPLE_DIR / f"gen_traits_report_v{version}.txt")


if __name__ == "__main__":
    main()
