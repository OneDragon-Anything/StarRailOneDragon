"""光锥查询 MCP 工具：按名称/星级/命途查光锥定义（运行时入口）。

数据单一真相源是 ``sr_od.mys.sr_light_cones`` 常量模块（本模块只是查询
薄壳，零 IO、零状态、无游戏依赖）；``with_ascension=true`` 时另读
``light_cone_ascension_const``（晋阶分段表，BWIKI 逐光锥页生成）与
``dungeon_drop_const``（材料→副本反查）。查询逻辑做成模块级纯函数
``lookup_light_cone`` 便于独立测试。

匹配策略（按优先级，命中即返回）：
1. 名称精确命中（170 名称索引）
2. 名称子串模糊（双向包含，如「于夜色」→「于夜色中」）——多命中返回
   候选列表不猜（社区简称不入表，见 sr_relic_sets 设计裁定）
过滤参数（与 query 组合使用）：rarity / path_id 缩小模糊结果域；
``list_all=true`` 忽略 query 直接按过滤条件列全量（agent 圈选场景）。
"""

from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from sr_od.config.dungeon_drop_const import (
    MATERIAL_EXTRA_SOURCES,
    find_dungeon_by_material,
    find_missions_by_material,
)
from sr_od.config.light_cone_ascension_const import get_light_cone_ascension
from sr_od.mys.sr_light_cones import (
    LIGHT_CONES,
    LightConeDef,
    resolve_light_cone,
)

_PATH_ID_CN: dict[str, str] = {
    'destruction': '毁灭', 'preservation': '存护', 'hunt': '巡猎', 'abundance': '丰饶',
    'nihility': '虚无', 'erudition': '智识', 'harmony': '同谐', 'remembrance': '记忆',
    'elation': '欢愉',
}


def _cone_to_data(cone: LightConeDef, match: str) -> dict:
    """光锥定义 → 工具返回的 data dict(含特效文本与图标模板项目相对路径)。"""
    return {
        'name': cone.name,
        'rarity': cone.rarity,
        'path_id': cone.path_id,
        'path_cn': _PATH_ID_CN.get(cone.path_id, cone.path_id),
        'obtain': cone.obtain,
        'skill': cone.skill,
        'icon': (f'assets/template/light_cone_icon/{cone.id}/raw.webp'
                 if cone.id else None),
        'match': match,
    }


def _cone_ascension_block(cone: LightConeDef) -> dict | None:
    """光锥 → 晋阶材料 + 刷取副本反查 dict；晋阶表未收录返回 None。

    段名口径：「Y级」= 突破段，「X～Y级」= 经验段（稀薄以太计，界面按
    所持书籍折算显示）。dungeon_by_material / missions_by_material 与
    character_lookup 同口径（分类级反查 / 实例级具体关卡）。"""
    ascension = get_light_cone_ascension(cone.name)
    if ascension is None:
        return None
    dungeon_by_material: dict[str, list[str]] = {}
    missions_by_material: dict[str, list[dict[str, str]]] = {}
    extra_by_material: dict[str, list[str]] = {}
    for material in ascension.total:
        dungeons = find_dungeon_by_material(material)
        if dungeons:
            dungeon_by_material[material] = dungeons
        missions = find_missions_by_material(material)
        if missions:
            missions_by_material[material] = missions
        extra = MATERIAL_EXTRA_SOURCES.get(material)
        if extra:
            extra_by_material[material] = list(extra)
    return {
        'stages': [{'name': s.name, 'materials': dict(s.materials)} for s in ascension.stages],
        'total': dict(ascension.total),
        'dungeon_by_material': dungeon_by_material,
        'missions_by_material': missions_by_material,
        'extra_sources_by_material': extra_by_material,
    }


def lookup_light_cone(
    query: str,
    rarity: int | None = None,
    path_id: str | None = None,
    list_all: bool = False,
    with_ascension: bool = False,
) -> dict:
    """按名称查光锥定义（统一信封，见模块 docstring 匹配策略）。

    Args:
        query: 光锥官方全名 / 模糊子串。
        rarity: 星级过滤（3/4/5），None 不过滤；list_all=true 时必填其一与 path_id 组合。
        path_id: 命途 id 过滤（九命途 id），None 不过滤。
        list_all: true 时忽略 query 按过滤条件返回全量（data.list）。
        with_ascension: true 时单命中结果附带 ``ascension``（晋阶分段表 +
            满晋阶总量 + 材料→刷取副本反查（分类级+实例级）+ 副本外途径）；
            ``list_all`` 模式不带。

    Returns:
        ``{"status","message","data"}``：``success`` 时 data 为光锥定义
        （list_all 时为 ``{'list': [...]}``）；``not_found`` 无命中；
        ``ambiguous`` 模糊多命中（data.candidates 为候选名称列表）。
    """
    def _single_hit(cone: LightConeDef, match: str) -> dict:
        data = _cone_to_data(cone, match)
        if with_ascension:
            data['ascension'] = _cone_ascension_block(cone)
        return {'status': 'success', 'message': None, 'data': data}

    # list_all 全量模式：按过滤条件列全量
    if list_all:
        if rarity is None and path_id is None:
            return {'status': 'not_found', 'message': 'list_all=true 时需提供 rarity 或 path_id 过滤', 'data': None}
        picked = [c for c in LIGHT_CONES
                  if (rarity is None or c.rarity == rarity)
                  and (path_id is None or c.path_id == path_id)]
        return {'status': 'success', 'message': None,
                'data': {'list': [_cone_to_data(c, 'list_all') for c in picked],
                         'count': len(picked)}}

    text = query.strip()
    if not text:
        return {'status': 'not_found', 'message': '查询词为空', 'data': None}

    def _filter(cone: LightConeDef) -> bool:
        return ((rarity is None or cone.rarity == rarity)
                and (path_id is None or cone.path_id == path_id))

    # 1. 名称精确
    hit = resolve_light_cone(text)
    if hit is not None and _filter(hit):
        return _single_hit(hit, 'name_exact')

    # 2. 名称子串模糊（过滤条件内）
    candidates = [c for c in LIGHT_CONES
                  if _filter(c) and (text in c.name or c.name in text)]
    if len(candidates) == 1:
        return _single_hit(candidates[0], 'fuzzy')
    if len(candidates) > 1:
        return {'status': 'ambiguous', 'message': f'「{text}」匹配到 {len(candidates)} 把光锥，请用官方全名精确查询',
                'data': {'candidates': sorted(c.name for c in candidates)}}
    return {'status': 'not_found', 'message': f'「{text}」查无光锥（可用名称子串模糊查询）', 'data': None}


def register_light_cone_tools(mcp, backend) -> None:  # noqa: ANN001 backend 类型见 app.py 装配处
    """注册光锥查询工具（app.py 装配入口）。"""
    del backend  # 纯常量查询，无 backend 依赖；参数保持装配签名一致

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="查询光锥"))
    def cone_lookup(
        query: Annotated[str, Field(
            description="查询词,按优先级匹配:①官方全名精确(如「于夜色中」);"
                        "②名称子串模糊(如「于夜色」,多命中返回候选);list_all=true 时忽略本参数")] = "",
        rarity: Annotated[int | None, Field(
            description="星级过滤:3/4/5;None 不过滤")] = None,
        path_id: Annotated[str | None, Field(
            description="命途id过滤:destruction/preservation/hunt/abundance/nihility/erudition/harmony/remembrance/elation;None 不过滤")] = None,
        list_all: Annotated[bool, Field(
            description="true=忽略 query,按 rarity/path_id 过滤返回全量列表(需提供其一);默认 false 按名称查询")] = False,
        with_ascension: Annotated[bool, Field(
            description="true=单命中结果附带 ascension 晋阶材料块:分段需求 stages(「Y级」=突破段,"
                        "「X～Y级」=经验段以稀薄以太计)+满晋阶总量 total+材料→刷取副本反查 "
                        "dungeon_by_material(键=指南分类名)+实例级 missions_by_material(具体关卡,"
                        "与指南关卡同名对齐)+副本外途径 extra_sources_by_material;list_all 模式不带;"
                        "默认 false")] = False,
    ) -> dict:
        """观察类(只读,零 IO 纯常量查询,不需要登录与游戏在线)。按名字查询崩坏:星穹铁道光锥的静态定义（星级/命途/获取途径/图标路径/特效文本）;可选打通「光锥→晋阶材料→所属副本」链路。

        与 ``relic_lookup`` 分工：本工具查**光锥**（武器卡牌）；查**遗器套装**走
        ``relic_lookup``；查**账号实际穿戴**走 ``mys_get_characters`` 的 equip 摘要。
        skill 字段为特效全文（含叠影 S1-S5 梯度数值,【】括号序列自左至右）。

        Returns:
            统一信封 ``{"status","message","data"}``：
            - ``success``：``data`` 含 name/rarity/path_cn(命途中文)/
              obtain(获取途径)/skill(特效全文)/icon(图标相对路径)/match(命中方式)；
              ``with_ascension=true`` 时另附 ``ascension``(stages 分段需求/
              total 满晋阶总量/dungeon_by_material 分类级副本反查/
              missions_by_material 实例级/extra_sources_by_material 副本外
              途径;表未收录该光锥时为 null)；
              ``list_all=true`` 时为 ``{'list': [...], 'count': n}``
              (不带详情与 ascension)；
            - ``ambiguous``：模糊查询多命中，``data.candidates`` 为候选名称；
            - ``not_found``：查无。
        """
        return lookup_light_cone(query, rarity, path_id, list_all, with_ascension)
