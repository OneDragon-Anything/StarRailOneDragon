"""统一卖出候选评估器(三触发卖出判据件;统一让位优先级迭代 3.2 重写)。

一个评估函数服务全部卖出触发场景(溢出紧急处理/采晶矿前空位/升级凑金/
节末凑息/店内筹资 + 冻结遗留 deploy_swap),输入 =(场景,容器状态),
输出 = 按让位序排序的卖出候选或空。规格单一源 =
``changes/2026-10-29-unified-priority/details/acquisition-and-sell.md``
§3(三触发卖出判据件)+ priority-model §5(卖出取用形态):

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
  保留(保命优先);跨档止盈保留为节末凑息场景参数;
- 价值评估函数与羁绊谓词仅剩 deploy_swap 冻结遗留路径消费(生产
  零消费面,拆除归属 3.4 旧判据拆除批);``is_field_irrelevant_unit``
  另有节末凑息观测键反事实支消费(entry,键退役归 3.5)。

**边界**:本模块 = 评估器本体;各动作发出点接线分属备战工序/商店
会话各消费位,``sell_gate``/``criteria/sell`` 通道现行保留。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.data.cw_shop_odds import (
    reencounter_window_frames,
)
from sr_od.application.currency_war.kernel.cw_board_by_row import board_by_row
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
    level_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_intention import locked_buy_cap_hold
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    merge_material_reject_reason,
    same_star_count,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import provisional
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
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import predicates

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        SwapPlanContext,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        GameState,
        Unit,
    )

# ============================================================ 场景注册表(三触发)


#: 资格面取值:
#: - ``self_rescue_full`` = 自救扩展面(真全量持有——循环防线与身份面
#:   全放行,线内件按统一序列末位让位;「零停机出口」优先于防自旋,
#:   acquisition §3 表溢出行,现行豁免保留);
#: - ``regular`` = 常规面(循环防线:窗口段/L1 同轮禁卖/种子年龄豁免
#:   经 sell_exclusions 装配 + 合成素材拒入守卫含释放集旁路);
#: - ``deploy_swap_current`` = 换人现行判据(swap_sell_exclusion_reason
#:   本体不动;冻结遗留路径,生产零消费面,3.4 处置)。
FACE_SELF_RESCUE: str = 'self_rescue_full'
FACE_REGULAR: str = 'regular'
FACE_DEPLOY_SWAP: str = 'deploy_swap_current'


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
    - ``legacy_channel``:P78 通道标记(sell_exclusions 装配的通道谱系
      参数;None = 不装配)。
    """

    scenario: str                # 场景 id(闭集成员)
    face: str                    # 循环防线资格面(FACE_* 闭集)
    legacy_channel: str | None   # P78 通道标记(None = 不装配)
    cross_tier_only: bool = False   # 跨档止盈(节末凑息)


#: 场景注册表(闭集;三触发五场景 + 冻结遗留 deploy_swap):
#: - ``shop_swap`` 行已随席满置换账被六步流程整段替换退役(3.2,
#:   dismantle §2——六步流程直通 ``priority.sell_order``,不经本评估器);
#: - ``c1_make_room`` 消费位归 3.4 C1 支拆除,收敛前随常规面统一序列
#:   消费(其「评估首位直接卖」消费形态不变,排序源切换为统一序列);
#: - ``deploy_swap`` 冻结遗留(部署换人域 design §2.2 不动;生产零
#:   消费面,评估走旧路径,价值函数拆除时随批处置)。
SCENE_SPECS: dict[str, SellSceneSpec] = {
    'self_rescue': SellSceneSpec(
        'self_rescue', FACE_SELF_RESCUE, None),
    'ore_make_room': SellSceneSpec(
        'ore_make_room', FACE_REGULAR, 'm4_fuel'),
    'session_funding': SellSceneSpec(
        'session_funding', FACE_REGULAR, 'funding'),
    'levelup_liquidate_prep': SellSceneSpec(
        'levelup_liquidate_prep', FACE_REGULAR, 'funding'),
    'node_end_interest': SellSceneSpec(
        'node_end_interest', FACE_REGULAR, 'interest',
        cross_tier_only=True),
    'deploy_swap': SellSceneSpec(
        'deploy_swap', FACE_DEPLOY_SWAP, None),
    'c1_make_room': SellSceneSpec(
        'c1_make_room', FACE_REGULAR, 'funding'),
}

#: 场景闭集(新场景必须先在此登记再接线——枚举外值抛错,与 sell_gate
#: SELL_CHANNELS 同款单一入口防线)。
SELL_SCENARIOS: frozenset[str] = frozenset(SCENE_SPECS)

#: deploy_swap 场景缺换人判定语境时的拒因键(fail-closed:现行判据本体
#: ctx=None 时返回 ''(全放行)是 fail-open 形态,评估器侧拒收——资格
#: 判据禁缺语境放行,与 sell_gate hold 登记缺读拒登记同纪律)。
REJECT_SWAP_CTX_MISSING: str = 'deploy_swap_ctx_missing'

#: 候选池/资格面过滤后为空的拒因键(诚实空输出,消费位按各自场景的
#: 「无候选」路径处置——自救场景 = 点消耗品出路承接,prep_pipeline §1
#: 第 0 步态 4)。
REJECT_NO_CANDIDATES: str = 'no_candidates'


# ============================================================ 价值函数(line_and_upgrade §4;deploy_swap 冻结遗留路径专用)


#: 每轮息损边际率(金/轮)——再遇窗口折算金当量的乘子。口径出处 =
#: line_and_upgrade §4:每利息档边际率 1 金【注·利息档粒度定义值】;真值
#: 上限 = cap 金/轮(默认局 5/息律局 10,随 cap 查表)**不消费**(消费
#: 口径 = 边际率)。利息档粒度是利息系统的定义值而非拟合值,零调参。
INTEREST_MARGIN_PER_ROUND: float = 1.0

#: 合成进度 ×2 结构近似系数的 provisional 槽名(line_and_upgrade §4:
#: 差一张 = 两张的再遇期权沉淀,×2 为结构近似系数【拟·owner = 编排者、
#: 期限 = 一个对局周期】;fail-closed 缺省 = ×1 线性运行——不放大持有
#: 期权 = 保守侧,标定对照完成后切 ×2)。
MERGE_PROGRESS_X2_SLOT: str = 'MERGE_PROGRESS_X2'


def _merge_pair_multiplier() -> float:
    """合成进度系数现读(provisional 槽:None = ×1 fail-closed,注入 = ×2)。"""
    cv = provisional.get(MERGE_PROGRESS_X2_SLOT)
    return float(cv.value) if cv is not None else 1.0


def sell_gold_equivalent(gs: GameState, unit: Unit) -> float:
    """手上牌的金当量(line_and_upgrade §4;deploy_swap 冻结遗留路径
    专用——五场景已切统一让位序列,本函数生产零消费面,拆除归属 3.4)。

    构成(金当量三项,全部为注册表查表确定式,无自由拟合参数——已标注
    项除外):

    - **变现价** = ``sell_refund(star, cost)``(注册表现读;费用档取
      ``bench_char_cost`` 含银狼LV.999 档感知);
    - **再遇期权** = ``reencounter_window_frames(level, cost, held)`` ×
      :data:`INTEREST_MARGIN_PER_ROUND`——再遇窗口折算金当量;held =
      同名同星持有计数现读(bench ∪ 场上全场域;line_and_upgrade §4
      现文口径「已持有数 = 同名同星持有计数现读」);
    - **合成进度** = 差一张(同名同星持有 ≥ 2 且 star < 3)→ 再遇期权 ×
      :func:`_merge_pair_multiplier`(×2 结构近似【拟】,fail-closed
      = ×1);零散单张 = 自身再遇期权。

    返回值可为 ``inf``(该等级刷不出该费用档 ⇒ 再遇窗 inf ⇒ 持有期权
    无限大 ⇒ 排序末位)。
    """
    star = int(getattr(unit, 'star', 1) or 1)
    name = str(getattr(unit, 'char_id', '') or '')
    cost = bench_char_cost(unit, gs)
    held = _same_star_held_of(gs, name, star)
    window = reencounter_window_frames(level_of(gs), cost, held) \
        * INTEREST_MARGIN_PER_ROUND
    pair = held >= 2 and star < 3
    merge_progress = window * (_merge_pair_multiplier() if pair else 1.0)
    return float(sell_refund(star, cost)) + window + merge_progress


def _same_star_held_of(gs: GameState, name: str, star: int) -> int:
    """同名同星持有计数现读(bench ∪ 场上全场域;计数单一源 =
    ``cw_merge_simulate.same_star_count``,禁手搓同式)。"""
    if not name:
        return 0
    front, back = deployed_rows_of(gs)
    deployed = [d for d in (*front, *back) if d is not None]
    return same_star_count(name, star, bench_entries_of(gs), deployed)


# ============================================================ 线内身份集与羁绊谓词


def sell_line_membership(gs: GameState) -> frozenset[str]:
    """卖出侧线内身份集(锁定 = ``line_members_view`` 名单〔core ∪
    shared〕;未锁定 = 候选 top3 线内成员并集——判定源 = 候选快照)。

    消费面(3.2 后):常规面 sell_exclusions 装配 k_members 入参、
    攒批资金口径(entry)、筹资兜底与买面投影位(shop;退役归 3.4)、
    节末凑息观测键反事实支的「场上无关角色」分支(entry,键退役归
    3.5)。同一集禁各消费点自建第二份名单口径。候选名注册表解析
    失败(漂移)跳过并告警——该线贡献空集,保守方向申报:少排除 =
    多可卖 = 让位面不受阻。
    """
    view = line_members_view(gs)
    if view.locked:
        return frozenset(view.members)
    names: set[str] = set()
    for comp_name in state_of(gs).line_candidates:
        comp = get_comp(comp_name) if comp_name else None
        if comp is None:
            log.warning('[cw!][sell-cand] 候选线名解析失败(%s),该线成员不入线内集',
                        comp_name)
            continue
        names |= set(comp.core_chars)
        names |= set(getattr(comp, 'shared_chars', None) or ())
    return frozenset(names)


def _unit_bond_tags(unit: Unit, row: str) -> set[str]:
    """单个上场单位的羁绊标签集(阵营+流派,开拓者按排归一形态)——
    经按排聚合单一源 ``board_by_row`` 的单单位聚合取键,禁复制其注册表
    读法(独立羁绊不计 = 与板面左面板计数口径一致,同 board_by_row)。"""
    agg = board_by_row([unit] if row == 'front' else [],
                       [unit] if row != 'front' else [])
    return set(agg.front if row == 'front' else agg.back)


def _activated_tier(tiers: tuple[int, ...], count: int) -> int | None:
    """该羁绊当前已达成的最高激活档(人数 ≥ 档位阈值的最大档;无 = None)。"""
    best: int | None = None
    for t in tiers:
        if t <= count:
            best = t
    return best


def _board_tag_counts(gs: GameState) -> dict[str, int]:
    """全板羁绊标签计数(单一源 = ``board_by_row_of`` 同构聚合)。"""
    front, back = deployed_rows_of(gs)
    return board_by_row(front, back).total()


def is_effective_bond_contributor(gs: GameState, unit: Unit, row: str) -> bool:
    """有效羁绊贡献件谓词:上场单位 ∧ 其任一羁绊标签当前有已激活档
    (人数 ≥ 注册表 tiers 最小档)。

    deploy_swap 冻结遗留路径与场上无关角色谓词的共享判定;统一序列
    下的羁绊承载 = 档 7 判定(criteria/priority),本谓词不再进任何
    卖出排序。"""
    counts = _board_tag_counts(gs)
    for tag in _unit_bond_tags(unit, row):
        info = FACTIONS.get(tag)
        if info is not None and info.tiers \
                and _activated_tier(info.tiers, counts.get(tag, 0)) is not None:
            return True
    return False


def bond_tier_drops_if_sold(gs: GameState, unit: Unit, row: str) -> bool:
    """羁绊排序规则项:卖后掉当前板面羁绊档(deploy_swap 冻结遗留路径
    专用;备战席候选恒 False——不在板上,不参与计数)。"""
    counts = _board_tag_counts(gs)
    for tag in _unit_bond_tags(unit, row):
        info = FACTIONS.get(tag)
        if info is None or not info.tiers:
            continue
        cur = _activated_tier(info.tiers, counts.get(tag, 0))
        if cur is not None and counts.get(tag, 0) == cur:
            return True
    return False


def is_field_irrelevant_unit(gs: GameState, unit: Unit, row: str) -> bool:
    """场上无关角色谓词(来金族候选池的场上支准入历史谓词;现役消费 =
    节末凑息观测键反事实支的 deployed 枚举,entry——键退役归 3.5):
    非锁定线成员(:func:`sell_line_membership` 判定)∧ 非有效羁绊贡献件。

    ``row`` = 该单位所在排('front'/'back';羁绊标签的开拓者形态按排
    归一需要排信息)。
    """
    name = str(getattr(unit, 'char_id', '') or '')
    if name in sell_line_membership(gs):
        return False
    return not is_effective_bond_contributor(gs, unit, row)


# ============================================================ 评估器(三触发单一入口)


@dataclass(frozen=True)
class SellCandidate:
    """一个卖出候选(评估器输出行;frozen 值对象)。

    [索引定义] ``idx`` 坐标系随 ``zone`` 分域:``zone='bench'`` = 备战席
    紧缩占席序(``bench_entries_of`` 列表 0 基下标,发出侧经容器槽位表
    枚举对位还原);``zone='deployed'`` = 上场紧缩行序(``deployed_rows_of``
    两行拼接〔前排在前〕的 0 基下标)。取值时机 = 评估帧现读(候选构造
    时快照)。

    ``gold_value``/``bond_drop``/``line_member`` = deploy_swap 冻结遗留
    路径的排序诊断维(统一序列路径恒缺省值,零消费)。
    """

    zone: str            # 'bench' | 'deployed'
    idx: int             # 容器内定位键(坐标系见类 docstring)
    unit: Unit           # 候选单位本体(frozen 值对象)
    char_id: str
    star: int
    gold_value: float = 0.0
    bond_drop: bool = False
    line_member: bool = False


def _deployed_rows_indexed(gs: GameState) -> list[tuple[Unit, str, int]]:
    """上场域 (单位,排,紧缩行序下标) 枚举——bond 谓词的排信息与候选
    idx 的行序坐标系由本口单一承载。"""
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


def _evaluate_deploy_swap_legacy(
        gs: GameState, swap_ctx: SwapPlanContext | None,
        deployed_indexed: list[tuple[Unit, str, int]],
        bench: list[BenchSlot],
) -> tuple[tuple[SellCandidate, ...], str]:
    """deploy_swap 冻结遗留评估路径(部署换人域 design §2.2 不动;
    生产零消费面,判据与排序逐位同 3.2 前——价值函数拆除批随批处置)。"""
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        swap_sell_exclusion_reason,
    )
    if swap_ctx is None:
        return (), REJECT_SWAP_CTX_MISSING
    deployed = [u for u, _row, _idx in deployed_indexed]
    line = sell_line_membership(gs)
    out: list[SellCandidate] = []

    def _ok(unit: Unit, *, is_bench: bool) -> bool:
        if swap_sell_exclusion_reason(
                str(getattr(unit, 'char_id', '') or ''), swap_ctx,
                star=int(getattr(unit, 'star', 1) or 1),
                bench=bench, deployed=deployed) != '':
            return False
        return not (is_bench and predicates.bench_effect_qualified(
            str(getattr(unit, 'char_id', '') or ''),
            predicates.bench_effect_context(gs, unit, tuple(line))))

    for i, slot in enumerate(bench):
        if predicates.item_slot_unsellable(slot):
            continue
        unit = bench_slot_unit(slot)
        name = str(getattr(unit, 'char_id', '') or '') if unit else ''
        if unit is None or name == '':
            continue
        if not _ok(unit, is_bench=True):
            continue
        out.append(SellCandidate(
            zone='bench', idx=i, unit=unit, char_id=name,
            star=int(getattr(unit, 'star', 1) or 1),
            gold_value=sell_gold_equivalent(gs, unit),
            line_member=name in line))
    for unit, row, idx in deployed_indexed:
        if not _ok(unit, is_bench=False):
            continue
        out.append(SellCandidate(
            zone='deployed', idx=idx, unit=unit,
            char_id=str(unit.char_id or ''),
            star=int(getattr(unit, 'star', 1) or 1),
            gold_value=sell_gold_equivalent(gs, unit),
            bond_drop=bond_tier_drops_if_sold(gs, unit, row),
            line_member=str(unit.char_id or '') in line))
    if not out:
        return (), REJECT_NO_CANDIDATES
    out.sort(key=lambda c: (c.line_member, c.bond_drop, c.gold_value,
                            c.zone, c.idx))
    return tuple(out), ''


def _held_cost(gs: GameState, name: str) -> int | None:
    """手持牌实费档供给(:attr:`HeldUnit.cost`;变费卡升费后现值,
    单一源 = ``cw_economy.effective_cost``;未注册名读 0 → None 回退
    判据件注册表保守估)。"""
    return effective_cost(gs, name) or None


def evaluate_sell_candidates(
        gs: GameState, scenario: str, *,
        swap_ctx: SwapPlanContext | None = None,
        counters: dict | None = None,
) -> tuple[tuple[SellCandidate, ...], str]:
    """统一卖出候选评估器(三触发单一入口;acquisition §3)。

    输入 =(场景,容器状态);输出 =(按让位序排序的候选元组,拒因键
    ——候选非空恒 '',空候选暴露拒因)。让位序 = 先卖到后卖:统一
    序列(priority.sell_order 升序,末位 = 最先让路)整体反转,消费位
    取首位 = 序列末位。

    统一路径(五场景):
    1. 空板止损守卫(deployed = 0 帧全部卖出场景哑火,as-built 申报
       沿袭);
    2. 部署重排定型(``mandate.snapshot_frame`` + ``assemble_prep_context``
       + ``select_deployment`` 纯函数现算;档 1 名集);
    3. 全局面候选(备战席 ∪ 场上;无场景专属池子【拍】)经循环防线
       过滤:常规面 = sell_exclusions(窗口段/L1 同轮禁卖/种子年龄
       豁免;身份段退役归属 3.4 sell_gate 收缩,收敛前随装配照读)+
       合成素材拒入守卫(释放集旁路保留);自救面 = 全放行(仅占位件
       物理门);档 1(部署定型内,按角色名命中)不进输出——「永不
       先卖」字面保证,板上同名牌同受保护;
    4. ``priority.sell_order`` 排序(升序 = 最不该卖 → 最先让路),输出
       取其反转;
    5. 跨档止盈(仅节末凑息):让位序内保留「单件退金 ≥ 到下一利息档
       缺口」者;无下一利息档(满档/买断制)或无可行件 = 空输出
       (REJECT_NO_CANDIDATES,一件不卖)。

    deploy_swap 场景走冻结遗留路径(:func:`_evaluate_deploy_swap_legacy`)。

    ``swap_ctx`` = deploy_swap 场景的换人判定语境(装配单一源 =
    ``cw_deploy_logic.assemble_swap_plan_inputs``);缺省 None ⇒ deploy_swap
    场景 fail-closed 拒评估,非 deploy_swap 场景忽略本参。

    ``counters`` = 遥测分键容器(缺省 None = 守卫纯判读形态)。
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
    if spec.face == FACE_DEPLOY_SWAP:
        return _evaluate_deploy_swap_legacy(gs, swap_ctx,
                                            deployed_indexed, bench)
    # —— 统一序列路径(部署重排定型 → 全局面序列)——
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        mandate,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        priority as crit_priority,
    )
    frame = mandate.snapshot_frame(gs)
    prep = mandate.assemble_prep_context(gs, gs, frame)
    target = mandate.select_deployment(frame, prep)
    ctx = crit_priority.assemble_priority_context(
        gs, gs, deployed_names=target,
        rng=crit_priority.priority_rng_of(gs))
    excl: frozenset[str] = frozenset()
    release: frozenset[str] = frozenset()
    if spec.face == FACE_REGULAR:
        # 循环防线装配(窗口段/L1 同轮禁卖/种子年龄豁免;身份段构成含
        # 终局键集标签命中件——退役归属 3.4 sell_gate 身份段收缩,收敛
        # 前随装配照读,禁在本层另设第二排除面)。释放集 = 死库存对
        # 素材守卫旁路(单一源 = dead_pair_exit_release)。
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
    # 牌永不先卖」的字面保证(priority-model §5);备战位上的同名牌
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
    ordered = crit_priority.sell_order(units, ctx)
    yield_order: list[SellCandidate] = [
        cands[('deployed' if u.deployed else 'bench', u.slot)]
        for u in reversed(ordered)]
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
    return tuple(yield_order), ''


__all__ = [
    'FACE_DEPLOY_SWAP',
    'FACE_REGULAR',
    'FACE_SELF_RESCUE',
    'INTEREST_MARGIN_PER_ROUND',
    'MERGE_PROGRESS_X2_SLOT',
    'REJECT_NO_CANDIDATES',
    'REJECT_SWAP_CTX_MISSING',
    'SCENE_SPECS',
    'SELL_SCENARIOS',
    'SellCandidate',
    'SellSceneSpec',
    'bond_tier_drops_if_sold',
    'evaluate_sell_candidates',
    'is_effective_bond_contributor',
    'is_field_irrelevant_unit',
    'sell_gold_equivalent',
    'sell_line_membership',
]
