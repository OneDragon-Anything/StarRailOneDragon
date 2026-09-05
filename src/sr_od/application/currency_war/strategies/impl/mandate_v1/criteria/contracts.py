"""cw4 判据契约层(assume-guarantee 纪律;2026-09-03 用户批准的组合性改进①)。

单一源=本模块 ``CONTRACTS``(循同包 ``BYPASS_TABLE`` 先例:注册表 +
静态完备性对拍测试)。缺陷背景:零刷新/arm1 两案均为「语境前提未被
核验」类缺陷——r1 EV 输入字面量 ``None`` 绕过前提
(ZERO_REFRESH_DIAG §4.1 实现缺口)、arm1 拿固定槽表常数当阈值域错位
(ZERO_REFRESH_DIAG §4.2)。契约化 = 把每个判据的**语境前提**写成谓词级
契约,接线处(entry.py / shop.py 判据消费位)经 ``ensure_contract``
核验:前提不成立 ⇒ 该判据本帧**弃权**(不发射/不求值)+
``criteria_contract_violation:<判据名>`` 计数——禁静默执行;fail-closed
不抛异常不断局(谓词异常同判弃权)。契约层只加前提核验,**禁改判据
数学**(判据本体函数零触碰)。

辖外声明:换线判据族(should_switch/回锁窗/干旱计数)=影子面
(IMPL_DESIGN §3.4 R197 症2 影子面声明),其行为接线=过线后批——本表
只登记判据面函数位(§4.2.1 三函数位),前提核验随实装接线批落位。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from sr_od.application.currency_war.strategies.impl.mandate_v1.audit.provisional import (
    CalibValue,
)


@dataclass
class ContractCtx:
    """契约核验的决策帧上下文(消费点现读快照;谓词按需取字段)。

    字段取值时机=判据消费点当帧现读(非生成期快照);缺失语义=
    None(谓词按「语境前提是否成立」各自解读,不在此默认)。

    - k_members:目标线 K 成员名元组(predicates.line_members 产物;
      空/None=目标线未成型)。
    - gold:决策帧金(消费位口径——商店波为支出后投影金)。
    - reserve:S 预留值(消费位现读,如 b_target 组装结果)。
    - deploy_cap:等级驱动可上阵 cap(GameState.max_units() 口径;
      None=消费位退固定槽表常数,即 arm1 域错位形态)。
    - ev_slot:EV 输入槽位现读的**原始对象**(FIX_REVIEW_20260903
      防线硬化:由消费位硬编码声明位 ``ev_input_wired=True`` 改造)——
      合法形态 = ``audit/provisional.get('V_GAP')`` 的返回物(None =
      None 期 fail-closed / CalibValue = 槽位现读);裸 float/字面量 =
      「回退字面量但保留声明」复发形态,违例。
    - k_target:战略层产物 target_comp **原值**(k_projection 前提的
      可核验派生输入,原声明位 ``k_none_domain_covered=True`` 改造)。
    - k_fallback_available:K 回退供给是否在场(消费位从
      v3_intention 在场性派生;缺供给帧=保守侧不回退,合法)。
    - k_fallback_resolved:消费位**实解析**的回退成员集(单一源
      cw_intention 调用的返回物;供给在场而解析为空 = 「回退字面量
      空元组」复发形态,违例)。
    """

    k_members: tuple[str, ...] | None = None
    gold: int | None = None
    reserve: int | None = None
    deploy_cap: int | None = None
    ev_slot: object | None = field(default=None)
    k_target: object = field(default=None)
    k_fallback_available: bool = field(default=False)
    k_fallback_resolved: object = field(default=None)


def _s_reserve_line_formed(ctx: ContractCtx) -> bool:
    """先例①前提:S 预留只在对目标线成型的语境下预留(禁恒预留)。

    规格辖域裁决(ZERO_REFRESH_DIAG §3 第 3 条,原文):硬约束③ S 预留
    拦截对象列=「EV 买入面(序 3-5 追加支出,stockpile 等)+ M6 +
    dominance_buy(R32-3)」——前提=目标线 K 已成型(k_members 非空):
    无目标线语境下的恒量预留即「语境前提未被核验」缺陷形态
    (R196 ``_s_reserve`` 恒 54 同型,diag §3 挂账项)。
    """
    return bool(ctx.k_members)


def _gold_minus_reserve_ctx(ctx: ContractCtx) -> bool:
    """先例②前提:r2 预算门消费「金−预留」语境(两个现读输入在场)。

    规格:金−预留 ≥ 刷价才批(refresh.r2_budget);前提=消费位给的是
    决策帧现读金与预留值(均非 None)——缺任一即语境未核验,弃权。
    辖域澄清(diag §3 第 3 条):付费刷新 r2 预算门**不在** S 预留
    拦截对象列,预留此处是预算语境输入而非硬约束③预留。
    """
    return ctx.gold is not None and ctx.reserve is not None


def _arm1_cap_level_driven(ctx: ContractCtx) -> bool:
    """先例③前提:arm1 板满口径=等级驱动 cap(禁固定常数)。

    ZERO_REFRESH_DIAG §4.2 实证:cap 口径=当前可上阵数
    (GameState.max_units():level+宝钻、封顶 10);旧条件拿固定槽表
    常数 10 当阈值 ⇒ deployed_count 构造性不可达 ⇒ 触发面恒空。
    前提=消费位传入了现读 cap(ctx.deploy_cap 非 None;
    ``deploy_cap=None`` 走固定常数兜底即违例)。
    """
    return ctx.deploy_cap is not None


def _ev_input_from_slot(ctx: ContractCtx) -> bool:
    """先例(r1 零刷新接线):EV 判据输入系 provisional 槽位现读。

    ZERO_REFRESH_DIAG §4.1 实现缺口:r1 输入为硬编码字面量 ``None``,
    开闸路径不可达;修复批接线后消费位现读 ``V_GAP`` 槽位。
    **可核验派生形态(FIX_REVIEW_20260903 防线硬化)**:前提不再采信
    消费位硬编码声明,而是核验 ``ctx.ev_slot`` 的运行时类型——合法 =
    ``None``(None 期 fail-closed,判据语义)或 ``CalibValue``
    (``audit/provisional.get`` 的返回物);裸 float/字面量 = 复发
    形态,违例弃权。
    """
    return ctx.ev_slot is None or isinstance(ctx.ev_slot, CalibValue)


def _k_projection_domain_full(ctx: ContractCtx) -> bool:
    """先例(K 空窗回退,第三病灶)前提:战略层产物字段值域全集含
    空窗期——K 投影域覆盖 None。

    SEEDS_EMPTY_LEDGER_DIAG §3/§4(2026-09-03 第三病灶裁定):
    ``session.target_comp`` 的值域含 None(P1 空窗=开局常态),消费端
    把 None 当「已锁线世界」直接投影(``line_members(None)→()``)=
    「单一值域的一端当全域」域错位(arm1 cap 口径/零刷新 r1 输入同型
    第三例)——空窗死锁环:K 空→零买入→板面零变化→永不锁。
    **可核验派生形态(FIX_REVIEW_20260903 防线硬化+R3 扩域)**:值域
    全集声明覆盖三带(P1 空窗带/P1 锁线过渡带/P2+ 带),前提不再采信
    消费位硬编码声明,而是核验实解析结果——``k_target`` 非 None
    (锁线世界)= 无回退义务,恒过;``k_target`` None 且供给缺帧
    (``k_fallback_available`` False)= 保守侧不回退,合法 fail 方向
    (与 committed_authority 缺供给同款);供给在场而
    ``k_fallback_resolved`` 为空 = 「回退字面量空元组但保留声明」
    复发形态,违例弃权。回退单一源=cw_intention.hoard_target_set /
    p1_early_pair_members(禁复制四体系全集逻辑)。
    """
    if ctx.k_target is not None:
        return True
    if not ctx.k_fallback_available:
        return True
    return bool(ctx.k_fallback_resolved)


@dataclass(frozen=True)
class Contract:
    """单判据契约:前提谓词(None=无条件)+ 辖域声明 + 规格锚。

    前提谓词签名统一 ``ContractCtx -> bool``;None=前提恒真(仍需
    显式登记辖域声明,防「未审计」与「无条件」混淆)。
    """

    precondition: Callable[[ContractCtx], bool] | None
    scope: str     # 辖域声明一句(该判据语境前提的适用面)
    anchor: str    # 规格锚(IMPL_DESIGN 节/引理号/诊断报告节)


#: (模块, 函数) → Contract。键集与 criteria 全公开函数对拍(静态
#: 完备性测试,漏登记=测试红);非 criteria 键(三先例+K 空窗回退
#: 消费位)单列。
CONTRACTS: dict[tuple[str, str], Contract] = {
    # —— criteria/buy ——
    ('buy', 'ev_buy_candidates'): Contract(
        _s_reserve_line_formed,
        'EV 买候选(S 预留消费位):辖 EV 买面,前提=目标线成型',
        'ZERO_REFRESH_DIAG §3 第 3 条(硬约束③拦截对象列)+IMPL_DESIGN §3.2 ③'),
    ('buy', 'ev_buy_veto'): Contract(
        None, 'EV 买否决门(随候选流一体;R7-1 发射面后半)',
        'IMPL_DESIGN §4.2.1 buy.ev_buy_* 行'),
    ('buy', 'p2_lock_buy'): Contract(
        None, 'P2 锁线核心卡钩子占位(默认关)', 'IMPL_DESIGN §2.11 P25'),
    # —— criteria/sell ——
    ('sell', 'line_switch_sell'): Contract(
        None, '换线塌缩出口:前提=K 已切换(判据自带 k_switched 门)',
        'IMPL_DESIGN §2.2 sell 行'),
    ('sell', 'sell_for_interest'): Contract(
        None, '凑息档 EV 面(T_SEARCH 缺省 fail-closed 自带)',
        'IMPL_DESIGN §2.2 R20-1'),
    ('sell', 'funding_support_sell'): Contract(
        None, '支付支撑通道(两臂同开;触发=金不足自带 gold<need 门)',
        'IMPL_DESIGN §4.2.1 R13-5/R14-4 行'),
    # —— criteria/levelup ——
    ('levelup', 'arm2_schedule'): Contract(
        None, 'arm2 调度门(结构守息门,零 λ 依赖)', 'IMPL_DESIGN §4.2.1 行'),
    ('levelup', 'saturation_floor'): Contract(
        None, '守息线 g*=10×cap_resolved 重导出(interest.saturation_line 单一源)',
        'IMPL_DESIGN §2.3 R70-1'),
    ('levelup', 'spend_unified'): Contract(
        None, 'P48 整买纪律(M3 义务侧消费)', 'IMPL_DESIGN D-BUYNOTE'),
    ('levelup', 'batch_form'): Contract(
        None, '批量成型判据(M3 义务侧消费)', 'IMPL_DESIGN §2.3'),
    ('levelup', 'lv9_stop'): Contract(
        None, '满级停(LEVEL_CAP=9;义务侧消费)', 'IMPL_DESIGN §2.3'),
    ('levelup', 'level_spend_blocked'): Contract(
        None, '危机带经验授权让位(候选③;判据自带 ALL IN 豁免与 '
        'hp 不可信 fail-closed,前提恒真)',
        'g_20260904_054904 候选③+P21/P48 λ>0 段(discipline 单一源)'),
    ('levelup', 'pop_slot'): Contract(
        None, 'D-lv7 OPEN 检查点(满编+富金+候补升 cap)', 'IMPL_DESIGN D-lv7'),
    # —— criteria/refresh ——
    ('refresh', 'r0_stop'): Contract(
        None, 'R0 维持结构门(结构位,输入=店面快照+金,恒良定义)',
        'IMPL_DESIGN §4.2.1 R10-3 行'),
    ('refresh', 'r1_start'): Contract(
        _ev_input_from_slot,
        '付费刷新发射位:前提=EV 输入系 provisional V_GAP 槽位现读'
        '(V̄ 封印族恒 None 不入此门;None 期 fail-closed 属判据语义)',
        'ZERO_REFRESH_DIAG §4.1 实现缺口+§6 修法 2'),
    ('refresh', 'r1_commitment_account'): Contract(
        None,
        'R1 启动门·形式二可负担性(ADR-0516):总账 c_eff·E(D|L*) + Σ卡费 '
        '+ L ≤ g − g*,输入全为游戏定义量(REFRESH_PROB/XP 表/息律),'
        '无标定槽位依赖(旧 V_GAP 槽位比较项已随 V̄ 链退役)',
        'ADR-0516(裁决=用户裁定禁胜率建模;形式二规格=P40/P47/P56 复用)'),
    ('refresh', 'r2_budget'): Contract(
        _gold_minus_reserve_ctx,
        '付费刷新预算门:前提=金−预留语境(现读金与预留均在场;'
        'r2 不在硬约束③ S 预留拦截对象列)',
        'ZERO_REFRESH_DIAG §3 第 3 条(规格辖域)+IMPL_DESIGN §2.4'),
    ('refresh', 'crisis_refresh_invariant'): Contract(
        None, 'P36-a 危机不变式(executor 结构位,本域纯数供对拍)',
        'IMPL_DESIGN §4.2.1 R1-11 行'),
    ('refresh', 'hard_node_reinforce_gate'): Contract(
        None, 'D-D 硬节点补强门(结构门,数值加权挂标定批)',
        'IMPL_DESIGN D-D'),
    # —— criteria/stockpile ——
    ('stockpile', 'stockpile_buy'): Contract(
        _s_reserve_line_formed,
        'M6 压库买入(S 预留消费位):辖 M6,前提=目标线成型',
        'ZERO_REFRESH_DIAG §3 第 3 条+IMPL_DESIGN §3.2 ③'),
    # —— criteria/equipment ——
    ('equipment', 'wear_release'): Contract(
        None, 'D-B 穿戴释放三态门(M7 消费的判据输入)', 'IMPL_DESIGN D-B'),
    ('equipment', 'affix_allocation'): Contract(
        None, 'D-F46 词缀条件装备分配排序(谓词非发射)', 'IMPL_DESIGN D-F46'),
    ('equipment', 'keep_policy'): Contract(
        None, '近兑现距离绝不喂(P42 ③ 零参数公理)', 'IMPL_DESIGN §2.6'),
    ('equipment', 'endgame_context'): Contract(
        None, 'D-P3 收尾段语境输入(r_remaining 现读)', 'IMPL_DESIGN D-P3'),
    # —— 第七面「换线」(proof 判据面函数位;影子面,前提核验随实装
    #    接线批落位——见模块 docstring 辖外声明)——
    ('proof', 'stop_buy'): Contract(
        None, '停买谓词(分类,非发射;输入=K/持有名单)', 'IMPL_DESIGN §4.2.1'),
    ('proof', 'should_switch'): Contract(
        None, '换线事件发射位(影子面:登记遥测,不写 target_comp)',
        'IMPL_DESIGN §4.2.1 R197 症2 行'),
    ('proof', 'signal_arm'): Contract(
        None, '直通信号臂(两臂同开,证明层状态驱动)', 'IMPL_DESIGN §4.2.1 R11-3 行'),
    # —— 三先例的非 criteria 消费位 ——
    ('mandate', 'dominance_buy'): Contract(
        _s_reserve_line_formed,
        'M2 前置支配买入(S 预留消费位,mandate.check_s_reserve 消费面):'
        '辖 dominance_buy,前提=目标线成型',
        'ZERO_REFRESH_DIAG §3 第 3 条+IMPL_DESIGN §3.2 ③'),
    ('predicates', 'arm1_existence'): Contract(
        _arm1_cap_level_driven,
        'M3 触发信号:前提=deploy_cap 等级驱动口径(禁固定槽表常数)',
        'ZERO_REFRESH_DIAG §4.2+statefn/predicates.arm1_existence 注释'),
    ('predicates', 'arm0_level_lag'): Contract(
        None,
        'arm0 升级授权触发谓词 v2(14号稿 §4.2 A4 现量版):need=期望态'
        '现量(排除谓词 (名,星) 口径,Y3),level 消费只认 level_readable '
        '可信位(C4,不可信帧消费端 fail 向分键 arm0_level_unreadable)'
        '——前提零槽位依赖(全量期望态现读,零新自由参数)',
        '14_p1_consume_arms §4.2/§7.1 mandate.py 行(2026-09-05 对抗收敛)'),
    # —— 第三病灶(K 空窗回退)消费位 ——
    ('shop', 'k_projection'): Contract(
        _k_projection_domain_full,
        '商店线方向 pass K 投影:前提=战略层产物 target_comp 值域全集'
        '含 None——回退辖三带(FIX_REVIEW_20260903 R3 扩域:P1 空窗带'
        '=hoard_target_set 四体系全集 / P1 锁线过渡带=p1_early_pair '
        'top-2 方向 / P2+ 带=hoard_target_set 绯英⑤兜底·跨线骨架·'
        '降格满配),单一源=cw_intention(禁复制);供给在场而回退解析'
        '空集即违例',
        'SEEDS_EMPTY_LEDGER_DIAG §3/§4(2026-09-03 第三病灶裁定)'
        '+FIX_REVIEW_20260903 ②旧核缺口 1/2/3+IMPL_DESIGN §4.2.2 规格补注'),
}


def ensure_contract(fn_key: tuple[str, str], ctx: ContractCtx,
                    counters: dict | None = None) -> bool:
    """判据契约核验(接线消费位入口;IMPL_DESIGN §4.2.2)。

    返回 True=前提成立,判据照常求值/发射;False=前提不成立,该判据
    本帧**弃权** + ``criteria_contract_violation:<模块>.<函数>`` 计数
    (键登记=design_telemetry 文末 R198 节,分键=判据名)。

    fail-closed 不抛异常不断局:键未登记(注册完备性缺口)与谓词异常
    均按违例处置(弃权+计数),由消费位跳过该判据本帧求值。
    """
    name = f'{fn_key[0]}.{fn_key[1]}'
    contract = CONTRACTS.get(fn_key)
    if contract is None or contract.precondition is None:
        if contract is None:
            if counters is not None:
                key = f'criteria_contract_violation:{name}'
                counters[key] = counters.get(key, 0) + 1
            return False
        return True
    try:
        ok = contract.precondition(ctx)
    except Exception:
        ok = False      # 谓词异常=fail-closed(弃权,不抛出)
    if not ok and counters is not None:
        key = f'criteria_contract_violation:{name}'
        counters[key] = counters.get(key, 0) + 1
    return ok
