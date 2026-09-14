"""商店单动作动作 op 集(ADR-0517 决策 3/10;flow 实施批)。

动作基类单方法(execute;原 execute+project 两方法契约(ADR-0517 决策 10)
的 project 半已删——T-163 纯规则路线裁定(用户 2026-09-12):策略与实机
操作链零 simulate 前瞻消费,期望态推进改走容器逻辑态直写
(``apply_shop_action_logic`` 简单腿 + ``apply_shop_merge_leg`` 合成升星腿,
kernel 规则单一源,与序列驱动器同形;等价性由锁 M1 钉,
test_cw_shop_projection_logic)):

- ``execute(env)``:机械执行(点击/拖拽;op 框架既有的重试/等待语义
  在此层),无判断。

**知识缺口申报(ADR-0517 决策 7 边界注;merge_mechanics 通篇未载)**:
非满栏常态时合成槽位买的一击张数无 research 记载——本实现取保守假设
**一击一张**(kernel 规则面同判:常态单击单张,满栏例外按 merge_buy_k
一击多张),规则模型误差由入口
对账兜底(下一画面入口观察 = 事实重建,决策 8)。实机冻结解除后补档
验证:验证未过则该买面升格为终结 op(原 fallback 载体 CompTransactionOp 已随 unified-action-factory 批2b R3 删除,终结语义收敛于 RefreshShop/CloseShop)。

守卫断言(决策 9):执行侧检查 = 防 bug 路栏非控制流分支,非法返回 =
策略器 bug 响亮暴露——``guard_proposal_vs_expected``(提案动作的对象在
期望态中存在且未被消费,防策略器算术 bug)+ ``guard_expected_vs_tracked``
(期望态逻辑态链 vs 执行侧 tracked 账双账对拍,逻辑态建模 bug 的唯一在环
检测器——历次逻辑态口径返工史证明逻辑态建模错是常态)。双账断言
零读屏(tracked 账纯内存随动),不违决策 1/8「循环内不读屏」。

执行侧观测通道(ADR-0517 §执行侧观测通道去向,候选 a;T-192 判效
拆除后的保留面):卖回金实收遥测/牌面变化留证位(安灯 free_refresh_proc
豁免判定输入)/免费刷新证据保留为 execute 实现层遥测,与决策读屏解耦
(均观测职责,非决策输入;刷新有效性判效半已随 T-192 拆除,判效权归
观察侧 reconcile)。
"""
from __future__ import annotations

import contextlib
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
    BenchChar,
    exec_state_of,
    pad_bench,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    BuyCard,
    SellBench,
)

# 刷新钮真值 reader 经模块属性路由消费(替身缝:测试 monkeypatch 模块属性,
# 直接 from-import 会绑死旧引用绕开替身,同 _buy_cards_mod 约定)。
from sr_od.application.currency_war.telemetry import defects

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_vocab import Action
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
    total_xp_buy: int = 0   # 买经验击数(单击=+4XP 非整级;真实升级=XP 过门槛,以读屏为准)
    total_refresh: int = 0
    total_sell: int = 0
    total_sell_income: int = 0
    total_sell_skip: int = 0
    spend_executed: int = 0
    plan_truncated: bool = False
    refresh_attempted: bool = False
    refresh_board_changed: bool | None = None
    bought_names: list[str] = field(default_factory=list)
    refresh_first_action: bool = True
    did_refresh: bool = False
    # `w536_merge_expect/` 买牌期望态基座(单元尾计算消费):
    buy_purchases: list = field(default_factory=list)
    buy_has_sell: bool = False
    buy_unidentified: bool = False
    # 买牌期望态基座(单元执行前 tracked 快照;迁移批 3.2 起随账本外发,
    # 消费方 = finalize 的 compute_buy_expect——事后取 tracked 已被本单元
    # 动作推进,必须取入口时点快照)。
    buy_pre_bench: list = field(default_factory=list)
    buy_pre_deployed: list = field(default_factory=list)
    # [索引定义] 访问事实行(安灯暂存载体;迁移批 3.2 切片5):list 下标 =
    # 发射序(先进先出;元素 = 发射/受阻时点构造的回执行 dict——发射行带
    # serialize_action 同 schema 动作载荷,受阻行仅结构化 extra);取值时机
    # = 发射时增量追加(写点 = note_shop_action_receipt,与 receipts 域
    # 同点同构造),自积累无容量上界,禁回读 receipts 滚动窗(容量 8 会
    # 截断繁忙访问段的计划侧 = 该停不停)。消费方 = visit_open_shop 经
    # unit_exec_facts_from_receipts 派生安灯判定输入。
    fact_rows: list = field(default_factory=list)
    # T-13 真值通道:刷前刷新钮按钮态 UI 读数(RefreshShopOp.execute 点击前
    # 帧快照,一次刷新写一次;消费方 = cw_op_buy_cards.apply_action_outcome
    # 免费闸)。None = 失读回退逻辑账(接线前保守形态),禁当 False。
    refresh_free_truth: bool | None = None
    # T-13 次数余量联动:免费态钮内剩余次数 UI 读数(同帧快照;消费方 =
    # apply_action_outcome 与 free_refresh_balance 逻辑账刷前值对票,失配落
    # 缺陷台账零决策)。
    refresh_free_remaining_truth: int | None = None
    # T-219 免费刷新对账三件(判定 = 对账类,比对收口在观察侧;动作 op
    # 只写不比)。写入端 = RefreshShopOp.execute(刷新点击前现读,一次
    # 刷新覆盖写一次);消费端 = run_buy_waves 段顶入口观察对账点(三腿
    # 比对 + 存证),消费即清 pending。坐标系:refresh_pre_gold = 刷前一帧
    # 游戏金币读数(仅刷新段 = 段顶整帧,连击段 = 点击前一帧;None =
    # 失读,金腿不可判);refresh_pre_names = 同帧商店 content 具名牌名集
    # (1080p 商店五槽读牌口径);生命周期 = 一次刷新恰一段(刷新为终结
    # op,段间无其他动作覆盖字段)。
    refresh_pre_gold: int | None = None
    refresh_pre_names: list[str] = field(default_factory=list)
    refresh_pending_reconcile: bool = False
    # T-251 种子段 tracked 空账读屏重建的单向阀门:同 visit(含刷新续段,
    # 账本跨段共用)至多尝试一次重建。触发红线 = tracked 空账/未建——
    # tracked 有账但与屏幕分叉不走此出口(那是丢件/幻影,重建会掩盖真
    # bug,交 guard_expected_vs_tracked 断言响亮暴露)。写点 =
    # run_buy_waves 段顶种子守卫前(消费方 rebuild_tracked_at_seed_if_vacant)。
    tracked_seed_rebuild_done: bool = False
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
    # 当前期望态(W6 波 4 容器化,设计件 §2.4-2:执行侧读点改容器单例
    # board_state_of(match.session);满栏 k 计等消费经席位/payload 读口)
    state: GameState


def _container_cards(state: GameState) -> list:
    """商店 payload 牌列表(容器;离屏 None = 空列表)。"""
    payload = state.shop.value
    return shop_payload_content_cards(payload)


def _plane_of(state: GameState) -> int:
    from sr_od.application.currency_war.kernel.cw_game_state import plane_of
    return plane_of(state)


def _round_of(state: GameState) -> int:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        round_num_of,
    )
    return round_num_of(state)


# ---------------------------------------------------------------------------
# 守卫断言(决策 9:防 bug 路栏,非法 = 响亮暴露)
# ---------------------------------------------------------------------------

def guard_proposal_vs_expected(action: Action, state: GameState) -> None:
    """proposal-vs-expected 断言(ADR-0517 §守卫两属 (i))。

    提案动作引用的对象在期望态中确实存在且未被消费——防策略器算术 bug
    (单动作循环下期望态每动作后即更新,此属天然成立;断言炸出 = 策略器
    bug,禁静默跳过)。辖面:SellBench 的槽位占用与 expect 名一致性;
    BuyCard 的所购牌名在期望态店中(已买走/陈旧快照牌再提案 = 跨代际
    提案,炸出;未识别牌 name 空 = 无名可对,跳过名断言交未识别面处理;
    满栏 merge 买的「一击多张」豁免属 expected-vs-tracked 双账豁免,
    本断言不受豁免——提案时点牌仍在店中,名恒可对)。
    """
    # bench_slots_of 读口在函数顶导入:函数体内任何位置的 import 语句都会
    # 把名字绑定为全函数局部变量——曾放 BuyCard 分支内,SellBench 分支
    # 未执行该 import 即引用,UnboundLocalError(2026-09-13 实机 T-181:
    # r2 席满卖人决策被守卫自身炸掉,触发买空店重进崩溃循环)。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_slots_of,
    )
    if isinstance(action, BuyCard):
        _name = action.card.name or ''
        _payload = state.shop.value
        if _name and not any((c.name or '') == _name
                             for c in shop_payload_content_cards(_payload)):
            raise AssertionError(
                f'[cw-shop][guard] BuyCard 提案牌不在期望态店中:'
                f'name={_name!r} cost={action.card.cost} '
                f'shop={[(c.name or "") for c in shop_payload_content_cards(_payload)]}'
                '(策略器 bug:跨代际/已消费提案,ADR-0517 决策 9)')
        return
    if isinstance(action, SellBench):
        _slots = bench_slots_of(state)
        tgt = (_slots[action.bench_idx]
               if 0 <= action.bench_idx < len(_slots) else None)
        if tgt is None:
            raise AssertionError(
                f'[cw-shop][guard] SellBench 提案指向空槽/越界:'
                f'bench_idx={action.bench_idx} expect={action.expect!r} '
                f'bench={[b.char_id if b else None for b in _slots]}'
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
                         tracked: list[BenchChar | None]) -> bool:
    """逻辑态 bench 布局按执行侧 tracked 槽位表就地回写(布局单一源重播种:
    churn 后 tracked/实况是重排侧真值,逻辑态副本跟随)。

    槽号健康门:tracked 槽号来自 SIFT/对账 churn,属无守卫数据——占用
    槽号须唯一 ∧ 全在 1..BENCH_CAPACITY,违者**拒绝重播种**维持旧布局
    (防坏槽号污染逻辑态后进入 M4 卖出链:重播种后两账同源,
    guard_proposal_vs_expected 对表位置-物理格错位结构性失明,错格拖拽
    = 卖错人/卖空格),并落 ``bench_slot_unhealthy`` 台账分键留证。
    返回是否实际重播种。
    """
    occupied = [b for b in (tracked or []) if b is not None]
    slots = [b.slot for b in occupied]
    healthy = all(isinstance(s, int) and 1 <= s <= BENCH_CAPACITY
                  for s in slots) and len(set(slots)) == len(slots)
    if not healthy:
        with contextlib.suppress(Exception):
            defects.record_defect(
                'bench', defects.DEFECT_KIND_BENCH_SLOT_UNHEALTHY,
                expected='tracked 占用槽号唯一 ∧ 全在 1..BENCH_CAPACITY',
                observed=f'slots={sorted(slots)}',
                verdict=('留证-tracked 槽号不健康,拒绝重播种(维持旧逻辑态'
                         '布局,坏槽号不进不可逆卖出链;根因=对账 churn '
                         '槽号无守卫,归观察层仲裁批)'),
                reader_source='reseed_health_gate',
                gap_large=True,
                note='重播种槽号健康门(占用表槽号唯一性与值域校验)')
        return False
    # 写目标 = 容器 bench 域(W6 波 4,设计件 §2.3:重播种写点 =
    # write_logic(bs.bench, tracked 重建 BenchView),逻辑态域集例外申报
    # 面;原「逻辑态帧就地回写」(前身黑板槽载体)随黑板槽退役消亡)。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
        bench_view_of_slots,
    )
    assert isinstance(state, GameState)   # 容器形态唯一(波 4 起)
    state.write_logic(state.bench, bench_view_of_slots(list(tracked)),
                      produced_by='reseed_bench_layout',
                      sig=ChannelSig(
                          family='logic_action', actor='CwScreenBuyCards',
                          mode='compute',
                          group_id=(f'act:CwScreenBuyCards@'
                                    f'{state.write_seq + 1}')))
    return True


def reseed_bench_if_layout_stale(state: GameState, session,
                                 seed_epoch: int) -> str:
    """S3 布局代次检差三步的封装(ADR-0646;单动作循环每动作消费前调用)。

    检差:exec_state 布局代次 vs 播种期快照——命中 = visit 内布局已重排
    (reconcile 纠漂递增,唯一写点 kernel/cw_reconcile),已发射动作的
    bench_idx 代际失效,不可只换 state.bench。三步语义:
    ①截断在飞计划(序列决策契约截断语义,plan_truncated 记账由调用方承担——
      本函数零 ledger 依赖,保持纯逻辑态面可单测);
    ②按 tracked 重播种(下标直拷 pad 后经 ``_reseed_bench_layout``,
      含槽号健康门——脏槽号拒绝重播种维持旧布局);
    ③重入决策(调用方 continue,decide 消费重播种后黑板帧)。

    Returns:
        'clean' = 代次未变(常态,当前架构 S2+S1 后恒此值——reconcile 均在
        visit 外跑);'reseeded' = 检差命中且重播种成功(调用方重入决策);
        'failed' = 检差命中但重播种被槽号健康门拒绝(布局不可信,调用方应
        fail-stop 本段收工交回外循环重观察——禁在不可信布局上继续发射)。
    """
    if exec_state_of(session).bench_layout_epoch == seed_epoch:
        return 'clean'
    tracked = pad_bench(deepcopy(
        getattr(exec_state_of(session), 'tracked_bench_chars', None) or []))
    if not _reseed_bench_layout(state, tracked):
        return 'failed'
    return 'reseeded'


def guard_expected_vs_tracked(state: GameState, session,
                              stage: str = 'project') -> None:
    """expected-vs-tracked 双账断言(ADR-0517 §守卫两属 (ii))。

    期望态(容器逻辑态直写链 = apply_shop_action_logic/合成升星腿维护;
    T-163 起 simulate 前瞻推算已删)vs 执行侧 tracked 账
    (``tracked_bench_chars`` 经 mutate 随执行更新)的对拍——分叉的
    在环检测器。零读屏(tracked 纯内存)。

    两级分型(签名比较先做多集(multiset)等价,再走两属归因):
    - **多集等价(槽位布局漂移,降级不炸)**:成员账对齐、仅槽位排列
      分歧——历史 bug 态(tracked 紧凑 × slot 稀疏)下对账 churn 后两域
      落洞不同源。根因申报(T-308/ADR-0646 已治本):漂移之根 =
      reconcile 写回紧凑列表制造**布局双源**——两域在播种时刻即读出
      不同布局(逻辑态=bench_from_compact 槽号重构、tracked=mutate 下标
      演化),每次落洞动作放大一次差异。治本 = S2 写回经
      bench_from_compact 重建槽位表(kernel/cw_reconcile,deployed 侧
      同构先例补齐)+ S1 tracked 域消费点下标直拷(播种同源,本守卫的
      tracked 构造即其一点);本重播种保留为 guard 内自愈通道 + S3
      epoch 检差(``reseed_bench_if_layout_stale``)的复用件,历史
      bug 态(tracked 未及 S2 重建)残留时仍可显影自愈。
      处置 = WARNING + 台账分键 ``bench_slot_layout_drift`` 留证
      (判读工具可查)+ 按 tracked 真值就地重播种逻辑态 bench
      (``_reseed_bench_layout``,含槽号健康门)——回写源选 tracked
      而非 ``match.bench_slot_map`` 的依据:后者只在买组确认后产出
      (守卫炸点在组中,来不及)且只含所购名→槽、不承载 churn 重排
      与洞位;tracked 账纯内存随执行与对账更新,是重排侧,零读屏。
    - **真多集分歧**:按 stage 两属归因,断言炸出(消息见下)。
      stage='seed'(visit 入口首动作前):期望侧 = 容器 bench(唯一实机
      漏斗写端 = 备战装配环 bench 观察块;合成口对未读域跳写,见
      CwSimFrame.bench_readable),两账多集分歧 = 观察漏斗与执行账
      真实分叉(跟踪账丢件/观察失真),断言炸出后由店开态恢复路由
      接管(cw_screen_buy_cards:守卫前的空账/接管重建出口辖结构性
      不同源;守卫后的收店→备战环 heavy 重建→再入辖有账真分歧,
      对局预算一次,耗尽即停)。
      stage='project'(默认,动作直写后):分叉 = 逻辑态直写/mutate 模型
      分叉——逻辑态建模 bug 的唯一在环检测器(错误卖出会实际执行、损害
      不可逆,历次逻辑态口径返工史为证)。

    已申报豁免(非分叉 bug 的已知建模分叉,豁免帧由调用方判定):
    满栏买入(豁免面 = 游戏接受而两模型都不收编的残余窗:非合成满栏买
    被游戏拒绝而像素差漏检的 fail-open 形态。合成满栏买面已随 T-182
    同构化——mutate 带 shop 视图走 `_apply_full_bench_merge_buy` 同
    分支,不再丢件漏记)。豁免面外的真分叉 = 断言炸出。
    """
    # T-308/ADR-0646 S1:tracked 输入域下标直拷(pad 补 None;deepcopy 隔离
    # ——旧 bench_from_compact 冲突分支经 bench_place 就地改 bc.slot,守卫
    # 读路径存在写副作用,直拷后自然关闭)。禁读 slot 字段:tracked 域
    # slot 与下标的一致性由 S2 写回端保证,消费端下标即布局(与 SIFT 现读
    # 域「slot 与读序同帧同源」是两套命题,分界见 ADR-0646)。
    tracked = pad_bench(deepcopy(
        getattr(exec_state_of(session), 'tracked_bench_chars', None) or []))
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_slots_of,
    )
    expect_sig = _bench_identity_signature(bench_slots_of(state))
    tracked_sig = _bench_identity_signature(tracked)
    if expect_sig != tracked_sig:
        from collections import Counter as _Counter
        if _Counter(expect_sig) == _Counter(tracked_sig):
            log.warning(
                '[cw-shop][guard] 双账槽位布局漂移(多集等价,降级不炸;'
                '已按 tracked 重播种逻辑态 bench):expected=%s tracked=%s',
                expect_sig, tracked_sig)
            with contextlib.suppress(Exception):
                defects.record_defect(
                    'bench', defects.DEFECT_KIND_BENCH_SLOT_LAYOUT_DRIFT,
                    expected=f'expected={expect_sig}',
                    observed=f'tracked={tracked_sig}',
                    verdict=('留证-双账槽位布局漂移(多集等价,仅槽序分歧;'
                             '降级不炸,已按 tracked 真值重播种逻辑态 bench;'
                             '根因=播种双源已随 T-308/ADR-0646 S2+S1 治本,'
                             '本行为历史 bug 态残留自愈面,复发=回退哨兵)'),
                    reader_source='guard_expected_vs_tracked',
                    gap_large=False,
                    note='双账对拍守卫降级分支(多集等价;真分歧仍 AssertionError)')
            _reseed_bench_layout(state, tracked)
            return
        if stage == 'seed':
            # 文案与实际条件对齐(勘误:旧文案「tracked 主账为空而屏幕
            # bench 非空」只覆盖单侧形态,本分支真实条件 = 双账多集不等
            # 的任意方向真分歧;旧句「下一入口 heavy 读屏重建可归零」
            # 描述的路径在店开 0n/接管首分发结构性不可达,现役出路 =
            # 守卫**前**的 rebuild_tracked_at_seed_if_vacant(空账/接管
            # 待办辖域)+ 守卫**后**的种子分叉恢复路由(收店→备战环
            # heavy 重建→再入,对局预算一次;耗尽 = 本消息随 round_fail
            # 升级为停机凭据,见 cw_screen_buy_cards 恢复路由)。
            raise AssertionError(
                '[cw-shop][guard] 种子期双账多集真分歧(播种/入口账分叉:'
                '跟踪账丢件/识别幻影/逻辑态陈旧嫌疑,非播种错误——播种 '
                'bug 形态已随 ADR-0520 旧账退役消失):'
                f'expected={expect_sig} tracked={tracked_sig}'
                '(期望态在首动作前即与 tracked 账不同源,逻辑态链无责)')
        raise AssertionError(
            '[cw-shop][guard] 期望态 vs tracked 双账分离(逻辑态建模 bug?):'
            f'expected={expect_sig} tracked={tracked_sig}'
            '(ADR-0517 §守卫两属 (ii);首动作前另有播种期对账,'
            '此处炸出 = project/mutate 模型分叉)')



# 商店单动作 op 族住动作文件:通用基类 ActionOp = cw_action_base.py
# (批1 自 ShopActionOp 升格);六动作 = 各自 cw_<action>_action.py;
# 词表→op 工厂 = cw_action_registry.py(单一注册表,批1 自
# cw_shop_actions 迁入,消费面 shop_action_op_for 转薄委托)。本文件 =
# 账本+守卫+执行支撑(ShopExecEnv/ShopVisitLedger 单一源;ShopExecEnv
# 以公共字段 op/match/config 结构化满足 ActionExecEnv 协议)。
