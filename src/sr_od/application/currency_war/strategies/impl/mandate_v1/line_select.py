"""终局线选择内核(统一阵容评分,正本 = 12 号稿)。

判据唯一源 = strategy-docs/12_line_and_intention.md §1(统一阵容评分:
**纯加权和,一个公式** + 数量级表——四轮对抗审查定稿,特殊处理全退役,
排除 = 极大减分非布尔特判)。本模块承载:

- **线分数值化**(§1.1 单值和;数量级常数单一源 =
  :mod:`kernel/cw_line_scales`,本模块零裸数字)+ top3 候选;
- **候选入选证据门**(§1.2:线分量 env ∨ carry ∨ 插件 > 0——
  **不含热度**,热度只作有证据线间的排序,不是入选理由);
- **锁定 = P2 时点兜底唯一路径**(12 号稿 §1.3:硬规则查表/角色硬锁/
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

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_affinity_table import (
    affix_line_score,
    boss_line_score,
    strong_enemy_score,
)
from sr_od.application.currency_war.kernel.cw_comps import (
    COMP_LIBRARY,
    carry_anchor,
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
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_game_state import GameState


#: 攻略热度映射常量表(排序立场数据,落策略层;数据源与口径见
#: strategy-docs/12_line_and_intention.md §1.1——十类帖数→21 线类级映射,
#: 长尾八线共享「其他长尾」桶;未登记线取 0 = 缺表 fail 方向)。
#: 量级:每点 +:data:`cw_line_scales.HEAT_PER_POINT`(满热度 274 < 1 插件
#: ——持有实证 > 社区先验)。
LINE_HEAT: dict[str, int] = {
    # —— 十类(类级篇数)——
    '列车同行·反震': 165,    # 姬子列车 A 反震(底稿 ~60%×274;批 3 拆分)
    '列车同行·直伤': 70,     # 姬子列车 B 输出(底稿 ~25%×274;批 3 拆分)
    # 特化 ~15%(≈39 篇,final_jizi C 节八变体)不拆挂——按特化形态主输出
    # 结算方向归入声明(示意归属,版本重跑校准基准,不进 A/B 热度值):
    # 战技点7永动→B(直伤系)/圣杯4→B(姬子保底过渡=输出核心,final_grail
    # 「姬子保底过渡→双核心」)/欢愉5→B(开拓者绑定堆前台强度,final_yinlang
    # 「前台强度轻松5000+」)/追击转→B(追击=附加攻击直伤)/直伤星期日→B
    # (形态名明示)/仙舟8→B(召唤叠段直伤,无反震记载)/双姬子→B(输出
    # 复用形态)/白厄混血→A(反震系;「姬子后台+白厄带队反震」外部线索归
    # final_baie_reflect 篇)。对账:165+70+39=274(底稿姬子类全量)。
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

#: COMP_LIBRARY 注册序索引(全维平分的终局裁定 = 注册序首线;「显式规则
#: 声明,非遍历序隐式定锁——稳定且可实现」,12 号篇 §1.1)。
_COMP_REG_INDEX: dict[str, int] = {c.name: i for i, c in enumerate(COMP_LIBRARY)}

#: 候选数量(用户立场值;12 号篇 §1.2)。
CANDIDATE_TOP_N: int = 3


@dataclass(frozen=True)
class OpeningCtx:
    """开局简报上下文(line_score_key 扩参 opening_ctx,12 号稿 §1.1——线分词缀/boss/投资
    分量的输入面,从 GameState 现读;调用方构造,签名幂等)。

    - ``enemy_affixes``:开局简报词缀名元组(键空间 = AFFIX_EFFECTS 注册名
      + 独立强敌键「红绿灯」——词缀读链对未注册名透传,强敌表经词缀行
      通道消费;词缀分/无燃料底线消费);
    - ``plane_bosses``:三位面 boss 名(非 None 项;boss 分 = Σ三只克制,
      均权——位面真值 CollectPlaneIntel 后逐位面的权重精细档先均权);
    - ``held_invest``:投资持有名集(active_strategies ∪ active_env)——
      投资环境分 + 投资策略分(通道派生)+ 扑满强敌可见通道(持有扑满
      环境 = 经济环境产物开局可见)消费;
    - ``held_equips``:装备持有多重集(批 3:装备证据分量输入面)——
      key_equips 逐件持有证据(A/B 拆分线的分化面,12 号稿 §1.1「B 唯一
      分化面 = 装备证据」)。
    """

    enemy_affixes: tuple[str, ...] = ()
    plane_bosses: tuple[str, ...] = ()
    held_invest: frozenset[str] = frozenset()
    held_equips: tuple[str, ...] = ()


def opening_ctx_of(gs: GameState) -> OpeningCtx:
    """开局简报上下文现读(三调用方共用的唯一读口)。

    未观察字段自然为空 = 外部分 0(fail 方向:缺读不虚构)。虚拟评估路径
    (shop 货架资格臂)仅持有面虚拟,词缀/boss/投资面与本读口同源现读。
    """
    affixes = tuple(gs.enemy_affixes.value or ())
    bosses = tuple(b for b in (gs.plane_bosses.value or ()) if b)
    equips = tuple(gs.equips.value or ())
    return OpeningCtx(enemy_affixes=affixes, plane_bosses=bosses,
                      held_invest=held_invest_names_of(gs),
                      held_equips=equips)


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
    """线分数值分解(12 号稿 §1.1 单值和的命名分量;``total`` = 各分量和)。

    分量即证据门判据面(:attr:`gate_positive` = env ∨ carry ∨
    插件 > 0,**不含热度/装备**——12 号篇 §1.2「热度不是入选理由」保持;
    装备证据只排序不点亮:纯装备零角色帧「线未点亮」语义保持,买到装备
    ≠ 能上人)。
    """

    carry: int      # 证据·carry 层(基准 +8000/名 + 其余 core +4000/名)
    plugin: int     # 证据·插件层(线成员 − carry,+500/名)
    equip: int      # 证据·装备层(key_equips 逐件持有,+500/件=插件档;批 3)
    heat: int       # 攻略热度(LINE_HEAT × +1/点)
    invest: int     # 投资环境分 + 投资策略分(通道派生,§3.1/§3.2)
    affix: int      # 词缀分(吃怕表 §3.3,含重开级/无燃料底线/兜底泛化)
    boss: int       # 敌情克制分(§3.4:Σ三只 boss + 非 boss 强敌——红绿灯/扑满)

    @property
    def total(self) -> int:
        return (self.carry + self.plugin + self.equip
                + self.heat + self.invest + self.affix + self.boss)

    @property
    def gate_positive(self) -> bool:
        """候选入选证据门(§1.2;命名访问,禁切片——分量集显式定义)。"""
        return (self.invest > 0 or self.carry > 0
                or self.plugin > 0)


def equip_evidence_bonus(comp: Comp,
                         held_equips: tuple[str, ...]) -> int:
    """装备证据分量(12 号稿 §1.1 姬子 A/B 拆分批;「B 唯一分化面 = 装备证据」的线分
    承载):线 ``key_equips`` 逐件持有,每件 :data:`PLUGIN_BONUS`
    (插件档复用——同为「线构成件的持有实证」,与角色插件层同族,
    零新常数);多重集计数(key_equips 重复件按重复计,如以牙还牙甲×2)。

    拆分线分化语义:A/B key_equips 无交集(甲族+外骨骼 vs 风暴潮+电锯+
    冷笑话)→ 专属装备在手即该线证据上升、姊妹线不动。
    """
    held = Counter(held_equips)
    return PLUGIN_BONUS * sum(min(held.get(name, 0), need)
                              for name, need
                              in Counter(comp.key_equips or []).items())


def line_score_breakdown(comp: Comp, held_chars: frozenset[str],
                         opening_ctx: OpeningCtx) -> LineScore:
    """线分数值分解(§1.1 单值和的分量计算;纯函数,同输入同值)。

    证据层逐名一档(基准 > 其余 core > 插件 > 装备件——同名角色跨层
    不重复计分:插件 = 线成员命中 − carry;装备 = key_equips 逐件持有);invest = 持有名逐个过环境/策略
    两通道派生(一名只命中自家注册表,无双计);boss = Σ三只克制 + 非
    boss 强敌(§3.4——红绿灯经词缀行通道/扑满经投资持有通道)。
    """
    anchor = carry_anchor(comp)
    carry = carry_set(comp)
    core_hits = (carry & held_chars) - {anchor}
    members = set(comp.members)
    plugin_hits = (members & held_chars) - carry
    invest = sum(env_line_bonus(name, comp)
                 + strategy_line_bonus(name, comp)
                 for name in opening_ctx.held_invest)
    return LineScore(
        carry=(CARRY_ANCHOR if anchor in held_chars else 0)
              + CARRY_CORE * len(core_hits),
        plugin=PLUGIN_BONUS * len(plugin_hits),
        equip=equip_evidence_bonus(comp, opening_ctx.held_equips),
        heat=HEAT_PER_POINT * LINE_HEAT.get(comp.name, 0),
        invest=invest,
        affix=affix_line_score(comp.name, opening_ctx.enemy_affixes),
        boss=boss_line_score(comp.name, opening_ctx.plane_bosses)
             + strong_enemy_score(comp.name, opening_ctx.enemy_affixes,
                                  opening_ctx.held_invest),
    )


def line_score_key(comp: Comp, held_chars: frozenset[str],
                   opening_ctx: OpeningCtx) -> int:
    """线分数(12 号稿 §1.1 单值和;排序消费 = 降序,见 :func:`_line_sort_key`)。"""
    return line_score_breakdown(comp, held_chars, opening_ctx).total


def _line_sort_key(comp: Comp, held_chars: frozenset[str],
                   opening_ctx: OpeningCtx) -> tuple[int, int]:
    """全序排序键(线分数降序 + 注册序终局;候选快照与锁定取首的同一全序)。"""
    return (-line_score_key(comp, held_chars, opening_ctx),
            _COMP_REG_INDEX.get(comp.name, len(COMP_LIBRARY)))


def compute_candidates(held_chars: frozenset[str],
                       opening_ctx: OpeningCtx, *,
                       evidence_gate: bool = False) -> tuple[str, ...]:
    """全 21 线算分取 top N 候选(§1.2:每帧对全部线算分,top3 为候选;
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

    硬规则/即时锁全退役(12 号稿 §1.3):核心在手 = carry 证据分(数值必然性
    替代角色硬锁)、定义卡/强关联投资 = 通道派生加分(替代策略即时锁)——
    拿到什么都不直接锁,分数说话;触发 = ``plane2_started``(窗口谓词,
    首入 (2,*) 段)∧ ``p2_strategy_pick_done``(P2 起首次投资策略三选一
    完成侦测)→ **候选首名**(候选元组已按全序降序)。**空候选兜底分支**
    (§1.3:证据门下空候选可达,兜底为真规则):候选空 → 锁全 21 线全序
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
    """选卡基准线(选卡侧统一,29 号稿 §2.2——锁定前帧基准
    统一 = 候选首名线,P1/P2 同一公式;帧间抖动由签名稳定性钳制)。

    锁定帧(非降格)= 锁定线本体(方向已裁定);未锁/降格帧 = 证据门版
    候选首名现算(纯函数,与 session_scope 候选快照同输入同值);空候选
    (零证据帧)= None——基准缺失帧方向分/克制减分/顶级保护按 0/False
    保守缺省。锁线名不可解析(OCR 漂移)防御位:回落候选首名。三处消费
    同基准 = 顶级保护/选卡方向分/选卡克制减分(invest_strategy/pick_common)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    if locked_comp and not demoted_endgame:
        locked = get_comp(locked_comp)
        if locked is not None:
            return locked
    cands = compute_candidates(held_chars_of(gs), opening_ctx_of(gs),
                               evidence_gate=True)
    return get_comp(cands[0]) if cands else None


# (旧评分定义件分歧登记表 _LINE_ANCHOR_DIVERGENCE 与 rating_anchor 读口已随
#  plaza_carry 退役整段删除:评分定义件 = carry_anchor = core_chars[0] 单源
#  ——火花星间旅人线分歧随主C 裁定收尾,沿革见 plaza-carry-retirement。)
