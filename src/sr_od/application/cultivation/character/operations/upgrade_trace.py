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
判停收口,漏检由连点封顶(4 次)兜底。券刷记账以结果框为成功证据:确认
点击不动账,「快速刷取结果弹窗」在场(领奖完成)才落账——确认点击未生效
重入轮凭判据位跳过设次数只重发确认,与角色晋阶/光锥线同口径。

补料优先级(负责人裁定,char/LC 同款):通用材料补全 → 快速刷取券 →
手动战斗——通用材料非稀缺优先消耗;授权补全时优先补全、不刷取(刷取会被
游戏以无可刷缺口拒绝),未授权补全且券刷预算内才转券刷。确认刷取被开拓力
不足拦截时游戏弹「开拓力补充」弹窗(全局模态)——链状态机探测首位识别
守卫,点「取消」原路清场后 POWER_CAPPED 可恢复判停(「确认」= 星琼购
开拓力,永不触碰,画面档刻意不建该 area)。

手动刷本划出 op 边界(负责人裁定):结算后回不到面板态,op 判停交还
agent——周本走 ChallengeEchoOfWarByName;花萼手动刷由调用方按行迹缺料
材料自行导航至对应副本挑战画面(FarmTraceMaterialOp 立项前过渡态;
FarmLightConeMaterialOp 只认光锥缺料格,行迹判停后不可用,勿套用)。

面板态交互(实机摸底):面板按钮三态——白底「快速升级」= 材料足;
「使用通用材料补全」/「材料合成」= 缺料两形态(fill_generic 授权自动
确认);「已达最大等级」蓝字 = 满级;「可提升至N级」文本在场且按钮带无
可用钮 = 全缺判停态。确认框滑条次数不记忆(重开恒 1)。开拓力不足时面板
「挑战/刷取」点击静默无反应(不弹窗)——链路重试预算耗尽即判停,不空烧
轮次;确认刷取被拦则弹「开拓力补充」弹窗,由链守卫识别判停(见上)。

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
from sr_od.application.cultivation import upgrade_common
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_TRACE_SCREEN: str = '角色-行迹'
_FAST_FARM_DIALOG: str = upgrade_common.FAST_FARM_DIALOG_SCREEN
_FAST_FARM_RESULT: str = upgrade_common.FAST_FARM_RESULT_SCREEN
_RESOURCE_WINDOW_SCREEN: str = upgrade_common.RESOURCE_WINDOW_SCREEN
# 开拓力补充弹窗(全局模态,确认刷取被拦时游戏弹出;与光锥线共用画面档)
_POWER_REPLENISH_DIALOG: str = upgrade_common.POWER_DIALOG_SCREEN

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

# 本线接入参数(线私有值单一源;消耗常量定义保留在上方,spec 只作入参搬运;
# 手动刷本划出 op 边界,副本锚表/读名屏序空置)
_SPEC = upgrade_common.UpgradeLineSpec(
    log_prefix='行迹升级',
    stop_status='MATERIAL_CAPPED',
    ascend_screen=_TRACE_SCREEN,
    dungeon_title_areas=(),
    name_read_screens=(),
    reentry_hint='',
    trailblaze_per=_FARM_TRAILBLAZE_PER,
    ticket_per=_FARM_TICKET_PER,
)


class UpgradeTraceOp(SrOperation):
    """把面板当前技能升到当前上限(起点=面板态,终点=关面板回树态)。

    结果状态:MAX_LEVEL(已达最大等级,含升满当前上限语义)/ MATERIAL_CAPPED
    (材料不足判停,日志带收尾等级)/ POWER_CAPPED(券刷确认被开拓力不足
    拦截判停,可恢复——开拓力随时间恢复,续跑即继续;日志带收尾等级)/
    不在目标技能面板(起跑校验或循环内画面异动 fail——前者零消耗直落,
    后者经收尾关面板回树态)。券刷记账以结果框为成功证据:确认点击不动
    账,结果框在场才落账(与角色晋阶/光锥线同口径)。

    补料优先级(负责人裁定,char/LC 同款):通用材料补全 → 快速刷取券 →
    手动战斗——通用材料非稀缺优先消耗;券免战斗次之;手动战斗划出 op
    边界。trace 行为后缀:缺料可合成形态(「使用通用材料补全」钮在场)
    授权补全(fill_generic 默认 True)时优先补全、不刷取——刷取会被游戏
    以无可刷缺口拒绝;未授权补全且 farm_dungeon 预算内才转券刷,缺口
    不可刷由 toast 正判+连点封顶兜底判停;材料合成形态券刷无收益,不走
    券刷。**farm_dungeon 发起前调用方必须向用户说明消耗并获明确同意**。
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
        upgrade_common.validate_farm_params(farm_times_per_round, farm_rounds_max)
        self.fill_generic: bool = fill_generic
        self.farm_dungeon: bool = farm_dungeon
        self.farm_times_per_round: int = farm_times_per_round
        self.farm_rounds_max: int = farm_rounds_max
        SrOperation.__init__(self, ctx, op_name=gt('行迹升级') + '-' + self.target,
                             node_max_retry_times=24)
        self._farm_rounds: int = 0  #: 已执行的券刷轮数(结果框轮 settle 时增长,预算控制)
        self._farm_draws: int = 0  #: 券刷累计次数(确认框实际设到的值,券/开拓力消耗记账口径,与 char/LC 同名同义)
        self._farm_times_set: int = 0  #: 券刷记账判据位:确认框已设次数且未记账(非零);settle 落账或守卫拦截作废时清零
        self._chain_farm_done: bool = False  #: 券刷链内状态机:确认已点=True(窗口分支据此关窗而非再点券钮)
        self._capped: bool = False  #: 券刷确认被开拓力不足拦截判停(True=链状态机进清场模式,只关不发起)
        self._farm_window_wait_rounds: int = 0  #: 面板钮连续点击尝试数(「尝试发出即增」口径;toast 探测门控与漏检兜底封顶用,窗口/弹窗出现即复位)
        self._final_status: str | None = None  #: 终态 status(收尾节点携带落账)
        self._close_rounds: int = 0  #: 收尾关面板连等计数(纯定位区无界等待防线)
        self._feedback_clicks: int = 0  #: 反馈遮罩期连续盲点计数(连续 6 轮无面板锚判画面异动)
        self._buttonless_rounds: int = 0  #: 升级循环按钮带全空连续计数(连续 3 轮=材料不足灰态判停;任一按钮命中复位)
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
            self._buttonless_rounds = 0
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-快速升级').rect.center)
            return self.round_retry('快速升级已执行', wait=_TRACE_SETTLE_SEC)

        # ⑤ 缺料可合成形态(「使用通用材料补全」钮在场 = 缺口可由合成
        # 覆盖)。补料优先级(负责人裁定,char/LC 同款)= 通用材料补全 →
        # 券刷 → 手动战斗(划出 op 边界):通用材料非稀缺,授权补全时优先
        # 补全、不刷取——此形态点面板「快速刷取」会被游戏以无可刷缺口
        # 拒绝;未授权补全且 farm 预算内才转券刷(缺口不可刷由 toast 正判
        # +连点封顶兜底);均不可用判停。
        if self.round_by_find_area(screen, _TRACE_SCREEN, '按钮-通用材料补全').is_success:
            self._buttonless_rounds = 0
            if self.fill_generic:
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-通用材料补全').rect.center)
                return self.round_retry('已点通用材料补全,等确认弹窗', wait=1.5)
            if self.farm_dungeon and self._farm_rounds < self.farm_rounds_max:
                return self.round_success('NEED_FARM')
            self._final_status = 'MATERIAL_CAPPED'
            self._end_level = self._read_panel_level()
            log.info('行迹升级: 缺专属材料(farm_dungeon/fill_generic 均未授权),'
                     '判停于等级 %s', self._end_level)
            return self.round_success('CLOSE_PANEL')

        # ⑤b 材料合成形态(原料已足):券刷无收益(快速刷取机制无可刷缺口,
        # 光锥线同款裁定),不走券刷——补全/判停两出口
        if self.round_by_find_area(screen, _TRACE_SCREEN, '按钮-材料合成').is_success:
            self._buttonless_rounds = 0
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
        # 期按钮暂隐 → 点空白重试不判停——误报判停比多等一轮危害大)。
        # 另一态:材料不足灰态(禁用钮+无可提升标记+快速刷取入口消失,重试
        # 永不收敛)——用连续轮次区分:按钮带全空连续 3 轮 = 灰态判停;过渡
        # 态一两轮内按钮回归,计数复位(④⑤⑤b 命中处复位)
        if self.round_by_find_area(screen, _TRACE_SCREEN, '文本-可提升至').is_success:
            self._final_status = 'MATERIAL_CAPPED'
            self._end_level = self._read_panel_level()
            log.info('行迹升级: 按钮为禁用态(全缺),判停于等级 %s', self._end_level)
            return self.round_success('CLOSE_PANEL')
        self._buttonless_rounds += 1
        if self._buttonless_rounds >= 3:
            self._final_status = 'MATERIAL_CAPPED'
            self._end_level = self._read_panel_level()
            log.info('行迹升级: 按钮带连续 %d 轮全空(材料不足灰态),判停于等级 %s',
                     self._buttonless_rounds, self._end_level)
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

        记账口径(与角色晋阶/光锥线同款):确认点击不动账,结果框「按钮-
        关闭刷取结果」在场 = 领奖完成 = 唯一成功证据,命中处 settle 落账
        (_farm_times_set 非零才计,判据位语义「已设未记账」);单节点状态机
        本就逐轮探测结果框,无 helper success 第二记账点。确认未生效重入
        轮凭判据位跳过设次数只重发确认(宁可少计不多计——确认生效但 op
        中途 fail 的边界下少计一轮,与 char/LC 取向一致)。

        开拓力守卫(探测序列首位):「开拓力补充弹窗」是全局模态,在场时
        其余画面锚在暗遮罩下全盲,首位识别是唯一不被误分流的探测位。命中
        = 确认点击被拦截,本轮未成交未记账——点「取消」(「确认」是星琼购
        开拓力,永不触碰,画面档刻意不建该 area)、仅清判据位作废本轮次数
        记录(零回滚:_farm_rounds 只在 settle 增长,守卫时本轮尚未 settle,
        禁止任何对账本的减法回滚)、置 _capped 可恢复判停(开拓力随时间
        恢复,续跑即继续)。

        清场模式(_capped 置位期间各态变体,只关不发起):补充弹窗再点取消
        (点击未生效重试)/快速刷取弹窗点其取消/结果框关(settle 判据位已零,
        幂等无记账,复用现状分支)/资源窗口一律关窗(不看 _chain_farm_done
        ——拦截后落点未实机确认,各态变体兜住)/面板态读收尾等级转
        CLOSE_PANEL(不得回「回面板」交升级循环——判停后重入违反可恢复
        判停语义);各态全 miss(过渡帧)落既有慢询兜底,节点超时 fail
        交调用方。

        面板态分两态(非清场):链内收口回落(_chain_farm_done=True,确认刷完
        关窗/取消路径同落点)→ 复位交回升级循环重判(预算在彼端核);链入口
        (False,NEED_FARM 刚路由进来,窗未开)→ 点面板「快速刷取」开窗:
        点前探无可刷缺口 toast 正判(门控同光锥线——仅前两次点击后的轮
        探测,防慢开窗冗余点击被拒再弹的 toast 被误读为无可刷缺口),命中
        即 MATERIAL_CAPPED 判停收口;漏检由连点封顶(spec.farm_open_max_attempts)
        兜底。
        连刷轮询用 round_wait 慢询(不计重试——连刷时长随次数不可预估,
        硬上限 = 节点 timeout_seconds)。"""
        screen = self.last_screenshot

        # ⓪ 开拓力守卫(探测序列首位,理由见 docstring):确认刷取被拦
        if self.round_by_find_area(screen, _POWER_REPLENISH_DIALOG,
                                   '标题-开拓力补充弹窗').is_success:
            result = self.round_by_find_and_click_area(
                screen, _POWER_REPLENISH_DIALOG, '按钮-取消',
                until_not_find_all=[(_POWER_REPLENISH_DIALOG, '标题-开拓力补充弹窗')],
                pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
            )
            # 仅清判据位(本轮未成交未记账,不动历史账):禁止对 _farm_rounds
            # 做减法——记账点已后置到结果框轮,守卫时本轮尚未 settle,天然
            # 零回滚,不得再加反向调整破坏该性质
            self._farm_times_set = 0
            if not self._capped:
                self._capped = True
                self._final_status = 'POWER_CAPPED'
                log.info('行迹升级: 券刷确认被开拓力不足拦截,本轮未成交——'
                         '原路清场返回面板态后关面板(开拓力随时间恢复,续跑即继续)')
            if result.is_success:
                return self.round_retry('补充弹窗已取消,清场中', wait=1.5)
            return result

        # 快速刷取弹窗在:清场模式只点其取消(原路清场,不发起刷取);正常
        # 分未确认(设次数+确认)/连刷进行中(确认钮已消失慢询)
        if self.round_by_find_area(screen, _FAST_FARM_DIALOG, '标题-快速刷取弹窗').is_success:
            self._farm_window_wait_rounds = 0
            if self._capped:
                result = self.round_by_find_and_click_area(
                    screen, _FAST_FARM_DIALOG, '按钮-取消',
                    until_not_find_all=[(_FAST_FARM_DIALOG, '标题-快速刷取弹窗')],
                    pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
                )
                if result.is_success:
                    return self.round_retry('选次数确认框已取消,清场中', wait=1.5)
                return result
            if self.round_by_find_area(
                    screen, _FAST_FARM_DIALOG, '按钮-确认快速刷取').is_success:
                # 幂等判据:判据位非零 = 已设未记账(确认未生效重入轮),
                # 跳过设次数只重发确认
                if self._farm_times_set == 0:
                    set_result = self._set_farm_times(self.farm_times_per_round)
                    if not set_result.is_success:
                        return set_result
                self.ctx.controller.click(
                    self.ctx.screen_loader.get_area(_FAST_FARM_DIALOG, '按钮-确认快速刷取').rect.center)
                # 事务式记账:确认点击不动账——置链状态位后慢询,账在结果框
                # 轮 settle;判据位保持非零(「已设未记账」),确认未生效重入
                # 轮据此跳过设次数只重发确认
                self._chain_farm_done = True
                return self.round_wait('连刷进行中', wait=_FARM_POLL_SEC)
            return self.round_wait('连刷进行中,慢询等待', wait=_FARM_POLL_SEC)

        # 结果框(领奖完成 = 确认点击生效的成功证据):settle 落账后关闭回
        # 资源窗口;清场模式轮判据位已零,settle 幂等无操作,行为等价「只关」
        if self.round_by_find_area(screen, _FAST_FARM_RESULT, '按钮-关闭刷取结果').is_success:
            self._farm_window_wait_rounds = 0
            self._settle_farm_accounting()
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_FAST_FARM_RESULT, '按钮-关闭刷取结果').rect.center)
            return self.round_retry('刷取结果框已关,回资源窗口', wait=1.5)

        # 资源窗口在:清场模式或确认已点 → 关窗回面板态(取消/确认路径同
        # 落点,取消路径已实测;清场不看 _chain_farm_done——拦截后落点未
        # 实机确认,窗口在场一律关,不得再点券钮发起新一轮刷取);正常且
        # 券未确认时行锚+券按钮双锚在场才点(防误点「进入」副本——进入
        # 按钮同行右侧,走到挑战画面是设计外链路)
        if self.round_by_find_area(screen, _RESOURCE_WINDOW_SCREEN, '标题-培养资源窗口').is_success:
            self._farm_window_wait_rounds = 0
            if self._capped or self._chain_farm_done:
                result = self.round_by_find_and_click_area(
                    screen, _RESOURCE_WINDOW_SCREEN, '按钮-关闭资源窗口',
                    until_not_find_all=[(_RESOURCE_WINDOW_SCREEN, '标题-培养资源窗口')],
                    pre_delay=0.5, success_wait=1.5, retry_wait=1.5,
                )
                if result.is_success:
                    return self.round_retry('资源窗口已关,回面板态', wait=1)
                return result
            if not self.round_by_find_area(
                    screen, _RESOURCE_WINDOW_SCREEN, '行锚-本周可领取奖励次数').is_success:
                return self.round_wait('资源窗口行锚未现,等加载', wait=1.5)
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_RESOURCE_WINDOW_SCREEN, '按钮-花萼行券按钮').rect.center)
            return self.round_retry('已点花萼行券按钮,等快速刷取弹窗', wait=2)

        # 面板态分两态(非清场):链内收口回落(_chain_farm_done=True,确认刷完
        # 关窗/取消路径同落点)→ 复位交回升级循环重判(预算在彼端核);链入口
        # (False,NEED_FARM 刚路由进来,窗未开)→ 点面板「快速刷取」开窗:
        # 点前探无可刷缺口 toast 正判(门控同光锥线——仅前两次点击后的轮
        # 探测,防慢开窗冗余点击被拒再弹的 toast 被误读为无可刷缺口),命中
        # 即 MATERIAL_CAPPED 判停收口;漏检由连点封顶(spec.farm_open_max_attempts)
        # 兜底。
        if self.round_by_find_area(screen, _TRACE_SCREEN, '开关-简略描述').is_success:
            if self._capped:
                # 清场模式面板态:复位与等待复用收口分支,返回状态改
                # CLOSE_PANEL——不得回「回面板」交升级循环(判停后重入违反
                # 可恢复判停语义);已在面板态,读收尾等级一次供日志对照
                self._chain_farm_done = False
                self._farm_window_wait_rounds = 0
                if self._end_level is None:
                    self._end_level = self._read_panel_level()
                log.info('行迹升级: 开拓力不足判停(POWER_CAPPED)清场完成,'
                         '等级 %s,转收尾关面板', self._end_level)
                return self.round_success('CLOSE_PANEL', wait=1)
            if self._chain_farm_done:
                self._chain_farm_done = False
                self._farm_window_wait_rounds = 0
                return self.round_success('回面板', wait=1)
            if self._farm_window_wait_rounds >= _SPEC.farm_open_max_attempts:
                self._final_status = 'MATERIAL_CAPPED'
                self._end_level = self._read_panel_level()
                self.save_screenshot(prefix='行迹面板快速刷取')
                log.info('行迹升级: 面板快速刷取连续未开窗(toast 漏检,兜底封顶),'
                         '现场已截图,判停收口')
                return self.round_success('CLOSE_PANEL')
            if upgrade_common.no_farm_gap_toast_hit(self, _TRACE_SCREEN,
                                                    self._farm_window_wait_rounds):
                self._farm_window_wait_rounds = 0
                self._final_status = 'MATERIAL_CAPPED'
                self._end_level = self._read_panel_level()
                self.save_screenshot(prefix='行迹面板快速刷取')
                log.info('行迹升级: 无可刷缺口(游戏 toast 命中),判停收口')
                return self.round_success('CLOSE_PANEL')
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_TRACE_SCREEN, '按钮-快速刷取').rect.center)
            self._farm_window_wait_rounds += 1
            return self.round_retry('已点面板快速刷取,等资源窗口', wait=1.5)

        return self.round_wait('券刷链过渡态,慢询等待', wait=_FARM_POLL_SEC)

    def _settle_farm_accounting(self) -> None:
        """本轮券刷记账(幂等):结果框「按钮-关闭刷取结果」在场 = 领奖完成
        = 确认点击生效的成功证据(单节点状态机本就逐轮探测结果框,无
        char/LC 的 helper success 第二记账点);以 _farm_times_set 非零为
        未记账判据,记账后归零,重入轮不重复计。"""
        upgrade_common.settle_farm_accounting(self, _SPEC)

    def _set_farm_times(self, target: int) -> OperationRoundResult:
        """确认框内把连刷次数设到目标(光锥线同款平移):target=-1 = 点「^」
        拉满;正数 = OCR 读「刷取次数 N」现值 → 点「+」补差值 → 达标即成。

        入口先清判据位(实际设到的值在成功路径写入):设置失败不得残留
        旧值,否则重入轮会拿旧判据跳过设次数直接确认。"""
        return upgrade_common.set_farm_times(self, _SPEC, target)

    def _read_farm_times(self) -> int | None:
        """确认框「刷取次数 N」OCR 取 N。"""
        return upgrade_common.read_farm_times(self)

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
