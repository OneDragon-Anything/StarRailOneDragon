"""备战执行器 CwScreenPrep:画面执行 / 对账接线 / 商店 obs 依赖面
(refresh 期望态依赖 obs.cw_shop_obs,留 app 合法向)。

对账职责 = 纯观察审计族(羁绊显示/商店池/合成预览/刷新,heavy 定型帧
消费);动作上报的对账归一走 apply_prep_action_logic 逻辑态直写 +
观察边界 cw_reconcile 兜底。
"""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_game_ports import (
    CwObservationSource,
    action_sink,
    observation_source,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BenchChar,
    deployed_row_slot,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    apply_prep_action_logic,
    game_state_of,
    gs_of_ctx,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import same_star_count
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.kernel.cw_overlay_registry import (
    derive_clearable,
    derive_decision,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PrepObservation,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    DeployMove,
    HoldFrame,
    LevelUp,
    OpenBookcard,
    OpenShop,
    SellBench,
    SellDeployed,
    StartBattle,
    action_key,
)
from sr_od.application.currency_war.obs.currency_war_cv import slot_occupied
from sr_od.application.currency_war.obs.cw_faction_obs import (
    compare_factions,
    read_displayed_factions,
    report_faction_reconcile,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    ensure_portrait_templates,
    read_reward_spheres,
    read_supply_boxes,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    read_tomes as cw_identity_obs_read_tomes,
)
from sr_od.application.currency_war.obs.cw_observation import (
    arbitrate_deployed_count,
    board_from_tracked,
    read_deploy_cap,
    read_deployed_count,
    read_node_sequence,
    read_phase_round,
)
from sr_od.application.currency_war.obs.cw_shop_obs import (
    RefreshExpect,
    check_shop_pool,
    compare_merge_preview,
    refresh_expect,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
    action_op_class_for,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_box_action import (
    OpenBoxOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_shop_action import (
    OpenShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_start_battle_action import (
    StartBattleOp,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.application.currency_war.prep_actions import (
    _OVERLAY_ANIM_WAIT_S,
    PrepActionExecutor,
    StopBrakeShortCircuit,
    row_area_centers,
)
from sr_od.application.currency_war.telemetry import (
    defects,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        CurrencyWarMatch,
    )

# ===== P0 清场段:环入口可一键关闭的 overlay 注册表(唯一消费方 = 本文件
# _clear_entry_overlays;单一源仍是 ``cw_overlay_registry.derive_clearable()``
# 派生桥接)=====
#: 只收「无决策语义的弹窗/面板」——星徽秘典/补给已 decision 化(关闭即丢
#: 决策内容,C1 红线),从清场集消失,改走 event_overlay bail → 0i 选卡 /
#: CwScreenSupplyNode 消化;投资环境/投资策略/选择伙伴/盛会之星/祈愿试炼
#: 等交互 overlay 同理,不进派生集。
ENTRY_OVERLAY_CLOSE: dict[str, str] = {
    spec.screen_name: spec.close_area for spec in derive_clearable()
}
#: 清场轮数上限(每轮:逐屏锚探 → 命中点关闭 → settle;无命中即出)。
ENTRY_OVERLAY_CLEAR_ROUNDS: int = 4
#: 点关闭后的画面过渡等待(秒)。
ENTRY_OVERLAY_SETTLE_S: float = 1.0



def _mark_frame_class(session, domain: str, value: str) -> None:
    """帧触发代次标注(终态契约 §B:gs 非 Field 双槽,读后即清协议)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import game_state_of
    setattr(game_state_of(session), 'frame_class_' + domain, value)


def _owned_remove(owned: list[str] | None, item: str) -> list[str] | None:
    """owned 名池摘一件(multiset 语义:同件多份只摘一份);None = 观察域
    未就绪透传(零写留观察)。"""
    if owned is None or item not in owned:
        return owned
    out = list(owned)
    out.remove(item)
    return out


def _owned_add(owned: list[str] | None, item: str) -> list[str] | None:
    """owned 名池加一件(multiset 语义);None = 观察域未就绪透传。"""
    if owned is None:
        return owned
    out = list(owned)
    out.append(item)
    return out


def _owned_replace_one(owned: list[str] | None, old: str,
                       new: str) -> list[str] | None:
    """owned 名池内单件名替换(multiset 语义:恰替换一份);None = 未就绪
    透传;old 不在池 = 原样返回(调用侧守卫)。"""
    if owned is None or old not in owned:
        return owned
    out = list(owned)
    out[out.index(old)] = new
    return out


def _next_free_bench_slot(bench_chars: list) -> int:
    """备战帧 bench_chars 占用外首个物理槽位 1-9(投影仪复制入席定位;
    生成期快照,帧内恒稳)。全占 = 9(调用侧席满守卫先行,不可达)。"""
    taken = {int(getattr(bc, 'slot', 0) or 0) for bc in bench_chars
             if bc is not None}
    for i in range(1, 10):
        if i not in taken:
            return i
    return 9


def vacancy_from_reads(cap: int | None, dep_n: int | None, cv_occ: int,
                       cached_vacancy: int) -> tuple[int, bool, bool]:
    """heavy 段 deploy_vacancy 判定(纯函数;15 号稿批 C/§4.1)。

    - 语义:vacancy = max(0, cap − **仲裁后** deployed)。deployed 双源
      (paddle X vs CV 占用)先过仲裁注册面键 ``deployed_count``
      (``arbitrate_deployed_count``,计数类取低值);此前部署放行判定消费的
      vacancy 用未仲裁 dep_n,同一量两条口径并存无对账(§1 行 21,A5 根)。
    - 返回 ``(vacancy, divergent, stale)``:divergent=仲裁判真分歧
      (取低值生效,§4.2 放行判定延迟语义的准备面载体);paddle 缺席 = CV
      单源值(计数类声明的退化方向,非 stale,消费侧板满门另有重读+分键
      契约);stale=True = cap 缺(无 cap 无法成 vacancy)→ 缓存兜底
      (**陈旧值显式申报**,B5——缓存值不再静默过放行判定)。
    """
    arb_dep, divergent = arbitrate_deployed_count(dep_n, cv_occ)
    if cap is not None and arb_dep is not None:
        return max(0, cap - arb_dep), divergent, False
    return cached_vacancy, False, True


# (prep_obs_actual_for 单条目实读构造器已随 ADR-0651 两态制废除——
#  prep_obs 覆盖点逐条目 diff 对账随 expected_state 条目表一并拆除。)


def store_plane_table(sess, seq: list[str], plane: int | None) -> bool:
    """开局帧槽序表的**每位面首帧**写入(ADR-0368)。

    write-once 守卫会使 P1 的 9 槽表整局滞留:进 P2 后 7 槽真值永不落盘 →
    nodes_of_plane / battles_left_p2 / 位面日程真值(cw_plane_table.schedule_of)
    全读错(表「在」但是错的)。按 ``plane_node_table_plane`` 锚定,位面变更即
    重写(位面内恒定语义不变,同位面多次 probe 不覆写);同时 append
    ``plane_lengths_seen``(位面长度真值序列,P3 进表即自适应)。

    返回是否写入(供调用方记日志)。纯簿记写入,无画面依赖,可单测。
    (终态契约 §A′:宿主 = gs.node_books,session 中转退役。)
    """
    if not seq or plane is None:
        return False
    from sr_od.application.currency_war.kernel.cw_game_state import game_state_of
    _nb = game_state_of(sess).node_books
    if _nb.plane_node_table_plane == plane:
        return False
    _nb.plane_node_table = list(seq)
    _nb.plane_node_table_plane = plane
    if _nb.plane_lengths_seen is None:
        _nb.plane_lengths_seen = []
    _nb.plane_lengths_seen.append(len(seq))
    return True



#: 单轮入口开商店收起探针后的落地等待(秒)。背景:战斗胜利后新回合游戏
#: 可能自动开商店(时序竞争),单轮入口收起后需等收起动画落地再观察
#(读互斥:hp/gold 关态可读;原「预收重试窗」随内环 gate 拆除)。
PRECOLLAPSE_RETRY_S: float = 1.0



# ===== 商店打开态对账(cw_shop_obs 接线;纯记账+对账,零决策行为变更)=====

#: 台账 surface/kind(商店通道;复现计数按 (surface, kind, expected) 分档)。
_SHOP_DEFECT_SURFACE = 'shop'

_SHOP_POOL_DEFECT_KIND = 'shop_pool_violation'

_SHOP_REFRESH_DEFECT_KIND = 'refresh_expect_mismatch'

_SHOP_MERGE_DEFECT_KIND = 'merge_preview_mismatch'



def _shop_pool_inputs(gs) -> tuple[list[tuple[str, int]], int]:
    """商店容器 payload → (参评牌列表, 未识别张数)(纯函数)。

    参评 = 有身份牌 ``(name, cost)``;未识别牌(name 空,SIFT miss 占位,
    cost=0)不进 check_shop_pool——空名+0 费会成 invalid_cost 假票,且
    「识别失败」已由置信度通道管辖,此处只计数随 refs 披露。
    换算单一源 = ``cw_game_state.shop_cards_to_legacy``(双 ShopCard
    类型归一波 4 立)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        shop_cards_to_legacy,
    )
    payload = gs.shop.value
    shop = shop_cards_to_legacy(shop_payload_content_cards(payload)) \
        if payload is not None else []
    cards = [(c.name, c.cost) for c in shop if getattr(c, 'name', '')]
    return cards, len(shop) - len(cards)



def _merge_preview_inputs(gs, frame_cards: list | None = None
                          ) -> tuple[dict[int, bool], dict[int, bool], int]:
    """商店容器 payload → (我方合成旗, 识别读数旗, 未识别张数)(纯函数;
    compare_merge_preview 接线的入参折算单一源)。

    槽位键 = 商店五格物理槽位下标(0 基左→右;同 read_shop_cards 顺序,
    即 cw_shop_obs.compare_merge_preview 的槽位坐标系)。
    - our:``cw_state.same_star_count`` 全场域同名同星持有 >0(合成预览语义
      单一源 = merge_mechanics.md §2.7:✦ 数 = 已持同名同星副本份数;商店牌
      恒 1★,star 兜 1)。bench/deployed 取容器席位读口(与卡池票同帧一致)。
    - det:该牌 merge_preview > 0(语义映射:0 是「无副本 ∨
      读不到」双义,映射为 False,our_suspect 祇当对账率归因,不逐票判死)。
      ✦ 是读取器派生域不入容器存储,经 ``shop_cards_to_legacy`` 的
      ``frame_cards`` 形参按同帧 raw 牌下标对齐透传(失配窗置缺省 0,
      语义申报见该函数)。
    - 未识别牌(name 空,SIFT miss)两侧都算不出 → 不进 compare,只计数
      (同 _shop_pool_inputs 口径:识别失败归置信度通道,此处不评)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_slots_of,
        deployed_slots_of,
        shop_cards_to_legacy,
    )
    our: dict[int, bool] = {}
    det: dict[int, bool] = {}
    unnamed = 0
    bench = list(bench_slots_of(gs))
    deployed = list(deployed_slots_of(gs))
    payload = gs.shop.value
    shop = shop_cards_to_legacy(shop_payload_content_cards(payload), frame_cards) \
        if payload is not None else []
    for i, c in enumerate(shop):
        if not getattr(c, 'name', ''):
            unnamed += 1
            continue
        our[i] = same_star_count(c.name, getattr(c, 'star', 1) or 1,
                                 bench, deployed) > 0
        det[i] = int(getattr(c, 'merge_preview', 0) or 0) > 0
    return our, det, unnamed



def build_refresh_expect(gold: int | None,
                         refresh_cost: int | None,
                         cards_old: list[tuple[str, int]],
                         plane: int,
                         round_num: int) -> tuple[RefreshExpect, int, int] | None:
    """刷新动作发出点 → 期望增量(纯函数;producer 契约,None 口径单一源)。

    刷价输入契约(ADR-0456):调用方传 ``cw_state.REFRESH_COST_BASE``
    基价常量——实付恒基价 2,「文本-刷新金币数」rect 是面板徽标(利息数值)
    非刷价,期望=实付,refresh_expect_mismatch 缺陷类随之归零。签名保留
    ``refresh_cost: int | None``:None 仍返回 None 跳过对账(gold 失读同理),
    供测试与未来免费 proc 建模(届时按「基价−免费抵扣」在此处计)传参;
    **禁把面板徽标读数当刷价传入**。

    挂账(producer 集成点):期望必须在**刷新动作内**构建——波前金与波前
    面板费都是单元内部现读;cw_screen_prep 持有的购买单元前后帧均为
    关店帧(F2 下金不可信、五格牌不可读),无合法评估窗。集成点 =
    ``operations/cw_op/cw_refresh_shop_action.py`` RefreshShopOp 刷新分支现读处
    (ADR-0517 迁移后消费时点 = 刷新动作的执行实现层,刷后现读帧即对账帧;
    旧「本环 heavy 帧消费」时点随 per-action heavy 契约退役归并于此);
    消费判据 = refresh_reconcile_mismatches(本文件,真值表已锁),落台账
    kind=refresh_expect_mismatch。
    """
    if gold is None or refresh_cost is None:
        return None
    return refresh_expect(gold, cards_old, refresh_cost), plane, round_num



def refresh_reconcile_mismatches(expect: RefreshExpect,
                                 gold_after_obs: int | None,
                                 cards_named: int) -> list[dict[str, str]]:
    """刷新期望 vs 实读对账判据(纯函数;口径:只硬验金差+有牌)。

    - 金腿:``gold_after_obs`` None = 失读不评(宁缺勿造);不等 = 一票
      (期望侧 gold_after 由 build_refresh_expect 保证基于波前现读,
      真值表含 0 与 None 分道)。
    - 牌腿:``cards_named`` = 实读有身份牌数;==0 = 刷新未生效形态开票;
      1-4 张**不判错**——低等级后槽未解锁是常态,槽位解锁规则未建模,
      「满格」期望无真值,计数由调用方随 refs 披露。
    """
    mism: list[dict[str, str]] = []
    if gold_after_obs is not None and gold_after_obs != expect.gold_after:
        mism.append({'domain': 'gold', 'slot': '-',
                     'expected': str(expect.gold_after),
                     'observed': str(gold_after_obs)})
    if cards_named <= 0:
        mism.append({'domain': 'cards', 'slot': '-',
                     'expected': '>=1', 'observed': '0'})
    return mism



#: 未识别节点图标采集防抖(idx → 上次采集时刻)。module-level:CwScreenPrep 每备战环重建
#: (cw_loop loop 内构造),实例属性跨环零存活 → 300s 窗
#: 失效(同 idx 每环各采一张,内容哈希对帧微变不设防)。
_NODE_ICON_SHOT_TS: dict[int, float] = {}



def faction_display_ok_debug_line(row_count: int, ocr_skip_count: int,
                                  suspects: list[str],
                                  computed_missing_count: int) -> str:
    """羁绊显示对账 ok 分支的 debug 行(纯函数,零决策)。

    疑截断行名非空时随行附列——纯计数留不下「哪几行被疑」,mismatch=0
    的稳定态行名不可考(复盘 g_20260903_232823 §4:恒 4 行疑截断无档)。
    只在非空时附带,空列表保持旧行形(计数后无括号段)。
    """
    return (f'[cw][director] faction_display reconcile: '
            f'ok({row_count}行) '
            f'ocr_skip={ocr_skip_count} '
            f'trunc_suspect={len(suspects)}'
            + (f'({",".join(suspects)})' if suspects else '')
            + f' computed_missing={computed_missing_count}')


class PrepLiveObservationAdapter:
    """实机适配器①(观察端口;统一观察架构 §2.3 识别链封口,试点步骤 1)。

    内部复用现役识别链(``CwScreenPrep._observe`` heavy 入口观察:observe_full
    + read_game_state 漏斗,含端口分流与 GameState 观察写端[P2-1/P3-10 门])
    ——识别机制(OCR/CV/SIFT/截图)不出端口(§2.1 契约三则)。sim 实现 =
    步骤 2 辖域(观察端口协议的引擎真值映射,§2.4),本批不建。
    """

    def observe(self, op: CwScreenPrep) -> PrepObservation:
        return op._observe(heavy=True)


class PrepLiveActionAdapter:
    """实机适配器②(动作端口;统一观察架构 §6.2 点击链封口,试点步骤 1)。

    内部复用现役点击链(``CwScreenPrep._act_execute_default``:OpenShop 流程
    层编排 + PrepActionExecutor 机械执行),机械执行**无返回**(
    发出即职责完成,端口回执 ``(progressed, detail)`` 退役;落地判定完全
    归观察侧 reconcile,§6.2/§6.5-1)。sim 实现 = 步骤 2 辖域
    (引擎动作应用,§6.3),本批不建。
    """

    def execute(self, op: CwScreenPrep, action: CwAction) -> None:
        op._act_execute_default(action)


class CwScreenPrep(CwScreenOpBase):
    """备战决策环:观察驱动单步决策,替代 CwScreenPrep 备战单轮 固定序列(P1)。

    单「决策环」节点 + 内部 while;环级预算 MAX_STEPS(步数)与 STALL_LIMIT(零进展)
    兜底强制出战(F5);ping-pong 由外环 MAX_ITER=2000 承担(勿引 node_max_retry —— round_wait
    不消耗 node 重试预算,operation.py:453-461 仅 RETRY 递增;strategy/03 §7)。

    统一观察架构试点(§9.2 迁移步骤 1,实机侧):本类是第一个基类
    (CwScreenOpBase)子类——五段生命周期方法见文末「五段生命周期」段;
    装配点(cw_game_ports)在场时 run() 经五段驱动,缺省 None = 生产直连
    旧路径(run() 原序列),试点等价门通过前生产行为零变化(§9.1)。
    """

    # 环级预算(§7 环级:步数>60 → 强制出战兜底;实跑校准 §10)
    MAX_STEPS: ClassVar[int] = 60
    STALL_LIMIT: ClassVar[int] = 5
    # 单动作访问动作数上限(ADR-0517:防御上界——决策循环不收敛 = 逻辑态或
    # 策略 bug,到顶交回外循环由 stall 防线接管,不静默续跑)
    VISIT_ACTION_CAP: ClassVar[int] = 16

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-备战决策环')
        # 交回契约事实(迭代 changes/2026-09-16-prep-visit-op design §2.1):
        # 出战意图经统一执行器发射成功即置位;战斗窗置位策略归外循环
        # 既有口径(ADR-0250),本事实为通道载体与观测面。单轮 op 每轮次
        # 重建,实例属性天然无跨轮残留。
        self.launch_fired: bool = False
        self._executor: PrepActionExecutor | None = None
        self._steps: int = 0
        self._stall: int = 0
        # 最近一次动作执行的机械摘要(登记件 detail 供给;端口无
        # 回执后由 _act_execute_default 写入,on_outcome 触发时消费)。
        self._last_mech_detail: str = ''
        self._bench_pts = []                        # screen_info 槽位中心(首步惰性读)
        # light 步沿用的 heavy 缓存(观察分层)。容器化段 2:state 缓存槽
        # 随黑板槽退役收缩为视觉域——bench/deployed/vacancy/gold_trusted
        # 四件 + 商店牌读取器域载荷(✦ merge_preview 信号,不入容器存储,
        # 供合成预览对账 det 侧同帧对齐;structurally 读取器域非局内事实)。
        self._cached_shop_cards: list = []
        self._cached_bench: list[BenchChar] = []
        self._cached_deployed: list[BenchChar] = []
        self._cached_vacancy: int = 0
        self._cached_gold_trusted: bool = False
        # 装备域三路 light 沿用缓存(P4 观察接线;None = 识别域未就绪)
        self._cached_owned_equips: list | None = None
        self._cached_occupied_equips: dict | None = None
        self._cached_back_layout_slots: int | None = None
        # 适配器位缺省装配(统一观察架构 §9.2 步骤 1):实机适配器 = 现役
        # 识别链/点击链封口(不新建读屏/点击实现);注入替位 = 构造参数/
        # 直接赋值(sim 适配器 = 步骤 2)。__new__ 绕道构造的测试桩无此
        # 属性 → getattr 兜底直连现役链(与旧路径同语义)。
        self._observation_adapter = PrepLiveObservationAdapter()
        self._action_adapter = PrepLiveActionAdapter()
        # on_outcome 落地登记注册表(架构设计 §6.4;单一发射口,发射即触发
        # ——最严读法:两 fire 口合并,落地回执门退役):本 op 级
        # 登记件原两件 = 经验期望账本推进(LevelUp/OpenShop 两通道),随
        # 期望账拆除退役——「未落地不计数」防线
        # 由逻辑态直写(apply_prep_action_logic LevelUp 分支)与观察覆盖
        # 承接。执行器内
        # 登记件(刷新计数组免费闸 record_refresh_execution、免战牌
        # consume_use,现役接线点 = cw_op_buy_cards 执行落地门/kernel
        # apply_op_effect 上报路径)**不随本批收编**:该执行链为双路径共链,迁移即
        # 生产行为变化——收编挂账至试点等价门通过后的执行器批(§6.4-R-J
        # 非登记职责留守执行器;免费闸/随点击置位等 §6.5 六条语义以现役
        # 位置逐字保绿)。

    # ===== 观察(F2:只由现成 reader 产出)=====

    def _observe_from_ports(self, src: CwObservationSource) -> PrepObservation:
        """观察源端口路径的观察装配。

        读半部(轻字段扫读 + observe_full 重观察)整体换端口真值直出;
        装配半部(单写者 session 写点)与读屏路径同语义:last_node_type
        写点/期望态对账/缓存/黑板帧——容器喂入 = 观察源实现方契约。
        (迁移批 3.2 切片4:``bundle.state`` 切容器形态,帧变量与 bench
        黑板播种随帧表示退役删除;节点类型/视觉域缓存装配改容器读口。)
        缺席申报:cap×paddle 双源 vacancy 仲裁在端口路径结构性不跑——
        假环境 vacancy 单一真值(cap−deployed),双源分歧问题不存在;
        坐标/视觉域字段(spheres/boxes/tomes/overlay 检测)恒空,消费方
        按「识别缺陷面结构性为零」申报(方案 §4-6)分流。
        """
        bundle = src.observe_prep(self.ctx, 'prep_clean')
        obs = bundle.prep if bundle.prep is not None else PrepObservation()
        session = self._session()
        if session is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of as _pobs_gs_of,
            )
            from sr_od.application.currency_war.kernel.cw_game_state import (
                shop_cards_to_legacy as _pobs_cards_legacy,
            )
            _pobs_gs = _pobs_gs_of(session)
            # (session.last_node_type 写点已随终态契约 §A′ 退役:node 单一源
            #  = gs 推导 node_kind_of,消费点已直读,本写点无读者。)
            # (last_state 写点已随链退役批删除:遗留读者与执行侧装配源
            #  全切容器单例,端口路径容器喂入 = 观察源实现方契约;原
            #  「写 last_state 前过 gated_hp」门随写点退役,gated_hp 门
            #  现役在册位 = prep 装配消费位(读屏路径同)。)
            # light 沿用缓存更新(视觉域载荷;MED-1 同读屏路径)。raw 牌
            # 缓存域:容器 payload 经 kernel 映射单一源转 legacy 读面
            #(假环境 merge_preview 读取器域结构性为零,§4-6 同申报)。
            _pobs_payload = _pobs_gs.shop.value
            self._cached_shop_cards = (
                _pobs_cards_legacy(shop_payload_content_cards(_pobs_payload))
                if _pobs_payload is not None else [])
            self._cached_bench = list(obs.bench_chars)
            self._cached_deployed = list(obs.deployed_chars)
            self._cached_vacancy = obs.deploy_vacancy
            self._cached_gold_trusted = obs.state_gold_trusted
        # 黑板写路径(W971 §2,P2):写者白名单 = 本装配点(与读屏路径同点)
        if session is not None:
            game_state_of(session).prep_obs = obs
        return obs

    def _observe(self, heavy: bool, screen: MatLike | None = None) -> PrepObservation:
        """组装备战观察(ADR-0517 迁移后:heavy = 画面 op 入口单次——期望态
        重建的唯一读屏点,即对账;调用点 = 单轮入口 / OpenShop(read_only)
        开态 gold 真值刷新)。旧「每个执行过的游戏动作后必调 heavy」契约已
        随单动作循环退役:逐动作零读屏,期望态由 ``_project_prep_obs`` 纯计算
        推进,动作后首读的光标 parking 职责随之迁移(入口观察 park 一次;
        执行侧读数性通道——卖出回金遥测等——的局部 park 由动作实现层自理)。
        light 分支保留为兼容形态(现生产无调用方)。

        screen 传入时(gate 末帧)复用该帧不重截——gate 稳定帧的全图 OCR 已
        按 id(image) 缓存,本方法所有 crop_first=False 读取(id_mark 判定/
        observe_full)全部缓存命中,heavy 观察的 OCR 成本归零;且观察的就是
        「已验证稳定」的那一帧(gate 语义),而非稳定后又隔一拍的帧。

        观察源端口改道:端口在场(假环境)时
        读半部整体换端口真值直出(见 :meth:`_observe_from_ports`),缺省
        None = 生产真实读屏,本方法体逐位不变。
        """
        _src = observation_source()
        if _src is not None:
            return self._observe_from_ports(_src)
        if heavy:
            self.park_cursor()
        screen = screen if screen is not None else self.screenshot()
        obs = PrepObservation()
        if not self._bench_pts:
            self._bench_pts = row_area_centers(self.ctx, '备战栏')
        # 轻:球/箱/典籍/overlay/占用(每步现读)
        # 球读带两帧持存交叉验证(奖励域防幻检批):瞬态特效假圆下一帧
        # 即消失,不采信;本帧原始读数(含黑名单过滤)存为下帧 prev
        #(实例属性跨步存活;CwScreenPrep 每备战环重建 → 跨环不残留,
        # 语义 = 环内连续帧)。
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            filter_persistent_spheres,
        )
        _spheres_raw = read_reward_spheres(self.ctx, screen)
        _prev_spheres = getattr(self, '_prev_spheres_raw', None)
        obs.spheres = (filter_persistent_spheres(_spheres_raw, _prev_spheres)
                       if _prev_spheres else _spheres_raw)
        self._prev_spheres_raw = _spheres_raw
        obs.boxes = read_supply_boxes(self.ctx, screen)
        obs.tomes = cw_identity_obs_read_tomes(self.ctx, screen)
        obs.shop_open = self.round_by_find_area(
            screen, SHOP_SCREEN_NAME, '按钮-收起', crop_first=False).is_success
        # (box_overlay_open 采集已退役删除:唯一决策消费面(entry 武装箱臂)
        #  随 R7 终结化删除,武装箱选择 = cw_loop 画面分发(0f2 行)辖,
        #  观察字段零消费即删,R1 退役=删。)
        # 事件 overlay(挡操作:deploy/equip 全灭根因,live 2026-08-15):检测到即由环 bail 交外环。
        # 扫描集单一源 = kernel/cw_overlay_registry 的 decision 派生段(B 面切换,
        # 零成员变化):锚 = spec.anchor_area,tag = spec.bail_tag,消费方拼
        # '事件overlay:' 前缀。命中即短路;break 语义与手写清单时代一致。
        # 遍历序 = 注册表声明序(与旧手写序不同但行为等价):各 decision overlay
        # 是全屏顶层弹窗,单帧锚互斥(历史帧组 ≤1 命中实证),先命中哪个即哪个
        # overlay 在场;且任一 decision overlay 在场的外层行为相同(即刻 bail 交
        # 外环 handler),序只影响多命中假想帧的 tag 归属。
        for _spec in derive_decision():
            if self.round_by_find_area(
                    screen, _spec.screen_name, _spec.anchor_area,
                    crop_first=False).is_success:
                obs.event_overlay = _spec.bail_tag
                break
        occupied = [i + 1 for i, p in enumerate(self._bench_pts)
                    if slot_occupied(screen, int(p.x), int(p.y))]
        obs.free_bench_slots = max(0, len(self._bench_pts) - len(occupied))
        front_pts = row_area_centers(self.ctx, '前排')
        back_pts = row_area_centers(self.ctx, '后排')
        obs.front_size = len(front_pts)
        # (obs.back_size 写点随死字段退役删除(波 5b,终端消费者零——决策链
        #  后排容量读容器 back_capacity_of);back_occupied 仍按后排点现读。)
        obs.front_occupied = {i + 1 for i, p in enumerate(front_pts)
                              if slot_occupied(screen, int(p.x), int(p.y))}
        obs.back_occupied = {i + 1 for i, p in enumerate(back_pts)
                             if slot_occupied(screen, int(p.x), int(p.y))}
        # 重:身份/星级/cap(环入口 + 结构变化 = 每个执行过的游戏动作)
        if heavy:
            # 可重定位读取(身份/gold==0 重读/substate)进组装层
            # 单一源(observe_full);director 保留副作用编排(session 写/审计/
            # 缓存——单写者原则)。
            from sr_od.application.currency_war.obs.cw_observe_full import (
                observe_full,
            )
            _of = observe_full(self.ctx, screen, tier='heavy',
                               source='director', op=self,
                               shop_open=obs.shop_open,   # F2 门
                               session=self._session())   # P4R4:SIFT 三层漏斗(session 优先匹配)
            templates = ensure_portrait_templates(self.ctx)   # 复用单一源(路径+缓存)
            if templates is not None:
                obs.bench_chars = _of.get('bench_chars') or []
                obs.deployed_chars = _of.get('deployed_chars') or []
                self._reconcile_tracking(obs.bench_chars, obs.deployed_chars, screen)
            else:
                obs.bench_chars = list(self._cached_bench)
                obs.deployed_chars = list(self._cached_deployed)
            # 装备域三路回填(P4 观察接线):采集已归位 observe_full
            # heavy 装配层,本点只做产物拷贝(单写者原则);None = 识别域
            # 未就绪,照 None 落帧(消费方按 fail/保守通道处理,禁造空值)。
            obs.owned_equips = _of.get('owned_equips')
            obs.occupied_equips = _of.get('occupied_equips')
            obs.back_layout_slots = _of.get('back_layout_slots')
            _st = _of.get('read_receipt')
            session = self._session()
            # (session.last_node_type 关态帧写点已随终态契约 §A′ 退役:
            #  node 单一源 = gs 推导,原「商店开态遮蔽恒 None 致 boss 判定
            #  死码」的病灶随锚退役一并消亡。)
            # PrepObservation 消费切换转适配器(迁移批次二,设计 §8.7):
            # 决策读自 GameState 容器单例(read_game_state 漏斗直写;
            # 旧 last_state 装配源契约随装配源迁移与链退役批终结,
            # ADR-0530 换源核销;obs.state 视图槽已随黑板槽退役消亡)。
            if session is not None:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    ChannelSig,
                    bench_view_from_obs,
                )
                from sr_od.application.currency_war.kernel.cw_reconcile import (
                    is_merge_effect_window,
                )
                _gs_obs = gs_of_ctx(getattr(self, 'ctx', None), session)
                # R1 渠道签名(§3.2.1):备战帧观察写入 = 渠道①,actor=本 op、
                # screen=备战建档名、quality=真读标记(承接现役真读/兜底可分
                # 语义)。
                _prep_sig = ChannelSig(family='obs', actor='CwScreenPrep',
                                       screen='货币战争-备战', mode='read',
                                       quality={'bench': 'real_read'})
                # 备战席观察写端(§3.2.5 观察写端=本屏):SIFT 身份+星级
                # (read_star 链)已读,零新增 OCR。P2-1(批次二落地审):
                # 空集 = 失读非全空(overlay 残留/动画帧/识别退化)——
                # bench_view_from_obs 返 None 时走 carried(§2.2 处置①;
                # 宁缺勿造,先例=商店空牌面观察漏斗 shop_cards 分支),
                # 禁把「9 槽全空」当 observation 入记录
                # (席空数派生误报 free=9 污染席满决策)。
                _bench_obs = bench_view_from_obs(obs.bench_chars)
                if _bench_obs is not None:
                    # 合成特效窗态门(P3-10 批次二复审,两态制 ADR-0651 等价
                    # 形态):星爆动画窗(≥2 帧)内 read_star 读旧星(reconcile_
                    # tracking 防抖同口径,读数物理不可信)——本帧**不写观察**
                    # (保 bench 的 logic 逻辑态值,§2.2 失读处置①的同族语义),
                    # 下帧干净帧实读覆盖:逻辑态与实读一致 = 零缺陷行;失配 =
                    # 逻辑态 bug 留证。原「挂起预期顺延核对」的防噪声语义由此
                    # 承接(原核对半随 expected 机制废除)。
                    if is_merge_effect_window(screen):
                        log.info('[cw][gs] 合成特效窗内读数不可信 → 本帧观察'
                                 '不写(保 logic 逻辑态值,下帧干净帧覆盖)')
                    else:
                        _gs_obs.observe(_gs_obs.bench, _bench_obs, sig=_prep_sig)
                else:
                    _gs_obs.carry(_gs_obs.bench,
                                  frame=(f'p{_st.plane}-r{_st.round_num}'
                                         if _st is not None else ''),
                                  sig=ChannelSig(
                                      family='obs', actor='CwScreenPrep',
                                      screen='货币战争-备战', mode='carried'))
                # 上场席位观察写端(与 bench 写端同环同纪律):
                # deployed_rows_from_obs 空集守卫(P2-1 同款:空集 = 失读非
                # 全空 → carry,禁「全场无人」假观察);特效窗门同 bench
                # (star 读数物理不可信);front_row/back_row 分排观察照写,
                # 换算归 kernel 映射层(deployed_rows_from_obs)。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    deployed_rows_from_obs,
                )
                _dep_rows = deployed_rows_from_obs(obs.deployed_chars)
                _dep_carried_sig = ChannelSig(
                    family='obs', actor='CwScreenPrep',
                    screen='货币战争-备战', mode='carried')
                if _dep_rows is not None:
                    if is_merge_effect_window(screen):
                        # 与 bench 特效窗门同语义:窗内不写(保 logic 逻辑态值,
                        # 下帧干净帧实读覆盖),不落 carried 假新鲜度。
                        pass
                    else:
                        _gs_obs.observe(_gs_obs.front_row, _dep_rows[0],
                                        sig=_prep_sig)
                        _gs_obs.observe(_gs_obs.back_row, _dep_rows[1],
                                        sig=_prep_sig)
                else:
                    _dep_frame = (f'p{_st.plane}-r{_st.round_num}'
                                  if _st is not None else '')
                    _gs_obs.carry(_gs_obs.front_row,
                                  frame=_dep_frame,
                                  sig=_dep_carried_sig)
                    _gs_obs.carry(_gs_obs.back_row,
                                  frame=_dep_frame,
                                  sig=_dep_carried_sig)
                # 备战帧现行链写端(链观察落地批):slots 由 observe_full
                # heavy 回传(原弃槽点改造),写容器在 director 侧(单写者
                # 原则);逐格映射/写门/基线回填语义见函数 docstring。
                _write_prep_node_chain(session, _of.get('node_slots'),
                                       _prep_sig)
                # 装备库存观察写端(P4 观察接线;W5 §2.2):owned
                # 采集已归位本入口观察链(observe_full heavy),写端随迁本
                # 装配点——原写点 = prep_actions._build_equip_wear_plan 两
                # 分支,随其三路现读退役消失。全量名单入记录(W209g 断点②
                # 采集层无权丢数据,工具件照录);失读(None)= 识别域未就绪
                # 不写保现值(宁缺勿造,同 bench 空集守卫族;装备区读不受
                # 合成特效窗影响,无需 is_merge_effect_window 门)。
                if obs.owned_equips is not None:
                    # (终态契约 §B:session.last_owned_equips 镜像行随重复
                    #  账退役删——gs.equips 观察写端即单一源,商店线权重/
                    #  flow 打分/库存 ±1 腿全部读容器。)
                    _gs_obs.observe(_gs_obs.equips, list(obs.owned_equips),
                                    sig=_prep_sig)
                # 溢出告警观察写端(2026-09-15 实机建档 prep.md 告警/溢出节):横幅 = 游戏侧权威信号(出战被游戏忽略的
                # 处理门,策略消费 = mandate 溢出门强收窄);溢出位 SIFT =
                # 入位对象身份旁路(SellBench 溢出腿;缺读 '' = 未识别,
                # 腿降级槽留空等下帧)。两读独立;横幅在场 = 唯一门语义,
                # 身份只作 tracked 闭合不作门。
                _ov_hit = self.round_by_find_area(
                    screen, '货币战争-备战', '告警-备战席已满',
                    crop_first=False).is_success
                _ov_id = ''
                if _ov_hit:
                    # ensure_portrait_templates 用模块级导入(:87;函数内
                    # 重绑定会遮蔽 _observe 前段 687 行的引用,F823 实证)。
                    from sr_od.application.currency_war.kernel.cw_obs_core import (
                        _area_rect,
                    )
                    from sr_od.application.currency_war.obs.cw_identity_obs import (
                        identify_slots,
                    )
                    _ov_rect = _area_rect(self.ctx, '区域-溢出角色',
                                          '货币战争-备战')
                    _ov_tmpl = ensure_portrait_templates(self.ctx)
                    if _ov_rect is not None and _ov_tmpl is not None:
                        _ov_chars = identify_slots(screen, _ov_tmpl,
                                                   [(1, _ov_rect)], '')
                        if _ov_chars:
                            _ov_id = _ov_chars[0].char_id or ''
                _gs_obs.observe(_gs_obs.overflow_warning, _ov_hit,
                                sig=_prep_sig)
                _gs_obs.observe(_gs_obs.overflow_card, _ov_id,
                                sig=_prep_sig)
            # (obs.state 视图合成随黑板槽退役消亡——容器化段 2 消点:
            #  game_state_view 全仓最后活调用清零,决策读自容器单例;
            #  cw_bs_view 文件本体删除归波 5,设计件 §2.3/§2.6。)
            obs.state_gold_trusted = obs.shop_open   # F2:gold 仅 shop 开态可信(关态读空)
            if not obs.state_gold_trusted:
                log.debug('[cw][director] heavy 读 state 于 shop 关态 → gold 不可信')
            # (last_state 写点已随链退役批删除:写点原带「写前过 gated_hp」
            #  hp 双源收口门,门随写点退役——gated_hp 门现役在册位 = prep
            #  装配消费位;hp 局内宿主 = 容器(观察漏斗质量门写入),期望态
            #  覆盖点·备战观察块已随 ADR-0651 两态制废除,tracked/gold
            #  实读写入链照常——观察赢。)
            # substate 消费:observe_full 的可读性
            # 标注落 PrepObservation(下游对账/日志可判;轻步
            # 沿用缓存,同 _cached_state 语义)。
            obs.substate = _of.get('substate') or {}
            # ⚠ 以下 cap/双源审计用 heavy 段
            # 开头的旧 screen,而回执可能来自 gold 重读的 0.3-0.9s
            # 后异帧——跨帧对拍在轮转动画窗内可假分歧(低概率,
            # 留证非阻塞);重读仅在 shop 开态,窗口缩小。
            cap = read_deploy_cap(self.ctx, screen)
            _audit_level = _st.level if _st is not None else None
            # 观察冲突审计 #15(2026-08-16;⚠ 2026-08-22 两段反转,ADR-0220+用户点题;
            # 2026-08-23 ADR-0281 再适配):财富宝钻官方效果「拥有即可使团队规模
            # 上限+1,无论是否被角色穿戴」可叠加(局38 r2 实证 cap5/lv3=两宝钻)。
            # 布局与 cap 无关(ADR-0281:level 驱动)后本检查只剩:
            # - cap < level → 不可能(读错/毒化)→ 留证(三源网 M38 天敌);
            # - cap ≥ level → 合法(cap>level=宝钻叠加,debug 记宝钻数)。
            if cap is not None and _audit_level is not None \
                    and cap < _audit_level:
                from sr_od.application.currency_war.kernel.cw_observe import (
                    obs_conflict,
                )
                obs_conflict('deploy_cap_vs_level', _audit_level, cap, screen,
                             verdict=('留证-cap<level不可能(cap或level读错;'
                                      '处理:看截图读「区域-部署数」X/Y 原文核 X>Y guard '
                                      '是否该拒,level 查 XP 反推是否一致;'
                                      '确认 reader 缺陷则修 read_deploy_cap/level 守卫;'
                                      '单次按 OCR 噪声忽略,复现 ≥3 次才排期)'),
                             source='paddle_cap')
            elif cap is not None and _audit_level is not None:
                # ADR-0385:cap>level(宝钻/钻石叠加)不只
                # 是经济信息——口述
                # 公式「后台格数 = 6+(cap−level)」使 cap 差直接驱动布局选档
                # (cw_back_layout.select_back_layout,含 7 格未建档留证)。
                # cap==level 是常态(无宝钻),别打
                # "宝钻×0"误导判读;仅真叠加(cap>level)才记
                if cap > _audit_level:
                    log.debug('[cw][obs] cap=%d(宝钻×%d 叠加,合法;后排扩展 +%d 格)',
                              cap, cap - _audit_level, cap - _audit_level)
            dep_n = read_deployed_count(self.ctx, screen)
            _cv_occ = len(obs.front_occupied) + len(obs.back_occupied)
            # vacancy 消费仲裁值(15 号稿批 C/§4.1,A5 根:同一量两条口径并存
            # 无对账——部署放行判定消费的 vacancy 此前用未仲裁 dep_n):判定收在
            # 纯函数 :func:`vacancy_from_reads`(判据见其 docstring),
            # divergent/stale 位随 obs 传播(§4.2 放行判定延迟语义的准备面载体)。
            obs.deploy_vacancy, obs.deploy_divergent, obs.deploy_stale = \
                vacancy_from_reads(cap, dep_n, _cv_occ, self._cached_vacancy)
            # deployed 总数双源对拍(同帧全齐):paddle X(读 deployed_count)
            # vs CV 占用(front+back)。
            # ⚠️ board 的 X 是「该阵营在场人数」非「角色数」——
            # 一个角色贡献多阵营(藿藿=仙舟+治疗,4 人可贡献 11 阵营次),
            # board_sum 系统性 ≥ 部署数,board 根本给不出角色数 →
            # **移出对拍**,对拍保持双源(paddle X vs CV 占用)。
            if dep_n is not None:
                # 对拍裁决迁仲裁注册面(15 号稿批 A;注册键 deployed_count,
                # 计数类取低值+spread>1 告警带):divergent 判定经注册面,
                # 留证行/分键仍在此处按键发射——行数/field/新旧值/verdict
                # 文本逐字节不变(零行为验收对拍)。
                from sr_od.application.currency_war.obs.cw_arbitration import (
                    arbitrate,
                )
                _value, _verdict, _divergent = arbitrate(
                    'deployed_count',
                    {'paddle_x': dep_n, 'cv_occupied': _cv_occ})
                if _divergent:
                    from sr_od.application.currency_war.kernel.cw_observe import (
                        obs_conflict,
                    )
                    obs_conflict('deployed_count_2src',
                                 {'paddle_x': dep_n, 'cv_occupied': _cv_occ},
                                 'spread>1', screen,
                                 verdict=('留证-双源分歧(处理:看截图数前排+后排占用实数,'
                                          '与 paddle X 对拍;哪源对修哪源——paddle 对→CV '
                                          '阈值/遮挡误漏,CV 对→X/Y 拆框;'
                                          '消费侧板满门已按取低值仲裁'
                                          '(cw_observation.arbitrate_deployed_count);'
                                          '单次按噪声忽略,同局 ≥3 次排期修)'),
                                 source='director_heavy')
                    # 不一致率分键(防静默;裁决事件层,与上方证据层行分键)
                    try:
                        from sr_od.application.currency_war.telemetry.defects import (
                            record_deployed_count_2src_divergence,
                        )
                        record_deployed_count_2src_divergence(
                            dep_n, _cv_occ, 'director_heavy')
                    except Exception:   # noqa: BLE001  遥测 best-effort
                        pass
            # 更新 light 沿用缓存(视觉域载荷;trusted 位随帧缓存,MED-1
            # —— light 步不重判 shop 态,缓存生成时的可信度就是它的可信度)
            self._cached_shop_cards = list(_st.shop if _st is not None else [])
            self._cached_bench = list(obs.bench_chars)
            self._cached_deployed = list(obs.deployed_chars)
            self._cached_vacancy = obs.deploy_vacancy
            self._cached_gold_trusted = obs.state_gold_trusted
            # 装备域三路缓存(P4 接线):None(识别域未就绪)照缓存,None
            # 沿用同族——light 步拿到的仍是上次 heavy 的识别域状态。
            self._cached_owned_equips = obs.owned_equips
            self._cached_occupied_equips = obs.occupied_equips
            self._cached_back_layout_slots = obs.back_layout_slots
        else:
            # light:heavy 字段沿用缓存(上次真读值;不恒默认防永动机)。
            # state 缓存随黑板槽退役消亡(容器化段 2):视觉域四件照旧沿用。
            obs.state_gold_trusted = self._cached_gold_trusted   # MED-1:trusted 位随缓存帧
            obs.bench_chars = list(self._cached_bench)
            obs.deployed_chars = list(self._cached_deployed)
            obs.deploy_vacancy = self._cached_vacancy
            # 装备域三路沿用(同分层语义;含 None = 上次 heavy 也未就绪)。
            obs.owned_equips = self._cached_owned_equips
            obs.occupied_equips = self._cached_occupied_equips
            obs.back_layout_slots = self._cached_back_layout_slots
        # 黑板写路径(W971 §2,P2):备战观察结果直写 session(写者白名单 =
        # 本装配点;读者 = decide_prep_screen)。离线契约:无 match(局外
        # 单跑/mock)不写。帧对象原样入 session(实现决策:容器形态,
        # 逐字段扇出归 P3,见 cw_strategy_session.prep_obs_frame 注)。
        _sess = self._session()
        if _sess is not None:
            game_state_of(_sess).prep_obs = obs
        return obs

    def _project_prep_obs(self, action: CwAction,
                          obs: PrepObservation) -> PrepObservation:
        """执行后期望态逻辑态直写(ADR-0517 决策 7/10;纯计算零读屏)。

        R9 逻辑态全覆盖(规则全集正本 = ``game_state/action-logic-state.md``):
        词表逐动作有逻辑态计算,
        「未建模 → 返回 None 保守回退交回外循环」分支**删除**;词表外
        类型 = 分派漏斗被绕过,AssertionError 响亮暴露(注册表同款纪律)。

        逐动作分支(确定性 UI 消耗/腾席/容器域直写;随机面一律观察收口):
        - OpenTome:开一件即腾席,tomes 按 ``action.slot`` 摘对应槽的件
          (slot=None = 首件,与发射形态对齐);
        - OpenBookcard:开卡即腾席(书册卡无独立载荷列表字段,占席事实只在
          ``free_bench_slots`` 现读口径 → 摘件 = 腾席 +1,与 heavy 现读
          ``slot_occupied`` 扫描同式;容器零写同箱/典籍,R10);
        - ClickSpheres:按载荷坐标**精确摘球**(R4 改形;原保守清空退役
          ——载荷即点击列,被点的球从 spheres 摘除,坐标匹配);
        - SellBench:该物理槽位件离席(bench_chars 摘除 +
          free_bench_slots+1;溢出腿落地时改为入位卡回占该槽、free 不变
          ——黑板帧镜像,与容器腿/执行账吸收同帧同源;规则正本 =
          game_state/action-logic-state.md §2.4 溢出条件行)+
          容器域逻辑态直写(gold 回金 + bench 摘槽,
          kernel 写口 ``apply_prep_action_logic`` 单一源);
        - DeployMove(批 2a 补齐,§3.1):bench 摘件 + deployed 落件
          (排/槽号信息位重写)+ 占用集推进 + 容器域(bench/front_row/
          back_row/board 增量);
        - SellDeployed(批 2a 补齐,§3.2):deployed 摘件 + 容器域
          (front_row/back_row/board 重算 + gold 回金);
        - LevelUp(批 2a 补齐,定案④):视觉帧零变,容器域 xp/level 推进
          (gold 中间态不写,金腿 = 执行缝金差);
        - WearEquip:``owned_equips`` 摘件(视觉域,与 OpenBox/OpenTome
          同形;容器 equips 域留观察覆盖——域集封闭申报);
        - 工具原子(R8):按 ``EQUIP_WRITE_SIDES`` 申报逐类直写——
          冶金炉 = 工具 −1 + 装备腿目标件消失(变异产物 = 随机面观察
          收口)/角色腿穿戴域 → 库存域全量迁移;特权赋予卡 = 工具 −1 +
          库存腿确定变换(名替换,桥 = ``transform_equip_to_privilege``)
          /拖角色腿只写工具 −1(哪件被选 = 随机面);拆装扳手 = 穿戴域
          全量回库存 + 工具 −1;精密扳手同款不消耗;投影仪 = 备战席
          创造 1 星复制(席满拒落零写)+ 工具 −1;好运令牌 = 工具 −1
          (选件随机面归观察);
        - OpenBox:**终结化**(R7)后不经本口——结束判定先行交回外循环
          (武装箱选择画面 op 分发),分支随终结化作废删除。

        保真边界:gold 可信位(``state_gold_trusted``)不随逻辑态翻转——
        直写金是账面值,可信位语义(heavy 真读)保持不变。
        """
        import dataclasses

        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            empty_deploy_slots,
        )
        from sr_od.application.currency_war.kernel.cw_vocab import (
            ClickSpheres,
            FurnaceUse,
            LuckyTokenUse,
            OpenBookcard,
            OpenTome,
            PerfectProjectorUse,
            PrecisionWrenchUse,
            PrivilegeCardUse,
            StaffProjectorUse,
            WearEquip,
            WrenchUse,
        )
        if isinstance(action, OpenTome):
            _tomes = list(getattr(obs, 'tomes', None) or [])
            if _tomes:
                _drop = action.slot if action.slot is not None else _tomes[0][0]
                _tomes = [t for t in _tomes if t[0] != _drop]
            return dataclasses.replace(obs, tomes=_tomes)
        if isinstance(action, OpenBookcard):
            # 开卡即腾席(R10 视觉域;发射位 = 环入口清场段交回,本分支为
            # 词表发射形态的完整逻辑态面,升 director 门控时与 OpenBox
            # 终结化同构补 visit 终结分支)
            return dataclasses.replace(
                obs, free_bench_slots=(getattr(obs, 'free_bench_slots', 0) or 0) + 1)
        if isinstance(action, ClickSpheres):
            _pts = {(int(x), int(y)) for x, y in action.points}
            _spheres = [s for s in (getattr(obs, 'spheres', None) or [])
                        if (int(s[1].x), int(s[1].y)) not in _pts]
            return dataclasses.replace(obs, spheres=_spheres)
        if isinstance(action, SellBench):
            _sess = self._session()
            _gs_sell = gs_of_ctx(getattr(self, 'ctx', None), _sess)
            # 溢出腿镜像读数(先读后写):溢出卡身份/旗标在本写口内被消费
            # 清空,镜像判定须取写前值;落地判定 = 写后旗标已清(本调用内
            # 唯一清空者 = 溢出腿,陈旧提案零写分支不清 → 镜像不误发)。
            _ov_id_pre = str(_gs_sell.overflow_card.value or '')
            _ov_warn_pre = bool(_gs_sell.overflow_warning.value)
            # 容器域逻辑态直写(容器化段 2:黑板帧 state 复制腿消亡;
            # gold 回金公式单一源 = cw_state.sell_refund,bench 摘槽 =
            # BenchView 重建 write_logic——写口内自持陈旧提案守卫;
            # 写口经模块顶 import 单一源,函数内禁局部再 import——局部
            # import 会把名字标记为函数局部变量,令同函数其余分支的
            # 裸引用在未走该分支时 UnboundLocalError)。
            # session 透传(溢出腿):溢出腿落地时写口内同步吸收执行侧
            # tracked 主账(容器腿/执行账同帧同源,商店播种守卫对拍
            # 不因本腿分叉)。
            apply_prep_action_logic(
                _gs_sell, action,
                produced_by='CwScreenPrep',
                sig=ChannelSig(family='logic_action', actor='CwScreenPrep'),
                session=_sess)
            # 黑板帧键 = SIFT 槽位信息位(物理槽号);动作携容器下标,读键
            # 映射 = 下标+1(构造不变量 slot=idx+1,容器槽位表换算惯例)。
            _slot_key = action.bench_idx + 1
            _bench = [bc for bc in (getattr(obs, 'bench_chars', None) or [])
                      if bc is None or getattr(bc, 'slot', None) != _slot_key]
            _free = (getattr(obs, 'free_bench_slots', 0) or 0)
            if _ov_warn_pre and _ov_id_pre \
                    and _gs_sell.overflow_warning.value is False:
                # 黑板帧镜像(溢出腿):溢出卡当帧入位,腾出槽即刻回占——
                # 入位卡补进黑板 bench,free 不 +1(与容器腿/tracked 吸收
                # 同帧同源;缺镜像 = 决策面假空席,席满拒落类门被假象绕过)。
                _bench = list(_bench) + [
                    BenchChar(slot=_slot_key, char_id=_ov_id_pre)]
                return dataclasses.replace(obs, bench_chars=_bench,
                                           free_bench_slots=_free)
            return dataclasses.replace(
                obs, bench_chars=_bench,
                free_bench_slots=_free + 1)
        if isinstance(action, DeployMove):
            _gs = gs_of_ctx(getattr(self, 'ctx', None), self._session())
            apply_prep_action_logic(
                _gs, action, produced_by='CwScreenPrep',
                sig=ChannelSig(family='logic_action', actor='CwScreenPrep'))
            # 黑板帧键 = SIFT 槽位信息位(同上);落位槽 = 本帧 deployed
            # 视图首空(kernel empty_deploy_slots 单一源,与发射位
            # assign_deploy_slots/执行坐标边同式规则)。
            _slot_key = action.bench_idx + 1
            _bench = [bc for bc in (getattr(obs, 'bench_chars', None) or [])
                      if bc is None or getattr(bc, 'slot', None) != _slot_key]
            moved = next((bc for bc in (getattr(obs, 'bench_chars', None) or [])
                          if bc is not None
                          and getattr(bc, 'slot', None) == _slot_key), None)
            _deployed = list(getattr(obs, 'deployed_chars', None) or [])
            if moved is not None:
                import copy as _copy
                _back_total = (getattr(obs, 'back_layout_slots', None) or 6)
                _fe, _be = empty_deploy_slots(
                    _deployed, front_total=4, back_total=int(_back_total))
                _chosen, _fb = ((_fe, _be) if action.to_row == 'front'
                                else (_be, _fe))
                if _chosen:
                    _row, _slot_no = action.to_row, _chosen[0]
                elif _fb:
                    _row = 'back' if action.to_row == 'front' else 'front'
                    _slot_no = _fb[0]
                else:
                    _row, _slot_no = action.to_row, 0   # 满板:信息位照记,
                    # 真实落位归容器 deployed_place 守卫(陈旧提案零写)
                moved = _copy.copy(moved)
                moved.position_pref = _row
                moved.slot = _slot_no
                _deployed.append(moved)
            _front = set(getattr(obs, 'front_occupied', None) or set())
            _back = set(getattr(obs, 'back_occupied', None) or set())
            # 占用集按 fallback 解析排(_row)记行——按 to_row 记会把换排
            # 落位记成假前排占位/漏记后排;满板分支(slot=0 信息位)不入集
            #(0 非物理槽号,真值归 heavy 现读;改动三审 代-1)。
            if moved is not None and moved.slot:
                (_front if _row == 'front' else _back).add(moved.slot)
            return dataclasses.replace(
                obs, bench_chars=_bench, deployed_chars=_deployed,
                front_occupied=_front, back_occupied=_back,
                free_bench_slots=(getattr(obs, 'free_bench_slots', 0) or 0) + 1)
        if isinstance(action, SellDeployed):
            _gs = gs_of_ctx(getattr(self, 'ctx', None), self._session())
            apply_prep_action_logic(
                _gs, action, produced_by='CwScreenPrep',
                sig=ChannelSig(family='logic_action', actor='CwScreenPrep'))
            # 容器下标 → (排, 槽号) 读键映射 = kernel deployed_row_slot
            # 单一函数(执行坐标边换算收口);黑板帧 deployed 是 SIFT 物理
            # 键视图,按读键对位摘除。
            _row, _slot_no = deployed_row_slot(action.deployed_idx)
            _deployed = [d for d in (getattr(obs, 'deployed_chars', None) or [])
                         if d is None
                         or not (getattr(d, 'position_pref', '') == _row
                                 and getattr(d, 'slot', None) == _slot_no)]
            return dataclasses.replace(obs, deployed_chars=_deployed)
        if isinstance(action, LevelUp):
            # 视觉帧零变;容器域 xp/level/gold(action.cost 直写)推进
            _gs = gs_of_ctx(getattr(self, 'ctx', None), self._session())
            apply_prep_action_logic(
                _gs, action, produced_by='CwScreenPrep',
                sig=ChannelSig(family='logic_action', actor='CwScreenPrep'))
            return obs
        if isinstance(action, WearEquip):
            _owned = _owned_remove(
                getattr(obs, 'owned_equips', None), action.item_name)
            return dataclasses.replace(obs, owned_equips=_owned)
        if isinstance(action, (FurnaceUse, PrivilegeCardUse, WrenchUse,
                               PrecisionWrenchUse, StaffProjectorUse,
                               PerfectProjectorUse, LuckyTokenUse)):
            return self._project_tool_obs(action, obs)
        # 词表外类型 = 分派漏斗被绕过(F3 白名单之后不可达),响亮暴露
        # (注册表 AssertionError 同款纪律;R9 保守回退分支已删,禁静默)。
        raise AssertionError(
            f'_project_prep_obs:动作 {type(action).__name__} 无逻辑态分支'
            '(词表外/分派漏斗被绕过,响亮暴露)')

    def _project_tool_obs(self, action: CwAction,
                          obs: PrepObservation) -> PrepObservation:
        """工具原子逻辑态(R8 七类逐件;规则正本 = ``game_state/action-logic-state.md``
        §4,写端登记单一源 = ``EQUIP_WRITE_SIDES``)。逐类:

        - 冶金炉:装备腿 = 工具 −1 + 目标件消失(变异产物随机 → 观察);
          角色腿 = 穿戴域全量 → 库存域(名迁移,变异随机 → 观察)+ 工具 −1;
        - 特权赋予卡:库存腿 = 工具 −1 + 目标件名确定变换(桥 =
          ``transform_equip_to_privilege``,经 ``apply_tool_execution_write``
          容器写端);拖角色腿 = 只写工具 −1(哪件被选随机 → 观察);
        - 拆装扳手 = 目标角色穿戴域全量回库存 + 工具 −1;精密扳手同款
          不消耗(工具库存面不递减);
        - 员工/完美投影仪 = 目标角色 1 星复制入备战席(费用门/席满拒落
          零写,门表单一源 = ``_TOOL_SPAWN_COST_GATE``)+ 工具 −1;
        - 好运令牌 = 工具 −1(选件 = 策略决策面,选定前无容器可算面)。
        """
        import copy as _copy
        import dataclasses

        from sr_od.application.currency_war.data.cw_chars import CHARACTERS
        from sr_od.application.currency_war.kernel.cw_affix_effects import (
            _TOOL_SPAWN_COST_GATE,
            apply_tool_execution_write,
        )
        from sr_od.application.currency_war.kernel.cw_effect_inventory import (
            privilege_counterpart,
        )
        from sr_od.application.currency_war.kernel.cw_vocab import (
            FurnaceUse,
            LuckyTokenUse,
            PerfectProjectorUse,
            PrecisionWrenchUse,
            PrivilegeCardUse,
            StaffProjectorUse,
            WrenchUse,
        )
        tool_name = {
            FurnaceUse: '冶金炉',
            PrivilegeCardUse: '特权赋予卡',
            WrenchUse: '拆装扳手',
            PrecisionWrenchUse: '精密拆装扳手',
            StaffProjectorUse: '员工投影仪',
            PerfectProjectorUse: '完美投影仪',
            LuckyTokenUse: '好运令牌',
        }[type(action)]
        consume_tool = not isinstance(action, PrecisionWrenchUse)
        owned = list(getattr(obs, 'owned_equips', None) or [])
        occupied = ({(row, int(slot)): list(names)
                     for (row, slot), names
                     in (getattr(obs, 'occupied_equips', None) or {}).items()}
                    if getattr(obs, 'occupied_equips', None) is not None
                    else None)
        _no_write = dataclasses.replace(obs)

        def _tool_minus(names: list[str]) -> list[str]:
            if not consume_tool:
                return names
            out = list(names)
            if tool_name in out:
                out.remove(tool_name)
            return out

        target_kind = getattr(action, 'target_kind', 'char')
        if isinstance(action, (FurnaceUse, PrivilegeCardUse)) \
                and target_kind == 'equip':
            tgt = action.item_name
            if owned is None or tgt not in owned:
                return _no_write   # 库存未观察/目标已消失 → 零写留观察
            if isinstance(action, PrivilegeCardUse):
                # 库存腿确定变换(桥;容器写端 + 帧面镜像)
                gs = game_state_of(self._session())
                apply_tool_execution_write(gs, tool_name,
                                           target_equip_name=tgt,
                                           frame=f'tool_{tool_name}')
                new_name = privilege_counterpart(tgt)
                if new_name is None:
                    return _no_write   # 非进阶成品 = 调用错,零写留观察
                owned = _tool_minus(owned)
                owned = _owned_replace_one(owned, tgt, new_name)
            else:
                owned = _tool_minus(owned)
                owned = _owned_remove(owned, tgt)   # 产物随机 → 观察收口
            return dataclasses.replace(obs, owned_equips=owned)
        # 角色目标腿(炉·角色/特权·角色/扳手两件/投影仪两件/令牌)
        _worn = list((occupied or {}).get((action.row, int(action.slot)), []))
        if occupied is not None:
            if isinstance(action, (FurnaceUse, WrenchUse, PrecisionWrenchUse)):
                # 穿戴域 → 库存域全量迁移(名迁移;炉变异随机 → 观察)
                for name in _worn:
                    owned = _owned_add(owned, name)
                occupied = dict(occupied)
                occupied[(action.row, int(action.slot))] = []
        if isinstance(action, (StaffProjectorUse, PerfectProjectorUse)):
            # 费用门 + 席满拒落零写(§4.5:席满不是部分成功,是无落位)
            gate = _TOOL_SPAWN_COST_GATE.get(tool_name, 0)
            dep = next((d for d in (getattr(obs, 'deployed_chars', None) or [])
                        if d is not None
                        and getattr(d, 'position_pref', '') == action.row
                        and getattr(d, 'slot', None) == action.slot), None)
            ch = CHARACTERS.get(getattr(dep, 'char_id', '') or '') \
                if dep is not None else None
            cost = int(getattr(ch, 'cost', 0) or 0) if ch is not None else None
            free = int(getattr(obs, 'free_bench_slots', 0) or 0)
            if dep is None or cost is None or free <= 0 \
                    or (gate and cost > gate):
                return _no_write   # 拒落(超门/席满/目标未识别)零写
            if owned is not None:
                owned = _tool_minus(owned)
            _bench = list(getattr(obs, 'bench_chars', None) or [])
            _copy_bc = _copy.copy(dep)
            _copy_bc.slot = _next_free_bench_slot(_bench)
            _copy_bc.position_pref = 'back'
            _copy_bc.star = 1
            _copy_bc.equips = []
            _bench.append(_copy_bc)
            return dataclasses.replace(
                obs, owned_equips=owned, bench_chars=_bench,
                free_bench_slots=free - 1)
        # 其余角色腿:确定面 = 工具 −1(令牌选件/特权拖角色腿选件随机 → 观察)
        if owned is None:
            return _no_write
        owned = _tool_minus(owned)
        out = {'owned_equips': owned}
        if occupied is not None:
            out['occupied_equips'] = occupied
        return dataclasses.replace(obs, **out)

    def _reconcile_tracking(self, bench: list[BenchChar], deployed: list[BenchChar],
                            screen=None) -> None:
        """环入口对账(§3:read≠tracking 漂移是既有 bug 源 → SIFT 真值重置 tracking)。

        统一走公共 ``cw_reconcile.reconcile_tracking``(空读守卫/漂移留证/
        obs_conflict JSONL 单一实现,star 用 read_star 实机金星)。read 失败
        (templates None)不动。漂移 = 需关注([cw!] + 截图存证)。
        """
        session = self._session()
        if session is None:
            return
        from sr_od.application.currency_war.kernel.cw_reconcile import (
            reconcile_tracking,
        )
        reconcile_tracking(session, bench, deployed, screen, source='director', ctx=self.ctx)

    def _reconcile_faction_display(self, obs: PrepObservation) -> None:
        """备战稳定帧羁绊显示对账(cw_faction_obs 接线;零决策:不一致仅落
        缺陷台账,不纠漂不重读——羁绊状态以计算侧为主源,显示只作对账票)。

        computed 侧 = ``board_from_tracked``(session tracked_deployed,全集
        主源;None=含未知身份算不出 → 宁缺勿造跳过);显示侧 = 左侧羁绊面板
        OCR(cw_faction_obs.read_displayed_factions,只读可视条目)。截断/
        OCR 失读/残名按 cw_faction_obs 口径不评不判错,仅计数随 refs 披露;
        ``computed_missing`` 形态(compare 第四态)同为留证不判错,
        report_faction_reconcile 只转发 mismatch 行。节奏 = heavy 定型帧
        消费,全程 best-effort。
        """
        try:
            session = self._session()
            if session is None:
                return
            computed = board_from_tracked(
                list(gs_of_ctx(getattr(self, 'ctx', None), session).tracked_books.deployed or []))
            if computed is None:
                return
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return
            reading = read_displayed_factions(self.ctx, frame)
            result = compare_factions(computed, reading.entries,
                                      reading.unreadable)
            # 台账行 plane/round = 容器读口(容器化段 2)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                plane_of,
                round_num_of,
            )
            _gs = gs_of_ctx(getattr(self, 'ctx', None), session)
            plane = int(plane_of(_gs))
            round_num = int(round_num_of(_gs))
            if result.mismatch_count <= 0:
                # 不一致为零也留一条 debug(含不评口径计数),频率统计靠台账
                # 数据说话,不在此落账;行名并入见 faction_display_ok_debug_line
                log.debug(faction_display_ok_debug_line(
                    len(result.rows), len(result.ocr_skipped),
                    list(result.truncation_suspects),
                    sum(1 for r in result.rows
                        if r.verdict == "computed_missing")))
                return
            refs = [
                {'field': 'ocr_skipped', 'value': ','.join(result.ocr_skipped)},
                {'field': 'unmatched', 'value': ','.join(reading.unmatched)},
                {'field': 'truncated', 'value': str(reading.truncated)},
                {'field': 'truncation_suspects',
                 'value': ','.join(result.truncation_suspects)},
                {'field': 'computed_missing',
                 'value': ','.join(r.faction for r in result.rows
                                   if r.verdict == 'computed_missing')},
            ]
            n = report_faction_reconcile(
                result, plane=plane, round_num=round_num,
                gap_large=True,
                verdict=('留证-羁绊面板显示计数与计算侧不一致(计算侧= tracked '
                         '全集主源,显示只作对账票;零决策记账不纠漂。已知不评:'
                         '面板底部截断/OCR 失读/残名/computed_missing 均只计数'
                         '不判错;单次 L1,复现升 L0 由分级安灯承接)'),
                refs=refs,
                reader_source='faction_display_reconcile',
            )
            log.debug(f'[cw-director] faction_display reconcile: '
                      f'{result.mismatch_count} mismatch → {n} 行台账')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] faction_display reconcile skip: {e}')

    def _reconcile_shop_pool(self, obs: PrepObservation) -> None:
        """商店打开 heavy 帧卡池一致性票(cw_shop_obs.check_shop_pool 接线;
        零决策:违例仅落缺陷台账,不 return/不重读不纠错)。

        帧 = obs.shop_open 且 state.shop 非空(shop 关态 read_shop_cards
        自带收起锚门返空,天然跳过;state.shop 即 read_game_state 内
        read_shop_cards 现读链,零新增 SIFT)。pool_state:无池追踪账
        (cw_state 只有我方 tracked 持有,池内剩余无人建账)→ 传 None =
        只查 tier 门,池守恒查如实降级(无池账口径),refs 披露。
        tier_locked = 该费用档在当前等级概率为 0(REFRESH_PROB 单一源)
        = 牌识别错或等级读错的强证据。节奏 = heavy 定型帧消费,全程
        best-effort。
        """
        try:
            session = self._session()
            if session is None or not obs.shop_open:
                return
            # 容器化段 2:牌面 = 容器 payload 域(离屏 None 天然跳过);
            # level/plane/round = 容器读口。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                level_of,
                plane_of,
                round_num_of,
            )
            _gs = gs_of_ctx(getattr(self, 'ctx', None), session)
            cards, unnamed = _shop_pool_inputs(_gs)
            if not cards:
                return
            violations = check_shop_pool(cards, int(level_of(_gs)), None)
            if not violations:
                return
            obs_txt = ';'.join(f'{v.name}/{v.cost}:{v.kind}({v.detail})'
                               for v in violations)
            defects.record_defect(
                _SHOP_DEFECT_SURFACE, _SHOP_POOL_DEFECT_KIND,
                expected='0 违例(五牌两查)',
                observed=obs_txt,
                plane=int(plane_of(_gs)),
                round_num=int(round_num_of(_gs)),
                gap_large=True,
                verdict=('留证-商店牌卡池一致性违例(tier_locked=该费用档本'
                         '等级概率为0,牌识别错或等级读错;invalid_cost=费用'
                         'OCR误读。pool_state 无账本传 None,池守恒查如实'
                         '降级未做;零决策记账,单次 L1,复现升 L0 由分级'
                         '安灯承接)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('level', str(int(level_of(_gs)))),
                    ('cards', str(len(cards))),
                    ('unnamed', str(unnamed)),
                    ('pool_state', 'None(池查降级)'))],
                reader_source='shop_pool_reconcile',
                note='期望态层·商店:违例票=cw_shop_obs.check_shop_pool'
                     ' 纯函数(REFRESH_PROB/POOL_COPIES_PER_CARD 单一源),'
                     '与买牌/经验/羁绊通道分立')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] shop_pool reconcile skip: {e}')

    def _reconcile_merge_preview(self, obs: PrepObservation) -> None:
        """商店打开 heavy 帧合成预览交叉验证(cw_shop_obs.compare_merge_preview
        接线,与 _reconcile_shop_pool 同族同帧;零决策:mismatch 仅落缺陷台账,
        不 return/不重读不纠错)。

        帧 = obs.shop_open 且 state.shop 非空(与卡池票同门)。our =
        ``_merge_preview_inputs`` 按同名同星持有折算;det = 商店快照逐牌
        merge_preview>0(reader = cw_identity_obs.read_merge_preview,已
        在产线;激活依据 = 激活评估:136 组同刻重复读数 0 分歧/15
        非零事件 8 例精确相符)。our_suspect/game_extra 均开票留证——
        our_suspect = 我方合成计算嫌疑(单向罚则唯一对象),game_extra =
        我方漏算(不判罚只计数);our_suspect 祇当「持有 ≥1 副本但同刻
        重复读数恒 0」的系统性形态才是暗相漏检证据(激活评估报告有
        回退采帧解锁条件),单票不判死。节奏 = 同款 heavy 定型帧消费,best-effort。
        """
        try:
            session = self._session()
            if session is None or not obs.shop_open:
                return
            # det 侧吃**同帧 raw 牌**(读取器域载荷缓存):merge_preview 是
            # ✦ 读取器信号,派生读取器域不入记录容器——容器 payload 经
            # ``shop_cards_to_legacy(frame_cards=同帧 raw 牌)`` 下标对齐
            # 透传,失配窗置缺省 0(拿容器当 det 会把「读不到 ✦」伪证成
            # 「无副本」,对账票毒化——缓存槽语义见 __init__ 注)。
            # our 侧席位 = 容器读口(容器化段 2:_cached_state 槽退役)。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                plane_of,
                round_num_of,
            )
            _gs = gs_of_ctx(getattr(self, 'ctx', None), session)
            our, det, unnamed = _merge_preview_inputs(
                _gs, frame_cards=(self._cached_shop_cards or None))
            if not our:
                return
            result = compare_merge_preview(our, det)
            mism = [r for r in result.rows if r.verdict != 'match']
            if not mism:
                return
            obs_txt = ';'.join(
                f'slot{r.slot}:{r.verdict}(our={r.our} det={r.detected})'
                for r in mism)
            defects.record_defect(
                _SHOP_DEFECT_SURFACE, _SHOP_MERGE_DEFECT_KIND,
                expected='0 mismatch(合成预览=我方同名同星持有>0 vs 识别✦>0)',
                observed=obs_txt,
                plane=int(plane_of(_gs)),
                round_num=int(round_num_of(_gs)),
                gap_large=True,
                verdict=('留证-商店牌合成预览对账不一致(our_suspect=我方算'
                         '有副本而识别无✦=合成计算嫌疑或识别暗相漏检,双义'
                         '不逐票判死;game_extra=识别有✦而我方无账=漏算'
                         '留证不判罚。merge_preview 读 0 双义=真无副本∨'
                         'fail-silent 读不到;零决策记账,单次 L1,复现升'
                         'L0 由分级安灯承接)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('slots', str(len(our))),
                    ('unnamed', str(unnamed)),
                    ('our_suspect', ','.join(str(r.slot) for r in mism
                                             if r.verdict == 'our_suspect')),
                    ('game_extra', ','.join(str(r.slot) for r in mism
                                            if r.verdict == 'game_extra')),
                    ('reader', 'shop.merge_preview(已产线)'))],
                reader_source='merge_preview_reconcile',
                note='期望态层·商店:对账票=cw_shop_obs.compare_merge_preview'
                     ' 纯函数(单向验证,合成主源=我方计算),与卡池票同帧'
                     '分立')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] merge_preview reconcile skip: {e}')


    def _session(self) -> StrategySession | None:
        match = getattr(self.ctx, 'cw_match', None)
        return match.session if (match is not None and match.session is not None) else None

    def _match(self) -> CurrencyWarMatch | None:
        return getattr(self.ctx, 'cw_match', None)

    # ===== 备战单轮 op(W971 P3b 返工定稿:拆内环,op 生命周期五段化)=====
    # 外循环(cw_loop)是唯一循环:备战画面在 → 外循环每轮调本 op 一轮。
    # 单轮 = ①数据观察(heavy→写 session)②对账(观察 vs session 历史/上轮
    # 期望)③-⑤ 单动作决策循环(决策→执行→逻辑态直写,循环内零读屏;终结 op
    # 交回外循环)——ADR-0517 迁移批:per-action heavy 重读契约已灭,期望态
    # 由逻辑态直写承载逐动作推进。原内环机制
    # (步数预算/stall 门/连败→恢复→屏蔽/bail 同因计数/ping-pong 停机)随
    # 内环拆除——稳定性由外循环每轮重识别保证(特效帧/overlay 弹出在轮间
    # 自然可见);无进展留证归外循环 stall 防线(cw_loop 备战分支)。

    @operation_node(name='备战单轮', is_start_node=True)
    def run(self) -> OperationRoundResult:
        match = self._match()
        if match is None or match.strategy is None:
            return self.round_fail(status='无 cw_match(对局未初始化)')
        # 装配点分流(统一观察架构 §9.1 并存期):cw_game_ports 两端口完整
        # 在场(= 测试 harness 显式装配)→ 五段生命周期新路径;缺省 None =
        # 生产直连旧路径(下方原序列,试点等价门通过前生产行为零变化)。
        # 判据用装配完整性(安装协议两端口成对),不新建开关机制
        #(开关生命周期纪律,strategy-work §3)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        session = match.session
        self._executor = PrepActionExecutor(self, self.ctx)
        self._cached_shop_cards = []
        self._cached_bench = []
        self._cached_deployed = []
        self._cached_vacancy = 0
        self._cached_gold_trusted = False

        # —— ① 数据观察:清场 + 开商店合法态收起(读互斥:hp 关态可读)→ heavy 全量观察写 session
        self._clear_entry_overlays()
        if self._clear_prep_cards():
            # 书册卡开卡交回(批2c 链拆):弹窗已弹,heavy 观察禁读弹窗帧 →
            # 交回外循环 0k 分发选卡;交回等待值来源写死 = OpenBookcard 动画
            # 等待 _OVERLAY_ANIM_WAIT_S(R7 OpenBox 终结化同构,§3.2a 口径)。
            return self.round_success('书册卡开卡(交回:专家邀请函弹窗分发)',
                                      wait=_OVERLAY_ANIM_WAIT_S)
        self._try_collapse_open_shop()
        obs = self._observe(heavy=True)
        # 帧代次标注(ADR-0583 §3.4):入口 heavy 主观察帧 = full;消费归
        # 决策入口(含经 overlay 防线反弹的 pick 子路径,§5.5-丁)。
        _mark_frame_class(session, 'prep', 'full')
        if obs.event_overlay is not None:
            # overlay 在场 → 交回外循环重识别分发(无计数;对应 loop 0x 分支/op 接管)
            log.info(f'[cw][director] 事件 overlay({obs.event_overlay})→ 交回外循环分发')
            return self.round_success(f'事件overlay({obs.event_overlay})交回外循环分发', wait=0.8)
        # 接管局补采(W971 §2.1,挂点随单轮观察段平移;详见块内注释)
        _tk = self._takeover_collect_if_needed(match, session)
        if _tk is not None:
            return _tk
        # —— ② 对账段:本轮入口 heavy 观察 = 纯观察审计族消费点
        #      (羁绊显示/商店池/合成预览/刷新留证;零决策)。
        #      ADR-0517 决策 8 的「入口观察即对账」时点存续,per-action
        #      heavy 重读契约已灭。动作上报的对账归一 = 逻辑态直写
        #      (apply_prep_action_logic)+ 观察边界 cw_reconcile 兜底;
        #      错卖类不可逆损害窗口的收窄手段 = 执行侧
        #      tracked 账随动,同商店线双账口径。
        self._v2_post_frame_accounting(obs, session)
        #      (迁移批次二,设计 §3.2.5:警告出现太短暂无法可靠采样,玩家
        #      裁定 2026-09-09;「双证据互督」随字段裁撤一并取消)。模态
        #      恢复路径改由三既有防线承接:①部署放行判定(ADR-0596 前置谓词:
        #      bench_free>0 才发席耗动作,模态源头收敛);②环入口清场
        #      (_clear_entry_overlays,残留模态一键关);③外循环无进展
        #      守卫(动作批签名计数)。派生席满判定单一源 =
        #      kernel.cw_game_state.bench_is_full(决策/拦截消费面);
        #      破墙主动探测不复活——派生席满≠模态在场(持 9 席是合法
        #      运营态,按席满主动腾席会打穿策略持仓)。
        #      观察终饰(dual/gated_hp)已随黑板槽退役消亡(容器化段 2:
        #      dual_track_phase 不入容器,消费读 committed_from 派生形态
        #      波 3 已立,帧上二次拷回是残件;gated_hp 帧上二次施门删除,
        #      hp 消费统一经 decision_hp 门前真值+施门)。
        #      —— ③④⑤ 单动作决策循环(ADR-0517 迁移批;前身份 = 序列消费 +
        #      每动作落地后 heavy 重观察的保守口径)。新形态:入口 heavy 一次
        #      建黑板 → 逐动作『决策(黑板=逻辑态)→ F3 校验 →
        #      执行 → 逻辑态直写』循环,循环内零读屏。已知画面出口
        #      (OpenShop/StartBattle/OpenBox)= 终结 op,执行即本访问结束
        #      交回外循环(下次入口重观察)。
        #      B1 拆除(用户裁定 2026-09-10):验证段+恢复原语分支退役——
        #      动作机械执行(端口无成败回执),无进展治理归外循环 stall
        #      防线(F2),落地判定归观察侧 reconcile。
        _visit_acts: list[str] = []
        # 段序号置位(备战期开始;唯一置位点 = 本 prep 访问循环入口):
        # 访问 = 腾席拒绝结论的输入不变性段,入口 +1 使上一访问/上一域
        #(商店 visit/破墙段)残留的续段 token/结论闩按序号不等自动失效。
        # 状态对象缺席(第三方策略面/桩)= 无缓存载体,跳过置位(决策核
        # 侧冷建自 0 起,行为 = 恒重推导,保守端安全;B4 缺席退缺省口径)。
        _st_seg = strategy_state_of(session)
        if _st_seg is not None:
            _st_seg.cw4_segment_serial += 1
        for _vi in range(self.VISIT_ACTION_CAP):
            # —— ③ 决策(黑板:读 session.prep_obs_frame,写者 = 入口观察/
            #      循环逻辑态直写步;首帧 = 入口 heavy,后续 = 逻辑态)
            try:
                result = match.strategy.decide_prep_screen()
            except Exception as e:  # noqa: BLE001  策略异常 = 本轮 fail(外循环 retry 链兜)
                log.warning(f'[cw!][director] decide_prep_screen 异常: {e}')
                return self.round_fail(status=f'策略决策异常: {e}')
            if not isinstance(result, CwAction):
                log.warning(f'[cw!][director] 策略输出非 CwAction: '
                            f'{type(result).__name__}')
                return self.round_fail(status='策略输出非 CwAction(F3)')
            if isinstance(result, HoldFrame):
                # HoldFrame = 本帧无动作可发,交回外循环重观察(终态契约
                # §2.2:备战空发射帧显式信号,None 退役;等待帧非动作——
                # 不进 validate/执行器/动作注册表/续段 token/动作记录,round
                # 返回形态与等待时长逐字不变。系统级 stall_watch/NODE-DWELL
                # 哨兵对其透明;系统并无「连续空发射计数器」,stall 防线
                # 哨兵只对无进展留证)。
                return self.round_success('本帧无动作(HoldFrame),交回外循环重观察', wait=1.0)
            action = result
            # F3 校验:参数非法交回留证;执行前输入契约检查,非动作后判效
            err = self._executor.validate(action)
            key = action_key(action)
            if err is not None:
                log.warning(f'[cw!][director] 参数非法 {key}: {err} → 拒绝,交回外循环留证')
                return self.round_success(f'参数非法 {key}:{err},交回外循环留证', wait=1.0)
            # —— ⑤ 执行(机械执行,无成败回执;发出即职责完成)
            #      执行体 = _act_execute(两路径共用抽提体):落地登记注册表
            #      (§6.4 on_outcome)在其发射点统一触发(单一发射口,发射即
            #      触发)。
            try:
                self._act_execute(action, obs)
            except StopBrakeShortCircuit as e:
                # W209j 刹车短路(ADR-0388):停机标志已设,动作未发出 →
                # 交回外循环,下轮 loop 顶见 STOP 退出(原回执 False 通道
                # 已退役改停机短路异常)。
                log.info(f'[cw][director] 停机刹车({e}),动作未发出 → 交回外循环')
                return self.round_success(f'停机刹车({e}),动作未发出,交回外循环', wait=1.0)
            except Exception as e:  # noqa: BLE001  执行异常上抛 = 本轮 fail
                log.warning(f'[cw!][director] 执行异常 {key}: {e}')
                return self.round_fail(status=f'执行异常 {key}: {e}')
            # 续段 token 写入(生产 prep 循环执行位;OpenShop 分支与
            # 执行器分支在此合流):发出即写(批3a 申报择一;原 progressed
            # 门退役)。状态对象缺席 = 无缓存载体,跳过(B4 缺席退缺省口径)。
            _st_tok = strategy_state_of(session)
            if _st_tok is not None:
                _st_tok.cw4_frame_action_record = (
                    type(action).__name__, _st_tok.cw4_segment_serial)
            _visit_acts.append(type(action).__name__)
            # —— 结束判定 → 交回外循环(动画等待已由执行器/编排内建)
            #      批3 终结判定对齐:终结集与等待时长改读注册表 op 类
            #      terminal/terminal_wait 类属性(消费点经注册表读类属性,
            #      禁消费点私表;本处与生命周期孪生环两处共用 _terminal_exit)。
            _op_cls = action_op_class_for(action)
            if _op_cls.terminal:
                return self._terminal_exit(action, key, _op_cls)
            # —— 逻辑态直写(ADR-0517 决策 7/10:逐动作零读屏,期望态纯计算
            #      推进;发出即直写。假黑板风险由下一入口 heavy reconcile 以
            #      实读纠逻辑态承担(期望态对账族即纠偏通道)。R9:词表逐
            #      动作有逻辑态分支,保守回退分支已删——词表外 = 响亮暴露)
            obs = self._project_prep_obs(action, obs)
            game_state_of(session).prep_obs = obs   # 黑板推进(下一动作决策读逻辑态)
            # 直写帧代次 = none(ADR-0583 §3.4):同 visit 内续动作不重复刷新
            _mark_frame_class(session, 'prep', 'none')
        # 访问动作数上限(防御:决策循环不收敛 = 逻辑态或策略 bug,交回外循环
        # 由 stall 防线接管——不静默续跑)
        return self.round_success(
            f'访问动作数达上限({self.VISIT_ACTION_CAP}),交回外循环重观察', wait=1.0)

    # ===== 统一观察架构·五段生命周期(试点步骤 1,实机侧)=====
    # 架构设计 §9.2 迁移步骤 1:本 op 为第一个基类(CwScreenOpBase)试点,
    # 现役观察/对账/决策/执行/落地登记逻辑按 §5.1 五段归位。触发面 = 装配点
    # (cw_game_ports)在场时 run() 经 run_lifecycle() 驱动(§9.1 并存期);
    # 缺省 None = 旧路径(上方原序列)。两路径共用的执行体 = _act_execute;
    # 六条已锁语义(P2-1 bench 守卫/P3-10 特效窗门/免费闸/同节点去重/
    # 随点击置位不等验效/预期条目表五键/write_logic 豁免面)逐字保绿,
    # 对照表见试点批交付(载体位置:前两者在 _observe 识别链内,免费闸/
    # 免战牌在执行器内,同节点去重在 cw_loop 备战分支挂点,均未随本批迁移)。

    def lifecycle_observe(self
                          ) -> tuple[PrepObservation,
                                     OperationRoundResult | None]:
        """段1 observe(架构设计 §5.1):适配器①取观察 payload。

        环装配前置(旧路径 run() 前置段的五段归位,语义逐位同):动作批
        签名先清 None(消费方 = cw_loop 备战分支;early return 保持 None
        防跨环误延)+ 执行器构建(act 段载体)+ light 沿用缓存复位。
        入口序列 = 过渡相位前置(§3.4:环入口清场注册表 ENTRY_OVERLAY_
        CLOSE = 过渡相位表「可一键关闭」子集的现役载体;开商店收起探针 =
        备战子态前置)→ 适配器①(可注入位,缺省实机适配器 = 现役识别链
        _observe,内部含 cw_game_ports 端口分流与 GameState 观察写端)→
        帧代次标注 → 过渡相位检查位(事件 overlay 命中 = 轻处理交回主
        循环)→ 接管补采。早退非 None = 交回外循环,后续段不执行。
        """
        match = self._match()
        session = match.session
        self._executor = PrepActionExecutor(self, self.ctx)
        self._cached_shop_cards = []
        self._cached_bench = []
        self._cached_deployed = []
        self._cached_vacancy = 0
        self._cached_gold_trusted = False
        # —— 段1 观察:清场 + 开商店合法态收起(读互斥:hp 关态可读)→ heavy 全量观察写 session
        self._clear_entry_overlays()
        if self._clear_prep_cards():
            # 书册卡开卡交回(批2c 链拆;语义与旧路径分支同源,见 run 体)
            return None, self.round_success(
                '书册卡开卡(交回:专家邀请函弹窗分发)',
                wait=_OVERLAY_ANIM_WAIT_S)
        self._try_collapse_open_shop()
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe(heavy=True))
        # 帧代次标注(ADR-0583 §3.4):入口 heavy 主观察帧 = full;消费归
        # 决策入口(含经 overlay 防线反弹的 pick 子路径,§5.5-丁)。
        _mark_frame_class(session, 'prep', 'full')
        if obs.event_overlay is not None:
            # 过渡相位检查位(§3.4):overlay 在场 → 交回外循环重识别分发
            # (无计数;对应 loop 0x 分支/op 接管)
            log.info(f'[cw][director] 事件 overlay({obs.event_overlay})→ 交回外循环分发')
            return obs, self.round_success(
                f'事件overlay({obs.event_overlay})交回外循环分发', wait=0.8)
        # 接管局补采(W971 §2.1,挂点随单轮观察段平移;详见 _takeover_collect_if_needed)
        _tk = self._takeover_collect_if_needed(match, session)
        if _tk is not None:
            return obs, _tk
        return obs, None

    def lifecycle_reconcile(self, payload: PrepObservation) -> None:
        """段2 reconcile(架构设计 §5.1):对账。

        - GameState 帧写入半已在适配器①识别链内完成(read_game_state
          观察流[observe/carry/prior/leave_screen/relay]
          + _observe 的备战席观察写端[P2-1 空集失读守卫/P3-10 特效窗
          观察顺延门])——识别质量机制归实机实现内部,对端口契约不可见
          (§2.3;obs.state 消费视图随黑板槽退役消亡,容器化段 2);
        - 本段 = op 级对账:纯观察审计族在本帧定型帧统一消费(ADR-0517
          决策 8:入口观察即对账)。动作上报的对账归一 = 逻辑态直写
          (apply_prep_action_logic)+ 观察边界 cw_reconcile 兜底。原观察
          终饰(dual 态拷回/gated_hp 单写者门)已随黑板槽退役消亡——
          dual_track_phase 不入容器(消费读 committed_from 派生),hp
          消费统一经 decision_hp(容器化段 2,设计件 §2.4-2)。"""
        session = self._match().session
        self._v2_post_frame_accounting(payload, session)

    def lifecycle_decision_cycle(self, payload: PrepObservation) -> OperationRoundResult:
        """段3-5 单动作决策循环。

        decide(黑板 = session.prep_obs_frame,策略消费,F3 形状校验)→
        act(适配器②:意图机械执行,无成败回执)→ on_outcome(落地登记
        注册表在 _act_execute 发射点统一触发,单一发射口发射即触发)。
        生命周期无验证段(用户裁定 2026-09-10:动作未生效归动作层修可靠
        性,落地判定归观察侧 reconcile)。终结出口语义 = 无动作(None)/
        参数非法/出战(发出即终结)/开店切换/访问上限。"""
        match = self._match()
        session = match.session
        _visit_acts: list[str] = []
        # 段序号置位(备战期开始;唯一置位点 = 本 prep 访问循环入口):
        # 访问 = 腾席拒绝结论的输入不变性段,入口 +1 使上一访问/上一域
        #(商店 visit/破墙段)残留的续段 token/结论闩按序号不等自动失效。
        # 状态对象缺席(第三方策略面/桩)= 无缓存载体,跳过置位(决策核
        # 侧冷建自 0 起,行为 = 恒重推导,保守端安全;B4 缺席退缺省口径)。
        _st_seg = strategy_state_of(session)
        if _st_seg is not None:
            _st_seg.cw4_segment_serial += 1
        for _vi in range(self.VISIT_ACTION_CAP):
            # —— 段3 decide(黑板:读 session.prep_obs_frame,写者 = 入口
            #      观察/循环逻辑态直写步;首帧 = 入口 heavy,后续 = 逻辑态)
            self._lifecycle_mark('decide')
            try:
                result = match.strategy.decide_prep_screen()
            except Exception as e:  # noqa: BLE001  策略异常 = 本轮 fail(外循环 retry 链兜)
                log.warning(f'[cw!][director] decide_prep_screen 异常: {e}')
                return self.round_fail(status=f'策略决策异常: {e}')
            if not isinstance(result, CwAction):
                log.warning(f'[cw!][director] 策略输出非 CwAction: '
                            f'{type(result).__name__}')
                return self.round_fail(status='策略输出非 CwAction(F3)')
            if isinstance(result, HoldFrame):
                # HoldFrame = 本帧无动作可发,交回外循环重观察(终态契约
                # §2.2:备战空发射帧显式信号,None 退役;等待帧非动作——
                # 不进 validate/执行器/动作注册表/续段 token/动作记录,round
                # 返回形态与等待时长逐字不变。系统级 stall_watch/NODE-DWELL
                # 哨兵对其透明;系统并无「连续空发射计数器」,stall 防线
                # 哨兵只对无进展留证)。
                return self.round_success('本帧无动作(HoldFrame),交回外循环重观察', wait=1.0)
            action = result
            # F3 校验:参数非法交回留证;执行前输入契约检查,非动作后判效
            err = self._executor.validate(action)
            key = action_key(action)
            if err is not None:
                log.warning(f'[cw!][director] 参数非法 {key}: {err} → 拒绝,交回外循环留证')
                return self.round_success(f'参数非法 {key}:{err},交回外循环留证', wait=1.0)
            # —— 段4 act(适配器②:意图机械执行)+ 段5 on_outcome(落地
            #      登记注册表在 _act_execute 发射点统一触发;单一发射口,
            #      发射即触发,发出即职责完成)
            self._lifecycle_mark('act')
            try:
                self._act_execute(action, payload)
            except StopBrakeShortCircuit as e:
                # W209j 刹车短路(ADR-0388):停机标志已设,动作未发出 →
                # 交回外循环,下轮 loop 顶见 STOP 退出。
                log.info(f'[cw][director] 停机刹车({e}),动作未发出 → 交回外循环')
                return self.round_success(f'停机刹车({e}),动作未发出,交回外循环', wait=1.0)
            except Exception as e:  # noqa: BLE001  执行异常上抛 = 本轮 fail
                log.warning(f'[cw!][director] 执行异常 {key}: {e}')
                return self.round_fail(status=f'执行异常 {key}: {e}')
            self._lifecycle_mark('on_outcome')
            # 续段 token 写入(生产 prep 循环执行位;OpenShop 分支与
            # 执行器分支在此合流):发出即写(批3a 申报择一;原 progressed
            # 门退役)。状态对象缺席 = 无缓存载体,跳过(B4 缺席退缺省口径)。
            _st_tok = strategy_state_of(session)
            if _st_tok is not None:
                _st_tok.cw4_frame_action_record = (
                    type(action).__name__, _st_tok.cw4_segment_serial)
            _visit_acts.append(type(action).__name__)
            # —— 结束判定 → 交回外循环(动画等待已由执行器/编排内建)
            #      批3 终结判定对齐(同 run 体;终结集与等待时长经注册表
            #      op 类 terminal/terminal_wait,两处孪生环共用 _terminal_exit)
            _op_cls = action_op_class_for(action)
            if _op_cls.terminal:
                return self._terminal_exit(action, key, _op_cls)
            # —— 逻辑态直写(ADR-0517 决策 7/10;R9:词表逐动作有逻辑态
            #      分支,保守回退分支已删,词表外 = 响亮暴露)
            payload = self._project_prep_obs(action, payload)
            session.prep_obs_frame = payload   # 黑板推进(下一动作决策读逻辑态)
            # 直写帧代次 = none(ADR-0583 §3.4):同 visit 内续动作不重复刷新
            _mark_frame_class(session, 'prep', 'none')
        # 访问动作数上限(防御:决策循环不收敛 = 逻辑态或策略 bug,交回外循环
        # 由 stall 防线接管——不静默续跑)
        return self.round_success(
            f'访问动作数达上限({self.VISIT_ACTION_CAP}),交回外循环重观察', wait=1.0)

    def _terminal_exit(self, action: CwAction, key: str,
                       op_cls: type[ActionOp]) -> OperationRoundResult:
        """终结动作交回(批3 终结判定对齐):终结判定与等待时长改读
        注册表 op 类 ``terminal``/
        ``terminal_wait`` 类属性(消费点经注册表读类属性,禁消费点私表;
        决策循环与生命周期孪生环两处共用本口)。交回 detail 文案逐动作
        保持原样(零行为)。

        调用契约 = 仅 ``op_cls.terminal`` 为真时进入(两处调用点同守卫);
        非终结动作到达 = 终结集与消费面失配,响亮暴露。
        """
        if op_cls is StartBattleOp:
            # 出战提前终结(批3a:发出即终结——点击序列完成即交回外循环
            # 战斗分支;点击序列事实经执行器 last_launch_ok 旁路供 cw_loop
            # 发射核,出战域重设计 T-286 收缩语义)。
            return self.round_success('出战(交回外循环战斗分支)',
                                      wait=op_cls.terminal_wait)
        if op_cls is OpenShopOp:
            # 开店切商店画面(非帧稳定)→ 终结,交回外循环重识别
            return self.round_success(f'{key} ✓,交回外循环重识别',
                                      wait=op_cls.terminal_wait)
        if op_cls is OpenBoxOp:
            # OpenBox 终结化(R7,批2a):开箱即引入新事实(武装箱选择画面
            # 出现,与刷新终结结构语义 R5 同构)→ 本访问交回,外循环按
            # 武装箱选择画面分发新画面 op 选卡。交回等待 =
            # OpenBoxOp.terminal_wait(与 ``_open_box`` 动画等待
            # ``_OVERLAY_ANIM_WAIT_S`` 等价,等价测试锁 = test_cw_unified_action_3)。
            return self.round_success(f'{key} ✓(交回:武装箱选择画面分发)',
                                      wait=op_cls.terminal_wait)
        raise AssertionError(
            f'[cw][director] 非终结动作进入终结出口:{type(action).__name__}'
            '(终结集与消费面失配,响亮暴露)')

    def _act_execute(self, action: CwAction,
                     obs: PrepObservation | None = None) -> None:
        """动作执行段(五段之 act 的端口分派面;两路径共用,落地登记注册表
        的**唯一触发点**)。注入动作适配器在场 → 经适配器机械执行(§6.2
        端口,无返回);缺省 = 现役点击链直连(:meth:`_act_execute_default`)。
        on_outcome 注册表在本口发射点恰触发一次(单一发射口,发射即
        触发;每次发射恰一次由触发点唯一性承载,禁在适配器/缺省体内重复
        触发——双计即免费闸/账本类登记件毒化)。机械摘要经
        ``_last_mech_detail`` 旁路供登记件 detail(非成败回执)。执行异常
        原样上抛(含 W209j 停机短路),由调用方统一处置。"""
        _adp = self._action_port()
        if _adp is not None:
            _adp.execute(self, action)
        else:
            self._act_execute_default(action, obs)
        self.fire_outcome_hooks(action, detail=self._last_mech_detail)

    def _act_execute_default(self, action: CwAction,
                             obs: PrepObservation | None = None) -> None:
        """现役点击链缺省执行体(实机适配器②的封口内容;旧路径 run() 与
        五段循环同调,自身**不触发**注册表——触发统一归
        :meth:`_act_execute` 分派面,防双计)。OpenShop = 流程层商店编排
        [spend 单元记账 + _open_shop_phase];其余 = 执行器机械执行。发射型
        登记件(遭遇/策略屏刷新计数)由各自执行链在点击发射点触发,不经
        本口。机械摘要写入 ``_last_mech_detail``(登记件 detail 供给;
        端口无返回后的旁路通道)。

        ``obs`` = 当前黑板帧(调用方传入;缺省 = session.prep_obs_frame
        黑板现值——黑板两写点[入口观察/循环逻辑态直写步]与决策循环局部帧恒
        同步,契约 W971 §2,故黑板现值即合法供给源)。"""
        if isinstance(action, StartBattle):
            # 出战意图执行 = 统一执行器(face=armed:屏态复验→浮层安全检查
            # →部署原子序→出战点击链;迭代 design §2.2/方案 4——策略前置
            # 发射位的意图在此落执行)。launch_fired = 交回契约事实。
            from sr_od.application.currency_war.operations.cw_loop import (
                launch_battle_unified,
            )
            _ok_lbu, _detail_lbu = launch_battle_unified(self, self.ctx,
                                                         face='armed')
            self.launch_fired = bool(_ok_lbu)
            self._last_mech_detail = _detail_lbu
            log.info(f'[cw][director] {action_key(action)} → {_detail_lbu}')
            return
        if isinstance(action, OpenShop):
            if getattr(action, 'restricted_spend', False):
                # 受限访问(发射帧仲裁意图执行;金出口族出口 B):仲裁单元
                # 自含预检/域判/预算闸/第三载体行,语义单一源 = cw_loop
                # _launch_frame_arbitration(意图化仅换宿主,函数原样复用)。
                from sr_od.application.currency_war.operations.cw_loop import (
                    _launch_frame_arbitration,
                )
                _arb = _launch_frame_arbitration(self)
                self._last_mech_detail = (
                    f"仲裁访问(zone={_arb.get('zone')} "
                    f"executed={_arb.get('executed')} "
                    f"gate_blocks={_arb.get('gate_blocks')})")
                log.info(f'[cw][director] {action_key(action)} → '
                         f'{self._last_mech_detail}')
                return
            if obs is None:
                _sess = self._session()
                obs = (game_state_of(_sess).prep_obs
                       if _sess is not None else None)
            try:
                progressed, detail = self._open_shop_phase(action, obs)
            except Exception as e:
                self._last_mech_detail = f'执行异常:{e}'
                raise
            self._last_mech_detail = detail
            log.info(f'[cw][director] {action_key(action)} → {detail}')
            return
        self._executor.execute(action)
        self._last_mech_detail = getattr(self._executor, 'last_detail', '')
        log.info(f'[cw][director] {action_key(action)} → {self._last_mech_detail}')

    def _takeover_collect_if_needed(self, match: CurrencyWarMatch,
                                    session: StrategySession
                                    ) -> OperationRoundResult | None:
        """接管局补采(W971 §2.1/01-opening §2.1;单轮化后挂点 = 单轮 op 观察段)。

        触发 = gs.plane_bosses 空(本局尚无位面序真值;终态契约 §B:session
        中转退役);可交互门 = 节点条
        可读;会开/关位面详情画面 → 执行后交回外循环重识别。计数挂容器
        match_facts 域 Field(单轮 op 每外循环轮次重建,实例属性不存活);
        成功或 2 次失败后停。旗标渠道 = 渠道③接管协议(logic_hook,actor =
        ResumeAttach 登记名)。
        """
        _gs = gs_of_ctx(getattr(self, 'ctx', None), session)
        _sig_takeover = ChannelSig(family='logic_hook', actor='ResumeAttach',
                                   mode='compute')
        if _gs.takeover_collect_done.value or _gs.plane_bosses.value:
            return None
        _tk_slots = None
        with contextlib.suppress(Exception):
            _tk_slots = read_node_sequence(self.ctx, self.last_screenshot)
        if _tk_slots is None:
            return None   # 节点条不可读(过场/overlay 半开帧)→ 等下轮,不消耗预算
        _tries = int(_gs.takeover_tries.value or 0) + 1
        _gs.write_logic(_gs.takeover_tries, _tries,
                        produced_by='ResumeAttach',
                        evidence='takeover_collect_tries',
                        sig=_sig_takeover)
        if _tries > 2:
            _gs.write_logic(_gs.takeover_collect_done, True,
                            produced_by='ResumeAttach',
                            evidence='takeover_collect_done',
                            sig=_sig_takeover)
            log.info('[cw][director] 接管补采两次未成,放弃(boss 缺省中性)')
            # 放弃也清空两池:残留值会被下局判空误消费(跨局泄漏)
            self.ctx.cw_plane_bosses = None
            self.ctx.cw_plane_affixes = None
            return None
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_plane_intel import (
            CwScreenPlaneIntel,
        )
        log.info('[cw][director] 新局 boss/词缀无实采真值(session 空)'
                 '→ 位面详情情报采集(可交互备战帧,第%d次)', _tries)
        # 起始采集位面(2026-09-03 用户裁决:时序反过来——进详情之前先在
        # 备战帧识别当前节点得当前位面,详情内只采当前及之后的位面);
        # 读不到保持 0 = 子 op 内部再试/全采回退。
        _start_plane = 0
        with contextlib.suppress(Exception):
            _pp = read_phase_round(self.ctx, self.last_screenshot)
            if _pp and _pp[0]:
                _start_plane = int(_pp[0])
        _pb_res = CwScreenPlaneIntel(self.ctx, start_plane=_start_plane).execute()
        # 成功取走/失败残留都清空(防泄漏到下局判空;词缀随采结算只在本分支)
        _names = list(self.ctx.cw_plane_bosses or [])
        _affixes = list(self.ctx.cw_plane_affixes or [])
        self.ctx.cw_plane_bosses = None
        self.ctx.cw_plane_affixes = None
        if _pb_res is not None and getattr(_pb_res, 'success', False) and _names:
            _gs.write_logic(_gs.takeover_collect_done, True,
                            produced_by='ResumeAttach',
                            evidence='takeover_collect_done',
                            sig=_sig_takeover)
            # 保位写(ADR-0398):徽章态位面采得 None 原样占 3 槽,
            # 丢弃会让后续位面名字左移错位(位面序真值变假)。
            # 终态契约 §B:直写 gs.plane_bosses(session 中转退役)。
            _gs.write_logic(_gs.plane_bosses, _names,
                            produced_by='ResumeAttach',
                            sig=ChannelSig(family='logic_hook',
                                           actor='ResumeAttach',
                                           screen='', mode='compute'))
            log.info('[cw][director] 开局 boss 实采完成(位面序保位):%s', _names)
        if _affixes and not _gs.enemy_affixes.value:
            _gs.write_logic(_gs.enemy_affixes, _affixes,
                            produced_by='ResumeAttach',
                            sig=ChannelSig(family='logic_hook',
                                           actor='ResumeAttach',
                                           screen='', mode='compute'))
            log.info('[cw][director] 词缀补采(位面详情横条随采,简报未供时):%s', _affixes)
        return self.round_success('接管补采执行,交回外循环重识别', wait=1.0)

    def _clear_entry_overlays(self) -> None:
        """P0 清场前置段(规范入口序列「先清场、再识别、后动作」;ADR-0462):
        环入口先逐屏探可一键关闭的 overlay(注册表 = ``ENTRY_OVERLAY_CLOSE``,
        单一源 = ``cw_overlay_registry.derive_clearable()`` 派生桥接;
        锚判定走现有 screen 体系),命中即点其关闭按钮,拿干净备战画面再进
        全量识别——识别与 overlay 状态交织是死读与冲突噪声的共同根。只收
        「无决策语义的弹窗/面板」;投资环境/策略等交互 overlay 有专属
        handler,关闭即丢决策内容,不进注册表、仍走既有 event_overlay
        bail → 外环消化路径。
        fail-open:截图/识别/点击任一异常静默返回(=现行为,外循环重判兜底)。"""
        from one_dragon.base.screen import screen_utils
        for _ in range(ENTRY_OVERLAY_CLEAR_ROUNDS):
            try:
                frame = self.screenshot()
            except Exception:   # noqa: BLE001  离线契约
                return
            _hit = None
            for _name in ENTRY_OVERLAY_CLOSE:
                try:
                    if screen_utils.get_match_screen_name(
                            ctx=self.ctx, screen=frame,
                            screen_name_list=[_name],
                            crop_first=False) is not None:
                        _hit = _name
                        break
                except Exception:   # noqa: BLE001  离线契约
                    return
            if _hit is None:
                return
            _area = ENTRY_OVERLAY_CLOSE[_hit]
            log.info(f'[cw][director] P0 清场:{_hit} 在场 → 点 {_area}')
            try:
                self.round_by_find_and_click_area(
                    frame, _hit, _area, success_wait=0.5)
            except Exception:   # noqa: BLE001  离线契约
                return
            time.sleep(ENTRY_OVERLAY_SETTLE_S)

    def _clear_prep_cards(self) -> bool:
        """备战栏物件清场(收编:原 cw_loop 备战分支派发前清场
        识别+点击逐位迁移至此——识别机制住画面 op 观察链,外循环只保留
        分派;统一观察架构设计 §3.4 过渡相位件收编挂账兑现,与环入口
        一键关注册表 ``_clear_entry_overlays`` 同位串联)。

        返回值(批2c 链拆):True = 本轮已发书册卡开卡,调用方必须**立即
        交回外循环**(弹窗已弹,heavy 观察禁读弹窗帧);False = 无书册卡
        或未发出,调用方照常续跑。两段:

        - 试用角色揭示卡(w595_trial_reveal_card):发光金卡点开即**免费**
          得 2★ 试用角色(原地变普通角色卡,后续 SIFT 自然识别)。无代价、
          无分支选择 → 非策略决策,不进 director 动作全集;环入口直接清掉
          (揭示后 heavy 观察读到的已是揭示后的真实板面,不毒化对账)。
          上界 3 轮防识别抖动死循环;揭示后卡片消失 → 自然防重入。
        - 书册卡(R10 链拆):识别到书册卡 → 改产备战词表
          动作 ``OpenBookcard`` 经执行器发射(遥测动作行 OpenBookcard 在册,
          单一发射口)→ **本访问交回**:专家邀请函弹窗由外循环 0k 分发
          ``CwScreenExpertInvite`` 选卡(R7 OpenBox 终结化同构;原 journal
          包装全链路径退役——该包装 = ADR-0584 §5.3 收编件,链拆后动作行
          归执行器、op 行归 0k 分发,双通道行缺口不再存在)。每次访问至多
          发一张,其余张由外循环下一轮自然续清;识别后不开(过渡帧/校验
          拒绝)→ 照旧续跑交 heavy 观察(识别抖动由外循环轮间自愈)。

        fail-open(与 ``_clear_entry_overlays`` 同位先例同纪律):截图/识别
        异常静默返回 False(=原外循环形态下异常交节点重试链,收编后交环内
        正常观察/外循环重判兜底;离线 mock 契约不让测试在空帧上炸)。
        """
        from sr_od.application.currency_war.kernel.cw_obs_core import (
            is_prep_like_frame,
        )
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            _ctx_slots,
            find_bookcards,
            find_trial_reveal_cards,
        )
        try:
            screen = self.screenshot()
        except Exception:   # noqa: BLE001  离线契约
            return False
        for _reveal_i in range(3):
            try:
                _cards = find_trial_reveal_cards(
                    screen, _ctx_slots(self.ctx, '备战栏', 9))
                if not _cards or not is_prep_like_frame(self.ctx, screen):
                    break
                _slot, _center = _cards[0]
                self.ctx.controller.mouse_move(_center)   # bug#1 缓解(同出战/点球口径)
                self.ctx.controller.click(_center)
                log.info('[cw][director] 试用角色揭示卡 slot%s → 点击揭示(免费 2★)', _slot)
            except Exception:   # noqa: BLE001  离线契约
                return False
            time.sleep(1.2)   # 揭示动画窗(发光消散 + 角色卡落位)
            try:
                screen = self.screenshot()
            except Exception:   # noqa: BLE001  离线契约
                return False
        try:
            _bc_cards = find_bookcards(
                screen, _ctx_slots(self.ctx, '备战栏', 9))
            if not _bc_cards or not is_prep_like_frame(self.ctx, screen):
                return False
        except Exception:   # noqa: BLE001  离线契约
            return False
        # 过渡帧点击会落空(r133 同型教训)→ 上判不在过渡帧才发。
        action = OpenBookcard(slot=_bc_cards[0][0])
        err = self._executor.validate(action)
        if err is not None:
            log.warning(f'[cw!][director] 参数非法 {action_key(action)}: '
                        f'{err} → 拒绝,交回外循环留证')
            return False
        try:
            self._act_execute(action)
        except StopBrakeShortCircuit as e:
            # W209j 刹车短路(ADR-0388):停机标志已设,动作未发出 → 交回
            # 外循环,下轮 loop 顶见 STOP 退出(与 visit 循环执行位同处置)。
            log.info(f'[cw][director] 停机刹车({e}),动作未发出 → 交回外循环')
            return True
        log.info('[cw][director] 书册卡 slot%s → OpenBookcard 已发'
                 '(交回外循环,0k 分发选卡)', _bc_cards[0][0])
        return True

    def _try_collapse_open_shop(self) -> bool:
        """环入口遇开商店稳定态(战斗胜利后新回合游戏可能自动开)→
        收起返回 True;非开态(真特效/overlay)返回 False。

        防线定位(0n 分支落地后):主防线已前移至外循环 0n 分支
        (cw_loop `_shop_open_anchors_hit` 路由,商店态禁部署/出战调度);
        本守卫降级为纵深防御二层——0n 分支漏收帧(如「备战阶段」OCR
        抖动)或 future 入口绕过路由时兜底,语义不变。

        两个调用方:① 环入口 gate 前的预收(主路径:开 → 收起后
        以收紧超时等关店态 stable,直接进本轮,不再 round_retry;
        见 _run_loop 环入口注释;首探 miss 后环入口会在有限窗内
        重试本探针,覆盖「自动开商店晚于首探」的时序竞争);② gate
        超时后的容忍探测(兜底:收起 + round_retry 重进)。

        HP/gold 读取语义本要求关态(shop.py 同款收起逻辑)。
        离线契约:探测/点击异常 → False(放行,等价旧探针 except
        break;不让容忍路径把离线 mock 测试炸掉)。
        """
        try:
            _sc = self.screenshot()
            if not self.round_by_find_area(
                    _sc, SHOP_SCREEN_NAME, '按钮-收起',
                    crop_first=False).is_success:
                return False
            log.info('[cw][director] 环入口开商店态(合法态非特效)→ 收起')
            self.round_by_find_and_click_area(
                _sc, SHOP_SCREEN_NAME, '按钮-收起', success_wait=1.0)
            return True
        except Exception:   # noqa: BLE001  离线契约
            return False

    # ===== W970 批 C:流程层商店编排(整段买牌解体的承接,§4.3.2/§4.3.6)=====

    def _open_shop_phase(self, action: CwAction,
                         obs: PrepObservation) -> tuple[bool, str]:
        """OpenShop 动作的流程层编排(壳直调三 op 调用点自 BuyShopCards 上移)。

        - read_only=True(腾席链 b 取 gold 真值 / 开态清洁面板):CwOpOpenShop
          (幂等,已开不点)→ heavy 观察(gold 开态真值进 session)→ **不调
          商店决策**(M-6 门保持:free=0 不进买牌)→ CwOpCloseShop → 节点探针
          → 回备战(W970 §4.3.6)。
        - read_only=False:开店前容器 hp 已由备战观察链直写(商店开态 HP 区
          不可读,W970 §4.3.4 读互斥;访问内 hp 决策消费统一经 decision_hp
          政策读口——迁移批 3.2 起 hp 三件组传参链随黑板帧退役删除)→
          商店单动作循环(run_buy_waves:入口观察 → decide_shop_action
          逐动作循环+逻辑态直写,终结 op 交回;MAX_REFRESH 硬墙)→
          CwOpCloseShop → finalize_buy_phase(买后重估/期望暂存/gold 对拍/
          执行事实)→ 节点探针。

        节点探针挂点 = CwOpCloseShop 完成后(店确定关的可靠时点;旧关店
        通道的字符串匹配判据已退役,改类型分派)。
        波循环失败路径不开收(店留着交上层/外环重新识别,同 BuyShopCards 原语义)。
        """
        from sr_od.application.currency_war.operations.cw_op.cw_op_close_shop import (
            close_shop,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_op_open_shop import (
            open_shop,
        )
        match = self._match()
        if match is None:
            return False, '无 cw_match(对局未初始化)'
        # B3 拆除(验证废除,用户裁定 2026-09-10:调用方不问成败,M1③):
        # open_shop/close_shop 的验关型失败回执消费删除——发出即职责完成,
        # 店实际开没开/关没关由下一帧观察侧对账自然闭环(heavy 观察 gold
        # 真值/0n 三锚/备战帧读互斥;波循环失败路径不开收语义不变)。
        _ = open_shop(self)
        if action.read_only:
            self._observe(heavy=True)   # 开态观察刷新(gold 真值)
            # 帧代次 = none(ADR-0583 §3.4/D6 补):read_only 分支不接决策
            #(M-6 门)——heavy 观察不等于主观察帧,禁把本分支误标 full
            _mark_frame_class(match.session, 'prep', 'none')
            _ = close_shop(self)
            self._probe_node_type()
            return True, 'read_only 开店重读(gold 真值)'
        # (hp 三件组读数块随黑板帧退役删除——迁移批 3.2,波 4 步 4 同款
        # 结论:容器 hp 由备战帧观察/结算既有写端承接,消费统一经
        # decision_hp 政策读口,覆盖传参链是绕行。)
        return self.visit_open_shop()

    # ===== [临时段·特殊投资策略商店停机钩子](od-dev-stop-hooks §2.1
    # 临时捕获类;用户 2026-09-10 指令:候逐条确定的特殊投资策略在场时,
    # 进入商店画面处理即停机。2026-09-16 裁定:直接停机人工采集,不再
    # 代码落截图/转储/flag。删除面 = 本整段(名单常量+防重集合+方法)
    # + visit_open_shop 首部挂点两行,不留开关/flag/配置)=====

    #: 候逐条确定的特殊投资策略名单(硬编码,不建配置;名字 = 注册表规范名,
    #: 同 cw_investments.STRATEGY_EFFECTS 键空间。名单可先于注册表建模面——
    #: 未建模的名字进不了效果清单,在册匹配是唯一判定,前瞻占位无害)。
    _SPEC_INVEST_WATCH_NAMES: ClassVar[frozenset[str]] = frozenset({
        '采购专员·金', '采购专员·彩', '双手狸开键盘！', '商业间谍', '躺平',
        '长期主义', '长期主义+', '超发货币', '成长基金', '伟大征服', '降本增效',
        '概率事件', '远见', '市场干预', '固定理财+', '返利', '返利+',
        '经验就是财富',
    })
    #: 防重停集合(进程内存):键 = 当次在场∩名单的规范名 frozenset——同组合
    #: 只停一次,组合变化(新名单效果入场)视为新组合再停;重启清零 = 允许重停。

    _SPEC_INVEST_CAPTURED: ClassVar[set[frozenset[str]]] = set()

    def _spec_invest_shop_stop_hook(self) -> str | None:
        """特殊投资策略商店停机钩子(临时捕获;触发 = 效果清单含名单效果)。

        2026-09-16 用户裁定:直接停机,采集改手动——不代码落盘。
        停机后画面原样保持(店开着):人工看画面 / MCP 截图补帧,对照
        效果注册表逐条确定该组合下商店改写/计数/经验行为,结论回填效果
        规格 verdict/notes;采够后删本整段(含 visit_open_shop 挂点两行),
        不留开关。框架截图([stop] 行)即现场帧。
        """
        match = self._match()
        session = match.session if match is not None else None
        if session is None:
            return None
        gs = gs_of_ctx(getattr(self, 'ctx', None), session)
        hit = sorted({e.spec.name for e in gs.effects.entries
                      if e.spec.name in self._SPEC_INVEST_WATCH_NAMES})
        if not hit:
            return None
        combo = frozenset(hit)
        if combo in self._SPEC_INVEST_CAPTURED:
            return None
        self._SPEC_INVEST_CAPTURED.add(combo)   # 先占位:同组合恰停一次
        log.warning('[cw!][spec-invest-hook] 特殊投资策略 %s 在场 → 停机,'
                    '人工采集(画面原样保持,处理流程见本段注释)', hit)
        rc = getattr(self.ctx, 'run_context', None)
        if rc is not None:
            rc.stop_running(reason='hook:spec_invest_shop',
                            save_screenshot=True)
        return f'特殊投资策略停机:{",".join(hit)}(人工采集)'

    # ===== [临时段结束] =====

    def visit_open_shop(self) -> tuple[bool, str]:
        """店已开态的商店访问编排(外循环 0n 分支入口,ADR-0562)。

        语义 = 「从店已开状态进入」(ADR-0517 单动作循环的入口形态):
        入口观察现读当前牌面重建期望态 → 策略器逐动作决策(买/卖/升/刷)
        → CloseShop 终结收店交回。**不调 open_shop**——店已开由外循环
        0n 三 id_mark 锚判定确认,直接跳过开店动作(比依赖 open_shop
        幂等性更进一步:已开连点都不发);「收不收」由策略器基于期望态
        决定(CloseShop = 商店画面 op 的一等终结动作),路由层不硬编码收起。

        (hp 三件组形参已随黑板帧退役删除——迁移批 3.2:访问内 hp 决策
        消费统一经 decision_hp 容器读口,显式开店路径与 0n 路径同源。)

        编排单一源归属:本方法 = 商店访问尾段(run_buy_waves → CwOpCloseShop
        → finalize_buy_phase → 节点探针)的唯一编排点,显式开店路径与 0n
        转交路径共用。失败路径不开收(店留着交上层重新识别,同 _open_shop_phase)。
        """
        # [临时钩子挂点] 特殊投资策略商店采集停机(采够删:整段 = 上方
        # _spec_invest_shop_stop_hook 临时段 + 本两行);触发即已停机留证,
        # 返回失败回执不进买牌循环——零 click,画面原样保持待 AI 接管。
        if (_spec_stop := self._spec_invest_shop_stop_hook()) is not None:
            return False, _spec_stop
        match = self._match()
        if match is None:
            return False, '无 cw_match(对局未初始化)'
        # gold_open = visit 入口现读快照(finalize 金差值对拍基线;对抗
        # F2-3:Field 单最新帧无历史,禁事后从容器回取历史帧)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of as _gs_of_open,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            gold_of as _gold_of_open,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_op_close_shop import (
            close_shop,
        )
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_buy_cards import (
            run_buy_waves,
        )
        _gold_open = _gold_of_open(_gs_of_open(match.session))
        _rr, ledger = run_buy_waves(self, match)
        if _rr is not None or ledger is None:
            return (False, f'买牌循环未完成'
                    f'({_rr.status if _rr is not None else "无产出"})')
        # B3 拆除(同上,M1③ 调用方不问成败):关店发出即过,不再验
        # 「收起消失」——店关没关由下一帧观察侧对账(0n 三锚/备战双锚)
        # 自然闭环,误入口时外循环 0n 重入商店访问幂等收起自愈。
        _ = close_shop(self)
        _summary = finalize_buy_phase(self, match, ledger, _gold_open)
        self._probe_node_type()
        return True, f'买牌 {_summary}'

    def _v2_post_frame_accounting(self, obs: PrepObservation,
                                  session: StrategySession) -> None:
        """新环 heavy 定型帧上的纯观察审计族(零决策)。

        输入 = 本帧 obs;每通道内部 best-effort,异常不阻塞环。覆盖:
        羁绊显示 / 商店池 / 合成预览。动作期望账通道(paddle 审计/
        drag_expect/买牌期望/经验/装备期望)不属本口——动作上报的对账
        归一 = 逻辑态直写(apply_prep_action_logic)+ 观察边界
        cw_reconcile 兜底。
        """
        import contextlib

        with contextlib.suppress(Exception):
            self._reconcile_faction_display(obs)
        with contextlib.suppress(Exception):
            self._reconcile_shop_pool(obs)
        with contextlib.suppress(Exception):
            self._reconcile_merge_preview(obs)

    def _probe_node_type(self, screen: MatLike | None = None) -> None:
        """[观测] 备战入场读节点行序列(read_node_sequence)→ log。

        read_node_sequence =
        HoughCircles 动态定圆 + HSV 三态 + Hu 匹配 + OCR(见 cw_node_reader)。
        screen 传入时(关店后的 gate 稳定帧透传)复用该帧
        不重截——gate 稳定帧的全图 OCR 已按 id(image) 缓存,节点行 OCR 读缓存命中,
        省一次截图 + 全图 OCR;None=自截图(旧行为,离线/其他调用点兼容)。
        未识别图标采集钩子(版本前哨,保留):未来圆 hu_dist > 阈值 → 裁图标存盘。
        ⚠️ 已知误报(2026-08-16 复盘):历史 61 张采集全是**宝箱(奖励)图标的小尺寸 Hu 漂移**
        (idx 4/5/7 远处节点,非新类型)——HU_DIST_UNRECOGNIZED=2.8 对远距小图标过严,
        修阈值/过滤属 reader 校准待办(与扑满无关:扑满=奖励图标已实证,M45 current:reward
        直接命中)。真新类型出现时本钩子仍是唯一自动捕获渠道,保留。"""
        try:
            from sr_od.application.currency_war.obs.cw_node_reader import (
                HU_DIST_UNRECOGNIZED,
                NODE_ROW_RECT,
            )
            from sr_od.application.currency_war.obs.cw_observation import (
                read_node_sequence,
            )
            screen = screen if screen is not None else self.screenshot()
            slots = read_node_sequence(self.ctx, screen)
            if not slots:
                log.info('[cw-director][nodeseq] skip(模板未加载 / 非 clean 备战帧)')
                return
            summary = ', '.join(
                f'{s.idx}:{s.state}:{s.node_type}' + (f'({s.hu_dist:.1f})' if s.hu_dist else '')
                for s in slots)
            log.info(f'[cw-director][nodeseq] n={len(slots)} | {summary}')
            self._capture_unrecognized_node_icons(screen, slots, NODE_ROW_RECT, HU_DIST_UNRECOGNIZED)
            # current 槽类型写 session(结算观测回路 cw_screen_battle_wait 消费——
            # 节点类型分层遥测;权威源=备战节点行,替代结算屏 OCR 推断)。
            # current 高亮态 Hu 不匹配(模板只对
            # future 生效)+OCR 标签错位守卫 → current 直读恒 None。
            # 修:**last-known upcoming**——上一备战帧 upcoming[i] 就是本轮
            # current(节点行固定序列左移);本帧 upcoming 同时存下轮用。
            try:
                _sess = (self.ctx.cw_match.session
                         if self.ctx.cw_match is not None else None)
                if _sess is not None:
                    # 首帧(r1 或重启后)写开局
                    # 槽序表——cw_loop 兜底此前**无写入者**
                    # (审计实锤死读);plane_node_table = 本帧全部槽
                    # (current+upcoming+past 按 idx)的类型序。
                    _all = sorted(slots, key=lambda s: s.idx)
                    _seq = [s.node_type for s in _all if s.node_type]
                    # 位面锚 = 容器节点读口(last_state 链退役换源;节点
                    # 未观察 = None,槽序表首帧写入退开局语义不变)。
                    _nd_now = (gs_of_ctx(getattr(self, 'ctx', None), self.ctx.cw_match.session)
                               .node.value
                               if self.ctx.cw_match is not None else None)
                    _plane_now = (_nd_now.plane if _nd_now is not None
                                  else None)
                    if store_plane_table(_sess, _seq, _plane_now):
                        log.info('[cw-director][nodeseq] 槽序表存 p%s %d 槽:%s',
                                 _plane_now, len(_seq), _seq)
                    # 台账写点③·备战行源(遥测观测面;ADR-0609):
                    # PlaneNodeLedger 原有两个写入端在正常局只覆盖 P1——写点②
                    # (投资环境选择后重读)只在开局 1-1 前触发,写点①(位面
                    # 详情采集)仅接管局触发(briefing_bosses 空门)→ P2/P3 序列
                    # 恒缺,p26 备战帧采样(node_type_next)与 flow 掉血回落查表
                    # 全 miss(sim 语料 P2 备战轮 miss 18/24 实证)。本写点每备战
                    # 帧 heavy 观察已在读节点行,读数按位合并进 session 权威表:
                    # 槽 idx(0-based)= 该位面第 idx+1 轮,与台账 seq 下标同基
                    # (cw_node_reader「槽 i = 第 1+i 轮」);current 槽已由
                    # read_node_sequence 的 OCR 标签带位置覆盖填值 → 备战查表
                    # 「当前轮」从本位面首个 clean 备战帧起即命中。合并语义
                    # (None 位保旧)下 past 槽 None 不覆盖历史非 None 读数;
                    # 投资环境变异窗内节点行合法变异中,不写(与三票校验豁免
                    # 窗同语义,防把变异中序列当真值落表)。另设轮位对齐门
                    # (检测圆漏检→槽枚举左移的错位帧拒写,见门注)。纯观测
                    # 写入:失败不阻塞备战环,查表消费面行为不变。
                    try:
                        import time as _ltime

                        from sr_od.application.currency_war.kernel.cw_exec_state import (
                            get_node_ledger,
                            ledger_update_plane,
                        )
                        _ledger_now = get_node_ledger(_sess)
                        _ledger_seq = [s.node_type for s in _all]
                        # 轮位对齐门(落地审建议修):槽 idx 是检测圆枚举序,
                        # HoughCircles 中段漏检一圆 → 后续槽整体左移 → 按绝对位
                        # 合并会把类型写错位且 past 位不可自愈。帧内自洽交叉锚 =
                        # current 槽 idx 必须 == round_num-1(台账语义 seq[round-1]
                        # 即当前轮);错位帧拒写本帧,等下个 clean 备战帧。
                        _align_cur = next(
                            (s for s in _all if s.state == 'current'), None)
                        _align_ok = (
                            _align_cur is not None
                            and _nd_now is not None and _nd_now.round_num
                            and _align_cur.idx == int(_nd_now.round_num) - 1)
                        if (_ledger_now is not None and _plane_now
                                and _ledger_seq and _align_ok
                                and _ledger_now.env_grace_until <= _ltime.monotonic()):
                            _lchanged = ledger_update_plane(
                                _sess, int(_plane_now), _ledger_seq, 'prep_row')
                            if _lchanged:
                                log.info('[cw-director][nodeseq] 台账落账 p%d(prep_row):%s',
                                         _plane_now, _ledger_seq)
                    except Exception:   # noqa: BLE001  观测写点 best-effort
                        pass
                    # (左移推断/current/upcoming 的 session 写段已随终态契约
                    #  §A′ node 单一源退役删除:消费点直读 node_kind_of(gs);
                    #  ledger 落账承探针真值面——重锚宿主迁移另子件 §A′。)
            except Exception:   # noqa: BLE001  best-effort 写入
                pass
        except Exception as e:  # noqa: BLE001  live 验证 best-effort,失败不阻塞备战
            log.info(f'[cw-director] nodeseq skip: {e}')

    def _capture_unrecognized_node_icons(self, screen: MatLike, slots: list,
                                         node_row_rect: tuple[int, int, int, int],
                                         hu_threshold: float) -> None:
        """未识别图标采集(版本前哨):未来圆 Hu 无显著最近 → 裁图标存盘(内容哈希去重)。

        仅 upcoming 槽(判态已修 V 门,变暗过去节点不再混入);RGB 裁剪存盘(颜色信息保留,
        模板同样 RGB——2026-08-16 用户指导)。
        同 idx 300s 时间窗防抖 —— 内容哈希去重防不住备战帧微变
        (光标/金币动画/抗锯齿 → 哈希必新),同 idx 每帧重采刷屏
        (2-7 实证 idx4/5 连发);
        已知误报源是远距小图标 Hu 漂移(61 张复盘),300s 窗足够人工/离线跟进,新类型
        (真未识别)首采不受影响。
        """
        import time as _time

        from sr_od.application.currency_war.kernel.cw_observe import cw_shot_unique
        icon_r = 24   # 采集分析窗(略 > 分类窗 _SAMPLE_R=18,多上下文)
        x0, y0, x1, y1 = node_row_rect
        row = screen[y0:y1, x0:x1]
        now = _time.monotonic()
        for s in slots:
            if s.state != 'upcoming' or s.hu_dist is None or s.hu_dist <= hu_threshold:
                continue
            if now - _NODE_ICON_SHOT_TS.get(s.idx, 0.0) < 300:
                continue   # 同 idx 时间窗内已采过(帧微变哈希必新,内容哈希去重失效;module-level 跨环存活)
            yc0, yc1 = max(0, s.cy - icon_r), s.cy + icon_r
            xc0, xc1 = max(0, s.cx - icon_r), s.cx + icon_r
            fn = cw_shot_unique(row[yc0:yc1, xc0:xc1], f'node_unknown_{s.idx}')
            if fn:
                _NODE_ICON_SHOT_TS[s.idx] = now
                log.info(f'[cw-director][nodeseq] 未识别图标 idx={s.idx} hu={s.hu_dist:.1f} → 采 {fn}')

    def _record_step(self, obs: PrepObservation, action: CwAction) -> None:
        """(已退役 no-op:步进 decisions 行随 decisions 流写入端删除——删除波 1。)

        方法体保留空壳的原因:测试 harness(_cw_helpers.make_prep_round_
        director)按桩面同源声明 monkeypatch 本方法,签名在场 = 桩面契约
        不破;步进序列的现役证据 = journal 快照行(每帧自带全量 state)。
        """
        return


def _write_prep_node_chain(session: object, slots: list | None,
                           sig: ChannelSig) -> None:
    """备战帧现行链写端(链观察落地批;语义正本 =
    game_state/chain-observation.md §3,quality=prep_row)。

    挂点 = 备战入口 heavy 观察的节点行读(director 侧写容器,组装层
    单写者原则只回传 slots)。逐格映射:past→dim/None;current→左移携带
    (上一帧该位 upcoming 的 Hu 读数,载体 = 链自身上一帧——自锚定免新增
    anchor 状态;首帧无携带 = none/None,与现役台账 fail-open 等价);
    upcoming→hu/超阈 none;boss 末槽→sift,SIFT miss→none/None 禁回落
    Hu(槽 Hu 距离系统性不可靠,cw_node_reader 在案)。

    写门 = 轮位对齐门(current 槽 idx == round-1,错位帧拒写);变异窗
    **不对链写设门**(整帧覆盖自愈 + diff 两帧门,见迭代 design §2.3-7);
    对齐 clean 读成功即关 env_grace_until(投资环境写点②退役后短窗重读
    职责由本读承接)。基线回填:本位面基线为空时同帧写 prep_row_first
    (P2/P3 基线承接,链正本 §3 回退序末位)。纯观测写点:异常不阻塞
    观察链。
    """
    if session is None or not slots:
        return
    try:
        import time as _diff_time

        from sr_od.application.currency_war.kernel.cw_exec_state import (
            get_node_ledger,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            NodeChain,
            TokenCell,
            maybe_emit_chain_diff,
        )
        from sr_od.application.currency_war.obs.cw_node_reader import (
            HU_DIST_UNRECOGNIZED,
        )
        gs = game_state_of(session)
        nd = gs.node.value
        if nd is None or not nd.round_num:
            return
        ordered = sorted(slots, key=lambda s: s.idx)
        cur = next((s for s in ordered if s.state == 'current'), None)
        if cur is None or cur.idx != int(nd.round_num) - 1:
            return   # 轮位对齐门:Hough 漏检左移的错位帧拒写
        prev = gs.node_path.value
        carry = None
        if isinstance(prev, NodeChain) and prev.plane == nd.plane \
                and 0 <= cur.idx < len(prev.seq):
            pc = prev.seq[cur.idx]
            if pc is not None and pc.channel == 'hu' and pc.token:
                carry = pc
        last_idx = ordered[-1].idx
        cells: list[TokenCell] = []
        for s in ordered:
            if s.state == 'past':
                cells.append(TokenCell(None, 'dim'))
            elif s.state == 'current':
                if carry is not None:
                    cells.append(
                        TokenCell(carry.token, 'hu', carry.hu_dist))
                else:
                    cells.append(TokenCell(None, 'none'))
            elif s.idx == last_idx:
                cells.append(TokenCell('boss', 'sift', s.hu_dist)
                             if s.boss else TokenCell(None, 'none'))
            elif s.node_type and s.hu_dist is not None \
                    and s.hu_dist <= HU_DIST_UNRECOGNIZED:
                cells.append(TokenCell(s.node_type, 'hu', s.hu_dist))
            else:
                cells.append(TokenCell(None, 'none'))
        chain = NodeChain(plane=int(nd.plane), seq=cells)
        gs.observe(gs.node_path, chain, evidence='prep_row', sig=sig)
        if gs.node_path_baseline.value is None:
            gs.observe(gs.node_path_baseline, chain,
                       evidence='prep_row_first', sig=sig)
        ledger = get_node_ledger(session)
        was_open = (ledger is not None
                    and ledger.env_grace_until > _diff_time.monotonic())
        if ledger is not None:
            ledger.env_grace_until = 0.0
        # 链 diff 触发(窗内豁免清候选,窗关后按两帧确认补比对)
        maybe_emit_chain_diff(gs, snapshot=False,
                              in_mutation_window=was_open, sig=sig)
    except Exception:   # noqa: BLE001  观测写点 best-effort,不阻塞观察链
        pass


def finalize_buy_phase(op: SrOperation, match, ledger, gold_open: int | None) -> str:
    """买牌单元收尾(W970 批 C 抽出:整段买牌解体后由流程层
    ``CwScreenPrep._open_shop_phase`` 与 sim 兼容壳 BuyShopCards.buy 共用;
    单一源防双份漂移)。gold 对拍 / 执行事实 gold_close 回填,返回单元
    摘要字符串(消费方包装成 round status/detail)。

    (迁移批 3.2:outcome 形参随 BuyCardsOutcome 退役改账本 ledger 本体;
     gold 基线 = 编排壳 visit 入口容器 gold 现读(调用方传入);摘要与
     对拍的 gold/level/plane = 容器读口。)
    """
    from sr_od.application.currency_war.obs.cw_observation import (
        read_gold,
    )
    from sr_od.application.currency_war.operations.cw_screen.cw_screen_buy_cards import (
        expected_gold_after_actions,
    )
    total_buy = ledger.total_buy
    total_xp_buy = ledger.total_xp_buy
    total_refresh = ledger.total_refresh
    total_sell = ledger.total_sell
    total_sell_income = ledger.total_sell_income
    _spend_executed = ledger.spend_executed
    # (「买后重估容器喂入」残段已退役,2026-09-16 归因批确认流程:OpenShop
    #  = 终结动作,执行完交回外循环,下一次备战访问的入口 heavy 观察必然
    #  先于任何决策发生——它以真读覆盖容器并把帧类标 'full',本段喂入的
    #  gold 真读写 / bench tracked 重播 / 'view' 标记三样全被覆盖,从不被
    #  消费;且流程层散读屏幕违反 ADR-0517 唯一读屏点纪律。买后方向刷新
    #  由入口观察链自然承载(r251 当年病灶的现役结构性替代)。金差值对拍
    #  职责保留。)
    # gold 差值双源对拍(观察冲突审计 #6 P2,2026-08-17):动作账(逐动作执行时
    # 累计的 _spend_executed:买价+升级费+当次刷价)vs 关店后实际读数 ——
    # expected = 开店首读金 − 全程执行花金 + 全程卖入。基线必须取首读快照
    # 而非末波重读值(后者已净含各波花销,再减全程账 = 跨波重复扣,多波
    # 刷新场景期望恒偏低,量级=前面各波刷新费合计)。(read_gold stylized
    # 间歇漏,但差值对拍容忍 ±2:收入/连胜金不可观项混入)。不等 → 一方有
    # 毒(stylized 漏读 / cost 错 / 未观收入),留证统计毒化率;机制核对器
    # (r9)另有 REFRESH_COST 专项,此处只管 gold 总账。
    if total_buy or total_xp_buy or total_refresh or total_sell:
        _spend = _spend_executed
        _final_gold = read_gold(op.ctx, op.screenshot())
    # (关店实读金暂存 set_unit_gold_close 已随 spend_ledger 流写入端
    #  退役删除——删除波 1;金对拍冲突留证(下方 obs_conflict,收编
    #  journal obs_event)照常。)
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of as _fb_gs_of,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        gold_of as _fb_gold_of,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        level_of as _fb_level_of,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        plane_of as _fb_plane_of,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        round_num_of as _fb_round_of,
    )
    _fb_gs = _fb_gs_of(match.session)
    # ADR-0329 件2:gold 差值对拍纳入卖入——卖出接线后,卖轮实际金 =
    # 开店金 − 花出 + 卖入(游戏侧卖出入账);旧口径不含卖入与实读金恒差
    # income → 每卖轮误报 gold_delta 冲突留证(design 章2.7 必改项)。
    # 基线缺读兜底 = 容器现读(旧 outcome.state.gold 回退同型)。
    _expected = expected_gold_after_actions(
        gold_open if gold_open is not None else _fb_gold_of(_fb_gs),
        _spend, total_sell_income)
    if _final_gold is not None and abs(_final_gold - _expected) > 2:
        from sr_od.application.currency_war.kernel.cw_observe import (
            obs_conflict as _oc,
        )
        _oc('gold_delta', _expected, _final_gold, None,
            verdict='留证-动作账vs读数不等(stylized漏读/cost错/未观收入)',
            source='shop_spend_audit',
            plane=_fb_plane_of(_fb_gs), round_num=_fb_round_of(_fb_gs),
            spend=_spend)
    # (`w577_refresh_fee_and_andon/` 执行事实暂存 set_unit_exec_facts 已随
    #  spend_ledger 流写入端退役删除——删除波 1;计划≠尝试可见化的现役
    #  面 = receipts 发射行 extra(plan_truncated/refresh_skipped 结构化
    #  在账,note_shop_action_receipt 写点)。)
    return (
        f'plan 买{total_buy}张 经验{total_xp_buy}击 刷{total_refresh}次 '
        f'卖{total_sell}张(+{total_sell_income}金,'
        f'守卫拦{ledger.total_sell_skip}) '
        f'(gold={_fb_gold_of(_fb_gs)} lv={_fb_level_of(_fb_gs)} '
        f'plane={_fb_plane_of(_fb_gs)})'
    )
