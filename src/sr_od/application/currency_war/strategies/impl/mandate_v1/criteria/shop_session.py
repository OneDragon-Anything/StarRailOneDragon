"""criteria/shop_session——商店会话读数协议与解拦复核(shop_session §4.2)。

本模块 = 商店会话的共用判据面(宪法第 6 条:备战第 4 步与商店入口两画面
消费同一函数,非画面文件互 import;存储 = session_scope/StrategyState)。

## 金位读数协议(账面维持 + 事件全集登记制 + 会话入口再锚定)

as-built 备战帧金位不可观察(cw_screen_prep「gold 仅 shop 开态可信」门
+ economy_cycle prep 帧恒 0 未采 + cw_screen_shop 备战帧 gold 门三处直证),
备战域金位唯一供给 = 本协议的账面(第 3 步攒批/第 7 步凑息/备战域变现/
第 4 步解拦复核金位腿消费):

- **① 记账层(已知 delta 多写点)**:买牌花费/卖出退金/购买经验单价
  由执行链上报函数写 ``gs.gold``(动作 op 自上报,期望态投影),账面
  经 :func:`sync_gold_ledger` 每决策帧入口再同步吸收(有效时账面 ==
  ``gs.gold`` 不变量;发出点不重复挂 delta 钩子防双记);付费刷新费由
  上报链直读容器刷价扣金(2026-10-16 用户裁决,与买牌同款双端逻辑态
  ——推翻旧「终结跳写、真值 = 下一入口观察」口径),账面同经再同步
  吸收;**单卡「X 动作时 +Y 金」型伴生入金**(返利/返利+〔每购买 3
  个 5 费角色 +3〕/节节高升〔任意升级 +1〕)上报链不覆盖,经伴生函数
  **双写**(账面 + ``gs.gold`` 期望态投影扩展);合并同类项(刷新出
  对 +1)与经验财富×淘金客类组合态由③的重进锚定吸收(组合空间不可
  枚举,归兜底不重复记账);
- **② 失效触发层(按事件/族组织,事件帧置 None)**:选卡族(任何三选一/
  二选一选卡帧,选中即失效实读——集中挂点 = flow._require_slot_options)
  / 合成族(任何 3★ 合成结果帧不分源,持有 3★ 集合帧差检测)/ 晶矿族
  (点晶矿随机金)/ 升级 9 级(成长基金 +40,独立失效)/ 计数达阈族
  (二手市场总刷 20 次 +30 / 长线利好第 30 次付费刷 +20——计数达阈帧
  失效,阈值帧兜底);「经验就是财富」(XP→金持续转换)入金时点 = 自然
  经验结算 = 节点边界,由节点边界重置天然吸收(失效先行);族登记制
  (新增卡入 cw_invest_data 注册表时按「伴生入金/选卡帧/独立失效」三分
  归类,漏归类由 ③ 再锚定收敛 + ④ 偏差侦测暴露);
- **③ 会话入口再锚定**(:func:`anchor_gold_ledger_if_new_visit`):商店
  画面每次访问入口(op 观察 node 与 sim 驱动器两路都在 visit 入口对
  ``cw4_segment_serial`` +1)金位实读可见,以实读重锚定账面基值(消除
  累积漂移与漏账;刷新重进/受限访问帧同——访问入口即实读);
- **④ 多卖循环账面判缺口**:凑息/变现卖到缺口闭合的第二笔起用账面金
  (:func:`session_gold`)判缺口,禁每笔触发开店重读(防震荡申报的自洽
  前提);账面与下一实读偏差 = 漏账侦测信号(实机观察点)。

## 解拦复核(shop_session §4.2;唯一触发点 = 备战第 4 步入口)

入口段(关门态)= :func:`shop_unblock_recheck`:判金位(账面)/席位空出
(备战可观察),任一使清单记录拦因解除 → 解拦(调用方清标记开店);金位
腿账面失效时申报读数开门(路径③金位读数形态,契约 A)。店内段 =
:func:`shop_recheck_drop_off_face`:会话入口验证记录的目标牌是否仍在
当前牌面,不在即销项(刷新/消耗后已不在店)。方向锁定不走清单解拦(锁定
写入直接清标记,line_and_upgrade §1.4)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    bench_units_of,
    deployed_rows_of,
    gold_of,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import session_scope
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_vocab import ShopCard


# ============================================================ 金位读数协议


def gold_ledger_of(gs: GameState) -> int | None:
    """金位账面读口(None = 失效待再锚定;备战域金位消费的单一供给)。

    有效时账面值 = ``gs.gold`` 的受控镜像(见 :func:`sync_gold_ledger`
    ——买/卖/经验 delta 由上报链写 ``gs.gold``、入口再同步吸收;伴生
    入金双写;付费刷新费由上报链终结跳写、下次访问入口锚定吸收)。"""
    return state_of(gs).gold_ledger


def sync_gold_ledger(gs: GameState) -> None:
    """账面值入口再同步(每决策帧入口调用,失效帧 no-op)。

    为什么需要:买/卖/经验的 delta 由执行链上报函数只写 ``gs.gold``
    (上一帧执行后的投影),账面值经本同步吸收这些 delta 维持
    「有效时账面 == gs.gold」不变量——发出点无须逐动作挂 delta 钩子
    (上报链已写的再记一次 = 双记),伴生入金(上报链不覆盖)仍经
    :func:`apply_gold_delta` 双写。"""
    st = state_of(gs)
    if st.gold_ledger is not None:
        st.gold_ledger = gold_of(gs)


def session_gold(gs: GameState) -> int:
    """会话内金位读口:账面优先,失效帧回退容器逻辑值(防御——会话入口
    必锚定,失效帧到达此处的唯一形态 = 锚定前的首帧内务序)。"""
    led = state_of(gs).gold_ledger
    return gold_of(gs) if led is None else int(led)


def anchor_gold_ledger_if_new_visit(gs: GameState) -> bool:
    """会话入口再锚定(协议③;返回 True = 本帧为新 visit 首帧)。

    visit 判重 = ``cw4_segment_serial`` 对比(生产 op 观察 node 与 sim
    驱动器两路均在访问入口 +1,单一锚定信号——覆盖会话入口/刷新重进/
    受限访问帧三类实读时点)。锚定值 = 该帧 ``gs.gold``(入口观察刚写入
    的实读真值)。

    漏账偏差侦测(锚定位留痕):锚定前账面非 None ∧ 与实读不等 ⇒ 计数
    ``gold_ledger_drift``(+``gold_ledger_drift_last_delta`` 末次差值)
    ——伴生记账漏项/失效族缺口的 telemetry 可见面,差值符号与幅度供
    实机 reconcile 归因(正偏差 = 漏计收入侧,负偏差 = 漏计支出侧)。"""
    st = state_of(gs)
    serial = st.cw4_segment_serial
    if st.gold_ledger_visit_serial == serial:
        return False
    st.gold_ledger_visit_serial = serial
    fresh = gold_of(gs)
    if st.gold_ledger is not None and st.gold_ledger != fresh:
        ct = st.cw4_counters
        if isinstance(ct, dict):
            ct['gold_ledger_drift'] = ct.get('gold_ledger_drift', 0) + 1
            ct['gold_ledger_drift_last_delta'] = \
                int(fresh) - int(st.gold_ledger)
    st.gold_ledger = fresh
    return True


#: 记账层伴生写容器的信号源标记(审计可辨:伴生入金非观察写)。
_COMPANION_SIG = ChannelSig(family='logic_action',
                            actor='shop_session.companion_gold',
                            mode='compute')


def apply_gold_delta(gs: GameState, delta: int, *,
                     also_container: bool = False) -> None:
    """记账层同步(协议①):已知 delta 写账面;``also_container=True``
    同时调 ``gs.gold``(伴生入金——上报链不覆盖的部分,期望态投影扩展;
    买/卖/刷/经验的 delta 由上报链写容器,本函数只同步账面防双记)。"""
    if delta == 0:
        return
    st = state_of(gs)
    if st.gold_ledger is not None:
        st.gold_ledger = int(st.gold_ledger) + int(delta)
    if also_container:
        gs.write_logic(
            gs.gold, int(gold_of(gs)) + int(delta),
            produced_by='shop_session.apply_gold_delta',
            sig=_COMPANION_SIG)


#: 失效触发族的计数键前缀(协议②;family 直接入键,判读可归因)。
INVALIDATE_COUNTER_KEY: str = 'gold_ledger_invalidated'


def invalidate_gold_ledger(gs: GameState, family: str) -> None:
    """失效触发(协议②):事件帧置 None——账面待下次实读再锚定。

    ``family`` = 族键(自由命名,判读归因;闭集 = 选卡/合成/晶矿/升 9 级/
    计数达阈/节点边界)。"""
    st = state_of(gs)
    st.gold_ledger = None
    ct = st.cw4_counters
    if isinstance(ct, dict):
        ct[f'{INVALIDATE_COUNTER_KEY}_{family}'] = \
            ct.get(f'{INVALIDATE_COUNTER_KEY}_{family}', 0) + 1


# ------------------------------------------------------------ 伴生入金(单卡)


def _augment_held(gs: GameState, name: str) -> bool:
    """投资策略持有判定(注册表名单 vs active_strategies 容器现读)。

    族登记制载体:新卡入 ``data/cw_invest_data`` 注册表时按效果文本三分
    归类——「X 动作时 +Y 金」单卡型入伴生(本模块)/选卡帧入选卡族/
    其余归兜底(再锚定收敛 + 偏差侦测暴露);归类触发的登记面归
    research/invest_effects 增补节(正本更新清单行)。"""
    return name in (gs.active_strategies.value or ())


#: 返利族的 5 费购买计数阈值(卡面文本「每购买 3 个 5 费角色,获得 3 金币」)。
REBATE_FIVE_COST_BATCH: int = 3
#: 返利族的达阈入账金额(卡面确定量)。
REBATE_GRANT_GOLD: int = 3


def account_buy_companion_gold(gs: GameState, card: ShopCard) -> int:
    """买入伴生入金(协议①单卡型:返利/返利+——每购买 3 个 5 费角色 +3)。

    5 费购买计数 = 局级单调计数器(达阈帧以卡面确定金额双写入账);返利+
    的「立刻获得 6 金币」部分属选卡帧入金(选卡族失效覆盖,不在此记)。
    返回本笔伴生金额(0 = 无伴生)。"""
    name = str(getattr(card, 'name', '') or '')
    cost = int(getattr(card, 'cost', 0) or 0)
    if not name or cost != 5:
        return 0
    if not (_augment_held(gs, '返利') or _augment_held(gs, '返利+')):
        return 0
    st = state_of(gs)
    st.shop_five_cost_buys += 1
    if st.shop_five_cost_buys % REBATE_FIVE_COST_BATCH != 0:
        return 0
    apply_gold_delta(gs, REBATE_GRANT_GOLD, also_container=True)
    ct = st.cw4_counters
    if isinstance(ct, dict):
        ct['companion_gold_rebate'] = \
            ct.get('companion_gold_rebate', 0) + 1
    return REBATE_GRANT_GOLD


#: 节节高升的升级伴生金额(卡面文本「每次升级时获得……1 金币」)。
LEVELUP_COMPANION_GOLD: int = 1


def account_upgrade_companion_gold(gs: GameState) -> int:
    """升级伴生入金(协议①单卡型:节节高升——任意升级 +1)。

    其「获得 1 个 2 星角色」部分 = 观察侧承接(升级转场后备战 heavy
    观察自然吸收,账面不记单位面)。返回本笔伴生金额(0 = 无伴生)。"""
    if not _augment_held(gs, '节节高升'):
        return 0
    apply_gold_delta(gs, LEVELUP_COMPANION_GOLD, also_container=True)
    ct = state_of(gs).cw4_counters
    if isinstance(ct, dict):
        ct['companion_gold_levelup'] = \
            ct.get('companion_gold_levelup', 0) + 1
    return LEVELUP_COMPANION_GOLD


# ------------------------------------------------------------ 事件级失效触发


def note_pick_frame(gs: GameState) -> None:
    """选卡族失效(协议②):任何三选一/二选一选卡决策帧——选中即失效
    实读,不枚举单项效果(发金/清金/hp 改写/存款语义)。

    集中挂点 = flow._require_slot_options(全部 pick 决策入口共用的候选
    槽读口;prep/shop 决策不经此口)。"""
    invalidate_gold_ledger(gs, 'pick')


def note_ore_click(gs: GameState) -> None:
    """晶矿族失效(协议②):点晶矿(普通金 1-5 随机 + 增发货币逐位面
    确定 + sphere 三选一)——随机量不可精确记账,失效交再锚定收敛。"""
    invalidate_gold_ledger(gs, 'ore')


def note_levelup_emission(gs: GameState, new_level: int) -> None:
    """升级动作发出的失效/入账挂点:升级 9 级(成长基金 +40,独立失效)+
    节节高升伴生(任意升级 +1,记账层)。

    消费位 = 备战第 3 步执行帧与会话内升级执行位(整批动作发出帧);``new_level``
    = 发出后到达等级(本批 = 当前级 + 1)。"""
    account_upgrade_companion_gold(gs)
    if int(new_level) >= 9:
        invalidate_gold_ledger(gs, 'level9')


#: 计数达阈族阈值(卡面文本:二手市场「商店刷新 20 次后获得 30 金币」/
#: 长线利好「花费金币进行 30 次刷新后,获得 20 金币」)。计数单一源 =
#: ``gs.effects.refresh_total/refresh_paid``(EffectsInventory,刷新上报
#: ``record_refresh`` 单口直加——本协议不自建第二计数器;二手市场 +30 /
#: 长线利好 +20 金均由上报尾部 ``check_env_refresh_grants`` 写 gs.gold
#: (T-21 后长线利好同有上报写点),失效语义降为阈值帧兜底)。
SECONDHAND_MARKET_TOTAL: int = 20
LONG_TERM_PAID_REFRESH: int = 30


def note_refresh_counters(gs: GameState, cost: int) -> None:
    """刷新计数达阈族失效(协议②;店内域挂点 = 刷新动作发出点)。

    达阈帧失效(阈值帧兜底):计数含本笔后恰达阈值 ⇒ 置 None。计数读
    ``gs.effects`` 现值 +1(动作发出点先于上报,上报后计数已含本笔——两
    时点读数等价,本处取前瞻值免下帧重判);总刷(含免费)覆盖二手市场
    20 次,付费刷覆盖长线利好 30 次(两域官方文本对照 = ENV_REFRESH_
    GRANTS 注)。刷新本身终结访问,重进锚定天然承接失效后的再锚定。"""
    eff = gs.effects
    if int(eff.refresh_total) + 1 == SECONDHAND_MARKET_TOTAL:
        invalidate_gold_ledger(gs, 'refresh_total_20')
    if int(cost) > 0 and int(eff.refresh_paid) + 1 == LONG_TERM_PAID_REFRESH:
        invalidate_gold_ledger(gs, 'refresh_paid_30')


def detect_merge_result_frame(gs: GameState) -> bool:
    """合成族失效检测(协议②;备战全扫级 + 店内会话循环级挂点)。

    任何 3★ 合成结果帧不分源(买入/消耗品/补给选卡/策略直发——持有凑
    三即合,检测点 = 合成结果帧非源动作帧):持有 3★ 名集帧差出现新增名
    ⇒ 合成发生 ⇒ 失效(星星相印 +5 是否入账由持有态决定,不在检测点
    枚举——失效保守向覆盖)。返回 True = 本帧检出合成结果。"""
    st = state_of(gs)
    front, back = deployed_rows_of(gs)
    current: dict[str, int] = {}
    for u in (*bench_units_of(gs), *front, *back):
        if u is not None and int(u.star or 1) >= 3:
            name = str(u.char_id or '')
            current[name] = current.get(name, 0) + 1
    # 基线标记键:快照是否已建立(首帧无历史可比,只建基线不判差;
    # 名空间 = 角色中文名,标记键不与之冲突)。
    first = not st.held_3star_snapshot.get('__seeded__')
    current['__seeded__'] = 1
    merged = (not first) and any(
        current.get(n, 0) > st.held_3star_snapshot.get(n, 0)
        for n in set(current) | set(st.held_3star_snapshot)
        if n != '__seeded__')
    st.held_3star_snapshot = current
    if merged:
        invalidate_gold_ledger(gs, 'merge_result')
    return merged


# ============================================================ 解拦复核(契约 A)


@dataclass(frozen=True)
class RecheckOutcome:
    """解拦复核入口段结果(shop_session §4.2)。

    ``unblock`` = 任一记录拦因解除(调用方清「本节点已处理」标记,本步
    开店);``need_gold_read`` = 金不足类记录在场 ∧ 账面失效(调用方按
    读数形态开店——路径③:锚定后复核自然继续,标记不动)。
    """

    unblock: bool
    need_gold_read: bool


def shop_unblock_recheck(gs: GameState) -> RecheckOutcome:
    """解拦复核判定函数(入口段·关门态;备战第 4 步入口唯一触发)。

    - 席满类:席位空出 = 备战可观察(``bench_free_slots`` 现读 > 0);
    - 金不足类:金位 = 账面供给(备战帧直读不可观察);账面失效时申报
      读数开门(不直接判不解拦——锚定后下帧复核);
    - 方向锁定不走本清单(锁定写入直接清标记,line_and_upgrade §1.4);
      记录拦因闭集 = {席满,金不足}(ShopOpportunity.blocked_by 值域)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_free_slots,
    )
    st = state_of(gs)
    records = session_scope.shop_opportunities_of(gs)
    if not records:
        return RecheckOutcome(False, False)
    bench_free = bench_free_slots(gs)
    unblock = False
    need_gold_read = False
    for rec in records:
        if rec.blocked_by == 'bench_full':
            if bench_free > 0:
                unblock = True
        elif rec.blocked_by == 'gold_short':
            if st.gold_ledger is None:
                need_gold_read = True
            elif int(st.gold_ledger) >= int(rec.price):
                unblock = True
    return RecheckOutcome(unblock, need_gold_read)


def shop_recheck_drop_off_face(gs: GameState) -> int:
    """解拦复核店内段(shop_session §4.2;会话入口消费)。

    验证清单记录的目标牌是否仍在当前牌面——不在即销项(刷新/消耗后已
    不在店);清单空且无其他可买 → 正常收工再关店(收工写清单以收工时
    牌面为准,本清理为会话中段的册面卫生)。返回销项数。"""
    records = session_scope.shop_opportunities_of(gs)
    if not records:
        return 0
    face_names = {c.name or '' for c in shop_payload_content_cards(gs.shop.value)}
    kept = tuple(rec for rec in records if rec.card_name in face_names)
    dropped = len(records) - len(kept)
    if dropped:
        state_of(gs).shop_opportunities = kept
        log.info('[cw][shop-recheck] 店内段验证:清单 %d 条中 %d 条目标牌'
                 '已不在当前牌面,销项', len(records), dropped)
    return dropped


__all__ = [
    'INVALIDATE_COUNTER_KEY',
    'LEVELUP_COMPANION_GOLD',
    'LONG_TERM_PAID_REFRESH',
    'REBATE_FIVE_COST_BATCH',
    'REBATE_GRANT_GOLD',
    'SECONDHAND_MARKET_TOTAL',
    'RecheckOutcome',
    'account_buy_companion_gold',
    'account_upgrade_companion_gold',
    'anchor_gold_ledger_if_new_visit',
    'apply_gold_delta',
    'detect_merge_result_frame',
    'gold_ledger_of',
    'invalidate_gold_ledger',
    'note_levelup_emission',
    'note_ore_click',
    'note_pick_frame',
    'note_refresh_counters',
    'session_gold',
    'shop_recheck_drop_off_face',
    'shop_unblock_recheck',
    'sync_gold_ledger',
]
