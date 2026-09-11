"""跨进程运行互斥:按游戏窗口标题的锁(Windows 字节区间锁)。

为什么存在:框架的「单跑道」约束(同一时刻至多一个运行体驱动游戏)原先只在
进程内成立——server 的 ``RunSlot`` 用线程池 + 进程内锁,``ApplicationRunContext``
用进程内运行态,跨进程互不可见。2026-08-24 实机事故:直驱进程与 server 进程
同时驱动同一游戏窗口,双 run 交替操作导致 OCR 残缺误识别、app 异常失败。
根治 = 把互斥载体移到跨进程可见的地方:锁文件(按窗口标题命名)+ 操作系统
字节区间锁(``msvcrt.locking``)。

为什么用字节区间锁而非 O_EXCL 标志文件:持有者进程无论正常退出还是崩溃,
操作系统都会自动释放句柄上的区间锁——不存在「残留死锁」态,无需心跳或
陈旧检测。锁文件内容(pid / 来源 / 取得时间)仅作诊断展示,不参与互斥判定。

边界:
- 锁的生命周期 = ``ApplicationRunContext`` 的运行态生命周期(start_running 取得,
  _finish_running 释放);停止信号(stop_running)即释放,与进程内运行态语义一致,
  op 线程收尾间隙不额外持锁。
- 缺省行为 = 检测到占用即拒绝(安全优先),不排队不等待;占用描述经
  ``other_holder_description`` 供调用方拼入「游戏窗口被他进程占用」类错误消息。
- 窗口标题不可得(非 PC 控制器等)时回退全局默认键——互斥变保守(跨窗口也互斥),
  宁可误拒不误放。
"""

import hashlib
import json
import msvcrt
import os
import re
import threading
from datetime import datetime
from pathlib import Path

from one_dragon.utils import os_utils
from one_dragon.utils.log_utils import log

# 窗口标题不可得时的回退锁键(全局一把锁,保守互斥)。
DEFAULT_LOCK_KEY: str = '__default_window__'

# 锁文件锁定区间长度(字节)。Windows 允许锁定超出文件末尾的区域,
# 因此空文件也能直接锁 [0,1),无需预写占位字节。
# 字节 0 专作锁字节:独占区间锁会连「其它句柄读取该字节」一并拒绝,
# 持有者信息从偏移 1 起写/读,保证占用描述在锁争用期间仍可读。
_LOCK_REGION_BYTES: int = 1
_INFO_OFFSET_BYTES: int = 1


def default_lock_dir() -> Path:
    """跨进程锁文件目录(``<work_dir>/.debug/run_mutex``)。

    独立成函数仅为让测试重定向到 tmp_path(测试禁写真实 .debug);
    work_dir 按源码位置推导(os_utils.get_work_dir),server / GUI / 直驱脚本
    各进程取值一致,保证锁文件同一。
    """
    return Path(os_utils.get_path_under_work_dir('.debug', 'run_mutex'))


def sanitize_lock_key(win_title: str | None) -> str:
    """把窗口标题转成合法且跨进程一致的锁文件名片段。

    标题可能含 Windows 文件名非法字符(如星铁标题里的冒号),统一替换为
    下划线;再附标题内容的短哈希后缀,防不同标题净化后撞名或超长。
    """
    if not win_title:
        return DEFAULT_LOCK_KEY
    cleaned = re.sub(r'[^\w\-]', '_', win_title)[:60]
    digest = hashlib.md5(win_title.encode('utf-8')).hexdigest()[:8]  # noqa: S324
    return f'{cleaned}_{digest}'


def resolve_lock_key(controller: object) -> str:
    """从控制器解析锁键(= 净化后的游戏窗口标题)。

    PC 控制器经 ``game_win.win_title`` 携带窗口标题(与窗口查找同源,两边进程
    配置一致即同键);非 PC 控制器或标题缺失/非字符串(测试替身常见)回退
    全局默认键。防御式取值是为不把互斥层耦合到具体控制器类型上。
    """
    game_win = getattr(controller, 'game_win', None)
    title = getattr(game_win, 'win_title', None)
    if not isinstance(title, str) or not title:
        return DEFAULT_LOCK_KEY
    return sanitize_lock_key(title)


def _lock_file_path(lock_dir: Path, lock_key: str) -> Path:
    """锁文件完整路径:``<lock_dir>/<lock_key>.lock``。"""
    return lock_dir / f'{lock_key}.lock'


def _read_holder_description(path: Path) -> str:
    """读锁文件里的持有者信息拼人类可读描述;读不到/内容坏按未知处理。

    仅在「区间锁争用失败」后调用——能失败即说明此刻确有持有者,文件内容
    只是标识它(可能是上一位持有者的残留,诊断参考,不作互斥依据)。
    从偏移 1 起读:字节 0 是锁字节,正被持有者独占区间锁着,读了必失败。
    """
    try:
        with open(path, 'rb') as f:
            f.seek(_INFO_OFFSET_BYTES)
            raw = f.read().decode('utf-8', errors='replace')
        info = json.loads(raw)
        pid = info.get('pid')
        source = info.get('source') or '未知来源'
        acquired_at = info.get('acquired_at') or ''
        return f'pid={pid}, 来源={source}, 取得于 {acquired_at}'.strip(', ')
    except Exception:  # noqa: BLE001 内容残缺不影响互斥判定,只降级描述
        return '持有者信息不可读'


class WindowRunMutex:
    """单个窗口锁的一次持有会话:acquire 持有,release 释放,实例不复用。

    实例与一次运行绑定(ApplicationRunContext 每次 start_running 新建),
    避免「上一次运行的句柄残留」类状态复用错误。方法可在不同线程调用
    (start 所在线程取锁,stop 信号所在线程释放),内部以锁保护状态翻转。
    """

    def __init__(self, lock_dir: Path | str, lock_key: str, owner_source: str = '') -> None:
        """声明锁目录、锁键与持有方来源标签(写入锁文件供诊断)。"""
        self._lock_dir: Path = Path(lock_dir)
        self._lock_key: str = lock_key
        self._owner_source: str = owner_source
        self._fd: int | None = None
        self._other_holder: str | None = None
        # 取锁与释放可能来自不同线程(运行线程取,停止线程放),状态翻转串行化。
        self._state_guard: threading.Lock = threading.Lock()

    @property
    def lock_key(self) -> str:
        """本锁对应的窗口键(净化后的窗口标题)。"""
        return self._lock_key

    @property
    def is_holding(self) -> bool:
        """当前实例是否持有区间锁。"""
        return self._fd is not None

    def other_holder_description(self) -> str | None:
        """最近一次 acquire 失败的占用者描述;从未失败过返回 None。"""
        return self._other_holder

    def acquire(self) -> bool:
        """非阻塞尝试取锁。成功返回 True;被占返回 False 并记录占用者描述。

        互斥真源 = 操作系统字节区间锁(持有进程死亡即自动释放),锁文件
        存在与否不代表占用;成功取得后才写持有者信息(诊断用)。
        """
        with self._state_guard:
            if self._fd is not None:
                # 本实例已持有:编程错误而非争用,显式失败防静默重入。
                log.error('窗口锁 %s 已被本实例持有,不可重复 acquire', self._lock_key)
                return False
            self._lock_dir.mkdir(parents=True, exist_ok=True)
            path = _lock_file_path(self._lock_dir, self._lock_key)
            try:
                fd = os.open(path, os.O_RDWR | os.O_CREAT)
            except OSError as e:
                # 打不开锁文件(权限/盘故障)按占用拒套:安全优先,不放行。
                log.error('窗口锁文件打开失败 %s: %s', path, e)
                self._other_holder = f'锁文件不可用({e})'
                return False
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, _LOCK_REGION_BYTES)
            except OSError:
                os.close(fd)
                self._other_holder = _read_holder_description(path)
                return False
            self._fd = fd
            self._write_owner_info(path)
            return True

    def _write_owner_info(self, path: Path) -> None:
        """取得锁之后写持有者信息(诊断展示;写失败不影响持锁)。

        从偏移 1 起写:字节 0 是锁字节(独占区间锁拒绝其它句柄读它),
        持有者信息放锁字节之后,争用方才能读出占用者描述。
        """
        try:
            os.ftruncate(self._fd, 0)
            os.lseek(self._fd, _INFO_OFFSET_BYTES, os.SEEK_SET)
            payload = json.dumps({
                'pid': os.getpid(),
                'source': self._owner_source,
                'acquired_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }, ensure_ascii=False)
            os.write(self._fd, payload.encode('utf-8'))
        except Exception as e:  # noqa: BLE001 诊断信息写失败不回滚互斥
            log.warning('窗口锁持有者信息写入失败 %s: %s', path, e)

    def release(self) -> None:
        """释放区间锁并关闭句柄;未持有时为幂等 no-op。

        只解锁不删文件:删文件与其它进程的打开句柄存在竞态,残留空文件
        无任何语义(互斥真源是区间锁,不是文件存在性)。
        """
        with self._state_guard:
            if self._fd is None:
                return
            fd, self._fd = self._fd, None
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, _LOCK_REGION_BYTES)
            except OSError as e:
                # 解锁失败通常意味着持有进程已由操作系统回收锁(崩溃/终止),
                # 关闭句柄兜底即可,不影响其它进程后续取锁。
                log.warning('窗口锁 %s 解锁异常(持有进程可能已退出): %s', self._lock_key, e)
            finally:
                os.close(fd)
            self._other_holder = None


def probe_window_occupancy(lock_dir: Path | str, lock_key: str) -> str | None:
    """无持有探测:锁空闲返回 None;被占返回占用者描述(供拒绝消息)。

    用「试锁即还」实现:拿得到 = 空闲(立即解锁还原);拿不到 = 被占。
    探测与后续真实取锁之间存在竞态窗口,探测结果只作快速拒绝的提示,
    权威判定仍在各运行入口的真实 acquire。
    """
    mutex = WindowRunMutex(lock_dir, lock_key, owner_source='probe')
    if mutex.acquire():
        mutex.release()
        return None
    return mutex.other_holder_description()


def describe_window_blocker(controller: object, owner_source: str = '') -> str | None:
    """一步拿到「当前窗口是否被他进程占用」的描述;空闲返回 None。

    供 server 运行槽在受理前快速探测;锁键从控制器窗口标题推导,
    与 ``ApplicationRunContext`` 运行门用同一推导(见 ``resolve_lock_key``)。
    """
    return probe_window_occupancy(default_lock_dir(), resolve_lock_key(controller))
