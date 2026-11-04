"""米游社账号 MCP 四工具 + 访问控制器（``MysAccessController``）。

设计出处：changes/mys-account-mcp/design.md §2.4（装配/状态机/并发语义/三工具/
知情声明原文）+ §2.5 契约 6 + §2.6（凭据红线）；changes/mys-roster-detail/
design.md §2 契约 5（第四工具 ``mys_get_roster_detail``，信封语义与
``mys_get_characters`` 完全一致，复用同一状态机与信封文案）。职责分界（design.md §2.1）：
验证的「单轮」在 ``one_dragon.mys.mys_client``（3.3 交付），验证的「循环」在
本控制器——持有 verifier、attempt 计数上限、每轮重开验证页。

并发语义（design.md §2.4 定死，控制器锁串行化入口）：
- awaiting_ticket 期二次 ``mys_login``：不重复登录——新账密即收即弃（不存储
  不加密），返回现存 ``verification_required`` 信封 + 现存 URL；
- awaiting_ticket 期 ``mys_get_characters`` 与 ``mys_get_roster_detail``：
  返回 ``verification_required``
  信封（附现存 URL），不裸打请求；
- awaiting_ticket 期 ``mys_logout``：执行登出 + 状态回 idle + verifier 关闭，
  此后的迟到票据被状态闸丢弃（显式登出后任何迟到验证结果不得静默重建会话）；
- 迟到票据双重防护：回传处理入口先查状态 == awaiting_ticket，再把
  ``payload.session_id`` 与控制器当前 challenge 再比对一道（T-3 评审强制判据
  ——verifier 层 409 配对校验之外的第二道闸，双保险）；
- ``wait_ticket`` 超时不改状态：该路径属阻塞式消费（GUI/CLI），MCP 走
  ``on_ticket`` 回调，本控制器不调用 ``wait_ticket``，无此路径；
- MCP server 重启：verifier 端口死亡，用户重新 ``mys_login`` 即新建 verifier
  （会话已落盘且未标记过期 → ``already_logged_in``；已标记过期 → 跳过判定
  走正常登录，成功后整体覆盖、标记随覆盖消失）。

会话过期处置（design.md §2.4/§2.6）：``mys_get_characters`` 与
``mys_get_roster_detail`` 收到 ``MysSessionExpired`` →
``store.mark_expired()``（**不清任何文件**，重登失败时
旧数据原样保留）→ 信封 ``session_expired``；清除仅发生于用户显式登出或登录
成功整体覆盖。

信封脱敏（landing §3.4 判据）：任何信封的 message/data 不含 cookie/token/
密码——信封内容只有固定文案、验证页 URL、角色列表与角色明细（明细载荷经
``character_to_dict`` 序列化，冻结字段集不含任何凭据字段）；异常文本只透传
``MysApiError`` 的 retcode 与服务端 message（client 层已保证不含本机凭据）。

FastMCP 工具入参日志核查结论（landing §3.4 判据，实读 mcp 1.28.1 源码）：
框架层不记录工具入参——调用链 ``ToolManager.call_tool`` → ``Tool.run`` →
``FuncMetadata.call_fn_with_arg_validation`` 全程无携带 arguments 的日志语句；
lowlevel server 仅记录请求类型名（``type(req).__name__``）。故无需框架层脱敏；
本模块亦不在任何日志输出账密（密码只在 ``client.login`` 调用栈内存）。
"""

import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from one_dragon.mys.aigis_verifier import AigisVerifier
from one_dragon.mys.mys_client import AigisChallenge, MysClient
from one_dragon.mys.mys_device import DeviceIdentity
from one_dragon.mys.mys_http import HttpSend, RequestsHttpSend
from one_dragon.mys.mys_session import MysApiError, MysSessionExpired, SessionStore
from one_dragon.utils import os_utils
from sr_od.backend.backend_context import SrBackendContext
from sr_od.mys.sr_mys_client import SrMysClient, character_to_dict

#: 控制器状态（design.md §2.4：idle / awaiting_ticket 两态）
STATE_IDLE: str = 'idle'
STATE_AWAITING_TICKET: str = 'awaiting_ticket'

#: 验证重试上限（design.md §2.4 验证循环：最多重复解题 3 次）
MAX_VERIFY_ATTEMPTS: int = 3

#: 数据接口风控（1034）专属文案（design.md §2.4 mys_get_characters 原文；
#: 1034 验证链本迭代不实现，design.md §1 明确不解决项 7）
RISK_CONTROL_1034_MESSAGE: str = '数据接口触发风控验证，本版本未实现该验证链，请稍后重试或反馈'

#: 会话过期信封文案（design.md §2.4 mys_get_characters 原文语义）
SESSION_EXPIRED_MESSAGE: str = '数据已过期，请重新登录（mys_login）；本机数据不受影响'

#: 验证引导文案（design.md §2.4 mys_login verification_required 信封原文）
VERIFICATION_REQUIRED_MESSAGE: str = (
    '请在浏览器打开以下地址完成人机验证；若被要求再次验证请重复解题（最多 3 次），'
    '完成后用 mys_get_characters 验证登录结果'
)


def _envelope(status: str, message: str | None = None, data: object = None) -> dict:
    """统一信封（design.md §2.5 契约 6）：三键齐全，data 默认 None。"""
    return {'status': status, 'message': message, 'data': data}


class MysAccessController:
    """米游社账号访问控制器：装配链持有者 + 验证循环状态机。

    模块级单例由 ``_get_controller`` 持有（进程级生命周期）；测试直接构造并
    注入假 http_send 与假 verifier 工厂（零真实副作用）。
    """

    def __init__(
        self,
        session_dir: Path,
        http_send: HttpSend,
        verifier_factory: Callable[[], AigisVerifier],
    ) -> None:
        """装配链（design.md §2.4）：session_dir → SessionStore →
        DeviceIdentity → MysClient；verifier 工厂在每次进入验证轮时调用一次
        （verifier close 后实例不可复用，重开验证须新实例——aigis_verifier
        生命周期约定）。

        三参必填无默认：requests 真实实装与 webbrowser 打开回调由运行入口
        （模块级单例装配）传入，测试注入假实现——缺任一参数构造即失败。

        Args:
            session_dir: 实例 mys 会话目录（``config/<实例>/mys``）。
            http_send: HTTP 发送实装，同一实例贯穿 DeviceIdentity 与
                MysClient（装配断言判据：同实例）。
            verifier_factory: 每轮验证新建验证页宿主的工厂。
        """
        self._store: SessionStore = SessionStore(session_dir, threading.Lock())
        self._device: DeviceIdentity = DeviceIdentity(self._store, http_send)
        self._client: MysClient = MysClient(self._store, self._device, http_send)
        self._sr_client: SrMysClient = SrMysClient(self._client, self._store)
        self._verifier_factory: Callable[[], AigisVerifier] = verifier_factory
        # 控制器锁：三工具入口与票据回传回调全部经它串行化（design.md §2.4）；
        # SessionStore 内部另有同实例锁，两层锁保护对象不同（状态机 / 落盘）
        self._lock: threading.Lock = threading.Lock()
        self._state: str = STATE_IDLE
        self._verifier: AigisVerifier | None = None
        self._verify_url: str | None = None
        self._current_challenge: AigisChallenge | None = None
        self._attempt: int = 0
        # 验证循环超限/失败的留档错误；信封在用户下次调用时体现 error 一次
        # （design.md §2.4 验证循环第 2 步）。None = 无留档错误。
        self._last_error: str | None = None

    @property
    def store(self) -> SessionStore:
        """装配链中的会话存储（装配断言与诊断用）。"""
        return self._store

    @property
    def client(self) -> MysClient:
        """装配链中的通用客户端（装配断言与诊断用）。"""
        return self._client

    @property
    def device(self) -> DeviceIdentity:
        """装配链中的设备身份（装配断言与诊断用）。"""
        return self._device

    # ---- 三工具业务入口（返回统一信封，不抛业务异常）----

    def login(self, username: str, password: str) -> dict:
        """登录入口（状态机 idle 分支 + awaiting 复用分支）。

        已登录判定（design.md §2.4 定死）：会话存在且 cookies 非空且未标记
        过期 → ``already_logged_in``；不主动探测官方接口。已标记过期则跳过
        判定走正常登录（成功后 ``save_session_full`` 整体覆盖，标记随覆盖
        消失）。awaiting_ticket 期新账密即收即弃，复用现存验证信封。
        登录失败（-3208/-3235/其它）不清任何落盘文件。
        """
        with self._lock:
            if self._last_error is not None:
                error = self._last_error
                self._last_error = None
                return _envelope('error', error)
            if self._state == STATE_AWAITING_TICKET:
                # 二次登录：新账密即收即弃（不存储不加密），复用现存信封与 URL
                return _envelope(
                    'verification_required', VERIFICATION_REQUIRED_MESSAGE, {'url': self._verify_url}
                )
            if self._is_logged_in():
                return _envelope('already_logged_in', '已存在有效登录会话，无需重复登录')
            try:
                result = self._client.login(username, password)
            except MysApiError as e:
                detail = e.message if e.message else '无服务端文案'
                return _envelope('error', f'登录失败(retcode={e.code}): {detail}')
            if result.status == 'ok':
                return _envelope('success', '登录成功')
            self._enter_verification(result.challenge)
            return _envelope(
                'verification_required', VERIFICATION_REQUIRED_MESSAGE, {'url': self._verify_url}
            )

    def logout(self) -> dict:
        """登出入口（幂等）：清会话（session.json + role.json，保留
        device.json 设备锚）+ awaiting 期取消验证轮 + 清留档错误。"""
        with self._lock:
            if self._state == STATE_AWAITING_TICKET:
                # awaiting 期登出 = 取消验证（design.md §2.4）：状态复位 +
                # verifier 关闭；此后迟到票据被 _on_ticket 状态闸丢弃
                self._reset_verification()
            self._client.logout()
            self._last_error = None
            return _envelope('success', '已登出，本机登录会话与角色定位缓存已清除')

    def get_characters(self) -> dict:
        """角色列表入口：awaiting 期不裸打请求；``MysSessionExpired`` → 打
        过期标记（不清任何文件）+ ``session_expired``；1034 → 专属文案；
        其余业务错误 → ``error`` 透传 retcode。"""
        with self._lock:
            if self._last_error is not None:
                error = self._last_error
                self._last_error = None
                return _envelope('error', error)
            if self._state == STATE_AWAITING_TICKET:
                return _envelope(
                    'verification_required', VERIFICATION_REQUIRED_MESSAGE, {'url': self._verify_url}
                )
            try:
                characters = self._sr_client.get_characters()
            except MysSessionExpired:
                # 过期处置（design.md §2.4/§2.6）：只打标记不清任何文件
                self._store.mark_expired()
                return _envelope('session_expired', SESSION_EXPIRED_MESSAGE)
            except MysApiError as e:
                if e.code == 1034:
                    return _envelope('error', RISK_CONTROL_1034_MESSAGE)
                detail = e.message if e.message else '无服务端文案'
                return _envelope('error', f'获取角色列表失败(retcode={e.code}): {detail}')
            except ValueError as e:
                # 请求目标非法（白名单外主机等），在发请求前被拒
                return _envelope('error', f'获取角色列表失败: {e}')
            return _envelope('success', f'共获取 {len(characters)} 名角色',
                             [character_to_dict(c) for c in characters])

    def get_roster_detail(self) -> dict:
        """角色名册明细入口（``mys_get_roster_detail`` 业务语义；design.md §2
        契约 5：信封逐态与 ``get_characters`` 完全一致，仅成功载荷换明细）：
        awaiting 期不裸打请求；``MysSessionExpired`` → 打过期标记（不清任何
        文件）+ ``session_expired``；1034 → 专属文案；其余业务错误 →
        ``error`` 透传 retcode；成功载荷经 ``character_to_dict`` 序列化
        ``CharacterDetail`` 冻结字段集（不含任何凭据字段）。"""
        with self._lock:
            if self._last_error is not None:
                error = self._last_error
                self._last_error = None
                return _envelope('error', error)
            if self._state == STATE_AWAITING_TICKET:
                return _envelope(
                    'verification_required', VERIFICATION_REQUIRED_MESSAGE, {'url': self._verify_url}
                )
            try:
                details = self._sr_client.get_characters_detail()
            except MysSessionExpired:
                # 过期处置（design.md §2.4/§2.6）：只打标记不清任何文件
                self._store.mark_expired()
                return _envelope('session_expired', SESSION_EXPIRED_MESSAGE)
            except MysApiError as e:
                if e.code == 1034:
                    return _envelope('error', RISK_CONTROL_1034_MESSAGE)
                detail = e.message if e.message else '无服务端文案'
                return _envelope('error', f'获取角色明细失败(retcode={e.code}): {detail}')
            except ValueError as e:
                # 请求目标非法（白名单外主机等），在发请求前被拒
                return _envelope('error', f'获取角色明细失败: {e}')
            return _envelope('success', f'共获取 {len(details)} 名角色明细',
                             [character_to_dict(d) for d in details])

    # ---- 状态机内部（调用方须持控制器锁）----

    def _is_logged_in(self) -> bool:
        """已登录判定（design.md §2.4 定死）：cookies 非空且未标记过期。"""
        return bool(self._store.load_cookies()) and not self._store.is_expired()

    def _enter_verification(self, challenge: AigisChallenge) -> None:
        """进入验证轮：新建 verifier（本轮首个挑战；后续换题复用同实例——
        同端口语义）挂载挑战、注册回传回调，状态置 awaiting_ticket。"""
        self._verifier = self._verifier_factory()
        self._verifier.on_ticket = self._on_ticket
        self._current_challenge = challenge
        self._attempt = 1
        self._state = STATE_AWAITING_TICKET
        self._verify_url = self._verifier.start(challenge)

    def _on_ticket(self, payload: dict) -> None:
        """验证页回传处理（verifier 服务线程内调用，持控制器锁串行化）。

        迟到票据双重防护：① 状态闸——非 awaiting_ticket（含已登出/已取消/
        已超限复位）一律丢弃；② 配对闸——payload.session_id 与控制器当前
        challenge 再比对一道（verifier 层 409 之外的第二道闸，T-3 评审强制
        判据）。取消回传 → 状态复位 + verifier 关闭；票据 → 单轮收口
        （complete_verification）后按结果推进或放弃。
        """
        with self._lock:
            if self._state != STATE_AWAITING_TICKET:
                return
            challenge = self._current_challenge
            if challenge is None or payload.get('session_id') != challenge.session_id:
                return
            if payload.get('cancelled') is True:
                self._reset_verification()
                return
            ticket = payload.get('ticket')
            if not isinstance(ticket, dict):
                return  # 契约外回传（verifier 层已 400 拦截，此处兜底丢弃）
            try:
                result = self._client.complete_verification(challenge, ticket)
            except MysApiError as e:
                detail = e.message if e.message else '无服务端文案'
                self._reset_verification()
                self._last_error = f'人机验证失败(retcode={e.code}): {detail}'
                return
            if result.status == 'ok':
                # 会话已由 client 整体覆盖落盘（save_session_full），本轮收尾
                self._reset_verification()
                return
            new_challenge = result.challenge
            if new_challenge is not None and self._attempt < MAX_VERIFY_ATTEMPTS:
                # 未达上限：同端口换题继续（verifier.start 更新 pending 并
                # 自动开浏览器），用户再解一次
                self._attempt += 1
                self._current_challenge = new_challenge
                self._verify_url = self._verifier.start(new_challenge)
                return
            self._reset_verification()
            self._last_error = (
                f'人机验证连续 {MAX_VERIFY_ATTEMPTS} 次未通过，已停止；可重新发起 mys_login 重试'
            )

    def _reset_verification(self) -> None:
        """验证轮收尾（调用方须持锁）：状态回 idle、关闭 verifier、清轮内
        状态。取消/验证成功/超限/异常四条路径共用。"""
        self._state = STATE_IDLE
        verifier = self._verifier
        self._verifier = None
        self._verify_url = None
        self._current_challenge = None
        self._attempt = 0
        if verifier is not None:
            verifier.close()


# ---- 模块级单例装配（运行入口；测试不经过此路径）----

_controller: MysAccessController | None = None
_controller_build_lock = threading.Lock()


def _open_verify_page(url: str) -> None:
    """打开系统浏览器（webbrowser.open 返回 bool，包装为 None 语义）。"""
    webbrowser.open(url)


def _default_verifier_factory() -> AigisVerifier:
    """真实验证页工厂：open_browser 接 webbrowser.open（运行入口注入真实现，
    设计出处 design.md §2.2 aigis_verifier）。"""
    return AigisVerifier(open_browser=_open_verify_page)


def resolve_instance_mys_dir(instance_idx: int) -> Path:
    """实例 mys 会话目录：``config/<实例两位序号>/mys``（与 YamlConfig 实例
    配置同一套目录约定：``f'{idx:02d}'`` 等价于该模块的 ``'%02d' % idx`` 拼法，
    见 one_dragon.base.config.yaml_config）。"""
    return Path(os_utils.get_path_under_work_dir('config', f'{instance_idx:02d}', 'mys'))


def _get_controller(backend: SrBackendContext) -> MysAccessController:
    """取模块级单例（进程级生命周期），首次工具调用时装配。

    - 实例目录按首次调用时刻的当前实例解析（``backend.ctx.current_instance_idx``
      ——SrContext 现有 API，实例目录 = 当前实例的 config 目录）；
    - requests 真实实装（``RequestsHttpSend``）与 webbrowser 打开回调在此传入
      （运行入口职责，design.md §2.4）；
    - 注册期（create_mcp_server）不构建：既不让注册路径触碰文件系统，也让
      backend 为测试替身时零副作用。

    进程内实例切换不重建单例（会话目录锚定首次调用时的实例）——当前 MCP
    server 的实例切换随 server 重启生效（backend._refresh_runtime_config 的
    切实例路径以运行场景为主），如后续要求热切实例需在此重建，属迭代外。
    """
    global _controller
    with _controller_build_lock:
        if _controller is None:
            _controller = MysAccessController(
                session_dir=resolve_instance_mys_dir(backend.ctx.current_instance_idx),
                http_send=RequestsHttpSend(),
                verifier_factory=_default_verifier_factory,
            )
        return _controller


def register_mys_tools(mcp: FastMCP, backend: SrBackendContext) -> None:
    """注册米游社账号四工具（由 ``create_mcp_server`` 调用，与既有
    register_prompts 模式一致）。工具函数只做信封透传：全部业务语义
    （状态机/验证循环/过期处置/脱敏）在 ``MysAccessController``，行为测试
    以控制器为对象。"""

    @mcp.tool(annotations=ToolAnnotations(title="登录米游社"))
    def mys_login(
        username: Annotated[str, Field(description="米游社账号（手机号或邮箱）")],
        password: Annotated[str, Field(description="米游社账号密码；仅在本调用内存中使用，不落盘、不写日志")],
    ) -> dict:
        """登录米游社账号（国服）。⚠️ 知情说明：需要在参数中提供账号与密码——密码会作为工具参数传入大模型上下文，存在泄露风险，是否继续由使用者自行决定。成功后仅落盘 cookie 会话（config/当前实例/mys/session.json），密码不落盘。

        验证等待期间重复调用本工具：不会重复登录，返回现存验证页地址。

        Returns:
            统一信封 ``{"status","message","data"}``：
            - ``success``：登录成功（返回值不含任何 cookie/token）；
            - ``already_logged_in``：已存在有效登录会话（未标记过期），
              无需重复登录；
            - ``verification_required``：触发人机验证，``data.url`` 为本机
              验证页地址，在浏览器完成解题后自动继续，重复验证最多 3 次，
              完成后用 mys_get_characters 验证登录结果；
            - ``error``：登录失败（密码错误过多/账号风控/其它），本机落盘
              数据不受影响。
        """
        return _get_controller(backend).login(username, password)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True, title="登出米游社"))
    def mys_logout() -> dict:
        """登出米游社账号：清除本机保存的登录会话与角色定位缓存。

        幂等（无会话也返回 success）。验证等待期间登出 = 取消验证：状态复位、
        验证页关闭，此后的迟到验证结果不会静默重建会话。设备锚
        （device.json）保留，不随登出轮换。

        Returns:
            统一信封 ``{"status","message","data"}``：``success``。
        """
        return _get_controller(backend).logout()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="获取角色列表"))
    def mys_get_characters() -> dict:
        """获取崩坏:星穹铁道角色列表（等级/稀有度/星魂数/命途/光锥摘要）；会话过期时返回 session_expired 并提示重新登录，不清除任何本机数据。

        Returns:
            统一信封 ``{"status","message","data"}``：
            - ``success``：``data`` 为角色数组，每项含
              id/name/level/rarity/rank（星魂数）/element（属性）/
              base_type（命途 id）/equip（光锥摘要 name/level/rank/rarity，
              未装备为 null）；
            - ``verification_required``：登录验证等待中，``data.url`` 为本机
              验证页地址（本次调用未发起数据请求）；
            - ``session_expired``：会话已过期，仅打标记提醒重新登录（mys_login），
              本机数据不受影响；
            - ``error``：接口业务失败；数据接口触发风控验证（1034）时返回
              专属提示（本版本未实现该验证链）。
        """
        return _get_controller(backend).get_characters()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="获取角色名册明细"))
    def mys_get_roster_detail() -> dict:
        """获取崩坏:星穹铁道全角色名册明细（每名角色的遗器六件套词条明细/位面饰品/星魂/行迹/属性面板，词条与面板属性均为中文名）。数据量较大（64 角色全量）。会话过期时返回 session_expired 并提示重新登录，不清除任何本机数据。

        Returns:
            统一信封 ``{"status","message","data"}``：
            - ``success``：``data`` 为角色明细数组，每项为轻口径十字段
              （id/name/level/rarity/rank/element/element_cn/base_type/
              base_type_cn/equip）加五组明细：relics（遗器六件套，每件含
              主/副词条 name_cn/value/times）、ornaments（位面饰品，与
              遗器同构）、ranks（星魂全量含解锁状态）、skills（行迹类型
              与分段文案）、properties（属性面板 base/add/final 字符串值）；
            - ``verification_required``：登录验证等待中，``data.url`` 为本机
              验证页地址（本次调用未发起数据请求）；
            - ``session_expired``：会话已过期，仅打标记提醒重新登录（mys_login），
              本机数据不受影响；
            - ``error``：接口业务失败；数据接口触发风控验证（1034）时返回
              专属提示（本版本未实现该验证链）。
        """
        return _get_controller(backend).get_roster_detail()
