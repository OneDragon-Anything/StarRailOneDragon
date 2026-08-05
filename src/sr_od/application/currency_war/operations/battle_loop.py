import random
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_telemetry
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_observation import (
    read_game_state,
    read_phase_round,
    read_round_outcome,
    reset_phase_round_cache,
)
from sr_od.application.currency_war.cw_state import GameState, MatchOutcome
from sr_od.application.currency_war.cw_strategy import CurrencyWarMatch
from sr_od.application.currency_war.cw_strategy_manager import StrategyManager
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
from sr_od.application.currency_war.operations.handlers.handle_select_partner import (
    HandleSelectPartner,
)
from sr_od.application.currency_war.operations.prep.battle_prep import BattlePrepCycle
from sr_od.application.currency_war.operations.run_nodes.run_megastar_node import (
    RunMegastarNode,
)
from sr_od.application.currency_war.operations.run_nodes.run_supply_node import (
    RunSupplyNode,
)
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
    SETTLEMENT_NEXT: ClassVar[Point] = Point(960, 898)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-对局循环')
        self._iter: int = 0
        # 开一次 run 的遥测 run_id(本地 decisions.jsonl 采集用;outcomes/summary 待接)
        cw_telemetry.start_run()
        # 每局清空 plane/round last-known-good(防跨局复用上局值;task#24)
        reset_phase_round_cache()
        # 策略插件机制(D-34/§11.7):每局新建 CurrencyWarMatch(strategy+session)挂 ctx。__init__ 时
        # SrOperation 还没 last_screenshot(截图由 node runner 进 @operation_node 时给)→ 不能 read_game_state;
        # on_match_start 在 loop() 首次截图后调(见下方 _iter==1 守卫)。跨步状态进 session.target_comp
        # (替代旧 BuyShopCards._target_comp class-attr hack,语义等价:每局新建已是现行为)。
        self._cw_config: CurrencyWarConfig = CurrencyWarConfig(self.ctx.current_instance_idx)
        _strategy = StrategyManager(self.ctx, self.ctx.currency_war_strategy_plugin_dirs).instantiate(
            self._cw_config.strategy_id)
        _session = _strategy.create_session(self._cw_config)
        if self._cw_config.strategy_seed is not None:
            _session.rng = random.Random(self._cw_config.strategy_seed)
        self.ctx.cw_match = CurrencyWarMatch(_strategy, _session)
        # 简报词缀(StartCurrencyWarMatch 读存 ctx.cw_briefing_affixes)→ copy 到 session(mechanics_fit 输入)
        if self.ctx.cw_briefing_affixes:
            _session.briefing_affixes = list(self.ctx.cw_briefing_affixes)
            self.ctx.cw_briefing_affixes = None  # 取走清空(防跨局复用)
        # 简报首领(3 位面 boss 名)→ copy 到 session(boss_fit 输入)
        if self.ctx.cw_briefing_bosses:
            _session.briefing_bosses = list(self.ctx.cw_briefing_bosses)
            self.ctx.cw_briefing_bosses = None  # 取走清空(防跨局复用)

    def _snap(self, tag: str) -> None:
        """初期接触玩法:关键决策点存 debug 截图 + 全量 OCR 日志(定位问题用,验证后去掉)。

        见 od-dev-gameplay-automation「开发时预留日志 + 截图开关 / 信息密度论」:让一次
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

    def _record_round_outcome(self, screen) -> None:
        """P1.5 观测回路:结算屏(挑战结束 + 小队生命值)→ ``read_round_outcome`` → ``strategy.on_round_end``。

        喂本回合战后 hp_after 给 ``PerformanceTracker``(via on_round_end 默认实现 ``performance.record``),
        记掉血 trend(观测驱动,非预测)。非结算屏(无「挑战结束」)→ 跳过。失败不阻塞对局(观测为辅)。
        node_type 暂粗(默认普通战斗,boss/elite 节点追踪后续 refine)。plane/round 用 last-known
        (``read_phase_round`` 结算屏不显 plane/round,返回上次备战读的)。
        """
        if self.ctx.cw_match is None:
            return
        if not self.round_by_ocr(screen, '挑战结束').is_success:
            return  # 非结算屏(继续挑战可能在他处)→ 不调 on_round_end,免误记
        try:
            _session = self.ctx.cw_match.session
            _plane, _round = read_phase_round(self.ctx, screen)   # last-known(结算屏不显 plane/round)
            _comp_tag = _session.target_comp.name if _session.target_comp else '?'
            _obs = read_round_outcome(self.ctx, screen, plane=_plane, round_num=_round,
                                      comp_tag=_comp_tag, node_type='普通战斗')
            self.ctx.cw_match.strategy.on_round_end(
                GameState(), _session, self._cw_config, _obs)
            log.info('[cw-loop] on_round_end plane=%s round=%s hp_after=%s conf=%s comp=%s',
                     _plane, _round, _obs.hp_after, _obs.hp_confidence, _comp_tag)
        except Exception as e:  # noqa: BLE001  观测回路失败不阻塞对局
            log.warning('[cw-loop] on_round_end 失败(不阻塞): %s', e)

    @operation_node(name='对局循环', is_start_node=True, node_max_retry_times=400)
    def loop(self) -> OperationRoundResult:
        self._iter += 1
        if self._iter > CurrencyWarRunLoop.MAX_ITER:
            return self.round_fail(status='对局循环超时')
        screen = self.last_screenshot

        # on_match_start(每局首次截图后调一次;D-34/§11.7):P1 默认 no-op,自定义策略可读 state 初始化。
        # 尽力而为 read_game_state(默认实现不读);**不做 hp 覆盖** —— hp 覆盖是 update_target 的事(§11.6 M6)。
        if self._iter == 1 and self.ctx.cw_match is not None:
            self.ctx.cw_match.strategy.on_match_start(
                read_game_state(self.ctx, screen), self.ctx.cw_match.session, self._cw_config)

        # 0. 备战被锁(顶部"返回投资策略选择"按钮)→ 点去选策略(check#4 接手)。
        #    lcs_percent=0.9:防与「请选择投资策略」共享「选择投资策略」(6/8=0.75=默认阈值之上)
        #    误匹配 → 投资策略屏被本分支吞(点标题不动作)→ 死循环(2026-08-04 实跑发现,卡 plane1)。
        #    真「返回投资策略选择」按钮 OCR 1.0 不受影响。
        if self.round_by_ocr_and_click(screen, '返回投资策略选择', success_wait=2, lcs_percent=0.9).is_success:
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
            RunMegastarNode(self.ctx).execute()  # 生命周期 owner:验证 overlay 消失,超预算 bail
            return self.round_wait(wait=2)

        # 0c. 遭遇节点(3 难度选择:遭遇其一/其二/其三 + 选择)→ HandleEncounter(点左卡=遭遇其一=最易 + 选择)。
        #     ↺ D-39 修正 D-35:D-35「遭遇=普通战斗无 UI」是误判 —— 实有 3 难度选择 UI 的遭遇节点(2026-08-05
        #     实跑再证实:屏「遭遇节点」+「遭遇其一/其二/其三」+ 难度/奖励 +「选择」)。D-35 删 dispatch 的真实
        #     根因 = 旧 0c 用默认 lcs 0.5 把**备战屏「遭遇」标签**误匹配(LCS 2/4=0.5);正解是收紧 lcs 非 removal。
        #     现 lcs 0.9:备战「遭遇」(2/4=0.5<0.9)不误匹配;真「遭遇其一」4/4 命中(HandleEncounter 自身检测亦 0.9)。
        #     handler 2026-08-04 实测交互:点卡身选中 → 点选择确认(中间勿插空白点击会取消选中)。
        if self.round_by_ocr(screen, '遭遇其一', lcs_percent=0.9).is_success:
            self._snap('encounter')
            HandleEncounter(self.ctx).execute()
            return self.round_wait(wait=2)

        # 0d. 出战确认弹窗(未达上限)→ HandleDeployNotFull(勾本局不再提示 + 确认,详见 op)。
        # lcs_percent=0.8:防投资策略屏的策略描述「能量上限」与「未达上限」共享子序列「上限」(LCS 2/4=0.5
        # =默认阈值)误匹配 → 投资策略屏被本分支吞 → 反复触发 HandleDeployNotFull 卡死(2026-08-05 实跑)。
        # 真「未达上限」弹窗 4/4 命中不受影响。同 loop 其他分支(0a/0b/0e 均 0.7-0.9)的收紧惯例。
        if self.round_by_ocr(screen, '未达上限', lcs_percent=0.8).is_success:
            HandleDeployNotFull(self.ctx).execute()
            return self.round_wait(wait=3)

        # 0e. 选择类事件 overlay(投资策略/环境/补给,3 选 1 + 确认)→ **必须在备战(1)前检测**:
        #     这些 overlay 叠在备战上,「购买经验」会从 overlay 后透出(底部左下未遮)→ 若先检查备战
        #     会误派 BuyShopCards(overlay 遮商店→"找不到商店/收起"失败→死循环)。
        #     2026-08-04 实跑发现:投资策略屏被误派 BuyShopCards(购买经验透出命中),卡死。
        #     lcs_percent=0.8:「投资策略」与「投资环境」共享「投资」(2/4=0.5)→ 0.8 杀交叉误匹配。
        if self.round_by_ocr(screen, '投资策略', lcs_percent=0.8).is_success:
            self._snap('invest_strategy')
            HandleInvestStrategy(self.ctx).execute()
            return self.round_wait(wait=2)
        if self.round_by_ocr(screen, '投资环境', lcs_percent=0.8).is_success:
            self._snap('invest_env')
            HandleInvestEnv(self.ctx).execute()
            return self.round_wait(wait=2)
        if self.round_by_ocr(screen, '补给阶段', lcs_percent=0.8).is_success:
            self._snap('supply')
            RunSupplyNode(self.ctx).execute()  # 生命周期 owner:验证 overlay 消失才完成,超预算 bail
            return self.round_wait(wait=2)

        # 1. 备战阶段 → 单轮(买+deploy+出战)
        # 注:遭遇/选择伙伴 等 event overlay 已在 0b/0c 处理(确认选择/未达上限)。
        # 遭遇 round 是普通战斗(2026-08-04 视觉大模型 确认:无选项选择 UI,只有难度标签 + 出战),
        # 走正常 prep→出战→战斗(原 遭遇 handler "2选1" 过时,且 click 干扰 prep → stall,已移除)。
        if self.round_by_ocr(screen, '购买经验').is_success:
            BattlePrepCycle(self.ctx).execute()
            return self.round_wait(wait=2)  # 战斗中,下轮再判

        # 1b. 详情弹窗(点卡/点角色触发的:"可合成列表"祝福详情 / "角色详情"角色信息)→ ESC 关闭。
        #     lcs_percent=0.8:「角色详情」与 invest env 等屏的「角色」label 共享「角色」(2/4=0.5)→
        #     不收紧则凡有"角色"标签的屏(投资环境/...)都被 1b 吞 → ESC 卡死(2026-08-04 实跑,自己上轮加
        #     的 1b 修复引入此误匹配)。0.8 杀误匹配(真「角色详情」1.0 不受影响)。
        if (self.round_by_ocr(screen, '可合成列表', lcs_percent=0.8).is_success
                or self.round_by_ocr(screen, '角色详情', lcs_percent=0.8).is_success):
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=1.5)

        # 2. 点击空白加速 / 点击空白处继续 → 点空白
        if (self.round_by_ocr(screen, '点击空白加速').is_success
                or self.round_by_ocr(screen, '点击空白处继续').is_success):
            self.ctx.controller.click(CurrencyWarRunLoop.BLANK.center)
            return self.round_wait(wait=1.5)

        # 3. 挑战成功/结束 → P1.5 结算屏读 hp(on_round_end 观测回路)→ 继续挑战
        if self.round_by_ocr(screen, '继续挑战').is_success:
            self._record_round_outcome(screen)  # P1.5: 结算屏(挑战结束)→ read_round_outcome → on_round_end
            time.sleep(1.0)
            if self.round_by_ocr_and_click(self.screenshot(), '继续挑战', success_wait=2).is_success:
                return self.round_wait(wait=2)

        # 3b. 对局结束结算(前往结算→下一页→返回货币战争)→ 逐页点回大厅。结算"前进"按钮恒在底部中央。
        for btn in ('前往结算', '下一页', '返回货币战争'):
            # lcs_percent=0.8:「返回货币战争」与事件屏「返回备战界面」共享「返回+战」(3/6=0.5)→
            # 不收紧则凡有"返回备战界面"的事件屏(投资策略/环境/补给)都被 3b 吞 → 卡死(2026-08-04 发现)。
            if self.round_by_ocr(screen, btn, lcs_percent=0.8).is_success:
                self.ctx.controller.click(CurrencyWarRunLoop.SETTLEMENT_NEXT)
                return self.round_wait(wait=2)

        # 3c. 回到大厅(对局结束)→ loop 完成,避免在 lobby 无动作无限 retry。
        # 用「创业指南」(大厅左菜单独有、无特殊括号,OCR 稳)而非「开始「货币战争」」(括号 gt 不稳)
        if self.round_by_ocr(screen, '创业指南').is_success:
            # 局终:on_match_end(P1 桩 MatchOutcome,默认 no-op;真实 outcome 填充属 P1.5)+ 清场防跨局污染(D-34/§11.7)
            if self.ctx.cw_match is not None:
                self.ctx.cw_match.strategy.on_match_end(
                    self.ctx.cw_match.session, self._cw_config, MatchOutcome())
                self.ctx.cw_match = None
            return self.round_success('对局结束,回大厅')

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
