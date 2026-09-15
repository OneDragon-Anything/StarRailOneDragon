"""货币战争画面状态判定(轻量画面状态模块,仿 sim_uni_screen_state 模式)。

只依赖 screen_utils 基础原语,不依赖 CurrencyWarApp / Operation——
供「返回普通大世界」等上层兜底 op 在不引入 app 依赖的前提下复用
对局中画面判定单一源(与 ``CurrencyWarApp._in_match`` 第①层同源)。
"""
from typing import TYPE_CHECKING

from cv2.typing import MatLike

from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

# 对局中画面名统一前缀:新对局画面建档(命名带前缀)自动进判定列表。
CW_IN_MATCH_PREFIX: str = '货币战争-'

# 大厅态白名单(非对局屏,必须显式排除):
# 这些屏名带 货币战争- 前缀,会被 in_match_screen_names 自动收进「对局中」
# 判定,但都不是对局中态——在场即误判「已在对局中」跳过入口导航,必须在此
# 显式排除:
# - 入口导航层:大厅/模式选择/攻略系/弹窗系/阵容编辑;
# - 列车补给每日弹窗:盖在大世界之上,早于 CW 入口首段导航;
# - 星琼详情/星徽详情/积分奖励:入口链路径上的详情弹窗与局末奖励页。
# - 对局前画面/图鉴查询页:难度确认(新局开始前选难度)、数据银行/
#   装备图鉴/竞争对手图鉴列表与详情(图鉴查询,与攻略系同类)。
LOBBY_STATE_SCREENS: frozenset[str] = frozenset({
    '货币战争-大厅', '货币战争-模式选择',
    '货币战争-攻略列表', '货币战争-攻略详情', '货币战争-攻略图例',
    '货币战争-攻略码输入弹窗', '货币战争-保存阵容弹窗',
    '货币战争-装备追踪弹窗', '货币战争-阵容编辑',
    '货币战争-列车补给弹窗',
    '货币战争-星琼详情', '货币战争-星徽详情', '货币战争-积分奖励',
    '货币战争-难度确认', '货币战争-数据银行', '货币战争-装备图鉴',
    '货币战争-竞争对手图鉴列表', '货币战争-竞争对手图鉴详情',
})


def in_match_screen_names(screen_info_list: list) -> list[str]:
    """对局中态屏名(screen_info 全集过滤:货币战争- 前缀 − 大厅态白名单)。

    新对局画面建档(命名带前缀)自动进列表——新屏漏判 → 兜底链死循环
    的 M54 类问题结构性消除。
    """
    return [si.screen_name for si in screen_info_list
            if si.screen_name.startswith(CW_IN_MATCH_PREFIX)
            and si.screen_name not in LOBBY_STATE_SCREENS]


def get_in_match_screen_name(ctx: 'SrContext', screen: MatLike) -> str | None:
    """当前画面是否为货币战争对局中画面,是则返回其屏名,否则 None。

    组合 ``in_match_screen_names``(判定单一源)+ ``get_match_screen_name``
    (画面匹配,与 ``CurrencyWarApp._in_match`` 第①层同一实现)。

    名单为空或匹配异常时 log.warning 后返回 None:判定失败退回调用方的
    既有兜底行为(有界失败,不阻塞);异常必须留日志,不静默。
    """
    try:
        screen_name_list = in_match_screen_names(ctx.screen_loader.screen_info_list)
        if not screen_name_list:
            log.warning('[cw-screen-state] 对局中画面名单为空(screen_info 未加载?),跳过判定')
            return None
        from one_dragon.base.screen.screen_utils import get_match_screen_name
        return get_match_screen_name(ctx, screen, screen_name_list=screen_name_list)
    except Exception:  # noqa: BLE001  画面匹配失败退回调用方兜底,不阻塞
        log.warning('[cw-screen-state] 对局中画面匹配异常,退回调用方兜底', exc_info=True)
        return None
