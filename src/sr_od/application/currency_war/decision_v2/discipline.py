"""决策框架 v2 纪律族(载体批 W35;自旧 line_strategy 移植+语义重接,
ADR-0336 后 line_strategy 已删,本包为唯一纪律族)。

**单一源**:`.debug/temp/currency_war/cw_dev/deep_read/strategy_v4.md` 点4(掉血
报警三臂/处置梯度时限)/点7(血线分级动作侧/位面末 ALL IN 限定)/点12(保血通道/
奖励关三态护栏)+ 裁决终版「第三选项」(纪律族移植,locked_line 派生改意向分层
输入——本模块**不 import** 线库/桥池,方向输入一律是
``cw_intention`` 的意向态与 ``session.v3_*`` 视图)。

移植清单(v1 → v2 语义重接对照,详 W35_报告):
- 应急(_emergency/_emergency_actions)→ ``emergency_hp`` 绝对档+``rebirth_floor``
  保留重生基数([18]):v1 同名常量移植,触发与地板语义不变;
- boss_breaker(_boss_breaker_actions)→ 破息窗地板(10/连胜 EV 5)+ P1 r5-r8
  遭遇预备窗口:围栏从 RECIPE_FACTIONS 换**意向线 form_tiers∪sub_tiers∩板面**
  (体系卡/意向线本体论);
- carry_gate(_carry_bench_gate)→ bench 满+意向核心在店+金足 → 降保护集卖最弱
  件买核心:carry 从 ``line_of(locked_line).carry`` 换 ``intention_core``(
  COMP_LIBRARY v2 的 plaza_carry/core_chars[0]);保护集从桥池名单换
  hoard 目标集;
- catchup(_catchup_actions/E5/E6)→ **已随 W126/ADR-0349 退场**(用户
  2026-08-25 裁决 F6/Q4:人口落后=阵容没上满的表现——通道 2 人口位
  ([33])+通道 4 概率等级窗([3])+EV 总账涌现承接;兜底局由 form_score
  按上场计算承接「人口别落后」的观察);
- 同轮互斥/种子年龄豁免(r408/ADR-0289 §5)→ 纯谓词移植(不依赖线库)。

行为纪律(strategy_v4 逐条;W51 语义修复批对齐 R1 审查 leader 裁决,
报警语义 why 详 ADR-0313,carry_gate 弱序/变现通道详 ADR-0314):
- **hp 报警语义**(点4/[W10 D8-5]):掉血三臂判据是**报警不是触发**——
  报警激活处置梯度(①自然凑羁绊上界 1 个战斗节点 → ②弃息 D 保血),
  **永不单独触发 ALL IN**;位面末最后一战的 ALL IN 由
  ``plane_last_battle`` 授权([18]——报警态下位面末同样开通,
  报警只是不作为 ALL IN 的触发条件);
- **位面末 ALL IN 限定**(点7/[18]):「花光提质量」仅位面末最后一战
  (boss 节点+轮=位面节点数)——``allin_window`` 是唯一把地板清零的路径;
- **保血通道**(点12):遭遇前战力不足+战斗语义掉血趋势 → 弃息 D 保血
  (放行 refresh 搜牌),三态护栏(贴息态/守息态)由层4 interest_rule 承载。

常量值镜像旧 line_strategy 同名初值(地板族);注册表化后独立演进
(旧两臂 A/B 语义随 ADR-0336 结束)。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_economy import streak_gold
from sr_od.application.currency_war.cw_intention import (
    IntentionState,
    intention_core,
)
from sr_od.application.currency_war.cw_plane_table import nodes_of_plane
from sr_od.application.currency_war.cw_state import (
    BENCH_CAPACITY,
    BuyCard,
    GameState,
    SellBench,
    bench_occupied,
    iter_occupied_deployed,
    sell_refund,
)
from sr_od.application.currency_war.cw_strategy import StrategySession

# ===== 体系卡引擎件(铁三角+希儿;C2 单一源 import 不复制)=====
# W47 统一化:engine_char_names 函数本体上移至 cw_system_cards(注册表旁),
# 本模块 import 复用——消费点(candidates/engine_seed_wants/carry 保护集)零变化。
from sr_od.application.currency_war.cw_system_cards import engine_char_names

# hp 决策可信位单一源(ADR-0428 收口;posture_release 对本模块的引用
# 全在函数体内延迟 import,模块级无环)。
from sr_od.application.currency_war.decision_v2.posture_release import (
    hp_decision_trusted,
)
from sr_od.application.currency_war.kernel.cw_discipline_rules import (
    _sell_floor_counts,
    _sell_floor_eval,
    seed_age_blocked,
    star_weighted_copies,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)

# ===== 纯谓词族(v1 移植;不依赖线库/桥池,ADR-0336 后无旧件) =====




def in_round_sold(name: str, state: GameState,
                  session: StrategySession) -> bool:
    """r408(ADR-0267 对称臂):该卡名本轮是否刚被卖出(买通道回读)。"""
    if not name:
        return False
    return (getattr(session, 'v2_round_key', None)
            == (state.plane, state.round_num)
            and name in (getattr(session, 'v2_round_sold', None) or ()))


def round_sell_blocked(bc, state: GameState,
                       session: StrategySession) -> bool:
    """r408(ADR-0267,F1 振荡):同轮已买的卡名禁卖;3合1 让位豁免(≥3 份)。"""
    if not getattr(bc, 'char_id', ''):
        return False
    if getattr(session, 'v2_round_key', None) \
            != (state.plane, state.round_num):
        return False
    if bc.char_id not in (getattr(session, 'v2_round_bought', None) or ()):
        return False
    return star_weighted_copies(bc.char_id, state) < 3


def sole_engine_sell_blocked(bc, state: GameState,
                             registry: DecisionV2Registry | None = None,
                             ) -> bool:
    """W184/ADR-0373 卖侧唯一体系引擎守卫(谓词;不改板面只辖卖出)。

    判据:该件是四过渡体系成员——三羁绊(TRANSITION_TRAITS:仙舟/
    列车同行/持续伤害——全羁绊 factions∪flows 口径,「持续伤害」是
    流派非阵营)**或希儿系贡献件**(W192/ADR-0375 辖域补全,**核心
    条件辖**:希儿本人唯一种子不卖;放大器件仅当希儿在手时按放大
    阵营成型门槛 2 辖)——且卖出会使所属体系「清空唯一 owned 引擎
    件」或「在手数跌破成型门槛」时,不可卖。冗余件照旧可卖——体系
    有余量时的清仓不受辖。

    语义依据:[31] top4 引擎羁绊是胜率保证、引擎件是方向件非可回收
    填充件;[22]① 买了再卖不损金 → 留住最后一件的成本=1 个 bench
    槽,弃掉的代价=该体系的恢复种子清零。修 W181 §3 谱系:演进换线
    把旧体系件下场到 bench 后,off_target 把它当死库存卖出(卖出的
    件均非 engine_char_names 名单件,方向切换后即失去目标身份)→
    体系引擎永不回场(S2 evict unrecovered)。W192 前辖域=TT 派生
    集显式排除 seele(cw_deploy_logic deploy 排序语义被守卫借用),
    希儿系贡献件可被任意卖出=清空 tier=1 体系唯一件(W190 洞一)。

    flag=registry.sell_sole_engine_guard_enabled(总开关,关=逐位回
    W179 后行为)+ registry.guard_seele_scope_enabled(W192 辖域
    补全开关,关=逐位回 W188 后行为=三羁绊辖域)。
    """
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    if not reg.sell_sole_engine_guard_enabled:
        return False
    name = getattr(bc, 'char_id', '') or ''
    ch = CHARACTERS.get(name)
    if ch is None:
        return False    # 未识别/注册表外件:既有守卫已挡,不重复辖
    # 判据单一源:计数底座 + 单件评估(W197/ADR-0380 起 batch 口径同源)
    return _sell_floor_eval(name, set(ch.factions) | set(ch.flows),
                            _sell_floor_counts(state, reg))


def form_break_sell_blocked(bc, state: GameState,
                            session: StrategySession,
                            registry: DecisionV2Registry | None = None,
                            ) -> bool:
    """成型后过渡件不拆守卫(方向二;设计单一源=
    ``.debug/temp/currency_war/w415_form_design/DESIGN.md`` §2,决策
    why=ADR-0433;开臂判据挂账见 registry.form_break_sell_blocked_enabled
    注释)。

    [13] 停手线的卖/下场侧对称口径——与 ADR-0343 成型停手(买侧)、
    ADR-0363/0373(演进/卖侧引擎守卫)是同一纪律族在「成型态」下的
    缺口径,非新守卫族。辖域=卖/下场候选的 SellBench 通道(挂点全在
    卖候选生成/采纳路径),覆盖 ADR-0373 的两型缝隙:配方档 5→4(冗余
    份恰是档位构成,0373「owned>tier 冗余件照旧」放行的盲区)与上场
    人数 5→4(经 SellBench 下场无回场窗)。remediation.SwapDeploy 换
    下场臂不辖:其换位可改变羁绊构成使 form_ok 翻假而不被拦(当前靠
    「换位不减员、上场人数缝隙不触发」缓解,配方档 5→4 缝隙经它仍可
    达);SwapDeploy 接入本守卫须补挂点,开臂前裁决。

    判据(缺一不可):
    1. 开关 ``registry.form_break_sell_blocked_enabled``(默认关);
    2. ``filters.formed_stop_active``(单一源,P1 ∧ comp 派生辖轮 ∧
       form_ok ∧ 承接口 gap=0 全部继承——承接口未达时 formed_stop 为
       假,本守卫自动不辖,「继续投资」语义天然优先,ADR-0400);
    3. 事务净效果:把 bc 从 bench/deployed 槽位移除后的状态(阵营计数
       按 ``cw_state`` 重算底座重算,与 sim 卖出执行同口径)使
       ``phase.form_ok`` 翻假(decision_v2.phase 单一源,禁第二把成型
       尺;ADR-0426 死分支教训:下游消费必须挂活判定单一源)。

    例外:卖了不破 form_ok 的件(纯冗余、真垫层)照旧可卖——补偿卖序
    的腾位/换金通道不堵死([22] 净0 件最先卖的既有弱序保留)。
    """
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    if not reg.form_break_sell_blocked_enabled:
        return False
    from sr_od.application.currency_war.decision_v2.filters import (
        formed_stop_active,
    )
    if not formed_stop_active(state, session, reg):
        return False
    from sr_od.application.currency_war.cw_state import _recount_board
    from sr_od.application.currency_war.decision_v2.phase import form_ok
    s2 = state.copy()
    s2.bench = [None if b is bc else b for b in (state.bench or [])]
    s2.deployed = [None if d is bc else d for d in (state.deployed or [])]
    s2.board = _recount_board(s2.deployed)
    return not form_ok(s2, session, reg)












def engine_seed_wants(card, state: GameState,
                      session: StrategySession | None = None) -> bool:
    """体系方向件放行门(点1/点3;v1 ADR-0260 门的语义重接):

    两路放行(OR):
    ① **C2 引擎件名单**(铁三角+希儿——见即买,点3 本体论名单);
    ② 过渡体系阵营件(仙舟/列车同行/持续伤害)未持有(v1 ADR-0260
       「引擎乐高第一块砖」门——体系方向件=对当前体系羁绊贡献>0 的件,
       定义节 class1 口径,窄化到引擎名单会漏 21% 买入面,ADR-0299 锁)。
    共同门:P1 过渡期;未持有同名;bench 满员不触发(r408 容量门);
    同轮已卖不回买。金够/不破息档由层4 gold_floor 辖(本门不加价)。
    """
    if not card.name or state.plane != 1:
        return False
    if bench_occupied(state.bench or []) >= BENCH_CAPACITY:
        return False   # r408:满员不种(ADR-0267 F1 容量门;ADR-0316 占用数)
    if session is not None and in_round_sold(card.name, state, session):
        return False
    if has_same_name_copy(card, state):
        return False
    if card.name in engine_char_names():
        return True    # ① C2 引擎件名单
    # ② 过渡体系阵营(v1 门语义)
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    from sr_od.application.currency_war.cw_deploy_logic import (
        TRANSITION_TRAITS,
    )
    ch = CHARACTERS.get(card.name)
    card_bonds = (set(ch.factions) | set(ch.flows)) if ch \
        else {card.faction}
    return bool(card_bonds & {f for f, _t in TRANSITION_TRAITS})


def has_same_name_copy(card, state: GameState) -> bool:
    """r383b:已拥有同名卡(bench/deployed 任一)→ 副本素材真。"""
    if not card.name:
        return False
    if any(b is not None and b.char_id == card.name
           for b in (state.bench or [])):
        return True
    return any(getattr(d, 'char_id', '') == card.name
               for d in (state.deployed or []))


def _char_bonds(name: str, faction: str = '') -> set[str]:
    ch = CHARACTERS.get(name)
    if ch is not None:
        return set(ch.factions) | set(ch.flows)
    return {faction} if faction and faction != '?' else set()


def _direction_factions(session: StrategySession) -> set[str] | None:
    """方向期阵营门(v1 r350 的语义重接):意向锁定 = 意向线主/副档羁绊;

    无方向(未锁/弱意向/兜底)= 过渡体系阵营(仙舟/列车同行/持续伤害)。
    None = 无方向信息(旧载体垫片已随 ADR-0336 删除——生产恒走意向源)。
    """
    ist = getattr(session, 'v3_intention', None)
    if ist is not None and isinstance(ist, IntentionState) \
            and ist.phase == 'locked' and ist.locked_comp:
        from sr_od.application.currency_war.cw_comps import get_comp
        comp = get_comp(ist.locked_comp)
        if comp is not None:
            allow = set(comp.form_tiers) | set(comp.sub_tiers)
            # W166/ADR-0367:①锁局过渡对副方向放行(locked_faction_scope
            # 同式扩位)——pair 通道的方向门不拦对体系件(二级囤货,
            # [22]④;comp 档位键仍为主方向)。transition_pair 非空 ⟺
            # P1 ①锁局(IntentionState 契约),无需 state 判位面。
            tp = getattr(ist, 'transition_pair', ()) or ()
            if tp:
                for sys in tp:
                    if sys == '希儿系':
                        allow |= {'量子同频', '贝洛伯格'}
                    else:
                        allow.add(sys)
            return allow
    from sr_od.application.currency_war.cw_deploy_logic import (
        TRANSITION_TRAITS,
    )
    return {f for f, _t in TRANSITION_TRAITS}


def pair_wants(card, state: GameState,
               session: StrategySession | None = None) -> bool:
    """凑对搭档件放行门(v1 _pair_wants 语义重接,方向输入=意向分层):

    - 方向期阵营门:意向线主/副档羁绊(锁定)/过渡体系阵营(未锁);
    - 冷启动(无已有阵营 或 P1 r≤2):只放行引擎件∪同名副本∪方向阵营件
      (v1 r368/r371b/r383b——买进来的每一张都是方向件);
    - A5 spread 门:已有阵营 ≥3 不开新阵营;
    - 常态:同阵营凑对;r408 同轮已卖不回买。
    """
    if not card.name or not card.faction or card.faction == '?':
        return False
    if session is not None and in_round_sold(card.name, state, session):
        return False
    # 方向期阵营门(仅**有方向**时辖——v1 r350 同式:无方向不过滤):
    # 意向锁定=意向线主/副档羁绊(旧载体 locked_line 垫片已删,
    # ADR-0336——生产恒走意向源)。
    ist = getattr(session, 'v3_intention', None)
    has_direction = (
        ist is not None and isinstance(ist, IntentionState)
        and ist.phase == 'locked' and ist.locked_comp)
    allow: set[str] | None = None
    if has_direction:
        allow = _direction_factions(session)
        if allow is not None \
                and not (_char_bonds(card.name, card.faction) & allow):
            return False
    owned_factions = set(state.board.keys())
    for b in (state.bench or []):
        if b is not None and b.faction and b.faction != '?':
            owned_factions.add(b.faction)
    if not owned_factions or (state.plane == 1 and state.round_num <= 2):
        # 冷启动:引擎件 ∪ 同名副本 ∪ 方向阵营件(classify_buy 单一源)
        if has_same_name_copy(card, state):
            return True
        if card.name in engine_char_names():
            return True
        if allow is not None and card.faction in allow:
            return True
        from sr_od.application.currency_war.cw_line_defs import classify_buy
        return classify_buy(card, state) in ('bridge_seed', 'engine')
    if card.faction not in owned_factions and len(owned_factions) >= 3:
        return False    # A5:阵营上限
    return card.faction in owned_factions


def p1_early_gate_open(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> frozenset[str] | None:
    """P1 早期新件买入门的窗判据(W179/ADR-0372;返回门内可买的
    未持有 distinct 对成员名集,窗关返回 None)。

    窗(轮级条件,逐笔的息档/单轮上限由消费点 arbiter.gold_floor 辖):

    - P1 ∧ ``registry.p1_early_gate_enabled``;
    - 派生配方对非空(``cw_intention.p1_early_pair``——锁定帧用意向
      字段,**未锁形态期同样派生**,对现行两字段仅锁后非空的语义扩展);
    - 未持有 distinct 对成员数 ≥ ``p1_early_min_missing``(缺件密度,
      [22]③ 弃购代价=再遇窗口的账面化);
    - bench 余槽 ≥ 1([22]② 唯一稀缺=bench 槽)。

    散买边界三条件(W175 §4,任一失守=越界)在此与消费点共同成立:
    target ∈ 配方对成员(本函数返回集)/ 只搭自然刷新便车(不授权
    任何刷新金——买门与 W170 刷门管辖动作不交集)/ distinct 未持有
    (返回集定义);同名重复不辖(3合1 素材语境交既有 copy 豁免面)。
    """
    if state.plane != 1 or not registry.p1_early_gate_enabled:
        return None
    from sr_od.application.currency_war.cw_intention import (
        _pair_members,
        p1_early_pair,
    )
    ist = getattr(session, 'v3_intention', None)
    pair = p1_early_pair(state, ist if isinstance(ist, IntentionState)
                         else None)
    if not pair:
        return None
    owned = ({getattr(d, 'char_id', '') for d in state.deployed or ()}
             | {b.char_id for b in (state.bench or []) if b is not None})
    unheld = frozenset(_pair_members(pair) - owned)
    if len(unheld) < registry.p1_early_min_missing:
        return None
    if bench_occupied(state.bench or []) >= registry.bench_capacity:
        return None
    return unheld


# ===== W300 press 通道:目标外同名副本压库(单一源;design v3 V-A2/V-B5)=====


def observed_probs(state: GameState) -> dict[int, float] | None:
    """当前概率语境真值(V-B5.3 轮岗盲区:读屏概率条披露域
    ``state.refresh_probs``,轮岗轮单档翻倍改变「当前要压的档」;
    None=取不到,调用方退 REFRESH_PROB 基线)。"""
    probs = getattr(state, 'refresh_probs', None)
    return dict(probs) if probs else None


def press_band_derive(level: int, probs: dict[int, float] | None,
                      registry: DecisionV2Registry) -> frozenset[int]:
    """REFRESH_PROB 推导带(P5 概率等级定理:该级概率大→找该带的牌):
    低费前缀累计概率首次 ≥ press_band_cum_threshold 即截断([30] 成本带
    聚焦方向=最低费优先)。输入表优先 observed(轮岗真值,V-B5.3),
    取不到退基线行;空行(该等级无概率数据)→ 空集。"""
    row = probs or {}
    if not row:
        from sr_od.application.currency_war.cw_shop_odds import REFRESH_PROB
        row = REFRESH_PROB.get(level) or {}
    acc = 0.0
    out: list[int] = []
    for c in sorted(row):
        if row[c] <= 0:
            continue
        acc += row[c]
        out.append(c)
        if acc >= registry.press_band_cum_threshold:
            break
    return frozenset(out)


def press_band(level: int, probs: dict[int, float] | None = None,
               registry: DecisionV2Registry | None = None,
               ) -> frozenset[int]:
    """press 费用带(V-B5.2 权威序裁决):推导带 ∪ (P1 开域 {1,2})。

    - [30] 口述「P1 过渡期=1-2 费带」为最高权威;REFRESH_PROB 推导是
      下位证据——开域(lv ≤ press_channel_max_level)内 band 强制并入
      {1,2},推导孤值被口述锚覆盖(lv4 推导 {1} 不再出现);
    - 开域判定按 level(plane==1 的位面门在 press_channel_open 与各
      消费点辖——本函数无 state 入参,纯函数可测);
    - lv≥7(中后段)纯推导(lv7={1,2,3}),彼时带自洽闸已关通道
      (press_channel_open),0.50 阈值在此段是守卫参数非行为旋钮。
    """
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    band = set(press_band_derive(level, probs, reg))
    if level <= reg.press_channel_max_level:
        band |= {1, 2}
    return frozenset(band)


def press_channel_max_band(registry: DecisionV2Registry | None = None,
                           ) -> frozenset[int]:
    """带自洽闸参照系 = press_band(press_channel_max_level),当前推导
    下恒 {1,2}(V-A2 停机推演;检查器成本带上限 import 本函数,消灭
    与 _SEG_TRANSITION_COST_MAX 的两处漂移)。"""
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    return press_band(reg.press_channel_max_level, None, reg)


def press_channel_open(state: GameState,
                       registry: DecisionV2Registry | None = None,
                       ) -> bool:
    """press 通道停机条件(V-A2 继承,V-B5 修订覆盖规则;任一失守=
    整通道关闭,杜绝按错误档位违规购买):
    ① plane==1(位面 2+ 概率语境整体脱离过渡带);
    ② 开域 lv ≤ press_channel_max_level;
    ③ 带自洽闸:press_band(level) ⊆ press_band(max_level)(={1,2})——
       lv≥7 推导带扩到 {1,2,3} 破闸;轮岗轮 observed 表推出 3 费进带
       同样破闸(保守关停)。
    停机是 REFRESH_PROB 的派生输出而非拍脑袋常数,max_level 仅作冗余
    护栏与①互为双保险。"""
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    if getattr(state, 'plane', 1) != 1:
        return False
    if state.level > reg.press_channel_max_level:
        return False
    return press_band(state.level, observed_probs(state), reg) \
        <= press_channel_max_band(reg)


def copy_swap_useless(card, state: GameState,
                      session: StrategySession) -> bool:
    """r410(ADR-0267 同族):同名跨副本无效换卡守卫(镜像 deploy 侧保留
    判据;target_comp 在新载体=COMP_LIBRARY v2 真 Comp,属性面兼容)。"""
    if not card.name:
        return False
    dep_copies = [d for d in (state.deployed or [])
                  if getattr(d, 'char_id', '') == card.name]
    if not dep_copies:
        return False
    _tc = getattr(session, 'target_comp', None)
    t_fac = set(getattr(_tc, 'factions', ()) or ()) if _tc else set()
    t_core = set(getattr(_tc, 'core_chars', ()) or ()) if _tc else set()
    for d in dep_copies:
        if d.char_id in t_core:
            return False   # core 显式保留 → 买副本合法
        if _char_bonds(d.char_id, d.faction) & t_fac:
            return False   # target 阵营单位保留 → 凑对合法
    return True


# ===== 掉血报警三臂(点4〔修A2 勿动〕;战斗语义,非战斗节点不计入不重置)=====

#: [19]② 血量安全边际低线:hp < 此值 = 报警档([W10 D8-5] hp<40 语义
#: 同源)——掉血报警分支里血边际已低时处置梯度直接生效(跳过①自然窗)
BLOOD_MARGIN_LOW_HP: int = 40
#: 处置梯度①「自然凑羁绊」的自然补强窗上界(战斗节点数;strategy_v4
#: 点4 S4「上界 1 轮」——1 个战斗节点自然补强未达标 → 直入②弃息 D)
BLOOD_GRADIENT_NATURAL_BATTLES: int = 1

#: 25/40 两档并存口径(两线不是二选一):
#: - **25 = 应急清仓线**(``registry.emergency_hp``):hp≤25 触发应急
#:   覆盖态(rebirth 地板 20,层2 应急过滤,危机囤金态)——低于此线
#:   已不是「报警」而是「应急」,处置=清仓止损;
#: - **40 = 报警降档线**(``BLOOD_MARGIN_LOW_HP``):hp<40 使掉血报警
#:   的处置梯度跳过①自然补强窗直入②弃息 D 保血(war+硬节点放行
#:   refresh)——报警语义([18] hp 低是运营质量报警),不触发 ALL IN。
#: 两线并存:报警(40 线)是处置梯度切换的加速条件,应急(25 线)是
#: 覆盖态触发;补偿机制(ADR-0326)只消费资源门槛事件,两线都只作
#: 辖域授权条件,不是补偿触发器。


@dataclass
class BloodAlarmTracker:
    """掉血三臂判据的跨步记忆(挂 session.v3_alarm;重启丢 session 保守重置)。

    - ``recent_losses``:(全局节点号, 战斗净掉血)滚动窗——窗口单位=
      **连续战斗节点**(W51 语义修复:战斗节点计数器,非日历轮;点4
      「3 轮内」按战斗语义读作「最近 3 个战斗节点」);②最近 3 个
      战斗节点累计 ≥20(急性)/③最近 5 个战斗节点累计 ≥30(慢性漂移);
      **跨位面重置**(慢性臂横跨整个位面的按轮漂移根修);
    - ``consec_battle_fails``:①连续 2 场战斗失败;
    - ``alarm_battles``:处置梯度计时——报警激活期间累计喂入的战斗
      节点数(=1 → ①自然补强窗内;>1 → 窗耗尽未达标;报警解除清零);
    - 非战斗节点:不入窗、不清臂(点4 冻结语义)。
    """

    recent_losses: deque = field(default_factory=lambda: deque(maxlen=5))
    consec_battle_fails: int = 0
    alarm_battles: int = 0
    plane: int | None = None

    _BATTLE_NODES: frozenset[str] = frozenset(
        {'battle', '普通战斗', 'boss', '精英', '遭遇'})

    def record(self, node_type: str, hp_before: int, hp_after: int,
               t: int, plane: int | None = None) -> None:
        """on_round_end 喂入(结算真值;hp_after 为空帧跳过)。

        ``plane`` 传入时做跨位面重置判定(位面变更 → 三臂全清,
        不带旧位面的掉血趋势进新位面)。
        """
        if plane is not None and plane != self.plane:
            self.plane = plane
            self.recent_losses.clear()
            self.consec_battle_fails = 0
            self.alarm_battles = 0
        if node_type not in self._BATTLE_NODES:
            return   # 非战斗节点不计入也不重置任何一臂
        loss = max(0, hp_before - hp_after)
        self.recent_losses.append((t, loss))
        # ①连续失败代理:单场净掉血 ≥10 = 该场伤害达到条件败局期望量级,
        # 记为结构性打输。阈值依据=math_proofs P15 条件败局伤害
        # L_c(rung)=11.32−0.37·rung(registry.vd_p1_loss_* 单一源):
        # rung 全域 0-8 的代表值——中点 rung4=9.84、代表帧 rung2=10.58,
        # 取整 10。胜利恒 +2(口述 [27],user_playstyle.md)永不入档;
        # 敌血近清空的小伤害败局(P 项小,同 [27])视为波动不计数。
        if loss >= 10:
            self.consec_battle_fails += 1
        else:
            self.consec_battle_fails = 0
        # 处置梯度①计时(S4 上界 1 轮):报警激活期间累计的战斗节点数
        if self.alarm_active():
            self.alarm_battles += 1
        else:
            self.alarm_battles = 0

    def alarm_active(self) -> bool:
        """三臂并集:①连续 2 场战斗失败;②最近 3 个战斗节点累计 ≥20;
        ③最近 5 个战斗节点累计 ≥30。累计阈值的持久依据=条件败局伤害
        期望的整数倍(math_proofs P15:L_c(rung)=11.32−0.37·rung,
        registry.vd_p1_loss_*;代表帧 rung2 → L_c≈10.6):
        ②20≈2×L_c(21.2)=3 节点窗吞两次满额败局(容 1 个良性节点,
        急性);③30≈3×L_c(31.7)=5 节点窗三次满额败局(慢性多数败
        漂移);①连续 2 败与②同账——2×L_c 分摊到相邻两场。"""
        if self.consec_battle_fails >= 2:
            return True
        losses = [loss for _t, loss in self.recent_losses]
        if len(losses) >= 3 and sum(losses[-3:]) >= 20:
            return True
        return len(losses) >= 5 and sum(losses) >= 30


# ===== 纪律族评估(decide_prep 每轮入口消费)=====


@dataclass(frozen=True)
class DisciplineView:
    """一轮的纪律族裁决(层2/层4 的视图输入)。

    - ``coverage``:'emergency' | 'blood_alarm' | 'boss_breaker' |
      'mode'(判读/遥测锚点;追赶态 'catchup' 已随 W126/ADR-0349 退场);
    - ``mode``:'war'|'economy'(filters/interest_rule 消费);
    - ``allin``:位面末最后一战([18] 限定)——**唯一**清零地板的路径;
    - ``allow_refresh_in_war``:保血通道(点12)——报警+硬节点放行 refresh
      (remediation S2 消费;层2 的 war 标签集已含 refresh,W126/ADR-0349
      「war 滤 refresh」废除——本字段只剩补偿辖域语义);
    - ``war_floor_override``:boss_breaker 破息窗地板(v1 r278/r308 EV 移植)。
    """

    coverage: str
    mode: str
    allin: bool = False
    allow_refresh_in_war: bool = False
    war_floor_override: int | None = None

    def arbiter_registry(self, registry: DecisionV2Registry
                         ) -> DecisionV2Registry:
        """层4 仲裁用注册表视图(地板按纪律调整;评分仍用原表)。"""
        reg = registry
        if self.allin:
            # [18] 位面末最后一战 ALL IN:地板全清零(唯一路径;hp 报警
            # 不是 ALL IN 的触发——报警态下此窗开通是位面末授权,
            # 非「报警触发」)。息线清零走 override 通道(D3 双源清偿:
            # interest_floor 字段已删,标定单一源 = interest_cap × 10 派生)
            reg = replace(reg, interest_floor_override=0, war_floor=0,
                          rebirth_floor=0, boss_floor=0)
        elif self.war_floor_override is not None:
            reg = replace(reg, war_floor=self.war_floor_override)
        return reg


def boss_window_active(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> bool:
    """boss 破息窗统一口径(W113 §8-2;W119/ADR-0347)。

    主判据=**节点图**:node_type ∈ boss_round_node_types(boss 节点)。
    轮数口径**全仓只在此处保留**,且仅作 node_type 缺读兜底:P1 位面末
    r≥boss_window_fallback_round(9)且节点类型不可读 → 按 boss 窗处理
    (P1 末节点恒为 boss 的节点图先验)。

    旧双口径收编说明:discipline 旧「P1 r≥5 遭遇预备窗」(无论节点
    类型一律 war)与 arbiter/remediation 旧「P1 r≥9」三处轮数口径
    一次收进本函数——节点图可读且非 boss 时不再按轮数入窗(W115-B2
    审计:轮数代理是 boss 临近的双口径漂移源)。
    消费点:arbiter._active_floor/_round_state_dims/interest_rule/
    boss_levelup_ban、remediation._compensate_slot、本模块 assess_
    discipline。
    """
    node = getattr(session, 'node_type_current', None) or state.node_type or ''
    if node:
        return node in registry.boss_round_node_types
    return (state.plane == 1
            and state.round_num >= registry.boss_window_fallback_round)


def _hard_node(state: GameState, session: StrategySession) -> bool:
    """硬节点分类(掉血风险节点;W119/ADR-0347 单一源)。

    = encounter/boss/遭遇 ∪ 普通战斗且位面内剩余 ≤3(boss 临近;剩余按
    ``nodes_of_plane(session)`` 本位面真值——ADR-0366:P2=7 轮,旧按 9 计
    使窗推迟两轮)。
    消费点:_streak_floor(连胜 EV 地板)与 assess_discipline 保血
    通道的 hard 判定(两处同源,禁散写)。

    **扑满节点(过热局 reward)不辖**(ADR-0348 口述定谒 2026-08-26:
    扑满关不掉血——真损失是「打不过没奖励」,处置=确保伤害阵容去拿
    奖励,**不深花保血**)——「低危战斗」的战斗向买/刷开放在 scoring
    侧(refresh 轮界豁免,`ev.reward_node_is_battle`),地板不降。
    """
    node = getattr(session, 'node_type_current', None) or state.node_type or ''
    if node in ('encounter', 'boss', '遭遇'):
        return True
    remaining = max(0, nodes_of_plane(session) - state.round_num)
    return node in ('battle', '战斗') and remaining <= 3


def plane_last_battle(state: GameState, session: StrategySession) -> bool:
    """位面末最后一战([18]):当前节点=boss 且轮=位面节点数(真值源
    ``nodes_of_plane``——P2 boss@r7 判正;旧按 9 计 P2 永不触发,
    ADR-0366 口径断层修复)。"""
    node = getattr(session, 'node_type_current', None) or state.node_type or ''
    return node in ('boss',) and state.round_num >= nodes_of_plane(session)


# ===== 血预算停手·停升级线(设计件 12 §3.1/§2.3-P1-b;ADR-0448)=====


def p2_levelup_stop_hp(registry: DecisionV2Registry) -> int:
    """P2 停升级线(设计件 12 §6 参数表 P2_LEVELUP_STOP_L_C)
    = ceil(blood_budget_stop_d × vd_p2_loss)。d=1、vd_p2_loss=20.05
    → 21 血。L_c 口径=registry.vd_p2_loss(P12 收益侧条件败局伤害);
    W375 双源重标定后的条件败面档(p2_cond_loss_table normal=12.77)
    与本线的口径取舍 = 设计件 12 §5.4-1 标定核对项——重推裁决前本线
    以设计定稿的 vd_p2_loss 为单一源,禁散写第二份数值。"""
    import math
    return math.ceil(registry.blood_budget_stop_d * registry.vd_p2_loss)


def p1_levelup_stop_hp(registry: DecisionV2Registry) -> int:
    """P1 停追级线(设计件 12 §6 参数表 P1_LEVELUP_STOP_L_C)
    = ceil(d × L_c),L_c = vd_p1_loss_intercept + vd_p1_loss_slope_rung
    × p1_levelup_stop_rung(d=1、rung2 代表帧 ≈10.58 → 11 血)。
    完备性条款(设计件 12 §2.3):线很深、预期触发少——堵死「1 血局
    仍升级」的角案,主杠杆在 P1-a/P1-c(未在本批辖域)。"""
    import math
    l_c = max(0.0, registry.vd_p1_loss_intercept
              + registry.vd_p1_loss_slope_rung * registry.p1_levelup_stop_rung)
    return math.ceil(registry.blood_budget_stop_d * l_c)


def blood_budget_levelup_blocked(state: GameState, session: StrategySession,
                                 registry: DecisionV2Registry) -> bool:
    """血预算停手·停升级门(设计件 12 §3.1 P2 / §2.3-P1-b;ADR-0448)。

    P21 已证:存活到账判据 h > d·L_c 在 h ≤ d·L_c 域内恒假 → 升级收益
    恒 0、EV=−C−I 严格为负,且敏感网格 (p,Δp,d,c) 全负域——结论与
    β 标定无关。备战帧 hp ≤ 停升级线(P1/P2 各自线)时拒绝购买经验。

    接缝语义(设计件 12 §5.2/§5.3,实现形态裁决):
    - **授权通道前置拒付过滤**,与息线门是独立谓词取 AND(血线胜)——
      不是第五种覆盖态,discipline 覆盖序不动,emergency 态内同样生效
      (应急梯度给「怎么花」,停手给「不许为未来花」);
    - 唯一豁免 = ``plane_last_battle`` ALL IN 清零窗(位面末最后一战
      是损失最小的花光时机,[18];停手让位)。
    消费点:arbiter 约束 'blood_budget_stop'(候选通道)/remediation
    稳态多击组与 deploy_cap 补偿臂①(授权通道旁路——两臂的升级收益
    同在 ≥1 战之后才兑现,同辖;拒付计数=session.v3_blood_budget_
    rejects,披露模式对齐 sim 执行层 level_cap_rejects)。

    消费层可信位门(ADR-0448 血线谓词唯一收口,W580):
    ``hp_decision_trusted`` 不过的帧((hp_readable, hp_trusted)=(False,
    False):开局兜底 100 帧/shop 覆盖丢位帧)fail-closed 按血线内处理
    (拒付升级)——线内升级 EV=−C−I 严格负(本函数数学),证据缺失时
    禁令保持有效与误放的非对称代价(误放=血线内追级,误拦=少升一级)
    同型于 ADR-0428 兜底假值帧拒语义。不降姿态/不维持上次决策:谓词
    逐帧无状态且被三面共享,引入跨帧记忆=新状态机不成比例;只封
    LevelUp 通道,买牌/刷新各有其门。置于 ALL IN 豁免之后:豁免语义
    =「末战花光是时机不是血线判断」,在不可信帧上仍生效。
    """
    if not registry.blood_budget_stop_enabled:
        return False
    if plane_last_battle(state, session):
        return False    # ALL IN 窗:停手让位([18] 唯一清零地板路径)
    if not hp_decision_trusted(state):
        return True     # 不可信 hp 帧:fail-closed 按血线内处理(拒升级)
    if state.plane == 2:
        return state.hp <= p2_levelup_stop_hp(registry)
    if state.plane == 1:
        return state.hp <= p1_levelup_stop_hp(registry)
    return False


# ===== 血预算停手·第二波:末窗支出降格/搜索型刷新停付 =====
# (设计件 12 §2.3-P1-a/P1-c、§3.2;ADR-0451)


def p1_exit_blood_short(state: GameState,
                        registry: DecisionV2Registry) -> bool:
    """P1 末窗血预算不足谓词(设计件 12 §2.2/§6;ADR-0451):
    P1 末窗(r≥handoff_gate_min_round,承接门语境单一源)∧
    hp < p1_exit_blood_target。

    hp 线语义=期望预算线(p1_exit_blood_target 注释;W524 审计后:
    充分不必要、非存活保证)。纯辖域谓词不带开关——开关语义在
    p1_directed_downgrade_active(P1-a)/blood_budget_refresh_blocked
    (P1-c)各自出入口,A/B 双臂可独立注入。依据=W516 排除证据
    (HG5/IF30):β 弱通道下「多买战力件」换回的胜率不足以对冲
    15-25 血/败;减损路径(bench 囤件变现上场、[11] 同息档羁绊档
    填充)无 β 依赖。
    """
    return (state.plane == 1
            and state.round_num >= registry.handoff_gate_min_round
            and state.hp < registry.p1_exit_blood_target)


def p1_directed_downgrade_active(state: GameState,
                                 registry: DecisionV2Registry,
                                 session: StrategySession | None = None,
                                 ) -> bool:
    """P1-a 末窗支出降格触发面(设计件 12 §2.3-P1-a;ADR-0451):
    承接门定向投资授权在血预算不足局的支出结构降格:战力投资 →
    减损保血。降格只停**授权豁免通道**(定向星级 copy 臂/破息缺口项/
    定向刷新预算),减损型动作族(bond_fallback/pair/plugin/deploy)
    不在辖域——动作族复用 11 号件 blood_protect 梯度既有语义,不新增
    动作。

    终止短路(P1「止损转支出」;ADR-0470 §3-3;ADR-0469):
    ``terminal_release`` 为真的帧降格不辖——降格的隐含前提是「血预算
    还值得保」(W516 排除证据的适用域),死亡域内保血价值被金零值
    引理压没,减损型填充在 hp≤10 战力面上正是「低效消费」的构成;
    短路后恢复定向战力买授权(W242/ADR-0405 通道,动作族零新增)。
    ``session`` 可选(记位面内触发闩的载体;None=裸评估,只算当帧
    S0 不置闩——遥测观测面用法)。
    """
    if not registry.p1_exit_downgrade_enabled:
        return False
    if not p1_exit_blood_short(state, registry):
        return False
    # 终止分支短路:死亡域保血零价值,降格让位(ADR-0470 §3-3)
    return not terminal_release(state, session, registry)


def blood_budget_refresh_blocked(state: GameState, session: StrategySession,
                                 registry: DecisionV2Registry) -> bool:
    """血预算停手·搜索型刷新停付(结构语义;设计件 12 §2.3-P1-c/§3.2;
    ADR-0451)。刷新分型:搜索型(为找件/挑线付刷新费)停付 vs 急救型
    保留。急救型豁免=应急带内刷新(应急带 hp≤emergency_hp 的刷新授权
    语义=搜牌补板当轮转化变现,[31]④ 合法用途归类;血线内的当轮转化
    豁免由此承载);唯一窗口豁免=``plane_last_battle`` ALL IN(同
    blood_budget_levelup_blocked,停手让位,[18])。

    接缝语义:与息线门独立谓词取 AND(血线胜——release 泄息刷新在
    血预算不足帧同样停,M-A 定向刷新预算不消耗);非第五种覆盖态。

    **数值停刷新线不在本谓词**:收益项=Δp×β 不可算,挂 β 开臂判据
    (设计件 12 §3.2/§4.1),标定前只落结构不落数值。P2 辖域在标定前
    为空:P2 血危机带(应急带)已在急救豁免面,非应急 P2 帧的血预算
    判据无数值——P1 辖域=末窗血预算不足([31]④ 硬约束归位,血预算
    不足局不为找件付刷新费;锁线判定本身不动,只挡搜索型支出)。
    消费点:arbiter refresh 收尾裁决(拒付计数=session.v3_blood_budget_
    refresh_rejects,披露模式对齐 blood_budget_levelup_rejects)。

    终止豁免(P1「止损转支出」;ADR-0470 §3-1;ADR-0469):ALL IN
    豁免之后、应急豁免之前,``terminal_release`` 帧 ∧ 当轮转化双门开
    (``terminal_round_conversion_open``)→ 不停付——死亡域刷新的真实
    成本(刷价 2 金+息损)被金零值压到可忽略,收益端任何 Δp>0 占优
    (EV 对比式);板满帧双门关维持停付(战力兑现延到次战之后,防
    无效购买形态)。**停升级门不在终止豁免辖内**(P21 数学:濒死升级
    EV=−C−I 严格为负,与金是否零价值无关;适用边界见设计 v2 R5)。
    """
    if not registry.blood_budget_refresh_stop_enabled:
        return False
    if plane_last_battle(state, session):
        return False    # ALL IN 窗:停手让位([18] 唯一清零地板路径)
    if terminal_release(state, session, registry) \
            and terminal_round_conversion_open(state, registry):
        return False    # 终止豁免(v2 §3.1;当轮转化双门,板满帧不辖)
    if state.hp <= registry.emergency_hp:
        return False    # 急救型保留(应急带=搜牌补板当轮转化豁免面)
    return p1_exit_blood_short(state, registry)


# ===== 血预算停手·终止分支(P1「止损转支出」;ADR-0470)=====
# 机制:低血攥金等死域(守钱世界存活概率上界 S0≤ε)内,金留到死=零
# 价值,停付防线让位给「当轮转化」支出路径。判据只用当前板面静态
# 标定量(S0/rung/剩余节点表),不含「转支出后」假设——非循环;
# S0 忽略非穿透场累计失血 → 是真存活概率的**上界**,用上界做触发
# → 只有连上界都 ≤ε 才放行 → 误放方向被压住(fail-safe)。


def terminal_survival_upper_bound(state: GameState, session: StrategySession,
                                  registry: DecisionV2Registry) -> float:
    """守钱世界存活概率上界 S0=Π_{i∈K} p_i(ADR-0470 §2-1)。

    - K = 单发穿透链:L_i ≥ hp 的剩余场(L_i=第 i 场条件败面伤害,
      一败即死 → 守钱世界必须全胜)。L_i/p_i 全走既有标定单一源:
      battle L=vd_p1_loss_intercept+vd_p1_loss_slope_rung×rung;
      encounter/boss L=streak_floor_loss_damage;battle/encounter/boss
      p=streak_floor_win_rate(P1 注入表;h3_win_rate 骨架插值表禁作
      第二源,双源互斥条款)。
    - rung 坐标 = 连胜地板同源口径(deployed 域,0-2 钳制,
      scoring._engines_formed;防 bench×0.35 偏乐观)。
    - 剩余节点表 = session.plane_node_table 本位面槽(表缺失退
      battles_left_est,全部按 battle 档——L 最小 → K 最小 → S0
      更高 → 触发更难,保守侧)。非战斗节点(reward/supply)不入列。
    - K=∅(没有任何「一败即死」的场)→ S0=1(空链恒真)→ 不触发:
      「死亡不可避免」判据自然不成立的语义承载(设计 §2.3 行进带
      上沿用例)。
    """
    from sr_od.application.currency_war.cw_plane_table import NODES_PER_PLANE
    from sr_od.application.currency_war.decision_v2.ev import (
        NON_BATTLE_NODE_TOKENS,
        battles_left_plane,
    )
    from sr_od.application.currency_war.decision_v2.scoring import (
        _engines_formed,
    )
    rung = min(2, max(0, _engines_formed(state, registry)))
    table = getattr(session, 'plane_node_table', None) or []
    kinds: list[str] | None = None
    if table:
        r = state.round_num
        remaining = [str(t) for t in
                     table[max(0, r - 1):min(len(table), NODES_PER_PLANE)]]
        kinds = ['encounter' if t in ('encounter', '遭遇')
                 else 'boss' if t == 'boss'
                 else 'battle'
                 for t in remaining if t not in NON_BATTLE_NODE_TOKENS]
    if kinds is None:
        kinds = ['battle'] * int(battles_left_plane(state, session, registry))
    s0 = 1.0
    for kind in kinds:
        if kind == 'battle':
            d = max(0.0, registry.vd_p1_loss_intercept
                    + registry.vd_p1_loss_slope_rung * rung)
        else:
            intercept, slope = registry.streak_floor_loss_damage[kind]
            d = max(0.0, intercept + slope * rung)
        if d < state.hp:
            continue    # 非穿透场不入 K(累计失血约束不计 → 上界口径)
        s0 *= registry.streak_floor_win_rate[kind][rung]
    return s0


def terminal_release(state: GameState, session: StrategySession | None,
                     registry: DecisionV2Registry) -> bool:
    """P1 终止分支谓词(ADR-0470 §0/§2):守钱世界存活
    概率上界 S0≤``registry.terminal_survival_eps`` 时停付防线让位。

    判据链(缺一不可):
    1. 开关 ``terminal_release_enabled``;
    2. **``state.plane == 1`` 硬门**(设计 v2 R6 一行必改)——首批辖域
       P1 only:P2 帧 hp≤21 早期帧 S0 极小,无硬门会持续算 True 形成
       不消费 P2 参数的第二判定源;两个被释放谓词经 p1_exit_blood_
       short 本就 plane==1,硬门使谓词自身辖域一致;
    3. 位面内触发闩(R7,FM-8 对冲):本位面首次触发后恒释放(session
       载体 ``v3_terminal_release``,位面切换由 ``v3_terminal_release_
       plane`` 键控清零)——释放后买件推高 rung 使 S0 回升越 ε 的邻域
       抖动不回退;金零值引理单调性:hp 只降不升,不存在「触发后又该
       守钱」的反悔世界;
    4. 非位面末 ALL IN 窗(既有豁免已让位,分支不重复辖,账本位同口径);
    5. ``hp_decision_trusted`` fail-closed(不可信 hp 帧不判,误放代价
       > 误拦,与血线谓词同取向);
    6. S0 ≤ ε(ε 推导与重标定挂账见 registry 注释)。

    session=None(裸评估):只算当帧判据不置闩——纯函数可测/观测面。
    """
    if not registry.terminal_release_enabled:
        return False
    if state.plane != 1:
        return False    # R6 硬门:首批 P1 only
    if session is not None \
            and getattr(session, 'v3_terminal_release', False) \
            and getattr(session, 'v3_terminal_release_plane', None) \
            == state.plane:
        return True     # 位面内触发闩(R7):邻域抖动不回退
    if plane_last_battle(state, session):
        return False    # ALL IN 窗既有豁免已让位,分支不重复辖
    if not hp_decision_trusted(state):
        return False    # 不可信 hp 帧 fail-closed:停付照旧
    if terminal_survival_upper_bound(state, session, registry) \
            > registry.terminal_survival_eps:
        return False
    if session is not None:
        session.v3_terminal_release = True
        session.v3_terminal_release_plane = state.plane
    return True


def terminal_release_bit(session: StrategySession | None,
                         plane: int) -> bool:
    """账本决策位(R4 记账面):闩位对指定位面的有效值(单一址=谓词
    本身的闩,无双源)。cw_sim 账本行/cw_telemetry 披露统一走本位——
    检查器只验位与行为一致,**禁同式复算 S0**(设计 v2 R4)。"""
    if session is None:
        return False
    return bool(getattr(session, 'v3_terminal_release', False)) \
        and getattr(session, 'v3_terminal_release_plane', None) == plane


def terminal_round_conversion_open(state: GameState,
                                   registry: DecisionV2Registry) -> bool:
    """终止豁免的当轮转化双门(ADR-0470 §3-1/R2;ADR-0469):
    刷新换来的战力件必须能**当轮上场兑现**(死前兑现确定性最高的
    deploy 空位帧),板满帧买入只能落 bench(sim 口径权重 0.35、兑现
    延到次战之后)——不进释放辖域,维持停付。

    双门(v2 R2 资源判据纠错:真约束是 deploy 槽非 bench 槽):
    **bench 空槽 ∧(deploy 空位 ∨ 存在可被替换的板面垫底件)**。
    垫底件判据=deployed 存在 1★ 件(星级=静态可读的强度序;2★/3★
    是合成载体不视作垫底);替换动作走既有 deploy/fill 语义,零新
    动作族。卖件腾槽路径首批不放(装备/合成素材损失 sim 不可见,
    FM-10)——本门不含卖侧,板满且全员 ≥2★ 的帧维持停付。"""
    from sr_od.application.currency_war.cw_state import (
        bench_occupied,
        deployed_occupied,
    )
    if bench_occupied(state.bench or []) >= registry.bench_capacity:
        return False    # bench 无空槽:买不进,无从转化
    if deployed_occupied(state.deployed or []) < state.max_units():
        return True     # deploy 空位:当轮上场直接兑现
    return any((getattr(d, 'star', 1) or 1) == 1
               for d in (state.deployed or [])
               if getattr(d, 'char_id', ''))   # 存在可替换的 1★ 垫底件


def _streak_floor(state: GameState, session: StrategySession,
                  registry: DecisionV2Registry,
                  base_floor: int) -> int:
    """boss_breaker 连胜 EV 地板(v1 r308 移植;标定账=ADR-0356 挂账项):

    连胜 ≥2 + 硬节点 + 深花收益 V ≥ 息成本 C → 地板在 base_floor 上
    再降 5。

        V = V_blood + V_streak ≥ C

    - **V_blood(主项)** = (1−p)·D·hp_to_gold:打赢当前硬节点避免一次
      败局掉血。D=**条件败局伤害**(two_state_model 口径,「打了但输了」
      的期望,胜率已单列——与 p 相乘不双计,P15 口径命题;误用无条件
      均值拟合会把胜率算进均值、双计且系统性低估):battle 复用
      ``vd_p1_loss_*`` 单一源,encounter/boss 见
      ``streak_floor_loss_damage``;D = 截距+斜率×成型档(封顶 2)。
    - **V_streak(次项)** = (连胜金档−1)×剩余战斗节点×p:断连胜后每场
      胜利的金档损失(STREAK_GOLD_TABLE,断后回 1 档;reward/supply
      节点不吃连胜金,故按 ``battles_left_plane`` 数)。胜率 p 取
      ``streak_floor_win_rate``(节点类型×成型档注入表)。
    - **C** = ``ev.interest_cost(gold, gold−5, ...)`` 回档口径:地板
      授权把金花到 5,息成本按「金 → 5」的真实跨档数 ×
      interest_recovery_rounds(金 12 → 1 档=3 金;金 ≥20 → 2 档=6 金)。

    量级:V ≈ 4-16 金(血项主导)≥ C ≤3 金在硬节点全域成立——
    **「5」是授权带宽(V−C 盈余带内偏保守),不是账本输出**;带宽加宽
    需 sim A/B 另批(与相位阶梯交叉)。boss 位面末 remaining=0 时
    V_streak=0,fire 由 V_blood 单独支撑(旧账 (tier−1)×remaining
    在此恒不 fire,正是其口径错档的症状)。
    """
    streak = getattr(session, 'last_streak', 0) or 0
    if streak < 2:
        return base_floor
    hard_node = _hard_node(state, session)
    if not hard_node:
        return base_floor
    from sr_od.application.currency_war.decision_v2.ev import (
        battles_left_plane,
        interest_cost,
    )
    from sr_od.application.currency_war.decision_v2.scoring import (
        _engines_formed,
    )
    node = getattr(session, 'node_type_current', None) or state.node_type or ''
    if node in ('encounter', '遭遇'):
        kind = 'encounter'
    elif node in ('boss',):
        kind = 'boss'
    else:
        kind = 'battle'
    rung = min(2, max(0, _engines_formed(state, registry)))
    p = registry.streak_floor_win_rate[kind][rung]
    if kind == 'battle':
        d = max(0.0, registry.vd_p1_loss_intercept
                + registry.vd_p1_loss_slope_rung * rung)
    else:
        intercept, slope = registry.streak_floor_loss_damage[kind]
        d = max(0.0, intercept + slope * rung)
    v_blood = (1.0 - p) * d * registry.hp_to_gold
    v_streak = (streak_gold(streak) - 1) \
        * battles_left_plane(state, session, registry) * p
    c = interest_cost(state.gold, max(0, state.gold - 5), state,
                      registry.interest_recovery_rounds)
    if v_blood + v_streak >= c:
        return 5
    return base_floor


def assess_discipline(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> DisciplineView:
    """纪律族评估(覆盖态优先序:应急 > 掉血报警 > boss_breaker > 模式;
    追赶态已随 W126/ADR-0349 退场——人口落后由通道 2/4+EV 涌现承接)。

    语义重接要点(strategy_v4 点4/点7/点12):
    - 应急(hp≤emergency_hp):rebirth 地板由层4 ``_active_floor`` 分派
      (is_emergency 优先),此处只标 coverage/mode;
    - 掉血报警(三臂):**报警不是触发**——处置梯度①自然补强窗
      (mode=economy)→②弃息 D 保血(war+硬节点放行 refresh);
      不动地板;ALL IN 仅当位面末(``plane_last_battle``,[18] 授权);
    - boss_breaker:boss 节点(boss_window_active 统一口径,W119/ADR-0347:
      节点图为主,轮数只作 node_type 缺读兜底),war 模式+破息地板 10
      (连胜 EV 5);
    - ALL IN:仅 ``plane_last_battle``([18] 位面末最后一战限定)。
    """
    if state.hp <= registry.emergency_hp:
        return DisciplineView(coverage='emergency', mode='war',
                              allin=plane_last_battle(state, session))
    tracker = getattr(session, 'v3_alarm', None)
    if tracker is not None and tracker.alarm_active():
        # 处置梯度三步(strategy_v4 点4 S4;W51 补全时限与血边际):
        # ①自然凑羁绊——上界 1 个战斗节点(报警激活后首个战斗节点窗
        # 内 mode=economy,不弃息,给自然补强机会);
        # 窗耗尽未达标(alarm_battles>BLOOD_GRADIENT_NATURAL_BATTLES)
        # 或血边际已低([19]② hp<BLOOD_MARGIN_LOW_HP——血 <40 本就是
        # 报警档,梯度直接生效)→ ②弃息 D 保血(war+硬节点放行
        # refresh,点12 保血通道);
        # ③位面末最后一战 ALL IN(allin=plane_last_battle——[18]/点4
        # 授权;报警不是 ALL IN 的触发,位面末才是)。
        # [19]③「来牌顺不顺」未消费(欠账声明:定性变量,sim 层无载体,
        # 挂实机语料后补)。
        # hard=硬节点分类单一源(_hard_node;扑满守卫 ADR-0348 在彼接线:
        # 过热局 reward 节点按战斗节点处理→保血通道辖)
        hard = _hard_node(state, session)
        escalated = (tracker.alarm_battles > BLOOD_GRADIENT_NATURAL_BATTLES
                     or state.hp < BLOOD_MARGIN_LOW_HP)
        if escalated:
            return DisciplineView(
                coverage='blood_alarm', mode='war',
                allin=plane_last_battle(state, session),
                allow_refresh_in_war=hard)
        return DisciplineView(
            coverage='blood_alarm', mode='economy',
            allin=plane_last_battle(state, session))
    if boss_window_active(state, session, registry):
        floor = _streak_floor(state, session, registry, registry.boss_floor)
        return DisciplineView(
            coverage='boss_breaker', mode='war',
            allin=plane_last_battle(state, session),
            war_floor_override=floor)
    return DisciplineView(coverage='mode', mode='economy')


# ===== carry_gate(bench 满腾位买意向核心;v1 r416 语义重接)=====


def _line_protect_set(comp) -> set[str]:
    """意向线正料保护集(核心+共享+替班+引擎件;carry_gate 与金不足
    变现通道共用单一源——防两处各自派生漂移)。"""
    protect = set(comp.core_chars) | set(comp.shared_chars)
    for p in comp.substitute_plan:
        if p.get('替班者'):
            protect.add(p['替班者'])
    protect |= engine_char_names()
    return protect


def carry_gate_actions(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry,
                       bought: set[str] | None = None) -> list:
    """carry 腾位门(v1 ADR-0280 r416 移植;语义重接):

    v1:carry=``line_of(locked_line).carry``;v2:carry=意向核心
    (``intention_core`` of COMP_LIBRARY v2 锁定套)。门(全过才腾位):
    ①收益域 P1 r≤carry_gate_max_round;②意向锁定且核心在店、未持有、
    金足(不破 war 地板);③bench 满(≥9)且无直接可卖件(保护集外
    且非近轮种子);④降保护集挑 off-line 价值最低件(弱序:非保护 >
    副本冗余/超上限;3合1 完整份不动;r416b absent_mergeable
    [上场份缺席的 ≥2 加权副本]弱序等同超上限冗余=最弱级;种子
    2 轮窗件单列兜底——唯一可卖=种子时豁免放行防 carry 死锁,
    仍选最弱,ADR-0289 §5 年龄保护在降保护集阶段让位于 carry);
    ⑤卖出件入同轮已卖集不回买。

    保护集口径(W51 声明修正,与实际实现对齐):**意向线正料派生**
    = core_chars ∪ shared_chars ∪ 替班者 ∪ 引擎件(engine_char_names)
    ——非 ``session.v3_hoard`` 全集(后者含跨线骨架/装备材料,口径
    更宽);跨线囤件不在保护集,可被降级卖出腾位买核心。
    """
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState) or ist.phase != 'locked':
        return []
    from sr_od.application.currency_war.cw_comps import get_comp
    comp = get_comp(ist.locked_comp)
    if comp is None:
        return []
    carry = intention_core(comp)
    if not carry:
        return []
    if state.plane != 1 or state.round_num > registry.carry_gate_max_round:
        return []
    if bought and carry in bought:
        return []
    carry_card = next((c for c in (state.shop or [])
                       if c.name == carry), None)
    if carry_card is None:
        return []
    if has_same_name_copy(carry_card, state) \
            or any(d.char_id == carry
                   for d in iter_occupied_deployed(state.deployed or [])):
        return []
    if in_round_sold(carry, state, session):
        return []
    # W544(ADR-0453):满栏合成买优先于腾位——用户权威裁决「备战满时,
    # 触发合成的购买应该被支持,否则被迫卖有用角色」。核心在店且本次
    # 购买完成恰好一次合成(k = min(店内张数, 3−已有数 mod 3),判据
    # 单一源 = cw_state.merge_buy_completes)→ 不卖任何件直接买,金按
    # k×单价校验 war 地板;不满足合成条件 → 原腾位链逐位不动(零漂移)。
    _mb_full = bench_occupied(state.bench or []) >= BENCH_CAPACITY
    _mb_k = 0
    if _mb_full:
        from sr_od.application.currency_war.cw_state import (
            merge_buy_completes,
            merge_buy_k,
        )
        if merge_buy_completes(carry, carry_card.star or 1, state.bench,
                               state.deployed, state.shop):
            _mb_k = max(1, merge_buy_k(carry, carry_card.star or 1,
                                       state.bench, state.deployed,
                                       state.shop))
    if state.gold - carry_card.cost * max(1, _mb_k) < registry.war_floor:
        return []
    if _mb_k >= 1:
        # 满栏合成买(k≥1,含旧 S3 k=1 特例——原腾位链对可合成买照样
        # 卖 weakest,即裁决针对的「被迫卖」)→ 不卖直接买。
        register_round_bought([carry], state, session)   # ADR-0328 同型登记
        return [BuyCard(carry_card, reason='carry_gate')]
    bench = state.bench or []
    if bench_occupied(bench) < BENCH_CAPACITY:
        return []   # 未满 → 常规买通道可达(ADR-0316:容量=占用数)
    # 保护集 = 意向线核心+共享+替班(正料不卖)+引擎件(种子)
    protect = _line_protect_set(comp)
    # ③ 直接卖通道可用 → 不降保护集
    board_factions = set(state.board.keys())
    for b in bench:
        if (b is not None and b.char_id and b.char_id not in protect
                and b.faction not in board_factions
                and not round_sell_blocked(b, state, session)
                and not seed_age_blocked(b, state, session)):
            return []
    # ④ 降保护集:off-line 价值最低件(统一弱序 sell_priority_key,
    # ADR-0327——absent_mergeable/超上限归 redundancy=0;加权副本≥2
    # 的 3合1 进行中素材由键统一挡,AD9-2-3)
    cands: list[tuple[tuple, int, object]] = []
    # 种子 2 轮窗(ADR-0289 §5)**绝对不让位**(W88/ADR-0339 件3 裁决):
    # 旧版 W51「carry 死锁豁免」在唯可卖=新鲜种子时仍卖种子买 carry
    # ——买侧见即买 engine_seed 与卖侧 carry_gate 互踩(seed16 姬子·启行
    # r4 买 r6 卖 r7 再买,检查器 0 容忍与设计豁免矛盾)。裁决:窗口内
    # 种子赢过 carry 腾位(卖种子换 carry 的期望=再遇窗口双倍化,[22]③
    # 弃购代价),本轮不腾、carry 延后——窗口 ≤2 轮自然解锁,死锁有界。
    for i, b in enumerate(bench):
        if b is None or not b.char_id or b.char_id == carry:
            continue
        if seed_age_blocked(b, state, session):
            continue
        key = sell_priority_key(b, state, session, protect, registry)
        if key is None:
            continue   # r408 同轮已买/加权副本≥2(AD9-2-3)/未识别统一挡
        cands.append((key, i, b))
    if not cands:
        return []   # 唯一可卖=窗口内种子:carry_gate 让位延后(上注)
    cands.sort(key=lambda c: c[0])
    _k, idx, weakest = cands[0]
    refund = None
    ch = CHARACTERS.get(weakest.char_id)
    if ch is not None and ch.cost:
        refund = sell_refund(getattr(weakest, 'star', 1) or 1, ch.cost)
    log.info('[cw][d2][carry-gate] r%d 腾位:降保护集卖 %s 买意向核心 %s',
             state.round_num, weakest.char_id, carry)
    register_round_sold([weakest.char_id], state, session)   # r408 对称臂
    # ADR-0328:腾位买即登记同轮已买集(登记点=动作采纳处,非 decide_prep
    # 尾)——carry_gate 先于 arbitrate 执行,不登记则同趟 arbitrate 内
    # SELL carry(段首旧副本)候选的 r408 守卫仍读空已买集,双双过。
    register_round_bought([carry], state, session)
    return [SellBench(bench_idx=idx, income=refund),
            BuyCard(carry_card, reason='carry_gate')]


# ===== 金不足变现通道(已收编,W52/ADR-0326)=====
# liquidity_actions + LIQUIDITY_BUY_TAGS 已删——语义收编进
# decision_v2/remediation.py 的 _compensate_gold(通用回连机制,
# 触发源从层3 预测 state.gold 换层4 实际 working.gold);
# remedy_buy_tags(含 carry_gate)迁 registry。既有测试锁语义化
# 重写见 test_cw_w35_decision_v2_carrier.py(liquidity → 补偿器)。

# ===== S5 统一卖件弱序(W52/ADR-0327;纪律族单一源)=====
# 四卖件通道(carry_gate ④/两补偿器/层3 off_target 评分)统一消费
# sell_priority_key——禁各通道手搓弱序(双源漂移温床,设计 §4)。


def _sell_expected_loss(cost: int, registry: DecisionV2Registry) -> float:
    """[22]③ 再遇代价 × W4 终局贯穿率(点5 键静态近似;ADR-0327)。

    loss = remeet_rounds(cost) × through_rate(cost)——费级表在
    registry(remeet_window_rounds/through_rate,sim 校准域)。
    """
    remeet = registry.remeet_window_rounds.get(cost, 30)
    through = registry.through_rate.get(cost, 0.15)
    return remeet * through


def sell_priority_key(bc, state: GameState,
                      session: StrategySession,
                      protect: set[str] | None = None,
                      registry: DecisionV2Registry | None = None,
                      ) -> tuple | None:
    """统一卖件弱序键(升序=最先卖;None=不可卖,调用方跳过)。

    键结构(逐位比较;既有豁免/守卫的复合 + 点5 期望损失键):
      (in_protect,          # 保护集外最先进(保护集成员垫底)
       redundancy,          # 0=冗余最弱(超上限/absent_mergeable,
                            #   carry_gate ④ 同档),1=常态
       expected_loss,       # 再遇代价×终局贯穿率(点5 键;静态近似)
       net0_rank,           # 净0 件(1星/1费,全额退)置 0 最先
       cost, star)          # 同档按费升序/星升序(确定性兜底)

    守卫(复用既有谓词,不重定义;任一命中 → None):
      round_sell_blocked(r408 同轮已买)/seed_age_blocked(ADR-0289 §5
      年龄窗;种子单列兜底逻辑由 carry_gate ④/补偿器保留在外——
      豁免是专属时序,键不管)/sole_engine_sell_blocked(W184/ADR-0373
      唯一体系引擎件)/未识别(空名)/**加权副本 ≥2**(3合1
      进行中素材与完整份,AD9-2-3/ADR-0327——防补偿/腾位通道拆
      合成进度)。

    槽位模型(ADR-0316):入参 bc=BenchChar(None 槽由调用方枚举时
    跳过);返回键不含槽位号——发射时由调用方带槽位号(置 None 语义)。
    ``registry`` 可选(期望损失表;缺省用模块默认注册表——A/B 注入
    时调用方显式传)。
    """
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    name = getattr(bc, 'char_id', '') or ''
    if not name:
        return None    # 未识别(空名)
    if name not in CHARACTERS:
        return None    # 未识别(注册表外——费级/回金/合成进度不可估)
    if round_sell_blocked(bc, state, session):
        return None
    if seed_age_blocked(bc, state, session):
        return None
    if sole_engine_sell_blocked(bc, state, reg):
        return None    # W184/ADR-0373:唯一体系引擎件不进任何卖件通道
    if form_break_sell_blocked(bc, state, session, reg):
        return None    # 方向二/ADR-0433:成型后拆队卖(净效果破 form_ok)
    if star_weighted_copies(name, state) >= 2:
        return None    # 3合1 进行中素材/完整份不卖(AD9-2-3;ADR-0327)
    ch = CHARACTERS.get(name)
    cost = ch.cost if ch is not None and ch.cost else 3
    star = max(1, int(getattr(bc, 'star', 1) or 1))
    cp = star_weighted_copies(name, state)
    deployed_names = {getattr(d, 'char_id', '') for d in
                      (state.deployed or [])}
    absent_mergeable = (name not in deployed_names and cp >= 2)
    in_protect = 1 if (protect and name in protect) else 0
    redundancy = 0 if (cp > 3 or absent_mergeable) else 1
    loss = _sell_expected_loss(cost, reg)
    net0 = 0 if star == 1 else 1
    return (in_protect, redundancy, loss, net0, cost, star)


def sell_score_weight(cost: int,
                      registry: DecisionV2Registry) -> float:
    """卖分缩放权重(S5 评分侧;ADR-0327):w=sell_key_weight_scale×
    (1+min_loss)/(1+loss),封顶 1.0。

    净0 件(1费,min-loss 档)w=1、升星沉淀件(高再遇代价)w→小——
    只改同通道内卖件**相对序**,不改「卖不卖」的正分门槛
    (纯占位件 val=bias×w>0 仍可卖)。scale=1 即回退均一 bias(A/B)。
    """
    min_loss = min(_sell_expected_loss(c, registry)
                   for c in registry.remeet_window_rounds)
    loss = _sell_expected_loss(cost, registry)
    return min(1.0, registry.sell_key_weight_scale
               * (1.0 + min_loss) / (1.0 + loss))


def register_round_sold(names, state: GameState,
                        session: StrategySession) -> None:
    """卖出件入同轮已卖集(r408 对称臂;带轮键自校验,防跨轮误写)。

    四卖件通道统一走本 helper(设计 §4):carry_gate ④/两补偿器/
    arbiter 主循环(采纳处,ADR-0328)。
    """
    key = (state.plane, state.round_num)
    if getattr(session, 'v2_round_key', None) != key:
        return    # 轮键不匹配(跨轮误写防御;set 下轮重置)
    sold = getattr(session, 'v2_round_sold', None)
    if sold is None:
        session.v2_round_sold = sold = set()
    for n in names:
        if n:
            sold.add(n)


def register_round_bought(names, state: GameState,
                          session: StrategySession) -> None:
    """买入件入同轮已买集(r408 主臂;带轮键自校验,防跨轮误写)。

    ADR-0328 时序修复:登记点从 decide_prep 尾部(arbitrate 之后)
    前移到**动作采纳处**(同一事务域)——同趟 arbitrate 内先采纳
    BUY X 后,后续 SELL X(段首旧副本)候选的守卫立即可见
    (no_same_round_buy_sell 回归 96/400 的根因:r408 守卫读的是
    上一段已买集,同趟 buy+sell 双双过)。三买发射点统一走本
    helper:arbiter 主循环采纳/补偿趟受益买重发/carry_gate 腾位买。
    """
    key = (state.plane, state.round_num)
    if getattr(session, 'v2_round_key', None) != key:
        return    # 轮键不匹配(跨轮误写防御;set 下轮重置)
    bought = getattr(session, 'v2_round_bought', None)
    if bought is None:
        session.v2_round_bought = bought = set()
    for n in names:
        if n:
            bought.add(n)
