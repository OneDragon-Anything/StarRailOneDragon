from typing import Optional, TypedDict, List

from basic import str_utils
from basic.os_utils import get_sunday_dt, dt_day_diff
from sr.app.app_description import AppDescriptionEnum
from sr.app.app_run_record import AppRunRecord
from sr.treasures_lightward.treasures_lightward_const import TreasuresLightwardTypeEnum


class TreasuresLightwardScheduleRecord(TypedDict):
    """
    每期挑战的记录
    """

    schedule_type: str  # 该期挑战的类型
    schedule_name: str  # 该期挑战的名称
    add_dt: str  # 开始记录的日期
    mission_star: dict[int, int]  # 每一关的星数
    total_star: int  # 总星数
    finished: bool  # 是否完成挑战


class TreasuresLightwardRunRecord(AppRunRecord):

    def __init__(self, account_idx: Optional[int] = None):
        super().__init__(AppDescriptionEnum.TREASURES_LIGHTWARD.value.id, account_idx=account_idx)
        self.base_sunday: str = '20240204'

    def _should_reset_by_dt(self):
        """
        根据时间判断是否应该重置状态 每两周会有一个新的关卡
        :return:
        """
        old_turn = self.get_turn_by_dt(self.dt)

        current_dt = self.get_current_dt()
        current_turn = self.get_turn_by_dt(current_dt)

        return current_turn > old_turn

    def get_turn_by_dt(self, dt: str) -> int:
        """
        获取某个日期对应的轮次
        :param dt:
        :return:
        """
        sunday = get_sunday_dt(dt)
        sunday_day_diff = dt_day_diff(sunday, self.base_sunday)
        sunday_week_diff = sunday_day_diff // 7
        return sunday_week_diff // 2

    def reset_record(self):
        """
        运行记录重置 非公共部分由各app自行实现
        :return:
        """
        super().reset_record()

    @property
    def schedule_list(self) -> List[TreasuresLightwardScheduleRecord]:
        return self.get('schedule_list', [])

    @schedule_list.setter
    def schedule_list(self, new_list: List[TreasuresLightwardScheduleRecord]):
        self.update('schedule_list', new_list)

    def add_schedule(self, schedule_type: TreasuresLightwardTypeEnum, schedule_name: str) -> TreasuresLightwardScheduleRecord:
        """
        增加新一期的记录
        :param schedule_type: 类型
        :param schedule_name: 名称
        :return:
        """
        old_list = self.schedule_list
        new_schedule = TreasuresLightwardScheduleRecord(
            schedule_type=schedule_type.value,
            schedule_name=schedule_name,
            mission_star={},
            total_star=0,
            add_dt=self.get_current_dt(),
            finished=False)
        old_list.append(new_schedule)
        self.schedule_list = old_list
        return new_schedule

    def is_schedule_existed(self, schedule_type: TreasuresLightwardTypeEnum, schedule_name: str):
        """
        某一期的记录是否已经存在
        :param schedule_type: 类型
        :param schedule_name: 名称
        :return:
        """
        schedule_list = self.schedule_list
        for schedule in schedule_list:
            if schedule['schedule_type'] != schedule_type.value:
                continue
            if str_utils.find_by_lcs(schedule['schedule_name'], schedule_name, percent=0.7):
                return True
        return False

    def match_existed_schedule(self, schedule_type: TreasuresLightwardTypeEnum, schedule_name: str) -> Optional[TreasuresLightwardScheduleRecord]:
        """
        匹配一起已经存在的记录
        :param schedule_type:
        :param schedule_name:
        :return:
        """
        schedule_list = self.schedule_list
        for schedule in schedule_list:
            if schedule['schedule_type'] != schedule_type.value:
                continue
            if str_utils.find_by_lcs(schedule['schedule_name'], schedule_name, percent=0.7):
                return schedule
        return None

    @property
    def should_challenge_fh(self) -> bool:
        """
        判断当前是否应该挑战 忘却之庭
        :return:
        """
        return self.should_challenge_by_type(TreasuresLightwardTypeEnum.FORGOTTEN_HALL)

    @property
    def should_challenge_pure_fiction(self) -> bool:
        """
        判断当前是否应该挑战 虚构叙事
        :return:
        """
        return self.should_challenge_by_type(TreasuresLightwardTypeEnum.PURE_FICTION)

    def should_challenge_by_type(self, schedule_type: TreasuresLightwardTypeEnum) -> bool:
        """
        判断当前是否该挑战某种类型
        :param schedule_type:
        :return:
        """
        # 找出最新一期的日期
        last_dt = '20230101'
        schedule_list = self.schedule_list
        for schedule in schedule_list:
            if schedule['schedule_type'] != schedule_type.value:
                continue
            if schedule['add_dt'] > last_dt:
                last_dt = schedule['add_dt']

        # 找出日期对应的轮次
        old_turn = self.get_turn_by_dt(last_dt)
        current_dt = self.get_current_dt()
        current_turn = self.get_turn_by_dt(current_dt)

        # 可能有新一轮
        if current_turn > old_turn:
            return True

        # 没有新一轮的情况下 看之前的是否都已经挑战完成了
        for schedule in schedule_list:
            if schedule['schedule_type'] != schedule_type.value:
                continue
            if not schedule['finished']:
                return True

        return False

    def get_total_star(self, schedule: TreasuresLightwardScheduleRecord) -> int:
        """
        某期挑战的总星数
        :param schedule: 当前挑战的期数
        :return: 星数
        """
        return 0 if 'total_star' not in schedule else schedule['total_star']

    def get_mission_star(self, schedule: TreasuresLightwardScheduleRecord, mission_num: int):
        """
        某个关卡的星数
        :param schedule: 当前挑战的期数
        :param mission_num: 关卡编号
        :return: 星数
        """
        stars = schedule['mission_star']
        return stars[mission_num] if mission_num in stars else 0

    def update_total_star(self, schedule: TreasuresLightwardScheduleRecord, total_star: int):
        """
        更新某一期的总星数
        :param schedule:
        :param total_star:
        :return:
        """
        schedule['total_star'] = total_star
        self.save()

    def update_mission_star(self, schedule: TreasuresLightwardScheduleRecord, mission_num: int, star: int):
        """
        更新某个关卡的星数
        :param schedule: 当前挑战的期数
        :param mission_num: 关卡编号
        :param star: 星数
        :return:
        """
        stars = schedule['mission_star']
        stars[mission_num] = star
        self.save()

    def get_latest_total_star(self, schedule_type: TreasuresLightwardTypeEnum):
        """
        获取某类型的
        :param schedule_type:
        :return:
        """
        latest_dt = '20230101'
        total_star = 0
        for schedule in self.schedule_list:
            if schedule['schedule_type'] != schedule_type.value:
                continue
            if schedule['add_dt'] > latest_dt:
                latest_dt = schedule['add_dt']
                total_star = self.get_total_star(schedule)
        return total_star
