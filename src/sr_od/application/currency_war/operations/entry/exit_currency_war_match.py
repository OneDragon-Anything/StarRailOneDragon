# r279/r302/r303 实战验证(战斗中/胜利结算/失败链三路 ✓);
# 投资策略屏分支 r303b 手动链验证(画面档齐)。
# r317(第三次实录 W71):投资策略屏退局卡点机制根修——
#   ① 分支顺序:投资策略屏(独立屏,右上「返回备战界面」按钮)必须**先**走
#      「选卡+确认」(area 定位,手动实证有效);若先走 :73「返回备战界面」
#      全屏 OCR 点击,该按钮热区与 OCR 框中心偏移(~60px)→ 点击落空 →
#      round_wait 死循环 141x/444s(2026-08-25 实录),且短路 :78 正确分支;
#   ② 结算按钮 OCR 统一收紧 lcs_percent=0.8(与 battle_loop 3b 同款):
#      「继续挑战」默认 0.5 与战斗暂停屏「继续战斗」ratio=0.75 误匹配
#      → 点「继续战斗」恢复战斗 → 退局打转 2min(实录 03:59:35-04:01:35)。

"""从货币战争对局中退出(放弃+结算)回大厅。

高频重复操作(测试/刷开局/回滚),手动做很繁琐(Esc→放弃→结算3页→大厅)→ 建成 op 一键调用。
支持入口:备战阶段 / 战斗中 / **事件 overlay**(投资策略/环境/补给/遭遇/巨星 —— 先 escape 回备战)
(任何有 Esc 放弃提示的态)→ 放弃并结算 → 结算 3 页 → 大厅。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_observation import area_center
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ExitCurrencyWarMatch(SrOperation):
    """放弃当前货币战争对局,返回大厅。"""

    STATUS_AT_LOBBY: ClassVar[str] = '已返回货币战争大厅'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='退出货币战争对局')

    @operation_node(name='退出对局', is_start_node=True, node_max_retry_times=30)
    def exit_match(self) -> OperationRoundResult:
        screen = self.last_screenshot

        # 已在大厅 → 完成
        if self.round_by_find_area(screen, '货币战争-大厅', '标识-创业指南').is_success:
            return self.round_success(ExitCurrencyWarMatch.STATUS_AT_LOBBY)

        # 放弃提示 → 放弃并结算
        if self.round_by_ocr_and_click(screen, '放弃并结算', success_wait=3).is_success:
            log.info('[cw-exit] 放弃并结算 → 结算页')
            return self.round_wait(wait=2)

        # 结算页 1:挑战失败/下一步。胜利结算屏(局30 实证卡点):
        # 按钮文案是「继续挑战」——先试它,再「下一步」
        # r309b(局31 卡点):「结算-失败」屏(挑战进度屏)按钮是
        # 「前往结算」——第三种文案,先试
        # r317:结算按钮 OCR 统一 lcs_percent=0.8(battle_loop 3b 同款)——
        # 防「继续挑战」误匹配战斗暂停屏「继续战斗」(ratio 0.75,默认 0.5 会命中)。
        if self.round_by_ocr_and_click(screen, '前往结算', success_wait=3, lcs_percent=0.8).is_success:
            log.info('[cw-exit] 进度结算屏 → 前往结算')
            return self.round_wait(wait=2)
        if self.round_by_ocr_and_click(screen, '继续挑战', success_wait=3, lcs_percent=0.8).is_success:
            log.info('[cw-exit] 胜利结算 → 继续挑战')
            return self.round_wait(wait=2)
        if self.round_by_ocr_and_click(screen, '下一步', success_wait=3, lcs_percent=0.8).is_success:
            return self.round_wait(wait=2)

        # 结算页 2:下一页
        if self.round_by_ocr_and_click(screen, '下一页', success_wait=3, lcs_percent=0.8).is_success:
            return self.round_wait(wait=2)

        # 结算页 3:返回货币战争
        if self.round_by_ocr_and_click(screen, '返回货币战争', success_wait=3, lcs_percent=0.8).is_success:
            return self.round_wait(wait=2)

        # 备战/对局中(无放弃提示)→ Esc 弹放弃提示
        # r317:「备战阶段」裸 OCR 必须收紧 lcs=0.8——find_by_ocr 直接 LCS 匹配
        # (无 difflib 前置过滤),默认 0.5 时在投资策略屏误命中「返回备战界面」
        # (LCS「备战」2/4=0.5)→ 每轮 esc(无效)→ round_wait 死循环 141x
        # (2026-08-25 实录零分支推进的真首卡点,先于 :73/:78)。
        if (self.round_by_find_area(screen, '货币战争-备战', '备战标识-购买经验').is_success       # 备战
                or self.round_by_ocr(screen, '备战阶段', lcs_percent=0.8).is_success   # TODO(T#103) 待建 area
                or self.round_by_find_area(screen, '货币战争-备战', '按钮-出战').is_success):
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=2)

        # r303b(局30 实证):「返回备战界面」点后可能弹投资策略
        # 三选一(退局途中绕不过)→ 选左卡+确认(任意策略都行,
        # 本局反正要弃)→ 回备战再走 Esc 链
        # r317 顺序修正:本分支(round_by_find_area area 定位)必须**在**
        # 「返回备战界面」(round_by_ocr_and_click 全屏 OCR)**之前**——
        # 投资策略屏是独立屏,右上角也有「返回备战界面」按钮文字:若
        # OCR 分支在前,会命中该文字并点击 OCR 框中心 (1790,57),但按钮
        # 热区中心 ≈ (1850,60)(像素实测,OCR 框 1717-1863 vs 底框
        # 1780-1920)→ 点击落空 → round_wait 死循环 141x/444s(2026-08-25
        # 实录,零分支推进),且短路本分支(选卡+确认,手动实证有效)。
        if self.round_by_find_area(screen, '货币战争-投资策略',
                                   '标识-请选择投资策略').is_success:
            # W62 件3(ADR-0329):确认按钮点击不落地修复——旧版
            # ``round_by_ocr_and_click(scr2, '确认')`` 全屏 OCR 搜「确认」
            # 对 stylized 按钮静默失配(验证局清场 748s 卡行;手动
            # (460,475)+(978,984) 两击解锁,(978,984) = screen_info
            # 「按钮-确认」area 中心)→ 改用 area 中心点击,与生产路径
            # HandleInvestStrategy 同源(同屏同按钮 area 中心,实机验证可靠);
            # 点击带 bug#1 mouse_move 缓解(partner reset 根因同类)。
            _confirm = (area_center(self.ctx, '按钮-确认', '货币战争-投资策略')
                        or Point(978, 983))   # 兜底常量 = HandleInvestStrategy.CONFIRM
            self.ctx.controller.mouse_move(Point(460, 475))   # 左卡
            self.ctx.controller.click(Point(460, 475))
            time.sleep(1.2)
            self.ctx.controller.mouse_move(_confirm)
            self.ctx.controller.click(_confirm)
            log.info('[cw-exit] 投资策略三选一(退局途中)→ 左卡+确认(area 定位)')
            return self.round_wait(wait=2)

        # 事件 overlay(投资策略/环境 有「返回备战界面」)→ 点回备战,下轮走备战分支 Esc→放弃。
        # 修 bug:事件屏无「放弃并结算」/备战文本 → 全分支不命中 → retry 死循环(2026-08-04 实测卡 210s+)。
        # r317 顺序修正:本分支**必须在投资策略分支之后**(投资策略屏也是独立屏,
        # 右上角同有「返回备战界面」按钮文字;全屏 OCR 点击其 OCR 框中心落空——
        # 按钮热区 vs OCR 框中心偏移 ~60px,实录 141x 等待零推进)→ 此处仅处理
        # 非投资策略的事件 overlay(环境等)。lcs_percent=0.8 同 battle_loop 3b
        # (防「返回备战界面」与「返回货币战争」共享子序列 0.5 误匹配)。
        if self.round_by_ocr_and_click(screen, '返回备战界面', success_wait=2, lcs_percent=0.8).is_success:
            return self.round_wait(wait=2)
        if (self.round_by_ocr(screen, '补给阶段').is_success
                or self.round_by_ocr(screen, '遭遇其一').is_success
                or self.round_by_ocr(screen, '盛会之星').is_success
                or self.round_by_ocr(screen, '可合成列表').is_success
                or self.round_by_ocr(screen, '角色详情').is_success):
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=2)

        # r279(用户交办,分支③实证建档 2026-08-23):战斗中(不可识别
        # 画面)→ 右上角 X → 「货币战争-战斗暂停」(新档)→「撤退」→
        # 中断挑战弹窗(上方「放弃并结算」分支接管)。修战斗中 retry
        # 死循环(旧版全分支不命中)。
        if self.round_by_find_area(screen, '货币战争-战斗暂停',
                                   '标识-战斗暂停').is_success:
            if self.round_by_find_and_click_area(
                    screen, '货币战争-战斗暂停', '按钮-撤退',
                    success_wait=2).is_success:
                log.info('[cw-exit] 战斗暂停→撤退 → 中断挑战弹窗')
                return self.round_wait(wait=2)
        # 战斗中(未暂停态):点右上角 X 弹暂停(实证 2026-08-23)
        # r302:controller.click 需 Point 对象(裸 int 坐标在
        # game2win_pos 坐标转换层炸 'int' has no .x——op 异常+
        # 采集钩子 skip 的共同根因)
        self.ctx.controller.click(Point(1843, 42))
        return self.round_wait(wait=1.5)
