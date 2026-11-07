"""行迹 TAB → 角色技能(行迹)升级 operation(把目标主技能升到当前上限)。

角色养成系列装备/技能线 op:角色技能升级。交互与光锥晋阶
(upgrade_light_cone)结构同构,差异(行迹树实机摸底):
- 入口 = 行迹 TAB 行迹树上的主技能节点(点击坐标按面板关闭态校准——
  面板开关间树位移约 25px,点击热区紧,非节点区域点击=关闭面板);
- 节点 → 技能名映射(藿藿样本实测):普攻(1002,583)/战技(1288,578)/
  终结技(1147,600)/天赋(1140,458)/秘技(1147,758)。**逐角色一致性未验**,
  不同角色布局若不同,实测修正映射表;
- 节点详情为**同屏面板态**(非独立 screen):选中态锚 = 「简略描述」开关
  (常显;「下一级」按钮在满级面板消失,不可作锚);
- 按钮态:材料足 = 白底「快速升级」;缺专属材料 = 「使用通用材料补全」
  (fill_generic 授权后自动确认);全缺 = 灰字(未实测,推理);满级 = 按钮
  消失显示蓝字「已达最大等级」。
- 行迹等级上限随角色晋阶解锁(藿藿 80 级:普攻上限 6、其余 8~10、秘技 1)。

材料说明:行迹与光锥晋阶**共用属性材料池**(样本:永恒之花/永寿幼芽
同批不足)——常规刷取一次可补多线缺口。官方 wiki trace_graph 无材料字段,
材料数量表未固化(全角色统一固定表,待外部源可达后补)——缺口判定以
游戏内面板按钮态实读为准。快速升级开关默认开(开=自动填材料;关态行为
未实测);信用点不足形态未实测(预期判停兜底,报告理由可能误标为材料不足)。

auto_farm/fill_generic 参数语义与消耗声明同 upgrade_character /
upgrade_light_cone:auto_farm 的单次消耗按行迹材料档位=拟造花萼(赤)
(开拓力 10/次,券数以实刷为准);**启用即真实资源消耗,调用方发起前必须
向用户说明消耗并获明确同意**。

前置:角色行迹 TAB(由 GotoCharacterDetail + SelectCharacterOp +
SwitchCharacterTabOp('行迹') 保证);列表遮挡态显式失败。
"""

import re
import time

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_TRACE_SCREEN: str = '角色-行迹'

# 主技能名清单(节点点击坐标的 screen_info 单一真相源 =
# 「角色-行迹」screen 的 点击区-节点-<技能名> area,藿藿样本实测;
# 逐角色一致性待验,布局不同的角色实测修正 area)
_SKILL_NAMES: list[str] = ['普攻', '战技', '终结技', '天赋', '秘技']

# 升级执行后的稳定等待(反馈形态未实测,首跑按 2.5s 起步)
_TRACE_SETTLE_SEC: float = 2.5
# 快速刷取消耗:行迹材料出自拟造花萼(赤),单次开拓力=10(指南档位数据);
# 券数为先例同款未实测,首刷后回填修正
_FARM_TRAILBLAZE_PER: int = 10
_FARM_TICKET_PER: int = 3
_FARM_POLL_SEC: float = 20.0
_FARM_ROUNDS_MAX: int = 10


class UpgradeTraceOp(SrOperation):
    """把目标主技能升到当前上限,终点 = 行迹 TAB 树态。

    结果状态:MAX_LEVEL(已满,含起点即满)/ 升满当前上限 / MATERIAL_CAPPED
    (材料不足停在当前等级,日志带等级)。

    ⚠️ fill_generic / auto_farm 为真实资源消耗路线(通用材料合成替代/
    每次刷取开拓力 30+快速刷取券 3):**调用方发起前必须向用户说明消耗
    并获明确同意**,本 op 不代替调用方做这个确认。"""

    def __init__(self, ctx: SrContext, target: str,
                 fill_generic: bool = False, auto_farm: bool = False):
        """
        :param ctx: 上下文
        :param target: 目标技能名(普攻/战技/终结技/天赋/秘技)
        :param fill_generic: 缺专属材料时是否自动确认「通用材料补全」
        :param auto_farm: 缺材料时是否自动「快速刷取」补材料后继续升级
        """
        self.target: str = target.strip()
        if self.target not in _SKILL_NAMES:
            raise ValueError(f'未知技能名: {target}(可选: {"/".join(_SKILL_NAMES)})')
        self.fill_generic: bool = fill_generic
        self.auto_farm: bool = auto_farm
        SrOperation.__init__(self, ctx, op_name=gt('行迹升级') + '-' + self.target,
                             node_max_retry_times=24)
        self._capped: bool = False
        self._capped_level: int | None = None
        self._farm_rounds: int = 0
        if auto_farm:
            log.info('行迹升级: auto_farm 已启用(每次消耗开拓力 %d + 券 %d)',
                     _FARM_TRAILBLAZE_PER, _FARM_TICKET_PER)

    #------------------- 识别辅助 -------------------#

    def _read_panel_level(self) -> int | None:
        """面板技能等级(读区-面板等级 OCR「等级N」取当前值)。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_TRACE_SCREEN, '读区-面板等级')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            m = re.search(r'等级\s*(\d+)', str(r.data or ''))
            if m:
                return int(m.group(1))
        return None

    def _read_panel_category(self) -> str | None:
        """面板技能分类标签(读区-技能分类:终结技/战技/普攻/天赋/秘技)。

        用于校验「面板当前显示的是目标技能」——面板关闭后节点保持选中态,
        再点同一节点是无操作,面板可能停留在别的技能上。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_TRACE_SCREEN, '读区-技能分类')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            text = str(r.data or '').strip()
            if text in _SKILL_NAMES:
                return text
        return None

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:须在行迹 TAB 且无列表遮挡。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, '角色-列表', '标题-角色列表').is_success:
            return self.round_fail('列表浮层开着(遮挡态):先由调用方收列表')
        if not self.round_by_find_area(screen, _TRACE_SCREEN, '标题-行迹').is_success:
            return self.round_fail('不在行迹 TAB(前置:前三步 op + 切「行迹」页签)')
        return self.round_success(status='AT_TREE')

    @node_from(from_name='入口核对', status='AT_TREE')
    @operation_node(name='打开节点面板', node_max_retry_times=6)
    def open_panel(self) -> OperationRoundResult:
        """点目标技能节点 → 面板态(until=简略描述开关)。

        实测坑:面板关闭后节点保持选中态——再点该节点是「无操作」,面板
        不重弹。所以**不先关面板**:面板开着点目标节点 = 切换选中(自然
        生效),面板关着点 = 打开。目标是否真选中由升级循环的分类标签
        校验兜底(本节点的 until 只保证面板态存在)。"""
        screen = self.last_screenshot
        # 开场先无条件点一次面板外空白:锁定属性节点的面板(「需要解锁前置
        # 行迹节点」)是模态的,不先关掉会吃掉后续所有节点点击(实测)
        self.ctx.controller.click(
            self.ctx.screen_loader.get_area(_TRACE_SCREEN, '点击区-面板外空白').rect.center)
        time.sleep(2.0)
        screen = self.last_screenshot
        result = self.round_by_find_and_click_area(
            screen, _TRACE_SCREEN, f'点击区-节点-{self.target}',
            until_find_all=[(_TRACE_SCREEN, '开关-简略描述')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(status='PANEL_OPEN')
        return self.round_retry('点击未进面板态,重试', wait=2)

    @node_from(from_name='打开节点面板', status='PANEL_OPEN')
    @operation_node(name='升级循环', node_max_retry_times=30)
    def upgrade_loop(self) -> OperationRoundResult:
        """flat loop:材料补全弹窗 → 满级判定 → 判停收尾 → 升级执行。

        每轮分类(优先级):
        ① 已判停(_capped) → 点空白关面板 → 到树态就 MATERIAL_CAPPED 成功;
        ② 满级锚(「已达最大等级」)在 → MAX_LEVEL 成功;
        ③ 不在面板态(简略描述不在) → 重新点节点打开;
        ④ 面板态 → 按钮三态:快速升级命中 = 材料足,点击执行;
           使用通用材料补全命中 = 缺料,fill_generic 授权才点(弹窗下一轮
           确认),否则判停;
        ⑤ 两按钮都不命中 = 灰字全缺态 → 判停。
        升级执行的反馈形态未实测(横幅 or 等级直跳):执行后统一等
        _TRACE_SETTLE_SEC 重入,由满级锚/等级读数自然收敛;异常形态由
        节点重试预算兜底耗尽显式失败。"""
        screen = self.last_screenshot

        # ⓪ 材料补全确认弹窗(授权流④点出后弹,模态盖住面板)——优先处理
        if self.round_by_find_area(screen, _TRACE_SCREEN, '标题-材料补全弹窗').is_success:
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-确认材料补全').rect.center)
                log.info('行迹升级: 确认通用材料补全(消耗通用材料合成替代缺口)')
                return self.round_retry('通用材料补全已确认,等界面刷新', wait=2.5)
            # fill_generic=False 不应到达(④ 已拦);防御处理 = 取消+判停
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-取消材料补全').rect.center)
            self._capped = True
            self._capped_level = self._read_panel_level()
            return self.round_retry('取消材料补全,关闭面板收尾', wait=1.5)

        # ① 已判停 → 关面板回树态,到了就成功结束
        if self._capped:
            if not self.round_by_find_area(screen, _TRACE_SCREEN, '开关-简略描述').is_success:
                log.info('行迹升级: 收尾,当前等级 %s,快速刷取 %d 次'
                         '(消耗开拓力 %d + 券 %d)',
                         self._capped_level, self._farm_rounds,
                         self._farm_rounds * _FARM_TRAILBLAZE_PER,
                         self._farm_rounds * _FARM_TICKET_PER)
                return self.round_success(status='MATERIAL_CAPPED', wait=1.5)
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '点击区-面板外空白').rect.center)
            return self.round_retry('关闭面板,返回树态收尾', wait=1.5)

        # ② 满级锚
        if self.round_by_find_area(screen, _TRACE_SCREEN, '文本-已达最大等级').is_success:
            log.info('行迹升级: %s 已达最大等级', self.target)
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '点击区-面板外空白').rect.center)
            return self.round_success(status='MAX_LEVEL', wait=1.5)

        # ③ 面板态判定 + 目标校验
        if not self.round_by_find_area(screen, _TRACE_SCREEN, '开关-简略描述').is_success:
            result = self.round_by_find_and_click_area(
                screen, _TRACE_SCREEN, f'点击区-节点-{self.target}',
                until_find_all=[(_TRACE_SCREEN, '开关-简略描述')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_retry('节点面板已打开,重入分类', wait=1)
            return result
        # 面板在但显示的不是目标技能(选中态残留/切换未生效) → 再点目标节点
        category = self._read_panel_category()
        if category != self.target:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, f'点击区-节点-{self.target}').rect.center)
            return self.round_retry(f'面板当前为 [{category}],再点目标节点切换', wait=1.5)

        # ④ 升级执行(两按钮同位不同文,find 按 text 区分)
        if self.round_by_find_area(screen, _TRACE_SCREEN, '按钮-快速升级').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-快速升级').rect.center)
            return self.round_retry('快速升级已执行', wait=_TRACE_SETTLE_SEC)
        if self.round_by_find_area(screen, _TRACE_SCREEN, '按钮-通用材料补全').is_success:
            if not self.fill_generic:
                self._capped = True
                self._capped_level = self._read_panel_level()
                log.info('行迹升级: 缺专属材料(通用材料补全未授权),判停于等级 %s',
                         self._capped_level)
                return self.round_retry('材料不足,关闭面板收尾', wait=1)
            # fill_generic 已授权但快速刷取预算尚有 → 刷取路线优先(常规资源)
            if self.auto_farm and self._farm_rounds < _FARM_ROUNDS_MAX:
                return self._farm_substep(screen)
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-通用材料补全').rect.center)
            return self.round_retry('已点通用材料补全,等确认弹窗', wait=1.5)

        # ④b auto_farm 独立刷取路径:缺料但按钮为「使用通用材料补全」之外的
        # 形态(如快速刷取可直接用的形态)——刷取按钮/弹窗四态推进(照光锥 op)
        if self.auto_farm:
            result = self._farm_substep(screen)
            if result is not None:
                return result

        # ⑤ 灰字全缺态(推理形态,未实测) → 判停
        self._capped = True
        self._capped_level = self._read_panel_level()
        log.info('行迹升级: 按钮为禁用态(全缺),判停于等级 %s', self._capped_level)
        return self.round_retry('材料不足,关闭面板收尾', wait=1)

    def _farm_substep(self, screen) -> OperationRoundResult | None:
        """auto_farm 快速刷取子流程一步(照光锥 op 四态推进)。

        返回 None = 预算耗尽(调用方继续走通用材料补全/判停)。"""
        if self.round_by_find_area(screen, _TRACE_SCREEN, '按钮-开始刷取').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-开始刷取').rect.center)
            self._farm_rounds += 1
            log.info('行迹升级: 第 %d 次快速刷取开始(消耗开拓力 %d + 券 %d)',
                     self._farm_rounds, _FARM_TRAILBLAZE_PER, _FARM_TICKET_PER)
            return self.round_retry('连刷进行中', wait=_FARM_POLL_SEC)
        if self.round_by_find_area(screen, _TRACE_SCREEN, '按钮-关闭刷取结果').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-关闭刷取结果').rect.center)
            return self.round_retry('刷取完成,关闭回面板', wait=2)
        if self._farm_rounds >= _FARM_ROUNDS_MAX:
            log.info('行迹升级: 快速刷取预算(%d 次)耗尽', _FARM_ROUNDS_MAX)
            return None
        if self.round_by_find_area(screen, _TRACE_SCREEN, '标题-等级提升').is_success or \
                self.round_by_find_area(screen, _TRACE_SCREEN, '开关-简略描述').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-快速刷取').rect.center)
            return self.round_retry('打开快速刷取确认', wait=2)
        # 确认弹窗与结果框都不在、面板锚也不在 = 连刷进行中,慢询等完成
        return self.round_retry('连刷中,慢询等待', wait=_FARM_POLL_SEC)

        # ⑤ 两按钮都不命中分两态(Y4 对抗修):「可提升至」锚可见 = 真灰字
        # 全缺判停;锚不可见 = 执行后的动画/过渡期按钮暂时不可见(反馈形态
        # 未实测) → 点面板外空白重试,不判停——误报判停比多等一轮危害大
        if self.round_by_find_area(screen, _TRACE_SCREEN, '文本-可提升至').is_success:
            self._capped = True
            self._capped_level = self._read_panel_level()
            log.info('行迹升级: 按钮为禁用态(全缺),判停于等级 %s', self._capped_level)
            return self.round_retry('材料不足,关闭面板收尾', wait=1)
        self.ctx.controller.click(
            self.ctx.screen_loader.get_area(_TRACE_SCREEN, '点击区-面板外空白').rect.center)
        return self.round_retry('疑似动画/过渡态,点空白重试', wait=2)
