"""崩坏:星穹铁道专属米游社封装：角色定位自动发现 + hkrpg 角色列表（轻/富双口径）。

设计出处：changes/mys-account-mcp/design.md §2.3 / §2.5 契约 5（v1 轻口径）、
changes/mys-roster-detail/design.md §2 契约 2/3/4（v2 中文字段与明细富口径）。
组合通用 ``one_dragon.mys.mys_client.MysClient``（不继承），在其通用
``request()`` 之上固化三件游戏专属事实：

1. 角色定位（``role.json`` 缓存）：崩铁 game_record 请求需 ``role_id`` 与
   ``server`` 两个定位参数；无缓存时经 binding 域角色发现接口自动取得
   （绝对 URL 形态、过滤国服 hkrpg 区服、``is_chosen`` 优先否则首个、
   ``role_id`` 一律字符串化——依据 miyoushe-api-flow.md §4.3），缓存被
   登出与换绑登录清除后自动重发现；
2. 角色列表映射：``hkrpg/api/index`` 的 ``data.avatar_list`` 到
   ``SrCharacter`` 冻结字段集——v1 八字段以 2026-11-03 实测响应为准
   （结构快照固化于测试仓 fixture，见 mys-account-mcp landing §3.4）；
   v2 增 ``element_cn``/``base_type_cn`` 两中文字段（码表经
   ``sr_od.mys.sr_codes`` 解析，接口层直接出中文，消费方零查表）。
   icon 等大体积字段不透传（本封装的消费方是练度盘点，不是资源下载）。
3. 角色明细映射（``get_characters_detail``）：打全量明细端点
   ``hkrpg/api/avatar/info``（``need_wiki=true`` 是五词典与明细数组的来源
   开关；``hkrpg/api/index`` 每角色只有轻口径 12 字段、不含遗器/星魂/
   行迹/面板——design.md §1 端点勘误，实机验收实证），对响应做富映射——
   遗器/位面饰品/星魂/行迹/属性面板到
   ``CharacterDetail`` 冻结字段集（契约 3/4）；词条显示名走
   ``sr_codes`` 三层查表，响应原生 ``data.property_info`` 键归一 int
   后作动态词典透传；遗器 lore desc/icon/figure/内部 id 等不透传。
4. 套装映射（changes/mys-relic-sets/design.md §2 契约 1/2）：遗器/饰品
   单件经 ``sr_relic_sets.resolve_set_name`` 件名反查套装名（miss 落
   「未知套装」字面量，告警由 resolve 层负责、本层不重复告警）；角色级
   收集 relic/ornament 件名经 ``build_set_effects`` 产出已激活套装效果
   条目 ``SrSetEffect``（未入常量的件名不产出条目）。v1 ``get_characters``
   轻口径不加套装字段（契约 4，外部行为零改动）。

会话失效透传（design.md §2.3）：``MysSessionExpired`` 原样上抛给上层
（MCP 工具层翻译成「请重新登录」并打过期标记），本模块不做任何处置。
"""

from dataclasses import asdict, dataclass

from one_dragon.mys.mys_client import MysClient
from one_dragon.mys.mys_const import ROLE_LIST_URL
from one_dragon.mys.mys_session import MysApiError, MysSessionExpired, SessionStore
from one_dragon.utils.log_utils import log
from sr_od.mys.sr_codes import (
    PropertyNameInfo,
    resolve_base_type_cn,
    resolve_element_cn,
    resolve_property_cn,
    resolve_relic_pos_cn,
    validate_relic_main_affix,
)
from sr_od.mys.sr_relic_sets import build_set_effects, resolve_set_name

#: 角色定位缓存文件内容（design.md §2.2 mys_session：``{"role_id","server"}``，
#: role_id 恒为字符串）
ROLE_CACHE_KEYS: frozenset[str] = frozenset({'role_id', 'server'})

#: 崩铁国服 game_biz 值（角色发现查询参数与响应过滤共用；国服登录会话只绑国服区服）
HSR_GAME_BIZ: str = 'hkrpg_cn'

#: 本地过期短路用的失效码（MysSessionExpired 需要继承 MysApiError 的 code；
#: 取会话失效码常量集中「Please login」语义的 10001，未发起请求故仅作标记用）
LOCAL_EXPIRED_CODE: int = 10001

#: 件名查无套装时的兜底套装名（resolve_set_name miss 落此字面量；告警由
#: resolve 层负责，映射层不重复告警——mys-relic-sets design.md §2 契约 1）
UNKNOWN_SET_NAME: str = '未知套装'


@dataclass(frozen=True)
class ConeSummary:
    """光锥摘要（冻结字段集，design.md §2.3）：name/level/rank/rarity。

    Attributes:
        name: 光锥名称。
        level: 光锥等级。
        rank: 光锥叠影数。
        rarity: 光锥稀有度（4-5 星）。
    """

    name: str
    level: int
    rank: int
    rarity: int


@dataclass(frozen=True)
class SrCharacter:
    """崩铁角色（v1 八字段 + v2 中文字段，冻结字段集——字段增删即契约失败）。

    字段集契约：changes/mys-roster-detail/design.md §2 契约 2（= v1 八字段
    〔mys-account-mcp design.md §2.3，以 2026-11-03 index 实测响应固化〕
    + ``element_cn``/``base_type_cn`` 两中文字段）；v1 存量消费方按既有
    字段序取值不受影响（新字段只追加在尾部）。icon/image 等大体积字段
    不透传。equip 在角色未装备光锥时为 None（实测存在此形态）。

    Attributes:
        id: 角色数字 id（游戏内部 id，如 1217）。
        name: 角色名（中文）。
        level: 角色等级。
        rarity: 稀有度（4-5 星）。
        rank: 星魂数（0-6）。
        element: 属性英文标识（如 fire/ice/wind/lightning）。
        base_type: 命途 id（数字）。
        equip: 装备光锥摘要；未装备为 None。
        element_cn: 属性中文名（ELEMENT_CN 查表；miss 落「未知元素(el)」）。
        base_type_cn: 命途中文名（BASE_TYPE_CN 查表；miss 落「未知命途(bt=N)」）。
    """

    id: int
    name: str
    level: int
    rarity: int
    rank: int
    element: str
    base_type: int
    equip: ConeSummary | None
    element_cn: str
    base_type_cn: str


@dataclass(frozen=True)
class SrPropertyEntry:
    """遗器词条（主/副同构，冻结字段集契约 4）。

    Attributes:
        name_cn: 属性显示中文名（sr_codes 三层查表：响应原生词典 → 快照 →
            「未知属性(pt=N)」终兜底，miss 不抛异常）。
        value: 词条数值字符串（原样透传，如 ``705`` / ``43.2%``）。
        times: 强化次数；主词条无强化恒为 0（照常透传 0）。
    """

    name_cn: str
    value: str
    times: int


@dataclass(frozen=True)
class SrRelic:
    """遗器/位面饰品单件（两数组同构，冻结字段集契约 4 + mys-relic-sets 契约 1）。

    Attributes:
        name: 件名（官方中文，如「翔鹰的长喙头盔」）。
        pos: 部位码——遗器/饰品坐标系：1-4=隧洞遗器、5-6=位面饰品，
            与 RELIC_POS_CN 同域；⚠️ 与星魂 ranks[].pos（星魂序号）撞值域，
            两处禁共用映射。
        pos_cn: 部位中文名（resolve_relic_pos_cn 查表；miss 落「未知部位」）。
        rarity: 稀有度（实测账号均为 5 星）。
        level: 强化等级（0-15）。
        main: 主词条。
        subs: 副词条列表（未出副词条为空列表）。
        set_name: 所属套装官方全名（resolve_set_name 件名反查；miss 落
            「未知套装」，告警在 resolve 层）。
    """

    name: str
    pos: int
    pos_cn: str
    rarity: int
    level: int
    main: SrPropertyEntry
    subs: list[SrPropertyEntry]
    set_name: str


@dataclass(frozen=True)
class SrRank:
    """星魂（冻结字段集契约 4）。

    Attributes:
        pos: 星魂序号——坐标系：星魂第 1-6 层，恒 1-6；⚠️ 与遗器部位码撞
            值域但语义无关，禁查 RELIC_POS_CN（本结构不设 pos_cn 字段即
            结构性防混淆）。
        name: 星魂名（官方中文）。
        desc: 星魂效果描述（官方中文）。
        is_unlocked: 是否已解锁——全量透传不过滤（解锁状态是消费方要的
            信息；ranks[] 实测恒 6 条，未解锁层照常在列）。
    """

    pos: int
    name: str
    desc: str
    is_unlocked: bool


@dataclass(frozen=True)
class SrSkillStage:
    """行迹分段文案（冻结字段集契约 4）。

    Attributes:
        name: 分段名（官方中文，如技能名）。
        desc: 分段效果描述（官方中文）。
        level: 该分段对应行迹等级。
    """

    name: str
    desc: str
    level: int


@dataclass(frozen=True)
class SrSkill:
    """行迹（冻结字段集契约 4）。

    Attributes:
        name: 技能类型标签（取响应 ``remake`` 字段，官方中文：普攻/战技/
            终结技/天赋/秘技/额外能力/属性加成/欢愉技——codes-draft.md
            实测词表）。
        level: 行迹等级。
        is_activated: 是否已激活。
        stages: 分段文案列表（终结技等多段技能一条以上）。
    """

    name: str
    level: int
    is_activated: bool
    stages: list[SrSkillStage]


@dataclass(frozen=True)
class SrPanelProperty:
    """角色面板属性行（冻结字段集契约 4）。

    Attributes:
        name_cn: 属性显示中文名（sr_codes 三层查表，同 SrPropertyEntry）。
        base: 基础值字符串（面板码 base/add/final 实测均为字符串，整数不带
            ``%``、百分比带 ``%``，展示层直接用；数值解析是消费方职责）。
        add: 词条加成值字符串。
        final: 最终面板值字符串。
    """

    name_cn: str
    base: str
    add: str
    final: str


@dataclass(frozen=True)
class SrSetEffectEntry:
    """已激活套装效果单档（冻结字段集，mys-relic-sets design.md §2 契约 2）。

    Attributes:
        count: 激活档位件数（2 或 4；只列已激活档，未激活档不出现在列表）。
        desc: 该档效果文案（官方 wiki 原文透传，不清洗富文本——契约 5）。
    """

    count: int
    desc: str


@dataclass(frozen=True)
class SrSetEffect:
    """角色已激活套装效果条目（冻结字段集，mys-relic-sets design.md §2 契约 2）。

    由佩戴件名按套装分组统计产出（build_set_effects，映射层
    ``_build_set_effects`` 做字段投影）；未入套装常量的件名不产出条目。
    列表排序：piece_count 降序、同级按 set_name 升序（稳定输出语义）。

    Attributes:
        set_name: 官方套装全名。
        kind: 套装类别——``'cavern'``=隧洞遗器、``'ornament'``=位面饰品。
        piece_count: 该套实际佩戴件数。
        pieces: 该套实际佩戴件名列表（佩戴顺序 = 响应数组顺序）。
        activated: 已激活档列表（隧洞套 2 件档 + piece_count=4 时的 4 件档；
            饰品套 2 件档）。
    """

    set_name: str
    kind: str
    piece_count: int
    pieces: list[str]
    activated: list[SrSetEffectEntry]


@dataclass(frozen=True)
class CharacterDetail:
    """角色全量明细（冻结字段集契约 3——字段增删即契约失败）。

    全量明细端点 ``hkrpg/api/avatar/info`` 富映射（``hkrpg/api/index`` 只有
    轻口径字段、不含明细——design.md §1 端点勘误）：轻口径 10 字段
    语义不变，追加遗器/饰品/星魂/行迹/面板/已激活套装效果六组明细
    （套装效果组为 mys-relic-sets 契约 2）。desc(遗器 lore)/icon/
    figure/URL/point_id 等大体积与内部形态字段一律不透传（契约 4 清单）。

    Attributes:
        id: 角色数字 id（游戏内部 id）。
        name: 角色名（中文）。
        level: 角色等级。
        rarity: 稀有度（4-5 星）。
        rank: 星魂数（0-6）。
        element: 属性英文标识。
        element_cn: 属性中文名（查表）。
        base_type: 命途 id（数字）。
        base_type_cn: 命途中文名（查表）。
        equip: 装备光锥摘要；未装备为 None。
        relics: 隧洞遗器列表（pos 1-4）。
        ornaments: 位面饰品列表（pos 5-6，与遗器同构映射）。
        ranks: 星魂列表（恒 6 条，解锁状态全量透传）。
        skills: 行迹列表。
        properties: 面板属性行列表（遍历渲染，不按固定行数假设）。
        set_effects: 已激活套装效果条目列表（build_set_effects 分组统计；
            无任何激活档〔如全未佩戴〕为空列表）。
    """

    id: int
    name: str
    level: int
    rarity: int
    rank: int
    element: str
    element_cn: str
    base_type: int
    base_type_cn: str
    equip: ConeSummary | None
    relics: list[SrRelic]
    ornaments: list[SrRelic]
    ranks: list[SrRank]
    skills: list[SrSkill]
    properties: list[SrPanelProperty]
    set_effects: list[SrSetEffect]


class SrMysClient:
    """崩铁专属米游社客户端：组合通用 client，提供角色列表获取。"""

    def __init__(self, client: MysClient, store: SessionStore) -> None:
        """两参必填（design.md §2.3）：client 提供通用请求管线，store 提供
        角色定位缓存与过期标记读取——同一 store 实例须贯穿装配链（同锁）。"""
        self._client: MysClient = client
        self._store: SessionStore = store

    def get_characters(self) -> list[SrCharacter]:
        """获取崩铁角色列表（过期短路 → 角色定位 → index → 冻结字段映射）。

        1. 过期短路：本地会话已标记过期时直接抛 ``MysSessionExpired``，
           不发起注定失败的请求（design.md §2.3 判据第 1 条）；
        2. 角色定位：读 ``role.json`` 缓存（server 取缓存值，不硬编码）；
           无缓存则走角色自动发现并写回缓存；
        3. 请求 ``hkrpg/api/index`` 取 ``data.avatar_list``；
        4. 逐条映射 ``SrCharacter``（缺失 avatar_list 按协议错误上抛，
           不静默返回空列表掩盖响应形态漂移）。

        Raises:
            MysSessionExpired: 本地过期标记命中，或服务端会话失效码（透传）。
            MysApiError: 角色发现失败 / 响应形态漂移 / 其它业务错误（透传）。
        """
        if self._store.is_expired():
            raise MysSessionExpired(LOCAL_EXPIRED_CODE, '本地会话已标记过期，请重新登录')
        role_id, server = self._resolve_role()
        data = self._client.request('hkrpg/api/index', {'role_id': role_id, 'server': server})
        avatar_list = data.get('avatar_list')
        if not isinstance(avatar_list, list):
            raise MysApiError(-1, 'index 响应缺少 avatar_list 字段')
        return [_map_character(avatar) for avatar in avatar_list]

    def get_characters_detail(self) -> list[CharacterDetail]:
        """获取崩铁角色全量明细（``hkrpg/api/avatar/info`` 富映射口径）。

        管线前置与 v1 轻口径一致（过期短路 → 角色定位），端点不同：avatar/info
        需带 ``need_wiki=true`` 才回 ``property_info`` 等五词典与全量明细数组
        （design.md §1 端点勘误），一次调用只打一次接口；响应原生
        ``data.property_info``（键为字符串）归一 int 后作动态词典透传给词条/
        面板中文名查表（sr_codes 三层查表契约）。``avatar_list`` 逐条富映射
        ``CharacterDetail``（契约 3）；缺失 avatar_list 按协议错误上抛，不
        静默返回空列表掩盖响应形态漂移。

        Raises:
            MysSessionExpired: 本地过期标记命中，或服务端会话失效码（透传）。
            MysApiError: 角色发现失败 / 响应形态漂移 / 其它业务错误（透传）。
        """
        if self._store.is_expired():
            raise MysSessionExpired(LOCAL_EXPIRED_CODE, '本地会话已标记过期，请重新登录')
        role_id, server = self._resolve_role()
        data = self._client.request(
            'hkrpg/api/avatar/info',
            {'need_wiki': 'true', 'role_id': role_id, 'server': server},
        )
        avatar_list = data.get('avatar_list')
        if not isinstance(avatar_list, list):
            raise MysApiError(-1, 'avatar/info 响应缺少 avatar_list 字段')
        property_info = _normalize_property_info(data.get('property_info'))
        return [_map_character_detail(avatar, property_info) for avatar in avatar_list]

    def _resolve_role(self) -> tuple[str, str]:
        """解析角色定位 (role_id, server)：缓存优先，无缓存自动发现。

        缓存损坏（非 dict / 字段缺失或类型不符）视同无缓存，走重发现——
        旧缓存不可信时硬用只会得到注定失败的 index 请求。
        """
        cached = self._store.load_role()
        if isinstance(cached, dict):
            role_id = cached.get('role_id')
            server = cached.get('server')
            if isinstance(role_id, str) and role_id and isinstance(server, str) and server:
                return role_id, server
        return self._discover_role()

    def _discover_role(self) -> tuple[str, str]:
        """角色自动发现：binding 域 getUserGameRolesByCookie（绝对 URL 形态，
        查询 game_biz=hkrpg_cn）→ 过滤崩铁国服区服 → is_chosen 优先否则首个
        → role_id 字符串化 → 写入 role.json 缓存。

        Raises:
            MysApiError: 响应缺 list / 无崩铁国服角色（定位参数无从取得，
                后续 index 必败，不上抛原始空结果掩盖语义）。
        """
        data = self._client.request(ROLE_LIST_URL, {'game_biz': HSR_GAME_BIZ})
        roles = data.get('list')
        if not isinstance(roles, list):
            raise MysApiError(-1, '角色发现响应缺少 list 字段')
        hsr_roles = [
            role for role in roles
            if isinstance(role, dict) and role.get('game_biz') == HSR_GAME_BIZ
        ]
        if not hsr_roles:
            raise MysApiError(-1, '未发现崩坏:星穹铁道（国服）绑定角色')
        chosen = next((role for role in hsr_roles if role.get('is_chosen') is True), hsr_roles[0])
        role_id = str(chosen.get('game_uid'))
        server = chosen.get('region')
        if not isinstance(server, str) or not server:
            raise MysApiError(-1, '角色发现响应缺少 region（区服）字段')
        self._store.save_role({'role_id': role_id, 'server': server})
        return role_id, server


def _normalize_property_info(raw: object) -> dict[int, PropertyNameInfo]:
    """响应 ``data.property_info`` → 键归一 int 的动态词典（sr_codes 层 1 入参）。

    实测响应键是字符串（如 ``"1"``），sr_codes 契约要求调用侧归一；只投影
    显示名两字段（icon 等 URL 字段不进契约）；非 dict 词条与非整型键跳过而
    非抛错——词典局部异常不该中断整份角色明细映射（缺词典时查表自动退快照）。
    """
    if not isinstance(raw, dict):
        return {}
    normalized: dict[int, PropertyNameInfo] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        try:
            pt = int(key)
        except (TypeError, ValueError):
            continue
        normalized[pt] = PropertyNameInfo(
            name=value.get('name'),
            property_name_relic=value.get('property_name_relic'),
        )
    return normalized


def _map_equip(equip_raw: object) -> ConeSummary | None:
    """equip 字段 → 光锥摘要；实测 null（未装备光锥，2026-11-03 实测 64 角色
    中 7 例）映射 None。equip dict 实测含 desc/icon/id 等大字段，只取摘要四元组。
    """
    if not isinstance(equip_raw, dict):
        return None
    return ConeSummary(
        name=equip_raw.get('name'),
        level=equip_raw.get('level'),
        rank=equip_raw.get('rank'),
        rarity=equip_raw.get('rarity'),
    )


def _map_character(avatar: dict) -> SrCharacter:
    """单条 avatar_list 条目 → 冻结字段集映射（icon 等大字段不透传）。

    v2 中文字段在映射时经码表助手解析（miss 不抛异常，落兜底文案）。
    """
    return SrCharacter(
        id=avatar.get('id'),
        name=avatar.get('name'),
        level=avatar.get('level'),
        rarity=avatar.get('rarity'),
        rank=avatar.get('rank'),
        element=avatar.get('element'),
        base_type=avatar.get('base_type'),
        equip=_map_equip(avatar.get('equip')),
        element_cn=resolve_element_cn(avatar.get('element')),
        base_type_cn=resolve_base_type_cn(avatar.get('base_type')),
    )


def _map_property_entry(item: dict, property_info: dict[int, PropertyNameInfo]) -> SrPropertyEntry:
    """单条词条（relic ``main_property`` 与 ``properties[]`` 条目同构）→
    SrPropertyEntry。``times=0``（主词条无强化）照常透传 0；
    ``is_preview`` 为内部形态字段不透传。
    """
    return SrPropertyEntry(
        name_cn=resolve_property_cn(item.get('property_type'), property_info),
        value=item.get('value'),
        times=item.get('times'),
    )


def _map_property_entry_list(
    raw: object, property_info: dict[int, PropertyNameInfo]
) -> list[SrPropertyEntry]:
    """词条数组 → SrPropertyEntry 列表（非 dict 条目跳过；字段缺失/形态漂移
    退空列表而非抛错——词条层异常不应中断整份角色明细）。"""
    if not isinstance(raw, list):
        return []
    return [_map_property_entry(item, property_info) for item in raw if isinstance(item, dict)]


def _resolve_set_name_or_unknown(piece_name: object) -> str:
    """件名 → 套装名（resolve 反查；miss 或件名缺失落「未知套装」兜底）。

    告警责任在 resolve 层（``resolve_set_name`` miss 时 warning 恰一次），
    本层不重复告警（mys-relic-sets design.md §2 契约 1）；件名非字符串
    （实测正常数据恒为字符串，此处为形态漂移兜底）不进 resolve、静默落
    兜底——单件异常不中断整份角色明细映射（与 _map_relic_list 容错纪律一致）。
    """
    if not isinstance(piece_name, str):
        return UNKNOWN_SET_NAME
    resolved = resolve_set_name(piece_name)
    return resolved if resolved is not None else UNKNOWN_SET_NAME


def _map_relic(item: dict, property_info: dict[int, PropertyNameInfo]) -> SrRelic:
    """单件遗器/饰品 → SrRelic（relics/ornaments 两数组同构，共用本映射）。

    主词条先过 ``validate_relic_main_affix`` 轻校验：False = 部位与词条码
    组合超出配置封闭集（数据异常哨兵），打 warning 但**不中断映射**——
    单件异常数据仍应随整份明细返回（显示名照常三层查表）。套装名经
    ``resolve_set_name`` 件名反查（miss 落「未知套装」，告警在 resolve
    层）。lore desc/icon/id/is_preview 不透传。
    """
    pos = item.get('pos')
    main_raw = item.get('main_property')
    main_pt = main_raw.get('property_type') if isinstance(main_raw, dict) else None
    main = _map_property_entry(main_raw if isinstance(main_raw, dict) else {}, property_info)
    if not validate_relic_main_affix(pos, main_pt):
        log.warning(
            f'sr_mys_client: 遗器主词条校验未通过（数据异常哨兵，映射继续）: '
            f'pos={pos} pt={main_pt}'
        )
    return SrRelic(
        name=item.get('name'),
        pos=pos,
        pos_cn=resolve_relic_pos_cn(pos),
        rarity=item.get('rarity'),
        level=item.get('level'),
        main=main,
        subs=_map_property_entry_list(item.get('properties'), property_info),
        set_name=_resolve_set_name_or_unknown(item.get('name')),
    )


def _map_relic_list(
    raw: object, property_info: dict[int, PropertyNameInfo]
) -> list[SrRelic]:
    """遗器/饰品数组 → SrRelic 列表（字段缺失/形态漂移退空列表）。"""
    if not isinstance(raw, list):
        return []
    return [_map_relic(item, property_info) for item in raw if isinstance(item, dict)]


def _map_rank(item: dict) -> SrRank:
    """单条星魂 → SrRank（全量透传解锁状态不过滤；icon/id 不透传）。

    ⚠️ pos 是星魂序号（1-6），禁查 RELIC_POS_CN（撞域纪律）。
    """
    return SrRank(
        pos=item.get('pos'),
        name=item.get('name'),
        desc=item.get('desc'),
        is_unlocked=item.get('is_unlocked'),
    )


def _map_rank_list(raw: object) -> list[SrRank]:
    """星魂数组 → SrRank 列表（字段缺失/形态漂移退空列表）。"""
    if not isinstance(raw, list):
        return []
    return [_map_rank(item) for item in raw if isinstance(item, dict)]


def _map_skill(item: dict) -> SrSkill:
    """单条行迹 → SrSkill（name 取 ``remake`` 技能类型标签；point_id/
    item_url/anchor 等内部形态字段不透传）。"""
    stages_raw = item.get('skill_stages')
    stages = [
        SrSkillStage(
            name=stage.get('name'),
            desc=stage.get('desc'),
            level=stage.get('level'),
        )
        for stage in (stages_raw if isinstance(stages_raw, list) else [])
        if isinstance(stage, dict)
    ]
    return SrSkill(
        name=item.get('remake'),
        level=item.get('level'),
        is_activated=item.get('is_activated'),
        stages=stages,
    )


def _map_skill_list(raw: object) -> list[SrSkill]:
    """行迹数组 → SrSkill 列表（字段缺失/形态漂移退空列表）。"""
    if not isinstance(raw, list):
        return []
    return [_map_skill(item) for item in raw if isinstance(item, dict)]


def _map_panel_property(
    item: dict, property_info: dict[int, PropertyNameInfo]
) -> SrPanelProperty:
    """单条面板属性行 → SrPanelProperty（base/add/final 字符串数值透传）。"""
    return SrPanelProperty(
        name_cn=resolve_property_cn(item.get('property_type'), property_info),
        base=item.get('base'),
        add=item.get('add'),
        final=item.get('final'),
    )


def _map_panel_property_list(
    raw: object, property_info: dict[int, PropertyNameInfo]
) -> list[SrPanelProperty]:
    """面板属性行数组 → SrPanelProperty 列表（遍历渲染，不按固定行数假设；
    字段缺失/形态漂移退空列表）。"""
    if not isinstance(raw, list):
        return []
    return [_map_panel_property(item, property_info) for item in raw if isinstance(item, dict)]


def _build_set_effects(relics: list[SrRelic], ornaments: list[SrRelic]) -> list[SrSetEffect]:
    """佩戴件名收集 → ``build_set_effects`` → SrSetEffect 冻结结构列表（契约 2）。

    分桶由本映射层负责（relics/ornaments 两数组即分桶，对齐 build_set_effects
    的入参约定）；dict 条目到冻结结构的字段投影在此收口。未知件名已在逐件
    映射时经 ``resolve_set_name`` 告警，此处按 build 层契约静默跳过不产出
    条目（不重复告警）。
    """
    entries = build_set_effects(
        [relic.name for relic in relics],
        [ornament.name for ornament in ornaments],
    )
    return [
        SrSetEffect(
            set_name=entry['set_name'],
            kind=entry['kind'],
            piece_count=entry['piece_count'],
            pieces=entry['pieces'],
            activated=[
                SrSetEffectEntry(count=act['count'], desc=act['desc'])
                for act in entry['activated']
            ],
        )
        for entry in entries
    ]


def _map_character_detail(
    avatar: dict, property_info: dict[int, PropertyNameInfo]
) -> CharacterDetail:
    """单条 avatar_list 条目 → CharacterDetail 冻结字段集富映射（契约 3/4）。

    轻口径字段语义与 ``_map_character`` 一致；明细六组：遗器/饰品同构映射
    （逐件反查套装名）、已激活套装效果（build_set_effects 按佩戴件名分组
    统计）、星魂全量透传（is_unlocked 不过滤）、行迹取 remake/skill_stages、
    面板遍历渲染。desc/icon/figure_path/element_id/point_id/servant_detail/
    special_skills/cur_enhanced_id 等实测在场字段一律不透传（契约 4 清单）。
    """
    relics = _map_relic_list(avatar.get('relics'), property_info)
    ornaments = _map_relic_list(avatar.get('ornaments'), property_info)
    return CharacterDetail(
        id=avatar.get('id'),
        name=avatar.get('name'),
        level=avatar.get('level'),
        rarity=avatar.get('rarity'),
        rank=avatar.get('rank'),
        element=avatar.get('element'),
        element_cn=resolve_element_cn(avatar.get('element')),
        base_type=avatar.get('base_type'),
        base_type_cn=resolve_base_type_cn(avatar.get('base_type')),
        equip=_map_equip(avatar.get('equip')),
        relics=relics,
        ornaments=ornaments,
        ranks=_map_rank_list(avatar.get('ranks')),
        skills=_map_skill_list(avatar.get('skills')),
        properties=_map_panel_property_list(avatar.get('properties'), property_info),
        set_effects=_build_set_effects(relics, ornaments),
    )


def character_to_dict(character: SrCharacter | CharacterDetail) -> dict:
    """角色/角色明细转 JSON 可序列化 dict（MCP 信封 data 载荷用；嵌套
    ConeSummary/SrRelic 等冻结结构一并展开）。"""
    return asdict(character)
