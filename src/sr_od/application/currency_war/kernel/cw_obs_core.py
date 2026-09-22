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
from sr_od.application.currency_war.kernel.cw_overlay_registry import (
    derive_upper_screens,
)
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


#: 非 overlay 上层屏残余段(两段式第二段;设计终版定案 2):
#: 会盖备战底层 UI、但**不是 overlay 生命周期对象**的画面——无 handler、
#: 无退场动作,注册表语义覆盖不到,显式保留 + 逐条 why 问责
#: (防「整表派生」强迫僵尸 spec 进注册表;注册表一致性测试断言
#: 「常量 = 派生值」防手改绕过派生)。
UPPER_SCREENS_NON_OVERLAY: tuple[str, ...] = (
    # 位面过渡:过渡帧(无交互对象),钩子/帧态门需排除
    '货币战争-位面过渡',
    # 攻略码输入弹窗:工具域弹窗,非对局 overlay 生命周期对象
    '货币战争-攻略码输入弹窗',
    # 备战-角色详情:检视浮窗(无 handler/无退场动作)
    '货币战争-备战-角色详情',
    # 装备详情浮窗(点右侧装备弹,备战底层 UI 全可见)与 角色信息提示(悬停角色
    # tooltip)同型穿透:唯一真值锚(装备推荐)只属角色详情大面板,两形态帧
    # 判不出角色详情 → 回落备战判定被放行(离线复跑实证:3 张真值帧
    # equip_detail_roller/synth_target/char_detail 锚 OCR 全空、prep-like=True;
    # 画面档按形态拆分后此处同步扩容,与 同手法)。
    '货币战争-备战-装备详情浮窗',
    '货币战争-备战-角色信息提示',
    # 赛前画面(对局外),非对局 overlay
    '货币战争-阵容编辑',
    '货币战争-模式选择',
)

#: 上层屏名单 = overlay 注册表派生段 + 非 overlay 残余段(两段拼接使残余屏
#: 移到段尾——逐屏判定的布尔结果与
#: 顺序无关,行为不变,消费方 is_prep_like_frame 零改动。防回归断言
#: 「常量 = 派生值」在测试仓 test_cw_overlay_registry.py)。
#: **逐个**判定,不能把名单与备战屏合并成一次 get_match_screen_name
#: 调用——框架按注册序返首个命中,备战在前则上层帧照样先中备战。
UPPER_SCREENS: tuple[str, ...] = (
    derive_upper_screens() + UPPER_SCREENS_NON_OVERLAY
)

# 金币说明 overlay 锚(Revision):C 类无档案 overlay(无独立 screen
# 档案,进不了 UPPER_SCREENS),保留锚 OCR 判定作为钩子帧态门的补充第三段
# (证据帧 034f8ef3:标题锚「标识-金币说明」pc_rect (1000,370,1165,435))。
_GOLD_INFO_ANCHOR_AREA: str = '标识-金币说明'
_GOLD_INFO_ANCHOR_TEXT: str = '金币说明'


def is_prep_like_frame(ctx: SrContext, screen: MatLike) -> bool:
    """帧态判据(两段式):**先**遍历 ``UPPER_SCREENS`` 逐屏
    get_match_screen_name,任一命中 → False(上层画面在场 = 非备战帧;
    上层不排除时曾发生选择伙伴帧被放行误拖实锤);**全部未命中后**再判
    备战/开商店双屏(id_mark 体系,框架 screen_utils)→ True;过渡帧/结算/
    事件/动画帧 → False。

    用途:**采集·停机钩子自检**——埋在 reader 深处的钩子
    (summon/bookcard/layout/star)任何调用路径下先过本判据,
    过渡帧不触发(防误采/误停;动画帧实证形态)。
    OCR 成本:上层判定与备战判定同帧复用全图 OCR 缓存(crop_first=False),
    对抗报告已证成本可忽略。best-effort:识别异常 → False(保守,不触发钩子)。
    """
    try:
        from one_dragon.base.screen import screen_utils
        for _upper in UPPER_SCREENS:
            if screen_utils.get_match_screen_name(
                    ctx=ctx, screen=screen,
                    screen_name_list=[_upper],
                    crop_first=False) is not None:
                return False
        name = screen_utils.get_match_screen_name(
            ctx=ctx, screen=screen,
            screen_name_list=[SCREEN_NAME, SHOP_SCREEN_NAME],
            crop_first=False)
        return name is not None
    except Exception:   # noqa: BLE001  判据 best-effort;异常=不触发
        return False


def gold_info_overlay_open(ctx: SrContext, screen: MatLike) -> bool:
    """金币说明 overlay 在场判定(Revision 第三段;锚 OCR,
    全图 OCR 缓存复用)。C 类无档案 overlay:无独立 screen 档案进不了
    ``UPPER_SCREENS``,两段式天然看不见 → 钩子停机前以锚命中作补充排除。
    best-effort:锚 area 缺失/异常 → False(不拦,回落两段式)。
    """
    try:
        r = _area_rect(ctx, _GOLD_INFO_ANCHOR_AREA, SCREEN_NAME)
        if r is None:
            return False
        return any(_GOLD_INFO_ANCHOR_TEXT in (t.data or '')
                   for t in _ocr(ctx, screen, r))
    except Exception:   # noqa: BLE001  best-effort;异常=不拦
        return False


def _first_int(texts: list[str]) -> int | None:
    """从文本列表提取第一个整数(逐文本正则);无则 None。"""
    for t in texts:
        m = re.search(r'\d+', t)
        if m:
            return int(m.group())
    return None
