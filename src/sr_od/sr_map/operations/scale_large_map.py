from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ScaleLargeMap(SrOperation):

    def __init__(self, ctx: SrContext, to_scale: int, is_main_region: bool = True):
        """
        默认在大地图页面 点击缩放按钮
        :param to_scale: 目标缩放比例
        :param is_main_region: 是否主区域
        """
        super().__init__(ctx, 5, op_name=gt('缩放地图至 %d') % to_scale)
        self.is_main_region: bool = is_main_region
        self.to_scale: int = to_scale
        self.scale_per_time: int = -1 if to_scale < self.ctx.pos_info.pos_lm_scale else 1  # 负数为缩小，正数为放大

    @operation_node(name='缩放大地图', is_start_node=True)
    def scale(self) -> OperationRoundResult:
        if self.to_scale == self.ctx.pos_info.pos_lm_scale:
            return self.round_success()

        # 没有使用模板匹配找加减号的位置 实际测试无法区分减价
        if self.is_main_region:
            if self.scale_per_time < 0:
                area = self.ctx.screen_loader.get_area('大地图', '主区域缩放-减号')
            else:
                area = self.ctx.screen_loader.get_area('大地图', '主区域缩放-加号')
        else:
            if self.scale_per_time < 0:
                area = self.ctx.screen_loader.get_area('大地图', '子区域缩放-减号')
            else:
                area = self.ctx.screen_loader.get_area('大地图', '子区域缩放-加号')
        log.info('准备缩放地图 点击 %s %s', area.center,
                 self.ctx.controller.click(area.center))
        self.ctx.pos_info.pos_lm_scale += self.scale_per_time
        if self.to_scale == self.ctx.pos_info.pos_lm_scale:
            return self.round_success()
        else:
            return self.round_wait(wait=0.5)
