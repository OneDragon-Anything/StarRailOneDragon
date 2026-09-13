# 退局调度器架构(2026-09-13 重写,用户设计):
#   退出 op 的职责 = 调度,不是画面处理——旧版在单节点内联 12 处全屏 OCR
#   分支复制各画面 op 的处理逻辑,复制体
#   随时间漂移:T-163 已把「角色详情」裸词锚化(与商店卡牌详情弹窗同词
#   LCS 1.0 全等,垄断 26 分钟),退出 op 的复制体未同步 → 2026-09-13
#   09:11 大世界详情页误命中,30 轮 140s 全打空 fail(日志实证)。治本 =
#   画面处理单一源回到各画面 op / CwLoop,本 op 只做识别与跳转。
# 判定纪律:画面识别 = 建档多锚全命中(完整 id),禁单词 OCR 判定;
#   点击 = 建档 area 中心 + pc_alt(锁光标恢复态加固,2026-09-02 一条龙
#   恢复链事故;框架 find_and_click 不透传 pc_alt,故取中心显式点)。
# 节点链(用户定稿):
#   节点1 画面路由(循环):退出流程画面→带状态跳对应节点;干净备战→
#     退局发起;loop 能处理的画面→委托 CwLoop(stop_at_prep)处理到回备战;
#     连续未识别→大概率战斗中→点右上 X。
#   节点2~7 = 退出流程每画面一节点:备战发起→弹窗放弃并结算→挑战失败
#     下一步→对局详情下一页→战报返回→大厅。
#   节点B1/B2 = 战斗中兜底:右上 X→战斗暂停(有档)→撤退→接回弹窗节点,
#     后半段与主链重合。
# 建档依据(2026-09-13 手动退局实录逐帧实测):结算链 3 页按钮同槽
#   (≈959,900,仅文字变:下一步/下一页/返回货币战争);演出帧(无按钮)
#   与完成帧(下一步出现)构成「挑战失败」档模糊/精准两态;「对局未完成
#   详情」「战报」两档为本次实测新增(三锚 id_mark,离线截图验证精准)。

"""从货币战争对局中退出(放弃+结算)回大厅(退局调度器)。

任何可识别的对局内态(备战/战斗中/事件 overlay/胜负结算)→ 识别分发:
- 退出流程画面 → 逐节点建档点击走完 弃局→结算3页→大厅;
- 干净备战 → 点门形「退出对局」图标(替代旧 ESC,bug#2 三次实锤);
- loop 能处理的画面 → 委托 CwLoop(stop_at_prep=True) 处理到回备战;
- 连续未识别(大概率战斗中)→ 右上 X → 战斗暂停 → 撤退 → 接弹窗节点。
全链零 ESC、零全屏 OCR(判定=建档多锚全命中,点击=建档 area 中心)。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
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
#: 只是过渡帧,连续两轮全锚 miss 才进;防过渡帧误点 X)
BATTLE_STREAK_ENTER: int = 2


class CwEntryExit(SrOperation):
    """放弃当前货币战争对局,返回大厅(退局调度器)。"""

    STATUS_AT_LOBBY: str = '已返回货币战争大厅'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='退出货币战争对局')
        self._miss_streak: int = 0

    # ---- 判定(建档多锚全命中;与外循环分发判定同源同参) ----

    def _hit(self, screen: MatLike | None, screen_name: str,
             area_names: tuple[str, ...]) -> bool:
        """画面判定:指定档的全部锚 area 逐个命中才算(完整 id,禁单词判定)。"""
        for area in area_names:
            if not self.round_by_find_area(
                    screen, screen_name, area, crop_first=False).is_success:
                return False
        return True

    def _is_dialog(self, screen: MatLike | None) -> bool:
        return self._hit(screen, '货币战争-中断挑战弹窗',
                         ('标识-中断挑战', '按钮-放弃并结算'))

    def _is_challenge_failed(self, screen: MatLike | None) -> bool:
        return self._hit(screen, '货币战争-挑战失败',
                         ('标识-挑战失败', '按钮-下一步'))

    def _is_settlement_detail(self, screen: MatLike | None) -> bool:
        return self._hit(screen, '货币战争-结算-对局详情',
                         ('标识-对局未完成', '标识-投资环境', '按钮-下一页'))

    def _is_settlement_report(self, screen: MatLike | None) -> bool:
        return self._hit(screen, '货币战争-结算-战报',
                         ('标识-总经济', '标识-阵容价值', '按钮-返回货币战争'))

    def _is_lobby(self, screen: MatLike | None) -> bool:
        return self._hit(screen, '货币战争-大厅',
                         ('标识-创业指南', '按钮-开始货币战争'))

    def _is_battle_pause(self, screen: MatLike | None) -> bool:
        return self._hit(screen, '货币战争-战斗暂停',
                         ('标识-战斗暂停', '按钮-撤退'))

    def _is_settlement(self, screen: MatLike | None) -> bool:
        """胜利结算屏(打赢 boss 的「挑战成功/挑战结束+继续挑战」残留态)。
        处理 = 点继续挑战继续对局(非弃局),后由路由重判回备战走退局发起。"""
        return self._hit(screen, '货币战争-结算',
                         ('按钮-继续挑战', '标识-挑战成功'))

    def _is_settlement_fail_step1(self, screen: MatLike | None) -> bool:
        """战败结算步骤1帧(战败演出未完:点击空白加速,「前往结算」未现)。
        双锚 = 挑战进度(战败独有)+ 点击空白加速(步骤1 独有,演出完即被
        「前往结算」顶替);与位面过渡「点击空白处继续」的区分靠 rect 不相交
        (docs/game/screens/currency_war_settlement_fail.md 状态流转)。"""
        return self._hit(screen, '货币战争-结算-失败',
                         ('标识-挑战进度', '提示-点击空白加速'))

    def _is_settlement_fail_step2(self, screen: MatLike | None) -> bool:
        """战败结算步骤2帧(演出完成:「前往结算」出现)。"""
        return self._hit(screen, '货币战争-结算-失败', ('按钮-前往结算',))

    def _is_clean_prep(self, screen: MatLike | None) -> bool:
        """干净备战判定:备战双锚(判定单一源 = cw_loop._prep_anchors_hit,
        与 CwLoop stop_at_prep 停机位同源——两侧判定分叉会互踢死循环)。"""
        return _prep_anchors_hit(self, screen)

    def _click_area(self, screen_name: str, area_name: str) -> bool:
        """建档 area 中心 + pc_alt 点击;area 缺失 fail-closed 返回 False。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        if area is None:
            log.error('[cw-exit] area 缺失:%s / %s', screen_name, area_name)
            return False
        self.ctx.controller.mouse_move(area.center)
        self.ctx.controller.click(area.center, pc_alt=True)
        return True

    # ---- 节点1:画面路由(循环) ----
    # 出边骨架(星形):全部流程节点的 SUCCESS 均经兜底边回本节点重识别——
    # 本节点是唯一识别中枢,流程节点只做「锚校验 + 单动作」;lobby_check
    # 例外(终点,不回路由,其 SUCCESS = op 完成)。node_from 挂本方法 =
    # 声明「从流程节点回路由」的兜底边(ignore_status,success 默认 True)。

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
        # 判定序:真模态弹窗最优先(遮罩会压住底层档锚),结算族按链序,
        # 大厅(完成态)与备战(发起态)随后。
        if self._is_dialog(screen):
            return self.round_success(ST_DIALOG)
        if self._is_settlement_report(screen):
            return self.round_success(ST_REPORT)
        if self._is_settlement_detail(screen):
            return self.round_success(ST_DETAIL)
        if (self._is_settlement_fail_step1(screen)
                or self._is_settlement_fail_step2(screen)):
            # 战败结算屏(真实打输后的失败链入口,与弃局「挑战失败」链分流):
            # 点空白加速/前往结算后交回路由,后续详情/战报段共用。
            return self.round_success(ST_FAIL_STEP)
        if self._is_settlement(screen):
            # 胜利结算残留:点继续挑战是继续对局(清场语义,T-57),非弃局;
            # 处理完回路由重判(通常回备战再走退局发起)。
            return self.round_success(ST_SETTLEMENT)
        if self._is_battle_pause(screen):
            return self.round_success(ST_PAUSE)
        if self._is_challenge_failed(screen):
            return self.round_success(ST_FAILED)
        if self._is_lobby(screen):
            return self.round_success(ST_LOBBY)
        if self._is_clean_prep(screen):
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
        if self._miss_streak <= BATTLE_STREAK_ENTER + 1:
            return self.round_retry('仍未识别,再等一拍', wait=1.5)
        self._miss_streak = 0
        return self.round_success(ST_BATTLE)

    # ---- 节点2:备战退局发起 ----

    @node_from('画面路由', status=ST_PREP)
    @operation_node(name='备战退局发起', node_max_retry_times=10,
                    timeout_seconds=120)
    def prep_exit(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self._is_clean_prep(screen):
            # 双锚不在 = 已弹窗(点图标生效)或画面漂移;交路由重判。
            return self.round_success('备战锚不在,交回路由')
        if self._click_area('货币战争-备战', '按钮-退出对局'):
            return self.round_retry('已点退出对局图标,等中断挑战弹窗', wait=2)
        return self.round_fail('按钮-退出对局 area 缺失,退局链无法发起(ESC 已禁用)')

    # ---- 节点3:中断挑战弹窗 → 放弃并结算 ----
    # ⚠️ 退出语义本体,内联本 op:弹窗的常规消费方 CwScreenInterruptDialog
    # 有「绝不点放弃并结算」语义红线(误触场景要继续对局),不可复用。

    @node_from('画面路由', status=ST_DIALOG)
    @node_from('战斗暂停撤退')
    @operation_node(name='弹窗放弃并结算', node_max_retry_times=10,
                    timeout_seconds=120)
    def dialog_giveup(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self._is_dialog(screen):
            return self.round_success('弹窗不在,交回路由')
        if self._click_area('货币战争-中断挑战弹窗', '按钮-放弃并结算'):
            return self.round_retry('已点放弃并结算,等结算演出', wait=2)
        return self.round_fail('按钮-放弃并结算 area 缺失')

    # ---- 节点4:胜利结算残留 → 继续挑战(继续对局,非弃局) ----

    @node_from('画面路由', status=ST_SETTLEMENT)
    @operation_node(name='胜利结算继续挑战', node_max_retry_times=10,
                    timeout_seconds=120)
    def settlement_continue(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self._is_settlement(screen):
            # 继续挑战生效 = 结算屏消失(对局推进);交回路由重判
            #(通常回备战,下一轮走退局发起)。
            return self.round_success('结算屏不在,交回路由')
        if self._click_area('货币战争-结算', '按钮-继续挑战'):
            return self.round_retry('已点继续挑战,等对局推进', wait=2)
        return self.round_fail('按钮-继续挑战 area 缺失')

    # ---- 节点4:战败结算(步骤1 点空白加速 / 步骤2 前往结算) ----

    @node_from('画面路由', status=ST_FAIL_STEP)
    @operation_node(name='战败结算推进', node_max_retry_times=12,
                    timeout_seconds=180)
    def settlement_fail(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if self._is_settlement_fail_step1(screen):
            # 点空白 = 演出加速(坐标单一源 = 位面过渡/区域-空白点击,与对局内
            # 主路径 CwScreenBattleWait.BLANK 同 Rect;右下真空档避中央演出元素)
            if self._click_area('货币战争-位面过渡', '区域-空白点击'):
                return self.round_retry('已点空白加速演出', wait=2)
            return self.round_fail('区域-空白点击 area 缺失')
        if self._is_settlement_fail_step2(screen):
            if self._click_area('货币战争-结算-失败', '按钮-前往结算'):
                return self.round_retry('已点前往结算,交回路由走结算页链', wait=2)
            return self.round_fail('按钮-前往结算 area 缺失')
        # 两子态锚都不在 = 演出推进完毕、画面已流转 → 交回路由识别后续
        #(详情/战报/大厅段与弃局链共用)。
        return self.round_success('战败结算屏已流转,交回路由')

    # ---- 节点5:挑战失败(演出等待 → 下一步) ----

    @node_from('画面路由', status=ST_FAILED)
    @node_from('弹窗放弃并结算')
    @operation_node(name='挑战失败下一步', node_max_retry_times=12,
                    timeout_seconds=180)
    def challenge_failed(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self._is_challenge_failed(screen):
            # 完成帧锚(下一步按钮)不在 = 演出中(WAIT 不计预算,节点
            # timeout_seconds 兜底演出超长)或画面漂移(WAIT 数拍后 timeout
            # fail 交回外层,不静默续跑)。
            return self.round_wait('等失败演出完成(下一步按钮出现)', wait=2)
        if self._click_area('货币战争-挑战失败', '按钮-下一步'):
            return self.round_retry('已点下一步,等对局详情页', wait=2)
        return self.round_fail('按钮-下一步 area 缺失')

    # ---- 节点5:对局详情 → 下一页 ----

    @node_from('画面路由', status=ST_DETAIL)
    @node_from('挑战失败下一步')
    @operation_node(name='对局详情下一页', node_max_retry_times=10,
                    timeout_seconds=120)
    def detail_next(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self._is_settlement_detail(screen):
            return self.round_wait('等对局详情页渲染', wait=2)
        if self._click_area('货币战争-结算-对局详情', '按钮-下一页'):
            return self.round_retry('已点下一页,等战报页', wait=2)
        return self.round_fail('按钮-下一页 area 缺失')

    # ---- 节点6:战报 → 返回货币战争 ----

    @node_from('画面路由', status=ST_REPORT)
    @node_from('对局详情下一页')
    @operation_node(name='战报返回大厅', node_max_retry_times=10,
                    timeout_seconds=120)
    def report_back(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self._is_settlement_report(screen):
            return self.round_wait('等战报页渲染', wait=2)
        if self._click_area('货币战争-结算-战报', '按钮-返回货币战争'):
            return self.round_retry('已点返回货币战争,等大厅', wait=2.5)
        return self.round_fail('按钮-返回货币战争 area 缺失')

    # ---- 节点7:大厅确认(终点) ----

    @node_from('画面路由', status=ST_LOBBY)
    @node_from('战报返回大厅')
    @operation_node(name='大厅确认', node_max_retry_times=12,
                    timeout_seconds=120)
    def lobby_check(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self._is_lobby(screen):
            return self.round_wait('等大厅渲染', wait=2)
        return self.round_success(CwEntryExit.STATUS_AT_LOBBY)

    # ---- 节点B1:战斗中 → 右上 X ----
    # 战斗画面无稳定 id 锚(自动战斗 UI 多变),由路由节点排除法进入
    # (连续未识别);X 坐标实证 2026-08-23,建档挂「货币战争-战斗」档。

    @node_from('画面路由', status=ST_BATTLE)
    @operation_node(name='战斗中点右上X', node_max_retry_times=15,
                    timeout_seconds=180)
    def battle_x(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if self._is_battle_pause(screen):
            return self.round_success('已弹出战斗暂停')
        if self._is_dialog(screen):
            return self.round_success('点X直接弹中断挑战弹窗,接放弃链')
        if self._click_area('货币战争-战斗', '按钮-右上X'):
            return self.round_retry('已点右上X,等战斗暂停', wait=2)
        return self.round_fail('按钮-右上X area 缺失')

    # ---- 节点B2:战斗暂停 → 撤退 ----

    @node_from('战斗中点右上X', status='已弹出战斗暂停')
    @node_from('画面路由', status=ST_PAUSE)
    @operation_node(name='战斗暂停撤退', node_max_retry_times=10,
                    timeout_seconds=120)
    def battle_pause(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self._is_battle_pause(screen):
            # 撤退生效 = 暂停面板消失(中断挑战弹窗接管);交回弹窗节点
            # (兜底边),由其入口锚校验兜异常。
            return self.round_success('暂停面板不在,交放弃链')
        if self._click_area('货币战争-战斗暂停', '按钮-撤退'):
            return self.round_retry('已点撤退,等中断挑战弹窗', wait=2)
        return self.round_fail('按钮-撤退 area 缺失')
