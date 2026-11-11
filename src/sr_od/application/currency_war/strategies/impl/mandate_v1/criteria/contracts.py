"""cw4 判据契约层(assume-guarantee 纪律;2026-09-03 用户批准的组合性改进①)。

单一源=本模块 ``CONTRACTS``(循同包 ``BYPASS_TABLE`` 先例:注册表 +
静态完备性交叉核对测试)。缺陷背景:零刷新/arm1 两案均为「语境前提未被
核验」类缺陷——r1 EV 输入字面量 ``None`` 绕过前提
(ZERO_REFRESH_DIAG §4.1 实现缺口)、arm1 拿固定槽表常数当阈值域错位
(ZERO_REFRESH_DIAG §4.2)。契约化 = 把每个判据的**语境前提**写成谓词级
契约,接入调用处(entry.py / shop.py 判据消费位)经 ``ensure_contract``
核验:前提不成立 ⇒ 该判据本帧**弃权**(不发出/不求值)+
``criteria_contract_violation:<判据名>`` 计数——禁静默执行;fail-closed
不抛异常不断局(谓词异常同判弃权)。契约层只加前提核验,**禁改判据
数学**(判据本体函数零触碰)。

覆盖外声明:换线判据族(should_switch/回锁窗/干旱计数/证据门影子评估)
已删除(随候选-锁定制整体)(见 proof.py 停用申报,git 历史可溯),
无行为接入调用遗留。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class ContractCtx:
    """契约核验的决策帧上下文(消费点现读快照;谓词按需取字段)。

    字段取值时机=判据消费点当帧现读(非生成期快照);缺失语义=
    None(谓词按「语境前提是否成立」各自解读,不在此默认)。

    - k_members:目标线 K 成员名元组(predicates.line_members 产物;
      空/None=目标线未成型)。
    - gold:决策帧金(消费位口径——商店波为支出后逻辑态金)。
    - reserve:S 预留值(消费位现读,如 b_target 组装结果)。
    - k_target:战略层产物 target_comp **原值**(k_projection 前提的
      可核验派生输入,原声明位 ``k_none_domain_covered=True`` 改造)。
    - k_fallback_available:K 回退供给是否在场(消费位从
      v3_intention 在场性派生;缺供给帧=保守侧不回退,合法)。
    - k_fallback_resolved:消费位**实解析**的回退成员集(单一源
      cw_intention 调用的返回物;供给在场而解析为空 = 「回退字面量
      空元组」复发形态,违例——两带均构造性非空,恒违例)。
    - k_fallback_band:分带 token(cw_intention.k_empty_window_fallback
      第二返回值直传,零第二派生)。值域 = p1_gap/p1_lock_band 两带
      (换轴:旧 p2plus 位面带废除——未终局锁定帧过渡层照常活跃,
      回退 = 见即买并集构造性非空)。None = 带未知,按保守期待
      处置(空 = 违例)。
    """

    k_members: tuple[str, ...] | None = None
    gold: int | None = None
    reserve: int | None = None
    k_target: object = field(default=None)
    k_fallback_available: bool = field(default=False)
    k_fallback_resolved: object = field(default=None)
    k_fallback_band: str | None = field(default=None)


def _s_reserve_line_formed(ctx: ContractCtx) -> bool:
    """先例①前提:S 预留只在对目标线成型的语境下预留(禁恒预留)。

    规格适用范围裁决(ZERO_REFRESH_DIAG §3 第 3 条,原文):硬约束③ S 预留
    拦截对象列=「EV 买入面(序 3-5 追加支出,stockpile 等)+ M6」
    (dominance_buy 行已随通道退役删除——富余买入并入 M6 一星兜底带,
    20 号稿 §3 出口序申报行;前提=目标线 K 已成型(k_members
    非空)):
    无目标线语境下的恒量预留即「语境前提未被核验」缺陷形态
    (R196 ``_s_reserve`` 恒 54 同型,diag §3 待办项)。

    **带维度非对称期待(修订——换轴后 p2plus 位面带废除)**:两带
    (p1_gap/p1_lock_band)回退集均构造性非空(见即买并集/条目集),
    空 = 复发违例(检测力保留);供给缺帧(k_fallback_available
    False)维持旧违例语义(无评估证据的空 = 复发形态)。"""
    return bool(ctx.k_members)


def _gold_minus_reserve_ctx(ctx: ContractCtx) -> bool:
    """先例②前提:r2 预算门消费「金−预留」语境(两个现读输入在场)。

    规格:金−预留 ≥ 刷价才批(refresh.r2_budget);前提=消费位给的是
    决策帧现读金与预留值(均非 None)——缺任一即语境未核验,弃权。
    适用范围澄清(diag §3 第 3 条):付费刷新 r2 预算门**不在** S 预留
    拦截对象列,预留此处是预算语境输入而非硬约束③预留。
    """
    return ctx.gold is not None and ctx.reserve is not None


def _k_projection_domain_full(ctx: ContractCtx) -> bool:
    """先例(K 空窗回退,第三病灶)前提:战略层产物字段值域全集含
    空窗期——K 投影域覆盖 None。

    K 投影 None 值域裁定(git 历史可溯):
    ``state_of(session).target_comp`` 的值域含 None(P1 空窗=开局常态),消费端
    把 None 当「已终局阵容锁定状态」直接投影(``line_members(None)→()``)=
    「单一值域的一端当全域」域错位(arm1 cap 口径/零刷新 r1 输入同型
    第三例)——空窗死锁环:K 空→零买入→板面零变化→永不锁。
    **可核验派生形态(防线硬化+R3 扩域)**:值域
    全集声明覆盖两带(空窗带/候选首位带——换轴后值域,任意位面同判),
    前提不再采信消费位硬编码声明,而是核验实解析结果——``k_target``
    非 None(终局锁定状态)= 无回退义务,恒过;``k_target`` None 且
    供给缺帧(``k_fallback_available`` False)= 保守侧不回退,合法
    fail 方向(与 committed_authority 缺供给同款);供给在场而
    ``k_fallback_resolved`` 为空 = 「回退字面量空元组但保留声明」
    复发形态,违例弃权。回退单一源=cw_intention.k_empty_window_fallback
    (p1_gap 带 hoard 回退 / p1_lock_band 带候选首位条目见即买集,
    禁复制见即买并集逻辑)。

    **带维度非对称期待(修订——换轴后 p2plus 位面带废除)**:两带
    (p1_gap/p1_lock_band)回退集均构造性非空(见即买并集/条目集),
    空 = 复发违例(检测力保留);供给缺帧(k_fallback_available
    False)维持旧违例语义(无评估证据的空 = 复发形态)。"""
    if ctx.k_target is not None:
        return True
    if not ctx.k_fallback_available:
        return True
    return bool(ctx.k_fallback_resolved)


@dataclass(frozen=True)
class Contract:
    """单判据契约:前提谓词(None=无条件)+ 适用范围声明 + 规格基准。

    前提谓词签名统一 ``ContractCtx -> bool``;None=前提恒真(仍需
    显式登记适用范围声明,防「未审计」与「无条件」混淆)。
    """

    precondition: Callable[[ContractCtx], bool] | None
    scope: str     # 适用范围声明一句(该判据语境前提的适用面)
    anchor: str    # 规格基准(现行文档节/引理号/符号名;历史 IMPL_DESIGN 节号已重定基准,映射见 git 历史)


#: (模块,函数) → Contract。键集与 criteria 全公开函数交叉核对(静态
#: 完备性测试,漏登记=测试红);非 criteria 键(三先例+K 空窗回退
#: 消费位)单列。
CONTRACTS: dict[tuple[str, str], Contract] = {
    # —— criteria/buy ——
    ('buy', 'ev_buy_candidates'): Contract(
        _s_reserve_line_formed,
        'EV 买候选(S 预留消费位):辖 EV 买面,前提=目标线成型',
        '02_mandate_layer §4(硬约束封闭定义)'),
    ('buy', 'ev_buy_veto'): Contract(
        None, 'EV 买否决门(随候选流一体;R7-1 发射面后半)',
        'BYPASS_TABLE 对应行(criteria/__init__.py 单一源;buy.ev_buy_* 行)'),
    # —— criteria/sell ——
    ('sell', 'sell_for_interest'): Contract(
        None, '凑息档 EV 面(T_SEARCH 缺省 fail-closed 自带)',
        '01_math_framework §3.2+P41 桶不动资格'),
    ('sell', 'funding_support_sell'): Contract(
        None, '支付支撑通道(两臂同开;触发=金不足自带 gold<need 门)',
        '02_mandate_layer §2/§7+BYPASS_TABLE 行(支付支撑通道)'),
    # —— criteria/levelup(11 号稿 §2;判据组 = 触发三分派/概率带/
    #    整买纪律/等级帽/资金线门)——
    ('levelup', 'upgrade_trigger'): Contract(
        None,
        '升级触发单判据三分派(stay_gate/natural):辖锁定后 ∧ '
        'plane2_started 双条件,判据体内自判;前提恒真(旧人口位板满'
        '口径前提随人口位臂删除消亡)',
        '11_shop_decisions §2 升级触发行(用户裁定 2026-10-18)'),
    ('levelup', 'prob_band_of_cost'): Contract(
        None, '最优概率带查表(REFRESH_PROB 1..9 域内峰值区间,平顶'
        '整段;输入全为游戏定义量)',
        '11_shop_decisions §2 停留门(带模型)'),
    ('levelup', 'spend_unified'): Contract(
        None, 'P48 整买纪律(M3 义务侧消费)',
        'P48 命题+11_shop_decisions(D-BUYNOTE 修复池编号,原文考古走 git 历史)'),
    ('levelup', 'lv9_stop'): Contract(
        None, '等级上限停(历史键名;单一源=注册表 level_max,消费位传'
        '上下文注册表 .level_max;义务侧消费)',
        '01_math_framework §3.3'),
    ('levelup', 'xp_ledger_stop'): Contract(
        None, 'XP 期望账本升级停(lv9_stop 轮内盲区补位;与 lv9_stop '
        '同位合取消费,消费位=shop M3 批/shop 溢余段 L3;live level_max=10 '
        '无门槛表项判据不辖,行为零变更)',
        'kernel/cw_economy.xp_apply_clicks 推进算子单一源'),
    ('levelup', 'fund_line_gate'): Contract(
        None, '升级资金线门(现金口径单门,花后金 ≥ saturation_line;'
        '出辖两支 = 终局域末战 ALL IN/买断制,判据体内自判)——前提恒真',
        '11_shop_decisions §2 资金线门行'),
    # —— criteria/refresh ——
    ('refresh', 'refresh_warranted'): Contract(
        None,
        '三段式刷新判据主式(查表零计算:P1 恒不刷'
        '〔plane2_started 谓词〕/P2 未锁窗口候选缺件/锁定后星级目标'
        '——带归属绑定 = 当前停留目标的带);目标可买合取已随预测门'
        '退役删除(11 号稿 §3 预测门整拆——刷新时点'
        '预测不可算,判据收敛三分派,拒因键 target_unbuyable 同批'
        '退役);无标定槽位依赖',
        '11 号稿 §3(用户裁定「期望价值难算不'
        '直观,星级目标直接驱动」——R1 路径总账判据面退役的替代面;'
        '预测门整拆)'),
    ('refresh', 'r2_budget'): Contract(
        _gold_minus_reserve_ctx,
        '付费刷新预算门:前提=金−预留语境(现读金与预留均在场;'
        'r2 不在硬约束③ S 预留拦截对象列)',
        'ZERO_REFRESH_DIAG §3 第 3 条(规格辖域)+01_math_framework §3.4'),
    ('refresh', 'r2_card_reserve'): Contract(
        None, 'R2 预算门卡价预留 ρ 单一源(停留目标实费档现读纯函数;'
        '锁定支恒有值,未锁窗口恒 0——两分支口径分行声明)',
        '2026-10-28 用户裁定实费档实现口径(停留目标 = '
        'stay_target_of 单一源)'),
    ('refresh', 'qualified_member_costs'): Contract(
        None, '合格集费带单一源(P91 压牌库同轴带单一消费源;'
        '注册表现读纯函数;T-263 批)',
        'math_proofs P91 行'),
    # —— criteria/stockpile ——
    ('stockpile', 'stockpile_buy'): Contract(
        _s_reserve_line_formed,
        'M6 压库买入(S 预留消费位):辖 M6,前提=目标线成型',
        'ZERO_REFRESH_DIAG §3 第 3 条+02_mandate_layer §4 ③'),
    # —— criteria/equipment(D-P3 待办登记载体,勿删)——
    # 修复池项 OPEN 维持待办登记(定案手段 = 实机 boss 掉血分布交叉核对,
    # 从未执行),复活须先「交叉核对定案→三形态标注→实现」全流程。
    ('equipment', 'endgame_context'): Contract(
        None, 'D-P3 修复池项 OPEN 登记成待办不变(定案手段 = 实机 boss 掉血'
        '分布对拍,从未执行),复活须先「对拍定案→三形态标注→已写进代码」'
        '全流程', 'D-P3 修复池(原文考古走 git 历史)'),
    # —— 第七面「换线」残留件(换线判据族
    #    (should_switch/signal_arm/证据门影子评估)已随候选-锁定制
    #    删除——见模块 docstring 覆盖外声明与 proof.py 停用申报)——
    ('proof', 'stop_buy'): Contract(
        None, '停买谓词(分类,非发射;输入=K/持有名单)',
        'BYPASS_TABLE 对应行(谓词)+02_mandate_layer §3'),
    # —— 三先例的非 criteria 消费位 ——
    # (契约键 ('mandate','dominance_buy') 已随 dominance_buy 通道退役
    #  整删——富余买入并入 M6 一星兜底带(20 号稿 §3 出口序申报行),
    #  S 预留语境前提由 M6 侧
    #  ('stockpile','stockpile_buy') 键继续承载。)
    # (契约键 ('mandate','core_single_card_buy_eligible') 已随 C1 支
    #  退役整删——卖出身份段退役批,git 历史可溯。)
    # —— 第三病灶(K 空窗回退)消费位 ——
    ('shop', 'k_projection'): Contract(
        _k_projection_domain_full,
        '商店线方向 pass K 投影:前提=战略层产物 target_comp 值域全集'
        '含 None——回退辖两带(空窗带=hoard 回退见即买并集 / '
        '候选首位带=过渡候选首位条目见即买集;换轴后任意位面同判,'
        '旧 P2+ 位面带已废),单一源=cw_intention(禁复制);'
        '供给在场而回退解析空集即违例(两带均构造性非空)',
        'K 投影 None 值域裁定(git 历史可溯)'
        '+旧核缺口审查修订(git 历史可溯)'
        '+K 空窗回退规格补注(git 历史可溯)'
        '+proofs/p86-proof-batch.md §4.6(带维度非对称期待;甲/乙臂退役修订;'
        '换轴再修订,git 历史可溯)'),
}


def ensure_contract(fn_key: tuple[str, str], ctx: ContractCtx,
                    counters: dict | None = None) -> bool:
    """判据契约核验(接入调用消费位入口;纪律单一源=本模块 CONTRACTS)。

    返回 True=前提成立,判据照常求值/发出;False=前提不成立,该判据
    本帧**弃权** + ``criteria_contract_violation:<模块>.<函数>`` 计数
    (键写点=本函数计数器,分键=判据名;登记节原文已删除,细节见 git 历史)。

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
