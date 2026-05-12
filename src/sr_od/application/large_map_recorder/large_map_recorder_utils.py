import os
from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future

import cv2
import numpy as np
import yaml
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResultList
from one_dragon.base.screen.template_info import TemplateInfo
from one_dragon.utils import os_utils, cv2_utils
from one_dragon.utils.log_utils import log
from sr_od.config import game_const
from sr_od.config.game_config import MiniMapPos
from sr_od.context.sr_context import SrContext
from sr_od.sr_map import large_map_utils
from sr_od.sr_map.sr_map_def import Region, SpecialPoint


def get_part_image_path(region: Region, row: int, col: int) -> str:
    """
    地图格子的图片路径
    """
    return os.path.join(
        os_utils.get_path_under_work_dir('.debug', 'world_patrol', region.pr_id, 'part'),
        f'{region.pr_id}_part_{region.l_str}_{row:02d}_{col:02d}.png'
    )


def get_part_image(region: Region, row: int, col: int) -> MatLike:
    """
    地图格子的图片
    """
    return cv2_utils.read_image(get_part_image_path(region, row, col))


def save_part_image(region: Region, row: int, col: int, image: MatLike) -> None:
    """
    地图格子的图片
    """
    path = get_part_image_path(region, row, col)
    cv2_utils.save_image(image, path)


def get_floor_image_path(region: Region) -> str:
    """
    地图格子的图片路径
    """
    return os.path.join(
        os_utils.get_path_under_work_dir('.debug', 'world_patrol', region.pr_id, 'floor'),
        f'{region.pr_id}_merge_{region.l_str}.png'
    )

def get_floor_image(region: Region) -> MatLike:
    """
    获取某个楼层的大地图

    Args:
        region: 区域

    Returns:
        MatLike: 大地图图片
    """
    return cv2_utils.read_image(get_floor_image_path(region))


def save_floor_image(region: Region, image: MatLike) -> None:
    """
    地图格子的图片
    """
    path = get_floor_image_path(region)
    cv2_utils.save_image(image, path)



class RegionMergeCheckpoint:

    def __init__(self):
        self.final_width: int = 0  # 最终的宽度
        self.final_height: int = 0  # 最终的高度
        self.part_positions: dict[tuple[int, int], tuple[int, int]] = {}  # 记录每个part_image在final_image中的位置
        self.done_part: set[tuple[int, int]] = set()  # 已经处理的part_image

def merge_parts_into_one(
        region: Region,
        max_row: int,
        max_col: int,
) -> MatLike:
    """
    将所有碎片地图合并成一个完整的大地图
    1. 找出地图掩码最大的一个碎片
    2. 从这个碎片开始，使用bfs，不断拓展四个方向的碎片，进行模板匹配找到两个碎片之间的重叠宽度或者高度，然后把新碎片拼接到上一个碎片的相邻位置
    3. 合并过程中，动态扩展图像大小，空白区域使用 rgb=(205, 205, 205) 填充
    4. 最终返回合并后的大地图

    Args:
        region: 当前合并的区域
        max_row: 碎片图片的最大行数 从1开始到max_row
        max_col: 碎片图片的最大列数 从1开始到max_col

    Returns:
        合并后的大地图图像

    """
    log.info(f'[{region.prl_id}] 开始合并碎片地图，行数: {max_row}, 列数: {max_col}')

    ck = _load_merge_checkpoint(region)

    if ck is None:
        ck = RegionMergeCheckpoint()

        # 找出地图掩码最大的一个碎片作为起始点
        start_pos = _get_most_road_pos(region, max_row, max_col)
        final_image = get_part_image(region, start_pos[0], start_pos[1]).copy()

        ck.final_width = final_image.shape[1]
        ck.final_height = final_image.shape[0]
        ck.part_positions[start_pos] = (0, 0)
        ck.done_part.add(start_pos)
    else:
        final_image = np.full((ck.final_height, ck.final_width, 3), 205, dtype=np.uint8)
        for part, pos in ck.part_positions.items():
            part_image = get_part_image(region, part[0], part[1])
            final_image[pos[1]:pos[1] + part_image.shape[0], pos[0]:pos[0] + part_image.shape[1]] = part_image

    bfs_list: deque[tuple[int, int]] = deque()  # bfs搜索列表
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # 方向: 上、下、左、右

    for part in ck.part_positions.keys():
        bfs_list.append(part)

    # 使用bfs方法拼接碎片
    while len(bfs_list) > 0:
        current_pos: tuple[int, int] = bfs_list.popleft()
        current_part: MatLike = get_part_image(region, current_pos[0], current_pos[1])
        for direction in directions:
            next_pos = (current_pos[0] + direction[0], current_pos[1] + direction[1])
            if next_pos in ck.done_part:  # 已经拼接过了
                continue

            next_part: MatLike = get_part_image(region, next_pos[0], next_pos[1])
            if next_part is None:  # 没有这个碎片
                continue

            if is_empty_part(next_part):  # 忽略一些大部分空白的块
                log.info(f"忽略空白块 {next_pos}")
                ck.done_part.add(next_pos)
                _save_merge_checkpoint(region, ck)
                continue

            log.info(f"正在计算 {current_pos} 和 {next_pos} 的位置")
            next_dx, next_dy = _cal_part_position(current_part, next_part, direction)
            if next_dx is None or next_dy is None:
                log.info(f"计算偏移量失败 {current_pos} -> {next_pos}")
                continue
            log.info(f"计算偏移量完成 {current_pos} -> {next_pos} : {next_dx, next_dy}")

            next_dx += ck.part_positions[current_pos][0]
            next_dy += ck.part_positions[current_pos][1]

            # 合并图片
            final_image = _merge_part_into_whole(final_image, next_part, next_dx, next_dy)
            ck.final_width = final_image.shape[1]
            ck.final_height = final_image.shape[0]
            cv2_utils.show_image(final_image, max_width=3820, max_height=2160, win_name='final_image', wait=1)

            # 修正各碎片在原图上的偏移量
            ck.part_positions[next_pos] = (next_dx, next_dy)
            if next_dx < 0:
                for part_pos, part_dxy in ck.part_positions.items():
                    ck.part_positions[part_pos] = (part_dxy[0] - next_dx, part_dxy[1])
            if next_dy < 0:
                for part_pos, part_dxy in ck.part_positions.items():
                    ck.part_positions[part_pos] = (part_dxy[0], part_dxy[1] - next_dy)

            bfs_list.append(next_pos)
            ck.done_part.add(next_pos)
            _save_merge_checkpoint(region, ck)

    return final_image


def _get_most_road_pos(
        region: Region,
        max_row: int,
        max_col: int,
) -> tuple[int, int]:
    """
    找到道路最多的那个碎片

    Args:
        region: 当前合并的区域
        max_row: 碎片图片的最大行数 从1开始到max_row
        max_col: 碎片图片的最大列数 从1开始到max_col

    Returns:
        道路最多的碎片的位置
    """
    max_road_pixels = 0
    start_pos = (1, 1)
    for row in range(1, max_row + 1):
        for col in range(1, max_col + 1):
            try:
                part_image = get_part_image(region, row, col)
                if part_image is None:
                    continue

                # 计算道路像素数量
                road_mask = _get_road_mask(part_image)
                road_pixels = road_mask.sum()

                if road_pixels > max_road_pixels:
                    max_road_pixels = road_pixels
                    start_pos = (row, col)

            except Exception as e:
                log.warning(f"读取碎片图片失败: {row}, {col}, {e}")
                continue

    log.info(f'找到最佳起始碎片: {start_pos}, 道路像素数: {max_road_pixels}')
    return start_pos


def _cal_part_position(
        current_part: MatLike,
        next_part: MatLike,
        direction: tuple[int, int],
) -> tuple[int | None, int | None]:
    """
    计算两个碎片的重叠区域 返回下一个碎片在当前碎片的相对位置

    Args:
        current_part: 当前碎片的图像
        next_part: 下一个碎片的图像
        direction: 方向

    Returns:
        下一个碎片在当前碎片的相对位置
    """
    if direction[1] == 0:
        return _cal_part_position_in_vertical(current_part, next_part, direction)
    else:
        return _cal_part_position_in_horizontal(current_part, next_part, direction)


def _cal_part_position_in_vertical(
        current_part: MatLike,
        next_part: MatLike,
        direction: tuple[int, int],
) -> tuple[int | None, int | None]:
    """
    计算两个碎片在垂直方向上的重叠区域 返回下一个碎片在当前碎片的相对位置

    Args:
        current_part: 当前碎片的图像
        next_part: 下一个碎片的图像
        direction: 方向

    Returns:
        下一个碎片在当前碎片的相对位置
    """
    if direction[0] == -1:
        up_part = next_part
        down_part = current_part
    else:
        up_part = current_part
        down_part = next_part

    # 设置搜索参数
    cut_x_min: int = 1
    cut_x_max: int = 15
    cut_y_min: int = 300
    cut_y_max: int = 400

    down_dx: int | None = None
    down_dy: int | None = None

    for cut_y in range(cut_y_min, cut_y_max, 10):
        for cut_x in range(cut_x_min, cut_x_max, 1):
            # 上方碎片 裁剪偏下方的部分 以及去掉两边部分宽度 和下方碎片进行匹配
            source = down_part
            template = up_part[cut_y:, cut_x:-cut_x]
            template_mask = _get_non_background_mask(template)
            mrl = cv2_utils.match_template(source, template, mask=template_mask, threshold=0.9, ignore_inf=True)
            if mrl.max is not None:
                # cv2_utils.show_overlap(source, template, mrl.max.x, mrl.max.y, wait=0)
                down_dx = cut_x - mrl.max.x
                down_dy = cut_y - mrl.max.y
                break

            # 下方碎片 裁剪偏上方的部分 以及去掉两边部分宽度 和上方碎片进行匹配
            source = up_part
            template = down_part[:-cut_y, cut_x:-cut_x]
            template_mask = _get_non_background_mask(template)
            mrl = cv2_utils.match_template(source, template, mask=template_mask, threshold=0.9, ignore_inf=True)
            if mrl.max is not None:
                # cv2_utils.show_overlap(source, template, mrl.max.x, mrl.max.y, wait=0)
                down_dx = mrl.max.x - cut_x
                down_dy = mrl.max.y
                break

        if down_dx is not None or down_dy is not None:
            break

    if down_dx is None or down_dy is None:
        return None, None

    # cv2_utils.show_overlap(up_part, down_part, x=down_dx, y=down_dy, wait=0)

    if direction[0] == -1:
        return -down_dx, -down_dy
    else:
        return down_dx, down_dy


def _cal_part_position_in_horizontal(
        current_part: MatLike,
        next_part: MatLike,
        direction: tuple[int, int],
) -> tuple[int | None, int | None]:
    """
    计算两个碎片在水平方向上的重叠区域 返回下一个碎片在当前碎片的相对位置

    Args:
        current_part: 当前碎片的图像
        next_part: 下一个碎片的图像
        direction: 方向

    Returns:
        下一个碎片在当前碎片的相对位置
    """
    if direction[1] == -1:
        left_part = next_part
        right_part = current_part
    else:
        left_part = current_part
        right_part = next_part

    # 设置搜索参数
    cut_x_min: int = 300
    cut_x_max: int = 400
    cut_y_min: int = 1
    cut_y_max: int = 15

    right_dx: int | None = None
    right_dy: int | None = None

    for cut_x in range(cut_x_min, cut_x_max, 10):
        for cut_y in range(cut_y_min, cut_y_max, 1):
            # 左方碎片 使用偏右方的部分 以及去掉上下两边部分高度 和右方碎片进行匹配
            source = right_part
            template = left_part[cut_y:-cut_y, cut_x:]
            template_mask = _get_non_background_mask(template)
            mrl = cv2_utils.match_template(source, template, mask=template_mask, threshold=0.9, ignore_inf=True)
            if mrl.max is not None:
                # cv2_utils.show_overlap(source, template, mrl.max.x, mrl.max.y, wait=0)
                right_dx = cut_x - mrl.max.x
                right_dy = cut_y - mrl.max.y
                break

            # 右方碎片 使用偏左方的部分 以及去掉上下两边部分高度 和左方碎片进行匹配
            source = left_part
            template = right_part[cut_y:-cut_y, :-cut_x]
            template_mask = _get_non_background_mask(template)
            mrl = cv2_utils.match_template(source, template, mask=template_mask, threshold=0.9, ignore_inf=True)
            if mrl.max is not None:
                # cv2_utils.show_overlap(source, template, mrl.max.x, mrl.max.y, wait=0)
                right_dx = mrl.max.x
                right_dy = mrl.max.y - cut_y
                break

        if right_dx is not None or right_dy is not None:
            break

    if right_dx is None or right_dy is None:
        return None, None

    # cv2_utils.show_overlap(left_part, right_part, x=right_dx, y=right_dy, wait=0)

    if direction[1] == -1:
        return -right_dx, -right_dy
    else:
        return right_dx, right_dy


def _get_non_background_mask(
        map_image: MatLike,
) -> MatLike:
    """
    获取非背景部分的掩码
    """
    bg_mask = _get_background_mask(map_image)
    return 255 - bg_mask


def _get_background_mask(
        map_image: MatLike,
) -> MatLike:
    """
    获取背景部分的掩码
    Args:
        map_image: 地图图片

    Returns:
        背景掩码图
    """
    return cv2_utils.color_in_hsv_range(map_image, [0, 0, 79], [0, 0, 90])


def _get_road_mask(map_image: MatLike) -> MatLike:
    """
    获取大地图的道路部分的掩码
    Args:
        map_image: 地图图片

    Returns:
        道路掩码图
    """
    return cv2_utils.color_in_hsv_range(map_image, [0, 0, 20], [0, 0, 55])


def _merge_part_into_whole(
        whole_image: MatLike,
        part_image: MatLike,
        part_dx: int,
        part_dy: int,
) -> MatLike:
    """
    将碎片添加到完整的图像中

    Args:
        whole_image: 完整的图像
        part_image: 要添加的碎片
        part_dx: 碎片在完整图像上的偏移量
        part_dy: 碎片在完整图像上的偏移量

    Returns:
        添加碎片后的完整图像
    """
    # 计算合并后图片的代销
    min_x = min(part_dx, 0)
    max_x = max(part_dx + part_image.shape[1], whole_image.shape[1])
    min_y = min(part_dy, 0)
    max_y = max(part_dy + part_image.shape[0], whole_image.shape[0])
    new_width = max_x - min_x
    new_height = max_y - min_y

    # 计算两个图片在合并后大图的偏移量
    whole_dx: int = 0
    whole_dy: int = 0
    if part_dx < 0:
        whole_dx = -part_dx
        part_dx = 0
    if part_dy < 0:
        whole_dy = -part_dy
        part_dy = 0

    # 创建一个大图
    # cv2_utils.show_image(whole_image, max_width=3820, max_height=2160, win_name='whole_image', wait=0)
    # cv2_utils.show_image(part_image, max_width=3820, max_height=2160, win_name='part_image', wait=0)
    new_image = np.full((new_height, new_width, 3), 205, dtype=np.uint8)
    new_image[whole_dy:whole_dy + whole_image.shape[0], whole_dx:whole_dx + whole_image.shape[1]] = whole_image
    new_image[part_dy:part_dy + part_image.shape[0], part_dx:part_dx + part_image.shape[1]] = part_image

    return new_image


def is_empty_part(map_image: MatLike) -> bool:
    """
    判断当前地图图片是否空白
    Args:
        map_image: 地图图片

    Returns:
        bool: 是否空白
    """
    road_mask = _get_road_mask(map_image)
    # cv2_utils.show_image(road_mask, win_name="road_mask", wait=0)
    road_cnt: int = np.count_nonzero(road_mask)
    if road_cnt >= 10:
        return False

    bg_mask = _get_background_mask(map_image)
    # cv2_utils.show_image(bg_mask, win_name="bg_mask", wait=0)
    total_cnt: int = road_mask.shape[0] * road_mask.shape[1]
    bg_cnt: int = np.count_nonzero(bg_mask)
    return bg_cnt > total_cnt * 0.9


def _load_merge_checkpoint(region: Region) ->  RegionMergeCheckpoint | None:
    """
    加载合并检查点

    Args:
        region: 区域

    Returns:
        合并检查点
    """

    merge_checkpoint_path = _get_region_checkpoint_path(region)
    if not os.path.exists(merge_checkpoint_path):
        return None

    with open(merge_checkpoint_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

        checkpoint = RegionMergeCheckpoint()
        checkpoint.final_width = data['final_width']
        checkpoint.final_height = data['final_height']
        for i in data.get('done_part', []):
            checkpoint.done_part.add((i[0], i[1]))

        for i in data.get('part_positions', []):
            checkpoint.part_positions[(i[0], i[1])] = (i[2], i[3])

        return checkpoint


def _save_merge_checkpoint(region: Region, checkpoint: RegionMergeCheckpoint) -> None:
    """
    保存合并的进度

    Args:
        region: 区域
        checkpoint: 检查点数据

    Returns:
        None
    """
    file_path = _get_region_checkpoint_path(region)

    data = {
        'final_width': checkpoint.final_width,
        'final_height': checkpoint.final_height,
        'done_part': [
            [i[0], i[1]]
            for i in checkpoint.done_part
        ],
        'part_positions': [
            [i[0], i[1], j[0], j[1]]
            for i, j in checkpoint.part_positions.items()
        ]
    }

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
    log.info(f'保存合并检查点成功')


def _get_region_checkpoint_path(region: Region) -> str:
    """
    获取区域的合并检查点文件路径
    Args:
        region: 区域

    Returns:
        合并检查点文件路径
    """
    return os.path.join(
        os_utils.get_path_under_work_dir('.debug', 'world_patrol', region.pr_id, 'merge_checkpoint'),
        f'{region.prl_id}.yml'
    )


def expand_large_map(
        region: Region,
        mm_pos: MiniMapPos,
) -> None:
    """
    对大地图的四周进行拓展 以适应下述情况

    1. 使用小地图匹配坐标时，使用的是模板匹配，因此大地图上最边缘的道路需要和地图边缘保留至少半个小地图的距离
    2. 在传送找传送点时，需要使用游戏中大地图局部画面和完整大地图进行模板匹配，如果局部画面和完整画面大小一致，则可能会报错，因此需要拓展一点点距离

    Args:
        region: 区域
        mm_pos: 小地图位置

    Returns:
        None
    """
    log.info(f'开始对大地图四周进行拓展 {region.display_name}')
    large_map = get_floor_image(region)
    expand_arr = get_expand_arr(large_map, mm_pos, large_map_utils.get_screen_map_rect(region))

    lp = expand_arr[0]
    rp = expand_arr[1]
    tp = expand_arr[2]
    bp = expand_arr[3]
    if lp == 0 and rp == 0 and tp == 0 and bp == 0:
        log.info(f'大地图无需进行拓展')
        return

    log.info(f'大地图开始进行拓展 lp:{lp} rp:{rp} tp:{tp} bp:{bp}')
    expand_map = np.full(
        (large_map.shape[0] + tp + bp, large_map.shape[1] + lp + rp, large_map.shape[2]),
        fill_value=205, dtype=np.uint8,
    )
    expand_map[tp:tp+large_map.shape[0], lp:lp+large_map.shape[1]] = large_map
    save_floor_image(region, expand_map)
    log.info(f'大地图拓展更新完成')


def get_expand_arr(raw: MatLike, mm_pos: MiniMapPos, screen_map_rect: Rect) -> tuple[int, int, int, int]:
    """
    如果道路太贴近大地图边缘 使用小地图模板匹配的时候会匹配失败
    如果最后截图高度或宽度跟大地图圈定范围CUT_MAP_RECT一致 则choose_transport_point中两个大地图做模板匹配可能会报错
    这些情况需要拓展一下大地图
    :param raw: 大地图原图
    :param mm_pos: 小地图位置
    :param screen_map_rect: 屏幕上大地图的区域
    :return: 各个方向需要扩展的大小
    """
    # 道路掩码图
    mask: MatLike = _get_road_mask(raw)

    padding = mm_pos.r + 10  # 边缘至少留一个小地图半径的空白

    # 四个方向需要拓展多少像素
    left, right, top, bottom = cv2_utils.get_four_corner(mask)
    lp = 0 if left[0] >= padding else padding - left[0]
    rp = 0 if right[0] + padding < raw.shape[1] else right[0] + padding + 1 - raw.shape[1]
    tp = 0 if top[1] >= padding else padding - top[1]
    bp = 0 if bottom[1] + padding < raw.shape[0] else bottom[1] + padding + 1 - raw.shape[0]

    # raw 尺寸至少跟CUT_MAP_RECT一致 所以只有上面没有拓展的情况要
    if tp == 0 and bp == 0 and raw.shape[0] == screen_map_rect.y2 - screen_map_rect.y1:
        tp = 5
        bp = 5
    if lp == 0 and rp == 0 and raw.shape[1] == screen_map_rect.x2 - screen_map_rect.x1:
        lp = 5
        rp = 5

    return lp, rp, tp, bp


def adjust_to_sames_size(r1: Region, r2: Region) -> bool:
    """
    调整两个大地图的大小至相同

    Args:
        r1: 区域1
        r2: 区域2

    Returns:
        bool: 是否进行了调整
    """
    log.info(f'开始调楼层地图的大小: {r1.l_str} {r2.l_str}')
    f1 = get_floor_image(r1)
    f2 = get_floor_image(r2)

    if f1.shape == f2.shape:
        log.info(f'大小相同 无需调整: {r1.l_str} {r2.l_str}')
        return False

    can_math: bool = False

    d1x: int = 0
    d1y: int = 0

    d2x: int = 0
    d2y: int = 0

    for cut in range(50, 500, 10):
        if cut * 2 >= min(f2.shape[0], f2.shape[1]):
            break
        source = f1
        template = f2[cut:-cut, cut:-cut]

        if template.shape[0] > source.shape[0] or template.shape[1] > source.shape[1]:
            continue

        mrl = cv2_utils.match_template(source, template, threshold=0.5, ignore_inf=True)
        if mrl.max is None:
            continue

        can_math = True
        d2x = mrl.max.x - cut
        d2y = mrl.max.y - cut

        break

    if not can_math:
        raise Exception('楼层地图无法匹配')

    if d2x < 0:
        d1x -= d2x
        d2x = 0
    if d2y < 0:
        d1y -= d2y
        d2y = 0

    final_height: int = max(d1y + f1.shape[0], d2y + f2.shape[0])
    final_width: int = max(d1x + f1.shape[1], d2x + f2.shape[1])

    adjust_f1 = np.full((final_height, final_width, 3), 205, dtype=np.uint8)
    adjust_f1[d1y:d1y + f1.shape[0], d1x:d1x + f1.shape[1], :] = f1

    adjust_f2 = np.full((final_height, final_width, 3), 205, dtype=np.uint8)
    adjust_f2[d2y:d2y + f2.shape[0], d2x:d2x + f2.shape[1], :] = f2

    # cv2_utils.show_image(adjust_f1, max_width=3840, max_height=2160, win_name='adjust_f1', wait=0)
    # cv2_utils.show_image(adjust_f2, max_width=3840, max_height=2160, win_name='adjust_f2', wait=0)
    save_floor_image(r1, adjust_f1)
    save_floor_image(r2, adjust_f2)

    return True


def save_region(ctx: SrContext, region: Region) -> None:
    """
    最终保存一个区域的最终使用大地图信息

    Args:
        ctx: 上下文
        region: 区域

    Returns:
        None
    """
    log.info(f'开始保存区域 {region.display_name}')
    large_map = get_floor_image(region)

    sp_list = get_sp_list_in_map(ctx, region)
    ctx.map_data.save_special_point_data(region, sp_list, overwrite=False)
    sp_mask = np.zeros(large_map.shape[:2], dtype=np.uint8)
    for sp in sp_list:
        ti: TemplateInfo = ctx.template_loader.get_template('mm_icon', sp.template_id)
        if ti is None:
            break
        template_mask = ti.mask

        x1 = sp.lm_pos.x - template_mask.shape[1] // 2
        x2 = x1 + template_mask.shape[1]
        y1 = sp.lm_pos.y - template_mask.shape[0] // 2
        y2 = y1 + template_mask.shape[0]
        sp_mask[y1:y2, x1:x2] = cv2.bitwise_or(sp_mask[y1:y2, x1:x2], template_mask)

    road_mask = _get_road_mask(large_map)

    # 特殊点掩码稍微膨胀一下 填充中间的以下间隙
    sp_mask = cv2_utils.dilate(sp_mask, 5)
    # 合并
    mask = cv2.bitwise_or(road_mask, sp_mask)

    # 保存
    ctx.map_data.save_large_map_image(large_map, region, 'raw')
    ctx.map_data.save_large_map_image(mask, region, 'mask')


def get_sp_list_in_map(ctx: SrContext, region: Region) -> list[SpecialPoint]:
    """
    在大地图上，匹配出所有的特殊点，使用模板匹配

    Args:
        ctx: 上下文
        region: 区域

    Returns:
        list[SpecialPoint]: 特殊点列表
    """
    log.info('开始并发匹配特殊点')
    executor = ThreadPoolExecutor(thread_name_prefix='large_map_recorder', max_workers=os.cpu_count())
    large_map = get_floor_image(region)
    future_list: list[tuple[str, Future]] = []

    for prefix in ['mm_tp', 'mm_sp', 'mm_boss', 'mm_sub']:
        for i in range(100):
            if i == 0:
                continue
            template_id = '%s_%02d' % (prefix, i)
            ti: TemplateInfo = ctx.template_loader.get_template('mm_icon', template_id)
            if ti is None:
                break
            template = ti.raw
            template_mask = ti.mask

            future_list.append(
                (
                    template_id,
                    executor.submit(
                        cv2_utils.match_template,
                        large_map,
                        template,
                        game_const.THRESHOLD_SP_TEMPLATE_IN_LARGE_MAP,
                        template_mask,
                        False,  # only_best
                        True,  # ignore_inf
                    )
                )
            )

    sp_list: list[SpecialPoint] = []
    for template_id, future in future_list:
        mrl: MatchResultList = future.result(100)
        if mrl.max is None:
            log.info(f'特殊点 {template_id} 未找到')
            continue

        log.info(f'特殊点 {template_id} 匹配到 {len(mrl)}个')
        for mr in mrl:
            sp = SpecialPoint(
                uid='',
                cn='',
                region=region,
                template_id=template_id,
                lm_pos=(mr.center.x, mr.center.y),
            )
            sp_list.append(sp)

    return sp_list


def _debug_is_empty_part():
    from one_dragon.utils import debug_utils
    from sr_od.sr_map import large_map_utils
    screen = debug_utils.get_debug_image('_1751767159001')
    map_part = large_map_utils.get_screen_map_part(screen)
    print(is_empty_part(map_part))

    screen = debug_utils.get_debug_image('_1751721851008')
    map_part = large_map_utils.get_screen_map_part(screen)
    print(is_empty_part(map_part))


if __name__ == '__main__':
    _debug_is_empty_part()