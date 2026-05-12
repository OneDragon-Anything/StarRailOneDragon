import os

from cv2.typing import MatLike

from one_dragon.base.matcher.match_result import MatchResultList
from one_dragon.utils import os_utils, cv2_utils
from one_dragon.utils.log_utils import log
from sr_od.application.large_map_recorder import large_map_recorder_utils
from sr_od.sr_map import mini_map_utils
from sr_od.sr_map.mys import mys_map_request_utils
from sr_od.sr_map.sr_map_def import Region


def _get_mys_image(region: Region, resize: int = 120) -> MatLike:
    """
    获取米游社的地图图片
    Args:
        region: 区域
        resize: 缩放比例

    Returns:
        map_image: 地图图片
    """
    # 先看是否已经有缓存图片
    save_dir = os_utils.get_path_under_work_dir('.debug', 'mys', 'map', region.planet.np_id)
    save_image_name = f'{region.prl_id}_{resize}.png'
    save_image_path = os.path.join(save_dir, save_image_name)
    if os.path.exists(save_image_path):
        return cv2_utils.read_image(save_image_path)

    # 下载米游社图片
    floor_2_map = mys_map_request_utils.download_map_image(
        planet_name=region.planet.cn,
        region_name=region.cn,
        resize=resize,
    )

    cv2_utils.save_image(floor_2_map[region.floor], save_image_path)

    return floor_2_map[region.floor]


def get_best_mys_image_resize_for_all(
        region_list: list[Region],
        max_row: int,
        max_col: int,
) -> int:
    """
    找到米游社图片最合适的缩放比例

    Args:
        region_list: 区域列表
        max_row: 最大行数
        max_col: 最大列数

    Returns:

    """
    max_road_pixels = 0
    best_region: Region | None = None
    best_pos = (1, 1)

    for region in region_list:
        for row in range(1, max_row + 1):
            for col in range(1, max_col + 1):
                try:
                    part_image = large_map_recorder_utils.get_part_image(region, row, col)
                    if part_image is None:
                        continue

                    # 计算道路像素数量
                    road_mask, _ = mini_map_utils.get_road_mask(part_image)
                    road_pixels = road_mask.sum()

                    if road_pixels > max_road_pixels:
                        best_region = region
                        max_road_pixels = road_pixels
                        best_pos = (row, col)

                except Exception as e:
                    log.warning(f"读取碎片图片失败: {row}, {col}, {e}")
                    continue

    log.info(f'找到最多道路像素的碎片: {best_region.prl_id}, {best_pos} 道路像素数: {max_road_pixels}')

    part_image = large_map_recorder_utils.get_part_image(best_region, best_pos[0], best_pos[1])
    return get_best_mys_image_resize_for_floor(best_region, part_image)[1]


def get_best_mys_image_resize_for_floor(
        region: Region,
        part: MatLike,
) -> tuple[MatLike, int]:
    """
    找到最合适缩放比例的大地图

    Args:
        region: 区域
        part: 地图碎片

    Returns:
        MatLike: 最合适缩放比例的地图图片
        int: 缩放比例
    """
    best_whole: MatLike = None
    best_score: float = 0
    best_resize: int = 0
    best_mrl: MatchResultList | None = None
    # cv2_utils.show_image(part, wait=0)
    for resize in range(80, 91):
        log.info(f'[{region.prl_id}] 尝试缩放比例：{resize}')
        whole = _get_mys_image(region, resize=resize)
        road_mask, _ = mini_map_utils.get_road_mask(part)
        # cv2_utils.show_image(whole, max_width=1920, wait=0)
        mrl = cv2_utils.match_template(whole, part, mask=road_mask,
                                       threshold=0.3, ignore_inf=True)
        score = mrl.max.confidence if mrl.max is not None else 0
        log.info(f'[{region.prl_id}] 缩放比例: {resize} 匹配分数: {score:0.3f}')
        if score > best_score:
            best_score = score
            best_whole = whole
            best_resize = resize
            best_mrl = mrl
        # if score > 0:
        #     cv2_utils.show_image(best_whole, rects=mrl, max_width=3840, wait=0)
    log.info(f'[{region.prl_id}] 最佳缩放比例：{best_resize}')
    cv2_utils.show_overlap(best_whole, part, best_mrl.max.x, best_mrl.max.y, template_scale=best_mrl.max.template_scale, wait=0)
    # cv2_utils.show_image(best_whole, rects=best_mrl, max_width=3840, wait=0)
    return best_whole, best_resize
