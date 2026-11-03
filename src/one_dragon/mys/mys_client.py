"""米游社通用客户端：密码登录（单轮分诊）、通用 GET 请求、本地登出。

口径出处（docs/develop/sr_od/application/account_profile/）：
- 登录头十件套 / RSA 加密 / 登录 DS / cookie 全量收取 / 成功判据：
  miyoushe-api-flow.md §2；
- 验证触发分诊（双条件、message 不参与）与 x-rpc-aigis 双层解析：
  login-verification-research.md §2.1-§2.3；
- 模块职责与跨层契约：changes/mys-account-mcp/design.md §2.2 mys_client
  小节、§2.5 契约 1/3。

职责分界（design.md §2.1 定死）：login 是单轮语义——一次请求 + 分诊，验证
触发时只解析并返回挑战（AigisChallenge），验证循环与票据重发由上层控制器
持有，本模块不做任何重试。凭据红线（design.md §2.6）：密码仅在 login 调用
栈内存（RSA 加密后进请求体）；cookie 只入内存罐与 session.json；两者不进
任何日志与异常文本——本模块异常只携带 retcode 与服务端 message 文案。
"""

import json
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

from one_dragon.mys.mys_const import (
    CONTENT_TYPE_JSON,
    GAME_RECORD_BASE_URL,
    HOST_WHITELIST,
    LOGIN_URL,
    LOGIN_X_RPC_APP_ID,
    LOGIN_X_RPC_CLIENT_TYPE,
    LOGIN_X_RPC_GAME_BIZ,
    LOGIN_X_RPC_SDK_VERSION,
    LOGIN_X_RPC_SOURCE,
    RECORD_REFERER,
    RECORD_X_RPC_APP_VERSION,
    RECORD_X_RPC_CLIENT_TYPE,
    USER_AGENT_DESKTOP_CHROME,
)
from one_dragon.mys.mys_device import DeviceIdentity
from one_dragon.mys.mys_http import HttpSend, HttpSendResult, header_get
from one_dragon.mys.mys_session import (
    SESSION_EXPIRED_RETCODES,
    MysApiError,
    MysSessionExpired,
    SessionStore,
)
from one_dragon.mys.mys_signing import (
    _build_query_string,
    ds_login,
    ds_record,
    rsa_encrypt,
)

#: 登录触发人机验证的 retcode（官方枚举 NeedAigis，login-verification-research.md §2.3）
LOGIN_NEED_VERIFICATION_RETCODE: int = -3101


@dataclass
class AigisChallenge:
    """登录人机验证挑战（响应头 x-rpc-aigis 的结构化产物，验证循环的全部输入）。

    Attributes:
        session_id: 服务端签发的验证会话 ID（重发回传头按其配对）。
        mmt_type: 外层可选字段（0=无需验证 1=需要）；缺失为 None。
        data: 极验挑战参数，已二次解析为 dict（外层 data 兼容字符串/对象双形态）。
        raw_header: 原始响应头值（排查留档）。
    """

    session_id: str
    mmt_type: int | None
    data: dict
    raw_header: str


@dataclass
class LoginResult:
    """单轮登录结果（design.md §2.5 契约 1）。

    Attributes:
        status: 'ok' = 会话已建立并落盘；'need_verification' = 触发人机验证。
        challenge: 验证挑战；need_verification 时必有，ok 时为 None。
    """

    status: Literal['ok', 'need_verification']
    challenge: AigisChallenge | None


def _parse_json_payload(result: HttpSendResult, stage: str) -> dict:
    """业务分诊前置：非 2xx 或响应体非 JSON 对象一律按 MysApiError 结构化上抛。

    传输层不判状态（mys_http 契约：response.ok 判定归调用方），本函数即调用方
    判定。code 用 HTTP 状态码承载（与参考实现 AccountAPIError(stage, status)
    同口径）；错误文本只含状态码，不携带响应报文与任何请求凭据。
    """
    if not 200 <= result.status < 300:
        raise MysApiError(result.status, f'{stage}: HTTP {result.status}')
    try:
        payload = json.loads(result.body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise MysApiError(result.status, f'{stage}: 响应体不是合法 JSON') from None
    if not isinstance(payload, dict):
        raise MysApiError(result.status, f'{stage}: 响应体不是 JSON 对象')
    return payload


def _require_retcode(payload: dict) -> int:
    """读取并校验 retcode 字段（排除 bool 是 int 子类的误判）；非法按协议错误上抛。"""
    retcode = payload.get('retcode')
    if isinstance(retcode, bool) or not isinstance(retcode, int):
        raise MysApiError(-1, '响应体缺少合法的 retcode 整数字段')
    return retcode


def _message_of(payload: dict) -> str:
    """服务端 message 文案（非字符串视为空；异常文本只允许携带它）。"""
    message = payload.get('message')
    return message if isinstance(message, str) else ''


def _extract_set_cookie_pairs(headers: list[tuple[str, str]]) -> dict[str, str]:
    """收取响应全部 Set-Cookie：每行取首个 ``;`` 前的 k=v 对（与参考实现
    account-client.mjs ``#readCookies`` 同口径；同名多条后者覆盖前者）。"""
    pairs: dict[str, str] = {}
    for header_name, header_value in headers:
        if header_name.lower() != 'set-cookie':
            continue
        pair = header_value.split(';', 1)[0]
        pos = pair.find('=')
        if pos > 0:
            pairs[pair[:pos]] = pair[pos + 1:]
    return pairs


def _parse_aigis_challenge(raw_header: str | None) -> AigisChallenge:
    """双层解析 x-rpc-aigis（login-verification-research.md §2.2 四源一致）：
    外层 JSON 取 session_id / mmt_type / data；data 兼容字符串与对象双形态，
    字符串再解析一次。解析不完整按验证触发的业务错误上抛——残缺挑战交给上层
    只会失败在更难排查的位置，不猜字段继续。"""
    if raw_header is None:
        raise MysApiError(
            LOGIN_NEED_VERIFICATION_RETCODE, '验证已触发但响应未携带 x-rpc-aigis 头'
        )
    try:
        outer = json.loads(raw_header)
    except ValueError:
        raise MysApiError(LOGIN_NEED_VERIFICATION_RETCODE, 'x-rpc-aigis 头不是合法 JSON') from None
    if not isinstance(outer, dict) or not isinstance(outer.get('session_id'), str):
        raise MysApiError(LOGIN_NEED_VERIFICATION_RETCODE, 'x-rpc-aigis 头缺少 session_id 字段')
    data = outer.get('data')
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            raise MysApiError(
                LOGIN_NEED_VERIFICATION_RETCODE, 'x-rpc-aigis 的 data 内层不是合法 JSON'
            ) from None
    mmt_type = outer.get('mmt_type')
    return AigisChallenge(
        session_id=outer['session_id'],
        mmt_type=mmt_type if isinstance(mmt_type, int) and not isinstance(mmt_type, bool) else None,
        data=data if isinstance(data, dict) else {},
        raw_header=raw_header,
    )


def _resolve_request_url(path_or_url: str) -> str:
    """双形态目标解析（design.md §2.2 request）：以 http 开头 = 绝对 URL，
    仅允许 https 且主机在白名单（mys_const.HOST_WHITELIST），违规 ValueError
    （白名单外主机不属于米游社 API 面，请求头/cookie 不外发）；否则视作
    game_record 基座相对路径（前导 '/' 容错剔除，基座本身以 '/' 结尾）。"""
    if not path_or_url.startswith('http'):
        return GAME_RECORD_BASE_URL + path_or_url.lstrip('/')
    parts = urlsplit(path_or_url)
    host = parts.hostname
    if parts.scheme != 'https' or host is None or host not in HOST_WHITELIST:
        raise ValueError(f'仅允许 https 且主机须在米游社白名单内，收到: {parts.scheme}://{host or ""}')
    return path_or_url


class MysClient:
    """米游社通用客户端：login / request / logout（均为单轮语义，无内部循环）。"""

    def __init__(self, store: SessionStore, device: DeviceIdentity, http_send: HttpSend) -> None:
        """三参全部必填无默认（design.md §2.2 / §2.5 契约 3）：requests 真实
        实装由运行入口（MCP 装配层）传入，测试注入剧本式假实现——缺任一参数
        构造即失败，测试不注入就零副作用。

        内存 cookie 罐构造时从落盘会话恢复：跨进程续用已落盘会话（MCP server
        重启后不重登即可继续请求，design.md §2.4 重启语义的前提）。
        """
        self._store: SessionStore = store
        self._device: DeviceIdentity = device
        self._http_send: HttpSend = http_send
        self._jar: dict[str, str] = dict(store.load_cookies())

    # ---- 登录（单轮）----

    def login(self, username: str, password: str) -> LoginResult:
        """密码登录单轮：POST loginByPassword → 分诊。

        成功（retcode==0 且 Set-Cookie 非空）：cookie 全量入罐 + 会话整体覆盖
        落盘（任何 expired 标记随覆盖消失）+ 清除 role.json（登录态换绑后强制
        重新发现角色定位）。验证触发（双条件：retcode==-3101 或 aigis 响应头
        非空；message 文案一律不参与分诊，login-verification-research.md
        §10.4-6）：解析挑战返回 need_verification，待上层走验证循环。其余
        retcode（-3208/-3235 即停码、首轮不可能出现的 -3102/-3202、其余未知码）
        一律 MysApiError 上抛且不落盘不清文件。
        """
        headers: dict[str, str] = {
            'Content-Type': CONTENT_TYPE_JSON,
            'x-rpc-app_id': LOGIN_X_RPC_APP_ID,
            'x-rpc-client_type': LOGIN_X_RPC_CLIENT_TYPE,
            'x-rpc-source': LOGIN_X_RPC_SOURCE,
            'x-rpc-game_biz': LOGIN_X_RPC_GAME_BIZ,
            'x-rpc-sdk_version': LOGIN_X_RPC_SDK_VERSION,
            'ds': ds_login(),
        }
        headers.update(self._device.get_headers())
        body = json.dumps(
            {
                'account': rsa_encrypt(username),
                'password': rsa_encrypt(password),
            },
            ensure_ascii=False,
            separators=(',', ':'),
        ).encode('utf-8')
        result = self._http_send(LOGIN_URL, 'POST', headers, body)
        payload = _parse_json_payload(result, 'login')
        aigis_header = header_get(result.headers, 'x-rpc-aigis')
        if payload.get('retcode') == LOGIN_NEED_VERIFICATION_RETCODE or aigis_header is not None:
            return LoginResult(
                status='need_verification', challenge=_parse_aigis_challenge(aigis_header)
            )
        retcode = _require_retcode(payload)
        if retcode == 0:
            cookies = _extract_set_cookie_pairs(result.headers)
            if not cookies:
                # 成功判据 = retcode==0 且 Set-Cookie 非空（flow.md §2.5）；
                # 不满足即非成功，保守上抛不落盘（不写空会话文件）
                raise MysApiError(0, '登录响应未下发任何 Set-Cookie，会话不可用')
            self._jar.update(cookies)
            # 清除角色定位缓存（换绑后强制重新发现，design.md §2.2 login）：
            # SessionStore 的删除原语只有 clear（session+role 双删），复用后再
            # 紧跟整体覆盖重建 session.json——净效果 = role 删除 + 新会话落盘；
            # 两步之间崩溃的窗口内无会话文件，下次直接重登，无脏态残留
            self._store.clear()
            self._store.save_session_full(dict(self._jar))
            return LoginResult(status='ok', challenge=None)
        raise MysApiError(retcode, _message_of(payload))

    # ---- 通用业务请求 ----

    def request(self, path_or_url: str, query: dict) -> dict:
        """通用 mys GET（单请求，无重试）：game_record 基座相对路径或白名单
        绝对 URL；头 = game_record 头 + 设备头 + Cookie 罐全量，DS2 按查询
        参数签名。响应 Set-Cookie 先滚动入罐并续存（保留 expired 标记——服务端
        滚动下发不因业务失败而中断）；retcode 命中 ``SESSION_EXPIRED_RETCODES``
        抛 MysSessionExpired；1034 落入通用非 0 分支按裸 MysApiError 抛出
        （1034 验证链本迭代不实现，design.md §1 明确不解决项 7）；成功返回
        data 字段（非 dict 视为空）。"""
        url = _resolve_request_url(path_or_url)
        if query:
            # URL query 串与 DS2 的 q 必须同源同编码（服务端按解析后的参数重算
            # DS 校验，参考实现两侧同用 URLSearchParams 口径）——复用签名模块
            # 的同一纯函数保证两侧逐字节一致，避免第二份编码实现漂移
            url = f'{url}?{_build_query_string(query)}'
        headers: dict[str, str] = {
            'Content-Type': CONTENT_TYPE_JSON,
            'User-Agent': USER_AGENT_DESKTOP_CHROME,
            'x-rpc-app_version': RECORD_X_RPC_APP_VERSION,
            'x-rpc-client_type': RECORD_X_RPC_CLIENT_TYPE,
            'Referer': RECORD_REFERER,
            'ds': ds_record(query),
        }
        headers.update(self._device.get_headers())
        if self._jar:
            headers['Cookie'] = '; '.join(f'{name}={value}' for name, value in self._jar.items())
        result = self._http_send(url, 'GET', headers, None)
        payload = _parse_json_payload(result, 'request')
        rolling = _extract_set_cookie_pairs(result.headers)
        if rolling:
            self._jar.update(rolling)
            self._store.save_cookies(dict(self._jar))
        retcode = _require_retcode(payload)
        if retcode in SESSION_EXPIRED_RETCODES:
            raise MysSessionExpired(retcode, _message_of(payload))
        if retcode != 0:
            raise MysApiError(retcode, _message_of(payload))
        data = payload.get('data')
        return data if isinstance(data, dict) else {}

    # ---- 登出 ----

    def logout(self) -> None:
        """仅本地清除（design.md §2.2）：删 session.json 与 role.json（保留
        device.json 设备锚）并清空内存罐。不调用任何官方登出端点——flow.md
        全文无登出端点记载，不引入未验证请求。幂等。"""
        self._store.clear()
        self._jar.clear()
