
"""货币战争 奖励球(晶矿)收取 op(B6;2026-08-14 首见机制)。

通关奖励节点后备战右侧面板出球形奖励(read_reward_spheres HoughCircles 识别,
color=gold/blue/gray)。点球即开启:金币/装备即时入账;角色或补给箱落备战席占 1 槽;
**备战席满时球点不动**(点空 click 无效果,球保留)→ 必须先开箱/腾席(CwScreenSupply 在前)。

流程:开箱(若有)→ 逐球点击(大球优先)→ 每球重读验消失;掉箱则开箱续收;
球数不减 → 本轮中断(席满或识别漂;外层腾席后下轮再收,防死循环点空球)。
"""
import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.obs.cw_identity_obs import (
    read_reward_spheres,
    read_supply_boxes,
)
from sr_od.application.currency_war.obs.cw_observation import read_gold_settled
from sr_od.application.currency_war.operations.cw_screen.cw_screen_supply import (
    CwScreenSupply,
)
from sr_od.application.currency_war.telemetry.recorder import record_modality_gold
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwOpCollectSpheres(SrOperation):
    """收奖励球:开箱(若有)→ 逐球点击 → 每球验消失;席满点不动则停(外层腾席后重试)。"""

    # 单轮最多点球数(防识别抖动死循环;正常一节点 ≤8 球)
    MAX_CLICKS: int = 12

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-奖励球收取')

    def _modality_round_key(self) -> tuple[int, int]:
        """归属轮号 (plane, round_num):session.last_state 快照(奖励面板属
        上次战斗节点,overlay 态 board 不可读的兜底口径与 record_event_choice
        同);无 match/离线 = (0, 0),遥测行由 run_id 门控自然缺席。"""
        _m = getattr(self.ctx, 'cw_match', None)
        _st = getattr(getattr(_m, 'session', None), 'last_state', None)
        return (int(getattr(_st, 'plane', 0) or 0),
                int(getattr(_st, 'round_num', 0) or 0))

    def _record_gold(self, gold_before: int | None,
                     gold_after: int | None) -> None:
        """收取前后金括号落账(模态期金去向通道;best-effort 不阻断业务)。"""
        try:
            plane, rnd = self._modality_round_key()
            record_modality_gold('spheres', plane, rnd,
                                 gold_before, gold_after)
        except Exception as e:   # noqa: BLE001  观测 best-effort,不阻断收取
            log.debug(f'[cw-sphere] 金括号落账失败(不阻断): {e}')

    @operation_node(name='奖励球收取', is_start_node=True, node_max_retry_times=6)
    def handle(self) -> OperationRoundResult:
        # 0) 有补给箱先开箱腾席(席满是点球硬阻塞;开箱后席位 +1)
        CwScreenSupply(self.ctx).execute()
        clicked = 0
        screen = self.screenshot()
        # 模态期金去向通道:收取前金基线(金球点开即入账;None=OCR miss,
        # 落账 delta=None 读端按不可信分型,不猜)
        gold_before: int | None = read_gold_settled(self.ctx, screen)
        while clicked < CwOpCollectSpheres.MAX_CLICKS:
            spheres = read_reward_spheres(self.ctx, screen)
            if not spheres:
                log.info('[cw-sphere] 奖励面板无球 → 收取完成')
                self._record_gold(gold_before, read_gold_settled(self.ctx, self.screenshot()))
                return self.round_success(wait=1)
            before = len(spheres)
            # 大球优先(gold r~44 > blue r~32 > gray r~18;高价值先收防中断丢失)
            color, center, r = max(spheres, key=lambda t: t[2])
            log.info(f'[cw-sphere] 点球 {color} r={r} @({center.x},{center.y}) 剩{before}')
            self.ctx.controller.mouse_move(center)   # bug#1 缓解
            self.ctx.controller.click(center)
            clicked += 1
            time.sleep(1.2)
            screen = self.screenshot()
            after_spheres = read_reward_spheres(self.ctx, screen)
            # 点球掉箱 → 弹武装箱链:开箱(腾席+得装备)后继续收剩余球
            if read_supply_boxes(self.ctx, screen):
                log.info('[cw-sphere] 掉补给箱 → 开箱后继续收球')
                CwScreenSupply(self.ctx).execute()
                screen = self.screenshot()
                continue
            if len(after_spheres) >= before:
                # 球数不减:席满点不动(机制)或识别漂 → 停,交外层腾席后下轮重试
                log.info(f'[cw-sphere] 球数未减({before}→{len(after_spheres)}) → 疑席满,中断本轮')
                self._record_gold(gold_before, read_gold_settled(self.ctx, screen))
                return self.round_success('球点不动(疑席满),腾席后下轮再收', wait=1)
        self._record_gold(gold_before, read_gold_settled(self.ctx, self.screenshot()))
        return self.round_success(wait=1)
