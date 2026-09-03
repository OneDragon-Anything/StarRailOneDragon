import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point

# 迁移审计 w75(git 历史)(ADR-0335):after_operation_done 的 result 注解在类定义期求值,OperationResult
# 必须**运行期可导入**(TYPE_CHECKING 块对此场景不够——本模块无
# `from __future__ import annotations`;用 _ 别名避与参数名冲突)。
from one_dragon.base.operation.operation_base import OperationResult as _OperationResult
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.decision.cw_strategy import StrategySession
from sr_od.application.currency_war.kernel.cw_performance import (
    RoundOutcome,
)
from sr_od.application.currency_war.kernel.cw_state import MatchOutcome
from sr_od.application.currency_war.obs.cw_observation import (
    read_game_state,
    read_node_sequence,
    read_phase_round,
    reset_phase_round_cache,
)
from sr_od.application.currency_war.obs.cw_resume_lock import (
    locked_after_start_battle,
    probe_resolve,
    resume_candidate,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_armory_box import (
    CwScreenArmoryBox,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_battle_wait import (
    CwScreenBattleWait,
    SettlementState,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_bookcard import (
    CwScreenBookcard,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_boss_briefing import (
    CwScreenBossBriefing,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_briefing import (
    CwScreenBriefing,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_deploy_not_full import (
    CwScreenDeployNotFull,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_encounter import (
    CwScreenEncounter,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_expert_invite import (
    CwScreenExpertInvite,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_fortune import (
    CwScreenFortune,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_invest_strategy import (
    CwScreenInvestStrategy,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_megastar import (
    CwScreenMegastar,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_partner import (
    CwScreenPartner,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_plane_transition import (
    CwScreenPlaneTransition,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_planner import (
    CwScreenPlanner,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_prep import (
    CwScreenPrep,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_supply_node import (
    CwScreenSupplyNode,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_wait_one_one import (
    CwScreenWaitOneOne,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_wish_trial import (
    CwScreenWishTrial,
)
from sr_od.application.currency_war.telemetry import query, recorder, state
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwLoop(SrOperation):
    """货币战争 对局内主循环:反复「备战单轮 + 轮间过渡」直到对局结束 / 超时。

    状态机(每轮截图后按优先级匹配):
    1. 备战阶段(「购买经验」)→ CwScreenPrep 备战单轮(观察→对账→决策→期望态→执行)→ 等战斗;
    2. 「点击空白加速」/「点击空白处继续」→ 点空白(加速战斗 / 关教程叠层);
    3. 「挑战成功」后「继续挑战」→ 点 → 下一轮;
    4. 「投资环境」3 选 1 → 点左牌 + 「确认」;
    5. 「下一步」等前进按钮 → 点。

    naive 策略(买全部 + 填位 deploy);对局从已进入的备战开始跑(开对局由
    ``CwEntryStart`` 负责,本 op 只跑对局内循环)。MAX_ITER 防失控。
    """

    MAX_ITER: ClassVar[int] = 2000  # 整局 3 位面多轮(备战+战斗+多类事件);战斗 round_wait 占大量迭代。
    # 2026-08-04 实跑:500 不够 —— reactive 弱阵战斗慢,plane2 r5 打「蚕食者之影」时 iter 撞 500
    # →「对局循环超时」失败(bot 一直在推进,非逻辑 bug,是迭代预算耗尽)。bump 到 2000(≈66min 预算)。
    # 待优化:MAX_ITER 应只计「动作迭代」(备战/事件/结算),不计战斗 round_wait(战斗长短不该吃预算)。
    # 未知画面常驻兜底钩子(方案 D):连续 N 轮未识别画面 → stop_running 保画面待 AI 建档。
    # 常驻安全网——兜一切未知态,不是点名某态的临时捕获;移除条件 = 该类未知态全部建档,
    # 实际不可达(实现见本类 _handle_unknown_fallback)。
    # 15 轮 ≈ 30s 纯卡(过渡帧 1-2 轮内被上面分支接走,不累计);远 < MAX_ITER。
    UNKNOWN_STOP_THRESHOLD: ClassVar[int] = 15
    #: 未知帧重试退避封顶(秒)。连续未识别帧的重试间隔按 2s 起步每连续一次翻倍,
    #: 封顶本值——旧实现恒 2s 立即重试,战斗特效长动画/未建档画面期每 2s 打一次
    #: 全量截图+OCR 空转(重试无退避缺陷)。阈值触达总时长由 ≈30s 放宽到 ≈2min,
    #: 换取停机钩子触发前画面有充分自愈窗口(若真是过渡帧,长动画期 2s 恒重试
    #: 只烧预算不推进)。
    UNKNOWN_RETRY_BACKOFF_CAP_S: ClassVar[float] = 10.0
    #: P4R:0j「前台无角色」恢复链的验证重部署重试上限(本 run 累计;出战
    #: 真转移后复位)。超限 round_fail 交未知画面兜底链——不再无限 round_wait
    #(1-1 事故 5h 死循环返工)。
    FRONTLESS_REDEPLOY_LIMIT: ClassVar[int] = 2
    #: P4R3:0q 位面过渡误分发型 fail 上限(连续计;0p 接管/过渡成功清零)。
    #: 超限 round_fail 交未知画面兜底链——第五局实锤:boss 简报帧误分发
    #: CwScreenPlaneTransition(「提示未出现」fail)每 2s 无限循环。
    PLANE_MISDISPATCH_LIMIT: ClassVar[int] = 3
    # r119 停滞 watchdog 参数:每 5 iter 采一次指纹(≈5-10s),连续 6 次相同
    # (≈1-2min 同屏)→ 哨兵。战斗态(指纹含「战斗/胜利/挑战」关键词)豁免。
    STALL_SNAPSHOT_EVERY: ClassVar[int] = 5
    STALL_N: ClassVar[int] = 6
    #: 战斗窗口 watch 宽限(ADR-0250):出战后合法静止上限。实测战斗 4-5.5min
    #: (P1r9 boss 4min20s/P2r1 遭遇 5min20s),600s 覆盖余量后仍可哨兵真挂死。
    BATTLE_WATCH_GRACE_S: ClassVar[float] = 600.0
    # (结算链常量族 SETTLE_PANEL_WAIT_S/SETTLE_DEFEAT_LATCH_MIN_T/
    #  RELAUNCH_SETTLE_GRACE_S/BLANK/SETTLEMENT_NEXT 已随 1f/2/3/3b/6 分支
    #  收编 CwScreenBattleWait(W971 05-battle §1),常量随 op 迁移单一源。)
    # ⚖️ PREP_SETTLE_S 备战稳定门已退役(W971 §2.6/03-prep §1):「识别到什么
    # 画面,就进入对应的 op」——半开帧/延迟 overlay 防护替身 = ①逐动作回流程层
    # 确认画面(overlay 弹出当步即见,转入 overlay op)②触发计算式追加等待
    # (03-prep §3 DeployMove 行)③director 环入口清场+自动开店预收探针。
    # 原「按最长动画盲等 3s」的门与其 bookkeeping(_frame_is_prep 族)一并删除。
    # 同批退役:_post_settle_auto_shop 标志位(结算后自动开店判稳收编 director
    # 环入口预收探针 + 准备就绪锚,不再跨分支传标志)。
    #: 备战 stall 留证阈值(W971 03-prep §3 规格最小集:连续 N 轮 session 对账
    #: 字段族无变化 → 留证;内环拆除后平移外循环。初值 3,校准项)。
    PREP_STALL_EVIDENCE_ROUNDS: ClassVar[int] = 3

    def __init__(self, ctx: SrContext, max_rounds: int | None = None):
        SrOperation.__init__(self, ctx, op_name='货币战争-对局循环')
        self._iter: int = 0
        # 迁移审计 w75(git 历史)(ADR-0335):runs summary 收口——中止/卡死/停机局不走 3c 回大厅
        # → record_run_summary 永不调(近 6 局无 runs 行实锤,r363 在 loop 顶
        # 的 stop 检查因 execute() 先查 stop 几乎永不触发,四局 [RUNS-GAP]
        # 哨兵连报)。机制:正常终局(3c)写 summary 后置本标记;``after_operation_done``
        # 收口钩子(成功/失败/停止全路径必达)检查未写 → 补一条 stopped/abandoned
        # (hp/plane/round 取最后已知值)。
        self._summary_written: bool = False
        # 可控轮数(单/多轮验证 + 采样本):跑完 max_rounds 轮后,停在下一轮备战屏(analyze board/star)。
        # 轮锚点 = 分支3「挑战成功」结算(每打赢 1 轮 +1);停点 = 分支1 备战 gate(rounds_done≥max → 停)。
        # None = 现行跑到对局结束/超时(向后兼容)。app 从 config.max_rounds 透传;run_operation 可直传。
        self._max_rounds: int | None = max_rounds
        # (轮计数 _rounds_done 已随结算链收编 CwScreenBattleWait → SettlementState
        #  .rounds_done(W971 05-battle §1);本类经 self._settle.rounds_done 读。)
        # r119 停滞 watchdog 状态:画面指纹采样(OCR 关键词 frozenset 哈希)。
        # 每 STALL_SNAPSHOT_EVERY iter 采样一次;连续 STALL_N 次相同 → 哨兵。
        self._stall_last_fp: int | None = None
        self._stall_count: int = 0
        self._stall_flag_written: bool = False
        # B4(ADR-0170):跨局分配器实例(进程级单例——后验跨局累积;失败安全:任何异常静默禁用)
        self._allocator = _get_or_init_allocator(self.ctx)
        # 开一次 run 的遥测 run_id(本地 decisions.jsonl 采集用;outcomes/summary 写端已接 2026-08-16)。
        # difficulty:ctx.cw_selected_difficulty(CwEntryStart 难度确认屏读存;此时**尚未**被
        # 下方取走 —— 取走在 cw_match new 之后,此处先读传 telemetry,review 半接线「difficulty 恒空」修复)。
        _diff_for_telemetry = self.ctx.cw_selected_difficulty or ''
        state.start_run(difficulty=_diff_for_telemetry)
        # R4-1(迁移审计 w52(git 历史) §3.1):recovered 三字段(_run_start_ts/_first_settlement_seen/
        # _is_new_match)+ match 建立/续用块 + 每局缓存清空,已迁 handle_init——
        # 框架语义:execute() 每次开头 _init_before_execute 调 handle_init,
        # __init__ 不随 execute 重入重跑(原写在 __init__ → 重入不重置,R4 审查
        # 报告检查项 4:「漏标不误标」保守退化,此处根治)。
        # _is_new_match 与 match 建立块必须**同块迁移**:_is_new_match 的求值
        # (ctx.cw_match is None)在「match 尚未建立」时点才有意义——只迁三字段
        # 会让首次 execute 重判时 cw_match 恒已存在(_is_new_match 恒 False,
        # on_match_start/残留屏判定双双失活)。整块迁移后:首次 execute 时序与
        # 原 __init__ 等价(本方法在首个节点运行前执行);execute 重入时重判
        # ——cw_match 若已建立则不再当新局(保守方向:漏标不误标,R4 已证)。

    def handle_init(self) -> None:
        """run 级状态初始化(框架钩子:每次 execute() 开头由
        ``_init_before_execute`` 调用;见类注 R4-1 迁移说明)。"""
        # 迁移审计 w28(git 历史) 缺陷①:run 启动时刻 + 首见结算屏标记(relaunch 残留结算判据)
        # ——已随结算链收编 CwScreenBattleWait(SettlementState,W971 05-battle §1):
        # run 启动时刻/新局标记在下方 _is_new_match 求值后注入。
        # 每局清空 plane/round last-known-good(防跨局复用上局值;task#24)
        reset_phase_round_cache()
        # SrOperation 还没 last_screenshot(截图由 node runner 进 @operation_node 时给)→ 不能 read_game_state;
        # on_match_start 在 loop() 首次截图后调(见下方 _iter==1 守卫)。跨步状态进 session.target_comp
        # (替代旧 BuyShopCards._target_comp class-attr hack,语义等价:每局新建已是现行为)。
        # 续跑支持(手动逐轮验证):cw_match 已存在(上轮 RunLoop 留下)→ 延用,不 new;否则 new(整局开始)。
        # 手动逐轮(max_rounds=1 反复 run_operation)靠此跨 run 延续 match state(target 稳定不每轮重选振荡)。
        # 停 app / 手停 / 重启 server 后 cw_match 清(None)→ 下次 run 重新 new(新局)。
        self._is_new_match: bool = self.ctx.cw_match is None
        # 战斗窗口驻留闩:出战成功置位 → 后续帧委托 CwScreenBattleWait 直到其
        # 完成(白名单/终局/bail);帧锚激活(接管局/残留屏)为第二入口。
        self._battle_wait_active: bool = False
        # 迁移审计 w62(git 历史) 件1(ADR-0329):恢复局(locked-resume)检测状态。
        # 候选 = 新 match(无本局记录),首个备战相位 round>1 时探针裁决;续跑恒 False。
        self._cw_resume_candidate: bool = self._is_new_match
        self._cw_locked_resume: bool = False   # 锁定确认(探针零响应)→ 直接出战
        self._cw_locked_round: int = 0         # 锁定确认时的轮次(遥测/日志锚)
        # 「返回投资策略选择」按钮出现计数(症状报警用:出现=上游策略屏处理失败)
        self._cw_back_btn_count: int = 0
        # 迁移审计 w103(git 历史) 件1(ADR-0342):策略失活连击(连续完整轮无 strategy_id 决策行)
        self._cw_strategy_dead_streak: int = 0
        self._cw_dead_prev_key: tuple[int, int] | None = None
        self._cw_config: CurrencyWarConfig = CurrencyWarConfig(self.ctx.current_instance_idx)
        # 战斗/结算链状态机 + CwScreenBattleWait 实例(W971 05-battle §1 收编):
        # 结算读点/点继续/败局链/终局分叉的状态随 op 迁移,本 loop 只持引用
        # (3c 收口/summary 读真值)。op 实例跨场复用(状态机生命周期 = 局级;
        # 每 execute 重handle_init → run 启动时刻/新局标记随之刷新,与原
        # _run_start_ts/_first_settlement_seen 的 run 级语义一致)。
        self._settle = SettlementState(
            run_start_ts=time.monotonic(), is_new_match=self._is_new_match)
        self._battle_wait = CwScreenBattleWait(self.ctx, self._settle, self._cw_config)
        if self._is_new_match:
            # match 建立(兜底分支):正常路径已由 CwEntryStart 在
            # 进对局时经 establish_new_match 前移建立(W971 §2.1,CwScreenBriefing
            # 直写 session 的时序前提);此处覆盖「绕过入口链直跑 loop」
            # 的场景(如 run_operation 单跑),同一 helper 无逻辑分叉。
            from sr_od.application.currency_war.decision.cw_strategy_manager import (
                establish_new_match,
            )
            establish_new_match(self.ctx, self._cw_config)
            # r339b:板深快照注册移**match new 后**(review 预核 A:
            # 原在 start_run 处注册时 cw_match 恒 None——新局
            # 首战快照死)。续跑局在 else 支支注册。
            state.set_ctx_match(self.ctx.cw_match)
        else:
            # 续跑局:同样注册(r339b——原注册点对续跑局也晚于
            # start_run,统一在两支各自 new/延用后注册)
            state.set_ctx_match(self.ctx.cw_match)
        # 入口链 ctx 中转吸收(P3b 收缩:仅剩职级难度——难度确认屏读存
        # ctx.cw_selected_difficulty,非简报信箱域)。简报词缀/boss/敌人难度
        # 的 ctx 信箱已退役(W971 §2.1「消灭 ctx 信箱」P3 批口径):唯一写点 =
        # CwScreenBriefing 直写 session,本段不再吸收。
        self._absorb_selected_difficulty(self.ctx.cw_match.session)
        # else 续跑:延用 self.ctx.cw_match(上轮留下),仅刷新 _cw_config(用户可能改 max_rounds 等运行时配置)

    def _absorb_selected_difficulty(self, session: StrategySession) -> None:
        """入口链职级难度 ctx 中转 → session(自原 _absorb_ctx_mailbox 收缩)。

        迁移自原 handle_init 新局分支(行为不变);简报三字段吸收段已随
        ctx 信箱退役删除(W971 §2.1 P3 批口径,见调用处注释)。
        """
        # 本局职级(CwEntryStart 难度确认屏读存 ctx.cw_selected_difficulty)→ session.selected_difficulty
        # → 策略层填 state → effective_hp_threshold D-32(3.5.1 接线)
        if self.ctx.cw_selected_difficulty:
            session.selected_difficulty = self.ctx.cw_selected_difficulty
            self.ctx.cw_selected_difficulty = None  # 取走清空(防跨局复用)

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

    @staticmethod
    def _watch_in_battle_grace(battle_ts: float | None, now: float) -> bool:
        """战斗窗口宽限判定(纯函数,ADR-0250):``battle_ts`` 非空且未超
        ``BATTLE_WATCH_GRACE_S`` → True(watch 不计数)。None/超时 → False。"""
        return (battle_ts is not None
                and now - battle_ts < CwLoop.BATTLE_WATCH_GRACE_S)

    def _stall_watch_tick(self, screen) -> None:
        """r119 停滞 watchdog:同屏指纹连续相同 → 哨兵(不停机,日志+flag 双通道)。

        指纹 = OCR 关键词 frozenset 哈希(5 iter 采一次,~5-10s 粒度)。战斗/
        结算/等待态关键词豁免(它们本来就该静止)。触发 = 写 stall_watch.flag
        (含处理指引)+ [cw!] 日志一次;画面变化后自动清计数(flag 留给 AI 巡检
        后删)。设计:采集哨兵非停机(bot 可能只是慢,停机代价>等待代价;
        od-dev-stop-hooks 采集/停机分流判据)。
        """
        if self._iter % CwLoop.STALL_SNAPSHOT_EVERY != 0:
            return
        # ADR-0250(战斗窗口宽限,局54 哨兵误报复盘):出战后的战斗进行期是
        # 合法静止(实测 4-5.5min > watch 阈值 ≈2.5min),且战斗 HUD 关键词
        # 可全程不含豁免词(局54 实锤:4 词缀+3 首领+难度常驻简报信息面板,
        # 「决战在即」是词缀名非战斗标语)→ 关键词豁免兜不住,误报稀释真哨兵
        # 信号。窗口内不计数;宽限过 → 恢复正常判定(出战卡死类真挂死仍可触发)。
        # 开窗=备战环出口(出战);关窗=on_round_end(结算观测)/备战分支再入。
        if self._watch_in_battle_grace(
                getattr(self, '_battle_ts', None), time.monotonic()):
            self._stall_count = 0
            self._stall_last_fp = None
            return
        if getattr(self, '_battle_ts', None) is not None:
            self._battle_ts = None   # 宽限已过 → 恢复正常停滞判定
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
        if self._stall_count >= CwLoop.STALL_N and not self._stall_flag_written:
            _shot = self.save_screenshot(prefix='cw_stall')
            _sentinel = (get_project_root() / '.debug' / 'temp'
                         / 'currency_war' / 'stall_watch.flag')
            _sentinel.parent.mkdir(parents=True, exist_ok=True)
            _sentinel.write_text(
                f'停滞 watchdog:iter={self._iter} 同屏指纹连续 {self._stall_count} 次'
                f'(≈{self._stall_count * CwLoop.STALL_SNAPSHOT_EVERY} iter)\n'
                f'OCR 关键词: {sorted(texts)[:12]}\n'
                f'处理流程:\n'
                f'1. 看关键词/截图:疑似事件 overlay(未建档 handler)→ 按\n'
                f'   od-dev-screen-onboarding 建档 + cw_loop 0x 分支加 handler;\n'
                f'2. 处理完删本 flag。bot 未停机(可能只是慢),处理完可继续跑。\n'
                f'shot={_shot}', encoding='utf-8')
            log.warning('[cw!][watch] 停滞哨兵:同屏 %s 次(≈%s iter)关键词=%s '
                        'shot=%s —— 疑似未处理 overlay/操作循环,详见 stall_watch.flag',
                        self._stall_count,
                        self._stall_count * CwLoop.STALL_SNAPSHOT_EVERY,
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

    def _last_true_hp(self, fallback_hp: int | None) -> int | None:
        """summary final_hp 真值源(r3 live 修):outcomes 内存轨迹的末条真 hp。

        recorder 只存 gold 轨迹,hp 轨迹由 CwScreenBattleWait 结算链维持
        (SettlementState.last_outcome_hp,W971 05-battle §1 收编);
        死局回大厅 fallback_hp 常为 100 兜底(hp_readable=False 污染 last_state)。
        """
        hp = self._settle.last_outcome_hp
        return hp if hp is not None else fallback_hp

    def after_operation_done(self, result: '_OperationResult') -> None:
        """局终 runs summary 收口(迁移审计 w75(git 历史)/ADR-0335;治本 r363 死码)。

        r363 把 stop 兜底放在 loop() 顶 —— 但 ``operation.execute()`` 每轮前
        (operation.py:408)先查 ``is_context_stop``,stop 到达后 ``loop()`` 不再被调,
        loop 顶检查几乎永不触发(MCP stop 四局 [RUNS-GAP] 哨兵连报实锤)。
        本钩子在 ``execute()`` 全路径收口(after_operation_done 对成功/失败/停止
        必达,operation.py:492):未写 summary 的对局在此补写,hp/plane/round
        取最后已知值(session.last_state;hp 走 ``_last_true_hp`` 防 100 兜底毒化),
        result='stopped'(停止) / 'abandoned'(超时/异常退出)。
        """
        super().after_operation_done(result)
        self._write_terminal_summary_if_needed()

    def _write_terminal_summary_if_needed(self) -> None:
        """局终/中止 summary 补写(幂等:_summary_written 守卫 + 假局守卫)。

        正常终局(3c 回大厅)已写 → 跳过;开局失败/无对局数据(假局)不写
        (镜像 3c 的 r10 守卫:无任何 round_outcome 却回大厅 = 开局失败,
        不拼假 loss 污染分母)。停止/超时/异常 → 取最后已知值补写。
        """
        if self._summary_written:
            return
        if self._settle.last_outcome_hp is None and self._settle.rounds_done == 0:
            return   # 假局守卫(镜像 3c):无 outcome 数据不写假 summary
        _m = self.ctx.cw_match
        _st = _m.session.last_state if _m is not None else None
        if _st is None:
            return   # 无最后已知态(理论上不可达:有 outcome 必有 state)
        try:
            _stopped = bool(getattr(self.ctx.run_context, 'is_context_stop', False))
            _final_hp = self._last_true_hp(_st.hp if _st.hp is not None else 0)
            state.record_run_summary(
                result='stopped' if _stopped else 'abandoned',
                plane_reached=_st.plane,
                rounds_survived=_st.round_num,
                final_hp=_final_hp,
                notes=('stopped:operation 收口(W75)' if _stopped
                       else 'abandoned:operation 异常收口(W75)'))
            self._summary_written = True
            log.info('[cw][loop] 局终 summary 收口:%s p%s-r%s hp=%s',
                     'stopped' if _stopped else 'abandoned',
                     _st.plane, _st.round_num, _final_hp)
        except Exception as e:   # noqa: BLE001  遥测 best-effort,不阻塞退出
            log.warning('[cw][loop] 局终 summary 收口失败(不阻塞): %s', e)


    def _record_supply_outcome(self, screen) -> None:
        """迁移审计 w28(git 历史) 缺陷②:补给节点完成 → 合成一行 outcome(node_type='补给')。

        补给是唯一无结算屏的节点(迁移审计 w23(git 历史) 定因:r5 34/34 全缺)——节点完成绕过
        分支3 的结算写入点 → hp_after/金币/装备选择在 outcomes 零行。本方法在
        CwScreenSupplyNode 成功完成点补一行:**复用 cw_telemetry.record_outcome 单一
        写入入口**,带 source='synthetic_supply'(镜像 ADR-0273 行来源标记)防与
        结算屏真值行混淆。hp 用 last_state 快照(最近备战观察;hp_readable=False
        时置信度记 0,hp 字段不冒认真值)。plane/round 用 last-known(补给屏顶栏
        被遮,read_phase_round 走缓存)。只写遥测,不喂 on_round_end/last_hp
        (不改策略行为面)。失败不阻塞对局(观测为辅)。
        """
        try:
            _m = self.ctx.cw_match
            if _m is None:
                return
            _session = _m.session
            _plane, _round = read_phase_round(self.ctx, screen)
            _st = _session.last_state
            _hp = (_st.hp if _st is not None and _st.hp is not None else 0)
            _conf = 1.0 if (_st is not None and getattr(_st, 'hp_readable', True)) else 0.0
            _comp_tag = _session.target_comp.name if _session.target_comp else '?'
            # 消费 run_supply_node 选定时暂存的选择快照,并附完成时点 gold
            # (gold_readable=False 不写——同 hp 不冒认真值;键缺失容忍=兜底点卡路径)。
            _pick = state.consume_last_supply_pick() or {}
            if _st is not None and getattr(_st, 'gold_readable', True):
                _pick['gold'] = getattr(_st, 'gold', None)
            _obs = RoundOutcome(
                round_num=_round, plane=_plane, node_type='补给', comp_tag=_comp_tag,
                hp_after=_hp, hp_confidence=_conf,
                killed=True,   # 语义=节点通过(非战斗击杀;synthetic 行专用)
            )
            recorder.record_outcome(_obs, source='synthetic_supply',
                                        supply_pick=_pick or None)
            log.info('[cw-loop] 补给节点完成 → 合成 outcome 行 P%s-r%s hp=%s(conf=%s pick=%s)',
                     _plane, _round, _hp, _conf, _pick or '-')
        except Exception as e:  # noqa: BLE001  合成行失败不阻塞对局
            log.warning('[cw-loop] 补给合成 outcome 失败(不阻塞): %s', e)

    @operation_node(name='对局循环', is_start_node=True, node_max_retry_times=400)
    def loop(self) -> OperationRoundResult:
        self._iter += 1
        if self._iter > CwLoop.MAX_ITER:
            return self.round_fail(status='对局循环超时')
        # 迁移审计 w75(git 历史)(ADR-0335):stop 路径 runs summary 收口已从 loop 顶迁到
        # ``after_operation_done`` —— r363 在 loop() 顶检查 is_context_stop,
        # 但 operation.execute() 每轮前(operation.py:408)先查 stop,stop 到达后
        # loop() 不再被调 → 原检查几乎永不触发(MCP stop 四局 [RUNS-GAP] 实锤)。
        # 收口钩子对成功/失败/停止全路径必达(operation.py:492),见类注。
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
            # ADR-0462:消费面只有 plane/round(恢复对局检测/on_match_start 归属标记)
            # → battle/过渡帧最小读(仅位面轮次,其余字段该帧无备战可读)。
            _st0 = read_game_state(self.ctx, screen, phase='battle_or_transit')
            # r25 恢复对局标记(telemetry):bot 侧新 match 但游戏已在中局(首读 round>1
            # = 上局残局;第十/十一局三次数据归属混乱实证)。只标不改行为。
            if _st0.round_num > 1 or _st0.plane > 1:
                # A18(hook审计退役批(ADR-0466/0467/0469)):数据归属标记,只标不改行为 → [cw] 非 [cw!]
                log.warning('[cw][loop] 恢复对局检测:新 match 但游戏在 P%s-r%s(上局残局,'
                            '本 run_id 数据含残局段)', _st0.plane, _st0.round_num)
                import contextlib
                with contextlib.suppress(Exception):   # 遥测 best-effort
                    recorder.record_exogenous(_st0.round_num, 'resumed_match',
                                                  detail=f'P{_st0.plane}-r{_st0.round_num} 残局续跑',
                                                  state=_st0)
            # 接管局补采(boss+词缀)挂点 = 干净备战观察(W971 §2.1,CwScreenPrep
            # 环入口 gate 后稳定帧执行;稳定门退役后由备战观察承担)。
            self.ctx.cw_match.strategy.on_match_start(
                _st0, self.ctx.cw_match.session, self._cw_config)

        # 「返回投资策略选择」分支已挪入备战分支(2026-08-26 用户定性:
        # 该按钮出现 = 上游投资策略屏处理失败的 symptom)——确定是备战画面后再
        # 特殊处理,不在备战判定前全屏扫(原位置吞掉策略屏自身 → 点标题死循环)。
        # (原子态稳定门 bookkeeping 随 PREP_SETTLE_S 退役删除,见类常量注。)

        # [历史停机钩子已全部建档移除](hook审计 S8/r351 删死代码:循环体
        # `for ... in ():` 永不执行)——r24 教训见 git:钩子停机的前提是该屏
        # **偶发**出现;建档完成后立即删除,别留到「下次遇到」(曾致每局必停
        # 被误判「外部会话拦截」排查一整晚)。

        # 0a0. 选择装备 overlay(r129,局37 r3 哨兵推送实证:**必须在 0a 选择伙伴前**——
        #      装备选择的副题也是「请选择1个」,选择伙伴屏的 标识-选择伙伴(文本
        #      「请选择1个」)在本屏同样命中 → CwScreenPartner 误派发找不到
        #      确认按钮 → 失败循环。双 id_mark 门:装备标题+请选择1个都命中才派发。
        if (self.round_by_find_area(screen, '货币战争-选择装备', '标识-选择装备', crop_first=False).is_success
                and self.round_by_find_area(screen, '货币战争-选择装备', '标识-请选择1个装备', crop_first=False).is_success):
            from sr_od.application.currency_war.operations.cw_screen.cw_screen_equip_pick import (
                CwScreenEquipPick,
            )
            _r0 = CwScreenEquipPick(self.ctx).execute()
            if _r0 is not None and getattr(_r0, 'success', False):
                self._clear_bail_count('事件overlay:equip_pick')
            return self.round_wait(wait=2)

        # 0a. 选择伙伴 overlay(必须在 0b 巨星前:选择伙伴也有"确认选择"但候选是 stage 立绘)
        #     → CwScreenPartner(overlay 分发接管;委托现役 handler,详见 op)。
        #     用 screen_info 标题 area(标识-选择伙伴)位置区分,非全屏 LCS:「选择伙伴」与「请选择投资策略」
        #     共享「选择」(2/4=0.5=默认阈值)会误匹配全屏 LCS → 投资策略屏被误派发(2026-08-04 snap 实测)。
        #     area 位置不同(选择伙伴 overlay 标题在 top-center id_mark rect)→ 不命中(同 0d/0e area 化理由)。
        if self.round_by_find_area(screen, '货币战争-列车同行', '标识-选择伙伴', crop_first=False).is_success:
            self._snap('choose_partner')  # 选人选项(立绘名)→ 后续建策略评估用
            _r = CwScreenPartner(self.ctx).execute()
            if _r is not None and getattr(_r, 'success', False):
                self._clear_bail_count('事件overlay:partner')   # review M2:仅成功才清(失败保计数=ping-pong 安全网)
            return self.round_wait(wait=2)

        # 0a2. 银狼「我来当策划」策划事件 overlay(r103,局29 P2r6 41min 卡死实证;
        #      机制见 docs/game/gameplay/currency_war.md 银狼策划事件节)→ CwScreenPlanner
        #      (W971 P3b overlay 分发接管;二选一卡,首次升2星=升费 vs 其他,默认升费;
        #      选卡后可能弹「属性详情」面板 → handler 内关)。
        #      ⚠️ 必须在 0a 后/备战(1)前:overlay 盖备战屏,loop 不认它就反复空读。
        if self.round_by_find_area(screen, '货币战争-骇入策划', '标识-我来当策划', crop_first=False).is_success:
            _r2 = CwScreenPlanner(self.ctx).execute()
            if _r2 is not None and getattr(_r2, 'success', False):
                self._clear_bail_count('事件overlay:planner')
                return self.round_wait(wait=2)
            return self.round_retry(wait=2)

        # 0a3. 命运卜者「强化效果三选一」overlay(r115,局32 P2r2 卡死 30min 实证;
        #      策划系事件族:标题+三卡+Q详情+确认,布局同策划事件)→ CwScreenFortune
        #      (W971 P3b overlay 分发接管)。P2 强化关。
        if (self.round_by_find_area(screen, '货币战争-命运卜者强化', '标识-命运卜者', crop_first=False).is_success
                and self.round_by_find_area(screen, '货币战争-命运卜者强化', '标识-请选择强化效果', crop_first=False).is_success):
            _r3 = CwScreenFortune(self.ctx).execute()
            if _r3 is not None and getattr(_r3, 'success', False):
                self._clear_bail_count('事件overlay:fortune')
                return self.round_wait(wait=2)
            return self.round_retry(wait=2)

        # 0a4. 位面详情 overlay(主循环兜底):情报采集 op 失败退出残留/开局自动
        #      弹出等一切来源 → 点 X 验标题消失。此前不在 0 系名单:2026-08-30
        #      残局恢复局实证,采集失败滞留详情屏 → 主循环连 15 轮未识别自停
        #      (ADR-0269「新增画面忘进名单」结构性缺口再现)。采集子 op 运行中
        #      不经此路(子 op 自带详情识别与关闭);恢复局商店探针/出战等
        #      in-match 分支全部位于本分支之后,overlay 不再污染其判读。
        if self.round_by_find_area(screen, '货币战争-位面详情', '标识-位面详情标题',
                                   crop_first=False).is_success:
            _pd_close = self.round_by_find_and_click_area(
                screen, '货币战争-位面详情', '按钮-关闭位面详情', success_wait=1.5)
            if not _pd_close.is_success:
                return self.round_retry('位面详情关闭键未命中,等重试')
            if self.round_by_find_area(self.screenshot(), '货币战争-位面详情',
                                       '标识-位面详情标题',
                                       crop_first=False).is_success:
                return self.round_retry('位面详情点X未关,等重试')
            self._clear_bail_count('事件overlay:plane_detail')
            log.info('[cw-loop] 位面详情 overlay 已关(主循环兜底)')
            return self.round_wait(wait=1.0)

        # 0b. 巨星强化(盛会之星选择 overlay)→ CwScreenMegastar(选候选 + 确认,已内联旧巨星节点执行器实现)。
        #     用 screen_info 标题 area(标识-盛会之星)位置区分。原用全屏「确认选择」(lcs 0.7 防「请选择投资策略」
        #     共享「选择」误匹配)—— 但「确认选择」partner overlay 也有(靠 0a 先捕 partner 区分);改用 megastar
        #     独有标题「盛会之星」更直接(独有标题位置区分,无需依赖分支先后)。
        if self.round_by_find_area(screen, '货币战争-盛会之星', '标识-盛会之星', crop_first=False).is_success:
            self._snap('megastar')  # 巨星候选(立绘名)→ 后续建策略评估用
            _r = CwScreenMegastar(self.ctx).execute()  # 生命周期 owner:验证 overlay 消失,超预算 bail
            if _r is not None and getattr(_r, 'success', False):
                self._clear_bail_count('事件overlay:megastar')   # 合法 bail 清计数(live M11 误停机;M2:仅成功才清)
            return self.round_wait(wait=2)

        # 0c. 遭遇节点(难度二选一 + 选择)→ CwScreenEncounter(点卡选中 + 选择确认)。
        #     live 2026-08-15:改 id_mark area 检测(标识-遭遇节点,yml 已建)—— 旧全屏 OCR「遭遇其一」
        #     lcs 0.9 在卡标题 OCR 截断帧(「遭遇其」3/4=0.75)miss → 整屏落未知画面停机。
        #     handler 交互(2026-08-04 实测):点卡身选中 → 点选择确认(中间勿插空白点击会取消选中)。
        if self.round_by_find_area(screen, '货币战争-遭遇节点', '标识-遭遇节点', crop_first=False).is_success:
            self._snap('encounter')
            CwScreenEncounter(self.ctx).execute()
            return self.round_wait(wait=2)

        # 0d. 出战确认弹窗(未达上限)→ CwScreenDeployNotFull(勾本局不再提示 + 确认,详见 op)。
        # 用 screen_info id_mark area(标识-未达上限警告)位置区分,非全屏 LCS:投资策略屏的策略描述「能量上限」
        # 与「未达上限」共享子序列「上限」(LCS 2/4=0.5)会误匹配全屏 LCS → 投资策略屏被本分支吞 → 反复触发
        # CwScreenDeployNotFull 卡死(2026-08-05 实跑)。id_mark area 位置不同 → 不命中(同 0e invest area 化理由)。
        if self.round_by_find_area(screen, '货币战争-未达上限警告', '标识-未达上限警告', crop_first=False).is_success:
            CwScreenDeployNotFull(self.ctx).execute()
            return self.round_wait(wait=3)

        # 0e. 选择类事件 overlay(投资策略/环境 3 选 1;补给动态 N 选,通常 4/augment 变
        #     3-5 + 确认)→ **必须在备战(1)前检测**:
        #     这些 overlay 叠在备战上,「购买经验」会从 overlay 后透出(底部左下未遮)→ 若先检查备战
        #     会误派 BuyShopCards(overlay 遮商店→"找不到商店/收起"失败→死循环)。
        #     2026-08-04 实跑发现:投资策略屏被误派 BuyShopCards(购买经验透出命中),卡死。
        #     lcs_percent=0.8:「投资策略」与「投资环境」共享「投资」(2/4=0.5)→ 0.8 杀交叉误匹配。
        # 用 screen_info id_mark area 检测(固定位置全等),非全屏 LCS —— 失败结算屏(对局未完成)含
        # 「投资策略/投资环境」(对局信息)会误匹配全屏 LCS(2026-08-06 实跑:loop 卡失败结算,
        # CwScreenInvestStrategy 误派点「标准博弈」死循环)。id_mark area 位置不同(失败结算在对局信息区,
        # 不在真屏 id_mark pc_rect)→ 不命中,落到 3b「下一页」回大厅。
        if self.round_by_find_area(screen, '货币战争-投资策略', '标识-请选择投资策略', crop_first=False).is_success:
            self._snap('invest_strategy')
            CwScreenInvestStrategy(self.ctx).execute()
            return self.round_wait(wait=2)
         # 开局投资环境段(01-opening §2,OpeningSequence 已拆解退役):投资环境仅开场一次
        # (#11:开场 1-1 前弹,1-3 后局中只弹投资策略,两画面不同 handler),
        # 开局投资环境由 0s 分支分发(OpeningSequence 拆解退役:外循环按画面自然流转)。
        if self.round_by_find_area(screen, '货币战争-补给', '标识-补给阶段', crop_first=False).is_success:
            self._snap('supply')
            _rs = CwScreenSupplyNode(self.ctx).execute()  # 生命周期 owner:验证 overlay 消失才完成,超预算 bail(旧节点基类 committed-but-verifying 语义已内联)
            # 迁移审计 w28(git 历史) 缺陷②:补给节点完成 → 合成 outcome 行(无结算屏节点的遥测补行;
            # 仅成功时记,失败重试由下轮 0e 再入,不重复写)。
            if _rs is not None and getattr(_rs, 'success', False):
                self._record_supply_outcome(screen)
            return self.round_wait(wait=2)

        # 0f. 节点武装箱弹窗(「武装突入」类节点,2026-08-15 M19 首见停机建档)→
        #     CwScreenArmoryBox(点开箱 → 四选一 → 选卡点卡 → 验关;与备战补给箱
        #     同下游不同入口,选卡公用 pick_box_card)。
        if self.round_by_find_area(screen, '货币战争-武装箱弹窗', '标识-简易武装箱', crop_first=False).is_success:
            self._snap('armory_box')
            CwScreenArmoryBox(self.ctx).execute()
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

        # 0h. 祈愿试炼 overlay(节点级 quest 选择:选1试炼 → 完 objective 得奖励)→ CwScreenWishTrial
        #     (W971 P3b overlay 分发接管;点第1卡 + 确认选择)。叠备战上挡备战分支 →
        #     必须在备战(1)前检测。2026-08-08 实跑发现:bot 卡此 overlay 68min(购买经验
        #     透出命中 → 备战分支误派 → shop 被遮失败 → 死循环)。ESC 不关;
        #     点卡身选中(金色边框)→ 确认选择 → 关回备战。
        if self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼', crop_first=False).is_success:
            # 钉屏停机钩子接线行([临时捕获],采集清单建档确认后连本注释整段删):
            # 当前为激活态(钩子本体 = grail_collect_hooks.grail_pin_stop_hook)。
            from sr_od.application.currency_war.operations.grail_collect_hooks import (
                grail_pin_stop_hook,
            )
            _hook_r = grail_pin_stop_hook(self)
            if _hook_r is not None:
                return _hook_r
            _rw = CwScreenWishTrial(self.ctx).execute()
            if _rw is not None and getattr(_rw, 'success', False):
                self._clear_bail_count('事件overlay:wish_trial')
            return self.round_wait(wait=2)

        # 0i. 星徽秘典四选一(2026-08-16 M45 完整建档,用户指导):备战席「秘密典籍」道具
        #     开启后弹四选一星徽 → CwScreenBookcard(overlay 分发接管,选卡读法按
        #     原内联 _handle_star_tome_pick 直写进 op)。判据(review P2 加固):id_mark
        #     命中即接管 —— 提示词 OCR miss 时也进 handler(fallback 卡1),**不放行到
        #     备战分支**(弹窗盖备战 → 误派 CwScreenPrep ping-pong)。
        if self.round_by_find_area(screen, '货币战争-星徽秘典弹窗', '标识-星徽秘典', crop_first=False).is_success:
            CwScreenBookcard(self.ctx).execute()
            return self.round_wait(wait=2)

        # 0k. 专家邀请函弹窗(2026-08-30 建档):备战席「书册卡」点开后的五选一
        #     (4 角色卡+现金为王)→ CwScreenExpertInvite 全链(开卡/选卡/收案;选卡
        #     判据=主力阵营同线→在场阵营同线→现金为王兜底,见 handler docstring)。
        #     判据同 0i:id_mark 命中即接管,不放行到备战分支(弹窗盖备战 →
        #     误派 CwScreenPrep ping-pong)。替代原 bookcard_confirm 停机钩子
        #     (钩子段已随本分支接线删除)。
        if self.round_by_find_area(screen, '货币战争-备战-专家邀请函', '标识-专家邀请函', crop_first=False).is_success:
            CwScreenExpertInvite(self.ctx).execute()
            return self.round_wait(wait=2)

        # 0m. 备战「锁定」暗色子态族(2026-09-02 建档+接线,用户口述时序 #12/#20):
        #     overlay 点「返回备战界面」→ 备战画面带暗色蒙层,右上「返回XX选择」
        #     可回对应 overlay。⚠️ 此态下备战双锚(购买经验/出战)仍精准命中
        #     (用户截图 analyze 实测 is_precise)——不先分流会被当正常备战操作
        #     (读暗牌/暗 gold)。命中即点对应按钮回 overlay(0e 系/0c 分支接管);
        #     备战分支内旧 OCR 兜底(双锚后)保留作双保险。
        #     通用规则单一源 = screen_flow_timing.md #18(暗色态判别锚=右上按钮)。
        for _lock_screen, _lock_area in (
                ('货币战争-备战-策略锁定', '按钮-返回投资策略选择'),
                ('货币战争-备战-遭遇锁定', '按钮-返回遭遇选择'),
        ):
            if self.round_by_find_area(screen, _lock_screen, _lock_area, crop_first=False).is_success:
                _sl = self.round_by_find_and_click_area(
                    screen, _lock_screen, _lock_area, success_wait=1.5)
                log.info('[cw-loop] 暗色锁定态(%s)→ 点返回按钮(success=%s)',
                         _lock_screen, _sl.is_success)
                return self.round_wait(wait=1.5)

        # 0j. 「前台区域无角色,无法出战」提示弹窗(2026-08-17 M49 停机建档)。
        #     P4R 升级(1-1 事故 5h 死循环返工):确认关闭 → **带落点验证的
        #     重部署**(CwOpDeploy,落点 CV 已收编)→ 验 deployed 前排 ≥1 →
        #     本迭代内再出战;重试上限 FRONTLESS_REDEPLOY_LIMIT,超限
        #     round_fail 交未知画面兜底链(旧「确认关闭→等下轮 CwScreenPrep
        #     → StartBattle 假成功」形态 = 无限 round_wait,根因见弹窗污染
        #     守卫 prep_actions.POST_LAUNCH_BLOCKERS)。
        if self.round_by_find_area(
                screen, '货币战争-提示-前台无角色', '标识-无角色提示', crop_first=False).is_success:
            _ok_pt = self.round_by_find_and_click_area(
                screen, '货币战争-提示-前台无角色', '按钮-确认', success_wait=1)
            self._frontless_redeploy = getattr(self, '_frontless_redeploy', 0) + 1
            if self._frontless_redeploy > CwLoop.FRONTLESS_REDEPLOY_LIMIT:
                log.error('[cw!] [loop] 前台无角色:验证重部署 %d 次仍前台空 → '
                          'round_fail 交兜底链(不再无限重试)',
                          CwLoop.FRONTLESS_REDEPLOY_LIMIT)
                return self.round_fail('前台无角色重部署超限(前台仍空)')
            log.info('[cw-loop] 前台无角色提示 → 确认关闭(%d/%d)→ 带验证重部署',
                     self._frontless_redeploy,
                     CwLoop.FRONTLESS_REDEPLOY_LIMIT)
            from sr_od.application.currency_war.operations.cw_op.cw_op_deploy import (
                CwOpDeploy,
            )
            _rd = CwOpDeploy(self.ctx).execute()
            log.info('[cw-loop] 前台无角色重部署 → %s',
                     getattr(_rd, 'status', '') or ('成功' if getattr(_rd, 'success', False) else '失败'))
            # 出口判据:deployed 前排 ≥1(独立于 CwOpDeploy 返回值——
            # 假成功已在 deploy 侧落点验证收编,此处再验一层作 0j 出口承诺)。
            from sr_od.application.currency_war.kernel.cw_obs_core import (
                slot_occupied as _slot_occ,
            )
            from sr_od.application.currency_war.prep_actions import (
                row_area_centers as _row_centers,
            )
            time.sleep(1.0)   # 部署动画/特效窗(落点 CV 稳定)
            _scr = self.screenshot()
            _front_ok = any(
                _slot_occ(_scr, int(p.x), int(p.y))
                for p in _row_centers(self.ctx, '前排'))
            if not _front_ok:
                log.warning('[cw!] [loop] 前台无角色重部署后前排仍空 → 交回重判'
                            '(下轮再入本分支计重试)')
                return self.round_wait(wait=1.5)
            # 前排已有角色 → 本迭代内直接再出战(不再依赖下轮 CwScreenPrep
            # 重派——旧链的假成功正是发生在这段间隙)。
            from sr_od.application.currency_war.kernel.cw_prep_actions import (
                StartBattle as _StartBattle,
            )
            from sr_od.application.currency_war.prep_actions import (
                PrepActionExecutor as _PAE,
            )
            _sb_ok, _sb_detail = _PAE(self, self.ctx).execute(_StartBattle())
            if _sb_ok:
                self._frontless_redeploy = 0   # 出战真转移 → 重试预算复位
                self._battle_ts = time.monotonic()
                self._battle_wait_active = True
                log.info('[cw-loop] 前台无角色恢复链:重部署+验前排 ✓ → 出战成功')
                return self.round_wait(wait=3)
            log.warning('[cw!] [loop] 前台无角色恢复链:重部署后出战未落地(%s)→ retry',
                        _sb_detail)
            return self.round_retry(wait=2)

        # 0p. BOSS 简报(P3b 实机第三局走查补:06-overlays §3 设计有、实现漏;
        #     #26 建档「标识-强敌来袭」)→ CwScreenBossBriefing(点空白 → 完成承诺 =
        #     等备战商店开,「按钮-收起」锚+上界兜底)。**分支序锚位 = 先于备战
        #     双锚**(事故教训:横幅遮挡下双锚模板仍透出命中,无本分支时帧误落
        #     备战分支空转 598s/SENTINEL-STALL)。
        #     P4R3 锚加固(第五局 1-9 实锤):area 锚被 OCR 误读击穿(「强敌
        #     来袭」读成「强敌米」)→ 分发改共享判别单一源 is_boss_briefing_
        #     texts(「强敌」片段,误读形态鲁棒;CwScreenBossBriefing 内部同源兜底)。
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_boss_briefing import (
            is_boss_briefing_texts as _is_boss_frame,
        )
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_boss_briefing import (
            read_ocr_texts as _frame_texts,
        )
        if (self.round_by_find_area(
                screen, '货币战争-BOSS简报', '标识-强敌来袭',
                crop_first=False).is_success
                or _is_boss_frame(_frame_texts(self.ctx, screen))):
            _bb_res = CwScreenBossBriefing(self.ctx).execute()
            # 0q 排他生效 = 误分发流恢复 → 计数清零
            self._plane_mis_streak = 0
            log.info('[cw-loop] BOSS 简报 → CwScreenBossBriefing → %s',
                     getattr(_bb_res, 'status', ''))
            return self.round_wait(wait=1.0)

        # 0q. 位面过渡(P4R2 序位返工:原在备战分支之后——「浮层叠备战」家族
        #     审计中唯一的序位漏项;全浮层序位纪律 = 先于备战双锚,序锁矩阵
        #     test_cw_dispatch_order_matrix.py 逐一钉死)。
        #     P4R3 两画面排他(第五局 1-9 实锤):boss 简报画面**也含**「点击
        #     空白处继续」(共享交互文案不作判据)——「强敌」特征在场 = boss
        #     简报帧,不进位面过渡(留给 0p);误分发型 fail(过渡提示不在)
        #     连续达上限 → round_fail 交未知兜底链(不再 2s 无限循环)。
        if self.round_by_ocr(screen, '点击空白处继续', lcs_percent=0.8).is_success:
            if _is_boss_frame(_frame_texts(self.ctx, screen)):
                log.info('[cw-loop] boss 简报帧含共享文案「点击空白处继续」→ '
                         '排他,留 0p(不误分发位面过渡)')
                return self.round_wait(wait=1.0)
            _pt = CwScreenPlaneTransition(self.ctx)
            _pt_res = _pt.execute()
            _pt_ok = bool(_pt_res is not None
                          and getattr(_pt_res, 'success', False))
            if _pt_ok:
                self._plane_mis_streak = 0
            else:
                self._plane_mis_streak = getattr(self, '_plane_mis_streak', 0) + 1
                if self._plane_mis_streak >= CwLoop.PLANE_MISDISPATCH_LIMIT:
                    try:
                        _shot = self.save_screenshot(prefix='plane_misdispatch')
                    except Exception:  # noqa: BLE001  留证失败不阻塞
                        _shot = ''
                    log.error('[cw!] [loop] 位面过渡连续 %d 次 fail(疑误分发/'
                              '误读)→ round_fail 交兜底链(shot=%s)',
                              self._plane_mis_streak, _shot)
                    return self.round_fail('位面过渡连续 fail 超上限(交兜底链)')
            log.info('[cw-loop] 位面过渡 → CwScreenPlaneTransition → %s',
                     getattr(_pt_res, 'status', ''))
            return self.round_wait(wait=1.0)

        # 0r. 位面简报(开场三 boss+词缀;接管局/重入首帧落此屏时兜底分流)
        #     → CwScreenBriefing(读简报写 session 位面序真值 → 点「下一步」链)。
        #     原 OpeningSequence 拆解退役(用户裁决:抽象不成立):四步各有
        #     画面 op,外循环按画面分发天然顺序流转(简报→位面过渡 0q→
        #     投资环境 0s→备战 1),接管局由分发器自然续走。
        if self.round_by_find_area(screen, '货币战争-简报', '标识-本场对局首领',
                                   crop_first=False).is_success:
            _br_res = CwScreenBriefing(self.ctx).execute()
            log.info('[cw-loop] 位面简报 → CwScreenBriefing → %s',
                     getattr(_br_res, 'status', ''))
            return self.round_wait(wait=1.0)

        # 0s. 投资环境(开场 1-1 前弹一次;接管局重入此屏时兜底分流)
        #     → CwScreenInvestEnv(节点台账重读/刷新流,现役 handler 全逻辑)。
        #     成功后链 CwScreenWaitOneOne:开局补给动画长且无结束标志(用户裁定
        #     特殊等待),等「备战阶段」锚就绪再交备战分支(承接退役序列的
        #     终步语义;锚一直不现由其超时上界留证 fail 交循环)。
        if self.round_by_find_area(screen, '货币战争-投资环境', '标识-投资环境',
                                   crop_first=False).is_success:
            from sr_od.application.currency_war.operations.cw_screen.cw_screen_invest_env import (
                CwScreenInvestEnv,
            )
            _iv_res = CwScreenInvestEnv(self.ctx).execute()
            log.info('[cw-loop] 投资环境 → CwScreenInvestEnv → %s',
                     getattr(_iv_res, 'status', ''))
            _w11_res = CwScreenWaitOneOne(self.ctx).execute()
            log.info('[cw-loop] 等待1-1 → CwScreenWaitOneOne → %s',
                     getattr(_w11_res, 'status', ''))
            return self.round_wait(wait=1.0)
        # 1. 备战阶段 → 备战单轮 op(CwScreenPrep 单轮五段:观察→对账→决策→
        #    期望态→执行,交回本循环;W971 P3b 返工定稿:内环已拆,外循环是
        #    唯一循环)。注:遭遇/选择伙伴 等 event overlay 已在 0 系分支处理。
        # 画面判定 = **双锚**(2026-08-26 用户定调「全面的 id mark」):「备战标识-购买经验」
        # (左下,conf 0.9999)+「按钮-出战」(右,跨 shop 开/关子态恒在;单锚在 overlay
        # 半开帧可从底层透出命中,prep.md §时序)。双锚同帧命中才认备战。
        if (self.round_by_find_area(screen, '货币战争-备战', '备战标识-购买经验').is_success
                and self.round_by_find_area(screen, '货币战争-备战', '按钮-出战').is_success):
            self._battle_ts = None   # ADR-0250:回备战 → 战斗窗口关(watch 恢复)
            # (原 PREP_SETTLE_S 子态稳定门 + _post_settle_auto_shop 自动开店判稳
            # 标志位已退役,W971 §2.6/§2.11:半开帧防护替身 = 单轮 op 清场 +
            # 自动开店收起探针;稳定性由外循环每轮重识别保证。)
            # 备战 stall 防线(W971 03-prep §3 规格最小集,内环拆除后平移外循环):
            # 连续 N 轮备战画面 session 关键字段无变化 → 留证(log + 存图;
            # 不停机,哨兵/未知兜底链继续兜)。签名 = prep_obs_frame 的对账字段族
            #(球/箱数、金、轮次、席位、vacancy;03-prep「对账字段族」口径)。
            _frame = getattr(self.ctx.cw_match.session, 'prep_obs_frame', None)
            _st = getattr(self.ctx.cw_match.session, 'last_state', None)
            _sig = (len(getattr(_frame, 'spheres', None) or []),
                    len(getattr(_frame, 'boxes', None) or []),
                    len(getattr(_frame, 'bench_chars', None) or []),
                    len(getattr(_frame, 'deployed_chars', None) or []),
                    getattr(_frame, 'deploy_vacancy', None),
                    getattr(_st, 'gold', None), getattr(_st, 'level', None),
                    getattr(_st, 'round_num', None))
            if getattr(self, '_prep_stall_sig', None) == _sig:
                self._prep_stall_count = getattr(self, '_prep_stall_count', 0) + 1
            else:
                self._prep_stall_sig = _sig
                self._prep_stall_count = 0
            if self._prep_stall_count >= self.PREP_STALL_EVIDENCE_ROUNDS:
                _stall_shot = self.save_screenshot(prefix='prep_stall')
                log.warning('[cw!][loop] 备战连续 %d 轮 session 无变化 → 留证(无进展;'
                            'sig=%s shot=%s)', self._prep_stall_count, _sig, _stall_shot)
            # 备战被锁(顶部「返回投资策略选择」按钮)→ 点去选策略(check#4 接手)。
            # 2026-08-26 挪位(原在备战判定前全屏扫):用户定性该按钮出现 = 上游
            # 投资策略屏处理失败的 symptom(策略屏点歪才退回备战带此按钮;同族 =
            # 补给/遭遇屏的「返回XX选择」)→ 先确定是备战画面(双锚)
            # 再特殊处理,顺带免掉每帧全屏 OCR。lcs_percent=0.9 保留:防与
            # 「请选择投资策略」共享「选择投资策略」(6/8=0.75=默认阈值之上)误匹配
            # → 投资策略屏被吞(点标题不动作)→ 死循环(2026-08-04 实跑,卡 plane1)。
            # 真「返回投资策略选择」按钮 OCR 1.0 不受影响。
            if self.round_by_ocr_and_click(screen, '返回投资策略选择', success_wait=2, lcs_percent=0.9).is_success:
                self._cw_back_btn_count += 1
                log.warning('[cw!][loop] 返回按钮=上游选择屏处理失败症状(策略屏点歪),第%d次',
                            self._cw_back_btn_count)
                return self.round_wait(wait=2)
            # 接管局补采(boss+词缀)已迁 CwScreenPrep(W971 §2.1/01-opening §2.1:
            # 稳定门退役后挂点 = 干净备战观察;见 cw_screen_prep._run_loop 采集块)。
            # 迁移审计 w103(git 历史) 件1(ADR-0342):策略失活早停——连续 2 个**完整轮**无任何带
            # strategy_id 的决策行(决策层整轮未参与;迁移审计 w98(git 历史) 两局实录:57/61 行恒空、
            # P1 全程 0 买、金囤 91/100,兜底打满 40min 垃圾局)→ 停局重启加载
            # 策略。「重大修复待加载=无条件早停」定调的运行期镜像:策略死了,
            # 继续跑=零信息量局。结算点=备战入口查**上一轮**(本轮决策尚未发生,
            # 查本轮恒空会误杀);telemetry 关闭时本检查让位(无数据=无判据)。
            if state.get_recorder().enabled:
                _dk = read_phase_round(self.ctx, screen)
                if _dk and _dk[0]:
                    _key = (int(_dk[0]), int(_dk[1]))
                    if _key != self._cw_dead_prev_key:
                        _dead_key = self._cw_dead_prev_key
                        _live = query.strategy_round_live(
                            state.current_run_id() or '', _dead_key) \
                            if _dead_key is not None else True
                        self._cw_strategy_dead_streak = (
                            query.dead_streak_transition(
                                _dead_key, _key,
                                self._cw_strategy_dead_streak, _live))
                        if _dead_key is not None and not _live:
                            log.warning('[cw!][loop] 策略失活轮 P%s-r%s'
                                        '(streak=%d,该轮无 strategy_id 决策行)',
                                        _dead_key[0], _dead_key[1],
                                        self._cw_strategy_dead_streak)
                        self._cw_dead_prev_key = _key
                        if self._cw_strategy_dead_streak >= 2:
                            log.warning('[cw!][loop] 策略失活连击 %d ≥2 → '
                                        '停局(重启加载策略;ADR-0342)',
                                        self._cw_strategy_dead_streak)
                            self.ctx.run_context.stop_running(
                                reason='cw:strategy_dead_early_stop')
                            return self.round_wait(
                                wait=1.0, status='策略失活早停(ADR-0342)')
            # 迁移审计 w62(git 历史) 件1(ADR-0329):恢复局(locked-resume)检测与直接出战。
            # 判据(设计章1.2)= 新 match(无本局记录)+ 首个备战相位 round>1 → 候选;
            # 一次「点商店→验收起」探针(章1.3)区分锁定/未锁(锁定唯一可观测特征
            # =商店按钮零响应);锁定态跳过全部备战交互直接出战(复用 StartBattle
            # 执行体,内含未达上限确认),出战成功即解除(章1.5)。误判防线:候选
            # 撤回(1-1 正常新局)/探针可开(非锁定)两处都不进锁定分支。
            if self._cw_resume_candidate:
                _pr = read_phase_round(self.ctx, screen)
                if not resume_candidate(self._is_new_match, _pr[0], _pr[1]):
                    self._cw_resume_candidate = False   # 1-1 正常新局,撤回候选
                else:
                    self.round_by_find_and_click_area(
                        screen, '货币战争-备战', '按钮-商店', success_wait=1.2)
                    _opened = self.round_by_find_area(
                        self.screenshot(), '货币战争-备战-开商店', '按钮-收起',
                        crop_first=False).is_success
                    self._cw_resume_candidate = False
                    if probe_resolve(_opened) == 'normal':
                        # 非锁定(误判防线):收起关店,清候选 → 落常规 CwScreenPrep
                        self.round_by_find_and_click_area(
                            self.screenshot(), '货币战争-备战-开商店', '按钮-收起',
                            success_wait=1.0)
                        log.info('[cw-loop] 恢复候选但商店可开 → 非锁定,走常规')
                    else:
                        self._cw_locked_resume = True
                        self._cw_locked_round = _pr[1]
                        import contextlib
                        with contextlib.suppress(Exception):   # 遥测 best-effort
                            recorder.record_exogenous(
                                _pr[1], 'locked_resume',
                                detail=f'P{_pr[0]}-r{_pr[1]} shop-probe-zero')
                        log.warning('[cw!][loop] 恢复局锁定确认(P%s-r%s,商店探针'
                                    '零响应)→ 直接出战', _pr[0], _pr[1])
            if self._cw_locked_resume:
                from sr_od.application.currency_war.kernel.cw_prep_actions import (
                    StartBattle,
                )
                from sr_od.application.currency_war.prep_actions import (
                    PrepActionExecutor,
                )
                progressed, detail = PrepActionExecutor(
                    self, self.ctx).execute(StartBattle())
                if progressed:
                    self._cw_locked_resume = locked_after_start_battle(progressed)
                    self._battle_ts = time.monotonic()   # ADR-0250:战斗窗口开
                    self._battle_wait_active = True   # 战斗窗口 → 下轮委托 CwScreenBattleWait
                    import contextlib
                    with contextlib.suppress(Exception):   # 遥测 best-effort
                        state.get_recorder().record_exec_event(
                            run_id=state.current_run_id() or '-',
                            round_num=self._cw_locked_round,
                            action_family='LockedResume_StartBattle',
                            screen='battle_prep', event='start_battle',
                            reason='locked_resume')
                    log.info('[cw-loop] 锁定恢复局 → 出战成功,锁解除(恢复正常循环)')
                    return self.round_wait(wait=3)
                log.warning('[cw!][loop] 锁定模式出战未落地(%s)→ retry(保锁定)',
                            detail)
                return self.round_retry(wait=2)
            # 过渡门说明(r7 review P0-B):0e 系分支(上方)先于本分支检查同截图同三元组(id_mark
            # 位置判),OCR 按 id(image) 缓存 → 到达此处时 overlay 检查必全 False——旧「半开帧
            # 等 1.2s」门为不可达死码,已删;其继任者 = 上方子态稳定门(连续 3s,非同帧检查)。
            # 可控轮数:已跑完 max_rounds 轮 → 停备战屏(可 analyze board/star + star 钩子采样本),不跑备战单轮。
            if self._max_rounds is not None and self._settle.rounds_done >= self._max_rounds:
                log.info('[cw-loop] max_rounds=%s 已跑 %s 轮 → 停备战屏(单/多轮验证)',
                         self._max_rounds, self._settle.rounds_done)
                return self.round_success(
                    f'已跑 {self._settle.rounds_done} 轮停备战(达 max_rounds={self._max_rounds})')
            # 补给节点(nodeseq 当前节点类型=supply):出战不推进(无出战打怪,确认补给即完成节点进下回合,
            # live 确认 2026-08-13)→ 点「返回补给阶段」进补给屏,下轮 Loop 0e 分支 CwScreenSupplyNode 选+确认。
            # ⚠️ 用 nodeseq 节点类型判,非「返回补给阶段」按钮 —— 该按钮 battle 节点也在(可 revisit),不可靠
            # (2026-08-13 实跑:1-6 battle 节点出战成功 + 也有该按钮)。nodeseq 读失败(非 clean 帧)→ 不 divert
            # (默认备战分支,保险不误判 battle 为 supply)。
            _cur_slot = next((s for s in (read_node_sequence(self.ctx, screen) or [])
                              if s.state == 'current'), None)
            if _cur_slot is not None and _cur_slot.node_type == 'supply':
                self.round_by_find_and_click_area(screen, '货币战争-备战', '按钮-返回补给阶段', success_wait=2)
                log.info('[cw-loop] 补给节点(nodeseq current=supply)→ 点返回补给阶段 进补给屏(下轮 CwScreenSupplyNode)')
                return self.round_wait(wait=2)
            # r332(批次3/终审①③:cw_loop 消费返回值——
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
            # `w595_trial_reveal_card/` 试用角色揭示卡清场:发光金卡点开即**免费**得 2★ 试用角色(原地变
            # 普通角色卡,后续 SIFT 自然识别)。无代价、无分支选择 → 非策略决策,
            # 不进 director 动作全集;备战环派发前直接清掉(揭示后 director heavy
            # 观察读到的已是揭示后的真实板面,不毒化对账)。上界 3 轮防识别抖动
            # 死循环;揭示后卡片消失 → 自然防重入。
            from sr_od.application.currency_war.kernel.cw_obs_core import (
                is_prep_like_frame,
            )
            from sr_od.application.currency_war.obs.cw_identity_obs import (
                _ctx_slots,
                find_bookcards,
                find_trial_reveal_cards,
            )
            for _reveal_i in range(3):
                _cards = find_trial_reveal_cards(screen, _ctx_slots(self.ctx, '备战栏', 9))
                if not _cards or not is_prep_like_frame(self.ctx, screen):
                    break
                _slot, _center = _cards[0]
                self.ctx.controller.mouse_move(_center)   # bug#1 缓解(同出战/点球口径)
                self.ctx.controller.click(_center)
                log.info('[cw-loop] 试用角色揭示卡 slot%s → 点击揭示(免费 2★)', _slot)
                time.sleep(1.2)   # 揭示动画窗(发光消散 + 角色卡落位)
                screen = self.screenshot()
            # 书册卡清场(2026-08-30 建档,与揭示卡同型预清场):开启后弹「专家邀请函」
            # 五选一,CwScreenExpertInvite 全链处理(开卡→默认策略选卡→收案);替代原
            # bookcard_confirm 停机钩子(钩子段已删,见 cw_identity_obs)。上界 2 轮
            # 防识别抖动死循环;选中的专家入商店由正常商店逻辑接管。
            for _bc_i in range(2):
                _bc_cards = find_bookcards(screen, _ctx_slots(self.ctx, '备战栏', 9))
                if not _bc_cards or not is_prep_like_frame(self.ctx, screen):
                    break
                _bc_result = CwScreenExpertInvite(self.ctx).execute()
                log.info('[cw-loop] 书册卡 slot%s → 处理链执行 success=%s',
                         _bc_cards[0][0], getattr(_bc_result, 'success', None))
                screen = self.screenshot()
            _ok = CwScreenPrep(self.ctx).execute()
            if not _ok or not _ok.success:   # 迁移审计 w68(git 历史):OperationResult 无 __bool__,
                # bool(FAIL)=True——裸 not _ok 恒 False,r332 停滞守卫成死码
                # (验证局 206 次崩溃-重派无限循环实录);success 才是判据。
                self._director_fail_streak = getattr(
                    self, '_director_fail_streak', 0) + 1
                if self._director_fail_streak >= 5:
                    log.warning('[cw!][loop] CwScreenPrep 连续 %d 次失败'
                                '(gate/环异常?)→ 本轮按未知画面处理'
                                '(哨兵/兜底链接管)', self._director_fail_streak)
                    return self.round_fail('CwScreenPrep 连续失败(停滞)')
            else:
                self._director_fail_streak = 0
                # 正常备战环跑完一轮 = 部署链健康 → 0j 恢复链重试预算复位
                #(预算只辖「前台无角色→重部署」连续失败窗,非整局总量)。
                self._frontless_redeploy = 0
                # ADR-0250:备战环经出战出口 → 战斗窗口开(watch 宽限计时起点)
                self._battle_ts = time.monotonic()
                # 环出口含出战 → 战斗窗口驻留闩置位(下轮委托 CwScreenBattleWait;
                # 环入口分诊交回/bail 的返回由下轮重判自然分流——非出战返回帧
                # 仍是备战画面,委托入口的帧锚不命中,闩却会错误置位?否:
                # 闩只表达「出战已发射」,CwScreenBattleWait 对非战斗帧走宽限等待,
                # 白名单锚(备战双锚单锚宽判定)命中即 success 交回,零风险)。
                self._battle_wait_active = True
            # 环让位重入契约(W971 §2.9,实机 P1-r6 bail ping-pong 修复):
            # director 返回(含环入口分诊交回/事件 overlay bail)后**必经本
            # return → 下轮 loop 顶全分支重判**(0x overlay 分支先于备战双锚),
            # 不在同一迭代内直接回备战分支/环。日志留痕 = 重入可观测
            #(此前 bail↔重派静默,排障无从分辨「没重判」vs「判了没接住」)。
            _ok_status = getattr(_ok, 'status', '') or ''
            log.info('[cw-loop] 备战环返回(success=%s status=%s)→ 交回顶层分发'
                     '(下轮全分支重判)', _ok.success if _ok else None, _ok_status)
            return self.round_wait(wait=1.0)  # 下轮重新识别分发(战斗中,下轮再判)

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
            # 局部条件 import 不保证本分支前已绑定(UnboundLocal 防御)
            import contextlib
            with contextlib.suppress(Exception):   # 遥测 best-effort
                recorder.record_exogenous(0, 'popup', detail='中断挑战dialog误触')
            _btn = self.round_by_find_and_click_area(
                screen, '货币战争-中断挑战弹窗', '按钮-关闭')
            if _btn.is_success:
                self.park_cursor(after_wait=0.1)
                return self.round_wait(wait=1.5)
            # X 点击失败兜底:ESC 同样关闭(实测无副作用)
            self.ctx.controller.esc()
            return self.round_wait(wait=1.5)

        # 战斗/结算窗口 → CwScreenBattleWait(W971 05-battle §1:原 1f/2/3/3b/5/6
        # 内联分支收编;三段式 = 等结算画面 / 结算处理(遥测读点 + 点继续挑战)
        # / 完成判据白名单;团灭终局分叉(多页 → 返回货币战争 → 大厅)交回本
        # 循环 3c 收口——runs summary/分配器/存档写端不随 op 化迁移,遥测
        # 连续性红线)。双入口:①出战驻留闩(出战成功置位);②帧锚(接管局/
        # relaunch 残留结算屏,等价旧「战斗中帧直接落 1f/2/3 分支」语义)。
        # op 返回后必经本 return → 下轮 loop 顶全分支重判(环让位重入契约)。
        if (self._battle_wait_active
                or self._frame_in_battle_window(screen)):
            self._settle.battle_ts = self._battle_ts
            _bw_res = self._battle_wait.execute()
            # ADR-0250:op 内已见结算屏 → 战斗窗口关(watch 恢复)
            if self._settle.saw_settlement:
                self._battle_ts = None
            _bw_ok = bool(_bw_res is not None and getattr(_bw_res, 'success', False))
            log.info('[cw-loop] 战斗等待返回(success=%s status=%s)→ 交回顶层分发'
                     '(下轮全分支重判)', _bw_ok,
                     getattr(_bw_res, 'status', '') or '')
            # 出口归一:白名单命中/终局/bail 都清闩(窗口单元结束);bail 帧
            # 交未知画面兜底链(超时兜底语义,裁决权留外循环)。
            self._battle_wait_active = False
            return self.round_wait(wait=1.0)
        # 3c. 回到大厅(对局结束)→ loop 完成,避免在 lobby 无动作无限 retry。
        # 用「创业指南」(大厅左菜单独有、无特殊括号,OCR 稳)而非「开始「货币战争」」(括号 gt 不稳)
        # (W971 05-battle §1:团灭终局链的终点由 CwScreenBattleWait 终局分叉交回此处
        # 收口——runs summary/分配器/存档/match 清理写端不随 op 化迁移。)
        if self.round_by_find_area(screen, '货币战争-大厅', '标识-创业指南').is_success:
            # r10 假局守卫:本 loop 从未记过 round_outcome(未打过任何一回合)却见大厅
            # = 开局失败/中断(第四局实证:开局失败回大厅 → 用旧 session 拼假 loss,
            # final_hp=100/rounds=2 全污染)。不记 summary、不喂分配器,仅清理 match。
            if self._settle.last_outcome_hp is None and self._settle.rounds_done == 0:
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
                # (值域守卫已在上游拒 8,此处双保险);且死局(本局见过战败结算屏)不判 win。
                _died_this_run = self._settle.saw_defeat_settlement
                _outcome = MatchOutcome(
                    won=(_st is not None and _st.plane == 3 and not _died_this_run),
                    final_plane=_st.plane if _st is not None else 1,
                    final_round=_st.round_num if _st is not None else 1,
                    final_hp=(_st.hp if _st is not None
                              and _st.hp is not None else 0),
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
                state.record_run_summary(
                    result='win' if _outcome.won else 'loss',
                    plane_reached=_outcome.final_plane,
                    rounds_survived=_outcome.final_round,
                    final_hp=self._last_true_hp(_outcome.final_hp),
                    notes='auto')
                self._summary_written = True
                # 按局存档装配(终局旁路,零运行时侵入):挂在 on_match_end
                # 调用点之后同一生命周期;只读 replay/*.jsonl 写 matches/,
                # 不碰任何内存态/决策路径,失败不阻塞局终收口。
                try:
                    from sr_od.application.currency_war.telemetry import match_archive
                    match_archive.assemble_pending(
                        state.get_recorder().replay_dir)
                except Exception as e:   # noqa: BLE001  观测旁路,best-effort
                    log.warning('[cw][archive] 局终装配失败(不阻塞): %s', e)
                self.ctx.cw_match = None
            return self.round_success('对局结束,回大厅')

        # 5. 前进按钮(简报等)
        if self.round_by_ocr_and_click(screen, '下一步', success_wait=2).is_success:
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
                from sr_od.application.currency_war.kernel.cw_comps import get_comp
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

    def _frame_in_battle_window(self, screen) -> bool:
        """帧锚:当前帧是否战斗/结算窗口画面(CwScreenBattleWait 第二入口)。

        覆盖接管局/relaunch 残留结算屏场景(闩未置位但画面已在战斗/结算窗
        口,等价旧「战斗中帧直接落 1f/2/3 分支」语义)。锚集 = 战斗/结算
        独有信号:继续挑战按钮/败局页模板/数据统计锚/点击空白加速/总伤害/
        前往结算·返回货币战争(终局链按钮,lcs 0.9 防「返回备战界面」子序列
        误匹配——同 3b 旧判据理由,lcs 收紧由位置唯一性兜底)。简报「下一步」
        不列(与终局链共享词形,误激活代价 = 白跑一窗口,宁缺勿造)。
        """
        return (
            self.round_by_find_area(screen, '货币战争-结算', '按钮-继续挑战',
                                    crop_first=False).is_success
            or self.round_by_find_area(screen, '货币战争-结算-失败', '标识-挑战结束',
                                       crop_first=False).is_success
            or self.round_by_find_area(screen, '货币战争-结算', '标识-数据统计',
                                       crop_first=False).is_success
            or self.round_by_ocr(screen, '点击空白加速').is_success
            or self.round_by_ocr(screen, '总伤害').is_success
            or self.round_by_ocr(screen, '前往结算', lcs_percent=0.9).is_success
            or self.round_by_ocr(screen, '返回货币战争', lcs_percent=0.9).is_success
        )

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
        if self._unknown_streak >= CwLoop.UNKNOWN_STOP_THRESHOLD:
            try:
                _shot = self.save_screenshot(prefix='cw_unknown')
                _sentinel = (get_project_root() / '.debug' / 'temp'
                             / 'currency_war' / 'unknown_state.flag')
                _sentinel.parent.mkdir(parents=True, exist_ok=True)
                _sentinel.write_text(
                    f'[HOOK-STOP] 持久未识别画面停机钩子([常驻兜底] loop 尾安全网):'
                    f'cw_loop._handle_unknown_fallback iter={self._iter} '
                    f'streak={self._unknown_streak}\n'
                    f'处理流程(r100k 补,别跳过):\n'
                    f'1. 用截图离线分析:analyze_screen(screenshot=<shot 路径>) 看已建档命中;\n'
                    f'2. 未命中 → 按元素语义判断:新画面/弹窗 → od-dev-screen-onboarding 建档\n'
                    f'   + cw_loop 0x 分支加 handler;战斗特效帧(OCR 乱码)→ **先确认\n'
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
            self.ctx.run_context.stop_running(reason='hook:battle_unknown_screen')
            return self.round_fail(status='持久未识别画面,停机待建档')
        # 连续未知帧退避(重试无退避缺陷修复):等待随 _unknown_streak 翻倍封顶;
        # 画面被任何分支接走 → streak 归 1,退避自动复位(见 UNKNOWN_RETRY_BACKOFF_CAP_S 注)。
        return self.round_retry(wait=self._unknown_backoff_wait(self._unknown_streak))

    @staticmethod
    def _unknown_backoff_wait(streak: int) -> float:
        """连续未识别帧第 ``streak`` 次(≥1,连续计数,归零复位)重试的等待秒数。

        2s 起步每连续一次翻倍、封顶 ``UNKNOWN_RETRY_BACKOFF_CAP_S``;纯函数便于锁测。
        """
        return min(2.0 * (2 ** (max(streak, 1) - 1)),
                   CwLoop.UNKNOWN_RETRY_BACKOFF_CAP_S)


# ===== B4(ADR-0170):跨局分配器进程级单例 + 终局 update =====
_ALLOCATOR = None          # 进程级(后验跨局累积;server 不重启跨局延续)


def _get_or_init_allocator(ctx: SrContext):
    """惰性建分配器(失败安全:建不出来 → None,update no-op)。plaza 份额先验。"""
    global _ALLOCATOR
    if _ALLOCATOR is not None:
        return _ALLOCATOR
    try:
        from sr_od.application.currency_war.data.cw_plaza_comps import (
            PLAZA_CARRY_CLUSTERS,
        )
        from sr_od.application.currency_war.kernel.cw_run_allocator import (
            ThompsonAllocator,
        )
        total = sum(max(c.n_posts, 0) for c in PLAZA_CARRY_CLUSTERS) or 1
        share = {c.carry: c.n_posts / total for c in PLAZA_CARRY_CLUSTERS if c.n_posts >= 15}
        _ALLOCATOR = ThompsonAllocator.from_plaza(share)
    except Exception as e:   # noqa: BLE001  影子期失败安全
        log.info(f'[cw-alloc] 分配器初始化失败(禁用): {e}')
        _ALLOCATOR = None
    return _ALLOCATOR

