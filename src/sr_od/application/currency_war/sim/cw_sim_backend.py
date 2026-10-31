"""sim 游戏后端 SimBackend(驱动反转;世界本体 + 画面状态机 + overlay 触发层)。

真流程(外层循环 + 画面 op + 动作 op + 策略器)当驱动者,本后端 = sim 世界:
组合持有 :class:`GameState`(禁子类——Field 通道与裸属性两套状态纪律
不得混于一体,决策输入形状不随运行模式漂移),自持实机不可观察的簿记
(采样去重集/overlay 队列/一次性标志/局结果面)。一实例一局。

**字段收敛判据**(容器一份,禁第三形态):实机可观察/影响玩法的世界事实
→ 容器 Field;生成器采样簿记 → 本后端私有。旧引擎 ``_Eng`` 三处双账
全部消灭:``plane``/``round_num`` → ``gs.node``;相位载荷(options/
supply/encounter/box/晶矿面板)→ 容器各 opts 槽(经 ``cw_screen_report``
同名上报函数送达,与实机观察同一条写通道,本后端不私持副本);
``streak_unsigned`` → 容器带符号连胜派生读 ``max(signed, 0)``。

**画面状态机**:状态 = (screen_info 档名,子态载荷)。转移源两类:
1. **动作后果声明**(声明化迭代主通道):动作 op 经
   ``cw_sim_ports.declare_world`` 喂入 :meth:`advance`,按
   ``decl.trigger`` 分派(键集单一源 = :data:`ADVANCE_TRIGGER_KINDS`,
   3.3 起 18 转移动作全量在表)——node_advance → 节点推进、
   battle_resolve → 战斗结算、选卡族/箱 → 各世界过程、``''`` → 纯
   画面转移;推进后按 ``decl.next_screen`` 等值对账画面档
   (:meth:`_reconcile_next_screen`)。
2. **点击源**(flow-seam 附录 B 边界登记:不入 kernel 事件集的推进型
   点击):简报下一步 / BOSS 简报点空白 / 位面过渡点空白 / 补给刷新 /
   开店。经端口 ``click_answer`` 感知。

**节点推进序列**(模块号流键坐标系):写 ``gs.node`` → 轮首收入
(kernel ``round_start_income`` 三分支,U04 败补消费容器 ``pending_loss``)
→ 位面开局环境发放分道(声明矿环境 → 声明入队 + 过期清理,其余 →
直发金)→ 商店自动全刷(整店锁跳过)→ overlay 队列检查 → offer
日程检查(U07 固定轮次 + 联席决策)→ 按节点类型呈现对应屏
(battle/reward → 备战档;奖励节点晶矿子态 = 面板矿 + 位面开局声明矿
同批合并,spheres 写一律过挂接入口
``cw_ore_channel.report_spheres_observed``;supply → 补给;encounter →
遭遇节点;boss → BOSS 简报)。节点经验在节点推进时入账
(NODE_XP_BY_TYPE 表原样);连胜转移在战斗结算后。

**overlay 触发层**(终态):判据 = kernel 值回调
(cw_faction_callbacks,deployed 逻辑写尾)→ 容器登记
(gs.screen_changes.pending)→ 呈现(问询时点懒呈现 + advance 纯转移
尾 + 节点窗起点,压住底层画面,选完返回)。一期目录:巨星/planner
(容器值回调判据)、开箱/专家/星徽(open_* 上报直登)、占卜屋/伙伴/
祈愿/阿哈(判据/选卡上报)。无 sim 观察分支族(partner/fortune/
wish_trial/star_tome/aha)呈现即卡 observe → 消费 + 逐 kind 披露,
候观察分支接线再呈现。

**确定性**:后端自有采样全部由 seed 派生(:func:`stream_rng` 流键,
键形沿用旧引擎模块号坐标系);动作分支采样(炉/骇客改件/晶矿/刷新)
经上报函数族 rng 形参,注入点在流程装配缝(运行器批)。

**装配**::func:`install_backend` = 端口槽装配;:func:`uninstall_backend`
幂等复位。测试 teardown 必卸(端口槽为进程全局)。
"""
from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.affix_effects_data import (
    AFFIX_EFFECTS,
)
from sr_od.application.currency_war.data.cw_shop_odds import REFRESH_PROB
from sr_od.application.currency_war.data.cw_synthesis import SYNTHESIS_BASES
from sr_od.application.currency_war.kernel.cw_battle_calib import (
    roll_rotation_per_stage,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    XP_TO_NEXT_LEVEL,
    LostNodeRef,
    RoundStartIncome,
    round_start_income,
    world_shop_refresh_cost,
    xp_apply_amount,
)
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    BOARD_REWRITE_SELL_ALL,
)
from sr_od.application.currency_war.kernel.cw_env_grants import (
    check_env_boss_grants,
    check_env_dot_grants,
    check_env_interest_grants,
    check_env_streak_grants,
    on_diamond_acquired,
)
from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    MegastarOption,
    SupplyOption,
)
from sr_od.application.currency_war.kernel.cw_gain_chain import (
    LEVEL_GRANT_PRODUCER,
    check_strategy_battle_grants,
    check_strategy_hp_loss_grants,
    check_strategy_level_equip_grants,
    check_strategy_level_grants,
    check_strategy_win_gold_grants,
    discharge_due_item_grants,
    discharge_due_item_opens,
    discharge_due_strategy_grants,
    gain_character,
    gain_equipment,
    gain_invest_env,
    gain_invest_strategy,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ENV_XP_WINDOW_DISCLOSURES,
    GAME_STATE_SCHEMA_VERSION,
    GameState,
    NodeKey,
    OreSight,
    ShopPayload,
    _row_unit_tags,
    clear_pending_loss,
    effective_node_pos,
    node_kind_of,
    observe_node_anchor,
    seed_opening_state,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_ORE_GRANTS,
    ENV_ORE_PANEL_BONUS,
    ENV_POOL_REWRITE,
    ENV_REROLL_ASSUMPTION_POOL,
    ENV_REROLL_NAMES,
    ENV_SUPPLY_EQUIP_COUNT,
    INVESTMENT_ENVS,
    INVESTMENT_STRATEGIES,
    STRATEGY_DELAYED_GRANTS,
    STRATEGY_DELAYED_OFFERS,
    STRATEGY_ECONOMY,
    STRATEGY_EFFECTS,
    STRATEGY_HP_LOSS_BUCKET_ASSUMPTION,
    STRATEGY_WIN_GOLD_SCOPE_ASSUMPTION,
    aggregate_economy,
    get_strategy,
    normalize_invest_name,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    NodePos,
    final_supply_pos,
    node_sequence_of,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    DIAMOND_EQUIP_NAMES,
)
from sr_od.application.currency_war.kernel.cw_ore_channel import (
    check_ore_declared_level,
    report_spheres_observed,
)
from sr_od.application.currency_war.kernel.cw_overlay_register import (
    consume_screen_change,
)
from sr_od.application.currency_war.kernel.cw_pool import (
    grant_bucket_names,
)
from sr_od.application.currency_war.kernel.cw_reward_node import (
    PIGGY_ENV_NAMES,
)
from sr_od.application.currency_war.kernel.cw_screen_report.box_pick import (
    CwScreenBoxPickObs,
    report_screen_box_pick_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.encounter import (
    CwScreenEncounterObs,
    report_screen_encounter_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.invest_env import (
    CwScreenInvestEnvObs,
    report_screen_invest_env_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.invest_strategy import (
    CwScreenInvestStrategyObs,
    report_screen_invest_strategy_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.megastar import (
    CwScreenMegastarObs,
    report_screen_megastar_obs,
)
from sr_od.application.currency_war.kernel.cw_screen_report.supply_node import (
    CwScreenSupplyNodeObs,
    report_screen_supply_node_obs,
)
from sr_od.application.currency_war.kernel.cw_shop_deal import sample_shop_deal
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.application.currency_war.sim.cw_sim_base import (
    logic_sig,
    obs_sig,
    sim_evidence,
)
from sr_od.application.currency_war.sim.cw_sim_battle import (
    SIM_BATTLE_FACE,
    SIM_REWARD_FREE_WIN_FACE,
    apply_hp_outcome,
    settle_battle,
)
from sr_od.application.currency_war.sim.cw_sim_enemy import (
    BOSS_DEDUP_PENDING,
    DIFFICULTY_BASE_PENDING_U25,
    HOLY_GRAIL_PENDING,
    DifficultyRecord,
    difficulty_of,
    resolve_plane_bosses,
)
from sr_od.application.currency_war.sim.cw_sim_opening import apply_opening
from sr_od.application.currency_war.sim.cw_sim_overlay import (
    OVERLAY_PARAM_PENDING,
)
from sr_od.application.currency_war.sim.cw_sim_run_config import RunConfig
from sr_od.application.currency_war.sim.cw_sim_streams import stream_rng

# ============================================================ 画面档名常量
# (screen_info 对局屏档名,权威 = assets/game_data/screen_info 各建档;
#  状态机状态首元。子态不设独立档名:晶矿子态 / wait_one_one 变体 =
#  备战档载荷,键形裁决归金路径生成器批。)

SCREEN_PREP: str = '货币战争-备战'
SCREEN_SHOP: str = '货币战争-备战-开商店'
SCREEN_BRIEFING: str = '货币战争-简报'
SCREEN_INVEST_ENV: str = '货币战争-投资环境'
SCREEN_INVEST_STRATEGY: str = '货币战争-投资策略'
SCREEN_SUPPLY: str = '货币战争-补给'
SCREEN_ENCOUNTER: str = '货币战争-遭遇节点'
SCREEN_BOSS_BRIEFING: str = '货币战争-BOSS简报'
SCREEN_PLANE_TRANSITION: str = '货币战争-位面过渡'
SCREEN_BOX: str = '货币战争-备战-武装箱选择'
SCREEN_EXPERT: str = '货币战争-备战-专家邀请函'
SCREEN_MEGASTAR: str = '货币战争-盛会之星'
SCREEN_PLANNER: str = '货币战争-银狼升星'
#: 战斗窗口呈现屏(sim 结算瞬时完成;战斗等待动画窗属实机时间维)。
#: 档名取流程消费面 = 「货币战争-结算」(currency_war_settlement.yml,
#: 「按钮-继续挑战」宿主屏):结算后流程经 CwScreenBattleWait 结算分支
#: + CwOpSettleConfirm 点击推进(档名 = 流程消费锚;错位则
#: 推进链不可达)。
SCREEN_SETTLE: str = '货币战争-结算'
#: 局终呈现屏(done 后终态;胜利/死亡两源共用)。呈现即可达
#: 流程终局链(CwScreenBattleWait ③B terminal_lobby → 主循环 3c 收尾)。
#: 非金路径档名(无生成器):呈现 ≠ 观察,observe 该档名按未注册响错。
SCREEN_LOBBY: str = '货币战争-大厅'

#: 备战子态载荷值(备战档第二元;'' = 常规备战)
PREP_SUB_ORE: str = 'ore'                    # 晶矿子态(奖励节点,gs.spheres 面板在场)
PREP_SUB_WAIT_ONE_ONE: str = 'wait_one_one'  # 开局补给动画等待变体(瞬时)

# ============================================================ 收入规则件
# (kernel round_start_income 三分支
#  单一源消费不变。)


#: 战斗类节点词表(连胜转移与败态归宿的判据域;补给/奖励轮不动连胜;
#: 奖励节点结算走战斗框架但收入分支仍为 reward)。
COMBAT_NODE_TYPES: frozenset[str] = frozenset({'battle', 'encounter', 'boss'})

#: 非战斗收入分支节点词表(分支优先级:supply/reward 先于败补,kernel
#: 分支序;败态在这些轮保留待下一战斗轮消费)。
INCOME_BRANCH_NODE_TYPES: frozenset[str] = frozenset({'supply', 'reward'})


@dataclass(frozen=True)
class IncomeApplied:
    """轮首收入应用回声(账面分解 + 落账后金;局内披露/判读消费)。"""

    row: RoundStartIncome
    gold_before: int
    gold_after: int


def income_modifiers_of(gs: GameState) -> tuple[float, int, int | None]:
    """持卡聚合的收入修饰 ``(win_reward_mult, interest_flat, cap_override)``。

    单一源 = ``aggregate_economy``(倍率取最大不叠乘/flat 求和/cap 取宽;
    cap None = 无覆写,由 ``interest_cap_resolved`` 归一链回默认)。
    """
    eff = aggregate_economy(list(gs.active_strategies.value or []))
    return eff.win_reward_mult, eff.interest_flat_per_node, \
        eff.interest_cap_override


def strategy_boss_gold_of(gs: GameState) -> int:
    """持卡策略聚合的进 boss 节点金(特战资金系,进 boss 节点每窗一笔)。

    单一源 = ``aggregate_economy``(多卡求和);返回 0 = 无该金腿,
    调用方(节点窗收口)零值零写。live 侧无此写端:金有整字段观察
    覆盖,实机真发由下一备战帧金观察覆盖兜底——金面禁 logic 直写防
    双计(裁定正本 = ``cw_effect_inventory.advance_node`` docstring
    「尾款金面走观察覆盖兜底」行),sim 世界自持账无观察可兜,不发即
    持卡局金系统性偏低,故唯 sim 侧补写。
    """
    return aggregate_economy(
        list(gs.active_strategies.value or [])).gold_per_boss_node


def strategy_final_supply_gold_of(gs: GameState) -> int:
    """持卡策略聚合的「最后一个补给阶段」金(尾款交付系,进锚点窗一笔)。

    单一源 = ``aggregate_economy``(多卡求和);锚 = 展平全序列最末
    supply 位(:func:`final_supply_pos`),整局一次——辖域与「后」字时点
    两假设见披露键 ``DISCLOSURE_FINAL_SUPPLY_GOLD_SCOPE`` /
    ``DISCLOSURE_FINAL_SUPPLY_GOLD_TIMING``。返回 0 = 无该金腿,调用方
    (节点窗收口)零值零写。live 侧无此写端:金有整字段观察覆盖,实机
    真发由下一备战帧金观察覆盖兜底——金面禁 logic 直写防双计(裁定正本
    = ``cw_effect_inventory.advance_node`` docstring「尾款金面走观察
    覆盖兜底」行),sim 世界自持账无观察可兜,不发即持卡局金系统性偏低,
    故唯 sim 侧补写。
    """
    return aggregate_economy(
        list(gs.active_strategies.value or [])).gold_at_final_supply


def apply_round_start_income(gs: GameState, *, plane: int, round_num: int,
                             node_type: str, streak: int,
                             pending_loss: LostNodeRef | None = None,
                             ) -> IncomeApplied:
    """轮首收入结算并 obs 写金(节点推进序列调用一次)。

    - ``streak`` = 收入侧无符号连胜计数(进轮连胜;派生读 = 容器带符号
      取 ``max(signed, 0)``,禁第二账);
    - ``pending_loss`` = 上一败掉的战斗类节点引用(单条登记的待办,容器
      ``gs.pending_loss``):非 supply/reward 节点传入触发 kernel 败补支
      (U04 口径);supply/reward 轮不传(败态跨轮保留,仅下一战斗轮
      消费——与 kernel 分支序一致);消费后清回 None 由调用方负责。
    """
    mult, flat, cap = income_modifiers_of(gs)
    gold_before = int(gs.gold.value or 0)
    effective_loss = (pending_loss
                      if node_type not in INCOME_BRANCH_NODE_TYPES else None)
    row = round_start_income(
        plane, round_num, node_type, gold_before, streak,
        lost_node=effective_loss, win_reward_mult=mult,
        interest_flat=flat, interest_cap=cap)
    gold_after = gold_before + row.total
    tag = f'income:p{plane}r{round_num}'
    gs.observe(gs.gold, gold_after, evidence=sim_evidence(tag),
               sig=obs_sig(group_id=f'sim:{tag}'))
    # 利息累计账入账 + 条件发放检查(T-27 公司契约条件分支;收入应用
    # 单一收口,四分支 supply/reward/败补/常规全含 interest 分量,在此
    # 一处收口即全分支随计)。record 先于 check 同组相邻;check 在金
    # 落账后(发放与收入同窗,金真值先行)。幂等性住调用方窗口守卫
    # (_begin_node_window),本函数无内建幂等——窗口路径外直调会双加,
    # 调用面纪律见函数 docstring。sig = logic_sig('sim:env')(触发函数
    # 两写均 logic 渠道,streak 接线同款单形态)。返回值忽略 = sim 无
    # 世界数值回调(托帕&账账无宝钻式联动;本模块零日志面,判读走
    # 容器/台账)。
    gs.effects.record_interest_earned(row.interest)
    check_env_interest_grants(gs, logic_sig('sim:env'))
    return IncomeApplied(row=row, gold_before=gold_before,
                         gold_after=gold_after)


def streak_income_after(streak: int, *, node_type: str,
                        won: bool) -> int:
    """收入侧无符号连胜计数转移(战斗类胜 +1/败归零;奖励/补给不动)。

    保留口 = 纯函数判读/测试对账;后端运行面用容器带符号派生,不再持
    第二账。"""
    if node_type not in COMBAT_NODE_TYPES:
        return streak
    return streak + 1 if won else 0


def streak_signed_after(streak_signed: int, *, node_type: str,
                        won: bool, piggy: bool = False) -> int:
    """容器带符号连胜转移(连胜 +/连败 −;战斗类胜 +1/败取负向计数;
    奖励/补给轮不动;与旧引擎逐位同式)。

    扑满帧例外(piggy=True,2026-10-10 用户裁定):胜 +1/败清零——
    败清零非负账;深井角斗场等连胜触发器读共用账自然跟随。"""
    if piggy:
        if won:
            return streak_signed + 1 if streak_signed > 0 else 1
        return 0
    if node_type not in COMBAT_NODE_TYPES:
        return streak_signed
    if won:
        return streak_signed + 1 if streak_signed > 0 else 1
    return streak_signed - 1 if streak_signed < 0 else -1


# ============================================================ 经验规则件
# (节点经验在节点推进时入账。)


#: 节点基础经验表(依据 docs/game/currency_war/research/xp-rules.md;
#: BOSS +12 = U17 定稿口径,构成/改道候实机数据,披露键已登记)。
NODE_XP_BY_TYPE: dict[str, int] = {
    'battle': 2,
    'reward': 2,
    'encounter': 2,
    'supply': 0,
    'boss': 12,
}

#: U17 余项披露键(BOSS +12 构成/P3 低难度经验/改道类,候实机数据)。
NODE_XP_PENDING_U17: str = 'node_xp_pending_u17'


def apply_node_xp(gs: GameState, *, node_type: str) -> int:
    """节点结算基础经验入账(补给 +0 = 表内显式档)。

    写容器 xp = (当前级已攒,升下一级所需);集外节点型 = 0 经验不入账
    (词表漂移在调用方暴露)。返回本节点实际入账经验量。
    """
    amount = NODE_XP_BY_TYPE.get(node_type, 0)
    if amount <= 0:
        return 0
    xp_field = gs.xp.value
    level_field = gs.level.value
    if xp_field is None or level_field is None:
        return 0
    level, cur = xp_apply_amount(int(level_field), int(xp_field[0]), amount)
    need = XP_TO_NEXT_LEVEL.get(level, int(xp_field[1]))
    sig = obs_sig(group_id='sim:xp')
    gs.observe(gs.level, level, evidence=sim_evidence('xp:node'), sig=sig)
    gs.observe(gs.xp, (cur, need), evidence=sim_evidence('xp:node'), sig=sig)
    return amount


def apply_strategy_pick_xp(gs: GameState, picked: Sequence[str]) -> int:
    """策略选卡落地拍即时经验入账(通用通道,辖域 = 注册表
    xp_instant>0 全体,字段分派非单卡特判)。

    为什么:sim 世界无观察、经验只有自持账,选卡当场即时型不在 kernel
    获得链发放(链内加经验写会连带 live——live 同拍 = 观察覆盖零写,
    经验面板画面可读,伟大征服口径),sim 不发即持卡局等级进度系统性
    失真,下游商店发牌分布/上阵上限/升级决策全链读等级现值。数额 =
    逐卡直读 :data:`STRATEGY_ECONOMY` 现值,**禁 aggregate_economy**:
    其聚合字段集不含 xp_instant,误走 = 静默零发放;且聚合语义 = 周期型
    重评,与「选卡单事件一次性发放」不匹配,逐卡各发各的(同持多卡笔笔
    独立)。升级结转/满级零推进复用 :func:`xp_apply_amount`;写入形态与
    :func:`apply_node_xp` 同款,evidence 按 ``xp:strategy_pick:<卡名>``
    与节点经验 ``xp:node`` 笔分账,sig 同组(同域字段同组,笔间靠
    evidence 区分)。返回本批实际入账经验总量。
    """
    total = 0
    for name in picked:
        canon = normalize_invest_name(str(name or ''))
        eff = STRATEGY_ECONOMY.get(canon)
        amount = eff.xp_instant if eff is not None else 0
        if amount <= 0:
            continue
        xp_field = gs.xp.value
        level_field = gs.level.value
        if xp_field is None or level_field is None:
            continue
        level, cur = xp_apply_amount(int(level_field), int(xp_field[0]),
                                     amount)
        need = XP_TO_NEXT_LEVEL.get(level, int(xp_field[1]))
        sig = obs_sig(group_id='sim:xp')
        evidence = sim_evidence(f'xp:strategy_pick:{canon}')
        gs.observe(gs.level, level, evidence=evidence, sig=sig)
        gs.observe(gs.xp, (cur, need), evidence=evidence, sig=sig)
        total += amount
    return total


def apply_strategy_pick_hp(gs: GameState, picked: Sequence[str]) -> int:
    """策略选卡落地拍即时生命入账(通用通道,辖域 = 注册表
    hp_instant>0 全体,字段分派非单卡特判)。

    为什么:sim 世界无观察、hp 只有自持账(开局查表种 + 战斗结算写),
    选卡当场即时型不在 kernel 获得链发放——链内写 hp 会在 live 侧引入
    hp 逻辑写端,违 fields.md hp 写入闸「无逻辑写入方」结构(live 同拍
    零写,游戏自算 + 血量条观察覆盖收口),sim 不发即持卡局血线系统性
    失真,败局余量/保底触发概率/局终时点全链读现值。数额 = 逐卡直读
    :data:`STRATEGY_ECONOMY` 现值,**禁 aggregate_economy**(聚合字段集
    不含 hp_instant,误走 = 静默零发放);hp 无结转语义(xp_apply_amount
    系 XP 特有),+N 直加。**不 clip**:sim 扣血绝对值制零上限消费
    (hp_max 字段缺位,缺口申报单一源 = fields.md HP 面行),clip 属无
    消费端语义,>100 可达 = 既有边界申报。写入经 observe 不触 floor
    判定;None 防御支沿 :func:`cw_sim_battle.apply_hp_outcome` 未观察
    零写形态(sim 局开局恒种,纯形态对齐);evidence 按
    ``hp:strategy_pick:<卡名>`` 与开局 ``opening``/战斗 ``battle:hp``
    笔分账可归因,sig 同组(同域字段同组,笔间靠 evidence 区分)。
    返回本批实际入账笔数(调用方轨迹追加按写行粒度对齐,一笔一追加)。
    """
    applied = 0
    for name in picked:
        canon = normalize_invest_name(str(name or ''))
        eff = STRATEGY_ECONOMY.get(canon)
        amount = eff.hp_instant if eff is not None else 0
        if amount <= 0:
            continue
        hp_now = gs.hp.value
        if hp_now is None:
            continue
        gs.observe(gs.hp, int(hp_now) + amount,
                   evidence=sim_evidence(f'hp:strategy_pick:{canon}'),
                   sig=obs_sig(group_id='sim:battle'))
        applied += 1
    return applied


def apply_strategy_pick_streak(gs: GameState, picked: Sequence[str]) -> int:
    """策略选卡落地拍连胜置位入账(通用通道,辖域 = 注册表
    streak_set≠0 全体,字段分派非单卡特判)。

    为什么:sim 世界真值必须显式写——置位发生在选卡刻,到下一结算屏
    带符号读数观察覆盖之间存在盲窗,观察无法承接(sim 不写即持卡局
    连胜系统性失真,下游结算转移/轮收入连胜分量/深井角斗场触发/
    伟大征服难度项全链读现值自动跟随)。与伟大征服「消费侧改写归
    观察」的本质差异:那张卡改写的是游戏自身连胜更新规则(乘数/派生),
    本通道在选卡拍直接改写字段值,状态侧置位须写端。语义 = 带符号
    **绝对赋值**:desc「使当前连胜数变为4」明文直读,高连胜回落与
    连败翻转均字面(禁外加 max 现值读法)。数额 = 逐卡直读
    :data:`STRATEGY_ECONOMY` 现值,**禁 aggregate_economy**:其聚合
    字段集不含 streak_set,误走 = 静默零发放。写入形态与结算连胜写
    同款(observe 通道,不触 write_logic 失配网),evidence 按
    ``streak:strategy_pick:<卡名>`` 与结算笔 ``streak:pNrN`` 分账
    可归因,sig 同组(同域字段同组,笔间靠 evidence 区分)。
    返回置位卡数。
    """
    applied = 0
    for name in picked:
        canon = normalize_invest_name(str(name or ''))
        eff = STRATEGY_ECONOMY.get(canon)
        value = eff.streak_set if eff is not None else 0
        if value == 0:
            continue
        gs.observe(gs.streak, int(value),
                   evidence=sim_evidence(f'streak:strategy_pick:{canon}'),
                   sig=obs_sig(group_id='sim:streak'))
        applied += 1
    return applied


#: 板面重写族出售支判据集(派生,禁硬编码名单)::data:`STRATEGY_EFFECTS`
#: 过滤 ``payload.board_rewrite == BOARD_REWRITE_SELL_ALL``。辖域 =
#: 注册表声明该语义的全体卡(现役成员唯「人力重组」;后继出售族卡按同
#: 语义注册即自动入列,本文件零改)。卖价修饰族(大裁员/降本增效,住
#: STRATEGY_ECONOMY)与仅注释归类未注册卡(现金为王)不入列,与桥出口
#: 语义同界(族归类注释 = cw_investments 板面重写族条)。
SELL_ALL_REWRITE_STRATEGIES: frozenset[str] = frozenset(
    name for name, spec in STRATEGY_EFFECTS.items()
    if str(getattr(getattr(spec, 'payload', None), 'board_rewrite', '')
           or '') == BOARD_REWRITE_SELL_ALL)

#: 出售发牌三档序列 ``(费用, 数量)``:卡文语序费用降序 3→2→1(卡文:
#: 「获得1个随机的2星3费角色、2个2星2费角色和2个2星1费角色」;族级
#: 读法「表内对序 = 卡文语序,禁按费用隐式重排」——本卡卡文即降序)。
SELL_ALL_DEAL_TIERS: tuple[tuple[int, int], ...] = ((3, 1), (2, 2), (1, 2))


def apply_strategy_pick_sell_all_deal(gs: GameState, picked: Sequence[str],
                                      rng: random.Random) -> int:
    """策略选卡落地拍出售发牌腿(板面重写族出售支,通用通道,辖域 =
    :data:`SELL_ALL_REWRITE_STRATEGIES` 全体,判据分派非单卡特判)。

    为什么:sim 世界自持无观察,live 发牌面 = 游戏侧发放、下一备战帧
    观察覆盖收口(板面重写桥「本桥禁替发牌面造单位」裁定,三正本在册
    零改动);sim 不发即持卡局 5 只 2★ 凭空缺失,合成素材池/held 派生/
    部署决策下游全链失真。本腿 = sim 世界真值直写,live 局不经过 sim
    后端,零假发牌。先卖后抽时序 = 挂点天然保证:kernel 获得链(含桥
    出售面清空+退款)已在本腿执行前写完容器,held 归零 → 各档剩余池 =
    固定牌库全集,桶出口「先回归后重抽」调用时序契约
    (:func:`cw_pool.grant_bucket_names`)天然满足。

    发牌本体 = 逐卡逐档(:data:`SELL_ALL_DEAL_TIERS`):桶出口派生桶 →
    同 rng 实例 count 次放回抽(同名可重复;批内零升星:同名 2★×2 不足
    3 合 1 门槛,与存量同名的合成照走链内级联)→ :func:`gain_character`
    star=2 直接落席(rand=True = 采样语义声明,kernel 随机赠卡支同口径)。
    2★ 与三档数量全卡面明写(「2星3费」),结构值非先验,禁实现为「发
    3 只 1★ 再合成」——行为等价但证据面失真,且批内同名 2★×2 的 6 副本
    语义依赖直接 2★ 形态(held 派生每只 2★ 计 3 副本)。桶出口恒缺省
    extra_experts(「专家 ∈ 授予采样空间」无定案,调用方禁自填,cw_pool
    在码申报)。空桶 = 注册表漂移态防御:零写 + log 警告不炸链(
    on_env_gained 随机支同款);桶出口守恒破(剩余负值 raise)= cw_pool
    显式炸错语义照抄不兜。rng 必须显式传参:缺省回退自掷破 sim 确定性
    (蓝海腿同款纪律);三档共用同一实例按卡文语序推进(掷序契约:改序
    = 掷序漂移)。返回发放单位数。
    """
    dealt = 0
    for name in picked:
        canon = normalize_invest_name(str(name or ''))
        if canon not in SELL_ALL_REWRITE_STRATEGIES:
            continue
        for cost, count in SELL_ALL_DEAL_TIERS:
            bucket = grant_bucket_names(gs, cost)
            if not bucket:
                # 运行期空 = 注册表漂移(出售刚清场,该费用档剩余池不应
                # 为空);零写留 log 防御分支(随机赠卡池空支同款,
                # 不改容器不炸链)
                log.warning(f'[cw-sim] 出售发牌腿空桶(注册表漂移?):'
                            f'cost={cost} card={canon}')
                continue
            for _ in range(count):
                gain_character(gs, rng.choice(bucket), 2, rand=True,
                               sig=logic_sig(group_id='sim:strategy'),
                               evidence='sim:board_rewrite_deal',
                               producer='SimBackend')
                dealt += 1
    return dealt


# ============================================================ 商店发牌件
# (发牌算法本体 = kernel cw_shop_deal 单一源。)


#: 轮岗建模假设档披露键(1/5 均匀系假设,实机待核;随局披露面消费)。
ROTATION_ASSUMPTION_DISCLOSURE: str = 'rotation_tier_assumed_uniform'

#: 轮岗环境已登记名(每备战阶段重掷翻倍档;kernel roll_rotation_per_stage)。
ROTATION_ENV_NAME: str = '轮岗'


def effective_deal_probs(level: int, rng: random.Random, *,
                         rotation_on: bool) -> dict[int, float]:
    """本备战期发牌概率表(基线 = ``REFRESH_PROB[level]``;轮岗环境在场
    = 每阶段重掷翻倍档)。"""
    if not rotation_on:
        return dict(REFRESH_PROB.get(level, {}))
    rolled = roll_rotation_per_stage(rng, level)
    return dict(rolled) if rolled is not None \
        else dict(REFRESH_PROB.get(level, {}))


def deal_shop(gs: GameState, rng: random.Random, *, level: int,
              probs: dict[int, float] | None = None,
              tag: str = 'shop:deal') -> None:
    """整店发牌并写容器商店载荷(obs 渠道;节点切换自动全刷写点)。

    发牌算法本体 = kernel ``cw_shop_deal.sample_shop_deal``(两执行面
    同源单一实现;sim 侧采样即世界真值)。名集空 → 槽留空(定长 5 槽
    三态模型的 empty 槽)。专家顾问入池 = 容器 ``gs.unlocked_experts``
    派生(获得链解锁写入,drawable_names 消费),本层零透传。
    """
    payload = sample_shop_deal(gs, rng, level=level, probs=probs)
    gs.observe(gs.shop, payload, evidence=sim_evidence(tag),
               sig=obs_sig(group_id=f'sim:{tag}'))


# ============================================================ offer 采样件
# (品质覆写名单常量位 = kernel cw_investments。)


#: 策略 offer 固定日程(U07① 已裁决;(plane, round_num) 对;P3r2 随
#: P3 适用范围自然延后生效)。
INVEST_OFFER_SCHEDULE: tuple[tuple[int, int], ...] = ((1, 3), (2, 2), (3, 2))

#: 联席决策环境注册表规范名(id122;效果原文「在2-6节点进行一次额外的
#: 投资策略三选一」)。
JOINT_DECISION_ENV_NAME: str = '联席决策'

#: 联席决策额外策略选卡槽(单一源 = kernel ENV_POOL_REWRITE 登记,键 =
#: JOINT_DECISION_ENV_NAME;本常量仅派生,勘误/改值只改 kernel 登记处,
#: 此处自动跟随)。
JOINT_DECISION_EXTRA_SLOT: tuple[int, int] = (
    ENV_POOL_REWRITE[JOINT_DECISION_ENV_NAME].extra_strategy_offer_node)
assert JOINT_DECISION_EXTRA_SLOT is not None, '联席决策登记缺挂点(数量通道事实残缺)'

#: 单次 offer 候选张数(画面语义三选一;环境屏同构占位,U08)。
OFFER_CANDIDATES: int = 3

#: 策略屏逐卡免费刷新基准次数(每卡;live OCR 常态「刷新次数1」×3 实证,
#: 读链 = cw_node_obs.read_invest_refresh_counts('strategy'),屏上数字即
#: 真值;环境增量 = kernel ``ENV_POOL_REWRITE.extra_pick_refreshes`` 登记,
#: 消费 = 基准 + 增量,2026-10-19 用户裁定「sim 与实机一致提供刷新次数」
#: 批接入)。建模选择申报:非银·金·彩局的刷新重掷品质 = 默认分布掷点
#: (desc 无刷新品质语义;实机对账如有出入,以对账评点纠偏)。
STRATEGY_REFRESH_BASE_PER_CARD: int = 1

#: 投资环境屏整组刷新基准次数(环境刷新 = 单全局钮整组重掷一次;基准
#: 1 次,docs/game/currency_war/data/advantage_layouts.md「环境刷新」行)。
ENV_REFRESH_BASE: int = 1

#: 品质掷点分布(显式常量参数,候实机数据回填;首版三档均匀 = 中性
#: 占位非实证,随局披露键见 :data:`QUALITY_DISTRIBUTION_DISCLOSURE`)。
QUALITY_DISTRIBUTION: tuple[tuple[str, float], ...] = (
    ('银', 1.0 / 3.0), ('金', 1.0 / 3.0), ('棱彩', 1.0 / 3.0),
)

#: 品质分布占位披露键(均匀占位非实证;候实机回填后移除)。
QUALITY_DISTRIBUTION_DISCLOSURE: str = 'invest_quality_distribution_uniform_pending'

#: 环境品质维度缺失披露键(PlazaPortal 无 rarity 注册,品质掷点不适用)。
ENV_QUALITY_DISCLOSURE: str = 'env_quality_not_registered'

#: 离群触发点未建模披露键(U07① ~1-2% 触发源未归因,不作机制建模)。
OFFER_OUTLIER_DISCLOSURE: str = 'invest_offer_outlier_triggers_unmodeled'

#: 策略延时 offer 呈现留证披露键(值 = 触发卡@frame;对账面 = 实机局
#: 额外选卡屏出现时点;「N个节点后」计数起点读法的证伪路径 = 同值与
#: 实机帧 ±1 对照。呈现路由第二判别面 = rng 流标签
#: ``M11/offer-extra/...`` 与固定日程 ``M11/offer/...`` 分域)。
STRATEGY_DELAYED_OFFER_FIRED: str = 'strategy_delayed_offer_fired'

#: 策略延时 offer 顺延留证披露键(值 = 原因 scheduled_slot_occupied/
#: window_cap + 悬置余量):同窗固定日程/联席槽在场,或本窗已呈现一次
#: 时,到点条目悬置顺延下一窗(到点判定「到了及以后都算」天然承载,
#: 不悬空不丢失)。现交付域冲突交集 = ∅(可达拿卡窗到点窗与槽窗集
#: 不相交),两分支预期均不触发——结构性守卫留证,实机对账见此键 =
#: 可达性核算被证伪,升级重算。
STRATEGY_DELAYED_OFFER_DEFERRED: str = 'strategy_delayed_offer_deferred'

#: 策略延时发放到点留证披露键(值 = 触发卡@frame:发放物;对账面 =
#: 实机局发放物入栏时点;「N个节点后」计数起点读法的证伪路径 = 同值
#: 与实机帧 ±1 对照)。
STRATEGY_DELAYED_GRANT_FIRED: str = 'strategy_delayed_grant_fired'


def offer_slots(plane: int, round_num: int,
                active_env: str | None) -> bool:
    """该 (plane, round_num) 是否存在策略 offer 槽。

    固定日程(U07①)∨ 联席决策额外槽(id122 挂 2-6;环境按容器
    ``active_env`` 现值判定)。环境名不可辨(None/空)→ 仅按固定日程。
    """
    key = (int(plane), int(round_num))
    if key in INVEST_OFFER_SCHEDULE:
        return True
    return (key == JOINT_DECISION_EXTRA_SLOT
            and (active_env or '') == JOINT_DECISION_ENV_NAME)


def _roll_quality(rng: random.Random) -> str:
    """品质掷点(按 :data:`QUALITY_DISTRIBUTION` 加权;概率质量恒和 1)。"""
    qualities = [q for q, _ in QUALITY_DISTRIBUTION]
    weights = [w for _, w in QUALITY_DISTRIBUTION]
    return rng.choices(qualities, weights=weights, k=1)[0]


def sample_strategy_offer(rng: random.Random, excluded: set[str],
                          forced_slots: tuple[str, ...] = (),
                          ) -> tuple[str, ...]:
    """策略 offer 候选生成(U07③:先掷品质 → 该品质池均匀取 1;
    offer 内去重 + 排除已出选项 = 全程不重复)。

    ``forced_slots`` = 三槽品质覆盖向量(坐标系 = 投资界面卡槽物理排位
    0..2,与 ``ENV_POOL_REWRITE.slot_qualities`` 同坐标系;长度不足处按
    默认掷点):非空元素 = 该槽跳过品质掷点直取目标品质池;'' 元素 =
    默认掷点。改写命中次(时代族/头彩/尾彩(settled 定谳)环境 = 三槽
    同向量;银·金·彩 = 卡面三槽品质按位,判据 =
    :func:`rewrite_slot_qualities_for_pick`)。2026-10-14 用户裁定:固定
    品质后照常抽样,可观察面 = 候选全目标品质;目标品质池被排除集吃光 →
    回退全池(排除后),回退语义 = 现役防御契约沿用(用户裁定:正常局
    不可达,不扩防御分支)。

    ``excluded`` = 本局已出过的全部选项名(后端持有的累计集,调用方
    须把返回值并入)。某品质池被排除集吃光 → 该候选回退全池(排除后)
    取;全池亦空 → 候选数不足如实少发(防御性声明,正常局不可达)。
    """
    banned = set(excluded)
    picks: list[str] = []
    for i in range(OFFER_CANDIDATES):
        quality = (forced_slots[i] if i < len(forced_slots)
                   and forced_slots[i] else _roll_quality(rng))
        pool = [n for n, s in INVESTMENT_STRATEGIES.items()
                if s.rarity == quality and n not in banned]
        if not pool:
            pool = [n for n in INVESTMENT_STRATEGIES if n not in banned]
        if not pool:
            break
        name = pool[rng.randrange(len(pool))]
        picks.append(name)
        banned.add(name)
    return tuple(picks)


def sample_strategy_card(rng: random.Random, excluded: set[str],
                         forced_quality: str = '') -> str:
    """单卡采样(刷新重掷分支;与 :func:`sample_strategy_offer` 同分布
    同排除契约的单槽形):``forced_quality`` 非空 = 直取目标品质池
    (银·金·彩槽位品质承诺跨刷新保持),'' = 默认分布掷点。品质池被
    排除集吃光 → 回退全池(排除后);全池亦空 → 返回 ''(调用方
    视为刷新未产出,防御性,正常局不可达)。"""
    quality = forced_quality or _roll_quality(rng)
    pool = [n for n, s in INVESTMENT_STRATEGIES.items()
            if s.rarity == quality and n not in excluded]
    if not pool:
        pool = [n for n in INVESTMENT_STRATEGIES if n not in excluded]
    if not pool:
        return ''
    return pool[rng.randrange(len(pool))]


def sample_env_offer(rng: random.Random, excluded: set[str],
                     ) -> tuple[str, ...]:
    """环境 offer 候选生成(U08 与 U07 同构;环境无品质注册 → 排除后
    全池均匀,品质掷点不适用)。"""
    banned = set(excluded)
    pool = sorted(n for n in INVESTMENT_ENVS if n not in banned)
    if not pool:
        return ()
    k = min(OFFER_CANDIDATES, len(pool))
    return tuple(rng.sample(pool, k))


def rewrite_slot_qualities_for_pick(active_env: str | None,
                                    pick_ordinal: int,
                                    ) -> tuple[str, ...] | None:
    """品质改写判据(槽位向量形):当前环境命中改写条目且本次取卡在改写
    域 → 返回 offer 三槽的品质覆盖向量(逐槽直取该品质池);否则 None
    (按默认分布逐槽掷点)。

    三型归一(2026-10-19 用户裁定批:判据从单品质形泛化为槽位向量形,
    原型语义等价——单品质 = 三槽同向量的特例,历史裁定零漂移):
    - 全改写型(时代 ×3,``rewrite_picks == (1, 2, 3)`` 结构特征,建表
      校验保证该形状无 pending 歧义):命中次返回 (q, q, q);
    - 部分改写型经 ``rewrite_settled`` 定谳后同判据接入——头彩已经用户
      裁定 2026-10-16 定谳 = offer 级覆盖面(第 1 次取卡机会 3 张候选全
      目标品质),尾彩同裁定 = 第 3 次;未定谳部分型必填 pending_notes
      的建表闸保持(判据 settled 分支保留为未来新增部分型的守卫);
    - 槽位向量型(银·金·彩,``slot_qualities`` = 卡面三槽品质按位,
      用户裁定 2026-10-19 卡面直读即真值):固定日程取卡恒返回登记向量
      (无序数条件——品质承诺对每个固定取卡节点成立,且跨逐卡刷新保持)。
    pick_ordinal 坐标系 = 本局策略三选一呈现全局序 1 基,
    与 ``ENV_POOL_REWRITE.rewrite_picks`` 同坐标系。环境名直查不做归一
    (与现役注册表消费同款形状;环境名来自注册表注册,无 OCR 变异源)。
    """
    rewrite = ENV_POOL_REWRITE.get(active_env or '')
    if rewrite is None:
        return None
    if rewrite.slot_qualities:
        return tuple(rewrite.slot_qualities)
    if rewrite.rewrite_quality == '' \
            or (rewrite.rewrite_picks != (1, 2, 3)
                and not rewrite.rewrite_settled):
        return None
    return (rewrite.rewrite_quality,) * 3 \
        if pick_ordinal in rewrite.rewrite_picks else None


def _offer_extra_refreshes(active_env: str) -> int:
    """策略屏逐卡刷新次数的环境增量(单一源 = kernel
    ``ENV_POOL_REWRITE.extra_pick_refreshes`` 登记;表外环境 = 0)。"""
    rewrite = ENV_POOL_REWRITE.get(active_env or '')
    return rewrite.extra_pick_refreshes if rewrite is not None else 0


# ============================================================ 节点事件件
# (选项生成保留;apply_*_pick 动作分支停用——
#  pick 动作走 op → 上报函数族获得链,与实机同构。)


#: 遭遇档位数(U22 占位:实机四档旁证 + 加成表四档已定案)。
ENCOUNTER_TIER_COUNT: int = 4

#: sim 节点 kind → 结算环行 node_type 词表(T-33 结算环帧补写用;词表
#: 正本 = live 结算行归一 cw_screen_battle_wait._normalize_node_type,
#: kernel→operations 反向 import 禁止故同形内联;战斗类四键在表,
#: supply 不经结算分支恒不入环)。
_SIM_KIND_TO_RING_LABEL: dict[str, str] = {
    'battle': '普通战斗', 'encounter': '遭遇',
    'boss': 'boss', 'reward': '奖励',
}

#: 遭遇奖励包金占位(U22)。
ENCOUNTER_REWARD_GOLD_PLACEHOLDER: int = 20

#: 遭遇占位参数披露键(U22)。
ENCOUNTER_PARAMS_PENDING_U22: str = 'encounter_tier_params_pending_u22'

#: 晶矿面板单例锚(U23:实测 1-8 清关样本 1 大金晶矿+5 蓝晶矿+2 灰晶矿)。
REWARD_ORE_PANEL_ANCHOR: tuple[tuple[str, int], ...] = (
    ('金', 1), ('蓝', 5), ('灰', 2),
)
# (面板矿内容不经本模块携带:spheres 写一律过挂接入口
#  ``cw_ore_channel.report_spheres_observed`` 生成附着——声明金先占席、
#  其余逐矿采样;分布参数未校准的披露单一源 = kernel
#  ``cw_ore_reward.ORE_ASSUMPTION_KEYS``,本模块不双源。)

#: 位面开局声明矿呈现面披露键:呈现色档(现按 '金' 占位)与「晶矿
#: 自动开启与否」均未实采,实机首遇校——sim 按「呈现可点」建模,若
#: 实机为自动开启则声明条目留至位面过渡被过期清理,机制面零污染。
ORE_PLANE_START_PENDING: str = 'ore_plane_start_pending'

#: 箱候选数(4 选 1,U23 画面语义)。
BOX_CANDIDATES: int = 4

#: 箱内容池占位披露键(U24 箱内容池候实机数据,占位 = 8 基础件均匀)。
BOX_POOL_PENDING_U24: str = 'box_pool_pending_u24'

#: 补给选项数(3 选 1,画面语义)。
SUPPLY_OPTION_COUNT: int = 3

#: 带钻槽位分布占位披露键(U24)。
SUPPLY_DIAMOND_SLOT_PENDING: str = 'supply_diamond_slot_pending_u24'

#: 扑满不掉血豁免披露键(M17:扑满关不掉血,gameplay「节点类型×战力
#: 要求」节;M14 豁免位由后端结算分支承载)。
PIGGY_NO_HP_LOSS: str = 'piggy_node_no_hp_loss_u01_face'

#: 扑满面板矿占位增量披露键(「掉落(超)多战利品」desc 无数值,sim
#: 面板矿增量 = 用户占位拍定 2026-10-15,非核实游戏事实,待实机采证
#: 校准)。值串 = 纯声明串不携数值:携值即与注册表双源,量级单一源 =
#: kernel :data:`ENV_ORE_PANEL_BONUS`。不进 kernel ORE_ASSUMPTION_KEYS
#: 汇总 tuple——该 tuple 辖 sphere 内容分布假设且现无发射接线,本键
#: 沿 :data:`ORE_PLANE_START_PENDING` 先例住本模块、接线
#: :data:`_BASE_DISCLOSURES`、测试直断发射(设计 designs/T-20-
#: jingji-yanzhong-guore.md §6.1)。
PIGGY_ORE_PANEL_BONUS_PLACEHOLDER: str = 'piggy_ore_panel_bonus_placeholder'

#: 商店 2★ 直出概率占位披露键(人才下沉 id 121:「商店中有概率出现2星
#: 角色」desc 无数值,sim 发牌翻星概率 = 用户占位拍定 2026-10-16,非
#: desc 真值,待实机采证校准)。值串 = 纯声明串不携数值:携值即与注册
#: 表双源,量级单一源 = kernel :data:`ENV_SHOP_TWO_STAR_DEAL_PROB`(翻
#: 星分支 = kernel/cw_shop_deal,sim/live 两执行面共用)。沿
#: :data:`PIGGY_ORE_PANEL_BONUS_PLACEHOLDER` 先例住本模块、接线
#: :data:`_BASE_DISCLOSURES`、测试直断发射(设计 designs/T-22-rencai-
#: xiachen.md §8)。
SHOP_TWO_STAR_DEAL_PLACEHOLDER: str = 'shop_two_star_deal_prob_user_placeholder'


def encounter_options() -> tuple[EncounterOption, ...]:
    """遭遇档位集生成(M16;首版固定四档集,奖励包占位文本随披露)。

    ``EncounterOption.difficulty`` 坐标系 = kernel 档位序 1 基(1=易..
    4=难);idx = 档位集 0 基下标(策略器输出同域)。实机档位含敌人
    词缀构成不建模(第一期随机输出面无消费)。
    """
    return tuple(
        EncounterOption(idx=i, difficulty=i + 1,
                        rewards=[f'金+{ENCOUNTER_REWARD_GOLD_PLACEHOLDER}'
                                 f'(占位,{ENCOUNTER_PARAMS_PENDING_U22})'])
        for i in range(ENCOUNTER_TIER_COUNT))


def encounter_options_for(strategy_names: list[str]) -> tuple[EncounterOption, ...]:
    """遭遇呈现集(持卡收窄;二极管 = 全档两端派生 + idx 重排)。

    辖域 = 注册表 ``encounter_tier_extremes_only`` 全体(任一持卡命中即
    收窄,「本场对局中」= 局级持续语义),payload 读法沿
    ``cw_sim_enemy._strategy_delta_of`` 同款单一形状(get_strategy ×
    normalize_invest_name,禁新立读法)。端点 = :func:`encounter_options`
    首/尾派生,零新数值(档数单一源 = ``ENCOUNTER_TIER_COUNT``,U22 校准
    自动跟随);idx 重建 = 呈现集 0 基位次——三消费方同域承重(策略器
    输出 ``o.idx`` / 上报 ``options[param.idx]`` 取载荷 / 机械链两卡位),
    不重排则策略器输出原档位下标越界,守卫 AssertionError。零 rng:确定
    性收窄,种子流无漂移;无命中返回全集原样(现行为零变化)。
    """
    opts = encounter_options()
    for raw in strategy_names:
        s = get_strategy(normalize_invest_name(raw))
        if s is not None and s.economy is not None \
                and s.economy.encounter_tier_extremes_only:
            return tuple(
                replace(o, idx=i) for i, o in enumerate((opts[0], opts[-1])))
    return opts


def is_piggy_node(gs: GameState) -> bool:
    """当前奖励节点是否被扑满环境替换(单一源 = ``PIGGY_ENV_NAMES`` ×
    容器 ``active_env``;非奖励节点恒 False)。"""
    return (str(node_kind_of(gs) or '') == 'reward'
            and str(gs.active_env.value or '') in PIGGY_ENV_NAMES)


def reward_ore_points() -> tuple[tuple[str, int, int, int], ...]:
    """晶矿面板点集(U23 单例锚展开;晶矿序 = 色档序内先大后小)。

    [索引定义] 元素 = ``(色档, x, y, r)``(OreSight.points 元素同形);
    (x, y) = sim 世界合成坐标,无画面语义,仅作晶矿身份键(点晶矿
    上报按坐标求交,容器 spheres 点集即真值)。内容不再由本面板携带
    ——spheres 写经挂接入口 ``cw_ore_channel.report_spheres_observed``
    生成附着(声明金先占席、其余逐矿采样,sim 采样即世界真值),点击
    按附着值兑现。
    """
    points: list[tuple[str, int, int, int]] = []
    i = 0
    for color, count in REWARD_ORE_PANEL_ANCHOR:
        for _ in range(count):
            i += 1
            points.append((color, i * 10, 10, 10))
    return tuple(points)


def reward_ore_panel_points(
        env_name: str) -> tuple[tuple[str, int, int, int], ...]:
    """奖励面板点集 = 锚 8 矿 + 扑满环境占位增量扩尾(奖励节点装配
    单点消费;纯函数,零采样零簿记)。

    [索引定义] 元素 = ``(色档, x, y, r)``,与 :func:`reward_ore_points`
    同形同坐标系(x/y = sim 世界合成坐标,身份键无画面语义)。增量矿
    查表 :data:`ENV_ORE_PANEL_BONUS`(量级单一源;表外环境零增量),
    色档 = '灰'(占位呈现身份:色档无内容语义,实采校准时连色带数
    一起校,披露键 :data:`PIGGY_ORE_PANEL_BONUS_PLACEHOLDER`)。

    **坐标续接面板序,禁独立从 1 起号**:增量点 x 自锚点序顺延
    ((锚点数+序)*10),与锚矿同列延伸——同批 spheres 写按 (x, y)
    身份求交,独立起号会撞键吞点;位面开局声明矿消费方传本函数结果
    长度续接(:meth:`SimBackend._plane_start_declared_points`),
    扩尾加长后声明矿坐标自动跟随,联动零改码。
    """
    points = list(reward_ore_points())
    bonus = ENV_ORE_PANEL_BONUS.get(str(env_name or ''), 0)
    for _ in range(bonus):
        points.append(('灰', (len(points) + 1) * 10, 10, 10))
    return tuple(points)


def box_options() -> tuple[str, ...]:
    """补给箱 4 选 1 装备候选(U24 箱内容池候实机数据,占位 = 8 基础件
    取前 4 定序;箱生成随机性候实机数据,首版固定候选集)。"""
    return tuple(sorted(SYNTHESIS_BASES)[:BOX_CANDIDATES])


def supply_options(rng: random.Random,
                   env_name: str = '') -> tuple[SupplyOption, ...]:
    """补给 3 选项采样(M18:8 基础件池均匀取 3 + 带钻槽 equip 级均匀占位;
    每列件数按环境注册表 :data:`ENV_SUPPLY_EQUIP_COUNT`,默认 1)。

    ``SupplyOption.char`` 恒空(补给 = 装备选);idx = 选项 0 基下标。
    ``env_name`` = 当前投资环境归一名(表外环境 = 每列 1 件)。
    采样 = **逐槽独立均匀有放回**(``rng.choice``,全环境统一一码径,可
    重复——「随机到一样就一样」):跨列重复有归档帧实证;同列重复实机
    真值未证,sim 按最简放回统一(单排默认局同规则,无证据支持分异)。
    同 seed 采样值随采样式变更漂移(分布假设变更,非回归破坏)。
    带钻槽 = 总槽位 equip 级均匀掷,落选项 → 该选项 ``has_diamond=True``
    (选项级布尔契约不变;钻具体在哪件属呈现面,SUPPLY_DIAMOND_SLOT_
    PENDING U24 披露已登记)。
    """
    pool = sorted(SYNTHESIS_BASES)
    per_col = ENV_SUPPLY_EQUIP_COUNT.get(
        normalize_invest_name(env_name or ''), 1)
    names = [rng.choice(pool)
             for _ in range(SUPPLY_OPTION_COUNT * per_col)]
    diamond_slot = rng.randrange(len(names))
    return tuple(
        SupplyOption(idx=i, char='',
                     equip=names[i * per_col],
                     extra_equips=tuple(
                         names[i * per_col + 1:(i + 1) * per_col]),
                     has_diamond=(diamond_slot // per_col == i))
        for i in range(SUPPLY_OPTION_COUNT))


# ============================================================ 披露键群
# (恒已登记声明面,随局结果 unmodeled 输出;装备三键键义
#  ——动作分支停用后不变:发放空表/特权投影仪/炉拖角色模式仍未建模。)

#: 环境结构化经济通道披露键(M02:两位面金通道已结构化,其余候效果批)。
DISCLOSURE_ENV_CHANNELS: str = 'env_economy_channels_pending_m02'

#: 开箱自发触发披露键(U23:首版无自发开箱,箱 = 备战席箱件开箱动作)。
DISCLOSURE_BOX_TRIGGER: str = 'box_spawn_trigger_pending_u23'

#: planner 选卡效果披露键(升费分支效果由 pick_planner 上报承载;其余
#: 选项效果面候效果批)。
DISCLOSURE_PLANNER_EFFECT: str = 'planner_pick_effect_pending_u26'

#: 整店锁披露键(裁定②:动作词表无锁通道,首版恒解锁 + 披露,字段先行)。
DISCLOSURE_SHOP_LOCK: str = 'shop_lock_sim_engine_state'

#: P3 未观测披露键(**已退役,不再发射**):U19 时代「P3 进场即局终」的
#: 历史遥测身份,常量保留仅供历史语料判读;位面 3 真值入码后超位面 3 =
#: 胜利终局,见 :data:`DISCLOSURE_RUN_COMPLETE`。
DISCLOSURE_P3_UNOBSERVED: str = 'p3_unobserved'

#: 胜利终局披露键(推进超出序列表末位面 = 位面 3 末 boss 结算存活后
#: 走完全部节点;用户裁定 2026-10-15「过了位面3就是胜利」。hp 归零
#: 败局走结算死亡分支不经此键 = 胜负判别单一源在披露集)。
DISCLOSURE_RUN_COMPLETE: str = 'run_complete'

#: lv10 满级零累计披露键(裁定③:cap 分母未定,满级经验不再累计)。
DISCLOSURE_LV10_XP: str = 'level_cap_xp_denominator_none'

#: U24 装备三披露键(发放空表/工具效果面/炉拖角色模式)。
UNMODELED_GRANTS: str = 'unmodeled_grants'
TOOL_EFFECTS_PENDING: str = 'tool_effects_pending_m10'
FURNACE_CHAR_MODE_PENDING: str = 'furnace_char_mode_pending_m10'

#: 词缀采样占位披露键(reset/affixes 流键采样:池 = affix_effects_data
#: 注册表键集,张数/分布占位候实机补档)。
DISCLOSURE_AFFIX_SAMPLE: str = 'reset_affixes_sample_placeholder'

#: 羁绊档位触发语义披露键(T-41 特邀专家:加拉赫,裁决点 3 电平语义为
#: 建模选择非实采——卡面「激活…时」的边沿细节未定谳,「电平 + 每档
#: 一次性 done 封账」为用户裁定建模口径;语义单一源 = kernel/
#: cw_faction_callbacks.check_env_bond_tier_grants docstring。纯声明,
#: 不进任何判定分支)。
DISCLOSURE_BOND_TIER_SEMANTICS: str = 'env_bond_tier_semantics_level'

#: 策略 boss 金通道披露键(特战资金系;纯声明,不进任何判定分支)。
#: 载义:①sim 侧策略 boss 金腿 = 「调用方聚合单列」过渡形态
#(:meth:`strategy_boss_gold_of` + 节点窗收口独立观察笔),承载方式随
#: T1b 定夺迁移(round_start_income docstring 预留两承载方式,选分量
#: 扩参则本腿合并进收入签名);②轮首收入口径常量(BASE_INCOME/
#: LOSS_GOLD_BY_NODE/REWARD_BASE_GOLD_BY_ROUND,按实机逐轮金轨迹
#: 整定)的校准样本域与本腿的叠加交互未实证(校准局是否含持卡局
#: 不可考)——首次实机持卡局金轨迹对照时核,异常表现 = 持卡局金轨迹
#: 系统性偏离。
DISCLOSURE_STRATEGY_BOSS_GOLD: str = 'strategy_boss_gold_sim_channel'

#: 策略选卡即时腿披露键(纯声明,不进任何判定分支)。载义:①策略选卡
#: 「选牌当场即时型」世界腿现值 = xp_instant/hp_instant 已建(辖域各 =
#: 注册表对应字段>0 全体,字段分派非单卡特判)/ 真即时金 instant_gold
#: 未建(族批另议)——三形状均在册申报,防「通道存在 = 族全覆盖」误读;
#: ②腿数额 = 单卡直读注册表现值,条目修订腿值随单一源自动跟随,无卡别
#: 硬编码。
DISCLOSURE_STRATEGY_PICK_INSTANT: str = 'strategy_pick_instant_legs'

#: 策略尾款金·锚点辖域假设披露键(尾款交付;纯声明,不进任何判定分支)。
#: 载义:①「最后一个补给阶段」按**全局一次**建模(锚 = 展平全序列最末
#: supply 位,单一源 = ``cw_node_schedule.final_supply_pos``;措辞依据 =
#: 卡文「最后一个」全局限定词,证伪路径 = 实机持卡局非锚 supply 节点窗
#: 金轨迹 +30 即证伪为每位面各一次,改判定 = helper 换位面域扫描);②
#: 修饰局锚点随场字段现值(继承 T-8 披露的场字段缺位回退默认表链路——
#: 本卡 live 零写金,该链路零行为影响)。
DISCLOSURE_FINAL_SUPPLY_GOLD_SCOPE: str = 'final_supply_gold_scope_assumption'

#: 策略尾款金·「后」字时点精度披露键(尾款交付;纯声明,不进任何判定
#: 分支)。载义:①「进入…后」按节点进窗拍建模(与特战资金「时」字同
#: 拍假设;若实机证伪为补给确认拍,live 观察覆盖兜底行为面无差,sim 发
#: 放时点差一个窗内位置);②拿卡当节点不发放(选卡确认恒晚于窗口前段
#: 聚合读,锚点错过即无——「尾款」语义自洽)。
DISCLOSURE_FINAL_SUPPLY_GOLD_TIMING: str = 'final_supply_gold_timing_assumption'

#: 策略卡到级条件·触发语义披露键(成长基金金腿 + 钻石商人装备腿两腿
#: 共用;纯声明,不进任何判定分支)。载义:「拿卡时已 ≥ 目标级也发放」
#: 状态检查型语义未经实机采证(等级 = 容器现值非事件流,拿卡时点无从
#: 回溯历史跨越,策略条件腿容器现值求值同款;若实机证伪为严格跨越事件
#: 型,两检查函数同批改读升级事件标记并随批退役本键)。
DISCLOSURE_STRATEGY_LEVEL_SEMANTICS: str = 'strategy_level_grant_state_semantics'

#: 策略卡到级条件·sim 休眠披露键(成长基金金腿 + 钻石商人装备腿两腿
#: 共用;纯声明,不进任何判定分支)。载义:现役 sim 经验写源(节点经验
#: 表 × 选卡即时腿)下全程等级上界低于 3→9 级累计门槛 194,到级两腿
#: 休眠恒短路(上界封顶 7 级);经验源扩网(买经验建模/经验常量修订)
#: 使上界 ≥ 194 时休眠锁先红触发边界重申报,本键随激活批复评退役。
DISCLOSURE_STRATEGY_LEVEL_DORMANT: str = 'strategy_level_grant_dormant_in_sim'

#: 全程披露常量表(恒已登记,与采样值无关的声明面)。
_BASE_DISCLOSURES: dict[str, object] = {
    SIM_BATTLE_FACE: 'random_win_p0.5_hp_loss_uniform_[23,70]',
    QUALITY_DISTRIBUTION_DISCLOSURE: 'uniform_1/3_each_placeholder',
    ENV_QUALITY_DISCLOSURE: 'env_pool_uniform_no_quality_axis',
    OFFER_OUTLIER_DISCLOSURE: 'u07_outlier_1-2pct_not_modeled',
    ENCOUNTER_PARAMS_PENDING_U22: 'count4_gold20_equip0_fixed_set',
    DIFFICULTY_BASE_PENDING_U25: 'base_curve_none_no_interpolation',
    HOLY_GRAIL_PENDING: 'activation_pending_u14',
    BOSS_DEDUP_PENDING: 'with_replacement_per_plane',
    ROTATION_ASSUMPTION_DISCLOSURE: 'tier_uniform_1of5_assumed',
    DISCLOSURE_SHOP_LOCK: 'field_first_no_action_channel_v1_unlocked',
    DISCLOSURE_LV10_XP: 'cap10_zero_accumulate_u18',
    DISCLOSURE_ENV_CHANNELS: 'structured_two_of_env_economy',
    DISCLOSURE_BOX_TRIGGER: 'no_spontaneous_box_first_phase',
    UNMODELED_GRANTS: 'u24_grant_table_empty_first_phase',
    TOOL_EFFECTS_PENDING: 'privilege_projector_token_unmodeled',
    FURNACE_CHAR_MODE_PENDING: 'furnace_drag_char_mode_unmodeled',
    NODE_XP_PENDING_U17: 'boss_xp12_composition_pending',
    PIGGY_NO_HP_LOSS: 'piggy_node_no_hp_loss_exempt',
    # 占位增量申报:值串纯声明不携数值,量级单一源 = ENV_ORE_PANEL_BONUS
    PIGGY_ORE_PANEL_BONUS_PLACEHOLDER: 'user_placeholder_pending_field_sampling',
    # 商店 2★ 直出概率占位申报:量级单一源 = ENV_SHOP_TWO_STAR_DEAL_PROB
    SHOP_TWO_STAR_DEAL_PLACEHOLDER: 'user_placeholder_pending_field_sampling',
    DISCLOSURE_AFFIX_SAMPLE: 'pool3_uniform_placeholder',
    # 羁绊档位触发语义申报(T-41,裁决点 3 电平语义为建模选择非实采;
    # 值串纯声明,语义单一源 = 判据函数 docstring)
    DISCLOSURE_BOND_TIER_SEMANTICS: 'level_reach_once_per_tier_done_sealed',
    # 策略 boss 金通道申报(载义见键常量注:过渡形态随 T1b 迁移 +
    # 收入口径常量校准交互未实证待持卡局对照)
    DISCLOSURE_STRATEGY_BOSS_GOLD: 'caller_side_aggregate_pending_t1b_carrier',
    # 策略选卡即时腿申报(载义见键常量注:xp/hp_instant 腿已建与真即时金
    # 未建三形状在册)
    DISCLOSURE_STRATEGY_PICK_INSTANT: 'xp_hp_instant_legs_built_pick_gold_instant_pending',
    # 策略尾款金两键(尾款交付;载义见键常量注:锚点辖域全局一次假设 +
    # 「后」字时点进窗拍假设)
    DISCLOSURE_FINAL_SUPPLY_GOLD_SCOPE: 'final_supply_global_once_seq_pos_anchor',
    DISCLOSURE_FINAL_SUPPLY_GOLD_TIMING: 'node_window_entry_beat_pick_miss_is_gone',
    # 策略卡到级金两键(成长基金;载义见键常量注:状态检查型语义未经
    # 实机采证 + 现役经验常量下 9 级不可达到级腿休眠)
    DISCLOSURE_STRATEGY_LEVEL_SEMANTICS: 'pick_already_at_level_also_grants_unverified',
    DISCLOSURE_STRATEGY_LEVEL_DORMANT: 'bound_96_lt_threshold_194_cap_level7',
    ORE_PLANE_START_PENDING: 'face_gold_color_auto_open_unverified',
    # 环境 XP 窗口通道披露键族(单一源 = kernel/cw_game_state
    # ENV_XP_WINDOW_DISCLOSURES,本处整表合并不复制键名)。
    **ENV_XP_WINDOW_DISCLOSURES,
}

#: 单局驱动步上限(防流程死循环;正常局 < 2000 动作)。
MAX_STEPS: int = 5000

#: 开局词缀采样张数(占位:实机简报词缀张数分布候实机补档)。
AFFIX_SAMPLE_COUNT: int = 3

#: 模态屏族(选卡/弹窗呈现态; dismiss 事件返回底层屏)。
_MODAL_SCREENS: frozenset[str] = frozenset({
    SCREEN_INVEST_ENV, SCREEN_INVEST_STRATEGY, SCREEN_BOX, SCREEN_EXPERT,
    SCREEN_MEGASTAR, SCREEN_PLANNER, SCREEN_SHOP,
})

#: sim 不可呈现浮层的「在场锚」(画面档 → 锚 area 集;3.4 联调 visible
#: area 级细化)。这些锚门控同屏上的分支分派(如备战帧的阿哈装备选择
#: 浮层检测):画面档匹配语义会把它们误答真 → 备战帧被浮层分支抢走。
#: sim 不建模该浮层 → 锚恒不可见 = 世界真值(呈现态查询语义)。
_UNPRESENTED_OVERLAY_ANCHORS: dict[str, frozenset[str]] = {
    SCREEN_PREP: frozenset({'标识-简易装备'}),
}


@dataclass(frozen=True)
class SimRunResult:
    """局结果面(消费方 = 运行器断言;纯结果无评判;
    位面/轮次读容器节点键)。"""

    final_hp: int
    plane_reached: int
    rounds: tuple[int, int]
    hp_trail: tuple[int, ...]
    unmodeled: dict[str, object]


# ============================================================ 声明驱动推进
# (动作后果声明 WorldDecl 的 advance 分派;设计件 = 动作后果声明化迭代
#  总纲 design.md §2.2 契约 5 + 详设 details/world-decl.md §3。转移事件
#  分派已停用:单动作单轨,advance 只承载已迁移动作的
#  trigger,同一动作任一时刻只有一条驱动路径。)

#: advance 分派表键集(``trigger`` 封闭集代码单一源;权威表 = 详设
#: world-decl.md §3,值零新词沿用现役动作名)。``''`` = 纯画面转移,
#: 恒合法(backend 只按 ``next_screen`` 推进,零专属过程);3.3 起 9 类
#: 过程 + 纯转移全量收齐,18 转移动作声明驱动全覆盖;2026-10-17 迭代
#: T-3 增 ``spy_shop_refresh``(商业间谍升级回调世界分支:上报声明触发,
#: 非转移动作——next_screen 恒备战档,零画面转移);2026-10-19 用户
#: 裁定批增 ``refresh_invest_env``/``refresh_invest_strategy``(投资
#: 两屏刷新世界分支,上报声明触发,同屏重呈现零转移);2026-10-29 流程
#: 模型对齐批:``pick_encounter`` 自 ``battle_resolve`` 拆出(遭遇选完
#: 回备战并自动弹店,遭遇战改由出战触发——旧「选档落地即结算」随呈现
#: 改造废止;``battle_resolve`` 现役唯一来源 = 出战声明)。
ADVANCE_TRIGGER_KINDS: frozenset[str] = frozenset({
    '', 'node_advance', 'battle_resolve', 'open_box', 'pick_box_card',
    'pick_megastar', 'pick_planner', 'pick_supply', 'pick_invest_env',
    'pick_invest_strategy', 'spy_shop_refresh', 'pick_encounter',
    'refresh_invest_env', 'refresh_invest_strategy',
})

#: 对账豁免场景键(建模内合法失配 = 最上层呈现屏 ≠ 底层稳态画面,
#: 断言延后至稳态;场景判定 = :meth:`SimBackend._reconcile_exempt_reason`
#: 逐字面量返回,禁第二登记面):
#: ① overlay 队列命中(``overlay_pending``:``_window_resume='offer'`` +
#:    ``_present_pending_overlay`` 呈现巨星/planner 等);
#: ② offer 日程命中(``offer_presented``:呈现投资策略屏);
#: ③ 节点窗让路恢复位未消费(``window_resume_pending``:让路期间选卡族
#:    经 ``_dismiss_modal`` 恢复到 offer 屏/节点屏)。

#: 对账漂移保留证据的 disclosures 键(声明与状态机画面漂移早期警报;值 =
#: 漂移明细串列表,缺陷保留证据不停机)。
DECL_SCREEN_DRIFT: str = 'decl_screen_drift'


@dataclass
class SimBackend:
    """sim 游戏后端(一实例一局;端口协议实现 + 画面状态机 + 世界规则件)。

    构造即 reset(开局序列:词缀/boss 名单采样并写容器 → 简报屏 →
    (env_present)投资环境屏 → wait_one_one → P1r1 对应屏);运行面 =
    端口六口 + kernel 事实事件 sink 订阅,世界推进全部由流程驱动
    (动作分支 = op → 上报函数族,本后端零私有动作语义)。
    """

    #: 局级输入(确定性锚;词缀入 seed 后此字段语义 = override 见下)。
    seed: int
    cfg: RunConfig
    #: 世界容器(组合,唯一一份)。
    gs: GameState = field(init=False)
    # —— 画面状态机(私有;状态 = 档名 + 子态) ——
    _screen: str = field(init=False, default='')
    _sub: str = field(init=False, default='')
    #: 上次广播画面值(:meth:`_announce_screen` prev_screen 行来源;初值 =
    #: 容器 prev_screen 冷建空串。值级豁免点(SETTLE/LOBBY)不经过本字段
    #: ——prev 语义 = 上次广播值,非上次状态机赋值)。
    _announced_screen: str = field(init=False, default='')
    #: 模态返回目标(呈现模态时的底层屏;None = 无挂起返回)。
    _return_screen: str | None = field(init=False, default=None)
    _return_sub: str = field(init=False, default='')
    #: 节点窗口让路恢复位('' = 无挂起):overlay/offer 呈现压住节点屏
    #: 时的续跑点。'offer' = 让路结束复走 offer 检查;'node' = offer 屏
    #: 返回后直出节点屏。让路不吞 offer 槽(权威序 = 旧引擎实测收尾
    #: 检查序 overlay → offer → 下一节点,overlay 选定复走 offer 检查;
    #: U07 固定日程生效于本节点备战窗口前)。
    _window_resume: str = field(init=False, default='')
    # —— 采样簿记(实机不可观察,后端私有) ——
    excluded_invest: set[str] = field(default_factory=set)
    excluded_env: set[str] = field(default_factory=set)
    #: 策略三选一呈现全局序(1 基;品质改写判据坐标系,与
    #: ``ENV_POOL_REWRITE.rewrite_picks`` 同基)。自增点 = offer 分支实际
    #: 呈现时点(`_present_offer_or_node_screen` 内),呈现一次计一次:
    #: 开局环境 offer 走 opening 形态不经该函数不计数;overlay 让路复走
    #: 在实际呈现前不进分支,无双计。sim 私有簿记,非 GameState 观察域。
    _invest_pick_ordinal: int = field(init=False, default=0)
    #: 投资策略 offer 刷新授权簿记(当前窗口;2026-10-19 用户裁定「sim 与
    #: 实机一致提供刷新次数」批):_offer_refreshable = 当前呈现的 offer
    #: 是否可刷新(固定日程槽 True / 联席额外槽 False——联席 desc 未写明
    #: 刷新语义,保守不呈现,随实机首遇或裁定收口);_offer_forced_slots =
    #: 本窗口品质改写槽位向量(空元组 = 无改写;刷新重掷沿用同向量 =
    #: 槽位品质承诺跨刷新保持,卡面语义直读);_offer_refresh_seq = 本
    #: 窗口刷新流水号(rng 流键分量,呈现时点归零)。观察真值(计数/候选)
    #: 一律走容器(report 观察写端),本组只承载「呈现授权」簿记。
    _offer_refreshable: bool = field(init=False, default=False)
    _offer_forced_slots: tuple[str, ...] = field(init=False, default=())
    _offer_refresh_seq: int = field(init=False, default=0)
    #: 商店牌面节点级记录(牌面 = 节点级持久事实,发牌时定;2026-10-17
    #: 用户裁定):值 = 商店在屏期间 ``gs.shop`` 的最后非空观测(跟随
    #: 发牌/刷新/买卡一切写点,驱动入口懒同步
    #: :meth:`_sync_shop_record`);开店呈现写回消费(:meth:`_open_shop`,
    #: 对偶实机「每次进店读屏」)。关店清 ``gs.shop`` 呈现不清本记录;
    #: 节点窗起新发牌自然覆盖(整店锁跳过发牌 = 牌面跨节点保留,同语义)。
    _shop_record: ShopPayload | None = field(init=False, default=None)
    # (私有 overlay 队列与评估器簿记三件[队列/一次性标志/银狼星基线/
    #  巨星水位]已停用:sim 呈现数据源 =
    #  容器登记 gs.screen_changes.pending,判据簿记 = ScreenChanges
    #  sidecar,呈现检查 = 问询时点[screen_identity] + advance 尾。)
    #: 武装箱待授予候选下标(装备卡点击源记录;pick_box_card 落地消费)。
    _box_pick_pending: int | None = field(init=False, default=None)
    #: 策略选卡即时经验腿呈现闩(offer 呈现置 True、落地拍消费置 None;
    #: 无闩的重复 advance = 零写防重放)。私有暂态不入容器/不入快照恢复
    #: (:data:`_box_pick_pending` 同形先例)。
    _strategy_pick_xp_latch: bool | None = field(init=False, default=None)
    #: 策略选卡连胜置位腿呈现闩(与 xp 闩同点置位同拍消费,独立不共享:
    #: 两腿语义独立,共享闩会让单腿测试直读互相牵连且无状态量收益)。
    #: 防重放实害 = 置位后战斗推进再重放会把已转移真值回写成置位值。
    #: 私有暂态不入容器/不入快照恢复(同形先例同上)。
    _strategy_pick_streak_latch: bool | None = field(init=False, default=None)
    #: 策略选卡出售发牌腿呈现闩(板面重写族出售支;与 xp/streak 闩同点
    #: 置位同拍消费,独立不共享——三腿语义独立,共享闩会让单腿测试直读
    #: 互相牵连且无状态量收益)。防重放实害 = 无闩的重放 advance 会把
    #: 5 只 2★ 二次发放(发放非幂等,与置位腿同害级)。私有暂态不入
    #: 容器/不入快照恢复(同形先例同上)。
    _strategy_pick_sell_deal_latch: bool | None = field(init=False,
                                                        default=None)
    #: 策略选卡即时生命腿呈现闩(hp 通道;与 xp/streak/sell-deal 闩同点
    #: 置位同拍消费,独立不共享——四腿语义独立,共享闩会让单腿测试直读
    #: 互相牵连且无状态量收益)。防重放实害 = 无闩的重放 advance 会把
    #: +N hp 二次发放(直加非幂等,与置位/发牌腿同害级)。私有暂态不入
    #: 容器/不入快照恢复(同形先例同上)。
    _strategy_pick_hp_latch: bool | None = field(init=False, default=None)
    # —— 局结果面(消费方 = 运行器断言) ——
    hp_trail: list[int] = field(default_factory=list)
    disclosures: dict[str, object] = field(default_factory=dict)
    #: 难度账快照(每场战斗结算时点一条;2026-10-14 用户裁定:sim 对
    #: 选择后的难度做记录更新)。落账点/输入口径/零结算耦合边界见
    #: :class:`DifficultyRecord` 与 :meth:`_resolve_battle`;胜负建模
    #: 明文另批,本面只记录。
    difficulty_records: list[DifficultyRecord] = field(default_factory=list)
    done: bool = field(init=False, default=False)
    #: 已完成结算的节点键(重入幂等守卫;战斗结算每节点恰一次)。
    _settled_key: tuple[int, int] | None = field(init=False, default=None)
    #: 已进窗的节点序位(节点推进重入幂等守卫;None = 尚无)。
    _entered_pos: NodePos | None = field(init=False, default=None)
    #: 已收尾节点窗口的节点序位(None = 尚无;窗口前段幂等守卫,
    #: :meth:`_begin_node_window`)。
    _window_begun_pos: NodePos | None = field(init=False, default=None)
    #: 扑满节点递延收入快照(None = 非扑满窗或已落账):统一公式
    #: 「战败时无连胜成分」需胜负,窗口开时未知 → 基数冻结(金/进轮
    #: 连胜/收入修饰 = 轮初口径),结算分支胜负后落账并清回 None。
    _piggy_income_snap: (tuple[int, int, tuple[float, int, int | None]]
                         | None) = field(init=False, default=None)
    #: 对账延后声明队列(豁免场景内 next_screen 等值断言延后至稳态,
    #: :meth:`_reconcile_next_screen`;元素 = (延后时点已进窗节点序位,声明),
    #: 每次 advance 入口消费)。
    _pending_reconcile: list[tuple[NodePos | None, WorldDecl]] = field(
        init=False, default_factory=list)
    _steps: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        if self.cfg.game_mode != '标准博弈':
            raise ValueError(
                f'对局类型 {self.cfg.game_mode!r} 不在首版辖域'
                '(sim 首版 = 标准博弈;非标准值显式拒,不猜差异)')
        self.disclosures.update(_BASE_DISCLOSURES)
        # 词缀入 seed(流键 reset/affixes):RunConfig.enemy_affixes 降级
        # override(定向测试定词缀用);常规局按注册表键集采样。
        affixes = tuple(self.cfg.enemy_affixes) \
            or self._sample_affixes(self.seed)
        cfg = replace(self.cfg, enemy_affixes=affixes)
        self.gs = GameState(schema_version=GAME_STATE_SCHEMA_VERSION)
        # 开局种子底座(与实机局容器冷建即种同契约:获得链/上报函数族的
        # 拒落档门以底座在场为前提;seed 值 = 常量基线,apply_opening 随后
        # 以 obs 真值覆盖,确定性不受影响)。
        seed_opening_state(self.gs)
        apply_opening(self.gs, cfg, stream_rng(self.seed, 'M01/opening_hand'))
        bosses = resolve_plane_bosses(cfg.boss_roster_override,
                                      stream_rng(self.seed, 'M20/boss'))
        self.gs.observe(self.gs.plane_bosses, list(bosses),
                        evidence=sim_evidence('boss:roster'),
                        sig=obs_sig(group_id='sim:boss'))
        self.gs.observe(self.gs.shop_locked, False,
                        evidence=sim_evidence('shop_lock:v1_unlocked'),
                        sig=obs_sig(group_id='sim:shop'))
        self.gs.observe(self.gs.diamond_count, 0,
                        evidence=sim_evidence('diamond:opening'),
                        sig=obs_sig(group_id='sim:diamond'))
        self._hp_trail_append()
        # 初始序列:简报屏(词缀 + boss 载荷已写容器;env 屏在简报下一步
        # 之后呈现,权威源 = screens/briefing.md 进入链)。
        self._announce_screen(SCREEN_BRIEFING)
        self._screen = SCREEN_BRIEFING

    # ---------------------------------------------------------- 初始序列

    def _sample_affixes(self, seed: int) -> tuple[str, ...]:
        """开局词缀采样(流键 ``reset/affixes``;池 = affix_effects_data
        注册表键集均匀无放回;张数/分布占位,披露键恒已登记)。"""
        rng = stream_rng(seed, 'reset/affixes')
        pool = sorted(AFFIX_EFFECTS)
        return tuple(rng.sample(pool, min(AFFIX_SAMPLE_COUNT, len(pool))))

    # ---------------------------------------------------------- 端口五口

    def screen_identity(self) -> str:
        """当前画面 screen_info 档名(状态机唯一答口)。

        问询时点呈现检查(事实事件槽停用后的
        sim 懒呈现位):答身份前先查容器登记 pending——动作上报内已
        register 的条目在此压上模态(等价实机「动作落地即弹」,时点 =
        宿主返回后的首次身份问询)。呈现门/消费披露族语义同
        :meth:`_present_pending_overlay`(fortune 门判当前底层)。
        """
        self._maybe_finish_wait()
        self._sync_shop_record()
        if self.gs.screen_changes.pending:
            self._present_pending_overlay()
        return self._screen

    def observe(self, screen_name: str) -> object:
        """生成器直出该屏观察产物(注册表分派)。

        注册表 = ``sim/cw_sim_obs_gen``(键 = screen_info 档名;金路径 13
        档,同档名子态由该档名生成器按状态机子态内部分派)。产物经同名
        ``report_screen_*`` 落容器(写通道铁律,单一源在 report 消费端)。
        未注册屏呈现 = :class:`LookupError` 具名响错(防静默失真,
        flow-seam §3 锁)。惰性导入注册表:注册表反向引用本模块档名
        常量,模块级互引成环。"""
        self._sync_shop_record()
        from sr_od.application.currency_war.sim.cw_sim_obs_gen import (
            observe_screen,
        )
        return observe_screen(self, screen_name)

    def visible(self, screen_name: str, area_name: str) -> bool:
        """until / 门可见性问询。

        3.2 语义 = 画面档匹配(问询屏 == 当前呈现屏;模态屏族在场时
        底层屏区域不可见)。3.4 联调细化 = 不可呈现浮层的在场锚恒
        False(:data:`_UNPRESENTED_OVERLAY_ANCHORS`,呈现态查询语义)。
        等待变体(wait_one_one)在问询时立即完成(sim 世界瞬时呈现,
        动画无时间维)。"""
        self._maybe_finish_wait()
        self._sync_shop_record()
        if screen_name != self._screen:
            return False
        return area_name not in _UNPRESENTED_OVERLAY_ANCHORS.get(
            screen_name, ())

    def click_answer(self, op, screen_name: str, area_name: str,
                     until_find_all, until_not_find_all):
        """sim 点击应答:先处理点击源(状态机转移),再出实机同形
        round 结果(机械镜 = :func:`cw_sim_ports.mirror_click_answer`;
        until 问询经 :meth:`visible` 取转移后真值)。"""
        self._maybe_finish_wait()
        self._sync_shop_record()
        self._handle_click_source(screen_name, area_name)
        self._tick()
        return cw_sim_ports.mirror_click_answer(
            op, screen_name, area_name, until_find_all, until_not_find_all)

    # ---------------------------------------------------------- 点击源

    def _handle_click_source(self, screen_name: str, area_name: str) -> None:
        """点击源分派(不入 kernel 事件集的推进型点击;逐 case =
        flow-seam 附录 B 边界登记面)。"""
        if screen_name == SCREEN_BRIEFING and area_name == '按钮-下一步':
            self._advance_briefing()
        elif screen_name == SCREEN_BOSS_BRIEFING \
                and area_name == '区域-空白点击':
            # 2026-10-29 流程模型对齐:简报点空白关闭模态回备战并自动
            # 弹店(#14 触发源「BOSS 简报关闭后」),boss 战由出战动作
            # 触发(battle_resolve);旧「点空白 → _resolve_battle 直接
            # 结算」随呈现改造废止。
            self._dismiss_and_settle_prep()
        elif screen_name == SCREEN_PLANE_TRANSITION \
                and area_name == '区域-空白点击':
            self._begin_node_window()
        elif screen_name == SCREEN_SUPPLY and area_name == '文本-剩余次数':
            self._supply_refresh()
        elif screen_name == SCREEN_BOX and area_name.startswith('装备卡-'):
            self._record_box_click(area_name)
        elif screen_name == SCREEN_PREP and area_name == '按钮-商店':
            self._open_shop()

    def _advance_briefing(self) -> None:
        """简报下一步:env_present 且未定局 → 投资环境屏(M02 采样);
        否则 → wait_one_one 变体。"""
        if self.done:
            return
        if self.cfg.env_present and not (self.gs.active_env.value or ''):
            if self._screen != SCREEN_INVEST_ENV:
                rng = stream_rng(self.seed, 'M02/env-offer')
                opts = sample_env_offer(rng, self.excluded_env)
                self._present_modal(SCREEN_INVEST_ENV)
                # 环境整组刷新呈现(2026-10-19 用户裁定批):基准 1 次
                #(单全局钮整组重掷;advantage_layouts「环境刷新」行),
                # 计数经 report 观察写端落 env_refresh_left,重掷世界分支
                # = _refresh_invest_env。
                report_screen_invest_env_obs(self.gs, CwScreenInvestEnvObs(
                    hit=True,
                    options=[(n, (i + 1) * 10) for i, n in enumerate(opts)],
                    refresh=(ENV_REFRESH_BASE, 10, 20)))
            return
        self._enter_wait_one_one()

    def _enter_wait_one_one(self) -> None:
        """wait_one_one 变体(开局补给动画等待;sim 瞬时呈现,下次问询
        即完成进 P1r1)。"""
        self._announce_screen(SCREEN_PREP)
        self._screen = SCREEN_PREP
        self._sub = PREP_SUB_WAIT_ONE_ONE

    def _maybe_finish_wait(self) -> None:
        """等待变体惰性完成(任何问询/点击时点动画已完成 → 进 P1r1)。"""
        if self._sub == PREP_SUB_WAIT_ONE_ONE and not self.done:
            self._sub = ''
            self._enter_node_window((1, 1))

    def _supply_refresh(self) -> None:
        """补给免费刷新(点击源;剩余闸:left>0 才刷,刷后 left−1;选项
        重掷流键与旧引擎计数闸等价推导一致)。"""
        left = self.gs.supply_refresh_left.value
        if left is None or int(left) <= 0:
            return
        plane, r = self._node_pos()
        used = 1 - int(left)   # 旧计数闸等价推导(保持流键稳定)
        self.gs.observe(self.gs.supply_refresh_left, max(0, int(left) - 1),
                        evidence=sim_evidence('supply:refresh'),
                        sig=obs_sig(group_id='sim:supply'))
        rng = stream_rng(self.seed,
                         f'M18/opts/p{plane}/r{r}/refresh{used + 1}')
        opts = supply_options(rng, normalize_invest_name(
            str(self.gs.active_env.value or '')))
        report_screen_supply_node_obs(self.gs, CwScreenSupplyNodeObs(
            in_node=True, options=list(opts), refresh_left=None))

    def _record_box_click(self, area_name: str) -> None:
        """武装箱候选点击记录(装备卡-N 建档序 = box_card_names 下标;
        授予在 pick_box_card 落地事件消费)。"""
        try:
            idx = int(area_name.rsplit('-', 1)[1]) - 1
        except (IndexError, ValueError):
            return
        self._box_pick_pending = idx

    def _open_shop(self) -> None:
        """开店点击源(备战 → 开商店态;close_shop 声明后返回)。

        呈现写回(2026-10-17 用户裁定,对偶实机「每次进店读屏」):
        离屏态(关店已清 ``gs.shop``)以节点级牌面记录
        (:attr:`_shop_record`)补写——实机每次进店 live 漏斗重读屏写
        payload,sim 无识别面,以发牌期记录承载同一观察语义;在屏态
        (节点窗起刚发牌)保持现值零写。

        刷价呈现写回(改价分支 sim 载体):每次开店以 kernel 渲染的世界
        真值(:func:`cw_economy.world_shop_refresh_cost`,付费计数达注册
        改价阈值即新价)现算写 ``gs.shop_refresh_cost``——对偶实机每次
        进店 live 漏斗重读刷价;不走 write_logic,观察域字段只收观察
        写端,渲染值 = sim 的「屏面显示」,与 live OCR 读数同渠道同格。
        节奏 = 开店(非持续写),不开店不写。"""
        if self._screen == SCREEN_PREP:
            self._present_modal(SCREEN_SHOP)
            self.gs.observe(self.gs.shop_refresh_cost,
                            world_shop_refresh_cost(self.gs),
                            evidence=sim_evidence('shop:reopen'),
                            sig=obs_sig(group_id='sim:shop:reopen'))
            if self.gs.shop.value is None and self._shop_record is not None:
                self.gs.observe(self.gs.shop, self._shop_record,
                                evidence=sim_evidence('shop:reopen'),
                                sig=obs_sig(group_id='sim:shop:reopen'))

    def _settle_on_prep(self) -> None:
        """落到备战档并按自动弹店规则呈现(2026-10-29 流程模型对齐,
        流程模型单一源 = ``docs/game/currency_war/research/screen_flow_
        timing.md`` 口述流程模型节 + #14):节点窗收尾或节点弹窗关闭回到
        备战后,游戏自动弹出商店(bot 视角 = 开商店态直接呈现,策略器
        商店会话经外循环商店访问路径接管);商店收起回备战 = 可操作主
        窗口(close_shop 声明走 '' 纯转移 dismiss,不经本 helper,零
        重弹面)。

        1-1 例外不弹(#29:开局奖励替代商店;等待变体完成后进窗照常
        走本 helper,例外内置)。``_sub`` 不在本 helper 内清理——子态
        (晶矿面板等)由调用方在调用前置定,弹店经 ``_present_modal``
        保存 ``_return_sub``、关店恢复,子态跨商店会话存续与实机一致
        (商店收起后晶矿面板仍在)。"""

        self._announce_screen(SCREEN_PREP)
        self._screen = SCREEN_PREP
        node = self.gs.node.value
        if node is not None and (node.plane, node.round_num) != (1, 1):
            self._open_shop()

    def _dismiss_and_settle_prep(self) -> None:
        """关闭节点弹窗模态回备战并弹店(弹窗选完类落点统一口;
        节点窗让路恢复位优先——resume 场景落 offer/节点屏,不弹店,
        由 resume 消费链的落点自行触发)。"""
        self._dismiss_modal()
        if self._screen == SCREEN_PREP:
            self._settle_on_prep()

    def _sync_shop_record(self) -> None:
        """商店牌面记录懒同步(全部驱动入口调用):在屏 payload 非
        ``None`` 即跟随记录。

        跟随面 = ``gs.shop`` 的一切写点——节点窗起发牌(deal_shop)、
        动作分支刷新/买卡(kernel 上报,均新建 payload 整体替换)。payload
        写入与下次开店之间必经驱动入口(策略帧循环先观察后决策,动作
        声明经 advance、开店经 click_answer),故入口同步即完整覆盖;
        离屏态(关店清 ``None``)不动记录——关店清的是呈现不是记录,
        节点级持久事实由本记录承载。"""

        payload = self.gs.shop.value
        if payload is not None:
            self._shop_record = payload

    def _apply_spy_shop_refresh(self) -> None:
        """商业间谍升级回调世界分支(2026-10-17-levelup-shop-transition
        design §2.3 步①-③;触发 = 升级上报 world_decl
        ``spy_shop_refresh``,动作 op 经 cw_sim_ports.declare_world 喂入;
        步④置信号 = kernel 上报回调,写端唯一,不经本层)。

        - ①抽 5 张:费用档按升级后等级概率表(单一源 =
          :func:`effective_deal_probs`,轮岗在场同款重掷);流键沿用发牌
          口径(M22/spy-deal|M22/spy-rotation,模块号沿 M21 续);发牌
          算法本体 = kernel ``sample_shop_deal`` 单一源,采样即世界真值;
        - ②偷最贵 3 张 → 备战席真实入席(席满溢出 = 不入席 + 计数披露,
          design §2.3 申报的 sim 先行形态;最贵序 = 费用降序 → 星级降序
          → 槽位升序确定性破并列);入席 = 容器 bench 观察直写(sim 世界
          真值通道,与 deal_shop 写 shop 同款;不级联合成——design 未
          申报偷取合成语义,保守不猜);
        - ③剩余 2 张 = 商店新牌面:容器 shop 观察直写(被偷槽位置空,
          剩余槽位原位保留)+ 经 :meth:`_sync_shop_record` 入节点级记录
          → 下次开店呈现之(不重新发牌——刷新已在本回调发生)。

        计数披露(sim 私有簿记,键域:spy_deal_count / spy_steal_placed_
        count / spy_steal_overflow_count)= 抽牌次数 / 入席张数累计 /
        溢出张数累计;判读面计数键(cw4_counters.spy_steal_placed_frames /
        spy_steal_overflow_frames)= 帧级增量,经容器挂接的策略器状态
        鸭子读回写(未挂接帧静默跳过 = 无判读面,合法)。持有判定不在
        本层(上报回调已闸;本层被声明即执行,声明构造点零副作用无持卡
        不构造)。"""
        from sr_od.application.currency_war.kernel.cw_game_state import (
            BenchSlot,
            BenchView,
            ShopSlot,
            Unit,
        )
        new_level = int(self.gs.level.value or 3)
        plane, r = self._node_pos()
        rotation_on = (str(self.gs.active_env.value or '')
                       == ROTATION_ENV_NAME)
        deal_rng = stream_rng(self.seed, f'M22/spy-deal/p{plane}/r{r}')
        probs = effective_deal_probs(
            new_level,
            stream_rng(self.seed, f'M22/spy-rotation/p{plane}/r{r}'),
            rotation_on=rotation_on)
        drawn = sample_shop_deal(self.gs, deal_rng, level=new_level,
                                 probs=probs)
        self.disclosures['spy_deal_count'] = \
            self.disclosures.get('spy_deal_count', 0) + 1

        # ②偷最贵 3 张(确定性最贵序)→ 备战席真实入席。
        content = [s for s in drawn.cards
                   if s.kind == 'content' and s.card is not None]
        ranked = sorted(content,
                        key=lambda s: (-(int(s.card.cost or 0)),
                                       -(int(s.card.star or 1)),
                                       int(s.card.slot or 0)))
        top3 = ranked[:3]
        stolen_slots = {id(s) for s in top3}
        view = self.gs.bench.value
        placed = 0
        overflow = 0
        if view is not None:
            slots = list(view.slots)
            for s in top3:
                spot = next((i for i, b in enumerate(slots)
                             if b is None or b.kind == 'empty'), None)
                if spot is None:
                    overflow += 1   # 席满溢出:不入席 + 计数披露(实机
                    continue        # 观察点,design §2.3 申报待证实形态)
                slots[spot] = BenchSlot(
                    kind='unit',
                    unit=Unit(char_id=str(s.card.name or ''),
                              star=max(1, int(s.card.star or 1))))
                placed += 1
            self.gs.observe(self.gs.bench,
                            BenchView(slots=slots, capacity=view.capacity),
                            evidence=sim_evidence('shop:spy_steal'),
                            sig=obs_sig(group_id='sim:shop:spy'))
        else:
            overflow = len(top3)   # bench 未观察 = 无席可入,全溢出保守侧
        self.disclosures['spy_steal_placed_count'] = \
            self.disclosures.get('spy_steal_placed_count', 0) + placed
        if overflow:
            self.disclosures['spy_steal_overflow_count'] = \
                self.disclosures.get('spy_steal_overflow_count', 0) + overflow
        _st = getattr(self.gs, 'strategy_state', None)
        ct = getattr(_st, 'cw4_counters', None) if _st is not None else None
        if isinstance(ct, dict):
            if placed:
                ct['spy_steal_placed_frames'] = \
                    ct.get('spy_steal_placed_frames', 0) + 1
            if overflow:
                ct['spy_steal_overflow_frames'] = \
                    ct.get('spy_steal_overflow_frames', 0) + 1

        # ③剩余 2 张 = 商店新牌面(被偷槽位置空,原位保留)→ 观察直写,
        # _sync_shop_record 懒同步入节点级记录,下次开店呈现。
        new_cards = [ShopSlot(kind='empty') if id(s) in stolen_slots else s
                     for s in drawn.cards]
        self.gs.observe(self.gs.shop,
                        ShopPayload(cards=new_cards,
                                    refresh_probs=drawn.refresh_probs),
                        evidence=sim_evidence('shop:spy_refresh'),
                        sig=obs_sig(group_id='sim:shop:spy'))

    # (事实事件订阅入口已停用删除:
    #  懒呈现位 = screen_identity 问询时点检查;板面真值观察 =
    #  advance 步界 _observe_board_truth。)

    # ------------------------------------------------------ 声明驱动推进

    def advance(self, decl: WorldDecl) -> None:
        """按声明推进世界(声明化主入口;动作后果声明化迭代总纲
        design.md §2.2 契约 5 + 详设 world-decl.md §3)。

        按 ``decl.trigger`` 分派推进(键集单一源 =
        :data:`ADVANCE_TRIGGER_KINDS`,集外值 ValueError 响亮——
        构造点漂移 = 接线 bug 禁静默),完成后
        :meth:`_reconcile_next_screen` 等值对账画面档。世界推进唯一
        驱动 = 本方法(单动作单轨;18 转移动作全量在表);
        ``trigger=''`` = 纯画面转移,
        零专属过程——专家邀请函档 = ``_present_modal`` 呈现(open_bookcard
        腾席写端在其上报,本层只呈现),其余 = ``_dismiss_modal`` 幂等
        返回(节点窗让路恢复位语义保留)。入口先消费
        :attr:`_pending_reconcile`(豁免场景延后的对账在稳态补验)。
        """
        if self.done:
            return
        self._drain_pending_reconciles()
        self._sync_shop_record()
        self._tick()
        if decl.trigger not in ADVANCE_TRIGGER_KINDS:
            raise ValueError(
                f'trigger {decl.trigger!r} 不在 advance 分派表键集 '
                f'{sorted(ADVANCE_TRIGGER_KINDS)}(构造点漂移 = 接线 bug,'
                '禁静默)')
        if decl.trigger == 'node_advance':
            if decl.next_screen == '':
                # 局终声明消费分支(键表示切换批 design §2.6):kernel 终局
                # 事件式(sequence_next = None → applied=True match_end,
                # 声明 next_screen='')的世界消费;kernel 声明权威、sim
                # 对账的分工不变。
                self._on_node_advance_terminal()
            else:
                self._on_node_advance()
        elif decl.trigger == 'battle_resolve':
            self._resolve_battle()
        elif decl.trigger == 'open_box':
            self._on_open_box()
        elif decl.trigger == 'pick_box_card':
            self._on_box_picked()
        elif decl.trigger == 'pick_megastar':
            self._on_overlay_picked('megastar')
        elif decl.trigger == 'pick_planner':
            self._on_overlay_picked('planner')
        elif decl.trigger == 'pick_supply':
            self._on_supply_picked()
        elif decl.trigger == 'pick_encounter':
            self._on_encounter_picked()
        elif decl.trigger == 'pick_invest_env':
            self._on_invest_picked(opening=True)
        elif decl.trigger == 'pick_invest_strategy':
            self._on_invest_picked(opening=False)
        elif decl.trigger == 'spy_shop_refresh':
            # 商业间谍升级回调世界分支(2026-10-17 迭代 design §2.3 步①-③;
            # 步④置信号 = kernel 上报回调,不经本层)。
            self._apply_spy_shop_refresh()
        elif decl.trigger == 'refresh_invest_strategy':
            # 投资策略屏逐卡刷新世界分支(2026-10-19 用户裁定批;上报声明
            # 触发,同屏重呈现零转移)。
            self._refresh_invest_strategy(decl.slots)
        elif decl.trigger == 'refresh_invest_env':
            # 投资环境屏整组刷新世界分支(同上批;环境刷新 = 整组重掷一次)。
            self._refresh_invest_env()
        elif decl.trigger == '':
            # 纯转移(详设 §3 '' 行):统一幂等返回
            #(底层稳态由 _reconcile_next_screen 对账)。专家邀请函档
            # 特判呈现已停用(声明改底层屏)——专家画面的出现事实由
            # 登记(kind = expert_invite,open_bookcard 上报内 register)
            # 承载,呈现走本分支尾的 pending 呈现检查。
            self._dismiss_modal()
        self._reconcile_next_screen(decl)
        self._observe_board_truth()   # 步界板面真值观察(等值零写)
        # overlay 呈现检查(3.4):**仅纯转移分支**——声明改底层屏后
        # open_bookcard/open_tome 的弹窗呈现入口(battle_resolve/
        # node_advance 等其余分派保留原呈现时机 = 各自过程内/节点窗
        # 起点检查,不在 advance 尾提前:overlay 让路序「窗起点 overlay
        # 先于 offer」是旧引擎收尾检查序的锁定语义)。
        if decl.trigger == '':
            self._present_pending_overlay()

    def _reconcile_exempt_reason(self) -> str:
        """当前对账豁免场景(:data:`RECONCILE_EXEMPT_KINDS`;命中 =
        最上层呈现屏 ≠ 底层稳态画面属建模内合法形态,断言延后至稳态;
        ''= 稳态可判)。overlay_trigger 3.4:overlay_pending 检查改读容器
        登记 ``gs.screen_changes.pending``(呈现数据源已迁,旧私有队列
        呈现面已停用)。"""
        if self.gs.screen_changes.pending:
            return 'overlay_pending'
        if self._screen == SCREEN_INVEST_STRATEGY:
            return 'offer_presented'
        if self._window_resume:
            return 'window_resume_pending'
        return ''

    def _drain_pending_reconciles(self) -> None:
        """消费延后对账队列(advance 入口;已入稳态 = 逐声明补验等值,
        失配保留证据后一并清空——每声明对账一次,不重复告警)。仍在豁免
        场景 = 继续延后;**世界已推进过下一节点窗**(进窗序位 ≠ 延后
        时点)= 断言时机已过,静默丢弃(预测的落点屏已被后续窗口替代,
        保留证据只会误报——sim 流程结算驻留快进形态常见)。"""
        if not self._pending_reconcile or self._reconcile_exempt_reason():
            return
        for entered_pos, decl in self._pending_reconcile:
            if self._entered_pos != entered_pos:
                continue
            if self._screen != decl.next_screen:
                self._record_decl_drift(decl, self._screen)
        self._pending_reconcile.clear()

    def _record_decl_drift(self, decl: WorldDecl, actual: str) -> None:
        """声明与状态机画面漂移保留证据(详设 §3 对账面;缺陷保留证据不停机,
        早期警报面 = :attr:`disclosures`)。"""
        self.disclosures.setdefault(DECL_SCREEN_DRIFT, []).append(
            f'{decl.trigger or "<pure>"}|{decl.next_screen or "<end>"}'
            f'|{actual}')

    def _reconcile_next_screen(self, decl: WorldDecl) -> None:
        """推进完成后 ``next_screen`` 等值对账(详设 world-decl.md §3
        对账面)。

        断言对象 = 状态机**底层稳态画面**(让路恢复位消费完、overlay
        队列弹完后的落点屏),对 ``next_screen`` 非空串声明等值断言;
        豁免场景(:data:`RECONCILE_EXEMPT_KINDS`)入延后队列,稳态达成时
        :meth:`_drain_pending_reconciles` 补验。局终双载体:``done`` 世界
        呈现恒 = 大厅(:meth:`_game_over`,声明预测已失效只锁载体);
        ``next_screen=''`` 预测局终而世界未终局 = 漂移。断言不等且不在
        豁免集 = 缺陷保留证据(:data:`DECL_SCREEN_DRIFT`)不停机——声明与
        状态机漂移的早期警报。
        """
        if self.done:
            if self._screen != SCREEN_LOBBY:
                self._record_decl_drift(decl, self._screen)
            return
        if decl.next_screen == '':
            self._record_decl_drift(
                decl, f'done=False screen={self._screen}')
            return
        if self._screen == decl.next_screen:
            return
        if self._reconcile_exempt_reason():
            self._pending_reconcile.append((self._entered_pos, decl))
            return
        self._record_decl_drift(decl, self._screen)

    # ------------------------------------------------ 转移事件 handler 群

    def _on_node_advance(self) -> None:
        """节点推进(终结动作上报触发;kernel report_node_advance 已做
        观察态门与同序位去重,本层再守序位 = 转移事件重入幂等)。键表示
        下不存在越界序位——eff 超真值表总长的局终分支已停用,局终
        = kernel 终局事件式声明,走 :meth:`_on_node_advance_terminal`。"""
        eff = effective_node_pos(self.gs)
        if eff is None or (self._entered_pos is not None
                           and eff <= self._entered_pos):
            return
        # 节点经验在节点推进时入账(被离开节点的类型;首推进无前节点)
        prev = self.gs.node.value
        if prev is not None:
            apply_node_xp(self.gs, node_type=prev.kind)
        # —— 策略卡到级金腿(成长基金 id 101701 首例;条件单一源 =
        # kernel check_strategy_level_grants 纯决策零写):挂经验入账后 =
        # 跨级事件拍,先于新节点窗轮首收入(达标金计入本窗息算基数;
        # 实机跨级金与节点金口径对位未逐帧采证,若实机为「跨级金落上
        # 节点末口径」则本接线零偏差,否则一次性息差 ≤ min(40//10, 5)
        # = 4 金,证伪路径 = 实机局跨级前后两窗利息差分)。双通道:sim
        # 金写全 observe 现役形态(金面禁直写辖效果账本到期接入点,本笔
        # = 世界合成非 logic 直写),闩 = write_logic(非金 Field 登记事
        # 实直写,discharge_due_item_grants 先形);组名沿 sim:strategy
        #(策略战后发放腿首落在役组)。现役 sim 经验常量下 9 级不可达
        #(节点 70 + 选卡即时腿 26 = 上界 96 < 3→9 级门槛 194)= 休眠
        # 正确路径恒短路零写,经验源扩网零改激活;幂等 = 决策函数 done
        # 闩短路 + 本层序位守卫双保险。
        _grant = check_strategy_level_grants(self.gs)
        if _grant is not None:
            _name, _amount = _grant
            self.gs.observe(
                self.gs.gold, int(self.gs.gold.value or 0) + _amount,
                evidence=sim_evidence(f'strategy:level_gold:{_name}'),
                sig=obs_sig(group_id='sim:strategy'))
            self.gs.write_logic(
                self.gs.strategy_conditional_done,
                tuple(self.gs.strategy_conditional_done.value or ())
                + (_name,),
                produced_by=LEVEL_GRANT_PRODUCER,
                evidence=f'strategy:level_gold:{_name}',
                sig=logic_sig('sim:strategy'))
        # —— 策略卡到级装备腿(钻石商人;条件单一源 = kernel
        # check_strategy_level_equip_grants 直写形态:发放 + 落闩两笔均
        # 在 kernel 函数内,logic 渠道,组名沿 sim:strategy 在役组)。
        # 接线点 = 经验入账后、新节点窗前(宝钻的 deploy_cap +1/后排格数
        # 自本窗生效 = 世界真值序);返回非 None → 宝钻回调(入参只传
        # 装备名,sig 由回调内构 obs 族,深井发放路径同分工)。live 结算
        # 位同函数零回调。现役经验常量下 9 级不可达 = 休眠正确路径恒
        # 短路零写;幂等 = kernel 函数 done 闩短路 + 本层序位守卫双保险。
        _equip_grant = check_strategy_level_equip_grants(
            self.gs, logic_sig('sim:strategy'))
        if _equip_grant is not None:
            on_diamond_acquired(self.gs, _equip_grant)
        self._entered_pos = eff
        self._enter_node_window(eff)

    def _on_node_advance_terminal(self) -> None:
        """胜利终局声明消费分支(trigger=node_advance ∧ next_screen=''):
        kernel 终局事件式声明(推进超出序列表末位面,现役 = 位面 3 末
        boss 结算存活)的世界消费——XP 入账(被离开节点类型,与现行
        局终前入账同序)+ 胜局披露 + 终局。hp 归零败局走结算死亡分支
        (:meth:`_resolve_battle` → :meth:`_game_over`,不经本分支)——
        披露集含 :data:`DISCLOSURE_RUN_COMPLETE` 与否 = 胜负判别单一源。
        此后 :meth:`_reconcile_next_screen` 走 done=True ∧ decl='' 合格
        分支,漂移面零新增。"""
        prev = self.gs.node.value
        if prev is not None:
            apply_node_xp(self.gs, node_type=prev.kind)
        # —— 策略卡到级金腿局终点(与推进点同段决策/双通道写,挂经验
        # 入账后、局终声明前 = 末节点跨级发放先于局终;双点为经验源扩网
        # 后前瞻一致——现世界不可达下与单点行为全等,单点则「局终跨级
        # 一次性缺口」永久缺失。通道/组名/休眠依据同推进点注释,不赘)。
        _grant = check_strategy_level_grants(self.gs)
        if _grant is not None:
            _name, _amount = _grant
            self.gs.observe(
                self.gs.gold, int(self.gs.gold.value or 0) + _amount,
                evidence=sim_evidence(f'strategy:level_gold:{_name}'),
                sig=obs_sig(group_id='sim:strategy'))
            self.gs.write_logic(
                self.gs.strategy_conditional_done,
                tuple(self.gs.strategy_conditional_done.value or ())
                + (_name,),
                produced_by=LEVEL_GRANT_PRODUCER,
                evidence=f'strategy:level_gold:{_name}',
                sig=logic_sig('sim:strategy'))
        # —— 策略卡到级装备腿局终点(与推进点同段直写形态/组名,挂经验
        # 入账后、胜局披露前 = 末节点跨级也发放;双点为经验源扩网后前瞻
        # 一致——现世界不可达下与单点行为全等。宝钻回调分工与休眠依据
        # 同推进点注释,不赘)。
        _equip_grant = check_strategy_level_equip_grants(
            self.gs, logic_sig('sim:strategy'))
        if _equip_grant is not None:
            on_diamond_acquired(self.gs, _equip_grant)
        self.disclosures[DISCLOSURE_RUN_COMPLETE] = 'survived_p3_boss'
        self._game_over()

    def _on_supply_picked(self) -> None:
        """补给选定落地:带钻选项给宝钻(世界事实写容器 diamond_count;
        钻信息 = 容器 chosen_supply 现值 2 元组 (角色,装备名列表) 按
        :data:`DIAMOND_EQUIP_NAMES` 名单派生(列表任一件名命中即钻;
        写端 = 补给画面 op 确认即写)。派生失败边 = 钻名 OCR 误读 →
        列表名不匹配 → 宝钻发放分支漏发;装备观察(整表)与钻数观察下一帧
        暴露失配,fail-visible 非静默)。

        落点(2026-10-29 流程模型对齐):关闭补给模态回备战并自动弹店
        (#14 触发源「补给选择完后」);节点推进归出战动作
        (``supply_finish``),本分支零推进。"""
        chosen = self.gs.chosen_supply.value
        if chosen is not None and any(
                n in DIAMOND_EQUIP_NAMES for n in chosen[1]):
            cur = int(self.gs.diamond_count.value or 0)
            self.gs.observe(self.gs.diamond_count, cur + 1,
                            evidence=sim_evidence('supply:diamond'),
                            sig=obs_sig(group_id='sim:diamond'))
        self.disclosures.setdefault(SUPPLY_DIAMOND_SLOT_PENDING,
                                    'uniform_slot')
        self._dismiss_and_settle_prep()

    def _on_encounter_picked(self) -> None:
        """遭遇选定落地(2026-10-29 流程模型对齐):关闭遭遇模态回备战
        并自动弹店(#14 触发源「遭遇选择完后」);遭遇战由出战动作触发
        (battle_resolve 消费 ``chosen_encounter`` 现值,时点后移不改
        消费语义——确认时已写容器)。效果面零写入(选档已由 kernel 上报
        落 ``chosen_encounter``,本层零效果)。"""
        self._dismiss_and_settle_prep()

    def _on_invest_picked(self, *, opening: bool) -> None:
        """投资选卡落地(效果 = kernel 获得链,经 report_action_pick_*
        已写容器;本层返回 + 去重集累计,排除集读容器 opts 现值)。"""
        opts = (self.gs.invest_env_opts.value if opening
                else self.gs.invest_strategy_opts.value) or []
        (self.excluded_env if opening else self.excluded_invest).update(opts)
        # 追加随机环境型(在册名 = cw_investments.ENV_REROLL_NAMES,现役
        # 唯一 = 蓝海 id113):选卡首链(上报函数)已完成「获得本环境」全部
        # 写分支(active_env + 即时金 + 申报行);本分支紧接世界掷骰出卷中名,
        # 原语二次入链「获得卷中环境」(gain_invest_env 一次调用完成
        # active_env 改写 + 节点序列场改写 + 登记分支 + on_env_gained 全族
        # 效果,零新发放实现;两次获得语义,追加非替换)。无重复发金:池
        # 排除在册名后无任何 gold_instant 条目。session=None:本层字段面
        # 无会话可取,登记分支跳过、容器写照常(gain_invest_env None 语义)。
        # rng 必须显式传参:gain_invest_env/on_env_gained 的 rng
        # 形参缺省回退自掷(random.Random()),池含随机支环境(人才引进),
        # 不传则同 seed 不重放——双流键解耦,不走动作分支注入槽(该槽服务
        # 上报函数族按调用序取键,本分支直调 kernel 显式流键零耦合)。门条件
        # 读 active_env 现值:二次入链后名已非名单成员,天然不重入。
        # 位置不变式:必须在 _after_modal_pick(进 1-1 节点窗)之前完成
        # 改写——窗口起点起全部环境门控读 active_env 现值,先改写再进窗。
        env_now = str(self.gs.active_env.value or '')
        if env_now in ENV_REROLL_NAMES:
            pool = sorted(n for n in INVESTMENT_ENVS
                          if n not in ENV_REROLL_NAMES)
            rolled = pool[stream_rng(
                self.seed, 'M02/env-reroll').randrange(len(pool))]
            self.disclosures.setdefault(ENV_REROLL_ASSUMPTION_POOL,
                                        'uniform_v0')
            gain_invest_env(self.gs, None, rolled, rand=False,
                            sig=logic_sig(group_id='act:sim@env-reroll'),
                            producer='SimBackend',
                            rng=stream_rng(self.seed,
                                           'M02/env-reroll-gift'))
        # 选卡落地拍连胜置位腿(通用通道,辖域 = 注册表 streak_set≠0
        # 全体)。必须在难度旗牌更新之前:旗牌读 gs.streak 现值写备战
        # 难度,先置位旗牌才随新值(伟大征服难度+连胜项同拍反映置位后
        # 真值,实机对齐)。带符号绝对置位语义与禁聚合依据见
        # :func:`apply_strategy_pick_streak`;live 同拍零写(置位到结算
        # 之间 gs.streak 持旧值,真值经下一结算屏带符号读数观察覆盖
        # 收口,fields.md streak 写入方两分不动)。拿卡名推导与呈现闩
        # 防重放 = xp 腿同款:闩消费先于判定(交集空亦消费——每呈现窗
        # 至多一次落地消费,无效载荷的重放同样不得再触发)。
        if not opening and self._strategy_pick_streak_latch:
            self._strategy_pick_streak_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if picked:
                apply_strategy_pick_streak(self.gs, picked)
        # 「选择后」敌方难度读数即时反映(裁定 2026-10-14);开局环境选卡时
        # 节点未进窗(node None),写点内早退。
        self._update_difficulty_flag()
        # 选卡落地拍即时经验腿(通用通道):sim 世界自持账补全——live 同拍
        # 零写(经验面板画面可读 = 观察覆盖),sim 无观察,不发即持卡局
        # 等级进度失真。拿卡名 = 呈现候选 ∩ 持有列表(offer 候选排除已持,
        # 落地交集 = 刚拿入的卡;无效载荷获得链零容器写 → 交集空 → 零写)。
        # 呈现闩防重放:闩消费先于发放判定,无闩的重复 advance 零写。
        if not opening and self._strategy_pick_xp_latch:
            self._strategy_pick_xp_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if picked:
                apply_strategy_pick_xp(self.gs, picked)
        # 选卡落地拍出售发牌腿(板面重写族出售支):sim 世界自持账补全——
        # live 同拍零写(游戏侧发 5 只 2★,下一备战帧观察覆盖收口,三正本
        # 裁定零改动),sim 无观察,不发即持卡局资产面失真。先卖后抽时序
        # = 挂点天然保证:kernel 获得链(含桥出售面)已在选卡首链写完,
        # 本腿落桶出口时 held 已归零(出口时序契约前提)。拿卡名推导与
        # 呈现闩防重放 = xp 腿同款(闩消费先于判定,交集空亦消费);
        # 发牌资格归判据集分派非单卡特判;rng 显式流键构造(缺省回退自掷
        # 破 sim 确定性;段位沿 M21/M22/M23 编号续,与商店发牌 M05/环境
        # 族 M02 分域)。位置 = 链尾独立笔:本腿非环境无门控读面、非注册
        # 表字段分派,与前置各腿零交互。
        if not opening and self._strategy_pick_sell_deal_latch:
            self._strategy_pick_sell_deal_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if picked:
                apply_strategy_pick_sell_all_deal(
                    self.gs, picked, stream_rng(self.seed,
                                                'M24/sell-all-deal'))
        # 选卡落地拍即时生命腿(hp 通道模式卡「健康充值」首落;通用通道,
        # 辖域 = 注册表 hp_instant>0 全体):sim 世界自持账补全——live 同拍
        # 零写(游戏自算,血量条观察覆盖收口,fields.md hp 写入闸无逻辑
        # 写入方)。拿卡名推导与呈现闩防重放 = 前置三腿同款(闩消费先于
        # 判定,交集空亦消费);不 clip/禁聚合依据见
        # :func:`apply_strategy_pick_hp`。位置 = 链尾独立笔:与前置各腿
        # 零交互(字段分派互斥:xp_instant / streak_set / 发牌判据集 /
        # hp_instant)。轨迹追加 = observe 同笔语义(hp 写流 ↔ hp_trail
        # 全序同构不变式按写行粒度对齐——腿返回笔数即写行数,逐笔追加)。
        if not opening and self._strategy_pick_hp_latch:
            self._strategy_pick_hp_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            for _ in range(apply_strategy_pick_hp(self.gs, picked)):
                self._hp_trail_append()
        self._after_modal_pick(opening=opening)

    def _on_open_box(self) -> None:
        """开箱动作落地 → 武装箱选择画面(候选 = 占位固定集;候选写入
        走 report_screen_box_pick_obs 同名通道)。"""
        if self._screen == SCREEN_BOX:
            return   # 重入幂等:候选已在场
        self._box_pick_pending = None
        self.disclosures.setdefault(BOX_POOL_PENDING_U24, 'bases4')
        cands = list(box_options())
        self._present_modal(SCREEN_BOX)
        report_screen_box_pick_obs(self.gs, CwScreenBoxPickObs(
            on_screen=True, card_names=cands,
            points=[((i + 1) * 10, 10) for i in range(len(cands))]))

    def _on_box_picked(self) -> None:
        """武装箱选定落地:选中装备走获得链入栏(kernel 单一时序,含
        获得后果回调);候选点击缺记录 = 世界不可辨,披露不猜。"""
        idx = self._box_pick_pending
        self._box_pick_pending = None
        if idx is not None:
            names = self.gs.box_card_names.value or []
            if 0 <= idx < len(names):
                gain_equipment(self.gs, names[idx], rand=False,
                               sig=logic_sig(group_id='act:sim@box'),
                               evidence='sim:box_pick',
                               producer='SimBackend')
            else:
                self.disclosures.setdefault(BOX_POOL_PENDING_U24,
                                            'pick_idx_out_of_range')
        else:
            self.disclosures.setdefault(BOX_POOL_PENDING_U24,
                                        'pick_card_unrecorded')
        self._dismiss_modal()

    def _on_overlay_picked(self, kind: str) -> None:
        """overlay 选定落地(模态返回 + 呈现检查):效果分支归各自上报/
        效果批,本层零效果。原私有队列出队分支
        停用——呈现数据源 = ``gs.screen_changes.pending``,消费 = 选卡
        上报内 ``consume_screen_change``(两世界同一行代码,register-
        consume.md「sim 消费」),本层不重复出队。
        """
        if kind == 'planner':
            self.disclosures[DISCLOSURE_PLANNER_EFFECT] = 'picked:report_branch'
        self._dismiss_modal()
        self._present_pending_overlay()

    # ---------------------------------------------------------- 状态机

    def _announce_screen(self, value: str) -> None:
        """画面广播(内部状态机 → 容器画面域,渲染复盘的画面章证据面)。

        - 值级豁免:``SCREEN_SETTLE``/``SCREEN_LOBBY`` 不广播——结算事实
          已由战斗章 settlement 写入行 + 局头终局行承载,大厅收口事实在
          局头;广播只各造一个未注册空壳章。豁免按值不按赋值点(模态
          返回位可为结算屏,点位豁免会泄漏「货币战争-结算」空壳章);
        - 两行一对:``prev_screen`` = 上次广播值(初值 = 容器冷建空串)→
          ``current_screen`` = value;渠道 = obs 族合成签名(mode=
          'synthesized' 为 obs_sig 内建的渠道级如实标记——引擎声明非
          真读数),evidence 前缀 ``screen:`` 为辅助标记;
        - 手搓两行对、不复用 kernel ``observe_screen_context``:该口对
          备战/开商店值触发顶栏观察/商店类型派生等实机分支(cw_game_
          state.py),sim 常量值与其同值会误触——刻意取舍非漏接单一源;
        - 同值广播不抑制:kernel 写端落 same_value=true 行,渲染路由
          续开 base 不重开章,零副作用;
        - 调用点 = ``self._screen`` 赋值行前一行(除 SETTLE/LOBBY 两处
          豁免点的全部 10 处赋值点),广播先行使后续观察行快照即带新值。
        """
        if value in (SCREEN_SETTLE, SCREEN_LOBBY):
            return
        self.gs.observe(self.gs.prev_screen, self._announced_screen,
                        evidence=sim_evidence(f'screen:{value}'),
                        sig=obs_sig(group_id='sim:screen'))
        self.gs.observe(self.gs.current_screen, value,
                        evidence=sim_evidence(f'screen:{value}'),
                        sig=obs_sig(group_id='sim:screen'))
        self._announced_screen = value

    def _present_modal(self, screen_name: str) -> None:
        """模态呈现(压住底层画面;返回目标 = 当前屏,选完返回)。"""
        if self._screen == screen_name:
            return
        self._return_screen = self._screen
        self._return_sub = self._sub
        self._announce_screen(screen_name)
        self._screen = screen_name

    def _dismiss_modal(self) -> None:
        """模态返回(幂等:无挂起返回 = 原地不动;节点窗让路恢复位优先)。"""
        resume = self._window_resume
        if resume:
            self._window_resume = ''
            self._return_screen = None
            self._return_sub = ''
            if resume == 'node':
                self._present_node_screen()
            else:
                self._present_offer_or_node_screen()
            return
        ret = self._return_screen
        if ret is None:
            return
        ret_sub = self._return_sub
        self._return_screen = None
        self._return_sub = ''
        self._announce_screen(ret)  # 返回位可为结算屏,值级豁免在 helper 内
        self._screen = ret
        self._sub = ret_sub

    def _after_modal_pick(self, *, opening: bool) -> None:
        """选卡族模态返回(投资双支共用):开局环境态(节点未进窗)→
        wait_one_one;其余 = 模态返回(节点窗让路恢复位优先)。"""
        if opening and self.gs.node.value is None:
            self._return_screen = None
            self._enter_wait_one_one()
            return
        self._dismiss_modal()

    def _present_pending_overlay(self, fortune_base: str | None = None) -> None:
        """overlay 呈现检查(数据源 = 容器登记
        ``gs.screen_changes.pending``,旧私有队列呈现面已停用——
        队列本体随评估器归 3.5 清扫;呈现时机不变 = advance/步界检查)。

        ``fortune_base`` = fortune 呈现门的底层判据屏(缺省 = 当前
        ``_screen``;节点窗起点传**目标底层**——当前屏仍是旧结算屏,判当前
        会吞掉后续呈现)。

        逐 kind 呈现门(overlay 生命周期契约(sim 消费)):

        - megastar:模态 + 候选写容器(场上盛会之星资格成员,含持徽
          贡献——候选语义 = 判据资格集同源);
        - planner:模态(选项桶实机 OCR 写点,sim 生成器批接线);
        - box_card/expert_invite:open_box/open_bookcard 的 advance 分派
          已呈现对应模态(候选写入在各自过程),本检查幂等守卫;
        - fortune:**逐 kind 呈现门**——仅底层 = 备战时收尾消费
          (用户确认:下一节点非备战时推迟,选完进备战
          先弹,不压补给/遭遇屏);底层非备战 = 条目存活等待;
        - aha/partner/fortune(备战底层时)/wish_trial/star_tome:无
          sim 呈现面族(aha 无独立画面档,实机 = 备战锚特殊规则点
          首件;其余画面 op 无 sim 观察分支,呈现即卡 observe 重试;
          partner 候选可自资格集算,候观察分支接线再呈现)→ 消费 +
          **逐 kind 披露**(披露键含 kind,多 kind 同帧各自留痕)。

        模态叠模态守卫(原语义):当前已在模态屏 = 推迟(返回后再查)。
        """
        pending = list(self.gs.screen_changes.pending)
        _fortune_base = self._screen if fortune_base is None else fortune_base
        for entry in pending:
            kind = entry.kind
            if self._screen in _MODAL_SCREENS:
                return   # 模态中:全部推迟(选完返回后再查)
            if kind == 'fortune' and _fortune_base != SCREEN_PREP:
                continue   # 呈现门:底层非备战,条目存活等待()
            if kind in ('aha', 'partner', 'fortune', 'wish_trial',
                        'star_tome'):
                # 无 sim 呈现面族:aha 无独立画面档(实机 = 备战锚特殊
                # 规则点首件);partner/fortune/wish_trial/star_tome 选项
                # 注册表缺位且画面 op 无 sim 观察分支(呈现即卡 observe
                # 重试;partner 候选可自资格集算,候 sim 观察分支接线再呈现)
                # → 消费 + 披露(fortune 呈现门语义保留:底层非备战时
                # 上方 continue 使条目存活)。
                consume_screen_change(self.gs, kind)
                # 逐 kind 披露(键含 kind,多 kind 同帧不互吞)。
                self.disclosures[f'{OVERLAY_PARAM_PENDING}:{kind}'] = (
                    'aha_auto_consumed' if kind == 'aha'
                    else f'{kind}_options_unmodeled')
                continue
            if kind == 'megastar':
                self._present_modal(SCREEN_MEGASTAR)
                self._present_megastar_options()
                return
            if kind == 'planner':
                self._present_modal(SCREEN_PLANNER)
                return
            if kind in ('box_card', 'expert_invite'):
                # open_* advance 分派已呈现(open_box 写候选/'' 纯转移
                # 呈现 expert);此处幂等守卫——若模态未在(异常序)= 补呈现。
                self._present_modal(
                    SCREEN_BOX if kind == 'box_card' else SCREEN_EXPERT)
                return
            # 集外 kind 不可构造(kind 封闭集在 register 口炸),防御披露。
            consume_screen_change(self.gs, kind)
            self.disclosures[f'{OVERLAY_PARAM_PENDING}:{kind}'] = \
                'unpresentable_kind'

    def _present_megastar_options(self) -> None:
        """巨星候选写容器(候选 = 场上盛会之星角色,含持星徽贡献;选项
        坐标 = sim 合成坐标,身份键无画面语义)。"""
        cands: list[MegastarOption] = []
        _view = self.gs.deployed.value
        for row_name, sub in (('front_row', _view.front_slots if _view is not None else ()),
                              ('back_row', _view.back_slots if _view is not None else ())):
            for unit in (sub or []):
                if unit is None:
                    continue
                if '盛会之星' in _row_unit_tags(unit, row_name):
                    cands.append(MegastarOption(
                        idx=len(cands), char_id=unit.char_id,
                        xy=((len(cands) + 1) * 10, 10)))
        report_screen_megastar_obs(self.gs, CwScreenMegastarObs(
            in_node=True, options=cands))

    def _node_pos(self) -> tuple[int, int]:
        """当前节点 (位面,轮)(gs.node 现值;未进窗 = (1, 1) 防御面)。"""
        node = self.gs.node.value
        if node is None:
            return 1, 1
        return node.plane, node.round_num

    def _enter_node_window(self, pos: NodePos) -> None:
        """进节点(输入即键;序列平移:写 gs.node + 节点序位观察锚定;
        位面首 = 位面过渡屏,其余序列在 _begin_node_window 收尾)。"""
        seq = node_sequence_of(pos[0], self.gs.node_seq_by_plane.value)
        kind = seq[pos[1] - 1]
        self.gs.observe(self.gs.node,
                        NodeKey(plane=pos[0], round_num=pos[1], kind=kind),
                        evidence=sim_evidence(f'node:p{pos[0]}r{pos[1]}'),
                        sig=obs_sig(group_id='sim:node'))
        # 节点序位锚定(sim 写端 = 世界呈现节点,与实机「备战帧顶栏/补给屏
        # 节点条」观察锚定同口;终结动作推进的观察态门以此为前提)。
        observe_node_anchor(self.gs, pos,
                            trigger_screen=self._screen_for_node(kind),
                            actor='SimBackend')
        self._window_resume = ''
        if pos[0] > 1 and pos[1] == 1:
            # 位面过渡(U20:全继承无重置;点空白后收尾节点窗口)
            self._announce_screen(SCREEN_PLANE_TRANSITION)
            self._screen = SCREEN_PLANE_TRANSITION
            self._sub = ''
            return
        self._begin_node_window()

    @staticmethod
    def _screen_for_node(kind: str) -> str:
        """节点类型 → 关联屏档名(进窗锚定 ``observe_node_anchor`` 的
        trigger_screen 消费——「节点条在哪个屏上被观察」的关联语义,
        非呈现稳态屏;2026-10-29 呈现改造后窗起点底层恒备战,各节点屏
        为其上模态,本映射仅承载锚定关联不再参与呈现)。"""
        return {'supply': SCREEN_SUPPLY, 'encounter': SCREEN_ENCOUNTER,
                'boss': SCREEN_BOSS_BRIEFING}.get(kind, SCREEN_PREP)

    def _begin_node_window(self) -> None:
        """节点窗口序列(收入 → 环境金 → 商店全刷 → overlay → offer →
        节点屏呈现;位面过渡点空白与直进节点共用本收尾)。

        幂等守卫(3.4 联调裁决①):窗口前段(轮首收入/环境金/发牌)对
        同一节点只执行一次——位面过渡点击重放(同点位二次 click_answer)
        会二次进入本收尾,无双发守卫则窗口前段收入/发牌双写(发牌覆盖
        同值无感、收入是真双账)。守卫键 = 节点序位 (位面,轮)。"""
        plane, r = self._node_pos()
        pos_key: NodePos = (plane, r)
        if self._window_begun_pos == pos_key:
            return
        self._window_begun_pos = pos_key
        kind = node_sequence_of(plane, self.gs.node_seq_by_plane.value)[r - 1]
        # 备战画面敌方难度读数观察(裁定 2026-10-14):窗开即敌方难度读数可见时点,
        # 上窗以来状态变动(连胜/选卡)在此反映;本窗内选卡的即时反映
        # 由 _on_invest_picked 写点承担。
        self._update_difficulty_flag()
        # 轮首收入(M04;败局补偿登记待办按 kernel 分支序消费——supply/reward
        # 轮不消费,败态跨轮保留至下一战斗轮;连胜 = 容器带符号派生读)
        pending = self.gs.pending_loss.value
        if is_piggy_node(self.gs):
            # 扑满节点收入递延:统一公式败局形需胜负,窗口开时未知 →
            # 只冻结基数(金/进轮连胜/修饰 = 轮初口径),结算分支落账
            # (_resolve_battle);支付时点 = 结算屏,与实机一致。
            self._piggy_income_snap = (
                int(self.gs.gold.value or 0),
                max(int(self.gs.streak.value or 0), 0),
                income_modifiers_of(self.gs))
        else:
            # 非扑满清递延快照(纯防御,幂等清理,现网不可达路径零行为
            # 变化):扑满局奖励节点必走上分支;残留快照若带入非扑满
            # 节点窗,结算分支会给战斗节点叠发一份 reward 收入——未来
            # 新增「未结算即推进」类流程时的开口,T-6 验收遗留项清账
            # (reviews/T-6-r1.md ⑤①)。
            self._piggy_income_snap = None
            apply_round_start_income(
                self.gs, plane=plane, round_num=r, node_type=kind,
                streak=max(int(self.gs.streak.value or 0), 0),
                pending_loss=pending)
        if kind not in INCOME_BRANCH_NODE_TYPES and pending is not None:
            clear_pending_loss(self.gs,
                               sig=obs_sig(group_id='sim:loss'))
        # 位面开局环境发放分道:声明矿环境走声明入队(金在点击兑现时
        # 入账),其余环境保留直发通道(通道留置)。
        self._apply_env_plane_start(plane)
        # 环境定时道具到点发放(迭代 2026-09-24-scheduled-env-gifts
        # design §2.4):本收尾在窗口幂等守卫内,且位面过渡点空白与直进
        # 节点共用——「第 N 位面开始时」类发放即落在该位面 1 号节点窗
        # 打开时点(位面过渡屏被点掉时),窗口重放不双发;环境发放为
        # 确定发放 → rand=False(gain-chain.md §5),组名沿 sim:env 与
        # 环境金同窗。
        discharge_due_item_grants(self.gs, plane=plane, round_num=r,
                                  rand=False, sig=logic_sig('sim:env'))
        # 环境倒计时件到点开盒(T-34 命运礼物;设计 = T-34 设计稿 §2.4,
        # 迭代 2026-09-23-invest-effects-calc):同一收口继承窗口幂等守卫
        #(窗口重放不双发);开盒 = 确定事件非采样 → rand=False,
        # sig 组名沿 sim:env 与定时道具发放同窗。
        discharge_due_item_opens(self.gs, rand=False,
                                 sig=logic_sig('sim:env'))
        # 策略延时发放到点入栏(策略卡「N个节点后获得发放物」族,人才
        # 激励首例;与 offer 呈现腿并列独立域——本腿产出 = 世界发放写):
        # 同一收口继承窗口幂等守卫(重放不双发);递减点 = kernel 节点
        # 边界 tick(advance 尾段),动作上报/锚定补推两路径均先于本窗
        # 开——本 advance 递减到 0 的条目本窗发放 = 「第 N 个后继节点
        # 窗」读法落点。确定发放 → rand=False(gain-chain.md §5);独立
        # sig 组名与环境 'sim:env' 区分(世界发放写非环境域,审计可分)。
        # 到点留证披露键按「先读后发」取到期卡名(发放原语效果串只载
        # 发放物不载卡名);注册表查行失败的防御条目由原语保留不弹除,
        # 披露值以 '?' 标记发放物缺失。
        due_grants = tuple((str(e[0]), int(e[1])) for e in
                           (self.gs.pending_strategy_grants.value or ())
                           if int(e[1]) <= 0)
        if due_grants:
            discharge_due_strategy_grants(self.gs, rand=False,
                                          sig=logic_sig('sim:strategy_grant'))
            for _name, _rem in due_grants:
                _spec = STRATEGY_DELAYED_GRANTS.get(_name)
                self.disclosures[STRATEGY_DELAYED_GRANT_FIRED] = (
                    f'{_name}@{plane}-{r}:'
                    f'{_spec.item if _spec is not None else "?"}')
        # 首领节点条件发放(劳务派遣合同分支2;条件单一源 = kernel
        # check_env_boss_grants):进窗事实点在窗口幂等守卫内(重放不双发),
        # done boss 键短路兜第二层。流键 M21 沿 M05/M18/M20 编号续,
        # 采样即世界真值;sig 与环境金/定时道具发放同组同窗。kind =
        # node_sequence_of(plane, seqs)[r-1](上窗已算),坐标 (plane, r) =
        # 窗口幂等守卫键现值,直传入参零转换。
        if kind == 'boss':
            check_env_boss_grants(self.gs, node_pos=(plane, r),
                                  rng=stream_rng(self.seed,
                                                 f'M21/env-boss/p{plane}/r{r}'),
                                  sig=logic_sig('sim:env'))
        # 策略 boss 金腿(特战资金系):进 boss 节点窗发持卡聚合值,独立
        # 观察笔(evidence/sig 与收入笔分键)——轮首收入三分量账
        #(IncomeApplied.total = 该笔金增量)对账关系保持纯净,禁并入
        # 收入写。缺口来源:实机进 boss 节点真发聚合值,sim 世界自持账
        # 无观察可兜,不发即持卡局金系统性偏低。与劳务派遣合同的角色
        # 发放腿同段收口(定时道具后、商店全刷前;两腿互不读对方字段,
        # 先后无行为差,同段为收口序单一)。承载方式 = 「调用方聚合
        # 单列」过渡形态(round_start_income docstring 预留的两承载方式
        # 之一),T1b 定夺后若选分量扩参,本腿随迁移合并进收入签名。
        # 零值零写(未持卡零新增观察行);幂等复用窗口守卫(同节点窗
        # 重放整段跳过),零新增守卫。
        if kind == 'boss':
            boss_gold = strategy_boss_gold_of(self.gs)
            if boss_gold > 0:
                gold_before = int(self.gs.gold.value or 0)
                tag = f'strategy:boss_gold:p{plane}r{r}'
                self.gs.observe(self.gs.gold, gold_before + boss_gold,
                                evidence=sim_evidence(tag),
                                sig=obs_sig(group_id=f'sim:{tag}'))
        # 策略尾款金腿(尾款交付):进入「最后一个补给阶段」节点窗发持卡
        # 聚合值——触发器 = **序列位置锚**((位面,轮) == 展平全序列最末
        # supply 位,整局一次;单一源 = final_supply_pos 场字段现值派生,
        # 修饰局零特判),与 boss 腿的节点类型触发器不同形态,不套其判定
        # 代码。独立观察笔(evidence/sig 与收入笔分键)——轮首收入三分量
        # 账(IncomeApplied.total = 该笔金增量)对账关系保持纯净,禁并入
        # 收入写;supply 支收入 = base+息照发,与本卡金平行分账。缺口来
        # 源与 live 零写金裁定同 boss 金腿(sim 世界自持账无观察可兜)。
        # 同段邻位收口(boss 金腿之后、商店全刷前;两腿互不读对方字段,
        # 先后无行为差,同段为收口序单一)。零值零写;幂等复用窗口守卫
        # (同节点窗重放整段跳过),零新增守卫。拿卡当节点不发放:聚合读
        # 在窗口前段,选卡确认(offer 呈现后)恒晚于本读,同窗拿卡天然零
        # 发放(现行建模域 offer 槽域与 supply 零重合,场景不可达,机制
        # 防御语义)。
        if (plane, r) == final_supply_pos(self.gs.node_seq_by_plane.value):
            supply_gold = strategy_final_supply_gold_of(self.gs)
            if supply_gold > 0:
                gold_before = int(self.gs.gold.value or 0)
                tag = f'strategy:final_supply_gold:p{plane}r{r}'
                self.gs.observe(self.gs.gold, gold_before + supply_gold,
                                evidence=sim_evidence(tag),
                                sig=obs_sig(group_id=f'sim:{tag}'))
        # 环境直发策略取卡挂点(T-46 策略大师数量分支;设计 = T-46 定稿
        # §2.2(e)):进窗事实点在窗口幂等守卫内(重放不双发,定时道具/
        # 开盒/boss 先例位);禁置 _node_window_target_base(纯判定契约)
        # 与 _present_offer_or_node_screen(幂等守卫区段外,resume 复走
        # 双发面)。direct 挂点查询 = kernel ENV_POOL_REWRITE 单一源
        #(表外环境 get None = 无直发的合法语义,登记残缺归评审把关,
        # 空条目闸已随 2026-10-28 校验治理移除);当前节点 ==
        # extra_strategy_grant_node → 直接经获得链
        # 发一张随机投资策略,不开 offer 无选卡屏(用户裁定 2026-10-26),
        # 发放后照常进该节点正常流程;到手名并入 excluded_invest(维持
        # 「本局已出过全部选项名」累计去重契约,漏并入 = 已拥有策略可再入
        # 未来 offer 池,同名跳写 + 同卡二次发放面被直发分支重开)。直发到手
        # 即触发金币分支(同链自动,含本张口径下首张直发即 2 金)。调用形态沿
        # 现役直调先例 _on_invest_picked:session=None(登记分支跳过、容器写
        # 照常)/rand=False(确定发放)/sig 与环境金/定时道具发放同组
        # sim:env;流键 M23 沿 M21/M22 编号续,采样即世界真值;样本 '' =
        # 全池被排除集吃光(防御性,正常局不可达)→ 静默跳发不空手入链。
        _rewrite = ENV_POOL_REWRITE.get(str(self.gs.active_env.value or ''))
        _grant_node = (_rewrite.extra_strategy_grant_node
                       if _rewrite is not None else None)
        if _grant_node == (plane, r):
            _pick_rng = stream_rng(self.seed,
                                   f'M23/env-pick/p{plane}/r{r}')
            _name = sample_strategy_card(_pick_rng, self.excluded_invest)
            if _name:
                self.excluded_invest.add(_name)
                gain_invest_strategy(self.gs, None, _name, rand=False,
                                     sig=logic_sig('sim:env'),
                                     rng=_pick_rng)
        # 商店全刷(M05:节点切换自动全刷;整店锁跳过——裁定②)
        if not bool(self.gs.shop_locked.value):
            rotation_on = (str(self.gs.active_env.value or '')
                           == ROTATION_ENV_NAME)
            rng = stream_rng(self.seed, f'M05/deal/p{plane}/r{r}')
            probs = effective_deal_probs(
                int(self.gs.level.value or 3),
                stream_rng(self.seed, f'M05/rotation/p{plane}/r{r}'),
                rotation_on=rotation_on)
            deal_shop(self.gs, rng, level=int(self.gs.level.value or 3),
                      probs=probs, tag=f'shop:deal:p{plane}r{r}')
        # overlay 呈现检查(旧引擎收尾序:overlay 先于 offer;呈现压住
        # 节点屏,选定经 _dismiss_modal 恢复位复走 offer 检查——让路
        # 不吞 offer 槽)。修正:fortune
        # 呈现门判**目标底层**(节点窗起点即将呈现的屏)而非当前
        # _screen——窗起点时 _screen 仍是旧结算屏(判当前则门恒
        # continue 吞掉后续呈现,resume 悬挂);battle/reward 目标 =
        # 备战(fortune 收尾),supply/遭遇 = 节点屏(条目存活)。
        # resume='offer' 仅在实际压上模态时置(纯门存活零呈现 = 不置,
        # 防无模态消费掉 resume 位);offer 槽屏(模态)在场 = overlay
        # 推迟到选卡后(present 幂等序:overlay 优先,offer 恢复查)。
        if self.gs.screen_changes.pending:
            _base = self._screen
            self._present_pending_overlay(
                fortune_base=self._node_window_target_base())
            if self._screen != _base:
                self._window_resume = 'offer'
                return
        self._present_offer_or_node_screen()

    def _node_window_target_base(self) -> str:
        """节点窗起点即将呈现的底层屏(不执行呈现,仅判定 fortune 门)。

        2026-10-29 呈现改造后所有节点类型的窗起点底层恒备战档(节点
        弹窗都是备战上的模态),offer 槽命中例外(投资策略屏,非备战侧,
        fortune 条目存活等待);策略延时 offer 到期同例外(同一呈现通道
        的模态,门判定与固定日程同待遇——overlay 先行时 fortune 条目
        不被本窗消费)。"""
        plane, r = self._node_pos()
        active_env = self.gs.active_env.value
        if offer_slots(plane, r, active_env):
            return SCREEN_INVEST_STRATEGY
        if self._has_due_extra_offer():
            return SCREEN_INVEST_STRATEGY
        return SCREEN_PREP

    def _has_due_extra_offer(self) -> bool:
        """策略延时 offer 到期条目在队列(呈现门判定位,零副作用):
        到点判定 = remaining <= 0(到了及以后都算)。"""
        queue = self.gs.pending_strategy_offers.value or ()
        return any(int(entry[1]) <= 0 for entry in queue)

    def _present_offer_or_node_screen(self) -> None:
        """offer 呈现检查序 = overlay 让路恢复后:策略延时 offer 到期 →
        offer 日程 → 节点屏呈现(节点窗口让路恢复序)。

        权威序 = 旧引擎实测:overlay 选定后复走节点窗 offer 检查
        (收尾检查序 overlay → offer → 节点呈现),U07 固定日程生效于
        本节点备战窗口前——overlay 让路不吞 offer 槽;窗口前段(收入/
        环境金/商店全刷)已在本窗起点执行,恢复不重入。期货到期检查挂
        日程检查**之前**:优先序 = 固定日程/联席槽 > 期货队列由
        :meth:`_present_due_extra_offer` 内槽在场让路承载(同窗冲突
        期货顺延并落披露键),槽空闲窗期货先于节点屏呈现。呈现本体 =
        :meth:`_present_node_screen`(2026-10-29 改造后落点 = 备战底层
        ±节点弹窗模态 ±自动弹店)。"""
        plane, r = self._node_pos()
        active_env = self.gs.active_env.value
        if self._present_due_extra_offer():
            return
        if offer_slots(plane, r, active_env):
            self._invest_pick_ordinal += 1
            fixed_schedule = (plane, r) in INVEST_OFFER_SCHEDULE
            forced = rewrite_slot_qualities_for_pick(str(active_env or ''),
                                                     self._invest_pick_ordinal)
            rng = stream_rng(self.seed, f'M11/offer/p{plane}/r{r}')
            opts = sample_strategy_offer(rng, self.excluded_invest,
                                         forced_slots=forced or ())
            self._window_resume = 'node'
            self._announce_screen(SCREEN_INVEST_STRATEGY)
            self._screen = SCREEN_INVEST_STRATEGY
            self._sub = ''
            # 策略 offer 呈现即置即时经验腿闩(落地拍消费,防重放)。
            self._strategy_pick_xp_latch = True
            # 连胜置位腿闩同点置位(独立闩;复呈现再置位 = xp 腿既有
            # 形状,重放防护窗以「呈现→落地」为界,复呈现后到达的重放
            # 属上游重试 bug 面)。
            self._strategy_pick_streak_latch = True
            # 出售发牌腿闩同点置位(三腿独立闩同形;防重放窗同界)。
            self._strategy_pick_sell_deal_latch = True
            # 即时生命腿闩同点置位(四腿独立闩同形;防重放窗同界)。
            self._strategy_pick_hp_latch = True
            # 刷新授权簿记(2026-10-19 用户裁定「sim 与实机一致提供刷新
            # 次数」批):固定日程槽呈现逐卡计数(基准 1 + 环境
            # extra_pick_refreshes 增量);联席额外槽 desc 未写明刷新语义,
            # 保守不呈现(空 refresh_slots = op 闸无授权)。重掷沿用本窗口
            # 改写向量(槽位品质承诺跨刷新保持,卡面语义直读)。
            self._offer_refreshable = fixed_schedule
            self._offer_forced_slots = tuple(forced or ())
            self._offer_refresh_seq = 0
            per_card = (STRATEGY_REFRESH_BASE_PER_CARD
                        + _offer_extra_refreshes(str(active_env or ''))
                        if fixed_schedule else 0)
            refresh_slots = ([(per_card, (i + 1) * 10, 20)
                              for i in range(len(opts))]
                             if fixed_schedule else [])
            report_screen_invest_strategy_obs(self.gs,
                                              CwScreenInvestStrategyObs(
                                                  entry_ok=True,
                                                  options=[
                                                      (n, (i + 1) * 10, 10)
                                                      for i, n in
                                                      enumerate(opts)],
                                                  refresh_slots=refresh_slots))
            return
        self._present_node_screen()

    def _present_due_extra_offer(self) -> bool:
        """策略延时 offer 到期呈现(呈现腿,sim 专用;策略卡「N个节点后
        一次定品质不可刷新三选一」通道唯一消费端,kernel 不 import 本
        模块 = live 不对称的模块边界):读 ``pending_strategy_offers``
        取首个 remaining <= 0 条目(登记序 = 确定性)。

        优先序 = 固定日程/联席槽 > 期货队列:槽在场 = 本窗让路,到点
        条目悬置顺延(deferred 披露;顺延不悬空——到点判定「到了及以后
        都算」,下一空闲窗必呈现);本窗已呈现一次的余者同式顺延
        (window_cap 披露)。呈现即消费(队列弹除与呈现同拍原子,呈现后
        选卡经既有落地通道,防重入双呈现;呈现后选卡失败 = 动作域异常,
        队列不回滚,世界偏穷一份 offer,有界一次一张)。呈现侧副作用 =
        现役固定日程分支全量同款延伸:序位计数照增(「一切策略三选一
        呈现都计数」口径,联席额外槽先例)、xp/streak 腿闩照置、刷新
        簿记清零(定品质禁刷新 = 卡面「不能刷新」直读,refresh_slots
        空表 = op 闸无授权,live 读缺同安全)。定品质 = 槽向量直取
        登记品质池(观察面 = 候选全目标品质;环境品质改写不作用于本
        通道——改写判据只挂固定日程分支,品质恒 = 登记值)。rng 流键
        独立分域,重放稳定。返回是否呈现。"""
        plane, r = self._node_pos()
        active_env = str(self.gs.active_env.value or '')
        if not self._has_due_extra_offer():
            return False
        if offer_slots(plane, r, active_env):
            self.disclosures.setdefault(
                STRATEGY_DELAYED_OFFER_DEFERRED,
                f'scheduled_slot_occupied@'
                f'{sum(1 for e in self.gs.pending_strategy_offers.value or () if int(e[1]) <= 0)}')
            return False
        queue = tuple(self.gs.pending_strategy_offers.value or ())
        due = [(i, entry) for i, entry in enumerate(queue)
               if int(entry[1]) <= 0]
        _idx, (name, _remaining) = due[0]
        spec = STRATEGY_DELAYED_OFFERS[name]
        self._invest_pick_ordinal += 1
        opts = sample_strategy_offer(
            stream_rng(self.seed, f'M11/offer-extra/p{plane}/r{r}'),
            self.excluded_invest,
            forced_slots=(spec.offer_quality,) * OFFER_CANDIDATES)
        keep = queue[:_idx] + queue[_idx + 1:]
        self.gs.write_logic(self.gs.pending_strategy_offers, keep,
                            produced_by='SimBackend',
                            evidence=f'present_due_extra_offer:{name}',
                            sig=logic_sig(group_id='sim:offer-extra'))
        if due[1:]:
            self.disclosures.setdefault(
                STRATEGY_DELAYED_OFFER_DEFERRED,
                f'window_cap@{len(due) - 1}')
        self._window_resume = 'node'
        self._announce_screen(SCREEN_INVEST_STRATEGY)
        self._screen = SCREEN_INVEST_STRATEGY
        self._sub = ''
        # 呈现即置即时经验腿闩 + 连胜置位腿闩(固定日程分支同款「呈现即
        # 置闩」口径,落地拍消费防重放);出售发牌腿闩三腿同形照置。
        self._strategy_pick_xp_latch = True
        self._strategy_pick_streak_latch = True
        self._strategy_pick_sell_deal_latch = True
        # 刷新授权簿记照写(定品质禁刷新:不可刷新 = 卡面直读,空授权;
        # 槽向量簿记同步清零 = 无刷新窗语义)。
        self._offer_refreshable = False
        self._offer_forced_slots = ()
        self._offer_refresh_seq = 0
        report_screen_invest_strategy_obs(self.gs,
                                          CwScreenInvestStrategyObs(
                                              entry_ok=True,
                                              options=[
                                                  (n, (i + 1) * 10, 10)
                                                  for i, n in
                                                  enumerate(opts)],
                                              refresh_slots=[]))
        self.disclosures[STRATEGY_DELAYED_OFFER_FIRED] = f'{name}@{plane}-{r}'
        return True

    def _refresh_invest_strategy(self, slots: tuple[int, ...]) -> None:
        """投资策略屏逐卡刷新世界分支(2026-10-19 用户裁定「sim 与实机一致
        提供刷新次数」批;上报声明触发,同屏重呈现零转移)。

        逐槽:容器剩余口径闸(≤0 = 尽,防御性——op 侧 obs/容器双闸在前,
        本分支是声明直喂的最后防线)→ 按本窗口改写向量取槽品质重掷单卡
        (:func:`sample_strategy_card`;槽位品质承诺跨刷新保持)→ 刷新
        流水号推进(rng 流键,同窗口多次刷新互不同流)→ 整屏重呈现
        (report 观察写端:候选槽覆盖 + 逐卡计数合并写;刷新后该槽剩余
        预算随新卡呈现,与实机「计数印在卡上」同形)。刷新前候选随落选
        出屏,排除集累计语义不变 = 选卡落地时累计。空候选/不可刷新窗/
        全槽无授权/重掷无产出 = 静默无操作(防御性,正常局不可达)。"""
        names = list(self.gs.invest_strategy_opts.value or [])
        if not names or not self._offer_refreshable:
            return
        plane, r = self._node_pos()
        left_map = dict(self.gs.strategy_refresh_left.value or {})
        new_names = list(names)
        new_counts: dict[int, int] = {}
        for i in slots:
            if not 0 <= i < len(names):
                continue
            old = names[i]
            left = int(left_map.get(old, 0) or 0)
            if left <= 0:
                continue
            quality = (self._offer_forced_slots[i]
                       if i < len(self._offer_forced_slots) else '')
            # banned 滚动并入 new_names(T-427 验收 F-2):多槽声明同窗
            # 重掷时后槽排除前槽新名,守 offer「全程不重复」契约;单槽
            # 生产链行为不变(new_names[i] 此时仍为旧名 = 原排除语义)。
            banned = set(self.excluded_invest) | set(new_names)
            rolled = sample_strategy_card(
                stream_rng(self.seed,
                           f'M11/offer/p{plane}/r{r}'
                           f'/refresh{self._offer_refresh_seq + 1}'),
                banned, forced_quality=quality)
            if not rolled:
                continue
            self._offer_refresh_seq += 1
            new_names[i] = rolled
            new_counts[i] = left - 1
        if not new_counts:
            return
        counts = [new_counts.get(i, int(left_map.get(n, 0) or 0))
                  for i, n in enumerate(new_names)]
        report_screen_invest_strategy_obs(self.gs, CwScreenInvestStrategyObs(
            entry_ok=True,
            options=[(n, (i + 1) * 10, 10) for i, n in enumerate(new_names)],
            refresh_slots=[(c, (i + 1) * 10, 20)
                           for i, c in enumerate(counts)]))

    def _refresh_invest_env(self) -> None:
        """投资环境屏整组刷新世界分支(环境刷新 = 单全局钮整组重掷一次;
        上报声明触发,同屏重呈现零转移)。

        容器剩余闸(≤0/None = 尽,防御性——op 侧 obs+容器双闸在前)→
        候选整组重掷(排除累计集 ∪ 当前候选,保证组内全换)→ 整屏重呈现
        (report 观察写端:候选覆盖 + ``env_refresh_left`` 写 0)。空候选
        = 静默无操作(防御性,正常局不可达)。"""
        left = self.gs.env_refresh_left.value
        names = list(self.gs.invest_env_opts.value or [])
        if left is None or int(left) <= 0 or not names:
            return
        banned = set(self.excluded_env) | set(names)
        rng = stream_rng(self.seed, 'M02/env-offer/refresh1')
        opts = sample_env_offer(rng, banned)
        report_screen_invest_env_obs(self.gs, CwScreenInvestEnvObs(
            hit=True,
            options=[(n, (i + 1) * 10) for i, n in enumerate(opts)],
            refresh=(0, 10, 20)))

    def _present_node_screen(self) -> None:
        """按节点类型呈现对应屏(2026-10-29 流程模型对齐,流程模型单一
        源 = ``docs/game/currency_war/research/screen_flow_timing.md``
        口述流程模型节):**所有节点类型底层恒备战档**——进节点先出备战
        (过渡帧),节点弹窗(补给/遭遇/BOSS 简报)是备战上的模态
        (:meth:`_present_modal`),弹窗关闭回备战并自动弹店
        (:meth:`_dismiss_and_settle_prep` 系);battle/reward 无节点弹窗,
        备战呈现即自动弹店(:meth:`_settle_on_prep`,1-1 例外内置);
        reward 晶矿子态(面板矿+声明矿)保留备战档载荷形态。
        旧「按节点类型直接呈现节点屏」语义( supply→补给屏等)随本改造
        废止——节点屏档名现为备战底层上的模态。"""
        self._window_resume = ''
        plane, r = self._node_pos()
        kind = node_sequence_of(plane, self.gs.node_seq_by_plane.value)[r - 1]
        # 备战底层呈现(所有节点类型统一;晶矿 spheres 写按类型分叉在
        # battle/reward 分支——挂接入口单写径不变)。子态清零 = 过渡帧
        # 无子态(上一节点晶矿子态不跨节点残留;本节点子态在各自分支重定)。
        self._sub = ''
        self._announce_screen(SCREEN_PREP)
        self._screen = SCREEN_PREP
        if kind == 'supply':
            rng = stream_rng(self.seed, f'M18/opts/p{plane}/r{r}')
            opts = supply_options(rng, normalize_invest_name(
                str(self.gs.active_env.value or '')))
            report_screen_supply_node_obs(self.gs, CwScreenSupplyNodeObs(
                in_node=True, options=list(opts), refresh_left=1))
            self._present_modal(SCREEN_SUPPLY)
            return
        if kind == 'encounter':
            report_screen_encounter_obs(self.gs, CwScreenEncounterObs(
                options=list(encounter_options_for(
                    list(self.gs.active_strategies.value or []))),
                refresh_left=None))
            self._present_modal(SCREEN_ENCOUNTER)
            return
        if kind == 'boss':
            self._present_modal(SCREEN_BOSS_BRIEFING)
            return
        # battle / reward → 备战档:奖励节点面板矿 + 位面开局声明矿
        # **同批合并**进一次 spheres 写(声明归属由生成函数 rng 掷,批内
        # 不预分);声明矿呈现无「首帧判定」状态——挂接入口出队即消费,
        # 后续呈现自然无声明矿。备战档呈现均检查 pending 当前 plane 条目
        # (含普通 battle 备战:有条目 → 声明矿点单独呈现,子态同为
        # PREP_SUB_ORE——面板在场语义与奖励节点一致)。
        # 面板矿 = 锚 8 矿 + 扑满环境占位增量(活跃环境查表扩尾,见
        # reward_ore_panel_points);len(panel) 入参使位面开局声明矿
        # 续接坐标随扩尾自动跟随。
        panel = (reward_ore_panel_points(
            str(self.gs.active_env.value or ''))
            if kind == 'reward' else ())
        points = panel + self._plane_start_declared_points(plane, len(panel))
        # spheres 写一律过挂接入口(单一写径,禁第二写径):非 ore 备战
        # 呈现空读照写 count=0 亦过入口——空批零生成、清理上节点残留
        # 矿身份(容差配对在 sim 为恒等,合成坐标恒稳)。
        report_spheres_observed(
            self.gs, OreSight(
                count=len(points),
                colors=tuple(dict.fromkeys(p[0] for p in points)),
                points=points),
            obs_sig=obs_sig(group_id='sim:ores'),
            hook_sig=logic_sig('sim:ores'),
            evidence=sim_evidence(f'ores:p{plane}r{r}'))
        self._sub = PREP_SUB_ORE if points else ''
        self._settle_on_prep()

    def _plane_start_declared_points(
            self, plane: int,
            panel_count: int) -> tuple[tuple[str, int, int, int], ...]:
        """位面开局声明矿点列(``ore_declared_pending`` 当前 plane 有条目
        → 恰 1 点;无 → 空元组)。

        - 坐标 = **面板序续接** ``(10*(N+1), 10)``(N = 同批面板点数;
          位面首节点为奖励节点时 8 面板矿 + 声明矿 = 第 9 点 (90,10),
          P2 首节点为战斗节点时 = 首点 (10,10))——**禁独立从 1 起号**:
          同批撞键会被点击载荷 ``by_xy`` 求交去重吞点,唯一性由续接
          构造保证;
        - 色档 '金' 为占位(呈现色未实采,披露键
          :data:`ORE_PLANE_START_PENDING` 实机首遇校);r = 10 与面板
          矿同;条目数 ≤ 1(入队电平的 (env, plane) 双守卫保证)。
        """
        pending = self.gs.ore_declared_pending.value or ()
        if not any(e[1] == plane for e in pending):
            return ()
        return (('金', 10 * (panel_count + 1), 10, 10),)

    def _apply_env_plane_start(self, plane: int) -> None:
        """位面开局环境发放分道(详设 ore-sim-plane-start §1;节点窗
        起点调用)。

        - env ∈ :data:`ENV_ORE_GRANTS` → **声明入队**:经 kernel 同一
          电平规则函数 :func:`check_ore_declared_level`(入队幂等守卫 =
          pending/done 双查,``_window_begun_pos`` 窗口幂等降为冗余
          保险;顺手清位面过渡过期条目,evidence
          ``ore_declared_expired#p{old}`` 留痕)——**金不再直发**,世界
          面的金在点击声明矿兑现时入账(策略面估值消费
          ``ENV_ECONOMY`` 数值不变,两侧一致性归测试与评审把关);sig =
          ``logic_sig('sim:env')``(与 ``discharge_due_item_grants``
          同组同窗,kernel 确定效果直写 write_logic 先例);
        - env ∉ 且 ``gold_per_plane_start`` 非空 → 保留直发(非矿形态
          位面开局金的预留通道,现无此形态环境)。
        """
        env_name = normalize_invest_name(str(self.gs.active_env.value or ''))
        if env_name in ENV_ORE_GRANTS:
            check_ore_declared_level(self.gs, hook_sig=logic_sig('sim:env'))
            return
        self._apply_env_plane_gold(plane)

    def _apply_env_plane_gold(self, plane: int) -> None:
        """环境结构化经济通道·直发分支(M02:已结构化子集直接生效——位面
        开局金通道;**非声明矿环境的预留通道**,声明矿环境已在上游
        :meth:`_apply_env_plane_start` 分道绕行)。"""
        env_name = normalize_invest_name(str(self.gs.active_env.value or ''))
        env = INVESTMENT_ENVS.get(env_name)
        eff = env.economy if env is not None else None
        if eff is None:
            return
        golds = eff.gold_per_plane_start
        if plane_entry_gold := (golds[plane - 1] if 0 < plane <= len(golds)
                                else 0):
            after = int(self.gs.gold.value or 0) + plane_entry_gold
            self.gs.observe(self.gs.gold, after,
                            evidence=sim_evidence(f'env:plane_gold:p{plane}'),
                            sig=obs_sig(group_id='sim:env'))

    # ---------------------------------------------------------- 结算分支

    def _record_difficulty(self, node: NodeKey, kind: str) -> None:
        """难度账快照落账(2026-10-14 用户裁定:sim 对选择后的难度做
        记录更新)。

        时点 = 每场战斗结算入口、连胜转移前——记录「这一仗按什么难度
        打」:品质分量/策略静态 Δ 取已选策略现值,特殊加成取胜负前连胜
        (带符号账取绝对值,派生口径 = 收入侧无符号计数),遭遇档取
        ``gs.chosen_encounter``(载荷 ``(难度档, 奖励文本)``,发出即写,
        兑现清除在结算确认之后,战斗时点在场;仅 encounter 节点读,
        防跨节点残留误计)。
        base 恒 None(U25 基础曲线未采)、圣杯恒未激活(占位面)。
        纯簿记:零随机流消费、零结算行为影响——难度不入胜负面,胜负
        建模另批(裁定明文)。幂等 = 调用点在 ``_settled_key`` 守卫后,
        每节点恰一条。
        """
        chosen = (self.gs.chosen_encounter.value
                  if kind == 'encounter' else None)
        self.difficulty_records.append(DifficultyRecord(
            plane=node.plane, round_num=node.round_num, node_kind=kind,
            breakdown=difficulty_of(
                list(self.gs.active_strategies.value or []),
                node_kind=kind,
                streak=abs(int(self.gs.streak.value or 0)),
                encounter_tier=(int(chosen[0])
                                if chosen is not None else None))))

    def _update_difficulty_flag(self) -> None:
        """备战画面敌方难度读数观察写点(2026-10-14 用户裁定:sim 对选择后的
        难度做记录更新——观察面 = 备战画面敌方难度读数;live 生产主源 =
        备战画面敌方难度读数两级管线,fields.md §3.2.14 语义 = 节点相关观察真值、
        非单调,难度修改器/简单模式/伟大征服/品质通胀都动它)。

        值 = 局级输入档(``RunConfig.enemy_difficulty``,简报开局基线)
        + 已定案修正项(品质通胀/策略静态 Δ/伟大征服连胜项,M19
        ``difficulty_of`` 派生);U25 基础节点曲线未采,节点间基线移动
        不在 sim 面(披露键 ``DIFFICULTY_BASE_PENDING_U25`` 已登记)。
        遭遇档恒不入(敌方难度读数住备战帧,遭遇档是遭遇节点内选项维度)。
        写点 = 节点窗开(状态变动后的下一次敌方难度读数可见)+ 投资选卡落地
        (「选择后」即时);obs 渠道直写(与 live 敌方难度读数 OCR 同一容器域,
        同值重写幂等)。局级输入缺省(None)不写——无基线禁出数。
        """
        base = self.cfg.enemy_difficulty
        node = self.gs.node.value
        if base is None or node is None:
            return
        breakdown = difficulty_of(
            list(self.gs.active_strategies.value or []),
            node_kind=node.kind,
            streak=abs(int(self.gs.streak.value or 0)),
            encounter_tier=None)
        self.gs.observe(
            self.gs.enemy_difficulty,
            int(base + breakdown.quality_bonus + breakdown.special_bonus
                + breakdown.strategy_delta),
            evidence=sim_evidence(
                f'difficulty:flag:p{node.plane}r{node.round_num}'),
            sig=obs_sig(group_id='sim:difficulty'))

    def _resolve_battle(self) -> None:
        """coarse 战斗结算(随机输出面;现役唯一来源 = 出战声明
        battle_resolve——2026-10-29 呈现改造后,遭遇选完回备战/BOSS 简
        报点空白回备战,两节点战斗改由出战动作触发,旧三源中两源废止;
        重入幂等守卫 = 已结算节点键)。"""
        node = self.gs.node.value
        if node is None:
            return
        key = (node.plane, node.round_num)
        if self._settled_key == key:
            return
        self._settled_key = key
        kind = node.kind
        self._record_difficulty(node, kind)
        rng = stream_rng(self.seed, f'M13/{node.plane}/{node.round_num}')
        outcome = settle_battle(rng, plane=node.plane,
                                round_num=node.round_num)
        if kind == 'reward' and not is_piggy_node(self.gs):
            # 普通奖励关恒胜白拿:奖励关不需要战力(用户账本 408 行裁定,
            # 单一源 = kernel cw_reward_node.py 裁定权威行;已退役口述登记簿
            # 「默认稳过」主条),不存在败局——不掉血不掷负。先采后改写:
            # M13 随机流消耗恒定,同 seed 其他节点随机序列不漂移。
            outcome = replace(outcome, won=True, hp_delta=0, progress=1.0,
                              face=SIM_REWARD_FREE_WIN_FACE)
        if is_piggy_node(self.gs) and outcome.hp_delta < 0:
            # 扑满不掉血豁免(M17:扑满关有战力要求、不掉血)
            outcome = replace(outcome, hp_delta=0)
        # 损血档位触发的损血实值锚(保险;hp_before = apply 前现值,
        # 「规定取法」= 设计内唯一——保底截断局写后值恒 1,不可由
        # (outcome.hp_delta, 写后现值) 反推面值前真值;真值差口径 =
        # 「损失」不超持有量)。None 防御 = hp 从未观察(直构域)时
        # 触发腿按零损血跳过,apply_hp_outcome 未观察零写同款防御。
        hp_before = int(self.gs.hp.value or 0)
        _floor, dead = apply_hp_outcome(self.gs, outcome)
        self._hp_trail_append()
        # —— 结算环帧补写(T-33 完胜判定数据面,设计 §2.4):与 live 同一
        # ring 读口——killed = won(killed 单一语义 = 「挑战成功」胜利标志,
        # cw_settlement_obs.py 注释正本),hp_after = apply 后 gs.hp 现值
        #(apply_hp_outcome 已写,与 live 结算屏读数同语义位)。node_type =
        # sim kind → 结算行词表映射(词表正本 = live 结算行归一
        # cw_screen_battle_wait._normalize_node_type;kernel→operations
        # 反向 import 禁止,sim 侧同形内联)。写端走环单一写端口
        # record_settlement_row(遭遇行随入经验表,encounter_tier=None
        # 不改 tier_cleared 判据;补给不经本分支 = 零行,环语义不变)。
        from sr_od.application.currency_war.kernel.cw_encounter_selection import (
            record_settlement_row,
        )
        from sr_od.application.currency_war.kernel.cw_performance import (
            RoundOutcome,
        )
        record_settlement_row(
            self.gs,
            RoundOutcome(round_num=node.round_num, plane=node.plane,
                         node_type=kind, comp_tag='',
                         killed=outcome.won,
                         hp_after=int(self.gs.hp.value or 0)),
            plane=node.plane, round_num=node.round_num,
            node_type=_SIM_KIND_TO_RING_LABEL.get(kind, kind),
            difficulty_node=None, encounter_tier=None)
        if dead:
            self._game_over()
            return
        # 连胜转移(M15:容器带符号;败局待办登记 M04,消费归下一战斗轮轮首)
        won = outcome.won
        piggy = is_piggy_node(self.gs)
        if self._piggy_income_snap is not None:
            # 扑满收入落账(统一公式「战败时无连胜成分」:败局 = 基础+息,
            # 胜局 = 基础+进轮连胜×倍率+息)。基数 = 窗口开快照(轮初口径,
            # 息按窗口开金),支付时点 = 结算屏与实机一致;增量落当前金,
            # 窗口内购物波动不受影响。
            gold_snap, streak_in, (mult, flat, cap) = \
                self._piggy_income_snap
            row = round_start_income(
                node.plane, node.round_num, 'reward', gold_snap, streak_in,
                win_reward_mult=mult, interest_flat=flat, interest_cap=cap,
                lost_round=not won)
            gold_now = int(self.gs.gold.value or 0)
            tag = f'income:p{node.plane}r{node.round_num}'
            self.gs.observe(self.gs.gold, gold_now + row.total,
                            evidence=sim_evidence(tag),
                            sig=obs_sig(group_id=f'sim:{tag}'))
            # 利息累计账入账 + 条件发放检查(T-27;递延 row 的息按窗口开
            # 快照基数,T-6 现役口径)。record 先于 check 同组相邻;check
            # 在金落账后(同窗金真值先行)。本分支与常规轮首(窗口守卫内)
            # 互斥:扑满节点窗口只冻快照不落账,结算分支一次性消费,无幂等
            # 面。sig = logic_sig('sim:env'),返回值忽略(无回调)。
            self.gs.effects.record_interest_earned(row.interest)
            check_env_interest_grants(self.gs, logic_sig('sim:env'))
            self._piggy_income_snap = None
        signed = streak_signed_after(int(self.gs.streak.value or 0),
                                     node_type=kind, won=won, piggy=piggy)
        self.gs.observe(self.gs.streak, signed,
                        evidence=sim_evidence(
                            f'streak:p{node.plane}r{node.round_num}'),
                        sig=obs_sig(group_id='sim:streak'))
        # —— 环境条件发放触发(迭代 2026-10-10-env-conditional-grants
        # landing 3.3;接线点 = streak observe 之后,连胜真值已落账,
        # 条件单一源 = kernel check_env_streak_grants)。sig 写死单形态
        # = logic_sig('sim:env'):触发函数两写均为 logic 渠道,obs 族进
        # write_logic_rand 即炸渠道族校验(禁 obs_sig,详设
        # env-conditional-grant.md §5)。返回非 None → 宝钻回调(入参
        # 只传装备名,sig 由回调内构 obs 族;宝钻裁决只认财富宝钻 =
        # 回调内早退,接线不预判)。带钻补给不采纳回调:钻类型未建模,
        # _on_supply_picked 零改动(详设 §5「补给宝钻不采纳回调」)。
        granted = check_env_streak_grants(self.gs, signed,
                                          logic_sig('sim:env'))
        if granted is not None:
            on_diamond_acquired(self.gs, granted)
        # —— 持续伤害契约条件分支(T-28 设计稿 §2.3;猜测写 + 进度累计 +
        # 证实同点,接线点 = streak 检查同点):active_env 门真后每次结算
        # 分支发火,「假设获得黑天鹅」猜测态写入(sim 世界写即真值,sim 无
        # 观察覆盖 → 认知猜测态写即存续)+ 进度键 dot_battle#<k> 追加,
        # 第 ENV_DOT_CONFIRM_BATTLES 笔同窗证实。计数代理口径(用户拍板
        # 值,非机制推导)单一源 = kernel 常量;非战斗轮(商店/事件)不经
        # 结算分支 = 不计数(结构性);_settled_key 重入幂等 = 单点每战斗
        # 恰发火一次。条件单一源 = kernel check_env_dot_grants,sig 同
        # streak 通道 logic_sig('sim:env'),返回值忽略(无回调面)。
        check_env_dot_grants(self.gs, logic_sig('sim:env'), count_battle=True)
        # —— 策略卡战后触发发放(策略卡战后触发发放首例;接线点 = 既有
        # 环境触发腿同段:dot 检查后、败局待办登记前,胜败两态共同路径
        # ——卡文无「胜利」限定 = 败局存活也发;死亡局在本函数提前
        # return 处已出局,不发放)。条件单一源 = kernel
        # check_strategy_battle_grants(登记表 STRATEGY_ENCOUNTER_BATTLE_
        # GRANTS,node_kind 传本函数结算点现值 kind,修饰局场字段改写天然
        # 跟随零特判);sig = logic_sig('sim:strategy') 新组首落(发放写
        # 为 logic 渠道,obs 族进 write_logic_rand 即炸渠道族校验);
        # 幂等零新增守卫 = 本函数 _settled_key(同节点重放整段跳过);
        # 返回值忽略(无回调面)。
        check_strategy_battle_grants(self.gs, kind,
                                     logic_sig('sim:strategy'))
        # —— 策略卡胜利结算条件金(招财狗 id 103501 首例;接线点 =
        # 策略卡战后触发发放之后、败局待办登记之前,胜败两态共同路径。
        # 触发域 = 全部结算节点,本接线不设节点类型守卫——卡面「战斗
        # 胜利」未限定节点类型,desc 无载面按字面全节点建模,假设经
        # STRATEGY_WIN_GOLD_SCOPE_ASSUMPTION 披露键随局申报,实机差额
        # 归披露键校准面)。条件单一源 = kernel
        # check_strategy_win_gold_grants(纯读零写:胜 ∧ 未损血 ∧ 佩佩
        # 数三条件函数内短路,扑满败局 won=False ∧ hp_delta=0 形态
        # 自然零发;死亡局已在本函数提前 return 处出局);写面 =
        # observe 金独立笔(世界数值面写端通道分工,扑满收入 observe
        # 金同款;obs 族,组名 'sim:strategy' 沿在役惯例 obs/logic
        # 共用——同名 logic 组 = 策略战后发放腿);幂等零新增守卫 =
        # 本函数 _settled_key(同节点重放整段跳过)。
        gold_gain = check_strategy_win_gold_grants(
            self.gs, won=won, hp_delta=outcome.hp_delta)
        if gold_gain > 0:
            gold_now = int(self.gs.gold.value or 0)
            self.gs.observe(
                self.gs.gold, gold_now + gold_gain,
                evidence=sim_evidence(
                    f'strategy_win_gold:p{node.plane}r{node.round_num}'),
                sig=obs_sig(group_id='sim:strategy'))
            self.disclosures.setdefault(
                STRATEGY_WIN_GOLD_SCOPE_ASSUMPTION,
                'all_settlement_nodes_v0')
        # —— 策略卡损血档位触发发放(保险 id 130501 首例,损血触发族
        # 首例;接线点 = 策略卡胜利金腿之后、败局待办登记之前,胜败两态
        # 共同路径——触发判据 = 实际损血非胜利,胜局零损血/扑满豁免形态
        # 在触发函数首序自然零通过;死亡局在本函数提前 return 处已出局,
        # 不发放)。损血实值 = hp_before 与写后现值差(保底截断后真值,
        # 「损失」不超持有量;hp 从未观察 → 前后均 0 → 零损血天然跳过,
        # apply_hp_outcome 未观察零写同款防御)。条件单一源 = kernel
        # check_strategy_hp_loss_grants(周期型:累积器全程累计 + 发放刻
        # 取模,无 done 闩;防重零新增守卫 = 本函数 _settled_key,同节点
        # 重放整段跳过);sig = logic_sig('sim:strategy') 沿策略战后发放
        # 腿同组(金写 obs 族签名由函数内构);rng = 独立子流键
        # M13/{p}/{r}/ins(装备采样专用,禁复用 M13 主流实例——其消耗序
        # = 文档化契约「胜负+扣血/进度依序」,续用即延展耦合;独立子流 =
        # 同 seed 其他流零扰动);发放非空 → 建模假设披露键随局申报
        #(三假设:桶结转/真值差/触发源域仅战斗结算,后继非战斗损血源
        # 落地批须扩挂点,过渡由本键承载)。
        hp_lost = hp_before - int(self.gs.hp.value or 0)
        gold_gain, _hp_loss_equips = check_strategy_hp_loss_grants(
            self.gs, hp_lost,
            logic_sig=logic_sig('sim:strategy'),
            rng=stream_rng(self.seed,
                           f'M13/{node.plane}/{node.round_num}/ins'))
        if gold_gain > 0:
            self.disclosures.setdefault(
                STRATEGY_HP_LOSS_BUCKET_ASSUMPTION,
                'bucket_carry_truth_diff_battle_only_v0')
        if not won and kind in COMBAT_NODE_TYPES:
            self.gs.observe(self.gs.pending_loss,
                            LostNodeRef(plane=node.plane,
                                        round_num=node.round_num,
                                        node_type=kind),
                            evidence=sim_evidence('loss:pending'),
                            sig=obs_sig(group_id='sim:loss'))
        self._screen = SCREEN_SETTLE
        self._sub = ''

    # (巨星/planner 触发评估器与银狼全域星基线已停用:判据 = 容器值回调[cw_faction_callbacks],簿记 =
    #  ScreenChanges sidecar,呈现 = pending 检查。)

    # ---------------------------------------------------------- 板面真值观察

    def _observe_board_truth(self) -> None:
        """板面真值观察(与实机「每备战帧面板观察」同契约;标签单一源
        = kernel ``_row_unit_tags``,容器行全量重算)。

        sim 是板面真值唯一持有者,kernel board 为派生量且基座未读时
        派生挂钩跳过——步界全量重算真值观察 board(等值零写):承担
        派生基座首读;sim 备战观察只写 node_path 无板面 obs 通道行写,
        全域写路径现均经 write_logic(装备穿戴分支含)使派生挂钩常态
        覆盖,本观察的漂移覆盖职责当前为防御性(基座首读为主要现役
        职能)。失配经容器吸收面(``_absorb_board_derived``,sim 证据
        前缀命中抑制面)以实际观察为准采新。触发点 = advance 步界(等值零写
        幂等,sim 板面观察的唯一步界)。

        选边型双羁绊角色(布洛妮娅,cw_chars.SIDE_PICK_DUAL_BONDS)经
        peers 透传按图鉴逻辑选边单边计入(选边不分排,peers = 全板其余
        有效单位)。"""
        truth: dict[str, int] = {}
        _view = self.gs.deployed.value
        all_units = [unit for _rn, sub in
                     (('front_row', _view.front_slots if _view is not None else ()),
                      ('back_row', _view.back_slots if _view is not None else ()))
                     for unit in (sub or []) if unit is not None]
        for row_name, sub in (('front_row', _view.front_slots if _view is not None else ()),
                              ('back_row', _view.back_slots if _view is not None else ())):
            for unit in (sub or []):
                if unit is None:
                    continue
                for tag in _row_unit_tags(unit, row_name,
                                          peers=[u for u in all_units
                                                 if u is not unit]):
                    truth[tag] = truth.get(tag, 0) + 1
        gs = self.gs
        plane, r = self._node_pos()
        if gs.board.value is not None and gs.board.value == truth:
            return
        gs.observe(gs.board, truth,
                   evidence=sim_evidence(f'board:p{plane}r{r}'),
                   sig=obs_sig(group_id='sim:board'))

    # ---------------------------------------------------------- 局结果面

    def _game_over(self) -> None:
        """局终(胜利:超位面 3 末节点存活,经 :meth:`_on_node_advance_terminal`
        披露 run_complete / 死亡:hp 归零且保底已用,经结算死亡分支;
        重入安全)。终态呈现 = 大厅屏:流程经 CwScreenBattleWait 终局锚
        (③B terminal_lobby)→ 主循环 3c 收尾,与实机「终局结算 → 返回
        货币战争 → 大厅」的消费链同形(sim 结算瞬时,直达终点)。"""
        self.done = True
        self._screen = SCREEN_LOBBY
        self._sub = ''

    def _hp_trail_append(self) -> None:
        hp = self.gs.hp.value
        if hp is not None:
            self.hp_trail.append(int(hp))

    def _tick(self) -> None:
        """驱动步计数(超上限 = 流程死循环响亮暴露)。"""
        self._steps += 1
        if self._steps > MAX_STEPS:
            raise RuntimeError(
                f'超过单局驱动步上限 {MAX_STEPS}(流程疑似死循环)')

    def result(self) -> SimRunResult:
        """局结果面(终局后消费;局中调用 = 各分量现值快照)。"""
        node = self.gs.node.value
        plane = node.plane if node is not None else 1
        round_num = node.round_num if node is not None else 1
        return SimRunResult(
            final_hp=int(self.gs.hp.value or 0),
            plane_reached=plane,
            rounds=(plane, round_num),
            hp_trail=tuple(self.hp_trail),
            unmodeled=dict(self.disclosures))


def install_backend(backend: SimBackend) -> None:
    """装配 sim 后端(端口槽 + kernel 事实事件 sink 订阅 + 动作分支 rng
    提供槽单点)。

    调用方(运行器/测试)负责 teardown 必卸(:func:`uninstall_backend`);
    端口槽单装配纪律由 ``cw_sim_ports`` 锁(重复安装 raise)。

    动作分支 rng 注入(3.4 联调接线;偏差申报的归属点):流程侧动作
    op → 上报函数族的采样分支(rng=None 回退)经
    ``cw_action_report.set_action_rng_provider`` 拿流键 rng——键形
    ``action/<tool>/<序号>``,序号 = 本装配内调用序(动作序列确定性
    ⟹ 采样链确定性);实机缺省 None = 未播种口径零变化。
    """
    import itertools

    from sr_od.application.currency_war.kernel.cw_action_report import (
        set_action_rng_provider,
    )

    seq = itertools.count()
    set_action_rng_provider(
        lambda tool: stream_rng(backend.seed, f'action/{tool}/{next(seq)}'))
    cw_sim_ports.install_sim_backend(backend)


def uninstall_backend() -> None:
    """卸载 sim 后端(端口槽 + 动作分支 rng 提供槽复位;
    幂等)。"""
    from sr_od.application.currency_war.kernel.cw_action_report import (
        set_action_rng_provider,
    )

    set_action_rng_provider(None)
    cw_sim_ports.uninstall_sim_backend()
