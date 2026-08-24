"""货币战争 P1 体系卡+组合规则(契约包 C2,步 4 第一批;判断层手编;2026-08-25)。

**单一源**:
- 教义 = ``.debug/temp/currency_war/cw_dev/deep_read/p1_definition.md``(体系卡四张/
  组合规则/升级路径;判据语义逐字对齐);
- 契约 = 同目录 ``契约包_C1-C7.md`` C2 节(签名冻结级;判据内部权重草案级);
- tier 阈值单一源 = ``cw_factions.FACTIONS``(仙舟 3 档/持续伤害 2 档/列车同行 2 档/
  量子同频 2 档/贝洛伯格 2 档均取 ``tiers[0]``,不在本文件重复硬编码);
- 铁三角名单 = ``cw_line_defs._CORE_TRIO`` 注册表真值(爻光+藿藿+丹恒·饮月,
  W26 测试锚;本文件只 import 不复制)。

**契约偏差声明(C2 落地时点)**:
1. C2 伪码签名 ``card_active(card, board_by_row: BoardByRow)`` —— **已换源
   (W38,C6 落地,偏差①闭环)**:``_faction_count`` 身份口径改读
   ``cw_board_by_row.board_by_row(deployed)`` 全板合计视图(全仓按排聚合单一源);
   判据语义零变化(仍取 max(board OCR, 身份计数));``card_active`` 入口签名
   保持 ``GameState``(C2 落地批任务规格,BoardByRow 经由内部消费);
2. C2 伪码返回 ``EngineState`` —— 本批按任务规格返回 ``bool``(缺件审计走
   ``engine_missing``;EngineState 包装留给 decision_v2 接线批,非本批接口面);
3. C2 伪码 ``pick_card_combination(cards_state, intent, affixes)`` —— 本批按任务
   规格直接接 ``GameState``(CardState 在函数内组装后参与打分,类型已建)。

消费方(后续批接线):decision_v2/candidates 层1 目标集换源、体系判定(board_rung
口径重接)、空窗期买门。**本批不接线任何消费点**(纯查询面 + 锁测试)。

词条吃怕表(数据字段 ``affix_likes``/``affix_fears``):词缀名与
``affix_effects_data``/竞品 data 对齐(DOT 吃敌方频动=忍无可忍/同步行动/应激反应,
怕净化身心;希儿警惕量子熄火;仙舟/列车泛用)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_board_by_row import board_by_row
from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.application.currency_war.cw_line_defs import _CORE_TRIO
from sr_od.application.currency_war.cw_state import GameState

# ===== 判据常量(tier 阈值派生自 FACTIONS,单一源)=====
_XIANZHOU_TIER: int = FACTIONS['仙舟'].tiers[0]              # 3(仙舟≥3 激活)
_DOT_TIER: int = FACTIONS['持续伤害'].tiers[0]               # 2(持续伤害≥2)
_TRAIN_TIER: int = FACTIONS['列车同行'].tiers[0]             # 2(列车同行≥2)
_QUANTUM_TIER: int = FACTIONS['量子同频'].tiers[0]           # 2(希儿 OR 分支)
_BELLY_TIER: int = FACTIONS['贝洛伯格'].tiers[0]             # 2(希儿 OR 分支)

_SEELE: str = '希儿'   # 卡4 引擎单卡(伤害全在她技能层,量子/贝是放大器)

# ===== 组合规则权重(草案级,C2 明示「判据内部权重草案级,步 4 调优」)=====
_WEIGHT_PIECE: float = 1.0        # 来牌主判据:每件 +1(主权重)
_WEIGHT_INTENT_ALIGNED: float = 0.5   # 意向同向 tie-break(非一票否决;量级刻意 < 1 件
#   来牌——tie-break 只裁同分,不得翻越「来牌主判据」)
_WEIGHT_AFFIX_LIKE: float = 1.5       # 词条吃:每条命中
_WEIGHT_AFFIX_FEAR: float = -3.0      # 词条怕:每条命中(怕>吃,counter 警惕优先)
_WEIGHT_DOT_FIRST: float = 1.0        # DOT2 默认首站加成(可达时;p1_definition 组合规则3)
_WEIGHT_TRIO_READY: float = 6.0       # 铁三角一轮成型直取仙舟3(例外条款,权重盖过常规差)

# 意向→体系同向映射(草案级;家族键 = cw_comps.V2_FAMILIES 子集,未知键→无加成)
_INTENT_CARD_MAP: dict[str, str] = {
    'DOT卡芙卡': 'dot2',
    '希儿量子': 'seele',
    '姬子列车': 'train2',
}


@dataclass(frozen=True)
class SystemCard:
    """一张 P1 体系卡(乐高块;p1_definition 一·体系卡)。

    - ``card_id``:'xianzhou3' | 'dot2' | 'train2' | 'seele';
    - ``judge``:判据描述(文档性;**函数 ``card_active`` 才是权威**);
    - ``engine_required``:引擎件(仙舟=铁三角三人;其余空);
    - ``star_goal``:星级目标(仙舟铁三角 2★;希儿 3★;其余不追);
    - ``affix_likes``/``affix_fears``:词条吃怕表(数据字段;输入=
      ``pick_card_combination(affixes=...)`` 的敌方词缀名,逐条命中计数)。
    """
    card_id: str
    display_name: str
    judge: str
    engine_required: list[str]
    star_goal: dict[str, int]
    affix_likes: list[str] = field(default_factory=list)
    affix_fears: list[str] = field(default_factory=list)


SYSTEM_CARDS: dict[str, SystemCard] = {
    'xianzhou3': SystemCard(
        card_id='xianzhou3', display_name='仙舟3',
        judge='仙舟≥3 人(3 人档激活);引擎=铁三角功能链不可拆(缺一=空壳)',
        engine_required=sorted(_CORE_TRIO),
        star_goal=dict.fromkeys(_CORE_TRIO, 2),   # 铁三角 2★ 即成型;不追 3★
        affix_likes=[],                          # 词条泛用(神君不挑敌方形态)
        affix_fears=[],
    ),
    'dot2': SystemCard(
        card_id='dot2', display_name='DOT2',
        judge='持续伤害≥2 人(2 人档激活,最低门槛);无引擎要求',
        engine_required=[],
        star_goal={},                            # 星级不追
        affix_likes=['忍无可忍', '同步行动', '应激反应'],   # 吃敌方频动→DOT 多结算
        affix_fears=['净化身心'],                # 敌解负面+回血(羁绊注册表 note:该环境别玩 DOT)
    ),
    'train2': SystemCard(
        card_id='train2', display_name='列车2',
        judge='列车同行≥2 人;无引擎(凑出就能用)',
        engine_required=[],
        star_goal={},
        affix_likes=[],                          # 词条泛用
        affix_fears=[],
    ),
    'seele': SystemCard(
        card_id='seele', display_name='希儿系',
        judge='希儿在场 AND(量子同频≥2 OR 贝洛伯格≥2);引擎=希儿单卡',
        engine_required=[_SEELE],
        star_goal={_SEELE: 3},                   # 希儿追 3★(高饥渴线,从 P1 就可开始)
        affix_likes=[],
        affix_fears=['量子熄火'],                # 量子属性伤害限 1(重开级 counter)
    ),
}


@dataclass(frozen=True)
class CardState:
    """一张体系卡的当前状态(C2 支撑类型:件数/引擎完备度)。

    - ``pieces``:该体系当前件数(在场+bench 的该系件数,来牌主判据的输入);
    - ``active``:体系判定(``card_active``);
    - ``engine_complete``:引擎完备度(``card_engine_complete``,owned=在场∪bench)。
    """
    card_id: str
    pieces: int
    active: bool
    engine_complete: bool


@dataclass(frozen=True)
class CombinationDecision:
    """``pick_card_combination`` 的组合建议(C2:返回选中的 1-2 张卡+裁决记录)。

    - ``chosen``:选中的 card_id 列表(1-2 个,序=主→副);
    - ``blank_window``:True = 四体系一个都没凑成(空窗期,走 ``blank_window_policy``);
    - ``scores``:各卡打分明细(审计);
    - ``ruling``:裁决记录(同分 tie-break 必非空,C2 冻结要求「可审计」)。
    """
    chosen: list[str]
    blank_window: bool
    scores: dict[str, float]
    ruling: list[str]


@dataclass(frozen=True)
class BlankWindowDecision:
    """``blank_window_policy`` 的空窗期行为建议(p1_definition 组合规则4)。

    - ``is_blank``:是否空窗(四体系一个都没凑成);
    - ``target_char_ids``:买侧目标件(引擎件见即买:铁三角+希儿);
    - ``target_factions``:来牌方向的目标阵营(已有件的体系——「目标件出现只买它」);
    - ``buy_idx``:当前商店里可买的目标件索引(char 命中 target 集合的槽位);
    - ``cost_band``:压库目标费用带(无目标件时按此带压库;草案级=目标件费用众数);
    - ``ruling``:裁决记录。
    """
    is_blank: bool
    target_char_ids: list[str]
    target_factions: list[str]
    buy_idx: list[int]
    cost_band: int
    ruling: list[str]


# ===== 体系判定(冻结的判据语义;p1_definition 一)=====

def _char_traits(ch) -> tuple[str, ...]:
    """角色的全部羁绊 tag(阵营 factions + 流派 flows)。

    持续伤害/量子同频等是**流派**羁绊(cw_chars.Character.flows),仙舟/贝洛伯格
    等是阵营(factions)——判据消费「该角色算不算某羁绊的件」必须双看(单看
    factions 会漏 DOT/量子件)。
    """
    return (ch.factions or ()) + (ch.flows or ())


def _owned_names(state: GameState) -> set[str]:
    """在场∪bench 的角色名集合(char_id 已识别者;tracking 未识别的槽不计)。"""
    names: set[str] = set()
    for c in list(state.deployed) + list(state.bench):
        if getattr(c, 'char_id', ''):
            names.add(c.char_id)
    return names


def _faction_count(state: GameState, faction: str) -> int:
    """板上某羁绊的计数(身份口径优先,board OCR 兜底,取 max)。

    deployed 与 board 应一致(cw_state 头注);单侧 miss(OCR 漏/重建缺身份)时
    取 max 容错——**判激活侧非计费侧**,漏判激活比多判更伤(体系卡是 P1 战力主体)。
    身份口径 = C6 ``board_by_row`` 全板合计视图(全仓按排聚合单一源,W38 换源
    闭环契约偏差①;口径与旧内联版逐字一致:CHARACTERS[char_id] 羁绊全集,
    多羁绊角色每系都计)。
    """
    cnt_board = state.board.get(faction, 0)
    cnt_ident = board_by_row(state.deployed).count(faction)
    return max(cnt_board, cnt_ident)


def _seele_on_board(state: GameState) -> bool:
    """希儿在场(= 上阵 deployed;bench 不算「在场」)。"""
    return any(c.char_id == _SEELE for c in state.deployed)


def card_active(card: SystemCard, state: GameState) -> bool:
    """体系判定(C2 冻结判据语义,逐字对 p1_definition):

    - 仙舟3 = 仙舟 ≥3;
    - DOT2 = 持续伤害 ≥2;
    - 列车2 = 列车同行 ≥2;
    - 希儿系 = 希儿在场 AND(量子同频 ≥2 OR 贝洛伯格 ≥2)。
    """
    if card.card_id == 'xianzhou3':
        return _faction_count(state, '仙舟') >= _XIANZHOU_TIER
    if card.card_id == 'dot2':
        return _faction_count(state, '持续伤害') >= _DOT_TIER
    if card.card_id == 'train2':
        return _faction_count(state, '列车同行') >= _TRAIN_TIER
    if card.card_id == 'seele':
        if not _seele_on_board(state):
            return False
        return (_faction_count(state, '量子同频') >= _QUANTUM_TIER
                or _faction_count(state, '贝洛伯格') >= _BELLY_TIER)
    raise ValueError(f'未知体系卡: {card.card_id}')


def card_engine_complete(card: SystemCard, owned: set[str]) -> bool:
    """引擎完备度(C2 冻结语义):仙舟=铁三角三人组到齐(缺一=空壳);无引擎卡恒 True。

    ``owned`` = 拥有角色名集合(在场∪bench 口径,由调用方给;判据只看「有没有」,
    bench 里的引擎件算到齐——上场时机归演进引擎/围栏,不归本判定)。
    """
    if not card.engine_required:
        return True
    return all(n in owned for n in card.engine_required)


def engine_missing(card: SystemCard, owned: set[str]) -> list[str]:
    """引擎缺口清单(审计用;``card_engine_complete`` 的明细对偶)。"""
    return [n for n in card.engine_required if n not in owned]


# ===== 件数/组合选择(组合规则 1-3;权重草案级)=====

def _card_factions(card: SystemCard) -> tuple[str, ...]:
    """该体系卡的判据阵营(希儿系双分支;其余单阵营)。"""
    if card.card_id == 'seele':
        return ('量子同频', '贝洛伯格')
    return ({'xianzhou3': '仙舟', 'dot2': '持续伤害',
             'train2': '列车同行'}[card.card_id],)


def card_pieces(card: SystemCard, state: GameState) -> int:
    """该体系当前件数(来牌主判据):在场+bench 的该系件数(含引擎件)。

    - 阵营系(仙舟/DOT/列车):按阵营成员身份计(deployed∪bench);
    - 希儿系:希儿在手(在场∪bench)计 1 + 量子/贝成员件数(bench+deployed
      身份口径)——引擎+放大器合为「件数」近似。
    """
    if card.card_id == 'seele':
        owned = _owned_names(state)
        if _SEELE not in owned:
            return 0   # 无希儿时量子/贝不能独立当过渡(放大器不算来牌方向)
        # 引擎(希儿)+ 放大器(量子/贝成员)按**角色去重**计件(多羁绊角色
        # 双分支只计一次;希儿本人既是引擎又属双分支,也只计一次)
        members: set[str] = set()
        for fac in _card_factions(card):
            for c in list(state.deployed) + list(state.bench):
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
    for c in list(state.deployed) + list(state.bench):
        if not getattr(c, 'char_id', ''):
            continue
        ch = CHARACTERS.get(c.char_id)
        if ch is not None and fac in _char_traits(ch):
            n += 1
    return n


def card_state_of(card: SystemCard, state: GameState) -> CardState:
    """组装单张卡的 CardState(件数/激活/引擎完备度)。"""
    return CardState(
        card_id=card.card_id,
        pieces=card_pieces(card, state),
        active=card_active(card, state),
        engine_complete=card_engine_complete(card, _owned_names(state)),
    )


def _affix_weight(card: SystemCard, affixes: list[str]) -> float:
    """词条吃怕权重:敌方词缀命中 likes/fears 逐条计(词条前置输入,组合规则2)。"""
    w = 0.0
    for a in affixes or ():
        if a in card.affix_likes:
            w += _WEIGHT_AFFIX_LIKE
        if a in card.affix_fears:
            w += _WEIGHT_AFFIX_FEAR
    return w


def pick_card_combination(state: GameState, intent: str | None = None,
                           affixes: list[str] | None = None) -> CombinationDecision:
    """组合选择(p1_definition 组合规则 1-3;C2 冻结入口形状,权重草案级)。

    - 主判据=来牌(``card_pieces``,哪系件先到);
    - 次=意向同向 tie-break(intent=家族键,非一票否决,同分裁决);
    - 词条输入(affixes=敌方词缀名;频动旺→DOT 权重升,净化身心→DOT 权重降);
    - DOT2 默认首站:可达(在手 DOT 件 ≥2)即加成;
      例外=仙舟铁三角一轮成型(三人全在手)直取仙舟3;
    - 空窗(四系件数为 0 且无可达)→ blank_window=True,chosen=[]。
    """
    affixes = list(affixes or [])
    owned = _owned_names(state)
    states = {cid: card_state_of(card, state) for cid, card in SYSTEM_CARDS.items()}
    scores: dict[str, float] = {}
    for cid, cs in states.items():
        card = SYSTEM_CARDS[cid]
        w = cs.pieces * _WEIGHT_PIECE + _affix_weight(card, affixes)
        if intent is not None and _INTENT_CARD_MAP.get(intent) == cid:
            w += _WEIGHT_INTENT_ALIGNED
        scores[cid] = w
    ruling: list[str] = []
    trio_ready = card_engine_complete(SYSTEM_CARDS['xianzhou3'], owned)
    dot_reachable = states['dot2'].pieces >= _DOT_TIER
    if trio_ready:
        scores['xianzhou3'] += _WEIGHT_TRIO_READY
        ruling.append('铁三角一轮成型→直取仙舟3(例外条款)')
    if dot_reachable and not trio_ready:
        scores['dot2'] += _WEIGHT_DOT_FIRST
        ruling.append('DOT2 可达→默认首站加成')
    ranked = sorted(scores, key=lambda cid: (-scores[cid], cid))
    top = ranked[0]
    if scores[top] <= 0.0:
        # 空窗:无来牌迹象且无词条/意向推动 → 不选卡
        return CombinationDecision(
            chosen=[], blank_window=True, scores=scores,
            ruling=['四体系一件未到→空窗期(blank_window_policy 接管)'],
        )
    chosen = [top]
    second = ranked[1]
    if states[second].pieces >= 1 and scores[second] > 0.0:
        chosen.append(second)   # 两两组合过 P1(组合规则1):副卡=次优且有来牌
    # 同分 tie-break 审计(C2 冻结:裁决记录可审计;同分构造下非空)
    if len(ranked) > 1 and abs(scores[ranked[0]] - scores[ranked[1]]) < 1e-9:
        ruling.append(f'同分 tie-break:{ranked[0]} vs {ranked[1]} 平分,'
                      f'按稳定序(card_id 字典序)取 {top}')
    if intent is not None:
        ruling.append(f'意向={intent}'
                      + (f'→同向 {top}' if _INTENT_CARD_MAP.get(intent) == top
                         else '(非同向,仅 tie-break 加成不否决)'))
    if affixes:
        ruling.append(f'词条输入={affixes}')
    ruling.append('打分明细:' + ', '.join(f'{cid}={scores[cid]:g}'
                                         for cid in ranked))
    return CombinationDecision(chosen=chosen, blank_window=False,
                               scores=scores, ruling=ruling)


# ===== 空窗期规则(组合规则4;p1_definition 二.4)=====

def blank_window_policy(state: GameState) -> BlankWindowDecision:
    """空窗期规则入口(四体系一个都没凑成,通常仅前 1-2 轮)。

    - 买侧 = 目标件出现只买它,否则压当前目标费用带([30] 压库模型:买同费件,
      目标出货概率随池空升高;费用带=目标件费用众数,草案级);
    - 上场侧 = 现有牌最优羁绊组合(归部署围栏/decision_v2,本入口只管买侧);
    - **绝不为凑数 D 牌**([31]):off-target 件一律不进 buy_idx。
    """
    active_any = any(card_active(card, state) for card in SYSTEM_CARDS.values())
    if active_any:
        return BlankWindowDecision(
            is_blank=False, target_char_ids=[], target_factions=[],
            buy_idx=[], cost_band=0,
            ruling=['已有体系激活,非空窗(走 pick_card_combination)'],
        )
    # 目标件:引擎件见即买(铁三角+希儿;点3)+ 来牌方向(已有 ≥1 件的体系阵营)
    engine_chars = sorted(set(SYSTEM_CARDS['xianzhou3'].engine_required)
                          | set(SYSTEM_CARDS['seele'].engine_required))
    target_factions: list[str] = []
    for cid, card in SYSTEM_CARDS.items():
        if cid == 'seele':
            continue   # 希儿系放大器不独立当方向(无希儿时量子/贝不能独立当过渡)
        if card_pieces(card, state) >= 1:
            target_factions.append(_card_factions(card)[0])
    target_chars = list(engine_chars)
    # buy_idx:店内目标件(具名引擎件,或来牌方向阵营的件)
    buy_idx: list[int] = []
    for i, card in enumerate(state.shop):
        if card.name and card.name in engine_chars:
            buy_idx.append(i)
            continue
        if card.faction and card.faction in target_factions:
            buy_idx.append(i)
    # 费用带(草案级):目标件费用众数;无目标件时兜底 1(前 1-2 轮低费带);
    # 同频取低费(前 1-2 轮压库偏保守)
    costs = [CHARACTERS[n].cost for n in engine_chars if n in CHARACTERS]
    cost_band = (sorted(costs, key=lambda c: (-costs.count(c), c))[0]
                 if costs else 1)
    ruling = ['空窗期:目标件出现只买它,否则压费用带;'
              '绝不为凑数 D 牌([31])']
    if target_factions:
        ruling.append(f'来牌方向={target_factions}(只买该方向件+引擎件)')
    else:
        ruling.append('无来牌方向:仅引擎件(铁三角+希儿)见即买')
    return BlankWindowDecision(
        is_blank=True, target_char_ids=target_chars,
        target_factions=target_factions, buy_idx=buy_idx,
        cost_band=cost_band, ruling=ruling,
    )
