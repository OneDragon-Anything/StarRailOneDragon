from typing import Optional, List

from one_dragon.base.config.yaml_config import YamlConfig
from one_dragon_qt.widgets.setting_card.yaml_config_adapter import YamlConfigAdapter
from sr_od.interastral_peace_guide.guide_data import SrGuideData
from sr_od.interastral_peace_guide.guide_def import GuideMission, GuideCategory


class TrailblazePowerPlanItem:

    def __init__(self, mission_id: str, team_num: int, support: str, plan_times: int,
                 run_times: int = 0, diff: int = 0):
        self.mission_id: str = mission_id  # 关卡id - 新
        self.team_num: int = team_num  # 使用配队 0代表游戏内当前配队
        self.support: str = support  # 支援角色 'none'或者None就是没有
        self.plan_times: int = plan_times  # 计划通关次数
        self.run_times: int = run_times  # 已经通关次数
        self.diff: int = diff  # 难度 0代表自动最高

        self.mission: Optional[GuideMission] = None


class TrailblazePowerConfig(YamlConfig):

    def __init__(self,
                 guide_data: SrGuideData,
                 instance_idx: Optional[int] = None):
        YamlConfig.__init__(self,'trailblaze_power', instance_idx=instance_idx)

        self.guide_data: SrGuideData = guide_data
        self.plan_list: List[TrailblazePowerPlanItem] = []

        self.init_plan_list()

    def init_plan_list(self) -> None:
        """
        体力规划配置
        :return:
        """
        self.plan_list = []
        for i in self.get('plan_list', []):
            mission_id = i.get('mission_id', '')
            mission = self.guide_data.get_mission_by_unique_id(mission_id)
            if mission is None:  # 过滤旧数据
                continue

            item = TrailblazePowerPlanItem(**i)
            item.mission = mission

            self.plan_list.append(item)

    def add_plan(self) -> None:
        """
        增加一个计划
        """
        category_config_list = self.guide_data.get_category_list_in_power_plan()
        category: GuideCategory = category_config_list[0].value
        mission_config_list = self.guide_data.get_mission_list_in_power_plan(category)
        mission: GuideMission = mission_config_list[0].value
        history: TrailblazePowerPlanItem = self.get_history_by_uid(mission.unique_id)
        item = TrailblazePowerPlanItem(
            mission.unique_id,
            team_num=0 if history is None else history.team_num,
            support='none' if history is None else history.support,
            plan_times=1 if history is None else history.plan_times,
            run_times=0,
            diff=0 if history is None else history.diff,
        )
        item.mission = mission

        self.plan_list.append(item)

    def update_plan(self, idx: int, new_plan: TrailblazePowerPlanItem):
        if idx >= len(self.plan_list):
            return

        self.plan_list[idx] = new_plan

        self.save()

    def delete_plan(self, idx: int) -> None:
        """
        删除一个计划
        """
        if idx >= len(self.plan_list):
            return

        self.plan_list.pop(idx)
        self.save()

    def move_up(self, idx: int) -> None:
        """
        将一个计划往上移动
        """
        if idx >= len(self.plan_list) or idx <= 0:
            return

        tmp = self.plan_list[idx]
        self.plan_list[idx] = self.plan_list[idx - 1]
        self.plan_list[idx - 1] = tmp

        self.save()

    def move_top(self, idx: int) -> None:
        """
        将一个计划移动到顶部
        """
        if idx >= len(self.plan_list) or idx <= 0:
            return

        tmp = self.plan_list[idx]
        self.plan_list.pop(idx)
        self.plan_list.insert(0, tmp)

        self.save()

    def add_run_times(self, mission_id: str, run_times: int) -> None:
        """
        增加运行次数
        """
        plan_list: List[TrailblazePowerPlanItem] = self.plan_list
        for item in plan_list:
            if item.mission_id == mission_id and item.run_times < item.plan_times:
                item.run_times += run_times
                self.save()
                return

    def save(self) -> None:
        """
        保存
        """
        data = {}

        data['plan_list'] = [
            {
                'mission_id': i.mission_id,
                'team_num': i.team_num,
                'support': i.support,
                'plan_times': i.plan_times,
                'run_times': i.run_times,
                'diff': i.diff
            }
            for i in self.plan_list
        ]

        # 当前内容存入历史
        history_teams = self.get('history_teams', [])
        for i in self.plan_list:
            in_history = False
            for history_data in history_teams:
                if history_data.get('mission_id', '') != i.mission_id:
                    continue

                history_data['team_num'] = i.team_num
                history_data['support'] = i.support
                history_data['plan_times'] = i.plan_times
                history_data['diff'] = i.diff

                in_history = True

            if not in_history:
                history_teams.append({
                    'mission_id': i.mission_id,
                    'team_num': i.team_num,
                    'support': i.support,
                    'plan_times': i.plan_times,
                    'diff': i.diff
                })

        data['history_teams'] = history_teams
        data['loop'] = self.loop

        self.data = data
        YamlConfig.save(self)

    @property
    def history_teams(self) -> List[TrailblazePowerPlanItem]:
        """
        历史配置
        :return:
        """
        return [TrailblazePowerPlanItem(**i) for i in self.get('history_teams', [])]

    def get_history_by_uid(self, mission_id: str) -> Optional[TrailblazePowerPlanItem]:
        old_history_teams = self.history_teams
        for item in old_history_teams:
            if item.mission_id == mission_id:
                return item
        return None

    @property
    def loop(self) -> bool:
        """
        是否循环执行
        """
        return self.get('loop', True)

    @loop.setter
    def loop(self, new_value: bool):
        self.update('loop', new_value)

    @property
    def loop_adapter(self) -> YamlConfigAdapter:
        return YamlConfigAdapter(self, 'loop', True)

    def _is_same_plan(self, x: TrailblazePowerPlanItem, y: TrailblazePowerPlanItem) -> bool:
        if x is None or y is None:
            return False

        # 比较ID, 运行次数, 计划次数
        return (x.mission_id == y.mission_id) and (x.plan_times == y.plan_times) and (x.run_times == y.run_times)

    def get_next_plan(self, last_tried_plan: Optional[TrailblazePowerPlanItem] = None) -> Optional[
        TrailblazePowerPlanItem]:
        """
        获取下一个未完成的计划任务。
        如果提供了 last_tried_plan，则从该任务之后开始查找。
        如果未提供，则从列表的开头查找第一个未完成任务。
        不再在此方法内调用 reset_plans，重置逻辑由调用方（ChargePlanApp）管理。
        """
        len_plan_list = len(self.plan_list)
        if len_plan_list == 0:
            return None

        start_index = 0
        if last_tried_plan is not None:
            # 1. 从上次尝试的计划之后开始查找
            # 倒序查找避免用户配置两个相同关卡后循环查找到前一个关卡从而无法达到计划末尾
            last_tried_index = -1
            for j in range(len_plan_list):
                i = len_plan_list - 1 - j
                plan = self.plan_list[i]
                if self._is_same_plan(plan, last_tried_plan):
                    last_tried_index = i
                    break

            if last_tried_index != -1:
                start_index = last_tried_index + 1
                # 如果已到达列表末尾，返回 None
                if start_index >= len(self.plan_list):
                    return None
            else:
                # 2. 找不到上次计划则从头开始
                start_index = 0

        # 3. 从指定位置开始遍历查找符合条件的计划
        for i in range(start_index, len(self.plan_list)):
            plan = self.plan_list[i]
            if plan.run_times < plan.plan_times:
                return plan

        # 4. 检查完一轮都没找到合适的计划
        return None

    def check_plan_run_times(self) -> None:
        """
        检查计划的运行次数 如果都完成了就重置
        """
        changed = False
        while True:
            plan_list: List[TrailblazePowerPlanItem] = self.plan_list
            any_incomplete = False
            for item in plan_list:
                if item.run_times < item.plan_times:
                    any_incomplete = True
                    break

            if any_incomplete:
                break

            for item in plan_list:
                item.run_times -= item.plan_times
            changed = True

        if changed:
            self.save()
