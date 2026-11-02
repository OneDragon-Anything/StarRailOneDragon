"""统一卖出候选评估器(三触发卖出判据件;统一让位优先级迭代 3.2 重写、
3.4 旧判据拆除收敛)。

一个评估函数服务全部卖出触发场景(溢出紧急处理/采晶矿前空位/节末凑息;
升级凑金场景已随凑金链整删——用户裁定 2026-10-30:不存在升级卖牌
凑金,保持最大压牌库,钱够了再升;会话内筹资场景已随统一获取让位评估
收编退役——roster-plane1-union design §2.2 第 4 项:获取受阻〔席满 ∨
金不足〕走买入臂内联统一评估,禁经本注册表),输入 =
(场景,容器状态),输出 = 按让位序排序的卖出候选或空。三触发卖出判据件
规格单一源 = strategy-docs/11_shop_decisions.md §4.0;统一序列判定与
卖出取用形态规格正本 = strategy-docs/32_unified_sell_priority.md(§3/§8):

- **统一序列消费**:各场景排序单一源 = ``criteria/priority.sell_order``
  (禁第二排序实现,总纲 §2.9 接口契约 1)——部署重排
  (``mandate.select_deployment``)定型后的全局面序列,末位起取用;
- **无场景专属池子**【拍,总纲 §2.7】:部署定型内的牌 = 档 1 天然
  永不先卖,场景不再各自设池;
- **身份过滤退役**:填充牌过滤/凑息仅一星过滤/筹资仅一星过滤删除
  (序列天然排序;「不设仅一星代理过滤」= 总纲 §2.4 拍板);
- **循环防线保留**(与优先级正交,防操作空转,总纲 §2.4):窗口段/
  L1 同轮禁卖/种子年龄豁免(常规面经 ``sell_exclusions`` 装配)+
  合成素材拒入守卫含释放集旁路 + 空板止损守卫;溢出场景全资格豁免
  保留(保命优先);跨档止盈保留为节末凑息场景参数;**凑息豁免**
  (roster-plane1-union design §2.2 第 5 项)同为节末凑息场景参数
  ——候选池剔除线内未达标成员(线内 ∧ 手持 ∧ 星未达目标,谓词
  单一源 = ``priority.interest_exempt_member``;为利息绝对不可卖,
  非排序后移;池空 → 零卖出),被迫类卖出(溢出/晶矿/获取让位)
  不适用——动机二分:因席位/金币被迫按优先级让位的无豁免;

**旧判据退役申报(3.4,dismantle §3 卖侧)**:旧价值函数(变现价 +
再遇期权 + 合成进度口径的 ``sell_gold_equivalent`` 三项、
``MERGE_PROGRESS_X2`` 登记槽)与冻结遗留 deploy_swap 评估路径、羁绊
排序谓词(``bond_tier_drops_if_sold``/``is_field_irrelevant_unit``)、
C1 恒买席满腾位场景(``c1_make_room``,随 C1 支退役)整批删除——
排序与资格统一由档位结构承载,概率表/退金表保留为兜底档分档与凑钱
目标算术数据源(非排序键)。

**边界**:本模块 = 评估器本体;各动作发出点接线分属备战工序/商店
会话各消费位,``sell_gate``/``criteria/sell`` 通道现行保留。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_economy import (
    bench_char_cost,
    cap_resolved_of_session,
    effective_cost,
    next_interest_line,
    sell_refund,
)
from sr_od.application.currency_war.kernel.cw_exec_state import bench_slot_unit
from sr_od.application.currency_war.kernel.cw_game_state import (
    bench_entries_of,
    deployed_rows_of,
    gold_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    _pair_members,
    locked_buy_cap_hold,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    merge_material_reject_reason,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.sell_gate import (
    EMPTY_BOARD_SELL_GUARD_KEY,
    dead_pair_exit_release,
    empty_board_sell_blocked,
    sell_exclusions,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.session_scope import (
    line_members_view,
    plane2_started_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import predicates

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
        Unit,
    )

# ============================================================ 场景注册表(三触发)


#: 资格面取值:
#: - ``self_rescue_full`` = 自救扩展面(真全量持有——循环防线与身份面
#:   全放行,线内件按统一序列末位让位;「零停机出口」优先于防自旋,
#:   acquisition §3 表溢出行,现行豁免保留);
#: - ``regular`` = 常规面(循环防线:窗口段/L1 同轮禁卖/种子年龄豁免
#:   经 sell_exclusions 装配 + 合成素材拒入守卫含释放集旁路;身份段
#:   已随统一让位优先级迭代 3.4 退役——装配自动收缩为循环防线面)。
FACE_SELF_RESCUE: str = 'self_rescue_full'
FACE_REGULAR: str = 'regular'


@dataclass(frozen=True)
class SellSceneSpec:
    """一个卖出场景的参数行(三触发场景表,acquisition §3 的实现形态)。

    各场景取用 = 部署重排定型后的统一序列末位起消费(帧级一卖、重评
    收敛,消费位承载);本表只声明场景间真实存在差异的参数:

    - ``face``:循环防线资格面(全资格豁免仅溢出;常规面防线清单见
      模块头);
    - ``cross_tier_only``:跨档止盈(节末凑息独有场景参数,design §2.4
      保留行)——仅「单件退金 ≥ 到下一利息档缺口」的候选可卖,跨不了
      档的卖出零利息收益,一件不卖;
    - ``exempt_unmet_members``:凑息豁免(节末凑息独有场景参数,
      roster-plane1-union design §2.2 第 5 项)——候选池剔除线内
      未达标成员,池空零卖出;字段语义详见字段注;
    - ``legacy_channel``:P78 通道标记(sell_exclusions 装配的通道谱系
      参数;None = 不装配)。
    """

    scenario: str                # 场景 id(闭集成员)
    face: str                    # 循环防线资格面(FACE_* 闭集)
    legacy_channel: str | None   # P78 通道标记(None = 不装配)
    cross_tier_only: bool = False   # 跨档止盈(节末凑息)
    exempt_unmet_members: bool = False
    """凑息豁免(节末凑息独有;roster-plane1-union design §2.2 第 5 项):
    候选池剔除线内未达标成员(线内 ∧ 手持 ∧ 星未达目标,谓词单一源 =
    ``priority.interest_exempt_member``)——为利息绝对不可卖,非排序
    后移;达标线内件(完成品居档 2/4,冗余副本落兜底档)与非线内件照常参与。仅利息
    动机场景可声明 True;被迫类(溢出/晶矿/获取让位)恒 False
    (动机二分)。"""


#: 场景注册表(闭集;三触发三场景):
#: - ``shop_swap`` 行已随席满置换账被六步流程整段替换退役(3.2,
#:   dismantle §2——六步流程直通 ``priority.sell_order``,不经本评估器);
#: - ``c1_make_room`` 行已随 C1 单卡核心支退役删除(3.4,dismantle §2
#:   场景死行);
#: - ``deploy_swap`` 冻结遗留行已随旧价值函数退役删除(3.4;kernel
#:   swap 机器(swap_sell_exclusion_reason 含)亦已随部署统一批丁整链
#:   收编——unified-deploy-order §2.7/§4,被换下者回 bench 由统一让位序
#:   处置,部署换人域无独立卖出资格面);
#: - ``levelup_liquidate_prep`` 行已随升级凑金链整删退役(用户裁定
#:   2026-10-30:不存在升级卖牌凑金——保持最大压牌库,钱够了再升;
#:   金不足帧恒 defer 等钱,零卖出动作);
#: - ``session_funding`` 行已随统一获取让位评估收编退役(roster-
#:   plane1-union design §2.2 第 4 项 + 用户裁定 2026-10-30:统一
#:   优先级——金不足与席满同一评估,禁再立筹资/凑金/腾位类场景;
#:   `funding` 通道随场景退役无消费者,SELL_CHANNELS 同批删除)。
SCENE_SPECS: dict[str, SellSceneSpec] = {
    'self_rescue': SellSceneSpec(
        'self_rescue', FACE_SELF_RESCUE, None),
    'ore_make_room': SellSceneSpec(
        'ore_make_room', FACE_REGULAR, 'm4_fuel'),
    'node_end_interest': SellSceneSpec(
        'node_end_interest', FACE_REGULAR, 'interest',
        cross_tier_only=True, exempt_unmet_members=True),
}

#: 场景闭集(新场景必须先在此登记再接线——枚举外值抛错,与 sell_gate
#: SELL_CHANNELS 同款单一入口防线)。
SELL_SCENARIOS: frozenset[str] = frozenset(SCENE_SPECS)

#: 候选池/资格面过滤后为空的拒因键(诚实空输出,消费位按各自场景的
#: 「无候选」路径处置——自救场景 = 点消耗品出路承接,prep_pipeline §1
#: 第 0 步态 4)。
REJECT_NO_CANDIDATES: str = 'no_candidates'

#: 凑息豁免剔光帧观测键(roster-plane1-union design §2.2 第 5 项;
#: 登记点原挂同设计 §2.2 第 3 项):节末凑息跨档止盈后的可行池全为
#: 线内未达标成员、被豁免剔空 → 零卖出动作的帧计数。设计指出该帧
#: 形态在豁免落地前不可观测;本键使「无豁免会卖出在建阵容
#: 件 → 有豁免零动作」的行为翻转可判读(§2.5 凑息频率略降落到此
#: 形态的份额)。写点 = :func:`evaluate_sell_candidates`(counters
#: 载体;消费位 = entry 第 8 步传 ``cw4_counters``);键名族登记 =
#: telemetry/schema.py 键表节。
INTEREST_EXEMPT_DEPLETED_KEY: str = 'node_end_interest_exempt_depleted'


# ============================================================ 线内身份集


def sell_line_membership(gs: GameState) -> frozenset[str]:
    """卖出侧线内身份集(双层名单口径 = 32 号稿 §2):
    锁定 = 锁定线名单(``line_members_view``,core ∪ shared)
    **∪ 过渡候选成员**;未锁定 = 实候选(证据门版快照)三线成员并集
    **∪ 过渡候选成员**。过渡支两态共用同一读口 =
    ``transition_candidates`` 槽各对 ``_pair_members`` 展开 + 读前判窗
    (``plane2_started_of``——进位面 2 即退出,锁定不是退出条件,
    P1 锁定局照收;**与买面同源**——同一槽展开,成员展开单一源 =
    kernel ``_pair_members``,与 ``shop._transition_candidate_members``
    同集)。

    消费面:常规面 sell_exclusions 装配 k_members 入参、备战帧
    k_members 装配(entry.emit / mandate.snapshot_frame)、买面投影位
    (shop)、预算投影的 1★ 活期口径(序 3-5 投影——entry
    攒批位已随凑金链整删)。同一集禁各消费点自建第二份名单口径。候选名注册表解析
    失败(漂移)跳过并告警——该线贡献空集,保守方向申报:少排除 =
    多可卖 = 让位面不受阻。
    """
    view = line_members_view(gs)
    names: set[str] = set()
    if view.locked:
        names |= set(view.members)
    else:
        for comp_name in state_of(gs).line_candidates:
            comp = get_comp(comp_name) if comp_name else None
            if comp is None:
                log.warning('[cw!][sell-cand] 候选线名解析失败(%s),该线成员不入线内集',
                            comp_name)
                continue
            names |= set(comp.core_chars)
            names |= set(getattr(comp, 'shared_chars', None) or ())
    # 过渡支(两态共用):槽展开 + 读前判窗——与 priority 装配/买面
    # 同口径(禁经 direction_comp_of 拼名单;进 P2 后本支恒空集,
    # clear_p1_recipe 同点清空 + 判窗双保险)。
    if not plane2_started_of(gs):
        for pair in (state_of(gs).transition_candidates or ()):
            names |= _pair_members(tuple(pair))
    return frozenset(names)


# ============================================================ 评估器(三触发单一入口)


@dataclass(frozen=True)
class SellCandidate:
    """一个卖出候选(评估器输出行;frozen 值对象)。

    [索引定义] ``idx`` 坐标系随 ``zone`` 分域:``zone='bench'`` = 备战席
    紧缩占席序(``bench_entries_of`` 列表 0 基下标,发出侧经容器槽位表
    枚举对位还原);``zone='deployed'`` = 上场紧缩行序(``deployed_rows_of``
    两行拼接〔前排在前〕的 0 基下标)。取值时机 = 评估帧现读(候选构造
    时快照)。
    """

    zone: str            # 'bench' | 'deployed'
    idx: int             # 容器内定位键(坐标系见类 docstring)
    unit: Unit           # 候选单位本体(frozen 值对象)
    char_id: str
    star: int
    tier: int | None = None
    """[观测载荷] 统一序列档位分量(``priority.sort_key`` 键首,1..10)。
    取值时机 = 评估帧排序时随键快照;None = 未观测形态(缺省,兼容
    旧构造)。判据零消费——仅供取用观测键(档位分布)读取。
    """
    rng_tail_hit: bool = False
    """[观测载荷] 随机尾键命中:池内存在另一件与本件排序键去尾后
    全同(等价牌群内部随机定序对本件实际生效,随机尾键契约 =
    strategy-docs/32_unified_sell_priority.md §7)。
    取值时机同上;缺省 False = 未观测形态。判据零消费。"""


def _deployed_rows_indexed(gs: GameState) -> list[tuple[Unit, str, int]]:
    """上场域 (单位,排,紧缩行序下标) 枚举——候选 idx 的行序坐标系由
    本口单一承载。"""
    front, back = deployed_rows_of(gs)
    out: list[tuple[Unit, str, int]] = []
    idx = 0
    for u in front:
        if u is not None:
            out.append((u, 'front', idx))
            idx += 1
    for u in back:
        if u is not None:
            out.append((u, 'back', idx))
            idx += 1
    return out


def _held_cost(gs: GameState, name: str) -> int | None:
    """手持牌实费档供给(:attr:`HeldUnit.cost`;变费卡升费后现值,
    单一源 = ``cw_economy.effective_cost``;未注册名读 0 → None 回退
    判据件注册表保守估)。"""
    return effective_cost(gs, name) or None


def evaluate_sell_candidates(
        gs: GameState, scenario: str, *,
        counters: dict | None = None,
) -> tuple[tuple[SellCandidate, ...], str]:
    """统一卖出候选评估器(三触发单一入口;acquisition §3)。

    输入 =(场景,容器状态);输出 =(按让位序排序的候选元组,拒因键
    ——候选非空恒 '',空候选暴露拒因)。让位序 = 先卖到后卖:统一
    序列(末位 = 最先让路)整体反转,消费位取首位 = 序列末位。
    候选行随键携带观测载荷(``tier`` 档位 / ``rng_tail_hit`` 随机尾键
    命中,见字段注)——取用观测键(档位分布/随机尾键命中)的数据源,
    判据零消费。

    统一路径(四场景):
    1. 空板止损守卫(deployed = 0 帧全部卖出场景哑火,as-built 申报
       沿袭);
    2. 部署重排定型(``mandate.snapshot_frame`` + ``assemble_prep_context``
       + ``select_deployment`` 纯函数现算;档 1 名集);
    3. 全局面候选(备战席 ∪ 场上;无场景专属池子【拍】——利息动机
       例外 = 凑息豁免池过滤,见步 6)经循环防线过滤:常规面 =
       sell_exclusions(窗口段/L1 同轮禁卖/种子年龄豁免;身份段已随
       统一让位优先级迭代 3.4 退役,装配自动收缩)+ 合成素材拒入
       守卫(释放集旁路保留);自救面 = 全放行(仅占位件物理门);
       档 1(部署定型内,按角色名命中)不进输出——「永不先卖」字面
       保证,板上同名牌同受保护;系统召唤单位(cost=0,不可卖)物理
       门与占位件门同向互补;
    4. ``priority.sell_order`` 排序(升序 = 最不该卖 → 最先让路),输出
       取其反转;
    5. 跨档止盈(仅节末凑息):让位序内保留「单件退金 ≥ 到下一利息档
       缺口」者;无下一利息档(满档/买断制)或无可行件 = 空输出
       (REJECT_NO_CANDIDATES,一件不卖);
    6. 凑息豁免(仅节末凑息;roster-plane1-union design §2.2 第 5 项):
       可行池剔除线内未达标成员(谓词单一源 =
       ``priority.interest_exempt_member``——为利息绝对不可卖,非
       排序后移);豁免把可行池剔空(无豁免时该帧会卖出在建阵容件)
       的帧落 :data:`INTEREST_EXEMPT_DEPLETED_KEY` 观测键;池空 →
       零卖出(现行「序列真空零动作」语义)。被迫类场景不走本步。

    ``counters`` = 遥测分键容器(缺省 None = 守卫纯判读形态,豁免
    过滤照常、观测键不落)。
    """
    spec = SCENE_SPECS.get(scenario)
    if spec is None:
        raise ValueError(
            f'未知卖出场景 {scenario!r}:合法闭集 = {sorted(SELL_SCENARIOS)}'
            ' (acquisition §3;新场景先登记 SCENE_SPECS 再接线)')
    deployed_indexed = _deployed_rows_indexed(gs)
    deployed = [u for u, _row, _idx in deployed_indexed]
    if empty_board_sell_blocked(deployed, counters=counters):
        return (), EMPTY_BOARD_SELL_GUARD_KEY
    bench = bench_entries_of(gs)
    # —— 统一序列路径(部署重排定型 → 全局面序列)——
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        mandate,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        priority as crit_priority,
    )
    frame = mandate.snapshot_frame(gs)
    prep = mandate.assemble_prep_context(gs, gs, frame)
    # 部署定型(阶段 5/6 统一部署搜索内核):返回 target_board =
    # 名 → (排, 星);档 1 名集消费 = 键集(接口契约②)。
    target_board = mandate.select_deployment(frame, prep)
    target = frozenset(target_board)
    ctx = crit_priority.assemble_priority_context(
        gs, gs, deployed_names=target,
        rng=crit_priority.priority_rng_of(gs))
    excl: frozenset[str] = frozenset()
    release: frozenset[str] = frozenset()
    if spec.face == FACE_REGULAR:
        # 循环防线装配(窗口段/L1 同轮禁卖/种子年龄豁免;身份段已随
        # 统一让位优先级迭代 3.4 退役——装配自动收缩,禁在本层另设
        # 第二排除面)。释放集 = 死库存对素材守卫旁路(单一源 =
        # dead_pair_exit_release)。
        line = sell_line_membership(gs)
        excl = sell_exclusions(
            gs, tuple(sorted(line)), channel=spec.legacy_channel,
            current_round=round_num_of(gs),
            cap_hold=locked_buy_cap_hold(gs))
        release = dead_pair_exit_release(
            gs, tuple(sorted(line)), bench, deployed,
            round_num_of(gs), cap_hold=locked_buy_cap_hold(gs))
    units: list[crit_priority.HeldUnit] = []
    cands: dict[tuple[str, int], SellCandidate] = {}
    # 档 1(部署定型内,按角色名命中)不进让位输出——「部署定型内的
    # 牌永不先卖」的字面保证(卖出取用形态正本 =
    # strategy-docs/32_unified_sell_priority.md §8);备战位上的同名牌
    # 同受保护(档 1 按名命中 = 在手优先不换手形态,3.1 判据件语义)。
    # 板空边界保守侧:部署外候选真空帧 = 空输出,不向部署需要面借牌。
    # —— 备战席支(占位件物理门 = 现行跨通道共享谓词)——
    for i, slot in enumerate(bench):
        if predicates.item_slot_unsellable(slot):
            continue
        unit = bench_slot_unit(slot)
        name = str(getattr(unit, 'char_id', '') or '') if unit else ''
        if unit is None or name == '':
            continue
        if predicates.is_unsellable_system_unit(name):
            # 系统召唤单位(cost=0)物理门:不可卖 + 实费档缺失会按中费
            # 3 估产生无意义排序键(F-2;与占位件物理门同向互补)。
            continue
        if name in target:
            continue
        if name in excl:
            continue
        if merge_material_reject_reason(
                name, int(getattr(unit, 'star', 1) or 1), bench,
                deployed) and name not in release:
            continue
        units.append(crit_priority.HeldUnit(
            name, int(getattr(unit, 'star', 1) or 1), i, False,
            cost=_held_cost(gs, name)))
        cands[('bench', i)] = SellCandidate(
            zone='bench', idx=i, unit=unit, char_id=name,
            star=int(getattr(unit, 'star', 1) or 1))
    # —— 场上支(全局面序列;部署定型内 = 档 1 已被上道过滤,入池者
    # 仅部署重排挤下的换阵牺牲件 = 部署外)——
    for unit, _row, idx in deployed_indexed:
        name = str(unit.char_id or '')
        if name in target:
            continue
        if predicates.is_unsellable_system_unit(name):
            continue
        if name in excl:
            continue
        if merge_material_reject_reason(
                name, int(getattr(unit, 'star', 1) or 1), bench,
                deployed) and name not in release:
            continue
        units.append(crit_priority.HeldUnit(
            name, int(getattr(unit, 'star', 1) or 1), idx, True,
            cost=_held_cost(gs, name)))
        cands[('deployed', idx)] = SellCandidate(
            zone='deployed', idx=idx, unit=unit, char_id=name,
            star=int(getattr(unit, 'star', 1) or 1))
    if not units:
        return (), REJECT_NO_CANDIDATES
    # 排序与观测同键(单一排序实现):带键排序回填观测载荷(档位 =
    # 键首分量;随机尾键命中 = 池内键去尾同撞,等价牌群内部随机定序
    # 对本件实际生效)。键值 = priority.sort_key 输出,判读口径与
    # 键名族登记 = telemetry/schema.py 键表节(acquisition §6)。
    keyed = crit_priority.sell_order_with_keys(units, ctx)
    _prefixes = [k[:-1] for _u, k in keyed]
    yield_order: list[SellCandidate] = []
    for u, k in reversed(keyed):
        cand = cands[('deployed' if u.deployed else 'bench', u.slot)]
        yield_order.append(replace(
            cand, tier=int(k[0]),
            rng_tail_hit=_prefixes.count(k[:-1]) >= 2))
    if spec.cross_tier_only:
        # 跨档止盈(场景参数;design §2.4 保留行):仅「单件退金 ≥ 到
        # 下一利息档缺口」者可卖;无下一档(满档/买断制)= 无卖益,
        # 一件不卖。
        _gold = int(gold_of(gs) or 0)
        _line = next_interest_line(_gold, cap_resolved_of_session(gs))
        if _line is None:
            return (), REJECT_NO_CANDIDATES
        _gap = _line - _gold

        def _refund(c: SellCandidate) -> int:
            return sell_refund(int(c.star or 1),
                               bench_char_cost(c.unit, gs))

        yield_order = [c for c in yield_order if _refund(c) >= _gap]
    if not yield_order:
        return (), REJECT_NO_CANDIDATES
    if spec.exempt_unmet_members:
        # 凑息豁免(场景参数;design §2.2 第 5 项):跨档止盈后的可行池
        # 剔除线内未达标成员——谓词单一源 = priority.interest_exempt_
        # member(线内 ∧ 手持 ∧ 星未达目标;为利息绝对不可卖,非排序
        # 后移),达标线内件(完成品居档 2/4,冗余副本落兜底档)与非线内件照常参与。
        # 剔光判定取「可行池非空(上方已保证)∧ 豁免后空」:计的是
        # 豁免真正翻转卖出→零动作的帧(无豁免时该帧会卖出在建阵容
        # 件);可行池本空帧已在上方提前返回,不落观测键。被迫类场景
        # 不走本步(动机二分)。
        kept = [c for c in yield_order
                if not crit_priority.interest_exempt_member(c.char_id, ctx)]
        if not kept and counters is not None:
            counters[INTEREST_EXEMPT_DEPLETED_KEY] = \
                counters.get(INTEREST_EXEMPT_DEPLETED_KEY, 0) + 1
        yield_order = kept
    if not yield_order:
        return (), REJECT_NO_CANDIDATES
    return tuple(yield_order), ''


__all__ = [
    'FACE_REGULAR',
    'FACE_SELF_RESCUE',
    'INTEREST_EXEMPT_DEPLETED_KEY',
    'REJECT_NO_CANDIDATES',
    'SCENE_SPECS',
    'SELL_SCENARIOS',
    'SellCandidate',
    'SellSceneSpec',
    'evaluate_sell_candidates',
    'sell_line_membership',
]
