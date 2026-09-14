"""买牌动作 op(BuyCardOp)——动作文件一 op 一文件拆分自
cw_shop_actions.py(该文件转聚合注册,本文件只放本动作)。
"""
from __future__ import annotations

import contextlib
import time

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
    bench_occupied,
    exec_state_of,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import merge_buy_k
from sr_od.application.currency_war.kernel.cw_obs_core import (
    A_SHOP_CARD_PREFIX,
    SHOP_SCREEN_NAME,
    _area_rect,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    BuyCard,
    mutate_bench_deployed,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
)


class BuyCardOp(ActionOp):
    """买一张 = 一个动作 op(ADR-0517 决策 3;满栏例外下一击多张仍一个
    op,张数由游戏规则定、逻辑态直写按 merge_buy_k 计——方案 A 补裁)。"""

    def execute(self, env: ShopExecEnv) -> bool:
        from one_dragon.base.geometry.point import Point as _Pt
        action: BuyCard = self.action
        from sr_od.application.currency_war.kernel.cw_game_state import (
            bench_slots_of,
        )
        op, match, ledger, state = env.op, env.match, env.ledger, env.state
        # 点击定位 = 牌自带物理槽号 slot(读链写入)→ screen_info
        # 「商店牌-N」现取(W6 波 4 双 ShopCard 归一:容器牌无 x 坐标,
        # 坐标单一真相源 = screen_info,设计件 §2.5-5)。身份匹配优先
        # 同一性(action 由决策核自 payload 产出),退化按 (name, star)
        # ——匹配下标仅作槽号缺失时的兜底锚,见下方点击解析。
        # 槽号主源 = payload 定长槽阵列位置(三态模型:数组下标+1 =
        # 物理槽;身份同一性优先,退化 (name, star));card.slot 兼容
        # 字段降为最后兜底(退役面审计:T-190 批2)。
        _slot_no_matched = None
        _payload = state.shop.value
        _slots = (_payload.cards if _payload is not None else [])
        for _i, _s in enumerate(_slots):
            if _s.kind == 'content' and _s.card is not None \
                    and _s.card is action.card:
                _slot_no_matched = _i + 1
                break
        if _slot_no_matched is None:
            for _i, _s in enumerate(_slots):
                if _s.kind == 'content' and _s.card is not None \
                        and (_s.card.name or '') == (action.card.name or '') \
                        and int(_s.card.star or 1) == int(action.card.star or 1):
                    _slot_no_matched = _i + 1
                    break
        # 点击坐标 = 牌自带实测槽位(观察期读链写入的物理槽号)→ screen_info
        # 「商店牌-N」中心。紧凑下标只在牌行满列期与物理槽位等价:游戏买入
        # 后不压缩剩余卡位(牌行打洞),紧凑列表全体下标偏离物理槽位,按下标
        # 取固定槽坐标 = 点击落空槽框(实机局实证:1 槽空、卡在 2-5 槽时恒打
        # 1 槽框,「买牌点击不注册」根因;布局双源同族 = ADR-0646 bench 布局
        # 错位的商店牌行版)。槽号缺省(0 = sim/离线构造、修复前旧档)退回
        # 紧凑下标映射(旧行为)。
        _slot_no = _slot_no_matched
        if _slot_no is None:
            # 兼容兜底:旧档/sim 构造牌的 slot 字段(退役过渡期保留)
            _slot_no = int(getattr(action.card, 'slot', 0) or 0)
        if 1 <= _slot_no <= len(env.click_pts):
            pt = env.click_pts[_slot_no - 1]
        else:
            pt = (_Pt(0, 288) if not env.click_pts else env.click_pts[0])
        # 买前裁该片矩形拷贝(`w536_merge_expect/`:「买了什么」的像素级
        # 证据,随期望态带到对账点;一帧原则,必须 copy 防帧缓存覆写)。
        # 纯留证零判效(T-192):crop 只进 buy_purchases 遥测;落地事实
        # 归下一帧入口观察 reconcile,不据执行侧像素判定改道。
        _card_crop = None
        with contextlib.suppress(Exception):
            _frame = op.screenshot()
            for _i in range(1, 6):
                _r = _area_rect(op.ctx,
                                f'{A_SHOP_CARD_PREFIX}{_i}',
                                SHOP_SCREEN_NAME)
                if _r is not None and _r.x1 <= pt.x <= _r.x2:
                    _card_crop = _frame[_r.y1:_r.y2, _r.x1:_r.x2].copy()
                    break
        op.ctx.controller.click(pt)
        log.info(f'[cw-shop] Buy click slot={_slot_no} @({pt.x},{pt.y}) '
                 f'{action.card.faction}/{action.card.name}/'
                 f'{action.card.cost}')
        time.sleep(0.4)
        ledger.total_buy += 1
        ledger.spend_executed += action.card.cost
        if action.card.name:
            ledger.bought_names.append(action.card.name)
            # 撤销操作证据留存(纯观测,零行为变更):体系成员买入不重置
            # 干旱计数(重置单一源 = 商店可见性 _update_pair_drought),
            # 解锁流程审计面落台账。复用 defect_ledger,异常不阻断买入。
            with contextlib.suppress(Exception):
                _ist_e = getattr(strategy_state_of(match.session), 'v3_intention', None)
                _pd = getattr(_ist_e, 'pair_drought', None)
                if isinstance(_pd, dict):
                    from sr_od.application.currency_war.kernel.cw_intention import (
                        members_in_shop,
                    )
                    from sr_od.application.currency_war.telemetry.undo_evidence import (
                        record_drought_buy_no_reset,
                    )
                    for _sys, _d in _pd.items():
                        if _d and _sys and members_in_shop(
                                _sys, {action.card.name}):
                            record_drought_buy_no_reset(
                                member=action.card.name,
                                system=_sys, drought=_d)
        # tracking 同步:满栏合成买与逻辑态直写同分支单一源(T-182:shop 视图
        # 进 tracked mutate,满栏完成合成的买入在 tracked 侧同样合成腾槽
        # ——旧丢件行为使 tracked 漏记合成,同 visit 下一动作守卫对拍
        # 误炸;2026-09-09 05:52 运行局双响事故)。
        _payload_cards = (shop_payload_content_cards(state.shop.value)
                          if state.shop.value is not None else [])
        mutate_bench_deployed(exec_state_of(match.session).tracked_bench_chars,
                              exec_state_of(match.session).tracked_deployed,
                              action, shop=_payload_cards)
        if action.card.name:
            _cnt = 1
            if bench_occupied(bench_slots_of(state)) >= BENCH_CAPACITY:
                # 满栏例外(merge_mechanics §2.5 方案 A):一击多张,张数
                # 单一源 = merge_buy_k(禁执行侧重算);金账无折扣 = 总价
                # k×单价,执行账补差 (k−1)×单价。
                _cnt = max(1, merge_buy_k(
                    action.card.name, action.card.star or 1,
                    bench_slots_of(state),
                    exec_state_of(match.session).tracked_deployed,
                    _payload_cards))
                ledger.spend_executed += (action.card.cost or 0) * (_cnt - 1)
            from sr_od.application.currency_war.kernel.cw_prep_expect import (
                BuyPurchase,
            )
            ledger.buy_purchases.append(BuyPurchase(
                name=action.card.name, star=action.card.star,
                count=_cnt, unit_cost=action.card.cost or 0,
                crop=_card_crop))
        else:
            ledger.buy_unidentified = True
        return True
