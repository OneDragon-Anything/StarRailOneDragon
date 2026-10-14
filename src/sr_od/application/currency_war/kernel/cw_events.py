"""货币战争 事件/节点族 kernel 决策:巨星/伙伴选项载体 + 银狼策划/
命运卜者/专家邀请函判据 + 装备名归一——本模块 = planner 等剩余画面
决策 + 观察载荷契约。遭遇与补给选卡决策不在本模块(宪法五:决策本体
归策略层 = ``strategies/impl/mandate_v1/encounter_pick.py`` /
``strategies/impl/mandate_v1/supply.py``;本模块仅留观察载荷契约
``EncounterOption``/``SupplyOption``)。

投资两屏选卡评序不在本模块(宪法五:衍生估值/评序归策略层):投资环境轴
= ``strategies/impl/mandate_v1/invest_env.py``(判据正本 = strategy-docs
28 号稿),投资策略轴 = ``strategies/impl/mandate_v1/invest_strategy.py``
(判据正本 = strategy-docs 29 号稿),flow 按 kind 分派。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.utils.str_utils import longest_common_subsequence_length
from sr_od.application.currency_war.data.cw_equipment_data import (
    EQUIPMENT_ROSTER,
)
from sr_od.application.currency_war.data.cw_equipment_wear_rules_data import (
    ITEM_WEAR_GATES,
)
from sr_od.application.currency_war.kernel.cw_equip_value import (
    equip_generic_value,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_units_of,
    deployed_rows_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp

# ===== 遭遇节点观察载荷契约(选档决策本体已迁策略层
# ``strategies/impl/mandate_v1/encounter_pick.py``,宪法五;本段仅留观察
# 载荷契约,消费方 = obs 写端 ``read_encounter_options``/容器
# ``gs.encounter``/观察上报/sim 占位/策略层)=====

@dataclass

class EncounterOption:
    """一个遭遇分支:难度档 + 敌人词缀 + 奖励(OCR 读,``read_encounter_options`` 阶段5)。

    观察载荷契约(与策略无关的游戏事实载体;决策语义单一源 = 策略层
    ``encounter_pick.py``)。
    difficulty:难度档 1-6(画面标题「遭遇其X」派生,OCR 漏读「一」→ 1;
    越高敌人越强、奖励越好)。
    affixes:敌人词缀 OCR 原名(经 ``AFFIX_MECHANIC_MAP`` → 机制 tag;
    选项 UI 不显词缀、战后才显——现役写端恒空列表,死输入申报已登记)。
    rewards:奖励(钻/装备/金币;偏好序消费 = 策略层 encounter_pick
    reward_tier 档序)。
    """
    idx: int
    difficulty: int = 1
    affixes: list[str] = field(default_factory=list)
    rewards: list[str] = field(default_factory=list)



# ===== 补给节点(决策本体已迁策略层 ``strategies/impl/mandate_v1/supply.py``
# (宪法五);本段仅留观察载荷契约 ``SupplyOption``,消费方 = obs 写端
# ``read_supply_options``/容器 ``gs.supply``/观察上报/sim 占位/策略层)=====

@dataclass

class SupplyOption:
    """一个补给选项 = 一列(角色 + 随选装备组;选中一并获得,**非穿戴
    语义**——角色入席不带装备、装备入栏,与现役发放语义一致;OCR/视觉
    读,``read_supply_options`` 阶段5)。

    观察载荷契约(与策略无关的游戏事实载体,形状五方引用;决策语义单一
    源 = 策略层 supply.py,宪法五)。
    has_diamond:装备位带三钻之一(红钻/蓝钻/财富宝钻;SIFT 主通道 + 文本
    兜底双通道,检测集单一源 =
    ``kernel/cw_obs_core.DIAMOND_EQUIP_NAMES``)。
    equip:列内画面 y 序首件装备名(OCR 原文,未归一;归一发生在选卡
    上报,``normalize_registry_equip_name``)。
    extra_equips:列内其余装备名(OCR 原文,未归一;y 序 = equip 之后;
    归一同 equip 两段式;默认 () = 单装备布局,additive 字段——既有
    消费面(``equip/char/has_diamond``)零变化)。
    """
    idx: int
    char: str = ""
    equip: str = ""
    has_diamond: bool = False
    extra_equips: tuple[str, ...] = ()


def _equip_value(equip: str) -> int:
    """装备通用价值(0=未知/无;共享机器单一源,表本体已迁
    ``cw_equip_value.EQUIP_GENERIC_VALUE``,值零变化)。"""
    return equip_generic_value(equip)


# ===== 巨星节点(decide_megastar;✅ 已派发 `cw_screen_megastar` 画面 op(候选标准化门 = op-layer.md §1.1,读缺 = 观察失败零盲发);本节点决策 = `decide_megastar`)=====

@dataclass

class MegastarOption:
    """一个巨星候选(OCR 读角色名(``obs/cw_megastar_obs.py::read_megastar_options``);/§11.3.4⑥)。

    char_id:候选角色名(空 = 读缺(画面 op 观察失败 round_fail 零盲发);非空 = cw_chars 规范名(观察侧标准化门产出))。
    xy:该候选的点击坐标 ``tuple[int, int]``(x, y,1080p 游戏空间;
    观察期快照 = 进访问入口观察帧识别产物,动作执行期恒稳;None = 未观察)。
    坐标单一真相源 = 观察上报(规范 = screens/op-layer.md §1.1「选择坐标
    观察上报」+ game_state/fields.md §3.4.5a B 类):动作 op 按 ``idx``
    自容器 ``megastar_opts[idx].xy`` 取点执行,动作/上报层零坐标现算。
    """
    idx: int
    char_id: str = ""
    xy: tuple[int, int] | None = None


@dataclass

class MegastarPick:
    """decide_megastar 返回:选第几个候选 + 原因。

    enhance_char_id:巨星 overlay step2「强化角色」意向(我方角色名);
    恒 None(强化角色决策意向已停用;字段保留兼容既有
    遥测/执行面读取,勿重接)。
    """
    idx: int
    reason: str = ""
    enhance_char_id: str | None = None


# ===== 选择伙伴节点(decide_partner;宿主 = operations/cw_screen/cw_screen_partner.py;候选真身 = SIFT 立绘识别,识别失败回落 label 流派名)=====

@dataclass

class PartnerOption:
    """一个伙伴候选(角色名 = SIFT 真身识别产物,识别失败回落 label 流派名;
    生产读端 = 画面 op 观察 node 一次读,cw_screen_partner.py::observe)。

    [索引定义] idx:坐标系 = 画面物理候选位序(左→右)0 基,与
    ``CwScreenPartnerObs.options``/容器 ``partner_opts`` 槽同一候选列表;
    取值时机 = 观察 node 入口帧一次读快照,访问内恒稳。
    char_id:候选角色名(空 = 识别未命中回落失败/读缺;识别失败回落
    流派名/空 = op-layer.md §1.1 :34 转换失败待修项形态,收敛方向 = 观察
    失败 round_fail 零写零上报;屏级转换成功性边界由 screens/partner.md
    登记,含多候选同名同判);缺省选卡语义单一源 = 策略器 ``decide_partner``
    (strategy-docs/13_pick_family.md §1 E6)。
    """
    idx: int
    char_id: str = ""


@dataclass

class PartnerPick:
    """kernel 时代伙伴选卡返回载体,已被 ``cw_vocab.CwActionPickPartnerParam``
    替代(替代关系已登记 = cw_vocab 该类 docstring);现役仅 ``EVENT_PICK_TYPES``
    登记在场(登记面,零生产零消费)。

    [索引定义] idx:历史语义 = 候选列表下标 0 基(登记面保留,现役零消费)。
    """
    idx: int
    reason: str = ""


# ===== 银狼策划事件(decide_planner;用户定调「接入策略模块,由策略模块定」;
#      机制见 docs/game/gameplay/currency_war.md 银狼策划事件节)=====

@dataclass
class PlannerOption:
    """一个策划选项(OCR 卡文字)。

    text:卡描述全文(如「提升费用至4费,变为1星银狼LV.999」/「使后续节点【弱化】…」/
    装备名+效果)。「提升费用」字样判升费卡由本模块打分表达,handler 不写死。
    升费腿结果 = 变为下一个费用档的 1 星银狼LV.999(卡面「变为1星银狼LV.999」
    即指此:单位身份保持银狼LV.999、费用档升一级、星级为 1 星
    [口述·权威 2026-09-18];机制单一源 = docs/game/currency_war/research/
    equipment_mechanics.md §7)。
    """
    idx: int
    text: str = ''


@dataclass
class PlannerPick:
    """decide_planner 返回:选第几张卡 + 原因。"""
    idx: int
    reason: str = ''


def decide_planner(options: list[PlannerOption], gs: GameState,
                   target_comp: Comp | None = None) -> PlannerPick:
    """银狼「我来当策划」二选一策略。

    用户定调:**必接策略模块由它定**(handler 不写死默认),虽结论
    几乎总是升费——打分走通用原则,让「何时升费不是最优」可被策略表达。
    定形(16 号稿 §1.7):两档定序结构 = 升费档 > 装备档,
    各层方向均有出处(升费优先 = 用户定调 + 银狼策划机制原文;装备域内
    key_equip 命中优先 = 阵容知识);下列数值全部
    是档位实现常数,只承载层间/层内定序,非基准基数:

    - **升费档**(「提升费用」):银狼成长滚动投资前提(升费→新费档刷商店→3星5费
      滚强度)。档内修饰:target 含银狼线(狼尊欢愉/量子系)⇒ **升档**(100+30,
      升费兑现更高);银狼确定不在场(board 有信息但无银狼)⇒ **降档**(100−60,
      投资无处兑现);信息缺失不降权(在场判定保守)。
    - **装备档**(其余;含弱化词未知名卡文按本档回落):_equip_value 回落
      (装备注册表);target key_equip 命中 ⇒ **装备域内命中优先键**(+15,
      只在装备档内排前)。
    - 未识别文字:0 分(idx 顺序兜底)。
    """
    _tgt_chars = set(target_comp.core_chars) if target_comp is not None else set()
    _tgt_factions = set(target_comp.factions) if target_comp is not None else set()
    has_wolf_line = bool(_tgt_chars & {'银狼LV.999'}) or bool(
        _tgt_factions & {'欢愉', '量子同频'})
    # 在场判定:bench+deployed 的 char_id(容器单位域现读;信息缺失=空→不降权,保守)
    front, back = deployed_rows_of(gs)
    _owned = {u.char_id for u in (*front, *back, *bench_units_of(gs))
              if getattr(u, 'char_id', '')}
    wolf_owned = ('银狼LV.999' in _owned) if _owned else True

    best_idx, best_score, best_reason = 0, -1.0, ''
    for opt in options:
        score, reason = 0.0, ''
        t = opt.text
        if '提升费用' in t:
            score, reason = 100.0, '升费(滚动投资前提)'
            if has_wolf_line:
                score += 30.0
                reason += '+银狼线'
            elif not wolf_owned:
                score -= 60.0
                reason += '-银狼不在场无处兑现'
        else:
            score = float(_equip_value(t)) if t else 0.0
            reason = f'装备({t[:8]})' if t else '未识别'
            if t and target_comp is not None:
                _ke = getattr(target_comp, 'key_equips', None) or []
                if any(e in t for e in _ke):
                    score += 15.0
                    reason += '+key_equip'
        if score > best_score:
            best_idx, best_score, best_reason = opt.idx, score, reason
    return PlannerPick(idx=best_idx, reason=best_reason or '全部未识别,兜底左卡')


# ===== 银狼策划腿型判定单源(记账分类器)=====
# 职责边界:本分类器只答「这张卡落在哪条记账腿」(动作上报记账用),与
# :func:`decide_planner` 的选卡打分关键词是两套语义——决策打分词表(升费
# 优先级等)表达「选哪个」,本分类词表表达「选中后怎么记账」,二者
# 职责不同禁互相复用(混用 = 装备授予被决策词表误判 → 记账缺位失配停;
# 具体碰撞例 = 破解芯片卡文含「弱化」而实为装备卡,装备域优先判定消解)。

#: 腿型词表(封闭集):upgrade=升费腿 / equip=装备腿 / unknown=未识别
#: (零记账留存证据;含弱化词且装备锚未命中的卡文落 unknown——弱化兜底档
#: 已按原文二分法停用,静默零记账变响亮申报)。
PLANNER_LEG_UPGRADE: str = 'upgrade'
PLANNER_LEG_EQUIP: str = 'equip'
PLANNER_LEG_UNKNOWN: str = 'unknown'

#: 装备域锚名单单一源 = 银狼专属 10 件穿戴门键集(data/cw_equipment_wear_
#: rules_data.ITEM_WEAR_GATES——同一名单的第二个消费面,名单收窄/扩圈自动
#: 跟随;禁复制名单成第二源)。longest-first 排序 = 构建期定序,「分身墨镜
#: Max」先于「分身墨镜」受检(防短名截胡归一)。
_PLANNER_EQUIP_ANCHORS: tuple[str, ...] = tuple(
    sorted(ITEM_WEAR_GATES, key=len, reverse=True))

#: 注册表相似归一的 LCS 占比下限(相对件名长度;0.75 = 件名 4 字容错 1 字
#: OCR 缺字,再低会把升费卡文「…银狼LV.999」等长文本误挂到短件名上)。
_EQUIP_NORM_LCS_FLOOR: float = 0.75


def _similar_equip_hits(text: str) -> list[str]:
    """注册表相似候选集(longest-first;LCS 占比 ≥
    :data:`_EQUIP_NORM_LCS_FLOOR`,相对件名长度)。"""
    t = text or ''
    if not t:
        return []
    return [name for name in _PLANNER_EQUIP_ANCHORS
            if (longest_common_subsequence_length(t, name) / len(name))
            >= _EQUIP_NORM_LCS_FLOOR]


def normalize_equip_name(text: str) -> str:
    """卡面 OCR 文本 × 装备注册表相似归一(longest-match 优先;design
    §2.1① equip 件名归一单一源)。

    - 判据 = :func:`_similar_equip_hits`;**唯一命中**才返回归一件名,
      零/多命中返回 ''(未解析——禁猜名,记账侧走值不变翻来源留存证据);
    - 纯函数零副作用,handler 决策半与测试共用。
    """
    hits = _similar_equip_hits(text)
    return hits[0] if len(hits) == 1 else ''


# ===== 补给装备名注册表级分层归一(迭代 2026-09-21-event-refresh-unify-
# ===== supply-pick design §2.0B;与上方银狼锚归一两入口分立,互不复用)=====

#: 装备注册表全键集 longest-first 定序(分层归一第 2 层 containment 与
#: 第 3 层相似的遍历序;构建期定序,「分身墨镜Max」先于「分身墨镜」受检)。
_REGISTRY_EQUIP_NAMES: tuple[str, ...] = tuple(
    sorted(EQUIPMENT_ROSTER, key=len, reverse=True))


def normalize_registry_equip_name(text: str) -> str:
    """补给侧装备名归一(注册表 158 键全键集分层归一;design §2.0B)。

    与 :func:`normalize_equip_name`(银狼锚 10 件集)分立:补给基础件不在
    银狼锚名单,恒未解析——故另立本入口,键集 = 装备注册表全键集。

    层级(定死,相似判据不得为首层——纯 LCS 0.75 直移 158 名键集时,
    完美 OCR 下 79/158 名多命中拒识:垃圾袋/金垃圾袋、生命之花/生命之环
    0.75 互撞、追击/击破星徽互撞、36 个特权名全撞进阶基名、Max/Pro
    后缀族等,精确相等必须走快道):

    1. **精确快道**:text 与注册表键名全等 → 直返;
    2. **containment longest-first**:注册表名 contained in text 取最长
       唯一(「·特权」类装饰噪声由本层消解;后缀族白昼/极·白昼同层按
       最长胜出);并列最长 → 落第 3 层;
    3. **相似救援**:LCS 占比 ≥ :data:`_EQUIP_NORM_LCS_FLOOR`(相对
       件名长度)唯一命中 → 返回;多命中/零命中 → ''(禁猜,fail-closed:
       错名不入账,报告侧翻来源留存证据,观察覆盖自愈)。

    纯函数零副作用,补给 handler 组装点与测试共用。
    """
    t = text or ''
    if not t:
        return ''
    if t in EQUIPMENT_ROSTER:
        return t
    best_len = 0
    contain_hits: list[str] = []
    for name in _REGISTRY_EQUIP_NAMES:
        if len(name) < best_len:
            break   # longest-first 定序,更短的不可能再并列最长
        if name in t:
            best_len = len(name)
            contain_hits.append(name)
    if len(contain_hits) == 1 and best_len > 0:
        return contain_hits[0]
    # 并列最长(歧义)或零 containment 命中 → 相似救援层。
    sim = [name for name in _REGISTRY_EQUIP_NAMES
           if (longest_common_subsequence_length(t, name) / len(name))
           >= _EQUIP_NORM_LCS_FLOOR]
    return sim[0] if len(sim) == 1 else ''


def classify_planner_leg(text: str) -> tuple[str, str]:
    """银狼策划选项腿型判定单源(记账分类器;全序)。

    判定序(装备域优先):
    1. **锚匹配**:银狼专属 10 件名单(:data:`_PLANNER_EQUIP_ANCHORS`,
       longest-first)件名 containment 命中 → equip,归一件名 = 命中锚
       (破解芯片卡文含「弱化」的碰撞在此消解——锚先于关键词);
    2. **相似归一**:锚未中 → :func:`_similar_equip_hits`——唯一命中 →
       equip(OCR 形变救援);**多命中 → equip 且件名未解析**(norm_item
       ='':多件注册表名同时高相似 = 装备信号成立而件名不可辨,禁猜——
       记账侧走值不变翻来源留存证据);零命中 = 无装备信号;
    3. **升费关键词**:「提升费用」→ upgrade(记账分类词表 = 本函数内联
       面,非 decide_planner 决策词表;弱化兜底档已停用——含弱化词且
       装备锚未命中的卡文落步 4 unknown,静默零记账变响亮留存证据);
    4. 空/未识别 → unknown(零记账,台账行证未识别事实)。

    返回 ``(leg_type, norm_item)``:norm_item 仅 equip 腿携带归一件名,
    其余腿恒 ''。
    """
    t = text or ''
    if not t:
        return (PLANNER_LEG_UNKNOWN, '')
    for anchor in _PLANNER_EQUIP_ANCHORS:   # longest-first:Max 先于短名
        if anchor in t:
            return (PLANNER_LEG_EQUIP, anchor)
    hits = _similar_equip_hits(t)
    if len(hits) == 1:
        return (PLANNER_LEG_EQUIP, hits[0])
    if len(hits) > 1:
        return (PLANNER_LEG_EQUIP, '')
    if '提升费用' in t:
        return (PLANNER_LEG_UPGRADE, '')
    return (PLANNER_LEG_UNKNOWN, '')


# ===== 命运卜者强化三选一(decide_fortune 判据;F-overlay-01
# ===== 判据体 = cw_screen_fortune handler 内联文本规则的逐位转写)
# ===== 单一源住 kernel,handler 留 OCR 分桶/写槽/点卡/确认链)=====

#: 战力关键词权重表(逐位平移自 handler v1)。累加制:同文多词各计各的——
#: 「伤害倍率」文本同时命中「伤害」「提高」子串,是迁移前既有行为非重复计分缺陷。
FORTUNE_KEYWORD_WEIGHTS: tuple[tuple[str, float], ...] = (
    ('伤害倍率', 3.0), ('强度提高', 2.0), ('层数提高', 2.0),
    ('伤害', 1.0), ('提高', 0.5),
)


def decide_fortune(texts: list[str]) -> int:
    """命运卜者强化三选一 → 应点选的卡下标(0 基;卡序 = handler OCR 分桶序)。

    判据(行为保持版,逐位复刻迁移前实码):逐卡累加命中关键词权重 →
    严格大于 argmax(并列取首卡);全无命中(全 0 分)= 首卡(卡 1 缺省,
    保守向);texts 为空同样落 0。
    """
    best_i, best_s = 0, -1.0
    for i, t in enumerate(texts):
        s = 0.0
        for kw, w in FORTUNE_KEYWORD_WEIGHTS:
            if kw in t:
                s += w
        if s > best_s:
            best_i, best_s = i, s
    return best_i


# ===== 专家邀请函选卡(choose_expert_index;F-overlay-02
# ===== 判据体 = cw_screen_expert_invite 整函数的逐位转写,三级语义原样)=====


def choose_expert_index(card_bonds: list[str | None],
                        board: dict[str, int]) -> int:
    """默认策略:返回应点选的卡下标(0..n-1);-1 = 现金为王。

    判据(行为保持版=在场浓度版,三级语义原样):
    ① 主力阵营(在场计数最大;并列取名字序首个,保证确定性)同线优先;
    ② 次选任意在场阵营(board 计数 > 0)同线——羁绊面板口径 = factions∪flows
    并计(read_board),卡上阵营/流派标签同属一个羁绊命名空间,可直接对键;
    ③ 全无同线 → -1(现金为王)。
    board 为空(读数失败)走 ③:选卡无依据时经济兜底优于盲选。

    边界:本实现与 13_pick_family.md E9 在案规格(目标线成员优先 → 池
    浓度)是两套语义,分叉已登记为独立行为变更待办——本函数保持实码行为。
    """
    if not card_bonds or not board:
        return -1
    dominant = max(sorted(board), key=lambda f: board[f])
    for i, bond in enumerate(card_bonds):
        if bond is not None and bond == dominant:
            return i
    for i, bond in enumerate(card_bonds):
        if bond is not None and board.get(bond, 0) > 0:
            return i
    return -1


# ===== 事件线 pick 族运行时元组(kernel 纯函数返回载体
# ===== 元组。终态契约 §2.2:策略器产出 = cw_vocab 词表 Pick 子类型并
# ===== 收敛单表 CW_ACTION_TYPES,本表 = kernel decide_* 返回载体的
# ===== 运行时登记,注册完备锁遍历走词表单表)=====

#: 事件线 kernel pick 全类(kernel ``decide_*`` 纯函数返回载体;策略入口
#: 负责包装成词表动作子类型——kernel 判据零触碰,§2.2)。
EVENT_PICK_TYPES: tuple = (
    MegastarPick, PartnerPick, PlannerPick,
)

#: pick 族类型联合(kernel 侧注解用;运行时零消费)。
EventPick = MegastarPick | PartnerPick | PlannerPick
