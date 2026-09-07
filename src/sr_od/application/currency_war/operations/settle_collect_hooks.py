"""货币战争 结算屏时序采集钩子 —— [临时采集批,本文件整段可删]。

目标:结算屏 C1-C6 标定(「小队生命值结算说明」悬浮面板出现条件 / 挑战进度条 /
战败布局 / 读点时序)。需要结算屏**停留期间的时间序列帧**(面板出现/消失相对
时序),不能用内容哈希去重——去重会把面板变化帧丢掉。改用「每次进入结算屏
分支存一帧」:对局 loop 在结算屏停留期间每 ~1.5-2s 重入分支一次,天然形成
2s 间隔序列;帧名带单调序号 + 墙钟时间,与 .log/mcp_server.log 的
[cw-loop][battle_end] / 结算观测行(cw-bwait)对齐即可还原轮次归属。

生命周期(SR 约定,无开关无参数):
- 采集清单完成(结论写入 redesign/REAL_MACHINE_COLLECTION_1.md)后:删本文件
  整段 + 删 cw_loop 分支 3 内一行接线 + 删产物
  fixtures/settle_ocr/window_batch/h_*.png,不留任何开关位;
- best-effort:钩子任何异常不阻塞对局推进;帧总数封顶防磁盘刷爆。
"""
from __future__ import annotations

import time

from cv2.typing import MatLike

from one_dragon.utils import cv2_utils
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log

# 产物落点(与外部 2s 截屏环同目录,便于离线合并对齐;h_ 前缀区分来源)
_OUT_DIR = (get_project_root() / '.debug' / 'temp' / 'currency_war' / 'redesign'
            / 'fixtures' / 'settle_ocr' / 'window_batch')

# 帧总数封顶:一局 6+ 场战斗 × 每场结算停留 ~10-30 轮,~300 帧足够;防死循环刷盘
_MAX_FRAMES = 400

# 已落盘帧数(进程内计数;钩子为临时件,不做持久化)
_FRAME_COUNT = 0


def settle_frame_collect(screen: MatLike | None) -> str | None:
    """结算屏时序帧采集([临时采集] 分类,清单完成后删整段)。

    调用点:cw_loop 分支 2「点击空白加速/处继续」、分支 3「按钮-继续挑战」、
    分支 1f 失败结算页、分支 3b 终局结算链(前往结算/下一页/下一步/返回货币战争,
    每页点前一帧)。1f/3b 为败局链补采分支(C4 战败布局缺口,跑局批实证败局
    零 h_ 帧)——即每个结算屏停留轮/每页各存一帧,不做哈希去重(要保留面板
    出现/消失的时序差分);由 loop 的自然重入节奏(~1.5-2s/轮)提供采样间隔。

    :param screen: 当前游戏截图(RGB);None 直接跳过
    :return: 落盘文件名;None = 落盘失败 / 超封顶
    """
    global _FRAME_COUNT
    if screen is None or _FRAME_COUNT >= _MAX_FRAMES:
        return None
    try:
        _OUT_DIR.mkdir(parents=True, exist_ok=True)
        _FRAME_COUNT += 1
        fn = f'h_{_FRAME_COUNT:03d}_{time.strftime("%H%M%S")}.png'
        cv2_utils.save_image(screen, str(_OUT_DIR / fn))
        log.info('[cw-settle-hook] 结算屏时序帧 %s', fn)
        return fn
    except Exception as e:  # noqa: BLE001  采集 best-effort,失败不阻塞对局
        log.warning('[cw-settle-hook] 落盘失败: %s', e)
        return None
