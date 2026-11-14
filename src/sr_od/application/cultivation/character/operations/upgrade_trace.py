"""行迹面板升级 operation(起点=面板态,把面板技能升到当前上限)。

角色养成系列 op 的行迹线。负责人裁定契约:节点选择归 agent——树形随命途/
角色变,程序层不做技能树节点选择;本 op 起点 = 角色-行迹·面板态(agent 在
树态读节点三态、点开目标技能面板后调本 op),终点 = 关面板回树态。

起跑闸(零消耗):「简略描述」开关(面板态锚)在场 + 读区-技能分类现读 ==
target 等值——不符显式失败,拦住点错节点。匹配基准 = target 本身,不维护
固定枚举(新命途分类免改码)。分类不符细分两态:开关不在场(真无面板/未知
态)直落 fail 不经收尾;开关在场但分类不符(面板开着别的技能)经收尾关面板
回树态再 fail(树态是 agent 重新选点的前置)。

op 自动闭环 = 升级循环 + 通用材料补全(双形态:「使用通用材料补全」/
「材料合成」同位不同文,与光锥线同构平移)+ 花萼券刷路线(面板「快速刷取」
→ 培养资源窗口 → 花萼行券按钮 → 共用快速刷取弹窗 → 连刷次数设置 → 回
面板)。确认刷取后的返回落点未实测(探索时 E2E 授权未批停在控件前;取消
路径已实测回资源窗口),为实机券刷 E2E 的验证项。面板「快速刷取」点击在
缺口可由合成覆盖时被游戏拒绝并弹 toast(实测显示≈2s,光锥线同款)——券刷
链面板态以 toast 正判(前两轮门控探测,防慢开窗误读)命中即 MATERIAL_CAPPED
判停收口,漏检由连点封顶(4 次)兜底。

手动刷本划出 op 边界(负责人裁定):结算后回不到面板态,op 判停交还
agent——周本走 ChallengeEchoOfWarByName;花萼手动刷由调用方按行迹缺料
材料自行导航至对应副本挑战画面(FarmTraceMaterialOp 立项前过渡态;
FarmLightConeMaterialOp 只认光锥缺料格,行迹判停后不可用,勿套用)。

面板态交互(实机摸底):面板按钮三态——白底「快速升级」= 材料足;
「使用通用材料补全」/「材料合成」= 缺料两形态(fill_generic 授权自动
确认);「已达最大等级」蓝字 = 满级;「可提升至N级」文本在场且按钮带无
可用钮 = 全缺判停态。确认框滑条次数不记忆(重开恒 1)。开拓力不足时
挑战/刷取静默无反应——链路重试预算耗尽即判停,不空烧轮次。

⚠️ farm_dungeon 发起即真实消耗(每次刷取开拓力 10 + 券 1/次,实测定案),
调用方发起前必须向用户说明并获明确同意,本 op 不代替调用方做这个确认。
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
_FAST_FARM_DIALOG: str = '快速刷取弹窗'
_FAST_FARM_RESULT: str = '快速刷取结果弹窗'
_RESOURCE_WINDOW_SCREEN: str = '培养资源窗口'

# 升级执行后的稳定等待(反馈形态实测后随实机批回填)
_TRACE_SETTLE_SEC: float = 2.5
# 快速刷取消耗:行迹材料出自拟造花萼(赤)。券耗实测定案=1(弹窗消耗行实读,
# 与角色晋阶线 30+3 不同,券耗随副本类型变化勿复用)
_FARM_TRAILBLAZE_PER: int = 10
_FARM_TICKET_PER: int = 1
# 券刷确认后的连刷轮询间隔(自动连刷时长由设置次数决定)
_FARM_POLL_SEC: float = 20.0
# 收尾关面板连等封顶:纯定位区点击 + until_not 无界等待的防线(超时限 60s)
_CLOSE_PANEL_MAX_ROUNDS: int = 5
# 券刷链面板钮连点封顶:toast 正判漏检时的兜底(无可刷缺口点击恒被拒、窗
# 永不开;连点 4 次仍未开 = 漏检或界面异态,判停收口)
_PANEL_FARM_CLICK_MAX: int = 4


class UpgradeTraceOp(SrOperation):
    """把面板当前技能升到当前上限(起点=面板态,终点=关面板回树态)。

    结果状态:MAX_LEVEL(已达最大等级,含升满当前上限语义)/ MATERIAL_CAPPED
    (材料不足判停,日志带收尾等级)/ 不在目标技能面板(起跑校验或循环内
    画面异动 fail——前者零消耗直落,后者经收尾关面板回树态)。

    路线地位:fill_generic(通用材料补全,默认开——通用材料非稀缺)是默认
    补料路线;显式开启 farm_dungeon(真实消耗开拓力 10+券 1/次)= 调用方
    显式要求优先刷取——预算内缺料先券刷,预算耗尽回落通用补全/判停。
    **farm_dungeon 发起前调用方必须向用户说明消耗并获明确同意**。
    """

    def __init__(self, ctx: SrContext, target: str, fill_generic: bool = True,
                 farm_dungeon: bool = False,
                 farm_times_per_round: int = -1, farm_rounds_max: int = 1):
        """
        :param ctx: 上下文
        :param target: 面板技能分类名(普攻/战技/终结技/天赋/秘技/欢愉技…)
            ——与面板读区现读分类等值校验,不符显式失败;不设固定枚举
        :param fill_generic: 缺料时是否自动确认补全(默认 True;双形态
            「材料补全」/「材料合成」确认框一并支持)
        :param farm_dungeon: 缺料时走花萼券刷路线补料(仅券刷——手动刷本
            划出 op 边界)。**真实消耗开拓力 10 + 券 1/次**
        :param farm_times_per_round: 券刷确认框连刷次数。正数 = 设到目标;
            -1(默认)= 点「^」拉满
        :param farm_rounds_max: 券刷轮数预算(耗尽转通用材料补全/判停)。
            默认 1,与光锥/角色线同构——多轮连刷缺口由调用方显式续跑
        """
        self.target: str = target.strip()
        if not self.target:
            raise ValueError('target(面板技能分类名)不能为空')
        if farm_times_per_round == 0 or farm_times_per_round < -1:
            raise ValueError(f'farm_times_per_round 须为正数或 -1(拉满), 得到 {farm_times_per_round}')
        if farm_rounds_max < 1:
            raise ValueError(f'farm_rounds_max 必须 >= 1, 得到 {farm_rounds_max}')
        self.fill_generic: bool = fill_generic
        self.farm_dungeon: bool = farm_dungeon
        self.farm_times_per_round: int = farm_times_per_round
        self.farm_rounds_max: int = farm_rounds_max
        SrOperation.__init__(self, ctx, op_name=gt('行迹升级') + '-' + self.target,
                             node_max_retry_times=24)
        self._farm_rounds: int = 0  #: 已执行的券刷轮数(预算控制)
        self._farm_times_set: int = 0  #: 确认框实际设到的连刷次数(券耗记账)
        self._chain_farm_done: bool = False  #: 券刷链内状态机:确认已点=True(窗口分支据此关窗而非再点券钮)
        self._panel_farm_click_rounds: int = 0  #: 面板钮连续点击轮数(toast 探测门控与漏检兜底封顶用,窗口/弹窗出现即复位)
        self._final_status: str | None = None  #: 终态 status(收尾节点携带落账)
        self._close_rounds: int = 0  #: 收尾关面板连等计数(纯定位区无界等待防线)
        self._feedback_clicks: int = 0  #: 反馈遮罩期连续盲点计数(连续 6 轮无面板锚判画面异动)
        self._end_level: int | None = None  #: 收尾面板等级(日志对照)
        if farm_dungeon:
            log.info('行迹升级: farm_dungeon 已启用(每次消耗开拓力 %d + 券 %d)',
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
        """面板技能分类现读文本(读区-技能分类首个非空行,strip 后返回)。

        等值校验在调用方与 target 比较——不设白名单,新命途分类免改码。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_TRACE_SCREEN, '读区-技能分类')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            text = str(r.data or '').strip()
            if text:
                return text
        return None

    def _panel_category_ok(self) -> bool:
        """面板分类现读 == target(normalize 后等值)。"""
        category = self._read_panel_category()
        return category is not None and category == self.target

    #------------------- 节点图 -------------------#

    @operation_node(name='入口校验', is_start_node=True, node_max_retry_times=3)
    def check_entry(self) -> OperationRoundResult:
        """起跑闸(零消耗):面板态双锚校验,不符拦住点错节点。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, _TRACE_SCREEN, '开关-简略描述').is_success:
            return self.round_fail('不在面板态(简略描述开关不在场):'
                                   'agent 先在树态点开目标技能面板再调本 op')
        if not self._panel_category_ok():
            # OCR 瞬时噪声复读一次(防误拦零消耗起跑)
            time.sleep(1)
            if not self._panel_category_ok():
                # 面板开着别的技能:置 fail 终态经收尾关面板回树态
                # (树态是 agent 重新选点的前置,不留面板态破口)
                self._final_status = '不在目标技能面板'
                return self.round_success('CLOSE_PANEL')
        return self.round_success()

    @node_from(from_name='入口校验')
    @node_from(from_name='券刷链')
    @operation_node(name='升级循环', node_max_retry_times=30)
    def upgrade_loop(self) -> OperationRoundResult:
        """flat loop(面板态):补全确认弹窗(双形态确认框同款)→ 满级+分类
        校验 → 按钮三态 → 券刷路由 → 全缺判停。判停/完成置 _final_status
        后转收尾关面板;循环内画面异动(面板不在/分类不符)同走收尾 fail。

        升级执行的反馈形态(实机:全屏「行迹提升 等级X»Y」横幅,点击空白关闭)
        由 ② 面板锚 miss 分态兜住(横幅锚在场点空白关闭);执行后统一等
        _TRACE_SETTLE_SEC 重入,由满级锚/按钮态自然收敛。"""
        screen = self.last_screenshot

        # ⓪ 材料补全确认弹窗(fill_generic 路线点出后弹,模态盖住面板;
        # 「材料补全」/「材料合成」两形态确认框同款)——优先处理
        if self.round_by_find_area(screen, _TRACE_SCREEN, '标题-材料补全弹窗').is_success:
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-确认材料补全').rect.center)
                log.info('行迹升级: 确认材料补全(消耗通用材料合成替代缺口)')
                return self.round_retry('材料补全已确认,等界面刷新', wait=2.5)
            # fill_generic=False 不应到达(下方缺料分支已拦);防御 = 取消+判停
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-取消材料补全').rect.center)
            self._final_status = 'MATERIAL_CAPPED'
            self._end_level = self._read_panel_level()
            return self.round_retry('取消材料补全,转收尾关面板', wait=1.5)

        # ① 满级锚 + 分类校验(锚命中后必须确认面板就是目标技能——别的
        # 满级技能面板会误报)
        if self.round_by_find_area(screen, _TRACE_SCREEN, '文本-已达最大等级').is_success:
            if not self._panel_category_ok():
                self._final_status = '不在目标技能面板'
                return self.round_success('CLOSE_PANEL')
            log.info('行迹升级: %s 已达最大等级', self.target)
            self._final_status = 'MAX_LEVEL'
            return self.round_success('CLOSE_PANEL')

        # ② 面板态判定:开关不在 = 升级反馈横幅/特效期(全屏遮罩,OCR 除遮罩
        # 自身外全盲,遮罩版式随技能描述长度浮动不可建档)或画面真异动。
        # 不识别遮罩物(负责人方案):盲点右下安全域空白(遮罩语义=「点击空白
        # 处关闭」,面板态该点也是关面板位,树态惰性)直到面板锚回归;连续 6 轮
        # 仍无锚 = 画面真异动,判失配交 agent(节点选择归 agent,op 不自纠)
        if not self.round_by_find_area(screen, _TRACE_SCREEN, '开关-简略描述').is_success:
            self._feedback_clicks += 1
            if self._feedback_clicks >= 6:
                self._final_status = '不在目标技能面板'
                return self.round_success('CLOSE_PANEL')
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '点击区-关面板空白').rect.center)
            return self.round_retry('面板锚未现,点空白回界面', wait=2)
        self._feedback_clicks = 0

        # ③ 分类校验:面板在但显示的不是 target(选中态残留/切换未生效)
        if not self._panel_category_ok():
            self._final_status = '不在目标技能面板'
            return self.round_success('CLOSE_PANEL')

        # ④ 升级执行(两按钮同位不同文,find 按 text 区分)
        if self.round_by_find_area(screen, _TRACE_SCREEN, '按钮-快速升级').is_success:
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-快速升级').rect.center)
            return self.round_retry('快速升级已执行', wait=_TRACE_SETTLE_SEC)

        # ④b 材料不足灰态(按钮带禁用文本,独立于两可点形态):升下一级的
        # 材料缺口超出通用补全与合成覆盖 = 升级不可行,直接判停(该文本与
        # 「材料合成」四字前缀同形,lcs 相似度恰好 0.5 踩线,area 侧已收紧
        # 阈值 0.75,此处再前置判停双保险,避免误入合成分支空点禁用钮)
        if self.round_by_find_area(screen, _TRACE_SCREEN, '文本-材料不足').is_success:
            self._final_status = 'MATERIAL_CAPPED'
            self._end_level = self._read_panel_level()
            log.info('行迹升级: 按钮带「材料不足」(缺口超出补全/合成覆盖),判停于等级 %s',
                     self._end_level)
            return self.round_success('CLOSE_PANEL')

        # ⑤ 缺料两形态(「使用通用材料补全」/「材料合成」同位不同文):
        # fill_generic 授权自动确认;farm_dungeon 预算内 → 券刷路线;
        # 均不可用判停。材料合成形态刷取无收益(原料已足,快速刷取机制
        # 无可刷缺口——光锥线同款裁定)
        if self.round_by_find_area(screen, _TRACE_SCREEN, '按钮-通用材料补全').is_success:
            if self.farm_dungeon and self._farm_rounds < self.farm_rounds_max:
                return self.round_success('NEED_FARM')
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-通用材料补全').rect.center)
                return self.round_retry('已点通用材料补全,等确认弹窗', wait=1.5)
            self._final_status = 'MATERIAL_CAPPED'
            self._end_level = self._read_panel_level()
            log.info('行迹升级: 缺专属材料(farm_dungeon/fill_generic 均未授权),'
                     '判停于等级 %s', self._end_level)
            return self.round_success('CLOSE_PANEL')

        if self.round_by_find_area(screen, _TRACE_SCREEN, '按钮-材料合成').is_success:
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-材料合成').rect.center)
                return self.round_retry('已点材料合成,等确认弹窗', wait=1.5)
            self._final_status = 'MATERIAL_CAPPED'
            self._end_level = self._read_panel_level()
            log.info('行迹升级: 材料合成形态(券刷无收益)且 fill_generic 未授权,'
                     '判停于等级 %s', self._end_level)
            return self.round_success('CLOSE_PANEL')

        # ⑥ 无补全钮形态:仅剩券刷路线(缺可刷材料时「快速刷取」钮在场)
        if self.farm_dungeon and self._farm_rounds < self.farm_rounds_max \
                and self.round_by_find_area(screen, _TRACE_SCREEN, '按钮-快速刷取').is_success:
            return self.round_success('NEED_FARM')

        # ⑦ 两按钮都不命中分两态(锚在=真全缺判停;锚不在=执行后动画/过渡
        # 期按钮暂隐[反馈形态未实测] → 点空白重试不判停——误报判停比多等
        # 一轮危害大)
        if self.round_by_find_area(screen, _TRACE_SCREEN, '文本-可提升至').is_success:
            self._final_status = 'MATERIAL_CAPPED'
            self._end_level = self._read_panel_level()
            log.info('行迹升级: 按钮为禁用态(全缺),判停于等级 %s', self._end_level)
            return self.round_success('CLOSE_PANEL')
        self.ctx.controller.click(
            self.ctx.screen_loader.get_area(_TRACE_SCREEN, '点击区-面板外空白').rect.center)
        return self.round_retry('疑似动画/过渡态,点空白重试', wait=2)

    @node_from(from_name='升级循环', status='NEED_FARM')
    @operation_node(name='券刷链', timeout_seconds=300, node_max_retry_times=30)
    def farm_ticket_chain(self) -> OperationRoundResult:
        """花萼券刷链(按探索裁定新链):面板「快速刷取」→ 培养资源窗口 →
        花萼行券按钮(行锚+按钮双锚防误点「进入」副本)→ 共用快速刷取弹窗
        (连刷次数按 farm_times_per_round 设置)→ 确认 → 结果框关 → 资源
        窗口关 → 回面板态交回升级循环。

        面板态分两态:链内收口回落(_chain_farm_done=True,确认刷完关窗/
        取消路径同落点)→ 复位交回升级循环重判(预算在彼端核);链入口
        (False,NEED_FARM 刚路由进来,窗未开)→ 点面板「快速刷取」开窗:
        点前探无可刷缺口 toast 正判(门控同光锥线——仅前两次点击后的轮
        探测,防慢开窗冗余点击被拒再弹的 toast 被误读为无可刷缺口),命中
        即 MATERIAL_CAPPED 判停收口;漏检由连点封顶(_PANEL_FARM_CLICK_MAX)
        兜底。
        预算在升级循环路由时已核(本链单轮执行,确认后 _farm_rounds+1)。
        连刷轮询用 round_wait 慢询(不计重试——连刷时长随次数不可预估,
        硬上限 = 节点 timeout_seconds)。"""
        screen = self.last_screenshot

        # 快速刷取弹窗在:未确认(设次数+确认)/连刷进行中(确认钮已消失)
        if self.round_by_find_area(screen, _FAST_FARM_DIALOG, '标题-快速刷取弹窗').is_success:
            self._panel_farm_click_rounds = 0
            if self.round_by_find_area(
                    screen, _FAST_FARM_DIALOG, '按钮-确认快速刷取').is_success:
                if self._farm_times_set == 0:
                    set_result = self._set_farm_times(self.farm_times_per_round)
                    if not set_result.is_success:
                        return set_result
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_FAST_FARM_DIALOG, '按钮-确认快速刷取').rect.center)
                self._farm_rounds += 1
                log.info('行迹升级: 第 %d 轮券刷确认(连刷 %d 次,消耗开拓力 %d + 券 %d/次)',
                         self._farm_rounds, self._farm_times_set,
                         _FARM_TRAILBLAZE_PER, _FARM_TICKET_PER)
                # 链内状态机切「已确认刷完」(资源窗口关窗分支依据);记账
                # 读数已入日志,消费后清零备下一轮
                self._chain_farm_done = True
                self._farm_times_set = 0
                return self.round_wait('连刷进行中', wait=_FARM_POLL_SEC)
            return self.round_wait('连刷进行中,慢询等待', wait=_FARM_POLL_SEC)

        # 结果框(领奖完成):关闭后回资源窗口
        if self.round_by_find_area(screen, _FAST_FARM_RESULT, '按钮-关闭刷取结果').is_success:
            self._panel_farm_click_rounds = 0
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_FAST_FARM_RESULT, '按钮-关闭刷取结果').rect.center)
            return self.round_retry('刷取结果框已关,回资源窗口', wait=1.5)

        # 资源窗口在:状态机分流——券未确认(_chain_farm_done=False)时行锚+
        # 券按钮双锚在场才点(防误点「进入」副本——进入按钮同行右侧,走到挑战
        # 画面是设计外链路);确认已点(_chain_farm_done=True)→ 关窗回面板态
        # (取消/确认路径同落点,取消路径已实测)
        if self.round_by_find_area(screen, _RESOURCE_WINDOW_SCREEN, '标题-培养资源窗口').is_success:
            self._panel_farm_click_rounds = 0
            if not self._chain_farm_done:
                if not self.round_by_find_area(
                        screen, _RESOURCE_WINDOW_SCREEN, '行锚-本周可领取奖励次数').is_success:
                    return self.round_wait('资源窗口行锚未现,等加载', wait=1.5)
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_RESOURCE_WINDOW_SCREEN, '按钮-花萼行券按钮').rect.center)
                return self.round_retry('已点花萼行券按钮,等快速刷取弹窗', wait=2)
            result = self.round_by_find_and_click_area(
                screen, _RESOURCE_WINDOW_SCREEN, '按钮-关闭资源窗口',
                until_not_find_all=[(_RESOURCE_WINDOW_SCREEN, '标题-培养资源窗口')],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
            )
            if result.is_success:
                return self.round_retry('资源窗口已关,回面板态', wait=1)
            return result

        # 面板态分两态:链内收口回落(_chain_farm_done=True,确认刷完关窗/
        # 取消路径同落点)→ 复位交回升级循环重判(预算在彼端核);链入口
        # (False,NEED_FARM 刚路由进来,窗未开)→ 点面板「快速刷取」开窗:
        # 点前探无可刷缺口 toast 正判(门控同光锥线——仅前两次点击后的轮
        # 探测,防慢开窗冗余点击被拒再弹的 toast 被误读为无可刷缺口),命中
        # 即 MATERIAL_CAPPED 判停收口;漏检由连点封顶(_PANEL_FARM_CLICK_MAX)
        # 兜底。
        if self.round_by_find_area(screen, _TRACE_SCREEN, '开关-简略描述').is_success:
            if self._chain_farm_done:
                self._chain_farm_done = False
                self._panel_farm_click_rounds = 0
                return self.round_success('回面板', wait=1)
            if self._panel_farm_click_rounds >= _PANEL_FARM_CLICK_MAX:
                self._final_status = 'MATERIAL_CAPPED'
                self._end_level = self._read_panel_level()
                self.save_screenshot(prefix='行迹面板快速刷取')
                log.info('行迹升级: 面板快速刷取连续未开窗(toast 漏检,兜底封顶),'
                         '现场已截图,判停收口')
                return self.round_success('CLOSE_PANEL')
            if self._panel_farm_click_rounds <= 1 and self.round_by_find_area(
                    screen, _TRACE_SCREEN, '提示-无可刷缺口').is_success:
                self._panel_farm_click_rounds = 0
                self._final_status = 'MATERIAL_CAPPED'
                self._end_level = self._read_panel_level()
                self.save_screenshot(prefix='行迹面板快速刷取')
                log.info('行迹升级: 无可刷缺口(游戏 toast 命中),判停收口')
                return self.round_success('CLOSE_PANEL')
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-快速刷取').rect.center)
            self._panel_farm_click_rounds += 1
            return self.round_retry('已点面板快速刷取,等资源窗口', wait=1.5)

        return self.round_wait('券刷链过渡态,慢询等待', wait=_FARM_POLL_SEC)

    def _set_farm_times(self, target: int) -> OperationRoundResult:
        """确认框内把连刷次数设到目标(光锥线同款平移):target=-1 = 点「^」
        拉满;正数 = OCR 读「刷取次数 N」现值 → 点「+」补差值 → 达标即成。"""
        if target == -1:
            max_area = self.ctx.screen_loader.get_area(_FAST_FARM_DIALOG, '按钮-刷取次数拉满')
            self.ctx.controller.click(max_area.rect.center)
            time.sleep(1)  # 滑条动画
            current = self._read_farm_times()
            if current is None:
                time.sleep(1)
                current = self._read_farm_times()
            if current is None:
                return self.round_fail('拉满后无法读取刷取次数')
            self._farm_times_set = current
            log.info('行迹升级: 券刷连刷次数已拉满至 %d', current)
            return self.round_success()
        plus_area = self.ctx.screen_loader.get_area(_FAST_FARM_DIALOG, '按钮-刷取次数加')
        for _ in range(target + 3):  # 点数上界 = 目标+3(防 OCR 偏差死循环)
            current = self._read_farm_times()
            if current is None:
                return self.round_fail('无法读取确认框刷取次数')
            if current >= target:
                self._farm_times_set = current
                return self.round_success()
            self.ctx.controller.click(plus_area.rect.center)
            time.sleep(0.4)  # 滑条动画
        return self.round_fail(f'券刷连刷次数未能设到 {target}')

    def _read_farm_times(self) -> int | None:
        """确认框「刷取次数 N」OCR 取 N。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_FAST_FARM_DIALOG, '读区-刷取次数')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            m = re.search(r'\d+', str(r.data or ''))
            if m:
                return int(m.group())
        return None

    @node_from(from_name='入口校验', status='CLOSE_PANEL')
    @node_from(from_name='升级循环', status='CLOSE_PANEL')
    @node_from(from_name='券刷链', status='CLOSE_PANEL')  # 券刷链 toast 正判/连点封顶判停(缺此边会被兜底边静默接回升级循环)
    @operation_node(name='收尾关面板', timeout_seconds=60, node_max_retry_times=8)
    def close_panel(self) -> OperationRoundResult:
        """一切出口的必经:点空白关面板回树态,落 _final_status。

        空白区取右下安全域(面板态右下被升级/补全/刷取按钮带占据,误触
        升级 = 真实材料消耗;避让清单见画面档「点击区-关面板空白」)。
        纯定位区点击 + until_not 无界等待的防线 = 连等封顶 + 节点限 60s,
        未关闭显式失败交调用方处置。"""
        final = self._final_status if self._final_status else 'MAX_LEVEL'
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, _TRACE_SCREEN, '开关-简略描述').is_success:
            # MISS = 面板已关(反馈遮罩由升级循环 ② 的盲点循环清理,到本节点
            # 时遮罩不应存在):落账
            log.info('行迹升级: 收尾完成,面板已关,终态 %s,等级 %s',
                     final, self._end_level)
            return self.round_success(final, wait=1)
        if self._close_rounds >= _CLOSE_PANEL_MAX_ROUNDS:
            return self.round_fail('面板连续未关闭(空白点击未生效),交调用方处置')
        self.ctx.controller.click(
            self.ctx.screen_loader.get_area(_TRACE_SCREEN, '点击区-关面板空白').rect.center)
        return self.round_retry('关闭面板,返回树态', wait=1.5)
