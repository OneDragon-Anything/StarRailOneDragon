"""货币战争 结算屏观测(P1.5 观测回路):战后小队 HP。

结算屏(战斗后「挑战结束/数据统计/继续挑战」)展示战后小队 HP「小队生命值<N>」+ 总伤害等
(2026-08-05 实跑 OCR 确认形态:['挑战结束','战斗','小队生命值71i','数据统计','连胜×0','继续挑战'])。
``parse_settlement_hp`` 纯函数(可单测);``read_round_outcome`` OCR 全屏调它 → ``RoundOutcome``
(``on_round_end`` 输入,性能 trend 用)。node_type/comp_tag/plane/round 由调用方(loop)传入
(结算屏不暴露这些)。

共享常量(HP_MIN/HP_MAX)在 ``cw_obs_core``。本模块被 ``cw_observation`` re-export。
"""
from __future__ import annotations

import re

from cv2.typing import MatLike

from sr_od.application.currency_war.cw_obs_core import HP_MAX, HP_MIN
from sr_od.context.sr_context import SrContext


def parse_settlement_hp(ocr_texts: list[str]) -> int | None:
    """结算屏「小队生命值<N>」→ hp_after(纯函数,可单测;P1.5)。

    取含「生命值」的文本,解析其**紧邻后方**的数字(``生命值\\s*(\\d+)``)—— 紧邻而非首部/尾部,
    防「每损失20点小队生命值获得5」(投资策略描述,偶同屏)误取 20/5。越界(HP_MIN..HP_MAX)→ 丢弃。
    """
    for t in ocr_texts:
        if '生命值' in t:
            m = re.search(r'生命值\s*(\d+)', t)
            if m:
                v = int(m.group(1))
                if HP_MIN <= v <= HP_MAX:
                    return v
    return None


def read_round_outcome(ctx: SrContext, screen: MatLike, *, plane: int, round_num: int,
                       comp_tag: str, node_type: str = '普通战斗'):
    """结算屏 → ``RoundOutcome``(观测回路 P1.5;``on_round_end`` 输入)。

    OCR 全屏 → ``parse_settlement_hp`` 得 hp_after;解析成功 hp_confidence=1.0(进 trend),失败 0.0
    (< ``HP_CONFIDENCE_THRESHOLD`` 不进 trend,防噪声)。plane/round_num/comp_tag/node_type 由调用方
    (loop,知当前节点 + ``session.target_comp``)传入 —— 结算屏本身不暴露这些。

    ⚠️ P1.5 组件:本函数已就位 + 单测,但 ``battle_loop`` 的 on_round_end 接线(结算检测 → 调本函数 →
    ``strategy.on_round_end``)留下局部署(避免杀当前验证 match);node_type 推断暂粗(默认普通战斗,
    boss/elite 需节点追踪,后续 refine)。
    """
    from sr_od.application.currency_war.cw_performance import RoundOutcome
    ocr_texts = [r.data for r in ctx.ocr_service.get_ocr_result_list(
        image=screen, rect=None, crop_first=False)]
    hp = parse_settlement_hp(ocr_texts)
    # 失败结算屏(「挑战失败」= 团灭)→ hp_after=0 确定(parse_settlement_hp 在失败屏常读到
    # 「生命值❤!」等非数字 → None,但失败 = hp 0 是 ground truth)。boss 结算屏「挑战结束」无
    # 「生命值」前缀(只裸数字)→ 暂 conf=0(后续实机核实 boss 结算屏 hp 位置 refine)。
    if hp is None and any('挑战失败' in t for t in ocr_texts):
        hp = 0
    return RoundOutcome(
        round_num=round_num, plane=plane, node_type=node_type, comp_tag=comp_tag,
        hp_after=hp if hp is not None else 0,
        hp_confidence=1.0 if hp is not None else 0.0,
    )
