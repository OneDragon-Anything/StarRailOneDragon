"""货币战争操作基类 CwOperation(sim 接缝覆写面;驱动反转迭代)。

CW operations 树全部操作类的唯一父类(实机路径行为零变化):继承框架
``SrOperation``,仅在 sim 后端装配(``sim/cw_sim_ports.install_sim_backend``)
时改写三条腿——观察/点击/按键停触真实 IO,改由后端应答:

- ``screenshot()`` —— sim 返回哨兵帧(空白 1080p 帧,模块级缓存),不触
  controller;框架每轮自动截图(``Operation._execute_one_round`` →
  ``self.screenshot()`` → ``last_screenshot``)无感运转。与 controller 桩
  构成双保险:漏改的帧消费者在哨兵帧上真识别 → 恒未找到 → retry 耗尽
  fail(帧取全屏空白形状,area 裁剪不崩、识别恒空,失败形态干净可归因)。
- ``round_by_find_and_click_area()`` —— sim 委托端口 ``click_answer``
  (后端按点击处理画面状态机转移,机械镜 = 档案点位直成功 + until =
  ``visible`` 问询,见 ``cw_sim_ports.mirror_click_answer``);until 轮询腿
  (点击已发出再问转移证据)在本层直接以 ``visible`` 问询收尾,不重进后端
  (重复进 = 重复触发转移);实机 → ``super()`` 原样。
- ``round_by_find_area()`` —— sim 以端口 ``visible`` 应答;实机 →
  ``super()``。
- ``park_cursor()`` —— sim 零光标可停,静默跳过;实机 → ``super()``。

其余 round_by_* / screen_utils 助手一律 ``super()`` 透传(全量清点表 =
flow-seam 详设附录 A);直连 controller 旁路不在本类覆写(逐点 port 检查
归各旁路文件,运行器 controller 桩兜底触碰即炸)。

sim 分支的等待语义:等待参数透传丢弃(sim 世界瞬时呈现,测试侧
``fast_sleep`` 旁路真实等待;sim 运行不该睡实机时长的等待)。
"""
from __future__ import annotations

import time
from collections.abc import Callable

import numpy as np
from cv2.typing import MatLike

from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 哨兵帧缓存(sim 模式全程共用同一空白帧;纯零内容,消费者只读)。
_SENTINEL_FRAME: np.ndarray | None = None


def _sentinel_frame() -> np.ndarray:
    """哨兵帧(1080p 空白;惰性构建一次)。"""
    global _SENTINEL_FRAME
    if _SENTINEL_FRAME is None:
        _SENTINEL_FRAME = np.zeros((1080, 1920, 3), dtype=np.uint8)
    return _SENTINEL_FRAME


class CwOperation(SrOperation):
    """CW 操作基类(operations 树唯一父类;sim 覆写面见模块 docstring)。"""

    def __init__(self, ctx: SrContext,
                 node_max_retry_times: int = 3,
                 op_name: str = '',
                 timeout_seconds: float = -1,
                 op_callback: Callable[[OperationResult], None] | None = None,
                 need_check_game_win: bool = True
                 ):
        SrOperation.__init__(self, ctx,
                             node_max_retry_times=node_max_retry_times,
                             op_name=op_name,
                             timeout_seconds=timeout_seconds,
                             op_callback=op_callback,
                             need_check_game_win=need_check_game_win)

    def screenshot(self) -> MatLike:
        """sim → 哨兵帧不触 controller;实机 → super() 原样。"""
        if cw_sim_ports.sim_backend_installed():
            frame = _sentinel_frame()
            self.last_screenshot_time = time.time()
            self.last_screenshot = frame
            return frame
        return super().screenshot()

    def park_cursor(self, before_wait: float = 0.1,
                    after_wait: float = 0.2) -> None:
        """sim → 无光标可停,静默跳过;实机 → super() 原样。"""
        if cw_sim_ports.sim_backend_installed():
            return
        super().park_cursor(before_wait=before_wait, after_wait=after_wait)

    def round_by_find_and_click_area(
        self,
        screen: MatLike | None = None,
        screen_name: str | None = None,
        area_name: str | None = None,
        pre_delay: float = 0.3,
        success_wait: float | None = None,
        success_wait_round: float | None = None,
        retry_wait: float | None = None,
        retry_wait_round: float | None = None,
        until_find_all: list[tuple[str, str]] = None,
        until_not_find_all: list[tuple[str, str]] = None,
        crop_first: bool = False,
        center_x: bool = False,
    ) -> OperationRoundResult:
        """sim → 端口 click_answer(状态机转移 + 机械镜应答);实机 → super()。

        until 轮询腿在本层收尾:点击已发出(``node_clicked``)且带 until 时,
        直接以端口 ``visible`` 问询出结果,**不再进后端 click_answer**——
        后端按点击处理状态机转移,轮询重入会重复触发转移(「sim 点击腿
        已成功不重发」,flow-seam 详设 §2)。
        """
        if cw_sim_ports.sim_backend_installed():
            if self.node_clicked and (until_find_all is not None
                                      or until_not_find_all is not None):
                if until_find_all is not None and all(
                        cw_sim_ports.visible(_s, _a)
                        for _s, _a in until_find_all):
                    return self.round_success(status=area_name)
                if until_not_find_all is not None and not any(
                        cw_sim_ports.visible(_s, _a)
                        for _s, _a in until_not_find_all):
                    return self.round_success(status=area_name)
                return self.round_wait(status=area_name)
            return cw_sim_ports.click_answer(
                self, screen_name, area_name,
                until_find_all, until_not_find_all)
        return super().round_by_find_and_click_area(
            screen=screen,
            screen_name=screen_name,
            area_name=area_name,
            pre_delay=pre_delay,
            success_wait=success_wait,
            success_wait_round=success_wait_round,
            retry_wait=retry_wait,
            retry_wait_round=retry_wait_round,
            until_find_all=until_find_all,
            until_not_find_all=until_not_find_all,
            crop_first=crop_first,
            center_x=center_x,
        )

    def round_by_find_area(
        self,
        screen: MatLike,
        screen_name: str,
        area_name: str,
        success_wait: float | None = None,
        success_wait_round: float | None = None,
        retry_wait: float | None = None,
        retry_wait_round: float | None = None,
        crop_first: bool = False,
    ) -> OperationRoundResult:
        """sim → 端口 visible 应答(可见 = success,不可见 = retry);
        实机 → super() 原样。等待参数 sim 侧丢弃。"""
        if cw_sim_ports.sim_backend_installed():
            if cw_sim_ports.visible(screen_name, area_name):
                return self.round_success(status=area_name)
            return self.round_retry(status=f'未找到 {area_name}')
        return super().round_by_find_area(
            screen,
            screen_name,
            area_name,
            success_wait=success_wait,
            success_wait_round=success_wait_round,
            retry_wait=retry_wait,
            retry_wait_round=retry_wait_round,
            crop_first=crop_first,
        )
