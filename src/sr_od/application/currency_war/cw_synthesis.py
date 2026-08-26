"""货币战争 装备合成图谱(2 件基础件 → 1 件进阶;meta 层,V4.4)。

**合成机理**:2 件「基础件」(简易级)合成 1 件「进阶」。数据银行装备图鉴每件基础件的
「合成公式」区列出它能合成的进阶名(单列文字,OCR 得);每件进阶 = 恰好 2 件基础件
的组件 → 进阶名出现在那 2 件基础件的列表交集里。据此派生本图谱(详见
``tools/cw/extract_synthesis.py`` + ``.debug/temp/equip_recipes.json``,本模块从其派生)。

**穿着即合成(用户口述+run 26 实锤,2026-08-26)**:两件简易装备穿到**同一角色**身上
时游戏**自动合成**、无确认无日志——tracking 账面记 2 件基础件、画面只余 1 件进阶
(实证:量产型装甲×2→很硬的甲;光能电池+生命之花→绝对热量)。后果:①equips 对账
须把本图谱纳入预期(账面组件 == 画面进阶为合法态);②穿戴分配(M7)给同一人穿两件
可合成组件 = 隐性消耗决策(与 [29]「定阵容前不浪费合成」的守卫联动);
③装备来源遥测链(tracking↔画面)全链需知悉此机制。

**7 件标准基础件构成完整两两合成图(K7)**::

    以太钻头 / 和平手枪 / 幸运星 / 折叠小刀 / 生命之花 / 轮滑鞋 / 量产型装甲

- **交叉配方** 21 个(C(7,2)):每两件不同基础件 → 1 件进阶。双组件经图鉴列表交集核实
  (= 确证:进阶名同时出现在两件基础件的合成列表里)。
- **自配配方** 7 个:每件基础件 ×2(两件相同)→ 1 件进阶(其「进阶版」)。逻辑确证 ——
  每件基础件合成列表恰好 7 项,其中 6 项是与其他 6 件的交叉(K7 闭合),第 7 项(count==1,
  仅自己列表有)无其他基础件可配 → 只能自配;且「反重力皮靴 = 2×轮滑鞋」攻略确证该机制存在。
- 合计 28 件进阶,合成图完整闭合。

**以太钻头 类别怪癖**:数据银行图鉴把「以太钻头」放在简易 tab(作合成基础件),但米游社
equipment.md 归「进阶」类别(故 ``cw_equipment.EQUIPMENTS['以太钻头'].category == '进阶'``)。
本图谱按图鉴事实将其作基础件处理,与另 6 件简易并列。

**光能电池系配方(官方 API 补齐,2026-08-26)**:光能电池=**第 8 件基础件**,与 7 件
标准件各交叉一件 + 自配一件(永动机)——8 基础件 × K8 闭合:C(8,2)=28 交叉 + 8 自配
= 36 件进阶**全量**。来源=官方活动页 API(``tools/cw/plaza_fetch.py`` config 子命令,
equipment_list[].compose_list.childrens);旧 OCR 提取(「恰好 2 家列表交集」判据)对此
系失明的根因=图鉴 UI 每件标准件合成列表恰 7 项被 K7 占满,光能电池交叉件在标准件侧
显示不出来。**装备数据首选采集通道=官方 API**(id/icon/配方/属性全量结构化,版本更新
重拉即可);游戏内图鉴采集降级为离线校验 fallback。

**用途**:ComposeEquip 自动合成(后续 op)/ 评估阵容成型时算合成可达性。
"""
from __future__ import annotations

# 7 件标准基础件(图鉴简易 tab;以太钻头因图鉴归简易 tab 故入此,尽管米游社类别为进阶)
SYNTHESIS_BASES: frozenset[str] = frozenset({
    "以太钻头", "和平手枪", "幸运星", "折叠小刀", "生命之花", "轮滑鞋", "量产型装甲",
})

# 交叉配方(确证):进阶名 → (基础件_a, 基础件_b)。每 {a, b} → 1 进阶,共 C(7,2)=21。
CROSS_RECIPES: dict[str, tuple[str, str]] = {
    # 以太钻头 × {6 件}
    "光速螺旋桨": ("以太钻头", "轮滑鞋"),
    "动能激发剑": ("以太钻头", "折叠小刀"),
    "斩首行动": ("以太钻头", "和平手枪"),
    "胜利之旗": ("以太钻头", "幸运星"),
    "物质分解液": ("以太钻头", "生命之花"),
    "闪光手榴弹": ("以太钻头", "量产型装甲"),
    # 和平手枪 × {5 件,除以太钻头}
    "电磁弹射器": ("和平手枪", "轮滑鞋"),
    "武器大师": ("和平手枪", "折叠小刀"),
    "反卫星狙击枪": ("和平手枪", "幸运星"),
    "掩体生成枪": ("和平手枪", "生命之花"),
    "自适应外骨骼": ("和平手枪", "量产型装甲"),
    # 幸运星 × {4 件}
    "追逐星辰": ("幸运星", "轮滑鞋"),
    "高周波电锯": ("幸运星", "折叠小刀"),
    "热血沸腾拳": ("幸运星", "生命之花"),
    "以牙还牙甲": ("幸运星", "量产型装甲"),
    # 折叠小刀 × {3 件}
    "火力风暴潮": ("折叠小刀", "轮滑鞋"),
    "杀红眼": ("折叠小刀", "生命之花"),
    "信心注入器": ("折叠小刀", "量产型装甲"),
    # 生命之花 × {2 件}
    "步步生花": ("生命之花", "轮滑鞋"),
    "痛觉阻断芯片": ("生命之花", "量产型装甲"),
    # 轮滑鞋 × 量产型装甲
    "流星飞翼": ("轮滑鞋", "量产型装甲"),
}

# 自配配方(逻辑确证,见模块 docstring):进阶名 → 基础件(×2 即得该进阶)。
SELF_RECIPES: dict[str, str] = {
    "虫洞掘进钻头": "以太钻头",
    "天基轨道炮": "和平手枪",
    "随便骰子": "幸运星",
    "碎星斩舰刀": "折叠小刀",
    "生命之环": "生命之花",
    "反重力皮靴": "轮滑鞋",   # 攻略确证(2× 轮滑鞋 = 反重力皮靴)
    "很硬的甲": "量产型装甲",
}

# 光能电池系配方(官方 API config equipment_list.compose_list,2026-08-26 补齐;
# V4.4 快照 .debug/temp/currency_war/plaza/config_v4.4.json,tools/cw/plaza_fetch.py 可重拉)。
# 光能电池=第 8 件基础件:与 7 件标准件各交叉一件 + 自配一件(永动机)——
# 8 基础件 × K8 闭合:C(8,2)=28 交叉 + 8 自配 = 36 件进阶全量。
GUANGNENG_CROSS_RECIPES: dict[str, tuple[str, str]] = {
    "行星钻地弹": ("光能电池", "以太钻头"),
    "蓄能帆": ("光能电池", "和平手枪"),
    "冷笑话引擎": ("光能电池", "幸运星"),
    "战场进化手册": ("光能电池", "折叠小刀"),
    "绝对热量": ("光能电池", "生命之花"),   # run 26 实锤互证(卡芙卡穿着合成)
    "电光履": ("光能电池", "轮滑鞋"),
    "光能盾牌": ("光能电池", "量产型装甲"),
}
GUANGNENG_SELF_RECIPES: dict[str, str] = {
    "永动机": "光能电池",   # 光能电池×2(旧提取漏网件——自配且不在 GUANGNENG_ONLY 旧清单)
}

# 合成保留组件集(ADR-0265;用户口述 [29]「定阵容前不浪费装备合成/穿着」):
# SYNTHESIS_BASES ∪ {光能电池}。P1(plane==1)阶段这些组件**不入穿戴池**
# (cw_comps.equip_allocation 消费本常量——单一源,别在装备层复制清单),
# 留在 owned 待合成;合成路线不被过渡穿着锁死。
RESERVED_COMPONENTS: frozenset[str] = frozenset(
    SYNTHESIS_BASES | {"光能电池"})


def cross_components(advance: str) -> tuple[str, str] | None:
    """交叉配方进阶的两件基础件组件;非交叉进阶或未知 → None。

    覆盖标准 K7 与光能电池系(官方 API 补齐,2026-08-26)。
    """
    return CROSS_RECIPES.get(advance) or GUANGNENG_CROSS_RECIPES.get(advance)


def self_base(advance: str) -> str | None:
    """自配进阶的基础件(×2 即得);非自配 → None。

    覆盖标准 7 件自配与永动机(光能电池×2,官方 API)。
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
