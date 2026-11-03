"""终局线选择内核(统一阵容评分;迭代 2026-11-03-unified-line-scoring)。

判据唯一源 = strategy-docs/12_line_and_intention.md §1(统一阵容评分:
**纯加权和,一个公式** + 数量级表——四轮对抗审查定稿,特殊处理全退役,
排除 = 极大减分非布尔特判)。本模块承载:

- **线分数值化**(§1.1 单值和;数量级常数单一源 =
  :mod:`kernel/cw_line_scales`,本模块零裸数字)+ top3 候选;
- **候选入选证据门**(§1.2:线分量 env ∨ carry ∨ 骨架 ∨ 插件 > 0——
  **不含热度**,热度只作有证据线间的排序,不是入选理由);
- **锁定 = P2 时点兜底唯一路径**(§1.3/design §6:硬规则查表/角色硬锁/
  策略即时锁全退役——拿到什么都不直接锁,分数说话;锁定 =
  ``plane2_started ∧ p2_strategy_pick_done`` → 候选首名;无排除过滤,
  重开级已数值化,全线极低分局最劣如实表现);
- **开局简报上下文** :class:`OpeningCtx`(词缀/boss/投资持有集——线分
  词缀/boss/投资分量的输入面,三调用方共用读口)。

终局裁定(全维平分)= COMP_LIBRARY 注册序(:func:`_line_sort_key` 追加
注册序维;候选排序同一全序,禁遍历序)。

锁定写入与连带动作的唯一所有者 = :func:`session_scope.write_line_lock`
(本模块只产判定,不写键——禁绕过 write_line_lock 直写锁定线槽)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_affinity_table import (
    affix_line_score,
)
from sr_od.application.currency_war.kernel.cw_comps import (
    COMP_LIBRARY,
    carry_set,
)
from sr_od.application.currency_war.kernel.cw_invest_channels import (
    env_line_bonus,
    strategy_line_bonus,
)
from sr_od.application.currency_war.kernel.cw_line_scales import (
    CARRY_ANCHOR,
    CARRY_CORE,
    HEAT_PER_POINT,
    PLUGIN_BONUS,
    SKELETON_BONUS,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_game_state import GameState


#: 攻略热度映射常量表(排序立场数据,落策略层;数据源与口径见
#: strategy-docs/12_line_and_intention.md §1.1——十类帖数→20 线类级映射,
#: 长尾八线共享「其他长尾」桶;未登记线取 0 = 缺表 fail 方向)。
#: 量级:每点 +:data:`cw_line_scales.HEAT_PER_POINT`(满热度 274 < 1 插件
#: ——持有实证 > 社区先验)。
LINE_HEAT: dict[str, int] = {
    # —— 十类(类级篇数)——
    '列车同行': 274,        # 姬子列车
    '命运圣杯红A': 118,     # 圣杯双核心
    '双王圣杯': 118,        # 圣杯双核心
    '狼尊欢愉': 68,         # 银狼欢愉
    '黄泉减益': 50,
    '万敌单C': 40,          # 万敌燃血
    '希儿量子': 38,
    '反甲白厄': 38,         # 白厄反甲
    '大黑塔银河学者': 38,   # 大黑塔群攻
    '绯英欢愉': 25,
    'DOT队': 20,            # DOT 卡芙卡
    '专家桑博DOT': 20,      # DOT 卡芙卡(桑博专家变体)
    # —— 其他长尾桶(~40;桶内终局裁定 = 注册序)——
    '千冶减益': 40,
    '巡海击破': 40,
    '龙丹战技点': 40,
    '火花星间旅人': 40,
    '银枝群攻': 40,
    '昼神阿雅': 40,
    '追击飞霄': 40,
    '景元仙舟': 40,
}

#: 线攻略锚核心表(design §2 carry·anchor 档判定:各线攻略锚核心——
#: 「core 首位或攻略明文『到手即开线』者」,从 final_comps 各篇核对;
#: 不确定线取 core_chars[0] 就地注释)。锚 = 单卡即战力档(:data:`CARRY_ANCHOR`
#: +8000/名),其余 core 减半(:data:`CARRY_CORE`)——攻略主次语义。
#: ⚠️ 与 kernel ``carry_anchor``(聚类交叉核对锚)分工:两表绝大多数同值;
#: 已登记分歧 = 火花星间旅人(聚类锚『火花』vs 攻略明文花火主C——评分锚
#: 按攻略重述取花火,分歧登记在 final_comps 交叉核对记录)。
LINE_ANCHOR: dict[str, str] = {
    '列车同行': '姬子·启行',      # S 级真神(V4.4 合集);「核心到手使过渡板保留率翻倍」
    '命运圣杯红A': 'Archer',      # 高倍率九五核心(任务系统产出,到手即接棒)
    '千冶减益': '千冶·刃',        # plaza 聚类 carry(n=29)
    '绯英欢愉': '绯英',
    '希儿量子': '希儿',           # 攻略「希儿到手即开线」(design §2 锚档例)
    '黄泉减益': '黄泉',
    '巡海击破': '波提欧',         # 锚=波提欧簇(12 篇全击破形,本条 plaza 校准注)
    '龙丹战技点': '丹恒·饮月',    # 唯一把点数上限转倍率的卡(龙丹节构造机理)
    '双王圣杯': 'Saber',          # 能量线主C(final_grail_dual B 线)
    '火花星间旅人': '花火',        # 攻略明文花火主C(BV 转录注);core_chars[0] 同值
    '大黑塔银河学者': '大黑塔',   # 52/52 载体C(final_daheita_aoe 构造机理)
    '银枝群攻': '银枝',           # 「必须3星银枝」(77006068 直读)
    '反甲白厄': '白厄',           # 78/78 载体(final_baie_reflect)
    '狼尊欢愉': '银狼LV.999',
    '昼神阿雅': '阿格莱雅',        # 3星 20/21(本条 plaza 校准注)
    '追击飞霄': '飞霄',            # 攻略重述(76883466;聚类代表那刻夏分歧已登记)
    '万敌单C': '万敌',             # 40/40 载体(final_wandi_burn)
    'DOT队': '卡芙卡',
    '景元仙舟': '景元',            # 24/24(final_longtail_others 景元节)
    '专家桑博DOT': '桑博',         # 33k use 帖「专家老桑博」低费引爆器主C
}

#: COMP_LIBRARY 注册序索引(全维平分的终局裁定 = 注册序首线;「显式规则
#: 声明,非遍历序隐式定锁——稳定且可实现」,12 号篇 §1.1)。
_COMP_REG_INDEX: dict[str, int] = {c.name: i for i, c in enumerate(COMP_LIBRARY)}

#: 候选数量(用户立场值;12 号篇 §1.2)。
CANDIDATE_TOP_N: int = 3


@dataclass(frozen=True)
class OpeningCtx:
    """开局简报上下文(design §6 扩参方案:r4/Y4-4——线分词缀/boss/投资
    分量的输入面,从 GameState 现读;调用方构造,签名幂等)。

    - ``enemy_affixes``:开局简报词缀名元组(键空间 = AFFIX_EFFECTS 注册名;
      词缀分/无燃料底线消费);
    - ``plane_bosses``:三位面 boss 名(非 None 项;boss 分批 2 落地,
      批 1 恒 0 分,字段先行承载);
    - ``held_invest``:投资持有名集(active_strategies ∪ active_env)——
      投资环境分 + 投资策略分(通道派生)消费。
    """

    enemy_affixes: tuple[str, ...] = ()
    plane_bosses: tuple[str, ...] = ()
    held_invest: frozenset[str] = frozenset()


def opening_ctx_of(gs: GameState) -> OpeningCtx:
    """开局简报上下文现读(三调用方共用的唯一读口)。

    未观察字段自然为空 = 外部分 0(fail 方向:缺读不虚构)。虚拟评估路径
    (shop 货架资格臂)仅持有面虚拟,词缀/boss/投资面与本读口同源现读。
    """
    affixes = tuple(gs.enemy_affixes.value or ())
    bosses = tuple(b for b in (gs.plane_bosses.value or ()) if b)
    return OpeningCtx(enemy_affixes=affixes, plane_bosses=bosses,
                      held_invest=held_invest_names_of(gs))


def held_chars_of(gs: GameState) -> frozenset[str]:
    """持有角色名集(bench ∪ 场上;锁定判定与持有证据分的持有读面)。

    空名不计(占位件/未识别件不构成持有证据)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_units_of,
        deployed_rows_of,
    )
    front, back = deployed_rows_of(gs)
    names = {u.char_id for u in (*front, *back, *bench_units_of(gs))
             if u is not None and u.char_id}
    return frozenset(names)


def held_invest_names_of(gs: GameState) -> frozenset[str]:
    """已持有投资名集(投资策略名单 ∪ 已选投资环境;投资通道派生的输入面)。"""
    strategies = list(gs.active_strategies.value or ())
    env = gs.active_env.value
    if env:
        strategies.append(env)
    return frozenset(strategies)


@dataclass(frozen=True)
class LineScore:
    """线分数值分解(design §2 单值和的命名分量;``total`` = 各分量和)。

    分量即证据门判据面(:attr:`gate_positive` = env ∨ carry ∨ 骨架 ∨
    插件 > 0,**不含热度**——12 号篇 §1.2「热度不是入选理由」保持)。
    """

    carry: int      # 证据·carry 层(锚 +8000/名 + 其余 core +4000/名)
    skeleton: int   # 证据·骨架层(key_items − carry,+2000/名)
    plugin: int     # 证据·插件层(线成员 − carry − key_items,+500/名)
    heat: int       # 攻略热度(LINE_HEAT × +1/点)
    invest: int     # 投资环境分 + 投资策略分(通道派生,§3.1/§3.2)
    affix: int      # 词缀分(吃怕表 §3.3,含重开级/无燃料底线)
    boss: int       # boss 分(Σ三只克制 §3.4;批 2 boss 面落地前恒 0)

    @property
    def total(self) -> int:
        return (self.carry + self.skeleton + self.plugin + self.heat
                + self.invest + self.affix + self.boss)

    @property
    def gate_positive(self) -> bool:
        """候选入选证据门(§1.2;命名访问,禁切片——分量集显式定义)。"""
        return (self.invest > 0 or self.carry > 0
                or self.skeleton > 0 or self.plugin > 0)


def line_score_breakdown(comp: Comp, held_chars: frozenset[str],
                         opening_ctx: OpeningCtx) -> LineScore:
    """线分数值分解(§1.1 单值和的分量计算;纯函数,同输入同值)。

    证据层逐名一档(锚 > 其余 core > 骨架 > 插件——同名角色跨层不重复
    计分:骨架 = key_items 命中 − carry,插件 = 线成员命中 − carry −
    key_items);invest = 持有名逐个过环境/策略两通道派生(一名只命中
    自家注册表,无双计);boss 分量批 2 前恒 0(design §8 批次划分)。
    """
    anchor = LINE_ANCHOR[comp.name]
    carry = carry_set(comp)
    core_hits = (carry & held_chars) - {anchor}
    skeleton_hits = (set(comp.key_items or ()) & held_chars) - carry
    members = set(comp.core_chars) | set(comp.shared_chars or ())
    plugin_hits = ((members & held_chars) - carry
                   - set(comp.key_items or ()))
    invest = sum(env_line_bonus(name, comp)
                 + strategy_line_bonus(name, comp)
                 for name in opening_ctx.held_invest)
    return LineScore(
        carry=(CARRY_ANCHOR if anchor in held_chars else 0)
              + CARRY_CORE * len(core_hits),
        skeleton=SKELETON_BONUS * len(skeleton_hits),
        plugin=PLUGIN_BONUS * len(plugin_hits),
        heat=HEAT_PER_POINT * LINE_HEAT.get(comp.name, 0),
        invest=invest,
        affix=affix_line_score(comp.name, opening_ctx.enemy_affixes),
        boss=0,
    )


def line_score_key(comp: Comp, held_chars: frozenset[str],
                   opening_ctx: OpeningCtx) -> int:
    """线分数(design §2 单值和;排序消费 = 降序,见 :func:`_line_sort_key`)。"""
    return line_score_breakdown(comp, held_chars, opening_ctx).total


def _line_sort_key(comp: Comp, held_chars: frozenset[str],
                   opening_ctx: OpeningCtx) -> tuple[int, int]:
    """全序排序键(线分数降序 + 注册序终局;候选快照与锁定取首的同一全序)。"""
    return (-line_score_key(comp, held_chars, opening_ctx),
            _COMP_REG_INDEX.get(comp.name, len(COMP_LIBRARY)))


def compute_candidates(held_chars: frozenset[str],
                       opening_ctx: OpeningCtx, *,
                       evidence_gate: bool = False) -> tuple[str, ...]:
    """全 20 线算分取 top N 候选(§1.2:每帧对全部线算分,top3 为候选;
    签名幂等——同持有面重算同值)。返回线名元组(分数降序,注册序终局)。

    ``evidence_gate``(候选快照消费开启版):只收证据门为正的线
    (:attr:`LineScore.gate_positive`)——零证据线不入候选,热度降为
    有证据线间的排序;开局零持有零投资零词缀 = 空候选(合法形态,
    时点兜底空候选分支承接)。**虚拟评估入口**(shop 货架资格臂):
    ``held_chars`` 即证据集,调用方传「在手 ∪ 货架」+ 不开门 = 虚拟
    top3(全量排序,资格器消费排位);词缀/boss/投资面经
    :func:`opening_ctx_of` 同源现读。
    """
    ranked = sorted(COMP_LIBRARY,
                    key=lambda c: _line_sort_key(c, held_chars, opening_ctx))
    if evidence_gate:
        ranked = [c for c in ranked
                  if line_score_breakdown(
                      c, held_chars, opening_ctx).gate_positive]
    return tuple(c.name for c in ranked[:CANDIDATE_TOP_N])


def evaluate_lock(candidates: tuple[str, ...],
                  held_chars: frozenset[str],
                  opening_ctx: OpeningCtx, *,
                  plane2_started: bool,
                  p2_strategy_pick_done: bool) -> str | None:
    """锁定判定(P2 时点兜底唯一路径;返回应终局阵容锁定名,None = 不锁)。

    硬规则/即时锁全退役(design §6):核心在手 = carry 证据分(数值必然性
    替代角色硬锁)、定义卡/强关联投资 = 通道派生加分(替代策略即时锁)——
    拿到什么都不直接锁,分数说话;触发 = ``plane2_started``(窗口谓词,
    首入 (2,*) 段)∧ ``p2_strategy_pick_done``(P2 起首次投资策略三选一
    完成侦测)→ **候选首名**(候选元组已按全序降序)。**空候选兜底分支**
    (§1.3:证据门下空候选可达,兜底为真规则):候选空 → 锁全 20 线全序
    首名(缺省全量版重算取首;零证据帧首名 = 热度首线)。

    锁后只读由调用侧(``session_scope`` 锁定守卫)承载:本函数只在
    未锁定态被求值。
    """
    if not (plane2_started and p2_strategy_pick_done):
        return None
    if candidates:
        return candidates[0]
    return compute_candidates(held_chars, opening_ctx)[0]


def anchor_line_of(gs: GameState, locked_comp: str,
                   demoted_endgame: bool) -> Comp | None:
    """选卡锚点线(design §3.2 选卡侧统一:r4/R4-4 拍板——锁定前帧锚点
    统一 = 候选首名线,P1/P2 同一公式;帧间抖动由签名稳定性钳制)。

    锁定帧(非降格)= 锁定线本体(方向已裁定);未锁/降格帧 = 证据门版
    候选首名现算(纯函数,与 session_scope 候选快照同输入同值);空候选
    (零证据帧)= None——锚缺失帧方向分/克制减分/顶级保护按 0/False
    保守缺省。锁线名不可解析(OCR 漂移)防御位:回落候选首名。三处消费
    同锚 = 顶级保护/选卡方向分/选卡克制减分(invest_strategy/pick_common)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    if locked_comp and not demoted_endgame:
        locked = get_comp(locked_comp)
        if locked is not None:
            return locked
    cands = compute_candidates(held_chars_of(gs), opening_ctx_of(gs),
                               evidence_gate=True)
    return get_comp(cands[0]) if cands else None


def _validate_line_anchor() -> None:
    """锚表构建校验(import 即炸):全 20 线覆盖 + 锚 ∈ 角色注册表
    (手编表写错名 = 锚档静默失效)。"""
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    names = {c.name for c in COMP_LIBRARY}
    if set(LINE_ANCHOR) != names:
        raise ValueError('LINE_ANCHOR 必须恰好覆盖 COMP_LIBRARY 全部线')
    for line, anchor in LINE_ANCHOR.items():
        if anchor not in CHARACTERS:
            raise ValueError(
                f'LINE_ANCHOR 锚不在角色注册表:{line!r}×{anchor!r}')


_validate_line_anchor()
