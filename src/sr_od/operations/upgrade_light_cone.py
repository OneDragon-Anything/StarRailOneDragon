"""光锥 TAB → 光锥晋阶升级 operation(把当前角色的光锥升到上限)。

角色养成系列的装备线 op:光锥等级是角色 80 满级后的主要缺口项。
交互与角色晋阶(UpgradeCharacterOp)结构同款,差异(光锥晋阶全流程实机摸底):
- 入口 = 光锥 TAB 右下「强化」按钮(「替换」旁;满级形态实测:按钮不消失,
  可进晋阶界面,满级判定在晋阶界面内做);
- 晋阶界面右上角是关闭 X(角色晋阶是返回箭头),关闭回光锥 TAB;
- 晋阶界面右下按钮三态:材料足 = 白底「快速升级」;缺专属材料但通用材料
  够 = 白底「使用通用材料补全」(点击弹「材料补全」确认框,以通用材料
  合成替代缺口——通用材料是稀缺消耗品(梦之珠泪类,锄大地/活动来源),
  **确认即真实消耗,fill_generic=True 时调用方须先向用户说明并获同意**);
  全缺 = 灰字禁用;
- 满级形态:晋阶界面右下显示「已提升至最高阶」(「可提升至」标签不存在)
  → 判满关闭收尾。

前置:光锥 TAB(由 GotoCharacterDetail + SelectCharacterOp +
SwitchCharacterTabOp('光锥') 保证);列表浮层开着显式失败先收列表;
起点不符显式失败。

晋阶结果横幅(执行成功后的弹层)未实测——首版按「两按钮不可见且晋阶
锚不可见 = 过渡/横幅态,点空白重试」兜底,实测暴露专属文本后再补 area。
"""

import re

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_LC_TAB_SCREEN: str = '角色-光锥'
_LC_ASCEND_SCREEN: str = '光锥-等级提升'
_REPLACE_SCREEN: str = '光锥-替换'
_LIST_SCREEN: str = '角色-列表'

# 升级执行后横幅+动画的稳定等待
_LC_ASCEND_SETTLE_SEC: float = 2.5
# 每次快速刷取的固定消耗(难度 IV 实测;两项都扣,与角色晋阶同款)
_LC_FARM_TRAILBLAZE_PER: int = 30
_LC_FARM_TICKET_PER: int = 3
# 快速刷取连刷的单轮等待(连刷含多次战斗,游戏自动停止;重入轮慢询状态)
_LC_FARM_POLL_SEC: float = 20.0
# auto_farm 单次晋阶段内最多刷取次数(防券/开拓力无限烧)
_LC_FARM_ROUNDS_MAX: int = 10


class UpgradeLightConeOp(SrOperation):
    """把当前角色的光锥升到上限,终点 = 光锥 TAB 页面。

    结果状态:LIGHT_CONE_CAPPED(光锥已到上限 / 材料不足停在当前等级,
    结果日志带等级)。已满级起点也归此状态(晋阶界面判「已提升至最高阶」
    后关闭收尾)。

    满级形态(实机):满级光锥的 TAB 页「强化」按钮不消失(可进晋阶界面),
    晋阶界面右下显示「已提升至最高阶」——满级判定在晋阶界面内做,不在
    TAB 入口做。
    晋阶界面右下按钮三态:材料足 = 白底「快速升级」;缺专属材料但通用材料
    够 = 白底「使用通用材料补全」(点击弹「材料补全」确认框,以通用材料
    合成替代缺口——通用材料是稀缺消耗品(梦之珠泪类,锄大地/活动来源),
    **确认即真实消耗,fill_generic=True 时调用方须先向用户说明并获同意**);
    全缺 = 灰字禁用。

    ⚠️ fill_generic=True 属真实资源消耗:**调用方发起前必须向用户
    说明消耗并获明确同意**,本 op 不代替调用方做这个确认。"""

    def __init__(self, ctx: SrContext, fill_generic: bool = False, auto_farm: bool = False):
        """
        :param ctx: 上下文
        :param fill_generic: 缺专属材料时是否用「通用材料补全」路线继续升级。
            False(默认) = 不用通用材料;True = 自动确认材料补全弹窗(消耗通用
            材料合成替代,如梦之珠泪 159 个换永恒之花 15 的实测量级)。
            **启用前调用方必须向用户说明消耗并获同意**。
        :param auto_farm: 缺材料时是否自动「快速刷取」补材料后继续升级。
            False(默认) = 不刷;True = 自动连刷补材料(**每次消耗开拓力 30 +
            快速刷取券 3,券不可自然恢复**)。**启用前调用方必须向用户说明
            消耗并获同意**。auto_farm=True 时优先走刷取路线(常规资源),
            fill_generic 退为刷取预算耗尽后的后备路线。
        """
        self.fill_generic: bool = fill_generic
        self.auto_farm: bool = auto_farm
        SrOperation.__init__(self, ctx, op_name=gt('光锥晋阶升级') + ('(自动刷取)' if auto_farm else '')
                             + ('(通用材料)' if fill_generic else ''),
                             node_max_retry_times=24)
        self._capped: bool = False          #: 材料不足已判停(回光锥 TAB 收尾途中标志)
        self._capped_level: int | None = None  #: 判停时的光锥等级(报告用)
        self._farm_rounds: int = 0          #: 本次运行已执行的快速刷取次数(消耗统计)
        if auto_farm:
            log.info('光锥晋阶: auto_farm 已启用——材料不足将自动快速刷取'
                     '(每次消耗开拓力 %d + 快速刷取券 %d)', _LC_FARM_TRAILBLAZE_PER, _LC_FARM_TICKET_PER)

    #------------------- 识别辅助 -------------------#

    def _read_lc_level(self, screen_name: str = _LC_TAB_SCREEN) -> int | None:
        """等级读数(「等级NN/MM」取当前值);两界面等级显示位置不同,按所在
        界面选读区:光锥 TAB 与晋阶界面的等级区 rect 各自建档。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(screen_name, '读区-等级'
                                               if screen_name == _LC_TAB_SCREEN else '读区-当前等级')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            m = re.search(r'(\d+)\s*/\s*\d+', str(r.data or ''))
            if m:
                return int(m.group(1))
        return None

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:画面级判定在光锥 TAB 且强化按钮可点。

        列表浮层(替换列表/角色列表)开着会遮挡强化按钮,画面判定识别浮层态
        显式失败提示收列表;满级判定不在入口做(满级时强化按钮仍在,见类
        docstring)。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot,
            screen_name_list=[_LC_TAB_SCREEN, _REPLACE_SCREEN, _LIST_SCREEN])
        if current in (_REPLACE_SCREEN, _LIST_SCREEN):
            return self.round_fail(f'{current} 浮层开着(遮挡态):先收列表'
                                   f'(替换列表点右上返回箭头)')
        if current != _LC_TAB_SCREEN:
            return self.round_fail(f'不在光锥 TAB(当前画面判定: {current};'
                                   f'前置:进详情 + 选角色 + 切「光锥」页签)')
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LC_TAB_SCREEN, '按钮-强化') == FindAreaResultEnum.TRUE:
            return self.round_success(status='CAN_UPGRADE')
        return self.round_fail('光锥 TAB 无强化按钮(画面状态未知),请实机确认')

    @node_from(from_name='入口核对', status='CAN_UPGRADE')
    @operation_node(name='打开晋阶', node_max_retry_times=6)
    def open_ascend(self) -> OperationRoundResult:
        """光锥 TAB 点「强化」→ 晋阶界面(until=双锚:标题+晋阶 TAB,两种
        形态常驻;「可提升至」标签满级态不存在不能作转移锚)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _LC_TAB_SCREEN, '按钮-强化',
            until_find_all=[
                (_LC_ASCEND_SCREEN, '标题-光锥详情'),
                (_LC_ASCEND_SCREEN, 'TAB-晋阶'),
            ],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='打开晋阶')
    @operation_node(name='升级循环', node_max_retry_times=30)
    def upgrade_loop(self) -> OperationRoundResult:
        """flat loop:材料补全弹窗 → 收尾 → 判满 → 升级执行。

        每轮分类(优先级):
        ① 材料补全确认弹窗在 → fill_generic 点确认继续 / 否则点取消判停;
        ② 已判停(_capped) → 关 X 回光锥 TAB → 到了就成功结束;
        ③ 不在晋阶界面(打开前/收尾途中) → 光锥 TAB 判:强化在 = 开界面,
           不在 = 满级成功;
        ④ 晋阶界面且两按钮其一命中 → 执行(快速升级直接消耗;通用材料补全
           需 fill_generic,弹窗交由 ① 下一轮确认);
        ⑤ 晋阶界面但两按钮都不命中 = 灰字禁用态(全缺) → 判停;
        ⑥ 晋阶锚不可见但光锥详情标题在 = 执行后的横幅/过渡态(未实测形态)
           → 点空白重试。
        异常形态由节点重试预算兜底耗尽显式失败。"""
        screen = self.last_screenshot

        # ① 材料补全确认弹窗
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '标题-材料补全弹窗').is_success:
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-确认材料补全').rect.center)
                log.info('光锥晋阶: 确认通用材料补全(消耗通用材料合成替代缺口)')
                return self.round_retry('通用材料补全已确认,等界面刷新', wait=2.5)
            # fill_generic=False 不应到达(④ 已判停);防御处理 = 取消+判停
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-取消材料补全').rect.center)
            self._capped = True
            self._capped_level = self._read_lc_level()
            return self.round_retry('取消材料补全,返回收尾', wait=1.5)

        # ② 已判停 → 关 X 回光锥 TAB → 到了就结束
        if self._capped:
            if self.round_by_find_area(screen, _LC_TAB_SCREEN, '标题-角色光锥').is_success:
                log.info('光锥晋阶: 材料不足收尾,当前光锥等级 %s', self._capped_level)
                return self.round_success(status='LIGHT_CONE_CAPPED', wait=1.5)
            result = self.round_by_find_and_click_area(
                screen, _LC_ASCEND_SCREEN, '按钮-关闭X',
                until_find_all=[(_LC_TAB_SCREEN, '标题-角色光锥')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_retry('返回光锥页,重入收尾', wait=1.5)
            return result

        # ③ 详情判满(打开前/收尾途中)
        if not self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '标题-光锥详情').is_success:
            if self.round_by_find_area(screen, _LC_TAB_SCREEN, '按钮-强化').is_success:
                result = self.round_by_find_and_click_area(
                    screen, _LC_TAB_SCREEN, '按钮-强化',
                    until_find_all=[
                        (_LC_ASCEND_SCREEN, '标题-光锥详情'),
                        (_LC_ASCEND_SCREEN, 'TAB-晋阶'),
                    ],
                    pre_delay=0.5, success_wait=1.5, retry_wait=2,
                )
                if result.is_success:
                    return self.round_retry('晋阶界面已开,重入分类', wait=1.5)
                return result
            return self.round_fail('离开晋阶界面且强化按钮不在(画面状态未知),请实机确认')

        # 满级态:右下「已提升至最高阶」(可提升至标签不存在) → 判停收尾归档
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '文本-已提升至最高阶').is_success:
            self._capped = True
            self._capped_level = self._read_lc_level(_LC_ASCEND_SCREEN)
            log.info('光锥晋阶: 光锥已满级(已提升至最高阶,等级 %s)', self._capped_level)
            return self.round_retry('满级,关闭回光锥页收尾', wait=1)

        # ④ 升级执行:按钮文本「快速升级」= 材料足(白底可点),直接执行;
        # 不命中 = 缺料态,进入 ⑤ 分流(两按钮同位不同文,find 按 text 天然区分)
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '按钮-快速升级').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-快速升级').rect.center)
            return self.round_retry('快速升级已执行,等横幅', wait=_LC_ASCEND_SETTLE_SEC)

        # ⑤ 「快速升级」不命中 = 缺料态 → 三路分流:
        # auto_farm 优先走快速刷取(常规资源);刷取预算耗尽后 fill_generic
        # 可转通用材料补全(稀缺资源,单独授权);都未授权 = 判停。
        if self.auto_farm:
            if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '按钮-开始刷取').is_success:
                # 确认弹窗在 → 点开始(游戏自动连刷到材料够并停止)
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-开始刷取').rect.center)
                self._farm_rounds += 1
                log.info('光锥晋阶: 第 %d 次快速刷取开始(消耗开拓力 %d + 券 %d)',
                         self._farm_rounds, _LC_FARM_TRAILBLAZE_PER, _LC_FARM_TICKET_PER)
                return self.round_retry('连刷进行中', wait=_LC_FARM_POLL_SEC)
            if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '按钮-关闭刷取结果').is_success:
                # 结果框在 = 连刷已自动停止(材料够) → 关闭回晋阶界面
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-关闭刷取结果').rect.center)
                return self.round_retry('刷取完成,关闭回晋阶', wait=2)
            if self._farm_rounds < _LC_FARM_ROUNDS_MAX:
                if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '标题-等级提升').is_success:
                    # 弹窗未开(晋阶界面裸露) → 打开刷取确认弹窗
                    self.ctx.controller.click(
                        self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-快速刷取').rect.center)
                    return self.round_retry('打开快速刷取确认', wait=2)
                # 确认弹窗与结果框都不在、晋阶界面锚也不在 = 连刷进行中
                return self.round_retry('连刷中,慢询等待', wait=_LC_FARM_POLL_SEC)
            log.info('光锥晋阶: 快速刷取预算(%d 次)耗尽', _LC_FARM_ROUNDS_MAX)

        if self.fill_generic:
            if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '按钮-通用材料补全').is_success:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-通用材料补全').rect.center)
                return self.round_retry('已点通用材料补全,等确认弹窗', wait=1.5)
            # 通用材料也不够(按钮灰字) → 判停
            self._capped = True
            self._capped_level = self._read_lc_level(_LC_ASCEND_SCREEN)
            log.info('光锥晋阶: 材料全缺(通用材料亦不足),判停于等级 %s', self._capped_level)
            return self.round_retry('材料全缺,关闭回光锥页收尾', wait=1)

        # 判停回光锥 TAB(等级留当前值)
        self._capped = True
        self._capped_level = self._read_lc_level(_LC_ASCEND_SCREEN)
        log.info('光锥晋阶: 材料不足(fill_generic/auto_farm 均未授权),判停于等级 %s',
                 self._capped_level)
        return self.round_retry('材料不足,关闭回光锥页收尾', wait=1)
