from typing import Optional

from one_dragon.base.geometry.point import Point
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.menu import phone_menu_const
from sr_od.operations.menu.click_phone_menu_item import ClickPhoneMenuItem
from sr_od.operations.menu.open_phone_menu import OpenPhoneMenu
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.synthesize.synthesize_const import (
    QUANTITY_MODE_PLUS_MONTHLY,
    SynthesizeItem,
    SynthesizeItemEnum,
)

STATUS_QTY_MAXED: str = 'QTY_MAXED'
"""plus_monthly 数量拉满完成(「+」已置灰),去点合成"""
STATUS_QUOTA_EXHAUSTED: str = 'QUOTA_EXHAUSTED'
"""本月额度已用完,无事可做——不点合成,op 以成功收尾(app 标本周期完成)"""
STATUS_ITEM_ABSENT: str = 'ITEM_ABSENT_FIRST_SCREEN'
"""plus_monthly 物品首屏未见(本期不可合成,沉底排序律)——op 以成功收尾,
额度用尽/材料不足的裁定归调用方(按运行记录当月锚区分)"""


class Synthesize(SrOperation):
    """合成指定物品:自动导航(回大世界 → 菜单 → 合成)后选物品、选数量、
    确认合成。非 MCP 传参单元:item 参数为运行时合成物品对象,仅限代码内调用。
    起点:任意可控画面;终点:合成页面(物品已合成;STATUS_QUOTA_EXHAUSTED /
    STATUS_ITEM_ABSENT 时停在合成页、未点合成)。
    副作用:消耗材料合成物品。
    """

    def __init__(self, ctx: SrContext, item: SynthesizeItem, num: int):
        """
        :param ctx: 上下文
        :param item: 要合成的物品(合成物品常量表对象)
        :param num: 合成数量,0 为最大值(当前仅支持最大值)
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('合成', 'game'), ''))

        self.item: SynthesizeItem = item  # 要合成的物品
        self.num: int = num  # 要合成的数量 0为最大值
        self._qty_dragged: bool = False
        """plus_monthly 路径本次运行是否已拖过滑条——区分「拖满到顶」与
        「入口即置灰的歧义态」(额度用完/材料约束到顶),节点轮询间保留"""
        self._category_reset_done: bool = False
        """plus_monthly 首屏判定前是否已点分类页签强制回顶(一次;防人工
        滚动过列表时视口不在顶、误判首屏未见)"""

    @node_from(from_name='画面识别')
    @operation_node(name='开始前返回')
    def back_at_first(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='开始前返回')
    @operation_node(name='打开菜单')
    def open_menu(self) -> OperationRoundResult:
        op = OpenPhoneMenu(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开菜单')
    @operation_node(name='选择合成')
    def choose_synthesize(self) -> OperationRoundResult:
        op = ClickPhoneMenuItem(self.ctx, phone_menu_const.SYNTHESIZE)
        return self.round_by_op_result(op.execute())

    @operation_node(name='画面识别', is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        """
        识别画面
        :return:
        """
        screen = self.last_screenshot
        result = self.round_by_find_area(screen, '合成', '标题-合成')

        if result.is_success:
            return self.round_success(result.status)
        else:
            return self.round_success()

    @node_from(from_name='选择合成')
    @node_from(from_name='画面识别', status='标题-合成')
    @operation_node(name='选择合成类别')
    def choose_category(self) -> OperationRoundResult:
        """
        选择合成类别
        :return:
        """
        screen = self.last_screenshot

        area = self.ctx.screen_loader.get_area('合成', '标题-合成分类')
        result = self.round_by_ocr(screen, self.item.category, area=area)

        if result.is_success:
            return self.round_success(result.status)
        else:
            self.round_by_click_area('合成', f'分类-{self.item.category}')
            return self.round_retry(result.status, wait=0.5)

    @node_from(from_name='选择合成类别')
    @operation_node(name='选择合成物品')
    def choose_item(self) -> OperationRoundResult:
        """
        选择合成物品
        :return:
        """
        screen = self.last_screenshot
        result = self.get_item_pos(screen)

        if result is None:
            if self.item.quantity_mode == QUANTITY_MODE_PLUS_MONTHLY:
                # 首屏判定(用户裁定:可合成时恒居列表左上首位,不可用沉底,
                # 同兑换商店月限商品排序律)——不拖拽深扫,沉底项深处位置
                # 不定,深扫不可达。前提 = 列表在顶:进页/切页签默认回顶;
                # 视口不在顶(中途人工滚动过)时先点分类页签强制回顶再判
                # 一次,仍未见才结论首屏未见。额度用尽/材料不足的裁定归
                # 调用方按运行记录当月锚(见 STATUS_ITEM_ABSENT)
                if not self._category_reset_done:
                    self._category_reset_done = True
                    self.round_by_click_area(
                        '合成', f'分类-{self.item.category}')
                    return self.round_retry('首屏未见,点分类页签回顶后复查',
                                            wait=1)
                return self.round_success(STATUS_ITEM_ABSENT)
            area = self.ctx.screen_loader.get_area('合成', '物品列表')
            drag_from = area.center
            drag_to = drag_from + Point(0, -300)
            self.ctx.controller.drag_to(start=drag_from, end=drag_to)
            return self.round_retry(f'未找到{self.item.name}', wait=2)
        else:
            self.ctx.controller.click(result.center)
            return self.round_success(wait=0.5)

    def get_item_pos(self, screen) -> Optional[MatchResult]:
        """
        获取合成物品的位置
        :param screen:
        :return:
        """
        area = self.ctx.screen_loader.get_area('合成', '物品列表')
        part = cv2_utils.crop_image_only(screen, area.rect)

        mrl = self.ctx.tm.match_template(part, 'synthesize', self.item.template_id)

        if mrl.max is None:
            return None

        result = mrl.max
        result.x += area.rect.left_top.x
        result.y += area.rect.left_top.y

        return result

    @node_from(from_name='选择合成物品')
    @operation_node(name='选择数量', node_max_retry_times=4)
    def choose_num(self) -> OperationRoundResult:
        """
        选择合成数量:按物品的数量策略分流。

        max_btn(默认):消耗品合成页点「最大值」,材料不足判失败;
        plus_monthly:月限物品,滑条拖满(重试预算覆盖拖动复查)。
        :return:
        """
        if self.item.quantity_mode == QUANTITY_MODE_PLUS_MONTHLY:
            return self._choose_num_plus_monthly()

        screen = self.last_screenshot

        result = self.round_by_find_area(screen, '合成', '合成所需材料不足')
        if result.is_success:
            return self.round_fail(result.status)

        self.round_by_click_area('合成', '按钮-最大值')
        return self.round_success(wait=0.5)

    def _choose_num_plus_monthly(self) -> OperationRoundResult:
        """
        月限物品数量拉满:滑条拖满 + 置灰判顶(拖动手法与滑条点选同源,
        拖到轨道右端取精确上限,不受上限值大小影响)。

        每轮顺序:材料不足判失败(裁定:材料不足是失败,不标本周期完成,
        由调用方后续补跑)→ 置灰命中:本轮已拖 = 拉满完成;入口即置灰为
        歧义态(额度用完 / 已被材料约束到顶),读「本月还可合成」消歧:0 =
        无事可做;≥1 = 已到顶,合成当前数量;读不出 = 判失败不冒险。未置灰
        = 拖手柄到轨道右端后重试(起点 = 手柄最小值位,新开合成页数量恒回
        1 实测;手柄不在最小值位时按住轨道会先跳到该位、拖到右端仍归位上限)。
        :return:
        """
        screen = self.last_screenshot

        insufficient = self.round_by_find_area(screen, '合成', '合成所需材料不足')
        if insufficient.is_success:
            return self.round_fail(insufficient.status)

        gray = self.round_by_find_area(screen, '合成', '按钮-数量增加-置灰')
        if gray.is_success:
            if self._qty_dragged:
                return self.round_success(STATUS_QTY_MAXED, wait=0.5)
            quota = self._read_monthly_quota()
            if quota == 0:
                return self.round_success(STATUS_QUOTA_EXHAUSTED)
            if quota is None:
                return self.round_fail('额度文本不可读')
            return self.round_success(STATUS_QTY_MAXED, wait=0.5)

        handle = self.ctx.screen_loader.get_area('合成', '滑条-手柄起点')
        end = self.ctx.screen_loader.get_area('合成', '滑条-拉满终点')
        self.ctx.controller.drag_to(start=handle.center, end=end.center,
                                    duration=0.6)
        self._qty_dragged = True
        return self.round_retry('已拖滑条到右端,下一轮复查', wait=1)

    def _read_monthly_quota(self) -> int | None:
        """
        读「本月还可合成: N」→ N;区域无文本或读不出数字返回 None。
        :return:
        """
        area = self.ctx.screen_loader.get_area('合成', '读区-本月还可合成')
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(
            self.last_screenshot, rect=area.rect)
        text = ''.join(result.data for result in ocr_result_list)
        if not text:
            return None
        return str_utils.get_positive_digits(text, err=None)

    @node_from(from_name='选择数量')
    @node_from(from_name='选择数量', status=STATUS_QTY_MAXED)
    @operation_node(name='点击合成')
    def click_synthesize(self) -> OperationRoundResult:
        """
        进行合成
        :return:
        """
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(screen, '合成', '按钮-合成',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='选择数量', status=STATUS_QUOTA_EXHAUSTED)
    @operation_node(name='额度已用完')
    def quota_done(self) -> OperationRoundResult:
        """
        本月额度已用完的终止节点:原样带状态成功收尾,不点合成。

        该精确边必须显式声明——「选择数量」的无状态边是兜底边(仅在无精确
        边命中时接管),缺此边时 QUOTA_EXHAUSTED 会被兜底误送去点合成。
        :return:
        """
        return self.round_success(STATUS_QUOTA_EXHAUSTED)

    @node_from(from_name='选择合成物品', status=STATUS_ITEM_ABSENT)
    @operation_node(name='首屏未见物品')
    def item_absent(self) -> OperationRoundResult:
        """
        月限物品首屏未见(本期不可合成)的终止节点:原样带状态成功收尾。

        精确边必须显式声明,否则该状态会被「选择合成物品」的兜底边误送进
        数量节点,对自动选中的无关物品执行合成(真实消耗风险)。
        :return:
        """
        return self.round_success(STATUS_ITEM_ABSENT)

    @node_from(from_name='点击合成')
    @operation_node(name='点击确认')
    def click_confirm(self) -> OperationRoundResult:
        """
        合成出现的对话框 点击确认
        :return:
        """
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(screen, '合成', '按钮-合成确认',
                                                 success_wait=5, retry_wait=1)

    @node_from(from_name='点击确认')
    @operation_node(name='点击空白处关闭')
    def click_empty(self) -> OperationRoundResult:
        """
        确认后 点击空白关闭
        :return:
        """
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(screen, '合成', '点击空白处关闭',
                                                 success_wait=1, retry_wait=1)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()

    op = Synthesize(ctx, SynthesizeItemEnum.TRICK_SNACK.value, 0)
    op.execute()


if __name__ == '__main__':
    __debug()