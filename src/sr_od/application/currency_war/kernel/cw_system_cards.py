"""货币战争 P1 体系卡+组合规则(契约包 C2;判断层手编)。

⚠️ **v4.7 换赛季退役声明**:本表 = V4.4 P1 教义四卡体系;v4.7「入画奇航」S2
换赛季后,仙舟/列车同行/量子同频/贝洛伯格羁绊消失、引擎单卡希儿掉出角色
注册表——xianzhou3/train2/seele 三卡判据机制已不存在,随本批退役
(考古走 git 历史);dot2 判据羁绊「持续伤害」为沿用档卡,判据迁移至新
数据层 ``cw_traits_data.trait_by_name``。v4.7 新体系卡(策略行为重建)
归策略暂缓批恢复后的策略迭代,本模块禁凭空登记新卡。

**单一源**:
- tier 阈值单一源 = ``cw_traits_data.trait_by_name``(持续伤害取
  ``tiers[0]``,不在本文件重复硬编码)。
  (V4.4 铁三角名单 = ``knowledge.cw_line_facts._CORE_TRIO`` 注册表真值;
  消费面随仙舟卡退役断开,权威副本仍在彼处。)

**契约偏差声明(相对 C2 伪码;保留面)**:
1. C2 伪码签名 ``card_active(card, board_by_row: BoardByRow)`` —— ``_faction_count``
   身份口径改读
   ``cw_board_by_row.board_by_row_of(gs)`` 全板合计视图(全仓按排聚合单一源;
   C6 契约,P4 起状态容器行域直读);判据语义零变化(仍取 max(board OCR,身份计数));
2. C2 伪码返回 ``EngineState`` —— 本模块按规格返回 ``bool``(缺件审计走
   ``engine_missing``;EngineState 包装留给 decision_v2 接入调用面)。

(组合决策层——CardState/CombinationDecision/BlankWindowDecision 三元
数据类与 pick_card_combination/blank_window_policy/_INTENT_CARD_MAP/权重
常量——已随配方决策层退役删除:组合选卡
与空窗买门的消费面由过渡候选机器与商店冷启动臂承接,考古走 git 历史。)

消费方(数据层保留面):体系判定(board_rung 口径)/引擎完备度
(cw_engine_facts/ab_judge 判据工具链)。

词条吃怕表(数据字段 ``affix_likes``/``affix_fears``):词缀名与
``affix_effects_data``/竞品 data 对齐(DOT 吃敌方频动=忍无可忍/同步行动/应激反应,
怕净化身心;消费面 = 过渡候选机器的词缀软排除判据
(cw_intention.TRANSIT_AFFIX_PENALTY 的数据参照)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.data.cw_chars import get_char
from sr_od.application.currency_war.data.cw_traits_data import trait_by_name
from sr_od.application.currency_war.kernel.cw_board_by_row import board_by_row_of
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_units_of,
    deployed_rows_of,
)

# (铁三角名单 _CORE_TRIO 的消费面 = V4.4 仙舟卡引擎件,随卡退役断开;
#  权威副本仍在 knowledge/cw_line_facts,考古走 git 历史。)

# ===== 判据常量(tier 阈值派生自新数据层,单一源)=====
# (_XIANZHOU_TIER/_TRAIN_TIER 随仙舟/列车同行羁绊消失退役删除;
#  _DOT_TIER = 沿用档「持续伤害」首档,唯一存活阈值。)
_DOT_TIER: int = trait_by_name['持续伤害'].tiers[0]          # v4.7 = 3

# (_SEELE 随希儿掉出角色注册表退役删除——seele 卡已退役,常量无消费。)

@dataclass(frozen=True)
class SystemCard:
    """一张 P1 体系卡(乐高块;p1_definition 一·体系卡)。

    - ``card_id``:现役仅 'dot2'(v4.7 前含 'xianzhou3'/'train2'/'seele');
    - ``judge``:判据描述(文档性;**函数 ``card_active`` 才是权威**);
    - ``engine_required``:引擎件(V4.4 语义 = 仙舟=铁三角三人;现役卡空);
    - ``star_goal``:星级目标(V4.4 语义 = 仙舟铁三角 2★/希儿 3★;现役卡不追);
    - ``judge_factions``:判据羁绊元组——**卡→羁绊映射的单一数据源**
      (字段化防多处手抄漂移,加卡零改动);
    - ``affix_likes``/``affix_fears``:词条吃怕表(数据字段;消费面 =
      过渡候选机器词缀软排除判据的表参照)。
    """
    card_id: str
    display_name: str
    judge: str
    engine_required: list[str]
    star_goal: dict[str, int]
    judge_factions: tuple[str, ...] = ()
    affix_likes: list[str] = field(default_factory=list)
    affix_fears: list[str] = field(default_factory=list)


# (xianzhou3/train2/seele 三卡随 v4.7 换赛季退役:仙舟/列车同行羁绊消失、
#  希儿系连引擎单卡都已掉出角色注册表——三卡判据机制不存在,考古走 git 历史。)
SYSTEM_CARDS: dict[str, SystemCard] = {
    'dot2': SystemCard(
        card_id='dot2', display_name='DOT2',
        judge='持续伤害≥首档(3 人档激活,v4.7);无引擎要求',
        engine_required=[],
        star_goal={},                            # 星级不追
        judge_factions=('持续伤害',),
        affix_likes=['忍无可忍', '同步行动', '应激反应'],   # 吃敌方频动→DOT 多结算
        affix_fears=['净化身心'],                # 敌解负面+回血(羁绊注册表注记:该环境别玩 DOT)
    ),
}


# (组合决策层三元数据类 CardState/CombinationDecision/BlankWindowDecision
#  已随配方决策层退役删除——组合选卡/空窗
#  买门消费面已由过渡候选机器与商店冷启动臂承接,考古走 git 历史。)

# ===== 体系判定(冻结的判据语义;p1_definition 一)=====

def _char_traits(ch) -> tuple[str, ...]:
    """角色的全部羁绊 tag(阵营 factions + 流派 schools)。

    持续伤害等是**流派**羁绊(cw_chars.Character.schools),阵营类羁绊在
    factions——判据消费「该角色算不算某羁绊的件」必须双看(单看 factions
    会漏流派件)。
    """
    return (ch.factions or ()) + (ch.schools or ())


def _owned_units(gs: GameState) -> list:
    """在场∪bench 的单位域现读(状态容器原生:行域 ``Unit`` + 备战席 unit 槽
    ``Unit``;占位件/空槽不计——身份域读口,槽位 kind 面不进本口)。"""
    front, back = deployed_rows_of(gs)
    return [*front, *back, *bench_units_of(gs)]


# (_owned_names/_seele_on_board 两 helper 的消费面 = V4.4 seele 卡分支,
#  随卡退役删除;考古走 git 历史。)


def _faction_count(gs: GameState, faction: str) -> int:
    """板上某羁绊的计数(身份口径优先,board OCR 兜底,取 max)。

    deployed 与 board 应一致(cw_state 头注);单侧 miss(OCR 漏/重建缺身份)时
    取 max 容错——**判激活侧非计费侧**,漏判激活比多判更伤(体系卡是 P1 战力主体)。
    身份口径 = C6 ``board_by_row_of`` 全板合计视图(全仓按排聚合单一源;
    口径:get_char(char_id) 羁绊全集,多羁绊角色每系都计;§2.1 faction
    类2 注册表派生,未知名不计)。"""
    cnt_board = (gs.board.value or {}).get(faction, 0)
    cnt_ident = board_by_row_of(gs).count(faction)
    return max(cnt_board, cnt_ident)


def card_active(card: SystemCard, gs: GameState) -> bool:
    """体系判定(V4.4 冻结判据语义;v4.7 现役面 = DOT 卡单卡):

    - DOT2 = 持续伤害 ≥ 首档(v4.7 = 3)。
    (仙舟3/列车2/希儿系三卡已随 v4.7 换赛季退役,card_id 不再注册。)
    """
    if card.card_id == 'dot2':
        return _faction_count(gs, '持续伤害') >= _DOT_TIER
    raise ValueError(f'未知体系卡: {card.card_id}')


def card_engine_complete(card: SystemCard, owned: set[str]) -> bool:
    """引擎完备度(V4.4 冻结语义:V4.4 仙舟卡=铁三角三人组到齐;无引擎卡恒 True)。

    ``owned`` = 拥有角色名集合(在场∪bench 口径,由调用方给;判据只看「有没有」,
    bench 里的引擎件算到齐——上场时机归演进引擎/围栏,不归本判定)。
    """
    if not card.engine_required:
        return True
    return all(n in owned for n in card.engine_required)


# ===== 件数/组合选择(组合规则 1-3;权重草案级)=====

def _card_factions(card: SystemCard) -> tuple[str, ...]:
    """该体系卡的判据羁绊(单元组;V4.4 希儿系双分支随卡退役)。

    映射本体已字段化为 ``SystemCard.judge_factions``
    (本函数保留为兼容视图,行为=原样返回字段)。
    """
    return card.judge_factions


def card_pieces(card: SystemCard, gs: GameState) -> int:
    """该体系当前件数(来牌主判据):在场+bench 的该系件数(含引擎件)。

    按羁绊成员身份计(deployed∪bench;V4.4 希儿系「引擎+放大器去重计件」
    特殊分支随 seele 卡退役)。
    """
    fac = _card_factions(card)[0]
    n = 0
    for c in _owned_units(gs):
        if not getattr(c, 'char_id', ''):
            continue
        ch = get_char(c.char_id)
        if ch is not None and fac in _char_traits(ch):
            n += 1
    return n


# (card_state_of/_affix_weight/pick_card_combination/blank_window_policy
#  四函数已随配方决策层退役删除,考古走 git 历史;件数/激活/引擎完备度
#  数据层判据(card_pieces/card_active/card_engine_complete)保留——结算键
#  rung 与 A/B 判据工具链〔cw_engine_facts/ab_judge〕的消费面。)
