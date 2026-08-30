"""件价值模型 Phase 1(kernel 估值单一源;W831 v2 §4 落码规格)。

设计单一源 = ``.debug/temp/currency_war/w831_piece_value_design/REPORT.md``
v2(§3.1 分量分解 / §3.3 可加性声明 / §4 落码规格 / §4.3 迁移表 /
§5 判据)+ W833 轻复核三补丁(哨兵语义收敛 / Phase 1.5 对照臂 / G7 折算口径)。

架构定位(设计 §1):买/留/卖/合成四类消费点共用的单一估值函数,
本模块 = **只读估值服务**——不发射动作、不碰金账、不做否决(否决归
W829 支出门,档位应用归 W803,惩罚侧归 W802 κ 外应用)。与既有件
切分见设计 §2.1 重叠面清单;禁第二分配器/第二罚分器/第二门。

**Phase 1 消费面收窄(设计 v2 修正④)**:六分量 dataclass 字段齐备
纯披露,但 ``total`` 合成面只启用 A(激活)/B(贯穿留存)两权重;
C/D/E/F 无权重字段(类型层收窄 = Phase 1 专用两字段
``PieceValueWeightPhase1``,全量 weight 类型 Phase 2 才引入)。
哨兵语义按 W833 补丁④收敛为「**禁进评分/决策路径**」:C/D/E/F
分量可进 telemetry 披露键(纯披露,ADR-0488 范式),禁被消费点
计入 total 或任何排序/授权输入——契约锁兜底见
test_cw_piece_value 锁 6。

纯函数边界(设计 §1.2):零跨帧账本、零副作用、零落盘;同输入
两次调用输出逐位相等。off 臂零漂移:消费点在本模块伞开关关闭时
逐位等于现行基线(零漂移锚 = W802 13 锁同款)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.decision.cw_strategy import StrategySession
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    GameState,
    bench_occupied,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.decision.decision_v2.remediation import (
        RejectReason,
    )

#: 分量 D 的持有份数权重(与 realization._MERGE_HELD_FRAC 同语义同值:
#: merge 候选构造性持有 2 份 → 2/3;份数比非标定值。披露面只读复刻,
#: 行为面单一实现仍在 realization.merge_timing_term——Phase 2-b 收口
#: 时该消费点改为读本分量,平行实现届时删除,设计 §4.3 迁移表)。
_MERGE_HELD_FRAC: float = 2.0 / 3.0


@dataclass(frozen=True)
class PieceValueWeightPhase1:
    """Phase 1 专用权重类型(类型层收窄,W833 补丁④方案 1)。

    **只有 A/B 两个字段**——C/D/E/F 的权重字段在本类型上不存在,
    这是「Phase 1 合成面仅 A/B 非零」的编译期结构(哨兵主实现);
    全量六字段 weight 类型属 Phase 2,提前引入 = 锁红。
    两字段缺省 0.0:权重未标定挂账(设计 §3.1 出处列)前不产生
    任何非零注入,零漂移由消费点伞开关+本缺省双保险。
    """

    w_activation: float = 0.0   # 分量 A 占位权重(出处 P20,辖域 e<2)
    w_retention: float = 0.0    # 分量 B 占位权重(出处 P1+P11,量挂 P34)


def phase1_weight_from_registry(
        registry: DecisionV2Registry) -> PieceValueWeightPhase1:
    """从 registry 权重字段构造 Phase 1 权重(单一参数入口)。

    registry 只持 w_activation/w_retention 两个权重字段(C/D/E/F
    权重字段在 Phase 1 的 registry 上不存在——契约锁兜底断言面,
    见 test_cw_piece_value 锁 6)。
    """
    return PieceValueWeightPhase1(
        w_activation=registry.piece_value_w_activation,
        w_retention=registry.piece_value_w_retention)


@dataclass
class PieceValueBreakdown:
    """六分量分解对象(设计 §3.1;逐分量进 telemetry 披露键)。

    ``total`` 合成面 Phase 1 = A/B 加权和(W833 补丁④:语义精确为
    「C/D/E/F 禁进 total 合成与评分消费,披露键除外」);C/D/E/F
    字段纯披露,零决策消费。
    """

    activation: float    # 分量 A,target 外体系钥匙件激活边际,辖域 e<2(P20)
    retention: float     # 分量 B,跨线留存期权,量占位挂 P34(P1+P11)
    tier_gap: float      # 分量 C,线内缺档成员档位边际(消费 missing_members 单一源)
    merge: float         # 分量 D,可合成对时点占位(P14;ADR-0437/0438 豁免语义不辖)
    bench_cost: float    # 分量 E(负),持位机会成本占位(H 标定挂账)
    interest_cost: float  # 分量 F(负),破息息档损失(P13/P33 口径)
    weight: PieceValueWeightPhase1 = field(
        default_factory=PieceValueWeightPhase1, repr=False, compare=False)

    @property
    def total(self) -> float:
        """Phase 1 合成面:A/B 加权和(C/D/E/F 无权重字段可乘——
        类型层收窄使「其余权重非零」构造性不可能)。"""
        return (self.weight.w_activation * self.activation
                + self.weight.w_retention * self.retention)


def _system_bonds(name: str) -> frozenset[str]:
    """件的过渡体系键集(与 scoring._cand_system_bonds 同源同式:
    TRANSITION_TRAITS 键∩件羁绊;希儿系单卡哨兵键)。"""
    if name == '希儿':
        return frozenset({'希儿系'})
    ch = CHARACTERS.get(name)
    if ch is None:
        return frozenset()
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        TRANSITION_TRAITS as _TRANSITION_TRAITS,
    )
    eng_bonds = {b for b, _t in _TRANSITION_TRAITS}
    return frozenset((set(ch.factions or ()) | set(ch.flows or ()))
                     & eng_bonds)


def _bond_advancing(name: str, bond: str, state: GameState,
                    deployed_names: frozenset[str]) -> bool:
    """件买入并上场后是否使该体系羁绊跨到下一档(board 计数 +1
    恰达下一档;与 realization.missing_members 的 k→k+1 恰达判据
    同式)。希儿系=单卡二元:希儿未在场即跨(部署后成引擎,
    scoring._cand_is_engine_piece 注释同一语义)。"""
    if bond == '希儿系':
        return '希儿' not in deployed_names
    from sr_od.application.currency_war.data.cw_factions import FACTIONS
    info = FACTIONS.get(bond)
    if info is None or not info.tiers:
        return False
    cur = int((state.board or {}).get(bond, 0) or 0)
    return next((t for t in info.tiers if t == cur + 1), None) is not None


def evaluate_piece(piece: object, state: GameState,
                   weight: PieceValueWeightPhase1,
                   registry: DecisionV2Registry,
                   session: StrategySession | None = None,
                   target_scope: frozenset[str] = frozenset(),
                   ) -> PieceValueBreakdown:
    """单一估值函数(设计 §1.2 一行签名的落码形态)。

    与设计签名的偏差声明(均有 why):①``registry`` 显式入参——
    分量常量(息档/κ 族/缺档判定)单一源在 registry,禁模块级
    第二常量面;②``session`` 可选入参——C/D 分量的辖域判据
    (锁定帧缺件)单一源在 cw_intention,经 session 读,传 None
    时 C/D 恒 0(纯披露分量,不影响 Phase 1 消费面 A/B);③
    ``target_scope`` 显式入参——「target 外」辖域由消费点从意向
    态解析后传入,本函数保持对意向态无依赖。

    辖域约定:``target_scope`` 为空 = 非锁定帧,A/B 均按「target
    外」辖域不可判 → 恒 0(Phase 1 试点辖域 = 锁定帧,设计 §4.3)。

    分量语义与出处(设计 §3.1/§6,注释按「结论→出处→边界」):
    - A 激活:target 外体系钥匙件在 e<2 且其体系羁绊 k→k+1 恰达时,
      = w_activation × engine_jump_gold(e)(与 V_D 收益侧同式同源,
      ADR-0352 金口径;P20 证明的是 e0→1 边际的方向与倍数带,序数
      优先);e≥2 恒 0 = P20 辖域硬门控,禁外推。
    - B 留存:target 外件在满息段(金≥息线,P11 满息段买入零息损)
      且 bench 有空位时 = w_retention × 件费用。费用是再遇稀有的
      序数代理(P1:同等级下期望再遇轮数随费用单调增 → 越稀有越囤);
      P34 挂账,证明前占位进入(设计 §3.1 注)。
    - C 档位(披露):件 ∈ 锁定帧缺件清单(missing_members 单一源,
      禁另写缺件判定)时 = Δp_tier × (1−s),与搜牌侧单件形态同构;
      数值不改写 W803 缺口差分(档位侧应用归 W803,设计 §2.1)。
    - D 合成(披露):线内缺档 ∧ 已持 2 份 ∧ 产物可上场时
      = 时点单位 × 2/3 × 剩余战斗轮(P14;占位,Phase 2-b 进消费面)。
    - E 位置成本(披露,负):bench 占用比,量纲归一占位(H 标定
      挂账,设计 §3.1;无新魔数——只报占用率真值)。
    - F 利息成本(披露,负):破息买入的息档损失 = Δ⌊g/10⌋ ×
      interest_rounds(P13/P33 口径);满息段恒 0(P11 直译,锁 3)。
    """
    if isinstance(piece, str):
        name = piece   # 直传件名(测试/判读便利);生产面传 ShopCard/Char
    else:
        name = (getattr(piece, 'name', '')
                or getattr(piece, 'char_id', '') or '')
    ch = CHARACTERS.get(name)
    cost = int(getattr(ch, 'cost', 0) or 0) if ch is not None else 0
    deployed_names = frozenset(
        getattr(d, 'char_id', '') or ''
        for d in (state.deployed or []) if d is not None)
    in_scope = name in target_scope if target_scope else True
    # —— A 激活(消费面)——
    activation = 0.0
    if target_scope and not in_scope and weight.w_activation:
        bonds = _system_bonds(name)
        if bonds:
            from sr_od.application.currency_war.decision.decision_v2.scoring import (  # noqa: E501  懒 import 防 scoring↔本模块环
                _engines_formed,
            )
            e = _engines_formed(state, registry)
            if e < 2 and any(_bond_advancing(name, b, state, deployed_names)
                             for b in bonds):
                from sr_od.application.currency_war.decision.decision_v2.scoring import (  # noqa: E501
                    engine_jump_gold,
                )
                activation = (weight.w_activation
                              * engine_jump_gold(e, state, registry, session))
    # —— B 留存(消费面)——
    retention = 0.0
    if target_scope and not in_scope and weight.w_retention and cost > 0:
        from sr_od.application.currency_war.decision.decision_v2.filters import (  # noqa: E501
            is_emergency,
        )
        if ((state.gold or 0) >= registry.interest_floor()
                and not is_emergency(state, registry)
                and bench_occupied(state.bench or [])
                < registry.bench_capacity):
            retention = weight.w_retention * float(cost)
    # —— C/D 披露(需 session 读锁定辖域;None → 恒 0)——
    tier_gap = 0.0
    merge = 0.0
    if session is not None and target_scope:
        from sr_od.application.currency_war.decision.decision_v2.realization import (  # noqa: E501
            missing_members,
        )
        missing = missing_members(state, session, registry)
        if name in missing:
            tier_gap = registry.realization_delta_p_tier \
                * (1.0 - missing[name])
            raw_copies = sum(
                1 for d in list(state.deployed or [])
                + [b for b in (state.bench or []) if b is not None]
                if getattr(d, 'char_id', '') == name
                and (getattr(d, 'star', 1) or 1) < 2)
            if raw_copies >= 2 and name not in deployed_names:
                from sr_od.application.currency_war.decision.decision_v2.ev import (  # noqa: E501
                    battles_left_plane,
                )
                merge = (registry.realization_merge_timing_unit
                         * _MERGE_HELD_FRAC
                         * battles_left_plane(state, session, registry))
    # —— E/F 披露 ——
    occ = bench_occupied(state.bench or [])
    bench_cost = -(occ / float(registry.bench_capacity)
                   if registry.bench_capacity > 0 else 0.0)
    interest_cost = 0.0
    if cost > 0 and (state.gold or 0) < registry.interest_floor():
        g = state.gold or 0
        before = min(registry.interest_cap, g // 10)
        after = min(registry.interest_cap, max(0, g - cost) // 10)
        interest_cost = -float(before - after) * registry.interest_rounds
    return PieceValueBreakdown(
        activation=activation, retention=retention, tier_gap=tier_gap,
        merge=merge, bench_cost=bench_cost, interest_cost=interest_cost,
        weight=weight)


# ===== 买前 bench 容量预检硬门(ADR-0497;件价值开臂前置件,W852
# ===== REPORT §3 挂账偿付:B 辖域位置成本约束,消费面逻辑不进评分)=====

def bench_reserve(state: GameState, session: StrategySession | None,
                  registry: DecisionV2Registry) -> int:
    """预留空位数(reserve)推导(禁拍死值;状态依赖,逐帧可复算)。

    推导(结论→出处→边界):
    - **基线项 1**(P29 卡点保守处理的直译):P29 明文「bench 占用 ≥
      容量−1 时 H 取禁囤阈值」——每帧至少保 1 个空位给受保护类
      (线内缺档成员 Δp_tier·R_rest ≥ 1.4×R_rest 金当量 / 激活钥匙件
      P20 2.6-2.9×),受保护类单帧到达期望 ≥1 而囤牌期权近零
      (P1:≤2 费再遇 7-15 轮;W846 归因:B 买入 56.7% 为 ≤2 费),
      不对称性恒成立 → 基线 reserve=1 恒在。
    - **开对项 +1/线**:线内同名 1★ 恰持 1 份(合成线开对)数。
      2★ 合成链深 = 3 张,但槽位需求峰值 = 2(第 3 张到达即触发
      merge 完成,满栏合成买合法,W544/ADR-0453,不需空位);已沉没
      1 槽后剩余需求 = 第 2 张的 1 个空位——若该空位被囤牌件占掉,
      整条合成线停在深度 1(沉没 1 槽 + 1 购),其损失大于一枚新
      囤牌的期权值 → 每条开对线 reserve +1。
    - **上限 cap**:registry.piece_value_bench_reserve_cap(扫描旋钮,
      缺省 2 = W852 扫描建议带 {1,2} 上沿);reserve ≥ 1 硬不变式
      (bench_front_full 同款守卫)。
    - 边界:无锁线意向(session 无 v3_intention/未 locked)时开对数
      不可判 → 退基线 1(保守,辖域不明不扩张预检)。
    """
    reserve = 1
    from sr_od.application.currency_war.kernel.cw_intention import (
        IntentionState,
        locked_buy_scope,
    )
    ist = getattr(session, 'v3_intention', None)
    scope = locked_buy_scope(ist) if isinstance(ist, IntentionState) else None
    if scope:
        raw_counts: dict[str, int] = {}
        for u in (list(state.deployed or [])
                  + [b for b in (state.bench or []) if b is not None]):
            n = getattr(u, 'char_id', '') or ''
            if n in scope and (getattr(u, 'star', 1) or 1) < 2:
                raw_counts[n] = raw_counts.get(n, 0) + 1
        reserve += sum(1 for c in raw_counts.values() if c == 1)
    return min(reserve, max(1, registry.piece_value_bench_reserve_cap))


def bench_gate_verdict(cand, working: GameState, state: GameState,
                       session: StrategySession | None,
                       registry: DecisionV2Registry) -> RejectReason | None:
    """买前 bench 容量预检硬门:空位 ≤ reserve 时拒新买非合成件。

    设计单一源 = ADR-0497(本模块头注释同源);判据谓词单一实现 =
    spend_gate.bench_front_full(传推导 reserve,禁第二处);豁免面 =
    merge 候选(合成完备,ADR-0437/0438 通道同语义)∪ 当轮可部署
    (转化性,不占 bench)∪ 线内缺档成员(missing_members 单一源,
    C 账受保护类)。让位序与支出门 D3 同族:boss 窗让位(W774⑤)、
    ADR-0474 分配器接管帧让位。与 D3 的裁决序去重:本门约束名在
    spend_gate 之后(链序先到先记,arbiter 首拒即断)——双门并存帧
    D3 覆盖占用 ≥ 容量−1 带,本门只记「未达 D3 带但 ≥ 容量−reserve」
    的不重叠带,零双计。伞 = piece_value_enabled × 本门子旗标,默认
    关零漂移(开臂判据挂账 = W836 PREREG 同格重验,ADR-0497)。
    拒因经 session.v3_pv_block 帧级计数进遥测(sess_pv_bench_block)。
    """
    if not (registry.piece_value_enabled
            and registry.piece_value_bench_gate_enabled):
        return None
    from sr_od.application.currency_war.kernel.cw_state import BuyCard
    a = cand.action
    if not isinstance(a, BuyCard) or getattr(cand, 'merge', False):
        return None    # 只辖买侧;merge 候选让位(合成完备豁免)
    from sr_od.application.currency_war.decision.decision_v2.discipline import (
        boss_window_active,
    )
    if boss_window_active(state, session, registry):
        return None    # boss 窗让位(W774⑤ 同仲裁语义)
    from sr_od.application.currency_war.decision.decision_v2.realization import (
        d2_entry_frame,
        missing_members,
    )
    if d2_entry_frame(state, registry):
        return None    # ADR-0474 分配器接管帧让位(单一分配器)
    from sr_od.application.currency_war.decision.decision_v2.spend_gate import (
        _deploy_free,
        bench_front_full,
    )
    if _deploy_free(working):
        return None    # 当轮可部署(转化性豁免,D3 同语义)
    name = getattr(getattr(a, 'card', None), 'name', '') or ''
    if name and name in missing_members(state, session, registry):
        return None    # 线内缺档成员 = 受保护类(硬门保护对象不拒)
    reserve = bench_reserve(state, session, registry)
    if not bench_front_full(working, registry, reserve=reserve):
        return None
    occ = bench_occupied(working.bench or [])
    # 拒因产出 + 帧级拒因计数(sess_pv_bench_block 透传写入面;
    # 轮键惰性重置,v3_sg_block 同模式)
    from sr_od.application.currency_war.decision.decision_v2.remediation import (
        RejectReason,
    )
    key = (state.plane, state.round_num)
    if getattr(session, 'v3_pv_block_key', None) != key:
        session.v3_pv_block_key = key
        session.v3_pv_block = {}
    blocks: dict[str, int] = getattr(session, 'v3_pv_block', {}) or {}
    blocks['pv_bench_reserve'] = blocks.get('pv_bench_reserve', 0) + 1
    session.v3_pv_block = blocks
    return RejectReason(
        'pv_bench_reserve', '', 0,
        f'pv_bench_reserve:件价值硬门 bench 预检拒(占用{occ}≥容量'
        f'{registry.bench_capacity}-{reserve},reserve=1+开对,'
        f'非合成∧非缺档∧非当轮可部署)')
