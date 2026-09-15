"""Δ 池解析与池视图(自 cw_sim 拆出,分包期6)。

诚实性前提:Δ 池是实机经验分布的采样源——auto(缺源 raise 不静默)/
snapshot(主仓提交快照)/fallback(显式退旧模型,结果打标)三态解析;
池指纹 = hash(池内容规范化 + 桶宽 + 采样器版本),跨日基线须核指纹。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

from sr_od.application.currency_war.data.cw_battle_tables import (
    BUCKET_MIN_N,
    DEPTH_BUCKET_W,
)
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    POOL_COPIES_PER_CARD,
    REFRESH_PROB,
)

# 血预算停手·终止分支账本决策位(设计 迁移审计 w659(git 历史) v2 §5.1 R4;ADR-0469)——
# 账本行 'terminal_release' 键的写入侧单一源 =
# sim/checks/segments.terminal_release_bit(sim 引擎轮入口调用,本模块
# 只消费行键不作记账面)。
from sr_od.application.currency_war.kernel.cw_battle_calib import (
    _engines_count,
    _star_depth_from_rows,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    STRATEGY_EFFECTS,
    EconomyEffect,
    normalize_invest_name,
)

# 生产流根 = kernel/cw_observe 单一源(telemetry/live;2026-09-07 布局
# 裁定前本模块曾自持一份 get_project_root 镜像,收拢后镜像双源不再存在)。
from sr_od.application.currency_war.kernel.cw_observe import (
    DEFAULT_REPLAY_DIR as _AUTO_REPLAY_DIR,
)
from sr_od.application.currency_war.kernel.cw_vocab import ShopCard

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
    # telemetry/sim/<batch_id>/{decisions,outcomes}.jsonl 两流。
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
    # `w213_sim_supply/`/ADR-0394:P1 出口 key_equips 命中度量(命中数 / 需求总数;
    # 口径 = P1 段末 worn(deployed.equips)+ owned(st.equips)合并
    # 对当时 target_comp.key_equips(计重复)的满足量;target 未锁
    # 定或 key 为空的局 total=0,聚合端按 total>0 局求均值——`w212_sim_equip/`
    # 批 A 同口径(key_last=最后一次分配时的 key 表))
    p1_key_hit_hits: int = 0
    p1_key_hit_total: int = 0
    # ===== `w614_sim_fidelity/` 迁移批 0:sim 保真三补的记账出口(纯观测,零漂移)=====
    # 装备事件落账(计数级;实机出口对应物 = `w607_affix_consumption/` 判读量「滞留件数」与
    # 库藏生锈词条暴露面,词条语义单一源 cw_comps.RUST_AFFIX_NAME):
    equip_grants: int = 0        # 发放件数(supply 选择/reward 直发/追加件)
    equip_wears: int = 0         # 穿戴件数(分配器从 owned 池移穿上板的件)
    equip_syntheses: int = 0     # 装备栏内合成成品件数(合成链 hook 点火时)
    p1_unworn_exit: int = 0      # P1 段末未穿滞留件数(len(owned 池))
    p1_rust_units_peak: int = 0  # P1 段内生锈暴露峰值 min(10, 未穿件数)
    # 上阵代理记账(实机出口对应物 = `w608_ladder_adversarial/` 重裁 M2「配方件躺 bench 轮数/局」
    # 与成型质量粗代理;代理语义=配方隶属按意向 target 的 core/faction 集)
    p1_bench_recipe_piece_rounds: int = 0   # P1 各轮「bench 上配方隶属件数」累计
    p1_deployed_power_avg: float = 0.0      # P1 各轮上阵战力贡献代理均值
                                            # (Σ(star + core∈target 计 1);口径见账本 sim.deployed_power)
    # 付费刷新产经验(xp_per_refresh,如淘金客;免费刷不计)局级累计
    refresh_xp_total: int = 0
    # 动作 v2(契约包 C1,步2):显式部署动作(SellDeployed/SwapDeploy/
    # 事务)被整体拒绝的次数(原子性拒绝披露;真策略当前;原 CompTransaction
    # 不发显式动作 → 恒 0,演进引擎 C3 接入后 >0 即决策侧提案越界信号)
    explicit_action_rejects: int = 0
    # 动作 v2:围栏跳过轮数(显式动作发出轮 select_deployments 自动
    # 部署让位——裁决1「显式>围栏,同轮互斥」;账本同步记 skip_fence 行)
    fence_skips: int = 0
    # ===== P2 段观测(ADR-0362,`w157_p2/`;planes>=2 时填,默认 0/False)=====
    p2_entered: bool = False        # 活过 P1 进场 P2(P1 段死=False)
    p2_rounds: int = 0              # P2 段已结算轮数(0-7)
    p2_combat_total: int = 0        # P2 段战斗类节点结算数
    p2_combat_wins: int = 0         # 其中 delta>=0 的胜场数
    p2_hp0: bool = False            # 死在 P2 段(终局 hp<=0)
    p2_refreshes: int = 0           # P2 段 RefreshShop 次数(D 次数)
    # ===== P2 校准层与判读观测(`w193_p2sim/`/ADR-0377;planes>=2 时填)=====
    p2_combat_calibrated: bool = False   # 本局 P2 结算走参数化校准层?
    p2_gold_carried: int | None = None   # 金带走量(死在 P2 段时的末金;
                                          # 活过 P2=None——`w183_carry/` D1 判据族)
    p2_buys_by_cost: dict[str, int] = field(default_factory=dict)
                                        # P2 段买笔数按价格带 {'1-2','3','4-5'}
                                        # (`w183_carry/` 价格带判读口径)
    p2_switch_events: list[tuple[int, str, str]] = field(default_factory=list)
                                        # 意向切换事件 (轮,前 target,后 target)
                                        # (`w182_p2/`「切换后采购执行密度」数据源)
    p2_lv6_round: int | None = None  # P2 段内首次 level>=6 的轮(None=未达)
    p2_lv7_round: int | None = None  # P2 段内首次 level>=7 的轮(`w183_carry/`:
                                     # run15 恒 lv6 卡死形态的可观测指标)
    # `w224_handoff/`/ADR-0399:P2 承接快照(decision_v2.handoff.HandoffSnapshot.
    # as_dict;进场继承完成后位面首帧采样——生产同点=strategy_state_of(session).v3_handoff,
    # 决策代码挂载零复制单一源)。None=未进 P2/策略桩未算。纯观测零漂移
    # (不耗 rng,planes=1 路径不触及)。
    p2_handoff: dict | None = None
    # ===== 投资注入观测(`w162_inject/`/ADR-0364;invest 注入时填,默认空/0)=====
    invest_env: str = ''            # 本局注入的投资环境名(空 = 无)
    invest_strategies: tuple[str, ...] = ()   # 本局实际注入持有的策略名序
    # 双臂:基线臂(真实判据)选卡归因——每条 = {'kind','plane','round',
    # 'options','picked','reason'},reason 为 kernel decide_event 的判据归因串
    # 透传(可观测要求:后续统计可按归因分桶)。仅 invest_arm='sink' 填;
    # freq 注入臂/固定剧本 = 注入无判据,恒 ()。
    invest_picks: tuple[dict, ...] = ()
    p1_locked_rounds: int = 0       # P1 段意向 phase=='locked' 的轮数

                                      # (①资格通道激活直证——无注入语料下
                                      # 恒 0,`w161_refresh/` 缺口闭合前后对照键)


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

# --- Δ 池三态解析(⓪ 快照化;对抗审查一轮#1/二轮#1/#5 定谳) -----
# 校准数据可复现性纪律:
# - **缺源大声报错,禁止隐式静默回退**(实测同 seed 有池/无池可
#   翻转 hp_ge_60 判定:seed42 final 36 vs 55)——回退必须显式
#   pool='fallback',结果行打标 pool_source;
# - **指纹 = hash(池内容+桶宽+采样器版本)**,随 SimResult/批量
#   结果记录——裸 seed 不构成可重放承诺,重放 = seed+指纹;
# - 池源与 sim 落盘(telemetry/sim)隔离,防线在生成器源目录断言
#   (tools/cw/gen_delta_pool_snapshot.py,防 sim 数据回灌校准池)。
# v6(ADR-0308,迁移审计 w37(git 历史)):回退层胜负面换 迁移审计 w31(git 历史) 实测节点×轮次胜率阶梯
# (NODE_WIN_P_LADDER,n=192)——battle 方向二元门控/encounter 恒败/
# boss rung 表+rung2 外推全部废弃(幅度层保留)。池内容不变但结算
# 语义变 → 快照 META 指纹与锚重记(ADR-0308 回归验证节)。
_SAMPLER_VERSION: int = 11  # 桶化/邻桶回退/采样语义变更时 +1(指纹输入)

# v7(ADR-0312,迁移审计 w50(git 历史) 口径统一):采样键 _deployable_depth 从
# min(level, len(deployed)) 改 **Σboard(全集口径)**——与池语料
# (decisions state.board 求和,实机全集口径)同口径;旧键与池语料
# 不同口径,同一局面两侧落不同桶,采样系统性偏浅(迁移审计 w49(git 历史) Q4)。同时
# state.board 本身换全集口径(_recount_board)——池内容不变但 sim
# 侧查询/结算键变 → 快照 META 指纹重算 + ANCHOR_REGISTRY_N300 锚
# 重记(ADR-0308 同款流程)。
# v8(ADR-0362,`w157_p2/` P2 段扩展):Δ池 **plane 维键化**——SNAPSHOT
# 形状 {节点:{位面:{桶:[Δ]}}},差分归属后行位面(P1r9→P2r1 跨
# 位面差分归 plane=2);顺手清除既有 P1 池 P2 污染(44 条 plane=2
# 差分混入无位面维的池,含 16 条跨位面差分,迁移审计 w156(git 历史) 勘察 §5.1)。
# P1 桶语料随污染清除小幅变化 → 指纹重算 + ANCHOR_REGISTRY_N300
# 锚重记(P2 段扩展换锚,P1 侧 drift 如实记档);live_delta_for
# 增 plane 参(plane≥2 不跨位面回退——位面难度语义不同,缺桶走
# 位面内兜底/回退层 P2 掉血带 15-17)。⚠️ 版本号勘误(迁移审计 w240(git 历史)):本条在
# 快照 note 链里记作 v9(生成器 note 链自 迁移审计 w109(git 历史) 批起与 _SAMPLER_VERSION
# 错位 +1);快照 note 链自 v10 起与本常量对齐。
# v10(ADR-0404,迁移审计 w240(git 历史)):**boss 桶键 Σboard→净星深**(上场件
# Σ(star−1),与 ADR-0399 HandoffSnapshot star_sum−deployed_n /
# p2_form_key star_depth 同源口径;单一源=_boss_star_depth)。修
# 迁移审计 w238(git 历史) 实证的方向冲突(3合1 消耗场上副本 → Σboard −2/次 → 键落浅桶,
# 而浅桶期望伤害更大 → sim 判「升星→boss 伤害↑」与 [27] 机制相反):
# 净星深下 1★→2★ 合并键 +1 永不落浅桶;重生成后 P1 boss 语料
# (49 行)全落桶 0——旧 Σboard 桶 9/12/15 的「条件性」系键口径伪影,
# 真值≈无条件期望 27.57(≈旧全池 fallback 27.33,交叉自洽)。
# encounter/reward/supply 桶键不动(Σboard);池内容变(指纹重算)+
# 迁移审计 w238(git 历史) 常数表重标定(registry handoff_boss_e_damage 键域
# {9,12,15}→{0})。
# v11(ADR-0407,`w250_delta_pool/`):encounter 桶键 depth→rung(_settle_rung 同源;
# 解批⑬ F1 暂缓——扩容后 rung 主桶 n=23/27 达标、梯度显著,而 depth
# 键下期望伤害真平 p=0.87)。reward/supply depth 键不动;池内容变。
# v2(ADR-0268):加防饥饿守卫——n<BUCKET_MIN_N 的桶降级采样
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
# (生产流根单一源见顶部 import:_AUTO_REPLAY_DIR 别名指向
# kernel/cw_observe.DEFAULT_REPLAY_DIR = telemetry/live;仓根锚定与
# 布局语义随根常量块统一,审查#7 的 cwd 敏感问题一并消除。)



class DeltaPoolUnavailable(RuntimeError):
    """auto 模式找不到可用 Δ 池源——显式选 snapshot/fallback。"""



def pool_fingerprint(pool: dict) -> str:
    """池指纹:hash(池内容规范化 + 桶宽 + 采样器版本)。

    只哈希内容盖不住采样器语义(分桶宽/回退策略变了,同 seed
    结果变而指纹仍显示命中——二轮#5),故语义常量一并入指纹。
    """
    import hashlib
    import json as _json
    # ADR-0362(`w157_p2/`):canon 多一层位面({节点:{位面:{桶:Δ}}})——
    # plane 维是池内容的一部分(位面分离语义),入指纹。
    canon = _json.dumps(
        {n: {str(p): {str(b): sorted(v) for b, v in sorted(buckets.items())}
             for p, buckets in sorted(planes.items())}
         for n, planes in sorted(pool.items())},
        ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(
        f'v{_SAMPLER_VERSION}|w{DEPTH_BUCKET_W}|{canon}'.encode()).hexdigest()[:16]



# 节点类型归一(Δ池配对共享件唯一表;快照生成器经本表消费,
# 消灭生成器/池两份镜像字典的漂移面)
NT_MAP: dict[str, str] = {'普通战斗': 'battle', '遭遇': 'encounter',
                          '奖励': 'reward', '首领': 'boss', '补给': 'supply'}


def hp_pair_endpoint_admissible(row: dict) -> bool:
    """outcome 行可否作 Δ池 hp 差分端点(共享过滤件谓词,ADR-0582)。

    - 合成行(source='synthetic_supply',全仓唯一写者 =
      cw_loop._record_supply_outcome,hp 取 last_state 战前快照)
      恒 False——**快照不是事件**(ADR-0577 §3.3 取证链,先验
      「陈旧直到证伪」):相邻差分把「前一行差分取反」记成补给
      增益(镜像律,语料复核 155/170=91.2%),并顶替后行真实
      战斗差分(+2 型被顶成 −20 型)。
    - 其余行走 ``_outcome_hp_trusted`` 单一源(缺字段=可信,边界
      声明在其常量注):conf<0.9 的真实行在本语料全部是终局
      loss_page hp=0 的 OCR-miss 兜底行(败页血条不可读),入
      配对 = 死亡腿伪值入池,且被节点冷启动表兜底误标『补给』。
    - 真实结算行(source=''/recovered,屏面**当时**读取,无快照
      携带机制)不受 source 过滤影响。

    判据语义 = ADR-0577 装配端 ``_settlement_hp_usable`` 延伸到
    Δ池消费面(0577 §3.2 自限「降权只及步进链」,扩面依据见
    ADR-0582);惰性 import 防 sim↔telemetry 模块级新环
    (telemetry.recorder 已模块级依赖 sim.ledger_hooks)。
    """
    if row.get('source') == 'synthetic_supply':
        return False
    from sr_od.application.currency_war.telemetry.query import (
        _outcome_hp_trusted,
    )
    return _outcome_hp_trusted(row)


def pair_outcome_rows_to_pool(
        seqs: dict[str, list[dict]], *,
        boards: dict, star_depths: dict, deployed_names: dict,
) -> tuple[dict, dict]:
    """run 分组 outcome 序列 → (Δ池, 构成统计)(共享配对件,ADR-0582)。

    快照生成器(cw_delta_pool_gen.build_pool)与 auto 池
    (_pool_from_replay)共同消费——两处曾各持一份镜像循环,过滤
    语义单侧修改即破坏 auto/snapshot 指纹收敛判据(无标签行案的
    教训:两侧同步修,见 _pool_from_replay 的指纹判据注),本函数
    把「行级过滤+配对」收成单一实现消除第三源漂移。

    行级过滤三步,**顺序有语义**:

    1. hp0 瞬态剔除(v12):非终局 hp==0 是结算过渡帧伪读
       数(紧随的同轮行血量恢复真值),配对前剔除;终局位保留
       (真死)。「终局」按本 run **原始序列**末行判,先于步骤 2;
    2. 端点资格过滤(:func:`hp_pair_endpoint_admissible`,ADR-0582):
       合成行/低可信行**移行桥接**——从序列移除、邻行重配对(先例
       = v12 hp0 瞬态「剔除后差分跨过它直接配对」)。不采用断链:
       断链会把真实战斗差分(如 +2)丢失、留下跨合成行错值;
    3. 相邻差分入桶:delta = 后行 hp − 前行 hp,归属后行的节点
       类型/位面/桶键(battle/encounter=rung,boss=净星深,
       其余=Σboard 深度桶;键语义出处见 _pool_from_replay 注)。

    :param seqs: 按 run_id 分组的 outcome 行(调用方已过 runs_filter/
        隔离清单/hp_after 非 None);本函数会按 (plane, round) 原地
        排序各 run 序列(与既有两实现同语义)。
    :param boards: decisions join 的 Σboard 桶键物料(键=(run,plane,round))。
    :param star_depths: decisions join 的净星深(同键;boss 桶键)。
    :param deployed_names: decisions join 的上场名单(同键;rung 判据)。
    :return: (pool, stats);stats 键 = ``runs``(逐 run 入池行数,
        post-步骤 1)/ ``unlabeled_dropped`` / ``hp0_transient_dropped``
        / ``synthetic_supply_dropped`` / ``hp_conf_dropped``(四类剔除
        计数,如实披露不静默)/ ``battle_killed``(ADR-0306 P1 逐桶
        killed 列表,快照生成器胜率统计消费)。
    """
    pool: dict = {}
    stats: dict = {
        'runs': {},
        'unlabeled_dropped': 0,
        'hp0_transient_dropped': 0,
        'synthetic_supply_dropped': 0,
        'hp_conf_dropped': 0,
        'battle_killed': {},
    }
    for run, seq in seqs.items():
        seq.sort(key=lambda o: (o.get('plane') or 0, o.get('round_num') or 0))
        # 步骤 1:hp0 瞬态伪读数(终局位保留;判据在原序列上)
        cleaned: list[dict] = []
        for i, o in enumerate(seq):
            if o['hp_after'] == 0 and i < len(seq) - 1:
                stats['hp0_transient_dropped'] += 1
                continue
            cleaned.append(o)
        stats['runs'][str(run)] = len(cleaned)
        # 步骤 2:端点资格过滤(移行桥接,ADR-0582)——判定唯一闸 =
        # :func:`hp_pair_endpoint_admissible`(判据禁第二源;此处只
        # 按 source 族分类计数,便于披露归因)
        kept: list[dict] = []
        for o in cleaned:
            if hp_pair_endpoint_admissible(o):
                kept.append(o)
                continue
            if o.get('source') == 'synthetic_supply':
                stats['synthetic_supply_dropped'] += 1
            else:
                stats['hp_conf_dropped'] += 1
        # 步骤 3:相邻差分入桶(归属后行)
        for a, b in zip(kept, kept[1:], strict=False):
            raw_nt = b.get('node_type') or ''
            nt = NT_MAP.get(raw_nt, raw_nt)
            if not nt:
                # 2026-08-22 retrofix(ADR-0239 配对配套):历史死链
                # node_type 置 None——无标签行不入池(标签不可信的
                # "经验分布"是幻觉地基),计数披露。此判据必须两侧
                # (auto/snapshot)同态:单侧缺失会让两态指纹结构性
                # 永不相等,指纹相等性无法用作收敛判据。
                stats['unlabeled_dropped'] += 1
                continue
            # ADR-0362:差分归属后行位面(P1r9→P2r1 归 plane=2;
            # 位面难度语义不同,混桶=P1 池被 P2 掉血带污染)
            plane = int(b.get('plane') or 1)
            k = (run, b.get('plane'), b.get('round_num'))
            dep = boards.get(k)
            sd = star_depths.get(k)
            if dep is None:
                continue
            delta = b['hp_after'] - a['hp_after']
            if nt == 'battle':
                # ADR-0279:battle 按 rung 一维分桶(结算前 board_before
                # + deployed join;rung 定义单一源=_engines_count)。
                bucket = _engines_count(
                    b.get('board_before') or {},
                    deployed_names.get(k, frozenset()))
                # ADR-0306:胜判定权威口径=killed(结算屏 extras),逐
                # 样本留档供快照 META 逐桶胜率统计;只辖 plane=1
                # (boss_win_p 消费面是 P1 回退层,P2 语料不足)。
                if plane == 1:
                    stats['battle_killed'].setdefault(
                        bucket, []).append(b.get('killed'))
            elif nt == 'boss':
                # ADR-0404:boss 桶键=净星深(上场件 Σ(star−1))——
                # Σboard 键下 3合1 升星使键 −2/次落浅桶,与机制相反。
                if sd is None:
                    continue
                bucket = min(sd // DEPTH_BUCKET_W, 5) * DEPTH_BUCKET_W
            elif nt == 'encounter':
                # v11(ADR-0407):encounter 桶键 depth→rung(与 battle
                # 同源 _engines_count;dep 键下期望伤害真平 p=0.87,
                # rung 键梯度单调显著)。
                bucket = _engines_count(
                    b.get('board_before') or {},
                    deployed_names.get(k, frozenset()))
            else:
                # reward/supply 沿用 Σboard 深度分桶。
                bucket = min(dep // DEPTH_BUCKET_W, 5) * DEPTH_BUCKET_W
            pool.setdefault(nt, {}).setdefault(
                plane, {}).setdefault(bucket, []).append(delta)
    return pool, stats


def _pool_from_replay(replay_dir: Path) -> tuple[dict, dict]:
    """从生产 live 流根的 jsonl 构建 Δ 池 + 构成 meta(auto 池解析体)。

    配对口径(r340 起):decisions 每轮取末行板深(Σboard),
    outcomes 同 run 按 (plane, round) 排序后相邻轮 hp 差分。
    半写行跳过并计数(生产 append 进行中尾行可能撕裂)。
    ADR-0362:差分归属后行位面——{节点:{位面:{桶:[Δ]}}}。
    **行级过滤与配对全部委托 :func:`pair_outcome_rows_to_pool`**
    (ADR-0582:与快照生成器单件同源,禁在本函数再长配对逻辑)。
    **run 级隔离与快照生成器同判据**(ADR-0595 适用范围含 auto 池:
    判据单一源 = cw_delta_pool_gen._run_quarantine_reason,本函数是
    消费方非第二实现;auto 池 = resolve_pool('auto') 是 simulate_p1
    的缺省池,假局/sim 批 run 不入缺省校准路径——ADR-0582 方案审
    阻断-1「默认路径继续吃毒」同型禁再犯)。
    """
    import json as _json

    # 判据单一源(ADR-0595):函数级 import,防 pool↔cw_delta_pool_gen
    # 模块级新环(生成器侧对 pool 同为函数级消费,先例同法)。
    from sr_od.application.currency_war.sim.cw_delta_pool_gen import (
        _run_quarantine_reason,
    )
    skipped: dict[str, int] = {}
    quarantined_hits: set = set()

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
    # ADR-0404:boss 桶键=净星深;v11 起桶键判据需 deployed 名单
    # (rung)也辖 encounter——decisions 行 join;reward/supply 仍用
    # Σboard(boards)。
    star_depths: dict = {}
    # ADR-0279:battle rung 判据需上场名单(希儿系=单卡依赖)——
    # 从 decisions join deployed;join 缺失时希儿系可能漏计(rung
    # 低估 1 档),与批⑬盲区声明一致。
    deployed_names: dict = {}
    for d in _rows('decisions.jsonl'):
        if _run_quarantine_reason(d.get('run_id')) is not None:
            quarantined_hits.add(d.get('run_id'))
            continue
        st = d.get('state') or {}
        b = st.get('board') or {}
        k = (d.get('run_id'), d.get('plane'), d.get('round_num'))
        boards[k] = sum(b.values())
        star_depths[k] = _star_depth_from_rows(st.get('deployed'))
        deployed_names[k] = frozenset(
            x.get('char_id') or '' for x in (st.get('deployed') or [])
            if isinstance(x, dict))
    seqs: dict[str, list[dict]] = {}
    for o in _rows('outcomes.jsonl'):
        if o.get('hp_after') is None:
            continue
        if _run_quarantine_reason(o.get('run_id')) is not None:
            quarantined_hits.add(o.get('run_id'))
            continue
        seqs.setdefault(o.get('run_id'), []).append(o)
    pool, stats = pair_outcome_rows_to_pool(
        seqs, boards=boards, star_depths=star_depths,
        deployed_names=deployed_names)
    meta = {'source_dir': str(replay_dir), 'runs': stats['runs'],
            'skipped_lines': skipped,
            'unlabeled_dropped': stats['unlabeled_dropped'],
            'hp0_transient_dropped': stats['hp0_transient_dropped'],
            'synthetic_supply_dropped': stats['synthetic_supply_dropped'],
            'hp_conf_dropped': stats['hp_conf_dropped'],
            # ADR-0595:被隔离 run 与快照生成器 META 同名披露(没命中=
            # 清单/规则过期,该清理;与 build_pool 同语义)。
            'quarantined_hits': sorted(quarantined_hits)}
    return pool, meta



def _normalize_pool(raw: dict) -> dict:
    """桶键/位面键归一 int(json round-trip 会变字符串键——str 键会让
    live_delta_for 的 int 桶查询全 miss = 快照静默失效;ADR-0362 起
    池形状 {节点:{位面:{桶:[Δ]}}},两层都归一)。"""
    return {n: {int(p): {int(b): list(v) for b, v in buckets.items()}
                for p, buckets in planes.items()}
            for n, planes in raw.items()}



def plane_view(pool_map: dict, plane: int = 1) -> dict:
    """取池的**单位面视图**({节点:{桶:[Δ]}};ADR-0362,`w157_p2/`)。

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

    - ``'auto'``(默认):生产 live 流根实时构建(进程内缓存一次
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
        from sr_od.application.currency_war.data.cw_delta_pool_data import (
            META as _META,
        )
        from sr_od.application.currency_war.data.cw_delta_pool_data import (
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



def _json_loads_path(p: Path) -> dict:
    import json as _json
    return _json.loads(p.read_text(encoding='utf-8'))



def live_delta_for(node_type: str, key: int,
                   rng: random.Random, *,
                   pool_map: dict | None = None,
                   plane: int = 1) -> int | None:
    """按节点类型 + 分桶键取实机经验 Δ;无匹配桶 → None(调用方走旧模型)。

    **位面维(ADR-0362,`w157_p2/`)**:``plane`` 选池的位面层;plane≥2
    **不跨位面回退**——位面难度语义不同(P2 掉血带 15-17 vs P1
    battle -7~-13),跨位面借样本=口径混桶;该位面桶缺 → 位面内
    兜底链(下探/全池合并)→ 仍空 → None(调用方走 P2 回退层
    掉血带,见 ``node_delta`` 的 plane 分支)。P2 语料 44 行,
    条件化分桶不做(每桶 n<5,防饥饿守卫辖)——实际采样≈位面内
    全池合并的经验分布(迁移审计 w156(git 历史) §2 分层结论)。

    **桶键语义按节点分流(ADR-0279,批⑬)**:

    - ``battle``:``key`` = 成型度 rung(0-4,池桶键即 rung;
      与 ``boss_settle_delta`` 的 rung 定义同源 ``_engines_count``)。
      桶不可达时逐级下探更低 rung(信息最接近的可及桶);全不可达
      → 全池合并兜底(rung 信息缺,保经验分布方差;批⑬ F3「池均值
      兜底」形态);池空 → None。
    - ``encounter``:``key`` = **成型度 rung**(v11,ADR-0407,`w250_delta_pool/`;
      与 battle 同源 ``_engines_count``/``_settle_rung`` 单一源。
      批⑬ F1「rung 样本不足暂 depth 分桶」经扩容+键查证解禁:depth
      键下期望伤害真平(Σboard<12 vs ≥12 置换检验 p=0.87,Spearman
      −0.001;净星深键同样无梯度),而 rung 键下梯度单调且显著
      (r0 n=23 EΔ−24.9 / r1 n=27 −15.6 / r2 n=6 −4.3,CI 不交叠)
      ——「深板扛遭遇」主通道在 encounter 节点以 rung 维为真载体,
      板面件数本身不可兑换伤害减免)。分桶/下探路径与 battle 共式
      (域内缺桶逐级浅侧回退;邻接宽=rung±1)。
    - ``boss``:``key`` = **净星深**(迁移审计 w240(git 历史)/ADR-0404:上场件 Σ(star−1),
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

    **防饥饿守卫(ADR-0268,批③ F1)**:命中的桶 n<BUCKET_MIN_N
    时不裸采样——n=1 的桶(如 battle 桶 6 恒 -11)等于把该深度
    锁死在唯一样本上,任何把板深推过桶边界的策略臂都被系统性
    伪惩罚(深度 6 悬崖)。降级策略:候选 = 本桶∪浅邻桶、本桶∪
    深邻桶、该节点全池均匀,取**方差最小**者采样(合并天然加权,
    样本多的邻桶主导);候选并列时按 浅邻→深邻→全池 序(确定
    性)。无任何可合并邻桶(极端小池)时退回裸样本——守卫降级
    采样,不改变「缺桶 → None」的既有两态语义(depth 路;battle/
    encounter 路的全池兜底见上)。邻接宽随键语义:battle/encounter
    =rung±1,其余=桶宽 ±DEPTH_BUCKET_W。
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
        bucket = min(key // DEPTH_BUCKET_W, 5) * DEPTH_BUCKET_W
        src_b = bucket if _map.get(bucket) else bucket - DEPTH_BUCKET_W   # 缺桶浅侧回退(r343 E)
        samples = _map.get(src_b)
        if not samples and node_type in ('reward', 'supply'):
            # ADR-0292:reward/supply 全池兜底(缺桶不退常数,
            # 语料真值优先;防饥饿守卫照常辖)
            samples = [d for v in _map.values() for d in v]
        if not samples:
            return None
        width = DEPTH_BUCKET_W
    if len(samples) >= BUCKET_MIN_N:
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

