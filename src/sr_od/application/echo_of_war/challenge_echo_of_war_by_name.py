from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.echo_of_war.challenge_echo_of_war_core import (
    STATUS_GIVE_UP_ON_LOSING_STREAK,
    STATUS_PLAN_FINISHED,
    STATUS_POWER_INSUFFICIENT,
    STATUS_TIMEOUT_VICTORY_EXITED,
    STATUS_TIMES_EXHAUSTED,
    STATUS_WITH_DEAD_RECOVERED,
    ChallengeEchoOfWarCore,
)
from sr_od.application.echo_of_war.echo_of_war_config import get_war_mission_list
from sr_od.application.trailblaze_power.trailblaze_power_config import (
    TrailblazePowerPlanItem,
)
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideMission
from sr_od.interastral_peace_guide.guide_transport import GuideTransport
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.sr_operation import SrOperation


class ChallengeEchoOfWarByName(SrOperation):
    """按关卡名或关卡 ID 挑战历战余响(周本)指定成功次数:回大世界 → 指南传送 →
    挑战循环 → 收尾回大世界。
    起点:任意可控画面(自行导航);终点:大世界(成功分支恒定落点);失败分支原样
    透传、画面停原地交调用方处置。
    配队不从参数传,固定取周本计划该关卡项(team_num=0 时沿用当前编队,日志显性
    提示——当前编队可能是上个玩法残留,周本败场照扣开拓力);支援 'none' 翻译为
    不用支援。运行日志打印计划配队与消耗预估/实际消耗供调用方向用户汇报。
    副作用:消耗周本挑战次数与开拓力(30/次),真实不可逆;调用方发起前须向用户
    说明并获同意。

    :param ctx: 上下文
    :param mission: 周本关卡中文名(如「坏灭的喜剧」,与关卡名互相包含即命中)或
        关卡 ID(周本计划 mission_id,精确匹配);多命中/零命中抛 ValueError 带候选
    :param plan_times: 计划成功次数,>=1
    """

    STATUS_BACK_TO_WORLD: str = '已返回大世界'

    def __init__(self, ctx: SrContext, mission: str, plan_times: int = 1):
        if not isinstance(mission, str) or len(mission.strip()) == 0:
            raise ValueError(f'关卡名或 ID 不能为空,得到 {mission!r}')
        if plan_times < 1:
            raise ValueError(f'计划成功次数须 >=1,得到 {plan_times}')

        mission_obj = self._resolve_mission(ctx, mission.strip())
        plan = self._find_plan_item(ctx, mission_obj)

        self.mission_obj: GuideMission = mission_obj
        self.plan_times: int = plan_times
        self.team_num: int = plan.team_num
        # 'none' 翻译是编排层职责(ChooseSupportInTeam 只认 None,编排层翻译先例
        # trailblaze_power_app.py);核心另有兜底归一防线
        self.support: str | None = None if plan.support in (None, 'none') else plan.support

        if self.team_num == 0:
            log.warning('计划配队=0,将沿用当前编队(可能是上个玩法残留,周本败场照扣开拓力)')
        log.info('计划配队 %d 支援 %s;预估消耗 开拓力 %d×%d 次 + 周本次数 %d 次',
                 self.team_num, self.support or '无',
                 mission_obj.power, plan_times, plan_times)

        SrOperation.__init__(
            self, ctx,
            op_name=f'{gt("历战余响", "game")} {mission_obj.display_name} '
                    f'{gt("次数")} {plan_times}'
        )

    @staticmethod
    def _resolve_mission(ctx: SrContext, mission: str) -> GuideMission:
        """
        解析关卡:ID 精确匹配优先,其次中文名互相包含匹配
        :param ctx: 上下文
        :param mission: 关卡名或关卡 ID(去空白后)
        :return: 唯一命中的关卡
        """
        war_list = get_war_mission_list(ctx.guide_data)
        exact = [m for m in war_list if m.unique_id == mission]
        if len(exact) == 1:
            return exact[0]
        candidates = [m for m in war_list
                      if mission in m.display_name or m.display_name in mission]
        if len(candidates) > 1:
            names = '、'.join(m.display_name for m in candidates)
            raise ValueError(f'关卡匹配到多命中,请用完整关卡名或 ID:{names}')
        if len(candidates) == 0:
            names = '、'.join(m.display_name for m in war_list)
            raise ValueError(f'未找到关卡 {mission!r},可选值:{names}')
        return candidates[0]

    @staticmethod
    def _find_plan_item(ctx: SrContext,
                        mission_obj: GuideMission) -> TrailblazePowerPlanItem:
        """
        按关卡查周本计划项(计划是配队单一源;plan_list 全量补齐保证必存在,
        缺失属配置异常态,显式报错不静默兜底)
        :param ctx: 上下文
        :param mission_obj: 已解析关卡
        :return: 周本计划项
        """
        for plan in ctx.echo_of_war_config.plan_list:
            if plan.mission_id == mission_obj.unique_id:
                return plan
        raise ValueError(f'周本计划缺少关卡项 {mission_obj.display_name}'
                         f'(mission_id={mission_obj.unique_id}),请检查周本计划配置')

    @operation_node(name='回大世界', is_start_node=True)
    def back_to_world_first(self) -> OperationRoundResult:
        """
        起点任意可控画面,先回大世界拿到干净导航起点(幂等,已在大世界快速成功)
        :return:
        """
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='回大世界')
    @operation_node(name='传送')
    def transport(self) -> OperationRoundResult:
        """
        指南传送到周本副本(成功即落挑战副本-历战余响挑战态)
        :return:
        """
        op = GuideTransport(self.ctx, self.mission_obj)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='传送')
    @operation_node(name='挑战循环')
    def run_core(self) -> OperationRoundResult:
        """
        委托周本挑战核心;核心 status 全名单显式分支(六类成功收口,其余 fail 原样透传)
        :return:
        """
        core = ChallengeEchoOfWarCore(self.ctx, team_num=self.team_num,
                                      plan_times=self.plan_times,
                                      support=self.support)
        core_result = core.execute()
        status = core_result.status
        if status in (STATUS_PLAN_FINISHED,
                      STATUS_TIMEOUT_VICTORY_EXITED,
                      STATUS_GIVE_UP_ON_LOSING_STREAK,
                      STATUS_TIMES_EXHAUSTED,
                      STATUS_POWER_INSUFFICIENT,
                      STATUS_WITH_DEAD_RECOVERED):
            if status == STATUS_TIMES_EXHAUSTED:
                # 带使命语义层的记账动作:清剩余次数(镜像 app 侧同款职责)
                self.ctx.echo_of_war_run_record.left_times = 0
            # 实际消耗记账由日志承载(设计口径):六类成功都可能带非零成功次数,
            # 连败放弃/次数耗尽分支同样可能已消耗部分开拓力
            log.info('实际消耗 开拓力 %d×%d 次 + 周本次数 %d 次',
                     self.mission_obj.power, core.battle_success_times,
                     core.battle_success_times)
            return self.round_success(status)
        # 不在历战余响挑战画面 / 战斗超时无结算 / 未列明的一切 → 原样透传
        return self.round_fail(status)

    @node_from(from_name='挑战循环')
    @operation_node(name='收尾回大世界')
    def back_to_world_last(self) -> OperationRoundResult:
        """
        统一收尾(核心成功分支落点挑战画面/大世界复活点,不分支处理,单一终态)
        :return:
        """
        op = BackToNormalWorldPlus(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_success(ChallengeEchoOfWarByName.STATUS_BACK_TO_WORLD)
        return self.round_by_op_result(op_result)
