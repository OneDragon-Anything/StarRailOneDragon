"""角色详情页晋阶升级 operation(把角色升到 80 级满级/材料耗尽判停)。

角色养成系列 op 第四步(与负责人对齐的四步分工):前三步进详情/选角色/切
「详情」TAB 后,本步执行等级提升与晋阶,直到 80 级满级或材料不足判停。

交互模型(2026-11-13 阿哈等级1 全形态实机摸底):
- 详情 TAB 右下按钮三态:等级未满上限 =「升级」;到上限未满 80 =「晋阶」;
  80/80 = 无按钮(已满判据)。两个按钮点开同一个「角色-等级提升」界面;
- 界面「快速升级」开关恒开(op 不动开关):材料自动预填到可达等级;
- 界面右下按钮分流(白/灰底文本直接区分,find 按 text 天然互斥):
  材料足 = 白底「快速升级」,点击直接执行;缺专属材料但通用材料(灵之珠泪,
  量大不稀缺)够 = 白底「使用通用材料补全」→「材料补全」确认框 → **确认即
  执行**(升级态补经验材料后继续升;晋阶态补晋阶材料后直接晋阶),弹对应
  结果横幅;全缺 = 灰底「材料不足」;
- 升到当前上限后界面自动切晋阶态(当前→下一阶段对比视图),晋阶材料需求
  单独列出,执行晋阶后上限提升,继续升级——升级与晋阶交替直到 80;
- 执行后横幅两种标题:升级 =「等级提升」、晋阶 =「角色晋阶」,点空白关闭;
- 右下「快速刷取」(2026-11-13 新版交互实机摸底):点开弹「培养还需获取资源」
  窗口(缺料材料清单,每行「开拓力30 + 进入」)→ 点「进入」直达对应副本挑战
  画面 → 两条刷取路线由 use_fast_ticket 分流:True = 副本画面左下「快速刷取」
  (快速刷取券)→ 确认框「消耗开拓力30+券3」→ 确认免战斗直接领奖;
  False = 正常「挑战」→ 编队「开始挑战」→ 自动战斗 → 结算「退出关卡」。
  刷完关闭副本回到等级提升界面,材料齐后继续升级——循环每轮只刷 1 次,
  材料够不够由右下按钮状态自反馈,不足再走刷取直至预算耗尽。

补料路线:通用材料补全(fill_generic 默认 True,确认即执行)优先于刷取——
右下按钮可点时不进刷取流程;右下全灰(「材料不足」)才走快速刷取。
**调用方发起前须向用户说明:刷取消耗开拓力 30/次,use_fast_ticket=True
另消耗快速刷取券 3/次(券不可自然恢复)**。

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
_CHALLENGE_SCREEN: str = '挑战副本'

# 升级/晋阶执行的横幅+动画稳定等待(实测约 2s,点空白后再收尾)
_ASCEND_SETTLE_SEC: float = 2.5
# 通用材料补全确认后的等待:确认即执行升级/晋阶并弹横幅,横幅弹出动画
# 约 1-2s,太短会截到动画中帧(横幅文字未到位 → 横幅锚不命中 → 过渡态误判)
_FILL_SETTLE_SEC: float = 3.0
# 每次刷取的固定消耗(难度 IV 实测;两项都扣)
_FARM_TRAILBLAZE_PER: int = 30
_FARM_TICKET_PER: int = 3
# 刷取次数预算(防开拓力/券无限烧:每轮循环刷 1 次,材料够不够由右下按钮
# 状态自反馈,不足再走刷取直至预算耗尽判停,调用方可续跑)
_FARM_ROUNDS_MAX: int = 10

# 详情页入口按钮两 area 同 rect 不同 text,OCR find 天然互斥
_ENTRY_BTN_RISE: str = '按钮-升级'
_ENTRY_BTN_ASCEND: str = '按钮-晋阶'


class UpgradeCharacterOp(SrOperation):
    """把当前角色升到 80 级满级(或材料耗尽判停),消耗养成材料与晋阶材料。
    起点:角色-详情画面·详情 TAB·列表已收起;终点:角色-详情画面(详情 TAB)。

    结果状态:MAX_LEVEL(已到 80 满级)/ MATERIAL_CAPPED(材料耗尽停在
    当前等级,结果文本带等级与消耗)。已满级起点直接成功(MAX_LEVEL)。

    界面右下按钮按文本分流:「快速升级」直接执行;「使用通用材料补全」按
    fill_generic 走确认框(消耗灵之珠泪合成补齐);灰底「材料不足」判停。
    升到上限后自动切晋阶态,晋阶执行后继续升级循环。

    ⚠️ fill_generic=True(默认)会消耗通用材料灵之珠泪:调用方发起前须向
    用户提示。⚠️ 刷取路线属真实资源消耗(开拓力 30/次,use_fast_ticket=True
    另耗快速刷取券 3/次,券不可自然恢复):**调用方发起前必须向用户说明
    预计消耗并获明确同意**,本 op 不代替调用方做这个确认。"""

    def __init__(self, ctx: SrContext, fill_generic: bool = True,
                 use_fast_ticket: bool = True):
        """
        :param ctx: 上下文
        :param fill_generic: 缺料时是否用「使用通用材料补全」路线(消耗通用
            材料灵之珠泪合成补齐)。True(默认) = 自动确认材料补全弹窗——
            灵之珠泪量大不稀缺,是官方默认补全路径;调用方发起前向用户提示
            即可。False = 不消耗通用材料,缺料走刷取路线或判停。
        :param use_fast_ticket: 右下全灰(材料不足)时的刷取路线。
            True(默认) = 副本内用「快速刷取」券免战斗直接领奖(**消耗开拓力
            30/次 + 快速刷取券 3/次,券不可自然恢复**)。False = 进副本正常
            挑战自动战斗(**消耗开拓力 30/次**,无券消耗)。
            **启用前调用方必须向用户说明消耗并获同意**。
        """
        self.fill_generic: bool = fill_generic
        self.use_fast_ticket: bool = use_fast_ticket
        SrOperation.__init__(self, ctx, op_name=gt('角色晋阶升级')
                             + ('(券刷取)' if use_fast_ticket else '(手动刷取)')
                             + ('' if fill_generic else '(不用通用材料)'),
                             node_max_retry_times=40)  # 升级↔晋阶交替多轮(≤6 阶晋阶+分段升级+横幅关闭),默认必中途夭折
        self._entry_btn_area: str = _ENTRY_BTN_ASCEND  #: 入口命中的按钮 area(打开界面用)
        self._capped: bool = False         #: 材料不足已判停(回详情页收尾途中标志)
        self._capped_level: int | None = None  #: 判停时的当前等级(报告用)
        self._farm_rounds: int = 0         #: 本次运行已执行的刷取次数(消耗统计)
        self._ascend_count: int = 0        #: 本次运行已执行的升级次数(日志统计)
        self._promotion_count: int = 0     #: 本次运行已执行的晋阶次数(日志统计)
        log.info('晋阶: 刷取路线=%s,通用材料补全=%s——每次刷取消耗开拓力 30'
                 + (' + 快速刷取券 3' if use_fast_ticket else ''),
                 '券' if use_fast_ticket else '手动打', fill_generic)

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
        """关闭执行结果横幅(点空白;升级横幅「等级提升」/晋阶横幅「角色晋阶」
        两种标题,任一在即关,until=两横幅都消失)。"""
        screen = self.last_screenshot
        banner_up = (self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-升级结果').is_success
                     or self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-晋阶结果').is_success)
        if not banner_up:
            return self.round_wait('横幅已不在', wait=0.5)
        return self.round_by_find_and_click_area(
            screen, _ASCEND_SCREEN, '点击区-关闭横幅',
            until_not_find_all=[
                (_ASCEND_SCREEN, '标题-升级结果'),
                (_ASCEND_SCREEN, '标题-晋阶结果'),
            ],
            pre_delay=0.5, success_wait=1, retry_wait=1.5,
        )

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:须在详情 TAB(属性详情锚);按右下按钮三态分流。

        列表开着等遮挡态不在本 op 范围(按钮被遮挡时不命中 = 走
        「已满级」误判——先显式判列表遮挡)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, '角色-列表', '标题-角色列表').is_success:
            return self.round_fail('列表浮层开着(遮挡态):先由调用方收列表')

        if not self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success:
            return self.round_fail('不在角色详情·详情 TAB(前置:前三步 op 保证)')

        if self.round_by_find_area(screen, _DETAIL_SCREEN, _ENTRY_BTN_ASCEND).is_success:
            self._entry_btn_area = _ENTRY_BTN_ASCEND
            return self.round_success(status='CAN_ASCEND')
        if self.round_by_find_area(screen, _DETAIL_SCREEN, _ENTRY_BTN_RISE).is_success:
            self._entry_btn_area = _ENTRY_BTN_RISE
            return self.round_success(status='CAN_UPGRADE')
        return self.round_success(status='ALREADY_MAX')

    @node_from(from_name='入口核对', status='ALREADY_MAX')
    @operation_node(name='已满级收尾')
    def already_max(self) -> OperationRoundResult:
        """已满级(80/80 无按钮):直接成功(无升级空间)。"""
        return self.round_success(status='MAX_LEVEL')

    @node_from(from_name='入口核对', status='CAN_ASCEND')
    @node_from(from_name='入口核对', status='CAN_UPGRADE')
    @operation_node(name='打开晋阶', node_max_retry_times=6)
    def open_ascend(self) -> OperationRoundResult:
        """详情页点入口按钮(升级/晋阶,入口核对时记录)→ 等级提升界面
        (until=标题锚)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _DETAIL_SCREEN, self._entry_btn_area,
            until_find_all=[(_ASCEND_SCREEN, '标题-等级提升')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='打开晋阶')
    @node_from(from_name='返回养成界面')  # 刷取链收口:副本刷完回养成界面重入本循环
    @operation_node(name='升级循环', node_max_retry_times=40)
    def upgrade_loop(self) -> OperationRoundResult:
        """flat loop:确认框 → 横幅 → 判停收尾 → 详情判 → 按钮分流。

        round_retry 内建重入本节点,不设自环出边——本节点发出的
        round_success(MATERIAL_CAPPED/MAX_LEVEL) 无出边匹配 = op 成功结束。

        每轮分类(优先级):
        ① 「材料补全」确认框在 → fill_generic 确认继续 / 未授权取消判停;
        ② 执行结果横幅(升级「等级提升」/晋阶「角色晋阶」)在 → 点空白关;
        ③ 已判停(_capped) → 返回箭头回详情页,到了就 MATERIAL_CAPPED 成功;
        ④ 不在等级提升界面 → 详情页判:入口按钮在 = 开界面,都不在 = 满 80;
        ⑤ 界面内右下按钮分流(白/灰底文本直接区分):
           「快速升级」= 材料足,点执行;「使用通用材料补全」= 缺料通用够,
           fill_generic 点(等确认框下一轮)/未授权判停;auto_farm 授权时缺料
           优先走快速刷取子流程(确认弹窗/连刷中/结果框/打开弹窗四态);
           「晋阶执行」= 晋阶态材料足,点执行;全部不命中 = 灰底全缺,判停。
        异常形态(材料足但点击没生效)由节点重试预算兜底耗尽显式失败。"""
        screen = self.last_screenshot

        # ① 材料补全确认框
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-材料补全弹窗').is_success:
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-确认材料补全').rect.center)
                log.info('晋阶: 确认通用材料补全(消耗灵之珠泪合成补齐)')
                return self.round_retry('通用材料补全已确认,等界面刷新', wait=_FILL_SETTLE_SEC)
            # fill_generic=False 不应到达(⑤ 已判停);防御处理 = 取消+判停
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-取消材料补全').rect.center)
            self._capped = True
            self._capped_level = self._read_ascend_level()
            return self.round_retry('取消材料补全,返回收尾', wait=1.5)

        # ② 执行结果横幅(升级/晋阶共用关闭动作)
        if (self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-升级结果').is_success
                or self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-晋阶结果').is_success):
            result = self._close_result_banner()
            if result.is_success:
                return self.round_retry('横幅已关,重入分类', wait=1.5)
            return result

        # ③ 材料耗尽已判 → 返回箭头回详情页,到了就成功结束(报告消耗)
        if self._capped:
            if self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success:
                log.info('晋阶: 收尾,当前等级 %s,升级 %d 次/晋阶 %d 次/快速刷取 %d 次'
                         '(消耗开拓力 %d + 券 %d)',
                         self._capped_level, self._ascend_count, self._promotion_count,
                         self._farm_rounds,
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

        # ④ 不在等级提升界面:先确认在详情页再判按钮——横幅弹出动画期间
        # 界面锚与详情按钮都不可见,无详情页锚防御会把过渡态误判成满级
        if not self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-等级提升').is_success:
            if not self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success:
                return self.round_retry('不在晋阶界面也不在详情页(横幅/加载过渡态),等画面稳定',
                                        wait=1.5)
            if self.round_by_find_area(screen, _DETAIL_SCREEN, _ENTRY_BTN_ASCEND).is_success:
                self._entry_btn_area = _ENTRY_BTN_ASCEND
            elif self.round_by_find_area(screen, _DETAIL_SCREEN, _ENTRY_BTN_RISE).is_success:
                self._entry_btn_area = _ENTRY_BTN_RISE
            else:
                return self.round_success(status='MAX_LEVEL')
            result = self.round_by_find_and_click_area(
                screen, _DETAIL_SCREEN, self._entry_btn_area,
                until_find_all=[(_ASCEND_SCREEN, '标题-等级提升')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_retry('晋阶界面已开,重入分类', wait=1.5)
            return result

        # ⑤ 右下按钮分流(三个白底按钮,全不命中 = 灰底缺料进刷取路线)
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-快速升级').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-快速升级').rect.center)
            self._ascend_count += 1
            return self.round_retry(f'快速升级已执行(第{self._ascend_count}次),等横幅',
                                    wait=_ASCEND_SETTLE_SEC)

        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-通用材料补全').is_success:
            if not self.fill_generic:
                self._capped = True
                self._capped_level = self._read_ascend_level()
                log.info('晋阶: 缺料且 fill_generic 未授权,判停于等级 %s', self._capped_level)
                return self.round_retry('材料不足,返回详情收尾', wait=1)
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-通用材料补全').rect.center)
            return self.round_retry('已点通用材料补全,等确认框', wait=1.5)

        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-晋阶执行').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-晋阶执行').rect.center)
            self._promotion_count += 1
            return self.round_retry(f'晋阶已执行(第{self._promotion_count}次),等横幅',
                                    wait=_ASCEND_SETTLE_SEC)

        # ⑥ 全部不命中 = 灰底「材料不足」全缺态 → 刷取路线(预算内)/判停
        if self._farm_rounds >= _FARM_ROUNDS_MAX:
            self._capped = True
            self._capped_level = self._read_ascend_level()
            log.info('晋阶: 刷取预算(%d 次)耗尽,判停于等级 %s', _FARM_ROUNDS_MAX, self._capped_level)
            return self.round_retry('刷取预算耗尽,返回详情收尾', wait=1)
        return self.round_success(status='NEED_FARM')

    @node_from(from_name='升级循环', status='NEED_FARM')
    @operation_node(name='打开资源窗口', node_max_retry_times=3)
    def open_farm_window(self) -> OperationRoundResult:
        """界面左下点「快速刷取」→「培养还需获取资源」窗口(until=窗口标题)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _ASCEND_SCREEN, '按钮-快速刷取',
            until_find_all=[(_ASCEND_SCREEN, '标题-培养资源窗口')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='打开资源窗口')
    @operation_node(name='进入副本', node_max_retry_times=3)
    def enter_dungeon(self) -> OperationRoundResult:
        """资源窗口点缺料行的「进入」→ 直达对应副本挑战画面(until=挑战锚)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _ASCEND_SCREEN, '按钮-进入副本',
            until_find_all=[(_CHALLENGE_SCREEN, '挑战按钮')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='进入副本')
    @operation_node(name='副本刷取')
    def farm_in_dungeon(self) -> OperationRoundResult:
        """副本画面按 use_fast_ticket 分流:券免战斗 / 正常挑战自动战斗。"""
        screen = self.last_screenshot
        if self.use_fast_ticket:
            result = self.round_by_find_and_click_area(
                screen, _CHALLENGE_SCREEN, '按钮-快速刷取副本',
                until_find_all=[(_CHALLENGE_SCREEN, '标题-快速刷取弹窗')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_success(status='USE_TICKET')
            return result
        result = self.round_by_find_and_click_area(
            screen, _CHALLENGE_SCREEN, '挑战按钮',
            until_find_all=[(_CHALLENGE_SCREEN, '按钮-开始编队挑战')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(status='MANUAL_FIGHT')
        return result

    @node_from(from_name='副本刷取', status='USE_TICKET')
    @operation_node(name='券确认刷取', node_max_retry_times=4)
    def confirm_ticket_farm(self) -> OperationRoundResult:
        """快速刷取确认框点确认(次数默认 1,每轮刷 1 次由循环自反馈收敛)
        → until 结果框「关闭」按钮出现(⚠️ 结果框与确认框标题同名同位
        「快速刷取」,消失判定不可用;结果框出现 = 领奖完成回副本画面)。"""
        self._farm_rounds += 1
        log.info('晋阶: 第 %d 次券刷取(消耗开拓力 %d + 快速刷取券 %d)',
                 self._farm_rounds, _FARM_TRAILBLAZE_PER, _FARM_TICKET_PER)
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _CHALLENGE_SCREEN, '按钮-确认快速刷取',
            until_find_all=[(_CHALLENGE_SCREEN, '按钮-关闭刷取结果')],
            pre_delay=0.5, success_wait=2, retry_wait=2,
        )

    @node_from(from_name='副本刷取', status='MANUAL_FIGHT')
    @operation_node(name='手动挑战战斗', node_max_retry_times=30)
    def manual_fight(self) -> OperationRoundResult:
        """编队画面开始挑战 → 自动战斗(约 1-2 分钟,until 重试覆盖)
        → 结算点「退出关卡」回副本画面。"""
        if self.round_by_find_area(self.last_screenshot,
                                   _CHALLENGE_SCREEN, '按钮-开始编队挑战').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_CHALLENGE_SCREEN, '按钮-开始编队挑战').rect.center)
            self._farm_rounds += 1
            log.info('晋阶: 第 %d 次手动刷取开始(消耗开拓力 %d)',
                     self._farm_rounds, _FARM_TRAILBLAZE_PER)
            return self.round_retry('战斗进行中', wait=15)
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, '战斗画面', '按钮-退出关卡',
            until_find_all=[(_CHALLENGE_SCREEN, '挑战按钮')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='券确认刷取')
    @node_from(from_name='手动挑战战斗')
    @operation_node(name='返回养成界面', node_max_retry_times=10)
    def back_to_ascend(self) -> OperationRoundResult:
        """逐层回退:关结果框(如有)→ 关副本 X → 关资源窗口 X → 回等级
        提升界面(until=标题锚)→ 重入升级循环。

        跳转链逆推实测(2026-11-13):副本关闭后回「培养还需获取资源」窗口,
        再关才回养成界面——节点自环覆盖逐层关闭。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-等级提升').is_success:
            log.info('晋阶: 刷取完成回到养成界面,已刷 %d 次', self._farm_rounds)
            return self.round_success(status='FARMED')
        if self.round_by_find_area(screen, _CHALLENGE_SCREEN, '按钮-关闭刷取结果').is_success:
            result = self.round_by_find_and_click_area(
                screen, _CHALLENGE_SCREEN, '按钮-关闭刷取结果',
                until_not_find_all=[(_CHALLENGE_SCREEN, '按钮-关闭刷取结果')],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
            )
            if result.is_success:
                return self.round_retry('刷取结果框已关,重入分类', wait=1)
            return result
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '标题-培养资源窗口').is_success:
            result = self.round_by_find_and_click_area(
                screen, _ASCEND_SCREEN, '按钮-关闭资源窗口',
                until_not_find_all=[(_ASCEND_SCREEN, '标题-培养资源窗口')],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
            )
            if result.is_success:
                return self.round_retry('资源窗口已关,重入分类', wait=1)
            return result
        return self.round_by_find_and_click_area(
            screen, _CHALLENGE_SCREEN, '按钮-关闭副本',
            until_find_all=[(_ASCEND_SCREEN, '标题-等级提升')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )
