import os

from one_dragon.base.config.config_item import ConfigItem
from one_dragon.base.config.yaml_operator import YamlOperator
from one_dragon.utils import os_utils, str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.interastral_peace_guide.guide_def import (
    GuideCategory,
    GuideMission,
    GuideTab,
)


class SrGuideData:

    def __init__(self):
        self.tab_list: list[GuideTab] = []
        self.category_list: list[GuideCategory] = []
        self.mission_list: list[GuideMission] = []

        self.tab_2_category: dict[str, list[GuideCategory]] = {}
        self.category_2_mission: dict[str, list[GuideMission]] = {}

        self.load_data()

    def load_data(self) -> None:
        """
        读取文件
        """
        self.tab_list: list[GuideTab] = []
        self.category_list: list[GuideCategory] = []
        self.mission_list: list[GuideMission] = []

        self.tab_2_category: dict[str, list[GuideCategory]] = {}
        self.category_2_mission: dict[str, list[GuideMission]] = {}

        file_path = os.path.join(
            os_utils.get_path_under_work_dir('assets', 'game_data'),
            'interastral_peace_guide_data.yml'
        )
        yaml_data = YamlOperator(file_path)

        for tab_data in yaml_data.data:
            self.init_tab(tab_data)

    def init_tab(self, tab_data: dict):
        """
        初始化一个tab
        """
        tab_name = tab_data.get('tab_name', '')
        tab = GuideTab(tab_name)
        self.tab_list.append(tab)
        self.tab_2_category[tab.unique_id] = []

        for category_data in tab_data.get('category_list', []):
            self.init_category(tab, category_data)

    def init_category(self, tab: GuideTab, category_data: dict):
        """
        初始化一个分类
        """
        category_name = category_data.get('category_name', '')
        category = GuideCategory(
            tab, category_name,
            ui_cn=category_data.get('display_name'),
            show_in_power_plan=category_data.get('show_in_power_plan', False),
            remark_in_game=category_data.get('remark_in_game'),
        )

        self.category_list.append(category)
        self.tab_2_category[tab.unique_id].append(category)
        self.category_2_mission[category.unique_id] = []

        for mission_data in category_data.get('mission_list', []):
            self.init_mission(category, mission_data)

    def init_mission(self, category: GuideCategory, mission_data: dict):
        """
        初始化一个副本
        """
        mission = GuideMission(
            category,
            mission_name=mission_data.get('mission_name', ''),
            display_name=mission_data.get('display_name'),
            power=mission_data.get('power', 0),

            region_name=mission_data.get('region_name'),
            show_in_power_plan=mission_data.get('show_in_power_plan', False),
        )

        self.mission_list.append(mission)
        self.category_2_mission[category.unique_id].append(mission)

    def best_match_tab_by_name(self, ocr_word: str) -> GuideTab | None:
        """
        根据OCR结果匹配TAB
        """
        target_list = [gt(i.cn, 'game') for i in self.tab_list]

        idx = str_utils.find_best_match_by_difflib(ocr_word, target_word_list=target_list)
        if idx is None:
            return None
        else:
            return self.tab_list[idx]

    def best_match_category_by_name(self, ocr_word: str, tab: GuideTab) -> GuideCategory | None:
        """
        根据OCR结果匹配GuideCategory
        """
        category_list = self.tab_2_category.get(tab.unique_id, [])
        target_list = [gt(i.cn, 'game') for i in category_list]
        idx = str_utils.find_best_match_by_difflib(ocr_word, target_word_list=target_list)
        if idx is None:
            return None
        else:
            return category_list[idx]

    def best_match_mission_by_name(self, ocr_word: str, category: GuideCategory, region_name: str | None = None) -> GuideMission | None:
        """
        根据OCR结果匹配GuideMission
        """
        mission_list = self.category_2_mission.get(category.unique_id, [])
        if region_name is not None:
            mission_list = [i for i in mission_list if i.region_name == region_name]

        target_list = [gt(i.mission_name, 'game') for i in mission_list]
        idx = str_utils.find_best_match_by_difflib(ocr_word, target_word_list=target_list)
        if idx is None:
            return None
        else:
            return mission_list[idx]

    def get_mission_by_unique_id(self, unique_id: str) -> GuideMission | None:
        """
        根据唯一标识获取对应的副本
        """
        for mission in self.mission_list:
            if mission.unique_id == unique_id:
                return mission

    def get_mission_by_guide_info(self, category_name: str, mission_name: str,
                                  region_name: str) -> GuideMission | None:
        """
        按 (分类名, 关卡名, 区域名) 精确匹配副本——口径与
        dungeon_drop_const.MATERIAL_MISSIONS 的 {category, mission, region}
        三元组一致(生成器 join 时即取自指南关卡字段),供材料刷取定位用
        """
        for mission in self.mission_list:
            if (mission.cate.cn == category_name
                    and mission.mission_name == mission_name
                    and mission.region_name == region_name):
                return mission
        return None

    def get_category_list_in_power_plan(self) -> list[ConfigItem]:
        """
        体力计划里的分类
        """
        return [
            ConfigItem(label=i.ui_cn, value=i)
            for i in self.category_list
            if i.show_in_power_plan
        ]

    def get_mission_list_in_power_plan(self, category: GuideCategory) -> list[ConfigItem]:
        """
        体力计划里的副本
        """
        return [
            ConfigItem(label=i.display_name, value=i)
            for i in self.category_2_mission.get(category.unique_id, [])
            if i.show_in_power_plan
        ]


def __debug():
    data = SrGuideData()
    print(len(data.tab_list))
    print(len(data.category_list))
    print(len(data.mission_list))


if __name__ == '__main__':
    __debug()
