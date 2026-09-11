"""P1 全流程模拟引擎(自 cw_sim 拆出,分包期6)。

诚实性分层(哪些是真机制,哪些是校准模拟——每层可独立替换):
- 真代码层:策略决策(DecisionV2 生产逻辑直接跑)、发牌概率
  (cw_shop_odds.REFRESH_PROB)、有限牌池(POOL_COPIES_PER_CARD,
  买走即减/卖出回池)、角色注册表(CHARACTERS)、升级 XP 表。
- 校准模拟层(参数有默认、可注入覆盖):开局 bench 构成、每轮收入、
  战斗结算(Δ池优先,池不可达回退层胜负面见 data/cw_battle_tables)。

用途:策略改动先过本模拟(A/B 对照,``runner.simulate_p1_batch``),
再上实机验证(40min/局)。
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_battle_tables import (
    P2_COMBAT_DEFAULT,
    P2CombatCalib,
)
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_battle_calib import (
    _board_counts_of,
    _board_factions_of,
    _deployable_depth,
    _direction_established,
    _settle_rung,
    _target_comp_label,
    deployed_star_depth,
    node_delta,
    p2_combat_delta,
    roll_rotation_per_stage,
    sample_node_sequence,
)
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_intention import serialize_intention
from sr_od.application.currency_war.kernel.cw_investments import (
    STRATEGY_EFFECTS,
    EconomyEffect,
    aggregate_economy,
    economy_effect_of,
    normalize_invest_name,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BENCH_CAPACITY,
    DEPLOYED_CAPACITY,
    XP_PER_BUY,
    XP_TO_NEXT_LEVEL,
    BenchChar,
    BuyCard,
    CompTransaction,
    GameState,
    LevelUp,
    LevelUpShop,
    RefreshShop,
    SellBench,
    SellDeployed,
    ShopCard,
    SwapDeploy,
    _bench_char_cost,
    bench_occupied,
    bench_place,
    card_cost,
    deployed_occupied,
    deployed_place,
    iter_occupied,
    iter_occupied_deployed,
    merge_buy_completes,
    sell_refund,
)
from sr_od.application.currency_war.kernel.cw_state import (
    simulate as _simulate_state,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.sim.cw_sim_invest import (
    InvestInjectionState,
    SimInvestProfile,
    SinkInvestSampler,
    sample_invest_profile,
)
from sr_od.application.currency_war.strategies.impl.cw_strategy import StrategySession

# (expected_paths 快照 import 已随 ADR-0651 两态制退役删除——telemetry
#  .recorder.snapshot_expected_paths 同批拆除。)

# 开局 bench 构成(遥测校准:开局 4 张,1 费主导)
START_BENCH_COUNT: int = 4
START_BENCH_COST_WEIGHTS: tuple[tuple[int, float], ...] = ((1, .65), (2, .35))


def _overlay_xp_per_refresh(strategy_names: list[str]) -> int:
    """付费刷新产经验数值(单一源 = ``cw_investments.STRATEGY_EFFECTS`` overlay)。

    - 逐持卡名(先 normalize_invest_name 归一 OCR 分隔符形变)查 overlay 的
      EffectSpec,payload 为 EconomyEffect 时累加 xp_per_refresh;未入 overlay
      的卡不供值 —— overlay 是该查询键的唯一供数面,overlay 值变更 sim 跟随。
    - pending 条目(verdict=None)保守支:其 payload 数值本身即按保守支建模
      (现均无 xp_per_refresh,与旧 STRATEGY_ECONOMY 聚合路径同值);verdict
      定谳若引入新语义(如 经验就是财富 改道),须回本查询点同步。
    """
    total = 0
    for n in strategy_names:
        spec = STRATEGY_EFFECTS.get(normalize_invest_name(n))
        if spec is None or not isinstance(spec.payload, EconomyEffect):
            continue
        total += spec.payload.xp_per_refresh
    return total

# 收入模型(r305 真值接入:sim 与决策共用 cw_economy 单一源;
# ADR-0439 收入口径修正:败轮节点金 + 奖励轮 base/streak 成对查表)
from sr_od.application.currency_war.kernel.cw_economy import (  # noqa: E402,F401
    BASE_INCOME,
    ECONOMY_CALIB_VERSION,
    LOSS_GOLD_BY_NODE,
    REWARD_BASE_GOLD_BY_ROUND,
    streak_gold,
)
from sr_od.application.currency_war.sim.pool import (  # noqa: E402
    SimResult,
    _Pool,
    live_delta_for,
    resolve_pool,
)

if TYPE_CHECKING:
    # P2ReplayEntry 仅作注解引用(future annotations 下运行期零依赖);
    # 模块级反向 import 会与 engine_p2→engine_p1 构成环,故挂 TYPE_CHECKING。
    # SwapPlan 仅作注解引用(kernel 与 sim 无环,但函数内已惰性导入,
    # 注解面统一挂 TYPE_CHECKING 保持「运行期零依赖」同款纪律)。
    # SwapPlanContext 同上(T-279 R1 计划 ctx 注解面;运行期消费位均
    # 函数内惰性导入)。
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        SwapPlan,
        SwapPlanContext,
    )
    from sr_od.application.currency_war.sim.engine_p2 import P2ReplayEntry


def _board_next_tier_of(board_factions: dict[str, int]) -> dict[str, int]:
    """板面各阵营「下档阈值」观测键(生产 ``GameState.board_next_tier``
    的 sim 同构面;语义 = 左面板 "X/Y" 的 Y)。

    派生单一源 = ``kernel.cw_board_state.board_next_tier_of``(迁移批次二:
    本函数 = **薄委托**,禁第三份推导——obs computed 支与 sim 观测键
    (ADR-0488 硬依赖键供给)同源由委托结构保证;consume 锁
    test_board_next_tier_of_matches_registry_formula)。
    消费方 = Δp_tier 档位分解标定批(观测披露面;兑现链开关族已随旧
    方案清退批删除,清查报告 OLD_MIX_AUDIT §1.3,键保留作判读面)。
    """
    from sr_od.application.currency_war.kernel.cw_board_state import (
        board_next_tier_of,
    )
    return board_next_tier_of(board_factions)

START_BENCH_COUNT: int = 4

START_BENCH_COST_WEIGHTS: tuple[tuple[int, float], ...] = ((1, .65), (2, .35))



def _overlay_xp_per_refresh(strategy_names: list[str]) -> int:
    """付费刷新产经验数值(单一源 = ``cw_investments.STRATEGY_EFFECTS`` overlay)。

    - 逐持卡名(先 normalize_invest_name 归一 OCR 分隔符形变)查 overlay 的
      EffectSpec,payload 为 EconomyEffect 时累加 xp_per_refresh;未入 overlay
      的卡不供值 —— overlay 是该查询键的唯一供数面,overlay 值变更 sim 跟随。
    - pending 条目(verdict=None)保守支:其 payload 数值本身即按保守支建模
      (现均无 xp_per_refresh,与旧 STRATEGY_ECONOMY 聚合路径同值);verdict
      定谳若引入新语义(如 经验就是财富 改道),须回本查询点同步。
    """
    total = 0
    for n in strategy_names:
        spec = STRATEGY_EFFECTS.get(normalize_invest_name(n))
        if spec is None or not isinstance(spec.payload, EconomyEffect):
            continue
        total += spec.payload.xp_per_refresh
    return total


# HP 上界(批㉘ F6,ADR-0287):游戏机制真值无文档证据,暂 cap 100
# (实机满血样本核真后更新;检查项 hp_upper_bound_truth 锁 hp>100 恒 0)
HP_UPPER_BOUND: int = 100


INTEREST_CAP: int = 5


# sim 执行层付费升级上界,守卫与轮末升级循环共用本常量防两处漂移。
# 注意:这不是游戏真实满级——真实满级 = 10(kernel.cw_registry
# .level_max、cw_shop_odds.REFRESH_PROB 已含 lv10 行、实机 replay 可达
# lv10),实机 lv10 才禁用购买经验,lv9 是正常付费升级档。本层仍取 9
# 的理由:sim P1 追级轨迹高于实机(实机 P1 上限 7),先开 10 是把失真
# 转移而非消除,且既有批次与池指纹在 9 级语义下产出。放开到 10 属行为
# 变更,前置 = P1 追级虚高治理(见 decisions/ ADR-0447 修补 E)+
# planes=2 池指纹重锚。
LEVEL_CAP: int = 9


# 装备供给结构校准(供给重校准批;数据源 = 实机 [cw!][grant] 快照 57 局
# 逐轮差分画像,分析脚本与校准目标表见 .debug 产物 w477_supply_recalib/):
# 实机装备类发放 = 基础件 86% / 进阶 14%(工具冶金炉/拆装扳手为跨局
# 持存物品,非穿戴件,不建模),P1 均 4.7 件、分布在 ~3.8 个发放轮;
# 供给节点 3 选 1 近全基础件,进阶来自奖励/投资/遭遇等多通道。
# 旧池(_EQUIP_VALUE 键 10 名、成品为主、基础件仅 2 名)与实机结构性
# 相反 → 合成链触发面不可达(见 decisions/ 对应 ADR)。新结构:
# 供给节点 3 选项采自基础件 8 名均匀池(decide_supply 决策语义不变),
# 追加件以固定概率代理多通道合计(含进阶)。结构变更是有意的行为
# 变更——新旧池不可比,指纹追加 +eqg<版本> 位,旧基线全部作废。
EQUIP_GRANT_CALIB_VERSION: int = 1

EQUIP_GRANT_BONUS_P: float = 0.30      # 每供给节点追加 1 件的概率

EQUIP_GRANT_BONUS_ADV_SHARE: float = 0.35   # 追加件中进阶占比

# ===== 工具发放注入基建(21 号稿 §4/§5 声明的最小面;10 号稿 §2.1.9)=====
# 目的:让炉准入/扳手闸等工具判据在 sim 行为分布观测中可达(sim 局内
# 自然发放永不含工具——工具为跨局持存物品,不建模,见上方供给校准注)。
# 注入走**追加件通道旁路**:pool 非空且命中概率时追加 1 件工具(不经
# 供给 3 选项,不改 decide_supply 决策语义)。**缺省(pool 空 ∧ P=0)零
# 漂移**——既有批次与池指纹完全不受影响;开注入属显式实验配置,池指纹
# 变化由实验批自行声明。消费侧:工具名进 st.equips 后不进 equip_allocation
# 可穿池(下方分配调用处按注册表类别过滤,与执行层 wearable 同口径)。
TOOL_GRANT_INJECT_POOL: list[str] = []
TOOL_GRANT_INJECT_P: float = 0.0



# 事件金 = 金流状态分布校准总闸(ADR-0233 建通道;ADR-0447 重整定)。
# 语义(why):sim 策略=产线策略且有意不模拟执行缺口(完美执行是终态),
# 而实机金状态分布含决策/执行缺口造成的富状态——本表按实机逐轮备战
# 帧金轨迹(2026-08-28 当日 15 局,`w493_income_calib/` 预注册)做反馈整定,使 sim 状态
# 分布对齐实机,「金高位前提」的策略检查在 sim 里真实激活。整定程序:
# δ(t) += 0.7·(实机帧金均值 − sim 帧金均值),3 轮收敛(残差全 |≤5| 金/轮),
# 台账 = .debug/temp/currency_war/w493_income_calib/calib_loop_log.json(gitignored)。
# 边界(`w503_attack_valve/` 对抗审计修补 E/B,ADR-0447):
# - **靶标注**:靶 = 带执行缺陷的 2026-08-28 败局为主轨迹(12/15 死亡,
#   幸存者偏差自认)——禁止被引用为长期经济真值;
# - **r9 退坡**:r9 δ=32.0 为「非策略病分量」,闭环原始收敛值 46.36 中
#   ≥14 金是 r9 levelup 泄金(已定位策略末段病)的补偿——按设计「r9
#   残差只披露不强修」退坡,r9 单轮缺口(约 +10)披露不收敛;策略面
#   修复 r9 泄金后**不得**以此表回填;
# - **重整定触发器**:spend_ledger 干净局攒到 2~3 局、或执行缺陷清零
#   里程碑达成 → 重采实机基线(≥15 局),若逐轮金均值漂移 >5 金/轮 →
#   δ 重整定 + ECONOMY_CALIB_VERSION 3;
# - spend_ledger/执行面修复落地后本表须重整定(届时注入量应显
#   著回落);±2 抖动机制不变;v1 值(1/5.5/2/2/2/2/4/9/4)见
#   ADR-0447,与 ECONOMY_CALIB_VERSION=2 配对,旧批次不可比。
EVENT_GOLD_BY_ROUND: dict[int, tuple[float, ...]] = {
    1: (0.0,), 2: (6.41,), 3: (13.95,), 4: (14.47,), 5: (23.11,),
    6: (19.41,), 7: (21.15,), 8: (35.05,), 9: (32.0,),
}



def _event_gold(round_num: int, rng: random.Random) -> int:
    """奖励球/节点事件金(校准总闸;ADR-0447 整定值,±2 抖动)。"""
    base = EVENT_GOLD_BY_ROUND.get(round_num, (4,))[0]
    return max(0, int(base + rng.uniform(-2, 2)))


# 战斗结算幅度层(25 局 HP 轨迹校准;胜负面自 ADR-0308 起由
# r259 二次校准(139 轮干净差分):lv7 后段观测中位 -23(无方向)/
# -31(锁线晚的弱队),原 3.5 系数低估后段流血 → 提到 4.0。
# 方向分桶样本小(4-10)且与「发牌差的队锁线晚」混杂;ADR-0308 起
# 胜负面不再由方向门控(幅度层保留方向无关的轮次递增),后续样本
# 攒够换「板深×方向×轮次」联合模型。
#
# r260(用户指路:节点类型必须分层)——**真实节点序列**来自实跑
# read_node_sequence 日志(nodeseq):每个位面的节点行是
# battle/encounter/reward/supply 混排(奖励/补给=零战力要求不掉血;
# 遭遇=战力要求高于普通甚至 boss,遭遇三四尤其)。真实观测形态:
# `battle battle encounter reward encounter reward` /
# `reward reward battle encounter supply battle encounter reward` /
# `... encounter encounter encounter reward`(三连遭遇)。
# 模拟逐局**随机采样节点序列**(类型分布对齐观测),替代旧
# 「每轮都是战斗」假设;遭遇轮结算强度对齐 boss 或更高。
NODE_TYPE_POOL: tuple[str, ...] = (
    'battle', 'battle', 'battle', 'battle',   # 战斗为主(~44%)
    'encounter', 'encounter',                 # 遭遇(~22%)
    'reward', 'reward', 'supply',             # 奖励/补给零战力(~33%)
)



# ===== P2 段校准层(`w157_p2/`/ADR-0362;语料边界=`w151_p2/` 四局解剖+16 局
# replay plane=2 行 44 条,行为分布验证口径非 hp 点值校准) =====
# P2 位面段轮数(boss@r7;迁移审计 w156(git 历史) §2:16 局 outcomes 拼版,r1-r7 全在)。
P2_ROUNDS: int = 7

# P2 节点序列(观测拼版,逐槽一致无变异观测):
# r1 battle(16/16)/r2 battle(10/10 到达局)/r3 supply(5/5)/
# r4 battle(4/4)/r5 encounter(3/3)/r6 reward(3/3)/r7 boss(2/2)。
# ⚠️ 与 economy.md §10.2 的 P2 开局帧(1 帧:battle/battle/
# encounter/reward/encounter/reward/?)在 r3-r6 槽序不一致——
# 开局帧 1 样本 vs outcomes 拼版 5+ 局一致,取拼版;帧间变异
# 无观测(P1 的变异位机制不外推),多局复核后如需变异位再改。
P2_NODE_SEQUENCE: tuple[str, ...] = (
    'battle', 'battle', 'supply', 'battle',
    'encounter', 'reward', 'boss',
)

























# r397/r399(用户定调重写 transition_combos.md;废除 r148/r149 大/中
# 引擎分层——旧词来源可疑且「大+中过不了位面1」被 895 帖数据证实):
# 过渡阵容 = **一级羁绊即有伤害**的 combat 羁绊两两组合——
# 仙舟3(召唤神舟)/列车2(星穹列车撞击)/DOT2(敌方回合超激发)。
# 人员要求:DOT2/列车2 无要求;仙舟3 用藿藿+饮月+爻光效果最好
# (功能链,95% 帖含全三人组);**希儿系**(r399 用户实战确认)=希儿
# 在场 AND(量子≥2 OR 贝≥2)——伤害在希儿技能层,量子/贝是放大器,
# 无希儿时不能独立当过渡(第四体系,单卡依赖)。
# 通用羁绊(战技点/护盾/学者/减益…)不是过渡主体——四种都不含的
# 49 帖全是直通线。
# 迁移审计 w47(git 历史) 统一化:``_TRANSITION_TRAITS`` 改 alias import 自模块头
# (``cw_deploy_logic.TRANSITION_TRAITS``,其本体已从 SYSTEM_CARDS 派生,
# 单一源;原先两模块各写一份同值常量对、注释互指——漂移窗口=任一侧单改)。
# 消费本名的 scoring._engine_frac_remainder 等 import 路径不变。














def sim_decision_registry():
    """sim 环境的决策层注册表视图:level_max 对齐执行层 LEVEL_CAP。

    为什么:满级升级拒付空转的根源 = 决策层单一源 registry.level_max=10
    (实机真值,lv9 付费升级有效)与 sim 执行层 LEVEL_CAP=9 的**声明性
    建模分歧**(见 LEVEL_CAP 注释与 cw_state.xp_apply_clicks「勿混用」
    注)——决策层的「等级未满」前置(candidates/remediation)在 sim 的
    lv9 帧恒放行 → 执行层恒拒付(22+/局 level_cap_rejects 空转)。
    本视图把 sim 的有效上限在**接线单一址**注入决策层,不造第二把尺
    (值源自 LEVEL_CAP);实机路径不受影响(DEFAULT_REGISTRY 不改,
    DEFAULT_REGISTRY.level_max 保持 10)。sim 拒付层保留作防线。
    """
    import dataclasses

    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    return dataclasses.replace(DEFAULT_REGISTRY, level_max=LEVEL_CAP)



def _lag_excluding_fenced_holds(lag_idx: list[int], replay_occ: list[int],
                                main_held_slots: set[int]) -> int:
    """重放 lag 扣除主趟围栏已仲裁 hold 的槽位(ADR-0287/W678:围栏
    hold 不计漏上,检查只盯「围栏认可却未执行」)。

    :param lag_idx: 重放趟认可的可上件下标(紧缩占用序,与 replay_occ
      同序同基);
    :param replay_occ: 重放时点 bench 占用槽位表(压缩序 → 槽位下标映射);
    :param main_held_slots: 主趟围栏仲裁为 hold 的槽位下标集。
    """
    return sum(1 for i in lag_idx
               if i < len(replay_occ)
               and replay_occ[i] not in main_held_slots)


def _fill_lag_replay(st: GameState,
                     target_factions: frozenset[str],
                     target_cores: frozenset[str],
                     fw_carry: frozenset[str],
                     locked_factions: frozenset[str],
                     recipe_floor_lock_exempt: bool = False,
                     last_held_slots: set[int] | None = None) -> int:
    """统一 lag 口径:对补部署后的 bench 残余重放围栏,「围栏认可未上」
    件数即 deploy_lag_units(W678:围栏 hold 不计漏上,豁免集 =
    ``last_held_slots``)。原为 ``_residual_fill_deploy`` 内嵌段,T-279
    R1-a 计划直投路径需同一 lag 口径,提取共用(行为逐位同旧)。"""
    from sr_od.application.currency_war.kernel import cw_deploy_logic as _dl
    _lag_slots = [i for i, bc in enumerate(st.bench) if bc is not None]
    _lag_keep = [bc for bc in st.bench if bc is not None]
    if not _lag_keep:
        return 0
    _lag_idx, _ = _dl.select_deployments(
        _lag_keep,
        deployed_cids={d.char_id
                       for d in iter_occupied_deployed(st.deployed)
                       if d.char_id},
        deployed_fac=_board_factions_of(st.deployed),
        board=dict(st.board),
        cap=st.max_units(),
        target_factions=target_factions,
        target_cores=target_cores,
        fw_carry=fw_carry,
        locked_factions=locked_factions,
        recipe_floor_lock_exempt=recipe_floor_lock_exempt,
    )
    # W678 豁免(与主趟路径同口径):重放认可的件若槽位属末次仲裁
    # hold 集 ⇒ 不计 lag(上下文翻转件,非漏上)。
    return _lag_excluding_fenced_holds(
        _lag_idx, _lag_slots, last_held_slots or set())


def _residual_fill_deploy(
    st: GameState,
    target_factions: frozenset[str],
    target_cores: frozenset[str],
    fw_carry: frozenset[str],
    locked_factions: frozenset[str],
    recipe_floor_lock_exempt: bool = False,
) -> tuple[int, int, int]:
    """skip_fence 轮轮末残余补部署(迁移审计 w716(git 历史) F1 修复设计 §三;命题 P-F1)。

    为什么:围栏互斥(裁决1「显式>围栏,同轮互斥」)原实现是**轮级禁运**
    ——演进事务密集轮每轮必有 applied CompTransaction,换阵撤回/3合1 吞
    副本造成的板面空槽连续过夜,欠载打仗掉血(F1 病理;样本 640247
    r5-r7 缩退 6→3→2)。修法 = 把互斥辖域从「轮级」收窄到「通道级」:
    skip 轮轮末对「围栏认可」执行 bench→空槽补部署。

    - 零支出零破息约束:上场动作仅 bench→空槽(pop-append),不买、不卖、
      不刷新、不 swap——金账恒等式(gold_before+inc−buys−levelup−refresh
      +income)不含本动作,任何 Δp>0 受益在 C=I=0 下严格非负(P-F1,
      docs/develop/currency_war/proofs/p24-residual-fill-dominance.md)。
    - 显式保留集投影已随 v3_hoard 通道退役删除(A6 裁决;dd-038
      统一迁移批 / commit b94e9cfb,2026-09-04 用户裁定清理)——
      写端已亡,保留集恒空;「与在场(deployed)同名」的素材副本
      仍由围栏 dedup(r404-A2/5.1.7 在场唯一)自然 held(ADR-0473
      增补/W748 收窄后唯一存留面)。
    - 补部署候选 = select_deployments(bench 占用全集,行动后 deployed/
      board/cap,目标集同围栏主趟)的 up 集;与主趟同一纯函数(单一源)。
    - 统一 lag 口径:补部署后再重放围栏,残余可上件数即
      deploy_lag_units,消除 skip 轮 lag 恒 0 的检查器失明面(设计 §四-2)。

    返回 (residual_deployed 补上场件数, residual_held 恒 0——保留集
    投影已随 v3_hoard 通道退役删除(见上),字段保留仅为账本 schema
    兼容, deploy_lag_units 补部署后残余可上件数)。

    T3 同轮保留·sim 建模缺口显式申报(修复批验收口径):本函数只在
    skip_fence 分支调用(调用点见 if _explicit_deploy_seen 块)——
    非 skip 轮的上板由围栏主趟代理,两代理都不等价生产 cw_op_deploy
    每轮主排序+P24 的完整链。故「被保垫件买入→上板转化率」在 sim 侧
    **只可部分测**(skip 轮可见 residual_deployed 转化;非 skip 轮
    不可测)。修复批验收口径据此降级:效果断言改测「净转化」——
    no_same_round_buy_sell violations 归零 + t3 买入轮的净金出口
    (轮末金−轮初金,金应真实离手或形成板面资产),禁拿 t3_buy 触发
    计数冒充上板效果;账本逐轮披露 sim.stall_buys_pending(轮末仍未
    销账的保护名数)供对账。
    """
    from sr_od.application.currency_war.kernel import cw_deploy_logic as _dl

    _occ = [(i, bc) for i, bc in enumerate(st.bench) if bc is not None]
    _keep = _occ
    _res_held = 0   # 保留集恒空(v3_hoard 写端已亡),如实恒 0
    _res_up = 0
    # 不动点循环:每次上场改变 board/dep_fac 阵营计数后,「成对/点火」
    # 判据可能使此前 held 的件转为可上(生产 op 侧 = drag 循环逐件动态
    # 仲裁同语义)——单趟会把「先上激活成对」的件错留 bench(640442 r7
    # 取证:单趟 up=2/lag=2,循环后归零)。
    while _keep:
        _up_idx, _held_idx = _dl.select_deployments(
            [bc for _, bc in _keep],
            deployed_cids={d.char_id
                           for d in iter_occupied_deployed(st.deployed)
                           if d.char_id},
            deployed_fac=_board_factions_of(st.deployed),
            board=dict(st.board),
            cap=st.max_units(),
            target_factions=target_factions,
            target_cores=target_cores,
            fw_carry=fw_carry,
            locked_factions=locked_factions,
            recipe_floor_lock_exempt=recipe_floor_lock_exempt,
        )
        # 末次仲裁 hold 槽位集(W678:围栏 hold 不计漏上——lag 重放的
        # 上下文翻转件以此为豁免集,与主趟路径同口径)。
        _last_held_slots = {_keep[j][0] for j in _held_idx
                            if j < len(_keep)}
        if not _up_idx:
            break
        # up_idx 是紧缩占用序(keep 表)→ 回映射槽位下标(ADR-0316 同式)
        _placed_any = False
        for _j in _up_idx:
            if _j < len(_keep):
                _slot, bc = _keep[_j]
                if st.bench[_slot] is not None:
                    deployed_place(st.deployed, bc)
                    st.bench[_slot] = None
                    _res_up += 1
                    _placed_any = True
        if not _placed_any:
            break
        st.board = _board_counts_of(st.deployed)
        _keep = [(i, bc) for i, bc in _keep if st.bench[i] is not None]
    # 统一 lag:补部署后残余(围栏认可未上件;重放单一实现 =
    # _fill_lag_replay,T-279 R1-a 直投路径共用)
    _lag = _fill_lag_replay(st, target_factions, target_cores, fw_carry,
                            locked_factions, recipe_floor_lock_exempt,
                            _last_held_slots)
    return _res_up, _res_held, _lag


def _m1p_plan_fill_deploy(st: GameState, plan: SwapPlan,
                          ctx: SwapPlanContext | None, sess) \
        -> tuple[int, int, int]:
    """M1″ 换血轮轮末补部署——计划单一源消费(T-279 R1;ADR-0640)。

    病灶(C-A2 强信号缺口 2/263,局 18 P2r4 黄泉/局 58 P2r5 佩拉):
    计划面(select_swap_plan,all_factions/锁线域收窄键集)与执行面
    (轮末补部署,手搓 comp.factions)双 target 视图,单空槽补部署被
    执行面改判给另一件,本轮新购义务件滞留备战席且零处置记录。修法 =
    执行面收口到计划单一源(装配单一源契约 ADR-0530/0534 延伸至部署
    补上段,ADR-0640 新裁决条文)。

    - **R1-a 直投(首选)**:卖出成功帧(sim ``m1p_swap_execute`` 卖的
      就是 ``plan.sell_names``,卖出后板面 ≡ 计划假想板面——同一 victim、
      同帧无漂移),计划已对该假想态算好 up 集,直接逐名部署,无需重选。
      前提校验(对抗审 F2 名字级单通道三点式,任一不满足 → R1-b):
      ①victim 已按计划卖出(调用方仅在本帧 m1p 卖出成功后调用,转录行
      name = 计划卖序);②up 成员仍在 bench(名字级,
      ``swap_plan_up_names`` 单一换算);③占用数与计划假想一致(计划
      时点占用 −1 victim)∧ up 名不与在场重复 ∧ 容量可容。
    - **R1-b 防御态**:装配单一源 ``assemble_swap_plan_inputs`` 对卖出后
      现读状态重 derive,``transition_domain`` 钉计划时点域事实
      (``ctx.transition_domain``;卖出后 board_full 翻假会让域谓词现算
      失真丢收窄辖域,域辖域不可从卖出后状态重推),再走
      ``_residual_fill_deploy`` 同一补部署机器(不动点循环/lag 口径继承)。
      局 18 实证:同帧收窄键集 up=[黄泉]=计划 pick、all_factions up=
      [丹恒·腾荒]——不钉域则防御路径复现缺口,钉定是等价性的必要前提
      (对抗审 F3 条件式【推】)。
    - **辖域(对抗审 F4 裁决)**= m1_swap_redeploy 轮:非 m1p 显式动作轮
      维持现状围栏 fill(原目标集),本函数只被 m1p 卖出成功帧调用,
      通用化收口归后续卡(证据义务 = R2 显影显式动作轮滞留面)。

    返回 ``(residual_deployed, residual_held 恒 0, deploy_lag_units)``
    ——与 ``_residual_fill_deploy`` 同三元组 schema(skip_fence 行消费
    面零迁移)。
    """
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        assemble_swap_plan_inputs,
        swap_plan_up_names,
    )
    up_names = swap_plan_up_names(plan, ctx)
    occ_now = sum(1 for _ in iter_occupied_deployed(st.deployed))
    occ_plan = len(ctx.deployed) if ctx is not None else None
    bench_names = {b.char_id for b in st.bench
                   if b is not None and b.char_id}
    dep_names = {d.char_id for d in iter_occupied_deployed(st.deployed)
                 if d.char_id}
    direct_ok = (ctx is not None and bool(up_names)
                 and occ_plan is not None and occ_now == occ_plan - 1
                 and all(n in bench_names for n in up_names)
                 and not (set(up_names) & dep_names)
                 and occ_now + len(up_names) <= st.max_units())
    if direct_ok:
        _placed = 0
        for _n in up_names:
            _slot = next((i for i, b in enumerate(st.bench)
                          if b is not None and b.char_id == _n), -1)
            if _slot < 0 or deployed_place(
                    st.deployed, st.bench[_slot]) is None:
                break   # 防御:前提已验不可达;部分放置如实计数
            st.bench[_slot] = None
            _placed += 1
        st.board = _board_counts_of(st.deployed)
        if _placed == len(up_names):
            _lag = _fill_lag_replay(
                st, ctx.target_factions, ctx.target_cores, ctx.fw_carry,
                ctx.locked_factions, ctx.recipe_floor_lock_exempt)
            return _placed, 0, _lag
        # 部分放置(前提中途破,直投不完整)→ 落 R1-b 对当前态补余
        # (已放置件在板,重 derive 从现读出发,不回滚)
    # R1-b:卖出后现读重 derive(域辖域钉计划时点事实);装配不可得
    # (sim 供给齐备不可达,防御缺省)退计划 ctx 视图——最近真值源。
    _ctx2 = None
    try:
        _ctx2 = assemble_swap_plan_inputs(
            sess, state=st,
            deployed=list(iter_occupied_deployed(st.deployed)),
            bench=[b for b in st.bench if b is not None],
            cap=st.max_units(),
            transition_domain=(ctx.transition_domain
                               if ctx is not None else None))
    except Exception:   # noqa: BLE001  重 derive 缺供给 = 退计划视图
        _ctx2 = None
    if _ctx2 is None:
        _ctx2 = ctx
    if _ctx2 is None:
        return _residual_fill_deploy(st, frozenset(), frozenset(),
                                     frozenset(), frozenset())
    return _residual_fill_deploy(
        st, _ctx2.target_factions, _ctx2.target_cores, _ctx2.fw_carry,
        _ctx2.locked_factions,
        recipe_floor_lock_exempt=_ctx2.recipe_floor_lock_exempt)


def project_sell_buyback(acts: list[dict]) -> list[dict]:
    """同轮「卖出→买回」回环投影(sim71 批;双层只读零 rng 的实例级半边)。

    背景:sim71 批定位「同名卡同轮卖出→买回」回环 29 例(单次 1-2 金
    价差,量级待分键),与 sim69/70 同轮买卖同族扩展——既有账本只有
    轮级 spend/sell_income 聚合,回环不可见。本函数是**已发生动作流的
    只读投影**:按动作序扫描,卖出登记名字→累计卖返;该名再被买时
    记一笔回环(净金 = 买价 − 卖返),登记清空(再卖再买各记各笔)。
    买先于卖不构成回环(登记序保证)。零 rng、零状态写入、零行为面。

    口径边界(如实声明):只辖 SellBench/BuyCard 两通道(SimP1 账本
    _acts 的商店回环主通道);deployed 侧卖出通道不入投影——其回环
    若成病灶属后续扩展,不与本键混桶。合并买 count=k 时买价 = 单价×k
    (金真实流出,与 _acts 花费口径同式)。
    【勘误(T-169 落地审 F5)】本注旧文「SellDeployed/SwapDeploy 转录行
    不含卖返/名字同形状」已失真:m1_swap_redeploy 转录行(T-169 执行面)
    带 name+income 键;本投影的辖域裁定不变(仍只消费 SellBench/BuyCard,
    deployed 侧卖出不成「买回」回环形态),行形状申报以此勘误为准。
    """
    loops: list[dict] = []
    sold: dict[str, int] = {}
    for a in acts or []:
        t = a.get('__type__')
        if t == 'SellBench':
            n = a.get('name') or ''
            if n:
                sold[n] = sold.get(n, 0) + int(a.get('income') or 0)
        elif t == 'BuyCard':
            card = a.get('card') or {}
            n = card.get('name') or ''
            if n in sold:
                cost = int(card.get('cost') or 0) * max(
                    1, int(a.get('count') or 1))
                income = sold.pop(n)
                loops.append({'name': n,
                              'sell_income': income,
                              'buy_cost': cost,
                              'net_gold': cost - income})
    return loops


def _m1p_plan_and_record(st: GameState, sess) \
        -> tuple[SwapPlan, dict, SwapPlanContext | None]:
    """M1″ 计划计算 + 发射意图记录(sim 决策面共用同一份计划对象)。

    语义出处:ADR-0530(board-full swap redeploy);执行面接入与本
    函数拆分 = 进度账本 T-169(sim 缺板满换血执行面,总图设计 R2 §2
    sim 边界行)。原 ``m1p_intent_record`` 只记意图零行为面(ADR-0530
    自述「sim 不建模执行侧 swap 卖出语义」)——实测该边界让换血行为
    在 sim 结构性不可见(板满帧计划非空、零卖出动作,模拟批#5 最大
    发现;账本 T-169 污染声明),本批按最小执行面接通:计划对象同时
    供引擎执行转录消费(见 ``m1p_swap_execute``),记录 dict 形状 =
    nonempty/abstain/sell/up/**up_names**/reasons(T-279 R2 追加
    up_names = 上序名单名字级,``swap_plan_up_names`` 单一换算;追加键
    下游零迁移)。第三个返回值 = 装配 ctx(计划时点快照;引擎执行转录
    与轮末补部署 ``_m1p_plan_fill_deploy`` 消费,发射⇔补上同吃同一
    份装配,禁二次装配出第二份输入)。

    谓词 = 生产同款单一源 ``assemble_swap_plan_inputs`` + ``select_swap_
    plan``(st = 买/升级后黑板,deployed/bench = 占用件现读,cap =
    max_units 派生链)——与生产发射/执行两面同函数、同一装配契约,禁
    第二装配。零 rng 消耗、纯读(状态写入只发生在引擎执行转录块)。
    """
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        assemble_swap_plan_inputs,
        select_swap_plan,
        swap_plan_up_names,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        iter_occupied_deployed,
    )
    ctx = assemble_swap_plan_inputs(
        sess, state=st,
        deployed=list(iter_occupied_deployed(st.deployed)),
        bench=[b for b in st.bench if b is not None],
        cap=st.max_units())
    reasons: dict[str, str] = {}
    plan = select_swap_plan(ctx, reasons_out=reasons)
    record = {
        'nonempty': plan.nonempty,
        'abstain': plan.abstain,
        'sell': list(plan.sell_names),
        'up': len(plan.up_bench),
        'up_names': swap_plan_up_names(plan, ctx),
        'reasons': dict(reasons),
    }
    return plan, record, ctx


def m1p_intent_record(st: GameState, sess) -> dict:
    """M1″ 发射意图记录(兼容入口;计划本体经 ``_m1p_plan_and_record``)。

    返回记录 dict 形状 = nonempty/abstain/sell/up/up_names/reasons
    (up_names 随 T-279 R2 追加);引擎现走 ``_m1p_plan_and_record``
    取计划执行,本包装仅供锁测试与只读探针消费(test_cw_swap_plan
    意图面双向断言)。
    """
    return _m1p_plan_and_record(st, sess)[1]


def m1p_swap_execute(st: GameState, plan: SwapPlan, *, acts: list[dict],
                     spend: dict, pool: _Pool) -> tuple[GameState, bool]:
    """M1″ 执行面 sim 转录:计划非空 → 逐件卖 victim(卖出臂)。

    T-169 最小执行面(总图设计 R2 §2 sim 边界行):生产链 = mandate 发射
    RunDeploy(m1_swap_redeploy)+ CwOpDeploy 卖出臂现读逐件卖 +
    部署 op 补上;sim 对应物 = 本函数卖 victim + 引擎轮末部署块残余
    补部署补上(调用方据返回值置显式动作旗 → skip_fence+residual_
    fill,与显式动作轮同语义)。卖出执行走 ``cw_state.simulate`` 单一源
    (金回充/装备回收/板面重算全在源内),账本转录行带 name+reason=
    'm1_swap_redeploy'(换血可见性的判读锚;既有显式动作行无名,本行
    加键不破消费)。victim 槽位 = 按 char_id 现读(占用件同名唯一,W43
    板面约束);单一源拒绝(原子性防线)= 零行为转录如实跳过。

    同构边界申报(T-169 落地审 F2):生产发射位门**未镜像**——生产
    plan.nonempty 后还有 m1p_defer_levelup(同帧 LevelUp 抑制,mandate
    发射位)与 P79-3 转型门(_redeploy_emission_allowed)两道 defer,
    sim 只看 plan.nonempty 即执行 ⇒ sim 换血活跃度结构上 ≥ 生产
    (defer 帧在 sim 照换;plan.arm 不入记录,P79-3 缺口不可从账本测)。
    当前批 defer 缺口实测共现 0(锚批 680 执行帧同轮 LevelUp=0),若
    后续策略批抬升 defer 触发率,换血读数会系统性偏置——显影键
    (arm/defer)归后续批。

    拒绝路径显影申报(T-169 落地审 F6):单一源拒绝帧**无账本痕迹**
    (不追加 rejected 行、不进 explicit_action_rejects;显式动作路径
    对 rejected 有逐行+reject_reason 纪律,本路径防御分支未对齐)——
    消费面只能按 m1p 记录 nonempty=1 而 executed 缺失反推。本锚批
    680/680 全 applied 未触发;rejected 行转录/计数键归后续批。

    :param acts: 轮账本动作流(调用方 ``_acts``,就地追加转录行);
    :param spend: 轮经济账(调用方 ``_spend``,sell_income 就地累加);
    :param pool: 有限牌池(卖出回池 ``ret``,与 SellBench 通道同守恒);
    :returns: (卖出后的新 GameState, 是否有任一 victim 真卖出)。
    """
    sold_any = False
    new_st = st
    for name in plan.sell_names:
        idx = next((i for i, d in enumerate(new_st.deployed)
                    if d is not None and d.char_id == name), -1)
        if idx < 0:
            continue   # victim 已不在场(防御;同帧装配不会走到)
        victim = new_st.deployed[idx]
        applied_st = _simulate_state(
            new_st, SellDeployed(deployed_idx=idx,
                                 reason='m1_swap_redeploy', expect=name))
        log = applied_st.action_log[-1] if applied_st.action_log else {}
        if log.get('result') != 'applied':
            continue   # 单一源拒绝 → 零行为转录(与显式动作分支同口径)
        new_st = applied_st
        refund = sell_refund(victim.star, _bench_char_cost(victim))
        spend['sell_income'] = spend.get('sell_income', 0) + refund
        if name:
            pool.ret(name)
        acts.append({'__type__': 'SellDeployed', 'deployed_idx': idx,
                     'name': name, 'income': refund,
                     'reason': 'm1_swap_redeploy', 'result': 'applied'})
        sold_any = True
    return new_st, sold_any


def _line_member_names(sess) -> frozenset[str]:
    """当前线名册集合(T-153 生成侧自算披露的计算 helper;ADR-0593)。

    名册单一源 = predicates.line_members;过渡配方标签解析与
    check_levelup_budget_gate._k_members 同式(生产/sim 同解析)。
    空 target/解析失败 = 空集——披露键写 False,复核面按
    selfcalc 的三态语义(键在场∧空名册 = 不可复核腿)处置。
    纯读:sim 决策执行点调用的观测底座,零 rng/零状态写入。
    """
    label = _target_comp_label(sess)
    if not label:
        return frozenset()
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    from sr_od.application.currency_war.kernel.cw_intention import (
        pair_target_comp,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
        line_members,
    )
    if label.startswith('过渡配方·'):
        comp = pair_target_comp(
            tuple(label.removeprefix('过渡配方·').split('+')))
    else:
        comp = get_comp(label)
    if comp is None:
        return frozenset()
    return frozenset(line_members(comp))



def simulate_p1(seed: int, *, use_refresh: bool = True,
                strategy=None, session=None,
                pool: str | Path = 'auto',
                diamond_cap_prob: float = 0.0,
                config=None,
                planes: int = 1,
                invest: SimInvestProfile | bool = False,
                invest_arm: str = 'sink',
                p2_combat: P2CombatCalib | None = None,
                synthesis_chain: bool = False,
                equip_wear_effect: float = 0.0,
                _p2_entry: P2ReplayEntry | None = None) -> SimResult:
    """单局位面段模拟(决策跑真策略代码;P1 段为主,``planes>=2``
    追加 P2 段——`w157_p2/`/ADR-0362 案 a 最小可用)。

    :param seed: 随机种子(同 seed 同局,可复现——**须同池指纹**,
        见 ``pool``;SimResult.pool_fingerprint 记录本局所用池)
    :param planes: 1=P1 九轮(默认,**逐位不变**——回归门=旧代码
        同 seed 同池 diff={});2=P1 段后追加 P2 七轮段(进场继承
        P1 末态 hp/gold/board/bench/deployed/equips/意向,ADR-0362):
        P2 节点序列 = ``P2_NODE_SEQUENCE`` 观测拼版、结算 = Δ池
        plane=2 桶优先/回退掉血带 15-17、事件金复用 P1 表(打标
        未校准,P2 基础收入 5 已实测,economy.md §10.1);P2 段
        观测进 SimResult.p2_* 字段。3+(P3)未实现,显式拒绝。
    :param use_refresh: False 时剔除 RefreshShop 动作(A/B 对照用)
    :param strategy: 注入策略(默认 DecisionV2Strategy;测试可换桩)
    :param session: 注入会话(默认新建;跨局复用场景可传)
    :param pool: Δ 池三态(⓪):'auto'(生产 replay,缺源 raise)/
        'snapshot'(主仓提交快照,CI/跨机基准)/'fallback'(显式
        退旧模型,结果打标)/Path(JSON 快照,历史重放)。
        A/B 对照同进程同池即可;**跨日基线对照须核指纹一致**。
    :param diamond_cap_prob: 财富宝钻获取通道(ADR-0286/迁移审计批 F4):每备战期
        以此概率获得 1 颗财富宝钻(cap = level + 宝钻数,可叠加)。**注入频率
        待实机语料统计,默认 0 = 通道建好但不注入**(baseline 与旧树可配对)。
    :param config: 策略配置桩(默认 None)。decision_v2 栈不读 config
        (唯一策略载体;default 栈已退役,off 臂=冻结快照 worktree)。
    :param invest: 投资策略/环境注入(`w162_inject/`/ADR-0364;默认 False =
        不注入,**主路径逐位零漂移**)。True = 按 seed 确定性采样
        (plaza 实选频次表,见 cw_sim_invest);传 ``SimInvestProfile``
        = 固定剧本(测试/A-B 配对臂)。注入写 session+state 的
        active_strategies/active_env(实机 handler 语义),经济聚合
        (economy_effect_of 链的已建模子集)在 sim 收入/刷价层生效,
        意向层①资格通道(ADR-0338)因此可点火。
    :param invest_arm: 投资选卡决策臂(``invest`` 真值时才有意义;
        T-155 前置批,见 cw_sim_invest 模块 docstring 双臂节):
        'sink'(缺省)= **基线臂**——选卡槽采样 3 候选,选哪张由真实
        判据 ``strategy.decide_invest``(flow 委托 kernel decide_event)
        裁决,归因透传 ``SimResult.invest_picks``;'freq' = 旧频次注入
        对照臂(plaza 名直注入,decide_event 零消费)。固定剧本
        (``invest=SimInvestProfile``)不受本开关影响(显式点名 = 直注入)。
        要求策略对象具备 flow 接口 ``decide_invest``(缺省 mandate_v1
        满足;测试桩策略不带该接口时基线臂响亮报错——基线臂的存在
        意义就是消费真实判据,静默降级 = 假验证)。
    :param p2_combat: P2 战斗存活层参数族(`w193_p2sim/`/ADR-0377;None=模块
        默认 ``P2_COMBAT_DEFAULT``)。``calibrated=False`` 臂逐位回
        `w157_p2/`/ADR-0362 行为(Δ池 plane=2 优先 + 恒值回退档)——A/B
        与回退对照臂;planes=1 路径不消费本参数(零漂移)。
    :param _p2_entry: 案 b 臂进场态注入(内部参数;``simulate_p2_replay_entry``
        构造——跳过 P1 段与开局 bench 采样,直接从真值进场态跑 P2 段。
        共享本函数的 P2 段循环体 = 单一源,迁移审计 w186(git 历史) 设计 §4 的消复制形态)。
    """
    if planes not in (1, 2):
        raise ValueError(
            f'planes 参数非法: {planes}(1=P1 段;2=P1+P2 段,ADR-0362;'
            'P3 语料零样本未实现——案 c 缓,迁移审计 w156(git 历史) 裁决)')
    pool_map, pool_fp, pool_src = resolve_pool(pool)
    rng = random.Random(seed)
    # 装备面执行链参数(默认全关 = 既有行为逐位零漂移):
    # _synth_on = 合成执行 hook(组件凑齐需求线配方即装备栏内合成);
    # _wear_eff = 已穿进阶成品对败局伤害的折减系数/件(校准假设层,
    # 量级无实机定量锚点,由 A/B 灵敏度带呈报,见结算段注释)。
    _synth_on = bool(synthesis_chain)
    _wear_eff = max(0.0, float(equip_wear_effect))
    cards_pool = _Pool(rng)   # 命名避参数遮蔽(审查 minor:pool 参数)
    # ADR-0272:池构造后硬断言无费用截断(不变式;检查函数单一源
    # 在 cw_sim_checks——纯 dict 入参,不构成 import 环)

    from sr_od.application.currency_war.sim.checks.ledger import (
        check_sim_pool_no_cost_truncation as _chk_pool,
    )
    if _chk_pool(cards_pool.copies)['violations']:
        raise RuntimeError(
            'sim 牌池被费用截断(4/5 费角色缺失)——ADR-0272 禁止;'
            '检查 cw_sim._Pool 构造')
    nodes = sample_node_sequence(rng)   # r260:本局节点序列(9 项)
    # 决策层注册表用 sim 视图(level_max=LEVEL_CAP,见 sim_decision_
    # registry):满级帧决策层不再发起升级,执行层拒付层保留作防线。
    if strategy is not None:
        strat = strategy
    else:
        # sim 默认被测体 = mandate_v1 单臂(统一迁移批 A9 裁决:与实机同源)
        from sr_od.application.currency_war.strategies.impl.mandate_v1.bridge import (
            MandateV1Strategy,
        )
        strat = MandateV1Strategy(registry=sim_decision_registry())
    # 观测键评估用的注册表(降格触发面等纯谓词;注入桩策略无 registry
    # 属性时回退 sim 视图——与默认策略同源,不依赖被测对象形状)
    _obs_registry = (getattr(strat, 'registry', None)
                     or sim_decision_registry())
    if _p2_entry is not None:
        # `w193_p2sim/`/ADR-0377 案 b 臂:P1 段与开局 bench 采样跳过,直接从
        # 真值进场态起跑(rng 不耗 nodes/bench 采样——进场态是外生
        # 真值,重放可复现性 = seed + 进场态 + 池指纹)。下方**共享**
        # 位面段循环体(单一源;与 simulate_p1 主入口零复制)。
        if invest:
            raise ValueError('案 b 臂(_p2_entry)不支持 invest 注入')
        st = _p2_entry.build_state()
        sess = session or StrategySession(
            rng=random.Random(f'sim-p1-entry-{seed}'))
        # 初始相位经统一 sim 构建口注入(session.md §3.4-2:禁裸 setattr
        # session 策略字段;ensure_strategy_state = 被测策略工厂薄 helper)。
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            ensure_strategy_state,
        )
        ensure_strategy_state(strat, sess, initial_v2_state=(
            'economy', False, False, 0, 0, 0, 0, 0))
        streak = _p2_entry.streak
        # 带符号 streak(生产口径:连胜 +/连败 −,结算「连胜×N」前缀=方向;
        # 本地 `streak` 是收入侧无符号连胜计数,语义不同勿合并——收入分支
        # `streak == 0 and _prev_combat_lost` 依赖无符号归零,改带符号会断
        # ADR-0439 败轮金路径)。案 b 臂进场真值自带带符号值。
        streak_signed = int(_p2_entry.streak or 0)
    else:
        st = GameState()
        st.plane, st.level, st.gold, st.hp = 1, 3, 5, 80
        # bench 槽位表(ADR-0316):GameState() 已 pad 9 空槽,勿重置为
        # 紧缩 [](会让 bench_place 只见 0 槽 → 全部买入失败)
        for _ in range(START_BENCH_COUNT):
            cost = rng.choices(
                [c for c, _ in START_BENCH_COST_WEIGHTS],
                weights=[w for _, w in START_BENCH_COST_WEIGHTS], k=1)[0]
            names = [n for n in cards_pool.copies
                     if CHARACTERS[n].cost == cost and cards_pool.copies[n] > 0]
            if names:
                n = rng.choice(names)
                cards_pool.take(n)
                bench_place(st.bench, BenchChar(
                    slot=0, char_id=n,
                    faction=(CHARACTERS[n].factions or ['散'])[0]))
        # 会话随机流从局 seed 派生(w910_sim_determinism/REPORT):与上方
        # rng(引擎采样流,seed 派生)同源不同流,杜绝裸 StrategySession()
        # 的 OS 熵默认——未来决策层接入 rng 消费时,同 seed 局天然可复现。
        sess = session or StrategySession(
            rng=random.Random(f'sim-p1-{seed}'))
        # 初始相位经统一 sim 构建口注入(session.md §3.4-2;同上案 b 臂)。
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            ensure_strategy_state,
        )
        ensure_strategy_state(strat, sess, initial_v2_state=(
            'economy', False, False, 0, 0, 0, 0, 0))
        streak = 0
        streak_signed = 0
    # hp 决策可信位对齐生产真读帧口径(sim 无识别过程 = 恒真值帧;生产
    # 真读帧两位皆 True,写入点语义 = operations/cw_op/cw_op_buy_cards.py `_apply_hp`
    # 真读分支。hp_readable 本就恒 True,本位对齐后 hp_decision_trusted
    # 读数不变,纯口径一致化零行为漂移)。
    st.hp_trusted = True
    # 开局帧带符号 streak 兜 0(生产备战帧 state.streak = session.last_streak,
    # 默认 0 非 None;结算逐轮覆写见下方结算段)。案 b 臂 build_state 已带。
    if st.streak is None:
        st.streak = streak_signed
    # (期望态离线口径段已随 ADR-0651 两态制删除:expected_state 条目表
    #  容器不存在,sim 无挂账对账环节;op 效果 = 字段直推。)
    # `w162_inject/`/ADR-0364:投资注入剧本解析(独立 rng 流,默认 False 零开销)。
    # 语义位 = session(持久宿主,handler 写点单一源参照)+ state(生产
    # 由 cw_observation 每帧同步,此处注入点直写两处 = 等价语义)。
    # T-155 前置批双臂(见 cw_sim_invest 模块 docstring):'sink' 基线臂 =
    # 采样器供 3 候选、真实判据裁决;'freq' 对照臂 = plaza 名直注入(原形态)。
    _inv: InvestInjectionState | None = None
    _sink: SinkInvestSampler | None = None
    if isinstance(invest, SimInvestProfile):
        _inv = InvestInjectionState.build(invest)
    elif invest:
        if invest_arm == 'freq':
            _inv = InvestInjectionState.build(sample_invest_profile(seed))
        elif invest_arm == 'sink':
            if not callable(getattr(strat, 'decide_invest', None)):
                raise ValueError(
                    'invest_arm="sink"(基线臂)要求策略对象具备 decide_invest '
                    f'(flow 接口);当前策略 {type(strat).__name__} 不带——基线臂 '
                    '的存在意义就是消费真实判据,禁静默降级')
            _sink = SinkInvestSampler(seed)
        else:
            raise ValueError(
                f"invest_arm 非法: {invest_arm!r}('sink'=基线臂(真实判据)|"
                "'freq'=旧频次注入对照臂)")
    # 基线臂选卡归因记录(局级;env 开局 1 条 + 逐选卡槽 1 条,见下方两写点)
    _inv_picks: list[dict] = []
    # env 归因条(单列引用;账本侧挂在 P1 r1 行——entry 口径,同 schedule
    # (1,1) 必选注释的时点语义;局级明细仍以 _inv_picks 为全集)
    _env_pick_rec: dict | None = None
    if _inv is not None:
        if _inv.profile.active_env:
            sess.active_env = _inv.profile.active_env
            st.active_env = _inv.profile.active_env
    elif _sink is not None:
        # 基线臂·开局环境选卡:3 候选 → decide_invest('env') 裁决。
        # 时点对齐生产 entry 流程(简报→投资环境屏);state 用开局真值帧
        # (board 空 = overlay 上 board 不可读的生产语义,decide_event 的
        # DoT 惩罚不触发);comp 未定(None)与生产开局环境屏同态。
        _env_opts = _sink.sample_env_options()
        if _env_opts:
            _env_pick = strat.decide_invest(
                'env', list(_env_opts), st, sess, config)
            _env = _env_opts[_env_pick.option_idx]
            sess.active_env = _env
            st.active_env = _env
            _env_pick_rec = {'kind': 'env', 'plane': 1, 'round': 1,
                             'options': list(_env_opts), 'picked': _env,
                             'reason': _env_pick.reason}
            _inv_picks.append(_env_pick_rec)
    # 供给重校准:装备发放结构版本并入指纹(+eqgN 位)——发放结构是
    # 行为语义的一部分,新旧结构不可比,跨版本对照必须显式失败。
    pool_fp = f'{pool_fp}+eqg{EQUIP_GRANT_CALIB_VERSION}'
    res = SimResult(seed=seed, pool_fingerprint=pool_fp,
                    pool_source=pool_src)
    if _inv is not None:
        res.invest_env = _inv.profile.active_env
    xp = 0 if _p2_entry is None else _p2_entry.xp
    # ADR-0286(批㉓ F3):xp_progress 真值化——sim 结算处维护(与生产 OCR 真值
    # 同语义),买牌/买经验累 XP_PER_BUY,升级按 XP_TO_NEXT_LEVEL 清零结转;
    # line_v2 的 clicks_to_next_level 消费点从此读到真值(旧恒 None → 恒按
    # 0 进度向上取整,追级类 EV 在 sim 系统性偏)。案 b 臂=进场真值直带。
    st.xp_progress = (_p2_entry.xp_progress if _p2_entry is not None
                      else (0, XP_TO_NEXT_LEVEL.get(st.level, 4)))
    # ADR-0286(迁移审计批 F4):财富宝钻通道(注入频率参数化,默认 0 不注入)
    _diamonds = 0
    # `w614_sim_fidelity/` 保真三补的局级计数器(纯观测,不进 rng 流;默认路径全 0):
    _equip_grants = 0    # 装备发放件数
    _equip_wears = 0     # 装备穿戴件数(owned→已穿)
    _equip_syntheses = 0  # 装备栏内合成成品件数(合成链 hook 点火时)
    _refresh_xp_total = 0  # 付费刷新产经验累计(xp_per_refresh)
    _rust_peak = 0       # 生锈暴露峰值 min(10, 未穿件数;P1 段)
    _bench_recipe_rounds_p1 = 0   # P1 配方件躺 bench 轮数累计(件×轮)
    _dep_power_sum_p1 = 0.0       # P1 上阵战力贡献代理累加
    _dep_power_rounds_p1 = 0      # P1 计均值用的轮数
    # ADR-0362(`w157_p2/`):位面段迭代——P1 段(9 轮)后按 ``planes``
    # 追加 P2 段(7 轮)。planes=1 时段表只含 P1 段,循环体逐位
    # 同旧(RNG 消耗序不变 = P1 零漂移回归门)。案 b 臂(`w193_p2sim/`)段表
    # 只含 P2 段(直接从真值进场态起跑)。
    _ts = 0   # 单调轮序号(跨位面累计;P1 段恒 == rn)
    # ADR-0439:上一轮节点与败胜态(败轮金路径——收入在下一轮开头入账,
    # 败轮结算金按**败掉那轮**的节点类型取 LOSS_GOLD_BY_NODE;跨位面
    # P1 末 boss 败 → P2 r1 收入同规则)。奖励/补给轮无结算,不清败态
    # 也不改 streak(与结算段口径一致)。
    _prev_node: str | None = None
    _prev_combat_lost = False
    if _p2_entry is not None:
        _segments: list[tuple[int, int, list[str]]] = [
            (2, P2_ROUNDS, list(P2_NODE_SEQUENCE))]
    else:
        _segments = [(1, 9, nodes)]
        if planes >= 2:
            _segments.append((2, P2_ROUNDS, list(P2_NODE_SEQUENCE)))
    # `w193_p2sim/`/ADR-0377:P2 战斗存活层参数族(单一注入点;None=模块默认)
    _p2c = p2_combat if p2_combat is not None else P2_COMBAT_DEFAULT
    for _seg_plane, _seg_rounds, nodes in _segments:
        if _seg_plane >= 2:
            # 进场继承块(ADR-0362):P1 末态 hp/gold/board/bench/
            # deployed/equips/意向**原样带过**——HP 跨位面继承是
            # 用户纠错真值(2026-08-23,economy.md §10.2);金/board/
            # equips 跨位面无重置证据,按全继承+标注假设(迁移审计 w156(git 历史) 表
            # #4)。决策代码 plane-aware:p1_pair 进 P2 由意向层
            # 自动清(cw_intention,ADR-0357),策略层零改动。
            st.plane = _seg_plane
            res.p2_entered = True
            # 生产语义对齐:开局帧槽序表写 session(cw_screen_prep
            # 首帧写;battles_left_p2 消费,ADR-0361)
            sess.plane_node_table = list(nodes)
            # ADR-0368(迁移审计 w169(git 历史)):位面日程真值序列(生产=cw_screen_prep 每位面
            # 首帧 append;sim P1 段不写表 → 进场补记 P1 真值 9,保
            # seen 序=位面序;cw_plane_table.schedule_of 消费)
            sess.plane_node_table_plane = _seg_plane
            _seen = sess.plane_lengths_seen
            if _seen is None:
                _seen = []
                sess.plane_lengths_seen = _seen
            from sr_od.application.currency_war.kernel.cw_plane_table import (
                NODES_PER_PLANE as _NPP,
            )
            while len(_seen) < _seg_plane - 1:
                _seen.append(_NPP)
            _seen.append(len(nodes))
        else:
            # T-263 对齐写点(P1 段):生产语义 = cw_screen_prep 每位面首帧
            # 写 plane_node_table + plane_lengths_seen(store_plane_table),
            # 此前 sim P1 段不写表 → 前窗查表谓词(front_window_frame,
            # ADR-0635)在 sim 结构性盲(P2 进场写点只辖 _seg_plane>=2)。
            # 纯 session 真值回填:零 rng 消耗、零既有消费面变化(表此前
            # 在 P1 段无读者);plane_lengths_seen 结果与旧回退路径逐位
            # 一致(P1 段 append 9,P2 进场 while 短路后 append 本段长)。
            sess.plane_node_table = list(nodes)
            sess.plane_node_table_plane = _seg_plane
            if sess.plane_lengths_seen is None:
                sess.plane_lengths_seen = []
            if not sess.plane_lengths_seen:
                sess.plane_lengths_seen.append(len(nodes))
        for rn in range(1, _seg_rounds + 1):
            _ts += 1
            st.round_num = rn
            # 基线臂本轮选卡归因条(env 条挂 P1 r1 行,见 _env_pick_rec 注)
            _round_pick_recs: list[dict] = (
                [_env_pick_rec]
                if (_env_pick_rec is not None and _seg_plane == 1 and rn == 1)
                else [])
            # 批⑤ F4(ADR-0276):决策前写 session.node_type_current——
            # 生产语义 = cw_screen_prep 备战期存下一节点类型(r308 保连胜
            # 门/节点感知消费读 session);sim 旧不写 → 门在 sim 恒盲
            # (300 局「地板降 5」0 次)。词表与 sim nodes 同源
            # (battle/encounter/boss/…)。
            sess.node_type_current = nodes[rn - 1]
            # 决策帧同点填充 st.node_type(「2026-09-08 奖励帧策略审查」
            # 建议①可见性批):规则①/②(b) 的帧型判据单一源
            # reward_node_suppressed 按帧 node_type 判(ADR-0580),此前
            # sim 决策帧该字段恒 None → 抑制在 sim 全域 fail-open,同一
            # 决策核在 sim/实机两域语义分叉(实机可辨面 = ADR-0587 台账制)。
            # 与上行同源同点,词表同为策略层 token 层('reward' 等,
            # sample_node_sequence/P2_NODE_SEQUENCE)。填充分支零行为改变
            # 边界:除本字段外帧内容逐位不变、不消耗 rng;申报行为面 =
            # 规则①四消费位与 ②(b) 在 sim 奖励帧按实机语义生效(审查
            # 定谳「属修复非波及」),遥测面 = 硬节点门计数与
            # v3_piggy_reward 刷新点(两者均无决策分支消费)。
            st.node_type = nodes[rn - 1]
            # ① 账本:收入分解(rng 消耗序不变——event 先取后加,同原式)
            _gold_before = st.gold
            _inc_event = _event_gold(rn, rng)   # 事件金 ADR-0233
            # `w193_p2sim/`/ADR-0377:事件金双臂(K3 零样本敏感性)——'zero' 臂
            # P2 段事件金归零;rng 照耗(双臂同 seed 配对可比)。
            if st.plane >= 2 and _p2c.event_gold == 'zero':
                _inc_event = 0
            # `w162_inject/`/ADR-0364:注入策略的经济聚合(economy_effect_of 链已建模
            # 子集)——息帽覆写 + 每节点给金。无 active_strategies 时表达式
            # 与旧逐位相同(零漂移);'invest' 键只在有持卡时才加(账本行
            # 形状对默认路径不变)。
            _agg_inv = (aggregate_economy(st.active_strategies)
                        if st.active_strategies else None)
            _icap = INTEREST_CAP
            if _agg_inv is not None and _agg_inv.interest_cap_override is not None:
                _icap = _agg_inv.interest_cap_override
            _node = nodes[rn - 1]
            # ADR-0439 收入口径(实机 gold 差分实证,108 局/767 轮):
            # - 败轮金:连胜结算 streak==0 且上一轮是败掉的战斗类节点 →
            #   发 LOSS_GOLD_BY_NODE[prev_node](普通 2/遭遇 4/boss 4),
            #   替换旧 streak_gold(0)=1(弹窗口径,与实发不符);
            # - 奖励轮:streak 分量照发 streak_gold(streak)(含 counter0=1;
            #   ADR-0351「奖励轮不发金」半句被全量数据推翻)+ base 查表
            #   REWARD_BASE_GOLD_BY_ROUND——**成对改**:旧 BASE_INCOME=5
            #   恰好盖住这 1 金,单改 streak 会变多发(净差≈0);
            # - 补给轮不动(仍零 streak + base+利息;实发零发放的证据
            #   样本不足,条件升级挂账 ADR-0439)。
            if _node == 'supply':
                _streak_amt = 0
            elif _node == 'reward':
                _streak_amt = streak_gold(streak)
            elif streak == 0 and _prev_combat_lost \
                    and _prev_node in LOSS_GOLD_BY_NODE:
                _streak_amt = LOSS_GOLD_BY_NODE[_prev_node]
            else:
                _streak_amt = streak_gold(streak)
            # 利息 flat 分量(前置缺陷 R92-4 修复;缺陷登记原文已删档,
            # 取回口径=ADR-0644):
            # 狸财经狸 interest_flat_per_node=每节点固定息,**与 interest_cap 无关**
            # (EconomyEffect 字段注释语义)——量值与存在性单一源 = cw_investments
            # 注册表(STRATEGY_ECONOMY),sim 侧不另设常量。无持卡/flat=0 时 +0,
            # 主路径逐位零漂移(与既有 interest_cap_override 消费同构)。
            _flat = (_agg_inv.interest_flat_per_node
                     if _agg_inv is not None else 0)
            _inc = {'base': (REWARD_BASE_GOLD_BY_ROUND.get(rn, BASE_INCOME)
                             if _node == 'reward' else BASE_INCOME),
                    'interest': min(_icap, st.gold // 10) + _flat,
                    'streak': _streak_amt,
                    'event': _inc_event}
            if _agg_inv is not None and _agg_inv.gold_per_node:
                _inc['invest'] = _agg_inv.gold_per_node
            st.gold += sum(_inc.values())
            # `w162_inject/`/ADR-0364:本轮策略选卡注入(overlay 在备战期出现 → 收入
            # 结算后、决策前;实机写点 = cw_screen_invest_strategy 的 session
            # append+去重)。instant_gold 在选卡时点入账(生产游戏引擎同点)。
            # 免费刷额度在选卡后按当前持卡聚合重算(当轮选的卡当轮生效)。
            # T-155 前置批:freq 臂 = 日程直采名;基线臂('sink')= 采样器供
            # 3 候选 → 真实判据 decide_invest 裁决(flow 委托 decide_event,
            # 含 CommitSignals 喂入 = 生产 handler 同路径),归因透传
            # _pick_rec → res.invest_picks / 账本行。采纳语义(append+去重+
            # 经济入账)两臂同一代码路径。
            _pk = None
            _pick_rec: dict | None = None   # 基线臂判据归因(freq 臂恒 None)
            if _inv is not None:
                _pk = _inv.picks_by_key.get((_seg_plane, rn))
            elif _sink is not None and (_seg_plane, rn) in _sink.pick_slots:
                _opts = _sink.sample_strategy_options(sess.active_strategies)
                if _opts:
                    _pe = strat.decide_invest(
                        'strategy', list(_opts), st, sess, config)
                    _pk = _opts[_pe.option_idx]
                    _pick_rec = {'kind': 'strategy', 'plane': _seg_plane,
                                 'round': rn, 'options': list(_opts),
                                 'picked': _pk, 'reason': _pe.reason}
                    _inv_picks.append(_pick_rec)
                    _round_pick_recs.append(_pick_rec)
            if _pk is not None and _pk not in sess.active_strategies:
                sess.active_strategies.append(_pk)
                st.active_strategies = list(sess.active_strategies)
                _pk_econ = economy_effect_of(_pk)
                st.gold += _pk_econ.instant_gold
                if _pk_econ.xp_instant > 0:
                    # 一次性经验选卡时点入账**一次**(接缝面批 S-4:
                    # xp_instant oneshot 位的生产对位——登记表独立
                    # 操作数 'xp_instant',禁并入每节点 flow 重复入账;
                    # 生产由游戏引擎同点入账、决策侧 XP 条读数已含,
                    # 壳只披露不叠加,防双计)。
                    xp += _pk_econ.xp_instant
                    st.xp_progress = (
                        xp, XP_TO_NEXT_LEVEL.get(st.level, 4))
            _free_r = (_agg_inv.free_refresh_per_node
                       if _agg_inv is not None else 0)
            if _inv is not None:
                # 注入局:免费刷额度按**选卡后**持卡重算(当轮选的卡当轮生效)
                _free_r = (aggregate_economy(st.active_strategies)
                           .free_refresh_per_node
                           if st.active_strategies else 0)
            _free_used = 0
            # ADR-0286(批㉓ F4)轮岗事件——**已勘误重建模**(01 §4.10 概率表族,
            # DESIGN_FINAL_ATTACK 阻断-2):旧「ROTATION_CHANCE=0.2 无条件掷
            # 事件」把 replay 观测在场频率误当机制概率。机制语义 = 已选轮岗
            # 环境后**每备战阶段 100% 重掷翻倍档**(翻倍档 1/5 均匀系建模
            # 假设,实机待核);未选环境恒基线表(None)。
            # 条件位 = st.active_env(注入点写 session+state 双处,见上方
            # _inv 装配;生产 handler 同字段语义)。
            if (getattr(st, 'active_env', '') or '') == '轮岗':
                st.refresh_probs = roll_rotation_per_stage(rng, st.level)
            else:
                st.refresh_probs = None
            # ADR-0286(迁移审计批 F4):宝钻通道(默认 prob=0 不掷,保 baseline 可配对)
            if diamond_cap_prob > 0 and rng.random() < diamond_cap_prob:
                _diamonds += 1
            # cap 真值 = level + 宝钻数(生产 read_deploy_cap 语义);无宝钻 None
            # → max_units() 兜底 level(与生产防抖拒信路径同态)
            st.deploy_cap = st.level + _diamonds if _diamonds else None
            st.shop = cards_pool.draw_shop(st.level, probs=st.refresh_probs)
            _waves = [{'event': 'offer', 'gold': st.gold,
                       'cards': [{'name': c.name, 'faction': c.faction,
                                  'cost': c.cost} for c in st.shop],
                       # 拒因串逐波留档位(None=本波无决策段:8 段上限
                       # 截断等;决策段覆写,见轮决策循环)
                       'rejects': None}
                      ]   # ① 账本:牌面波(supply 视图;gold=该波时点金)
            # ① 账本:轮内聚合(段结构折叠,花销/买入逐笔记)
            _spend = {'buys': {}, 'levelup': 0, 'refresh': 0, 'sell_income': 0}
            _merges = 0   # ADR-0276:本轮 3合1 合并次数(账本 sim.merges)
            _refresh_xp_round = 0   # `w614_sim_fidelity/` G3:本轮付费刷新产经验(账本披露)
            _bench_full_skips = 0   # ADR-0283 守卫:本轮满栏**非合成**拒买数(合成买已执行,不计入——`w566_sim_guard/` 语义收窄)
            _bench_full_skip_gold = 0   # ADR-0285:非合成拒买折算金(净滞留口径)
            _phantom_rebuys = 0   # ADR-0284:已消费槽/店外买提案数(应恒 0)
            # 满级 LevelUp 拒付计数(执行层 cap 守卫披露;>0 = 决策层在
            # 满级态仍发升级,策略侧判读输入)
            _lv_cap_rejects = 0
            # M-A 定向刷新轮归因基线(局级累计计数器只增不减;轮末差值 =
            # 本轮被定向车道放行并执行的刷新数,刷帽检查 directed_refresh_
            # game_cap_lock 的数据源。计数器在 arbiter 采纳处递增,本侧
            # 只读——观测非指令)
            _dir_used0 = int(getattr(strategy_state_of(sess), 'v3_dir_refresh_used', 0) or 0)
            # 动作 v2(契约包 C1,步2):本轮策略是否发出**且被应用**的显式部署
            # 动作(SellDeployed/SwapDeploy/CompTransaction)——是则轮末围栏
            # 跳过自动部署并记 skip_fence(裁决1:显式>围栏,同轮互斥;
            # 迁移审计 w65(git 历史)/ADR-0323:被拒事务不置位,围栏照跑)
            _explicit_deploy_seen = False
            _acts: list[dict] = []
            _segs_used = 0
            # ADR-0343:成型停手轮内 OR 聚合——一轮多决策段,演进事务可
            # 轮中改变板面使成型态中途点亮(段前的买入合法);行标志=
            # 「本任一段曾处于停手态」(检查器豁免消费:有买的轮本就
            # 不进 streak,OR 只会多豁免「全轮零买且曾成型」的轮=停手线
            # 语义正确辖域)
            _round_formed_stop = False
            # ===== 观测硬依赖键·决策入口快照(W793 后继批;取**决策时点**
            # 值而非轮末——席满/下档判读须与腾席/刷新动作同帧对齐,生产
            # decisions 行同口径)**=====
            # - bench_full_flag:满栏旗标(消费 = 锁#10 D1 弱序量产对账,
            #   PREREG 兑现链 v3 判读;生产读端 review_skeleton.merge_round_rows 按
            #   state.bench_full_flag 消费,sim 侧自此有真值源——W797
            #   不可测项「恒 null」的 sim 收口)。轮内 OR 聚合(生产
            #   merge 同式:「任一决策帧满栏」;bench 在轮内买入段才
            #   填满,轮入口快照会系统性漏亮)。sim 满观测无 OCR 缺读,
            #   恒 bool(生产 bool|None 的 None 态在 sim 不存在)。
            _round_bench_full = False
            # - board_next_tier:各阵营下档阈值(观测披露面;兑现链开关族
            #   已随旧方案清退批删除,键保留作判读面)。
            _round_board_next_tier = _board_next_tier_of(
                _board_factions_of(st.deployed))
            # - ADR-0474 分配器遥测键(消费 = 锁#11 D2 接管可观测性):
            #   alloc_frame = 本轮最后一段 decide_prep 的分配器帧位
            #   (strategy_state_of(session).v3_alloc_frame 每段覆写,末值 = 轮终帧披露;
            #   此前该帧位无任何落盘消费面);alloc_active_any = 轮内
            #   任一段接管过(OR 聚合,与 formed_stop 同式)。
            _round_alloc_frame = None
            _round_alloc_active_any = False
            # `w227_handoff_gate/`/ADR-0400:P1 末窗承接门缺口观测(轮入口首段快照;
            # formed_stop 承接维/EV 缺口项的判读数据面)
            _round_handoff_gap = 0
            # 迁移审计 w238(git 历史)/ADR-0403:boss 投影 hp 披露(None=投影关/非末窗)
            _round_handoff_hp_proj = None
            # 血预算停手·终止豁免位轮首缺省(账本行键 terminal_release;
            # 真值由首决策段快照覆写——显式预初始化防「段循环零段」时
            # 行键 NameError,与 _round_formed_stop 同族)
            _round_terminal_release = False
            # 迁移审计 w52(git 历史)(ADR-0326):本轮补偿放弃信号快照——决策段后对比计数增量,
            # 进账本 sim.remedy_abandoned(检查项 decision_v2_remedy_loop
            # 的「连续放弃轮」数据源)
            _remedy_abandons_before = getattr(strategy_state_of(sess), 'v3_remedy_abandoned', 0)
            # 血预算停手拒付计数轮前快照(设计件 12/ADR-0448):决策段后
            # 差分进账本 sim.blood_budget_levelup_rejects(与
            # remedy_abandoned 同式的轮级差分披露)
            _bb_rejects_before = getattr(strategy_state_of(sess), 'v3_blood_budget_rejects', 0)
            # 血预算停手·搜索型刷新停付拒付计数轮前快照(设计件 12
            # §2.3-P1-c/§3.2/ADR-0451):决策段后差分进账本
            # sim.blood_budget_refresh_rejects(同式轮级差分披露)
            _bb_refresh_rejects_before = getattr(
                strategy_state_of(sess),
                'v3_blood_budget_refresh_rejects', 0)
            # 迁移审计 w114(git 历史)/ADR-0346 相位影子观测:轮入口(首决策段)快照——与生产
            # 「每轮决策入口计算一次」对齐;一轮多决策段时取首段(轮初态)。
            _round_phase: str = ''
            _round_form_ok: bool = False
            _round_b_t: int = 0   # 板面目标线承重计数(form_score 替代披露口径)
            _round_dp_posture: str = ''
            _round_reserve_cap = 0
            _round_reserve_overflow = 0
            _round_release_budget = 0
            _round_release_reason = ''
            _round_posture_unfulfilled: dict | None = None
            _phase_snap = False
            # 商店波未买牌拒因串(轮内逐决策段覆写=末波口径;sim/实机
            # 同源生产端=cw4/shop.shop_unbought_reasons,落账本行顶层
            # shop_rejects——「线内核心在售未买」的供给空缺 vs 闸门拒绝
            # 判据,消费=R4 报告 §3 类复盘归因)
            _round_shop_rejects: dict[str, str] = {}
            # ===== 采购面三观察计数(sim 观测面,零策略行为改动)=====
            # 背景:sim 找问题轮定位三形态但纪律要求「先立观察面再定谳,
            # 禁直接立病灶」。三个观察面全部是**已发生决策帧的只读投影**,
            # 零 rng 消耗、零状态写入、零策略分支——挂行内 'obs' 键而非
            # 增行/动 actions(同 launch 键的先例:一轮一行/outcomes 配对/
            # 段级检查轮键/行为投影 digest 四不变式不被观测面挤占)。
            # - 超容观察:每决策帧 |locked_buy_membership| vs
            #   BENCH_CAPACITY+DEPLOYED_CAPACITY(判据与告警门同式,
            #   单一源 = cw_intention.locked_buy_membership 直调;超容帧
            #   计数 + 持续轮数由统计端按「连续轮 overcap_frames>0」聚合);
            # - 刷新触发率观察:「刷新可得帧」= 缺员(buy_members 中未
            #   owned)∧ 缺员在售 ∧ 金 ≥ interest_floor+刷价+在售最低
            #   买价——阈值口径 = 注册表 ADR-0369「[3] 单次预算前提」
            #   (interest_floor+刷价+买价),零新自由参数;对偶计数 =
            #   本轮实际刷新数(轮首差分);
            # - 冷启动买率观察:轮级 actions/spend 已入账本,r1-r4 买
            #   次数/金花费分布由统计端聚合,引擎零新键。
            _obs_locked_b = 0            # 本轮最大锁定采购集 |B|(0=帧全未锁)
            _obs_overcap_frames = 0      # 本轮超容决策帧数
            _obs_refresh_avail = 0       # 本轮「刷新可得」决策帧数
            _obs_refreshes0 = res.refreshes   # 轮首刷新数(差分 = 本轮实刷)
            # 刷新触发源分键(观测面):本轮各触发源
            # 实刷次数。源 = RefreshShop.reason 记录字段(策略层发射位
            # 写,r1 / must_spend_r1_yielded;''/未知 = other 桶)——
            # 测绘结论:刷新发射位单一(R1),L2 补位=买卡、L3 末位=
            # 升级,结构上不产刷新动作,源信息只能在策略层动作对象取
            # (引擎侧推断不了 yielded 分支),故载体 = 动作 reason 透传。
            _obs_refresh_src: dict[str, int] = {}
            # cw4_counters 轮差分(策略计数器账本可见性):
            # 策略行为观测计数(strategy_state_of(session).cw4_counters)此前不入 sim 账本
            # ——fenced 拆键(theta/fenced 成因分桶)落计数器后无账本面。
            # 轮首快照 → 行内 obs.cw4_counters = 本轮增量 dict(零增量为
            # 空 dict,不占判读视野)。纯只读投影,零行为面。
            _cw4_before = dict(getattr(strategy_state_of(sess), 'cw4_counters', None) or {})
            # ===== 必花域观测三键(20 号稿 §6;策略审查升格本批落地)=====
            # 帧型 = 商店决策段(本引擎逐段决策点);判定单一源 =
            # in_must_spend_zone(与生产同链,零第二套语义)。
            # - must_spend_zone_frames:必花域动作帧数;
            # - must_spend_zero_consume:其中零消费帧数(无花费类动作;
            #   物理残量白名单帧归此桶,判读看归因非直接判失败);
            # - must_spend_layer_hit:层命中计数(L1=普通买/刷新,
            #   L2=垫件买 fuel_filler_stall,L3=升级),dict 聚合。
            _ms_zone = 0
            _ms_zero = 0
            _ms_layer: dict[str, int] = {}
            # ===== 达标臂发射事件建模(sim 行为消费面)=====
            # 生产面:达标即出战臂(cw_loop 备战分支,14号稿 §9.6):
            # 备战双锚命中 → 判据核 readiness_launch_decision(kernel
            # cw_launch_admission 单一源;两小批①上收,零第二实现)⇒
            # 发射核 launch_prepared_battle(RunDeploy+StartBattle),
            # **短路备战动作链**——位次 = 动作链之前,门在轮入口板面
            # (买/部署前)评估。
            # sim 消费(两小批②,裁决 = ADR-0557 方案三混合):发射成立
            # ∧ 战斗类节点 ⇒ 本轮**短路决策段**
            # (不跑 decide_shop_screen,金不花——生产发射帧不产生买/刷
            # 动作,sim 行为对齐,消「金出口族 A/B 恒假阴性」的结构根);
            # 'launch' 键保留观测 + short_circuited 分键。sim 边界如实
            # 声明:发射恒成立(ok 恒 True——sim 无屏态过期/浮层在场/
            # 执行失败面,战斗节点必然结算);执行失败/浮层面不建模;
            # 战斗就绪在 sim = 节点本身为战斗类(逐轮必战结构,sim 无
            # 「等战斗」语义)。**门 = armed 单键**(三审整改:admission
            # 仅作 victim 观测位、异常吞 None——若 admission 缺失也拦
            # 短路,该帧族会留「生产短路金不花、sim 决策照常」的假阴性
            # 残留,恰为本批消除的结构根)。
            # 零漂移声明:发射判定本身零 rng 消耗;短路是生产语义对齐的
            # **行为**变更(金流分叉即本批目的)。挂行内 'launch' 键而非
            # 向 actions 追加——行为投影 digest(w614 零漂移锚)含 actions
            # 逐项,观测面不得挤占行为哨兵的判别域;「一轮一行/outcomes
            # 配对/段级检查轮键」三面不变式不破。
            # 已知边界(历史注,已被 sim71 批死镜像处置取代):mandate_v1
            # 单臂下 v3_form_ok 原无写者恒 False,不可作触发源——生产门的
            # 本源是判据核内 form_progress 现读,本消费直调同源;镜像写端
            # 现已接回 readiness_form_ok 现读(write_shop_mirrors),发射
            # 触发仍不经镜像层(防镜像缺写回归敞口)。
            _round_launch: dict | None = None
            _tc_launch = getattr(strategy_state_of(sess), 'target_comp', None)
            if (nodes[rn - 1] in ('battle', 'encounter', 'boss')
                    and _tc_launch is not None):
                from sr_od.application.currency_war.kernel.cw_launch_admission import (
                    LAUNCH_QUALITY_DEFER_FRAMES_KEY,
                    LAUNCH_QUALITY_EVAL_ERROR_KEY,
                    readiness_launch_decision,
                )
                from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
                    line_members,
                )
                _core = readiness_launch_decision(
                    st, _tc_launch, line_members=line_members)
                # 质量闸观测分键(ADR-0570 待标定①观测 sink:推迟帧/评估
                # 异常帧;best-effort,容器缺席静默跳过,与
                # launch_frame_idle_gold 同写入族;键名单一源 = kernel 常量,
                # 三审07轮 C2 禁字面量散写)。
                _cts_q = getattr(strategy_state_of(sess), 'cw4_counters', None)
                if isinstance(_cts_q, dict):
                    if _core.get('quality_eval_error'):
                        _cts_q[LAUNCH_QUALITY_EVAL_ERROR_KEY] = \
                            _cts_q.get(LAUNCH_QUALITY_EVAL_ERROR_KEY, 0) + 1
                    _q = _core.get('quality')
                    if _q is not None and _q.get('defer_by_quality'):
                        _cts_q[LAUNCH_QUALITY_DEFER_FRAMES_KEY] = \
                            _cts_q.get(LAUNCH_QUALITY_DEFER_FRAMES_KEY, 0) + 1
                if _core['armed']:
                    # form_ok 镜像现读补写(sim71 批死镜像处置的结构半边):
                    # 发射帧短路决策段 → write_shop_mirrors 本轮永不执行,
                    # 快照恒读上一轮旧值(False)= 死镜像形态在发射帧复活。
                    # armed 本身就是判据核 readiness_form_ok 现读输出,
                    # 直接落镜像位(零第二判据);session 位同写,与生产
                    # 遥测 extra(form_ok)对拍同源。
                    strategy_state_of(sess).v3_form_ok = True
                    _round_form_ok = True
                    # 发射帧滞留金观测键(sim71 批,零行为面):发射帧
                    # 短路备战动作链 → 金出口族既有键(shop_visit_idle_
                    # gold 等)全不计发射帧金,「发射帧金出口权衡」设计件
                    # 判读不可见。双层披露:①launch 行内 idle_gold =
                    # 该帧现读金(逐帧分布);②session.cw4_counters 增量
                    # 键 launch_frame_idle_gold(累计金,经 obs.cw4_counters
                    # 轮差分入账本;容器缺席静默跳过 = 缺省零漂移)。
                    _idle_gold = int(getattr(st, 'gold', 0) or 0)
                    _cts_l = getattr(strategy_state_of(sess), 'cw4_counters', None)
                    if _cts_l is not None:
                        _cts_l['launch_frame_idle_gold'] = \
                            _cts_l.get('launch_frame_idle_gold', 0) + _idle_gold
                    _round_launch = {
                        '__type__': 'LaunchBattle',
                        # 发射帧滞留金现读(逐帧口径;见上方注释)
                        'idle_gold': _idle_gold,
                        # 授权依据(判据核单一源输出;与 LevelUp.auth_basis
                        # 观测同键名族)
                        'auth_basis': _core['auth_basis'],
                        # victim = G1 准入三元观测位(异常吞 None,门不读
                        # 它——见 ADR-0557 §4)
                        'victim': _core['admission'],
                        'ok': True,
                        # 两小批②:本轮决策段被发射短路(行为消费分键;
                        # 反假阴性哨兵 check_sim_launch_short_circuit 消费)
                        'short_circuited': True,
                    }
            # ===== 发射帧受限消费仲裁(出口 B;ADR-0566)=====
            # 位次契约(DESIGN v1.1 I-2 钉死,sim 同构接线):armed 立模后、
            # 决策段循环前。两道生产闸(浮层在场/屏态过期)的 sim 结构等价物
            # = 恒真(结构盲区申报:sim 无浮层、无切屏竞态,不仿真)。
            # 区判单一源 = kernel in_launch_spend_zone(与必花域共享 g* 链):
            # - 溢出段(g>g*):决策段循环以仲裁段帽运行,段内逐动作过
            #   launch_arbitration_gate(P70 Δ息=0 形:花后金位 ≥ g*,花穿
            #   息线部分出辖=p70 边界 1);消费对象与评估序全由既有策略栈
            #   裁决,仲裁只供预算。
            # - 带内段(g≤g*):挂 L1' 独立命题 fail-closed,决策段仍零执行
            #   (证不出不花);inband 分键显影防「零消费」被误读为溢出帧
            #   无机会。
            _arb_seg_cap = 0
            _launch_budget_on = False
            _launch_arb: dict | None = None
            _arb_stop = False
            if _round_launch is not None:
                from sr_od.application.currency_war.kernel import (
                    cw_launch_arbitrage as _kla,
                )
                from sr_od.application.currency_war.kernel.cw_economy import (
                    cap_resolved_of_session as _cap_of_a,
                )
                from sr_od.application.currency_war.kernel.cw_economy import (
                    in_launch_spend_zone as _ilz,
                )
                from sr_od.application.currency_war.kernel.cw_economy import (
                    saturation_line as _sat_a,
                )
                _g0_arb = int(getattr(st, 'gold', 0) or 0)
                _cts_a = getattr(strategy_state_of(sess), 'cw4_counters', None)
                _launch_arb = {
                    'gold_before': _g0_arb,
                    'g_star': _sat_a(_cap_of_a(sess)),
                    'segments': 0, 'actions': 0, 'spent': 0,
                    'stop_reason': '', 'gate_blocks': 0,
                }
                if _ilz(_g0_arb, sess):
                    _launch_budget_on = True
                    _arb_seg_cap = _kla.LAUNCH_ARBITRAGE_SEGMENT_CAP
                    _launch_arb['zone'] = 'overflow'
                    if _cts_a is not None:
                        _cts_a[_kla.KEY_ZONE_FRAMES] = \
                            _cts_a.get(_kla.KEY_ZONE_FRAMES, 0) + 1
                else:
                    _launch_arb['zone'] = 'inband_failclosed'
                    _launch_arb['stop_reason'] = 'inband'
                    if _cts_a is not None:
                        _cts_a[_kla.KEY_INBAND_CLOSED] = \
                            _cts_a.get(_kla.KEY_INBAND_CLOSED, 0) + 1
            # 决策循环:刷新后同轮再决策(真 op 两阶段语义;每个
            # RefreshShop 动作后**独立重决策一段**——r270 连刷在
            # 决策层一口气输出多个 RefreshShop,但实机 op 是逐动作
            # 执行+买后重估(r251):刷→见新店→(再刷或买)。
            # r273 修:sim 逐动作消费,遇 RefreshShop 执行后立即
            # re-decide(捕捉"刷到就买"),段数上限防死循环。
            # r361b(ADR-0219 代理语义纪律,第三次命中):r358 检查点核心维
            # 读 state.deployed——sim 不建模 deployed 恒空 → 核心恒 0/2 →
            # 档位折扣恒触发(r5+ 恒走围栏,sim 行为与实机分叉)。
            # ADR-0287(批㉘ F1-F5,deploy_after_buy_semantics):部署块
            # 从轮首移到**买/升级之后**(生产序对齐:cw_loop 备战分支
            # 单轮 ⓪收球→①买牌→②部署→③装备→④出战)。旧轮首序让当轮
            # 买的件/当轮升级腾出的 cap 滞后一轮上板(n=300 观测 33.0%
            # 轮存在「当轮可上未上」,1124 件次),结算键(rung/depth)读
            # 滞后一档的 deployed(boss 轮 53.6% 结算键滞后)。部署块
            # 本体在轮末升级后执行(见下方「②部署」),目标集也在彼处
            # 从 session 现读(生产语义:买后 finalize 暂存帧已由决策入口
            # 刷新方向视图,ADR-0583)。
            # 两小批②短路(ADR-0557)+ 发射帧仲裁段(ADR-0566):发射帧的
            # 自由决策段恒零执行(备战动作链被发射短路的语义不变);
            # 溢出段帧以仲裁段帽运行本循环(段内逐动作过预算闸)=「先受限
            # 消费再发射」;带内段帧 range=0(fail-closed 不花)。
            # RunDeploy 对应的部署块照常执行,与生产
            # launch_prepared_battle 内 RunDeploy+StartBattle 同构。
            for _seg in range(_arb_seg_cap if _round_launch is not None
                              else 8):
                # W971 sim 适配批:决策调用切黑板新接口(生产/离线同路)。
                # sim 决策段 = 商店决策核:帧写者 = 本处(shop_state_frame
                # 写者白名单含 sim 引擎,见 cw_strategy_session 字段注释);
                # sim 合成态全字段可读(无 OCR 缺读面),帧语义与生产波顶
                # 融合段同构。decide_shop_screen 出口的升级意图为
                # LevelUpShop(is-a LevelUp,simulate/执行器零改动,账本
                # __type__ 仍落 'LevelUp')。帧缺失由接口抛错暴露
                # (黑板契约),禁静默按空态决策。
                # 帧代次 = full(ADR-0583 §3.3-sim):每段入口帧触发方向重估——
                # 首段键新驱动机器、后续段键同只刷视图(每段视图刷新保持,
                # 与旧「每段战略层直调重估」效果一致;段内投影帧槽值保持
                # 'none' 不再刷新,= 段内视图不漂)。
                sess.shop_state_frame = st
                sess.shop_frame_class = 'full'
                # BoardState 记录模型合成口(迁移批次一;设计 §2.1/§3.2.5,
                # 字段级规格正本 =
                # docs/develop/currency_war/game_state/fields.md):sim 真值帧同步记观察
                # (evidence 恒 sim:synthesized),bench 槽位保序 = 记录模型
                # 按实机真值箱占席(sim「无箱实体」只是内部口径约定不进
                # 记录)。纯记录零决策面:sim 账本/行为逐位不变。best-effort
                # 不炸引擎(记录层故障不毒化 sim)。
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    bench_is_full as _bs_bench_is_full,
                )
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    board_state_of as _bs_of,
                )
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    synthesize_from_game_state as _bs_synth,
                )
                try:
                    _bs_synth(_bs_of(sess), st, at_round=f'p{_seg_plane}-r{rn}')
                except Exception as _bs_e:   # noqa: BLE001
                    from one_dragon.utils.log_utils import log as _log
                    _log.debug('[cw-sim] BoardState 合成口跳过: %s', _bs_e)
                # ADR-0488 席满观测键·派生支(迁移批次二;设计 §8.7 as-built
                # 「席满观测键 ADR-0488 经合成口后 bench_is_full 供给」):
                # 满栏旗标改经 BoardState 派生(席空数==0,§3.2.5 派生单一
                # 源),不再直接数 st.bench。**语义等值申报**:sim 无箱实体,
                # 占席谓词(unit/empty)与 bench_occupied 非 None 计数逐位
                # 等值——零行为漂移。轮内 OR 聚合语义不变(生产 merge 同式:
                # 「任一决策帧满栏」;本判定在合成口后 = 本段帧语境,与旧
                # 「段入口值」同点);合成失败窗(None→False)保守端,下段
                # 合成自愈。
                _round_bench_full = _round_bench_full or bool(
                    _bs_bench_is_full(_bs_of(sess)))
                acts = strat.decide_shop_screen(sess, config)
                # 采购面三观察·帧级只读投影(见轮首「采购面三观察计数」
                # 块;位次 = 本段入口刷新后 = 意向状态已刷新,与策略决策帧
                # 同语境;纯读,零行为面)。义务面口径与策略侧
                # buy_members 同式:锁定帧 = locked_buy_membership,未锁
                # 帧 = line_members(target_comp)(单一源直调,禁第二实现;
                # T-307/R1 零参调 = 宽集,观测面监控宽集超容,与 P60 门
                # 同对象——截断集上检查恒假 = 死观测面,ADR-0647)。
                # 位次申报(ADR-0583):旧序 = 战略层直调先于本块;
                # 内化后刷新发生在驱动器首帧消费,本块后移到决策调用之后
                # 以保持「读数 = 本段入口态刷新后视图」语境逐位不变。
                _obs_ist = getattr(strategy_state_of(sess), 'v3_intention', None)
                _obs_bm = None
                if _obs_ist is not None:
                    from sr_od.application.currency_war.kernel import (
                        cw_intention as _obs_intention,
                    )
                    _obs_bm = _obs_intention.locked_buy_membership(_obs_ist)
                if _obs_bm is None:
                    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
                        predicates as _obs_predicates,
                    )
                    _obs_bm = _obs_predicates.line_members(
                        getattr(strategy_state_of(sess), 'target_comp', None))
                if _obs_bm:
                    if _obs_ist is not None and getattr(
                            _obs_ist, 'locked_comp', ''):
                        # |B| 与超容判据只辖锁定采购集(策略侧 P60 告警门
                        # 同式;未锁帧的 line_members 是 comp core∪shared
                        # 小集,天然 ≤ 容量,不入 |B| 峰值)
                        _obs_locked_b = max(_obs_locked_b, len(_obs_bm))
                        if len(_obs_bm) > BENCH_CAPACITY + DEPLOYED_CAPACITY:
                            _obs_overcap_frames += 1
                    _obs_owned = {(c.char_id or '')
                                  for c in list(st.bench or [])
                                  + list(st.deployed or [])
                                  if getattr(c, 'char_id', '')}
                    _obs_missing = [m for m in _obs_bm if m not in _obs_owned]
                    if _obs_missing:
                        _obs_cands = [c for c in (st.shop or [])
                                      if (c.name or '') in _obs_missing]
                        if _obs_cands:
                            from sr_od.application.currency_war.kernel.cw_registry import (
                                DEFAULT_REGISTRY as _obs_reg,
                            )
                            _obs_buy0 = min(
                                (c.cost if c.cost else 3)
                                for c in _obs_cands)
                            _obs_thr = (_obs_reg.interest_floor()
                                        + (st.shop_refresh_cost or 2)
                                        + _obs_buy0)
                            if (st.gold or 0) >= _obs_thr:
                                _obs_refresh_avail += 1
                # 必花域观测三键(20 号稿 §6;判定单一源,见轮首块注释)。
                from sr_od.application.currency_war.kernel.cw_economy import (
                    in_must_spend_zone as _msz_pred,
                )
                if _msz_pred(st.gold, sess):
                    _ms_zone += 1
                    # 层命中按动作类 isinstance 判定:
                    # decide_shop_screen 出口的升级意图为 LevelUpShop
                    # 子类实例,无 __type__ 属性,type().__name__ 落子类
                    # 名 'LevelUpShop',字符串匹配集只含基类名 'LevelUp'
                    # ⇒ 旧写法 L3 恒缺且该帧误入零消费。过滤器含基类
                    # LevelUp(备战栈 mandate.py:454 有基类发射先例,
                    # 防同型复发敞口;is-a 覆盖 Shop 子类)。
                    _ms_acts = [
                        a for a in (acts or [])
                        if isinstance(a, (BuyCard, LevelUp, LevelUpShop,
                                          RefreshShop))
                    ]
                    if not _ms_acts:
                        _ms_zero += 1
                    for _ms_a in _ms_acts:
                        if (isinstance(_ms_a, BuyCard)
                                and getattr(_ms_a, 'reason', '')
                                    == 'fuel_filler_stall'):
                            _ms_layer['L2'] = _ms_layer.get('L2', 0) + 1
                        elif isinstance(_ms_a, (LevelUp, LevelUpShop)):
                            _ms_layer['L3'] = _ms_layer.get('L3', 0) + 1
                        else:
                            _ms_layer['L1'] = _ms_layer.get('L1', 0) + 1
                # 拒因遥测透传(纯观测,零行为面:sim 决策走 decision_v2
                # 栈,不调 cw4 决策核,故由引擎在每决策段直调生产端函数
                # ——同一输入同一映射,双栈无第二实现)。口径=段帧首静态
                # 快照(与生产 decide_shop_action 单动作循环的段入口态同
                # 语义):state=段入口态,
                # actions=本段原始决策(sim 不走生产截断器,差异如实声明
                # ——被截断器丢弃的买在 sim 无对应面)。逐波留档进
                # sim.shop_waves 对应波(键 rejects,与该波 cards/gold 同
                # 位对齐),顶层 shop_rejects=末波 last-wins(生产 decisions
                # 行 session 单槽同语义)。K 空窗时 target_comp=None,
                # comp 派生分类不可得,membership/hub 面与生产 comp=None
                # 分支同源(hub 直传面见下方打标块注)。
                from sr_od.application.currency_war.strategies.impl.mandate_v1.shop import (
                    shop_unbought_reasons,
                )
                _k_comp = getattr(strategy_state_of(sess), 'target_comp', None)
                # 买侧 membership 正典口径 = _obs_bm(上方 obs 段构造:
                # 锁定帧 locked_buy_membership / 未锁帧 line_members,
                # 与生产 shop.py buy_members 同式)——打标与 obs 同帧消费
                # 同一实例,两观测位物理同源禁分叉;旧口径本块第二实现
                # line_members 直传曾把锁定帧阵营成员误标 non_line
                #(g_20260905_035710 同型事故修法在 sim 打标点的对齐)。
                # hub_names 直传(生产 _arms 同条件:K 空窗 ∧ p2plus 带,
                # 分带走 k_empty_window_fallback 单一源,禁 plane 直判)
                # ——空窗帧枢纽件落 hub_option,不再混入 non_line。
                _seg_hub: frozenset[str] = frozenset()
                if _k_comp is None and _obs_ist is not None:
                    from sr_od.application.currency_war.kernel import (
                        cw_intention as _rej_intention,
                    )
                    _rej_fb, _rej_tok = (
                        _rej_intention.k_empty_window_fallback(
                            st, _obs_ist, session=sess,
                            registry=_obs_registry))
                    if _rej_tok == 'p2plus':
                        _rej_arms = _rej_intention.no_target_arms(
                            st, _obs_ist, session=sess,
                            registry=_obs_registry)
                        _seg_hub = frozenset(_rej_arms.hub_names)
                _seg_rejects = shop_unbought_reasons(
                    st, _k_comp, _obs_bm, acts, hub_names=_seg_hub)
                _round_shop_rejects = _seg_rejects
                if _waves:
                    _waves[-1]['rejects'] = dict(_seg_rejects)
                _round_formed_stop = _round_formed_stop or bool(
                    getattr(strategy_state_of(sess), 'v3_formed_stop', False))
                # ADR-0474 分配器帧位轮内采集(每段 decide_prep 覆写
                # strategy_state_of(session).v3_alloc_frame,这里逐段留末值 + OR 聚合)
                _af = getattr(strategy_state_of(sess), 'v3_alloc_frame', None)
                if _af is not None:
                    _round_alloc_frame = _af
                    _round_alloc_active_any = (_round_alloc_active_any
                                               or bool(_af.get('active')))
                if not _phase_snap:
                    _phase_snap = True   # 轮入口首段快照(迁移审计 w114(git 历史) 影子)
                    # 镜像族缺写守卫(度量修复):覆写 decide_shop_screen 的
                    # 策略核(如 mandate_v1)不经旧核商店决策核,镜像族
                    # (phase/B_t/dp_posture/储备披露)原无写者 → 下方
                    # 快照恒读初值。sim71 批后 v3_form_ok 亦由
                    # write_shop_mirrors 现读写端承载(死镜像处置);轮
                    # 键戳 v3_mirror_key(写者=write_shop_mirrors 单一源)
                    # 标「本轮已写」:旧核每决策段自写、键戳恒盖 →
                    # 守卫不触发(旧核路径零漂移);缺写且策略带该钩子时
                    # 在此补写(新核路径,判据同源无第二实现)。
                    if getattr(strategy_state_of(sess), 'v3_mirror_key', None) \
                            != (st.plane, st.round_num):
                        _wsm = getattr(strat, 'write_shop_mirrors', None)
                        if callable(_wsm):
                            _wsm(st, sess)
                    _round_phase = str(getattr(strategy_state_of(sess), 'v3_phase', '') or '')
                    _round_form_ok = bool(getattr(strategy_state_of(sess), 'v3_form_ok', False))
                    # B_t 板面目标线承重计数(form_score 替代披露口径;
                    # 写者单一源 = write_shop_mirrors,历史 form_score 只读退役)
                    _round_b_t = int(getattr(strategy_state_of(sess), 'v3_b_t', 0) or 0)
                    # 迁移审计 w119(git 历史)/ADR-0347 授权依据 trace:当轮 DP 姿态 tag
                    _round_dp_posture = str(getattr(getattr(
                        getattr(strategy_state_of(sess), 'v3_dp_posture', None),
                        'posture', None), 'tag', '') or '')
                    # `w611_econ_cycle/` 储备/义务披露(轮入口快照;与生产 decisions 行
                    # sess_* 同语义,义务帧兑现率/闲置金判读的 sim 侧源)
                    _round_reserve_cap = int(
                        getattr(strategy_state_of(sess), 'v3_reserve_cap', 0) or 0)
                    _round_reserve_overflow = int(
                        getattr(strategy_state_of(sess), 'v3_reserve_overflow', 0) or 0)
                    _round_release_budget = int(
                        getattr(strategy_state_of(sess), 'v3_release_budget', 0) or 0)
                    _round_release_reason = str(
                        getattr(strategy_state_of(sess), 'v3_release_reason', '') or '')
                    # ADR-0348 ↺:扑满节点识别标记(遥测数据面)
                    _round_piggy = bool(getattr(strategy_state_of(sess), 'v3_piggy_reward',
                                                False))
                    # `w227_handoff_gate/`/ADR-0400:承接门缺口(filters.formed_stop_
                    # active 写;轮入口快照,判读「门扣住哪些轮」)
                    _round_handoff_gap = int(
                        getattr(strategy_state_of(sess), 'v3_handoff_gap', 0) or 0)
                    # 迁移审计 w238(git 历史)/ADR-0403:boss 投影 hp 同点快照(投影开时非 None)
                    _round_handoff_hp_proj = getattr(
                        strategy_state_of(sess), 'v3_handoff_hp_proj', None)
                    # 终止豁免位——写入侧单一源 =
                    # checks.segments.terminal_release_bit(检查器
                    # seg_p1_blood_budget_refresh 消费行键禁复算)。
                    # 账本行键 terminal_release = 轮入口首段快照(决策
                    # 帧现值,与检查器「决策发生在本轮回战斗前」的 hp
                    # 口径同源;旧 session 闩载体已删——其恒释放语义与
                    # 本谓词的无状态 hp 带口径冲突)。
                    from sr_od.application.currency_war.sim.checks.segments import (
                        terminal_release_bit as _tr_bit,
                    )
                    _round_terminal_release = bool(_tr_bit(sess, st))
                # 预算-回执契约·对账门声明(**逐段覆写=末段口径**,
                # 与回执 last-wins/生产 per-frame 直读同语义;w943_audit5
                # P3-4:首段口径会漏记「前段已兑现、刷新后重决策段未兑现」
                # 的轮。判前预注册 A/B 主判据的数据源)
                _unf = getattr(strategy_state_of(sess), 'v3_posture_unfulfilled', None)
                _round_posture_unfulfilled = dict(_unf) if _unf else None
                if not use_refresh:
                    acts = [a for a in acts
                            if not isinstance(a, RefreshShop)]
                if not acts:
                    break
                _segs_used += 1
                progressed = False
                for a in acts:
                    if _launch_budget_on:
                        # 仲裁单动作预算闸(ADR-0566;判定单一源 = kernel
                        # launch_arbitration_gate,生产同源):花后金位 ≥ g*
                        # 才放行;拒 = 本动作不执行 + 整个仲裁段收工(消费
                        # 终止非跳过续试:跳过高位动作改试低位 = 重排既有
                        # 评估序,违金出口族红线 5)。零成本动作(卖出/部署
                        # 族)恒放行,闸辖「花」不辖「换手」。
                        from sr_od.application.currency_war.kernel import (
                            cw_launch_arbitrage as _kla_g,
                        )
                        _g_ok, _g_why = _kla_g.launch_arbitration_gate(
                            a, int(getattr(st, 'gold', 0) or 0), sess)
                        if not _g_ok:
                            _launch_arb['stop_reason'] = _g_why
                            _launch_arb['gate_blocks'] += 1
                            _cts_g = getattr(strategy_state_of(sess),
                                             'cw4_counters', None)
                            if _cts_g is not None:
                                _cts_g[_kla_g.KEY_GATE_BLOCKS] = \
                                    _cts_g.get(_kla_g.KEY_GATE_BLOCKS, 0) + 1
                            _arb_stop = True
                            break
                        if _kla_g.launch_spend_cost(a) > 0:
                            _launch_arb['actions'] += 1   # 过闸花费动作计数(执行侧拒买不扣,如实申报为尝试口径)
                    if isinstance(a, RefreshShop):
                        res.refreshes += 1
                        # 触发源分键(见轮首「刷新触发源分键」块;
                        # reason = 策略层记录字段,''=旧调用归 other 桶)
                        _r_src = getattr(a, 'reason', '') or 'other'
                        _obs_refresh_src[_r_src] = \
                            _obs_refresh_src.get(_r_src, 0) + 1
                        if st.plane >= 2:
                            res.p2_refreshes += 1   # ADR-0362:P2 段 D 次数
                        _cost_r = (st.shop_refresh_cost or 2)
                        # `w162_inject/`/ADR-0364:策略免费刷额度(如 加油站 每节点
                        # 1 次;cw_economy._refresh_cost 同语义)——额度内
                        # 刷价 0。无持卡/无额度时与旧逐位相同。
                        if _free_r and _free_used < _free_r:
                            _cost_r = 0
                            _free_used += 1
                        st.gold -= _cost_r
                        _spend['refresh'] += _cost_r
                        # xp_per_refresh 数值接入:付费刷新产经验(淘金客 +2,
                        # 官方原文「每次消耗金币刷新商店都会获得 2 经验值」;
                        # 免费刷额度内 cost=0 不计)。数值源单一面 =
                        # cw_investments.STRATEGY_EFFECTS overlay(_overlay_xp_per_refresh
                        # 逐持卡查 spec payload,overlay 值变更 sim 跟随;
                        # pending 条目 payload 即保守支)。
                        # 零漂移:无持卡时表达式恒 0,无 xp/行为变化。
                        _xpr = (_overlay_xp_per_refresh(st.active_strategies)
                                if st.active_strategies else 0)
                        if _cost_r > 0 and _xpr > 0:
                            xp += _xpr
                            _refresh_xp_total += _xpr
                            _refresh_xp_round += _xpr
                            st.xp_progress = (
                                xp, XP_TO_NEXT_LEVEL.get(st.level, 4))
                        _acts.append({'__type__': 'RefreshShop',
                                      'cost': _cost_r, 'reason': _r_src})
                        st.shop = cards_pool.draw_shop(st.level,
                                                       probs=st.refresh_probs)
                        _waves.append(
                            {'event': 'refresh', 'gold': st.gold,
                             'cards': [{'name': c.name, 'faction': c.faction,
                                        'cost': c.cost} for c in st.shop],
                             # 拒因串留档位(下一段决策覆写;段上限截断
                             # 时保持 None=无决策段)
                             'rejects': None})
                        progressed = True
                        break          # 刷后立即 re-decide(见新店)
                    if isinstance(a, BuyCard):
                        # 商店买入执行 = kernel/cw_state.simulate 单一源
                        # (live 投影同款;分歧消解对账 = ADR-0561 申报表):
                        # 状态变更(金/店槽下架/合成连锁/满栏合成买)全在
                        # simulate 内部,引擎只余预检披露 + 池/经济/账本转录。
                        # 满栏预检(ADR-0283/`w566_sim_guard/`):只为「满栏
                        # 非合成拒买」计数披露,判定函数与 simulate 内部
                        # 同源(merge_buy_completes),不构成第二套语义。
                        if bench_occupied(st.bench) >= BENCH_CAPACITY \
                                and not merge_buy_completes(
                                    a.card.name, a.card.star or 1, st.bench,
                                    st.deployed, st.shop):
                            _bench_full_skips += 1
                            _bench_full_skip_gold += a.card.cost
                            continue
                        # 幻影再买披露(ADR-0284):槽匹配判定随单一源统一为
                        # simulate 的 x 槽位口径;此处身份→同名兜底只辖
                        # 「已消费槽再买」的可执行性跳过(金/池/板不消费)
                        # 与店外构造(测试桩)的 legacy 执行披露;真策略
                        # 提案恒来自 st.shop,phantom_rebuys 锁真批次恒 0。
                        _slot = next((c for c in st.shop if c is a.card),
                                     None)
                        if _slot is None:
                            _slot = next(
                                (c for c in st.shop
                                 if c.name == a.card.name), None)
                        if _slot is None:
                            _phantom_rebuys += 1
                            _offered = {c.get('name') for w in _waves
                                        for c in w.get('cards') or []}
                            if a.card.name in _offered:
                                continue   # 已消费槽再买:不可执行
                        _was_full = (bench_occupied(st.bench)
                                     >= BENCH_CAPACITY)
                        _ch = a.reason or 'unknown'
                        # reason=**通道**(创建点语义);channel=**身份**
                        # (classify_buy——通道经济分析别混桶,审查#7)。
                        # 序列化形状对齐生产 serialize_action(card 嵌套;
                        # 视图读 a['card']['cost'],平铺会让 economy 算 0)。
                        from sr_od.application.currency_war.kernel.cw_line_defs import (
                            classify_buy as _cb,
                        )
                        _channel = _cb(a.card, st)
                        # T-153 生成侧自算披露(ADR-0593):成型度执行点
                        # 现读(单一源 = cw_deploy_logic.engines_count;
                        # 买前帧口径,零 rng/零状态写入纯观测)。消费 =
                        # C5 成型停手自报复核 / D2 停手失配检测在生成点
                        # 可见。同 ADR-0589 dec_* 键理由:行为投影 digest
                        # 只取动作 (__type__,reason,result),本键零位移。
                        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
                            engines_count as _ec,
                        )
                        _dec_engines = _ec(
                            _board_factions_of(st.deployed),
                            {d.char_id for d in (st.deployed or [])
                             if getattr(d, 'char_id', '')})
                        _pre_units = (bench_occupied(st.bench)
                                      + deployed_occupied(st.deployed))
                        _pre_gold = st.gold
                        st = _simulate_state(st, a)
                        _spent = _pre_gold - st.gold
                        if _spent <= 0:
                            # 防御:预检守卫与 simulate 判定同源,恒 applied;
                            # 零消费 = 单一源语义漂移信号,如实不转录。
                            continue
                        # 实购张数(满栏合成买 k>1;常规买恒 1)
                        _k = max(1, _spent // max(1, card_cost(a.card)))
                        _spend['buys'][_ch] = \
                            _spend['buys'].get(_ch, 0) + _spent
                        for _ in range(_k):
                            cards_pool.take(a.card.name)
                        _acts.append({'__type__': 'BuyCard',
                                      'card': {'x': a.card.x,
                                               'faction': a.card.faction,
                                               'name': a.card.name,
                                               'cost': a.card.cost},
                                      'reason': _ch,
                                      'channel': _channel,
                                      # T-153 披露键(纯观测;ADR-0593)
                                      'dec_engines_count': _dec_engines,
                                      **({'count': _k} if _was_full else {})})
                        # ADR-0129 购买经验单击模型:一次点击 +XP_PER_BUY
                        # (k 张自动多买仍是一次点击,不加倍)。XP 记账统一
                        # (ADR-0561 申报表 #4):XP 只在引擎侧本单一
                        # 记账点累加,simulate 分支无 XP 语义,数值逐位不变。
                        xp += XP_PER_BUY
                        st.xp_progress = (xp, XP_TO_NEXT_LEVEL.get(st.level, 4))
                        # 轮内新鲜度登记(发射位写入取舍,与
                        # cw4_fuel_filler_stall_buys 先例同位):多买入
                        # 意图逐名入集(k 张合成买 = k 个意图,防漏记)。
                        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
                            record_fresh_buy as _rfb,
                        )
                        for _ in range(_k if _was_full else 1):
                            _rfb(sess, st, a.card.name)
                        # 合并次数按单位消减推算(每次合并净减 2 个单位;
                        # 消费 3 产 1,链式多级同式)
                        _merges += (_pre_units + (_k if _was_full else 1)
                                    - bench_occupied(st.bench)
                                    - deployed_occupied(st.deployed)) // 2
                        progressed = True
                    elif isinstance(a, LevelUp):
                        # cap 守卫:level >= LEVEL_CAP 时 LevelUp 拒付
                        # (不扣金/不进 XP),账本记 LevelUpRejected 行
                        # (不占 LevelUp 类型行:升级支出锁判据 =
                        # spend.levelup == Σ(LevelUp 行 cost,缺读兜 4;
                        # ADR-0632 重推,原 flat4 字面「4 × 行数」判据已废止),
                        # 拒付行混入会虚增合计误报),计数进
                        # sim.level_cap_rejects 披露。
                        # 【sim-only 已知差异·申报保留,ADR-0561 申报表 #6】
                        # 实机 lv10 才禁用购买经验,lv9 是正常付费档,本守卫
                        # 在 lv9 拒付与实机方向相反;LEVEL_CAP=9 冻结有在案
                        # 前置(见本文件 LEVEL_CAP 注释:追级虚高治理+池指纹
                        # 重锚,归行为变更批)。不随本批切 simulate:切源会
                        # 连带引入「cap10 + 攒够即升即时升级」双重行为变更,
                        # 违本批「切源不改行为」零漂移门,#6 只登记不顺手改。
                        if st.level >= LEVEL_CAP:
                            _lv_cap_rejects += 1
                            _acts.append({'__type__': 'LevelUpRejected',
                                          'reason': 'level_cap',
                                          'level': st.level})
                            continue
                        # 花费载体统一(ADR-0561 申报表 #5,载体面):从
                        # action.cost 读(策略层 xp_click_cost 真值优先,
                        # fallback 常量;sim 恒 4 = 兜底值,真值接入归
                        # sim-wiring P2 件——本行只消灭执行侧硬编码载体)。
                        _lv_cost = int(getattr(a, 'cost', 0) or 4)
                        st.gold -= _lv_cost
                        _spend['levelup'] += _lv_cost
                        # auth=授权依据观测(ADR-0354):LevelUp.auth_basis
                        # 放行臂名(pop_slot/dp/static_ev/m3_batch;
                        # ''=default 栈旧调用或未过账)——检查器
                        # levelup_interest_engine_gate 判据消费;记录非指令。
                        _lv_auth = getattr(a, 'auth_basis', '')
                        # 支A 谓词输入的执行点披露(观测非指令;零 rng 消耗/
                        # 零状态写入):单动作架构(ADR-0517)下动作执行点
                        # 状态 = 发射帧状态,levelup_budget_gate 检查器的支A
                        # 镜像据此按击判 realize——行末快照在「帧内合成
                        # 2★→升级批→轮末部署块当帧上板」确定性序列下 bench
                        # 已无 2★,行末口径恒误报绕闸(假阳定谳 =
                        # ADR-0589;谓词单一源 = ADR-0576 §2.5 支A,
                        # criteria/levelup._realize_chain_ready 同判)。cap
                        # 缺读对齐生产谓词 fail-closed(False,非恒真)。
                        # 行为投影 digest 只取动作 (__type__,reason,result)
                        # (test_cw_w614_sim_fidelity 锚),本键零位移。
                        _lv_mu = st.max_units()
                        # T-153 生成侧自算披露(ADR-0593):升级授权存在性
                        # 腿执行点现读——板满腿 = 下方 dec_board_full
                        # (ADR-0589 同披露载体);待上场腿 = bench 持有
                        # 当前线名册成员(名册 = _line_member_names,消费
                        # = C2 授权自报复核 / D3 前置失配检测)。纯观测。
                        _dec_wait = any(
                            getattr(b, 'char_id', '') in _line_member_names(
                                sess)
                            for b in iter_occupied(st.bench))
                        _acts.append({'__type__': 'LevelUp',
                                      'cost': _lv_cost, 'auth': _lv_auth,
                                      'dec_board_full': (
                                          _lv_mu is not None
                                          and deployed_occupied(st.deployed)
                                          >= _lv_mu),
                                      'dec_bench_2star': any(
                                          (getattr(b, 'star', 1) or 1) >= 2
                                          for b in iter_occupied(st.bench)),
                                      # T-153 披露键(纯观测;ADR-0593)
                                      'dec_bench_wait_member': _dec_wait})
                        xp += XP_PER_BUY   # 与买牌同源(ADR-0286 xp 真值化;值=4)
                        st.xp_progress = (xp, XP_TO_NEXT_LEVEL.get(st.level, 4))
                        progressed = True
                    elif isinstance(a, SellBench):
                        # 卖出执行 = kernel/cw_state.simulate 单一源
                        # (ADR-0561 申报表 #7/#8):装备回收随单一源生效
                        # ——【已申报行为修正,申报表 #7】sim 卖带装件装备回 owned
                        # 池(C6 装备守恒,修复前凭空消失);expect 代际校验
                        # 同源归位(#8,stale_proposal 拒绝;sim 单线程同帧
                        # 语义下实际不可达,纯防线)。引擎保留池回填/同轮
                        # 保留集销账/账本转录。
                        _tgt = (st.bench[a.bench_idx]
                                if 0 <= a.bench_idx < len(st.bench) else None)
                        _stale = (_tgt is not None and a.expect
                                  and _tgt.char_id != a.expect)
                        if _tgt is not None and not _stale:
                            # ADR-0276:卖出回金接生产 sell_refund 单一源
                            # (费用口径随单一源 = bench_char_cost:识别名查
                            # 注册表,未知名 3 中费保守估——与旧 ch.cost
                            # 兜底 1 在已识别名域恒等;merge 后 bench 可有
                            # star≥2,按星退防合成件价值低估)。
                            _sell_v = sell_refund(_tgt.star,
                                                  _bench_char_cost(_tgt))
                            # T-153 生成侧自算披露(ADR-0593):孤儿性机械
                            # 腿执行点现读 = 被卖件是否当前线名册成员
                            # (线账闭合语境判据;义务登记簿引擎层不可见,
                            # 本键只携线成员机械腿,复核面 = C4 转化分键
                            # 复核 / D1 身份对照的输入,ADR-0591 §4 写端
                            # 证明义务的检查端补位)。纯观测。⚠ 未锁线
                            # 期名册不可解析 → 键恒 False(语境缺失非
                            # 「非线成员」证据);复核面按 unverifiable
                            # 处置(seed18 p1r1 口径,禁据键定罪)。
                            _dec_in_line = _tgt.char_id in (
                                _line_member_names(sess))
                            st = _simulate_state(st, a)
                            _spend['sell_income'] += _sell_v
                            _acts.append({'__type__': 'SellBench',
                                          'bench_idx': a.bench_idx,
                                          'name': _tgt.char_id,
                                          'income': _sell_v,
                                          # 卖出通道分键转录(记录非指令;
                                          # 同轮买卖检查豁免面据此收敛)
                                          'sell_reason': getattr(
                                              a, 'reason', '') or '',
                                          # 转化类豁免分键转录(C4/ADR-0611:
                                          # 结构化证明键
                                          # convert_reason 进账本行,检查器
                                          # 转化类豁免分支据此判定;孤儿键
                                          # 仍在 sell_reason,按键分工零双源)
                                          'convert_reason': getattr(
                                              a, 'convert_reason', '') or '',
                                          # T-153 披露键(纯观测;ADR-0593)
                                          'dec_sell_in_line': _dec_in_line})
                            # T3 同轮保留集「卖出即销」(生命周期出口②,
                            # sim 侧与生产 sell 通道同语义闭环)
                            from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
                                stall_buys_consume as _sbc,
                            )
                            _sbc(sess, _tgt.char_id)
                            cards_pool.ret(_tgt.char_id)
                            progressed = True
                    elif isinstance(a, (SellDeployed, SwapDeploy,
                                        CompTransaction)):
                        # 动作 v2(契约包 C1,步2):显式部署通道执行——
                        # 转移语义在 cw_state.simulate 单一源(全量校验+原子
                        # 应用),此处转录账本 + 池守恒/经济记账同步。
                        # 迁移审计 w65(git 历史) 修法3(ADR-0323):``_explicit_deploy_seen`` 移到
                        # 下方 applied 分支置位——**只有真执行(未被拒)的显式
                        # 动作才占显式通道**;被拒事务不消耗围栏(围栏跳过语义
                        # 修正,同轮围栏照跑,板面欠载不再被事务风暴封死;迁移审计 w64(git 历史)
                        # Ring5:被拒事务也 skip_fence,90 次/11 局)。
                        # 预状态引用快照(池 ret / 经济记账用;simulate 会
                        # deepcopy,引用不跨界)
                        _sold_names: list[str] = []
                        _shop_fill_cards: list[ShopCard] = []
                        if isinstance(a, SellDeployed) \
                                and 0 <= a.deployed_idx < len(st.deployed) \
                                and st.deployed[a.deployed_idx] is not None:   # ADR-0392 空槽
                            _sold = st.deployed[a.deployed_idx]
                            _sold_names = [_sold.char_id]
                        elif isinstance(a, CompTransaction):
                            _sold_names = [
                                st.bench[i].char_id
                                for i, d in a.sell if d == 'bench'
                                and 0 <= i < len(st.bench)
                                and st.bench[i] is not None] + [
                                st.deployed[i].char_id
                                for i, d in a.sell if d == 'deployed'
                                and 0 <= i < len(st.deployed)
                                and st.deployed[i] is not None]   # ADR-0392
                            _shop_fill_cards = [
                                st.shop[f.idx] for f in (a.fill or [])
                                if f.source == 'shop'
                                and 0 <= f.idx < len(st.shop)]
                        _new = _simulate_state(st, a)
                        _log = _new.action_log[-1] if _new.action_log else {}
                        _applied = _log.get('result') == 'applied'
                        _tx_income = int(_log.get('income', 0) or 0)
                        _tx_fill_cost = int(_log.get('fill_cost', 0) or 0)
                        # 迁移审计 w101(git 历史):applied 事务的 bench 净腾位数(执行点真值;账本
                        # 序列化不展开 deploy/sell/fill 明细,检查器重放缺此
                        # 项会把合法买误报超容——seeds 18/22 实证)。正数=腾位。
                        _tx_bench_delta = (
                            bench_occupied(st.bench) - bench_occupied(_new.bench)
                            if isinstance(a, CompTransaction) else 0)
                        if _applied and isinstance(a, SellDeployed) \
                                and 0 <= a.deployed_idx < len(st.deployed) \
                                and st.deployed[a.deployed_idx] is not None:   # ADR-0392
                            # SellDeployed 的 income 未进 action_log(单动作
                            # 无事务汇总)——预状态现算(与 simulate 同口径)
                            _tx_income = sell_refund(
                                _sold.star, _bench_char_cost(_sold))
                        if _applied:
                            # 迁移审计 w65(git 历史) 修法3(ADR-0323):显式动作**真执行**才置位
                            # (被拒不跳围栏,见上方分支注释)
                            _explicit_deploy_seen = True
                            st = _new   # 整体替换(事务原子;simulate 单一源)
                            for _n in _sold_names:
                                if _n:
                                    cards_pool.ret(_n)
                            for _c in _shop_fill_cards:
                                cards_pool.take(_c.name)
                                xp += XP_PER_BUY   # 买牌同源给 XP(ADR-0129)
                            _spend['sell_income'] += _tx_income
                            if _tx_fill_cost:
                                _ch = a.reason or 'tx_fill'
                                _spend['buys'][_ch] = \
                                    _spend['buys'].get(_ch, 0) + _tx_fill_cost
                            progressed = True
                        else:
                            res.explicit_action_rejects += 1
                        _entry = {'__type__': type(a).__name__,
                                  'reason': getattr(a, 'reason', ''),
                                  'result':
                                      'applied' if _applied else 'rejected'}
                        if _applied and _tx_bench_delta:
                            _entry['bench_delta'] = _tx_bench_delta
                        if not _applied:
                            _entry['reject_reason'] = _log.get('reason', '')
                        if _tx_income:
                            _entry['income'] = _tx_income
                        if _tx_fill_cost:
                            _entry['fill_cost'] = _tx_fill_cost
                        _acts.append(_entry)
                        if _applied and _shop_fill_cards:
                            # 迁移审计 w43(git 历史) leader 裁决 2(phantom_rebuys 根治):事务
                            # fill 已消费店槽——同批后续 BuyCard 是对陈旧
                            # state.shop 的提案,作废并立即重决策(同
                            # RefreshShop 的 break-redecide 语义),不套用
                            # 陈旧引用。
                            break
                if _arb_stop:
                    break   # 仲裁段预算闸拒:消费终止,带内预算已用尽(ADR-0566)
                if not progressed:
                    break
            while (st.level < LEVEL_CAP
                   and xp >= XP_TO_NEXT_LEVEL.get(st.level, 999)):
                xp -= XP_TO_NEXT_LEVEL[st.level]
                st.level += 1
            # ADR-0286:轮末升级后 xp_progress 同步清零结转(生产 XP 条语义)
            st.xp_progress = (xp, XP_TO_NEXT_LEVEL.get(st.level, xp or 4))
            # 仲裁段披露终化(ADR-0566):gold_after/segments/spent 落
            # launch.arbitrage 位(发射帧行内;零漂移锚辖非发射帧,本键只
            # 在发射帧存在)。后验跌破检测 = 合并多买等投影外成本显影
            #(正常恒 0);溢出帧零消费单列分键,与带内 fail-closed 可辨。
            if _launch_arb is not None and _round_launch is not None:
                _ga_arb = int(getattr(st, 'gold', 0) or 0)
                _launch_arb['gold_after'] = _ga_arb
                _launch_arb['segments'] = _segs_used
                _launch_arb['spent'] = _launch_arb['gold_before'] - _ga_arb
                _cts_x = getattr(strategy_state_of(sess), 'cw4_counters', None)
                if (_launch_arb['zone'] == 'overflow'
                        and _launch_arb['spent'] > 0
                        and _ga_arb < _launch_arb['g_star']
                        and _cts_x is not None):
                    from sr_od.application.currency_war.kernel import (
                        cw_launch_arbitrage as _kla_x,
                    )
                    _cts_x[_kla_x.KEY_CROSS_LINE] = \
                        _cts_x.get(_kla_x.KEY_CROSS_LINE, 0) + 1
                if (_launch_arb['zone'] == 'overflow'
                        and _launch_arb['spent'] == 0
                        and _cts_x is not None):
                    from sr_od.application.currency_war.kernel import (
                        cw_launch_arbitrage as _kla_z,
                    )
                    _cts_x[_kla_z.KEY_ZERO_CONSUME] = \
                        _cts_x.get(_kla_z.KEY_ZERO_CONSUME, 0) + 1
                _round_launch['arbitrage'] = _launch_arb
            # M1″ 计划+意图面(行内观测键;决策语境 = 买/升级后、部署代理
            # 前,与生产 M1″ 决策帧同语境;判定单一源直调,见函数注)。
            # 零 rng 消耗;计划非空帧由下方执行转录产生状态写入(其余帧
            # 纯读)——不挤占行为投影 digest 判别域的声明自此收窄为
            # 「计划空帧纯读」(T-169 执行面接入后的如实申报)。
            # 两小批②短路帧:生产无 M1″ 决策帧(备战动作链被发射短路)
            # ⇒ 恒 None(非观测异常,如实无帧)。T-307/R3-a(ADR-0647)
            # 起短路形态由独立行内键 ``m1p_obs_skipped`` 显影(None 双义
            # 拆解:观测异常 vs 发射短路无帧),见行组装邻位透传。
            _m1p_obs: dict | None = None
            # R3-a 发射帧盲窗显影键:发射帧置 'launch_short_circuit',
            # 非发射帧恒 None。独立行内键形态(否决哨兵 dict 注入 m1p:
            # 防 isinstance(dict)/.get('nonempty') 判读路径误读——C-A2
            # _c2_plan_point、dig 工具、锁测试双向断言均消费 m1p dict
            # 形状)。
            _m1p_obs_skipped: str | None = None
            # T-279 R1:计划对象/装配 ctx/卖出旗带出本块,轮末部署块
            # R1-a 直投消费(变量先置缺省——达标臂发射帧整块跳过时,
            # 部署块分支仍需可读)。
            _m1p_plan: SwapPlan | None = None
            _m1p_ctx: SwapPlanContext | None = None
            _m1p_sold = False
            if _round_launch is None:
                try:
                    _m1p_plan, _m1p_obs, _m1p_ctx = \
                        _m1p_plan_and_record(st, sess)
                except Exception:   # noqa: BLE001  观测 best-effort(launch 同款)
                    _m1p_plan, _m1p_obs, _m1p_ctx = None, None, None
                # M1″ 执行面 sim 转录(T-169;总图设计 R2 §2 sim 边界行,
                # 修订 ADR-0530「sim 不建模执行侧」申报):计划非空 = 生产
                # 发射 RunDeploy(m1_swap_redeploy) 帧 → sim 逐件卖 victim
                # (卖出臂单一源执行,见 m1p_swap_execute),腾出的 vacancy
                # 由轮末部署块补上——显式动作旗置位走 skip_fence+残余补
                # 部署路径(裁决1「显式>围栏」同语义;T-279 R1/ADR-0640
                # 起 m1p 卖出成功帧的补上 = 计划单一源消费
                # _m1p_plan_fill_deploy:R1-a 计划 up 直投/防御退 R1-b
                # 卖出后现读重 derive,与生产 CwOpDeploy 卖出臂+部署 op
                # 消费计划单一源两段同构)。计划空/卖出被拒帧零状态写入
                #(原「零行为面」语义在这些帧保持)。
                if _m1p_plan is not None and _m1p_plan.nonempty:
                    st, _m1p_sold = m1p_swap_execute(
                        st, _m1p_plan, acts=_acts, spend=_spend,
                        pool=cards_pool)
                    if _m1p_sold:
                        _m1p_obs['executed'] = True
                        _explicit_deploy_seen = True
            else:
                # R3-a(T-307/ADR-0647)发射帧盲窗置键:发射帧备战动作
                # 链被发射短路,生产无 M1″ 决策帧——m1p=None 的成因在此
                # 显影,判读面不再与观测异常帧混桶。
                _m1p_obs_skipped = 'launch_short_circuit'
            # ②部署(ADR-0287,批㉘ F1-F5):买/升级**之后**执行(生产序
            # 对齐)。r390 起 deployed 代理 = deploy_bench 真实围栏逻辑
            # (cw_deploy_logic.select_deployments 纯函数,与 CwOpDeploy op
            # 同一源)——r373/r387 类执行层 bug sim 可发现。target 集从
            # session **买后**现读(生产:买牌段 finalize 暂存帧已由决策
            # 入口刷新方向视图,锁线轮目标已更新,ADR-0583);未识别
            # (char_id 空)照旧上,与 op 一致。
            from sr_od.application.currency_war.kernel import cw_deploy_logic as _dl
            _tf, _tc, _fw = frozenset(), frozenset(), frozenset()
            # `w155_evolve_lock/`/ADR-0360 件3:锁定帧体系键并入围栏放行集(同生产 op 侧)
            _lf = frozenset()
            _rf = False
            try:
                _tc = frozenset(getattr(strategy_state_of(sess), 'target_comp', None).core_chars
                                or ()) if getattr(strategy_state_of(sess), 'target_comp', None) else frozenset()
                _tf = frozenset(getattr(strategy_state_of(sess), 'target_comp', None).factions
                                or ()) if getattr(strategy_state_of(sess), 'target_comp', None) else frozenset()
                _fw_name = getattr(strategy_state_of(sess), 'transition_framework', '') or ''
                _fw = frozenset()
                if _fw_name:
                    from sr_od.application.currency_war.kernel.cw_transition import (
                        TRANSITION_PACK,
                    )
                    _fw = frozenset(
                        n for n, (f, t) in TRANSITION_PACK.items()
                        if (f == _fw_name or f == '通用') and t != 'drop')
                from sr_od.application.currency_war.kernel.cw_intention import (
                    locked_faction_scope as _lfs,
                )
                _lf = _lfs(getattr(strategy_state_of(sess), 'v3_intention', None)) or frozenset()
            except Exception:   # noqa: BLE001  代理 best-effort
                pass
            # ADR-0564 锁定线语境豁免(sim 接线):_rf 计算独立 try/except
            # (fail-closed False)且**显式后置**于 _lf 赋值之后,禁并入上方
            # from-import 组、禁与 _lf 同块——上方裸 except pass 的
            # best-effort 兜底是既有面(_lf 围栏放行集),若本新增量的
            # import/计算留在同块,未来改名/搬运抛 ImportError 会中断整块
            # → _lf 停留空集 → 锁定件被散牌围栏按非锁定语义误拦(行为变严
            # 零显影,一个新增量失败面摧毁既有兜底)。独立块 = 新增量故障
            # 面与既有兜底隔离。
            try:
                from sr_od.application.currency_war.kernel.cw_intention import (
                    locked_line_recipe_floor_conflict as _rfc,
                )
                _rf = _rfc(getattr(strategy_state_of(sess), 'v3_intention',
                                   None))
            except Exception:   # noqa: BLE001  豁免语境 best-effort:fail-closed
                _rf = False
            # ADR-0271(批⑦ F1,ADR-0219 第四次命中根治):上阵即 pop
            # ——生产语义(cw_state.simulate/mutate_bench_deployed 的
            # DeployMove:bench.pop → deployed.append → board 聚合)。
            # deployed 跨轮累积(生产跟踪态),select_deployments 吃真实
            # deployed_cids/deployed_fac/cap 语义;board = deployed 主阵营
            # 聚合(生产 board 口径)。ADR-0287:此处 cap=st.max_units()
            # 在轮末升级后读 → LevelUp 当轮腾出的 cap 立即生效(批㉘ F5
            # 「升级→上阵」链断一轮的修复)。
            _dep_cids = {d.char_id for d in iter_occupied_deployed(st.deployed)
                         if d.char_id}
            _dep_fac = _board_factions_of(st.deployed)
            # 围栏互斥(契约包 C1 + 六矛盾裁决1,步2):**被应用**的显式动作发出轮
            # select_deployments 围栏跳过自动部署(显式>围栏,同轮不叠加),
            # **账本必记一行 skip_fence**(防静默跳过,checks 可见——
            # check_skip_fence_pairing 同轮配对锁;迁移审计 w65(git 历史)/ADR-0323:被拒事务
            # 不置位 → 不跳围栏 → 板面欠载不再被事务风暴封死)。
            # 迁移审计 w716(git 历史) F1 修复(设计 §三):skip 轮不再整轮禁运——互斥辖域从
            # 「轮级」收窄为「通道级+保留集」,轮末对「围栏认可 ∖ 显式保留集」
            # 执行零支出残余补部署(P-F1:补部署严格支配禁运);skip_fence
            # 行保留(配对锁不破),reason 扩展 residual_fill 标记。
            _deploy_lag_units = 0
            _res_up = 0
            _res_held = 0
            if _explicit_deploy_seen:
                # T-279 R1(ADR-0640):m1p 换血卖出成功帧 → 补部署消费
                # 计划单一源(R1-a 计划 up 直投,前提破退 R1-b 卖出后
                # 现读重 derive,域辖域钉计划时点事实);非 m1p 显式动作
                # 轮(CompTransaction 等)维持现状围栏 fill(F4 辖域
                # 裁决:同款双源暴露面在彼处无分母无证据,不扩面)。
                if _m1p_sold:
                    _res_up, _res_held, _deploy_lag_units = \
                        _m1p_plan_fill_deploy(st, _m1p_plan, _m1p_ctx,
                                              sess)
                else:
                    _res_up, _res_held, _deploy_lag_units = \
                        _residual_fill_deploy(st, _tf, _tc, _fw, _lf,
                                              recipe_floor_lock_exempt=_rf)
                _acts.append({
                    '__type__': 'skip_fence',
                    'reason': (('m1p_plan_up' if _m1p_sold
                                else 'explicit_action_v2')
                               + ('+residual_fill' if _res_up else '')),
                    'residual_deployed': _res_up,
                    'residual_held': _res_held,
                })
                res.fence_skips += 1
                # board 已由 cw_state.simulate/_residual_fill_deploy 维护一致
            else:
                # ADR-0316:select_deployments 吃**紧缩占用序**(None 槽剔除;
                # 返回 up_idx 是占用序下标,下方回映射槽位下标)
                _occ_idx = [i for i, b in enumerate(st.bench) if b is not None]
                # 迁移审计 w652(git 历史) §5 处置①(重放语境冻结):真趟**行动前**快照。
                # 重放趟改用与真趟完全相同的围栏输入判定——残余语义 =
                # 「行动语境下仍有围栏认可件未上」。此前重放吃真趟部署
                # 后的 board/bench/deployed,围栏「成对」判据(board∪bench
                # 计数)被本轮自身部署翻转,把行动语境下合法 held 的件
                # 过判为可上(迁移审计 w652(git 历史) 两帧取证:seed 630027/630035 r6 lag=2,
                # 复算含 locked_factions 亦不变)。真趟输入不变。
                _snap_dep_fac = dict(_dep_fac)
                _snap_board = dict(st.board)
                _up_idx, _held_idx = _dl.select_deployments(
                    [b for b in st.bench if b is not None],
                    deployed_cids=_dep_cids,
                    deployed_fac=_dep_fac,
                    board=dict(st.board),
                    cap=st.max_units(),
                    target_factions=_tf,
                    target_cores=_tc,
                    fw_carry=_fw,
                    locked_factions=_lf,
                    recipe_floor_lock_exempt=_rf,
                )
                # ADR-0316:up_idx 是紧缩占用序 → 回映射槽位下标置 None
                # (ADR-0271 上阵即出 bench 语义不变)
                for _i in _up_idx:
                    if _i < len(_occ_idx):
                        bc = st.bench[_occ_idx[_i]]
                        if bc is not None:
                            deployed_place(st.deployed, bc)   # ADR-0392 槽位落位
                            st.bench[_occ_idx[_i]] = None
                st.board = _board_counts_of(st.deployed)
                # ADR-0287(批㉘ 检查项 ledger_deploy_lag_disclosure):重放
                # 围栏,残留可上件数入账本(deploy_lag_units)——部署时序
                # 回归(未来重构再犯轮首序/围栏漏上)可被 checks 常态扫出。
                # 语境冻结(迁移审计 w652(git 历史) §5 处置①):残余 bench(真趟部署后剩余)
                # 的「成对/点火」判据配**行动前**快照 board/deployed_fac
                # (_snap_*);占位与 cap 用部署后真实 deployed_cids/cap
                # (vacancy 不虚增——真趟已上场件真实占位)。残余语义 =
                # 「行动语境下仍有围栏认可件未上」:不再因本轮自身部署
                # 改变 board 阵营计数而翻转围栏「成对」判据产生口径过判
                # (迁移审计 w652(git 历史) 两帧取证:seed 630027/630035 r6 lag=2,冻结后判 0)。
                _lag_idx, _ = _dl.select_deployments(
                    [b for b in st.bench if b is not None],
                    deployed_cids={d.char_id
                                   for d in iter_occupied_deployed(st.deployed)
                                   if d.char_id},
                    deployed_fac=dict(_snap_dep_fac),
                    board=dict(_snap_board),
                    cap=st.max_units(),
                    target_factions=_tf,
                    target_cores=_tc,
                    fw_carry=_fw,
                    locked_factions=_lf,
                    recipe_floor_lock_exempt=_rf,
                )
                # 主趟围栏已仲裁 hold 的槽位不计 lag(W678 销案语义:
                # 「围栏 hold」本身不漏上,检查只盯「围栏认可却未执行」)。
                # 缺此豁免 = 重放 bench 上下文缩减(主趟 up 后剩余)会把
                # 主趟按容量/成对留置的件翻转成可上 → 0 锁假阳(seed
                # 31016 p1r6 lag=1,board 5/6 非满板 hold 形态)。
                _lag_units = _lag_excluding_fenced_holds(
                    _lag_idx,
                    [i for i, b in enumerate(st.bench) if b is not None],
                    {_occ_idx[j] for j in _held_idx if j < len(_occ_idx)})
                _deploy_lag_units = _lag_units
            # T3 同轮保留集「部署即销」(生命周期出口①,sim 对应物):
            # 部署决议(围栏趟/skip 残余补部署)上板的名从保留集销账——
            # 保护使垫件活到部署阶段、上板后保护使命完成。
            from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
                stall_buys_prune_deployed as _sbpd,
            )
            _sbpd(sess, {d.char_id
                         for d in iter_occupied_deployed(st.deployed)
                         if d.char_id})
            # `w614_sim_fidelity/` G2:上阵代理记账(轮末部署块后取值;纯观测零漂移)。
            # - bench_recipe_pieces:bench 上配方隶属件数(char∈target core
            #   或 faction∈target factions;目标集=部署块同源 session 现读,
            #   未锁定时空集→恒 0)——逐轮落账本,局级累计=「配方件躺 bench
            #   轮数」(实机出口 `w608_ladder_adversarial/` M2 的 sim 对应物);
            # - deployed_power:上阵战力贡献代理 = Σ(star + core∈target 计 1)
            #   ——星级加权 + 核心标记,记账级代理(非物理仿真),供成型质量
            #   粗比较;与 Δ池结算键(_settle_rung)口径无关。
            _bench_recipe = sum(
                1 for b in iter_occupied(st.bench)
                if b.char_id in _tc or b.faction in _tf)
            _dep_power = sum(
                (int(getattr(d, 'star', 1) or 1)
                 + (1 if getattr(d, 'char_id', '') in _tc else 0))
                for d in iter_occupied_deployed(st.deployed))
            if _seg_plane == 1:
                _bench_recipe_rounds_p1 += _bench_recipe
                _dep_power_sum_p1 += _dep_power
                _dep_power_rounds_p1 += 1
                # (生锈暴露峰值已移到轮账本行键写入点采样——原此处取值
                # 与行键 `rust_units` 是两个观测时点,轮中段卖出回充装备
                # [T-169 执行面:victim 带装回收进 owned 池]会让分配器穿戴
                # 前后的两读数分叉,峰值 ≠ 行值最大值;T-169 锁红重推后
                # 收口为「峰值 = 逐轮账本行口径最大值」,恒等式由构造保证。)
            if res.dir_round == 99 and _direction_established(sess):
                res.dir_round = rn
            # `w162_inject/`/ADR-0364:P1 段锁定轮计数(①资格通道激活直证——
            # 注入前语料下 P1 恒 unlocked/p1_pair,此键恒 0[`w161_refresh/`])
            if (_seg_plane == 1
                    and getattr(strategy_state_of(sess), 'v3_intention', None) is not None
                    and getattr(strategy_state_of(sess).v3_intention, 'phase', '') == 'locked'):
                res.p1_locked_rounds += 1
            # r260:按本局采样的真实节点类型结算(奖励/补给不掉血;
            # 遭遇=boss×1.15;战斗=方向二元;boss=boss 档)
            # r340:板深条件化实机 Δ 池优先(经验分布重放——
            # 深[6-8] -1.0 vs [3-5] -11.3 的板深效应入 sim);
            # 无匹配桶回退旧方向二元模型。
            # r343:同修正——Δ 采样用可 deploy 深度;① 收口进
            # _deployable_depth 单一源(原三处内联口径不一)
            # ADR-0279(批⑬ F4):battle Δ 采样键=rung(成型度一维
            # 分桶,与 boss_settle_delta 同源 _settle_rung)——depth-
            # only 池对 d9 成型局高估战损 ~6.4hp/场,是 sim hp_ge_60
            # vs 实机 32% 裂口的最大已定量化分量;encounter 亦 rung 键
            # (v11/ADR-0407,depth 键下期望伤害真平故迁 rung);
            # boss 键=净星深(迁移审计 w240(git 历史)/ADR-0404,修升星方向冲突)。
            _dep = _deployable_depth(st)
            # `w193_p2sim/`/ADR-0377:参数化校准层辖 plane≥2 战斗类结算——绕过
            # Δ池 plane=2 合并采样(防饥饿守卫已抹平其条件性,ADR-0362
            # 判「假条件化」;Phase 3 桶键 form×round 到量[n≥5]后让位
            # 池采样)。calibrated=False = 逐位回 `w157_p2/` 路径(池优先 +
            # node_delta 回退档)。planes=1 恒不进本分支(P1 零漂移)。
            _p2_wp: float | None = None
            if (st.plane >= 2 and _p2c.calibrated
                    and nodes[rn - 1] in ('battle', 'encounter', 'boss')):
                delta, _p2_wp = p2_combat_delta(
                    st, nodes[rn - 1], rn, rng, _p2c)
            else:
                # ADR-0362:P2 段(uncalibrated 臂)结算查 Δ池 plane=2 桶
                # (位面内兜底,不跨位面回退);缺桶回退层见 node_delta 的
                # plane 分支。P1 段结算同原式(逐位零漂移)。
                # 粗参数两态模型(coarse_battle 模块单一源):战斗类
                # 节点(battle/encounter/boss)默认脱离 Δ池经验分布,
                # 改胜态查表(+2)/败态节点级伤害直方采样;``delta``
                # 模式保留原 Δ池路径作对照臂(粗模型转正前的三率对拍
                # 验证批消费)。reward/supply 两模式下均仍走 Δ池。
                _node = nodes[rn - 1]
                from sr_od.application.currency_war.kernel import (
                    cw_coarse_battle as _cb,
                )
                if (_cb.BATTLE_ENGINE_MODE == 'coarse'
                        and _node in ('battle', 'encounter', 'boss')):
                    # 位面维透传(P1 先行):P1 层现值/P2 别名,取表见
                    # cw_coarse_battle 模块头;默认 plane=1 = 旧调用零漂移。
                    delta = _cb.sample_battle_delta(
                        _node, _settle_rung(st), st.hp, rng,
                        difficulty=getattr(st, 'enemy_difficulty', None),
                        plane=st.plane)
                else:
                    if _node == 'battle':
                        _ld = live_delta_for('battle', _settle_rung(st), rng,
                                             pool_map=pool_map, plane=st.plane)
                    elif _node == 'boss':
                        # 迁移审计 w240(git 历史)/ADR-0404:boss 采样键=净星深(修 Σboard 升星
                        # 方向冲突,见 live_delta_for docstring)。
                        _ld = live_delta_for(
                            'boss', deployed_star_depth(st), rng,
                            pool_map=pool_map, plane=st.plane)
                    elif _node == 'encounter':
                        # v11/ADR-0407:encounter 采样键=rung(与 battle 同源
                        # _settle_rung——depth 键下期望伤害真平,`w250_delta_pool/` 查证;
                        # live_delta_for 桶缺逐级下探路径与 battle 共用)。
                        _ld = live_delta_for('encounter', _settle_rung(st), rng,
                                             pool_map=pool_map, plane=st.plane)
                    elif _node in ('reward', 'supply'):
                        # ADR-0292(批㉗ F3/F4):reward/supply 由恒 EARLY_WIN_DELTA
                        # 改 Δ池经验分布采样(语料真值;F4 胖尾经复核为跨 run 配对
                        # 伪影,真值分布 = 恒 +2,采样口径保语料增长自动跟真)。
                        # 池缺 → live_delta_for None → node_delta 回退常数。
                        _ld = live_delta_for(_node, _dep, rng,
                                             pool_map=pool_map, plane=st.plane)
                    else:
                        _ld = None
                    if _ld is not None:
                        delta = _ld
                    elif _node in ('battle', 'encounter', 'boss'):
                        # `w493_income_calib/` D1(ADR-0447):delta 对照臂桶缺回退由 迁移审计 w31(git 历史) 无
                        # 成型度阶梯(node_win_p/battle_delta)改接粗模型
                        # 注入胜率——零新数值(纯复用 cw_coarse_battle 已
                        # 验收表与 plaza 收缩),对照臂与主路径同交付口径。
                        # ADR-0277 教训边界:胜率只来自 _WIN_TABLE 遥测
                        # p_data + plaza Beta 收缩(份额硬顶 25%,零样本
                        # 单元原样返回),不引入设计拍值。默认 coarse 主
                        # 路径不经本分支(P1 默认批逐位零漂移,B1 锁)。
                        # 旧 boss_settle_delta/battle_delta 保留为
                        # ADR-0308 最终兜底语义(本路径不再消费;测试/
                        # 单元引用不受影响)。
                        delta = _cb.sample_battle_delta(
                            _node, _settle_rung(st), st.hp, rng,
                            difficulty=getattr(st, 'enemy_difficulty', None),
                            plane=st.plane)
                    else:
                        delta = node_delta(_node, rn, res.dir_round, rng,
                                           plane=st.plane)
            # 批㉘ F6(ADR-0287,hp_upper_bound_truth):HP 结算加上界钳制。
            # 游戏机制真值未见文档证据(语料 max hp_after=88 / sim max 92
            # 均未触界,非 cap 证明)——暂按 cap 100 钳制;批㉗ reward
            # 胖尾(+20~39 回血)落地后 hp 破百的担忧已随 ADR-0292 复核
            # 消解(胖尾为跨 run 配对伪影,池真值恒 +2,实测触界率 0),
            # 钳制维持(防御性不变式);实机满血样本核真后更新本常量
            # (检查项 hp_upper_bound_truth 锁 hp>100 恒 0)。
            # 装备效果通道(校准假设层):sim 已知缺口「装备效果未建模」
            # (ADR-0394 后果节声明的边界)的显式参数化——败局伤害按
            # 已穿进阶成品件数线性折减。仅 battle/encounter(boss 败局
            # 钳制语义冻结,不折减);0=关闭(逐位零漂移)。量级无实机
            # 定量锚点(`w465_equip_flow/` 装备流分析:P1 白板八战 -62 为裸装口径,
            # 无「穿装对照」数据),总折减 60% 硬顶——A/B 消费时按
            # 灵敏度带呈报效应量,不作为已标定值。
            if _wear_eff > 0 and delta < 0 \
                    and nodes[rn - 1] in ('battle', 'encounter'):
                from sr_od.application.currency_war.data.cw_synthesis import (
                    RESERVED_COMPONENTS as _RC,
                )
                _worn_units = 0.0
                for _d in (st.deployed or []):
                    for _e in (getattr(_d, 'equips', ()) or ()):
                        # 进阶成品全权 1.0;基础件半权 0.5(用户裁定
                        # 「简易件效果通常不大」;穿戴可逆=卖角色取回)
                        _worn_units += 0.5 if _e in _RC else 1.0
                if _worn_units > 0:
                    delta = max(delta, round(
                        delta * (1.0 - min(0.6, _wear_eff * _worn_units))))
            st.hp = max(0, min(HP_UPPER_BOUND, int(st.hp + delta)))
            # ADR-0351 计数口径(奖励/补给轮不计连胜数;实机奖励轮结算后
            # streak 恒 0):战斗类节点(battle/encounter/boss)胜后计数
            # (delta>0)否则归零;奖励/补给轮不动 streak。发金半句已按
            # ADR-0439 修正(奖励轮照发表,见收入段)。
            if nodes[rn - 1] in ('battle', 'encounter', 'boss'):
                streak = streak + 1 if delta > 0 else 0
                # 带符号 streak(生产口径:连胜 +/连败 −;奖励/补给轮不动,
                # 与无符号计数同规则)。备战帧 st.streak 恒 None 曾使 ④连败
                # 金流与 ①连败门在 sim 成死输入(观测态补齐)。
                streak_signed = (streak_signed + 1 if streak_signed > 0 else 1) \
                    if delta > 0 \
                    else (streak_signed - 1 if streak_signed < 0 else -1)
            # ADR-0439:败轮金路径的上一轮状态(败态判据与结算段一致
            # = delta<=0;奖励/补给轮不覆盖——败态跨奖励轮保留,
            # 但奖励轮收入分支不消费败态,仅下一战斗轮消费)
            _prev_node = nodes[rn - 1]
            _prev_combat_lost = (nodes[rn - 1] in ('battle', 'encounter', 'boss')
                                 and delta <= 0)
            # 批⑤ F4(ADR-0276):结算补写 session.last_streak——生产语义
            # = 结算「连胜×N」写 session(结算观察半直写,ADR-0583),
            # r308 保连胜门/evaluate 连胜响应消费读 session;sim 旧连胜
            # 只存本地变量算收入,决策侧连胜响应恒盲。
            # 观测态补齐:改写带符号值并对齐备战帧 state.streak(生产
            # 备战读 session.last_streak,带符号 连胜+/连败−;旧无符号
            # 写法连败恒 0,连败侧消费面在 sim 永远读不到连败)。正值域
            # 与旧写法逐位相同,唯一消费面差异在连败侧(补齐目标本身);
            # v2 消费面核验:allocator._w_per_battle 负值钳 0、discipline
            # _streak_floor streak<2 门负值不点火,均与旧 0 等价。
            sess.last_streak = streak_signed
            st.streak = streak_signed
            res.hp_trail.append(st.hp)
            # ADR-0362:P2 段事件用跨位面单调轮号(_ts);P1 段 _ts==rn
            # (零漂移);方向判据 P2 段=「P1 内已建立」
            res.hp_events.append(( _ts, nodes[rn - 1], delta,
                                   res.dir_round <= rn if st.plane == 1
                                   else res.dir_round < 99))
            if st.plane >= 2:
                # ADR-0362:P2 段观测(存活轮/战斗胜负)
                res.p2_rounds += 1
                if nodes[rn - 1] in ('battle', 'encounter', 'boss'):
                    res.p2_combat_total += 1
                    res.p2_combat_wins += 1 if delta >= 0 else 0
            # ① 账本:每轮一行(轮内段聚合;depth 单一源;core_count
            # 按 target 语境路由 core_count_for——③ 攒数据地基:
            # 桥池 fixed+core/三人组单一口径(旧 v1 线库 core_cards
            # 随 ADR-0336 删除),旧 core_trio_count 绑死仙舟非仙舟
            # 线局恒 0,审查二轮#8)
            _depth = _deployable_depth(st)
            res.depth_trail.append(_depth)
            # r393(装备层执行代理):supply 节点 = 3 选 1 装备——
            # decide_supply(纯逻辑,与 run_supply_node 同源)选 →
            # 入 st.equips(owned 池);equip_allocation(纯逻辑,与
            # CwOpEquipAll 同源)分配给 deployed → 账本 equipped 字段。
            # 装备获取采样(供给重校准后):池结构见 EQUIP_GRANT_CALIB_VERSION
            # 模块常量注;带钻概率 15%(实机简报词缀影响的粗估,校准点)。
            # r388 类 bug(开局乱穿)从此 sim 可见。
            # ADR-0294 件2(ADR-0289 §5 裁决,红项 174/300):采样池
            # 只进注册表认识的装备名(EQUIPMENT_ROSTER 单一源)——
            # '未知装备' 与价值表旧名(注册表外)不进 owned 池;带钻
            # 是词缀元数据,不再以 '钻石' 占位实体进池(占位实体只进
            # 披露计数 res.phantom_supply_picks,不进池)。
            # 供给重校准:发放通道 = supply + reward 两类节点(实机发放
            # 时点画像:~3.8 个发放轮/局,sim 供给节点仅 ~1 个/局——单靠
            # 它永远凑不出实机件数;奖励节点同为零战力节点,承载通道
            # 语义等价)。结构与常量见 EQUIP_GRANT_CALIB_VERSION 注。
            _equipped_now: list[tuple[str, str]] = []
            if nodes[rn - 1] in ('supply', 'reward'):
                from sr_od.application.currency_war.data.cw_equipment_data import (
                    EQUIPMENT_ROSTER,
                )
                from sr_od.application.currency_war.kernel.cw_events import (
                    _EQUIP_VALUE as _EV,
                )
                from sr_od.application.currency_war.kernel.cw_events import (
                    SupplyOption,
                    decide_supply,
                )
                _pool_names = [n for n in _EV if n in EQUIPMENT_ROSTER]
                # 供给重校准:3 选项池 = 基础件 8 名均匀(实机供给节点
                # 近全基础件,见 EQUIP_GRANT_CALIB_VERSION 注);进阶名
                # 只走下方追加件通道。decide_supply 决策语义零改动。
                from sr_od.application.currency_war.data.cw_synthesis import (
                    RESERVED_COMPONENTS as _BASICS,
                )
                _basic_names = [n for n in _BASICS if n in EQUIPMENT_ROSTER]
                _adv_names = [n for n in _pool_names if n not in _BASICS]

                def _sample_supply_opts(
                        _basic: list[str]) -> list[SupplyOption]:
                    # 发放采样(3 列;带钻 15% 粗估校准点)——两步各自
                    # 调用一次,消耗局内 rng 流(`w212_sim_equip/` 批 monkeypatch 臂
                    # 用独立 rng 是补丁层限制,原生实现必须走局内 rng
                    # 才与实机发放分布一致)
                    return [SupplyOption(
                        idx=_oi, char='', equip=rng.choice(_basic),
                        has_diamond=rng.random() < 0.15)
                        for _oi in range(3)]

                # `w213_sim_supply/`/ADR-0394:生产 RunSupplyNode 是真两步——
                # 第一步 decide_supply(refresh_used=session 标志):
                # 带钻→直接选;全无钻且本局未刷过→返回 refresh=True
                # (sim 旧形态漏掉这一步的分支:恒把 refresh 标志丢弃、
                # 直接取 _opts[pick.idx]=options[0],价值评分分支
                # 在 sim 从未执行 = 「恒取 idx0」伪影,ADR-0394);
                # 刷新→session 标志置位(run_supply_node:71 同语义,
                # StrategySession._supply_refresh_used 为正式字段)+
                # 重掷 3 列再选;refresh_used=True 时 decide_supply
                # 走 key_equips 契合(+10)+ 通用价值评分。补给刷新
                # 免费(「剩余次数:1」,run_supply_node:50)——不耗金。
                _is_supply = nodes[rn - 1] == 'supply'
                if _is_supply:
                    # 补给节点:真两步 decide_supply(语义零改动,见下)
                    _opts = _sample_supply_opts(_basic_names)
                    _pick = decide_supply(_opts, st, strategy_state_of(sess).target_comp, None,
                                          refresh_used=exec_state_of(sess)._supply_refresh_used)
                    if _pick.refresh and not exec_state_of(sess)._supply_refresh_used:
                        exec_state_of(sess)._supply_refresh_used = True
                        _opts = _sample_supply_opts(_basic_names)
                        _pick = decide_supply(_opts, st, strategy_state_of(sess).target_comp, None,
                                              refresh_used=True)
                    st.equips.append(_opts[_pick.idx].equip)
                    _equip_grants += 1   # `w614_sim_fidelity/` G1 发放落账
                else:
                    # 奖励节点:非选择型发放,直接 1 件基础件(均匀)
                    st.equips.append(rng.choice(_basic_names))
                    _equip_grants += 1   # `w614_sim_fidelity/` G1 发放落账
                # 追加件(多通道聚合代理):实机装备来自奖励/补给/投资
                # 环境/遭遇后多通道,sim 只有上述两类节点承载 →
                # 以固定概率补 1 件(基础为主、含少量进阶,
                # 常量见 EQUIP_GRANT_BONUS_P 注),非决策件(均匀采样,
                # 无带钻语义——钻只属补给节点选项)。
                if rng.random() < EQUIP_GRANT_BONUS_P:
                    if rng.random() < EQUIP_GRANT_BONUS_ADV_SHARE:
                        st.equips.append(rng.choice(_adv_names))
                    else:
                        st.equips.append(rng.choice(_basic_names))
                    _equip_grants += 1   # `w614_sim_fidelity/` G1 追加件落账
                # 工具注入旁路(21 号稿 §4/§5 最小面;缺省零漂移,见
                # TOOL_GRANT_INJECT_POOL 注)
                if TOOL_GRANT_INJECT_POOL and rng.random() < TOOL_GRANT_INJECT_P:
                    st.equips.append(rng.choice(TOOL_GRANT_INJECT_POOL))
                    _equip_grants += 1
                if _is_supply and _pick.idx < len(_opts) \
                        and _opts[_pick.idx].has_diamond:
                    res.phantom_supply_picks += 1   # 披露计数(不进池)
            # 合成执行链 hook(默认关,synthesis_chain=True 点火):
            # **方向确定性门(用户裁决:组件留给目标阵容,乱合成=后期缺
            # 关键装备)——意向已锁线(phase=='locked'∧locked_comp,与
            # _target_comp_label 消费判据同款)才允许合成**;P1 FORM 期
            # target_comp 易变,对着它合成=压注未定方向。门内再过隶属度
            # (plan_syntheses:目标件 1.0/共享件 0.5,默认阈值 1.0 只合
            # 目标件)。持有组件凑齐配方 → 装备栏内合成(耗金口径:文档
            # 与注册表无耗金记载,按免费建模,声明见 plan_syntheses)。
            # 产物是进阶成品、不在 cw_synthesis.RESERVED_COMPONENTS——
            # 自然进入下方 equip_allocation 的可穿池,与 ADR-0265 组件
            # 保留池不对撞(本门是叠加在保留池之上的兑现门,不放松保留
            # 条件);时机 = 每备战期分配前,最小改动不重构分配器。
            _synth_events: list[str] = []
            _ist = getattr(strategy_state_of(sess), 'v3_intention', None)
            _line_locked = (getattr(_ist, 'phase', '') == 'locked'
                            and getattr(_ist, 'locked_comp', ''))
            if _synth_on and _line_locked and st.equips:
                from sr_od.application.currency_war.data.cw_synthesis import (
                    plan_syntheses,
                )
                _tgt = getattr(strategy_state_of(sess), 'target_comp', None)
                _keys = list(getattr(_tgt, 'key_equips', ()) or ()) \
                    if _tgt is not None else []
                # P2 锁线回收:合成门需要的组件若正被穿着,先取回再合成
                # (用户裁定:基础件穿着可逆=卖角色取回;sim 语义与卖出
                # 回收 equips.extend 同向,这里是「扳手/卖出」的等价代理)
                from sr_od.application.currency_war.data.cw_synthesis import (
                    component_demand as _cd,
                )
                _need_comps = set(_cd(_keys))
                for _d in iter_occupied_deployed(st.deployed):
                    for _e in list(getattr(_d, 'equips', ()) or ()):
                        if _e in _need_comps:
                            _d.equips.remove(_e)
                            st.equips.append(_e)
                for _adv, _comps in plan_syntheses(_keys, st.equips):
                    for _c in _comps:
                        st.equips.remove(_c)
                    st.equips.append(_adv)
                    _synth_events.append(_adv)
                    _equip_syntheses += 1   # `w614_sim_fidelity/` G1 合成落账
            _duty = False
            if st.equips and deployed_occupied(st.deployed):   # ADR-0392 占用数(定长表恒真值)
                from sr_od.application.currency_war.data.cw_equipment_data import (
                    EQUIP_TOOL_CATEGORY as _EQTOOL,
                )

                # 工具注入伴随面(21 号稿 §4):工具不进可穿池(执行层
                # wearable 同口径,类别=工具排除);st.equips 本体不动,
                # 工具行为分布由工具判据消费端观测。
                from sr_od.application.currency_war.data.cw_equipment_data import (
                    EQUIPMENTS as _EQM,
                )
                from sr_od.application.currency_war.kernel.cw_comps import (
                    equip_allocation,
                )
                _wearable_equips = [n for n in st.equips
                                    if _EQM.get(n) is not None
                                    and _EQM[n].category != _EQTOOL]
                # `w212_sim_equip/`/ADR-0393:equip_allocation 生产调用形态——
                # ① occupied = 画面已穿(生产 occupied_m7
                # 同语义;旧 sim 恒 None → 配对守卫看不见历史已穿,只看得
                # 见本趟内部分配,跨轮守卫形同虚设)。BenchChar.equips
                # (r393 写回)即跨轮已穿真值。
                _occupied: dict[tuple[str, int], list[str]] = {}
                for d in iter_occupied_deployed(st.deployed):
                    _occupied[(getattr(d, 'position_pref', '') or '',
                               int(getattr(d, 'slot', 0) or 0))
                              ] = list(getattr(d, 'equips', ()) or ())
                # (②carry duty 的 sim 观测桩已随五开关定谳清理摘除,
                # ADR-0487:谓词 p1_iface_carry_duty_active 已删;账本行
                # p1_duty 键按披露稳定保留恒 False。)
                _equipped_now = equip_allocation(
                    strategy_state_of(sess).target_comp, st.deployed, _wearable_equips,
                    occupied=_occupied)
                # ADR-0312(迁移审计 w50(git 历史) L2 雏形):分配结果同步写回 BenchChar.equips
                # ——星徽/卡带的羁绊贡献随 unit_bond_tags 进 board(生产
                # tracked_deployed[].equips 同语义)。写回按**多重集差**:
                # 本趟新增 = 本趟分配 − 轮前已穿(防跨轮对同一人重复记同一
                # 件);同名多件各自记数(基础件发放均匀,同名复制常见——
                # 旧「not in」防重守卫把同趟第二件静默丢弃 = 装备凭空消失)。
                _adds: dict[str, list[str]] = {}
                for _who, _what in _equipped_now:
                    if _what in st.equips:
                        st.equips.remove(_what)
                        _equip_wears += 1   # `w614_sim_fidelity/` G1 穿戴落账(owned→已穿)
                    _adds.setdefault(_who, []).append(_what)
                for d in iter_occupied_deployed(st.deployed):
                    _want = _adds.pop(d.char_id, None)
                    if not _want:
                        continue
                    _pre = list(d.equips)
                    for _w in _want:
                        if _w in _pre:
                            _pre.remove(_w)   # 轮前已穿,不双记
                        else:
                            d.equips.append(_w)
            from sr_od.application.currency_war.kernel.cw_line_defs import (
                core_count_for,
            )
            # ===== 同轮卖→买回分键投影(sim71 批;双层只读零 rng)=====
            # 实例级 = obs.sell_buyback_loops(逐笔明细);局级 =
            # cw4_counters 两键 sell_buyback_count / sell_buyback_net_gold
            # (Σ买价−卖返,经 obs.cw4_counters 轮差分同路入账本;容器
            # 缺席静默跳过 = 缺省零漂移)。投影本身只读本轮 _acts,
            # 零 rng/零行为面(函数 docstring 见 project_sell_buyback)。
            _sell_buyback_loops = project_sell_buyback(_acts)
            if _sell_buyback_loops:
                _cts_sb = getattr(strategy_state_of(sess), 'cw4_counters', None)
                if _cts_sb is not None:
                    _cts_sb['sell_buyback_count'] = \
                        _cts_sb.get('sell_buyback_count', 0) \
                        + len(_sell_buyback_loops)
                    _cts_sb['sell_buyback_net_gold'] = \
                        _cts_sb.get('sell_buyback_net_gold', 0) \
                        + sum(lp['net_gold'] for lp in _sell_buyback_loops)
            res.ledger.append({
                'ts': _ts,   # 单调轮序号(跨位面累计;P1 段 == rn;审查①#9)
                'plane': st.plane, 'round_num': rn,
                'gold': st.gold, 'hp': st.hp,
                # ADR-0343:成型停手态入账本(轮内 OR 聚合;检查器豁免/判读锚点数据源)
                'formed_stop': _round_formed_stop,
                # 血预算停手·终止豁免位(轮入口首段快照;写入侧单一源 =
                # checks.segments.terminal_release_bit,消费 =
                # seg_p1_blood_budget_refresh 行键豁免面——位真 = 带内
                # 刷新合法的账本依据)
                'terminal_release': _round_terminal_release,
                #  已随 C4 开关族删除——旧方案清退批,清查报告
                #  OLD_MIX_AUDIT §1.3;v3_line_gate_* session 字段同批删。)
                # `w227_handoff_gate/`/ADR-0400:末窗承接门缺口(0=不辖/达标;判读承接维
                # 触发面;与 formed_stop=False 并读 = 门扣住证据行)
                'handoff_gap': _round_handoff_gap,
                # 迁移审计 w238(git 历史)/ADR-0403:boss 投影 hp(None=投影关/非末窗;判读
                # 「boss 后投影 hp」面,与 handoff_gap 同点快照)
                'handoff_hp_proj': _round_handoff_hp_proj,
                # 迁移审计 w114(git 历史)/ADR-0346 相位影子观测(轮入口快照;零消费)
                'phase': _round_phase,
                'form_ok': _round_form_ok,
                # form_score 已退役(历史账本只读);替代披露口径 = b_t
                'b_t': _round_b_t,
                # (expected_paths 挂起期望快照键已随 ADR-0651 两态制退役:
                #  条目表拆除无快照可写,sim 新行不再携带;schema 字段按
                #  历史数据只读口径保留,读端旧行分型不变。)
                'dp_posture': _round_dp_posture,
                # `w611_econ_cycle/` 储备/义务披露(轮入口快照;生产 decisions 行 sess_* 同语义)
                'reserve_cap': _round_reserve_cap,
                'reserve_overflow': _round_reserve_overflow,
                'release_budget': _round_release_budget,
                'release_reason': _round_release_reason,
                'posture_unfulfilled': _round_posture_unfulfilled,
                'piggy_reward': _round_piggy,
                # ②carry 装备分配义务帧(键按披露稳定保留;谓词已随五开关
                # 定谳清理删除,恒 False——历史账本字段只读口径,ADR-0487)
                'p1_duty': _duty,
                # 迁移审计 w146(git 历史) v3 意向状态(与生产 decisions 行同构;sim 分析批
                # 按它分锁定/未锁局——target_comp 只在锁定后非空,phase
                # 才能区分 unlocked/weak/locked)
                'v3_intention': serialize_intention(
                    getattr(strategy_state_of(sess), 'v3_intention', None)),
                'target_comp': _target_comp_label(sess),
                'state': {'board': dict(st.board), 'level': st.level,
                          # r394(过渡阵容判据接线):板面阵营档位——
                          # deployed 的 factions 计数(生产 board 口径;
                          # 旧恒空 dict 让「r几凑到配方X档/三人组上场」
                          # 在 sim 判读不可见)。recipe_tier 判据的输入。
                          'board_factions': _board_factions_of(st.deployed),
                          # bench 对齐生产 BenchChar 形状(dict 带
                          # char_id/faction——视图/检查读 b['faction']
                          # 不炸;审查#3)。ADR-0316:序列化保持**占用序
                          # 紧缩**(null 槽不落账本——下游 checks/视图按
                          # 紧缩数组消费,零迁移;占用数=len)
                          'bench': [{'char_id': b.char_id,
                                     'faction': b.faction,
                                     'slot': b.slot,
                                     # 星级入账本(与 deployed star 同语义
                                     # 同口径):3合1 merge 后 bench 可有
                                     # star≥2,_asset_thickness(C1 口径
                                     # 纯终局件星级当量)重算需要它——缺
                                     # 此键该度量只对 deployed 侧成立
                                     'star': int(getattr(b, 'star', 1) or 1),
                                     # 装备随人入账本(与 deployed
                                     # equips 同语义)——换下场角色可带装,
                                     # 缺此键会让保有量口径漏计 bench 侧
                                     'equips': list(getattr(b, 'equips', ()) or ())}
                                    for b in iter_occupied(st.bench)],
                          # r391(执行层代理配套):deployed/cap 入账本
                          # ——「开局 deploy<cap」检查项的数据源
                          # (r387 类 bug 的 sim 常态化防线)。deployed
                          # 形状对齐 rounds 视图消费(dict 带
                          # position_pref,同 bench 形状)。
                          'deployed': [{'char_id': d.char_id,
                                        'faction': d.faction,
                                        'slot': d.slot,
                                        'star': int(getattr(d, 'star', 1) or 1),   # 迁移审计 w88(git 历史)/ADR-0339:星级入账本(2★ 达成率度量)
                                         'position_pref': d.position_pref,
                                        # ADR-0312(迁移审计 w50(git 历史)):装备随人进账本——
                                        # 检查镜像(_board_agg_of_deployed_
                                        # row)复算星徽羁绊贡献需要它
                                        'equips': list(getattr(d, 'equips', ())
                                                       or ())}
                                       for d in (st.deployed or [])
                                       if getattr(d, 'char_id', '')],
                          'cap': st.max_units(),
                          # r393(装备层代理):本轮分配结果(谁穿了什么)
                          # +owned 余量——「开局零穿着/乱穿」检查项数据源。
                          'equipped': [{'char': w, 'equip': e}
                                       for w, e in _equipped_now],
                          'owned_equips': list(st.equips),
                          # 观测态保真位入账本(带符号 streak + hp 可信
                          # 两位;死输入哨兵检查 sim_streak_propagation_
                          # live 与 replay 对拍的观测面)
                          'streak': st.streak,
                          'hp_readable': bool(st.hp_readable),
                          'hp_trusted': bool(st.hp_trusted),
                          # 观测硬依赖键(决策入口快照,语义见轮入口块
                          # 注释):bench_full_flag 消费 = 锁#10 D1 对账;
                          # board_next_tier 消费 = Δp_tier 档位分解标定。
                          'bench_full_flag': _round_bench_full,
                          'board_next_tier': dict(_round_board_next_tier),
                          # (p1_downgrade_active 账本位已随 v2 退役链退役——统一迁移批
                          #  ② MAP A7/B 类;新数据恒缺省。)
                          # 表。生产 OCR 覆盖 21% 的 sim 全量对账源)
                          'refresh_probs': (
                              dict(st.refresh_probs)
                              if st.refresh_probs else None)},
                # 投资环境名(生产 decisions 行 _extra.sess_active_env
                # 同名同位;invest 注入写 session.active_env,cw_replay
                # 回读消费。空串 = 未注入/无环境——机制性缺省,非缺口)
                'sess_active_env': str(getattr(sess, 'active_env', '') or ''),
                # 持卡注入面轮末快照(生产 decisions 行 top-level
                # active_strategies 同语义;空列表 = 未注入/无持卡——
                # 消费面 = sim 检查器 τ 的覆写语境观测键,ADR-0598
                # 兑现 ledger.py 近似声明的预留义务)。
                'sess_active_strategies': list(sess.active_strategies),
                # (W829 支出门拒因枚举计数 sess_spend_gate_block 已随
                #  spend_gate 开关族删除——旧方案清退批,清查报告
                #  OLD_MIX_AUDIT §1.3;v3_sg_block session 键同批删。)
                'actions': _acts,
                # 达标臂发射事件(见上方「达标臂发射事件建模」块;None=
                # 本轮达标臂未触发——非战斗节点/未成型/准入预估不可得)
                'launch': _round_launch,
                # M1″ 计划+执行面(_m1p_plan_and_record;None = 观测异常帧。
                # nonempty = 谓词判计划非空 ⇒ M1″ 发射;executed = 本帧
                # 计划已经执行转录(卖出臂真卖,T-169 执行面接入;键缺省
                # = 计划空/执行异常,锁测试双向断言与换血可见性判读锚)。
                # abstain = 弃权键(cap_unreadable/membership_unreadable/
                # input_missing);sell = 卖序;up = 上序件数;up_names =
                # 上序名单(T-279 R2 名字级,义务件处置四态直读的判读锚);
                # reasons = 逐件拒因。卖出动作明细 = actions 流 SellDeployed
                # 行(reason='m1_swap_redeploy'),补上 = 同轮 skip_fence 行
                # residual_deployed 计数(执行语义见 m1p_swap_execute;
                # T-279 R1 起补上消费计划单一源,skip_fence reason 分键
                # m1p_plan_up,语义见 _m1p_plan_fill_deploy/ADR-0640)。
                # R3-a(T-307/ADR-0647)发射帧盲窗显影键(独立行内键,
                # 邻位透传):'launch_short_circuit' = 本轮为发射帧、生产
                # 无 M1″ 决策帧(备战动作链被发射短路,m1p 恒 None 的
                # 成因);None = 非发射帧(m1p 应在场)或观测异常帧。
                # 遥测层改动,sim 结构性无行为面(纯观测键)。
                'm1p_obs_skipped': _m1p_obs_skipped,
                'm1p': _m1p_obs,
                # 采购面三观察计数(见轮首「采购面三观察计数」块):
                # locked_b=本轮最大锁定采购集 |B|(0=帧全未锁);
                # overcap_frames=超容决策帧数;refresh_avail_frames=
                # 「刷新可得」决策帧数;refreshes=本轮实际刷新数(轮首差分)。
                # 冷启动 r1-r4 买次数/金花费不另设键——actions/sim.spend
                # 既有轮级披露即数据源,统计端聚合。
                'obs': {
                    'locked_b': _obs_locked_b,
                    'overcap_frames': _obs_overcap_frames,
                    'refresh_avail_frames': _obs_refresh_avail,
                    'refreshes': res.refreshes - _obs_refreshes0,
                    # 必花域观测三键(20 号稿 §6):zone_frames = 必花域
                    # 动作帧数;zero_consume = 其中零消费帧(白名单帧归此,
                    # 判读看归因);layer_hit = 层命中计数(L1 普通/L2 垫件/
                    # L3 升级,dict)。
                    'must_spend_zone_frames': _ms_zone,
                    'must_spend_zero_consume': _ms_zero,
                    'must_spend_layer_hit': dict(_ms_layer),
                    # 刷新触发源分键(观测面):源 →
                    # 本轮实刷次数('other' = reason 未标/旧调用)。
                    'refresh_trigger': dict(_obs_refresh_src),
                    # cw4_counters 轮差分(策略行为观测计数账本可见性):
                    # 本轮增量(键 = strategy_state_of(session).cw4_counters 原键,含 fenced
                    # 拆键/theta 成因分桶);零增量 = 空 dict。
                    'cw4_counters': {
                        k: int(v) - int(_cw4_before.get(k, 0))
                        for k, v in (getattr(strategy_state_of(sess), 'cw4_counters', None)
                                     or {}).items()
                        if int(v) != int(_cw4_before.get(k, 0))},
                    # 同轮卖→买回实例级投影(sim71 批;round/node 由
                    # 引擎补上下文,明细字段单一源 = project_sell_buyback;
                    # 空列表 = 本轮无回环,不占判读视野)
                    'sell_buyback_loops': [
                        dict(lp, round=rn, node=nodes[rn - 1])
                        for lp in _sell_buyback_loops],
                },
                # 商店波未买牌拒因串(末波 last-wins;生产端
                # cw4/shop.shop_unbought_reasons,实机 DecisionTrace.
                # shop_rejects 同键同值枚举;逐波明细=sim.shop_waves[].rejects)
                'shop_rejects': dict(_round_shop_rejects),
                'sim': {
                    'node': nodes[rn - 1], 'delta': delta,
                    # 合成执行链事件(本轮装备栏内合成的成品名;默认关恒空)
                    'syntheses': _synth_events,
                    # `w193_p2sim/`/ADR-0377:参数化胜率披露(校准层结算行;
                    # None=非校准路径[P1 段/uncalibrated 臂/reward 类])
                    'p2_win_p': _p2_wp,
                    'gold_before': _gold_before,
                    'income': _inc, 'spend': _spend,
                    'depth': _depth,
                    # core_count 语义=core_routed(core_count_for 按
                    # target 路由;known-line-no-core=None)。**此前的
                    # 账本批次是旧三人组口径,聚合端按 ledger_semantics
                    # 过滤**(manifest 键;审查#2:口径混桶=③ 噪声)
                    # ADR-0336:target 用 v3 意向名(旧 v1 字段已删)
                    'core_count': core_count_for(
                        _target_comp_label(sess),
                        {d.char_id for d in (st.deployed or [])
                         if getattr(d, 'char_id', '')}),
                    # deployed 代理名单(审查#5:tiers sim 行可渲染
                    # 角色构成——比只有计数信息量高一档)
                    'deployed': [d.char_id for d in (st.deployed or [])
                                 if getattr(d, 'char_id', '')],
                    'shop_waves': _waves,
                    'dir_established': (res.dir_round <= rn if st.plane == 1
                                        else res.dir_round < 99),
                    'segments': _segs_used,
                    # ADR-0276:本轮 3合1 合并次数(单位守恒/席位判读输入)
                    'merges': _merges,
                    # ADR-0283(批⑰ F6)+ `w566_sim_guard/` 语义收窄:本轮满栏**非合成**
                    # 被拒的买次数(合成买已按 merge_buy_completes 执行,
                    # 不计入;0=常态;>0 = 决策层在满栏态想买不合成牌,
                    # 判读买门时须知)
                    'bench_full_skipped_buys': _bench_full_skips,
                    # ADR-0285(批㉑ F3/F5):非合成拒买折算金(净滞留口径
                    # = 末金 − 本值;判读区分「策略滞留」vs「守卫拦截」)
                    'bench_full_skipped_gold': _bench_full_skip_gold,
                    # ADR-0284(批㉒ F1):本轮幻影再买提案数(已消费槽/
                    # 店外;真策略批次应恒 0,检查项归 0 锁)
                    'phantom_rebuys': _phantom_rebuys,
                    # 满级 LevelUp 拒付次数(执行层 cap 守卫;>0 = 决策层
                    # 满级后仍发升级——防线拦金,策略病由本计数暴露)
                    'level_cap_rejects': _lv_cap_rejects,
                    # M-A 定向刷新本轮执行数(轮末差值归因;刷帽检查
                    # directed_refresh_game_cap_lock / refresh_roll_cap_
                    # frame 的普通车道扣除项。其余车道:release/E2 臂
                    # 预算另有界,计入普通车道口径——检查事件供归因)
                    'dir_refreshes': max(
                        0, int(getattr(strategy_state_of(sess), 'v3_dir_refresh_used', 0) or 0)
                        - _dir_used0),
                    # 血预算停手·停升级拒付次数(决策层;设计件 12/
                    # ADR-0448):hp≤停升级线帧被门拦下的升级事件数
                    # (>0 = 本语义在该轮生效;决策侧判读输入)
                    'blood_budget_levelup_rejects': max(
                        0, getattr(strategy_state_of(sess), 'v3_blood_budget_rejects', 0)
                        - _bb_rejects_before),
                    # 血预算停手·搜索型刷新停付拒付次数(决策层;设计件
                    # 12 §2.3-P1-c/§3.2/ADR-0451):血预算不足帧被门拦下
                    # 的刷新事件数(>0 = 本语义在该轮生效;急救型/ALL IN
                    # 豁免帧不计)
                    'blood_budget_refresh_rejects': max(
                        0, getattr(strategy_state_of(sess), 'v3_blood_budget_refresh_rejects', 0)
                        - _bb_refresh_rejects_before),
                    # ADR-0287(批㉘ F1)+迁移审计 w652(git 历史) §5 处置①:重放围栏(部署前
                    # 快照语境冻结)的残留可上件数(行动语境下围栏认可件
                    # 未上;检查项 deploy_after_buy_semantics /
                    # ledger_deploy_lag_disclosure 的数据源)
                    'deploy_lag_units': _deploy_lag_units,
                    # 迁移审计 w716(git 历史) F1 修复:skip 轮残余补部署披露
                    # (上几件;residual_held 恒 0——保留集投影已随 v3_hoard
                    # 通道退役删除,字段保留仅为账本 schema 兼容;非 skip 轮
                    # 恒 0——补部署只在 skip 分支。T3 修复批 sim 建模缺口
                    # 申报见 _residual_fill_deploy docstring:上板转化率
                    # sim 只可部分测,验收口径=净转化,禁触发计数冒充)
                    'residual_deployed': _res_up,
                    'residual_held': _res_held,
                    # T3 同轮保留集轮末未销账保护名数(对账面:与 t3_buy/
                    # fuel_filler_stall_buy 触发数、residual_deployed 上板
                    # 数三方对读;>0 = 垫件仍持有待转化,非异常)
                    'stall_buys_pending': len(
                        getattr(strategy_state_of(sess), 'cw4_fuel_filler_stall_buys', None)
                        or ()),
                    # 动作 v2(契约包 C1):本轮围栏是否被显式动作跳过
                    # (skip_fence 账本行的 sim 侧披露;checks 配对锁数据源)
                    'fence_skipped': _explicit_deploy_seen,
                    # 迁移审计 w52(git 历史)(ADR-0326):本轮补偿趟是否放弃(0/1;连续放弃轮
                    # ≥3 由检查项 decision_v2_remedy_loop 报警——设计容量
                    # 不足信号)
                    'remedy_abandoned': 1 if getattr(
                        strategy_state_of(sess), 'v3_remedy_abandoned', 0)
                        > _remedy_abandons_before else 0,
                    # ===== `w614_sim_fidelity/` 保真三补:记账出口(纯观测)=====
                    # 未穿滞留件数/生锈暴露(词条语义 cw_comps.RUST_AFFIX_NAME:
                    # 每件未穿装备敌伤+3%,最多 10 件;「生锈泄洪」=穿戴/合成
                    # 使 rust_units 下降的轮,配 sim.refresh_xp 旁的计数读)
                    'unworn_equips': len(st.equips),
                    'rust_units': min(10, len(st.equips)),
                    'worn_equips_total': sum(
                        len(getattr(u, 'equips', ()) or ())
                        for u in (*iter_occupied_deployed(st.deployed),
                                  *iter_occupied(st.bench))),
                    # 付费刷新产经验(xp_per_refresh;免费刷不计)
                    'refresh_xp': _refresh_xp_round,
                    # 上阵代理(G2):配方件躺 bench 数 / 上阵战力贡献
                    'bench_recipe_pieces': _bench_recipe,
                    'deployed_power': _dep_power,
                    # ADR-0474 分配器遥测键(消费 = 锁#11 D2 接管可观测
                    # 性/D2 开臂验收;W797 不可测项「分配器是否接管不可
                    # 观测,只能金账反推」的收口):frame = 轮终帧分配器
                    # 帧位披露(active/domain/reason/proposals/chosen/
                    # alloc_gold;strategy.decide_prep 每帧写
                    # strategy_state_of(session).v3_alloc_frame);None = 本轮无决策段。
                    'alloc_frame': _round_alloc_frame,
                    'alloc_active_any': _round_alloc_active_any,
                    # T-155 基线臂:本轮选卡判据归因(kind/options/picked/
                    # reason;env 条挂 P1 r1 行)。None = 本轮无基线臂选卡
                    # (freq 臂/固定剧本/未开注入恒 None——注入无判据归因)
                    'invest_picks': (_round_pick_recs
                                     if _round_pick_recs else None),
                },
            })
            # P1 段生锈暴露峰值(采样点 = 账本行 rust_units 键同点:峰值 ≡
            # 逐轮行值最大值,由构造保证)。原采样点在轮中部 power 块
            # (部署后/结算+分配器前),与行键是两个观测时点——轮中段
            # 卖出回充装备(T-169 执行面:victim 带装回收)再被分配器
            # 穿戴时,两读数分叉(峰值≠行值最大);T-169 锁红重推后移点
            # 收口,勘误说明留在 power 块注释。
            if _seg_plane == 1:
                _rust_peak = max(_rust_peak, min(10, len(st.equips)))
            if st.hp <= 0:
                break
        # `w213_sim_supply/`/ADR-0394:P1 段出口 key_equips 命中度量段末快照
        # (无论 P1 段是打满还是中途死亡都记;口径见 SimResult
        # 字段注释)。段内变量 _seg_plane 在此可见(for 循环变量)。
        if _seg_plane == 1:
            # `w614_sim_fidelity/` G1:P1 出口滞留件数(段末 owned 池快照;实机出口
            # 「滞留件数」的 sim 对应物,段内死亡也记)
            res.p1_unworn_exit = len(st.equips)
            res.p1_rust_units_peak = _rust_peak
            _tc = getattr(strategy_state_of(sess), 'target_comp', None)
            _keys = (list(getattr(_tc, 'key_equips', ()) or ())
                     if _tc is not None else [])
            _have: dict[str, int] = {}
            for _e in (*[e for d in (st.deployed or [])
                         for e in (getattr(d, 'equips', ()) or ())],
                       *st.equips):
                _have[_e] = _have.get(_e, 0) + 1
            _need: dict[str, int] = {}
            for _k in _keys:
                _need[_k] = _need.get(_k, 0) + 1
            # 口径与 `w212_sim_equip/` 批 A 一致:命中 = Σ min(需求份数, 持有份数)
            # / 需求总份数(key 表可含重复份数)
            res.p1_key_hit_total = sum(_need.values())
            res.p1_key_hit_hits = sum(
                min(_n, _have.get(_k, 0)) for _k, _n in _need.items())
        # ADR-0362:位面段间死亡即终局(P1 段死=不进 P2,P2 段死=止)
        if st.hp <= 0:
            break
    res.p2_hp0 = res.p2_entered and st.hp <= 0
    res.final_hp = st.hp
    res.level = st.level
    # `w614_sim_fidelity/` 保真三补:局级记账出口汇总(纯观测)
    res.equip_grants = _equip_grants
    res.equip_wears = _equip_wears
    res.equip_syntheses = _equip_syntheses
    res.refresh_xp_total = _refresh_xp_total
    res.p1_bench_recipe_piece_rounds = _bench_recipe_rounds_p1
    res.p1_deployed_power_avg = (
        round(_dep_power_sum_p1 / _dep_power_rounds_p1, 2)
        if _dep_power_rounds_p1 else 0.0)
    # `w193_p2sim/`/ADR-0377:P2 判读同构观测(headline/账本扩展)——由账本
    # plane=2 行派生(金带走量/carry 笔数价格带/意向切换/lv 到达轮)。
    if res.p2_entered:
        res.p2_combat_calibrated = _p2c.calibrated
        # `w224_handoff/`/ADR-0399:承接快照披露(策略 decide_prep 位面首帧块写
        # strategy_state_of(session).v3_handoff——案 b 臂同样经首轮 decide_prep 采样)。
        _h = getattr(strategy_state_of(sess), 'v3_handoff', None)
        res.p2_handoff = _h.as_dict() if _h is not None else None
        _p2_rows = [row for row in res.ledger
                    if (row.get('plane') or 1) == 2]
        if res.p2_hp0:
            # 金带走量:死在 P2 段时的末金(活过 P2=None——`w183_carry/` D1)
            _g = _p2_rows[-1].get('gold') if _p2_rows else None
            res.p2_gold_carried = _g if isinstance(_g, int) else None
        _buys: dict[str, int] = {'1-2': 0, '3': 0, '4-5': 0}
        _prev_tgt = ''
        for row in _p2_rows:
            for _a in row.get('actions') or ():
                if _a.get('__type__') != 'BuyCard':
                    continue
                _c = ((_a.get('card') or {}).get('cost')) or 0
                _k = '1-2' if _c <= 2 else ('3' if _c == 3 else '4-5')
                _buys[_k] = _buys.get(_k, 0) + 1
            _tgt = row.get('target_comp') or ''
            if _prev_tgt and _tgt and _tgt != _prev_tgt:
                res.p2_switch_events.append(
                    (int(row.get('round_num') or 0), _prev_tgt, _tgt))
            if _tgt:
                _prev_tgt = _tgt
            _lv = int((row.get('state') or {}).get('level') or 0)
            if _lv >= 6 and res.p2_lv6_round is None:
                res.p2_lv6_round = int(row.get('round_num') or 0)
            if _lv >= 7 and res.p2_lv7_round is None:
                res.p2_lv7_round = int(row.get('round_num') or 0)
        res.p2_buys_by_cost = _buys
    # ADR-0336:locked_line/bridge_id 字段保留(输出结构兼容),
    # 赋值取 v3 意向锁定名(v1 线库字段已删;无锁定=None)
    res.locked_line = _target_comp_label(sess) or None
    res.bridge_id = None
    # ADR-0284:单局披露(幻影再买/池地板;真批次双 0)
    res.phantom_rebuys = sum(
        (row.get('sim') or {}).get('phantom_rebuys', 0)
        for row in res.ledger)
    res.pool_floor_hits = cards_pool.floor_hits
    if _inv is not None or _sink is not None:
        # `w162_inject/`/ADR-0364:注入观测(实际持有序 = session 真值,含去重)。
        # env/持有序统一读 session 写点后的真值——freq 臂(开局/日程直写)
        # 与基线臂(裁决后写)语义同源,单读点免双臂分叉
        res.invest_env = str(getattr(sess, 'active_env', '') or '')
        res.invest_strategies = tuple(sess.active_strategies)
    if _sink is not None:
        # T-155 基线臂:选卡判据归因全集(env + 逐策略槽;reason =
        # decide_event 归因串透传,判读/统计入口)
        res.invest_picks = tuple(_inv_picks)
    return res


