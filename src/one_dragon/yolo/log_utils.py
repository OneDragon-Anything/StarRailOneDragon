import logging
import os

_VERBOSE = str(os.getenv("OD_YOLO_VERBOSE", True)).lower() == "true"


def get_logger() -> logging.Logger:
    """YOLO 子系统 logger：零自有 handler，经框架层级落到进程单一信道。

    为什么不挂 console handler：旧实现给本 logger 挂裸 ``StreamHandler``(stderr)，
    在 MCP server 进程里 stderr 被 daemon 重定向进 stdout 兜底日志
    (``.debug/sr_od_mcp/main_server.log``)，而框架日志走 ``.log/mcp_server.log``
    ——同一行模型加载日志双写两文件，两文件 mtime 交替变新，哨兵按
    「mtime 最新」选活性信道时来回切换(日志信道漂移告警的直接写端)。

    单一信道走 ``'OneDragon.YOLO'`` 命名层级：propagate 到父 logger
    ``OneDragon``(框架 ``one_dragon.utils.log_utils`` 的 logger)，信道随进程
    身份自动归位——server 进程落到 mcp_server.log，GUI 进程落到 log.txt+console。

    边界：完全不经过框架 logger 的裸脚本里(YOLO 单测/下载工具且未 import
    框架 log_utils)，``OneDragon`` 无 handler，记录继续上传 root；root 也无
    handler 时仅 WARNING+ 经 lastResort 可见，INFO 进度行不可见(可设
    ``OD_YOLO_VERBOSE=false`` 静音，不受本改动影响)。
    """
    level = logging.INFO if _VERBOSE else logging.ERROR
    logger = logging.getLogger('OneDragon.YOLO')
    logger.setLevel(level)
    logger.propagate = True
    return logger


log = get_logger()
