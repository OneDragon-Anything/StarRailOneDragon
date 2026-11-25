"""帧来源信号:告诉识别链「当前处理的这一帧是不是实机实时画面」。

为什么需要它:入口层(``SrBackendContext.analyze``)的实时分支与读图分支只在「取帧」
处分开,取到帧之后走同一段识别代码——下游的停机钩子、补采门、留证汇点、状态容器写端
无从分辨手里的帧是刚从窗口截的、还是调用方传入的一张历史图,只能各自用代理条件猜
(「有控制器就是实时」「凡进识别链的帧都是实机当前画面」),而且都猜错。公共包对识别器
的契约本就是纯读(``one_dragon/base/screen/screen_recognizer.py`` 类注释:recognize
不得写 ``self.``、不得复用带业务语义进程级可变状态的 reader),这个信号是让下游在
产生副作用前有一个可靠的「该不该做」判据。

为什么用上下文变量而不是给读链加参数:读链入口调用方多(备战 / 开商店识别器、
重观察、对局记录器、各 op),加参数要逐层透传,漏传一处就回到现状;「这帧是不是实时的」
是帧的属性,跟着调用上下文走更贴合。并发上:``analyze_screen`` 是同步工具函数,MCP SDK
对同步工具在事件循环线程上直接调用(不经线程池),每条入站 MCP 消息各起一个 anyio
任务,任务起始拷贝上下文,``offline_frame()`` 的置位与复位在同一任务内同步完成;同时
在对局线程里跑的 op 读到的是缺省 ``LIVE``,互不影响。

本模块只提供信号,不提供任何写盘 / 停机 / 截图能力:需要离线语义的调用方
``with offline_frame():`` 即可,零副作用。
"""
from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager
from enum import Enum


class FrameSource(Enum):
    """帧来源取值。"""

    LIVE = 'live'       #: 实时帧:刚从游戏窗口截到的当前画面
    OFFLINE = 'offline'  # 离线帧:调用方传入的历史图(路径 / debug 图名 / 样本)


#: 当前识别链处理的帧来源。缺省 LIVE——对局运行链(op / heavy 观察 / 对局记录器)
#: 与直接调读链的测试 / 脚本都不进 ``offline_frame()``,读到的就是这个缺省值。
_current: contextvars.ContextVar[FrameSource] = contextvars.ContextVar(
    'sr_od_frame_source', default=FrameSource.LIVE)


def frame_is_live() -> bool:
    """当前识别链处理的帧是否实时帧(缺省 True;``offline_frame()`` 内为 False)。"""
    return _current.get() is FrameSource.LIVE


@contextmanager
def offline_frame() -> Iterator[None]:
    """把当前调用上下文标记为「离线帧」的上下文管理器。

    进入置 OFFLINE;退出(含异常退出)复位到进入前的值——嵌套时内层退出不会
    把外层的标记也清掉。效果限于当前执行线程 / 任务的上下文副本。
    """
    token = _current.set(FrameSource.OFFLINE)
    try:
        yield
    finally:
        _current.reset(token)
