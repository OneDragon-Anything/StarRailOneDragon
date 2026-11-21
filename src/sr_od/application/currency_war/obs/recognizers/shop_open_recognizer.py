"""货币战争**备战-开商店画面**额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「货币战争-备战-开商店」后,框架按 ``screen_name`` 查表调用本
识别器,把开商店画面(商店横排面板 + 备战舞台同屏)的结构化领域事实塞进返回的 ``extras``:
商店五槽牌面 + 刷新概率条 + 刷新钮免费次数 + 备战全量状态(金币/阶段/血量/等级/经验/
前后台/备战席)。供 MCP 智能体玩货币战争时直接读用,不必自己 OCR / 看图。

**与备战识别器的关系**:备战侧领域事实读取主体 = ``battle_prep_recognizer.read_prep_extras``
(单一实现,本识别器叠加商店域字段),不复制第二份读链。

**并发安全**:与备战识别器同纪律 —— 纯读(不写 self. / 模块全局 / session)。
商店读链 :func:`cw_observation.read_shop_cards` 的收起识别标志门(无全帧 OCR 入参时)
走二值化裁剪路径,首判 miss 会截新帧重判一次;本识别器只在画面已精准命中「开商店」后
被调用,门首判即过,不引入重帧。终判稳定门(全 empty/含 unknown 时 0.8s 后重读一次)
是读链内建语义,原样保留(analyze 响应耗时上限 ~0.8s,观察类 tool 可接受)。

v4.7 布局注:商店横排在画面顶部(五槽「商店牌-N」区域沿用旧建档,实机命中正常);
刷新按钮为圆形「D」钮,按钮态读数(免费剩余次数/付费标价)走
``cw_shop_refresh_obs.read_shop_refresh_button`` 现役链(免费态次数渲染在
「文本-刷新价格」rect 内,付费态该 rect 渲染标价——三态语义见该模块),本识别器
暴露其中的免费剩余次数字段(extras 消费面);刷新钮点击交互仍走既有「按钮-刷新」
area(动作原语),与本读数链分工。
"""
from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.obs.cw_observation import (
    read_refresh_probs,
    read_shop_cards,
)
from sr_od.application.currency_war.obs.cw_shop_refresh_obs import (
    read_shop_refresh_button,
)
from sr_od.application.currency_war.obs.recognizers.battle_prep_recognizer import (
    PREP_EXTRAS_DOC,
    read_prep_extras,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


def _shop_slots_to_json(slots: list) -> list[dict]:
    """ShopSlot 列表 → JSON 可序列化 list(定长 5,下标 0-4 ↔ 物理槽 1-5)。

    ShopCard 字段(x/slot/faction/name/cost/star/cost_source/trial)经 asdict 展开为 dict;
    slot = 物理槽号(1 基,= screen_info「商店牌-N」序号),买牌点击按它取坐标。
    """
    out: list[dict] = []
    for s in slots:
        entry: dict = {'kind': s.kind}
        if s.card is not None:
            entry['card'] = asdict(s.card)
        else:
            entry['card'] = None
        out.append(entry)
    return out


def _free_count_from_button(free: bool | None, free_remaining: int | None) -> int | None:
    """按钮态读数 → extras 免费剩余次数(纯函数可单测)。

    双态口径(与观察写端 gs.free_refresh_left 同源语义,``cw_observation``
    商店开态喂入口):免费态 = 识别标志读数(失读 None);付费域(耗尽/灰态,
    游戏规则 ⇒ 免费余量恒 0)= 0;整帧判不出(free=None)= None,不猜。
    """
    if free is True:
        return free_remaining
    if free is False:
        return 0
    return None


class ShopOpenRecognizer(ScreenRecognizer):
    """货币战争备战-开商店画面额外识别器(商店牌 + 备战全量状态)。"""

    screen_name: str = SHOP_SCREEN_NAME   # '货币战争-备战-开商店'

    # extras 字段说明(与 analyze 响应平级返回;备战族字段语义复用备战识别器声明,零第二转录)
    extras_doc: dict[str, str] = {
        **PREP_EXTRAS_DOC,
        'shop_cards': '商店五槽 list(定长 5,下标 0-4 ↔ 物理槽 1-5);元素 {kind: content/empty/unknown,'
                      'card: {slot: 物理槽号1基, x: 槽中心x(点击用), faction, name, cost, star, cost_source, trial} | null}。'
                      'trial=「试用」标签命中(试用形态卡,蓝紫底白字标签是唯一判别;同一形态有灰暗化与'
                      '正常亮度两种渲染,亮度不可作判据);'
                      '买光 = [empty×5] 合法真值;unknown = 应为内容但识别失败(决策一律跳过);店未开读不到→None',
        'refresh_probs': '刷新概率条 {费用档: 概率}(read_refresh_probs;读不到→None)',
        'refresh_free_count': '刷新钮免费剩余次数(int|None):免费态 = 钮内渲染数字;'
                              '付费态(「刷新 N金」耗尽/不可用灰态)= 0(游戏规则免费余量恒 0);'
                              '整帧判不出/次数失读→None(不猜,禁当 0 用)',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002  命中画面 ScreenInfo;读取经 cw_obs_core 读 area,暂未直接用
    ) -> dict | None:
        """开商店画面领域事实 → dict(备战全量 + 商店牌行 + 概率条 + 免费次数;纯读)。

        Args:
            ctx: 运行上下文。
            image: 开商店画面截图(analyze 已截,复用)。
            screen_info: 命中画面的 ScreenInfo。

        Returns:
            备战族 extras(dict,键集见 extras_doc)叠加商店域字段。
        """
        # with_rows=False:商店牌行盖住部署计数、面板遮挡使行 SIFT 不可靠(实机恒缺/残缺),
        # 开商店画面这三项设计性不返回;完整读数用备战画面(收店后)。
        data = read_prep_extras(ctx, image, full_read=False)
        slots = read_shop_cards(ctx, image)
        data['shop_cards'] = _shop_slots_to_json(slots) if slots is not None else None
        probs = read_refresh_probs(ctx, image)
        data['refresh_probs'] = ({str(k): v for k, v in probs.items()}
                                 if probs else None)
        # 刷新钮按钮态读数(免费剩余次数;复用现役三态链,零新增识别路径)。
        # gold 不传:affordable 判别不在本 extras 消费面,失读(None)不影响
        # free/free_remaining 判定。
        _btn = read_shop_refresh_button(ctx, image)
        data['refresh_free_count'] = _free_count_from_button(
            _btn.free, _btn.free_remaining)
        return data
