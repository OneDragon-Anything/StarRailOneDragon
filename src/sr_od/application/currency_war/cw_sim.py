"""货币战争 P1 全流程模拟器(公共测试基建)。

诚实性分层(哪些是真机制,哪些是校准模拟——每层可独立替换):
- **真代码层**:策略决策(`DecisionV2Strategy.update_target` + `decide_prep`,
  生产逻辑直接跑;旧 `LineStrategy` 已删,ADR-0336)、发牌概率
  (`cw_shop_odds.REFRESH_PROB`,游戏内
  OCR 权威表)、有限牌池(`POOL_COPIES_PER_CARD` 27/27/9/9/9,
  买走即减/卖出回池)、角色注册表(`CHARACTERS`)、升级 XP 表
  (`XP_TO_NEXT_LEVEL` + 买牌 4XP)。
- **校准模拟层**(参数有默认、可注入覆盖):
  开局 bench 构成(4 张,65% 1费/35% 2费——遥测校准);
  每轮收入(基础 5 + 息 + 连胜奖);
  战斗结算:Δ池优先(实机经验分布采样);池不可达时的回退层
  胜负面 = **W31 实测节点×轮次胜率阶梯**(n=192 replay 语料,
  ``NODE_WIN_P_LADDER`` 单一源,ADR-0308),损益幅度沿用旧
  方向二元模型的幅度层(25 局 HP 轨迹校准)。

用途:策略改动先过本模拟(A/B 对照),再上实机验证(40min/局)。
典型用法::

    from sr_od.application.currency_war.cw_sim import simulate_p1

    res = simulate_p1(seed=42, use_refresh=False)   # A/B 对照
    report = simulate_p1_batch(n=500)               # 批量统计
    # Δ 池三态(⓪ 可复现基建):auto(默认,缺源 raise 不静默)/
    # snapshot(主仓提交快照,CI/跨机基准)/fallback(显式退旧
    # 模型,结果打标);A/B 对照同进程同池即可,跨日基线须核指纹。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_deploy_logic import (
    TRANSITION_TRAITS as _TRANSITION_TRAITS,
)
from sr_od.application.currency_war.cw_investments import (
    aggregate_economy,
    economy_effect_of,
)
from sr_od.application.currency_war.cw_shop_odds import (
    POOL_COPIES_PER_CARD,
    REFRESH_PROB,
    ROTATION_CHANCE,
    rotation_probs,
)
from sr_od.application.currency_war.cw_sim_invest import (
    InvestInjectionState,
    SimInvestProfile,
    sample_invest_profile,
)
from sr_od.application.currency_war.cw_state import (
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
    deployed_from_compact,
    deployed_occupied,
    deployed_place,
    iter_occupied,
    iter_occupied_deployed,
    sell_refund,
)
from sr_od.application.currency_war.cw_state import (
    simulate as _simulate_state,
)
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.cw_telemetry import serialize_intention

# 开局 bench 构成(遥测校准:开局 4 张,1 费主导)
START_BENCH_COUNT: int = 4
START_BENCH_COST_WEIGHTS: tuple[tuple[int, float], ...] = ((1, .65), (2, .35))

# 收入模型(r305 真值接入:sim 与决策共用 cw_economy 单一源)
from sr_od.application.currency_war.cw_economy import streak_gold  # noqa: E402,F401

# HP 上界(批㉘ F6,ADR-0287):游戏机制真值无文档证据,暂 cap 100
# (实机满血样本核真后更新;检查项 hp_upper_bound_truth 锁 hp>100 恒 0)
HP_UPPER_BOUND: int = 100

BASE_INCOME: int = 5
INTEREST_CAP: int = 5

# r360(v7 分轮次裁决):实机对账残差=奖励球/节点事件金未建模,
# 随轮次增长(r1→r2 中位 +1 … r8→r9 中位 +9)。校准层注入
# (ADR-0233):按轮次经验分布采样,让 sim 金压力对齐实机
# (策略的攒息/破息行为分布依赖真实金流)。
EVENT_GOLD_BY_ROUND: dict[int, tuple[float, ...]] = {
    1: (1,), 2: (5.5,), 3: (2,), 4: (2,), 5: (2,),
    6: (2,), 7: (4,), 8: (9,),
}


def _event_gold(round_num: int, rng: random.Random) -> int:
    """奖励球/节点事件金(校准层;v7 各轮中位,±2 抖动)。"""
    base = EVENT_GOLD_BY_ROUND.get(round_num, (4,))[0]
    return max(0, int(base + rng.uniform(-2, 2)))

# 战斗结算幅度层(25 局 HP 轨迹校准;胜负面自 ADR-0308 起由
# W31 节点×轮次胜率阶梯掷,幅度常量沿用本组)
EARLY_WIN_DELTA: int = 2            # r1-r2 弱敌小胜
WIN_DELTAS: tuple[int, ...] = (2, 2, 0, -4)   # 战斗胜时的轮结算
LOSS_BASE: float = 7.0              # r3 基础损
LOSS_PER_ROUND: float = 4.0         # 每多一轮加重(r7≈-23 对齐观测)
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
# 遭遇结算强度 = boss 档 × 1.15(用户口述:遭遇三四可比 boss 难;
# 遭遇一/二较温和 → 取均值系数,模拟无法读档位时的近似)
ENCOUNTER_MULT: float = 1.15
BOSS_BY_DIR_ROUND: tuple[tuple[int, float, float], ...] = (
    # (方向建立轮上限, boss 基础损, 抖动幅度)
    (2, 14.0, 8.0),
    (4, 22.0, 8.0),
    (6, 30.0, 8.0),
    (99, 36.0, 10.0),
)

# ===== W31 实测节点×轮次胜率阶梯(回退层胜负面单一源;ADR-0308) =====
# 来源:replay outcomes 语料 plane=1 & killed 非空 & board_before 非空
# = n=192(killed True 104 / False 88),按 (node_type, round) 统计的
# killed 胜率——W31 报告(`.debug/temp/currency_war/cw_dev/deep_read/
# W31_报告.md` §2)。替换旧拍脑袋胜负面:
#   battle  方向二元门控(方向已立→胜)——胜率从未按节点实测;
#   encounter 结构性恒败(p=0);
#   boss    rung 表 (0, 0, 0.25) + rung2 桶外推(ADR-0306,跨节点
#           外推边界已声明)。
# 逐轮实测:奖励轮 r1/r2/r8 全胜;battle r3 0.30 / r4 0.29;
# encounter r7 0.04;boss r9 0.05。未观测的 (node, round) 组合按
# 节点类型边际值兜底(``NODE_WIN_P_BY_TYPE``)。
# ⚠️ 数据边界(ADR-0308):语料全部来自旧策略(line_strategy)病局
# ——「六局同型败的镜像」(进度树 W30/W31 收账判读),阶梯是旧
# 策略在各种板面下的**边际**胜率,不含成型度条件性(rung 维被
# 压平);decision_v2 新策略语料攒够后**应重标本表**(届时遥测
# board_before 补记角色名+星级,W31 §6.1,条件性才可标定)。
NODE_WIN_P_LADDER: dict[tuple[str, int], float] = {
    ('battle', 3): 0.30,
    ('battle', 4): 0.29,
    ('encounter', 7): 0.04,
    ('boss', 9): 0.05,
}
NODE_WIN_P_BY_TYPE: dict[str, float] = {
    'reward': 1.0,    # 零战力节点,实测 100% 胜
    'supply': 1.0,
    'battle': 0.29,
    'encounter': 0.04,
    'boss': 0.05,
}
# 胜时小额(与 reward/supply 的 EARLY_WIN_DELTA 同档;「大胜」
# 形态待样本后校准幅度——W31 语料只有 killed 二值,无胜幅度分层)。
# ⚠️ P1 初始 HP=80 非 100(simulate_p1 `st.hp = 80`;批⑪ 自纠记档
# ——按 100 锚算 boss 损失会出伪影)。
BOSS_WIN_DELTA: int = 2

# ===== P2 段校准层(W157/ADR-0362;语料边界=W151 四局解剖+16 局
# replay plane=2 行 44 条,行为分布验证口径非 hp 点值校准) =====
# P2 位面段轮数(boss@r7;W156 §2:16 局 outcomes 拼版,r1-r7 全在)。
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
# P2 战斗回退档:胜率 0.11(W151:P2+ 战斗 1 胜 8 败)/败掉血带
# 15-17(W151:每败 -15~-17,B≈10+未达标罚 P;结算屏三项拆解
# P2r1 实证 +2/-10/-15,economy.md §10.2)。Δ池 plane=2 桶可及
# 时经验分布优先;缺桶走本带(ADR-0362)。
P2_BATTLE_WIN_P: float = 0.11
P2_LOSS_BAND: tuple[int, int] = (15, 17)

# ===== P2 战斗存活层参数化校准族(W193/ADR-0377,W186 设计 Phase 1) =====
# 结构:win_p = clip(p0 + β·form − γ·drift(round)),form=板面质量键
# (engines 数[deployed 口径,_settle_rung 同源]+level 折算+星级深度折算);
# 负=分段掉血带内均匀。**校准层(非真战斗机制)**,诚实边界:
# - 21 run 语料只够钉边界不够点估计 β——p0/β/γ 取保守值 + 敏感性带
#   扫描为裁决口径(修法在带端点一致翻正才裁「分布级」);
# - Δ池 plane=2 条件化(键 form×round,每桶 n≥5)留 Phase 3 自动让位
#   (语料阈值触发,非日历);
# - 四常数族单一注入点=P2CombatCalib(A/B 与敏感性扫描同通道)。
# 掉血分段带校准来源(`w193_p2sim/calibrate_truth.py` 复跑,真值=
# 生产 replay plane=2 未删失差分;hp_after==1 为败北地板删失样本弃):
# - battle_r1 (14,28):进场首战(跨位面差分,n=6 未删失;W186 设计文本
#   的「r1-r2 带 −4~−16」系 r2-vs-r1 相邻差分口径,不含 r1 自身——
#   本批实测 r1 明显更重,分立成段,偏差记 ADR-0377);
# - battle_early (4,16):r2-r3(设计口径带;本批未删失样本 15/15 落内);
# - battle_late (15,25):r4+(设计口径带;本批未删失 19-21 落内);
# - encounter (9,18) / boss (21,26):设计口径带(boss 样本均地板删失,
#   取原始差分下界语义=真损 ≥ 带端)。
# 胜率:p0=0.11(W151/语料边际 5/37=0.135 的保守下沿);β 方向由胜例
# board 强制为正、量级未定(胜例 form 1.25-2.25 vs 全体均值 ≈1.4,
# 几乎无区分度)→ 保守 0.04,敏感性主扫参;γ 弱(轮梯度未识别)→ 0.02。
# 星级分量(W230/ADR-0401,ADR-0377 form 扩展):star_depth=上场件
# Σ(star−1)(全量口径,同 ADR-0399 HandoffSnapshot star_sum−deployed_n,
# 纯 state 可算、生产/sim/离线回放三面同式);真值分帧校准
# (w230_star_form/calibrate_star.py,44 combat 帧/6 胜):
# engines=1 桶内 sd=0 → 0/8 胜,sd∈{1,2} → 3/15(0.20)——方向为正
# (胜例集中于 sd 1-2);sd≥3 零胜但 n≤4 不可辨 → 量级未定,保守
# form_star_weight=0.5(一颗 2★ 折半台引擎)+ 敏感性扫描端点 0/0.25/1.0;
# 动机 = W226/W227 实证 sim 缺星级因果通道(board_tier core2 维打不
# 出去、承接门主投资方向不可仲裁)。


@dataclass(frozen=True)
class P2CombatCalib:
    """P2 段战斗存活层参数族(W193/ADR-0377;单一注入点,A/B 同通道)。

    ``calibrated=False`` = 逐位回 W157/ADR-0362 行为(Δ池 plane=2 桶
    优先 + ``P2_BATTLE_WIN_P`` 恒值回退档)——A/B 回退对照臂。
    """

    #: 总开关:True=参数化校准层辖 plane≥2 战斗类结算(绕过 Δ池
    #: plane=2 合并采样——该路径被防饥饿守卫抹平条件性,ADR-0362
    #: 已判「假条件化」;Phase 3 桶键 form×round 到量后让位池采样)
    calibrated: bool = True
    #: 基础胜率(语料边际保守下沿)
    p0: float = 0.11
    #: form(板面质量键)系数:每单位 form 的胜率增量(敏感性主扫参)
    beta: float = 0.04
    #: 轮次漂移系数:敌人强度随轮增长(每轮 γ)
    gamma: float = 0.02
    #: 胜率钳制带
    win_p_clip: tuple[float, float] = (0.0, 0.5)
    #: form 键的 level 折算权重(form = engines + w·(level−6);
    #: engines=deployed 口径 _settle_rung 同源,0-4)
    form_level_weight: float = 0.25
    #: form 键的星级深度折算权重(W230/ADR-0401:star_depth=上场件
    #: Σ(star−1) 全量口径,同 ADR-0399 HandoffSnapshot;core2/board_tier
    #: 的星级维胜率因果通道)。保守 0.5,敏感性端点 0/0.25/1.0。
    form_star_weight: float = 0.5
    #: level 折算基准(P2 常见进场 level 6)
    form_level_base: int = 6
    #: 事件金双臂(W186 §3:K3 零样本——'p1'=复用 P1 表[打标未校准],
    #: 'zero'=P2 段事件金归零;敏感性双臂,rng 流两臂同耗保配对)
    event_gold: str = 'p1'
    #: 分段掉血带(败场;带内均匀采样)
    band_battle_r1: tuple[int, int] = (14, 28)
    band_battle_early: tuple[int, int] = (4, 16)
    band_battle_late: tuple[int, int] = (15, 25)
    band_encounter: tuple[int, int] = (9, 18)
    band_boss: tuple[int, int] = (21, 26)
    #: 胜场结算值(语料胜例 Δ=+2)
    win_delta: int = 2


#: 默认参数族(模块单一实例;敏感性/A/B 经 simulate_p1 的 p2_combat 注入)
P2_COMBAT_DEFAULT = P2CombatCalib()


def deployed_star_depth(st: GameState) -> int:
    """净星深 = 上场件 Σ(star−1)(全量口径,同 ADR-0399
    HandoffSnapshot star_sum−deployed_n;纯 state 可算、生产/sim/
    离线回放三面同式)。

    消费点:p2_form_key 星级分量(W230/ADR-0401)与 **Δ池 boss 桶键**
    (W240/ADR-0404,替代 Σboard——修 3合1 升星使 Σboard −2/次键落
    浅桶的方向冲突;净星深下 1★→2★ 合并键 +1 永不落浅桶,买 bench
    副本不扰动)。已知边界:2★→3★ 合并键 −1(3 副本 Σ(star−1)=3 →
    载体 2),仅当键恰为 3 的倍数时跨桶——高级合并当前语料零样本,
    语料攒厚后复核。
    """
    return sum(
        int(getattr(d, 'star', 1) or 1) - 1
        for d in (st.deployed or []) if d is not None)


def _star_depth_from_rows(rows) -> int:
    """净星深(replay 行口径):decisions ``state.deployed`` 条目
    (dict 形态)Σ(star−1)——与 :func:`deployed_star_depth` 同式,
    池语料侧(_pool_from_replay/cw_delta_pool_gen)共用,防双源。"""
    return sum(int(x.get('star') or 1) - 1
               for x in (rows or []) if isinstance(x, dict))


def p2_form_key(st: GameState, calib: P2CombatCalib) -> float:
    """form=板面质量键(W193/ADR-0377:engines+level 折算;
    W230/ADR-0401 扩展:+星级深度折算)。

    engines = ``_settle_rung`` 同源(deployed 口径四体系达成数,0-4);
    W182 实测 deployed 口径与掉血对应最干净、板深无区分度。
    star_depth = ``deployed_star_depth`` 单一源(core2 维/board_tier
    的星级分量因果通道,W226 §⑥/W227 挂账的 sim 建模缺口)。
    """
    star_depth = deployed_star_depth(st)
    return (float(_settle_rung(st)) + calib.form_level_weight * (
        st.level - calib.form_level_base)
        + calib.form_star_weight * star_depth)


def p2_win_p(st: GameState, node: str, round_num: int,
             calib: P2CombatCalib) -> float:
    """参数化胜率:clip(p0 + β·form − γ·drift(round))。

    drift = max(0, round−1)(r1 无漂移;敌人强度逐轮增长的最小参数化)。
    """
    lo, hi = calib.win_p_clip
    form = p2_form_key(st, calib)
    drift = max(0, round_num - 1)
    return min(hi, max(lo, calib.p0 + calib.beta * form
                       - calib.gamma * drift))


def p2_loss_band(node: str, round_num: int,
                 calib: P2CombatCalib) -> tuple[int, int]:
    """分段掉血带路由(battle 按 r1/r2-r3/r4+ 分段;encounter/boss 独立)。"""
    if node == 'battle':
        if round_num == 1:
            return calib.band_battle_r1
        if round_num <= 3:
            return calib.band_battle_early
        return calib.band_battle_late
    if node == 'encounter':
        return calib.band_encounter
    return calib.band_boss


def p2_combat_delta(st: GameState, node: str, round_num: int,
                    rng: random.Random,
                    calib: P2CombatCalib) -> tuple[int, float]:
    """P2 战斗类节点参数化结算(胜→win_delta/负→分段带内均匀)。

    返回 (delta, win_p)——win_p 随账本披露(检查器带锚/敏感性判读消费)。
    """
    wp = p2_win_p(st, node, round_num, calib)
    if rng.random() < wp:
        return calib.win_delta, wp
    lo, hi = p2_loss_band(node, round_num, calib)
    return -rng.randint(lo, hi), wp


def node_win_p(node_type: str, round_num: int = 0) -> float:
    """节点胜率单一取值口(ADR-0308;回退层胜负面)。

    (node, round) 实测组合优先(``NODE_WIN_P_LADDER``),缺组合退
    节点类型边际(``NODE_WIN_P_BY_TYPE``)。语料边界见常量注释:
    旧策略病局镜像、无成型度条件性——新策略语料攒够后重标。
    """
    if node_type in ('reward', 'supply'):
        return NODE_WIN_P_BY_TYPE[node_type]
    v = NODE_WIN_P_LADDER.get((node_type, round_num))
    if v is None:
        v = NODE_WIN_P_BY_TYPE.get(node_type, 0.0)
    return v


@dataclass
class SimResult:
    """单局模拟结果。"""

    seed: int
    dir_round: int = 99             # 方向(锁线/桥)建立轮;99=未建立
    final_hp: int = 0
    hp_trail: list[int] = field(default_factory=list)
    refreshes: int = 0
    level: int = 3
    locked_line: str | None = None
    bridge_id: str | None = None
    # r338 诊断基建:逐轮事件 (round, node_type, delta, dir_established)
    hp_events: list[tuple[int, str, int, bool]] = field(default_factory=list)
    # r341 诊断基建:逐轮板深(_deployable_depth=min(level, len(
    # deployed));r390 起读 deployed,ADR-0271 起为真上场名单)
    depth_trail: list[int] = field(default_factory=list)
    # ⓪ 可复现基建:本局所用 Δ 池指纹与来源(裸 seed 不构成
    # 重放承诺,重放 = seed + 指纹;跨日基线对照必须同指纹)
    pool_fingerprint: str = ''
    pool_source: str = ''
    # ① 判读同构账本:每轮一行(轮内多段聚合;字段与遥测 jsonl
    # 同构 + sim 专属键挂 'sim' 下)。由 write_batch_ledger 落盘
    # sim_runs/<batch_id>/{decisions,outcomes}.jsonl 两流。
    ledger: list[dict] = field(default_factory=list)
    # ADR-0284(批㉒ F1/F5):幻影再买提案数(已消费槽/店外构造;
    # 真策略批次应恒 0)与牌池 take 地板命中数(copies≤0 仍 take;
    # 槽消费落地后池超卖不可达,>0 = 池守恒破)
    phantom_rebuys: int = 0
    pool_floor_hits: int = 0
    # ADR-0294 件2(ADR-0289 §5 裁决):supply 带钻选项被选中次数
    # (占位实体披露计数——'钻石' 不再以真装备身份进 owned 池,
    # 只在此计数披露,phantom_equip_no_wear 回归 0 容忍)
    phantom_supply_picks: int = 0
    # W213/ADR-0394:P1 出口 key_equips 命中度量(命中数 / 需求总数;
    # 口径 = P1 段末 worn(deployed.equips)+ owned(st.equips)合并
    # 对当时 target_comp.key_equips(计重复)的满足量;target 未锁
    # 定或 key 为空的局 total=0,聚合端按 total>0 局求均值——W212
    # 批 A 同口径(key_last=最后一次分配时的 key 表))
    p1_key_hit_hits: int = 0
    p1_key_hit_total: int = 0
    # 动作 v2(契约包 C1,步2):显式部署动作(SellDeployed/SwapDeploy/
    # CompTransaction)被整体拒绝的次数(原子性拒绝披露;真策略当前
    # 不发显式动作 → 恒 0,演进引擎 C3 接入后 >0 即决策侧提案越界信号)
    explicit_action_rejects: int = 0
    # 动作 v2:围栏跳过轮数(显式动作发出轮 select_deployments 自动
    # 部署让位——裁决1「显式>围栏,同轮互斥」;账本同步记 skip_fence 行)
    fence_skips: int = 0
    # ===== P2 段观测(ADR-0362,W157;planes>=2 时填,默认 0/False)=====
    p2_entered: bool = False        # 活过 P1 进场 P2(P1 段死=False)
    p2_rounds: int = 0              # P2 段已结算轮数(0-7)
    p2_combat_total: int = 0        # P2 段战斗类节点结算数
    p2_combat_wins: int = 0         # 其中 delta>=0 的胜场数
    p2_hp0: bool = False            # 死在 P2 段(终局 hp<=0)
    p2_refreshes: int = 0           # P2 段 RefreshShop 次数(D 次数)
    # ===== P2 校准层与判读观测(W193/ADR-0377;planes>=2 时填)=====
    p2_combat_calibrated: bool = False   # 本局 P2 结算走参数化校准层?
    p2_gold_carried: int | None = None   # 金带走量(死在 P2 段时的末金;
                                          # 活过 P2=None——W183 D1 判据族)
    p2_buys_by_cost: dict[str, int] = field(default_factory=dict)
                                        # P2 段买笔数按价格带 {'1-2','3','4-5'}
                                        # (W183 价格带判读口径)
    p2_switch_events: list[tuple[int, str, str]] = field(default_factory=list)
                                        # 意向切换事件 (轮,前 target,后 target)
                                        # (W182「切换后采购执行密度」数据源)
    p2_lv6_round: int | None = None  # P2 段内首次 level>=6 的轮(None=未达)
    p2_lv7_round: int | None = None  # P2 段内首次 level>=7 的轮(W183:
                                     # run15 恒 lv6 卡死形态的可观测指标)
    # W224/ADR-0399:P2 承接快照(decision_v2.handoff.HandoffSnapshot.
    # as_dict;进场继承完成后位面首帧采样——生产同点=session.v3_handoff,
    # 决策代码挂载零复制单一源)。None=未进 P2/策略桩未算。纯观测零漂移
    # (不耗 rng,planes=1 路径不触及)。
    p2_handoff: dict | None = None
    # ===== 投资注入观测(W162/ADR-0364;invest 注入时填,默认空/0)=====
    invest_env: str = ''            # 本局注入的投资环境名(空 = 无)
    invest_strategies: tuple[str, ...] = ()   # 本局实际注入持有的策略名序
    p1_locked_rounds: int = 0       # P1 段意向 phase=='locked' 的轮数
                                      # (①资格通道激活直证——无注入语料下
                                      # 恒 0,W161 缺口闭合前后对照键)


class _Pool:
    """有限牌池(真机制):每卡剩余副本,买走即减、卖出回池;
    槽抽取 = REFRESH_PROB 定费用档 → 池内均匀。

    ADR-0272(批④F1,实机已裁决):**不按费用截断**——全角色入池
    (1-5 费),出率由 REFRESH_PROB 按等级自然给出(lv5 起 4 费
    .02→lv9 .30;lv7 起 5 费 .01→lv9 .10——P1 等级可达 9,5 费
    可达故入池)。旧 max_cost=3 截断把 4/5 费概率质量静默重归一化
    (lv9 4费 .30→0),14 个 4 费角色不进池——低费虚高频 = 供给
    失真。表源=游戏内概率表 OCR(D-91),无位面维度。"""

    def __init__(self, rng: random.Random):
        self.rng = rng
        # ADR-0284(批㉒ F5):take 逼近池地板时如实记(copies≤0
        # 仍 take 的次数;旧 max(0,…) 静默吞——真批次应恒 0)
        self.floor_hits: int = 0
        self.copies: dict[str, int] = {
            name: POOL_COPIES_PER_CARD[ch.cost]
            for name, ch in CHARACTERS.items()
            if ch.cost
        }

    def draw_shop(self, level: int,
                  probs: dict[int, float] | None = None) -> list[ShopCard]:
        """抽一帧商店;``probs`` 非空 = 轮岗翻倍后的概率表(ADR-0286,生产
        概率条 OCR 真值同构),None = 基线 REFRESH_PROB。"""
        out: list[ShopCard] = []
        for i in range(5):
            dist = probs if probs is not None else REFRESH_PROB.get(level, {})
            costs = [c for c in dist if dist[c] > 0]
            if not costs:
                continue
            cost = self.rng.choices(
                costs, weights=[dist[c] for c in costs], k=1)[0]
            names = [n for n in self.copies
                     if CHARACTERS[n].cost == cost and self.copies[n] > 0]
            if not names:
                continue
            name = self.rng.choice(names)
            out.append(ShopCard(
                x=i, faction=(CHARACTERS[name].factions or ['散'])[0],
                name=name, cost=cost))
        return out

    def take(self, name: str) -> None:
        # ADR-0284(批㉒ F5):池地板如实记——批㉒ 实测 27 份/卡
        # 下地板不可达(潜伏),未来降池容量/共享池时 >0 即暴露。
        if self.copies.get(name, 0) <= 0:
            self.floor_hits += 1
        self.copies[name] = max(0, self.copies.get(name, 0) - 1)

    def ret(self, name: str) -> None:
        base = POOL_COPIES_PER_CARD.get(CHARACTERS[name].cost, 9)
        self.copies[name] = min(base, self.copies.get(name, 0) + 1)


def battle_delta(round_num: int, dir_round: int,
                 rng: random.Random) -> int:
    """普通战斗 HP 变化(校准层回退;ADR-0308)。

    胜负面 = W31 实测阶梯 ``node_win_p('battle', round_num)``
    (n=192;旧方向二元门控「已立→胜」废弃——胜率从未按节点实测,
    语料实测方向已立后战斗胜率仍 ~0.29);胜 → ``WIN_DELTAS``,
    负 → 旧损益幅度层(LOSS_BASE/LOSS_PER_ROUND,25 局轨迹校准,
    保留)。``dir_round`` 保留签名兼容,不再参与胜负判定。
    """
    if round_num <= 2:
        return EARLY_WIN_DELTA
    if rng.random() < node_win_p('battle', round_num):
        return rng.choice(WIN_DELTAS)
    loss = LOSS_BASE + LOSS_PER_ROUND * (round_num - 3) \
        + rng.uniform(-3, 4)
    return int(-loss)


# r343 实机分布(31 局 outcomes 全量差分,645 轮):
# 逐 run 差分 battle -7.3 / boss -25.1 / encounter -12.2;
# **板深条件化**(decisions board join,深=Σ阵营人次):
# battle 深[6-8] -1.0 vs [3-5] -11.3 vs [15-17] -7.1(非单调,
# 深 12+ 才稳);boss 深15+ -23.7 vs 深12 -27.9。
# 池结构:{node_type: {depth_bucket: [Δ...]}}——sim 结算按
# 当轮实deep采样(经验分布,无参数假设)。
# r343(review E 注):池在进程内懒加载一次冻结——消费方是
# sim CLI(短命),新遥测数据要重跑进程生效。
# r343(review F/J):深度代理=可 deploy 件数(阵营 count≥2
# +引擎单件,capped by level)——对齐实机 _should_deploy。
# r375:引擎阵营消手抄双源——顶部 import 挂 cw_line_defs.
# ENGINE_FACTIONS(桥池 engine_bonds 派生;别名 _SIM_ENGINE_
# FACTIONS 保留,r343 源码锁与历史注释引用)。手抄副本曾三处
# 漂移:缺 持续伤害/贝洛伯格(r373 给 dot_belog 桥补了生产
# deploy 身份,sim 代理没跟 → 该桥局板深低估,ADR-0219 病),
# 多 银河学者(不在任何桥 engine_bonds)。
_DEPTH_BUCKET_W: int = 3   # 板深分桶宽

# --- Δ 池三态解析(⓪ 快照化;对抗审查一轮#1/二轮#1/#5 定谳) -----
# 校准数据可复现性纪律:
# - **缺源大声报错,禁止隐式静默回退**(实测同 seed 有池/无池可
#   翻转 hp_ge_60 判定:seed42 final 36 vs 55)——回退必须显式
#   pool='fallback',结果行打标 pool_source;
# - **指纹 = hash(池内容+桶宽+采样器版本)**,随 SimResult/批量
#   结果记录——裸 seed 不构成可重放承诺,重放 = seed+指纹;
# - 池源与 sim 落盘(sim_runs)隔离,防线在生成器源目录断言
#   (tools/cw/gen_delta_pool_snapshot.py,防 sim 数据回灌校准池)。
# v6(ADR-0308,W37):回退层胜负面换 W31 实测节点×轮次胜率阶梯
# (NODE_WIN_P_LADDER,n=192)——battle 方向二元门控/encounter 恒败/
# boss rung 表+rung2 外推全部废弃(幅度层保留)。池内容不变但结算
# 语义变 → 快照 META 指纹与锚重记(ADR-0308 回归验证节)。
_SAMPLER_VERSION: int = 11  # 桶化/邻桶回退/采样语义变更时 +1(指纹输入)
# v7(ADR-0312,W50 口径统一):采样键 _deployable_depth 从
# min(level, len(deployed)) 改 **Σboard(全集口径)**——与池语料
# (decisions state.board 求和,实机全集口径)同口径;旧键与池语料
# 不同口径,同一局面两侧落不同桶,采样系统性偏浅(W49 Q4)。同时
# state.board 本身换全集口径(_recount_board)——池内容不变但 sim
# 侧查询/结算键变 → 快照 META 指纹重算 + ANCHOR_REGISTRY_N300 锚
# 重记(ADR-0308 同款流程)。
# v8(ADR-0362,W157 P2 段扩展):Δ池 **plane 维键化**——SNAPSHOT
# 形状 {节点:{位面:{桶:[Δ]}}},差分归属后行位面(P1r9→P2r1 跨
# 位面差分归 plane=2);顺手清除既有 P1 池 P2 污染(44 条 plane=2
# 差分混入无位面维的池,含 16 条跨位面差分,W156 勘察 §5.1)。
# P1 桶语料随污染清除小幅变化 → 指纹重算 + ANCHOR_REGISTRY_N300
# 锚重记(P2 段扩展换锚,P1 侧 drift 如实记档);live_delta_for
# 增 plane 参(plane≥2 不跨位面回退——位面难度语义不同,缺桶走
# 位面内兜底/回退层 P2 掉血带 15-17)。⚠️ 版本号勘误(W240):本条在
# 快照 note 链里记作 v9(生成器 note 链自 W109 批起与 _SAMPLER_VERSION
# 错位 +1);快照 note 链自 v10 起与本常量对齐。
# v10(ADR-0404,W240):**boss 桶键 Σboard→净星深**(上场件
# Σ(star−1),与 ADR-0399 HandoffSnapshot star_sum−deployed_n /
# p2_form_key star_depth 同源口径;单一源=_boss_star_depth)。修
# W238 实证的方向冲突(3合1 消耗场上副本 → Σboard −2/次 → 键落浅桶,
# 而浅桶期望伤害更大 → sim 判「升星→boss 伤害↑」与 [27] 机制相反):
# 净星深下 1★→2★ 合并键 +1 永不落浅桶;重生成后 P1 boss 语料
# (49 行)全落桶 0——旧 Σboard 桶 9/12/15 的「条件性」系键口径伪影,
# 真值≈无条件期望 27.57(≈旧全池 fallback 27.33,交叉自洽)。
# encounter/reward/supply 桶键不动(Σboard);池内容变(指纹重算)+
# W238 常数表重标定(registry handoff_boss_e_damage 键域
# {9,12,15}→{0})。
# v11(ADR-0407,W250):encounter 桶键 depth→rung(_settle_rung 同源;
# 解批⑬ F1 暂缓——扩容后 rung 主桶 n=23/27 达标、梯度显著,而 depth
# 键下期望伤害真平 p=0.87)。reward/supply depth 键不动;池内容变。
# v2(ADR-0268):加防饥饿守卫——n<_BUCKET_MIN_N 的桶降级采样
# (邻桶合并/全池均匀取方差最小),不再裸采样。v1→v2 变更采样
# 语义,历史报告对旧池(v1 指纹)重放须用导出 JSON 快照。
# v3(ADR-0279,批⑬):battle 桶键 depth→rung(成型度一维分桶,
# 守卫邻接宽随键语义 = rung±1);encounter 维持 depth 分桶
# (批⑬ F1 encounter rung 桶样本不足,暂不分;v11 已解禁迁 rung)。
# 历史报告对旧池
# (v2 指纹)重放同样须用导出 JSON 快照。
# v4(ADR-0292,批㉗ F3/F4):reward/supply 结算由恒 EARLY_WIN_DELTA
# 改 Δ池经验分布采样(depth 桶 + 全池兜底);批㉗ F4 的「右胖尾
# mean 9.15/p90+39」经语料复核为**跨 run 配对伪影**(同 run 奖励轮
# 差分 n=43 全 +2;+27~+61/负值样本只出现在跨 run 相邻行),入池
# 真值 = 恒 +2 分布——历史报告对旧池(v3 指纹)重放须用导出 JSON。
# v5(ADR-0306,Δ池扩容批):boss 胜分支 rung≥3 胜率由拍脑袋 0.25 改
# rung2 桶实测外推(boss_win_p,快照 META 单一源);快照 META 新增
# 胜判定权威口径(killed)逐桶统计与桶贫困披露。池内容不变但校准
# 语义变 → 旧锚全作废重记(ADR-0306 回归验证节)。
_BUCKET_MIN_N: int = 5   # 防饥饿守卫门槛(批③ F1:battle 桶6 n=1
# 恒 -11,把跨深度 6 边界的策略臂系统性伪惩罚;建议值同报告)
# 仓根锚定(审查#7:相对路径 cwd 敏感,非仓根 cwd 的 auto 指错目录)
_AUTO_REPLAY_DIR = Path(__file__).resolve().parents[4] / '.debug' \
    / 'temp' / 'currency_war' / 'replay'


class DeltaPoolUnavailable(RuntimeError):
    """auto 模式找不到可用 Δ 池源——显式选 snapshot/fallback。"""


def pool_fingerprint(pool: dict) -> str:
    """池指纹:hash(池内容规范化 + 桶宽 + 采样器版本)。

    只哈希内容盖不住采样器语义(分桶宽/回退策略变了,同 seed
    结果变而指纹仍显示命中——二轮#5),故语义常量一并入指纹。
    """
    import hashlib
    import json as _json
    # ADR-0362(W157):canon 多一层位面({节点:{位面:{桶:Δ}}})——
    # plane 维是池内容的一部分(位面分离语义),入指纹。
    canon = _json.dumps(
        {n: {str(p): {str(b): sorted(v) for b, v in sorted(buckets.items())}
             for p, buckets in sorted(planes.items())}
         for n, planes in sorted(pool.items())},
        ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(
        f'v{_SAMPLER_VERSION}|w{_DEPTH_BUCKET_W}|{canon}'.encode()).hexdigest()[:16]


def _pool_from_replay(replay_dir: Path) -> tuple[dict, dict]:
    """从生产 replay jsonl 构建 Δ 池 + 构成 meta。

    配对口径(r340 起):decisions 每轮取末行板深(Σboard),
    outcomes 同 run 按 (plane, round) 排序后相邻轮 hp 差分。
    半写行跳过并计数(生产 append 进行中尾行可能撕裂)。
    ADR-0362(W157):差分归属**后行位面**——{节点:{位面:{桶:[Δ]}}}
    (与 cw_delta_pool_gen.build_pool 同口径;P1/P2 分桶)。
    """
    import json as _json
    skipped: dict[str, int] = {}

    def _rows(name: str) -> list[dict]:
        out: list[dict] = []
        f = replay_dir / name
        if not f.exists():
            return out
        for ln in f.read_text(encoding='utf-8').splitlines():
            if not ln.strip():
                continue
            try:
                out.append(_json.loads(ln))
            except _json.JSONDecodeError:
                skipped[name] = skipped.get(name, 0) + 1
        return out

    boards: dict = {}
    # W240/ADR-0404:boss 桶键=净星深(上场件 Σ(star−1));v11 起桶键
    # 判据需 deployed 名单(rung)也辖 encounter——decisions 行 join;
    # reward/supply 仍用 Σboard(boards)。
    star_depths: dict = {}
    # ADR-0279(批⑬):battle rung 判据需上场名单(希儿系=单卡
    # 依赖)——从 decisions join deployed;join 缺失时希儿系可能
    # 漏计(rung 低估 1 档),与批⑬盲区声明一致。
    deployed_names: dict = {}
    for d in _rows('decisions.jsonl'):
        st = d.get('state') or {}
        b = st.get('board') or {}
        k = (d.get('run_id'), d.get('plane'), d.get('round_num'))
        boards[k] = sum(b.values())
        star_depths[k] = _star_depth_from_rows(st.get('deployed'))
        deployed_names[k] = frozenset(
            x.get('char_id') or '' for x in (st.get('deployed') or [])
            if isinstance(x, dict))
    seqs: dict[str, list] = {}
    for o in _rows('outcomes.jsonl'):
        if o.get('hp_after') is None:
            continue
        seqs.setdefault(o.get('run_id'), []).append(o)
    pool: dict = {}
    per_run_rounds: dict[str, int] = {}
    unlabeled_dropped = 0
    for run, seq in seqs.items():
        seq.sort(key=lambda o: (o.get('plane') or 0, o.get('round_num') or 0))
        per_run_rounds[str(run)] = len(seq)
        for a, b in zip(seq, seq[1:], strict=False):
            raw_nt = b.get('node_type') or ''
            nt = {'普通战斗': 'battle', '遭遇': 'encounter',
                  '奖励': 'reward', '首领': 'boss',
                  '补给': 'supply'}.get(raw_nt, raw_nt)
            if not nt:
                # 2026-08-22 retrofix(ADR-0239 配套)后历史死链标签
                # 置 None——无标签行不入池(与快照生成器 v2 同口径;
                # 审查#1:否则 auto/snapshot 两态指纹结构性永不相等,
                # 指纹相等性无法用作收敛判据)。
                unlabeled_dropped += 1
                continue
            # ADR-0362(W157):差分归属后行位面(P1r9→P2r1 归 plane=2)
            plane = int(b.get('plane') or 1)
            k = (run, b.get('plane'), b.get('round_num'))
            dep = boards.get(k)
            sd = star_depths.get(k)
            if dep is None:
                continue
            delta = b['hp_after'] - a['hp_after']
            if nt == 'battle':
                # ADR-0279(批⑬ F1/F2/F4):battle 按 rung 一维分桶
                # ——depth-only 池把成型信息扔掉(d9 成型桶 sim 高估
                # 战损 ~6.4hp/场);rung 输入 = 结算前 board_before
                # (主阵营计数)+decisions deployed(希儿系单卡判据),
                # rung 定义单一源 = _engines_count(与 boss_settle_
                # delta 同源)。depth 维弃用(批⑬ F3:depth×rung 二维
                # 键 27 格仅 3 格够,样本粉碎)。
                bucket = _engines_count(
                    b.get('board_before') or {},
                    deployed_names.get(k, frozenset()))
            elif nt == 'boss':
                # W240/ADR-0404:boss 桶键=净星深(上场件 Σ(star−1),
                # deployed_star_depth 同式)——Σboard 键下 3合1 升星
                # 使键 −2/次落浅桶而浅桶期望伤害更大,与 [27]「星级↑
                # =战力↑」相反(W238 实证);净星深下 1★→2★ 合并键 +1。
                if sd is None:
                    continue
                bucket = min(sd // _DEPTH_BUCKET_W, 5) * _DEPTH_BUCKET_W
            else:
                # v11(ADR-0407,W250):encounter 桶键 depth→rung(与
                # battle 同源 _engines_count;键查证:dep/sd 键下期望
                # 伤害真平 p=0.87,rung 键梯度显著)。reward/supply 沿用
                # depth 分桶。
                if nt == 'encounter':
                    bucket = _engines_count(
                        b.get('board_before') or {},
                        deployed_names.get(k, frozenset()))
                else:
                    bucket = min(dep // _DEPTH_BUCKET_W,
                                 5) * _DEPTH_BUCKET_W
            pool.setdefault(nt, {}).setdefault(
                plane, {}).setdefault(bucket, []).append(delta)
    meta = {'source_dir': str(replay_dir), 'runs': per_run_rounds,
            'skipped_lines': skipped,
            'unlabeled_dropped': unlabeled_dropped}
    return pool, meta


def _normalize_pool(raw: dict) -> dict:
    """桶键/位面键归一 int(json round-trip 会变字符串键——str 键会让
    live_delta_for 的 int 桶查询全 miss = 快照静默失效;ADR-0362 起
    池形状 {节点:{位面:{桶:[Δ]}}},两层都归一)。"""
    return {n: {int(p): {int(b): list(v) for b, v in buckets.items()}
                for p, buckets in planes.items()}
            for n, planes in raw.items()}


def plane_view(pool_map: dict, plane: int = 1) -> dict:
    """取池的**单位面视图**({节点:{桶:[Δ]}};ADR-0362,W157)。

    P1 锚定的池级检查(min_n/深崖/rung 锁/reward 锁/coverage)判据
    全是 P1 语料口径——消费位面化池时先取本视图,检查代码零改动;
    plane≥2 桶不进这些判据(语料贫困,走 META ``p2:`` 前缀披露)。
    """
    return {n: dict(planes.get(plane) or {})
            for n, planes in (pool_map or {}).items()}


_RESOLVED_CACHE: dict[str, tuple[dict, str, str]] = {}


def resolve_pool(pool: str | Path = 'auto', *,
                 auto_dir: Path | None = None) -> tuple[dict, str, str]:
    """Δ 池三态解析 → (pool_map, fingerprint, source_label)。

    - ``'auto'``(默认):生产 replay 实时构建(进程内缓存一次
      冻结);缺源/空池 raise DeltaPoolUnavailable——**不静默**;
    - ``'snapshot'``:主仓提交快照 ``cw_delta_pool_data``
      (CI/跨机可复现基准;重生成 tools/cw/gen_delta_pool_snapshot.py);
    - ``'fallback'``:显式退旧方向二元模型(结果打标,供无池
      环境的语义测试);
    - :class:`Path`:JSON 快照文件(生成器 --export-json 产物,
      历史版本重放用)。
    """
    key = repr((str(pool), str(auto_dir)))
    if key in _RESOLVED_CACHE:
        return _RESOLVED_CACHE[key]
    if pool == 'fallback':
        out = ({}, pool_fingerprint({}), 'fallback')
    elif pool == 'snapshot':
        from sr_od.application.currency_war.cw_delta_pool_data import (
            META as _META,
        )
        from sr_od.application.currency_war.cw_delta_pool_data import (
            SNAPSHOT as _SNAP_RAW,
        )
        _SNAP = _normalize_pool(_SNAP_RAW)
        if pool_fingerprint(_SNAP) != _META.get('fingerprint'):
            raise RuntimeError(
                '快照指纹失配:cw_delta_pool_data 被手改或指纹逻辑'
                '漂移——重跑 tools/cw/gen_delta_pool_snapshot.py')
        out = (_SNAP, _META['fingerprint'], 'snapshot')
    elif isinstance(pool, Path):
        doc = _json_loads_path(pool)
        snap = _normalize_pool(doc['snapshot'])
        fp = pool_fingerprint(snap)
        _meta_fp = (doc.get('meta') or {}).get('fingerprint')
        if _meta_fp is not None and _meta_fp != fp:
            # 审查#2:Path 模式校验 meta 指纹(失配 JSON 静默接受
            # = 历史重放的可信前提缺失)
            raise RuntimeError(
                f'快照文件指纹失配: {pool}(meta {_meta_fp} vs 重算 '
                f'{fp})——文件被改或导出时损坏,重导出')
        out = (snap, fp, f'path:{pool.name}')
    elif pool == 'auto':
        d = Path(auto_dir) if auto_dir else _AUTO_REPLAY_DIR
        p_map, meta = _pool_from_replay(d)
        if not p_map:
            raise DeltaPoolUnavailable(
                f'auto 池源不可用: {d.resolve()}(缺失/空/不可解析)。'
                "显式指定 pool='snapshot'(主仓提交快照)或 "
                "pool='fallback'(退旧方向二元模型,结果打标)")
        # 审查#4:半写行/整文件重写窗口 → 静默减样池——计数并入
        # source_label 披露(非空池也可见,不只覆盖空池)
        _skip = sum(meta.get('skipped_lines', {}).values()) \
            + meta.get('unlabeled_dropped', 0)
        label = 'auto' + (f'(skip{_skip})' if _skip else '')
        out = (p_map, pool_fingerprint(p_map), label)
    else:
        raise ValueError(
            f'pool 参数非法: {pool!r}(auto/snapshot/fallback/Path)')
    _RESOLVED_CACHE[key] = out
    return out


def reset_resolved_cache() -> None:
    """清空池解析缓存(审查#3:同路径文件更新后进程内仍返旧池;
    生成器/测试改写快照文件后调用,拿新指纹)。"""
    _RESOLVED_CACHE.clear()


def _json_loads_path(p: Path) -> dict:
    import json as _json
    return _json.loads(p.read_text(encoding='utf-8'))


def live_delta_for(node_type: str, key: int,
                   rng: random.Random, *,
                   pool_map: dict | None = None,
                   plane: int = 1) -> int | None:
    """按节点类型 + 分桶键取实机经验 Δ;无匹配桶 → None(调用方走旧模型)。

    **位面维(ADR-0362,W157)**:``plane`` 选池的位面层;plane≥2
    **不跨位面回退**——位面难度语义不同(P2 掉血带 15-17 vs P1
    battle -7~-13),跨位面借样本=口径混桶;该位面桶缺 → 位面内
    兜底链(下探/全池合并)→ 仍空 → None(调用方走 P2 回退层
    掉血带,见 ``node_delta`` 的 plane 分支)。P2 语料 44 行,
    条件化分桶不做(每桶 n<5,防饥饿守卫辖)——实际采样≈位面内
    全池合并的经验分布(W156 §2 分层结论)。

    **桶键语义按节点分流(ADR-0279,批⑬)**:

    - ``battle``:``key`` = 成型度 rung(0-4,池桶键即 rung;
      与 ``boss_settle_delta`` 的 rung 定义同源 ``_engines_count``)。
      桶不可达时逐级下探更低 rung(信息最接近的可及桶);全不可达
      → 全池合并兜底(rung 信息缺,保经验分布方差;批⑬ F3「池均值
      兜底」形态);池空 → None。
    - ``encounter``:``key`` = **成型度 rung**(v11,ADR-0407,W250;
      与 battle 同源 ``_engines_count``/``_settle_rung`` 单一源。
      批⑬ F1「rung 样本不足暂 depth 分桶」经扩容+键查证解禁:depth
      键下期望伤害真平(Σboard<12 vs ≥12 置换检验 p=0.87,Spearman
      −0.001;净星深键同样无梯度),而 rung 键下梯度单调且显著
      (r0 n=23 EΔ−24.9 / r1 n=27 −15.6 / r2 n=6 −4.3,CI 不交叠)
      ——「深板扛遭遇」主通道在 encounter 节点以 rung 维为真载体,
      板面件数本身不可兑换伤害减免)。分桶/下探路径与 battle 共式
      (域内缺桶逐级浅侧回退;邻接宽=rung±1)。
    - ``boss``:``key`` = **净星深**(W240/ADR-0404:上场件 Σ(star−1),
      ``deployed_star_depth`` 单一源;旧 Σboard 键与 3合1 升星方向
      冲突——升星使 Σboard −2 落浅桶而浅桶期望伤害更大,sim 判
      「升星→boss 伤害↑」与 [27] 机制相反)。分桶/缺桶浅侧回退
      沿用 depth 桶式。
    - ``reward``/``supply``(ADR-0292,批㉗ F3/F4):depth 桶 + 缺桶
      浅侧回退沿用,再缺 → **该节点全池合并兜底**——奖励/补给零
      战力交互,语料差分无深度条件性(n=43 全 +2),分桶只是沿既有
      维度的载体;不让 r1-r2 浅板深轮退恒常数(池有真值就采样)。
      池空 → None(调用方回退 EARLY_WIN_DELTA)。

    ⓪ 起 pool_map 显式注入(resolve_pool 产物;None=auto 解析,
    缺源 raise 不静默)。

    **防饥饿守卫(ADR-0268,批③ F1)**:命中的桶 n<_BUCKET_MIN_N
    时不裸采样——n=1 的桶(如 battle 桶 6 恒 -11)等于把该深度
    锁死在唯一样本上,任何把板深推过桶边界的策略臂都被系统性
    伪惩罚(深度 6 悬崖)。降级策略:候选 = 本桶∪浅邻桶、本桶∪
    深邻桶、该节点全池均匀,取**方差最小**者采样(合并天然加权,
    样本多的邻桶主导);候选并列时按 浅邻→深邻→全池 序(确定
    性)。无任何可合并邻桶(极端小池)时退回裸样本——守卫降级
    采样,不改变「缺桶 → None」的既有两态语义(depth 路;battle/
    encounter 路的全池兜底见上)。邻接宽随键语义:battle/encounter
    =rung±1,其余=桶宽 ±_DEPTH_BUCKET_W。
    """
    if pool_map is None:
        pool_map = resolve_pool('auto')[0]
    # ADR-0362:位面层解包({节点:{位面:{桶:[Δ]}}});plane≥2
    # 缺桶不跨位面回退(见 docstring)
    _map = (pool_map.get(node_type) or {}).get(plane) or {}
    if node_type in ('battle', 'encounter'):
        # ADR-0279:rung 桶(键域 0-4);v11 起 encounter 同路
        # (ADR-0407:与 battle 同键语义/同下探/同守卫邻接宽)。
        src_b = min(max(int(key), 0), 4)
        while src_b not in _map and src_b > 0:
            src_b -= 1
        samples = _map.get(src_b)
        if not samples:
            # 全池兜底(批⑬ F3):rung 信息缺 → 经验分布整体采样
            samples = [d for v in _map.values() for d in v]
        if not samples:
            return None
        width = 1
    else:
        bucket = min(key // _DEPTH_BUCKET_W, 5) * _DEPTH_BUCKET_W
        src_b = bucket if _map.get(bucket) else bucket - _DEPTH_BUCKET_W   # 缺桶浅侧回退(r343 E)
        samples = _map.get(src_b)
        if not samples and node_type in ('reward', 'supply'):
            # ADR-0292:reward/supply 全池兜底(缺桶不退常数,
            # 语料真值优先;防饥饿守卫照常辖)
            samples = [d for v in _map.values() for d in v]
        if not samples:
            return None
        width = _DEPTH_BUCKET_W
    if len(samples) >= _BUCKET_MIN_N:
        return rng.choice(samples)
    cands: list[list[int]] = []
    for nb in (src_b - width, src_b + width):
        merged_neighbor = _map.get(nb)
        if merged_neighbor:
            cands.append(list(samples) + list(merged_neighbor))
    all_pool = [d for v in _map.values() for d in v]
    if len(all_pool) > len(samples):
        cands.append(all_pool)
    if not cands:
        return rng.choice(samples)

    def _pvar(seq: list[int]) -> float:
        import statistics
        return statistics.pvariance(seq) if len(seq) > 1 else 0.0

    best = min(cands, key=_pvar)
    return rng.choice(best)


def boss_delta(dir_round: int, rng: random.Random,
               multiplier: float = 1.0) -> int:
    """P1 boss(r9)HP 变化(校准层;按方向建立早晚分档)。

    multiplier>1 用于遭遇轮(用户口述:遭遇三四可比 boss 难)。"""
    for cap, base, jitter in BOSS_BY_DIR_ROUND:
        if dir_round <= cap:
            return int(-(base * multiplier
                         + rng.uniform(0, jitter)))
    return int(-(36.0 * multiplier + rng.uniform(0, 10.0)))


def _settle_rung(st: GameState) -> int:
    """ADR-0279:结算时点成型度 rung(boss_settle_delta 与 battle/
    encounter(v11,ADR-0407)Δ池 rung 分桶的采样键**单一源**)。

    口径 = _engines_count(四体系达成数:仙舟3/列车2/DOT2/希儿系),
    输入 = **board 全集口径**(ADR-0312,W50:_recount_board——对齐生产
    outcomes board_before 的全集+星徽口径;旧 _board_factions_of 输入
    缺星徽贡献,星徽局 rung 系统性偏低落错桶)+上场名单(希儿系单卡判据)。
    """
    from sr_od.application.currency_war.cw_state import _recount_board
    _bf = _recount_board(st.deployed)
    _names = frozenset(d.char_id for d in (st.deployed or [])
                       if getattr(d, 'char_id', ''))
    return _engines_count(_bf, _names)


def boss_settle_delta(st: GameState, dir_round: int,
                      rng: random.Random) -> int:
    """ADR-0308:boss Δ池桶不可达时的回退结算(胜负面=W31 阶梯)。

    胜 → ``BOSS_WIN_DELTA`` 小额(掷 ``node_win_p('boss', round)``,
    n=192 实测 0.05);负 → 旧 ``boss_delta`` 档(幅度层保留)。
    旧 rung 条件胜率(ADR-0277/0306 的 0/0/0.25 + rung2 外推)已被
    W31 实测边际替换——语料是旧策略病局镜像,无条件性可标(成型度
    条件性等新策略语料,见 ``NODE_WIN_P_LADDER`` 注释)。
    仅当 ``live_delta_for`` 返 None(无可及桶)时由调用方使用;
    Δ池可及桶命中时经验分布优先(池是实机真值,sim 规则表是补洞)。
    """
    if rng.random() < node_win_p('boss', st.round_num):
        return BOSS_WIN_DELTA
    return boss_delta(dir_round, rng)


def sample_node_sequence(rng: random.Random) -> list[str]:
    """P1 节点序列(r306b 实证统计:25 开局帧众数表)。

    典型表(每帧读全,用户指路):reward/reward/battle/battle/
    supply/battle/encounter/reward/boss——slot1/2/4/7 全帧
    一致(25/25);**slot3/5/6 是变异位**(24/25、23/25、24/25
    主型,余为策略效果改节点:战斗→遭遇/补给)。
    用户定调:位面节点基本固定,特殊策略才改;实机以实时
    识别为权威,本表用于模拟骨架/策略预知(如 r7 遭遇→
    r6 备战破息)。"""
    seq = ['reward', 'reward', 'battle', 'battle', 'supply']
    # slot5(r6):battle 主(23/25),策略效果位
    seq.append(rng.choices(('battle', 'encounter'), (0.92, 0.08))[0])
    # slot6(r7):encounter 主(24/25)
    seq.append(rng.choices(('encounter', 'supply'), (0.96, 0.04))[0])
    seq.append('reward')
    seq.append('boss')
    return seq


def node_delta(node: str, round_num: int, dir_round: int,
               rng: random.Random, *, plane: int = 1) -> int:
    """按节点类型的 HP 变化(r260 分层;ADR-0292 起 reward/supply 的
    **池回退档**——Δ池可及时结算侧优先池采样;ADR-0308 起战斗类
    节点回退档胜负面 = W31 实测阶梯 ``node_win_p``):
    reward/supply 零战力要求 → 不掉血(回退档 +2 长线作战回血观测,
    池真值同分布);
    battle → 阶梯掷胜(W31:n=192,~0.29),胜 WIN_DELTAS/负旧幅度;
    encounter → 阶梯掷胜(0.04),胜 +2/负 boss 档 × ENCOUNTER_MULT
    (档位不可观,均值近似);
    boss → 阶梯掷胜(0.05),胜 +2/负 boss 档。

    plane≥2(ADR-0362,W157):battle 回退档换 **P2 掉血带**——
    胜率 P2_BATTLE_WIN_P(0.11)/负 -15~-17 均匀带(语料 W151,
    P1 阶梯的 r3/r4 战斗胜率与幅度带都不辖 P2);encounter/boss
    沿用 P1 档+标注(P2 语料 3/2 行不足,池可及时优先池采样)。"""
    if node in ('reward', 'supply'):
        return EARLY_WIN_DELTA
    if node == 'encounter':
        if rng.random() < node_win_p('encounter', round_num):
            return EARLY_WIN_DELTA
        return boss_delta(dir_round, rng, multiplier=ENCOUNTER_MULT)
    if node == 'boss':
        if rng.random() < node_win_p('boss', round_num):
            return BOSS_WIN_DELTA
        return boss_delta(dir_round, rng)
    if plane >= 2:
        # ADR-0362:P2 battle 回退档(掉血带 15-17,W151)
        if rng.random() < P2_BATTLE_WIN_P:
            return rng.choice(WIN_DELTAS)
        return -rng.randint(P2_LOSS_BAND[0], P2_LOSS_BAND[1])
    return battle_delta(round_num, dir_round, rng)


def _direction_established(session: StrategySession) -> bool:
    """方向判据 = 策略自身认领(意向锁定),与遥测 target 字段一致。

    ADR-0309 载体批后唯一策略载体 = decision_v2,方向真值在
    ``session.v3_intention`` 意向分层锁定(旧臂 line_v2 的
    locked_line/bridge_id 读取随 ADR-0336 删除)。
    W145/ADR-0357:P1 配方锁(p1_pair 体系对)同构认领方向——
    终局 comp 锁与配方对锁任一成立即方向已立(纯遥测口径)。
    """
    ist = getattr(session, 'v3_intention', None)
    if ist is None:
        return False
    if getattr(ist, 'phase', '') == 'locked' and getattr(ist, 'locked_comp', ''):
        return True
    return bool(getattr(ist, 'p1_pair', ()))


def _target_comp_label(session: StrategySession) -> str:
    """账本 ``target_comp`` 字段(W43 leader 裁决 3):v3 意向。

    decision_v2 栈不写 ``locked_line``/``bridge_id``,意向真值在
    ``session.v3_intention.locked_comp``(COMP_LIBRARY 套名;旧 v1
    字段回退随 ADR-0336 删除)。W145/ADR-0357:P1 配方锁局无 comp 锁,
    标签=``过渡配方·A+B``(体系对;遥测可读性,不进任何决策)。
    """
    ist = getattr(session, 'v3_intention', None)
    if ist is not None:
        locked = getattr(ist, 'locked_comp', '') or ''
        if locked:
            return locked
        pair = getattr(ist, 'p1_pair', ()) or ()
        if pair:
            return '过渡配方·' + '+'.join(pair)
    return ''


def _board_factions_of(deployed) -> dict[str, int]:
    """r394:上场角色的阵营计数(生产 board 口径,flows 并计)。

    「过渡阵容凑到没有」的判据输入:recipe_tier(配方档位)/
    三人组在场上——此前 sim 账本 board 恒空,成型质量不可观测。
    """
    from sr_od.application.currency_war.cw_chars import CHARACTERS as _CH
    out: dict[str, int] = {}
    for d in (deployed or []):
        if d is None:   # ADR-0392 槽位表空槽
            continue
        cid = getattr(d, 'char_id', '') or ''
        ch = _CH.get(cid)
        if ch is None:
            continue
        for f in (ch.factions or ()) + (ch.flows or ()):
            out[f] = out.get(f, 0) + 1
    return out


def _board_counts_of(deployed) -> dict[str, int]:
    """board 全集计数(ADR-0312,W50 口径统一)。

    **= ``cw_state._recount_board`` 本体**(alias import,单一源)——
    旧「主阵营逐件累加」口径已废:state.board 消费方(recipe 门/
    在场阵营集合/意向②信号)此前读的是压掉流派/独立羁绊/
    星徽贡献的窄口径,与实机 board_from_tracked(左面板真值)系统性
    分叉(W49 Q4)。未识别(char_id 空)回退 faction 字段(生产 OCR
    空板同形)。"""
    from sr_od.application.currency_war.cw_state import _recount_board
    return _recount_board(deployed)


def _first_tier_round(res, tier: int) -> int | None:
    """r394:配方档位首达轮(ledger 的 board_factions 逐轮查
    recipe_tier≥tier 的最小轮;查不到=None)。"""
    from sr_od.application.currency_war.cw_line_defs import recipe_tier
    for row in res.ledger:
        bf = (row.get('state') or {}).get('board_factions') or {}
        if bf and recipe_tier(bf) >= tier:
            return row.get('round_num')
    return None


def _first_trio_round(res, target: int) -> int | None:
    """r394:核心三人组上场首达轮(deployed∩_CORE_TRIO 计数
    ≥target 的最小轮;查不到=None)。"""
    from sr_od.application.currency_war.cw_line_defs import _CORE_TRIO
    for row in res.ledger:
        dep = (row.get('state') or {}).get('deployed') or []
        cnt = sum(1 for d in dep
                  if d.get('char_id') in _CORE_TRIO)
        if cnt >= target:
            return row.get('round_num')
    return None


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
# W47 统一化:``_TRANSITION_TRAITS`` 改 alias import 自模块头
# (``cw_deploy_logic.TRANSITION_TRAITS``,其本体已从 SYSTEM_CARDS 派生,
# 单一源;原先两模块各写一份同值常量对、注释互指——漂移窗口=任一侧单改)。
# 消费本名的 scoring._engine_frac_remainder 等 import 路径不变。


def _engines_count(board_factions: dict[str, int],
                   deployed_names: frozenset[str] | set[str] = frozenset()
                   ) -> int:
    """过渡体系达成数(三选几+希儿系;两两组合=过渡成型)。

    r399:希儿系=希儿在场 AND(量子同频≥2 OR 贝洛伯格≥2)——
    与三羁绊同级可组合(列车2+希儿系 13 帖/仙舟+希儿系 3/DOT+希儿
    系 2/量贝同开 6)。
    """
    n = sum(1 for bond, tier in _TRANSITION_TRAITS
            if board_factions.get(bond, 0) >= tier)
    seele = ('希儿' in deployed_names
             and (board_factions.get('量子同频', 0) >= 2
                  or board_factions.get('贝洛伯格', 0) >= 2))
    if seele:
        n += 1
    return n


def _transition_formed(board_factions: dict[str, int],
                       deployed_names: frozenset[str] | set[str] = frozenset()
                       ) -> bool:
    """过渡阵容成型判据(transition_combos.md 2026-08-23 定稿):

    四种体系(仙舟3/列车2/DOT2/希儿系)**两两组合**=成型
    (三选二 140/328 帖;希儿系×三过渡 18 帖);
    单个体系点火不等于成型(门槛低的体系如 DOT2 可单独当起点)。
    """
    return _engines_count(board_factions, deployed_names) >= 2


def _first_engines_round(res, target: int) -> int | None:
    """r399:过渡体系达成数首达 target 的最小轮。

    判据走 _engines_count(四体系:仙舟3/列车2/DOT2/希儿系各算一个;
    希儿系需 deployed 含希儿——ledger 的 state.deployed 提供名单);
    target=2=过渡成型(两两组合),target=1=单体系点火
    (门槛低的体系如 DOT2 可单独当起点)。
    """
    for row in res.ledger:
        st = row.get('state') or {}
        bf = st.get('board_factions') or {}
        dep = frozenset(d.get('char_id', '')
                        for d in (st.get('deployed') or []))
        if bf and _engines_count(bf, dep) >= target:
            return row.get('round_num')
    return None


def _battles_before_engines(res, target: int = 2) -> int | None:
    """ADR-0305 件2(口径修正):首达 target 引擎数前经历的战斗结算数。

    背景:0304 附带观察「v1 到达 rung2 的战斗轮次 30 vs v2 10」的
    口径未在代码定义(一次性诊断数字),0305 复测(20 局配对,seed
    500-519)两臂几乎相等(53 vs 50)——该数字不可再引用。本函数
    把口径钉死:**hp_events 中 round < _first_engines_round(target)
    的战斗类节点(battle/encounter/boss)计数**;未达 target 返 None
    (与 _first_engines_round 同 None 语义,均值只对达成局算)。
    """
    e2 = _first_engines_round(res, target)
    if e2 is None:
        return None
    return sum(1 for rn, nt, _, _ in res.hp_events
               if rn < e2 and nt in ('battle', 'encounter', 'boss'))


def _deployable_depth(st: GameState) -> int:
    """板深 = **Σboard(全集口径)**(ADR-0312,W50 桶键统一)。

    池语料的板深 = decisions 行 state.board 求和(实机全集口径,双标签
    角色每人贡献 ≥2)——sim 采样键旧用 ``min(level, len(deployed))``
    与池语料不同口径:同一局面在池里落深桶、sim 查询落浅桶,采样系统性
    偏向低桶/miss(W49 Q4「隐患最重的消费端缺陷」)。本函数是 Δ 池采样
    键/depth_trail/账本 depth 的单一源,与池语料同口径(Σboard,不加
    level 上限——池侧同样无上限,桶键在 live_delta_for 侧统一分桶)。
    r390 的「读 deployed 不数 bench」语义由 board=_recount_board
    (deployed 派生)间接保留。
    **辖域(v11 后)**:reward/supply 桶键与观测面(depth_trail/账本);
    boss 桶键=净星深(W240/ADR-0404,deployed_star_depth);encounter
    桶键=rung(v11/ADR-0407,_settle_rung 同源;depth 键下期望伤害
    真平——W248「主通道断裂」的 encounter 维由扩容+键查证裁决:
    板深维不可兑换,rung 维可辨)。
    """
    return sum((st.board or {}).values())


def _roll_rotation(rng: random.Random, level: int) -> dict[int, float] | None:
    """本备战期轮岗事件(ADR-0286/批㉓ F4):概率 ROTATION_CHANCE 掷中 →
    随机一档(基线 0<p<0.5 才可能被翻倍)×2 → 完整概率表;
    未掷中/该等级无可翻倍档 → None(基线表,生产「未读到概率条」同态)。"""
    if rng.random() >= ROTATION_CHANCE:
        return None
    base = REFRESH_PROB.get(level, {})
    tiers = [c for c, p in base.items() if 0 < p < 0.5]
    if not tiers:
        return None
    return rotation_probs(level, rng.choice(tiers))


def simulate_p1(seed: int, *, use_refresh: bool = True,
                strategy=None, session=None,
                pool: str | Path = 'auto',
                diamond_cap_prob: float = 0.0,
                config=None,
                planes: int = 1,
                invest: SimInvestProfile | bool = False,
                p2_combat: P2CombatCalib | None = None,
                _p2_entry: P2ReplayEntry | None = None) -> SimResult:
    """单局位面段模拟(决策跑真策略代码;P1 段为主,``planes>=2``
    追加 P2 段——W157/ADR-0362 案 a 最小可用)。

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
    :param diamond_cap_prob: 财富宝钻获取通道(ADR-0286/批㉔ F4):每备战期
        以此概率获得 1 颗财富宝钻(cap = level + 宝钻数,可叠加)。**注入频率
        待实机语料统计,默认 0 = 通道建好但不注入**(baseline 与旧树可配对)。
    :param config: 策略配置桩(默认 None)。decision_v2 栈不读 config;
        A/B 对照臂 default 栈(DefaultCwStrategy)需要
        ``faction_priority``/``character_priority`` 等字段——对照
        runner 传 SimpleNamespace 桩(ADR-0336 对照臂方案)。
    :param invest: 投资策略/环境注入(W162/ADR-0364;默认 False =
        不注入,**主路径逐位零漂移**)。True = 按 seed 确定性采样
        (plaza 实选频次表,见 cw_sim_invest);传 ``SimInvestProfile``
        = 固定剧本(测试/A-B 配对臂)。注入写 session+state 的
        active_strategies/active_env(实机 handler 语义),经济聚合
        (economy_effect_of 链的已建模子集)在 sim 收入/刷价层生效,
        意向层①资格通道(ADR-0338)因此可点火。
    :param p2_combat: P2 战斗存活层参数族(W193/ADR-0377;None=模块
        默认 ``P2_COMBAT_DEFAULT``)。``calibrated=False`` 臂逐位回
        W157/ADR-0362 行为(Δ池 plane=2 优先 + 恒值回退档)——A/B
        与回退对照臂;planes=1 路径不消费本参数(零漂移)。
    :param _p2_entry: 案 b 臂进场态注入(内部参数;``simulate_p2_replay_entry``
        构造——跳过 P1 段与开局 bench 采样,直接从真值进场态跑 P2 段。
        共享本函数的 P2 段循环体 = 单一源,W186 设计 §4 的消复制形态)。
    """
    from sr_od.application.currency_war.decision_v2.strategy import (
        DecisionV2Strategy,
    )
    if planes not in (1, 2):
        raise ValueError(
            f'planes 参数非法: {planes}(1=P1 段;2=P1+P2 段,ADR-0362;'
            'P3 语料零样本未实现——案 c 缓,W156 裁决)')
    pool_map, pool_fp, pool_src = resolve_pool(pool)
    rng = random.Random(seed)
    cards_pool = _Pool(rng)   # 命名避参数遮蔽(审查 minor:pool 参数)
    # ADR-0272:池构造后硬断言无费用截断(不变式;检查函数单一源
    # 在 cw_sim_checks——纯 dict 入参,不构成 import 环)
    from sr_od.application.currency_war.cw_sim_checks import (
        check_sim_pool_no_cost_truncation as _chk_pool,
    )
    if _chk_pool(cards_pool.copies)['violations']:
        raise RuntimeError(
            'sim 牌池被费用截断(4/5 费角色缺失)——ADR-0272 禁止;'
            '检查 cw_sim._Pool 构造')
    nodes = sample_node_sequence(rng)   # r260:本局节点序列(9 项)
    strat = strategy or DecisionV2Strategy()
    if _p2_entry is not None:
        # W193/ADR-0377 案 b 臂:P1 段与开局 bench 采样跳过,直接从
        # 真值进场态起跑(rng 不耗 nodes/bench 采样——进场态是外生
        # 真值,重放可复现性 = seed + 进场态 + 池指纹)。下方**共享**
        # 位面段循环体(单一源;与 simulate_p1 主入口零复制)。
        if invest:
            raise ValueError('案 b 臂(_p2_entry)不支持 invest 注入')
        st = _p2_entry.build_state()
        sess = session or StrategySession()
        sess.v2_state = ('economy', False, False, 0, 0, 0, 0, 0)
        streak = _p2_entry.streak
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
    # W162/ADR-0364:投资注入剧本解析(独立 rng 流,默认 False 零开销)。
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
    # ADR-0286(批㉔ F4):财富宝钻通道(注入频率参数化,默认 0 不注入)
    _diamonds = 0
    # ADR-0362(W157):位面段迭代——P1 段(9 轮)后按 ``planes``
    # 追加 P2 段(7 轮)。planes=1 时段表只含 P1 段,循环体逐位
    # 同旧(RNG 消耗序不变 = P1 零漂移回归门)。案 b 臂(W193)段表
    # 只含 P2 段(直接从真值进场态起跑)。
    _ts = 0   # 单调轮序号(跨位面累计;P1 段恒 == rn)
    if _p2_entry is not None:
        _segments: list[tuple[int, int, list[str]]] = [
            (2, P2_ROUNDS, list(P2_NODE_SEQUENCE))]
    else:
        _segments = [(1, 9, nodes)]
        if planes >= 2:
            _segments.append((2, P2_ROUNDS, list(P2_NODE_SEQUENCE)))
    # W193/ADR-0377:P2 战斗存活层参数族(单一注入点;None=模块默认)
    _p2c = p2_combat if p2_combat is not None else P2_COMBAT_DEFAULT
    for _seg_plane, _seg_rounds, nodes in _segments:
        if _seg_plane >= 2:
            # 进场继承块(ADR-0362):P1 末态 hp/gold/board/bench/
            # deployed/equips/意向**原样带过**——HP 跨位面继承是
            # 用户纠错真值(2026-08-23,economy.md §10.2);金/board/
            # equips 跨位面无重置证据,按全继承+标注假设(W156 表
            # #4)。决策代码 plane-aware:p1_pair 进 P2 由意向层
            # 自动清(cw_intention,ADR-0357),策略层零改动。
            st.plane = _seg_plane
            res.p2_entered = True
            # 生产语义对齐:开局帧槽序表写 session(prep_director
            # 首帧写;battles_left_p2 消费,ADR-0361)
            sess.plane_node_table = list(nodes)
            # ADR-0368(W169):位面日程真值序列(生产=prep_director 每位面
            # 首帧 append;sim P1 段不写表 → 进场补记 P1 真值 9,保
            # seen 序=位面序;cw_horizon.schedule_of 消费)
            sess.plane_node_table_plane = _seg_plane
            _seen = sess.plane_lengths_seen
            if _seen is None:
                _seen = []
                sess.plane_lengths_seen = _seen
            from sr_od.application.currency_war.cw_horizon import (
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
            # W193/ADR-0377:事件金双臂(K3 零样本敏感性)——'zero' 臂
            # P2 段事件金归零;rng 照耗(双臂同 seed 配对可比)。
            if st.plane >= 2 and _p2c.event_gold == 'zero':
                _inc_event = 0
            # W162/ADR-0364:注入策略的经济聚合(economy_effect_of 链已建模
            # 子集)——息帽覆写 + 每节点给金。无 active_strategies 时表达式
            # 与旧逐位相同(零漂移);'invest' 键只在有持卡时才加(账本行
            # 形状对默认路径不变)。
            _agg_inv = (aggregate_economy(st.active_strategies)
                        if st.active_strategies else None)
            _icap = INTEREST_CAP
            if _agg_inv is not None and _agg_inv.interest_cap_override is not None:
                _icap = _agg_inv.interest_cap_override
            _inc = {'base': BASE_INCOME,
                    'interest': min(_icap, st.gold // 10),
                    # W129(ADR-0351;实机裁决 2026-08-26):奖励/补给节点不发
                    # 连胜金——run13 r2 奖励结算屏=基础5+连胜×0(无 streak 分量);
                    # 战斗轮 counter0 照发 table[0]=1(run15 r3=5+3+1)。
                    'streak': 0 if nodes[rn - 1] in ('reward', 'supply')
                    else streak_gold(streak),   # 单一源 cw_economy(r305)
                    'event': _inc_event}
            if _agg_inv is not None and _agg_inv.gold_per_node:
                _inc['invest'] = _agg_inv.gold_per_node
            st.gold += sum(_inc.values())
            # W162/ADR-0364:本轮策略选卡注入(overlay 在备战期出现 → 收入
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
            # ADR-0286(批㉔ F4):宝钻通道(默认 prob=0 不掷,保 baseline 可配对)
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
            _bench_full_skips = 0   # ADR-0283:本轮超容被守卫跳过的买(账本 sim 披露)
            _bench_full_skip_gold = 0   # ADR-0285:守卫拦截买折算金(净滞留口径)
            _phantom_rebuys = 0   # ADR-0284:已消费槽/店外买提案数(应恒 0)
            # 动作 v2(契约包 C1,步2):本轮策略是否发出**且被应用**的显式部署
            # 动作(SellDeployed/SwapDeploy/CompTransaction)——是则轮末围栏
            # 跳过自动部署并记 skip_fence(裁决1:显式>围栏,同轮互斥;
            # W65/ADR-0323:被拒事务不置位,围栏照跑)
            _explicit_deploy_seen = False
            _acts: list[dict] = []
            _segs_used = 0
            # ADR-0343:成型停手轮内 OR 聚合——一轮多决策段,演进事务可
            # 轮中改变板面使成型态中途点亮(段前的买入合法);行标志=
            # 「本任一段曾处于停手态」(检查器豁免消费:有买的轮本就
            # 不进 streak,OR 只会多豁免「全轮零买且曾成型」的轮=停手线
            # 语义正确辖域)
            _round_formed_stop = False
            # W227/ADR-0400:P1 末窗承接门缺口观测(轮入口首段快照;
            # formed_stop 承接维/EV 缺口项的判读数据面)
            _round_handoff_gap = 0
            # W238/ADR-0403:boss 投影 hp 披露(None=投影关/非末窗)
            _round_handoff_hp_proj = None
            # W52(ADR-0326):本轮补偿放弃信号快照——决策段后对比计数增量,
            # 进账本 sim.remedy_abandoned(检查项 decision_v2_remedy_loop
            # 的「连续放弃轮」数据源)
            _remedy_abandons_before = getattr(sess, 'v3_remedy_abandoned', 0)
            # W114/ADR-0346 相位影子观测:轮入口(首决策段)快照——与生产
            # 「每轮决策入口计算一次」对齐;一轮多决策段时取首段(轮初态)。
            _round_phase: str = ''
            _round_form_ok: bool = False
            _round_form_score: float = 0.0
            _round_dp_posture: str = ''
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
                strat.update_target(st, sess, config)
                acts = strat.decide_prep(st, sess, config)
                _round_formed_stop = _round_formed_stop or bool(
                    getattr(sess, 'v3_formed_stop', False))
                if not _phase_snap:
                    _phase_snap = True   # 轮入口首段快照(W114 影子)
                    _round_phase = str(getattr(sess, 'v3_phase', '') or '')
                    _round_form_ok = bool(getattr(sess, 'v3_form_ok', False))
                    _round_form_score = round(float(
                        getattr(sess, 'v3_form_score', 0.0) or 0.0), 3)
                    # W119/ADR-0347 授权依据 trace:当轮 DP 姿态 tag
                    _round_dp_posture = str(getattr(getattr(
                        getattr(sess, 'v3_dp_posture', None),
                        'posture', None), 'tag', '') or '')
                    # ADR-0348 ↺:扑满节点识别标记(遥测数据面)
                    _round_piggy = bool(getattr(sess, 'v3_piggy_reward',
                                                False))
                    # W227/ADR-0400:承接门缺口(filters.formed_stop_
                    # active 写;轮入口快照,判读「门扣住哪些轮」)
                    _round_handoff_gap = int(
                        getattr(sess, 'v3_handoff_gap', 0) or 0)
                    # W238/ADR-0403:boss 投影 hp 同点快照(投影开时非 None)
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
                        # W162/ADR-0364:策略免费刷额度(如 加油站 每节点
                        # 1 次;cw_economy._refresh_cost 同语义)——额度内
                        # 刷价 0。无持卡/无额度时与旧逐位相同。
                        if _free_r and _free_used < _free_r:
                            _cost_r = 0
                            _free_used += 1
                        st.gold -= _cost_r
                        _spend['refresh'] += _cost_r
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
                        # ADR-0283(批⑰ F6):生产 bench 满 = 硬模态拒买
                        # (ADR-0136;cw_identity_obs「备战席已满」球点不动),
                        # sim 旧无守卫 → 单轮 4-8 连买把 bench 顶到 11-17
                        # (批⑰ 3/300 局)——满仓局的买门/腾位门读的是生产
                        # 不可能出现的状态。守卫:合并域(bench+deployed,
                        # _merge_bench 全场域)中 bench 槽为约束——deployed
                        # 不占备战槽,故判据 = 占用数 ≥ BENCH_CAPACITY(9,
                        # ADR-0316 槽位表);超容买跳过(金/牌池均不消费)+
                        # 计数披露。
                        if bench_occupied(st.bench) >= BENCH_CAPACITY:
                            _bench_full_skips += 1
                            _bench_full_skip_gold += a.card.cost
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
                        from sr_od.application.currency_war.cw_line_defs import (
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
                        # W65 修法3(ADR-0323):``_explicit_deploy_seen`` 移到
                        # 下方 applied 分支置位——**只有真执行(未被拒)的显式
                        # 动作才占显式通道**;被拒事务不消耗围栏(围栏跳过语义
                        # 修正,同轮围栏照跑,板面欠载不再被事务风暴封死;W64
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
                        # W101:applied 事务的 bench 净腾位数(执行点真值;账本
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
                            # W65 修法3(ADR-0323):显式动作**真执行**才置位
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
                            # W43 leader 裁决 2(phantom_rebuys 根治):事务
                            # fill 已消费店槽——同批后续 BuyCard 是对陈旧
                            # state.shop 的提案,作废并立即重决策(同
                            # RefreshShop 的 break-redecide 语义),不套用
                            # 陈旧引用。
                            break
                if not progressed:
                    break
            while st.level < 9 and xp >= XP_TO_NEXT_LEVEL.get(st.level, 999):
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
            from sr_od.application.currency_war import cw_deploy_logic as _dl
            _tf, _tc, _fw = frozenset(), frozenset(), frozenset()
            # W155/ADR-0360 件4:锁定帧体系键并入围栏放行集(同生产 op 侧)
            _lf = frozenset()
            try:
                _tc = frozenset(getattr(sess, 'target_comp', None).core_chars
                                or ()) if getattr(sess, 'target_comp', None) else frozenset()
                _tf = frozenset(getattr(sess, 'target_comp', None).factions
                                or ()) if getattr(sess, 'target_comp', None) else frozenset()
                _fw_name = getattr(sess, 'transition_framework', '') or ''
                _fw = frozenset()
                if _fw_name:
                    from sr_od.application.currency_war.cw_transition import (
                        TRANSITION_PACK,
                    )
                    _fw = frozenset(
                        n for n, (f, t) in TRANSITION_PACK.items()
                        if (f == _fw_name or f == '通用') and t != 'drop')
                from sr_od.application.currency_war.cw_intention import (
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
            # check_skip_fence_pairing 同轮配对锁;W65/ADR-0323:被拒事务
            # 不置位 → 不跳围栏 → 板面欠载不再被事务风暴封死)。
            _deploy_lag_units = 0
            if _explicit_deploy_seen:
                _acts.append({'__type__': 'skip_fence',
                              'reason': 'explicit_action_v2'})
                res.fence_skips += 1
                # board 已由 cw_state.simulate 的 _recount_board 维护一致
            else:
                # ADR-0316:select_deployments 吃**紧缩占用序**(None 槽剔除;
                # 返回 up_idx 是占用序下标,下方回映射槽位下标)
                _occ_idx = [i for i, b in enumerate(st.bench) if b is not None]
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
                # ADR-0287(批㉘ 检查项 ledger_deploy_lag_disclosure):部署后
                # 重放围栏,残留可上件数入账本(deploy_lag_units)——部署时序
                # 回归(未来重构再犯轮首序/围栏漏上)可被 checks 常态扫出;
                # 买后部署语义下应恒 0(>0 = 本轮末仍有围栏认可的可上件)。
                _lag_idx, _ = _dl.select_deployments(
                    [b for b in st.bench if b is not None],
                    deployed_cids={d.char_id
                                   for d in iter_occupied_deployed(st.deployed)
                                   if d.char_id},
                    deployed_fac=_board_factions_of(st.deployed),
                    board=dict(st.board),
                    cap=st.max_units(),
                    target_factions=_tf,
                    target_cores=_tc,
                    fw_carry=_fw,
                )
                _deploy_lag_units = len(_lag_idx)
            if res.dir_round == 99 and _direction_established(sess):
                res.dir_round = rn
            # W162/ADR-0364:P1 段锁定轮计数(①资格通道激活直证——
            # 注入前语料下 P1 恒 unlocked/p1_pair,此键恒 0[W161])
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
            # boss 键=净星深(W240/ADR-0404,修升星方向冲突)。
            _dep = _deployable_depth(st)
            # W193/ADR-0377:参数化校准层辖 plane≥2 战斗类结算——绕过
            # Δ池 plane=2 合并采样(防饥饿守卫已抹平其条件性,ADR-0362
            # 判「假条件化」;Phase 3 桶键 form×round 到量[n≥5]后让位
            # 池采样)。calibrated=False = 逐位回 W157 路径(池优先 +
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
                if nodes[rn - 1] == 'battle':
                    _ld = live_delta_for('battle', _settle_rung(st), rng,
                                         pool_map=pool_map, plane=st.plane)
                elif nodes[rn - 1] == 'boss':
                    # W240/ADR-0404:boss 采样键=净星深(修 Σboard 升星
                    # 方向冲突,见 live_delta_for docstring)。
                    _ld = live_delta_for(
                        'boss', deployed_star_depth(st), rng,
                        pool_map=pool_map, plane=st.plane)
                elif nodes[rn - 1] == 'encounter':
                    # v11/ADR-0407:encounter 采样键=rung(与 battle 同源
                    # _settle_rung——depth 键下期望伤害真平,W250 查证;
                    # live_delta_for 桶缺逐级下探路径与 battle 共用)。
                    _ld = live_delta_for('encounter', _settle_rung(st), rng,
                                         pool_map=pool_map, plane=st.plane)
                elif nodes[rn - 1] in ('reward', 'supply'):
                    # ADR-0292(批㉗ F3/F4):reward/supply 由恒 EARLY_WIN_DELTA
                    # 改 Δ池经验分布采样(语料真值;F4 胖尾经复核为跨 run 配对
                    # 伪影,真值分布 = 恒 +2,采样口径保语料增长自动跟真)。
                    # 池缺 → live_delta_for None → node_delta 回退常数。
                    _ld = live_delta_for(nodes[rn - 1], _dep, rng,
                                         pool_map=pool_map, plane=st.plane)
                else:
                    _ld = None
                if _ld is not None:
                    delta = _ld
                elif nodes[rn - 1] == 'boss':
                    # ADR-0277(批⑪ F1/F2 同根):boss Δ池桶不可达的回退路径
                    # 加胜分支——胜率=f(成型度),成型→少掉血→胜 boss 的
                    # 价值链接通(hp 类指标恢复判读力)。
                    delta = boss_settle_delta(st, res.dir_round, rng)
                else:
                    delta = node_delta(nodes[rn - 1], rn, res.dir_round, rng,
                                       plane=st.plane)
            # 批㉘ F6(ADR-0287,hp_upper_bound_truth):HP 结算加上界钳制。
            # 游戏机制真值未见文档证据(语料 max hp_after=88 / sim max 92
            # 均未触界,非 cap 证明)——暂按 cap 100 钳制;批㉗ reward
            # 胖尾(+20~39 回血)落地后 hp 破百的担忧已随 ADR-0292 复核
            # 消解(胖尾为跨 run 配对伪影,池真值恒 +2,实测触界率 0),
            # 钳制维持(防御性不变式);实机满血样本核真后更新本常量
            # (检查项 hp_upper_bound_truth 锁 hp>100 恒 0)。
            st.hp = max(0, min(HP_UPPER_BOUND, int(st.hp + delta)))
            # W129(ADR-0351;实机裁决 2026-08-26):奖励/补给节点既不计连胜数
            # 也不发连胜金——run13 r1/r2 奖励全过后计数仍 0(r2 结算屏连胜×0),
            # run15 r3 战斗轮按 counter0 结算。战斗类节点(battle/encounter/
            # boss)胜后计数+发金语义不变(delta>0 计连胜)。
            if nodes[rn - 1] in ('battle', 'encounter', 'boss'):
                streak = streak + 1 if delta > 0 else 0
            # 批⑤ F4(ADR-0276):结算补写 session.last_streak——生产语义
            # = 结算「连胜×N」写 session(default_strategy.on_settlement),
            # r308 保连胜门/evaluate 连胜响应消费读 session;sim 旧连胜
            # 只存本地变量算收入,决策侧连胜响应恒盲。
            sess.last_streak = streak
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
            # 装备获取采样:通用装备池按 _EQUIP_VALUE 键(注册表过滤,
            # ADR-0294 件2,见下);带钻概率 15%(实机简报词缀影响的
            # 粗估,校准点)。r388 类 bug(开局乱穿)从此 sim 可见。
            # ADR-0294 件2(ADR-0289 §5 裁决,红项 174/300):采样池
            # 只进注册表认识的装备名(EQUIPMENT_ROSTER 单一源)——
            # '未知装备' 与价值表旧名(注册表外)不进 owned 池;带钻
            # 是词缀元数据,不再以 '钻石' 占位实体进池(占位实体只进
            # 披露计数 res.phantom_supply_picks,不进池)。
            _equipped_now: list[tuple[str, str]] = []
            if nodes[rn - 1] == 'supply':
                from sr_od.application.currency_war.cw_equipment_data import (
                    EQUIPMENT_ROSTER,
                )
                from sr_od.application.currency_war.cw_events import (
                    _EQUIP_VALUE as _EV,
                )
                from sr_od.application.currency_war.cw_events import (
                    SupplyOption,
                    decide_supply,
                )
                _pool_names = [n for n in _EV if n in EQUIPMENT_ROSTER]

                def _sample_supply_opts(
                        _names: list[str]) -> list[SupplyOption]:
                    # 发放采样(3 列;带钻 15% 粗估校准点)——两步各自
                    # 调用一次,消耗局内 rng 流(W212 批 monkeypatch 臂
                    # 用独立 rng 是补丁层限制,原生实现必须走局内 rng
                    # 才与实机发放分布一致)
                    return [SupplyOption(
                        idx=_oi, char='', equip=rng.choice(_names),
                        has_diamond=rng.random() < 0.15)
                        for _oi in range(3)]

                # W213/ADR-0394:生产 RunSupplyNode 是真两步——
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
                _opts = _sample_supply_opts(_pool_names)
                _pick = decide_supply(_opts, st, sess.target_comp, None,
                                      refresh_used=sess._supply_refresh_used)
                if _pick.refresh and not sess._supply_refresh_used:
                    sess._supply_refresh_used = True
                    _opts = _sample_supply_opts(_pool_names)
                    _pick = decide_supply(_opts, st, sess.target_comp, None,
                                          refresh_used=True)
                st.equips.append(_opts[_pick.idx].equip)
                if _pick.idx < len(_opts) and _opts[_pick.idx].has_diamond:
                    res.phantom_supply_picks += 1   # 披露计数(不进池)
            if st.equips and deployed_occupied(st.deployed):   # ADR-0392 占用数(定长表恒真值)
                from sr_od.application.currency_war.cw_comps import (
                    equip_allocation,
                )
                # W212/ADR-0393:补齐 equip_allocation 生产调用形态——
                # ① plane 从 st.plane 现读(生产 EquipAll 从 last_state 读,
                # 见 equip_all M7 调用点;旧 sim 漏传 = 恒按默认 plane=1,
                # ADR-0391 死库存回收去向(P2/P3 生效)与 P2 组件放行在
                # sim 从未点火);② occupied = 画面已穿(生产 occupied_m7
                # 同语义;旧 sim 恒 None → 配对守卫看不见历史已穿,只看得
                # 见本趟内部分配,跨轮守卫形同虚设)。BenchChar.equips
                # (r393 写回)即跨轮已穿真值。
                _occupied: dict[tuple[str, int], list[str]] = {}
                for d in iter_occupied_deployed(st.deployed):
                    _occupied[(getattr(d, 'position_pref', '') or '',
                               int(getattr(d, 'slot', 0) or 0))
                              ] = list(getattr(d, 'equips', ()) or ())
                _equipped_now = equip_allocation(
                    sess.target_comp, st.deployed, list(st.equips),
                    occupied=_occupied, plane=st.plane)
                for _who, _what in _equipped_now:
                    if _what in st.equips:
                        st.equips.remove(_what)
                    # ADR-0312(W50 L2 雏形):分配结果同步写回 BenchChar.equips
                    # ——星徽/卡带的羁绊贡献随 unit_bond_tags 进 board(生产
                    # tracked_deployed[].equips 同语义);防重守卫(跨轮对同一
                    # 人重复分配同一件不双记)。
                    for d in iter_occupied_deployed(st.deployed):
                        if d.char_id == _who:
                            if _what not in d.equips:
                                d.equips.append(_what)
                            break
            from sr_od.application.currency_war.cw_line_defs import (
                core_count_for,
            )
            res.ledger.append({
                'ts': _ts,   # 单调轮序号(跨位面累计;P1 段 == rn;审查①#9)
                'plane': st.plane, 'round_num': rn,
                'gold': st.gold, 'hp': st.hp,
                # ADR-0343:成型停手态入账本(轮内 OR 聚合;检查器豁免/判读锚点数据源)
                'formed_stop': _round_formed_stop,
                # W227/ADR-0400:末窗承接门缺口(0=不辖/达标;判读承接维
                # 触发面;与 formed_stop=False 并读 = 门扣住证据行)
                'handoff_gap': _round_handoff_gap,
                # W238/ADR-0403:boss 投影 hp(None=投影关/非末窗;判读
                # 「boss 后投影 hp」面,与 handoff_gap 同点快照)
                'handoff_hp_proj': _round_handoff_hp_proj,
                # W114/ADR-0346 相位影子观测(轮入口快照;零消费)
                'phase': _round_phase,
                'form_ok': _round_form_ok,
                'form_score': _round_form_score,
                'dp_posture': _round_dp_posture,
                'piggy_reward': _round_piggy,
                # W146 v3 意向状态(与生产 decisions 行同构;sim 分析批
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
                                     'slot': b.slot}
                                    for b in iter_occupied(st.bench)],
                          # r391(执行层代理配套):deployed/cap 入账本
                          # ——「开局 deploy<cap」检查项的数据源
                          # (r387 类 bug 的 sim 常态化防线)。deployed
                          # 形状对齐 rounds 视图消费(dict 带
                          # position_pref,同 bench 形状)。
                          'deployed': [{'char_id': d.char_id,
                                        'faction': d.faction,
                                        'slot': d.slot,
                                        'star': int(getattr(d, 'star', 1) or 1),   # W88/ADR-0339:星级入账本(2★ 达成率度量)
                                         'position_pref': d.position_pref,
                                        # ADR-0312(W50):装备随人进账本——
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
                          'owned_equips': list(st.equips)},
                'actions': _acts,
                'sim': {
                    'node': nodes[rn - 1], 'delta': delta,
                    # W193/ADR-0377:参数化胜率披露(校准层结算行;
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
                    # ADR-0283(批⑰ F6):本轮 bench 满被守卫跳过的买次数
                    # (0=常态;>0 = 决策层在非法状态上想买,判读买门时须知)
                    'bench_full_skipped_buys': _bench_full_skips,
                    # ADR-0285(批㉑ F3/F5):守卫拦截买折算金(净滞留口径
                    # = 末金 − 本值;判读区分「策略滞留」vs「守卫拦截」)
                    'bench_full_skipped_gold': _bench_full_skip_gold,
                    # ADR-0284(批㉒ F1):本轮幻影再买提案数(已消费槽/
                    # 店外;真策略批次应恒 0,检查项归 0 锁)
                    'phantom_rebuys': _phantom_rebuys,
                    # ADR-0287(批㉘ F1):本轮末重放围栏的残留可上件数
                    # (买后部署语义下应恒 0;检查项 deploy_after_buy_
                    # semantics / ledger_deploy_lag_disclosure 的数据源)
                    'deploy_lag_units': _deploy_lag_units,
                    # 动作 v2(契约包 C1):本轮围栏是否被显式动作跳过
                    # (skip_fence 账本行的 sim 侧披露;checks 配对锁数据源)
                    'fence_skipped': _explicit_deploy_seen,
                    # W52(ADR-0326):本轮补偿趟是否放弃(0/1;连续放弃轮
                    # ≥3 由检查项 decision_v2_remedy_loop 报警——设计容量
                    # 不足信号)
                    'remedy_abandoned': 1 if getattr(
                        sess, 'v3_remedy_abandoned', 0)
                        > _remedy_abandons_before else 0,
                },
            })
            if st.hp <= 0:
                break
        # W213/ADR-0394:P1 段出口 key_equips 命中度量段末快照
        # (无论 P1 段是打满还是中途死亡都记;口径见 SimResult
        # 字段注释)。段内变量 _seg_plane 在此可见(for 循环变量)。
        if _seg_plane == 1:
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
            # 口径与 W212 批 A 一致:命中 = Σ min(需求份数, 持有份数)
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
    # W193/ADR-0377:P2 判读同构观测(headline/账本扩展)——由账本
    # plane=2 行派生(金带走量/carry 笔数价格带/意向切换/lv 到达轮)。
    if res.p2_entered:
        res.p2_combat_calibrated = _p2c.calibrated
        # W224/ADR-0399:承接快照披露(策略 decide_prep 位面首帧块写
        # session.v3_handoff——案 b 臂同样经首轮 decide_prep 采样)。
        _h = getattr(sess, 'v3_handoff', None)
        res.p2_handoff = _h.as_dict() if _h is not None else None
        _p2_rows = [row for row in res.ledger
                    if (row.get('plane') or 1) == 2]
        if res.p2_hp0:
            # 金带走量:死在 P2 段时的末金(活过 P2=None——W183 D1)
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
        # W162/ADR-0364:注入观测(实际持有序 = session 真值,含去重)
        res.invest_strategies = tuple(sess.active_strategies)
    return res


@dataclass
class P2ReplayEntry:
    """案 b 臂真值进场态(W193/ADR-0377;``simulate_p2_replay_entry``
    的输入)。

    字段来源 = 生产 replay decisions 的 plane=2 首行 state(锚脚本
    构造);bench/deployed 为 dict 列表(char_id/faction/star/
    position_pref/equips),与生产遥测同构。有限牌池消费态不可观
    (W186 表 #4 K4)→ 满池假设 + 标注。
    """

    hp: int
    gold: int
    level: int
    board: dict[str, int] = field(default_factory=dict)
    bench: list[dict] = field(default_factory=list)
    deployed: list[dict] = field(default_factory=list)
    equips: list[str] = field(default_factory=list)
    xp: int = 0
    xp_progress: tuple[int, int] | None = None
    streak: int = 0
    locked_comp: str = ''

    @staticmethod
    def _unit(u: dict, slot: int) -> BenchChar:
        return BenchChar(
            slot=slot, char_id=u.get('char_id', ''),
            faction=u.get('faction', '?'),
            star=int(u.get('star', 1) or 1),
            position_pref=u.get('position_pref', 'back'),
            equips=list(u.get('equips') or []))

    def build_state(self) -> GameState:
        """进场态 → GameState(plane=2;bench 保 9 槽 pad 语义)。"""
        st = GameState()
        st.plane, st.level, st.gold, st.hp = 2, self.level, self.gold, self.hp
        st.board = dict(self.board)
        for i, u in enumerate(self.bench[:BENCH_CAPACITY]):
            st.bench[i] = self._unit(u, i + 1)
        # ADR-0392:进场态紧缩序 → 槽位表(按 position_pref 路由落槽)
        st.deployed = deployed_from_compact(
            [self._unit(u, i + 1) for i, u in enumerate(self.deployed)])
        st.equips = list(self.equips)
        st.streak = self.streak
        return st


def simulate_p2_replay_entry(entry: P2ReplayEntry, seed: int, *,
                             pool: str | Path = 'snapshot',
                             p2_combat: P2CombatCalib | None = None,
                             use_refresh: bool = True) -> SimResult:
    """案 b 交叉校验臂(W193/ADR-0377;W186 设计 §4/§3 锚 R1)。

    从真值 P2 进场态(hp/gold/board/bench/deployed/level/意向)直接
    跑 P2 段——**共享 ``simulate_p1`` 的 P2 段循环体**(经 ``_p2_entry``
    注入跳过 P1 段,单一源零复制)。锚 R1 对拍口径:存活轮分布/战斗
    胜率/逐轮掉血带覆盖/金轨迹符号,统计量落实测带内即过(**带内**
    不是「贴近」——贴脸=过拟合警报,W186 §6);真值 run 是旧策略
    病局,sim 跑当前策略,决策层差异 expected,锚只锁结算与经济层。
    """
    sess = StrategySession()
    if entry.locked_comp:
        from sr_od.application.currency_war.cw_comps import COMP_LIBRARY
        if entry.locked_comp in COMP_LIBRARY:
            sess.target_comp = COMP_LIBRARY[entry.locked_comp]
    return simulate_p1(seed, use_refresh=use_refresh, pool=pool,
                       session=sess, p2_combat=p2_combat,
                       _p2_entry=entry)


class _Plane1View:
    """P1 段辖域切片(ADR-0362,W157):planes>=2 批次的 P1 锚定指标
    只消费 plane=1 行;planes=1 时视图 ≡ 原结果(零漂移)。

    hp_events 的 P1 行 ts∈1-9、P2 行 ts≥10(P2_NODE_SEQUENCE 首轮
    ts=10)——按 ts 切片;ledger 按 plane 字段切片。
    """

    def __init__(self, r: SimResult):
        self.ledger = [row for row in r.ledger
                       if (row.get('plane') or 1) == 1]
        self.hp_events = [e for e in r.hp_events if e[0] <= 9]
        self.dir_round = r.dir_round
        self.final_hp = r.final_hp


def simulate_p1_batch(n: int = 500, *, use_refresh: bool = True,
                      seed_base: int = 0,
                      pool: str | Path = 'auto',
                      ledger: bool | Path = True,
                      checks: bool = True,
                      planes: int = 1,
                      invest: SimInvestProfile | bool = False,
                      p2_combat: P2CombatCalib | None = None) -> dict:
    """批量模拟 + 统计(HP≥60 概率/方向建立分布/平均末 HP)。

    :param planes: 透传 ``simulate_p1``(1=P1 段——历史口径逐位不变;
        2=追加 P2 段,报告增 P2 headline 四联,ADR-0362/W157)。
    :param invest: 透传 ``simulate_p1``(W162/ADR-0364;注入批报告增
        invest headline 三联:环境注入率/持卡均值/P1 锁定轮——含 D 的
        P1 侧结论自此批起以注入口径为基准)。

    返回含 ``pool_fingerprint``/``pool_source``(⓪):跨日基线
    对照必须核对指纹一致——池随实机追加漂移,裸数字不可比。

    :param ledger: True=落两流账本到 ``sim_runs/<batch_id>/"``"
        (decisions+outcomes.jsonl,判读 CLI 可查);Path=显式目录;
        False=不落盘。batch_id 含时间戳,自动保留最近
        ``_SIM_RUNS_KEEP`` 个批次。
    :param checks: 跑完执行 cw_sim_checks 异常断言(②;默认开,
        结果挂 ``checks_violations``)。
    """
    import statistics
    results = [simulate_p1(seed_base + i, use_refresh=use_refresh,
                           pool=pool, planes=planes, invest=invest,
                           p2_combat=p2_combat)
               for i in range(n)]
    # ADR-0362(W157):P1 过程指标的辖域切片——planes>=2 时账本含
    # P2 段行,P1 锚定指标(成型/败场/引擎)只算 plane=1 行;
    # planes=1 时视图 ≡ 原结果(零漂移)。
    views = [_Plane1View(r) for r in results]
    _entered = [r for r in results if r.p2_entered]
    report = {
        'n': n,
        'pool_fingerprint': results[0].pool_fingerprint,
        'pool_source': results[0].pool_source,
        'hp_ge_60': sum(1 for h in (r.final_hp for r in results) if h >= 60) / n,
        'avg_final_hp': statistics.mean(r.final_hp for r in results),
        # r370(新验收对齐,goal rev5):战斗节点败场 ≤2 概率
        # (battle/encounter/boss 计分,奖励/补给不计;hp_events
        # 的 delta<0=败)。与实机 outcomes killed+node_type 同构。
        'battle_losses_le_2': sum(
            1 for v in views
            if sum(1 for _, nt, d, _ in v.hp_events
                   if nt in ('battle', 'encounter', 'boss') and d < 0) <= 2
        ) / n,
        'dir_by_r2': sum(1 for d in (r.dir_round for r in results) if d <= 2) / n,
        'dir_by_r4': sum(1 for d in (r.dir_round for r in results) if d <= 4) / n,
        'dir_never': sum(1 for d in (r.dir_round for r in results) if d >= 99) / n,
        'avg_dir_round': (statistics.mean(
            [d for d in (r.dir_round for r in results) if d < 99])
            if any(r.dir_round < 99 for r in results) else float('nan')),
        'avg_refreshes': sum(r.refreshes for r in results) / n,
        # ===== P2 headline 四联(ADR-0362,W157;planes>=2 有意义)=====
        # 存活轮/P2 胜率/hp0 率/D 次数——P2 修法(ADR-0361 V_D)
        # 的行为分布验证场;比率分母=进场 P2 的局(P1 段死局不计,
        # 与实机「活过 P1 才有 P2」幸存口径一致,W156 §3 风险声明)。
        'p2_entered_rate': len(_entered) / n,
        'avg_p2_rounds': (round(statistics.mean(
            [r.p2_rounds for r in _entered]), 2)
            if _entered else None),
        'p2_win_rate': (round(sum(r.p2_combat_wins for r in _entered)
                              / max(1, sum(r.p2_combat_total
                                           for r in _entered)), 4)
            if any(r.p2_combat_total for r in _entered) else None),
        'p2_hp0_rate': (sum(1 for r in _entered if r.p2_hp0)
                        / len(_entered) if _entered else None),
        'avg_p2_refreshes': (round(statistics.mean(
            [r.p2_refreshes for r in _entered]), 2)
            if _entered else None),
        # ===== P2 校准层与判读观测 headline(W193/ADR-0377;判读同构
        # 口径对齐 W182/W183:金带走量/carry 笔数价格带/意向切换/lv 到达)=====
        'p2_combat_calibrated': bool(
            _entered and _entered[0].p2_combat_calibrated),
        'avg_p2_gold_carried': (round(statistics.mean(
            [r.p2_gold_carried for r in _entered
             if r.p2_gold_carried is not None]), 2)
            if any(r.p2_gold_carried is not None for r in _entered)
            else None),
        'p2_carry_buys': {k: sum(r.p2_buys_by_cost.get(k, 0)
                                 for r in _entered)
                          for k in ('1-2', '3', '4-5')},
        'avg_p2_carry_buys': (round(statistics.mean(
            [sum(r.p2_buys_by_cost.values()) for r in _entered]), 2)
            if _entered else None),
        'p2_switch_rate': (sum(1 for r in _entered if r.p2_switch_events)
                           / len(_entered) if _entered else None),
        'avg_p2_first_switch_round': (round(statistics.mean(
            [r.p2_switch_events[0][0] for r in _entered
             if r.p2_switch_events]), 2)
            if any(r.p2_switch_events for r in _entered) else None),
        'p2_lv7_reach_rate': (sum(1 for r in _entered
                                  if r.p2_lv7_round is not None)
                              / len(_entered) if _entered else None),
        # W193/ADR-0377:校准层上下文(检查器带锚消费;bands=本批实参)
        'p2_calib': {
            'win_delta': (p2_combat or P2_COMBAT_DEFAULT).win_delta,
            'bands': {
                'battle_r1':
                    list((p2_combat or P2_COMBAT_DEFAULT).band_battle_r1),
                'battle_early':
                    list((p2_combat or P2_COMBAT_DEFAULT).band_battle_early),
                'battle_late':
                    list((p2_combat or P2_COMBAT_DEFAULT).band_battle_late),
                'encounter':
                    list((p2_combat or P2_COMBAT_DEFAULT).band_encounter),
                'boss': list((p2_combat or P2_COMBAT_DEFAULT).band_boss),
            },
        },
        # ===== invest headline 三联(W162/ADR-0364;invest 注入时有意义)=====
        # 环境注入率/P1 持卡均值/P1 锁定轮分布(①资格通道激活直证:
        # 无注入语料下 invest_p1_lock_rate 恒 0——W161 缺口闭合对照键)
        'invest_env_rate': (sum(1 for r in results if r.invest_env) / n
                            if invest else None),
        'avg_invest_strategies': (round(statistics.mean(
            [len(r.invest_strategies) for r in results]), 2)
            if invest else None),
        'invest_p1_lock_rate': (sum(
            1 for r in results if r.p1_locked_rounds > 0) / n
            if invest else None),
        'avg_p1_locked_rounds': (round(statistics.mean(
            [r.p1_locked_rounds for r in results]), 2)
            if invest else None),
        # r394/r399(过渡阵容成型指标;判据单一源=transition_combos.md
        # 2026-08-23 定稿:四体系两两组合):
        # engines2_by_r6=四体系(仙舟3/列车2/DOT2/希儿系)达成≥2 的
        # r6 前占比——「位面1 能否顺利凑到过渡阵容」的直接度量。
        # 希儿系=希儿在场 AND(量2 OR 贝2),伤害在希儿技能层,
        # 量子/贝是放大器(单卡依赖,r399 用户实战确认)。
        'engines2_by_r6': sum(
            1 for v in views
            if _first_engines_round(v, 2) is not None
            and _first_engines_round(v, 2) <= 6) / n,
        'recipe5_by_r6': sum(
            1 for v in views
            if _first_tier_round(v, 5) is not None
            and _first_tier_round(v, 5) <= 6) / n,
        'trio3_by_r8': sum(
            1 for v in views
            if _first_trio_round(v, 3) is not None
            and _first_trio_round(v, 3) <= 8) / n,
        # ADR-0305 件2:到达 e2 前的战斗结算数(口径钉死,防 0304
        # 「30 vs 10」类未定义口径误读;None=未达 e2 不计入均值)
        'avg_battles_before_e2': (round(statistics.mean(
            [b for b in (_battles_before_engines(v, 2) for v in views)
             if b is not None]), 2)
            if any(_first_engines_round(v, 2) is not None
                   for v in views) else None),
        # ADR-0283(批⑰ F6):全批 bench 满守卫跳过的买总次数(超容买
        # 披露;0=守卫未介入,>0 = 满仓态买门判读须对照此计数)
        'bench_full_skipped_buys': sum(
            (row.get('sim') or {}).get('bench_full_skipped_buys', 0)
            for r in results for row in r.ledger),
        # ADR-0285(批㉑ F3):守卫拦截买折算金总额(净滞留口径输入)
        'bench_full_skipped_gold': sum(
            (row.get('sim') or {}).get('bench_full_skipped_gold', 0)
            for r in results for row in r.ledger),
        # ADR-0284(批㉒ F1/F5):幻影再买提案与池 take 地板命中
        # (真策略批次双 0;>0 = 槽消费回归/池守恒破)
        'phantom_rebuys': sum(r.phantom_rebuys for r in results),
        # ADR-0294 件2:supply 带钻选中总数(占位实体披露;带钻
        # 是词缀元数据不进 owned 池,此计数是它唯一的 sim 痕迹)
        'phantom_supply_picks': sum(
            r.phantom_supply_picks for r in results),
        # W213/ADR-0394:P1 出口 key_equips 命中率(有 key 需求局
        # 的均值;两步语义修复后应显著高于旧「恒 idx0」形态的基线)
        'p1_key_hit_rate': (round(statistics.mean(
            [r.p1_key_hit_hits / r.p1_key_hit_total
             for r in results if r.p1_key_hit_total > 0]), 3)
            if any(r.p1_key_hit_total > 0 for r in results) else None),
        'p1_key_hit_runs': sum(
            1 for r in results if r.p1_key_hit_total > 0),
        'pool_floor_hits': sum(r.pool_floor_hits for r in results),
        # ADR-0287(批㉘ F1):全批残留可上件总数(买后部署语义下
        # 应 0;>0 = 部署时序回归/围栏漏上,检查项扫出)
        'deploy_lag_units': sum(
            (row.get('sim') or {}).get('deploy_lag_units', 0)
            for r in results for row in r.ledger),
        # 动作 v2(契约包 C1,步2):显式动作拒绝/围栏跳过全批披露
        # (真策略不发显式动作 → 双 0;演进引擎 C3 接入后作决策质量信号)
        'explicit_action_rejects': sum(
            r.explicit_action_rejects for r in results),
        'fence_skips': sum(r.fence_skips for r in results),
    }
    if ledger is not False:
        out = (Path(ledger) if isinstance(ledger, Path)
               else _default_sim_runs_dir(report['pool_fingerprint'], n,
                                          seed_base))
        report['ledger_dir'] = str(write_batch_ledger(
            results, out, pool_fp=report['pool_fingerprint']))
    if checks:
        from sr_od.application.currency_war.cw_sim_checks import (
            check_battle_rung_pool_bucket_lock,
            check_delta_pool_bucket_coverage,
            check_delta_pool_bucket_min_n,
            check_depth_cliff_monotonicity,
            check_reward_delta_pool_bucket_lock,
            run_checks_on_ledgers,
        )
        rep_checks = run_checks_on_ledgers(
            [v.ledger for v in views])
        # ADR-0268:池级检查(桶饥饿/深崖单调)——批③ F1 的常态
        # 化防线;fallback 空池无违规属预期(池语义检查不辖旧模型)
        # ADR-0362:池级检查消费 plane=1 视图(判据全 P1 语料口径,
        # plane≥2 桶贫困走 META ``p2:`` 前缀披露,不进判据)
        _pm, _, _ = resolve_pool(pool)
        _pm = plane_view(_pm)
        rep_checks['delta_pool_bucket_min_n'] = \
            check_delta_pool_bucket_min_n(_pm)
        rep_checks['depth_cliff_monotonicity'] = \
            check_depth_cliff_monotonicity(_pm)
        # ADR-0279(批⑬):battle rung 分桶锁(真值表/边界声明/
        # 池域覆盖);fallback 空池不辖
        rep_checks['battle_rung_pool_bucket_lock'] = \
            check_battle_rung_pool_bucket_lock(_pm)
        # ADR-0306 件5:桶覆盖披露(n≥10 或 META bucket_poverty 显式
        # 披露)——snapshot 池带 META 披露;auto/fallback 无披露载体,
        # 贫困桶计违规(可见性优先)
        _meta = None
        if pool == 'snapshot':
            from sr_od.application.currency_war.cw_delta_pool_data import (
                META as _META_SNAP,
            )
            _meta = _META_SNAP
        rep_checks['delta_pool_bucket_coverage'] = \
            check_delta_pool_bucket_coverage(_pm, meta=_meta)
        # ADR-0292(批㉗ F3/F4):reward/supply Δ 分布入池 + 均值对拍
        # 语料真值(含跨 run 配对伪影哨兵)
        rep_checks['reward_delta_pool_bucket_lock'] = \
            check_reward_delta_pool_bucket_lock(_pm)
        # W109(ADR-0344):池新鲜度——snapshot/auto 池与本机生产
        # replay 落后 ≥2 局 = 再生管线断(池停 12h 零报警事故的
        # 常设防线);fallback 无池语义不辖;无本机 replay(CI)跳过。
        if pool in ('snapshot', 'auto'):
            from sr_od.application.currency_war.cw_sim_checks import (
                check_pool_freshness,
            )
            rep_checks['pool_freshness'] = check_pool_freshness()
        # ADR-0272:池构造无费用截断(单局已硬断言;批级披露)
        from sr_od.application.currency_war.cw_sim_checks import (
            check_sim_pool_no_cost_truncation as _chk_pool,
        )
        rep_checks['sim_pool_no_cost_truncation'] = \
            _chk_pool(_Pool(random.Random(0)).copies)
        # 批⑩/批⑪ 检查项(ADR-0276/0277):批级聚合检查——boss 胜率
        # 校准/成型-hp 耦合哨兵/升级 binding/末段刷新闭合/末金校准/
        # 锚登记制;吃全批账本(跨局聚合,不进 _BATCH_CHECKS 的逐局循环)
        # ADR-0362:辖 P1 段账本(views;planes=1 时 ≡ 全量零漂移)
        from sr_od.application.currency_war.cw_sim_checks import (
            check_anchor_registry_n300,
            check_boss_win_calibration,
            check_formation_hp_coupling_sentinel,
            check_levelup_binding,
            check_r5plus_refresh_closure,
            check_sim_endgold_calib,
        )
        _ledgers = [v.ledger for v in views]
        rep_checks['boss_win_calibration'] = \
            check_boss_win_calibration(_ledgers)
        rep_checks['formation_hp_coupling_sentinel'] = \
            check_formation_hp_coupling_sentinel(_ledgers)
        rep_checks['levelup_binding_check'] = check_levelup_binding(_ledgers)
        rep_checks['r5plus_refresh_closure'] = \
            check_r5plus_refresh_closure(_ledgers)
        rep_checks['sim_endgold_calib'] = check_sim_endgold_calib(_ledgers)
        rep_checks['anchor_registry_n300'] = \
            check_anchor_registry_n300(report)
        # ADR-0294 件3(ADR-0289 接线欠账):批级聚合入口并入——
        # 清偿批的批级披露/哨兵/条件型检查一次跑全(逐局锁已由
        # run_checks_on_ledgers 自动扫;worker X 合流后本欠账清偿)
        from sr_od.application.currency_war.cw_sim_checks import (
            run_batch_level_checks,
        )
        rep_checks.update(run_batch_level_checks(
            _ledgers, report=report, pool_map=_pm))
        # ADR-0362(W157):P2 段检查器最小集——金轨迹非负 + 段形状
        # (辖 planes>=2 批次的 P2 段行;P1 批无 plane=2 行恒绿)
        from sr_od.application.currency_war.cw_sim_checks import (
            check_p2_gold_nonneg,
            check_p2_segment_shape,
        )
        _ledgers_p2 = [r.ledger for r in results]
        rep_checks['p2_gold_nonneg'] = check_p2_gold_nonneg(_ledgers_p2)
        rep_checks['p2_segment_shape'] = check_p2_segment_shape(_ledgers_p2)
        # W193/ADR-0377:P2 战斗存活层检查器(掉血带覆盖锚 + 胜率带锚;
        # 辖 calibrated 批——uncalibrated 批恒绿跳过,legacy 档不辖)
        from sr_od.application.currency_war.cw_sim_checks import (
            check_p2_loss_band_anchor,
            check_p2_win_rate_band,
        )
        rep_checks['p2_loss_band_anchor'] = check_p2_loss_band_anchor(
            _ledgers_p2, report=report)
        rep_checks['p2_win_rate_band'] = check_p2_win_rate_band(
            _ledgers_p2, report=report)
        # 审查#6:报告自带 seed_base/n——games 索引 → seed =
        # seed_base+idx,跨日志传阅时索引可独立解读
        for v in rep_checks.values():
            v['seed_base'] = seed_base
        report['checks_violations'] = rep_checks
    return report


def simulate_p1_ab(n: int = 300, *, pool: str | Path = 'snapshot',
                   seed_base: int = 0) -> dict:
    """A/B 对照报告(同 seed 配对双臂 + 分辨率底;ADR-0285 件4)。

    批㉒ F4 实测:单流 RNG 共享只消掉约 1/3 方差(耦合比 0.675,
    n=300 底 ±1.93hp)——**|Δavg_hp| < 95% 底的差值在噪声带内,
    不得叙述为方向性结论**(报告带 ``noise_band`` 标注;底按本批
    配对差 sd 现算,勿写死 1.93)。默认 A=刷新开/B=刷新关,同
    seed 配对。
    """
    from sr_od.application.currency_war.cw_sim_checks import (
        check_ab_resolution_floor,
    )
    res_a = [simulate_p1(seed_base + i, use_refresh=True, pool=pool)
             for i in range(n)]
    res_b = [simulate_p1(seed_base + i, use_refresh=False, pool=pool)
             for i in range(n)]
    # 双臂 headline(直接从 results 聚合)
    import statistics
    hps_a = [r.final_hp for r in res_a]
    hps_b = [r.final_hp for r in res_b]
    return {
        'n': n, 'pool_fingerprint': res_a[0].pool_fingerprint,
        'avg_hp_a': round(statistics.mean(hps_a), 2),
        'avg_hp_b': round(statistics.mean(hps_b), 2),
        'hp_ge_60_a': sum(1 for h in hps_a if h >= 60) / n,
        'hp_ge_60_b': sum(1 for h in hps_b if h >= 60) / n,
        'ab_resolution_floor': check_ab_resolution_floor(hps_a, hps_b),
    }


def simulate_p2_ab(n: int = 100, *, pool: str | Path = 'snapshot',
                   seed_base: int = 0,
                   planes: int = 2) -> dict:
    """P2 段 vd_p2_enabled A/B 对照(W157/ADR-0362;ADR-0361 预留通道)。

    A 臂=vd_p2_enabled 开(W154 口径:DP 窗授权+机会成本 C_dec+
    存活收益口径)/B 臂=关(W153 前行为:P2 窗二分断死);同池同
    seed 配对,planes=2(进场继承 + P2 七轮段)。**同进程 flag
    对照**(W154 记档:并行期唯一安全 sim A/B 法——跨时点对照会被
    在飞批/池重生成污染)。

    headline 四联(存活轮/胜率/hp0 率/D 次数)+ D 方向对拍:
    预期 **D 次数 on>off**(W154 四局回放 6/14 帧翻正在分布面的
    体现——翻正帧=「差一张」找件通道打开);hp 类观测项如实报
    (P2 回退层掉血带口径,hp0 率是观测不是验收)。
    """
    import dataclasses
    import logging
    import statistics

    from sr_od.application.currency_war.decision_v2.registry import (
        DEFAULT_REGISTRY,
    )
    from sr_od.application.currency_war.decision_v2.strategy import (
        DecisionV2Strategy,
    )
    logging.disable(logging.CRITICAL)   # 批量跑静音(决策日志逐段刷屏)
    try:
        _strat_on = DecisionV2Strategy(registry=DEFAULT_REGISTRY)
        _strat_off = DecisionV2Strategy(
            registry=dataclasses.replace(DEFAULT_REGISTRY,
                                         vd_p2_enabled=False))
        res_a = [simulate_p1(seed_base + i, pool=pool, planes=planes,
                             strategy=_strat_on) for i in range(n)]
        res_b = [simulate_p1(seed_base + i, pool=pool, planes=planes,
                             strategy=_strat_off) for i in range(n)]
    finally:
        logging.disable(logging.NOTSET)

    def _headline(results: list[SimResult]) -> dict:
        entered = [r for r in results if r.p2_entered]
        combat_t = sum(r.p2_combat_total for r in entered)
        return {
            'p2_entered_rate': len(entered) / len(results),
            'avg_p2_rounds': round(statistics.mean(
                [r.p2_rounds for r in entered]), 2) if entered else None,
            'p2_win_rate': (round(sum(r.p2_combat_wins for r in entered)
                                  / combat_t, 4) if combat_t else None),
            'p2_hp0_rate': (sum(1 for r in entered if r.p2_hp0)
                            / len(entered) if entered else None),
            'total_p2_refreshes': sum(r.p2_refreshes for r in entered),
        }

    d_a = [r.p2_refreshes for r in res_a]
    d_b = [r.p2_refreshes for r in res_b]
    return {
        'n': n, 'planes': planes,
        'pool_fingerprint': res_a[0].pool_fingerprint,
        'headline_on': _headline(res_a),
        'headline_off': _headline(res_b),
        # D 次数对拍(配对计数;on>off 的局数 = W154 翻正预测的
        # 分布面证据;方向计数不含平局)
        'refresh_direction': {
            'on_gt_off': sum(
                1 for a, b in zip(d_a, d_b, strict=True) if a > b),
            'off_gt_on': sum(
                1 for a, b in zip(d_a, d_b, strict=True) if b > a),
            'tie': sum(
                1 for a, b in zip(d_a, d_b, strict=True) if a == b),
        },
        'avg_hp_on': round(statistics.mean(
            [r.final_hp for r in res_a]), 2),
        'avg_hp_off': round(statistics.mean(
            [r.final_hp for r in res_b]), 2),
    }


def simulate_handoff_ab(n: int = 300, *, pool: str | Path = 'snapshot',
                        seed_base: int = 0, planes: int = 2,
                        invest: bool = True) -> dict:
    """W227/ADR-0400 P1 末窗承接门 A/B + W238/ADR-0403 hp 投影臂(三臂
    +正交臂;设计件 08 §4.1 判据 3 / 09 §6 第一步口径)。

    四臂同池同 seed 配对、同进程 flag 对照(ADR-0362 §③):

    - **off**(基线)= 双 flag 关(当前默认);
    - **gate**(headline_on)= ``handoff_gate_enabled`` 开、投影关
      (W227 原两臂语义,键名保留兼容);
    - **proj**(headline_proj)= 门开 + ``handoff_boss_project`` 开
      (boss 后投影 hp 喂档位切点);
    - **proj_only**(正交性核验,不进 headline)= 仅投影开、门关——
      投影只在 ``handoff_gate_gap`` 门开路径内被消费,此臂 ledger
      应与 off 臂**整局逐位一致**(两 flag 正交的结构证据)。

    报告四面:

    - headline:P2 存活族(p2_entered/存活轮/hp0 率/胜率)——验收
      判据 3 的主指标(hp0 率下降/存活轮上移);
    - 末窗观测:各行为臂承接门扣住轮数(ledger handoff_gap>0 的轮)、
      r8 买入分布、进场承接档位分布 + **盲区修复行为差**
      (``blindspot``:同 seed 同轮 proj 臂 gap≥1 而 gate 臂 gap=0 的
      轮数/局数——run28/31/33 型「板面达标 hp 临界」局投影门触发而
      现投影门不触发的行为差证据,设计件 09 §2);
    - P1 非末窗零漂移门:plane1 round<handoff_gate_min_round 的
      ledger 行逐 seed 逐位 diff(判据 3 后半;应恒空;gate/proj 两臂)。
    """
    import dataclasses
    import json as _json
    import logging
    import statistics

    from sr_od.application.currency_war.decision_v2.registry import (
        DEFAULT_REGISTRY,
    )
    from sr_od.application.currency_war.decision_v2.strategy import (
        DecisionV2Strategy,
    )
    logging.disable(logging.CRITICAL)
    try:
        _reg_gate = dataclasses.replace(DEFAULT_REGISTRY,
                                        handoff_gate_enabled=True)
        _reg_proj = dataclasses.replace(_reg_gate, handoff_boss_project=True)
        _reg_proj_only = dataclasses.replace(DEFAULT_REGISTRY,
                                             handoff_boss_project=True)
        _strat_gate = DecisionV2Strategy(registry=_reg_gate)
        _strat_proj = DecisionV2Strategy(registry=_reg_proj)
        _strat_proj_only = DecisionV2Strategy(registry=_reg_proj_only)
        res_gate = [simulate_p1(seed_base + i, pool=pool, planes=planes,
                                invest=invest, strategy=_strat_gate)
                    for i in range(n)]
        res_off = [simulate_p1(seed_base + i, pool=pool, planes=planes,
                               invest=invest) for i in range(n)]
        res_proj = [simulate_p1(seed_base + i, pool=pool, planes=planes,
                                invest=invest, strategy=_strat_proj)
                    for i in range(n)]
        res_proj_only = [simulate_p1(seed_base + i, pool=pool, planes=planes,
                                     invest=invest,
                                     strategy=_strat_proj_only)
                         for i in range(n)]
    finally:
        logging.disable(logging.NOTSET)

    def _headline(results: list[SimResult]) -> dict:
        entered = [r for r in results if r.p2_entered]
        combat_t = sum(r.p2_combat_total for r in entered)
        return {
            'p2_entered_rate': len(entered) / len(results),
            'avg_p2_rounds': round(statistics.mean(
                [r.p2_rounds for r in entered]), 2) if entered else None,
            'p2_win_rate': (round(sum(r.p2_combat_wins for r in entered)
                                  / combat_t, 4) if combat_t else None),
            'p2_hp0_rate': (sum(1 for r in entered if r.p2_hp0)
                            / len(entered) if entered else None),
        }

    def _dump(obj) -> str:
        return _json.dumps(obj, default=str, ensure_ascii=False)

    # 正交性核验:proj_only(仅投影开)vs off 整局 ledger 逐位一致
    # (投影的消费点全在 handoff_gate_gap 门开路径内,结构零漂移)
    proj_only_drift_seeds = [
        seed_base + i for i, (p, o) in enumerate(
            zip(res_proj_only, res_off, strict=True))
        if _dump(p.ledger) != _dump(o.ledger)]

    # P1 非末窗零漂移门(判据 3 后半):逐 seed 比较行为臂 vs 基线臂
    # plane1 round<handoff_gate_min_round 的账本行(逐位;含 actions/state)
    _min_r = DEFAULT_REGISTRY.handoff_gate_min_round

    def _pre_final(rows: list[dict]) -> list[dict]:
        return [row for row in rows
                if row.get('plane') == 1
                and (row.get('round_num') or 0) < _min_r]

    drift_gate_seeds: list[int] = []
    drift_proj_seeds: list[int] = []
    for i, (g, p, o) in enumerate(
            zip(res_gate, res_proj, res_off, strict=True)):
        if _dump(_pre_final(g.ledger)) != _dump(_pre_final(o.ledger)):
            drift_gate_seeds.append(seed_base + i)
        if _dump(_pre_final(p.ledger)) != _dump(_pre_final(o.ledger)):
            drift_proj_seeds.append(seed_base + i)

    # 盲区修复行为差(设计件 09 §2):同 seed 同轮 proj gap≥1 ∧ gate
    # gap=0 —— hp 临界局投影门触发、现投影门不触发的轮(逐轮配对)
    blindspot_rounds = 0
    blindspot_games: set[int] = set()
    for i, (g, p) in enumerate(zip(res_gate, res_proj, strict=True)):
        g_gap = {(row.get('plane'), row.get('round_num')):
                 row.get('handoff_gap') or 0 for row in g.ledger}
        for row in p.ledger:
            if ((row.get('handoff_gap') or 0) > 0
                    and (g_gap.get((row.get('plane'), row.get('round_num')))
                         or 0) == 0):
                blindspot_rounds += 1
                blindspot_games.add(seed_base + i)

    # 末窗观测(行为臂):承接门扣住轮/r8 买数/进场档位分布
    def _gate_hold_rounds(results: list[SimResult]) -> int:
        return sum(1 for r in results for row in r.ledger
                   if (row.get('handoff_gap') or 0) > 0)

    def _r8_avg_buys(results: list[SimResult]) -> float | None:
        buys = [sum(1 for act in (row.get('actions') or [])
                    if act.get('__type__') == 'BuyCard')
                for r in results for row in r.ledger
                if row.get('plane') == 1 and row.get('round_num') == _min_r]
        return round(statistics.mean(buys), 2) if buys else None

    def _entry_tiers(results: list[SimResult]) -> dict[str, int]:
        tiers: dict[str, int] = {}
        for r in results:
            if r.p2_entered and r.p2_handoff:
                t = str(r.p2_handoff.get('tier'))
                tiers[t] = tiers.get(t, 0) + 1
        return tiers

    return {
        'n': n, 'planes': planes, 'invest': invest,
        'pool_fingerprint': res_gate[0].pool_fingerprint,
        'headline_off': _headline(res_off),
        'headline_on': _headline(res_gate),
        'headline_proj': _headline(res_proj),
        'gate_hold_rounds_on': _gate_hold_rounds(res_gate),
        'gate_hold_rounds_proj': _gate_hold_rounds(res_proj),
        'r8_avg_buys_off': _r8_avg_buys(res_off),
        'r8_avg_buys_on': _r8_avg_buys(res_gate),
        'r8_avg_buys_proj': _r8_avg_buys(res_proj),
        'entry_tier_dist_on': _entry_tiers(res_gate),
        'entry_tier_dist_proj': _entry_tiers(res_proj),
        # 盲区修复行为差(设计件 09 §6 第一步验收:投影臂在 hp 临界局
        # gap≥1 触发、现投影臂不触发的行为差)
        'blindspot': {'rounds': blindspot_rounds,
                      'games': len(blindspot_games),
                      'game_seeds': sorted(blindspot_games)},
        'proj_only_orthogonality': {'drift_seeds': proj_only_drift_seeds,
                                    'ok': not proj_only_drift_seeds},
        'p1_zero_drift': {'min_round': _min_r,
                          'drift_seeds_gate': drift_gate_seeds,
                          'drift_seeds_proj': drift_proj_seeds,
                          'ok': not drift_gate_seeds
                          and not drift_proj_seeds},
    }


def simulate_p2_sensitivity(n: int = 100, *, pool: str | Path = 'snapshot',
                            seed_base: int = 0, planes: int = 2,
                            betas: tuple[float, ...] = (0.0, 0.04, 0.08, 0.15),
                            gammas: tuple[float, ...] = (0.0, 0.02, 0.05, 0.10),
                            event_gold_arms: tuple[str, ...] = ('p1', 'zero'),
                            form_level_weights: tuple[float, ...] = (0.25,),
                            form_star_weights: tuple[float, ...] = (0.5,),
                            ) -> dict:
    """β/γ/事件金/form 权重敏感性扫描(W193/ADR-0377;**裁决口径**)。

    语料不足以点估计 β(W186 §3)——P2 修法的 sim 分布结论必须呈报
    本扫描:**修法在某(β,γ)网格点翻正、在带端点(β=0 / β=0.15 /
    γ=0 / γ=0.10 / 事件金双臂)一致翻正才裁「分布级」**;单点翻正
    = 不可裁。headline:存活轮/胜率/hp0 率/金带走量(判读同构)。

    ``form_level_weights``(W199/W196 发现③):β 扫描只缩放整条
    form(engines + w·(lv−6) 同乘 β),分辨不了 engines:lv 构成比
    ——lv 投资型修法(金流改道升级)的存活收益显影取决于 lv 项
    真实权重,故 w 入网格(端点 0=lv 零贡献 / 高档 0.5/1.0);
    默认 (0.25,) = P2_COMBAT_DEFAULT 单值,行为向后兼容。
    ``form_star_weights``(W230/ADR-0401,同型):星级投资型修法
    (承接门/W227)的存活收益显显取决于 star_depth 项真实权重
    (真值分帧只定向不定量)——端点 0(星级零贡献=旧 form 形态)/
    0.25 / 1.0;默认 (0.5,) = 单值。
    """
    import dataclasses
    import logging
    import statistics

    logging.disable(logging.CRITICAL)
    try:
        table = []
        for eg in event_gold_arms:
            for b in betas:
                for g in gammas:
                    for w in form_level_weights:
                        for ws in form_star_weights:
                            calib = dataclasses.replace(
                                P2_COMBAT_DEFAULT, beta=b, gamma=g, event_gold=eg,
                                form_level_weight=w, form_star_weight=ws)
                            rs = [simulate_p1(seed_base + i, pool=pool,
                                              planes=planes, p2_combat=calib)
                                  for i in range(n)]
                            entered = [r for r in rs if r.p2_entered]
                            ct = sum(r.p2_combat_total for r in entered)
                            cw = sum(r.p2_combat_wins for r in entered)
                            carried = [r.p2_gold_carried for r in entered
                                       if r.p2_gold_carried is not None]
                            table.append({
                                'event_gold': eg, 'beta': b, 'gamma': g,
                                'form_level_weight': w, 'form_star_weight': ws,
                                'p2_entered_rate': len(entered) / n,
                                'avg_p2_rounds': round(statistics.mean(
                                    [r.p2_rounds for r in entered]), 2)
                                if entered else None,
                                'p2_win_rate': round(cw / ct, 4) if ct else None,
                                'p2_hp0_rate': (sum(1 for r in entered
                                                    if r.p2_hp0)
                                                / len(entered))
                                if entered else None,
                                'avg_p2_gold_carried': round(statistics.mean(
                                    carried), 2) if carried else None,
                                'avg_final_hp': round(statistics.mean(
                                    [r.final_hp for r in rs]), 2),
                            })
    finally:
        logging.disable(logging.NOTSET)
    return {
        'n': n, 'planes': planes,
        'pool_fingerprint': resolve_pool(pool)[1],
        'grid': table,
    }


# sim 账本落盘根目录(与生产 replay 隔离;写入器有目录守卫)
SIM_RUNS_DIR = _AUTO_REPLAY_DIR.parent / 'sim_runs'   # 仓根锚定(同上)
_SIM_RUNS_KEEP: int = 20   # 批次保留数(防无限累积;旧的自动清理)
_NT_TO_PROD = {'battle': '普通战斗', 'encounter': '遭遇',
               'reward': '奖励', 'boss': '首领', 'supply': '补给'}


def _default_sim_runs_dir(pool_fp: str, n: int, seed_base: int) -> Path:
    import time
    stamp = time.strftime('%Y%m%d_%H%M%S') + f'{time.monotonic_ns() % 1000:03d}'
    return SIM_RUNS_DIR / f'sim_{stamp}_n{n}_s{seed_base}_{pool_fp[:8]}'


def write_batch_ledger(results: list[SimResult], out_dir: Path, *,
                       pool_fp: str = '') -> Path:
    """两流账本落盘:``<out_dir>/{decisions,outcomes}.jsonl``。

    - decisions 每轮一行(SimResult.ledger;run_id=batch 目录名);
    - outcomes 每轮一行(OutcomeRecord 同构:生产 node_type 词表
      + hp_after + board_before/bench_count;sim 专属键挂 'sim');
    - **守卫:out_dir 不得是生产 replay 目录**(自中毒防线,
      生成器侧另有源目录断言,双保险)。
    """
    import json as _json
    out_dir = Path(out_dir)
    _prod = _AUTO_REPLAY_DIR.resolve()
    if out_dir.resolve() == _prod or _prod in out_dir.resolve().parents:
        raise RuntimeError(
            f'sim 账本禁写生产 replay 目录: {out_dir}(自中毒回路;'
            f'落盘目标只能是 {SIM_RUNS_DIR} 下或显式独立目录)')
    out_dir.mkdir(parents=True, exist_ok=True)
    base_id = out_dir.name
    with (out_dir / 'decisions.jsonl').open('w', encoding='utf-8') as f_d, \
         (out_dir / 'outcomes.jsonl').open('w', encoding='utf-8') as f_o, \
         (out_dir / 'shop_snapshots.jsonl').open('w',
                                                 encoding='utf-8') as f_s:
        for r in results:
            # 每局独立 run_id(带 seed——判读视图按 run 过滤时一局一局
            # 看,且 id 即重放地址:simulate_p1(<seed>) 重放该局)
            run_id = f'{base_id}_s{r.seed}'
            for row in r.ledger:
                row = dict(row)
                row['run_id'] = run_id
                row['schema_version'] = 1
                f_d.write(_json.dumps(row, ensure_ascii=False) + '\n')
                o = {
                    'schema_version': 1, 'ts': row['ts'],
                    'run_id': run_id, 'plane': row['plane'],
                    'round_num': row['round_num'],
                    'node_type': _NT_TO_PROD.get(
                        row['sim']['node'], row['sim']['node']),
                    'comp_tag': row['target_comp'] or '',
                    'hp_after': row['hp'],
                    # ADR-0271:board 真值(deployed 主阵营聚合;
                    # 旧恒空 dict 让 rounds/economy 视图板面恒缺)
                    'board_before': dict(
                        (row['state'] or {}).get('board') or {}),
                    'bench_count':
                        len(row['state']['bench']),
                    'sim': {'delta': row['sim']['delta'],
                            'depth': row['sim']['depth'],
                            # killed 语义同产线=**胜**(击杀敌方;
                            # settlement_obs _won / battle_loop
                            # hp_after>=prev_hp——审查 major:killed
                            # 极性反转会把败场读成胜场)
                            'killed': row['sim']['delta'] >= 0},
                }
                f_o.write(_json.dumps(o, ensure_ascii=False) + '\n')
                # 第三流:牌面波(生产 shop_snapshots 同 schema——
                # supply 视图零改动可查 sim 批次)
                for w in row['sim'].get('shop_waves') or []:
                    f_s.write(_json.dumps({
                        'schema_version': 1, 'ts': row['ts'],
                        'run_id': run_id, 'plane': row['plane'],
                        'round_num': row['round_num'],
                        'event': w['event'], 'gold': w['gold'],
                        'shop': w['cards'],
                    }, ensure_ascii=False) + '\n')
    # manifest(审查#5:写半失败无标记 → 残批被当有效批;判读端
    # 可校验 manifest 在+行数匹配才认批)。ledger_semantics 标记
    # 账本字段语义版本(审查#2:core_count 三人组→按线路由变更
    # 无标记,新旧批次混存=③ 聚合静默混桶)。
    (out_dir / 'manifest.json').write_text(_json.dumps({
        'n': len(results),
        'seeds': [r.seed for r in results],
        'pool_fingerprint': pool_fp or (
            results[0].pool_fingerprint if results else ''),
        'rounds_rows': sum(len(r.ledger) for r in results),
        'ledger_semantics': 'core_routed',
    }, ensure_ascii=False), encoding='utf-8')
    # 保留清理(旧批次滚动删除;只清 sim_ 前缀批——用户显式传的
    # 非 sim 目录不动,审查#5)
    if SIM_RUNS_DIR.exists():
        batches = sorted(p for p in SIM_RUNS_DIR.iterdir()
                         if p.is_dir() and p.name.startswith('sim_'))
        for old in batches[:-_SIM_RUNS_KEEP]:
            import shutil
            shutil.rmtree(old, ignore_errors=True)
    return out_dir


def _cli_main() -> None:
    """④ seed 重放入口(可复现 bug 报告:seed+池指纹 → 逐轮决策)。

    用法:
        uv run python -m sr_od.application.currency_war.cw_sim \\
            replay --seed 42 --pool snapshot
    checks 报的 games 索引 → seed = seed_base + idx,同参数重放。
    池指纹不符(历史 bug 对新池)→ 提示换池版本,不硬跑(⓪ 纪律)。
    """
    import argparse
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(prog='cw_sim')
    ap.add_argument('cmd', choices=['replay', 'batch'])
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--n', type=int, default=100)
    ap.add_argument('--planes', type=int, default=1,
                    help='1=P1 段;2=追加 P2 段(ADR-0362)')
    ap.add_argument('--seed-base', type=int, default=0)
    ap.add_argument('--pool', default='snapshot',
                    help='auto/snapshot/fallback/JSON 路径')
    ap.add_argument('--expect-fingerprint', default='',
                    help='期望池指纹(不符即拒——历史报告对旧池重放)')
    args = ap.parse_args()
    pool_arg = args.pool
    if args.cmd == 'replay':
        r = simulate_p1(args.seed, pool=pool_arg, planes=args.planes)
        if args.expect_fingerprint and \
                r.pool_fingerprint != args.expect_fingerprint:
            print(f'池指纹不符: 期望 {args.expect_fingerprint} '
                  f'实得 {r.pool_fingerprint}(换池版本或 Path 快照)')
            return
        print(f"=== seed {args.seed} | 池 {r.pool_source} "
              f"{r.pool_fingerprint[:8]} | 末HP {r.final_hp} "
              f"| dir r{r.dir_round} ===")
        for row in r.ledger:
            s = row['sim']
            buys = [f"{(a.get('card') or {}).get('name')}"
                    f"({a.get('reason', '?')})"
                    for a in row['actions']
                    if a.get('__type__') == 'BuyCard']
            print(f"  p{row['plane']}r{row['round_num']} {s['node']:<9} "
                  f"Δ{s['delta']:+3d} hp={row['hp']:>3} "
                  f"g={row['gold']:>3} 深{s['depth']:>2} "
                  f"花={sum(s['spend']['buys'].values())} "
                  f"tgt={row['target_comp'] or '-'} "
                  f"买={','.join(buys) or '-'}")
    else:
        rep = simulate_p1_batch(args.n, seed_base=args.seed_base,
                                pool=pool_arg, planes=args.planes)
        for k in ('n', 'hp_ge_60', 'battle_losses_le_2', 'avg_final_hp',
                  'p2_entered_rate', 'avg_p2_rounds', 'p2_win_rate',
                  'p2_hp0_rate', 'avg_p2_refreshes',
                  'pool_fingerprint'):
            print(f'{k}: {rep[k]}')
        print('checks:', rep['checks_violations'])


if __name__ == '__main__':
    _cli_main()
