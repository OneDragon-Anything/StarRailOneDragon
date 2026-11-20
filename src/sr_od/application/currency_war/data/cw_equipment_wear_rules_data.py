"""装备穿戴规则结构化载体(件专属前置 + 件级/类别可穿性门;分配可行性谓词判据源)。

**与 cw_equipment_data.py 的关系**(先例 =
affix_wear_semantics_data.py ↔ affix_effects_data.py):``EQUIPMENTS`` = 真值源
(生成器产物,勿手改);本文件 = 独立结构化条目,手工维护、非散文解析、非生成器
产物——结构化字段混入生成器文件会被下次重写冲掉,故独立承载。
``name``/``prose_ref`` = 装备规范名基准,指向 ``EQUIPMENTS`` 同名键(行号随生成器
重写下移不稳定,名基准稳定)。

**交叉核对义务**:注册表 effect 散文 = 前置措辞真值;本文件结构值 = 带交叉核对义务的派生
建模。游戏改前置措辞 → ``check_equipment_wear_rule_coverage`` 显警 + 测试仓交叉核对锁
(test_equip.py 穿戴规则交叉核对锁)拦截,禁静默沿用。

**v4.7 换赛季形态(门侧清空/前置保留)**:官方注册表单源重灌(105 官方 + 11
派生简易)后,门侧三常量清空——银狼专属 10 件、「骇客」类别键、白名单两角色
全部不在 v4.7 官方名单,防误拖保护对象消失(不存在误拖场景,保护缺位影响
趋零)。前置表保留:「随便骰子」(id 35030404,进阶装备)与「随便骰子·特权」
(id 35040404,特权装备)在库,effect 均含「需要空装备栏」,骰子防线继续
有效。互检函数骨架完整保留:正向向继续为新件漏建模兜底(新注册表 effect
命中关键词且无条目即显警),门孤儿向随空表自然归零。
**门重建条件(三常量回填前提)**:实机/实战数据工程——新赛季专属件清单
(拖拽静默拒逐件取证)+ 可穿性白名单口述/实证,拿到取证后按旧形态回填;
回填前禁凭旧赛季记忆直接复原(对象名单已换血,旧门键对本季恒放行或恒拒
皆错)。事件卡文装备识别锚(cw_events ``_PLANNER_EQUIP_ANCHORS``)以门键集
为源,随门重建自动恢复。

**消费位**:kernel/cw_comps._wearable_gate_ok(``equip_allocation`` 分配前排除)。
禁散落硬编码(前置/可穿性建模单一源 = 本文件)。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.data.cw_equipment_data import EQUIPMENTS

#: 前置类型:「需要空装备栏才能装备」族(注册表 随便骰子/随便骰子·特权 effect
#: 原文,v4.7 注册表恰 2 处)。判定读法空间 =「全空 vs ≥2 空槽」(「≥1 空槽」读法
#: 已被实机实证排除:2 件在身 + 1 空槽拖骰子被拒);两读法已定案前消费端取
#: 最保守「身上有任意件即拒」——两读法下有件均拒,保守缺省无需先行定案;
#: 已定案义务 = 实机被动采集(区分样本:1 件在身 = 2 空槽被拒 →「全空」;
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
    """名字作对拍键 → ``EQUIPMENTS`` 同名键(effect 原文含前置措辞,对拍义务载体)。"""


#: 件专属前置已登记条目(首件锚定 = 注册表 随便骰子/随便骰子·特权 两行 effect
#: 原文「需要空装备栏才能装备…」;新件出现由互检显警兜,禁解析散文)。
EQUIP_WEAR_PREREQUISITES: dict[str, EquipmentWearRule] = {
    '随便骰子': EquipmentWearRule(
        name='随便骰子', predicate=WEAR_PREREQ_EMPTY_SLOTS, prose_ref='随便骰子'),
    '随便骰子·特权': EquipmentWearRule(
        name='随便骰子·特权', predicate=WEAR_PREREQ_EMPTY_SLOTS, prose_ref='随便骰子·特权'),
}

#: 银狼专属白名单(件级门/类别门共用单一源;v4.7 换赛季清空:银狼/
#: 银狼LV.999 均不在 v4.7 角色名单,白名单随门侧清空。旧定案「银狼专属
#: 装备两个都行」的两角色口径在门重建取证后随本表回填;空 frozenset =
#: 门判据恒放行)。
YINLANG_WEAR_ALLOWLIST: frozenset[str] = frozenset()

#: 件级可穿性门(fail-closed 白名单):装备规范名 → 允许装备该件的角色名单
#: (精确规范名)。已登记条目之外恒可穿(门只辖本表键 = 开方向;新类别若
#: 出现拒收证据,先取证回填再消费,禁散落判断)。
#:
#: v4.7 换赛季清空:旧 10 件银狼专属装备(分身墨镜族/数据拷贝仪族/病毒
#: 防火墙族/破解芯片/管理员手套ProMax/欢愉卡带Max)全部不在官方名单,
#: 防误拖保护对象消失。为何件级而非类别级(重建时沿用):专属限制不在
#: 注册表 effect 散文里(游戏文本未写明),证据 = 口述 + 实机拖拽取证,
#: 类别粒度罩不住,必须逐件登记;条目对本表孤儿向的互检义务见
#: ``check_equipment_wear_rule_coverage``(限制本身豁免散文措辞核对)。
ITEM_WEAR_GATES: dict[str, frozenset[str]] = {}

#: 类别可穿性门(fail-closed 白名单):类别 → 允许装备该类装备的角色名单
#: (精确规范名)。已登记类别之外恒可穿(门只覆盖本表键 = 开方向)。
#:
#: v4.7 换赛季清空:旧键「骇客」不在官方 7 类(进阶装备/特权装备/星徽/
#: 餐品改件/列车改件/宝钻/固有装备),消费面查旧类名恒空集、静默失效。
#: 重建条件 = 实机确认 v4.7 新类别的可穿性限制(餐品改件/列车改件能否
#: 穿角色等语义挂账实机确认)后按旧形态回填。
CATEGORY_WEAR_GATES: dict[str, frozenset[str]] = {}

#: 前置措辞检测关键词(取窄防噪声:「需要空装备栏」完整短语)。
_COVERAGE_KEYWORD: str = '需要空装备栏'


def check_equipment_wear_rule_coverage() -> list[str]:
    """装备注册表 ↔ 结构化载体互检(纯函数;返回警告文案列表,空 = 无缺口)。

    四个方向的显警(显警不拦截,消费点 = ``equip_allocation`` 每次调用头部
    评估一次;量级 = 注册表件数,零性能顾虑):
    - 正向:effect 命中前置关键词 ∧ 无同名结构条目 → 疑似新件漏建模;
    - 反向:前置条目在注册表无同名行 → 孤儿条目(注册表重写后改名/删除);
    - 措辞交叉核对:前置条目锚定的 effect 不再含关键词 → 前置措辞漂移,
      须交叉核对后更新结构值;
    - 门孤儿(件级/类别门):白名单条目在注册表无同名行,或白名单角色名
      不在 ``cw_dropped_names.GUARD_CHARACTER_ROSTER`` → 注册表/角色表重写
      改名后条目静默失效(错字角色进白名单 = 该角色恒被拒;专属件被改名
      = 门对旧名恒放行、新名恒拒)。件级门的散文措辞交叉核对**豁免**
      (限制不在游戏文本,见 ``ITEM_WEAR_GATES`` 注释),孤儿向是它唯一的
      互检义务。
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
                f'结构化前置条目[{name}]的散文参照键已失效(effect 不再含'
                f'「{_COVERAGE_KEYWORD}」,前置措辞漂移,须对拍后更新)')
        if entry.prose_ref != name:
            warnings.append(f'结构化前置条目[{name}]名参照键错位(prose_ref={entry.prose_ref})')
    from sr_od.application.currency_war.data.cw_dropped_names import (
        GUARD_CHARACTER_ROSTER,
    )
    for name in ITEM_WEAR_GATES:
        if name not in EQUIPMENTS:
            warnings.append(f'件级穿戴门条目[{name}]在装备注册表无同名行(孤儿条目)')
    _gate_chars: set[str] = set()
    for _gate in ITEM_WEAR_GATES.values():
        _gate_chars.update(_gate)
    for _gate in CATEGORY_WEAR_GATES.values():
        _gate_chars.update(_gate)
    for _char in sorted(_gate_chars):
        if _char not in GUARD_CHARACTER_ROSTER:
            warnings.append(f'可穿性门白名单角色[{_char}]不在角色注册表(错字或改名)')
    return warnings
