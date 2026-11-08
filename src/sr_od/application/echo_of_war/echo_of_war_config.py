from typing import List, Optional

from one_dragon.base.config.yaml_config import YamlConfig
from one_dragon.utils.i18_utils import gt
from sr_od.application.trailblaze_power.trailblaze_power_config import TrailblazePowerPlanItem
from sr_od.interastral_peace_guide.guide_data import SrGuideData
from sr_od.interastral_peace_guide.guide_def import GuideMission


def get_war_mission_list(guide_data: SrGuideData) -> list[GuideMission]:
    """
    指南里历战余响分类的全部关卡(周本全量)
    :return: 关卡列表,顺序即指南内分类顺序
    """
    tab = guide_data.best_match_tab_by_name(gt('生存索引', 'game'))
    category = guide_data.best_match_category_by_name(gt('历战余响', 'game'), tab)
    return guide_data.category_2_mission.get(category.unique_id, [])


class EchoOfWarConfig(YamlConfig):

    def __init__(self, guide_data: SrGuideData, instance_idx: Optional[int] = None):
        YamlConfig.__init__(self, 'echo_of_war', instance_idx=instance_idx)

        self.guide_data = guide_data
        self.plan_list: List[TrailblazePowerPlanItem] = []
        self.init_plan_list()

    def init_plan_list(self):
        war_list: List[GuideMission] = get_war_mission_list(self.guide_data)

        id_2_plan = {}

        for i in self.get('plan_list', []):
            mission_id = i.get('mission_id', '')
            mission = self.guide_data.get_mission_by_unique_id(mission_id)
            if mission is None:  # 过滤旧数据
                continue

            item = TrailblazePowerPlanItem(**i)
            item.mission = mission

            id_2_plan[mission_id] = item

        for war in war_list:
            existed_plan = id_2_plan.get(war.unique_id, None)
            if existed_plan is None:
                item = TrailblazePowerPlanItem(
                    mission_id=war.unique_id,
                    team_num=0,
                    support='none',
                    plan_times=1,
                    run_times=0,
                    diff=0,
                )
                item.mission = war
                self.plan_list.append(item)
            else:
                self.plan_list.append(existed_plan)

    def check_plan_finished(self):
        """
        检测计划是否都执行完了
        执行完的话 所有执行次数置为0 重新开始下一轮
        :return:
        """
        changed = False
        while True:
            plan_list: List[TrailblazePowerPlanItem] = self.plan_list
            if not plan_list:  # 空计划:无东西可重置,且 any_incomplete 永远 False 会死循环
                break
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

    @property
    def next_plan_item(self) -> Optional[TrailblazePowerPlanItem]:
        """
        按规划配置列表，找到第一个还没有完成的去执行
        如果都完成了 选择第一个
        :return: 下一个需要执行的计划
        """
        for item in self.plan_list:
            if item.run_times < item.plan_times:
                return item

        return None

    def update_plan(self, idx: int, new_plan: TrailblazePowerPlanItem):
        if idx >= len(self.plan_list):
            return

        self.plan_list[idx] = new_plan

        self.save()

    def update_plan_by_mission_id(self, mission_id: str, new_plan: TrailblazePowerPlanItem) -> bool:
        """
        按 mission_id 原位更新计划并落盘(MCP 通用配置路由 ``update_config_item`` 的领域方法)

        历战余响的计划列表由 init_plan_list 按周本全量补齐 —— 正确操作语义是改既有
        条目的次数,而非增删条目(增删会在下次 init_plan_list 时被全量补齐重排/还原)。
        原位替换保持列表顺序,mission 关联沿用既有条目。
        :param mission_id: 定位用的关卡 id,须与 new_plan.mission_id 一致(防改错条目)
        :param new_plan: 替换后的计划项
        :return: True=定位并更新;False=列表中无该 mission_id
        :raises ValueError: new_plan.mission_id 与定位 mission_id 不一致
        """
        if new_plan.mission_id != mission_id:
            raise ValueError(
                f'new_plan.mission_id ({new_plan.mission_id}) 与定位 mission_id ({mission_id}) 不一致'
            )
        for i, item in enumerate(self.plan_list):
            if item.mission_id != mission_id:
                continue
            new_plan.mission = item.mission
            self.plan_list[i] = new_plan
            self.save()
            return True
        return False

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

        self.data = data
        YamlConfig.save(self)

