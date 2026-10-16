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
祈愿/阿哈(判据/选卡上报)。无 sim 观察腿族(partner/fortune/
wish_trial/star_tome/aha)呈现即卡 observe → 消费 + 逐 kind 披露,
候观察腿接线再呈现。

**确定性**:后端自有采样全部由 seed 派生(:func:`stream_rng` 流键,
键形沿用旧引擎模块号坐标系);动作腿采样(炉/骇客改件/晶矿/刷新)
经上报函数族 rng 形参,注入点在流程装配缝(运行器批)。

**装配**::func:`install_backend` = 端口槽装配;:func:`uninstall_backend`
幂等复位。测试 teardown 必卸(端口槽为进程全局)。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, replace

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
)
from sr_od.application.currency_war.kernel.cw_env_grants import (
    check_env_boss_grants,
    check_env_streak_grants,
    on_diamond_acquired,
)
from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    MegastarOption,
    SupplyOption,
)
from sr_od.application.currency_war.kernel.cw_gain_chain import (
    discharge_due_item_grants,
    gain_equipment,
    gain_invest_env,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
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
    aggregate_economy,
    normalize_invest_name,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    NodePos,
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


def xp_apply_amount(level: int, xp_cur: int, amount: int) -> tuple[int, int]:
    """任意经验量推进 ``(level, xp_cur)``(升级结转与 ``xp_apply_clicks``
    单一源同式:攒满门槛即升级、溢出结转;cap = ``MAX_PLAYER_LEVEL``,
    满级零推进——lv10 分母未定,按 U18 口径不再累计)。

    通用量版理由:节点基础经验含非单击倍数(+2/+12),无法折成
    「购买经验击数」走既有算子。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        MAX_PLAYER_LEVEL,
    )
    if amount <= 0 or level >= MAX_PLAYER_LEVEL:
        return level, xp_cur
    cur = xp_cur + amount
    while level < MAX_PLAYER_LEVEL:
        need = XP_TO_NEXT_LEVEL.get(level, 4)
        if cur < need:
            break
        cur -= need
        level += 1
    return level, cur


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

#: 联席决策额外策略选卡槽(机制文档口径挂 2-6;样本未命中候实机对账)。
JOINT_DECISION_EXTRA_SLOT: tuple[int, int] = (2, 6)

#: 单次 offer 候选张数(画面语义三选一;环境屏同构占位,U08)。
OFFER_CANDIDATES: int = 3

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
                          forced_quality: str = '',
                          ) -> tuple[str, ...]:
    """策略 offer 候选生成(U07③:先掷品质 → 该品质池均匀取 1;
    offer 内去重 + 排除已出选项 = 全程不重复)。

    ``forced_quality`` 非空 = 品质改写命中次(时代族环境,判据 =
    :func:`rewrite_quality_for_pick`):该张候选跳过品质掷点直取目标
    品质池(2026-10-14 用户裁定:固定品质后照常抽样,可观察面 = 候选
    全目标品质);目标品质池被排除集吃光 → 回退全池(排除后),回退
    语义 = 现役防御契约沿用(用户裁定:正常局不可达,不扩防御分支)。

    ``excluded`` = 本局已出过的全部选项名(后端持有的累计集,调用方
    须把返回值并入)。某品质池被排除集吃光 → 该候选回退全池(排除后)
    取;全池亦空 → 候选数不足如实少发(防御性声明,正常局不可达)。
    """
    banned = set(excluded)
    picks: list[str] = []
    for _ in range(OFFER_CANDIDATES):
        quality = forced_quality or _roll_quality(rng)
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


def rewrite_quality_for_pick(active_env: str | None,
                             pick_ordinal: int) -> str | None:
    """品质改写判据:当前环境命中「全改写型」条目且本次取卡序在改写集
    内 → 返回目标品质;否则 None(按默认分布抽样)。

    全改写型判据 = ``rewrite_picks == (1, 2, 3)``(时代族结构特征,建表
    校验保证该形状无 pending 歧义——部分改写型必填 pending_notes 的逆
    否)。部分改写型(头彩/尾彩)offer 覆盖面歧义未定案,不接入返回
    None(2026-10-14 用户裁定:实采定案后由各自建模批接入,复用本判据
    放宽一行)。pick_ordinal 坐标系 = 本局策略三选一呈现全局序 1 基,
    与 ``ENV_POOL_REWRITE.rewrite_picks`` 同坐标系。环境名直查不做归一
    (与现役注册表消费同款形状;环境名来自注册表注册,无 OCR 变异源)。
    """
    rewrite = ENV_POOL_REWRITE.get(active_env or '')
    if rewrite is None or rewrite.rewrite_quality == '' \
            or rewrite.rewrite_picks != (1, 2, 3):
        return None
    return rewrite.rewrite_quality if pick_ordinal in rewrite.rewrite_picks \
        else None


# ============================================================ 节点事件件
# (选项生成保留;apply_*_pick 动作腿停用——
#  pick 动作走 op → 上报函数族获得链,与实机同构。)


#: 遭遇档位数(U22 占位:实机四档旁证 + 加成表四档已定案)。
ENCOUNTER_TIER_COUNT: int = 4

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
#: 要求」节;M14 豁免位由后端结算腿承载)。
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
#  ——动作腿停用后不变:发放空表/特权投影仪/炉拖角色模式仍未建模。)

#: 环境结构化经济通道披露键(M02:两位面金通道已结构化,其余候效果批)。
DISCLOSURE_ENV_CHANNELS: str = 'env_economy_channels_pending_m02'

#: 开箱自发触发披露键(U23:首版无自发开箱,箱 = 备战席箱件开箱动作)。
DISCLOSURE_BOX_TRIGGER: str = 'box_spawn_trigger_pending_u23'

#: planner 选卡效果披露键(升费腿效果由 pick_planner 上报承载;其余
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
#: 败局走结算死亡腿不经此键 = 胜负判别单一源在披露集)。
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
    DISCLOSURE_AFFIX_SAMPLE: 'pool3_uniform_placeholder',
    ORE_PLANE_START_PENDING: 'face_gold_color_auto_open_unverified',
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
#: 过程 + 纯转移全量收齐,18 转移动作声明驱动全覆盖。
ADVANCE_TRIGGER_KINDS: frozenset[str] = frozenset({
    '', 'node_advance', 'battle_resolve', 'open_box', 'pick_box_card',
    'pick_megastar', 'pick_planner', 'pick_supply', 'pick_invest_env',
    'pick_invest_strategy',
})

#: 对账豁免场景键集(建模内合法失配 = 最上层呈现屏 ≠ 底层稳态画面,
#: 断言延后至稳态;场景判定 = :meth:`SimBackend._reconcile_exempt_reason`):
#: ① overlay 队列命中(``overlay_pending``:``_window_resume='offer'`` +
#:    ``_present_pending_overlay`` 呈现巨星/planner 等);
#: ② offer 日程命中(``offer_presented``:呈现投资策略屏);
#: ③ 节点窗让路恢复位未消费(``window_resume_pending``:让路期间选卡族
#:    经 ``_dismiss_modal`` 恢复到 offer 屏/节点屏)。
RECONCILE_EXEMPT_KINDS: frozenset[str] = frozenset({
    'overlay_pending', 'offer_presented', 'window_resume_pending',
})

#: 对账漂移保留证据的 disclosures 键(声明与状态机画面漂移早期警报;值 =
#: 漂移明细串列表,缺陷保留证据不停机)。
DECL_SCREEN_DRIFT: str = 'decl_screen_drift'


@dataclass
class SimBackend:
    """sim 游戏后端(一实例一局;端口协议实现 + 画面状态机 + 世界规则件)。

    构造即 reset(开局序列:词缀/boss 名单采样并写容器 → 简报屏 →
    (env_present)投资环境屏 → wait_one_one → P1r1 对应屏);运行面 =
    端口六口 + kernel 事实事件 sink 订阅,世界推进全部由流程驱动
    (动作腿 = op → 上报函数族,本后端零私有动作语义)。
    """

    #: 局级输入(确定性锚;词缀入 seed 后此字段语义 = override 见下)。
    seed: int
    cfg: RunConfig
    #: 世界容器(组合,唯一一份)。
    gs: GameState = field(init=False)
    # —— 画面状态机(私有;状态 = 档名 + 子态) ——
    _screen: str = field(init=False, default='')
    _sub: str = field(init=False, default='')
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
    #: 连胜/收入修饰 = 轮初口径),结算腿胜负后落账并清回 None。
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
            self._resolve_battle()
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
                report_screen_invest_env_obs(self.gs, CwScreenInvestEnvObs(
                    hit=True,
                    options=[(n, (i + 1) * 10) for i, n in enumerate(opts)],
                    refresh=None))
            return
        self._enter_wait_one_one()

    def _enter_wait_one_one(self) -> None:
        """wait_one_one 变体(开局补给动画等待;sim 瞬时呈现,下次问询
        即完成进 P1r1)。"""
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
        (节点窗起刚发牌)保持现值零写。"""
        if self._screen == SCREEN_PREP:
            self._present_modal(SCREEN_SHOP)
            if self.gs.shop.value is None and self._shop_record is not None:
                self.gs.observe(self.gs.shop, self._shop_record,
                                evidence=sim_evidence('shop:reopen'),
                                sig=obs_sig(group_id='sim:shop:reopen'))

    def _sync_shop_record(self) -> None:
        """商店牌面记录懒同步(全部驱动入口调用):在屏 payload 非
        ``None`` 即跟随记录。

        跟随面 = ``gs.shop`` 的一切写点——节点窗起发牌(deal_shop)、
        动作腿刷新/买卡(kernel 上报,均新建 payload 整体替换)。payload
        写入与下次开店之间必经驱动入口(策略帧循环先观察后决策,动作
        声明经 advance、开店经 click_answer),故入口同步即完整覆盖;
        离屏态(关店清 ``None``)不动记录——关店清的是呈现不是记录,
        节点级持久事实由本记录承载。"""

        payload = self.gs.shop.value
        if payload is not None:
            self._shop_record = payload

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
                # 局终声明消费腿(键表示切换批 design §2.6):kernel 终局
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
        elif decl.trigger == 'pick_invest_env':
            self._on_invest_picked(opening=True)
        elif decl.trigger == 'pick_invest_strategy':
            self._on_invest_picked(opening=False)
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
        self._entered_pos = eff
        self._enter_node_window(eff)

    def _on_node_advance_terminal(self) -> None:
        """胜利终局声明消费腿(trigger=node_advance ∧ next_screen=''):
        kernel 终局事件式声明(推进超出序列表末位面,现役 = 位面 3 末
        boss 结算存活)的世界消费——XP 入账(被离开节点类型,与现行
        局终前入账同序)+ 胜局披露 + 终局。hp 归零败局走结算死亡腿
        (:meth:`_resolve_battle` → :meth:`_game_over`,不经本分支)——
        披露集含 :data:`DISCLOSURE_RUN_COMPLETE` 与否 = 胜负判别单一源。
        此后 :meth:`_reconcile_next_screen` 走 done=True ∧ decl='' 合格
        分支,漂移面零新增。"""
        prev = self.gs.node.value
        if prev is not None:
            apply_node_xp(self.gs, node_type=prev.kind)
        self.disclosures[DISCLOSURE_RUN_COMPLETE] = 'survived_p3_boss'
        self._game_over()

    def _on_supply_picked(self) -> None:
        """补给选定落地:带钻选项给宝钻(世界事实写容器 diamond_count;
        钻信息 = 容器 chosen_supply 现值 2 元组 (角色,装备名列表) 按
        :data:`DIAMOND_EQUIP_NAMES` 名单派生(列表任一件名命中即钻;
        写端 = 补给画面 op 确认即写)。派生失败边 = 钻名 OCR 误读 →
        列表名不匹配 → 宝钻腿漏发;装备观察(整表)与钻数观察下一帧
        暴露失配,fail-visible 非静默)。"""
        chosen = self.gs.chosen_supply.value
        if chosen is not None and any(
                n in DIAMOND_EQUIP_NAMES for n in chosen[1]):
            cur = int(self.gs.diamond_count.value or 0)
            self.gs.observe(self.gs.diamond_count, cur + 1,
                            evidence=sim_evidence('supply:diamond'),
                            sig=obs_sig(group_id='sim:diamond'))
        self.disclosures.setdefault(SUPPLY_DIAMOND_SLOT_PENDING,
                                    'uniform_slot')

    def _on_invest_picked(self, *, opening: bool) -> None:
        """投资选卡落地(效果 = kernel 获得链,经 report_action_pick_*
        已写容器;本层返回 + 去重集累计,排除集读容器 opts 现值)。"""
        opts = (self.gs.invest_env_opts.value if opening
                else self.gs.invest_strategy_opts.value) or []
        (self.excluded_env if opening else self.excluded_invest).update(opts)
        # 追加随机环境型(在册名 = cw_investments.ENV_REROLL_NAMES,现役
        # 唯一 = 蓝海 id113):选卡首链(上报函数)已完成「获得本环境」全部
        # 写腿(active_env + 即时金 + 申报行);本腿紧接世界掷骰出卷中名,
        # 原语二次入链「获得卷中环境」(gain_invest_env 一次调用完成
        # active_env 改写 + 节点序列场改写 + 登记腿 + on_env_gained 全族
        # 效果,零新发放实现;两次获得语义,追加非替换)。无重复发金:池
        # 排除在册名后无任何 gold_instant 条目。session=None:本层字段面
        # 无会话可取,登记腿跳过、容器写照常(gain_invest_env None 语义)。
        # rng 必须显式传参:gain_invest_env/on_env_gained 的 rng
        # 形参缺省回退自掷(random.Random()),池含随机支环境(人才引进),
        # 不传则同 seed 不重放——双流键解耦,不走动作腿注入槽(该槽服务
        # 上报函数族按调用序取键,本腿直调 kernel 显式流键零耦合)。门条件
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
        # 「选择后」敌方难度读数即时反映(裁定 2026-10-14);开局环境选卡时
        # 节点未进窗(node None),写点内早退。
        self._update_difficulty_flag()
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
        """overlay 选定落地(模态返回 + 呈现检查):效果腿归各自上报/
        效果批,本层零效果。原私有队列出队腿
        停用——呈现数据源 = ``gs.screen_changes.pending``,消费 = 选卡
        上报内 ``consume_screen_change``(两世界同一行代码,register-
        consume.md「sim 消费」),本层不重复出队。
        """
        if kind == 'planner':
            self.disclosures[DISCLOSURE_PLANNER_EFFECT] = 'picked:report_leg'
        self._dismiss_modal()
        self._present_pending_overlay()

    # ---------------------------------------------------------- 状态机

    def _present_modal(self, screen_name: str) -> None:
        """模态呈现(压住底层画面;返回目标 = 当前屏,选完返回)。"""
        if self._screen == screen_name:
            return
        self._return_screen = self._screen
        self._return_sub = self._sub
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
          首件;其余画面 op 无 sim 观察腿,呈现即卡 observe 重试;
          partner 候选可自资格集算,候观察腿接线再呈现)→ 消费 +
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
                # 注册表缺位且画面 op 无 sim 观察腿(呈现即卡 observe
                # 重试;partner 候选可自资格集算,候 sim 观察腿接线再呈现)
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
            self._screen = SCREEN_PLANE_TRANSITION
            self._sub = ''
            return
        self._begin_node_window()

    @staticmethod
    def _screen_for_node(kind: str) -> str:
        """节点类型 → 呈现屏档名(_present_node_screen 同一映射,锚定
        trigger_screen 消费)。"""
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
            # 只冻结基数(金/进轮连胜/修饰 = 轮初口径),结算腿落账
            # (_resolve_battle);支付时点 = 结算屏,与实机一致。
            self._piggy_income_snap = (
                int(self.gs.gold.value or 0),
                max(int(self.gs.streak.value or 0), 0),
                income_modifiers_of(self.gs))
        else:
            # 非扑满清递延快照(纯防御,幂等清理,现网不可达路径零行为
            # 变化):扑满局奖励节点必走上分支;残留快照若带入非扑满
            # 节点窗,结算腿会给战斗节点叠发一份 reward 收入——未来
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
        # 首领节点条件发放(劳务派遣合同腿2;条件单一源 = kernel
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

        目标值参与门的备战/非备战二分:offer 槽命中 → 投资策略屏
        (非备战侧,fortune 条目存活等待);其余 = 节点类型映射
        (:meth:`_screen_for_node` 单一源——battle/reward → 备战,
        supply/遭遇 → 各节点屏,boss → 简报)。"""
        plane, r = self._node_pos()
        active_env = self.gs.active_env.value
        if offer_slots(plane, r, active_env):
            return SCREEN_INVEST_STRATEGY
        kind = node_sequence_of(
            plane, self.gs.node_seq_by_plane.value)[r - 1]
        return self._screen_for_node(kind)

    def _present_offer_or_node_screen(self) -> None:
        """offer 日程检查 → 节点屏呈现(节点窗口让路恢复序)。

        权威序 = 旧引擎实测:overlay 选定后复走节点窗 offer 检查
        (收尾检查序 overlay → offer → 下一节点),U07 固定日程生效于
        本节点备战窗口前——overlay 让路不吞 offer 槽;窗口前段(收入/
        环境金/商店全刷)已在本窗起点执行,恢复不重入。"""
        plane, r = self._node_pos()
        active_env = self.gs.active_env.value
        if offer_slots(plane, r, active_env):
            self._invest_pick_ordinal += 1
            forced = rewrite_quality_for_pick(str(active_env or ''),
                                              self._invest_pick_ordinal)
            rng = stream_rng(self.seed, f'M11/offer/p{plane}/r{r}')
            opts = sample_strategy_offer(rng, self.excluded_invest,
                                         forced_quality=forced or '')
            self._window_resume = 'node'
            self._screen = SCREEN_INVEST_STRATEGY
            self._sub = ''
            report_screen_invest_strategy_obs(self.gs,
                                              CwScreenInvestStrategyObs(
                                                  entry_ok=True,
                                                  options=[
                                                      (n, (i + 1) * 10, 10)
                                                      for i, n in
                                                      enumerate(opts)],
                                                  refresh_slots=[]))
            return
        self._present_node_screen()

    def _present_node_screen(self) -> None:
        """按节点类型呈现对应屏(battle/reward → 备战档,reward = 晶矿
        子态;supply → 补给;encounter → 遭遇节点;boss → BOSS 简报)。"""
        self._window_resume = ''
        plane, r = self._node_pos()
        kind = node_sequence_of(plane, self.gs.node_seq_by_plane.value)[r - 1]
        if kind == 'supply':
            rng = stream_rng(self.seed, f'M18/opts/p{plane}/r{r}')
            opts = supply_options(rng, normalize_invest_name(
                str(self.gs.active_env.value or '')))
            report_screen_supply_node_obs(self.gs, CwScreenSupplyNodeObs(
                in_node=True, options=list(opts), refresh_left=1))
            self._screen = SCREEN_SUPPLY
            self._sub = ''
            return
        if kind == 'encounter':
            report_screen_encounter_obs(self.gs, CwScreenEncounterObs(
                options=list(encounter_options()), refresh_left=None))
            self._screen = SCREEN_ENCOUNTER
            self._sub = ''
            return
        if kind == 'boss':
            self._screen = SCREEN_BOSS_BRIEFING
            self._sub = ''
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
        self._screen = SCREEN_PREP
        self._sub = PREP_SUB_ORE if points else ''

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
          ``ENV_ECONOMY`` 数值不变,双源同值校验构建期闭合);sig =
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
        """环境结构化经济通道·直发腿(M02:已结构化子集直接生效——位面
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

    # ---------------------------------------------------------- 结算腿

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
        """coarse 战斗结算(随机输出面;start_battle/pick_encounter/
        BOSS 简报点空白三源共用;重入幂等守卫 = 已结算节点键)。"""
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
        _floor, dead = apply_hp_outcome(self.gs, outcome)
        self._hp_trail_append()
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
        全域写路径现均经 write_logic(装备穿戴腿含)使派生挂钩常态
        覆盖,本观察的漂移覆盖职责当前为防御性(基座首读为主要现役
        职能)。失配经容器吸收面(``_absorb_board_derived``,sim 证据
        前缀命中抑制面)以实际观察为准采新。触发点 = advance 步界(等值零写
        幂等,sim 板面观察的唯一步界)。"""
        truth: dict[str, int] = {}
        _view = self.gs.deployed.value
        for row_name, sub in (('front_row', _view.front_slots if _view is not None else ()),
                              ('back_row', _view.back_slots if _view is not None else ())):
            for unit in (sub or []):
                if unit is None:
                    continue
                for tag in _row_unit_tags(unit, row_name):
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
        披露 run_complete / 死亡:hp 归零且保底已用,经结算死亡腿;
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
    """装配 sim 后端(端口槽 + kernel 事实事件 sink 订阅 + 动作腿 rng
    提供槽单点)。

    调用方(运行器/测试)负责 teardown 必卸(:func:`uninstall_backend`);
    端口槽单装配纪律由 ``cw_sim_ports`` 锁(重复安装 raise)。

    动作腿 rng 注入(3.4 联调接线;偏差申报的归属点):流程侧动作
    op → 上报函数族的采样腿(rng=None 回退)经
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
    """卸载 sim 后端(端口槽 + 动作腿 rng 提供槽复位;
    幂等)。"""
    from sr_od.application.currency_war.kernel.cw_action_report import (
        set_action_rng_provider,
    )

    set_action_rng_provider(None)
    cw_sim_ports.uninstall_sim_backend()
