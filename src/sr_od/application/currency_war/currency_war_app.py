# 已 live 验(整局跑通多场 D-74~D-79 + 2026-08-12:EnterCW→StartMatch→RunLoop→结算→lobby 全 lifecycle 自主;_in_match resume 多锚含战斗/挑战成功/挑战结束,中间态接手不卡 entry)

import contextlib
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.debug_utils import save_debug_image
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import currency_war_const, cw_screen_state
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.currency_war_run_record import CurrencyWarRunRecord
from sr_od.application.currency_war.kernel.cw_game_state import current_run_id_safe
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

# [停机钩子·常驻兜底,统一观察对账迭代 2026-09-16 §2.4]
# 触发:GameState.observe() 观察覆盖 logic 值失配(逻辑态被实读证伪),
# 未命中豁免注册表 → 截图留证 + 停机 flag + 协作式停机。

#: 哨兵 flag 路径(仓根锚定绝对路径:daemon spawn 的非 CWD 进程里相对路径
#: 会落错,教训先例 = run_state._EXEC_FAIL_FLAG_RELPATH 注释)。
_RECONCILE_ANDON_FLAG_RELPATH = Path('.debug') / 'temp' / 'cw_reconcile_andon.flag'


def reconcile_andon_flag_path() -> Path:
    """哨兵 flag 绝对路径(锚仓根,经 get_project_root 定位;测试经
    闭包工厂参数注入 tmp_path)。"""
    return get_project_root() / _RECONCILE_ANDON_FLAG_RELPATH


def write_reconcile_andon_flag(flag_path: Path, *, run_id: str,
                               row: dict) -> str:
    """写停机 flag(纯 IO,可单测;内容锁 od-dev-stop-hooks 三要素)。

    三要素:触发定位([HOOK-STOP] + 失配行全维度)/ 可执行处理步骤(两
    原因排查,归因一手数据 = journal 行)/ 移除条件(常驻兜底——单次
    触发只删 flag;机制性差异走豁免申报,不留开关)。返回写入内容(测试
    断言用)。
    """
    content = (
        '[HOOK-STOP] 观察对账安灯(真失配停机;统一观察对账迭代 2026-09-16)\n'
        '触发:GameState.observe() 观察覆盖 logic 值失配 = 逻辑态被实读证伪 = bug'
        '(此前观察态错 / 逻辑推算代码错),未命中豁免注册表。\n'
        f'定位:run_id={run_id} ts={row.get("ts")} 字段={row.get("field")} '
        f'画面={row.get("screen")} actor={row.get("actor")} '
        f'动作组={row.get("group_id")} 逻辑写端={row.get("logic_evidence")} '
        f'observed_evidence={row.get("observed_evidence")}\n'
        f'逻辑值(expected)={row.get("expected")} 实读(actual)={row.get("actual")}\n'
        f'截图:.debug/images/reconcile_andon_{run_id}_{row.get("field")}_*\n'
        '处理步骤:两原因排查——\n'
        ' 1. 此前的观察态错了:查 state/journal.jsonl 该字段前序写入行'
        '(行行自足,含渠道签名与质量元数据);\n'
        ' 2. 逻辑态推算代码错了:按 actor / 动作组 / 逻辑写端 evidence 定位'
        '写入点修推算。\n'
        ' 归因一手数据 = journal 行(expected/actual/evidence + 写入后完整'
        'state 快照)。\n'
        '移除条件:常驻兜底钩子——单次触发只删本 flag;差异长期确证属游戏'
        '机制性结构 → 走豁免申报进 kernel/cw_mismatch_policy.EXEMPT_REGISTRY'
        '(带 reason),不留开关。\n'
    )
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text(content, encoding='utf-8')
    return content


def _build_reconcile_andon(ctx: SrContext, latch: dict[str, bool],
                           flag_path: Path) -> Callable[[dict], None]:
    """构造统一观察对账安灯闭包(装配段专用;模块级函数便于离线单测)。

    触发契约(kernel 侧逐行同步调用):真失配缺陷行 → 截图留证(失败不
    拦 flag/停机;flag 是主哨兵)→ 每局一闩(键 run_id,同局第二失配跳过)
    → 写三要素 flag → ``run_context.stop_running`` 协作式停机(当前节点
    收尾后外循环退出,被证伪的逻辑态不再喂下一个决策)。run_id 空(局外)
    = 只落证不停机,不写假局 flag(与 journal 局外拒写假行同向);
    ``flag_path`` 参数供测试注入 tmp_path。"""
    def _andon(row: dict) -> None:
        run_id = current_run_id_safe()
        field = str(row.get('field') or 'unknown')
        with contextlib.suppress(Exception):
            # 契约解包(screenshot 返回 (ts, MatLike|None) 元组;independent
            # =独立抓帧,防安灯触发刷新共享截图态,先例 = cw_observe.
            # _save_andon_frame)。
            _ts, frame = ctx.controller.screenshot(independent=True)
            if frame is not None:
                save_debug_image(frame,
                                 prefix=f'reconcile_andon_{run_id}_{field}')
        if not run_id:
            return   # 局外:只落证不停机(不写假局 flag)
        if latch.get(run_id):
            return
        latch[run_id] = True
        write_reconcile_andon_flag(flag_path, run_id=run_id, row=row)
        log.warning('[cw!][andon] 观察对账真失配停机: 字段=%s 逻辑=%s 实读=%s '
                    '(现场 flag=cw_reconcile_andon.flag)',
                    row.get('field'), row.get('expected'), row.get('actual'))
        rc = getattr(ctx, 'run_context', None)
        if rc is not None:
            rc.stop_running(reason='hook:reconcile_mismatch')
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
        # L0 安灯停线的生产武装点(显式注册,幂等):停线副作用缺省关、在此
        # 接通——缺省惰性接真实现会让测试进程漏桩时被 gc 扫描命中 session 级
        # test_context 写停机位(w505 全集假红实证,见 cw_telemetry 槽注释)。
        from sr_od.application.currency_war.kernel.cw_observe import stop_for_l0_andon
        state.set_l0_andon_handler(stop_for_l0_andon)
        # 分包期 4 出口钩子武装(幂等):kernel/obs/decision 三桶的 telemetry
        # 上行出口(落账/安灯/run_id 归属键)经 kernel/cw_telemetry_exit 钩子位
        # 转发,缺省关;生产在此与安灯执行器同点接通。
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
        # run 归属读取函数在此注入(kernel 禁依 telemetry,依赖倒置;同 L0
        # 安灯/出口钩子的装配点显式接通纪律)。
        from sr_od.application.currency_war.kernel.cw_state_journal import (
            install_state_telemetry,
        )
        install_state_telemetry(run_id_provider=state.current_run_id)
        # 统一观察对账安灯武装(幂等;迭代 2026-09-16-unified-obs-reconcile
        # §2.4):真失配缺陷行 → 截图留证 + 停机 flag + 协作式停机,每局
        # 一闩;kernel 槽缺省关,生产在此与 L0 安灯/出口钩子同点接通。
        set_reconcile_andon_hook(
            _build_reconcile_andon(ctx, {}, reconcile_andon_flag_path()))
        # obs_event 收编制 GameState 供给(kernel 禁自寻会话;观察冲突证据
        # 行型 2 的宿主供给,与 run_id provider 同点注入)。
        from sr_od.application.currency_war.kernel import cw_telemetry_exit
        from sr_od.application.currency_war.kernel.cw_game_state import (
            board_state_of,
        )

        def _obs_event_board():
            _sess = getattr(getattr(self.ctx, 'cw_match', None),
                            'session', None)
            return board_state_of(_sess) if _sess is not None else None

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
        # cw_entry_start.ENTRY_POPUP_GUARDS;ADR-0574/ADR-0607):弹窗盖在大世界
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
        # 起局前置码哈希结构闸(ADR-0581;混合码事故防线):工作树≠HEAD 的
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
