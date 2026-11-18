from typing import ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.operations.cw_entry.cw_entry_start import (
    try_handle_entry_popups,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guid_choose_tab import GuideChooseTab
from sr_od.interastral_peace_guide.open_guide import GuideOpen


class CwEntryEnter(CwOperation):
    """从大世界进入「货币战争」大厅(入口流程 M1)。
    起点:大世界;终点:货币战争大厅(弹窗守卫自动处理沿途一次性弹窗)。

    路径:打开指南(星际和平指南)→ 旷宇纷争 TAB → (货币战争分类默认选中)→ 前往参与
    → 关一次性弹窗(「点击空白处关闭」类 / 版本公告轮播,见 wait_lobby)→ 货币战争大厅。

    repo guide_data / screen_info 尚无货币战争,故 TAB 用现有「星际和平指南-TAB-旷宇纷争」area,
    其余用 OCR 点击(非 GuideTransport)。
    """

    # 点空白关闭「点击空白处关闭」类弹窗的区域(避开中央内容)
    BLANK_CLICK: ClassVar[Rect] = Rect(1450, 920, 1560, 980)
    # 大厅 screen_info 画面名;到达判定经 round_by_find_area(替代全屏 ocr)
    LOBBY_SCREEN: ClassVar[str] = '货币战争-大厅'

    STATUS_AT_LOBBY: ClassVar[str] = '已在货币战争大厅'

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='进入货币战争')

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
        # 按钮不在 ≠ 失败(实测事故:传送已落地/恢复场景下本节点判死
        # 「找不到 前往参与」,而画面已在朝露公馆入口只差按 F)。交 wait_lobby 分流 ——
        # 它已有全部下游分支:仍在指南页则重点击 / 入口按 F / 弹窗消化 / 大厅即成功,
        # 真到不了大厅由它的节点预算兜底退出。
        log.info('[cw-entry] 「前往参与」不在画面(可能已传送/加载中)→ 交等待大厅节点分流')
        return self.round_success(status='前往参与不在画面,交下游分流')

    @node_from(from_name='前往参与')
    @operation_node(name='关闭弹窗并等待大厅', node_max_retry_times=30)
    def wait_lobby(self) -> OperationRoundResult:
        screen = self.last_screenshot

        # 入口链弹窗守卫(注册表统一入口,supply→jade→badge 序位见
        # cw_entry_start.ENTRY_POPUP_GUARDS;/):纵深调用点——
        # 弹窗可盖在指南页/朝露公馆入口任意一帧上,不接住则下方「前往参与」/
        # 大厅识别标志/F 分支全部落空 → 节点预算耗尽。
        popup = try_handle_entry_popups(self, screen)
        if popup is not None:
            return popup

        # 到达大厅:左上角玩法名标题「货币战争」(大厅独有识别标志;lobby screen_info
        # area 判定)。v4.7 大厅改版:旧锚「创业指南」左菜单已不存在;曾换锚赛季名
        # 「入画奇航」,但赛季名每赛季必漂移(v4.7 赛季「零和博弈」实帧失配)——换锚
        # 「货币战争」玩法名标题:玩法名不随赛季更替,是标题区唯一跨赛季稳定文本。
        # 不用「开始「货币战争」」——会与旷宇纷争页「货币战争」分类文本 LCS 误匹配
        # (玩法名标题 rect 对准指南页左上「旷宇纷争」标题下沿,带内无文本,实测不失配)。
        if self.round_by_find_area(screen, CwEntryEnter.LOBBY_SCREEN, '标识-玩法名').is_success:
            log.info('[cw-entry] 到达货币战争大厅')
            return self.round_success(CwEntryEnter.STATUS_AT_LOBBY)

        # 传送确认框(地图点传送后偶发「是否传送至附近」):点确认。
        # ⚠️ 须先于地图传送分支:确认框文案含「传送」二字,顺序颠倒会在
        # 确认框上误点句中「传送」词(非按钮)。
        if self.round_by_ocr(screen, '传送至附近', lcs_percent=0.7).is_success:
            log.info('[cw-entry] 传送确认框 → 确认')
            self.round_by_ocr_and_click(screen, '确认', success_wait=4,
                                        retry_wait=1)
            # round_retry 非 success:传送落地只是中转,终点仍是大厅
            return self.round_retry('已确认传送', wait=4)

        # 任务面板「前往」后的传送地图(导航/大地图):点「传送」传到任务点
        # (朝露公馆),落地后由下方 F 分支进大厅。
        # ⚠️ 须先于下方任务面板分支:地图右下也有「停止追踪」按钮,顺序颠倒
        # 会在地图帧误入任务面板分支、点到两按钮间空位空转(实机 28 重试卡死根因)。
        if self.round_by_ocr(screen, '传送', lcs_percent=0.7).is_success:
            log.info('[cw-entry] 传送地图 → 点「传送」')
            self.round_by_ocr_and_click(screen, '传送', success_wait=4,
                                        retry_wait=2)
            # round_retry 非 success:op 终点 = 大厅,传送只是链路中转
            # (success 会提前结束整个 op,实机停在大世界 F 分支未跑,已修)。
            return self.round_retry('已点传送,等待落地', wait=5)

        # v4.7 新手任务门(实机两次卡死根因):新手关未完成时,旷宇纷争页
        # 「前往参与」改为弹出任务面板(货币战争•入画奇航/试用货币战争新系统),
        # 不再直接传送。面板含「货币战争」字样且无「前往参与」→ 下方旧 F 分支
        # 误触发按 F 死循环(面板不响应 F)。处理 = 点面板内「前往」(按钮位 =
        # 「按钮-开始追踪」area,追踪态文案变体,位置一致)→ 落传送地图 →
        # 由上方地图传送分支接力;面板识别锚 =「停止追踪」(面板与地图右下
        # 按钮共有,故本分支必须排在地图分支之后)。
        if self.round_by_ocr(screen, '停止追踪', lcs_percent=0.7).is_success:
            log.info('[cw-entry] v4.7 新手任务面板 → 点「前往」走地图传送链')
            # 纯定位点「前往」:按钮文案随追踪态在 前往/开始追踪 间切换,
            # find_and_click 按建档文本「开始追踪」匹配会恒 miss(实机 30 重试失败根因),
            # 改点「按钮-开始追踪」area 中心(位置恒定);面板本身已由
            # 「停止追踪」OCR 锚确认,不靠按钮文案复核。
            self.round_by_click_area('任务', '按钮-开始追踪',
                                     pre_delay=0.3, success_wait=3)
            return self.round_retry('任务面板已点前往', wait=2)

        # 仍在指南页(「前往参与」还在 = 上个节点的 transport click 没落地,仍在加载)→ 重点击。
        # 否则停在指南页(「货币战争」分类 + 「前往参与」按钮都在)→ 下方 F 分支(NOT 前往参与)被跳过
        # → 无分支命中 → 死循环重试(全流程跑 37x 重试失败根因)。
        # ⚠️ lcs_percent=0.7 防误配(实测事故):朝露公馆大世界左侧任务追踪文本
        # 「请前往匹诺康尼-飞翔时针号」与「前往参与」LCS=前往(2/4=0.5)恰过默认阈值 → 存在性检查
        # 假阳性 → 永远走本分支重点击 → F 分支被饿死,对局 8s 内失败。真按钮 OCR 4/4(一字形变 3/4=0.75),
        # 0.7 同时容忍形变与拒绝该假阳性;round_by_ocr_and_click 有 difflib 预筛不受此扰。
        if self.round_by_ocr(screen, '前往参与', lcs_percent=0.7).is_success:
            return self.round_by_ocr_and_click(screen, '前往参与', success_wait=2)

        # 「点击空白处关闭」类弹窗(如新内容解禁)→ 点空白;lcs 0.8 拒
        # 「点击空白处继续」互串(5/7≈0.71 过默认),容忍 1 字误读(6/7≈0.86)
        if self.round_by_ocr(screen, '点击空白处关闭',
                             lcs_percent=0.8).is_success:
            self.ctx.controller.click(CwEntryEnter.BLANK_CLICK.center)
            return self.round_retry(wait=1)

        # 版本公告轮播(「贪饕」侵蚀版本):游戏级公告弹窗可盖在
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
