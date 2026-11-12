"""兑换商店按商品名购买 —— 常驻商店·兑换商店(Exchange Shop)通用购买 op。

效果:按传入的商品名在兑换商店购买指定数量,画面停在商店列表页,
购买结果(实际数量/单价/余额/月限剩余)经运行结果 data 返回。
起点:商店页常驻商店任意 tab(列表滚动位任意,op 自行回顶;或兑换弹窗重入);
终点:商店页目标 tab 列表页。
副作用:消耗星芒/余烬等兑换材料,不可逆。仅限用户明确授权的购买请求调用。

兑换商店五个 tab(星芒兑换/余烬兑换/星尘之礼/光锥呈现/戏言成真)共用同一
画面结构(6 列商品网格 + 同款兑换弹窗),本 op 的流程与 tab 无关;tab 差异
只体现在切换锚(:class:`ShopSwitchTabOp`)与商品清单(:data:`_GOODS_META`),
新 tab 启用 = 补锚建档 + 加映射条目,不改本类代码。当前实测开放星芒/余烬。

:param goods: 商品英文标识符(官方英文名主体词 snake_case),如 ``pass``(星轨
    通票 Star Rail Pass)/``special_pass``(星轨专票)/``tracks_of_destiny``
    (命运的足迹);未注册的标识符构造时抛 ValueError 并列出可用值。
    同名商品在双 tab 在售时(票类三件套)默认指余烬月限渠道——折扣价优先
    用完月度额度;要走星芒不限量渠道须显式传 ``tab='starlight'``。
:param count: 购买数量;``None`` = 拉满(受月限剩余与余额共同限制)。
    指定数量超月限剩余或超余额时**直接失败,不静默截断**——静默减量违背
    用户意图,须显式失败让调用方改传拉满或减量。
:param tab: 目标 tab,``embers``=余烬兑换 / ``starlight``=星芒兑换;
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
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.cultivation.account.operations.read_warp_status import (
    parse_count,
)
from sr_od.application.cultivation.account.operations.shop_switch_tab import (
    TAB_EMBERS,
    TAB_STARLIGHT,
    ShopSwitchTabOp,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_ALLOWED_TABS: set[str] = {TAB_EMBERS, TAB_STARLIGHT}

_SHOP_SCREEN: str = '商店'
_POPUP_SCREEN: str = '商店-兑换弹窗'

_AREA_LIST_REGION: str = '商品列表'
_AREA_POPUP_MARK: str = '文本-兑换数量'
_AREA_POPUP_TITLE: str = '读区-弹窗商品名'
_AREA_POPUP_MONTHLY: str = '读区-弹窗月限剩余'
_AREA_POPUP_PRICE: str = '读区-弹窗价格'
_AREA_POPUP_STATUS_BAR: str = '文本-弹窗状态横条'
_AREA_CONFIRM: str = '按钮-确认'
_AREA_CANCEL: str = '按钮-取消'
_AREA_PLUS: str = '按钮-加号'
_AREA_MINUS: str = '按钮-减号'
_AREA_MAX: str = '按钮-拉满'
_AREA_COUNT: str = '读区-兑换数量'
_AREA_CURRENCY: str = '读区-货币数量'
_AREA_REWARD_MARK: str = '文本-获得物品'
_REWARD_CLOSE_POS: Point = Point(100, 1000)
"""关闭「获得物品」奖励弹窗的遮罩点击点:遮罩任意处可关,但关闭瞬间存在
穿透竞态(遮罩销毁后释放事件落下层),落点必须在商品卡网格与左侧菜单之外
的无元素空白区。买 1 件也会弹奖励弹窗(实机双样本),确认后必查此分支。"""

# 商品网格几何(1080p):6 列 × N 行,列距 245、卡宽约 216。列位置固定不随
# 滚动变,行位置随滚动吸附态漂移(常规行距 325,列表底部对齐态行位偏移)——
# 目标卡定位 = 名字文本中心归列 + 名字中心反推卡顶(商品名在卡内垂直偏移
# 恒定,与滚动态无关),任意吸附态均可定位。
_GRID_COL_WINDOWS: list[tuple[int, int]] = [
    (305, 560), (550, 805), (795, 1050),
    (1040, 1295), (1285, 1540), (1530, 1785),
]
_CARD_WIDTH: int = 216
_CARD_HEIGHT: int = 285
_NAME_OFFSET_FROM_TOP: int = 195
"""商品名文本框中心相对卡顶的垂直偏移(1080p 实测标定,标定样本见
test_shop_buy_goods 流程测试素材)"""
_LIST_Y_MIN: int = 110
"""卡顶反推的合理上界(列表区上沿之上视为异帧残留,拒绝)"""
# 卡左上角限额角标区(「可兑换 X/Y」/「已达上限」/「已售罄」/「未解锁」),
# 按卡槽 rect 推演;角标为悬挂样式(文字框左缘超出卡左缘约 25px,实拍标定),
# x1 需左移容纳;窗口 y 不盖住角标下方的倒计时文本框
_BADGE_OFFSET: tuple[int, int, int, int] = (-25, 8, 175, 52)
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
_BADGE_UNAVAILABLE_KEYWORDS: tuple[str, ...] = ('已售罄', '已达上限', '未解锁')
# 弹窗状态横条(与列表角标同源的不可购提示,弹窗内出现时点取消诚实失败)
_POPUP_STATUS_KEYWORDS: tuple[tuple[str, str], ...] = (
    ('已售罄', 'SOLD_OUT'),
    ('兑换材料不足', 'INSUFFICIENT_MATERIALS'),
)

_TITLE_MATCH_LCS: float = 0.8
"""弹窗商品名校验的 LCS 兜底阈值:弹窗标题字体有异体字形态(实测「命运的
足迹」标题 OCR 为「命运的足跡」,LCS=0.8);阈值须高于易混对的相似度
(星轨通票/星轨专票 LCS=0.75,低于阈值不误放行)"""


def _is_target_popup_title(title: str | None, goods_cn: str) -> bool:
    """弹窗商品名与目标关键词匹配:包含优先,异体字形态走 LCS 兜底。"""
    if not title:
        return False
    return (goods_cn in title
            or str_utils.find_by_lcs(goods_cn, title,
                                     percent=_TITLE_MATCH_LCS))


_COUNT_OCR_SCALE: float = 3.0
"""数量型 area 的 OCR 放大倍数(单字符数字兜底,同 ReadWarpStatusOp 口径)"""
"""数量型 area 的 OCR 放大倍数(单字符数字兜底,同 ReadWarpStatusOp 口径)"""
_BALANCE_TOLERANCE: int = 2
"""余额差值终验容差(顶部货币读数的 OCR 个位抖动)"""

_GOODS_META: dict[str, tuple[str, str]] = {
    # 英文标识符(官方英文名主体词) → (默认 tab, 商品名 OCR 关键词)
    # 关键词 = 卡面商品名的唯一子串(去书名号/逗号等装饰,防 OCR 抖动)
    # ——对照表来源:2026-11-12 实机中英双态走查(见 .debug/temp/operation-explore/
    #   2026-11-12-shop-buy-goods/screen-flow.md,永久副本归档后指针随测试固化)
    'special_pass': (TAB_EMBERS, '星轨专票'),
    'pass': (TAB_EMBERS, '星轨通票'),
    'tracks_of_destiny': (TAB_EMBERS, '命运的足迹'),
    'adventure_log': (TAB_EMBERS, '冒险记录'),
    'condensed_aether': (TAB_EMBERS, '凝缩以太'),
    'lost_gold_fragment': (TAB_EMBERS, '遗失碎金'),
    'credit': (TAB_EMBERS, '信用点'),
    'key_of_knowledge': (TAB_EMBERS, '启迪之钥'),
    # 3 星光锥残器(30/版本,18 余烬)
    'lifeless_blade': (TAB_EMBERS, '无生残刃'),
    'arrow_of_the_demon_slayer': (TAB_EMBERS, '屠魔之矢'),
    'oath_of_steel': (TAB_EMBERS, '寒铁的誓言'),
    'obsidian_of_desolation': (TAB_EMBERS, '虚空黑曜'),
    'ancestral_hymn': (TAB_EMBERS, '家族颂歌'),
    'sprout_of_life': (TAB_EMBERS, '生命之芽'),
    'lupitoxin_sawteeth': (TAB_EMBERS, '狼毒锯牙'),
    'destined_expiration': (TAB_EMBERS, '命定死因'),
    'dynamic_outlining': (TAB_EMBERS, '动态线稿'),
    'crystal_meteorites': (TAB_EMBERS, '流星棱晶'),
    'starfire_essence': (TAB_EMBERS, '星火之精'),
    'celestial_section': (TAB_EMBERS, '空际小节'),
    'nourishing_honey': (TAB_EMBERS, '滋长花蜜'),
    'seedling_of_manas': (TAB_EMBERS, '末那芽苗'),
    'the_fluffy_serialization_memorial_issue': (TAB_EMBERS, '连载纪念刊'),
    'resin_of_valor': (TAB_EMBERS, '战魂血珀'),
    'wine_of_phagousa': (TAB_EMBERS, '法吉娜之酒'),
    'galaxy_framework': (TAB_EMBERS, '星系框桇'),
    'sixen_king_rook_fork': (TAB_EMBERS, '王手飞车'),
    # 2 星养成材料(20/版本,12 余烬)
    'shattered_blade': (TAB_EMBERS, '破碎残刃'),
    'arrow_of_the_beast_hunter': (TAB_EMBERS, '猎兽之矢'),
    'key_of_inspiration': (TAB_EMBERS, '灵感之钥'),
    'endurance_of_bronze': (TAB_EMBERS, '青铜的执着'),
    'obsidian_of_dread': (TAB_EMBERS, '黯淡黑曜'),
    'harmonic_tune': (TAB_EMBERS, '谐乐小调'),
    'seed_of_abundance': (TAB_EMBERS, '丰饶之种'),
    'borisin_teeth': (TAB_EMBERS, '步离犬牙'),
    'meteoric_bullet': (TAB_EMBERS, '陨铁弹丸'),
    'rough_sketch': (TAB_EMBERS, '凌乱草图'),
    'scattered_stardust': (TAB_EMBERS, '散逸星砂'),
    'fiery_spirit': (TAB_EMBERS, '炽情之灵'),
    'firmament_note': (TAB_EMBERS, '云际音符'),
    'alien_tree_seed': (TAB_EMBERS, '异木种籽'),
    'bija_of_consciousness': (TAB_EMBERS, '思量的种'),
    'the_fluffy_hand_drawn_storyboards': (TAB_EMBERS, '手绘分镜稿'),
    'grit_of_strife': (TAB_EMBERS, '纷争血尘'),
    'tear_of_phagousa': (TAB_EMBERS, '法吉娜之泪'),
    'celestial_globe': (TAB_EMBERS, '天体模型'),
    'four_phases_crossing_the_river_to_check_the_king': (TAB_EMBERS, '过河照君'),
    # 周限遗器材料(40/周,4 余烬)
    'extinguished_core': (TAB_EMBERS, '熄灭原核'),
    'thiefs_instinct': (TAB_EMBERS, '掠夺的本能'),
    'silvermane_badge': (TAB_EMBERS, '铁卫扣饰'),
    'ancient_part': (TAB_EMBERS, '古代零件'),
    'immortal_scionette': (TAB_EMBERS, '永寿幼芽'),
    'artifexs_module': (TAB_EMBERS, '工造机杼'),
    'dream_collection_component': (TAB_EMBERS, '蓄梦元件'),
    'tatters_of_thought': (TAB_EMBERS, '思绪末屑'),
    'fear_stomped_flesh': (TAB_EMBERS, '恐惧踏碎血肉'),
    'ethereal_omen': (TAB_EMBERS, '预兆似有若无'),
    'whimsy_wax': (TAB_EMBERS, '童真蜡笔'),
    # 星芒兑换 tab 专属(600 星芒/版本 1 个;140 档已达上限形态同角标拦截)
    'night_on_the_milky_way': (TAB_STARLIGHT, '银河铁道之夜'),
    'something_irreplaceable': (TAB_STARLIGHT, '无可取代的东西'),
    'but_the_battle_isnt_over': (TAB_STARLIGHT, '但战斗还未结束'),
    'in_the_name_of_the_world': (TAB_STARLIGHT, '以世界之名'),
    'moment_of_victory': (TAB_STARLIGHT, '制胜的瞬间'),
    'sleep_like_the_dead': (TAB_STARLIGHT, '如泥酣眠'),
    'time_waits_for_no_one': (TAB_STARLIGHT, '时节不居'),
    'dan_heng': (TAB_STARLIGHT, '丹恒'),
    'serval': (TAB_STARLIGHT, '希露瓦'),
}


def parse_monthly_left(text: str | None) -> int | None:
    """「可兑换 X/Y」月限文本 → 剩余次数 X。

    斜杠对须用 ``\\d+\\s*/\\s*\\d+`` 分别取值——get_positive_digits 对「5/5」
    会取成 55(同 ShopSwitchTabOp 口径);X 为本期限剩余可兑换数。
    """
    if not text:
        return None
    m = re.search(r'(\d+)\s*/\s*(\d+)', text)
    if m is None:
        return None
    return int(m.group(1))


class ExchangeShopBuyGoods(SrOperation):
    """按商品名在兑换商店购买指定数量。
    起点:商店页常驻商店任意 tab(或兑换弹窗重入);终点:商店页目标 tab 列表页。
    副作用:消耗星芒/余烬等兑换材料,不可逆;仅限用户明确授权的购买请求调用。

    结果状态:
    - ``PURCHASED``:购买完成回列表页,data 带 ``goods``/``tab``/``bought``
      (实际购买数量)/``unit_price``(单价)/``balance_left``(购买后余额)/
      ``monthly_left``(期限限购商品的购买后剩余额度;不限量商品为 None);
    失败:起点不在商店页、商品标识符未注册、tab 切换失败、商品不在列表
    (滚动到底未命中)、目标卡不可购(已售罄/已达上限/未解锁)、弹窗状态
    横条(售罄/兑换材料不足)、数量超月限或超余额(不截断)、数量调不到
    目标、确认未生效、余额差值终验不符。
    """

    def __init__(self, ctx: SrContext, goods: str, count: int | None = None,
                 tab: str | None = None, scroll_search: bool = True):
        """
        :param ctx: 上下文
        :param goods: 商品英文标识符,见类 docstring(未注册抛 ValueError)
        :param count: 购买数量;``None`` = 拉满。**消耗参数:仅限用户明确授权的购买请求传入。**
        :param tab: 目标 tab;``None`` = 按 :data:`_GOODS_META` 默认
        :param scroll_search: 商品不在首屏时是否滚动扫描(默认 True)
        """
        meta = _GOODS_META.get(goods)
        if meta is None:
            raise ValueError(
                f'未注册的商品标识符: {goods}(可用: {sorted(_GOODS_META)})')
        resolved_tab = meta[0] if tab is None else tab
        if resolved_tab not in _ALLOWED_TABS:
            raise ValueError(
                f'不支持的 tab: {resolved_tab}(仅支持 embers/starlight)')
        if count is not None and count <= 0:
            raise ValueError(f'count 必须为正数或 None(拉满),收到: {count}')

        self._goods: str = goods
        self._goods_cn: str = meta[1]
        self._tab: str = resolved_tab
        self._count: int | None = count
        self._scroll_search: bool = scroll_search

        self._popup_opened: bool = False
        """弹窗已打开(数量调整/确认节点的前置判据)"""
        self._pre_balance: int | None = None
        """购买前列表页货币余额(余额差值终验基准;弹窗重入场景读不到则为 None,终验降级为软读数)"""
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
        SrOperation.__init__(self, ctx, op_name=gt('兑换商店购买'),
                             node_max_retry_times=60)

    @operation_node(name='准备tab', is_start_node=True)
    def setup_tab(self) -> OperationRoundResult:
        """入口画面级判定,分发:商店页 → 子 op 切 tab 后进扫描;弹窗 → 商品名核验后直接调数量。

        画面不在预期集合直接失败(不做逐 area 试命中推断);切 tab 复用
        ShopSwitchTabOp(自带目标 tab 选中态模板锚验证)。注意:目标 tab 已是
        当前 tab 时点击幂等、列表**不回顶**(回顶由 reset_scroll 节点负责)。
        """
        screen = self.check_and_update_current_screen(screen_name_list=[
            _SHOP_SCREEN, _POPUP_SCREEN])
        if screen == _POPUP_SCREEN:
            title = self._area_text(self.last_screenshot, _POPUP_SCREEN,
                                    _AREA_POPUP_TITLE)
            if not _is_target_popup_title(title, self._goods_cn):
                return self.round_fail(
                    f'当前兑换弹窗不是目标商品 {self._goods_cn}(弹窗商品名: '
                    f'{title or "未识别"}),请先关闭该弹窗再重试')
            self._popup_opened = True
            return self.round_success(status='POPUP_OPENED', wait=1)
        if screen != _SHOP_SCREEN:
            return self.round_fail('起点不在商店页,请先导航到商店(常驻商店)')
        # 前台点击/拖拽要求游戏窗口激活:窗口失焦时手势落在窗外全部无效
        # (实机对照:MCP 工具每次 active_window 后有效,op 中途失焦后无效)
        self.ctx.controller.active_window()
        switch_op = ShopSwitchTabOp(self.ctx, tab=self._tab)
        switch_result = switch_op.execute()
        if not switch_result.success:
            return self.round_fail(f'切换到目标 tab 失败: {switch_result.status}')
        return self.round_success(status='TAB_READY', wait=0.5)

    @node_from(from_name='准备tab', status='TAB_READY')
    @operation_node(name='回顶列表', node_max_retry_times=20)
    def reset_scroll(self) -> OperationRoundResult:
        """扫描前把商品列表回滚到顶:起点滚动位置不定(上一 op 可能留在中途),
        从顶部起扫才能覆盖全列表。回顶 = 手指下滑(内容上移),拖一次 → 等吸附
        → OCR 全文对比判静止,连续静止即到顶——连发拖拽会被后续手势打断
        吸附,净位移只剩最后一拖,不能一次拖到位。

        拖拽 x 取列表右缘空白带(第 6 列卡右缘之外):卡面手势可能被判定为
        点击卡而非列表滚动。duration ≥0.5:更快的快速手势不被识别为拖拽
        (实机对照,同参数 0.5 有效 0.3 无效)。
        """
        area = self.ctx.screen_loader.get_area(_SHOP_SCREEN, _AREA_LIST_REGION)
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
            self.last_screenshot, _SHOP_SCREEN, _AREA_CURRENCY))
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
            return self.round_success(status='POPUP_OPENED', wait=1)
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
                    f'可能未在售或本期额度形态变化)')
            if not self._scroll_search:
                return self.round_fail(
                    f'首屏未找到商品 {self._goods_cn}(scroll_search=False 不滚动)')
            if self._scroll_rounds >= _SCROLL_MAX_ROUNDS:
                return self.round_fail(
                    f'滚动 {_SCROLL_MAX_ROUNDS} 次仍未找到商品 {self._goods_cn},中止')
            return self.round_success(status='SCROLL_NEXT', wait=0.5)
        unavailable = self._read_badge_state(card_rect)
        if unavailable is not None:
            return self.round_fail(
                f'目标商品卡不可购(角标: {unavailable})', data={
                    'goods': self._goods_cn})
        self._card_rect = card_rect
        self._click_rect_center(_SHOP_SCREEN, card_rect)
        return self.round_retry('已点商品卡,下一轮验证兑换弹窗', wait=1.5)

    @node_from(from_name='定位商品', status='SCROLL_NEXT')
    @operation_node(name='滚动一格')
    def scroll_next(self) -> OperationRoundResult:
        """列表区右缘空白带上滑一格(行吸附),回定位商品重扫。

        拖拽 x 同 reset_scroll 取列表右缘空白带,避免手势落在商品卡上。
        """
        area = self.ctx.screen_loader.get_area(_SHOP_SCREEN, _AREA_LIST_REGION)
        start = Point(area.rect.x2 - 60, area.center.y)
        end = Point(area.rect.x2 - 60, area.center.y - _SCROLL_STEP)
        self.ctx.controller.drag_to(end, start, duration=0.8)
        self._scroll_rounds += 1
        return self.round_success(status='SCROLLED', wait=1)

    @node_from(from_name='准备tab', status='POPUP_OPENED')
    @node_from(from_name='定位商品', status='POPUP_OPENED')
    @operation_node(name='调整数量', node_max_retry_times=40)
    def adjust_count(self) -> OperationRoundResult:
        """按 count 调整兑换数量,完成时记录实际数量与单价,进入确认。

        count=None:点「拉满」一键到滑条上限(期限商品=月限剩余,不限量商品
        受余额截断),两轮读数同值判到顶(余额/月限只够 1 张时 current==1 也
        是终态,不能用 >1 判生效);count=N:先做月限与余额预判(超限 fail 不
        截断),再读当前数量 c,c<N 点「+」,c==N 记 bought 进确认,c>N 点「-」
        (弹窗默认 1,理论上 c<=N 恒成立,减号分支为兜底)。
        """
        if not self._popup_opened:
            return self.round_retry('弹窗未打开,等待画面稳定', wait=1)
        if not self._exchange_popup_visible():
            return self.round_fail('兑换弹窗已不在屏(被意外关闭?),中止调整')
        status_bar = self._popup_status_bar()
        if status_bar is not None:
            keyword, status = status_bar
            self._click_area_center(_POPUP_SCREEN, _AREA_CANCEL)
            return self.round_fail(
                f'弹窗出现不可购横条「{keyword}」,已点取消({status})')
        current: int | None = parse_count(
            self._area_count_text(self.last_screenshot, _POPUP_SCREEN, _AREA_COUNT))
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
            price_text = self._area_text(self.last_screenshot, _POPUP_SCREEN,
                                         _AREA_POPUP_PRICE)
            price = parse_count(price_text)
            if price is None:
                return self.round_retry('弹窗价格读取失败,重试', wait=1)
            self._unit_price = max(1, round(price / current))
            if (self._count is not None and self._pre_balance is not None
                    and self._count * self._unit_price > self._pre_balance):
                return self.round_fail(
                    f'余额不足:购买 {self._count} × {self._unit_price} 超过余额 '
                    f'{self._pre_balance},不截断执行;如需拉满请传 count=None')
        if self._count is None:
            # 拉满点滑条到顶后重复点击无效;但「数量同值」有两种可能——已到顶,
            # 或该次点击丢失。首轮同值再点一次,连续两轮同值才判到顶
            # (含「余额/月限只够 1 张」的 1 张顶格形态,不能用 >1 判生效)
            if current == self._last_pull_count:
                if self._pull_confirmed:
                    self._bought = current
                    return self.round_success(status='COUNT_READY', wait=1)
                self._pull_confirmed = True
                self._click_area_center(_POPUP_SCREEN, _AREA_MAX)
                return self.round_retry('数量同值,复点拉满区分到顶/丢点', wait=1.5)
            self._last_pull_count = current
            self._pull_confirmed = False
            self._click_area_center(_POPUP_SCREEN, _AREA_MAX)
            return self.round_retry('已点拉满,下一轮读数验证', wait=1.5)
        if self._monthly_left is not None and self._count > self._monthly_left:
            return self.round_fail(
                f'购买 {self._count} 超本期限剩余额度({self._monthly_left}),'
                f'不截断执行;如需全换请传 count=None(拉满)')
        if current == self._count:
            self._bought = current
            return self.round_success(status='COUNT_READY', wait=1)
        if current < self._count:
            self._click_area_center(_POPUP_SCREEN, _AREA_PLUS)
        else:
            self._click_area_center(_POPUP_SCREEN, _AREA_MINUS)
        return self.round_retry(f'当前数量 {current},向目标 {self._count} 调整中',
                                wait=0.6)

    @node_from(from_name='调整数量', status='COUNT_READY')
    @operation_node(name='确认购买', node_max_retry_times=15)
    def confirm(self) -> OperationRoundResult:
        """状态分派确认购买:每轮先读画面证据再决定动作,无证据不点击。

        优先级:①「获得物品」奖励弹窗(实机证实买 1 件也会弹)→ 点安全空白
        点关闭——不能点确认按钮坐标:关闭瞬间遮罩销毁、释放事件可能穿透
        下层,落在确认坐标上会误触商品卡;②兑换弹窗仍在(「兑换数量」可读)
        → 横条在则点取消诚实失败,否则重点确认;③两者都不在且画面识别为
        商店页 → 购买完成,余额差值硬校验 + 月限角标软读数终验。
        """
        # 关键词语义匹配而非非空判断:商店页正常态下同 rect 会扫到 tab 词/
        # 商品价格数字,非空判断会把正常商店页误判成弹窗在屏
        reward_text = self._area_text(self.last_screenshot, _SHOP_SCREEN,
                                      _AREA_REWARD_MARK)
        if reward_text is not None and '获得物品' in reward_text:
            self.ctx.controller.click(_REWARD_CLOSE_POS, press_time=0.1)
            return self.round_retry('获得物品弹窗,点安全空白点关闭', wait=1.5)
        if self._exchange_popup_visible():
            status_bar = self._popup_status_bar()
            if status_bar is not None:
                keyword, status = status_bar
                self._click_area_center(_POPUP_SCREEN, _AREA_CANCEL)
                return self.round_fail(
                    f'弹窗出现不可购横条「{keyword}」,已点取消({status})')
            self._click_area_center(_POPUP_SCREEN, _AREA_CONFIRM)
            return self.round_retry('确认未生效,弹窗仍在,重点确认', wait=1.5)
        if self.check_and_update_current_screen(
                screen_name_list=[_SHOP_SCREEN]) == _SHOP_SCREEN:
            balance_left = parse_count(self._area_count_text(
                self.last_screenshot, _SHOP_SCREEN, _AREA_CURRENCY))
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
        return self.round_retry('画面过渡中(未识别到弹窗或商店页),等待', wait=1.5)

    def _scan_goods(self, screen) -> tuple[Rect | None, str]:
        """商品列表区 OCR 扫描,返回 (目标卡槽位 rect 或 None, 本帧全文)。

        商品名用**包含匹配**——不引入模糊兜底:同名易混对(星轨通票/星轨
        专票一字之差)模糊匹配会误命中,后果是读错卡的角标甚至点错卡,
        比漏扫(诚实失败)严重。
        """
        area = self.ctx.screen_loader.get_area(_SHOP_SCREEN, _AREA_LIST_REGION)
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(
            screen, rect=area.rect)
        full_text = ''.join(result.data for result in ocr_result_list)
        for result in ocr_result_list:
            text = result.data or ''
            if self._goods_cn not in text:
                continue
            center = result.center
            col = self._locate_window(center.x, _GRID_COL_WINDOWS)
            if col is None:
                # 商品名文字不在任何列窗口(异帧残留等),跳过
                continue
            card_top = int(center.y) - _NAME_OFFSET_FROM_TOP
            if card_top < _LIST_Y_MIN:
                continue
            col_center = sum(_GRID_COL_WINDOWS[col]) // 2
            return Rect(col_center - _CARD_WIDTH // 2, card_top,
                        col_center + _CARD_WIDTH // 2, card_top + _CARD_HEIGHT), full_text
        return None, full_text

    def _locate_window(self, value: float,
                       windows: list[tuple[int, int]]) -> int | None:
        """值落在哪个窗口,返回下标;都不在返回 None。"""
        for idx, (low, high) in enumerate(windows):
            if low <= value <= high:
                return idx
        return None

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
        """卡槽位 rect → 左上角限额角标区 rect(窗口不盖住角标下方倒计时)。"""
        return Rect(card_rect.x1 + _BADGE_OFFSET[0],
                    card_rect.y1 + _BADGE_OFFSET[1],
                    card_rect.x1 + _BADGE_OFFSET[2],
                    card_rect.y1 + _BADGE_OFFSET[3])

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

        商品名在卡内垂直偏移恒定 → 顶行名字中心必落在标准行位附近;
        顶行不可见说明列表未到顶(顶部截断态)或拖拽无效。
        """
        area = self.ctx.screen_loader.get_area(_SHOP_SCREEN, _AREA_LIST_REGION)
        y_low = _NAME_OFFSET_FROM_TOP - 25
        y_high = _NAME_OFFSET_FROM_TOP + 35
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

    def _area_text(self, screen, screen_name: str, area_name: str) -> str | None:
        """读画面建档 area 内的 OCR 文本(空 = None)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        return self._ocr_rect_text(screen=screen, rect=area.rect)

    def _ocr_rect_text(self, screen, rect: Rect) -> str | None:
        """读指定 rect 的 OCR 文本(空 = None)。"""
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(
            screen, rect=rect)
        if len(ocr_result_list) == 0:
            return None
        return ''.join(result.data for result in ocr_result_list)

    def _area_count_text(self, screen, screen_name: str, area_name: str) -> str | None:
        """读数量型 area:两层取数——全图 OCR+rect 过滤 → 3 倍放大裁剪兜底。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(screen, rect=area.rect)
        if len(ocr_result_list) > 0:
            return ''.join(result.data for result in ocr_result_list)
        cropped = cv2_utils.crop_image_only(screen, area.rect)
        big = cv2_utils.scale_image(cropped, scale=_COUNT_OCR_SCALE)
        raw = self.ctx.ocr.run_ocr(big)
        if len(raw) == 0:
            return None
        return ''.join(raw.keys())
