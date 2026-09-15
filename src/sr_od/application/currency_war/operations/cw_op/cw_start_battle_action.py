"""出战动作 op(StartBattleOp)——备战域动作文件(统一动作工厂批3 体迁:
体自 ``prep_actions.py::PrepActionExecutor._start_battle`` 及其发射家族
(``_launch_attempt``/``_launch_dead_reset``/``_launch_dead_escalate``)
逐字迁移,原入口方法改薄委托保持替身缝,design.md unified-action-factory
§2.4)。

**基类契约在册例外**(例外登记口落款):``execute`` 返回值 = 发射位
**内部事实**(非恒 True;找不到按钮/未落地 = False),消费面 = runner
包络 ``last_launch_ok`` 旁路(cw_loop 发射链读点)与执行态写点
``exec_state.last_prep_battle_launch_ok``。退役挂账:判效/重发/停机面随
统一观察架构 A6(消费端退役时同退),本批体迁零行为。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import (
        PrepActionExecutor,
        PrepExecEnv,
    )


class StartBattleOp(ActionOp):
    """出战发射(常规发射 → 未落地原样重发(长按下) → 仍败计连败停机留证)。

    终结动作:发出即本备战访问终结(交回外循环战斗分支);终结等待 =
    ``terminal_wait``(消费点经注册表读类属性)。
    """

    terminal = True

    #: 终结交回等待秒数(与原决策循环 ``wait=3`` 逐字等价;等价测试锁 =
    #: test_cw_unified_action_3)。
    terminal_wait = 3

    def execute(self, env: PrepExecEnv) -> bool:
        """出战发射(体迁原 ``_start_battle``;返回值契约见类 docstring
        在册例外申报)。

        恢复语义(用户裁定 2026-08-30):禁用 active_window 激活——激活会抢占
        用户桌面焦点,自主推进运行期不可接受,无例外;重发=同通道原样重试。
        连续失败达限 → 停机留证(截图+flag+stop_running,与 bail ping-pong
        停机同款三要素),根因判定交人工:留证线索=输入投递机制状态
        (SendInput 落点 vs 真前台句柄)与游戏侧输入管线状态。
        """
        ex = env.executor
        ok, detail = self._start_battle(ex)
        env.detail = detail
        env.emitted = ok
        return ok

    def _start_battle(self, ex: PrepActionExecutor) -> tuple[bool, str]:
        """发射主链:常规发射 → 未落地原样重发(长按下) → 仍败计连败停机留证。"""
        ok, detail = self._launch_attempt(ex)
        if ok:
            self._launch_dead_reset(ex)
            return True, detail
        log.warning('[cw!][battle] 出战未落地(%s) → 原样重发(长按下)', detail)
        # 重发段 press_time=0.15:人工解锁实证参数(2026-08-30 16:31 手动 click_game
        # 0.15 即生效)——输入管线半死态下短按下可能不被采样,重发放长按下加固。
        ok2, detail2 = self._launch_attempt(ex, press_time=0.15)
        if ok2:
            self._launch_dead_reset(ex)
            return True, f'{detail2}(重发)'
        ex._op.save_screenshot()   # 诊断存证(同 battle_prep:bug#1 drag vs overlay 挡 vs 坐标偏)
        if '未落地' not in detail2:
            return False, f'出战失败(重发后): {detail2}'
        escalated = self._launch_dead_escalate(ex)
        if escalated is not None:
            return False, escalated
        return False, f'出战 click 未落地(重发后仍在备战;首次: {detail})'

    def _launch_attempt(self, ex: PrepActionExecutor,
                        press_time: float = 0.1) -> tuple[bool, str]:
        """单次发射尝试:找按钮 → mouse_move+click+失焦守卫 → 轮询转移。

        press_time:按下时长(秒);默认 0.1(框架 click 默认),重发段用
        0.15(人工解锁实证参数,防输入管线半死态短按下不被采样)。
        成功判据 = 备战标识消失(或未达上限警告弹出后确认完成且标识消失);
        轮询耗尽仍备战 = 未落地 → (False, detail),由调用方决定重发/失败。

        子态(2026-08-17 M72 实锤建档):「免战牌」策略激活时出战按钮变「跳过(N/N)」(直跳战斗,
        免战 2 次)——查不到「出战」时查子态「按钮-跳过」,同语义点它(推进节点)。

        ⚠️ 正交态查找(子态建模四问③,skill feedback 案例库):免战与「商店开」**可叠加**(跳过
        按钮 + 牌区展开同帧)——叠加帧识别为 货币战争-备战-开商店(它盖基态 id_mark),
        按单一屏查「按钮-跳过」会落空。跳过/出战按钮在两屏同一位置 → fallback 查找
        **不锁死单一屏**(备战+开商店都查);按钮 area 单源归备战屏,不复制双源。
        """
        from sr_od.application.currency_war.prep_actions import (
            PrepActionExecutor,
        )
        screen = ex._op.screenshot()
        _btn_area = '按钮-出战'
        _btn_screens: list[str] = [SCREEN_NAME, '货币战争-备战-开商店']
        _btn_found = any(
            ex._op.round_by_find_area(screen, _sc, '按钮-出战').is_success
            for _sc in _btn_screens)
        if not _btn_found:
            if any(ex._op.round_by_find_area(screen, _sc, '按钮-跳过', crop_first=False).is_success
                   for _sc in _btn_screens):
                _btn_area = '按钮-跳过'   # 免战牌子态:跳过=本节点直进(免战次数-1)
                log.info('[cw][battle] 出战按钮为子态「跳过」(免战牌激活)→ 点跳过')
            else:
                return False, '找不到出战按钮'
        btn = area_center(ex._ctx, _btn_area)
        if btn is None:
            # area 缺失 = 建档漂移,显式失败禁兜底坐标(坐标单一真相源)。
            # (False, 非「未落地」detail)→ 重发后立即判败上交,
            # 不进连败停机环(area 缺失是确定性失败,重发无意义)。
            return False, f'area 缺失:{_btn_area}({SCREEN_NAME}),禁兜底坐标'
        ex._ctx.controller.mouse_move(btn)   # bug#1 缓解(2026-08-06 r9 实打出战 click ×4 未落地)
        ex._ctx.controller.click(btn, press_time=press_time)
        # r9 失焦守卫:click 后验窗口焦点,失焦 → game_win.active() 激活 + 重点一次
        # (live 实证 2026-08-18:窗口后台化时输入静默丢,截图正常 → 环僵尸 20min;
        # MCP click 激活后立即恢复。active() 是框架窗口原语,见 pc_game_window)。)
        try:
            time.sleep(0.4)
            if not ex._ctx.controller.game_win.is_win_active:
                log.warning('[cw!][battle] 窗口失焦(输入静默丢)→ 激活 + 重试出战')
                ex._ctx.controller.game_win.active()
                time.sleep(0.3)
                ex._ctx.controller.mouse_move(btn)
                ex._ctx.controller.click(btn, press_time=press_time)
        except Exception:   # noqa: BLE001  焦点守卫 best-effort(无窗口对象则跳过)
            pass
        for _ in range(6):   # 6 × 0.5s 轮询窗口(同 battle_prep D-70)
            time.sleep(0.5)
            scr = ex._op.screenshot()
            if ex._op.round_by_find_area(scr, '货币战争-未达上限警告', '标识-未达上限警告').is_success:
                # M16 死循环根因修复(ADR-0136):只点确认不勾「本局不再提示」→ 人口不足时**每次**出战
                # 都弹此窗;确认后若弹窗未消(点击落空/动画)轮询重进 → 外层判"仍在备战"=fail → 死循环 86min。
                # 对齐 CwScreenDeployNotFull 完整行为:勾选(幂等,已勾无害)→ 确认 → 下轮验消失。
                check = area_center(ex._ctx, '勾选-本局不再提示',
                                    '货币战争-未达上限警告')
                if check is None:
                    return False, ('area 缺失:勾选-本局不再提示'
                                   '(货币战争-未达上限警告),禁兜底坐标')
                ex._ctx.controller.mouse_move(check)
                ex._ctx.controller.click(check)
                time.sleep(0.3)
                confirm = area_center(ex._ctx, '按钮-确认',
                                      '货币战争-未达上限警告')
                if confirm is None:
                    return False, ('area 缺失:按钮-确认'
                                   '(货币战争-未达上限警告),禁兜底坐标')
                ex._ctx.controller.mouse_move(confirm)   # bug#1 缓解(review M-5)
                ex._ctx.controller.click(confirm)
                time.sleep(1.0)
                continue
            if not ex._op.round_by_find_area(scr, SCREEN_NAME, '备战标识-购买经验').is_success:
                # P4R 弹窗污染守卫(1-1 事故):备战标识消失 ≠ 出战成功——
                # 「前台区域无角色」等确认弹窗同样盖掉标识(实锤:假成功 →
                # 交回外循环 → 「确认关闭→重部署」无限 round_wait 死循环)。
                # 出战被拒弹窗在场 = 失败,交上层「带验证的重部署 → 再出战」链。
                time.sleep(0.6)   # 弹窗渲染窗(标识消失帧可能早于弹窗)
                _post = ex._op.screenshot()
                for _bscr, _banchor in PrepActionExecutor.POST_LAUNCH_BLOCKERS:
                    if ex._op.round_by_find_area(_post, _bscr, _banchor).is_success:
                        return False, f'出战被拒:弹窗 {_banchor}(标识消失为弹窗污染,非转移)'
                log.info('[cw][battle] 出战成功 → 备战标识消失(无拦截弹窗)')
                if _btn_area == '按钮-跳过':
                    # 免战牌跳过递减挂点(迁移批次三,设计 §3.2.19 载体归一
                    # 另一半/§8.7 批次三件 5):正本 = effect_inventory
                    # .remaining_uses(§5.1),跳过**执行落地**(备战标识消失
                    # 验证通过)= 次数递减,归零移除。与登记挂点解耦:未登记
                    # (登记面缺位的局)→ consume_use 返 None 零动作,不炸
                    # 发射回执。best-effort 记录面(与升级挂点同纪律)。
                    try:
                        from sr_od.application.currency_war.kernel.cw_game_state import (
                            board_state_of,
                        )
                        from sr_od.application.currency_war.kernel.cw_investments import (
                            STRATEGY_EFFECTS,
                        )
                        _mz = getattr(ex._ctx, 'cw_match', None)
                        _sz = getattr(_mz, 'session', None) if _mz is not None else None
                        _spec_z = STRATEGY_EFFECTS.get('免战牌')
                        if _sz is not None and _spec_z is not None:
                            _left = board_state_of(_sz).effects.consume_use(
                                _spec_z.id)
                            log.info(f'[cw][battle] 免战牌跳过落地 → '
                                     f'次数递减(余 {_left})')
                    except Exception as e:   # noqa: BLE001  记录面不阻塞
                        log.warning(f'[cw][battle] 免战牌递减记录失败(不阻塞): {e}')
                return True, '出战成功'
        return False, '出战 click 未落地(6×0.5s 轮询+失焦守卫后仍在备战)'

    def _launch_dead_reset(self, ex: PrepActionExecutor) -> None:
        """发射成功/环内任何成功发射 → 清连败计数(输入通道已恢复的证据)。"""
        match = getattr(ex._ctx, 'cw_match', None)
        session = getattr(match, 'session', None) if match is not None else None
        if session is not None and getattr(exec_state_of(session), 'launch_dead_streak', 0):
            exec_state_of(session).launch_dead_streak = 0

    def _launch_dead_escalate(self, ex: PrepActionExecutor) -> str | None:
        """发射连败升级:未落地连发达限 → 停机留证(返回失败 detail);未达限返回 None。

        只对「未落地」型失败计数(识别类失败如找不到按钮不是输入通道问题);
        计数挂 session(跨环重入存活——环级计数随 Director 重建清零,挡不住
        round_fail → 外环重入的 2min/次僵尸循环,两局实证)。
        """
        from sr_od.application.currency_war.prep_actions import (
            PrepActionExecutor,
        )
        match = getattr(ex._ctx, 'cw_match', None)
        session = getattr(match, 'session', None) if match is not None else None
        if session is None:
            return None
        streak = getattr(exec_state_of(session), 'launch_dead_streak', 0) + 1
        exec_state_of(session).launch_dead_streak = streak
        if streak < PrepActionExecutor.LAUNCH_DEAD_LIMIT:
            log.warning('[cw!][battle] 出战未落地连败 %s/%s', streak,
                        PrepActionExecutor.LAUNCH_DEAD_LIMIT)
            return None
        # 停机留证三要素(截图 + 自描述 flag + stop_running;与 bail ping-pong 同款)。
        # 截图走显式通道不落 suppress(2026-09-02 夜间语料批局1实证:last 帧
        # 通道在停机时刻静默缺失,被 bare suppress 吞掉无日志线索)——失败
        # 必须 log.error 留痕,且 last 帧缺失时用独立现帧兜底(同 L0 安灯
        # _save_andon_frame 通道,不污染 op 循环帧缓存)。
        import contextlib
        stop_shot = ''
        try:
            stop_shot = ex._op.save_screenshot(prefix='launch_dead')
        except Exception:
            log.error('[cw!][battle] launch_dead 取证截图失败(last 帧通道)', exc_info=True)
        if not stop_shot:
            try:
                _ts, _img = ex._ctx.controller.screenshot(independent=True)
                if _img is not None:
                    from one_dragon.utils import debug_utils
                    stop_shot = debug_utils.save_debug_image(_img, prefix='launch_dead')
            except Exception:
                log.error('[cw!][battle] launch_dead 取证截图失败(独立现帧兜底通道)', exc_info=True)
        with contextlib.suppress(Exception):
            import time as _t

            # flag 路径锚项目根(与 defects.l0_andon_flag_path 同口径):相对路径
            # 会把 flag 落在进程 cwd 下——pytest(仓根 cwd)复现本钩子时会误写
            # 真 flag,值班者误判实机停线(2026-09-03 停机现场实证)。
            from one_dragon.utils.file_utils import get_project_root
            _flag = (get_project_root()
                     / '.debug/temp/currency_war/launch_dead_hook.flag')
            _flag.parent.mkdir(parents=True, exist_ok=True)
            _flag.write_text(
                f'[HOOK-STOP] 出战发射连败停机(常驻安全网,无激活自愈——用户裁定)\n'
                f'触发:出战 click 未落地 ×{streak}(原样重发仍败)——根因未定,\n'
                f'头号候选=真前台被其他进程抢占(SendInput 落点非游戏)/游戏侧输入管线挂起。\n'
                f'取证:1. 对比 GetForegroundWindow 句柄与游戏句柄(谁在真前台);\n'
                f'2. 手动点击游戏画面确认输入是否恢复;3. 看 .debug/images/launch_dead_*;\n'
                f'4. 处理完删本 flag 重启对局。\n'
                f'ts={_t.strftime("%m-%d %H:%M:%S")}\n', encoding='utf-8')
        rc = getattr(ex._ctx, 'run_context', None)
        if rc is not None:
            with contextlib.suppress(Exception):
                rc.stop_running(reason='hook:cw_launch_dead')
        return f'出战 click 未落地×{streak} → 停机留证(hook:cw_launch_dead)'
