import random
import time
from pathlib import Path
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
    read_node_sequence,
    read_phase_round,
    read_round_outcome,
    reset_phase_round_cache,
)
from sr_od.application.currency_war.cw_state import GameState, MatchOutcome
from sr_od.application.currency_war.cw_strategy import CurrencyWarMatch
from sr_od.application.currency_war.cw_strategy_manager import StrategyManager
from sr_od.application.currency_war.operations.handlers.handle_armory_box import (
    HandleArmoryBoxDialog,
)
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
from sr_od.application.currency_war.operations.handlers.handle_wish_trial import (
    HandleWishTrial,
)
from sr_od.application.currency_war.operations.run_nodes.run_megastar_node import (
    RunMegastarNode,
)
from sr_od.application.currency_war.operations.run_nodes.run_supply_node import (
    RunSupplyNode,
)
from sr_od.application.currency_war.prep_director import PrepDirector
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
    # 临时随机态停机钩子(方案 D):连续 N 轮未识别画面 → stop_running 保画面待 AI 建档。建档后删本钩子。
    # 15 轮 ≈ 30s 纯卡(过渡帧 1-2 轮内被上面分支接走,不累计);远 < MAX_ITER,快速捕 novel 随机态。
    UNKNOWN_STOP_THRESHOLD: ClassVar[int] = 15
    # 点空白区(加速战斗 / 关叠层;避开中央内容)
    BLANK: ClassVar[Rect] = Rect(1450, 920, 1560, 980)
    # 结算"前进"按钮(前往结算/下一页/返回货币战争)恒在底部中央,文案随页变。
    # 2026-08-04 实测(失败结算屏 OCR):「下一页」x922y882w76h33、「返回货币战争」x885y882w149h31
    # → 中心均 ~(960,898)。原 (900,882) 偏左 22px 落在按钮左边缘外 → 点空 → 结算翻页卡死。
    SETTLEMENT_NEXT: ClassVar[Point] = Point(960, 898)

    def __init__(self, ctx: SrContext, max_rounds: int | None = None):
        SrOperation.__init__(self, ctx, op_name='货币战争-对局循环')
        self._iter: int = 0
        # 可控轮数(单/多轮验证 + 采样本):跑完 max_rounds 轮后,停在下一轮备战屏(analyze board/star)。
        # 轮锚点 = 分支3「挑战成功」结算(每打赢 1 轮 +1);停点 = 分支1 备战 gate(rounds_done≥max → 停)。
        # None = 现行跑到对局结束/超时(向后兼容)。app 从 config.max_rounds 透传;run_operation 可直传。
        self._max_rounds: int | None = max_rounds
        self._rounds_done: int = 0
        # B4(ADR-0170):跨局分配器实例(进程级单例——后验跨局累积;失败安全:任何异常静默禁用)
        self._allocator = _get_or_init_allocator(self.ctx)
        # 开一次 run 的遥测 run_id(本地 decisions.jsonl 采集用;outcomes/summary 写端已接 2026-08-16)。
        # difficulty:ctx.cw_selected_difficulty(StartCurrencyWarMatch 难度确认屏读存;此时**尚未**被
        # 下方取走 —— 取走在 cw_match new 之后,此处先读传 telemetry,review 半接线「difficulty 恒空」修复)。
        _diff_for_telemetry = self.ctx.cw_selected_difficulty or ''
        cw_telemetry.start_run(difficulty=_diff_for_telemetry)
        # 每局清空 plane/round last-known-good(防跨局复用上局值;task#24)
        reset_phase_round_cache()
        # SrOperation 还没 last_screenshot(截图由 node runner 进 @operation_node 时给)→ 不能 read_game_state;
        # on_match_start 在 loop() 首次截图后调(见下方 _iter==1 守卫)。跨步状态进 session.target_comp
        # (替代旧 BuyShopCards._target_comp class-attr hack,语义等价:每局新建已是现行为)。
        # 续跑支持(手动逐轮验证):cw_match 已存在(上轮 RunLoop 留下)→ 延用,不 new;否则 new(整局开始)。
        # 手动逐轮(max_rounds=1 反复 run_operation)靠此跨 run 延续 match state(target 稳定不每轮重选振荡)。
        # 停 app / 手停 / 重启 server 后 cw_match 清(None)→ 下次 run 重新 new(新局)。
        self._is_new_match: bool = self.ctx.cw_match is None
        self._cw_config: CurrencyWarConfig = CurrencyWarConfig(self.ctx.current_instance_idx)
        if self._is_new_match:
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
            # 本局职级(StartCurrencyWarMatch 难度确认屏读存 ctx.cw_selected_difficulty)→ session.selected_difficulty
            # → default_strategy 填 state → effective_hp_threshold D-32(3.5.1 接线)
            if self.ctx.cw_selected_difficulty:
                _session.selected_difficulty = self.ctx.cw_selected_difficulty
                self.ctx.cw_selected_difficulty = None  # 取走清空(防跨局复用)
            # 敌人难度数值(简报读存 ctx.cw_enemy_difficulty)→ session.enemy_difficulty(3.5.2 接线)
            if self.ctx.cw_enemy_difficulty is not None:
                _session.enemy_difficulty = self.ctx.cw_enemy_difficulty
                self.ctx.cw_enemy_difficulty = None  # 取走清空(防跨局复用)
            # 简报首领(3 位面 boss 名)→ copy 到 session(boss_fit 输入)
            if self.ctx.cw_briefing_bosses:
                _session.briefing_bosses = list(self.ctx.cw_briefing_bosses)
                self.ctx.cw_briefing_bosses = None  # 取走清空(防跨局复用)
        # else 续跑:延用 self.ctx.cw_match(上轮留下),仅刷新 _cw_config(用户可能改 max_rounds 等运行时配置)

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

    def _clear_bail_count(self, reason: str) -> None:
        """外环 handler 成功消化某 overlay 后清其 bail 计数(M11 误停机修复)。

        Director 对同一 overlay 的多次 bail 若都被外环**成功处理**(巨星节点每场触发一次,连胜连开),
        是合法流转而非 ping-pong —— 不清零会在第 3 次合法出现时误升级停机(M11 2-2 巨星实锤)。
        """
        _m = self.ctx.cw_match
        if _m is not None and getattr(_m.session, 'bail_reason_counts', None):
            _m.session.bail_reason_counts.pop(reason, None)

    def _record_round_outcome(self, screen) -> None:
        """P1.5 观测回路:结算屏(挑战成功 + 小队生命值)→ ``read_round_outcome`` → ``strategy.on_round_end``。

        喂本回合战后 hp_after 给 ``PerformanceTracker``(via on_round_end 默认实现 ``performance.record``),
        记掉血 trend(观测驱动,非预测)+ 写 ``session.last_hp``(达阈;给下回合 prep 真值 hp)。
        **仅从分支3(按钮-继续挑战 = 已确认 round-end 结算屏)调用**,故无内部结算屏 gate —— 原 gate 查
        「挑战结束」与实屏「挑战成功」不符 → 永不命中 → on_round_end 从不调 → performance/last_hp 全不喂
        (P1.5 观测回路 + prep-hp 真值机制双双静默死;2026-08-07 捕结算屏实锤「挑战成功」修复)。
        失败不阻塞对局(观测为辅)。node_type:结算屏含「首领」(如「1-9首领」)→ boss,否则普通战斗。
        plane/round 用 last-known(``read_phase_round`` 结算屏不显 plane/round)。
        """
        if self.ctx.cw_match is None:
            return
        try:
            _session = self.ctx.cw_match.session
            _plane, _round = read_phase_round(self.ctx, screen)   # last-known(结算屏不显 plane/round)
            _comp_tag = _session.target_comp.name if _session.target_comp else '?'
            _is_boss = self.round_by_ocr(screen, '首领').is_success   # 「1-9首领」= boss 结算。TODO(T#103) 待 area 化(需 boss 结算帧;词缀在简报不在结算屏,不误匹配)
            _obs = read_round_outcome(self.ctx, screen, plane=_plane, round_num=_round,
                                      comp_tag=_comp_tag, node_type='boss' if _is_boss else '普通战斗')
            self.ctx.cw_match.strategy.on_round_end(
                GameState(), _session, self._cw_config, _obs)
            # 遥测写端(review 半接线修复,2026-08-16):outcomes.jsonl 生产侧此前无写入方
            # (读端 join_decisions_outcomes 一直在等,两文件从未对上)。hp_after/hp_confidence/
            # node_type/comp_tag 已在 _obs;damage_dealt/killed 待 L1 结算屏建档(ADR-0166)。
            cw_telemetry.record_outcome(_obs)
            log.info('[cw-loop] on_round_end plane=%s round=%s hp_after=%s conf=%s comp=%s node=%s',
                     _plane, _round, _obs.hp_after, _obs.hp_confidence, _comp_tag, _obs.node_type)
        except Exception as e:  # noqa: BLE001  观测回路失败不阻塞对局
            log.warning('[cw-loop] on_round_end 失败(不阻塞): %s', e)

    def _probe_settlement_nodetype(self, screen) -> None:
        """[采集钩子·临时] 结算屏「挑战成功」下方 "X-Y <节点类型>" → log + 存裁图(标定节点类型词汇)。

        结算屏恒干净(无 shop 开/事件 overlay 干扰),比备�战节点行(仅 shop-closed 可见)可靠。
        逐轮采 → 配备�战节点行图标(位置 i ↔ 第 i+1 轮)得 位置→类型 映射,建图标模板。
        采够(位面1 全轮类型齐)→ 删本方法 + loop 分支3 的调用(CLAUDE.md 临时钩子用完即删)。
        """
        try:
            from one_dragon.base.geometry.rectangle import Rect
            from sr_od.application.currency_war.cw_obs_core import _ocr
            from sr_od.application.currency_war.cw_observe import cw_log, cw_shot
            # 「挑战成功」标识 y184-274;其下 "X-Y <type>" ~y270-310。OCR 宽带含上下文。
            blob = ''.join(r.data for r in _ocr(self.ctx, screen, Rect(700, 250, 1260, 330)))
            cw_log('settlement', step='nodetype', attn=True, raw=blob,
                   shot=cw_shot(screen[245:335, 690:1270], f'settlement_nt_{blob[:12]}'))
        except Exception as e:  # noqa: BLE001  采集钩子 best-effort
            log.info(f'[cw-loop] settlement nodetype probe skip: {e}')

    @operation_node(name='对局循环', is_start_node=True, node_max_retry_times=400)
    def loop(self) -> OperationRoundResult:
        self._iter += 1
        if self._iter > CurrencyWarRunLoop.MAX_ITER:
            return self.round_fail(status='对局循环超时')
        screen = self.last_screenshot

        # 尽力而为 read_game_state(默认实现不读);**不做 hp 覆盖** —— hp 覆盖是 update_target 的事(§11.6 M6)。
        if self._iter == 1 and self._is_new_match:
            self.ctx.cw_match.strategy.on_match_start(
                read_game_state(self.ctx, screen), self.ctx.cw_match.session, self._cw_config)

        # 0. 备战被锁(顶部"返回投资策略选择"按钮)→ 点去选策略(check#4 接手)。
        #    lcs_percent=0.9:防与「请选择投资策略」共享「选择投资策略」(6/8=0.75=默认阈值之上)
        #    误匹配 → 投资策略屏被本分支吞(点标题不动作)→ 死循环(2026-08-04 实跑发现,卡 plane1)。
        #    真「返回投资策略选择」按钮 OCR 1.0 不受影响。
        if self.round_by_ocr_and_click(screen, '返回投资策略选择', success_wait=2, lcs_percent=0.9).is_success:
            return self.round_wait(wait=2)

        # [停机钩子·临时] 未完整建档节点 + 待排查节点 → 停机给 AI 按 od-dev-screen-onboarding 建档/排查。
        # 建档/排查完删该 tuple 项。CLAUDE.md「两种钩子」方案 D。
        # - 祈愿:screen_info+handler 有但无完整 skill 建档(doc/fixture/id_mark 测缺)。巨星(盛会之星)已完整建档(2026-08-13)→ 移出 tuple,0b 接管。
        # - 投资环境已解除隔离(2026-08-15 M19 live:id_mark 已建 + HandleInvestEnv 经入口路径
        #   多局验证;本 session 修防御分支 AttributeError 后 0e 分支接管)→ 移出 tuple。
        # - 投资策略已完整重建档(2026-08-15 live:9 步 onboarding + 独立屏实锤 + 三态 fixture + id_mark
        #   测 4/4 + HandleInvestStrategy 点击模型 live 核对)→ 移出 tuple,0e 分支接管。
        # - 补给已完整重建档(2026-08-15 live:独立屏实锤(返回备战界面)+ 5 列交互验证(点列选中
        #   0/1→1/1、确认 1708,980 与 yml 一致)+ RunSupplyNode 模型 live 核对 + fixture 4 态 +
        #   id_mark 测既有 2 项)→ 移出 tuple,0e 分支接管。
        # ⚠️ 选择伙伴已完整建档(2026-08-13,组合 id_mark 购买经验+选择伙伴;备战含被盖前台区域→overlay 帧备战不 is_precise,无测试豁免)→ 移出 tuple,0a 接管。
        for _scr, _area, _tag in (
            ('货币战争-祈愿试炼', '标识-祈愿试炼', 'wish_trial'),
        ):
            if self.round_by_find_area(screen, _scr, _area, crop_first=False).is_success:
                self.save_screenshot(prefix=f'{_tag}_hook')
                Path(f'.debug/temp/currency_war/{_tag}_hook.flag').write_text(_tag, encoding='utf-8')
                log.info(f'[cw-hook] {_tag} 节点(未建档)→ 停机给 AI 建档 + 接决策')
                self.ctx.run_context.stop_running()
                return self.round_wait(status=f'{_tag} 停机建档')

        # 0a. 选择伙伴 overlay(必须在 0b 巨星前:选择伙伴也有"确认选择"但候选是 stage 立绘)
        #     → HandleSelectPartner(点 stage 立绘 + 确认选择,详见 op)。
        #     用 screen_info 标题 area(标识-选择伙伴)位置区分,非全屏 LCS:「选择伙伴」与「请选择投资策略」
        #     共享「选择」(2/4=0.5=默认阈值)会误匹配全屏 LCS → 投资策略屏被误派发(2026-08-04 snap 实测)。
        #     area 位置不同(选择伙伴 overlay 标题在 top-center id_mark rect)→ 不命中(同 0d/0e area 化理由)。
        if self.round_by_find_area(screen, '货币战争-选择伙伴', '标识-选择伙伴', crop_first=False).is_success:
            self._snap('choose_partner')  # 选人选项(立绘名)→ 后续建策略评估用
            _r = HandleSelectPartner(self.ctx).execute()
            if _r is not None and getattr(_r, 'success', False):
                self._clear_bail_count('事件overlay:partner')   # review M2:仅成功才清(失败保计数=ping-pong 安全网)
            return self.round_wait(wait=2)

        # 0b. 巨星强化(盛会之星选择 overlay)→ RunMegastarNode(选候选 + 确认,详见 op)。
        #     用 screen_info 标题 area(标识-盛会之星)位置区分。原用全屏「确认选择」(lcs 0.7 防「请选择投资策略」
        #     共享「选择」误匹配)—— 但「确认选择」partner overlay 也有(靠 0a 先捕 partner 区分);改用 megastar
        #     独有标题「盛会之星」更直接(独有标题位置区分,无需依赖分支先后)。
        if self.round_by_find_area(screen, '货币战争-盛会之星', '标识-盛会之星', crop_first=False).is_success:
            self._snap('megastar')  # 巨星候选(立绘名)→ 后续建策略评估用
            _r = RunMegastarNode(self.ctx).execute()  # 生命周期 owner:验证 overlay 消失,超预算 bail
            if _r is not None and getattr(_r, 'success', False):
                self._clear_bail_count('事件overlay:megastar')   # 合法 bail 清计数(live M11 误停机;M2:仅成功才清)
            return self.round_wait(wait=2)

        # 0c. 遭遇节点(难度二选一 + 选择)→ HandleEncounter(点卡选中 + 选择确认)。
        #     live 2026-08-15:改 id_mark area 检测(标识-遭遇节点,yml 已建)—— 旧全屏 OCR「遭遇其一」
        #     lcs 0.9 在卡标题 OCR 截断帧(「遭遇其」3/4=0.75)miss → 整屏落未知画面停机。
        #     handler 交互(2026-08-04 实测):点卡身选中 → 点选择确认(中间勿插空白点击会取消选中)。
        if self.round_by_find_area(screen, '货币战争-遭遇节点', '标识-遭遇节点', crop_first=False).is_success:
            self._snap('encounter')
            HandleEncounter(self.ctx).execute()
            return self.round_wait(wait=2)

        # 0d. 出战确认弹窗(未达上限)→ HandleDeployNotFull(勾本局不再提示 + 确认,详见 op)。
        # 用 screen_info id_mark area(标识-未达上限警告)位置区分,非全屏 LCS:投资策略屏的策略描述「能量上限」
        # 与「未达上限」共享子序列「上限」(LCS 2/4=0.5)会误匹配全屏 LCS → 投资策略屏被本分支吞 → 反复触发
        # HandleDeployNotFull 卡死(2026-08-05 实跑)。id_mark area 位置不同 → 不命中(同 0e invest area 化理由)。
        if self.round_by_find_area(screen, '货币战争-未达上限警告', '标识-未达上限警告', crop_first=False).is_success:
            HandleDeployNotFull(self.ctx).execute()
            return self.round_wait(wait=3)

        # 0e. 选择类事件 overlay(投资策略/环境/补给,3 选 1 + 确认)→ **必须在备战(1)前检测**:
        #     这些 overlay 叠在备战上,「购买经验」会从 overlay 后透出(底部左下未遮)→ 若先检查备战
        #     会误派 BuyShopCards(overlay 遮商店→"找不到商店/收起"失败→死循环)。
        #     2026-08-04 实跑发现:投资策略屏被误派 BuyShopCards(购买经验透出命中),卡死。
        #     lcs_percent=0.8:「投资策略」与「投资环境」共享「投资」(2/4=0.5)→ 0.8 杀交叉误匹配。
        # 用 screen_info id_mark area 检测(固定位置全等),非全屏 LCS —— 失败结算屏(对局未完成)含
        # 「投资策略/投资环境」(对局信息)会误匹配全屏 LCS(2026-08-06 实跑:loop 卡失败结算,
        # HandleInvestStrategy 误派点「标准博弈」死循环)。id_mark area 位置不同(失败结算在对局信息区,
        # 不在真屏 id_mark pc_rect)→ 不命中,落到 3b「下一页」回大厅。
        if self.round_by_find_area(screen, '货币战争-投资策略', '标识-请选择投资策略', crop_first=False).is_success:
            self._snap('invest_strategy')
            HandleInvestStrategy(self.ctx).execute()
            return self.round_wait(wait=2)
        if self.round_by_find_area(screen, '货币战争-投资环境', '标识-投资环境', crop_first=False).is_success:
            self._snap('invest_env')
            HandleInvestEnv(self.ctx).execute()
            return self.round_wait(wait=2)
        if self.round_by_find_area(screen, '货币战争-补给', '标识-补给阶段', crop_first=False).is_success:
            self._snap('supply')
            RunSupplyNode(self.ctx).execute()  # 生命周期 owner:验证 overlay 消失才完成,超预算 bail
            return self.round_wait(wait=2)

        # 0f. 节点武装箱弹窗(「武装突入」类节点,2026-08-15 M19 首见停机建档)→
        #     HandleArmoryBoxDialog(点开箱 → 四选一 → 选卡点卡 → 验关;与备战补给箱
        #     同下游不同入口,选卡公用 pick_box_card)。
        if self.round_by_find_area(screen, '货币战争-武装箱弹窗', '标识-简易武装箱', crop_first=False).is_success:
            self._snap('armory_box')
            HandleArmoryBoxDialog(self.ctx).execute()
            return self.round_wait(wait=2)

        # 0e2. 商店刷新概率表弹窗 → 点 × 关闭(live 2026-08-14 1-2 实锤补:点球误触开后无分支消化,
        #       遮出战按钮 → Director bail → 外环也认不出 → 停机)。× 位置 VLM 定位 (1501,263);
        #       mouse_move 必带(bug#1:恢复原语同坐标点击曾落空)。
        if self.round_by_find_area(screen, '货币战争-商店刷新概率表', '标识-刷新概率表',
                                   crop_first=False).is_success:
            self.ctx.controller.mouse_move(Point(1501, 263))
            self.ctx.controller.click(Point(1501, 263))
            log.info('[cw-loop] 概率表弹窗 → 点× 关闭')
            return self.round_wait(wait=1.5)
        # 0e3. 道具详情弹窗(聘用书类;live 2026-08-15 M13 首遇):获得 3费聘用书 等道具后自动弹介绍 modal,
        #       关键词与消耗品(消耗品+拖动到)不同 → 落未知画面停机。点 ×(1862,65 VLM 定位)关;道具使用属 P4 工具域。
        if self.round_by_ocr(screen, '聘用书', lcs_percent=0.8).is_success:
            self.ctx.controller.mouse_move(Point(1862, 65))
            self.ctx.controller.click(Point(1862, 65))
            log.info('[cw-loop] 道具详情弹窗(聘用书)→ 点× 关闭')
            return self.round_wait(wait=1.5)
        # 0f. 消耗品详情浮层 → ESC 关。获消耗品奖励(投资策略「星星相印」给【员工投影仪】等)后游戏自动弹
        #     介绍 modal,遮挡备战/投资策略屏 → 上面所有分支都不命中 → round_retry 死循环(2026-08-06 实跑:
        #     plane2 supply 后弹「员工投影仪」modal,flat retry ~19min 失败;**非策略死,UI 弹窗卡死**)。
        #     签名「消耗品」(类型 label) AND 「拖动到」(拖动使用说明 —— 只出现在消耗品详情 modal,备战底部
        #     消耗品栏无)→ 双条件精确,不误匹配备战。装备类详情 modal(无「拖动到」)是长尾,观察到再补。
        if (self.round_by_ocr(screen, '消耗品', lcs_percent=0.9).is_success
                and self.round_by_ocr(screen, '拖动到', lcs_percent=0.9).is_success):
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=1.5)

        # 0g. 投资策略「阿哈大悦」装备选择 overlay(为阿哈选1件简易装备)→ 点装备自动关。
        #     阿哈投资策略在某节点弹此 overlay(选1件简易装备给阿哈)。bot 不选 → overlay 持 → 卡备战
        #     (2026-08-07 实跑:plane1 1-3 卡此 overlay 666s)。点第1装备(幸运星位 626,250;策略可后续
        #     按 key_equips 选,先关 overlay 推进)→ 实测自动关 overlay 回备战。
        if self.round_by_find_area(screen, '货币战争-备战', '标识-简易装备', crop_first=False).is_success:
            self.ctx.controller.click(Point(626, 250))
            return self.round_wait(wait=1.5)

        # 0h. 祈愿试炼 overlay(节点级 quest 选择:选1试炼 → 完 objective 得奖励)→ HandleWishTrial
        #     (点第1卡 + 确认选择)。叠备战上挡备战分支 → 必须在备战(1)前检测。2026-08-08 实跑发现:
        #     bot 卡此 overlay 68min(购买经验透出命中 → BattlePrepCycle 误派 → shop 被遮失败 → 死循环)。
        #     ESC 不关;点卡身选中(金色边框)→ 确认选择 → 关回备战。详见 op。
        if self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼', crop_first=False).is_success:
            self._snap('wish_trial')
            HandleWishTrial(self.ctx).execute()
            return self.round_wait(wait=2)

        # 0i. 星徽秘典道具详情弹窗(挡全屏 → 15 streak 停机钩子,M33 实锤)→ 点右上 X 关回原画面。
        #     「星徽秘典」= 使用类道具(开四选一星徽);详情弹窗疑似点击道具误开。只关不选
        #     (使用该道具 = 四选一星徽决策,价值不明先保守关;后续要消费再建 handler)。
        if self.round_by_find_area(screen, '货币战争-星徽秘典弹窗', '标识-星徽秘典', crop_first=False).is_success:
            self.ctx.controller.click(Point(1867, 64))
            return self.round_wait(wait=1.5)

        # 1. 备战阶段 → PrepDirector 决策环(P1 挂载切换,doc 15/ADR-0123;原 BattlePrepCycle
        #   固定序列退役为 P3 前可切回的回退路径)。注:遭遇/选择伙伴 等 event overlay 已在
        #   0b/0c 处理(确认选择/未达上限);遭遇 round 是普通战斗(2026-08-04 视觉大模型确认)。
        if self.round_by_find_area(screen, '货币战争-备战', '备战标识-购买经验').is_success:
            # 可控轮数:已跑完 max_rounds 轮 → 停备战屏(可 analyze board/star + star 钩子采样本),不跑备战单轮。
            if self._max_rounds is not None and self._rounds_done >= self._max_rounds:
                log.info('[cw-loop] max_rounds=%s 已跑 %s 轮 → 停备战屏(单/多轮验证)',
                         self._max_rounds, self._rounds_done)
                return self.round_success(
                    f'已跑 {self._rounds_done} 轮停备战(达 max_rounds={self._max_rounds})')
            # 补给节点(nodeseq 当前节点类型=supply):出战不推进(无出战打怪,确认补给即完成节点进下回合,
            # live 确认 2026-08-13)→ 点「返回补给阶段」进补给屏,下轮 Loop 0e 分支 RunSupplyNode 选+确认。
            # ⚠️ 用 nodeseq 节点类型判,非「返回补给阶段」按钮 —— 该按钮 battle 节点也在(可 revisit),不可靠
            # (2026-08-13 实跑:1-6 battle 节点出战成功 + 也有该按钮)。nodeseq 读失败(非 clean 帧)→ 不 divert
            # (默认 BattlePrepCycle,保险不误判 battle 为 supply)。
            _cur_slot = next((s for s in (read_node_sequence(self.ctx, screen) or [])
                              if s.state == 'current'), None)
            if _cur_slot is not None and _cur_slot.node_type == 'supply':
                self.round_by_find_and_click_area(screen, '货币战争-备战', '按钮-返回补给阶段', success_wait=2)
                log.info('[cw-loop] 补给节点(nodeseq current=supply)→ 点返回补给阶段 进补给屏(下轮 RunSupplyNode)')
                return self.round_wait(wait=2)
            PrepDirector(self.ctx).execute()
            return self.round_wait(wait=2)  # 战斗中,下轮再判

        # 1b. 详情弹窗(点卡/点角色触发的:"可合成列表"祝福详情 / "角色详情"角色信息)→ ESC 关闭。
        #     lcs_percent=0.8:「角色详情」与 invest env 等屏的「角色」label 共享「角色」(2/4=0.5)→
        #     不收紧则凡有"角色"标签的屏(投资环境/...)都被 1b 吞 → ESC 卡死(2026-08-04 实跑,自己上轮加
        #     的 1b 修复引入此误匹配)。0.8 杀误匹配(真「角色详情」1.0 不受影响)。
        if (self.round_by_ocr(screen, '可合成列表', lcs_percent=0.8).is_success
                or self.round_by_ocr(screen, '角色详情', lcs_percent=0.8).is_success):
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=1.5)

        # 1f. **失败结算页**(M41 实锤 2026-08-16,历史首达 P3 后 HP 归零):「挑战结束」大标 +
        #     「X-Y 战斗」+ 点击空白加速(无继续挑战按钮)。此前未建档 → loop 未识别返回 None →
        #     app 层 AttributeError。建档:货币战争-结算-失败(id_mark=标识-挑战结束,lcs 0.9)。
        #     ⚠️ 双保险(M43 二次咬人教训):近形文案「挑战结束/失败/成功」两两 LCS=0.5,lcs 单靠
        #     不住(yml 旧值/漂移都会复活)——本分支加结构判据「无继续挑战按钮」(真失败结算页没有,
        #     挑战成功屏恒有)→ 成功屏永不会被 1f 吞(其归 3 分支处理)。
        #     ⚠️ M44 三次咬人(2026-08-16 20:34):P2-1 轮败屏 = 「挑战结束 + 前往结算」(直接带局终
        #     前进按钮,无「点击空白加速」)——1f 点空白无效循环。**分支内先查 3b 前进按钮词**,有则
        #     点 SETTLEMENT_NEXT(与 3b 同语义:结算翻页回大厅收局),无才点空白加速。
        if (self.round_by_find_area(screen, '货币战争-结算-失败', '标识-挑战结束', crop_first=False).is_success
                and not self.round_by_find_area(
                    screen, '货币战争-结算', '按钮-继续挑战', crop_first=False).is_success):
            for _btn in ('前往结算', '下一页', '下一步', '返回货币战争'):
                if self.round_by_ocr(screen, _btn, lcs_percent=0.8).is_success:
                    self.ctx.controller.click(CurrencyWarRunLoop.SETTLEMENT_NEXT)
                    self.park_cursor(after_wait=0.1)
                    return self.round_wait(wait=2)
            self.ctx.controller.click(CurrencyWarRunLoop.BLANK.center)
            self.park_cursor(after_wait=0.1)
            return self.round_wait(wait=2)

        # 1g. [停机钩子·临时] 中断挑战 dialog(bug#2:ESC 误按弹「是否中断挑战」,历史 3 次实锤;
        #     r2 review A-1 缺口)。无实拍图不能建档 → hook 捕获自然出现:检测「中断挑战」或
        #     「是否中断」→ 存证 + 停机给 AI 建档(优先点取消保对局)。建档后删本钩子。
        #     lcs 0.9(4字词要求完整子序列,防「中断」类误匹配)。
        if (self.round_by_ocr(screen, '中断挑战', lcs_percent=0.9).is_success
                or self.round_by_ocr(screen, '是否中断', lcs_percent=0.9).is_success):
            _shot = self.save_screenshot(prefix='cw_interrupt_dialog')
            _sentinel = (Path(__file__).resolve().parents[5] / '.debug' / 'temp'
                         / 'currency_war' / 'interrupt_dialog.flag')
            _sentinel.parent.mkdir(parents=True, exist_ok=True)
            _sentinel.write_text(f'iter={self._iter} shot={_shot}', encoding='utf-8')
            log.info('[cw-hook] 中断挑战 dialog 出现 → 停机存证待建档 shot=%s', _shot)
            self.ctx.run_context.stop_running()
            return self.round_fail(status='中断挑战 dialog 停机待建档')

        # 2. 点击空白加速 / 点击空白处继续 → 点空白
        if (self.round_by_ocr(screen, '点击空白加速').is_success
                or self.round_by_ocr(screen, '点击空白处继续').is_success):
            self.ctx.controller.click(CurrencyWarRunLoop.BLANK.center)
            return self.round_wait(wait=1.5)

        # 3. 挑战成功/结束 → P1.5 结算屏读 hp(on_round_end 观测回路)→ 继续挑战
        if self.round_by_find_area(screen, '货币战争-结算', '按钮-继续挑战').is_success:
            self._record_round_outcome(screen)  # P1.5: 结算屏(挑战成功)→ read_round_outcome → on_round_end
            self._probe_settlement_nodetype(screen)  # [采集钩子·临时] 结算 "X-Y <type>" 标定,采完删
            # C-1(r2 review,2026-08-16):计数锚点 = 新结算帧(非命中帧)——结算屏点击不生效循环 k 轮时,
            # 旧行为每轮 +1 → rounds_done 虚增 → max_rounds=N>1 时提前停备战。改:同屏指纹(结果文本行)
            # 不重复计数;仅进入新结算帧(上一轮不是结算/或结算内容变了)才 +1。轮败(1f)不计数(轮锚点=
            # 挑战成功结算;失败局 0 计数是设计内)。
            _fp = tuple(sorted((r.data, r.y) for r in self.ctx.ocr_service.get_ocr_result_list(
                image=screen, rect=None, crop_first=False)))
            if getattr(self, '_last_settle_fp', None) != _fp:
                self._rounds_done += 1
                self._last_settle_fp = _fp
            time.sleep(1.0)
            if self.round_by_find_and_click_area(self.screenshot(), '货币战争-结算', '按钮-继续挑战', success_wait=2).is_success:
                # 停留计数(M39 实证 2026-08-16,3-1 普通轮结算):「继续挑战」OCR/模板全识别、
                # 普通 click **不响应**(40min 空转同帧),长按 0.5s @ 底部中央才推进(手动实锤;
                # 推进后进 P3 投资策略 = 3-1 只是普通关,非终局)。归因未定(焦点/热区偏移/交互
                # 需长按),**机制**:结算屏停留 ≥3 轮 = 点击未生效 → 长按兜底推进 + 留证观察。
                self._settle_stay = getattr(self, '_settle_stay', 0) + 1
                if self._settle_stay >= 3:
                    log.info('[cw-loop] 结算屏停留 %s 轮(点击未生效)→ 长按 (960,898) 兜底推进',
                             self._settle_stay)
                    self.ctx.controller.click(CurrencyWarRunLoop.SETTLEMENT_NEXT, press_time=0.5)
                    self.park_cursor(after_wait=0.1)
                    self._settle_stay = 0
                return self.round_wait(wait=2)
            return self.round_wait(wait=2)
        self._settle_stay = 0   # 离开结算屏重置

        # 3b. 对局结束结算(前往结算→下一页→返回货币战争)→ 逐页点回大厅。结算"前进"按钮恒在底部中央。
        # 「下一步」= 挑战失败终局结算屏(M41 战败形态,M42 实锤):同底部中央位,SETTLEMENT_NEXT 点进。
        for btn in ('前往结算', '下一页', '下一步', '返回货币战争'):
            # lcs_percent=0.8:「返回货币战争」与事件屏「返回备战界面」共享「返回+战」(3/6=0.5)→
            # 不收紧则凡有"返回备战界面"的事件屏(投资策略/环境/补给)都被 3b 吞 → 卡死(2026-08-04 发现)。
            if self.round_by_ocr(screen, btn, lcs_percent=0.8).is_success:
                self.ctx.controller.click(CurrencyWarRunLoop.SETTLEMENT_NEXT)
                # 光标 parking(审计 R6):点击点正落在「下一页」文本框内,多页结算每页按钮同带
                # → 光标压当页按钮文字 → OCR miss → unknown streak 停机。点完 park。
                self.park_cursor(after_wait=0.1)
                return self.round_wait(wait=2)

        # 3c. 回到大厅(对局结束)→ loop 完成,避免在 lobby 无动作无限 retry。
        # 用「创业指南」(大厅左菜单独有、无特殊括号,OCR 稳)而非「开始「货币战争」」(括号 gt 不稳)
        if self.round_by_find_area(screen, '货币战争-大厅', '标识-创业指南').is_success:
            if self.ctx.cw_match is not None:
                # B4(ADR-0170 telemetry 接线):终局真实数据灌 MatchOutcome(原桩全默认)——
                # won=回大厅即本局结束;plane/round/hp 取 session.last_state(每回合框架刷新的
                # 最后快照;⚠️ CurrencyWarMatch 无 state 字段——review 子代理 P0 实锤,勿写
                # cw_match.state)。喂 strategy.on_match_end + 跨局分配器(0170,分级奖励)。
                _st = self.ctx.cw_match.session.last_state
                _outcome = MatchOutcome(
                    won=(_st is not None and _st.plane >= 3),
                    final_plane=_st.plane if _st is not None else 1,
                    final_round=_st.round_num if _st is not None else 1,
                    final_hp=_st.hp if _st is not None else 0,
                )
                self.ctx.cw_match.strategy.on_match_end(
                    self.ctx.cw_match.session, self._cw_config, _outcome)
                self._allocator_update(_outcome)
                # 遥测写端(review 半接线修复,2026-08-16):runs.jsonl 生产侧此前无写入方。
                # result:plane>=3 = win(通关),否则 loss(死在 P3 内);gold 轨迹由 recorder
                # 内存累积自动带。B4 的 outcome 真值同源。
                cw_telemetry.record_run_summary(
                    result='win' if _outcome.won else 'loss',
                    plane_reached=_outcome.final_plane,
                    rounds_survived=_outcome.final_round,
                    final_hp=_outcome.final_hp,
                    notes='auto')
                self.ctx.cw_match = None
            return self.round_success('对局结束,回大厅')

        # 5. 前进按钮(简报等)
        if self.round_by_ocr_and_click(screen, '下一步', success_wait=2).is_success:
            return self.round_wait(wait=1.5)

        # 6. 战斗/过场屏(总伤害/数据统计 在,无其他动作;OCR 常漏「点击空白加速」)→ 点空白加速/推进。
        # 只用战斗独有关键词;不用「羁绊」(大厅"羁绊链路"会误匹配)
        if (self.round_by_ocr(screen, '总伤害').is_success   # TODO(T#103) 待建 area(此结算帧未见「总伤害」label)
                or self.round_by_find_area(screen, '货币战争-结算', '标识-数据统计').is_success):
            self.ctx.controller.click(CurrencyWarRunLoop.BLANK.center)
            return self.round_wait(wait=1.5)
        # 兜底(M43-resume 修复 2026-08-16):所有分支不命中 → 停机钩子(streak 累计/保画面停机)。
        # 此前钩子代码被 _allocator_update 插错位置卷进方法体(从未执行)→ loop 隐式返 None。
        return self._handle_unknown_fallback()

    # ===== B4(ADR-0170):终局喂分配器(影子期:只记后验不改选臂;分级奖励+adherence) =====
    def _allocator_update(self, outcome: MatchOutcome) -> None:
        """终局 update:臂 = 终局 target_comp 名(adherence 近似 1;开局臂双列待 v1)。"""
        if self._allocator is None or self.ctx.cw_match is None:
            return
        try:
            arm_obj = getattr(self.ctx.cw_match.session, 'target_comp', None)
            arm_id = getattr(arm_obj, 'name', '') if arm_obj is not None else ''
            if not arm_id or arm_id not in self._allocator.arms:
                return
            reward = self._allocator.reward_graded(
                outcome.won, outcome.final_plane, rounds=outcome.final_round)
            self._allocator.update(arm_id, reward, adherence=1.0)
            log.info('[cw-alloc] 终局 update: arm=%s won=%s plane=%s reward=%.2f → mean=%.3f',
                     arm_id, outcome.won, outcome.final_plane, reward,
                     self._allocator.arms[arm_id].mean)
        except Exception as e:   # noqa: BLE001  影子期失败安全
            log.info(f'[cw-alloc] update 失败(跳过): {e}')

    def _handle_unknown_fallback(self) -> OperationRoundResult:
        """临时随机态停机钩子(方案 D,M43-resume 修复 2026-08-16):loop 尾部兜底 ——
        所有分支不命中(战斗特效帧 OCR 乱码/新未建档画面)→ streak 累计 → 保画面停机待建档。
        曾被 _allocator_update 插入位置错误卷进方法体(从未执行)→ loop 隐式返 None(19:59 实锤)。
        """
        if getattr(self, '_unknown_last_iter', -1) == self._iter - 1:
            self._unknown_streak = getattr(self, '_unknown_streak', 0) + 1
        else:
            self._unknown_streak = 1
        self._unknown_last_iter = self._iter
        if self._unknown_streak >= CurrencyWarRunLoop.UNKNOWN_STOP_THRESHOLD:
            try:
                _shot = self.save_screenshot(prefix='cw_unknown')
                _sentinel = (Path(__file__).resolve().parents[5] / '.debug' / 'temp'
                             / 'currency_war' / 'unknown_state.flag')
                _sentinel.parent.mkdir(parents=True, exist_ok=True)
                _sentinel.write_text(
                    f'iter={self._iter} streak={self._unknown_streak} shot={_shot}', encoding='utf-8')
                log.info('[cw!] [loop] 持久未识别画面 → stop_running 待 AI 建档 shot=%s streak=%s',
                         _shot, self._unknown_streak)
            except Exception as e:  # noqa: BLE001  钩子失败不阻塞
                log.warning('[cw-loop] unknown stop 钩子失败(不阻塞): %s', e)
            self.ctx.run_context.stop_running()
            return self.round_fail(status='持久未识别画面,停机待建档')
        return self.round_retry(wait=2)


# ===== B4(ADR-0170):跨局分配器进程级单例 + 终局 update =====
_ALLOCATOR = None          # 进程级(后验跨局累积;server 不重启跨局延续)


def _get_or_init_allocator(ctx: SrContext):
    """惰性建分配器(失败安全:建不出来 → None,update no-op)。plaza 份额先验。"""
    global _ALLOCATOR
    if _ALLOCATOR is not None:
        return _ALLOCATOR
    try:
        from sr_od.application.currency_war.cw_plaza_comps import PLAZA_CARRY_CLUSTERS
        from sr_od.application.currency_war.cw_run_allocator import ThompsonAllocator
        total = sum(max(c.n_posts, 0) for c in PLAZA_CARRY_CLUSTERS) or 1
        share = {c.carry: c.n_posts / total for c in PLAZA_CARRY_CLUSTERS if c.n_posts >= 15}
        _ALLOCATOR = ThompsonAllocator.from_plaza(share)
    except Exception as e:   # noqa: BLE001  影子期失败安全
        log.info(f'[cw-alloc] 分配器初始化失败(禁用): {e}')
        _ALLOCATOR = None
    return _ALLOCATOR
