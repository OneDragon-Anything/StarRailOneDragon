"""criteria/levelup——升级面判据(最优概率带单判据 + 单帧原子发射)。

判据体系 = 升级触发统一与资金门重定义批(用户裁定 2026-10-18 四条;
触发/资金门/删除面权威基准 = strategy-docs/11_shop_decisions.md §2)+
2026-10-17-levelup-shop-transition 迭代收尾(资格门全链判定单一源
:func:`upgrade_gate_verdict`,支出形态单帧原子,跨画面键退役):

- **触发单判据三分派**(11 号稿 §2 停留门「可达最优等级」模型承接):
  以锁定线星级目标(need_star)的最优概率带为唯一升级判据——
  带下界 > 当前等级 → 升级(键 ``stay_gate``);等级 ∈ 带或被推过带上
  界 → 停留刷新(不触发);无未完成星级目标 → 自然升级(键
  ``natural``)。辖域 = 锁定后 ∧ plane2_started(P1 与未锁定期零主动
  升级,阶段保护)。旧五臂(人口位/arm0/富余段-L3/概率账)随批删除
  ——非带驱动臂都能绕过「等级该不该升」核心判据,与统一裁定冲突;
- **资金门**(11 号稿 §2 资金线门):下界单一源 =
  saturation_line(cap_resolved)(当前局最高利息线;买断制 cap=0 ⇒
  下界 0 ⇒ 门恒过),口径 = 现金(花后金 = 现金 − 整批成本,活期
  退金不进放行算术);花后破线恒整批推迟等钱,拒因键
  ``levelup_fund_line_defer``(用户裁定 2026-10-30:不存在升级卖牌
  凑金——保持最大压牌库,钱够了再升;凑金域分派臂已整删);
- **支出形态**(单帧原子):判据通过 → 同帧发购买经验整批(实付上界
  = 发射时授权值,授权不跨帧携带)——「买一半」缺陷(逐帧单击 ×
  静态阈值逐帧重闸)由发射原子性消解;
- **拦截层**(11 号稿 §2 拦截层处置):保留 = 资金线门
  (:func:`levelup_fund_gate`)/ 等级帽闸(``lv9_stop``/
  ``xp_ledger_stop``)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_game_state import (
    gold_of,
    level_of,
    plane_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_reward_node import (
    reward_node_suppressed,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )


def lv9_stop(level: int, level_max: int) -> bool:
    """等级上限停(义务侧消费)。历史键名 'lv9_stop':cap=9 旧语义时代
    命名,现语义 =「等级达注册表 level_max 即拒发升级」——键串保留
    不改名(改键牵连判读脚本与历史档案可比性,纯改名无收益)。

    单一源 = 注册表 ``level_max``(kernel/cw_registry.py,实机真值 10,
    与 cw_economy.xp_apply_clicks「封顶 10」live 机制语义同源);sim 与
    live 同一规则核共享本单一源(原 ``sim_decision_registry`` 注入视图
    已停用)。⚠ 与同文件 ``cap_resolved``(利息
    上限)毫无数值或语义关联,禁接错源。

    ``level_max`` = 消费位传上下文注册表的 ``.level_max``(禁裸常数),
    **必填**:消费位(备战第 4 步升级检查/商店会话升级意图出口两屏同参)已全量接入调用,
    过渡缺省通道已拆除;禁新消费位依赖缺省。
    """
    return level >= level_max


def xp_ledger_stop(xp_progress: tuple[int, int] | None,
                   level_max: int) -> bool:
    """XP 期望账本升级停判据(lv9_stop 的轮内盲区补位,与 lv9_stop
    同位合取消费;语义基准 = 推进算子单一源 ``kernel/cw_economy.
    xp_apply_clicks``)。

    为什么需要(病灶实测):商店域逻辑态直写只写 xp 元组不写 level
    域(升档等观察覆盖,kernel/cw_action_report 上报函数族买经验行
    双类型时代遗留;双类型已退役,单类型单行);ALL IN 窗逐击决策环
    (decide_shop_screen 驱动器
    逐动作直写推进)内 level 域滞留轮初值 ⇒ lv9_stop 恒 False,而
    clicks_to_next_level 按推进后元组的新级 need 续算 ⇒ 同窗内连买
    下级(sim n100 s77000 段 44/100 局 R9 击数超整买上限,批计 ≥864 金,
    20260913 sim 找问题报告问题 1)。本判据改读「XP 期望账本」——

    判据式:元组不变量 = need 槽恒为 ``XP_TO_NEXT_LEVEL[账本真等级]``
    (xp_apply_clicks 写端写入,跨门槛推进后 need 槽换新级门槛;门槛表
    按级严格递增)⇒ ``need >= XP_TO_NEXT_LEVEL[level_max]`` ⟺ 账本真
    等级 ≥ level_max,即已到/越过升级目标,拒发。

    跨域同构:sim/live 消费同一函数,注入视图 level_max 同源 = 10
    (``kernel/cw_economy.py::MAX_PLAYER_LEVEL`` 单一尺,sim 重做反转后
    不存在第二把尺);门槛表键域 3-9 无表项 ⇒ 判据两域恒不覆盖,停止语义
    两域同由 lv9_stop 承载。

    ``xp_progress`` = 状态容器 ``gs.xp.value`` 原样透传(缺读 None 不覆盖,
    与 clicks_to_next_level 的缺省兜底方向一致——停判据缺读宁可放行
    交 lv9_stop/量闸管辖,不制造静默拒)。单一源 = kernel
    ``cw_economy.XP_TO_NEXT_LEVEL``,禁第二份表。
    """
    if not xp_progress or len(xp_progress) < 2:
        return False
    from sr_od.application.currency_war.kernel.cw_economy import (
        XP_TO_NEXT_LEVEL,
    )
    threshold = XP_TO_NEXT_LEVEL.get(int(level_max))
    if threshold is None:
        return False   # level_max 无门槛表项(live=10):判据不覆盖
    return int(xp_progress[1]) >= threshold


def spend_unified(clicks_to_next: int, gold: int, click_cost: int) -> bool:
    """P48 整买纪律(D-BUYNOTE):整批 XP 放行判据。

    仅当「一次买齐到下一级」的金够付时放行(clicks×click_cost ≤ gold)
    ——散买 XP(买不够升级)零收益,拦截(line_and_upgrade §2.2 裸金
    足支的判据位;P72(1) 整买形态 = Leontief 互补的实现载体)。
    """
    if clicks_to_next <= 0:
        return False
    return gold >= clicks_to_next * click_cost


def _plane_round_of(state: GameState) -> tuple[int, int]:
    """(plane, round_num) 状态容器读(读口单一源,prep 链结构化段 2 起
    gs 单形态)。"""
    return plane_of(state), round_num_of(state)


# ============================================================ 最优概率带(§2.1 停留门)


def prob_band_of_cost(cost: int) -> tuple[int, int]:
    """费用档 → 最优概率带 (下界,上界)(line_and_upgrade §2.1 停留门)。

    带 = **搜索域 1..9 内** REFRESH_PROB 概率峰值的等级区间,平顶整段
    取全部峰值等级(1 费带 [1,3] 类)——成员由 REFRESH_PROB 直接计算。
    禁写成「全域最高值区间 ∩ ≤9」:4/5 费全域峰在 lv10(0.40/0.25),
    截掉得空集;域内峰口径下 4/5 费带 = [9,9](lv9 的 0.30/0.10)。

    lv10 出域依据:P35 已证停手窗 lv9→10 恒负 + ``peak_refresh_level``
    在产表即此口径(1..9 域内取峰,cw_plane_table);带成员与该表的
    关系 = 带上界取 max(带)(单点峰形态,并列取高档),peak_refresh_
    level 作域上限校验,非带定义本体(line_and_upgrade §2.1 带成员
    规则与在产载体关系申报)。
    """
    from sr_od.application.currency_war.data.cw_shop_odds import refresh_prob
    c = min(5, max(1, int(cost)))
    probs = [refresh_prob(lv, c) for lv in range(1, 10)]
    peak = max(probs)
    return probs.index(peak) + 1, 9 - probs[::-1].index(peak)


def _held_max_star(state: GameState, name: str) -> int:
    """同名持有最高星(bench ∪ 场上全场域;未持有 = 0)。

    星级目标完成判定 = 持有最高星 ≥ 必要星级(need_star 以「追到底」
    语义登记,合成路径的中间拷贝由最高星天然承载,line_and_upgrade
    §1.5)。"""
    best = 0
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_units_of,
        deployed_rows_of,
    )
    front, back = deployed_rows_of(state)
    for u in (*bench_units_of(state), *front, *back):
        if u is not None and (u.char_id or '') == name:
            best = max(best, int(u.star or 1))
    return best


def unfinished_star_targets(state: GameState) -> list[tuple[str, int, int]]:
    """未完成星级目标集(line_and_upgrade §1.5/§2.1;锁定线 need_star
    驱动)。

    锁定线 need_star 表中持有最高星 < 必要星级的成员,返回
    (角色名,必要星级,当前实费档)。定义 3★ 就追到底无降档、定义
    2★ 即完成(§1.5);辅助 1★ 持有即完成,未持有者入集(首张即目标)。
    费用档 = ``effective_cost`` 当前实费 resolved 口径(银狼系变费后
    实档,档漂移时带随之重取)。未锁定期 = 空集(停留门覆盖锁定后,
    line_and_upgrade §2.1)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    from sr_od.application.currency_war.kernel.cw_economy import (
        effective_cost,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.session_scope import (
        line_members_view,
    )
    view = line_members_view(state)
    if not view.locked:
        return []
    comp = get_comp(view.comp_name) if view.comp_name else None
    if comp is None:
        return []
    out: list[tuple[str, int, int]] = []
    for name, need in (comp.need_star or {}).items():
        need_i = int(need)
        if _held_max_star(state, name) < need_i:
            out.append((name, need_i, effective_cost(state, name)))
    return out


def stay_target_of(state: GameState) -> tuple[str, int, int] | None:
    """当前停留目标 = 未完成星级目标中费用档最低者(shop_session §2.4
    多目标停留顺序:先低费后高费,与搜牌等级节奏一致;并列取注册表
    名序,确定性)。"""
    targets = unfinished_star_targets(state)
    if not targets:
        return None
    return min(targets, key=lambda t: (t[2], t[0]))


def _locked_and_plane2(state: GameState,
                       session: StrategySession) -> bool:
    """升级触发单判据的共同适用范围门:锁定后 ∧ plane2_started 双条件。

    P1 硬规则锁定子局星级目标存在仍不覆盖(P1 零主动升级,阶段保护:
    P1 经验论证在案〔到 7 级为 P2 人口目标,P1 冲级与「P1 恒不刷」及
    经验账冲突,line_and_upgrade §2.1〕;P2 未锁定窗口同样零升级——
    窗口靠候选缺件刷新,锁定后带驱动接管)。窗口谓词形态 =
    ``plane2_started_of``(宪法第 2 条合规)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.session_scope import (
        line_members_view,
        plane2_started_of,
    )
    return line_members_view(state).locked and plane2_started_of(state)


# ============================================================ 升级触发(单判据三分派)

#: 触发键值域(发出 auth_basis 记录与命中计数键 ``levelup_trigger_<键>``
#: 共用;11 号稿 §2 三分派一一对应,分派 2 停留无键)。
TRIGGER_STAY_GATE: str = 'stay_gate'
TRIGGER_NATURAL: str = 'natural'


def upgrade_trigger(gs: GameState, session: StrategySession,
                    registry: DecisionV2Registry | None = None,
                    ) -> tuple[bool, str]:
    """升级触发单判据三分派(11 号稿 §2 停留门「可达最优等级」模型;
    主入口)。

    以锁定线星级目标(need_star)的**最优概率带**为唯一升级判据,
    三分派互斥完备:
    ① 存在未完成星级目标 ∧ 其最优带下界 > 当前等级 → 升级(升到带内
       去刷),键 ``stay_gate``;
    ② 存在未完成星级目标 ∧ 等级 ∈ 带 ∨ 等级 > 带上界(纯状态描述,
       历史升级/自然经验所致,单调不可降)→ 停留刷新,不升,无触发
       命中;
    ③ 无未完成星级目标(全部追完,或锁定线无追星目标)→ 自然升级
       (不停留),键 ``natural``。

    辖域 = 锁定后 ∧ plane2_started(:func:`_locked_and_plane2`;P1 与
    未锁定期零主动升级)。旧五臂(人口位/arm0/富余段-L3/概率账)已删
    ——四个非带驱动臂都能绕过「等级该不该升」核心判据(用户裁定
    2026-10-18:升级只保留「目标角色在哪个等级刷出概率最好」一个判据,
    板面坐满等战力义务触发删除)。

    奖励帧抑制覆盖升级触发(reward_node_suppressed 闸,消费位 = 本函数
    调用方前置)。返回 (是否触发,触发键;``registry`` 形参 = 调用方
    统一传参形态保留,判据本体零注册表消费)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        level_of,
    )
    if not _locked_and_plane2(gs, session):
        return False, ''
    target = stay_target_of(gs)
    if target is None:
        return True, TRIGGER_NATURAL
    lo, _hi = prob_band_of_cost(target[2])
    if lo > level_of(gs):
        return True, TRIGGER_STAY_GATE
    return False, ''


# ============================================================ 发射资格门全链判定(两屏同参单一源)


#: 判定结论值域(:func:`upgrade_gate_verdict`;两屏同参消费——商店会话
#: 升级意图出口与备战升级执行,资格门全链两屏同参)。
GATE_MISS: str = 'miss'              # 判据未命中(单判据不触发;非门拒)
GATE_DEFER: str = 'defer'            # 资格门拦(拒因计数已写入 counters)
GATE_EMIT: str = 'emit'              # 全链通过,可发射


def upgrade_gate_verdict(gs: GameState,
                         session: StrategySession,
                         registry: DecisionV2Registry | None = None,
                         counters: dict | None = None,
                         ) -> tuple[str, str, int, int]:
    """升级发射资格门全链判定(两屏同参单一源;商店会话升级意图出口与
    备战升级执行两屏同参消费——**禁任一侧子集化或第二实现**,漏报任一
    门则转场/发射后继不能合法兑现,开/关店环复活)。

    门序 = 现役发射门序:①奖励帧抑制(reward_node_suppressed)
    ②等级帽(level_max)③升级判据命中(单判据三分派)④击数 > 0
    ⑤经验批支付门(币种通式:支付币余额 ≥ 整批成本,金本位局直通
    ——金侧守线在门⑥,币种模式解析 = ``cw_investments.blood_xp_mode``)
    ⑥资金线门(现金口径:花后金 = 现金 − 整批 ≥ saturation_line;花后
    破线恒 defer 等钱——凑金域分派臂已整删,用户裁定 2026-10-30:不
    存在升级卖牌凑金,保持最大压牌库,钱够了再升)。全部通过 →
    ``emit``。

    返回 ``(verdict, arm_key, clicks, click_cost)``:

    - ``miss``:判据未触发(无拒因计数——判据未命中非门拒);
    - ``defer``:①-⑥任一门拦,拒因计数键已写入 ``counters``(键域:
      levelup_reward_node_defer / levelup_reject_level_cap /
      levelup_zero_clicks_defer / xp_batch_payment_defer /
      levelup_fund_line_defer;两屏判读面共享同一键域——资金面拒因
      统一 ``levelup_fund_line_defer``,金不足帧与等级帽/奖励帧 verdict
      同形,语义按「升级不发射帧」统称);
    - ``emit``:可发射(血本位局 = 经验批支付门过即 emit;金本位局 =
      花后守线 ∧ 整买纪律过)。``arm_key`` = 触发键(miss/defer
      恒 '');``clicks/click_cost`` = 整级批参数(emit 语境有效,
      miss/defer 恒 0)。

    ``counters`` = None 时静默(契约层同款)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        clicks_to_next_level,
        xp_batch_payment_gate_for,
        xp_click_cost,
    )
    from sr_od.application.currency_war.kernel.cw_investments import (
        blood_xp_mode,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        contracts,
    )

    def _count(key: str) -> None:
        if counters is not None:
            counters[key] = counters.get(key, 0) + 1

    # ===== 资格门①②③(奖励帧抑制 → 等级帽 → 升级判据)=====
    if reward_node_suppressed(gs):
        _count('levelup_reward_node_defer')
        return GATE_DEFER, '', 0, 0
    reg = registry if registry is not None else DEFAULT_REGISTRY
    if not contracts.ensure_contract(('levelup', 'lv9_stop'),
                                     contracts.ContractCtx(), counters):
        return GATE_DEFER, '', 0, 0
    if lv9_stop(level_of(gs), reg.level_max):
        _count('levelup_reject_level_cap')
        return GATE_DEFER, '', 0, 0
    if not contracts.ensure_contract(
            ('levelup', 'upgrade_trigger'),
            contracts.ContractCtx(), counters):
        return GATE_DEFER, '', 0, 0
    trig, arm_key = upgrade_trigger(gs, session, reg)
    if not trig:
        return GATE_MISS, '', 0, 0
    _count(f'levelup_trigger_{arm_key}')
    # ===== 资格门④:击数 > 0(整级批参数推导前置)=====
    clicks = clicks_to_next_level(gs)
    if clicks <= 0:
        _count('levelup_zero_clicks_defer')
        return GATE_DEFER, '', 0, 0
    click_cost = xp_click_cost(gs)
    # ===== 资格门⑤:经验批支付门(币种通式,金本位局直通)=====
    if not xp_batch_payment_gate_for(gs, session):
        _count('xp_batch_payment_defer')
        return GATE_DEFER, '', 0, 0
    if blood_xp_mode(session) is not None:
        # 血本位局:支付门已过 = 支付可行(血本位无金变现步,资金门无
        # 对象——花血非花金),可发射。
        return GATE_EMIT, arm_key, clicks, click_cost
    # ===== 资格门⑥:资金线门(现金口径单门;花后破线恒 defer)=====
    from sr_od.application.currency_war.strategies.impl.mandate_v1.entry import (
        _levelup_fund_line_ok,
    )
    gold = gold_of(gs)
    if not _levelup_fund_line_ok(gs, session, gold, clicks, click_cost):
        # 花后破线 → 整批推迟等钱(凑金域分派臂已整删——用户裁定
        # 2026-10-30:不存在升级卖牌凑金,保持最大压牌库,钱够了再升;
        # 拒因键 levelup_fund_line_defer,计数点位 = 本判定函数,
        # 两屏同参共享)。
        _count('levelup_fund_line_defer')
        return GATE_DEFER, '', 0, 0
    # 花后守线 ⇒ 现金 ≥ 批(线 ≥ 0)结构性蕴含整买纪律;契约核验与
    # 判据照落(保留面),防御分支保持零计数。
    if contracts.ensure_contract(
            ('levelup', 'spend_unified'),
            contracts.ContractCtx(gold=gold), counters) \
            and spend_unified(clicks, gold, click_cost):
        return GATE_EMIT, arm_key, clicks, click_cost
    # 防御分支(整买纪律与花后守线同式,结构性不可达):零计数保持。
    return GATE_DEFER, '', 0, 0


# ============================================================ 资金线门(拦截层保留件)


def _plane_last_battle(gs: GameState,
                       session: StrategySession) -> bool:
    """位面末最后一战判定(cw4 消费面;单一源 =
    decision_v2.discipline.plane_last_battle 的重导出委托,禁第二实现;
    模块私有——非判据面函数,不入契约/旁路枚举表)。kernel 侧波 2 已切
    状态容器签名,状态容器 gs 直读。"""
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        plane_last_battle as _plb,
    )
    return _plb(gs, session)


def terminal_all_in(gs: GameState, session: StrategySession) -> bool:
    """终局域末战 ALL IN 判定(位面末战 ∧ R_全局 ≤ 1)。

    单一源供 :func:`levelup_fund_gate` 豁免支消费(末位面末战后金无
    任何消费场景,P41 终局清仓恒优/P23 死亡域攥金价值恒零——ALL IN
    维持花光原语义)。``r_remaining`` 门面场字段自算查表(R 含当前
    节点,决策帧最小值 = 末位面末战的 1;禁自推位面数——宪法 01 §8-1
    位面参数化不变量)。
    """
    if not _plane_last_battle(gs, session):
        return False
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.horizon import (
        r_remaining,
    )
    return r_remaining(session, *_plane_round_of(gs)) <= 1


def levelup_fund_gate(gs: GameState, session: StrategySession,
                      gold: int, clicks: int, click_cost: int,
                      cap_resolved: int) -> bool:
    """升级资金线门(11 号稿 §2 资金线门行):升级整批发出前的现金口径
    单门,真 = 放行。

    检查式:花后金 = 现金 − 整批成本,下界单一源 =
    ``saturation_line(cap_resolved)``(当前局最高利息线;口径 = 现金,
    活期退金不进放行算术——发射分支不消费活期资产)。花后破线帧的
    处置 = 恒整批推迟等钱(拒因键 ``levelup_fund_line_defer``;凑金
    域分派臂已整删——用户裁定 2026-10-30:不存在升级卖牌凑金,保持
    最大压牌库,钱够了再升),消费位 = :func:`upgrade_gate_verdict`
    门⑥。

    出辖两支(任一真 = 不设下界,让位语义各有已登记出处):
    - **终局域**::func:`terminal_all_in` 单一源(ALL IN 维持花光原
      语义);
    - **买断制**:cap_resolved = 0 ⇒ saturation_line(0) = 0 ⇒ 门恒过,
      无特判分支(下界随 resolved 链自动消解)。

    下界推导链(利息线 = 花完仍守当期最高利息线):升级整批花穿金位会
    归零利息收入,后续刷新金前提(R 预算线)不可达、等级概率收益零
    兑现——守线使升级不破利息线纪律(与买牌面「跌破利息线要例外理由」
    同一纪律面,11 号稿 §1 金约束门)。
    """
    if terminal_all_in(gs, session):
        return True          # 终局域:末位面末战,守线前提失效
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
        saturation_line,
    )
    return gold - clicks * click_cost >= saturation_line(cap_resolved)
