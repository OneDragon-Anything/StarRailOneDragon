# 退局调度器架构(2026-09-13 重写,用户设计):
#   退出 op 的职责 = 调度,不是画面处理——旧版在单节点内联十几个全屏 OCR
#   分支复制各画面 op 的处理逻辑,复制体随时间漂移:「角色详情」
#   裸词锚化(与商店卡牌详情弹窗同词全等,垄断 26 分钟),退出 op 的复制体
#   未同步 → 大世界详情页误命中,30 轮全打空 fail(日志实证)。治本 = 画面
#   处理单一源回到各画面 op / CwLoop,本 op 只做识别与跳转。
# 画面识别单一源 = cw_screen_state.get_in_match_screen_name(建档 id_mark
#   精准匹配的框架实现);点击与推进判定 = round_by_find_and_click_area:
#   until_find_all = 点击后进入下一预期画面;until_not_find_all = 点击后
#   离开当前画面;按钮未现(演出中)→ round_retry 等待;节点预算兜底。
# 节点链(用户定稿,星形):节点1 画面路由(识别→按屏名跳转)为唯一中枢,
#   流程节点做完单动作即回路由重识别;lobby_check 为终点(SUCCESS = op 完成);
#   例外:弹窗放弃后直边进挑战失败节点——失败演出帧(单锚态)对建档精准
#   匹配不可见,回路由会被误判未识别,演出等待在该节点内由 retry 承载。
"""从货币战争对局中退出(放弃+结算)回大厅(退局调度器)。

任何可识别的对局内态(备战/战斗中/事件 overlay/胜负结算)→ 识别分发:
- 退出流程画面 → 逐节点建档点击走完 弃局→结算页→大厅;
- 干净备战 → 点门形「退出对局」图标(替代旧 ESC,误弹中断挑战史);
- loop 能处理的画面 → 委托 CwLoop(stop_at_prep=True) 处理到回备战;
- 连续未识别(大概率战斗中)→ 右上 X → 战斗暂停 → 撤退 → 接弹窗节点。
全链零 ESC、零全屏 OCR(识别走框架建档精准匹配,点击走框架建档原语)。
"""
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen.screen_utils import get_match_screen_name
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_screen_state import (
    get_in_match_screen_name,
)
from sr_od.application.currency_war.operations.cw_loop import (
    CwLoop,
    _prep_anchors_hit,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 路由状态常量(边匹配键;route 节点 SUCCESS 携带,边按状态精确跳转)
ST_PREP: str = '备战'
ST_DIALOG: str = '中断挑战弹窗'
ST_FAILED: str = '挑战失败'
ST_DETAIL: str = '对局详情'
ST_REPORT: str = '战报'
ST_LOBBY: str = '大厅'
ST_BATTLE: str = '战斗中'
ST_PAUSE: str = '战斗暂停'
ST_SETTLEMENT: str = '胜利结算'
ST_FAIL_STEP: str = '战败结算'

#: 连续未识别多少轮后判「大概率战斗中」进入右上 X 兜底(单次 miss 可能
#: 只是过渡帧,连续多轮全不识别才进;防过渡帧误点 X)
BATTLE_STREAK_ENTER: int = 4


class CwEntryExit(SrOperation):
    """放弃当前货币战争对局,返回大厅(退局调度器)。"""

    STATUS_AT_LOBBY: ClassVar[str] = '已返回货币战争大厅'

    #: 对局中屏名 → 路由状态(退出流程画面;识别单一源 =
    #: cw_screen_state.get_in_match_screen_name,建档精准匹配)
    ROUTE_BY_SCREEN: ClassVar[dict[str, str]] = {
        '货币战争-中断挑战弹窗': ST_DIALOG,
        '货币战争-结算-战报': ST_REPORT,
        '货币战争-结算-对局详情': ST_DETAIL,
        '货币战争-结算-失败': ST_FAIL_STEP,
        '货币战争-挑战失败': ST_FAILED,
        '货币战争-战斗暂停': ST_PAUSE,
        '货币战争-结算': ST_SETTLEMENT,
    }
    LOBBY_SCREEN: ClassVar[str] = '货币战争-大厅'
    PREP_SCREEN: ClassVar[str] = '货币战争-备战'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='退出货币战争对局')
        self._miss_streak: int = 0

    # ---- 节点1:画面路由(循环;唯一识别中枢) ----
    # 出边骨架(星形):流程节点的 SUCCESS 均经兜底边回本节点重识别;
    # 例外两条精确直边:战斗中点右上X →(弹出暂停)→ 战斗暂停撤退;
    # lobby_check 为终点(SUCCESS 无出边 = op 完成)。

    @node_from('备战退局发起')
    @node_from('弹窗放弃并结算')
    @node_from('胜利结算继续挑战')
    @node_from('战败结算推进')
    @node_from('挑战失败下一步')
    @node_from('对局详情下一页')
    @node_from('战报返回大厅')
    @node_from('战斗中点右上X')
    @node_from('战斗暂停撤退')
    @operation_node(name='画面路由', is_start_node=True, node_max_retry_times=40,
                    timeout_seconds=600)
    def route(self) -> OperationRoundResult:
        screen = self.last_screenshot

        # 对局中画面:框架建档精准匹配一次,屏名映射路由状态
        name = get_in_match_screen_name(self.ctx, screen)
        st = self.ROUTE_BY_SCREEN.get(name) if name is not None else None
        if st is not None:
            self._miss_streak = 0
            return self.round_success(st)

        # 大厅(白名单屏,不在对局中名单内,单独精准判)
        if get_match_screen_name(self.ctx, screen,
                                 screen_name_list=[self.LOBBY_SCREEN]) \
                == self.LOBBY_SCREEN:
            return self.round_success(ST_LOBBY)

        # 干净备战:备战双锚(判定单一源 = cw_loop._prep_anchors_hit,与
        # CwLoop stop_at_prep 停机位同源——两侧判定分叉会互踢死循环)
        if _prep_anchors_hit(self, screen):
            self._miss_streak = 0
            return self.round_success(ST_PREP)

        # 未识别:连续计数过渡帧防误判;丢 CwLoop 处理一次;仍未解决判战斗中。
        self._miss_streak += 1
        if self._miss_streak == 1:
            return self.round_retry('未识别(可能是过渡帧),重入重判', wait=1.5)
        if self._miss_streak == 2:
            # 委托 CwLoop:非退出流程、非备战的对局内画面(事件 overlay/
            # 补给/遭遇/位面过渡等全在 loop 分发域)由它处理到干净备战。
            # 开局画面(不在 loop 分发域)清单候实机盘点后加专用分支。
            log.info('[cw-exit] 未识别画面 → 委托 CwLoop 处理到干净备战')
            res = CwLoop(self.ctx, stop_at_prep=True).execute()
            log.info('[cw-exit] CwLoop 返回 success=%s status=%s → 重入路由',
                     res.success, res.status)
            return self.round_retry('CwLoop 处理返回,重入路由', wait=1)
        if self._miss_streak <= BATTLE_STREAK_ENTER:
            return self.round_retry('仍未识别,再等一拍', wait=1.5)
        self._miss_streak = 0
        return self.round_success(ST_BATTLE)

    # ---- 节点:备战退局发起(点门形图标 → 进入中断挑战弹窗) ----

    @node_from('画面路由', status=ST_PREP)
    @operation_node(name='备战退局发起', node_max_retry_times=10,
                    timeout_seconds=120)
    def prep_exit(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, self.PREP_SCREEN, '按钮-退出对局',
            until_find_all=[('货币战争-中断挑战弹窗', '标识-中断挑战')],
            success_wait=2)

    # ---- 节点:中断挑战弹窗 → 放弃并结算 ----
    # ⚠️ 退出语义本体,内联本 op:弹窗的常规消费方 CwScreenInterruptDialog
    # 有「绝不点放弃并结算」语义红线(误触场景要继续对局),不可复用。
    # 进入下一预期画面 = 失败演出标题(「下一步」按钮此时未出现,由下一
    # 节点的 retry 等待承载)。

    @node_from('画面路由', status=ST_DIALOG)
    @node_from('战斗暂停撤退')
    @operation_node(name='弹窗放弃并结算', node_max_retry_times=10,
                    timeout_seconds=120)
    def dialog_giveup(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, '货币战争-中断挑战弹窗', '按钮-放弃并结算',
            until_find_all=[('货币战争-挑战失败', '标识-挑战失败')],
            success_wait=2)

    # ---- 节点:胜利结算残留 → 继续挑战(继续对局,非弃局) ----

    @node_from('画面路由', status=ST_SETTLEMENT)
    @operation_node(name='胜利结算继续挑战', node_max_retry_times=10,
                    timeout_seconds=120)
    def settlement_continue(self) -> OperationRoundResult:
        # 无 until:点击成功即交回路由(对局推进后通常回备战走退局发起)
        return self.round_by_find_and_click_area(
            self.last_screenshot, '货币战争-结算', '按钮-继续挑战',
            success_wait=2)

    # ---- 节点:战败结算 → 前往结算(进对局详情) ----
    # 战败演出未完成时「前往结算」未出现 → retry 等待(演出自动完成);
    # 旧「点空白加速演出」为可选加速,收敛时删(慢几秒换结构简单)。

    @node_from('画面路由', status=ST_FAIL_STEP)
    @operation_node(name='战败结算推进', node_max_retry_times=15,
                    timeout_seconds=180)
    def settlement_fail(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, '货币战争-结算-失败', '按钮-前往结算',
            until_find_all=[('货币战争-结算-对局详情', '标识-对局未完成')],
            success_wait=2)

    # ---- 节点:挑战失败 → 下一步(进对局详情) ----

    @node_from('画面路由', status=ST_FAILED)
    @node_from('弹窗放弃并结算')
    @operation_node(name='挑战失败下一步', node_max_retry_times=15,
                    timeout_seconds=180)
    def challenge_failed(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, '货币战争-挑战失败', '按钮-下一步',
            until_find_all=[('货币战争-结算-对局详情', '标识-对局未完成')],
            success_wait=2)

    # ---- 节点:对局详情 → 下一页(进战报) ----

    @node_from('画面路由', status=ST_DETAIL)
    @node_from('挑战失败下一步')
    @operation_node(name='对局详情下一页', node_max_retry_times=10,
                    timeout_seconds=120)
    def detail_next(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, '货币战争-结算-对局详情', '按钮-下一页',
            until_find_all=[('货币战争-结算-战报', '标识-总经济')],
            success_wait=2)

    # ---- 节点:战报 → 返回货币战争(回大厅) ----

    @node_from('画面路由', status=ST_REPORT)
    @node_from('对局详情下一页')
    @operation_node(name='战报返回大厅', node_max_retry_times=10,
                    timeout_seconds=120)
    def report_back(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, '货币战争-结算-战报', '按钮-返回货币战争',
            until_find_all=[('货币战争-大厅', '标识-创业指南')],
            success_wait=2.5)

    # ---- 节点:大厅确认(终点;SUCCESS 无出边 = op 完成) ----

    @node_from('画面路由', status=ST_LOBBY)
    @operation_node(name='大厅确认', node_max_retry_times=12,
                    timeout_seconds=120)
    def lobby_check(self) -> OperationRoundResult:
        if get_match_screen_name(self.ctx, self.last_screenshot,
                                 screen_name_list=[self.LOBBY_SCREEN]) \
                != self.LOBBY_SCREEN:
            return self.round_wait('等大厅渲染', wait=2)
        return self.round_success(CwEntryExit.STATUS_AT_LOBBY)

    # ---- 节点:战斗中 → 右上 X(弹出战斗暂停) ----
    # 战斗画面无稳定 id 锚(自动战斗 UI 多变),由路由节点排除法进入
    #(连续未识别);X 坐标实证 2026-08-23,建档挂「货币战争-战斗」档。

    @node_from('画面路由', status=ST_BATTLE)
    @operation_node(name='战斗中点右上X', node_max_retry_times=15,
                    timeout_seconds=180)
    def battle_x(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, '货币战争-战斗', '按钮-右上X',
            until_find_all=[('货币战争-战斗暂停', '标识-战斗暂停')],
            success_wait=2)

    # ---- 节点:战斗暂停 → 撤退(进中断挑战弹窗) ----

    @node_from('战斗中点右上X', status='已弹出战斗暂停')
    @node_from('画面路由', status=ST_PAUSE)
    @operation_node(name='战斗暂停撤退', node_max_retry_times=10,
                    timeout_seconds=120)
    def battle_pause(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, '货币战争-战斗暂停', '按钮-撤退',
            until_find_all=[('货币战争-中断挑战弹窗', '标识-中断挑战')],
            success_wait=2)
