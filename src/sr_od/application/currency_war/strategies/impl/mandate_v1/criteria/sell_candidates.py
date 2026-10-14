"""统一卖出候选评估器(契约 D 单一入口;迭代 2026-10-12-prep-shop-workflow-redesign 批 3.2)。

一个评估函数服务全部八类卖出场景(溢出自救/晶矿腾位/店内置换/会话内筹资/
升级变现/节末凑息/部署换血/C1 恒买腾位),输入 =(场景, 容器状态),输出 =
按让位序排序的卖出候选或空。场景参数全集(候选池/资格面/消费方式)的
唯一法定义处 = 迭代总纲 design.md 契约 D;价值评估函数统一口径 =
line_and_upgrade §4(金当量三项 + 羁绊排序规则项)——本模块是它们的
落码载体,禁各场景自算第二份。

**本批边界(纪律)**:只建评估器本体 + 谓词 + 测试,不接生产调用链——
各发射位接线归 3.3(备战工序)/3.5(商店执行链)/3.6(商店会话)各批;
现行 ``sell_gate``/``criteria/sell`` 三通道零破坏(退役随消费批)。

结构:

- 场景注册表(:data:`SCENE_SPECS`)——八场景(升级变现分备战/会话两域
  共九行)各带候选池族/资格面/消费方式标记;消费方式由调用方(prep 各
  步/shop 各序)按场景取,评估器只出排序候选;
- 价值函数(:func:`sell_gold_equivalent`)——金当量三项(变现价/再遇
  期权/合成进度),量纲与合成式按 line_and_upgrade §4 直读实现;
- 线内身份集(:func:`sell_line_membership`)——锁定 = line_members_view
  名单;未锁定 = 候选 top3 线内成员并集(判定源 = 候选快照,line_and_upgrade
  §1.2「线内身份集 = 候选 top3 线内成员」);
- 场上无关角色谓词(:func:`is_field_irrelevant_unit`)与有效羁绊贡献件
  谓词(:func:`is_effective_bond_contributor`)——羁绊判定消费现有羁绊
  注册表(FACTIONS tiers)与按排聚合单一源(board_by_row);
- 垫件谓词(:func:`is_ore_pad_unit`)——晶矿场景过滤(prep_pipeline §1
  第 2 步现文口径;P96 释放集「挂账不激活」申报域 = 垫件层——池级 FACE_REGULAR
  仍含 dead_pair_exit_release 旁路为惰性面:垫件谓词恒拒 released 名〔同名对素材〕、
  3.3 消费面走垫件过滤,行为零激活;P96 推进遥测/清账时一并收口);
- 评估器(:func:`evaluate_sell_candidates`)。
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
from sr_od.application.currency_war.kernel.cw_card_identity import (
    is_engine_piece,
    sell_hold_exclusion_names,
)
from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_economy import (
    bench_char_cost,
    sell_refund,
)
from sr_od.application.currency_war.kernel.cw_exec_state import bench_slot_unit
from sr_od.application.currency_war.kernel.cw_game_state import (
    bench_entries_of,
    deployed_rows_of,
    level_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_intention import locked_buy_cap_hold
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    merge_material_reject_reason,
    same_star_count,
)
from sr_od.application.currency_war.kernel.cw_plugins import PLUGIN_LIBRARY
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
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vopt import (
    refund_full_star_ok,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        SwapPlanContext,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        GameState,
        Unit,
    )

# ============================================================ 场景注册表(契约 D)


#: 候选池族取值(契约 D 唯一定义处的落码形态;四族):
#: - ``bench_only`` = 仅备战席(腾槽族〔自救/晶矿〕+ 店内四场景;
#:   机理 = 解除溢出/买入晶矿/店内卖出均只腾备战槽,卖场上件无此效果,
#:   店内另有 2026-10-12 用户裁定「店内禁卖场上」);
#: - ``bench_union_field_irrelevant`` = 备战席 ∪ 场上无关角色(来金族:
#:   节末凑息/备战升级变现;2026-10-13 用户裁定「来金目的卖谁都行」);
#: - ``field_union_bench`` = 场上 ∪ 备战席(部署换血——场上锁定线成员/
#:   有效羁绊件的唯一卖出场景,羁绊维在该场景生效)。
POOL_BENCH_ONLY: str = 'bench_only'
POOL_BENCH_FIELD_IRRELEVANT: str = 'bench_union_field_irrelevant'
POOL_FIELD_AND_BENCH: str = 'field_union_bench'

#: 资格面取值:
#: - ``self_rescue_full`` = 自救扩展面(真全量持有——P78 资格仲裁族全通道
#:   豁免:核心/④件/种子/同 visit 买入在自救场景豁免、线内件按价值序
#:   末位可卖;「零停机出口」优先于硬资格,契约 D 自救行);
#: - ``regular`` = 常规面(现行 sell_gate 排除集收编:装配 A(身份段 ∪
#:   窗口段 ∪ L1 同轮硬面 ∪ 种子豁免)+ 合成素材拒入守卫(含死库存对
#:   释放子谓词旁路)+ 挂后台效果资格);
#: - ``deploy_swap_current`` = 换血现行判据(swap_sell_exclusion_reason
#:   本体不动,契约 D 部署换血行;不经装配 A——该判据自带 membership/
#:   fresh_buy/守恒门/素材守卫资格族)。
FACE_SELF_RESCUE: str = 'self_rescue_full'
FACE_REGULAR: str = 'regular'
FACE_DEPLOY_SWAP: str = 'deploy_swap_current'


@dataclass(frozen=True)
class SellSceneSpec:
    """一个卖出场景的参数行(契约 D 场景表的落码形态)。

    ``consumption`` = 消费方式标记(调用方按场景取的动作语义;评估器只出
    排序候选,不执行消费):``sell_first`` 取首候选直接卖 / ``pad_filter_min``
    垫件谓词过滤后取价值最小 / ``swap_account`` 置换账裁决 / ``sell_until_
    gap_closed`` 卖到缺口闭合即止 / ``swap_pair`` 换血对(卖场上件 + 上阵
    替补)/ ``sell_first_buy_core`` 腾位卖 Y 后买核心。
    **P78-5 四条件兜底豁免不在本评估器**(契约 D 筹资/升级变现行资格面的
    兜底腿):其触发前提 = 消费位状态(主路径空 ∧ 缺口未闭合 = gold <
    need),超出「(场景, 容器状态)」入参面——单一源 = ``sell_gate.
    funding_hold_fallback``,由筹资(shop_session)与升级变现(entry
    备战第 3 步)消费循环在主路径尽时拼装,与现行消费位同构(触发前提
    由消费位判,函数本体只承载兜底池定义)。
    ``legacy_channel`` = P78 通道重映射(现行五通道资格面按契约 D 重映射:
    凑息→节末凑息 / 筹资→会话内筹资 / m4_fuel→晶矿 / line_switch→退役
    不接(部署换血走现行 swap 判据,不走其装配)/ projection→保留不动
    (投影视图读位照旧,不进评估器场景);None = 不装配 A(自救豁免 /
    换血自带判据)。非 projection 通道的装配 A 输出逐位相同,通道选择
    仅承继族谱系语义。
    """

    scenario: str                # 场景 id(闭集成员)
    pool: str                    # 候选池族(POOL_* 闭集)
    face: str                    # 资格面(FACE_* 闭集)
    one_star_refund_only: bool   # 仅 1★ 全额退件过滤(活期件口径)
    consumption: str             # 消费方式标记(见类 docstring)
    legacy_channel: str | None   # P78 通道重映射(None = 不装配 A)


#: 场景注册表(闭集;契约 D 八场景——升级变现按分域拆两行,共九行:
#: 备战侧(第 3 步)= 备战席 ∪ 场上无关角色,会话内侧 = 仅备战席)。
#: 消费方式/资格面逐行对齐契约 D 表格,禁行内自创第三口径。
SCENE_SPECS: dict[str, SellSceneSpec] = {
    'self_rescue': SellSceneSpec(
        'self_rescue', POOL_BENCH_ONLY, FACE_SELF_RESCUE, False,
        'sell_first', None),
    'ore_make_room': SellSceneSpec(
        'ore_make_room', POOL_BENCH_ONLY, FACE_REGULAR, False,
        'pad_filter_min', 'm4_fuel'),
    'shop_swap': SellSceneSpec(
        'shop_swap', POOL_BENCH_ONLY, FACE_REGULAR, False,
        'swap_account', 'funding'),
    'session_funding': SellSceneSpec(
        'session_funding', POOL_BENCH_ONLY, FACE_REGULAR, True,
        'sell_until_gap_closed', 'funding'),
    'levelup_liquidate_prep': SellSceneSpec(
        'levelup_liquidate_prep', POOL_BENCH_FIELD_IRRELEVANT, FACE_REGULAR,
        True, 'sell_until_gap_closed', 'funding'),
    'levelup_liquidate_shop': SellSceneSpec(
        'levelup_liquidate_shop', POOL_BENCH_ONLY, FACE_REGULAR, True,
        'sell_until_gap_closed', 'funding'),
    'node_end_interest': SellSceneSpec(
        'node_end_interest', POOL_BENCH_FIELD_IRRELEVANT, FACE_REGULAR, True,
        'sell_until_gap_closed', 'interest'),
    'deploy_swap': SellSceneSpec(
        'deploy_swap', POOL_FIELD_AND_BENCH, FACE_DEPLOY_SWAP, False,
        'swap_pair', None),
    'c1_make_room': SellSceneSpec(
        'c1_make_room', POOL_BENCH_ONLY, FACE_REGULAR, False,
        'sell_first_buy_core', 'funding'),
}

#: 场景闭集(新场景必须先在此登记再接线——枚举外值抛错,与 sell_gate
#: SELL_CHANNELS 同款单一入口防线)。
SELL_SCENARIOS: frozenset[str] = frozenset(SCENE_SPECS)

#: deploy_swap 场景缺换血判定语境时的拒因键(fail-closed:现行判据本体
#: ctx=None 时返回 ''(全放行)是 fail-open 形态,评估器侧拒收——资格
#: 判据禁缺语境放行,与 sell_gate hold 登记缺读拒登记同纪律)。
REJECT_SWAP_CTX_MISSING: str = 'deploy_swap_ctx_missing'

#: 候选池/资格面过滤后为空的拒因键(诚实空输出,消费位按各自场景的
#: 「无候选」路径处置——自救场景 = 点消耗品出路承接,prep_pipeline §1
#: 第 0 步态 4)。
REJECT_NO_CANDIDATES: str = 'no_candidates'


# ============================================================ 价值函数(line_and_upgrade §4)

#: 每轮息损边际率(金/轮)——再遇窗口折算金当量的乘子。口径出处 =
#: line_and_upgrade §4:每息档边际率 1 金【注·息档粒度定义值】;真值
#: 上限 = cap 金/轮(默认局 5/息律局 10,随 cap 查表)**不消费**(消费
#: 口径 = 边际率)。息档粒度是利息系统的定义值而非拟合值,零调参。
INTEREST_MARGIN_PER_ROUND: float = 1.0

#: 合成进度 ×2 结构近似系数的 provisional 槽名(line_and_upgrade §4:
#: 差一张 = 两张的再遇期权沉淀,×2 为结构近似系数【拟·owner = 编排者、
#: 期限 = 一个对局周期】;fail-closed 缺省 = ×1 线性运行——不放大持有
#: 期权 = 保守侧,标定对照完成后切 ×2)。
MERGE_PROGRESS_X2_SLOT: str = 'MERGE_PROGRESS_X2'

#: 差一张合成的判定阈值(同名同星持有 == 2;满 3 自动升星使稳态计数
#: 恒 ≤ 2,见 cw_merge_simulate.merge_material_reject_reason 的不变量
#: 论证)。
_MERGE_PAIR_HELD: int = 2


def _merge_pair_multiplier() -> float:
    """合成进度系数现读(provisional 槽:None = ×1 fail-closed,注入 = ×2)。"""
    cv = provisional.get(MERGE_PROGRESS_X2_SLOT)
    return float(cv.value) if cv is not None else 1.0


def sell_gold_equivalent(gs: GameState, unit: Unit) -> float:
    """手上牌的金当量(line_and_upgrade §4 统一口径;所有卖出场景共用,
    禁各场景自算)。

    构成(金当量三项,全部为注册表查表确定式,无自由拟合参数——已标注
    项除外):

    - **变现价** = ``sell_refund(star, cost)``(注册表现读;费用档取
      ``bench_char_cost`` 含银狼LV.999 档感知);
    - **再遇期权** = ``reencounter_window_frames(level, cost, held)`` ×
      :data:`INTEREST_MARGIN_PER_ROUND`——再遇窗口折算金当量;held =
      同名同星持有计数现读(bench ∪ 场上全场域;line_and_upgrade §4
      现文口径「已持有数 = 同名同星持有计数现读」,与查表函数自身
      docstring 的基础副本折算口径(1★1/2★3/3★9 折算)存在偏差:
      1★ 同值、2★+ 计数值 < 折算值——设计现文为权威,按计数口径取;
      折算口径若启用属设计层变更,非本函数缺漏);
    - **合成进度** = 差一张(同名同星持有 ≥ 2 且 star < 3——3★ 无下一
      星档,完成档不存在按零散单张处理,裁量申报)→ 再遇期权 ×
      :func:`_merge_pair_multiplier`(×2 结构近似【拟】,fail-closed
      = ×1);零散单张 = 自身再遇期权。

    完成档语义:未锁定期「完成档」缺省 = 该成员自身下一星档(line_and_
    upgrade §4,无目标线依赖)——差一张时「看到下一张」的再遇窗即完成
    档再遇期权,由 ``reencounter_window_frames`` 的 held 参数天然承载,
    无独立星级入参。羁绊贡献不是本函数的项(P3 作废不折金,排序规则项
    由 :func:`evaluate_sell_candidates` 的 bond_drop 维承载)。

    返回值可为 ``inf``(该等级刷不出该费用档 ⇒ 再遇窗 inf ⇒ 持有期权
    无限大 ⇒ 排序末位)——语义 = 极难再遇的持有最后让位。
    """
    star = int(getattr(unit, 'star', 1) or 1)
    name = str(getattr(unit, 'char_id', '') or '')
    cost = bench_char_cost(unit, gs)
    held = _same_star_held_of(gs, name, star)
    window = reencounter_window_frames(level_of(gs), cost, held) \
        * INTEREST_MARGIN_PER_ROUND
    pair = held >= _MERGE_PAIR_HELD and star < 3
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
    shared〕;未锁定 = 候选 top3 线内成员并集——判定源 = 候选快照,
    line_and_upgrade §1.2「线内身份集 = 候选 top3 线内成员,替代
    k_members 的线内判定职责」)。

    消费面:评估器线内排除与自救末位分层、场上无关角色谓词、垫件谓词
    的「非线内/非候选集成员」腿、装配 A 的 k_members 入参——同一集,
    禁各消费点自建第二份名单口径(design 契约 B)。候选名注册表解析
    失败(漂移)跳过并告警——该线贡献空集,保守方向申报:少排除 =
    多可卖 = 自救/让位面不受阻,线内保护面收窄由 3.7 候选判据的注册表
    校验兜底。
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

    口径申报:契约 D/line_and_upgrade 差分节定义「场上无关角色 = 非锁定
    线成员 ∧ 非有效羁绊贡献件」,「有效羁绊贡献」无现成谓词(全仓检索
    无此判定),按设计给的兜底口径「上场且激活羁绊的成员」落码——比
    「卖后掉档」严格判定宽(计数超阈值的成员也算贡献件),保守向 =
    保护面更大(更多场上件被排除出卖点候选池);排序规则项(掉档置后)
    与本谓词分立,见 :func:`evaluate_sell_candidates` 的 bond_drop 维。
    """
    counts = _board_tag_counts(gs)
    for tag in _unit_bond_tags(unit, row):
        info = FACTIONS.get(tag)
        if info is not None and info.tiers \
                and _activated_tier(info.tiers, counts.get(tag, 0)) is not None:
            return True
    return False


def bond_tier_drops_if_sold(gs: GameState, unit: Unit, row: str) -> bool:
    """羁绊排序规则项:卖后掉当前板面羁绊档(line_and_upgrade §4——
    不折金,P3 作废禁引数值;上阵位才有此代价,备战席位天然不掉档)。

    判据 = 该单位任一标签的板面计数恰等于当前已激活最高档(移除后
    跌破该档);备战席候选恒 False(不在板上,不参与计数)。
    """
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
    """场上无关角色谓词(来金族候选池的场上支准入;契约 D/2026-10-13
    用户裁定):非锁定线成员(:func:`sell_line_membership` 判定)∧
    非有效羁绊贡献件(:func:`is_effective_bond_contributor`)。

    ``row`` = 该单位所在排('front'/'back';羁绊标签的开拓者形态按排
    归一需要排信息)。
    """
    name = str(getattr(unit, 'char_id', '') or '')
    if name in sell_line_membership(gs):
        return False
    return not is_effective_bond_contributor(gs, unit, row)


# ============================================================ 垫件谓词(晶矿场景过滤)


def is_ore_pad_unit(gs: GameState, char_id: str, star: int) -> bool:
    """垫件谓词(晶矿腾位场景过滤;prep_pipeline §1 第 2 步现文口径):
    卖出损失 ≈ 0 的持有。

    合取六项(逐项单一源):

    - 1★;
    - 非线内(:func:`sell_line_membership`;未锁定期含候选 top3 成员——
      囤货集排除防候选囤件被垫件卖出,与「囤终局件为锁线准备」承诺
      一致);
    - 非合成素材(``merge_material_reject_reason`` 单一源——同名同星
      另有副本即素材对);
    - 非通用插件注册表成员(``PLUGIN_LIBRARY``——插件有座位价值不在
      垫件集);
    - 非 registry 核心/④件(``sell_hold_exclusion_names``——核心/转线
      件有再遇期权不在垫件集);
    - 非种子身份件(``is_engine_piece`` 引擎件身份层——裁量申报:设计
      文「非种子」按身份层取引擎件全集而非种子登记簿子集,引擎件 =
      跨线羁绊结构件有保留价值;登记簿级种子已由常规面装配 A 排除,
      身份层取超集 = 更保守的垫件收窄,无漏放)。

    P96 释放集【挂账不激活】不并入(证明前提不随场景迁移,标定前晶矿
    垫件不含释放集)。
    """
    if int(star or 1) != 1 or not char_id:
        return False
    if char_id in sell_line_membership(gs):
        return False
    front, back = deployed_rows_of(gs)
    deployed = [d for d in (*front, *back) if d is not None]
    if merge_material_reject_reason(char_id, 1, bench_entries_of(gs),
                                    deployed):
        return False
    if char_id in PLUGIN_LIBRARY:
        return False
    if char_id in sell_hold_exclusion_names():
        return False
    return not is_engine_piece(char_id)


# ============================================================ 评估器(契约 D 单一入口)


@dataclass(frozen=True)
class SellCandidate:
    """一个卖出候选(评估器输出行;frozen 值对象)。

    [索引定义] ``idx`` 坐标系随 ``zone`` 分域:``zone='bench'`` = 备战席
    紧缩占席序(``bench_entries_of`` 列表 0 基下标,与现行三通道候选位键
    ``criteria/sell._slot_of`` 同构,发射侧经容器槽位表枚举对位还原);
    ``zone='deployed'`` = 上场紧缩行序(``deployed_rows_of`` 两行拼接
    〔前排在前〕的 0 基下标)。取值时机 = 评估帧现读(候选构造时快照)。

    ``gold_value`` = 金当量三项(:func:`sell_gold_equivalent`;可为
    inf);``bond_drop`` = 羁绊排序规则项(卖后掉当前羁绊档;仅上场位
    可 True);``line_member`` = 线内身份集成员标记(自救扩展面的末位
    分层依据——线内件整体置末层后仍按金当量序,prep_pipeline §2)。
    """

    zone: str            # 'bench' | 'deployed'
    idx: int             # 容器内定位键(坐标系见类 docstring)
    unit: Unit           # 候选单位本体(frozen 值对象)
    char_id: str
    star: int
    gold_value: float
    bond_drop: bool
    line_member: bool


def _deployed_rows_indexed(gs: GameState) -> list[tuple[Unit, str, int]]:
    """上场域 (单位, 排, 紧缩行序下标) 枚举——bond 谓词的排信息与候选
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


def _regular_face_ok(unit: Unit, *, excl: frozenset[str],
                     release: frozenset[str],
                     bench: list[BenchSlot],
                     deployed: list[Unit]) -> bool:
    """常规面资格过滤(单候选;两段收编——装配 A 排除集 + 合成素材
    拒入守卫〔含死库存对释放子谓词旁路〕)。挂后台效果资格 = 现行
    三通道资格谓词的收编(bench_effect_qualified/bench_effect_context
    单一源消费),在 :func:`_bench_effect_blocked` 单独分派——仅备战席
    候选查,场上支不查(谓词语义 = 备战席后台效果生效)。
    """
    name = str(getattr(unit, 'char_id', '') or '')
    star = int(getattr(unit, 'star', 1) or 1)
    if name in excl:
        return False
    return not (merge_material_reject_reason(name, star, bench, deployed)
                and name not in release)


def _bench_effect_blocked(gs: GameState, unit: Unit,
                          line: frozenset[str]) -> bool:
    """挂后台效果资格拒入(备战席候选;语境装配单一源 =
    ``predicates.bench_effect_context``,与现行三通道同门)。"""
    return predicates.bench_effect_qualified(
        str(getattr(unit, 'char_id', '') or ''),
        predicates.bench_effect_context(gs, unit, tuple(line)))


def evaluate_sell_candidates(
        gs: GameState, scenario: str, *,
        swap_ctx: SwapPlanContext | None = None,
        counters: dict | None = None,
) -> tuple[tuple[SellCandidate, ...], str]:
    """统一卖出候选评估器(契约 D 单一入口)。

    输入 =(场景, 容器状态);输出 =(按让位序排序的候选元组, 拒因键
    ——候选非空恒 '',空候选显影拒因)。让位序 = 先卖到后卖:

    1. 线内末位分层(自救扩展面:线内件整体置末层,组内仍按金当量序;
       常规面场景线内件已被资格面排除,本层恒 0);
    2. 羁绊规则二分(不掉档组在前,掉档组在后——不折金的上阵位代价);
    3. 组内金当量三项升序(:func:`sell_gold_equivalent`);
    4. 确定性并列破除((zone, idx) 字典序——物理位序,禁随机/集合序)。

    全场景共用空板守卫(现行为等价收编,prep_pipeline §1 第 0 步
    as-built 申报:deployed = 0 帧全部卖出场景哑火,本设计不收窄)。

    ``swap_ctx`` = deploy_swap 场景的换血判定语境(``SwapPlanContext``,
    装配单一源 = ``cw_deploy_logic.assemble_swap_plan_inputs``,调用方
    〔3.3 部署面〕从决策帧装配传入);缺省 None ⇒ deploy_swap 场景
    fail-closed 拒评估(REJECT_SWAP_CTX_MISSING),非 deploy_swap 场景
    忽略本参。

    ``counters`` = 遥测分键容器(缺省 None = 守卫纯判读形态;A 装配的
    计数面经策略器状态自带容器,不经本参)。
    """
    spec = SCENE_SPECS.get(scenario)
    if spec is None:
        raise ValueError(
            f'未知卖出场景 {scenario!r}:合法闭集 = {sorted(SELL_SCENARIOS)}'
            ' (design 契约 D;新场景先登记 SCENE_SPECS 再接线)')
    deployed_indexed = _deployed_rows_indexed(gs)
    deployed = [u for u, _row, _idx in deployed_indexed]
    if empty_board_sell_blocked(deployed, counters=counters):
        return (), EMPTY_BOARD_SELL_GUARD_KEY
    if spec.face == FACE_DEPLOY_SWAP and swap_ctx is None:
        return (), REJECT_SWAP_CTX_MISSING
    bench = bench_entries_of(gs)
    line = sell_line_membership(gs)
    excl: frozenset[str] = frozenset()
    release: frozenset[str] = frozenset()
    if spec.face == FACE_REGULAR:
        # 装配 A(现行 sell_gate 排除集收编;k_members = 线内身份集——
        # 未锁定期候选成员判定替代 k_members 线内判定职责,line §1.2)+
        # 死库存对释放集(素材守卫旁路,单一源 = dead_pair_exit_release,
        # 判据本体禁自算)。
        excl = sell_exclusions(
            gs, tuple(sorted(line)), channel=spec.legacy_channel,
            current_round=round_num_of(gs),
            cap_hold=locked_buy_cap_hold(gs))
        release = dead_pair_exit_release(
            gs, tuple(sorted(line)), bench, deployed,
            round_num_of(gs), cap_hold=locked_buy_cap_hold(gs))

    def _face_ok(unit: Unit, *, is_bench: bool) -> bool:
        """场景资格面分派(自救全量直通/常规面三段/换血现行判据)。"""
        if spec.face == FACE_SELF_RESCUE:
            return True   # 真全量:仅占位件物理门在前置循环拦截
        if spec.face == FACE_DEPLOY_SWAP:
            from sr_od.application.currency_war.kernel.cw_deploy_logic import (
                swap_sell_exclusion_reason,
            )
            return swap_sell_exclusion_reason(
                str(getattr(unit, 'char_id', '') or ''), swap_ctx,
                star=int(getattr(unit, 'star', 1) or 1),
                bench=bench, deployed=deployed) == ''
        if not _regular_face_ok(unit, excl=excl,
                                release=release, bench=bench,
                                deployed=deployed):
            return False
        if is_bench and _bench_effect_blocked(gs, unit, line):
            return False
        if spec.one_star_refund_only:
            return refund_full_star_ok(
                int(getattr(unit, 'star', 1) or 1),
                bench_char_cost(unit, gs))
        return True

    out: list[SellCandidate] = []
    # —— 备战席支(全场景池成员;占位件物理门 = 现行跨通道共享谓词)——
    for i, slot in enumerate(bench):
        if predicates.item_slot_unsellable(slot):
            continue
        unit = bench_slot_unit(slot)
        name = str(getattr(unit, 'char_id', '') or '') if unit else ''
        if unit is None or name == '':
            continue
        if not _face_ok(unit, is_bench=True):
            continue
        out.append(SellCandidate(
            zone='bench', idx=i, unit=unit, char_id=name,
            star=int(getattr(unit, 'star', 1) or 1),
            gold_value=sell_gold_equivalent(gs, unit),
            bond_drop=False,
            line_member=name in line))
    # —— 场上支(按池族:来金族 = 仅无关角色;部署换血 = 全部上场件)——
    if spec.pool in (POOL_BENCH_FIELD_IRRELEVANT, POOL_FIELD_AND_BENCH):
        for unit, row, idx in deployed_indexed:
            if spec.pool == POOL_BENCH_FIELD_IRRELEVANT \
                    and not is_field_irrelevant_unit(gs, unit, row):
                continue
            if not _face_ok(unit, is_bench=False):
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


__all__ = [
    'FACE_DEPLOY_SWAP',
    'FACE_REGULAR',
    'FACE_SELF_RESCUE',
    'INTEREST_MARGIN_PER_ROUND',
    'MERGE_PROGRESS_X2_SLOT',
    'POOL_BENCH_FIELD_IRRELEVANT',
    'POOL_BENCH_ONLY',
    'POOL_FIELD_AND_BENCH',
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
    'is_ore_pad_unit',
    'sell_gold_equivalent',
    'sell_line_membership',
]
