"""货币战争 备战期望/估值纯函数(kernel 桶)。

决策核(decision)与应用执行层(app)共同消费的**无副作用估值函数**单一源:
输入名字/数值,输出期望价值,零识别零点击零包外依赖。

为何落在 kernel:同一条估值曲线同时喂给武装箱选卡策略(decision_v2.decide_box_card)
与 app 侧 handler 的旧内联回落(handle_supply_box.pick_box_card),归 kernel 是
分包依赖矩阵(DESIGN 分包 §3.2)下唯一同时合法的方向。
"""

#: 合成材料通用性静态表(v1:进阶配方引用数;数据源
#: docs/game/currency_war/data/equipment.md 合成公式)。
MATERIAL_VALUE_TABLE: dict[str, int] = {
    '生命之花': 7, '轮滑鞋': 6, '光能电池': 6, '以太钻头': 5, '折叠小刀': 5,
    '量产型装甲': 5, '和平手枪': 4, '幸运星': 3,
}


def material_value(name: str) -> int:
    """装备名 → 合成材料通用性分(表外 = 0;key_equips 打分的材料侧输入)。"""
    return MATERIAL_VALUE_TABLE.get(name, 0)
