import time

from cv2.typing import MatLike
from typing import Optional, ClassVar, List

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_const import match_best_curio_by_ocr, SimUniCurio, SimUniCurioEnum
from sr_od.context.sr_context import SrContext
from sr_od.operations.click_dialog_confirm import ClickDialogConfirm
from sr_od.operations.sr_operation import SrOperation


class SimUniChooseCurio(SrOperation):
    # 奇物名字对应的框 - 3个的情况
    CURIO_RECT_3_LIST: ClassVar[List[Rect]] = [
        Rect(315, 280, 665, 320),
        Rect(780, 280, 1120, 320),
        Rect(1255, 280, 1590, 320),
    ]

    # 奇物名字对应的框 - 2个的情况
    CURIO_RECT_2_LIST: ClassVar[List[Rect]] = [
        Rect(513, 280, 876, 320),
        Rect(1024, 280, 1363, 320),
    ]

    # 奇物名字对应的框 - 1个的情况
    CURIO_RECT_1_LIST: ClassVar[List[Rect]] = [
        Rect(780, 280, 1120, 320),
    ]

    CURIO_NAME_RECT: ClassVar[Rect] = Rect(315, 280, 1590, 320)  # 奇物名字的框

    CONFIRM_BTN: ClassVar[Rect] = Rect(1500, 950, 1840, 1000)  # 确认选择

    def __init__(self, ctx: SrContext, config: Optional[SimUniChallengeConfig] = None,
                 skip_first_screen_check: bool = True):
        """
        模拟宇宙中 选择奇物
        这里只处理一次选择奇物 再次触发的内容由外层调用处理
        目前使用的有
        - 战斗后/破坏物后 sim_uni_battle
        - 事件 sim_uni_event
        :param ctx: 上下文
        :param config: 挑战配置
        :param skip_first_screen_check: 是否跳过第一次画面状态检查
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('选择奇物')))

        self.config: Optional[SimUniChallengeConfig] = config
        self.skip_first_screen_check: bool = skip_first_screen_check  # 是否跳过第一次的画面状态检查 用于提速
        self.first_screen_check: bool = True  # 是否第一次检查画面状态

    def handle_init(self) -> Optional[OperationRoundResult]:
        """
        执行前的初始化 由子类实现
        注意初始化要全面 方便一个指令重复使用
        可以返回初始化后判断的结果
        - 成功时跳过本指令
        - 失败时立刻返回失败
        - 不返回时正常运行本指令
        """
        self.first_screen_check = True
        self.curio_cnt_type: int = 3  # 奇物数量

        return None

    @node_from(from_name='确认后画面判断', status=sim_uni_screen_state.ScreenState.SIM_CURIOS.value)
    @operation_node(name='选择奇物', is_start_node=True)
    def _choose_curio(self) -> OperationRoundResult:
        screen = self.screenshot()

        if not self.first_screen_check or not self.skip_first_screen_check:
            self.first_screen_check = False
            if not sim_uni_screen_state.in_sim_uni_choose_curio(screen, self.ctx.ocr):
                return self.round_retry('未在模拟宇宙-选择奇物页面')

        curio_pos_list: List[MatchResult] = self._get_curio_pos(screen)
        if len(curio_pos_list) == 0:
            return self.round_retry('未识别到奇物', wait=1)

        target_curio_pos: Optional[MatchResult] = self._get_curio_to_choose(curio_pos_list)
        self.ctx.controller.click(target_curio_pos.center)
        time.sleep(0.25)
        self.ctx.controller.click(SimUniChooseCurio.CONFIRM_BTN.center)
        return self.round_success(wait=0.1)

    def _get_curio_pos(self, screen: MatLike) -> List[MatchResult]:
        """
        获取屏幕上的奇物的位置
        :param screen: 屏幕截图
        :return: MatchResult.data 中是对应的奇物 SimUniCurio
        """
        curio_list = self._get_curio_pos_by_rect(screen, SimUniChooseCurio.CURIO_RECT_3_LIST)
        if len(curio_list) > 0 and self.curio_cnt_type >= 3:
            return curio_list

        curio_list = self._get_curio_pos_by_rect(screen, SimUniChooseCurio.CURIO_RECT_2_LIST)
        if len(curio_list) > 0 and self.curio_cnt_type >= 2:
            return curio_list

        curio_list = self._get_curio_pos_by_rect(screen, SimUniChooseCurio.CURIO_RECT_1_LIST)
        if len(curio_list) > 0 and self.curio_cnt_type >= 1:
            return curio_list

        return []

    def _get_curio_pos_by_rect(self, screen: MatLike, rect_list: List[Rect]) -> List[MatchResult]:
        """
        获取屏幕上的奇物的位置
        :param screen: 屏幕截图
        :param rect_list: 指定区域
        :return: MatchResult.data 中是对应的奇物 SimUniCurio
        """
        curio_list: List[MatchResult] = []

        for rect in rect_list:
            title_part = cv2_utils.crop_image_only(screen, rect)
            title_ocr = self.ctx.ocr.run_ocr_single_line(title_part)
            # cv2_utils.show_image(title_part, wait=0)

            curio = match_best_curio_by_ocr(title_ocr)

            if curio is None:  # 有一个识别不到就返回 提速
                return curio_list

            log.info('识别到奇物 %s', curio)
            curio_list.append(MatchResult(1,
                                          rect.x1, rect.y1,
                                          rect.width, rect.height,
                                          data=curio))

        return curio_list

    def _get_curio_to_choose(self, curio_pos_list: List[MatchResult]) -> Optional[MatchResult]:
        """
        根据优先级选择对应的奇物
        :param curio_pos_list: 奇物列表
        :return:
        """
        curio_list = [curio.data for curio in curio_pos_list]
        target_idx = SimUniChooseCurio.get_curio_by_priority(curio_list, self.config)
        if target_idx is None:
            return None
        else:
            return curio_pos_list[target_idx]

    @staticmethod
    def get_curio_by_priority(curio_list: List[SimUniCurio], config: Optional[SimUniChallengeConfig]) -> Optional[int]:
        """
        根据优先级选择对应的奇物
        :param curio_list: 可选的奇物列表
        :param config: 挑战配置
        :return: 选择的下标
        """
        if config is None:
            return 0

        for curio_id in config.curio_priority:
            curio_enum = SimUniCurioEnum[curio_id]
            for idx, opt_curio in enumerate(curio_list):
                if curio_enum.value == opt_curio:
                    return idx

        return 0

    @node_from(from_name='选择奇物')
    @node_from(from_name='点击空白处继续')
    @operation_node(name='确认后画面判断')
    def _check_after_confirm(self) -> OperationRoundResult:
        """
        确认后判断画面
        :return:
        """
        screen = self.screenshot()
        state = sim_uni_screen_state.get_sim_uni_screen_state(
            self.ctx, screen,
            in_world=True,
            curio=True,
            drop_curio=True,
            bless=True,
            drop_bless=True,
            empty_to_close=True)

        log.info(f'当前画面状态 {state}')
        if state is None:
            # 未知情况都先点击一下
            self.round_by_click_area('模拟宇宙', '点击空白处关闭')
            return self.round_retry('未能判断当前页面', wait=1)
        elif state == sim_uni_screen_state.ScreenState.SIM_CURIOS.value:
            # 还在选奇物的画面 说明上一步没有选择到奇物
            # 只有2个奇物的时候，使用3个奇物的第1个位置 可能会识别到奇物(名字位置重叠) 这时候点击第1个位置是会失败的
            # 所以每次重试 curio_cnt_type-=1 即重试的时候 需要排除调3个奇物的位置 尝试2个奇物的位置
            self.curio_cnt_type -= 1
            if self.curio_cnt_type <= 0:
                return self.round_fail("点击确认失败")
            else:
                return self.round_success(sim_uni_screen_state.ScreenState.SIM_CURIOS.value)
        elif state in [sim_uni_screen_state.ScreenState.SIM_BLESS.value,
                       sim_uni_screen_state.ScreenState.SIM_DROP_BLESS.value,
                       sim_uni_screen_state.ScreenState.SIM_DROP_CURIOS.value]:
            return self.round_success(state)
        else:
            return self.round_success(state)

    @node_from(from_name='确认后画面判断', status=sim_uni_screen_state.ScreenState.EMPTY_TO_CLOSE.value)
    @operation_node(name='点击空白处继续')
    def _click_empty_to_continue(self) -> OperationRoundResult:
        return self.round_by_click_area('模拟宇宙', '点击空白处关闭',
                                        success_wait=2, retry_wait=1)


class SimUniDropCurio(SrOperation):

    DROP_BTN: ClassVar[Rect] = Rect(1024, 647, 1329, 698)  # 确认丢弃
    STATUS_RETRY: ClassVar[str] = '重试其他奇物位置'

    def __init__(self, ctx: SrContext, config: Optional[SimUniChallengeConfig] = None,
                 skip_first_screen_check: bool = True):
        """
        模拟宇宙中 丢弃奇物
        :param ctx:
        :param config: 挑战配置
        :param skip_first_screen_check: 是否跳过第一次画面状态检查
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('丢弃奇物', 'game')))

        self.config: Optional[SimUniChallengeConfig] = config
        self.skip_first_screen_check: bool = skip_first_screen_check  # 是否跳过第一次的画面状态检查 用于提速

    def handle_init(self) -> Optional[OperationRoundResult]:
        """
        执行前的初始化 由子类实现
        注意初始化要全面 方便一个指令重复使用
        可以返回初始化后判断的结果
        - 成功时跳过本指令
        - 失败时立刻返回失败
        - 不返回时正常运行本指令
        """
        self.first_screen_check = True  # 是否第一次检查画面状态
        self.curio_cnt_type: int = 3  # 奇物数量类型 3 2 1

        return None

    @operation_node(name='画面检测', is_start_node=True)
    def _check_screen_state(self):
        screen = self.screenshot()

        if self.first_screen_check and self.skip_first_screen_check:
            self.first_screen_check = False
            return self.round_success(sim_uni_screen_state.ScreenState.SIM_DROP_CURIOS.value)

        state = sim_uni_screen_state.get_sim_uni_screen_state(self.ctx, screen, drop_curio=True)

        if state is not None:
            return self.round_success(state)
        else:
            return self.round_retry('未在丢弃奇物页面', wait=1)

    @node_from(from_name='画面检测')
    @node_from(from_name='确认', status=STATUS_RETRY)
    @operation_node(name='选择奇物')
    def _choose_curio(self) -> OperationRoundResult:
        screen = self.screenshot()

        curio_pos_list: List[MatchResult] = self._get_curio_pos(screen)
        if len(curio_pos_list) == 0:
            return self.round_retry('未识别到奇物', wait=1)

        target_curio_pos: Optional[MatchResult] = self._get_curio_to_choose(curio_pos_list)
        self.ctx.controller.click(target_curio_pos.center)
        time.sleep(0.25)
        self.ctx.controller.click(SimUniChooseCurio.CONFIRM_BTN.center)
        return self.round_success(wait=1)

    def _get_curio_pos(self, screen: MatLike) -> List[MatchResult]:
        """
        获取屏幕上的奇物的位置
        :param screen: 屏幕截图
        :return: MatchResult.data 中是对应的奇物 SimUniCurio
        """
        curio_list = self._get_curio_pos_by_rect(screen, SimUniChooseCurio.CURIO_RECT_3_LIST)
        if len(curio_list) > 0 and self.curio_cnt_type >= 3:
            return curio_list

        curio_list = self._get_curio_pos_by_rect(screen, SimUniChooseCurio.CURIO_RECT_2_LIST)
        if len(curio_list) > 0 and self.curio_cnt_type >= 2:
            return curio_list

        curio_list = self._get_curio_pos_by_rect(screen, SimUniChooseCurio.CURIO_RECT_1_LIST)
        if len(curio_list) > 0 and self.curio_cnt_type >= 1:
            return curio_list

        return []

    def _get_curio_pos_by_rect(self, screen: MatLike, rect_list: List[Rect]) -> List[MatchResult]:
        """
        获取屏幕上的奇物的位置
        :param screen: 屏幕截图
        :param rect_list: 指定区域
        :return: MatchResult.data 中是对应的奇物 SimUniCurio
        """
        curio_list: List[MatchResult] = []

        for rect in rect_list:
            title_part = cv2_utils.crop_image_only(screen, rect)
            title_ocr = self.ctx.ocr.run_ocr_single_line(title_part)
            # cv2_utils.show_image(title_part, wait=0)

            curio = match_best_curio_by_ocr(title_ocr)

            if curio is None:  # 有一个识别不到就返回 提速
                return curio_list

            log.info('识别到奇物 %s', curio)
            curio_list.append(MatchResult(1,
                                          rect.x1, rect.y1,
                                          rect.width, rect.height,
                                          data=curio))

        return curio_list

    def _get_curio_to_choose(self, curio_pos_list: List[MatchResult]) -> Optional[MatchResult]:
        """
        根据优先级选择对应的奇物
        :param curio_pos_list: 奇物列表
        :return:
        """
        curio_list = [curio.data for curio in curio_pos_list]
        target_idx = SimUniDropCurio.get_curio_by_priority(curio_list, self.config)
        if target_idx is None:
            return None
        else:
            return curio_pos_list[target_idx]

    @staticmethod
    def get_curio_by_priority(curio_list: List[SimUniCurio], config: Optional[SimUniChallengeConfig]) -> Optional[int]:
        """
        根据优先级选择对应的奇物 要丢弃的应该是优先级最低的
        :param curio_list: 可选的奇物列表
        :param config: 挑战配置
        :return: 选择的下标
        """
        if config is None:
            return 0

        opt_priority_list: List[int] = [99 for _ in curio_list]  # 选项的优先级
        cnt = 0

        for curio_enum in SimUniCurioEnum:
            curio = curio_enum.value
            if not curio.negative:  # 优先丢弃负面奇物
                continue
            for idx, opt_curio in enumerate(curio_list):
                if curio_enum.value == opt_curio and opt_priority_list[idx] == 99:
                    opt_priority_list[idx] = cnt
                    cnt += 1

        for curio_enum in SimUniCurioEnum:
            curio = curio_enum.value
            if not curio.invalid_after_got:  # 优先丢弃已失效奇物
                continue
            for idx, opt_curio in enumerate(curio_list):
                if curio_enum.value == opt_curio and opt_priority_list[idx] == 99:
                    opt_priority_list[idx] = cnt
                    cnt += 1

        for curio_id in config.curio_priority:
            curio_enum = SimUniCurioEnum[curio_id]
            for idx, opt_curio in enumerate(curio_list):
                if curio_enum.value == opt_curio and opt_priority_list[idx] == 99:
                    opt_priority_list[idx] = cnt
                    cnt += 1

        max_priority: Optional[int] = None
        max_idx: Optional[int] = None
        for idx in range(0, len(opt_priority_list)):
            if max_idx is None or opt_priority_list[idx] > max_priority:
                max_idx = idx
                max_priority = opt_priority_list[idx]

        return max_idx

    @node_from(from_name='选择奇物')
    @operation_node(name='确认')
    def _confirm(self) -> OperationRoundResult:
        """
        确认丢弃
        :return:
        """
        op = ClickDialogConfirm(self.ctx, wait_after_success=2)
        op_result = op.execute()
        if op_result.success:
            return self.round_success()
        else:
            # 只有2个奇物的时候，使用3个奇物的第1个位置 可能会识别到奇物(名字位置重叠) 这时候点击第1个位置是会失败的
            # 所以每次重试 curio_cnt_type-=1 即重试的时候 需要排除调3个奇物的位置 尝试2个奇物的位置
            self.curio_cnt_type -= 1
            if self.curio_cnt_type > 0:
                return self.round_success(status=SimUniDropCurio.STATUS_RETRY)
            else:
                return self.round_fail(op_result.status)
