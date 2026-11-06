"""sim 游戏后端 SimBackend(驱动反转;状态副本本体 + 画面状态机 + overlay 触发层)。

真流程(外层循环 + 画面 op + 动作 op + 策略器)当驱动者,本后端 = sim 状态副本:
组合持有 :class:`GameState`(禁子类——Field 通道与裸属性两套状态纪律
不得混于一体,决策输入形状不随运行模式漂移),自持实机不可观察的簿记
(采样去重集/overlay 队列/一次性标志/局结果面)。一实例一局。

**字段收敛判据**(状态容器一份,禁第三形态):实机可观察/影响玩法的状态副本事实
→ 状态容器 Field;生成器采样簿记 → 本后端私有。旧引擎 ``_Eng`` 三处双账
全部消灭:``plane``/``round_num`` → ``gs.node``;相位载荷(options/
supply/encounter/box/晶矿面板)→ 状态容器各 opts 槽(经 ``cw_screen_report``
同名上报函数送达,与实机观察同一条写通道,本后端不私持副本);
``streak_unsigned`` → 状态容器带符号连胜派生读 ``max(signed, 0)``。

**画面状态机**:状态 = (screen_info 档名,子态载荷)。转移源两类:
1. **动作后果声明**(声明化迭代主通道):动作 op 经
   ``cw_sim_ports.declare_world`` 喂入 :meth:`advance`,按
   ``decl.trigger`` 分派(键集单一源 = :data:`ADVANCE_TRIGGER_KINDS`,
   3.3 起 18 转移动作全量在表)——node_advance → 节点推进、
   battle_resolve → 战斗结算、选卡族/箱 → 各状态过程、``''`` → 纯
   画面转移;推进后按 ``decl.next_screen`` 等值对账画面档
   (:meth:`_reconcile_next_screen`)。
2. **点击源**(flow-seam 附录 B 边界登记:不入 kernel 事件集的推进型
   点击):简报下一步 / BOSS 简报点空白 / 位面过渡点空白 / 补给刷新 /
   开店。经端口 ``click_answer`` 感知。

**节点推进序列**(模块号流键坐标系):写 ``gs.node`` → 轮首收入
(kernel ``round_start_income`` 三分支,U04 败补消费状态容器 ``pending_loss``)
→ 位面开局环境发放分道(声明矿环境 → 声明入队 + 过期清理,其余 →
直发金)→ 商店自动全刷(整店锁跳过)→ overlay 队列检查 → offer
日程检查(U07 固定轮次 + 联席决策)→ 按节点类型呈现对应屏
(battle/reward → 备战档;奖励节点晶矿子态 = 面板矿 + 位面开局声明矿
同批合并,spheres 写一律过挂接入口
``cw_ore_channel.report_spheres_observed``;supply → 补给;encounter →
遭遇节点;boss → BOSS 简报)。节点经验在节点推进时入账
(NODE_XP_BY_TYPE 表原样);连胜转移在战斗结算后。

**overlay 触发层**(终态):判据 = kernel 值回调
(cw_faction_callbacks,deployed 逻辑写尾)→ 状态容器登记
(gs.screen_changes.pending)→ 呈现(问询时点懒呈现 + advance 纯转移
尾 + 节点窗起点,压住底层画面,选完返回)。一期目录:巨星/planner
(状态容器值回调判据)、开箱/专家/星徽(open_* 上报直登)、占卜屋/伙伴/
祈愿/阿哈(判据/选卡上报)。无 sim 观察分支族(partner/fortune/
wish_trial/star_tome/aha)呈现即卡 observe → 消费 + 逐 kind 披露,
等观察分支接通调用后再呈现。

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
from sr_od.application.currency_war.data.cw_shop_odds import (
    REFRESH_PROB,
    SHOP_SLOTS,
)
from sr_od.application.currency_war.data.cw_synthesis import SYNTHESIS_BASES
from sr_od.application.currency_war.kernel.cw_battle_calib import (
    roll_rotation_per_stage,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    LostNodeRef,
    RoundStartIncome,
    round_start_income,
    world_shop_refresh_cost,
)
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    BOARD_REWRITE_SELL_ALL_DEAL,
    CounterKey,
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
    GAIN_CHAIN_PRODUCER,
    LEVEL_GRANT_PRODUCER,
    check_strategy_battle_end_heal,
    check_strategy_battle_grants,
    check_strategy_bench_count_xp,
    check_strategy_bench_leave_gold,
    check_strategy_bench_left_cost_xp,
    check_strategy_bond_battle_grants,
    check_strategy_bond_tier_grants,
    check_strategy_boss_battle_grants,
    check_strategy_boss_clear_gold,
    check_strategy_boss_completion_grants,
    check_strategy_boss_end_heal,
    check_strategy_empty_equip_xp,
    check_strategy_equip_count_xp,
    check_strategy_equip_expiry,
    check_strategy_gift_grants,
    check_strategy_hp_loss_gold,
    check_strategy_hp_loss_grants,
    check_strategy_kechuan_wear_grants,
    check_strategy_level_equip_grants,
    check_strategy_level_grants,
    check_strategy_node_char_grants,
    check_strategy_node_rewrite,
    check_strategy_plane_boss_grants,
    check_strategy_plane_start_grants,
    check_strategy_reward_ore_grants,
    check_strategy_win_gold_grants,
    consume_strategy_interest_topup,
    discharge_due_item_grants,
    discharge_due_item_opens,
    discharge_due_kechuan_leaves,
    discharge_due_strategy_grants,
    discharge_strategy_bond_battle_grants,
    gain_bench_item,
    gain_character,
    gain_equipment,
    gain_invest_env,
    gain_invest_strategy,
    take_strategy_death_save,
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
    refresh_shop_randomized_pending_stamp,
    seed_opening_state,
    settle_xp_observe,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_ORE_GRANTS,
    ENV_ORE_PANEL_BONUS,
    ENV_POOL_REWRITE,
    ENV_REROLL_ASSUMPTION_POOL,
    ENV_REROLL_NAMES,
    ENV_SUPPLY_EQUIP_COUNT,
    FORESIGHT_ENV_REWRITE_PRIORITY,
    FORESIGHT_EXEMPTION_READING,
    FORESIGHT_REWRITE_SCREEN_SHAPE,
    HYPEREMIT_SPEC_ID,
    HYPEREMIT_SPEC_NAME,
    INVESTMENT_ENVS,
    INVESTMENT_STRATEGIES,
    STRATEGY_BATTLE_HEAL_SCOPE_ASSUMPTION,
    STRATEGY_BENCH_LEAVE_GOLD_GRANTS,
    STRATEGY_BOSS_HEAL_HP_CAP_ASSUMPTION,
    STRATEGY_BOSS_HEAL_PERFECT_WIN_BIAS,
    STRATEGY_DEATH_SAVE_ASSUMPTION_KEYS,
    STRATEGY_DELAYED_GRANTS,
    STRATEGY_DELAYED_OFFERS,
    STRATEGY_ECONOMY,
    STRATEGY_EFFECTS,
    STRATEGY_HP_LOSS_BUCKET_ASSUMPTION,
    STRATEGY_HP_LOSS_GOLD_BASELINE_ASSUMPTION,
    STRATEGY_NODE_REWRITE_TRIGGERS,
    STRATEGY_PLANE_START_GRANTS,
    STRATEGY_RANDOM_GRANT_ASSUMPTION_UNIFORM_V0,
    STRATEGY_RANDOM_GRANTS,
    STRATEGY_WIN_GOLD_SCOPE_ASSUMPTION,
    StrategyDelayedOffer,
    aggregate_economy,
    dakuozhao_deduction_plan,
    get_strategy,
    normalize_invest_name,
    strategy_loss_battle_modifier,
)
from sr_od.application.currency_war.kernel.cw_levelup_callbacks import (
    take_levelup_world_decl,
)
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    NodePos,
    PlaneSeqMissingError,
    final_supply_pos,
    node_sequence_of,
    sequence_next,
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
from sr_od.application.currency_war.kernel.cw_shop_deal import (
    sample_shop_deal,
    sample_shop_deal_forced,
)
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl
from sr_od.application.currency_war.obs.cw_node_reader import NodeSlot
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
#: 位面详情屏(接管补采委派链的呈现屏:备战点节点条开详情 → CwScreenPlaneIntel
#: 识别 → 点 X 关回备战;呈现态 = 备战上的模态,封闭链见 T-440 委派闭环)。
SCREEN_PLANE_INTEL: str = '货币战争-位面详情'
SCREEN_BOX: str = '货币战争-备战-武装箱选择'
SCREEN_EXPERT: str = '货币战争-备战-专家邀请函'
SCREEN_MEGASTAR: str = '货币战争-盛会之星'
SCREEN_PLANNER: str = '货币战争-银狼升星'
#: 战斗窗口呈现屏(sim 结算瞬时完成;战斗等待动画窗属实机时间维)。
#: 档名取流程消费面 = 「货币战争-结算」(currency_war_settlement.yml,
#: 「按钮-继续挑战」宿主屏):结算后流程经 CwScreenBattleWait 结算分支
#: + CwOpSettleConfirm 点击推进(档名 = 流程消费识别标志;错位则
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

#: 免战跳过按钮替换/跳过消费的节点辖域(免战牌;卡面「进入战斗节点时」
#: 词义类型读法 = 仅普通战斗——「战斗 ↔ 遭遇」「首领」「奖励」卡词汇分立
#: 先例已登记,词义依据同战争边疆 T-18 类型读法)。实机按钮出现面失配
#: (遭遇/首领/奖励备战帧也替换按钮)的校准挂披露键
#: :data:`CW_SKIP_SCOPE_BATTLE_ONLY_ASSUMPTION`,失配 = 本常量单点改值
#: 跟随,禁按 ``COMBAT_NODE_TYPES`` 顺延扩域。
CW_SKIP_NODE_KINDS: frozenset[str] = frozenset({'battle'})


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


def strategy_xp_per_node_of(gs: GameState) -> int:
    """持卡聚合的每节点静态经验量(买断制 xp_per_node=4 消费面;
    单一源 = aggregate_economy 求和分量,静态量通道,禁动态计数挂此
    ——条件 XP 族走各自 check_* 纯判定)。零 rng 纯读。"""
    return aggregate_economy(list(gs.active_strategies.value or [])).xp_per_node


def strategy_boss_gold_of(gs: GameState) -> int:
    """持卡策略聚合的进 boss 节点金(特战资金系,进 boss 节点每窗一笔)。

    单一源 = ``aggregate_economy``(多卡求和);返回 0 = 无该金效果条目,
    调用方(节点窗收尾)零值零写。live 侧无此写端:金有整字段观察
    覆盖,实机真发由下一备战帧金观察覆盖兜底——金面禁 logic 直写防
    双计(权威裁定 = ``cw_effect_inventory.advance_node`` docstring
    「尾款金面走观察覆盖兜底」行),sim 状态副本自持账无观察可兜,不发即
    持卡局金系统性偏低,故唯 sim 侧补写。
    """
    return aggregate_economy(
        list(gs.active_strategies.value or [])).gold_per_boss_node


def strategy_final_supply_gold_of(gs: GameState) -> int:
    """持卡策略聚合的「最后一个补给阶段」金(尾款交付系,进基准点窗一笔)。

    单一源 = ``aggregate_economy``(多卡求和);基准 = 展平全序列最末
    supply 位(:func:`final_supply_pos`),整局一次——辖域与「后」字时点
    两假设见披露键 ``DISCLOSURE_FINAL_SUPPLY_GOLD_SCOPE`` /
    ``DISCLOSURE_FINAL_SUPPLY_GOLD_TIMING``。返回 0 = 无该金效果条目,调用方
    (节点窗收尾)零值零写。live 侧无此写端:金有整字段观察覆盖,实机
    真发由下一备战帧金观察覆盖兜底——金面禁 logic 直写防双计(权威裁定
    = ``cw_effect_inventory.advance_node`` docstring「尾款金面走观察
    覆盖兜底」行),sim 状态副本自持账无观察可兜,不发即持卡局金系统性偏低,
    故唯 sim 侧补写。
    """
    return aggregate_economy(
        list(gs.active_strategies.value or [])).gold_at_final_supply


def strategy_invest_node_gold_of(gs: GameState) -> int:
    """持卡策略聚合的每节点金(定期福利系,进任意节点窗每窗一笔)。

    单一源 = ``aggregate_economy``(多卡求和);注册族姊妹剩余价值/按劳
    分配的注册值系战斗表现条件金的每节点期望近似(条件与上限未注册,
    实机和模拟器两边零建模),效果条目经聚合通道自动跟随、无双计。返回 0 = 无该金效果条目,调用方
    (节点窗收入段)零值零写。live 侧无此写端:金有整字段观察覆盖,实机
    真发由下一备战帧金观察覆盖兜底——金面禁 logic 直写防双计(权威裁定
    = ``cw_effect_inventory.advance_node`` docstring「尾款金面走观察
    覆盖兜底」行),sim 状态副本自持账无观察可兜,不发即持卡局金系统性偏低,
    故唯 sim 侧补写。
    """
    return aggregate_economy(
        list(gs.active_strategies.value or [])).gold_per_node


#: 分期金「现在」效果条目实存性披露键(建模假设档,静态常量已登记,无运行时
#: setdefault 动作;家族先例 = cw_effect_inventory.
#: STRATEGY_ON_MERGE_LIVE_UNVERIFIED 同形)。登记一件实机未证事实:
#: 用户裁决(strategy-env-impacts.md 用户裁决段,2026-09-10)把长期主义
#: 系按「拿卡当场 +7 + 接下来 3 次进节点各 +7」4 次处理,并明示
#: 「不确定是不是4次」——「现在」效果条目在拿卡拍是否真发、与「节点」效果条目是否
#: 分离,持卡局档案金轨迹核对(当场段有无即判 4/3)。sim 现役只建模
#: 「节点」效果条目(「现在」效果条目的状态副本写端 = T-112 族级待办维持不建);live 由游戏
#: 自算自显,本假设零误真值。退役条件 = 实机局采得拿卡帧金轨迹定案。
STRATEGY_GOLD_NEXT_NODES_NOW_LEG_UNVERIFIED: str = (
    'strategy_gold_next_nodes_now_leg_unverified')


def apply_invest_installment_gold(gs: GameState, *, plane: int,
                                  round_num: int) -> int:
    """持卡分期金节点窗效果条目(长期主义系「接下来 count 次」,进任意节点
    窗每卡每窗一笔)。

    递减状态容器字段 = ``gs.strategy_gold_next_nodes_left``(键 = 卡规范名,值
    = 剩余效果条数):逐卡判剩余 >0 → 按 :data:`STRATEGY_ECONOMY` 注册值
    ``gold_next_nodes_amount`` 支付该卡独立金笔 → 剩余递减;耗尽短路
    零写(条目留置 0),游戏终局剩余效果条目自然蒸发不补发。支付源 = 各条目
    注册值按卡名直读,**禁 aggregate_economy**:聚合 amount 求和/count
    取 max = 策略侧选卡估值口径,对分期双持 = 畸形(count 取 max 丢一
    卡窗口、amount 求和错额);状态副本里的值 = desc 逐卡字面「每次获得7/9
    金币」。与在码 gold_per_node 效果条目(定期福利系)同窗并存 = 同段两笔
    独立写、互不聚合。evidence 前缀钉死
    ``strategy:installment:<卡名>:p{plane}r{r}``(完整卡名段+分隔符:
    「长期主义」系「长期主义+」真前缀,消费侧过滤禁裸前缀匹配);
    状态容器递减 = 单笔 write_logic 簿记(非金 Field 登记事实直写先形)。
    注册表缺行/零额 = 条目悬空跳过不递减(下次窗重试自愈,拒落域不置一次性标志位
    同向)。幂等性住调用方窗口守卫(:meth:`SimBackend._begin_node_
    window`),本函数无内建幂等——窗口路径外直调会双发。live 侧无此
    写端:金有整字段观察覆盖,实机真发由下一备战帧金观察覆盖兜底
    (金面禁 logic 直写防双计,权威裁定 = ``cw_effect_inventory
    .advance_node`` docstring);sim 状态副本自持账无观察可兜,不发即持卡
    局分期段系统性偏低,故唯 sim 侧补写。全节点型计数:凡进窗即一期
    (supply/reward/battle/boss/修饰局插入节点照算,纯节点事件先例
    T-106 稿承 T-98 §1.1)。返回本窗发金笔数(审计/测试消费)。
    """
    remaining = dict(gs.strategy_gold_next_nodes_left.value or {})
    if not remaining:
        return 0
    fired = 0
    for canon, left in list(remaining.items()):
        if int(left) <= 0:
            continue
        eff = STRATEGY_ECONOMY.get(canon)
        amount = eff.gold_next_nodes_amount if eff is not None else 0
        if amount <= 0:
            continue
        tag = f'strategy:installment:{canon}:p{plane}r{round_num}'
        gs.observe(gs.gold, int(gs.gold.value or 0) + amount,
                   evidence=sim_evidence(tag),
                   sig=obs_sig(group_id='sim:strategy'))
        remaining[canon] = int(left) - 1
        fired += 1
    if fired:
        gs.write_logic(gs.strategy_gold_next_nodes_left, remaining,
                       produced_by='SimBackend',
                       evidence=f'strategy:installment:p{plane}r{round_num}',
                       sig=logic_sig('sim:strategy'))
    return fired


def apply_round_start_income(gs: GameState, *, plane: int, round_num: int,
                             node_type: str, streak: int,
                             pending_loss: LostNodeRef | None = None,
                             interest_floor: int = 0,
                             ) -> IncomeApplied:
    """轮首收入结算并 obs 写金(节点推进序列调用一次)。

    - ``streak`` = 收入侧无符号连胜计数(进轮连胜;派生读 = 状态容器带符号
      取 ``max(signed, 0)``,禁第二账);
    - ``pending_loss`` = 上一败掉的战斗类节点引用(单条登记的待办,状态容器
      ``gs.pending_loss``):非 supply/reward 节点传入触发 kernel 败补支
      (U04 口径);supply/reward 轮不传(败态跨轮保留,仅下一战斗轮
      消费——与 kernel 分支序一致);消费后清回 None 由调用方负责。
    - ``interest_floor`` = 开源节流条件息顶满下限(载体消费位传入,见
      ``_begin_node_window``;直调面〔单测/单元锁〕不传 = 零漂移)。
    """
    mult, flat, cap = income_modifiers_of(gs)
    gold_before = int(gs.gold.value or 0)
    effective_loss = (pending_loss
                      if node_type not in INCOME_BRANCH_NODE_TYPES else None)
    row = round_start_income(
        plane, round_num, node_type, gold_before, streak,
        lost_node=effective_loss, win_reward_mult=mult,
        interest_flat=flat, interest_cap=cap, interest_floor=interest_floor)
    gold_after = gold_before + row.total
    tag = f'income:p{plane}r{round_num}'
    gs.observe(gs.gold, gold_after, evidence=sim_evidence(tag),
               sig=obs_sig(group_id=f'sim:{tag}'))
    # 利息累计账入账 + 条件发放检查(T-27 公司契约条件分支;收入应用
    # 单一收尾点,四分支 supply/reward/败补/常规全含 interest 分量,在此
    # 一处收尾即全分支随计)。record 先于 check 同组相邻;check 在金
    # 落账后(发放与收入同窗,金真值先行)。幂等性住调用方窗口守卫
    # (_begin_node_window),本函数无内建幂等——窗口路径外直调会双加,
    # 调用面纪律见函数 docstring。sig = logic_sig('sim:env')(触发函数
    # 两写均 logic 渠道,streak 接入调用同款单形态)。返回值忽略 = sim 无
    # 状态副本数值回调(托帕&账账无宝钻式联动;本模块零日志面,判读走
    # 状态容器/台账)。
    gs.effects.record_interest_earned(row.interest)
    check_env_interest_grants(gs, logic_sig('sim:env'))
    return IncomeApplied(row=row, gold_before=gold_before,
                         gold_after=gold_after)


def streak_income_after(streak: int, *, node_type: str,
                        won: bool, keep_on_loss: bool = False) -> int:
    """收入侧无符号连胜计数转移(战斗类胜 +1/败归零;奖励/补给不动)。

    keep_on_loss = 败局连胜维持(嘴硬族;仅带符号正值维持,读法边界见
    :func:`streak_signed_after`):辖战斗类败局分支,无符号口径下正值
    保留原值、零维持与清零等值;无 piggy 形参,扑满帧经 node_type=
    'reward' 恒原样返回,扑满帧维持语义不在本口辖域(断言归
    :func:`streak_signed_after` 面)。维持的是计数,败局收入恒无连胜
    成分(收入公式战败无),与金账无关。保留口 = 纯函数判读/测试对账;
    后端运行面用状态容器带符号派生,不再持第二账。缺省 False = 现行为
    逐位不变。"""
    if node_type not in COMBAT_NODE_TYPES:
        return streak
    if not won and keep_on_loss:
        return streak if streak > 0 else 0
    return streak + 1 if won else 0


def streak_signed_after(streak_signed: int, *, node_type: str,
                        won: bool, piggy: bool = False,
                        keep_on_loss: bool = False) -> int:
    """状态容器带符号连胜转移(连胜 +/连败 −;战斗类胜 +1/败取负向计数;
    奖励/补给轮不动;与旧引擎逐位同式)。

    扑满帧例外(piggy=True,2026-10-10 用户裁定):胜 +1/败清零——
    败清零非负账;深井角斗场等连胜触发器读共用账自然跟随。

    keep_on_loss = 败局连胜维持(嘴硬族):读法边界 = 仅带符号正值维持
    ——「原来的连胜数」字面辖域 = 连胜计数,零/连败无连胜数可维持,
    desc 未写负值分支 = 判读申报制(后继族稿禁当已定案结论转引);辖域 =
    战斗类与扑满帧两败局分支(signed>0 → 原值保留,非正值照常转移),
    胜局/奖励/补给分支形参不参与。缺省 False = 现行为逐位不变。"""
    if piggy:
        if won:
            return streak_signed + 1 if streak_signed > 0 else 1
        return streak_signed if (keep_on_loss and streak_signed > 0) else 0
    if node_type not in COMBAT_NODE_TYPES:
        return streak_signed
    if won:
        return streak_signed + 1 if streak_signed > 0 else 1
    if keep_on_loss and streak_signed > 0:
        return streak_signed
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

    把结果写进状态副本 = 结算原语 ``settle_xp_observe`` 一行调用(推进 + 观察
    双笔 + 跨级连锁统一收尾,模拟器各经验效果条目同一入口;帽形参经
    ``level_cap_of`` 随链在原语内)。集外节点型 = 0 经验不入账
    (词表漂移在调用方暴露)。返回本节点实际入账经验量。
    """
    amount = NODE_XP_BY_TYPE.get(node_type, 0)
    if amount <= 0:
        return 0
    settle_xp_observe(gs, amount, sig=obs_sig(group_id='sim:xp'),
                      evidence=sim_evidence('xp:node'))
    return amount


def apply_strategy_pick_xp(gs: GameState, picked: Sequence[str]) -> int:
    """策略选卡落地拍即时经验入账(通用通道,辖域 = 注册表
    xp_instant>0 全体,字段分派非单卡特判)。

    为什么:sim 状态副本无观察、经验只有自持账,选卡当场即时型不在 kernel
    获得链发放(链内加经验写会连带 live——live 同拍 = 观察覆盖零写,
    经验面板画面可读,伟大征服口径),sim 不发即持卡局等级进度系统性
    失真,下游商店发牌分布/上阵上限/升级决策全链读等级现值。数额 =
    逐卡直读 :data:`STRATEGY_ECONOMY` 现值,**禁 aggregate_economy**:
    其聚合字段集不含 xp_instant,误走 = 静默零发放;且聚合语义 = 周期型
    重评,与「选卡单事件一次性发放」不匹配,逐卡各发各的(同持多卡笔笔
    独立)。把结果写进状态副本 = 结算原语 ``settle_xp_observe`` 一行调用(帽经
    ``level_cap_of`` 随链在原语内),evidence 按 ``xp:strategy_pick:<卡名>``
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
        settle_xp_observe(gs, amount, sig=obs_sig(group_id='sim:xp'),
                          evidence=sim_evidence(f'xp:strategy_pick:{canon}'))
        total += amount
    return total


def apply_strategy_plane_refire_xp(gs: GameState,
                                   picked: Sequence[str]) -> int:
    """策略选卡落地拍位面段补发经验入账(通用通道,辖域 = 注册表
    xp_per_plane>0 全体,字段分派非单卡特判;用户裁定 2026-11-01 确定:
    「现在以及每个位面开始时」族中途拿卡时,当前已开始的位面其位面段
    登记拍全额补发,后续位面开始事件照常走位面首节点窗效果条目)。

    为什么:位面段 XP(把结果写进状态副本的实现分支)挂 sim 位面首节点窗(:meth:`SimBackend
    ._apply_strategy_plane_start_xp`),只对登记后到达的 (plane,1) 窗
    发放,拿卡晚于位面开始时该位面段对持卡局系统性缺失(sim 无观察,
    不补即持卡局等级进度失真,即时经验效果条目同缺口来源)。已开始判据与
    kernel 登记拍补发桥(apply_effect_plane_refire_grant)同口径:策略卡
    登记恒发生于节点窗内(策略选卡全日程非 round-1,开场 1-1 前弹的是
    投资环境——live 权威版本 screen_flow_timing.md「第一次投资策略 overlay」
    节),进窗推进已在 (plane,1) 消费过位面开始边界 → ``gs.node`` 在场
    即已开始,None = 保守零补发(禁猜)。数额 = 逐卡直读
    :data:`STRATEGY_ECONOMY` 现值,**禁 aggregate_economy**(聚合字段集
    不含 xp_per_plane,误走 = 静默零发放);写入形态与
    :func:`apply_node_xp` 同款,evidence 按
    ``xp:strategy_plane_refire:<卡名>`` 与节点经验/即时经验笔分账,sig
    同组(同域字段同组,笔间靠 evidence 区分)。返回本批实际入账经验
    总量。
    """
    if gs.node.value is None:
        return 0
    total = 0
    for name in picked:
        canon = normalize_invest_name(str(name or ''))
        eff = STRATEGY_ECONOMY.get(canon)
        amount = eff.xp_per_plane if eff is not None else 0
        if amount <= 0:
            continue
        settle_xp_observe(gs, amount, sig=obs_sig(group_id='sim:xp'),
                          evidence=sim_evidence(
                              f'xp:strategy_plane_refire:{canon}'))
        total += amount
    return total


def apply_strategy_plane_refire_gold(gs: GameState,
                                     picked: Sequence[str]) -> int:
    """策略选卡落地拍位面段补发金入账(通用通道,辖域 = 注册表
    gold_per_plane>0 全体,字段分派非单卡特判;用户裁定 2026-11-01 族级
    确定的「现在及每个位面开始时」族中途拿卡补发,与 XP 支
    :func:`apply_strategy_plane_refire_xp` 同判同形)。

    为什么:位面段金(把结果写进状态副本的实现分支)挂 sim 位面首节点窗(:meth:`SimBackend
    ._apply_strategy_plane_start_gold`),只对登记后到达的 (plane,1) 窗
    发放,拿卡晚于位面开始时该位面段对持卡局系统性缺失——live 同拍零写
    (游戏自加,金整字段由观察覆盖收尾定值,金面禁直写),sim 不补即持卡局金
    轨线失真,下游利息/购买力全链读金现值。已开始判据与 XP 支同口径:
    策略卡登记恒发生于节点窗内(策略选卡全日程非 round-1),进窗推进
    已在 (plane,1) 消费过位面开始边界 → ``gs.node`` 在场即已开始,
    None = 保守零补发(禁猜)。数额 = 逐卡直读 :data:`STRATEGY_ECONOMY`
    现值,**禁 aggregate_economy**(聚合字段集不含 gold_per_plane,误走 =
    静默零发放);逐卡各一笔独立 observe(evidence 按
    ``strategy:plane_gold_refire:<卡名>`` 与位面窗金效果条目
    ``strategy:plane_gold:p<位面>`` 分账,sig 同组 sim:strategy 同域
    字段,笔间靠 evidence 区分)。状态容器金缺读(None)= 本拍零写留待观察
    覆盖,禁猜(env 形 None 视 0 照写会伪造金绝对值假真值,不取)。
    返回本批实际入账卡数。"""
    if gs.node.value is None:
        return 0
    applied = 0
    for name in picked:
        canon = normalize_invest_name(str(name or ''))
        eff = STRATEGY_ECONOMY.get(canon)
        amount = eff.gold_per_plane if eff is not None else 0
        if amount <= 0:
            continue
        gold_now = gs.gold.value
        if gold_now is None:
            continue
        gs.observe(gs.gold, int(gold_now) + amount,
                   evidence=sim_evidence(f'strategy:plane_gold_refire:{canon}'),
                   sig=obs_sig(group_id='sim:strategy'))
        applied += 1
    return applied


def apply_strategy_plane_refire_item(gs: GameState,
                                     picked: Sequence[str]) -> int:
    """策略选卡落地拍位面段补发占席道具入席(通用通道,辖域 = 注册表
    STRATEGY_PLANE_START_GRANTS 全体,字段分派非单卡特判;用户裁定
    2026-11-01 族级确定的「每个位面开始时」族中途拿卡补发·当前位面
    全额,裁定注释点名终身学习共享,与 XP 支
    :func:`apply_strategy_plane_refire_xp` / 金支
    :func:`apply_strategy_plane_refire_gold` 同判同形)。

    为什么:位面段发放(状态副本落席实现分支)挂 sim 位面首节点窗
    (check_strategy_plane_start_grants 位面开局插入位置),只对登记后到达
    的 (plane,1) 窗发放,拿卡晚于位面开始时当前位面段对持卡局系统性
    缺失——live 同拍零写(游戏自发,道具入栏 = 观察覆盖),sim 不补即
    持卡局备战席轨线失真。已开始判据与 XP/金支同口径:策略卡登记恒
    发生于节点窗内,进窗推进已在 (plane,1) 消费过位面开始边界 →
    ``gs.node`` 在场即已开始,None = 保守零补发(禁猜)。发放 = 逐卡
    直读 STRATEGY_PLANE_START_GRANTS 现值按 count 逐件
    gain_bench_item(rand=False),evidence 按
    ``bench:strategy_plane_refire:<卡名>`` 与常规位面开始笔分账,sig
    同组。返回本批实际入席件数。
    """
    if gs.node.value is None:
        return 0
    placed = 0
    for name in picked:
        canon = normalize_invest_name(str(name or ''))
        grant = STRATEGY_PLANE_START_GRANTS.get(canon)
        if grant is None:
            continue
        for _ in range(grant.count):
            ok = gain_bench_item(gs, grant.item, rand=False,
                                 sig=logic_sig(group_id='sim:strategy'),
                                 evidence=sim_evidence(
                                     f'bench:strategy_plane_refire:{canon}'))
            if ok:
                placed += 1
    return placed




def apply_strategy_pick_hp(gs: GameState, picked: Sequence[str],
                           rng: random.Random) -> int:
    """策略选卡落地拍即时生命入账(通用通道,辖域 = 注册表
    hp_instant≠0 全体,正加负损双向,字段分派非单卡特判)。

    为什么:sim 状态副本无观察、hp 只有自持账(开局查表种 + 战斗结算写),
    选卡当场即时型不在 kernel 获得链发放——链内写 hp 会在 live 侧引入
    hp 逻辑写端,违 fields.md hp 写入闸「无逻辑写入方」结构(live 同拍
    零写,游戏自算 + 血量条观察覆盖收尾),sim 不发即持卡局血线系统性
    失真,败局余量/保底触发概率/局终时点全链读现值。数额 = 逐卡直读
    :data:`STRATEGY_ECONOMY` 现值,**禁 aggregate_economy**(聚合字段集
    不含 hp_instant,误走 = 静默零发放);hp 无结转语义(xp_apply_amount
    系 XP 特有),+N 直加。**不 clip(上下界同此)**:sim 扣血绝对值制
    零上限消费(hp_max 字段缺位,缺口申报单一源 = fields.md HP 面行),
    clip 属无消费端语义,>100 可达 = 既有边界申报;负值支(先亏后盈
    −20 首例)同判——hp 可写 ≤0(选卡写经 observe 直落,floor/dead
    只存在于战斗结算域 apply_hp_outcome,后续败局按其现值分支判定),
    下界无消费端语义镜像上界裁决。写入经 observe;None 防御支沿
    :func:`cw_sim_battle.apply_hp_outcome` 未观察零写形态(sim 局开局
    恒种,纯形态对齐);evidence 按 ``hp:strategy_pick:<卡名>`` 与开局
    ``opening``/战斗 ``battle:hp`` 笔分账可归因,sig 同组(同域字段同
    组,笔间靠 evidence 区分)。

    负值支新增插入位置(损血档位触发族第二个插入位置):hp 写后同拍调
    :func:`cw_gain_chain.check_strategy_hp_loss_grants`,负 delta 取正
    损失量入累计器(**非减负**——累计器单调增取模发放,「−20」换算
    +20 损失计入),持保险局选卡损血同拍触发档位;logic_sig 与结算效果条目
    同组,rng = 调用方显式传流键(装备采样专用,禁缺省回退自掷——
    出售发牌效果条目同款纪律),触发函数零二次守卫防重 = 本效果条目呈现一次性标志位(标志位消费
    先于发放判定,重放零触发)。
    返回本批实际入账笔数(调用方轨迹追加按写行粒度对齐,一笔一追加;
    插入位置写入面 = 累计器/金/装备,不产 hp 写行,零扰轨迹同构)。"""
    applied = 0
    for name in picked:
        canon = normalize_invest_name(str(name or ''))
        eff = STRATEGY_ECONOMY.get(canon)
        amount = eff.hp_instant if eff is not None else 0
        if amount == 0:
            continue
        hp_now = gs.hp.value
        if hp_now is None:
            continue
        gs.observe(gs.hp, int(hp_now) + amount,
                   evidence=sim_evidence(f'hp:strategy_pick:{canon}'),
                   sig=obs_sig(group_id='sim:battle'))
        applied += 1
        if amount < 0:
            check_strategy_hp_loss_grants(gs, -amount,
                                          logic_sig=logic_sig('sim:strategy'),
                                          rng=rng)
    return applied


def apply_strategy_pick_streak(gs: GameState, picked: Sequence[str]) -> int:
    """策略选卡落地拍连胜置位入账(通用通道,辖域 = 注册表
    streak_set≠0 全体,字段分派非单卡特判)。

    为什么:sim 状态副本真值必须显式写——置位发生在选卡刻,到下一结算屏
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


#: 出售发牌效果条目判据集(派生,禁硬编码名单):板面重写族出售支中**卡文携带
#: 发牌效果条目**的卡——判据 = :data:`STRATEGY_EFFECTS` 过滤
#: ``payload.board_rewrite == BOARD_REWRITE_SELL_ALL_DEAL``。发牌效果条目是人力
#: 重组卡文附加面、非出售语义固有:素出售卡(大裁员/降本增效/现金为王,
#: 'sell_all' 值)无发牌面,不入列——不细分则素出售卡注册即自动入列,
#: sim 局将向无发牌卡注入假 2★(状态副本假单位污染)。按语义值细分后,后继
#: 具发牌效果条目卡以 _DEAL 值注册自动入列,素出售卡注册零扰动。
SELL_ALL_REWRITE_STRATEGIES: frozenset[str] = frozenset(
    name for name, spec in STRATEGY_EFFECTS.items()
    if str(getattr(getattr(spec, 'payload', None), 'board_rewrite', '')
           or '') == BOARD_REWRITE_SELL_ALL_DEAL)

#: 出售发牌三档序列 ``(费用, 数量)``:卡文语序费用降序 3→2→1(卡文:
#: 「获得1个随机的2星3费角色、2个2星2费角色和2个2星1费角色」;族级
#: 读法「表内对序 = 卡文语序,禁按费用隐式重排」——本卡卡文即降序)。
SELL_ALL_DEAL_TIERS: tuple[tuple[int, int], ...] = ((3, 1), (2, 2), (1, 2))


def apply_strategy_pick_sell_all_deal(gs: GameState, picked: Sequence[str],
                                      rng: random.Random) -> int:
    """策略选卡落地拍出售发牌效果条目(板面重写族出售支,通用通道,辖域 =
    :data:`SELL_ALL_REWRITE_STRATEGIES` 全体,判据分派非单卡特判)。

    为什么:sim 状态副本自持无观察,live 发牌面 = 游戏侧发放、下一备战帧
    观察覆盖收尾(板面重写桥「本桥禁替发牌面造单位」裁定,三处权威版本已登记
    零改动);sim 不发即持卡局 5 只 2★ 凭空缺失,合成素材池/held 派生/
    部署决策下游全链失真。本效果条目 = sim 状态副本真值直写,live 局不经过 sim
    后端,零假发牌。先卖后抽时序 = 插入位置天然保证:kernel 获得链(含桥
    出售面清空+退款)已在本效果条目执行前写完状态容器,held 归零 → 各档剩余池 =
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
    (蓝海效果条目同款纪律);三档共用同一实例按卡文语序推进(掷序契约:改序
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
                # 不改状态容器不炸链)
                log.warning(f'[cw-sim] 出售发牌分支空桶(注册表漂移?):'
                            f'cost={cost} card={canon}')
                continue
            for _ in range(count):
                gain_character(gs, rng.choice(bucket), 2, rand=True,
                               sig=logic_sig(group_id='sim:strategy'),
                               evidence='sim:board_rewrite_deal',
                               producer='SimBackend')
                dealt += 1
    return dealt


def apply_strategy_pick_gold_next_nodes_init(
        gs: GameState, picked: Sequence[str]) -> int:
    """策略选卡落地拍分期金剩余效果条数初始化(通用通道,辖域 = 注册表
    ``gold_next_nodes_count`` > 0 全体,字段分派非单卡特判)。

    为什么:「接下来 count 次进节点每次 amount 金」的递减状态必须在
    拿卡刻定格——节点窗效果条目(:func:`apply_invest_installment_gold`)按
    剩余效果条数发放,无初始化写点则递减状态容器字段永空 = 持卡局分期段整段静默
    零发。数额 = 注册值 ``gold_next_nodes_count`` 直读(键 = 卡规范名
    每卡独立条目,双持姊妹卡各键并存各窗各付各额,禁聚合槽);直接
    赋值 = 同卡重拿重置语义(现役 ``excluded_invest`` 采样排除闸下
    同卡重拿不可达,重置 = 防御性默认,族申报「重派逐次授予、现役
    不设防」同向)。live 零写:live 分期发放由游戏自算自显,金整字段
    观察覆盖收尾,假计数入状态容器无纠偏通道故禁。evidence
    ``strategy:gold_next_nodes_init:<卡名>``。返回初始化条数。
    """
    applied = 0
    for name in picked:
        canon = normalize_invest_name(str(name or ''))
        eff = STRATEGY_ECONOMY.get(canon)
        count = eff.gold_next_nodes_count if eff is not None else 0
        if count <= 0:
            continue
        merged = dict(gs.strategy_gold_next_nodes_left.value or {})
        merged[canon] = int(count)
        gs.write_logic(gs.strategy_gold_next_nodes_left, merged,
                       produced_by='SimBackend',
                       evidence=f'strategy:gold_next_nodes_init:{canon}',
                       sig=logic_sig('sim:strategy'))
        applied += 1
    return applied


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
    """整店发牌并写状态容器商店载荷(obs 渠道;节点切换自动全刷写点)。

    发牌算法本体 = kernel ``cw_shop_deal.sample_shop_deal``(两执行面
    同源单一实现;sim 侧采样即状态副本里的值)。名集空 → 槽留空(定长 5 槽
    三态模型的 empty 槽)。专家顾问入池 = 状态容器 ``gs.unlocked_experts``
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
assert JOINT_DECISION_EXTRA_SLOT is not None, '联席决策登记缺插入位置(数量通道事实残缺)'

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

#: 拿卡拍立即 offer 呈现留证披露键(值 = 触发卡@frame;对账面 = 实机局
#: 拿卡后第二选卡屏出现时点)。与到期效果条目呈现留证键分立,流标签判别面 =
#: 拿卡拍 ``M11/offer-extra/pick/...`` vs 窗首 ``M11/offer-extra/...``
#(两个插入位置分键,防族批部署态同键跨插入位置统计耦合)。
STRATEGY_IMMEDIATE_OFFER_FIRED: str = 'strategy_immediate_offer_fired'

#: 策略延时 offer 顺延留证披露键(值 = 原因 scheduled_slot_occupied/
#: window_cap + 悬置余量):同窗固定日程/联席槽在场,或本窗已呈现一次
#: 时,到点条目悬置顺延下一窗(到点判定「到了及以后都算」天然承载,
#: 不悬空不丢失)。白银投资延时效果条目入队后冲突交集非空:联席路径拿卡
#(2,6)→ 3 后继窗 = (3,2) 撞固定日程槽 = scheduled_slot_occupied 顺延
#: (3,3)——自然可达冲突首例,披露键由守卫转真值留证,实机对账见此键
#: = 核算吻合预期非异常。
STRATEGY_DELAYED_OFFER_DEFERRED: str = 'strategy_delayed_offer_deferred'

#: 策略延时发放到点留证披露键(值 = 触发卡@frame:发放物;对账面 =
#: 实机局发放物入栏时点;「N个节点后」计数起点读法的证伪路径 = 同值
#: 与实机帧 ±1 对照)。
STRATEGY_DELAYED_GRANT_FIRED: str = 'strategy_delayed_grant_fired'


def offer_slots(plane: int, round_num: int,
                active_env: str | None) -> bool:
    """该 (plane, round_num) 是否存在策略 offer 槽。

    固定日程(U07①)∨ 联席决策额外槽(id122 挂 2-6;环境按状态容器
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
    默认掷点。改写命中次(时代族/头彩/尾彩(settled 已定案)环境 = 三槽
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
    - 部分改写型经 ``rewrite_settled`` 定案后同判据接入——头彩已经用户
      裁定 2026-10-16 已定案 = offer 级覆盖面(第 1 次取卡机会 3 张候选全
      目标品质),尾彩同裁定 = 第 3 次;未定案部分型必填 pending_notes
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
#: 权威版本 = live 结算行归一 cw_screen_battle_wait._normalize_node_type,
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

#: 晶矿面板单例基准点(U23:实测 1-8 清关样本 1 大金晶矿+5 蓝晶矿+2 灰晶矿)。
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
#: 面板矿增量 = 用户占位确定 2026-10-15,非核实游戏事实,待实机采证
#: 校准)。值串 = 纯声明串不携数值:携值即与注册表双源,量级单一源 =
#: kernel :data:`ENV_ORE_PANEL_BONUS`。不进 kernel ORE_ASSUMPTION_KEYS
#: 汇总 tuple——该 tuple 辖 sphere 内容分布假设且现无发射接入调用,本键
#: 沿 :data:`ORE_PLANE_START_PENDING` 先例住本模块、接入
#: :data:`_BASE_DISCLOSURES`、测试直断发射(设计 designs/T-20-
#: jingji-yanzhong-guore.md §6.1)。
PIGGY_ORE_PANEL_BONUS_PLACEHOLDER: str = 'piggy_ore_panel_bonus_placeholder'

#: 商店 2★ 直出概率占位披露键(人才下沉 id 121:「商店中有概率出现2星
#: 角色」desc 无数值,sim 发牌翻星概率 = 用户占位确定 2026-10-16,非
#: desc 真值,待实机采证校准)。值串 = 纯声明串不携数值:携值即与注册
#: 表双源,量级单一源 = kernel :data:`ENV_SHOP_TWO_STAR_DEAL_PROB`(翻
#: 星分支 = kernel/cw_shop_deal,sim/live 两执行面共用)。沿
#: :data:`PIGGY_ORE_PANEL_BONUS_PLACEHOLDER` 先例住本模块、接入
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
    自动跟随);idx 重建 = 呈现集 0 基位次——三消费方同域起决定作用(策略器
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
    状态容器 ``active_env``;非奖励节点恒 False)。"""
    return (str(node_kind_of(gs) or '') == 'reward'
            and str(gs.active_env.value or '') in PIGGY_ENV_NAMES)


def reward_ore_points() -> tuple[tuple[str, int, int, int], ...]:
    """晶矿面板点集(U23 单例基准点展开;晶矿序 = 色档序内先大后小)。

    [索引定义] 元素 = ``(色档, x, y, r)``(OreSight.points 元素同形);
    (x, y) = sim 状态副本合成坐标,无画面语义,仅作晶矿身份键(点晶矿
    上报按坐标求交,状态容器 spheres 点集即真值)。内容不再由本面板携带
    ——spheres 写经挂接入口 ``cw_ore_channel.report_spheres_observed``
    生成附着(声明金先占席、其余逐矿采样,sim 采样即状态副本里的值),点击
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
    """奖励面板点集 = 基准 8 矿 + 扑满环境占位增量扩尾(奖励节点装配
    单点消费;纯函数,零采样零簿记)。

    [索引定义] 元素 = ``(色档, x, y, r)``,与 :func:`reward_ore_points`
    同形同坐标系(x/y = sim 状态副本合成坐标,身份键无画面语义)。增量矿
    查表 :data:`ENV_ORE_PANEL_BONUS`(量级单一源;表外环境零增量),
    色档 = '灰'(占位呈现身份:色档无内容语义,实采校准时连色带数
    一起校,披露键 :data:`PIGGY_ORE_PANEL_BONUS_PLACEHOLDER`)。

    **坐标续接面板序,禁独立从 1 起号**:增量点 x 自基准点序顺延
    ((基准点数+序)*10),与基准矿同列延伸——同批 spheres 写按 (x, y)
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
#: 建模选择非实采——卡面「激活…时」的边沿细节未定案,「电平 + 每档
#: 一次性 done 封账」为用户裁定建模口径;语义单一源 = kernel/
#: cw_faction_callbacks.check_env_bond_tier_grants docstring。纯声明,
#: 不进任何判定分支)。
DISCLOSURE_BOND_TIER_SEMANTICS: str = 'env_bond_tier_semantics_level'

#: 策略 boss 金通道披露键(特战资金系;纯声明,不进任何判定分支)。
#: 载义:①sim 侧策略 boss 金效果条目 = 「调用方聚合单列」过渡形态
#(:meth:`strategy_boss_gold_of` + 节点窗收尾独立观察笔),承载方式随
#: T1b 定夺迁移(round_start_income docstring 预留两承载方式,选分量
#: 扩参则本效果条目合并进收入签名);②轮首收入口径常量(BASE_INCOME/
#: LOSS_GOLD_BY_NODE/REWARD_BASE_GOLD_BY_ROUND,按实机逐轮金轨迹
#: 整定)的校准样本域与本效果条目的叠加交互未实证(校准局是否含持卡局
#: 不可考)——首次实机持卡局金轨迹对照时核,异常表现 = 持卡局金轨迹
#: 系统性偏离。
DISCLOSURE_STRATEGY_BOSS_GOLD: str = 'strategy_boss_gold_sim_channel'

#: 策略选卡即时效果条目披露键(纯声明,不进任何判定分支)。载义:①策略选卡
#: 「选牌当场即时型」把结果写进状态副本的实现分支现值 = xp_instant 已建(辖域 = 注册表字段>0
#: 全体,字段分派非单卡特判)/ hp_instant 已建含负成员(正加负损双向,
#: 辖域 = 字段≠0 全体;负值 = 损失直加不 clip,先亏后盈 −20 为首例,
#: 负 delta 同拍入损血档位累计器非「减负」)/ 真即时金 instant_gold
#: 未建(族批另议)——三形状均已登记申报,防「通道存在 = 族全覆盖」误读;
#: ②效果条目数额 = 单卡直读注册表现值,条目修订效果条目值随单一源自动跟随,无卡别
#: 硬编码。
DISCLOSURE_STRATEGY_PICK_INSTANT: str = 'strategy_pick_instant_legs'

#: 免战跳过辖域假设披露键(免战牌;纯声明,不进任何判定分支):跳过辖域
#: = :data:`CW_SKIP_NODE_KINDS`(仅普通战斗)系卡词汇类型读法假设,
#: 实机按钮出现面(遭遇/首领/奖励备战帧是否同样替换为跳过)校准插入位置;
#: 失配可观测路径 = live 跳过声明(battle_skip)到达而本辖域不含该节点
#: 类型 → 分派落空响亮(ValueError 守卫族)或对账漂移告警。发射点 =
#: 跳过消费拍(假设兑现时点)。
CW_SKIP_SCOPE_BATTLE_ONLY_ASSUMPTION: str = 'cw_skip_scope_battle_only_assumption'

#: 免战跳过结算语义暂定披露键(免战牌;纯声明,不进任何判定分支):
#: 跳过结算语义族(hp/streak/收入不动 + 被跳节点经验照常入账 + 直进
#: 下一节点窗)= live 暂定表述(fields.md §4.2「跳过=无结算帧」结构性
#: 事实 + action-logic-state.md §5/§7 比对计划行)的建模化,实机局
#: 跳过前后字段比对批为消费方;证伪即改 :meth:`SimBackend._skip_battle`
#: 对应支。发射点 = 跳过消费拍。
CW_SKIP_SETTLEMENT_SEMANTICS_PENDING: str = 'cw_skip_settlement_semantics_pending'

#: 策略尾款金·基准点辖域假设披露键(尾款交付;纯声明,不进任何判定分支)。
#: 载义:①「最后一个补给阶段」按**全局一次**建模(基准 = 展平全序列最末
#: supply 位,单一源 = ``cw_node_schedule.final_supply_pos``;措辞依据 =
#: 卡文「最后一个」全局限定词,证伪路径 = 实机持卡局非基准 supply 节点窗
#: 金轨迹 +30 即证伪为每位面各一次,改判定 = helper 换位面域扫描);②
#: 修饰局基准位随场字段现值(继承 T-8 披露的场字段缺位回退默认表链路——
#: 本卡 live 零写金,该链路零行为影响)。
DISCLOSURE_FINAL_SUPPLY_GOLD_SCOPE: str = 'final_supply_gold_scope_assumption'

#: 策略尾款金·「后」字时点精度披露键(尾款交付;纯声明,不进任何判定
#: 分支)。载义:①「进入…后」按节点进窗拍建模(与特战资金「时」字同
#: 拍假设;若实机证伪为补给确认拍,live 观察覆盖兜底行为面无差,sim 发
#: 放时点差一个窗内位置);②拿卡当节点不发放(选卡确认恒晚于窗口前段
#: 聚合读,基准点错过即无——「尾款」语义自洽)。
DISCLOSURE_FINAL_SUPPLY_GOLD_TIMING: str = 'final_supply_gold_timing_assumption'

#: 策略卡到级条件·触发语义披露键(成长基金金效果条目 + 钻石商人装备效果条目两条效果条目
#: 共用;纯声明,不进任何判定分支)。载义:「拿卡时已 ≥ 目标级也发放」
#: 状态检查型语义未经实机采证(等级 = 状态容器现值非事件流,拿卡时点无从
#: 回溯历史跨越,策略条件效果条目状态容器现值求值同款;若实机证伪为严格跨越事件
#: 型,两检查函数同批改读升级事件标记并随批退役本键)。
DISCLOSURE_STRATEGY_LEVEL_SEMANTICS: str = 'strategy_level_grant_state_semantics'

#: 策略卡到级条件·sim 休眠披露键(成长基金金效果条目 + 钻石商人装备效果条目两条效果条目
#: 共用;纯声明,不进任何判定分支)。载义:现役 sim 经验写源(节点经验
#: 表 × 选卡即时效果条目)下全程等级上界低于 3→9 级累计门槛 194,到级两条效果条目
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
    # 策略选卡即时效果条目申报(载义见键常量注:xp/hp_instant 效果条目已建与真即时金
    # 未建三形状已登记)
    DISCLOSURE_STRATEGY_PICK_INSTANT: 'xp_hp_instant_legs_built_pick_gold_instant_pending',
    # 策略尾款金两键(尾款交付;载义见键常量注:基准点辖域全局一次假设 +
    # 「后」字时点进窗拍假设)
    DISCLOSURE_FINAL_SUPPLY_GOLD_SCOPE: 'final_supply_global_once_seq_pos_anchor',
    DISCLOSURE_FINAL_SUPPLY_GOLD_TIMING: 'node_window_entry_beat_pick_miss_is_gone',
    # 策略卡到级金两键(成长基金;载义见键常量注:状态检查型语义未经
    # 实机采证 + 现役经验常量下 9 级不可达到级效果条目休眠)
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
    SCREEN_MEGASTAR, SCREEN_PLANNER, SCREEN_SHOP, SCREEN_PLANE_INTEL,
})

#: sim 不可呈现浮层的「在场识别标志」(画面档 → 识别标志 area 集;3.4 联调 visible
#: area 级细化)。这些识别标志门控同屏上的分支分派(如备战帧的阿哈装备选择
#: 浮层检测):画面档匹配语义会把它们误答真 → 备战帧被浮层分支抢走。
#: sim 不建模该浮层 → 识别标志恒不可见 = 状态副本里的值(呈现态查询语义)。
_UNPRESENTED_OVERLAY_ANCHORS: dict[str, frozenset[str]] = {
    SCREEN_PREP: frozenset({'标识-简易装备'}),
}


@dataclass(frozen=True)
class SimRunResult:
    """局结果面(消费方 = 运行器断言;纯结果无评判;
    位面/轮次读状态容器节点键)。"""

    final_hp: int
    plane_reached: int
    rounds: tuple[int, int]
    hp_trail: tuple[int, ...]
    unmodeled: dict[str, object]


@dataclass(frozen=True)
class PlaneIntelPresentation:
    """位面详情屏呈现面快照(:meth:`SimBackend.plane_intel_view` 产物;
    纯查询非观察——零状态容器写,采集真值落账仍走 op 上报节点经
    ``report_screen_plane_intel_obs`` 写门)。

    字段形状与实机 CV 读链逐点同形(消费方 = CwScreenPlaneIntel 的
    sim 改道读点,逐字段映射):``selected_plane`` ↔ 文本-节点编号 OCR
    位面段;``node_slots`` ↔ ``read_plane_detail_nodes``;``enemy_affixes``
    ↔ ``read_detail_affixes``;``node_type_label`` ↔
    ``read_detail_node_type_label``(boss 节点点击后呈现,否则 None);
    ``boss_name`` ↔ 大图标 SIFT 命中;``difficulty`` = sim 未建模恒
    None(实机该读数本就 best-effort 缺位容忍,语义同形)。
    """

    selected_plane: int
    node_slots: list
    enemy_affixes: list[str]
    node_type_label: str | None
    boss_name: str | None
    difficulty: int | None


# ============================================================ 声明驱动推进
# (动作后果声明 WorldDecl 的 advance 分派;设计件 = 动作后果声明化迭代
#  总纲 design.md §2.2 契约 5 + 详设 details/world-decl.md §3。转移事件
#  分派已停用:单动作单轨,advance 只承载已迁移动作的
#  trigger,同一动作任一时刻只有一条驱动路径。)

#: advance 分派表键集(``trigger`` 封闭集代码单一源;权威表 = 详设
#: world-decl.md §3,值零新词沿用现役动作名)。``''`` = 纯画面转移,
#: 恒合法(backend 只按 ``next_screen`` 推进,零专属过程);3.3 起 9 类
#: 过程 + 纯转移全量收齐,18 转移动作声明驱动全覆盖;2026-10-17 迭代
#: T-3 增 ``spy_shop_refresh``(商业间谍升级值变更回调状态副本侧分支:上报
#: 声明触发 + advance 尾统一排空段消费,非转移动作——next_screen 恒
#: 备战档,零画面转移);2026-10-19 用户
#: 裁定批增 ``refresh_invest_env``/``refresh_invest_strategy``(投资
#: 两屏刷新状态副本侧分支,上报声明触发,同屏重呈现零转移);2026-10-29 流程
#: 模型对齐批:``pick_encounter`` 自 ``battle_resolve`` 拆出(遭遇选完
#: 回备战并自动弹店,遭遇战改由出战触发——旧「选档落地即结算」随呈现
#: 改造废止;``battle_resolve`` 现役唯一来源 = 出战声明);免战牌建模批
#: 增 ``battle_skip``(免战跳过声明,来源 = 出战上报跳过子态分支,
#: kernel ``_SKIP_DECL_TRIGGER`` 同批)。
ADVANCE_TRIGGER_KINDS: frozenset[str] = frozenset({
    '', 'node_advance', 'battle_resolve', 'battle_skip', 'open_box',
    'pick_box_card', 'pick_megastar', 'pick_planner', 'pick_supply',
    'pick_invest_env', 'pick_invest_strategy', 'spy_shop_refresh',
    'pick_encounter', 'refresh_invest_env', 'refresh_invest_strategy',
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
    """sim 游戏后端(一实例一局;端口协议实现 + 画面状态机 + 状态规则件)。

    构造即 reset(开局序列:词缀/boss 名单采样并写状态容器 → 简报屏 →
    (env_present)投资环境屏 → wait_one_one → P1r1 对应屏);运行面 =
    端口六口 + kernel 事实事件 sink 订阅,状态副本推进全部由流程驱动
    (动作分支 = op → 上报函数族,本后端零私有动作语义)。
    """

    #: 局级输入(确定性基准;词缀入 seed 后此字段语义 = override 见下)。
    seed: int
    cfg: RunConfig
    #: 状态容器(组合,唯一一份)。
    gs: GameState = field(init=False)
    # —— 画面状态机(私有;状态 = 档名 + 子态) ——
    _screen: str = field(init=False, default='')
    _sub: str = field(init=False, default='')
    #: 上次广播画面值(:meth:`_announce_screen` prev_screen 行来源;初值 =
    #: 状态容器 prev_screen 每局全新创建空串。值级豁免点(SETTLE/LOBBY)不经过本字段
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
    #: 刷新语义,保守不呈现,随实机首遇或裁定收尾);_offer_forced_slots =
    #: 本窗口品质改写槽位向量(空元组 = 无改写;刷新重掷沿用同向量 =
    #: 槽位品质承诺跨刷新保持,卡面语义直读);_offer_refresh_seq = 本
    #: 窗口刷新流水号(rng 流键分量,呈现时点归零)。观察真值(计数/候选)
    #: 一律走状态容器(report 观察写端),本组只承载「呈现授权」簿记。
    _offer_refreshable: bool = field(init=False, default=False)
    _offer_forced_slots: tuple[str, ...] = field(init=False, default=())
    _offer_refresh_seq: int = field(init=False, default=0)
    #: 获得时点随机策略发放已掷源名集合(远见效果条目②一次性门;记名集合非单
    #: 布尔 = 多张 grant 卡各自身 exactly-once,且两个插入位置共用同一门)。
    #: 消费面 = :meth:`_fire_strategy_random_grants`(拾取落地拍 + 环境
    #: 直发分支两个插入位置);exactly-once 由集合记名构造保证(源卡按名字去重
    #: 只入列一次,获得一次 → 恰发一次);零假发由 membership 判定保证
    #(呈现未选 → 不入列 → 零发放)。私有暂态不入状态容器/不入快照恢复
    #: (一次性标志位族同形先例);resume 安全 = sim 全局重放模型(RunConfig 无
    #: active_strategies 输入面,源卡已登记 ⇒ 其获得拍已在本后端跑内
    #: 重放,集合在该拍置位)。
    _strategy_grant_fired: set[str] = field(init=False, default_factory=set)
    #: 商店牌面节点级记录(牌面 = 节点级持久事实,发牌时定;2026-10-17
    #: 用户裁定):值 = 商店在屏期间 ``gs.shop`` 的最后非空观测(跟随
    #: 发牌/刷新/买卡一切写点,驱动入口懒同步
    #: :meth:`_sync_shop_record`);开店呈现写回消费(:meth:`_open_shop`,
    #: 对偶实机「每次进店读屏」)。关店清 ``gs.shop`` 呈现不清本记录;
    #: 节点窗起新发牌自然覆盖(整店锁跳过发牌 = 牌面跨节点保留,同语义)。
    _shop_record: ShopPayload | None = field(init=False, default=None)
    # (私有 overlay 队列与评估器簿记三件[队列/一次性标志/银狼星基线/
    #  巨星水位]已停用:sim 呈现数据源 =
    #  状态容器登记 gs.screen_changes.pending,判据簿记 = ScreenChanges
    #  sidecar,呈现检查 = 问询时点[screen_identity] + advance 尾。)
    #: 武装箱待授予候选下标(装备卡点击源记录;pick_box_card 落地消费)。
    _box_pick_pending: int | None = field(init=False, default=None)
    #: 策略选卡即时经验效果条目呈现一次性标志位(offer 呈现置 True、落地拍消费置 None;
    #: 无一次性标志位的重复 advance = 零写防重放)。私有暂态不入状态容器/不入快照恢复
    #: (:data:`_box_pick_pending` 同形先例)。
    _strategy_pick_xp_latch: bool | None = field(init=False, default=None)
    #: 策略选卡连胜置位效果条目呈现一次性标志位(与 xp 标志位同点置位同拍消费,独立不共享:
    #: 两条效果条目语义独立,共享一次性标志位会让单条效果条目测试直读互相牵连且无状态量收益)。
    #: 防重放实害 = 置位后战斗推进再重放会把已转移真值回写成置位值。
    #: 私有暂态不入状态容器/不入快照恢复(同形先例同上)。
    _strategy_pick_streak_latch: bool | None = field(init=False, default=None)
    #: 策略选卡出售发牌效果条目呈现一次性标志位(板面重写族出售支;与 xp/streak 标志位同点
    #: 置位同拍消费,独立不共享——三条效果条目语义独立,共享一次性标志位会让单条效果条目测试直读
    #: 互相牵连且无状态量收益)。防重放实害 = 无一次性标志位的重放 advance 会把
    #: 5 只 2★ 二次发放(发放非幂等,与置位效果条目同害级)。私有暂态不入
    #: 状态容器/不入快照恢复(同形先例同上)。
    _strategy_pick_sell_deal_latch: bool | None = field(init=False,
                                                        default=None)
    #: 策略选卡即时生命效果条目呈现一次性标志位(hp 通道;与 xp/streak/sell-deal 标志位同点
    #: 置位同拍消费,独立不共享——四条效果条目语义独立,共享一次性标志位会让单条效果条目测试直读
    #: 互相牵连且无状态量收益)。防重放实害 = 无一次性标志位的重放 advance 会把
    #: +N hp 二次发放(直加非幂等,与置位/发牌效果条目同害级)。私有暂态不入
    #: 状态容器/不入快照恢复(同形先例同上)。
    _strategy_pick_hp_latch: bool | None = field(init=False, default=None)
    #: 策略选卡分期金初始化效果条目呈现一次性标志位(gold-next-nodes 通道;与 xp/streak/
    #: sell-deal/hp 标志位同点置位同拍消费,独立不共享——五条效果条目语义独立,共享
    #: 一次性标志位会让单条效果条目测试直读互相牵连且无状态量收益)。防重放实害 = 无一次性标志位的
    #: 重放 advance 会把已递减的剩余效果条数重置回初值(窗效果条目已消费的期数
    #: 凭空回补,分期多发)。私有暂态不入状态容器/不入快照恢复(同形先例
    #: 同上)。
    _strategy_pick_gold_next_nodes_latch: bool | None = field(
        init=False, default=None)
    #: 策略选卡位面段补发效果条目呈现一次性标志位(xp_per_plane 通道;与前置五个一次性标志位同点置位
    #: 同拍消费,独立不共享——六条效果条目语义独立,共享一次性标志位会让单条效果条目测试直读互相
    #: 牵连且无状态量收益)。防重放实害 = 无一次性标志位的重放 advance 会把 +4 XP
    #: 二次发放(直加非幂等)。私有暂态不入状态容器/不入快照恢复(同形先例
    #: 同上)。
    _strategy_pick_plane_refire_latch: bool | None = field(init=False,
                                                           default=None)
    #: 策略选卡超发货币负债效果条目呈现一次性标志位(与前置六个一次性标志位同点置位同拍消费,独立
    #: 不共享——七条效果条目语义独立,共享一次性标志位会让单条效果条目测试直读互相牵连且无状态量
    #: 收益)。防重放实害 = 窗内重放会把金清零笔二次申报(负债清零本身
    #: −0 幂等,但金已为 0 短路下重放连证据笔都不应再出——一次性标志位使重放零
    #: 动作零噪声)。私有暂态不入状态容器/不入快照恢复(同形先例同上)。
    _strategy_pick_hyperemit_drain_latch: bool | None = field(
        init=False, default=None)
    #: 策略选卡大扩招扣金负效果条目呈现一次性标志位(与前置七个一次性标志位同点置位同拍消费,独立
    #: 不共享——八条效果条目语义独立,共享一次性标志位会让单条效果条目测试直读互相牵连且无状态量
    #: 收益)。防重放实害 = 窗内重放会把扣金二次申报(扣金非幂等,重放
    #: 多扣一笔金)。私有暂态不入状态容器/不入快照恢复(同形先例同上)。
    _strategy_pick_recruit_drain_latch: bool | None = field(
        init=False, default=None)
    #: 策略选卡宝钻状态副本联动效果条目呈现一次性标志位(与前置八个一次性标志位同点置位同拍消费,独立
    #: 不共享——九条效果条目语义独立,共享一次性标志位会让单条效果条目测试直读互相牵连且无状态量
    #: 收益)。防重放实害 = 宝钻回调三写非幂等(diamond_count +1 /
    #: back_layout +1,窗内重放会伪 +1)。私有暂态不入状态容器/不入快照恢复
    #: (同形先例同上)。
    _strategy_pick_diamond_latch: bool | None = field(init=False, default=None)
    #: 策略选卡已损血衍生金效果条目呈现一次性标志位(星际和平保险 id 303001 首例;与前置
    #: 九个一次性标志位同点置位同拍消费,独立不共享——十条效果条目语义独立,共享一次性标志位会让单条效果条目
    #: 测试直读互相牵连且无状态量收益)。防重放实害 = 衍生金非幂等,窗内
    #: 重放会把金笔二次申报(多加一笔金)。私有暂态不入状态容器/不入快照恢复
    #: (同形先例同上)。
    _strategy_pick_hp_loss_gold_latch: bool | None = field(init=False,
                                                           default=None)
    #: 策略选卡获得链交换效果条目呈现一次性标志位(不等价交换 hp⇄gold 互换轨迹成对;
    #: 与前置十个一次性标志位同点置位同拍消费,独立不共享——十一条效果条目语义独立,共享一次性标志位
    #: 会让单条效果条目测试直读互相牵连且无状态量收益)。防重放实害 = kernel 交
    #: 换写行恰一而轨迹追加非幂等,窗内重放会凭空多配一行破写流↔轨迹
    #: 全序同构。私有暂态不入状态容器/不入快照恢复(同形先例同上)。
    _strategy_pick_swap_latch: bool | None = field(init=False, default=None)
    #: 超发货币回流效果条目挂起额(前读快照跨窗承载:remaining==1 的窗口快照,
    #: 下一入口 = 第 6 次入口开窗先付;一次性消费,None = 无挂起)。
    #: 私有暂态不入状态容器/不入快照恢复(呈现一次性标志位同形);机制根因与单载体
    #: 声明见 :meth:`_enter_node_window` 回流效果条目注释。
    _hyperemit_payoff_pending: tuple[str, int] | None = field(
        init=False, default=None)
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
    #: 窗口起点持有策略快照(选卡拍改写/补发双效果条目的「本拍新获得」限定
    #: 判据):记录时刻 = 节点窗幂等守卫同拍(重放不重拍),消费 =
    #: _on_invest_picked 尾段取差分后**前滚并入现值**(链式选卡同窗二次
    #: 落地时差分 = 本拍新获得,旧卡不重燃;重放落地差分恒空 = 零写)。
    #: 私有暂态不入状态容器/不入快照恢复(呈现一次性标志位同形先例)。
    _strategies_at_window_start: tuple[str, ...] = field(init=False,
                                                         default=())
    #: 扑满节点递延收入快照(None = 非扑满窗或已落账):统一公式
    #: 「战败时无连胜成分」需胜负,窗口开时未知 → 基数冻结(金/进轮
    #: 连胜/收入修饰/开源节流息顶满下限 = 轮初口径;floor 评估时点 =
    #: tick 捕获 = 进节点时点,结算刻重评估会读扑满节点自身花费禁),
    #: 结算分支胜负后落账并清回 None。
    _strategy_reward_ore_pending: int = 0
    """窗内待呈现晶矿数(买断制块后条件发放效果条目写入,_present_node_screen
    消费;窗内幂等不置零,设计稿 r1-O2 修后写法)。"""
    _piggy_income_snap: (tuple[int, int, tuple[float, int, int | None], int]
                         | None) = field(init=False, default=None)
    #: 对账延后声明队列(豁免场景内 next_screen 等值断言延后至稳态,
    #: :meth:`_reconcile_next_screen`;元素 = (延后时点已进窗节点序位,声明),
    #: 每次 advance 入口消费)。
    _pending_reconcile: list[tuple[NodePos | None, WorldDecl]] = field(
        init=False, default_factory=list)
    #: 间谍抽牌流键执行序计数器(按节点位;键 = (位面,轮) 1 基,值 = 该
    #: 位已执行次数,取值时机 = 执行期现读先取后增)。坐标系 = 本后端
    #: 采样簿记私有(不入状态容器/不入快照恢复,呈现一次性标志位族同形先例)。
    _spy_stream_seq: dict[tuple[int, int], int] = field(
        init=False, default_factory=dict)
    #: 位面详情呈现态·选中位面卡(1 基;None = 详情屏未呈现)。坐标系 =
    #: 呈现态私有(不入状态容器/不入快照恢复,同形先例);写入端 = 详情屏
    #: 点击源(位面卡点击推进,开屏点击源置当前节点位面)。
    _pd_selected_plane: int | None = field(init=False, default=None)
    #: 位面详情呈现态·boss 节点已选中(详情条「首领」标签呈现判据;
    #: 切卡/关屏复位)。写入端 = 详情屏节点条点击源。
    _pd_boss_selected: bool = field(init=False, default=False)
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
        # 开局初始值(与实机局状态容器每局全新创建即种同契约:获得链/上报函数族的
        # 拒落档门以初始值在场为前提;seed 值 = 常量基线,apply_opening 随后
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
        # 初始序列:简报屏(词缀 + boss 载荷已写状态容器;env 屏在简报下一步
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
        sim 懒呈现位):答身份前先查状态容器登记 pending——动作上报内已
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
        ``report_screen_*`` 落状态容器(写通道铁律,单一源在 report 消费端)。
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
        底层屏区域不可见)。3.4 联调细化 = 不可呈现浮层的在场识别标志恒
        False(:data:`_UNPRESENTED_OVERLAY_ANCHORS`,呈现态查询语义)。
        免战牌按钮替换子态(免战牌建模批):备战/开商店两屏上持卡且
        余量 > 0 且节点在跳过辖域 → 出战按钮替换为跳过(与出战 op
        「查不到出战 fallback 查跳过」的双屏查找同构;独立于静态排除表,
        后者零改动)。等待变体(wait_one_one)在问询时立即完成(sim
        状态副本瞬时呈现,动画无时间维)。

        跳过识别标志真值域边界:「按钮-跳过」在出辖域节点不走替换分支 → 落
        默认「不在排除表即 True」(呈现态查询语义),与实机真值(出辖域
        右下恒出战)不符——消费面必须以「出战 miss」为前置条件再探跳过
        (现役唯一消费 = 出战 op 双查找序 + 备战两识别标志同帧命中时的第二识别标志 or 短路,均
        满足);禁把跳过识别标志单独当出战按钮在场判据。"""
        self._maybe_finish_wait()
        self._sync_shop_record()
        if screen_name != self._screen:
            return False
        if screen_name in (SCREEN_PREP, SCREEN_SHOP) \
                and area_name in ('按钮-出战', '按钮-跳过'):
            node = self.gs.node.value
            if node is not None and node.kind in CW_SKIP_NODE_KINDS:
                # battle 节点按钮对真值 = 子态开关:免战在场余量>0 →
                # 出战 False/跳过 True;用尽移除(entry 离场)→ 出战
                # True/跳过 False(设计 §4-5)。出辖域节点不走本分支 =
                # 现役语义维持(出战恒可见)。
                if area_name == '按钮-跳过':
                    return self._skip_card_active()
                return not self._skip_card_active()   # 按钮-出战
        return area_name not in _UNPRESENTED_OVERLAY_ANCHORS.get(
            screen_name, ())

    def _skip_card_active(self) -> bool:
        """免战牌跳过子态开关(免战牌 entry 在场且 ``remaining_uses > 0``);
        问询屏与节点辖域限定由调用方承担——按钮 area 单源归备战屏,
        开商店叠加帧同位(出战 op 双屏查找同构)。"""
        entry = self.gs.effects.first(STRATEGY_EFFECTS['免战牌'].id)
        return entry is not None and (entry.remaining_uses or 0) > 0

    # ------------------------------------------------------ 屏内子读点答口

    def node_sequence(self) -> list | None:
        """备战节点条读点答口(:func:`cw_sim_ports.sim_or_live_node_sequence`
        的 sim 答法;查询面零状态容器写)。

        当前呈现屏非备战 → None(实机语义 = 节点条只在备战帧可见,半开帧/
        其它画面读条 = None——守卫的「画面稳定判据」语义保持,词缀随机态
        ∧ 备战帧时本答口非 None = 封死分支在 sim 不可达,活锁闭环的对偶面)。

        备战帧 → 按状态副本合成 ``cw_node_reader.NodeSlot`` 行(合成细节 =
        :meth:`_synth_node_slots`):序列真值 = ``node_sequence_of(位面,
        场字段现值)``(策略改写后的场字段即权威,与节点窗呈现同口)。
        序列缺键 = None(可读性守卫语义:合不出 = 不可读,禁静默造行)。
        """
        if self._screen != SCREEN_PREP:
            return None
        plane, _r = self._node_pos()
        try:
            node_sequence_of(plane, self.gs.node_seq_by_plane.value)
        except PlaneSeqMissingError:
            return None
        return self._synth_node_slots(plane)

    def plane_intel_view(self) -> PlaneIntelPresentation:
        """位面详情屏呈现面答口(:func:`cw_sim_ports.sim_or_live_plane_intel_view`
        的 sim 答法;形状契约 = :class:`PlaneIntelPresentation`)。

        选中位面 = 状态机呈现态(位面卡点击源推进;None 防御面 = 1——
        开屏点击源置当前节点位面,正常调用序恒有值);节点条槽/词缀/boss
        名全自状态副本直出;详情条标签 = boss 节点已选中时「首领」(实机
        详情条随选中节点联动,识别管线只在点 boss 后读标签,前态无消费)。
        """
        plane = self._pd_selected_plane or 1
        bosses = self.gs.plane_bosses.value
        boss = None
        if bosses is not None and len(bosses) >= plane:
            boss = bosses[plane - 1]
        return PlaneIntelPresentation(
            selected_plane=plane,
            node_slots=self._synth_node_slots(plane),
            enemy_affixes=list(self.gs.enemy_affixes.value or []),
            node_type_label=('首领' if self._pd_boss_selected else None),
            boss_name=boss,
            difficulty=None,
        )

    def _synth_node_slots(self, plane: int) -> list:
        """位面节点条合成(备战行读点与详情条预览共用;形状与坐标约定见
        :meth:`node_sequence`)。state 按当前节点序位 past/current/upcoming
        (非当前位面 = 整条 upcoming——详情条预览其它位面无当前态着色,
        消费面只读 node_type 与槽序,标注零行为影响);当前槽 ``node_type``
        = 节点类型真值(实机由 OCR 标签覆盖,状态副本直出同值),未来槽 =
        序列真值(实机 Hu 模板匹配,状态副本直出),过去槽 None。cx/cy =
        下标派生合成值(合成坐标约定——sim 消费面禁读坐标:委派链 sim
        点击走区域点击源,不消费点位)。序列缺键 = 空表(调用方按不可读
        语义消费,禁静默造行)。"""
        try:
            seq = node_sequence_of(plane, self.gs.node_seq_by_plane.value)
        except PlaneSeqMissingError:
            return []
        cur_plane, r = self._node_pos()
        cur = r if plane == cur_plane else 0
        return [
            NodeSlot(idx=i, cx=(i + 1) * 10, cy=(i + 1) * 10,
                     state='past' if i < cur - 1
                     else ('current' if cur and i == cur - 1 else 'upcoming'),
                     node_type=(None if cur and i < cur - 1 else k),
                     hu_dist=None)
            for i, k in enumerate(seq)
        ]

    def _open_plane_intel(self) -> None:
        """位面详情开屏点击源(备战节点条点击 → 模态呈现;flow-seam 附录 B
        「推进型画面 op 点击 = click 源」同族)。

        选中位面初值 = 当前节点位面(与实机「进屏初始选中随接管时点变」
        同构——编排首拍恒点卡 1 重定选中,初值只影响点击前瞬间);非备战
        帧 = 建模外点击静默忽略(屏门已拒点,呈现态不翻)。
        """
        if self._screen != SCREEN_PREP:
            return
        self._pd_selected_plane = self._node_pos()[0]
        self._pd_boss_selected = False
        self._present_modal(SCREEN_PLANE_INTEL)

    def _close_plane_intel(self) -> None:
        """位面详情关屏点击源(X 点击 → 模态返回备战;呈现态复位)。"""
        self._pd_selected_plane = None
        self._pd_boss_selected = False
        self._dismiss_modal()


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
        elif screen_name == SCREEN_PREP and area_name == '区域-节点条':
            self._open_plane_intel()
        elif screen_name == SCREEN_PLANE_INTEL \
                and area_name.startswith('按钮-位面卡'):
            # 位面卡点击源(建档名「按钮-位面卡N」:前缀剥除后余文 = 位面号,
            # 1-3;切卡复位 boss 选中态,详情条随选中位面联动)。
            try:
                plane_no = int(area_name.removeprefix('按钮-位面卡'))
            except ValueError:
                return
            if self._screen == SCREEN_PLANE_INTEL and plane_no in (1, 2, 3):
                self._pd_selected_plane = plane_no
                self._pd_boss_selected = False
        elif screen_name == SCREEN_PLANE_INTEL and area_name == '区域-节点条':
            # boss 节点点击源(详情条标签「首领」呈现态置位;识别管线
            # 点 boss 后读标签验首领,先验 = 槽序最右)。
            if self._screen == SCREEN_PLANE_INTEL:
                self._pd_boss_selected = True
        elif screen_name == SCREEN_PLANE_INTEL \
                and area_name == '按钮-关闭位面详情':
            self._close_plane_intel()

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
                # 计数经 report 观察写端落 env_refresh_left,重掷状态副本侧分支
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

        刷价呈现写回(改价分支 sim 载体):每次开店以 kernel 渲染的状态副本
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
        """商业间谍升级连锁状态副本侧分支(2026-10-17-levelup-shop-transition
        design §2.3 步①-③;触发 = spy_shop_refresh 声明,来源双消费口 =
        买经验上报尾单项喂入 + advance 尾统一排空段逐项直调;步④置信号
        = kernel 升级值变更回调(任意经验来源升级),写端唯一,不经本层)。

        - ①抽 5 张:费用档按升级后等级概率表(单一源 =
          :func:`effective_deal_probs`,轮岗在场同款重掷);流键 =
          发牌口径 + 执行序后缀(M22/spy-deal#k|M22/spy-rotation#k,k =
          :attr:`_spy_stream_seq` 按节点位先取后增,同键同序列语义下
          同窗双执行不重牌;模块号沿 M21 续);发牌算法本体 = kernel
          ``sample_shop_deal`` 单一源,采样即状态副本里的值;
        - ②偷最贵 3 张 → 备战席真实入席(席满溢出 = 不入席 + 计数披露,
          design §2.3 申报的 sim 先行形态;最贵序 = 费用降序 → 星级降序
          → 槽位升序确定性破并列);入席 = 状态容器 bench 观察直写(sim 状态副本
          真值通道,与 deal_shop 写 shop 同款;不级联合成——design 未
          申报偷取合成语义,保守不猜);
        - ③剩余 2 张 = 商店新牌面:状态容器 shop 观察直写(被偷槽位置空,
          剩余槽位原位保留)+ 经 :meth:`_sync_shop_record` 入节点级记录
          → 下次开店呈现之(不重新发牌——刷新已在本回调发生)。

        计数披露(sim 私有簿记,键域:spy_deal_count / spy_steal_placed_
        count / spy_steal_overflow_count)= 抽牌次数 / 入席张数累计 /
        溢出张数累计;判读面计数键(cw4_counters.spy_steal_placed_frames /
        spy_steal_overflow_frames)= 帧级增量,经状态容器挂接的策略器状态
        鸭子类型读取(duck typing)回写(未挂接帧静默跳过 = 无判读面,合法)。持有判定不在
        本层(升级值变更回调调度器已闸;本层被声明即执行,声明构造点零
        副作用无持卡不构造)。"""
        from sr_od.application.currency_war.kernel.cw_game_state import (
            BenchSlot,
            BenchView,
            ShopSlot,
            Unit,
        )
        new_level = int(self.gs.level.value or 3)
        plane, r = self._node_pos()
        # 流键执行序后缀(同键同序列语义下双执行的唯一修法):结算排空
        # 接入后「窗开跨级排空抽牌 + 同窗后继买经验跨级抽牌」消费同一
        # (位面,轮) 流键会抽到完全相同的 5 张,实机两次独立刷新语义破;
        # 后端私有按节点位计数器,每次分支执行先取后增,k 从 0 起——
        # 键位移半径最小(仅同位第二次执行起变键),重放判据相容(首执行
        # = '#0',测试重放构造同式追加)。独立计数器非复用披露计数 =
        # 遥测计数与随机确定性解耦。
        seq = self._spy_stream_seq.get((plane, r), 0)
        self._spy_stream_seq[(plane, r)] = seq + 1
        rotation_on = (str(self.gs.active_env.value or '')
                       == ROTATION_ENV_NAME)
        deal_rng = stream_rng(self.seed, f'M22/spy-deal/p{plane}/r{r}#{seq}')
        probs = effective_deal_probs(
            new_level,
            stream_rng(self.seed, f'M22/spy-rotation/p{plane}/r{r}#{seq}'),
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
        # 步⑤信号代次戳刷新(T-434;kernel 唯一入口
        # refresh_shop_randomized_pending_stamp):分支执行 = 信号所指牌面
        # 的最终写,戳刷新为牌面所属节点窗的生效序位——免战跳过路径
        # (_skip_battle 经验入账在本地推进序位之前)置位戳滞后一节点,
        # 不刷新则该源信号下一备战帧被节点边界当过期代次清掉。信号未登记
        # = 零动作(声明直调形态,上报尾喂入与 advance 尾排空同过此处)。
        refresh_shop_randomized_pending_stamp(self.gs)

    # (事实事件订阅入口已停用删除:
    #  懒呈现位 = screen_identity 问询时点检查;板面真值观察 =
    #  advance 步界 _observe_board_truth。)

    # ------------------------------------------------------ 声明驱动推进

    def advance(self, decl: WorldDecl) -> None:
        """按声明推进状态副本(声明化主入口;动作后果声明化迭代总纲
        design.md §2.2 契约 5 + 详设 world-decl.md §3)。

        按 ``decl.trigger`` 分派推进(键集单一源 =
        :data:`ADVANCE_TRIGGER_KINDS`,集外值 ValueError 响亮——
        构造点漂移 = 调用点接错禁静默),完成后
        :meth:`_reconcile_next_screen` 等值对账画面档。状态副本推进唯一
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
                f'{sorted(ADVANCE_TRIGGER_KINDS)}(构造点漂移 = 接入调用 bug,'
                '禁静默)')
        if decl.trigger == 'node_advance':
            if decl.next_screen == '':
                # 局终声明消费分支(键表示切换批 design §2.6):kernel 终局
                # 事件式(sequence_next = None → applied=True match_end,
                # 声明 next_screen='')的状态副本侧消费;kernel 声明权威、sim
                # 对账的分工不变。
                self._on_node_advance_terminal()
            else:
                self._on_node_advance()
        elif decl.trigger == 'battle_resolve':
            self._resolve_battle()
        elif decl.trigger == 'battle_skip':
            if decl.next_screen == '':
                # 局终防御臂(声明构造面 _skip_next_screen 空串臂同源:
                # 后继 None/表外位面;默认辖域战斗节点非位面末,现规则集
                # 不可达):终局消费效果条目,对齐 node_advance 终局事件式形态。
                self._on_node_advance_terminal()
            else:
                self._skip_battle()
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
            # 商业间谍升级连锁状态副本侧分支(2026-10-17 迭代 design §2.3
            # 步①-③;声明来源 = 上报尾喂入或 advance 尾排空段,
            # 步④置信号 = kernel 升级值变更回调,不经本层)。
            self._apply_spy_shop_refresh()
        elif decl.trigger == 'refresh_invest_strategy':
            # 投资策略屏逐卡刷新状态副本侧分支(2026-10-19 用户裁定批;上报声明
            # 触发,同屏重呈现零转移)。
            self._refresh_invest_strategy(decl.slots)
        elif decl.trigger == 'refresh_invest_env':
            # 投资环境屏整组刷新状态副本侧分支(同上批;环境刷新 = 整组重掷一次)。
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
        # 升级连锁声明统一排空段(本 advance 的最终商店写,覆盖节点经验/
        # 窗口分支/选卡/首购等全部非买经验源跨级产生的 spy 声明)。
        self._drain_pending_levelup_decls()
        # overlay 呈现检查(3.4):**仅纯转移分支**——声明改底层屏后
        # open_bookcard/open_tome 的弹窗呈现入口(battle_resolve/
        # node_advance 等其余分派保留原呈现时机 = 各自过程内/节点窗
        # 起点检查,不在 advance 尾提前:overlay 让路序「窗起点 overlay
        # 先于 offer」是旧引擎收尾检查序的锁定语义)。
        if decl.trigger == '':
            self._present_pending_overlay()

    def _drain_pending_levelup_decls(self) -> None:
        """升级连锁声明统一排空段(advance 尾第三消费点;前两口 = 买经验
        上报尾读取 + 本段,取走即清)。

        队列非空则逐项直调 :meth:`_apply_spy_shop_refresh`(不走
        declare_world 再入 = 零状态机重入),单项失败上抛使后续项滞留 =
        下一 advance 重试(语义自洽,零内吞)。次序 = 本 advance 的最终
        商店写:间谍分支晚于 M05 全刷与位面强制店改写分支,被覆盖的中间
        牌面无观察者(模拟器不呈现中间态),玩家所见最终店面 = 间谍分支
        结果。锁交互:无整店锁守卫,沿位面强制店改写分支在卷先例(效果
        触发的商店写不入 M05 自动全刷的锁豁免域,真值待实采与间谍卡共享
        同一实采裁决)。重放安全 = 排空即清空不变式(重复 advance 到达时
        队列已空,零双消费)。done(局终)守卫跳过:终局升级不刷店,队列内
        声明随局终止不消费(与「局终无商店」语义自洽,零处理)。
        """
        if self.done:
            return
        while True:
            decl = take_levelup_world_decl(self.gs)
            if decl is None:
                return
            self._apply_spy_shop_refresh()

    def _reconcile_exempt_reason(self) -> str:
        """当前对账豁免场景(:data:`RECONCILE_EXEMPT_KINDS`;命中 =
        最上层呈现屏 ≠ 底层稳态画面属建模内合法形态,断言延后至稳态;
        ''= 稳态可判)。overlay_trigger 3.4:overlay_pending 检查改读状态容器
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
        场景 = 继续延后;**状态副本已推进过下一节点窗**(进窗序位 ≠ 延后
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
        :meth:`_drain_pending_reconciles` 补验。局终双载体:``done`` 状态副本
        呈现恒 = 大厅(:meth:`_game_over`,声明预测已失效只锁载体);
        ``next_screen=''`` 预测局终而状态副本未终局 = 漂移。断言不等且不在
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
        # —— 策略卡到级金效果条目(成长基金 id 101701 首例;条件单一源 =
        # kernel check_strategy_level_grants 纯决策零写):挂经验入账后 =
        # 跨级事件拍,先于新节点窗轮首收入(达标金计入本窗息算基数;
        # 实机跨级金与节点金口径对位未逐帧采证,若实机为「跨级金落上
        # 节点末口径」则本接入调用零偏差,否则一次性息差 ≤ min(40//10, 5)
        # = 4 金,证伪路径 = 实机局跨级前后两窗利息差分)。双通道:sim
        # 金写全 observe 现役形态(金面禁直写辖效果账本到期接入点,本笔
        # = 状态副本合成非 logic 直写),一次性标志位 = write_logic(非金 Field 登记事
        # 实直写,discharge_due_item_grants 先形);组名沿 sim:strategy
        #(策略战后发放效果条目首落在役组)。现役 sim 经验常量下 9 级不可达
        #(节点 70 + 选卡即时效果条目 64 = 上界 134 < 3→9 级门槛 194;即时效果条目
        # 键集显式扩集制,免战牌 +30 入注册面随批重申报)= 休眠
        # 正确路径恒短路零写,经验源扩网零改激活;幂等 = 决策函数 done
        # 一次性标志位短路 + 本层序位守卫双保险。
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
        # —— 策略卡到级装备效果条目(钻石商人;条件单一源 = kernel
        # check_strategy_level_equip_grants 直写形态:发放 + 落一次性标志位两笔均
        # 在 kernel 函数内,logic 渠道,组名沿 sim:strategy 在役组)。
        # 接入调用点 = 经验入账后、新节点窗前(宝钻的 deploy_cap +1/后排格数
        # 自本窗生效 = 状态副本真值序);返回非 None → 宝钻回调(入参只传
        # 装备名,sig 由回调内构 obs 族,深井发放路径同分工)。live 结算
        # 位同函数零回调。现役经验常量下 9 级不可达 = 休眠正确路径恒
        # 短路零写;幂等 = kernel 函数 done 一次性标志位短路 + 本层序位守卫双保险。
        _equip_grant = check_strategy_level_equip_grants(
            self.gs, logic_sig('sim:strategy'))
        if _equip_grant is not None:
            on_diamond_acquired(self.gs, _equip_grant)
        self._entered_pos = eff
        self._enter_node_window(eff)

    def _on_node_advance_terminal(self) -> None:
        """胜利终局声明消费分支(trigger=node_advance ∧ next_screen=''):
        kernel 终局事件式声明(推进超出序列表末位面,现役 = 位面 3 末
        boss 结算存活)的状态副本侧消费——XP 入账(被离开节点类型,与现行
        局终前入账同序)+ 胜局披露 + 终局。hp 归零败局走结算死亡分支
        (:meth:`_resolve_battle` → :meth:`_game_over`,不经本分支)——
        披露集含 :data:`DISCLOSURE_RUN_COMPLETE` 与否 = 胜负判别单一源。
        此后 :meth:`_reconcile_next_screen` 走 done=True ∧ decl='' 合格
        分支,漂移面零新增。"""
        prev = self.gs.node.value
        if prev is not None:
            apply_node_xp(self.gs, node_type=prev.kind)
        # —— 策略卡到级金效果条目局终点(与推进点同段决策/双通道写,挂经验
        # 入账后、局终声明前 = 末节点跨级发放先于局终;双点为经验源扩网
        # 后前瞻一致——现状态下不可达下与单点行为全等,单点则「局终跨级
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
        # —— 策略卡到级装备效果条目局终点(与推进点同段直写形态/组名,挂经验
        # 入账后、胜局披露前 = 末节点跨级也发放;双点为经验源扩网后前瞻
        # 一致——现状态下不可达下与单点行为全等。宝钻回调分工与休眠依据
        # 同推进点注释,不赘)。
        _equip_grant = check_strategy_level_equip_grants(
            self.gs, logic_sig('sim:strategy'))
        if _equip_grant is not None:
            on_diamond_acquired(self.gs, _equip_grant)
        self.disclosures[DISCLOSURE_RUN_COMPLETE] = 'survived_p3_boss'
        self._game_over()

    def _on_supply_picked(self) -> None:
        """补给选定落地:带钻选项给宝钻(状态副本事实写状态容器 diamond_count;
        钻信息 = 状态容器 chosen_supply 现值 2 元组 (角色,装备名列表) 按
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
        消费语义——确认时已写状态容器)。效果面零写入(选档已由 kernel 上报
        落 ``chosen_encounter``,本层零效果)。"""
        self._dismiss_and_settle_prep()

    def _fire_strategy_random_grants(self, *, plane: int, r: int) -> None:
        """获得链调用后就地判随机策略发放命中即掷(远见效果条目②「获得一个
        随机黄金投资策略」状态副本侧掷骰;登记表单一源 =
        ``cw_investments.STRATEGY_RANDOM_GRANTS``,现役唯一 = 远见)。

        - 触发载体 = 两个插入位置共用本助手:①拾取落地拍
          (:meth:`_on_invest_picked` 各落地效果条目后、难度旗牌更新前)
          ②环境直发分支(T-46 策略大师数量效果条目 ``gain_invest_strategy``
          调用后)。原设计一次性标志位挂拾取拍单点,被 T-46 直发分支实现(用户裁定
          2026-10-26「直接发一张随机投资策略不开 offer 无选卡屏」)推翻:
          直发 = 非拾取路径,远见(棱彩 ∈ 直发全池)可经直发入列
          active_strategies,门单挂拾取拍会把效果条目②迟滞到下一拾取拍,违
          「获得〔远见〕时」语义——改「获得链调用后就地判」后直发拍即掷。
        - 门 = 源名 ∉ ``_strategy_grant_fired`` ∧ 源名 ∈
          active_strategies:exactly-once 由集合记名构造保证(源卡按名字
          去重只入列一次);零假发 = membership 判定(呈现候选含源卡但
          未选 → 不入列 → 零发放);granted 名经 kernel 原语直接入列
          (非 pick 声明,零 ``_on_invest_picked`` 分派扰门)。重放安全:
          重复 advance 的同拍重放门已闭(集合记名),沿全局重放模型。
        - 池 = 目标品质池 − ``excluded_invest``(已出选项全集;掷中名
          **不加入** excluded——desc 无排除语义,与「游戏重复发放同名
          策略」行为对齐的保守形;且效果条目③生效期 offer 恒单棱彩候选,金名
          重现于 offer 结构性不可达,残余暴露面仅远见末槽拾取局无后继
          offer,零暴露)。掷中已持名照常可掷(注册效果条目去重跳写、效果条目
          照常,禁掷前排除持卡面)。池空(排除集吃光,金池 135 对排除集
          ~12 名上界,正常局不可达)静默跳发零置门——不迟滞不空手入链。
        - session=None:效果账本登记效果条目跳过(状态容器写照常,蓝海同构语义;
          granted 卡 overlay 注册面缺口按 40/135 现值随披露键申报);
          rng 显式流键 ``M11/grant/...`` 独立新流(缺省自掷 = 同 seed
          不重放,蓝海同款纪律),掷骰与二次入链分键(-gift 后缀)。
        """
        held = set(self.gs.active_strategies.value or [])
        for _src, _quality in STRATEGY_RANDOM_GRANTS.items():
            if _src in self._strategy_grant_fired or _src not in held:
                continue
            pool = [n for n, s in INVESTMENT_STRATEGIES.items()
                    if s.rarity == _quality
                    and n not in self.excluded_invest]
            if not pool:
                continue
            # 门先置防重放(一次性标志位族「标志位消费先于发放判定」同向);发放异常 =
            # 保守丢失,重放不双发。
            self._strategy_grant_fired.add(_src)
            self.disclosures.setdefault(
                STRATEGY_RANDOM_GRANT_ASSUMPTION_UNIFORM_V0, 'uniform_v0')
            rolled = pool[stream_rng(
                self.seed, f'M11/grant/p{plane}/r{r}').randrange(len(pool))]
            gain_invest_strategy(self.gs, None, rolled, rand=False,
                                 sig=logic_sig(
                                     group_id='act:sim@strategy-grant'),
                                 producer='SimBackend',
                                 rng=stream_rng(self.seed,
                                                f'M11/grant/p{plane}'
                                                f'/r{r}-gift'))
            log.info('[cw-sim] 随机策略发放分支:%s 获得 → 发放 %s(%s)',
                     _src, rolled, _quality)

    def _on_invest_picked(self, *, opening: bool) -> None:
        """投资选卡落地(效果 = kernel 获得链,经 report_action_pick_*
        已写状态容器;本层返回 + 去重集累计,排除集读状态容器 opts 现值)。"""
        opts = (self.gs.invest_env_opts.value if opening
                else self.gs.invest_strategy_opts.value) or []
        (self.excluded_env if opening else self.excluded_invest).update(opts)
        # 选卡落地拍大扩招扣金负效果条目(卡文「每损失4金币…最多扣除40金币」
        # 现算扣金,状态副本真值补全):live 同拍零写(游戏自扣,金整字段观察
        # 覆盖收尾,金面禁直写)。判别沿兄弟效果条目「呈现候选 ∩ 持有列表」交集
        # 形态(裸读呈现候选会把同框未选候选误燃);呈现一次性标志位防重放(扣金非
        # 幂等,重放多扣一笔)。扣金计划单一源 = dakuozhao_deduction_plan
        # (与获得链随机角色效果条目的发放只数同函数,两端数量口径天然一致);
        # 只扣 4 的整数倍、余金保留(取整读法,权威版本 = invest_effects.md
        # B 类裁定行);判别名 = PICK_INVEST_EFFECTS 登记键(注册面与负效果条目
        # 两字面量由键集闭集锁 + 本效果条目 evidence 锁兜漂移)。不置花费位:
        # 强制扣金非玩家操作支出,与买卡/升级/刷新花费通道分立。n=0
        #(持金 <4)零写零笔;扣后金自然参与下窗计息(先于下窗窗开,无
        # 基数序新语义)。位置 = 排除集累计后独立笔:本效果条目非环境无门控
        # 读面、非注册表字段分派,与后续各效果条目零交互;位置不变式(须在
        # _after_modal_pick 前)随函数整体满足。
        if not opening and self._strategy_pick_recruit_drain_latch:
            self._strategy_pick_recruit_drain_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if '大扩招' in picked:
                deduct, cnt = dakuozhao_deduction_plan(
                    int(self.gs.gold.value or 0))
                if cnt > 0:
                    gold_now = int(self.gs.gold.value or 0)
                    self.gs.observe(self.gs.gold, gold_now - deduct,
                                    evidence=sim_evidence(
                                        'strategy:recruit_drain:大扩招'),
                                    sig=obs_sig(group_id='sim:strategy'))
                    log.info('[cw-sim] 大扩招扣金分支:持金 %s 扣 %s'
                             '(发 %s 只 4 费随机角色)',
                             gold_now, deduct, cnt)
        # 追加随机环境型(已登记名 = cw_investments.ENV_REROLL_NAMES,现役
        # 唯一 = 蓝海 id113):选卡首链(上报函数)已完成「获得本环境」全部
        # 写分支(active_env + 即时金 + 申报行);本分支紧接状态副本侧掷骰出卷中名,
        # 原语二次入链「获得卷中环境」(gain_invest_env 一次调用完成
        # active_env 改写 + 节点序列场改写 + 登记分支 + on_env_gained 全族
        # 效果,零新发放实现;两次获得语义,追加非替换)。无重复发金:池
        # 排除已登记名后无任何 gold_instant 条目。session=None:本层字段面
        # 无会话可取,登记分支跳过、状态容器写照常(gain_invest_env None 语义)。
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
        # 选卡落地拍连胜置位效果条目(通用通道,辖域 = 注册表 streak_set≠0
        # 全体)。必须在难度旗牌更新之前:旗牌读 gs.streak 现值写备战
        # 难度,先置位旗牌才随新值(伟大征服难度+连胜项同拍反映置位后
        # 真值,实机对齐)。带符号绝对置位语义与禁聚合依据见
        # :func:`apply_strategy_pick_streak`;live 同拍零写(置位到结算
        # 之间 gs.streak 持旧值,真值经下一结算屏带符号读数观察覆盖
        # 收尾,fields.md streak 写入方两分不动)。拿卡名推导与呈现一次性标志位
        # 防重放 = xp 效果条目同款:标志位消费先于判定(交集空亦消费——每呈现窗
        # 至多一次落地消费,无效载荷的重放同样不得再触发)。
        if not opening and self._strategy_pick_streak_latch:
            self._strategy_pick_streak_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if picked:
                apply_strategy_pick_streak(self.gs, picked)
        # 选卡落地拍宝钻状态副本联动效果条目(拿卡即发宝钻的策略卡族共用:这么大的
        # 钻石 = 首例(用户裁定 2026-11-02 读法 B)、控制规模 = 帽改写卡
        # 随批归一同支(两卡各发宝钻×1,同名同物回调零差);卡级点名判别 =
        # 设计默认案最小推导,选卡通道批落地时归一为共享推导效果条目,先落方
        # 定形):sim 状态副本自持账补全
        # ——live 同拍零写(diamond_count/deploy_cap/back_layout 三域
        # live 归观察识别器跟踪,逻辑侧禁写,投影审计契约)。拿卡名推导
        # 与呈现一次性标志位防重放 = 前置各效果条目同款(标志位消费先于判定,交集空亦消费;
        # 回调三写非幂等,重放伪 +1)。发放落地门 = equips 现值非 None:
        # 宝钻装备效果条目(kernel 效果体)在拒落档(equips 未观察)下不入栏,
        # 此时回调会伪写 diamond_count/back_layout +1(equips_unobserved
        # 同判据,T-141 到级效果条目 placed 门同构);sim 初始值 equips=[] 下
        # 门恒开,门系形态级卫生面(直构/测试形态防御)。执行时序 = 效果条目1
        # 效果体入栏写之后(获得链首链先于本落地效果条目),deploy_cap 派生读
        # 现值天然含新宝钻。回调入参只传装备名,三写 observe 通道 sig
        # 由回调内构(on_diamond_acquired 零改动复用);位置 = 难度旗更
        # 新之前(家族惯例:选卡落地拍效果条目先于同拍难度读数;deploy_cap
        # 与难度无耦合,位置纯为家族一致性)。
        if not opening and self._strategy_pick_diamond_latch:
            self._strategy_pick_diamond_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if (('这么大的钻石' in picked or '控制规模' in picked or '财富就是力量' in picked or '多元化团队' in picked)
                    and self.gs.equips.value is not None):
                on_diamond_acquired(self.gs, '财富宝钻')
        # 选卡落地拍随机策略发放效果条目(远见效果条目②「获得一个随机黄金投资策略」,
        # 登记表 = cw_investments.STRATEGY_RANDOM_GRANTS):位置 = 各已落
        # 基准效果条目之后、难度旗牌更新之前——先落先占位、后落顺延插队(禁跨越
        # 已落基准效果条目重排);难度同拍时序 = granted 金(+3)与远见自身(豁免
        # 后 0)在下一拍 _update_difficulty_flag 同帧反映,与「选择后难度
        # 即时反映」裁定(2026-10-14)一致。直发路径的另一插入位置见 T-46
        # 直发分支(获得链调用后就地判,两个插入位置共用一门,R1 修订形态)。
        _grant_plane, _grant_r = self._node_pos()
        self._fire_strategy_random_grants(plane=_grant_plane, r=_grant_r)
        # 「选择后」敌方难度读数即时反映(裁定 2026-10-14);开局环境选卡时
        # 节点未进窗(node None),写点内早退。
        self._update_difficulty_flag()
        # 选卡落地拍即时经验效果条目(通用通道):sim 状态副本自持账补全——live 同拍
        # 零写(经验面板画面可读 = 观察覆盖),sim 无观察,不发即持卡局
        # 等级进度失真。拿卡名 = 呈现候选 ∩ 持有列表(offer 候选排除已持,
        # 落地交集 = 刚拿入的卡;无效载荷获得链零状态容器写 → 交集空 → 零写)。
        # 呈现一次性标志位防重放:标志位消费先于发放判定,无一次性标志位的重复 advance 零写。
        if not opening and self._strategy_pick_xp_latch:
            self._strategy_pick_xp_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if picked:
                apply_strategy_pick_xp(self.gs, picked)
        # 选卡落地拍位面段补发经验效果条目(「现在以及每个位面开始时」族中途拿
        # 卡补发,用户裁定 2026-11-01 确定:当前已开始的位面其位面段登记
        # 拍全额补发,后续位面照常;通用通道辖域 = 注册表 xp_per_plane>0
        # 全体):sim 状态副本自持账补全——live 同拍零写(经验面板画面可读 =
        # 观察覆盖),sim 不补即持卡局等级进度失真。拿卡名推导与呈现一次性标志位防
        # 重放 = 即时经验效果条目同款(标志位消费先于判定,交集空亦消费);已开始
        # 判据/禁聚合/写入形态见 :func:`apply_strategy_plane_refire_xp`。
        # 位置 = 即时经验效果条目后独立笔:同域 XP 字段分派(xp_instant /
        # xp_per_plane 互斥读),与其余各效果条目零交互。
        if not opening and self._strategy_pick_plane_refire_latch:
            self._strategy_pick_plane_refire_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if picked:
                apply_strategy_plane_refire_xp(self.gs, picked)
        # 选卡落地拍出售发牌效果条目(板面重写族出售支):sim 状态副本自持账补全——
        # live 同拍零写(游戏侧发 5 只 2★,下一备战帧观察覆盖收尾,三权威版本
        # 裁定零改动),sim 无观察,不发即持卡局资产面失真。先卖后抽时序
        # = 插入位置天然保证:kernel 获得链(含桥出售面)已在选卡首链写完,
        # 本效果条目落桶出口时 held 已归零(出口时序契约前提)。拿卡名推导与
        # 呈现一次性标志位防重放 = xp 效果条目同款(标志位消费先于判定,交集空亦消费);
        # 发牌资格归判据集分派非单卡特判;rng 显式流键构造(缺省回退自掷
        # 破 sim 确定性;段位沿 M21/M22/M23 编号续,与商店发牌 M05/环境
        # 族 M02 分域)。位置 = 链尾独立笔:本效果条目非环境无门控读面、非注册
        # 表字段分派,与前置各效果条目零交互。
        if not opening and self._strategy_pick_sell_deal_latch:
            self._strategy_pick_sell_deal_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if picked:
                apply_strategy_pick_sell_all_deal(
                    self.gs, picked, stream_rng(self.seed,
                                                'M24/sell-all-deal'))
        # 选卡落地拍获得链交换效果条目的轨迹成对效果条目(不等价交换 hp⇄gold 互换;
        # 通用通道辖域 = 注册表 hp_gold_swap=True 全体):kernel 交换写端
        # 在选卡首链(report_action_pick_* → gain_invest_strategy →
        # on_strategy_gained)已落状态容器,本效果条目只做 hp_trail 成对追加(写流
        # ↔轨迹全序同构不变式,first_run 状态容器不变式②——交换写行 journal
        # 在案而轨迹缺行即红)。配对形态 = 呈现一次性标志位族形(与前置各效果条目一致)
        # 非尾值检测式:检测式「trail 尾值 ≠ hp 现值」在等值交换(交换前
        # hp 已 == min(gold,100))下漏配——等值写行照落(先例 =
        # apply_hp_outcome 胜局支),尾值判据看不见该行,同构锁红;一次性标志位 +
        # 判别按「交换效果条目每发恰一写行」配对,等值形态天然覆盖。拿卡名
        # 推导与呈现一次性标志位防重放 = 前置各效果条目同款(标志位消费先于判别,交集空亦
        # 消费;防重放窗同界 = 呈现→落地)。位置 = 即时生命效果条目之前:kernel
        # 写行先于本函数各效果条目落状态容器,轨迹追加序须与写行序同构对齐(未来
        # 同拍双 hp 效果条目一旦成立,追加序错位即红,前置卡位保序)。
        if not opening and self._strategy_pick_swap_latch:
            self._strategy_pick_swap_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            for _n in picked:
                _eff = STRATEGY_ECONOMY.get(_n)
                if _eff is not None and _eff.hp_gold_swap is True:
                    self._hp_trail_append()
        # 选卡落地拍即时生命效果条目(hp 通道模式卡「健康充值」首落;通用通道,
        # 辖域 = 注册表 hp_instant≠0 全体,正加负损双向——负值支先亏后盈
        # −20 随批扩面):sim 状态副本自持账补全——live 同拍零写(游戏自算,
        # 血量条观察覆盖收尾,fields.md hp 写入闸无逻辑写入方)。拿卡名
        # 推导与呈现一次性标志位防重放 = 前置三条效果条目同款(标志位消费先于判定,交集空亦
        # 消费);不 clip/禁聚合依据见 :func:`apply_strategy_pick_hp`。
        # 负值支写后同拍扩挂损血档位触发器(持保险局选卡损血入累计器,
        # 非「减负」——−20 换算 +20 损失计入,披露键 ③ 触发源域随批扩
        # 两个插入位置);rng 显式流键构造(缺省回退自掷破 sim 确定性,出售发牌
        # 效果条目同款纪律;独立子流与 M13 结算保险流分域,同 seed 其他流零
        # 扰动)。位置 = 链尾独立笔:与前置各效果条目零交互(字段分派互斥:
        # xp_instant / streak_set / 发牌判据集 / hp_instant)。轨迹追加 =
        # observe 同笔语义(hp 写流 ↔ hp_trail 全序同构不变式按写行粒度
        # 对齐——效果条目返回笔数即写行数,逐笔追加)。
        if not opening and self._strategy_pick_hp_latch:
            self._strategy_pick_hp_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            for _ in range(apply_strategy_pick_hp(
                    self.gs, picked,
                    stream_rng(self.seed, 'M25/pick-hp-loss'))):
                self._hp_trail_append()
        # 选卡落地拍分期金剩余效果条数初始化效果条目(「接下来 count 次」递减状态容器字段
        # 状态;通用通道辖域 = 注册表 gold_next_nodes_count>0 全体):
        # sim 状态副本自持账补全——live 同拍零写(游戏自算自显,金整字段观察
        # 覆盖收尾),sim 无初始化则节点窗分期效果条目永空 = 持卡局分期段静默
        # 零发。拿卡名推导与呈现一次性标志位防重放 = 前置各效果条目同款(标志位消费先于
        # 判定,交集空亦消费);初始化 = 直接赋值(键 = 卡名每卡独立条目,
        # 同卡重拿重置 = 排除闸下防御性默认)。位置 = 链尾独立笔:与
        # 前置各效果条目零交互(字段分派互斥:gold_next_nodes_count)。
        if not opening and self._strategy_pick_gold_next_nodes_latch:
            self._strategy_pick_gold_next_nodes_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if picked:
                apply_strategy_pick_gold_next_nodes_init(self.gs, picked)
        # 选卡落地拍超发货币负债效果条目(金面播值负债卡清零支,状态副本真值补全):
        # live 同拍零写(游戏自扣,金整字段观察覆盖收尾,金面禁直写三基准
        # T-85 定形)。判别三重:呈现一次性标志位防重放(前效果条目同形)→ 本拍拿卡名判别
        #(呈现候选 ∩ 持有列表,前置各效果条目同款推导;条目已登记不能单独作本拍
        # 信号——条目生命跨 6 个节点入口,窗内后继拿卡事件「已登记」仍真,
        # 只按条目判会误清后继窗累积收入)→ 条目已登记校验(单载体制:条目
        # = 获得链登记产物,兼负债额快照载体;条目缺 = bypass 路径未经
        # 获得链,保守零动作 + disclosures 留证——零新增披露键,内联运行
        # 时键承载保守形态)。动作:负债额读 counters[LOST](缺播防御 =
        # 以扣减前金现值兜底同值);金清零写独立证据笔
        # strategy:hyperemit_drain:<卡名>(−G 增量 = 写前金 − 0,金轨迹
        # 对账可导);金已为 0 短路零写(重放 −0 幂等,T-177 同写点同形
        # 防御取舍)。位置 = 链尾独立笔:与前置各效果条目零交互(非注册表字段
        # 分派,条目判别);扣后下一窗利息按扣后金算,自然跟随。
        if not opening and self._strategy_pick_hyperemit_drain_latch:
            self._strategy_pick_hyperemit_drain_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if HYPEREMIT_SPEC_NAME in picked:
                _em = self.gs.effects.first(HYPEREMIT_SPEC_ID)
                if _em is None:
                    self.disclosures.setdefault(
                        'strategy_hyperemit_bypass_no_entry',
                        'picked_without_registered_effect_entry')
                else:
                    gold_now = int(self.gs.gold.value or 0)
                    if gold_now > 0:
                        _lost = int(_em.counters.get(CounterKey.LOST,
                                                     gold_now))
                        tag = f'strategy:hyperemit_drain:{_em.spec.name}'
                        self.gs.observe(self.gs.gold, 0,
                                        evidence=sim_evidence(tag),
                                        sig=obs_sig(group_id='sim:strategy'))
                        log.info('[cw-sim] 超发货币负债分支:%s 清零 '
                                 '(快照 %s,现持 %s,增量 −%s)',
                                 _em.spec.name, _lost, gold_now, gold_now)
        # 选卡落地拍已损血衍生金效果条目(「获得等同于你已损失生命数量的金币」,
        # 星际和平保险 id 303001 首例;通用通道辖域 = 注册表
        # gold_per_hp_lost_now 全体,状态副本派生计算形非静态字段):sim 状态副本
        # 自持账补全——live 同拍零写(游戏自算自发,金余额观察覆盖收尾,
        # 金面禁直写三基准 T-85 定形)。已损失口径与开局基线来源见
        # :func:`check_strategy_hp_loss_gold`(基线 = hp_trail[0] 开局
        # 真值,reset 序尾已记录,pick 时点恒在场);条件单一源 = kernel
        # 检查函数(卡直读注册行禁聚合)。建模假设经
        # STRATEGY_HP_LOSS_GOLD_BASELINE_ASSUMPTION 随局申报(判读申报
        # 制)。拿卡名推导与呈现一次性标志位防重放 = 前置各效果条目同款(标志位消费先于判定,
        # 交集空亦消费——每呈现窗至多一次落地消费,无效载荷的重放同样
        # 不得再触发);零损失选卡(开局即选)检查函数返回 0 = 零笔零
        # 申报(与游戏「已损失 0 → 金 0」自算同形)。位置 = 链尾独立笔:
        # 与前置各效果条目零交互(金域加笔,扣金负效果条目为减向分账,evidence 分账
        # 可归因);先于立即效果条目呈现体(其 return 早退会吞本拍落地语义)。
        if not opening and self._strategy_pick_hp_loss_gold_latch:
            self._strategy_pick_hp_loss_gold_latch = None
            picked = [n for n in (self.gs.invest_strategy_opts.value or [])
                      if n in (self.gs.active_strategies.value or [])]
            if picked:
                gold_gain = check_strategy_hp_loss_gold(
                    self.gs, opening_hp=self.hp_trail[0])
                if gold_gain > 0:
                    gold_now = int(self.gs.gold.value or 0)
                    self.gs.observe(self.gs.gold, gold_now + gold_gain,
                                    evidence=sim_evidence(
                                        'strategy:hp_loss_gold'),
                                    sig=obs_sig(group_id='sim:strategy'))
                    self.disclosures.setdefault(
                        STRATEGY_HP_LOSS_GOLD_BASELINE_ASSUMPTION,
                        'opening_minus_current_sim_model_v0')
                    log.info('[cw-sim] 已损血衍生金分支:开局 %s 现值 %s '
                             '衍生金 +%s', self.hp_trail[0],
                             int(self.gs.hp.value or 0), gold_gain)
        # 选卡拍商店改写效果条目 + 位面段补发双效果条目(「现在及每个位面开始时」族,
        # 公司严选 301401 首条目;通用通道辖域 = 注册表 shop_rewrite_
        # forced_cost>0 / gold_per_plane>0 全体,字段分派非单卡特判)。
        # 触发面 = 窗口起点快照差分限定「本拍新获得」——本方法是环境/
        # 策略双支统一口,扫描式遍历持有表会在后续拿他卡时反复触发(卡面
        # 「现在」= 获得时点,无此语义);快照在节点窗守卫同拍记录,差分
        # 消费后前滚并入现值(链式选卡〔delay-0 呈现〕同窗二次落地时差分
        # = 本拍新获得,旧卡不重燃;重放落地差分恒空 = 零写,无一次性标志位自防)。
        # 改写效果条目 = kernel 强制采样器单源直写(live 同拍零写观察覆盖);
        # 位面段补发 = 用户裁定 2026-11-01 族级确定(中途拿卡判当前位面
        # 已开始 → 登记拍全额补发·非按比例,后续位面照常):金效果条目沿
        # apply_strategy_plane_refire_xp 同判形(node 在场即已开始,
        # None = 保守零补发禁猜),补发改写效果条目同拍独立流键/evidence——
        # 同拍「选卡改写 × 补发改写」双触发两条效果条目都发(固定理财族「两条效果条目
        # 都发」同判,journal 双行如实登记禁静默合并)。位置 = 链尾、
        # 拿卡拍立即效果条目呈现之前:重入选卡须先于模态返回(呈现体 return
        # 早退会吞本拍),先于呈现 = 改写属本拍落地语义非呈现副作用。
        if not opening:
            now_held = tuple(self.gs.active_strategies.value or ())
            new_picked = [n for n in now_held
                          if n not in self._strategies_at_window_start]
            self._strategies_at_window_start = now_held
            if new_picked:
                self._apply_strategy_shop_rewrite_gain(new_picked)
                if self.gs.node.value is not None:
                    apply_strategy_plane_refire_gold(self.gs, new_picked)
                    # 位面段占席道具补发(终身学习首例;用户裁定 2026-11-01 族级
                    # 「位面段补发·当前位面全额」裁定注释点名终身学习共享,与
                    # XP/金支同判同形;gs.node 在场判据,None 保守零补发;item 域
                    # 走 gain_bench_item(rand=False),evidence 沿族形分账禁静默合并)
                    apply_strategy_plane_refire_item(self.gs, new_picked)
                    self._apply_strategy_shop_rewrite_refire(new_picked)
        # 拿卡拍立即效果条目(delay_nodes=0 承载,白银投资首例):队列存在
        # 本拍刚拿卡的 delay-0 条目(拿卡同拍登记,remaining 恒 0 未递减;
        # delayed 效果条目到点条目非本拍入队,不入本插入位置辖域——顺延语义归
        # 窗首到期效果条目,拿卡拍不抢,防同窗二次呈现吞掉「下一空闲窗必呈现」
        # 契约)→ 弹除 + 呈现 + resume='node',不进 _after_modal_pick——
        # 第二选卡经同一 report 通道重入落地(链式语义同机制;每拍至多
        # 呈现 1 次 = delay-0 条目每卡至多一条的结构性承载,排除集下
        # 同卡不可重拿)。呈现体与窗首到期效果条目共用(品质改写不作用、弹除
        # = 呈现时),rng 流键分键(pick 段),呈现留证分键
        # (strategy_immediate_offer_fired)。拿卡名推导 = 各效果条目同款
        # 「呈现候选 ∩ 持有列表」;命中即本拍新登记(delay-0 条目只在
        # 本拍产生,旧条目 remaining 已递减或属他卡)。位置不变式:
        # 尾段、_after_modal_pick 之前(重入选卡须先于模态返回)。
        if not opening:
            queue_now = tuple(self.gs.pending_strategy_offers.value or ())
            picked_now = [n for n in (self.gs.invest_strategy_opts.value or [])
                          if n in (self.gs.active_strategies.value or [])]
            imm_idx = next((i for i, entry in enumerate(queue_now)
                            if entry[0] in picked_now
                            and int(entry[1]) == 0), None)
            if imm_idx is not None:
                imm_name = queue_now[imm_idx][0]
                imm_spec = next(leg for leg in
                                STRATEGY_DELAYED_OFFERS[imm_name]
                                if leg.delay_nodes == 0)
                imm_plane, imm_r = self._node_pos()
                self._present_extra_offer_screen(
                    imm_name, imm_spec, queue=queue_now, idx=imm_idx,
                    rng_key=f'M11/offer-extra/pick/p{imm_plane}/r{imm_r}',
                    evidence=f'present_immediate_extra_offer:{imm_name}',
                    disclosure_key=STRATEGY_IMMEDIATE_OFFER_FIRED)
                return
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
        获得后果回调);候选点击缺记录 = 状态副本不可辨,披露不猜。"""
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
        上报内 ``consume_screen_change``(两侧同一行代码,register-
        consume.md「sim 消费」),本层不重复出队。
        """
        if kind == 'planner':
            self.disclosures[DISCLOSURE_PLANNER_EFFECT] = 'picked:report_branch'
        self._dismiss_modal()
        self._present_pending_overlay()

    # ---------------------------------------------------------- 状态机

    def _announce_screen(self, value: str) -> None:
        """画面广播(内部状态机 → 状态容器画面域,渲染复盘的画面章证据面)。

        - 值级豁免:``SCREEN_SETTLE``/``SCREEN_LOBBY`` 不广播——结算事实
          已由战斗章 settlement 写入行 + 局头终局行承载,大厅收尾事实在
          局头;广播只各造一个未注册空壳章。豁免按值不按赋值点(模态
          返回位可为结算屏,点位豁免会泄漏「货币战争-结算」空壳章);
        - 两行一对:``prev_screen`` = 上次广播值(初值 = 状态容器每局全新创建空串)→
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
        """overlay 呈现检查(数据源 = 状态容器登记
        ``gs.screen_changes.pending``,旧私有队列呈现面已停用——
        队列本体随评估器归 3.5 清扫;呈现时机不变 = advance/步界检查)。

        ``fortune_base`` = fortune 呈现门的底层判据屏(缺省 = 当前
        ``_screen``;节点窗起点传**目标底层**——当前屏仍是旧结算屏,判当前
        会吞掉后续呈现)。

        逐 kind 呈现门(overlay 生命周期契约(sim 消费)):

        - megastar:模态 + 候选写状态容器(场上盛会之星资格成员,含持徽
          贡献——候选语义 = 判据资格集同源);
        - planner:模态(选项桶实机 OCR 写点,sim 生成器批接入);
        - box_card/expert_invite:open_box/open_bookcard 的 advance 分派
          已呈现对应模态(候选写入在各自过程),本检查幂等守卫;
        - fortune:**逐 kind 呈现门**——仅底层 = 备战时收尾消费
          (用户确认:下一节点非备战时推迟,选完进备战
          先弹,不压补给/遭遇屏);底层非备战 = 条目存活等待;
        - aha/partner/fortune(备战底层时)/wish_trial/star_tome:无
          sim 呈现面族(aha 无独立画面档,实机 = 备战识别标志特殊规则点
          首件;其余画面 op 无 sim 观察分支,呈现即卡 observe 重试;
          partner 候选可自资格集算,候观察分支接通调用后再呈现)→ 消费 +
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
                # 无 sim 呈现面族:aha 无独立画面档(实机 = 备战识别标志特殊
                # 规则点首件);partner/fortune/wish_trial/star_tome 选项
                # 注册表缺位且画面 op 无 sim 观察分支(呈现即卡 observe
                # 重试;partner 候选可自资格集算,候 sim 观察分支接通调用后再呈现)
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
        """巨星候选写状态容器(候选 = 场上盛会之星角色,含持星徽贡献;选项
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
        # 节点序位锚定(sim 写端 = 状态副本呈现节点,与实机「备战帧顶栏/补给屏
        # 节点条」观察锚定同口;终结动作推进的观察态门以此为前提)。
        # 超发货币回流效果条目(金面播值负债卡回流支,前读两拍跨窗挂起形):
        # 拍① = 窗内现读条目——remaining_nodes == 1 即「下一入口 = 第 6 次
        # 入口」(remaining ≡ N − counter 等价式;第 6 次节点入口 = 注册行
        # offset+1,impacts 用户裁定 2026-09-10),快照回流额 = counters[LOST]
        # + payload.gold_at_node 挂起;拍② = 下一窗开窗先付挂起额一笔,
        # evidence 笔 strategy:hyperemit:<卡名>:p{plane}r{r}。跨窗挂起的
        # 机制根因:sim 动作流的节点效果递减发生在动作上报路径
        #(kernel advance_node_effective 尾段,settle_confirm/supply_finish
        # 上报内)先于本方法——窗口内现读恒为 tick 后状态,条目归零移除
        # 已随第 6 入口的转换 tick 发生,本方法内无 pre-tick 可读位;挂起
        # 值 = 设计稿「前读值」概念的跨窗承载(设计稿基准前提 = 推进基准执行
        # 递减,经引擎链实测在 sim 动作流不成立,批次报告随批申报)。持久
        # 状态仍只有条目一份:挂起值 = 一次性消费单窗暂态(呈现一次性标志位同形
        # 私有暂态,不入状态容器/不入快照恢复),一次性消费即自防重;局终未
        # 消费挂起随局蒸发不补发。发放点先于 _begin_node_window 收入段
        # = 支付入本窗利息基数(与定期福利 T-162 落账入基数序同向,禁
        # 静默分叉);位面过渡早退分支在本效果条目之后 → 位面首入口照常回流
        #(计数域 = 节点入口事件全型,supply/reward/battle/boss/修饰局
        # 插入节点照计数,T-106 先例)。live 零写(游戏自发,金整字段
        # 观察覆盖兜底)。
        # 拍② 先行:上一窗挂起的回流额在本窗开窗先付(本窗 = 第 6 次入口;
        # 支付先于本窗收入段 = 入息基数,T-162 同向)。
        if self._hyperemit_payoff_pending is not None:
            _em_name, _amount = self._hyperemit_payoff_pending
            self._hyperemit_payoff_pending = None
            tag = f'strategy:hyperemit:{_em_name}:p{pos[0]}r{pos[1]}'
            self.gs.observe(
                self.gs.gold, int(self.gs.gold.value or 0) + _amount,
                evidence=sim_evidence(tag),
                sig=obs_sig(group_id='sim:strategy'))
            log.info('[cw-sim] 超发货币回流分支:%s + %s(第 6 入口,p%sr%s)',
                     _em_name, _amount, pos[0], pos[1])
        # 拍① 后行:本窗现读条目——remaining_nodes == 1 即「下一入口 =
        # 第 6 次入口」,快照回流额挂起待下一窗支付。
        _em = self.gs.effects.first(HYPEREMIT_SPEC_ID)
        if _em is not None and _em.remaining_nodes == 1:
            self._hyperemit_payoff_pending = (
                _em.spec.name,
                int(_em.counters.get(CounterKey.LOST, 0))
                + int(getattr(_em.spec.payload, 'gold_at_node', 0) or 0))
        observe_node_anchor(self.gs, pos,
                            trigger_screen=self._screen_for_node(kind),
                            actor='SimBackend')
        # 策略卡条件节点序列改写效果条目(决议:娱乐星球 id 302301 策略侧首例;
        # 「进入战斗时，若拥有180枚金币，将本局游戏剩余的非首领节点替换
        # 为奖励节点」触发器单一源 = kernel check_strategy_node_rewrite,
        # 白名单表 STRATEGY_NODE_REWRITE_TRIGGERS 驱动,注册表 = 策略卡域
        # cw_investments,cw_investments.py 表头辖域互斥申报在卷:env 名
        # 键域归 ENV_NODE_REWRITE_RULES 注册刻无条件应用,策略卡名键域归
        # 本效果条目条件触发,两表键域互斥)。插入位置 = 窗开拍非防漏——位面过渡
        # 分支提前 return 后过渡屏点击照常收尾本窗(_begin_node_window),
        # 钉在收尾只会迟不会漏;取窗开的真实优点 = 触发时点贴「进入战斗」
        # 窗开语义(过渡屏呈现即评估,不待点击)+ 当前位已按旧 kind
        # observe 零失真(改写不含当前位,本窗收尾重读现值零失真)。
        # gold 口径 = 轮首收入前(apply_round_start_income 在窗收尾收入段
        # 晚于本插入位置;同段前序 = 超发回流效果条目先付,其金入判定口径,判读
        # 申报制)。kernel 纯决策零写,命中才本侧一拍两写:场字段改写值
        # (evidence='node_seq:strategy',与 env 注册写 'node_seq:env'
        # 分键双写端)+ 一次性标志位追加(strategy_conditional_done 纯卡名键共域,
        # 键集 = 持卡∩表未置一次性标志位成员——改写后剩余槽位无 battle 位,后续
        # 不再有可达评估点,同拍全量封账不可能跳过会发的后续触发;
        # 证伪前提随 env 覆盖边申报)。相对序申报:策略改写后同局再选
        # 节点改写环境 → env 注册写整表覆盖策略改写(后写赢),双改写
        # 叠加交互零特判(判读申报制,证伪路径 = 实机双改写叠加局观察)。
        # 零 rng;live 零写观察覆盖(实机改写游戏自算自演,bot 经既有
        # 节点观察链承接,偏离留证不自动改写);后继推进 sequence_next/
        # 各消费面读场字段自动跟随。
        _rw_seqs = check_strategy_node_rewrite(
            self.gs, pos=pos, gold=int(self.gs.gold.value or 0))
        if _rw_seqs is not None:
            _rw_ev = sim_evidence('node_seq:strategy')
            self.gs.write_logic(self.gs.node_seq_by_plane, _rw_seqs,
                                produced_by='SimBackend:strategy_node_rewrite',
                                evidence=_rw_ev,
                                sig=logic_sig('sim:strategy'))
            _rw_done = tuple(self.gs.strategy_conditional_done.value or ())
            _rw_latch = [n for n in (self.gs.active_strategies.value or ())
                         if n in STRATEGY_NODE_REWRITE_TRIGGERS
                         and n not in _rw_done]
            self.gs.write_logic(
                self.gs.strategy_conditional_done,
                _rw_done + tuple(_rw_latch),
                produced_by='SimBackend:strategy_node_rewrite',
                evidence=_rw_ev, sig=logic_sig('sim:strategy'))
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
        # 窗口起点持有策略快照(守卫同拍):选卡拍改写/补发双效果条目的差分
        # 基线(重放同窗守卫早退不重拍,差分语义跨重放稳定)。
        self._strategies_at_window_start = tuple(
            self.gs.active_strategies.value or ())
        kind = node_sequence_of(plane, self.gs.node_seq_by_plane.value)[r - 1]
        # 备战画面敌方难度读数观察(裁定 2026-10-14):窗开即敌方难度读数可见时点,
        # 上窗以来状态变动(连胜/选卡)在此反映;本窗内选卡的即时反映
        # 由 _on_invest_picked 写点承担。
        self._update_difficulty_flag()
        # 策略卡备战席条件离场金效果条目(「进入新节点时，备战席的1星【花火】/
        # 【火花】会留下2/4金币并去别处找乐子」族,愚者恶作剧 id 260701
        # 首例):进窗事实点在窗口幂等守卫内(重放不双发),kernel 检查函数
        # 单一源 check_strategy_bench_leave_gold(纯读零写,未持卡/无匹配
        # 单位零写,零 done 一次性标志位——卡面无「首次」限定,每节点窗条件成立即
        # 触发)。插入位置钉在收入段最前(与定期福利金效果条目同段邻位、扑满递延
        # 快照与轮首收入之前——离场金入本节点利息基数,与 live 轮初口径
        # 「利息计算基数 = 结算前金现值」同向,T-162 定形;离场腾槽在任何
        # 后续读数前生效)。计划非空两笔写:①金写 = observe Σ计划金币
        # 独立笔(与收入三分量账分键;evidence 含逐单位明细
        # 'strategy:bench_leave_gold:<卡名>:p<位面>r<轮>:名@s槽+金;…');
        # ②离场写 = BenchView 整视图结构性写(匹配槽置空槽,卖备战席角色
        # 置 empty 同形,capacity 不动;两笔互不读对方字段,先后无行为差,
        # 序 = 卡文语序「留下金币并去别处找乐子」先金后离场)。
        # **相对序现位申报**(沿人才空洞计数效果条目先例治理模式):本效果条目位于同窗
        # 全部 bench 谓词消费之前——移出 1星花火/火花会改变后续 bench 谓词
        # 输入域:人才空洞计数 XP 效果条目(≤4/≥8 门槛计数,如 6→4 触发 ≤4 多发
        # 3XP)/空仓 XP 效果条目与装备计数 XP 效果条目(离场单位身上装备随移出,装备域
        # 输入收窄)/node_char 复制效果条目(落席空槽候选增多;谓词本体零交互——
        # 价值投资族绑定 = 随机 1 费角色,花火 2 费/火花 4 费永不被绑定)。
        # 相对序官方无定论 = 判读申报制辖域,现位 = 收入段最前(证伪路径 =
        # 实机持卡局节点窗内离场与 XP/复制发放的先后观察,证伪则改序重
        # 申报)。live 零写观察覆盖(实机离场与离场金由游戏自算自显,备战
        # 席整表观察 + 金观察链覆盖);零 rng 确定结算。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            BenchSlot,
            BenchView,
        )
        leave_plan = check_strategy_bench_leave_gold(self.gs)
        if leave_plan:
            leave_card = next(
                (n for n in (self.gs.active_strategies.value or ())
                 if n in STRATEGY_BENCH_LEAVE_GOLD_GRANTS), '')
            leave_detail = ';'.join(
                f'{name}@s{slot}+{gold}'
                for slot, name, gold in leave_plan)
            leave_tag = (f'strategy:bench_leave_gold:{leave_card}'
                         f':p{plane}r{r}:{leave_detail}')
            self.gs.observe(
                self.gs.gold,
                int(self.gs.gold.value or 0)
                + sum(g for _, _, g in leave_plan),
                evidence=sim_evidence(leave_tag),
                sig=obs_sig(group_id='sim:strategy'))
            view = self.gs.bench.value
            if view is not None:
                slots = list(view.slots)
                for slot_idx, name, _gold in leave_plan:
                    if 0 <= slot_idx < len(slots):
                        s = slots[slot_idx]
                        if (s is not None and s.kind == 'unit'
                                and s.unit is not None
                                and s.unit.char_id == name):
                            slots[slot_idx] = BenchSlot(kind='empty')
                        else:
                            # 判定与写刻间槽内容漂移(同窗内前置效果条目写席
                            # 才可达;当前段序收入段最前,无前置写席效果条目
                            # = 现网不可达防御):留证跳写不误清他人槽。
                            log.warning(
                                '[cw-sim] bench_leave_gold 槽内容与'
                                '判定漂移,跳写留证: p%sr%s slot=%s',
                                plane, r, slot_idx)
                self.gs.observe(
                    self.gs.bench,
                    BenchView(slots=slots, capacity=view.capacity),
                    evidence=sim_evidence(leave_tag),
                    sig=obs_sig(group_id='sim:strategy'))
        # 投资策略每节点金效果条目(定期福利系):进任意节点窗发持卡聚合值,
        # 独立观察笔(evidence/sig 与收入笔分键)——轮首收入三分量账
        #(IncomeApplied.total = 该笔金增量)对账关系保持纯净,禁并入
        # 收入写。插入位置钉在收入段最前(扑满递延快照与轮首收入之前):
        # 卡面「每次进入新节点时」= 最早时点,窗开先落账后,扑满快照与
        # 轮首收入的利息基数(均读金现值)自然含本效果条目,与 live 口径「利息
        # 计算基数 = 结算前金现值」(cw_effect_inventory)同向。boss 金效果条目
        # /尾款金效果条目挂收尾段、不入同节点利息基数——两卡 desc 时点语义不
        # 同(「进入首领节点时」/「最后一个补给阶段后」 vs 无条件每节点
        # 息账前给金),各自插入位置均有已登记支撑,基数序分叉为显式申报非静默
        #(统一收尾提案归 round_start_income 承载方式定夺批)。零值零写
        #(未持卡零新增观察行);幂等复用窗口守卫(同节点窗重放整段跳过),
        # 零新增守卫。
        invest_gold = strategy_invest_node_gold_of(self.gs)
        if invest_gold > 0:
            gold_before = int(self.gs.gold.value or 0)
            tag = f'strategy:invest_node_gold:p{plane}r{r}'
            self.gs.observe(self.gs.gold, gold_before + invest_gold,
                            evidence=sim_evidence(tag),
                            sig=obs_sig(group_id=f'sim:{tag}'))
        # 分期金效果条目(长期主义系「接下来 count 次」):递减状态容器字段逐卡判剩余,
        # 窗开先落账 + 入同节点利息基数(裁决点 5 默认案,与上方 gold_per_
        # node 聚合效果条目无条件同插入位置序——本写点仍在扑满递延快照与轮首收入
        # 之前);与聚合效果条目同段两笔独立写、互不聚合(每卡独立 evidence 笔,
        # 支付源 = 各条目注册值按卡名直读,禁聚合 payload)。全节点型
        # 计数:凡进窗即一期(supply/reward/battle/boss/修饰局插入节点
        # 照算,纯节点事件先例 T-106 稿承 T-98 §1.1);游戏终局剩余效果条目
        # 自然蒸发不补发。零值零写(未持分期卡零新增观察行);幂等复用
        # 窗口守卫,零新增守卫。
        apply_invest_installment_gold(self.gs, plane=plane, round_num=r)
        # 开源节流条件息顶满消费(kernel tick 捕获→载体→窗开消费契约的
        # 消费半边,读+清单清点):floor 评估时点 = tick 捕获 = 进节点时点
        # (卡面「进入新节点时」口径);非扑满支随收入透传,扑满支入快照
        # 四元组递延——结算时重评估会读到扑满节点自身的花费(时点漂移),
        # 快照随行禁现读。
        interest_floor = consume_strategy_interest_topup(self.gs)
        # 轮首收入(M04;败局补偿登记待办按 kernel 分支序消费——supply/reward
        # 轮不消费,败态跨轮保留至下一战斗轮;连胜 = 状态容器带符号派生读)
        pending = self.gs.pending_loss.value
        if is_piggy_node(self.gs):
            # 扑满节点收入递延:统一公式败局形需胜负,窗口开时未知 →
            # 只冻结基数(金/进轮连胜/修饰/顶满下限 = 轮初口径),结算分支
            # 落账(_resolve_battle);支付时点 = 结算屏,与实机一致。
            self._piggy_income_snap = (
                int(self.gs.gold.value or 0),
                max(int(self.gs.streak.value or 0), 0),
                income_modifiers_of(self.gs), interest_floor)
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
                pending_loss=pending, interest_floor=interest_floor)
        if kind not in INCOME_BRANCH_NODE_TYPES and pending is not None:
            clear_pending_loss(self.gs,
                               sig=obs_sig(group_id='sim:loss'))
        # 位面开局环境发放分道:声明矿环境走声明入队(金在点击兑现时
        # 入账),其余环境保留直发通道(通道留置)。
        self._apply_env_plane_start(plane)
        if r == 1:
            # 位面首节点窗:策略域位面开始 XP 效果条目(固定理财首例;增发货币
            # 环境分道同窗先形,窗口幂等守卫承接重放不双发)。刷新支不在此
            # ——kernel 推进边界拍位面开始桥(双插入位置分工,拍点差申报 =
            # 先推进后开窗,XP 支略后)
            self._apply_strategy_plane_start_xp(plane)
            # 策略域位面开始金效果条目(公司严选首例,「现在及每个位面开始时」
            # 族位面段金支):XP 支同窗邻位独立笔,注册表直读禁聚合;窗口
            # 幂等守卫承接重放不双发。
            self._apply_strategy_plane_start_gold(plane)
        # 环境定时道具到点发放(迭代 2026-09-24-scheduled-env-gifts
        # design §2.4):本收尾在窗口幂等守卫内,且位面过渡点空白与直进
        # 节点共用——「第 N 位面开始时」类发放即落在该位面 1 号节点窗
        # 打开时点(位面过渡屏被点掉时),窗口重放不双发;环境发放为
        # 确定发放 → rand=False(gain-chain.md §5),组名沿 sim:env 与
        # 环境金同窗。
        discharge_due_item_grants(self.gs, plane=plane, round_num=r,
                                  rand=False, sig=logic_sig('sim:env'))
        # 环境倒计时件到点开盒(T-34 命运礼物;设计 = T-34 设计稿 §2.4,
        # 迭代 2026-09-23-invest-effects-calc):同一收尾点继承窗口幂等守卫
        #(窗口重放不双发);开盒 = 确定事件非采样 → rand=False,
        # sig 组名沿 sim:env 与定时道具发放同窗。
        discharge_due_item_opens(self.gs, rand=False,
                                 sig=logic_sig('sim:env'))
        # 策略位面开始发放检查(终身学习首例:「每个位面开始时,获得1个
        # 【星徽秘典】」族;位面段发放 = 状态副本落席,同收尾点继承窗口
        # 幂等守卫重放不双发;窗谓词 r==1 + 持卡谓词合成,kernel 侧零新
        # 域;确定发放 rand=False 沿族)
        check_strategy_plane_start_grants(self.gs, node_pos=(plane, r),
                                          sig=logic_sig('sim:strategy'))
        # 策略延时发放到点入栏(策略卡「N个节点后获得发放物」族,人才
        # 激励首例;与 offer 呈现效果条目并列独立域——本效果条目产出 = 状态副本发放写):
        # 同一收尾点继承窗口幂等守卫(重放不双发);递减点 = kernel 节点
        # 边界 tick(advance 尾段),动作上报/锚定补推两路径均先于本窗
        # 开——本 advance 递减到 0 的条目本窗发放 = 「第 N 个后继节点
        # 窗」读法落点。确定发放行 → rand=False(gain-chain.md §5);
        # 随机 choice-set 行(是钻石总会发光首例)发放效果条目内部采样并覆盖
        # rand=True,rng = 独立命名流 M26(采样消耗不与他流共享 → 同局
        # 其余随机事件流零移位,固定 seed 面只受状态副本值变化影响)。
        # 独立 sig 组名与环境 'sim:env' 区分(状态副本发放写非环境域,审计
        # 可分)。到点留证披露键按「先读后发」取到期卡名与选中物(发放
        # 原语效果串只载发放物不载卡名,采样行掷点结果只回传在效果串
        # 内);注册表查行失败的防御条目由原语保留不弹除,披露值以
        # '?' 标记发放物缺失。
        due_grants = tuple((str(e[0]), int(e[1])) for e in
                           (self.gs.pending_strategy_grants.value or ())
                           if int(e[1]) <= 0)
        if due_grants:
            grant_effects = discharge_due_strategy_grants(
                self.gs, rand=False,
                rng=stream_rng(self.seed,
                               f'M26/strategy-grant/p{plane}/r{r}'),
                sig=logic_sig('sim:strategy_grant'))
            # 披露「选中物」按到期序对位解析效果串(确定行串值 = 登记
            # 物,choice-set 行串值 = 掷点结果);仅注册表漂移条目无串
            # (防御支)回退 '?'——choice 行 item='' 空值同以 '?' 标记,
            # 不披露空。
            _fired = [fx[len('delayed_grant:'):].split('(placed=')[0]
                      for fx in grant_effects]
            for _idx, (_name, _rem) in enumerate(due_grants):
                _spec = STRATEGY_DELAYED_GRANTS.get(_name)
                if _idx < len(_fired):
                    _item = _fired[_idx]
                elif _spec is not None:
                    _item = _spec.item or '?'
                else:
                    _item = '?'
                self.disclosures[STRATEGY_DELAYED_GRANT_FIRED] = (
                    f'{_name}@{plane}-{r}:{_item}')
        # 首领节点条件发放(劳务派遣合同分支2;条件单一源 = kernel
        # check_env_boss_grants):进窗事实点在窗口幂等守卫内(重放不双发),
        # done boss 键短路兜第二层。流键 M21 沿 M05/M18/M20 编号续,
        # 采样即状态副本里的值;sig 与环境金/定时道具发放同组同窗。kind =
        # node_sequence_of(plane, seqs)[r-1](上窗已算),坐标 (plane, r) =
        # 窗口幂等守卫键现值,直传入参零转换。
        if kind == 'boss':
            check_env_boss_grants(self.gs, node_pos=(plane, r),
                                  rng=stream_rng(self.seed,
                                                 f'M21/env-boss/p{plane}/r{r}'),
                                  sig=logic_sig('sim:env'))
        # 策略 boss 金效果条目(特战资金系):进 boss 节点窗发持卡聚合值,独立
        # 观察笔(evidence/sig 与收入笔分键)——轮首收入三分量账
        #(IncomeApplied.total = 该笔金增量)对账关系保持纯净,禁并入
        # 收入写。缺口来源:实机进 boss 节点真发聚合值,sim 状态副本自持账
        # 无观察可兜,不发即持卡局金系统性偏低。与劳务派遣合同的角色
        # 发放效果条目同段收尾(定时道具后、商店全刷前;两条效果条目互不读对方字段,
        # 先后无行为差,同段为收尾序单一)。承载方式 = 「调用方聚合
        # 单列」过渡形态(round_start_income docstring 预留的两承载方式
        # 之一),T1b 定夺后若选分量扩参,本效果条目随迁移合并进收入签名。
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
        # 策略尾款金效果条目(尾款交付):进入「最后一个补给阶段」节点窗发持卡
        # 聚合值——触发器 = **序列位置基准**((位面,轮) == 展平全序列最末
        # supply 位,整局一次;单一源 = final_supply_pos 场字段现值派生,
        # 修饰局零特判),与 boss 效果条目的节点类型触发器不同形态,不套其判定
        # 代码。独立观察笔(evidence/sig 与收入笔分键)——轮首收入三分量
        # 账(IncomeApplied.total = 该笔金增量)对账关系保持纯净,禁并入
        # 收入写;supply 支收入 = base+息照发,与本卡金平行分账。缺口来
        # 源与 live 零写金裁定同 boss 金效果条目(sim 状态副本自持账无观察可兜)。
        # 同段邻位收尾(boss 金效果条目之后、商店全刷前;两条效果条目互不读对方字段,
        # 先后无行为差,同段为收尾序单一)。零值零写;幂等复用窗口守卫
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
        # 环境直发策略取卡插入位置(T-46 策略大师数量分支;设计 = T-46 定稿
        # §2.2(e)):进窗事实点在窗口幂等守卫内(重放不双发,定时道具/
        # 开盒/boss 先例位);禁置 _node_window_target_base(纯判定契约)
        # 与 _present_offer_or_node_screen(幂等守卫区段外,resume 复走
        # 双发面)。direct 插入位置查询 = kernel ENV_POOL_REWRITE 单一源
        #(表外环境 get None = 无直发的合法语义,登记残缺归评审把关,
        # 空条目闸已随 2026-10-28 校验治理移除);当前节点 ==
        # extra_strategy_grant_node → 直接经获得链
        # 发一张随机投资策略,不开 offer 无选卡屏(用户裁定 2026-10-26),
        # 发放后照常进该节点正常流程;到手名并入 excluded_invest(维持
        # 「本局已出过全部选项名」累计去重契约,漏并入 = 已拥有策略可再入
        # 未来 offer 池,同名跳写 + 同卡二次发放面被直发分支重开)。直发到手
        # 即触发金币分支(同链自动,含本张口径下首张直发即 2 金)。调用形态沿
        # 现役直调先例 _on_invest_picked:session=None(登记分支跳过、状态容器写
        # 照常)/rand=False(确定发放)/sig 与环境金/定时道具发放同组
        # sim:env;流键 M23 沿 M21/M22 编号续,采样即状态副本里的值;样本 '' =
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
                # 直发到手即判随机策略发放(远见效果条目②插入位置 2;获得链调用后
                # 就地判命中即掷——直发 = 非拾取路径,门单挂拾取拍会把
                # 效果条目②迟滞到下一拾取拍,违「获得时点」语义;与拾取落地
                # 拍共用 _fire_strategy_random_grants 一门,exactly-once
                # 由已掷源名集合保证)。
                self._fire_strategy_random_grants(plane=plane, r=r)
        # 策略卡每节点绑定角色复制发放效果条目(「每次进入新节点时,获得1星的
        # 该角色,补给后额外获得2个」族,价值投资·金首例):进窗事实点在
        # 窗口幂等守卫内(重放不双发),kernel 检查函数单一源
        # check_strategy_node_char_grants(持卡 ∩ 绑定域驱动,未持卡零
        # 写)。与同段多条效果条目邻位收尾(定时道具/开盒/boss 发放/boss 金/尾款
        # 金/直发取卡;互不读对方字段,先后无行为差,同段为收尾序单一)
        # ——插入位置在商店全刷前:「每次进入新节点时」= 本窗内最早段,复制
        # 单位先于本窗商店发牌落席。prev_kind 现值推导(调用方现算,不
        # 新增存储):同位面取前序位;r=1 跨位面取前位面序列末位(现役
        # 日程三位面末位恒 boss → 「补给后」跨位面不可达,分支为防御
        # 代码,节点改写环境扩册自动正确);P1r1 无前节点 = None(基础
        # 1 名照发)。零 rng 确定发放 → rand=False 语义由检查效果条目内定;
        # live 零写观察覆盖(实机复制单位由游戏自发入席,下一备战帧
        # bench 整表观察覆盖);sig 组名 'sim:strategy'(策略状态副本发放
        # 家族,与延时发放 'sim:strategy_grant' 分组,本效果条目零采样)。
        _seqs = self.gs.node_seq_by_plane.value
        _cur_seq = node_sequence_of(plane, _seqs)
        if r >= 2:
            _prev_kind: str | None = _cur_seq[r - 2]
        elif plane >= 2:
            _prev_kind = node_sequence_of(plane - 1, _seqs)[-1]
        else:
            _prev_kind = None
        check_strategy_node_char_grants(self.gs, prev_kind=_prev_kind,
                                        sig=logic_sig('sim:strategy'))
        # 策略卡羁绊条件节点窗交付拍(不要小看我们的羁绊 id 200901 首例;
        # 触发-发放两拍制的发放拍,武装拍 = 结算效果条目 check_strategy_bond_
        # battle_grants):进窗事实点在窗口幂等守卫内(重放不双发),武装
        # 在场即采样交付——desc「进入节点时获得」= 本窗内最早段,发放物
        # 先于本窗商店发牌落位。kernel 检查函数单一源 discharge_strategy_
        # bond_battle_grants(armed 非 True 短路,未武装局零写);不按
        # kind 分叉(任意节点窗开都查武装——武装事实已由结算拍锚定,窗
        # 拍零条件);与同段多条效果条目邻位收尾(定时道具/开盒/boss 发放/boss 金/
        # 尾款金/直发取卡/node_char;互不读对方字段,先后无行为差,同段
        # 为收尾序单一);sig = logic_sig('sim:strategy') 沿策略战后发放
        # 效果条目同组;rng = 独立子流键 M13/{p}/{r}/strategy-bond(策略战后
        # 发放族子键式沿 'ins'/'boss-grant' 先例,装备采样专用禁复用 M13
        # 主流实例——独立子流 = 同 seed 其他流零扰动);幂等零新增守卫 =
        # 窗口幂等守卫,零新增;返回值忽略(无回调面);live 零写观察覆盖
        # (装备入栏有画面真值可读)。
        discharge_strategy_bond_battle_grants(
            self.gs, rng=stream_rng(self.seed,
                                    f'M13/{plane}/{r}/strategy-bond'),
            sig=logic_sig('sim:strategy'),
            producer=GAIN_CHAIN_PRODUCER)
        # 策略卡空仓经验效果条目(「进入新节点时，如果物品栏和备战席没有任何装备
        # (消耗品除外)，则获得2经验值」族,空仓首例):进窗事实点在窗口幂等
        # 守卫内(重放不双发),kernel 检查函数单一源
        # check_strategy_empty_equip_xp(纯读零写,未持卡/非空仓零写,零 done
        # 一次性标志位——卡面无「首次」限定,每节点窗可重复)。与同段多条效果条目邻位收尾
        #(定时道具/开盒/延时发放/boss 发放/boss 金/尾款金/直发取卡/
        # node_char/羁绊交付;同段为收尾序单一——邻位 ≠ 互不影响,对账见下)。
        # 前置效果条目装备域写端对账(本判定读 gs.equips,前置写端产出是否计入
        # 本窗谓词输入由相对序决定):①延时发放两行(「好运令牌·银」工具
        # 类/「是钻石总会发光」红钻蓝钻特殊类)发放物恰全落消耗品判据词表
        # {工具, 特殊} → 对谓词透明;②羁绊交付效果条目交付的随机星徽(非消耗品
        # 装备)与③直发取卡效果条目经获得链可发的新卡随机装备效果条目(环境改写条件
        # 触发)均为装备域写端且位于本插入位置前——现序下其产出计入本窗谓词
        # 输入(双持武装局每窗星徽先入栏,空仓恒判 0)。与②③的相对序
        # 官方无定论 = 判读申报制辖域,现位申报:羁绊交付后、商店全刷前
        #(证伪路径 = 实机双持武装局 XP 发放观察,证伪则改序重申报)。
        # 插入位置钉在商店全刷前:
        # XP 输出与同窗发牌有真实耦合(全刷直读 gs.level 取发牌概率),
        # 先写 = 本窗发牌分布按升级后等级,与卡面「进入新节点时…获得」的
        # 即时到账语义一致(顺序非无关,禁以后写形态表述)。live 零写观察
        # 覆盖(实机 XP 由游戏自算自显,经验条观察链 read_xp_progress 覆盖;
        # live 不评估条件——备战席单位穿戴无观察通道,结构性边界非缺口)。
        # XP 状态副本写与节点经验/即时经验同域同组(sig 'sim:xp'),evidence
        # 独立笔 'xp:empty_slot' 分账;零 rng 确定发放;level/xp 未观察 =
        # 零写留待观察覆盖,禁猜(apply_node_xp 同形态)。
        empty_xp = check_strategy_empty_equip_xp(self.gs)
        if empty_xp > 0:
            settle_xp_observe(self.gs, empty_xp,
                              sig=obs_sig(group_id='sim:xp'),
                              evidence=sim_evidence('xp:empty_slot'))
        # 策略卡备战席计数经验效果条目(「节点开始时，如果备战席角色小于等于4名，
        # 则获得3经验」族,人才空洞 id 202601 首例):进窗事实点在窗口幂等
        # 守卫内(重放不双发),kernel 检查函数单一源
        # check_strategy_bench_count_xp(纯读零写,未持卡/条件不满足零写,
        # 零 done 一次性标志位——卡面无「首次」限定,每节点窗可重复)。与同段多条效果条目邻位
        # 收尾(定时道具/开盒/延时发放/boss 发放/boss 金/尾款金/直发取卡/
        # node_char/羁绊交付/空仓;同段为收尾序单一——邻位 ≠ 互不影响,
        # 对账见下)。前置效果条目本卡谓词输入域(bench 单位数)写端对账:计数
        # 口径 = bench_units_of 仅单位槽(占位件/空槽不计,desc「角色」
        # 文义直读,判读申报制非定论);**node_char 复制效果条目写 bench 单位且
        # 位于本插入位置前——现序下其复制单位计入本窗 ≤4 判定**(与空仓效果条目
        # 「互不读对方字段、互序无关」不同:本卡谓词输入域恰是 node_char
        # 的写入域,相对序敏感面)。与 node_char 的相对序官方无定论 =
        # 判读申报制辖域,现位申报:node_char 之后、商店全刷前(证伪路径
        # = 实机双持价值投资族 + 席内单位 ≤4 局 XP 发放观察,证伪则改序
        # 重申报)。插入位置钉在商店全刷前:XP 输出与同窗发牌有真实耦合(全刷
        # 直读 gs.level 取发牌概率),先写 = 本窗发牌分布按升级后等级,
        # 与卡面「节点开始时…获得」的即时到账语义一致(顺序非无关,禁以
        # 后写形态表述)。live 零写观察覆盖(实机 XP 由游戏自算自显,经验
        # 条观察链 read_xp_progress 覆盖;live 不评估条件——备战席单位计数
        # live 观察通道已登记〔read_bench_view〕可对账,对账义务归采集批,
        # 零写义务不变)。XP 状态副本写与节点经验/即时经验同域同组
        # (sig 'sim:xp'),evidence 独立笔 'xp:bench_count' 分账;零 rng
        # 确定发放;level/xp 未观察 = 零写留待观察覆盖,禁猜
        # (apply_node_xp 同形态)。
        bench_xp = check_strategy_bench_count_xp(self.gs)
        if bench_xp > 0:
            settle_xp_observe(self.gs, bench_xp,
                              sig=obs_sig(group_id='sim:xp'),
                              evidence=sim_evidence('xp:bench_count'))
        # 策略卡装备计数经验效果条目(「每拥有一件【白昼装备】以及其原型装备，
        # 在进入新节点时就获得1点经验」族,赞美太阳 id 252401 首例):进窗
        # 事实点在窗口幂等守卫内(重放不双发),kernel 检查函数单一源
        # check_strategy_equip_count_xp(纯读零写,未持卡/零持有零写,零
        # done 一次性标志位——卡面无「首次」限定,每节点窗可重复)。与同段多条效果条目邻位
        # 收尾(定时道具/开盒/延时发放/boss 发放/boss 金/尾款金/直发取卡/
        # node_char/羁绊交付/空仓/备战席计数;同段为收尾序单一——邻位 ≠
        # 互不影响,对账见下)。前置效果条目本卡谓词输入域(装备库存与穿戴)写端
        # 对账:空仓效果条目零装备域写(空仓守卫恰要求物品栏无非消耗品);羁绊
        # 交付效果条目/直发取卡效果条目/延时发放效果条目位于本插入位置前且可写装备域(随机星徽/
        # 新卡随机装备/延时具名装备)——现序下其产出计入本窗件数(先入栏
        # 后计数 = 「拥有」进窗快照口径)。相对序官方无定论 = 判读申报制
        # 辖域,现位申报:备战席计数效果条目后、商店全刷前(证伪路径 = 实机持卡
        # 局同窗装备入栏 XP 发放观察,证伪则改序重申报)。插入位置钉在商店全刷
        # 前:XP 输出与同窗发牌有真实耦合(全刷直读 gs.level 取发牌概率),
        # 先写 = 本窗发牌分布按升级后等级,与卡面「进入新节点时…获得」的
        # 即时到账语义一致(顺序非无关,禁以后写形态表述)。live 零写观察
        # 覆盖(实机 XP 由游戏自算自显,经验条观察链 read_xp_progress 覆盖;
        # live 不评估条件——四源持有观察通道已登记〔库存/穿戴〕可对账,对账
        # 义务归采集批,零写义务不变)。XP 状态副本写与节点经验/即时经验同域
        # 同组(sig 'sim:xp'),evidence 独立笔 'xp:equip_count' 分账;零 rng
        # 确定发放;level/xp 未观察 = 零写留待观察覆盖,禁猜
        # (apply_node_xp 同形态)。
        equip_xp = check_strategy_equip_count_xp(self.gs)
        if equip_xp > 0:
            settle_xp_observe(self.gs, equip_xp,
                              sig=obs_sig(group_id='sim:xp'),
                              evidence=sim_evidence('xp:equip_count'))
        # 策略卡赠礼条件双效果条目(迷之旅人 id 253601 首例;「激活4【巡海游侠】
        # 时…获得…2星【黄泉】(携【星间旅人星徽】)」= 羁绊人数条件效果条目,
        # 任意节点入窗评估;「进入下一个奖励节点时，获得【波提欧】」=
        # 节点类型条件效果条目):进窗事实点在窗口幂等守卫内(重放不双发),kernel
        # 检查函数单一源 check_strategy_gift_grants(持卡 ∩ 双登记表驱动,
        # 未持卡零写;一次性封账 = strategy_grants_done 逐效果条目复合键,落位才
        # 一次性标志位拒落自愈)。与同段多条效果条目邻位收尾(定时道具/开盒/延时发放/boss
        # 发放/boss 金/尾款金/直发取卡/node_char/羁绊交付/空仓/备战席计数
        # /装备计数;同段为收尾序单一——邻位 ≠ 互不影响,对账见下)。前置效果条目
        # 本卡效果条目1 谓词输入域(deployed)写端对账:直发取卡效果条目位于本插入位置前且
        # 经获得链效果体可写板面(板面重写族),现序下其产出计入本窗羁绊
        # 计数(先变板面后计数 = 进窗快照口径);相对序官方无定论 = 判读
        # 申报制辖域,现位申报:装备计数 XP 效果条目后、商店全刷前(证伪路径 =
        # 实机持卡局直发取卡改板面同窗计数观察,证伪则改序重申报);其余
        # 前置效果条目写域(金/XP/bench/equips)与本卡计数零交集零敏感。效果条目2 发放
        # 物先于本窗商店发牌落席(「进入下一个奖励节点时」= 本窗内最早段,
        # 与 node_char 复制效果条目同向)。kind = 窗内已算变量直传零转换(节点序列
        # 真值,修饰局天然跟随)。零 rng 采样(角色具名确定发放;徽效果条目
        # rand=True 系随机态认知通道非采样,无掷序消费);live 零写观察覆盖
        #(角色落席/装备入栏有画面真值可读,实机局不接本通道);sig 组名
        # 'sim:strategy' 沿策略战后发放效果条目同组;幂等零新增守卫 = 窗口幂等
        # 守卫 + done 一次性标志位双层;返回值忽略(无回调面)。
        check_strategy_gift_grants(self.gs, node_kind=kind,
                                   sig=logic_sig('sim:strategy'))
        # 条件 XP 族第 4 形(被动收入 id 300601;备战席左一角色基础费用
        # 动态量,量形 = 单角色属性直读族内首例)。现位申报:gift 双效果条目后、
        # 商店全刷前(证伪路径 = 实机持卡局左一角色与本窗商店发牌费用档
        # 耦合观察,证伪则改序重申报);XP 状态副本写与节点经验/即时经验同域
        # 同组(sig 'sim:xp'),evidence 独立笔 'xp:bench_left_cost' 分账;
        # 零 rng 确定发放;level/xp 未观察 = 零写留待观察覆盖,禁猜
        # (apply_node_xp 同形态;cost=0/无单位零发放门在判定端)。
        left_cost_xp = check_strategy_bench_left_cost_xp(self.gs)
        if left_cost_xp > 0:
            settle_xp_observe(self.gs, left_cost_xp,
                              sig=obs_sig(group_id='sim:xp'),
                              evidence=sim_evidence('xp:bench_left_cost'))
        # 条件 XP 族外唯一静态量通道(买断制 id 300901 xp_per_node=4;
        # 聚合薄读 strategy_xp_per_node_of 单一源,静态量禁动态计数挂此
        # ——条件 XP 族走各自 check_* 纯判定)。现位申报:被动收入效果条目后、
        # 商店全刷前(证伪路径 = 实机持卡局同窗发牌等级耦合观察,证伪则
        # 改序重申报)。XP 状态副本写与节点经验/即时经验同域同组
        # (sig 'sim:xp'),evidence 独立笔 'xp:strategy_per_node' 分账;
        # 零 rng 确定发放;level/xp 未观察 = 零写留待观察覆盖,禁猜
        # (apply_node_xp 同形态)。
        strategy_xp = strategy_xp_per_node_of(self.gs)
        if strategy_xp > 0:
            settle_xp_observe(self.gs, strategy_xp,
                              sig=obs_sig(group_id='sim:xp'),
                              evidence=sim_evidence('xp:strategy_per_node'))
        # 节点条件晶矿发放(彩虹矿 id 301201 首例;「进入新的奖励节点时，
        # 获得1个晶矿」触发器单一源 = kernel check_strategy_reward_ore_grants,
        # 白名单表 STRATEGY_REWARD_ORE_GRANTS 驱动)。现位申报:买断制静态
        # XP 效果条目后、商店全刷前(证伪路径 = 实机持卡局晶矿呈现时点与本窗发牌
        # 耦合观察,证伪则改序重申报)。窗内 transient 承载(镜像
        # _piggy_income_snap 先例),呈现段由 _present_node_screen 补点;
        # 返回值忽略(无回调面);live 零写观察覆盖。
        self._strategy_reward_ore_pending = \
            check_strategy_reward_ore_grants(self.gs, node_kind=kind,
                                             sig=logic_sig('sim:strategy'))
        # 策略位面-节点合取条件写状态副本发放(盗用身份 id 352401 首例;「进入第二
        # 位面的首领节点时…获得…【火花】」触发器单一源 = kernel
        # check_strategy_plane_boss_grants,白名单表 STRATEGY_PLANE_BOSS_
        # GRANTS 驱动)。进窗事实点在窗口幂等守卫内(重放不双发),done 复合
        # 键一次性标志位('<卡名>#p2_boss')兜第二层;位面/kind 合取函数内
        # 现读(场字段现值,修饰局天然正确,零坐标猜测)。现位申报:晶矿效果
        # 条目后、商店全刷前——前置效果条目与本效果条目零交互(谓词输入域 =
        # 持卡/done/日程/bench None 门,不读 bench 内容与金/XP/equips;写入域
        # = bench 落位 + done,下游至商店全刷无 bench 谓词消费,证伪路径 =
        # 实机持卡局同窗发放物呈现时点观察,证伪则改序重申报)。零 rng 确定
        # 发放;sig 组名 'sim:strategy'(策略状态副本发放家族,与 sim:env
        # 分组);返回值忽略(无回调面);live 零写观察覆盖(角色落席有画面
        # 真值可读,实机局不接本通道,写状态副本的发放经观察对账兜底)。
        check_strategy_plane_boss_grants(self.gs, node_pos=(plane, r),
                                         sig=logic_sig('sim:strategy'))
        # 装备到期消失(临时工合约 id 301901 效果条目2;「进入下个节点时，所有
        # 未使用的【员工投影仪】都会消失」触发器单一源 = kernel
        # check_strategy_equip_expiry,白名单表驱动)。现位申报:晶矿效果条目后、
        # 商店全刷前(证伪路径 = 实机持卡局装备消失时点与本窗发牌耦合观察,
        # 证伪则改序重申报)。移除写 = write_logic 独立笔(evidence
        # strategy_equip_expiry:带卡名段);一次性标志位与移除同拍(kernel 函数内落一次性标志位,
        # 本侧消费返回集执行移除写);移除集空 = 零写留待观察。
        expired = check_strategy_equip_expiry(self.gs,
                                              sig=logic_sig('sim:strategy'))
        if expired:
            kept = [e for e in (self.gs.equips.value or [])
                    if e not in expired]
            self.gs.write_logic(self.gs.equips, kept,
                                produced_by='SimBackend:equip_expiry',
                                evidence='strategy_equip_expiry:expiry',
                                sig=logic_sig('sim:strategy'))
        # —— 策略卡周期离场(佩佩客串 id 331001 首例;接入调用点 = 装备
        # 到期效果条目之后、商店全刷前,节点窗收尾序并列——「进入5个
        # 节点后」= 拿卡后第 5 后继节点窗收尾触发,倒计时 tick 挂节点
        # 推进边界 advanced 闸)。条件单一源 = kernel
        # discharge_due_kechuan_leaves(队列弹除 + 本卡佩佩 uid 过滤移除
        # + 装备走 gain_equipment 原语入栏 + 计数域清账);sig =
        # logic_sig('sim:strategy') 沿策略战后发放效果条目同组;幂等零
        # 新增守卫 = 窗口幂等守卫 + 队列弹除即消费(条目移除);返回值
        # 忽略(无回调面);live 零写观察覆盖(离场为游戏侧自发)。
        discharge_due_kechuan_leaves(self.gs,
                                     sig=logic_sig('sim:strategy'))
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
        # 位面首节点窗策略域强制店改写效果条目(M05 全刷之后后置覆盖;公司严选
        # 首例。「每个位面开始时…开启商店」)。后置覆盖与「替换 M05」观察
        # 等价(玩家所见最终店面同为强制面),差异仅 rng 消耗与 journal
        # 行数——取改动面最小形(基线 M05 块内不加特判分支)。锁交互沿
        # 间谍效果条目形(无锁守卫;效果触发的商店写不入 M05 自动全刷的锁
        # 豁免域,真值待实采与间谍卡共享同一实采裁决,零新增键)。
        # journal 形态:位面首节点窗 shop 域恰两行 = M05 deal 行 + 本覆盖行
        #(evidence 可辨 shop:deal / shop:rewrite:plane)——复盘/对账工具
        # 按「每节点窗一行 deal」假设会误报,防误读注记随披露计数落
        # :meth:`_write_forced_shop_rewrite`。
        if r == 1:
            self._apply_strategy_plane_start_shop_rewrite(plane, r)
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
            # 远见改写分支(效果条目③「后续的投资策略节点改为获得随机1个棱彩
            # 投资策略（无法刷新）」;判定名 = 注册面唯一挂值基准——
            # STRATEGY_ECONOMY['远见'].future_quality_upgrade 全注册表
            # 唯一挂值,枚举即收敛硬编码沿 ENV_AFFIX_DISABLE_ENV 先例,
            # 单卡零复用面不入登记表):触发 = membership 状态容器现值,无需
            # ordinal 追踪——远见只能于 offer 槽被拾取,自身槽呈现先于
            # 入列天然不命中,后继槽 membership 已真(联席额外槽同判,
            # 其效果原文自称「投资策略三选一」= 投资策略节点,offer_slots
            # 唯一入口自动覆盖零特判)。单棱彩候选 = 单卡采样器单一源复用
            #(排除集 = 已出选项全集,棱彩池 123 名对排除集 ~12 名上界,
            # 池空结构性不可达);'' 防御分支 = 落回常规三选一路径(正常
            # 局不可达)。位置 = env 改写向量计算之前、命中即短路:改写
            # 对象层级 = 获得行为本体(三选一 → 随机单发)> 槽位品质
            #(env 改写所附着的「三选一」形态已被移除),卡文「改为」
            # 绝对时语;冲突证伪通道 = FORESIGHT_ENV_REWRITE_PRIORITY。
            # pick_ordinal 已照常 +1(env 侧 rewrite_picks/槽位向量型的
            # 全局序语义保持连续,改写槽占用序位的事实如实申报——时代族
            # rewrite_picks 命中判据 = 序位非内容,不受远见存在影响)。
            if '远见' in (self.gs.active_strategies.value or []):
                rolled = sample_strategy_card(
                    stream_rng(self.seed,
                               f'M11/offer/p{plane}/r{r}/foresight'),
                    self.excluded_invest, forced_quality='棱彩')
                if rolled:
                    if rewrite_slot_qualities_for_pick(
                            str(active_env or ''),
                            self._invest_pick_ordinal) is not None:
                        self.disclosures.setdefault(
                            FORESIGHT_ENV_REWRITE_PRIORITY,
                            'foresight_wins')
                    self.disclosures.setdefault(
                        FORESIGHT_REWRITE_SCREEN_SHAPE,
                        'single_candidate_screen_sim_v0')
                    self._window_resume = 'node'
                    self._announce_screen(SCREEN_INVEST_STRATEGY)
                    self._screen = SCREEN_INVEST_STRATEGY
                    self._sub = ''
                    # 十一条效果条目的呈现一次性标志位全量照置(呈现即置一次性标志位口径 = 固定日程分支
                    # 同款;改写槽拾取走常规 pick 链,落地拍各效果条目消费依赖
                    # 一次性标志位已置位,防重放窗同界)。
                    self._strategy_pick_xp_latch = True
                    self._strategy_pick_streak_latch = True
                    self._strategy_pick_sell_deal_latch = True
                    self._strategy_pick_hp_latch = True
                    self._strategy_pick_gold_next_nodes_latch = True
                    self._strategy_pick_plane_refire_latch = True
                    self._strategy_pick_hyperemit_drain_latch = True
                    self._strategy_pick_recruit_drain_latch = True
                    self._strategy_pick_diamond_latch = True
                    self._strategy_pick_hp_loss_gold_latch = True
                    self._strategy_pick_swap_latch = True
                    # 刷新授权簿记:「无法刷新」卡面直读——固定日程槽由
                    # 本分支压 False(fields.md「另有远见改写=0」已写进代码),
                    # 联席槽本就 False;槽向量簿记同步清零(刷新重掷效果条目已被
                    # _offer_refreshable 闸死,向量无消费位)。
                    self._offer_refreshable = False
                    self._offer_forced_slots = ()
                    self._offer_refresh_seq = 0
                    report_screen_invest_strategy_obs(
                        self.gs,
                        CwScreenInvestStrategyObs(
                            entry_ok=True,
                            options=[(rolled, 10, 10)],
                            refresh_slots=[]))
                    return
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
            # 策略 offer 呈现即置即时经验效果条目一次性标志位(落地拍消费,防重放)。
            self._strategy_pick_xp_latch = True
            # 连胜置位效果条目一次性标志位同点置位(独立一次性标志位;复呈现再置位 = xp 效果条目既有
            # 形状,重放防护窗以「呈现→落地」为界,复呈现后到达的重放
            # 属上游重试 bug 面)。
            self._strategy_pick_streak_latch = True
            # 出售发牌效果条目一次性标志位同点置位(三条效果条目独立一次性标志位同形;防重放窗同界)。
            self._strategy_pick_sell_deal_latch = True
            # 即时生命效果条目一次性标志位同点置位(四条效果条目独立一次性标志位同形;防重放窗同界)。
            self._strategy_pick_hp_latch = True
            # 分期金初始化效果条目一次性标志位同点置位(五条效果条目独立一次性标志位同形;防重放窗同界)。
            self._strategy_pick_gold_next_nodes_latch = True
            # 位面段补发效果条目一次性标志位同点置位(六条效果条目独立一次性标志位同形;防重放窗同界)。
            self._strategy_pick_plane_refire_latch = True
            # 超发货币负债效果条目一次性标志位同点置位(七条效果条目独立一次性标志位同形;防重放窗同界)。
            self._strategy_pick_hyperemit_drain_latch = True
            # 大扩招扣金负效果条目一次性标志位同点置位(八条效果条目独立一次性标志位同形;防重放窗同界)。
            self._strategy_pick_recruit_drain_latch = True
            # 宝钻状态副本联动效果条目一次性标志位同点置位(九条效果条目独立一次性标志位同形;防重放窗同界)。
            self._strategy_pick_diamond_latch = True
            # 已损血衍生金效果条目一次性标志位同点置位(十条效果条目独立一次性标志位同形;防重放窗同界)。
            self._strategy_pick_hp_loss_gold_latch = True
            # 获得链交换效果条目一次性标志位同点置位(十一条效果条目独立一次性标志位同形;防重放窗同界,
            # 重放会凭空多配一行轨迹破写流↔轨迹全序同构)。
            self._strategy_pick_swap_latch = True
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
        """策略延时 offer 窗首到期呈现(呈现效果条目双插入位置之一,sim 专用;
        策略卡「N个节点后一次定品质三选一」通道的窗首消费端,kernel
        不 import 本模块 = live 不对称的模块边界):读
        ``pending_strategy_offers`` 取首个 remaining <= 0 条目(登记序
        = 确定性)。delay_nodes=0 立即效果条目不辖本插入位置——拿卡拍已由
        ``_on_invest_picked`` 尾段立即效果条目消费(双插入位置分立,弹除即互斥)。

        优先序 = 固定日程/联席槽 > 队列:槽在场 = 本窗让路,到点
        条目悬置顺延(deferred 披露;顺延不悬空——到点判定「到了及以后
        都算」,下一空闲窗必呈现);本窗已呈现一次的余者同式顺延
        (window_cap 披露)。呈现即消费(队列弹除与呈现同拍原子,呈现后
        选卡经既有落地通道,防重入双呈现;呈现后选卡失败 = 动作域异常,
        队列不回滚,状态副本偏穷一份 offer,有界一次一张)。呈现侧副作用 =
        现役固定日程分支全量同款延伸(呈现体 :meth:
        `_present_extra_offer_screen` 两个插入位置共用)。定品质 = 槽向量直取
        登记品质池(观察面 = 候选全目标品质;环境品质改写不作用于本
        通道——改写判据只挂固定日程分支,品质恒 = 登记值)。rng 流键
        独立分域(窗首键无 pick 段,与拿卡拍立即效果条目分键),重放稳定。
        返回是否呈现。"""
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
        # 窗首通道辖延时效果条目:呈现效果条目 = 登记元组内最大节拍效果条目(delay_nodes=0
        # 立即效果条目由拿卡拍插入位置消费;到点条目 remaining 随 tick 递减,不可
        # 反推原节拍;同卡多效果条目品质+授权同值时条目序无歧义,单条效果条目卡即唯一效果条目)。
        spec = max(STRATEGY_DELAYED_OFFERS[name],
                   key=lambda leg: leg.delay_nodes)
        if due[1:]:
            self.disclosures.setdefault(
                STRATEGY_DELAYED_OFFER_DEFERRED,
                f'window_cap@{len(due) - 1}')
        self._present_extra_offer_screen(
            name, spec, queue=queue, idx=_idx,
            rng_key=f'M11/offer-extra/p{plane}/r{r}',
            evidence=f'present_due_extra_offer:{name}',
            disclosure_key=STRATEGY_DELAYED_OFFER_FIRED)
        return True

    def _present_extra_offer_screen(self, name: str,
                                    spec: StrategyDelayedOffer, *,
                                    queue: tuple, idx: int,
                                    rng_key: str, evidence: str,
                                    disclosure_key: str) -> None:
        """extra offer 呈现体(窗首到期效果条目与拿卡拍立即效果条目两个插入位置共用;
        白银投资批自固定日程呈现分支抽形):

        - 序位计数照增(「一切策略三选一呈现都计数」口径,联席额外槽
          先例)、八条效果条目呈现一次性标志位全量照置(固定日程分支同款「呈现即置一次性标志位」
          口径,落地拍消费防重放);
        - 刷新授权逐卡按登记 refresh_count 呈现(卡面「选择有3次刷新
          机会」直读,sim 与实机「计数印在卡上」同形;0 = 不可刷 =
          期货系卡面直读,空授权 = op 闸无授权两侧零分支承载)——
          授权数值单一源 = 登记表 refresh_count,本处零字面量;品质
          承诺跨刷新保持 = 槽向量簿记取登记品质(重掷品质恒 = 登记池);
          实机对账面 = 实机局该 offer 刷新钮读数对照(授权与实机同源
          卡面,零缺口申报键);
        - 弹除时机 = 呈现时(呈现即消费,防重入双呈现;呈现后选卡失败
          不回滚);env 品质改写不作用于本通道(品质恒 = 登记值)。

        [索引定义] idx = queue 队列下标(调用方进拍快照内的弹出位,
        恒稳快照值非执行期现读——呈现与弹除同拍原子);queue = 同拍
        快照(弹除取 keep = 快照去 idx 位)。"""
        plane, r = self._node_pos()
        self._invest_pick_ordinal += 1
        opts = sample_strategy_offer(
            stream_rng(self.seed, rng_key),
            self.excluded_invest,
            forced_slots=(spec.offer_quality,) * OFFER_CANDIDATES)
        keep = queue[:idx] + queue[idx + 1:]
        self.gs.write_logic(self.gs.pending_strategy_offers, keep,
                            produced_by='SimBackend',
                            evidence=evidence,
                            sig=logic_sig(group_id='sim:offer-extra'))
        self._window_resume = 'node'
        self._announce_screen(SCREEN_INVEST_STRATEGY)
        self._screen = SCREEN_INVEST_STRATEGY
        self._sub = ''
        # 呈现即置即时经验效果条目一次性标志位 + 连胜置位效果条目一次性标志位(固定日程分支同款「呈现即
        # 置一次性标志位」口径,落地拍消费防重放);出售发牌效果条目一次性标志位同形照置;即时生命
        # 效果条目一次性标志位同形照置;分期金初始化效果条目一次性标志位同形照置;位面段补发效果条目一次性标志位同形照置;
        # 超发货币负债效果条目一次性标志位同形照置;大扩招扣金负效果条目一次性标志位同形照置;宝钻状态副本
        # 联动效果条目一次性标志位同形照置;已损血衍生金效果条目一次性标志位同形照置;获得链交换效果条目一次性标志位同形
        # 照置。
        self._strategy_pick_xp_latch = True
        self._strategy_pick_streak_latch = True
        self._strategy_pick_sell_deal_latch = True
        self._strategy_pick_hp_latch = True
        self._strategy_pick_gold_next_nodes_latch = True
        self._strategy_pick_plane_refire_latch = True
        self._strategy_pick_hyperemit_drain_latch = True
        self._strategy_pick_recruit_drain_latch = True
        self._strategy_pick_diamond_latch = True
        self._strategy_pick_hp_loss_gold_latch = True
        self._strategy_pick_swap_latch = True
        # 刷新授权簿记(逐卡按登记 refresh_count;0 = 不可刷 = 空授权,
        # 槽向量簿记同步清零 = 无刷新窗语义)。
        refreshable = spec.refresh_count > 0
        self._offer_refreshable = refreshable
        self._offer_forced_slots = ((spec.offer_quality,) * OFFER_CANDIDATES
                                    if refreshable else ())
        self._offer_refresh_seq = 0
        refresh_slots = ([(spec.refresh_count, (i + 1) * 10, 20)
                          for i in range(len(opts))] if refreshable else [])
        report_screen_invest_strategy_obs(self.gs,
                                          CwScreenInvestStrategyObs(
                                              entry_ok=True,
                                              options=[
                                                  (n, (i + 1) * 10, 10)
                                                  for i, n in
                                                  enumerate(opts)],
                                              refresh_slots=refresh_slots))
        self.disclosures[disclosure_key] = f'{name}@{plane}-{r}'

    def _refresh_invest_strategy(self, slots: tuple[int, ...]) -> None:
        """投资策略屏逐卡刷新状态副本侧分支(2026-10-19 用户裁定「sim 与实机一致
        提供刷新次数」批;上报声明触发,同屏重呈现零转移)。

        逐槽:状态容器剩余口径闸(≤0 = 尽,防御性——op 侧 obs/状态容器双闸在前,
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
        """投资环境屏整组刷新状态副本侧分支(环境刷新 = 单全局钮整组重掷一次;
        上报声明触发,同屏重呈现零转移)。

        状态容器剩余闸(≤0/None = 尽,防御性——op 侧 obs+状态容器双闸在前)→
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
        # 面板矿 = 基准 8 矿 + 扑满环境占位增量(活跃环境查表扩尾,见
        # reward_ore_panel_points);len(panel) 入参使位面开局声明矿
        # 续接坐标随扩尾自动跟随。
        panel = (reward_ore_panel_points(
            str(self.gs.active_env.value or ''))
            if kind == 'reward' else ())
        reward_ore_extra = getattr(self, '_strategy_reward_ore_pending', 0) \
            if kind == 'reward' else 0
        extra_points = tuple(
            ('棱彩', 10 * (len(panel) + i + 1), 10, 10)
            for i in range(reward_ore_extra))
        points = panel + self._plane_start_declared_points(plane, len(panel)) \
            + extra_points
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
          ``ore_declared_expired#p{old}`` 留痕)——**金不再直发**,状态副本
          这一侧的金在点击声明矿兑现时入账(策略面估值消费
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

    def _apply_strategy_plane_start_xp(self, plane: int) -> None:
        """策略域位面开始 XP 效果条目(「现在以及每个位面开始时」族位面段 XP
        支;载体 = STRATEGY_ECONOMY.xp_per_plane,固定理财 4 首条目,
        字段分派非单卡特判;效果登记账本迭代辖域与 kernel 位面开始刷新
        桥 apply_effect_plane_start_grant 同域——刷新支 = kernel 推进边界
        拍、XP 支 = 本窗效果条目,双插入位置分工与即时经验效果条目 live 观察覆盖口径
        一致)。触发 = _begin_node_window 内 r==1(位面首节点窗;
        ``_window_begun_pos`` 窗口幂等守卫承接重放不双发,与
        _apply_env_plane_start 同窗同守卫)。数额 = 迭代账本鸭子类型读取(duck typing)合计
        (同持多卡求和单笔;XP 写入 = observe 状态副本笔,无 produced_by)。
        live 无本效果条目(本函数住 sim)——kernel 零 sim import,XP 状态副本真值
        live 归观察覆盖。状态容器缺读(None)= 本拍零写留待观察覆盖,禁猜;
        零值零写(未持卡零新增观察行)。"""
        total = 0
        for e in self.gs.effects.entries:
            n = int(getattr(e.spec.payload, 'xp_per_plane', 0) or 0)
            if n > 0:
                total += n
        if total <= 0:
            return
        settle_xp_observe(self.gs, total, sig=obs_sig(group_id='sim:xp'),
                          evidence=sim_evidence(f'xp:strategy_plane:p{plane}'))

    def _apply_strategy_plane_start_gold(self, plane: int) -> None:
        """策略域位面开始金效果条目(「现在及每个位面开始时」族位面段金支,
        公司严选 3 首条目,策略域位面周期金首例;载体 =
        EconomyEffect.gold_per_plane,注册表直读禁聚合——聚合字段集不含
        本字段,误走 = 静默零发放)。触发 = _begin_node_window 内 r==1,
        XP 支同窗邻位(位面首节点窗;``_window_begun_pos`` 窗口幂等守卫
        承接重放不双发)。写形 = 合计单笔 observe(同持多卡求和;金 = 状态副本
        真值,live 同拍零写观察覆盖,金面禁直写硬裁定在 live 侧)。状态容器
        金缺读(None)= 本拍零写留待观察覆盖,禁猜(env 直发形 None 视 0
        照写会伪造金绝对值假真值,不取——缺口面 = 观察覆盖前金效果条目静默,
        有意分道取 xp 形)。零值零写(未持卡零新增观察行)。"""
        total = 0
        for name in (self.gs.active_strategies.value or ()):
            eff = STRATEGY_ECONOMY.get(normalize_invest_name(str(name or '')))
            if eff is not None:
                total += eff.gold_per_plane
        if total <= 0:
            return
        gold_now = self.gs.gold.value
        if gold_now is None:
            return
        self.gs.observe(
            self.gs.gold, int(gold_now) + total,
            evidence=sim_evidence(f'strategy:plane_gold:p{plane}'),
            sig=obs_sig(group_id='sim:strategy'))

    def _apply_strategy_plane_start_shop_rewrite(self, plane: int,
                                                 r: int) -> None:
        """策略域位面开始强制店改写效果条目(M05 全刷后后置覆盖;「现在及每个
        位面开始时」族位面段改写支,公司严选 4 首条目)。辖域 = 持有表中
        命中 ``shop_rewrite_forced_cost>0`` 的卡(现役至多一张,逐卡独立
        笔;流键携卡名防同窗多卡撞流)。采样与写经共享助手
        :meth:`_write_forced_shop_rewrite`(kernel 强制采样器单源,商店
        发牌出口 = drawable_names)。"""
        for name in (self.gs.active_strategies.value or ()):
            canon = normalize_invest_name(str(name or ''))
            eff = STRATEGY_ECONOMY.get(canon)
            if eff is None or eff.shop_rewrite_forced_cost <= 0:
                continue
            self._write_forced_shop_rewrite(
                eff, canon,
                stream_key=f'M28/rewrite-plane/p{plane}r{r}:{canon}',
                tag=f'shop:rewrite:plane:p{plane}r{r}',
                counter_key='shop_rewrite_plane_count')

    def _write_forced_shop_rewrite(self, eff, canon: str, *,
                                   stream_key: str, tag: str,
                                   counter_key: str) -> None:
        """强制店改写采样与状态容器写(三触发拍共享助手:选卡 gain /
        位面 plane / 补发 refire;差异只在流键/evidence/计数键)。

        kernel 强制采样器单源(:func:`sample_shop_deal_forced`,费用档
        定死 + unique 去重);写 = gs.observe 直写(sim 状态副本真值,live
        同拍零写观察覆盖)。披露三计数(sim 私有簿记,键域:
        shop_rewrite_gain_count / shop_rewrite_plane_count /
        shop_rewrite_shortfall_count)= 两拍改写触发累计 / 桶不足 5 事件
        累计(事件口径,非缺槽数)。商店记录镜像 = 端口懒同步自动覆盖,
        零显式 sync(M22 间谍效果条目同形)。对账注记:位面首节点窗 shop 域
        恰两行(M05 deal + rewrite:plane),按「每节点窗一行 deal」假设
        的复盘/对账工具会误报。"""
        rng = stream_rng(self.seed, stream_key)
        payload = sample_shop_deal_forced(
            self.gs, rng, cost=int(eff.shop_rewrite_forced_cost),
            unique=bool(eff.shop_rewrite_forced_unique),
            level=int(self.gs.level.value or 3))
        self.gs.observe(self.gs.shop, payload,
                        evidence=sim_evidence(tag),
                        sig=obs_sig(group_id=f'sim:{tag}'))
        self.disclosures[counter_key] = \
            self.disclosures.get(counter_key, 0) + 1
        content = sum(1 for s in payload.cards if s.card is not None)
        if content < SHOP_SLOTS:
            self.disclosures['shop_rewrite_shortfall_count'] = \
                self.disclosures.get('shop_rewrite_shortfall_count', 0) + 1
            log.info('[cw-sim] 强制店改写短缺:%s 桶 %s 张/5 槽(%s)',
                     canon, content, tag)
        log.info('[cw-sim] 强制店改写:%s → 全店 %s 费 %s(%s)',
                 canon, eff.shop_rewrite_forced_cost,
                 '独特' if eff.shop_rewrite_forced_unique else '不去重', tag)

    def _apply_strategy_shop_rewrite_gain(self,
                                          new_names: Sequence[str]) -> None:
        """选卡拍强制店改写效果条目(「现在…开启一个由5个独特4费角色组成的
        商店」,公司严选 4 首条目)。辖域 = 本拍新获得表中命中
        ``shop_rewrite_forced_cost>0`` 的卡(现役至多一张,逐卡独立笔;
        流键携卡名防链式选卡同窗撞流)。「本拍新获得」限定 = 窗口起点
        快照差分(调用方消费后前滚),扫描式遍历持有表会在后续拿他卡时
        反复触发——卡面「现在」= 获得时点一次,无此语义。"""
        for name in new_names:
            canon = normalize_invest_name(str(name or ''))
            eff = STRATEGY_ECONOMY.get(canon)
            if eff is None or eff.shop_rewrite_forced_cost <= 0:
                continue
            plane, r = self._node_pos()
            self._write_forced_shop_rewrite(
                eff, canon,
                stream_key=f'M27/rewrite-gain/p{plane}r{r}:{canon}',
                tag=f'shop:rewrite:gain:p{plane}r{r}',
                counter_key='shop_rewrite_gain_count')

    def _apply_strategy_shop_rewrite_refire(self,
                                            new_names: Sequence[str]) -> None:
        """选卡拍位面段补发改写效果条目(用户裁定 2026-11-01 族级确定:中途拿
        卡判当前位面已开始 → 位面段〔+金 + 强制店改写〕登记拍全额补发,
        后续位面照常;公司严选位面段两条效果条目的补发改写支)。辖域 = 本拍新
        获得表中命中 ``shop_rewrite_forced_cost>0`` 的卡;独立流键与
        evidence(refire)——同拍「选卡改写 × 补发改写」双触发两条效果条目都发
        (固定理财族「两条效果条目都发」同判,journal 双行如实登记禁静默合并),
        共流键会使两条效果条目采出同一序列假同貌。node 缺席保守零补发(禁猜,
        金效果条目 :func:`apply_strategy_plane_refire_gold` 同判)。"""
        for name in new_names:
            canon = normalize_invest_name(str(name or ''))
            eff = STRATEGY_ECONOMY.get(canon)
            if eff is None or eff.shop_rewrite_forced_cost <= 0:
                continue
            plane, r = self._node_pos()
            self._write_forced_shop_rewrite(
                eff, canon,
                stream_key=f'M29/rewrite-refire/p{plane}r{r}:{canon}',
                tag=f'shop:rewrite:refire:p{plane}r{r}',
                counter_key='shop_rewrite_plane_count')

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
        (「选择后」即时);obs 渠道直写(与 live 敌方难度读数 OCR 同一状态容器域,
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
        # 难度豁免读法申报(远见在列时):现值读数 = 读法 A 自身豁免
        #(quality 分量不计远见棱彩 +6),读法依据与证伪通道随披露键
        #(宿主 = cw_investments;773 轮聚合对账对本分支系空载背书,
        # 对账对象 = 本局 settled 备战帧读数逐轮微分,归遥测批)。
        if '远见' in (self.gs.active_strategies.value or []):
            self.disclosures.setdefault(FORESIGHT_EXEMPTION_READING,
                                        'self_exempt_v0')
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
        # —— 败局修饰 hp 效果条目(嘴硬族首例;接入调用点 = 扑满豁免之后、损血实值
        # 基准/apply_hp_outcome 之前:hp_before 基准、结算环帧行与损血档位
        # 状态容器差分全部按修饰后损血记账,修饰效果条目插入序与各消费效果条目无关)。
        # 聚合单一源 = kernel strategy_loss_battle_modifier(卡直读禁
        # aggregate_economy)。三重门 = 败局 ∧ 存在基础伤害 ∧ 修饰非零:
        # 扑满帧豁免后 hp_delta=0 零基础不产生伤害(豁免优先,「扑满不掉
        # 血」同向);死局连带(追加扣血可推过 0)经 apply_hp_outcome
        # 既有保底/死亡语义如实结算。零 rng(同 seed 其他节点随机序列
        # 不漂移);live 零写观察覆盖(游戏自算,结算屏读数入状态容器)。
        hp_extra, keep = strategy_loss_battle_modifier(
            list(self.gs.active_strategies.value or []))
        if (not outcome.won) and outcome.hp_delta < 0 and hp_extra:
            outcome = replace(outcome, hp_delta=outcome.hp_delta - hp_extra)
        # 损血档位触发的损血实值基准(保险;hp_before = apply 前现值,
        # 「规定取法」= 设计内唯一——保底截断局写后值恒 1,不可由
        # (outcome.hp_delta, 写后现值) 反推面值前真值;真值差口径 =
        # 「损失」不超持有量)。None 防御 = hp 从未观察(直构域)时
        # 触发效果条目按零损血跳过,apply_hp_outcome 未观察零写同款防御。
        hp_before = int(self.gs.hp.value or 0)
        # —— 策略卡死亡救援(藏一手 id 302801 首例,死亡救援族首例;接入调用点
        # = apply_hp_outcome 折算点前置分支)。致死预判 = 「生命值将降低至0」
        # 直译(伤害后值 ≤0),与 apply_hp_outcome 内部判据同形,重复面仅单行
        # 不等式,漂移面由 sr-od-test 致死矩阵锁钉死;禁止改写 outcome.hp_delta
        # 实现救援(正 delta 违反 BattleOutcome.hp_delta 恒 ≤0 契约)。救援局
        # 不触 apply_hp_outcome:hp_floor_triggered 零翻转(用户裁定 2026-11-04
        # M-B 独立叠加 = 卡救先消耗、全局保底留给后续致死,序列 卡救→保底 1→
        # 局终)、dead 恒 False → 后段结算环帧/扑满/连胜/败局待办按正常败局
        # 走完(救援只改 hp 落点 + 奖励两笔,不改变败局属性);保底已用(或救援
        # 已用)再归零 → take 返回 None 走 apply_hp_outcome 原路死亡早退,其后
        # 插入位置天然不触。hp None 基座门(None 局禁救援,apply_hp_outcome 未观察
        # 零写同款防御;现役开局种子初始值下不可达)。条件单一源 = kernel
        # take_strategy_death_save(一次性标志位 strategy_death_save_used 承载
        # 防复发,奖励两笔同函数内发放);sig = logic_sig('sim:strategy') 沿
        # 策略战后发放族同组;幂等 = 本函数 _settled_key + 一次性标志位双保险;live 零写
        # 观察覆盖(救援由游戏自算,实机局不接本通道)。
        lethal = (outcome.hp_delta < 0 and self.gs.hp.value is not None
                  and hp_before + outcome.hp_delta <= 0)
        save = (take_strategy_death_save(self.gs,
                                         logic_sig=logic_sig('sim:strategy'))
                if lethal else None)
        if save is not None:
            _floor, dead = False, False
            # 救援发放刻建模假设随局申报(desc 无载面两假设各一键:一次性
            # + 与全局保底独立叠加;键名单一源 = kernel 注册表模块
            # STRATEGY_DEATH_SAVE_ASSUMPTION_KEYS 随家族遍历,值 = 在役
            # 标记纯声明不携数值——变体语义在键名,STRATEGY_WIN_GOLD_
            # SCOPE_ASSUMPTION 同款判读申报制;奖励时点 R1 = 定读非假设
            # 不设键)。
            for _assume in STRATEGY_DEATH_SAVE_ASSUMPTION_KEYS:
                self.disclosures.setdefault(_assume, 'assumed_v0')
        else:
            _floor, dead = apply_hp_outcome(self.gs, outcome)
        self._hp_trail_append()
        # —— 结算环帧补写(T-33 完胜判定数据面,设计 §2.4):与 live 同一
        # ring 读口——killed = won(killed 单一语义 = 「挑战成功」胜利标志,
        # cw_settlement_obs.py 权威注释),hp_after = apply 后 gs.hp 现值
        #(apply_hp_outcome 已写,与 live 结算屏读数同语义位)。node_type =
        # sim kind → 结算行词表映射(词表权威版本 = live 结算行归一
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
        # 连胜转移(M15:状态容器带符号;败局待办登记 M04,消费归下一战斗轮轮首)
        won = outcome.won
        piggy = is_piggy_node(self.gs)
        if self._piggy_income_snap is not None:
            # 扑满收入落账(统一公式「战败时无连胜成分」:败局 = 基础+息,
            # 胜局 = 基础+进轮连胜×倍率+息)。基数 = 窗口开快照(轮初口径,
            # 息按窗口开金),支付时点 = 结算屏与实机一致;增量落当前金,
            # 窗口内购物波动不受影响。
            gold_snap, streak_in, (mult, flat, cap), floor = \
                self._piggy_income_snap
            row = round_start_income(
                node.plane, node.round_num, 'reward', gold_snap, streak_in,
                win_reward_mult=mult, interest_flat=flat, interest_cap=cap,
                interest_floor=floor, lost_round=not won)
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
                                     node_type=kind, won=won, piggy=piggy,
                                     keep_on_loss=keep)
        self.gs.observe(self.gs.streak, signed,
                        evidence=sim_evidence(
                            f'streak:p{node.plane}r{node.round_num}'),
                        sig=obs_sig(group_id='sim:streak'))
        # —— 环境条件发放触发(迭代 2026-10-10-env-conditional-grants
        # landing 3.3;接入调用点 = streak observe 之后,连胜真值已落账,
        # 条件单一源 = kernel check_env_streak_grants)。sig 写死单形态
        # = logic_sig('sim:env'):触发函数两写均为 logic 渠道,obs 族进
        # write_logic_rand 即炸渠道族校验(禁 obs_sig,详设
        # env-conditional-grant.md §5)。返回非 None → 宝钻回调(入参
        # 只传装备名,sig 由回调内构 obs 族;宝钻裁决只认财富宝钻 =
        # 回调内早退,接入调用不预判)。带钻补给不采纳回调:钻类型未建模,
        # _on_supply_picked 零改动(详设 §5「补给宝钻不采纳回调」)。
        granted = check_env_streak_grants(self.gs, signed,
                                          logic_sig('sim:env'))
        if granted is not None:
            on_diamond_acquired(self.gs, granted)
        # —— 持续伤害契约条件分支(T-28 设计稿 §2.3;猜测写 + 进度累计 +
        # 证实同点,接入调用点 = streak 检查同点):active_env 门真后每次结算
        # 分支发火,「假设获得黑天鹅」猜测态写入(sim 状态副本写即真值,sim 无
        # 观察覆盖 → 认知猜测态写即存续)+ 进度键 dot_battle#<k> 追加,
        # 第 ENV_DOT_CONFIRM_BATTLES 笔同窗证实。计数代理口径(用户决定
        # 值,非机制推导)单一源 = kernel 常量;非战斗轮(商店/事件)不经
        # 结算分支 = 不计数(结构性);_settled_key 重入幂等 = 单点每战斗
        # 恰发火一次。条件单一源 = kernel check_env_dot_grants,sig 同
        # streak 通道 logic_sig('sim:env'),返回值忽略(无回调面)。
        check_env_dot_grants(self.gs, logic_sig('sim:env'), count_battle=True)
        # —— 策略卡战后触发发放(策略卡战后触发发放首例;接入调用点 = 既有
        # 环境触发效果条目同段:dot 检查后、败局待办登记前,胜败两态共同路径
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
        # —— 策略卡胜利结算条件金(招财狗 id 103501 首例;接入调用点 =
        # 策略卡战后触发发放之后、败局待办登记之前,胜败两态共同路径。
        # 触发域 = 全部结算节点,本接入调用不设节点类型守卫——卡面「战斗
        # 胜利」未限定节点类型,desc 无载面按字面全节点建模,假设经
        # STRATEGY_WIN_GOLD_SCOPE_ASSUMPTION 披露键随局申报,实机差额
        # 归披露键校准面)。条件单一源 = kernel
        # check_strategy_win_gold_grants(纯读零写:胜 ∧ 未损血 ∧ 佩佩
        # 数三条件函数内短路,扑满败局 won=False ∧ hp_delta=0 形态
        # 自然零发;死亡局已在本函数提前 return 处出局);写面 =
        # observe 金独立笔(状态副本数值面写端通道分工,扑满收入 observe
        # 金同款;obs 族,组名 'sim:strategy' 沿在役惯例 obs/logic
        # 共用——同名 logic 组 = 策略战后发放效果条目);幂等零新增守卫 =
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
        # —— 策略卡完美通关穿戴(佩佩客串 id 331001 首例;接入调用点 =
        # 胜利结算条件金效果条目之后、败局待办登记之前,胜败两态共同
        # 路径——判定输入复用 won ∧ hp_delta==0 与 win 金同源,sim 完胜
        # ≡ 胜利模型差(M12 简化档既有)归对账预期差申报)。条件单一源 =
        # kernel check_strategy_kechuan_wear_grants(本卡佩佩 uid 过滤,
        # Unit.equips 直写旁路转换拦截);sig = logic_sig('sim:strategy')
        # 沿策略战后发放效果条目同组;rng = 独立子流键
        # M13/{p}/{r}/kechuan-wear(装备采样专用,禁复用 M13 主流实例
        # ——ins/boss-grant 独立子流同构先例);幂等零新增守卫 = 本函数
        # _settled_key(同节点重放整段跳过);返回值忽略(无回调面)。
        check_strategy_kechuan_wear_grants(
            self.gs, won=won, hp_delta=outcome.hp_delta,
            sig=logic_sig('sim:strategy'),
            rng=stream_rng(self.seed,
                           f'M13/{node.plane}/{node.round_num}/kechuan-wear'))
        # —— 策略卡损血档位触发发放(保险 id 130501 首例,损血触发族
        # 首例;接入调用点 = 策略卡胜利金效果条目之后、败局待办登记之前,胜败两态
        # 共同路径——触发判据 = 实际损血非胜利,胜局零损血/扑满豁免形态
        # 在触发函数首序自然零通过;死亡局在本函数提前 return 处已出局,
        # 不发放)。损血实值 = hp_before 与写后现值差(保底截断后真值,
        # 「损失」不超持有量;hp 从未观察 → 前后均 0 → 零损血天然跳过,
        # apply_hp_outcome 未观察零写同款防御)。条件单一源 = kernel
        # check_strategy_hp_loss_grants(周期型:累积器全程累计 + 发放刻
        # 取模,无 done 一次性标志位;防重零新增守卫 = 本函数 _settled_key,同节点
        # 重放整段跳过);sig = logic_sig('sim:strategy') 沿策略战后发放
        # 效果条目同组(金写 obs 族签名由函数内构);rng = 独立子流键
        # M13/{p}/{r}/ins(装备采样专用,禁复用 M13 主流实例——其消耗序
        # = 文档化契约「胜负+扣血/进度依序」,续用即延展耦合;独立子流 =
        # 同 seed 其他流零扰动);发放非空 → 建模假设披露键随局申报
        #(三假设:桶结转/真值差/触发源域仅战斗结算,后继非战斗损血源
        # 落地批须扩插入位置,过渡由本键承载)。
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
        # —— 策略卡首领战后随机装备发放(枪在手 id 200501 首例;接入调用点 =
        # 策略卡损血效果条目之后、败局待办登记之前,胜败两态共同路径——卡面无
        # 「胜利」限定 = 败局存活也发;死亡局在本函数提前 return 处已出局,
        # 不发放)。条件单一源 = kernel check_strategy_boss_battle_grants
        # (登记表 STRATEGY_BOSS_BATTLE_GRANTS,node_kind 传本函数结算点
        # 现值 kind,修饰局场字段改写天然跟随零特判);sig =
        # logic_sig('sim:strategy') 沿策略战后发放效果条目同组;rng = 独立子流
        # 键 M13/{p}/{r}/boss-grant(装备采样专用,禁复用 M13 主流实例——
        # 独立子流 = 同 seed 其他流零扰动,'ins' 键同构先例);幂等零新增
        # 守卫 = 本函数 _settled_key(同节点重放整段跳过);返回值忽略
        # (无回调面);live 零写观察覆盖(装备入栏有画面真值可读)。
        check_strategy_boss_battle_grants(
            self.gs, kind,
            sig=logic_sig('sim:strategy'),
            rng=stream_rng(self.seed,
                           f'M13/{node.plane}/{node.round_num}/boss-grant'))
        # —— 策略卡羁绊条件战后武装拍(不要小看我们的羁绊 id 200901
        # 首例;触发-发放两拍制的武装拍,接入调用点 = 策略卡首领战后效果条目之后、
        # 败局待办登记之前,胜败两态共同路径——卡面无「胜利」限定 =
        # 败局存活也武装;死亡局在本函数提前 return 处已出局,不武装)。
        # 条件单一源 = kernel check_strategy_bond_battle_grants(持卡 ∩
        # 登记表 STRATEGY_BOND_BATTLE_GRANTS,激活羁绊数板面真值评估,
        # 达标写武装标记;采样与发放归下一节点窗开拍——desc「进入节点时
        # 获得」= 发放时点在节点窗非结算拍);sig = logic_sig('sim:strategy')
        # 沿策略战后发放效果条目同组;零 rng(武装拍零采样);幂等零新增守卫 =
        # 本函数 _settled_key(同节点重放整段跳过);返回值忽略(无回调
        # 面);live 零写观察覆盖(武装标记无 live 观察通道,装备入栏有
        # 画面真值可读)。
        check_strategy_bond_battle_grants(
            self.gs, sig=logic_sig('sim:strategy'),
            producer=GAIN_CHAIN_PRODUCER)
        # —— 策略卡羁绊档位条件发放(梦境大舞台 id 252301 首例;接入调用点 =
        # 羁绊条件战后武装拍之后、败局待办登记之前,胜败两态共同路径——
        # 卡面无「胜利」限定 = 败局存活也评;死亡局在本函数提前 return 处
        # 已出局,不发放)。触发-发放单拍制(区别于上一效果条目两拍制:本卡
        # 「战斗中…后获得」发放时点 = 结算拍本拍,无节点窗载体句),条件
        # 单一源 = kernel check_strategy_bond_tier_grants(gate + 激活非
        # 独立羁绊档位评估 + 逐档首达一次性标志位,具名确定发放);sig =
        # logic_sig('sim:strategy') 沿策略战后发放效果条目同组;零 rng(具名
        # 确定发放零采样);幂等零新增守卫 = 本函数 _settled_key(同节点
        # 重放整段跳过);返回值忽略(无回调面);live 零写观察覆盖
        #(星徽入栏有画面真值可读)。
        check_strategy_bond_tier_grants(self.gs, logic_sig('sim:strategy'))
        # —— 策略卡首领战结束回血(奋斗协议 id 301801 首例;接入调用点 =
        # 策略效果条目区尾段:羁绊档位效果条目之后、败局待办登记之前,胜败两态共同
        # 路径——卡面无「胜利」限定 = 败局存活也回;死亡局在本函数提前
        # return 处已出局,不回血)。插入位置序位三重依据:①在结算环行之后
        # ——回血笔不进本场环行,本场完胜差分零污染(ring 前置则 boss
        # 战自身环行差分直接被 +50 污染);②在损血差分(hp_lost 取值)
        # 之后——+50 不污染损血档位判据;③回血笔落在本场环行与次战斗
        # 环行之间 → 次节点完胜判据(相邻环行 hp 持平差分)结构性漏判,
        # 方向单一偏严 = 该判据既有偏差面条款辖内新事件源,经披露键随局
        # 申报。条件单一源 = kernel check_strategy_boss_end_heal(Σ 持卡
        # boss_end_heal_hp,纯读零写);写面 = observe hp 独立笔 +
        # _hp_trail_append 成对(first_run 状态容器不变式②——写流与轨迹
        # 全序同构,写一笔追一笔)。**直加不 clip**(正部 HP 加法在码
        # 家族形:选卡即时效果条目 apply_strategy_pick_hp/获得时点回血
        # apply_equip_acquire_hp 同判——hp_max 字段缺位零上限消费,
        # clip 属无消费端语义;live 真实小队生命上限未采证,经披露键随局
        # 申报,实采证伪 → 常量改值零迁移)。hp 未观察(None)= 无基座
        # 零写零追加(禁造假基座,apply_hp_outcome 未观察零写同款)。
        # sig = obs 族 'sim:strategy' 组(状态副本数值面 observe 分工,
        # 策略胜利金效果条目同组;evidence 与选卡即时效果条目 hp:strategy_pick 分账)。
        # 幂等零新增守卫 = 本函数 _settled_key(同节点重放整段跳过);
        # live 零写观察覆盖(回血后血量条真值入状态容器自动收尾)。
        boss_heal = check_strategy_boss_end_heal(self.gs)
        if kind == 'boss' and boss_heal > 0:
            hp_now = self.gs.hp.value
            if hp_now is not None:
                self.gs.observe(
                    self.gs.hp, int(hp_now) + boss_heal,
                    evidence=sim_evidence(
                        f'strategy:boss_heal:p{node.plane}'
                        f'r{node.round_num}'),
                    sig=obs_sig(group_id='sim:strategy'))
                self._hp_trail_append()
                self.disclosures.setdefault(
                    STRATEGY_BOSS_HEAL_HP_CAP_ASSUMPTION,
                    'direct_add_no_clip_v0')
                self.disclosures.setdefault(
                    STRATEGY_BOSS_HEAL_PERFECT_WIN_BIAS,
                    'next_node_perfect_missed_strict_v0')
        # —— 策略卡战斗结束回血(星际和平保险 id 303001 首例;战斗结束
        # 回血族第二成员,全战斗域扩 = T-313 首领战限定域的族级邻效果条目;接入调用
        # 点 = 策略效果条目区尾段 boss 回血效果条目之后、败局待办登记之前,胜败两态
        # 共同路径——卡面「战斗后」无「胜利」限定 = 败局存活也回;死亡局
        # 在本函数提前 return 处已出局,不回血)。插入位置序位依据同 boss 效果条目
        # 三重(结算环行后零污染/损血差分后/环行间插入 → 完胜判据结构性
        # 漏判,同族事件源经 STRATEGY_BOSS_HEAL_PERFECT_WIN_BIAS 键随局
        # 申报,频次 ×N 扩)。条件单一源 = kernel
        # check_strategy_battle_end_heal(Σ 持卡 battle_end_heal_hp,纯读
        # 零写,与 boss 效果条目函数独立不相串);节点门 = kind ∈
        # COMBAT_NODE_TYPES 三型现役单一源词表——扑满 ∈ reward 零回血系
        # 语义收窄(扑满具战斗实体而词表不含 reward),奖励关/补给排除,
        # 经 STRATEGY_BATTLE_HEAL_SCOPE_ASSUMPTION 随局申报(判读申报
        # 制)。写面 = observe hp 独立笔 + _hp_trail_append 成对(不变式
        # ②写流↔轨迹同构)。**直加不 clip**(正部 HP 加法家族形:
        # apply_strategy_pick_hp/apply_equip_acquire_hp/boss 回血效果条目同判
        # ——hp_max 字段缺位零上限消费,clip 属无消费端语义;cap 假设面
        # = STRATEGY_BOSS_HEAL_HP_CAP_ASSUMPTION 家族键,值同
        # direct_add_no_clip_v0 零双源)。hp 未观察(None)= 无基座零写
        # 零追加(禁造假基座,apply_hp_outcome 未观察零写同款)。sig =
        # obs 族 'sim:strategy' 组(状态副本数值面 observe 分工;evidence 与
        # boss 效果条目 strategy:boss_heal 分账)。幂等零新增守卫 = 本函数
        # _settled_key(同节点重放整段跳过);live 零写观察覆盖。
        battle_heal = check_strategy_battle_end_heal(self.gs)
        if kind in COMBAT_NODE_TYPES and battle_heal > 0:
            hp_now = self.gs.hp.value
            if hp_now is not None:
                self.gs.observe(
                    self.gs.hp, int(hp_now) + battle_heal,
                    evidence=sim_evidence(
                        f'strategy:battle_heal:p{node.plane}'
                        f'r{node.round_num}'),
                    sig=obs_sig(group_id='sim:strategy'))
                self._hp_trail_append()
                self.disclosures.setdefault(
                    STRATEGY_BATTLE_HEAL_SCOPE_ASSUMPTION,
                    'combat_node_types_piggy_excluded_v0')
                self.disclosures.setdefault(
                    STRATEGY_BOSS_HEAL_HP_CAP_ASSUMPTION,
                    'direct_add_no_clip_v0')
                self.disclosures.setdefault(
                    STRATEGY_BOSS_HEAL_PERFECT_WIN_BIAS,
                    'next_node_perfect_missed_strict_v0')
        # —— 策略卡首领节点完成固定集发放(武器批发商 id 303501 首例;
        # 接入调用点 = 策略效果条目区链尾顺延:战斗结束回血效果条目之后、败局待办登记
        # 之前,胜败两态共同路径——卡面「下个首领节点后」无「胜利」限定
        # = 败局存活也发;死亡局在本函数提前 return 处已出局,不发放)。
        # 条件单一源 = kernel check_strategy_boss_completion_grants
        # (登记表 STRATEGY_BOSS_COMPLETION_GRANTS,node_kind 传本函数
        # 结算点现值 kind,修饰局场字段改写天然跟随零特判);一次性 =
        # strategy_conditional_done 纯卡名一次性标志位(函数内自管,「下个」恰一次,
        # 后续首领零重复);sig = logic_sig('sim:strategy') 沿策略战后
        # 发放效果条目同组;零 rng(固定全集确定发放零采样,无流键面);幂等零
        # 新增守卫 = 本函数 _settled_key(同节点重放整段跳过);返回值
        # 忽略(无回调面);live 零写观察覆盖(装备入栏有画面真值可读)。
        check_strategy_boss_completion_grants(self.gs, kind,
                                              logic_sig('sim:strategy'))
        # —— 策略卡首领通关价值金(搜打撤 id 303701 首例;接入调用点 =
        # 策略效果条目区链尾顺延:首领完成固定集效果条目之后、败局待办登记之前,
        # 胜败两态共同路径——「通关」= 胜利限定,零发放由触发函数
        # won 门内短路承载;死亡局在本函数提前 return 处已出局,不
        # 发放)。条件单一源 = kernel check_strategy_boss_clear_gold
        #(登记表 STRATEGY_BOSS_CLEAR_GOLD_GRANTS 白名单标记形;金量 =
        # board_bench_char_value_sum 场上+备战席全体角色价值,
        # sell_refund 卖出回金口径;一次性 = strategy_conditional_done
        # 纯卡名一次性标志位,置一次性标志位后同局后续首领零重复);金写 = observe 金独立笔
        #(状态副本数值面写端通道分工,招财狗胜利金效果条目同形;obs 族
        # 'sim:strategy' 组沿结算段在役惯例,evidence = sim_evidence
        # 前缀形 sim:engine:strategy:boss_clear_value:p<r>〔函数内惰性
        # import,star_merge/hp_loss 金笔同款;前缀承载失配抑制消费面〕
        # 与其他策略金效果条目分账),一次性标志位笔
        # logic 族签名由函数内构(observe/write_logic 渠道族互斥,
        # 详见常量注释);0 值金笔照发且一次性标志位照落(空场空席结构可达,
        # 一次性标志位与金笔同窗 = 「下一个」恰一次的载体);零 rng(条件全真值
        # + 板面现读);幂等零新增守卫 = 本函数 _settled_key(同节点
        # 重放整段跳过);live 零写观察覆盖(金由游戏自发入账,结算
        # 屏真值覆盖收束)。
        if won and kind == 'boss':
            check_strategy_boss_clear_gold(self.gs,
                                           obs_sig(group_id='sim:strategy'))
        if not won and kind in COMBAT_NODE_TYPES:
            self.gs.observe(self.gs.pending_loss,
                            LostNodeRef(plane=node.plane,
                                        round_num=node.round_num,
                                        node_type=kind),
                            evidence=sim_evidence('loss:pending'),
                            sig=obs_sig(group_id='sim:loss'))
        self._screen = SCREEN_SETTLE
        self._sub = ''

    def _skip_battle(self) -> None:
        """免战跳过消费(免战牌;现役唯一来源 = 出战声明 battle_skip):
        被跳节点战斗不发生——零战斗面(不掷 U01、不掉血、无结算收入
        落账、无连胜转移、无环境/策略战后发放、无难度记录、无结算环帧行、
        无败局待办登记,清单面 = :meth:`_resolve_battle` 全战斗结算的
        补集),被跳节点经验照常入账 + 状态副本直进下一节点窗。

        入账段镜像 :meth:`_on_node_advance` 现值记账段(含策略卡到级金效果条目
        与到级装备效果条目):跳过拍 = 跨级事件拍,漏镜像则跳过跨级不触发到级
        发放 = 与常规推进分叉;通道/写形态/组名逐字同构,休眠依据与幂等
        说明同推进点注释,不赘。uses 递减不在本效果条目(单一写端 = 上报效果条目
        start_battle consume_use,本效果条目零递减防双写)。重入幂等守卫 =
        已结算节点键(:attr:`_settled_key`;skip 后又到的 battle_resolve
        /重复 battle_skip 同键空转,零双账);后到的 kernel node_advance
        声明经 :meth:`_on_node_advance` 序位守卫自然空转。"""
        node = self.gs.node.value
        if node is None:
            return
        key = (node.plane, node.round_num)
        if self._settled_key == key:
            return
        self._settled_key = key
        self.disclosures.setdefault(CW_SKIP_SCOPE_BATTLE_ONLY_ASSUMPTION,
                                    'battle_only_v0')
        self.disclosures.setdefault(CW_SKIP_SETTLEMENT_SEMANTICS_PENDING,
                                    'hp_streak_income_untouched_v0')
        # 被跳节点经验照常入账(被离开节点的类型;与 _on_node_advance 对
        # 被离开节点的入账同段——跳过 = 节点完成,裁决点 7 默认案)。
        apply_node_xp(self.gs, node_type=node.kind)
        # —— 策略卡到级金效果条目(记账段镜像,挂经验入账后 = 跨级事件拍,
        # 先于新节点窗轮首收入:达标金计入本窗息算基数)。
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
        # —— 策略卡到级装备效果条目(记账段镜像;返回非 None → 宝钻回调,
        # 入参分工同推进点)。
        _equip_grant = check_strategy_level_equip_grants(
            self.gs, logic_sig('sim:strategy'))
        if _equip_grant is not None:
            on_diamond_acquired(self.gs, _equip_grant)
        # 状态副本直进下一节点窗(位面首过渡/常规窗由 _enter_node_window 内部
        # 分支呈现,新窗全部效果条目经 _begin_node_window 窗口幂等守卫自动继承)。
        eff = effective_node_pos(self.gs)
        nxt = (sequence_next(eff, self.gs.node_seq_by_plane.value)
               if eff is not None else None)
        if nxt is None:
            # 防御臂(与 advance 分派 battle_skip+'' 同臂语义;声明面预测
            # 非空而状态副本后继为 None = 声明与状态机漂移,对账面自然留证)。
            self._on_node_advance_terminal()
            return
        self._entered_pos = nxt
        self._enter_node_window(nxt)

    # (巨星/planner 触发评估器与银狼全域星基线已停用:判据 = 状态容器值回调[cw_faction_callbacks],簿记 =
    #  ScreenChanges sidecar,呈现 = pending 检查。)

    # ---------------------------------------------------------- 板面真值观察

    def _observe_board_truth(self) -> None:
        """板面真值观察(与实机「每备战帧面板观察」同契约;标签单一源
        = kernel ``_row_unit_tags``,状态容器行全量重算)。

        sim 是板面真值唯一持有者,kernel board 为派生量且基座未读时
        派生挂钩跳过——步界全量重算真值观察 board(等值零写):承担
        派生基座首读;sim 备战观察只写 node_path 无板面 obs 通道行写,
        全域写路径现均经 write_logic(装备穿戴分支含)使派生挂钩常态
        覆盖,本观察的漂移覆盖职责当前为防御性(基座首读为主要现役
        职能)。失配经状态容器吸收面(``_absorb_board_derived``,sim 证据
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
        重入安全)。终态呈现 = 大厅屏:流程经 CwScreenBattleWait 终局识别标志
        (③B terminal_lobby)→ 主循环 3c 收尾,与实机「终局结算 → 返回
        货币战争 → 大厅」的消费链同形(sim 结算瞬时,直达终点)。

        局终清 pending:终局结算帧前的板面写(如部署拖动跨档)仍可
        登记弹窗;实机局终 = 全部弹窗作废,sim 若保留登记,局终后的
        身份问询懒呈现(:meth:`screen_identity`)会把模态压上大厅,
        而 :meth:`advance` 对 done 状态副本早退不消费——选卡 op 无限重派
        (驱动步上限 5000 烧穿后的失败截图风暴把整局拖到测试超时;
        2026-10-31 统一部署批戊批后 DP 轨迹首次触达该态,定位实录)。
        簿记(fired 集/计数)不清——其生命周期 = 局,与 pending 队列
        语义分界(:func:`clear_screen_changes` 同口径)。"""
        self.done = True
        self._screen = SCREEN_LOBBY
        self._sub = ''
        self.gs.screen_changes.pending.clear()

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

    动作分支 rng 注入(3.4 联调接入;偏差申报的归属点):流程侧动作
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
