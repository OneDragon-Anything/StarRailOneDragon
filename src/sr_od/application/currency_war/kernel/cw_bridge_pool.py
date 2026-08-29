"""货币战争 · 桥线池——纯数据表(消费 = cw_intention / cw_line_defs)。

**手维护调研数据**(数据候选来自战力表 P1/P2 榜+transition_combos
调研的 fixed/core 三档;本文件把调研结论结构化)。
选桥函数簇(score_bridge/pick_bridge,r207 重合度评分 + r253 平局
偏好)已退役——其决策路径由 cw_intention/line_defs 的 form_tiers
机制取代(ADR-0336 删旧 line_strategy 后无生产消费,仅测试消费)。

设计要点(redesign §4.2):
  - 桥线=线库的短线子集(无终局形态,只有位面内配方);
  - r203 融合:[20] 过渡是配方不是散买 / r139c 三档角色构成。

字段语义:
  fixed: 缺=不选此桥(判据级,r139c)
  core:  重合度计分的主力件
  flex:  凑数位(双羁绊挂件)
  engine_bonds: 该桥凑的羁绊(战力表键的组成部分)
  budget: 预期成型金币(全员 1-2 费)
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BridgeCombo:
    """一条桥线(位面内配方;r149 引擎乐高 + r139c 三档)。"""
    bridge_id: str
    engine_bonds: dict[str, int]          # 要凑的羁绊档
    fixed: list[str]                      # 100% 件(缺=不选)
    core: list[str]                       # 准固定(重合度计分)
    flex: list[str] = field(default_factory=list)   # 凑数
    budget: int = 6                       # 预期成型金
    phase: str = 'P1'                     # 主力位面


#: 桥线池(按 r191 P1 榜验证强度排序;数据底:81/41/31 篇)
#: r353(局38-42 四局同型失败判读,V4.0 口径对齐):原三桥全
#: V3.7「仙舟+DOT」系——V4.0+ A830+ 不提升羁绊基础伤害 →
#: 怪血翻倍而 DOT 不涨,3 仙舟+2DOT 过渡**不稳**;V4.0 攻略
#: 过渡框架(sources/V4.0-4.4_公共_难度攻略.md §中期过渡):
#: 1-3/1-4 开 2DOT+2列车 或 **2DOT+2贝洛伯格**;1-6 前开
#: 3仙舟+2DOT/4列车。新增 dot_belog 早期桥(1-3 窗口的
#: 第二选项);狼狩系另入引擎阵营(见 ADR-0336 前 line_strategy r353)。
BRIDGE_POOL: list[BridgeCombo] = [
    BridgeCombo(
        bridge_id='xianzhou_dot',
        engine_bonds={'仙舟': 3, '持续伤害': 2},
        fixed=['爻光'],
        core=['藿藿', '丹恒·饮月', '艾丝妲', '椒丘'],
        flex=['卡芙卡', '忘归人'],
        budget=6,
        phase='P1',
    ),
    BridgeCombo(
        bridge_id='xianzhou_train',
        engine_bonds={'仙舟': 3, '列车同行': 2},
        fixed=['藿藿', '爻光'],
        core=['丹恒·饮月', '三月七'],
        flex=['丹恒·腾荒', '星期日'],
        budget=7,
        phase='P1',
    ),
    BridgeCombo(
        bridge_id='train_dot',
        engine_bonds={'列车同行': 2, '持续伤害': 2},
        fixed=['丹恒·饮月'],
        core=['三月七', '椒丘', '艾丝妲'],
        flex=['卡芙卡', '赛飞儿'],
        budget=5,
        phase='P1',
    ),
    # W126/ADR-0350:dot_belog(2DOT+2贝)与 hunt3(3狼狩+2DOT)两桥已删
    # ——狼狩/贝洛伯格体系随 2026-08-24 四体系封闭裁定封存(W124-H2 债:
    # 桥池/评分层仍奖励已封存线),git 可查;贝洛伯格只在希儿系判据内
    # 保留计数(cw_evaluate._seele_system_activated),不作独立伤害源。
]

#: P2 桥(列车4+护盾3=40 篇验证的 P2→P3 平滑桥;r191 P2 榜)
BRIDGE_POOL_P2: list[BridgeCombo] = [
    BridgeCombo(
        bridge_id='train4_shield3',
        engine_bonds={'列车同行': 4, '护盾': 3},
        fixed=['姬子·启行', '三月七'],
        core=['丹恒·腾荒', '砂金', '杰帕德'],
        flex=['星期日', '符玄'],
        budget=20,
        phase='P2',
    ),
]


#: 桥线池定位说明(S5 修正):本表为**调研期手选**(r139c 逐篇
#: 提取的 fixed/core 三档;版本更新靠人重跑调研),不是运行时
#: 从战力表自动派生——redesign §4.2 的「数据派生」指 P1/P2 榜
#: 数据决定**哪些组合够格入池**(81/41/31 篇的门槛),入池后
#: 的角色构成是调研产物。

#: 构造期一致性断言:combo.phase 必须与所在池一致(S3)
for _pool, _ph in ((BRIDGE_POOL, 'P1'), (BRIDGE_POOL_P2, 'P2')):
    for _c in _pool:
        assert _c.phase == _ph, f'{_c.bridge_id} phase 与所在池不符'
