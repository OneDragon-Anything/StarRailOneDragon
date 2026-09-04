"""货币战争 备战决策环 原子动作全集 + 执行器(P1;strategy/03(原 doc 15§4)/§13)。

框架层:本模块**不含玩法判断**(何时收球/卖谁/何时出战 = 策略层 CwStrategy.decide_prep_action),
只负责「执行一个动作 + 完成验证」。三失败路径(§13.2):
- 验证失败 → execute 返回 progressed=False(CwScreenPrep 计 fail/屏蔽);
- 参数非法 → validate 返回错误串(Director 拒绝执行 + 该步计 stall + telemetry);
- 执行异常 → 异常上抛(Director 上抛 = 本环 fail,外层 op retry 接管)。

slot 语义全局统一(§13.1):**物理槽位** —— 备战栏 1-9 / 前排 1-4 / 后排 1-N;非 bench 列表下标!
与族 A(cw_state.Action 策略动作)同名类(SellBench/DeployMove/SellDeployed)的坐标系对照:
族 B 物理槽位 = 族 A 下标 + 1(bench 域);deployed 域两族结构不同(族 B=row+slot
物理排槽位,族 A=紧缩列表下标)——完整对照表见 cw_state.py Action 节约定块。
组合动作命名映射(§7 L1):RunDeploy=CwOpDeploy / RunEquip=CwOpEquipAll(RunBuyPhase 组合已随 shop.py 壳退役删除,W970 批 C 后决策核只发显式开店意图)
(P1 过渡,P2/P3 溶解为原子)。
"""
from __future__ import annotations

import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    SHOP_SCREEN_NAME,
    _area_rect,
    _ocr,
    area_center,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PREP_ACTION_TYPES,
    BailToOuter,
    ClickSpheres,
    DeferSpheres,
    DeployMove,
    EnsureShopClosed,
    EnsureShopOpen,
    LevelUp,
    OpenBox,
    OpenTome,
    PickBoxCard,
    PrepAction,
    RunDeploy,
    RunEquip,
    SellBench,
    SellDeployed,
    StartBattle,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    read_reward_spheres,
    read_supply_boxes,
)
from sr_od.application.currency_war.obs.cw_observation import read_gold
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 点击后 overlay 弹出/关闭的事件驱动轮询预算(替代旧固定
#: sleep 1.5s 后单次验证——overlay 通常更快就位,命中即返回;
#: 慢时仍受上界,失败语义与旧固定等待一致。依据:单局耗时
#: 审计报告 .debug/temp/currency_war/w417_duration_audit/
#: REPORT.md「需验证·出战链」)。取旧固定值 1.5s + 一个轮询
#: 间隔 0.3s,保证最坏情形覆盖面不缩水。
_OVERLAY_POLL_TIMEOUT_S: float = 1.8

#: 商店收起动画时长(DD-011 操作完成自等动画;实测口径 screen_flow_timing
#: #15「收起过场动画 ~1s 即备战画面稳定」,用户口述。op 完成后显式等待,替代
#: 测量驱动 gate——画面状态判断已外移建档识别层,等待时长归产生动画的操作声明)。
SHOP_CLOSE_ANIM_S: float = 1.0
#: 商店打开动画时长(DD-011 固定时长自等;用户口述定值 2026-09-02「干净的备战
#: 里打开商店,只要等 1 秒就够了」。等待后验证「按钮-收起」出现 = 点击生效验证,
#: 非动画判定。自动开店场景不经此处——cw_loop 备战分支按「备战阶段」识别)。
SHOP_OPEN_ANIM_S: float = 1.0


def _read_level_raw(ctx: SrContext, screen) -> int | None:
    """OCR 直读等级数字(「文本-等级」区,**无 _expected_level 兜底**;review MED-8)。

    read_level 的兜底曲线适合决策估值,不适合完成验证(期望值>实际时假成功)。漏读返 None,
    调用方决定基线退路。放大读与读链单一源 = ``cw_observation.read_level_raw_opt``。
    """
    from sr_od.application.currency_war.obs.cw_observation import read_level_raw_opt

    return read_level_raw_opt(ctx, screen)


def row_area_centers(ctx: SrContext, prefix: str) -> list[Point]:
    """从 screen_info「货币战争-备战」读全部 prefix-N 区域中心(N 升序)。

    同 CwOpDeploy._row_centers 逻辑(读全不硬编码,后排 >6 时 screen_info 补区后自动跟上);
    prep_actions 执行器 / cw_screen_prep 观察共用。
    """
    si = ctx.screen_loader.get_screen(SCREEN_NAME)
    if si is None:
        return []
    pts: list[tuple[int, Point]] = []
    pfx = f'{prefix}-'
    for a in si.area_list:
        if a.area_name.startswith(pfx) and a.pc_rect is not None:
            try:
                n = int(a.area_name[len(pfx):])
            except ValueError:
                continue
            pts.append((n, a.pc_rect.center))
    pts.sort(key=lambda t: t[0])
    return [p for _, p in pts]


def sell_point(ctx: SrContext) -> Point:
    """出售区落点(单一源):screen_info「货币战争-备战.区域-出售区」中心;
    缺失/未建档兜底 ``PrepActionExecutor.SELL_POINT`` 常量(硬编码坐标)。

    W62 件2(ADR-0329,设计章2.6):出售区原是硬编码坐标
    (``SELL_POINT = Point(70, 846)``,prep_actions/deploy_bench/shop.py 三处同值
    ——游戏机制为「拖到左下区域即出售」,无按钮)→ 补 screen_info area 后
    经本 helper 读中心,硬编码作兜底(与 ``LEVEL_UP_FALLBACK`` 同模式)。
    """
    return area_center(ctx, '区域-出售区') or PrepActionExecutor.SELL_POINT


def drag_bench_to_sell(op: SrOperation, ctx: SrContext, bench_idx: int) -> bool:
    """拖备战槽(槽位下标 0-8)→ 出售区(共享卖原语,W62 件2/设计章2.10)。

    d2 卖通道生产接线(shop.py prefix 循环 SellBench 分支)与 prep_actions
    ``_sell_bench`` 共用本 helper:「拖→出售区→验源槽空」一段(DragCwChar.drag_char
    内含验源槽像素变 + retry);tracking 同步由调用方各自做。失焦守卫同
    ``PrepActionExecutor._drag`` 语义(窗口后台化时拖拽输入静默丢,r9 实证)。

    Args:
        op: 调用方 op(取 ctx.controller 操作 + screenshot 验证)。
        ctx: SrContext。
        bench_idx: 槽位下标 0-8(ADR-0316:列表下标 = 物理备战栏槽位 1-9 减一)。
    """
    pts = row_area_centers(ctx, '备战栏')
    if not (0 <= bench_idx < len(pts)):
        return False
    try:
        gw = ctx.controller.game_win
        if not gw.is_win_active:
            log.warning('[cw!][drag] 窗口失焦(拖拽输入将静默丢)→ 先激活')
            gw.active()
            time.sleep(0.3)
    except Exception:   # noqa: BLE001  焦点守卫 best-effort
        pass
    from sr_od.application.currency_war.operations.dev.drag_cw_char import (
        DragCwChar,
    )
    return DragCwChar.drag_char(op, pts[bench_idx], sell_point(ctx))


class PrepActionExecutor:
    """备战原子/组合动作执行器(框架层;持 ctx + 宿主 op 复用截图/区域匹配/拖拽原语)。

    宿主 op = CwScreenPrep(SrOperation);所有验证经 op.round_by_find_area / OCR,
    拖拽统一走 DragCwChar.drag_char(中心拖 + hold0,2026-08-13 实测验证)。
    """

    SELL_POINT: ClassVar[Point] = Point(70, 846)      # 出售区(左下,同 deploy_bench/_handle_bench_full)
    BOX_SCREEN: ClassVar[str] = '货币战争-备战-武装箱选择'
    BOX_OPEN_DY: ClassVar[int] = 41                   # 「开启」文字区 = 箱 icon 下方偏移(cw_screen_supply 实测)
    CARD_Y: ClassVar[int] = 290                       # 武装箱卡身点击 y(点卡名下方一点避「查看详情」)
    LEVEL_MAX_CLICKS: ClassVar[int] = 12              # 升级单动作最多买经验次数(同 _handle_bench_full 量级)
    SPHERE_MAX_CLICKS: ClassVar[int] = 12             # 单动作点球硬上限(防识别抖动死循环)
    BATTLE_FALLBACK: ClassVar[Point] = Point(1817, 749)   # 出战按钮兜底(同 battle_prep)
    CONFIRM_FALLBACK: ClassVar[Point] = Point(1159, 653)  # 未达上限确认兜底(同 battle_prep)
    CHECKBOX_FALLBACK: ClassVar[Point] = Point(912, 589)   # 本局不再提示勾选兜底(ADR-0136;同 CwScreenDeployNotFull)
    LAUNCH_DEAD_LIMIT: ClassVar[int] = 3   # 出战未落地连败停机阈值(session 级计数;两局实证环重入 ~2min/次)
    #: P4R:出战后「转移成功」的拦截弹窗白名单(锚 = 已建档 id_mark)。
    #: 出战按钮点击后备战标识消失但下列弹窗在场 = 出战被游戏拒(1-1 事故
    #: 「前台区域无角色」确认弹窗盖标识 = 旧判据假成功)。新弹窗建档后追加。
    POST_LAUNCH_BLOCKERS: ClassVar[tuple[tuple[str, str], ...]] = (
        ('货币战争-提示-前台无角色', '标识-无角色提示'),
    )

    def __init__(self, op: SrOperation, ctx: SrContext) -> None:
        self._op = op
        self._ctx = ctx
        # 槽位中心(screen_info 静态,构造时读一次;F3 参数校验 + 拖拽坐标共用)
        self._bench_pts: list[Point] = row_area_centers(ctx, '备战栏')
        self._front_pts: list[Point] = row_area_centers(ctx, '前排')
        self._back_pts: list[Point] = row_area_centers(ctx, '后排')

    # ===== F3 参数校验(非法 → 错误串;合法 → None)=====

    def validate(self, action: PrepAction) -> str | None:
        """校验动作合法域 + 参数(§5.0 F3)。返回错误描述;None=合法。

        两层:① 动作全集白名单(review M-4 —— 未知类型走参数非法路径拒绝,不进 execute
        的验证失败/fail 循环);② 静态可判参数(槽位越界/row 枚举)。动态前置(球是否存
        在/overlay 是否开)由 execute 的完成验证覆盖(验证失败路径,非参数非法路径)。
        """
        if not isinstance(action, PREP_ACTION_TYPES):
            return f'未知动作类型 {type(action).__name__}(不在动作全集,§4)'
        if isinstance(action, SellBench):
            if not (1 <= action.slot <= len(self._bench_pts)):
                return f'SellBench slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, SellDeployed):
            if action.row not in ('front', 'back'):
                return f'SellDeployed row={action.row!r} 非法(front/back)'
            n = len(self._front_pts if action.row == 'front' else self._back_pts)
            if not (1 <= action.slot <= n):
                return f'SellDeployed slot={action.slot} 越界(1-{n})'
        elif isinstance(action, DeployMove):
            if not (1 <= action.from_slot <= len(self._bench_pts)):
                return f'DeployMove from_slot={action.from_slot} 越界(1-{len(self._bench_pts)})'
            if action.to_row not in ('front', 'back'):
                return f'DeployMove to_row={action.to_row!r} 非法(front/back)'
            n = len(self._front_pts if action.to_row == 'front' else self._back_pts)
            if not (1 <= action.to_slot <= n):
                return f'DeployMove to_slot={action.to_slot} 越界(1-{n})'
        elif isinstance(action, ClickSpheres):
            if action.max_k < 1:
                return f'ClickSpheres max_k={action.max_k} < 1'
        elif isinstance(action, OpenBox):
            if action.slot is not None and not (1 <= action.slot <= len(self._bench_pts)):
                return f'OpenBox slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, OpenTome):
            if action.slot is not None and not (1 <= action.slot <= len(self._bench_pts)):
                return f'OpenTome slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, PickBoxCard):
            if action.card_idx is not None and not (1 <= action.card_idx <= 4):
                return f'PickBoxCard card_idx={action.card_idx} 越界(1-4)'
        return None

    # ===== 执行入口(三失败路径之「验证失败」→ (False, detail);异常自然上抛)=====

    def execute(self, action: PrepAction) -> tuple[bool, str]:
        """执行动作 → (progressed, detail)。progressed=完成验证过的进展。

        ⚖️ W209j 刹车语义(ADR-0388,纵深防御第二层):运行中被停 → 拒绝
        执行任何动作(点击/拖拽/出战),直接返回停止态。run 27 实证:director
        环在 Deploy 钩子 stop_running 后仍发 StartBattle 点出战(14:09:14
        「出战成功」)——环顶检查(第一层)之外,本入口兜底覆盖绕环路径
        (_force_battle 恢复原语等)。判据 = last_run_result 非空(start 清
        None/stop 写入;run_state STOP 是 idle 初始态不能直接用)。
        """
        _rc = getattr(self._ctx, 'run_context', None)
        if _rc is not None and getattr(_rc, 'last_run_result', None) is not None:
            log.info('[cw][battle] 停机标志已设 → 拒绝执行 %s'
                     '(W209j 刹车,ADR-0388)', type(action).__name__)
            return False, '已停止[W209j刹车]'
        ok, detail = self._execute_dispatch(action)
        if ok and isinstance(action, RunEquip):
            # M7 备战期装备闩置位(执行位,唯一写点 = mandate.mark_equip_
            # pass_executed;发射位只读不写):本入口在 RunEquip 组合 op
            # 成功返回时记账「本期穿戴 pass 已完整执行」——单动作备战环
            # 下发射列表中 RunEquip 之前的可续动作先执行即终结本环,
            # 发射即置闩会闩烧而装备未穿(与开店闩置位时机修复同型,
            # 依据 = mandate.mark_equip_pass_executed docstring)。
            try:
                from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
                    mark_equip_pass_executed,
                )
                _m = self._ctx.cw_match
                _sess = _m.session if _m is not None else None
                if _sess is not None:
                    mark_equip_pass_executed(
                        _sess, getattr(_sess, 'last_state', None))
            except Exception as e:  # noqa: BLE001  记账失败不阻塞执行
                log.warning('[cw][equip-latch] 置位失败(不阻塞): %s', e)
        # 期望态推进(EXPECTED_STATE §6 对抗 F8:两执行面同源接线)——
        # 本执行器是 PrepActionExecutor.execute 与 decision_assembly.execute
        # 的共同底层(decision 面经绑定回放委托到这里),登记挂本入口 = 两面
        # 一次覆盖、零双写。progressed 才登记(失败=未执行,无逻辑后果);
        # 登记失败不阻塞执行(观测面,best-effort)。
        if ok:
            try:
                from sr_od.application.currency_war.kernel.cw_expected_state import (
                    apply_op_effect,
                )
                match = self._ctx.cw_match
                session = match.session if match is not None else None
                if session is not None:
                    apply_op_effect(session, action, detail=detail,
                                    produced_by=type(self).__name__)
            except Exception as e:  # noqa: BLE001  登记失败不阻塞执行
                log.warning('[cw][expect] apply_op_effect 失败(不阻塞): %s', e)
        return ok, detail

    def _execute_dispatch(self, action: PrepAction) -> tuple[bool, str]:
        """动作分派(原 execute 主体;期望态钩子在其上层 execute)。"""
        if isinstance(action, ClickSpheres):
            return self._click_spheres(action)
        if isinstance(action, OpenBox):
            return self._open_box(action)
        if isinstance(action, OpenTome):
            return self._open_tome(action)
        if isinstance(action, PickBoxCard):
            return self._pick_box_card(action)
        if isinstance(action, SellBench):
            return self._sell_bench(action)
        if isinstance(action, SellDeployed):
            return self._sell_deployed(action)
        if isinstance(action, DeployMove):
            return self._deploy_move(action)
        if isinstance(action, LevelUp):
            return self._level_up()
        if isinstance(action, EnsureShopOpen):
            return self._ensure_shop(True)
        if isinstance(action, EnsureShopClosed):
            return self._ensure_shop(False)
        if isinstance(action, StartBattle):
            return self._start_battle()
        if isinstance(action, RunDeploy):
            return self._run_composite('部署', 'sr_od.application.currency_war.operations.cw_op.cw_op_deploy.CwOpDeploy')
        if isinstance(action, RunEquip):
            return self._run_composite('装备', 'sr_od.application.currency_war.operations.cw_op.cw_op_equip_all.CwOpEquipAll')
        if isinstance(action, (DeferSpheres, BailToOuter)):   # 本模块定义,无需导入
            return False, '控制流动作不经 execute(框架信号,§4.2b;环应在控制流分支拦下)'
        return False, f'未知动作类型 {type(action).__name__}'

    # ===== 奖励域 =====

    def _click_spheres(self, action: ClickSpheres) -> tuple[bool, str]:
        """批式点球(大球优先):一次全点 → 等满动画 → 一次截图统一验证。

        2026-09-02 用户指导(screen_flow_timing.md #16):奖励球飞行动画
        最长 ~2s(去向 = 备战/商店/装备栏),原逐球「点击 + 1.2s 验证」×N
        慢(且实证日志有同 step 重复发球)。权衡(用户裁定):席满时部分球
        可能没点开——由后续 heavy 观察自然回补(球仍在 → 下轮再派)。
        review H-3 语义保留:progressed = 验证球数减少 > 0;全没消失 =
        席满点不动 → False 走环的 fail/恢复路径(§13.2)。
        """
        budget = min(action.max_k, PrepActionExecutor.SPHERE_MAX_CLICKS)
        screen = self._op.screenshot()
        spheres = read_reward_spheres(self._ctx, screen)
        if not spheres:
            return True, '无球(观察-执行竞态,无事可做)'   # LOW-2:不计验证失败
        targets = sorted(spheres, key=lambda t: t[2], reverse=True)[:budget]
        clicked = 0
        for _color, center, _r in targets:
            self._ctx.controller.mouse_move(center)   # bug#1 缓解
            self._ctx.controller.click(center)
            clicked += 1
            self._op.park_cursor(after_wait=0.1)
        # 用户口径:飞行动画最长 ~2s → 等满再一次观察(非逐球等待)
        time.sleep(2.0)
        screen = self._op.screenshot()
        after = read_reward_spheres(self._ctx, screen)
        verified = max(0, len(spheres) - len(after))
        detail = f'点球 {clicked}/{budget} 验证消失 {verified}(剩 {len(after)})'
        # 点击后零消失幻检(奖励域防幻检批;实机停机局实证:礼盒幻球点击
        # 零消失 → 同分支无限重进,DD-030 才是唯一出口):验证期一球未消
        # 且备战席**有空位**(席满点不动是既有裁定语义 = 真球保留待下轮,
        # 不可拉黑)→ 点击目标复现在原位 = 幻球,登记会话黑名单 + 分键,
        # 后续读侧过滤放弃该目标。
        if verified == 0 and self._bench_has_free_slot():
            from sr_od.application.currency_war.obs.cw_identity_obs import (
                note_phantom_sphere,
            )
            for _color, center, _r in targets:
                if any(abs(center.x - a[1].x) <= 18
                       and abs(center.y - a[1].y) <= 18 for a in after):
                    note_phantom_sphere(self._ctx, center)
                    detail += f' 幻球({center.x},{center.y})→黑名单'
        if read_supply_boxes(self._ctx, screen):
            detail += ' 掉箱→下步 OpenBox 统筹'
        log.info(f'[cw][sphere] {detail}')
        return verified > 0, detail

    def _bench_has_free_slot(self) -> bool:
        """备战席有空位?(幻球拉黑前置:席满点不动 = 真球保留,禁拉黑。)
        CV 占用现读,便宜;读失败按「无空位」保守(不拉黑,回到重试语义)。"""
        try:
            from sr_od.application.currency_war.obs.currency_war_cv import (
                slot_occupied,
            )
            pts = row_area_centers(self._ctx, '备战栏')
            free = [p for p in pts if not slot_occupied(
                self._op.screenshot(), int(p.x), int(p.y))]
            return bool(free)
        except Exception:   # noqa: BLE001  保守:读失败不拉黑
            return False

    def _poll_transition(self, check, timeout_s: float,
                         interval_s: float = 0.3) -> bool:
        """点击后过渡的事件驱动等待:每 interval_s 轮询 check,
        命中即返回 True;预算内未命中返回 False(失败语义与旧
        「固定 sleep 后单次验证」一致,只是把死等换成轮询)。"""
        deadline = time.monotonic() + timeout_s
        while True:
            if check():
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(interval_s)

    def _open_box(self, action: OpenBox) -> tuple[bool, str]:
        """开箱:点箱槽「开启」→ 验武装箱 overlay 弹出(标识-请选择)。"""
        screen = self._op.screenshot()
        boxes = read_supply_boxes(self._ctx, screen)
        if not boxes:
            return False, '无补给箱'
        picked = boxes[0]
        if action.slot is not None:
            matched = next((b for b in boxes if b[0] == action.slot), None)
            if matched is None:
                return False, f'槽{action.slot} 无补给箱(实读 {boxes})'
            picked = matched
        slot, center = picked
        open_point = Point(center.x, center.y + PrepActionExecutor.BOX_OPEN_DY)
        self._ctx.controller.mouse_move(open_point)   # bug#1 缓解
        self._ctx.controller.click(open_point)
        if not self._poll_transition(
                lambda: self._op.round_by_find_area(
                    self._op.screenshot(),
                    PrepActionExecutor.BOX_SCREEN, '标识-请选择').is_success,
                _OVERLAY_POLL_TIMEOUT_S):
            return False, f'武装箱 overlay 未弹(槽{slot} 点击落空?)'
        log.info(f'[cw][box] 开箱槽{slot} → overlay 弹出 ✓')
        return True, f'开箱槽{slot}'

    def _open_tome(self, action: OpenTome) -> tuple[bool, str]:
        """开秘密典籍:点槽两次(选中→开启)→ 验星徽四选一弹窗(标识-星徽秘典)。

        点两次间隔 ~1s(第一次选中边框高亮,第二次弹窗);弹窗后 loop 0i 接管选卡
        (本动作不选 —— 选卡是策略决策,板上阵营匹配在 0i handler)。
        """
        from sr_od.application.currency_war.obs.cw_identity_obs import read_tomes
        screen = self._op.screenshot()
        tomes = read_tomes(self._ctx, screen)
        if not tomes:
            return False, '无秘密典籍'
        picked = tomes[0]
        if action.slot is not None:
            matched = next((t for t in tomes if t[0] == action.slot), None)
            if matched is None:
                return False, f'槽{action.slot} 无典籍(实读 {tomes})'
            picked = matched
        slot, center = picked
        self._ctx.controller.mouse_move(center)   # bug#1 缓解
        self._ctx.controller.click(center)        # 第一次:选中
        time.sleep(1.0)
        self._ctx.controller.click(center)        # 第二次:开启
        if not self._poll_transition(
                lambda: self._op.round_by_find_area(
                    self._op.screenshot(),
                    '货币战争-星徽秘典弹窗', '标识-星徽秘典').is_success,
                _OVERLAY_POLL_TIMEOUT_S):
            return False, f'星徽四选一未弹(槽{slot} 点两次落空?)'
        log.info(f'[cw][tome] 开典籍槽{slot} → 星徽四选一弹出 ✓(选卡交 loop 0i)')
        return True, f'开典籍槽{slot}'

    def _pick_box_card(self, action: PickBoxCard) -> tuple[bool, str]:
        """选卡:OCR 卡名行 → (card_idx 指定 | 执行器默认:key_equips 命中 → 材料通用性 → 第1张)→ 点卡验关。"""
        overlay = self._op.screenshot()
        if not self._op.round_by_find_area(overlay, PrepActionExecutor.BOX_SCREEN, '标识-请选择').is_success:
            return False, '武装箱 overlay 未开(先 OpenBox)'
        rect = _area_rect(self._ctx, '区域-卡名行', PrepActionExecutor.BOX_SCREEN)
        names: list[tuple[str, int]] = []
        if rect is not None:
            for r in _ocr(self._ctx, overlay, rect):
                if 2 <= len(r.data) <= 8:
                    names.append((r.data, r.center.x))
        names.sort(key=lambda t: t[1])
        if not names:
            return False, 'OCR 未读到卡名'
        if action.card_idx is not None:
            if not (1 <= action.card_idx <= len(names)):
                return False, f'card_idx={action.card_idx} 超实读卡数 {len(names)}'
            chosen, choose_x = names[action.card_idx - 1]
        else:
            chosen, choose_x = self._default_box_card(names)
        card_point = Point(choose_x, PrepActionExecutor.CARD_Y)
        self._ctx.controller.mouse_move(card_point)   # bug#1 缓解
        self._ctx.controller.click(card_point)        # 点卡选中即确认(实测单步)
        if not self._poll_transition(
                lambda: not self._op.round_by_ocr(
                    self._op.screenshot(), '武装箱', lcs_percent=0.5).is_success,
                _OVERLAY_POLL_TIMEOUT_S):
            return False, f'选卡 {chosen} 后 overlay 仍在'
        log.info(f'[cw][box] 选卡 {chosen} → overlay 关 ✓')
        return True, f'选卡 {chosen}'

    def _default_box_card(self, names: list[tuple[str, int]]) -> tuple[str, int]:
        """执行器内嵌默认选卡(r104 起委托策略模块 decide_box_card;P5 上移已落地两处归一)。

        策略层打分:key_equips 命中 +100 / key 材料两跳 +30 / 材料通用性;
        无 match(局外)回落旧内联(key_equips → 材料通用性 → 第1张)。
        """
        match = self._ctx.cw_match
        if match is not None:
            try:
                from sr_od.application.currency_war.kernel.cw_state import GameState
                _st = match.session.last_state or GameState()
                idx = match.strategy.decide_box_card(
                    [n for n, _ in names], _st, match.session,
                    getattr(match, 'config', None))
                if 0 <= idx < len(names):
                    return names[idx]
            except Exception:   # noqa: BLE001  策略失败回落旧逻辑
                pass
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_supply import (
            _material_value,
        )
        if match is not None and match.session.target_comp is not None:
            key_equips = set(match.session.target_comp.key_equips or [])
            for n, x in names:
                if n in key_equips:
                    return n, x
        best = max(names, key=lambda t: _material_value(t[0]))
        return best

    # ===== 席位域 =====

    def _sell_bench(self, action: SellBench) -> tuple[bool, str]:
        """卖备战槽角色:drag 槽中心 → 出售区(``drag_bench_to_sell`` 单一源;
        drag_char 内验源槽空)。"""
        ok = drag_bench_to_sell(self._op, self._ctx, action.slot - 1)
        if ok:
            self._track_remove_bench(action.slot)
            # 用户口述口径(screen_flow_timing.md #21,2026-09-02):卖出金币
            # 动画很快,等 1s 足够——批尾观察前补这段,防读到金币动画帧。
            time.sleep(1.0)
        return ok, f'卖备战槽{action.slot} {"✓" if ok else "拖3次源槽未变"}'

    def _sell_deployed(self, action: SellDeployed) -> tuple[bool, str]:
        """卖上阵角色:drag 排槽中心 → 出售区(落点经 ``sell_point`` 单一源);
        drag_char 内验源槽空。"""
        pts = self._front_pts if action.row == 'front' else self._back_pts
        src = pts[action.slot - 1]
        ok = self._drag(src, sell_point(self._ctx))
        if ok:
            self._track_remove_deployed(action.row, action.slot)
            time.sleep(1.0)   # 同上 #21 口径:卖出动画 1s
        return ok, f'卖{action.row}排{action.slot} {"✓" if ok else "拖3次源槽未变"}'

    def _deploy_move(self, action: DeployMove) -> tuple[bool, str]:
        """bench → 上阵单步拖拽(腾席链专用);drag_char 内验源槽空。"""
        pts = self._front_pts if action.to_row == 'front' else self._back_pts
        src = self._bench_pts[action.from_slot - 1]
        dst = pts[action.to_slot - 1]
        ok = self._drag(src, dst)
        if ok:
            self._track_move_deployed(action.from_slot, action.to_row, action.to_slot)
            # 用户口述口径(screen_flow_timing.md #10,2026-09-02):拖动触发
            # 羁绊阶段变更时角色头顶徽章动画 ~2s——拖完立即返回会让批尾
            # heavy 观察打在徽章动画帧上(SIFT/对账读脏,「对账纠漂」日志
            # 噪声源之一)。按「都等 2s」简单方案落(批尾/中间的区分不做)。
            time.sleep(2.0)
            # 用户口述口径(#24,2026-09-02):羁绊达标触发的 overlay(盛会之星
            # 等)在徽章动画后再 ~2s 才弹出——固定等待覆盖不住。执行端等待后
            # 快查一次触发型 overlay 锚(模板毫秒级),命中 → detail 标注(拖拽
            # 本身已成功);批尾 heavy 的 event_overlay 检测将看到它并 bail 交
            # 外环 handler——防「decide 的下一步动作打在 overlay 上」。清单
            # 可扩(圣杯/银狼升星等实测出现时加锚)。
            _post = self._op.screenshot()
            if self._op.round_by_find_area(
                    _post, '货币战争-盛会之星', '标识-盛会之星',
                    crop_first=False).is_success:
                log.info('[cw][deploy] 拖后检出盛会之星 overlay(羁绊达标触发)')
                return True, '部署✓ 但盛会之星 overlay 弹出(外环接管)'
        return ok, f'部署槽{action.from_slot}→{action.to_row}{action.to_slot} {"✓" if ok else "拖3次源槽未变"}'

    def _drag(self, src: Point, dst: Point) -> bool:
        """统一拖拽原语(DragCwChar.drag_char:中心拖+hold0+retry+验源槽像素变)。

        r10 review#2:失焦守卫下沉到本原语(所有拖拽路径共享)——窗口后台化时
        拖拽输入静默丢(r9 实证同机制:截图正常/输入丢/连环「源槽未变」假失败),
        拖前验焦点,失焦先激活。StartBattle 的 click 守卫同款语义(在它自己的
        路径上,click 不走本原语)。
        """
        from sr_od.application.currency_war.operations.dev.drag_cw_char import (
            DragCwChar,
        )

        try:
            gw = self._ctx.controller.game_win
            if not gw.is_win_active:
                log.warning('[cw!][drag] 窗口失焦(拖拽输入将静默丢)→ 先激活')
                gw.active()
                time.sleep(0.3)
        except Exception:   # noqa: BLE001  焦点守卫 best-effort
            pass
        return DragCwChar.drag_char(self._op, src, dst)

    def _track_remove_bench(self, slot: int) -> None:
        """卖出后备势跟踪同步(单一跟踪账 tracked_bench_chars)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        # 形状双源防御(ADR-0316):tracked_bench_chars 可能是 pad 态(含 None)
        match.session.tracked_bench_chars = [
            bc for bc in match.session.tracked_bench_chars
            if bc is not None and bc.slot != slot]

    def _track_remove_deployed(self, row: str, slot: int) -> None:
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        # ADR-0392:tracked_deployed 槽位表(置 None 不移位);(row, slot)
        # 物理 1-based → 槽位下标(front: slot-1 / back: 4+slot-1)
        from sr_od.application.currency_war.kernel.cw_state import (
            DEPLOYED_FRONT_CAPACITY,
            pad_deployed,
        )
        tracked = pad_deployed(list(match.session.tracked_deployed))
        idx = (slot - 1 if row == 'front'
               else DEPLOYED_FRONT_CAPACITY + slot - 1)
        if 0 <= idx < len(tracked) and tracked[idx] is not None \
                and tracked[idx].position_pref == row:
            tracked[idx] = None
        match.session.tracked_deployed = tracked

    def _track_move_deployed(self, from_slot: int, to_row: str, to_slot: int) -> None:
        """上阵后备势跟踪同步:bench 条目 → deployed 条目(位置/槽位改写)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        # 形状双源防御(ADR-0316):tracked_bench_chars 可能是 pad 态(含 None)
        moved = [bc for bc in match.session.tracked_bench_chars
                 if bc is not None and bc.slot == from_slot]
        match.session.tracked_bench_chars = [
            bc for bc in match.session.tracked_bench_chars
            if bc is not None and bc.slot != from_slot]
        # ADR-0392:tracked_deployed 槽位表——deployed_place 单一源落槽;
        # to_slot 是执行器物理槽位真值,落槽后覆写信息位。
        from sr_od.application.currency_war.kernel.cw_state import deployed_place
        for bc in moved:
            bc.position_pref = to_row
            deployed_place(match.session.tracked_deployed, bc)
            bc.slot = to_slot

    # ===== 商店域 =====

    def _level_up(self) -> tuple[bool, str]:
        """买经验至 level+1(循环点「购买经验」+ **OCR 直读**验证;gold 前置由策略保证)。

        MED-8:完成验证用 _read_level_raw(无 _expected_level 兜底)—— read_level 漏读时返
        期望曲线值,落后攒金场景 expected>actual → 首点即假成功 + 污染 session 单调守卫。
        """
        match = self._ctx.cw_match
        session = match.session if match is not None else None
        screen = self._op.screenshot()
        before = _read_level_raw(self._ctx, screen)
        if before is None and session is not None and session.last_level_obs:
            before = session.last_level_obs   # OCR 漏读基线退单调守卫值(只作比较基,不写回)
        if before is None:
            return False, 'level 基线读不到(OCR 漏读),拒绝盲点'
        btn = area_center(self._ctx, '备战标识-购买经验') or Point(296, 860)
        for _ in range(PrepActionExecutor.LEVEL_MAX_CLICKS):
            # r15 review P1:循环内金检查——旧版 12 连点无金门,策略侧金前置滞后一环时
            # (如 P2 急救态 _saving_for_level 仍攒金但 plan 已发 LevelUp),gold 63→9
            # 一动作排干(M57 P2-1 实证)。每点前读金,gold < 单击价(4)即停(防排干买牌本金)。
            gold_now = read_gold(self._ctx, self._op.screenshot())
            if gold_now is not None and gold_now < 4:
                log.info('[cw][levelup] gold %s < 单击价 → 停点(保买牌本金)', gold_now)
                break
            self._ctx.controller.mouse_move(btn)   # bug#1 缓解(review M-5:循环内 screenshot 移光标后紧接 click)
            self._ctx.controller.click(btn)
            # 光标 parking(审计 P0,2026-08-16 = M38 level 毒化注入点):按钮距等级显示区 18px,
            # 点击后光标压住 Lv.N 区 → 下帧 OCR 读错(4 毒化 3 位面的链头)。park 后再读。
            self._op.park_cursor(before_wait=0.3, after_wait=0.15)
            lv = _read_level_raw(self._ctx, self._op.screenshot())
            # live 幽灵 lv10(2026-08-15 两局实锤):raw 读可吃到相邻数字(XP「10/20」的 10),接受任意
            # >before 会把 6→10 假成功写进 last_level_obs 被单调守卫永久锁死(→ 永不买经验+攒金死)。
            # 游戏机制:每点一次经验 +1 级 → 接受窗钳 before+2;窗外读数当漏读,继续循环。
            if lv is not None and before < lv <= before + 2:
                if session is not None:
                    session.last_level_obs = lv
                    # W612 挂点A(升级事件;四挂点中唯一无现成事件行者,裁决见
                    # .debug/temp/currency_war/w612_effect_inventory/HOOKS.md):
                    # 升级发生的集中执行点 = 效果最密集单点(商业间谍升级段/
                    # 固定理财位面段/成长基金到级全在升级邻域),inventory 标记 +
                    # record_exogenous 'level_up' 事件行一次接全。观测 best-effort,
                    # 零决策语义(失败不阻塞,与本文件其余观测回路同纪律)。
                    try:
                        session.effect_inventory.on_level_up()
                        from sr_od.application.currency_war.telemetry import (
                            recorder as cw_telemetry,
                        )


                        _st = session.last_state
                        if _st is not None and _st.round_num:
                            cw_telemetry.record_exogenous(
                                _st.round_num, 'level_up',
                                detail=f'level {before}->{lv}', state=_st)
                    except Exception as e:   # noqa: BLE001  观测失败不阻塞对局
                        log.warning('[cw][levelup] effect inventory 挂点失败(不阻塞): %s', e)
                log.info(f'[cw][levelup] level {before}→{lv} ✓')
                return True, f'level {before}→{lv}'
        return False, f'点{PrepActionExecutor.LEVEL_MAX_CLICKS}次经验 level 未变({before})'

    def _ensure_shop(self, want_open: bool) -> tuple[bool, str]:
        """开/关商店 + 锚点验证(按钮-收起 可见 = 开态)。

        r312(ADR-0213 批次1):开/关向单次验证在动画窗(~3s,
        r299 实测)可假阴性(开店「收起未出现」假失败喂恢复
        机制噪声)。r347(旧路径删除):gate 无条件化(原 flag
        分支删);异常=旧单次验证(离线契约,非 flag 路径)。
        """
        screen = self._op.screenshot()
        is_open = self._op.round_by_find_area(screen, SHOP_SCREEN_NAME, '按钮-收起').is_success
        if want_open:
            if is_open:
                return True, '商店已开'
            # 手动开(用户口述 2026-09-02 场景②):干净备战画面点击商店打开——
            # 固定等待 1.0s(用户口述定值)后验证「按钮-收起」出现(点击生效验证,
            # 非动画判定)。自动开店场景不经此处:结算后由 cw_loop 备战分支按
            # 「备战阶段」识别等面板就位(W971 §2.5/§2.6 场景①),两场景互不竞速。
            self._op.round_by_find_and_click_area(
                screen, SCREEN_NAME, '按钮-商店')
            # 光标 parking(审计 R3):点击点在验证矩形正中(0px),不 park 则收起锚验证读被光标压
            self._op.park_cursor(before_wait=0.5, after_wait=0.1)
            time.sleep(SHOP_OPEN_ANIM_S)
            ok = self._op.round_by_find_area(
                self._op.screenshot(), SHOP_SCREEN_NAME,
                '按钮-收起').is_success
            return ok, f'开商店 {"✓" if ok else "收起未出现(开店未生效)"}'
        if not is_open:
            return True, '商店已关'
        self._op.round_by_find_and_click_area(
            screen, SHOP_SCREEN_NAME, '按钮-收起')
        self._op.park_cursor(before_wait=0.5, after_wait=0.1)   # 同 R3:验证「收起消失」前 park
        # DD-011:收起动画 ~1s(#15)自等;关态验证 = 「收起消失」(建档 area)。
        time.sleep(SHOP_CLOSE_ANIM_S)
        ok = not self._op.round_by_find_area(
            self._op.screenshot(), SHOP_SCREEN_NAME,
            '按钮-收起').is_success
        return ok, f'关商店 {"✓" if ok else "收起仍在"}'

    # ===== 战斗域 =====

    def _start_battle(self) -> tuple[bool, str]:
        """出战发射:常规发射 → 未落地原样重发(长按下) → 仍败计连败停机留证。

        恢复语义(用户裁定 2026-08-30):禁用 active_window 激活——激活会抢占
        用户桌面焦点,自主推进运行期不可接受,无例外;重发=同通道原样重试。
        连续失败达限 → 停机留证(截图+flag+stop_running,与 bail ping-pong
        停机同款三要素),根因判定交人工:留证线索=输入投递机制状态
        (SendInput 落点 vs 真前台句柄)与游戏侧输入管线状态。
        """
        ok, detail = self._launch_attempt()
        if ok:
            self._launch_dead_reset()
            return True, detail
        log.warning('[cw!][battle] 出战未落地(%s) → 原样重发(长按下)', detail)
        # 重发段 press_time=0.15:人工解锁实证参数(2026-08-30 16:31 手动 click_game
        # 0.15 即生效)——输入管线半死态下短按下可能不被采样,重发放长按下加固。
        ok2, detail2 = self._launch_attempt(press_time=0.15)
        if ok2:
            self._launch_dead_reset()
            return True, f'{detail2}(重发)'
        self._op.save_screenshot()   # 诊断存证(同 battle_prep:bug#1 drag vs overlay 挡 vs 坐标偏)
        if '未落地' not in detail2:
            return False, f'出战失败(重发后): {detail2}'
        escalated = self._launch_dead_escalate()
        if escalated is not None:
            return False, escalated
        return False, f'出战 click 未落地(重发后仍在备战;首次: {detail})'

    def _launch_attempt(self, press_time: float = 0.1) -> tuple[bool, str]:
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
        screen = self._op.screenshot()
        _btn_area = '按钮-出战'
        _btn_screens: list[str] = [SCREEN_NAME, '货币战争-备战-开商店']
        _btn_found = any(
            self._op.round_by_find_area(screen, _sc, '按钮-出战').is_success
            for _sc in _btn_screens)
        if not _btn_found:
            if any(self._op.round_by_find_area(screen, _sc, '按钮-跳过', crop_first=False).is_success
                   for _sc in _btn_screens):
                _btn_area = '按钮-跳过'   # 免战牌子态:跳过=本节点直进(免战次数-1)
                log.info('[cw][battle] 出战按钮为子态「跳过」(免战牌激活)→ 点跳过')
            else:
                return False, '找不到出战按钮'
        btn = area_center(self._ctx, _btn_area) or PrepActionExecutor.BATTLE_FALLBACK
        self._ctx.controller.mouse_move(btn)   # bug#1 缓解(2026-08-06 r9 实打出战 click ×4 未落地)
        self._ctx.controller.click(btn, press_time=press_time)
        # r9 失焦守卫:click 后验窗口焦点,失焦 → game_win.active() 激活 + 重点一次
        # (live 实证 2026-08-18:窗口后台化时输入静默丢,截图正常 → 环僵尸 20min;
        # MCP click 激活后立即恢复。active() 是框架窗口原语,见 pc_game_window)。)
        try:
            time.sleep(0.4)
            if not self._ctx.controller.game_win.is_win_active:
                log.warning('[cw!][battle] 窗口失焦(输入静默丢)→ 激活 + 重试出战')
                self._ctx.controller.game_win.active()
                time.sleep(0.3)
                self._ctx.controller.mouse_move(btn)
                self._ctx.controller.click(btn, press_time=press_time)
        except Exception:   # noqa: BLE001  焦点守卫 best-effort(无窗口对象则跳过)
            pass
        for _ in range(6):   # 6 × 0.5s 轮询窗口(同 battle_prep D-70)
            time.sleep(0.5)
            scr = self._op.screenshot()
            if self._op.round_by_find_area(scr, '货币战争-未达上限警告', '标识-未达上限警告').is_success:
                # M16 死循环根因修复(ADR-0136):只点确认不勾「本局不再提示」→ 人口不足时**每次**出战
                # 都弹此窗;确认后若弹窗未消(点击落空/动画)轮询重进 → 外层判"仍在备战"=fail → 死循环 86min。
                # 对齐 CwScreenDeployNotFull 完整行为:勾选(幂等,已勾无害)→ 确认 → 下轮验消失。
                check = (area_center(self._ctx, '勾选-本局不再提示', '货币战争-未达上限警告')
                         or PrepActionExecutor.CHECKBOX_FALLBACK)
                self._ctx.controller.mouse_move(check)
                self._ctx.controller.click(check)
                time.sleep(0.3)
                confirm = (area_center(self._ctx, '按钮-确认', '货币战争-未达上限警告')
                           or PrepActionExecutor.CONFIRM_FALLBACK)
                self._ctx.controller.mouse_move(confirm)   # bug#1 缓解(review M-5)
                self._ctx.controller.click(confirm)
                time.sleep(1.0)
                continue
            if not self._op.round_by_find_area(scr, SCREEN_NAME, '备战标识-购买经验').is_success:
                # P4R 弹窗污染守卫(1-1 事故):备战标识消失 ≠ 出战成功——
                # 「前台区域无角色」等确认弹窗同样盖掉标识(实锤:假成功 →
                # 交回外循环 → 「确认关闭→重部署」无限 round_wait 死循环)。
                # 出战被拒弹窗在场 = 失败,交上层「带验证的重部署 → 再出战」链。
                time.sleep(0.6)   # 弹窗渲染窗(标识消失帧可能早于弹窗)
                _post = self._op.screenshot()
                for _bscr, _banchor in PrepActionExecutor.POST_LAUNCH_BLOCKERS:
                    if self._op.round_by_find_area(_post, _bscr, _banchor).is_success:
                        return False, f'出战被拒:弹窗 {_banchor}(标识消失为弹窗污染,非转移)'
                log.info('[cw][battle] 出战成功 → 备战标识消失(无拦截弹窗)')
                return True, '出战成功'
        return False, '出战 click 未落地(6×0.5s 轮询+失焦守卫后仍在备战)'

    def _launch_dead_reset(self) -> None:
        """发射成功/环内任何成功发射 → 清连败计数(输入通道已恢复的证据)。"""
        match = getattr(self._ctx, 'cw_match', None)
        session = getattr(match, 'session', None) if match is not None else None
        if session is not None and getattr(session, 'launch_dead_streak', 0):
            session.launch_dead_streak = 0

    def _launch_dead_escalate(self) -> str | None:
        """发射连败升级:未落地连发达限 → 停机留证(返回失败 detail);未达限返回 None。

        只对「未落地」型失败计数(识别类失败如找不到按钮不是输入通道问题);
        计数挂 session(跨环重入存活——环级计数随 Director 重建清零,挡不住
        round_fail → 外环重入的 2min/次僵尸循环,两局实证)。
        """
        match = getattr(self._ctx, 'cw_match', None)
        session = getattr(match, 'session', None) if match is not None else None
        if session is None:
            return None
        streak = getattr(session, 'launch_dead_streak', 0) + 1
        session.launch_dead_streak = streak
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
            stop_shot = self._op.save_screenshot(prefix='launch_dead')
        except Exception:
            log.error('[cw!][battle] launch_dead 取证截图失败(last 帧通道)', exc_info=True)
        if not stop_shot:
            try:
                _ts, _img = self._ctx.controller.screenshot(independent=True)
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
        rc = getattr(self._ctx, 'run_context', None)
        if rc is not None:
            with contextlib.suppress(Exception):
                rc.stop_running(reason='hook:cw_launch_dead')
        return f'出战 click 未落地×{streak} → 停机留证(hook:cw_launch_dead)'

    # ===== 组合动作(P1 过渡;旧 op 内部一行不动)=====

    def _run_composite(self, name: str, op_path: str) -> tuple[bool, str]:
        """执行组合动作(按模块路径延迟导入,避免 prep_actions ↔ operations 循环导入)。"""
        import importlib

        module_path, cls_name = op_path.rsplit('.', 1)
        op_cls = getattr(importlib.import_module(module_path), cls_name)
        result = op_cls(self._ctx).execute()
        # live 修复(2026-08-14):OperationResult 字段是 success(非 is_success —— 那是
        # OperationRoundResult 的字段);旧 getattr 恒 False → 组合动作全被误判失败。
        ok = bool(result is not None and getattr(result, 'success', False))
        status = getattr(result, 'status', '')
        log.info(f'[cw][composite] {name} → {"✓" if ok else "✗"} {status}')
        return ok, f'{name} {status}'


# ===== 恢复原语(§13.3;动作连败 2 次时先试,bail 是恢复失败后的上抛)=====


def try_recovery(op: SrOperation, ctx: SrContext) -> tuple[str, bool]:
    """恢复原语:已知弹层分型关闭(检测到才动,bug#2 合规),未知 → 点真空白(960,530)兜底。

    返回 (原语描述, 是否关过已知弹层)。closed_known 供 Director 恢复无效时**分型**(review
    H-2:关过已知弹层仍败 = 弹层顽固 → BailToOuter 交外环;无已知弹层仍败 = 状态/识别类
    失败 → 本环屏蔽该动作)。调用后外层靠下一步动作是否恢复判断效果。
    """
    screen = op.last_screenshot
    # 消耗品详情 modal(签名:消耗品 + 拖动到 双条件;L-2:双条件精确,单「消耗品」易误)→ ESC
    if (op.round_by_ocr(screen, '消耗品', lcs_percent=0.9).is_success
            and op.round_by_ocr(screen, '拖动到', lcs_percent=0.9).is_success):
        ctx.controller.btn_tap('esc')
        return 'ESC 关消耗品详情', True
    # 可合成列表 overlay → ESC
    if op.round_by_ocr(screen, '可合成列表', lcs_percent=0.8).is_success:
        ctx.controller.btn_tap('esc')
        return 'ESC 关可合成列表', True
    # 角色详情面板 → 点空白(960,530 真空白 = 前后排之间;700,400 旧值前排有人时=前排-1 槽,已修)
    if op.round_by_ocr(screen, '角色详情', lcs_percent=0.8).is_success:
        ctx.controller.mouse_move(Point(960, 530))   # live 2026-08-14:恢复点击也要 mouse_move(bug#1)
        ctx.controller.click(Point(960, 530))
        return '点空白关角色详情', True
    # 概率表弹窗 → 点 ×(1501,263;VLM live 定位 2026-08-14,与原建档 1502,258 同点)。MED-5:
    # area 化检测(标识-刷新概率表 id_mark)—— 旧全屏 OCR「概率」lcs=0.7 过松会误中商店文本。
    # live 实锤(2026-08-14 1-2):恢复点击无 mouse_move 被 bug#1 吃掉 → 弹窗关不掉 → bail 链停机。
    if op.round_by_find_area(screen, '货币战争-商店刷新概率表', '标识-刷新概率表',
                             crop_first=False).is_success:
        ctx.controller.mouse_move(Point(1501, 263))   # bug#1 缓解(live 实锤必须)
        ctx.controller.click(Point(1501, 263))
        return '点×关概率表', True
    # 未知弹层兜底:点真空白 —— **仅当画面是备战屏**(r10 review 治本:M53 实锤在投资策略屏上
    # 盲点 (960,530)=中卡描述区正中 → 误开星徽详情弹窗 → 15 streak 停机。固定点在未知屏上
    # 永远是赌注;非备战屏不点,让环走 overlay 白名单 bail / 外环接管)。
    if op.round_by_find_area(screen, '货币战争-备战', '备战标识-购买经验',
                             crop_first=False).is_success:
        ctx.controller.mouse_move(Point(960, 530))   # bug#1 缓解
        ctx.controller.click(Point(960, 530))
        return '点空白兜底(960,530,已验备战屏)', False
    return '非备战屏不点(避免盲点误触,交 overlay 检测/外环)', False
