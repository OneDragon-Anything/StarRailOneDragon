# 已 live 验(整局跑通多场 D-74~D-79 + 2026-08-12:EnterCW→StartMatch→RunLoop→结算→lobby 全 lifecycle 自主;_in_match resume 多锚含战斗/挑战成功/挑战结束,中间态接手不卡 entry)

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
from sr_od.application.currency_war.operations.cw_loop import CwLoop
from sr_od.application.currency_war.telemetry import defects, state
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext

# [停机钩子·常驻兜底,统一观察对账迭代 2026-09-16 §2.4;2026-09-16 框架化]
# 触发:GameState.observe() 观察覆盖 logic 值失配(逻辑态被实读证伪),
# 未命中豁免注册表 → stop_running(框架截图留证 + [stop] 日志行)。
# flag 文件与每局闩退役:事实载体 = 日志 + 缺陷台账行;stop_running 幂等
# + was_live 截图门天然防重复,闭包不再需要自维护闩。


def _build_reconcile_andon(ctx: SrContext) -> Callable[[dict], None]:
    """构造统一观察对账安灯闭包(装配段专用;模块级函数便于离线单测)。

    处置壳 = stop_running 一行(2026-09-16 框架化):截图留证由框架
    ``stop_running(save_screenshot=True)`` 承担,事实载体 = [stop] 日志行 +
    缺陷台账行(kernel 侧 _emit_defect 已落)。真失配 = 逻辑态被实读证伪
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
    → 对局循环到结束(`CwLoop`:备战 买/升等级/deploy/出战 + 多类事件 + 结算回大厅)。

    **中间态接手(,2026-08-04)**:app 不再总从大世界线性起 —— 各入口 op 先检测当前态,
    已在 CW(大厅/对局中)就跳过 enter/start、直接进 loop。故 bot crash/重启/手动接管后,
    从任何态(大世界 / 大厅 / 备战 / 事件 / 战斗 / 结算)重跑 app 都能 resume,不卡 entry。

    naive 策略 + 购买经验升等级,实测赢下位面 1、打完整两位面局(输位面 2 boss)。
    打赢更高难度需 Strategy 精修(羁绊/经济/deploy 智能化,见 design.md)。
    """

    STATUS_AT_LOBBY: ClassVar[str] = CwEntryEnter.STATUS_AT_LOBBY

    # 对局中态 OCR 锚点(备战 / 事件 overlay / 战斗 / 结算)—— 命中任一 = 已在对局里,跳过 enter+start
    _IN_MATCH_KEYWORDS: ClassVar[tuple[str, ...]] = (
        '购买经验', '备战阶段', '投资策略', '投资环境', '补给阶段',
        '遭遇其一', '盛会之星', '出战', '挑战结束', '挑战成功', '请选择投资',
        '总伤害', '敌方行动中', '我方行动中',  # 战斗屏(对局中,防 _in_match 漏判 → 重进大厅卡,2026-08-12)
        '简易武装箱',  # 节点武装箱弹窗(盖底层屏,OCR 只见弹窗文字;M19 停机重启曾漏判 → 误走 enter 链「返回普通大世界」连点关掉弹窗,2026-08-15)
        '星徽秘典', '返回投资策略选择',   # 星徽秘典道具详情弹窗(盖投资策略/备战,M34 实锤:OCR 只见弹窗文字 → _in_match 漏判 → enter 链循环点右上角[overlay 的返回位]8min);返回投资策略选择=备战屏对局中独有右上按钮
        '挑战失败',   # 挑战失败终局结算屏(对局评价/下一步;M42 实锤 2026-08-16:M41 战败后 app 重启,_in_match 漏判 → 误走 enter 链「返回普通大世界」循环点右上角;loop 3b「返回货币战争」同收局)
    )

    # ⚖️ 治本(2026-08-17,M19/M34/M42 关键词补丁链的结构替代):对局中态检测升级为
    # **screen_info 画面匹配**(货币战争- 前缀 − 大厅态白名单)——新对局画面建档即自动生效,
    # 不再靠事后补关键词(每漏一个新屏 = enter 链「返回普通大世界」死循环 ~8min)。
    # 关键词保留为 fallback(id_mark 未全中的半开/过渡帧)。
    # 对局中画面判定单一源已平移至 cw_screen_state(前缀 + 白名单 + 过滤逻辑),
    # 本类方法仅委托——供既有测试(经类方法调用)与内部消费保持同一入口。

    # 启动恢复态预检锚(局10/11 实证):上局中途停机后客户端可能停在「战斗暂停/
    # 关卡信息」面板(进度保留态,含 撤退/重新挑战/继续战斗)。识别用「战斗暂停」
    # 独有文本锚 —— 同屏的「关卡信息」与 敌人信息浮层 的标识文本撞车(2026-08-30
    # 离线 analyze 实证:暂停面板帧被精准匹配为 货币战争-敌人信息浮层),不能作判据。
    PAUSE_SCREEN: ClassVar[str] = '货币战争-战斗暂停'
    PAUSE_MARK: ClassVar[str] = '标识-战斗暂停'

    @classmethod
    def in_match_screen_names(cls, screen_info_list) -> list[str]:
        """对局中态屏名。判定单一源 = ``cw_screen_state.in_match_screen_names``
        (货币战争- 前缀 − 大厅态白名单);本方法仅委托,签名/行为不变
        (既有测试锁经类方法调用)。
        """
        return cw_screen_state.in_match_screen_names(screen_info_list)

    def __init__(self, ctx: SrContext):
        # 分包期 4 出口钩子武装(幂等):kernel/obs/decision 三桶的 telemetry
        # 上行出口(落账/run_id 归属键)经 kernel/cw_telemetry_exit 钩子位
        # 转发,缺省关;生产在此接通。
        defects.install_exit_hooks()
        # 分包期 5 obs 读口注入(幂等):decision/kernel 桶禁直依 obs,新局弃置
        # 残留容器时的 obs last-known-good 缓存清理与对账合成特效帧态门
        # (kernel/cw_reconcile)经 decision_assembly 装配点接通
        # (缺省关=跳过缓存清理/门放行;session 全量重建承担状态隔离)。
        from sr_od.application.currency_war.decision_assembly import install_obs_ports
        install_obs_ports()
        # R1 统一 state 状态流水武装(幂等):删除波 1(用户 2026-09-10 直迁
        # 裁定「journal 无条件常开,无 state_journal flag」)后装配段无条件
        # 武装——旧 12 流中收编 9 流的写入端已删,journal 是流程侧唯一落盘流。
        # run 归属读取函数在此注入(kernel 禁依 telemetry,依赖倒置;同
        # 出口钩子的装配点显式接通纪律)。
        from sr_od.application.currency_war.kernel.cw_state_journal import (
            install_state_telemetry,
        )
        install_state_telemetry(run_id_provider=state.current_run_id)
        # 统一观察对账安灯武装(幂等;迭代 2026-09-16-unified-obs-reconcile
        # §2.4;2026-09-16 框架化:处置壳 = stop_running 一行,截图归框架):
        # 真失配缺陷行 → 停机;kernel 槽缺省关,生产在此与出口钩子同点接通。
        set_reconcile_andon_hook(_build_reconcile_andon(ctx))
        # obs_event 收编制 GameState 供给(kernel 禁自寻会话;观察冲突证据
        # 行型 2 的宿主供给,与 run_id provider 同点注入)。
        from sr_od.application.currency_war.kernel import cw_telemetry_exit
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
        """已在货币战争大厅(「创业指南」大厅独有锚点,lobby screen_info area)。"""
        return self.round_by_find_area(screen, CwEntryEnter.LOBBY_SCREEN, '标识-创业指南').is_success

    def _in_match(self, screen) -> bool:
        """已在货币战争对局中(备战/事件/战斗/结算任一态)。

        双层:①screen_info 画面匹配(治本,新屏建档即生效);②关键词 fallback(半开/过渡帧)。
        """
        # 大厅不是对局中态:防 _IN_MATCH_KEYWORDS 短词(如「出战」)round_by_ocr 默认 lcs 0.5
        # 误匹配大厅文字(「货币战争」含「战」→「出战」1/2=0.5 命中)→ _start_match 误判已在对局 →
        # 跳过 start 交 loop → loop 见大厅「创业指南」→ 误「对局结束」2.4s 空跑(2026-08-06 实跑)。
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
        # ② 关键词 fallback(历史行为保留):真在对局时这些锚点 OCR 干净 4/4 命中。
        return any(self.round_by_ocr(screen, kw, lcs_percent=0.8).is_success for kw in self._IN_MATCH_KEYWORDS)

    def _recover_if_paused(self, screen) -> OperationRoundResult | None:
        """启动恢复态预检:命中「战斗暂停」面板 → 走退局链回大厅再正常起跑。

        恢复链委托 CwEntryExit(撤退 → 中断挑战弹窗「放弃并结算」→
        失败结算页「下一步」→ 大厅锚确认;编排者手动实机验证过的范式,op 内
        r279/r302 实测同链)。该 op 的成功出口唯一 = 大厅锚命中,回大厅确认由
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
