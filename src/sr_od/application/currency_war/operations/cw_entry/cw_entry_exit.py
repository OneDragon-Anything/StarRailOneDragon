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
#   匹配不可见,回路由会被误判未识别,演出等待在该节点内由 retry 承载;
#   委托对局循环/敌人信息关闭为表外画面的默认去处(cw-exit-dispatch)。
"""从货币战争对局中退出(放弃+结算)回大厅(退局调度器,三分发结构)。

任何可识别的对局内态(备战/战斗中/事件 overlay/胜负结算)→ 识别分发,
认出的画面必有去处,识别结果不丢弃(cw-exit-dispatch 迭代,治 2026-09-15
列车同行事故:表外画面无去处 → 落穿透双锚误判干净备战 → 原地空转):
- 退出流程画面(ROUTE_BY_SCREEN)→ 逐节点建档点击走完 弹窗→挑战失败→结算页→大厅;
- A 类备战态(含免战)→ 点门形「退出对局」图标(替代旧 ESC,误弹中断挑战史);
- 其余对局中画面 → 默认委托 CwLoop(stop_at_prep=True) 处理到可交还备战态;
  唯一特判:敌人信息浮层 → 内联关闭节点(loop 无该分支);
- 认不出(未建档/过渡帧)→ 重试数拍后按连续计数判战斗中 → 右上 X → 撤退。
全链零 ESC、零全屏 OCR(识别走框架建档精准匹配,点击走框架建档原语)。
"""
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen.screen_utils import get_match_screen_name
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_screen_state import (
    PREP_DIRECT_EXIT_SCREENS,
    get_in_match_screen_name,
)
from sr_od.application.currency_war.operations.cw_loop import CwLoop
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
ST_SETTLEMENT: str = '胜利结算'
ST_FAIL_STEP: str = '战败结算'
ST_DELEGATE: str = '委托对局循环'
ST_ENEMY_INFO: str = '敌人信息浮层'

#: 连续未识别多少轮后判「大概率战斗中」进入右上 X 兜底(单次 miss 可能
#: 只是过渡帧,连续多轮全不识别才进;防过渡帧误点 X)
BATTLE_STREAK_ENTER: int = 4


class CwEntryExit(SrOperation):
    """放弃当前货币战争对局,返回大厅(退局调度器)。"""

    STATUS_AT_LOBBY: ClassVar[str] = '已返回货币战争大厅'

    #: 对局中屏名 → 路由状态(退出流程画面;识别单一源 =
    #: cw_screen_state.get_in_match_screen_name,建档精准匹配)。
    #: 不含「货币战争-战斗暂停」:该屏无 id_mark,建档精准匹配结构性
    #: 不可达,入表即死项;实际入口 = 「战斗中点右上X」节点的直边
    #: (until 单锚命中「标识-战斗暂停」),勿再依赖路由表到达它。
    ROUTE_BY_SCREEN: ClassVar[dict[str, str]] = {
        '货币战争-中断挑战弹窗': ST_DIALOG,
        '货币战争-结算-战报': ST_REPORT,
        '货币战争-结算-对局详情': ST_DETAIL,
        '货币战争-结算-失败': ST_FAIL_STEP,
        '货币战争-挑战失败': ST_FAILED,
        '货币战争-结算': ST_SETTLEMENT,
    }
    LOBBY_SCREEN: ClassVar[str] = '货币战争-大厅'
    #: A 类名单(直接退出)引用单一源常量,禁在本文件复写
    DIRECT_EXIT_SCREENS: ClassVar[frozenset[str]] = PREP_DIRECT_EXIT_SCREENS
    PREP_SCREEN: ClassVar[str] = '货币战争-备战'
    ENEMY_INFO_SCREEN: ClassVar[str] = '货币战争-敌人信息浮层'

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
    @node_from('委托对局循环')
    @node_from('敌人信息关闭')
    @operation_node(name='画面路由', is_start_node=True, node_max_retry_times=40,
                    timeout_seconds=600)
    def route(self) -> OperationRoundResult:
        """三分发路由(cw-exit-dispatch §2.1,判定序即设计表序①-⑥)。

        认出的画面必有去处:②③④⑤各自精确跳转,⑤兜住全部表外画面;
        仅 None(认不出)走⑥计数兜底。②与③之间不再有任何穿透双锚判定
        ——「能不能点退出」由③的屏名名单表达(穿透判定误判是事故根因)。
        """
        screen = self.last_screenshot

        # ① 全集建档识别(单一源) → ② 退出过程画面分发表
        name = get_in_match_screen_name(self.ctx, screen)
        st = self.ROUTE_BY_SCREEN.get(name) if name is not None else None
        if st is not None:
            self._miss_streak = 0
            return self.round_success(st)

        # ③ A 类:可直接点门形图标退出的备战态(含免战;屏名白名单,
        # 非锚判定——免战画面「出战」锚被「跳过」替换,锚判定恒 False)
        if name in PREP_DIRECT_EXIT_SCREENS:
            self._miss_streak = 0
            return self.round_success(ST_PREP)

        # ④ 大厅(白名单屏,不在对局中名单内,单独精准判)
        if get_match_screen_name(self.ctx, screen,
                                 screen_name_list=[self.LOBBY_SCREEN]) \
                == self.LOBBY_SCREEN:
            return self.round_success(ST_LOBBY)

        # ⑤ 默认委托:非退出流程的对局中画面(穷举清单外零维护——新建档
        # 画面识别即收)。唯一特判:敌人信息浮层(loop 无该分支)内联关闭。
        if name is not None:
            self._miss_streak = 0
            if name == self.ENEMY_INFO_SCREEN:
                return self.round_success(ST_ENEMY_INFO)
            return self.round_success(ST_DELEGATE)

        # ⑥ 认不出(未建档/过渡帧):重试数拍等画面稳定,连续仍认不出按
        # 计数判战斗中 → 右上 X 兜底。不做 CwLoop 委托——已建档画面在⑤
        # 全部有去处,落到此的未建档画面委托对局循环同样无力(纯冗余,删)。
        self._miss_streak += 1
        if self._miss_streak <= BATTLE_STREAK_ENTER:
            return self.round_retry('未识别(过渡帧/未建档),等待画面稳定',
                                    wait=1.5)
        self._miss_streak = 0
        return self.round_success(ST_BATTLE)

    # ---- 节点:委托对局循环(⑤默认委托;处理到可交还备战态回路由) ----

    @node_from('画面路由', status=ST_DELEGATE)
    @operation_node(name='委托对局循环', node_max_retry_times=10,
                    timeout_seconds=600)
    def delegate_loop(self) -> OperationRoundResult:
        # CwLoop 复用其既有身份分发与停滞看门狗(单一出口,退出链不维护
        # 第二张「屏名→op」映射表);stop_at_prep 停机位与路由③共用 A 类
        # 名单常量 → 两侧对「是否已到可交还态」结论恒一致,无互踢往返。
        res = CwLoop(self.ctx, stop_at_prep=True).execute()
        log.info('[cw-exit] 委托对局循环返回 success=%s status=%s',
                 res.success, res.status)
        if res.success:
            return self.round_success('对局循环已交还,重入路由')
        return self.round_retry('对局循环未交还,重试', wait=1)

    # ---- 节点:敌人信息关闭(⑤唯一特判;loop 无该分支,内联关闭) ----
    # 触发场景 = 观察采集模式(自动对局不打开,低频);关闭后回路由重识别。

    @node_from('画面路由', status=ST_ENEMY_INFO)
    @operation_node(name='敌人信息关闭', node_max_retry_times=10,
                    timeout_seconds=120)
    def enemy_info_close(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, self.ENEMY_INFO_SCREEN, '按钮-关闭',
            until_not_find_all=[(self.ENEMY_INFO_SCREEN, '标识-敌方信息')],
            success_wait=1)

    # ---- 节点:备战退局发起(点门形图标 → 进入中断挑战弹窗) ----

    @node_from('画面路由', status=ST_PREP)
    @operation_node(name='备战退局发起', node_max_retry_times=10,
                    timeout_seconds=120)
    def prep_exit(self) -> OperationRoundResult:
        # 备战档「按钮-退出对局」纯定位区对 A 类两屏共用:免战画面门形
        # 图标同位同款(归档帧实证),无需独立 area。
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
    @operation_node(name='战斗暂停撤退', node_max_retry_times=10,
                    timeout_seconds=120)
    def battle_pause(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, '货币战争-战斗暂停', '按钮-撤退',
            until_find_all=[('货币战争-中断挑战弹窗', '标识-中断挑战')],
            success_wait=2)
