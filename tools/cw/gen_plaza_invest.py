"""货币战争 · plaza 官方接口 → 投资策略/环境 base 数据生成器(版本更新重跑)。

数据源(免登录公开 API,同 plaza_fetch.py):
  GET https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config?game=hkrpg
  (必需 header x-rpc-currencywar-tourn: tourn)
  取 ``fight_augment_list``(投资策略)/``portal_list``(投资环境)。

产出 ``src/sr_od/application/currency_war/cw_invest_data.py``(勿手编):
  ``PLAZA_AUGMENTS`` / ``PLAZA_PORTALS`` —— 数字 id 为稳定主键;name 经 canon 归一为
  注册表键(OCR 友好形);effect 为官方效果全文(去富文本标签,保换行)。

两层架构(ADR-0150):本生成器只管 **base 事实层**(名字/品质/效果,API 直出);
人工建模增量(economy 数值化/评估分/环境分类/阵营绑定/补遗条目)在
``cw_investments.py`` 手维护,合并层应用 —— 版本更新 = 重跑本脚本 + 按 diff 报告
核对 overlay 孤儿键(测试 test_cw_invest_registry 有守卫)。

canon 键归一(显式小表,勿扩大):
  - ``•``(U+2022)→``·``(U+00B7,与角色侧一致);
  - 全角冒号/逗号 → 半角(live OCR 实测读半角:战术专家:佩拉);叹号/问号**不动**
    (无实测证据,保持官方原样);
  - 去空格(``摸个鱼吧 III``→``摸个鱼吧III``,对齐既有键);
  - 罗马数字 Ⅰ/Ⅱ/Ⅲ → 拉丁 I/II/III(对齐既有键);
  - ``剎``→``刹``(游戏真名为刹,OCR 常见形变剎 → 键用真名,形变走 LCS 兜底)。

用法(项目根):
  uv run python tools/cw/gen_plaza_invest.py            # 在线拉取 + 生成 + diff
  uv run python tools/cw/gen_plaza_invest.py --cache    # 用本地最新 config 缓存(离线调试)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
DATA_PY = REPO / "src/sr_od/application/currency_war/cw_invest_data.py"
CACHE_GLOB = ".debug/temp/currency_war/plaza/config_v*.json"

CONFIG_URL = "https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config?game=hkrpg"
HEADERS = {
    "x-rpc-currencywar-tourn": "tourn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://act.miyoushe.com/",
}

_QUALITY: dict[int, str] = {1: "银", 2: "金", 3: "棱彩"}
_CHAR_MAP: dict[str, str] = {
    "•": "·", "：": ":", "，": ",", "剎": "刹",
    "Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III",
    " ": "", "\u3000": "", "\xa0": "",  # API 混用三种空格(摸个鱼吧\xa0I 实测 NBSP)
}


def canon(name: str) -> str:
    """API 名 → 注册表键(归一规则见模块 docstring)。"""
    return "".join(_CHAR_MAP.get(c, c) for c in name)


def strip_rich(s: str) -> str:
    """去富文本标签(通用 ``<tag attr>...</tag>`` 形态:color/property/gridfight*/i 等),保正文与换行。

    ``•``→``·``、``剎``→``刹``(与注册表键字符一致 —— strategy_bindings 从 effect 文本
    提取阵营/角色名,字符不统一会绑不上);其余标点/空格保持官方原样。
    """
    s = re.sub(r"</?[a-zA-Z][a-zA-Z0-9]*[^>]*>", "", s)
    return s.replace("•", "·").replace("剎", "刹").strip()


def fetch_config(use_cache: bool) -> dict:
    """拉 config(在线直连或本地缓存)。"""
    if use_cache:
        cands = sorted(REPO.glob(CACHE_GLOB))
        if not cands:
            raise RuntimeError("无本地缓存,去掉 --cache 在线拉")
        return json.loads(cands[-1].read_text(encoding="utf-8"))
    req = urllib.request.Request(CONFIG_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        d = json.loads(resp.read())
    if d.get("retcode") != 0:
        raise RuntimeError(f"config retcode={d.get('retcode')} msg={d.get('message')}")
    return d["data"]


def render(version: str, augments: list[dict], portals: list[dict]) -> str:
    """生成 cw_invest_data.py 全文。"""
    lines = [
        f'# 警告:本文件由 tools/cw/gen_plaza_invest.py 生成(plaza config V{version}),勿手编;',
        '# 版本更新重跑生成;人工建模增量(economy/评估分/分类)在 cw_investments.py。',
        '"""货币战争 投资策略/环境 base 数据(plaza 官方 API,gen_plaza_invest.py 生成)。',
        "",
        f'投资策略(fight_augment_list){len(augments)} 条 / 投资环境(portal_list){len(portals)} 条,V{version}。',
        '数字 id 为稳定主键;name 已 canon 归一(注册表键);effect 为官方效果全文(去富文本)。',
        '"""',
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True)",
        "class PlazaAugment:",
        '    """投资策略 base 条目(局内 3 选 1,可刷新)。"""',
        "    id: str      # plaza 稳定 id(fight_augment_list.id)",
        "    name: str    # canon 归一名(注册表键)",
        "    rarity: str  # 棱彩/金/银(quality 3/2/1)",
        "    effect: str  # 官方效果全文",
        "",
        "",
        "@dataclass(frozen=True)",
        "class PlazaPortal:",
        '    """投资环境 base 条目(开局/固定节点 3 选 1)。"""',
        "    id: str",
        "    name: str",
        "    effect: str",
        "",
        "",
        "PLAZA_AUGMENTS: tuple[PlazaAugment, ...] = (",
    ]
    for a in augments:
        lines.append(
            f"    PlazaAugment(id={a['id']!r}, name={canon(a['name'])!r}, "
            f"rarity={_QUALITY[a['quality']]!r}, effect={strip_rich(a['desc'])!r}),"
        )
    lines.append(")")
    lines.append("")
    lines.append("PLAZA_PORTALS: tuple[PlazaPortal, ...] = (")
    for p in portals:
        lines.append(f"    PlazaPortal(id={p['id']!r}, name={canon(p['title'])!r}, effect={strip_rich(p['desc'])!r}),")
    lines.append(")")
    lines.append("")
    lines.append("")
    lines.append("def augments_by_id() -> dict[str, PlazaAugment]:")
    lines.append('    """id → 条目。"""')
    lines.append("    return {a.id: a for a in PLAZA_AUGMENTS}")
    lines.append("")
    lines.append("")
    lines.append("def portals_by_id() -> dict[str, PlazaPortal]:")
    lines.append('    """id → 条目。"""')
    lines.append("    return {p.id: p for p in PLAZA_PORTALS}")
    lines.append("")
    return "\n".join(lines)


def diff_report(augments: list[dict], portals: list[dict]) -> None:
    """对比旧 data 文件(by id),打印 新增/移除/改名/品质变/效果变。"""
    try:
        from sr_od.application.currency_war.cw_invest_data import (
            PLAZA_AUGMENTS,
            PLAZA_PORTALS,
        )
    except Exception:
        print("[diff] 无旧版 data 文件,跳过 diff")
        return
    for kind, old_items, new_raw, name_of, extra_of in (
        ("策略", PLAZA_AUGMENTS, augments, lambda a: a["name"], lambda a: _QUALITY[a["quality"]]),
        ("环境", PLAZA_PORTALS, portals, lambda p: p["title"], lambda p: ""),
    ):
        old_by_id = {x.id: x for x in old_items}
        new_by_id = {str(x["id"]): x for x in new_raw}
        added = set(new_by_id) - set(old_by_id)
        removed = set(old_by_id) - set(new_by_id)
        renamed = quality_changed = effect_changed = 0
        for rid, x in new_by_id.items():
            o = old_by_id.get(rid)
            if o is None:
                continue
            if canon(name_of(x)) != o.name:
                renamed += 1
                print(f"  ~ {kind} {rid} 改名 {o.name} -> {canon(name_of(x))}")
            if extra_of(x) and extra_of(x) != getattr(o, "rarity", ""):
                quality_changed += 1
                print(f"  ~ {kind} {rid} 品质变 {getattr(o, 'rarity', '')} -> {extra_of(x)}")
            if strip_rich(x.get("desc", "")) != o.effect:
                effect_changed += 1
        print(f"[diff] {kind}: +{len(added)}新增 -{len(removed)}移除 {renamed}改名 "
              f"{quality_changed}品质变 {effect_changed}效果变")
        for rid in sorted(removed):
            print(f"  - {kind} {rid} {old_by_id[rid].name}(移除,核对 overlay 孤儿)")


def main() -> None:
    parser = argparse.ArgumentParser(description="生成投资策略/环境 base 数据")
    parser.add_argument("--cache", action="store_true", help="用本地 config 缓存(离线)")
    args = parser.parse_args()

    cfg = fetch_config(args.cache)
    version = str(cfg.get("rpg_game_big_version", "?"))
    augments: list[dict] = cfg["fight_augment_list"]
    portals: list[dict] = cfg["portal_list"]

    diff_report(augments, portals)
    DATA_PY.write_text(render(version, augments, portals), encoding="utf-8")
    qn: dict[str, int] = {}
    for a in augments:
        qn[_QUALITY[a["quality"]]] = qn.get(_QUALITY[a["quality"]], 0) + 1
    print(f"[data] 策略{len(augments)}({qn}) 环境{len(portals)} V{version} -> {DATA_PY.relative_to(REPO)}")


if __name__ == "__main__":
    main()
