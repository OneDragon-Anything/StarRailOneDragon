"""角色静态基础信息查询 MCP 工具：全角色定义 + 行迹满级 + 星魂效果。

数据单一真相源是 ``character_const``（98 条角色常量）与
``sr_character_details``（行迹/星魂快照）——本模块只是查询薄壳（零 IO、
零状态、无游戏依赖）。与 ``mys_get_characters`` 的分工：本工具查**静态
基础信息**（全角色，不随账号变、不需要登录）；查**账号拥有与练度**
（等级/星魂解锁/遗器词条/面板）走 mys 工具。

匹配策略（按优先级，命中即返回）：
1. 纯数字 = 游戏内部角色数字 id（avatar_id，mys equip 同源）→ 精确反查
2. 英文代号精确 / 中文名精确
3. 名称子串模糊（双向包含，中英文都扫）——多命中返回候选不猜
``list_all=true`` 忽略 query 按过滤条件列全量基础信息（不带行迹/星魂详情）。
"""

from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

import sr_od.config.character_const as _cc
from sr_od.config.character_const import Character
from sr_od.mys.sr_character_details import resolve_eidolons, resolve_traces

#: 模块级角色索引（加载时构建一次：英文代号 → Character 实例）
_CHARACTER_INDEX: dict[str, Character] = {
    obj.id: obj for name, obj in vars(_cc).items() if isinstance(obj, Character)
}
#: 中文名 → 英文代号（精确中文名查表用；开拓者等 cn 可能重复，取首个）
_CN_INDEX: dict[str, Character] = {}
for _char in _CHARACTER_INDEX.values():
    _CN_INDEX.setdefault(_char.cn, _char)


def _char_base_data(char: Character, match: str) -> dict:
    """角色定义 → 基础信息 dict（不含行迹/星魂详情）。"""
    return {
        'avatar_id': char.avatar_id,
        'id': char.id,
        'cn': char.cn,
        'path_cn': char.path.cn,
        'element_cn': char.combat_type.cn,
        'rarity': char.level,
        'technique_type': char.technique_type.id,
        'icon': f'assets/template/character_avatar/{char.id}/raw.webp',
        'match': match,
    }


def _char_full_data(char: Character, match: str) -> dict:
    """基础信息 + 行迹满级 + 星魂全 6 层（单角色精确查询用）。"""
    data = _char_base_data(char, match)
    data['traces'] = [
        {'tag': t.tag, 'name': t.name, 'max_level': t.max_level,
         'max_values': list(t.max_values), 'desc': t.desc}
        for t in resolve_traces(char.avatar_id)
    ]
    data['eidolons'] = [
        {'pos': e.pos, 'name': e.name, 'desc': e.desc}
        for e in resolve_eidolons(char.avatar_id)
    ]
    return data


def lookup_character(
    query: str,
    rarity: int | None = None,
    path_cn: str | None = None,
    element_cn: str | None = None,
    list_all: bool = False,
) -> dict:
    """按名称/数字 id 查角色静态基础信息（统一信封）。

    Args:
        query: 中文角色名 / 英文代号 / 数字 avatarId / 子串模糊。
        rarity: 星级过滤（4/5），None 不过滤。
        path_cn: 命途中文过滤（毁灭/存护/巡猎/丰饶/虚无/智识/同谐/记忆/欢愉）。
        element_cn: 属性中文过滤（火/冰/风/雷/量子/物理/虚数）。
        list_all: true 时忽略 query 按过滤条件返回全量基础列表（不带详情）。

    Returns:
        ``{"status","message","data"}``：``success`` 时 data 为角色定义
        （精确/模糊单命中带 traces+eidolons 详情；list_all 时为
        ``{'list': [...]}`` 仅基础字段）；``ambiguous`` 模糊多命中
        （candidates 候选名）；``not_found`` 查无。
    """
    def _filter(char: Character) -> bool:
        return ((rarity is None or char.level == rarity)
                and (path_cn is None or char.path.cn == path_cn)
                and (element_cn is None or char.combat_type.cn == element_cn))

    # list_all 全量模式
    if list_all:
        if rarity is None and path_cn is None and element_cn is None:
            return {'status': 'not_found',
                    'message': 'list_all=true 时需提供 rarity/path_cn/element_cn 至少一个过滤', 'data': None}
        picked = [c for c in _CHARACTER_INDEX.values() if _filter(c)]
        picked.sort(key=lambda c: (-c.level, c.id))
        return {'status': 'success', 'message': None,
                'data': {'list': [_char_base_data(c, 'list_all') for c in picked],
                         'count': len(picked)}}

    text = query.strip()
    if not text:
        return {'status': 'not_found', 'message': '查询词为空', 'data': None}

    # 1. 纯数字 = avatar_id 精确反查
    if text.isdigit():
        hit = next((c for c in _CHARACTER_INDEX.values() if c.avatar_id == int(text)), None)
        if hit is not None and _filter(hit):
            return {'status': 'success', 'message': None, 'data': _char_full_data(hit, 'avatar_id')}
        return {'status': 'not_found', 'message': f'数字 id {text} 查无角色', 'data': None}

    # 2. 英文代号精确 / 中文名精确
    hit = _CHARACTER_INDEX.get(text) or _CN_INDEX.get(text)
    if hit is not None and _filter(hit):
        return {'status': 'success', 'message': None, 'data': _char_full_data(hit, 'name_exact')}

    # 3. 子串模糊（中文名/英文代号双向包含）
    candidates = [c for c in _CHARACTER_INDEX.values()
                  if _filter(c) and (text in c.cn or c.cn in text
                                     or text in c.id or c.id in text)]
    if len(candidates) == 1:
        return {'status': 'success', 'message': None,
                'data': _char_full_data(candidates[0], 'fuzzy')}
    if len(candidates) > 1:
        return {'status': 'ambiguous', 'message': f'「{text}」匹配到 {len(candidates)} 个角色，请用官方名精确查询',
                'data': {'candidates': sorted(c.cn for c in candidates)}}
    return {'status': 'not_found', 'message': f'「{text}」查无角色（可用名称子串模糊查询）', 'data': None}


def register_character_tools(mcp, backend) -> None:  # noqa: ANN001 backend 类型见 app.py 装配处
    """注册角色静态信息查询工具（app.py 装配入口）。"""
    del backend  # 纯常量查询，无 backend 依赖；参数保持装配签名一致

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="查询角色基础信息"))
    def character_lookup(
        query: Annotated[str, Field(
            description="查询词,按优先级匹配:①角色数字id(如1217=藿藿);②官方中文名精确(如「黄泉」)或英文代号(如acheron);"
                        "③名称子串模糊(多命中返回候选);list_all=true 时忽略本参数")] = "",
        rarity: Annotated[int | None, Field(
            description="星级过滤:4/5;None 不过滤")] = None,
        path_cn: Annotated[str | None, Field(
            description="命途中文过滤:毁灭/存护/巡猎/丰饶/虚无/智识/同谐/记忆/欢愉;None 不过滤")] = None,
        element_cn: Annotated[str | None, Field(
            description="属性中文过滤:火/冰/风/雷/量子/物理/虚数;None 不过滤")] = None,
        list_all: Annotated[bool, Field(
            description="true=忽略 query,按过滤条件返回全量角色基础列表(不含行迹/星魂详情,需提供至少一个过滤);默认 false")] = False,
    ) -> dict:
        """观察类。按名字查询崩坏:星穹铁道角色的**静态基础信息**——本体定义(命途/属性/星级/秘技类型/数字id/头像路径)与行迹满级效果、星魂全6层效果。

        与 ``mys_get_characters`` 分工：本工具查**静态定义**（全部角色,不随账号变,
        不需要登录）；查**账号拥有与练度**（等级/星魂解锁状态/遗器词条/面板）走
        mys 工具。行迹为满级口径,星魂全 6 层,均为官方原文透传。零 IO 纯常量查询。

        Returns:
            统一信封 ``{"status","message","data"}``：
            - ``success``：精确/模糊单命中时 ``data`` 含基础字段(avatar_id/id/cn/
              path_cn/element_cn/rarity/technique_type/icon)+``traces``(行迹满级
              列表: tag/name/max_level/max_values/desc)+``eidolons``(星魂:
              pos/name/desc)；``list_all=true`` 时 ``data`` 为 ``{'list': [...],
              'count': n}`` 仅基础字段；
            - ``ambiguous``：模糊多命中，``data.candidates`` 为候选角色名；
            - ``not_found``：查无。
        """
        return lookup_character(query, rarity, path_cn, element_cn, list_all)
