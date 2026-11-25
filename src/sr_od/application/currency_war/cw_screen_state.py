"""货币战争画面状态判定(轻量画面状态模块,仿 sim_uni_screen_state 模式)。

只依赖 screen_utils 基础原语,不依赖 CurrencyWarApp / Operation——
供「返回普通大世界」等上层兜底 op 在不引入 app 依赖的前提下复用
对局中画面判定单一源(与 ``CurrencyWarApp._in_match`` 第①层同源)。
对局中名单(前缀 − 白名单)与大厅态白名单互补,两者各配一个画面匹配函数。
图鉴查询页名单(CODEX_STATE_SCREENS)是大厅态白名单的子集,单独成常量供退出链
按屏名清单识别图鉴页(消费方自带画面匹配,不另配函数)。
唯一的例外依赖 = :func:`is_exit_safe_prep_frame` 在函数内惰性导入观察域的合成确认
浮层识别(模块级不导入,上面「只依赖基础原语」的边界不变)。
"""
from typing import TYPE_CHECKING

from cv2.typing import MatLike

from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

# 对局中画面名统一前缀:新对局画面建档(命名带前缀)自动进判定列表。
CW_IN_MATCH_PREFIX: str = '货币战争-'

#: 图鉴查询页名单(数据银行总门户 + 其子页)。入表判据 = 右上返回箭头与各档
#: 「按钮-返回」area 同位同模板(cw_adv_layout_back),且返回逐级向上:子页 →
#: 数据银行 → 大厅(数据银行自备战打开时 → 备战);各级去向的画面档依据见
#: 玩家 skill 画面卡 skills/sr-od-currency-war/references/screens/
#: 货币战争-数据银行.md「按钮-返回」行。消费方 = BackToNormalWorldPlus 图鉴族
#: 分支(屏名清单精确命中后点返回箭头退一级)。成员按定义是对局前查询页,
#: 经 LOBBY_STATE_SCREENS 并集自动进大厅态白名单——新图鉴页建档(带返回箭头
#: area + 返回边)只改本常量,判定与退出链两处同时生效。
CODEX_STATE_SCREENS: frozenset[str] = frozenset({
    '货币战争-数据银行', '货币战争-装备图鉴', '货币战争-主角光环图鉴',
    '货币战争-竞争对手图鉴列表', '货币战争-竞争对手图鉴详情',
})

# 大厅态白名单(非对局屏,必须显式排除):
# 这些屏名带 货币战争- 前缀,会被 in_match_screen_names 自动收进「对局中」
# 判定,但都不是对局中态——在场即误判「已在对局中」跳过入口导航,必须在此
# 显式排除:
# - 入口导航层:大厅/模式选择(普通+进行中形态)/攻略系/弹窗系/阵容编辑;
#   模式选择-进行中与结束结算确认是挂起对局的入口画面(委托退出链处置,
#   不是对局中态,见 CwEntryExit.route 的显式点名分支);
# - 列车补给每日弹窗:盖在大世界之上,早于 CW 入口首段导航;
# - 星琼详情/星徽详情/积分奖励:入口链路径上的详情弹窗与局末奖励页。
# - 对局前画面:难度确认(新局开始前选难度);图鉴查询页 = CODEX_STATE_SCREENS
#   (并集入本白名单,成员不在此重复枚举)。
LOBBY_STATE_SCREENS: frozenset[str] = frozenset({
    '货币战争-大厅', '货币战争-模式选择',
    '货币战争-模式选择-进行中', '货币战争-模式选择-结束结算确认',
    '货币战争-攻略列表', '货币战争-攻略详情', '货币战争-攻略图例',
    '货币战争-攻略码输入弹窗', '货币战争-保存阵容弹窗',
    '货币战争-装备追踪弹窗', '货币战争-阵容编辑',
    '货币战争-列车补给弹窗',
    '货币战争-星琼详情', '货币战争-星徽详情', '货币战争-积分奖励',
    '货币战争-难度确认',
}) | CODEX_STATE_SCREENS


#: 可直接点门形图标发起退局的备战态屏名(A 类,语义 = 可交还退出 op 的
#: 备战态,含出战钮形态变体)。屏名白名单而非备战档全识别标志判定:变体画面的
#: 「出战」识别标志被替换(免战→「跳过(N/N)」/茶歇预告→「幕后茶歇」),全识别标志
#: 判定对变体恒 False。变体入表判据 = 归档帧左上门形退出图标在场且与备战帧同位
#: 同一(免战:归档帧 货币战争-备战-免战/跳过态.webp;茶歇预告:归档帧
#: 货币战争-备战-茶歇预告/茶歇预告态.webp,同位裁片模板匹配 ≥0.99、灰度平均绝对差
#: ≤3/255;点击定位统一走备战档「按钮-退出对局」纯定位区)。退出链路由③与对局
#: 循环 stop_at_prep 停机位共用本常量(cw-exit-dispatch 迭代),禁两处各写一份——
#: 两侧判定分叉会互踢死循环。
PREP_DIRECT_EXIT_SCREENS: frozenset[str] = frozenset({
    '货币战争-备战', '货币战争-备战-免战', '货币战争-备战-茶歇预告',
})


def in_match_screen_names(screen_info_list: list) -> list[str]:
    """对局中态屏名(screen_info 全集过滤:货币战争- 前缀 − 大厅态白名单)。

    新对局画面建档(命名带前缀)自动进列表——新屏漏判 → 兜底链死循环
    的 M54 类问题结构性消除。
    """
    return [si.screen_name for si in screen_info_list
            if si.screen_name.startswith(CW_IN_MATCH_PREFIX)
            and si.screen_name not in LOBBY_STATE_SCREENS]


def is_exit_safe_prep_frame(ctx: 'SrContext', screen: MatLike,
                            screen_name: str | None = None) -> bool:
    """当前帧是不是「可安全交还退出调度」的备战态。

    两个条件同时成立才算:屏名在 A 类名单(:data:`PREP_DIRECT_EXIT_SCREENS`)里,且合成
    确认浮层不在场。退出链路由③与对局循环的 stop_at_prep 停机位共用本判定——同源是防
    「循环停 ↔ 退出重派」互踢死循环的硬前提。

    为什么要加浮层这一条:合成确认浮层是全局模态,在场时备战画面的识别标志照样全中,
    只看屏名会把浮层帧当成可交还的备战态直接去点门形图标——那一下会被浮层吞掉,退局
    必败。浮层在场、有按钮候选但配不成对、配对有歧义,都算不安全(判否之后交给备战
    画面 op 处置,处置完的下一帧才交还)。开商店画面不在 A 类名单里,商店开着的帧不进
    这道判定、不读右侧装备。

    Args:
        screen_name: 调用方已经认过的屏名;缺省时现做一次对局中画面全集识别。调用方
            手里已有屏名就传进来,省一次全集识别。
    """
    if screen_name is None:
        screen_name = get_in_match_screen_name(ctx, screen)
    if screen_name not in PREP_DIRECT_EXIT_SCREENS:
        return False
    from sr_od.application.currency_war.obs import cw_synthesis_overlay_obs
    state = cw_synthesis_overlay_obs.read_synthesis_overlay_of(ctx, screen).state
    return state == cw_synthesis_overlay_obs.STATE_ABSENT


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


def get_lobby_state_screen_name(ctx: 'SrContext', screen: MatLike) -> str | None:
    """当前画面是否为大厅态白名单画面(对局前 / 非对局建档屏),是则返回其屏名,否则 None。

    与 ``get_in_match_screen_name`` 互补:两名单互斥(对局中名单 = 前缀 − 白名单),
    合起来覆盖带前缀的全部建档画面。消费场景 = 关键词启发式之前先问「是不是已知
    的非对局屏」:白名单只过滤对局中名单,对 ``CurrencyWarApp._in_match`` 第②层
    关键词兜底不可见——对局前建档页带「投资策略图鉴」字样即被关键词误判为对局中。
    精确建档命中(任一方向)必须优先于关键词启发式,本函数即「非对局」方向的精确命中。

    边界:白名单成员未建档时 ``get_match_screen_name`` 自然跳过;无 id_mark 的建档屏
    结构性不可命中(精确匹配 = 全 id_mark AND)。匹配异常时 log.warning 后返回 None,
    调用方不短路、退回既有兜底(有界失败,不阻塞);异常必须留日志,不静默。
    """
    try:
        from one_dragon.base.screen.screen_utils import get_match_screen_name
        return get_match_screen_name(ctx, screen,
                                     screen_name_list=list(LOBBY_STATE_SCREENS))
    except Exception:  # noqa: BLE001  画面匹配失败退回调用方兜底,不阻塞
        log.warning('[cw-screen-state] 大厅态白名单画面匹配异常,退回调用方兜底',
                    exc_info=True)
        return None
