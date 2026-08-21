# 未验证(P1 新建,2026-08-14;设计 doc 15 v7 + ADR-0123;环流程待实机跑验)
# review 修订(review round-1,2026-08-14):H-1 观察分层(执行过的游戏动作一律 heavy 重读,
# light 仅控制流;light 沿用上次 heavy 缓存)/H-2 恢复-屏蔽-bail 分型语义/M-2 模板路径复用
# ensure_portrait_templates/M-3 gold 可信标记/L-1 对账漂移 [cw!]+截图/L-4 强制出战异常兜底。

"""货币战争 备战决策环(PrepDirector)—— 两层环之内环(框架层;doc 15)。

**框架不含任何玩法判断**:何时收球/卖谁/何时出战 = 策略(CwStrategy.decide_prep_action);
本模块只保证八项框架不变式(F1-F8,doc 15 §5.0):
- F1 单步契约: 每步 = observe → decide_prep_action → execute(带验证) → 再 observe
- F2 观察真实: obs 只由现成 reader 产出;gold 可信度由框架显式标记
  (state_gold_trusted:仅 shop 开态重读的 state 才 True,关态读空不可信)
- F3 动作合法域: 策略输出须在动作全集内(白名单);框架校验参数后执行
- F4 验证与防护: 每动作完成验证;fail 计数/恢复原语/屏蔽/预算强制出战(§7)
- F5 出口兜底: 策略不出战且 stall/预算耗尽 → 框架强制出战
- F6 无状态策略: 环不污染策略实例;跨步意图走 StrategySession
- F7 可换策略: strategy 由配置选(11 号);换策略只换决策
- F8 可回放: obs+action 序列落 telemetry(P1 仅落盘)

**观察分层(P1 实现,review H-1 定稿)**:执行过的游戏动作(含组合)**一律 heavy 重读**
(买/卖/部署/装备/开箱/点球/升级/商店开关都改变结构 —— 单步决策环几乎每步都是结构变化);
light 观察(仅控制流 DeferSpheres / 拒绝步后)**沿用上次 heavy 的 state/bench_chars/
deployed_chars/deploy_vacancy 缓存**(不重 SIFT/OCR,只刷新轻字段)。性能(每步 heavy
~2-3s)live 校准后再分层细化。

**防死循环三层(§7 + review H-2 修订)**:同动作验证连败 2 → 恢复原语(一次/动作实例)→
恢复后仍连败 2(恢复无效)→ **分型**:恢复时关过已知弹层 → BailToOuter(环让位交外环,
弹层分支/停机钩子接手);恢复时只是兜底点空白(无已知弹层 = 状态/识别类失败)→ 本环
屏蔽该动作实例(策略须换路;StartBattle 豁免)。stall≥5 且恢复已试 → 强制出战(F5)。

挂载:battle_loop 备战分支 → PrepDirector(替换 BattlePrepCycle 固定序列;P1)。
环入口对账(SIFT 重读 vs tracking)是 deploy_bench._reconcile_tracking /
battle_prep._verify_recognition 钩子的继任宿主。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_telemetry
from sr_od.application.currency_war.currency_war_cv import slot_occupied
from sr_od.application.currency_war.cw_identity_obs import (
    ensure_portrait_templates,
    read_bench_chars,
    read_deployed_chars,
    read_reward_spheres,
    read_supply_boxes,
)
from sr_od.application.currency_war.cw_identity_obs import (
    read_tomes as cw_identity_obs_read_tomes,
)
from sr_od.application.currency_war.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.cw_observation import (
    read_deploy_cap,
    read_deployed_count,
    read_game_state,
    read_gold,
)
from sr_od.application.currency_war.cw_state import BenchChar, GameState
from sr_od.application.currency_war.prep_actions import (
    BailToOuter,
    ClickSpheres,
    DeferSpheres,
    DeployMove,
    OpenTome,
    PrepAction,
    PrepActionExecutor,
    StartBattle,
    action_key,
    row_area_centers,
    try_recovery,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


@dataclass
class PrepObservation:
    """备战决策环统一观察(§3;决策单一输入,组合现成 reader 不新写识别)。

    P1 恒空字段(§13.4,策略不得依赖):overlay_state / overlay_options / shop_cards /
    owned_equips(P4 工具域接线)。

    分层语义:state/bench_chars/deployed_chars/deploy_vacancy 只在 heavy
    观察刷新(环入口 + 每个执行过的游戏动作后);light 步沿用上次 heavy 值(可能 stale,
    单线程内 stale 窗口 = 无动作步,安全)。轻字段(spheres/boxes/占用/shop_open/overlay)
    每步现读。
    """
    state: GameState | None = None        # heavy 重读;gold 仅 shop_open 时可信(F2)
    state_gold_trusted: bool = False      # F2:state.gold 是否可信(= heavy 时 shop 开)
    bench_chars: list[BenchChar] = field(default_factory=list)   # heavy: SIFT 身份
    deployed_chars: list[BenchChar] = field(default_factory=list)
    spheres: list = field(default_factory=list)       # read_reward_spheres [(color, Point, r)]
    boxes: list = field(default_factory=list)         # read_supply_boxes [(slot, Point)]
    tomes: list = field(default_factory=list)         # read_tomes [(slot, Point)] 秘密典籍(2026-08-16)
    free_bench_slots: int = 0           # 9 − 占用(角色+箱都占席;CV 每步现读)
    deploy_vacancy: int = 0             # deploy_cap − deployed_count(heavy 刷新)
    shop_open: bool = False             # 锚点「按钮-收起」可见(每步现读)
    box_overlay_open: bool = False      # 武装箱 overlay(标识-请选择;每步现读)
    front_occupied: set = field(default_factory=set)  # 前排占用物理槽位号(每步现读)
    back_occupied: set = field(default_factory=set)
    front_size: int = 4
    back_size: int = 6
    overlay_state: str | None = None    # P5
    # 事件 overlay 检测(P1-4 过渡:盛会之星/选择伙伴/祈愿试炼 —— 挡操作,检测到即 BailToOuter
    # 交外环分支 handler;live 2026-08-15 实锤:盛会之星 overlay 下 deploy 全灭 → 空场 HP 82→1)
    event_overlay: str | None = None
    overlay_options: list | None = None # P5
    shop_cards: list | None = None      # P1 恒 None(仅买牌阶段刷新)


#: 未识别节点图标采集防抖(idx → 上次采集时刻)。module-level:r80 审计 c)实锤
#: PrepDirector 每备战环重建(battle_loop loop 内构造),实例属性跨环零存活 → 300s 窗
#: 失效(同 idx 每环各采一张,内容哈希对帧微变不设防)。
_NODE_ICON_SHOT_TS: dict[int, float] = {}


class PrepDirector(SrOperation):
    """备战决策环:观察驱动单步决策,替代 BattlePrepCycle 固定序列(P1)。

    单「决策环」节点 + 内部 while;环级预算 MAX_STEPS(步数)与 STALL_LIMIT(零进展)
    兜底强制出战(F5);ping-pong 由外环 MAX_ITER=2000 承担(勿引 node_max_retry —— round_wait
    不消耗 node 重试预算,operation.py:453-461 仅 RETRY 递增;doc 15 §7 v7 M-1)。
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
        # light 步沿用的 heavy 缓存(观察分层,review H-1)
        self._cached_state: GameState | None = None
        self._cached_bench: list[BenchChar] = []
        self._cached_deployed: list[BenchChar] = []
        self._cached_vacancy: int = 0
        self._cached_gold_trusted: bool = False

    # ===== 观察(F2:只由现成 reader 产出)=====

    def _observe(self, heavy: bool) -> PrepObservation:
        """组装备战观察。heavy=True(环入口 + 每个执行过的游戏动作后):SIFT 身份 + GameState
        + cap 全重读;False(控制流/拒绝步后):只现读轻字段,heavy 字段沿用缓存。"""
        # 光标 parking(审计 P0,2026-08-16,用户指示):上个动作(买牌点购买经验/拖拽停目标/
        # 点球)后光标停在点击处,与识别区重叠 → OCR/SIFT 污染(M38 level 毒化根因链)。
        # F1 契约:heavy 在每个执行过的游戏动作后必调 → 此处 park 覆盖全部动作后首读。
        if heavy:
            self.park_cursor()
        screen: MatLike = self.screenshot()
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
        # star_tome(星徽秘典四选一)2026-08-16 补(review P2:纵深防御 —— loop 0i 判据 miss 时
        # 误派本环,穿模观察/动作失败搅动;加清单 → 即刻 bail 交回外环 0i 接管)。
        for _scr, _area, _tag in (
            ('货币战争-盛会之星', '标识-盛会之星', 'megastar'),
            ('货币战争-选择伙伴', '标识-选择伙伴', 'partner'),
            ('货币战争-祈愿试炼', '标识-祈愿试炼', 'wish_trial'),
            ('货币战争-星徽秘典弹窗', '标识-星徽秘典', 'star_tome'),
            # r10 review 根因修:投资策略/投资环境/补给 3 个 0e 屏(此前白名单缺 → 在策略屏上
            # 卡片立绘被 HoughCircles 误检成假球 → ClickSpheres 连败 → 恢复原语盲点 (960,530)
            # = 中卡描述区正中 → 误开星徽详情弹窗 → 15 streak 停机,M53 实锤)。
            ('货币战争-投资策略', '标识-请选择投资策略', 'invest_strategy'),
            ('货币战争-投资环境', '标识-投资环境', 'invest_env'),
            ('货币战争-补给', '标识-补给阶段', 'supply'),
        ):
            if self.round_by_find_area(screen, _scr, _area, crop_first=False).is_success:
                obs.event_overlay = _tag
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
            templates = ensure_portrait_templates(self.ctx)   # M-2:复用单一源(路径+缓存)
            if templates is not None:
                obs.bench_chars = read_bench_chars(self.ctx, screen, templates)
                obs.deployed_chars = read_deployed_chars(self.ctx, screen, templates)
                self._reconcile_tracking(obs.bench_chars, obs.deployed_chars, screen)
            else:
                obs.bench_chars = list(self._cached_bench)
                obs.deployed_chars = list(self._cached_deployed)
            st = read_game_state(self.ctx, screen)
            session = self._session()
            # r7 review P0-①:shop 关态帧节点行可读 → node_type 真值写 session(商店开态被遮恒 None,
            # plan 路径 boss 判定全死码的根因);仿 last_hp 模式。
            if session is not None and st.node_type:
                session.last_node_type = st.node_type
            st.bench = list(obs.bench_chars or (session.tracked_bench_chars if session else []))
            obs.state = st
            obs.state_gold_trusted = obs.shop_open   # F2:gold 仅 shop 开态可信(关态读空)
            if not obs.state_gold_trusted:
                log.debug('[cw][director] heavy 读 state 于 shop 关态 → gold 不可信')
            elif st.gold == 0:
                # MED-2:gold 读 0 间歇漏读是实证问题(shop.py 同款缓解)—— 不重读则腾席链 b
                # 误判无金 → 链 c 误卖角色。shop 开态连读 0 才认 0(重截图 3 次取首个 >0)。
                for _ in range(3):
                    time.sleep(0.4)
                    gv = read_gold(self.ctx, self.screenshot())
                    if gv > 0:
                        st.gold = gv
                        break
            if session is not None:
                session.last_state = st
            cap = read_deploy_cap(self.ctx, screen)
            # 观察冲突审计 #15(2026-08-16):cap Y ∈ {level, level+1}(D-53 域知识:无加成=level,
            # 钻石/宝钻=level+1)→ Y 是 level 的**第三独立源**(空间远离 Lv/XP 区,不受同一光标
            # 污染)——不符 = level 或 cap 有读错,留证(三源网是 M38 类毒化天敌)。
            if cap is not None and not (st.level <= cap <= st.level + 1):
                from sr_od.application.currency_war.cw_observe import obs_conflict
                obs_conflict('deploy_cap_vs_level', st.level, cap, screen,
                             verdict='留证-域知识不符(cap应在level..level+1)',
                             source='paddle_cap')
            dep_n = read_deployed_count(self.ctx, screen)
            if cap is not None and dep_n is not None:
                obs.deploy_vacancy = max(0, cap - dep_n)
            else:
                obs.deploy_vacancy = self._cached_vacancy
            # 观察冲突审计 #9(2026-08-16):deployed 总数三源对拍(同帧全齐)——
            # board OCR 阵营计数和 vs paddle X(读 deployed_count)vs CV 占用(front+back)。
            # ⚠️ 语义修正(2026-08-17 r3 live):sum(board.values()) ≠ 部署角色数——
            # 一个角色贡献多阵营(藿藿=仙舟+治疗,4 人可贡献 11 阵营次),board 的 X 是
            # 「该阵营在场人数」非「角色数」→ board_sum 系统性 ≥ 部署数,拿它对拍恒分歧
            # (live M 实测 board_ocr=11/paddle=4/cv=4 的"分歧"全是本语义错,非 reader 毒化)。
            # 修:board 源改「独立羁绊外的最大单阵营计数」也不对(同阵营多角色)——board
            # 根本给不出角色数,**移出三源对拍**,对拍改双源(paddle X vs CV 占用)。
            _cv_occ = len(obs.front_occupied) + len(obs.back_occupied)
            if dep_n is not None:
                _spread = abs(dep_n - _cv_occ)
                if _spread > 1:
                    from sr_od.application.currency_war.cw_observe import obs_conflict
                    obs_conflict('deployed_count_2src',
                                 {'paddle_x': dep_n, 'cv_occupied': _cv_occ},
                                 'spread>1', screen, verdict='留证-双源分歧(paddle拆框/CV阈值)',
                                 source='director_heavy')
            # 更新 light 沿用缓存(trusted 位随 state 缓存,MED-1 —— light 步不重判 shop 态,
            # 缓存 state 生成时的可信度就是它的可信度)
            self._cached_state = st
            self._cached_bench = list(obs.bench_chars)
            self._cached_deployed = list(obs.deployed_chars)
            self._cached_vacancy = obs.deploy_vacancy
            self._cached_gold_trusted = obs.state_gold_trusted
        else:
            # light:heavy 字段沿用缓存(上次真读值;review H-1 — 不再恒默认导致永动机)
            obs.state = self._cached_state
            obs.state_gold_trusted = self._cached_gold_trusted   # MED-1:trusted 位随缓存 state
            obs.bench_chars = list(self._cached_bench)
            obs.deployed_chars = list(self._cached_deployed)
            obs.deploy_vacancy = self._cached_vacancy
        return obs

    def _reconcile_tracking(self, bench: list[BenchChar], deployed: list[BenchChar],
                            screen=None) -> None:
        """环入口对账(§3:read≠tracking 漂移是既有 bug 源 → SIFT 真值重置 tracking)。

        继任宿主:deploy_bench._reconcile_tracking + battle_prep._verify_recognition(P1 挂载
        切换搬入;star 用 read_star 实机金星,同 D-12 语义)。read 失败(templates None)不动。
        漂移 = 需关注([cw!] + 截图存证,继承 _verify_recognition 语义,review L-1)。
        2026-08-16(观察冲突审计 #11):改调公共 ``cw_reconcile.reconcile_tracking`` ——
        与 deploy_bench 版同语义统一(空读守卫/漂移留证/obs_conflict JSONL 单一实现)。
        """
        session = self._session()
        if session is None:
            return
        from sr_od.application.currency_war.cw_reconcile import reconcile_tracking
        reconcile_tracking(session, bench, deployed, screen, source='director', ctx=self.ctx)

    def _session(self):
        match = getattr(self.ctx, 'cw_match', None)
        return match.session if (match is not None and match.session is not None) else None

    def _match(self):
        return getattr(self.ctx, 'cw_match', None)

    # ===== 环主体(F1 单步契约;抽普通方法便于离线 mock 测,run 只做入口)=====

    @operation_node(name='备战决策环', is_start_node=True, node_max_retry_times=6)
    def run(self) -> OperationRoundResult:
        match = self._match()
        if match is None or match.strategy is None:
            return self.round_fail(status='无 cw_match(对局未初始化)')
        # 环入口:环级计数清零(§4.2b/§7;局级 bail_reason_counts 不清)
        session = match.session
        session.defer_count = 0
        session.prep_phase = 0
        session.prep_phase_retry = 0
        self._executor = PrepActionExecutor(self, self.ctx)
        self._steps = 0
        self._stall = 0
        self._fail_counts = {}
        self._blocked = set()
        self._recovered = set()
        self._recovery_closed_known = {}
        self._recovery_tried = False
        self._cached_state = None
        self._cached_bench = []
        self._cached_deployed = []
        self._cached_vacancy = 0
        self._cached_gold_trusted = False
        # r297(P0③):_probe_node_type 迁至 EnsureShopClosed 后
        #(与 _probe_node_reward 同挂点;原 run() 入口调用已删)。
        return self._run_loop(match)

    def _run_loop(self, match) -> OperationRoundResult:
        """环循环主体(可离线 mock 测):observe → decide → execute → 再 observe。"""
        session = match.session
        from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        # ⚠️ 特效消化等待(用户 2026-08-16 实证):上一步动作(drag 上场/买卡合成)会触发羁绊
        # 特效/升星 overlay(盛会之星/圣杯/银狼升级等)遮挡画面 —— heavy 观察(SIFT/OCR)在特效
        # 帧读 = 污染。环入口先截一帧探「备战标识」,miss(被特效遮)→ 等 1s 重试,最多 3 次
        # 让特效播完再观察(非交互 overlay 播完即走;交互型由下方 event_overlay 检测 bail)。
        # 探针 best-effort(截图/识别异常不阻塞 —— 离线 mock 测试无真画面)。
        # r297(审查 P0①:单锚过弱实锤 16:42:35 deployed 6人读成
        # 1人——「购买经验」按钮在 shop 开/关两态均可见,特效
        # 盖舞台不盖底部按钮时门照样放行;全日志消化门 0 触发
        # 而污染证据 370+682 次):①锚改「备战屏(shop 关)专属
        # 的舞台锚(按钮-出战)」——shop 开态帧不再放行(该帧
        # SIFT 本就不可信);②探 3 次仍不 clean 也**不再
        # fall-through 盲 observe**,bail 重试(外环重进消化)。
        for _try in range(3):
            try:
                _probe = self.screenshot()   # 新鲜帧(review:旧 last_screenshot 短路复用旧帧,miss 重试退化盲等)
                _prep_clean = self.round_by_find_area(
                    _probe, '货币战争-备战', '按钮-出战',
                    crop_first=False).is_success
                if _prep_clean:
                    break
                log.info('[cw][director] 环入口非 clean 备战帧(shop开/特效/overlay)→ 等 1s 消化(try %d)',
                         _try + 1)
                time.sleep(1.0)
            except Exception:   # noqa: BLE001  离线/无画面环境直接放行
                break
        else:
            # 3 次都不 clean:盲 observe 会在毒帧上喂 update_target
            # (P0① 实锤路径)→ bail 交外环重进(而非带病决策)
            return self._bail(match, '环入口帧不clean(特效/overlay未消化)')
        obs = self._observe(heavy=True)   # 环入口重观察 + 对账
        if obs.event_overlay is not None:   # 事件 overlay 挡操作 → 环让位(交外环 handler)
            return self._bail(match, f'事件overlay:{obs.event_overlay}')
        # r287→r292:钩子挂点迁至 EnsureShopClosed 执行成功后
        #(见 _run_loop while 内;此处保留说明,原调用已删)。
        # ADR-0136(M16 死循环 86min 根因):「备战席已满」警告模态下游戏**拒绝一切拖拽/出战** ——
        # Director 若无视警告继续发 DeployMove/StartBattle,全部"源槽未变/未落地"连环失败 → stall
        # 死循环。环入口感知警告(read_bench_full)→ 立即走腾席链破警告(优先升级扩容;点不起 → 卖最弱),
        # 警告解除后才继续常规决策。每次环入口重判(警告可反复出现)。
        from sr_od.application.currency_war.cw_observation import read_bench_full
        _scr_full = getattr(self, 'last_screenshot', None)
        if _scr_full is not None and read_bench_full(self.ctx, _scr_full):
            log.warning('[cw!][director] 备战席已满警告(模态挡拖拽/出战)→ 破警告优先(腾席链)')
            # r2 review#1(P0):曾用 type() 造假 obs(缺 tomes 等字段)→ 策略一读即 AttributeError
            # 炸环。改 dataclasses.replace 从真 obs 派生(全字段保真,仅覆写腾席相关)。
            import dataclasses
            bf_obs = dataclasses.replace(
                obs, box_overlay_open=False, boxes=[], spheres=[],
                free_bench_slots=0, shop_open=False,
                # ADR-0136 补修:横幅在时拖放被游戏拒 → vacancy 置 0 强制走 b(升级)/c(卖最弱)
                deploy_vacancy=0)
            action = match.strategy.decide_prep_action(bf_obs, session, config)
            progressed, detail = self._executor.execute(action)
            log.info(f'[cw][director] 破警告动作 {type(action).__name__} → {"✓" if progressed else "✗"} {detail}')
            # r11 review #2(盲节点可观测性):破墙路径此前零遥测——M55 r3 的 59 金+双跳级全发生在
            # decisions.jsonl 外(复盘盲区)。破墙动作也记一条(类名带 BenchFull 前缀,审计可辨)。
            # r1 review#4:曾传 type() 造假对象(非 dataclass)→ serialize_action TypeError 被吞
            # → 破墙遥测从未落盘。改 exec_events 通道(本就为执行事件设计)。
            try:
                from sr_od.application.currency_war import cw_telemetry

                if obs.state is not None:
                    _bf_rid = cw_telemetry.current_run_id() or '-'
                    if _bf_rid == '-' and self.ctx.cw_match is not None:
                        _bf_rid = f'match:{id(self.ctx.cw_match) & 0xffff:x}'   # 与 _record_exec_obs 兜底一致
                    # r98 类型 gate 抓真 bug:record_exec_event 是 TelemetryRecorder 类方法,
                    # 模块级直调 = AttributeError(此前被 except 吞 → 破墙遥测从未落盘)。
                    cw_telemetry.get_recorder().record_exec_event(
                        run_id=_bf_rid,
                        round_num=obs.state.round_num,
                        action_family=f'BenchFull_{type(action).__name__}',
                        screen='battle_prep', event='bench_full_break',
                        reason='备战席满破墙')
            except Exception:   # noqa: BLE001  遥测 best-effort
                pass
            return self.round_wait(status=f'备战席已满,已试破警告({type(action).__name__})', wait=1.0)
        # MED-4:战略层 update_target 环入口调一次(doc 15 §6;RunBuyPhase 内 shop.py:166 仍会
        # 调 = P1 允许的双调)。失败不炸环(沿用上轮 target 继续步级决策)。
        # ⚖️ r68 review:**入口先过 HP 新鲜度门再调**(cw_strategy.gated_hp,与 shop.py 同门)——
        # 旧版 obs.state.hp 常是 shop 开态 100 兜底 → maybe_pivot 在假 hp 上做信号1涌现判定,
        # 10s 后 shop 侧真 hp 又触发信号3保命反向换线(r68 实证:hp=100 转红A → hp=26 转DOT队,
        # 同节点两次方向相反 pivot = comp churn 主燃料)。
        if obs.state is not None:
            from sr_od.application.currency_war.cw_strategy import gated_hp
            _os = obs.state
            # r73 RC3:dual 态从 session 拷回(单一源;read 新对象默认 False 会冲掉双轨门)
            _os.dual_track_phase = getattr(session, 'dual_track_phase', False)
            _os_t = ((_os.plane - 1) * 9 + _os.round_num) if (_os.plane and _os.round_num) else None
            _os.hp = gated_hp(_os.hp, session, _os_t,
                              current_readable=bool(getattr(_os, 'hp_readable', True)))
        try:
            match.strategy.update_target(obs.state or GameState(), session, config)
        except Exception as e:  # noqa: BLE001  战略层失败不阻塞步级决策
            log.warning(f'[cw!][director] update_target 异常(沿用旧 target): {e}')
        while True:
            self._steps += 1
            if self._steps > PrepDirector.MAX_STEPS:
                log.warning(f'[cw!][director] 步数>{PrepDirector.MAX_STEPS} → 强制出战(F5)')
                return self._force_battle('步数预算耗尽')
            try:
                action = match.strategy.decide_prep_action(obs, session, config)
            except Exception as e:  # noqa: BLE001  策略异常:上抛 = 本环 fail(§13.2 路径 3)
                log.warning(f'[cw!][director] decide_prep_action 异常: {e}')
                return self.round_fail(status=f'策略决策异常: {e}')
            if not isinstance(action, PrepAction):
                log.warning(f'[cw!][director] 策略输出非 PrepAction: {type(action).__name__}')
                return self.round_fail(status='策略输出非 PrepAction(F3)')
            self._record_step(obs, action)

            # —— 控制流(不走 execute 验证链,§4.2b)——
            if isinstance(action, DeferSpheres):
                session.defer_count += 1
                log.info(f'[cw][director] DeferSpheres(defer={session.defer_count})')
                obs = self._observe(heavy=False)
                continue
            if isinstance(action, BailToOuter):
                return self._bail(match, action.reason or '未注明')

            # —— F3 校验(全集白名单 + 参数;非法:拒绝执行 + stall + 遥测,§13.2 路径 2)——
            err = self._executor.validate(action)
            key = action_key(action)
            if err is not None:
                log.warning(f'[cw!][director] 参数非法 {key}: {err} → 拒绝 + 计 stall')
                self._stall += 1
                gate = self._stall_gate()   # MED-3:拒绝路径也要兜 stall 门(防 55 步空转)
                if gate is not None:
                    return gate
                obs = self._observe(heavy=False)
                continue
            # 屏蔽命中:拒绝执行 + stall + 遥测(策略确定性重提案同动作被拒,M-5)
            if key in self._blocked and not isinstance(action, StartBattle):
                log.warning(f'[cw!][director] 动作已屏蔽 {key} → 拒绝 + 计 stall(M-5)')
                self._stall += 1
                gate = self._stall_gate()   # MED-3:同上
                if gate is not None:
                    return gate
                obs = self._observe(heavy=False)
                continue

            # —— 执行(验证失败路径:计 fail;异常自然上抛 = 本环 fail)——
            try:
                progressed, detail = self._executor.execute(action)
            except Exception as e:  # noqa: BLE001
                log.warning(f'[cw!][director] 执行异常 {key}: {e} → 本环 fail')
                return self.round_fail(status=f'执行异常 {key}: {e}')
            log.info(f'[cw][director] step{self._steps} {key} → {"✓" if progressed else "✗"} {detail}')

            # r292+P0③(r297):reward 采集钩子挂点(EnsureShopClosed
            # 执行成功后=店确定关的可靠时点)。**_probe_node_type
            # 同挂点迁入**(审查 P0③:原挂 run() 入口一次性读,
            # skip 69%——shop 开态帧读不了节点行,与本钩子
            # r280-294 四次静默同病根)。
            if 'EnsureShopClosed' in key and progressed:
                self._probe_node_type()
                self._probe_node_reward()

            if isinstance(action, StartBattle) and progressed:
                return self.round_success('出战(环出口)', wait=3)
            if progressed:
                self._stall = 0
                self._fail_counts.pop(key, None)
            else:
                try:
                    bail = self._on_verify_fail(match, action, key)
                except Exception as e:  # noqa: BLE001  LOW-5:恢复原语点击异常同执行异常路径
                    log.warning(f'[cw!][director] 失败处理/恢复原语异常 {key}: {e} → 本环 fail')
                    return self.round_fail(status=f'失败处理异常 {key}: {e}')
                if bail is not None:
                    return bail
            # 再观察:执行过的游戏动作一律 heavy(结构变化,review H-1);控制流走 light(上方)
            obs = self._observe(heavy=True)
            if obs.event_overlay is not None:   # 动作后浮出事件 overlay(mid-prep 弹出)→ bail
                return self._bail(match, f'事件overlay:{obs.event_overlay}')

    def _record_exec_obs(self, key: str, event: str, reason: str = '') -> None:
        """观测钩子(常驻,27 号能力画像):执行事件落 exec_events.jsonl。

        run_id 兜底:current_run_id → match 短 id。动作族:key 是动作 repr → 取首
        `(` 前类名;bail 类事件 key 是 reason 字符串 → 族归 'bail'。round_num 用
        游戏 轮次(r2#5:环步数重入清零且重复,与 decisions/outcomes 无法对齐;
        last_state.round_num 才是 join key)。best-effort。
        """
        try:
            from sr_od.application.currency_war.cw_telemetry import (
                current_run_id,
                get_recorder,
            )
            run_id = current_run_id() or '-'
            game_round = 0
            _m = self.ctx.cw_match
            if _m is not None:
                run_id = run_id if run_id != '-' else f'match:{id(_m) & 0xffff:x}'
                _st = getattr(_m.session, 'last_state', None)
                if _st is not None:
                    game_round = getattr(_st, 'round_num', 0) or 0
            family = 'bail' if event == 'bail' else (
                key.split('(')[0].split(':')[0].strip() or '?')
            get_recorder().record_exec_event(
                run_id=run_id, round_num=game_round,
                action_family=family,
                screen='battle_prep', event=event, reason=reason or key,
                retry_count=self._fail_counts.get(key, 0))
        except Exception:   # noqa: BLE001  观测 best-effort
            pass

    def _stall_gate(self) -> OperationRoundResult | None:
        """环级强制出战门(§7 H-2b):stall≥5 且恢复已试尽 → 强制 StartBattle(F5)。

        MED-3:所有计 stall 的路径(验证失败/参数非法/屏蔽拒绝)统一走本门 —— 否则屏蔽后
        策略确定性重提案会 55 步空转到 MAX_STEPS 才兜住。
        """
        if self._stall >= PrepDirector.STALL_LIMIT and self._recovery_tried:
            log.warning(f'[cw!][director] stall≥{PrepDirector.STALL_LIMIT} 且恢复已试尽 → 强制出战(F5)')
            return self._force_battle('stall+恢复试尽')
        return None

    def _on_verify_fail(self, match, action: PrepAction, key: str) -> OperationRoundResult | None:
        """验证失败处理(review H-2 修订):连败 2 → 恢复原语(一次/实例)→ 仍连败 2 → 分型
        bail(关过已知弹层 = 弹层顽固)/屏蔽(无弹层 = 状态类失败)。返回非 None = 环终止。"""
        self._fail_counts[key] = self._fail_counts.get(key, 0) + 1
        fails = self._fail_counts[key]
        self._stall += 1
        # 观测钩子(常驻,27 号能力画像数据源):失败计数落盘(原来局终即弃)
        self._record_exec_obs(key, 'fail', f'fails={fails}')
        if fails >= PrepDirector.FAIL_TO_RECOVER and key not in self._recovered:
            # 首次连败门:恢复原语(一次/动作实例),重置计数给恢复后重试窗
            prim, closed_known = try_recovery(self, self.ctx)
            self._recovered.add(key)
            self._recovery_closed_known[key] = closed_known
            self._recovery_tried = True
            log.info(f'[cw][director] {key} 连败{fails} → 恢复原语({prim}),重试窗开启')
            time.sleep(1.0)
            self._fail_counts[key] = 0
            return None
        if fails >= PrepDirector.FAIL_TO_RECOVER and key in self._recovered:
            # 恢复后仍连败(恢复无效)→ 分型(§7 优先级条落地语义,ADR-0123):
            # 关过已知弹层仍败 = 弹层顽固/未知 → 环让位(bail 交外环弹层分支/停机钩子);
            # 无已知弹层(兜底点空白)仍败 = 状态/识别类失败 → 本环屏蔽(策略换路)。
            # ClickSpheres 特判(live M12 二停):假球点击打开的道具详情弹层被恢复关掉 →
            # closed_known=True 误走 bail 分支 ×3 停机。收球的恢复无效本质是识别类失败(假球),
            # 一律走 shield+defer(那个"弹层"是我们自己点出来的,非阻塞弹层)。
            if self._recovery_closed_known.get(key, False) and not isinstance(action, ClickSpheres):
                log.warning(f'[cw!][director] {key} 恢复(关弹层)后仍连败 → BailToOuter(弹层顽固)')
                return self._bail(match, f'恢复无效-弹层:{key}')
            if not isinstance(action, StartBattle):
                self._blocked.add(key)
                self._record_exec_obs(key, 'blocked', '恢复无效-状态类')
                # r93 审计 46336415:DeployMove 被屏蔽 = 落点被游戏拒(同名在场/行限制等)
                # → 写 session.deploy_fail_counts,策略腾席链跳过该角色(防下轮同卡重提案;
                # 第14局 r9 藿藿 5 连败实证)。备战场面变化后 heavy 对账自然换候选。
                try:
                    if isinstance(action, DeployMove):
                        _bc = (getattr(match.session, 'tracked_bench_chars', None) or [])
                        _hit = next((b for b in _bc if b.slot == action.from_slot), None)
                        if _hit is not None and _hit.char_id:
                            match.session.deploy_fail_counts[_hit.char_id] = (
                                match.session.deploy_fail_counts.get(_hit.char_id, 0) + 1)
                            log.info('[cw-director] DeployMove 失败记忆 %s(腾席链将跳过,换下一候选)',
                                     _hit.char_id)
                except Exception:   # noqa: BLE001  记忆 best-effort
                    pass
            if isinstance(action, ClickSpheres):
                match.session.defer_count = max(match.session.defer_count, 2)
            if isinstance(action, OpenTome):
                # r15 review P0-②:defer 门对 OpenTome 曾是死码(defer 只由 DeferSpheres/
                # ClickSpheres 置位)——失败置 defer 让策略侧门(规则 2)真正生效。
                match.session.defer_count = max(match.session.defer_count, 2)
            log.warning(f'[cw!][director] {key} 恢复(无弹层)后仍连败 → 本环屏蔽(策略须换路)')
            self._fail_counts[key] = 0   # 屏蔽后拒绝走 stall 路径,计数归零防重复触发
            return None
        # 环级强制出战门(stall≥5 且恢复已试尽,§7 H-2b)
        return self._stall_gate()

    def _bail(self, match, reason: str) -> OperationRoundResult:
        """环让位:交外环处理(§4.2b;外环重入重建 Director 时环级计数全清零)。"""
        session = match.session
        self._record_exec_obs(reason, 'bail', '环让位')
        session.bail_reason_counts[reason] = session.bail_reason_counts.get(reason, 0) + 1
        n = session.bail_reason_counts[reason]
        if n >= PrepDirector.BAIL_SAME_REASON_DIAG:
            # MED-7:同因 bail≥3 = 外环 3 次未消化该弹层(bail↔重入 ping-pong,MAX_ITER 兜底
            # 需多小时)→ 升级停机钩子(方案 D):存证 + stop_running 保画面待 AI 建档/排查。
            log.warning(f'[cw!][director] 同因 bail ×{n}: {reason} → 升级停机(ping-pong,保画面建档)')
            import contextlib
            with contextlib.suppress(Exception):
                self.save_screenshot(prefix='bail_pingpong')
            rc = getattr(self.ctx, 'run_context', None)
            if rc is not None:
                with contextlib.suppress(Exception):
                    rc.stop_running()
            return self.round_fail(status=f'同因 bail ×{n}({reason}) 停机待建档')
        log.info(f'[cw][director] BailToOuter({reason}) → 交外环')
        return self.round_success(f'BailToOuter({reason})', wait=1)

    def _force_battle(self, why: str) -> OperationRoundResult:
        """F5 出口兜底:框架强制出战(策略挂了流程不断;StartBattle 豁免屏蔽)。"""
        if self._executor is None:
            return self.round_fail(status='无执行器')
        try:
            progressed, detail = self._executor.execute(StartBattle())
        except Exception as e:  # noqa: BLE001  L-4:强制出战异常不裸传(防整环 retry 重跑)
            log.warning(f'[cw!][director] 强制出战异常({why}): {e}')
            return self.round_fail(status=f'强制出战异常({why}): {e}')
        if progressed:
            return self.round_success(f'强制出战({why})', wait=3)
        return self.round_fail(status=f'强制出战失败({why}): {detail}')

    def _probe_node_type(self) -> None:
        """[观测] 备战入场读节点行序列(read_node_sequence)→ log。

        自 battle_prep._probe_node_type 搬入(P1 挂载切换,doc §7 L1)。read_node_sequence =
        HoughCircles 动态定圆 + HSV 三态 + Hu 匹配 + OCR(见 cw_node_reader)。
        未识别图标采集钩子(版本前哨,保留):未来圆 hu_dist > 阈值 → 裁图标存盘。
        ⚠️ 已知误报(2026-08-16 复盘):历史 61 张采集全是**宝箱(奖励)图标的小尺寸 Hu 漂移**
        (idx 4/5/7 远处节点,非新类型)——HU_DIST_UNRECOGNIZED=2.8 对远距小图标过严,
        修阈值/过滤属 reader 校准待办(与扑满无关:扑满=奖励图标已实证,M45 current:reward
        直接命中)。真新类型出现时本钩子仍是唯一自动捕获渠道,保留。"""
        try:
            from sr_od.application.currency_war.cw_node_reader import (
                HU_DIST_UNRECOGNIZED,
                NODE_ROW_RECT,
            )
            from sr_od.application.currency_war.cw_observation import read_node_sequence
            screen = self.screenshot()
            slots = read_node_sequence(self.ctx, screen)
            if not slots:
                log.info('[cw-director][nodeseq] skip(模板未加载 / 非 clean 备战帧)')
                return
            summary = ', '.join(
                f'{s.idx}:{s.state}:{s.node_type}' + (f'({s.hu_dist:.1f})' if s.hu_dist else '')
                for s in slots)
            log.info(f'[cw-director][nodeseq] n={len(slots)} | {summary}')
            self._capture_unrecognized_node_icons(screen, slots, NODE_ROW_RECT, HU_DIST_UNRECOGNIZED)
            # r265:current 槽类型写 session(battle_loop on_round_end 消费——
            # 节点类型分层遥测;权威源=备战节点行,替代结算屏 OCR 推断)。
            # r266(current 恒 None 修复):current 高亮态 Hu 不匹配(模板只对
            # future 生效)+OCR 标签错位守卫 → current 直读恒 None。
            # 修:**last-known upcoming**——上一备战帧 upcoming[i] 就是本轮
            # current(节点行固定序列左移);本帧 upcoming 同时存下轮用。
            try:
                _sess = (self.ctx.cw_match.session
                         if self.ctx.cw_match is not None else None)
                if _sess is not None:
                    # r290(current 覆盖链改左移优先):OCR 标签
                    # 位置门(r80)拦不住相邻同类标签(局20 实证:
                    # r3 结算屏「战斗」vs current 读 reward——
                    # reward 标签恰在 current 下方 x 对上)→
                    # current 直读不可信。改:**左移推断优先**
                    # (上帧 upcoming[0],r266 已有),OCR 标签
                    # 只在左移无值时兜底(开局首帧)。
                    _prev = getattr(_sess, 'upcoming_types', None) or []
                    _direct = _prev[0] if _prev else None
                    if _direct is None:
                        _cur = next((s for s in slots
                                     if s.state == 'current'), None)
                        _direct = _cur.node_type if _cur is not None else None
                    _sess.node_type_current = _direct
                    # 存本帧 upcoming(下轮左移用; idx 升序)
                    _sess.upcoming_types = [
                        s.node_type for s in sorted(
                            (x for x in slots if x.state == 'upcoming'),
                            key=lambda x: x.idx) if s.node_type]
            except Exception:   # noqa: BLE001  best-effort 写入
                pass
        except Exception as e:  # noqa: BLE001  live 验证 best-effort,失败不阻塞备战
            log.info(f'[cw-director] nodeseq skip: {e}')

    def _probe_node_reward(self) -> None:
        """[采集钩子·临时] 节点奖励明细采集(r280;用户交办,采完删)。

        用户口述(2026-08-23,最高权威):备战画面商店按钮左侧六边形
        图标+数字 → 点开可见本节点预期金币奖励明细(连胜 0-1→1金,
        2-4→2金…+ 节点基础奖励)。**先采集一段时间,看基础奖励会
        不会变,之后再接策略**。

        实现capture-only(零风险):每节点一次——点六边形(1555,930,
        实证 2026-08-23)→ 截图存 shots(cw_reward 前缀)→ OCR 全
        文本记 log → 点空白(960,150)关弹窗。不解析(解析等样本攒
        够后按真实弹窗结构写);关闭若失败下一轮备战自愈(弹窗点
        备战标识会消,采集门每节点一次不会刷屏)。
        """
        import time as _time

        try:
            _match = self.ctx.cw_match
            if _match is None:
                return
            _sess = _match.session
            _key = getattr(_sess, '_reward_probed_key', None)
            from sr_od.application.currency_war.cw_observation import (
                read_phase_round,
            )
            # r294→r299(五次实测收敛):关店动画实测 ~3s;原
            # 0.8s×3(检测消耗次数)3 连 miss 全耗在动画窗。
            # 修:等待与检测分离——总窗 4.5s,检测不消耗次数;
            # clean(备战关态锚「按钮-出战」——shop 开屏无此
            # area,双态区分)即出。
            _deadline = _time.time() + 4.5
            _clean = False
            _plane = _round = None
            while _time.time() < _deadline:
                screen0 = self.screenshot()
                if self.round_by_find_area(
                        screen0, '货币战争-备战',
                        '按钮-出战').is_success:
                    _plane, _round = read_phase_round(self.ctx, screen0)
                    _clean = True
                    break
                _time.sleep(0.6)
            if not _clean:
                log.info('[cw][reward-probe] 备战帧未稳定(关店动画/'
                         '特效),本步跳过下轮再试')
                return
            cur_key = f'{_plane}:{_round}'
            if _key == cur_key:   # 本节点已采
                return
            _sess._reward_probed_key = cur_key
            # r302:controller.click 需 Point 对象(裸 int 在坐标
            # 转换层炸 'int' has no .x——四代 skip 的共同根因)
            from one_dragon.base.geometry.point import Point
            self.ctx.controller.click(Point(1555, 930))
            _time.sleep(1.0)
            screen1 = self.screenshot()
            # r300b:cw_shot_unique 签名 (image, label) 位置参——
            # 首版 prefix= kwarg 在截图行即 TypeError(catch 吞,
            # 截图/OCR 全没执行)
            from sr_od.application.currency_war.cw_observe import cw_shot_unique
            cw_shot_unique(screen1, 'cw_reward')
            # r300(实测 'int' object has no attribute 'x'):
            # OCR 走框架 _ocr 惯例(rect 必传;弹窗内容区实测
            # x1000-1560,y370-1010)
            from one_dragon.base.geometry.rectangle import Rect
            from sr_od.application.currency_war.cw_obs_core import _ocr
            _texts = [r.data for r in _ocr(
                self.ctx, screen1, Rect(1000, 370, 1560, 1010))]
            log.info('[cw][reward-probe] plane=%s round=%s texts=%s',
                     _plane, _round, _texts[:20])
            self.ctx.controller.click(Point(960, 150))   # 关弹窗(空白,r302 Point)
            _time.sleep(0.6)
        except Exception as e:   # noqa: BLE001  采集 best-effort,不阻塞备战
            log.info(f'[cw][reward-probe] skip: {e}')

    def _capture_unrecognized_node_icons(self, screen, slots, node_row_rect, hu_threshold) -> None:
        """未识别图标采集(版本前哨):未来圆 Hu 无显著最近 → 裁图标存盘(内容哈希去重)。

        仅 upcoming 槽(判态已修 V 门,变暗过去节点不再混入);RGB 裁剪存盘(颜色信息保留,
        模板同样 RGB——2026-08-16 用户指导)。
        r80(审计 P1-3):**同 idx 300s 时间窗防抖** —— 内容哈希去重防不住备战帧微变
        (光标/金币动画/抗锯齿 → 哈希必新),同 idx 每帧重采刷屏(2-7 实证 idx4/5 连发);
        已知误报源是远距小图标 Hu 漂移(61 张复盘),300s 窗足够人工/离线跟进,新类型
        (真未识别)首采不受影响。
        """
        import time as _time

        from sr_od.application.currency_war.cw_observe import cw_shot_unique
        icon_r = 24   # 采集分析窗(略 > 分类窗 _SAMPLE_R=18,多上下文)
        x0, y0, x1, y1 = node_row_rect
        row = screen[y0:y1, x0:x1]
        now = _time.monotonic()
        for s in slots:
            if s.state != 'upcoming' or s.hu_dist is None or s.hu_dist <= hu_threshold:
                continue
            if now - _NODE_ICON_SHOT_TS.get(s.idx, 0.0) < 300:
                continue   # 同 idx 时间窗内已采过(帧微变哈希必新,内容哈希去重失效;r80 审计c:module-level 跨环存活)
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
            cw_telemetry.record_decision(
                st if st is not None else GameState(),
                target_comp=(self._session().target_comp.name
                             if self._session() is not None and self._session().target_comp else ''),
                candidate_scores={},
                eval_breakdown={'prep_step': float(self._steps)},
                actions=[action],   # type: ignore[list-item]  PrepAction 与旧 Action 并存(P2 归一)
                gold_point=False,   # r68 review:步进记录不进 gold_trajectory(每回合一采样,shop 侧采)
            )
        except Exception as e:  # noqa: BLE001  遥测失败不阻塞环
            log.debug(f'[cw-director] telemetry skip: {e}')
