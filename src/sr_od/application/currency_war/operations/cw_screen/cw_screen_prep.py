"""备战执行器 CwScreenPrep:画面执行 / 对账接线 / 商店 obs 依赖面
(refresh 期望态依赖 obs.cw_shop_obs,留 app 合法向)。

期望态计算与对账纯函数在 kernel/cw_prep_expect(共享给 decision);
exec_fail 停机旗标族在 run_state。
"""

from __future__ import annotations

import contextlib
import time
from pathlib import Path
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.kernel.cw_overlay_registry import derive_decision
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    BailToOuter,
    DeferSpheres,
    DeployMove,
    LevelUp,
    OpenShop,
    PrepAction,
    PrepObservation,
    SellBench,
    SellDeployed,
    StartBattle,
    action_key,
)
from sr_od.application.currency_war.kernel.cw_prep_expect import (
    _BUY_DEFECT_KIND,
    _DRAG_DEFECT_KIND,
    _DRAG_DEFECT_SURFACE,
    _EQUIP_DEFECT_KIND,
    _EQUIP_DEFECT_SURFACE,
    _XP_DEFECT_KIND,
    _XP_DEFECT_SURFACE,
    BuyExpect,
    DragExpect,
    EquipDragIntent,
    EquipExpect,
    XpLedger,
    _xp_compare,
    _xp_parse_buy_clicks,
    compare_buy_expect,
    compare_drag_expect,
    compare_equip_expect,
    compute_drag_expect,
    compute_equip_drag_expect,
)
from sr_od.application.currency_war.kernel.cw_state import (
    XP_TO_NEXT_LEVEL,
    BenchChar,
    GameState,
    bench_from_compact,
    same_star_count,
    xp_apply_clicks,
    xp_clicks_to_level,
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
    board_from_tracked,
    read_deploy_cap,
    read_deployed_count,
    read_node_sequence,
)
from sr_od.application.currency_war.obs.cw_shop_obs import (
    RefreshExpect,
    check_shop_pool,
    compare_merge_preview,
    refresh_expect,
)
from sr_od.application.currency_war.prep_actions import (
    PrepActionExecutor,
    row_area_centers,
    try_recovery,
)
from sr_od.application.currency_war.run_state import (
    exec_fail_flag_path,
    exec_fail_should_stop,
    write_exec_fail_flag,
)
from sr_od.application.currency_war.telemetry import (
    defects,
    query,
    recorder,
    schema,
    state,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def prep_obs_actual_for(session, entry, st, obs,
                        bench_ids: str, deployed_ids: str) -> tuple | None:
    """prep_obs 覆盖点单条目实读构造(纯函数,EXPECTED_STATE §2 最大覆盖点;
    缺口件1配套:到账登记区条目的「可信读即清账不 diff」语义在此承载)。

    返回 ``(实读值, 可信)``;None = 该条目本帧不读(不进 actual → 保留)。
    - tracked/merge_group:身份串(比对按身份匹配豁免位移,裁决器语义不变);
    - gold:仅 shop 开态可信(F2/F5 可信门),关态不读;
    - owned / strategy(到账登记区粗粒度条目,值 = 「+N(...)」「已选…」推进
      描述):字段本体确认到账 → 回填条目自身值走相等清账(§3 C 区只清账
      不 diff);本体缺失 → 保留不清(宁缺勿造);
    - pending_reward / xp_ledger:既有口径原样。
    """
    p, kind = entry.path, entry.kind
    if kind in ('tracked', 'merge_group'):
        return (f'{bench_ids}|{deployed_ids}', True)
    if kind == 'gold':
        if not getattr(obs, 'state_gold_trusted', False):
            return None
        g = getattr(st, 'gold', None)
        return (g, g is not None)
    if kind == 'xp_ledger':
        _xp = getattr(st, 'xp_progress', None)
        _lv = int(getattr(st, 'level', 0) or 0)
        return (f'lv{_lv} xp{(_xp[0] if _xp else 0)}',
                bool(_xp) and _lv > 0)
    if kind == 'owned':
        name = (p[len('owned['):-1] if p.startswith('owned[') else '')
        own = getattr(session, 'last_owned_equips', None) or []
        present = name in own
        if '−1' in str(entry.value):
            # 减量条目(穿戴消耗,§3 B-6):登记时件已在场,件消失 = 到账。
            return (entry.value, not present)
        return (entry.value if present else name, present)
    if kind == 'pending_reward':
        return ('sphere' if getattr(obs, 'spheres', None) else 'gone', True)
    if kind == 'strategy':
        # 投资策略确认(active_strategies[N])与巨星/伙伴 chosen_* 本体读。
        if p.startswith('active_strategies['):
            nm = p[len('active_strategies['):-1]
            has = nm in (getattr(session, 'active_strategies', None) or [])
            return (entry.value if has else nm, has)
        v = getattr(session, p, '')
        return (entry.value, bool(v))
    return None


def store_plane_table(sess, seq: list[str], plane: int | None) -> bool:
    """开局帧槽序表的**每位面首帧**写入(ADR-0368)。

    write-once 守卫会使 P1 的 9 槽表整局滞留:进 P2 后 7 槽真值永不落盘 →
    nodes_of_plane / battles_left_p2 / 位面日程真值(cw_plane_table.schedule_of)
    全读错(表「在」但是错的)。按 ``plane_node_table_plane`` 锚定,位面变更即
    重写(位面内恒定语义不变,同位面多次 probe 不覆写);同时 append
    ``plane_lengths_seen``(位面长度真值序列,P3 进表即自适应)。

    返回是否写入(供调用方记日志)。纯 session 写入,无画面依赖,可单测。
    """
    if not seq or plane is None:
        return False
    if getattr(sess, 'plane_node_table_plane', None) == plane:
        return False
    sess.plane_node_table = list(seq)
    sess.plane_node_table_plane = plane
    if sess.plane_lengths_seen is None:
        sess.plane_lengths_seen = []
    sess.plane_lengths_seen.append(len(seq))
    return True



#: 单轮入口开商店收起探针后的落地等待(秒)。背景:战斗胜利后新回合游戏
#: 可能自动开商店(时序竞争),单轮入口收起后需等收起动画落地再观察
#(读互斥:hp/gold 关态可读;原「预收重试窗」随内环 gate 拆除)。
PRECOLLAPSE_RETRY_S: float = 1.0



def _save_buy_evidence(evidence_dir: str, file_tag: str, expect: BuyExpect,
                       mism: list[dict[str, str]], frame: MatLike | None,
                       bench_slots: list[tuple[int, Rect]]) -> list[str]:
    """对账不一致时的现场留证(钩子素材;平时零磁盘写入)。

    落盘两类裁片:①买前商店帧的被买牌裁片(expect.crops——像素级「买了
    什么」证据,比意图对象硬);②定型帧中不一致备战槽的对应裁片(实读
    现场证据)。文件名带 file_tag(位面-轮次)与身份,便于与台账行互查。
    返回落盘路径列表(best-effort:单张失败跳过,不阻塞对账记账)。
    调用方在对账完成后置 ``expect.crops = None`` 释放内存(裁片是拷贝,
    不留整帧,~125KB/张)。
    """
    from one_dragon.utils import cv2_utils
    paths: list[str] = []
    try:
        base = Path(evidence_dir)
        base.mkdir(parents=True, exist_ok=True)
        for name, crop in (expect.crops or []):
            if crop is None:
                continue
            p = base / f'buy_expect_{file_tag}_buy_{name}_{len(paths)}.webp'
            cv2_utils.save_image(crop, str(p))
            paths.append(str(p))
        if frame is not None:
            for m in mism:
                if m['domain'] != 'bench':
                    continue
                slot = int(m['slot'])
                rect = next((r for s, r in bench_slots if s == slot), None)
                if rect is None:
                    continue
                crop = frame[rect.y1:rect.y2, rect.x1:rect.x2]
                p = base / (f'buy_expect_{file_tag}_settle_bench'
                            f'{slot}_{len(paths)}.webp')
                cv2_utils.save_image(crop, str(p))
                paths.append(str(p))
    except Exception:   # noqa: BLE001  留证 best-effort,不阻塞对账记账
        pass
    return paths



# ===== 商店打开态对账(cw_shop_obs 接线;纯记账+对账,零决策行为变更)=====

#: 台账 surface/kind(商店通道;复现计数按 (surface, kind, expected) 分档)。
_SHOP_DEFECT_SURFACE = 'shop'

_SHOP_POOL_DEFECT_KIND = 'shop_pool_violation'

_SHOP_REFRESH_DEFECT_KIND = 'refresh_expect_mismatch'

_SHOP_MERGE_DEFECT_KIND = 'merge_preview_mismatch'



def _shop_pool_inputs(st: GameState) -> tuple[list[tuple[str, int]], int]:
    """商店帧 state.shop → (参评牌列表, 未识别张数)(纯函数)。

    参评 = 有身份牌 ``(name, cost)``;未识别牌(name 空,SIFT miss 占位,
    cost=0)不进 check_shop_pool——空名+0 费会成 invalid_cost 假票,且
    「识别失败」已由置信度通道管辖,此处只计数随 refs 披露。
    """
    shop = list(getattr(st, 'shop', None) or [])
    cards = [(c.name, c.cost) for c in shop if getattr(c, 'name', '')]
    return cards, len(shop) - len(cards)



def _merge_preview_inputs(st: GameState) -> tuple[dict[int, bool], dict[int, bool], int]:
    """商店帧 state → (我方合成旗, 识别读数旗, 未识别张数)(纯函数;
    compare_merge_preview 接线的入参折算单一源)。

    槽位键 = state.shop 列表下标(商店五格物理槽位,0 基左→右;同
    read_shop_cards 顺序,即 cw_shop_obs.compare_merge_preview 的槽位坐标系)。
    - our:``cw_state.same_star_count`` 全场域同名同星持有 >0(合成预览语义
      单一源 = merge_mechanics.md §2.7:✦ 数 = 已持同名同星副本份数;商店牌
      恒 1★,star 兜 1)。bench/deployed 取 state(由 session tracked 播种,
      与卡池票同帧一致)。
    - det:该牌 merge_preview > 0(语义映射:0 是「无副本 ∨
      读不到」双义,映射为 False,our_suspect 祇当对账率归因,不逐票判死)。
    - 未识别牌(name 空,SIFT miss)两侧都算不出 → 不进 compare,只计数
      (同 _shop_pool_inputs 口径:识别失败归置信度通道,此处不评)。
    """
    our: dict[int, bool] = {}
    det: dict[int, bool] = {}
    unnamed = 0
    bench = list(getattr(st, 'bench', None) or [])
    deployed = list(getattr(st, 'deployed', None) or [])
    for i, c in enumerate(list(getattr(st, 'shop', None) or [])):
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

    挂账(producer 集成点):期望必须在**刷新波内**构建——波前金与波前
    面板费都是单元内部现读;cw_screen_prep 持有的 RunBuyPhase 前后帧均为
    关店帧(F2 下金不可信、五格牌不可读),无合法评估窗。集成点 =
    ``operations/cw_op/cw_op_buy_cards.py`` 刷新波现读处(先例 = pending_buy_expect
    同文件暂存、本环 heavy 帧消费);消费判据 = refresh_reconcile_mismatches
    (本文件,真值表已锁),落台账 kind=refresh_expect_mismatch。
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



class CwScreenPrep(SrOperation):
    """备战决策环:观察驱动单步决策,替代 CwScreenPrep 备战单轮 固定序列(P1)。

    单「决策环」节点 + 内部 while;环级预算 MAX_STEPS(步数)与 STALL_LIMIT(零进展)
    兜底强制出战(F5);ping-pong 由外环 MAX_ITER=2000 承担(勿引 node_max_retry —— round_wait
    不消耗 node 重试预算,operation.py:453-461 仅 RETRY 递增;strategy/03 §7)。
    """

    # 环级预算(§7 环级:步数>60 或 stall≥5 且恢复已试尽 → 强制 StartBattle;实跑校准 §10)
    MAX_STEPS: ClassVar[int] = 60
    STALL_LIMIT: ClassVar[int] = 5
    # 同动作验证连败 2 → 恢复原语(一次/动作实例)→ 恢复后仍连败 2 → 分型 bail/屏蔽(§7)
    FAIL_TO_RECOVER: ClassVar[int] = 2
    BAIL_SAME_REASON_DIAG: ClassVar[int] = 3   # 同因 bail ≥3 → [cw!] 升诊断(局级计数)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-备战决策环')
        self._executor: PrepActionExecutor | None = None
        self._steps: int = 0
        self._stall: int = 0
        self._fail_counts: dict[str, int] = {}      # 动作实例键 → 连续验证失败次数
        self._blocked: set[str] = set()             # 本环屏蔽动作实例键(§7;StartBattle 豁免)
        self._recovered: set[str] = set()           # 已试过恢复原语的动作实例键(一次/实例)
        self._recovery_closed_known: dict[str, bool] = {}   # 恢复时是否关过已知弹层(分型用)
        self._recovery_tried: bool = False          # 本环恢复原语是否已试(强制出战门)
        self._bench_pts = []                        # screen_info 槽位中心(首步惰性读)
        # light 步沿用的 heavy 缓存(观察分层)
        self._cached_state: GameState | None = None
        self._cached_bench: list[BenchChar] = []
        self._cached_deployed: list[BenchChar] = []
        self._cached_vacancy: int = 0
        self._cached_gold_trusted: bool = False
        # 购买单元记账态(纯观测;unit_seq 轮内序,
        # 按 _spend_unit_key=(plane, round) 重计,见 _spend_unit_open)
        self._spend_unit_seq: int = 0
        self._spend_unit_key: tuple[int, int] | None = None
        self._unit_meta: dict | None = None
        self._exec_fail_hook_fired: bool = False   # 安灯:每局最多停一次

    # ===== 观察(F2:只由现成 reader 产出)=====

    def _observe(self, heavy: bool, screen: MatLike | None = None) -> PrepObservation:
        """组装备战观察。heavy=True(环入口 + 每个执行过的游戏动作后):SIFT 身份 + GameState
        + cap 全重读;False(控制流/拒绝步后):只现读轻字段,heavy 字段沿用缓存。

        screen 传入时(gate 末帧)复用该帧不重截——gate 稳定帧的全图 OCR 已
        按 id(image) 缓存,本方法所有 crop_first=False 读取(id_mark 判定/
        observe_full)全部缓存命中,heavy 观察的 OCR 成本归零;且观察的就是
        「已验证稳定」的那一帧(gate 语义),而非稳定后又隔一拍的帧。
        """
        # 光标 parking(审计 P0,2026-08-16,用户指示):上个动作(买牌点购买经验/拖拽停目标/
        # 点球)后光标停在点击处,与识别区重叠 → OCR/SIFT 污染(M38 level 毒化根因链)。
        # F1 契约:heavy 在每个执行过的游戏动作后必调 → 此处 park 覆盖全部动作后首读。
        if heavy:
            self.park_cursor()
        screen = screen if screen is not None else self.screenshot()
        obs = PrepObservation()
        if not self._bench_pts:
            self._bench_pts = row_area_centers(self.ctx, '备战栏')
        # 轻:球/箱/典籍/overlay/占用(每步现读)
        obs.spheres = read_reward_spheres(self.ctx, screen)
        obs.boxes = read_supply_boxes(self.ctx, screen)
        obs.tomes = cw_identity_obs_read_tomes(self.ctx, screen)
        obs.shop_open = self.round_by_find_area(
            screen, SHOP_SCREEN_NAME, '按钮-收起', crop_first=False).is_success
        obs.box_overlay_open = self.round_by_find_area(
            screen, '货币战争-备战-武装箱选择', '标识-请选择', crop_first=False).is_success
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
        obs.back_size = len(back_pts)
        obs.front_occupied = {i + 1 for i, p in enumerate(front_pts)
                              if slot_occupied(screen, int(p.x), int(p.y))}
        obs.back_occupied = {i + 1 for i, p in enumerate(back_pts)
                             if slot_occupied(screen, int(p.x), int(p.y))}
        # 重:身份/星级/GameState/cap(环入口 + 结构变化 = 每个执行过的游戏动作)
        if heavy:
            # 可重定位读取(身份/gold==0 重读/substate)进组装层
            # 单一源(observe_full);director 保留副作用编排(session 写/审计/
            # 缓存——单写者原则)。
            from sr_od.application.currency_war.obs.cw_observe_full import (
                observe_full,
            )
            _of = observe_full(self.ctx, screen, tier='heavy',
                               source='director', op=self,
                               shop_open=obs.shop_open)   # F2 门
            templates = ensure_portrait_templates(self.ctx)   # 复用单一源(路径+缓存)
            if templates is not None:
                obs.bench_chars = _of.get('bench_chars') or []
                obs.deployed_chars = _of.get('deployed_chars') or []
                self._reconcile_tracking(obs.bench_chars, obs.deployed_chars, screen)
            else:
                obs.bench_chars = list(self._cached_bench)
                obs.deployed_chars = list(self._cached_deployed)
            st = _of['state']
            session = self._session()
            # shop 关态帧节点行可读 → node_type 真值写 session(商店开态被遮恒 None,
            # plan 路径 boss 判定全死码的根因);仿 last_hp 模式。
            if session is not None and st.node_type:
                session.last_node_type = st.node_type
            st.bench = bench_from_compact(
                list(obs.bench_chars
                     or (session.tracked_bench_chars if session else [])))
            obs.state = st
            obs.state_gold_trusted = obs.shop_open   # F2:gold 仅 shop 开态可信(关态读空)
            if not obs.state_gold_trusted:
                log.debug('[cw][director] heavy 读 state 于 shop 关态 → gold 不可信')
            # gold==0 重读已在 observe_full 内(单一源,防双源易漏同步)
            if session is not None:
                # 单写者语义(hp 双源收口):写
                # last_state 前过 gated_hp(与 shop.py 同门同
                # 单源 helper)——防「director 写门控值 →
                # shop 写现读值」反向翻转(两写者保留
                # (各有上下文)
                # 但**写出的 hp 同源**:结算真值优先,新鲜度
                # 门拒绝陈值。
                _st_t = ((st.plane - 1) * 9 + st.round_num) \
                    if (st.plane and st.round_num) else None
                from sr_od.application.currency_war.decision.cw_strategy import (
                    gated_hp as _gh,
                )
                st.hp = _gh(st.hp, session, _st_t,
                            current_readable=bool(
                                getattr(st, 'hp_readable', True)))
                session.last_state = st
                # 期望态覆盖点·备战观察(EXPECTED_STATE §2 最大覆盖点):
                # tracked/xp/owned 族实读确认清账;可信门(F5)= gold 仅 shop
                # 开态可信(obs.state_gold_trusted),不可信读数不进 actual →
                # 期望条目保留不清账。hp 族归 reconcile_hp 单源门(不在此列)。
                # 全程 best-effort,失败不阻塞环。
                try:
                    from sr_od.application.currency_war.kernel.cw_expected_state import (
                        reconcile_expected,
                    )
                    _ids = ' | '.join(
                        f'{bc.char_id}@{bc.star}★'
                        for bc in (obs.bench_chars or [])
                        if getattr(bc, 'char_id', ''))
                    _dids = ' | '.join(
                        f'{bc.char_id}@{bc.star}★'
                        for bc in (obs.deployed_chars or [])
                        if getattr(bc, 'char_id', ''))
                    _act: dict = {}
                    for _p, _e in list(
                            (getattr(session, 'expected_state', None)
                             or {}).items()):
                        if _e.confirm_point != 'prep_obs':
                            continue   # 条目绑覆盖点(F7):不可确认点透传
                        _r = prep_obs_actual_for(session, _e, st, obs,
                                                 _ids, _dids)
                        if _r is not None:
                            _act[_p] = _r
                    reconcile_expected(session, 'prep_obs', _act)
                except Exception as _e:  # noqa: BLE001  观测面不阻塞环
                    log.debug(f'[cw-director] expected reconcile skip: {_e}')
            # substate 消费:observe_full 的可读性
            # 标注落 PrepObservation(下游对账/日志可判;轻步
            # 沿用缓存,同 _cached_state 语义)。
            obs.substate = _of.get('substate') or {}
            # ⚠ 以下 cap/双源审计用 heavy 段
            # 开头的旧 screen,而 st 可能来自 gold 重读的 0.3-0.9s
            # 后异帧——跨帧对拍在轮转动画窗内可假分歧(低概率,
            # 留证非阻塞);重读仅在 shop 开态,窗口缩小。
            cap = read_deploy_cap(self.ctx, screen)
            # 观察冲突审计 #15(2026-08-16;⚠ 2026-08-22 两段反转,ADR-0220+用户点题;
            # 2026-08-23 ADR-0281 再适配):财富宝钻官方效果「拥有即可使团队规模
            # 上限+1,无论是否被角色穿戴」可叠加(局38 r2 实证 cap5/lv3=两宝钻)。
            # 布局与 cap 无关(ADR-0281:level 驱动)后本检查只剩:
            # - cap < level → 不可能(读错/毒化)→ 留证(三源网 M38 天敌);
            # - cap ≥ level → 合法(cap>level=宝钻叠加,debug 记宝钻数)。
            if cap is not None and cap < st.level:
                from sr_od.application.currency_war.kernel.cw_observe import (
                    obs_conflict,
                )
                obs_conflict('deploy_cap_vs_level', st.level, cap, screen,
                             verdict=('留证-cap<level不可能(cap或level读错;'
                                      '处理:看截图读「区域-部署数」X/Y 原文核 X>Y guard '
                                      '是否该拒,level 查 XP 反推是否一致;'
                                      '确认 reader 缺陷则修 read_deploy_cap/level 守卫;'
                                      '单次按 OCR 噪声忽略,复现 ≥3 次才排期)'),
                             source='paddle_cap')
            elif cap is not None:
                # ADR-0385:cap>level(宝钻/钻石叠加)不只
                # 是经济信息——口述
                # 公式「后台格数 = 6+(cap−level)」使 cap 差直接驱动布局选档
                # (cw_back_layout.select_back_layout,含 7 格未建档留证)。
                # cap==level 是常态(无宝钻),别打
                # "宝钻×0"误导判读;仅真叠加(cap>level)才记
                if cap > st.level:
                    log.debug('[cw][obs] cap=%d(宝钻×%d 叠加,合法;后排扩展 +%d 格)',
                              cap, cap - st.level, cap - st.level)
            dep_n = read_deployed_count(self.ctx, screen)
            if cap is not None and dep_n is not None:
                obs.deploy_vacancy = max(0, cap - dep_n)
            else:
                obs.deploy_vacancy = self._cached_vacancy
            # deployed 总数双源对拍(同帧全齐):paddle X(读 deployed_count)
            # vs CV 占用(front+back)。
            # ⚠️ board 的 X 是「该阵营在场人数」非「角色数」——
            # 一个角色贡献多阵营(藿藿=仙舟+治疗,4 人可贡献 11 阵营次),
            # board_sum 系统性 ≥ 部署数,board 根本给不出角色数 →
            # **移出对拍**,对拍保持双源(paddle X vs CV 占用)。
            _cv_occ = len(obs.front_occupied) + len(obs.back_occupied)
            if dep_n is not None:
                _spread = abs(dep_n - _cv_occ)
                if _spread > 1:
                    from sr_od.application.currency_war.kernel.cw_observe import (
                        obs_conflict,
                    )
                    obs_conflict('deployed_count_2src',
                                 {'paddle_x': dep_n, 'cv_occupied': _cv_occ},
                                 'spread>1', screen,
                                 verdict=('留证-双源分歧(处理:看截图数前排+后排占用实数,'
                                          '与 paddle X 对拍;哪源对修哪源——paddle 对→CV '
                                          '阈值/遮挡误漏,CV 对→X/Y 拆框;'
                                          '单次按噪声忽略,同局 ≥3 次排期修)'),
                                 source='director_heavy')
            # 更新 light 沿用缓存(trusted 位随 state 缓存,MED-1 —— light 步不重判 shop 态,
            # 缓存 state 生成时的可信度就是它的可信度)
            self._cached_state = st
            self._cached_bench = list(obs.bench_chars)
            self._cached_deployed = list(obs.deployed_chars)
            self._cached_vacancy = obs.deploy_vacancy
            self._cached_gold_trusted = obs.state_gold_trusted
        else:
            # light:heavy 字段沿用缓存(上次真读值;不恒默认防永动机)
            obs.state = self._cached_state
            obs.state_gold_trusted = self._cached_gold_trusted   # MED-1:trusted 位随缓存 state
            obs.bench_chars = list(self._cached_bench)
            obs.deployed_chars = list(self._cached_deployed)
            obs.deploy_vacancy = self._cached_vacancy
        # 黑板写路径(W971 §2,P2):备战观察结果直写 session(写者白名单 =
        # 本装配点;读者 = decide_prep_screen)。离线契约:无 match(局外
        # 单跑/mock)不写。帧对象原样入 session(实现决策:容器形态,
        # 逐字段扇出归 P3,见 cw_strategy_session.prep_obs_frame 注)。
        _sess = self._session()
        if _sess is not None:
            _sess.prep_obs_frame = obs
        return obs

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

    def _reconcile_drag_expect(self, expect: DragExpect) -> None:
        """拖动期望态对账(动作完成后调用;零决策行为变更:不一致仅落台账)。

        读法:复用动作后 heavy 重观察的定型帧(``last_screenshot``,零新增
        截屏);身份读走 identify_slots 纯读组合(**不经 read_bench_chars**
        ——后者内置召唤物/书册卡停机钩子,动画帧误触停机即违背本对账零
        行为约束;先例=观测自检框架 §2.2 身份回读)。deployed 排复用
        read_deployed_chars(其挂点均为留证级非停机,且后排布局选档单一源)。
        全部 best-effort:任一环节失败静默跳过(宁缺勿造)。
        """
        try:
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return
            templates = ensure_portrait_templates(self.ctx)
            if templates is None:
                return
            from sr_od.application.currency_war.obs.cw_identity_obs import (
                _ctx_slots,
                identify_slots,
                read_deployed_chars,
            )
            bench_read = identify_slots(
                frame, templates, _ctx_slots(self.ctx, '备战栏', 9), '')
            deployed_read = read_deployed_chars(self.ctx, frame, templates)
            mism = compare_drag_expect(expect, bench_read, deployed_read)
            if not mism:
                return
            obs_st = self._cached_state
            exp_txt = (f'{expect.kind} identity={expect.identity} '
                       f'from_slot={expect.from_slot}'
                       + (f' target={expect.target_row}{expect.target_slot}'
                          f'/{expect.target_kind}' if expect.kind == 'deploy_move' else ''))
            obs_txt = ';'.join(f"{m['domain']}槽{m['slot']} 期望[{m['expected']}] "
                               f"实读[{m['observed']}]" for m in mism)
            defects.record_defect(
                _DRAG_DEFECT_SURFACE, _DRAG_DEFECT_KIND,
                expected=exp_txt, observed=obs_txt,
                plane=int(getattr(obs_st, 'plane', 0) or 0),
                round_num=int(getattr(obs_st, 'round_num', 0) or 0),
                gap_large=True,
                verdict=('留证-拖动后期望态与定型帧实读不一致(身份未识别槽不评;'
                         '单次 L1,复现自动升 L0,停线由分级安灯承接;本对账'
                         '零决策行为,不 return/不重拖)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('kind', expect.kind), ('identity', expect.identity),
                    ('from_slot', str(expect.from_slot)),
                    ('target_row', expect.target_row),
                    ('target_slot', str(expect.target_slot)),
                    ('target_kind', expect.target_kind))],
                reader_source='drag_expect_reconcile',
                note='期望态层:期望=动作意图纯函数,与 W512 paddle 动作级对拍分立(身份级 vs 计数级)')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] drag_expect reconcile skip: {e}')

    def _reconcile_buy_expect(self, expect: BuyExpect) -> None:
        """买牌期望态对账(RunBuyPhase 完成后调用;零决策行为变更:不一致仅落台账)。

        读法与 _reconcile_drag_expect 同款:复用 heavy 定型帧(last_screenshot,
        零新增截屏)+ identify_slots/read_deployed_chars 纯读组合(不经
        read_bench_chars 停机钩子)。全部 best-effort:任一环节失败静默跳过
        (宁缺勿造)。低置信子案(满栏自动多买)不一致照常落账——对账不一致
        =证据,如实落台账不改语义(merge_mechanics §2.5 声明由对账实证修正)。
        """
        try:
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return
            templates = ensure_portrait_templates(self.ctx)
            if templates is None:
                return
            from sr_od.application.currency_war.obs.cw_identity_obs import (
                _ctx_slots,
                identify_slots,
                read_deployed_chars,
            )
            bench_read = identify_slots(
                frame, templates, _ctx_slots(self.ctx, '备战栏', 9), '')
            deployed_read = read_deployed_chars(self.ctx, frame, templates)
            mism = compare_buy_expect(expect, bench_read, deployed_read)
            if not mism:
                return
            obs_st = self._cached_state
            exp_txt = (f'buy {expect.summary} 总价{expect.total_cost}'
                       + ('(低置信:满栏自动多买)' if expect.low_confidence else ''))
            obs_txt = ';'.join(f"{m['domain']}槽{m['slot']} 期望[{m['expected']}] "
                               f"实读[{m['observed']}]" for m in mism)
            # 现场留证(仅不一致时落盘,平时零磁盘写入):买前商店牌裁片
            # (像素级「买了什么」证据)+ 定型帧不一致备战槽裁片;落在台账
            # 回放目录(与 defect_ledger 同域)。file_tag=位面-轮次 便于互查。
            evidence: list[str] = []
            try:
                _rec = state.get_recorder()
                _dir = getattr(_rec, 'replay_dir', None) if _rec else None
                if _dir:
                    _tag = (f"p{int(getattr(obs_st, 'plane', 0) or 0)}"
                            f"-r{int(getattr(obs_st, 'round_num', 0) or 0)}")
                    evidence = _save_buy_evidence(
                        str(_dir), _tag, expect, mism, frame,
                        _ctx_slots(self.ctx, '备战栏', 9))
            except Exception:   # noqa: BLE001  留证 best-effort
                evidence = []
            defects.record_defect(
                _DRAG_DEFECT_SURFACE, _BUY_DEFECT_KIND,
                expected=exp_txt, observed=obs_txt,
                plane=int(getattr(obs_st, 'plane', 0) or 0),
                round_num=int(getattr(obs_st, 'round_num', 0) or 0),
                gap_large=True,
                verdict=('留证-买牌后期望态与定型帧实读不一致(仅评增量槽;'
                         '身份未识别槽不评;单次 L1,复现自动升 L0,停线由'
                         '分级安灯承接;本对账零决策行为,不 return/不重买)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('summary', expect.summary),
                    ('total_cost', str(expect.total_cost)),
                    ('low_confidence', str(expect.low_confidence)),
                    ('changed_bench', ','.join(map(str, expect.changed_bench))),
                    ('changed_deployed', ','.join(map(str, expect.changed_deployed))),
                    ('evidence', ';'.join(evidence)))],
                shot=evidence[0] if evidence else None,
                reader_source='buy_expect_reconcile',
                note='期望态层·买牌:期望=购买意图纯函数(落点规则单一源 '
                     'cw_state._merge_bench),与拖动通道 intent_state_mismatch 分立')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] buy_expect reconcile skip: {e}')
        finally:
            expect.crops = None   # 对账完成即释放裁片拷贝(内存,~125KB/张)

# ===== 经验期望态账本(纯记账+对账,零决策行为变更)=====

    def _xp_ledger(self) -> XpLedger | None:
        """会话级账本取存(动态属性挂 StrategySession——pending_buy_expect
        同款先例;session 每局新建 → 账本天然局级生命周期,跨局零残留)。"""
        session = self._session()
        if session is None:
            return None
        led = getattr(session, 'xp_expect_ledger', None)
        if led is None:
            led = XpLedger()
            session.xp_expect_ledger = led
        return led

    def _xp_apply_levelup(self) -> None:
        """直接 LevelUp 动作通道推进账本(腾席链「循环点至 level+1、首次
        OCR 验证成功即停」;仅 progressed 调用 = 升级已验证达成,实际击数
        = xp_clicks_to_level 最小击数,无超额点击)。未锚定 → 丢弃(对局
        首帧锚定前的意图不推算,由锚点吸收)。"""
        led = self._xp_ledger()
        if led is None or not led.anchored:
            return
        clicks = xp_clicks_to_level(led.level, led.xp_cur)
        if clicks <= 0:
            return
        led.level, led.xp_cur = xp_apply_clicks(led.level, led.xp_cur, clicks)
        led.xp_next = XP_TO_NEXT_LEVEL.get(led.level, led.xp_cur)
        led.pending_clicks += clicks
        led.events_txt += f'+LevelUp×{clicks}(至{led.level}级)'

    def _xp_apply_buy_clicks(self, detail: str) -> None:
        """RunBuyPhase 通道推进账本:执行 detail 解析升级次数(执行侧实况
        计数,shop.py total_level 口径;调用方仅 progressed 分支——单元
        失败=未购买不推算)。已知盲区:shop._handle_bench_full 席满急救的
        盲击购买经验不经单元摘要 → 不在账,该形态的不一致是本对账的预期
        留证对象(verdict 注明,不改语义)。未锚定 → 丢弃(同上)。"""
        led = self._xp_ledger()
        if led is None or not led.anchored:
            return
        clicks = _xp_parse_buy_clicks(detail)
        if clicks <= 0:
            return
        led.level, led.xp_cur = xp_apply_clicks(led.level, led.xp_cur, clicks)
        led.xp_next = XP_TO_NEXT_LEVEL.get(led.level, led.xp_cur)
        led.pending_clicks += clicks
        led.events_txt += f'+buy×{clicks}击'

    def _reconcile_xp_expect(self, obs: PrepObservation) -> None:
        """备战稳定帧经验对账(heavy 帧消费;零决策:不一致仅落缺陷台账,
        不 return/不重买)。段语义见 XpLedger:轮界重锚(外生经验吸收并
        披露)/锚定前不对账/同段有未对账购买意图才评;display 或 level
        失读 → 保 pending 不评下帧重试(宁缺勿造)。全程 best-effort。"""
        try:
            led = self._xp_ledger()
            st = obs.state
            if led is None or st is None:
                return
            display = getattr(st, 'xp_progress', None)
            level_obs = int(getattr(st, 'level', 0) or 0)
            key = (int(getattr(st, 'plane', 0) or 0),
                   int(getattr(st, 'round_num', 0) or 0))
            if not led.anchored:
                if display is not None and level_obs > 0:
                    led.level, led.xp_cur = level_obs, display[0]
                    led.xp_next = display[1]
                    led.anchored = True
                    led.round_key = key
                    led.pending_clicks = 0
                    led.events_txt = ''
                return
            if led.round_key != key:
                # 轮界重锚:外生经验流(轮奖励/位面过渡,未建模)吸收进锚点;
                # 同级同门槛帧才把差值记入 exogenous_xp(异级差值不可分,不记)。
                if display is not None and level_obs > 0:
                    if led.level == level_obs and display[1] == led.xp_next:
                        led.exogenous_xp += max(0, display[0] - led.xp_cur)
                    led.level, led.xp_cur = level_obs, display[0]
                    led.xp_next = display[1]
                    led.round_key = key
                    led.pending_clicks = 0
                    led.events_txt = ''
                return
            if led.pending_clicks <= 0:
                return
            mism = _xp_compare(led, display, level_obs)
            clicks = led.pending_clicks
            events = led.events_txt
            led.pending_clicks = 0
            led.events_txt = ''
            if not mism:
                return
            obs_txt = ';'.join(f"{m['domain']}/{m['slot']} "
                               f"期望[{m['expected']}] 实读[{m['observed']}]"
                               for m in mism)
            defects.record_defect(
                _XP_DEFECT_SURFACE, _XP_DEFECT_KIND,
                expected=(f'lv{led.level} xp {led.xp_cur}/{led.xp_next}'
                          f'(账本;events={events or "本段"})'),
                observed=(f'lv{level_obs} xp '
                          + (f'{display[0]}/{display[1]}' if display else '失读')
                          + (f';{obs_txt}' if obs_txt else '')),
                plane=key[0], round_num=key[1],
                gap_large=True,
                verdict=('留证-买经验后期望账本与显示读数不一致(零决策记账;'
                         '已知盲区=shop 席满急救盲击购买经验不经账,该形态为'
                         '预期留证;单次 L1,复现升 L0 由分级安灯承接)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('pending_clicks', str(clicks)), ('events', events))],
                reader_source='xp_expect_reconcile',
                note='期望态层·经验:期望=锚点读数+购买意图纯函数推进'
                     '(XP_TO_NEXT_LEVEL 结转),与买牌/拖动通道分立')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] xp_expect reconcile skip: {e}')

    def _reconcile_faction_display(self, obs: PrepObservation) -> None:
        """备战稳定帧羁绊显示对账(cw_faction_obs 接线;零决策:不一致仅落
        缺陷台账,不纠漂不重读——羁绊状态以计算侧为主源,显示只作对账票)。

        computed 侧 = ``board_from_tracked``(session tracked_deployed,全集
        主源;None=含未知身份算不出 → 宁缺勿造跳过);显示侧 = 左侧羁绊面板
        OCR(cw_faction_obs.read_displayed_factions,只读可视条目)。截断/
        OCR 失读/残名按 cw_faction_obs 口径不评不判错,仅计数随 refs 披露;
        ``computed_missing`` 形态(compare 第四态)同为留证不判错,
        report_faction_reconcile 只转发 mismatch 行。节奏 = 与
        _reconcile_xp_expect 同款 heavy 定型帧消费,全程 best-effort。
        """
        try:
            session = self._session()
            if session is None:
                return
            computed = board_from_tracked(
                list(getattr(session, 'tracked_deployed', None) or []))
            if computed is None:
                return
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return
            reading = read_displayed_factions(self.ctx, frame)
            result = compare_factions(computed, reading.entries,
                                      reading.unreadable)
            st = obs.state
            plane = int(getattr(st, 'plane', 0) or 0)
            round_num = int(getattr(st, 'round_num', 0) or 0)
            if result.mismatch_count <= 0:
                # 不一致为零也留一条 debug(含不评口径计数),频率统计靠台账
                # 数据说话,不在此落账
                log.debug(f'[cw][director] faction_display reconcile: '
                          f'ok({len(result.rows)}行) '
                          f'ocr_skip={len(result.ocr_skipped)} '
                          f'trunc_suspect={len(result.truncation_suspects)} '
                          f'computed_missing='
                          f'{sum(1 for r in result.rows if r.verdict == "computed_missing")}')
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
        = 牌识别错或等级读错的强证据。节奏 = 与 _reconcile_xp_expect
        同款 heavy 定型帧消费,全程 best-effort。
        """
        try:
            st = obs.state
            if st is None or not obs.shop_open:
                return
            cards, unnamed = _shop_pool_inputs(st)
            if not cards:
                return
            violations = check_shop_pool(cards, int(st.level or 0), None)
            if not violations:
                return
            obs_txt = ';'.join(f'{v.name}/{v.cost}:{v.kind}({v.detail})'
                               for v in violations)
            defects.record_defect(
                _SHOP_DEFECT_SURFACE, _SHOP_POOL_DEFECT_KIND,
                expected='0 违例(五牌两查)',
                observed=obs_txt,
                plane=int(getattr(st, 'plane', 0) or 0),
                round_num=int(getattr(st, 'round_num', 0) or 0),
                gap_large=True,
                verdict=('留证-商店牌卡池一致性违例(tier_locked=该费用档本'
                         '等级概率为0,牌识别错或等级读错;invalid_cost=费用'
                         'OCR误读。pool_state 无账本传 None,池守恒查如实'
                         '降级未做;零决策记账,单次 L1,复现升 L0 由分级'
                         '安灯承接)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('level', str(int(st.level or 0))),
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
            st = obs.state
            if st is None or not obs.shop_open:
                return
            our, det, unnamed = _merge_preview_inputs(st)
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
                plane=int(getattr(st, 'plane', 0) or 0),
                round_num=int(getattr(st, 'round_num', 0) or 0),
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

    # ===== 装备期望态对账(纯记账+对账,零决策行为变更)=====
    # 语义单一源 = docs/game/currency_war/research/equipment_mechanics.md §1.1
    # (两件简易必合成无共存 28/28 配方实证 / 角色装备上限 3 件 / 合成落点 =
    # 角色最左简易槽 / 装备不堆叠每格一件 / 卖角色=装备全量回装备区;
    # 唯一件=待确认项,本批不建模)。合成规则单一源 = cw_synthesis
    # (synthesize_target/self_advance,图谱派生自注册表,勿自造第二套)。
    # 架构与买牌/拖动/经验通道同构:动作意图 →
    # 期望增量(纯函数)→ heavy 定型帧实读(read_equip_grid 逐格三态)比对
    # → 不一致落缺陷台账;一致/不可评不打扰。遮挡格按三态如实跳过
    # (不评不算错);穿戴侧(read_equipped_below)精度未验证,按不评口径
    # (失读/空读一律不建期望,宁缺勿造)。

    def _equip_expect_for_sell(self, action: SellDeployed) -> EquipExpect | None:
        """卖上阵角色 → 「装备全量回装备区」期望(equipment_mechanics §1.1)。

        已穿装备读 = read_equipped_below(below-avatar TM;精度未验证——
        按不评口径:空读/失读/坐标缺失一律 None 不评,不发明期望);
        装备区 before 快照 = 同帧 read_equip_grid 非遮挡占用计数(遮挡格
        进快照会污染 after 对账基准 → 有遮挡即不评)。全程 best-effort。
        """
        try:
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return None
            from sr_od.application.currency_war.obs.cw_back_layout import (
                select_back_layout,
            )
            from sr_od.application.currency_war.obs.cw_equipment import (
                ensure_equip_sift_templates,
                ensure_equip_tm_templates,
                read_equip_grid,
                read_equipped_below,
            )
            grays = ensure_equip_tm_templates(self.ctx)
            templates = ensure_equip_sift_templates(self.ctx)
            if grays is None or templates is None:
                return None
            if action.row == 'front':
                prefix, n = '前排', 4
            else:
                n, prefix = select_back_layout(self.ctx, frame)
            from sr_od.application.currency_war.obs.cw_identity_obs import (
                _ctx_slots,
                avatar_to_below,
            )
            rect = next((r for i, r in _ctx_slots(self.ctx, prefix, n)
                         if i == action.slot), None)
            if rect is None:
                return None
            equipped = read_equipped_below(
                frame, grays, [(action.slot, avatar_to_below(rect))]
            ).get(action.slot, [])
            if not equipped:
                return None   # 未穿/穿戴读失读:无可评增量,不评
            # 前置契约:帧 = 决策环定型截图(gate stable 已判「货币战争-备战」)。
            # 干净备战判定在外层画面识别层,read_equip_grid 不再自带遮挡守卫。
            cells = read_equip_grid(frame, templates)
            before: dict[str, int] = {}
            for c in cells:
                if c.name is not None:
                    before[c.name] = before.get(c.name, 0) + 1
            return compute_equip_drag_expect(
                EquipDragIntent(kind='sell_char', source_name='',
                                equipped_names=tuple(sorted(equipped))), before)
        except Exception:   # noqa: BLE001  期望构建 best-effort,不阻塞环
            return None

    def _reconcile_equip_expect(self, expect: EquipExpect) -> None:
        """装备期望态对账(heavy 定型帧消费;零决策:不一致仅落缺陷台账,
        不 return/不重拖)。读法 = read_equip_grid 纯读逐格分类(占用/空两态),
        复用本轮 heavy 定型帧(last_screenshot,零新增截屏)。全程 best-effort。
        前置契约:定型帧经 gate stable 判「货币战争-备战」;干净判定在外层画面
        识别层,read_equip_grid 不再自带遮挡守卫。
        """
        try:
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return
            from sr_od.application.currency_war.obs.cw_equipment import (
                ensure_equip_sift_templates,
                read_equip_grid,
            )
            templates = ensure_equip_sift_templates(self.ctx)
            if templates is None:
                return
            cells = read_equip_grid(frame, templates)
            mism = compare_equip_expect(expect, cells)
            if not mism:
                return
            obs_st = self._cached_state
            obs_txt = ';'.join(f"{m['slot']} 期望[{m['expected']}] "
                               f"实读[{m['observed']}]" for m in mism)
            defects.record_defect(
                _EQUIP_DEFECT_SURFACE, _EQUIP_DEFECT_KIND,
                expected=f'equip {expect.summary}',
                observed=obs_txt,
                plane=int(getattr(obs_st, 'plane', 0) or 0),
                round_num=int(getattr(obs_st, 'round_num', 0) or 0),
                gap_large=True,
                verdict=('留证-装备拖拽期望态与装备区实读不一致(穿戴读精度未验证'
                         '按不评口径;equip=中决策相关面,'
                         '单次 L2 初判,复现升 L1;本对账零决策行为,'
                         '不 return/不重拖)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('kind', expect.kind), ('summary', expect.summary),
                    ('product', expect.product),
                    ('deltas', ';'.join(f'{k}:{v:+d}'
                                        for k, v in expect.deltas.items())))],
                reader_source='equip_expect_reconcile',
                note='期望态层·装备:期望=拖拽意图纯函数(equipment_mechanics '
                     '§1.1;合成单一源 cw_synthesis),与买牌/拖动/经验通道分立')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] equip_expect reconcile skip: {e}')

    def _session(self):
        match = getattr(self.ctx, 'cw_match', None)
        return match.session if (match is not None and match.session is not None) else None

    def _match(self):
        return getattr(self.ctx, 'cw_match', None)

    # ===== 备战单轮 op(W971 P3b 返工定稿:拆内环,op 生命周期五段化)=====
    # 外循环(cw_loop)是唯一循环:备战画面在 → 外循环每轮调本 op 一轮。
    # 单轮 = ①数据观察(heavy→写 session)②对账(观察 vs session 历史/上轮
    # 期望)③决策 ④期望态计算 ⑤执行+结束判定 → 交回外循环。原内环机制
    # (步数预算/stall 门/连败→恢复→屏蔽/bail 同因计数/ping-pong 停机)随
    # 内环拆除——稳定性由外循环每轮重识别保证(特效帧/overlay 弹出在轮间
    # 自然可见);无进展留证归外循环 stall 防线(cw_loop 备战分支)。

    @operation_node(name='备战单轮', is_start_node=True)
    def run(self) -> OperationRoundResult:
        match = self._match()
        if match is None or match.strategy is None:
            return self.round_fail(status='无 cw_match(对局未初始化)')
        session = match.session
        self._executor = PrepActionExecutor(self, self.ctx)
        self._cached_state = None
        self._cached_bench = []
        self._cached_deployed = []
        self._cached_vacancy = 0
        self._cached_gold_trusted = False
        # 购买单元序按 (plane, round) 键在 _spend_unit_open 内重计(ADR-0514);
        from sr_od.application.currency_war.currency_war_config import (
            CurrencyWarConfig,
        )
        config = CurrencyWarConfig(self.ctx.current_instance_idx)

        # —— ① 数据观察:清场 + 开商店合法态收起(读互斥:hp 关态可读)→ heavy 全量观察写 session
        self._clear_entry_overlays()
        self._try_collapse_open_shop()
        obs = self._observe(heavy=True)
        if obs.event_overlay is not None:
            # overlay 在场 → 交回外循环重识别分发(无计数;对应 loop 0x 分支/op 接管)
            log.info(f'[cw][director] 事件 overlay({obs.event_overlay})→ 交回外循环分发')
            return self.round_success(f'事件overlay({obs.event_overlay})交回外循环分发', wait=0.8)
        # 接管局补采(W971 §2.1,挂点随单轮观察段平移;详见块内注释)
        _tk = self._takeover_collect_if_needed(match, session)
        if _tk is not None:
            return _tk
        # —— ② 对账段:本轮 heavy 观察 vs session 历史/上轮期望(acct 空 = 无新执行动作,
        #      仅消费 pending_buy_expect + 经验/羁绊/商店池/合成预览留证族)
        self._v2_post_frame_accounting(obs, {'key': None, 'progressed': False,
                                             'drag_expect': None, 'equip_expect': None,
                                             'dep_delta': 0, 'dep_pre': None,
                                             'unit_open': False}, session)
        # —— 决策前置:席满破墙(M16,保留)→ 方向层/gated_hp/update_target(幂等键守卫)
        _bf = self._bench_full_break_round(match, session, obs, config)
        if _bf is not None:
            return _bf
        if obs.state is not None:
            from sr_od.application.currency_war.decision.cw_strategy import gated_hp
            from sr_od.application.currency_war.decision.decision_v2.prep_brain import (
                committed_from,
                drive_intention,
            )
            _os = obs.state
            # 方向层接管(P7 驱动点契约):意向状态机每 game-round 恰一次;
            # 段级重入守卫 = v3_intention_key(双驱动幂等,单轮每轮调不重复驱动)。
            try:
                drive_intention(_os, session)
            except Exception as e:  # noqa: BLE001  方向驱动失败不阻塞步级决策
                log.warning(f'[cw!][director] 意向驱动异常(沿用旧方向): {e}')
            # dual 态拷回(读端 = R1 唯一合法读端 committed_from)
            _os.dual_track_phase = not committed_from(session, _os)
            _os_t = ((_os.plane - 1) * 9 + _os.round_num) if (_os.plane and _os.round_num) else None
            _os.hp = gated_hp(_os.hp, session, _os_t,
                              current_readable=bool(getattr(_os, 'hp_readable', True)))
        try:
            match.strategy.update_target(obs.state or GameState(), session, config)
        except Exception as e:  # noqa: BLE001  战略层失败不阻塞步级决策
            log.warning(f'[cw!][director] update_target 异常(沿用旧 target): {e}')
        # —— ③ 决策(黑板:读 session.prep_obs_frame,写者 = 本 op 观察段/破墙派生帧)
        try:
            action = match.strategy.decide_prep_screen(session, config)
        except Exception as e:  # noqa: BLE001  策略异常 = 本轮 fail(外循环 retry 链兜)
            log.warning(f'[cw!][director] decide_prep_screen 异常: {e}')
            return self.round_fail(status=f'策略决策异常: {e}')
        if not isinstance(action, PrepAction):
            log.warning(f'[cw!][director] 策略输出非 PrepAction: {type(action).__name__}')
            return self.round_fail(status='策略输出非 PrepAction(F3)')
        self._record_step(obs, action)
        # 控制流(词表退役过渡):球留置 = 空动作表达(交回外循环,不计任何内环计数)
        if isinstance(action, DeferSpheres):
            session.defer_count += 1
            log.info(f'[cw][director] DeferSpheres(defer={session.defer_count})→ 交回外循环')
            return self.round_success('球留置(空动作),交回外循环', wait=1.0)
        if isinstance(action, BailToOuter):
            # 词表已退役(W971 §2.6.1);防御性兜底 = 原样交回(无计数)
            log.info(f'[cw][director] BailToOuter({action.reason})→ 交回外循环(词表退役兜底)')
            return self.round_success(f'BailToOuter({action.reason}),交回外循环(词表退役兜底)', wait=1.0)
        # F3 校验(非法:拒绝执行 + 交回留证)
        err = self._executor.validate(action)
        key = action_key(action)
        if err is not None:
            log.warning(f'[cw!][director] 参数非法 {key}: {err} → 拒绝,交回外循环留证')
            return self.round_success(f'参数非法 {key}:{err},交回外循环留证', wait=1.0)
        # —— ④ 期望态计算(动作发出点;None=无法建真值不评)+ 执行前置记账
        _drag_expect = None
        if isinstance(action, (SellBench, DeployMove)):
            _drag_expect = compute_drag_expect(
                action, obs.bench_chars, obs.deployed_chars)
        _equip_expect = None
        if isinstance(action, SellDeployed):
            _equip_expect = self._equip_expect_for_sell(action)
        _dep_delta = 0
        _dep_pre: int | None = None
        if isinstance(action, (DeployMove, SellDeployed)):
            _dep_delta = 1 if isinstance(action, DeployMove) else -1
            _dep_frame = getattr(self, 'last_screenshot', None)
            if _dep_frame is not None:
                try:
                    _dep_pre = read_deployed_count(self.ctx, _dep_frame)
                except Exception:   # noqa: BLE001  观测 best-effort
                    _dep_pre = None
        acct: dict = {'last_obs': obs, 'key': key, 'progressed': False,
                      'drag_expect': _drag_expect, 'equip_expect': _equip_expect,
                      'dep_delta': _dep_delta, 'dep_pre': _dep_pre, 'unit_open': False}
        # —— ⑤ 执行 + 结束判定(OpenShop = 流程层商店编排;其余经执行器 F3 验证链)
        if isinstance(action, OpenShop):
            _unit = not action.read_only
            if _unit:
                self._spend_unit_open(obs)
            try:
                progressed, detail = self._open_shop_phase(action, obs)
            except Exception as e:
                if _unit:
                    self._spend_unit_close(progressed=False, detail=f'执行异常:{e}',
                                           boundary='aborted')
                log.warning(f'[cw!][director] 执行异常 {key}: {e}')
                return self.round_fail(status=f'执行异常 {key}: {e}')
            if _unit:
                self._spend_unit_close(progressed=progressed, detail=detail,
                                       boundary='closed' if progressed else 'failed')
            if progressed:
                self._xp_apply_buy_clicks(detail)
            log.info(f'[cw][director] {key} → {"✓" if progressed else "✗"} {detail}')
        else:
            try:
                progressed, detail = self._executor.execute(action)
            except Exception as e:  # noqa: BLE001  执行异常上抛 = 本轮 fail
                log.warning(f'[cw!][director] 执行异常 {key}: {e}')
                return self.round_fail(status=f'执行异常 {key}: {e}')
            log.info(f'[cw][director] {key} → {"✓" if progressed else "✗"} {detail}')
            if progressed and isinstance(action, LevelUp):
                self._xp_apply_levelup()
        acct['progressed'] = progressed
        # 执行后对账 + 期望态消费(heavy 重观察帧;单轮内一次,交回前完成)
        _post_obs = self._observe(heavy=True)
        self._v2_post_frame_accounting(_post_obs, acct, session)
        # —— 结束判定 → 交回外循环(DD-011 等待已由执行器/编排内建;外循环下轮重识别)
        if isinstance(action, StartBattle) and progressed:
            return self.round_success('出战(交回外循环战斗分支)', wait=3)
        if not progressed:
            # 验证失败:恢复原语一次(关已知弹层)→ 交回外循环(无内环屏蔽/计数;
            # 连续无进展由外循环 stall 防线留证)
            try:
                _prim, _closed = try_recovery(self, self.ctx)
                log.info(f'[cw][director] {key} 验证失败 → 恢复原语({_prim})→ 交回外循环')
            except Exception as e:  # noqa: BLE001  恢复异常不阻塞交回
                log.warning(f'[cw!][director] 恢复原语异常 {key}: {e}')
            return self.round_success(f'{key} 验证失败({detail}),已试恢复,交回外循环', wait=1.0)
        return self.round_success(f'{key} ✓,交回外循环重识别', wait=1.0)

    def _takeover_collect_if_needed(self, match, session) -> OperationRoundResult | None:
        """接管局补采(W971 §2.1/01-opening §2.1;单轮化后挂点 = 单轮 op 观察段)。

        触发 = session.briefing_bosses 空(本局尚无位面序真值);可交互门 = 节点条
        可读;会开/关位面详情画面 → 执行后交回外循环重识别。计数挂 session
        (单轮 op 每外循环轮次重建,实例属性不存活);成功或 2 次失败后停。
        """
        if (getattr(session, 'cw_takeover_collect_done', False)
                or getattr(session, 'briefing_bosses', None)):
            return None
        _tk_slots = None
        with contextlib.suppress(Exception):
            _tk_slots = read_node_sequence(self.ctx, self.last_screenshot)
        if _tk_slots is None:
            return None   # 节点条不可读(过场/overlay 半开帧)→ 等下轮,不消耗预算
        _tries = getattr(session, 'cw_takeover_tries', 0) + 1
        session.cw_takeover_tries = _tries
        if _tries > 2:
            session.cw_takeover_collect_done = True
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
        _pb_res = CwScreenPlaneIntel(self.ctx).execute()
        # 成功取走/失败残留都清空(防泄漏到下局判空;词缀随采结算只在本分支)
        _names = list(self.ctx.cw_plane_bosses or [])
        _affixes = list(self.ctx.cw_plane_affixes or [])
        self.ctx.cw_plane_bosses = None
        self.ctx.cw_plane_affixes = None
        if _pb_res is not None and getattr(_pb_res, 'success', False) and _names:
            session.cw_takeover_collect_done = True
            # 保位写(ADR-0398):徽章态位面采得 None 原样占 3 槽,
            # 丢弃会让后续位面名字左移错位(位面序真值变假)。
            session.briefing_bosses = _names
            log.info('[cw][director] 开局 boss 实采完成(位面序保位):%s', _names)
        if _affixes and not getattr(session, 'briefing_affixes', None):
            session.briefing_affixes = _affixes
            log.info('[cw][director] 词缀补采(位面详情横条随采,简报未供时):%s', _affixes)
        return self.round_success('接管补采执行,交回外循环重识别', wait=1.0)

    def _bench_full_break_round(self, match, session, obs, config) -> OperationRoundResult | None:
        """席满破墙单轮(M16,ADR-0136):备战席满警告模态拒绝拖拽/出战 →
        破墙动作优先(腾席链),执行后交回外循环。None = 无警告,继续正常单轮。"""
        from sr_od.application.currency_war.obs.cw_observation import read_bench_full
        _scr_full = getattr(self, 'last_screenshot', None)
        _bench_full_now = (_scr_full is not None
                           and read_bench_full(self.ctx, _scr_full))
        if not _bench_full_now:
            # r366b(review A1):警告解除 → 等待计数清零(正常态恢复预算)
            if getattr(session, 'free_bench_gold_wait', 0):
                session.free_bench_gold_wait = 0
            return None
        log.warning('[cw!][director] 备战席已满警告(模态挡拖拽/出战)→ 破警告优先(腾席链)')
        # 破墙 obs 用 dataclasses.replace 从真 obs 派生(全字段保真,仅覆写腾席相关)
        import dataclasses
        bf_obs = dataclasses.replace(
            obs, box_overlay_open=False, boxes=[], spheres=[],
            free_bench_slots=0, shop_open=False,
            # ADR-0136 补修:横幅在时拖放被游戏拒 → vacancy 置 0 强制走 b(升级)/c(卖最弱)
            deploy_vacancy=0)
        # 黑板接口:破墙派生帧写 session → decide_prep_screen
        session.prep_obs_frame = bf_obs
        action = match.strategy.decide_prep_screen(session, config)
        progressed, detail = self._executor.execute(action)
        log.info(f'[cw][director] 破警告动作 {type(action).__name__} → {"✓" if progressed else "✗"} {detail}')
        # 破墙动作也记一条 exec_events(类名带 BenchFull 前缀,审计可辨)
        try:
            if obs.state is not None:
                _bf_rid = state.current_run_id() or '-'
                if _bf_rid == '-' and self.ctx.cw_match is not None:
                    _bf_rid = f'match:{id(self.ctx.cw_match) & 0xffff:x}'
                state.get_recorder().record_exec_event(
                    run_id=_bf_rid,
                    round_num=obs.state.round_num,
                    action_family=f'BenchFull_{type(action).__name__}',
                    screen='battle_prep', event='bench_full_break',
                    reason='备战席满破墙')
        except Exception:   # noqa: BLE001  遥测 best-effort
            pass
        return self.round_wait(
            status=f'备战席已满,已试破警告({type(action).__name__}),交回外循环', wait=1.0)

    def _clear_entry_overlays(self) -> None:
        """P0 清场前置段(规范入口序列「先清场、再识别、后动作」;ADR-0462):
        环入口先逐屏探可一键关闭的 overlay(注册表 = ``cw_observation_gate.
        ENTRY_OVERLAY_CLOSE``,锚判定走现有 screen 体系),命中即点其关闭按钮,
        拿干净备战画面再进 gate/全量识别——识别与 overlay 状态交织是死读与
        冲突噪声的共同根。只收「无决策语义的弹窗/面板」;投资环境/策略等
        交互 overlay 有专属 handler,关闭即丢决策内容,不进注册表、仍走既有
        event_overlay bail → 外环消化路径。fail-open:截图/识别/点击任一异常
        静默返回(=现行为,gate 的帧态门继续兜底)。"""
        from one_dragon.base.screen import screen_utils
        from sr_od.application.currency_war.obs.cw_observation_gate import (
            ENTRY_OVERLAY_CLEAR_ROUNDS,
            ENTRY_OVERLAY_CLOSE,
            ENTRY_OVERLAY_SETTLE_S,
        )
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

    def _try_collapse_open_shop(self) -> bool:
        """环入口遇开商店稳定态(战斗胜利后新回合游戏可能自动开)→
        收起返回 True;非开态(真特效/overlay)返回 False。

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

    # ===== 购买单元记账(spend_ledger;纯观测,零行为变更)=====

    def _spend_unit_open(self, obs: PrepObservation) -> None:
        """开购买单元(RunBuyPhase 执行前):记时点与单元开时点 gold 观测。

        F2 语义:本时点商店关,gold 恒不可信——诚实记录不冒充真值,只作
        辅助对拍。plane/round 取 session.last_state(与 exec_events 同
        join 口径)。纯内存写,失败不影响环。
        """
        st = obs.state
        sess = self._session()
        ls = getattr(sess, 'last_state', None) if sess is not None else None
        plane = int(getattr(ls, 'plane', 0) or 0)
        rnd = int(getattr(ls, 'round_num', 0) or 0)
        # 同轮多单元序号恒递增:序只在 (plane, round) 变化(或新局清键)时
        # 重置为 1——run() 环节点重入不清序,消除同轮双单元撞 unit_seq=1
        #(ADR-0514:任何按 (round, unit_seq)
        # 对拍的消费方都会撞键,_spend_unit_row 靠「取最后一行」侥幸取对)。
        key = (plane, rnd)
        if key != self._spend_unit_key:
            self._spend_unit_key = key
            self._spend_unit_seq = 1
        else:
            self._spend_unit_seq += 1
        self._unit_meta = {
            'seq': self._spend_unit_seq,
            't0': time.monotonic(),
            'gold': getattr(st, 'gold', None) if st is not None else None,
            'gold_trusted': bool(obs.state_gold_trusted),
            'plane': plane,
            'round': rnd,
        }

    def _spend_unit_close(self, progressed: bool, detail: str = '',
                          boundary: str = 'closed') -> None:
        """关购买单元:框架事实落 spend_ledger.jsonl(best-effort)。

        boundary:closed=执行返回且进展 / failed=执行返回但未进展 /
        aborted=执行抛异常。plan 与金真值不在此复制——读端 join
        decisions/obs_conflicts(cw_telemetry.query_spend_ledger)。
        """
        meta = self._unit_meta
        self._unit_meta = None
        if meta is None:
            return
        try:

            from sr_od.application.currency_war.telemetry.recorder import (
                record_spend_unit,
            )
            record_spend_unit(
                plane=meta['plane'], round_num=meta['round'],
                unit_seq=meta['seq'], boundary=boundary,
                progressed=progressed,
                duration_s=time.monotonic() - meta['t0'],
                detail=detail or '',
                gold_before=meta['gold'],
                gold_before_trusted=meta['gold_trusted'])
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] spend_ledger skip: {e}')
        # [停机钩子·临时采证,安灯式] 采够/问题闭环后整段删除(钩子纪律:不留开关)。
        # 判定与记账同点:
        # 命中 mismatch → 哨兵(截图+flag)→ stop_running → 不再点击保画面。
        # 每局最多停一次;判定复用分类器,数据源与离线读端同一套
        #(shop 关店对拍的冲突行在本单元返回前已同步落盘 journal)。
        if not self._exec_fail_hook_fired:
            try:
                self._exec_fail_hook_check(meta, boundary)
            except Exception as e:  # noqa: BLE001  钩子 best-effort,不阻塞环收口
                log.debug(f'[cw-director] exec_fail hook skip: {e}')

    def _exec_fail_hook_check(self, meta: dict, boundary: str) -> None:
        """安灯判定+触发(内部方法;谓词与 flag 写入是模块级纯函数,离线可测)。

        数据源:decisions.jsonl 本轮 shop plan 行(plan/开店金,shop 开态可信)
        + spend_ledger.jsonl 本单元行的 gold_close(shop.py 关店对拍点无条件
        暂存、落账时消费填充——每单元必写、带 run_id/plane/round/unit_seq
        单元身份)。历史局旧行(无 gold_close 字段)→ 回退 obs_conflicts
        gold_delta 冲突行 + ts 邻近窗 join 兼容路径;新行读失败以 None 进
        分类器 = unknown = 不停(不猜)。

        为什么主源必须是单元行:冲突行是「仅 mismatch 才写」的条件性 journal、
        行内无 run_id/unit_seq,(plane,round)+ts 窗 join 会吃到同轮上一单元的
        陈旧行(实机误停例:健康第二单元 join 到 86 秒前
        第一单元的 new=51,金差算 0 → not_effective → 误停;
        见 ADR-0514)。单元行身份键天然完整,一举消掉两个病根。
        """
        run_id = state.current_run_id()
        if not run_id:
            return
        replay_dir = state.get_recorder().replay_dir
        plan_row = query._shop_plan_rows(
            replay_dir, run_id).get((meta['plane'], meta['round']))
        if plan_row is None:
            return
        # ADR-0456:spend_ledger 单元行的执行侧「计划≠尝试」字段
        #(与 plan 行同一 replay join 面,run_id+unit_seq 定位,无陈旧风险)
        # ——硬墙跳过/截断的单元分流 plan_truncated 豁免(防误停),
        # 不再被当「点击落空」误停。行缺失 → executed=None,退回无
        # executed 字段的原语义。
        unit_row = query._spend_unit_row(
            replay_dir, run_id, meta['plane'], meta['round'], meta['seq'])
        executed = None
        if unit_row is not None:
            executed = {
                'plan_truncated': unit_row.get('plan_truncated'),
                'refresh_attempted': unit_row.get('refresh_attempted'),
                'refresh_board_changed': unit_row.get('refresh_board_changed'),
            }
        plan_actions = plan_row.get('actions') or []
        gold_open = plan_row.get('gold')
        # 关店金解析(query.resolve_unit_gold_close 单一源,与离线视图同口径):
        # 单元行自身 gold_close 优先(身份键完整、每单元必写);旧行无该字段
        # 才回退冲突行 join。读失败以 None 形态进入分类器 → unknown 不停。
        import datetime as _dt
        gold_close = query.resolve_unit_gold_close(
            unit_row, query._read_conflict_gold_delta(replay_dir),
            meta['plane'], meta['round'],
            _dt.datetime.now().isoformat(timespec='seconds'))
        if not exec_fail_should_stop(plan_actions, gold_open, gold_close,
                                     boundary=boundary, executed=executed):
            return
        self._exec_fail_hook_fired = True
        items = query.plan_gold_flow(plan_actions)['items']
        plan_summary = ';'.join(
            f"{i['type']}:{i['target']}:{i['cost']}" for i in items) or '(空plan)'
        shot_prefix = (f'exec_fail_{run_id}_p{meta["plane"]}'
                       f'r{meta["round"]}u{meta["seq"]}')
        import contextlib
        with contextlib.suppress(Exception):   # 截图失败不拦停机(flag 是主哨兵)
            self.save_screenshot(prefix=shot_prefix)
        write_exec_fail_flag(exec_fail_flag_path(),
                             run_id=run_id, plane=meta['plane'],
                             round_num=meta['round'], unit_seq=meta['seq'],
                             plan_summary=plan_summary,
                             gold_open=gold_open, gold_close=gold_close)
        log.warning('[cw!][director] 安灯:购买单元执行失败(计划花费>0 金差≈0)'
                    ' p%sr%s u%s → 停机留现场 flag=cw_exec_fail_hook.flag',
                    meta['plane'], meta['round'], meta['seq'])
        rc = getattr(self.ctx, 'run_context', None)
        if rc is not None:
            rc.stop_running(reason='hook:exec_fail_mismatch')

    # ===== W970 批 C:流程层商店编排(RunBuyPhase 解体的承接,§4.3.2/§4.3.6,dd-017)=====

    def _open_shop_phase(self, action, obs) -> tuple[bool, str]:
        """OpenShop 动作的流程层编排(壳直调三 op 调用点自 BuyShopCards 上移)。

        - read_only=True(腾席链 b 取 gold 真值 / 开态清洁面板):CwOpOpenShop
          (幂等,已开不点)→ heavy 观察(gold 开态真值进 session)→ **不调
          商店决策**(M-6 门保持:free=0 不进买牌)→ CwOpCloseShop → 节点探针
          → 回备战(W970 §4.3.6;r364 进展保证 = 开店成功即 progressed)。
        - read_only=False:开店前 hp 三件组取**开店前的备战观察**(商店开态
          HP 区不可读,W970 §4.3.4 读互斥承接;结算真值链已在 gated_hp 收口,
          trusted 位 = 本帧可读)→ 商店动作波循环(run_buy_waves:观察 →
          decide_shop_screen → 执行至首个 RefreshShop → 重判,MAX_REFRESH 硬墙)
          → CwOpCloseShop → finalize_buy_phase(买后重估/期望暂存/gold 对拍/
          执行事实)→ 节点探针。

        节点探针挂点 = CwOpCloseShop 完成后(店确定关的可靠时点;原
        EnsureShopClosed 后字符串匹配判据退役,改类型分派)。
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
        _r_open = open_shop(self)
        if not _r_open.is_success:
            return False, f'开店未生效({_r_open.status})'
        if action.read_only:
            self._observe(heavy=True)   # 开态观察刷新(gold 真值)
            _r_close = close_shop(self)
            if not _r_close.is_success:
                return False, f'read_only 关店未生效({_r_close.status})'
            self._probe_node_type()
            return True, 'read_only 开店重读(gold 真值)'
        st = getattr(obs, 'state', None)
        hp_value = getattr(st, 'hp', None) if st is not None else None
        hp_readable = bool(getattr(st, 'hp_readable', False))
        hp_trusted = hp_readable
        from sr_od.application.currency_war.operations.cw_op.cw_op_buy_cards import (
            run_buy_waves,
        )
        _rr, outcome = run_buy_waves(self, match, hp_value, hp_readable, hp_trusted)
        if _rr is not None or outcome is None:
            return (False, f'买牌波循环未完成'
                    f'({_rr.status if _rr is not None else "无产出"})')
        _r_close = close_shop(self)
        if not _r_close.is_success:
            return False, f'关店未生效({_r_close.status})'
        _summary = finalize_buy_phase(self, match, outcome,
                                      hp_value, hp_readable, hp_trusted)
        self._probe_node_type()
        return True, f'买牌 {_summary}'

    def _v2_post_frame_accounting(self, obs, acct: dict,
                                  session) -> None:
        """新环 heavy 定型帧上的动作级对账族(旧环同帧消费逐位对齐;零决策)。

        输入 = 本帧 obs + acct(最近一步动作记账状态);每通道内部
        best-effort,异常不阻塞环。覆盖:paddle 审计 / 拖动期望 / 买牌
        期望(买牌期望上报通道,蓝图 §7)/ 经验 / 羁绊显示 /
        商店池 / 合成预览 / 卖角色装备期望。
        """
        import contextlib

        from sr_od.application.currency_war.obs.cw_observation import (
            read_deployed_count,
        )

        key = acct.get('key')
        progressed = bool(acct.get('progressed'))
        # 动作级板面对拍(后读;期望不等 = 未生效证据,纯留证)
        if acct.get('dep_pre') is not None:
            with contextlib.suppress(Exception):
                _dep_post = read_deployed_count(self.ctx, self.last_screenshot)
                if _dep_post is not None and _dep_post - acct['dep_pre'] != acct['dep_delta']:
                    _gap = _dep_post - acct['dep_pre']
                    defects.record_defect(
                        'deployed', 'invariant_break',
                        expected=f'{key} 执行后 paddle={acct["dep_pre"] + acct["dep_delta"]}',
                        observed=f'paddle={_dep_post}',
                        plane=int(getattr(obs.state, 'plane', 0) or 0),
                        round_num=int(getattr(obs.state, 'round_num', 0) or 0),
                        gap=float(_gap), gap_large=True,
                        reader_source='paddle_action_audit',
                        note='部署/卖出动作级即时对拍(§2.3;与 deployed_align 自动纠漂分立)')
        # 期望态对账(仅 progressed 分支——验证失败 = 动作未发生,期望不适用)
        with contextlib.suppress(Exception):
            if progressed and acct.get('drag_expect') is not None:
                self._reconcile_drag_expect(acct['drag_expect'])
        # 期望态层·买牌:RunBuyPhase 单元购买期望由
        # shop.py 买入点写入 session.pending_buy_expect;本帧消费对账。
        with contextlib.suppress(Exception):
            _pending_buy = session.pending_buy_expect
            if _pending_buy is not None:
                session.pending_buy_expect = None
                if progressed:
                    self._reconcile_buy_expect(_pending_buy)
        with contextlib.suppress(Exception):
            self._reconcile_xp_expect(obs)
        with contextlib.suppress(Exception):
            self._reconcile_faction_display(obs)
        with contextlib.suppress(Exception):
            self._reconcile_shop_pool(obs)
        with contextlib.suppress(Exception):
            self._reconcile_merge_preview(obs)
        with contextlib.suppress(Exception):
            if progressed and acct.get('equip_expect') is not None:
                self._reconcile_equip_expect(acct['equip_expect'])
        acct.update(key=None, progressed=False, drag_expect=None,
                    equip_expect=None, dep_delta=0, dep_pre=None,
                    unit_open=False)

    def _probe_node_type(self, screen: MatLike | None = None) -> None:
        """[观测] 备战入场读节点行序列(read_node_sequence)→ log。

        read_node_sequence =
        HoughCircles 动态定圆 + HSV 三态 + Hu 匹配 + OCR(见 cw_node_reader)。
        screen 传入时(EnsureShopClosed 后的 gate 稳定帧透传)复用该帧
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
            # [激活位·圣杯采集批 B2] 被动哈希采集接线行([临时采集],采集清单采齐后连本注释整段删):
            # 激活 = 下面两行取消注释(diff 一次一行);钩子本体在 grail_collect_hooks.grail_passive_collect
            # (每备战观察帧整帧哈希去重+节流收圣杯任务瞬时帧,零决策影响)。
            from sr_od.application.currency_war.operations.grail_collect_hooks import (
                grail_passive_collect,
            )
            grail_passive_collect(screen)
            # current 槽类型写 session(cw_loop on_round_end 消费——
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
                    _st_now = (self.ctx.cw_match.session.last_state
                               if self.ctx.cw_match is not None else None)
                    _plane_now = (_st_now.plane
                                  if _st_now is not None else None)
                    if store_plane_table(_sess, _seq, _plane_now):
                        log.info('[cw-director][nodeseq] 槽序表存 p%s %d 槽:%s',
                                 _plane_now, len(_seq), _seq)
                    # current 覆盖链左移优先:OCR 标签
                    # 位置门拦不住相邻同类标签(reward 标签恰在
                    # current 下方 x 对上时误读)→
                    # current 直读不可信。改:**左移推断优先**
                    # (上帧 upcoming[0]),OCR 标签
                    # 只在左移无值时兜底(开局首帧)。
                    # 左移**锚定轮次**——同轮
                    # 多次 probe(开店/关店/重开)时 upcoming 还是本轮
                    # 的,会把 current 写成下一节点(超前一位)。
                    # 只在上次 probe 是更早轮次时才左移;同轮保持原值。
                    _anchor = (_st_now.plane, _st_now.round_num) \
                        if _st_now is not None else None
                    _prev_anchor = getattr(
                        _sess, 'nodeseq_probe_anchor', None)
                    if _anchor is not None and _anchor != _prev_anchor:
                        _prev = getattr(_sess, 'upcoming_types', None) or []
                        _direct = _prev[0] if _prev else None
                        if _direct is not None:
                            _sess.node_type_current = _direct
                        _sess.nodeseq_probe_anchor = _anchor
                    # current 直读兜底(首帧:无左移源时)
                    if getattr(_sess, 'node_type_current', None) is None:
                        _cur = next((s for s in slots
                                     if s.state == 'current'), None)
                        if _cur is not None and _cur.node_type:
                            _sess.node_type_current = _cur.node_type
                    # 存本帧 upcoming(下轮左移用; idx 升序)
                    _sess.upcoming_types = [
                        s.node_type for s in sorted(
                            (x for x in slots if x.state == 'upcoming'),
                            key=lambda x: x.idx) if s.node_type]
                    # 实时识别权威(用户裁定方向):
                    # **实时识别是权威**——每备战帧读节点行,
                    # 应对 invest-env 等策略对节点的改变;
                    # 开局帧的完整槽序存 plane_node_table 只作
                    # **离线统计源**(跨局累积建「位面典型节点表」
                    # 进 sim 骨架/策略知识)+ current 槽高亮读不到
                    # 时的左移兜底参照。不做决策主源。
            except Exception:   # noqa: BLE001  best-effort 写入
                pass
        except Exception as e:  # noqa: BLE001  live 验证 best-effort,失败不阻塞备战
            log.info(f'[cw-director] nodeseq skip: {e}')

    def _capture_unrecognized_node_icons(self, screen, slots, node_row_rect, hu_threshold) -> None:
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

    def _record_step(self, obs: PrepObservation, action: PrepAction) -> None:
        """F8:obs+action 序列落 telemetry(P1 仅落盘;replay 评分后置)。"""
        try:
            st = obs.state
            _sess = self._session()
            if st is not None:
                st = st.copy()
                # obs.state 是 OCR 现读态(equips 恒空),从 session owned 快照
                # 补拷。copy 后再写——cw_comps 装备权重读 state.equips,
                # 原地写会污染 director 后续决策输入(观测链修复禁越界)。
                st.equips = list(getattr(_sess, 'last_owned_equips', []) or []) \
                    if _sess is not None else []
            recorder.record_decision(
                st if st is not None else GameState(),
                target_comp=(_sess.target_comp.name
                             if _sess is not None and _sess.target_comp else ''),
                candidate_scores={},
                eval_breakdown={'prep_step': float(self._steps)},
                actions=[action],   # type: ignore[list-item]  PrepAction 与旧 Action 并存(P2 归一)
                gold_point=False,   # 步进记录不进 gold_trajectory(每回合一采样,shop 侧采)
                extra={'formed_stop': bool(getattr(
                    _sess, 'v3_formed_stop', False)),  # ADR-0343 豁免联动
                    # P1 配方对平铺观测(P1 备战帧判读「终局线何时锁」的
                    # 上游量;锁定产物/副方向取序见 p1_pair_label)
                    'sess_p1_pair': schema.p1_pair_label(
                        getattr(_sess, 'v3_intention', None))},
            )
        except Exception as e:  # noqa: BLE001  遥测失败不阻塞环
            log.debug(f'[cw-director] telemetry skip: {e}')


def finalize_buy_phase(op: SrOperation, match, outcome,
                       hp_value: int | None, hp_readable: bool,
                       hp_trusted: bool) -> str:
    """买牌单元收尾(W970 批 C 抽出:RunBuyPhase 解体后由流程层
    ``CwScreenPrep._open_shop_phase`` 与 sim 兼容壳 BuyShopCards.buy 共用;
    单一源防双份漂移)。买后重估 / 买牌期望暂存 / gold 对拍 / 执行事实暂存,
    返回单元摘要字符串(消费方包装成 round status/detail)。"""
    from sr_od.application.currency_war.obs.cw_observation import (
        read_game_state,
        read_gold,
        read_gold_settled,
    )
    from sr_od.application.currency_war.obs.cw_observation_gate import PHASE_PREP_CLEAN
    from sr_od.application.currency_war.operations.cw_op.cw_op_buy_cards import (
        _apply_hp,
        _tracked_bench_chars,
        build_post_buy_incremental_state,
        expected_gold_after_actions,
    )
    state = outcome.state
    config = outcome.config
    total_buy = outcome.total_buy
    total_level = outcome.total_level
    total_refresh = outcome.total_refresh
    total_sell = outcome.total_sell
    total_sell_income = outcome.total_sell_income
    _spend_executed = outcome.spend_executed
    gold_open = outcome.gold_open
    _plan_truncated = outcome.plan_truncated
    _refresh_skipped = outcome.refresh_skipped
    _refresh_attempted = outcome.refresh_attempted
    _refresh_board_changed = outcome.refresh_board_changed
    _buy_purchases = outcome.buy_purchases
    _buy_has_sell = outcome.buy_has_sell
    _buy_unidentified = outcome.buy_unidentified
    _buy_pre_bench = outcome.buy_pre_bench
    _buy_pre_deployed = outcome.buy_pre_deployed
    # r251 修 A(买后同轮重估):update_target 原只在买前跑——买桥件
    # 当轮桥不认领,deploy 当轮无方向(第六局 r4 买藿藿/爻光但
    # target='' 仙舟件全坐板凳,散 pair 白挨打 -8/-12/-28)。
    # 买完用最新 bench 重估一次:桥/锁线当轮生效,紧随的 deploy
    # 就有方向。幂等(update_target 是纯重估,已锁线不漂移)。
    try:
        if match is not None and (total_buy or total_level or total_refresh):
            _post = None
            if not total_level:
                # 执行边界压缩·买后验证增量:本单元动作(无升级)只改
                # gold/bench(plane/round/board 等机制不变量,构造单一源 =
                # build_post_buy_incremental_state)→ 单区金真读 + tracked
                # 重播,替代整帧 OCR。fail-closed 双维回退全量读:金失读
                # (None)/tracked 空(真空与丢跟踪不可区分,见构造点契约)。
                # 金读走稳定门(read_gold_settled):关店帧入账计数器可能
                # 仍在跳,单帧会采到入账前旧值(误读维度造值;门=两帧一致
                # 才采信,不一致取末帧+留证)。
                _inc_gold = None
                with contextlib.suppress(Exception):
                    _inc_gold = read_gold_settled(op.ctx, op.screenshot())
                if _inc_gold is not None:
                    _post = build_post_buy_incremental_state(
                        state, _inc_gold,
                        (match.session.tracked_bench_chars
                         or _tracked_bench_chars(match.session.tracked_bench)),
                        match.session.last_node_type or None,
                        hp_value, hp_readable, hp_trusted)
            if _post is None:
                _post = read_game_state(op.ctx, op.screenshot(),
                                        phase=PHASE_PREP_CLEAN)   # ADR-0462 关店后=干净备战基线
                _apply_hp(_post, hp_value, hp_readable, hp_trusted)
                if match.session.last_node_type:
                    _post.node_type = match.session.last_node_type
            match.strategy.update_target(_post, match.session, config)
    except Exception as e:   # noqa: BLE001  重估失败不阻塞买牌
        log.debug('[cw] 买后重估失败(不阻塞): %s', e)
    # `w536_merge_expect/`:单元购买意图 → 期望态,暂存 session 供 CwScreenPrep 主环在
    # RunBuyPhase 后的 heavy 定型帧上消费对账(surface='bench',
    # kind='buy_expect_mismatch';零决策记账)。含卖出/未识别牌不建
    # (见单元头注释);计算失败静默跳过(best-effort,不阻塞买牌)。
    if match is not None and _buy_purchases \
            and not _buy_has_sell and not _buy_unidentified:
        with contextlib.suppress(Exception):

            from sr_od.application.currency_war.kernel.cw_prep_expect import (
                compute_buy_expect,
            )
            _buy_expect = compute_buy_expect(
                _buy_purchases, _buy_pre_bench, _buy_pre_deployed)
            if _buy_expect is not None:
                match.session.pending_buy_expect = _buy_expect
    # gold 差值双源对拍(观察冲突审计 #6 P2,2026-08-17):动作账(逐动作执行时
    # 累计的 _spend_executed:买价+升级费+当次刷价)vs 关店后实际读数 ——
    # expected = 开店首读金 − 全程执行花金 + 全程卖入。基线必须取首读快照
    # 而非末波重读值(后者已净含各波花销,再减全程账 = 跨波重复扣,多波
    # 刷新场景期望恒偏低,量级=前面各波刷新费合计)。(read_gold stylized
    # 间歇漏,但差值对拍容忍 ±2:收入/连胜金不可观项混入)。不等 → 一方有
    # 毒(stylized 漏读 / cost 错 / 未观收入),留证统计毒化率;机制核对器
    # (r9)另有 REFRESH_COST 专项,此处只管 gold 总账。
    if total_buy or total_level or total_refresh or total_sell:
        _spend = _spend_executed
        _final_gold = read_gold(op.ctx, op.screenshot())
        # 金面收口:关店实读金无条件暂存(无论对拍是否冲突)——director
        # 单元关闭落账时经 record_spend_unit 消费,填 spend_ledger 预留
        # 字段 gold_close。此前只有 mismatch 才落冲突行,「对拍通过」与
        # 「read_gold 失读」离线不可分(三态判定 unknown 面);失读(None)
        # 照记(trusted=False),unknown 占比降到读失败率。分类器零改动。
        from sr_od.application.currency_war.telemetry import state as _cw_tel
        _cw_tel.set_unit_gold_close(_final_gold)
        # 迁移审计 w62(git 历史) 件2(ADR-0329):gold 差值对拍纳入卖入——卖出接线后,卖轮实际金 =
        # 开店金 − 花出 + 卖入(游戏侧卖出入账);旧口径不含卖入与实读金恒差
        # income → 每卖轮误报 gold_delta 冲突留证(design 章2.7 必改项)。
        _expected = expected_gold_after_actions(
            gold_open if gold_open is not None else state.gold,
            _spend, total_sell_income)
        if _final_gold is not None and abs(_final_gold - _expected) > 2:
            from sr_od.application.currency_war.kernel.cw_observe import (
                obs_conflict as _oc,
            )
            _oc('gold_delta', _expected, _final_gold, None,
                verdict='留证-动作账vs读数不等(stylized漏读/cost错/未观收入)',
                source='shop_spend_audit', plane=state.plane, round_num=state.round_num,
                spend=_spend)
    # `w577_refresh_fee_and_andon/`:「计划≠尝试」执行事实 → 单元账暂存(director 落账时经模块级
    # record_spend_unit 消费进 spend_ledger;与 set_unit_gold_close 同槽
    # 模式)。全缺省不调(免残留噪声);best-effort 不阻塞收工。
    if _plan_truncated or _refresh_attempted \
            or _refresh_skipped is not None:
        with contextlib.suppress(Exception):
            # 遥测模块显式别名(裸 state=GameState 变量,误绑会被
            # suppress 吞成执行事实静默断流,同 free_refresh 留证段)
            from sr_od.application.currency_war.telemetry import state as _cw_tel
            _cw_tel.set_unit_exec_facts(
                plan_truncated=_plan_truncated,
                refresh_skipped=_refresh_skipped,
                refresh_attempted=_refresh_attempted,
                refresh_board_changed=_refresh_board_changed)
    return (
        f'plan 买{total_buy}张 升{total_level}次 刷{total_refresh}次 '
        f'卖{total_sell}张(+{total_sell_income}金,守卫拦{outcome.total_sell_skip}) '
        f'(gold={state.gold} lv={state.level} plane={state.plane})'
    )
