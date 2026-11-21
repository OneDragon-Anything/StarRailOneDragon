"""货币战争**备战-开拓商店画面**额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「货币战争-备战-开拓商店」后,框架按 ``screen_name``
查表调用本识别器,把开拓商店浮层的结构化领域事实塞进返回的 ``extras``:
开拓力余额 + 四商品槽结构化读卡(槽带态)/ 中央展示卡(软锁态)+ 帕姆王进度。
读取主体 = :func:`cw_trainshop_obs.read_trainshop_panel` 等纯读函数(与画面 op
消费同源,MCP agent 不必自己 OCR / 看图)。此前本画面无识别器 → extras 恒 null,
第十一局的读数全靠截帧 + 视觉读图顶替,本识别器落地后补齐结构化识别口径。

**并发安全**:纯读(不写 self. / 模块全局 / session),与备战识别器同纪律。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.application.currency_war.kernel.cw_obs_core import (
    PIONEER_SHOP_SCREEN_NAME,
)
from sr_od.application.currency_war.obs.cw_trainshop_obs import (
    read_pam_progress,
    read_trainshop_balance,
    read_trainshop_panel,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


class TrainShopPanelRecognizer(ScreenRecognizer):
    """货币战争备战-开拓商店画面额外识别器(余额 + 四槽读卡 + 帕姆王进度)。"""

    screen_name: str = PIONEER_SHOP_SCREEN_NAME   # '货币战争-备战-开拓商店'

    extras_doc: dict[str, str] = {
        'balance': '开拓力余额(int|None;读区-星穹列车币先裁后 OCR,读不到→None)',
        'mode': "面板呈现形态:'slots'=常规四槽带(槽1刷新钮+槽2-4商品)/"
                "'showcase'=中央展示卡态(四槽带不在场;= 首开空池软锁态或恢复态"
                '死锁,画面同构读层不区分,解锁=点中央展示卡,坐标见 showcase_card)/'
                "'unknown'=形态判不出(三信号不全,两键 None,不猜)",
        'shop_cards': "四槽 list(定长 4,下标 0-3 ↔ 物理槽 1-4;槽带态才产出,"
                      'showcase/unknown→None);元素 {kind: refresh/content/unknown,'
                      'card: {slot: 物理槽号1基, x: 槽中心x(点击用), name, faction,'
                      'cost: 开拓力标价(int|None,OCR 名行行尾), star: 恒 null'
                      '(卡面无星级未建模), trial, item_type: char/other} | null}。'
                      '槽1=「全部刷新」钮(kind=refresh,标价=读区-刷新费用窄窗 OCR,'
                      '实测恒 1);角色卡身份=SIFT 立绘识别(faction=注册表首阵营;'
                      '卡面显示玩家昵称「Momojie」的开拓者变体读规范名「开拓者」,'
                      '换季改名归一表口径,同备战席读数),'
                      '属性/改件卡=名行 OCR(item_type=other,faction="?");'
                      'unknown=应为内容但识别失败(决策一律跳过)',
        'showcase_card': "中央展示卡读数 {name, cost, cx, cy} | None(showcase 态产出;"
                         'cx/cy=卡 rect 中心 1080p 绝对坐标=解锁点击点;cost 0 价赠送品'
                         '实测「星穹列车,跃迁!」)',
        'pam_progress': '[当前进度, 目标] (int 二元组|None):帕姆王累计消费进度'
                        '(本局内口径,每局从 0 重起,满 500 送帕姆王);分母非 500 判'
                        '误读→None;首开空池帧实测帕姆块未渲染→None(与玩家卡'
                        '「软锁态全程可读」另局口径并存,以实读为准)',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002  命中画面 ScreenInfo;读取经 cw_obs_core 读 area,暂未直接用
    ) -> dict | None:
        """开拓商店面板领域事实 → dict(纯读;字段语义见 extras_doc)。"""
        panel = read_trainshop_panel(ctx, image)
        data = dict(panel)
        data['balance'] = read_trainshop_balance(ctx, image)
        pam = read_pam_progress(ctx, image)
        data['pam_progress'] = ([pam[0], pam[1]] if pam is not None else None)
        return data
