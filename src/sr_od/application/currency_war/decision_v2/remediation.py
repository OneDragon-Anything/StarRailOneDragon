"""决策框架 v2 纪律族补偿子模块(W52;ADR-0326 通用回连机制)。

「拒绝→补裁决」通用回连:层4 拒绝事件(资源型:金/bench/槽)结构化
捕获(``RejectReason``/``Rejection``)→ 同轮单趟定向补偿
(``remediation_pass`` 构造补偿动作组)→ arbiter 侧整组重验后追加
执行(事务性,防环)。

**定位 = 纪律族的补偿子模块**(与 discipline.py 同层同族,ADR-0326
方案 B 拓扑):import 方向单向——本模块 → discipline{保护集/弱序/
豁免谓词} + candidates{Candidate} + cw_state{Action 族};
**不 import arbiter**(Rejection 定义在本模块,arbiter 反向 import,
无环)。liquidity 旧债(discipline 里函数级 ``from arbiter import
_active_floor``)已随 S1 收编删除。

行为对照(口述原则,user_playstyle.md;每处行为判断的对照条目):
- [18] hp 低是报警不是触发:补偿的**触发器**=资源门槛事件(拒绝),
  不是 hp 数值;报警只在 ``DisciplineView.allow_refresh_in_war`` 里作
  辖域授权条件之一;
- [20]/[31] 过渡是配方不是散买:补偿卖序只卖**垫层/压库件**
  (``_compensate_gold``/``_compensate_bench`` 的边际羁绊贡献守卫,
  §0.6-① r3 修正),过渡配方正件不卖;
- [21] final 买而不上:金补偿只管买(remedy_buy_tags 辖域),零涉及
  上场管线;
- [22] 净0 件最先卖(1星卖出全额退≈净0)是补偿卖序的依据;
  [22]② bench 槽稀缺由 S6(``_compensate_bench`` 腾位)闭环。
"""
from __future__ import annotations

from dataclasses import dataclass

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_intention import IntentionState
from sr_od.application.currency_war.cw_state import (
    Action,
    BuyCard,
    DeployMove,
    GameState,
    LevelUp,
    RefreshShop,
    SellBench,
    SwapDeploy,
    bench_occupied,
    sell_refund,
)
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.candidates import Candidate
from sr_od.application.currency_war.decision_v2.discipline import (
    _char_bonds,
    _line_protect_set,
    engine_char_names,
    register_round_sold,
    seed_age_blocked,
    sell_priority_key,
    star_weighted_copies,
)
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)

# 补偿路由键 → 处理序(金是另两维共同上游;每轮只处理首个可补偿维)
_RESOURCE_ORDER: dict[str, int] = {'gold': 0, 'bench': 1, 'slot': 2}


@dataclass(frozen=True)
class RejectReason:
    """结构化拒绝原因(层4 产出;``describe`` 兼容既有 log 格式)。

    - ``constraint``:约束名('gold_floor'|'bench_capacity'|'deploy_cap'
      资源型;纪律型拒绝也带自己的约束名,resource='');
    - ``resource``:补偿路由键('gold'|'bench'|'slot';纪律型='');
    - ``shortfall``:gold=还差几金;bench=缺几槽(恒≥1);slot=缺几个
      上阵位(恒≥1);纪律型=0;
    - ``describe``:人读原因(旧裸 str 拒绝原因的语义原样迁移,log 行
      格式不变——``f'{constraint}:{describe}'``)。
    """

    constraint: str
    resource: str
    shortfall: int
    describe: str


@dataclass(frozen=True)
class Rejection:
    """一条资源型拒绝(补偿的受益动作引用 + 分)。

    - ``cand``:被拒候选(补偿的受益动作;refresh 拒的 cand 即 refresh
      候选——N2 捕获点②);
    - ``score``:被拒候选分(补偿门槛输入,remedy_min_score 消费)。
    """

    reason: RejectReason
    cand: Candidate
    score: float


def _describe_action(a: Action) -> str:
    """补偿动作人读描述(log schema 的 ``actions`` 元素)。

    **本模块不 import arbiter**(ADR-0326 拓扑),故 arbiter._describe
    的短格式在此本地复刻(判读格式一致;两处均为 log 只读面)。
    """
    if isinstance(a, BuyCard):
        return f'买 {a.card.name}({a.card.cost}费)'
    if isinstance(a, SellBench):
        return f'卖 bench[{a.bench_idx}]'
    if isinstance(a, LevelUp):
        return f'买经验×1(-{a.cost}金)'
    if isinstance(a, RefreshShop):
        return f'刷新(-{a.cost or 2}金)'
    if isinstance(a, SwapDeploy):
        return (f'换位 d{a.deployed_idx}↔b{a.bench_idx}'
                f'({a.expect_deployed}/{a.expect_bench})')
    return str(a)


def _benefit_desc(rej: Rejection) -> str:
    """受益动作人读描述(arbiter._describe 同格式的本地复刻)。"""
    a = rej.cand.action
    if isinstance(a, BuyCard):
        return f'买 {a.card.name}({a.card.cost}费)'
    if isinstance(a, RefreshShop):
        return f'刷新(-{a.cost or 2}金)'
    if isinstance(a, LevelUp):
        return f'买经验(-{a.cost}金)'
    return str(a)


def remediation_pass(working: GameState, state: GameState,
                     session: StrategySession,
                     registry: DecisionV2Registry,
                     rejections: list[Rejection],
                     disc_view=None,
                     floor: int = 0,
                     ) -> tuple[list[Action], list[dict]]:
    """拒绝→补裁决主入口(同轮单趟;arbitrate 末段调用)。

    只构造补偿动作组与日志(§1.1 schema),**不做最终重验**——重验由
    arbiter 侧在 working 上逐动作 _check_constraint+simulate、受益候选
    最后重验完成。动作组内部序=卖先于买/换(资金/槽位先到位,carry_gate
    同序)。每轮每资源维至多一批(防环见 §1.5)。

    ``disc_view``:纪律族视图(arbitrate 传入;S2 报警 refresh 辖域消费);
    ``floor``:本轮生效地板(arbiter 侧已算;remediation 不 import arbiter
    ——地板经参传入,拓扑无环,ADR-0326 方案 B)。
    """
    if not rejections:
        return [], []
    # 资源维处理序:gold → bench → slot(金是另两维共同上游);每轮只
    # 处理首个可补偿维(1c 金+槽叠加态跨轮消化,显式声明——补偿是
    # 救急不是重规划,§1.4 末段)。
    ordered = sorted(rejections, key=lambda r: _RESOURCE_ORDER.get(
        r.reason.resource, 9))
    rej = ordered[0]
    resource = rej.reason.resource
    if resource == 'gold':
        acts = _compensate_gold(working, state, session, registry, rej,
                                disc_view, floor)
    elif resource == 'bench':
        acts = _compensate_bench(working, state, session, registry, rej)
    elif resource == 'slot':
        acts = _compensate_slot(working, state, session, registry, rej)
    else:
        return [], []    # 纪律型拒绝不进回连(§1.1 捕获条件)
    if not acts:
        return [], []    # 弱序降级链尽头:无可卖/可换件 → 放弃(§1.5-5)
    rlog = [{
        'kind': resource,
        'benefit_tag': rej.cand.tag,
        'benefit_desc': _benefit_desc(rej),
        'actions': [_describe_action(a) for a in acts],
        'outcome': 'done',
        'reason': '',
    }]
    return acts, rlog


def _marginal_bond_contribution(bc, state: GameState) -> bool:
    """边际羁绊贡献守卫(r3,§0.6-①修正;ADR-0326):bc 与当前板面
    (board 阵营)能凑羁绊 → True(过渡配方正件,不进补偿卖序)。

    判定=[31] 填充选择标准的对偶:与 board 阵营能凑羁绊的件不卖,
    卖的只能是垫层/压库件([20]「过渡阵容是 P1 通关阵容本身」——
    拆配方换囤货违反 [20]/[21])。board 为空的冷启动:无贡献判定,
    所有件均可入卖序(此时无配方可拆)。
    """
    bonds = _char_bonds(getattr(bc, 'char_id', '') or '',
                        getattr(bc, 'faction', '') or '')
    if not bonds:
        return False
    return bool(bonds & set((state.board or {}).keys()))


def _compensate_gold(working: GameState, state: GameState,
                     session: StrategySession,
                     registry: DecisionV2Registry, rej: Rejection,
                     disc_view=None, floor: int = 0) -> list[Action]:
    """gold_floor 拒 → 降保护集卖压库件凑金(liquidity_actions 语义收编,S1)。

    辖域:remedy_buy_tags 的买 + (disc_view.allow_refresh_in_war 且
    remedy_alarm_refresh 时)报警升级态的 refresh(S2 残余);
    守卫全量继承 liquidity:保护集(_line_protect_set;无锁定意向=引擎件)
    /r408 已买/种子年龄窗/3合1 完整份/未知费级;
    **边际羁绊贡献守卫(r3,§0.6-①修正)**:bc 对当前板面(deployed/board
    阵营)边际羁绊贡献>0 → 跳过——过渡配方正件([20]「P1 通关阵容
    本身」)不进补偿卖序,卖的只能是垫层/压库件;
    **压库量回吐对照(§0.6 补,[30]/[15] 非量化声明)**:补偿卖压库件
    = 成本带压库量([30] 买光本带/池共享压缩 [15])的回吐——买入动机
    (压库)与卖出动机(变现)同件两用;回吐量随卖出发生,本补偿器
    **不做量化记账**(压库是全局供给策略的统计效应,单件回吐不可归因);
    **触发源修正(§5,ADR-0326)**:缺口按 ``working.gold``(层4 真缺口,
    同轮已采纳买已扣)而非 ``state.gold``(层3 预测)——同轮已有采纳
    买消耗金时旧版多卖、新版按真缺口少卖;
    不足额整体放弃;凑够即停(卖最少件数)。发射的 SellBench 索引
    = ``state.bench`` 槽位下标(原始快照,ADR-0316 索引稳定;working
    占用守卫防陈旧提案)。
    """
    a = rej.cand.action
    if rej.score <= registry.remedy_min_score:
        return []    # 只救高价值买(§1.3 remedy_min_score 下沿)
    if isinstance(a, BuyCard):
        if a.card.name in (getattr(session, 'v2_round_sold', None) or ()):
            return []    # r408:同轮已卖不回买(振荡结构禁止,§1.5-4)
        if rej.cand.tag not in registry.remedy_buy_tags:
            return []    # 不为非目标件变现(§1.3 remedy_buy_tags 辖域)
        cost = a.card.cost or 3
        buy = a.card
    elif isinstance(a, RefreshShop):
        # S2 残余(§2):报警升级态 refresh 金拒才补偿(不为常态刷新借钱)
        if not (registry.remedy_alarm_refresh
                and disc_view is not None
                and getattr(disc_view, 'allow_refresh_in_war', False)):
            return []
        cost = a.cost or 2
        buy = None
    else:
        return []
    # 资源判定用 working(真缺口;触发源修正 §5)
    shortfall = floor + cost - working.gold
    if shortfall <= 0:
        # 金已在同轮被后续采纳的卖补齐(受益候选最终 working 不再金
        # 拒)——重试受益候选本身(不带卖件;§1.2 回连目的=「被拒动作
        # 获得资源后重试」;受益候选最终重验在 arbiter 侧完成)。
        # 「先采纳卖→金足→无补偿」(W56 攻击面 3)的另一面:卖先于买
        # 被采纳时买候选直接通过、无拒绝事件,本分支不触发。
        if buy is not None:
            return [BuyCard(buy, reason='d2_' + rej.cand.tag)]
        return []
    ist = getattr(session, 'v3_intention', None)
    comp = None
    if isinstance(ist, IntentionState) and ist.phase == 'locked':
        from sr_od.application.currency_war.cw_comps import get_comp
        comp = get_comp(ist.locked_comp)
    protect = _line_protect_set(comp) if comp is not None \
        else set(engine_char_names())
    buy_name = buy.name if buy is not None else ''
    sellable: list[tuple[tuple, int, int]] = []
    for i, b in enumerate(state.bench or []):
        if b is None or not b.char_id or b.char_id == buy_name:
            continue
        # working 占用守卫:同槽在 working 已被前序动作消费(卖出置
        # None/买入占位)→ 跳过——陈旧提案/双重卖防御(事务性兜底
        # 在 arbiter 重验层,此处提前过滤更省)
        wb = (working.bench[i]
              if 0 <= i < len(working.bench or []) else None)
        if wb is None or wb.char_id != b.char_id:
            continue
        if b.char_id in protect:
            continue
        if _marginal_bond_contribution(b, state):
            continue    # 边际羁绊贡献守卫(r3):过渡配方正件不卖
        ch = CHARACTERS.get(b.char_id)
        if ch is None or not ch.cost:
            continue    # 未知费级回金不可估,不入变现序
        # 统一弱序(S5/ADR-0327):r408/种子年龄/加权副本≥2(AD9-2-3)
        # 由键统一挡(None);净0 件最先 → 低费散件 → 升星沉淀件
        key = sell_priority_key(b, state, session, protect, registry)
        if key is None:
            continue
        star = getattr(b, 'star', 1) or 1
        refund = sell_refund(star, ch.cost)
        sellable.append((key, i, refund))
    sellable.sort(key=lambda s: s[0])
    sells: list[SellBench] = []
    got = 0
    for _key, idx, refund in sellable:
        if got >= shortfall:
            break
        # §1.7 硬规范(ADR-0326):SellBench.expect 从候选生成时的
        # state 快照取名(禁从 working 取——working 已被同批先行动作
        # 改变,取 working 名=校验恒过,防线失效)
        _nm = state.bench[idx].char_id if state.bench[idx] is not None \
            else ''
        sells.append(SellBench(bench_idx=idx, income=refund,
                               expect=_nm))
        got += refund
    if got < shortfall:
        return []    # 变现不足额 → 整体放弃(不卖一半,事务性 §1.5-3)
    for s in sells:
        nm = state.bench[s.bench_idx].char_id
        if nm:
            register_round_sold([nm], state, session)   # r408 对称臂
    if buy is not None:
        benefit = f'买 {buy.name}'
        tail = BuyCard(buy, reason='d2_' + rej.cand.tag)
    else:
        benefit = '刷新'
        tail = RefreshShop(cost=cost)
    log.info('[cw][d2][remedy] r%d 金补偿 %d 件凑金 %d %s(%s)',
             state.round_num, len(sells), shortfall, benefit,
             rej.cand.tag)
    return [*sells, tail]


def _compensate_bench(working: GameState, state: GameState,
                      session: StrategySession,
                      registry: DecisionV2Registry, rej: Rejection,
                      ) -> list[Action]:
    """bench_capacity 拒(非 merge 候选)→ 腾位卖+重试买(S6)。

    容量判据=占用计数(bench_occupied,§0.5——len(bench) 在槽位模型下
    恒 9);腾位卖件选择=与 ``_compensate_gold`` 同 sellable 集
    (**保护集与边际羁绊贡献守卫取并集挡**:配方正件([20]「P1 通关阵容
    本身」)与意向线正料两条线都不可卖——守卫与保护集并集,双线齐挡
    的件才是真正钉死)+ r408/种子年龄/3合1 完整份/未知费级;
    选最弱件(弱序=carry_gate ④ 同式的简化:冗余/absent_mergeable 最弱
    → 同档按 cp → 费 → 星;种子单列兜底——bench 真满且唯一可卖=种子
    时豁免,防买死锁,同 carry_gate);
    不辖 P1 r≤7/carry 在店(那是 carry_gate 专用门的前置域——本补偿
    是 carry_gate 之外的兜底,S6)。
    """
    a = rej.cand.action
    if not isinstance(a, BuyCard):
        return []
    if rej.score <= registry.remedy_min_score:
        return []
    if a.card.name in (getattr(session, 'v2_round_sold', None) or ()):
        return []    # r408:同轮已卖不回买
    if rej.cand.tag not in registry.remedy_buy_tags:
        return []    # 不为非目标件腾位
    # 工作态占用(槽位模型下 len 恒 9;容量判据=占用计数 §0.5):
    # 缺槽数 = 占用 − 容量 + 1;占用 < 容量 = 槽位已被同轮采纳
    # 卖/上阵腾出 → 重试受益买(不带卖件,§1.2 回连目的=「被拒动作
    # 获得资源后重试」;受益候选最终重验在 arbiter 侧完成)。
    occupied = bench_occupied(working.bench or [])
    if occupied < registry.bench_capacity:
        return [BuyCard(a.card, reason='d2_' + rej.cand.tag)]
    need = max(1, rej.reason.shortfall or 1)   # 缺几槽(恒≥1)
    ist = getattr(session, 'v3_intention', None)
    comp = None
    if isinstance(ist, IntentionState) and ist.phase == 'locked':
        from sr_od.application.currency_war.cw_comps import get_comp
        comp = get_comp(ist.locked_comp)
    protect = _line_protect_set(comp) if comp is not None \
        else set(engine_char_names())
    cands: list[tuple[tuple, int, int]] = []
    seed_cands: list[tuple[tuple, int, int]] = []
    for i, b in enumerate(state.bench or []):
        if b is None or not b.char_id or b.char_id == a.card.name:
            continue
        wb = (working.bench[i]
              if 0 <= i < len(working.bench or []) else None)
        if wb is None or wb.char_id != b.char_id:
            continue    # working 占用守卫(防陈旧提案/双重卖)
        if b.char_id in protect:
            continue    # 保护集挡(并集线 1)
        if _marginal_bond_contribution(b, state):
            continue    # 边际羁绊贡献守卫(并集线 2):配方正件不卖
        ch = CHARACTERS.get(b.char_id)
        if ch is None or not ch.cost:
            continue    # 未知费级
        star = getattr(b, 'star', 1) or 1
        refund = sell_refund(star, ch.cost)
        # 统一弱序(S5/ADR-0327):r408/加权副本≥2(AD9-2-3)/未识别由键
        # 统一挡;种子单列兜底(唯一可卖=种子时豁免,防买死锁,同 carry)
        if seed_age_blocked(b, state, session):
            cp = star_weighted_copies(b.char_id, state)
            key = (1, 0 if cp > 3 else 1, cp, ch.cost, star)
            seed_cands.append((key, i, refund))
            continue
        key = sell_priority_key(b, state, session, protect, registry)
        if key is None:
            continue
        cands.append((key, i, refund))
    if not cands:
        cands = seed_cands   # 唯一可卖=种子:死锁豁免(仍选最弱)
    cands.sort(key=lambda c: c[0])
    sells: list[SellBench] = []
    for _key, idx, refund in cands:
        if len(sells) >= need:
            break
        # §1.7 硬规范(ADR-0326):expect 从 state 快照取名(禁 working)
        _nm = state.bench[idx].char_id if state.bench[idx] is not None \
            else ''
        sells.append(SellBench(bench_idx=idx, income=refund,
                               expect=_nm))
    if len(sells) < need:
        return []    # 无可卖件/不足 → 整组放弃(§1.5-5)
    for s in sells:
        nm = state.bench[s.bench_idx].char_id
        if nm:
            register_round_sold([nm], state, session)   # r408 对称臂
    log.info('[cw][d2][remedy] r%d 腾位 %d 槽卖 %d 件买 %s(%s)',
             state.round_num, need, len(sells), a.card.name,
             rej.cand.tag)
    return [*sells, BuyCard(a.card, reason='d2_' + rej.cand.tag)]


def steady_state_levelup_group(working: GameState, state: GameState,
                               session: StrategySession,
                               registry: DecisionV2Registry,
                               ) -> list[Action]:
    """[33] 稳态 LevelUp 多击组(W194/ADR-0378;W185 泛化方向 1 落地)。

    触发面从「轮内 deploy_cap 拒绝」解耦——W185 实证该触发器结构性
    失活(``select_deployments`` 在 deployed≥cap 时把全部 bench 件归
    held → 无部署候选 → deploy_cap 拒绝不发生 → 多击组永不触发,
    Catch-22:恰是升级最该提速的稳态没有任何触发器)。本函数按
    [33] 稳态字面语义主动授权:

    - **稳态判据**(进轮快照 ``state``,与 levelup_ev_basis 人口位臂
      同源):**plane ≥ 2**(辖域限 P2+——P1 的多击通道已由
      deploy_cap 补偿臂覆盖(W185 run16 p1r7 形态),全位面泛化在
      n=300 引入 never2 9→10 回归,W194 辙回)+ cap 满
      (deployed ≥ max_units)∧ bench 有方向件(∈ ``_target_names``:
      意向骨架/引擎件)——「进轮时已满员 + 目标件躺 bench 等位」
      ([33]:刷出框架单位 → 花金升级 → 让它上场,升级的触发时机
      包含「有框架单位等着上场」);
    - 前置守卫与 ``_compensate_slot`` 臂① 全同:非 boss 轮
      ([32] 禁升)、level < level_max、cap 由 level 驱动
      (deploy_cap 真值 > level 时升级不抬 cap);
    - 组 = [LevelUp]*n,n=clicks_to_next_level(从 ``working``
      xp_progress 现算——同轮主通道已采纳的单击计入后取余量);
    - 授权 = ``levelup_ev_basis`` 按 n×总价单次判(稳态下人口位臂
      天然成立;可负担性 after≥0 入口门),auth_basis 写入每个
      LevelUp(ADR-0354 观测,与补偿臂同构);
    - 金/资源事务性重验在 arbiter 侧(逐动作 _resource_blocked +
      simulate,与补偿组同一重验链——本函数只构造不重验,
      ``remediation_pass`` 同款契约)。

    纯构造无副作用;不满足判据返回 []。
    """
    if not registry.levelup_multihit_enabled:
        return []
    if state.plane < 2:
        return []    # 辖域 P2+(W194 裁决:P1 回归辙回,见 docstring)
    # 稳态判据(进轮快照,与 ev.levelup_ev_basis 臂① 的 state 读点同源)
    from sr_od.application.currency_war.cw_state import bench_occupied
    if len(state.deployed or []) < state.max_units():
        return []    # cap 未满:方向件直接上场即可([32](b) 升级纯浪费)
    if bench_occupied(state.bench or []) == 0:
        return []
    from sr_od.application.currency_war.decision_v2.candidates import (
        _target_names,
    )
    if not any(b is not None and b.char_id in _target_names(state, session)
               for b in (state.bench or [])):
        return []    # bench 无方向件:非 [33] 人口位形态
    # 前置守卫(_compensate_slot 臂① 同款)
    from sr_od.application.currency_war.decision_v2.discipline import (
        boss_window_active,
    )
    from sr_od.application.currency_war.decision_v2.ev import (
        levelup_ev_basis,
    )
    boss = boss_window_active(state, session, registry)
    cap_level_driven = (state.deploy_cap is None
                        or state.deploy_cap <= state.level)
    if boss or state.level >= registry.level_max or not cap_level_driven:
        return []
    from sr_od.application.currency_war.cw_economy import xp_click_cost
    from sr_od.application.currency_war.cw_state import (
        XP_PER_BUY as _XP_PER_BUY,
    )
    from sr_od.application.currency_war.cw_state import (
        XP_TO_NEXT_LEVEL as _XP_TO_NEXT_LEVEL,
    )
    cost = xp_click_cost(state)
    _xp = working.xp_progress or (0, 1)
    _cur = _xp[0] if _xp else 0
    _need = _XP_TO_NEXT_LEVEL.get(working.level, _XP_PER_BUY * 2)
    remain = max(0, _need - _cur)
    if remain <= 0:
        return []    # 已跨级(simulate 清零结转)——无余量可补
    n = -(-remain // _XP_PER_BUY)
    total = n * cost
    _basis = levelup_ev_basis(
        state, session, registry, working.gold, total,
        _target_names(state, session))
    if not _basis:
        return []    # EV 总账拒([12]/可负担性;[18] hp 不作触发器)
    log.info('[cw][d2][steady-lv] r%d 稳态多击组 %d 击(-%d金,%s)',
             state.round_num, n, total, _basis)
    return [LevelUp(cost=cost, auth_basis=_basis) for _ in range(n)]


def _compensate_slot(working: GameState, state: GameState,
                     session: StrategySession,
                     registry: DecisionV2Registry, rej: Rejection,
                     ) -> list[Action]:
    """deploy_cap 拒(持件上场)→ ①评估 LevelUp ②弱件换上(S4/D3 裁决)。

    ①(H2,r2 重写:LevelUp=单击+XP_PER_BUY 经验,非升 1 级,cw_state:34/
      ADR-0129;执行层逐动作独立应用,无节流/去重——§9.6 已核):n 次
      点击整组——n=ceil(剩余XP/XP_PER_BUY)(剩余XP=升 1 级所需-当前
      级内进度,读 state.xp_progress);整组=[LevelUp]*n(LevelUp.cost=
      单击花金,总价=n×单价);**整组事务性重验**(arbiter 侧重验
      gold_floor 按 n×总价;boss 轮判定(boss_window_active 统一口径)
      与息引擎门(ev.levelup_ev_authorized,W119/ADR-0347 总账化)
      在本函数前置守卫);非 boss 轮才发;cap 由 level
      驱动才发(deploy_cap 真值绑定>level 时升级不抬 cap,改走 ②)。
      cap+n 次点击后才 +1,下轮起部署管线自然消化;受益 DeployMove
      本轮仍拒——显式注释「升级解的是下轮」,不假装同轮通(设计 §9-2);
    ②否则 SwapDeploy:场上最弱(deployed 中非 target_cores/非引擎件,
      弱序=(star, cost)升序,与填位优先级同源——v4 点11 leader 裁决
      「满员侧:弱件换上,优先级同填位」)↔ 被拒上场的 bench 件;
    两者互斥,①优先(升级不损件)。SwapDeploy 带 expect 代际校验
      (§1.7:从候选生成时 state 快照取名,防陈旧提案)。
    """
    a = rej.cand.action
    if not isinstance(a, DeployMove):
        return []
    ben_idx = a.bench_idx
    in_char = (state.bench[ben_idx]
               if 0 <= ben_idx < len(state.bench or []) else None)
    if in_char is None:
        return []
    # ① LevelUp 臂(优先:升级不损件;H2 n 次点击整组)
    from sr_od.application.currency_war.decision_v2.candidates import (
        _target_names,
    )
    from sr_od.application.currency_war.decision_v2.discipline import (
        boss_window_active,
    )
    from sr_od.application.currency_war.decision_v2.ev import (
        levelup_ev_basis,
    )
    boss = boss_window_active(state, session, registry)
    cap_level_driven = (state.deploy_cap is None
                        or state.deploy_cap <= state.level)
    if not boss and state.level < registry.level_max \
            and cap_level_driven:
        from sr_od.application.currency_war.cw_economy import xp_click_cost
        from sr_od.application.currency_war.cw_state import (
            XP_PER_BUY as _XP_PER_BUY,
        )
        from sr_od.application.currency_war.cw_state import (
            XP_TO_NEXT_LEVEL as _XP_TO_NEXT_LEVEL,
        )
        cost = xp_click_cost(state)
        _xp = state.xp_progress or (0, 1)
        _cur = _xp[0] if _xp else 0
        _need = _XP_TO_NEXT_LEVEL.get(state.level, _XP_PER_BUY * 2)
        n = max(1, -(-(max(0, _need - _cur)) // _XP_PER_BUY))
        total = n * cost
        # 息引擎门 → EV 总账(W119/ADR-0347,A2 镜像清:ev.levelup_ev_
        # authorized 单一裁决,[33] 人口位/DP 花费授权;按 n×总价口径
        # ——设计 H2 整组事务性重验。补偿路径无层3 分,V 侧只有 ①②
        # 两路可授权——满员换位场景 bench 有等上场件,[33] 常真)
        _basis = levelup_ev_basis(
            state, session, registry, working.gold, total,
            _target_names(state, session))
        if _basis:
            # gold_floor 按 n×总价的逐动作重验在 arbiter 侧(每组动作
            # 各自 _check_constraint+simulate);受益 DeployMove 本轮仍拒
            # (升级解的是下轮——cap+n 次点击后才 +1,下轮部署管线消化)
            # auth_basis=授权依据观测(ADR-0354):整组同一臂(前置守卫
            # 按 n×总价一次判);记录非指令,行为零改动。
            return [LevelUp(cost=cost, auth_basis=_basis)
                    for _ in range(n)]
    # ② SwapDeploy 臂:场上最弱(deployed 中非 target_cores/非引擎件,
    # 弱序=(star, cost)升序,与填位优先级同源)↔ 被拒上场的 bench 件
    tc = getattr(session, 'target_comp', None)
    t_core = set(getattr(tc, 'core_chars', None) or ()) if tc else set()
    eng = set(engine_char_names())
    out_cands: list[tuple[int, int, int]] = []
    for di, d in enumerate(state.deployed or []):
        name = getattr(d, 'char_id', '') or ''
        if name in t_core or name in eng:
            continue
        c = CHARACTERS.get(name)
        out_cands.append(((getattr(d, 'star', 1) or 1),
                          c.cost if c is not None else 9, di))
    if not out_cands:
        return []    # 无可换弱件 → 放弃(§1.5-5)
    out_cands.sort(key=lambda x: (x[0], x[1], x[2]))
    d_idx = out_cands[0][2]
    out_char = state.deployed[d_idx]
    # 「换上不优不换」(§7 反例):被拒上场的 bench 件弱于/等于场上最弱
    # 可换件 → 换上是降级,无动作(填位优先级语义的保守侧)
    _in_c = CHARACTERS.get(in_char.char_id)
    _in_cost = _in_c.cost if _in_c is not None else 9
    _out_c = CHARACTERS.get(out_char.char_id)
    _out_cost = _out_c.cost if _out_c is not None else 9
    if (getattr(in_char, 'star', 1) or 1, _in_cost) \
            <= (getattr(out_char, 'star', 1) or 1, _out_cost):
        return []
    # 同名唯一性守卫(W43 裁决 1):上场者与场上其余单位同名 → 换不上,
    # 放弃(swapped 后 duplicate_on_board 会整动作拒)
    from sr_od.application.currency_war.cw_state import board_unique_key
    _k = board_unique_key(in_char)
    if _k is not None and any(
            board_unique_key(d) == _k
            for i, d in enumerate(state.deployed or []) if i != d_idx):
        return []
    log.info('[cw][d2][remedy] r%d 满员换位:deployed[%d] %s ↔ '
             'bench[%d] %s', state.round_num, d_idx,
             out_char.char_id, ben_idx, in_char.char_id)
    return [SwapDeploy(d_idx, ben_idx, reason='remedy_slot',
                       expect_deployed=out_char.char_id,
                       expect_bench=in_char.char_id)]
