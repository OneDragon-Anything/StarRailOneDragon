import time

from functools import cached_property
from typing import Optional, List

from one_dragon.base.operation.application import application_const
from one_dragon.base.operation.one_dragon_context import OneDragonContext
from one_dragon.utils import i18_utils
from sr_od.application.sim_universe.sim_uni_challenge_config import SimUniChallengeConfig, SimUniChallengeConfigData
from sr_od.application.sim_universe.sim_uni_route_data import SimUniRouteData
from sr_od.application.world_patrol.world_patrol_route_data import WorldPatrolRouteData
from sr_od.config.character_const import Character, TECHNIQUE_ATTACK, TECHNIQUE_BUFF, TECHNIQUE_BUFF_ATTACK, FEIXIAO, \
    TECHNIQUE_BUFF_ATTACK_DISAPPEAR
from sr_od.context.context_pos_info import ContextPosInfo
from sr_od.context.preheat_context import SrPreheatContext
from sr_od.context.sr_pc_controller import SrPcController
from sr_od.interastral_peace_guide.guide_data import SrGuideData
from sr_od.screen_state.yolo_screen_detector import YoloScreenDetector
from sr_od.sr_map.sr_map_data import SrMapData


class TeamInfo:

    def __init__(self,
                 character_list: Optional[List[Character]] = None,
                 current_active: int = 0):
        """
        当前组队信息
        """
        self.character_list: List[Character] = character_list
        self.current_active: int = current_active  # 当前使用的是第几个角色

    @property
    def is_attack_technique(self) -> bool:
        """
        当前角色使用的秘技是否buff类型
        :return:
        """
        if self.character_list is None or len(self.character_list) == 0:
            return False
        if self.current_active < 0 or self.current_active >= len(self.character_list):
            return False
        if self.character_list[self.current_active] is None:
            return False
        return self.character_list[self.current_active].technique_type in [TECHNIQUE_ATTACK]

    @property
    def is_buff_technique(self) -> bool:
        """
        当前角色使用的秘技是否buff类型
        :return:
        """
        if self.character_list is None or len(self.character_list) == 0:
            return False
        if self.current_active < 0 or self.current_active >= len(self.character_list):
            return False
        if self.character_list[self.current_active] is None:
            return False
        return self.character_list[self.current_active].technique_type in [
            TECHNIQUE_BUFF,
            TECHNIQUE_BUFF_ATTACK,
            TECHNIQUE_BUFF_ATTACK_DISAPPEAR,
        ]

    @property
    def is_buff_attack_disappear_technique(self) -> bool:
        """
        当前角色使用的秘技是否buff攻击后重置
        :return:
        """
        if self.character_list is None or len(self.character_list) == 0:
            return False
        if self.current_active < 0 or self.current_active >= len(self.character_list):
            return False
        if self.character_list[self.current_active] is None:
            return False
        return self.character_list[self.current_active].technique_type  == TECHNIQUE_BUFF_ATTACK_DISAPPEAR

    def update_character_list(self, new_character_list: List[Character]):
        self.character_list = new_character_list

    def same_as_current(self, new_character_list: List[Character]):
        """
        是否跟当前配队一致
        :param new_character_list:
        :return:
        """
        if self.character_list is None and new_character_list is None:
            return True
        elif self.character_list is None:
            return False
        elif new_character_list is None:
            return False
        elif self.character_list is not None and len(self.character_list) != len(new_character_list):
            return False
        else:
            for i in range(len(self.character_list)):
                if self.character_list[i] is None and new_character_list[i] is None:
                    return True
                elif self.character_list[i] is None or new_character_list[i] is None:
                    return False
                elif self.character_list[i].id != new_character_list[i].id:
                    return False
            return True

    @property
    def is_first_feixiao(self) -> bool:
        return (
                self.character_list is not None
                and len(self.character_list) > 0
                and self.character_list[0] is not None
                and self.character_list[0].id == FEIXIAO.id
        )

    def get_buff_lasting_seconds(self, num: int) -> float:
        """
        获取BUFF持续时间
        :param num: 第几个角色 从1开始
        """
        if self.character_list is None:  # 随便设一个默认值兜底
            return 20
        idx = num - 1
        if idx < 0 or idx >= len(self.character_list) or self.character_list[idx] is None:
            return 20
        return self.character_list[idx].buff_lasting_seconds


class SimUniInfo:

    def __init__(self):
        """
        模拟宇宙信息
        """
        self.world_num: int = 0  # 当前第几世界


class DetectInfo:

    def __init__(self):
        """
        用于目标检测的一些信息
        """
        self.view_down: bool = False  # 当前视角是否已经下移 形成俯视角度


class SrContext(OneDragonContext):

    def __init__(self):
        OneDragonContext.__init__(self)

        self.controller: Optional[SrPcController] = None
        self.is_pc: bool = True
        self.record_coordinate: bool = True  # 记录坐标

        self.map_data: SrMapData = SrMapData()
        self.world_patrol_route_data: WorldPatrolRouteData = WorldPatrolRouteData(self.map_data)
        self.sim_uni_route_data: SimUniRouteData = SimUniRouteData(self.map_data)
        self.guide_data: SrGuideData = SrGuideData()

        self.pos_info: ContextPosInfo = ContextPosInfo()
        self.team_info: TeamInfo = TeamInfo()
        self.sim_uni_info = SimUniInfo()
        self.detect_info: DetectInfo = DetectInfo()

        # 秘技相关
        self.technique_used: bool = False  # 新一轮战斗前是否已经使用秘技了
        self.last_use_tech_time: float = 0  # 上一次使用秘技的时间
        self.ban_technique: bool = False  # 禁用秘技 部分路线中途可能需要模拟按键 这时候不能有秘技影响移动速度

        # 共用配置
        from sr_od.config.model_config import ModelConfig
        self.model_config: ModelConfig = ModelConfig()

        # 服务
        from one_dragon.base.cv_process.cv_service import CvService
        self.cv_service: CvService = CvService(self)
        self.yolo_detector: YoloScreenDetector = YoloScreenDetector(
            standard_resolution_h=self.project_config.screen_standard_height,
            standard_resolution_w=self.project_config.screen_standard_width
        )
        self.preheat_context = SrPreheatContext(self)

        # 实例独有的配置
        self.reload_instance_config()

    def register_application_factory(self) -> None:
        OneDragonContext.register_application_factory(self)
        self.app_group_manager.set_default_apps(self.run_context.default_group_apps)
        self.app_group_manager.clear_config_cache()

        from one_dragon.base.config.notify_config import NotifyConfig
        self.notify_config = NotifyConfig(self.current_instance_idx, self.run_context.notify_app_map)

    def refresh_application_registration(self) -> None:
        OneDragonContext.refresh_application_registration(self)

        from one_dragon.base.config.notify_config import NotifyConfig
        self.notify_config = NotifyConfig(self.current_instance_idx, self.run_context.notify_app_map)

    def init_by_config(self) -> None:
        """
        根据配置进行初始化
        :return:
        """
        self.init()

    def init_controller(self) -> None:
        i18_utils.update_default_lang(self.game_config.lang)

        if self.controller is not None:
            self.controller.cleanup_after_app_shutdown()

        self.controller = SrPcController(
            game_config=self.game_config,
            screenshot_method=self.env_config.screenshot_method,
            standard_width=self.project_config.screen_standard_width,
            standard_height=self.project_config.screen_standard_height
        )
        self.controller.set_window_title(self._get_win_title())

    def _get_win_title(self) -> str:
        if self.game_account_config.use_custom_win_title:
            return self.game_account_config.custom_win_title
        return self.game_config.win_title

    def load_instance_config(self) -> None:
        self.reload_instance_config()

    @cached_property
    def sim_uni_challenge_config_data(self) -> SimUniChallengeConfigData:
        return SimUniChallengeConfigData()

    def reload_instance_config(self) -> None:
        OneDragonContext.reload_instance_config(self)

        # 切换实例后 所有信息都需要重置
        self.pos_info: ContextPosInfo = ContextPosInfo()
        self.team_info: TeamInfo = TeamInfo()
        self.sim_uni_info = SimUniInfo()
        self.detect_info: DetectInfo = DetectInfo()

        from sr_od.config.game_config import GameConfig
        self.game_config: GameConfig = GameConfig(self.current_instance_idx)
        from one_dragon.base.config.game_account_config import GameAccountConfig
        self.game_account_config: GameAccountConfig = GameAccountConfig(self.current_instance_idx)
        from one_dragon.base.config.notify_config import NotifyConfig
        self.notify_config: NotifyConfig = NotifyConfig(self.current_instance_idx, self.run_context.notify_app_map)

        for prop in [
            'sim_uni_challenge_config_data',
        ]:
            if prop in self.__dict__:
                del self.__dict__[prop]

    def on_switch_instance(self) -> None:
        self.init_controller()

    @property
    def sim_uni_challenge_config(self) -> Optional[SimUniChallengeConfig]:
        from sr_od.application.sim_universe import sim_universe_const
        sim_uni_config = self.run_context.get_config(
            app_id=sim_universe_const.APP_ID,
            instance_idx=self.current_instance_idx,
            group_id=application_const.DEFAULT_GROUP_ID,
        )
        if self.sim_uni_info.world_num == 0 or sim_uni_config is None:
            return None
        else:
            return sim_uni_config.get_challenge_config(self.sim_uni_info.world_num)

    def init_for_world_patrol(self) -> None:
        self.ocr.init_model()
        self.preheat_context.preheat_for_world_patrol_async()
        self.yolo_detector.init_world_patrol_model(
            model_name=self.model_config.world_patrol,
            gpu=self.model_config.world_patrol_gpu
        )

    def init_for_sim_uni(self) -> None:
        self.ocr.init_model()
        self.preheat_context.preheat_for_world_patrol_async()  # 与锄大地共用大地图
        self.yolo_detector.init_sim_uni_model(
            model_name=self.model_config.sim_uni,
            gpu=self.model_config.sim_uni_gpu
        )

    def check_and_update_speed(self, world_patrol: bool) -> None:
        """
        根据当前1号位 判断移动速度
        """
        if world_patrol and self.is_fx_world_patrol_tech:
            self.controller.run_speed = 40
            self.controller.walk_speed = 30
        else:
            self.controller.run_speed = 30
            self.controller.walk_speed = 20

    @property
    def tech_used_in_lasting(self) -> bool:
        """
        考虑BUFF持续时间 判断是否使用了秘技
        """
        return self.technique_used and time.time() - self.last_use_tech_time <= self.team_info.get_buff_lasting_seconds(1)

    @property
    def is_fx_world_patrol_tech(self) -> bool:
        """
        锄大地场景 是否飞霄使用秘技
        :return:
        """
        if self.ban_technique:
            return False
        from sr_od.application.world_patrol import world_patrol_const
        world_patrol_config = self.run_context.get_config(
            app_id=world_patrol_const.APP_ID,
            instance_idx=self.current_instance_idx,
            group_id=application_const.DEFAULT_GROUP_ID,
        )
        return world_patrol_config is not None and self.team_info.is_first_feixiao and world_patrol_config.technique_fight

    @property
    def fx_had_used_tech(self) -> bool:
        """
        飞霄使用了秘技 = 上一次使用秘技到现在还没有超出持续时间
        :return:
        """
        if self.ban_technique:
            return True
        return self.team_info.is_first_feixiao and time.time() - self.last_use_tech_time <= self.team_info.get_buff_lasting_seconds(1)

    @property
    def world_patrol_fx_should_use_tech(self) -> bool:
        """
        锄大地场景 飞霄是否该继续使用秘技了
        :return:
        """
        if self.ban_technique:
            return False
        return self.is_fx_world_patrol_tech and time.time() - self.last_use_tech_time > self.team_info.get_buff_lasting_seconds(1)

