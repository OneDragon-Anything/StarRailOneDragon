"""sim 重做·战斗结算模型(M12/M13/M14,第一期:随机胜负 + 随机扣血)。

设计正本 = ``docs/develop/sr_od/application/currency_war/sim/sim-design.md``
(§2.2 战斗结算/§8.2 未建模申报)第一期口径:

- **U01 第一期定案**:战斗输出 = 纯随机面,不消费任何板面/战力/敌人
  特征——胜负 = 均匀伯努利(P(win)=0.5);败局扣血 = 整数均匀采样,
  常量区间 ``[SIM_HP_LOSS_MIN, SIM_HP_LOSS_MAX]``(初值 [23,70];锚定
  规则 = 实测「单次败局总扣血」样本域 min/max,在案散点 P2r1 −23 /
  遭遇 −28 / P3 遭遇 −70 定界;采样对象 = 总扣血,不以分量域定界;
  新实测样本并入后按同规则重估常量)。**sim-only 简化档**:与实机
  战斗无机制对应,禁作任何实机行为外推(逐局披露当用区间与采样值);
- **U03 定稿口径**:「基础伤害 + 未完成进度伤害」分项第一期随 U01
  直扣不拆,结构字段置 None 占位并随局披露不可分;
- 败 → 挑战进度均匀采样(服务遭遇达标制等结构消费);胜 → 进度记
  达标;
- **M14 结构规则**:HP 只在节点战斗失败时扣;**普通奖励关例外恒胜
  白拿**(奖励关不需要战力,不存在败局;后端结算分支承载改写,输出面
  ``SIM_REWARD_FREE_WIN_FACE``);扑满奖励关不掉血(M17);首次 hp≤0
  保底剩 1(保底位 = 容器 ``hp_floor_triggered``,全局机制);再次归零
  → 局终;HP 跨位面继承不重置。

随机流键(后端侧装配):``M13/{plane}/{round}``(胜负掷点 + 扣血/进度
采样同流依序消耗)。
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from sr_od.application.currency_war.kernel.cw_game_state import GameState
from sr_od.application.currency_war.sim.cw_sim_base import obs_sig, sim_evidence

#: 败局扣血均匀区间下界(实测单次败局总扣血散点域 min;锚 P2r1 −23,
#: M13 锚定规则;新样本并入按同规则重估)。
SIM_HP_LOSS_MIN: int = 23

#: 败局扣血均匀区间上界(散点域 max;锚 P3 遭遇 −70,同上)。
SIM_HP_LOSS_MAX: int = 70

#: 胜负均匀伯努利概率(U01 定案 P=0.5,非战力映射)。
SIM_WIN_PROB: float = 0.5

#: 输出面简化档标记(随局披露;sim-only 简化档禁外推)。
SIM_BATTLE_FACE: str = 'sim_random_face_u01'

#: 普通奖励关恒胜白拿的输出面标记(奖励关不需要战力 = 用户账本 408 行
#: 裁定,kernel ``cw_reward_node.py`` 裁定权威行单一源;不存在败局,
#: 判读侧据此区分「真随机战斗面」并挡外推)。
SIM_REWARD_FREE_WIN_FACE: str = 'sim_reward_free_win_face'


@dataclass(frozen=True)
class BattleOutcome:
    """战斗类节点结构化结算输出(M12 集合;判定来源 = 第一期随机面)。"""

    #: 胜负(均匀伯努利;胜 → 挑战进度记达标)
    won: bool
    #: 挑战进度:胜 = 1.0(达标);败 = 均匀采样 [0,1)(遭遇达标制等
    #: 结构消费位;数值本身无实机对应,简化档)
    progress: float
    #: 基础伤害分项(U03:第一期恒 None,随 U01 直扣不拆,披露不可分)
    base_damage: int | None
    #: 未完成进度伤害分项(同上,恒 None)
    progress_damage: int | None
    #: 本节点 HP 变化量(恒 ≤0;败 = 区间均匀采样总扣血;胜 = 0)
    hp_delta: int
    #: 输出面标记(恒 ``SIM_BATTLE_FACE``;判读侧据此挡外推)
    face: str


def settle_battle(rng: random.Random, *, plane: int, round_num: int) -> BattleOutcome:
    """战斗类节点结算(随机输出面;``M13/{plane}/{round}`` 流,胜负掷点
    先于扣血/进度采样,依序消耗)。"""
    won = rng.random() < SIM_WIN_PROB
    if won:
        return BattleOutcome(won=True, progress=1.0, base_damage=None,
                             progress_damage=None, hp_delta=0,
                             face=SIM_BATTLE_FACE)
    hp_delta = rng.randint(SIM_HP_LOSS_MIN, SIM_HP_LOSS_MAX)
    progress = rng.random()
    return BattleOutcome(won=False, progress=progress, base_damage=None,
                         progress_damage=None, hp_delta=-hp_delta,
                         face=SIM_BATTLE_FACE)


def apply_hp_outcome(gs: GameState, outcome: BattleOutcome) -> tuple[bool, bool]:
    """M14 折算:败局扣血写容器 + 0hp 保底/局终判定。

    Returns:
        ``(floor_triggered_now, dead)``:本次是否触发首次保底(容器
        ``hp_floor_triggered`` 事件位同时翻真);``dead`` = 保底已用过
        再次归零 → 整局结束(引擎据此进 game_over)。
    """
    if outcome.won or outcome.hp_delta == 0:
        # 胜局/零扣血也落一行等值 hp 写:hp 写流 = 「每战斗结算恰一条 +
        # 选卡落地即时腿逐笔」的测试面(first_run 容器不变式②——写流与
        # hp_trail 全序同构,每写恰一条轨迹),等值跳写会破坏同构——实机
        # 对偶 = 结算屏恒显 hp,无「胜利就不读 hp」的形态。hp 未观察
        # (None)= 无值可写,照旧零写(防御面;正常局 reset 即种)。
        hp_now = gs.hp.value
        if hp_now is not None:
            gs.observe(gs.hp, int(hp_now),
                       evidence=sim_evidence('battle:hp'),
                       sig=obs_sig(group_id='sim:battle'))
        return False, False
    hp_after = int(gs.hp.value or 0) + outcome.hp_delta
    tag = 'battle:hp'
    if hp_after > 0:
        gs.observe(gs.hp, hp_after, evidence=sim_evidence(tag),
                   sig=obs_sig(group_id='sim:battle'))
        return False, False
    floor_used = bool(gs.hp_floor_triggered.value)
    if not floor_used:
        # 首次 0hp 保底剩 1(全局机制;事件位翻真 = 保底已消费)
        gs.observe(gs.hp_floor_triggered, True,
                   evidence=sim_evidence('battle:hp_floor'),
                   sig=obs_sig(group_id='sim:battle'))
        gs.observe(gs.hp, 1, evidence=sim_evidence(tag),
                   sig=obs_sig(group_id='sim:battle'))
        return True, False
    gs.observe(gs.hp, 0, evidence=sim_evidence(tag),
               sig=obs_sig(group_id='sim:battle'))
    return False, True
