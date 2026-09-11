"""货币战争 工具消耗 op:admitted_tool_actions(G1 准入)→ 逐件拖曳执行 → 消耗确认通道。

**机制(D-36/D-40;机制篇 §5)**:工具件(category='工具')不可 drag 穿,
但其消耗交互仍是 owned 多列网格内的 icon→icon 拖曳——冶金炉拖到一件装备
icon 上(原地变异为同类型随机装备),特权赋予卡拖到一件进阶装备 icon 上
(原地名字替换为对应特权装备)。两者均与穿戴类共用「区域-道具装备」
建档(D-40,col2 冶金炉 click 实锤),无新画面。

**判据面单一源**(策略侧,禁本层第二套时机判断——与 ADR-0461 裁定 3 同理):
``cw_equip_env.evaluate_tool_actions``(10 号稿 §2.1 三道门冷启动分支)
→ ``admitted_tool_actions``(G1 发射位准入,TOOL_EXEC_CHANNEL_READY,
ADR-0529/流程:197)。本 op 只消费 admitted 的 usable 件:
- ``furnace_single``:冶金炉 drag → 死库存件(recycle_qualified 命中)icon;
- ``privilege_upgrade``:特权卡 drag → key 对应进阶成品 icon(栏内拖法,
  21 号稿 §3.4「精确控制配对」);
- 其余动作(扳手/投影仪/令牌)判据面 fail-closed,永不进 admitted;
  万一出现未知 usable 动作 = 实现分歧 → 日志披露 + 跳过(不猜交互)。

**工具消耗确认通道**(21 号稿 §3.2 硬门,四态登记+三分支):拖曳后
pre/post owned 现读对拍(``classify_tool_consume`` 纯函数):
- 成功 = 工具消失 ∧ 目标件消失 → 全量登记(目标件 −1 + 新件待实读 +1);
- 部分消费 → 按「画面现读」登记实际发生面,显影 ``tool_partial_consume``;
- 取消/拖曳落空(工具与目标原样)→ 全量不登记,显影
  ``tool_consume_cancel``(防静默重试不可见)。
对账基准 = 登记后由 prep_obs heavy 覆盖点与现读对拍(与穿戴登记同型)。

前置(与 CwOpEquipAll 同):入口预期屏执行断言「货币战争-备战」,非预期屏
round_fail 交回外循环(T-163 D5 降级,旧 success-skip 假成功形态已废)。
发射位 = mandate_v1 M7.5(逐备战帧评估,admitted 非空才发
RunTools;执行位闩 = mandate.mark_tools_pass_executed)。
"""
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_equip_env import (
    admitted_tool_actions,
    evaluate_tool_actions,
)
from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.obs.cw_equipment import (
    read_equips,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp

# 拖曳参数(与 CwOpEquipAll 拖拽失败降级同型口径;工具 icon→icon 同网格,
# 距离短,首档参数即可,不建补救链——失败由确认通道 cancel 分支如实上报,
# 重算归分发层下一环重派,ADR-0601 §3)
_TOOL_DRAG_HOLD: float = 0.5
_TOOL_DRAG_DURATION: float = 1.2
_TOOL_MAX_PER_PASS: int = 4   # 单 pass 执行硬上限(防 owned 全死库存时超时)
_TOOL_RETRY_PER_ACTION: int = 2   # 单动作重试预算(超预算 → cancel 分支停手)


@dataclass(frozen=True)
class ToolDragPlan:
    """单件工具的执行计划(纯数据;发射位产出 → 执行位消费)。

    ``tool``/``target`` = 注册名;``tool_pos``/``target_pos`` = owned 网格
    内 icon 中心坐标(1080p 游戏空间,现读快照)。``tool_pos=None`` 表示
    计划面有件但画面未识别到 icon(识别 miss)→ 执行位跳过并披露。
    """
    action: str
    tool: str
    target: str
    tool_pos: tuple[int, int] | None
    target_pos: tuple[int, int] | None


def plan_tool_drags(admitted: list, owned_hits: list,
                    comp: 'Comp | None') -> list[ToolDragPlan]:
    """admitted 判据产物 → 逐件拖曳计划(纯函数,离线可锁)。

    ``admitted`` = ``admitted_tool_actions`` 输出(ToolAction 列表,只消费
    usable 件);``owned_hits`` = read_equips 命中 [(名, (cx, cy), score)];
    ``comp`` = target_comp(key_equips 载体,炉目标过滤与特权映射同源)。
    - furnace_single:目标 = owned 中死库存件(b ∈ ``recycle_qualified``)
      ——直接复用判据面同源纯函数(同判定非第二套判据),禁「画面可读
      首件」这类宽取:误烧需求向量内件 = 判据面已把门的负操作。
    - privilege_upgrade:目标 = key 特权件对应进阶成品(判据面
      ``_privilege_base_name`` 同族映射,owned ∩ 候选取画面可读首件)。
    判据面放行但画面 icon 未识别到 / 目标件现读已消失(合成消耗/reflow
    miss)→ 计划照产(位置 None)交执行位披露,不静默。
    """
    from sr_od.application.currency_war.data.cw_synthesis import (
        recycle_qualified,
    )
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        _privilege_base_name,
    )
    pos_by_name: dict[str, tuple[int, int]] = {}
    for name, pos, _score in owned_hits:
        pos_by_name.setdefault(name, (int(pos[0]), int(pos[1])))
    keys = list(getattr(comp, 'key_equips', None) or []) if comp is not None \
        else []
    plans: list[ToolDragPlan] = []
    for a in admitted:
        if not a.usable:
            continue
        tool_pos = pos_by_name.get(a.tool)
        if a.action == 'furnace_single':
            rq = recycle_qualified(keys)
            tgt = next((n for n in pos_by_name
                        if n != a.tool and n in rq), None)
            plans.append(ToolDragPlan(a.action, a.tool, tgt or '', tool_pos,
                                      pos_by_name.get(tgt) if tgt else None))
        elif a.action == 'privilege_upgrade':
            # 目标 = key 特权件对应进阶成品(key 带「·特权」后缀去后缀得
            # 基名,判据面 _privilege_base_name 同族映射;owned ∩ 取首件)
            priv_targets = {_privilege_base_name(k)
                            for k in keys
                            if _privilege_base_name(k) is not None}
            tgt = next((n for n in pos_by_name if n in priv_targets), None)
            plans.append(ToolDragPlan(a.action, a.tool, tgt or '', tool_pos,
                                      pos_by_name.get(tgt) if tgt else None))
        else:
            # 未知 usable 动作 = 判据面扩容未同步执行面 → 不猜交互
            log.warning('[cw-tools] 未知 usable 工具动作 %s/%s → 跳过'
                        '(执行面未建模,禁猜)', a.tool, a.action)
    return plans


def owned_hits_names(owned_hits: list) -> list[str]:
    """read_equips 命中 → 名单(顺序保留;纯函数)。"""
    return [n for n, _p, _s in owned_hits]


def classify_tool_consume(pre_owned: list[str], post_owned: list[str],
                          tool: str, target: str) -> tuple[str, list[str], list[str]]:
    """消耗确认通道对拍(21 号稿 §3.2 三分支;纯函数,离线可锁)。

    返回 (outcome, removed, added):
    - ``consumed``:工具消失 ∧ 目标消失 → removed 含工具+目标,added =
      post−pre 全量(变异新件名可读时进 added,不可读时 post 侧识别
      miss 自然不进——对账由 heavy 覆盖点兜)。
    - ``partial``:工具或目标任一消失但非全消 → 按现读登记实际发生面
      (removed/added = 逐名 diff),消费方显影 tool_partial_consume。
    - ``cancel``:工具与目标原样 → 空登记(无账面变化)。
    多副本计数按 multiset diff 逐名算,不吃单一名单集合化(同件多张
    特权卡/同件多份时 diff 保真)。
    """
    def _counts(names: list[str]) -> dict[str, int]:
        c: dict[str, int] = {}
        for n in names:
            c[n] = c.get(n, 0) + 1
        return c

    pre, post = _counts(pre_owned), _counts(post_owned)
    tool_consumed = post.get(tool, 0) < pre.get(tool, 0)
    target_consumed = post.get(target, 0) < pre.get(target, 0)
    removed = sorted(k for k in pre
                     if pre.get(k, 0) > post.get(k, 0))
    added = sorted(k for k in post
                   if post.get(k, 0) > pre.get(k, 0))
    if tool_consumed and target_consumed:
        return 'consumed', removed, added
    if tool_consumed or target_consumed:
        return 'partial', removed, added
    return 'cancel', [], []


def run_tool_queue(queue: list[ToolDragPlan], exec_fn,
                   max_pass: int = _TOOL_MAX_PER_PASS) -> tuple[int, int, bool]:
    """工具执行环驱动(纯控制流,注入执行;离线可锁)。

    while 队列循环逐件执行;**首件 consumed/partial 后画面网格 reflow →
    剩余计划坐标全部作废**(三审定谳:沿用切片快照的过期坐标拖曳 = 误烧
    负操作,已落错的首次拖曳确认通道救不回)。ADR-0601 §3 整改:op 内
    不再重评准入自建新队列(replan 删除——「重评 admitted」是策略判据的
    第二次触发,违反动作 op 机械执行规范),计划失效如实上报交回分发层,
    下一环重派即天然重算(发射位 G1 对 fresh owned 重评 = 判据单一源;
    _click_spheres「观察-执行竞态 → 下轮再派」同形先例)。cancel 件直接
    丢弃(exec_fn 内重试预算已耗尽,同件原地重拖失败相关,bug#1 结论;
    画面未消费 = 无 reflow,队列其余坐标仍有效,继续下一件)。
    ``max_pass`` = 执行尝试硬上限(防异常态空转)。
    返回 (consumed, attempts, plan_stale)——plan_stale = 有剩余计划因
    reflow 作废(调用方须 round_fail 上报,不得当合法完成)。
    """
    consumed = attempts = 0
    plan_stale = False
    while queue and attempts < max_pass:
        plan = queue.pop(0)
        outcome = exec_fn(plan)
        attempts += 1
        if outcome == 'consumed':
            consumed += 1
        if outcome != 'cancel':
            # 消费发生(consumed/partial)→ 网格 reflow,剩余计划坐标作废
            plan_stale = bool(queue)
            break
    return consumed, attempts, plan_stale


class CwOpTools(SrOperation):
    """备战:G1 准入 admitted 工具动作 → 逐件 drag → 消耗确认通道对拍登记。

    入口预期屏执行断言(非干净备战如实 fail 交回外循环,T-163 D5;判断
    上提 _run_composite 派发前置);出口验真转移(确认通道 consumed 才算
    成,partial/cancel 计入观测披露——发射位闩在执行位成功返回时置位,
    单 pass 语义与 M7 穿戴闩同型)。
    """

    SCREEN_NAME: str = '货币战争-备战'
    # 失败状态具名常量(ADR-0601 §4;禁散字符串,判读侧可分键)。
    STATUS_PLAN_STALE: str = '工具计划失效(首件消费后 reflow,剩余计划作废)'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-工具消耗')

    def _get_templates(self) -> 'dict[str, tuple[MatLike, tuple, object]] | None':
        """加载 cw_equip SIFT 模板(单一源 = cw_op_equip_all 共享 helper)。"""
        from sr_od.application.currency_war.operations.cw_op.cw_op_equip_all import (
            get_equip_templates_cached,
        )
        return get_equip_templates_cached(self.ctx)

    def _read_owned(self) -> list:
        """现读 owned 全量命中([(名, (cx,cy), score)];区域 = 建档单一源)。"""
        rect = _area_rect(self.ctx, '区域-道具装备', self.SCREEN_NAME)
        if rect is None:
            return []
        return read_equips(self.screenshot(), self._get_templates(),
                           equip_rect=(rect.x1, rect.y1, rect.x2, rect.y2))

    def _register_consume(self, session, outcome: str, removed: list[str],
                          added: list[str], tool: str, target: str) -> None:
        """工具消费确认通道(两态制 ADR-0651 后 = 纯日志留证位)。

        原「逐名 diff 登记 owned 期望态」随 expected_state 条目表废除——
        消费真值 = ``_exec_plan`` 的拖后现读对拍(post_names,观察),无
        挂账条目可登记;本方法保留为消费事实日志面(判读留证)。"""
        if outcome == 'cancel':
            return
        log.info('[cw-tools][fact] tool=%s target=%s outcome=%s '
                 'removed=%s added=%s', tool, target, outcome, removed, added)

    def _exec_plan(self, plan: ToolDragPlan) -> tuple[str, list[str], list[str]]:
        """单计划执行:drag → 现读对拍 → (outcome, removed, added)。"""
        assert plan.tool_pos is not None and plan.target_pos is not None
        pre_names = owned_hits_names(self._read_owned())
        for attempt in range(_TOOL_RETRY_PER_ACTION):
            start = Point(*plan.tool_pos)
            end = Point(*plan.target_pos)
            self.ctx.controller.mouse_move(start)
            time.sleep(0.2)
            self.ctx.controller.drag_to(start=start, end=end,
                                        hold_time=_TOOL_DRAG_HOLD,
                                        duration=_TOOL_DRAG_DURATION)
            time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
            self.park_cursor(after_wait=0.1)
            post_hits = self._read_owned()
            post_names = owned_hits_names(post_hits)
            outcome, removed, added = classify_tool_consume(
                pre_names, post_names, plan.tool, plan.target)
            if outcome != 'cancel':
                return outcome, removed, added
            log.info('[cw-tools] %s→%s 拖曳未落地(cancel,#%d)→ 重试',
                     plan.tool, plan.target, attempt + 1)
            # 重定位:列 reflow/首读错位 → 现读重取坐标(与穿戴补救链同向)
            fresh = {n: p for n, p, _s in post_hits}
            plan = ToolDragPlan(plan.action, plan.tool, plan.target,
                                fresh.get(plan.tool), fresh.get(plan.target))
            if plan.tool_pos is None or plan.tool_pos == plan.target_pos:
                break
        return 'cancel', [], []

    @operation_node(name='工具消耗', is_start_node=True, node_max_retry_times=3)
    def tools_consume(self) -> OperationRoundResult:
        cur = self.screenshot()
        # 入口预期屏执行断言(T-163 D5,与 CwOpEquipAll 同形同批):非预期屏
        # 如实 round_fail 交回外循环,禁假成功吞分发;判断上提见
        # PrepActionExecutor._run_composite 派发前置。
        current = self.check_and_update_current_screen(
            cur, screen_name_list=[self.SCREEN_NAME])
        if current != self.SCREEN_NAME:
            log.warning('[cw!][tools] 当前画面 %s 非预期屏(%s)→ 执行断言 fail',
                        current, self.SCREEN_NAME)
            return self.round_fail(f'不在预期屏: {current}')
        templates = self._get_templates()
        if templates is None:
            return self.round_fail('cw_equip 模板库未加载')
        hits = self._read_owned()
        if not hits:
            return self.round_success('owned 识别空,无工具面')
        owned_names = owned_hits_names(hits)
        _match = getattr(self.ctx, 'cw_match', None)
        _sess = getattr(_match, 'session', None) if _match is not None else None
        comp = getattr(strategy_state_of(_sess), 'target_comp', None) if _sess is not None else None
        # 判据 → G1 准入(策略侧单一源;本层禁第二套时机判断)
        admitted = admitted_tool_actions(evaluate_tool_actions(owned_names, comp))
        for a in admitted:
            log.info('[cw!][tools] tool=%s action=%s usable=%s reason=%s',
                     a.tool, a.action, a.usable, a.reason or '-')
        all_plans = plan_tool_drags(admitted, hits, comp)
        plans = [p for p in all_plans
                 if p.tool_pos is not None and p.target_pos is not None
                 and p.target]
        skipped = [p for p in all_plans if p not in plans]
        if skipped:
            log.info('[cw-tools] 计划面缺 icon(识别 miss)跳过: %s',
                     [(p.tool, p.target) for p in skipped])
        if not plans:
            return self.round_success('无可用工具动作(判据拒/准入拒见 [cw!][tools] 分键)')

        def _exec(plan: ToolDragPlan) -> str:
            outcome, removed, added = self._exec_plan(plan)
            self._register_consume(_sess, outcome, removed, added,
                                   plan.tool, plan.target)
            if outcome == 'consumed':
                log.info('[cw-tools] %s→%s 消费成功 removed=%s added=%s',
                         plan.tool, plan.target, removed, added)
            elif outcome == 'partial':
                log.warning('[cw!][tools] tool_partial_consume %s→%s '
                            'removed=%s added=%s', plan.tool, plan.target,
                            removed, added)
            else:
                log.info('[cw!][tools] tool_consume_cancel %s→%s(重试预算耗尽)',
                         plan.tool, plan.target)
            return outcome

        # 旧 op 内 _replan(fresh owned 重评 admitted 再建队列)已删(ADR-0601
        # §3):「重评 admitted」是策略判据在 op 内第二次触发,违反动作
        # op 机械执行规范;计划失效改由 plan_stale 如实上报交回分发层重算。
        consumed, _attempts, _plan_stale = run_tool_queue(plans, _exec)
        if _plan_stale:
            # 计划失效上报(C3):闩不置位(execute ok=False),下一环重派
            # 即天然重算(发射位 G1 对 fresh owned 重评 = 判据单一源)。
            log.info('[cw-tools] 首件消费后剩余计划失效(reflow)→ round_fail '
                     '交回分发层(本环已消费 %d 件)', consumed)
            return self.round_fail(CwOpTools.STATUS_PLAN_STALE)
        return self.round_success(f'工具消费 {consumed} 件(确认通道对拍完成)')
