import os
import shutil
from typing import List, Optional

from cv2.typing import MatLike

from one_dragon.base.config.yaml_operator import YamlOperator
from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import os_utils, str_utils, cv2_utils, cal_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.application.world_patrol import world_patrol_route_utils
from sr_od.sr_map.large_map_info import LargeMapInfo
from sr_od.sr_map.sr_map_def import Planet, Region, RegionSet, SpecialPoint


class SrMapData:

    def __init__(self):
        self.planet_list: List[Planet] = []
        self.region_list: List[Region] = []
        self.planet_2_region: dict[str, List[Region]] = {}  # key=np_id

        self.region_set_list: List[RegionSet] = []
        self.planet_2_region_set: dict[str, List[RegionSet]] = {}  # key=np_id

        self.sp_list: List[SpecialPoint] = []
        self.region_2_sp: dict[str, List[SpecialPoint]] = {}

        self.load_map_data()

        self.large_map_info_map: dict[str, LargeMapInfo] = {}

    def load_map_data(self) -> None:
        """
        加载数据
        :return:
        """
        self.load_planet_data()
        self.load_region_set_data()
        self.load_region_data()
        self.load_special_point_data()

    @staticmethod
    def get_map_data_dir() -> str:
        return os_utils.get_path_under_work_dir('assets', 'game_data', 'world_patrol_map')

    def load_planet_data(self) -> None:
        """
        加载星球数据
        :return:
        """
        file_path = os.path.join(self.get_map_data_dir(), 'planet.yml')
        yaml_op = YamlOperator(file_path)
        self.planet_list = [Planet(**item) for item in yaml_op.data]

    def save_planet_data(self, new_planet_list: list[Planet]) -> None:
        """
        保存星球数据并处理相关文件重命名
        :param new_planet_list: 星球变更信息列表
        """
        # 处理星球变更（编号、ID变更导致的文件重命名）
        for current_planet in new_planet_list:
            original_planet = self.get_planet_by_cn(current_planet.cn)
            if original_planet is None:
                self._handle_new_planet(current_planet)
                continue

            # 检查是否有编号或ID变更
            has_num_change = original_planet.num != current_planet.num
            has_id_change = original_planet.id != current_planet.id

            if has_num_change or has_id_change:
                # 处理文件夹和文件重命名
                self._handle_planet_rename(original_planet, current_planet)

        # 转化成保存格式
        to_save_data = []
        for current_planet in new_planet_list:
            to_save_data.append({
                'num': current_planet.num,
                'uid': current_planet.id,
                'cn': current_planet.cn
            })

        # 按编号排序
        to_save_data.sort(key=lambda x: x['num'])

        # 保存到文件
        file_path = os.path.join(self.get_map_data_dir(), 'planet.yml')
        yaml_op = YamlOperator(file_path)
        yaml_op.data = to_save_data
        yaml_op.save()

        # 重新加载数据
        self.load_planet_data()
        self.load_region_set_data()

    def _handle_new_planet(self, current_planet: Planet) -> None:
        """
        处理新增星球
        """
        # assets/game_data/world_patrol_map 下新建文件夹
        map_data_dir = self.get_map_data_dir()
        new_folder_path = os.path.join(map_data_dir, current_planet.np_id)

        if not os.path.exists(new_folder_path):
            os.makedirs(new_folder_path)

        # config/world_patrol 下新建文件夹
        world_patrol_route_utils.get_planet_route_dir(current_planet, personal=False)

    def _handle_planet_rename(self, original_planet: Planet, current_planet: Planet) -> None:
        """
        处理星球重命名 目前只能更改 id和num
        Args:
            original_planet: 原始星球数据
            current_planet: 更改后星球数据

        Returns:
            None
        """
        # assets/game_data/world_patrol_map 下改名
        map_data_dir = self.get_map_data_dir()
        old_folder_path = os.path.join(map_data_dir, original_planet.np_id)
        if os.path.exists(old_folder_path):
            new_folder_path = os.path.join(map_data_dir, current_planet.np_id)
            # 重命名文件夹
            if os.path.exists(new_folder_path):
                # 如果目标文件夹已存在，先删除
                shutil.rmtree(new_folder_path)

            os.rename(old_folder_path, new_folder_path)

            # 重命名文件夹内的yml文件
            self._rename_planet_yml_files(new_folder_path, original_planet.np_id, current_planet.np_id)

        # config/world_patrol 下改名
        old_folder_path = world_patrol_route_utils.get_planet_route_dir(original_planet, personal=False)
        if os.path.exists(old_folder_path):
            new_folder_path = world_patrol_route_utils.get_planet_route_dir(current_planet, personal=False)
            # 重命名文件夹
            if os.path.exists(new_folder_path):
                # 如果目标文件夹已存在，先删除
                shutil.rmtree(new_folder_path)
            os.rename(old_folder_path, new_folder_path)

            # 重命名文件夹内的yml文件
            self._rename_planet_yml_files(new_folder_path, original_planet.np_id, current_planet.np_id)

    def _rename_planet_yml_files(
            self,
            folder_path: str,
            old_planet_uid: str,
            new_planet_uid: str,
    ) -> None:
        """
        重命名文件夹内的yml文件
        Args:
            folder_path: 文件夹路径
            old_planet_uid: 原始星球ID
            new_planet_uid: 新星球ID

        Returns:
            None
        """
        if not os.path.exists(folder_path):
            return

        for filename in os.listdir(folder_path):
            if filename.endswith('.yml') and filename.startswith(old_planet_uid):
                old_file_path = os.path.join(folder_path, filename)
                new_filename = filename.replace(old_planet_uid, new_planet_uid, 1)
                new_file_path = os.path.join(folder_path, new_filename)

                if os.path.exists(new_file_path):
                    # 如果目标文件已存在，先删除
                    os.remove(new_file_path)

                os.rename(old_file_path, new_file_path)

    def load_region_set_data(self) -> None:
        """
        加载区域集合数据
        :return:
        """
        self.region_set_list = []
        self.planet_2_region_set: dict[str, List[RegionSet]] = {}

        for p in self.planet_list:
            file_path = os.path.join(self.get_map_data_dir(), p.np_id, f'{p.np_id}.yml')
            yaml_op = YamlOperator(file_path)
            self.planet_2_region_set[p.np_id] = []

            for r in yaml_op.data:
                region_set = RegionSet(
                    num=r['num'],
                    uid=r['uid'],
                    cn=r['cn'],
                    floors=r.get('floors', [0]),
                    parent_region_name=r.get('parent_region_name', None),
                    parent_region_floor=r.get('parent_region_floor', None),
                    enter_template_id=r.get('enter_template_id', None),
                    enter_lm_pos=r.get('enter_lm_pos', None),
                )

                self.region_set_list.append(region_set)
                self.planet_2_region_set[p.np_id].append(region_set)

        log.info(f'区域集合数据加载完成 共{len(self.region_set_list)}个')

    def save_region_set_data(self, planet: Planet, new_region_set_list: list[RegionSet]) -> None:
        """
        保存区域集合数据
        :param planet: 星球
        :param new_region_set_list: 区域集合变更信息列表
        """
        # 转化成保存格式
        to_save_data = []
        for region_set in new_region_set_list:
            data = {
                'num': region_set.num,
                'uid': region_set.id,
                'cn': region_set.cn,
            }

            # 只有非默认值才保存
            if region_set.floors is not None and len(region_set.floors) > 1:
                data['floors'] = region_set.floors
            if region_set.parent_region_name:
                data['parent_region_name'] = region_set.parent_region_name
            if region_set.parent_region_floor is not None:
                data['parent_region_floor'] = region_set.parent_region_floor
            if region_set.enter_template_id:
                data['enter_template_id'] = region_set.enter_template_id
            if region_set.enter_lm_pos:
                data['enter_lm_pos'] = region_set.enter_lm_pos

            to_save_data.append(data)

        # 这里不需要排序 传入时已经按米游社返回顺序排好序了 编号是一条龙用于唯一标识的

        # 保存到文件
        file_path = os.path.join(self.get_map_data_dir(), planet.np_id, f'{planet.np_id}.yml')
        yaml_op = YamlOperator(file_path)
        yaml_op.data = to_save_data
        yaml_op.save()

        # 重新加载数据
        self.load_region_set_data()
        self.load_region_data()

    def get_region_set_by_planet(self, planet: Planet) -> List[RegionSet]:
        """
        根据星球获取区域集合列表
        :param planet: 星球
        :return: 区域集合列表
        """
        return self.planet_2_region_set.get(planet.np_id, [])

    def load_region_data(self) -> None:
        """
        加载区域数据
        :return:
        """
        self.region_list = []
        self.planet_2_region: dict[str, List[Region]] = {}

        for p in self.planet_list:
            file_path = os.path.join(self.get_map_data_dir(), p.np_id, f'{p.np_id}.yml')
            yaml_op = YamlOperator(file_path)
            self.planet_2_region[p.np_id] = []

            for r in yaml_op.data:
                parent_region_name = r.get('parent_region_name', None)
                parent_region_floor = r.get('parent_region_floor', 0)
                enter_template_id = r.get('enter_template_id', None)
                enter_lm_pos = r.get('enter_lm_pos', [0, 0])

                if parent_region_name is not None:
                    parent_region = self.best_match_region_by_name(parent_region_name, p, parent_region_floor)
                    enter_lm_pos = Point(enter_lm_pos[0], enter_lm_pos[1])
                else:
                    parent_region = None
                    enter_lm_pos = None

                floor_list = r.get('floors', [0])
                for floor in floor_list:
                    region = Region(r['num'], r['uid'], r['cn'], p, floor,
                                    parent=parent_region,
                                    enter_template_id=enter_template_id, enter_lm_pos=enter_lm_pos)

                    self.region_list.append(region)
                    self.planet_2_region[p.np_id].append(region)

    def get_region_sp_yml_path(self, region: Region) -> str:
        """
        获取区域特殊点配置文件路径
        Args:
            region: 区域

        Returns:
            str: 特殊点yml文件路径
        """
        return os.path.join(self.get_map_data_dir(), region.planet.np_id, f'{region.pr_id}.yml')

    def load_special_point_data(self) -> None:
        """
        加载特殊点数据
        :return:
        """
        self.sp_list = []
        self.region_2_sp = {}

        loaded_region_set = set()
        for region in self.region_list:
            if region.pr_id in loaded_region_set:
                continue
            loaded_region_set.add(region.pr_id)

            file_path = self.get_region_sp_yml_path(region)
            yaml_op = YamlOperator(file_path)

            for sp_data in yaml_op.data:
                real_planet = self.best_match_planet_by_name(sp_data['planet_name'])
                real_region = self.best_match_region_by_name(sp_data['region_name'], real_planet, sp_data.get('region_floor', 0))

                sp = SpecialPoint(sp_data['uid'], sp_data['cn'], real_region, sp_data['template_id'], sp_data['lm_pos'],
                                  sp_data.get('tp_pos', None))
                self.sp_list.append(sp)

                if real_region.pr_id not in self.region_2_sp:
                    self.region_2_sp[real_region.pr_id] = []

                self.region_2_sp[real_region.pr_id].append(sp)

    def save_special_point_data(
            self,
            region: Region,
            new_sp_list: list[SpecialPoint],
            overwrite: bool = False,
    ) -> None:
        """
        保存特殊点数据

        Args:
            region: 区域
            new_sp_list: 特殊点列表
            overwrite: 是否覆盖已有文件

        Returns:
            None
        """
        file_path = self.get_region_sp_yml_path(region)
        yaml_op = YamlOperator(file_path)
        existed_sp_list: list[SpecialPoint] = []
        if not overwrite:
            for sp_data in yaml_op.data:
                sp_region = self.get_region_by_cn(sp_data['planet_name'], sp_data['region_name'], sp_data.get('region_floor', 0))

                sp = SpecialPoint(
                    uid=sp_data['uid'],
                    cn=sp_data['cn'],
                    region=sp_region,
                    template_id=sp_data['template_id'],
                    lm_pos=sp_data['lm_pos'],
                    tp_pos=sp_data.get('tp_pos', None),
                )
                existed_sp_list.append(sp)

        # 追加到原楼层后方
        merge_sp_list: list[SpecialPoint] = []
        found_floor: bool = False
        add_new: bool = False
        for existed_sp in existed_sp_list:
            if existed_sp.region.floor == region.floor:
                found_floor = True
                merge_sp_list.append(existed_sp)
            elif not found_floor:
                merge_sp_list.append(existed_sp)
            elif not add_new:
                for new_sp in new_sp_list:
                    merge_sp_list.append(new_sp)
                add_new = True
            else:
                merge_sp_list.append(existed_sp)

        if not add_new:
            merge_sp_list.extend(new_sp_list)

        # 按照自己顺眼的格式保存
        sp_info_list: list[str] = []

        with open(file_path, 'w', encoding='utf-8') as f:
            for sp in merge_sp_list:
                sp_info = [
                    f'- uid: "{sp.id}"',
                    f'  cn: "{sp.cn}"',
                    f'  planet_name: "{sp.region.planet.cn}"',
                    f'  region_name: "{sp.region.cn}"',
                    f'  region_floor: {sp.region.floor}',
                    f'  template_id: "{sp.template_id}"',
                    f'  lm_pos: [{sp.lm_pos.x}, {sp.lm_pos.y}]',
                ]
                if sp.lm_pos.x != sp.tp_pos.x or sp.lm_pos.y != sp.tp_pos.y:
                    sp_info.append(f'  tp_pos: [{sp.tp_pos.x}, {sp.tp_pos.y}]')

                sp_info_list.append('\n'.join(sp_info))

            f.write('\n\n'.join(sp_info_list))

        log.info(f'特殊点保存成功 {region.pr_id}')

    def get_planet_by_cn(self, cn: str) -> Optional[Planet]:
        """
        根据星球的中文 获取对应常量
        :param cn: 星球中文
        :return: 常量
        """
        for i in self.planet_list:
            if i.cn == cn:
                return i
        return None

    def best_match_planet_by_name(self, ocr_word: str) -> Optional[Planet]:
        """
        根据OCR结果匹配一个星球
        :param ocr_word: OCR结果
        :return:
        """
        planet_names = [gt(p.cn, 'ocr') for p in self.planet_list]
        idx = str_utils.find_best_match_by_difflib(ocr_word, target_word_list=planet_names)
        if idx is None:
            return None
        else:
            return self.planet_list[idx]

    def get_region_by_cn(self, planet_name: str, region_name: str, floor: int = 0) -> Region | None:
        """
        根据中文名称 获取对应的区域

        Args:
            planet_name: 星球名称-中文
            region_name: 区域名称-中文
            floor: 楼层

        Returns:
            region: 区域
        """
        planet: Planet = self.get_planet_by_cn(planet_name)
        region_list: list[Region] = self.planet_2_region.get(planet.np_id, [])
        for region in region_list:
            if region.cn == region_name and region.floor == floor:
                return region
        return None

    def best_match_region_by_name(self, ocr_word: Optional[str], planet: Optional[Planet] = None,
                                  target_floor: Optional[int] = None) -> Optional[Region]:
        """
        根据OCR结果匹配一个区域 随机返回楼层
        :param ocr_word: OCR结果
        :param planet: 所属星球
        :param target_floor: 目标楼层 不传入时随机一个
        :return:
        """
        if ocr_word is None or len(ocr_word) == 0:
            return None

        to_check_region_list: List[Region] = []
        to_check_region_name_list: List[str] = []

        for region in self.region_list:
            if planet is not None and planet.np_id != region.planet.np_id:
                continue

            if target_floor is not None and target_floor != region.floor:
                continue

            to_check_region_list.append(region)
            to_check_region_name_list.append(gt(region.cn, 'ocr'))

        idx = str_utils.find_best_match_by_difflib(ocr_word, to_check_region_name_list)
        if idx is None:
            return None
        else:
            return to_check_region_list[idx]

    def region_with_another_floor(self, region: Region, floor: int) -> Optional[Region]:
        """
        获取区域的另一个楼层
        :param region: 区域
        :param floor: 目标楼层
        :return:
        """
        for r in self.region_list:
            if r.pr_id == region.pr_id and r.floor == floor:
                return r

    def get_region_with_all_floor(self, region: Region) -> List[Region]:
        """
        获取区域对应的全部楼层
        :param region:
        :return:
        """
        return [r for r in self.region_list if r.pr_id == region.pr_id]

    def get_sub_region_by_cn(self, region: Region, cn: str, floor: int = 0) -> Optional[Region]:
        """
        根据子区域的中文 获取对应常量
        :param region: 所属区域
        :param cn: 子区域名称
        :param floor: 子区域的层数
        :return: 常量
        """
        same_planet_region_list = self.planet_2_region.get(region.planet.np_id, [])
        for r in same_planet_region_list:
            # 进入子区域
            if r.parent is not None and r.parent.pr_id == region.pr_id and r.cn == cn and r.floor == floor:
                return r
            # 换了楼层
            if r.pr_id == region.pr_id and r.floor == floor:
                return r
            # 回到主区域
            if region.parent is not None and region.parent.pr_id == r.pr_id and region.parent.cn == cn and region.parent.floor == floor:
                return r
        return None

    def best_match_sp_by_name(self, region: Region, ocr_word: str) -> Optional[SpecialPoint]:
        """
        在指定区域中 忽略楼层 根据名字匹配对应的特殊点
        :param region: 区域
        :param ocr_word: 特殊点名称
        :return:
        """
        if ocr_word is None or len(ocr_word) == 0:
            return None

        to_check_sp_list: List[SpecialPoint] = self.region_2_sp.get(region.pr_id, [])
        to_check_sp_name_list: List[str] = [gt(i.cn, 'ocr') for i in to_check_sp_list]

        idx = str_utils.find_best_match_by_difflib(ocr_word, to_check_sp_name_list)
        if idx is None:
            return None
        else:
            return to_check_sp_list[idx]

    def best_match_sp_by_all_name(self, planet_name: str, region_name: str, sp_name: str, region_floor: int = 0) -> Optional[
        SpecialPoint]:
        """
        根据名称 匹配具体的特殊点
        :param planet_name: 星球名称
        :param region_name: 区域名称
        :param sp_name: 特殊点名称
        :param region_floor: 区域楼层
        :return:
        """
        planet = self.best_match_planet_by_name(planet_name)
        region = self.best_match_region_by_name(region_name, planet, region_floor)
        return self.best_match_sp_by_name(region, sp_name)

    def get_sp_type_in_rect(self, region: Region, rect: Rect) -> dict:
        """
        获取区域特定矩形内的特殊点 按种类分组
        :param region: 区域
        :param rect: 矩形 为空时返回全部
        :return: 特殊点
        """
        sp_list = self.region_2_sp.get(region.pr_id)
        sp_map = {}
        if sp_list is None or len(sp_list) == 0:
            return sp_map
        for sp in sp_list:
            if rect is None or cal_utils.in_rect(sp.lm_pos, rect):
                if sp.template_id not in sp_map:
                    sp_map[sp.template_id] = []
                sp_map[sp.template_id].append(sp)

        return sp_map

    def get_region_list_by_planet(self, planet: Planet) -> List[Region]:
        """
        获取星球下的所有区域
        :param planet: 星球
        :return:
        """
        return self.planet_2_region.get(planet.np_id, [])

    def load_large_map_info(self, region: Region) -> LargeMapInfo:
        """
        加载某张大地图到内存中
        :param region: 对应区域
        :return: 地图图片
        """
        dir_path = SrMapData.get_large_map_dir_path(region)
        info = LargeMapInfo()
        info.region = region
        info.raw = cv2_utils.read_image(os.path.join(dir_path, 'raw.webp'))
        info.mask = cv2_utils.read_image(os.path.join(dir_path, 'mask.png'))
        self.large_map_info_map[region.prl_id] = info
        return info

    def get_large_map_info(self, region: Region) -> LargeMapInfo:
        """
        获取某张大地图
        :param region: 区域
        :return: 地图图片
        """
        if region.prl_id not in self.large_map_info_map:
            # 尝试加载一次
            return self.load_large_map_info(region)
        else:
            return self.large_map_info_map[region.prl_id]

    @staticmethod
    def get_large_map_dir_path(region: Region):
        """
        获取某个区域的地图文件夹路径
        :param region:
        :return:
        """
        return os.path.join(os_utils.get_path_under_work_dir('assets', 'template', 'large_map',
                                                             region.planet.np_id, region.rl_id))

    @staticmethod
    def get_map_path(region: Region, mt: str = 'raw', suffix: str = 'png') -> str:
        """
        获取某张地图路径
        Args:
            region: 对应区域
            mt: 地图类型 raw/mask
            suffix: 后缀/文件类型

        Returns:
            str: 图片路径
        """
        return os.path.join(SrMapData.get_large_map_dir_path(region), f'{mt}.{suffix}')

    @staticmethod
    def save_large_map_image(image: MatLike, region: Region, mt: str = 'raw'):
        """
        保存某张地图
        :param image: 图片
        :param region: 区域
        :param mt: 地图类型
        :return:
        """
        path = SrMapData.get_map_path(region, mt)
        cv2_utils.save_image(image, path)

    @staticmethod
    def get_large_map_image(region: Region, mt: str = 'raw') -> MatLike:
        """
        保存某张地图
        :param region: 区域
        :param mt: 地图类型
        :return:
        """
        path = SrMapData.get_map_path(region, mt)
        return cv2_utils.read_image(path)


if __name__ == '__main__':
    _data = SrMapData()
    print(len(_data.planet_list))
    print(len(_data.region_list))
    print(len(_data.sp_list))

