import time

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.sim_universe import sim_uni_screen_state
from sr_od.application.sim_universe.operations.bless.sim_uni_choose_bless import (
    SimUniChooseBless,
)
from sr_od.application.sim_universe.operations.bless.sim_uni_drop_bless import (
    SimUniDropBless,
)
from sr_od.application.sim_universe.operations.curio.sim_uni_choose_curio import (
    SimUniChooseCurio,
    SimUniDropCurio,
)
from sr_od.application.sim_universe.operations.sim_uni_event import SimUniEvent
from sr_od.application.sim_universe.operations.sim_uni_exit import SimUniExit
from sr_od.context.sr_context import SrContext
from sr_od.operations.interact.talk_interact import TalkInteract
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state

# NPC 对话态脱困用的「告别」类选项词表(LCS 高阈值匹配,防同屏其他选项误配)。
# 词表是设计先行的保守集:2026-08-26 事故现场选项为「告别」(用户口述);
# 后续按 od-dev-screen-onboarding 用守卫采集的截图样本核对/扩充,再考虑建 screen_info 档。
NPC_DIALOG_FAREWELL_WORDS: list[str] = ['告别', '离开', '再见']
NPC_DIALOG_FAREWELL_LCS: float = 0.7


class BackToNormalWorldPlus(SrOperation):

    def __init__(self, ctx: SrContext):
        """
        返回普通大世界 增强版
        需要在任何情况下使用都能顺利地返回手机菜单 用于应用结束后 确保不会卡死下一个应用
        已考虑场景如下
        :param ctx:
        """
        SrOperation.__init__(self, ctx, op_name=gt('返回普通大世界'))

    @operation_node(name='画面识别', node_max_retry_times=20, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.last_screenshot

        # 先看看左上角是否退出按钮
        result = self.round_by_find_area(screen, '模拟宇宙', '大世界返回按钮')
        if result.is_success:
            # 判断是否在模拟宇宙内
            sim_uni_level_type = sim_uni_screen_state.get_level_type(self.ctx, screen)
            if sim_uni_level_type is not None:
                return self.sim_uni_exit(False)

            # 如果有返回按钮 又不是在模拟宇宙 则就是在逐光捡金内
            result = self.round_by_find_and_click_area(screen, '模拟宇宙', '大世界返回按钮')
            if result.is_success:
                return self.round_wait(wait=1)

            # 都不在的话 暂时不支持返回大世界
            return self.round_fail('未支持的副本画面')

        # 在可以移动的画面 - 普通大世界
        result = self.round_by_find_area(screen, '大世界', '角色图标')
        if result.is_success:  # 右上角有角色图标
            # 检测弹窗 "点击空白处关闭" 弹窗不会遮挡角色图标 需要先关闭
            result = self.round_by_find_and_click_area(screen, '大世界', '点击空白处关闭')
            if result.is_success:
                return self.round_wait(wait=1)
            return self.round_success()

        # 手机菜单
        result = self.round_by_find_area(screen, '菜单', '开拓等级')
        if result.is_success:
            self.round_by_click_area('菜单', '右上角返回')
            return self.round_wait(wait=1)

        # 模拟宇宙内的画面
        sim_uni_state = sim_uni_screen_state.get_sim_uni_screen_state(
            self.ctx, screen,
            event=True,
            bless=True,
            drop_bless=True,
            curio=True,
            drop_curio=True
        )
        if sim_uni_state is not None:
            # region 差分宇宙4.0
            if sim_uni_state == sim_uni_screen_state.ScreenState.SELECT_STATION.value:  # 选择站点卡
                self.ctx.controller.click(Point(160, 343))  # 第一个
                time.sleep(0.2)
                self.ctx.controller.click(Point(1626, 939))  # 确认
                return self.round_wait(sim_uni_state, wait=2)
            if sim_uni_state == sim_uni_screen_state.ScreenState.SELECT_NEXT_STATION.value:  # 选择下一站
                self.ctx.controller.click(Point(867, 589))  # 中间偏左
                time.sleep(0.1)
                self.ctx.controller.click(Point(701, 589))  # 第一个
                time.sleep(0.1)
                self.ctx.controller.click(Point(1152, 969))  # 确认
                return self.round_wait(sim_uni_state, wait=3)
            if sim_uni_state == sim_uni_screen_state.ScreenState.CHOOSE_WILL_POWER.value:  # 选择奇迹
                self.ctx.controller.click(Point(867, 589))  # 中间偏左
                time.sleep(0.1)
                self.ctx.controller.click(Point(475, 483))  # 第一个
                time.sleep(0.1)
                self.ctx.controller.click(Point(953, 969))  # 确认
                return self.round_wait(sim_uni_state, wait=1)
            if sim_uni_state == sim_uni_screen_state.ScreenState.AHA_MASK.value:  # 选择面具
                self.ctx.controller.click(Point(314, 914))  # 第一个
                time.sleep(1)
                self.ctx.controller.click(Point(1576, 982))  # 确认
                return self.round_wait(sim_uni_state, wait=1)
            # endregion

            if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_BLESS.value:
                return self.sim_uni_choose_bless()

            if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_DROP_BLESS.value:
                return self.sim_uni_drop_bless()

            if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_CURIOS.value:
                return self.sim_uni_choose_curio()

            if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_DROP_CURIOS.value:
                return self.sim_uni_drop_curio()

            if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_EVENT.value:
                return self.sim_uni_event()

        # 对话框 - 逐光捡金 退出确认
        result = self.round_by_find_and_click_area(screen, '逐光捡金', '退出对话框确认')
        if result.is_success:
            return self.round_wait(wait=5)

        # 列车补给 - 点击空白处继续
        if common_screen_state.is_express_supply(self.ctx, screen):
            common_screen_state.claim_express_supply(self.ctx)
            return self.round_wait(wait=2)

        # 战斗中 点击右上角后出现的画面 需要需要退出
        battle_exit_area_list = [
            ('模拟宇宙', '终止战斗并结算'),  # 模拟宇宙
        ]
        for area in battle_exit_area_list:
            result = self.round_by_find_and_click_area(screen, area[0], area[1])
            if result.is_success:
                return self.round_wait(result.status, wait=1)

        # 战斗结束后 出现的退出关卡
        result = self.round_by_find_and_click_area(screen, '战斗画面', '退出关卡按钮')
        if result.is_success:
            return self.round_wait(result.status, wait=2)

        # 对话态守卫(2026-08-26 实机事故根修,NPC 对话态下兜底点击会命中对话隐藏按钮):
        # 登录落点等活动摊位 NPC 对话态时,右上角图标全被对话 UI 遮蔽,前面所有分支
        # 都不命中,原兜底直接点「菜单-右上角返回」——该坐标与对话的隐藏按钮重叠,
        # 一点就把对话 UI 收掉 → 裸场景假象 + 键盘输入被吞 → 后续判断全乱。
        # 守卫在兜底之前先检测对话态并走脱困序,检测不命中才落回原兜底。
        dialog_result = self.check_npc_dialog(screen)
        if dialog_result is not None:
            return dialog_result

        # 其他情况 - 均点击右上角触发返回上一级
        result = self.round_by_click_area('菜单', '右上角返回')
        # 兜底分支必须用 round_retry（计入 node_max_retry_times）而非 round_wait：
        # 框架中 WAIT 不消耗 retry（operation.py 循环里 WAIT 直接 continue、且任何非 RETRY
        # 结果会把 node_retry_times 清零），兜底点击无法改变画面时会无限循环
        # （2026-08-24 实跑：战斗结算画面点右上角无效，兜底卡约 2 小时拖垮整条龙）。
        # 正常「连续退多级菜单」不受影响：每退一级后画面变化、check_screen 命中其他
        # 分支返回 WAIT/SUCCESS，node_retry_times 被清零，不会累计到 20 次上限。
        return self.round_retry(result.status, wait=1)

    def check_npc_dialog(self, screen: MatLike) -> OperationRoundResult | None:
        """
        对话态守卫：检测当前是否处于 NPC 对话态，是则走脱困序（推进/告别），否则返回 None 落回兜底。

        检测与动作坐标全部复用 TalkInteract 的既有已验证常量（交谈交互区 + 空白推进点击点），
        不引入未验证的新坐标。脱困序为逐帧反应式（本方法每轮重跑，无跨轮状态）：

        1. 告别类选项可见 → 点它退出对话（对完后续帧由「角色图标」分支接管）；
        2. 有其他选项但无告别词 → 不乱点未知选项（可能接受任务/开商店），点空白推进，
           用 round_retry 计入节点预算，有界退出而非破坏性误点；
        3. 交互区无任何文字 → 无法确认对话态，返回 None 落回原兜底。

        :param screen: 游戏画面
        :return: 命中对话态时返回对应的 round 结果；否则 None
        """
        part = cv2_utils.crop_image_only(screen, TalkInteract.INTERACT_RECT)

        farewell_map = self.ctx.ocr.match_words(
            part, words=NPC_DIALOG_FAREWELL_WORDS, lcs_percent=NPC_DIALOG_FAREWELL_LCS,
        )
        if len(farewell_map) > 0:
            # 采集钩子(临时,对话态建档后整段删除):守卫首次实证命中时留截图样本,
            # 供 od-dev-screen-onboarding 离线核对选项词表/坐标。
            self.save_screenshot(prefix='npc_dialog_guard')
            log.info('[对话态守卫] 命中告别类选项 %s,点击退出对话', list(farewell_map.keys()))
            for r in farewell_map.values():
                to_click: Point = r.max.center + TalkInteract.INTERACT_RECT.left_top
                # 与 TalkInteract 同款:先移上去停留再点,提高选项选中稳定性
                self.ctx.controller.mouse_move(to_click)
                time.sleep(0.1)
                if self.ctx.controller.click(press_time=0.1, pc_alt=True):
                    return self.round_wait('对话态-告别', wait=1)

        ocr_map = self.ctx.ocr.run_ocr(part)
        if len(ocr_map) > 0:
            # 有选项但没匹配到告别词:不点未知选项(语义不明,可能触发任务/购物),
            # 点空白推进对话(选项出现前的对话文本阶段可推进),交给下一帧重新判定。
            log.info('[对话态守卫] 检测到未知对话选项 %s,不乱点,点空白推进', list(ocr_map.keys()))
            to_click = Point(self.ctx.project_config.screen_standard_width // 2,
                             self.ctx.project_config.screen_standard_height - 100)
            self.ctx.controller.click(to_click)
            return self.round_retry('对话态-未知选项', wait=1)

        return None

    def sim_uni_exit(self, is_in_x: bool) -> OperationRoundResult:
        op = SimUniExit(self.ctx, is_in_x, temporarily_leave=True)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_event(self) -> OperationRoundResult:
        op = SimUniEvent(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_choose_bless(self) -> OperationRoundResult:
        op = SimUniChooseBless(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_drop_bless(self) -> OperationRoundResult:
        op = SimUniDropBless(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_choose_curio(self) -> OperationRoundResult:
        op = SimUniChooseCurio(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_drop_curio(self) -> OperationRoundResult:
        op = SimUniDropCurio(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)


def __debug():
    ctx = SrContext()
    ctx.init_ocr()
    ctx.init_by_config()

    ctx.start_running()
    op = BackToNormalWorldPlus(ctx)
    op.execute()
    ctx.stop_running()


if __name__ == '__main__':
    __debug()
