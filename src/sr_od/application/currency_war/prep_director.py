# 未验证(P1 新建,2026-08-14;设计 doc 15 v7 + ADR-0123;环流程待实机跑验)

"""货币战争 备战决策环(PrepDirector)—— 两层环之内环(框架层;doc 15)。

**框架不含任何玩法判断**:何时收球/卖谁/何时出战 = 策略(CwStrategy.decide_prep_action);
本模块只保证八项框架不变式(F1-F8,doc 15 §5.0):
- F1 单步契约: 每步 = observe → decide_prep_action → execute(带验证) → 再 observe
- F2 观察真实: obs 只由现成 reader 产出;shop 开关互斥由框架校验读取前置
- F3 动作合法域: 策略输出须在动作全集内;框架校验参数后执行
- F4 验证与防护: 每动作完成验证;fail 计数/stall 屏蔽/预算强制出战(§7)
- F5 出口兜底: 策略不出战且 stall/预算耗尽 → 框架强制出战
- F6 无状态策略: 环不污染策略实例;跨步意图走 StrategySession
- F7 可换策略: strategy 由配置选(11 号);换策略只换决策
- F8 可回放: obs+action 序列落 telemetry(P1 仅落盘)

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
    read_bench_chars,
    read_reward_spheres,
    read_supply_boxes,
)
from sr_od.application.currency_war.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.cw_observation import (
    read_deploy_cap,
    read_deployed_count,
    read_game_state,
)
from sr_od.application.currency_war.cw_state import BenchChar, GameState
from sr_od.application.currency_war.prep_actions import (
    BailToOuter,
    DeferSpheres,
    OpenBox,
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
    """
    state: GameState | None = None        # 重读(阶段边界);gold 仅 shop_open 时可信(关态读空)
    bench_chars: list[BenchChar] = field(default_factory=list)   # 环入口 SIFT + 轻步 slot_occupied
    deployed_chars: list[BenchChar] = field(default_factory=list)
    spheres: list = field(default_factory=list)       # read_reward_spheres [(color, Point, r)]
    boxes: list = field(default_factory=list)         # read_supply_boxes [(slot, Point)]
    free_bench_slots: int = 0           # 9 − 占用(角色+箱都占席)
    deploy_vacancy: int = 0             # deploy_cap − deployed_count
    shop_open: bool = False             # 锚点「按钮-收起」可见
    box_overlay_open: bool = False      # 武装箱 overlay(标识-请选择)
    front_occupied: set = field(default_factory=set)  # 前排占用物理槽位号
    back_occupied: set = field(default_factory=set)
    front_size: int = 4
    back_size: int = 6
    overlay_state: str | None = None    # P5
    overlay_options: list | None = None # P5
    shop_cards: list | None = None      # P1 恒 None(仅买牌阶段刷新)


class PrepDirector(SrOperation):
    """备战决策环:观察驱动单步决策,替代 BattlePrepCycle 固定序列(P1)。

    单「决策环」节点 + 内部 while;环级预算 MAX_STEPS(步数)与 STALL_LIMIT(零进展)
    兜底强制出战(F5);ping-pong 由外环 MAX_ITER=2000 承担(勿引 node_max_retry —— round_wait
    不消耗 node 重试预算,operation.py:453-461 仅 RETRY 递增;doc 15 §7 v7 M-1)。
    """

    # 环级预算(§7 环级:步数>60 或 stall≥5 且恢复已试尽 → 强制 StartBattle;实跑校准 §10)
    MAX_STEPS: ClassVar[int] = 60
    STALL_LIMIT: ClassVar[int] = 5
    # 同动作连败 → 恢复原语 → 仍败 → bail(§7 优先级:恢复先于屏蔽双响应)
    FAIL_TO_RECOVER: ClassVar[int] = 2
    BAIL_SAME_REASON_DIAG: ClassVar[int] = 3   # 同因 bail ≥3 → [cw!] 升诊断(局级计数)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-备战决策环')
        self._executor: PrepActionExecutor | None = None
        self._steps: int = 0
        self._stall: int = 0
        self._fail_counts: dict[str, int] = {}      # 动作实例键 → 连续验证失败次数
        self._blocked: set[str] = set()             # 本环屏蔽动作实例键(§7;StartBattle 豁免)
        self._recovery_tried: bool = False          # 本环恢复原语是否已试(强制出战门)
        self._last_action_key: str = ''
        self._bench_pts = []                        # screen_info 槽位中心(首步惰性读)

    # ===== 观察(F2:只由现成 reader 产出)=====

    def _observe(self, heavy: bool) -> PrepObservation:
        """组装备战观察。heavy=True 环入口/结构变化(SIFT + state 重读);False 轻步(CV 级)。"""
        screen: MatLike = self.screenshot()
        obs = PrepObservation()
        if not self._bench_pts:
            self._bench_pts = row_area_centers(self.ctx, '备战栏')
        # 轻:球/箱/overlay/占用
        obs.spheres = read_reward_spheres(self.ctx, screen)
        obs.boxes = read_supply_boxes(self.ctx, screen)
        obs.shop_open = self.round_by_find_area(
            screen, SHOP_SCREEN_NAME, '按钮-收起', crop_first=False).is_success
        obs.box_overlay_open = self.round_by_find_area(
            screen, '货币战争-备战-武装箱选择', '标识-请选择', crop_first=False).is_success
        occupied = [i + 1 for i, p in enumerate(self._bench_pts)
                    if slot_occupied(screen, int(p.x), int(p.y))]
        obs.free_bench_slots = max(0, len(self._bench_pts) - len(occupied))
        # 重:身份/星级/GameState/占位集(环入口 + 结构变化)
        if heavy:
            templates = self._get_templates()
            if templates is not None:
                obs.bench_chars = read_bench_chars(self.ctx, screen, templates)
                obs.deployed_chars = self._identity_obs_read_deployed(templates)
                self._reconcile_tracking(obs.bench_chars, obs.deployed_chars)
            st = read_game_state(self.ctx, screen)
            st.bench = list(obs.bench_chars or self._session().tracked_bench_chars)
            obs.state = st
            self._session().last_state = st
            cap = read_deploy_cap(self.ctx, screen)
            dep_n = read_deployed_count(self.ctx, screen)
            if cap is not None and dep_n is not None:
                obs.deploy_vacancy = max(0, cap - dep_n)
        # 排占用(轻,CV;front/back 槽中心)
        front_pts = row_area_centers(self.ctx, '前排')
        back_pts = row_area_centers(self.ctx, '后排')
        obs.front_size = len(front_pts)
        obs.back_size = len(back_pts)
        obs.front_occupied = {i + 1 for i, p in enumerate(front_pts)
                              if slot_occupied(screen, int(p.x), int(p.y))}
        obs.back_occupied = {i + 1 for i, p in enumerate(back_pts)
                             if slot_occupied(screen, int(p.x), int(p.y))}
        return obs

    def _identity_obs_read_deployed(self, templates):
        from sr_od.application.currency_war.cw_identity_obs import read_deployed_chars

        return read_deployed_chars(self.ctx, self.last_screenshot, templates)

    def _get_templates(self):
        """avatar SIFT 模板(缓存 ctx;同 DeployBench._get_templates)。"""
        from pathlib import Path

        from sr_od.application.currency_war.currency_war_char_id import (
            load_avatar_templates,
        )

        cached = getattr(self.ctx, 'cw_portrait_templates', None)
        if cached is not None:
            return cached
        portrait_dir = Path(__file__).resolve().parents[5] / 'assets/template/character_cw_portrait'
        if not portrait_dir.is_dir():
            log.warning(f'[cw-director] 立绘库目录不存在 {portrait_dir},重观察退 tracking')
            return None
        templates = load_avatar_templates(portrait_dir)
        self.ctx.cw_portrait_templates = templates
        return templates

    def _reconcile_tracking(self, bench: list[BenchChar], deployed: list[BenchChar]) -> None:
        """环入口对账(§3:read≠tracking 漂移是既有 bug 源 → SIFT 真值重置 tracking)。

        继任宿主:deploy_bench._reconcile_tracking + battle_prep._verify_recognition(P1 挂载
        切换搬入;star 用 read_star 实机金星,同 D-12 语义)。read 失败(templates None)不动。
        """
        session = self._session()
        if session is None:
            return
        old_b = [bc.char_id for bc in session.tracked_bench_chars]
        old_d = [bc.char_id for bc in session.tracked_deployed]
        if bench is not None:
            session.tracked_bench_chars = list(bench)
        if deployed is not None:
            session.tracked_deployed = list(deployed)
        new_b = [bc.char_id for bc in (bench or [])]
        new_d = [bc.char_id for bc in (deployed or [])]
        if old_b != new_b or old_d != new_d:
            log.info(f'[cw][director] 对账纠漂:bench {old_b}→{new_b} | deployed {old_d}→{new_d}')

    def _session(self):
        match = getattr(self.ctx, 'cw_match', None)
        return match.session if (match is not None and match.session is not None) else None

    def _match(self):
        return getattr(self.ctx, 'cw_match', None)

    # ===== 环主体(F1 单步契约)=====

    @operation_node(name='备战决策环', is_start_node=True, node_max_retry_times=6)
    def run(self) -> OperationRoundResult:
        match = self._match()
        if match is None or match.strategy is None:
            return self.round_fail(status='无 cw_match(对局未初始化)')
        # 环入口:环级计数清零(§4.2b/§7;局级 bail_reason_counts 不清)
        session = match.session
        session.defer_count = 0
        session.prep_phase = 0
        self._executor = PrepActionExecutor(self, self.ctx)
        self._steps = 0
        self._stall = 0
        self._fail_counts = {}
        self._blocked = set()
        self._recovery_tried = False

        from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
        config = CurrencyWarConfig(self.ctx.current_instance_idx)

        self._probe_node_type()   # [采集钩子·临时] 节点类型标定(自 battle_prep 搬入;采完删)
        obs = self._observe(heavy=True)   # 环入口重观察 + 对账
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
                reason = action.reason or '未注明'
                session.bail_reason_counts[reason] = (
                    session.bail_reason_counts.get(reason, 0) + 1)
                n = session.bail_reason_counts[reason]
                if n >= PrepDirector.BAIL_SAME_REASON_DIAG:
                    log.warning(f'[cw!][director] 同因 bail ×{n}: {reason}(ping-pong 诊断)')
                log.info(f'[cw][director] BailToOuter({reason}) → 交外环')
                return self.round_success(f'BailToOuter({reason})', wait=1)

            # —— F3 参数校验(非法:拒绝执行 + stall + 遥测,§13.2 路径 2)——
            err = self._executor.validate(action)
            key = action_key(action)
            if err is not None:
                log.warning(f'[cw!][director] 参数非法 {key}: {err} → 拒绝 + 计 stall')
                self._stall += 1
                obs = self._observe(heavy=False)
                continue
            # 屏蔽命中:拒绝执行 + stall + 遥测(策略确定性重提案同动作被拒,M-5)
            if key in self._blocked and not isinstance(action, StartBattle):
                log.warning(f'[cw!][director] 动作已屏蔽 {key} → 拒绝 + 计 stall(M-5)')
                self._stall += 1
                obs = self._observe(heavy=False)
                continue

            # —— 执行(验证失败路径:计 fail;异常自然上抛 = 本环 fail)——
            try:
                progressed, detail = self._executor.execute(action)
            except Exception as e:  # noqa: BLE001
                log.warning(f'[cw!][director] 执行异常 {key}: {e} → 本环 fail')
                return self.round_fail(status=f'执行异常 {key}: {e}')
            log.info(f'[cw][director] step{self._steps} {key} → {"✓" if progressed else "✗"} {detail}')

            if isinstance(action, StartBattle) and progressed:
                return self.round_success('出战(环出口)', wait=3)
            if progressed:
                self._stall = 0
                self._fail_counts.pop(key, None)
            else:
                self._fail_counts[key] = self._fail_counts.get(key, 0) + 1
                fails = self._fail_counts[key]
                self._stall += 1
                if fails >= PrepDirector.FAIL_TO_RECOVER:
                    # §7 优先级:恢复原语先行(屏蔽/bail 不与恢复双响应)。恢复后重置该动作
                    # 计数,给一次恢复后重试窗;再连败同动作 → 屏蔽本环 + [cw!](策略须换路)。
                    prim = try_recovery(self, self.ctx)
                    self._recovery_tried = True
                    log.info(f'[cw][director] {key} 连败{fails} → 恢复原语: {prim}')
                    time.sleep(1.0)
                    self._fail_counts[key] = 0
                    self._fail_counts[f'{key}#post-recovery'] = 1
                    continue
                # 环级强制出战门(stall≥5 且恢复已试尽,§7 H-2b)
                if (self._stall >= PrepDirector.STALL_LIMIT and self._recovery_tried):
                    log.warning(f'[cw!][director] stall≥{PrepDirector.STALL_LIMIT} 且恢复已试尽 → 强制出战(F5)')
                    return self._force_battle('stall+恢复试尽')
            # 下一步观察:结构变化类(买/部署/装备/开箱)重;纯点击(球)轻
            obs = self._observe(heavy=isinstance(action, (OpenBox, StartBattle)))
            if not progressed:
                # 恢复后仍连败同动作(post-recovery 计数 ≥2)→ 本环屏蔽该动作实例 + [cw!];
                # 环继续(策略须换路;StartBattle 豁免屏蔽;stall 门兜底强制出战,F5)。bail 是
                # 策略动作(显式 BailToOuter),框架不代发 —— 恢复无效≠环让位(可能只是该槽位异常)。
                if self._fail_counts.get(f'{key}#post-recovery', 0) >= PrepDirector.FAIL_TO_RECOVER:
                    if not isinstance(action, StartBattle):
                        self._blocked.add(key)
                    log.warning(f'[cw!][director] {key} 恢复后仍连败 → 本环屏蔽(策略须换路)')

    def _force_battle(self, why: str) -> OperationRoundResult:
        """F5 出口兜底:框架强制出战(策略挂了流程不断;StartBattle 豁免屏蔽)。"""
        if self._executor is None:
            return self.round_fail(status='无执行器')
        progressed, detail = self._executor.execute(StartBattle())
        if progressed:
            return self.round_success(f'强制出战({why})', wait=3)
        return self.round_fail(status=f'强制出战失败({why}): {detail}')

    def _probe_node_type(self) -> None:
        """[采集钩子·临时] 备战入场读节点行序列(read_node_sequence)→ log + 未识别图标采集。

        自 battle_prep._probe_node_type 搬入(P1 挂载切换,doc §7 L1)。read_node_sequence =
        HoughCircles 动态定圆 + HSV 三态 + Hu 匹配 + OCR(见 cw_node_reader)。未识别图标
        (hu_dist > 阈值:扑满 / 新节点类型)→ 存图标离线分析加模板。扑满模板补上 +
        session.node_types 生产接线后 → 删本方法 + run 调用(CLAUDE.md「两种钩子」)。"""
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
        except Exception as e:  # noqa: BLE001  live 验证 best-effort,失败不阻塞备战
            log.info(f'[cw-director] nodeseq skip: {e}')

    def _capture_unrecognized_node_icons(self, screen, slots, node_row_rect, hu_threshold) -> None:
        """[采集钩子·临时] 未来圆 Hu 无显著最近(hu_dist > 阈值)→ 裁图标存盘(同 battle_prep 逻辑)。"""
        from sr_od.application.currency_war.cw_observe import cw_shot_unique
        icon_r = 24   # 采集分析窗(略 > 分类窗 _SAMPLE_R=18,多上下文);临时常量随钩子删
        x0, y0, x1, y1 = node_row_rect
        row = screen[y0:y1, x0:x1]
        for s in slots:
            if s.state != 'upcoming' or s.hu_dist is None or s.hu_dist <= hu_threshold:
                continue
            yc0, yc1 = max(0, s.cy - icon_r), s.cy + icon_r
            xc0, xc1 = max(0, s.cx - icon_r), s.cx + icon_r
            fn = cw_shot_unique(row[yc0:yc1, xc0:xc1], f'node_unknown_{s.idx}')
            if fn:
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
            )
        except Exception as e:  # noqa: BLE001  遥测失败不阻塞环
            log.debug(f'[cw-director] telemetry skip: {e}')
