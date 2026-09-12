import time

from cv2.typing import MatLike
from enum import Enum
from typing import List

from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from one_dragon.utils import cv2_utils
from sr_od.context.sr_context import SrContext


class ScreenState(Enum):

    NORMAL_IN_WORLD = '大世界'
    EXPRESS_SUPPLY = '列车补给'


def is_normal_in_world(ctx: SrContext, screen: MatLike) -> bool:
    """
    是否在普通大世界主界面 - 右上角是否有角色的图标
    约3ms
    :param ctx: 上下文
    :param screen: 游戏画面
    :return:
    """
    return screen_utils.find_area(ctx, screen, '大世界', '角色图标') == FindAreaResultEnum.TRUE


def is_mission_in_world(ctx: SrContext, screen: MatLike) -> bool:
    """
    是否在副本的大世界画面 看左上角是否退出按钮
    可以用于
    - 逐光捡金
    - 模拟宇宙
    :param ctx: 上下文
    :param screen: 游戏画面
    :return:
    """
    return screen_utils.find_area(ctx, screen, '模拟宇宙', '大世界返回按钮') == FindAreaResultEnum.TRUE


def is_express_supply(ctx: SrContext, screen: MatLike) -> bool:
    """
    是否在列车补给画面
    :param ctx: 上下文
    :param screen: 游戏画面
    :return:
    """
    return (screen_utils.find_area(ctx, screen, '列车补给', '列车补给1') == FindAreaResultEnum.TRUE
            or screen_utils.find_area(ctx, screen, '列车补给', '列车补给2') == FindAreaResultEnum.TRUE)


def get_ui_titles(ctx: SrContext, screen: MatLike,
                  screen_name: str = '', area_name: str = '') -> List[str]:
    """
    获取页面左上方标题文字 可能有两个
    例如 模拟宇宙 选择祝福
    :param ctx: 上下文
    :param screen: 游戏画面
    :param screen_name: 需要识别的画面名称
    :param area_name: 需要识别的区域名称
    :return:
    """
    area = ctx.screen_loader.get_area(screen_name, area_name)
    part = cv2_utils.crop_image_only(screen, area.rect)
    # cv2_utils.show_image(part, wait=0)
    ocr_result_map = ctx.ocr.run_ocr(part)
    return list(ocr_result_map.keys())


def in_secondary_ui(ctx: SrContext, screen: MatLike,
                    title_cn: str, lcs_percent: float = 0.3,
                    screen_name: str = '通用画面', area_name: str = '左上角标题') -> bool:
    """
    根据页面左上方标题文字 判断在哪个二级页面中
    :param ctx: 上下文
    :param screen: 游戏画面
    :param title_cn: 中文标题
    :param lcs_percent: LCS阈值
    :param screen_name: 画面名称
    :param area_name: 识别区域
    :return:
    """
    area = ctx.screen_loader.get_area(screen_name, area_name)
    part, _ = cv2_utils.crop_image(screen, area.rect)
    # cv2_utils.show_image(part, wait=0)
    ocr_map = ctx.ocr.match_words(part, words=[title_cn],
                                  lcs_percent=lcs_percent, merge_line_distance=10)

    return len(ocr_map) > 0


def click_empty_to_close(ctx: SrContext) -> bool:
    area = ctx.screen_loader.get_area('大世界', '点击空白处关闭')
    return ctx.controller.click(area.center)

def claim_express_supply(ctx: SrContext):
    """
    领取列车补给
    :param ctx:
    :return:
    """
    area = ctx.screen_loader.get_area('列车补给', '点击领取今日补给')
    ctx.controller.click(area.center)
    time.sleep(3)  # 暂停一段时间再操作
    ctx.controller.click(area.center)  # 领取需要分两个阶段 点击两次
    time.sleep(1)  # 暂停一段时间再操作
