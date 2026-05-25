import cv2

from one_dragon.utils import debug_utils, cv2_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.move import cal_pos_utils
from sr_od.sr_map import mini_map_utils, large_map_utils
from sr_od.sr_map.large_map_info import LargeMapInfo
from sr_od.sr_map.sr_map_def import SpecialPoint


def cal_one(tp: SpecialPoint, debug_image: str, show: bool = False):
    image = debug_utils.get_debug_image(debug_image)
    mm = mini_map_utils.cut_mini_map(image, ctx.game_config.mini_map_pos)

    possible_pos = (*(tp.lm_pos.tuple()), 200)
    lm_info: LargeMapInfo = ctx.map_data.get_large_map_info(tp.region)
    lm_rect = large_map_utils.get_large_map_rect_by_pos(lm_info.raw.shape, mm.shape[:2], possible_pos)
    mm_info = mini_map_utils.analyse_mini_map(mm)
    result = cal_pos_utils.cal_character_pos_by_sp_result(ctx, lm_info, mm_info, lm_rect=lm_rect)
    if result is None:
        result = cal_pos_utils.cal_character_pos_by_gray(ctx, lm_info, mm_info, lm_rect=lm_rect,
                                                         scale_list=cal_pos_utils.get_mini_map_scale_list(False, is_debug=True))

    log.info('%s 传送落地坐标 tp_pos: [%d, %d] 使用缩放 %.2f', tp.display_name, result.center.x, result.center.y, result.template_scale)
    if show:
        cv2_utils.show_overlap(
            lm_info.raw, mm, result.x, result.y,
            template_scale=result.template_scale, wait=0,
            max_width=3840, max_height=2160
        )


if __name__ == '__main__':
    ctx = SrContext()
    ctx.init_by_config()

    planet_name: str = '翁法罗斯'
    region_name: str = '「永恒圣城」奥赫玛'

    planet = ctx.map_data.best_match_planet_by_name(gt(planet_name, 'game'))
    region = ctx.map_data.best_match_region_by_name(gt(region_name, 'game'), planet=planet)

    sp_name_list = [
        '三季海庭',
        '满溢主池',
        '流憩大厅',
        '云石天宫',
        '云石市集',
        '刻法勒广场',
        '离怀之路',
        '达米亚诺斯',
        '豹豹碰碰大赛场',
        '生命花园',
        '英雄浴池',
        '奇美拉管理中心',
    ]
    img_list = [
        '_1751784718441',
        '_1751784820844',
        '_1751784826909',
        '_1751784835044',
        '_1751784845893',
        '_1751784851264',
        '_1751784897779',
        '_1751785127724',
        '_1751785136540',
        '_1751785582313',
        '_1751785587046',
        '_1751785143340',
    ]
    for i in range(len(sp_name_list)):
        sp = ctx.map_data.best_match_sp_by_name(region, gt(sp_name_list[i], 'game'))
        if sp is None:
            log.error(f'找不到 {sp_name_list[i]}')
        cal_one(sp, debug_image=img_list[i], show=True)
        # cal_one(sp_list[i])
    cv2.destroyAllWindows()
