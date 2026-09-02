from concurrent.futures import Future

from one_dragon.base.controller.stop_guard import StopRunInterrupted
from one_dragon.utils.log_utils import log


def handle_future_result(future: Future):
    try:
        future.result()
    except StopRunInterrupted:
        # 停机守卫异常是 BaseException(穿透 best-effort 包装),泛型 except
        # Exception 接不住——future 携带它时若不显式接,会穿透 done-callback
        # 打死 executor 工作线程(threading.excepthook 只留栈不留语义)。
        # 在此收口为信息级日志:异步任务被停机中断是预期终态,非失败。
        log.info('异步执行被停机中断收口(StopRunInterrupted)')
    except Exception:
        log.error('异步执行失败', exc_info=True)
