"""后端服务层：传输无关地包装 SrContext，提供感知/操作方法。

本模块是后端 game 切片的地基：
- ``SrBackendContext`` 持有 ``SrContext``，管理其生命周期，并对外暴露与
  传输协议（HTTP/IPC 等）无关的感知/操作方法。
- ``BackendNotReadyError`` 在前置校验失败（SrContext 尚未就绪）时抛出。

game 切片方法（``check_window``/``capture``/``analyze``）从
``SrContext`` 的控制器、OCR 服务、运行上下文中读取数据，并以 ``sr_od.backend.schemas``
中的传输无关结构返回。运行类操作（``start_run``/``run_one_dragon``/
``run_standalone_app``/``query_status``/``stop``）统一委托给单个 ``RunSlot``，
槽内按 app / op 路径分派（详见 ``RunSlot``）。
"""

import asyncio
import contextlib
import json
import subprocess
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from one_dragon.base.config.basic_game_config import TypeInputWay
from one_dragon.base.controller.pc_clipboard import PcClipboard
from one_dragon.base.controller.stop_guard import (
    StopRunInterrupted,
    stop_guard_exemption,
)
from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation import window_run_mutex
from one_dragon.base.operation.application import application_const
from one_dragon.base.operation.application.application_run_context import (
    RunFinishReason,
)
from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_area import ScreenArea
from one_dragon.base.screen.screen_info import ScreenInfo
from one_dragon.base.screen.screen_match import find_screen_matches
from one_dragon.utils import cv2_utils, debug_utils, os_utils, str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log, mask_text
from sr_od.backend.schemas import (
    AnalyzeScreenResult,
    ApplicationInfo,
    ApplicationListResult,
    OcrText,
    RunStatusResult,
    WindowStatus,
)
from sr_od.backend.screen_recognizer_scan import get_recognizer
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.operation.operation import Operation


# analyze_screen 返回的能力边界提示:本结果仅含 OCR + 模板匹配的部分识别,
# 提醒调用方(智能体)需要全面判断画面时,补一步视觉工具 / 多模态再看。
# 见 docs/develop/sr_od/backend/design-principles.md P6/P13。
_VISION_HINT = (
    '本工具=识别层对账(画面身份判定/area 命中坐标/结构化数据),与视觉判读互补:'
    '理解画面布局、图标语义、状态或未建档元素 → 用视觉模型直接看截图'
    '(save_image=True 回传 screenshot_path);本结果与视觉判读不一致时,'
    '优先怀疑建档漂移(area 坐标/文本过期),回验 screen_info。'
)


def _iso(ts: float | None) -> str | None:
    """epoch 秒 → ISO 字符串(None 透传)。"""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts).isoformat()


def _validate_pc_rect(pc_rect: list[int]) -> str | None:
    """校验 pc_rect=[x1,y1,x2,y2];合法返 None,否则返错误描述。"""
    if (not isinstance(pc_rect, list) or len(pc_rect) != 4
            or not all(isinstance(v, int) for v in pc_rect)):
        return f'pc_rect 非法(需 4 个整数): {pc_rect}'
    x1, y1, x2, y2 = pc_rect
    if not (0 <= x1 < x2 <= 1920 and 0 <= y1 < y2 <= 1080):
        return f'pc_rect 越界或非正(需 1920×1080 内、x2>x1、y2>y1): {pc_rect}'
    return None


def _area_result(success: bool, screen_name: str, area_name: str, action: str | None,
                 error: str | None = None, count: int | None = None) -> dict:
    """构造 area CRUD 的统一返回 dict。"""
    return {
        'success': success,
        'screen_name': screen_name,
        'area_name': area_name,
        'action': action,
        'area_count': count,
        'error': error,
    }


class RunState(str, Enum):
    """运行槽状态。

    IDLE:从未运行;RUNNING:operation 活(含 stop 后退出中的间隙,统一报 RUNNING);
    SUCCESS/FAILED/STOPPED:终态(固化)。无 PAUSED(当前不可达)、无 STOPPING(框架无此态)。
    """

    IDLE = 'idle'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    STOPPED = 'stopped'


class RunType(str, Enum):
    """运行单元类型:app 路径委托 run_application,op 路径槽自管生命周期。"""

    APPLICATION = 'application'
    OPERATION = 'operation'


class RunSlot:
    """单跑道运行槽:MCP/HTTP 共享,固化终态,运行中读 operation 实例。

    状态判据用固化字段 terminal_state(单一事实源),不读 run_context 推中间态。
    详见 docs/superpowers/specs/2026-07-05-mcp-run-state-design.md。
    """

    def __init__(self, ctx: 'SrContext', thread_name_prefix: str = 'sr_backend_run') -> None:
        self._ctx: SrContext = ctx
        self._lock: threading.Lock = threading.Lock()
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=thread_name_prefix)
        self.source: str | None = None
        self.op_id: str | None = None          # 唯一标识(定位用):app 路径=app_id、op 路径=display_name 或类名
        self.run_type: RunType | None = None   # APPLICATION / OPERATION
        self.app: str | None = None            # 展示名(_run 内固化):op 路径=op.op_name、app 路径=get_application_name
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.terminal_state: RunState | None = None
        self.last_status: str | None = None
        self.failed_node: str | None = None
        self.future: Future | None = None
        self.current_op: Operation | None = None
        # 最近一次 _start 拒绝的原因;None = 拒绝源于本进程已有运行(历史语义)。
        # 跨进程窗口占用与本进程已有 run 须可区分(2026-08-24 双进程交替操作事故
        # 的排查教训:笼统的「已有运行在进行中」把排障引向错误进程),受理成功时
        # 清空。start 类入口经 run_refusal_response 消费。
        self.last_refusal_reason: str | None = None

    def is_running(self) -> bool:
        """当前槽是否有未完成的运行。"""
        with self._lock:
            return self.future is not None and not self.future.done()

    def has_history(self) -> bool:
        """当前槽是否有可查询的历史运行。"""
        with self._lock:
            return self.started_at is not None

    def _start(
        self,
        source: str,
        op_factory: 'Callable[[SrContext], Operation] | None' = None,
        app_id: str | None = None,
        instance_idx: int | None = None,
        group_id: str | None = None,
        display_name: str | None = None,
        refresh_config: 'Callable[[], None] | None' = None,
    ) -> tuple[bool, Future | None]:
        """触发运行(单跑道)。op_factory 与 app_id 二选一,互斥校验。

        - op 路径(op_factory):槽自管 start_running/execute/stop_running(open_game / 自定义 op)。
        - app 路径(app_id):委托 run_application(复用 GUI/CLI 共享入口)。

        check 与 submit 在同一把锁内原子,消除跨槽 check-then-act 竞态。

        Args:
            source: 触发方标识(如 ``"mcp"``/``"http"``)。
            op_factory: operation 构造器(op 路径,与 app_id 互斥)。
            app_id: 应用 id(app 路径,与 op_factory 互斥)。
            instance_idx: 账号实例下标;op 路径 None 时取 ctx.current_instance_idx。
            group_id: 应用组 id(app 路径)。
            display_name: op 路径定位标识(如 op_id);None 时 _run 内 fallback 类名。
            refresh_config: 配置刷新钩子(app 路径在 run_application 前、_start 已赢锁后调用)。

        Returns:
            (ok, future):ok=False 表示已有运行在进行(future=None);ok=True 表示已启动。

        Raises:
            ValueError: op_factory 与 app_id 同时传或同时缺省。
        """
        if (op_factory is None) == (app_id is None):
            raise ValueError('op_factory 与 app_id 必须二选一')
        with self._lock:
            if self.future is not None and not self.future.done():
                # 本进程已有 run 的拒绝:清掉可能残留的上一次拒绝原因,让拒绝
                # 响应回落「已有运行在进行中」历史文案(每次拒绝只记自己的因)。
                self.last_refusal_reason = None
                return False, None                         # 单跑道:已在跑就拒(拒绝路径不刷新配置)
            # 跨进程窗口占用探测:本槽空闲但游戏窗口被他进程驱动时,受理前即拒
            # (2026-08-24 双进程交替操作事故)。权威判定仍在运行门
            # (ApplicationRunContext.start_running 真实取锁),此处是快速拒绝的
            # 提示层;探测存在竞态窗口,竞态漏过时由运行门兜住、运行快速失败。
            blocker = window_run_mutex.describe_window_blocker(self._ctx.controller)
            if blocker is not None:
                self.last_refusal_reason = f'游戏窗口被他进程占用({blocker})'
                return False, None
            self.last_refusal_reason = None
            self.terminal_state = None
            self.last_status = None
            self.failed_node = None
            self.finished_at = None
            self.op_id = app_id or display_name            # app 路径=app_id;op 路径=display_name,未传则 _run 内 fallback 类名
            self.run_type = RunType.APPLICATION if app_id is not None else RunType.OPERATION
            self.app = None                                # 展示名待 _run 填
            self.source = source
            self.started_at = time.time()
            self.future = self._executor.submit(
                self._run, source, op_factory, app_id, instance_idx, group_id, refresh_config,
            )
            return True, self.future

    def _run(
        self,
        source: str,
        op_factory: 'Callable[[SrContext], Operation] | None',
        app_id: str | None,
        instance_idx: int | None,
        group_id: str | None,
        refresh_config: 'Callable[[], None] | None',
    ) -> OperationResult | None:
        """后台线程:按 app / op 分派执行,顶层 try/except/finally 固化终态。

        - app 路径:refresh_config → 委托 run_application → 读 last_application_result。
        - op 路径:start_running → op_factory(ctx) → op.execute() → stop_running。

        任何异常都固化终态(镜像原 RunSlot 安全网),避免卡 terminal_state=None/RUNNING。
        """
        ctx = self._ctx
        run_context = ctx.run_context
        result: OperationResult | None = None
        failed_node: str | None = None
        try:
            if app_id is not None:
                # —— app 路径:委托 run_application(共享入口)——
                if refresh_config is not None:
                    refresh_config()                       # 槽线程内、_start 已赢锁后、run_application 前(修刷新竞态)
                # 刷新后再读实例下标(refresh_config 可能切实例),修 instance_idx 回归
                run_context.current_instance_idx = ctx.current_instance_idx
                try:
                    self.app = run_context.get_application_name(app_id)   # 固化应用中文名
                except Exception:  # noqa: BLE001
                    self.app = app_id
                run_result = run_context.run_application(
                    app_id, run_context.current_instance_idx, group_id
                )
                if run_result.finish_reason == RunFinishReason.NOT_STARTED:
                    # 未启动时透出跨进程窗口占用(若有):占用拒绝与其它未启动
                    # 原因须可区分,否则 agent 只见 NOT_STARTED 无从归因。
                    blocker = getattr(run_context, 'window_mutex_blocker', None)
                    if isinstance(blocker, str) and blocker:
                        result = OperationResult(
                            success=False,
                            status=f'应用未启动: 游戏窗口被他进程占用({blocker})',
                        )
                    else:
                        result = OperationResult(
                            success=False,
                            status=f'应用运行失败: {run_result.finish_reason}',
                        )
                else:
                    result = run_context.last_application_result
                    if result is None:
                        result = OperationResult(
                            success=False,
                            status=f'应用运行失败: {run_result.finish_reason}',
                        )
            else:
                # —— op 路径:槽自管生命周期(open_game / 自定义 op 通用)——
                run_context.current_instance_idx = instance_idx if instance_idx is not None else ctx.current_instance_idx
                if not run_context.start_running():
                    # 失败原因区分跨进程窗口占用与进程内其它运行(运行门在
                    # window_mutex_blocker 记录占用描述;isinstance 防测试替身)。
                    blocker = getattr(run_context, 'window_mutex_blocker', None)
                    if isinstance(blocker, str) and blocker:
                        result = OperationResult(
                            success=False,
                            status=f'start_running 失败(游戏窗口被他进程占用: {blocker})',
                        )
                    else:
                        result = OperationResult(success=False, status='start_running 失败(有其它运行)')
                else:
                    op: Operation | None = None
                    try:
                        op = op_factory(ctx)
                        with self._lock:
                            self.current_op = op
                            if self.op_id is None:
                                self.op_id = op.__class__.__name__   # open_game 未传 display_name 时 fallback 类名
                            self.app = op.op_name or op.__class__.__name__   # 优先 Operation.op_name(中文),空时类名
                        result = op.execute()
                    except StopRunInterrupted:
                        # 停机守卫穿透到顶层(ADR-0396):收口「已停止」,终态计算
                        # 按 '已停止' 前缀落 STOPPED,不误标执行异常。
                        result = OperationResult(success=False, status='已停止[guard]')
                    except Exception as e:  # noqa: BLE001 execute 抛异常也兜住,避免卡 RUNNING
                        result = OperationResult(success=False, status=f'执行异常: {e}')
                    finally:
                        # 清除句柄前本地捕获失败节点(修 failed_node 丢失),与原 RunSlot 一致
                        failed_node = getattr(getattr(op, '_current_node', None), 'cn', None) if op is not None else None
                        with self._lock:
                            self.current_op = None
                        # 正常收口而非 stop_running(ADR-0396):op 自然完成后清理运行态,
                        # 不置停机中断闩——否则后续 MCP 手动操作(残局清理)会被守卫误拦。
                        run_context.finish_running()
        except StopRunInterrupted:
            # 停机守卫穿透(ADR-0396,app 路径兜底:run_application 已收口,此为
            # refresh_config 等外层环节被拦的极端路径):不误标执行异常。
            result = OperationResult(success=False, status='已停止[guard]')
        except Exception as e:  # noqa: BLE001 兜底:refresh_config/run_application 等抛异常也固化,避免卡 RUNNING
            result = OperationResult(success=False, status=f'执行异常: {e}')
        finally:
            # —— 固化终态(任何路径都执行,镜像原 RunSlot finally)——
            # 内层再兜一层异常(2026-08-24 终态残留 bug):此前 finally 内任何一处
            # 抛异常(候选:status=None 时 startswith / _node_name 属性链)会让 future
            # 以异常态完成且被 executor 静默吞掉——线程回池、future done,但
            # terminal_state 永不赋值 → /game/status 恒 running(daemon restart 守卫
            # 被误拒),而 stop_run/新 _start 又认为无运行(sim 3 次实证 19:27/21:09/
            # 21:58,py-spy 全线程 idle + future done + status=running 三证齐)。
            # 兜底保证固化不变量「finally 必达」:异常时强制 FAILED + 栈留痕。
            try:
                _status = result.status if (result is not None and result.status) else ''
                terminal = (RunState.SUCCESS if (result is not None and result.success)
                            else RunState.STOPPED if _status.startswith('已停止')
                            else RunState.FAILED)
                if failed_node is None:
                    failed_node = self._node_name() or (_status or None)
            except Exception as e:  # noqa: BLE001 固化前置计算炸 → 强制失败终态,别让状态悬空
                from one_dragon.utils.log_utils import log as _diag_log
                _diag_log.error('[slot-diag] 终态计算异常(强制 FAILED): %s', e, exc_info=True)
                terminal = RunState.FAILED
                result = OperationResult(success=False, status=f'终态计算异常: {e}')
            with self._lock:
                self.terminal_state = terminal
                self.last_status = result.status if result is not None else '执行异常'
                self.failed_node = failed_node if terminal == RunState.FAILED else None   # 仅 FAILED 记失败节点
                self.finished_at = time.time()
            from one_dragon.utils.log_utils import log as _diag_log
            _diag_log.info('[slot-diag] _run finally 固化: terminal=%s op_id=%s', terminal, self.op_id)
        return result

    def _node_name(self) -> str | None:
        """统一读进度句柄的当前节点(app 路径读 current_application,op 路径读 current_op)。"""
        op = self.current_op or self._ctx.run_context.current_application
        node = getattr(op, '_current_node', None) if op is not None else None
        return getattr(node, 'cn', None) if node is not None else None

    def _query_status(self) -> RunStatusResult:
        """查询运行状态。判据用固化 terminal_state(单一事实源),不读 run_context。

        终态:返固化 terminal_state + last_status/failed_node。
        运行中(started_at 非 None 且 terminal_state None):统一 RUNNING,
        进度读 progress = current_op or run_context.current_application(Application 也是 Operation)。
        空闲(从未运行,started_at None):返 idle。
        """
        with self._lock:
            if self.terminal_state is not None:
                duration = (self.finished_at - self.started_at) if (self.finished_at and self.started_at) else None
                return RunStatusResult(
                    state=self.terminal_state.value,
                    source=self.source, app=self.app,
                    started_at=_iso(self.started_at), duration_seconds=duration,
                    last_status=self.last_status, failed_node=self.failed_node,
                )
            source = self.source
            app = self.app
            started_at = self.started_at
            op = self.current_op
            if started_at is None:
                return RunStatusResult(state=RunState.IDLE.value, source=source)
        # 进度句柄:op 路径读 current_op,app 路径(current_op=None)读 run_context.current_application
        progress = op if op is not None else self._ctx.run_context.current_application
        node = getattr(progress, '_current_node', None) if progress is not None else None
        current_node = getattr(node, 'cn', None) if node is not None else None
        retry_count = getattr(progress, 'node_retry_times', None) if progress is not None else None
        duration = (time.time() - started_at) if started_at else None
        return RunStatusResult(
            state=RunState.RUNNING.value,
            source=source, app=app,
            started_at=_iso(started_at), duration_seconds=duration,
            current_node=current_node, retry_count=retry_count,
        )

    def _stop(self) -> tuple[bool, str | None]:
        """发出停止信号(run_context.stop_running 直接设 STOP,非阻塞)。

        operation 实际退出有过渡期(下一轮才退),期间 _query_status 仍报 running。

        Returns:
            (stopped, source):无运行 → (False, None);否则 (True, 被停运行的触发方)。
        """
        with self._lock:
            if self.future is None or self.future.done():
                return False, None
            source = self.source
        self._ctx.run_context.stop_running(reason='mcp:stop_run')
        return True, source

    def shutdown(self) -> None:
        """关闭运行槽:停掉单跑道线程池,释放其后台线程。

        backend 关闭时调用;不等待在跑的 operation(ThreadPoolExecutor 无法中断
        在跑任务,仍在跑的会在进程退出时随线程结束)。``cancel_futures`` 取消排队
        中的 future(Py3.9+,本项目 3.11 满足)。
        """
        self._executor.shutdown(wait=False, cancel_futures=True)


class BackendNotReadyError(Exception):
    """后端未就绪。

    当 ``SrContext`` 尚未完成初始化，或控制器/游戏窗口缺失时抛出，
    用于在调用 game 切片方法前做统一的前置校验。
    """


def _save_screenshot(image: 'MatLike') -> str:
    """将 RGB 截图以 BGR 写盘到 ``.debug/sr_od_mcp/screenshot/``,返回绝对路径。

    Args:
        image: backend ``capture`` / ``analyze`` 截到的 RGB ``ndarray``。

    Returns:
        保存后的截图文件绝对路径。

    Raises:
        RuntimeError: ``cv2.imwrite`` 写盘失败时抛出。
    """
    import cv2

    screenshot_dir = Path(os_utils.get_path_under_work_dir('.debug', 'sr_od_mcp', 'screenshot'))
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    img_path = screenshot_dir / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    bgr_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    if not cv2.imwrite(str(img_path), bgr_image):
        raise RuntimeError(f'截图写盘失败: {img_path}')
    return str(img_path)


# start 模式宽限期(秒):覆盖 gdigrab 打开 + 编码器会话初始化(实测约 1.5-2s 产出
# 首帧),又要短于「活着但注定失败」的误报窗口——采集源/编码器错误均在 1s 内退出,
# 2.5s 能把两类干净分开。
_RECORDER_START_GRACE_SECONDS: float = 2.5


def _resolve_ffmpeg_exe() -> str | None:
    """延迟解析 ffmpeg 路径(imageio_ffmpeg → PATH),缺失返回 None。

    延迟导入的原因:imageio-ffmpeg 是 dev 依赖,缺失时不能影响 server 启动,
    只能在真正录屏时暴露。
    """
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        import shutil
        return shutil.which('ffmpeg')


def _probe_h264_nvenc(ffexe: str) -> bool:
    """探测本机 h264_nvenc 可用性:lavfi 合成源试编码 3 帧,可用返回 True。

    为什么探测而不是直接录:无 NVIDIA 显卡/驱动的机器上 nvenc 在编码器初始化时
    直接退出,录屏以失败告终。合成源试编码约 0.3s(实测)换确定性的编码器
    选择,不可用时回退 libx264 软编(imageio-ffmpeg 自带),去除硬编码的
    NVIDIA 硬依赖。探测异常(如缺 lavfi 滤镜)一律按不可用处理,走向软编。
    """
    try:
        proc = subprocess.run(
            [ffexe, '-hide_banner', '-loglevel', 'error',
             '-f', 'lavfi', '-i', 'color=c=black:s=256x256:d=0.1',
             '-frames:v', '3', '-c:v', 'h264_nvenc', '-f', 'null', '-'],
            capture_output=True, timeout=10,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _record_dir() -> Path:
    """录屏输出目录。独立成函数仅为让测试重定向到 tmp_path(禁写真实 .debug)。"""
    return Path('.debug', 'record')


def _build_record_cmd(
    ffexe: str,
    input_arg: str,
    encoder: str,
    out_path: str,
    mode: str,
    fps: int,
    bitrate: str,
    duration: float,
) -> list[str]:
    """组装 ffmpeg 录屏命令。fragmented 参数组仅 start 模式携带,见分支内注释。"""
    cmd = [ffexe, '-hide_banner', '-loglevel', 'error',
           '-f', 'gdigrab', '-framerate', str(fps), '-draw_mouse', '1',
           '-i', input_arg,
           '-c:v', encoder, '-preset', 'fast', '-b:v', bitrate,
           '-pix_fmt', 'yuv420p']
    if mode == 'fixed':
        # -t 让 ffmpeg 录满自停:正常收尾写 moov trailer,产出干净 mp4。
        cmd += ['-t', str(duration)]
    else:
        # start 模式 = kill-safe fragmented mp4。四件缺一不可(ffmpeg 7.1 gdigrab
        # + nvenc 4K 桌面逐项实测定谳),少任何一件被 kill 后都不可播:
        # - movflags 必须是 empty_moov(带下划线的 mp4 muxer 合法 flag);误拼
        #   emptymoov 会让 ffmpeg 在解析 movflags 时直接退出、产出 0 字节文件
        #   (.debug/record/ 下历史 0 字节 startstop 产物即此根因);
        # - g=fps(1 秒一个关键帧)驱动 frag_keyframe 每秒切一个 fragment——
        #   nvenc 默认关键帧间隔太长,不强制则 fragment 迟迟不落盘;
        # - flush_packets=1 把每个 fragment 立刻写盘,否则低码率开头会滞留
        #   在 AVIO 缓冲里,kill 时连 ftyp+moov 都没到磁盘;
        # - h264_nvenc 须加 delay=0:其默认 delay=INT_MAX 把编码包攒到 EOF 才
        #   一次性吐出,mid-run kill 全部丢失(fragmented muxer 无包可切)。
        #   libx264 无 delay 选项,传了直接报错,故仅 nvenc 携带。
        cmd += ['-g', str(fps),
                '-movflags', '+frag_keyframe+empty_moov+default_base_moof',
                '-flush_packets', '1']
        if encoder == 'h264_nvenc':
            cmd += ['-delay', '0']
    cmd += [out_path, '-y']
    return cmd


def _drain_stderr(proc: subprocess.Popen, limit: int = 400) -> str:
    """读出子进程 stderr 摘要文本(loglevel error 下输出量极小,不会撑爆管道)。

    Args:
        proc: 目标进程(通常已退出;stderr 可能为 None——继承句柄或假对象)。
        limit: 摘要最大字符数。

    Returns:
        去掉换行后的 stderr 前 ``limit`` 字符;读不到返回空串。
    """
    stream = getattr(proc, 'stderr', None)
    if stream is None:
        return ''
    try:
        text = stream.read().decode('utf-8', errors='replace')
    except Exception:
        return ''
    return ' '.join(text.split())[:limit]


def _wait_recorder_early_death(proc: subprocess.Popen, grace_seconds: float) -> str | None:
    """start 模式宽限等待:ffmpeg 在宽限期内退出则返回 stderr 摘要,存活返回 None。

    为什么需要:Popen 成功不等于 ffmpeg 活着——坏 flag、编码器不可用、采集源
    失败都会让它在启动后 1 秒内退出;不检查就会把死进程当「录屏中」报给调用方,
    stop 收尾拿到 0 字节文件还报成功。
    """
    time.sleep(grace_seconds)
    if proc.poll() is None:
        return None
    err = _drain_stderr(proc)
    return err if err else f'ffmpeg 已退出(returncode={proc.returncode})'


class SrBackendContext:
    """后端 context：持有 ``SrContext``，管理生命周期，暴露传输无关方法。

    设计要点：
        - 生命周期方法（``start``/``shutdown``）通过 ``asyncio.to_thread``
          在线程池中调用 ``SrContext`` 的同步初始化/清理逻辑，避免阻塞事件循环。
        - ``ctx`` 属性仅供同进程内部使用，不应通过适配器对外暴露原始 context。
        - 任何 game 切片方法在执行前应先调用 ``_ensure_ready`` 校验。
    """

    def __init__(self, ctx: SrContext) -> None:
        """初始化后端 context。

        Args:
            ctx: 被包装的 ``SrContext`` 实例，由调用方负责构造并注入。
        """
        self._ctx: SrContext = ctx
        self.run_slot: RunSlot = RunSlot(ctx)
        # 录屏状态(dev-only record_screen 用);observe 类,独立于单跑道,可与 bot run 并行。
        self._recorder_lock = threading.Lock()
        self._recorder_proc: subprocess.Popen | None = None
        self._recorder_path: str | None = None
        # 已探测的录屏视频编码器('h264_nvenc'|'libx264');None=未探测(首次录屏时探测一次)。
        self._recorder_encoder: str | None = None

    @property
    def ctx(self) -> SrContext:
        """底层 ``SrContext``（仅同进程内部使用，不对外通过适配器暴露）。"""
        return self._ctx

    def _ensure_ready(self) -> None:
        """前置校验：确认 ``SrContext`` 已完成初始化、可运行应用。

        Raises:
            BackendNotReadyError: 当 ``ctx.ready_for_application`` 为 False 时抛出。
        """
        if not self._ctx.ready_for_application:
            raise BackendNotReadyError('SrContext 未就绪（ready_for_application=False）')

    def _refresh_runtime_config(self) -> None:
        """刷新外部 GUI 可能已经写入 YAML 的运行配置。

        MCP server 是独立进程，GUI 修改配置后不会自动更新本进程内的
        ``YamlConfig`` / ``ApplicationFactory`` 缓存。运行前刷新一次，可减少
        独立应用选择、体力计划、自动战斗配置等与 GUI 设置不一致的问题。
        """
        # one_dragon_config 是 cached_property；删除缓存后会从 YAML 重新构造。
        if 'one_dragon_config' in self._ctx.__dict__:
            del self._ctx.__dict__['one_dragon_config']
        active_instance = self._ctx.one_dragon_config.current_active_instance
        active_instance_idx = getattr(active_instance, 'idx', None)
        if isinstance(active_instance_idx, int) and active_instance_idx != self._ctx.current_instance_idx:
            # GUI 改了当前启用实例时，server 进程要同步切到同一个实例再运行。
            self._ctx.current_instance_idx = active_instance_idx
            self._ctx.reload_instance_config()
            self._ctx.on_switch_instance()
        else:
            self._ctx.reload_instance_config()
        # 应用配置和运行记录在工厂里有缓存；运行前清掉，下一次读取会落到最新 YAML。
        self._ctx.run_context.clear_application_cache()
        self._ctx.app_group_manager.clear_config_cache()

    def check_window(self) -> WindowStatus:
        """检查游戏窗口状态。

        读取控制器上当前的游戏窗口信息，封装为传输无关的 ``WindowStatus`` 返回。
        窗口矩形不可用时，坐标/尺寸字段为 None。

        Returns:
            游戏窗口状态（标题、有效性、激活态、缩放、客户区矩形）。

        Raises:
            BackendNotReadyError: ``SrContext`` 未就绪，或控制器/游戏窗口未初始化时抛出。
        """
        self._ensure_ready()
        controller = self._ctx.controller
        if controller is None or controller.game_win is None:
            raise BackendNotReadyError('控制器或游戏窗口未初始化')
        game_win = controller.game_win
        rect = game_win.win_rect
        return WindowStatus(
            win_title=game_win.win_title,
            is_win_valid=game_win.is_win_valid,
            is_win_active=game_win.is_win_active,
            is_win_scale=game_win.is_win_scale,
            x=rect.x1 if rect is not None else None,
            y=rect.y1 if rect is not None else None,
            width=rect.width if rect is not None else None,
            height=rect.height if rect is not None else None,
        )

    def capture(self) -> 'MatLike':
        """截取游戏当前画面。

        通过控制器对游戏窗口进行截图，返回 RGB ``ndarray``。

        Returns:
            截图图像（RGB ``MatLike``）。

        Raises:
            BackendNotReadyError: ``SrContext`` 未就绪、游戏窗口未就绪或截图返回 None 时抛出。
        """
        self._ensure_ready()
        controller = self._ctx.controller
        if controller is None or not controller.is_game_window_ready:
            raise BackendNotReadyError('游戏窗口未就绪')
        image = controller.get_screenshot(independent=False)
        if image is None:
            raise BackendNotReadyError('截图返回 None')
        # 打码 UID:对齐 controller.screenshot()(框架流程截图本就经 fill_uid_black 打码,
        # backend 截图供 MCP/HTTP 落盘 / 外传,同样不能带账号信息)。
        return controller.fill_uid_black(image)

    def _resolve_game_hwnd_input(self) -> str | None:
        """解析游戏窗口的 gdigrab 输入串 ``hwnd=<句柄>``;解析不出有效窗口返回 None。

        为什么不让 gdigrab 按 title 找窗:gdigrab 的 ``title=`` 内部是 FindWindow
        按标题取第一处命中,会命中同名隐藏 0×0 窗录到无效画面(录屏通道诊断结论,
        产物存 .debug/record/);框架 ``PcGameWindow`` 用 pygetwindow 枚举 +
        ``is_win_valid`` + ``win_rect``(零尺寸客户区判无效、最小化先恢复)解析出
        的句柄与 bot 截图同源,是已验证的采集目标,以它为准。
        """
        try:
            controller = self._ctx.controller
            game_win = controller.game_win if controller is not None else None
            if game_win is None:
                return None
            hwnd = game_win.get_hwnd()
            if not hwnd or not game_win.is_win_valid or game_win.win_rect is None:
                return None
            return f'hwnd={int(hwnd)}'
        except Exception:
            return None

    def record_screen(
        self,
        mode: str = 'fixed',
        duration: float = 10.0,
        out_name: str = 'rec',
        fps: int = 30,
        capture: str = 'window',
        bitrate: str = '6M',
    ) -> dict:
        """录屏(dev-only,需 dev 依赖 imageio-ffmpeg)。观察类,不占单跑道,可与 bot run 并行。

        ffmpeg gdigrab 采集,跑在本 server 进程(Session 1 / 交互桌面),故能录到
        游戏画面 —— 从 SSH / 服务会话(Session 0)直跑 ffmpeg 会 BitBlt
        ACCESS_DENIED,录不到交互桌面,这是录屏放 backend 的根本原因。

        编码器自动探测:h264_nvenc 可用(有 NVIDIA 显卡)则用之,否则回退 libx264
        软编,结果带 ``encoder`` 字段可观测。

        Args:
            mode: 'fixed'(默认)= 录 ``duration`` 秒后 ffmpeg 自停(-t,正常写 moov,
                mp4 干净),阻塞返回; 'start'= 后台开始(返回 pid),之后调
                ``mode='stop'`` 收尾(启动后经宽限期存活检查,启动即死的 ffmpeg
                直接报错而不是假成功;fragmented mp4,被 kill 也安全可播);
                'stop'= 停止进行中的录屏。
            duration: fixed 模式录制秒数。
            out_name: 输出文件名(可带可不带 .mp4),存 ``.debug/record/``。
            fps: 帧率。
            capture: 'window'= 按框架解析的游戏窗口句柄(hwnd=,防同名隐藏窗,
                解析不到退回 desktop);'desktop'= 全桌面。
            bitrate: 目标码率,如 ``6M``。

        Returns:
            ``{success, path?, pid?, action, error?, hint?, encoder?, returncode?}``。
            无 ffmpeg 时 success=False + error 提示装 dev 依赖(imageio-ffmpeg)。
            imageio-ffmpeg 为延迟导入,缺失不影响 server 启动。
        """
        with self._recorder_lock:
            if mode == 'stop':
                proc = self._recorder_proc
                out = self._recorder_path
                self._recorder_proc = None
                self._recorder_path = None
                if proc is None:
                    return {'success': False, 'error': '没有正在进行的录屏'}
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    with contextlib.suppress(Exception):
                        proc.kill()
                # fragmented mp4 被 TerminateProcess 截断也保持可播(参数组依据见
                # _build_record_cmd start 分支),故 stop 无需优雅收尾。
                return {'success': True, 'path': out, 'action': 'stopped',
                        'returncode': proc.returncode}

            ffexe = _resolve_ffmpeg_exe()
            if not ffexe:
                return {
                    'success': False,
                    'error': '未找到 ffmpeg。录屏是 dev-only,需 dev 依赖 imageio-ffmpeg',
                    'hint': '确认已 uv sync --group dev;或把 ffmpeg 放到 PATH',
                }

            out_dir = _record_dir()
            out_dir.mkdir(parents=True, exist_ok=True)
            if not out_name.lower().endswith('.mp4'):
                out_name = out_name + '.mp4'
            out_path = str((out_dir / out_name).resolve())

            input_arg = 'desktop'
            if capture == 'window':
                input_arg = self._resolve_game_hwnd_input() or 'desktop'

            encoder = self._recorder_encoder
            if encoder is None:
                encoder = 'h264_nvenc' if _probe_h264_nvenc(ffexe) else 'libx264'
                self._recorder_encoder = encoder

            cmd = _build_record_cmd(ffexe, input_arg, encoder, out_path, mode, fps, bitrate, duration)

            try:
                # stderr 接管道只为把 ffmpeg 的失败原因带回给调用方(loglevel
                # error 输出量极小,长录也不会撑爆管道缓冲)。
                proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)
            except Exception as e:
                return {'success': False, 'error': f'启动 ffmpeg 失败: {e}'}

            if mode == 'fixed':
                try:
                    proc.wait(timeout=duration + 10)
                    ok = proc.returncode == 0
                except subprocess.TimeoutExpired:
                    proc.kill()
                    with contextlib.suppress(Exception):
                        proc.wait()
                    ok = False
                result: dict = {'success': ok, 'path': out_path if ok else None,
                                'action': 'fixed', 'returncode': proc.returncode,
                                'encoder': encoder}
                if not ok:
                    err = _drain_stderr(proc)
                    result['error'] = err or f'ffmpeg 非零退出(returncode={proc.returncode})'
                return result

            if mode == 'start':
                death_err = _wait_recorder_early_death(proc, _RECORDER_START_GRACE_SECONDS)
                if death_err is not None:
                    return {'success': False, 'action': 'start',
                            'error': f'ffmpeg 启动后立即退出: {death_err}'}
                self._recorder_proc = proc
                self._recorder_path = out_path
                return {'success': True, 'pid': proc.pid, 'path': out_path,
                        'action': 'started', 'encoder': encoder,
                        'hint': '后台录屏中;调 record_screen(mode="stop") 收尾'}
            with contextlib.suppress(Exception):
                proc.kill()
            return {'success': False, 'error': f'未知 mode={mode}(支持 fixed/start/stop)'}

    @staticmethod
    def _resolve_screenshot(screenshot: str) -> 'tuple[MatLike | None, str]':
        """把 screenshot(绝对路径或 debug 图名)解析为(图像, 解析后完整路径)。

        绝对路径按路径读;否则当 ``.debug/images`` 下的 debug 图名,自动补 ``.png``。
        图像读不到时返回 ``(None, 解析后路径)``,由调用方报错。

        Args:
            screenshot: 截图绝对路径,或 ``.debug/images`` 下的图名(不带后缀)。

        Returns:
            (image, resolved_path):image 为 RGB ndarray,文件不存在/不可读时为 None。
        """
        if Path(screenshot).is_absolute():
            resolved = screenshot
        else:
            resolved = debug_utils.get_debug_image_path(screenshot)
        return cv2_utils.read_image(resolved), resolved

    def analyze(self, screenshot: str | None = None, save_image: bool = False,
                include_ocr: bool = False) -> AnalyzeScreenResult:
        """识别层客观回读:截图 + 画面匹配(精准/模糊)+ area 命中。

        screenshot 省略 → 截当前游戏画面(需游戏窗口就绪);精准命中回写
        ``ctx.screen_loader.update_current_screen_name``,为下次 BFS 提供起点。
        screenshot 传入 → 解析指定截图,**无需游戏窗口就绪**:绝对路径按路径读,
        纯名字到 ``.debug/images/<名字>.png`` 读;读不到返失败(error 带解析后完整路径)。
        **不回写**识别状态(离线 / 可能是旧图,不污染实时识别)。

        save_image=True(**仅实时模式生效**)→ 把截到的内存图落盘到
        ``.debug/sr_od_mcp/screenshot/``,路径写入 ``screenshot_path`` 返回,
        供调用方视觉判读复用(省掉第二次截图)。离线模式忽略(调用方本就有路径)。

        include_ocr=False(默认)→ ``ocr_texts`` 恒为空列表:全量散落 OCR 是
        无视觉时代的「替眼睛」输出,当前定位(对账:画面身份/坐标/结构化数据)
        下默认是噪音;读屏幕零散文字时由调用方显式开启。

        Args:
            screenshot: 截图绝对路径,或 ``.debug/images`` 下的图名(不带后缀);
                None 表示实时截当前画面。
            save_image: 实时模式下是否把截图落盘并回传路径(默认 False)。
            include_ocr: 是否返回全量散落 OCR 文本(默认 False)。

        Returns:
            分析结果:成功标志、OCR 文本列表(include_ocr=False 时为空)、
            画面匹配列表、错误描述、
            screenshot_path(本次新存的截图路径,实时+save_image=True 时有值)、
            vision_hint(成功时填的分工提示,失败时 None)。
        """
        self._ensure_ready()
        should_save: bool = save_image and screenshot is None
        saved_path: str | None = None
        if screenshot is None:
            controller = self._ctx.controller
            if controller is None or not controller.is_game_window_ready:
                return AnalyzeScreenResult(success=False, ocr_texts=[], screens=[], error='游戏窗口未就绪')
            image = controller.get_screenshot(independent=False)
            if image is None:
                return AnalyzeScreenResult(success=False, ocr_texts=[], screens=[], error='截图失败')
            # 打码 UID:对齐 controller.screenshot(),analyze 的 OCR / 画面匹配不依赖 UID 区域。
            image = controller.fill_uid_black(image)
            write_back = True
        else:
            image, resolved = self._resolve_screenshot(screenshot)
            if image is None:
                return AnalyzeScreenResult(success=False, ocr_texts=[], screens=[], error=f'读取截图失败: {resolved}')
            write_back = False
        try:
            if should_save:
                saved_path = _save_screenshot(image)  # 写盘失败抛错,由本 except 兜住
            # crop_first=False:与下方 find_screen_matches 内 find_area_with_detail(color_range=None)复用
            # 同一份全图 OCR 缓存(cache key 含 crop_first;True/False 不复用会触发两次全图 OCR)。
            # rect=None 时 crop_first 不影响 OCR 结果(都全图),只改 cache key。
            # 注意:全图 OCR 总是要跑(find_screen_matches 的文字 area 匹配依赖它),
            # include_ocr 只控制是否把散落文本回传给调用方。
            ocr_texts: list[OcrText] = []
            if include_ocr:
                ocr_result_list = self._ctx.ocr_service.get_ocr_result_list(image=image, crop_first=False)
                ocr_texts = [
                    OcrText(text=r.data, x=int(r.x), y=int(r.y), width=int(r.w), height=int(r.h))
                    for r in ocr_result_list
                ]
            screens = find_screen_matches(self._ctx, image)
            if write_back and screens and screens[0].is_precise:
                self._ctx.screen_loader.update_current_screen_name(screens[0].screen_name)

            # —— 精准命中 → 按画面查表跑额外识别器(无注册则 None,稳态零额外开销)——
            #    整个查表+调用都包在 try 里(含 get_recognizer 触发的惰性首扫):任一步异常 → extras=None,绝不中断 analyze。
            #    extras_doc(字段说明)在 recognize 调用前先取:识别器异常时 extras=None 但说明照常返回,调用方可对照排障。
            extras: dict | None = None
            extras_doc: dict[str, str] | None = None
            if screens and screens[0].is_precise:
                try:
                    recognizer = get_recognizer(self._ctx, screens[0].screen_name)   # 惰性首扫在此触发;扫描内部已 try/except 记 failures 不抛,但兜底防 rglob 等意外
                    if recognizer is not None:
                        extras_doc = getattr(recognizer, 'extras_doc', None) or None   # 声明为空 dict → None(稀疏返回)
                        screen_info = self._ctx.screen_loader.get_screen(screens[0].screen_name)   # 精准命中保证该画面已建档故能取到(非 Optional);理论边界异常由本 try 兜成 extras=None
                        extras = recognizer.recognize(self._ctx, image, screen_info)
                        if extras is not None:
                            json.dumps(extras)   # 提前校验 JSON 可序列化,违例走下面 except(extras=None),不让坏值漏到序列化层拖垮响应
                except Exception as e:  # noqa: BLE001 recognizer 异常(含扫描/读取/返回非 JSON 可序列化值)绝不中断 analyze
                    log.warning(f'recognizer[{screens[0].screen_name}] 异常: {e}')
                    extras = None

            return AnalyzeScreenResult(success=True, ocr_texts=ocr_texts, screens=screens, error=None,
                                       screenshot_path=saved_path, vision_hint=_VISION_HINT,
                                       extras=extras, extras_doc=extras_doc)
        except Exception as e:  # noqa: BLE001 OCR/匹配/存盘异常兜底:不回写,返失败(存盘已成功的仍回传路径排障)
            return AnalyzeScreenResult(success=False, ocr_texts=[], screens=[], error=str(e), screenshot_path=saved_path)

    def upsert_screen_area(
        self,
        screen_name: str,
        area_name: str,
        pc_rect: list[int],
        text: str = '',
        lcs_percent: float = 0.5,
        template_sub_dir: str = '',
        template_id: str = '',
        template_match_threshold: float = 0.7,
        color_range: list[list[int]] | None = None,
        goto_list: list[str] | None = None,
        id_mark: bool = False,
        gamepad_key: str | None = None,
    ) -> dict:
        """按 area_name 在指定 screen 插入或更新一个 area(写 yml + reload)。操作类。

        area_name 已存在 → 整体更新;不存在 → 追加。写回 screen_info yml 并重载,
        下次 analyze_screen 即生效。无需游戏窗口在线。

        Args:
            screen_name: 目标画面名(中文,对齐 get_screen / analyze 返回)。
            area_name: 区域名(同 screen 内唯一,作匹配键)。
            pc_rect: ``[x1, y1, x2, y2]``,1920×1080 内、x2>x1、y2>y1。
            text: 文本区域的 OCR 文本(空则非文本区)。
            lcs_percent: 文本匹配阈值。
            template_sub_dir / template_id: 模板引用;template_id 非空时模板必须存在,否则阻断。
            template_match_threshold: 模板匹配阈值。
            color_range: 文本颜色筛选 ``[[lower], [upper]]`` 或 None。
            goto_list: 交互后可能跳转的画面名列表。
            id_mark: 是否画面唯一标识。
            gamepad_key: 手柄动作名。

        Returns:
            ``{success, screen_name, area_name, action(inserted/updated), area_count, error}``。
        """
        try:
            if not area_name:
                return _area_result(False, screen_name, area_name, None, error='area_name 不能为空')
            rect_msg = _validate_pc_rect(pc_rect)
            if rect_msg is not None:
                return _area_result(False, screen_name, area_name, None, error=rect_msg)
            if template_id and self._ctx.template_loader.load_template(template_sub_dir, template_id) is None:
                return _area_result(False, screen_name, area_name, None,
                                    error=f'模板不存在: {template_sub_dir}/{template_id}')
            # goto_list 是画面路由图的边(填错要到运行时 round_by_goto_screen 才 log.error),
            # 建档时就在这里拦下,并列出既有画面名供修正。
            known_screen_names = {s.screen_name for s in self._ctx.screen_loader.screen_info_list}
            bad_goto = [g for g in (goto_list or []) if g not in known_screen_names]
            if bad_goto:
                sample = '、'.join(sorted(known_screen_names)[:10])
                return _area_result(False, screen_name, area_name, None,
                                    error=f'goto_list 目标画面不存在: {bad_goto}(画面名须与 screen_info 的 screen_name 完全一致;示例: {sample} …可用 list_screen_names 工具查全量)')
            area = ScreenArea(
                area_name=area_name,
                pc_rect=Rect(int(pc_rect[0]), int(pc_rect[1]), int(pc_rect[2]), int(pc_rect[3])),
                text=text, lcs_percent=lcs_percent,
                template_id=template_id, template_sub_dir=template_sub_dir,
                template_match_threshold=template_match_threshold,
                color_range=color_range, goto_list=goto_list or [],
                id_mark=id_mark, gamepad_key=gamepad_key,
            )
            screen_info = self._ctx.screen_loader.get_screen(screen_name)  # 未找到 raise
            action = screen_info.upsert_area(area)
            self._ctx.screen_loader.save_screen(screen_info)
            return _area_result(True, screen_name, area_name, action, count=len(screen_info.area_list))
        except Exception as e:  # noqa: BLE001 工具层兜底,不向 MCP 透传
            return _area_result(False, screen_name, area_name, None, error=str(e),
                                count=self._safe_area_count(screen_name))

    def delete_screen_area(self, screen_name: str, area_name: str) -> dict:
        """按 area_name 删除指定 screen 的一个 area(写 yml + reload)。操作类。

        Args:
            screen_name: 目标画面名。
            area_name: 要删除的区域名;不存在则报错。

        Returns:
            ``{success, screen_name, area_name, action(deleted), area_count, error}``。
        """
        try:
            if not area_name:
                return _area_result(False, screen_name, area_name, None, error='area_name 不能为空')
            screen_info = self._ctx.screen_loader.get_screen(screen_name)  # 未找到 raise
            if not screen_info.remove_area_by_name(area_name):
                return _area_result(False, screen_name, area_name, None,
                                    error=f'未找到 area: {area_name}', count=len(screen_info.area_list))
            self._ctx.screen_loader.save_screen(screen_info)
            return _area_result(True, screen_name, area_name, 'deleted', count=len(screen_info.area_list))
        except Exception as e:  # noqa: BLE001 工具层兜底
            return _area_result(False, screen_name, area_name, None, error=str(e),
                                count=self._safe_area_count(screen_name))

    def create_screen(self, screen_id: str, screen_name: str, app_id: str = '', pc_alt: bool = False) -> dict:
        """创建一个新画面(空 area_list;写 yml + reload)。操作类。

        screen_id 不与既有冲突、screen_name 唯一。创建后用 ``upsert_screen_area`` 加 area。
        无需游戏在线。

        Args:
            screen_id: 画面 ID(英文 snake_case,作 yml 文件名;如 currency_war_lobby)。
            screen_name: 画面名(中文,作 get_screen / analyze 的 key;如 货币战争-大厅)。
            app_id: 所属应用 ID(空 = 全局 screen)。
            pc_alt: PC 端点击是否需 Alt。

        Returns:
            ``{success, screen_id, screen_name, action(created), error}``。
        """
        try:
            if not screen_id or not screen_name:
                return {'success': False, 'screen_id': screen_id, 'screen_name': screen_name,
                        'action': None, 'error': 'screen_id / screen_name 不能为空'}
            loader = self._ctx.screen_loader
            if screen_id in loader._id_2_screen:
                return {'success': False, 'screen_id': screen_id, 'screen_name': screen_name,
                        'action': None, 'error': f'screen_id 已存在: {screen_id}'}
            if screen_name in loader.screen_info_map:
                return {'success': False, 'screen_id': screen_id, 'screen_name': screen_name,
                        'action': None, 'error': f'screen_name 已存在: {screen_name}'}
            screen_info = ScreenInfo({
                'screen_id': screen_id, 'screen_name': screen_name,
                'app_id': app_id, 'pc_alt': pc_alt, 'area_list': [],
            })
            loader.save_screen(screen_info)
            return {'success': True, 'screen_id': screen_id, 'screen_name': screen_name,
                    'action': 'created', 'error': None}
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'success': False, 'screen_id': screen_id, 'screen_name': screen_name,
                    'action': None, 'error': str(e)}

    def list_screen_names(self) -> dict:
        """列出全部画面名(只读,无副作用)。

        供 goto_list 填写与 goto_screen 目标选择时查全量;screen_name 是
        screen_info 的匹配键(中文),须完全一致。

        Returns:
            ``{success, count, screen_names(排序后全量), error}``。
        """
        try:
            names = sorted(s.screen_name for s in self._ctx.screen_loader.screen_info_list)
            return {'success': True, 'count': len(names), 'screen_names': names, 'error': None}
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'success': False, 'count': 0, 'screen_names': [], 'error': str(e)}

    def get_screen_detail(self, screen_name: str) -> dict:
        """读取单个画面档全集(只读):全部 area 含 goto_list,加路由图可达邻居。

        analyze_screen 只回当前帧命中;本方法回建档全集 —— agent 建档/核对
        screen_info 与查「从这里能 goto 到哪」用。

        Args:
            screen_name: 目标画面名(与 screen_info 的 screen_name 完全一致)。

        Returns:
            ``{success, screen_name, screen_id, pc_alt, area_count, areas[], goto_neighbors[], error}``;
            areas 元素含 area_name/id_mark/pc_rect/text/lcs_percent/template_id/
            template_sub_dir/template_match_threshold/goto_list。
        """
        try:
            screen_info = self._ctx.screen_loader.get_screen(screen_name)  # 未找到 raise
            areas = [
                {
                    'area_name': a.area_name,
                    'id_mark': a.id_mark,
                    'pc_rect': [a.rect.x1, a.rect.y1, a.rect.x2, a.rect.y2],
                    'text': a.text,
                    'lcs_percent': a.lcs_percent,
                    'template_id': a.template_id,
                    'template_sub_dir': a.template_sub_dir,
                    'template_match_threshold': a.template_match_threshold,
                    'goto_list': list(a.goto_list),
                }
                for a in screen_info.area_list
            ]
            route_map = self._ctx.screen_loader.screen_route_map.get(screen_name, {})
            neighbors = sorted(
                to for to, route in route_map.items()
                if to != screen_name and route is not None and route.can_go
            )
            return {
                'success': True, 'screen_name': screen_name,
                'screen_id': screen_info.screen_id, 'pc_alt': screen_info.pc_alt,
                'area_count': len(areas), 'areas': areas,
                'goto_neighbors': neighbors, 'error': None,
            }
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'success': False, 'screen_name': screen_name, 'screen_id': None,
                    'pc_alt': None, 'area_count': 0, 'areas': [], 'goto_neighbors': [],
                    'error': str(e)}

    def _find_area_click_point(self, screen: 'MatLike', screen_info: ScreenInfo,
                               area: ScreenArea) -> Point | None:
        """在截图内定位 area 的可点击点;找不到返 None。

        与 screen_utils.find_and_click_area 同匹配逻辑,差异:pc_alt 取
        ``area.pc_alt or screen_info.pc_alt`` —— 锁光标画面(如大世界)的
        area 通常不单设 pc_alt,只按 area 判会落空。
        纯定位区(无 text 无 template)直接回 area.center。
        """
        if area.is_text_area:
            ocr_result_list = self._ctx.ocr_service.get_ocr_result_list(
                image=screen, rect=area.rect, color_range=area.color_range)
            for ocr_result in ocr_result_list:
                if str_utils.find_by_lcs(gt(area.text, 'game'), ocr_result.data,
                                         percent=area.lcs_percent):
                    return ocr_result.center
            return None
        if area.is_template_area:
            mrl = self._ctx.tm.crop_and_match_template(
                screen, area.rect, area.template_sub_dir, area.template_id,
                threshold=area.template_match_threshold)
            if mrl.max is None:
                return None
            return mrl.max.center + area.rect.left_top
        return area.center

    def goto_screen(self, target_screen_name: str, max_steps: int = 10) -> dict:
        """沿建档 goto_list 路由导航到目标画面。操作类(会实际点击游戏)。

        复用 op 层 round_by_goto_screen 的同一套路由图(screen_loaderFloyd
        预计算),供 MCP agent 手工导航用,不再逐步 click_game 造轮子。
        边界:路由取决于画面档 goto_list 的完整度 —— 报「无路径」= 两画面间
        的跳转边未建档,补 area 的 goto_list 而非硬试坐标。每步点击后等
        1.5s 转场再识别(同 op 层 success_wait 口径)。

        Args:
            target_screen_name: 目标画面名(与 screen_info 的 screen_name 一致)。
            max_steps: 最多点击次数(防路由环/坏边打转)。

        Returns:
            ``{success, current_screen, target_screen, steps[每步 <画面>--<area>--><画面>], error}``。
        """
        self._ensure_ready()
        if self._ctx.controller is None or not self._ctx.controller.is_game_window_ready:
            raise BackendNotReadyError('游戏窗口未就绪')
        known = {s.screen_name for s in self._ctx.screen_loader.screen_info_list}
        if target_screen_name not in known:
            return {'success': False, 'current_screen': None, 'target_screen': target_screen_name,
                    'steps': [], 'error': f'目标画面不存在: {target_screen_name}(用 list_screen_names 查全量)'}
        steps: list[str] = []
        current: str | None = None
        try:
            for _ in range(max(1, max_steps)):
                # 对齐 analyze:controller.get_screenshot 返 ndarray;
                # controller.screenshot() 返 (image, 时间) 元组,不能直接喂识别。
                image = self._ctx.controller.get_screenshot(independent=False)
                if image is None:
                    return {'success': False, 'current_screen': current, 'target_screen': target_screen_name,
                            'steps': steps, 'error': '截图失败'}
                current = screen_utils.get_match_screen_name(self._ctx, image)
                if current is None:
                    return {'success': False, 'current_screen': None, 'target_screen': target_screen_name,
                            'steps': steps, 'error': '当前画面无法识别(过渡帧或未建档),稍后重试或先 analyze_screen 判现状'}
                self._ctx.screen_loader.update_current_screen_name(current)
                if current == target_screen_name:
                    return {'success': True, 'current_screen': current, 'target_screen': target_screen_name,
                            'steps': steps, 'error': None}
                route = self._ctx.screen_loader.get_screen_route(current, target_screen_name)
                if route is None or not route.can_go or not route.node_list:
                    return {'success': False, 'current_screen': current, 'target_screen': target_screen_name,
                            'steps': steps,
                            'error': f'路由图中无 {current} -> {target_screen_name} 的路径(画面档 goto_list 未建档)'}
                node = route.node_list[0]
                screen_info = self._ctx.screen_loader.get_screen(current)
                area = self._ctx.screen_loader.get_area(current, node.from_area)
                to_click = self._find_area_click_point(image, screen_info, area)
                if to_click is None:
                    return {'success': False, 'current_screen': current, 'target_screen': target_screen_name,
                            'steps': steps,
                            'error': f'画面 {current} 与建档不符:area {node.from_area} 未命中(画面可能已流转,重试或 analyze_screen 核对)'}
                if not self._ctx.controller.click(to_click, pc_alt=area.pc_alt or screen_info.pc_alt):
                    return {'success': False, 'current_screen': current, 'target_screen': target_screen_name,
                            'steps': steps, 'error': f'点击 {current}/{node.from_area} 失败'}
                steps.append(f'{current} --{node.from_area}--> {node.to_screen}')
                self._ctx.screen_loader.update_current_screen_name(node.to_screen)
                time.sleep(1.5)  # 等转场动画,下一轮截图再识别(同 op 层 success_wait 口径)
            return {'success': False, 'current_screen': current, 'target_screen': target_screen_name,
                    'steps': steps, 'error': f'超过 max_steps={max_steps} 步未到达 {target_screen_name}(路由可能成环)'}
        except StopRunInterrupted:
            # 停机守卫穿透(异常为 BaseException,泛型 except Exception 接不住):
            # run 收口期调用 goto_screen 属被拦场景,按本工具的错误契约返回
            # 结构化失败,不把异常漏给 MCP 请求层。
            return {'success': False, 'current_screen': current, 'target_screen': target_screen_name,
                    'steps': steps, 'error': '运行已被停机中断(守卫拦截本次导航点击)'}
        except Exception as e:  # noqa: BLE001 工具层兜底
            return {'success': False, 'current_screen': current, 'target_screen': target_screen_name,
                    'steps': steps, 'error': str(e)}

    def _safe_area_count(self, screen_name: str) -> int | None:
        """异常路径下尽量取 area 数(取不到返 None,不再抛)。"""
        try:
            return len(self._ctx.screen_loader.get_screen(screen_name).area_list)
        except Exception:  # noqa: BLE001
            return None

    def close_game(self) -> str:
        """关闭游戏(发关闭窗口信号,秒级,不走运行槽)。

        controller.close_game() 内部 try/except 吞异常(log)、不返成功标志,
        故无法区分关成功/失败 —— 返「已发送关闭信号」,用 check_game_window 验证。

        Returns:
            '已发送关闭游戏信号,可用 check_game_window 验证'。

        Raises:
            BackendNotReadyError: SrContext 未就绪或游戏窗口未就绪时抛。
        """
        self._ensure_ready()
        controller = self._ctx.controller
        if controller is None or not controller.is_game_window_ready:
            raise BackendNotReadyError('游戏窗口未就绪')
        controller.close_game()
        return '已发送关闭游戏信号,可用 check_game_window 验证'

    def click_game(self, x: int | float, y: int | float, press_time: float = 0.1, pc_alt: bool = False) -> dict:
        """点击游戏窗口内指定坐标(1080p 游戏空间,同源 screen_info pc_rect)。操作类。

        坐标经控制器自动缩放到真实屏幕。坐标不在游戏窗口内时控制器返 False(不点击)。

        Args:
            x, y: 默认分辨率(1920×1080)下的游戏窗口坐标。
            press_time: >0 时长按若干秒。
            pc_alt: 点击前是否先按住 Alt 解锁光标。大世界等 ``pc_alt=true`` 画面必需
                (星穹铁道会锁光标,不按 Alt 点击落空);其余画面保持 False。

        Returns:
            ``{success, x, y, in_window, pc_alt}``:``success/in_window=False`` 表示坐标不在窗口内。

        Raises:
            BackendNotReadyError: SrContext 未就绪或游戏窗口未就绪时抛。
        """
        self._ensure_ready()
        controller = self._ctx.controller
        if controller is None or not controller.is_game_window_ready:
            raise BackendNotReadyError('游戏窗口未就绪')
        # 手动入口 = 停机后的显式外部接管:本地豁免不清全局停机闩(ADR-0406,
        # 旧 consume 清闩会在 run 收口期摘守卫放幽灵输入)。豁免按线程隔离,
        # unwind 中的 run 线程输入仍被守卫拦截。
        with stop_guard_exemption():
            controller.active_window()
            clicked = controller.click(Point(int(x), int(y)), press_time=press_time, pc_alt=pc_alt)
        return {'success': clicked, 'x': int(x), 'y': int(y), 'in_window': clicked, 'pc_alt': pc_alt}

    def key_tap(self, key: str, press_time: float = 0.0) -> dict:
        """键盘按键:``press_time=0`` 短按(tap),``press_time>0`` 长按(press→保持→release)。操作类。

        覆盖框架 ``btn_controller`` 能发的键:移动 ``w``/``a``/``s``/``d``、交互 ``f``、
        ``esc``、``space`` 等。键名沿用框架约定。需游戏窗口就绪。

        Args:
            key: 按键名(如 ``'w'``/``'f'``/``'esc'``/``'space'``)。
            press_time: >0 时长按若干秒(如移动长按 1-2s);=0 短按。

        Returns:
            ``{success, key, press_time}``。

        Raises:
            BackendNotReadyError: SrContext / 游戏窗口未就绪时抛。
        """
        self._ensure_ready()
        controller = self._ctx.controller
        if controller is None or not controller.is_game_window_ready:
            raise BackendNotReadyError('游戏窗口未就绪')
        with stop_guard_exemption():  # 手动接管本地豁免,不清全局停机闩(ADR-0406)
            controller.active_window()
            if press_time > 0:
                # 走公开入口 btn_press(带停机守卫与后台模式处理),不直按 btn_controller
                controller.btn_press(key, press_time=press_time)
            else:
                controller.btn_tap(key)
        return {'success': True, 'key': key, 'press_time': press_time}

    def drag(self, x1: int | float, y1: int | float, x2: int | float, y2: int | float, duration: float = 1.0) -> dict:
        """鼠标按住拖拽:从 (x1,y1) 拖到 (x2,y2),持续 duration 秒。操作类。

        1080p 游戏空间坐标(同 screen_info ``pc_rect``)。覆盖刮刮卡刮开、八卦收集
        来回拖、咖啡拖动等。需游戏窗口就绪。

        Args:
            x1, y1: 起点坐标(1920×1080)。
            x2, y2: 终点坐标。
            duration: 拖拽持续秒数(默认 1.0)。

        Returns:
            ``{success, x1, y1, x2, y2, duration}``。

        Raises:
            BackendNotReadyError: SrContext / 游戏窗口未就绪时抛。
        """
        self._ensure_ready()
        controller = self._ctx.controller
        if controller is None or not controller.is_game_window_ready:
            raise BackendNotReadyError('游戏窗口未就绪')
        with stop_guard_exemption():  # 手动接管本地豁免,不清全局停机闩(ADR-0406)
            controller.active_window()
            controller.drag_to(Point(int(x2), int(y2)), start=Point(int(x1), int(y1)), duration=duration)
        return {'success': True, 'x1': int(x1), 'y1': int(y1), 'x2': int(x2), 'y2': int(y2), 'duration': duration}

    def input_text(self, text: str, use_clipboard: bool | None = None) -> dict:
        """向当前焦点输入框输入文本(账号/密码等)。操作类。

        use_clipboard=None → 跟随 ``game_config.type_input_way``(同 ``EnterGame``);
        True/False → 强制剪贴板/逐键。输入前激活游戏窗口(键盘注入 / Ctrl+V 均需前台焦点)。

        Args:
            text: 要输入的文本。
            use_clipboard: True=剪贴板(copy_and_paste,支持中文/特殊字符);
                False=逐键(controller.input_str);None=跟随全局配置。

        Returns:
            ``{success, method, masked_text}``:method ∈ {'clipboard','keyboard'};
            masked_text 为脱敏文本。

        Raises:
            BackendNotReadyError: SrContext 未就绪或游戏窗口未就绪时抛。
        """
        self._ensure_ready()
        controller = self._ctx.controller
        if controller is None or not controller.is_game_window_ready:
            raise BackendNotReadyError('游戏窗口未就绪')
        with stop_guard_exemption():  # 手动接管本地豁免,不清全局停机闩(ADR-0406)
            use_cb = self._resolve_use_clipboard(use_clipboard)
            controller.active_window()
            if use_cb:
                PcClipboard.copy_and_paste(text)
                method = 'clipboard'
            else:
                controller.input_str(text)
                method = 'keyboard'
        return {'success': True, 'method': method, 'masked_text': mask_text(text)}

    def _resolve_use_clipboard(self, use_clipboard: bool | None) -> bool:
        """解析输入方式:非 None 原样返回;None 读 game_config.type_input_way(== CLIPBOARD 则 True)。"""
        if use_clipboard is not None:
            return use_clipboard
        return self._ctx.game_config.type_input_way == TypeInputWay.CLIPBOARD.value.value

    def start_run(
        self,
        source: str,
        op_factory: 'Callable[[SrContext], Operation]',
        display_name: str | None = None,
    ) -> tuple[bool, Future | None]:
        """触发运行(op 原语入口,供 open_game 等经适配器调用)。

        单跑道委托 ``run_slot._start``(op 路径):已有运行在进行时返回 ``ok=False``，
        适配器据此返回并发拒绝；其余由 RunSlot 在后台线程内执行 operation。
        单跑道互斥由 ``run_slot._start`` 锁内 check-then-submit 原子保证。

        Args:
            source: 触发方标识，如 ``"mcp"``/``"http"``。
            op_factory: operation 构造器，由适配器提供。
            display_name: op 路径定位标识(如 op_id);None 时 _run 内 fallback 类名。

        Returns:
            ``(ok, future)``：``ok=False`` 表示已有运行在进行(``future=None``)；
            ``ok=True`` 表示已启动，``future`` 可供阻塞 await 取结果。
        """
        return self.run_slot._start(source, op_factory=op_factory, display_name=display_name)

    def run_one_dragon(self, source: str) -> tuple[bool, Future | None]:
        """按当前一条龙配置启动完整一条龙运行(app 路径,经 ``_start_app``)。"""
        self._ensure_ready()
        return self._start_app(source, application_const.ONE_DRAGON_APP_ID, application_const.DEFAULT_GROUP_ID)

    def run_standalone_app(self, source: str, app_id: str | None = None) -> tuple[bool, Future | None]:
        """启动独立应用；app_id 为空时使用 GUI 当前选中的独立应用(app 路径,经 ``_start_app``)。"""
        self._ensure_ready()
        target_app_id = app_id or self._ctx.standalone_app_config.active_app_id
        if not target_app_id:
            raise BackendNotReadyError('未选择独立应用')
        return self._start_app(source, target_app_id, application_const.DEFAULT_GROUP_ID)

    def _start_app(self, source: str, app_id: str, group_id: str) -> tuple[bool, Future | None]:
        """app 路径统一入口:委托 ``run_slot._start`` 的 app 分派。

        ``refresh_config`` 作为钩子注入槽线程:仅在 ``_start`` 赢锁后、``run_application``
        前执行(拒绝路径不进 ``_run``,不刷新),修原 ``run_one_dragon``/``run_standalone_app``
        的刷新竞态;``instance_idx`` 由 ``_run`` 在刷新后重读(可能切实例)。

        Args:
            source: 触发方标识。
            app_id: 应用 id(同时作唯一标识 op_id)。
            group_id: 应用组 id。

        Returns:
            ``(ok, future)``:``ok=False`` 表示单跑道已有运行在跑。
        """
        return self.run_slot._start(
            source, app_id=app_id, group_id=group_id,
            instance_idx=self._ctx.current_instance_idx,
            refresh_config=self._refresh_runtime_config,
        )

    def list_applications(self) -> ApplicationListResult:
        """列出当前实例可运行应用和独立应用选择状态(只读路径,不刷新配置)。"""
        self._ensure_ready()
        active_standalone_app_id = self._ctx.standalone_app_config.active_app_id
        standalone_app_ids = set(self._ctx.standalone_app_config.app_list)
        group_config = self._ctx.app_group_manager.get_one_dragon_group_config(self._ctx.current_instance_idx)
        enabled_map = {item.app_id: item.enabled for item in group_config.app_list}

        # 展示顺序与运行语义一致：先固定一条龙入口，再追加默认组注册的独立应用。
        app_ids: list[str] = []
        if self._ctx.run_context.is_app_registered(application_const.ONE_DRAGON_APP_ID):
            app_ids.append(application_const.ONE_DRAGON_APP_ID)
        for app_id in self._ctx.run_context.default_group_apps:
            if app_id not in app_ids:
                app_ids.append(app_id)

        applications: list[ApplicationInfo] = []
        for app_id in app_ids:
            try:
                app_name = self._ctx.run_context.get_application_name(app_id)
            except Exception:  # noqa: BLE001 应用列表用于展示，跳过异常名称
                app_name = app_id
            applications.append(ApplicationInfo(
                app_id=app_id,
                app_name=app_name,
                enabled_in_one_dragon=enabled_map.get(app_id, False),
                in_standalone_list=app_id in standalone_app_ids,
                is_active_standalone=app_id == active_standalone_app_id,
            ))
        return ApplicationListResult(
            current_instance_idx=self._ctx.current_instance_idx,
            active_standalone_app_id=active_standalone_app_id,
            applications=applications,
        )

    def query_status(self) -> RunStatusResult:
        """查询当前或最近一次运行状态(单槽,直接委托)。"""
        return self.run_slot._query_status()

    def run_refusal_response(self, hint: str) -> dict:
        """start 类入口被拒(``_start`` 返回 ok=False)时的统一拒绝响应。

        error 优先取 ``run_slot.last_refusal_reason``:跨进程窗口占用与本进程
        已有 run 必须可区分(2026-08-24 双进程交替操作事故的排查教训——笼统的
        「已有运行在进行中」会把 agent 的处置引向错误进程)。

        Args:
            hint: 各入口按自身协议给出的下一步提示(如 MCP 查 get_run_status)。

        Returns:
            ``{started: False, error, source, hint}``;source 为当前/最近运行触发方。
        """
        st = self.query_status()
        # isinstance 防御:测试替身的 run_slot 常是 MagicMock,非 str 原因回落历史文案。
        reason = self.run_slot.last_refusal_reason
        error = reason if isinstance(reason, str) and reason else '已有运行在进行中'
        return {
            'started': False,
            'error': error,
            'source': st.source,
            'hint': hint,
        }

    def stop(self) -> dict:
        """停止当前运行(单槽)。无运行时返回 ``{stopped: False, error}``。"""
        stopped, source = self.run_slot._stop()
        if stopped:
            return {'stopped': True, 'source': source}
        return {'stopped': False, 'error': '当前无运行'}

    async def start(self) -> None:
        """启动服务：在线程池中初始化 ``SrContext``，不阻塞事件循环。

        ``SrContext.init()`` 是同步且可能较重的初始化流程（含 OCR/onnx 模型加载、
        控制器构建等）。通过 ``asyncio.to_thread`` 将其放到默认线程池执行，
        保证事件循环可继续调度其它协程。

        注意：
            ``ctx.init_async()`` 返回 None（fire-and-forget），不可 await；
            要等待初始化真正完成，必须使用 ``asyncio.to_thread(ctx.init)``。
        """
        await asyncio.to_thread(self._ctx.init)

    async def shutdown(self) -> None:
        """关闭服务：在线程池中释放 ``SrContext`` 持有的资源。

        ``SrContext.after_app_shutdown()`` 是同步的清理流程（遥测、战斗上下文、
        框架服务等），同样通过 ``asyncio.to_thread`` 避免阻塞事件循环。
        并关闭 ``RunSlot`` 的单跑道线程池,释放其后台线程。
        """
        self.run_slot.shutdown()
        await asyncio.to_thread(self._ctx.after_app_shutdown)
