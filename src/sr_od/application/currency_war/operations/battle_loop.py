import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_telemetry
from sr_od.application.currency_war.operations.handlers.handle_deploy_not_full import (
    HandleDeployNotFull,
)
from sr_od.application.currency_war.operations.handlers.handle_encounter import (
    HandleEncounter,
)
from sr_od.application.currency_war.operations.handlers.handle_invest_env import (
    HandleInvestEnv,
)
from sr_od.application.currency_war.operations.handlers.handle_invest_strategy import (
    HandleInvestStrategy,
)
from sr_od.application.currency_war.operations.handlers.handle_megastar import (
    HandleMegastar,
)
from sr_od.application.currency_war.operations.handlers.handle_select_partner import (
    HandleSelectPartner,
)
from sr_od.application.currency_war.operations.handlers.handle_supply import (
    HandleSupply,
)
from sr_od.application.currency_war.operations.prep.battle_prep import BattlePrepCycle
from sr_od.application.currency_war.operations.prep.shop import BuyShopCards
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CurrencyWarRunLoop(SrOperation):
    """货币战争 对局内主循环:反复「备战单轮 + 轮间过渡」直到对局结束 / 超时。

    状态机(每轮截图后按优先级匹配):
    1. 备战阶段(「购买经验」)→ ``BattlePrepCycle``(买+deploy+出战)→ 等战斗;
    2. 「点击空白加速」/「点击空白处继续」→ 点空白(加速战斗 / 关教程叠层);
    3. 「挑战成功」后「继续挑战」→ 点 → 下一轮;
    4. 「投资环境」3 选 1 → 点左牌 + 「确认」;
    5. 「下一步」等前进按钮 → 点。

    naive 策略(买全部 + 填位 deploy);对局从已进入的备战开始跑(开对局由
    ``StartCurrencyWarMatch`` 负责,本 op 只跑对局内循环)。MAX_ITER 防失控。
    """

    MAX_ITER: ClassVar[int] = 2000  # 整局 3 位面多轮(备战+战斗+多类事件);战斗 round_wait 占大量迭代。
    # 2026-08-04 实跑:500 不够 —— reactive 弱阵战斗慢,plane2 r5 打「蚕食者之影」时 iter 撞 500
    # →「对局循环超时」失败(bot 一直在推进,非逻辑 bug,是迭代预算耗尽)。bump 到 2000(≈66min 预算)。
    # 待优化:MAX_ITER 应只计「动作迭代」(备战/事件/结算),不计战斗 round_wait(战斗长短不该吃预算)。
    # 点空白区(加速战斗 / 关叠层;避开中央内容)
    BLANK: ClassVar[Rect] = Rect(1450, 920, 1560, 980)
    # 结算"前进"按钮(前往结算/下一页/返回货币战争)恒在底部中央,文案随页变。
    # 2026-08-04 实测(失败结算屏 OCR):「下一页」x922y882w76h33、「返回货币战争」x885y882w149h31
    # → 中心均 ~(960,898)。原 (900,882) 偏左 22px 落在按钮左边缘外 → 点空 → 结算翻页卡死。
    # bug#1:round_by_ocr_and_click 的 click 易被 before_screenshot 移鼠标吞掉 → 手动 active_window+sleep+click(同出战)。
    SETTLEMENT_NEXT: ClassVar[Point] = Point(960, 898)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-对局循环')
        self._iter: int = 0
        # 开一次 run 的遥测 run_id(本地 decisions.jsonl 采集用;outcomes/summary 待接)
        cw_telemetry.start_run()
        # 每局重置 A2 稳定 target(防上局 _target_comp 跨局污染;task#16)
        BuyShopCards._target_comp = None

    def _snap(self, tag: str) -> None:
        """初期接触玩法:关键决策点存 debug 截图 + 全量 OCR 日志(定位问题用,验证后去掉)。

        见 sr-od-dev-gameplay-automation「开发时预留日志 + 截图开关 / 信息密度论」:让一次
        实跑暴露尽量多的问题(选人选项长啥样 / OCR 误读 / 坐标漂移 / 漏事件),而非每次只测
        一种情况。截图存 ``.debug/images/``(``save_screenshot``),日志带当前帧全量 OCR 文本
        (选人/事件选项 OCR 现无策略评估 → 先靠 snap 看清每局都 offered 什么,再建评估)。
        非关键路径:try 兜底,debug 失败不影响对局推进。
        """
        try:
            ocr_map = self.ctx.ocr_service.get_ocr_result_map(
                image=self.last_screenshot, rect=None, color_range=None, crop_first=False,
            )
            texts = [k for k, mrl in ocr_map.items() if mrl.max is not None]
            path = self.save_screenshot(prefix=f'cw_{tag}')
            log.info(f'[cw-snap] {tag} iter={self._iter} shot={path} ocr={texts[:15]}')
        except Exception as e:  # noqa: BLE001  debug 路径,失败不阻塞对局
            log.warning(f'[cw-snap] {tag} iter={self._iter} failed: {e}')

    @operation_node(name='对局循环', is_start_node=True, node_max_retry_times=400)
    def loop(self) -> OperationRoundResult:
        self._iter += 1
        if self._iter > CurrencyWarRunLoop.MAX_ITER:
            return self.round_fail(status='对局循环超时')
        # 游戏窗口可能失焦(后台进程抢焦)→ controller.click 不 active_window 会点空,
        # 每轮迭代先聚焦游戏(同 click_game 的 active_window),保证后续点击落地。
        self.ctx.controller.active_window()
        screen = self.last_screenshot

        # 0. 备战被锁(本轮需先选投资策略,顶部有"返回投资策略选择"按钮)→ 点去选策略(check#4 接手)
        if self.round_by_ocr_and_click(screen, '返回投资策略选择', success_wait=2).is_success:
            return self.round_wait(wait=2)

        # 0a. 选择伙伴 overlay(必须在 0b 巨星前:选择伙伴也有"确认选择"但候选是 stage 立绘)
        #     → HandleSelectPartner(点 stage 立绘 + 确认选择,详见 op)。
        #     lcs_percent=0.7:「选择伙伴」与「请选择投资策略」共享「选择」(2/4=0.5=默认阈值)→
        #     投资策略屏被误派发到本 handler(2026-08-04 snap 实测发现)。收紧到 0.7 杀误匹配
        #     (真「选择伙伴」OCR 1.0 不受影响)。
        if self.round_by_ocr(screen, '选择伙伴', lcs_percent=0.7).is_success:
            self._snap('choose_partner')  # 选人选项(立绘名)→ 后续建策略评估用
            HandleSelectPartner(self.ctx).execute()
            return self.round_wait(wait=2)

        # 0b. 巨星强化(有"确认选择"、无"选择伙伴")→ HandleMegastar(选候选 + 确认,详见 op)。
        #     lcs_percent=0.7:同上,防「确认选择」与「请选择投资策略」共享「选择」误匹配。
        if self.round_by_ocr(screen, '确认选择', lcs_percent=0.7).is_success:
            self._snap('megastar')  # 巨星候选(立绘名)→ 后续建策略评估用
            HandleMegastar(self.ctx).execute()
            return self.round_wait(wait=2)

        # 0c. 遭遇节点二选一 → HandleEncounter(点卡身 + 选择;踩坑:中间不能插空白点击,详见 op)。
        if self.round_by_ocr(screen, '遭遇其一').is_success:
            self._snap('encounter')  # 遭遇二选一选项 → 后续建策略评估用
            HandleEncounter(self.ctx).execute()
            return self.round_wait(wait=2)

        # 0d. 出战确认弹窗(未达上限)→ HandleDeployNotFull(勾本局不再提示 + 确认,详见 op)。
        if self.round_by_ocr(screen, '未达上限').is_success:
            HandleDeployNotFull(self.ctx).execute()
            return self.round_wait(wait=3)

        # 1. 备战阶段 → 单轮(买+deploy+出战)
        # 注:遭遇/选择伙伴 等 event overlay 已在 0b/0c 处理(确认选择/未达上限)。
        # 遭遇 round 是普通战斗(2026-08-04 vision 确认:无选项选择 UI,只有难度标签 + 出战),
        # 走正常 prep→出战→战斗(原 遭遇 handler "2选1" 过时,且 click 干扰 prep → stall,已移除)。
        if self.round_by_ocr(screen, '购买经验').is_success:
            BattlePrepCycle(self.ctx).execute()
            return self.round_wait(wait=2)  # 战斗中,下轮再判

        # 1b. 详情弹窗(点卡触发的"生命之花祝福"等:有「可合成列表」、无确认)→ ESC 关闭
        if self.round_by_ocr(screen, '可合成列表').is_success:
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=1.5)

        # 2. 点击空白加速 / 点击空白处继续 → 点空白
        if (self.round_by_ocr(screen, '点击空白加速').is_success
                or self.round_by_ocr(screen, '点击空白处继续').is_success):
            self.ctx.controller.click(CurrencyWarRunLoop.BLANK.center)
            return self.round_wait(wait=1.5)

        # 3. 挑战成功/结束 → 继续挑战(过渡屏按钮可能"可见但延迟可点" → 先等再刷新点)
        if self.round_by_ocr(screen, '继续挑战').is_success:
            time.sleep(1.0)
            if self.round_by_ocr_and_click(self.screenshot(), '继续挑战', success_wait=2).is_success:
                return self.round_wait(wait=2)

        # 3b. 对局结束结算(前往结算→下一页→返回货币战争)→ 逐页点回大厅。结算"前进"按钮恒在底部中央
        # ~(900,882)。bug#1:round_by_ocr_and_click 的 click 易被 before_screenshot 移鼠标吞掉(实测卡死在
        # 结算页 → 对局循环超时)→ 改 round_by_ocr 检测 + active_window/sleep + 直接 click(同 出战 解法)。
        for btn in ('前往结算', '下一页', '返回货币战争'):
            if self.round_by_ocr(screen, btn).is_success:
                self.ctx.controller.mouse_move(CurrencyWarRunLoop.SETTLEMENT_NEXT)  # bug#1 fix
                time.sleep(0.3)
                self.ctx.controller.click(CurrencyWarRunLoop.SETTLEMENT_NEXT)
                return self.round_wait(wait=2)

        # 3c. 回到大厅(对局结束)→ loop 完成,避免在 lobby 无动作无限 retry。
        # 用「创业指南」(大厅左菜单独有、无特殊括号,OCR 稳)而非「开始「货币战争」」(括号 gt 不稳)
        if self.round_by_ocr(screen, '创业指南').is_success:
            return self.round_success('对局结束,回大厅')

        # 4. 选择类事件(3 选 1 + 确认)→ 分派到对应 op(各 op TODO 接 decide_event/decide_supply)。
        #    _snap 捕获 3 张卡 OCR(投资策略/环境名)→ 策略评估接线后据此挑最优卡,非盲点中卡。
        if self.round_by_ocr(screen, '投资策略').is_success:
            self._snap('invest_strategy')
            HandleInvestStrategy(self.ctx).execute()
            return self.round_wait(wait=2)
        if self.round_by_ocr(screen, '投资环境').is_success:
            self._snap('invest_env')
            HandleInvestEnv(self.ctx).execute()
            return self.round_wait(wait=2)
        if self.round_by_ocr(screen, '补给阶段').is_success:
            self._snap('supply')
            HandleSupply(self.ctx).execute()
            return self.round_wait(wait=2)

        # 5. 前进按钮(简报等)
        if self.round_by_ocr_and_click(screen, '下一步', success_wait=2).is_success:
            return self.round_wait(wait=1.5)

        # 6. 战斗/过场屏(总伤害/数据统计 在,无其他动作;OCR 常漏「点击空白加速」)→ 点空白加速/推进。
        # 只用战斗独有关键词;不用「羁绊」(大厅"羁绊链路"会误匹配)
        if (self.round_by_ocr(screen, '总伤害').is_success
                or self.round_by_ocr(screen, '数据统计').is_success):
            self.ctx.controller.click(CurrencyWarRunLoop.BLANK.center)
            return self.round_wait(wait=1.5)

        return self.round_retry(wait=2)
