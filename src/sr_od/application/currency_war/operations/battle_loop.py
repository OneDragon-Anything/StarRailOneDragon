import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war import cw_telemetry
from sr_od.application.currency_war.operations.prep.battle_prep import BattlePrepCycle
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
    # 选择类事件卡牌:点**中牌** x≈900 @ y550(投资环境/补给,点卡身选中)。
    # 各事件牌位 x 变化(3 张/5 张不定),中点最稳命中任一张(朴素选一张即可推进)。
    INVEST_CARD: ClassVar[Point] = Point(900, 550)
    # 投资策略:点卡身会开详情,需点**卡底 y≈815** 选中(实测 920 有效;900 偏左 20px 会卡)。
    INVEST_CARD_BOTTOM: ClassVar[Point] = Point(920, 815)
    # 投资环境:body y550 开角色对话(佩佩),需点**卡底 y≈700** 选中(实测)。
    INVEST_ENV_CARD: ClassVar[Point] = Point(900, 700)
    # 结算"前进"按钮(前往结算/下一页/返回货币战争)恒在底部中央 ~(900,882),文案随页变。
    # bug#1:round_by_ocr_and_click 的 click 易被 before_screenshot 移鼠标吞掉 → 手动 active_window+sleep+click(同出战)。
    SETTLEMENT_NEXT: ClassVar[Point] = Point(900, 882)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-对局循环')
        self._iter: int = 0
        # 开一次 run 的遥测 run_id(本地 decisions.jsonl 采集用;outcomes/summary 待接)
        cw_telemetry.start_run()

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

        # 0b. 巨星强化选择轮(有"确认选择"按钮)→ 选左候选 + 确认选择
        if self.round_by_ocr(screen, '确认选择').is_success:
            self.ctx.controller.click(Point(822, 333))  # 左候选(花火/大丽花位)
            time.sleep(0.6)
            self.round_by_ocr_and_click(self.screenshot(), '确认选择', success_wait=2)
            return self.round_wait(wait=2)

        # 0c. 出战确认弹窗("可出战角色人数未达上限")→ 勾"本局不再提示"+ 确认(阵容不全出战时触发;
        # 之前所有"出战卡死"的真根因 —— 非bug#1,是此确认弹窗未处理)
        if self.round_by_ocr(screen, '未达上限').is_success:
            self.ctx.controller.active_window()
            self.ctx.controller.click(Point(912, 589))  # 本局不再提示(本局永久自动确认)
            time.sleep(0.3)
            self.ctx.controller.click(Point(1159, 653))  # 确认
            return self.round_wait(wait=3)

        # 1. 备战阶段 → 单轮(买+deploy+出战)
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
                self.ctx.controller.active_window()
                time.sleep(0.5)
                self.ctx.controller.click(CurrencyWarRunLoop.SETTLEMENT_NEXT)
                return self.round_wait(wait=2)

        # 3c. 回到大厅(对局结束)→ loop 完成,避免在 lobby 无动作无限 retry。
        # 用「创业指南」(大厅左菜单独有、无特殊括号,OCR 稳)而非「开始「货币战争」」(括号 gt 不稳)
        if self.round_by_ocr(screen, '创业指南').is_success:
            return self.round_success('对局结束,回大厅')

        # 4. 选择类事件(3 选 1 + 确认)→ 选一张 + 确认。
        #  投资策略:点卡身开详情,需点**卡底 y≈815** 选中;投资环境/补给:点卡身 y≈550 选中。
        if self.round_by_ocr(screen, '投资策略').is_success:
            # 投资策略卡位因变体不同:body(900,550)对部分变体直接选中、对部分开 detail;
            # 先点 body → 若确认被遮(detail 开了)→ ESC + 卡底(920,815)→ 确认
            self.ctx.controller.click(CurrencyWarRunLoop.INVEST_CARD)
            time.sleep(0.6)
            if not self.round_by_ocr(self.screenshot(), '确认').is_success:
                self.ctx.controller.btn_tap('esc')
                time.sleep(0.5)
                self.ctx.controller.click(CurrencyWarRunLoop.INVEST_CARD_BOTTOM)
                time.sleep(0.6)
            self.round_by_ocr_and_click(self.screenshot(), '确认', success_wait=2)
            return self.round_wait(wait=2)
        if self.round_by_ocr(screen, '投资环境').is_success:
            self.ctx.controller.click(CurrencyWarRunLoop.INVEST_ENV_CARD)  # 卡底 y700(body 550 开佩佩对话)
            time.sleep(0.6)
            self.round_by_ocr_and_click(self.screenshot(), '确认', success_wait=2)
            return self.round_wait(wait=2)
        if self.round_by_ocr(screen, '补给阶段').is_success:
            self.ctx.controller.click(CurrencyWarRunLoop.INVEST_CARD)  # body y550(补给卡 body 不开对话)
            time.sleep(0.6)
            self.round_by_ocr_and_click(self.screenshot(), '确认', success_wait=2)
            return self.round_wait(wait=2)
        # 4b. 遭遇节点(2 选 1 难度:遭遇其一/其三)→ 选左遭遇 + 选择
        if self.round_by_ocr(screen, '遭遇节点').is_success:
            self.ctx.controller.click(Point(646, 500))  # 左遭遇(遭遇其一)中心
            time.sleep(0.6)
            self.round_by_ocr_and_click(self.screenshot(), '选择', success_wait=2)
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
