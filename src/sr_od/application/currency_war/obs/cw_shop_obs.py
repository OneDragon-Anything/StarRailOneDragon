"""货币战争 商店开态对账纯函数(W556):卡池一致性 / 合成预览交叉验证 / 刷新期望。

形态同 ``cw_faction_obs`` 的「识别器+对账纯函数」分层:判定与落账分离,
接线点在 ``prep_director``(卡池票/合成预览)与 ``shop.py`` 刷新波
(刷新期望 producer),均已接线;各函数 docstring 登记消费点与口径。

三个对账点:
1. :func:`check_shop_pool` —— 商店五牌两查:①费用档 ≤ 当前等级解锁档
   (``cw_shop_odds.REFRESH_PROB`` 非零概率的档);②池副本守恒(同牌
   可见张数 + 我方持有 ≤ ``POOL_COPIES_PER_CARD``,需 pool_state 可得)。
   违反 = 识别错或数据缺口,返回违例清单**不判哪边错**(记账留证)。
2. :func:`compare_merge_preview` —— 合成预览交叉验证(merge_mechanics.md
   §2.7:合成预览 = 我方可算,游戏 UI 只作对账信号)。**单向验证**:
   我方算 True 而游戏识别无星 = 我方合成计算嫌疑。识别端
   ``cw_identity_obs.read_merge_preview`` 已在产线运行(商店快照
   merge_preview 字段),消费点 = ``prep_director`` 商店对账段
   (``_reconcile_merge_preview``);``preview_detected=None`` 仍合法
   (登记/测试形态,全行 pending)。
3. :func:`refresh_expect` —— 刷新动作的期望增量(金 −refresh_cost、
   旧五张回池、新五张重抽),供刷新后对账。

机制依据:
- 概率表/池副本单一源 = ``cw_shop_odds``(REFRESH_PROB / POOL_COPIES_PER_CARD);
- 合成语义 = ``docs/game/currency_war/research/merge_mechanics.md`` §2.7;
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
# 2. 合成预览交叉验证(单向)
# ---------------------------------------------------------------------------

#: 商店牌位坐标系:dict 键 = 商店五格物理槽位 idx,0 基(左→右 0..4;
#: 同 ``read_shop_cards`` 返回列表下标),生成期快照(商店开帧内恒稳)。


@dataclass
class MergePreviewCompareRow:
    """单牌位的合成预览对账行。"""
    slot: int  # 商店五格槽位 idx,0 基(左→右 0..4)
    our: bool  # 我方合成计算(主源,同 cw_faction_obs 的「计算侧主源」口径)
    detected: bool | None  # 游戏识别;None = 识别端未建(恒 None 形态)
    verdict: str  # 'match' | 'our_suspect' | 'game_extra' | 'pending'


@dataclass
class MergePreviewCompareResult:
    """合成预览交叉验证结果(纯数据,无行为)。"""
    rows: list[MergePreviewCompareRow] = field(default_factory=list)

    @property
    def suspect_slots(self) -> list[int]:
        """我方算 True 而游戏无星的牌位(我方合成计算嫌疑,单向罚则唯一对象)。"""
        return [r.slot for r in self.rows if r.verdict == 'our_suspect']


def compare_merge_preview(our_merge_flags: dict[int, bool],
                          preview_detected: dict[int, bool] | None) -> MergePreviewCompareResult:
    """合成预览交叉验证(merge_mechanics.md §2.7「对账信号候选」落地)。

    **已接线**(激活依据 = W600 批B 数据充分性评估,
    ``.debug/temp/currency_war/w600_batch_b_assessment/REPORT.md``:reader
    ``cw_identity_obs.read_merge_preview`` 产线 136 组同刻重复读数 0 分歧、
    15 非零事件 8 例与持有台账精确相符,原「多帧闪烁采样」合格线作废)。
    消费点 = ``prep_director._reconcile_merge_preview``(商店打开 heavy 帧):
    our_merge_flags 由 tracked 持有按 ``cw_state.same_star_count`` 折算
    (>0 = True),preview_detected 由商店快照逐牌 ``merge_preview > 0``
    映射;mismatch 落缺陷台账 kind=merge_preview_mismatch(零决策)。

    **单向验证**(用户裁决):合成以我方计算为主源,游戏金色星标 UI 只作
    票——我方 True 而识别 False = 我方合成计算嫌疑(our_suspect);
    识别 True 而我方 False = 我方漏算,单向框架内不判罚,仅 game_extra
    计数留证(同 cw_faction_obs computed_missing 的第四态口径)。
    preview_detected=None 仍合法(登记/测试形态)= 全行 pending,
    函数照常返回完整行集。

    槽位键集 = both 侧键的并集;两侧同键布尔相等 = match。
    已知边界:✦ 为闪烁动画,识别暗相可能单帧漏检(merge_preview 读 0 是
    「无副本 ∨ 读不到」双义)→ our_suspect 票按对账率归因,系统性
    「持有 ≥1 副本但同刻重复读数恒 0」才是暗相漏检证据(届时回退采帧,
    见 W600 报告解锁条件)。
    """
    slots = sorted(set(our_merge_flags) | set(preview_detected or {}))
    res = MergePreviewCompareResult()
    for s in slots:
        our = bool(our_merge_flags.get(s, False))
        det: bool | None = None if preview_detected is None \
            else bool(preview_detected.get(s, False))
        if det is None:
            verdict = 'pending'
        elif our and not det:
            verdict = 'our_suspect'
        elif det and not our:
            verdict = 'game_extra'
        else:
            verdict = 'match'
        res.rows.append(MergePreviewCompareRow(s, our, det, verdict))
    return res


# ---------------------------------------------------------------------------
# 3. 刷新期望
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
