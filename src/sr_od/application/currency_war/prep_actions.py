# 未验证(P1 新建,2026-08-14;设计 doc 15 v7 + ADR-0123;op 流程待实机跑验)

"""货币战争 备战决策环 原子动作全集 + 执行器(P1;doc 15 §4/§13)。

框架层:本模块**不含玩法判断**(何时收球/卖谁/何时出战 = 策略层 CwStrategy.decide_prep_action),
只负责「执行一个动作 + 完成验证」。三失败路径(§13.2):
- 验证失败 → execute 返回 progressed=False(PrepDirector 计 fail/屏蔽);
- 参数非法 → validate 返回错误串(Director 拒绝执行 + 该步计 stall + telemetry);
- 执行异常 → 异常上抛(Director 上抛 = 本环 fail,外层 op retry 接管)。

slot 语义全局统一(§13.1):**物理槽位** —— 备战栏 1-9 / 前排 1-4 / 后排 1-N;非 bench 列表下标!
组合动作命名映射(§7 L1):RunBuyPhase=BuyShopCards / RunDeploy=DeployBench / RunEquip=EquipAll
(P1 过渡,P2/P3 溶解为原子)。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_identity_obs import (
    read_reward_spheres,
    read_supply_boxes,
)
from sr_od.application.currency_war.cw_obs_core import (
    SCREEN_NAME,
    SHOP_SCREEN_NAME,
    _area_rect,
    _ocr,
    area_center,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# ===== 动作全集(§13.1)=====


class PrepAction:
    """备战决策环动作标记基类(策略 → 框架的单步意图载体)。"""


@dataclass
class DeferSpheres(PrepAction):
    """控制流:奖励球留置(本环不再尝试;不计 stall,计步数;§4.2b)。"""


@dataclass
class BailToOuter(PrepAction):
    """控制流:中止本环交外环(弹层/事件;框架信号不走验证链;§4.2b)。"""
    reason: str = ""


@dataclass
class ClickSpheres(PrepAction):
    """点奖励球(带上界批,大球优先,内验早停;掉箱即停回环交规则统筹)。"""
    max_k: int = 1


@dataclass
class OpenBox(PrepAction):
    """开补给箱(点「开启」→ 弹武装箱 overlay;开箱即腾席)。slot=None → 第一箱。"""
    slot: int | None = None


@dataclass
class PickBoxCard(PrepAction):
    """武装箱 4 选 1 点卡。card_idx=None → 执行器内嵌默认选卡(v7 M-3:P1 住执行器,P5 上移策略)。"""
    card_idx: int | None = None


@dataclass
class SellBench(PrepAction):
    """卖备战席角色(slot=物理槽位 1-9;身份感知「卖谁」由策略层保证)。"""
    slot: int


@dataclass
class SellDeployed(PrepAction):
    """卖已上阵角色(row=front/back + 物理槽位)。"""
    row: str
    slot: int


@dataclass
class DeployMove(PrepAction):
    """bench → 上阵单步拖拽(腾席链专用,P1;组合部署走 RunDeploy 保四项板上行为)。"""
    from_slot: int
    to_row: str            # "front" / "back"
    to_slot: int


@dataclass
class LevelUp(PrepAction):
    """买经验升等级(点「购买经验」循环至 level+1;cap+1 = 腾席链 b 步)。"""


@dataclass
class EnsureShopOpen(PrepAction):
    """开商店(gold 只在开态可读;§3 读取前置管理)。"""


@dataclass
class EnsureShopClosed(PrepAction):
    """关商店(HP 只在关态可读)。"""


@dataclass
class StartBattle(PrepAction):
    """出战(环出口;含未达上限确认;验证=备战标识消失)。StartBattle 豁免屏蔽(§7)。"""


@dataclass
class RunBuyPhase(PrepAction):
    """组合(P1 过渡):整段买牌 = BuyShopCards(P2 溶解为原子)。"""


@dataclass
class RunDeploy(PrepAction):
    """组合(P1 过渡):整体部署 = DeployBench(v7 H-2:保 D-10 换血/同角色去重/前排保证/cap 门
    四项板上行为,P3 原子化时上移策略)。"""


@dataclass
class RunEquip(PrepAction):
    """组合(P1 过渡):全员装备 = EquipAll(P3 溶解为 WearEquip)。"""


# 动作全集白名单(F3 membership 校验,review M-4;新动作加入全集时同步此处)
PREP_ACTION_TYPES: tuple = (
    DeferSpheres, BailToOuter, ClickSpheres, OpenBox, PickBoxCard,
    SellBench, SellDeployed, DeployMove, LevelUp,
    EnsureShopOpen, EnsureShopClosed, StartBattle,
    RunBuyPhase, RunDeploy, RunEquip,
)


def action_key(action: PrepAction) -> str:
    """动作实例键(屏蔽计数粒度 = 动作类型 + 参数,§13.2;SellBench(3) 与 SellBench(5) 各自计数)。"""
    import dataclasses

    if dataclasses.is_dataclass(action):
        params = dict(vars(action))
        if not params:
            return type(action).__name__   # 无字段 dataclass(StartBattle 等)→ 裸名
        return f'{type(action).__name__}({params})'
    return type(action).__name__


def _read_level_raw(ctx: SrContext, screen) -> int | None:
    """OCR 直读等级数字(「文本-等级」区,**无 _expected_level 兜底**;review MED-8)。

    read_level 的兜底曲线适合决策估值,不适合完成验证(期望值>实际时假成功)。漏读返 None,
    调用方决定基线退路。
    """
    from sr_od.application.currency_war.cw_obs_core import (
        LEVEL_MAX,
        LEVEL_MIN,
        _first_int,
        _ocr,
    )

    rect = _area_rect(ctx, '文本-等级')
    if rect is None:
        return None
    v = _first_int([r.data for r in _ocr(ctx, screen, rect)])
    if v is not None and (LEVEL_MIN <= v <= LEVEL_MAX):
        return v
    return None


def row_area_centers(ctx: SrContext, prefix: str) -> list[Point]:
    """从 screen_info「货币战争-备战」读全部 prefix-N 区域中心(N 升序)。

    同 DeployBench._row_centers 逻辑(读全不硬编码,后排 >6 时 screen_info 补区后自动跟上);
    prep_actions 执行器 / prep_director 观察共用。
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


class PrepActionExecutor:
    """备战原子/组合动作执行器(框架层;持 ctx + 宿主 op 复用截图/区域匹配/拖拽原语)。

    宿主 op = PrepDirector(SrOperation);所有验证经 op.round_by_find_area / OCR,
    拖拽统一走 DragCwChar.drag_char(中心拖 + hold0,2026-08-13 实测验证)。
    """

    SELL_POINT: ClassVar[Point] = Point(70, 846)      # 出售区(左下,同 deploy_bench/_handle_bench_full)
    BOX_SCREEN: ClassVar[str] = '货币战争-备战-武装箱选择'
    BOX_OPEN_DY: ClassVar[int] = 41                   # 「开启」文字区 = 箱 icon 下方偏移(handle_supply_box 实测)
    CARD_Y: ClassVar[int] = 290                       # 武装箱卡身点击 y(点卡名下方一点避「查看详情」)
    LEVEL_MAX_CLICKS: ClassVar[int] = 12              # 升级单动作最多买经验次数(同 _handle_bench_full 量级)
    SPHERE_MAX_CLICKS: ClassVar[int] = 12             # 单动作点球硬上限(防识别抖动死循环)
    BATTLE_FALLBACK: ClassVar[Point] = Point(1817, 749)   # 出战按钮兜底(同 battle_prep)
    CONFIRM_FALLBACK: ClassVar[Point] = Point(1159, 653)  # 未达上限确认兜底(同 battle_prep)
    CHECKBOX_FALLBACK: ClassVar[Point] = Point(912, 589)   # 本局不再提示勾选兜底(ADR-0136;同 HandleDeployNotFull)

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
        elif isinstance(action, PickBoxCard):
            if action.card_idx is not None and not (1 <= action.card_idx <= 4):
                return f'PickBoxCard card_idx={action.card_idx} 越界(1-4)'
        return None

    # ===== 执行入口(三失败路径之「验证失败」→ (False, detail);异常自然上抛)=====

    def execute(self, action: PrepAction) -> tuple[bool, str]:
        """执行动作 → (progressed, detail)。progressed=完成验证过的进展。"""
        if isinstance(action, ClickSpheres):
            return self._click_spheres(action)
        if isinstance(action, OpenBox):
            return self._open_box(action)
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
        if isinstance(action, RunBuyPhase):
            return self._run_composite('买牌', 'sr_od.application.currency_war.operations.prep.shop.BuyShopCards')
        if isinstance(action, RunDeploy):
            return self._run_composite('部署', 'sr_od.application.currency_war.operations.prep.deploy_bench.DeployBench')
        if isinstance(action, RunEquip):
            return self._run_composite('装备', 'sr_od.application.currency_war.operations.prep.equip_all.EquipAll')
        if isinstance(action, (DeferSpheres, BailToOuter)):   # 本模块定义,无需导入
            return False, '控制流动作不经 execute(框架信号,§4.2b;环应在控制流分支拦下)'
        return False, f'未知动作类型 {type(action).__name__}'

    # ===== 奖励域 =====

    def _click_spheres(self, action: ClickSpheres) -> tuple[bool, str]:
        """逐球点击(大球优先)→ 只计**验证消失**的球;掉箱即停(下步 OpenBox 统筹,v5 定);席满停。

        review H-3:progressed 只认真进展 —— 每次点击后重读,球数减少才 verified+1;
        点击落空(球没少 = 席满/遮挡)不计进展 → 返 False 走环的 fail/恢复路径(§13.2)。
        """
        clicked = 0
        verified = 0
        budget = min(action.max_k, PrepActionExecutor.SPHERE_MAX_CLICKS)
        screen = self._op.screenshot()
        if not read_reward_spheres(self._ctx, screen):
            return True, '无球(观察-执行竞态,无事可做)'   # LOW-2:不计验证失败
        while clicked < budget:
            spheres = read_reward_spheres(self._ctx, screen)
            if not spheres:
                break
            before = len(spheres)
            color, center, r = max(spheres, key=lambda t: t[2])   # 大球优先(gold r~44 > blue ~32 > gray ~18)
            self._ctx.controller.mouse_move(center)   # bug#1 缓解
            self._ctx.controller.click(center)
            clicked += 1
            time.sleep(1.2)
            screen = self._op.screenshot()
            after = read_reward_spheres(self._ctx, screen)
            if len(after) < before:
                verified += 1   # 真进展:球消失(入账/落席)
            if read_supply_boxes(self._ctx, screen):
                log.info('[cw][sphere] 点球掉箱 → 停回环(下步 OpenBox 统筹,v5 定)')
                break
            if len(after) >= before:
                log.info(f'[cw][sphere] 球数未减({before}→{len(after)}) → 疑席满点不动,停')
                break
        detail = f'点球 {clicked}/{budget} 验证消失 {verified}'
        log.info(f'[cw][sphere] {detail}')
        return verified > 0, detail

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
        time.sleep(1.5)
        overlay = self._op.screenshot()
        if not self._op.round_by_find_area(overlay, PrepActionExecutor.BOX_SCREEN, '标识-请选择').is_success:
            return False, f'武装箱 overlay 未弹(槽{slot} 点击落空?)'
        log.info(f'[cw][box] 开箱槽{slot} → overlay 弹出 ✓')
        return True, f'开箱槽{slot}'

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
        time.sleep(1.5)
        if self._op.round_by_ocr(self._op.screenshot(), '武装箱', lcs_percent=0.5).is_success:
            return False, f'选卡 {chosen} 后 overlay 仍在'
        log.info(f'[cw][box] 选卡 {chosen} → overlay 关 ✓')
        return True, f'选卡 {chosen}'

    def _default_box_card(self, names: list[tuple[str, int]]) -> tuple[str, int]:
        """执行器内嵌默认选卡(v7 M-3:P1 住执行器,P5 上移策略):key_equips 命中 → 材料通用性 → 第1张。

        逻辑同 HandleSupplyBox._pick_card(P1 复用 _material_value 单一源,不重复建表;
        P5 上移策略时两处归一)。
        """
        from sr_od.application.currency_war.operations.handlers.handle_supply_box import (
            _material_value,
        )

        match = self._ctx.cw_match
        if match is not None and match.session.target_comp is not None:
            key_equips = set(match.session.target_comp.key_equips or [])
            for n, x in names:
                if n in key_equips:
                    return n, x
        best = max(names, key=lambda t: _material_value(t[0]))
        return best

    # ===== 席位域 =====

    def _sell_bench(self, action: SellBench) -> tuple[bool, str]:
        """卖备战槽角色:drag 槽中心 → 出售区;drag_char 内验源槽空。"""
        src = self._bench_pts[action.slot - 1]
        ok = self._drag(src, PrepActionExecutor.SELL_POINT)
        if ok:
            self._track_remove_bench(action.slot)
        return ok, f'卖备战槽{action.slot} {"✓" if ok else "拖3次源槽未变"}'

    def _sell_deployed(self, action: SellDeployed) -> tuple[bool, str]:
        """卖上阵角色:drag 排槽中心 → 出售区;drag_char 内验源槽空。"""
        pts = self._front_pts if action.row == 'front' else self._back_pts
        src = pts[action.slot - 1]
        ok = self._drag(src, PrepActionExecutor.SELL_POINT)
        if ok:
            self._track_remove_deployed(action.row, action.slot)
        return ok, f'卖{action.row}排{action.slot} {"✓" if ok else "拖3次源槽未变"}'

    def _deploy_move(self, action: DeployMove) -> tuple[bool, str]:
        """bench → 上阵单步拖拽(腾席链专用);drag_char 内验源槽空。"""
        pts = self._front_pts if action.to_row == 'front' else self._back_pts
        src = self._bench_pts[action.from_slot - 1]
        dst = pts[action.to_slot - 1]
        ok = self._drag(src, dst)
        if ok:
            self._track_move_deployed(action.from_slot, action.to_row, action.to_slot)
        return ok, f'部署槽{action.from_slot}→{action.to_row}{action.to_slot} {"✓" if ok else "拖3次源槽未变"}'

    def _drag(self, src: Point, dst: Point) -> bool:
        """统一拖拽原语(DragCwChar.drag_char:中心拖+hold0+retry+验源槽像素变)。"""
        from sr_od.application.currency_war.operations.dev.drag_cw_char import (
            DragCwChar,
        )

        return DragCwChar.drag_char(self._op, src, dst)

    def _track_remove_bench(self, slot: int) -> None:
        """卖出后备势跟踪同步(主跟踪 tracked_bench_chars;tracked_bench 旧名列表无法映射物理槽,不动)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        match.session.tracked_bench_chars = [
            bc for bc in match.session.tracked_bench_chars if bc.slot != slot]

    def _track_remove_deployed(self, row: str, slot: int) -> None:
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        match.session.tracked_deployed = [
            bc for bc in match.session.tracked_deployed
            if not (bc.position_pref == row and bc.slot == slot)]

    def _track_move_deployed(self, from_slot: int, to_row: str, to_slot: int) -> None:
        """上阵后备势跟踪同步:bench 条目 → deployed 条目(位置/槽位改写)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        moved = [bc for bc in match.session.tracked_bench_chars if bc.slot == from_slot]
        match.session.tracked_bench_chars = [
            bc for bc in match.session.tracked_bench_chars if bc.slot != from_slot]
        for bc in moved:
            bc.position_pref = to_row
            bc.slot = to_slot
        match.session.tracked_deployed.extend(moved)

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
                log.info(f'[cw][levelup] level {before}→{lv} ✓')
                return True, f'level {before}→{lv}'
        return False, f'点{PrepActionExecutor.LEVEL_MAX_CLICKS}次经验 level 未变({before})'

    def _ensure_shop(self, want_open: bool) -> tuple[bool, str]:
        """开/关商店 + 锚点验证(按钮-收起 可见 = 开态)。"""
        screen = self._op.screenshot()
        is_open = self._op.round_by_find_area(screen, SHOP_SCREEN_NAME, '按钮-收起').is_success
        if want_open:
            if is_open:
                return True, '商店已开'
            r = self._op.round_by_find_and_click_area(
                screen, SCREEN_NAME, '按钮-商店', success_wait=1.5)
            if not r.is_success:
                return False, '找不到按钮-商店'
            time.sleep(0.5)
            ok = self._op.round_by_find_area(
                self._op.screenshot(), SHOP_SCREEN_NAME, '按钮-收起').is_success
            return ok, f'开商店 {"✓" if ok else "收起未出现"}'
        if not is_open:
            return True, '商店已关'
        self._op.round_by_find_and_click_area(
            screen, SHOP_SCREEN_NAME, '按钮-收起', success_wait=1.0)
        time.sleep(0.5)
        still = self._op.round_by_find_area(
            self._op.screenshot(), SHOP_SCREEN_NAME, '按钮-收起').is_success
        return (not still), f'关商店 {"✓" if not still else "收起仍在"}'

    # ===== 战斗域 =====

    def _start_battle(self) -> tuple[bool, str]:
        """出战:mouse_move+click 出战 → 轮询(未达上限确认 / 备战标识消失)。失败存证(bug#1 诊断)。"""
        screen = self._op.screenshot()
        if not self._op.round_by_find_area(screen, SCREEN_NAME, '按钮-出战').is_success:
            return False, '找不到出战按钮'
        btn = area_center(self._ctx, '按钮-出战') or PrepActionExecutor.BATTLE_FALLBACK
        self._ctx.controller.mouse_move(btn)   # bug#1 缓解(2026-08-06 r9 实打出战 click ×4 未落地)
        self._ctx.controller.click(btn)
        for _ in range(6):   # 6 × 0.5s 轮询窗口(同 battle_prep D-70)
            time.sleep(0.5)
            scr = self._op.screenshot()
            if self._op.round_by_find_area(scr, '货币战争-未达上限警告', '标识-未达上限警告').is_success:
                # M16 死循环根因修复(ADR-0136):只点确认不勾「本局不再提示」→ 人口不足时**每次**出战
                # 都弹此窗;确认后若弹窗未消(点击落空/动画)轮询重进 → 外层判"仍在备战"=fail → 死循环 86min。
                # 对齐 HandleDeployNotFull 完整行为:勾选(幂等,已勾无害)→ 确认 → 下轮验消失。
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
                log.info('[cw][battle] 出战成功 → 备战标识消失')
                return True, '出战成功'
        self._op.save_screenshot()   # 诊断存证(同 battle_prep:bug#1 drag vs overlay 挡 vs 坐标偏)
        return False, '出战 click 未落地(3s 仍在备战)'

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
        if name == '装备':
            self._verify_equipped()   # L-1:_verify_equipped 随 RunEquip 保留(自 battle_prep 搬入)
        status = getattr(result, 'status', '')
        log.info(f'[cw][composite] {name} → {"✓" if ok else "✗"} {status}')
        return ok, f'{name} {status}'

    def _verify_equipped(self) -> None:
        """[装备核对钩子·临时] EquipAll 后 read_row_equipped → log(对比 EquipAll 意图核装备识别)。

        自 battle_prep._verify_equipped 搬入(P1 挂载切换,doc §7 L-1:_verify_equipped 不进 Director
        观察阶段,随 RunEquip 组合动作保留)。核完装备 reader 删本方法 + _run_composite 调用。
        """
        try:
            from sr_od.application.currency_war.cw_equipment import (
                ensure_equip_tm_templates,
            )
            from sr_od.application.currency_war.cw_identity_obs import read_row_equipped

            grays = ensure_equip_tm_templates(self._ctx)
            if grays is None:
                return
            scr = self._op.screenshot()
            front = read_row_equipped(self._ctx, scr, grays, '前排', 4)
            back = read_row_equipped(self._ctx, scr, grays, '后排', 6)
            log.info(f'[cw-hook][equip] read 已穿装备: front={front} back={back}')
        except Exception as e:  # noqa: BLE001  live 验证 best-effort,失败不阻塞备战
            log.info(f'[cw-hook][equip] skip: {e}')


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
    # 未知弹层兜底:点真空白
    ctx.controller.mouse_move(Point(960, 530))   # bug#1 缓解
    ctx.controller.click(Point(960, 530))
    return '点空白兜底(960,530)', False
