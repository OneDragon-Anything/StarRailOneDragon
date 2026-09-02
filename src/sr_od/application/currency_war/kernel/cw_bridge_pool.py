"""货币战争 · 桥线池——纯数据表(消费 = cw_intention / cw_line_defs)。

**手维护调研数据**(数据候选来自战力表 P1/P2 榜+transition_combos
调研的 fixed/core 三档;本文件把调研结论结构化)。
本文件仅存数据表;score_bridge/pick_bridge 等选桥函数簇已随旧
line_strategy 退役(ADR-0336),决策路径由 cw_intention/line_defs 的
form_tiers 机制承载。

设计要点(redesign §4.2):
  - 桥线=线库的短线子集(无终局形态,只有位面内配方);
  - 设计融合:[20] 过渡是配方不是散买 / 三档角色构成。

字段语义:
  fixed: 缺=不选此桥(判据级)
  core:  重合度计分的主力件
  flex:  凑数位(双羁绊挂件)
  engine_bonds: 该桥凑的羁绊(战力表键的组成部分)
  budget: 预期成型金币(全员 1-2 费)
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BridgeCombo:
    """一条桥线(位面内配方;引擎乐高式拆分 + 三档角色构成)。"""
    bridge_id: str
    engine_bonds: dict[str, int]          # 要凑的羁绊档
    fixed: list[str]                      # 100% 件(缺=不选)
    core: list[str]                       # 准固定(重合度计分)
    flex: list[str] = field(default_factory=list)   # 凑数
    budget: int = 6                       # 预期成型金
    phase: str = 'P1'                     # 主力位面


#: 桥线池;池内容=调研数据,顺序无行为面(消费面按键集精确匹配,
#: 300 局 A/B 逐位零差,heuristic_ab B1;REPORT = .debug/temp/currency_war/
#: redesign/heuristic_ab/REPORT.md)。数据底:81/41/31 篇
#: 版本口径(V4.0+ 对齐):V3.7「仙舟+DOT」系桥在 V4.0+ A830+ 下
#: 不提升羁绊基础伤害 → 怪血翻倍而 DOT 不涨,3 仙舟+2DOT 过渡**不稳**;
#: V4.0 攻略过渡框架(sources/V4.0-4.4_公共_难度攻略.md §中期过渡):
#: 1-3/1-4 开 2DOT+2列车 或 **2DOT+2贝洛伯格**;1-6 前开
#: 3仙舟+2DOT/4列车。
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
    # ADR-0350:狼狩/贝洛伯格体系已封存(四体系封闭裁定),不入桥池;
    # 贝洛伯格只在希儿系判据内保留计数(希儿系判定
    # `_seele_system_activated` 口径),不作独立伤害源。
]

#: P2 桥(列车4+护盾3=40 篇验证的 P2→P3 平滑桥;攻略 P2 榜)
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


#: 桥线池定位说明(S5 修正):本表为**调研期手选**(逐篇
#: 提取的 fixed/core 三档;版本更新靠人重跑调研),不是运行时
#: 从战力表自动派生——redesign §4.2 的「数据派生」指 P1/P2 榜
#: 数据决定**哪些组合够格入池**(81/41/31 篇的门槛),入池后
#: 的角色构成是调研产物。

#: 构造期一致性断言:combo.phase 必须与所在池一致(S3)
for _pool, _ph in ((BRIDGE_POOL, 'P1'), (BRIDGE_POOL_P2, 'P2')):
    for _c in _pool:
        assert _c.phase == _ph, f'{_c.bridge_id} phase 与所在池不符'
