"""cw4 EV 判据层(criteria 七面)——IMPL_DESIGN §6.4-R 步4,§2 落码映射。

§1 包树:buy/sell/levelup/refresh/stockpile/equipment 六模块(第七面
「换线」在 proof/line_selector,R1-3)。判据族数学口径已迁
design_economy.md §E1-§E3(本包实现消费 statefn 单一源,禁自算状态量)。

**臂①旁路集函数级枚举表**(§4.2.1,R5-4 类别分列 + R7-1 第四类「发射面」)
= 本模块 ``BYPASS_TABLE``,旁路枚举对拍测试的单一源。类别合法值 =
发射位 / 门 / 谓词 / 状态函数 / 发射面(复合)/ 支付支撑通道;
``arm1`` 列 = 臂①形态(不旁路 / 旁路 / 旁路=门关闭 / 不旁路(两臂同开))。

修复池落点(R189-5 表):D-B/D-F46(equipment)、D-D(refresh+buy)、
D-F1(选卡 eval,pick 接口辖外——本包登记接口占位)、D-FM1(全局
candidates+economy sink)、D-P3(levelup+equipment)、D-BUYNOTE
(buy 内嵌 P48 整买纪律)。
"""
from __future__ import annotations

# (模块, 函数) → (类别, 臂①形态, 依据标签)
# 类别与臂①形态的合法配对 = §4.2.1 逐行;谓词/状态函数恒「不旁路」。
BYPASS_TABLE: dict[tuple[str, str], tuple[str, str, str]] = {
    # —— criteria/buy(§2.1;支配族 dominance_buy 已移 mandate 邻位,本域无)——
    ('buy', 'ev_buy_candidates'): (
        '发射面', '旁路', 'R2-2+R7-1(候选生成+否决门一体,整体不发射)'),
    ('buy', 'ev_buy_veto'): (
        '发射面', '旁路', '随 ev_buy_candidates 整体旁路(拆开=fail-open)'),
    # ('buy', 'p2_lock_buy') 行已随 P25 占位接管批删除(ADR-0569):与
    # 占位函数删除同批(P25 数值语义唯一载体 = C1 通道数值支,挂账不落
    # 码,设计 §4 P25 行);对拍测试双向强制(函数↔行,墓碑豁免另册)。
    # —— criteria/sell(§2.2;fuel_sell/protected_sell 在 mandate/predicates)——
    ('sell', 'line_switch_sell'): (
        '发射位', '旁路', 'R2-2(换线机关闭,塌缩出口无对象)'),
    ('sell', 'sell_for_interest'): (
        '发射位', '旁路', 'R5-4 补漏(凑息档 EV 追加发射)'),
    ('sell', 'funding_support_sell'): (
        '支付支撑通道', '不旁路(两臂同开)',
        'R13-5/R14-4(mandate=false+funding_support=true,臂间对称)'),
    # —— criteria/levelup(§2.3;arm1_existence 在 statefn/predicates)——
    ('levelup', 'arm2_schedule'): (
        '门', '旁路=门关闭', 'R5-4 范畴定谲(M3 触发退 arm1 单臂)'),
    ('levelup', 'spend_unified'): (
        '判据/闭式', '不旁路', '骨架层§3.5(3)(义务侧消费)'),
    ('levelup', 'batch_form'): (
        '判据/闭式', '不旁路', 'M3 义务侧消费'),
    ('levelup', 'lv9_stop'): (
        '判据/闭式', '不旁路', 'M3 义务侧消费'),
    ('levelup', 'level_spend_blocked'): (
        '谓词', '不旁路', '候选③(危机带经验授权让位;M3 两域发射位消费)'),
    ('levelup', 'pop_slot'): (
        '判据/闭式', '不旁路', 'D-lv7(OPEN 检查点;决策迹理由显式)'),
    ('levelup', 'saturation_floor'): (
        '状态函数', '不旁路', 'g*=10×cap_resolved 单一源重导出(R70-1)'),
    ('levelup', 'levelup_budget_gate'): (
        '门', '不旁路', 'P72 (3) 全段预算闸(p72-full-band-budget-gate'
        '+ADR-0576;P71-b 溢余段形态全段化,M3 两域+L3 发射位消费,'
        '义务侧量闸)'),
    # —— criteria/refresh(§2.4)——
    ('refresh', 'r0_stop'): (
        '门', '不旁路', 'R10-3(结构位,与 crisis_refresh_invariant 同族)'),
    ('refresh', 'r1_start'): (
        '发射位', '旁路', 'R2-2 原判(零调用面墓碑:刷新.r1_start 函数'
        '自 ADR-0516 起无生产调用点,目录行保留旁路枚举完备性)'),
    ('refresh', 'r1_commitment_account'): (
        '发射位', '旁路', 'R2-2 原判同位(ADR-0516 新语义:形式二可负担性'
        '判据,全游戏定义量输入、无 provisional 槽位依赖;arm1 旁路集'
        '成员)'),
    ('refresh', 'r2_budget'): (
        '门', '旁路=门关闭', 'R5-4(预算门不批)'),
    ('refresh', 'r2_card_reserve'): (
        '状态函数', '不旁路', 'P54 §② ρ 公共单一源(ADR-0560 提升批;'
        'R2 门与 P71-b 闸同源消费)'),
    ('refresh', 'hard_node_reinforce_gate'): (
        '门', '旁路=门关闭', 'D-D(硬节点补强门,消费面 r1/candidates 均臂①旁路)'),
    ('refresh', 'crisis_refresh_invariant'): (
        '结构不变式', '不旁路', 'R1-11(executor 结构位;本域纯数供对拍)'),
    # —— criteria/stockpile(§2.5;档匹配谓词/V_comp 表在 statefn/vopt)——
    ('stockpile', 'stockpile_buy'): (
        '发射位', '旁路', 'R2-2 原判'),
    # —— criteria/equipment(§2.6;M7 基础穿戴在 mandate,D-B 释放门在此)——
    ('equipment', 'wear_release'): (
        '谓词', '不旁路', 'D-B 三态释放门(M7 消费的判据输入)'),
    ('equipment', 'affix_allocation'): (
        '谓词', '不旁路', 'D-F46 零调用面墓碑:词缀分配生产单一源 = '
        'cw_equip_env.resolve_affix_priority_order(cw_op_equip_all 消费);'
        '本函数系孤儿第二实现+死键,已随判据出处纠错批物理删除,'
        '目录行保留旁路枚举完备性'),
    ('equipment', 'keep_policy'): (
        '判据/闭式', '不旁路', '§2.6(排序/保守端)'),
    ('equipment', 'endgame_context'): (
        '谓词', '不旁路', 'D-P3(收尾段语境输入)'),
    # —— criteria/contracts(R198 判据契约层;基础设施非判据,恒开)——
    ('contracts', 'ensure_contract'): (
        '谓词', '不旁路', 'R198(IMPL_DESIGN §4.2.2 判据契约纪律;前提核验'
        '层非判据,两臂同开,违例=弃权+计数)'),
}
