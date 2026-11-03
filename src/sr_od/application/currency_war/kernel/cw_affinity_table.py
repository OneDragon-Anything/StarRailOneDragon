"""货币战争 词缀吃怕表注册表(逐线 × 词缀;design §3.3/§4)。

结构 = ``{线名: {词缀注册名: AffixStance}}``;键名空间 =
data/affix_effects_data 的 ``AFFIX_EFFECTS`` 注册名(52 词缀,运行时采集
入库的官方名)。俗称键(怪物提速/满愿)不入表——俗称→注册名映射归批 2
(design §3.3「俗称建映射,未采集词条待实机采集归位」)。

批次划分(design §8):批 1 = 注册表结构 + 万敌行直入(燃料集依赖方,
r4/Y4-3 非临时占位,消两形态漂移窗);其余 11 已审线 + 长尾 8 线的行、
未登记词缀默认兜底层(方向保守:只给怕不给吃)归批 2 扩行。

同词缀方向逐线相反是本表存在理由(design §1 第 4 条「词缀吃怕是阵容
特定知识」):正当防卫对万敌 +900/对姬子 A·B −150(批 3)/其余怕(批 2)。

万敌无燃料底线(design §4 a 类·独例):开局词缀 ∩ 燃料集 = 空 →
:data:`cw_line_scales.RESTART_PENALTY`(与重开级同档);燃料集 =
本表万敌行**正值**词缀名的投影(吃怕表为源,投影派生单一源)。
「反伤类」= 正当防卫族同义(design §4 表注:当前无独立注册名)。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.data.affix_effects_data import (
    AFFIX_EFFECTS,
)
from sr_od.application.currency_war.kernel.cw_line_scales import (
    AFFIX_STRONG_FUEL,
    AFFIX_STRONG_TOP,
    FEAR_PENALTY,
    RESTART_PENALTY,
)


@dataclass(frozen=True)
class AffixStance:
    """单线单词缀吃怕立场(吃=正/怕=负/重开级=极大负)。

    - ``score``:主阶段(成型常态)分值,现行帧消费值;
    - ``stage_overrides``:双面词条的阶段条件覆写((阶段名, 分值) 序列)。
      批 1 只建结构不生效:万敌×灼热轰炸是当前唯一双面词条(低血期怕
      −150/成型后吃 +750,design §3.3),血线阶段判定输入面未建,低血期
      覆写以登记形态声明,批 2 词缀面接入时挂消费;
    - ``note``:分值依据(攻略篇/设计节号)——手编数据的防漂移锚。
    """

    score: int
    stage_overrides: tuple[tuple[str, int], ...] = ()
    note: str = ''


#: 吃怕表本体(批 1 = 万敌行;批 2 扩 12 已审线 + 长尾 8 线)。
#: 万敌行数据源 = docs/game/currency_war/research/final_comps/
#: final_wandi_burn.md(debuff=buff 典型:反伤/AoE/持续伤害利燃血)+
#: design §4 万敌行直入清单。
AFFINITY_TABLE: dict[str, dict[str, AffixStance]] = {
    '万敌单C': {
        # 强吃·顶级:正当防卫(反伤)——「反伤类」族同义注释:当前
        # AFFIX_EFFECTS 无独立「反伤」注册名,族指即正当防卫本名。
        '正当防卫': AffixStance(
            score=AFFIX_STRONG_TOP,
            note='final_wandi_burn 反伤利燃血(debuff=buff 典型);design §2 词缀强吃·顶级档'),
        # 强吃·燃料族:受击/挨打触发类词缀=燃血层的直接燃料。
        '忍无可忍': AffixStance(
            score=AFFIX_STRONG_FUEL,
            note='final_wandi_burn 敌多动旺=受击驱动叠层燃料;design §2 词缀强吃·燃料档'),
        '应激反应': AffixStance(
            score=AFFIX_STRONG_FUEL,
            note='受击触发类=燃血燃料(design §4 万敌行直入清单)'),
        '灼热轰炸': AffixStance(
            score=AFFIX_STRONG_FUEL,
            stage_overrides=(('低血期', FEAR_PENALTY),),
            note='双面词条:成型后吃 +750/低血期怕 −150(design §3.3);低血期覆写待血线判定输入面(批 2)'),
        '一鼓作气': AffixStance(
            score=AFFIX_STRONG_FUEL,
            note='敌方行动增益=受击频率增益=燃血燃料(design §4 万敌行直入清单)'),
        # 重开级:掉血削上限对燃血是双损(掉血→减上限),机制反例 counter
        # (kernel MECHANIC_COUNTERS「掉血削上限→克燃血」同源)。
        '永久创伤': AffixStance(
            score=RESTART_PENALTY,
            note='final_wandi_burn「不可玩」;design §2 重开级(排除=极大减分)'),
        # (已登记强吃线的未登记词条记 0 不罚——design §3.3;批 2 扩行时补)
    },
}

#: 无燃料底线登记线(design §4 a 类:词缀依赖独例 = 万敌;开局词缀 ∩
#: 燃料集 = 空 → 重开级)。批 2 词缀全表落地时若出现第二条依赖线,在此
#: 扩名即可——燃料集恒按「该线吃怕表行正值投影」现算,无第二份名单。
FUEL_BOTTOM_LINES: frozenset[str] = frozenset({'万敌单C'})


def affix_row_of(line_name: str) -> dict[str, AffixStance]:
    """线吃怕行读口(未登记线 → 空表 = 词缀分恒 0,批 2 扩行前的形态)。"""
    return AFFINITY_TABLE.get(line_name, {})


def fuel_set_of(line_name: str) -> frozenset[str]:
    """线燃料集 = 吃怕表该行**正值**词缀名投影(design §4:吃怕表为源,
    投影派生单一源——禁手抄第二份名单;行登记变动燃料集自动跟随)。"""
    return frozenset(
        affix for affix, stance in affix_row_of(line_name).items()
        if stance.score > 0)


def affix_line_score(line_name: str, enemy_affixes: tuple[str, ...]) -> int:
    """线词缀分(design §2 公式的词缀分量;线分引擎消费)。

    = Σ 本线吃怕表[开局词缀] 主阶段分值 + 无燃料底线(登记线 ∧ 开局词缀 ∩
    燃料集 = 空 → 重开级)。未登记词缀记 0(design §3.3「已登记强吃线的
    未登记词条记 0 不罚」);阶段覆写批 1 不生效(结构已建,见 AffixStance)。
    """
    row = affix_row_of(line_name)
    total = sum(row[a].score for a in enemy_affixes if a in row)
    if line_name in FUEL_BOTTOM_LINES:
        fuel = fuel_set_of(line_name)
        if fuel and not (fuel & set(enemy_affixes)):
            total += RESTART_PENALTY
    return total


def _validate_affinity_table() -> None:
    """构建校验(import 即炸):词缀键必须在 AFFIX_EFFECTS 注册名空间
    (手编表写错名 = 分值静默失效);线名必须在 COMP_LIBRARY(同理)。"""
    from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
    line_names = {c.name for c in COMP_LIBRARY}
    for line, row in AFFINITY_TABLE.items():
        if line not in line_names:
            raise ValueError(f'吃怕表孤儿线名(COMP_LIBRARY 无此线):{line!r}')
        for affix in row:
            if affix not in AFFIX_EFFECTS:
                raise ValueError(
                    f'吃怕表词缀键不在 AFFIX_EFFECTS 注册名空间:'
                    f'{line!r}×{affix!r}')


_validate_affinity_table()
