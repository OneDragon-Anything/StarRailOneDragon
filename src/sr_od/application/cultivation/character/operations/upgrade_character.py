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
- 右下「快速刷取」:缺料时消耗开拓力 30/次 + 快速刷取券 3/次补材料
  (券不可自然恢复)。

补料路线(auto_farm=True 时优先级):快速刷取(常规资源)→ 通用材料补全
(fill_generic 后备);都未授权 = 判停。fill_generic 默认 True(灵之珠泪
不稀缺,是官方设计的默认补全路径),**调用方发起前仍须向用户提示会消耗
通用材料**;auto_farm 属真实资源消耗,**调用方发起前必须向用户说明消耗
(预计刷取次数 × 30 开拓力 + × 3 券)并获用户明确同意**,不得静默启用。

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

# 升级/晋阶执行的横幅+动画稳定等待(实测约 2s,点空白后再收尾)
_ASCEND_SETTLE_SEC: float = 2.5
# 通用材料补全确认后的等待:确认即执行升级/晋阶并弹横幅,横幅弹出动画
# 约 1-2s,太短会截到动画中帧(横幅文字未到位 → 横幅锚不命中 → 过渡态误判)
_FILL_SETTLE_SEC: float = 3.0
# 每次快速刷取的固定消耗(难度 IV 实测;两项都扣)
_FARM_TRAILBLAZE_PER: int = 30
_FARM_TICKET_PER: int = 3
# 快速刷取连刷的单轮等待(每次连刷含多次战斗,自动停止;重入轮慢询状态)
_FARM_POLL_SEC: float = 20.0
# auto_farm 单次晋阶段内最多刷取次数(防券/开拓力无限烧:缺料大时刷满预算
# 判停报告,调用方可续跑)
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
    用户提示。⚠️ auto_farm=True 属真实资源消耗(开拓力 30/次 + 快速刷取券
    3/次,券不可自然恢复):**调用方发起前必须向用户说明预计消耗并获明确
    同意**,本 op 不代替调用方做这个确认。"""

    def __init__(self, ctx: SrContext, fill_generic: bool = True, auto_farm: bool = False):
        """
        :param ctx: 上下文
        :param fill_generic: 缺料时是否用「使用通用材料补全」路线(消耗通用
            材料灵之珠泪合成补齐)。True(默认) = 自动确认材料补全弹窗——
            灵之珠泪量大不稀缺,是官方默认补全路径;调用方发起前向用户提示
            即可。False = 不消耗通用材料,缺料走 auto_farm 或判停。
        :param auto_farm: 材料不足时是否自动「快速刷取」补材料后继续升级。
            False(默认) = 不刷,缺料走 fill_generic 或判停(安全,零额外
            消耗);True = 自动连刷补材料继续升(消耗开拓力 30/次 + 快速刷取
            券 3/次)。**启用前调用方必须向用户说明消耗并获同意**。
            auto_farm=True 时优先走刷取路线(常规资源),fill_generic 退为
            刷取预算耗尽后的后备路线。
        """
        self.fill_generic: bool = fill_generic
        self.auto_farm: bool = auto_farm
        SrOperation.__init__(self, ctx, op_name=gt('角色晋阶升级')
                             + ('(自动刷取)' if auto_farm else '')
                             + ('' if fill_generic else '(不用通用材料)'),
                             node_max_retry_times=40)  # 升级↔晋阶交替多轮(≤6 阶晋阶+分段升级+横幅关闭),默认必中途夭折
        self._entry_btn_area: str = _ENTRY_BTN_ASCEND  #: 入口命中的按钮 area(打开界面用)
        self._capped: bool = False         #: 材料不足已判停(回详情页收尾途中标志)
        self._capped_level: int | None = None  #: 判停时的当前等级(报告用)
        self._farm_rounds: int = 0         #: 本次运行已执行的快速刷取次数(消耗统计)
        self._ascend_count: int = 0        #: 本次运行已执行的升级次数(日志统计)
        self._promotion_count: int = 0     #: 本次运行已执行的晋阶次数(日志统计)
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

        # ⑤ 右下按钮分流(先 auto_farm 刷取子流程,再三个白底按钮,全不中判停)
        if self.auto_farm:
            farm_result = self._try_farm_route(screen)
            if farm_result is not None:
                return farm_result

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

        # 全部不命中 = 灰底「材料不足」全缺态 → 判停
        self._capped = True
        self._capped_level = self._read_ascend_level()
        log.info('晋阶: 材料全缺(按钮灰底),判停于等级 %s', self._capped_level)
        return self.round_retry('材料不足,返回详情收尾', wait=1)

    #------------------- 快速刷取子流程(auto_farm) -------------------#

    def _try_farm_route(self, screen) -> OperationRoundResult | None:
        """auto_farm 快速刷取子流程四态推进;不走刷取路线时返回 None 交回
        按钮分流(「快速升级」白底态 / fill_generic 路线 / 判停)。

        「使用通用材料补全」白底在 = 缺料态:预算内开刷取确认弹窗推进;
        「快速升级」白底在 = 材料足,不属于刷取路线(返回 None 交回分流)。"""
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
        if self._farm_rounds >= _FARM_ROUNDS_MAX:
            if self.fill_generic:
                # 预算耗尽转通用材料补全后备路线(与类 docstring 的路线优先级一致)
                log.info('晋阶: 快速刷取预算(%d 次)耗尽,转通用材料补全路线', _FARM_ROUNDS_MAX)
                return None
            self._capped = True
            self._capped_level = self._read_ascend_level()
            log.info('晋阶: 快速刷取预算(%d 次)耗尽,判停于等级 %s',
                     _FARM_ROUNDS_MAX, self._capped_level)
            return self.round_retry('刷取预算耗尽,返回详情收尾', wait=1)
        if self.round_by_find_area(screen, _ASCEND_SCREEN, '按钮-快速刷取').is_success:
            # 弹窗未开(晋阶界面裸露且快速刷取按钮可见 = 缺料态) → 打开确认弹窗
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_ASCEND_SCREEN, '按钮-快速刷取').rect.center)
            return self.round_retry('打开快速刷取确认', wait=2)
        return None
