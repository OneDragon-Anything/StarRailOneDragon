"""货币战争 采购拍值平表 + EffectSpec 偏置通道(R5;自 decision_v2.scoring
迁入 strategies/impl——pick 族决策钩子消费面的活单一源)。

蓝图 §4.2-R5:拍值打分钩子(box_card/star_tome/wish_trial,原 default_
strategy 内联魔数)降为「名字→标定权重」数据平表;本表 = 唯一标定源,
钩子消费面读表取值(数值原样迁移,行为零漂移;战场族条目推迟挂账)。
decision_v2.scoring 已随统一迁移批 ② 删除,本模块为唯一单一源。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.kernel.cw_game_state import (
    board_state_of,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    StrategySession,
)


@dataclass(frozen=True)
class PickBiasTable:
    """单帧单发采购拍值平表(R5;数值出处 = 退役前策略钩子内联值,git prior art)。"""
    # 星徽秘典四选一(decide_star_tome)
    tome_target_faction: float = 40.0     # 终局线需要的阵营星徽
    tome_board_hit: float = 8.0           # 板上已有该阵营(每件;边际高)
    tome_framework_faction: float = 15.0  # 过渡配方框架阵营(双轨期)
    # 祈愿试炼选卡(decide_wish_trial)
    wish_gold: float = 25.0               # 金币类(直接经济,阵容无关)
    wish_faction: float = 20.0            # target/框架阵营相关词
    wish_operation: float = 10.0          # 刷新/购买操作向(与 DP 攒息协同)
    # 武装箱四选一常数(box_key_equip/box_key_material)已随该面迁共享机器
    # cw_equip_value 序数分档制退役(armory-box-value);材料通用性表同批退役


PICK_BIAS = PickBiasTable()


def effect_pick_bias(session: StrategySession, option_name: str) -> float:
    """EffectSpec → 拍值偏置通道(方向层消费接入;R5 消费面)。

    - 输入 = GameState.effects 在场效果条目(board_state_of(session).effects,
      单一实例正本);按条目 spec 的
      ``notes`` 声明偏置选项名(平表外挂,数值随实采/sim 标定批填,
      **缺省 0 = 无偏置**,不猜值——strategy-work「决策规则数学先行」门);
    - 战场族(BATTLEFIELD category)推迟:战场改写类偏置语义待执行预判批
      (``w610_gold_digger_spec`` P2-2)定义,本通道暂只认 ECONOMY/STATE 族;
    - pending=True 条目不参与(二义未定谳,消费端走保守支,cw_effect_
      inventory 契约)。
    """
    del option_name   # 通道预留:选项名级偏置随标定批启用(当前 spec 级=0)
    inv = board_state_of(session).effects
    bias = 0.0
    for entry in getattr(inv, 'entries', ()):
        spec = getattr(entry, 'spec', None)
        if spec is None or getattr(spec, 'pending', False):
            continue
        if getattr(spec, 'category', None) is not None:
            if getattr(spec.category, 'value', '') not in ('economy', 'state'):
                continue   # 战场族推迟(设计挂账,不猜语义)
    return bias
