"""cw4 EV 判据层(criteria 七面);判据族规格=01_math_framework §3。

包树:buy/sell/levelup/refresh/stockpile 五模块(第七面
「换线」在 proof,line_selector,12_line_and_intention §1-§3)。判据族
数学口径=01_math_framework §3.1-§3.5(本包实现消费 statefn 单一源,
禁自算状态量)。

**分支①旁路集函数级枚举表**(本模块 ``BYPASS_TABLE``=单一源;
R5-4 类别分列 + R7-1 第四类「动作发出面」;表内类别字面量沿用
'动作发出点'/'发射面' 写法)
= 旁路枚举交叉核对测试的单一源。类别语义 =
动作发出点('动作发出点')/ 门 / 谓词 / 状态函数 / 动作发出面('发射面',复合)/ 支付支撑通道;
``arm1`` 列 = 分支①形态(不旁路 / 旁路 / 旁路=门关闭 / 不旁路(两分支同开))。

修复池落点(R189-5 表):D-D(refresh+buy)、
D-F1(选卡 eval,pick 接口覆盖外——本包登记接口占位)、D-FM1(全局
candidates+economy sink)、D-P3(待办登记载体 = 表尾 endgame_context 行)、
D-BUYNOTE(buy 内嵌 P48 整买纪律)。
"""
from __future__ import annotations

# (模块,函数) → (类别,分支①形态,依据标签)
# 类别与分支①形态的合法配对以本表逐行为单一源;谓词/状态函数恒「不旁路」。
BYPASS_TABLE: dict[tuple[str, str], tuple[str, str, str]] = {
    # —— criteria/buy(01_math_framework §3.1;支配族 dominance_buy 已移 mandate 邻位,本域无)——
    ('buy', 'ev_buy_candidates'): (
        '发射面', '旁路', 'R2-2+R7-1(候选生成+否决门一体,整体不发射)'),
    ('buy', 'ev_buy_veto'): (
        '发射面', '旁路', '随 ev_buy_candidates 整体旁路(拆开=fail-open)'),
    # —— criteria/sell(01_math_framework §3.2;fuel_sell/protected_sell 在 mandate/predicates;
    #    line_switch_sell 换线清仓出口已删除,勿再登记)——
    ('sell', 'sell_for_interest'): (
        '发射位', '旁路', 'R5-4 补漏(凑息档 EV 追加发射)'),
    ('sell', 'funding_support_sell'): (
        '支付支撑通道', '不旁路(两臂同开)',
        'R13-5/R14-4(mandate=false+funding_support=true,臂间对称)'),
    # —— criteria/levelup(11 号稿 §2;触发单判据三分派)——
    ('levelup', 'upgrade_trigger'): (
        '判据/闭式', '不旁路',
        '升级触发单判据三分派(11 号稿 §2:带下界>等级升级 stay_gate/'
        '带内或推过停留无键/无目标自然升级 natural;消费位 = 备战第 4 步'
        '升级检查与商店会话升级意图出口两屏同参)'),
    ('levelup', 'prob_band_of_cost'): (
        '状态函数', '不旁路',
        '最优概率带查表(REFRESH_PROB 1..9 域内峰值区间,平顶整段;'
        'peak_refresh_level 域上限校验非带定义本体)'),
    ('levelup', 'spend_unified'): (
        '判据/闭式', '不旁路', '02_mandate_layer §3(义务侧消费)'),
    ('levelup', 'lv9_stop'): (
        '判据/闭式', '不旁路', 'M3 义务侧消费'),
    ('levelup', 'xp_ledger_stop'): (
        '判据/闭式', '不旁路', 'T-228(XP 期望账本停,lv9_stop 轮内盲区'
        '补位;shop M3 批/L3 两发射位与 lv9_stop 合取消费)'),
    ('levelup', 'fund_line_gate'): (
        '门', '不旁路', '升级资金线门(11 号稿 §2:现金口径单门,'
        '花后金 ≥ saturation_line;出辖 = 终局域 ALL IN/买断制)'),
    # —— criteria/refresh(01_math_framework §3.4)——
    ('refresh', 'r2_budget'): (
        '门', '旁路=门关闭', 'R5-4(预算门不批)'),
    ('refresh', 'r2_card_reserve'): (
        '状态函数', '不旁路', 'R2 预留 ρ 单一源(停留目标实费档;'
        '锁定支恒有值,未锁窗口恒 0)'),
    ('refresh', 'hard_node_reinforce_gate'): (
        '门', '旁路=门关闭', 'D-D(硬节点补强门,消费面 r1/candidates 均臂①旁路)'),
    # —— criteria/stockpile(01_math_framework §3.5;档匹配谓词/V_comp 表在 statefn/vopt)——
    ('stockpile', 'stockpile_buy'): (
        '发射位', '旁路', 'R2-2 原判'),
    # —— criteria/equipment(D-P3 待办登记载体,勿删;01_math_framework §3.6)——
    # 修复池项 OPEN 维持待办登记(定案手段 = 实机 boss 掉血分布交叉核对,
    # 从未执行),复活须先「交叉核对定案→三形态标注→实现」全流程。
    ('equipment', 'endgame_context'): (
        '谓词', '不旁路', 'D-P3 修复池项 OPEN 挂账不变(定谳手段 = '
        '实机 boss 掉血分布对拍,从未执行),复活须先「对拍定谳→三形态'
        '标注→落码」全流程'),
    # —— criteria/contracts(R198 判据契约层;基础设施非判据,恒开)——
    ('contracts', 'ensure_contract'): (
        '谓词', '不旁路', 'R198(判据契约纪律,单一源=criteria/contracts.py;'
        '前提核验'
        '层非判据,两臂同开,违例=弃权+计数)'),
}
