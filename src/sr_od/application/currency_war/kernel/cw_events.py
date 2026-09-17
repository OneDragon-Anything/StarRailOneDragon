"""货币战争 事件节点决策:投资策略/环境 3 选 1(decide_event;ADR-0143/0144 pick_value)+ 遭遇(decide_encounter)+ 补给(decide_supply)+ 巨星/伙伴选项类型。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_comps import (
    augment_affinity,
    candidate_faction_universe,
    form_progress,
    get_comp,
    gift_hit_tier,
    mechanics_fit,
    merged_mechanic_tables,
)
from sr_od.application.currency_war.kernel.cw_env_economy import (
    ECON_VALUE_NORM,
    env_economy_value,
)
from sr_od.application.currency_war.kernel.cw_equip_value import (
    equip_generic_value,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_slots_of,
    deployed_count_of,
    deployed_slots_of,
    max_units_of,
    plane_of,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    detect_signals,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_FACTION_MATCH_FLOOR,
    ENV_GIFTS,
    GIFT_FLOOR_ADVISOR_CORE,
    GIFT_FLOOR_CORE,
    GIFT_FLOOR_SHARED,
    EconomyEffect,
    get_env,
    get_strategy,
    is_blood_economy,
    pick_value_of,
    resolve_strategy_canonical,
    strategy_bindings,
)
from sr_od.application.currency_war.kernel.cw_vocab import PickEvent

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp

# ===== 事件 =====
# 设计注:boss 克制是 comp-vs-boss 机制级(走 boss_fit/
# comp.countered_by_bosses + 机制建模),非阵营级——不做阵营降权。

# 用户转向轴(投资策略/环境;develop config.md §3):priority 软加分 + forbid 重罚。
# (用户偏好配置,宪法允许面:分值是用户语义的载体非策略经验量。)
STEERING_PRIORITY_BONUS: float = 30.0     # soft:倾向选,可被 comp-hit(65-110)/增强定义(120)压过
STEERING_FORBID_PENALTY: float = 10000.0  # hard−:有替代永不选

# (品质→敌难度机制 = 游戏定义:金 +3 / 棱彩 +6(核心机制 38-40)。旧选卡
# 难度惩罚 棱彩−12/−24、金−6/−12 已退役 2026-09-04(「未证即退役」裁定:
# 机制方向是游戏文本,但惩罚幅度无游戏定义或证明出处,选卡侧无法从定义量
# 推出「难度+3 值多少分」——幅度退役置 0。连同退役:_option_rarity LCS
# 品质兜底与 INVESTMENT_STRATEGIES_KEYS 缓存(唯一消费 = 该惩罚)。)


# 「克 DoT/减益」的机制属性集合(与 MECHANIC_COUNTERS 值域对齐)
_DOT_PUNISHED_MECHS: frozenset[str] = frozenset({'DoT', '减益'})


# ===== 投资选卡新定序结构(ADR-0597;用户裁定 2026-09-08「优先经济,
# 然后是终局阵容」;S0/S0'/S1/S4/叠加项语义保留,S2 新增/S3 换源重构)=====

# S2 经济引擎档域带(ADR-0524 定序实现常数;锚位声明 = 110 < S2 下界 且
# S2 上界 < 120:S2 整带压过终局对齐族上界(45×2+20=110)、低于定义型
# augment 档(120,S1>S2 编者预裁)。档内序 = PICK_VALUE 线性归一到带内
# (monotone,只承载带内先后,禁读基数);PV_NORM 取评估分域上界 100。
ECON_ENGINE_BAND_BASE: float = 111.0
ECON_ENGINE_BAND_SPAN: float = 8.0
ECON_ENGINE_PV_NORM: float = 100.0

# 持续通道字段闭集(S2 谓词的单一源;出处 = 方案 §3.1 分族表→ADR-0597 §3):
# 「引擎 vs 一次性」的界 = 效果原文持续/一次性结构事实,零幅度拍值。四族:
# 利息(interest_flat_per_node;interest_cap_override 单列)/持续金流/刷新/
# 经验。经验通道属经济 = ADR-0131 EconomyEffect docstring 明文含经验 +
# 「经验就是财富」效果原文 XP↔金 1:1 游戏定义兑换(候裁 2a 推荐采纳)。
# **不入集**:一次性金族(instant_gold/gold_at_node/gold_at_level/
# gold_per_hp_lost_now)、期权/难度族、血本位族(hp_gold_swap/
# xp_buy_hp_cost,另由 is_blood_economy 集合排除)、补偿型
# gold_per_20hp_lost(不属四族);孪生素数(EconomyEffect(xp_instant=0)
# 全默认)自然 miss。
_ECON_ENGINE_SINGLE_FIELDS: tuple[tuple[str, float], ...] = (
    # (字段, 默认值):非默认即通道存在。
    ('gold_per_node', 0), ('gold_per_boss_node', 0),
    ('gold_per_level_up', 0), ('gold_per_three_5cost', 0),
    ('gold_per_2star2cost_merge', 0), ('gold_per_3star_merge', 0),
    ('interest_flat_per_node', 0),
    ('win_reward_mult', 1.0), ('sell_price_mult', 1.0),
    ('free_refresh_per_node', 0), ('free_refresh_burst', 0),
    ('refresh_surprise_every', 0), ('refresh_per_compose', 0),
    ('refresh_free_chance', 0.0), ('refresh_shop_rewrite_every_3cost', 0),
    ('xp_per_refresh', 0), ('xp_per_node', 0), ('xp_buy_cost_discount', 0),
    ('xp_instant', 0),
)
# 配对字段通道:效果语义两半齐备才存在(「接下来 count 次每次 amount」/
# 「level 起单击减金」)——任一半缺省 = 通道不存在。
_ECON_ENGINE_PAIR_FIELDS: tuple[tuple[str, str], ...] = (
    ('gold_next_nodes_amount', 'gold_next_nodes_count'),
    ('xp_click_discount_from_level', 'xp_click_discount_from_level_at'),
)


def is_economy_engine(economy: EconomyEffect | None) -> bool:
    """S2 经济引擎档谓词(ADR-0597):economy 存在非默认的持续通道字段。

    结构事实判据(存在性,非幅度):命中任意持续通道字段即真;字段值不参与
    定序(档内先后由 PICK_VALUE 承载)。与血本位排除族零交集(两族字段不
    相交,ADR-0578 对账声明)。
    """
    if economy is None:
        return False
    if economy.interest_cap_override is not None:
        # 有效值口径:0 也是有效覆写(买断制 cap=0 = 息通道改写)。
        return True
    for name, default in _ECON_ENGINE_SINGLE_FIELDS:
        if getattr(economy, name) != default:
            return True
    for amt, cnt in _ECON_ENGINE_PAIR_FIELDS:
        if getattr(economy, amt) != 0 and getattr(economy, cnt) != 0:
            return True
    return False


def _invest_d_star(gs: GameState, locked_comp: str,
                   demoted_endgame: bool,
                   evicted: frozenset[str] | set[str]) -> tuple[set[str], set[str], str]:
    """投资选卡的「预期终局方向」D* 解析(ADR-0597;级联单规则零阶段特判)。

    ①终局锁线:``locked_comp`` 非空取其绑定集(P2+ 主形态;P1 ①资格锁局
      照常落此,配方锁局恒空由级联自然落②③);``demoted_endgame`` 帧
      D*=∅——降格终局「赢不了就少输」无对齐语义,detect_signals 不查
      降格标志,此短路必要(防降格帧②复活对齐)。
    ②资产层信号:``detect_signals`` ②family_bond/③core_card/④resource
      (①层 env/strategy 亲和排除 = 反投资自证:候选卡的亲和不得参与证明
      选它自己,自证排除同构),继承 evicted 过滤(「等同信号未发生」契约的
      消费面镜像,意向层 :1189 同款)+ weak_planes 弱面过滤(注册表自注
      位面死路,意向层 :1197 同款);取 (layer 升序, weight 降序,
      comp_name 字典序)最优线。
    ③皆空:D*=∅ → S3 全体 N=0,候选自然落 S2/S4,不引入兜底方向。
    P2 缓锁门/H1 环境门/P1 ①资格过滤**不继承**(ADR-0597 §2 五门裁决:
    辖「锁线动作资格」非「方向证据本体」;缓锁门另需 session/registry,
    kernel 纯函数结构性不可达)。
    返回 (factions, core_chars, source);source ∈ 'locked'|'signal'|''。
    """
    if demoted_endgame:
        return set(), set(), ''
    if locked_comp:
        comp = get_comp(locked_comp)
        if comp is not None:
            return set(comp.factions), set(comp.core_chars), 'locked'
    sigs = [s for s in detect_signals(gs)
            if s.layer != 1
            and s.comp_name not in evicted
            and plane_of(gs) not in (getattr(get_comp(s.comp_name),
                                            'weak_planes', ()) or ())]
    if not sigs:
        return set(), set(), ''
    best = sorted(sigs, key=lambda s: (s.layer, -s.weight, s.comp_name))[0]
    comp = get_comp(best.comp_name)
    if comp is None:   # detect_signals 只对 COMP_LIBRARY 在册线发射,防御保底
        return set(), set(), ''
    return set(comp.factions), set(comp.core_chars), 'signal'


def _opt_counters_dot(opt: str) -> bool:
    """选项(词缀/环境名)是否克制 DoT/减益主派 —— 机制注册表单一源。

    名 → ``AFFIX_MECHANIC_MAP`` 机制 tag → ``MECHANIC_COUNTERS`` 克制属性,与「净化身心」
    同类的任意 anti-DoT 词缀/环境都覆盖(不止单点名);子串包含匹配保留旧 OCR 容错语义。
    未知名(不在映射)→ False(不惩罚)。包词缀按开关并表(全关=基表零漂移)。
    """
    affix_map, counters, _ = merged_mechanic_tables()
    for affix, tag in affix_map.items():
        if affix in opt and not _DOT_PUNISHED_MECHS.isdisjoint(counters.get(tag, ())):
            return True
    return False


def decide_event(options: list[str], config, gs: GameState,
                 locked_comp: str = '', demoted_endgame: bool = False,
                 evicted: frozenset[str] | set[str] = frozenset()) -> PickEvent:
    """事件选项打分(投资策略/环境 3 选 1;判据重构,ADR-0597)。

    分值来源优先级表(每项只在**高于当前分**时覆盖;ADR-0143/0144/0144b 语义;
    ADR-0524 定序改形:各分值族只承载同族定序语义,跨族仅保留 max() 覆盖
    结构,禁新增加减叠加消费点;用户裁定 2026-09-08「投资选卡优先经济、
    然后是终局阵容,不为过渡阵容服务」——comp 命中层的对齐对象由过渡对
    target_comp 换 D* 预期终局方向,解析 = :func:`_invest_d_star`:D*①
    锁线 comp 由 decide_invest 从意向状态解析传入,D*② kernel 内直算
    detect_signals,单帧单读):
    1. 用户 forbid(−10000):唯一压过一切的家,有替代永不选
    2. augment 定义型(120,支配性优先序):黑塔纪元/飞光类拿到即改写本局玩法 →
       优先于一切常规评估项(S2 域带/S3 对齐 110/steering +30 之上);
       120 是该优先序的定序实现常数(ADR-0152 机制级声明),非基数
    3. **S2 经济引擎档(本批新增)**:EconomyEffect 含持续通道字段的策略卡
       (:func:`is_economy_engine`,一次性金/期权/难度/血本位不入),域带
       111-119(整带压过 S3 上界 110、低于 S1 120),档内序 = PICK_VALUE
       归一带内(monotone,定序实现常数)
    4. S3 终局对齐族(信号源 = D*,换源重构):comp 命中 45×N+20 =
       选项绑定∩D* 绑定集(N 单调定序语义与 45/20 常数沿 ADR-0143/0152/
       16 号稿 §1.5 现状保留);env 阵营 floor(三档 = category 定序档位
       邀请 70<契约 72<概念股 78,禁读基数,ADR-0524)触发条件 =
       _env.faction ∈ D*_factions(预裁③:floor 与 comp-hit 同批换源)。
       D*=∅(冷启动/降格帧)→ 全体 N=0、floor 不触,候选自然落 S2/S4
    5. S4 常规评估层(现状保留):策略评估分 pick_value(12-75,ADR-0143
       知识判据定序器)/ env 裸分(ADR-0144;全集门前置——faction 非空 ∧ ∉
       候选终局阵容全集的环境跳过本支,失格归因 ``env-off-universe`` 仅观测)/
       eval-lcs(策略 OCR 形变裸分,
       **env 名跳过**——0144b 守卫,83 env 名 29 个 LCS 误中策略名)/
       品质回落(纯字典序,零拍值,ADR-0524):仅未评估卡可达,主键=品质序
       (棱彩>金>银,游戏定义),次键=economy 效果有无;回落域整体
       压低于评估分域(评估分有知识判据依据,回落只是「未评估时别全盲」)
    env 分支内机制按 invest-env 迭代 design.md §2.3 汇合次序组合(单一真源,
    max() 覆盖定序):全集门 → 裸分(env-eval)→ 送卡静态档(ENV_GIFTS 命中:
    gift-core 66/gift-shared 60/advisor-core 54,消费契约 =
    ``cw_comps.gift_hit_tier`` docstring;发卡角色全集外 → 0,
    env-gift-off-universe)→ 经济域带(env_economy_value resolved ∧ > 0 →
    S2 同款 111-119 带,归一 = ECON_VALUE_NORM,归因 env-econ)→ 阵营 floor
    → steering。值域链:裸分 0-72 ⊇ 送卡档 54-66 < floor 70-78 < 域带
    111-119——「静态结构证据 < 动态对齐 < 真金流」。
    叠加项(全部之后):机制克制惩罚(-100 档,MECHANIC_COUNTERS 单一源)/
    用户转向轴(策略/环境 priority +30 soft、forbid −10000 hard−,config.md §3)。
    未注册非 env = 0 分。刷新判据见函数尾刷新判据段。
    刷新判据双轴:策略帧 = ADR-0600;环境帧 = invest-env 迭代 §2.8
    (3.5 接线,取代 ADR-0600「env 帧恒不刷」F9 规则——行为翻转在册申报)。

    **裁定回避(集合级排除,非分值族;[40]①「主动选择=回避」,ADR-0578)**:
    血本位候选(判据 = ``cw_investments.is_blood_economy``,注册表派生零名单)
    不进上述任何分值族的竞争——三态触发序在评分循环之后收口:①可入选非血集
    非空 → 其 argmax;②仅非禁血卡可选 → 血卡间常规评估序 argmax;③全禁帧
    → 全体 argmax(现状退化零漂移)。排除是结构规则不是定价:任何罚值都是
    拍值,且给血计分触 [40]③ 定价禁域。血卡排位于「可入选非血卡」
    之后、「被禁非血卡」之前(user-forbid「有替代永不选」的血卡替代在 ② 兑现)。
    S2 谓词与血本位字段零交集(四族闭集不含 hp_gold_swap/xp_buy_hp_cost,
    ADR-0597 对账);归因串 ``econ-engine``/``align×N``/``align-locked``/
    ``align-signal`` 为 ADR-0597 批新增,env 轴 ``env-off-universe``(全集门)/
    ``env-econ``/``gift-core``/``gift-shared``/``advisor-core``/
    ``env-gift-off-universe``(invest-env 3.5)同口径:全部仅观测归因,
    不进任何检查器白名单(C1→D4 迁移兼容,裁定见 sim/checks/suspects.py 模块头)。
    """
    strategy_priority = list(getattr(config, 'strategy_priority', []) or [])
    strategy_forbid = list(getattr(config, 'strategy_forbid', []) or [])
    env_priority = list(getattr(config, 'env_priority', []) or [])
    env_forbid = list(getattr(config, 'env_forbid', []) or [])
    on_dot = sum((gs.board.value or {}).get(f, 0) for f in ('持续伤害', '减益')) >= 2
    penalty = 100
    # 品质回落字典序的序数编码(ADR-0524):品质序=游戏定义(棱彩>金>银),
    # 主键 rank(0/1/2)+ 次键 econ(0/1);×2 保证次键永不翻转主键——
    # 两个常数都是纯位置编码,不是拍定的语义幅度(序到分的映射无推导,
    # 同「未证即退役」判)。
    _rarity_lex_rank: dict[str, int] = {'银': 0, '金': 1, '棱彩': 2}
    # D* 单帧单读(ADR-0597):每决策帧现算一次快照,帧内不重读——
    # 「K 活读数轮内重排」病灶在消费面结构性不可发生。
    _d_facs, _d_chars, _d_src = _invest_d_star(
        gs, locked_comp, demoted_endgame, evicted)
    # 候选全集单帧单读(与 D* 快照同款纪律):env 分支全集门的派生输入,
    # 循环外一次派生,帧内禁重读。
    _universe = candidate_faction_universe(evicted)

    best_idx, best_score = 0, -1.0
    best_reason = ''
    # [40]① 血本位分区随算随记(ADR-0578,单次评分循环内,不二次评分):
    # 每候选记录 (得分, 归因, 是否血本位, 是否被禁)——三态触发序在循环后收口。
    _cand_scores: list[float] = []
    _cand_reasons: list[str] = []
    _cand_blood: list[bool] = []
    _cand_forbid: list[bool] = []
    # 刷新判据的逐槽分类存档(循环内顺手存,不二次评分):exact =
    # 策略轴归一后精确命中(get_strategy;LCS 兜底不入刷新分类,fail-closed
    # 见帧级闸——评分侧对形变名既定判定就是「comp/economy 修饰不可靠」,
    # 评分错只排错序、刷新错会弃掉真顶级卡,不对称风险取严)/ s1 = 定义型档
    # / engine = S2 经济引擎档 / align_n = S3 对齐档 N。消费序安全依赖(G8):
    # 只在帧级触发(三卡全精确分类)前提下消费——先判帧级闸、后取分类。
    # env 三件(3.5 环境刷新判据同款纪律):env = 环境注册表精确命中(env
    # 帧级闸)/ env_off = 全集门失格(零价值槽判定;非 env 槽恒 False)/
    # pri = user-priority 命中(零价值槽豁免:用户点名保选的集外槽不刷)。
    _cand_exact: list[bool] = []
    _cand_s1: list[bool] = []
    _cand_engine: list[bool] = []
    _cand_align_n: list[int] = []
    _cand_env: list[bool] = []
    _cand_env_off: list[bool] = []
    _cand_pri: list[bool] = []
    for i, opt in enumerate(options):
        score = 0.0
        reason = 'eval'
        _st = get_strategy(opt)
        _env = get_env(opt)   # 提前查 env 表(防跨表污染,见下 eval-lcs/惩罚两处守卫)
        _pv = None if _env is not None else pick_value_of(opt)
        # ↑ ADR-0144b 跨表污染守卫:83 env 名中 29 个会 LCS 误中策略名(全量扫描实测:列车同行概念股→
        # 列车同行星徽28/增发货币→超发货币55 等)——env 名走 env 分支评分,不进策略 LCS 兜底。
        # ADR-0152(评审🔴3a)augment 定义型 comp:黑塔纪元/飞光等拿到即改写本局玩法(216 张黑塔
        # 入商店/师徒变身)—— 支配性优先序(ADR-0524 定形,16 号稿 §1.4):定义型命中优先于
        # 一切常规评估项(S2 域带/S3 对齐 110/升费 100/steering +30 之上),仅低于用户 forbid;120 是
        # 该零参数结构规则的定序实现常数,禁读作基数。(M1 资源入口:拿到 = 换打法)
        # [40]① 候选级血本位分类(N2 挂点,ADR-0578):精确名 miss(OCR 形变)的
        # 策略候选在进任何分值支**之前**先解析分类——不依赖后续分值支可达性
        # (评估表未命中 → eval-lcs 分支不可达,分支内挂点会让未评估血卡漏分
        # 区)。仅策略轴候选解析;env 名禁进策略解析(上方 ADR-0144b 守卫同款:
        # 29/83 env 名会 LCS 误中策略名,误分类会错杀 env 选项)。
        _is_blood = False
        if _st is not None:
            _is_blood = is_blood_economy(_st.economy)
        elif _env is None:
            _canon = resolve_strategy_canonical(opt)
            if _canon is not None:
                _canon_st = get_strategy(_canon)
                if _canon_st is not None:
                    _is_blood = is_blood_economy(_canon_st.economy)
        _aug = augment_affinity(opt)
        _is_engine = False
        if _st is not None:
            _is_engine = is_economy_engine(_st.economy)
        if _aug:
            score = max(score, 120.0)
            reason = 'augment-defining'
        _comp_hit = 0
        if _st is not None:
            _fs, _cs = strategy_bindings(_st)
            _comp_hit = len((_fs & _d_facs) | (_cs & _d_chars))
            if _comp_hit:
                # 45×N+20 = 定序实现常数:N 的单调序数承载优先序(16 号稿 §1.5);
                # N≥1 域(≥65)压过纯基准分域(品质回落 0-5/未注册 0),N=2(110)
                # 再压过单命中与评估分上界 75。立项挂账:台账价值候选锚 =
                # ΔP̂ 完成概率增量参数化(08 E1/E2,owner=事件面命题批,ADR-0524)。
                score = max(score, 45.0 * _comp_hit + 20.0)
                reason = f'align×{_comp_hit}'
            # S2 经济引擎档(ADR-0597):持续通道策略卡整带(≥111)压过
            # S3 上界(110),用户裁定「优先经济」的分值载体;档内序 = PICK_VALUE
            # 归一带内(只承载带内先后)。域带是 max() 覆盖结构的一员,非加减叠加。
            if _is_engine:
                _pv_norm = min(float(_pv) if _pv is not None else 0.0,
                               ECON_ENGINE_PV_NORM)
                _s2 = ECON_ENGINE_BAND_BASE + ECON_ENGINE_BAND_SPAN * (
                    _pv_norm / ECON_ENGINE_PV_NORM)
                if _s2 > score:
                    score, reason = _s2, 'econ-engine'
            # ADR-0143 评估分(知识判据定序器)优先;未评估卡 → 品质回落字典序
            # (ADR-0524,纯字典序零拍值:主键品质序+次键经济有无)。
            if _pv is not None:
                _prior = float(_pv)
            else:
                _econ = 1 if (_st.economy is not None and _st.economy != EconomyEffect()) else 0
                _prior = float(_rarity_lex_rank.get(_st.rarity, 0) * 2 + _econ)
            if _prior > score:
                score, reason = _prior, ('eval' if _pv is not None else f'prior-{_st.rarity}')
        elif _pv is not None and float(_pv) > score:
            # 精确名 miss 但 LCS 命中评估表(OCR 形变)→ 裸评估分(comp/economy 修饰不可靠)
            score, reason = float(_pv), 'eval-lcs'
        # ADR-0144(环境侧评估分):env 名不在策略注册表(原恒 0 分 → fallback 恒选第一张);
        # 基准分 + 阵营定向条件分(概念股/邀请/契约 faction ∈ D*_factions——
        # 换源:floor 与 comp-hit 同批从过渡对换 D*,预裁③;D*=∅ 不触)。
        # OCR 形变的 env 名(如 尾彩•变体)不进策略 LCS(上方 _env 精确查 miss 时仍可能污染 ——
        # 但 OCR 只出现在 handler 层归一名后才进决策,形变 env 名实际不达此处;守卫以精确查为准)。
        if _st is None and _env is not None:
            # 候选全集门(形态 B;用户裁定 2026-09-12「我们有对应的终局阵容定义,
            # 才选对应的投资环境」):faction 非空 ∧ faction ∉ 候选终局阵容全集
            # → 跳过裸分支,分数维持 0(env 无品质字段、品质回落域在策略分支内,
            # env 本就无回落——落 0 即天然垫底,零新常量);faction 空(时代/经济/
            # 规则/随机送角色等阵容无关型)恒放行。
            _env_in_universe = (not _env.faction) or (_env.faction in _universe)
            if _env_in_universe:
                if _env.pick_value > 0 and float(_env.pick_value) > score:
                    score, reason = float(_env.pick_value), 'env-eval'
                # 送卡静态档 max() 支(invest-env 迭代 3.5;details/
                # env-value-models.md §2.1.3 消费位,分派映射 = 禁二次推导的
                # 单一源契约,见 ``cw_comps.gift_hit_tier`` docstring 消费契约):
                # 白得契约全员集外 → 失格 0(tier='off' ∧ 非 advisor ∧ 即时集
                # 非空;advisor off = 不买无浪费、条件降档落底 = 未到手,均维持
                # 裸分);命中档有 floor 常数 → max 提档(core/shared/advisor-core,
                # advisor 由 grant.advisor 换族)。归因串仅观测,不进检查器白名单
                # (C1→D4 口径,裁定见 sim/checks/suspects.py 模块头)。
                _grant = ENV_GIFTS.get(_env.name)
                if _grant is not None:
                    _tier = gift_hit_tier(_grant, evicted)
                    if (_tier == 'off' and not _grant.advisor
                            and bool(_grant.chars_immediate)):
                        score = 0.0
                        reason = 'env-gift-off-universe'
                    elif (not _grant.advisor and _tier == 'core'
                            and score < GIFT_FLOOR_CORE):
                        score, reason = float(GIFT_FLOOR_CORE), 'gift-core'
                    elif (not _grant.advisor and _tier == 'shared'
                            and score < GIFT_FLOOR_SHARED):
                        score, reason = float(GIFT_FLOOR_SHARED), 'gift-shared'
                    elif (_grant.advisor and _tier == 'core'
                            and score < GIFT_FLOOR_ADVISOR_CORE):
                        score, reason = (float(GIFT_FLOOR_ADVISOR_CORE),
                                         'advisor-core')
                    # 其余(advisor 的 shared/transition/off、条件降档后非
                    # core/shared)无 floor 维持裸分(即时空 ∧ 条件全集外的
                    # 推论支同落此——条件发放未到手,off 只是不提档)。
                # 经济域带 max() 支(invest-env 迭代 3.5;design.md §2.3 门 4,
                # 用户裁定「优先经济」的环境轴载体):整局金等价期望 resolved
                # ∧ > 0 才进带(缺参/CI 不闭合 fail-closed → 消费端按无经济
                # 通道处理,退裸分);域带常量复用策略卡 S2(三选一帧同质,
                # F9 已证不同帧不同场竞争,共享域带 = 跨轴同序零新常数),
                # 期望按 ECON_VALUE_NORM 归一带内(带内序 monotone,定序
                # 实现常数,禁读基数)。经济入模环境全部 faction 空(design
                # §2.2.1 注),与本分支上方全集门结构性无交集。
                if _env.economy is not None:
                    _econ_gold, _econ_ok = env_economy_value(_env.name, gs)
                    if _econ_ok and _econ_gold > 0:
                        _band = ECON_ENGINE_BAND_BASE + ECON_ENGINE_BAND_SPAN * (
                            min(_econ_gold, ECON_VALUE_NORM) / ECON_VALUE_NORM)
                        if _band > score:
                            score, reason = _band, 'env-econ'
            else:
                # 失格归因串(全无用帧胜出时可见);仅观测归因,不进任何
                # 检查器白名单(C1→D4 口径,裁定见 sim/checks/suspects.py 模块头)。floor 不受门辖:
                # D* ⊆ 全集恒成立(锁线 comp 与 evicted 互斥/信号已按 evicted
                # 过滤),阵营 floor 永不为全集外 faction 触发,无交叉处理。
                reason = 'env-off-universe'
            if _env.faction and _env.faction in _d_facs:
                # 阵营匹配定序门(ADR-0524 定形,16 号稿 §1.3):三档值 = category 间
                # 定序档位(邀请 70 < 契约 72 < 概念股 78,评估实证序),承重语义 =
                # 「匹配 ⇒ 提到本 category 档位、压过全体 env 裸分(上界 72)」,
                # 禁读作基数。default 70.0 = 兜底档(未知 category)。
                _floor = ENV_FACTION_MATCH_FLOOR.get(_env.category, 70.0)
                if _floor > score:
                    # 归因串 = D* 来源级(ADR-0597;align-locked=①锁线/
                    # align-signal=②资产信号;仅观测归因)。
                    score = _floor
                    reason = ('align-locked' if _d_src == 'locked'
                              else 'align-signal')
        # 用户转向轴(develop config.md §3):投资策略/环境 priority 软加分 + forbid 重罚。
        # 选项归属:env 注册表命中走 env 轴,其余(策略/未注册)走 strategy 轴 —— env 名经 handler
        # 归一后才进决策(ADR-0144b),未注册项按事件主流(投资策略)处理。子串匹配与白名单一致(OCR 容错)。
        _pri = env_priority if _env is not None else strategy_priority
        _pri_hit = any(p in opt for p in _pri)
        if _pri_hit:
            score += STEERING_PRIORITY_BONUS
            reason = 'user-priority'
        _forbid = env_forbid if _env is not None else strategy_forbid
        _opt_forbidden = any(p in opt for p in _forbid)
        if _opt_forbidden:
            score -= STEERING_FORBID_PENALTY
            reason = 'user-forbid'
        if on_dot and _opt_counters_dot(opt):
            score -= penalty
        _cand_scores.append(score)
        _cand_reasons.append(reason)
        _cand_blood.append(_is_blood)
        _cand_forbid.append(_opt_forbidden)
        _cand_exact.append(_st is not None)
        _cand_s1.append(bool(_aug))
        _cand_engine.append(_is_engine)
        _cand_align_n.append(_comp_hit)
        _cand_env.append(_st is None and _env is not None)
        _cand_env_off.append(_st is None and _env is not None
                             and not _env_in_universe)
        _cand_pri.append(_pri_hit)
        if score > best_score:
            best_score, best_idx, best_reason = score, i, reason
    # [40]① 血本位回避·三态触发序(ADR-0578;裁定「主动选择=不选」):
    # L1 可入选非血集(非血 ∧ 非 forbid)非空 → 其 argmax(既有管线分值全序,
    #     内序零漂移;血卡无论被 priority +30 抬多高都进不了本分区——排除是
    #     集合级结构规则,分值族软加分不可逾越);本帧存在血卡候选时 winner
    #     reason 附 '+blood-avoided'(观测锚,零新遥测通道)。
    # L2 可入选非血集空 ∧ 非禁血卡非空 → 血卡间常规评估序 argmax(被禁非血卡
    #     让位于血卡 = user-forbid「有替代永不选」的替代语义兑现)。
    # L3 全禁帧(含血与非血混合全禁)→ 全体 argmax 最不负分者,现状退化零
    #     漂移——全禁帧 forbid 已无「替代」可用,把血卡抬到被禁非血卡之上
    #     无根据(超防御态,判读面 reason 可辨)。
    _l1 = [j for j in range(len(options))
           if not _cand_blood[j] and not _cand_forbid[j]]
    _l2 = [j for j in range(len(options))
           if _cand_blood[j] and not _cand_forbid[j]]
    if _l1:
        if best_idx not in _l1:
            # 全体 argmax 落在血卡/被禁卡 → 分区内重选(strict > 取首序与主循环同语义)
            _j = max(_l1, key=lambda k: _cand_scores[k])
            best_idx, best_score, best_reason = _j, _cand_scores[_j], _cand_reasons[_j]
        if any(_cand_blood):
            best_reason = f'{best_reason}+blood-avoided'
    elif _l2:
        if best_idx not in _l2:
            _j = max(_l2, key=lambda k: _cand_scores[k])
            best_idx, best_score, best_reason = _j, _cand_scores[_j], _cand_reasons[_j]
        best_reason = f'blood-forced({best_reason})'
    # ===== 事件面刷新判据(ADR-0600 §3.1;推导 = ADR-0600 §3.2 +
    # math_proofs P81;零阈值结构存在性判据,逐槽弱占优论证承载;旧评估分
    # 阈值判据已退役,推导已换代重立,退役史归档)=====
    # G8 消费序依赖(安全面,勿改序):下列 _cand_* 存档量只在帧级触发
    # (三卡全精确分类)前提下消费——先判帧级闸、后取分类。精确 miss 槽的
    # 存档值(如经 resolve_strategy_canonical LCS 兜底的 _cand_blood)视为
    # 不可分类禁止下游消费;改动此序 = 静默击穿 fail-closed(锁 6/锁 3 辖)。
    refresh_slots: tuple[int, ...] = ()
    if len(options) == 3 and all(_cand_exact):
        # 全 env 帧守卫(零 kind 参,decide_event 签名不变):三选项全部精确命中
        # 环境注册表(get_env 同源查表)→ env 帧,走下方环境判据分支,不进本策略
        # 判据。策略∩环境注册表精确/归一后双 ∅(直调在案),all(_cand_exact) 已
        # 蕴含非 env 帧,本守卫只防注册表交叉演化;即使误判,后果方向 = 漏刷
        # (保守向,失败安全)。
        _env_frame = all(get_env(o) is not None for o in options)
        if not _env_frame:
            # 帧级触发门(ADR-0600 §3.1):
            # ① S1/S2 达档检查——被禁卡不参加达档判定(P5①:被禁卡永不被选,
            #    不构成达档、不阻断触发);
            # ② max_N ≠ 1 门——N 档 = 非被禁候选的绑定∩D* 绑定数(J6:被禁卡
            #    不计入 max_N);帧内最高对齐档 = 1 → 整帧不刷(N=1 价值地位
            #    未决挂账,与 S4 抽样的交换不可比 → 保守缺省,
            #    ADR-0600 §3.2);max_N=0(无对齐)或 ≥2 → 继续。
            _s1s2_hit = any(
                (not _cand_forbid[j]) and (_cand_s1[j] or _cand_engine[j])
                for j in range(3))
            if not _s1s2_hit:
                _max_n = max((n for j, n in enumerate(_cand_align_n)
                              if not _cand_forbid[j]), default=0)
                if _max_n != 1:
                    # 槽级动作集:非顶级槽可刷。顶级 = S1 ∨ S2 ∨ [N≥2 对齐]
                    # ——顶级判定在被禁卡上恒取否(P5② 被禁槽恒入可刷集,含
                    # 被禁∧N≥2 对齐槽:永不被选,保护无对象);血∧N≥2 现行不可达
                    # (两血卡 STRATEGY_BINDINGS 双空恒 N=0,直调在案),注册表
                    # 演化致可达时按 ADR-0600 §3.1 J7 申报裁:保护无对象 → 不保护。
                    _action = [
                        j for j in range(3)
                        if _cand_forbid[j] or not (
                            _cand_s1[j] or _cand_engine[j]
                            or ((not _cand_blood[j]) and _cand_align_n[j] >= 2))
                    ]
                    # F2 唯一 L1 槽守卫(kernel 静态口径):L1 = 非血∧非禁
                    # (cw_investments.is_blood_economy + user-forbid);恰一个时
                    # 该槽不可刷——刷掉唯一 L1 且新卡为血/禁 → 三态序强制血选,
                    # 确定损失分支,优势论证不闭合。执行期「逐步重估」(覆盖
                    # L1={A,B} 刷 A 后 B 成唯一的序贯形态)由 handler 槽序循环
                    # 承载(kernel 单次调用不可表达,单帧锁 14)。
                    _refresh_l1 = [j for j in range(3)
                                   if not _cand_blood[j] and not _cand_forbid[j]]
                    if len(_refresh_l1) == 1 and _refresh_l1[0] in _action:
                        _action.remove(_refresh_l1[0])
                    refresh_slots = tuple(_action)
    elif len(options) == 3 and all(_cand_env):
        # ===== 环境帧刷新判据(invest-env 迭代 3.5,design.md §2.8;取代
        # ADR-0600 §2/§4「env 帧恒不刷」F9 规则——既有在册行为的翻转,启用
        # 前置「环境侧顶级类建模」由经济域带/送卡档接线满足)=====
        # 帧级门:候选恰 3 ∧ 全部精确命中环境注册表(all(_cand_env));未注册名
        # 形变帧两轴闸都不触发 → 刷新集恒空(fail-closed,同 ADR-0600 G7 轴:
        # 评分错只排错序、刷新错会弃掉真顶级卡,不对称风险取严)。
        # 槽级动作集(design §2.8 分类,零自由参数):
        # - 零价值 = 全集门失格 ∧ 未被 user-priority 命中 → 恒可刷(弱占优:
        #   当前增益无消费方价值 0,替换样本任一环境价值 ≥ 0 且 P(>0) 显著,
        #   免费刷新 = 白弃改善期权不刷才亏);
        # - 被禁 = user-forbid 命中 → 恒可刷(优先于顶级保护,P5② 同构:
        #   被禁者永不被选,保护无对象);
        # - 顶级(经济域带 resolved ∨ 阵营 floor 命中)与其余(全集内裸分槽,
        #   含送卡档与 unresolved 经济槽——后者基数化挂账 design §2.8)→
        #   不入动作集即「保护不刷」,无需显式顶级分类(动作集 = 零价值 ∪ 被禁,
        #   补集自然承载保护面)。
        refresh_slots = tuple(
            j for j in range(3)
            if _cand_forbid[j] or (_cand_env_off[j] and not _cand_pri[j]))
    if refresh_slots:
        # 归因后缀仅观测归因,不进任何检查器白名单(C1→D4 迁移
        # 兼容口径,沿投资选卡归因串先例;裁定见 sim/checks/suspects.py 模块头)。
        best_reason = f'{best_reason}+refresh-suggest'
    return PickEvent(option_idx=best_idx, refresh=bool(refresh_slots),
                     refresh_slots=refresh_slots,
                     reason=f"{best_reason} score={best_score:.0f}")




# ===== 遭遇节点(decide_encounter;design 08)。✅ 已接:``CwScreenEncounter`` 调本函数 +
# ``read_encounter_options``(cw_node_obs,OCR 卡标题「遭遇其X」→ difficulty)。affix 分支 N/A
# (选项 UI 不显词缀,战后才显)。=====

@dataclass

class EncounterOption:
    """一个遭遇分支:难度档 + 敌人词缀 + 奖励(OCR 读,``read_encounter_options`` 阶段5)。

    difficulty:难度档 1=易/2=中/3=难(越高奖励越好但敌人越凶)。
    affixes:敌人词缀 OCR 原名(经 ``AFFIX_MECHANIC_MAP`` → 机制 tag,再 ``mechanics_fit`` 判 comp 克/利)。
    rewards:奖励(钻/装备/金币;带钻最优,详 design 08 / cw_comps MECHANIC 表)。
    """
    idx: int
    difficulty: int = 1
    affixes: list[str] = field(default_factory=list)
    rewards: list[str] = field(default_factory=list)


@dataclass

class EncounterPick:
    """decide_encounter 返回:选哪个分支 + 是否刷新避开。"""
    idx: int
    refresh: bool = False
    reason: str = ""



def _option_mechanics(option: EncounterOption, target_comp: Comp | None) -> float:
    """该分支词缀对 target_comp 的契合(``mechanics_fit`` 0..1;<0.4 克、>0.5 利 debuff=buff)。

    无 target_comp / 无词缀信号(mechanics_fit 返 None)→ 中性 0.5(纯按难度选,不触发刷新)。
    """
    if target_comp is None:
        return 0.5
    affix_map, _, _ = merged_mechanic_tables()
    mechs = {affix_map.get(a, a) for a in option.affixes}
    fit = mechanics_fit(target_comp, mechs)
    return fit if fit is not None else 0.5


def _reward_value(rewards: list[str]) -> float:
    """奖励文本 → 价值分(恒中性 0.5)。

    奖励稀有度序(棱彩>金>银)是游戏定义,但序到分的映射无推导;
    保守缺省 = 恒中性:遭遇选档不因奖励文本冒险(P3 tiebreak 项随之恒定)。
    reason 回显只会打 0.50,无任何稀有度信号,判读勿据此归因。
    """
    return 0.5



def decide_encounter(options: list[EncounterOption], gs: GameState,
                     target_comp: Comp | None, config, refresh_used: bool = False) -> EncounterPick:
    """遭遇节点选难度档 + 是否刷新(纯逻辑,design 08)。✅ 已接:``CwScreenEncounter`` 调本函数 +
    ``read_encounter_options``(cw_node_obs,OCR 卡标题「遭遇其X」→ difficulty)。affix 分支 N/A
    (选项 UI 不显词缀,战后才显)。

    决策(观测驱动 + comp 相关,debuff=buff):
    1. **未成型**(deployed 不足 / target 成型度低)→ 偏低难度(生存优先)。
    2. **词缀按 comp 判**(``mechanics_fit``):全分支都克 comp + 刷新未用 → **刷新换批**避开;
       存在不克的分支 → 选最利 comp 的。
    3. **成型 + 词缀利 comp**(debuff=buff)→ 挑高难度拿奖励(奖励权重随成型度)。
    4. 刷新已用 → 不再刷,按 1-3 选最优分支。

    config 预留(未来对策装备映射 / 偏好;当前未用)。
    """
    if not options:
        return EncounterPick(idx=0, reason="no-options")
    mechs = [_option_mechanics(o, target_comp) for o in options]
    form = (form_progress(target_comp, gs)
            if target_comp is not None else 0.5)
    formed = form >= 0.4 and deployed_count_of(gs) >= max(2, max_units_of(gs) // 2)

    # 全分支词缀都克 comp(mechanics_fit < 0.4)+ 刷新未用 → 刷新换批(避开高危)
    if not refresh_used and target_comp is not None and all(m < 0.4 for m in mechs):
        return EncounterPick(idx=options[0].idx, refresh=True,
                             reason=f"全分支词缀克 comp(mech_max={max(mechs):.2f}),刷新换批")

    # 评分:词缀契合(利 comp 加分)+ 难度档定价(P9 接难度账本:场合三态替代固定 ±0.3)
    def _score(o: EncounterOption, m: float) -> float:
        from sr_od.application.currency_war.kernel.cw_survey19_hooks import (
            encounter_tier_score,
        )
        s = m
        # 0..1 clamp(难度 1→0、3→1;「其四」=4 越界 1.5 → 钳回,ADR-0130)
        diff_norm = min(max((o.difficulty - 1) / 2.0, 0.0), 1.0)
        # 奖励价值(用户指路;OCR 奖励带已读)——与难度联动:
        # 只有「敢难」时奖励差才兑现,不敢难时好奖励也白搭(不独立加分)
        rv = _reward_value(o.rewards)
        if plane_of(gs) == 3:
            # ADR-0130:P3 永避高难遭遇(一次 -70 血无回报,成型也不赌)。
            s -= 0.5 * diff_norm
            s -= 0.1 * (1.0 - rv)   # P3 不为奖励冒险,仅轻微 tiebreak
        else:
            # P9(用户口径「阵容足够强才敢难」):压 −2 档价值作风险计——
            # 碾压(form≥0.9,gap≤−36,bell→0)敢难白拿;其余保守保血。
            gap = (0.4 - form) * 60
            press_v = encounter_tier_score(d_now=100.0, tier_delta=-2,
                                           gap=gap, plane=plane_of(gs))
            dare = press_v < 0.05
            s += (0.3 + 0.2 * (rv - 0.5)) * diff_norm if dare else -0.3 * diff_norm
        return s

    scored = sorted(zip(options, mechs, strict=True), key=lambda om: _score(om[0], om[1]), reverse=True)
    best_o, best_m = scored[0]
    return EncounterPick(idx=best_o.idx, refresh=False,
                          reason=(f"mech={best_m:.2f} formed={formed} diff={best_o.difficulty} "
                                  f"reward={_reward_value(best_o.rewards):.2f}"))



# ===== 补给节点(decide_supply,design 07/08)。✅ 已接 run_supply_node + read_supply_options =====

@dataclass

class SupplyOption:
    """一个补给选项:角色 + 装备 + 是否带钻(OCR/视觉读,``read_supply_options`` 阶段5)。

    has_diamond:带红/蓝钻(视觉判定;钻 = 拿到基本赢,碾压一切)。
    equip:装备名(OCR;``key_equips`` 契合 + 通用价值排序用)。
    """
    idx: int
    char: str = ""
    equip: str = ""
    has_diamond: bool = False


@dataclass

class SupplyPick:
    """decide_supply 返回:选哪个 + 是否刷新找钻。"""
    idx: int
    refresh: bool = False
    reason: str = ""



def _equip_value(equip: str) -> int:
    """装备通用价值(0=未知/无;共享机器单一源,表本体已迁
    ``cw_equip_value.EQUIP_GENERIC_VALUE``,值零变化)。"""
    return equip_generic_value(equip)



def decide_supply(options: list[SupplyOption], gs: GameState,
                  target_comp: Comp | None, config, refresh_used: bool = False) -> SupplyPick:
    """补给节点选装备 + 是否刷新(纯逻辑,design 07/08)。✅ 已接:``run_supply_node`` 调本函数 +
    ``read_supply_options``(cw_node_obs,OCR 每列角色+装备)。

    决策(comp 相关 + 钻优先):
    1. **带钻**(红/蓝)→ 选它(拿到基本赢,碾压)。
    2. **全无钻 + 刷新未用** → **刷新找钻**(钻价值远超装备)。
    3. **刷新已用 / 有钻** → 按 ``target_comp.key_equips`` 契合(命脉级,+10 碾压)+ 通用装备价值
       (鞋>电池>花)选。
    """
    if not options:
        return SupplyPick(idx=0, reason="no-options")
    # 1) 带钻 → 选第一个带钻的(基本赢)
    diamond = [o for o in options if o.has_diamond]
    if diamond:
        return SupplyPick(idx=diamond[0].idx, reason="带钻(基本赢)")
    # 2) 全无钻 + 刷新未用 → 刷新找钻
    if not refresh_used:
        return SupplyPick(idx=options[0].idx, refresh=True, reason="无钻,刷新找钻")
    # 3) 刷新已用 → key_equips 契合(命脉,+10)+ 通用装备价值
    key_equips = set(target_comp.key_equips) if target_comp is not None else set()

    def _score(o: SupplyOption) -> int:
        s = _equip_value(o.equip)
        if o.equip in key_equips:
            s += 10   # 契合 target_comp 命脉装备(碾压通用价值)
        return s

    scored = sorted(options, key=_score, reverse=True)
    best = scored[0]
    return SupplyPick(idx=best.idx, reason=f"equip={best.equip or '?'} key_fit={best.equip in key_equips}")


# ===== 巨星节点(decide_megastar;✅ 已派发 run_megastar_node,按 target.core_chars 选;⚠️ 候选 char_id OCR 限时 fallback idx0)=====

@dataclass

class MegastarOption:
    """一个巨星候选(OCR/SIFT 读角色名,``read_megastar`` 阶段5;/§11.3.4⑥)。

    char_id:候选角色名(空 = OCR 未就绪,匹配恒失败 → 默认 idx=0 = 今天盲点左候选)。
    """
    idx: int
    char_id: str = ""


@dataclass

class MegastarPick:
    """decide_megastar 返回:选第几个候选 + 原因。

    enhance_char_id:巨星 overlay step2「强化角色」意向(我方角色名);
    恒 None(强化角色决策意向已随 megastar_enhance_enabled 开关族删除
    ——旧方案清退批,清查报告 OLD_MIX_AUDIT §1.3;字段保留兼容既有
    遥测/执行面读取)。
    """
    idx: int
    reason: str = ""
    enhance_char_id: str | None = None


# ===== 选择伙伴节点(decide_partner;✅ 已派发 cw_screen_partner;⚠️ 候选只立绘 char_id=label→多 idx0,真接需 SIFT 立绘)=====

@dataclass

class PartnerOption:
    """一个伙伴候选(OCR/SIFT 读角色名,``read_partner`` 阶段5;/§11.3.4⑦)。

    char_id:候选角色名(空 = OCR 未就绪 → 默认 idx=0 = 今天盲点 stage 立绘)。
    """
    idx: int
    char_id: str = ""


@dataclass

class PartnerPick:
    """decide_partner 返回:选第几个候选 + 原因。"""
    idx: int
    reason: str = ""


# ===== 银狼策划事件(decide_planner;用户定调「接入策略模块,由策略模块定」;
#      机制见 docs/game/gameplay/currency_war.md 银狼策划事件节)=====

@dataclass
class PlannerOption:
    """一个策划选项(OCR 卡文字)。

    text:卡描述全文(如「提升费用至4费,变为1星银狼LV.999」/「使后续节点【弱化】…」/
    装备名+效果)。「提升费用」字样判升费卡由本模块打分表达,handler 不写死。
    """
    idx: int
    text: str = ''


@dataclass
class PlannerPick:
    """decide_planner 返回:选第几张卡 + 原因。"""
    idx: int
    reason: str = ''


def decide_planner(options: list[PlannerOption], gs: GameState,
                   target_comp: Comp | None = None) -> PlannerPick:
    """银狼「我来当策划」二选一策略。

    用户定调:**必接策略模块由它定**(handler 不写死默认),虽结论
    几乎总是升费——打分走通用原则,让「何时升费不是最优」可被策略表达。
    ADR-0524 定形(16 号稿 §1.7):三层定序结构 = 升费档 > 弱化档 > 装备档,
    各层方向均有出处(升费优先 = 用户定调 + 银狼策划机制原文;弱化次之 =
    全场即时战力;装备域内 key_equip 命中优先 = comp 知识);下列数值全部
    是档位实现常数,只承载层间/层内定序,非基准基数:

    - **升费档**(「提升费用」):银狼成长滚动投资前提(升费→新费档刷商店→3星5费
      滚强度)。档内修饰:target 含银狼线(狼尊欢愉/量子系)⇒ **升档**(100+30,
      升费兑现更高);银狼确定不在场(board 有信息但无银狼)⇒ **降档**(100−60,
      落到弱化档之下=投资无处兑现);信息缺失不降权(在场判定保守)。
    - **弱化档**(「弱化」/「降低敌人」):全场即时战力(55;原低血 +20 钩子
      已退役,hp 可标不可定价)。
    - **装备档**(其余):_equip_value 回落(装备注册表);target key_equip 命中
      ⇒ **装备域内命中优先键**(+15,只在装备档内排前,不跨域压弱化档)。
    - 未识别文字:0 分(idx 顺序兜底)。
    """
    _tgt_chars = set(target_comp.core_chars) if target_comp is not None else set()
    _tgt_factions = set(target_comp.factions) if target_comp is not None else set()
    has_wolf_line = bool(_tgt_chars & {'银狼LV.999'}) or bool(
        _tgt_factions & {'欢愉', '量子同频'})
    # 在场判定:bench+deployed 的 char_id(信息缺失=空列表→不降权,保守)
    _pool = [d for d in deployed_slots_of(gs) if d is not None] + \
        [b for b in bench_slots_of(gs) if b is not None]
    _owned = {getattr(bc, 'char_id', '') for bc in _pool
              if getattr(bc, 'char_id', '')}
    wolf_owned = ('银狼LV.999' in _owned) if _owned else True

    best_idx, best_score, best_reason = 0, -1.0, ''
    for opt in options:
        score, reason = 0.0, ''
        t = opt.text
        if '提升费用' in t:
            score, reason = 100.0, '升费(滚动投资前提)'
            if has_wolf_line:
                score += 30.0
                reason += '+银狼线'
            elif not wolf_owned:
                score -= 60.0
                reason += '-银狼不在场无处兑现'
        elif '弱化' in t or '降低敌人' in t:
            # 低血加分(+20「+低血保命」)已退役:hp 可标
            # 不可定价,经验加分无推导(与其余经验加分项同型)。
            score, reason = 55.0, '全场弱化(即时战力)'
        else:
            score = float(_equip_value(t)) if t else 0.0
            reason = f'装备({t[:8]})' if t else '未识别'
            if t and target_comp is not None:
                _ke = getattr(target_comp, 'key_equips', None) or []
                if any(e in t for e in _ke):
                    score += 15.0
                    reason += '+key_equip'
        if score > best_score:
            best_idx, best_score, best_reason = opt.idx, score, reason
    return PlannerPick(idx=best_idx, reason=best_reason or '全部未识别,兜底左卡')


# ===== 事件线 pick 族运行时元组(统一动作工厂批4;注册完备锁遍历单一源
# ===== 之一,先例 = cw_vocab.CW_ACTION_TYPES 白名单元组形态)=====

#: 事件线意图词表全类(decide_* 决策返回载体;overlay act 段经注册表
#: 工厂 ``action_op_for`` 分派,design.md §2.5)。退役 = 删类(R1):
#: 元组中不存在即天然不可复活,无退役行无墓碑;新 pick 类型入词表 =
#: 先改契约再落码(词表纪律,统一观察架构 §6.1),漏登记 = 注册完备锁红。
#: (终态契约 §2.2 正名:本表 = 事件线决策返回载体;动作子类型收敛单表
#:  = cw_vocab.PICK_ACTION_TYPES,两者勿混。)
EVENT_PICK_TYPES: tuple = (
    EncounterPick, SupplyPick, MegastarPick, PartnerPick, PlannerPick,
)

#: pick 族类型联合(注册表动作参数注解用;运行时零消费)。
EventPick = EncounterPick | SupplyPick | MegastarPick | PartnerPick | PlannerPick
