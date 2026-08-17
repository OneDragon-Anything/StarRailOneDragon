"""动作本体注册表 v0(redesign 26 号;ADR-0185):动作语义一等公民 + 完备性审计。

**诊断(26 号)**:cw_state 的 6 类 Action 是裸种子(只有名与参数,无语义元数据);
前置合法性散在 cw_plan 100+ 行分支;13/14/22 各自维护动作假设。「我们能做什么」
零声明零审计 —— 候选完备性从未成为可审计对象。

**v0 落地**(纯函数,离线;26 号主张 A + C 的最小闭环):
- ``ActionSemantics``:六元语义算子(前置/效应/成本/可逆性/随机性/观测验证)+ 23 式
  证据状态;首版登记 6 类既有 Action + 2 个**无主动作**(26 号预验:特选填格、池操纵
  ——guides 实证存在、代码零候选);
- ``legal_actions``:状态 → 合法动作投影(候选完备性的单源供给;06/plan 消费为切流批次);
- ``completeness_audit``:J1 完备性审计 —— 已知动作清单(玩法 doc/guides 实证)对照
  注册表覆盖度,未登记 = 决策栈结构性盲区(进 04 可观测性矩阵/27 能力矩阵)。

效应的条件分支(开拓者位置形态/银狼升费时相/面板锁定)登记为 effect_note 溯源,
数值化进 v1(消费端需要时展开)。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionSemantics:
    """一个动作的六元语义说明书(26 号主张 A)。"""

    name: str                     # 动作名(与 cw_state Action 类名对齐;无主的用语义名)
    precondition: str             # 前置条件(状态谓词,声明式)
    effect: str                   # 效应(直述;条件分支注 effect_note)
    cost: str                     # 资源成本(引 23 号注册表名,不内嵌数值)
    reversibility: str            # 'reversible' | 'compensable' | 'irreversible'(封闭词汇)
    randomness: str               # 'none' | 'shop_face' | 'upgrade_branch'
    observation_verify: str       # 动作后要读什么确证落地(13 号后置条件模板)
    evidence: str = 'bracketed'   # 23 式证据状态
    registered: bool = True       # False = 无主动作(不在任何决策候选集 —— 盲区实锤)
    effect_note: str = ''
    reversibility_note: str = ''  # 补偿机制细节(可逆性词的实证说明)


_ONTOLOGY: dict[str, ActionSemantics] = {a.name: a for a in [
    ActionSemantics(
        'BuyCard', 'gold ≥ card.cost 且 bench 未满', 'bench+1(同名 ≥3 自动升星)、金-cost',
        'card.cost(OCR live/费用带估)', 'compensable',
        'none', 'bench 计数与金 OCR 复读',
        reversibility_note='卖出回池+星级退款(cw_economy.sell_refund)'),
    ActionSemantics(
        'SellBench', 'bench[idx] 存在', 'bench-1、金+refund(星级×费用档)',
        '负成本(回金)', 'reversible',
        'none', '金 OCR 复读',
        reversibility_note='同费买回近似;升星消耗不可逆'),
    ActionSemantics(
        'LevelUp', 'level<10 且 gold ≥ 单击价', 'XP+XP_PER_BUY、金-单击价;攒够门槛自动升级',
        'XP_CLICK_COST(注册表 bracketed 4-8)', 'irreversible',
        'none', 'xp_progress/level OCR 复读',
        reversibility_note='经验不可退'),
    ActionSemantics(
        'DeployMove', 'bench[idx] 存在且目标排未满', 'board[faction]+1、deployed+1',
        '0(免费)', 'reversible',
        'none', '左面板阵营计数复读',
        effect_note='条件效应:开拓者=位置定形态(前排记忆/后排欢愉);银狼=上场才触发升费(bench 不触发)',
        reversibility_note='换位/撤下近似零成本'),
    ActionSemantics(
        'RefreshShop', 'gold ≥ SHOP_REFRESH_COST', 'shop 重采样 5 张',
        'SHOP_REFRESH_COST(注册表 verified est=2)', 'irreversible',
        'shop_face', '商店 OCR 复读',
        reversibility_note='刷面不可回'),
    ActionSemantics(
        'PickEvent', '事件屏(选项 ≥1)', '选项特定效应',
        '事件特定', 'irreversible',
        'none', '事件屏流转',
        reversibility_note='保守档:事件选择不可回,具体事件可覆写'),
    # —— 无主动作(26 号 J1 预验实锤:guides 实证存在、代码零候选)——
    ActionSemantics(
        'FillBladeSlots特选填格', '持有刃印装备且格未满', '小件填满 3 格 → 随机把一件进阶装备变特选',
        '小件占格(星徽/简易也算)', 'irreversible',
        'upgrade_branch', '装备区 OCR',
        evidence='unverified', registered=False,
        effect_note='26 号预验:代码 grep「特选」全库零命中;guides 实证策略(填格指定行星抓地/特选鞋)',
        reversibility_note='进阶方向随机锁定'),
    ActionSemantics(
        'PoolManipulation池操纵', 'gold ≥ 1 费牌价', '买同费非目标牌压池 → 原价卖回净 0',
        '净 0(买入即卖回)', 'reversible',
        'none', '金 OCR 复读(净 0 确证)',
        evidence='bracketed', registered=False,
        effect_note='26 号预验:cw_shop_odds.non_target_taken 数学存在零调用方;ADR-0121 已量化',
        reversibility_note='卖回回池'),
]}


def legal_actions(state) -> list[str]:
    """状态 → 合法动作名投影(候选完备性单源;v0 按前置谓词粗判,精细门切流批次接)。"""
    out = []
    bench_full = state.bench_is_full() if hasattr(state, 'bench_is_full') else False
    if not bench_full and state.gold >= 1:
        out.append('BuyCard')
    if getattr(state, 'bench', None):
        out.append('SellBench')
        out.append('DeployMove')
    if state.level < 10 and state.gold >= 4:
        out.append('LevelUp')
    if state.gold >= 2:
        out.append('RefreshShop')
    return out


def completeness_audit(known_actions: list[str] | None = None) -> dict:
    """J1 完备性审计:已知动作清单对照注册表 → 未登记/无主动作清单(盲区)。

    known_actions 缺省 = 26 号 J1 预列 7 缝候选(玩法 doc/guides 实证源)。"""
    if known_actions is None:
        known_actions = [
            'BuyCard', 'SellBench', 'LevelUp', 'DeployMove', 'RefreshShop', 'PickEvent',
            'FillBladeSlots特选填格',      # 26 号预验 a
            'PoolManipulation池操纵',      # 26 号预验 b
        ]
    unregistered = [k for k in known_actions if k not in _ONTOLOGY]
    unowned = [k for k, a in _ONTOLOGY.items() if not a.registered]
    return {
        'n_known': len(known_actions),
        'n_registered': len(_ONTOLOGY),
        'unregistered': unregistered,          # 完全盲区(注册表都没有)
        'unowned_registered': unowned,         # 已登记但不在任何决策候选集(结构性盲区)
        'verdict': 'gaps_found' if (unregistered or unowned) else 'complete',
    }
