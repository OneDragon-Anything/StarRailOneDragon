"""遗器套装查询 MCP 工具：按名称/件名/tid 查遗器定义（运行时入口）。

数据单一真相源是 ``sr_od.mys.sr_relic_sets`` 常量模块——本模块只是查询
薄壳（零 IO、零状态、无游戏依赖），agent 与日常查问经此获取遗器信息，
无需读源码。查询逻辑做成模块级纯函数 ``lookup_relic`` 便于独立测试。

匹配策略（按优先级，命中即返回）：
1. 纯数字 = 遗器件 id（tid，60000/50000 段公式）→ 套装反查
2. 件名精确命中（192 件名索引）→ 所属套装
3. 套装官方全名精确命中
4. 子串模糊（双向包含，如「翁瓦克」→「生命的翁瓦克」）——多命中返回
   候选列表不猜（社区简称不入表，见 sr_relic_sets 设计裁定）
"""

from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from sr_od.mys.sr_relic_sets import (
    RELIC_SETS,
    RelicSetDef,
    icon_webp_rel_path,
    resolve_set_by_tid,
)

_KIND_CN: dict[str, str] = {'cavern': '隧洞遗器', 'ornament': '位面饰品'}

_POS_CN: dict[int, str] = {1: '头部', 2: '手部', 3: '躯干', 4: '脚部', 5: '位面球', 6: '连结绳'}

#: 件名 → 套装定义索引（模块加载时构建一次；数据源为纯常量，进程内恒稳）
_PIECE_INDEX: dict[str, RelicSetDef] = {
    piece.name: relic_set
    for relic_set in RELIC_SETS
    for piece in relic_set.pieces
}


def _set_to_data(relic_set: RelicSetDef, matched_piece: str | None, match: str) -> dict:
    """套装定义 → 工具返回的 data dict（含每件图标项目相对路径）。"""
    return {
        'set_name': relic_set.set_name,
        'kind': relic_set.kind,
        'kind_cn': _KIND_CN.get(relic_set.kind, relic_set.kind),
        'set_id': relic_set.set_id,
        'obtain': relic_set.obtain,
        'effects': dict(relic_set.effects),
        'pieces': [
            {
                'pos': piece.pos,
                'pos_cn': _POS_CN.get(piece.pos, f'未知部位({piece.pos})'),
                'name': piece.name,
                'desc': piece.desc,
                'icon': icon_webp_rel_path(relic_set.set_name, piece.name),
            }
            for piece in relic_set.pieces
        ],
        'match': match,
        'matched_piece': matched_piece,
    }


def lookup_relic(query: str) -> dict:
    """按套装名/件名/tid 查遗器定义（统一信封，见模块 docstring 匹配策略）。

    Args:
        query: 套装官方全名 / 单件名 / tid 数字字符串 / 模糊子串。

    Returns:
        ``{"status","message","data"}``：``success`` 时 data 为套装全量
        （含件列表与图标路径）；``not_found`` 无命中；``ambiguous`` 模糊
        多命中（data.candidates 为候选套装名列表）。
    """
    text = query.strip()
    if not text:
        return {'status': 'not_found', 'message': '查询词为空', 'data': None}

    # 1. 纯数字 = tid 反查（遗器件 id，见 resolve_set_by_tid 公式）
    if text.isdigit():
        relic_set = resolve_set_by_tid(int(text))
        if relic_set is not None:
            return {'status': 'success', 'message': None, 'data': _set_to_data(relic_set, None, 'tid')}
        return {'status': 'not_found', 'message': f'tid {text} 查无套装', 'data': None}

    # 2. 件名精确
    hit = _PIECE_INDEX.get(text)
    if hit is not None:
        return {'status': 'success', 'message': None,
                'data': _set_to_data(hit, text, 'piece_exact')}

    # 3. 套装名精确
    hit = next((s for s in RELIC_SETS if s.set_name == text), None)
    if hit is not None:
        return {'status': 'success', 'message': None, 'data': _set_to_data(hit, None, 'set_exact')}

    # 4. 子串模糊（双向包含）
    candidates = [s for s in RELIC_SETS if text in s.set_name or s.set_name in text]
    if len(candidates) == 1:
        return {'status': 'success', 'message': None,
                'data': _set_to_data(candidates[0], None, 'fuzzy')}
    if len(candidates) > 1:
        return {'status': 'ambiguous', 'message': f'「{text}」匹配到 {len(candidates)} 个套装，请用官方全名精确查询',
                'data': {'candidates': sorted(s.set_name for s in candidates)}}
    return {'status': 'not_found', 'message': f'「{text}」查无套装/件名（可用套装名子串模糊查询）', 'data': None}


def register_relic_tools(mcp, backend) -> None:  # noqa: ANN001 backend 类型见 app.py 装配处
    """注册遗器查询工具（app.py 装配入口）。"""
    del backend  # 纯常量查询，无 backend 依赖；参数保持装配签名一致

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="查询遗器套装"))
    def relic_lookup(
        query: Annotated[str, Field(
            description="查询词,按优先级匹配:①遗器件id数字(如53076);②单件名精确(如「翁瓦克的诞生之岛」);"
                        "③套装官方全名精确(如「生命的翁瓦克」);④套装名子串模糊(如「翁瓦克」,多命中返回候选)")],
    ) -> dict:
        """观察类。按名字查询崩坏:星穹铁道遗器套装的静态定义（套装效果/单件列表/单件描述/获取途径/内部ID/图标路径）。

        与 ``mys_get_roster_detail`` 分工：本工具查**游戏静态数据**（全部套装,
        不需要登录与游戏在线）；查**账号实际穿戴的遗器词条**走后者。

        查询词匹配策略见参数说明,按优先级命中即返回;模糊多命中返回
        ``ambiguous`` + 候选列表,不猜测。零 IO 纯常量查询。

        Returns:
            统一信封 ``{"status","message","data"}``：
            - ``success``：``data`` 含 set_name/kind_cn(隧洞遗器或位面饰品)/
              set_id(游戏内部套装ID)/obtain(获取途径)/effects(2件与4件效果文案)/
              pieces(单件列表: 部位/件名/描述/图标相对路径)/match(命中方式)；
            - ``ambiguous``：模糊查询多命中，``data.candidates`` 为候选套装名；
            - ``not_found``：查无。
        """
        return lookup_relic(query)
