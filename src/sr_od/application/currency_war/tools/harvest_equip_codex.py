# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 · 装备图鉴批量采集(工具型 operation;CW 专属,放 app/cw/tools/)。

== 作用 ==
从游戏内「数据银行 → 装备图鉴」逐件选中装备,采集①右侧详情面板的装备图标(固定框裁切,
存 ``assets/template/cw_equip/<名>.png``)②该装备的整屏截图(存 ``.debug/temp/cw_shots/<tier>/``,
含完整效果正文 / 合成公式,供离线 OCR 抽数据)。按 OCR 装备名去重,整页 0 新增即停。
用于:建装备图标库(身份识别/恢复用)+ 采权威装备数据(效果/合成公式,数据银行为权威源)。

== ⚠️ 使用前提:必须先手动进到这个画面 ==
游戏内:从「备战」点「数据银行」(非破坏性 overlay,对局保留)→ 进「装备图鉴」,
**停在装备图鉴画面**(左侧装备网格 + 右侧详情面板可见)。不必预选 tier —— 传 ``tab_x``
让本 op 自己点 tier tab;或先手动切到某 tier 再跑(``tab_x=0`` 采当前 tab)。
不在装备图鉴画面跑会乱点(坐标按图鉴布局硬编码)。需游戏窗口就绪(Session 1)。

== 怎么用(经 MCP run_operation)==
    # 采某个 tier:传 tier 名 + 次级 tab 的 x 坐标(op 自动切 tab 再采)
    run_operation(op_id='sr_od.application.currency_war.tools.harvest_equip_codex.HarvestEquipCodex',
                  args={'tier': '进阶', 'tab_x': 338})
    # 采当前 tab(tab_x=0 或省略):
    run_operation(op_id='sr_od.application.currency_war.tools.harvest_equip_codex.HarvestEquipCodex',
                  args={'tier': '当前'})

次级 tier tab 的 x 坐标(y 固定 170):简易 217 / 进阶 338 / 特权 459 / 星徽 579 /
合集(白昼+Fate+骇客+财富)699 / 消耗品 811。

== 2026-08-15 起重跑范围(官方 API 已覆盖的跳过) ==
攻略广场官方 API 已覆盖:进阶/特权/星徽 全部数据+图标(gen_plaza_chars.py 一键),
简易的 11 个合成材料。重跑只需两个 tab:
- 简易(217):仅补数据字段(图标手工库已有;官方无简易 desc/属性)
- 合集(699):42 条缺口全在此(命运改件/圣杯系/Max/Pro 系/卡带系/功能件——
  白昼+Fate+骇客+财富四子 tab 都要过;部分需诅咒局/投资环境解锁图鉴条目)
进阶(338)/特权(459)/星徽(579)跳过——重复采只费时不增数据。
消耗品(811)低优先(工具类,策略价值待定)。

== 为什么是 operation 而非独立脚本 ==
独立脚本用 ``SrContext.controller`` 经 ``pyautogui`` 找游戏窗口,**只在 Session 1 能看到窗口**;
Session 0 的 Bash 跑报「游戏窗口未就绪」(session 隔离,见 memory session0-cannot-see-game-window)。
本 operation 经 ``run_operation`` 在 **backend 进程(Session 1)** 执行,直接用 backend 已挂的
``ctx.controller`` + ``ctx.ocr_service``,绕开 session 问题 + 无需重新 init。

== 几何(1080p 固定;跨 tier tab 不变)==
网格 7 列 × 3 可见行;右侧详情:装备名 OCR 区 + 选中装备图标固定框(CV squares 验证)。
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.log_utils import log
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

# 固定几何(1080p 游戏坐标;简易 tab CV 校准,跨 tier tab 不变)
GRID_COLS = [131, 307, 482, 657, 832, 1006, 1183]   # 7 列 x 中心
GRID_ROWS = [348, 581, 814]                          # 3 可见行 y 中心(行间距 233)
ICON_BOX = (1443, 125, 1541, 223)                   # 右侧详情「选中装备图标」固定框 98×98
NAME_REGION = (1540, 115, 1860, 160)                # 右侧装备名 OCR 区(加宽防长名截断)
SCROLL_FROM = Point(600, 800)                       # 上滑翻页:从底拖向顶(往下看更多行)
SCROLL_TO = Point(600, 520)


class HarvestEquipCodex(SrOperation):
    """采集当前 tier tab 的全部装备图标 + 全图(点格→截图→OCR名→存→滚动→去重)。"""

    def __init__(self, ctx: SrContext, tier: str = '当前', tab_x: int = 0):
        """
        :param ctx: 上下文(backend 注入)
        :param tier: tier 名(输出目录命名 / 日志)
        :param tab_x: 次级 tier tab 的 x 坐标(y 固定 170);>0 时先点该 tab 切到目标 tier 再采,
            =0 时采当前 tab(调用方已切好)。简易217/进阶338/特权459/星徽579/合集699。
        """
        SrOperation.__init__(
            self, ctx,
            op_name=f'采装备图鉴-{tier}',
            need_check_game_win=False,   # 在图鉴 overlay 内,不让框架尝试 OpenAndEnterGame 纠正
        )
        self.tier: str = tier
        self.tab_x: int = tab_x

    def _ocr_name(self, img) -> str:
        """OCR 右侧装备名区,取最长(最像装备名)文本;归一 OCR 把「·」读成「-」的问题。

        保留裁剪读(2026-08-24 crop-first 审计):每次 click 后独立截图、单 OCR 消费者
        (无同帧缓存复用收益);NAME_REGION 窄带隔离图鉴网格密集文字。
        """
        x0, y0, x1, y1 = NAME_REGION
        crop = img[y0:y1, x0:x1]
        res = self.ctx.ocr_service.get_ocr_result_list(image=crop, crop_first=False)
        texts = [r.data.strip() for r in res if r.data and r.w > 20]
        nm = max(texts, key=len) if texts else ''
        # 装备名分隔符规范是「·」(中点),OCR 偶读成「-」;装备名不含「-」→ 全归一为「·」
        return nm.replace('-', '·')

    @operation_node(name='采集装备图鉴', is_start_node=True)
    def harvest(self) -> OperationRoundResult:
        ctrl = self.ctx.controller
        # 先切到目标 tier tab(若指定 tab_x)
        if self.tab_x > 0:
            ctrl.click(Point(self.tab_x, 170), press_time=0.1, pc_alt=False)
            time.sleep(1.2)
        repo = Path(__file__).resolve().parents[3]
        # 统一模板目录(2026-08-16 用户规范 assets/template/currency_war/<类型>/;2026-08-18
        # 修:旧 'assets/template/cw_equip' 是规范外路径 → 归一 equip_legacy(手采图鉴
        # icon 与 plaza 官方库互补,同库去重)。
        icon_dir = repo / 'assets/template/currency_war/equip_legacy'
        shot_dir = repo / '.debug/temp/cw_shots' / self.tier
        icon_dir.mkdir(parents=True, exist_ok=True)
        shot_dir.mkdir(parents=True, exist_ok=True)

        seen: set[str] = set()
        pass_no = 0
        while pass_no < 8:
            pass_no += 1
            new_this = 0
            for ry in GRID_ROWS:
                for cx in GRID_COLS:
                    try:
                        ctrl.click(Point(cx, ry), press_time=0.1, pc_alt=False)
                        time.sleep(0.4)
                        img = ctrl.get_screenshot(independent=False)
                        if img is None:
                            continue
                        img = ctrl.fill_uid_black(img)
                        nm = self._ocr_name(img)
                        if not nm or nm in seen:
                            continue
                        seen.add(nm)
                        new_this += 1
                        x0, y0, x1, y1 = ICON_BOX
                        cv2_utils.save_image(img[y0:y1, x0:x1], str(icon_dir / f'{nm}.png'))
                        cv2_utils.save_image(img, str(shot_dir / f'{nm}.png'))
                        log.info(f'[采装备-{self.tier} pass{pass_no}] +{nm}')
                    except Exception as e:  # noqa: BLE001 单格失败不致命,继续下一格
                        log.warning(f'[采装备-{self.tier}] 格 ({cx},{ry}) 失败: {e}')
            log.info(f'[采装备-{self.tier} pass{pass_no}] +{new_this} new (total {len(seen)})')
            if new_this == 0:
                break
            ctrl.drag_to(SCROLL_TO, start=SCROLL_FROM, duration=0.5)
            time.sleep(0.6)

        names = sorted(seen)
        log.info(f'[采装备-{self.tier}] 完成: {len(names)} 件')
        return self.round_success(status=f'采装备-{self.tier} 完成: {len(names)} 件 -> {", ".join(names)}')
