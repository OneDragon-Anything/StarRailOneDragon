"""货币战争 敌人信息浮层处理 op(1+N 形态独立画面 op,退出链内联特判清偿,
跨迭代挂账「敌人信息浮层建画面 op」条)。

点右上「按钮-关闭」关闭浮层交回主循环。零恢复动作语义:关闭即结束本次
访问,不推进不采集——浮层是情报查看层(自动对局不主动打开,低频;退出链
异常交接与观察采集模式经主循环身份分发到达),词缀/波次读数域归遭遇域
词缀读数通道(遭遇节点 op 死输入申报),不归本 op;浮层残留 = 主循环下一
帧重判再入本 op,天然幂等。

形态(画面 op 两段式 = 1+N 无策略段:识别+上报 node → 点关闭特殊流程
node,继承 CwOperation,轻屏统一形态,先例 = ``CwScreenNoFrontHint``/
``CwScreenDeployNotFull``):观察 node = 标识门(id_mark「标识-敌方信息」,
miss = round_fail 交编排壳按步分流)+ 门内 obs{on_screen} → 调占位
``report_screen_enemy_info_obs``(统一形态;本屏现役零状态容器写点,接口
为占位,match/gs 缺席跳过)→ obs 挂实例属性进关闭 node。关闭 node =
落地复查顶部(关闭已发 → 识别标志不在 = 浮层已关 → success 返回主循环;
识别标志在场 = 关闭未落地 → 重做关闭)→ 点「按钮-关闭」→ round_wait 循环
推进(不烧节点重试预算;不收敛 = 动作 bug 响亮暴露,无防御上限)。
本屏 sim 分支不适用:模拟器不建模本浮层,浮层帧恒不派发到本 op。
"""
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_screen_report.enemy_info import (
    CwScreenEnemyInfoObs,
    report_screen_enemy_info_obs,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext


class CwScreenEnemyInfo(CwOperation):
    """敌人信息浮层:点关闭交回主循环(零恢复动作)。
    起点:货币战争-敌人信息浮层出现;终点:已点关闭(浮层是否落地由下一帧
    观察裁决,本 op 只认「本画面处理完结」)。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-敌人信息浮层'   # screen_info 画面(currency_war_enemy_info.yml)

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='货币战争-敌人信息浮层关闭')
        # 关闭已发待落地复查标志(单 op 生命周期):区分「首发识别标志 miss =
        # 误分发 fail 返回主循环」与「重入识别标志 miss = 浮层已关 success 返回
        # 主循环」(零验证形态:动作层不做效果验证,判效归下一帧观察)。
        self._close_pending: bool = False
        # 观察结果(观察 node 产物;门早退轮不装载)。
        self._obs: CwScreenEnemyInfoObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """标识门 + obs{on_screen} → 占位 report 接入调用。

        门 miss = round_fail 早退交编排壳按步分流(与前台无角色弹窗 op 同
        status 语义);门 hit → obs 装载 + 占位 report(match/gs 缺席跳过)。"""
        screen = self.last_screenshot
        # 门 = screen_info id_mark area 实测:主循环身份分发与 op 执行之间画面
        # 可能已切换,重验防在已切换画面上盲点关闭。
        if not self.round_by_find_area(
                screen, CwScreenEnemyInfo.SCREEN_NAME,
                '标识-敌方信息').is_success:
            return self.round_fail('非敌人信息浮层')
        obs = CwScreenEnemyInfoObs(on_screen=True, screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_enemy_info_obs(_gs, obs)
        self._obs = obs
        return self.round_success(wait=0)

    @node_from(from_name='观察')
    @operation_node(name='关闭浮层', node_max_retry_times=2)
    def close_overlay(self) -> OperationRoundResult:
        """落地复查(顶部)→ 点关闭 → round_wait。

        落地复查(观察驱动,零验证形态):上轮关闭已发 → 识别标志不在 = 浮层
        已关(落地与否归下一帧观察侧重分发;此处只认「本画面处理完结」)
        → success 返回主循环;识别标志在场 = 关闭未落地 → 重做关闭。循环
        推进 = round_wait(不烧节点重试预算;不收敛 = 动作 bug 响亮暴露)。"""
        if self._close_pending:
            self._close_pending = False
            if not self.round_by_find_area(
                    self.last_screenshot, CwScreenEnemyInfo.SCREEN_NAME,
                    '标识-敌方信息').is_success:
                return self.round_success('敌人信息浮层已关(重入观察裁决)',
                                          wait=1.5)
        return self._click_close()

    def _click_close(self) -> OperationRoundResult:
        """关闭体:点「按钮-关闭」→ 置位(落地判定归下一轮落地复查)→
        round_wait 循环推进。点击落空/失败 = 透传 round_retry(计节点预算,
        有界终止单;按钮永久不可点 = 动作 bug 响亮暴露)。"""
        click_res = self.round_by_find_and_click_area(
            self.last_screenshot, CwScreenEnemyInfo.SCREEN_NAME,
            '按钮-关闭', pre_delay=0.3, success_wait=1, retry_wait=1)
        if not click_res.is_success:
            return click_res
        self._close_pending = True
        return self.round_wait(wait=1)
