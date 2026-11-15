"""每月合成 app:自动把「每月限量合成」的物品合成拉满(当前仅自塑尘脂)。

编排(design: docs/develop/sr_od/application/monthly_synthesize/
changes/v1-initial/application-flow.md,四段式):
    ① 导航段+玩法段 合成自塑尘脂(start):开关关 → 跳过(月度职责视为
       已履行);开 → Synthesize(SELF_MODELING_RESIN)(op 内部自带
       回大世界 → 菜单 → 合成导航,数量拉满/额度用完/材料不足见 op 契约)
    ② 领奖段 无(合成确认与结果关闭在 op 内闭环)
    ③ 返回段 返回大世界(BackToNormalWorldPlus,一条龙在大世界交接)
    ④ 失败收尾 尽力回大世界后带原始语境 FAIL

运行语义:周期 MONTHLY(月限额度自然月刷新)——每月首跑合成拉满标完成,
月内不再跑;额度用完/开关关 = 预期内完成照常标;材料不足 = 失败不标
(用户裁定 2026-11-15),一条龙日批重跑补做。
首屏未见裁定(op 沉底排序律,ITEM_ABSENT_FIRST_SCREEN):当月锚
(resin_quota_confirmed)已置 = 额度用尽,标本月完成;未置 = 材料不足或
额度被人手用尽,判失败重试(已知边界:额度被人手提前用尽且当月 app 从未
成功过时,会日批失败噪音到月底,下月自愈)。
"""

from one_dragon.base.operation.application_run_record import AppRunRecord
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_notify import NotifyTiming, node_notify
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.application.monthly_synthesize import monthly_synthesize_const
from sr_od.application.monthly_synthesize.monthly_synthesize_config import (
    MonthlySynthesizeConfig,
)
from sr_od.application.monthly_synthesize.monthly_synthesize_record import (
    MonthlySynthesizeRunRecord,
)
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.synthesize.synthesize import (
    STATUS_ITEM_ABSENT,
    STATUS_QTY_MAXED,
    STATUS_QUOTA_EXHAUSTED,
    Synthesize,
)
from sr_od.operations.synthesize.synthesize_const import SynthesizeItemEnum


class MonthlySynthesizeApp(SrApplication):

    def __init__(self, ctx: SrContext,
                 config: MonthlySynthesizeConfig,
                 run_record: AppRunRecord):
        """
        :param ctx: 上下文
        :param config: app 配置(factory 注入,与 GUI/MCP 同一缓存实例)
        :param run_record: 运行记录(factory 注入,周期 MONTHLY)
        """
        self._config: MonthlySynthesizeConfig = config
        self._record: MonthlySynthesizeRunRecord = run_record
        self._abort_msg: str = ''
        """非预期失败的原始语境(失败收尾尽力回大世界后随 FAIL 带出)"""
        SrApplication.__init__(self, ctx,
                               monthly_synthesize_const.APP_ID,
                               op_name=gt('每月合成', 'game'),
                               run_record=run_record)

    @operation_node(name='合成自塑尘脂', is_start_node=True)
    def synthesize_resin(self) -> OperationRoundResult:
        """导航段+玩法段:开关分流后合成自塑尘脂到月限拉满。

        op 成功(合成完成/额度用完/首屏未见且当月已锚)与开关跳过都进返回
        段——月度职责已履行,框架按 app 成功标本月完成;op 失败(材料不足/
        识别失败)与首屏未见且当月未锚(材料不足或额度被人手用尽)转失败
        收尾,不标完成,一条龙后续补跑。
        """
        if not self._config.self_modeling_resin_enabled:
            return self.round_success('开关未启用', wait=0.5)

        result = Synthesize(
            self.ctx, SynthesizeItemEnum.SELF_MODELING_RESIN.value, 0).execute()
        if not result.success:
            self._abort_msg = f'合成自塑尘脂失败: {result.status}'
            return self.round_success(status='SYNTH_FAIL', wait=0.5)
        if result.status == STATUS_ITEM_ABSENT:
            # 沉底排序律下的首屏未见:成因裁定按当月锚(见模块 docstring)
            if self._record.resin_quota_confirmed:
                return self.round_success('额度已用完(首屏未见)', wait=0.5)
            self._abort_msg = ('材料合成列表首屏未见自塑尘脂'
                               '(材料不足,或额度已被人手用尽)')
            return self.round_success(status='SYNTH_FAIL', wait=0.5)
        if result.status in (STATUS_QTY_MAXED, STATUS_QUOTA_EXHAUSTED):
            # 额度确实耗尽的直接证据(合成拉满/读到额度 0),置当月锚
            self._record.mark_resin_quota_confirmed()
        # 成功状态透传(合成完成/QUOTA_EXHAUSTED),供通知区分语义
        return self.round_by_op_result(result, wait=0.5)

    @node_from(from_name='合成自塑尘脂')
    @node_notify(when=NotifyTiming.CURRENT_DONE, detail=True)
    @operation_node(name='返回大世界')
    def back_to_world(self) -> OperationRoundResult:
        """返回段:BackToNormalWorldPlus,保证一条龙在大世界交接。"""
        result = BackToNormalWorldPlus(self.ctx).execute()
        if not result.success:
            return self.round_fail(f'返回大世界失败: {result.status}')
        return self.round_by_op_result(result)

    @node_from(from_name='合成自塑尘脂', status='SYNTH_FAIL')
    @operation_node(name='失败收尾')
    def fail_return(self) -> OperationRoundResult:
        """失败收尾:尽力返回大世界(下一 app 的干净起点)后带原始语境 FAIL。

        返回失败不掩盖原始失败信息;框架对失败 app 无画面收尾,此节点补位。
        """
        result = BackToNormalWorldPlus(self.ctx).execute()
        msg = self._abort_msg
        if not result.success:
            msg = f'{msg};返回大世界也未成功({result.status})'
        return self.round_fail(msg)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    app = MonthlySynthesizeApp(
        ctx,
        config=ctx.run_context.get_config(
            app_id=monthly_synthesize_const.APP_ID,
            group_id='one_dragon'),
        run_record=ctx.run_context.get_run_record(
            app_id=monthly_synthesize_const.APP_ID),
    )
    app.execute()


if __name__ == '__main__':
    __debug()
