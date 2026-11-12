"""商店兑换专票 op —— 商店兑换页用转化材料兑换星轨专票。

两个供货渠道(``source`` 参数):
- ``stardust`` 星芒兑换(角色转化材料):20 星芒/张,不限量,拉满受星芒余额限制;
- ``ash`` 余烬兑换(光锥转化材料):90 余烬/张,**每月限量 5 张**(按版本月历刷新),
  拉满受月限剩余与余烬余额共同限制;月限剩余读自弹窗左下「可兑换 X/5」胶囊。

⚠️ 消耗红线:兑换消耗星芒/余烬(抽卡副产物材料),仅限用户明确授权的兑换请求调用。
参数 ``count``:``None`` = 拉满全部(能换多少换多少);数字 = 兑换指定张数。
余烬渠道 count 超过月限剩余时**直接失败,不静默截断**——用户要 5 张只剩 3 张时,
静默换 3 张违背用户意图,须显式失败让调用方改传拉满或减量。

前置:已在商店页且处于 source 对应兑换 tab(经 EnterShopFromWarpOp +
ShopSwitchTabOp 到达)——本 op 不做导航与切 tab,单一职责。
两渠道商品卡同在第 1 行第 1 列槽位(``商品-星轨专票卡``),弹窗为同一建档
(``商店-兑换弹窗``,area 坐标通用);余烬弹窗仅多「可兑换 X/5」月限胶囊。

流程:校验当前 tab 与 source 匹配 → 点专票商品卡打开兑换弹窗 →
调整数量(读数→点+/拉满→读数验证)→ 点确认 → 兑换成功弹出「获得物品」
奖励弹窗(件数 ≥2 时出现,点击任意处关闭)→ 关闭回商店页 →
余烬渠道再读商品卡月限角标终验(剩余次数已按兑换量扣减)。

点击纪律(实机事故教训):所有点击必须有画面证据门——先读证据确认目标
在屏,才允许点击;点击后画面未达预期时,重试轮**先重判状态再决定是否
点击**,严禁对固定坐标盲目重试(奖励弹窗遮屏时盲点确认坐标会穿透误触
下层商品卡,引发计划外购买)。
"""


import re

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from sr_od.application.cultivation.account.operations.read_warp_status import (
    parse_count,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

SOURCE_STARDUST: str = 'stardust'
"""星芒兑换渠道(角色转化材料,20/张,不限量)"""
SOURCE_ASH: str = 'ash'
"""余烬兑换渠道(光锥转化材料,90/张,每月限量 5 张)"""
_ALLOWED_SOURCES: set[str] = {SOURCE_ASH, SOURCE_STARDUST}

_SHOP_SCREEN: str = '商店'
_POPUP_SCREEN: str = '商店-兑换弹窗'
_GOODS_TICKET_CARD: str = '商品-星轨专票卡'

# 当前兑换 tab 判定:两 tab 第 1 行第 4 列槽位商品互斥(建档 area 同 rect 不同文本),
# 读该槽位 OCR 含目标关键词即处于对应 tab
_AREA_TAB_SLOT: str = '文本-冒险记录'
_TAB_SLOT_KEYWORD: dict[str, str] = {SOURCE_ASH: '冒险', SOURCE_STARDUST: '银河铁道'}

_AREA_POPUP_MARK: str = '文本-兑换数量'
_AREA_CONFIRM: str = '按钮-确认'
_AREA_PLUS: str = '按钮-加号'
_AREA_MINUS: str = '按钮-减号'
_AREA_MAX: str = '按钮-拉满'
_AREA_COUNT: str = '读区-兑换数量'
_AREA_CURRENCY: str = '读区-货币数量'
_AREA_MONTHLY_LEFT: str = '读区-弹窗月限剩余'
"""弹窗左下「可兑换 X/5」月限胶囊(仅余烬渠道商品可见)"""
_AREA_MONTHLY_BADGE: str = '读区-专票兑换次数'
"""商店页商品卡上的「可兑换：X/5」月限角标(仅余烬渠道;确认后终验用)"""
_AREA_GOODS_TITLE: str = '读区-弹窗商品名'
"""兑换弹窗标题(「星轨专票」/「启迪之钥」等)——弹窗重入放行前校验商品身份,
防把上轮遗留的其他商品弹窗当专票弹窗接手"""
_AREA_REWARD_MARK: str = '文本-获得物品'
"""「获得物品」奖励弹窗锚(挂商店屏;件数 ≥2 的兑换确认后弹出,点击任意处关闭)"""
_REWARD_CLOSE_POS: Point = Point(100, 1000)
"""关闭奖励弹窗的点击点:遮罩任意处可关;关闭瞬间存在穿透竞态(遮罩销毁后
释放事件落下层),落点必须在商品卡网格与左侧菜单之外的无元素空白区"""

_COUNT_OCR_SCALE: float = 3.0
"""数量型 area 的 OCR 放大倍数(单字符数字兜底,同 ReadWarpStatusOp 口径)"""


def parse_monthly_left(text: str | None) -> int | None:
    """「可兑换 X/5」月限文本 → 剩余次数 X。

    斜杠对须用 ``\\d+\\s*/\\s*\\d+`` 分别取值——get_positive_digits 对「5/5」
    会取成 55(同 ShopSwitchTabOp 口径);X 为本月剩余可兑换张数。
    """
    if not text:
        return None
    m = re.search(r'(\d+)\s*/\s*(\d+)', text)
    if m is None:
        return None
    return int(m.group(1))


class ShopExchangeTicketOp(SrOperation):
    """商店兑换页兑换星轨专票(星芒/余烬双渠道)。

    结果状态:
    - ``EXCHANGED``:兑换完成回商店页,data 带
      ``source``/``exchanged``(实际兑换张数)/``material_left``(材料余额)/
      ``monthly_left``(余烬渠道:兑换后月限剩余;星芒渠道为 None);
    失败:起点不在商店页、tab 与 source 不符、弹窗打不开、数量调不到目标、
    余烬渠道 count 超月限剩余、确认未生效、终验不符。
    """

    def __init__(self, ctx: SrContext, count: int | None = None,
                 source: str = SOURCE_STARDUST):
        """
        :param ctx: 上下文
        :param count: 兑换张数;``None`` = 拉满全部(星芒受余额限制,余烬受月限+余额)。
            **消耗参数:仅限用户明确授权的兑换请求传入。**
        :param source: 供货渠道,``stardust``=星芒(不限量) / ``ash``=余烬(月限 5)。
        """
        self._count: int | None = count
        self._source: str = source
        self._popup_opened: bool = False
        """弹窗已打开(数量调整/确认节点的前置判据)"""
        self._monthly_left: int | None = None
        """兑换前月限剩余(余烬渠道,count 超限判定与拉满验证的基准)"""
        self._last_pull_count: int | None = None
        """上一轮拉满后的数量读数(两轮同值判滑条到顶,防 1 张顶格时误判未生效)"""
        self._pull_confirmed: bool = False
        """同值已复点一次(区分「已到顶」与「单次点击丢失」,第二次同值才判到顶)"""
        SrOperation.__init__(self, ctx, op_name=gt('商店兑换专票'),
                             node_max_retry_times=60)

    @operation_node(name='打开兑换弹窗', is_start_node=True)
    def open_popup(self) -> OperationRoundResult:
        """校验画面与 source 对应 tab,点专票商品卡,until 兑换弹窗锚出现。

        tab 判定读第 1 行第 4 列槽位互斥商品文本(两渠道槽位卡不同);不符
        直接失败提示先切 tab——本 op 不代切(单一职责,切 tab 见 ShopSwitchTabOp)。
        弹窗已打开的重入场景(op 中断恢复):先读弹窗商品名核验是专票弹窗才
        放行——其他商品弹窗(上轮事故遗留/误开)接手会在错误商品上执行兑换。
        """
        if self._source not in _ALLOWED_SOURCES:
            return self.round_fail(
                f'不支持的 source: {self._source}(仅支持 stardust/ash)')
        screen = self.check_and_update_current_screen(screen_name_list=[
            _SHOP_SCREEN, _POPUP_SCREEN])
        if screen == _POPUP_SCREEN:
            title = self._area_text(self.last_screenshot, _POPUP_SCREEN,
                                    _AREA_GOODS_TITLE)
            if title is None or '专票' not in title:
                return self.round_fail(
                    f'当前兑换弹窗不是星轨专票(商品名: {title or "未识别"}),'
                    f'请先关闭该弹窗再重试')
            self._popup_opened = True
            return self.round_success(status='POPUP_OPENED', wait=1)
        if screen != _SHOP_SCREEN:
            return self.round_fail('起点不在商店页,请先经 EnterShopFromWarpOp 进入')
        slot_text = self._area_text(self.last_screenshot, _SHOP_SCREEN,
                                    _AREA_TAB_SLOT)
        keyword = _TAB_SLOT_KEYWORD[self._source]
        if slot_text is None or keyword not in slot_text:
            current = ('余烬' if slot_text is not None and '冒险' in slot_text
                       else '星芒' if slot_text is not None and '银河铁道' in slot_text
                       else '未知')
            return self.round_fail(
                f'当前不在 {self._source} 对应兑换 tab(槽位识别: {current}),'
                f'请先经 ShopSwitchTabOp 切换')
        # 专票卡固定在第 1 行第 1 列——不能用「商品列表」area 中心
        # (页面几何中心落在第 4 列商品卡上,实测踩坑)
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _SHOP_SCREEN, _GOODS_TICKET_CARD,
            until_find_all=[(_POPUP_SCREEN, _AREA_POPUP_MARK)],
            success_wait=1.5, retry_wait=1.5)
        if result.is_success:
            self._popup_opened = True
            return self.round_success(status='POPUP_OPENED', wait=1.5)
        return result

    @node_from(from_name='打开兑换弹窗', status='POPUP_OPENED')
    @operation_node(name='调整数量', node_max_retry_times=40)
    def adjust_count(self) -> OperationRoundResult:
        """按 count 调整兑换数量,到达目标后进入确认。

        count=None:点「拉满」一键到滑条上限(星芒=余额,余烬=月限剩余),
        两轮读数同值判到顶(余额/月限只够 1 张时 current==1 也是终态,
        不能用 >1 判生效);count=N:余烬渠道先校验 N 不超月限剩余(超限
        fail 不截断),读当前数量 c,c<N 点「+」逐张上调,c==N 进入确认,
        c>N 点「-」下调(弹窗默认 1,理论上 c<=N 恒成立,减号分支为兜底)。
        数量以 OCR 实读为准(点了≠成了)。
        """
        if not self._popup_opened:
            return self.round_retry('弹窗未打开,等待画面稳定', wait=1)
        # 弹窗在屏证据门:弹窗意外消失(误触关闭/奖励弹窗残留场景)时中止——
        # 此时加减号/拉满坐标会落在商店页商品卡上,继续点击就是计划外购买
        if not self._exchange_popup_visible():
            return self.round_fail('兑换弹窗已不在屏(被意外关闭?),中止调整')
        current: int | None = parse_count(
            self._area_count_text(self.last_screenshot, _POPUP_SCREEN, _AREA_COUNT))
        if current is None:
            return self.round_retry('兑换数量读取失败,重试', wait=1)
        if self._source == SOURCE_ASH and self._monthly_left is None:
            monthly_text = self._area_text(self.last_screenshot, _POPUP_SCREEN,
                                           _AREA_MONTHLY_LEFT)
            self._monthly_left = parse_monthly_left(monthly_text)
            if self._monthly_left is None:
                return self.round_retry('月限剩余读取失败,重试', wait=1)
        if self._count is None:
            # 拉满点滑条到顶后重复点击无效;但「数量同值」有两种可能——已到顶,
            # 或该次点击丢失。首轮同值再点一次,连续两轮同值才判到顶
            # (含「余额/月限只够 1 张」的 1 张顶格形态,不能用 >1 判生效)
            if current == self._last_pull_count:
                if self._pull_confirmed:
                    return self.round_success(status='COUNT_READY', wait=1)
                self._pull_confirmed = True
                self._click_area_center(_POPUP_SCREEN, _AREA_MAX)
                return self.round_retry('数量同值,复点拉满区分到顶/丢点', wait=1.5)
            self._last_pull_count = current
            self._pull_confirmed = False
            self._click_area_center(_POPUP_SCREEN, _AREA_MAX)
            return self.round_retry('已点拉满,下一轮读数验证', wait=1.5)
        if self._source == SOURCE_ASH and self._count > self._monthly_left:
            return self.round_fail(
                f'兑换 {self._count} 张超本月剩余额度({self._monthly_left} 张),'
                f'不截断执行;如需全换请传 count=None(拉满)')
        if current == self._count:
            return self.round_success(status='COUNT_READY', wait=1)
        if current < self._count:
            self._click_area_center(_POPUP_SCREEN, _AREA_PLUS)
        else:
            self._click_area_center(_POPUP_SCREEN, _AREA_MINUS)
        return self.round_retry(f'当前数量 {current},向目标 {self._count} 调整中',
                                wait=0.6)

    @node_from(from_name='调整数量', status='COUNT_READY')
    @operation_node(name='确认兑换', node_max_retry_times=15)
    def confirm(self) -> OperationRoundResult:
        """状态分派确认兑换:每轮先读画面证据再决定动作,无证据不点击。

        优先级:①「获得物品」奖励弹窗(件数 ≥2 的兑换确认后出现)→ 点安全
        空白点关闭——不能点确认按钮坐标:关闭瞬间遮罩销毁、释放事件可能
        穿透下层,落在确认坐标上会误触商品卡;②兑换弹窗仍在(「兑换数量」
        可读)→ 说明确认未生效,重点确认;③两者都不在且画面识别为商店页
        → 兑换已完成,进入读数终验。
        """
        count = self._count
        # 关键词语义匹配而非非空判断:商店页正常态下同 rect 会扫到 tab 词/
        # 商品价格数字,非空判断会把正常商店页误判成弹窗在屏
        reward_text = self._area_text(self.last_screenshot, _SHOP_SCREEN,
                                      _AREA_REWARD_MARK)
        if reward_text is not None and '获得物品' in reward_text:
            self.ctx.controller.click(_REWARD_CLOSE_POS, press_time=0.1)
            return self.round_retry('获得物品弹窗,点安全空白点关闭', wait=1.5)
        if self._exchange_popup_visible():
            self._click_area_center(_POPUP_SCREEN, _AREA_CONFIRM)
            return self.round_retry('确认未生效,弹窗仍在,重点确认', wait=1.5)
        if self.check_and_update_current_screen(
                screen_name_list=[_SHOP_SCREEN]) == _SHOP_SCREEN:
            material_left = parse_count(
                self._area_count_text(self.last_screenshot, _SHOP_SCREEN, _AREA_CURRENCY))
            monthly_left: int | None = None
            if self._source == SOURCE_ASH:
                badge_text = self._area_text(self.last_screenshot, _SHOP_SCREEN,
                                             _AREA_MONTHLY_BADGE)
                monthly_left = parse_monthly_left(badge_text)
                expected = 0 if count is None else self._monthly_left - count
                if monthly_left is None or monthly_left != expected:
                    return self.round_retry(
                        f'终验不符:月限角标读数 {badge_text},期望剩余 {expected};重试', wait=1.5)
            actual = count if count is not None else None
            return self.round_success(status='EXCHANGED', data={
                'source': self._source,
                'exchanged': actual,
                'material_left': material_left,
                'monthly_left': monthly_left,
            }, wait=1)
        return self.round_retry('画面过渡中(未识别到弹窗或商店页),等待', wait=1.5)

    def _click_area_center(self, screen_name: str, area_name: str) -> None:
        """点指定 area 中心(press_time=0.1,点击有效性由调用方轮询验证)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        self.ctx.controller.click(area.center, press_time=0.1)

    def _exchange_popup_visible(self) -> bool:
        """兑换弹窗在屏证据:「兑换数量」关键词命中弹窗锚 area。"""
        text = self._area_text(self.last_screenshot, _POPUP_SCREEN, _AREA_POPUP_MARK)
        return text is not None and '兑换数量' in text

    def _area_text(self, screen, screen_name: str, area_name: str) -> str | None:
        """读画面建档 area 内的 OCR 文本(空 = None)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(screen, rect=area.rect)
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
