# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

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
        # OCR 偶 garble「生命值」→「命值」(missing 生);两形态都匹配(2026-08-07 实跑 on_round_end hp=0 根因)。
        for kw in ('生命值', '命值'):
            if kw in t:
                m = re.search(kw + r'\s*(\d+)', t)
                if m:
                    v = int(m.group(1))
                    if HP_MIN <= v <= HP_MAX:
                        return v
    return None


def parse_streak(ocr_texts: list[str]) -> int:
    """结算屏「连胜×N」/「连败×N」→ 带符号 streak(连胜 + / 连败 − / 未读到 0;纯函数可单测)。

    fixture 核实(2026-08-11):结算屏 OCR 含 '连胜×0' 形态,**前缀连胜/连败 = 方向**(read_streak
    备战只读 magnitude 无方向)。OCR 偶把 × 读成 x/X/*;前缀与尾随数字在同一 token。
    """
    for t in ocr_texts:
        if '连胜' in t or '连败' in t:
            m = re.search(r'(\d+)', t)
            if m:
                n = int(m.group(1))
                return n if '连胜' in t else -n
    return 0


def read_round_outcome(ctx: SrContext, screen: MatLike, *, plane: int, round_num: int,
                       comp_tag: str, node_type: str = '普通战斗'):
    """结算屏 → ``RoundOutcome``(观测回路 P1.5;``on_round_end`` 输入)。

    OCR 全屏 → ``parse_settlement_hp`` 得 hp_after;解析成功 hp_confidence=1.0(进 trend),失败 0.0
    (< ``HP_CONFIDENCE_THRESHOLD`` 不进 trend,防噪声)。plane/round_num/comp_tag/node_type 由调用方
    (loop,知当前节点 + ``session.target_comp``)传入 —— 结算屏本身不暴露这些。

    ✅ 已接线(2026-08-07 起):battle_loop._record_round_outcome(分支3)每轮胜结算屏调用 →
    strategy.on_round_end → performance.record + telemetry.record_outcome(2026-08-16 补)。
    node_type:结算屏含「首领」→ boss,否则普通战斗(粗档;boss/elite 细分待节点追踪 refine)。
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
        streak=parse_streak(ocr_texts),   # 结算「连胜×N」前缀=方向(C 杠杆 2/3;fixture 核实 2026-08-11)
    )
