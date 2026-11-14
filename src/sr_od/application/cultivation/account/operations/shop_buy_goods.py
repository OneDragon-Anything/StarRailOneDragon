"""兑换商店按商品名购买 —— 常驻商店·兑换商店(Exchange Shop)通用购买 op。

效果:按传入的商品名在兑换商店购买指定数量,画面停在商店列表页,
购买结果(实际数量/单价/余额/月限剩余)经运行结果 data 返回。
起点:商店页常驻商店任意 tab(列表滚动位任意,op 自行回顶;或兑换弹窗重入);
终点:商店页目标 tab 列表页。
副作用:消耗星芒/余烬等兑换材料,不可逆。仅限用户明确授权的购买请求调用。

兑换商店五个 tab(星芒兑换/余烬兑换/星尘之礼/光锥呈现/戏言成真)共用同一
画面结构(6 列商品网格 + 同款兑换弹窗),本 op 的流程与 tab 无关;tab 差异
只体现在切换锚(:class:`ShopSwitchTabOp`)与商品清单(:data:`_GOODS_META`),
新 tab 启用 = 补锚建档 + 加映射条目,不改本类代码。当前实测开放星芒/余烬/
光锥呈现(光锥呈现单把定价,弹窗带数量滑条,单次兑换上限 5 张)。

:param goods: 商品英文标识符(官方英文名主体词 snake_case),如 ``pass``(星轨
    通票 Star Rail Pass)/``special_pass``(星轨专票)/``tracks_of_destiny``
    (命运的足迹);未注册的标识符构造时抛 ValueError 并列出可用值。
    同名商品在双 tab 在售时(票类三件套)默认指余烬月限渠道——折扣价优先
    用完月度额度;要走星芒不限量渠道须显式传 ``tab='starlight'``。
:param count: 购买数量;``None`` = 拉满(受月限剩余与余额共同限制)。
    指定数量超月限剩余或超余额时**直接失败,不静默截断**——静默减量违背
    用户意图,须显式失败让调用方改传拉满或减量。
:param tab: 目标 tab,``embers``=余烬兑换 / ``starlight``=星芒兑换 /
    ``light_cone_manifest``=光锥呈现;
    ``None`` = 按 :data:`_GOODS_META` 的默认 tab。
:param scroll_search: 商品不在当前首屏时是否滚动扫描;``False`` = 只在
    首屏找、找不到直接失败——确定商品在首屏时(如票类三件套)传 False 提速。
"""

import re

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.cultivation.account.operations.read_warp_status import (
    parse_count,
)
from sr_od.application.cultivation.account.operations.shop_goods_scan import (
    BADGE_UNAVAILABLE_KEYWORDS as _BADGE_UNAVAILABLE_KEYWORDS,
)
from sr_od.application.cultivation.account.operations.shop_goods_scan import (
    MONTHLY_TRIO,
    locate_cards,
    parse_monthly_left,
)
from sr_od.application.cultivation.account.operations.shop_goods_scan import (
    NAME_OFFSET_FROM_TOP as _NAME_OFFSET_FROM_TOP,
)
from sr_od.application.cultivation.account.operations.shop_goods_scan import (
    badge_rect as _badge_rect_of,
)
from sr_od.application.cultivation.account.operations.shop_goods_scan import (
    ocr_rect_text as _ocr_rect_text_of,
)
from sr_od.application.cultivation.account.operations.shop_goods_scan import (
    read_count_two_pass as _read_count_two_pass_of,
)
from sr_od.application.cultivation.account.operations.shop_switch_tab import (
    TAB_EMBERS,
    TAB_LIGHT_CONE_MANIFEST,
    TAB_STARLIGHT,
    ShopSwitchTabOp,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_ALLOWED_TABS: set[str] = {TAB_EMBERS, TAB_STARLIGHT, TAB_LIGHT_CONE_MANIFEST}
_SHOP_EXCHANGE: str = 'exchange'
_SHOP_STELLAR_CONVERGENCE: str = 'stellar_convergence'
_SHOP_CONTRACT: str = 'contract'
_ALLOWED_SHOPS: set[str] = {_SHOP_EXCHANGE, _SHOP_STELLAR_CONVERGENCE,
                            _SHOP_CONTRACT}

_SHOP_SCREEN: str = '商店'
_POPUP_SCREEN: str = '商店-兑换弹窗'
_GIFT_SCREEN: str = '商店-礼包弹窗'
_SC_SCREEN: str = '商店-聚灵铸星'
_CT_SCREEN: str = '商店-协议商店'
_SHOP_SCREEN_BY_SHOP: dict[str, str] = {
    _SHOP_EXCHANGE: _SHOP_SCREEN,
    _SHOP_STELLAR_CONVERGENCE: _SC_SCREEN,
    _SHOP_CONTRACT: _CT_SCREEN,
}

_AREA_LIST_REGION: str = '商品列表'
_AREA_POPUP_MARK: str = '文本-兑换数量'
_AREA_POPUP_TITLE: str = '读区-弹窗商品名'
_AREA_POPUP_MONTHLY: str = '读区-弹窗月限剩余'
_AREA_POPUP_STATUS_BAR: str = '文本-弹窗状态横条'
_AREA_CONFIRM: str = '按钮-确认'
_AREA_CANCEL: str = '按钮-取消'
_AREA_COUNT: str = '读区-兑换数量'
_AREA_CURRENCY: str = '读区-货币数量'
_AREA_GIFT_MARK: str = '文本-购买后立刻获得'
_AREA_GIFT_TITLE: str = '读区-弹窗商品名'
_AREA_GIFT_CONFIRM: str = '按钮-确认'
_AREA_GIFT_CANCEL: str = '按钮-取消'
_MENU_SC: str = '菜单-聚灵铸星'
_MENU_CT: str = '菜单-协议商店'
_SC_TAB_ANCHOR: str = '文本-角色兑换'
_SC_TAB_AREA: str = 'tab-角色兑换'
_SC_TAB2_ANCHOR: str = '文本-光锥兑换'
_SC_TAB_CHARACTER: str = 'character_redemption'
_SC_TAB_LIGHT_CONE: str = 'light_cone_redemption'
_CT_ANCHOR: str = '文本-战略合作协议'
_POST_MAX_ROUNDS: int = 40
"""后购收尾的手动轮数上限(覆盖最长展示动画;框架节点预算仅作兜底)"""
_CONFIRM_MAX_WAIT_ROUNDS: int = 12
"""确认后弹窗未消失的连等封顶(轮):until_not 等待是 round_wait 无界
(WAIT 不烧重试预算),弹窗不消失(确认按钮禁用等异形)会挂死一条龙——
封顶转 FAIL,不判定购买结果(对照 back_to_normal_world_plus 同型教训)"""
_SKIP_POS: Point = Point(1875, 68)
"""后购画面右上角通用点击点:展示画面=跳过键,获得物品弹窗=「点击空白处
关闭」的可关区,一笔通吃;商店页识别命中时不会走到此点击(该位置在商店页
是关闭 X,误点会关店,故点击严格放在画面识别为非商店页之后)"""

# 商品网格几何/卡定位/角标读取管线平移至 shop_goods_scan 单一源模块
# (识别器与购买 op 共用;本模块经上方别名导入消费)

_SCROLL_STEP: int = 300
"""单次滚动拖距(px),行高 325 且列表按行吸附,300 拖距吸附 1 行,连续帧
至少完整露出一行商品,不漏扫"""
_SCROLL_MAX_ROUNDS: int = 12
"""滚动找商品的保险上限(余烬页约 10 行),防列表异常时无限拖"""
_RESET_SCROLL_MAX_DRAGS: int = 12
"""回顶拖拽上限(余烬页从底部回顶约 8 行,单拖约 1.7 行;判静止提前退出)"""
_SCROLL_SAME_TEXT_ROUNDS: int = 2
"""拖后画面文本与上轮一致的连续轮数判定到底(行吸附列表拖后无变化 = 到底;
连续 2 轮防拖拽动画过渡帧/轮间时序导致的单轮同帧误判)"""

# 卡不可购态角标关键词:命中即 fail,不进弹窗(售罄弹窗确认按钮禁用,进了也无法购买)
# 角标关键词 → fail_status(语义分支用;已达上限/未解锁同属「卡面不可购」)
_BADGE_FAIL_STATUS: dict[str, str] = {
    '已售罄': 'SOLD_OUT',
    '已达上限': 'CARD_UNAVAILABLE',
    '未解锁': 'CARD_UNAVAILABLE',
}
# 弹窗状态横条(与列表角标同源的不可购提示,弹窗内出现时点取消诚实失败)
_POPUP_STATUS_KEYWORDS: tuple[tuple[str, str], ...] = (
    ('已售罄', 'SOLD_OUT'),
    ('兑换材料不足', 'INSUFFICIENT_MATERIALS'),
)

_TITLE_MATCH_LCS: float = 0.8
"""弹窗商品名校验的 LCS 兜底阈值:弹窗标题字体有异体字形态(实测「命运的
足迹」标题 OCR 为「命运的足跡」,LCS=0.8);阈值须高于易混对的相似度
(星轨通票/星轨专票 LCS=0.75,低于阈值不误放行)"""

# 弹窗中部控件行几何(锚定推导):弹窗中部布局随描述文字行数浮动(实测两
# 变体——余烬月限型 2026-11-12 实拍、光锥呈现型 2026-11-13 实拍——滑条行
# y 相差 35px),固定矩形撑不住;「兑换数量：N」标签是弹窗结构元素,两变体
# 相对偏移一致(滑条行 +24px、价格行 +55px),以标签 OCR 框中心为锚推导控件位。
# x 为两变体恒定值:滑条行 减号 778 / 加号 1378 / 拉满 1453,价格框 x 1050-1230。
_ROW_DY: int = 24
_MINUS_X: int = 778
_PLUS_X: int = 1378
_MAX_X: int = 1453
_PRICE_RECT_REL: tuple[int, int, int, int] = (-90, 35, 90, 75)
"""价格读区相对标签锚的 (dx1, dy1, dx2, dy2);锚 x≈1140 → 框 x 1050-1230"""


def _is_target_popup_title(title: str | None, goods_cn: str) -> bool:
    """弹窗商品名与目标关键词匹配:包含优先,异体字形态走 LCS 兜底。"""
    if not title:
        return False
    return (goods_cn in title
            or str_utils.find_by_lcs(goods_cn, title,
                                     percent=_TITLE_MATCH_LCS))


_BALANCE_TOLERANCE: int = 2
"""余额差值终验容差(顶部货币读数的 OCR 个位抖动)"""

_GOODS_META: dict[str, tuple[str, str, str]] = {
    # 值 = (shop, tab, 商品名 OCR 关键词)
    # 英文标识符(官方英文名主体词) → (shop, tab, 商品名 OCR 关键词)
    # 关键词 = 卡面商品名的唯一子串(去书名号/逗号等装饰,防 OCR 抖动)
    # ——对照表来源:2026-11-12 实机中英双态走查(见 .debug/temp/operation-explore/
    #   2026-11-12-shop-buy-goods/screen-flow.md,永久副本归档后指针随测试固化)
    # 月限三件套关键词引自 shop_goods_scan.MONTHLY_TRIO(识别器共用单一源)
    'special_pass': (_SHOP_EXCHANGE, TAB_EMBERS, MONTHLY_TRIO['special_pass']),
    'pass': (_SHOP_EXCHANGE, TAB_EMBERS, MONTHLY_TRIO['pass']),
    'tracks_of_destiny': (_SHOP_EXCHANGE, TAB_EMBERS,
                          MONTHLY_TRIO['tracks_of_destiny']),
    'adventure_log': (_SHOP_EXCHANGE, TAB_EMBERS, '冒险记录'),
    'condensed_aether': (_SHOP_EXCHANGE, TAB_EMBERS, '凝缩以太'),
    'lost_gold_fragment': (_SHOP_EXCHANGE, TAB_EMBERS, '遗失碎金'),
    'credit': (_SHOP_EXCHANGE, TAB_EMBERS, '信用点'),
    'key_of_knowledge': (_SHOP_EXCHANGE, TAB_EMBERS, '启迪之钥'),
    # 3 星光锥残器(30/版本,18 余烬)
    'lifeless_blade': (_SHOP_EXCHANGE, TAB_EMBERS, '无生残刃'),
    'arrow_of_the_demon_slayer': (_SHOP_EXCHANGE, TAB_EMBERS, '屠魔之矢'),
    'oath_of_steel': (_SHOP_EXCHANGE, TAB_EMBERS, '寒铁的誓言'),
    'obsidian_of_desolation': (_SHOP_EXCHANGE, TAB_EMBERS, '虚空黑曜'),
    'ancestral_hymn': (_SHOP_EXCHANGE, TAB_EMBERS, '家族颂歌'),
    'sprout_of_life': (_SHOP_EXCHANGE, TAB_EMBERS, '生命之芽'),
    'lupitoxin_sawteeth': (_SHOP_EXCHANGE, TAB_EMBERS, '狼毒锯牙'),
    'destined_expiration': (_SHOP_EXCHANGE, TAB_EMBERS, '命定死因'),
    'dynamic_outlining': (_SHOP_EXCHANGE, TAB_EMBERS, '动态线稿'),
    'crystal_meteorites': (_SHOP_EXCHANGE, TAB_EMBERS, '流星棱晶'),
    'starfire_essence': (_SHOP_EXCHANGE, TAB_EMBERS, '星火之精'),
    'celestial_section': (_SHOP_EXCHANGE, TAB_EMBERS, '空际小节'),
    'nourishing_honey': (_SHOP_EXCHANGE, TAB_EMBERS, '滋长花蜜'),
    'seedling_of_manas': (_SHOP_EXCHANGE, TAB_EMBERS, '末那芽苗'),
    'the_fluffy_serialization_memorial_issue': (_SHOP_EXCHANGE, TAB_EMBERS, '连载纪念刊'),
    'resin_of_valor': (_SHOP_EXCHANGE, TAB_EMBERS, '战魂血珀'),
    'wine_of_phagousa': (_SHOP_EXCHANGE, TAB_EMBERS, '法吉娜之酒'),
    'galaxy_framework': (_SHOP_EXCHANGE, TAB_EMBERS, '星系框桇'),
    'sixen_king_rook_fork': (_SHOP_EXCHANGE, TAB_EMBERS, '王手飞车'),
    # 2 星养成材料(20/版本,12 余烬)
    'shattered_blade': (_SHOP_EXCHANGE, TAB_EMBERS, '破碎残刃'),
    'arrow_of_the_beast_hunter': (_SHOP_EXCHANGE, TAB_EMBERS, '猎兽之矢'),
    'key_of_inspiration': (_SHOP_EXCHANGE, TAB_EMBERS, '灵感之钥'),
    'endurance_of_bronze': (_SHOP_EXCHANGE, TAB_EMBERS, '青铜的执着'),
    'obsidian_of_dread': (_SHOP_EXCHANGE, TAB_EMBERS, '黯淡黑曜'),
    'harmonic_tune': (_SHOP_EXCHANGE, TAB_EMBERS, '谐乐小调'),
    'seed_of_abundance': (_SHOP_EXCHANGE, TAB_EMBERS, '丰饶之种'),
    'borisin_teeth': (_SHOP_EXCHANGE, TAB_EMBERS, '步离犬牙'),
    'meteoric_bullet': (_SHOP_EXCHANGE, TAB_EMBERS, '陨铁弹丸'),
    'rough_sketch': (_SHOP_EXCHANGE, TAB_EMBERS, '凌乱草图'),
    'scattered_stardust': (_SHOP_EXCHANGE, TAB_EMBERS, '散逸星砂'),
    'fiery_spirit': (_SHOP_EXCHANGE, TAB_EMBERS, '炽情之灵'),
    'firmament_note': (_SHOP_EXCHANGE, TAB_EMBERS, '云际音符'),
    'alien_tree_seed': (_SHOP_EXCHANGE, TAB_EMBERS, '异木种籽'),
    'bija_of_consciousness': (_SHOP_EXCHANGE, TAB_EMBERS, '思量的种'),
    'the_fluffy_hand_drawn_storyboards': (_SHOP_EXCHANGE, TAB_EMBERS, '手绘分镜稿'),
    'grit_of_strife': (_SHOP_EXCHANGE, TAB_EMBERS, '纷争血尘'),
    'tear_of_phagousa': (_SHOP_EXCHANGE, TAB_EMBERS, '法吉娜之泪'),
    'celestial_globe': (_SHOP_EXCHANGE, TAB_EMBERS, '天体模型'),
    'four_phases_crossing_the_river_to_check_the_king': (_SHOP_EXCHANGE, TAB_EMBERS, '过河照君'),
    # 周限遗器材料(40/周,4 余烬)
    'extinguished_core': (_SHOP_EXCHANGE, TAB_EMBERS, '熄灭原核'),
    'thiefs_instinct': (_SHOP_EXCHANGE, TAB_EMBERS, '掠夺的本能'),
    'silvermane_badge': (_SHOP_EXCHANGE, TAB_EMBERS, '铁卫扣饰'),
    'ancient_part': (_SHOP_EXCHANGE, TAB_EMBERS, '古代零件'),
    'immortal_scionette': (_SHOP_EXCHANGE, TAB_EMBERS, '永寿幼芽'),
    'artifexs_module': (_SHOP_EXCHANGE, TAB_EMBERS, '工造机杼'),
    'dream_collection_component': (_SHOP_EXCHANGE, TAB_EMBERS, '蓄梦元件'),
    'tatters_of_thought': (_SHOP_EXCHANGE, TAB_EMBERS, '思绪末屑'),
    'fear_stomped_flesh': (_SHOP_EXCHANGE, TAB_EMBERS, '恐惧踏碎血肉'),
    'ethereal_omen': (_SHOP_EXCHANGE, TAB_EMBERS, '预兆似有若无'),
    'whimsy_wax': (_SHOP_EXCHANGE, TAB_EMBERS, '童真蜡笔'),
    # 星芒兑换 tab 专属(600 星芒/版本 1 个;140 档已达上限形态同角标拦截)
    'night_on_the_milky_way': (_SHOP_EXCHANGE, TAB_STARLIGHT, '银河铁道之夜'),
    'something_irreplaceable': (_SHOP_EXCHANGE, TAB_STARLIGHT, '无可取代的东西'),
    'but_the_battle_isnt_over': (_SHOP_EXCHANGE, TAB_STARLIGHT, '但战斗还未结束'),
    'in_the_name_of_the_world': (_SHOP_EXCHANGE, TAB_STARLIGHT, '以世界之名'),
    'moment_of_victory': (_SHOP_EXCHANGE, TAB_STARLIGHT, '制胜的瞬间'),
    'sleep_like_the_dead': (_SHOP_EXCHANGE, TAB_STARLIGHT, '如泥酣眠'),
    'time_waits_for_no_one': (_SHOP_EXCHANGE, TAB_STARLIGHT, '时节不居'),
    'dan_heng': (_SHOP_EXCHANGE, TAB_STARLIGHT, '丹恒'),
    'serval': (_SHOP_EXCHANGE, TAB_STARLIGHT, '希露瓦'),
    # 光锥呈现 tab(4星常驻光锥,200 流光余晖/把,单次兑换上限 5 张)
    'mushyshroomysadventures': (_SHOP_EXCHANGE, TAB_LIGHT_CONE_MANIFEST, '菇菇嘎嘎历险记'),
    # 聚灵铸星 Stellar Convergence:常驻 5 星角色(1 金徽,可重复兑换升星魂;
    # 角色兑换 tab)。关键词取卡面名唯一子串(「阮·梅」的间隔点 OCR 易丢,
    # 取单字「阮」;「托帕&账账」取「托帕」)
    'jiaoqiu': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '椒丘'),
    'robin': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '知更鸟'),
    'huohuo': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '藿藿'),
    'topaz_numby': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '托帕'),
    'ruan_mei': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '阮'),
    'luocha': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '罗刹'),
    'himeko': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '姬子'),
    'clara': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '克拉拉'),
    'welt': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '瓦尔特'),
    'gepard': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '杰帕德'),
    'yanqing': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '彦卿'),
    'bailu': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_CHARACTER, '白露'),
    # 聚灵铸星光锥兑换 tab(4 蓝徽,常驻 5 星光锥;英文名 2026-11-13 英文态实采)
    'those_many_springs': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '那无数个春天'),
    'dance_at_sunset': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '落日时起舞'),
    'flowing_nightglow': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '夜色流光溢彩'),
    'an_instant_before_a_gaze': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '留在眼底'),
    'night_of_fright': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '惊魂夜'),
    'incessant_rain': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '雨一直下'),
    'worrisome_blissful': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '烦恼着'),
    'past_self_in_mirror': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '镜中故我'),
    'she_already_shut_her_eyes': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '闭上双眼'),
    'the_unreachable_side': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '彼岸'),
    'echoes_of_the_coffin': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '棺的回响'),
    'in_the_night': (_SHOP_STELLAR_CONVERGENCE, _SC_TAB_LIGHT_CONE, '于夜色中'),
    # 协议商店 Contract Shop:黑塔支持协议礼包(黑塔券,限购+倒计时)
    'herta_contract_strategic_cooperation': (_SHOP_CONTRACT, None, '战略合作协议'),
    'herta_contract_strategic_support': (_SHOP_CONTRACT, None, '战略支援协议'),
    'herta_contract_trailblaze_aid': (_SHOP_CONTRACT, None, '开拓支援协议'),
    'herta_contract_fuel_refill': (_SHOP_CONTRACT, None, '燃料补充协议'),
    'herta_contract_quest_sharing': (_SHOP_CONTRACT, None, '冒险共享协议'),
    'herta_contract_roaming_refill': (_SHOP_CONTRACT, None, '漫游补充协议'),
    'herta_contract_resource_supply_v2': (_SHOP_CONTRACT, None, '材料支持协议'),
}

# parse_monthly_left 已平移至 shop_goods_scan(斜杠对单一源),本模块经
# 顶部导入保留同名符号(存量 import 兼容);re 仅供 _slider_cap 上限条解析。


class ExchangeShopBuyGoods(SrOperation):
    """按商品名在兑换商店购买指定数量。
    起点:商店页常驻商店任意 tab(或兑换弹窗重入);终点:商店页目标 tab 列表页。
    副作用:消耗星芒/余烬等兑换材料,不可逆;仅限用户明确授权的购买请求调用。

    结果状态:
    - ``PURCHASED``:购买完成回列表页,data 带 ``goods``/``tab``/``bought``
      (实际购买数量)/``unit_price``(单价)/``balance_left``(购买后余额)/
      ``monthly_left``(期限限购商品的购买后剩余额度;不限量商品为 None);
    失败分类(供编排分支的机器可读语义,``status`` 保持人读诊断句不变):
    失败出口的 data 带 ``fail_status`` 与英文标识符口径的 ``goods``——
    ``SOLD_OUT``=本期额度已尽(列表角标已售罄/弹窗横条已售罄)、
    ``CARD_UNAVAILABLE``=卡面不可购(角标已达上限/未解锁)、
    ``NOT_FOUND``=商品不在列表(到底未命中/首屏未命中/滚动上限)、
    ``INSUFFICIENT_MATERIALS``=余额/额度不够换满(弹窗横条兑换材料不足/
    余额预判/超月限预判);其余失败 data 无 ``fail_status`` = 非预期失败
    (起点不在商店页/弹窗商品名不符/确认未生效/余额终验不符/画面未回
    商店页等,编排方按中止处理)。
    其余失败:起点不在商店页、商品标识符未注册、tab 切换失败、商品不在列表
    (滚动到底未命中)、目标卡不可购(已售罄/已达上限/未解锁)、弹窗状态
    横条(售罄/兑换材料不足)、数量超月限或超余额(不截断)、数量调不到
    目标、确认未生效、余额差值终验不符、确认后画面未回商店页(此时购买
    可能已完成,失败 data 带尽力读的余额供人工对账)。
    """

    def __init__(self, ctx: SrContext, goods: str, count: int | None = None,
                 tab: str | None = None, shop: str | None = None,
                 scroll_search: bool = True):
        """
        :param ctx: 上下文
        :param goods: 商品英文标识符,见类 docstring(未注册抛 ValueError)
        :param count: 购买数量;``None`` = 拉满。**消耗参数:仅限用户明确授权的购买请求传入。**
        :param tab: 目标 tab,``embers``=余烬兑换 / ``starlight``=星芒兑换 /
            ``light_cone_manifest``=光锥呈现;``None`` = 按 :data:`_GOODS_META` 默认
        :param shop: 目标子商店(exchange/stellar_convergence/contract);
            ``None`` = 按 :data:`_GOODS_META` 默认
        :param scroll_search: 商品不在首屏时是否滚动扫描(默认 True)
        """
        meta = _GOODS_META.get(goods)
        if meta is None:
            raise ValueError(
                f'未注册的商品标识符: {goods}(可用: {sorted(_GOODS_META)})')
        resolved_shop = meta[0] if shop is None else shop
        if resolved_shop not in _ALLOWED_SHOPS:
            raise ValueError(
                f'不支持的 shop: {resolved_shop}(仅支持 {sorted(_ALLOWED_SHOPS)})')
        resolved_tab = meta[1] if tab is None else tab
        if resolved_shop == _SHOP_EXCHANGE and resolved_tab not in _ALLOWED_TABS:
            raise ValueError(
                f'不支持的 tab: {resolved_tab}(仅支持 {"/".join(sorted(_ALLOWED_TABS))})')
        if count is not None and count <= 0:
            raise ValueError(f'count 必须为正数或 None(拉满),收到: {count}')

        self._goods: str = goods
        self._goods_cn: str = meta[2]
        self._shop: str = resolved_shop
        self._shop_screen: str = _SHOP_SCREEN_BY_SHOP[resolved_shop]
        self._tab: str = resolved_tab
        self._count: int | None = count
        self._scroll_search: bool = scroll_search

        self._popup_opened: bool = False
        """弹窗已打开(数量调整/确认节点的前置判据)"""
        self._popup_is_gift: bool = False
        """弹窗为礼包确认形态(协议商店:无数量滑条,数量恒 1 直确认)"""
        self._currency_area: str = (
            '读区-货币数量-金徽'
            if (resolved_shop == _SHOP_STELLAR_CONVERGENCE
                and resolved_tab == _SC_TAB_CHARACTER)
            else _AREA_CURRENCY)
        """余额读数 area:聚灵铸星页右上双货币并排,角色兑换读金徽(第 1 个)、
        光锥兑换读默认区(蓝徽);其余子商店单货币用默认区"""
        self._pre_balance: int | None = None
        """购买前列表页货币余额(余额差值终验基准;不可读场景(协议代币不在
        货币区)为 None,终验降级为角标软读数)"""
        self._monthly_left: int | None = None
        """弹窗月限胶囊剩余(None = 不限量商品);count 超限判定与拉满上限"""
        self._unit_price: int | None = None
        """单价(弹窗数量 1 时价格读数;余额不足预判与终验)"""
        self._bought: int | None = None
        """数量调整完成时的实际数量(确认后的终验与 data)"""
        self._card_rect: Rect | None = None
        """目标商品卡槽位(列表页坐标;弹窗打开期间列表不滚动,坐标恒稳)"""
        self._last_scan_text: str | None = None
        """上一轮列表区 OCR 全文(拖后一致判到底)"""
        self._same_text_rounds: int = 0
        """全文与上轮一致的连续轮数(达 _SCROLL_SAME_TEXT_ROUNDS 判到底)"""
        self._scroll_rounds: int = 0
        """已执行滚动次数(保险上限)"""
        self._last_pull_count: int | None = None
        """上一轮拉满后的数量读数(两轮同值判滑条到顶,防 1 张顶格时误判未生效)"""
        self._pull_confirmed: bool = False
        """同值已复点一次(区分「已到顶」与「单次点击丢失」,第二次同值才判到顶)"""
        self._probe_price: int | None = None
        """单价探测点击前的弹窗价格(None = 未在探测;下一轮价差=单价,0=已到顶)"""
        self._post_rounds: int = 0
        """后购收尾已用轮数(达 _POST_MAX_ROUNDS 判画面不收敛,带语境失败)"""
        self._confirm_wait_rounds: int = 0
        """确认后弹窗未消失的连等轮数(达 _CONFIRM_MAX_WAIT_ROUNDS 转 FAIL)"""
        SrOperation.__init__(self, ctx, op_name=gt('商店购买'),
                             node_max_retry_times=60)

    @operation_node(name='准备商店', is_start_node=True)
    def setup_shop(self) -> OperationRoundResult:
        """入口画面级判定,分发:目标子商店页 → 回顶扫描;弹窗 → 商品名核验后调数量。

        画面不在预期集合直接失败(不做逐 area 试命中推断)。导航:
        - exchange → ShopSwitchTabOp(目标 tab 选中态模板锚)
        - stellar_convergence/contract → 左侧菜单入口点击 → until 页特征锚
          (聚灵铸星=双 tab 词、协议=首卡商品名)
        目标子商店已是当前页时跳过导航点击(幂等)。
        """
        screen = self.check_and_update_current_screen(screen_name_list=[
            _SHOP_SCREEN, _SC_SCREEN, _CT_SCREEN, _POPUP_SCREEN, _GIFT_SCREEN])
        if screen in (_POPUP_SCREEN, _GIFT_SCREEN):
            title_screen = screen
            title_area = (_AREA_GIFT_TITLE if screen == _GIFT_SCREEN
                          else _AREA_POPUP_TITLE)
            title = self._area_text(self.last_screenshot, title_screen,
                                    title_area)
            if not _is_target_popup_title(title, self._goods_cn):
                return self.round_fail(
                    f'当前弹窗不是目标商品 {self._goods_cn}(弹窗商品名: '
                    f'{title or "未识别"}),请先关闭该弹窗再重试')
            self._popup_opened = True
            self._popup_is_gift = screen == _GIFT_SCREEN
            return self.round_success(
                status='POPUP_GIFT' if self._popup_is_gift else 'POPUP_OPENED',
                wait=1)
        if screen != self._shop_screen:
            # 在其他子商店页 → 左侧菜单直达目标子商店;转移验证由下一轮
            # 入口判定承担(screen == 目标子商店屏)。非商店族画面仍 fail。
            if screen in (_SHOP_SCREEN, _SC_SCREEN, _CT_SCREEN):
                menu_area = (_MENU_SC if self._shop == _SHOP_STELLAR_CONVERGENCE
                             else _MENU_CT)
                menu = self.ctx.screen_loader.get_area(screen, menu_area)
                if menu is None:
                    return self.round_fail(
                        f'当前画面 {screen} 无子商店入口 {menu_area}')
                self.ctx.controller.click(menu.center, press_time=0.1)
                return self.round_retry(
                    f'已点子商店入口 {menu_area},下一轮验证页面锚', wait=1.5)
            return self.round_fail(
                f'起点不在商店页(当前: {screen or "未识别"}),'
                f'请先导航到商店(常驻商店)')
        # 前台点击/拖拽要求游戏窗口激活:窗口失焦时手势落在窗外全部无效
        # (实机对照:MCP 工具每次 active_window 后有效,op 中途失焦后无效)
        self.ctx.controller.active_window()
        if self._shop == _SHOP_EXCHANGE:
            switch_op = ShopSwitchTabOp(self.ctx, tab=self._tab)
            switch_result = switch_op.execute()
            if not switch_result.success:
                return self.round_fail(
                    f'切换到目标 tab 失败: {switch_result.status}')
            return self.round_success(status='SHOP_READY', wait=0.5)
        # 聚灵铸星/协议商店:已在目标子商店页 → 直接进回顶
        return self.round_success(status='SHOP_READY', wait=0.5)

    @node_from(from_name='准备商店', status='SHOP_READY')
    @operation_node(name='回顶列表', node_max_retry_times=20)
    def reset_scroll(self) -> OperationRoundResult:
        """扫描前把商品列表回滚到顶:起点滚动位置不定(上一 op 可能留在中途),
        从顶部起扫才能覆盖全列表。回顶 = 手指下滑(内容上移),拖一次 → 等吸附
        → OCR 全文对比判静止,连续静止即到顶——连发拖拽会被后续手势打断
        吸附,净位移只剩最后一拖,不能一次拖到位。

        拖拽 x 取列表右缘空白带(第 6 列卡右缘之外):卡面手势可能被判定为
        点击卡而非列表滚动。duration ≥0.5:更快的快速手势不被识别为拖拽
        (实机对照,同参数 0.5 有效 0.3 无效)。

        协议商店单页(约 1.2 行,无滚动)直接跳过回顶。
        """
        if self._shop == _SHOP_CONTRACT:
            # 协议代币不在顶部货币区(货币区显示星琼),余额不可读 → None,
            # 终验降级为角标软读数
            return self.round_success(status='RESET_DONE', wait=0.5)
        area = self.ctx.screen_loader.get_area(self._shop_screen, _AREA_LIST_REGION)
        drag_x = area.rect.x2 - 60
        drag_y_top = max(area.center.y - 260, area.rect.y1 + 40)
        drag_y_bottom = min(area.center.y + 260, area.rect.y2 - 40)
        full_text = self._scan_goods(self.last_screenshot)[1]
        for _ in range(_RESET_SCROLL_MAX_DRAGS):
            self.ctx.controller.drag_to(
                Point(drag_x, drag_y_bottom), Point(drag_x, drag_y_top),
                duration=0.5)
            # round_wait 借框架等待睡吸附时长;丢弃返回值(流转由节点 return 决定)
            self.round_wait('回顶拖拽后等待吸附', wait=0.8)
            self.screenshot()  # 节点内主动取新帧(last_screenshot 仅轮次开头更新)
            new_text = self._scan_goods(self.last_screenshot)[1]
            if new_text == full_text:
                # 同帧 + 顶行商品可见 = 真到顶;同帧但顶行不在 = 拖拽被偶发
                # 吞掉(实机:首拖无效曾误判到顶,列表实际留在原地),继续强拖
                if self._top_row_visible():
                    break
            full_text = new_text
        self._pre_balance = parse_count(self._area_count_text(
            self.last_screenshot, self._shop_screen, self._currency_area))
        if self._pre_balance is None:
            return self.round_fail('顶部货币余额读取失败,无法进行余额终验')
        # wait 覆盖末次拖拽的惯性+吸附余波,保证 locate 拿到静止帧
        return self.round_success(status='RESET_DONE', wait=1.5)

    @node_from(from_name='回顶列表', status='RESET_DONE')
    @node_from(from_name='滚动一格', status='SCROLLED')
    @operation_node(name='定位商品', node_max_retry_times=30)
    def locate_goods(self) -> OperationRoundResult:
        """弹窗已在屏则核验商品名放行;否则 OCR 扫描列表定位目标卡,角标拦截后点卡。

        点击后的转移验证由下一轮的弹窗分支承担(点卡 → 重入 → 弹窗锚在屏
        才放行),不做「点了即成功」;同帧全文与上轮一致且未命中 = 列表到底。
        """
        if self._exchange_popup_visible():
            title = self._area_text(self.last_screenshot, _POPUP_SCREEN,
                                    _AREA_POPUP_TITLE)
            if not _is_target_popup_title(title, self._goods_cn):
                return self.round_fail(
                    f'兑换弹窗商品名与目标不符(期望 {self._goods_cn},'
                    f'实读 {title or "未识别"}),中止')
            self._popup_opened = True
            self._popup_is_gift = False
            return self.round_success(status='POPUP_OPENED', wait=1)
        if self._gift_popup_visible():
            title = self._area_text(self.last_screenshot, _GIFT_SCREEN,
                                    _AREA_GIFT_TITLE)
            if not _is_target_popup_title(title, self._goods_cn):
                return self.round_fail(
                    f'礼包弹窗商品名与目标不符(期望 {self._goods_cn},'
                    f'实读 {title or "未识别"}),中止')
            self._popup_opened = True
            self._popup_is_gift = True
            return self.round_success(status='POPUP_GIFT', wait=1)
        card_rect, full_text = self._scan_goods(self.last_screenshot)
        if card_rect is None:
            if full_text == self._last_scan_text:
                self._same_text_rounds += 1
            else:
                self._same_text_rounds = 0
                self._last_scan_text = full_text
            if (self._scroll_rounds > 0
                    and self._same_text_rounds >= _SCROLL_SAME_TEXT_ROUNDS):
                return self.round_fail(
                    f'列表已到底,未找到商品 {self._goods_cn}({self._goods_cn} '
                    f'可能未在售或本期额度形态变化)',
                    data={'goods': self._goods, 'fail_status': 'NOT_FOUND'})
            if not self._scroll_search:
                return self.round_fail(
                    f'首屏未找到商品 {self._goods_cn}(scroll_search=False 不滚动)',
                    data={'goods': self._goods, 'fail_status': 'NOT_FOUND'})
            if self._scroll_rounds >= _SCROLL_MAX_ROUNDS:
                return self.round_fail(
                    f'滚动 {_SCROLL_MAX_ROUNDS} 次仍未找到商品 {self._goods_cn},中止',
                    data={'goods': self._goods, 'fail_status': 'NOT_FOUND'})
            return self.round_success(status='SCROLL_NEXT', wait=0.5)
        unavailable = self._read_badge_state(card_rect)
        if unavailable is not None:
            return self.round_fail(
                f'目标商品卡不可购(角标: {unavailable})', data={
                    'goods': self._goods,
                    'fail_status': _BADGE_FAIL_STATUS.get(unavailable, 'CARD_UNAVAILABLE'),
                })
        self._card_rect = card_rect
        self._click_rect_center(self._shop_screen, card_rect)
        return self.round_retry('已点商品卡,下一轮验证兑换弹窗', wait=1.5)

    @node_from(from_name='定位商品', status='SCROLL_NEXT')
    @operation_node(name='滚动一格')
    def scroll_next(self) -> OperationRoundResult:
        """列表区右缘空白带上滑一格(行吸附),回定位商品重扫。

        拖拽 x 同 reset_scroll 取列表右缘空白带,避免手势落在商品卡上。
        """
        area = self.ctx.screen_loader.get_area(self._shop_screen, _AREA_LIST_REGION)
        start = Point(area.rect.x2 - 60, area.center.y)
        end = Point(area.rect.x2 - 60, area.center.y - _SCROLL_STEP)
        self.ctx.controller.drag_to(end, start, duration=0.8)
        self._scroll_rounds += 1
        return self.round_success(status='SCROLLED', wait=1)

    @node_from(from_name='准备商店', status='POPUP_OPENED')
    @node_from(from_name='准备商店', status='POPUP_GIFT')
    @node_from(from_name='定位商品', status='POPUP_OPENED')
    @node_from(from_name='定位商品', status='POPUP_GIFT')
    @operation_node(name='调整数量', node_max_retry_times=40)
    def adjust_count(self) -> OperationRoundResult:
        """按 count 调整兑换数量,完成时记录实际数量与单价,进入确认。

        count=None:点「拉满」一键到滑条上限(期限商品=月限剩余,不限量商品
        受余额截断),两轮读数同值判到顶(余额/月限只够 1 张时 current==1 也
        是终态,不能用 >1 判生效);count=N:先做月限与余额预判(超限 fail 不
        截断),再读当前数量 c,c<N 点「+」,c==N 记 bought 进确认,c>N 点「-」
        (弹窗默认 1,理论上 c<=N 恒成立,减号分支为兜底)。数量读取带价格
        互推兜底:单价确立后,数量 OCR 噪声轮由「价格整除单价」反推。

        礼包确认形态(协议商店,无数量滑条):数量恒 1,打开即视为 COUNT_READY。
        """
        if self._popup_is_gift:
            if not self._gift_popup_visible():
                return self.round_fail('礼包弹窗已不在屏(被意外关闭?),中止调整')
            self._bought = 1
            return self.round_success(status='COUNT_READY', wait=1)
        if not self._popup_opened:
            return self.round_retry('弹窗未打开,等待画面稳定', wait=1)
        if not self._exchange_popup_visible():
            return self.round_fail('兑换弹窗已不在屏(被意外关闭?),中止调整')
        anchor = self._popup_quantity_anchor()
        if anchor is None:
            return self.round_retry('兑换数量标签未定位到,重试', wait=1)
        status_bar = self._popup_status_bar()
        if status_bar is not None:
            keyword, status = status_bar
            self._click_area_center(_POPUP_SCREEN, _AREA_CANCEL)
            return self.round_fail(
                f'弹窗出现不可购横条「{keyword}」,已点取消({status})', data={
                    'goods': self._goods, 'fail_status': status})
        price = parse_count(self._popup_price_text(anchor))
        current: int | None = parse_count(
            self._area_count_text(self.last_screenshot, _POPUP_SCREEN, _AREA_COUNT))
        if current is None and price is not None and self._unit_price is not None \
                and self._unit_price > 0 and price % self._unit_price == 0:
            # 数量 OCR 噪声兜底:弹窗价格恒 = 单价×数量(实测数量 4 全图/裁剪
            # 双读皆败、价格 '800' 稳定),整除反推数量;非整除视为垃圾值不采用。
            current = price // self._unit_price
        if current is None and price is not None:
            # 数量与单价双盲(重入弹窗即遇噪声数字,单价无法由「成功读数×价格」
            # 自举):+ 一击测单价——点前记价,下一轮价差=单价;价差 0 = 已到
            # 滑条顶,数量与单价由上限条(单次兑换上限N张)反推。目标过冲会被
            # 减号分支走回,无多买风险(确认仅在 current==count 时发生)。
            cap = self._slider_cap()
            if self._probe_price is not None and price == self._probe_price:
                if cap is not None:
                    self._unit_price = max(1, price // cap)
                    current = cap
            elif self._probe_price is not None and price > self._probe_price:
                self._unit_price = price - self._probe_price
                current = price // self._unit_price
            if current is None:
                self._probe_price = price
                self.ctx.controller.click(Point(_PLUS_X, anchor.y + _ROW_DY),
                                          press_time=0.1)
                return self.round_retry('数量不可读,+一击测单价,下一轮对价差',
                                        wait=1.5)
        if current is None:
            return self.round_retry('兑换数量读取失败,重试', wait=1)
        if self._monthly_left is None:
            monthly_text = self._area_text(self.last_screenshot, _POPUP_SCREEN,
                                           _AREA_POPUP_MONTHLY)
            if monthly_text is not None and '可兑换' in monthly_text:
                self._monthly_left = parse_monthly_left(monthly_text)
                if self._monthly_left is None:
                    return self.round_retry('月限剩余读取失败,重试', wait=1)
        if self._unit_price is None:
            if price is None:
                return self.round_retry('弹窗价格读取失败,重试', wait=1)
            self._unit_price = max(1, round(price / current))
            if (self._count is not None and self._pre_balance is not None
                    and self._count * self._unit_price > self._pre_balance):
                return self.round_fail(
                    f'余额不足:购买 {self._count} × {self._unit_price} 超过余额 '
                    f'{self._pre_balance},不截断执行;如需拉满请传 count=None',
                    data={'goods': self._goods,
                          'fail_status': 'INSUFFICIENT_MATERIALS'})
        if self._count is None:
            # 拉满点滑条到顶后重复点击无效;但「数量同值」有两种可能——已到顶,
            # 或该次点击丢失。首轮同值再点一次,连续两轮同值才判到顶
            # (含「余额/月限只够 1 张」的 1 张顶格形态,不能用 >1 判生效)
            if current == self._last_pull_count:
                if self._pull_confirmed:
                    self._bought = current
                    return self.round_success(status='COUNT_READY', wait=1)
                self._pull_confirmed = True
                self.ctx.controller.click(Point(_MAX_X, anchor.y + _ROW_DY),
                                          press_time=0.1)
                return self.round_retry('数量同值,复点拉满区分到顶/丢点', wait=1.5)
            self._last_pull_count = current
            self._pull_confirmed = False
            self.ctx.controller.click(Point(_MAX_X, anchor.y + _ROW_DY),
                                      press_time=0.1)
            return self.round_retry('已点拉满,下一轮读数验证', wait=1.5)
        if self._monthly_left is not None and self._count > self._monthly_left:
            return self.round_fail(
                f'购买 {self._count} 超本期限剩余额度({self._monthly_left}),'
                f'不截断执行;如需全换请传 count=None(拉满)',
                data={'goods': self._goods,
                      'fail_status': 'INSUFFICIENT_MATERIALS'})
        if current == self._count:
            self._bought = current
            return self.round_success(status='COUNT_READY', wait=1)
        if current < self._count:
            self.ctx.controller.click(Point(_PLUS_X, anchor.y + _ROW_DY),
                                      press_time=0.1)
        else:
            self.ctx.controller.click(Point(_MINUS_X, anchor.y + _ROW_DY),
                                      press_time=0.1)
        return self.round_retry(f'当前数量 {current},向目标 {self._count} 调整中',
                                wait=0.6)

    @node_from(from_name='调整数量', status='COUNT_READY')
    @operation_node(name='确认购买', node_max_retry_times=15)
    def confirm(self) -> OperationRoundResult:
        """点确认,until 购买弹窗消失(转移验证:弹窗锚不在 = 确认已生效)。

        弹窗消失后的画面收敛(4星光锥全屏展示动画/获得物品弹窗/回列表)由
        下一节点统一分类处理,本节点只负责「确认已生效」这一件事。
        """
        if self._popup_is_gift:
            if self._gift_popup_visible():
                self._click_area_center(_GIFT_SCREEN, _AREA_GIFT_CONFIRM)
                return self.round_retry('确认未生效,礼包弹窗仍在,重点确认', wait=1.5)
            return self.round_success(status='CONFIRMED', wait=1.5)
        if self._exchange_popup_visible():
            if self.node_clicked:
                self._confirm_wait_rounds += 1
                if self._confirm_wait_rounds > _CONFIRM_MAX_WAIT_ROUNDS:
                    return self.round_fail(
                        '已点确认但兑换弹窗未消失(连等封顶)——确认可能未生效,'
                        '不判定购买结果')
            status_bar = self._popup_status_bar()
            if status_bar is not None:
                keyword, status = status_bar
                self._click_area_center(_POPUP_SCREEN, _AREA_CANCEL)
                return self.round_fail(
                    f'弹窗出现不可购横条「{keyword}」,已点取消({status})', data={
                        'goods': self._goods, 'fail_status': status})
            result = self.round_by_find_and_click_area(
                self.last_screenshot, _POPUP_SCREEN, _AREA_CONFIRM,
                until_not_find_all=[(_POPUP_SCREEN, _AREA_POPUP_MARK)],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5)
            if result.is_success:
                return self.round_success(status='CONFIRMED', wait=1.5)
            return result
        # 弹窗已不在屏(重入:上一轮确认已生效),直接放行进收尾
        return self.round_success(status='CONFIRMED', wait=1)

    @node_from(from_name='确认购买', status='CONFIRMED')
    @operation_node(name='后购收尾', node_max_retry_times=60)
    def post_confirm(self) -> OperationRoundResult:
        """确认生效后的画面收敛:识别回商店页即终验,其余画面一律点右上角。

        后购画面不可枚举(4星光锥全屏展示动画/获得物品弹窗/过渡帧),共性 =
        右上角为跳过键或「点击空白处关闭」可关区,点 _SKIP_POS 一笔通吃;
        点击严格放在画面识别为非商店页之后,不做盲点。预算烧尽时购买可能
        已完成,失败信息带尽力读的余额供人工对账。
        """
        self._post_rounds += 1
        if self.check_and_update_current_screen(
                screen_name_list=[self._shop_screen]) == self._shop_screen:
            balance_left = parse_count(self._area_count_text(
                self.last_screenshot, self._shop_screen, _AREA_CURRENCY))
            if (self._pre_balance is not None and self._unit_price is not None
                    and self._bought is not None):
                expected = self._pre_balance - self._unit_price * self._bought
                if balance_left is None or abs(balance_left - expected) > _BALANCE_TOLERANCE:
                    return self.round_retry(
                        f'余额终验不符:期望 {expected},实读 {balance_left};重试',
                        wait=1.5)
            monthly_left = self._rescan_monthly_left()
            return self.round_success(status='PURCHASED', data={
                'goods': self._goods,
                'tab': self._tab,
                'bought': self._bought,
                'unit_price': self._unit_price,
                'balance_left': balance_left,
                'monthly_left': monthly_left,
            }, wait=1)
        if self._post_rounds >= _POST_MAX_ROUNDS:
            return self.round_fail(
                '已点确认与右上角跳过,画面未回商店页——购买可能已完成,'
                '余额与到货请人工核对', data={
                    'balance_left': parse_count(self._area_count_text(
                        self.last_screenshot, self._shop_screen, _AREA_CURRENCY)),
                })
        self.ctx.controller.click(_SKIP_POS, press_time=0.1)
        return self.round_retry('后购画面(展示动画/获得物品弹窗),点右上角跳过/空白',
                                wait=1.5)

    def _scan_goods(self, screen) -> tuple[Rect | None, str]:
        """商品列表区 OCR 扫描,返回 (目标卡槽位 rect 或 None, 本帧全文)。

        定位逻辑在 shop_goods_scan.locate_cards(单一源,识别器共用),
        本方法只做单目标过滤与全文拼接。
        """
        area = self.ctx.screen_loader.get_area(self._shop_screen, _AREA_LIST_REGION)
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(
            screen, rect=area.rect)
        full_text = ''.join(result.data for result in ocr_result_list)
        cards = locate_cards(ocr_result_list, {self._goods_cn})
        return cards.get(self._goods_cn), full_text

    def _read_badge_state(self, card_rect: Rect) -> str | None:
        """读目标卡左上角限额角标,返回不可购态关键词;可购/读不出返回 None。

        不可购卡的弹窗确认按钮禁用(实机售罄形态),进弹窗也无法购买,
        在列表页即拦截。
        """
        text = self._ocr_rect_text(
            screen=self.last_screenshot, rect=self._badge_rect(card_rect))
        if text is None:
            return None
        for keyword in _BADGE_UNAVAILABLE_KEYWORDS:
            if keyword in text:
                return keyword
        return None

    def _badge_rect(self, card_rect: Rect) -> Rect:
        """卡槽位 rect → 左上角限额角标区 rect(实现见 shop_goods_scan)。"""
        return _badge_rect_of(card_rect)

    def _popup_status_bar(self) -> tuple[str, str] | None:
        """读弹窗状态横条,返回 (关键词, fail status);无横条返回 None。

        「已售罄」「兑换材料不足」横条出现时确认按钮无效,点取消诚实失败。
        """
        text = self._area_text(self.last_screenshot, _POPUP_SCREEN,
                               _AREA_POPUP_STATUS_BAR)
        if text is None:
            return None
        for keyword, status in _POPUP_STATUS_KEYWORDS:
            if keyword in text:
                return keyword, status
        return None

    def _popup_quantity_anchor(self) -> Point | None:
        """弹窗中部控件行锚:「兑换数量：N」标签 OCR 框中心;未定位返回 None。

        弹窗中部布局随描述文字行数浮动(见模块常量区标定说明),固定矩形
        撑不住;标签为弹窗结构元素,两变体相对偏移一致,故以它为锚。
        """
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(
            self.last_screenshot)
        for result in ocr_result_list:
            text = result.data or ''
            if '兑换数量' in text:
                return result.center
        return None

    def _popup_price_text(self, anchor: Point) -> str | None:
        """锚推导价格读区内的 OCR 文本(空 = None)。"""
        rect = Rect(anchor.x + _PRICE_RECT_REL[0], anchor.y + _PRICE_RECT_REL[1],
                    anchor.x + _PRICE_RECT_REL[2], anchor.y + _PRICE_RECT_REL[3])
        return self._ocr_rect_text(self.last_screenshot, rect)

    def _slider_cap(self) -> int | None:
        """读弹窗上限条「单次兑换上限N张」的 N;无此条(月限型弹窗)返回 None。

        与 :meth:`_popup_status_bar` 同 area:上限条关键词不在不可购关键词
        集合内,两条互不误触。
        """
        text = self._area_text(self.last_screenshot, _POPUP_SCREEN,
                               _AREA_POPUP_STATUS_BAR)
        if text is None:
            return None
        m = re.search(r'上限\s*(\d+)\s*张', text)
        return int(m.group(1)) if m is not None else None

    def _rescan_monthly_left(self) -> int | None:
        """购买后重扫列表读目标卡月限角标(软终验)。

        列表未滚动时卡在原槽位;期限商品换光会重排列表(换光卡滞留列表
        末尾),重扫不命中时返回 None 并记日志,不作硬校验。
        """
        card_rect, _ = self._scan_goods(self.last_screenshot)
        if card_rect is None:
            log.info('购买后列表重定位未命中目标卡(可能已换光重排),'
                     '月限剩余以弹窗前读数为准')
            return None
        badge_text = self._ocr_rect_text(
            screen=self.last_screenshot, rect=self._badge_rect(card_rect))
        return parse_monthly_left(badge_text)

    def _top_row_visible(self) -> bool:
        """列表顶行(吸附后标准首行)是否有商品名:回顶判定辅助。

        顶行卡顶恒定(吸附列表顶部=tab 栏下方),商品名中心 = 卡顶+
        _NAME_OFFSET_FROM_TOP → 顶行名字带固定;顶行不可见说明列表未到顶
        (顶部截断态)或拖拽无效。
        """
        area = self.ctx.screen_loader.get_area(self._shop_screen, _AREA_LIST_REGION)
        y_center = area.rect.y1 + _NAME_OFFSET_FROM_TOP
        y_low = y_center - 25
        y_high = y_center + 35
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(
            self.last_screenshot, rect=area.rect)
        return any(y_low <= result.center.y <= y_high
                   for result in ocr_result_list)

    def _click_area_center(self, screen_name: str, area_name: str) -> None:
        """点指定 area 中心(press_time=0.1,点击有效性由调用方轮询验证)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        self.ctx.controller.click(area.center, press_time=0.1)

    def _click_rect_center(self, screen_name: str, rect: Rect) -> None:
        """点推演 rect 中心(商品卡槽位无独立建档 area,由网格几何推演)。"""
        self.ctx.controller.click(rect.center, press_time=0.1)

    def _exchange_popup_visible(self) -> bool:
        """兑换弹窗在屏证据:「兑换数量」关键词命中弹窗锚 area。"""
        text = self._area_text(self.last_screenshot, _POPUP_SCREEN, _AREA_POPUP_MARK)
        return text is not None and '兑换数量' in text

    def _gift_popup_visible(self) -> bool:
        """礼包确认弹窗(协议商店)在屏证据:「购买后立刻获得」关键词命中。"""
        text = self._area_text(self.last_screenshot, _GIFT_SCREEN, _AREA_GIFT_MARK)
        return text is not None and '购买后立刻获得' in text

    def _area_text(self, screen, screen_name: str, area_name: str) -> str | None:
        """读画面建档 area 内的 OCR 文本(空 = None)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        return self._ocr_rect_text(screen=screen, rect=area.rect)

    def _ocr_rect_text(self, screen, rect: Rect) -> str | None:
        """读指定 rect 的 OCR 文本(实现见 shop_goods_scan 单一源)。"""
        return _ocr_rect_text_of(self.ctx.ocr_service, screen, rect)

    def _area_count_text(self, screen, screen_name: str, area_name: str) -> str | None:
        """读数量型 area:两层取数(实现见 shop_goods_scan 单一源,强化版口径)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        return _read_count_two_pass_of(self.ctx.ocr_service, self.ctx.ocr,
                                       screen, area)
