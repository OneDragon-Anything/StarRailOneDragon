"""敌人词缀「穿戴条件谓词」结构化载体(18 号稿 §3.1;派生缓存,带对拍义务)。

**与 affix_effects_data.py 互不触碰**(18 号稿 §3.1):散文注册表由运行时采集
批整文件重写(ADR-0081 修法形态),结构化条目混入其中会被下次重写冲掉——
散文文件只随采集批更新,本文件只随结构批/对拍批更新。

真值与缓存的关系:散文注册表(``affix_effects_data.AFFIX_EFFECTS``)= 真值源;
本文件结构值 = 带对拍义务的派生缓存。``prose_ref`` = 词缀名锚,指向散文
注册表同名词缀键(散文行号随整文件重写下移不稳定,名锚稳定)。游戏改罚值
时散文更新而本缓存 divergent → 首次消费对拍锁(本批 =
sr-od-test/test_cw_equip_wear_semantics_18.py 的对拍锁)与 D-81 守卫拦截,
禁止静默沿用旧值;对拍为采集批常设项。

在册词缀集判定规则(消费侧,18 号稿 §3.1):结构化条目存在 ∧
``wear_predicate`` 非空 ∧ ``penalty_side == 'output'`` 才进词缀条件优先层
——缺结构化条目的散文词缀不进(防解析散文)。

邻接排除族(18 号稿 §3.1 点名,谓词与「穿戴件数」同族但本体非穿戴,
显式排除防检测面一般形误扫,见 ``EXCLUDED_ADJACENT_AFFIXES``):
- 挫其锋芒(谓词 = 伤害减免属性未达阈,减益面);
- 形单影只(谓词 = 未激活羁绊数;现建模只含「免罚」半边,ADR-0500)。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.data.affix_effects_data import AFFIX_EFFECTS


@dataclass(frozen=True)
class AffixWearSemantics:
    """单条词缀的结构化穿戴语义(值全部游戏定义,零自由参数)。"""

    name: str
    """词缀名(= 散文注册表 ``AFFIX_EFFECTS`` 的键)。"""
    wear_predicate: tuple[str, int] | None
    """穿戴条件谓词:(谓词类型, N)。现役类型单一值:
    ``min_worn_per_char`` = 每个角色至少穿 N 件装备,否则吃罚(软弱无力
    「没有穿戴3件装备的角色…伤害为80%」→ ('min_worn_per_char', 3))。
    None = 无穿戴件数谓词(如额外打击按空栏结算,不构成本层谓词)。"""
    penalty_side: str
    """罚则方向:'output' 输出侧(伤害衰减)| 'damage_taken' 承伤侧。
    承伤侧族不入分配优先层(18 号稿 §3.2 分叉声明:承伤罚只与总空槽数
    相关,与分配集中度无关)。"""
    penalty_value: float
    """罚值(游戏定义):输出侧 = 罚后伤害乘数(0.8 = 伤害×80%);
    承伤侧 = 单位罚值(0.08 = 每空栏额外 8% 真实伤害)。"""
    prose_ref: str
    """词缀名锚 → 散文注册表同名词缀键(对拍义务载体;行号不稳故用名锚)。"""


WEAR_AFFIX_SEMANTICS: dict[str, AffixWearSemantics] = {
    '软弱无力': AffixWearSemantics(
        name='软弱无力',
        wear_predicate=('min_worn_per_char', 3),
        penalty_side='output',
        penalty_value=0.8,
        prose_ref='软弱无力',
    ),
    '额外打击': AffixWearSemantics(
        name='额外打击',
        wear_predicate=None,
        penalty_side='damage_taken',
        penalty_value=0.08,
        prose_ref='额外打击',
    ),
}

#: 检测面排除表(邻接/异域条目:关键词会命中但**不进本层**,显式点名
#: 防一般形误扫;每条带排除理由,新排除须先过结构批)。
EXCLUDED_ADJACENT_AFFIXES: dict[str, str] = {
    '挫其锋芒': '谓词=伤害减免属性阈,减益面(18 号稿 §3.1 点名排除族)',
    '形单影只': '谓词=未激活羁绊数,羁绊面(18 号稿 §3.1 点名排除族;ADR-0500)',
    '高费审美': '谓词=角色费用档,伤害衰减但非穿戴条件',
    '低费审美': '谓词=角色费用档,伤害衰减但非穿戴条件',
    '以人为本': '无条件全队效果(羁绊/投资策略基础伤害衰减),非穿戴条件',
    '库藏生锈': '走 §2.1 row4 豁免行专属判据(registry RUST_AFFIX_NAME),非本层谓词载体',
}

#: 检测面关键词族(18 号稿 §3.1「互检显警」):散文命中穿戴/伤害衰减类
#: 关键词但无同名结构条目 → 显警。'件装备' 取窄于裸「件」防噪声。
_COVERAGE_KEYWORDS: tuple[str, ...] = ('穿戴', '件装备', '伤害变为')


def check_wear_semantics_coverage() -> list[str]:
    """散文注册表 ↔ 结构化载体互检(18 号稿 §3.1 检测面;纯函数)。

    两个方向的显警(返回警告文案列表,空 = 无缺口):
    - 正向:散文命中关键词族 ∧ 无同名结构条目 ∧ 不在排除表 → 疑似新词缀
      漏建模(显警留证,不静默);
    - 反向:结构条目在散文中无同名行 → 孤儿缓存(散文重写后词缀更名/删除)。

    值差异不在此拦截(散文不可靠机读)——走首次消费对拍锁(测试)与
    D-81 守卫(采集批 divergent 拦截)。消费点 = 词缀优先层求序入口
    (kernel/cw_equip_env.resolve_affix_priority_order),每次求序前跑一遍
    (dict 扫描,量级 = 词缀总数,零性能顾虑)。
    """
    warnings: list[str] = []
    for name, prose in AFFIX_EFFECTS.items():
        if name in WEAR_AFFIX_SEMANTICS or name in EXCLUDED_ADJACENT_AFFIXES:
            continue
        if any(k in prose for k in _COVERAGE_KEYWORDS):
            warnings.append(
                f'词缀[{name}]散文命中穿戴/伤害衰减关键词但无结构条目'
                f'(疑似漏建模,非排除表在册): {prose}')
    for name in WEAR_AFFIX_SEMANTICS:
        if name not in AFFIX_EFFECTS:
            warnings.append(f'结构条目[{name}]在散文注册表无同名行(孤儿缓存)')
    return warnings
