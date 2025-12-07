import time

from typing import Optional, List

from one_dragon.base.operation.one_dragon_context import OneDragonContext
from one_dragon.utils import i18_utils
from sr_od.app.assignments.assignments_run_record import AssignmentsRunRecord
from sr_od.app.buy_xianzhou_parcel.buy_xianzhou_parcel_run_record import BuyXianZhouParcelRunRecord
from sr_od.app.claim_email.email_run_record import EmailRunRecord
from sr_od.app.daily_training.daily_training_run_record import DailyTrainingRunRecord
from sr_od.app.echo_of_war.echo_of_war_config import EchoOfWarConfig
from sr_od.app.echo_of_war.echo_of_war_run_record import EchoOfWarRunRecord
from sr_od.app.nameless_honor.nameless_honor_run_record import NamelessHonorRunRecord
from sr_od.app.relic_salvage.relic_salvage_config import RelicSalvageConfig
from sr_od.app.relic_salvage.relic_salvage_run_record import RelicSalvageRunRecord
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig, SimUniChallengeConfigData
from sr_od.app.sim_uni.sim_uni_config import SimUniConfig
from sr_od.app.sim_uni.sim_uni_route_data import SimUniRouteData
from sr_od.app.sim_uni.sim_uni_run_record import SimUniRunRecord
from sr_od.app.support_character.support_character_run_record import SupportCharacterRunRecord
from sr_od.app.trailblaze_power.trailblaze_power_config import TrailblazePowerConfig
from sr_od.app.trailblaze_power.trailblaze_power_run_record import TrailblazePowerRunRecord
from sr_od.app.trick_snack.trick_snack_config import TrickSnackConfig
from sr_od.app.trick_snack.trick_snack_record import TrickSnackRunRecord
from sr_od.app.memory_crystal_shard.memory_crystal_shard_run_record import MemoryCrystalShardRunRecord
from sr_od.app.world_patrol.world_patrol_config import WorldPatrolConfig
from sr_od.app.world_patrol.world_patrol_route_data import WorldPatrolRouteData
from sr_od.app.world_patrol.world_patrol_run_record import WorldPatrolRunRecord
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
        self.load_instance_config()

    def init_by_config(self) -> None:
        """
        根据配置进行初始化
        :return:
        """
        OneDragonContext.init_by_config(self)
        i18_utils.update_default_lang(self.game_config.lang)

        self.controller = SrPcController(
            game_config=self.game_config,
            win_title=self.game_config.win_title,
            standard_width=self.project_config.screen_standard_width,
            standard_height=self.project_config.screen_standard_height
        )

    def load_instance_config(self) -> None:
        OneDragonContext.load_instance_config(self)

        # 切换实例后 所有信息都需要重置
        self.pos_info: ContextPosInfo = ContextPosInfo()
        self.team_info: TeamInfo = TeamInfo()
        self.sim_uni_info = SimUniInfo()
        self.detect_info: DetectInfo = DetectInfo()

        from sr_od.config.game_config import GameConfig
        self.game_config: GameConfig = GameConfig(self.current_instance_idx)
        from one_dragon.base.config.game_account_config import GameAccountConfig
        self.game_account_config: GameAccountConfig = GameAccountConfig(self.current_instance_idx)

        game_refresh_hour_offset = self.game_account_config.game_refresh_hour_offset

        from sr_od.config.notify_config import NotifyConfig
        self.notify_config: NotifyConfig = NotifyConfig(self.current_instance_idx)
        from sr_od.app.notify.notify_run_record import NotifyRunRecord
        self.notify_record: NotifyRunRecord = NotifyRunRecord(self.current_instance_idx, game_refresh_hour_offset)

        self.world_patrol_config: WorldPatrolConfig = WorldPatrolConfig(self.current_instance_idx)
        self.world_patrol_record: WorldPatrolRunRecord = WorldPatrolRunRecord(self.current_instance_idx, game_refresh_hour_offset)

        self.power_config: TrailblazePowerConfig = TrailblazePowerConfig(self.guide_data, self.current_instance_idx)
        self.power_record: TrailblazePowerRunRecord = TrailblazePowerRunRecord(self.power_config, self.current_instance_idx, game_refresh_hour_offset)

        self.echo_of_war_config: EchoOfWarConfig = EchoOfWarConfig(self.guide_data, self.current_instance_idx)
        self.echo_of_war_run_record: EchoOfWarRunRecord = EchoOfWarRunRecord(self.current_instance_idx, game_refresh_hour_offset)

        self.sim_uni_challenge_config_data: SimUniChallengeConfigData = SimUniChallengeConfigData()
        self.sim_uni_config: SimUniConfig = SimUniConfig(self.current_instance_idx)
        self.sim_uni_record: SimUniRunRecord = SimUniRunRecord(self.sim_uni_config, self.current_instance_idx, game_refresh_hour_offset)

        self.assignments_run_record: AssignmentsRunRecord = AssignmentsRunRecord(self.current_instance_idx, game_refresh_hour_offset)
        self.nameless_honor_run_record: NamelessHonorRunRecord = NamelessHonorRunRecord(self.current_instance_idx, game_refresh_hour_offset)
        self.daily_training_run_record: DailyTrainingRunRecord = DailyTrainingRunRecord(self.current_instance_idx, game_refresh_hour_offset)
        self.email_run_record: EmailRunRecord = EmailRunRecord(self.current_instance_idx, game_refresh_hour_offset)
        self.buy_xz_parcel_run_record: BuyXianZhouParcelRunRecord = BuyXianZhouParcelRunRecord(self.current_instance_idx, game_refresh_hour_offset)
        self.memory_crystal_shard_run_record: MemoryCrystalShardRunRecord = MemoryCrystalShardRunRecord(self.current_instance_idx, game_refresh_hour_offset)
        self.support_character_run_record: SupportCharacterRunRecord = SupportCharacterRunRecord(self.current_instance_idx, game_refresh_hour_offset)

        self.relic_salvage_config: RelicSalvageConfig = RelicSalvageConfig(self.current_instance_idx)
        self.relic_salvage_run_record: RelicSalvageRunRecord = RelicSalvageRunRecord(self.current_instance_idx, game_refresh_hour_offset)

        self.trick_snack_config: TrickSnackConfig = TrickSnackConfig(self.current_instance_idx)
        self.trick_snack_run_record: TrickSnackRunRecord = TrickSnackRunRecord(self.current_instance_idx, game_refresh_hour_offset)

    @property
    def sim_uni_challenge_config(self) -> Optional[SimUniChallengeConfig]:
        if self.sim_uni_info.world_num == 0 or self.sim_uni_config is None:
            return None
        else:
            return self.sim_uni_config.get_challenge_config(self.sim_uni_info.world_num)

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
        return self.team_info.is_first_feixiao and self.world_patrol_config.technique_fight

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
