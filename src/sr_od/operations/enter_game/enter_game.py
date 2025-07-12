import time
from typing import Optional

from cv2.typing import MatLike

from one_dragon.base.config.basic_game_config import TypeInputWay
from one_dragon.base.config.one_dragon_config import InstanceRun
from one_dragon.base.controller.pc_clipboard import PcClipboard
from one_dragon.base.matcher.ocr import ocr_utils
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.sr_operation import SrOperation


class EnterGame(SrOperation):

    def __init__(self, ctx: SrContext, switch: bool = False):
        """
        进入游戏后 进行登陆
        :param ctx:
        """
        SrOperation.__init__(self, ctx, op_name=gt('进入游戏'))

        self.force_login: bool = (self.ctx.one_dragon_config.instance_run == InstanceRun.ALL.value.value
            and len(self.ctx.one_dragon_config.instance_list_in_od) > 1)

        # 切换账号的情况下 一定需要登录
        if switch:
            self.force_login = True

        self.already_login: bool = False  # 是否已经登录了
        self.use_clipboard: bool = self.ctx.game_config.type_input_way == TypeInputWay.CLIPBOARD.value.value  # 使用剪切板输入

    @node_from(from_name='国服-输入账号密码')
    @node_from(from_name='登陆其他账号')
    @operation_node(name='画面识别', node_max_retry_times=60, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.screenshot()

        login_result = self.check_login_related(screen)
        if login_result is not None:
            return login_result

        interact_result = self.check_screen_to_interact(screen)
        if interact_result is not None:
            return interact_result

        in_game_result = self.round_by_find_area(screen, '大世界', '角色图标')
        if in_game_result.is_success:  # 右上角有角色图标
            return self.round_success(status='大世界', wait=1)

        return self.round_retry(wait=1)

    def check_login_related(self, screen: MatLike) -> OperationRoundResult:
        """
        判断登陆相关的出现内容
        :param screen: 游戏画面
        :return: 是否有相关操作 有的话返回对应操作结果
        """
        # 判断“错误提示-重新启动”
        result_restart = self.round_by_find_and_click_area(screen, '进入游戏', '错误提示-重新启动')
        if result_restart.is_success:
            # 点击到“重新启动”，说明需要检查本地网络连接情况。
            return self.round_fail("获取全局分发错误，登录失败，请检查网络设置并重新启动脚本")

        if self.force_login and not self.already_login:
            result = self.round_by_find_area(screen, '进入游戏', '文本-点击进入')
            if result.is_success:
                result2 = self.round_by_find_and_click_area(screen, '进入游戏', '按钮-登出确定')
                if result2.is_success:
                    return self.round_wait(result2.status, wait=2)

                result2 = self.round_by_find_area(screen, '进入游戏-退出登陆', '标题-退出登录')
                if result2.is_success:
                    return self.round_success(result2.status)

                result2 = self.round_by_find_and_click_area(screen, '进入游戏', '按钮-登出')
                if result2.is_success:
                    return self.round_wait(result2.status, wait=1)

                return self.round_retry(result2.status, wait=1)
            else:
                result2 = self.round_by_find_and_click_area(screen, '进入游戏-选择账号', '按钮-登陆其他账号')
                if result2.is_success:
                    return self.round_wait(result2.status, wait=1)
        else:
            result = self.round_by_find_and_click_area(screen, '进入游戏', '文本-点击进入')
            if result.is_success:
                return self.round_wait(result.status, wait=1)

            result = self.round_by_find_and_click_area(screen, '进入游戏', '提示-确认')
            if result.is_success:
                # 如果检测到了“提示-确认”并点击
                return self.round_wait(status=result.status, wait=1)

        result = self.round_by_find_and_click_area(screen, '进入游戏', '国服-账号密码')
        if result.is_success:
            return self.round_success(result.status, wait=1)

        result = self.round_by_find_and_click_area(screen, '进入游戏', '文本-开始游戏')
        if result.is_success:
            return self.round_wait(result.status, wait=1)

        return None

    @node_from(from_name='画面识别', status='国服-账号密码')
    @operation_node(name='国服-输入账号密码')
    def input_account_password(self) -> OperationRoundResult:
        if self.ctx.game_account_config.account == '' or self.ctx.game_account_config.password == '':
            return self.round_fail('未配置账号密码')

        screen = self.screenshot()
        self.round_by_click_area('进入游戏', '国服-账号输入区域')
        time.sleep(0.5)
        if self.use_clipboard:
            PcClipboard.copy_and_paste(self.ctx.game_account_config.account)
        else:
            self.ctx.controller.keyboard_controller.keyboard.type(self.ctx.game_account_config.account)
        time.sleep(1.5)

        self.round_by_click_area('进入游戏', '国服-密码输入区域')
        time.sleep(0.5)
        if self.use_clipboard:
            PcClipboard.copy_and_paste(self.ctx.game_account_config.password)
        else:
            self.ctx.controller.keyboard_controller.keyboard.type(self.ctx.game_account_config.password)
        time.sleep(1.5)

        result = self.round_by_find_area(screen, '进入游戏', '文本-同意-旧')
        if result.is_success:
            self.round_by_click_area('进入游戏', '国服-同意按钮-旧')

        result = self.round_by_find_area(screen, '进入游戏', '文本-同意-新')
        if result.is_success:
            self.round_by_click_area('进入游戏', '国服-同意按钮')
        time.sleep(0.5)

        screen = self.screenshot()
        self.already_login = True
        return self.round_by_find_and_click_area(screen, '进入游戏', '国服-账号密码进入游戏',
                                                 success_wait=5, retry_wait=1)

    @node_from(from_name='画面识别', status='标题-退出登录')
    @operation_node(name='退出并保留登陆记录')
    def logout_with_account_kept(self) -> OperationRoundResult:
        screen = self.screenshot()
        self.round_by_click_area('进入游戏-退出登陆', '按钮-退出并保留登陆记录', success_wait=1)
        return self.round_by_find_and_click_area(screen, '进入游戏-退出登陆', '按钮-退出',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='退出并保留登陆记录')
    @operation_node(name='登陆其他账号')
    def choose_other_account(self) -> OperationRoundResult:
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '进入游戏-选择账号', '按钮-登陆其他账号',
                                                 success_wait=1, retry_wait=1)

    def check_screen_to_interact(self, screen: MatLike) -> Optional[OperationRoundResult]:
        """
        判断画面 处理可能出现的需要交互的情况
        :param screen: 游戏画面
        :return: 是否有相关操作 有的话返回对应操作结果
        """
        ocr_result_map = self.ctx.ocr.run_ocr(screen)

        target_word_list: list[str] = [
            '确认',  # 登陆失败 issue #442
            '点击领取今日补贴',  # 小月卡
        ]
        ignore_list: list[str] = [
        ]
        target_word_idx_map: dict[str, int] = {}
        to_match_list: list[str] = []
        for idx, target_word in enumerate(target_word_list):
            target_word_idx_map[target_word] = idx
            to_match_list.append(gt(target_word, 'game'))

        match_word, match_word_mrl = ocr_utils.match_word_list_by_priority(
            ocr_result_map,
            target_word_list,
            ignore_list=ignore_list
        )
        if match_word is not None and match_word_mrl is not None and match_word_mrl.max is not None:
            for mr in match_word_mrl:
                self.ctx.controller.click(mr.center)
                time.sleep(1)
            return self.round_wait(status=match_word)

        return None

    @node_from(from_name='画面识别', status='大世界')
    @operation_node(name='等待画面加载')
    def wait_game(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()
    app = EnterGame(ctx, switch=True)
    app.execute()


if __name__ == '__main__':
    __debug()
