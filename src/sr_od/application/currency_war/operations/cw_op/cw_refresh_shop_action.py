"""刷新商店动作 op(RefreshShopOp)——动作文件(一 op 一文件,拆分自
cw_shop_actions.py,该文件转聚合注册)。

免费刷新判定 = 对账类(比对收口纪律:判定随对账走,不随动作走):
动作 op 内不做「金未扣 ∧ 牌面变」比对,本 op 只把刷前金/牌名与
「待对账」标记落 ledger(坐标系与写入端声明见 ShopVisitLedger 字段
注);比对与存证(截图+flag+log)由下一段入口观察的对账点承接,
宿主 = cw_screen_buy_cards.run_buy_waves 段顶入口观察。
"""
from __future__ import annotations

import time

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_economy import REFRESH_COST_BASE
from sr_od.application.currency_war.obs import cw_shop_refresh_obs
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
    _container_cards,
    _plane_of,
    _round_of,
)
from sr_od.application.currency_war.telemetry import defects

# 刷新点击后固定等待(重掷动画收敛):两帧指纹等稳门废弃(T-219)后的
# 等待语义——固定时长即收,与买牌点击后固定 sleep 同风格的时长常量;
# 牌面/金真值判读不在动作内自证,交下一段入口观察(对账点)。
REFRESH_CLICK_SETTLE_WAIT_S: float = 1.0


class RefreshShopOp(ActionOp):
    """刷新 = 终结 op(决策 7:唯一引入新事实的动作,期望态必须在新事实
    处重建——终结后外循环入口重观察)。T-192 判效半拆除:牌名集三值
    对比仅作安灯豁免判定输入 + 遥测字段(候选 a 留证遥测半合法保留)。
    免费刷新判定 = 对账类(T-219):execute 内不比对,只落对账三件
    (刷前金/刷前牌名/待对账标记)进 ledger,由下一段入口观察对账;
    刷新期望对账(refresh_expect_mismatch)= 执行实现层遥测(与决策
    读屏解耦),「刷新是否生效」的判效权归观察侧 reconcile。"""

    terminal = True

    def execute(self, env: ShopExecEnv) -> bool:
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
        _pre_gold: int | None = None
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
        # 免费刷新对账三件落账(T-219:判定收口到观察侧对账点,本 op
        # 零比对;字段坐标系与写入端声明见 ShopVisitLedger)。失读字段
        # 照实落 None/空,对账点按腿判空放行(宁缺勿造)。
        ledger.refresh_pre_gold = _pre_gold
        ledger.refresh_pre_names = list(_pre_shop_names or [])
        ledger.refresh_pending_reconcile = True
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
        time.sleep(REFRESH_CLICK_SETTLE_WAIT_S)
        # 当次刷价进花销账(ADR-0456:实付恒基价;容器刷价在场用现值,
        # 未观察/0 = 回基价)。读数必须走 .value 读口——Field 直接进算术
        # = TypeError(实机 04:37 刷新首击即崩实证,店 env 容器化后此读
        # 点漏迁移)。
        _refresh_fee = state.shop_refresh_cost.value or REFRESH_COST_BASE
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
