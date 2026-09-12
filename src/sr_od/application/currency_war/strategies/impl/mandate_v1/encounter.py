"""遭遇分支选卡判据(E3 奖励侧候选模型落码;判据语义单一源 = ADR-0536)。

落码形态(ADR-0536 §2,前身为不入库设计稿 v2 的收编件):对实际读到的
每个分支 b:

    EV(b) = V_r(r_b) − Δλ_death(b)·G_loss

P26 备战 EV 门同构(奖励增量 vs λ_death 敞口增量),λ 项按 P51 折现
口径入负项(W_floor = λ×(存量金 g+未来纯金流),区间敞口比较合法形态)。

- V_r 子型分立(按实例对评估,子型与难度档独立组合——金子型在高难支
  实录在案 exogenous event_choice 帧;文本匹配经 ``str_utils.find_by_lcs``
  相似匹配容 OCR 变体,裸子串误分型会污染未立分键判读):
  * 随机 4 费角色×3 ⇒ V_r = 3×``cw_state.sell_refund(1★, 4费)`` = 12
    (清算下界:1★ 全额退随时可得,P41;持有增值 fail-closed 不计);
  * 金币×2 ⇒ V_r = provisional 槽 ``ENCOUNTER_G_GOLD``(金币×2 金额,
    观察值挂采——exogenous event_choice 单例 +8,另有 ["10"] 读数两帧
    OCR 存疑;定带 = 先判读历史帧再开新采集,≥3 局观察值后注入标定值。
    **None 期金币支 V_r 未立**(未立 ≠ 0),数值开闸 = 本槽与
    ``ENCOUNTER_DSTAT_MAP`` 双槽都注入(ADR-0536 §3:双槽互锁防半标定
    全开闸——只注 dstat 时金币支未立 → fail 向,「12>8 ⇒ 高难更优」
    结论不会在 G_gold 定带前产出);
  * 其余子型(随机 5 费角色/员工投影仪/读空)在册未建模 ⇒ V_r 未立
    (5 费子型有独立下界形态 3×sell_refund(1★,5费)=15,标定轮首扩展
    对象;未立 ≠ 0,禁置零续比)。
- λ 项(P51 折现口径入形;数值 fail-closed):负项 = ``lambda_death.
  differential_composite``(第三口唯一合法数值算子,d̂ = 同格 CI 宽度,
  敞口 = 存量金 g + Ī×R_剩余——P51 §R.1「存量金核心」;区间敞口比较
  合法形态 = P51 §5-11)。**金缺读帧 fail-closed**(``gold_readable``
  False = 缺读兜底 0 非真值,禁进敞口——0 会压薄 λ 项、方向与保守
  相反)。分支 λ 键需要敌难度**真值**(stat 值,带界 108)而卡面只有
  旗牌 1-6,旗牌→stat 映射未标定 ⇒ 键观测量缺失 = 域外同判(R29-6
  同款:禁产假真值),经 provisional 槽位 ``ENCOUNTER_DSTAT_MAP`` 供给,
  None 期 fail-closed。
- **λ label 四态接死(ADR-0536 §2-③)**:「不可判」≡ 任一分支 λ 键为
  None/域外/损坏态,或格 label ≠ 可消费(空格/禁用/仅方向)⇒ **放弃
  argmax、整体 fail 向选低难度支**;「负项置零继续比较」是禁止实现
  (其产出与设计申报的现态行为相反)。仅方向格只作方向注记不决胜负。
- fail 向 = 选低难度支(并列取先读支),保守 = 少掉血方向;与现行
  「未成型→低难保生存」零冲突(未成型帧动作序列 diff 空);formed 态
  dare→高难帧被 fail 向覆盖 = 判据接线的预期差(验收门按动作序列级)。
- 刷新肢(ADR-0536 §2-④):分支刷新**不是免费期权**——生产执行链语义
  是刷新生效后原对弃用、强制从重掷对中选(cw_screen_encounter :95-101/
  :144-155),重掷分布未建模、期望可为负。故仅当双支 λ 可消费、EV 比较
  存在但**不稳健**(保守端 d̂=CI 宽度与乐观端 d̂=0 给出不同胜者 = EV 差
  落入不可判带)时,才作探索性建议(refresh=True);λ 整体不可判帧不刷新
  (fail 向已知安全选项,重掷可能更差不赌)。**EV 精确并列**(双支 V_r
  与复合项全等)走并列出口 fail 向(决策树第 5 肢),不构成胜者翻转、
  不给刷新(三审定谳:并列曾误入翻转支,同难度双卡帧标定后可触发)。
- 零 hp 直读自变量(00 §3):hp 只入 λ 路由键(P51 hp 入路由键、不入
  金流,裁定二),不进任何数值运算;不建胜率阶梯、不评单位强弱、分支
  间 argmax 不新增排序键。

现态行为申报与验收口径(ADR-0536 §4):现态生产 = 双槽 None 期恒
fail 向选低难、**零刷新建议**(刷新建议结构性不可触发:其前置 = 双支
λ 可消费 + 胜者翻转,双槽 None 期不成立;标定注入后亦仅在窄域可观测,
作条件触发观察位,验收勿按「应见到刷新建议」判接线)。

遥测分键(state_of(session).cw4_counters,与骨架 pass 计数同容器):
encounter_ev_fail_low(总出口)/ encounter_ev_fail_low_tie /
encounter_ev_pick / encounter_ev_fail_low_lambda_undecidable /
encounter_ev_fail_low_reward_unmodeled /
encounter_ev_undecidable_band_flip / encounter_ev_refresh_suggested /
encounter_ev_reward_gold / encounter_ev_reward_4fee /
encounter_ev_lambda_direction_note。拒因串经 ``EncounterPick.reason``
透传至既有 ``record_event_choice``(event_choice)账本,拒因串从难度
评分格式改为 EV 拒因格式 = 预期遥测差(ADR-0536 §2)。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils import str_utils
from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    EncounterPick,
)
from sr_od.application.currency_war.kernel.cw_economy import sell_refund
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.lambda_death import (
        ExposureComposite,
        LambdaCell,
    )

# 4 费件招募费档(注册表 CHARACTERS cost=4 档;清算下界的乘数输入)
FEE4_COST: int = 4

# 子型识别:家族关键词经 find_by_lcs 相似匹配(0.7 容单字 OCR 误读)。
# 4/5 费同属「随机X费角色」家族(LCS 分不开仅一字之差的两关键词,故合并
# 家族面),档位再抽「数字+费」正则定——档位数字缺失按未立 fail-closed,
# 禁猜档。金币独立关键词(2 字,1.0 = 两字全须在场,误读落 other=未立)。
_REWARD_FAMILY_KEYWORDS: tuple[tuple[str, str, float], ...] = (
    ('fee', '随机4费角色', 0.7),
    ('fee', '随机5费角色', 0.7),
    ('gold', '金币', 1.0),
)


@dataclass(frozen=True)
class _BranchEval:
    """单分支判据求值中间物(决策树一节点的求值快照,内部面)。

    label 四态取值与 ``lambda_death.LambdaCell.label`` 同词表:
    可消费 / 仅方向 / 禁用 / 空格;``undecidable_why`` 记非可消费格的
    具体态(或 key None=域外/观测量缺失),fail 向拒因透传用。
    """

    option: EncounterOption
    reward_kind: str
    reward_value: int | None
    lam_label: str | None
    undecidable_why: str | None
    composite: ExposureComposite | None    # 不透明 λ 敞口项(可消费格)


def _g_gold_observed() -> int | None:
    """金币×2 金额读口(provisional 槽 ``ENCOUNTER_G_GOLD``;None=未定带)。

    为什么经槽位而非代码常量:金额是观察值(单例)非机制定义,数值开闸
    须过「≥3 局观察值定带」判据;槽位 None 期金币支 V_r 未立(fail 向),
    与 dstat 槽构成双槽互锁(ADR-0536 §3),防「只注 λ 侧映射即半标定
    全开闸、单例金额进承重比较位」的越线形态。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
        provisional,
    )
    v = provisional.get('ENCOUNTER_G_GOLD')
    return None if v is None else int(v.value)


def reward_subtype_value(rewards: list[str],
                         g_gold: int | None) -> tuple[str, int | None]:
    """奖励文本 → (子型, V_r)。子型与难度档独立组合,按实例对评估。

    未建模/未定带子型 V_r = None(未立 ≠ 0:置零续比 = 禁止实现形态)。
    文本匹配 = ``str_utils.find_by_lcs`` 相似匹配(关键词 vs OCR 文本;
    4/5 费档位再经「数字+费」正则定档,LCS 分不开仅一字之差的 4费/5费;
    档位数字缺失按未立 fail-closed,禁猜档)。
    """
    text = ''.join(rewards)
    for kind, keyword, percent in _REWARD_FAMILY_KEYWORDS:
        if not str_utils.find_by_lcs(keyword, text, percent):
            continue
        if kind == 'fee':
            m = re.search(r'([1-9])费', text)
            if m is None or int(m.group(1)) not in (4, 5):
                return 'fee', None      # 家族在场、档位不可辨:未立,禁猜档
            tier = int(m.group(1))
            if tier == 5:
                # 5 费:在册实录、**未入树**(ADR-0536 §5 辖域外,标定轮
                # 首扩展对象)⇒ V_r 恒未立,即便其独立下界形态可算
                # (3×sell_refund(1,5)=15)——子型授权面扩展须过标定批,
                # 禁在判据内顺手开闸。
                return '5fee', None
            # 4 费清算下界(全类成立:1★ 全额退随时可得,P41/sell_refund
            # 注册表直调;持有增值 fail-closed 不计——线内增值只进未计量
            # 上行侧)。件数恒 3(「随机4费角色×3」),档位只进单件清算价。
            return '4fee', 3 * sell_refund(1, 4)
        return 'gold', g_gold    # 未定带(None)期金币支未立,非置零
    if not text:
        return 'unread', None      # 读缺帧:奖励整段读空
    return 'other', None           # 员工投影仪等未立子型(知识判据承载)


def _branch_lambda(option: EncounterOption,
                   state: GameState | None) -> tuple[str | None,
                                                     LambdaCell | None,
                                                     str | None]:
    """分支 λ 键+格解析(共享 helper;label 与复合项两消费面同一解析链,
    禁各写一套双读 provisional=漂移源)。

    返回 (键, 格, 不可判原因)。键 = PL 键(难度带×血带×位面×encounter):
    分支敌难度 stat 真值经 provisional 槽位 ``ENCOUNTER_DSTAT_MAP``
    (旗牌→stat 映射;None 期 = 键观测量缺失 = 域外同判,禁拿旗牌值
    冒充 stat 假真值,R29-6 同款);hp 只入路由键(裁定二),缺读 None
    → 域外 fail-closed。节点类型 = 'encounter'(本判据仅在遭遇屏调用,
    构造性已知,非 OCR 依赖)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
        provisional,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
        lambda_death,
    )
    dstat = provisional.get('ENCOUNTER_DSTAT_MAP')
    if dstat is None:
        return None, None, 'dstat_map_none'
    stat = dstat.value.get(option.difficulty)
    if stat is None:
        return None, None, f'dstat_missing(diff={option.difficulty})'
    hp = getattr(state, 'hp', None) if state is not None else None
    plane = getattr(state, 'plane', 1) if state is not None else 1
    key = lambda_death.make_key(stat, hp, int(plane), 'encounter')
    if key is None:
        return None, None, 'key_observable_missing'
    c = lambda_death.cell(key)
    if c is None:
        return None, None, f'domain_out({key})'
    return key, c, (None if c.label == '可消费' else f'{key}=label{c.label}')


def _branch_lambda_label(option: EncounterOption,
                         state: GameState | None) -> tuple[str | None,
                                                           str | None]:
    """分支 λ 格 label 四态查询(可消费/仅方向/禁用/空格;None=域外)。"""
    _key, c, why = _branch_lambda(option, state)
    return (c.label if c is not None else None), why


def _branch_composite(option: EncounterOption, state: GameState | None,
                      session: StrategySession | None) -> ExposureComposite | None:
    """λ 敞口差分复合项(d̂×(g+Ī×R_剩余);P51 第三口唯一合法数值算子)。

    d̂ = 同格 CI 宽度(λ_U−λ_L,保守端——两支公共 λ_L 在差分中抵消,
    R29-3 同构);敞口 = 存量金 g(核心项,P51 §R.1)+ Ī×R_剩余。
    金充裕帧敞口放大 ⇒ 生存折现主导,高难支惩罚加重(P51 折现语义)。
    金缺读帧(gold_readable False)→ None fail-closed:缺读兜底 0 非真值,
    进敞口会压薄 λ 项(方向与保守相反)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import net_income
    from sr_od.application.currency_war.kernel.cw_plane_table import r_remaining
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
        lambda_death,
    )
    key, c, _why = _branch_lambda(option, state)
    if key is None or c is None or c.label != '可消费':
        return None
    if state is None or not getattr(state, 'gold_readable', True):
        return None
    round_num = int(getattr(state, 'round_num', 1))
    ibar = net_income(round_num, 0)
    r_rem = r_remaining(session, int(state.plane), round_num) \
        if session is not None else 0
    return lambda_death.differential_composite(key, int(state.gold),
                                               ibar, r_rem)


def _fail_low(evals: list[_BranchEval], reason: str,
              session: StrategySession | None) -> EncounterPick:
    """fail 向出口:选低难度支(并列取先读支=idx 小者),保守少掉血。"""
    best = min(evals, key=lambda e: (e.option.difficulty, e.option.idx))
    _count(session, 'encounter_ev_fail_low')
    return EncounterPick(idx=best.option.idx, refresh=False, reason=reason)


def _count(session: StrategySession | None, key: str) -> None:
    """分键计数(cw4_counters 容器;session 缺席静默跳过,纯逻辑可单测)。"""
    counters = getattr(state_of(session), 'cw4_counters', None)
    if isinstance(counters, dict):
        counters[key] = counters.get(key, 0) + 1


def _hp_gate_state(state: GameState | None,
                   session: StrategySession | None) -> GameState | None:
    """hp 消费读点显式施门(W5 hp 专项:视图 hp = 门前真值,记录/消费
    分离;本读点是视图 hp 的直读消费域——遭遇屏恰在 gap==1 窗,结算在
    紧邻上一节点,门辖语义见宪法 00 §3 hp 授权消费面与 ADR-0583 §2.4
    「消费方必须同门」)。门输入 readable = 视图映射单一源
    (``state.hp_readable``,源 = bs.hp.source=='observation' 最近观察),
    时基 t 经 kernel 单一源派生(schedule_of 前序位面实际长度和,与生产门
    同源同式)。session 无结算锚(last_hp/last_hp_t 缺)时门恒等返回 =
    旧行为,纯函数可单测。

    :return: hp 已施门的 state 拷贝(其余字段共享引用,本判据链只读);
        state 为 None 时原样返回 None。
    """
    if state is None:
        return None
    from sr_od.application.currency_war.kernel.cw_plane_table import node_t_of
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        gated_hp,
    )
    t = node_t_of(session, getattr(state, 'plane', None),
                  getattr(state, 'round_num', None))
    gated = gated_hp(state.hp, session, t,
                     current_readable=bool(getattr(state, 'hp_readable',
                                                   False)))
    if gated == state.hp:
        return state
    import dataclasses
    return dataclasses.replace(state, hp=gated)


def decide_encounter_ev(options: list[EncounterOption], state: GameState | None,
                        session: StrategySession | None,
                        refresh_used: bool = False) -> EncounterPick:
    """E3 判据形态本体(纯函数;mandate_v1.decide_encounter 消费)。

    hp 施门:入口处对 state 施新鲜度门(见 :func:`_hp_gate_state`)——
    视图收编后 ``state.hp`` 是门前真值,λ 路由键的 hp 维必须与备战决策
    同门,否则误读帧血带翻转→选支漂移(W5 方案 §2.4 读点清单点名域)。
    旧链(帧值已门)再过门幂等,行为零变化。

    决策树(ADR-0536 §2):
    1. 无选项 → idx0(default,与生产 handler 一致);单卡帧(读缺)
       → 已读卡直接选;
    2. 任一分支 V_r 未立(未建模子型/金币未定带/读空)→ fail 向低难
       (禁置零续比);
    3. 任一分支 λ label 非可消费(四态接死)→ fail 向低难 + 拒因带格态
       (仅方向格另记方向注记分键,不作数值);
    4. 双支 λ 可消费 → EV 比较(EV(b)>EV(b′) ⟺ comp_{b′}+V_r(b) >
       comp_b+V_r(b′),复合项白名单运算内):
       * EV 精确并列(双支 V_r 与复合项全等)→ 并列出口 fail 向低难
         (第 5 肢;不构成胜者翻转,不给刷新);
       * EV 胜者 = V_r 胜者(稳健)→ 选 EV 胜者;
       * 胜者翻转(保守端 vs 乐观端 d̂=0 不同胜者 = EV 差落入不可判带)
         → fail 向低难;若刷新未用 → 附探索性刷新建议(原对弃用、重掷
         分布未建模可为负——非免费期权)。
    """
    # hp 消费读点显式施门(见 helper)。W6 波 4 双形态归一:容器 bs 输入
    # 先转帧形态本地视图(hp = 政策层读口 decision_hp 门后值,设计件
    # 《商店黑板容器化方案》§2.2-2「商店链 hp 消费一律经 decision_hp」;
    # gold/plane/round 经容器读口;gold_readable = source != 'prior' 保真
    # 位映射)——下游 helper 的 duck 读零改。帧输入走原 _hp_gate_state 门
    # (旧链再过门幂等,行为零变化)。
    from sr_od.application.currency_war.kernel.cw_board_state import (
        BoardState,
    )
    if isinstance(state, BoardState):
        from sr_od.application.currency_war.kernel.cw_board_state import (
            gold_of,
            plane_of,
            round_num_of,
        )
        from sr_od.application.currency_war.kernel.cw_hp_policy import (
            decision_hp,
        )
        from sr_od.application.currency_war.kernel.cw_state import GameState as _GS
        _view = _GS(gold=gold_of(state), plane=plane_of(state),
                    round_num=round_num_of(state), hp=decision_hp(state,
                                                                  session))
        _view.gold_readable = state.gold.source != 'prior'
        state = _view
    state = _hp_gate_state(state, session)   # 帧输入:hp 消费读点显式施门
    if not options:
        return EncounterPick(idx=0, refresh=False, reason='e3:no-options')
    if len(options) == 1:
        return EncounterPick(idx=options[0].idx, refresh=False,
                             reason='e3:single_option(读缺帧 fail 向与生产 default 一致)')

    g_gold = _g_gold_observed()
    evals: list[_BranchEval] = []
    for o in options:
        kind, value = reward_subtype_value(o.rewards, g_gold)
        label, why = _branch_lambda_label(o, state)
        comp = _branch_composite(o, state, session) if label == '可消费' else None
        if label == '可消费' and comp is None:
            # λ 格可消费但敞口缺真值金(gold_readable False):负项数值
            # 不授权 → 并入整体不可判(fail 向),禁置零续比。
            why = 'gold_unreadable(λ 敞口缺真值金,fail-closed)'
        evals.append(_BranchEval(option=o, reward_kind=kind,
                                 reward_value=value, lam_label=label,
                                 undecidable_why=why, composite=comp))
        if kind == 'gold':
            _count(session, 'encounter_ev_reward_gold')
        elif kind == '4fee':
            _count(session, 'encounter_ev_reward_4fee')

    # 肢 2:奖励侧未立(含金币未定带)→ fail 向(未立 ≠ 0)
    unmodeled = [e for e in evals if e.reward_value is None]
    if unmodeled:
        kinds = ','.join(sorted({e.reward_kind for e in unmodeled}))
        _count(session, 'encounter_ev_fail_low_reward_unmodeled')
        return _fail_low(evals, f'e3_fail_low:reward_unmodeled({kinds})', session)

    # 肢 3:λ label 四态接死(任一非可消费 ⇒ 整体不可判,fail 向;禁止置零;
    # 可消费格而敞口缺真值金同判不可判)
    bad = [e for e in evals if e.lam_label != '可消费' or e.composite is None]
    if bad:
        detail = ';'.join(f'{e.undecidable_why}' for e in bad if e.undecidable_why)
        if any(e.lam_label == '仅方向' for e in bad):
            _count(session, 'encounter_ev_lambda_direction_note')
        _count(session, 'encounter_ev_fail_low_lambda_undecidable')
        return _fail_low(evals, f'e3_fail_low:lambda_undecidable({detail})', session)

    # 肢 4:EV 数值比较(复合项白名单运算;精确并列显式先行,防误入翻转支)
    def _ev_beats(a: _BranchEval, b: _BranchEval) -> bool:
        # EV(a) > EV(b) ⟺ V_a + d̂_b·X > V_b + d̂_a·X
        return (b.composite + a.reward_value) > (a.composite + b.reward_value)

    def _ev_tied(a: _BranchEval, b: _BranchEval) -> bool:
        """EV 精确并列:双支 V_r 全等 ∧ 复合项全等(典型形态 = 标定后
        同难度双卡帧,两支解析到同 λ 格)。并列判定用 ≤ 双向(复合项
        白名单无 __eq__,总序下双向 ≤ 即全等)。"""
        return (a.reward_value == b.reward_value
                and a.composite <= b.composite
                and b.composite <= a.composite)

    def _vr_beats(a: _BranchEval, b: _BranchEval) -> bool:
        if a.reward_value != b.reward_value:
            return a.reward_value > b.reward_value
        return (a.option.difficulty, a.option.idx) < (b.option.difficulty, b.option.idx)

    ev_best = evals[0]
    ev_tied = False
    for e in evals[1:]:
        if _ev_tied(e, ev_best):
            ev_tied = True
        elif _ev_beats(e, ev_best):
            ev_best, ev_tied = e, False
        # ev_best 严格胜 e:保持(并列标志只在最优层有义)

    if ev_tied:
        # 第 5 肢:EV 并列 → fail 向低难(不记翻转、不给刷新)
        _count(session, 'encounter_ev_fail_low_tie')
        return _fail_low(evals, 'e3_fail_low:ev_tie(双支 V_r 与 λ 敞口项全等)',
                         session)

    vr_best = evals[0]
    for e in evals[1:]:
        if _vr_beats(e, vr_best):
            vr_best = e

    if ev_best.option.idx == vr_best.option.idx:
        # 稳健:保守端与乐观端同胜者
        _count(session, 'encounter_ev_pick')
        return EncounterPick(
            idx=ev_best.option.idx, refresh=False,
            reason=(f'e3_pick:ev_argmax(diff={ev_best.option.difficulty} '
                    f'kind={ev_best.reward_kind} vr={ev_best.reward_value})'))
    # 胜者翻转 = EV 差落入不可判带 → fail 向 + 探索性刷新建议(条件化)
    _count(session, 'encounter_ev_undecidable_band_flip')
    refresh = not refresh_used
    if refresh:
        _count(session, 'encounter_ev_refresh_suggested')
    pick = _fail_low(evals, 'e3_fail_low:flip_band(V_r 胜者与 EV 胜者不一致,'
                     'λ CI 宽度翻转比较)', session)
    pick.refresh = refresh
    if refresh:
        pick.reason += '+branch_refresh_suggest(原对弃用强制新选,重掷分布未建模可为负)'
    return pick
