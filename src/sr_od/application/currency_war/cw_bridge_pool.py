"""货币战争 · 桥线池(Phase A Day 4;redesign §4.2 r207 版)。

**判断层,手维护**(数据候选来自战力表 P1/P2 榜+transition_combos
调研的 fixed/core 三档;本文件把调研结论结构化)。

设计要点(redesign §4.2):
  - 桥线=线库的短线子集(无终局形态,只有位面内配方);
  - 按手牌/商店组件重合度选桥(不是泛买保值件);
  - 桥线桶由战力表数据派生(版本自适应);
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
#: 版本漂移防护(⑧-5 修正):**尚未接线**——line_strategy 当前
#: 不对 bridge 调 check;接线排在 Phase B(桥成立性验证);
#: 在此之前本注释如实声明「无运行时守卫」。

#: 构造期一致性断言:combo.phase 必须与所在池一致(S3)
for _pool, _ph in ((BRIDGE_POOL, 'P1'), (BRIDGE_POOL_P2, 'P2')):
    for _c in _pool:
        assert _c.phase == _ph, f'{_c.bridge_id} phase 与所在池不符'


def _char_bond_hits(name: str, bonds: dict[str, int]) -> int:
    """角色对目标羁绊的贡献数(纯查询,不含持有判定——调用方管)。

    ⚠️ 开拓者两形态按当前排归一(cw_chars 约定);owned 是名字
    集合的接口下无法表达形态,含开拓者时此函数按注册表默认
    形态计(消费方如需精确,传归一后的羁绊计数进来)。
    """
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    ch = CHARACTERS.get(name)
    if ch is None:
        return 0
    hits = 0
    all_bonds = list(ch.factions) + list(ch.flows)
    if ch.independent:
        all_bonds.append(ch.independent)
    for b in bonds:
        if b in all_bonds:
            hits += 1
    return hits


def score_bridge(combo: BridgeCombo, owned: set[str]) -> float:
    """桥线与当前手牌的重合度评分(r207:选重合度最高)。

    计分口径(双重加分是有意的:配方件+凑羁绊各记一次——
    同一角色最多 +4;调权重时注意此口径):
      fixed 缺一=0(判据级);core 每命中 +2;flex 命中 +1;
      羁绊贡献每点 +1(按羁绊名命中数,不按档人数——
      档人数维度由引擎凑档进度另行判断,见 pick_bridge)。
    """
    for fx in combo.fixed:
        if fx not in owned:
            return 0.0
    s = 0.0
    s += 2.0 * sum(1 for c in combo.core if c in owned)
    s += 1.0 * sum(1 for c in combo.flex if c in owned)
    for name in owned:
        s += _char_bond_hits(name, combo.engine_bonds)
    return s


_POOL_BY_PHASE: dict[str, list[BridgeCombo]] = {
    'P1': BRIDGE_POOL,
    'P2': BRIDGE_POOL_P2,
}


def pick_bridge(owned: set[str],
                phase: str = 'P1') -> BridgeCombo | None:
    """按重合度选桥(未锁线时的购买方向;r207 混合边界表)。

    phase 仅接受 P1/P2(显式映射,拼写错误即 KeyError——
    防静默落到错池);池内 combo.phase 已在构造期与所在
    池一致性校验(见模块尾部断言)。
    r253(第八局复盘):P1 平局 tie-break 偏好 xianzhou_dot
    ——它同时供 P1 的 DOT 引擎与 P2 列车桥的仙舟件
    (藿藿/爻光/饮月都是 P2 方向的铺垫),P1→P2 平滑性
    最优;第八局实证:散 DOT 板 P1 零败但进 P2 拆向
    列车4+护盾3 转型成本高(四连败根因之一)。
    分差 >0.5 时正常选高分(偏好只在真平局生效)。"""
    pool = _POOL_BY_PHASE[phase]
    best, best_s = None, 0.0
    for c in pool:
        s = score_bridge(c, owned)
        if s > best_s:
            best, best_s = c, s
        elif (phase == 'P1' and best is not None
              and abs(s - best_s) <= 0.5
              and c.bridge_id == 'xianzhou_dot'):
            best = c   # r253 平局偏好(P1→P2 平滑)
    return best
