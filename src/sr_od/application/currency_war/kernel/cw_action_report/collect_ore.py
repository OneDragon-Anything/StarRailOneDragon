"""货币战争动作上报:点晶矿(report_action_collect_ore_param)。

**逻辑随机态首个落地动作**(logic-rand-sampling 迭代;设计正本 =
``docs/develop/sr_od/application/currency_war/changes/
2026-09-20-logic-rand-sampling/design.md`` §2.4):

- **逐点顺序推演**:载荷为批式坐标列表,逐点独立守卫/独立采样/独立
  逐步写(每步一行,同组 group_id,evidence 带点序 ``#ore<k>``);
- **席满即该点无效**:该点时备战席无空位(含前点角色奖励耗席后的
  累计判)→ 晶矿留在 spheres 字段现值中(不摘除、不采样),等下轮
  重派(screen_flow_timing #16 在册裁定同源);
- **全部容器写均为随机态**(rand = :meth:`GameState.write_logic_rand`):
  spheres 终值同样依随机链而变(后续晶矿开否取决于采样奖励是否耗席),
  本动作不存在确定面写;观察覆盖差异 = 随机效果落地预期内
  (``logic_rand_outcome`` 台账行),策略消费前必须重观察;
- **采样** = ``kernel/cw_ore_reward.py::roll_ore_reward``(临时建模
  口径 v0:金 1–5/简易装备池/当前概率表抽角色,假设档披露键在册);
  rng 注入——实机缺省未播种(采样是猜测),sim 传流键 rng(采样即
  世界真值,零自算)。

动作上报函数族拆分件(每动作一文件;族规约 = 包 ``cw_action_report.
__init__`` docstring)。本包 → 容器单向依赖。
"""
from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import replace as _dc_replace
from typing import Any

from sr_od.application.currency_war.kernel.cw_exec_state import (
    BenchChar,
    bench_place,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    BenchView,
    ChannelSig,
    GameState,
    LogicOutcome,
    OreSight,
    Unit,
    _validate_sig,
    bench_slots_of,
    deployed_slots_of,
    deployed_slots_to_rows,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    _merge_bench,
)
from sr_od.application.currency_war.kernel.cw_ore_reward import (
    roll_ore_reward,
)

_PRODUCER = 'CwActionCollectOreParam'


def _bench_view_keep_items(work: list[BenchChar | None],
                           orig: BenchView) -> BenchView:
    """工作槽位表 → BenchView,**占位件 kind 细分按原观察保留**。

    `bench_view_of_slots` 对占位件(典籍/书册卡/箱)恒降级 supply_box
    (is_item_slot 布尔无类型信息,该口已申报的已知边界)——本动作的
    角色奖励写会整表换新,降级会让后续 OpenTome/OpenBookcard 按 kind
    找不到槽(实锁 test_cw_collect_ore_rand 契约)。本口按原观察槽位
    还原 tome/bookcard/supply_box 细分,其余槽照 unit 形态映射。
    """
    slots = []
    for i, bc in enumerate(work):
        orig_slot = orig.slots[i] if i < len(orig.slots) else None
        if bc is None:
            slots.append(BenchSlot(kind='empty'))
        elif (bool(getattr(bc, 'is_item_slot', False))
                and orig_slot is not None
                and orig_slot.kind in ('tome', 'bookcard', 'supply_box')):
            slots.append(orig_slot)
        else:
            slots.append(BenchSlot(kind='unit', unit=Unit(
                char_id=str(getattr(bc, 'char_id', '') or ''),
                star=int(getattr(bc, 'star', 1) or 1),
                equips=list(getattr(bc, 'equips', None) or []),
                slot=i + 1)))
    while len(slots) < len(orig.slots):
        slots.append(BenchSlot(kind='empty'))
    return BenchView(slots=slots, capacity=orig.capacity)


def _slot_sig(slots: list[BenchChar | None]) -> list:
    """槽位表值签名(bench/deployed 通用;变更检测用,防共享对象
    原地变异导致「签名没变值已变」的假阴——快照在深拷贝工作列表上,
    签名比较仅判『是否需要落一行』)。"""
    return [None if b is None else
            (b.char_id, b.star, tuple(b.equips or ()))
            for b in slots]


def report_action_collect_ore_param(gs: GameState, param: Any, sig: ChannelSig,
                                    session: object = None,
                                    rng: random.Random | None = None) -> LogicOutcome:
    """点晶矿上报(逐点顺序推演 + 随机态逐步写;design §2.4 全表)。

    - **整批拒(零写)**:spheres 未观察(现行为)/载荷无交集(现行为)/
      bench 未观察('bench_unobserved'——席满守卫与角色落点均不可判)/
      level 缺读('level_unread'——角色采样需当前等级,宁缺勿造);
    - **逐点守卫**:该点时备战席无空位 → 该晶矿留在 spheres、不采样
      (裁决 3:满栏点击无效;前点奖励耗席累计判);
    - **写序**(每点):spheres 摘除 → 未抽中域标记(值不变,现值非
      None 才标)→ 奖励应用(金 +N/装备 +件/角色落位 + 3合1 连锁——
      每级合并后受影响域各落一行,board 派生随行写自动继承随机态);
    - **动作级出参**:全部开成 = applied=True;混合批 =
      'ore_partial_open_skipped';全部席满跳过 = applied=False
      'bench_full_no_open'。
    """
    _validate_sig(sig, ('logic_action',))
    roll_rng = rng if rng is not None else random.Random()

    view = gs.spheres.value
    if view is None:
        return LogicOutcome(applied=True, reason='spheres_unobserved')
    orig_bench = gs.bench.value
    if orig_bench is None:
        return LogicOutcome(applied=False, reason='bench_unobserved')
    level = gs.level.value
    if level is None:
        return LogicOutcome(applied=False, reason='level_unread')

    # 载荷 ∩ 现值,按载荷序保序去重(同坐标重复点 = 单点)
    by_xy = {(int(p[1]), int(p[2])): p for p in view.points}
    ordered: list[tuple] = []
    seen: set[tuple[int, int]] = set()
    for x, y in param.points:
        xy = (int(x), int(y))
        if xy in by_xy and xy not in seen:
            seen.add(xy)
            ordered.append(by_xy[xy])
    if not ordered:
        return LogicOutcome(applied=True, reason='no_intersection')

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w_rand(target: Any, value: Any, evidence: str) -> None:
        gs.write_logic_rand(target, value, produced_by=_PRODUCER,
                            evidence=evidence, sig=_grp_sig)

    # 工作态(深拷贝防别名:容器帧持同源对象,合并原地变异不得穿透)
    remaining = list(view.points)
    work_bench: list[BenchChar | None] = [
        deepcopy(b) if b is not None else None for b in bench_slots_of(gs)]
    work_dep: list[BenchChar | None] = [
        deepcopy(d) if d is not None else None for d in deployed_slots_of(gs)]

    opened = 0
    skipped = 0
    for k, p in enumerate(ordered, 1):
        xy = (int(p[1]), int(p[2]))
        if sum(1 for b in work_bench if b is None) <= 0:
            skipped += 1
            continue   # 席满即该点无效:晶矿留在 spheres,不摘不采

        # 步1 spheres 摘除(随机态——终值依随机链而变,design §2.4 表注)
        remaining = [q for q in remaining
                     if (int(q[1]), int(q[2])) != xy]
        _w_rand(gs.spheres, OreSight(
            count=len(remaining),
            colors=tuple(dict.fromkeys(q[0] for q in remaining)),
            points=tuple(remaining)), f'proj_collect_ore_drop#ore{k}')
        opened += 1

        reward = roll_ore_reward(roll_rng, int(level))
        written = {'spheres'}
        rolled_domain = {'gold': 'gold', 'equip': 'equips',
                         'char': 'bench'}[reward.kind]

        # 步2 未抽中域标记(值不变,现值非 None 才标——None 域跳写,
        # 随机态标记对「本就未知」的域无信息增益)
        for dom, fld in (('gold', gs.gold), ('equips', gs.equips),
                         ('bench', gs.bench), ('front_row', gs.front_row),
                         ('back_row', gs.back_row)):
            if dom == rolled_domain or dom in written:
                continue
            cur = fld.value
            if cur is None:
                continue
            _w_rand(fld, cur, f'proj_ore_mark_{dom}#ore{k}')
            written.add(dom)

        # 步3 奖励应用(抽中域写采样值)
        if reward.kind == 'gold':
            g = gs.gold.value
            if g is not None:
                _w_rand(gs.gold, int(g) + int(reward.gold),
                        f'proj_ore_reward_gold#ore{k}')
                written.add('gold')
        elif reward.kind == 'equip':
            eq = gs.equips.value
            if eq is not None:
                _w_rand(gs.equips, list(eq) + [reward.equip],
                        f'proj_ore_reward_equip#ore{k}')
                written.add('equips')
        else:
            # 角色奖励:落备战席首空槽 → 3合1 连锁(每级合并后受影响域
            # 各落一行;board 派生随行写自动继承随机态)。bench 整表写
            # 走保留占位件 kind 口(典籍/书册卡/箱不降级,见 helper 注)
            bench_place(work_bench, BenchChar(
                slot=0, char_id=reward.char_id, star=reward.char_star))
            _w_rand(gs.bench, _bench_view_keep_items(work_bench, orig_bench),
                    f'proj_ore_reward_char#ore{k}')
            written.add('bench')
            merge_no = 0
            last_bs = _slot_sig(work_bench)
            last_ds = _slot_sig(work_dep)

            def on_step(_k: int = k,
                        _written: set[str] = written) -> None:
                # 默认参数绑定本点序/本点登记集(B023:回调内聚合同步
                # 调用,绑定义为调用刻值,防循环变量晚绑隐患)
                nonlocal merge_no, last_bs, last_ds
                merge_no += 1
                ev = f'proj_ore_merge#{merge_no}#ore{_k}'
                bs = _slot_sig(work_bench)
                if bs != last_bs:
                    _w_rand(gs.bench,
                            _bench_view_keep_items(work_bench, orig_bench),
                            ev)
                    last_bs = bs
                    _written.add('bench')
                ds = _slot_sig(work_dep)
                if ds != last_ds:
                    front, back = deployed_slots_to_rows(work_dep)
                    _w_rand(gs.front_row, front, ev)
                    _w_rand(gs.back_row, back, ev)
                    last_ds = ds
                    _written.update({'front_row', 'back_row'})

            _merge_bench(work_bench, work_dep, on_step=on_step)

            # 步4 合成未触及的行域标记(真值可能因角色奖励而变)
            for dom, fld in (('front_row', gs.front_row),
                             ('back_row', gs.back_row)):
                if dom in written:
                    continue
                cur = fld.value
                if cur is None:
                    continue
                _w_rand(fld, cur, f'proj_ore_mark_{dom}#ore{k}')
                written.add(dom)

    if opened == 0:
        return LogicOutcome(applied=False, reason='bench_full_no_open')
    if skipped:
        return LogicOutcome(applied=True, reason='ore_partial_open_skipped')
    return LogicOutcome(applied=True)
