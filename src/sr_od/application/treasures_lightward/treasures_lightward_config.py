from typing import List, Optional

from basic.config import ConfigHolder
from sr.app.app_description import AppDescriptionEnum
from sr.treasures_lightward.treasures_lightward_team_module import TreasuresLightwardTeamModule, \
    TreasuresLightwardTeamModuleItem


class TreasuresLightwardConfig(ConfigHolder):

    def __init__(self, account_idx: Optional[int] = None):
        ConfigHolder.__init__(self, AppDescriptionEnum.TREASURES_LIGHTWARD.value.id, account_idx=account_idx)

    def _init_after_read_file(self):
        # 2024-05-25 加入旧配置向新配置转换
        team_module_list = self.team_module_list
        changed: bool = False
        if len(team_module_list) > 0:
            for module in team_module_list:
                if module.character_id_list is None or len(module.character_id_list) == 0:
                    continue
                if module.character_list is not None and len(module.character_list) > 0:
                    continue
                module.character_list = [
                    TreasuresLightwardTeamModuleItem(i)
                    for i in module.character_id_list
                ]
                changed = True

        if changed:
            self.team_module_list = team_module_list

    @property
    def team_module_list(self) -> List[TreasuresLightwardTeamModule]:
        arr = self.get('team_module_list', [])
        ret = []
        for i in arr:
            ret.append(TreasuresLightwardTeamModule(**i))
        return ret

    @team_module_list.setter
    def team_module_list(self, new_list: List[TreasuresLightwardTeamModule]):
        dict_arr = []
        for i in new_list:
            dict_arr.append(i.to_dict())
        self.update('team_module_list', dict_arr)
