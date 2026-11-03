"""开局血量(hp)初值表——遥测实证的先验,替代「开局 hp=None 诚实未知」的实证过档。

**数据出处 = hp0_survey 普查(2026-09-06,
`.debug/temp/currency_war/hp0_survey/报告.md`,133 局对局档案逐局 p1-r1 读数,
settlement 源 hp_confidence=1.0)**。

与已废止的「开局兜底 100」(引入、废止)的本质区别:
- 兜底 100 是无证据假值(实测定值非 100,毒化遥测);
- 本表只填**实证过的档**:A8/难度 108 下基础值 82(109 局零方差)、
  词缀「开局不利」恒 −20 → 62(7/7 局)。**其他难度/数值难度无数据,
  保持 None(诚实未知),禁外推**——133 局样本全为 A8/108,难度维度无法验证。

消费端 = ``cw_reconcile.reconcile_hp`` 开局分支(读不到且 session 无真值):
初值是**先验**不是真读——返回 readable=False,后续真值帧按既有新鲜度门
正常覆盖,禁覆盖真读。「时间刺客」不另设值(初值仍 82):它通过局内周期
扣血污染 1-1 读数(实测 r1=44/46,r2 回 84/86),不改初值;该污染的判读
由 hp 下行拒信/复现确认通道既有防线兜住,本表不碰判读。

词缀域写尾 HP 先验跟随回调(:func:`on_enemy_affixes_logic_write`)住本
模块 = 档表与现算函数的域归属(挂点 = ``cw_game_state._write_logic_frame``
enemy_affixes 分支,logic/logic_rand 两通道同经;观察写不经该宿主 =
零回调,deployed 写尾回调级联同契约)。T-45 敌后破坏删除分支的 HP 跟随
载体;姊妹卡退化(策略卡)同宿主复用,其 mid-run 获得态由回调内
「节点窗在动跳写」守卫承接——开局先验通道 mid-run 停用,当期 hp
(真读/沿用/效果支付)不被覆写。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_game_state import ChannelSig

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )

#: 基础初值(A8/数值难度 108,无修正词缀;109 局零方差)。
OPENING_HP_BASE: int = 82

#: 数值难度实证档(唯一有数据的档;其他数值难度无数据不查表)。
_KNOWN_ENEMY_DIFFICULTY: int = 108

#: 职级实证档(133 局全 A8;其他职级无数据不查表)。
_KNOWN_SELECTED_DIFFICULTY: str = 'A8'

#: 确定性词缀修正(词缀识别键 = 简报 OCR 原名,affix_effects_data 注册表同名键;
#: 「开局不利」效果原文「游戏开始时,小队生命值减少20点」,7/7 局实测 82−20)。
_AFFIX_HP_DELTA: dict[str, int] = {
    '开局不利': -20,
}


def opening_hp_prior(briefing_affixes: list[str] | None,
                     selected_difficulty: str | None,
                     enemy_difficulty: int | None) -> int | None:
    """开局 hp 初值 = f(词缀集),限实证过的难度档。

    Args:
        briefing_affixes: 简报敌人词缀 OCR 原名(session.briefing_affixes;
            None/空 = 未采到,按无修正词缀处理——词缀读链失败时初值仍可给,
            与「无词缀局」同值 82,实证上无修正词缀档占 109/116)。
        selected_difficulty: 本局职级(session.selected_difficulty;'' = 未检测)。
        enemy_difficulty: 数值难度(session.enemy_difficulty;None = 未读到)。

    Returns:
        实证档内的初值(82/62);难度档无实证(A8/108 之外,含未读到)→ None。
    """
    if (selected_difficulty or '').strip() != _KNOWN_SELECTED_DIFFICULTY:
        return None
    if enemy_difficulty != _KNOWN_ENEMY_DIFFICULTY:
        return None
    affixes = set(briefing_affixes or [])
    hp = OPENING_HP_BASE
    for name, delta in _AFFIX_HP_DELTA.items():
        if name in affixes:
            hp += delta
    return hp


#: 词缀域写尾回调重算先验的渠道签名(obs 族 prior 子模;先例 =
#: cw_observation reconcile 先验写行同形,actor 换本域宿主)。
_HP_RESYNC_SIG: ChannelSig = ChannelSig(family='obs', actor='CwOpeningHp',
                                        mode='prior',
                                        quality={'hp': 'prior'})

#: 重算先验行 evidence 前缀(write_prior 强制 ``prior:`` 前缀;语义段
#: = 消失词缀触发,同一常量供测试断言,防散写字面量)。
AFFIX_HP_RESYNC_EVIDENCE: str = 'prior:affix_disable_hp'


def on_enemy_affixes_logic_write(gs: GameState, old_names: list[str] | None,
                                 new_names: list[str] | None,
                                 source: str) -> None:
    """词缀域逻辑写尾的 HP 先验跟随回调(T-45 敌后破坏删除分支;设计 =
    迭代 2026-09-23-invest-effects-calc T-45 设计稿 §2.3 裁决点 a,2026-10-18
    用户方案「词缀更新回调」+ 对抗轮 2 N1/N2 修法甲落定形态)。

    挂点 = ``cw_game_state._write_logic_frame`` enemy_affixes 分支尾
    (logic/logic_rand 两逻辑通道同经;**observe 覆盖不经该宿主 = 零回调**
    ——回归 deployed 写尾「观察写零回调」契约,对抗轮 2 N1 改判:live
    先验每读失败帧从当前名单懒算落储 + 首备战帧 hp 真读先于委派挂点,
    observe 触发反而把开局先验覆写到新鲜真值上)。数据流 = deployed
    写尾级联同构:按名单 diff 出消失词缀 → 命中 :data:`_AFFIX_HP_DELTA`
    → 以删除后词缀表经 :func:`opening_hp_prior` 现算 → 经
    ``GameState.write_prior`` 重算 HP 先验(写通道统一 prior 单一来源,
    对抗轮 2 N2 修法甲:不采 logic/logic_rand 来源继承——HP 域来源三叉
    会造成真值覆盖行为分裂;真读覆盖 prior = 静默采新零告警,先验永不过
    可信位 ``hp_decision_trusted_of`` fail-closed 底线不变)。

    跳写边界(全列,任一命中即零写):
    - ``old_names`` None(种子写/字段首写):diff 语义 = 全量消失候选,
      回调防种子误触发直接跳过;
    - **mid-run 节点窗在动**(``gs.node.value`` 非 None):节点窗在动 =
      已过开局窗,当期 hp 由真读/沿用/效果支付承载——开局先验重算对该态
      只有「静默踩踏」一个效果(策略卡退化可中途获得,其词缀删除写会
      触发本回调;词缀失效不追溯已结战斗的 HP,游戏语义同向),一律
      跳写 = 开局先验通道 mid-run 停用。开局窗(node 未锚)照旧重算:
      敌后破坏/退化开局选卡时 hp = 种子或先验,无真值可踩;
    - 消失词缀不命中 :data:`_AFFIX_HP_DELTA`(空 diff 同此):HP 与该词缀
      集零耦合,零 HP 写;
    - 现算返回 None(非实证难度档):先验表只填实证档禁外推,跳写。

    sim hp_trail 伪影披露(实现批裁定 = 接受伪影 + 披露):本回调重算
    改写 sim HP 后,``cw_sim_backend._hp_trail_append`` 的步界采样轨迹
    呈开局双值(先验值 → 重算值的跳变行,如 62 → 82)——不做回溯补行
    (kernel 回调反向感知 sim 步界 = 层级倒挂),A/B 遥测读开局 HP 时
    按「词缀失效局开局双值」判读。

    Args:
        gs: 局容器(写目标 = ``gs.hp``,先验输入 = 职级/数值难度现值)。
        old_names: 写前词缀名单(种子态 None)。
        new_names: 写后词缀名单(删除分支 = 剩余列表)。
        source: 宿主写 produced_by(契约对称形参,归因走写台账 evidence,
            与 ``on_deployed_logic_write`` 同款零消费面)。
    """
    if old_names is None:
        return   # 种子写防误触发(设计 §2.3 N5:None 档全量消失候选不判)
    if gs.node.value is not None:
        # mid-run 跳写守卫:节点窗在动 = 开局先验通道停用(宿主 docstring
        # 跳写边界 2;策略卡退化 mid-run 获得场景的残面处置——先验覆写
        # 当期 hp = 静默踩踏,禁)。
        return
    vanished = set(old_names or []) - set(new_names or [])
    if not vanished & set(_AFFIX_HP_DELTA):
        return   # 消失词缀不命中 HP 档(含空 diff)→ 零 HP 写
    prior = opening_hp_prior(list(new_names or []),
                             gs.selected_difficulty.value,
                             gs.enemy_difficulty.value)
    if prior is None:
        return   # 非实证档先验返 None → 跳写(禁外推,查表口径)
    gs.write_prior(gs.hp, prior, evidence=AFFIX_HP_RESYNC_EVIDENCE,
                   sig=_HP_RESYNC_SIG)
