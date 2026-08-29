import logging
import os
import shutil
import threading
import time
import weakref
from contextlib import suppress
from dataclasses import dataclass
from errno import EACCES, EBUSY
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from one_dragon.utils import os_utils

LOGGER_NAME = 'OneDragon'
_HANDLER_OWNER_ATTR = '_one_dragon_logger_owner'

#: 轮转被占用时的重试次数与基础退避秒数(指数退避,上限 0.8s/次)。
_ROTATE_RETRY_COUNT = 5
_ROTATE_RETRY_BASE_DELAY = 0.05
#: 重试全失败的冷却秒数:期间沿用当前文件继续写,不逐条日志反复撞锁。
#: 下一轮转时点到期后自动重试,占用方(其他进程的轮转窗口通常 <1s)早已释放。
_ROTATE_DEFER_COOLDOWN_SECONDS = 60.0

#: 同路径互斥锁表:同进程内指向同一日志文件的多个 handler 共用一把锁,
#: 串行化 doRollover —— 没有它,A 刚完成换名、B 仍按旧文件对象重开/降级,
#: 会出现两个活跃写句柄(与跨进程双写同症状)。
_PATH_LOCKS: dict[str, threading.RLock] = {}
_PATH_LOCKS_GUARD = threading.Lock()
#: 同路径活跃 handler 登记表(弱引用,close 时注销):换名成功后据此定位
#: 同路径的其他 handler 并强制关闭其存活流 —— 旧流若继续写,写入的是
#: 已改名的归档文件,单文件离线取证会读出「延迟重放流混入实时流」的
#: 错乱时间线。跨进程对端的句柄在本进程内关不掉,由占用退避+推迟降级兜底,
#: 本表只管进程内可达的部分。
_PATH_HANDLERS: dict[str, weakref.WeakSet] = {}


def _norm_path_key(filename: str) -> str:
    """把日志文件路径归一成登记表/锁表的键(Windows 大小写不敏感)。"""
    return os.path.normcase(os.path.abspath(filename))


def _get_path_lock(path_key: str) -> threading.RLock:
    with _PATH_LOCKS_GUARD:
        lock = _PATH_LOCKS.get(path_key)
        if lock is None:
            lock = threading.RLock()
            _PATH_LOCKS[path_key] = lock
        return lock


def _path_handlers(path_key: str) -> list['SafeTimedRotatingFileHandler']:
    """登记在册的同路径 handler 快照(含任意调用者自身;死引用自动剔除)。"""
    with _PATH_LOCKS_GUARD:
        handlers = _PATH_HANDLERS.get(path_key)
        return [h for h in tuple(handlers) if h is not None] if handlers else []


class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """跨进程安全加固的按时间轮转文件 handler。

    背景(WinError 32 四度实证,W251/W252/W261 批测试随机红):
    ``TimedRotatingFileHandler.doRollover`` 在 Windows 上用 ``os.rename`` 换名,
    而 Windows 不允许改名被任何进程打开中的文件 —— 凡是两个进程同时持有同一
    日志文件的句柄(默认 ``log.txt`` 在每个 import 本模块的进程中都会挂一份),
    到点轮转时后到的那个进程 rename 必然抛 ``PermissionError(WinError 32)``。

    策略:rename 遇到「文件被占用」类错误(WinError 32/33、errno EACCES/EBUSY)
    时退避重试;仍失败则退化为 copytruncate 兜底(见 rotate),仅当连兜底都无法
    完成时才放弃本次轮转、继续向当前文件追加并推迟到下一个时点再试 —— 日志短暂
    跨天不切分是可接受的降级,写日志抛异常污染调用方(pytest 随机红)不可接受。
    其余 OSError 照常上抛。

    另三处同族守卫(跨零点错乱时间线的实证根因是标准库 doRollover 失败时
    ``rolloverAt`` 不推进 → 每条日志重试换名、重试窗口内换名偶发成功会把
    别的写入流甩进已改名的归档文件,出现"延迟重放流混入实时流"):
    ① 换名已成功但随后的旧归档清理被占用 → 视作轮转完成,只推进时点,
       绝不重试(对已不存在的源文件再 rename 会抛 FileNotFoundError 逃逸);
    ② 全败降级重开流时,只在无流时补开 —— 并发 emit 的 shouldRollover
       可能在本方法关闭流之后已重开流,直接赋值会丢弃活句柄造成同进程双写;
    ③ 同进程内指向同一文件的所有 handler 经同路径锁串行化轮转,换名成功
       (含被他人换名、源文件消失的视作完成分支)后,强制其他 handler 的
       存活流关闭置空 —— 旧流继续写会落进已改名的归档文件,是重放流混入
       的换名成功侧根因;置空后对端按路径重开,自然落到换名后的新文件。
    """

    def __init__(
        self,
        filename: str,
        when: str = 'h',
        interval: int = 1,
        backupCount: int = 0,
        encoding: str | None = None,
        delay: bool = False,
        utc: bool = False,
        errors: str | None = None,
        atTime=None,
    ) -> None:
        # 显式声明父类(logging.handlers.TimedRotatingFileHandler)签名并透传:
        # 基类来自标准库,kwarg 静态审计锁(kwarg_audit.scanner)只能看到同文件
        # 的 def/class 定义,看不到继承来的 __init__,会把本类的调用点误判为
        # 「无参类收 kwarg」违规 —— 显式转发让签名静态可见。
        TimedRotatingFileHandler.__init__(
            self,
            filename=filename,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            errors=errors,
            atTime=atTime,
        )
        # baseFilename 已由 FileHandler.__init__ 归一为绝对路径,这里再 normcase
        # 统一 Windows 大小写,保证同文件的两个 handler 命中同一把锁/同一登记表。
        with _PATH_LOCKS_GUARD:
            _PATH_HANDLERS.setdefault(
                _norm_path_key(self.baseFilename), weakref.WeakSet()
            ).add(self)

    def close(self) -> None:
        # 先注销再走标准关闭:登记表是弱引用,不留悬挂条目,也不阻止 GC。
        with _PATH_LOCKS_GUARD:
            handlers = _PATH_HANDLERS.get(_norm_path_key(self.baseFilename))
            if handlers is not None:
                handlers.discard(self)
        super().close()

    def doRollover(self) -> None:
        # 同路径互斥:同文件的其他 handler 的轮转与本方法串行,防止交叠期
        # 「A 换名 / B 降级重开」产生第二个活跃写句柄。
        with _get_path_lock(_norm_path_key(self.baseFilename)):
            self._do_rollover_locked()

    def _do_rollover_locked(self) -> None:
        # 与基类约定一致:先把当前流关掉(rename 的阻塞来源除本流自身的句柄外,
        # 还有其他进程持有的打开句柄 —— 自己这份必须先释放才有换名成功的可能)。
        if self.stream:
            self.stream.close()
            self.stream = None

        for attempt in range(_ROTATE_RETRY_COUNT):
            try:
                super().doRollover()
                # 换名成功:同路径其他 handler 的存活流必须置换,否则继续
                # 写进的是已改名的归档文件(重放流侧根因)。
                self._close_sibling_streams()
                return
            except OSError as e:
                occupied = (
                    getattr(e, 'winerror', None) in (32, 33)
                    or e.errno in (EACCES, EBUSY)
                )
                if not occupied:
                    raise
                if not os.path.exists(self.baseFilename):
                    # 源文件不在:可能本 handler 换名成功但旧归档清理被占用,
                    # 也可能是同路径另一 handler(或其他进程)已抢先换名。
                    # 两种情况都视作轮转完成:文件已按日期归档,流交惰性
                    # 重开落到新文件;不重试 —— 对不存在的源文件 rename 会
                    # 抛 FileNotFoundError 逃逸。
                    self.rolloverAt = self.computeRollover(int(time.time()))
                    self._close_sibling_streams()
                    return
                if attempt < _ROTATE_RETRY_COUNT - 1:
                    time.sleep(min(_ROTATE_RETRY_BASE_DELAY * (2 ** attempt), 0.8))

        # 重试全失败:放弃本次轮转(日志短暂跨天不切分是可接受的降级),
        # 重开当前文件保持可写,并把下一个轮转时点推迟一个冷却期 —— 到期自动
        # 再试,届时占用方(其他进程的轮转窗口通常 <1s)早已释放。
        # 只在无流时补开:重试期间并发 emit 的 shouldRollover 会因流为 None
        # 重开流继续写当前文件,这里若无条件赋值会把那个活句柄变成游离的
        # 第二写句柄(同进程双写,与跨进程双写同症状)。
        if self.stream is None:
            self.stream = self._open()
        self.rolloverAt = int(time.time()) + int(_ROTATE_DEFER_COOLDOWN_SECONDS)
        # 静默降级:不向调用方抛错(调用方大多只是想记一行日志)。

    def rotate(self, source: str, dest: str) -> None:
        """占用兜底的轮转落点:rename 被外部句柄挡住时退化为 copytruncate。

        标准库 doRollover 的换名收口就是 ``self.rotate(source, dest)``,覆盖它
        即覆盖了全部 rename 失败路径(WinError 32 丢失现场的精确栈帧)。
        copytruncate(复制内容到归档名 + 截断源文件)不要求独占:Windows 的
        rename 需要目标无任何打开句柄,但读写打开(CRT 默认共享读+写)互不
        阻塞 —— 持有者是读句柄(尾随观察/日志查看器)时本路径必然成功。
        兜底自身失败(归档名不可写/源不可截断)时异常上抛,由调用方的重试
        +推迟降级接管,数据仍不丢。
        """
        try:
            os.rename(source, dest)
        except OSError as e:
            occupied = (
                getattr(e, 'winerror', None) in (32, 33)
                or e.errno in (EACCES, EBUSY)
            )
            if not occupied:
                raise
            self._rotate_by_copytruncate(source, dest)

    def _rotate_by_copytruncate(self, source: str, dest: str) -> None:
        """copytruncate 兜底:内容归档到 dest,源文件截断为空继续写。

        竞态限界(经典 copytruncate):复制与截断之间其他进程并发追加的行会被
        截掉,代价上限是该窗口内几行 —— 显式优于旧「推迟降级」的整日不轮转
        (轮转缺位会让归档错期,跨天判读误归属)。截断用 append 模式打开后
        truncate(0):持有 O_APPEND 写句柄的写入方下次写自动落到新 EOF(截断后
        的 0 偏移),不会在文件里留下稀疏空洞;本 handler 自身的流已由
        doRollover 入口关闭。
        """
        shutil.copyfile(source, dest)
        with open(source, 'ab') as f:
            f.truncate(0)

    def _close_sibling_streams(self) -> None:
        """换名成功后强制同路径其他 handler 关闭存活流(置换为按路径重开)。

        换名窗口内旧流仍存活时,它后续写入的是已改名的归档文件 —— 实时行
        落进归档,离线读出双流错乱时间线。置空流后,对端下一次 emit 经
        shouldRollover/惰性重开按路径打开,自然落到换名后的新文件。

        拿不到对端 handler 锁时跳过而非等待:对端 emit 的加锁序是
        「handler 锁 → 本方法所在的路径锁」,这里若阻塞等同一把 handler 锁
        会与之构成环(死锁)。跳过是安全的:对端当次写完即释放锁,后续
        任何一次轮转仍会置换其流;跨进程对端本就不可达,由占用退避兜底。
        """
        for sibling in _path_handlers(_norm_path_key(self.baseFilename)):
            if sibling is self or sibling.stream is None:
                continue
            # Handler.acquire() 不支持非阻塞,直接用底层 RLock 非阻塞获取。
            if not sibling.lock.acquire(blocking=False):
                continue
            try:
                if sibling.stream is not None:
                    with suppress(Exception):
                        sibling.stream.flush()
                        sibling.stream.close()
                    sibling.stream = None
            finally:
                sibling.lock.release()


#: stdout 兜底日志的尺寸轮转阈值(字节,20MB)与保留归档份数。
#: 背景见 rotate_large_stdout_log:server 的 stdout 日志(uvicorn 协议行/MCP SDK
#: 请求行)增长可达 ~0.7MB/分钟,只靠重启时清一次不够,启动方每次 spawn 前都查。
STDOUT_LOG_ROTATE_BYTES = 20 * 1024 * 1024
STDOUT_LOG_BACKUP_COUNT = 3


def rotate_large_stdout_log(
    log_path: str | Path,
    max_bytes: int = STDOUT_LOG_ROTATE_BYTES,
    backup_count: int = STDOUT_LOG_BACKUP_COUNT,
) -> bool:
    """对「多写端 append 共享」的 stdout 兜底日志做 copytruncate 尺寸轮转。

    使用场景:被 launcher 重定向 stdout 的子进程日志(如 MCP server 的
    main_server.log)。这类文件同时被多个进程持有打开句柄(子进程继承的
    stdout fd / GUI 日志页尾读 / 哨兵 tail),Windows rename 语义要求
    无任何打开句柄,直接换名必然 PermissionError——旧实现静默吞掉后
    轮转缺位、文件无限增长。copytruncate(复制归档 + 截断源文件)用
    CRT 默认共享模式读写打开,不要求独占,任何持有者都不阻塞。

    竞态限界(经典 copytruncate):复制与截断窗口内其他进程并发追加的行
    会被截掉,代价上限是该窗口几行;截断用 append 模式打开后 truncate(0),
    各写端(O_APPEND 语义)的下一次写自动落到新 EOF,不产生稀疏空洞。

    Args:
        log_path: 日志文件路径;不存在或未超阈值时不做任何事。
        max_bytes: 触发轮转的尺寸阈值(字节)。
        backup_count: 保留归档份数(编号 .1 最新 → .N 最旧,超出删除)。

    Returns:
        True=执行了轮转;False=未达阈值跳过。轮转自身失败不抛出:
        向日志文件本体追加一行 ERROR 标记后返回 False,保证「轮转缺位
        可观测」且绝不阻塞调用方(调用方处于启动子进程的关键路径上)。
    """
    path = Path(log_path)
    try:
        if not path.is_file() or path.stat().st_size <= max_bytes:
            return False
        # 旧归档无人持有打开句柄,按编号顺移(与 RotatingFileHandler 同约定)
        for i in range(backup_count - 1, 0, -1):
            src = path.with_name(path.name + f'.{i}')
            if not src.exists():
                continue
            dst = path.with_name(path.name + f'.{i + 1}')
            if dst.exists():
                dst.unlink()
            src.replace(dst)
        archive = path.with_name(path.name + '.1')
        shutil.copyfile(path, archive)
        with open(path, 'ab') as f:
            f.truncate(0)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f'[log_utils] stdout 日志已轮转(>{max_bytes // (1024 * 1024)}MB → {archive.name})\n')
        return True
    except OSError as e:
        with suppress(Exception), open(path, 'a', encoding='utf-8') as f:
            f.write(f'[log_utils] stdout 日志轮转失败(保持 append): {e}\n')
        return False


@dataclass(slots=True)
class LoggerConfig:
    level: int = logging.INFO
    log_file_path: str | None = None
    default_name: str = 'log.txt'
    add_console_handler: bool = True
    propagate: bool = False


@dataclass(slots=True)
class ProjectRuntimeLoggingContext:
    """项目显式启用的运行时日志分流结果。"""

    project_logger: logging.Logger
    framework_logger: logging.Logger
    project_log_file_path: str
    framework_log_file_path: str


def get_log_formatter() -> logging.Formatter:
    return logging.Formatter(
        '[%(asctime)s.%(msecs)03d] [%(filename)s %(lineno)d] [%(levelname)s]: %(message)s',
        '%H:%M:%S',
    )


def configure_logger(logger: logging.Logger, config: LoggerConfig) -> logging.Logger:
    """显式配置 logger。

    职责只有一个：将一个现成的 logger 调整到目标配置。
    仅会替换框架自己创建的 handler，不会移除外部追加的 handler。
    """
    _close_managed_handlers(logger)
    logger.setLevel(config.level)
    logger.propagate = config.propagate
    logger.addHandler(_build_file_handler(logger, config))
    if config.add_console_handler:
        logger.addHandler(_prepare_handler(logging.StreamHandler(), logger, config))
    return logger


def get_or_create_logger(name: str, config: LoggerConfig | None = None) -> logging.Logger:
    """获取指定名称的 logger。

    - 若框架尚未为该 logger 挂载默认 handler，则按给定配置初始化
    - 若已初始化过，则直接复用
    - 不会因为外部额外挂载了 handler 而跳过框架默认配置
    """
    logger = logging.getLogger(name)
    if any(_handler_belongs_to_logger(handler, logger) for handler in logger.handlers):
        return logger
    return configure_logger(logger, config or LoggerConfig())


def configure_project_runtime_logging(
    project_logger_name: str,
    project_log_file_path: str,
    framework_log_file_path: str,
    *,
    level: int = logging.INFO,
    project_add_console_handler: bool = False,
    framework_add_console_handler: bool = False,
    framework_logger_name: str = LOGGER_NAME,
) -> ProjectRuntimeLoggingContext:
    """为项目运行态显式启用项目日志与框架日志分流。

    默认的框架日志仍然写入 `log.txt`；只有项目主动调用本函数时，
    才会把项目 logger 和框架 logger 分别切到指定文件。
    """
    if project_logger_name == framework_logger_name:
        raise ValueError(
            'configure_project_runtime_logging 需要不同的 '
            'project_logger_name 和 framework_logger_name；否则 '
            '_configure_runtime_logger 会对同一个 logger 调用两次 '
            '_close_managed_handlers，导致 ProjectRuntimeLoggingContext '
            '静默丢失其中一套 handler 配置。'
        )

    project_logger = logging.getLogger(project_logger_name)
    framework_logger = logging.getLogger(framework_logger_name)

    framework_logger = _configure_runtime_logger(
        framework_logger,
        log_file_path=framework_log_file_path,
        level=level,
        add_console_handler=framework_add_console_handler,
    )
    project_logger = _configure_runtime_logger(
        project_logger,
        log_file_path=project_log_file_path,
        level=level,
        add_console_handler=project_add_console_handler,
    )
    return ProjectRuntimeLoggingContext(
        project_logger=project_logger,
        framework_logger=framework_logger,
        project_log_file_path=project_log_file_path,
        framework_log_file_path=framework_log_file_path,
    )


def _configure_runtime_logger(
    logger: logging.Logger,
    *,
    log_file_path: str,
    level: int,
    add_console_handler: bool,
) -> logging.Logger:
    return configure_logger(
        logger,
        LoggerConfig(
            level=level,
            log_file_path=log_file_path,
            add_console_handler=add_console_handler,
            propagate=False,
        ),
    )


def get_log_file_path(log_file_path: str | None = None, default_name: str = 'log.txt') -> str:
    """获取日志文件路径。

    - 未传 `log_file_path` 时，使用工作目录 `.log/` 下的默认文件名
    - 传相对路径/文件名时，仍然放在工作目录 `.log/` 下
    - 传绝对路径时，直接使用
    """
    configured = (log_file_path or '').strip()
    if not configured:
        configured = default_name
    path = Path(configured)
    if path.is_absolute():
        return str(path)
    return str(Path(os_utils.get_path_under_work_dir('.log')) / path)


def get_logger() -> logging.Logger:
    """获取框架默认 logger。

    若尚未初始化，则按默认配置初始化一次；若已经存在框架默认 handler，则直接复用。
    """
    return get_or_create_logger(LOGGER_NAME, LoggerConfig())


def set_log_level(level: int, logger: logging.Logger | None = None) -> None:
    """
    显示日志等级
    :param level:
    :return:
    """
    target = logger or log
    target.setLevel(level)
    for handler in target.handlers:
        if not _handler_belongs_to_logger(handler, target):
            continue
        handler.setLevel(level)


def mask_text(text: str) -> str:
    """
    对给定的文本进行脱敏处理，保留首尾部分字符，其余用 * 替换。
    如果字符数少于5个，则只保留首字符不脱敏。

    :param text: 需要脱敏的文本
    :return: 脱敏后的文本
    """
    if len(text) < 5:
        return text[0] + '*' * (len(text) - 1)
    else:
        return text[:2] + '*' * (len(text) - 4) + text[-2:]


def _close_managed_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if not _handler_belongs_to_logger(handler, logger):
            continue
        logger.removeHandler(handler)
        with suppress(Exception):
            handler.close()


def _handler_belongs_to_logger(handler: logging.Handler, logger: logging.Logger) -> bool:
    return getattr(handler, _HANDLER_OWNER_ATTR, None) == logger.name


def _build_file_handler(logger: logging.Logger, config: LoggerConfig) -> logging.Handler:
    handler = SafeTimedRotatingFileHandler(
        get_log_file_path(config.log_file_path, default_name=config.default_name),
        when='midnight',
        interval=1,
        backupCount=3,
        encoding='utf-8',
        delay=True,
    )
    return _prepare_handler(handler, logger, config)


def _prepare_handler(
    handler: logging.Handler,
    logger: logging.Logger,
    config: LoggerConfig,
) -> logging.Handler:
    setattr(handler, _HANDLER_OWNER_ATTR, logger.name)
    handler.setLevel(config.level)
    handler.setFormatter(get_log_formatter())
    return handler


log = get_logger()
