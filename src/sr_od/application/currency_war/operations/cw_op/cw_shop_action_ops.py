"""商店单动作动作 op 集(ADR-0517 决策 3/10;flow 实施批)。

动作基类两方法(决策 10,用户 2026-09-06 确认):

- ``execute(env)``:机械执行(点击/拖拽;op 框架既有的重试/等待语义
  在此层),无判断;
- ``project(state)``:纯计算更新期望态(金/板凳/持有副本/等级/合成
  连锁),零读屏,可独立单测——实现 = ``cw_state.simulate`` 单一源
  (合成连锁/满栏例外 §2.5 自动多买/金账全在其内,禁第二实现)。

**知识缺口申报(ADR-0517 决策 7 边界注;merge_mechanics 通篇未载)**:
非满栏常态时合成槽位买的一击张数无 research 记载——本实现取保守假设
**一击一张**(与 simulate 的常规买入分支一致),规则模型误差由入口
对账兜底(下一画面入口观察 = 事实重建,决策 8)。实机冻结解除后补档
验证:验证未过则该买面升格为终结 op(fallback 语义,见 CompTransactionOp)。

守卫断言(决策 9):执行侧检查 = 防 bug 路栏非控制流分支,非法返回 =
策略器 bug 响亮暴露——``guard_proposal_vs_expected``(提案动作的对象在
期望态中存在且未被消费,防策略器算术 bug)+ ``guard_expected_vs_tracked``
(期望态投影链 vs 执行侧 tracked 账双账对拍,投影建模 bug 的唯一在环
检测器——ADR-0516 投影口径族史证明 project 建模错是常态)。双账断言
零读屏(tracked 账纯内存随动),不违决策 1/8「循环内不读屏」。

执行侧观测通道(ADR-0517 §执行侧观测通道去向,候选 a):卖回金实收
遥测/刷新有效性检测/免费刷新证据保留为 execute 实现层遥测,与决策读屏
解耦(三通道均观测职责,非决策输入)。
"""
from __future__ import annotations

import contextlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import (
    A_SHOP_CARD_PREFIX,
    SHOP_SCREEN_NAME,
    _area_rect,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BENCH_CAPACITY,
    REFRESH_COST_BASE,
    BenchChar,
    BuyCard,
    CloseShop,
    CompTransaction,
    GameState,
    LevelUp,
    RefreshShop,
    SellBench,
    bench_from_compact,
    bench_occupied,
    merge_buy_k,
    mutate_bench_deployed,
    simulate,
)
from sr_od.application.currency_war.telemetry import defects, recorder

if TYPE_CHECKING:
    from sr_od.operations.sr_operation import SrOperation  # noqa: F401


# ---------------------------------------------------------------------------
# 访问账本与执行环境
# ---------------------------------------------------------------------------

@dataclass
class ShopVisitLedger:
    """商店访问执行账(旧 ``run_buy_waves`` 闭包计数器的具名化,ADR-0517)。

    ``refresh_first_action`` = 本访问段(两次刷新之间的段)此前零动作
    ——「仅刷新波」判定输入(``refresh_wave_is_refresh_only`` 单一判据,
    刷前现读复用段顶整帧读的边界条件)。
    """

    total_buy: int = 0
    total_level: int = 0
    total_refresh: int = 0
    total_sell: int = 0
    total_sell_income: int = 0
    total_sell_skip: int = 0
    total_sell_fail: int = 0
    spend_executed: int = 0
    plan_truncated: bool = False
    refresh_skipped: str | None = None
    refresh_attempted: bool = False
    refresh_board_changed: bool | None = None
    bought_names: list[str] = field(default_factory=list)
    refresh_first_action: bool = True
    did_refresh: bool = False
    # `w536_merge_expect/` 买牌期望态基座(单元尾计算消费):
    buy_purchases: list = field(default_factory=list)
    buy_has_sell: bool = False
    buy_unidentified: bool = False


@dataclass
class ShopExecEnv:
    """动作 op 执行环境(画面 op 注入;动作 op 不自持画面层状态)。"""

    op: SrOperation
    match: object            # CurrencyWarMatch(避免运行时导入环,注解宽松)
    config: object
    click_pts: list
    level_btn: Point
    refresh_btn: Point
    ledger: ShopVisitLedger
    state: GameState         # 当前期望态(执行时点读;满栏 k 计等消费)


# ---------------------------------------------------------------------------
# 守卫断言(决策 9:防 bug 路栏,非法 = 响亮暴露)
# ---------------------------------------------------------------------------

def guard_proposal_vs_expected(action, state: GameState) -> None:
    """proposal-vs-expected 断言(ADR-0517 §守卫两属 (i))。

    提案动作引用的对象在期望态中确实存在且未被消费——防策略器算术 bug
    (单动作循环下期望态每动作后即更新,此属天然成立;断言炸出 = 策略器
    bug,禁静默跳过)。辖面:SellBench 的槽位占用与 expect 名一致性;
    BuyCard 的所购牌名在期望态店中(已买走/陈旧快照牌再提案 = 跨代际
    提案,炸出;未识别牌 name 空 = 无名可对,跳过名断言交未识别面处理;
    满栏 merge 买的「一击多张」豁免属 expected-vs-tracked 双账豁免,
    本断言不受豁免——提案时点牌仍在店中,名恒可对)。
    """
    if isinstance(action, BuyCard):
        _name = action.card.name or ''
        if _name and not any((c.name or '') == _name
                             for c in (state.shop or [])):
            raise AssertionError(
                f'[cw-shop][guard] BuyCard 提案牌不在期望态店中:'
                f'name={_name!r} cost={action.card.cost} '
                f'shop={[(c.name or "") for c in (state.shop or [])]}'
                '(策略器 bug:跨代际/已消费提案,ADR-0517 决策 9)')
        return
    if isinstance(action, SellBench):
        tgt = (state.bench[action.bench_idx]
               if 0 <= action.bench_idx < len(state.bench) else None)
        if tgt is None:
            raise AssertionError(
                f'[cw-shop][guard] SellBench 提案指向空槽/越界:'
                f'bench_idx={action.bench_idx} expect={action.expect!r} '
                f'bench={[b.char_id if b else None for b in state.bench]}'
                '(策略器 bug:期望态无此对象,ADR-0517 决策 9)')
        if action.expect and (tgt.char_id or '') != action.expect:
            raise AssertionError(
                f'[cw-shop][guard] SellBench 名-槽不一致:'
                f'idx={action.bench_idx} expect={action.expect!r} '
                f'实际={(tgt.char_id or "")!r}'
                '(策略器 bug:跨代际提案,ADR-0517 决策 9)')


def _bench_identity_signature(
        table: list[BenchChar | None]) -> list[tuple[str, int]]:
    """槽位表的占用身份签名(逐槽 (char_id, star);None 槽跳过)。"""
    return [(b.char_id or '', b.star or 1)
            for b in (table or []) if b is not None]


def _reseed_bench_layout(state: GameState,
                         tracked: list[BenchChar | None]) -> None:
    """投影 bench 布局按执行侧 tracked 槽位表就地回写(布局单一源重播种:
    churn 后 tracked/实况是重排侧真值,投影副本跟随)。"""
    state.bench[:] = list(tracked)


def guard_expected_vs_tracked(state: GameState, session,
                              stage: str = 'project') -> None:
    """expected-vs-tracked 双账断言(ADR-0517 §守卫两属 (ii))。

    期望态(project 链 = simulate 维护)vs 执行侧 tracked 账
    (``tracked_bench_chars`` 经 mutate 随执行更新)的对拍——分叉的
    在环检测器。零读屏(tracked 纯内存)。

    两级分型(签名比较先做多集(multiset)等价,再走两属归因):
    - **多集等价(槽位布局漂移,降级不炸)**:成员账对齐、仅槽位排列
      分歧——对账 churn(卖出/合并/换位)后 tracked/实况槽位重排,
      投影副本未跟随重播种,两侧落槽规则一致但「洞在哪」不同源
      (第八局 OpenShop HIT 实证:expected=[符玄,阮·梅,阮·梅] vs
      tracked=[阮·梅,符玄,阮·梅],买后守卫炸、环消化局存活)。
      处置 = WARNING 记「槽位布局漂移」另账 + 按 tracked 真值就地
      重播种投影 bench(``_reseed_bench_layout``)——回写源选 tracked
      而非 ``match.bench_slot_map`` 的依据:后者只在买组确认后产出
      (守卫炸点在组中,来不及)且只含所购名→槽、不承载 churn 重排
      与洞位;tracked 账纯内存随执行与对账更新,是重排侧,零读屏。
    - **真多集分歧**:按 stage 两属归因,断言炸出(消息见下)。
      stage='seed'(播种后、首动作前):tracked 非空时本对账按构造
      恒等(state.bench 即自 tracked 播种),唯一可达场景 = tracked 主
      账为空而屏幕 bench 非空 ⇒ 跟踪账丢件/识别幻影检测器;投影链无责。
      stage='project'(默认,动作投影后):分叉 = project/mutate 模型
      分叉——投影建模 bug 的唯一在环检测器(错误卖出会实际执行、损害
      不可逆,ADR-0516 投影口径族史)。

    已申报豁免(非分叉 bug 的已知建模分叉,豁免帧由调用方判定):
    满栏买入(执行侧 tracked 的 bench_place 在满栏时丢件,simulate 走
    §2.5 自动多买 k 张分支——两模型在满栏语境不同构,对账重挂点 = 下一
    入口观察)。豁免面外的真分叉 = 断言炸出。
    """
    tracked = bench_from_compact(
        [bc for bc in (getattr(session, 'tracked_bench_chars', None) or [])
         if bc is not None])
    expect_sig = _bench_identity_signature(state.bench)
    tracked_sig = _bench_identity_signature(tracked)
    if expect_sig != tracked_sig:
        from collections import Counter as _Counter
        if _Counter(expect_sig) == _Counter(tracked_sig):
            log.warning(
                '[cw-shop][guard] 双账槽位布局漂移(多集等价,降级不炸;'
                '已按 tracked 重播种投影 bench):expected=%s tracked=%s',
                expect_sig, tracked_sig)
            _reseed_bench_layout(state, tracked)
            return
        if stage == 'seed':
            raise AssertionError(
                '[cw-shop][guard] tracked 主账为空而屏幕 bench 非空'
                '(跟踪账丢件/识别幻影嫌疑,非播种错误——播种 bug 形态'
                '已随 ADR-0520 旧账退役消失):'
                f'expected={expect_sig} tracked={tracked_sig}'
                '(期望态在首动作前即与 tracked 账不同源,投影链无责;'
                '下一入口 heavy 读屏重建可归零)')
        raise AssertionError(
            '[cw-shop][guard] 期望态 vs tracked 双账分离(投影建模 bug?):'
            f'expected={expect_sig} tracked={tracked_sig}'
            '(ADR-0517 §守卫两属 (ii);首动作前另有播种期对账,'
            '此处炸出 = project/mutate 模型分叉)')


# ---------------------------------------------------------------------------
# 动作基类与具体动作 op
# ---------------------------------------------------------------------------

class ShopActionOp(ABC):
    """商店动作 op 基类(ADR-0517 决策 10:execute + project 两方法)。"""

    #: 终结动作(执行即本画面访问结束,交回外循环;决策 4)
    terminal: bool = False

    def __init__(self, action):
        self.action = action

    def project(self, state: GameState) -> GameState:
        """确定性投影(纯计算,零读屏):simulate 单一源(合成连锁/
        满栏 §2.5/金/等级全在其内;模块头知识缺口申报)。"""
        return simulate(state, self.action)

    @abstractmethod
    def execute(self, env: ShopExecEnv) -> bool:
        """机械执行;返回执行是否落地(SellBench 拖 3 次失败 = False,
        调用方据此跳过投影保持双账一致)。"""


class BuyCardOp(ShopActionOp):
    """买一张 = 一个动作 op(ADR-0517 决策 3;满栏例外下一击多张仍一个
    op,张数由游戏规则定、投影按 merge_buy_k 计——方案 A 补裁)。"""

    def execute(self, env: ShopExecEnv) -> bool:
        from one_dragon.base.geometry.point import Point as _Pt
        action: BuyCard = self.action
        op, match, ledger, state = env.op, env.match, env.ledger, env.state
        pt = (min(env.click_pts, key=lambda p: abs(p.x - action.card.x))
              if env.click_pts else _Pt(action.card.x, 288))
        # 买前裁该片矩形拷贝(`w536_merge_expect/`:「买了什么」的像素级
        # 证据,随期望态带到对账点;一帧原则,必须 copy 防帧缓存覆写)。
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
        log.info(f'[cw-shop] Buy click @({pt.x},{pt.y}) '
                 f'{action.card.faction}/{action.card.name}/'
                 f'{action.card.cost}')
        time.sleep(0.4)
        ledger.total_buy += 1
        ledger.spend_executed += action.card.cost
        if action.card.name:
            ledger.bought_names.append(action.card.name)
        mutate_bench_deployed(match.session.tracked_bench_chars,
                              match.session.tracked_deployed, action)
        if action.card.name:
            _cnt = 1
            if bench_occupied(state.bench) >= BENCH_CAPACITY:
                # 满栏例外(merge_mechanics §2.5 方案 A):一击多张,张数
                # 单一源 = merge_buy_k(禁执行侧重算);金账无折扣 = 总价
                # k×单价,执行账补差 (k−1)×单价。
                _cnt = max(1, merge_buy_k(
                    action.card.name, action.card.star or 1, state.bench,
                    match.session.tracked_deployed, state.shop))
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


class LevelUpOp(ShopActionOp):
    """升一级 = 一个动作 op(决策 3;clicks 序列 = 动作内部步骤,外部买
    面不可插花,ADR-0517 §权衡构造性消解)。单动作形态下每帧恰发一个
    「购买经验」单击,序列由决策循环逐帧重组。"""

    def execute(self, env: ShopExecEnv) -> bool:
        action: LevelUp = self.action
        op, ledger = env.op, env.ledger
        op.ctx.controller.click(env.level_btn)
        log.info(f'[cw-shop] LevelUp click @({env.level_btn.x},'
                 f'{env.level_btn.y})')
        # 用户口述口径(screen_flow_timing.md #22,2026-09-02):购买经验
        # 动画 ~1s(原 0.6s 不足;光标遮挡由段顶 park_cursor 防)。
        time.sleep(1.0)
        ledger.total_level += 1
        ledger.spend_executed += action.cost
        return True


class SellBenchOp(ShopActionOp):
    """卖一张 = 一个动作 op;卖回金实收遥测 = 执行实现层(候选 a)。"""

    def execute(self, env: ShopExecEnv) -> bool:
        action: SellBench = self.action
        op, match, ledger = env.op, env.match, env.ledger
        state = env.state
        _expected = (state.bench[action.bench_idx]
                     if 0 <= action.bench_idx < len(state.bench) else None)
        _expected_name = (_expected.char_id if _expected is not None else None)
        # 卖牌实收回金 = 执行前后 gold OCR 差,拖拽前取基数(候选 a 遥测)。
        _gold_before = None
        with contextlib.suppress(Exception):
            from sr_od.application.currency_war.obs.cw_observation import (
                read_gold,
            )
            _gold_before = read_gold(op.ctx, op.screenshot())
        from sr_od.application.currency_war.prep_actions import (
            drag_bench_to_sell,
        )
        ok = drag_bench_to_sell(op, op.ctx, action.bench_idx)
        if not ok:
            ledger.total_sell_fail += 1   # 拖 3 次源槽未变(现有语义)
            log.warning('[cw-shop] Sell bench%d %s 拖3次源槽未变',
                        action.bench_idx, _expected_name)
            return False
        # tracking 同步:置 None 不紧缩(ADR-0316);紧凑态先归一为槽位表
        # 语义再 mutate(索引=槽位,防清错槽)。
        _tracked = match.session.tracked_bench_chars
        _tracked[:] = bench_from_compact(
            [bc for bc in _tracked if bc is not None])
        mutate_bench_deployed(_tracked, match.session.tracked_deployed, action)
        # ADR-0328 执行域对齐:卖出件入同轮已卖集(执行成功是卖出事实的
        # 权威,register_round_sold 带轮键自校验)。
        from sr_od.application.currency_war.kernel.cw_round_ledger import (
            register_round_sold,
        )
        register_round_sold([_expected_name], state, match.session)
        ledger.total_sell += 1
        ledger.buy_has_sell = True   # 含卖出 → 本单元期望态不建(`w536`)
        ledger.total_sell_income += action.income or 0
        try:
            time.sleep(0.5)   # 卖出入账动画
            from sr_od.application.currency_war.obs.cw_observation import (
                read_gold,
            )
            _gold_after = read_gold(op.ctx, op.screenshot())
            recorder.record_sell_income(state, action.bench_idx,
                                        _expected_name or '',
                                        _gold_before, _gold_after)
        except Exception:   # noqa: BLE001  观测 best-effort
            pass
        log.info('[cw-shop] Sell bench%d %s(+%s) ✓',
                 action.bench_idx, _expected_name, action.income or '?')
        return True


class RefreshShopOp(ShopActionOp):
    """刷新 = 终结 op(决策 7:唯一引入新事实的动作,期望态必须在新事实
    处重建——终结后外循环入口重观察)。刷新有效性检测/免费刷新证据/
    刷新期望对账 = 执行实现层遥测(候选 a;与决策读屏解耦)。"""

    terminal = True

    def execute(self, env: ShopExecEnv) -> bool:
        from one_dragon.base.geometry.rectangle import Rect
        from one_dragon.utils import cv2_utils as _cvu

        # 读函数经 cw_op_buy_cards 模块属性路由(该模块的读点替身缝,
        # 测试 monkeypatch 面;自本模块直接 import 会绕开替身)。
        from sr_od.application.currency_war.operations.cw_op import (
            cw_op_buy_cards as _buy_cards_mod,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_op_buy_cards import (
            refresh_effective,
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
            if ledger.refresh_first_action:
                _pre_gold = state.gold if state.gold > 0 else None
                _pre_shop_names = [c.name for c in state.shop if c.name]
            else:
                _pre_shot = op.screenshot()
                _pre_gold = _buy_cards_mod.read_gold_opt(op.ctx, _pre_shot)
                _pre_shop_names = [c.name
                                   for c in _buy_cards_mod.read_shop_cards(
                                       op.ctx, _pre_shot)
                                   if c.name]
            _refresh_expect = build_refresh_expect(
                _pre_gold, REFRESH_COST_BASE,
                [(c.name, c.star) for c in state.shop],
                state.plane, state.round_num)
            _reconcile = refresh_reconcile_mismatches
        except Exception:   # noqa: BLE001  best-effort 不阻塞买牌
            _refresh_expect = None
            _reconcile = None
        op.ctx.controller.click(env.refresh_btn)
        log.info(f'[cw-shop] Refresh click @({env.refresh_btn.x},'
                 f'{env.refresh_btn.y})')
        # r325(P1⑤):刷新后两帧一致门(牌行区指纹;刷新动画帧上的
        # SIFT miss 是 r97/383 样本实证根因);超时 2.5s 回退旧 sleep 语义。
        _rects = (Rect(300, 228, 1560, 326),)   # 商店牌行
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
            recorder.record_shop_snapshot(
                'refresh', _new_shop, state.gold - _refresh_fee,
                state.plane, state.round_num)
            # 刷新有效性对拍(§2.5):三值,False=全同(未变)透传分类器。
            ledger.refresh_board_changed = refresh_effective(
                _pre_shop_names or [], [c.name for c in _new_shop])
            if ledger.refresh_board_changed is False:
                _ineff_shot = None
                with contextlib.suppress(Exception):
                    _ineff_shot = op.save_screenshot(
                        prefix='refresh_ineffective')
                defects.record_defect(
                    'shop_refresh', 'invariant_break',
                    expected=('刷后牌面≠刷前:'
                              f'{sorted(_pre_shop_names or [])}'),
                    observed=('刷新后5牌与刷前全同(点击落空/费金照扣未刷/'
                              f'动画误读):'
                              f'{sorted(c.name for c in _new_shop)}'),
                    plane=state.plane, round_num=state.round_num,
                    verdict='留证-刷新未生效嫌疑(费金照扣牌面未变)',
                    shot=_ineff_shot,
                    reader_source='refresh_set_compare',
                    gap_large=True,
                    refs=[{'stream': 'decisions',
                           'key': (f'plane={state.plane}'
                                   f'|round={state.round_num}'
                                   f'|refresh_wave='
                                   f'{ledger.total_refresh + 1}')}],
                    note='观测自检框架设计 §2.5:全同=刷新未生效;'
                         '两连全同才确认(台账复现计数)')
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
                        plane=state.plane, round_num=state.round_num,
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
        f'plane={state.plane} round={state.round_num} '
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


class CloseShopOp(ShopActionOp):
    """关店 = 恒可用终结 op(决策 4/6):执行即本画面访问结束;关店点击
    由编排壳(CwOpCloseShop)承担——与旧「空序列触发关店」同一落点,
    动作 op 内为 no-op。"""

    terminal = True

    def execute(self, env: ShopExecEnv) -> bool:
        return True


class CompTransactionOp(ShopActionOp):
    """整档替换事务 = 复合动作类(ADR-0517 §复合动作类):一个 op、
    原子投影、C1 前置合法性(任一子步资源不足 ⇒ 整体不提案)。

    **终结邻接 fallback(现行档)**:合成建模验证未过(非满栏一击张数
    = research 知识缺口,模块头申报)⇒ 执行后本画面访问结束交回外循环
    重观察(= 旧截断点语义,禁半档中间态)。商店单动作决策核现行不提案
    CompTransaction(词表保留;提案面在备战域),本 op 为词表完备性落位。
    """

    terminal = True

    def execute(self, env: ShopExecEnv) -> bool:
        log.info('[cw-shop] CompTransaction(终结邻接 fallback:'
                 '执行后交回外循环重观察,ADR-0517 §复合动作类)')
        return True


_OP_TABLE = {
    BuyCard: BuyCardOp,
    LevelUp: LevelUpOp,       # LevelUpShop is-a LevelUp,同 op(单击)
    RefreshShop: RefreshShopOp,
    SellBench: SellBenchOp,
    CloseShop: CloseShopOp,
    CompTransaction: CompTransactionOp,
}


def shop_action_op_for(action) -> ShopActionOp:
    """动作词表 → 动作 op(词表外类型 = 策略器 bug 响亮暴露,决策 9)。"""
    for cls, op_cls in _OP_TABLE.items():
        if isinstance(action, cls):
            return op_cls(action)
    raise AssertionError(
        f'[cw-shop][guard] 商店动作词表外类型:{type(action).__name__}'
        '(ADR-0517 决策 9:非法返回 = 策略器 bug,禁静默跳过)')
