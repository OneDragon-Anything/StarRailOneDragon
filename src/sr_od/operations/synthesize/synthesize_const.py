from enum import Enum

# 数量策略:数量节点的两种操作路径
QUANTITY_MODE_MAX_BTN: str = 'max_btn'
"""点「最大值」按钮(消耗品合成页的 UI 形态,奇巧零食在用)"""
QUANTITY_MODE_PLUS_MONTHLY: str = 'plus_monthly'
"""月限物品:+ 按钮逐次点满,置灰判顶,额度 0 跳过(材料合成页滑条 UI)"""


class SynthesizeItem:

    def __init__(self, category: str, name: str, template_id: str,
                 quantity_mode: str = QUANTITY_MODE_MAX_BTN):
        self.category: str = category
        self.name: str = name
        self.template_id: str = template_id
        # 数量策略,决定「选择数量」节点走哪条路径(见模块顶部常量)
        self.quantity_mode: str = quantity_mode


class SynthesizeItemEnum(Enum):

    TRICK_SNACK = SynthesizeItem('消耗品合成', '奇巧零食', 'trick_snack')
    SELF_MODELING_RESIN = SynthesizeItem(
        '材料合成', '自塑尘脂', 'self_modeling_resin',
        quantity_mode=QUANTITY_MODE_PLUS_MONTHLY)
