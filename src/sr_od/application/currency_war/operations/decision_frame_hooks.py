"""货币战争 决策帧截图留证钩子 —— [留证钩子·常驻]。

**层次定位(用户裁定)**:本钩子是**识别源头缺陷的仲裁留证**,不是遥测
替代——决策依据的结构化重建才是主路径(刷后黑板重建 / K 回退显影等,
各自在飞批次承载)。截图兜的是「识别层自身漏读/误读时,结构化数据无法
自证」的形态:留的是**识别完成点的原始画面**(牌面/读数解析的仲裁基准),
判读时以本帧为 ground truth 对拍结构化行,而不是拿截图重新决策。

背景(P35 局复盘缺口):复盘遇「OCR 文本与牌面解析对不上」时无画面
实锤。本钩子在识别完成点无条件留原始帧,文件名 ts 与 decisions.jsonl
行 ts(秒级)+ run_id 对齐还原归属。

挂点(4 类,均为识别完成点的原始帧):
1. 商店入口观察帧(run_buy_waves 每段循环入口观察刚完成时,每段一帧;
   牌面解析的仲裁基准)——刷新完成后的重观察与挂点 1 同点自然覆盖
   (刷新终结 → 下一次入口观察);
2. 部署执行帧(CwOpDeploy.deploy 主流程一帧);
3. 事件 overlay 命中帧(cw_loop 0 系浮层分支命中时一帧)。

预算与治理(留证钩子形态:无条件触发,不留开关/参数):
- 每帧成本 = 一次内存截图落盘(挂点已有帧直接复用,不截新图),<100ms;
  挂点均为决策帧(段级/分支命中级,非每轮全图 OCR 级高频);
- 体积治理:每挂点(tag 维度)滚动保留最近 _KEEP_PER_TAG 帧,写入后删旧,
  防长局商店段循环多帧刷爆磁盘;
- 异常/冲突帧走既有 obs_conflict 通道不变,本钩子不替代;
- best-effort:钩子任何异常不阻塞对局推进。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from cv2.typing import MatLike

from one_dragon.utils import cv2_utils
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    from one_dragon.base.operation.operation import Operation

# 每挂点保留最近帧数(滚动删除旧文件;40 帧 × ~1-2MB ≈ 80MB/挂点上限)
_KEEP_PER_TAG = 40


def _out_dir(run_id: str):
    return (get_project_root() / '.debug' / 'temp' / 'currency_war'
            / 'decision_frames' / run_id)


def _prune_old(dir_path, tag: str, suffix: str = '.png') -> None:
    """按 tag 维度滚动删除,保留最近 _KEEP_PER_TAG 帧(文件名 ts 前缀字典序=时间序)。"""
    mine = sorted(p for p in dir_path.iterdir()
                  if p.is_file() and p.name.endswith(f'_{tag}{suffix}'))
    for p in mine[:-_KEEP_PER_TAG] if len(mine) > _KEEP_PER_TAG else []:
        p.unlink(missing_ok=True)


def save_decision_frame(op: Operation, tag: str,
                        screen: MatLike | None = None) -> str | None:
    """识别完成点原始帧留证(常驻留证钩子,无条件触发;仲裁兜底,见模块头层次定位)。

    :param op: 宿主 op(取 telemetry run_id 做目录 run 标记;screen 缺省时
        用 op.screenshot() 截新帧——挂点已有帧时显式传入,避免二次截图错帧)
    :param tag: 挂点名(如 shop_entry/deploy/overlay_partner),同 tag 滚动治理
    :param screen: 当前游戏截图(RGB);None 时 op.screenshot() 现截
    :return: 落盘文件名(与 decisions.jsonl 行 ts 秒级可对齐);None=跳过/失败

    假环境改形(T-120 方案 §2.3 契约三则「留证面改形」):观察源端口
    在场(假环境)时,「识别完成点原始帧」不存在语义(无读图)——留证
    改落**结构化观察 JSON**(观察内容快照,消费端按来源分型),不再落
    PNG(stub 帧落图 = 假证据)。观察载荷经 duck-typed
    ``evidence_snapshot(tag)`` 从端口实现方取(协议不折叠载荷形状;
    实现方无此能力 = 只落定位行)。
    """
    try:
        from sr_od.application.currency_war.cw_game_ports import (
            observation_source,
        )
        from sr_od.application.currency_war.telemetry.state import current_run_id
        run_id = current_run_id() or 'norun'
        out = _out_dir(run_id)
        out.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        stem = (f'{now.strftime("%Y%m%d_%H%M%S")}_{now.microsecond // 1000:03d}'
                f'_{tag}')
        src = observation_source()
        if src is not None:
            payload: dict = {'kind': 'observation_evidence', 'tag': tag,
                             'ts': now.isoformat(timespec='seconds'),
                             'run_id': run_id}
            snap = getattr(src, 'evidence_snapshot', None)
            if callable(snap):
                loaded = snap(tag)
                if isinstance(loaded, dict):
                    payload.update(loaded)
            fn = f'{stem}.json'
            (out / fn).write_text(json.dumps(payload, ensure_ascii=False,
                                             default=str),
                                  encoding='utf-8')
            _prune_old(out, tag, suffix='.json')
            return fn
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


# 供测试与审计读(单一源:保留帧数常量)
KEEP_PER_TAG = _KEEP_PER_TAG
