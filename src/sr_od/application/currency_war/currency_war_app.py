# 已 live 验(整局跑通多场 D-74~D-79 + 2026-08-12:EnterCW→StartMatch→RunLoop→结算→lobby 全 lifecycle 自主;_in_match resume 多识别标志含战斗/挑战成功/挑战结束,中间态接手不卡 entry)

from collections.abc import Callable
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import currency_war_const, cw_screen_state
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.currency_war_run_record import CurrencyWarRunRecord
from sr_od.application.currency_war.kernel.cw_mismatch_policy import (
    set_reconcile_andon_hook,
)
from sr_od.application.currency_war.operations.cw_entry.cw_entry_enter import (
    CwEntryEnter,
)
from sr_od.application.currency_war.operations.cw_entry.cw_entry_exit import (
    CwEntryExit,
)
from sr_od.application.currency_war.operations.cw_entry.cw_entry_start import (
    CwEntryStart,
    try_handle_entry_popups,
)
from sr_od.application.currency_war.operations.cw_loop import (
    STATUS_HANDOFF_PREFIX,
    STATUS_LOBBY_DONE,
    CwLoop,
)
from sr_od.application.currency_war.telemetry import state
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext

# [停机钩子·常驻兜底;设计 = 统一观察对账迭代设计 §2.4]
# 触发:GameState.observe() 观察覆盖 logic 值失配(逻辑态被实读证伪),
# 未命中豁免注册表 → stop_running(框架截图保留证据 + [stop] 日志行)。
# flag 文件与每局标志停用:事实载体 = 日志 + gs 缺陷行(buffer/sink 面,
# kernel _emit_defect);stop_running 幂等
# + was_live 截图门天然防重复,闭包不再需要自维护标志。


def _build_reconcile_andon(ctx: SrContext) -> Callable[[dict], None]:
    """构造统一观察对账失配告警闭包(装配段专用;模块级函数便于离线单测)。

    处置壳 = stop_running 一行:截图保留证据由框架
    ``stop_running(save_screenshot=True)`` 承担,事实载体 = [stop] 日志行 +
    gs 缺陷行(kernel 侧 _emit_defect 已落 buffer/sink)。真失配 = 逻辑态被实读证伪
    = bug,停机现场修推算代码(处置协议归 guards.md / game_state README)。
    """
    def _andon(row: dict) -> None:
        log.warning('[cw!][andon] 观察对账真失配: 字段=%s 逻辑=%s 实读=%s',
                    row.get('field'), row.get('expected'), row.get('actual'))
        ctx.run_context.stop_running(reason='hook:reconcile_mismatch',
                                     save_screenshot=True)
    return _andon


class CurrencyWarApp(SrApplication):
    """货币战争应用。纯代码自主打完整局(无 LLM,实机验证):

    大世界 → 货币战争大厅(`CwEntryEnter`)→ 开始对局到备战(`CwEntryStart`)
    → 对局循环到结束(`CwLoop`:备战 买/升等级/deploy/出战 + 多类事件 + 结算回大厅)
    → 退出收尾(交接节点:弹窗守卫 + `CwEntryExit` 退局/大厅确认;debug 停点
    留局与假局守卫形态跳过退出,非 debug 停点走交接退局回大厅)。

    **中间态接手**:app 不再总从大世界线性起 —— 各入口 op 先检测当前态,
    已在 CW(大厅/对局中)就跳过 enter/start、直接进 loop。故 bot crash/重启/手动接管后,
    从任何态(大世界 / 大厅 / 备战 / 事件 / 战斗 / 结算)重跑 app 都能 resume,不卡 entry。

    naive 策略 + 购买经验升等级,实测赢下位面 1、打完整两位面局(输位面 2 boss)。
    打赢更高难度需 Strategy 精修(羁绊/经济/deploy 智能化)。
    """

    STATUS_AT_LOBBY: ClassVar[str] = CwEntryEnter.STATUS_AT_LOBBY

    # 对局中态 OCR 识别标志(备战 / 事件 overlay / 战斗 / 结算)—— 命中任一 = 已在对局里,跳过 enter+start
    _IN_MATCH_KEYWORDS: ClassVar[tuple[str, ...]] = (
        '购买经验', '备战阶段', '投资策略', '投资环境', '补给阶段',
        '遭遇其一', '盛会之星', '出战', '挑战结束', '挑战成功', '请选择投资',
        '总伤害', '敌方行动中', '我方行动中',  # 战斗屏(对局中,防 _in_match 漏判 → 重进大厅卡)
        '武装箱',  # 节点武装箱弹窗(盖底层屏,OCR 只见弹窗文字;M19:停机重启后 _in_match 漏判 → 误走 enter 链「返回普通大世界」连点关掉弹窗)。族名关键词:简易/特权弹窗标题同命中(lcs_percent=0.8 下 LCS(武装箱,标题)=3 ≥ 3×0.8)
        '星徽秘典', '返回投资策略选择',   # 星徽秘典道具详情弹窗(盖投资策略/备战,M34 已实测确认:OCR 只见弹窗文字 → _in_match 漏判 → enter 链循环点右上角[overlay 的返回位]8min);返回投资策略选择=备战屏对局中独有右上按钮
        '挑战失败',   # 挑战失败终局结算屏(对局评价/下一步;M42 已实测确认:M41 战败后 app 重启,_in_match 漏判 → 误走 enter 链「返回普通大世界」循环点右上角;loop 3b「返回货币战争」同收局)
    )

    # ⚖️ 治本(M19/M34/M42 关键词补丁的结构性替代):对局中态检测升级为
    # **screen_info 画面匹配**(货币战争- 前缀 − 大厅态白名单)——新对局画面建档即自动生效,
    # 不再靠事后补关键词(每漏一个新屏 = enter 链「返回普通大世界」死循环 ~8min)。
    # 关键词保留为 fallback(id_mark 未全中的半开/过渡帧)。
    # 对局中画面判定单一源已平移至 cw_screen_state(前缀 + 白名单 + 过滤逻辑),
    # 本类方法仅委托——供既有测试(经类方法调用)与内部消费保持同一入口。

    # 启动恢复态预检识别标志(局10/11 实证):上局中途停机后客户端可能停在「战斗暂停/
    # 关卡信息」面板(进度保留态,含 撤退/重新挑战/继续战斗)。识别用「战斗暂停」
    # 独有文本识别标志 —— 同屏的「关卡信息」与 敌人信息浮层 的标识文本撞车(2026-08-30
    # 离线 analyze 实证:暂停面板帧被精准匹配为 货币战争-敌人信息浮层),不能作判据。
    PAUSE_SCREEN: ClassVar[str] = '货币战争-战斗暂停'
    PAUSE_MARK: ClassVar[str] = '标识-战斗暂停'

    @classmethod
    def in_match_screen_names(cls, screen_info_list) -> list[str]:
        """对局中态屏名。判定单一源 = ``cw_screen_state.in_match_screen_names``
        (货币战争- 前缀 − 大厅态白名单);本方法仅委托,签名/行为不变
        (既有测试经类方法调用)。
        """
        return cw_screen_state.in_match_screen_names(screen_info_list)

    def __init__(self, ctx: SrContext):
        # 出口钩子武装(幂等):kernel/obs/decision 三桶的 telemetry
        # 上行出口(run_id 归属键)经 kernel/cw_telemetry_exit 钩子位
        # 转发,缺省关;生产在此接通。(缺陷台账落账出口已随缺陷台账
        # 废弃拆除——现役注入面只剩 run_id provider;观察冲突证据归宿 =
        # journal obs_event 行,不依赖本注入。)
        from sr_od.application.currency_war.kernel import cw_telemetry_exit
        cw_telemetry_exit.install_exit_hooks(run_id_provider=state.current_run_id)
        # obs 读口注入(幂等):decision/kernel 层禁直依 obs,新局弃置
        # 残留状态容器时的 obs last-known-good 缓存清理与对账合成特效帧态门
        # (kernel/cw_reconcile)经 decision_assembly 装配点接通
        # (缺省关=跳过缓存清理/门放行;session 全量重建承担状态隔离)。
        from sr_od.application.currency_war.decision_assembly import install_obs_ports
        install_obs_ports()
        # 统一 state 状态流水武装(幂等):用户裁定 journal 无条件常开(无
        # state_journal flag),装配段无条件武装——旧 12 流中 9 流已并入
        # journal(旧写入端已删),journal 是流程侧唯一落盘流。
        # run 归属读取函数在此注入(kernel 禁依 telemetry,依赖倒置;同
        # 出口钩子的装配点显式接通纪律)。
        from sr_od.application.currency_war.kernel.cw_state_journal import (
            install_state_telemetry,
        )
        install_state_telemetry(run_id_provider=state.current_run_id)
        # 统一观察对账失配告警武装(幂等;处置壳 = stop_running 一行,截图归框架):
        # 真失配缺陷行 → 停机;kernel 槽缺省关,生产在此与出口钩子同点接通。
        set_reconcile_andon_hook(_build_reconcile_andon(ctx))
        # obs_event 并入 GameState 供给(kernel 禁自寻会话;观察冲突证据
        # 行型 2 的宿主供给,与 run_id provider 同点注入)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of,
        )

        def _obs_event_board():
            _sess = getattr(getattr(self.ctx, 'cw_match', None),
                            'session', None)
            return game_state_of(_sess) if _sess is not None else None

        cw_telemetry_exit.set_obs_event_board_provider(_obs_event_board)
        SrApplication.__init__(
            self, ctx, currency_war_const.APP_ID,
            op_name=gt('货币战争', 'game'),
            run_record=CurrencyWarRunRecord(ctx.current_instance_idx),
        )

    def _at_lobby(self, screen: MatLike) -> bool:
        """已在货币战争大厅(「货币战争」玩法名标题,赛季无关稳定锚,lobby screen_info area)。"""
        return self.round_by_find_area(screen, CwEntryEnter.LOBBY_SCREEN, '标识-玩法名').is_success

    def _in_match(self, screen) -> bool:
        """已在货币战争对局中(备战/事件/战斗/结算任一态)。

        三层:①screen_info 画面匹配(治本,新屏建档即生效);①b 大厅态白名单
        精确命中短路(已知的非对局建档屏直接判否,不进关键词层);②关键词
        fallback(半开/过渡帧)。判定序约定:精确建档命中(任一方向)优先于
        关键词启发式。
        """
        # 大厅不是对局中态:防 _IN_MATCH_KEYWORDS 短词(如「出战」)round_by_ocr 默认 lcs 0.5
        # 误匹配大厅文字(「货币战争」含「战」→「出战」1/2=0.5 命中)→ _start_match 误判已在对局 →
        # 跳过 start 交 loop → loop 见大厅识别标志 → 误「对局结束」2.4s 空跑(2026-08-06 实跑)。
        if self._at_lobby(screen):
            return False
        # ① 画面匹配层:已建档对局屏(备战系/事件系/战斗系/结算系/警告系/难度确认)。
        # 难度确认 = start 流已开对局(点开始后),归对局中。
        _in_match_screens = self.in_match_screen_names(self.ctx.screen_loader.screen_info_list)
        if _in_match_screens:
            try:
                from one_dragon.base.screen.screen_utils import get_match_screen_name
                if get_match_screen_name(self.ctx, screen, screen_name_list=_in_match_screens) is not None:
                    return True
            except Exception:  # noqa: BLE001  画面匹配失败退关键词层,不阻塞启动
                pass
        # ①b 白名单短路:对局前建档屏(数据银行/图鉴族/难度确认等,LOBBY_STATE_SCREENS)对①层
        # 不可见(①层名单 = 前缀 − 白名单),不短路即落②层——数据银行页带「投资策略图鉴」字样
        # 被关键词命中误判对局中 → 单跑 app 跳过 start 交 loop,对局循环跑在图鉴页上。
        # 上方 _at_lobby 是本层的大厅单例快路径,本层是其全白名单推广。
        if cw_screen_state.get_lobby_state_screen_name(self.ctx, screen) is not None:
            return False
        # ② 关键词 fallback(历史行为保留):真在对局时这些识别标志 OCR 干净 4/4 命中。
        return any(self.round_by_ocr(screen, kw, lcs_percent=0.8).is_success for kw in self._IN_MATCH_KEYWORDS)

    def _recover_if_paused(self, screen) -> OperationRoundResult | None:
        """启动恢复态预检:命中「战斗暂停」面板 → 走退局链回大厅再正常起跑。

        恢复链委托 CwEntryExit(撤退 → 中断挑战弹窗「放弃并结算」→
        失败结算页「下一步」→ 大厅识别标志确认;编排者手动实机验证过的范式,op 内
        r279/r302 实测同链)。该 op 的成功出口唯一 = 大厅识别标志命中,回大厅确认由
        它承担;成功后回到调用节点的常规判定继续启动流。未命中返回 None(零
        额外动作,正常启动只多一次小区域 OCR 查找)。
        """
        if not self.round_by_find_area(screen, self.PAUSE_SCREEN, self.PAUSE_MARK).is_success:
            return None
        log.info('[cw-app] 启动预检:命中战斗暂停面板(上局残留恢复态)→ 走退局链回大厅')
        op = CwEntryExit(self.ctx)
        return self.round_by_op_result(op.execute())

    @operation_node(name='进入货币战争大厅', is_start_node=True)
    def _enter_lobby(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # 入口链弹窗守卫最先接(注册表统一入口,supply→jade→badge 序位见
        # cw_entry_start.ENTRY_POPUP_GUARDS;/):弹窗盖在大世界
        # 上,早于一切 CW 导航识别——模态压暗+模糊背景下 _recover 预检/_at_lobby/
        # _in_match 全部失明,不接住则 enter 链空烧预算。
        popup = try_handle_entry_popups(self, screen)
        if popup is not None:
            return popup
        # 预检必须在 _in_match 之前:战斗暂停屏带 货币战争- 前缀,会被 _in_match
        # 判成「已在对局中」跳过 enter/start 交 loop,而 loop 不识该面板(局10/11 死因)。
        recover_result = self._recover_if_paused(screen)
        if recover_result is not None:
            return recover_result
        if self._at_lobby(screen) or self._in_match(screen):
            return self.round_success('已在 CW(大厅/对局中),跳过 enter')
        op = CwEntryEnter(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='进入货币战争大厅')
    @operation_node(name='开始对局到备战阶段')
    def _start_match(self) -> OperationRoundResult:
        # 起局前置码哈希结构闸(混合码事故防线):工作树≠HEAD 的
        # 码面不允许起局——run 记录会以本失败状态收尾,不一致清单进日志。
        # 闸关(config.code_hash_gate=False)时整段跳过。
        _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
        if _cfg.code_hash_gate:
            from sr_od.application.currency_war.kernel.cw_code_hash_gate import (
                check_workspace_matches_head,
            )
            _gate = check_workspace_matches_head()
            if not _gate.ok:
                log.error(f'[cw][code-hash-gate] 起局拒绝:{_gate.reason} '
                          f'不一致码面={_gate.mismatches}')
                return self.round_fail(
                    f'起局拒绝:代码哈希闸检出工作树与 HEAD 不一致 '
                    f'{len(_gate.mismatches)} 个文件(详见日志)')
        screen = self.last_screenshot
        # 同 _enter_lobby:面板残留时的防御性预检(_enter_lobby 截图后画面才
        # 落到暂停面板的边缘情形),未命中零开销。
        recover_result = self._recover_if_paused(screen)
        if recover_result is not None:
            if recover_result.is_success:
                # 不直落 success 边(下一节点是 loop,而此刻人在大厅)—— round_wait
                # 重跑本节点,走大厅 → CwEntryStart 正常起跑链。
                return self.round_wait(status='恢复完成已回大厅,重走 start 链')
            return recover_result
        if self._in_match(screen):
            return self.round_success('已在对局中,跳过 start 交 loop')
        op = CwEntryStart(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='开始对局到备战阶段')
    @operation_node(name='对局循环到结束')
    def _run_loop(self) -> OperationRoundResult:
        _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
        op = CwLoop(self.ctx, max_rounds=_cfg.max_rounds)
        return self.round_by_op_result(op.execute())

    # 交接节点重试预算口径:守卫注册表现 4 条,最坏全叠 = 每层 1 轮守卫动作
    # + 点击偶发不落地 ×2 余量 = 8 轮;再留 1 倍余量取 16。预算只在守卫命中轮
    # 消耗(round_retry),未命中轮落 exit 段或跳过分支即非 RETRY 出口,
    # 框架归零计数,不为无弹窗场景白付。框架缺省 3 次不够多层弹窗叠加。
    EXIT_NODE_RETRY: ClassVar[int] = 16

    @node_from(from_name='对局循环到结束')
    @operation_node(name='退出收尾', node_max_retry_times=EXIT_NODE_RETRY)
    def _exit_cleanup(self) -> OperationRoundResult:
        """交接节点(loop→exit 交接):对局循环结束后把「该退出但还没退」的
        状态移交 CwEntryExit 处置。

        三形态判定,载体 = ``self._previous_round_result.status``(框架在节点
        转移时写入;WAIT/RETRY 重入不覆盖,守卫段重试不污染载体;带动态后缀
        的结束文本不能走节点边文本全等,故读上一轮结果对象):
        - 大厅完成(STATUS_LOBBY_DONE):游戏已回大厅 → exit 大厅确认形态
          (幂等确认,无弹窗压制时近 no-op);
        - 异常交接(STATUS_HANDOFF_PREFIX 前缀;来源 = loop 外环 fail-streak
          耗尽的交接出口,或非 debug 停点的交接弃局出口):残局留在对局内 →
          exit 按当前画面路由清场退局(备战点门/战斗退局范式/其余画面委托
          loop 清理),exit 不区分形态传参;
        - 其余(max_rounds 停备战留局采样,仅 is_debug=True / 假局守卫开局
          失败-中断〔已在大厅且对局状态已清〕)→ 跳过退出直接结束。
        loop fail(看门狗/框架超时/未捕获/未知兜底)不经本节点:success 边才
        入,fail 无匹配出边 = app 失败收尾(残局下次启动预检兜底)。

        两段式:守卫段复用进局链弹窗守卫注册表 ENTRY_POPUP_GUARDS,清掉局末
        自动弹、会压住 exit 识别的弹窗(不守卫则 exit 识别全落空误入战斗链)
        → exit 调用段。两交接形态 exit 成功后置 ``ctx.cw_match = None``
        (兜底清理点:分层清理口径的 app 层,幂等;同进程下一局 CwLoop 兜底建
        判据 ``ctx.cw_match is None`` 的前提)。exit 调用失败或守卫预算耗尽
        → 本节点 FAIL → 无出边 → app 失败收尾(与硬失败同型,残局可见)。
        """
        prev = self._previous_round_result
        prev_status = prev.status if prev is not None else None
        is_handoff = (prev_status is not None
                      and prev_status.startswith(STATUS_HANDOFF_PREFIX))
        if prev_status != STATUS_LOBBY_DONE and not is_handoff:
            return self.round_success(f'非退出交接形态,跳过退出({prev_status})')
        screen = self.last_screenshot
        popup = try_handle_entry_popups(self, screen)
        if popup is not None:
            return popup
        op = CwEntryExit(self.ctx)
        result = self.round_by_op_result(op.execute())
        if result.is_success:
            self.ctx.cw_match = None
        return result
