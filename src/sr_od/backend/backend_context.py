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
from one_dragon.base.operation.application import application_const
from one_dragon.base.operation.application.application_run_context import (
    RunFinishReason,
)
from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.screen.screen_area import ScreenArea
from one_dragon.base.screen.screen_info import ScreenInfo
from one_dragon.base.screen.screen_match import find_screen_matches
from one_dragon.utils import cv2_utils, debug_utils, os_utils
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
    '本结果仅包含 OCR 识别的文字与模板匹配的命中项,是画面的部分识别结果,'
    '不等同于对画面的完整视觉理解。需要全面判断画面时,请用视觉工具或多模态大模型再看一遍该画面。'
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
                return False, None                         # 单跑道:已在跑就拒(拒绝路径不刷新配置)
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

        ffmpeg gdigrab 采集 + h264_nvenc(NVIDIA GPU)硬编码,跑在本 server 进程
        (Session 1 / 交互桌面),故能录到游戏画面 —— 从 SSH / 服务会话(Session 0)直跑
        ffmpeg 会 BitBlt ACCESS_DENIED,录不到交互桌面,这是录屏放 backend 的根本原因。

        Args:
            mode: 'fixed'(默认)= 录 ``duration`` 秒后 ffmpeg 自停(-t,正常写 moov,mp4 干净),
                阻塞返回; 'start'= 后台开始(返回 pid),之后调 ``mode='stop'`` 收尾
                (用 fragmented mp4,kill 也安全可播); 'stop'= 停止进行中的录屏。
            duration: fixed 模式录制秒数。
            out_name: 输出文件名(可带可不带 .mp4),存 ``.debug/record/``。
            fps: 帧率。
            capture: 'window'= 按游戏窗口标题(游戏不在则退回 desktop);'desktop'= 全桌面。
            bitrate: 目标码率,如 ``6M``。

        Returns:
            ``{success, path?, pid?, action, error?, hint?}``。无 ffmpeg 时 success=False +
            error 提示装 dev 依赖(imageio-ffmpeg)。imageio-ffmpeg 为延迟导入,缺失不影响 server 启动。
        """
        def _resolve_ffmpeg() -> str | None:
            """延迟解析 ffmpeg 路径(imageio_ffmpeg → PATH),缺失返回 None(不影响启动)。"""
            try:
                import imageio_ffmpeg
                return imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                import shutil
                return shutil.which('ffmpeg')

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
                return {'success': True, 'path': out, 'action': 'stopped'}

            ffexe = _resolve_ffmpeg()
            if not ffexe:
                return {
                    'success': False,
                    'error': '未找到 ffmpeg。录屏是 dev-only,需 dev 依赖 imageio-ffmpeg',
                    'hint': '确认已 uv sync --group dev;或把 ffmpeg 放到 PATH',
                }

            out_dir = Path('.debug/record')
            out_dir.mkdir(parents=True, exist_ok=True)
            if not out_name.lower().endswith('.mp4'):
                out_name = out_name + '.mp4'
            out_path = str((out_dir / out_name).resolve())

            input_arg = 'desktop'
            if capture == 'window':
                try:
                    title = self._ctx.controller.game_win.win_title
                    if title:
                        input_arg = f'title={title}'
                except Exception:
                    input_arg = 'desktop'

            cmd = [ffexe, '-hide_banner', '-loglevel', 'error',
                   '-f', 'gdigrab', '-framerate', str(fps), '-draw_mouse', '1',
                   '-i', input_arg,
                   '-c:v', 'h264_nvenc', '-preset', 'fast', '-b:v', bitrate,
                   '-pix_fmt', 'yuv420p']
            if mode == 'fixed':
                cmd += ['-t', str(duration)]
            else:  # start → fragmented mp4,被 kill 也安全可播
                cmd += ['-movflags', '+frag_keyframe+emptymoov+default_base_moof']
            cmd += [out_path, '-y']

            try:
                proc = subprocess.Popen(cmd)
            except Exception as e:
                return {'success': False, 'error': f'启动 ffmpeg 失败: {e}'}

            if mode == 'fixed':
                try:
                    proc.wait(timeout=duration + 10)
                    ok = proc.returncode == 0
                except subprocess.TimeoutExpired:
                    proc.kill()
                    ok = False
                return {'success': ok, 'path': out_path if ok else None,
                        'action': 'fixed', 'returncode': proc.returncode}
            elif mode == 'start':
                self._recorder_proc = proc
                self._recorder_path = out_path
                return {'success': True, 'pid': proc.pid, 'path': out_path, 'action': 'started',
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

    def analyze(self, screenshot: str | None = None, save_image: bool = False) -> AnalyzeScreenResult:
        """分析画面:截图 + 全图 OCR + 画面匹配(精准/模糊)。

        screenshot 省略 → 截当前游戏画面(需游戏窗口就绪);精准命中回写
        ``ctx.screen_loader.update_current_screen_name``,为下次 BFS 提供起点。
        screenshot 传入 → 解析指定截图,**无需游戏窗口就绪**:绝对路径按路径读,
        纯名字到 ``.debug/images/<名字>.png`` 读;读不到返失败(error 带解析后完整路径)。
        **不回写**识别状态(离线 / 可能是旧图,不污染实时识别)。

        save_image=True(**仅实时模式生效**)→ 把截到的内存图落盘到
        ``.debug/sr_od_mcp/screenshot/``,路径写入 ``screenshot_path`` 返回,
        供调用方喂给 vision 复用(省掉第二次截图)。离线模式忽略(调用方本就有路径)。

        Args:
            screenshot: 截图绝对路径,或 ``.debug/images`` 下的图名(不带后缀);
                None 表示实时截当前画面。
            save_image: 实时模式下是否把截图落盘并回传路径(默认 False)。

        Returns:
            分析结果:成功标志、OCR 文本列表、画面匹配列表、错误描述、
            screenshot_path(本次新存的截图路径,实时+save_image=True 时有值)、
            vision_hint(成功时填的能力边界提示,失败时 None)。
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
