"""崩坏:星穹铁道专属米游社封装：角色定位自动发现 + hkrpg 角色列表。

设计出处：changes/mys-account-mcp/design.md §2.3 / §2.5 契约 5。组合通用
``one_dragon.mys.mys_client.MysClient``（不继承），在其通用 ``request()``
之上固化两件游戏专属事实：

1. 角色定位（``role.json`` 缓存）：崩铁 game_record 请求需 ``role_id`` 与
   ``server`` 两个定位参数；无缓存时经 binding 域角色发现接口自动取得
   （绝对 URL 形态、过滤国服 hkrpg 区服、``is_chosen`` 优先否则首个、
   ``role_id`` 一律字符串化——依据 miyoushe-api-flow.md §4.3），缓存被
   登出与换绑登录清除后自动重发现；
2. 角色列表映射：``hkrpg/api/index`` 的 ``data.avatar_list`` 到
   ``HsrCharacter`` 冻结字段集——字段集以 2026-11-03 实测响应为准
   （结构快照固化于测试仓 fixture，见 landing §3.4）；icon 等大体积字段
   不透传（本封装的消费方是练度盘点，不是资源下载）。

会话失效透传（design.md §2.3）：``MysSessionExpired`` 原样上抛给上层
（MCP 工具层翻译成「请重新登录」并打过期标记），本模块不做任何处置。
"""

from dataclasses import asdict, dataclass

from one_dragon.mys.mys_client import MysClient
from one_dragon.mys.mys_const import ROLE_LIST_URL
from one_dragon.mys.mys_session import MysApiError, MysSessionExpired, SessionStore

#: 角色定位缓存文件内容（design.md §2.2 mys_session：``{"role_id","server"}``，
#: role_id 恒为字符串）
ROLE_CACHE_KEYS: frozenset[str] = frozenset({'role_id', 'server'})

#: 崩铁国服 game_biz 值（角色发现查询参数与响应过滤共用；国服登录会话只绑国服区服）
HSR_GAME_BIZ: str = 'hkrpg_cn'

#: 本地过期短路用的失效码（MysSessionExpired 需要继承 MysApiError 的 code；
#: 取会话失效码常量集中「Please login」语义的 10001，未发起请求故仅作标记用）
LOCAL_EXPIRED_CODE: int = 10001


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
class HsrCharacter:
    """崩铁角色（冻结字段集，design.md §2.3 / §2.5 契约 5——字段增删即契约失败）。

    字段集以 index 实测响应（2026-11-03 trace 条目）覆盖固化；icon/image 等
    大体积字段不透传。equip 在角色未装备光锥时为 None（实测存在此形态）。

    Attributes:
        id: 角色数字 id（游戏内部 id，如 1217）。
        name: 角色名（中文）。
        level: 角色等级。
        rarity: 稀有度（4-5 星）。
        rank: 星魂数（0-6）。
        element: 属性英文标识（如 fire/ice/wind/lightning）。
        base_type: 命途 id（数字）。
        equip: 装备光锥摘要；未装备为 None。
    """

    id: int
    name: str
    level: int
    rarity: int
    rank: int
    element: str
    base_type: int
    equip: ConeSummary | None


class HsrMysClient:
    """崩铁专属米游社客户端：组合通用 client，提供角色列表获取。"""

    def __init__(self, client: MysClient, store: SessionStore) -> None:
        """两参必填（design.md §2.3）：client 提供通用请求管线，store 提供
        角色定位缓存与过期标记读取——同一 store 实例须贯穿装配链（同锁）。"""
        self._client: MysClient = client
        self._store: SessionStore = store

    def get_characters(self) -> list[HsrCharacter]:
        """获取崩铁角色列表（过期短路 → 角色定位 → index → 冻结字段映射）。

        1. 过期短路：本地会话已标记过期时直接抛 ``MysSessionExpired``，
           不发起注定失败的请求（design.md §2.3 判据第 1 条）；
        2. 角色定位：读 ``role.json`` 缓存（server 取缓存值，不硬编码）；
           无缓存则走角色自动发现并写回缓存；
        3. 请求 ``hkrpg/api/index`` 取 ``data.avatar_list``；
        4. 逐条映射 ``HsrCharacter``（缺失 avatar_list 按协议错误上抛，
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


def _map_character(avatar: dict) -> HsrCharacter:
    """单条 avatar_list 条目 → 冻结字段集映射（icon 等大字段不透传）。

    equip 实测双形态：dict（含 desc/icon/id/level/name/rank/rarity）或 null
    （未装备光锥，2026-11-03 实测 64 角色中 7 例）——后者映射 None。
    """
    equip_raw = avatar.get('equip')
    equip = ConeSummary(
        name=equip_raw.get('name'),
        level=equip_raw.get('level'),
        rank=equip_raw.get('rank'),
        rarity=equip_raw.get('rarity'),
    ) if isinstance(equip_raw, dict) else None
    return HsrCharacter(
        id=avatar.get('id'),
        name=avatar.get('name'),
        level=avatar.get('level'),
        rarity=avatar.get('rarity'),
        rank=avatar.get('rank'),
        element=avatar.get('element'),
        base_type=avatar.get('base_type'),
        equip=equip,
    )


def character_to_dict(character: HsrCharacter) -> dict:
    """角色转 JSON 可序列化 dict（MCP 信封 data 载荷用；嵌套 ConeSummary 一并展开）。"""
    return asdict(character)
