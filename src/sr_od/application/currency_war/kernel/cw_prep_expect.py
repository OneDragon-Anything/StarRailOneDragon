"""货币战争 备战购买意图载体(kernel 桶)。

现役唯一存活导出 = ``BuyPurchase``:商店买入点(cw_buy_card_action)逐击
记录的购买意图,随单元账本(cw_shop_action_ops BuyLedger)供给
cw_screen_buy_cards 的满栏多买张数读取与执行事实面。

历史注:本模块曾承载拖动/买牌/经验/装备四通道的期望态对账纯函数与
材料通用性估值表;期望态对账随对账归一(动作上报经上报函数族
写逻辑态,观察边界 cw_reconcile 兜底)整套拆除,材料估值表早已随
armory-box-value 迭代退役(选卡价值单一源 = kernel/cw_equip_value)。
"""

from dataclasses import dataclass


@dataclass
class BuyPurchase:
    """一次购买单元内记录的单条购买意图(shop.py 买入点写入)。

    [定义注释] name/star = 商店牌 OCR 身份与星级(ShopCard 真值源);
    count = 该牌本单元购入张数 k——常态=1;备战栏满且可触发合成时 =
    游戏自动多买 min(店内同牌张数, 3−已有数 mod 3)(merge_mechanics §2.5,
    【置信:低】,由对账网实证修正);unit_cost = 单体招募费(无折扣:
    总价 = k×unit_cost,§2.5 无价格优惠)。
    """
    name: str
    star: int
    count: int
    unit_cost: int
