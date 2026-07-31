from typing import Optional, List, ClassVar

from basic.i18_utils import gt
from basic.img import cv2_utils
from basic.log_utils import log
from sr.app.app_run_record import AppRunRecord
from sr.app.application_base import Application
from sr.app.treasures_lightward.treasures_lightward_config import TreasuresLightwardConfig
from sr.app.treasures_lightward.treasures_lightward_record import TreasuresLightwardRunRecord, \
    TreasuresLightwardScheduleRecord
from sr.const import phone_menu_const
from sr.const.character_const import CharacterCombatType, Character
from sr.context.context import Context
from sr.operation import StateOperationEdge, StateOperationNode, OperationResult, OperationOneRoundResult, Operation
from sr.operation.common.back_to_normal_world_plus import BackToNormalWorldPlus
from sr.operation.unit.forgotten_hall.get_reward_in_fh import GetRewardInForgottenHall
from sr.interastral_peace_guide.guide_const import GuideTabEnum
from sr.interastral_peace_guide.choose_guide_tab import ChooseGuideTab
from sr.operation.unit.menu.click_phone_menu_item import ClickPhoneMenuItem
from sr.operation.unit.menu.open_phone_menu import OpenPhoneMenu
from sr.screen_area.screen_treasures_lightward import ScreenTreasuresLightWard
from sr.treasures_lightward.op.challenge_mission import ChallengeTreasuresLightwardMission
from sr.treasures_lightward.op.check_max_unlock_mission import CheckMaxUnlockMission
from sr.treasures_lightward.op.check_star import TlCheckTotalStar
from sr.treasures_lightward.treasures_lightward_const import TreasuresLightwardTypeEnum
from sr.treasures_lightward.treasures_lightward_team_module import search_best_mission_team


class TreasuresLightwardApp(Application):

    STATUS_SHOULD_CHALLENGE: ClassVar[str] = '进行挑战'

    def __init__(self, ctx: Context):
        self.run_record: Optional[TreasuresLightwardRunRecord] = ctx.tl_run_record
        edges: List[StateOperationEdge] = []

        world = StateOperationNode('返回大世界', op=BackToNormalWorldPlus(ctx))

        open_menu = StateOperationNode('打开菜单', op=OpenPhoneMenu(ctx))
        edges.append(StateOperationEdge(world, open_menu))

        choose_guide = StateOperationNode('选择【指南】', op=ClickPhoneMenuItem(ctx, phone_menu_const.INTERASTRAL_GUIDE))
        edges.append(StateOperationEdge(open_menu, choose_guide))

        choose_treasure = StateOperationNode('选择【逐光捡金】', op=ChooseGuideTab(ctx, GuideTabEnum.TAB_4.value))
        edges.append(StateOperationEdge(choose_guide, choose_treasure))

        # 忘却之庭
        choose_fh = StateOperationNode('选择【忘却之庭】', self._choose_forgotten_hall)
        edges.append(StateOperationEdge(choose_treasure, choose_fh))

        fh_check_record = StateOperationNode('检测【忘却之庭】记录', self._check_record_and_tp)
        edges.append(StateOperationEdge(choose_fh, fh_check_record))

        # 虚构叙事
        choose_pf = StateOperationNode('选择【虚构叙事】', self._choose_pure_fiction)
        edges.append(StateOperationEdge(fh_check_record, choose_pf, ignore_status=True))  # 忘却之庭完成后 进行虚构叙事

        pf_check_record = StateOperationNode('检测【虚构叙事】记录', self._check_record_and_tp)
        edges.append(StateOperationEdge(choose_pf, pf_check_record))

        pf_start_screen = StateOperationNode('【虚构叙事】新一期画面检测', self._check_pf_new_start)
        edges.append(StateOperationEdge(pf_check_record, pf_start_screen, status=TreasuresLightwardApp.STATUS_SHOULD_CHALLENGE))

        # 公共挑战部分
        check_total_star = StateOperationNode('检测总星数', self._check_total_star)
        edges.append(StateOperationEdge(fh_check_record, check_total_star, status=TreasuresLightwardApp.STATUS_SHOULD_CHALLENGE))  # 需要进行挑战 检测星数
        edges.append(StateOperationEdge(pf_start_screen, check_total_star))  # 需要进行挑战 检测星数

        finished = StateOperationNode('设置完成', self._check_schedule_finished)
        edges.append(StateOperationEdge(check_total_star, finished, status=TlCheckTotalStar.STATUS_FULL_STAR))  # 满星的时候直接设置为成功

        get_reward = StateOperationNode('领取奖励', op=GetRewardInForgottenHall(ctx))
        edges.append(StateOperationEdge(finished, get_reward))

        back_menu = StateOperationNode('返回菜单', op=OpenPhoneMenu(ctx))
        edges.append(StateOperationEdge(get_reward, back_menu))
        edges.append(StateOperationEdge(back_menu, choose_guide))  # 继续下一期的挑战

        check_max_unlock = StateOperationNode('最大的已解锁关卡', self._check_unlock)
        edges.append(StateOperationEdge(check_total_star, check_max_unlock, ignore_status=True))  # 非满星的时候找到开始关卡

        challenge_mission = StateOperationNode('挑战关卡', self._challenge_next_mission)
        edges.append(StateOperationEdge(check_max_unlock, challenge_mission))  # 挑战

        check_total_star_before_next = StateOperationNode('关卡后检测总星数', self._check_total_star)
        edges.append(StateOperationEdge(challenge_mission, check_total_star_before_next, status='3'))  # 该关卡满星就循环挑战下一关
        edges.append(StateOperationEdge(check_total_star_before_next, challenge_mission))

        edges.append(StateOperationEdge(challenge_mission, finished, ignore_status=True))  # 没满星就不挑战下一个了

        super().__init__(ctx, op_name=gt('逐光捡金', 'game'),
                         run_record=self.run_record, edges=edges)

        self.schedule_type: TreasuresLightwardTypeEnum = TreasuresLightwardTypeEnum.FORGOTTEN_HALL  # 当前挑战类型
        self.challenge_schedule: Optional[TreasuresLightwardScheduleRecord] = None  # 当前挑战的期数
        self.config: TreasuresLightwardConfig = self.ctx.tl_config
        self.current_mission_num: int = 1  # 当前挑战的关卡
        self.max_unlock_num: int = 1  # 最大解锁的关卡
        self.challenged_set: set[str] = set()  # 本次运行已经挑战的
        self.from_last_schedule = False  # 本次挑战是否从上期继续的 如果是的话 3星之后可以将前面的关卡都设为3星

    def _choose_forgotten_hall(self):
        """
        在【指南】-【逐光捡金】画面 选择【忘却之庭】
        :return:
        """
        area = ScreenTreasuresLightWard.TL_CATEGORY_FORGOTTEN_HALL.value
        click = self.find_and_click_area(area)
        if click == Operation.OCR_CLICK_SUCCESS:
            self.schedule_type = TreasuresLightwardTypeEnum.FORGOTTEN_HALL
            return self.round_success()
        else:
            return self.round_retry('点击%s失败', area.text)

    def _choose_pure_fiction(self):
        """
        在【指南】-【逐光捡金】画面 选择【虚构叙事】
        :return:
        """
        area = ScreenTreasuresLightWard.TL_CATEGORY_PURE_FICTION.value
        click = self.find_and_click_area(area)
        if click == Operation.OCR_CLICK_SUCCESS:
            self.schedule_type = TreasuresLightwardTypeEnum.PURE_FICTION
            return self.round_success(wait=1)
        else:
            return self.round_retry('点击%s失败', area.text)

    def _check_record_and_tp(self):
        """
        在【指南】-【逐光捡金】画面 检查对应排期的运行记录 并传送到一个没有完成挑战的
        :return:
        """
        screen = self.screenshot()
        tp_area_list = [ScreenTreasuresLightWard.TL_SCHEDULE_1_TRANSPORT.value, ScreenTreasuresLightWard.TL_SCHEDULE_2_TRANSPORT.value]
        name_area_list = [ScreenTreasuresLightWard.TL_SCHEDULE_1_NAME.value, ScreenTreasuresLightWard.TL_SCHEDULE_2_NAME.value]

        self.challenge_schedule = None
        to_challenge_idx: int = -1
        find_schedule: bool = False
        for i in range(2):
            if self.find_area(tp_area_list[i], screen):
                find_schedule = True

                part = cv2_utils.crop_image_only(screen, name_area_list[i].rect)
                schedule_name = self.ctx.ocr.run_ocr_single_line(part)
                existed_schedule: TreasuresLightwardScheduleRecord = self.run_record.match_existed_schedule(self.schedule_type, schedule_name)
                if existed_schedule is None:
                    self.challenge_schedule = self.run_record.add_schedule(self.schedule_type, schedule_name)
                    to_challenge_idx = i
                elif not existed_schedule['finished'] and existed_schedule['schedule_name'] not in self.challenged_set:
                    self.challenge_schedule = existed_schedule
                    to_challenge_idx = i

        if not find_schedule:
            return self.round_retry('未检测到相关挑战', wait=1)

        if to_challenge_idx == -1:  # 没有需要挑战的
            return self.round_success()

        self.challenged_set.add(self.challenge_schedule['schedule_name'])

        click_tp = self.ctx.controller.click(tp_area_list[to_challenge_idx].rect.center)
        if click_tp:
            return self.round_success(TreasuresLightwardApp.STATUS_SHOULD_CHALLENGE, wait=3)
        else:
            return self.round_retry('点击传送失败', wait=1)

    def _check_pf_new_start(self) -> OperationOneRoundResult:
        screen = self.screenshot()

        title = ScreenTreasuresLightWard.PF_TITLE.value
        if self.find_area(title, screen):
            return self.round_success()

        start = ScreenTreasuresLightWard.PF_NEW_START.value
        click = self.find_and_click_area(start, screen)
        if click == Operation.OCR_CLICK_SUCCESS:
            return self.round_success(wait=1)

        return self.round_retry('未进入虚构叙事画面', wait=1)

    def _check_total_star(self) -> OperationOneRoundResult:
        """
        获取总星数 判断是否需要挑战
        :return:
        """
        op = TlCheckTotalStar(self.ctx, self.schedule_type)
        op_result = op.execute()
        if op_result.success:
            self.run_record.update_total_star(self.challenge_schedule, op_result.data)
        return self.round_by_op(op_result)

    def _check_schedule_finished(self) -> OperationOneRoundResult:
        """
        挑战结束后 判断星数是否已经满星 满星则将该期设置为完成
        :return:
        """
        op = TlCheckTotalStar(self.ctx, self.schedule_type)
        op_result = op.execute()
        if op_result.success:
            self.run_record.update_total_star(self.challenge_schedule, op_result.data)

        if self.challenge_schedule['total_star'] >= self.get_max_num() * 3:
            self.challenge_schedule['finished'] = True
            self.run_record.save()
        return self.round_success()

    def _on_mission_finished(self, op_result: OperationResult):
        """
        通关后更新星数
        并找到下一个需要挑战的关卡
        :param op_result:
        :return:
        """
        if not op_result.success:
            return
        mission_num: int = self.current_mission_num
        star: int = op_result.data
        log.info('%s 关卡 %d 当前星数 %d', self.challenge_schedule['schedule_name'], mission_num, star)
        self.run_record.update_mission_star(self.challenge_schedule, mission_num, star)

        if star == 3:
            if self.from_last_schedule:  # 从上期挑战继续的 那前面关卡都可以设置成3星
                for i in range(1, mission_num):
                    self.run_record.update_mission_star(self.challenge_schedule, i, star)
            # 进入下一关
            self.current_mission_num += 1

    def _cal_team_member(self, node_combat_types: List[List[CharacterCombatType]]) -> Optional[List[List[Character]]]:
        """
        根据关卡属性计算对应配队
        :param node_combat_types: 节点对应的属性
        :return:
        """
        module_list = self.config.team_module_list
        filter_module_list = []
        for module in module_list:
            if not module.fit_schedule_type(self.schedule_type):
                continue
            if not module.fit_combat_type(node_combat_types):
                continue
            filter_module_list.append(module)
        result = search_best_mission_team(node_combat_types, filter_module_list)
        if result is not None:
            log.info('得到配队')
            for team in result:
                log.info([i.cn for i in team if i is not None])
        return result

    def _update_record_after_stop(self, result: OperationResult):
        """
        应用停止后的对运行记录的更新
        :param result: 运行结果
        :return:
        """
        self.run_record.update_status(AppRunRecord.STATUS_SUCCESS)

    def _on_max_unlock_done(self, op_result: OperationResult):
        """
        更新最大的未解锁关卡 初始化最初挑战的关卡
        :return:
        """
        last_num: int = self.get_num_able_to_continue()
        if op_result.success:
            max_unlock_num: int = op_result.data
            log.info('最大已解锁关卡 %02d', max_unlock_num)
            self.from_last_schedule = False  # 是否从上期继续的
            if max_unlock_num <= last_num:
                for i in range(max_unlock_num, 0, -1):  # 可以从上期继续的 优先挑战高的
                    if self.run_record.get_mission_star(self.challenge_schedule, i) < 3:
                        self.current_mission_num = i
                        self.from_last_schedule = True
                        break
            else:  # 已经解锁可继续之后的 哪关没满就打哪
                for i in range(1, max_unlock_num + 1):
                    if self.run_record.get_mission_star(self.challenge_schedule, i) < 3:
                        self.current_mission_num = i
                        break

    def get_num_able_to_continue(self) -> int:
        """
        根据类型 获取可以从上期继续的关卡数
        :return:
        """
        if self.schedule_type == TreasuresLightwardTypeEnum.FORGOTTEN_HALL:
            return 7
        elif self.schedule_type == TreasuresLightwardTypeEnum.PURE_FICTION:
            return 3
        else:
            return 1

    def get_max_num(self) -> int:
        """
        获取最大关卡
        :return:
        """
        if self.schedule_type == TreasuresLightwardTypeEnum.FORGOTTEN_HALL:
            return 12
        elif self.schedule_type == TreasuresLightwardTypeEnum.PURE_FICTION:
            return 4
        else:
            return 1

    def _check_unlock(self) -> OperationOneRoundResult:
        op = CheckMaxUnlockMission(self.ctx, self.schedule_type, self._on_max_unlock_done)
        return self.round_by_op(op.execute())

    def _challenge_next_mission(self) -> OperationOneRoundResult:
        """
        获取下一个挑战关卡的指令
        :return: 指令
        """
        if self.current_mission_num > self.get_max_num() or \
                self.run_record.get_total_star(self.challenge_schedule) >= self.get_max_num() * 3:
            return self.round_success()

        op = ChallengeTreasuresLightwardMission(self.ctx,
                                                self.schedule_type,
                                                self.current_mission_num, 2,
                                                cal_team_func=self._cal_team_member,
                                                op_callback=self._on_mission_finished)
        return self.round_by_op(op.execute())
