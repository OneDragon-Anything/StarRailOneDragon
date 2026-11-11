"""差分执行器(24 号稿 §1.3)。

diff = 现板面 vs target_board(就位判定粒度 = **名 + 排 + 星**,
D2-1——槽不进判定)→ 统一拖动/换星直卖动作序列;diff 空 = 显式零
动作。与第 6 步(常规部署调整,零读屏循环 + 入口 heavy 对账)和
计划执行期(拖动与重观察交替,§3.5)共用本执行器——target 来源
不同(第 6 步 = 当前搜索;计划 = 写端定型 T),执行器逻辑同一。

收敛论证(§3.4):非卖步每步至少一名字就位且不被挤回(落位槽选择
规则保证——禁占已就位者的槽);卖步(换星低星直卖)不减少已就位
名字集;排错修正一步到位;星分量两步收敛(低星下场后高星上场即
就位)。

新鲜度守卫(D2-17):下场/交换步涉及 fresh 件(本帧刚买)→ 跳过该步
挂起(防同帧买入即被换下抖动);不拦卖出(卖出归卖出场景/计划变量,
卖侧自有新鲜度排除)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionMoveUnitParam,
    CwActionSellDeployedParam,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )

#: 防御上限(动作序列长度上界;K ≤ 10 时换血全序列 ≤ ~3K,超限 =
#: 生成器 bug 防死循环)。
_DIFF_ACTION_CAP: int = 40


def deploy_diff_actions(
        gs: GameState,
        target: dict[str, tuple[str, int, int | None]],
        *,
        fresh: frozenset[str] = frozenset(),
        ) -> list:
    """现板面 → target 的统一拖动/换星直卖动作序列(§3;幂等——每帧
    重算取序,执行进度由状态容器逻辑态自上报推进)。

    target 值 = (排, 星, 槽位或 None);槽位级(char_positions 槽位
    登记,board_index 转排内 1 基)**只在落位时机生效**——上场
    (_place_missing)与换排(_fix_misrow)的目标槽优先占指定槽,
    被占/超容回退 D-4 自适应序;**不触发已就位件(名+排+星全对)
    的槽位重排**(软约束,避免无谓扰动)。

    动作序 = 换星直卖(同名异星对两步之一,§3.3)→ 缺位者上场(bench
    → 场上,D-4 落位槽选择)→ 错位者排修正(场上直拖一步)→ 多余者
    下场(场上 → bench 空槽)。返回 [] = diff 空(显式零动作)。
    """
    front, back = _rows_of(gs)
    bench: list = _bench_slots_of(gs)

    # 轻量模拟态:((名, 星) | None) 三列表 + bench 槽;动作按
    # CwActionMoveUnitParam 坐标系产出并在模拟态上推进(推演矩阵
    # 与上报侧同核——锁校验/唯一性归段 0 与上报侧防线承载)。
    f_state: list[list] = [[_cell(u) for u in front]]
    b_state: list[list] = [[_cell(u) for u in back]]
    bench_state: list[list] = [[_cell_b(s) for s in bench]]

    def _snap():
        return (list(f_state[0]), list(b_state[0]), list(bench_state[0]))

    def _restore(snap) -> None:
        f_state[0], b_state[0], bench_state[0] = \
            [list(snap[0])], [list(snap[1])], [list(snap[2])]

    out: list = []
    for _step in range(_DIFF_ACTION_CAP):
        acted = False
        # —— 1. 换星直卖(同名异星对两步之一:场上低星直卖,低星不
        #    进 bench——名字 ∈ target 名集 → 档 1 备战位同名牌永不
        #    先卖 → bench 席位死锁;D3-3)——
        for row_list, domain, _base in ((f_state[0], 'front', 1),
                                       (b_state[0], 'back', 1)):
            for i, cell in enumerate(row_list):
                if cell is None or cell[0] not in target:
                    continue
                t_row, t_star, _t_slot = target[cell[0]]
                if cell[1] >= t_star:
                    continue
                # bench 有该名高星副本 → 直卖场上低星(两步之一)。
                if not any(bc is not None and bc[0] == cell[0]
                           and bc[1] == t_star for bc in bench_state[0]):
                    continue
                idx = (i if domain == 'front'
                       else len(f_state[0]) + i)
                out.append(CwActionSellDeployedParam(
                    deployed_idx=idx, reason='deploy_star_swap'))
                row_list[i] = None
                acted = True
                break
            if acted:
                break
        if acted:
            continue
        # —— 2. 缺位者上场(bench → 场上;D-4 落位槽选择)——
        did = _place_missing(target, f_state[0], b_state[0], bench_state[0],
                             fresh, out)
        if did:
            continue
        # —— 3. 错位者排修正(场上直拖一步;目标排槽 = D-4 规则)——
        did = _fix_misrow(target, f_state[0], b_state[0], fresh, out)
        if did:
            continue
        # —— 4. 多余者下场(场上 → bench 空槽)——
        did = _disembark_extra(target, f_state[0], b_state[0], bench_state[0],
                               fresh, out)
        if did:
            continue
        break
    return out


def deploy_diff_target_actions(session, gs: GameState,
                               target: dict[str, tuple[str, int, int | None]],
                               ) -> list:
    """目标板 → 差分动作序的 session 感知入口(fresh 拦截账本自动装配;
    第 6 步常规部署 / 计划游标驱板 / 出战链部署原子序三消费面共用,
    禁各面自写 fresh 装配)。

    定型收敛(target 空 = fail-closed 容量矛盾 / diff 空 = 已就位)→
    返回 [](消费面零动作形态)。"""
    if not target:
        return []
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        fresh_buys_of,
    )
    try:
        fresh = frozenset(fresh_buys_of(session))
    except Exception:   # noqa: BLE001  新鲜度账本缺读 = 无 fresh 面
        fresh = frozenset()
    return deploy_diff_actions(gs, target, fresh=fresh)


def _cell(u) -> tuple[str, int] | None:
    """场上 Unit → (名, 星);空槽/未知件(char_id 空)→ 标记保留
    (未知件占格不可挤,D3-13;用 (None, 0) 哨兵区分空槽)。"""
    if u is None:
        return None
    cid = str(u.char_id or '')
    if not cid:
        return ('', int(u.star or 1))   # 未知件:名空占格,禁挤
    return (cid, int(u.star or 1))


def _cell_b(s):
    """bench 槽 → (名, 星) | None(空槽);占位件 → None(不可交互)。"""
    if s is None:
        return None
    if getattr(s, 'kind', 'unit') != 'unit' or s.unit is None:
        return None
    cid = str(s.unit.char_id or '')
    return (cid, int(s.unit.star or 1)) if cid else None


def _rows_of(gs) -> tuple[list, list]:
    """现板物理表(带空槽;deployed 视图子表直读——紧缩行序
    ``deployed_rows_of`` 无空槽位,落位槽选择坐标系错位不可用)。"""
    view = gs.deployed.value
    if view is None:
        return [], []
    return list(view.front_slots or []), list(view.back_slots or [])


def _bench_slots_of(gs) -> list:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_view_slots_of,
    )
    return list(bench_view_slots_of(gs) or [])


def _target_slot_for(domain: str, row_list: list, target,
                     prefer: int | None = None) -> int | None:
    """D-4 落位槽选择:同排内取「多余者(名 ∉ target)> 错位者(在
    target 排错)」的槽,禁占已就位者(名+排皆对)与未知件槽(禁挤);
    空槽最优先。返回排内 1 基槽号;满员(无可占槽)→ None。

    ``prefer``(char_positions 槽位级登记经 target 第三元传入):指定槽
    状态可占(空/多余者/错位者——同 D-4 可占性分类)→ 优先返回;
    不可占(已就位者/未知件占)或超排容量 → 回退自适应序(软约束)。"""
    empty = None
    extra = None
    misrow = None
    prefer_ok = False
    for i, cell in enumerate(row_list):
        slot_no = i + 1
        if cell is None:
            if empty is None:
                empty = slot_no
            if slot_no == prefer:
                prefer_ok = True
            continue
        if cell[0] == '':
            continue   # 未知件:禁挤
        if cell[0] not in target:
            if extra is None:
                extra = slot_no
            if slot_no == prefer:
                prefer_ok = True
            continue
        if target[cell[0]][0] != domain:
            if misrow is None:
                misrow = slot_no
            if slot_no == prefer:
                prefer_ok = True
            continue
        # 已就位者(名+排皆对):禁占(prefer 命中亦不让)
    if prefer is not None and prefer_ok:
        return prefer
    for pick in (empty, extra, misrow):
        if pick is not None:
            return pick
    return None


def _fresh_ok(cell, fresh: frozenset[str]) -> bool:
    """fresh 拦截(D2-17):涉及 fresh 件的「该件被移动」步跳过挂起。"""
    return cell is not None and cell[0] in fresh


def _place_missing(target, front: list, back: list, bench: list,
                   fresh: frozenset[str], out: list) -> bool:
    """缺位者上场:target 名不在场 ∧ bench 有 → 上场到目标排(D-4)。
    bench 源槽 = 该名副本槽;目标槽被占 = 交换(被占者回 bench 源槽,
    bench 占用不变)。"""
    on_board = {c[0] for c in (*front, *back) if c is not None and c[0]}
    for name, (row, _star, t_slot) in sorted(target.items()):
        if name in on_board:
            continue
        src = next((i for i, bc in enumerate(bench)
                    if bc is not None and bc[0] == name), None)
        if src is None:
            continue   # 缺位者不在 bench(被合并/被卖)→ 无动作帧
        row_list = front if row == 'front' else back
        slot = _target_slot_for(row, row_list, target, prefer=t_slot)
        if slot is None:
            continue   # 容量矛盾/禁挤形态 → 无动作帧(卡死计数域)
        occ = row_list[slot - 1]
        # fresh 拦截:上场者自身 fresh 不拦(买入即上是合法);被
        # 交换顶替者 fresh → 跳过该步挂起。
        if occ is not None and _fresh_ok(occ, fresh):
            continue
        out.append(CwActionMoveUnitParam(
            src_domain='bench', src_slot=src,
            dst_domain=row, dst_slot=slot, reason='deploy_diff_place'))
        moved = bench[src]
        bench[src] = occ if occ is not None else None
        row_list[slot - 1] = moved
        return True
    return False


def _fix_misrow(target, front: list, back: list,
                fresh: frozenset[str], out: list) -> bool:
    """错位者排修正:场上直拖一步(现排 → 目标排;目标槽 = D-4)。"""
    for row_list, src_domain in ((front, 'front'), (back, 'back')):
        for i, cell in enumerate(row_list):
            if cell is None or cell[0] == '' or cell[0] not in target:
                continue
            t_row, _t_star, t_slot = target[cell[0]]
            if t_row == src_domain:
                continue
            if _fresh_ok(cell, fresh):
                continue   # fresh 件换排跳过挂起
            dst_list = front if t_row == 'front' else back
            slot = _target_slot_for(t_row, dst_list, target, prefer=t_slot)
            if slot is None:
                continue
            occ = dst_list[slot - 1]
            if occ is not None and _fresh_ok(occ, fresh):
                continue
            out.append(CwActionMoveUnitParam(
                src_domain=src_domain, src_slot=i + 1,
                dst_domain=t_row, dst_slot=slot,
                reason='deploy_diff_misrow'))
            row_list[i] = occ
            dst_list[slot - 1] = cell
            return True
    return False


def _disembark_extra(target, front: list, back: list, bench: list,
                     fresh: frozenset[str], out: list) -> bool:
    """多余者下场(场上名 ∉ target → bench 空槽);无空槽 = 依赖交换
    顶替路径(_place_missing 的交换),此处跳过(无动作,留卖出场景
    在 bench 按统一让位序处置)。"""
    free = next((i for i, bc in enumerate(bench) if bc is None), None)
    if free is None:
        return False
    for row_list, src_domain in ((front, 'front'), (back, 'back')):
        for i, cell in enumerate(row_list):
            if cell is None or cell[0] == '':
                continue
            if cell[0] in target:
                continue
            if _fresh_ok(cell, fresh):
                continue
            out.append(CwActionMoveUnitParam(
                src_domain=src_domain, src_slot=i + 1,
                dst_domain='bench', dst_slot=free,
                reason='deploy_diff_disembark'))
            bench[free] = cell
            row_list[i] = None
            return True
    return False


def diff_settled(gs: GameState,
                 target: dict[str, tuple[str, int, int | None]]) -> bool:
    """就位判定(名+排+星全对):diff 空 = 已收敛。计划执行期的卡死
    检测数据源(§3.5:观察帧对账后的已就位集)。"""
    return settled_count(gs, target) == len(target) and not _extra_on_board(
        gs, target)


def settled_count(gs: GameState,
                  target: dict[str, tuple[str, int, int | None]]) -> int:
    """已就位名字数(名+排+星全对者;计划游标 progress_mark 数据源,
    §3.5 计数域 = 观察帧对账后的已就位集)。"""
    front, back = _rows_of(gs)
    n = 0
    for u, domain in ((*[(u, 'front') for u in front],
                       *[(u, 'back') for u in back])):
        if u is None:
            continue
        cid = str(u.char_id or '')
        t = target.get(cid) if cid else None
        if t is not None and t[0] == domain and t[1] == int(u.star or 1):
            n += 1
    return n


def _extra_on_board(gs: GameState,
                    target: dict[str, tuple[str, int, int | None]]) -> bool:
    """多余者(场上名 ∉ target 的已知身份件)在场判定。"""
    front, back = _rows_of(gs)
    for u in (*front, *back):
        if u is None:
            continue
        cid = str(u.char_id or '')
        if cid and cid not in target:
            return True
    return False
