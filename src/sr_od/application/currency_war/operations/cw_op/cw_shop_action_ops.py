"""商店单动作动作 op 集(ADR-0517 决策 3/10;flow 实施批)。

动作基类单方法(execute;原 execute+project 两方法契约(ADR-0517 决策 10)
的 project 半已删——T-163 纯规则路线裁定(用户 2026-09-12):策略与实机
操作链零 simulate 前瞻消费,期望态推进改走容器逻辑态直写
(``apply_shop_action_logic`` 简单腿 + ``apply_shop_merge_leg`` 合成升星腿,
kernel 规则单一源,与序列驱动器同形;写语义由投影直锁钉
(锁 M1,test_cw_shop_projection_logic)):

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
期望态中存在且未被消费,防策略器算术 bug)。原 ``guard_expected_vs_
tracked``(期望态 vs tracked 双账对拍)已随 T-268 退役(用户裁定·对账
归属原则:对账 = 观察 vs 逻辑的双态比对,唯一合法时点 = 画面 op 上报
观察数据进入 game state 的观察边界,由 kernel cw_reconcile 执行;规则
文本 = flow/screen_op.md §2.3/§4)——逻辑态建模 bug 的检出归观察边界
reconcile 纠漂显影(观察赢),op 层不再做双态比对。

执行侧观测通道(ADR-0517 §执行侧观测通道去向,候选 a;T-192 判效
拆除后的保留面):卖回金实收遥测/牌面变化留证位(安灯 free_refresh_proc
豁免判定输入)/免费刷新证据保留为 execute 实现层遥测,与决策读屏解耦
(均观测职责,非决策输入;刷新有效性判效半已随 T-192 拆除,判效权归
观察侧 reconcile)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    game_state_of,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    BuyCard,
    SellBench,
)

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
    # (refresh_board_changed 字段已随批4 比对收口退役:三值对比单一源 =
    #  cw_shop_refresh_obs.refresh_board_changed_of,刷前/刷后名集原样
    #  落账(refresh_pre_names/refresh_post_names),消费点现算,禁再
    #  在动作 op 内预计算比对结果。)
    bought_names: list[str] = field(default_factory=list)
    refresh_first_action: bool = True
    did_refresh: bool = False
    # `w536_merge_expect/` 买牌期望态基座(单元尾计算消费):
    buy_purchases: list = field(default_factory=list)
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
    # 刷后牌名集原样落账(批4 比对收口:动作 op 只读不比;三值对比单一
    # 源 = cw_shop_refresh_obs.refresh_board_changed_of,消费方 = 刷新回执
    # extra(安灯 free_refresh_proc 豁免判定输入)与入口观察对账点免费腿)。
    # 坐标系:同帧商店 content 具名牌名列表(1080p 商店五槽读牌口径,与
    # refresh_pre_names 同帧语义对侧);空表 = 刷后帧失读/全空位(对比
    # 函数按 None 不可判处理,宁缺勿造)。生命周期 = 一次刷新恰一段。
    refresh_post_names: list[str] = field(default_factory=list)
    # 刷新期望三件组(批4 比对收口随账本外发;原 RefreshShopOp.execute
    # 内联消费迁入口观察对账点):值 = build_refresh_expect 产物
    # ((期望金/卡判据, 位面, 轮次)元组)或 None(失读跳过对账,宁缺
    # 勿造)。写入端 = RefreshShopOp.execute(刷新点击前现读构建,期望
    # 基于波前状态);消费端 = run_buy_waves 段顶入口观察对账点
    # (refresh_expect_mismatch 腿,缺陷台账承接,消费即清 pending)。
    refresh_expect: tuple | None = None


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
    # game_state_of(match.session);满栏 k 计等消费经席位/payload 读口)
    state: GameState
    # 买牌 miss 计数键旁路(T-44 买牌落地验证):发射牌的物理槽号。
    # [索引定义] 商店牌行物理槽 1-5(screen_info「商店牌-N」area 序,
    # 1 基);取值时机 = 执行期(点击解析后);写入端 = BuyCardOp 仅
    # miss 时;0 = 未写(非买动作/落地路径)。消费端 = run_buy_waves
    # miss 计数口(cw_screen_buy_cards.buy_miss_streak_tick 的键)。
    last_buy_slot_no: int = 0


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


def bench_layout_stale(session, seed_epoch: int) -> bool:
    """S3 布局代次检差(T-271 fail-stop 形态)。

    检差:容器簿记布局代次(GameState.exec_books.bench_layout_epoch,唯一
    写点 kernel/cw_reconcile)vs 播种期快照——命中 = visit 内布局已重排,
    已发射动作的 bench_idx 代际失效。

    处置 = fail-stop(与未观察机制同构,编排者裁定,T-268 卡 note):
    命中即本段收工交回外循环,外循环落回备战 heavy 观察 → 入口
    reconcile 锚定后再进店。禁店内按执行侧簿记重播种容器 bench——那是
    op 层第二条容器 bench 写口,违写口归属硬规则(对账与仲裁唯一发生
    在观察边界,flow/screen_op.md §4 + action-logic-state.md §1.3);
    槽号健康门留证职责由 reconcile 前置槽号健康门承接。

    Returns:
        True = 布局代次已漂移(调用方 fail-stop 本段收工);
        False = 代次未变(常态)。
    """
    return game_state_of(session).exec_books.bench_layout_epoch != seed_epoch


# 商店单动作 op 族住动作文件:通用基类 ActionOp = cw_action_base.py
# (批1 自 ShopActionOp 升格);六动作 = 各自 cw_<action>_action.py;
# 词表→op 工厂 = cw_action_registry.py(单一注册表,批1 自
# cw_shop_actions 迁入,消费面 shop_action_op_for 转薄委托)。本文件 =
# 账本+守卫+执行支撑(ShopExecEnv/ShopVisitLedger 单一源;ShopExecEnv
# 以公共字段 op/match/config 结构化满足 ActionExecEnv 协议)。
