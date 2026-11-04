"""货币战争 P1 体系卡+组合规则(契约包 C2;判断层手编)。

**单一源**:
- 教义 = 「P1 体系卡定义」深度研读笔记(体系卡四张/
  组合规则/升级路径;判据语义逐字对齐);
- 契约 = 同目录 ``契约包_C1-C7.md`` C2 节(签名冻结级;判据内部权重草案级);
- tier 阈值单一源 = ``cw_factions.FACTIONS``(仙舟 3 档/持续伤害 2 档/列车同行 2 档/
  量子同频 2 档/贝洛伯格 2 档均取 ``tiers[0]``,不在本文件重复硬编码);
- 铁三角名单 = ``knowledge.cw_line_facts._CORE_TRIO`` 注册表真值(爻光+藿藿+丹恒·饮月,
  测试基准;本文件只 import 不复制)。

**契约偏差声明(相对 C2 伪码;保留面)**:
1. C2 伪码签名 ``card_active(card, board_by_row: BoardByRow)`` —— ``_faction_count``
   身份口径改读
   ``cw_board_by_row.board_by_row_of(gs)`` 全板合计视图(全仓按排聚合单一源;
   C6 契约,P4 起状态容器行域直读);判据语义零变化(仍取 max(board OCR,身份计数));
2. C2 伪码返回 ``EngineState`` —— 本模块按规格返回 ``bool``(缺件审计走
   ``engine_missing``;EngineState 包装留给 decision_v2 接入调用面)。

(组合决策层——CardState/CombinationDecision/BlankWindowDecision 三元
数据类与 pick_card_combination/blank_window_policy/_INTENT_CARD_MAP/权重
常量——已随 comp-structure-unification 3.3 配方决策层退役删除:组合选卡
与空窗买门的消费面由过渡候选机器与商店冷启动臂承接,考古走 git 历史。)

消费方(数据层保留面):体系判定(board_rung 口径)/引擎完备度
(cw_engine_facts/ab_judge 判据工具链)。

词条吃怕表(数据字段 ``affix_likes``/``affix_fears``):词缀名与
``affix_effects_data``/竞品 data 对齐(DOT 吃敌方频动=忍无可忍/同步行动/应激反应,
怕净化身心;希儿警惕量子熄火;仙舟/列车泛用);消费面 = 过渡候选
机器的词缀软排除判据(cw_intention.TRANSIT_AFFIX_PENALTY 的数据参照)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_board_by_row import board_by_row_of
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_units_of,
    deployed_rows_of,
)

# 符号解耦:铁三角权威副本在 knowledge/cw_line_facts,
# 不再依赖 kernel/cw_line_defs(迁移待办文件)
from sr_od.application.currency_war.knowledge.cw_line_facts import _CORE_TRIO

# ===== 判据常量(tier 阈值派生自 FACTIONS,单一源)=====
_XIANZHOU_TIER: int = FACTIONS['仙舟'].tiers[0]              # 3(仙舟≥3 激活)
_DOT_TIER: int = FACTIONS['持续伤害'].tiers[0]               # 2(持续伤害≥2)
_TRAIN_TIER: int = FACTIONS['列车同行'].tiers[0]             # 2(列车同行≥2)

_SEELE: str = '希儿'   # 卡4 引擎单卡(伤害全在她技能层,量子/贝是放大器)

@dataclass(frozen=True)
class SystemCard:
    """一张 P1 体系卡(乐高块;p1_definition 一·体系卡)。

    - ``card_id``:'xianzhou3' | 'dot2' | 'train2' | 'seele';
    - ``judge``:判据描述(文档性;**函数 ``card_active`` 才是权威**);
    - ``engine_required``:引擎件(仙舟=铁三角三人;其余空);
    - ``star_goal``:星级目标(仙舟铁三角 2★;希儿 3★;其余不追);
    - ``judge_factions``:判据阵营元组(希儿系双元组=('量子同频','贝洛伯格');
      其余单元组)——**卡→阵营映射的单一数据源**(字段化防多处手抄漂移,
      加卡零改动);
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


SYSTEM_CARDS: dict[str, SystemCard] = {
    'xianzhou3': SystemCard(
        card_id='xianzhou3', display_name='仙舟3',
        judge='仙舟≥3 人(3 人档激活);引擎=铁三角功能链不可拆(缺一=空壳)',
        engine_required=sorted(_CORE_TRIO),
        star_goal=dict.fromkeys(_CORE_TRIO, 2),   # 铁三角 2★ 即成型;不追 3★
        judge_factions=('仙舟',),
        affix_likes=[],                          # 词条泛用(神君不挑敌方形态)
        affix_fears=[],
    ),
    'dot2': SystemCard(
        card_id='dot2', display_name='DOT2',
        judge='持续伤害≥2 人(2 人档激活,最低门槛);无引擎要求',
        engine_required=[],
        star_goal={},                            # 星级不追
        judge_factions=('持续伤害',),
        affix_likes=['忍无可忍', '同步行动', '应激反应'],   # 吃敌方频动→DOT 多结算
        affix_fears=['净化身心'],                # 敌解负面+回血(羁绊注册表 note:该环境别玩 DOT)
    ),
    'train2': SystemCard(
        card_id='train2', display_name='列车2',
        judge='列车同行≥2 人;无引擎(凑出就能用)',
        engine_required=[],
        star_goal={},
        judge_factions=('列车同行',),
        affix_likes=[],                          # 词条泛用
        affix_fears=[],
    ),
    'seele': SystemCard(
        card_id='seele', display_name='希儿系',
        judge='希儿在场 AND(量子同频≥2 OR 贝洛伯格≥2);引擎=希儿单卡',
        engine_required=[_SEELE],
        star_goal={_SEELE: 3},                   # 希儿追 3★(高饥渴线,从 P1 就可开始)
        judge_factions=('量子同频', '贝洛伯格'),   # 双分支(顺序=演进目标基准取首位)
        affix_likes=[],
        affix_fears=['量子熄火'],                # 量子属性伤害限 1(重开级 counter)
    ),
}


# (组合决策层三元数据类 CardState/CombinationDecision/BlankWindowDecision
#  已随 comp-structure-unification 3.3 配方决策层退役删除——组合选卡/空窗
#  买门消费面已由过渡候选机器与商店冷启动臂承接,考古走 git 历史。)

# ===== 体系判定(冻结的判据语义;p1_definition 一)=====

def _char_traits(ch) -> tuple[str, ...]:
    """角色的全部羁绊 tag(阵营 factions + 流派 flows)。

    持续伤害/量子同频等是**流派**羁绊(cw_chars.Character.flows),仙舟/贝洛伯格
    等是阵营(factions)——判据消费「该角色算不算某羁绊的件」必须双看(单看
    factions 会漏 DOT/量子件)。
    """
    return (ch.factions or ()) + (ch.flows or ())


def _owned_units(gs: GameState) -> list:
    """在场∪bench 的单位域现读(状态容器原生:行域 ``Unit`` + 备战席 unit 槽
    ``Unit``;占位件/空槽不计——身份域读口,槽位 kind 面不进本口)。"""
    front, back = deployed_rows_of(gs)
    return [*front, *back, *bench_units_of(gs)]


def _owned_names(gs: GameState) -> set[str]:
    """在场∪bench 的角色名集合(char_id 已识别者;未识别槽不计)。"""
    return {u.char_id for u in _owned_units(gs)
            if getattr(u, 'char_id', '')}


def _faction_count(gs: GameState, faction: str) -> int:
    """板上某羁绊的计数(身份口径优先,board OCR 兜底,取 max)。

    deployed 与 board 应一致(cw_state 头注);单侧 miss(OCR 漏/重建缺身份)时
    取 max 容错——**判激活侧非计费侧**,漏判激活比多判更伤(体系卡是 P1 战力主体)。
    身份口径 = C6 ``board_by_row_of`` 全板合计视图(全仓按排聚合单一源;
    口径:CHARACTERS[char_id] 羁绊全集,多羁绊角色每系都计;§2.1 faction
    类2 注册表派生,未知名不计)。"""
    cnt_board = (gs.board.value or {}).get(faction, 0)
    cnt_ident = board_by_row_of(gs).count(faction)
    return max(cnt_board, cnt_ident)


def _seele_on_board(gs: GameState) -> bool:
    """希儿在场(= 上阵 deployed;bench 不算「在场」)。"""
    front, back = deployed_rows_of(gs)
    return any(u.char_id == _SEELE for u in (*front, *back))


def card_active(card: SystemCard, gs: GameState) -> bool:
    """体系判定(C2 冻结判据语义,逐字对 p1_definition):

    - 仙舟3 = 仙舟 ≥3;
    - DOT2 = 持续伤害 ≥2;
    - 列车2 = 列车同行 ≥2;
    - 希儿系 = 希儿在场 AND(量子同频 ≥2 OR 贝洛伯格 ≥2)。
    """
    if card.card_id == 'xianzhou3':
        return _faction_count(gs, '仙舟') >= _XIANZHOU_TIER
    if card.card_id == 'dot2':
        return _faction_count(gs, '持续伤害') >= _DOT_TIER
    if card.card_id == 'train2':
        return _faction_count(gs, '列车同行') >= _TRAIN_TIER
    if card.card_id == 'seele':
        if not _seele_on_board(gs):
            return False
        return any(_faction_count(gs, f) >= FACTIONS[f].tiers[0]
                   for f in card.judge_factions)
    raise ValueError(f'未知体系卡: {card.card_id}')


def card_engine_complete(card: SystemCard, owned: set[str]) -> bool:
    """引擎完备度(C2 冻结语义):仙舟=铁三角三人组到齐(缺一=空壳);无引擎卡恒 True。

    ``owned`` = 拥有角色名集合(在场∪bench 口径,由调用方给;判据只看「有没有」,
    bench 里的引擎件算到齐——上场时机归演进引擎/围栏,不归本判定)。
    """
    if not card.engine_required:
        return True
    return all(n in owned for n in card.engine_required)


# ===== 件数/组合选择(组合规则 1-3;权重草案级)=====

def _card_factions(card: SystemCard) -> tuple[str, ...]:
    """该体系卡的判据阵营(希儿系双分支;其余单阵营)。

    映射本体已字段化为 ``SystemCard.judge_factions``
    (本函数保留为兼容视图,行为=原样返回字段)。
    """
    return card.judge_factions


def card_pieces(card: SystemCard, gs: GameState) -> int:
    """该体系当前件数(来牌主判据):在场+bench 的该系件数(含引擎件)。

    - 阵营系(仙舟/DOT/列车):按阵营成员身份计(deployed∪bench);
    - 希儿系:希儿在手(在场∪bench)计 1 + 量子/贝成员件数(bench+deployed
      身份口径)——引擎+放大器合为「件数」近似。
    """
    if card.card_id == 'seele':
        owned = _owned_names(gs)
        if _SEELE not in owned:
            return 0   # 无希儿时量子/贝不能独立当过渡(放大器不算来牌方向)
        # 引擎(希儿)+ 放大器(量子/贝成员)按**角色去重**计件(多羁绊角色
        # 双分支只计一次;希儿本人既是引擎又属双分支,也只计一次)
        members: set[str] = set()
        for fac in _card_factions(card):
            for c in _owned_units(gs):
                if not getattr(c, 'char_id', ''):
                    continue
                ch = CHARACTERS.get(c.char_id)
                if ch is not None and fac in _char_traits(ch):
                    members.add(c.char_id)
        if _SEELE in owned:
            members.add(_SEELE)
        return len(members)
    fac = _card_factions(card)[0]
    n = 0
    for c in _owned_units(gs):
        if not getattr(c, 'char_id', ''):
            continue
        ch = CHARACTERS.get(c.char_id)
        if ch is not None and fac in _char_traits(ch):
            n += 1
    return n


# (card_state_of/_affix_weight/pick_card_combination/blank_window_policy
#  四函数已随配方决策层退役删除,考古走 git 历史;件数/激活/引擎完备度
#  数据层判据(card_pieces/card_active/card_engine_complete)保留——结算键
#  rung 与 A/B 判据工具链〔cw_engine_facts/ab_judge〕的消费面。)
