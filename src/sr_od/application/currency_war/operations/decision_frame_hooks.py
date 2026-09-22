"""货币战争 决策帧截图留证钩子 —— [留证钩子·常驻]。

**层次定位(用户裁定)**:本钩子是**识别源头缺陷的仲裁留证**,不是遥测
替代——决策依据的结构化重建才是主路径(刷后黑板重建 / K 回退显影等,
各自在飞批次承载)。截图兜的是「识别层自身漏读/误读时,结构化数据无法
自证」的形态:留的是**识别完成点的原始画面**(牌面/读数解析的仲裁基准),
判读时以本帧为 ground truth 对拍结构化行,而不是拿截图重新决策。

背景(P35 局复盘缺口):复盘遇「OCR 文本与牌面解析对不上」时无画面
实锤。本钩子在识别完成点无条件留原始帧,文件名 ts 与旧流决策行行 ts
(秒级)对齐还原归属(行写入已随删除波 1 退役;帧留证钩子保留——
识别仲裁基准与账本形态无关)。

挂点(2 类,均为识别完成点的原始帧):
1. 商店入口观察帧(商店画面 op 观察 node 入口观察刚完成时,每访问
   一帧;牌面解析的仲裁基准)——刷新完成后的重观察与挂点 1 同点自然
   覆盖(刷新终结 = 访问交回 → 下一次入口观察);
2. 事件 overlay 命中帧(cw_loop 浮层分发分支命中时一帧)。

(原挂点「部署执行帧」随部署机画面 op 退役消失;原装配槽
``set_decision_frame_dir`` 零消费随批退役拆除——写根恒生产公式。)

预算与治理(留证钩子形态:无条件触发,不留开关/参数):
- 每帧成本 = 一次内存截图落盘(挂点已有帧直接复用,不截新图),<100ms;
  挂点均为决策帧(段级/分支命中级,非每轮全图 OCR 级高频);
- 体积治理:每挂点(tag 维度)滚动保留最近 _KEEP_PER_TAG 帧,写入后删旧,
  防长局商店段循环多帧刷爆磁盘;
- 异常/冲突帧走既有 obs_conflict 通道不变,本钩子不替代;
- best-effort:钩子任何异常不阻塞对局推进。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from cv2.typing import MatLike

from one_dragon.utils import cv2_utils
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    from one_dragon.base.operation.operation import Operation

# 每挂点保留最近帧数(滚动删除旧文件;40 帧 × ~1-2MB ≈ 80MB/挂点上限)
_KEEP_PER_TAG = 40


def _out_dir(run_id: str) -> Path:
    """决策帧目录现算(生产公式;既有测试以 monkeypatch
    ``get_project_root`` 作落盘重定向缝,缝保持活读=不失效)。"""
    return (get_project_root() / '.debug' / 'temp' / 'currency_war'
            / 'decision_frames' / run_id)


def _prune_old(dir_path: Path, tag: str) -> None:
    """按 tag 维度滚动删除,保留最近 _KEEP_PER_TAG 帧(文件名 ts 前缀字典序=时间序)。"""
    mine = sorted(p for p in dir_path.iterdir()
                  if p.is_file() and p.name.endswith(f'_{tag}.png'))
    for p in mine[:-_KEEP_PER_TAG] if len(mine) > _KEEP_PER_TAG else []:
        p.unlink(missing_ok=True)


def save_decision_frame(op: Operation, tag: str,
                        screen: MatLike | None = None) -> str | None:
    """识别完成点原始帧留证(常驻留证钩子,无条件触发;仲裁兜底,见模块头层次定位)。

    :param op: 宿主 op(取 telemetry run_id 做目录 run 标记;screen 缺省时
        用 op.screenshot() 截新帧——挂点已有帧时显式传入,避免二次截图错帧)
    :param tag: 挂点名(如 shop_entry/deploy/overlay_partner),同 tag 滚动治理
    :param screen: 当前游戏截图(RGB);None 时 op.screenshot() 现截
    :return: 落盘 PNG 文件名(ts 秒级命名);None=跳过/失败
    """
    try:
        from sr_od.application.currency_war.telemetry.state import current_run_id
        run_id = current_run_id() or 'norun'
        out = _out_dir(run_id)
        out.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        stem = (f'{now.strftime("%Y%m%d_%H%M%S")}_{now.microsecond // 1000:03d}'
                f'_{tag}')
        if screen is None:
            screen = op.screenshot()
        if screen is None:
            return None
        fn = f'{stem}.png'
        cv2_utils.save_image(screen, str(out / fn))
        _prune_old(out, tag)
        return fn
    except Exception as e:  # noqa: BLE001  留证 best-effort,失败不阻塞对局
        log.warning('[cw-dframe] 决策帧落盘失败 tag=%s: %s', tag, e)
        return None
