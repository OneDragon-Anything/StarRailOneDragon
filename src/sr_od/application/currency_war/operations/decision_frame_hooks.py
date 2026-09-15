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

挂点(4 类,均为识别完成点的原始帧):
1. 商店入口观察帧(run_buy_waves 每段循环入口观察刚完成时,每段一帧;
   牌面解析的仲裁基准)——刷新完成后的重观察与挂点 1 同点自然覆盖
   (刷新终结 → 下一次入口观察);
2. 部署执行帧(CwScreenDeploy.deploy 主流程一帧);
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
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cv2.typing import MatLike

from one_dragon.utils import cv2_utils
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    from one_dragon.base.operation.operation import Operation

# 每挂点保留最近帧数(滚动删除旧文件;40 帧 × ~1-2MB ≈ 80MB/挂点上限)
_KEEP_PER_TAG = 40


# ===== 决策帧落盘根装配槽(三遥测写根的第三槽;三审二波 F2)=====
# 为什么是槽:决策帧写根原恒锚生产树(.debug/temp/currency_war/
# decision_frames/),假环境只靠 harness monkeypatch 私函数 _out_dir 改道
# ——不经 harness 的假局驱动方(易失离线 runner/未来 sim 批真 op 驱动)
# 会把 kind=observation_evidence 的观察证据静默写进生产树,正是写端根
# 隔离(裁定机制见 op_journal.set_journal_dir 注)要防的
# 静默混流形态换流复发(出处:.debug/temp/currency_war/attacks/
# three_review_20260908/三审报告-第二波.md F2,**易失产物**待 ADR 回填)。
# 与既有两槽(telemetry/state.set_recorder_replay_dir /
# op_journal.set_journal_dir)同构:缺省 None = 生产路径逐位不变;驱动方
# 显式接指假局档案根,teardown 复位(进程全局槽,残留会把后续帧带去
# 假局根)。零生产行为变更:生产全程无设槽点,生产公式逐位保留(守卫
# = test_cw_telemetry_root_slot 的缺省路径锁 + 生产树零设槽点扫描
# TestZeroProductionWiring)。
_DIR_OVERRIDE: Path | None = None


def set_decision_frame_dir(path: Path | None) -> None:
    """接通/复位决策帧落盘根(缺省 None = 生产路径)。

    与 :func:`telemetry.state.set_recorder_replay_dir`、
    :func:`telemetry.op_journal.set_journal_dir` 同装配纪律:缺省关、
    驱动方显式接通、teardown 复位。三槽同点接指同一假局档案根
    (harness 先例 = fixtures/cw_harness.fake_p1_run)——漏接一件即
    部分隔离,该驱动方的遥测流仍触生产树。
    """
    global _DIR_OVERRIDE
    _DIR_OVERRIDE = Path(path) if path is not None else None


def _out_dir(run_id: str) -> Path:
    """决策帧目录现算(根槽优先;槽是函数内读取,测试可 monkeypatch
    槽变量后立即生效,不经模块 import 绑定快照——journal 槽
    ``_journal_path`` 同纪律)。

    槽缺省回落生产公式**活读** ``get_project_root``:既有测试以
    monkeypatch ``get_project_root`` 作落盘重定向缝
    (test_cw_decision_frame_hooks 同款),缝保持活读=不失效;根槽是
    追加缝,不改写既有缝语义(journal 槽缺省回落 ``_JOURNAL`` 常量
    同款先例)。"""
    if _DIR_OVERRIDE is not None:
        return _DIR_OVERRIDE / 'decision_frames' / run_id
    return (get_project_root() / '.debug' / 'temp' / 'currency_war'
            / 'decision_frames' / run_id)


def _prune_old(dir_path: Path, tag: str, suffix: str = '.png') -> None:
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
    :return: 落盘文件名(与旧流决策行行 ts 秒级同源,ts 面语义不变);None=跳过/失败

    假环境改形(契约三则「留证面改形」):观察源端口
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
        src = observation_source()
        if src is not None and _DIR_OVERRIDE is None:
            # 拒写守卫(写端根隔离,同上裁决):假环境观察证据 +
            # 未接根槽 = 三审二波 F2 的静默混流形态(证据落生产
            # decision_frames 树)。宁缺勿混——证据缺失在消费端表现为
            # 文件不存在(可发现),混流是静默污染(不可发现);生产
            # 路径零感知(生产 observation_source 恒 None 不进本分支)。
            # 判定位次须先于 mkdir:守卫拒写连目录也不得建(空目录
            # 同为生产树写痕迹)。
            log.warning('[cw-dframe] 假环境观察证据未接决策帧根槽,'
                        '拒写 tag=%s(驱动方需 set_decision_frame_dir)',
                        tag)
            return None
        out = _out_dir(run_id)
        out.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        stem = (f'{now.strftime("%Y%m%d_%H%M%S")}_{now.microsecond // 1000:03d}'
                f'_{tag}')
        if src is not None:
            payload: dict[str, Any] = {'kind': 'observation_evidence', 'tag': tag,
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
