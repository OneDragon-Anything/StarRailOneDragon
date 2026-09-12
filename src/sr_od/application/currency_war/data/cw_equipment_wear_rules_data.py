"""装备穿戴规则结构化载体(件专属前置 + 类别可穿性门;分配可行性谓词 W2/W3 判据源)。

**与 cw_equipment_data.py 的关系**(18 号稿 §3.1 同构形态,先例 =
affix_wear_semantics_data.py ↔ affix_effects_data.py):``EQUIPMENTS`` = 真值源
(生成器产物,勿手改);本文件 = 独立结构化条目,手工维护、非散文解析、非生成器
产物——结构化字段混入生成器文件会被下次重写冲掉,故独立承载。
``name``/``prose_ref`` = 装备规范名锚,指向 ``EQUIPMENTS`` 同名键(行号随生成器
重写下移不稳定,名锚稳定)。

**对拍义务**:注册表 effect 散文 = 前置措辞真值;本文件结构值 = 带对拍义务的派生
建模。游戏改前置措辞 → ``check_equipment_wear_rule_coverage`` 显警 + 测试仓对拍锁
(test_cw_equip.py 穿戴规则对拍锁)拦截,禁静默沿用。

**消费位**:kernel/cw_comps._wearable_gate_ok(``equip_allocation`` 分配前排除,
P95 支配命题 §2-A W2/W3;命题单篇 =
docs/develop/sr_od/application/currency_war/proofs/p95-allocation-feasibility-dominance.md)。
禁散落硬编码(前置/可穿性建模单一源 = 本文件)。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS

#: 前置类型:「需要空装备栏才能装备」族(注册表 随便骰子/随便骰子·特权 effect
#: 原文,全注册表恰 2 处)。判定读法空间 =「全空 vs ≥2 空槽」(「≥1 空槽」读法
#: 已被实机实证排除:希儿 2 件在身 + 1 空槽拖骰子被拒);两读法定谳前消费端取
#: 最保守「身上有任意件即拒」——两读法下有件均拒,保守缺省无需先行定谳;
#: 定谳义务 = 实机被动采集(区分样本:1 件在身 = 2 空槽被拒 →「全空」;
#: 可穿 →「≥2 空槽」)。
WEAR_PREREQ_EMPTY_SLOTS: str = 'empty_slots_only'


@dataclass(frozen=True)
class EquipmentWearRule:
    """单件装备的结构化穿戴规则(值全部游戏定义,零自由参数)。"""

    name: str
    """装备规范名(= ``EQUIPMENTS`` 键)。"""
    predicate: str
    """穿戴前置类型(现役单一值 = ``WEAR_PREREQ_EMPTY_SLOTS``)。"""
    prose_ref: str
    """名锚 → ``EQUIPMENTS`` 同名键(effect 原文含前置措辞,对拍义务载体)。"""


#: 件专属前置在册条目(首件锚定 = 注册表 随便骰子/随便骰子·特权 两行 effect
#: 原文「需要空装备栏才能装备…」;新件出现由互检显警兜,禁解析散文)。
EQUIP_WEAR_PREREQUISITES: dict[str, EquipmentWearRule] = {
    '随便骰子': EquipmentWearRule(
        name='随便骰子', predicate=WEAR_PREREQ_EMPTY_SLOTS, prose_ref='随便骰子'),
    '随便骰子·特权': EquipmentWearRule(
        name='随便骰子·特权', predicate=WEAR_PREREQ_EMPTY_SLOTS, prose_ref='随便骰子·特权'),
}


#: 类别可穿性门(fail-closed 白名单):类别 → 允许装备该类装备的角色名单
#: (精确规范名)。在册类别之外恒可穿(门只辖本表键 = 开方向;新类别若出现
#: 拒收证据,先过结构批补键再消费,禁散落判断)。
#:
#: 骇客门白名单 = '银狼LV.999'【假说级,禁当已证】。收敛旁证四条:①
#: cw_factions.py「头号玩家」行 =「银狼LV.999 专属:升费/骇客改件」;②注册表
#: 欢愉卡带Max effect 唯一角色特化条款 =【银狼LV.999】装备时;③投资牌「获得
#: 1个随机4费骇客改件」(cw_invest_data);④plaza equip_freq 前 50 零骇客件。
#: 反面直证 = 异阵营普通角色 4/4 拖拽全败(对局档案逐件归因)。真值定谳前
#: fail-closed 保守拒(错杀 = 件滞留 owned 等待;漏放 = 白拖 ~18s/对 + 拉黑
#: 记忆污染 + 永久滞留,前者严格小);定谳义务 = 实机单点拖拽(持有骇客件 +
#: 银狼在场,观测 diff/icon),定谳后按真值收窄——若银狼也不可穿,改「骇客件
#: 不参与 drag 分配,归特殊消费批」。
#:
#: 与 cw_bond_equips 的对账(防第二源分叉):卡带「无条件计数 +1」建模中
#: 「非成员可穿 +1」半边所依赖的分配通道(普通角色 × 卡带)因本门在分配面
#: 关闭——bot 自派面不再放电该形态;银狼LV.999 佩戴卡带的计数路径不受影响;
#: cw_bond_equips 建模本体不动(该口述条目真值候裁归属在册待玩家确认行,
#: 与本门互不替代)。
CATEGORY_WEAR_GATES: dict[str, frozenset[str]] = {
    '骇客': frozenset({'银狼LV.999'}),
}

#: 前置措辞检测关键词(取窄防噪声:「需要空装备栏」完整短语)。
_COVERAGE_KEYWORD: str = '需要空装备栏'


def check_equipment_wear_rule_coverage() -> list[str]:
    """装备注册表 ↔ 结构化载体互检(纯函数;返回警告文案列表,空 = 无缺口)。

    三个方向的显警(显警不拦截,消费点 = ``equip_allocation`` 每次调用头部
    评估一次;量级 = 注册表件数,零性能顾虑):
    - 正向:effect 命中前置关键词 ∧ 无同名结构条目 → 疑似新件漏建模;
    - 反向:结构条目在注册表无同名行 → 孤儿条目(注册表重写后改名/删除);
    - 措辞对拍:结构条目锚定的 effect 不再含关键词 → 前置措辞漂移,
      须对拍后更新结构值。
    """
    warnings: list[str] = []
    for name, eq in EQUIPMENTS.items():
        if name in EQUIP_WEAR_PREREQUISITES:
            continue
        if _COVERAGE_KEYWORD in (eq.effect or ''):
            warnings.append(
                f'装备[{name}]effect 命中「{_COVERAGE_KEYWORD}」但无结构化前置条目'
                f'(疑似漏建模): {eq.effect}')
    for name, entry in EQUIP_WEAR_PREREQUISITES.items():
        eq = EQUIPMENTS.get(name)
        if eq is None:
            warnings.append(f'结构化前置条目[{name}]在装备注册表无同名行(孤儿条目)')
            continue
        if _COVERAGE_KEYWORD not in (eq.effect or ''):
            warnings.append(
                f'结构化前置条目[{name}]的散文锚已失效(effect 不再含'
                f'「{_COVERAGE_KEYWORD}」,前置措辞漂移,须对拍后更新)')
        if entry.prose_ref != name:
            warnings.append(f'结构化前置条目[{name}]名锚错位(prose_ref={entry.prose_ref})')
    return warnings
