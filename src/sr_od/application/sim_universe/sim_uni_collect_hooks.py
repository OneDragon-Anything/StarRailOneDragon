"""模拟宇宙 采集钩子(临时,采证后整段删除本文件 + 两处调用 + 对应 import,不留开关/参数)。

背景(2026-08-27 游戏 run 48 实证):昨天游戏版本更新后,模拟宇宙 app 内
①「选择祝福」三轮识别到祝福=[](祝福卡未渲染完就 OCR?无现场帧无法定位);
②「向下一层移动」未找到下一层入口。
本文件给上述两个失败分支各埋一个采集钩子:失败时存现场截图(bot 不停),下个实机 run 自动留证。

手法约定(SR 项目口径):
- 无条件触发:只在识别失败分支内调用,不加任何开关/配置;
- 内容哈希去重:按缩略灰度图哈希去重(简版 cw_shot_unique 手法,cw_observe.py 在禁触碰清单,故此处独立实现);
- 前置门(reader 锚点):画面态锚点不命中时「空读」是伪信号,直接跳过不存样本(runtime-iteration 随机态钩子分流判据);
- best-effort:钩子任何异常都不阻塞识别/对局。
"""
import hashlib
from pathlib import Path

import cv2
from cv2.typing import MatLike

from one_dragon.utils import cv2_utils
from one_dragon.utils.log_utils import log
from sr_od.application.sim_universe import sim_uni_screen_state
from sr_od.context.sr_context import SrContext

# 本模块在 src/sr_od/application/sim_universe/,parents[4]=仓库根;样本存 .debug/(已 gitignore)
_SHOT_DIR = Path(__file__).resolve().parents[4] / '.debug' / 'temp' / 'sim_universe' / 'shots'


def _shot_unique(image: MatLike, label: str) -> None:
    """按内容哈希去重存截图到 shots 目录。

    用 64x36 缩略灰度做哈希(而非原图字节):相机转动/微小动画会让原图字节必新,
    缩略哈希把近似相同的帧归并,一轮重试不会刷几十张近重复图。
    """
    try:
        small = cv2.resize(image, (64, 36))
        gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
        hash_ = hashlib.md5(gray.tobytes()).hexdigest()[:8]
        fp = _SHOT_DIR / f'{label}__{hash_}.png'
        if fp.exists():
            return
        _SHOT_DIR.mkdir(parents=True, exist_ok=True)
        cv2_utils.save_image(image, str(fp))  # RGB → save_image 内部转 BGR
        log.info('[sim-uni-collect] 已留证 %s', fp.name)
    except Exception as e:  # noqa: BLE001 采集 best-effort,失败不阻塞对局
        log.info('[sim-uni-collect] 留证失败 label=%s err=%s', label, e)


def collect_bless_empty(ctx: SrContext, screen: MatLike, retry_times: int) -> None:
    """采集钩子①:「选择祝福」识别到空列表时存现场截图。

    :param ctx: 上下文
    :param screen: 当前游戏截图(RGB)
    :param retry_times: 节点重试次数(轮次上下文,进文件名便于区分同一次 op 内第几轮)
    """
    # 前置门:不在选择祝福页(title 未命中)时空列表是过渡帧伪信号,跳过
    if not sim_uni_screen_state.in_sim_uni_choose_bless(ctx, screen):
        return
    _shot_unique(screen, f'bless_empty_retry{retry_times}')


def collect_next_floor_miss(screen: MatLike, move_times: int, retry_times: int) -> None:
    """采集钩子②:「向下一层移动」未匹配到任何下层入口图标时存现场截图。

    :param screen: 当前游戏截图(RGB);调用点已在 is_normal_in_world 分支内(大世界锚点天然命中)
    :param move_times: 已移动次数(上下文)
    :param retry_times: 节点重试次数(上下文)
    """
    _shot_unique(screen, f'next_floor_miss_m{move_times}_r{retry_times}')
