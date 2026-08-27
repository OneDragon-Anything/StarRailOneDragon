# ADR-0396 停机守卫:run 26 停机后幽灵活动(run 27「已停止后又出战成功」同型,
# ADR-0388 的 CW 局部刹车是第一代补丁,本模块是其框架级重写)。
# ADR-0406 手动端点本地豁免:显式外部接管(MCP 手动输入)不清全局闩,改为
# 本线程豁免——守卫在 run 收口期(STOP 已置、run 线程仍 unwind)保持活跃,
# 手动操作在豁免令牌内放行;豁免按线程隔离,run 线程视角守卫永远生效。
from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager


class StopRunInterrupted(Exception):
    """运行被停止信号中断。

    停机守卫(controller 层)在任何游戏输入动作(click/drag/按键/滚轮/输入/
    移动光标)前检查「本次运行已被停止信号中断」闩,已中断则抛本异常。
    异常穿透所有嵌套 ``Operation.execute``(不在中间 op 层被吞成普通失败——
    否则父链会像 ADR-0388 实证的 director 环一样继续发下一步动作),由顶层
    (``ApplicationRunContext.run_application`` / backend op 槽)收口为「已停止」。
    """


# 豁免令牌按线程隔离(thread-local):手动端点跑在 MCP 请求线程,run 跑在
# executor 线程——豁免只对本线程的 controller 调用生效,另一线程(unwind
# 中的 run 线程)同时发起的输入仍被守卫拦截(ADR-0406)。
_exempt_tls = threading.local()


@contextmanager
def stop_guard_exemption() -> Iterator[None]:
    """本线程的停机守卫本地豁免上下文。

    显式外部接管入口(MCP 手动 click_game/key_tap/drag/input_text 等)用
    本上下文包裹 controller 调用:动作放行但**不清全局停机闩**——闩仍保护
    run 收口期(STOP 已置、run 线程仍 unwind)的幽灵输入(ADR-0406,
    取代 ADR-0396 的 consume_stop_interrupted 清闩语义)。可嵌套(内层
    退出不解除外层豁免)。
    """
    prev = getattr(_exempt_tls, 'value', False)
    _exempt_tls.value = True
    try:
        yield
    finally:
        _exempt_tls.value = prev


def is_stop_guard_exempted() -> bool:
    """当前线程是否持有停机守卫豁免令牌。"""
    return getattr(_exempt_tls, 'value', False)


def check_stop_guard(stop_guard: Callable[[], bool] | None) -> None:
    """检查停机中断闩;已中断则抛 ``StopRunInterrupted``。

    Args:
        stop_guard: 无参谓词,返回 True 表示本次运行已被停止信号中断
            (``ApplicationRunContext.is_stop_interrupted``)。None = 未接线
            (独立使用 controller 的场景,不拦)。

    本线程持有豁免令牌(手动端点接管)时不拦——闩本身不动,其它线程仍受辖。
    """
    if (not is_stop_guard_exempted()
            and stop_guard is not None and stop_guard()):
        raise StopRunInterrupted('运行已被停止信号中断,拦截本次游戏输入(ADR-0396)')
