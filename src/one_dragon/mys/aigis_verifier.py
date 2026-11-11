"""本地 aigis 验证页服务（跨游戏通用）。

设计出处：docs/develop/one_dragon/mys/README.md（模块表 aigis_verifier 行）；
组件调用参数与双载口径：login-verification-research.md §3.2；取消闭环与
自动弹出手法：同文档 §10.5-3（Moonward）。

- 挑战不下沉 URL：服务端持有「当前 pending 挑战」，页面
  加载/刷新时 GET /challenge 取最新挑战——刷新即换新题，不存在旧 URL 解旧题。
- 页面模板是纯静态模块常量：挑战数据完全经 GET /challenge 的 JSON 流转，
  模板零插值——research §10.5-3 的「参数 base64 后嵌入 HTML 防转义」手法在
  本形态下退化为「无参数可嵌」，HTML 注入面天然不存在（base64 防转义注意点
  的落点即此设计）。
- POST /ticket 防线照参考实现 server.mjs:16 手法：``sec-fetch-site`` 为
  cross-site、或 Origin 非本服务 → 403；``session_id`` 与 pending 不一致 →
  409 丢弃（防旧页面解旧题的迟到票据污染新一轮挑战）。
- open_browser 默认 None = 不自动打开浏览器（AGENTS.md §7 纪律：外部 IO 回调
  默认不做事，真实现由运行入口传入，MCP 装配层传 ``webbrowser.open``；测试
  不注入则零副作用）。on_ticket 与 wait_ticket 是同一回传的两条消费通路：
  回调供 MCP 控制器异步场景，阻塞等待供 GUI/CLI 场景；wait_ticket 超时只
  结束等待调用本身，不改状态不关服务（页面仍有效可继续解题）。
"""

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from one_dragon.mys.mys_client import AigisChallenge
from one_dragon.utils.log_utils import log

#: 验证页 CSP 白名单（照抄参考实现 verify.html policy：geetest/mihoyo/webstatic 域）
_VERIFIER_CSP: str = (
    "default-src 'self'; "
    "script-src 'self' https://*.geetest.com https://*.geevisit.com "
    "https://webstatic.mihoyo.com https://*.miyoushe.com; "
    "style-src 'self' 'unsafe-inline' https://*.geetest.com https://*.geevisit.com; "
    "font-src 'self' data: https://*.geetest.com https://*.geevisit.com; "
    "img-src 'self' data: https://*.geetest.com https://*.geevisit.com; "
    "media-src https://*.geetest.com https://*.geevisit.com; "
    "connect-src 'self' https://*.geetest.com https://*.geevisit.com "
    "https://*.mihoyo.com https://*.miyoushe.com; "
    "frame-src https://*.geetest.com https://*.geevisit.com https://*.mihoyo.com; "
    "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)

#: 票据/取消回传体积上限（照参考实现 server.mjs 口径；极验票据为数百字节级 JSON）
_MAX_TICKET_BODY_BYTES: int = 8192

# 验证页模板（纯静态：双组件脚本同载 + no-referrer meta + 挑战经 /challenge 取）。
# 组件脚本出处（research §3.1/§3.2/§10.3-7）：gt4 = 官方登录页在用的
# webstatic.mihoyo.com 副本；gt3 = static.geetest.com gt.0.5.0.js（参考实现与
# genshin.py 同款）。双载防服务端下发 gt3 形态时组件缺失（research §8.1.3）。
_VERIFIER_HTML: str = '''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="referrer" content="no-referrer">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>米游社人机验证</title>
<style>
  body { font-family: sans-serif; background: #f5f6f8; display: flex; justify-content: center; padding-top: 48px; }
  main { background: #fff; border-radius: 8px; padding: 24px 32px; max-width: 420px; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
  h1 { font-size: 18px; margin-top: 0; }
  #status { color: #555; }
  #error { color: #c0392b; white-space: pre-wrap; }
</style>
</head>
<body>
<main>
<h1>完成米游社人机验证</h1>
<p id="status">正在获取验证挑战…</p>
<p id="error"></p>
<div id="captchaContainer"></div>
</main>
<script src="https://webstatic.mihoyo.com/dora/lib/geetest/v4/gt4.js"></script>
<script src="https://static.geetest.com/static/js/gt.0.5.0.js"></script>
<script>
(async () => {
  const statusEl = document.querySelector('#status');
  const errorEl = document.querySelector('#error');
  const container = document.querySelector('#captchaContainer');
  const showStatus = (text) => { statusEl.textContent = text; };
  const showError = (text) => { errorEl.textContent = text; };
  // 回传契约：{session_id, ticket} 或 {session_id, cancelled: true}
  const postTicket = async (payload) => {
    const response = await fetch('/ticket', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (response.status === 409) {
      showError('本页题目已过期（服务端已换新挑战），请刷新本页获取新题。');
      return false;
    }
    if (!response.ok) {
      showError('回传验证结果失败（HTTP ' + response.status + '），请刷新本页重试。');
      return false;
    }
    return true;
  };
  const cancel = async (sessionId, reason) => {
    showError('验证未完成：' + reason + '。请回到应用重新发起登录。');
    try { await postTicket({ session_id: sessionId, cancelled: true }); } catch (e) { /* 回传失败时保留页面供重试 */ }
  };
  try {
    const response = await fetch('/challenge', { cache: 'no-store' });
    if (!response.ok) {
      showStatus('获取挑战失败（HTTP ' + response.status + '），请确认应用仍在运行后刷新本页。');
      return;
    }
    const payload = await response.json();
    const data = payload.data || {};
    const sessionId = payload.session_id;
    if (data.use_v4) {
      if (typeof window.initGeetest4 !== 'function') { cancel(sessionId, '极验 v4 组件（gt4.js）加载失败'); return; }
      showStatus('正在初始化极验 v4 验证…');
      // 参数口径 research §3.2：riskType 缺省 icon、product=popup、userInfo 带 session_id；
      // onReady 即 verify() 自动弹出（research §10.5-3 Moonward 手法）
      window.initGeetest4({
        captchaId: data.gt,
        riskType: data.risk_type || 'icon',
        language: 'zho',
        product: 'popup',
        hideSuccess: true,
        userInfo: JSON.stringify({ session_id: sessionId }),
        timeout: 10000,
        https: true,
        protocol: 'https',
      }, (captchaObj) => {
        captchaObj.onReady(() => captchaObj.verify());
        captchaObj.onSuccess(async () => {
          if (await postTicket({ session_id: sessionId, ticket: captchaObj.getValidate() })) {
            showStatus('验证完成，请返回应用继续操作。');
          }
        });
        captchaObj.onClose(() => cancel(sessionId, '验证弹窗被关闭'));
        captchaObj.onError(() => cancel(sessionId, '验证组件出错'));
      });
    } else if (data.challenge) {
      if (typeof window.initGeetest !== 'function') { cancel(sessionId, '极验 gt3 组件（gt.0.5.0.js）加载失败'); return; }
      showStatus('正在初始化极验验证…');
      // 参数口径 research §3.2（gt3 兜底）：api_server 必传，no-referrer meta 已在 head
      window.initGeetest({
        gt: data.gt,
        challenge: data.challenge,
        new_captcha: data.new_captcha,
        offline: !data.success,
        product: 'popup',
        api_server: 'api.geetest.com',
        https: true,
        lang: 'zh-cn',
      }, (captchaObj) => {
        captchaObj.appendTo(container);
        captchaObj.onReady(() => captchaObj.verify());
        captchaObj.onSuccess(async () => {
          if (await postTicket({ session_id: sessionId, ticket: captchaObj.getValidate() })) {
            showStatus('验证完成，请返回应用继续操作。');
          }
        });
        captchaObj.onClose(() => cancel(sessionId, '验证弹窗被关闭'));
        captchaObj.onError(() => cancel(sessionId, '验证组件出错'));
      });
    } else {
      // 两键双缺：无法渲染任何极验组件，按取消语义回传（控制器收到即复位，
      // research §10.4-2：并联判据仍可能双缺，不猜组件硬走）
      showError('服务端下发的挑战数据不含极验参数（既无 use_v4 也无 challenge），无法渲染验证组件。');
      try { await postTicket({ session_id: sessionId, cancelled: true }); } catch (e) { /* 同上 */ }
    }
  } catch (e) {
    showStatus('无法连接本机验证服务，请确认应用仍在运行后刷新本页。');
  }
})();
</script>
</body>
</html>
'''


class _AigisRequestHandler(BaseHTTPRequestHandler):
    """验证页服务 handler：GET /verify（页面）/ GET /challenge（pending 挑战）/
    POST /ticket（票据或取消回传）。宿主 verifier 由 _VerifierHttpServer 装配。"""

    def log_message(self, format: str, *args: object) -> None:
        """静默访问日志（单用户本地回环服务，成败由页面自行呈现）。"""

    def _verifier(self) -> 'AigisVerifier':
        """宿主 verifier（装配时挂到 server 对象上）。"""
        return self.server.verifier  # type: ignore[attr-defined] # _VerifierHttpServer 提供

    def _send_bytes(self, status: int, content_type: str, body: bytes, csp: str | None = None) -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if csp is not None:
            self.send_header('Content-Security-Policy', csp)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self._send_bytes(status, 'application/json; charset=utf-8', body)

    def _path(self) -> str:
        """请求路径（剥掉 query 串）。"""
        return urlsplit(self.path).path

    def _cross_origin_rejected(self) -> bool:
        # 照参考实现 server.mjs:16 手法：sec-fetch-site 为 cross-site、或 Origin
        # 存在且与本服务（http://<Host>）不一致即拒——浏览器同源 POST（Origin =
        # 本服务）与无这些头的非浏览器客户端不受影响
        expected = f'http://{self.headers.get("Host", "")}'
        site = self.headers.get('Sec-Fetch-Site')
        origin = self.headers.get('Origin')
        return site == 'cross-site' or (origin is not None and origin != expected)

    def do_GET(self) -> None:
        verifier = self._verifier()
        path = self._path()
        if path == '/verify':
            self._send_bytes(200, 'text/html; charset=utf-8', _VERIFIER_HTML.encode('utf-8'), csp=_VERIFIER_CSP)
        elif path == '/challenge':
            # 服务端持有 pending：页面每次加载/刷新取当前挑战（刷新即换新题）
            challenge = verifier.current_challenge()
            if challenge is None:
                self._send_json(409, {'error': 'NO_PENDING_CHALLENGE'})
            else:
                self._send_json(200, {
                    'session_id': challenge.session_id,
                    'mmt_type': challenge.mmt_type,
                    'data': challenge.data,
                })
        else:
            self._send_json(404, {'error': 'NOT_FOUND'})

    def do_POST(self) -> None:
        verifier = self._verifier()
        if self._path() != '/ticket':
            self._send_json(404, {'error': 'NOT_FOUND'})
            return
        if self._cross_origin_rejected():
            self._send_json(403, {'error': 'ORIGIN_DENIED'})
            return
        try:
            length = int(self.headers.get('Content-Length') or '0')
        except ValueError:
            length = 0
        if length > _MAX_TICKET_BODY_BYTES:
            self._send_json(413, {'error': 'BODY_TOO_LARGE'})
            return
        raw = self.rfile.read(length) if length > 0 else b''
        try:
            payload = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            payload = None
        if not isinstance(payload, dict):
            self._send_json(400, {'error': 'INVALID_JSON'})
            return
        status, response = verifier.accept_ticket_payload(payload)
        self._send_json(status, response)


class AigisVerifier:
    """aigis 验证页宿主：pending 挑战服务端持有 + 票据/取消回传接收。

    生命周期：start 挂载挑战（服务未起则以 port=0 绑
    随机空闲端口，已起则复用同端口）→ 页面解题回传 → close 释放端口（幂等；
    关闭后实例不可再用，重开验证由上层新建实例）。
    """

    def __init__(self, open_browser: Callable[[str], None] | None = None) -> None:
        """open_browser 为可注入的打开浏览器回调（默认 None = 只返回 URL 不打开）。

        Args:
            open_browser: 以验证页 URL 调用；MCP 装配层传 ``webbrowser.open``，
                测试注入记录器或不注入（零副作用）。
        """
        self._open_browser: Callable[[str], None] | None = open_browser
        #: 票据/取消回传回调（MCP 场景由控制器设置；在服务线程内被调用，
        #: 回调内部不得再阻塞等待本实例）
        self.on_ticket: Callable[[dict], None] | None = None
        self._lock: threading.Lock = threading.Lock()
        self._pending: AigisChallenge | None = None
        self._last_payload: dict | None = None
        self._payload_event: threading.Event = threading.Event()
        self._server: _VerifierHttpServer | None = None
        self._serve_thread: threading.Thread | None = None
        self._closed: bool = False

    def start(self, challenge: AigisChallenge) -> str:
        """挂载 pending 挑战并返回验证页 URL。

        URL 仅 ``http://127.0.0.1:<port>/verify``，不含任何挑战参数——挑战由
        页面经 GET /challenge 实时取，二次 start 换新挑战后旧页面刷新即取新题
        （服务端持有模式的核心语义）。open_browser 非空时以 URL 调用。
        """
        if self._closed:
            raise RuntimeError('AigisVerifier 已关闭，重开验证请新建实例')
        with self._lock:
            self._pending = challenge
            self._last_payload = None
        # 新挑战 = 新一轮验证：清空上一轮回传，等待方只拿得到本轮的票据/取消
        self._payload_event.clear()
        if self._server is None:
            server = _VerifierHttpServer(self)
            thread = threading.Thread(
                target=server.serve_forever, daemon=True, name='aigis-verifier'
            )
            thread.start()
            self._server = server
            self._serve_thread = thread
        port = int(self._server.server_address[1])
        url = f'http://127.0.0.1:{port}/verify'
        if self._open_browser is not None:
            self._open_browser(url)
        return url

    def current_challenge(self) -> AigisChallenge | None:
        """当前 pending 挑战（GET /challenge 数据源；无 pending 返回 None）。"""
        with self._lock:
            return self._pending

    def accept_ticket_payload(self, payload: dict) -> tuple[int, dict]:
        """POST /ticket 的裁决入口（handler 调用）：配对校验 + 合格回传的记录
        与回调分派。返回（HTTP 状态码, 应答 JSON）。

        - 无 pending 或 session_id 与 pending 不一致 → 409 丢弃（防旧页面解
          旧题的迟到票据污染新一轮挑战）；
        - cancelled 真值 → 按取消语义记录；ticket 为对象 → 按票据记录；两者
          皆无 → 400（契约外回传不进等待方）。
        """
        with self._lock:
            pending = self._pending
        if pending is None:
            return 409, {'error': 'NO_PENDING_CHALLENGE'}
        if payload.get('session_id') != pending.session_id:
            return 409, {'error': 'SESSION_MISMATCH'}
        delivered: dict = {'session_id': pending.session_id}
        if payload.get('cancelled') is True:
            delivered['cancelled'] = True
        elif isinstance(payload.get('ticket'), dict):
            delivered['ticket'] = dict(payload['ticket'])
        else:
            return 400, {'error': 'PAYLOAD_REQUIRES_TICKET_OR_CANCELLED'}
        with self._lock:
            self._last_payload = delivered
        self._payload_event.set()
        callback = self.on_ticket
        if callback is not None:
            try:
                callback(dict(delivered))
            except Exception as e:  # 回调异常不拖垮服务线程（回传已记录，等待方可达）
                log.warning(f'aigis 验证回传回调异常: {type(e).__name__}: {e}')
        return 200, {'ok': True}

    def wait_ticket(self, timeout_sec: float = 300) -> dict | None:
        """阻塞等待一次回传（GUI/CLI 场景）：票据或取消 payload；超时返回 None。

        超时只结束等待调用本身——不改状态、不关服务、不清 pending（页面仍有效
        可继续解题后再次回传）；start 挂载新挑战时清空上一轮回传。
        """
        signaled = self._payload_event.wait(timeout_sec)
        if not signaled:
            return None
        with self._lock:
            return self._last_payload

    def close(self) -> None:
        """释放端口（幂等）。关闭后 start 不可再用；已在等待中的 wait_ticket
        不被唤醒（上层应先结束等待再关闭）。"""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            server = self._server
            thread = self._serve_thread
            self._server = None
            self._serve_thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=5)


class _VerifierHttpServer(ThreadingHTTPServer):
    """绑定宿主 verifier 的回环 HTTP 服务（port=0 随机空闲端口）。"""

    def __init__(self, verifier: AigisVerifier) -> None:
        super().__init__(('127.0.0.1', 0), _AigisRequestHandler)
        self.verifier: AigisVerifier = verifier
