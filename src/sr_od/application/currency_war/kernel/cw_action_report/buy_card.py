"""货币战争动作上报:买牌(report_action_buy_card_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    ShopActionExecuted,
    ShopPayload,
    ShopSlot,
    _validate_sig,
    bench_slots_of,
    bench_view_of_slots,
    deployed_slots_of,
    deployed_slots_to_rows,
    detect_merge_upgrade,
    mutate_bench_deployed_local,
    shop_cards_to_legacy,
    shop_payload_content_cards,
)


def report_action_buy_card_param(gs: GameState, param: Any, sig: ChannelSig,
                                 executed: ShopActionExecuted | None = None) -> LogicOutcome:
    """买牌上报:gold −单价×k + bench 落位 + 合成连锁 + payload −k
    ((name, star) 计数)+ 升星腿整表覆盖(买前快照三件组基点,快照在
    本函数内第一时间取——原落地门/两驱动器三处抄写收编单点)。

    满栏且合成不可达 = 游戏拒买(applied=False + reason='bench_full',
    零写,ADR-0283)。k 来源:executed 给定 = 回执 k(live);None =
    理想执行自算(简单腿 1,满栏从应用机器出)。语义源 = simulate
    BuyCard 分支,直锁 test_cw_transfer_golden / 锁 M1 钉住。
    """
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_economy import (
        card_cost,
    )
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        BenchChar,
        bench_place,
    )
    from sr_od.application.currency_war.kernel.cw_merge_simulate import (
        _apply_full_bench_merge_buy,
        _merge_bench,
    )
    from sr_od.application.currency_war.kernel.cw_vocab import (
        ShopCard as _LegacyShopCard,
    )

    # 买前快照三件组(升星腿 scratch 基点;必须在简单腿写之前取——基点
    # 误取买后容器会重复落位,shop 视图缺失会漏满栏合成)。
    pre_bench = bench_slots_of(gs)
    pre_deployed = deployed_slots_of(gs)
    _payload_pre = gs.shop.value
    pre_shop = (shop_payload_content_cards(_payload_pre)
                if _payload_pre is not None else [])

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionBuyCardParam',
                       evidence=evidence, sig=_grp_sig)

    def _legacy_card(c: Any) -> _LegacyShopCard:
        """容器牌 → 平移机器入参 Legacy 牌(仅 (name, star) 语义位消费)。"""
        return _LegacyShopCard(
            x=0,
            faction=str(getattr(c, 'faction', '') or '?'),
            name=str(getattr(c, 'name', '') or ''),
            cost=int(getattr(c, 'cost', 0) or 0),
            star=int(getattr(c, 'star', 1) or 1),
            cost_source=str(getattr(c, 'cost_source', '') or 'roster'))

    card = param.card
    name = str(getattr(card, 'name', '') or '')
    star = int(getattr(card, 'star', 1) or 1)
    bench_slots = bench_slots_of(gs)
    dep_slots = deployed_slots_of(gs)
    payload = gs.shop.value
    shop_view = shop_cards_to_legacy(shop_payload_content_cards(payload))
    # k 来源:executed 给定 = 回执 k(live);None = 理想执行自算(简单腿 1,
    # 满栏从应用机器出)。
    k_exec = (max(1, int(executed.bought_count))
              if executed is not None and executed.bought_count is not None
              else None)
    scratch_b = list(bench_slots)
    scratch_d = list(dep_slots)
    # ⚠ list() 浅拷贝与读口结果共享元素对象——_merge_bench 原地改星
    # 后「scratch is pre」逐元素相等,行写判据必须用值签名快照。
    _dep_pre_sig = [(str(getattr(d, 'char_id', '') or ''),
                     int(getattr(d, 'star', 1) or 1),
                     tuple(getattr(d, 'equips', ()) or ()),
                     str(getattr(d, 'position_pref', '') or ''))
                    for d in dep_slots]
    new_bc = BenchChar(slot=0, char_id=name,
                       faction=str(getattr(card, 'faction', '') or '?'),
                       star=star)
    placed = bench_place(scratch_b, new_bc) is not None
    if placed:
        k = k_exec if k_exec is not None else 1
        _merge_bench(scratch_b, scratch_d)
    else:
        k_apply = _apply_full_bench_merge_buy(
            scratch_b, scratch_d, _legacy_card(card), shop_view)
        if k_apply is None:
            return LogicOutcome(applied=False, reason='bench_full')
        k = k_exec if k_exec is not None else max(1, int(k_apply))
    g = gs.gold.value
    if g is not None:
        _w(gs.gold, int(g) - card_cost(card) * k, 'proj_buy_gold')
    if payload is not None:
        slots = list(payload.cards)
        while len(slots) < 5:
            slots.append(ShopSlot(kind='empty'))
        _left = k
        for _i, s in enumerate(slots):
            if _left <= 0:
                break
            if s.kind == 'content' and s.card is not None \
                    and (s.card.name or '') == name \
                    and int(s.card.star or 1) == star:
                slots[_i] = ShopSlot(kind='empty')
                _left -= 1
        _w(gs.shop, ShopPayload(cards=slots,
                                refresh_probs=(dict(payload.refresh_probs) if payload.refresh_probs is not None else None)),
           'proj_buy_payload')
    _w(gs.bench, bench_view_of_slots(scratch_b), 'proj_buy_place')
    _dep_post_sig = [(str(getattr(d, 'char_id', '') or ''),
                      int(getattr(d, 'star', 1) or 1),
                      tuple(getattr(d, 'equips', ()) or ()),
                      str(getattr(d, 'position_pref', '') or ''))
                     for d in scratch_d]
    if _dep_post_sig != _dep_pre_sig:
        front, back = deployed_slots_to_rows(scratch_d)
        _w(gs.front_row, front, 'proj_deployed_front')
        _w(gs.back_row, back, 'proj_deployed_back')

    # —— 升星腿(买前快照基点;整表 write_logic 后写覆盖,与简单腿
    #    两写合计的期望态由投影直锁钉住,锁 M1)——
    from types import SimpleNamespace as _NS

    from sr_od.application.currency_war.kernel.cw_exec_state import (
        snapshot_copy,
    )
    scratch_mb = [snapshot_copy(b) if b is not None else None
                  for b in pre_bench]
    scratch_md = [snapshot_copy(d) if d is not None else None
                  for d in pre_deployed]
    mutate_bench_deployed_local(scratch_mb, scratch_md, param,
                                shop=pre_shop)
    if detect_merge_upgrade(_NS(bench=pre_bench, deployed=pre_deployed),
                            _NS(bench=scratch_mb, deployed=scratch_md)):
        gs.write_logic(gs.bench, bench_view_of_slots(scratch_mb),
                       produced_by='CwActionBuyCardParam',
                       evidence='proj_merge_upgrade',
                       sig=ChannelSig(
                           family='logic_action', actor=sig.actor,
                           mode='compute',
                           group_id=(f'act:{sig.actor}@'
                                     f'{gs.write_seq + 1}')))
    return LogicOutcome(applied=True, bought_count=k)

