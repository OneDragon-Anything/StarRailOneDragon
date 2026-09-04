"""CW 运维「停局-杀净-重启载码-武装哨兵-起局」一键化脚本。

背景:实机迭代期每轮重复固定序列(runtime-ops.md「局间交接序」):停局等结算 →
rewatch 杀净哨兵 → daemon 重启 MCP server(加载新代码)→ 重武哨兵 → 起下一局,
手工每轮 3-5 分钟且易跳步。本脚本把它串成一条命令。

形态选择(读码结论,MCP 工具不必进 Python):
  主 server(:24001)在 ``/mcp`` 之外同进程暴露了普通 HTTP 端点(``sr_od.backend.http``
  的 FastMCP custom_route):``GET /game/status``、``POST /game/stop``、
  ``POST /game/run/standalone?app_id=&block=false`` —— 即 get_run_status /
  stop_run / run_standalone_app 三个动作可直接 urllib 完成,无需 MCP 协议;
  server 重启走 daemon(:24000/mcp)的 ``restart_sr_od_mcp_server`` tool,
  本脚本内置一个最小 streamable-http JSON-RPC 客户端(initialize →
  tools/call)调用它,**不复制 daemon 的启停逻辑**(单一源保持)。
  故五步全部可自动化,唯一例外是哨兵的「起」。

⚠️ 哨兵信道纪律(2026-08-25 用户纠正,rewatch.py 头注同源):哨兵三件的
「起」必须保证**退出码有接收方**。本脚本的用法是被编排者经**会话后台任务**
起它(Python 用 Popen 以继承句柄方式拉起哨兵子进程,自己阻塞看守)——
哨兵报警退出 → 本进程打印 [CYCLE-*] 并带码退出 → 编排者的后台 job 结算送达。
禁 DETACHED 自起本脚本:那等于把整条报警链再度挂空。

用法(项目根;哨兵脚本须存在于 .debug/temp/currency_war/,默认 sentinel+gap 两件):

  uv run python tools/cw/cycle_restart.py --to-ready    # 只做①②③,打印就绪信号与武装命令即退(编排者手动收尾用)
  uv run python tools/cw/cycle_restart.py --stop-only   # 只做①停局(≥ to-ready 更保守的分步开关,②③④⑤全不碰)

用法拆分背景(2026-08-27 编排者指示):实测期间脚本连发 stop_run→restart 已一次性
走完五步;编排者要求后续步骤(哨兵重武/起局)由其统一接管,避免 server 刚重启又
连环操作——故提供 --to-ready / --start-only 分步形态,编排者可在两步之间插入
自己的判读/清理动作,而不是让脚本一口气跑完。
  uv run python tools/cw/cycle_restart.py --no-supervise  # 武装+起局后不阻塞看守(后台无人值守场景,慎用:退出码无人接)
  uv run python tools/cw/cycle_restart.py --early       # 哨兵组含 early_stop(纪律:首条遥测落后再武装,须显式传)

前提(本脚本不做,由调用前状态保证):游戏窗口有效(check_game_window)、
残局已清理回货币战争-大厅(结算屏残留会让 app 启动死循环,runtime-ops 运行坑)。
停局是**信号式**(POST /game/stop,当前战斗打完才终),超时(--stop-timeout,默认
900s)未终则中止后续步骤(fail-safe:绝不带着活跃对局重启——daemon r99 守卫同判据)。

退出码:0 全流程完成(含哨兵全部以 0 退出);2 参数/前置失败;3 重启失败或停局超时;
非零透传首个退出的哨兵的退出码时附 [CYCLE-ALARM](哨兵报警/事件,需介入判读)。
"""
import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')   # type: ignore[attr-defined]  Windows GBK 控制台下保中文输出

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WATCH_DIR = os.path.join(REPO_ROOT, '.debug', 'temp', 'currency_war')
MAIN_SERVER = 'http://127.0.0.1:24001'
DAEMON_MCP = 'http://127.0.0.1:24000/mcp'

# 武装组合(与 rewatch.py WATCHERS 同口径;early 有显式纪律须 --early)
WATCHERS: dict[str, tuple[str, str]] = {
    'sentinel': ('cw_sentinel.py', '事件哨兵'),
    'gap': ('cw_runs_gap.py', 'runs 断流哨兵'),
    'early': ('cw_early_stop.py', '早停哨兵(首条遥测落后再武装)'),
}


def _log(msg: str) -> None:
    """统一时间戳输出并立即刷新(被后台任务消费时保序)。"""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _http(url: str, method: str = 'GET', timeout: float = 10.0) -> dict | str:
    """请求 JSON 端点,返回解析后的 dict;失败抛异常(调用方自行分类处理)。"""
    req = urllib.request.Request(url, method=method, data=b'' if method == 'POST' else None,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8', errors='replace'))


# ── 步骤①:查状态+停局 ──────────────────────────────────────────────

def stop_running(stop_timeout: float) -> bool:
    """有对局在跑则信号式停局并轮询至终态;返回 False = 超时仍 running(中止全流程)。"""
    try:
        st = _http(f'{MAIN_SERVER}/game/status')
    except Exception as e:   # noqa: BLE001  server 不可达 → 无局可停,交给重启救活
        _log(f'[1/5] 状态查询失败(server 可能已死,继续): {e!r}')
        return True
    if st.get('state') != 'running':
        _log(f'[1/5] 无对局在跑(state={st.get("state")}),无需停局')
        return True
    app = st.get('app', '?')
    _log(f'[1/5] 检测到对局在跑(app={app}, 已跑 {st.get("duration_seconds", 0):.0f}s)'
         f'——发信号式停局,等当前战斗结算…')
    try:
        _http(f'{MAIN_SERVER}/game/stop', method='POST')
        # 归因标记(编排者要求:可秒级归因停局事件来源)——编排者看到 stop_run 事件时,
        # grep 本行签名即可确认是本脚本所为,而非其他信道的手动停局。
        _log(f'[cycle_restart] [1/5] 已停止对局(app={app},信号式 /game/stop 已发)')
    except Exception as e:   # noqa: BLE001
        _log(f'[1/5] ⚠️ stop 请求失败(可能信号已发): {e!r}')
    deadline = time.time() + stop_timeout
    while time.time() < deadline:
        time.sleep(5)
        try:
            st = _http(f'{MAIN_SERVER}/game/status')
        except Exception as e:   # noqa: BLE001  停局过程中 server 死了也算终态
            _log(f'[1/5] 状态查询失败(视作已终): {e!r}')
            return True
        if st.get('state') != 'running':
            _log(f'[1/5] ✅ 对局已终(state={st.get("state")}, last={st.get("last_status")})')
            return True
    _log(f'[1/5] ❌ 停局超时(>{stop_timeout:.0f}s 仍 running),中止——'
         f'绝不停不下来就重启(daemon r99 同判据)。请人工核查游戏画面。')
    return False


# ── 步骤②:哨兵杀净(复用 rewatch,单一源)──────────────────────────

def kill_watchers(wanted: list[str]) -> None:
    """杀净旧哨兵实例 + 删事件哨兵旧水位,逻辑全走 rewatch(不自起纪律的另一半)。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rewatch  # noqa: PLC0415  局部导入:仅此函数需要
    procs = rewatch.find_old_watchers()
    rewatch.print_old_list(procs)
    rewatch.kill_all(procs)
    pos = os.path.join(WATCH_DIR, 'cw_sentinel.pos')
    if 'sentinel' in wanted and os.path.exists(pos):
        with contextlib.suppress(OSError):
            os.unlink(pos)
        _log('[2/5] 已删旧水位 cw_sentinel.pos')


# ── 步骤③:daemon 重启主 server(最小 MCP streamable-http 客户端)────

def _mcp_sse_result(body: str) -> dict:
    """从响应体取 JSON-RPC result:兼容裸 JSON 与 SSE(event/data 分帧)两种返回。"""
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(body)['result']
    for ln in reversed(body.splitlines()):
        if ln.startswith('data:'):
            return json.loads(ln[5:].strip())['result']
    raise RuntimeError(f'daemon 响应不可解析: {body[:200]}')


def daemon_restart_server(timeout: float = 150.0) -> str:
    """调 daemon 的 restart_sr_od_mcp_server tool,返回其文本结果。

    只搭协议(initalize 换 session id → initialized → tools/call),
    启停逻辑单源仍在 daemon。异常向上抛,由调用方决定降级。
    """
    sess: dict = {}

    def _post(payload: dict) -> dict | None:
        """POST 一条 JSON-RPC 消息;返回 result(通知类消息按协议回 202 空体 → None)。"""
        hdrs = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
        if sess.get('id'):
            hdrs['mcp-session-id'] = sess['id']
        req = urllib.request.Request(DAEMON_MCP, method='POST',
                                     data=json.dumps(payload).encode(), headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.headers.get('mcp-session-id'):
                sess['id'] = resp.headers['mcp-session-id']
            body = resp.read().decode('utf-8', errors='replace')
        if not body.strip():
            return None   # 202 Accepted(notification 无响应体,协议规定)
        return _mcp_sse_result(body)

    _rid = 0

    def rid() -> int:
        nonlocal _rid
        _rid += 1
        return _rid

    _post({'jsonrpc': '2.0', 'id': rid(), 'method': 'initialize',
           'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                      'clientInfo': {'name': 'cw-cycle-restart', 'version': '1'}}})
    _post({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
    res = _post({'jsonrpc': '2.0', 'id': rid(), 'method': 'tools/call',
                 'params': {'name': 'restart_sr_od_mcp_server', 'arguments': {}}})
    assert res is not None   # tools/call 必有响应体(notification 分支只对通知触发)
    content = res.get('content') or []
    text = content[0].get('text', '') if content else ''
    if '[ERROR]' in text:
        raise RuntimeError(f'daemon 重启失败: {text}')
    return text


def wait_server_up(restart_wait: float) -> bool:
    """轮询主 server /game/status 直到可应答(server 起来有初始化耗时)。"""
    deadline = time.time() + restart_wait
    while time.time() < deadline:
        try:
            st = _http(f'{MAIN_SERVER}/game/status')
            _log(f'[3/5] ✅ 新 server 应答(state={st.get("state")})')
            return True
        except Exception:   # noqa: BLE001  还没起来,继续等
            time.sleep(3)
    return False


def restart_server(skip: bool, restart_wait: float) -> bool:
    """③ 重启主 server 加载新代码;daemon 不可达时降级为提示并按 skip=False 中止。"""
    if skip:
        _log('[3/5] --skip-restart:跳过重启(本轮无待载代码时用)')
        return True
    try:
        out = daemon_restart_server()
    except Exception as e:   # noqa: BLE001
        _log(f'[3/5] ❌ daemon(:24000) 重启调用失败: {e!r}')
        _log('[3/5] 请人工执行 MCP 工具 restart_sr_od_mcp_server 后重跑 '
             '`cycle_restart.py --no-arm`(或确认 daemon 存活)。中止后续步骤。')
        return False
    _log(f'[3/5] daemon 返回: {" | ".join(ln.strip() for ln in out.splitlines() if ln.strip())}')
    if not wait_server_up(restart_wait):
        # 排障入口=运行日志单一信道(op/框架日志,单一源=server.py MCP_SERVER_LOG_FILE_NAME);
        # main_server.log 只是 daemon 重定向的 stdout 兜底,仅收 traceback,静默属常态。
        _log(f'[3/5] ❌ 重启后 {restart_wait:.0f}s 内主 server 未应答,中止。查运行日志 .log/mcp_server.log'
             '(stdout 兜底 .debug/sr_od_mcp/main_server.log 仅在有 traceback 时才有内容)')
        return False
    return True


# ── 步骤④:武装哨兵(本进程 Popen 子进程,阻塞看守见 supervise)───────

def arm_watchers(wanted: list[str]) -> list[subprocess.Popen]:
    """武装哨兵:作为本进程子进程起(继承控制台句柄,退出码由本进程接收转达)。

    命令口径与 runtime-ops 一致($env:PYTHONUTF8=1 + uv run python);注意
    「会话后台任务信道」要求的落点在本脚本自身如何被执行(必须由编排者经
    后台任务起本脚本),不在此处 DETACHED——那是 2026-08-25 明令禁止的哑哨兵形态。
    """
    env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    kids: list[subprocess.Popen] = []
    for key in wanted:
        name, note = WATCHERS[key]
        script = os.path.join(WATCH_DIR, name)
        if not os.path.exists(script):
            _log(f'[4/5] ⚠️ 缺哨兵脚本 {script}({note})——跳过该件')
            continue
        kid = subprocess.Popen(['uv', 'run', 'python', script], cwd=REPO_ROOT, env=env)
        kids.append(kid)
        _log(f'[4/5] 已武装 {key}: pid={kid.pid} {name}({note})')
    if len(kids) != len(wanted):
        _log(f'[4/5] ⚠️ 武装件数 {len(kids)} < 计划 {len(wanted)},建议人工核岗')
    time.sleep(3)   # 给哨兵完成水位定位,避免起局日志洪水淹没 armed 行
    for kid in kids:
        if kid.poll() is not None:
            _log(f'[4/5] ❌ 哨兵 pid={kid.pid} 起 3s 内即退(码 {kid.returncode})——先修再起局')
    return [k for k in kids if k.poll() is None]


# ── 步骤⑤:起局 ────────────────────────────────────────────────────

def start_app(app_id: str) -> bool:
    """POST /game/run/standalone 非阻塞起局,并回读一次状态确认 accepted。"""
    try:
        res = _http(f'{MAIN_SERVER}/game/run/standalone?app_id={app_id}&block=false', method='POST')
    except Exception as e:   # noqa: BLE001
        _log(f'[5/5] ❌ 起局请求失败: {e!r}')
        return False
    if not res.get('started'):
        _log(f'[5/5] ❌ 未受理: {res}')
        return False
    st = _http(f'{MAIN_SERVER}/game/status')
    _log(f'[5/5] ✅ 起局受理 app={res.get("app", app_id)} state={st.get("state")} '
         f'started_at={st.get("started_at")}——进度看 MCP get_run_status 或 GET /game/status')
    return True


# ── 看守:任一哨兵退出即上报,终止兄弟,带码退出 ──────────────────────

def supervise(kids: dict[int, subprocess.Popen]) -> int:
    """阻塞看守:首个哨兵退出 → 打印事件摘要,终止其余兄弟,按退出码分类返回。

    哨兵退出本身 = 待验证事件(IDLE 正常交接 / HIT·SILENCE·LOOP 报警都在其
    打印流里),统一上报给编排者判断;这里只负责「醒来 + 不吞退出码」。
    """
    _log(f'[看守] {len(kids)} 件哨兵在岗,阻塞值守中……(哨兵任意一件退出即唤醒上报)')
    names = {}
    for k in kids.values():
        names[k.pid] = next((key for key, v in WATCHERS.items() if key in k.args[-1]), '?')
    while True:
        time.sleep(2)
        for pid, kid in list(kids.items()):
            rc = kid.poll()
            if rc is None:
                continue
            del kids[pid]
            tone = '[CYCLE-IDLE]' if rc == 0 else '[CYCLE-ALARM]'
            _log(f'{tone} 哨兵 {names.get(pid)}(pid={pid})退出 code={rc}'
                 f'{"——正常交接窗(局终/IDLE),请判读并启动下一周期" if rc == 0 else "——报警/异常,读上方该哨兵输出判定"}')
            for other in kids.values():
                with contextlib.suppress(Exception):
                    other.terminate()
            _log('[看守] 其余哨兵已终止(防双实例残留);全程结束')
            return 0 if rc == 0 else (rc or 7)


def main() -> None:
    parser = argparse.ArgumentParser(description='CW 停局-杀净-重启载码-武装-起局 一键化(详见面板 docstring)')
    parser.add_argument('--app', default='currency_war', help='独立应用 id(默认 currency_war)')
    parser.add_argument('--to-ready', action='store_true', help='只做①②③,打印就绪信号即退(编排者手动收尾)')
    parser.add_argument('--stop-only', action='store_true', help='只做①停局即退(分步保守形态,②③④⑤全不碰)')
    parser.add_argument('--start-only', action='store_true', help='只做⑤起局(server 已就绪后补跑)')
    parser.add_argument('--no-arm', action='store_true', help='不起哨兵(只打印标准武装命令)')
    parser.add_argument('--early', action='store_true', help='哨兵组含 early_stop(纪律:首条遥测落后再武装)')
    parser.add_argument('--no-supervise', action='store_true', help='武装+起局后不阻塞看守(报警链自断风险,慎用)')
    parser.add_argument('--skip-restart', action='store_true', help='跳过③重启(本轮无待载代码)')
    parser.add_argument('--stop-timeout', type=float, default=900, help='①停局等待上限秒(默认 900)')
    parser.add_argument('--restart-wait', type=float, default=120, help='③重启后等 server 应答上限秒(默认 120)')
    args = parser.parse_args()

    wanted = ['sentinel', 'gap'] + (['early'] if args.early else [])

    if args.start_only:
        sys.exit(0 if start_app(args.app) else 2)

    if args.stop_only:
        _log('[开始] CW 周期重启 --stop-only:只做①停局,其余步骤不碰')
        if not stop_running(args.stop_timeout):
            sys.exit(3)
        return

    _log(f'[开始] CW 周期重启:停局→杀净→重启载码→武装({"/".join(wanted)})→起局({args.app})')

    if not stop_running(args.stop_timeout):
        sys.exit(3)
    kill_watchers(wanted)
    if not restart_server(args.skip_restart, args.restart_wait):
        sys.exit(3)

    if args.to_ready:
        _log('[READY] ①②③ 完成——server 新代码已生效。编排者收尾:')
        for key in wanted:
            name, _note = WATCHERS[key]
            print(f"  武装: $env:PYTHONUTF8='1'; uv run python {os.path.join('.debug', 'temp', 'currency_war', name)}")
        print(f'  起局: uv run python tools/cw/cycle_restart.py --start-only --app {args.app}')
        print('  前提自查: analyze_screen 确认货币战争-大厅(runtime-ops 残局清理序)')
        return

    kids_list: list[subprocess.Popen] = []
    if args.no_arm:
        _log('[4/5] --no-arm:跳过武装(报警链在本场景无接收方,哨兵不起;建议改用缺省形态)')
    else:
        kids_list = arm_watchers(wanted)
        kids = {k.pid: k for k in kids_list}
        if not kids:
            _log('[4/5] ❌ 一件哨兵都没起来,中止起局(裸奔局烧时间没人报)')
            sys.exit(3)
    if not start_app(args.app):
        for kid in kids_list:
            kid.terminate()
        sys.exit(2)
    if args.no_supervise or args.no_arm:
        _log('[完] 起局完成;看守已关(--no-supervise/--no-arm)——编排者需自管监控兜底')
        return
    sys.exit(supervise(kids))


if __name__ == '__main__':
    main()
