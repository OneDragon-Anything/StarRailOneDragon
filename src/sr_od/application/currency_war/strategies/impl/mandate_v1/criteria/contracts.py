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
(R197 症2 裁决:换线权威=意向状态机,本模块只产遥测;02_mandate_layer
§2/§7 权限划界),其行为接线=过线后批——本表
只登记判据面三函数位,前提核验随实装接线批落位。
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
      空元组」复发形态,违例——p1 带恒违例;p2plus 带合法空须携带
      k_fallback_source 证据,见该字段)。
    - k_fallback_band:分带 token(cw_intention.k_empty_window_fallback
      第二返回值直传,零第二派生;P86 证明批 §4.6-1)。空窗期待按带
      非对称:p1 带(p1_gap/p1_lock_band)回退集注册表派生构造性非空;
      p2plus 带落码后空集合法(丙臂守息帧)。None = 带未知,按 p1 带
      保守期待处置(空 = 违例)。
    - k_fallback_source:p2plus 带合法空的来源证据(P86 证明批 §4.6-2;
      合法值 = cw_intention.K_FALLBACK_SOURCE_THREE_ARM——判据臂评估
      产出)。无来源标记的空集 = 复发形态,违例(检测力不松动)。
    - locked_buy_members:锁定帧买侧采购集实解析
      (cw_intention.locked_buy_membership 返回物)。合法形态 = None
      (未锁帧/锁定解析空,消费位按未锁处置)或非空 frozenset(锁线态);
      其他对象 = 「字面量冒充解析结果」复发形态,违例。消费位 =
      C1 核心卡通道契约(ADR-0569)。
    """

    k_members: tuple[str, ...] | None = None
    gold: int | None = None
    reserve: int | None = None
    deploy_cap: int | None = None
    ev_slot: object | None = field(default=None)
    k_target: object = field(default=None)
    k_fallback_available: bool = field(default=False)
    k_fallback_resolved: object = field(default=None)
    k_fallback_band: str | None = field(default=None)
    k_fallback_source: str | None = field(default=None)
    locked_buy_members: object | None = field(default=None)


def _s_reserve_line_formed(ctx: ContractCtx) -> bool:
    """先例①前提:S 预留只在对目标线成型的语境下预留(禁恒预留)。

    规格辖域裁决(ZERO_REFRESH_DIAG §3 第 3 条,原文):硬约束③ S 预留
    拦截对象列=「EV 买入面(序 3-5 追加支出,stockpile 等)+ M6 +
    dominance_buy(R32-3)」——前提=目标线 K 已成型(k_members 非空):
    无目标线语境下的恒量预留即「语境前提未被核验」缺陷形态
    (R196 ``_s_reserve`` 恒 54 同型,diag §3 挂账项)。

    **P86 带维度扩展(无目标期三臂判据落码批;证明批 §4.3 裁决②)**:
    k_members 空且系三臂判据评估产出的合法空(k_target=None ∧ 回退供给
    在场 ∧ 实解析空集 ∧ p2plus 带证据 source 齐备)时前提放行——该帧不
    存在「为目标线预留」语境,S 预留原始禁令对象(无目标语境恒量预留,
    R196 同型)不成立;溢余带必花通道(dominance/EV,ADR-0528)按裁决②
    「必花域维持」不以本前提误伤,其自身带判据/候选门照旧辖。证据要件
    与 k_projection 契约同构(F-9 防御纵深:band='p2plus' ∧ source=
    three_arm 双核,无来源空不放行,两谓词判定一致);供给缺帧
    (k_fallback_available False)维持旧违例语义(无评估证据的空 =
    复发形态)。"""
    if ctx.k_members:
        return True
    from sr_od.application.currency_war.kernel.cw_intention import (
        K_FALLBACK_SOURCE_THREE_ARM,
    )
    return (ctx.k_target is None and ctx.k_fallback_available
            and not ctx.k_fallback_resolved
            and ctx.k_fallback_band == 'p2plus'
            and ctx.k_fallback_source == K_FALLBACK_SOURCE_THREE_ARM)


def _gold_minus_reserve_ctx(ctx: ContractCtx) -> bool:
    """先例②前提:r2 预算门消费「金−预留」语境(两个现读输入在场)。

    规格:金−预留 ≥ 刷价才批(refresh.r2_budget);前提=消费位给的是
    决策帧现读金与预留值(均非 None)——缺任一即语境未核验,弃权。
    辖域澄清(diag §3 第 3 条):付费刷新 r2 预算门**不在** S 预留
    拦截对象列,预留此处是预算语境输入而非硬约束③预留。
    """
    return ctx.gold is not None and ctx.reserve is not None


def _budget_gate_ctx(ctx: ContractCtx) -> bool:
    """P71-b 预算闸前提(ADR-0560):现读金与等级驱动 cap 在场。

    闸值分量 g* 依赖 cap_resolved(消费位传 cap_resolved_of_session
    口径)、闸比较依赖决策帧现读金——缺任一即语境未核验,弃权
    (fail-closed,与先例②同型)。ρ/Σ预留分量对合格集空自带 0 兜底
    (refresh.r2_card_reserve 契约),不另设前提。
    """
    return ctx.gold is not None and ctx.deploy_cap is not None


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
    ``state_of(session).target_comp`` 的值域含 None(P1 空窗=开局常态),消费端
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

    **带维度非对称期待(P86 落码批,证明批 §4.6)**:p1 带
    (p1_gap/p1_lock_band)回退集注册表派生构造性非空,空 = 复发违例
    (检测力保留);p2plus 带落码后空集合法(两臂皆空 → 丙臂守息帧),
    但合法空必须携带来源证据——``k_fallback_source`` ==
    cw_intention.K_FALLBACK_SOURCE_THREE_ARM(判据臂评估产出)才放行,
    无来源空 = 复发形态守卫不松动。分期接线:退役常量在位期 p2plus
    解析恒非空,本分支无行为面。"""
    if ctx.k_target is not None:
        return True
    if not ctx.k_fallback_available:
        return True
    if ctx.k_fallback_resolved:
        return True
    if ctx.k_fallback_band == 'p2plus':
        # 延迟 import(内核→契约面单向依赖;常量单一源在 cw_intention)
        from sr_od.application.currency_war.kernel.cw_intention import (
            K_FALLBACK_SOURCE_THREE_ARM,
        )
        return ctx.k_fallback_source == K_FALLBACK_SOURCE_THREE_ARM
    return bool(ctx.k_fallback_resolved)


def _core_channel_locked_ctx(ctx: ContractCtx) -> bool:
    """C1 核心卡通道前提(ADR-0569):锁线态语境,可核验派生形态。

    前提 = ctx.locked_buy_members 系 cw_intention.locked_buy_membership
    实解析物且非空(锁线态);None = 未锁帧,通道不评估(设计判据式
    前件,合法 fail 方向非违例)。空 frozenset / 非 frozenset 对象 =
    「字面量冒充解析结果」复发形态,违例弃权。
    """
    return (isinstance(ctx.locked_buy_members, frozenset)
            and bool(ctx.locked_buy_members))


@dataclass(frozen=True)
class Contract:
    """单判据契约:前提谓词(None=无条件)+ 辖域声明 + 规格锚。

    前提谓词签名统一 ``ContractCtx -> bool``;None=前提恒真(仍需
    显式登记辖域声明,防「未审计」与「无条件」混淆)。
    """

    precondition: Callable[[ContractCtx], bool] | None
    scope: str     # 辖域声明一句(该判据语境前提的适用面)
    anchor: str    # 规格锚(现行文档节/引理号/符号名;历史 IMPL_DESIGN 节号已重锚,映射=ADR-0644)


#: (模块, 函数) → Contract。键集与 criteria 全公开函数对拍(静态
#: 完备性测试,漏登记=测试红);非 criteria 键(三先例+K 空窗回退
#: 消费位)单列。
CONTRACTS: dict[tuple[str, str], Contract] = {
    # —— criteria/buy ——
    ('buy', 'ev_buy_candidates'): Contract(
        _s_reserve_line_formed,
        'EV 买候选(S 预留消费位):辖 EV 买面,前提=目标线成型',
        'ZERO_REFRESH_DIAG §3 第 3 条(硬约束③拦截对象列)+02_mandate_layer §4 ③'),
    ('buy', 'ev_buy_veto'): Contract(
        None, 'EV 买否决门(随候选流一体;R7-1 发射面后半)',
        'BYPASS_TABLE 对应行(criteria/__init__.py 单一源;buy.ev_buy_* 行)'),
    # ('buy', 'p2_lock_buy') 契约键已随 P25 占位接管批删除(ADR-0569):
    # 占位函数与 BYPASS_TABLE 行同批清,P25 数值语义唯一载体 = C1 通道
    # 数值支(挂账不落码,设计 §4 P25 行),消双源。
    # —— criteria/sell ——
    ('sell', 'line_switch_sell'): Contract(
        None, '换线塌缩出口:前提=K 已切换(判据自带 k_switched 门)',
        '01_math_framework §3.2(卖)'),
    ('sell', 'sell_for_interest'): Contract(
        None, '凑息档 EV 面(T_SEARCH 缺省 fail-closed 自带)',
        '01_math_framework §3.2+P41 桶不动资格(R20-1)'),
    ('sell', 'funding_support_sell'): Contract(
        None, '支付支撑通道(两臂同开;触发=金不足自带 gold<need 门)',
        '02_mandate_layer §2/§7+BYPASS_TABLE 行(R13-5/R14-4 支付支撑通道)'),
    # —— criteria/levelup ——
    ('levelup', 'arm2_schedule'): Contract(
        None, 'arm2 调度门(结构守息门,零 λ 依赖)', 'BYPASS_TABLE 对应行(门)'),
    ('levelup', 'saturation_floor'): Contract(
        None, '守息线 g*=10×cap_resolved 重导出(interest.saturation_line 单一源)',
        '01_math_framework §3.3+interest.saturation_line(R70-1 参数化)'),
    ('levelup', 'spend_unified'): Contract(
        None, 'P48 整买纪律(M3 义务侧消费)',
        'P48 命题+11_shop_decisions(D-BUYNOTE 修复池编号,原文=ADR-0644 取回)'),
    ('levelup', 'batch_form'): Contract(
        None, '批量成型判据(M3 义务侧消费)', '01_math_framework §3.3'),
    ('levelup', 'lv9_stop'): Contract(
        None, '等级上限停(历史键名;单一源=注册表 level_max,消费位传'
        '上下文注册表 .level_max,sim 经注入视图;义务侧消费)',
        '01_math_framework §3.3'),
    ('levelup', 'level_spend_blocked'): Contract(
        None, '危机带经验授权让位(候选③;判据自带 ALL IN 豁免与 '
        'hp 不可信 fail-closed,前提恒真)',
        'g_20260904_054904 候选③+P21/P48 λ>0 段(discipline 单一源)'),
    ('levelup', 'pop_slot'): Contract(
        None, 'D-lv7 OPEN 检查点(满编+富金+候补升 cap)',
        'D-lv7 修复池(原文=ADR-0644 取回;现行=本判据与决策迹)'),
    ('levelup', 'levelup_budget_gate'): Contract(
        _budget_gate_ctx,
        'P72 (3) 全段预算闸(ADR-0576;P71-b 溢余段形态全段化):前提='
        '现读金与等级驱动 cap 在场(息档 τ 与退化锚 g* 依赖 '
        'cap_resolved 口径,禁固定常数;ALL IN 豁免与支A 兑现链在'
        '判据体内自判,不另设前提)',
        'p72-full-band-budget-gate §1+§2.5+ADR-0576'),
    # —— criteria/refresh ——
    ('refresh', 'r0_stop'): Contract(
        None, 'R0 维持结构门(结构位,输入=店面快照+金,恒良定义)',
        'BYPASS_TABLE 对应行(R10-3 结构位)'),
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
        'ZERO_REFRESH_DIAG §3 第 3 条(规格辖域)+01_math_framework §3.4'),
    ('refresh', 'crisis_refresh_invariant'): Contract(
        None, 'P36-a 危机不变式(executor 结构位,本域纯数供对拍)',
        'BYPASS_TABLE 对应行(结构不变式;R1-11)'),
    ('refresh', 'hard_node_reinforce_gate'): Contract(
        None, 'D-D 硬节点补强门(结构门,数值加权挂标定批)',
        'D-D 修复池(原文=ADR-0644 取回;现行=本判据)'),
    ('refresh', 'r2_card_reserve'): Contract(
        None, 'R2 预算门 Σ预留卡价 ρ 公共单一源(注册表现读纯函数;'
        'R2 门与 P71-b 预算闸同源消费,ADR-0560 提升批)',
        'P54-r2-interest-floor §②+ADR-0560'),
    ('refresh', 'all_channel_buy_exists'): Contract(
        None, 'P92 全通道可实现买入集判定尺(R1 发射前存在性门;'
        'p40 R0-1 席满维在册语义落地,非新门——math_proofs P92 '
        '「在册结构的严格化」口径;T-263 批)',
        'math_proofs P92 行+p40-refresh-ev §② R0-1'),
    ('refresh', 'qualified_member_costs'): Contract(
        None, '合格集费带单一源(P91 压库同轴带 + R2 预留卡价同源消费;'
        '注册表现读纯函数;T-263 批)',
        'math_proofs P91 行+p54-r2-interest-floor §②'),
    # —— criteria/stockpile ——
    ('stockpile', 'stockpile_buy'): Contract(
        _s_reserve_line_formed,
        'M6 压库买入(S 预留消费位):辖 M6,前提=目标线成型',
        'ZERO_REFRESH_DIAG §3 第 3 条+02_mandate_layer §4 ③'),
    # —— criteria/equipment ——
    ('equipment', 'wear_release'): Contract(
        None, 'D-B 穿戴释放三态门(M7 消费的判据输入)',
        '18_equip_wear_semantics(D-B 穿戴释放语义)'),
    ('equipment', 'affix_allocation'): Contract(
        None, 'D-F46 零调用面墓碑:词缀分配生产单一源 = '
        'cw_equip_env.resolve_affix_priority_order(cw_op_equip_all 消费);'
        '本函数系孤儿第二实现+死键,已随判据出处纠错批物理删除,'
        '登记行保留契约枚举完备性', '18_equip_wear_semantics(D-F46 词缀分配)'),
    ('equipment', 'keep_policy'): Contract(
        None, '近兑现距离绝不喂(P42 ③ 零参数公理)', '01_math_framework §3.6'),
    ('equipment', 'endgame_context'): Contract(
        None, 'D-P3 收尾段语境输入(r_remaining 现读)',
        'D-P3 修复池(原文=ADR-0644 取回)'),
    # —— 第七面「换线」(proof 判据面函数位;影子面,前提核验随实装
    #    接线批落位——见模块 docstring 辖外声明)——
    ('proof', 'stop_buy'): Contract(
        None, '停买谓词(分类,非发射;输入=K/持有名单)',
        'BYPASS_TABLE 对应行(谓词)+02_mandate_layer §3'),
    ('proof', 'should_switch'): Contract(
        None, '换线事件发射位(影子面:登记遥测,不写 target_comp)',
        'BYPASS_TABLE 对应行(换线事件影子面;R197 症2 换线权威=意向状态机)'),
    ('proof', 'signal_arm'): Contract(
        None, '直通信号臂(两臂同开,证明层状态驱动)',
        'BYPASS_TABLE 对应行(两臂同开;R11-3 直通信号臂)'),
    # —— 三先例的非 criteria 消费位 ——
    ('mandate', 'dominance_buy'): Contract(
        _s_reserve_line_formed,
        'M2 前置支配买入(前提=目标线成型):R32-3 规格拦截对象列虽含 '
        'dominance_buy,其金位面实接线为结算线地板(shop.check_settlement_'
        'line,截断口径),与 s_reserve 可变现口径不同源不同面,'
        '非 mandate.check_s_reserve 消费位(T-193;ADR-0624)',
        'ZERO_REFRESH_DIAG §3 第 3 条+02_mandate_layer §4 ③'),
    ('mandate', 'core_single_card_buy_eligible'): Contract(
        _core_channel_locked_ctx,
        'C1 直通核心卡支配性支资格门:前提=锁线态(锁定采购集实解析在'
        '场;未锁帧通道不评估)',
        '设计《直通核心卡信号层入口》§2 案A+§4 P25 行(ADR-0569)'),
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
        '含 None——回退辖三带(P1 空窗带=hoard_target_set 四体系全集 / '
        'P1 锁线过渡带=p1_early_pair top-2 方向 / P2+ 带=三臂判据'
        '[P86:甲臂判活=机器强锁门逐字方向采购集;甲臂空=合法空集'
        '(丙臂守息,须携带 k_fallback_source=three_arm 证据;'
        'weak/demoted 分带仍走跨线骨架)]),单一源=cw_intention(禁复制);'
        '供给在场而回退解析空集即违例(p1 带恒违例;p2plus 带无来源'
        '证据的空集违例)',
        'SEEDS_EMPTY_LEDGER_DIAG §3/§4(2026-09-03 第三病灶裁定)'
        '+FIX_REVIEW_20260903 ②旧核缺口 1/2/3'
        '+K 空窗回退规格补注(原 IMPL_DESIGN §4.2.2 R198b 标,ADR-0644)'
        '+P86 证明批 §4.6(带维度非对称期待)'),
}


def ensure_contract(fn_key: tuple[str, str], ctx: ContractCtx,
                    counters: dict | None = None) -> bool:
    """判据契约核验(接线消费位入口;纪律单一源=本模块 CONTRACTS)。

    返回 True=前提成立,判据照常求值/发射;False=前提不成立,该判据
    本帧**弃权** + ``criteria_contract_violation:<模块>.<函数>`` 计数
    (键写点=本函数计数器,分键=判据名;登记节原文已删档,取回=ADR-0644)。

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
