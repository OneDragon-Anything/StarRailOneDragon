from typing import ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.operations.entry.start_currency_war_match import (
    try_handle_train_supply_popup,
)
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guid_choose_tab import GuideChooseTab
from sr_od.interastral_peace_guide.open_guide import GuideOpen
from sr_od.operations.sr_operation import SrOperation


class EnterCurrencyWar(SrOperation):
    """从大世界进入「货币战争」大厅(入口流程 M1)。

    路径:打开指南(星际和平指南)→ 旷宇纷争 TAB → (货币战争分类默认选中)→ 前往参与
    → 关一次性弹窗(「点击空白处关闭」类 / 版本公告轮播,见 wait_lobby)→ 货币战争大厅。

    repo guide_data / screen_info 尚无货币战争,故 TAB 用现有「星际和平指南-TAB-旷宇纷争」area,
    其余用 OCR 点击(非 GuideTransport)。详见 .debug/temp/currency_war/design.md。
    """

    # 点空白关闭「点击空白处关闭」类弹窗的区域(避开中央内容)
    BLANK_CLICK: ClassVar[Rect] = Rect(1450, 920, 1560, 980)
    # 大厅 screen_info 画面名;到达判定经 round_by_find_area(替代全屏 ocr)
    LOBBY_SCREEN: ClassVar[str] = '货币战争-大厅'

    STATUS_AT_LOBBY: ClassVar[str] = '已在货币战争大厅'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='进入货币战争')

    @operation_node(name='打开指南', is_start_node=True)
    def open_guide(self) -> OperationRoundResult:
        op = GuideOpen(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开指南')
    @operation_node(name='选择旷宇纷争TAB')
    def choose_tab(self) -> OperationRoundResult:
        # 复用 GuideChooseTab:检测当前 tab + find_and_click_area 真正点击(旷宇纷争在 repo guide_data 内)
        tab = self.ctx.guide_data.best_match_tab_by_name('旷宇纷争')
        if tab is None:
            return self.round_fail(status='指南数据无「旷宇纷争」TAB')
        op = GuideChooseTab(self.ctx, tab)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择旷宇纷争TAB')
    @operation_node(name='前往参与')
    def enter(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # success_wait 给点击落地 + 跳转加载留时间
        result = self.round_by_ocr_and_click(screen, '前往参与', retry_wait=1, success_wait=2)
        if result.is_success:
            return result
        # 按钮不在 ≠ 失败(2026-08-17 实测事故:传送已落地/恢复场景下本节点判死
        # 「找不到 前往参与」,而画面已在朝露公馆入口只差按 F)。交 wait_lobby 分流 ——
        # 它已有全部下游分支:仍在指南页则重点击 / 入口按 F / 弹窗消化 / 大厅即成功,
        # 真到不了大厅由它的节点预算兜底退出。
        log.info('[cw-entry] 「前往参与」不在画面(可能已传送/加载中)→ 交等待大厅节点分流')
        return self.round_success(status='前往参与不在画面,交下游分流')

    @node_from(from_name='前往参与')
    @operation_node(name='关闭弹窗并等待大厅', node_max_retry_times=30)
    def wait_lobby(self) -> OperationRoundResult:
        screen = self.last_screenshot

        # 列车补给每日弹窗(纵深挂点:弹窗可盖在指南页/朝露公馆入口任意一帧上,
        # 不接住则下方「前往参与」/F 分支全部落空 → 节点预算耗尽)。共享助手见
        # start_currency_war_match 模块级函数。
        popup = try_handle_train_supply_popup(self, screen)
        if popup is not None:
            return popup

        # 到达大厅:左菜单「创业指南」(大厅独有锚点;lobby screen_info area 判定,替代全屏 ocr)。
        # 不用「开始「货币战争」」——会与旷宇纷争页「货币战争」分类文本 LCS 误匹配。
        if self.round_by_find_area(screen, EnterCurrencyWar.LOBBY_SCREEN, '标识-创业指南').is_success:
            log.info('[cw-entry] 到达货币战争大厅')
            return self.round_success(EnterCurrencyWar.STATUS_AT_LOBBY)

        # 仍在指南页(「前往参与」还在 = 上个节点的 transport click 没落地,仍在加载)→ 重点击。
        # 否则停在指南页(「货币战争」分类 + 「前往参与」按钮都在)→ 下方 F 分支(NOT 前往参与)被跳过
        # → 无分支命中 → 死循环重试(2026-08-04 全流程跑 37x 重试失败根因)。
        # ⚠️ lcs_percent=0.7 防误配(2026-08-19 实测事故):朝露公馆大世界左侧任务追踪文本
        # 「请前往匹诺康尼-飞翔时针号」与「前往参与」LCS=前往(2/4=0.5)恰过默认阈值 → 存在性检查
        # 假阳性 → 永远走本分支重点击 → F 分支被饿死,对局 8s 内失败。真按钮 OCR 4/4(一字形变 3/4=0.75),
        # 0.7 同时容忍形变与拒绝该假阳性;round_by_ocr_and_click 有 difflib 预筛不受此扰。
        if self.round_by_ocr(screen, '前往参与', lcs_percent=0.7).is_success:
            return self.round_by_ocr_and_click(screen, '前往参与', success_wait=2)

        # 「点击空白处关闭」类弹窗(如新内容解禁)→ 点空白
        if self.round_by_ocr(screen, '点击空白处关闭').is_success:
            self.ctx.controller.click(EnterCurrencyWar.BLANK_CLICK.center)
            return self.round_retry(wait=1)

        # 版本公告轮播(「贪饕」侵蚀,2026-08-26 版本,W301):游戏级公告弹窗可盖在
        # 入口流程任意画面上(待机自动弹出)。项目新规禁键输入——旧实现对公告类
        # 弹窗(赛季扩充说明)按 ESC 关闭,已废;改与 BackToNormalWorldPlus 同款
        # 点击链:标题 id_mark(两页共享)正面识别公告屏 → 第 2 页(「关闭」钮可见)
        # 点关闭露出底下画面 / 第 1 页点右箭头翻页 → round_retry 逐帧重识别,
        # 点掉后由上方各分支接管。坐标全走 screen_info area,零键输入。
        if self.round_by_find_area(screen, '版本公告轮播', '标识-贪饕侵蚀').is_success:
            if self.round_by_find_area(screen, '版本公告轮播', '按钮-关闭').is_success:
                self.round_by_find_and_click_area(screen, '版本公告轮播', '按钮-关闭')
            else:
                self.round_by_click_area('版本公告轮播', '按钮-下一页')
            return self.round_retry('版本公告轮播', wait=1)

        # 「前往参与」把角色传送到朝露公馆入口附近(大世界旷野),需按 F(交互)进货币战争大厅。
        # 判定:画面有「货币战争」(入口交互提示)且不在指南页(无「前往参与」)→ 按 F。
        # lcs_percent=0.7 同上(防「请前往匹诺康尼…」任务追踪假阳性饿死本分支)。
        if (self.round_by_ocr(screen, '货币战争', lcs_percent=0.7).is_success
                and not self.round_by_ocr(screen, '前往参与', lcs_percent=0.7).is_success):
            log.info('[cw-entry] 朝露公馆入口(传送后)→ 按 F(交互)进货币战争大厅')
            self.ctx.controller.btn_tap(self.ctx.controller.game_config.key_interact)
            return self.round_retry(wait=2)

        # 加载中或未知态 → 继续等
        return self.round_retry(wait=1)
