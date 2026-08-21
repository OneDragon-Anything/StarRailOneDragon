# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 OCR 观测层共享基础设施:screen_info 区域读取 + OCR helper + 常量。

各画面观测模块(``cw_briefing_obs`` 简报 / ``cw_settlement_obs`` 结算 / ``cw_observation`` 备战)
共用的 helper 与 screen_info area 名 / 坐标系常量集中于此,**避免循环导入**(本模块不依赖任何兄弟
观测模块,只依赖底层 geometry/ctx)。

**区域单一真相源 = screen_info**(用户 2026-08-03):备战 ``currency_war_battle_prep.yml``
(screen「货币战争-备战」)、简报 ``currency_war_briefing.yml``。改区域改 yml 即可,不动代码。
本模块经 ``ctx.screen_loader`` 读 area 的 pc_rect。
"""
from __future__ import annotations

import re

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from sr_od.context.sr_context import SrContext

# screen_info「货币战争-备战」(currency_war_battle_prep.yml)area 名
SCREEN_NAME: str = '货币战争-备战'
# 开商店子态画面(currency_war_battle_prep_shop_open.yml):商店牌/刷新/收起 等商店态 area 迁此
SHOP_SCREEN_NAME: str = '货币战争-备战-开商店'
A_GOLD: str = '文本-金币数'
A_PHASE: str = '区域-阶段'
A_BOARD: str = '区域-羁绊面板'
A_SHOP_REGION: str = '商店牌区'             # 5 张牌的阵营+名文本带(整体 OCR,按 y 分阵营/名;商店态,读 SHOP_SCREEN_NAME)
A_SHOP_CARD_PREFIX: str = '商店牌-'        # 商店牌-1..5(点击中心;商店态,读 SHOP_SCREEN_NAME)
# 商店牌区内行分类阈值(卡牌布局固定):y < 此 = 阵营标签;>= 此 = 角色名
SHOP_FACTION_NAME_SPLIT_Y: int = 278
COL_TOLERANCE: int = 100                   # 文本 x 分配到牌位的容差

# sanity bounds(越界 → 丢弃用默认,防误读级联:gold 读成 500 → 狂买)
GOLD_MIN, GOLD_MAX = 0, 400
HP_MIN, HP_MAX = 0, 200
LEVEL_MIN, LEVEL_MAX = 1, 10

# 简报屏(对局开始,词缀/首领读取;非备战)
BRIEFING_SCREEN: str = '货币战争-简报'


def _area_rect(ctx: SrContext, name: str, screen_name: str = SCREEN_NAME) -> Rect | None:
    """从 screen_info 取 area 的 pc_rect(Rect);screen/area 缺失 → None。

    Args:
        screen_name: 画面名(默认备战);事件态画面(投资环境/投资策略等)传其画面名。
    """
    si = ctx.screen_loader.get_screen(screen_name)
    if si is None:
        return None
    area = next((a for a in si.area_list if a.area_name == name), None)
    return area.pc_rect if (area is not None and area.pc_rect is not None) else None


def area_center(ctx: SrContext, name: str, screen_name: str = SCREEN_NAME) -> Point | None:
    """从 screen_info 取 area 中心 Point(点击用);缺失 → None。

    Args:
        screen_name: 画面名(默认备战);事件态画面(投资环境/投资策略等)传其画面名。
    """
    rect = _area_rect(ctx, name, screen_name)
    return rect.center if rect is not None else None


def shop_card_click_points(ctx: SrContext) -> list[Point]:
    """商店 5 牌位点击中心(按 商店牌-1..5 顺序,screen_info);screen 缺失 → []。

    商店牌 area 在开商店子态画面(``SHOP_SCREEN_NAME``)。
    """
    si = ctx.screen_loader.get_screen(SHOP_SCREEN_NAME)
    if si is None:
        return []
    pts: list[Point] = []
    for i in range(1, 6):
        area = next((a for a in si.area_list if a.area_name == f'{A_SHOP_CARD_PREFIX}{i}'), None)
        if area is not None and area.pc_rect is not None:
            pts.append(area.pc_rect.center)
    return pts


def _ocr(ctx: SrContext, screen: MatLike, rect: Rect | None) -> list:
    """对 screen 的 rect 区域 OCR(rect None → [])。"""
    if rect is None:
        return []
    return ctx.ocr_service.get_ocr_result_list(image=screen, rect=rect, crop_first=False)


def is_prep_like_frame(ctx: SrContext, screen: MatLike) -> bool:
    """帧态判据(r330,用户循环「稳定→观察→对账&hook」的 hook 门):
    画面精准命中 备战屏 或 开商店屏(id_mark 体系,框架
    screen_utils)→ True;过渡帧/结算/事件/动画帧 → False。

    用途:**采集·停机钩子自检**——埋在 reader 深处的钩子
    (summon/bookcard/layout/star)任何调用路径下先过本判据,
    过渡帧不触发(防误采/误停;局35 类动画帧实证形态)。
    best-effort:识别异常 → False(保守,不触发钩子)。
    """
    try:
        from one_dragon.base.screen import screen_utils
        name = screen_utils.get_match_screen_name(
            ctx=ctx, screen=screen,
            screen_name_list=[SCREEN_NAME, SHOP_SCREEN_NAME],
            crop_first=False)
        return name is not None
    except Exception:   # noqa: BLE001  判据 best-effort;异常=不触发
        return False


def _first_int(texts: list[str]) -> int | None:
    """从文本列表提取第一个整数(逐文本正则);无则 None。"""
    for t in texts:
        m = re.search(r'\d+', t)
        if m:
            return int(m.group())
    return None
