"""角色详情页晋阶升级 operation(把角色升到当前晋阶上限/材料耗尽)。

角色养成系列 op 第四步(与负责人对齐的四步分工):前三步进详情/选角色/切
「详情」TAB 后,本步执行等级提升。

交互模型(角色晋阶全流程实机摸底,含快速刷取闭环):
- 详情 TAB·未满级 → 右下「晋阶」大按钮(满级角色无此按钮 = 已满判据);
- 点晋阶 → 「角色-等级提升」界面:「快速升级」开关开 = 自动填材料到可达
  等级(默认开),点「快速升级」**无确认弹窗直接执行**;
- **能不能升 = 按钮文本直接区分**(负责人定案):材料充足 = 白底「快速升级」,
  不足 = 灰底「材料不足」——find_area 按文本判定天然两态互斥,不命中即
  判停,不会误点禁用按钮;
- 执行后弹「角色晋阶」结果横幅(点空白关闭),关后回到提升界面;
- 右上返回箭头回详情页。

缺材料处理(auto_farm=True 时):晋阶界面左下「快速刷取」→ 确认弹窗
「开始刷取」→ 自动连刷到材料够(游戏内置自动停止)→ 结果框「关闭」→
按钮变回「快速升级」→ 继续升级循环。
**每次刷取消耗开拓力 30 + 快速刷取券 3(两项硬消耗,券不可自然恢复)**;
auto_farm 属真实资源消耗,**调用方(agent/app)发起前必须向用户说明
消耗(预计刷取次数 × 30 开拓力 + × 3 券)并获用户明确同意**,不得静默启用。

前置:角色详情画面·详情 TAB·列表已收起(前三步保证);本 op 不选角色、
不切页签——起点不符显式失败,组合编排归调用方。
"""

import re

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_DETAIL_SCREEN: str = '角色-详情'
_ASCEND_SCREEN: str = '角色-等级提升'

# 升级执行后横幅+动画的稳定等待(实测横幅弹出约 2s,点空白后再 1.5s 收尾)
_ASCEND_SETTLE_SEC: float = 2.5
# 每次快速刷取的固定消耗(难度 IV 实测;两项都扣)
_FARM_TRAILBLAZE_PER: int = 30
_FARM_TICKET_PER: int = 3
# 快速刷取连刷的单轮等待(每次连刷含多次战斗,自动停止;重入轮慢询状态)
_FARM_POLL_SEC: float = 20.0
# auto_farm 单次晋阶段内最多刷取次数(防券/开拓力无限烧:缺料大时刷满预算
# 判停报告,调用方可续跑)
_FARM_ROUNDS_MAX: int = 10


class UpgradeCharacterOp(SrOperation):
    """把当前角色升到晋阶上限(或材料耗尽),终点 = 详情 TAB 页面。

    结果状态:MAX_LEVEL(已到晋阶上限)/ MATERIAL_CAPPED(材料耗尽停在
    当前等级,结果文本带等级与消耗)。已满级起点直接成功(MAX_LEVEL)。

    ⚠️ auto_farm=True 属真实资源消耗(开拓力 30/次 + 快速刷取券 3/次,
    券不可自然恢复):**调用方发起前必须向用户说明预计消耗并获明确同意**,
    本 op 不代替调用方做这个确认。"""

    def __init__(self, ctx: SrContext, auto_farm: bool = False):
        """
        :param ctx: 上下文
        :param auto_farm: 材料不足时是否自动「快速刷取」补材料后继续升级。
            False(默认) = 判停返回详情页报告等级(安全,零额外消耗);
            True = 自动连刷补材料继续升(消耗开拓力 30/次 + 快速刷取券 3/次)。
            **启用前调用方必须向用户说明消耗并获同意**。
        """
        self.auto_farm: bool = auto_farm
        SrOperation.__init__(self, ctx, op_name=gt('角色晋阶升级') + ('(自动刷取)' if auto_farm else ''),
                             node_max_retry_times=24)  # flat loop 推进轮次多,默认 1 次必中途夭折
        self._capped: bool = False         #: 材料不足已判停(回详情页收尾途中标志)
        self._capped_level: int | None = None  #: 判停时的当前等级(报告用)
        self._farm_rounds: int = 0         #: 本次运行已执行的快速刷取次数(消耗统计)
        if auto_farm:
            log.info('晋阶: auto_farm 已启用——材料不足将自动快速刷取'
                     '(每次消耗开拓力 %d + 快速刷取券 %d)', _FARM_TRAILBLAZE_PER, _FARM_TICKET_PER)

    #------------------- 识别辅助 -------------------#

    def _read_ascend_level(self) -> int | None:
        """晋阶界面左侧当前等级(读区-当前等级 OCR「等级NN/MM」取当前值)。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '读区-当前等级')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            m = re.search(r'(\d+)\s*/\s*\d+', str(r.data or ''))
            if m:
                return int(m.group(1))
        return None

    def _close_result_banner(self) -> OperationRoundResult:
        """关闭晋阶结果横幅(点画面下方空白;横幅锚「角色晋阶」消失 = 关闭)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _ASCEND_SCREEN, '标题-晋阶结果',
            until_not_find_all=[(_ASCEND_SCREEN, '标题-晋阶结果')],
            pre_delay=0.5, success_wait=1, retry_wait=1.5,
        )

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:须在详情 TAB(属性详情锚);按晋阶按钮有无分流。

        列表开着等遮挡态不在本 op 范围(晋阶按钮被遮挡时不命中 = 走
        「已满级」误判——先显式判列表遮挡)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, '角色-列表', '标题-角色列表').is_success:
            return self.round_fail('列表浮层开着(遮挡态):先由调用方收列表')

        if not self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success:
            return self.round_fail('不在角色详情·详情 TAB(前置:前三步 op 保证)')

        if self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-晋阶').is_success:
            return self.round_success(status='CAN_ASCEND')
        return self.round_success(status='ALREADY_MAX')

    @node_from(from_name='入口核对', status='ALREADY_MAX')
    @operation_node(name='已满级收尾')
    def already_max(self) -> OperationRoundResult:
        """已满级:直接成功(无升级空间)。"""
        return self.round_success(status='MAX_LEVEL')

    @node_from(from_name='入口核对', status='CAN_ASCEND')
    @operation_node(name='打开晋阶', node_max_retry_times=6)
    def open_ascend(self) -> OperationRoundResult:
        """详情页点右下「晋阶」→ 等级提升界面(until=标题锚)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _DETAIL_SCREEN, '按钮-晋阶',
            until_find_all=[(_ASCEND_SCREEN, '标题-等级提升')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='打开晋阶')
    @operation_node(name='升级循环', node_max_retry_times=40)
    def upgrade_loop(self) -> OperationRoundResult:
        """flat loop:横幅处理 → 材料耗尽收尾 → 详情判满 → 升级执行/刷取。

        round_retry 内建重入本节点,不设自环出边——本节点发出的
        round_success(MATERIAL_CAPPED/MAX_LEVEL) 无出边匹配 = op 成功结束。

        每轮分类(优先级):
        ① 晋阶结果横幅在 → 点空白关掉(上轮升级的收尾);
        ② 已判材料耗尽(_capped) → 回详情页途中/已到 → MATERIAL_CAPPED 成功;
        ③ 不在等级提升界面 → 详情页判:晋阶按钮在 = 开界面,不在 = 满级;
        ④ 界面正常 → find「快速升级」按钮文本:命中 = 材料足,点击执行;
        ⑤ 按钮「材料不足」且 auto_farm → 快速刷取子流程四态推进(确认弹窗/
           连刷中/结果框/打开弹窗);
        ⑥ 按钮「材料不足」且非 auto_farm → 判停回详情收尾。
        异常形态(材料足但点击没生效)由节点重试预算兜底耗尽显式失败。"""
        screen = self.last_screenshot

        # ① 结果横幅(上轮升级的收尾)
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-晋阶结果').is_success:
            result = self._close_result_banner()
            if result.is_success:
                return self.round_retry('横幅已关,重入分类', wait=1.5)
            return result

        # ② 材料耗尽已判 → 回详情页,到了就成功结束(报告消耗)
        if self._capped:
            if self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success:
                log.info('晋阶: 收尾,当前等级 %s,快速刷取 %d 次(消耗开拓力 %d + 券 %d)',
                         self._capped_level, self._farm_rounds,
                         self._farm_rounds * _FARM_TRAILBLAZE_PER,
                         self._farm_rounds * _FARM_TICKET_PER)
                return self.round_success(status='MATERIAL_CAPPED', wait=1.5)
            result = self.round_by_find_and_click_area(
                screen, _ASCEND_SCREEN, '按钮-返回箭头',
                until_find_all=[(_DETAIL_SCREEN, '按钮-属性详情')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_retry('返回详情页,重入收尾', wait=1.5)
            return result

        # ③ 详情页判定(打开前)
        if not self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-等级提升').is_success:
            if self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-晋阶').is_success:
                result = self.round_by_find_and_click_area(
                    screen, _DETAIL_SCREEN, '按钮-晋阶',
                    until_find_all=[(_ASCEND_SCREEN, '标题-等级提升')],
                    pre_delay=0.5, success_wait=1.5, retry_wait=2,
                )
                if result.is_success:
                    return self.round_retry('晋阶界面已开,重入分类', wait=1.5)
                return result
            return self.round_success(status='MAX_LEVEL')

        # ④ 升级执行:按钮文本「快速升级」= 材料足(白底可点);否则为
        # 「材料不足」灰字禁用态——find 不命中即判停,不误点禁用按钮
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-快速升级').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-快速升级').rect.center)
            return self.round_retry('快速升级已执行,等横幅', wait=_ASCEND_SETTLE_SEC)

        if not self.auto_farm:
            # ⑥ 判停回详情(等级留当前值)
            self._capped = True
            self._capped_level = self._read_ascend_level()
            log.info('晋阶: 按钮为材料不足态,判停于等级 %s', self._capped_level)
            return self.round_retry('材料不足,返回详情收尾', wait=1)

        # ⑤ auto_farm 快速刷取子流程(四态推进)
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-开始刷取').is_success:
            # 确认弹窗在 → 点开始(此后游戏自动连刷到材料够并停止)
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-开始刷取').rect.center)
            self._farm_rounds += 1
            log.info('晋阶: 第 %d 次快速刷取开始(消耗开拓力 %d + 券 %d)',
                     self._farm_rounds, _FARM_TRAILBLAZE_PER, _FARM_TICKET_PER)
            return self.round_retry('连刷进行中', wait=_FARM_POLL_SEC)
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-关闭刷取结果').is_success:
            # 结果框在 = 连刷已自动停止(材料够) → 关闭回晋阶界面
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-关闭刷取结果').rect.center)
            return self.round_retry('刷取完成,关闭回晋阶', wait=2)
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-等级提升').is_success:
            # 弹窗未开(晋阶界面裸露) → 打开刷取确认弹窗;预算内才继续
            if self._farm_rounds >= _FARM_ROUNDS_MAX:
                self._capped = True
                self._capped_level = self._read_ascend_level()
                log.info('晋阶: 快速刷取预算(%d 次)耗尽,判停于等级 %s',
                         _FARM_ROUNDS_MAX, self._capped_level)
                return self.round_retry('刷取预算耗尽,返回详情收尾', wait=1)
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-快速刷取').rect.center)
            return self.round_retry('打开快速刷取确认', wait=2)
        # 确认弹窗与结果框都不在、晋阶界面锚也不在 = 连刷进行中,慢询等完成
        return self.round_retry('连刷中,慢询等待', wait=_FARM_POLL_SEC)
