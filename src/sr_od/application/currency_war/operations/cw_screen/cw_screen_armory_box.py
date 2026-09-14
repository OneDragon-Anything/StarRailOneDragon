"""货币战争 道具获得弹窗 op(「简易武装箱」类说明弹窗;2026-08-15 M19 首见停机建档,M20 实锤机制)。

机制(M20 17:37-18:05 实证,3 候选点击坐标全无反应 + × 关闭露底层屏):
- 弹窗 = **获得道具时的说明弹窗**(标题「简易武装箱」+ 说明「点击后开启…从四件简易装备中选择
  一件获得。该道具使用后消失」),叠在 3 选 1 屏(投资策略/环境)或备战上;
- 弹窗内**顶部箱图标是展示图不可点**((812,175)/(810,194)/(960,837) 三点全无反应);
- 正确动作 = **点 × 关闭**弹窗(道具进背包,备战界面箱槽走 prep_actions 的
  OpenBox 开箱链路;选卡 = 武装箱选择画面 op ``cw_screen_box_pick``,
  R7 批 2a);
- 不关会挡死底层屏(M20 卡 19min/286 次 retry 实证)。

⚠️ M19 建档时曾按「点箱图标开箱→四选一」建模——错误(展示图不可点);M20 实锤后改关闭模型。
四选一选卡职责在独立画面 op(cw_screen_box_pick,CwScreenBoxPick;R7 批 2a 起替代
原 PickBoxCard 备战动作形态),本 op 只关弹窗。

统一观察架构逐屏迁移(账本 T-48 收尾五屏;架构设计 §9.1 并存纪律):本类是
CwScreenOpBase 子类,handle 顶部装配点分流(重入裁决**之后**,先例锚 =
cw_screen_encounter.py :241-251 重入裁决 / :252-258 装配点分流;总纲契约 6):
cw_game_ports 两端口完整在场 → 五段生命周期新路径;缺省 None = 生产直连
旧路径(原序列,生产行为零变化)。五段形态:observe = 标识门(miss 未发 →
fail 交编排壳)+ 帧引用(实机适配器① = 轻观察封口,T-8 简报同式;重入
裁决不在本段,总纲契约 6:留守 handle 分流前共享段);reconcile = 空申报;
decide+act 内聚 ``_close_dialog``(读「按钮-关闭」center → mouse_move+click
+1s → 置位,两路径共享零转录);on_outcome = 无登记件(注册表缺席 = 零
动作,__init__ 申报)。本屏裁决位序 = pending 先行、miss fail 后置(与未达
上限弹窗的 miss 分支内序不同,逐字保真禁统一,收尾屏详设 §2)。本屏 sim 腿
= 不适用(F11 例外清单:sim 无对应画面段),等价判据主承重 = 实机在册行为
锁 + 新路径行为锁(test_cw_obs_arch_closing_screens.py)。
"""
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class ArmoryBoxObservation:
    """武装箱弹窗观察 payload(五段之段1产物;T-48 实机转录形态)。

    中断弹窗族轻观察(收尾屏详设 §2):标识门判定在段内(门失败 →
    round_fail 早退交编排壳按步分流);payload 仅携带稳定帧引用(实机
    识别域载体,不出端口——sim 适配器落位时该域 = None 帧语义,F11
    例外清单本批不建)。
    """

    screen: Any = None


class ArmoryBoxLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,T-48)。

    轻观察封口(先例 = T-8 简报轻观察适配器):标识门须在段内产出早退
    轮次,归 ``lifecycle_observe``;适配器仅装配稳定帧引用。sim 实现 =
    不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenArmoryBox') -> ArmoryBoxObservation:
        return ArmoryBoxObservation(screen=op.last_screenshot)


class CwScreenArmoryBox(CwScreenOpBase):
    """道具获得说明弹窗:点 × 关闭 + 重入观察裁决交回(验证废除)。"""

    DIALOG_SCREEN: ClassVar[str] = '货币战争-武装箱弹窗'

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-武装箱弹窗')
        # 适配器位缺省装配(先例 = T-8 五相位屏):观察口 = 实机适配器
        #(轻观察封口);动作口 = None = 直连现役动作体(基类「None = 子类
        # 缺省实现自担」)。on_outcome 注册表:本屏无登记件(注册表缺席 =
        # 零动作)。
        self._observation_adapter = ArmoryBoxLiveObservationAdapter()
        # 点 × 已发待重入裁决标志(验证废除形态):标识不在 + 已发 = 弹窗已关
        #(道具进背包)→ success 交回;标识在 = 重点(计节点预算)。
        self._click_pending: bool = False

    @operation_node(name='武装箱弹窗', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        _hit = self.round_by_find_area(
            screen, CwScreenArmoryBox.DIALOG_SCREEN, '标识-简易武装箱', crop_first=False).is_success
        # 重入裁决(观察驱动):上轮点 × 已发 → 标识不在 = 弹窗已关(底层屏
        # 交还 loop)→ success;标识在 = 点击未落地 → 重点。两路径共用
        #(分流前挂,先于五段 lifecycle 的 observe 门;总纲契约 6)。
        if self._click_pending:
            self._click_pending = False
            if not _hit:
                log.info('[cw-armbox] 弹窗已关(重入观察裁决,底层屏交还 loop)')
                return self.round_success(wait=1.0)
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run/
        # CwScreenEncounter.handle):两端口完整在场(= 测试 harness 显式装配)
        # → 五段生命周期新路径;缺省 None = 生产直连旧路径(下方原序列,
        # 生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        # 旧路径原序列(§9.1 并存期逐位保留):
        if not _hit:
            return self.round_fail('非武装箱弹窗')
        return self._close_dialog()

    def _close_dialog(self) -> OperationRoundResult:
        """点 × 关闭体(五段 decide+act 两路径共享零转录;旧 handle :51-61
        逐位平移):读「按钮-关闭」center(缺失 → fail 缺坐标;道具进背包,
        开箱走备战箱槽 OpenBox 链路)→ mouse_move+click+1s → 置位(落地
        判定归下一轮重入裁决)。"""
        _pt = area_center(self.ctx, '按钮-关闭', CwScreenArmoryBox.DIALOG_SCREEN)
        if _pt is None:
            return self.round_fail('武装箱弹窗缺「按钮-关闭」坐标')
        log.info(f'[cw-armbox] 关闭说明弹窗({_pt.x},{_pt.y})(道具入背包;开箱走备战箱槽)')
        self.ctx.controller.mouse_move(_pt)   # bug#1 缓解
        self.ctx.controller.click(_pt)
        time.sleep(1.0)
        # 机械交回(验证废除):弹窗消失与否由下一轮重入观察裁决(handle 顶部)。
        self._click_pending = True
        return self.round_retry('点 × 已发,重入观察裁决', wait=1)

    # ---- 五段生命周期(统一观察架构 §5.1;T-48,先例 = T-8 简报)----

    def lifecycle_observe(self
                          ) -> tuple[ArmoryBoxObservation,
                                     OperationRoundResult | None]:
        """段1 observe:标识门(id_mark「标识-简易武装箱」miss 未发 →
        round_fail 早退交编排壳按步分流,旧 handle 首闸逐位转录)→ 轻观察
        payload。重入裁决不在本段(总纲契约 6:留守 handle 分流前共享段)。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else ArmoryBoxObservation(screen=self.last_screenshot))
        _hit = self.round_by_find_area(
            self.last_screenshot, CwScreenArmoryBox.DIALOG_SCREEN,
            '标识-简易武装箱', crop_first=False).is_success
        if not _hit:
            return obs, self.round_fail('非武装箱弹窗')
        return obs, None

    def lifecycle_decision_cycle(self, payload: ArmoryBoxObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作决策循环):decide+act 内聚 ``_close_dialog``
        (点 × 关闭体,两路径共享零转录);on_outcome = 本屏无登记件
        (注册表缺席 = 零动作,__init__ 申报)。轮次终结出口 = 机械交回
        round_retry(落地判定归下一轮重入裁决,验证废除形态)。"""
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        rs = self._close_dialog()
        self._lifecycle_mark('on_outcome')
        return rs
