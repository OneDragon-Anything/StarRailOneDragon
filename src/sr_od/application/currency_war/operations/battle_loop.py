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
from sr_od.application.currency_war.cw_performance import HP_CONFIDENCE_THRESHOLD
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
    # r119 停滞 watchdog 参数:每 5 iter 采一次指纹(≈5-10s),连续 6 次相同
    # (≈1-2min 同屏)→ 哨兵。战斗态(指纹含「战斗/胜利/挑战」关键词)豁免。
    STALL_SNAPSHOT_EVERY: ClassVar[int] = 5
    STALL_N: ClassVar[int] = 6
    # 点空白区(加速战斗 / 关叠层;避开中央内容)
    BLANK: ClassVar[Rect] = Rect(1450, 920, 1560, 980)
    # 结算"前进"按钮(前往结算/下一页/返回货币战争)恒在底部中央,文案随页变。
    # 2026-08-04 实测(失败结算屏 OCR):「下一页」x922y882w76h33、「返回货币战争」x885y882w149h31
    # → 中心均 ~(960,898)。原 (900,882) 偏左 22px 落在按钮左边缘外 → 点空 → 结算翻页卡死。
    SETTLEMENT_NEXT: ClassVar[Point] = Point(960, 898)
    # 子态稳定门(2026-08-18 用户定调「连续3秒子态稳定再分发」):节点结算后游戏**先渲染备战、
    # 再按下一节点类型弹 overlay**(普通战斗节点=商店面板/奖励=奖励面板/投资类=对应选择屏;
    # 策略→环境可链式)。半开帧上分发 = 在未定型画面上行动——两类实锤:M47 ClickSpheres 误点
    # (22:34:46/50)、bench_unidentified 钩子在 overlay 帧误采(11:17 投资策略帧)。
    # 门语义:备战分支**连续**命中 ≥ 本值才派 PrepDirector;期间只观察(overlay 弹出后 0e 系
    # 分支先于本分支接管,处理完回备战时门重新计时——链式 overlay 逐个消化)。
    # ⚖️ ADR-0213 批次4 归属声明(r336):本门是「分支分发层」的
    # 排程性迁移防御(overlay-after-prep),与 PrepPhase 环内
    # gate(帧内动画防御)正交——**不迁入 gate 体系**(review
    # 双方实证:双帧替代丢时间维度会重开 M47);结算屏/事件
    # overlay 帧的识别走各 handler 自带锚+置信度门,同属
    # 本层职责(三道防线:锚存在/conf≥0.9/同屏指纹去重)。
    PREP_SETTLE_S: ClassVar[float] = 3.0

    def __init__(self, ctx: SrContext, max_rounds: int | None = None):
        SrOperation.__init__(self, ctx, op_name='货币战争-对局循环')
        self._iter: int = 0
        # r363(审计 P1-6):runs summary 兜底——中止/卡死/停机局从不走
        # 3c 回大厅 → record_run_summary 永不调(近 6 局无 runs 行实锤)。
        # 机制:正常终局写 summary 后置 _summary_written;loop 实例被
        # 回收时未写 → 补一条 abandoned(gold 轨迹由 recorder 内存带)。
        self._summary_written: bool = False
        # 可控轮数(单/多轮验证 + 采样本):跑完 max_rounds 轮后,停在下一轮备战屏(analyze board/star)。
        # 轮锚点 = 分支3「挑战成功」结算(每打赢 1 轮 +1);停点 = 分支1 备战 gate(rounds_done≥max → 停)。
        # None = 现行跑到对局结束/超时(向后兼容)。app 从 config.max_rounds 透传;run_operation 可直传。
        self._max_rounds: int | None = max_rounds
        self._rounds_done: int = 0
        # 子态稳定门状态(见 PREP_SETTLE_S 注释):_frame_is_prep=本帧是否走备战分支
        # (迭代开头 shift 到 _prev_frame_prep 后清零,备战分支命中再置);_prep_entry_ts=
        # 本次备战相位的首命中时刻(连续性断开/新相位 → 重置重计)。
        self._frame_is_prep: bool = False
        self._prev_frame_prep: bool = False
        self._prep_entry_ts: float | None = None
        # r119 停滞 watchdog 状态:画面指纹采样(OCR 关键词 frozenset 哈希)。
        # 每 STALL_SNAPSHOT_EVERY iter 采样一次;连续 STALL_N 次相同 → 哨兵。
        self._stall_last_fp: int | None = None
        self._stall_count: int = 0
        self._stall_flag_written: bool = False
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
            # r339b:板深快照注册移**match new 后**(review 预核 A:
            # 原在 start_run 处注册时 cw_match 恒 None——新局
            # 首战快照死)。续跑局在 else 支支注册。
            cw_telemetry.set_ctx_match(self.ctx.cw_match)
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
        else:
            # 续跑局:同样注册(r339b——原注册点对续跑局也晚于
            # start_run,统一在两支各自 new/延用后注册)
            cw_telemetry.set_ctx_match(self.ctx.cw_match)
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

    def _stall_watch_tick(self, screen) -> None:
        """r119 停滞 watchdog:同屏指纹连续相同 → 哨兵(不停机,日志+flag 双通道)。

        指纹 = OCR 关键词 frozenset 哈希(5 iter 采一次,~5-10s 粒度)。战斗/
        结算/等待态关键词豁免(它们本来就该静止)。触发 = 写 stall_watch.flag
        (含处理指引)+ [cw!] 日志一次;画面变化后自动清计数(flag 留给 AI 巡检
        后删)。设计:采集哨兵非停机(bot 可能只是慢,停机代价>等待代价;
        od-dev-stop-hooks 采集/停机分流判据)。
        """
        if self._iter % CurrencyWarRunLoop.STALL_SNAPSHOT_EVERY != 0:
            return
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        texts = frozenset(k for k, mrl in ocr_map.items() if mrl.max is not None)
        # 战斗/结算/等待态豁免(合法静止)
        _exempt = any(w in t for t in texts for w in
                      ('战斗', '胜利', '挑战', '结算', '准备', '倒计时'))
        if _exempt:
            self._stall_count = 0
            self._stall_last_fp = None
            return
        fp = hash(texts)
        if fp == self._stall_last_fp:
            self._stall_count += 1
        else:
            self._stall_count = 0
            self._stall_last_fp = fp
            self._stall_flag_written = False   # 画面动了 → 哨兵可再次触发(新一轮停滞)
        if self._stall_count >= CurrencyWarRunLoop.STALL_N and not self._stall_flag_written:
            _shot = self.save_screenshot(prefix='cw_stall')
            _sentinel = (Path(__file__).resolve().parents[5] / '.debug' / 'temp'
                         / 'currency_war' / 'stall_watch.flag')
            _sentinel.parent.mkdir(parents=True, exist_ok=True)
            _sentinel.write_text(
                f'停滞 watchdog:iter={self._iter} 同屏指纹连续 {self._stall_count} 次'
                f'(≈{self._stall_count * CurrencyWarRunLoop.STALL_SNAPSHOT_EVERY} iter)\n'
                f'OCR 关键词: {sorted(texts)[:12]}\n'
                f'处理流程:\n'
                f'1. 看关键词/截图:疑似事件 overlay(未建档 handler)→ 按\n'
                f'   od-dev-screen-onboarding 建档 + battle_loop 0x 分支加 handler;\n'
                f'2. 疑似操作循环失败(点了没反应)→ od-dev-debug-automation 定位\n'
                f'   (grep 该时刻日志,看哪个 node 在 retry);\n'
                f'3. 处理完删本 flag。bot 未停机(可能只是慢),处理完可继续跑。\n'
                f'shot={_shot}', encoding='utf-8')
            log.warning('[cw!][watch] 停滞哨兵:同屏 %s 次(≈%s iter)关键词=%s '
                        'shot=%s —— 疑似未处理 overlay/操作循环,详见 stall_watch.flag',
                        self._stall_count,
                        self._stall_count * CurrencyWarRunLoop.STALL_SNAPSHOT_EVERY,
                        sorted(texts)[:8], _shot)
            self._stall_flag_written = True   # 只写一次,画面变化后可重置重写

    def _clear_bail_count(self, reason: str) -> None:
        """外环 handler 成功消化某 overlay 后清其 bail 计数(M11 误停机修复)。

        Director 对同一 overlay 的多次 bail 若都被外环**成功处理**(巨星节点每场触发一次,连胜连开),
        是合法流转而非 ping-pong —— 不清零会在第 3 次合法出现时误升级停机(M11 2-2 巨星实锤)。
        """
        _m = self.ctx.cw_match
        if _m is not None and getattr(_m.session, 'bail_reason_counts', None):
            _m.session.bail_reason_counts.pop(reason, None)

    def _handle_star_tome_pick(self, screen) -> None:
        """星徽秘典四选一(2026-08-16 建档;r104 接入策略模块 decide_star_tome)。

        卡名 OCR 在卡头带(四个卡名 y≈277 行,卡 x 中心 ≈ 660/950/1240/1530);「XX星徽」名去
        「星徽」后缀即阵营名。策略层打分:target 阵营/board 已有/配方框架;无命中 fallback 卡1。
        实测点卡即选(无需确认按钮),弹窗自关。
        """
        try:
            _match = self.ctx.cw_match
            ocr = self.ctx.ocr_service.get_ocr_result_list(screen, crop_first=False)
            cards: list[tuple[str, int]] = []   # (阵营名, x中心)
            for o in ocr:
                t = o.data.strip()
                if t.endswith('星徽') and len(t) > 2:
                    faction = t[:-2]
                    cards.append((faction, o.x + o.w // 2))
            cards.sort(key=lambda c: c[1])
            pick_x = 660   # fallback 卡1
            pick_name = '(fallback卡1)'
            if cards and _match is not None:
                from sr_od.application.currency_war.cw_state import GameState
                _st = _match.session.last_state or GameState()
                _cfg = getattr(_match, 'config', None)
                idx = _match.strategy.decide_star_tome(
                    [c[0] for c in cards], _st, _match.session, _cfg)
                if 0 <= idx < len(cards):
                    pick_x, pick_name = cards[idx][1], cards[idx][0]
            self.ctx.controller.click(Point(pick_x, 300))
            log.info('[cw-loop] 星徽秘典四选一: 候选=%s → 选 %s @(%s,300)',
                     [c[0] for c in cards] or 'OCR未读到', pick_name, pick_x)
        except Exception as e:   # noqa: BLE001  选卡失败不阻塞(下轮重试或停机钩子接)
            log.warning('[cw-loop] 星徽秘典选卡异常(不阻塞): %s', e)
            self.ctx.controller.click(Point(660, 300))

    def _battle_frame_sample(self, screen) -> None:
        """[观测钩子·常驻,44 号]战斗中画面低频采样。

        判「战斗中」= 非备战屏(round_by_find_area 备战失败 + 非 popup);≥15s 一帧;
        内容哈希去重(同画面不重复存)。采到的是「loop 等待循环路过时的战斗画面」,
        非全量(战斗动画帧率远高于采样率)——边际证据用,足够 44 号起步。
        """
        import time as _time
        now = _time.time()
        if now - getattr(self, '_last_bframe_ts', 0.0) < 15.0:
            return
        try:
            if self.round_by_find_area(screen, '货币战争-备战', '标识-备战阶段',
                                       crop_first=False).is_success:
                return   # 备战屏不采
        except Exception:   # noqa: BLE001
            return
        # r2 review#4:曾只哈希前 30KB(顶部 5 行,战斗帧中部差异被吞)——resize 灰度
        # 64x36 哈希全帧(降采样后整帧信息都进哈希)
        import cv2
        _small = cv2.resize(cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY), (64, 36))
        h = hash(_small.tobytes())
        if h == getattr(self, '_last_bframe_hash', 0):
            return
        self._last_bframe_ts = now
        self._last_bframe_hash = h
        out_dir = Path('.debug/temp/currency_war/battle_frames')
        out_dir.mkdir(parents=True, exist_ok=True)
        cv2.imencode('.png', cv2.cvtColor(screen, cv2.COLOR_RGB2BGR))[1].tofile(
            str(out_dir / f'bf_{int(now)}.png'))

    def _last_true_hp(self, fallback_hp: int) -> int:
        """summary final_hp 真值源(r3 live 修):outcomes 内存轨迹的末条真 hp。

        recorder 只存 gold 轨迹,hp 轨迹在此模块内存维持(record_outcome 时);
        死局回大厅 fallback_hp 常为 100 兜底(hp_readable=False 污染 last_state)。
        """
        hp = getattr(self, '_last_outcome_hp', None)
        return hp if hp is not None else fallback_hp

    @staticmethod
    def _normalize_node_type(raw: str) -> str:
        """r363(审计 P0-1):节点类型词汇表统一(三源→中文标准词)。

        输入可能是:英文 Hu token(battle/reward/encounter/supply/boss/
        megastar)、OCR 中文(奖励/遭遇/补给/首领/巨星/战斗)、旧中文兜底
        (普通战斗)。输出 = cw_performance.EXPECTED_DROP 键域的中文标准词
        (普通战斗/精英/遭遇/boss/补给/奖励/巨星)。未知原样透传(不吞错)。
        """
        _MAP = {'battle': '普通战斗', 'reward': '奖励', 'encounter': '遭遇',
                'supply': '补给', 'boss': 'boss', 'megastar': '巨星',
                '战斗': '普通战斗', '奖励': '奖励', '遭遇': '遭遇',
                '补给': '补给', '首领': 'boss', '巨星': '巨星',
                '普通战斗': '普通战斗', '精英': '精英'}
        return _MAP.get((raw or '').strip(), raw or '普通战斗')

    @staticmethod
    def _node_type_from_table(_session, plane: int | None,
                              round_num: int | None) -> str | None:
        """r362:current 无值时按开局帧槽序表查本节点类型(首节点冷启动兜底)。

        plane_node_table(r306 开局帧读的完整槽序,session 级):slot i 的
        类型 ≈ 该位面第 i+1 节点(reward/reward/battle/battle/supply… 实证
        稳定,变异位仅 slot5/6)。位面重启后 session 重建 → 表也重建,无
        跨局污染。查不到(表空/越界)→ None(调用方退普通战斗)。
        """
        try:
            _table = getattr(_session, 'plane_node_table', None) or []
            _r = int(round_num or 0)
            if _table and 1 <= _r <= len(_table):
                return str(_table[_r - 1])
        except Exception:   # noqa: BLE001  best-effort 兜底
            pass
        return None

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
            # r260/r265(用户两轮指路修正):节点类型的**权威源 = 备战画面节点行**
            # (read_node_sequence,Hu 模板匹配,prep_director 每次备战已读并存
            # session.node_seq)——结算屏 OCR 是二手推断(r260 首版全屏搜'奖励'
            # 误中金币区'基础奖励',r265 area 版仍是推断),弃。
            # 此处只消费 session 里备战期读到的本节点类型。
            # r363(审计 P0-1:词汇表三源混写):中文兜底/英文 token/OCR
            # 中文混在同一列(全量 829 行 8 种值),下游 EXPECTED_DROP/
            # sim Δ池/视图按错误桶聚合。统一经 _normalize_node_type
            # 出口(中文标准词),三源进一个 normalizer。
            _node = 'boss' if _is_boss else self._normalize_node_type(
                getattr(_session, 'node_type_current', None)
                or self._node_type_from_table(_session, _plane, _round)
                or '普通战斗')
            _obs = read_round_outcome(self.ctx, screen, plane=_plane, round_num=_round,
                                      comp_tag=_comp_tag, node_type=_node)
            # killed 文本兜底(2026-08-18 用户语义:「扣血=战斗失败」):输轮结算屏形态 =
            # 「挑战结束+继续挑战」(无「挑战成功」/无带符号进度,文本规则返 None)→ 用
            # **上一轮结算真值 hp** 对比:hp 降 = 输,不降/回升 = 赢(赢轮 +2 长线作战回血
            # 实证 80→82→84)。last_hp 由 on_round_end 结算真值链维护,此处读 = 上轮值。
            # ⚖️ r64 review P1/P2 修:①**双侧置信度门** —— 本轮 hp_confidence < 0.9 不比
            # (boss 胜利屏 hp 裸数字读不到 → conf=0/hp_after=0,旧版 0≥prev 恒 False →
            # boss 赢轮恒判输);②**轮次邻接门** —— 上轮 hp 读失败时 last_hp 是更早轮的
            # 陈值,隔轮对比误判,只在上轮与本轮节点相邻(t 差 1)才比。_last_outcome_t
            # 与 last_hp 同步更新(高置信轮都记,与 killed 是否被文本判定无关)。
            _now_t = (_plane - 1) * 9 + _round if (_plane and _round) else None
            if _obs.hp_confidence >= 0.9 and _now_t is not None:
                if _obs.killed is None:
                    _prev_hp = getattr(_session, 'last_hp', None)
                    _prev_t = getattr(self, '_last_outcome_t', None)
                    if (_prev_hp is not None and _prev_t is not None
                            and _now_t - _prev_t == 1):
                        _obs.killed = _obs.hp_after >= _prev_hp
                        log.info('[cw-loop] killed 兜底(hp 对比):上轮 %s → 本轮 %s → %s',
                                 _prev_hp, _obs.hp_after, '赢' if _obs.killed else '输')
                self._last_outcome_t = _now_t
            # r68 结算第一页 progress 合并:「挑战进度 ±N」只在第一页(分支2 已暂存
            # _settle_page1_progress),第二页 parse 读不到 → 用暂存值兜底;用后清(下轮新值)。
            if _obs.progress_delta is None:
                _pg1 = getattr(self, '_settle_page1_progress', None)
                if _pg1 is not None:
                    _obs.progress_delta = _pg1
                    log.info('[cw-loop] progress 合并(第一页暂存):%s', _pg1)
                self._settle_page1_progress = None
            self.ctx.cw_match.strategy.on_round_end(
                GameState(), _session, self._cw_config, _obs)
            # last_hp_t 同步(r68 review:prep 新鲜度门的写入端;镜像 on_round_end 的
            # HP_CONFIDENCE_THRESHOLD 门,保证 last_hp 与 last_hp_t 恒同源同轮)。
            if _obs.hp_confidence >= HP_CONFIDENCE_THRESHOLD and _now_t is not None:
                _session.last_hp_t = _now_t
            # 遥测写端(review 半接线修复,2026-08-16):outcomes.jsonl 生产侧此前无写入方
            # (读端 join_decisions_outcomes 一直在等,两文件从未对上)。hp_after/hp_confidence/
            # node_type/comp_tag 已在 _obs;damage_dealt/killed 待 L1 结算屏建档(ADR-0166)。
            cw_telemetry.record_outcome(_obs)
            if _obs.hp_confidence >= 0.9:
                self._last_outcome_hp = _obs.hp_after   # summary final_hp 真值源(r3 修)
            # 外生事件(strategy/05 telemetry,预案触发频率语料):战斗节点完成
            # (r1 review#3:模块级便捷函数,run_id 自动取——此前传 run_id 首参打签名
            # 不存在,AttributeError 被吞致 exogenous 静默死)
            cw_telemetry.record_exogenous(
                _round, 'node_enter',
                detail=f'battle_done:{_obs.node_type}',
                state=_session.last_state)
            log.info('[cw-loop] on_round_end plane=%s round=%s hp_after=%s conf=%s comp=%s node=%s',
                     _plane, _round, _obs.hp_after, _obs.hp_confidence, _comp_tag, _obs.node_type)
        except Exception as e:  # noqa: BLE001  观测回路失败不阻塞对局
            log.warning('[cw-loop] on_round_end 失败(不阻塞): %s', e)

    @operation_node(name='对局循环', is_start_node=True, node_max_retry_times=400)
    def loop(self) -> OperationRoundResult:
        self._iter += 1
        if self._iter > CurrencyWarRunLoop.MAX_ITER:
            return self.round_fail(status='对局循环超时')
        # r363(审计 P1-6):stop 信号/超时路径补 abandoned summary——
        # 中止局(手停/哨兵/停机钩子)不走 3c 回大厅 → runs.jsonl 无此局
        # (近 6 局实锤,跨局统计分母偏)。loop 顶检测停止请求即补记,
        # 正常终局已写标记跳过(result 归 win/loss)。
        if (not self._summary_written
                and self.ctx.run_context.is_context_stop
                and self.ctx.cw_match is not None):
            import contextlib
            with contextlib.suppress(Exception):   # 遥测 best-effort
                _st_ab = self.ctx.cw_match.session.last_state
                cw_telemetry.record_run_summary(
                    result='abandoned',
                    plane_reached=_st_ab.plane if _st_ab else 1,
                    rounds_survived=_st_ab.round_num if _st_ab else 0,
                    final_hp=self._last_true_hp(
                        _st_ab.hp if _st_ab else 0),
                    notes='stopped-mid-run(r363 兜底)')
                self._summary_written = True
                log.info('[cw][loop] 中止局 summary 兜底:abandoned')
        screen = self.last_screenshot

        # r119 停滞 watchdog(用户 2026-08-21 纠偏「卡 30min 没发现」):
        # 局29 银狼 41min/局32 命运卜者 30min/局33 祈愿崩 553 iter——轮询监控
        # 只看进度摘要,卡死形态(同屏不动/空转)要跨采样对比才可见。本钩子
        # 让 bot 自己检测:**每 STALL_SNAPSHOT_EVERY 次迭代采样一次画面指纹
        # (OCR 关键词集合的哈希),连续 STALL_N 次指纹相同且非战斗/结算态
        # → 写 stall_watch.flag 哨兵**(AI 下次巡检/交互第一时间可见,处理
        # 流程写在 flag 里)。不停机(bot 可能只是慢),哨兵+日志双通道。
        try:
            self._stall_watch_tick(screen)
        except Exception as _e:   # noqa: BLE001  watchdog 失败不阻塞
            log.debug('[cw-watch] 停滞检测失败(不阻塞): %s', _e)

        # r15 焦点防线(loop 级,失焦僵尸根治):每 10 迭代主动验窗口焦点,失焦即激活。
        # r9 实证窗口后台化时输入静默丢/截图正常 → 环僵尸;click/drag 点位守卫(r9/r10)
        # 只护单操作,本防线兜全类(未覆盖操作/未来新动作)。best-effort。
        if self._iter % 10 == 0:
            import contextlib
            with contextlib.suppress(Exception):
                _gw = self.ctx.controller.game_win
                if not _gw.is_win_active:
                    log.warning('[cw!][loop] 窗口失焦(输入静默丢风险)→ 主动激活')
                    _gw.active()

        # 尽力而为 read_game_state(默认实现不读);**不做 hp 覆盖** —— hp 覆盖是 update_target 的事(§11.6 M6)。
        if self._iter == 1 and self._is_new_match:
            _st0 = read_game_state(self.ctx, screen)
            # r25 恢复对局标记(telemetry):bot 侧新 match 但游戏已在中局(首读 round>1
            # = 上局残局;第十/十一局三次数据归属混乱实证)。只标不改行为。
            if _st0.round_num > 1 or _st0.plane > 1:
                # A18(hook审计批4):数据归属标记,只标不改行为 → [cw] 非 [cw!]
                log.warning('[cw][loop] 恢复对局检测:新 match 但游戏在 P%s-r%s(上局残局,'
                            '本 run_id 数据含残局段)', _st0.plane, _st0.round_num)
                import contextlib
                with contextlib.suppress(Exception):   # 遥测 best-effort
                    cw_telemetry.record_exogenous(_st0.round_num, 'resumed_match',
                                                  detail=f'P{_st0.plane}-r{_st0.round_num} 残局续跑',
                                                  state=_st0)
            self.ctx.cw_match.strategy.on_match_start(
                _st0, self.ctx.cw_match.session, self._cw_config)

        # 0. 备战被锁(顶部"返回投资策略选择"按钮)→ 点去选策略(check#4 接手)。
        #    lcs_percent=0.9:防与「请选择投资策略」共享「选择投资策略」(6/8=0.75=默认阈值之上)
        #    误匹配 → 投资策略屏被本分支吞(点标题不动作)→ 死循环(2026-08-04 实跑发现,卡 plane1)。
        #    真「返回投资策略选择」按钮 OCR 1.0 不受影响。
        # 子态稳定门 bookkeeping(见 PREP_SETTLE_S):shift 本帧标志到 prev 后清零 ——
        # 备战分支命中时置回 True;下迭代 prev=False(非备战/overlay/结算)→ 新相位重计时。
        self._prev_frame_prep = self._frame_is_prep
        self._frame_is_prep = False
        if self.round_by_ocr_and_click(screen, '返回投资策略选择', success_wait=2, lcs_percent=0.9).is_success:
            return self.round_wait(wait=2)

        # [历史停机钩子已全部建档移除](hook审计 S8/r351 删死代码:循环体
        # `for ... in ():` 永不执行)——r24 教训见 git:钩子停机的前提是该屏
        # **偶发**出现;建档完成后立即删除,别留到「下次遇到」(曾致每局必停
        # 被误判「外部会话拦截」排查一整晚)。

        # [观测钩子·常驻,44 号战斗过程观测] 战斗中画面低频采样(≥15s/帧 → battle_frames/,
        # 内容哈希去重防同一战斗刷屏;非交互死时间的边际证据,结算屏/备战屏不采)。
        import contextlib
        with contextlib.suppress(Exception):   # 观测 best-effort
            self._battle_frame_sample(screen)

        # 0a0. 选择装备 overlay(r129,局37 r3 哨兵推送实证:**必须在 0a 选择伙伴前**——
        #      装备选择的副题也是「请选择1个」,选择伙伴屏的 标识-选择伙伴(文本
        #      「请选择1个」)在本屏同样命中 → HandleSelectPartner 误派发找不到
        #      确认按钮 → 失败循环。双 id_mark 门:装备标题+请选择1个都命中才派发。
        if (self.round_by_find_area(screen, '货币战争-选择装备', '标识-选择装备', crop_first=False).is_success
                and self.round_by_find_area(screen, '货币战争-选择装备', '标识-请选择1个装备', crop_first=False).is_success):
            from sr_od.application.currency_war.operations.handlers.handle_equip_pick import (
                HandleEquipPick,
            )
            _r0 = HandleEquipPick(self.ctx).execute()
            if _r0 is not None and getattr(_r0, 'success', False):
                self._clear_bail_count('事件overlay:equip_pick')
            return self.round_wait(wait=2)

        # 0a0b. 位面简报屏(r374,局54 哨兵实锤 30 iter stall):P2/P3 开局前
        #       的简报(三 boss+词缀+「下一步」)。屏已建档(货币战争-简报,
        #       按钮area「按钮-下一步」)但**位面过渡后的 loop 首见帧**走不到
        #       尾部分支 5——该屏全屏 OCR 耗时 3s+(文字密集),一帧多次全屏
        #       OCR 查询把 iter 拖到 10s+;更早的结算帧分支 6 点空白加速后,
        #       过渡到简报的半开帧反复 round_wait。修:0x 头部 find_area 优先
        #       命中即点按钮 area(单次区域查询,绕开全屏 OCR 依赖),并采简报
        #       真值(词缀/boss/难度 → ctx,与 StartCurrencyWarMatch 同槽)。
        if self.round_by_find_area(screen, '货币战争-简报', '标识-本场对局首领', crop_first=False).is_success:
            # 简报真值采集(boss_fit/mechanics_fit 输入;同 StartCurrencyWarMatch 槽位)
            try:
                from sr_od.application.currency_war.cw_briefing_obs import (
                    read_affixes,
                    read_bosses,
                )
                _aff = read_affixes(self.ctx, screen)
                if _aff:
                    self.ctx.cw_briefing_affixes = _aff
                _bs = read_bosses(self.ctx, screen)
                if _bs:
                    self.ctx.cw_briefing_bosses = _bs
            except Exception:   # noqa: BLE001  采集 best-effort
                pass
            _nx = self.round_by_find_and_click_area(
                screen, '货币战争-简报', '按钮-下一步', success_wait=2)
            if _nx.is_success:
                log.info('[cw-loop] 位面简报 → 点下一步(词缀/首领已采集)')
                # r378b(测量链 review B1):exogenous 生产端补 briefing——
                # schema 声明的 kind 此前零写入(死链同构),简报词缀是
                # 22 号预案频率统计的输入。
                with contextlib.suppress(Exception):   # 遥测 best-effort
                    cw_telemetry.record_exogenous(
                        0, 'briefing',
                        detail=f'affixes={getattr(self.ctx, "cw_briefing_affixes", None)}'
                               f' bosses={getattr(self.ctx, "cw_briefing_bosses", None)}')
                return self.round_wait(wait=1.5)
            return self.round_retry(wait=2)

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

        # 0a2. 银狼「我来当策划」策划事件 overlay(r103,局29 P2r6 41min 卡死实证;
        #      机制见 docs/game/gameplay/currency_war.md 银狼策划事件节):二选一卡,
        #      首次升2星=升费 vs 其他(默认升费——成长滚动投资前提);5费升2星=两卡
        #      全装备(无升费,任选)。选卡后可能弹「属性详情」面板 → handler 内关。
        #      ⚠️ 必须在 0a 后/备战(1)前:overlay 盖备战屏,loop 不认它就反复空读。
        if self.round_by_find_area(screen, '货币战争-骇入策划', '标识-我来当策划', crop_first=False).is_success:
            from sr_od.application.currency_war.operations.handlers.handle_planner_event import (
                HandlePlannerEvent,
            )
            _r2 = HandlePlannerEvent(self.ctx).execute()
            if _r2 is not None and getattr(_r2, 'success', False):
                self._clear_bail_count('事件overlay:planner')
                return self.round_wait(wait=2)
            return self.round_retry(wait=2)

        # 0a3. 命运卜者「强化效果三选一」overlay(r115,局32 P2r2 卡死 30min 实证;
        #      策划系事件族:标题+三卡+Q详情+确认,布局同策划事件)。P2 强化关。
        if (self.round_by_find_area(screen, '货币战争-命运卜者强化', '标识-命运卜者', crop_first=False).is_success
                and self.round_by_find_area(screen, '货币战争-命运卜者强化', '标识-请选择强化效果', crop_first=False).is_success):
            from sr_od.application.currency_war.operations.handlers.handle_fortune_picker import (
                HandleFortunePicker,
            )
            _r3 = HandleFortunePicker(self.ctx).execute()
            if _r3 is not None and getattr(_r3, 'success', False):
                self._clear_bail_count('事件overlay:fortune')
                return self.round_wait(wait=2)
            return self.round_retry(wait=2)

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
        #       ⚠️ r31 死循环修(live 实锤 15min+):祈愿试炼选项名含「聘用书」(4费聘用书)→ 本分支
        #       截胡 0h 祈愿分支(反复点×无效)。加祈愿屏排除:标识-祈愿试炼 命中 → 让路 0h。
        if (self.round_by_ocr(screen, '聘用书', lcs_percent=0.8).is_success
                and not self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼',
                                                crop_first=False).is_success):
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

        # 0i. 星徽秘典四选一(2026-08-16 M45 完整建档,用户指导):备战席「秘密典籍」道具
        #     (投资策略给,类补给箱占席)开启后弹四选一星徽。旧处理「点X保守关」(M33 只见过
        #     误开)升级为选卡:OCR 四卡名 → 选与 board 阵营匹配的(板上已有阵营优先,星徽
        #     阵营计数+1);无匹配 → fallback 卡1。选完弹窗自关回备战、槽腾空、星徽入 owned。
        #     判据(review P2 加固):id_mark 命中即接管 —— 提示词 OCR miss 时也进 handler
        #     (fallback 卡1),**不放行到备战分支**(弹窗盖备战 → 误派 PrepDirector ping-pong)。
        if self.round_by_find_area(screen, '货币战争-星徽秘典弹窗', '标识-星徽秘典', crop_first=False).is_success:
            self._handle_star_tome_pick(screen)
            return self.round_wait(wait=2)

        # 0j. 「前台区域无角色,无法出战」提示弹窗(2026-08-17 M49 停机建档):出战时前台空被
        #     游戏拒(cap 满角色留 bench / 前排保证未触发的边缘)。处理:点确认关弹窗 → 下轮
        #     备战分支 PrepDirector 重新部署(前排保证会把 bench 角色强转前排);若再次出战仍
        #     拒(部署失败边缘)会再弹本窗,15 streak 停机兜底(不至于死循环)。
        if self.round_by_find_area(
                screen, '货币战争-提示-前台无角色', '标识-无角色提示', crop_first=False).is_success:
            _ok_pt = self.round_by_find_and_click_area(
                screen, '货币战争-提示-前台无角色', '按钮-确认', success_wait=1)
            log.info('[cw-loop] 前台无角色提示 → 确认关闭(下轮 PrepDirector 前排保证重部署)')
            return self.round_wait(wait=1.5)

        # 1. 备战阶段 → PrepDirector 决策环(P1 挂载切换,doc 15/ADR-0123;原 BattlePrepCycle
        #   固定序列退役为 P3 前可切回的回退路径)。注:遭遇/选择伙伴 等 event overlay 已在
        #   0b/0c 处理(确认选择/未达上限);遭遇 round 是普通战斗(2026-08-04 视觉大模型确认)。
        if self.round_by_find_area(screen, '货币战争-备战', '备战标识-购买经验').is_success:
            self._frame_is_prep = True   # 稳定门 bookkeeping(本帧走备战分支)
            # ⚖️ 子态稳定门(2026-08-18 用户定调):结算→备战先渲染→节点类型 overlay 后弹
            # (普通战斗=商店面板/奖励/投资类…;策略→环境链式)—— 半开帧分发 = 未定型画面
            # 上行动(M47 ClickSpheres 误点 / bench_unidentified overlay 帧误采,两类实锤)。
            # 门:备战分支连续命中 ≥ PREP_SETTLE_S 才派 Director;期间只观察(round_wait 让
            # overlay 弹出,弹出后 0e 系分支先于本分支接管,消化完回备战重新计时 —— 链式
            # overlay 逐个走)。mid-phase 再入(prev=prep,如 Director bail 后重进)不重付。
            if not self._prev_frame_prep or self._prep_entry_ts is None:
                self._prep_entry_ts = time.monotonic()
                log.info('[cw-loop] 备战相位进入 → 稳定门计时 %.1fs(PREP_SETTLE_S)',
                         self.PREP_SETTLE_S)
            if time.monotonic() - self._prep_entry_ts < self.PREP_SETTLE_S:
                return self.round_wait(wait=1.0)   # 只观察:等 overlay 弹出/画面定型
            # 过渡门说明(r7 review P0-B):0e 系分支(上方)先于本分支检查同截图同三元组(id_mark
            # 位置判),OCR 按 id(image) 缓存 → 到达此处时 overlay 检查必全 False——旧「半开帧
            # 等 1.2s」门为不可达死码,已删;其继任者 = 上方子态稳定门(连续 3s,非同帧检查)。
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
            # r332(批次3/终审①③:battle_loop 消费返回值——
            # 旧版忽略 execute() 结果 → director 失败后下轮
            # 无条件重派新实例(实例计数清零)= 无限 ping-pong
            # (Y-1c/D-2.3 七轮 review 实证)。修:连续 N 次失败
            # →告警+视为停滞(交 stall 哨兵/unknown 兜底链),
            # 不再无限静默重派。
            # ⚠ 语义澄清(review 第9条):round_fail 在本节点
            # node_max_retry_times=400 下**不停机**——刻意:
            # 消除的是「静默」(无日志)而非「重试」;warning 进
            # 日志 = 哨兵(SENTINEL-HIT 检 [cw!])与人都能看到,
            # 停机决策留给观察者(对拍期不想因 gate bug 硬停局)。
            _ok = PrepDirector(self.ctx).execute()
            if not _ok:
                self._director_fail_streak = getattr(
                    self, '_director_fail_streak', 0) + 1
                if self._director_fail_streak >= 5:
                    log.warning('[cw!][loop] PrepDirector 连续 %d 次失败'
                                '(gate/环异常?)→ 本轮按未知画面处理'
                                '(哨兵/兜底链接管)', self._director_fail_streak)
                    return self.round_fail('PrepDirector 连续失败(停滞)')
            else:
                self._director_fail_streak = 0
            return self.round_wait(wait=2)  # 战斗中,下轮再判

        # 1b. 详情弹窗(点卡/点角色触发的:"可合成列表"祝福详情 / "角色详情"角色信息)→ ESC 关闭。
        #     lcs_percent=0.8:「角色详情」与 invest env 等屏的「角色」label 共享「角色」(2/4=0.5)→
        #     不收紧则凡有"角色"标签的屏(投资环境/...)都被 1b 吞 → ESC 卡死(2026-08-04 实跑,自己上轮加
        #     的 1b 修复引入此误匹配)。0.8 杀误匹配(真「角色详情」1.0 不受影响)。
        if (self.round_by_ocr(screen, '可合成列表', lcs_percent=0.8).is_success
                or self.round_by_ocr(screen, '角色详情', lcs_percent=0.8).is_success):
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=1.5)

        # 1d. 星徽详情弹窗(2026-08-17 M53 停机建档:「XX星徽套组」标题 + 流派星徽类型 + 效果/
        #     适配角色/合成公式面板;点球/装备操作误点开星徽图标的详情)。点右上 X 关回备战。
        #     不用 ESC(bug#2:面板已关时 ESC 落备战弹中断挑战);X 是弹窗内坐标永远安全。
        if (self.round_by_find_area(screen, '货币战争-星徽详情', '标识-流派星徽', crop_first=False).is_success
                or self.round_by_find_area(screen, '货币战争-星徽详情', '标识-套组标题', crop_first=False).is_success):
            _close = self.round_by_find_and_click_area(
                screen, '货币战争-星徽详情', '按钮-关闭', success_wait=1)
            log.info('[cw-loop] 星徽详情弹窗 → 点X关闭(误开,回备战)')
            return self.round_wait(wait=1.5)

        # 1f. **失败结算页**(战败即时结算:挑战结束大标 + 挑战进度掉血,无「按钮-继续挑战」——
        #     首领胜利屏也有「挑战结束」但无「挑战进度」+有继续挑战,组合 id_mark 天然区分;M44 前三连咬
        #     皆单锚撞车,组合归位)。两步序贯出口(用户实证):先「点击空白加速」→ 后「前往结算」按钮。
        #     分支内先查按钮词(有则点 SETTLEMENT_NEXT),无则点空白加速——两步都推进。
        if (self.round_by_find_area(screen, '货币战争-结算-失败', '标识-挑战进度', crop_first=False).is_success
                and self.round_by_find_area(screen, '货币战争-结算-失败', '标识-挑战结束', crop_first=False).is_success
                and not self.round_by_find_area(
                    screen, '货币战争-结算', '按钮-继续挑战', crop_first=False).is_success):
            # 假 win 守卫(M70 事故):见过战败结算屏的 run 绝不判 win(即使 last_state.plane
            # 因 OCR 毒化显示 3)。
            self._saw_defeat_settlement = True
            for _btn in ('前往结算', '下一页', '下一步', '返回货币战争'):
                if self.round_by_ocr(screen, _btn, lcs_percent=0.8).is_success:
                    self.ctx.controller.click(CurrencyWarRunLoop.SETTLEMENT_NEXT)
                    self.park_cursor(after_wait=0.1)
                    return self.round_wait(wait=2)
            self.ctx.controller.click(CurrencyWarRunLoop.BLANK.center)
            self.park_cursor(after_wait=0.1)
            return self.round_wait(wait=2)

        # 1g. 中断挑战 dialog(bug#2:ESC 误按/误点左上角弹「是否中断挑战」,历史 3 次实锤;
        #     2026-08-17 建档「货币战争-中断挑战弹窗」,替原停机钩子)。真模态、点遮罩无效;
        #     出口:ESC / 右上X 关回备战(无副作用)。bot 策略 = 点右上 X 关闭继续对局
        #     (不点「暂时离开」免中断对局,绝不点「放弃并结算」——不可逆放弃进度)。
        #     弹窗内「小队生命值」为 HP 真值快照,顺带对账(备用,暂不消费)。
        if self.round_by_find_area(screen, '货币战争-中断挑战弹窗', '标识-中断挑战',
                                  crop_first=False).is_success:
            log.info('[cw] [loop] [1g] 中断挑战 dialog(误触)→ 点右上X关闭回备战')
            # r378b(测量链 review B1):exogenous 生产端补 popup——
            # 误触弹窗是外生事件高频源(bug#2 ESC 三次实锤),22 号
            # 预案的「弹窗干扰频率」此前零数据。
            with contextlib.suppress(Exception):   # 遥测 best-effort
                cw_telemetry.record_exogenous(0, 'popup', detail='中断挑战dialog误触')
            _btn = self.round_by_find_and_click_area(
                screen, '货币战争-中断挑战弹窗', '按钮-关闭')
            if _btn.is_success:
                self.park_cursor(after_wait=0.1)
                return self.round_wait(wait=1.5)
            # X 点击失败兜底:ESC 同样关闭(实测无副作用)
            self.ctx.controller.esc()
            return self.round_wait(wait=1.5)

        # 2. 点击空白加速 / 点击空白处继续 → 点空白
        if (self.round_by_ocr(screen, '点击空白加速').is_success
                or self.round_by_ocr(screen, '点击空白处继续').is_success):
            # r68 结算第一页暂存(progress 真值页):「挑战进度 ±N」只在第一页(点击空白加速
            # 帧);outcome 记录在第二页(按钮-继续挑战帧) → 第一页 progress 丢失(r135318
            # 实证 outcome 全 progress=None 而屏上有 +2)。此处读出暂存,分支3 记录时合并。
            try:
                _texts1 = [r.data for r in self.ctx.ocr_service.get_ocr_result_list(
                    image=screen, rect=None, crop_first=False)]
                from sr_od.application.currency_war.cw_settlement_obs import (
                    parse_settlement_progress,
                )
                _pg1 = parse_settlement_progress(_texts1)
                if _pg1 is not None:
                    self._settle_page1_progress = _pg1
            except Exception:   # noqa: BLE001  暂存 best-effort
                pass
            self.ctx.controller.click(CurrencyWarRunLoop.BLANK.center)
            return self.round_wait(wait=1.5)

        # 3. 挑战成功/结束 → P1.5 结算屏读 hp(on_round_end 观测回路)→ 继续挑战
        if self.round_by_find_area(screen, '货币战争-结算', '按钮-继续挑战').is_success:
            self._record_round_outcome(screen)  # P1.5: 结算屏(挑战成功)→ read_round_outcome → on_round_end
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
                # ⚠️ 场景切换过渡等待(用户 2026-08-16 实证):结算→下一场景时**备战先渲染、
                # 事件 overlay(投资策略/遭遇等)后弹出**(M47 22:34:43 帧同屏并存实锤)——旧
                # wait=2 时 loop 可能在 overlay 半开帧进备战分支动手(点球乱操作)。加到 3s
                # + 备战分支过渡门(见分支1)双保险。
                return self.round_wait(wait=3)
            return self.round_wait(wait=3)
        self._settle_stay = 0   # 离开结算屏重置

        # 3b. 对局结束结算(前往结算→下一页→返回货币战争)→ 逐页点回大厅。结算"前进"按钮恒在底部中央。
        # 「下一步」= 挑战失败终局结算屏(M41 战败形态,M42 实锤):同底部中央位,SETTLEMENT_NEXT 点进。
        for btn in ('前往结算', '下一页', '下一步', '返回货币战争'):
            # lcs_percent=0.8:「返回货币战争」与事件屏「返回备战界面」共享「返回+战」(3/6=0.5)→
            # 不收紧则凡有"返回备战界面"的事件屏(投资策略/环境/补给)都被 3b 吞 → 卡死(2026-08-04 发现)。
            if self.round_by_ocr(screen, btn, lcs_percent=0.8).is_success:
                # 输轮 outcome 记录(2026-08-18 用户点破:「扣血=战斗失败,游戏内有记录」):
                # 「前往结算」帧 = 轮败/位面结束/团灭结算(无「继续挑战」按钮,分支3 不达)——
                # 旧版输轮从不产生 outcome 行 → telemetry 只见赢轮,「P2 输给谁/扣多少」全盲。
                # 同屏指纹防重(结算屏停留多轮只记一次;与分支3 _last_settle_fp 同机制)。
                if btn == '前往结算':
                    _fp = tuple(sorted((r.data, r.y) for r in self.ctx.ocr_service.get_ocr_result_list(
                        image=screen, rect=None, crop_first=False)))
                    if getattr(self, '_last_loss_fp', None) != _fp:
                        self._last_loss_fp = _fp
                        self._record_round_outcome(screen)   # killed/progress_delta 由屏文本判定
                # r10 战败屏 hp=0 补录:第四局实证 P2-2 团灭,战败结算屏不走
                # _record_round_outcome(仅胜利结算屏分支3)→ outcomes 无 hp=0 记录
                # → _last_outcome_hp 空 → summary 落 last_state 100 兜底污染。
                if btn == '下一步' and self.round_by_ocr(screen, '挑战失败').is_success:
                    self._last_outcome_hp = 0
                    self._saw_defeat_settlement = True
                    log.info('[cw-loop] 战败结算屏 → hp=0 补录 outcomes 真值源')
                self.ctx.controller.click(CurrencyWarRunLoop.SETTLEMENT_NEXT)
                # 光标 parking(审计 R6):点击点正落在「下一页」文本框内,多页结算每页按钮同带
                # → 光标压当页按钮文字 → OCR miss → unknown streak 停机。点完 park。
                self.park_cursor(after_wait=0.1)
                return self.round_wait(wait=2)

        # 3c. 回到大厅(对局结束)→ loop 完成,避免在 lobby 无动作无限 retry。
        # 用「创业指南」(大厅左菜单独有、无特殊括号,OCR 稳)而非「开始「货币战争」」(括号 gt 不稳)
        if self.round_by_find_area(screen, '货币战争-大厅', '标识-创业指南').is_success:
            # r10 假局守卫:本 loop 从未记过 round_outcome(未打过任何一回合)却见大厅
            # = 开局失败/中断(第四局实证:开局失败回大厅 → 用旧 session 拼假 loss,
            # final_hp=100/rounds=2 全污染)。不记 summary、不喂分配器,仅清理 match。
            if getattr(self, '_last_outcome_hp', None) is None and self._rounds_done == 0:
                log.warning('[cw][loop] 开局阶段即回大厅(无任何 round_outcome)→ 判开局失败,不记假 summary')
                self.ctx.cw_match = None
                return self.round_success('开局失败/中断(未产生对局数据,不记 summary)')
            if self.ctx.cw_match is not None:
                # B4(ADR-0170 telemetry 接线):终局真实数据灌 MatchOutcome(原桩全默认)——
                # won=回大厅即本局结束;plane/round/hp 取 session.last_state(每回合框架刷新的
                # 最后快照;⚠️ CurrencyWarMatch 无 state 字段——review 子代理 P0 实锤,勿写
                # cw_match.state)。喂 strategy.on_match_end + 跨局分配器(0170,分级奖励)。
                _st = self.ctx.cw_match.session.last_state
                # ⚠️ 假 win 守卫(2026-08-17 M70 事故):won 曾用 `plane >= 3`——恢复对局时 plane
                # 被 OCR 读成 8(A8 难度泄漏)→ 8>=3 → 假通关进遥测。现要求 **plane==3 精确值**
                # (值域守卫已在上游拒 8,此处双保险);且死局(本局见过战败结算屏 1f)不判 win。
                _died_this_run = getattr(self, '_saw_defeat_settlement', False)
                _outcome = MatchOutcome(
                    won=(_st is not None and _st.plane == 3 and not _died_this_run),
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
                # ⚠️ final_hp 语义修正(2026-08-17 r3 live):死局回大厅后 last_state.hp
                # 是结算屏后读不到的 100 兜底(hp_readable=False)——summary 曾记 100 而
                # 实际 1。改用 outcomes 侧最后真值(recorder 内存轨迹,conf=1.0 的末条)。
                cw_telemetry.record_run_summary(
                    result='win' if _outcome.won else 'loss',
                    plane_reached=_outcome.final_plane,
                    rounds_survived=_outcome.final_round,
                    final_hp=self._last_true_hp(_outcome.final_hp),
                    notes='auto')
                self._summary_written = True
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
            comp_name = getattr(arm_obj, 'name', '') if arm_obj is not None else ''
            # 57-A1 修(臂命名空间):臂表键 = plaza carry 角色名,update 侧是 comp 阵容名
            # → 恒 no-op(62 局零累积实证)。comp→carry 归一映射(comp.plaza_carry)。
            arm_id = ''
            if comp_name:
                from sr_od.application.currency_war.cw_comps import get_comp
                _c = get_comp(comp_name)
                arm_id = getattr(_c, 'plaza_carry', '') or ''
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
        """[常驻兜底] loop 尾未知画面安全网(hook审计 S5/r351 分类修正:
        触发条件=「loop 尾所有分支不命中」= 兜一切未知的常驻安全网,
        **不是临时随机态钩子**——按临时写有误删风险;移除条件=该类
        未知态全部建档,实际不可达,长期保留)。方案 D,M43-resume 修复
        2026-08-16:战斗特效帧 OCR 乱码/新未建档画面 → streak 累计 →
        保画面停机待建档。曾被 _allocator_update 插入位置错误卷进方法体
        (从未执行)→ loop 隐式返 None(19:59 实锤)。
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
                    f'[HOOK-STOP] 持久未识别画面停机钩子([常驻兜底] loop 尾安全网):'
                    f'battle_loop._handle_unknown_fallback iter={self._iter} '
                    f'streak={self._unknown_streak}\n'
                    f'处理流程(r100k 补,别跳过):\n'
                    f'1. 用截图离线分析:analyze_screen(screenshot=<shot 路径>) 看已建档命中;\n'
                    f'2. 未命中 → 按元素语义判断:新画面/弹窗 → od-dev-screen-onboarding 建档\n'
                    f'   + battle_loop 0x 分支加 handler;战斗特效帧(OCR 乱码)→ **先确认\n'
                    f'   非新画面(analyze_screen 为准)才可**加大 UNKNOWN_STOP_THRESHOLD\n'
                    f'   或加等待,不是新画面;\n'
                    f'3. 建档完删本 flag + 重启 MCP server;若判断为瞬时帧误触发 → 删 flag\n'
                    f'   直接重跑(阈值/防抖在 UNKNOWN_STOP_THRESHOLD)。\n'
                    f'移除条件:该类未知态全部建档(实际不可达,长期保留)。\n'
                    f'shot={_shot}', encoding='utf-8')
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

