"""货币战争静态数据查询 MCP 工具:角色 / 羁绊 / 装备三域注册表的只读查询薄壳。

数据单一真相源 = ``cw_chars``(角色与系统单位)、``cw_traits_data``(羁绊)、
``cw_equipment_data``(装备)——本模块零 IO、零状态、无游戏依赖;注册表随
版本重跑更新后本族工具自动跟上(无复制数据)。

与 ``analyze_screen`` 分工:本族查**静态定义**(角色费用与羁绊所属、羁绊
档位效果、装备效果与配方);对局动态(商店在售、板面在场、装备栏持有)走
``analyze_screen``。角色技能文本不在注册表(数据面现实)——技能细节需
游戏内点角色卡查看;本族给到的是决策静态面(费用/羁绊/站位/定位标签)。

匹配策略(三域一致,按优先级,命中即返回):
1. 规范名精确(如「瓦尔特」「欢愉」「蓄能帆」);
2. 名称子串模糊(双向包含)——单命中即 success;多命中 status=ambiguous,
   matches 携带全部命中条目(条目本身轻量,不另设纯名字候选通道);
3. ``list_all=true`` 忽略 query 按过滤条件列全量(需至少一个过滤,防全表
   膨胀);过滤结果为空列表时 status=success(matches 空)。

status 判定:精确命中恒 success(角色同名多档合并为一条,如星神★阿哈
costs=[4,5,7]);not_found 仅用于 query 查无。
"""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from sr_od.application.currency_war.data.cw_chars import (
    CHARACTERS,
    SYSTEM_UNITS,
)
from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS, Equipment
from sr_od.application.currency_war.data.cw_traits_data import TRAITS, Trait
from sr_od.backend.backend_context import SrBackendContext

# trait_type 官方枚举 → 中文(0 阵营 / 1 流派 / 2 独立;cw_traits_data.Trait 字段注释)
_TRAIT_KIND_CN: dict[int, str] = {0: '阵营', 1: '流派', 2: '独立'}


# ===== Out 模型(返回体纯数据;status 为业务多态判别字段,失败走异常通道) =====

class CwCharInfo(BaseModel):
    """货币战争角色条目(静态注册表口径)。"""
    name: str = Field(description='角色规范名(官方名归一口径)')
    costs: list[int] = Field(
        description='费用档(1-5);多档角色多条目合并(如星神★阿哈=[4,5,7]);0=系统赠送单位(非购买)')
    position: str = Field(description='站位类型:front=前台 / back=后台 / common=双排皆可(技能效果不绑定排)')
    category_tags: list[str] = Field(description='官方技能分类标签(输出/辅助/治疗/护盾,可多个)')
    factions: list[str] = Field(description='所属阵营羁绊名(空列表=无)')
    schools: list[str] = Field(description='所属流派羁绊名(空列表=无)')
    independent: str = Field(description='独立羁绊名(空字符串=无)')
    is_expert: bool = Field(description='专家顾问:初始不在普通商店招募,需局内经投资策略/环境/邀请函解锁后加入')
    is_hide: bool = Field(description='隐藏单位:数据保留但不在玩家可见列表(如饮月绑定随从丹恒·腾荒)')
    system_note: str = Field(description='系统赠送单位的来源说明(投资策略/环境赠送,恒后台不可卖;普通角色为空字符串)')


class CwCharLookupOut(BaseModel):
    """cw_char_lookup 返回体。"""
    status: str = Field(description='success=命中(含多档合并与 list_all)/ambiguous=名称模糊多命中/not_found=查无')
    matches: list[CwCharInfo] = Field(description='命中条目列表(ambiguous 时为全部命中,按名消歧后重查)')


class CwTraitLayerInfo(BaseModel):
    """羁绊单档效果条目。"""
    layer: int = Field(description='激活所需计数档位(按 count_mode 口径:人数或三星人数)')
    desc: str = Field(description='该档效果全文(官方原文透传)')


class CwTraitInfo(BaseModel):
    """货币战争羁绊条目(静态注册表口径)。"""
    trait_id: str = Field(description='官方稳定机器键(跨版本对拍/资产映射用)')
    name: str = Field(description='羁绊规范名')
    kind: str = Field(description='阵营/流派/独立')
    count_mode: str = Field(
        description='计数方式:TOTAL=按上场人数(含穿戴该羁绊星徽的角色)/STAR3=按场上三星成员数(全表仅千星商会)')
    members: list[str] = Field(description='全部成员角色名(注册表口径)')
    layers: list[CwTraitLayerInfo] = Field(description='逐档效果(layer 升序)')
    simple_desc: str = Field(description='官方总效果简述')


class CwTraitLookupOut(BaseModel):
    """cw_trait_lookup 返回体。"""
    status: str = Field(description='success=命中(含 list_all)/ambiguous=名称模糊多命中/not_found=查无')
    matches: list[CwTraitInfo] = Field(description='命中条目列表')


class CwEquipInfo(BaseModel):
    """货币战争装备条目(静态注册表口径)。"""
    name: str = Field(description='装备规范名')
    category: str = Field(
        description='官方分类:进阶装备/特权装备/星徽/餐品改件/列车改件/宝钻/固有装备;另含派生类「简易装备」')
    effect: str = Field(description='效果全文(官方原文透传)')
    stacking: bool = Field(description='效果是否可叠加(效果文本推断口径)')
    recipes: list[str] = Field(description='合成路线,每条为材料组合(如「红钻+光能电池」);空列表=不可合成')
    props: list[str] = Field(description='结构化基础属性(如「前台强度 30%」);空列表=无')


class CwEquipLookupOut(BaseModel):
    """cw_equip_lookup 返回体。"""
    status: str = Field(description='success=命中(含 list_all)/ambiguous=名称模糊多命中/not_found=查无')
    matches: list[CwEquipInfo] = Field(description='命中条目列表')


# ===== 查询实现(模块级纯函数,测试直调) =====

def _merge_char_entries(name: str) -> list[CwCharInfo]:
    """按规范名合并同名多档条目(星神★阿哈 4/5/7 → costs=[4,5,7] 单条)。"""
    same_name = [c for c in CHARACTERS if c.name == name]
    if not same_name:
        return []
    first = same_name[0]
    return [CwCharInfo(
        name=first.name,
        costs=sorted({c.cost for c in same_name}),
        position=first.position,
        category_tags=list(first.category_tags),
        factions=list(first.factions),
        schools=list(first.schools),
        independent=first.independent,
        is_expert=any(c.is_expert for c in same_name),
        is_hide=any(c.is_hide for c in same_name),
        system_note='',
    )]


def _system_unit_info(name: str, note: str) -> CwCharInfo:
    """系统赠送单位(投资策略/环境送的召唤物类)的条目形态(注册表常量语义)。"""
    return CwCharInfo(
        name=name, costs=[0], position='back',
        category_tags=[], factions=[], schools=[],
        independent='', is_expert=False, is_hide=False,
        system_note=note,
    )


def lookup_cw_char(
    query: str = '',
    cost: int | None = None,
    list_all: bool = False,
) -> CwCharLookupOut:
    """角色域查询实现(匹配策略见模块 docstring)。"""
    all_names = [c.name for c in CHARACTERS]
    if list_all:
        if cost is None:
            raise ValueError('list_all 需要至少一个过滤条件(如 cost=4);查询已知名字用 query 精确/模糊匹配')
        entries: list[CwCharInfo] = []
        for name in dict.fromkeys(all_names):
            merged = _merge_char_entries(name)
            if merged and cost in merged[0].costs:
                entries.append(merged[0])
        return CwCharLookupOut(status='success', matches=entries)

    if not query:
        return CwCharLookupOut(status='not_found', matches=[])
    exact = query in set(all_names)
    fuzzy = sorted({name for name in all_names if query in name or name in query}
                   | {name for name in SYSTEM_UNITS if query in name or name in query})
    system_exact = query in SYSTEM_UNITS
    if exact:
        return CwCharLookupOut(status='success', matches=_merge_char_entries(query))
    if system_exact:
        return CwCharLookupOut(status='success',
                               matches=[_system_unit_info(query, SYSTEM_UNITS[query].source)])
    if len(fuzzy) == 1:
        name = fuzzy[0]
        if name in SYSTEM_UNITS:
            return CwCharLookupOut(status='success',
                                   matches=[_system_unit_info(name, SYSTEM_UNITS[name].source)])
        return CwCharLookupOut(status='success', matches=_merge_char_entries(name))
    if len(fuzzy) > 1:
        matches: list[CwCharInfo] = []
        for name in fuzzy:
            if name in SYSTEM_UNITS:
                matches.append(_system_unit_info(name, SYSTEM_UNITS[name].source))
            else:
                matches.extend(_merge_char_entries(name))
        return CwCharLookupOut(status='ambiguous', matches=matches)
    return CwCharLookupOut(status='not_found', matches=[])


def lookup_cw_trait(
    query: str = '',
    kind_cn: str | None = None,
    list_all: bool = False,
) -> CwTraitLookupOut:
    """羁绊域查询实现(匹配策略见模块 docstring)。"""
    traits = sorted(TRAITS.values(), key=lambda t: t.trait_name)

    def to_info(t: Trait) -> CwTraitInfo:
        return CwTraitInfo(
            trait_id=t.trait_id,
            name=t.trait_name,
            kind=_TRAIT_KIND_CN.get(t.trait_type, str(t.trait_type)),
            count_mode=t.count_mode,
            members=list(t.members),
            layers=[CwTraitLayerInfo(layer=ly.layer, desc=ly.trait_desc) for ly in t.layers],
            simple_desc=t.simple_desc,
        )

    if list_all:
        if kind_cn is None:
            raise ValueError('list_all 需要至少一个过滤条件(如 kind_cn=阵营);查询已知羁绊用 query 精确/模糊匹配')
        if kind_cn not in _TRAIT_KIND_CN.values():
            raise ValueError(f'kind_cn 合法值: {sorted(_TRAIT_KIND_CN.values())}')
        return CwTraitLookupOut(
            status='success',
            matches=[to_info(t) for t in traits if _TRAIT_KIND_CN.get(t.trait_type) == kind_cn])

    if not query:
        return CwTraitLookupOut(status='not_found', matches=[])
    by_name = {t.trait_name: t for t in traits}
    if query in by_name:
        return CwTraitLookupOut(status='success', matches=[to_info(by_name[query])])
    fuzzy = sorted(name for name in by_name if query in name or name in query)
    if len(fuzzy) == 1:
        return CwTraitLookupOut(status='success', matches=[to_info(by_name[fuzzy[0]])])
    if len(fuzzy) > 1:
        return CwTraitLookupOut(status='ambiguous', matches=[to_info(by_name[n]) for n in fuzzy])
    return CwTraitLookupOut(status='not_found', matches=[])


def lookup_cw_equip(
    query: str = '',
    category: str | None = None,
    list_all: bool = False,
) -> CwEquipLookupOut:
    """装备域查询实现(匹配策略见模块 docstring)。"""
    def to_info(e: Equipment) -> CwEquipInfo:
        return CwEquipInfo(
            name=e.name,
            category=e.category,
            effect=e.effect,
            stacking=e.stacking,
            recipes=['+'.join(recipe) for recipe in e.recipes],
            props=[f'{k} {v}' for k, v in e.props],
        )

    equips = sorted(EQUIPMENTS.values(), key=lambda e: e.name)
    if list_all:
        if category is None:
            raise ValueError('list_all 需要至少一个过滤条件(如 category=星徽);查询已知装备用 query 精确/模糊匹配')
        valid = sorted({e.category for e in equips})
        if category not in valid:
            raise ValueError(f'category 合法值: {valid}')
        return CwEquipLookupOut(
            status='success',
            matches=[to_info(e) for e in equips if e.category == category])

    if not query:
        return CwEquipLookupOut(status='not_found', matches=[])
    if query in EQUIPMENTS:
        return CwEquipLookupOut(status='success', matches=[to_info(EQUIPMENTS[query])])
    fuzzy = sorted(name for name in EQUIPMENTS if query in name or name in query)
    if len(fuzzy) == 1:
        return CwEquipLookupOut(status='success', matches=[to_info(EQUIPMENTS[fuzzy[0]])])
    if len(fuzzy) > 1:
        return CwEquipLookupOut(status='ambiguous', matches=[to_info(EQUIPMENTS[n]) for n in fuzzy])
    return CwEquipLookupOut(status='not_found', matches=[])


# ===== MCP 工具注册(三工具均为纯静态查询,不触达 backend 运行时) =====

def register_cw_lookup_tools(mcp: FastMCP, backend: SrBackendContext) -> None:
    """注册货币战争静态查询工具族(签名与各 register_* 族一致;backend 参数本族不消费)。"""

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title='查询货币战争角色'))
    def cw_char_lookup(
        query: Annotated[str, Field(
            description='查询词:①角色名精确(如「瓦尔特」「星神★阿哈」,同名多档合并返回);'
                        '②名称子串模糊(多命中返回全部条目按名消歧);list_all=true 时忽略本参数')] = '',
        cost: Annotated[int | None, Field(
            description='费用过滤:1-5;list_all 必填(list_all=true 需要至少一个过滤)')] = None,
        list_all: Annotated[bool, Field(
            description='true=忽略 query,按 cost 过滤返回全量角色(如「4 费都有谁」);需提供 cost;默认 false')] = False,
    ) -> CwCharLookupOut:
        """观察类(只读,零 IO 纯常量查询,不需要登录与游戏在线)。按名字查货币战争角色的静态定义——费用/站位/分类标签/所属羁绊(阵营+流派+独立)/专家顾问标记/隐藏标记。

        决策用途:商店出牌时快速判断「这张牌是什么、进哪条线」(费用与羁绊所属)、
        凑羁绊时确认候选成员。系统赠送单位(投资策略送的召唤物类)也在查询域
        (costs=[0] 标记)。角色**技能文本不在数据面**——技能细节需游戏内点角色卡查看。

        与 ``cw_trait_lookup``/``cw_equip_lookup`` 分工:本工具查角色;查羁绊档位效果
        走 ``cw_trait_lookup``;查装备效果配方走 ``cw_equip_lookup``;查对局动态(商店
        在售/板面在场)走 ``analyze_screen``。
        """
        return lookup_cw_char(query, cost, list_all)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title='查询货币战争羁绊'))
    def cw_trait_lookup(
        query: Annotated[str, Field(
            description='查询词:①羁绊名精确(如「欢愉」「开拓银轨」);②名称子串模糊(多命中返回全部条目);'
                        'list_all=true 时忽略本参数')] = '',
        kind_cn: Annotated[str | None, Field(
            description='羁绊类型过滤:阵营/流派/独立;list_all 必填(list_all=true 需要至少一个过滤)')] = None,
        list_all: Annotated[bool, Field(
            description='true=忽略 query,按类型过滤返回全量羁绊(如「全部阵营羁绊」);需提供 kind_cn;默认 false')] = False,
    ) -> CwTraitLookupOut:
        """观察类(只读,零 IO 纯常量查询,不需要登录与游戏在线)。按名字查货币战争羁绊的静态定义——全部成员/逐档效果原文/计数方式(按人数或按三星人数)/类型(阵营/流派/独立)。

        决策用途:凑羁绊时确认「还差几人、差谁」(成员表)与「下一档值不值得追」
        (逐档效果);千星商会的计数方式为按场上三星成员数(STAR3,全表唯一特例),
        光上场不升星不激活。
        """
        return lookup_cw_trait(query, kind_cn, list_all)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title='查询货币战争装备'))
    def cw_equip_lookup(
        query: Annotated[str, Field(
            description='查询词:①装备名精确(如「蓄能帆」「火力风暴潮」);②名称子串模糊(多命中返回全部条目);'
                        'list_all=true 时忽略本参数')] = '',
        category: Annotated[str | None, Field(
            description='分类过滤:进阶装备/特权装备/星徽/餐品改件/列车改件/宝钻/固有装备/简易装备;'
                        'list_all 必填(list_all=true 需要至少一个过滤)')] = None,
        list_all: Annotated[bool, Field(
            description='true=忽略 query,按分类过滤返回全量装备(如「全部星徽」);需提供 category;默认 false')] = False,
    ) -> CwEquipLookupOut:
        """观察类(只读,零 IO 纯常量查询,不需要登录与游戏在线)。按名字查货币战争装备的静态定义——效果全文/合成配方(材料组合)/分类(进阶/星徽/宝钻…)/基础属性/可叠加性。

        决策用途:合成前确认配方材料、穿戴前确认效果与唯一性、看到陌生装备名时
        快速了解它是什么。星徽类装备的效果是「装备者加入某羁绊」——是凑羁绊
        档位的正规手段,与 ``cw_trait_lookup`` 配合使用。
        """
        return lookup_cw_equip(query, category, list_all)
