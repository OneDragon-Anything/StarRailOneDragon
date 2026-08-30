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
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.decision.cw_strategy import StrategySession

# 血预算停手·终止分支账本决策位(设计 迁移审计 w659(git 历史) v2 §5.1 R4;ADR-0469)——
# 账本行 'terminal_release' 键的单一记账址。discipline 模块级无 cw_sim
# 环(scoring→cw_sim 只在函数体内延迟 import),模块级引入安全。
from sr_od.application.currency_war.decision.decision_v2.discipline import (  # noqa: E402
    terminal_release_bit,
)
from sr_od.application.currency_war.kernel.cw_battle_calib import (
    _board_counts_of,
    _board_factions_of,
    _deployable_depth,
    _direction_established,
    _roll_rotation,
    _settle_rung,
    _target_comp_label,
    deployed_star_depth,
    node_delta,
    p2_combat_delta,
    sample_node_sequence,
)
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
    XP_PER_BUY,
    XP_TO_NEXT_LEVEL,
    BenchChar,
    BuyCard,
    CompTransaction,
    GameState,
    LevelUp,
    RefreshShop,
    SellBench,
    SellDeployed,
    ShopCard,
    SwapDeploy,
    _bench_char_cost,
    _merge_bench,
    bench_clear,
    bench_occupied,
    bench_place,
    deployed_occupied,
    deployed_place,
    iter_occupied,
    iter_occupied_deployed,
    merge_buy_completes,
    merge_buy_k,
    sell_refund,
)
from sr_od.application.currency_war.kernel.cw_state import (
    simulate as _simulate_state,
)
from sr_od.application.currency_war.sim.cw_sim_invest import (
    InvestInjectionState,
    SimInvestProfile,
    sample_invest_profile,
)

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
    from sr_od.application.currency_war.sim.engine_p2 import P2ReplayEntry


def _board_next_tier_of(board_factions: dict[str, int]) -> dict[str, int]:
    """板面各阵营「下档阈值」观测键(生产 ``GameState.board_next_tier``
    的 sim 同构面;语义 = 左面板 "X/Y" 的 Y)。

    判据单一源 = ``FACTIONS[].tiers``:取 >当前人数 的最小档,无更高档
    不计入(与 obs/cw_observation computed 支同一式,禁第二份推导)。
    消费方 = Δp_tier 档位分解标定批(registry.realization_delta_p_tier
    的标定前置依赖;W802 边界声明:标定批前置,不阻塞开臂)。
    """
    out: dict[str, int] = {}
    for _f, _c in board_factions.items():
        _tiers = FACTIONS[_f].tiers if _f in FACTIONS else ()
        _nt = next((t for t in _tiers if t > _c), 0)
        if _nt:
            out[_f] = _nt
    return out

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



def _residual_fill_deploy(
    st: GameState,
    sess: object,
    target_factions: frozenset[str],
    target_cores: frozenset[str],
    fw_carry: frozenset[str],
    locked_factions: frozenset[str],
) -> tuple[int, int, int]:
    """skip_fence 轮轮末残余补部署(迁移审计 w716(git 历史) F1 修复设计 §三;命题 P-F1)。

    为什么:围栏互斥(裁决1「显式>围栏,同轮互斥」)原实现是**轮级禁运**
    ——演进事务密集轮每轮必有 applied CompTransaction,换阵撤回/3合1 吞
    副本造成的板面空槽连续过夜,欠载打仗掉血(F1 病理;样本 640247
    r5-r7 缩退 6→3→2)。修法 = 把互斥辖域从「轮级」收窄到「通道级」:
    skip 轮轮末对「围栏认可 ∖ 显式保留集」执行 bench→空槽补部署。

    - 零支出零破息约束:上场动作仅 bench→空槽(pop-append),不买、不卖、
      不刷新、不 swap——金账恒等式(gold_before+inc−buys−levelup−refresh
      +income)不含本动作,任何 Δp>0 受益在 C=I=0 下严格非负(P-F1,
      docs/game/currency_war/research/proofs/p24-residual-fill-dominance.md)。
    - 显式保留集(消解互斥的本意 = 防「同一部署通道双写」):显式通道
      **刻意**留在 bench 的件,即 final 买而不上件——session 持有名单
      (v3_hoard)在 locked/forced 模式的 char_targets([21] 窗口语义:
      羁绊组齐才替换上场;P1 过渡模式(p1_pair/p1_transition/weak/
      fallback)的囤货集是买侧方向,不构成部署保留——否则 F1 修复面
      被囤货全集吞掉)。
      「与在场(deployed)同名」的素材副本由围栏 dedup(r404-A2/5.1.7
      在场唯一)自然 held,无需保留集;**bench 内同名对(无在场同名)
      不保留**——3合1 合并域是全场(bench∪deployed),部署一对之一不
      破坏合成进度,且生产 DeployBench 围栏同语义会上(首版把 bench 对
      整对保留是过宽:642763/642795 实证 dep 停滞 4/7、5/7 而检查器
      「可上货」口径(非在场同名)全数命中,即本缺失的 W748 重现根因;
      cw_plan 同名对保护辖的是卖出不是部署)。
    - 补部署候选 = select_deployments(非保留 bench,行动后 deployed/board/
      cap,目标集同围栏主趟)的 up 集;与主趟同一纯函数(单一源)。
    - 统一 lag 口径:补部署后再重放围栏(输入剔除保留集——保留件是
      「刻意不上」不是 lag),残余可上件数即 deploy_lag_units,消除
      skip 轮 lag 恒 0 的检查器失明面(设计 §四-2)。

    返回 (residual_deployed 补上场件数, residual_held 被保留集扣下的
    up 候选件数, deploy_lag_units 补部署后残余可上件数)。
    """
    from sr_od.application.currency_war.kernel import cw_deploy_logic as _dl

    # —— 保留集:final 买而不上件(locked 持有名单);素材副本交围栏
    # dedup(在场同名自然 held,见 docstring 的 W748 收窄裁决)——
    _hold_names: frozenset[str] = frozenset()
    _hoard = getattr(sess, 'v3_hoard', None)
    if _hoard is not None \
            and getattr(_hoard, 'mode', '') in ('locked', 'forced'):
        _hold_names = frozenset(
            getattr(_hoard, 'char_targets', ()) or [])

    def _reserved(bc: BenchChar) -> bool:
        if not bc.char_id:
            return False   # 未识别:围栏照旧上,保留集不管
        return bc.char_id in _hold_names

    _occ = [(i, bc) for i, bc in enumerate(st.bench) if bc is not None]
    _keep = [(i, bc) for i, bc in _occ if not _reserved(bc)]
    # residual_held = 被保留集扣下的件数(保留件不进围栏输入,故不能
    # 取 select_deployments 的 held 桶——那是围栏自身拦截,非保留集扣除)
    _res_held = len(_occ) - len(_keep)
    _res_up = 0
    # 不动点循环:每次上场改变 board/dep_fac 阵营计数后,「成对/点火」
    # 判据可能使此前 held 的件转为可上(生产 op 侧 = drag 循环逐件动态
    # 仲裁同语义)——单趟会把「先上激活成对」的件错留 bench(640442 r7
    # 取证:单趟 up=2/lag=2,循环后归零)。
    while _keep:
        _up_idx, _ = _dl.select_deployments(
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
        )
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
    # 统一 lag:补部署后残余(剔除保留集——刻意不上 ≠ 围栏认可未上)
    _lag_keep = [bc for i, bc in _occ
                 if st.bench[i] is not None and not _reserved(bc)]
    _lag = 0
    if _lag_keep:
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
        )
        _lag = len(_lag_idx)
    return _res_up, _res_held, _lag



def simulate_p1(seed: int, *, use_refresh: bool = True,
                strategy=None, session=None,
                pool: str | Path = 'auto',
                diamond_cap_prob: float = 0.0,
                config=None,
                planes: int = 1,
                invest: SimInvestProfile | bool = False,
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
    :param p2_combat: P2 战斗存活层参数族(`w193_p2sim/`/ADR-0377;None=模块
        默认 ``P2_COMBAT_DEFAULT``)。``calibrated=False`` 臂逐位回
        `w157_p2/`/ADR-0362 行为(Δ池 plane=2 优先 + 恒值回退档)——A/B
        与回退对照臂;planes=1 路径不消费本参数(零漂移)。
    :param _p2_entry: 案 b 臂进场态注入(内部参数;``simulate_p2_replay_entry``
        构造——跳过 P1 段与开局 bench 采样,直接从真值进场态跑 P2 段。
        共享本函数的 P2 段循环体 = 单一源,迁移审计 w186(git 历史) 设计 §4 的消复制形态)。
    """
    from sr_od.application.currency_war.decision.decision_v2.strategy import (
        DecisionV2Strategy,
    )
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
    strat = strategy or DecisionV2Strategy(registry=sim_decision_registry())
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
        sess = session or StrategySession()
        sess.v2_state = ('economy', False, False, 0, 0, 0, 0, 0)
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
        sess = session or StrategySession()
        sess.v2_state = ('economy', False, False, 0, 0, 0, 0, 0)
        streak = 0
        streak_signed = 0
    # hp 决策可信位对齐生产真读帧口径(sim 无识别过程 = 恒真值帧;生产
    # 真读帧两位皆 True,写入点语义 = operations/prep/shop.py `_apply_hp`
    # 真读分支。hp_readable 本就恒 True,本位对齐后 hp_decision_trusted
    # 读数不变,纯口径一致化零行为漂移)。
    st.hp_trusted = True
    # 开局帧带符号 streak 兜 0(生产备战帧 state.streak = session.last_streak,
    # 默认 0 非 None;结算逐轮覆写见下方结算段)。案 b 臂 build_state 已带。
    if st.streak is None:
        st.streak = streak_signed
    # `w162_inject/`/ADR-0364:投资注入剧本解析(独立 rng 流,默认 False 零开销)。
    # 语义位 = session(持久宿主,handler 写点单一源参照)+ state(生产
    # 由 cw_observation 每帧同步,此处注入点直写两处 = 等价语义)。
    _inv: InvestInjectionState | None = None
    if isinstance(invest, SimInvestProfile):
        _inv = InvestInjectionState.build(invest)
    elif invest:
        _inv = InvestInjectionState.build(sample_invest_profile(seed))
    if _inv is not None:
        if _inv.profile.active_env:
            sess.active_env = _inv.profile.active_env
            st.active_env = _inv.profile.active_env
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
            # 生产语义对齐:开局帧槽序表写 session(prep_director
            # 首帧写;battles_left_p2 消费,ADR-0361)
            sess.plane_node_table = list(nodes)
            # ADR-0368(迁移审计 w169(git 历史)):位面日程真值序列(生产=prep_director 每位面
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
        for rn in range(1, _seg_rounds + 1):
            _ts += 1
            st.round_num = rn
            # 批⑤ F4(ADR-0276):决策前写 session.node_type_current——
            # 生产语义 = prep_director 备战期存下一节点类型(r308 保连胜
            # 门/节点感知消费读 session);sim 旧不写 → 门在 sim 恒盲
            # (300 局「地板降 5」0 次)。词表与 sim nodes 同源
            # (battle/encounter/boss/…)。
            sess.node_type_current = nodes[rn - 1]
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
            _inc = {'base': (REWARD_BASE_GOLD_BY_ROUND.get(rn, BASE_INCOME)
                             if _node == 'reward' else BASE_INCOME),
                    'interest': min(_icap, st.gold // 10),
                    'streak': _streak_amt,
                    'event': _inc_event}
            if _agg_inv is not None and _agg_inv.gold_per_node:
                _inc['invest'] = _agg_inv.gold_per_node
            st.gold += sum(_inc.values())
            # `w162_inject/`/ADR-0364:本轮策略选卡注入(overlay 在备战期出现 → 收入
            # 结算后、决策前;实机写点 = handle_invest_strategy 的 session
            # append+去重)。instant_gold 在选卡时点入账(生产游戏引擎同点)。
            # 免费刷额度在选卡后按当前持卡聚合重算(当轮选的卡当轮生效)。
            if _inv is not None:
                _pk = _inv.picks_by_key.get((_seg_plane, rn))
                if _pk is not None and _pk not in sess.active_strategies:
                    sess.active_strategies.append(_pk)
                    st.active_strategies = list(sess.active_strategies)
                    st.gold += economy_effect_of(_pk).instant_gold
            _free_r = (_agg_inv.free_refresh_per_node
                       if _agg_inv is not None else 0)
            if _inv is not None:
                # 注入局:免费刷额度按**选卡后**持卡重算(当轮选的卡当轮生效)
                _free_r = (aggregate_economy(st.active_strategies)
                           .free_refresh_per_node
                           if st.active_strategies else 0)
            _free_used = 0
            # ADR-0286(批㉓ F4):轮岗事件——每备战期掷一次,翻倍档概率表
            # 写 st.refresh_probs(生产「概率条 OCR 真值」同态;未掷中 = None
            # 退基线表),draw_shop(开态+每次刷新)消费轮岗后表。
            st.refresh_probs = _roll_rotation(rng, st.level)
            # ADR-0286(迁移审计批 F4):宝钻通道(默认 prob=0 不掷,保 baseline 可配对)
            if diamond_cap_prob > 0 and rng.random() < diamond_cap_prob:
                _diamonds += 1
            # cap 真值 = level + 宝钻数(生产 read_deploy_cap 语义);无宝钻 None
            # → max_units() 兜底 level(与生产防抖拒信路径同态)
            st.deploy_cap = st.level + _diamonds if _diamonds else None
            st.shop = cards_pool.draw_shop(st.level, probs=st.refresh_probs)
            _waves = [{'event': 'offer', 'gold': st.gold,
                       'cards': [{'name': c.name, 'faction': c.faction,
                                  'cost': c.cost} for c in st.shop]}
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
            _dir_used0 = int(getattr(sess, 'v3_dir_refresh_used', 0) or 0)
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
            #   PREREG 兑现链 v3 判读;生产读端 merge_round_rows 按
            #   state.bench_full_flag 消费,sim 侧自此有真值源——W797
            #   不可测项「恒 null」的 sim 收口)。轮内 OR 聚合(生产
            #   merge 同式:「任一决策帧满栏」;bench 在轮内买入段才
            #   填满,轮入口快照会系统性漏亮)。sim 满观测无 OCR 缺读,
            #   恒 bool(生产 bool|None 的 None 态在 sim 不存在)。
            _round_bench_full = False
            # - board_next_tier:各阵营下档阈值(消费 = Δp_tier 档位分解
            #   标定批,registry.realization_delta_p_tier 标定前置)。
            _round_board_next_tier = _board_next_tier_of(
                _board_factions_of(st.deployed))
            # - ADR-0474 分配器遥测键(消费 = 锁#11 D2 接管可观测性):
            #   alloc_frame = 本轮最后一段 decide_prep 的分配器帧位
            #   (session.v3_alloc_frame 每段覆写,末值 = 轮终帧披露;
            #   此前该帧位无任何落盘消费面);alloc_active_any = 轮内
            #   任一段接管过(OR 聚合,与 formed_stop 同式)。
            _round_alloc_frame = None
            _round_alloc_active_any = False
            # - p1_downgrade_active:末窗支出降格触发面(discipline.
            #   p1_directed_downgrade_active;session=None 裸评估=遥测
            #   观测面用法,不置位面内闩——禁观测改变决策状态)。
            #   消费 = W797 不可测项 A5(停付/降格机制零触发样本)的
            #   sim 触发面对账源。
            from sr_od.application.currency_war.decision.decision_v2.discipline import (
                p1_directed_downgrade_active,
            )
            _round_p1_downgrade = p1_directed_downgrade_active(
                st, _obs_registry)
            # `w227_handoff_gate/`/ADR-0400:P1 末窗承接门缺口观测(轮入口首段快照;
            # formed_stop 承接维/EV 缺口项的判读数据面)
            _round_handoff_gap = 0
            # 迁移审计 w238(git 历史)/ADR-0403:boss 投影 hp 披露(None=投影关/非末窗)
            _round_handoff_hp_proj = None
            # 迁移审计 w52(git 历史)(ADR-0326):本轮补偿放弃信号快照——决策段后对比计数增量,
            # 进账本 sim.remedy_abandoned(检查项 decision_v2_remedy_loop
            # 的「连续放弃轮」数据源)
            _remedy_abandons_before = getattr(sess, 'v3_remedy_abandoned', 0)
            # 血预算停手拒付计数轮前快照(设计件 12/ADR-0448):决策段后
            # 差分进账本 sim.blood_budget_levelup_rejects(与
            # remedy_abandoned 同式的轮级差分披露)
            _bb_rejects_before = getattr(sess, 'v3_blood_budget_rejects', 0)
            # 血预算停手·搜索型刷新停付拒付计数轮前快照(设计件 12
            # §2.3-P1-c/§3.2/ADR-0451):决策段后差分进账本
            # sim.blood_budget_refresh_rejects(同式轮级差分披露)
            _bb_refresh_rejects_before = getattr(
                sess, 'v3_blood_budget_refresh_rejects', 0)
            # 迁移审计 w114(git 历史)/ADR-0346 相位影子观测:轮入口(首决策段)快照——与生产
            # 「每轮决策入口计算一次」对齐;一轮多决策段时取首段(轮初态)。
            _round_phase: str = ''
            _round_form_ok: bool = False
            _round_form_score: float = 0.0
            _round_dp_posture: str = ''
            _round_reserve_cap = 0
            _round_reserve_overflow = 0
            _round_release_budget = 0
            _round_release_reason = ''
            _phase_snap = False
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
            # 从轮首移到**买/升级之后**(生产序对齐:battle_prep.py 备战
            # 单轮 ⓪收球→①买牌→②部署→③装备→④出战)。旧轮首序让当轮
            # 买的件/当轮升级腾出的 cap 滞后一轮上板(n=300 观测 33.0%
            # 轮存在「当轮可上未上」,1124 件次),结算键(rung/depth)读
            # 滞后一档的 deployed(boss 轮 53.6% 结算键滞后)。部署块
            # 本体在轮末升级后执行(见下方「②部署」),目标集也在彼处
            # 从 session 现读(生产语义:买后 update_target 已刷新)。
            for _seg in range(8):
                # 满栏旗标逐决策段 OR(生产「任一帧置 1」同式;取段入口
                # 值=该段 decide_prep 的决策语境)
                _round_bench_full = _round_bench_full or (
                    bench_occupied(st.bench) >= BENCH_CAPACITY)
                strat.update_target(st, sess, config)
                acts = strat.decide_prep(st, sess, config)
                _round_formed_stop = _round_formed_stop or bool(
                    getattr(sess, 'v3_formed_stop', False))
                # ADR-0474 分配器帧位轮内采集(每段 decide_prep 覆写
                # session.v3_alloc_frame,这里逐段留末值 + OR 聚合)
                _af = getattr(sess, 'v3_alloc_frame', None)
                if _af is not None:
                    _round_alloc_frame = _af
                    _round_alloc_active_any = (_round_alloc_active_any
                                               or bool(_af.get('active')))
                if not _phase_snap:
                    _phase_snap = True   # 轮入口首段快照(迁移审计 w114(git 历史) 影子)
                    _round_phase = str(getattr(sess, 'v3_phase', '') or '')
                    _round_form_ok = bool(getattr(sess, 'v3_form_ok', False))
                    _round_form_score = round(float(
                        getattr(sess, 'v3_form_score', 0.0) or 0.0), 3)
                    # 迁移审计 w119(git 历史)/ADR-0347 授权依据 trace:当轮 DP 姿态 tag
                    _round_dp_posture = str(getattr(getattr(
                        getattr(sess, 'v3_dp_posture', None),
                        'posture', None), 'tag', '') or '')
                    # `w611_econ_cycle/` 储备/义务披露(轮入口快照;与生产 decisions 行
                    # sess_* 同语义,义务帧兑现率/闲置金判读的 sim 侧源)
                    _round_reserve_cap = int(
                        getattr(sess, 'v3_reserve_cap', 0) or 0)
                    _round_reserve_overflow = int(
                        getattr(sess, 'v3_reserve_overflow', 0) or 0)
                    _round_release_budget = int(
                        getattr(sess, 'v3_release_budget', 0) or 0)
                    _round_release_reason = str(
                        getattr(sess, 'v3_release_reason', '') or '')
                    # ADR-0348 ↺:扑满节点识别标记(遥测数据面)
                    _round_piggy = bool(getattr(sess, 'v3_piggy_reward',
                                                False))
                    # `w227_handoff_gate/`/ADR-0400:承接门缺口(filters.formed_stop_
                    # active 写;轮入口快照,判读「门扣住哪些轮」)
                    _round_handoff_gap = int(
                        getattr(sess, 'v3_handoff_gap', 0) or 0)
                    # 迁移审计 w238(git 历史)/ADR-0403:boss 投影 hp 同点快照(投影开时非 None)
                    _round_handoff_hp_proj = getattr(
                        sess, 'v3_handoff_hp_proj', None)
                if not use_refresh:
                    acts = [a for a in acts
                            if not isinstance(a, RefreshShop)]
                if not acts:
                    break
                _segs_used += 1
                progressed = False
                for a in acts:
                    if isinstance(a, RefreshShop):
                        res.refreshes += 1
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
                        _acts.append({'__type__': 'RefreshShop', 'cost': _cost_r})
                        st.shop = cards_pool.draw_shop(st.level,
                                                       probs=st.refresh_probs)
                        _waves.append(
                            {'event': 'refresh', 'gold': st.gold,
                             'cards': [{'name': c.name, 'faction': c.faction,
                                        'cost': c.cost} for c in st.shop]})
                        progressed = True
                        break          # 刷后立即 re-decide(见新店)
                    if isinstance(a, BuyCard):
                        # ADR-0283(批⑰ F6)满栏守卫 + sim 解冻(ADR-0453
                        # 影响节兑现):满栏不再一律拒——与生产 simulate
                        # (cw_state.simulate BuyCard 满栏分支,`w544_fullbench_mergebuy/`)同源:
                        # merge_buy_completes 判「本次点击完成一次合成」
                        # → 执行满栏合成买(k = merge_buy_k 张一次买入,
                        # 金 k×单价全款,店 k 张同身份牌下架,合成链
                        # _merge_bench 照走;merge_mechanics.md §2.5
                        # 自动多买)。不满足合成仍拒(ADR-0283 兜底语义
                        # 保留);bench_full_skipped_* 计数语义收窄为
                        # 「非合成拒买」——合成买已执行,计入 skipped
                        # 会让拦截指标说谎。
                        if bench_occupied(st.bench) >= BENCH_CAPACITY:
                            _mb_star = a.card.star or 1
                            if not merge_buy_completes(
                                    a.card.name, _mb_star, st.bench,
                                    st.deployed, st.shop):
                                _bench_full_skips += 1
                                _bench_full_skip_gold += a.card.cost
                                continue
                            _mb_k = max(1, merge_buy_k(
                                a.card.name, _mb_star, st.bench,
                                st.deployed, st.shop))
                            st.gold -= a.card.cost * _mb_k
                            _ch = a.reason or 'unknown'
                            _spend['buys'][_ch] = \
                                _spend['buys'].get(_ch, 0) \
                                + a.card.cost * _mb_k
                            for _ in range(_mb_k):
                                cards_pool.take(a.card.name)
                            # 店 k 张同身份牌下架(生产语义:槽买后消失,
                            # ADR-0284;不清槽会让 merge_buy_k 的 in_shop
                            # 计数虚高 → 同槽幻影再买)
                            _mb_left = _mb_k
                            _mb_kept: list[ShopCard] = []
                            for _c in st.shop:
                                if _mb_left > 0 and _c.name == a.card.name \
                                        and (_c.star or 1) == _mb_star:
                                    _mb_left -= 1
                                    continue
                                _mb_kept.append(_c)
                            st.shop = _mb_kept
                            # 序列化形状对齐生产 serialize_action(card 嵌套;
                            # 视图读 a['card']['cost'],平铺会让 economy 算 0)。
                            # reason=**通道**(创建点语义);channel=**身份**
                            # (classify_buy);count=自动多买张数(判读 k>1
                            # 生效面的纯增列,既有消费方不读该键)。
                            from sr_od.application.currency_war.kernel.cw_line_defs import (
                                classify_buy as _cb,
                            )
                            _acts.append({'__type__': 'BuyCard',
                                          'card': {'x': a.card.x,
                                                   'faction': a.card.faction,
                                                   'name': a.card.name,
                                                   'cost': a.card.cost},
                                          'reason': _ch,
                                          'channel': _cb(a.card, st),
                                          'count': _mb_k})
                            # ADR-0129 购买经验单击模型:一次点击 +XP_PER_BUY
                            # (k 张自动多买仍是一次点击,不加倍)
                            xp += XP_PER_BUY
                            st.xp_progress = (xp, XP_TO_NEXT_LEVEL.get(st.level, 4))
                            _pre_units = (bench_occupied(st.bench)
                                          + deployed_occupied(st.deployed))
                            # 执行序与生产同源(cw_state.simulate 满栏分支):
                            # k 张临时挂 bench 尾参与全场 _merge_bench;
                            # own+k ≡ 0 (mod 3) → 合成恰耗尽本次 k 张,
                            # 截回定长 9。已知边:own=0 且 k=3 非链式时合成
                            # 载体落尾槽、截断即丢——生产 simulate 同序同语义
                            # (§2.5 满栏合成落点置信低),实机对账实证后两处同改。
                            for _ in range(_mb_k):
                                st.bench.append(BenchChar(
                                    slot=0, char_id=a.card.name,
                                    faction=a.card.faction, star=_mb_star))
                            _merge_bench(st.bench, st.deployed)
                            del st.bench[BENCH_CAPACITY:]
                            # 合并次数按单位消减推算(每次合并净减 2 个单位;
                            # 消费 3 产 1,链式多级同式)
                            _merges += (_pre_units + _mb_k
                                        - bench_occupied(st.bench)
                                        - deployed_occupied(st.deployed)) // 2
                            progressed = True
                            continue
                        # ADR-0284(批㉒ F1,最大杠杆):商店槽消费语义
                        # ——买走即下架(生产语义:槽买后消失)。旧 sim
                        # 买入不消费槽 → 同槽幻影再买(批㉒ 账本实测
                        # 65.13% 买轮含槽再买、单槽最高 6 连买),3合1
                        # 被同槽重复点击无限兜底 → 成型类指标系统性
                        # 偏乐观(批㉒ F3)。槽匹配:引用同一 → 同名
                        # 兜底(策略构造副本形态);无槽且本轮曾上架
                        # 该名 = 已消费槽再买 → 跳过(金/池不消费)+
                        # 披露;本轮从未上架 = 店外构造(测试桩)→
                        # legacy 执行 + 披露计数(真策略提案恒来自
                        # st.shop,检查项 phantom_rebuy_disclosure 锁
                        # 真批次恒 0)。
                        _slot = next((c for c in st.shop if c is a.card),
                                     None)
                        if _slot is None:
                            _slot = next(
                                (c for c in st.shop
                                 if c.name == a.card.name), None)
                        if _slot is not None:
                            st.shop.remove(_slot)
                        else:
                            _phantom_rebuys += 1
                            _offered = {c.get('name') for w in _waves
                                        for c in w.get('cards') or []}
                            if a.card.name in _offered:
                                continue   # 已消费槽再买:不可执行
                        cards_pool.take(a.card.name)
                        st.gold -= a.card.cost
                        _ch = a.reason or 'unknown'
                        _spend['buys'][_ch] = \
                            _spend['buys'].get(_ch, 0) + a.card.cost
                        # 序列化形状对齐生产 serialize_action(card 嵌套;
                        # 视图读 a['card']['cost'],平铺会让 economy 算 0)。
                        # reason=**通道**(创建点语义);channel=**身份**
                        # (classify_buy——通道经济分析别混桶,审查#7)
                        from sr_od.application.currency_war.kernel.cw_line_defs import (
                            classify_buy as _cb,
                        )
                        _acts.append({'__type__': 'BuyCard',
                                      'card': {'x': a.card.x,
                                               'faction': a.card.faction,
                                               'name': a.card.name,
                                               'cost': a.card.cost},
                                      'reason': _ch,
                                      'channel': _cb(a.card, st)})
                        xp += XP_PER_BUY
                        st.xp_progress = (xp, XP_TO_NEXT_LEVEL.get(st.level, 4))
                        # ADR-0276(批⑩最大杠杆):3合1 merge 接入 sim
                        # 执行层——生产 simulate(BuyCard) 每次买入后调
                        # _merge_bench(全场域 bench+deployed,同名同星
                        # ≥3 → star+1、删 2 张),sim 旧不接 → 副本占席
                        # → bench 满 → 买通道死 → 滞留金 2.2× 虚高
                        # (批⑩ F3/F4/F5 同根)。合并次数按单位消减推算
                        # (每次合并净减 2 个单位;载体在场时 deployed
                        # 计数不变)。
                        _pre_units = (bench_occupied(st.bench)
                                      + deployed_occupied(st.deployed))   # ADR-0392
                        bench_place(st.bench, BenchChar(
                            slot=0, char_id=a.card.name,
                            faction=a.card.faction))
                        _merge_bench(st.bench, st.deployed)
                        _merges += (_pre_units + 1
                                    - bench_occupied(st.bench)
                                    - deployed_occupied(st.deployed)) // 2
                        progressed = True
                    elif isinstance(a, LevelUp):
                        # cap 守卫:level >= LEVEL_CAP 时 LevelUp 拒付
                        # (不扣金/不进 XP),账本记 LevelUpRejected 行
                        # (不占 LevelUp 类型行:flat4 台账锁判据 =
                        # spend.levelup == 4 × LevelUp 行数,拒付行混入会
                        # 误报),计数进 sim.level_cap_rejects 披露。
                        # 已知语义分歧:实机 lv10 才禁用购买经验,lv9 是
                        # 正常付费档,本守卫在 lv9 拒付与实机方向相反;
                        # 不静默,靠 level_cap_rejects 披露,放开归
                        # LEVEL_CAP 注释所载行为变更批。
                        if st.level >= LEVEL_CAP:
                            _lv_cap_rejects += 1
                            _acts.append({'__type__': 'LevelUpRejected',
                                          'reason': 'level_cap',
                                          'level': st.level})
                            continue
                        st.gold -= 4
                        _spend['levelup'] += 4
                        # auth=授权依据观测(ADR-0354):LevelUp.auth_basis
                        # 放行臂名(pop_slot/dp/static_ev;''=default 栈旧调用
                        # 或未过账)——检查器 levelup_interest_engine_gate
                        # 判据消费;记录非指令。
                        _lv_auth = getattr(a, 'auth_basis', '')
                        _acts.append({'__type__': 'LevelUp', 'cost': 4,
                                      'auth': _lv_auth})
                        xp += XP_PER_BUY   # 与买牌同源(ADR-0286 xp 真值化;值=4)
                        st.xp_progress = (xp, XP_TO_NEXT_LEVEL.get(st.level, 4))
                        progressed = True
                    elif isinstance(a, SellBench):
                        # ADR-0316:槽位置 None(占用校验在 bench_clear)
                        bc = bench_clear(st.bench, a.bench_idx)
                        if bc is not None:
                            ch = CHARACTERS.get(bc.char_id)
                            # ADR-0276:卖出回金接生产 sell_refund 单一源
                            # ——merge 落地后 bench 可有 star≥2(1星=cost、
                            # 2星=3×cost−1…),旧恒按 1星 cost 退会低估
                            # 合成件价值、卖出通道失真。
                            _sell_v = (sell_refund(bc.star, ch.cost)
                                       if ch and ch.cost else 1)
                            st.gold += _sell_v
                            _spend['sell_income'] += _sell_v
                            _acts.append({'__type__': 'SellBench',
                                          'bench_idx': a.bench_idx,
                                          'name': bc.char_id,
                                          'income': _sell_v})
                            cards_pool.ret(bc.char_id)
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
                if not progressed:
                    break
            while (st.level < LEVEL_CAP
                   and xp >= XP_TO_NEXT_LEVEL.get(st.level, 999)):
                xp -= XP_TO_NEXT_LEVEL[st.level]
                st.level += 1
            # ADR-0286:轮末升级后 xp_progress 同步清零结转(生产 XP 条语义)
            st.xp_progress = (xp, XP_TO_NEXT_LEVEL.get(st.level, xp or 4))
            # ②部署(ADR-0287,批㉘ F1-F5):买/升级**之后**执行(生产序
            # 对齐)。r390 起 deployed 代理 = deploy_bench 真实围栏逻辑
            # (cw_deploy_logic.select_deployments 纯函数,与 DeployBench op
            # 同一源)——r373/r387 类执行层 bug sim 可发现。target 集从
            # session **买后**现读(生产:买牌段 update_target 已刷新,
            # 锁线轮目标已更新);未识别(char_id 空)照旧上,与 op 一致。
            from sr_od.application.currency_war.kernel import cw_deploy_logic as _dl
            _tf, _tc, _fw = frozenset(), frozenset(), frozenset()
            # `w155_evolve_lock/`/ADR-0360 件4:锁定帧体系键并入围栏放行集(同生产 op 侧)
            _lf = frozenset()
            try:
                _tc = frozenset(getattr(sess, 'target_comp', None).core_chars
                                or ()) if getattr(sess, 'target_comp', None) else frozenset()
                _tf = frozenset(getattr(sess, 'target_comp', None).factions
                                or ()) if getattr(sess, 'target_comp', None) else frozenset()
                _fw_name = getattr(sess, 'transition_framework', '') or ''
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
                _lf = _lfs(getattr(sess, 'v3_intention', None)) or frozenset()
            except Exception:   # noqa: BLE001  代理 best-effort
                pass
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
                _res_up, _res_held, _deploy_lag_units = \
                    _residual_fill_deploy(st, sess, _tf, _tc, _fw, _lf)
                _acts.append({
                    '__type__': 'skip_fence',
                    'reason': ('explicit_action_v2+residual_fill'
                               if _res_up else 'explicit_action_v2'),
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
                )
                _deploy_lag_units = len(_lag_idx)
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
                _rust_peak = max(_rust_peak, min(10, len(st.equips)))
            if res.dir_round == 99 and _direction_established(sess):
                res.dir_round = rn
            # `w162_inject/`/ADR-0364:P1 段锁定轮计数(①资格通道激活直证——
            # 注入前语料下 P1 恒 unlocked/p1_pair,此键恒 0[`w161_refresh/`])
            if (_seg_plane == 1
                    and getattr(sess, 'v3_intention', None) is not None
                    and getattr(sess.v3_intention, 'phase', '') == 'locked'):
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
            # = 结算「连胜×N」写 session(策略层 on_round_end 观测段),
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
            # EquipAll 同源)分配给 deployed → 账本 equipped 字段。
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
                    _pick = decide_supply(_opts, st, sess.target_comp, None,
                                          refresh_used=sess._supply_refresh_used)
                    if _pick.refresh and not sess._supply_refresh_used:
                        sess._supply_refresh_used = True
                        _opts = _sample_supply_opts(_basic_names)
                        _pick = decide_supply(_opts, st, sess.target_comp, None,
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
            _ist = getattr(sess, 'v3_intention', None)
            _line_locked = (getattr(_ist, 'phase', '') == 'locked'
                            and getattr(_ist, 'locked_comp', ''))
            if _synth_on and _line_locked and st.equips:
                from sr_od.application.currency_war.data.cw_synthesis import (
                    plan_syntheses,
                )
                _tgt = getattr(sess, 'target_comp', None)
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
                from sr_od.application.currency_war.kernel.cw_comps import (
                    equip_allocation,
                )
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
                    sess.target_comp, st.deployed, list(st.equips),
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
            res.ledger.append({
                'ts': _ts,   # 单调轮序号(跨位面累计;P1 段 == rn;审查①#9)
                'plane': st.plane, 'round_num': rn,
                'gold': st.gold, 'hp': st.hp,
                # ADR-0343:成型停手态入账本(轮内 OR 聚合;检查器豁免/判读锚点数据源)
                'formed_stop': _round_formed_stop,
                # 血预算停手·终止分支决策位(设计 迁移审计 w659(git 历史) v2 §5.1 R4;ADR-0469):
                # 谓词闩位经 discipline.terminal_release_bit 单一址记账,
                # 检查器 seg_p1_blood_budget_refresh/seg_terminal_release_
                # ledger 消费(禁复算 S0);决策发生在本轮回战斗前,位是
                # 闩(单调),轮 r 位=真 ⟺ 自本轮回决策起停付已让位
                'terminal_release': terminal_release_bit(sess, st.plane),
                # 换线存活门决策位(迁移审计 w665(git 历史) DESIGN v2 §3-2/R3;帧级=本轮
                # 最后一次意向驱动帧,update_intention 入口清零、
                # _switch_gate_open 评估点写入):line_gate_blocked=拦截位
                #(on 臂门判定);line_gate_cf_blocked=反事实判定位
                # P(f)=[R<need](off 臂反事实记账/on 臂同门判定)。消费=
                # A/B 批器算反事实拦截精度与 cw_sim_checks 位一致性核验
                #——检查器禁复算门判据式(迁移审计 w659(git 历史) 攻击 6 纪律)
                'line_gate_blocked': bool(getattr(
                    sess, 'v3_line_gate_blocked', False)),
                'line_gate_cf_blocked': bool(getattr(
                    sess, 'v3_line_gate_cf_blocked', False)),
                # `w227_handoff_gate/`/ADR-0400:末窗承接门缺口(0=不辖/达标;判读承接维
                # 触发面;与 formed_stop=False 并读 = 门扣住证据行)
                'handoff_gap': _round_handoff_gap,
                # 迁移审计 w238(git 历史)/ADR-0403:boss 投影 hp(None=投影关/非末窗;判读
                # 「boss 后投影 hp」面,与 handoff_gap 同点快照)
                'handoff_hp_proj': _round_handoff_hp_proj,
                # 迁移审计 w114(git 历史)/ADR-0346 相位影子观测(轮入口快照;零消费)
                'phase': _round_phase,
                'form_ok': _round_form_ok,
                'form_score': _round_form_score,
                'dp_posture': _round_dp_posture,
                # `w611_econ_cycle/` 储备/义务披露(轮入口快照;生产 decisions 行 sess_* 同语义)
                'reserve_cap': _round_reserve_cap,
                'reserve_overflow': _round_reserve_overflow,
                'release_budget': _round_release_budget,
                'release_reason': _round_release_reason,
                'piggy_reward': _round_piggy,
                # ②carry 装备分配义务帧(键按披露稳定保留;谓词已随五开关
                # 定谳清理删除,恒 False——历史账本字段只读口径,ADR-0487)
                'p1_duty': _duty,
                # 迁移审计 w146(git 历史) v3 意向状态(与生产 decisions 行同构;sim 分析批
                # 按它分锁定/未锁局——target_comp 只在锁定后非空,phase
                # 才能区分 unlocked/weak/locked)
                'v3_intention': serialize_intention(
                    getattr(sess, 'v3_intention', None)),
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
                          # 末窗支出降格触发面(语义见轮入口块注释;真值
                          # 恒披露——生产 OCR trace 267 帧恒 false 的
                          # sim 对账源)
                          'p1_downgrade_active': bool(_round_p1_downgrade),
                          # 轮岗概率条(本备战期真值;未掷中=None 退基线
                          # 表。生产 OCR 覆盖 21% 的 sim 全量对账源)
                          'refresh_probs': (
                              dict(st.refresh_probs)
                              if st.refresh_probs else None)},
                # 投资环境名(生产 decisions 行 _extra.sess_active_env
                # 同名同位;invest 注入写 session.active_env,cw_replay
                # 回读消费。空串 = 未注入/无环境——机制性缺省,非缺口)
                'sess_active_env': str(getattr(sess, 'active_env', '') or ''),
                # W829 支出门拒因枚举计数(生产 decisions 行
                # sess_spend_gate_block 同名同位;伞关/零拒因恒 None)
                'sess_spend_gate_block': (
                    dict(getattr(sess, 'v3_sg_block', None) or {}) or None),
                # 件价值·bench 预检硬门拒因计数(生产 decisions 行
                # sess_pv_bench_block 同名同位;伞关/零拒因恒 None)
                'sess_pv_bench_block': (
                    dict(getattr(sess, 'v3_pv_block', None) or {}) or None),
                'actions': _acts,
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
                        0, int(getattr(sess, 'v3_dir_refresh_used', 0) or 0)
                        - _dir_used0),
                    # 血预算停手·停升级拒付次数(决策层;设计件 12/
                    # ADR-0448):hp≤停升级线帧被门拦下的升级事件数
                    # (>0 = 本语义在该轮生效;决策侧判读输入)
                    'blood_budget_levelup_rejects': max(
                        0, getattr(sess, 'v3_blood_budget_rejects', 0)
                        - _bb_rejects_before),
                    # 血预算停手·搜索型刷新停付拒付次数(决策层;设计件
                    # 12 §2.3-P1-c/§3.2/ADR-0451):血预算不足帧被门拦下
                    # 的刷新事件数(>0 = 本语义在该轮生效;急救型/ALL IN
                    # 豁免帧不计)
                    'blood_budget_refresh_rejects': max(
                        0, getattr(sess, 'v3_blood_budget_refresh_rejects', 0)
                        - _bb_refresh_rejects_before),
                    # ADR-0287(批㉘ F1)+迁移审计 w652(git 历史) §5 处置①:重放围栏(部署前
                    # 快照语境冻结)的残留可上件数(行动语境下围栏认可件
                    # 未上;检查项 deploy_after_buy_semantics /
                    # ledger_deploy_lag_disclosure 的数据源)
                    'deploy_lag_units': _deploy_lag_units,
                    # 迁移审计 w716(git 历史) F1 修复:skip 轮残余补部署披露(上几件/保留集扣
                    # 几件;非 skip 轮恒 0——补部署只在 skip 分支)
                    'residual_deployed': _res_up,
                    'residual_held': _res_held,
                    # 动作 v2(契约包 C1):本轮围栏是否被显式动作跳过
                    # (skip_fence 账本行的 sim 侧披露;checks 配对锁数据源)
                    'fence_skipped': _explicit_deploy_seen,
                    # 迁移审计 w52(git 历史)(ADR-0326):本轮补偿趟是否放弃(0/1;连续放弃轮
                    # ≥3 由检查项 decision_v2_remedy_loop 报警——设计容量
                    # 不足信号)
                    'remedy_abandoned': 1 if getattr(
                        sess, 'v3_remedy_abandoned', 0)
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
                    # session.v3_alloc_frame);None = 本轮无决策段。
                    'alloc_frame': _round_alloc_frame,
                    'alloc_active_any': _round_alloc_active_any,
                },
            })
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
            _tc = getattr(sess, 'target_comp', None)
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
        # session.v3_handoff——案 b 臂同样经首轮 decide_prep 采样)。
        _h = getattr(sess, 'v3_handoff', None)
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
    if _inv is not None:
        # `w162_inject/`/ADR-0364:注入观测(实际持有序 = session 真值,含去重)
        res.invest_strategies = tuple(sess.active_strategies)
    return res




