"""货币战争 商店开态对账纯函数(W556):卡池一致性 / 刷新期望。

形态同 ``cw_faction_obs`` 的「识别器+对账纯函数」分层:判定与落账分离,
接线点在 ``cw_screen_prep``(卡池票)与 ``shop.py`` 刷新波
(刷新期望 producer),均已接线;各函数 docstring 登记消费点与口径。

两个对账点:
1. :func:`check_shop_pool` —— 商店五牌两查:①费用档 ≤ 当前等级解锁档
   (``cw_shop_odds.REFRESH_PROB`` 非零概率的档);②池副本守恒(同牌
   可见张数 + 我方持有 ≤ ``POOL_COPIES_PER_CARD``,需 pool_state 可得)。
   违反 = 识别错或数据缺口,返回违例清单**不判哪边错**(记账留证)。
2. :func:`refresh_expect` —— 刷新动作的期望增量(金 −refresh_cost、
   旧五张回池、新五张重抽),供刷新后对账。

机制依据:
- 概率表/池副本单一源 = ``cw_shop_odds``(REFRESH_PROB / POOL_COPIES_PER_CARD);
- 刷新语义(口述权威·倾向口径):刷新 = 旧五张全部回池,**新五格按当前
  等级 SHOP_ODDS 概率独立抽取(同名牌可能重复)**。早期「五张全异」
  假设作废(用户无法证明按概率说,但取其为倾向口径)——故本函数是
  *期望增量*而非逐张断言:**单次刷新的对账范围只硬验三面**——
  ①金 −刷新费;②五格有牌(格数 = SHOP_SLOTS);③池守恒统计面
  (旧五张回池账 pool_returned,新五张可见计数与之合并后对总账),
  不逐张断言全异。刷新费**不写死**:W554 实机发现费用疑似 f(当前金币)
  而非常数 2 → refresh_cost 必填,由调用方从面板现读传入。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.data.cw_shop_odds import (
    POOL_COPIES_PER_CARD,
    SHOP_SLOTS,
    refresh_prob,
)

# ---------------------------------------------------------------------------
# 1. 卡池一致性票
# ---------------------------------------------------------------------------


@dataclass
class ShopPoolViolation:
    """单张商店牌的一致性违例(不判哪边错,只留证)。

    ``kind`` 取值:
    - ``invalid_cost``:费用不在 1-5(OCR 误读/缺读),两查都无法做;
    - ``tier_locked``:该费用档在当前等级概率为 0(REFRESH_PROB 无非零项),
      商店不可能刷出 → 识别错或等级读错;
    - ``pool_overdraw``:同牌可见张数 + 我方持有 > 池副本上限 → 识别重复
      计数或持有账缺口(仅 pool_state 提供时检查)。
    """
    name: str
    cost: int
    kind: str
    detail: str  # 人读证据:如 'visible=2 held=26 cap=27' / 'p(level,cost)=0'


def check_shop_pool(cards: list[tuple[str, int]],
                    level: int,
                    pool_state: dict[str, int] | None = None) -> list[ShopPoolViolation]:
    """商店五牌卡池一致性票(纯函数;违例清单,空 = 全部通过)。

    :param cards: [(牌名, 费用)];同牌出现多次 = 可见张数(逐张各评)。
    :param level: 当前等级(1-10;越界按 refresh_prob 的 0 兜 = 全档锁,违例如实报)。
    :param pool_state: {牌名: 我方已持有基础副本数}(1星1/2星3/3星9/4星27,
      3合1 折算口径同 ``acquirability_factor`` 的 held)。None/缺名 = 该牌
      跳过池守恒查(现状:**cw_state 无池追踪账**——tracked bench/board
      只有我方持有,池内剩余无人建账,故池状态作入参由调用方折算持有
      传入,本函数不自行建账;NPC 消耗不可知,入参语义即「我方持有」,
      非「全池离池量」)。

    逐牌两查独立:invalid_cost 牌两查都免(费用不可信,查了也是噪声);
    tier_locked 牌仍做池查(两票独立留证,便于归因是哪一查先破)。
    票粒度:tier_locked 按牌位逐张开票(每格是独立证据);pool_overdraw
    按牌名**去重开一张**(池守恒是名字级账户,同牌多张只有一笔账)。
    """
    visible: dict[str, int] = {}
    for name, _c in cards:
        visible[name] = visible.get(name, 0) + 1

    violations: list[ShopPoolViolation] = []
    for name, cost in cards:
        if cost not in POOL_COPIES_PER_CARD:
            violations.append(ShopPoolViolation(
                name, cost, 'invalid_cost', f'cost={cost} 不在 1-5,两查免'))
            continue
        if refresh_prob(level, cost) <= 0.0:
            violations.append(ShopPoolViolation(
                name, cost, 'tier_locked',
                f'p(level={level}, cost={cost})=0,该等级刷不出此档'))
        if pool_state is None:
            continue
        held = pool_state.get(name, 0)
        cap = POOL_COPIES_PER_CARD[cost]
        if visible[name] + held > cap and not any(
                v.kind == 'pool_overdraw' and v.name == name for v in violations):
            violations.append(ShopPoolViolation(
                name, cost, 'pool_overdraw',
                f'visible={visible[name]} held={held} cap={cap}'))
    return violations


# ---------------------------------------------------------------------------
# 2. 刷新期望
# ---------------------------------------------------------------------------


@dataclass
class RefreshExpect:
    """一次刷新动作的期望增量(供刷新后对账;纯数据)。

    ``pool_returned``:旧五张回池账 {牌名: 回池张数}——刷新对账时,
    新五张里同名再现**不违规**(旧牌先回池),池守恒查应把回池量计回。
    ``insufficient``:金不足刷新费(gold < refresh_cost)——期望增量仍
    完整给出(金取算术差,可为负),是否执行由调用方判。
    """
    gold_before: int
    gold_after: int
    refresh_cost: int
    insufficient: bool
    #: 旧五张回池账 {牌名: 回池张数}(cards_old 原样折算,费用不入账:
    #: 池守恒上限按费用查,调用方对账时用新五张的 cost 查 POOL_COPIES_PER_CARD)
    pool_returned: dict[str, int] = field(default_factory=dict)
    #: 新五张格数(恒 = SHOP_SLOTS;昔涟诗篇改格数时改 cw_shop_odds 单一源)
    new_slots: int = SHOP_SLOTS


def refresh_expect(gold: int,
                   cards_old: list[tuple[str, int]],
                   refresh_cost: int) -> RefreshExpect:
    """刷新动作期望增量(纯函数;规则见模块头「刷新语义」)。

    语义:刷新 = 旧五张全部回池 + 新五格按当前等级概率独立抽取
    (同牌可重复,不逐张断言);金 −refresh_cost。refresh_cost **必填**
    ——W554 实机发现费用疑似 f(当前金币)而非常数,调用方须从商店面板
    现读传入,本函数不写死任何默认值。cards_old 空表合法(开局首刷前
    无旧牌,回池账为空)。
    """
    returned: dict[str, int] = {}
    for name, _c in cards_old:
        returned[name] = returned.get(name, 0) + 1
    return RefreshExpect(
        gold_before=gold,
        gold_after=gold - refresh_cost,
        refresh_cost=refresh_cost,
        insufficient=gold < refresh_cost,
        pool_returned=returned,
    )
