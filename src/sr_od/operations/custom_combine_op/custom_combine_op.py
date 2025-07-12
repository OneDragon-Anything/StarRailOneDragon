from typing import Optional, List, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.click_point import ClickPoint
from sr_od.operations.custom_combine_op.custom_combine_op_config import CustomCombineOpConfig, CustomCombineOpItem
from sr_od.operations.custom_combine_op.custom_combine_op_const import OpEnum, OpWaitTypeEnum, OpInteractTypeEnum
from sr_od.operations.interact.move_interact import MoveInteract
from sr_od.operations.interact.talk_interact import TalkInteract
from sr_od.operations.move.move_directly import MoveDirectly
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.store.buy_store_item import BuyStoreItem
from sr_od.operations.store.store_const import StoreItemEnum
from sr_od.operations.synthesize.synthesize import Synthesize
from sr_od.operations.synthesize.synthesize_const import SynthesizeItemEnum
from sr_od.operations.wait.wait_in_seconds import WaitInSeconds
from sr_od.operations.wait.wait_in_world import WaitInWorld
from sr_od.sr_map.operations.transport_by_map import TransportByMap


class CustomCombineOp(SrOperation):

    STATUS_ALL_DONE: ClassVar[str] = '全部完成'

    def __init__(self, ctx: SrContext, config_name: str, no_battle: bool = False):
        """
        按配置文件执行对应的指令
        最后会返回大世界
        :param ctx:
        :param config_name:
        """
        self.config: CustomCombineOpConfig = CustomCombineOpConfig(config_name)
        self.op_idx: int = 0  # 当前指定的指令下标
        self.no_battle: bool = no_battle

        SrOperation.__init__(self, ctx, op_name=gt(self.config.config_name))

    @node_from(from_name='执行指令')
    @operation_node(name='执行指令', is_start_node=True)
    def run_op(self) -> OperationRoundResult:
        if not self.config.existed:
            return self.round_fail('配置文件不存在')

        op_item: CustomCombineOpItem = self.config.ops[self.op_idx]
        next_op_item: CustomCombineOpItem = None if self.op_idx >= len(self.config.ops) - 1 else self.config.ops[self.op_idx + 1]

        op: Optional[SrOperation] = None
        if op_item.op == OpEnum.BACK_TO_WORLD_PLUS.value:
            op = BackToNormalWorldPlus(self.ctx)
        elif op_item.op == OpEnum.TRANSPORT.value:
            op = self.op_transport(op_item)
        elif op_item.op == OpEnum.WAIT.value:
            op = self.op_wait(op_item)
        elif op_item.op in [OpEnum.MOVE.value, OpEnum.SLOW_MOVE.value]:
            op = self.op_move(op_item, next_op_item)
        elif op_item.op == OpEnum.INTERACT.value:
            op = self.op_interact(op_item)
        elif op_item.op == OpEnum.CLICK.value:
            op = ClickPoint(self.ctx, Point(int(op_item.data[0]), int(op_item.data[1])))
        elif op_item.op == OpEnum.BUY_STORE_ITEM.value:
            op = self.op_buy_store_item(op_item)
        elif op_item.op == OpEnum.SYNTHESIZE.value:
            op = self.op_synthesize(op_item)

        if op is None:
            return self.round_fail(f'不支持的指令 {op_item.op}')

        op_result = op.execute()
        if op_result.success or op_item:
            self.op_idx += 1
            if self.op_idx >= len(self.config.ops):
                return self.round_success(CustomCombineOp.STATUS_ALL_DONE)
            else:
                return self.round_success()
        else:
            return self.round_by_op_result(op_result)

    def op_transport(self, op_item: CustomCombineOpItem) -> SrOperation:
        """
        传送指令
        :param op_item:
        :return:
        """
        planet_name = op_item.data[0]
        region_name = op_item.data[1]
        region_floor = int(op_item.data[2])
        tp_name = op_item.data[3]

        tp = self.ctx.map_data.best_match_sp_by_all_name(gt(planet_name, 'game'), gt(region_name, 'game'), gt(tp_name, 'game'), region_floor)

        return TransportByMap(self.ctx, tp)

    def op_wait(self, op_item: CustomCombineOpItem) -> SrOperation:
        """
        等待指令
        :param op_item:
        :return:
        """
        wait_type = op_item.data[0]
        wait_seconds = float(op_item.data[1])
        if wait_type == OpWaitTypeEnum.IN_WORLD.value:
            return WaitInWorld(self.ctx, wait_seconds)
        elif wait_type == OpWaitTypeEnum.SECONDS.value:
            return WaitInSeconds(self.ctx, wait_seconds)

        log.error('错误的等待类型 %s' % wait_type)

    def op_move(self, op_item: CustomCombineOpItem, next_op_item: CustomCombineOpItem):
        """
        移动指令
        :param op_item:
        :param next_op_item:
        :return:
        """
        data: List[int] = [int(i) for i in op_item.data]
        current_pos = self.ctx.pos_info.pos_point
        current_lm_info = self.ctx.map_data.get_large_map_info(self.ctx.pos_info.pos_region)

        if len(data) > 2:
            next_region = self.ctx.map_data.region_with_another_floor(self.ctx.pos_info.pos_region, data[2])
            next_lm_info = self.ctx.map_data.get_large_map_info(next_region)
        else:
            next_region = None
            next_lm_info = None

        next_pos = Point(data[0], data[1])

        # 看后续指令判断这次移动结束后要不要停止
        dont_stop_afterwards = (
                next_op_item is not None and
                next_op_item.op in [
                    OpEnum.MOVE.value,
                    OpEnum.SLOW_MOVE.value,
                    OpEnum.PATROL.value,  # 如果下一个是攻击 则靠攻击停止移动 这样还可以取消疾跑后摇
                ]
        )

        no_run = op_item.op == OpEnum.SLOW_MOVE.value

        return MoveDirectly(self.ctx, current_lm_info, next_lm_info=next_lm_info,
                            target=next_pos, start=current_pos,
                            stop_afterwards=not dont_stop_afterwards, no_run=no_run,
                            no_battle=self.no_battle,
                            technique_fight=self.ctx.world_patrol_config.technique_fight,
                            technique_only=self.ctx.world_patrol_config.technique_only
                            )

    def op_interact(self, op_item: CustomCombineOpItem) -> SrOperation:
        """
        交互指令
        :param op_item:
        :return:
        """
        interact_type = op_item.data[0]
        interact_word = op_item.data[1]
        interact_lcs_percent = float(op_item.data[2]) if len(op_item.data) > 2 else 0.5
        interact_single_line = interact_type in [OpInteractTypeEnum.WORLD_SINGLE_LINE.value]

        if interact_type in [OpInteractTypeEnum.WORLD.value, OpInteractTypeEnum.WORLD_SINGLE_LINE.value]:
            return MoveInteract(self.ctx, cn=interact_word,
                                lcs_percent=interact_lcs_percent,
                                single_line=interact_single_line)
        elif interact_type == OpInteractTypeEnum.TALK.value:
            return TalkInteract(self.ctx, option=interact_word, lcs_percent=interact_lcs_percent)

        log.error('错误的交互类型 %s' % interact_type)

    def op_buy_store_item(self, op_item: CustomCombineOpItem) -> SrOperation:
        """
        购买商品指令
        :param op_item:
        :return:
        """
        item_id = op_item.data[0]
        buy_num = int(op_item.data[1])
        store_item = StoreItemEnum[item_id.upper()].value

        return BuyStoreItem(self.ctx, store_item, buy_num)

    def op_synthesize(self, op_item: CustomCombineOpItem) -> SrOperation:
        """
        合成指令
        :param op_item:
        :return:
        """
        category = op_item.data[0]
        item_id = op_item.data[1]
        num = int(op_item.data[2])

        item = SynthesizeItemEnum[item_id.upper()].value
        return Synthesize(self.ctx, item, num)

    @node_from(from_name='执行指令', status=STATUS_ALL_DONE)
    @operation_node(name='结束后返回')
    def back_at_last(self) -> OperationRoundResult:
        """
        完成指令结束
        :return:
        """
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())


def __debug_op():
    ctx = SrContext()
    ctx.start_running()

    op = CustomCombineOp(ctx, 'buy_trick_snack', no_battle=True)
    op.execute()


if __name__ == '__main__':
    __debug_op()