"""货币战争 · plaza 官方接口 → 主角光环 base 数据生成器(版本更新重跑)。

数据源(免登录公开 API,同 plaza_fetch.py):
  GET https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config?game=hkrpg
  (必需 header x-rpc-currencywar-tourn: tourn)
  取 ``spot_light_list``(主角光环)+ ``spot_light_tag_list``(官方标签枚举)。

产出(**base 事实层,勿手编**):
  ``src/sr_od/application/currency_war/data/cw_spot_lights.py`` —— 官方口径镜像
  (id/name/desc/tags/suitable_roles):数字 id 为稳定主键;desc 为官方效果全文
  (去富文本);tags 为官方标签名元组(tag_id 经 spot_light_tag_list 翻译);
  suitable_roles 为适配角色规范名元组(生成期由 plaza role id 经角色注册表
  翻译,同名多档合并)。

游戏内名称「主角光环」(API 代号 spot_light):首领战前为主角选定的全局增强,
全 82 条官方直出。其中 5 条是特殊羁绊的授予面(从师/连携追击/星狩誓言/
四维狂潮/救世主 = trait 域 400xxx 骨架),桥接信息在本表自足,不在 trait 域
重复登记。

两层架构:本生成器只管 **base 事实层**(官方镜像);「怎么选光环」的策略建模
(评序/分等)当前无决策消费点,不建——消费点出现时按 data-collection.md §五
方法论人工增量(对齐 cw_investments 模式),本文件保持生成器产物勿手编。

依赖顺序耦合:suitable_roles 的 id 翻译依赖角色注册表(cw_chars.CHARACTERS)
先就绪,角色域没闭环前本生成器必红——同 gen_traits 成员对拍,是顺序契约。

用法(项目根):
  uv run python skills/sr-od-dev-currency-war/scripts/gen_plaza_spot_lights.py
  uv run python skills/sr-od-dev-currency-war/scripts/gen_plaza_spot_lights.py --cache
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
sys.path.insert(0, str(REPO / "src"))
DATA_PY = REPO / "src/sr_od/application/currency_war/data/cw_spot_lights.py"
GEN_CMD = "uv run python skills/sr-od-dev-currency-war/scripts/gen_plaza_spot_lights.py"
CACHE_GLOB = ".debug/game_data/currency_war/plaza/config_v*.json"

CONFIG_URL = "https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config?game=hkrpg"
HEADERS = {
    "x-rpc-currencywar-tourn": "tourn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://act.miyoushe.com/",
}

_CHAR_MAP: dict[str, str] = {
    "•": "·", "：": ":", "，": ",", "剎": "刹",
    "Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III",
    " ": "", "\u3000": "", "\xa0": "",
}


def canon(name: str) -> str:
    """API 名 → 注册表键(归一规则与 gen_plaza_invest 同款;当前名单无命中,幂等防御)。"""
    return "".join(_CHAR_MAP.get(c, c) for c in name)


def strip_rich(s: str) -> str:
    """去富文本标签(通用 ``<tag attr>...</tag>`` 形态:color/i 等),保正文与换行。

    ``{NICKNAME}`` = 游戏运行时模板占位符(渲染为玩家昵称)→ 归一为「开拓者」
    (当前名单无命中,与投资域同契约防未来漂移)。
    """
    s = re.sub(r"</?[a-zA-Z][a-zA-Z0-9]*[^>]*>", "", s)
    return s.replace("•", "·").replace("剎", "刹").replace("{NICKNAME}", "开拓者").strip()


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


def translate_roles(role_ids: list[str]) -> tuple[str, ...]:
    """plaza role id → 适配角色规范名元组(fail-closed;同名多档合并保序)。

    翻译查表契约 = 派生形态:运行时从角色注册表 CHARACTERS 的 source 字段
    派生 id→名映射(与 gen_traits 成员翻译同构),注册表改名单自动跟上;
    未知 id 直接报错(fail-closed),不静默丢弃。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS

    by_source: dict[str, str] = {ch.source: ch.name for ch in CHARACTERS if ch.source}
    names: list[str] = []
    for rid in role_ids:
        name = by_source.get(str(rid))
        if name is None:
            raise RuntimeError(
                f"主角光环适配角色 id {rid!r} 不在角色注册表 source 中——"
                "角色域未就绪或官方新角色未录入,先闭环角色域再重跑本生成器"
            )
        if name not in names:
            names.append(name)
    return tuple(names)


def render(version: str, lights: list[dict], tag_names: dict[str, str]) -> str:
    """生成 cw_spot_lights.py 全文(base 事实层,单产物)。"""
    lines = [
        f'# 警告:本文件由 skills/sr-od-dev-currency-war/scripts/gen_plaza_spot_lights.py 生成(plaza config V{version}),勿手编;',
        '# 版本更新重跑生成;base 事实层(官方口径镜像),「怎么选光环」策略建模暂无消费点不建。',
        f'# 重跑: {GEN_CMD}',
        '"""货币战争 主角光环 base 数据(plaza 官方 API,gen_plaza_spot_lights.py 生成)。',
        "",
        f'主角光环(spot_light_list){len(lights)} 条,V{version}。首领战前为主角选定的全局增强;',
        "数字 id 为稳定主键;desc 为官方效果全文(去富文本);tags 为官方标签名元组",
        "(枚举源 = plaza spot_light_tag_list,官方序);suitable_roles 为适配角色规范名",
        "元组(生成期经角色注册表翻译,同名多档合并;空元组 = 全局/非角色绑定型光环,",
        "官方原样非缺数据)。5 条特殊羁绊授予面(= trait 域 400xxx 骨架:从师/",
        "连携追击/星狩誓言/四维狂潮/救世主)在本表登记,桥接信息本表自足。",
        '"""',
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True)",
        "class SpotLight:",
        '    """主角光环 base 条目(官方口径镜像;生成器产物,勿手编)。"""',
        "    id: str               # plaza 稳定 id(spot_light_list.id)",
        "    name: str             # canon 归一名",
        "    desc: str             # 官方效果全文(去富文本)",
        "    tags: tuple[str, ...] # 官方标签名元组(官方序)",
        "    suitable_roles: tuple[str, ...]  # 适配角色规范名;空 = 全局型光环",
        "",
        "",
        "SPOT_LIGHTS: tuple[SpotLight, ...] = (",
    ]
    for x in lights:
        tags = tuple(tag_names[t["tag_id"]] for t in x["tag_list"])
        roles = translate_roles(x["suitable_role_list"])
        lines.append(
            f"    SpotLight(id={str(x['id'])!r}, name={canon(x['name'])!r}, "
            f"desc={strip_rich(x['desc'])!r}, tags={tags!r}, suitable_roles={roles!r}),"
        )
    lines.append(")")
    lines.append("")
    lines.append("")
    lines.append("def spot_light_by_id() -> dict[str, SpotLight]:")
    lines.append('    """id → 条目。"""')
    lines.append("    return {x.id: x for x in SPOT_LIGHTS}")
    lines.append("")
    return "\n".join(lines)


def diff_report(lights: list[dict], tag_names: dict[str, str]) -> None:
    """对比旧 data 文件(by id),打印 新增/移除/改名/标签变/适配变/效果变。"""
    try:
        from sr_od.application.currency_war.data.cw_spot_lights import SPOT_LIGHTS
    except Exception:
        print("[diff] 无旧版 data 文件,跳过 diff")
        return
    old_by_id = {x.id: x for x in SPOT_LIGHTS}
    new_by_id = {str(x["id"]): x for x in lights}
    added = set(new_by_id) - set(old_by_id)
    removed = set(old_by_id) - set(new_by_id)
    renamed = 0
    changed: list[str] = []
    for rid, x in new_by_id.items():
        o = old_by_id.get(rid)
        if o is None:
            continue
        if canon(x["name"]) != o.name:
            renamed += 1
            print(f"  ~ {rid} 改名 {o.name} -> {canon(x['name'])}")
        new_tags = tuple(tag_names[t["tag_id"]] for t in x["tag_list"])
        if new_tags != o.tags:
            changed.append(f"{rid} {o.name} 标签 {o.tags} -> {new_tags}")
        new_roles = translate_roles(x["suitable_role_list"])
        if new_roles != o.suitable_roles:
            changed.append(f"{rid} {o.name} 适配名单变")
        if strip_rich(x["desc"]) != o.desc:
            changed.append(f"{rid} {o.name} 效果变")
    print(f"[diff] 主角光环: +{len(added)}新增 -{len(removed)}移除 {renamed}改名 {len(changed)}条目变")
    for line in changed[:20]:
        print(f"  ~ {line}")
    if len(changed) > 20:
        print(f"  ...另 {len(changed) - 20} 条")
    for rid in sorted(added):
        print(f"  + {rid} {canon(new_by_id[rid]['name'])}(新增)")
    for rid in sorted(removed):
        print(f"  - {rid} {old_by_id[rid].name}(移除,核对策略消费点引用)")


def main() -> None:
    parser = argparse.ArgumentParser(description="生成主角光环 base 数据")
    parser.add_argument("--cache", action="store_true", help="用本地 config 缓存(离线)")
    args = parser.parse_args()

    cfg = fetch_config(args.cache)
    version = str(cfg.get("rpg_game_big_version", "?"))
    lights: list[dict] = cfg["spot_light_list"]
    tag_names = {str(t["tag_id"]): t["name"] for t in cfg["spot_light_tag_list"]}

    diff_report(lights, tag_names)
    DATA_PY.write_text(render(version, lights, tag_names), encoding="utf-8")
    print(f"[data] 主角光环{len(lights)} 条 V{version} -> {DATA_PY.relative_to(REPO)}")


if __name__ == "__main__":
    main()
