"""决策纪律·卖侧下界/种子年龄判据族(自 decision_v2.discipline
下沉;DESIGN §3.3-①e)。

下沉闭包 = cw_evolution 溢出卖出/种子豁免消费面:
``sole_engine_sell_floor_plan``(批量逐笔下界,ADR-0380)及其计数底座
(``_sell_floor_counts/_eval/_decrement``,ADR-0373/0375 单一源)、
``seed_age_blocked``(engine_seed 年龄豁免,ADR-0289/0339)及其计数
依赖 ``star_weighted_copies``。全部为纯谓词(不依赖线库/桥池;
registry 注解在 cw_registry 下沉 kernel 后 kernel 内自洽)——
discipline 余部(行为臂/纪律视图)留 decision 桶,经本模块消费同一
计数底座(单一源不破)。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from dataclasses import dataclass, field  # noqa: E402

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import GameState

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )

def star_weighted_copies(name: str, state: GameState) -> int:
    """同名星级加权副本数(bench+deployed;2★=2 份,3★=3 份)。"""
    n = sum(getattr(b, 'star', 1) or 1
            for b in (state.bench or []) if b is not None
            and b.char_id == name)
    n += sum(getattr(d, 'star', 1) or 1
             for d in (state.deployed or [])
             if getattr(d, 'char_id', '') == name)
    return n


def sole_engine_sell_floor_plan(bcs: list,
                                state: GameState,
                                registry: DecisionV2Registry | None = None,
                                ) -> list[bool]:
    """ADR-0380:同批多笔卖出的逐笔下界判定(批量口径)。

    背景(实机实证):arbitrate 同段可采纳多笔同名 TT 件卖候选——
    候选生成对**批前状态**计数(列车在手 3>tier 2),逐笔合法而批内
    聚合 3→1 跌破 tier。``sole_engine_sell_blocked`` 单件口径对同批
    前序卖出不可见——本函数按 ``bcs`` 顺序逐笔评估,**前序判定为
    「可卖」的件从计数扣减**(blocked 件不卖、不扣减);单笔输入时
    与单件谓词逐位一致(同一计数底座/同一辖域判据,ADR-0373/0375)。

    消费面:arbiter 卖候选采纳点(对 working 复检,前序扣减由 working
    前序采纳天然实现)/ execute_replacement 溢出卖出下界(ADR-0380
    件1,事务内多笔同序扣减)/ remediation 两补偿器卖件组发射前过滤
    (ADR-0384 ``_sell_floor_filter``,对 working 逐笔扣减)。
    """
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    counts = _sell_floor_counts(state, reg)
    out: list[bool] = []
    for bc in bcs:
        name = getattr(bc, 'char_id', '') or ''
        ch = CHARACTERS.get(name)
        if not reg.sell_sole_engine_guard_enabled or ch is None:
            out.append(False)
            continue
        bonds = set(ch.factions) | set(ch.flows)
        blocked = _sell_floor_eval(name, bonds, counts)
        out.append(blocked)
        if not blocked:
            _sell_floor_decrement(name, bonds, counts)
    return out


def _sell_floor_counts(state: GameState,
                       reg: DecisionV2Registry) -> dict:
    """下界守卫计数底座(ADR-0373/0375/0380 单一源)。

    返回可变计数 dict:
    - TT 三羁绊键 → {'tier': 门槛, 'count': 在手件数(bench∪deployed
      逐件计,全羁绊 factions∪flows 口径)};
    - '_seele_scope'(辖域开关)/'_seele_core'(希儿在手)/
      '_seele_core_copies'(希儿副本数)/'_seele_amp:{阵营}'(放大阵营
      在手件数)——希儿系核心条件辖(ADR-0375 判据)。
    """
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        SEELE_AMP_FACTIONS,
        TRANSITION_TRAITS,
    )
    counts: dict = {b: {'tier': t, 'count': 0} for b, t in TRANSITION_TRAITS}
    pool = [p for p in (*state.bench, *state.deployed)
            if p is not None and p.char_id]
    core_copies = 0
    amp_counts = dict.fromkeys(SEELE_AMP_FACTIONS, 0)
    for p in pool:
        pc = CHARACTERS.get(p.char_id)
        if pc is None:
            continue
        pb = set(pc.factions) | set(pc.flows)
        for b in counts:
            if b in pb:
                counts[b]['count'] += 1
        if p.char_id == '希儿':
            core_copies += 1
        else:
            for f in amp_counts:
                if f in pb:
                    amp_counts[f] += 1
    counts['_seele_scope'] = reg.guard_seele_scope_enabled
    counts['_seele_core_copies'] = core_copies
    counts['_seele_core'] = core_copies > 0
    for f, c in amp_counts.items():
        counts[f'_seele_amp:{f}'] = c
    return counts


def _sell_floor_eval(name: str, bonds: set, counts: dict) -> bool:
    """单件下界判定(对计数底座;TT ≤tier + 希儿系条件辖,两判据取或)。"""
    blocked = any(v['count'] <= v['tier'] for b, v in counts.items()
                  if not b.startswith('_') and b in bonds)
    if not blocked and counts.get('_seele_scope'):
        if name == '希儿':
            blocked = counts.get('_seele_core_copies', 0) <= 1
        else:
            amp = {b for b in bonds
                   if f'_seele_amp:{b}' in counts}
            if amp and counts.get('_seele_core'):
                blocked = any(counts[f'_seele_amp:{f}'] <= 2 for f in amp)
    return blocked


def _sell_floor_decrement(name: str, bonds: set, counts: dict) -> None:
    """该件将卖出 → 计数底座扣减(批量口径的前序可见性)。"""
    for b, v in counts.items():
        if not b.startswith('_') and b in bonds:
            v['count'] -= 1
    if name == '希儿':
        counts['_seele_core_copies'] = counts.get('_seele_core_copies', 0) - 1
        counts['_seele_core'] = counts['_seele_core_copies'] > 0
    else:
        for f in bonds:
            k = f'_seele_amp:{f}'
            if k in counts:
                counts[k] -= 1


def seed_age_blocked(bc, state: GameState,
                     session: StrategySession | None) -> bool:
    """engine_seed 年龄豁免——**结构性恒 False**(session.md §2.5 退役收口)。

    豁免数据源 = 原购入轮登记(v2_seed_bought):其唯一写端是局首清零,
    登记写端早已不存在 → 该 dict 现状恒空,豁免分支结构性失效(空输入
    查表恒 miss → False)。职责分离切换批把该死码显式收口:删除恒空
    查表读段,保留函数签名与恒 False 语义(cw_evolution 卖面判据的
    豁免位消费零改;ADR-0289/0339 的豁免设计随登记写端消亡一并退役)。
    """
    return False


# ===== 血预算停手/危机带判据族(自 decision_v2.discipline 下沉,迁移底稿
# MAP ⓪ A3:mandate_v1 判据级消费的唯一 v2 import 收编进 kernel;discipline
# 本名保留 re-export,消费方调用零改)。闭包 = 判据 1-2 层依赖:
# nodes_of_plane(plane_last_battle 轮维)/hp 可信位与门后值读口(统一 state
# 迁移波 2 起经 kernel 政策层 cw_hp_policy 单一读口:决策 hp 消费 =
# decision_hp 门后值,可信位 = hp_decision_trusted 委托
# hp_decision_trusted_of——kernel 决策分支禁旁路直读 bs.hp/state.hp,
# 消费同门纪律承接 ADR-0583 §2.4)。

from sr_od.application.currency_war.kernel.cw_plane_table import (  # noqa: E402
    nodes_of_plane,
)
from sr_od.application.currency_war.kernel.cw_hp_policy import (  # noqa: E402
    decision_hp,
    hp_decision_trusted_of,
)


def hp_decision_trusted(frame) -> bool:
    """hp 决策可信位(单一源;**双形态过渡函数**,统一 state 迁移波 2 起):

    - **容器形态**(输入 = ``BoardState``):委托
      ``cw_hp_policy.hp_decision_trusted_of``(定谳二单一源:
      ``bs.hp.source in ('observation', 'carried')``,语义见该函数
      docstring);
    - **GameState 形态**(输入 = 旧标量帧:``frame.hp`` 非 Field 载体):
      旧双位读法 ``hp_readable or hp_trusted``——辖策略域未切换消费面
      (statefn/flow 等,strategies 全簇随波 4 切),**随统一 state 迁移
      W8 GameState 本体删除消亡**(r5-migration-plan §6 残留表),禁在
      该形态下新增消费点。

    同模块(及跨模块引用点)禁再手写双位判定(W393 A1.1 单一源纪律):
    语义=ADR-0282 对账层「沿用真值帧放行 vs 兜底假值帧拒」(ADR-0428
    收紧口径)——prior/logic 支两位皆 False 不评估,carried 沿用帧放行。
    新增 hp 守卫消费点一律走容器形态本 helper 或政策层读口。
    """
    _hp = getattr(frame, 'hp', None)
    if hasattr(_hp, 'source'):    # 容器帧:hp 是 Field 载体(带 .source)
        return hp_decision_trusted_of(frame)
    # GameState 残留形态(getattr 读法,随 W8 消亡;AST 双位锁豁免位)
    return bool(getattr(frame, 'hp_readable', False)
                or getattr(frame, 'hp_trusted', False))


# p1_crisis_band(P1 ≈22 血危局带判据)不设:经用户裁决不授权、废弃
# (发展为主,不做低血补救)——(b)2/(b)3 消费位永久挂空,处置记录 =
# docs/develop/sr_od/application/currency_war/strategy-docs/14_p1_consume_arms.md §11.8。
# 危局面合规件仅血线硬地板 ≤15 族,消费在 mandate_v1 criteria 层
# (levelup.level_spend_blocked 停付让位 / sell_for_interest 凑息禁令),
# 判据单一源 = statefn/predicates.p1_blood_floor,不在本模块设第二份。
def plane_last_battle(bs, session) -> bool:
    """位面末最后一战([18]):当前节点=boss 且轮=位面节点数(真值源
    ``nodes_of_plane``——P2 boss@r7 判正;旧按 9 计 P2 永不触发,
    ADR-0366 口径断层修复)。波 2 签名切容器:节点类型/轮次经容器读口
    (node_kind_of/round_num_of 镜像,桥视图 kind 空串 = 未识别忠实镜像
    同旧 `or ''`)。"""
    from sr_od.application.currency_war.kernel.cw_board_state import (
        node_kind_of,
        round_num_of,
    )
    node = getattr(session, 'node_type_current', None) or node_kind_of(bs) or ''
    return node in ('boss',) and round_num_of(bs) >= nodes_of_plane(session)


def all_in_xp_domain_hit(bs, session,
                         registry: DecisionV2Registry) -> bool:
    """ALL IN 窗 XP 类别过滤的辖域判据(ADR-0604 §4-F5;P21 域钉死)。

    = 位面末最后一战(``plane_last_battle`` 单一源,[18] 豁免窗)
    ∧ hp 真值可信(``hp_decision_trusted`` 单一源)
    ∧ 门后 hp ≤ 停升级线(复用 p1/p2_levelup_stop_hp 锚表,零新参数——
    「按下一节点型 L_c^stop 查表」的落码形态即在产停升级线同一线表,
    禁另建第二套血线表;辖域口径差申报 = ADR-0604 §4-D1:在产线
    P1=11 不分节点型 vs 设计锚 12/15/30,重校债归重设计落码批)。
    hp 消费 = 政策层读口 ``decision_hp`` 门后值(消费同门,ADR-0583
    §2.4;旧链由上游 adapter 施门间接保证,波 2 起读点显式施门,门幂等
    保证过渡期行为一致)。

    辖域语义:ALL IN 窗内支出按「当轮可上场」类别白名单过滤(档 0
    d=0 形态/档 1/让位卖出后部署;XP 升级类仅支A 兑现链形态合法),
    本谓词只辖「hp 落停升级线内」的帧——域外帧(hp>停线)不受过滤,
    维持既有 [18] 全豁免(域外不动申报 = ADR-0604 §4-F5:批#2 s9 型
    hp=35 帧 8×LevelUp 在域外,过滤后不拦)。hp 不可信/None 帧 = 线内线外
    不可判 → False 不过滤([18]「末战花光是时机不是血线判断」豁免
    语义在不可信帧仍生效,与 blood_budget_levelup_blocked 的豁免序、
    p2_crisis_band 的「血预算未知不判带」非对称口径一致:误放有地板
    与 refresh 预算兜底,误拦失转化通道)。

    宪法姿态:消费既有停升级线 hp 读数,零新增 hp 消费点(总图 N5
    对账「既有授权辖域收窄非新增 hp 点」);判据级辖域收窄,非血线
    地板解锁包件(hp 闸批另落,总图实施序第 5 步)。支A 谓词不进
    kernel(消费侧 criteria/levelup._realize_chain_ready 单一源,
    P39 指示项锚对契约),本谓词只答血侧半支。
    """
    from sr_od.application.currency_war.kernel.cw_board_state import (
        plane_of,
    )
    if not plane_last_battle(bs, session):
        return False
    if not hp_decision_trusted(bs):
        return False
    hp = decision_hp(bs, session)
    if hp is None:
        return False
    plane = plane_of(bs)
    if plane == 2:
        return hp <= p2_levelup_stop_hp(registry)
    if plane == 1:
        return hp <= p1_levelup_stop_hp(registry)
    return False


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


def blood_budget_levelup_blocked(bs, session,
                                 registry: DecisionV2Registry) -> bool:
    """血预算停手·停升级门(设计件 12 §3.1 P2 / §2.3-P1-b;ADR-0448)。

    P21 已证:存活到账判据 h > d·L_c 在 h ≤ d·L_c 域内恒假 → 升级收益
    恒 0、EV=−C−I 严格为负,且敏感网格 (p,Δp,d,c) 全负域——结论与
    β 标定无关。备战帧门后 hp ≤ 停升级线(P1/P2 各自线)时拒绝购买经验。
    hp 消费 = 政策层读口 ``decision_hp`` 门后值(消费同门,ADR-0583
    §2.4;旧链由上游 adapter 施门间接保证,波 2 起读点显式施门,门幂等
    保证过渡期行为一致)。

    接缝语义(设计件 12 §5.2/§5.3,实现形态裁决):
    - **授权通道前置拒付过滤**,与息线门是独立谓词取 AND(血线胜)——
      不是第五种覆盖态,discipline 覆盖序不动,emergency 态内同样生效
      (应急梯度给「怎么花」,停手给「不许为未来花」);
    - 唯一豁免 = ``plane_last_battle`` ALL IN 清零窗(位面末最后一战
      是损失最小的花光时机,[18];停手让位)。
    消费点:cw4 M3 升级门(criteria/levelup.level_spend_blocked)/
    arbiter 约束 'blood_budget_stop'(候选通道)/remediation 稳态多击组
    与 deploy_cap 补偿臂①(授权通道旁路——两臂的升级收益同在 ≥1 战
    之后才兑现,同辖;拒付计数=strategy_state_of(session).v3_blood_budget_rejects,披露
    模式对齐 sim 执行层 level_cap_rejects)。

    消费层可信位门(ADR-0448 血线谓词唯一收口,W580):
    ``hp_decision_trusted`` 不过的帧(容器 source=prior/logic 支:开局
    先验帧/推算帧)fail-closed 按血线内处理(拒付升级)——线内升级
    EV=−C−I 严格负(本函数数学),证据缺失时禁令保持有效与误放的非对称
    代价(误放=血线内追级,误拦=少升一级)同型于 ADR-0428 兜底假值帧拒
    语义。不降姿态/不维持上次决策:谓词逐帧无状态且被三面共享,引入跨帧
    记忆=新状态机不成比例;只封 LevelUp 通道,买牌/刷新各有其门。置于
    ALL IN 豁免之后:豁免语义=「末战花光是时机不是血线判断」,在不可信
    帧上仍生效。
    """
    if not registry.blood_budget_stop_enabled:
        return False
    if plane_last_battle(bs, session):
        return False    # ALL IN 窗:停手让位([18] 唯一清零地板路径)
    if not hp_decision_trusted(bs):
        return True     # 不可信 hp 帧:fail-closed 按血线内处理(拒升级)
    hp = decision_hp(bs, session)
    if hp is None:
        # hp 无真值帧 fail-closed(ADR-0495 消费点对 None 一律保守):
        # 容器未写帧(值 None)会以缺省来源骗过上面的可信位门,但 hp=None
        # 时停升级线无法判「线内/线外」——误放(线内追级)与误拦(少升
        # 一级)代价非对称,按线内处理拒升级。
        return True
    from sr_od.application.currency_war.kernel.cw_board_state import (
        plane_of,
    )
    plane = plane_of(bs)
    if plane == 2:
        return hp <= p2_levelup_stop_hp(registry)
    if plane == 1:
        return hp <= p1_levelup_stop_hp(registry)
    return False


def p2_crisis_stop_hp(registry: DecisionV2Registry) -> int:
    """P2 危机带血线 = ceil(2 × vd_p2_loss)≈41 血(零新自由参数)。

    推导链(输入全为既有注册表/常数,无新拍定值):
    - **血预算语义**:hp ≤ 2×L_c = 剩余吸收不足两次条件败局——「双失
      缓冲」算术与 ``emergency_hp`` 推导链同款(registry emergency_hp
      注:应急线下界 = 2×L_c 吸收上界);L_c = registry.vd_p2_loss
      (P12 收益侧条件败局伤害,20.05,单一源禁第二份);
    - **P21 到账延迟形式**:h > d·L_c 判据中 d=2 是设计件 12 §3.1
      步骤 3 已登记的「到账更慢」档(原注:"d=2 时为 41 血");搜索型
      刷新的收益到账链 = 刷出→买入→(第二张合成[merge_mechanics:三张
      合一,副本不成三零战力 P48 A1 Leontief]或槽位腾挪)→再下一战兑现,
      最短诚实延迟 2 战;ceil(2×20.05)=41 与血预算读数同值互证;
    - **P21 敏感网格覆盖**:网格 d∈{0,1,2} 全负域 ⇒ 结论在 β≤0.30
      与 β 无关(设计件 12 §3.1 步骤 1)——本线不消费 β,不挂 β 门。
    边界声明:该线是**血预算带分界**(带内行为=转化优先/搜索停付),
    不是存活保证——与 p1_exit_blood_target 的「期望预算线非存活保证」
    同款口径(W524 审计)。
    """
    import math
    return math.ceil(2 * registry.vd_p2_loss)


def p2_crisis_band(bs, session, registry: DecisionV2Registry) -> bool:
    """P2 危机带谓词(plane≥2 ∧ 门后 hp 真值 ∧ hp ≤ 危机带线)。

    两个行为面的共域判据(消费点各取所需,谓词单一源):
    - ``blood_budget_refresh_blocked`` P2 臂:带内搜索型刷新停付;
    - arbiter 危机买入闸门(``_crisis_buy_gate_open``):带内目标件
      买候选越过非正分门/息律门(P48 λ>0 段转化优先);
    - cw4 M3 危机让位(criteria/levelup.level_spend_blocked 危机支)。
    hp 消费 = 政策层读口 ``decision_hp`` 门后值(消费同门,ADR-0583
    §2.4;``session`` 形参随波 2 签名切换补入——hp 消费函数统一持
    session 装配结算锚,与 blood_budget_levelup_blocked 同形态)。
    应急带(hp≤emergency_hp)不属本带语义管辖:应急覆盖态
    (层2 emergency_tags/危机囤金)自有一套处置,本谓词不重复触发
    (消费点在应急豁免**之后**取值,天然不含);hp 不可信/None 帧返回
    False(与 P1 末窗线同款:血预算未知时不判带——误放代价=血预算
    未知帧多付一次搜索/少买一件,有金地板与 refresh 预算兜底;误拦
    代价=危机帧失去转化通道,非对称取不拦)。
    """
    from sr_od.application.currency_war.kernel.cw_board_state import (
        plane_of,
    )
    hp = decision_hp(bs, session)
    return (plane_of(bs) >= 2
            and hp is not None
            and hp <= p2_crisis_stop_hp(registry))


@dataclass
class BloodAlarmTracker:
    """掉血三臂判据的跨步记忆(挂 strategy_state_of(session).v3_alarm;重启丢 session 保守重置)。

    - ``recent_losses``:(全局节点号, 战斗净掉血)滚动窗——窗口单位=
      **连续战斗节点**(W51 语义修复:战斗节点计数器,非日历轮;点4
      「3 轮内」按战斗语义读作「最近 3 个战斗节点」);②最近 3 个
      战斗节点累计 ≥20(急性)/③最近 5 个战斗节点累计 ≥30(慢性漂移);
      **跨位面重置**(慢性臂横跨整个位面的按轮漂移根修);
    - ``consec_battle_fails``:①连续 2 场战斗失败;
    - ``alarm_battles``:处置梯度计时——报警激活期间累计喂入的战斗
      节点数(=1 → ①自然补强窗内;>1 → 窗耗尽未达标;报警解除清零);
    - 非战斗节点:不入窗、不清臂(点4 冻结语义)。

    写者 = flow 结算策略半惰性 drain(ADR-0583:原 on_round_end 拆两半后,
    battle_wait 观察半入 pending 槽、决策入口 drain 喂入;结算真值;两栈共享)。
    """

    recent_losses: deque = field(default_factory=lambda: deque(maxlen=5))
    consec_battle_fails: int = 0
    alarm_battles: int = 0
    plane: int | None = None

    _BATTLE_NODES: frozenset[str] = frozenset(
        {'battle', '普通战斗', 'boss', '精英', '遭遇'})

    def record(self, node_type: str, hp_before: int, hp_after: int,
               t: int, plane: int | None = None) -> None:
        """结算策略半喂入(结算真值;hp_after 为空帧跳过)。

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
