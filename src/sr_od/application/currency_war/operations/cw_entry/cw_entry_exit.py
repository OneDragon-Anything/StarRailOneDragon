# 退局调度器架构(重写,用户设计):
#   退出 op 的职责 = 调度,不是画面处理——旧版在单节点内联十几个全屏 OCR
#   分支复制各画面 op 的处理逻辑,复制体随时间漂移:「角色详情」
#   裸词直接当识别标志用(与商店卡牌详情弹窗同词全等,垄断 26 分钟),退出 op 的复制体
#   未同步 → 大世界详情页误命中,30 轮全打空 fail(日志实证)。治本 = 画面
#   处理单一源回到各画面 op / CwLoop,本 op 只做识别与跳转。
# 画面识别单一源 = cw_screen_state.get_in_match_screen_name(建档 id_mark
#   精准匹配的框架实现);点击与推进判定 = round_by_find_and_click_area:
#   until_find_all = 点击后进入下一预期画面;until_not_find_all = 点击后
#   离开当前画面;按钮未现(演出中)→ round_retry 等待;节点预算兜底。
# 节点链(用户定稿,星形):节点1 画面路由(识别→按屏名跳转)为唯一中枢,
#   流程节点做完单动作即回路由重识别;lobby_check 为终点(SUCCESS = op 完成);
#   例外:弹窗放弃后直边进挑战失败节点——失败演出帧(单识别标志态)对建档精准
#   匹配不可见,回路由会被误判未识别,演出等待在该节点内由 retry 承载;
#   委托对局循环为表外画面的默认去处(cw-exit-dispatch)。
"""从货币战争对局中退出(放弃+结算)回大厅(退局调度器,三分发结构)。

任何可识别的对局内态(备战/战斗中/事件 overlay/胜负结算)→ 识别分发,
认出的画面必有去处,识别结果不丢弃(cw-exit-dispatch 迭代,治
列车同行事故:表外画面无去处 → 落穿透式两识别标志同帧命中判定误判干净备战 → 原地空转):
- 退出流程画面(ROUTE_BY_SCREEN)→ 逐节点建档点击走完 弹窗→挑战失败→结算页→大厅;
- A 类备战态(含免战 / 茶歇预告两个出战钮形态变体)→ 点门形「退出对局」图标(替代旧 ESC,误弹中断挑战史);
- 其余对局中画面 → 默认委托 CwLoop(stop_at_prep=True) 处理到可交还备战态
  (零特判:全部表外画面同一去处;敌人信息浮层等清理型浮层由 loop 阶段一
  身份分发派对应画面 op,终态形态见待跟进事项「敌人信息浮层建画面 op」条);
- 认不出(未建档/过渡帧)→ 重试数拍后按连续计数判战斗中 → 右上 X → 撤退;
  右上 X 节点每轮先认画面,认出非战斗自家画面即回路由重识别(误入时的回头路)。
全链零 ESC、零全屏 OCR(识别走框架建档精准匹配,点击走框架建档原语)。
"""
from typing import ClassVar

import numpy as np
from cv2.typing import MatLike

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
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

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
ST_MODE_ONGOING: str = '模式选择进行中'
ST_GIVEUP_CONFIRM: str = '结束结算确认弹窗'

#: 连续未识别多少轮后判「大概率战斗中」进入右上 X 兜底(单次 miss 可能
#: 只是过渡帧,连续多轮全不识别才进;防过渡帧误点 X)
BATTLE_STREAK_ENTER: int = 4

#: 右上 X 兜底的静态页哨:连续多少轮节点重入截图逐像素不变即提前失败。
#: 对无 X 控件的页面(未建档报告页/建档锚漂移),area 定位是静态 rect 直点,
#: 画面永不变化 → until 永不命中,原路径唯一硬边界是节点 180s 超时(框架
#: 对 WAIT 不计 retry 且清零计数,retry 网在此路径从不生效)。取 3:计数自
#: 基线帧之后的重入轮起算,共 4 次节点重入 ≈ 12s(每轮 until 等待 ~3s),
#: 足够排除「点击已落地但画面渲染慢」的转场帧(转场在 route ⑥ 已耗 4 拍)。
BATTLE_X_DEAD_CLICK_LIMIT: int = 3

#: 「战斗中点右上X」返回成功、状态为本值 = 认出了一个路由有去处的画面,不点、
#: 回路由重识别(边匹配键)。
ST_SCREEN_RECOGNIZED: str = '认出画面'

#: 「战斗中点右上X」每轮先认画面时的豁免名单 = 「点 X → 弹出暂停」这条路自己
#: 经过、且建档识别认得出的两个画面。认出它们按认不出处理(继续点 X):
#: 战斗画面若回头,真战斗永远点不了 X;暂停画面是点 X 成功后的下一轮画面,
#: 回头会改变点 X 之后的既有走法。也不计入重复认出计数(真战斗连续多轮认出
#: 战斗画面是常态,计数会把正常战斗判成失败)。
BATTLE_X_OWN_SCREENS: frozenset[str] = frozenset({
    '货币战争-战斗', '货币战争-战斗暂停',
})

#: 「战斗中点右上X」不点就退出时,连续认出同一个画面名多少次即判失败。
#: 新分支只认路由有去处的画面,正常不会路由处理不动;但路由判「战斗中」
#: 返回的是成功,引擎对非重试结果清零节点重试与超时预算,路由↔点 X 两个节点
#: 互踢没有任何一层预算会耗尽。第 1 次认出回路由是正常回头路,第 2 次同名
#: = 路由没把它处理掉,失败比空转对。
BATTLE_X_RECOGNIZED_REPEAT_LIMIT: int = 2

#: 挂起对局入口两屏(白名单屏,不在对局中名单内):判定走 route ④b 显式
#: 点名,不进 ROUTE_BY_SCREEN(该表只收 get_in_match_screen_name 可见的
#: 对局中屏);处置链下半段(挑战失败→详情→战报→大厅)与既有节点完全同构。
#: 模块级常量:消费方(返回大世界 op/入口链/测试委托假类)不经类身份引用。
MODE_ONGOING_SCREEN: str = '货币战争-模式选择-进行中'
GIVEUP_CONFIRM_SCREEN: str = '货币战争-模式选择-结束结算确认'


class CwEntryExit(CwOperation):
    """放弃当前货币战争对局,返回大厅(退局调度器)。
    起点:货币战争对局内任意画面 + 有挂起对局的入口画面
    (模式选择-进行中/结束结算确认弹窗);终点:货币战争大厅(对局已放弃)。
    副作用:放弃当前对局进度,不可恢复。挂起对局(服务端保留的未完成局)
    同样被放弃并结算——自动化语义一律弃局,绝不「继续进度」续跑;
    人工玩家手动挂起的对局亦然。"""

    STATUS_AT_LOBBY: ClassVar[str] = '已返回货币战争大厅'

    #: 对局中屏名 → 路由状态(退出流程画面;识别单一源 =
    #: cw_screen_state.get_in_match_screen_name,建档精准匹配)。
    #: 不含「货币战争-战斗暂停」:该屏无 id_mark,建档精准匹配结构性
    #: 不可达,入表即死项;实际入口 = 「战斗中点右上X」节点的直边
    #: (until 单识别标志命中「标识-战斗暂停」),勿再依赖路由表到达它。
    ROUTE_BY_SCREEN: ClassVar[dict[str, str]] = {
        '货币战争-中断挑战弹窗': ST_DIALOG,
        '货币战争-结算-战报': ST_REPORT,
        '货币战争-结算-对局详情': ST_DETAIL,
        '货币战争-结算-失败': ST_FAIL_STEP,
        '货币战争-挑战失败': ST_FAILED,
        '货币战争-结算': ST_SETTLEMENT,
    }
    LOBBY_SCREEN: ClassVar[str] = '货币战争-大厅'
    PREP_SCREEN: ClassVar[str] = '货币战争-备战'

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='退出货币战争对局')
        self._miss_streak: int = 0
        # 「战斗中点右上X」静态页哨状态(仅 battle_x 节点读写;节点函数每轮
        # 重入不销毁 self,跨轮承载):上一轮进入节点时的帧与连续无变化计数。
        self._battle_x_prev_frame: MatLike | None = None
        self._battle_x_static_rounds: int = 0
        # 同上(仅 battle_x 读写,跨轮重入承载):本轮之前连续认出的画面名与次数;
        # 认不出的那一轮清零。
        self._battle_x_recognized_name: str | None = None
        self._battle_x_recognized_times: int = 0

    # ---- 节点1:画面路由(循环;唯一识别中枢) ----
    # 出边骨架(星形):流程节点的 SUCCESS 均经兜底边回本节点重识别;
    # 例外两条精确直边:战斗中点右上X →(弹出暂停)→ 战斗暂停撤退;
    # lobby_check 为终点(SUCCESS 无出边 = op 完成)。

    @node_from('备战退局发起')
    @node_from('弹窗放弃并结算')
    @node_from('模式选择放弃挂起局')
    @node_from('结束结算确认放弃')
    @node_from('胜利结算继续挑战')
    @node_from('战败结算推进')
    @node_from('挑战失败下一步')
    @node_from('对局详情下一页')
    @node_from('战报返回大厅')
    @node_from('战斗中点右上X')
    @node_from('战斗中点右上X', status=ST_SCREEN_RECOGNIZED)
    @node_from('战斗暂停撤退')
    @node_from('委托对局循环')
    @operation_node(name='画面路由', is_start_node=True, node_max_retry_times=40,
                    timeout_seconds=600)
    def route(self) -> OperationRoundResult:
        """三分发路由(cw-exit-dispatch §2.1,判定序即设计表序①-⑥)。

        认出的画面必有去处:②③④⑤各自精确跳转,⑤兜住全部表外画面;
        仅 None(认不出)走⑥计数兜底。②与③之间不再有任何穿透式两识别标志同帧命中判定
        ——「能不能点退出」由③的屏名名单表达(穿透判定误判是事故根因)。
        """
        screen = self.last_screenshot

        # ① 全集建档识别(单一源) → ② 退出过程画面分发表
        name = get_in_match_screen_name(self.ctx, screen)
        st = self.ROUTE_BY_SCREEN.get(name) if name is not None else None
        if st is not None:
            self._miss_streak = 0
            return self.round_success(st)

        # ③ A 类:可直接点门形图标退出的备战态(含出战钮形态变体;屏名白名单,
        # 非识别标志判定——变体画面「出战」识别标志被「跳过」/「幕后茶歇」替换,
        # 识别标志判定恒 False)
        if name in PREP_DIRECT_EXIT_SCREENS:
            self._miss_streak = 0
            return self.round_success(ST_PREP)

        # ④ 大厅(白名单屏,不在对局中名单内,单独精准判)
        if get_match_screen_name(self.ctx, screen,
                                 screen_name_list=[self.LOBBY_SCREEN]) \
                == self.LOBBY_SCREEN:
            return self.round_success(ST_LOBBY)

        # ④b 挂起对局入口两屏(白名单屏,同④显式点名;不进 ROUTE_BY_SCREEN——
        # 该表只收 get_in_match_screen_name 可见的对局中屏,两屏经白名单排除)。
        # 判定 = 屏级全 id_mark AND(双锚:「进行中」∧「结束并结算」),同族
        # 模拟宇宙-世界详情页有结束并结算但无「进行中」分类,凑不齐组合。
        pending_name = get_match_screen_name(
            self.ctx, screen,
            screen_name_list=[MODE_ONGOING_SCREEN, GIVEUP_CONFIRM_SCREEN])
        if pending_name == MODE_ONGOING_SCREEN:
            return self.round_success(ST_MODE_ONGOING)
        if pending_name == GIVEUP_CONFIRM_SCREEN:
            return self.round_success(ST_GIVEUP_CONFIRM)

        # ⑤ 默认委托:非退出流程的对局中画面(穷举清单外零维护——新建档
        # 画面识别即收,零特判;敌人信息浮层等清理型浮层由委托的 loop 经
        # 阶段一身份分发派对应画面 op 处理)。
        if name is not None:
            self._miss_streak = 0
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
        # cleanup_delegate=True = 委托清理模式(loop 耗尽出口维持 fail 由
        # 本节点重试承接):委托实例失败计数从零重算,若用默认参,粘滞
        # 耗尽会以交接 success 返回 → 本节点误判清理完成,残局遗留。
        res = CwLoop(self.ctx, stop_at_prep=True,
                     cleanup_delegate=True).execute()
        log.info('[cw-exit] 委托对局循环返回 success=%s status=%s',
                 res.success, res.status)
        if res.success:
            return self.round_success('对局循环已交还,重入路由')
        return self.round_retry('对局循环未交还,重试', wait=1)

    # ---- 节点:备战退局发起(点门形图标 → 进入中断挑战弹窗) ----

    @node_from('画面路由', status=ST_PREP)
    @operation_node(name='备战退局发起', node_max_retry_times=10,
                    timeout_seconds=120)
    def prep_exit(self) -> OperationRoundResult:
        # 备战档「按钮-退出对局」纯定位区对 A 类各屏共用:变体画面门形
        # 图标同位同款(各变体归档帧实证),无需独立 area。
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

    # ---- 节点:模式选择-进行中 → 结束并结算(挂起对局处置入口) ----
    # ⚠️ 「放弃并结算」语义红线同「弹窗放弃并结算」节点:此处是本 op 的
    # 退局语义本体(挂起局一律弃局,见类 docstring);弹窗的「关闭」钮
    # (取消语义 = 留在挂起态)无生产消费方,不建退出分支,area 在档备用。

    @node_from('画面路由', status=ST_MODE_ONGOING)
    @operation_node(name='模式选择放弃挂起局', node_max_retry_times=10,
                    timeout_seconds=120)
    def mode_ongoing_giveup(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, MODE_ONGOING_SCREEN, '按钮-结束并结算',
            until_find_all=[(GIVEUP_CONFIRM_SCREEN, '标识-确认文案')],
            success_wait=2)

    # ---- 节点:结束结算确认弹窗 → 放弃并结算 ----

    @node_from('画面路由', status=ST_GIVEUP_CONFIRM)
    @operation_node(name='结束结算确认放弃', node_max_retry_times=10,
                    timeout_seconds=120)
    def giveup_confirm(self) -> OperationRoundResult:
        return self.round_by_find_and_click_area(
            self.last_screenshot, GIVEUP_CONFIRM_SCREEN, '按钮-放弃并结算',
            until_find_all=[('货币战争-挑战失败', '标识-挑战失败')],
            success_wait=2)

    # ---- 节点:胜利结算残留 → 继续挑战(继续对局,非弃局) ----

    @node_from('画面路由', status=ST_SETTLEMENT)
    @operation_node(name='胜利结算继续挑战', node_max_retry_times=10,
                    timeout_seconds=120)
    def settlement_continue(self) -> OperationRoundResult:
        # 无 until:点击成功即结束本次访问路由(对局推进后通常回备战走退局发起)
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
            until_find_all=[('货币战争-大厅', '标识-玩法名')],
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
    # 战斗画面无稳定 id 识别标志(自动战斗 UI 多变),由路由节点排除法进入
    #(连续未识别);X 坐标实证,建档挂「货币战争-战斗」档。

    @node_from('画面路由', status=ST_BATTLE)
    @operation_node(name='战斗中点右上X', node_max_retry_times=15,
                    timeout_seconds=180)
    def battle_x(self) -> OperationRoundResult:
        cur = self.last_screenshot

        # ① 认画面(误入本节点时的回头路,每轮重入、点击之前先跑):本节点唯一
        # 成功条件是「战斗暂停」出现,点击把画面点到别处(如备战的「数据统计」
        # 钮与右上X区域重叠)后出不去,原路只能耗到节点超时。只认路由有去处
        # 的画面——对局中画面名单(路由②③⑤全接)与大厅(路由④,同函数同参数);
        # 大厅态白名单里的弹窗画面路由没有去处,认了就是两节点互踢空转,留给
        # 下方点 X 老路顺手关掉。认不出 = 与改前一样走哨、点 X。
        name = get_in_match_screen_name(self.ctx, cur)
        if name is None:
            name = get_match_screen_name(self.ctx, cur,
                                         screen_name_list=[self.LOBBY_SCREEN])
        if name in BATTLE_X_OWN_SCREENS:
            name = None
        if name is not None:
            if name == self._battle_x_recognized_name:
                self._battle_x_recognized_times += 1
            else:
                self._battle_x_recognized_name = name
                self._battle_x_recognized_times = 1
            if self._battle_x_recognized_times >= BATTLE_X_RECOGNIZED_REPEAT_LIMIT:
                return self.round_fail(
                    f'连续{self._battle_x_recognized_times}次认出同一画面「{name}」,路由无法处理')
            # 哨的计数含义是「本次进入本节点后点了几轮画面都没变」;经路由再被
            # 送回来是又一次进入,接着上次的计数会把同一张静态画面误判成点了没反应。
            self._battle_x_prev_frame = None
            self._battle_x_static_rounds = 0
            return self.round_success(status=ST_SCREEN_RECOGNIZED)
        self._battle_x_recognized_name = None
        self._battle_x_recognized_times = 0

        # ② 静态页哨(认画面之后、点击之前,每轮重入都跑):「按钮-右上X」是纯定位区,对无 X
        # 控件的页面恒点击恒成功、画面永不变化 → until 永不命中,原路径
        # 唯一硬边界是本节点 180s 超时(WAIT 不计 retry 且清零计数,retry
        # 网在此路径从不生效)。连续 BATTLE_X_DEAD_CLICK_LIMIT 轮与上一轮
        # 帧逐像素不变 → 立即失败,把此类失效从 3 分钟压到 ~12s。判据 =
        # np.array_equal 全等(静态页逐帧同图,事故连拍字节全等实证);
        # 上一帧为 None / shape 不符 / 比较异常一律按「帧变化」清零——
        # 截屏损坏帧真实存在(事故连拍含不可解码帧),不中断节点。
        prev = self._battle_x_prev_frame
        changed = True
        if prev is not None and prev.shape == cur.shape:
            try:
                changed = not np.array_equal(prev, cur)
            except Exception:  # noqa: BLE001  损坏帧按帧变化处理
                changed = True
        self._battle_x_prev_frame = cur
        self._battle_x_static_rounds = 0 if changed \
            else self._battle_x_static_rounds + 1
        if self._battle_x_static_rounds >= BATTLE_X_DEAD_CLICK_LIMIT:
            return self.round_fail(
                f'右上X点击无效(连续{self._battle_x_static_rounds}轮画面无变化,疑无X页面)')
        # ③ 点 X 并等「战斗暂停」出现
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
