"""货币战争 op 执行的逻辑效果推进(两态制,ADR-0651)。

职能(ADR-0651 字段来源两态制):op 执行后按游戏规则推算的效果**直接写
session 字段**(gold delta/owned 增减——策略器立即可读);tracked 族本体
推进单一写者 = 执行器(prep_actions ``_sync_tracking_after_sell`` 等同步位),
本函数不碰 tracked。实读帧照常覆盖(观察赢):推算与实读失配 = 推算代码
bug,修推算代码——运行时不挂账、不对账兜底。

历史形态已废除(W971 EXPECTED_STATE 期望态条目表):ExpectedEntry 登记/
last-wins/组清账/覆盖点 diff 对账(expected_reconcile.jsonl 留证)整套
随 ADR-0651 拆除——条目表簿记镜像 = 运行时挂账对账,与「逻辑态错误 =
代码 bug」错误哲学相抵;原「覆盖点确认/清账」的核对职能由观察覆盖
(BoardState.observe,观察赢)自然承接。

tracked 族 reconcile 防抖语义(star 回退防抖/双空读守卫/合成特效帧态门/
银狼升费豁免)= **observation 写入路径防抖**,重归属保留在
``kernel/cw_reconcile.py``(裁决器本体原地,归属语义见 ADR-0651)。

独立存续的旁支通道(非本模块辖,原 expected_state 仅挂载点):
- BuyExpect 载体(exec_state.pending_buy_expect;写入 = cw_prep_expect
  .compute_buy_expect@买组收尾,消费 = CwScreenPrep heavy 定型帧对账);
- XpLedger 经验账本(exec_state.xp_expect_ledger;锚点+轮界重锚,外生
  经验流吸收不判罚;推进 = CwScreenPrep._xp_apply_levelup)。

分包边界:本模块在 kernel(决策核与执行面共同消费的纯函数)。
"""
from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    merge_simulate,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PickBoxCard,
    PrepAction,
    SellBench,
    SellDeployed,
)
from sr_od.application.currency_war.kernel.cw_state import (
    DEPLOYED_FRONT_CAPACITY,
    BenchChar,
    iter_occupied,
    sell_refund,
)


def _char_fee(name: str) -> int | None:
    """角色招募费(注册表单一源);未知 → None(回金不可算 → 不推字段,
    观察帧覆盖兜底)。"""
    try:
        from sr_od.application.currency_war.data.cw_chars import CHARACTERS
        ch = CHARACTERS.get(name)
        return int(getattr(ch, 'cost', 0) or 0) or None
    except Exception:  # noqa: BLE001  注册表异常按未知处理
        return None


def _session_tracked(session) -> tuple[list[BenchChar], list[BenchChar | None]]:
    m = getattr(exec_state_of(session), 'tracked_bench_chars', None) or []
    d = getattr(exec_state_of(session), 'tracked_deployed', None) or []
    return list(m), list(d)


def _advance_gold(session, delta: int) -> None:
    """last_state.gold 逻辑推进(可为负;None 视 0 基线——金账由商店波顶/
    结算屏可信读覆盖修正,观察赢)。"""
    st = getattr(session, 'last_state', None)
    if st is None:
        return
    base = getattr(st, 'gold', 0) or 0
    st.gold = base + delta


def _owned_add(session, item: str) -> None:
    """last_owned_equips 逻辑推进:+1 件(选卡/确认到账类)。"""
    owned = list(getattr(session, 'last_owned_equips', None) or [])
    owned.append(item)
    session.last_owned_equips = owned


def apply_op_effect(session, action: PrepAction | dict, *,
                    produced_by: str = 'PrepActionExecutor',
                    detail: str = '') -> list[dict]:
    """原子 op 的逻辑效果推进(两态制标准语义,ADR-0651;两执行面同源入口)。

    按游戏规则把 op 的可推算效果**直接写 session 字段**(gold delta/
    owned 增减),返回推进清单 [{path, value, kind}](组合动作子动作
    效果上抛形态,只含本函数实际写过的字段)。回金不可算(角色费未知/
    无 tracked 身份)→ 不推字段、不挂账,观察帧覆盖兜底(ADR-0651:
    推算不了不是挂账理由)。

    显式不建模盲区(EXPECTED_STATE §6 原申报语义存续):``_handle_bench_full``
    席满急救(买经验×10 + 卖前几槽)不经执行器 → 不在推进面,该形态由
    观察覆盖兜底(声明而非遗漏)。
    """
    effects: list[dict] = []
    if session is None:
        return effects

    def _eff(path: str, value: Any, kind: str) -> None:
        effects.append({'path': path, 'value': value, 'kind': kind})

    if isinstance(action, SellBench):
        bench, _dep = _session_tracked(session)
        bc = next((b for b in iter_occupied(bench) if b.slot == action.slot), None)
        fee = _char_fee(bc.char_id) if bc is not None else None
        if bc is not None and fee is not None:
            refund = sell_refund(bc.star, fee)
            _advance_gold(session, refund)
            _eff('gold', f'+{refund}(sell_refund {bc.star}星×{fee}费)', 'gold')
    elif isinstance(action, SellDeployed):
        _bench, dep = _session_tracked(session)
        idx = (action.slot - 1 if action.row == 'front'
               else DEPLOYED_FRONT_CAPACITY + action.slot - 1)
        bc = dep[idx] if 0 <= idx < len(dep) else None
        fee = _char_fee(bc.char_id) if bc is not None else None
        if bc is not None and fee is not None:
            refund = sell_refund(bc.star, fee)
            _advance_gold(session, refund)
            _eff('gold', f'+{refund}(sell_refund {bc.star}星×{fee}费)', 'gold')
            for eq in (getattr(bc, 'equips', None) or []):
                _owned_add(session, eq)
                _eff(f'owned[{eq}]', '+1(卖场上装备全额返还)', 'owned')
    elif isinstance(action, PickBoxCard):
        chosen = ''
        for token in (detail or '').replace('选卡', ' ').split():
            chosen = token.strip()
            break
        if chosen:
            _owned_add(session, chosen)
            _eff(f'owned[{chosen}]', '+1(武装箱选卡)', 'owned')
    elif isinstance(action, dict):
        # 确认类到账(dict 形态;{'op','item'}):owned 本体推进。
        # ConfirmStrategy 不在此推(active_strategies 本体追加 = handler
        # 确认成功后既有写点,cw_screen_invest_strategy)。
        op = action.get('op', '')
        item = action.get('item', '')
        if op in ('ConfirmSupply', 'ConfirmBox', 'ConfirmTome') and item:
            _owned_add(session, item)
            _eff(f'owned[{item}]', f'+1({op})', 'owned')
        elif op == 'BuyCard':
            # dict 形 BuyCard(模拟/离线入口):合成引擎算购买数,金账
            # 逻辑推进;tracked 本体推进 = 执行器/调用方辖。
            _apply_buy_card(session, action, _eff)
    else:
        # 显式不推进理由(原 §3 铁律枚举,两态制下语义存续):
        # - OpenBox/OpenTome:箱/典籍不消失(仅画面态,消耗在选卡确认);
        # - OpenShop(含 read_only)/EnsureShop*:画面态周转,零局状态变更;
        # - StartBattle:进战斗,hp/gold/streak 由结算屏观察覆盖接管;
        # - RunDeploy/RunEquip:组合动作,tracked 本体推进 = 执行器
        #   (_sync_tracking_after_sell/_track_move_deployed 单一写者);
        # - LevelUp:经验账本推进 = CwScreenPrep._xp_apply_levelup
        #   (XpLedger 通道);金账点击数不可推算 → 观察覆盖兜底;
        # - DeployMove:tracked 位移 = 执行器 _track_move_deployed;
        # - ClickSpheres:pending_reward 无 session 字段载体,零推进;
        # - RunBuyPhase:BuyExpect 载体走 exec_state.pending_buy_expect
        #   独立通道(shop.py 买组收尾写,heavy 定型帧消费)。
        pass
    return effects


def _apply_buy_card(session, action: dict, _eff) -> None:
    """dict 形 BuyCard 的金账推进(merge_simulate 单一引擎算购买数)。"""
    name = action.get('name', '')
    star = int(action.get('star', 1) or 1)
    k = int(action.get('k', 1) or 1)
    cost = int(action.get('cost', 0) or 0)
    bench, dep = _session_tracked(session)
    res = merge_simulate(bench, dep, name, star, k=k,
                         in_shop_count=action.get('in_shop_count'))
    if cost:
        _advance_gold(session, -cost * max(1, res.buy_k or 1))
        _eff('gold', f"-{cost * max(1, res.buy_k or 1)}(买牌×{res.buy_k})",
             'gold')
