"""米游社 game_record 中文码表快照与三层查表助手。

设计出处：docs/develop/sr_od/backend/mys.md「sr_od/mys（崩铁特有封装）」节
（三层查表，miss 不抛异常）。映射内容的权威草案：四源交叉验证的码表侦察稿——
本模块只固化其映射，禁自行增删改；未来新码一律走兜底而非进表。

三层查表契约：
1. 响应原生词典优先：调用方透传 ``avatar/info`` 的 ``data.property_info``
   （56 码官方词典，随响应更新、自动前向兼容新码）。**键须先归一为 int**——
   响应原生键是字符串。显示名取词条内「干净可用值」（非空且不含 ``#``），
   ``property_name_relic`` 优先、``name`` 兜底：实测词典存在两形态占位符——
   pt=36 的 name 带 ``#1[f1]%``（靠 relic 字段规避）、pt=26/28/30 的
   property_name_relic 带 ``#1[i]``（靠 name 字段规避），对偶处理；
2. 硬编码快照兜底：下方 ``PROPERTY_INFO_SNAPSHOT``（2026-11-03 实测词典 56 码
   逐键固化）与四张小表；
3. 终兜底：「未知属性(pt=N)」等文案 + warning，不抛异常（官方有预占码位习惯；
   新码等响应词典带名后经层 1 自动前向兼容）。

模块纪律：零外部 IO、零状态——纯常量 + 纯函数；词典参数由调用方传入并在
调用侧归一键型，本模块不做缓存。

撞域纪律：星魂 ``ranks[].pos`` 同取 1-6 但语义是星魂序号，与遗器部位码撞值域
（同码不同义）——``RELIC_POS_CN`` / ``resolve_relic_pos_cn``
只许服务遗器/饰品 pos 字段，两处禁共用。
"""

from collections.abc import Mapping
from typing import TypedDict

from one_dragon.utils.log_utils import log


class PropertyNameInfo(TypedDict, total=False):
    """``avatar/info`` 响应原生 property_info 单条（轻类型）。

    只声明显示名两字段；icon 等 URL 字段不进本契约（不透传）。键可缺失
    （total=False），值可为空串——官方空名占位码实测如此（pt=8/61）。

    Attributes:
        name: 词典 name 字段；可能带模板占位符（实测 pt=36
            ``受治疗量提高#1[f1]%``）。
        property_name_relic: 词条语境显示名；多数码与 name 同值，个别码带
            占位符（实测 pt=26/28/30 ``基础生命值提高#1[i]``）。
    """

    name: str
    property_name_relic: str


# ---- 表 1：property_type → 属性中文名 ----
# 2026-11-03 实测词典 56 码逐键固化：53 实名 + 2 空名占位如实存空串 + 1 占位符
# 修正码（36）。三域编号独立（面板/主词条/副词条），
# 双层兜底下按码查名即可，无需分域接口。
PROPERTY_INFO_SNAPSHOT: dict[int, str] = {
    # 面板码 1-11（64 角色全员出现）
    1: '生命值',
    2: '攻击力',
    3: '防御力',
    4: '速度',
    5: '暴击率',
    6: '暴击伤害',
    7: '治疗量加成',
    8: '',  # 官方词典即空名（占位码，勿编名；显示层落「未知属性(pt=8)」）
    9: '能量恢复效率',
    10: '效果命中',
    11: '效果抵抗',
    # 12-24 偶数 = 七属性伤害提高（每角色面板恰带一条、与 element 一一对应）；
    # 13-25 奇数 = 七属性抗性提高（词典有名、面板未展示，如实固化）
    12: '物理属性伤害提高',
    13: '物理属性抗性提高',
    14: '火属性伤害提高',
    15: '火属性抗性提高',
    16: '冰属性伤害提高',
    17: '冰属性抗性提高',
    18: '雷属性伤害提高',
    19: '雷属性抗性提高',
    20: '风属性伤害提高',
    21: '风属性抗性提高',
    22: '量子属性伤害提高',
    23: '量子属性抗性提高',
    24: '虚数属性伤害提高',
    25: '虚数属性抗性提高',
    # 遗器词条码 26-36（26/28/30 基础值、27/29/31 平坦值、
    # 32-34 百分比组、35 词典保留码勿在词条解析依赖）
    26: '基础生命值',  # 词典 name 干净；其 relic 字段带占位符——快照存干净名
    27: '生命值',
    28: '基础攻击力',  # 同 26：name 干净、relic 带占位符
    29: '攻击力',
    30: '基础防御力',  # 同 26：name 干净、relic 带占位符
    31: '防御力',
    32: '生命值',  # 遗器词条语境即百分比组（词典 filter 名「生命值百分比」）
    33: '攻击力',  # 同 32（filter「攻击力百分比」）
    34: '防御力',  # 同 32（filter「防御力百分比」）
    35: '速度',  # 词典保留码（64 角样本未出现）
    36: '治疗量加成',  # 词典 name='受治疗量提高#1[f1]%' 含占位符——取词典
    # relic 字段的干净值固化（显示层同规则，见 resolve_property_cn）
    # 37-43：与 13-25 同中文名的抗性 Delta 组（词典有名、样本未出现，如实固化）
    37: '物理属性抗性提高',
    38: '火属性抗性提高',
    39: '冰属性抗性提高',
    40: '雷属性抗性提高',
    41: '风属性抗性提高',
    42: '量子属性抗性提高',
    43: '虚数属性抗性提高',
    # 词条主/副码 51-61（54/55 仅主词条、57 仅副词条）
    51: '速度',
    52: '暴击率',
    53: '暴击伤害',
    54: '能量恢复效率',
    55: '治疗量加成',
    56: '效果命中',
    57: '效果抵抗',
    58: '击破特攻',  # 面板值（词条码 59 的修饰目标，relic_properties 59→58 佐证）
    59: '击破特攻',  # 词条值（连结绳主词条/副词条）
    60: '能量上限',
    61: '',  # 官方词典即空名（占位码，勿编名）
    # 3.7 版面板新增行（71 全员常驻「欢愉度」；72 为其 Base 变体词典保留码）
    71: '欢愉度',
    72: '欢愉度',
}

# ---- 表 2：base_type 命途 → 中文 ----
# 全集 = 9：官方 wiki 筛选器全集、接口实测码域 1-9、genshin.py StarRailPath
# 枚举、StarRailRes paths.json 四源同构（任务书曾假设 14，被三源证伪，勿扩
# 10-14）。基准：9=欢愉（开拓者 id 8010，wiki「开拓者•欢愉」词条双确认）、
# 3=智识（姬子）。
BASE_TYPE_CN: dict[int, str] = {
    1: '毁灭',
    2: '巡猎',
    3: '智识',
    4: '同谐',
    5: '虚无',
    6: '存护',
    7: '丰饶',
    8: '记忆',
    9: '欢愉',
}

# ---- 表 3：element 英文码 → 属性中文（wiki 筛选器措辞）----
# element_id 掩码族 = 1/2/4/8/16/32/64（2 的幂位掩码，与响应 element_id 字段
# 一一对应）；封装以字符串码为准、element_id 仅作掩码运算用。陷阱：接口字符串
# 用 lightning，社区 StarRailRes 内部名用 Thunder——两套名字勿混淆。
ELEMENT_CN: dict[str, str] = {
    'physical': '物理',  # element_id=1
    'fire': '火',  # element_id=2
    'ice': '冰',  # element_id=4
    'lightning': '雷',  # element_id=8（接口码是 lightning，勿写成社区内部名 Thunder）
    'wind': '风',  # element_id=16
    'quantum': '量子',  # element_id=32
    'imaginary': '虚数',  # element_id=64
}

# ---- 表 4：遗器 pos → 部位中文 ----
# 1-4 = 隧洞遗器、5-6 = 位面饰品（wiki 遗器详情页逐部位措辞）。
# 撞域纪律：星魂 ranks[].pos 同取 1-6 但语义是星魂序号——两处禁共用本表。
RELIC_POS_CN: dict[int, str] = {
    1: '头部',
    2: '手部',
    3: '躯干',
    4: '脚部',
    5: '位面球',
    6: '连结绳',
}

# 表 4 附：部位 → 主词条可选集（配置封闭集，StarRailRes 四稀有度档交叉一致）。
# 供 validate_relic_main_affix 做轻校验；脚部 34（防御%）
# 属配置集但实测账号未观测到，如实保留。
RELIC_MAIN_AFFIX_ALLOWED: dict[int, frozenset[int]] = {
    1: frozenset({27}),  # 头部：生命值平坦（物理约束恒成立）
    2: frozenset({29}),  # 手部：攻击力平坦（物理约束恒成立）
    3: frozenset({32, 33, 34, 52, 53, 55, 56}),  # 躯干：无效果抵抗主词条
    4: frozenset({32, 33, 34, 51}),  # 脚部：生命%/攻击%/防御%/速度
    5: frozenset({32, 33, 34, 12, 14, 16, 18, 20, 22, 24}),  # 位面球：三百分比+七属性伤害
    6: frozenset({32, 33, 34, 54, 59}),  # 连结绳（55 治疗不在此列）
}


def _clean_display(text: object) -> str | None:
    """词典字段 → 可直接展示的干净名：非字符串、空串、含 ``#`` 均不可用。

    ``#`` 是官方格式占位符标记（实测 ``#1[f1]%`` / ``#1[i]`` 两形态），直接
    展示会把占位符漏给用户，按不可用处理（退另一字段或快照）。
    """
    if not isinstance(text, str):
        return None
    if not text or '#' in text:
        return None
    return text


def resolve_property_cn(pt: int, property_info: Mapping[int, PropertyNameInfo] | None) -> str:
    """property_type → 属性显示名（三层查表，miss 不抛异常）。

    层 1 动态词典：词条内按「干净可用值」取名，property_name_relic 优先、
    name 兜底，任一字段含 ``#`` 占位符或为空即弃用（实测 pt=36 靠 relic 字段
    规避占位符、pt=26/28/30 靠 name 字段规避）。层 2 硬编码快照。层 3 终兜底
    （官方有预占码位习惯，新码等响应词典带名后经层 1 自动前向兼容）。

    Args:
        pt: property_type 数字码。
        property_info: 响应原生词典透传（键须已归一为 int）；None = 无词典，
            直接走快照。

    Returns:
        属性中文名；三层全 miss（含快照空名占位码）时返回 ``未知属性(pt=N)``。
    """
    if property_info is not None:
        entry = property_info.get(pt)
        if entry is not None:
            relic_name = _clean_display(entry.get('property_name_relic'))
            if relic_name is not None:
                return relic_name
            plain_name = _clean_display(entry.get('name'))
            if plain_name is not None:
                return plain_name
    snapshot_name = PROPERTY_INFO_SNAPSHOT.get(pt)
    if snapshot_name:
        return snapshot_name
    log.warning(f'sr_codes: property_type={pt} 响应词典与快照均查无干净名，按未知属性兜底')
    return f'未知属性(pt={pt})'


def resolve_base_type_cn(bt: int) -> str:
    """base_type 数字码 → 命途中文名（miss 兜底不抛异常）。

    新命途实装时走兜底勿猜码。
    """
    name = BASE_TYPE_CN.get(bt)
    if name is not None:
        return name
    log.warning(f'sr_codes: base_type={bt} 查表 miss，按未知命途兜底')
    return f'未知命途(bt={bt})'


def resolve_element_cn(el: str) -> str:
    """element 英文码 → 属性中文名（miss 兜底不抛异常）。"""
    name = ELEMENT_CN.get(el)
    if name is not None:
        return name
    log.warning(f'sr_codes: element={el} 查表 miss，按未知元素兜底')
    return f'未知元素({el})'


def resolve_relic_pos_cn(pos: int) -> str:
    """遗器/饰品 pos → 部位中文名（miss 兜底不抛异常）。

    ⚠️ 只许传遗器/饰品字段；星魂 ranks[].pos 是星魂序号，禁传入本函数（撞域纪律）。
    """
    name = RELIC_POS_CN.get(pos)
    if name is not None:
        return name
    log.warning(f'sr_codes: relic pos={pos} 查表 miss，按未知部位兜底')
    return f'未知部位(pos={pos})'


def validate_relic_main_affix(pos: int, pt: int) -> bool:
    """遗器主词条合法性校验：pt 是否在 pos 部位的主词条可选集内。

    纯检查、不落日志——映射层拿返回值做 warning 哨兵（False = 数据异常，
    由调用方决定告警方式），本函数只给判值。

    Args:
        pos: 遗器部位码（1-6；未知部位一律 False）。
        pt: 主词条 property_type 码。

    Returns:
        pt 属于该部位配置封闭集时 True，否则 False。
    """
    allowed = RELIC_MAIN_AFFIX_ALLOWED.get(pos)
    if allowed is None:
        return False
    return pt in allowed
