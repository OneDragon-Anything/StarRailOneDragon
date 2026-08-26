# ADR-0396 停机守卫:run 26 停机后幽灵活动(run 27「已停止后又出战成功」同型,
# ADR-0388 的 CW 局部刹车是第一代补丁,本模块是其框架级重写)。
from __future__ import annotations

from collections.abc import Callable


class StopRunInterrupted(Exception):
    """运行被停止信号中断。

    停机守卫(controller 层)在任何游戏输入动作(click/drag/按键/滚轮/输入/
    移动光标)前检查「本次运行已被停止信号中断」闩,已中断则抛本异常。
    异常穿透所有嵌套 ``Operation.execute``(不在中间 op 层被吞成普通失败——
    否则父链会像 ADR-0388 实证的 director 环一样继续发下一步动作),由顶层
    (``ApplicationRunContext.run_application`` / backend op 槽)收口为「已停止」。
    """


def check_stop_guard(stop_guard: Callable[[], bool] | None) -> None:
    """检查停机中断闩;已中断则抛 ``StopRunInterrupted``。

    Args:
        stop_guard: 无参谓词,返回 True 表示本次运行已被停止信号中断
            (``ApplicationRunContext.is_stop_interrupted``)。None = 未接线
            (独立使用 controller 的场景,不拦)。
    """
    if stop_guard is not None and stop_guard():
        raise StopRunInterrupted('运行已被停止信号中断,拦截本次游戏输入(ADR-0396)')
