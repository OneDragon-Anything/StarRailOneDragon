"""光锥 TAB → 光锥晋阶升级 operation(把当前角色的光锥升到上限)。

角色养成系列的装备线 op:角色 80 满级后的主要缺口是光锥等级(如藿藿光锥
50→80)。交互与角色晋阶(UpgradeCharacterOp)结构同款,差异(2026-11-07
藿藿光锥惊魂夜 50→80 场景实机):
- 入口 = 光锥 TAB 右下「强化」按钮(「替换」旁;满级形态未实测,按角色
  晋阶同款假设满级时消失——首次满级光锥实测时复核);
- 晋阶界面右上角是关闭 X(角色晋阶是返回箭头),关闭回光锥 TAB;
- **缺材料时按钮三态**:材料足 = 白底「快速升级」;缺专属材料但通用材料
  够 = 白底「使用通用材料补全」(点击弹「材料补全」确认框,以通用材料
  合成替代缺口——通用材料是稀缺消耗品(梦之珠泪类,锄大地/活动来源),
  **确认即真实消耗,fill_generic=True 时调用方须先向用户说明并获同意**);
  全缺 = 灰字禁用(形态未实测,按两态互斥逻辑推理)。

前置:光锥 TAB(由 GotoCharacterDetail + SelectCharacterOp +
SwitchCharacterTabOp('光锥') 保证);起点不符显式失败。

晋阶结果横幅(执行成功后的弹层)未实测——首版按「两按钮不可见且晋阶
锚不可见 = 过渡/横幅态,点空白重试」兜底,实测暴露专属文本后再补 area。
"""

import re

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_LC_TAB_SCREEN: str = '角色-光锥'
_LC_ASCEND_SCREEN: str = '光锥-等级提升'

# 升级执行后横幅+动画的稳定等待
_LC_ASCEND_SETTLE_SEC: float = 2.5


class UpgradeLightConeOp(SrOperation):
    """把当前角色的光锥升到上限,终点 = 光锥 TAB 页面。

    结果状态:MAX_LEVEL(已满)/ LIGHT_CONE_CAPPED(材料不足停在当前等级,
    结果日志带等级)。已满起点直接成功(MAX_LEVEL)。

    ⚠️ fill_generic=True 属真实资源消耗(通用材料合成替代晋阶缺口,如
    梦之珠泪 159 个换永恒之花 15 的实测量级):**调用方发起前必须向用户
    说明消耗并获明确同意**,本 op 不代替调用方做这个确认。"""

    def __init__(self, ctx: SrContext, fill_generic: bool = False):
        """
        :param ctx: 上下文
        :param fill_generic: 缺专属材料时是否用「通用材料补全」路线继续升级。
            False(默认) = 判停返回光锥 TAB 报告等级(零额外消耗);
            True = 自动确认材料补全弹窗(消耗通用材料合成替代)。
            **启用前调用方必须向用户说明消耗并获同意**。
        """
        self.fill_generic: bool = fill_generic
        SrOperation.__init__(self, ctx, op_name=gt('光锥晋阶升级') + ('(通用材料)' if fill_generic else ''),
                             node_max_retry_times=24)
        self._capped: bool = False          #: 材料不足已判停(回光锥 TAB 收尾途中标志)
        self._capped_level: int | None = None  #: 判停时的光锥等级(报告用)

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
        """入口核对:须在光锥 TAB;按强化按钮有无分流。

        列表遮挡不在本 op 范围(强化按钮被遮挡时不命中会误判满级,先显式判)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, '角色-列表', '标题-角色列表').is_success:
            return self.round_fail('列表浮层开着(遮挡态):先由调用方收列表')

        if not self.round_by_find_area(screen, _LC_TAB_SCREEN, '标题-角色光锥').is_success:
            return self.round_fail('不在光锥 TAB(前置:前三步 op + 切「光锥」页签)')

        if self.round_by_find_area(screen, _LC_TAB_SCREEN, '按钮-强化').is_success:
            return self.round_success(status='CAN_UPGRADE')
        # 强化按钮不在:满级(假设,未实测复核)或替换/强化都不在 = 不在预期画面
        if self.round_by_find_area(screen, _LC_TAB_SCREEN, '按钮-替换').is_success:
            return self.round_success(status='ALREADY_MAX')
        return self.round_fail('光锥 TAB 无强化/替换按钮(画面状态未知),请实机确认')

    @node_from(from_name='入口核对', status='ALREADY_MAX')
    @operation_node(name='已满级收尾')
    def already_max(self) -> OperationRoundResult:
        """已满级:直接成功。"""
        return self.round_success(status='MAX_LEVEL')

    @node_from(from_name='入口核对', status='CAN_UPGRADE')
    @operation_node(name='打开晋阶', node_max_retry_times=6)
    def open_ascend(self) -> OperationRoundResult:
        """光锥 TAB 点「强化」→ 晋阶界面(until=双锚:标题+可提升至标签)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _LC_TAB_SCREEN, '按钮-强化',
            until_find_all=[
                (_LC_ASCEND_SCREEN, '标题-光锥详情'),
                (_LC_ASCEND_SCREEN, '文本-可提升至'),
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
                        (_LC_ASCEND_SCREEN, '文本-可提升至'),
                    ],
                    pre_delay=0.5, success_wait=1.5, retry_wait=2,
                )
                if result.is_success:
                    return self.round_retry('晋阶界面已开,重入分类', wait=1.5)
                return result
            return self.round_success(status='MAX_LEVEL')

        # ④ 升级执行(两按钮同位不同文,find 按 text 天然区分三态)
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '按钮-快速升级').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-快速升级').rect.center)
            return self.round_retry('快速升级已执行,等横幅', wait=_LC_ASCEND_SETTLE_SEC)
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '按钮-通用材料补全').is_success:
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_LC_ASCEND_SCREEN, '按钮-通用材料补全').rect.center)
                return self.round_retry('已点通用材料补全,等确认弹窗', wait=1.5)
            self._capped = True
            self._capped_level = self._read_lc_level(_LC_ASCEND_SCREEN)
            log.info('光锥晋阶: 缺专属材料(通用材料补全未授权),判停于等级 %s',
                     self._capped_level)
            return self.round_retry('材料不足,关闭回光锥页收尾', wait=1)

        # ⑤ 两按钮都不命中时分两态:晋阶锚(可提升至)可见 = 真禁用态(全缺)判停;
        # 锚不可见 = 执行后的横幅/过渡态盖住了按钮区(横幅形态未实测) → 点空白
        # 重试,不判停——横幅是暂态,空白点击会关掉它
        if self.round_by_find_area(screen, _LC_ASCEND_SCREEN, '文本-可提升至').is_success:
            self._capped = True
            self._capped_level = self._read_lc_level(_LC_ASCEND_SCREEN)
            log.info('光锥晋阶: 按钮为禁用态(全缺),判停于等级 %s', self._capped_level)
            return self.round_retry('材料不足,关闭回光锥页收尾', wait=1)
        # 过渡态点空白(画面中部空白区,不压任何控件)
        self.ctx.controller.click(Point(900, 550))
        return self.round_retry('疑似横幅/过渡态,点空白重试', wait=2)
