"""后端服务层：传输无关地包装 SrContext，提供感知/操作方法。

本模块是后端 game 切片的地基：
- ``SrBackendContext`` 持有 ``SrContext``，管理其生命周期，并对外暴露与
  传输协议（HTTP/IPC 等）无关的感知/操作方法。
- ``BackendNotReadyError`` 在前置校验失败（SrContext 尚未就绪）时抛出。

game 切片方法（``check_window``/``capture``/``analyze``）从
``SrContext`` 的控制器、OCR 服务、运行上下文中读取数据，并以 ``sr_od.backend.schemas``
中的传输无关结构返回。运行类操作通过 ``start_run``/``query_status``/``stop``
委托给 ``run_slot``(RunSlot)。
"""

import asyncio
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
from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.screen.screen_area import ScreenArea
from one_dragon.base.screen.screen_match import find_screen_matches
from one_dragon.utils import cv2_utils, debug_utils
from one_dragon.utils.log_utils import mask_text
from sr_od.backend.schemas import (
    AnalyzeScreenResult,
    OcrText,
    RunStatusResult,
    WindowStatus,
)
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.operation.operation import Operation


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
    """RunSlot 状态。

    IDLE:从未运行;RUNNING:operation 活(含 stop 后退出中的间隙,统一报 RUNNING);
    SUCCESS/FAILED/STOPPED:终态(固化)。无 PAUSED(当前不可达)、无 STOPPING(框架无此态)。
    """

    IDLE = 'idle'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    STOPPED = 'stopped'


class RunSlot:
    """单跑道运行槽:MCP/HTTP 共享,固化终态,运行中读 operation 实例。

    状态判据用固化字段 terminal_state(单一事实源),不读 run_context 推中间态。
    详见 docs/superpowers/specs/2026-07-05-mcp-run-state-design.md。
    """

    def __init__(self, ctx: 'SrContext') -> None:
        self._ctx: SrContext = ctx
        self._lock: threading.Lock = threading.Lock()
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='sr_backend_run')
        self.source: str | None = None
        self.app: str | None = None
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.terminal_state: RunState | None = None
        self.last_status: str | None = None
        self.failed_node: str | None = None
        self.future: Future | None = None
        self.current_op: Operation | None = None

    def _start_run(self, source: str, op_factory: 'Callable[[SrContext], Operation]') -> tuple[bool, Future | None]:
        """触发运行。单跑道:已在跑则拒绝。

        Returns:
            (ok, future):ok=False 表示已有运行在进行(future=None);ok=True 表示已启动。
        """
        with self._lock:
            if self.future is not None and not self.future.done():
                return False, None
            self.terminal_state = None
            self.last_status = None
            self.failed_node = None
            self.finished_at = None
            self.app = None
            self.source = source
            self.started_at = time.time()
            self.future = self._executor.submit(self._run, op_factory)
            return True, self.future

    def _run(self, op_factory: 'Callable[[SrContext], Operation]') -> OperationResult | None:
        """后台线程:启动 run_context → 跑 operation → finally 固化终态 + stop_running。

        并发(已在跑)已在 _start_run 拦截;此处 start_running 返回 False 只可能是初始化失败。
        终态判据:OperationResult.status == '人工结束' → STOPPED(框架唯一 stop 标记)。
        返回 OperationResult(future 解析值)供 block=True 的适配器 await 后取结果。
        """
        run_context = self._ctx.run_context
        op: Operation | None = None
        result: OperationResult | None = None
        terminal: RunState = RunState.FAILED
        failed_node: str | None = None   # 局部累积,finally 锁内固化(避免锁外写固化字段)
        try:
            if not run_context.start_running():
                failed_node = 'start_running 初始化失败'
                result = OperationResult(success=False, status='start_running 初始化失败')
            else:
                run_context.current_instance_idx = self._ctx.current_instance_idx
                op = op_factory(self._ctx)
                with self._lock:
                    self.current_op = op
                    self.app = op.__class__.__name__
                result = op.execute()
                if result.success:
                    terminal = RunState.SUCCESS
                elif result.status == '人工结束':
                    terminal = RunState.STOPPED
                else:
                    terminal = RunState.FAILED
                    failed_node = op._current_node.cn if op._current_node is not None else None
        except Exception as e:  # noqa: BLE001 兜底:execute 抛异常也固化,避免卡 terminal_state=None
            terminal = RunState.FAILED
            if op is not None and op._current_node is not None:
                failed_node = op._current_node.cn
            else:
                failed_node = f'异常: {e}'
            result = OperationResult(success=False, status='执行异常')
        finally:
            with self._lock:
                self.terminal_state = terminal
                self.last_status = result.status if result is not None else '执行异常'
                self.failed_node = failed_node
                self.finished_at = time.time()
                self.current_op = None
            run_context.stop_running()
        return result

    def _query_status(self) -> RunStatusResult:
        """查询运行状态。判据用固化 terminal_state(单一事实源),不读 run_context。

        终态:返固化 terminal_state + last_status/failed_node。
        运行中(started_at 非 None 且 terminal_state None):统一 RUNNING,读 current_op 的 current_node/retry。
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
        current_node = op._current_node.cn if op is not None and op._current_node is not None else None
        retry_count = op.node_retry_times if op is not None else None
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
        self._ctx.run_context.stop_running()
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
        return image

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

    def analyze(self, screenshot: str | None = None) -> AnalyzeScreenResult:
        """分析画面:截图 + 全图 OCR + 画面匹配(精准/模糊)。

        screenshot 省略 → 截当前游戏画面(需游戏窗口就绪);精准命中回写
        ``ctx.screen_loader.update_current_screen_name``,为下次 BFS 提供起点。
        screenshot 传入 → 解析指定截图,**无需游戏窗口就绪**:绝对路径按路径读,
        纯名字到 ``.debug/images/<名字>.png`` 读;读不到返失败(error 带解析后完整路径)。
        **不回写**识别状态(离线 / 可能是旧图,不污染实时识别)。

        Args:
            screenshot: 截图绝对路径,或 ``.debug/images`` 下的图名(不带后缀);
                None 表示实时截当前画面。

        Returns:
            分析结果:成功标志、OCR 文本列表、画面匹配列表、错误描述。
        """
        self._ensure_ready()
        if screenshot is None:
            controller = self._ctx.controller
            if controller is None or not controller.is_game_window_ready:
                return AnalyzeScreenResult(success=False, ocr_texts=[], screens=[], error='游戏窗口未就绪')
            image = controller.get_screenshot(independent=False)
            if image is None:
                return AnalyzeScreenResult(success=False, ocr_texts=[], screens=[], error='截图失败')
            write_back = True
        else:
            image, resolved = self._resolve_screenshot(screenshot)
            if image is None:
                return AnalyzeScreenResult(success=False, ocr_texts=[], screens=[], error=f'读取截图失败: {resolved}')
            write_back = False
        try:
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
            return AnalyzeScreenResult(success=True, ocr_texts=ocr_texts, screens=screens, error=None)
        except Exception as e:  # noqa: BLE001 OCR/匹配异常兜底:不回写,返失败
            return AnalyzeScreenResult(success=False, ocr_texts=[], screens=[], error=str(e))

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

    def _safe_area_count(self, screen_name: str) -> int | None:
        """异常路径下尽量取 area 数(取不到返 None,不再抛)。"""
        try:
            return len(self._ctx.screen_loader.get_screen(screen_name).area_list)
        except Exception:  # noqa: BLE001
            return None

    def close_game(self) -> str:
        """关闭游戏(发关闭窗口信号,秒级,不走 RunSlot)。

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

    def click_game(self, x: int | float, y: int | float, press_time: float = 0.0) -> dict:
        """点击游戏窗口内指定坐标(1080p 游戏空间,同源 screen_info pc_rect)。操作类。

        坐标经控制器自动缩放到真实屏幕。坐标不在游戏窗口内时控制器返 False(不点击)。

        Args:
            x, y: 默认分辨率(1920×1080)下的游戏窗口坐标。
            press_time: >0 时长按若干秒。

        Returns:
            ``{success, x, y, in_window}``:``success/in_window=False`` 表示坐标不在窗口内。

        Raises:
            BackendNotReadyError: SrContext 未就绪或游戏窗口未就绪时抛。
        """
        self._ensure_ready()
        controller = self._ctx.controller
        if controller is None or not controller.is_game_window_ready:
            raise BackendNotReadyError('游戏窗口未就绪')
        controller.active_window()
        clicked = controller.click(Point(int(x), int(y)), press_time=press_time)
        return {'success': clicked, 'x': int(x), 'y': int(y), 'in_window': clicked}

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

    def start_run(self, source: str, op_factory: 'Callable[[SrContext], Operation]') -> tuple[bool, Future | None]:
        """触发运行(供 MCP/HTTP 适配器调用,返回 future 供 block=True 时 await)。

        单跑道委托 ``run_slot._start_run``:已有运行在进行时返回 ``ok=False``，
        适配器据此返回并发拒绝；其余由 RunSlot 在后台线程内执行 operation。

        Args:
            source: 触发方标识，如 ``"mcp"``/``"http"``。
            op_factory: operation 构造器，由适配器提供。

        Returns:
            ``(ok, future)``：``ok=False`` 表示已有运行在进行(``future=None``)；
            ``ok=True`` 表示已启动，``future`` 可供阻塞 await 取结果。
        """
        return self.run_slot._start_run(source, op_factory)

    def query_status(self) -> RunStatusResult:
        """查询运行状态(委托 ``run_slot._query_status``)。

        Returns:
            当前运行状态的传输无关结构。
        """
        return self.run_slot._query_status()

    def stop(self) -> dict:
        """停止当前运行(委托 ``run_slot._stop``)。

        Returns:
            ``{"stopped": True, "source": <触发方>}`` 成功发出停止信号；
            ``{"stopped": False, "error": "当前无运行"}`` 无运行可停。
        """
        stopped, source = self.run_slot._stop()
        if not stopped:
            return {'stopped': False, 'error': '当前无运行'}
        return {'stopped': True, 'source': source}

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
