"""投资策略画面策略(mandate_v1;宪法六「一画面一策略文件」)。

设计正本 = strategy-docs/29_invest_strategy_screen.md(下称「29 号稿」,
节号即该篇节号);评分模型 = 「统一加法标尺」——单位 = 分,
**1 分 := 1 金等价**(归一化约定,沿 28 号稿 §1;XP 折算沿
env_economy.XP_GOLD_RATE 承载),非多标尺层次压制形态
(分值族不相加、靠层次常数定先后的设计禁复辟)。

总分公式(29 号稿 §1)::

    总分 = 现金分 + 方向分 + 赠卡分 + 立场分 + 转向轴加分

- 现金分 = strategy_economy.strategy_economy_value(resolved ∧ > 0 才计,
  fail-closed 恒 0);
- 方向分组件恒 0(strength/方向分链整线下线,29 号稿 §2.2 方向分行废止);
- 赠卡分 = STRATEGY_GRANTS + gift_value.grant_gift_value(29 号稿 §2.3);
- 立场分 = :data:`STANCE_SCORE`(【拍】形态,现行无非零行;表外卡恒 0);
- 转向轴 = strategy_priority 命中 + :data:`pick_common.
  STEERING_PRIORITY_BONUS`(软偏好,立场系数);strategy_forbid = 排除出
  候选(不走分值,29 号稿 §2.4)。

结构分区(选卡序,29 号稿 §3 + invest-direction-guard §2.3,全部零拍值):
阵容冲突护栏出域 → 禁选排除 → 自拆台(适用范围护栏)→ 血本位三态 →
定义型分区 → 组件总分 argmax;归因标签按管线序拼接,护栏未生效帧
tag/输出与无护栏逐位一致。

阵容冲突护栏(changes/2026-10-17-invest-direction-guard,下称「护栏设计」
§2.2/§2.3):基准 = 锁线 Comp.factions(锁定帧,历史误持不入基)∨ 已持有
投资指向并集(未锁定帧,:func:`_conflict_basis`);基准空帧护栏不辖,
选卡行为与无护栏逐位一致。排除语义 = 域收缩非负分;刷新侧出域卡沿
E-豁免同款(不入帧级顶级/不计 max_N/恒入动作集/不算 L1)。

刷新判据(29 号稿 §4;P81 承接):帧级门与槽级顶级两谓词分立,
帧级门 = 候选恰 3 ∧ 全精确分类 ∧ 无帧级顶级卡 ∧(终局阵容锁定帧 max_N≠1);
槽级动作集 = 非槽级顶级可刷/被禁与出域恒入/唯一 L1 守卫。

输出契约(29 号稿 §4)::func:`decide` 返回纯值 dataclass
(:class:`InvestStrategyDecision` / :class:`StrategyRefreshSuggestion`,
不含动作词表)——动作包装(CwActionPickInvestStrategyParam/
CwActionRefreshInvestCardsParam)留 flow;:func:`decide_pick`
= 同一评分基线的纯选卡口,永不建议刷(flow 同帧去重 memo 命中后的落选卡
入口;为 sim 复用预留)。本文件是投资策略选卡评序的单一源(flow 直调;
kernel ``decide_event`` 不复存在,模块停用史)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_comps import (
    augment_affinity,
    get_comp,
)
from sr_od.application.currency_war.kernel.cw_game_state import GameState
from sr_od.application.currency_war.kernel.cw_investments import (
    INVESTMENT_STRATEGIES,
    STRATEGY_BINDINGS,
    STRATEGY_GRANTS,
    EconomyEffect,
    env_faction_scope,
    get_env,
    get_strategy,
    is_blood_economy,
    is_economy_engine,
    normalize_invest_name,
    resolve_strategy_canonical,
    strategy_faction_scope,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.gift_value import (
    grant_gift_value,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.pick_common import (
    BOARD_DOT_COUNT_THRESHOLD,
    STEERING_PRIORITY_BONUS,
    counters_dot,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.strategy_economy import (
    strategy_economy_value,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.currency_war_config import (
        CurrencyWarConfig,
    )


# ===== 输出契约(29 号稿 §4X:纯值 dataclass,不含动作词表)=====

@dataclass(frozen=True)
class InvestStrategyDecision:
    """选卡决策。

    idx = options 容器下标(0 基;候选序 = 调用方传入序,取值时机 =
    本帧决策期快照);reason = 归因串(总分与五组件分解,仅观测);
    total = 组件总分(统一标尺,分 = 金等价);components = 五组件分解
    (现金,方向,赠卡,立场,转向轴),与总分同帧快照,仅观测。
    """
    idx: int
    reason: str
    total: float
    components: tuple[float, float, float, float, float]


@dataclass(frozen=True)
class StrategyRefreshSuggestion:
    """刷新建议(与 env 落地件 invest_env.RefreshSuggestion 不共享不继承
    ——两屏刷新语义不同构:env = 整帧重掷单钮、无槽语义;策略 = 逐槽
    刷新,同名歧义以屏别前缀消解,29 号稿 §4X)。

    slots = 可刷槽位元组(元素 = options 容器下标,0 基;坐标系与取值
    时机同 idx——本帧决策期快照,handler 槽序循环消费)。
    """
    reason: str
    slots: tuple[int, ...]


# ===== 立场分表(29 号稿 §2.4;【拍】形态,每行带理由)=====

@dataclass(frozen=True)
class StanceRow:
    """立场分表行。

    score = 立场分(统一标尺上的量,分差有含义——加法标尺合法前提);
    reason = 裁定理由(表的裁决记录,落地裁决窗过目 = 验收凭据)。
    """
    score: float
    reason: str


#: 策略卡立场分表(29 号稿 §2.4:**现行无非零行**)。表只收非零行,
#: 未登记卡默认 0(战力类/契约任务链/期权类等无机械成分卡全部默认 0,
#: 理由:①「不为过渡阵容服务」裁定下无机械证据卡不预设正分;②335 张
#: 逐行拍值的裁决负担不成比例;③逐条重拍由实机判读驱动)。现行无强度
#: 效果立场行(战力类全 0 = 不登记不建模),宪法一确认义务面为空;未来
#: 登记强度行时按硬闸门逐项确认。立场查表口径 = canonical(与组件解析
#: 同源)。覆盖义务由 strategy_economy 字段分类校验 + 下方孤儿校验承载。
STANCE_SCORE: dict[str, StanceRow] = {}

_STANCE_ZERO = 0.0


def _validate_stance_registry() -> None:
    """立场表孤儿校验:表键必须在注册表(版本改名后漏跟 → import 即炸)。

    空表该断言恒真,首行登记起生效(29 号稿 §2.4 表与构建校验)。"""
    for _name in STANCE_SCORE:
        if _name not in INVESTMENT_STRATEGIES:
            raise ValueError(f"立场分表孤儿键(注册表无此卡):{_name!r}")


_validate_stance_registry()


# ===== 平分裁决键(29 号稿 §3)=====

#: 品质序 tie-break(棱彩>金>银,【注】游戏定义;零拍值序表)。**命名
#: 声明**:本表驻策略层、独立命名(``_RARITY_TIE_RANK``)——品质序
#: tie-break 是策略评序内容(29 号稿 §3),宪法五归策略层,不复用
#: kernel 侧符号名。
_RARITY_TIE_RANK: dict[str, int] = {'银': 0, '金': 1, '棱彩': 2}


def _econ_effect_flag(eff: EconomyEffect | None) -> int:
    """economy 效果有无谓词(**钉死沿用旧合取式** = ``economy is not None
    and economy != EconomyEffect()``——非 None 但全默认如孪生素数不记 1,
    与旧机评分循环同判,29 号稿 §3)。"""
    return 1 if (eff is not None and eff != EconomyEffect()) else 0


# ===== 单卡组件(29 号稿 §2)=====
# (旧方向分触线集构造 _touched_line_comps/_locked_line_comps 已随方向分链
# 整线下线删除——29 号稿 §2.2 方向分行废止,git 历史可溯。)


def _locked_alignment_n(bindings: tuple[frozenset[str], frozenset[str]] | None,
                        locked_comp: str) -> int:
    """刷新 N 计数 = 绑定元素(阵营∪角色)命中终局阵容锁定单线的元素数。

    **绑定元素空间直读,不经触线阵容 集**(与方向分阵容 空间分开命名,
    29 号稿 §4-2 N 口径换基):终局阵容锁定帧旧口径本就只对终局阵容锁定计数,语义
    保真。locked_comp 不在 COMP_LIBRARY → 0(无终局阵容锁定单线可命中)。
    """
    if bindings is None:
        return 0
    lc = get_comp(locked_comp)
    if lc is None:
        return 0
    bound_facs, bound_chars = bindings
    return (sum(1 for f in bound_facs if f in lc.factions)
            + sum(1 for ch in bound_chars if ch in lc.core_chars))


# ===== 阵容冲突护栏(护栏设计 §2.2/§2.3)=====


def _conflict_basis(gs: GameState, locked_comp: str,
                    demoted_endgame: bool) -> frozenset[str]:
    """冲突基准(护栏设计 §2.2):锁定帧 = 锁线 Comp.factions——锁定 =
    终局方向裁定完成,历史误持不入基(误持黑塔纪元后锁定圣杯,基准 =
    锁线 factions,银河学者卡照排);未锁定帧 = 已持有投资的指向并集
    (环境 + 策略,持有 append-only → 基准单调不减,出域判定只收紧)。

    降格帧(demoted_endgame,现全库不可达,前瞻语义)锁线不入基 =
    回持有基——与模块既有 demoted 语义(``locked_comp and not
    demoted_endgame``)同构,降格 = 终局方向暂席,回退到持有信号比对。

    锁线名不可解析(OCR 漂移/非阵容名)→ 空集;基准空 = 护栏不辖,
    选卡行为与无护栏逐位一致。全部指向集查询经 kernel 归一口径
    (``env_faction_scope``/``strategy_faction_scope`` 内先
    ``normalize_invest_name``,持有名 OCR 形变不静默漏拦)。"""
    if locked_comp and not demoted_endgame:
        lc = get_comp(locked_comp)
        return frozenset(lc.factions) if lc is not None else frozenset()
    basis: set[str] = set()
    env_name = gs.active_env.value or ''
    if env_name:
        basis |= env_faction_scope(env_name)
    for name in (gs.active_strategies.value or []):
        basis |= strategy_faction_scope(name)
    return frozenset(basis)


def _components(canonical: str | None, opt: str, gs: GameState,
                locked_comp: str, demoted_endgame: bool,
                evicted: frozenset[str],
                strategy_priority: list[str]) -> tuple[
        float, float, float, float, float, float]:
    """单候选五组件 (现金,方向,赠卡,立场,转向轴) + 总分;未解析名
    (垃圾名)→ 全 0。

    - 现金分走 canonical(resolved ∧ > 0 才计,fail-closed 恒 0);
    - 方向分组件恒 0(方向分链整线下线;
      终局阵容锁定集 = 终局阵容锁定阵营线成员并集(空串/降格帧 → 未锁口径);
    - 赠卡分:STRATEGY_GRANTS + grant_gift_value(无条目自然 0);
    - 立场分:空表恒 0(表外卡默认 0);
    - 转向轴:strategy_priority 子串命中(OCR 容错,与白名单一致)加
      STEERING_PRIORITY_BONUS(软偏好)。
    """
    if canonical is None:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    cash, resolved = strategy_economy_value(canonical, gs)
    cash_v = cash if (resolved and cash > 0) else 0.0
    direction = 0.0   # 方向分链整线下线(strength/LINE_STRENGTH_SCORE 删除),恒 0
    grant = STRATEGY_GRANTS.get(canonical)
    gift = grant_gift_value(grant, evicted) if grant is not None else 0.0
    stance = STANCE_SCORE[canonical].score if canonical in STANCE_SCORE \
        else _STANCE_ZERO
    steer = STEERING_PRIORITY_BONUS if any(p in opt for p in strategy_priority) \
        else 0.0
    total = cash_v + direction + gift + stance + steer
    return (cash_v, direction, gift, stance, steer, total)


# ===== 帧评分存档(单次评分循环内随算随记,禁二次评分)=====


@dataclass(frozen=True)
class _Cand:
    """单候选评分存档。

    idx = options 容器下标(0 基,取值时机 = 本帧决策期快照);
    exact = 归一后精确命中注册表(get_strategy;LCS 兜底不入刷新分类,
    fail-closed——评分错只排错序、刷新错会弃掉真顶级卡,不对称风险取严);
    align_n = 终局阵容锁定帧绑定元素命中数(未锁定帧恒 0,N 无语义);
    off_direction = 阵容冲突护栏出域标记(基准非空 ∧ 指向集非空 ∧ 与基准
    零交,护栏设计 §2.3;基准空帧/通用卡恒 False)。
    """
    idx: int
    opt: str
    canonical: str | None
    total: float
    components: tuple[float, float, float, float, float]
    forbidden: bool
    blood: bool
    defining: bool
    engine: bool
    exact: bool
    align_n: int
    direction: float
    off_direction: bool


def _score_frame(options: list[str], gs: GameState, locked_comp: str,
                 demoted_endgame: bool, evicted: frozenset[str],
                 strategy_priority: list[str],
                 strategy_forbid: list[str],
                 basis: frozenset[str]) -> list[_Cand]:
    """帧评分一次(选卡/刷新两入口共享;板面 DoT/减益计数循环外单帧单读,
    沿旧机器纪律)。

    env 名防御(29 号稿 §3):get_env(o) 命中的候选 = 注册表交叉
    演化形态,跳过解析、0 分垫底(canonical=None 路径)。LCS 兜底命中即
    告警(观测锚,申报 5 义务实现)——精确 miss 而解析成功 = LCS 互撞
    形态,误中会把错卡的大额现金分赋给形变名,须可见。

    basis = 冲突基准(护栏设计 §2.2,调用方入口算好传入):仅对 canonical
    非 None 的候选算指向集并标出域——评分帧保留全量候选(不前置过滤,
    帧级门「候选恰 3」与刷新分类全量可见),排除在 :func:`_pick_domain`。"""
    locked_frame = bool(locked_comp) and not demoted_endgame
    cands: list[_Cand] = []
    for i, opt in enumerate(options):
        forbidden = any(p in opt for p in strategy_forbid)
        _norm = normalize_invest_name(opt)
        canonical: str | None = None
        if get_env(opt) is None:
            # env 名防御:仅防 env 名 LCS 误中策略名的交叉演化形态;
            # 策略屏选项域无 env 名,防御支正常帧不可达(29 号稿 §3)
            canonical = resolve_strategy_canonical(opt)
            if canonical is not None and _norm not in INVESTMENT_STRATEGIES:
                log.warning(
                    f'[cw!][invest_strategy] LCS 兜底命中(形变名 {opt!r} → '
                    f'{canonical!r});误中会赋错卡全组件分,请核对候选名')
        st = get_strategy(opt) if canonical is not None else None
        exact = st is not None
        eff = st.economy if st is not None else None
        blood = is_blood_economy(eff)
        defining = bool(augment_affinity(canonical)) if canonical is not None \
            else False
        engine = is_economy_engine(eff) if st is not None else False
        bindings = STRATEGY_BINDINGS.get(canonical) if canonical is not None \
            else None
        align_n = _locked_alignment_n(bindings, locked_comp) \
            if locked_frame else 0
        # 出域标记(护栏设计 §2.3):基准非空 ∧ 候选有指向 ∧ 与基准零交;
        # 通用卡(指向集空)与基准空帧恒不标记
        scope = strategy_faction_scope(canonical) \
            if canonical is not None else frozenset()
        off_direction = bool(basis) and bool(scope) and not (scope & basis)
        cash, direction, gift, stance, steer, total = _components(
            canonical, opt, gs, locked_comp, demoted_endgame, evicted,
            strategy_priority)
        cands.append(_Cand(
            idx=i, opt=opt, canonical=canonical, total=total,
            components=(cash, direction, gift, stance, steer),
            forbidden=forbidden, blood=blood, defining=defining,
            engine=engine, exact=exact, align_n=align_n,
            direction=direction, off_direction=off_direction))
    return cands


# ===== 平分裁决(29 号稿 §3)=====


def _tie_key(c: _Cand) -> tuple[float, int, int, int]:
    """平分裁决键:总分 → 无 canonical 殿后 → 品质序 → economy 有无。

    **无 canonical 候选恒排任何 canonical 候选之后**(防并列 0 分帧垃圾
    名凭槽序压过真卡;垃圾名之间按槽序)。槽序 = max() 首达语义(候选序
    即传入序)天然承载,不入键。"""
    if c.canonical is None:
        return (c.total, 0, 0, 0)
    st = INVESTMENT_STRATEGIES[c.canonical]
    return (c.total, 1,
            _RARITY_TIE_RANK.get(st.rarity, 0),
            _econ_effect_flag(st.economy))


def _argmax_tiebreak(cands: list[_Cand]) -> _Cand:
    """组件总分 argmax + 平分裁决键(键同分取槽序先者——max 首达语义)。"""
    return max(cands, key=_tie_key)


# ===== 结构分区(29 号稿 §3;全部零拍值)=====


def _pick_domain(cands: list[_Cand],
                 on_dot: bool) -> tuple[list[_Cand], str]:
    """结构分区,返回 (竞争域,归因标签串)。落地序 = 阵容冲突护栏 → 禁选
    → 自拆适用范围护栏 → 血本位三态 → 定义型(29 号稿 §3 + 护栏设计
    §2.3);标签按管线序拼接、空格分隔,常规帧空串(护栏未生效帧输出与
    无护栏逐位一致)。

    0. 阵容冲突护栏:出域候选(off_direction,与全部持有指向都冲突)
       排除——部分出域才滤(域收缩不可选,非负分);全部出域 → 回退全
       候选 argmax 不制造空选(tag ``off-direction fallback``,
       all-excluded-fallback 同形态);
    1. 禁选排除:被禁候选出局;禁选致候选域全空 → 全体候选(含被禁)
       退化(标签 all-excluded-fallback,调用方 argmax 最不负分者);
    2. 自拆台(适用范围护栏):板面 持续伤害+减益 ≥ 阈值时,克制 DoT/减益的
       候选 = 自拆台,**仅作用于非血非禁候选域**(禁选已先行收窄,此处
       即非血域);排除后该域空 → 自拆卡回归(自拆是策略回避立场非用户
       意志,不得制造血卡上位——1 自拆+2 血、2 禁+1 自拆复合帧与旧机器
       L1 行为对齐);
    3. 血本位三态序:非血域非空 → 其内竞争;仅非禁血卡可选 → 血卡间
       竞争(判据 = is_blood_economy,kernel 注册表派生零名单);
    4. 定义型分区:竞争域内存在定义型卡(augment_affinity 命中,「拿到
       即改写本局玩法」机制级声明)→ 域收缩为定义型子集,域内多张按
       组件总分 argmax(支配性优先的新机兑现,29 号稿 §3-4)。
    """
    tags: list[str] = []
    off = [c for c in cands if c.off_direction]
    if off:
        if len(off) == len(cands):
            tags.append('off-direction fallback')
        else:
            cands = [c for c in cands if not c.off_direction]
            tags.append('off-direction')
    live = [c for c in cands if not c.forbidden]
    if not live:
        tags.append('all-excluded-fallback')
        return cands, ' '.join(tags)
    nonblood = [c for c in live if not c.blood]
    if nonblood:
        if on_dot:
            kept = [c for c in nonblood if not counters_dot(c.opt)]
            domain = kept if kept else nonblood   # 自拆掏空 → 自拆卡回归
        else:
            domain = nonblood
    else:
        # 仅非禁血卡可选 → 血卡间竞争(L2;血克制卡无罚无排除,近死区)
        domain = [c for c in live if c.blood]
    defining = [c for c in domain if c.defining]
    if defining:
        tags.append('defining-zone')
        return defining, ' '.join(tags)
    if all(c.blood for c in domain):
        tags.append('blood-forced')
    return domain, ' '.join(tags)


# ===== 决策入口(29 号稿 §3/§4)=====


def _breakdown(c: _Cand) -> str:
    """归因串:总分 + 五组件分解(仅观测,进 reason;形态 = 测试仓
    行为测试 test_invest_strategy.py 锚定的 ``pick total=...`` 前缀)。"""
    _cash, _dir, _gift, _stance, _steer = c.components
    return (f'pick total={c.total:.0f}'
            f' cash={_cash:.0f} dir={_dir:.0f} gift={_gift:.0f}'
            f' stance={_stance:.0f} steer={_steer:.0f}')


def _pick_decision(cands: list[_Cand],
                   on_dot: bool) -> InvestStrategyDecision:
    """评分帧 → 选卡决策(结构分区 + 组件总分 argmax,平分裁决键取先;
    空候选帧不进本函数,由入口防御)。"""
    domain, tag = _pick_domain(cands, on_dot)
    winner = _argmax_tiebreak(domain)
    # 分区退化/收缩标签前缀(仅观测归因;管线序拼接):护栏出域/全出域
    # 回退/全禁帧退化/血强制帧/定义型分区收缩;常规帧无前缀(reason 形态
    # = 测试仓行为测试锚定的 pick total=... 前缀)
    reason = f'{tag} {_breakdown(winner)}' if tag else _breakdown(winner)
    return InvestStrategyDecision(
        idx=winner.idx, reason=reason, total=winner.total,
        components=winner.components)


def decide_pick(options: list[str], gs: GameState, locked_comp: str,
                demoted_endgame: bool, evicted: frozenset[str] | set[str],
                config: CurrencyWarConfig) -> InvestStrategyDecision:
    """纯选卡决策(无刷新判据;与 :func:`decide` 同一评分基线,永不建议刷)。

    独立成口的原因:decide 是纯函数,flow 同帧去重 memo 命中(handler
    刷新闸全败后的重调)时再调 decide 仍返建议——落选卡走本口,同一评分
    基线保证零选卡漂移(29 号稿 §4X;缺此口则建议帧三闸全败时
    op round_fail,现实可达路径)。冲突基准在此入口算好(护栏设计 §2.2,
    :func:`_conflict_basis`)传入评分帧。"""
    strategy_priority = list(getattr(config, 'strategy_priority', []) or [])
    strategy_forbid = list(getattr(config, 'strategy_forbid', []) or [])
    if not options:
        # 空候选帧(观察层失约形态;沿 env 落地件先例退化 idx=0 并标注
        # 归因,不抛错不盲发——op 层空候选已 round_fail 拦截,此态仅防御
        # 可达,29 号稿 §3)
        return InvestStrategyDecision(
            idx=0, reason='empty-frame: 无候选退化', total=0.0,
            components=(0.0, 0.0, 0.0, 0.0, 0.0))
    basis = _conflict_basis(gs, locked_comp, demoted_endgame)
    cands = _score_frame(options, gs, locked_comp, demoted_endgame,
                         frozenset(evicted), strategy_priority, strategy_forbid,
                         basis)
    on_dot = sum((gs.board.value or {}).get(f, 0)
                 for f in ('持续伤害', '减益')) >= BOARD_DOT_COUNT_THRESHOLD
    return _pick_decision(cands, on_dot)


def decide(options: list[str], gs: GameState, locked_comp: str,
           demoted_endgame: bool, evicted: frozenset[str] | set[str],
           config: CurrencyWarConfig,
           ) -> InvestStrategyDecision | StrategyRefreshSuggestion:
    """投资策略 3 选 1 决策(纯值出口;flow 包装动作词表,29 号稿 §4X)。

    - options = 屏上候选名列表(容器序);locked_comp/demoted_endgame/
      evicted 与现役 kernel 调用的三参同源(flow 意向状态直通);
    - 选卡 = 结构分区 + 组件总分 argmax(见 :func:`decide_pick`;冲突基准
      在本入口算好,护栏设计 §2.2);
    - 刷新判据(P81 承接,29 号稿 §4):帧级门 = 候选恰 3 ∧ 全
      精确分类 ∧ 帧内无帧级顶级卡 ∧(终局阵容锁定帧 max_N≠1)——帧级门失败
      (含未锁定帧)→ 整帧不刷,槽级不评;帧级门过 → 槽级动作集 = 非槽级
      顶级可刷/被禁与出域恒入/唯一 L1 守卫,动作集非空 → 建议(输出槽序
      元组;刷新余量三闸留 op 层,结构零改动);
    - **帧级顶级类 = 定义型 ∨ 持续通道引擎**(E-豁免:被禁/出域卡不入
      判定、不计 max_N);**槽级顶级类 = 帧级顶级类 ∨ 对齐保护**(终局
      阵容锁定帧 = 非血 ∧ N≥2 元素命中;未锁定帧 = 恒 False——方向分
      链整线下线后无「触 S/A 档线」判定,保守向不保护)。
    """
    strategy_priority = list(getattr(config, 'strategy_priority', []) or [])
    strategy_forbid = list(getattr(config, 'strategy_forbid', []) or [])
    if not options:
        return InvestStrategyDecision(
            idx=0, reason='empty-frame: 无候选退化', total=0.0,
            components=(0.0, 0.0, 0.0, 0.0, 0.0))
    basis = _conflict_basis(gs, locked_comp, demoted_endgame)
    cands = _score_frame(options, gs, locked_comp, demoted_endgame,
                         frozenset(evicted), strategy_priority, strategy_forbid,
                         basis)
    on_dot = sum((gs.board.value or {}).get(f, 0)
                 for f in ('持续伤害', '减益')) >= BOARD_DOT_COUNT_THRESHOLD
    locked_frame = bool(locked_comp) and not demoted_endgame

    slots = _refresh_slots(cands, on_dot, locked_frame)
    if slots:
        return StrategyRefreshSuggestion(
            reason=f'refresh: 帧级门过,可刷槽 {len(slots)}/3', slots=slots)
    return _pick_decision(cands, on_dot)


def _refresh_slots(cands: list[_Cand], on_dot: bool,
                   locked_frame: bool) -> tuple[int, ...]:
    """刷新判据(29 号稿 §4;P81 判据结构迁入,帧级/槽级两谓词分立)。

    返回可刷槽位元组;空元组 = 不建议刷(帧级门失败或动作集空)。
    **G8 消费序依赖沿旧机器纪律**:分类存档只在帧级触发(恰 3 ∧ 全精确)
    前提下消费——先判帧级门、后取分类;精确 miss 槽的分类值视为不可分类
    禁止下游消费(fail-closed,改动此序 = 静默击穿)。"""
    if len(cands) != 3 or not all(c.exact for c in cands):
        return ()
    # 帧级门③:帧内无帧级顶级卡(E-豁免:被禁/出域卡不入判定——被禁卡
    # 永不被选、出域卡被护栏排除,都不构成达档、不阻断触发;护栏设计 §2.3
    # 出域沿被禁同款)
    _top_frame = any((not c.forbidden) and (not c.off_direction)
                     and (c.defining or c.engine)
                     for c in cands)
    if _top_frame:
        return ()
    # 帧级门④:终局阵容锁定帧 max_N≠1(E-豁免:被禁/出域卡不计入 max_N;
    # max_N=0 或 ≥2 → 继续)。未锁定帧无 N 语义,本门只覆盖终局阵容锁定帧
    # (保守缺省:终局阵容锁定帧单元素命中 → 整帧不刷;门的依据重建归
    # P81 换基重演必答③;出域不计在数据面上冗余——绑元命中锁线则指向集
    # 必交基准、不可能是出域卡——与被禁同款防御性对称保留)
    if locked_frame:
        max_n = max((c.align_n for c in cands
                     if not c.forbidden and not c.off_direction), default=0)
        if max_n == 1:
            return ()
    # 槽级动作集:非槽级顶级可刷;被禁/出域槽恒入(被禁∧顶级/出域槽:
    # 永不被选,保护无对象 → 不保护;出域占槽应刷掉换本线卡机会,护栏
    # 设计 §2.3)。槽级顶级 = 帧级顶级 ∨ 对齐保护(终局阵容锁定帧 =
    # 非血 ∧ N≥2;未锁定帧 = 非血 ∧ 触 S/A 档线——血卡保护语义由血本位
    # 三态序覆盖,注册表演化出「血卡+绑定」时按已登记 J7 申报裁:保护无对象
    # → 不保护)
    action = [c.idx for c in cands
              if c.forbidden or c.off_direction
              or not (c.defining or c.engine
                      or (not c.blood and _alignment_guard(c, locked_frame)))]
    # F2 唯一 L1 槽守卫:L1 = 非血∧非禁∧非出域;恰一个时该槽不可刷——刷掉唯一
    # L1 且新卡为血/禁 → 三态序强制血选,确定损失分支,优势论证不闭合
    # (出域槽与被禁同款不算 L1:其被排除是护栏裁定,不存在「刷掉后被迫
    # 选它」的损失分支)。执行期「逐步重估」(覆盖 L1={A,B} 刷 A 后 B 成
    # 唯一的序贯形态)由 handler 槽序循环承载(kernel 单次调用不可表达的
    # 旧纪律原样保留)。
    l1 = [c.idx for c in cands
          if not c.blood and not c.forbidden and not c.off_direction]
    if len(l1) == 1 and l1[0] in action:
        action.remove(l1[0])
    return tuple(action)


def _alignment_guard(c: _Cand, locked_frame: bool) -> bool:
    """槽级对齐保护位(终局阵容锁定帧 N≥2;非血条件由调用方合取)。
    未锁定帧恒 False——方向分链下线后无「触 S/A 档线」判定,保守向不保护。"""
    if locked_frame:
        return c.align_n >= 2
    return False
