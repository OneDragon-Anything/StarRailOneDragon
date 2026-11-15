"""MCP 查询类工具的自解释文本渲染层。

约定（``docs/develop/sr_od/backend/mcp-implementation.md`` §3 的扩展）：
- MCP 层面向 agent 消费：查询类工具直接返回自解释 markdown 文本，不保留
  JSON 形态。text 返回没有 schema 兜底，输出里每个数据必须由文本自身回答
  「是什么、哪个工具的哪个参数消费它」——与工具清单无关的数据不输出；
- 数据 ↔ 工具的关系说明按「一次一行」收拢在输出头部，明细行只留该行特有
  的信息，缺省值与样板语义不逐行重复；
- backend 方法保持结构化返回（框架内部消费不变），渲染只发生在 MCP 工具层；
- 每个工具配一个 ``render_xxx(result: dict) -> str``：输入是该工具结构化
  返回的信封，``success=False`` 错误形态同样渲染（单一出口）。
"""

#: 建档缺省识别阈值（``ScreenArea`` 构造缺省 / ``upsert_screen_area`` 入参缺省）：
#: 明细行不重复标注，收拢到输出头部说明；None 视同缺省
_DEFAULT_LCS_PERCENT = 0.5
_DEFAULT_TEMPLATE_THRESHOLD = 0.7


def _one_line(value: object) -> str:
    """值 → 单行文本：None/空 → 空串，换行折空格（游戏文案可能带换行）。"""
    if value is None:
        return ''
    return str(value).replace('\n', ' ')


def _render_area_line(area: dict) -> str:
    """单个 area → 一行自描述文本（不含行首 ``- ``），``区域名:属性段,…`` 形态。

    属性段序：id_mark（命中才标）、识别方式（OCR 找文案 / 模板比对路径，
    非缺省阈值就地标注 / 纯定位）、点击坐标（1080p 区域矩形 + 中心）、
    goto 跳转目标。区域名的语义与各段的全局解释由输出头部的关系说明承载。
    """
    parts: list[str] = []
    if area.get('id_mark'):
        parts.append('id_mark')
    text = _one_line(area.get('text'))
    template_id = _one_line(area.get('template_id'))
    if text:
        label = f'OCR 找「{text}」'
        lcs = area.get('lcs_percent')
        if lcs is not None and lcs != _DEFAULT_LCS_PERCENT:
            label += f'(相似度 {lcs})'
        parts.append(label)
    elif template_id:
        sub_dir = _one_line(area.get('template_sub_dir'))
        label = '模板比对 ' + (f'{sub_dir}/{template_id}' if sub_dir else template_id)
        threshold = area.get('template_match_threshold')
        if threshold is not None and threshold != _DEFAULT_TEMPLATE_THRESHOLD:
            label += f'(阈值 {threshold})'
        parts.append(label)
    else:
        parts.append('纯定位')
    rect: list[int] = area.get('pc_rect') or []
    if len(rect) == 4:
        center = ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)
        parts.append(f'区域[{rect[0]},{rect[1]},{rect[2]},{rect[3]}] 中心({center[0]},{center[1]})')
    goto: list[str] = area.get('goto_list') or []
    if goto:
        parts.append('点击后→' + '、'.join(goto))
    return f'{_one_line(area.get("area_name"))}:' + '，'.join(parts)


def render_screen_detail(result: dict) -> str:
    """``get_screen_detail`` 结构化返回 → 自解释 markdown。

    首行画面档概要；其后的关系说明行把输出数据与消费它的 MCP 工具一一挂钩
    （画面名 → ``goto_screen`` 目标与 ``get_screen_detail`` / ``upsert_screen_area``
    入参、区域中心 → ``click_game`` 坐标、识别配置 → ``analyze_screen`` 命中
    依据、可达名单 → ``goto_screen`` 目标），只在有内容时输出；最后每个区域
    一行（见 ``_render_area_line``），区域顺序保持建档原序。
    """
    if not result.get('success'):
        return f"画面档查询失败: {result.get('error')}"

    screen_name = result.get('screen_name')
    neighbors: list[str] = result.get('goto_neighbors') or []
    lines: list[str] = [
        f"# 画面档:{screen_name} · {result.get('area_count')} 个区域",
        '',
        f'- 「{screen_name}」是画面名(screen_name):goto_screen 的跳转目标，'
        'get_screen_detail / upsert_screen_area 的定位入参都用它',
    ]

    coord_line = ('- 坐标为 1080p 口径:区域[左,上,右,下] = upsert_screen_area 的 pc_rect，'
                  '中心(x,y) 可直接喂 click_game')
    if result.get('pc_alt'):
        coord_line += '；本画面 pc_alt=true，点击前需按住 Alt → click_game 带 pc_alt=True'
    lines.append(coord_line)

    lines.append(
        '- 识别方式是 analyze_screen 命中该区域的依据；id_mark 行是画面身份判定锚'
        '(analyze_screen 精准命中 is_precise 靠它)；「纯定位」= 无识别特征，直接点中心')
    lines.append(
        f'- 说明:阈值只在非缺省时标注(OCR 相似度缺省 {_DEFAULT_LCS_PERCENT}'
        f'/模板阈值缺省 {_DEFAULT_TEMPLATE_THRESHOLD})')
    if neighbors:
        lines.append(
            f'- 可直达画面 —— 名字都是画面名，可直接作为 goto_screen 的目标'
            f'({len(neighbors)}):{"、".join(neighbors)}')
    lines.append('')

    areas: list[dict] = result.get('areas') or []
    if not areas:
        lines.append('(尚无 area)')
        return '\n'.join(lines)
    for area in areas:
        lines.append('- ' + _render_area_line(area))
    return '\n'.join(lines)
