"""每月余烬兑换 app:自动兑换常驻商店·兑换商店余烬 tab 的月限三件套。

编排(design: docs/develop/sr_od/application/monthly_embers_exchange/
changes/v1-initial/application-flow.md,四段式):
    ① 导航段 OpenExchangeShop(任意画面 → 兑换商店列表页)
    ② 兑换段 按配置优先级逐项 ExchangeShopBuyGoods(count=None 拉满),
       按购买 op 的 data.fail_status 分支:
       售罄/不可购/未找到 → 跳过记 skip_note 继续;
       余额不足 → 终止循环,其后项记 SKIP_BALANCE(用户裁定:换到换不动为止);
       其余失败(无 fail_status)= 非预期 → 尽力返回大世界后 FAIL 不标完成。
    ③ 领奖段 无(获得物品弹窗在购买 op 内)
    ④ 返回段 BackToNormalWorldPlus(一条龙在大世界干净交接)

运行语义:周期 DAILY,预期内完成(含全部售罄/零购买/全部关闭/余额终止)
照常标当日完成——「已换不重买」由购买 op 售罄拦截承担;额度月中解锁
(版本口径)最迟次日补上。业务字段随循环逐项即时写入运行记录。
"""

from one_dragon.base.operation.application_run_record import AppRunRecord
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_notify import NotifyTiming, node_notify
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.application.cultivation.account.operations.shop_buy_goods import (
    ExchangeShopBuyGoods,
)
from sr_od.application.monthly_embers_exchange import (
    monthly_embers_exchange_const,
)
from sr_od.application.monthly_embers_exchange.monthly_embers_exchange_config import (
    MonthlyEmbersExchangeConfig,
)
from sr_od.application.monthly_embers_exchange.monthly_embers_exchange_run_record import (
    MonthlyEmbersExchangeRunRecord,
)
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.store.open_exchange_shop import OpenExchangeShop

GOODS_FIXED_ORDER: list[str] = ['special_pass', 'pass', 'tracks_of_destiny']
"""同优先级时的兜底顺序:专票 > 通票 > 足迹(用户裁定 2026-11-13 第 8 条)"""

SKIP_BALANCE: str = 'SKIP_BALANCE'
"""余额不足终止循环后,未尝试项在 skip_note 中的标记(区别于尝试后的
INSUFFICIENT_MATERIALS:该项从未进弹窗)"""

STATUS_ALL_DONE: str = 'ALL_PROCESSED'
"""兑换段正常完成(零跳过)的出口状态"""
STATUS_DONE_WITH_SKIP: str = 'ALL_PROCESSED_WITH_SKIP'
"""兑换段正常完成但有跳过/放弃项的出口状态(明细在运行记录 skip_note,
通知细节模式的状态行会显示该标记提示查阅)"""
STATUS_UNEXPECTED_FAIL: str = 'UNEXPECTED_FAIL'
"""兑换段非预期失败的出口状态(转失败收尾)"""

_CLASSIFY_SKIP: set[str] = {'SOLD_OUT', 'CARD_UNAVAILABLE', 'NOT_FOUND'}


def resolve_exchange_order(
        items: list[tuple[str, bool, int]]) -> list[str]:
    """兑换项解析:过滤关闭项,按 (priority 升序, 固定序兜底) 排出兑换顺序。

    :param items: (英文标识符, 开关, 优先级) 列表
    :return: 已排序的英文标识符列表
    """
    fixed_idx = {goods: idx for idx, goods in enumerate(GOODS_FIXED_ORDER)}
    enabled = [item for item in items if item[1]]
    enabled.sort(key=lambda item: (item[2], fixed_idx.get(item[0],
                                                        len(fixed_idx))))
    return [item[0] for item in enabled]


def classify_purchase_result(
        success: bool, fail_status: str | None) -> str:
    """购买结果 → 编排分支(应用编排稿 §3.1 分支表的纯函数形态)。

    :param success: 购买 op 是否成功(PURCHASED)
    :param fail_status: 失败时的 data.fail_status(成功时忽略)
    :return: ``BOUGHT``=换到继续下一项 / ``SKIP``=预期内跳过继续下一项
        (售罄/不可购/未找到) / ``STOP_BALANCE``=余额不足终止循环 /
        ``ABORT``=非预期失败中止
    """
    if success:
        return 'BOUGHT'
    if fail_status in _CLASSIFY_SKIP:
        return 'SKIP'
    if fail_status == 'INSUFFICIENT_MATERIALS':
        return 'STOP_BALANCE'
    return 'ABORT'


class MonthlyEmbersExchangeApp(SrApplication):

    def __init__(self, ctx: SrContext,
                 config: MonthlyEmbersExchangeConfig,
                 run_record: AppRunRecord):
        """
        :param ctx: 上下文
        :param config: app 配置(factory 注入,与 GUI/MCP 同一缓存实例)
        :param run_record: 运行记录(factory 注入,周期 DAILY)
        """
        self._config: MonthlyEmbersExchangeConfig = config
        self._record: MonthlyEmbersExchangeRunRecord = run_record
        self._abort_msg: str = ''
        """非预期失败的原始语境(n4 尽力返回大世界后随 FAIL 带出)"""
        SrApplication.__init__(self, ctx,
                               monthly_embers_exchange_const.APP_ID,
                               op_name=gt('每月余烬兑换', 'game'),
                               run_record=run_record)

    @operation_node(name='到达兑换商店', is_start_node=True)
    def navigate(self) -> OperationRoundResult:
        """导航段:OpenExchangeShop 到兑换商店列表页;失败转失败收尾。"""
        result = OpenExchangeShop(self.ctx).execute()
        if not result.success:
            self._abort_msg = f'导航到兑换商店失败: {result.status}'
            return self.round_success(status='NAV_FAIL', wait=0.5)
        return self.round_by_op_result(result)

    @node_from(from_name='到达兑换商店')
    @node_notify(when=NotifyTiming.CURRENT_DONE, detail=True)
    @operation_node(name='按优先级兑换')
    def exchange(self) -> OperationRoundResult:
        """兑换段:开启项按优先级逐项拉满,分支见模块 docstring。

        skip_note 与购买数量逐项即时写入运行记录;UNEXPECTED_FAIL 不在此
        终结,转失败收尾节点尽力返回大世界后带原始语境 FAIL。
        """
        items: list[tuple[str, bool, int]] = [
            (goods,
             getattr(self._config, f'{goods}_enabled'),
             getattr(self._config, f'{goods}_priority'))
            for goods in GOODS_FIXED_ORDER
        ]
        order = resolve_exchange_order(items)
        stop_idx: int | None = None
        for idx, goods in enumerate(order):
            # scroll_search=False(用户优化 2026-11-14):月限三件套可用排前、
            # 售罄沉底——首屏没有 = 本期已尽,无需滚动扫描(切 tab 默认回顶,
            # 首屏判定对位置敏感由购买 op 内置回顶保证)
            result = ExchangeShopBuyGoods(self.ctx, goods, count=None,
                                          scroll_search=False).execute()
            branch = classify_purchase_result(
                result.success,
                (result.data or {}).get('fail_status'))
            if branch == 'BOUGHT':
                bought = int((result.data or {}).get('bought', 0))
                self._record.record_purchase(goods, bought)
                self._record.record_balance_left(
                    (result.data or {}).get('balance_left'))
                continue
            if branch == 'SKIP':
                self._record.record_skip(f'{goods}:{(result.data or {}).get("fail_status")}')
                continue
            if branch == 'STOP_BALANCE':
                self._record.record_skip(f'{goods}:INSUFFICIENT_MATERIALS')
                stop_idx = idx
                break
            self._abort_msg = (
                f'{goods} 兑换非预期失败: {result.status}(余额与到货请以'
                f'游戏内为准)')
            self._record.record_balance_left(None)
            return self.round_success(status=STATUS_UNEXPECTED_FAIL, wait=0.5)
        if stop_idx is not None:
            # 裁定「后面的放弃」:余额不足后未尝试项显式记 SKIP_BALANCE
            for goods in order[stop_idx + 1:]:
                self._record.record_skip(f'{goods}:{SKIP_BALANCE}')
        status = (STATUS_DONE_WITH_SKIP if self._record.skip_note
                  else STATUS_ALL_DONE)
        return self.round_success(status=status, wait=0.5)

    @node_from(from_name='按优先级兑换', status=STATUS_ALL_DONE)
    @node_from(from_name='按优先级兑换', status=STATUS_DONE_WITH_SKIP)
    @operation_node(name='返回大世界')
    def back_to_world(self) -> OperationRoundResult:
        """返回段:BackToNormalWorldPlus,保证一条龙在大世界交接。"""
        result = BackToNormalWorldPlus(self.ctx).execute()
        if not result.success:
            return self.round_fail(f'返回大世界失败: {result.status}')
        return self.round_by_op_result(result)

    @node_from(from_name='按优先级兑换', status=STATUS_UNEXPECTED_FAIL)
    @node_from(from_name='到达兑换商店', status='NAV_FAIL')
    @operation_node(name='失败收尾')
    def fail_return(self) -> OperationRoundResult:
        """失败收尾:尽力返回大世界(下一 app 的干净起点)后带原始语境 FAIL。

        返回失败不掩盖原始失败信息;框架对失败 app 无画面收尾,此节点补位。
        """
        result = BackToNormalWorldPlus(self.ctx).execute()
        msg = self._abort_msg
        if not result.success:
            msg = f'{msg};返回大世界也未成功({result.status})'
        return self.round_fail(msg)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    app = MonthlyEmbersExchangeApp(
        ctx,
        config=ctx.run_context.get_config(
            app_id=monthly_embers_exchange_const.APP_ID,
            group_id='one_dragon'),
        run_record=ctx.run_context.get_run_record(
            app_id=monthly_embers_exchange_const.APP_ID),
    )
    app.execute()


if __name__ == '__main__':
    __debug()
