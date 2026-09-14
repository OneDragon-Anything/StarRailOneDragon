"""刷新商店动作 op(RefreshShopOp)与免费刷新 proc 留证——动作文件
一 op 一文件拆分自 cw_shop_actions.py(该文件转聚合注册,留证函数
只服务本 op 故随迁)。
"""
from __future__ import annotations

import contextlib
import time

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_economy import REFRESH_COST_BASE
from sr_od.application.currency_war.kernel.cw_game_state import GameState
from sr_od.application.currency_war.obs import cw_shop_refresh_obs
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ShopActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
    ShopVisitLedger,
    _container_cards,
    _plane_of,
    _round_of,
)
from sr_od.application.currency_war.telemetry import defects


class RefreshShopOp(ShopActionOp):
    """刷新 = 终结 op(决策 7:唯一引入新事实的动作,期望态必须在新事实
    处重建——终结后外循环入口重观察)。T-192 判效半拆除:牌名集三值
    对比仅作安灯豁免判定输入 + 遥测字段(候选 a 留证遥测半合法保留);
    免费刷新证据/刷新期望对账 = 执行实现层遥测(与决策读屏解耦);
    「刷新是否生效」的判效权归观察侧 reconcile。"""

    terminal = True

    def execute(self, env: ShopExecEnv) -> bool:
        from one_dragon.utils import cv2_utils as _cvu

        # 读函数经 cw_op_buy_cards 模块属性路由(该模块的读点替身缝,
        # 测试 monkeypatch 面;自本模块直接 import 会绕开替身)。
        from sr_od.application.currency_war.operations.cw_screen import (
            cw_screen_buy_cards as _buy_cards_mod,
        )
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_prep import (
            build_refresh_expect,
            refresh_reconcile_mismatches,
        )
        op, _match, ledger, state = (env.op, env.match, env.ledger,
                                    env.state)
        ledger.refresh_attempted = True
        # 刷前现读两口径(执行边界压缩·连击共享往返):「仅刷新段」
        # (段内零先行动作)复用段顶整帧读;其余段点击前一帧现读金+牌名集
        # (`w592_free_refresh_fix/`:波内买卡不从 state.shop 摘已买牌,
        # plan 读 vs 点击后实读集合必不等,真落空会被洗成免费生效)。
        _pre_shop_names: list[str] | None = None
        _refresh_expect = None
        _reconcile = None
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                gold_of,
            )
            if ledger.refresh_first_action:
                _pre_gold = gold_of(state) if gold_of(state) > 0 else None
                _pre_shop_names = [c.name for c in _container_cards(state)
                                   if c.name]
            else:
                _pre_shot = op.screenshot()
                _pre_gold = _buy_cards_mod.read_gold_opt(op.ctx, _pre_shot)
                _pre_shop_names = [
                    s.card.name for s in (
                        _buy_cards_mod.read_shop_cards(op.ctx, _pre_shot)
                        or [])
                    if s.kind == 'content' and s.card and s.card.name]
            _refresh_expect = build_refresh_expect(
                _pre_gold, REFRESH_COST_BASE,
                [(c.name, c.star) for c in _container_cards(state)],
                _plane_of(state), _round_of(state))
            _reconcile = refresh_reconcile_mismatches
        except Exception:   # noqa: BLE001  best-effort 不阻塞买牌
            _refresh_expect = None
            _reconcile = None
        # 刷前刷新钮真值读(T-13 读链接入):按钮三态 + 免费态剩余次数。
        # 经模块属性路由 = 测试替身缝(同 _buy_cards_mod 约定)。best-effort:
        # 识别层故障不阻塞执行链,ledger 字段保持 None = 免费闸回退逻辑账。
        _btn = None
        try:
            _btn = cw_shop_refresh_obs.read_shop_refresh_button(
                op.ctx, op.screenshot(), gold=_pre_gold)
        except Exception:   # noqa: BLE001  best-effort 不阻塞执行
            _btn = None
        if _btn is not None:
            ledger.refresh_free_truth = _btn.free
            ledger.refresh_free_remaining_truth = _btn.free_remaining
            log.info('[cw-shop] refresh button truth: free=%s remaining=%s '
                     'price=%s affordable=%s',
                     _btn.free, _btn.free_remaining, _btn.price, _btn.affordable)
        op.ctx.controller.click(env.refresh_btn)
        log.info(f'[cw-shop] Refresh click @({env.refresh_btn.x},'
                 f'{env.refresh_btn.y})')
        # r325(P1⑤):刷新后两帧一致门(牌行区指纹;刷新动画帧上的
        # SIFT miss 是 r97/383 样本实证根因);超时 2.5s 回退旧 sleep 语义。
        # 牌行 rect 单一源:改调 _shop_row_rects()(建档 area 派生+字面量
        # 兜底同门),删除本文件第二副本字面量(坐标单一源清点项)。
        _rects = _buy_cards_mod._shop_row_rects(op)   # 商店牌行
        _base = None
        _stable = False
        for _ in range(8):   # ≤2s@0.25s 步长
            time.sleep(0.25)
            _fp = None
            try:   # r327:截图裸调炸分支 → suppress 降级继续等
                _shot = op.screenshot()
                _fp = _cvu.fingerprint_in_rects(_shot, _rects)
            except Exception:   # noqa: BLE001  离线契约
                _fp = None
            if _fp is not None and _base is not None \
                    and _cvu.fingerprint_same(_fp, _base):
                _stable = True
                break
            if _fp is not None:
                _base = _fp
        if not _stable:
            time.sleep(0.5)   # 超时回退(≈旧 1.0s 总量)
        # 当次刷价进花销账 = 基价常量(ADR-0456:实付恒基价)
        _refresh_fee = state.shop_refresh_cost or REFRESH_COST_BASE
        ledger.spend_executed += _refresh_fee
        ledger.total_refresh += 1
        ledger.did_refresh = True
        try:
            _new_shop = _buy_cards_mod.read_shop_cards(op.ctx, op.screenshot())
            # (refresh 牌面快照行已随 shop_snapshots 流写入端退役删除
            #  ——删除波 1;牌面现役归宿 = journal 快照行自带 shop 域。)
            # 留证遥测半(T-192 判效半拆除后的保留面,候选 a):刷前/刷后
            # 牌名集三值对比只作安灯 free_refresh_proc 豁免判定输入
            # (classify_spend_unit 判定序③)+ 遥测字段
            # (schema.refresh_board_changed),不再产「刷新未生效嫌疑」
            # 判效结论——判效权归观察侧 reconcile。任一侧空(整帧失读/
            # 买光全空位)= None 不可判,不猜。
            _post_shop_names = [s.card.name for s in (_new_shop or [])
                                if s.kind == 'content' and s.card
                                and s.card.name]
            ledger.refresh_board_changed = (
                None if not _pre_shop_names or not _post_shop_names
                else set(_pre_shop_names) != set(_post_shop_names))
            # 刷新期望 vs 实读对账(零决策记账):金腿 + 牌腿。
            if _refresh_expect is not None and _reconcile is not None:
                _gold_after = _buy_cards_mod.read_gold_opt(
                    op.ctx, op.screenshot())
                # 免费刷新事后正证据通道(ADR-0456,永久保留——判定语义
                # 的一部分):刷新已点击 ∧ 牌面已变 ∧ 点后金=点前金 →
                # 免费 proc 真实发生,截图+flag 留证(不停机)。
                if (ledger.refresh_board_changed is True
                        and _pre_gold is not None
                        and _gold_after is not None
                        and _gold_after == _pre_gold):
                    with contextlib.suppress(Exception):
                        _record_free_refresh_proc(
                            op, state, ledger, _pre_gold, _gold_after,
                            _pre_shop_names, _new_shop)
                _cards_named = sum(1 for c in _new_shop if c.name)
                for _m in _reconcile(_refresh_expect[0], _gold_after,
                                     _cards_named):
                    defects.record_defect(
                        'shop', 'refresh_expect_mismatch',
                        expected=(f'{_m["domain"]}/{_m["slot"]}: '
                                  f'{_m["expected"]}'),
                        observed=_m['observed'],
                        plane=_plane_of(state), round_num=_round_of(state),
                        verdict='留证-刷新期望不符(零决策)',
                        reader_source='refresh_expect_reconcile',
                        note='期望三输入波前现读,None 跳过;'
                             '判据真值表已锁')
        except Exception:   # noqa: BLE001  快照 best-effort 不阻塞买牌
            pass
        return True


def _record_free_refresh_proc(op, state: GameState, ledger: ShopVisitLedger,
                              pre_gold, gold_after, pre_names,
                              new_shop) -> None:
    """免费刷新 proc 留证(ADR-0456;自 RefreshShopOp 抽出,单一行为)。"""
    from datetime import datetime as _dt

    from one_dragon.utils.file_utils import get_project_root
    from sr_od.application.currency_war.telemetry import (
        state as _cw_tel,
    )
    _free_shot = op.save_screenshot(prefix='free_refresh_proc')
    _flag_p = get_project_root() / '.debug' / 'temp' \
        / 'cw_free_refresh_proc.flag'
    _flag_p.parent.mkdir(parents=True, exist_ok=True)
    _flag_p.write_text(
        'FREE-REFRESH-PROC: 免费刷新实机正证据(非停机,bot 照常跑)\n'
        f'run={_cw_tel.current_run_id()} '
        f'plane={_plane_of(state)} round={_round_of(state)} '
        f'wave={ledger.total_refresh} ts={_dt.now().isoformat(timespec="seconds")}\n'
        f'前后牌面: {sorted(pre_names or [])} -> '
        f'{sorted(c.name for c in new_shop)}\n'
        f'gold: 前={pre_gold} 后={gold_after}(未扣=免费)\n'
        f'截图: {_free_shot}\n'
        '处理: 汇总频率判免费来源(棱 45%/策略类/未知),'
        '确认后删本 flag;通道本身保留(对账防线)。\n',
        encoding='utf-8')
    log.warning(
        '[cw!][shop] 免费刷新 proc:牌面已变 金未扣'
        '(前=%s 后=%s)→ 留证不停 flag=cw_free_refresh_proc.flag',
        pre_gold, gold_after)
