"""货币战争 装备合成图谱(2 件基础件 → 1 件进阶;meta 层,V4.4)。

**单一源 = ``cw_equipment_data.EQUIPMENTS[].recipes``(官方 API compose_list 采集生成)**。
本模块的全部配方常量在 import 时从注册表派生——recipes 改了(版本更新重拉
``tools/cw/plaza_fetch.py`` → ``tools/cw/gen_equip_registry.py``)本图谱自动跟上,
无手抄双源。历史沿革:旧版由图鉴 OCR 提取后手工固化(K7)+ 光能电池系手工补齐,
曾与注册表形成双源且漏网 8 件(equipment_mechanics.md 勘误记);W267 改为派生。

**合成机理**:2 件「基础件」合成 1 件「进阶」。注册表每件进阶的 recipes 列出
组件名组;两组件相同=自配(a×2),不同=交叉。派生规则::

    进阶配方集 = {name: eq.recipes | eq.category == '进阶' 且 eq.recipes 非空}
      —— 星徽/宝钻的 recipes(红钻/蓝钻系、三路宝钻)不属基础件两合图谱,按类别排除。
    自配:recipe[0] == recipe[1];交叉:recipe[0] != recipe[1]。
    GUANGNENG_* 视图 = 配方中含「光能电池」的子集(与 7 标准件的分组管理口径,
    仅为兼容既有消费方命名,非独立数据源)。

**穿着即合成(用户口述+run 26 实锤,2026-08-26)**:两件可合成组件穿到**同一角色**
身上时游戏**自动合成**、无确认无日志——tracking 账面记 2 件组件、画面只余 1 件
进阶(实证:量产型装甲×2→很硬的甲;光能电池+生命之花→绝对热量)。后果:
①equips 对账须把本图谱纳入预期(账面组件 == 画面进阶为合法态);
②穿戴分配(M7)给同一人穿两件可合成组件 = 隐性消耗决策;
③装备来源遥测链(tracking↔画面)全链需知悉此机制。

**K8 闭合**(派生后的结构事实):8 件基础件(7 标准简易 + 光能电池)两两合成图完整
闭合:C(8,2)=28 交叉 + 8 自配 = 36 件进阶全量。

**以太钻头 类别怪癖**:米游社 equipment.md 归「进阶」,但注册表按图鉴归「简易」
(作合成基础件)——以官方 API 类别为准。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_equipment_data import EQUIPMENTS

# 「光能电池系」视图的分组成员名。仅用于把全量配方切成两组常量(兼容旧 API 命名),
# 不参与任何判定逻辑;若未来新增强基础件系,应改为通用分组而非继续加名字。
_GUANGNENG_BASE: str = '光能电池'

# 进阶层的合成配方(名称 → 组件元组的元组),派生自注册表官方 compose_list。
# 排除星徽/宝钻:它们的 recipes 是红钻/蓝钻系或三路合成,不属「两基础件→一进阶」图谱。
_ADVANCE_RECIPES: dict[str, tuple[tuple[str, ...], ...]] = {
    _name: _eq.recipes for _name, _eq in EQUIPMENTS.items()
    if _eq.category == '进阶' and _eq.recipes
}

# 全量拆分:自配(a==b)/交叉(a!=b)。当前数据每件进阶恰 1 条配方;若未来出现
# 多条冲突配方的同名进阶,这里会静默取末条——由测试仓 K8 闭合锁兜住该漂移。
_ALL_SELF_RECIPES: dict[str, str] = {}
_ALL_CROSS_RECIPES: dict[str, tuple[str, str]] = {}
for _adv, _recipes in _ADVANCE_RECIPES.items():
    for _r in _recipes:
        if _r[0] == _r[1]:
            _ALL_SELF_RECIPES[_adv] = _r[0]
        else:
            _ALL_CROSS_RECIPES[_adv] = (_r[0], _r[1])

# 全部基础件(任一进阶配方的组件并集)= 7 件标准简易 + 光能电池,共 8 件。
_ALL_BASES: frozenset[str] = frozenset(
    _comp for _recipes in _ADVANCE_RECIPES.values() for _r in _recipes for _comp in _r)

# 7 件标准基础件(图鉴简易 tab 口径,不含光能电池;类别「简易」全集 − 光能电池)。
SYNTHESIS_BASES: frozenset[str] = frozenset(_ALL_BASES - {_GUANGNENG_BASE})

# 交叉配方:进阶名 → (基础件_a, 基础件_b),不含光能电池系的 21 个(C(7,2))。
CROSS_RECIPES: dict[str, tuple[str, str]] = {
    _k: _v for _k, _v in _ALL_CROSS_RECIPES.items() if _GUANGNENG_BASE not in _v}

# 自配配方:进阶名 → 基础件(×2 即得),不含光能电池的 7 个。
SELF_RECIPES: dict[str, str] = {
    _k: _v for _k, _v in _ALL_SELF_RECIPES.items() if _v != _GUANGNENG_BASE}

# 光能电池系视图(与标准 7 件分组的兼容切分):交叉 7 件 + 自配(永动机)。
GUANGNENG_CROSS_RECIPES: dict[str, tuple[str, str]] = {
    _k: _v for _k, _v in _ALL_CROSS_RECIPES.items() if _GUANGNENG_BASE in _v}
GUANGNENG_SELF_RECIPES: dict[str, str] = {
    _k: _v for _k, _v in _ALL_SELF_RECIPES.items() if _v == _GUANGNENG_BASE}

# 合成保留组件集(ADR-0265;用户口述 [29]「定阵容前不浪费装备合成/穿着」):
# 全部 8 件基础件。P1(plane==1)阶段这些组件**不入穿戴池**
# (cw_comps.equip_allocation 消费本常量——单一源,别在装备层复制清单),
# 留在 owned 待合成;合成路线不被过渡穿着锁死。
RESERVED_COMPONENTS: frozenset[str] = _ALL_BASES


def cross_components(advance: str) -> tuple[str, str] | None:
    """交叉配方进阶的两件基础件组件;非交叉进阶或未知 → None。

    覆盖标准 K7 与光能电池系(全量派生自注册表)。
    """
    return CROSS_RECIPES.get(advance) or GUANGNENG_CROSS_RECIPES.get(advance)


def self_base(advance: str) -> str | None:
    """自配进阶的基础件(×2 即得);非自配 → None。

    覆盖标准 7 件自配与永动机(光能电池×2)。
    """
    return SELF_RECIPES.get(advance) or GUANGNENG_SELF_RECIPES.get(advance)


def synthesize_target(a: str, b: str) -> str | None:
    """给定两件基础件,返回能合成的交叉进阶;无交叉配方 → None。

    不含自配(自配 a==b,见 ``self_advance``)。覆盖标准+光能电池系。
    """
    pair = {a, b}
    for adv, (x, y) in {**CROSS_RECIPES, **GUANGNENG_CROSS_RECIPES}.items():
        if {x, y} == pair:
            return adv
    return None


def self_advance(base: str) -> str | None:
    """基础件 ×2 合成的进阶(其「进阶版」);无 → None。

    覆盖标准 7 件与光能电池(→永动机)。
    """
    merged = {**SELF_RECIPES, **GUANGNENG_SELF_RECIPES}
    for adv, b in merged.items():
        if b == base:
            return adv
    return None


# ===== 装备策略接入(P14 期望模型的生产化;ADR-0391)=====
# P14(docs/game/currency_war/research/proofs/p14-equipment-acquisition-ev.md)
# 已证结论在此从证明脚本晋升为生产纯函数——装备分配准入/判读锚点消费;
# 证明脚本与本文档共享图谱单一源(本模块),数值改动自动传导。


def component_demand(key_equips: list[str]) -> dict[str, int]:
    """目标装备多重集 K 的**基础件需求向量**(P14 决策表的输入)。

    每件 K 展开为配方组件:交叉件 = 两件不同基础(火力风暴潮 = 轮滑鞋+
    折叠小刀);自配件 = 同基础 ×2(反重力皮靴 = 轮滑鞋×2)。K 中无配方件
    (白昼/特权类,无常规获取通道)跳过——不产生可规划需求(P14 Q4)。
    例:K=[反重力皮靴×2, 火力风暴潮] → {轮滑鞋: 5, 折叠小刀: 1}
    (皮靴=轮滑鞋×2,两双=4;风暴潮再加 1 轮滑鞋+1 小刀)——对拍 P14 例 1。
    """
    demand: dict[str, int] = {}
    for adv in key_equips:
        cross = cross_components(adv)
        if cross is not None:
            for b in cross:
                demand[b] = demand.get(b, 0) + 1
            continue
        base = self_base(adv)
        if base is not None:
            demand[base] = demand.get(base, 0) + 2
    return demand


def recycle_qualified(key_equips: list[str] | None) -> frozenset[str]:
    """**回收合格**基础件集(P14 定理 3 准入的生产化)。

    判据(证明见 P14 Q3):基础件 b 回收合格 ⟺ b 不是任何目标进阶的组件
    ——b 若能合成出想要的进阶,回收(销毁它换 1/36 抽卡机会)严格劣于
    留着合成;只有「连合成原料都当不上」的件才允许进回收流水线
    (2合1 → 3 件同刷,equipment_mechanics「回收流水线」节)。
    例:K=[反重力皮靴×2, 火力风暴潮](阿雅)→ 合格 = 以太钻头/光能电池/
    和平手枪/幸运星/生命之花/量产型装甲(轮滑鞋除外——需求 ×5)。
    ``key_equips=None``(无目标)→ 空集:有用性无从判定,一律不当死库存
    (保守侧,行为同旧)。
    """
    if not key_equips:
        return frozenset()
    useful = set(component_demand(key_equips))
    return frozenset(b for b in RESERVED_COMPONENTS if b not in useful)


def hoard_gaps(key_equips: list[str], owned: list[str]) -> dict[str, int]:
    """「缺什么囤什么」差集(P14 结论的判读锚点):基础件需求 − 库存。

    抵扣序:owned 已持有的**进阶件** 1:1 抵 K 同名需求(持有成品不再
    需要组件);剩余需求展开组件向量后减 owned 基础件库存,取正差。
    输出 = 「现在缺、发放流来了该囤住」的基础件及件数(P14 对实现的
    检验点 2:遥测按组件需求向量 − 库存向量报)。
    """
    from collections import Counter
    if not key_equips:
        return {}
    owned_ct = Counter(owned)
    remaining_k: list[str] = []
    for adv, need in Counter(key_equips).items():
        remain = max(0, need - owned_ct.get(adv, 0))
        remaining_k.extend([adv] * remain)
    demand = component_demand(remaining_k)
    gaps: dict[str, int] = {}
    for b, need in demand.items():
        lack = need - owned_ct.get(b, 0)
        if lack > 0:
            gaps[b] = lack
    return gaps
