"""货币战争 过渡引擎体系注册事实(自 kernel 死刑判据文件迁入的权威副本)。

迁入出处:`docs/develop/currency_war/archive/redesign/03_legacy_cleanup_plan.md` 批 0
第 1/5 项——telemetry/schema 与 kernel/cw_battle_calib 消费的**数据半部**
符号(TRANSITION_TRAITS 注册数据 + engines_count 机制事实判据)迁出
cw_deploy_logic(部署决策半部,处死计划批 3 处死)。

engines_count 是机制事实判据(transition_combos.md 2026-08-23 定稿口径:
四体系两两组合=过渡成型),输入 board 计数输出体系达成数,无 ctx/无拍值,
归知识层合法;cw_deploy_logic 内的决策半部(部署围栏)不随迁。

零漂移契约:与 kernel/cw_deploy_logic 同名符号派生式同源(同一
SYSTEM_CARDS/FACTIONS 注册表派生,不存在字面双源;本模块 = 知识层
权威副本,kernel 侧同名副本的迁移挂账见该文件注释,历史过渡叙述中
的 sim 旧引擎消费点已随 sim 重做删除面退役)。**新增消费一律
import 本模块。**

依赖方向:仅 import 数据注册表与 cw_system_cards(体系卡注册,保留件);
不 import 任何决策符号。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_system_cards import SYSTEM_CARDS

# 与 op 侧同源(RECIPE ∪ ENGINE 桥派生集;三羁绊(阵营, 阈值)对改从
# SYSTEM_CARDS 派生(排除 seele 卡——希儿系是 deployed 单卡判定非阵营
# 计数,deploy 排序/形态维无意义);tier 阈值经 FACTIONS 注册表,单一源)。
TRANSITION_TRAITS: tuple[tuple[str, int], ...] = tuple(
    (card.judge_factions[0], FACTIONS[card.judge_factions[0]].tiers[0])
    for card in SYSTEM_CARDS.values() if card.card_id != 'seele'
)


def engines_count(board_factions: dict[str, int],
                  deployed_names: frozenset[str] | set[str] = frozenset()
                  ) -> int:
    """过渡体系达成数(四体系:仙舟3/列车2/DOT2(TRANSITION_TRAITS
    阈值)+ 希儿系(希儿在场 ∧ 放大器≥2)。两两组合=过渡成型。

    希儿系 = 希儿在场 AND(量子同频≥2 OR 贝洛伯格≥2)——
    与三羁绊同级可组合(口径出处 = docs/game/currency_war/research/
    transition_combos.md 希儿系行)。
    """
    n = sum(1 for bond, tier in TRANSITION_TRAITS
            if board_factions.get(bond, 0) >= tier)
    seele = ('希儿' in deployed_names
             and (board_factions.get('量子同频', 0) >= 2
                  or board_factions.get('贝洛伯格', 0) >= 2))
    if seele:
        n += 1
    return n
