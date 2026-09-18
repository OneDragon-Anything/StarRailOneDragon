"""货币战争 备战-武装箱选择 四选一画面 op(R7 独立立档;unified-action-factory 批 2a)。

R7 正位(用户裁定,design.md §2.6/R7):武装箱 4 选 1 的访问面是**独立建档
画面**「货币战争-备战-武装箱选择」——此前选卡以备战动作承载
(``CwActionPickBoxCardParam``,发射点 entry 'prep_box_pick' 臂,执行器内嵌默认选卡),
策略实现长进了备战词表且错挂画面归属。批 2a 起形态:

- 词表:``CwActionPickBoxCardParam`` 全链删除(词表类/发射点/执行器选卡半/适配器
  映射/效果账分支);武装箱选卡不属备战动作词表(screen_op.md §7
  单选族例外:选卡即终结);
- 链路:备战环 ``CwActionOpenBoxParam`` 点开启(**终结化**——开箱即交回)→ 外循环按
  本画面分发本 op → OCR 卡名 → 选卡决策(局内策略 ``decide_box_card``
  契约面,局外 kernel ``pick_equipment`` 机器单一源)→ 点卡 → 固定动画
  等待 → **选卡即终结交回**(选卡落地由下一帧观察覆盖)。

决策分层纪律(自原 ``PrepActionExecutor._default_box_card`` 原位平移,
decide_box_card 策略侧 / pick_equipment kernel 侧**不搬家**):打分只住
机器,本 op 禁第二打分实现;``decide_box_card`` 异常留证(完整栈)后
显式上抛、返回越界索引同 fail-closed 上抛——两者都禁无声回落内联打分
(策略 bug 永久遮蔽,2026-09-12 动作 op 规范判读应修②)。局外回落行为
= 机器空键纯通用输出先验排序(与局内未锁态同构)。

单选族交互(实测口径,原执行器注释存档):点卡选中即确认(单步,无
独立确认钮);点卡名带下方一点(y=290,避「查看详情」按钮)。OCR 未读
卡名(变体字型/动画帧)= 未发出通道 round_fail 交回外循环重派,禁
「盲点首卡」兜底(选错不可逆,门 C)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect, _ocr
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenBoxPick(SrOperation):
    """武装箱 4 选 1 选卡画面 op(选卡即终结;单选族例外,screen_op.md §7)。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-备战-武装箱选择'
    #: 卡身点击 y(点卡名下方一点避「查看详情」按钮;2026-08-14 实测,
    #: 自原执行器 CARD_Y 常量平移)
    CARD_Y: ClassVar[int] = 290

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=CwScreenBoxPick.SCREEN_NAME)

    @operation_node(name='武装箱四选一选卡', is_start_node=True,
                    node_max_retry_times=5)
    def handle(self) -> OperationRoundResult:
        """观察四卡 → 选卡决策 → 点卡 → 固定动画等待 → 交回(选卡即终结)。"""
        screen = self.screenshot()
        # 入口锚复验(分发即门,op 内机械复验防误派;锚 miss = 非本画面
        # → fail 交回外循环按画面重分发)
        if not self.round_by_find_area(
                screen, CwScreenBoxPick.SCREEN_NAME, '标识-请选择',
                crop_first=False).is_success:
            return self.round_fail('非武装箱选择画面(标识-请选择 miss)')
        names = self._read_card_names(screen)
        if not names:
            # OCR 未读卡名(变体字型/动画帧)= 未发出通道:交回外循环
            # 重派(重观察语境禁猜),禁盲点首卡兜底(选错不可逆)。
            return self.round_fail('OCR 未读到卡名(变体/动画帧),交回重派')
        idx = self._decide_card_index([n for n, _ in names])
        chosen, choose_x = names[idx]
        card_point = Point(choose_x, CwScreenBoxPick.CARD_Y)
        self.ctx.controller.mouse_move(card_point)   # bug#1 缓解
        self.ctx.controller.click(card_point)        # 点卡选中即确认(实测单步)
        # 固定动画等待(来源写死 = 现役 overlay 动画等待常量;与 CwActionOpenBoxParam
        # 终结化交回等待同源,弹窗/选卡动画就位与否交下一帧观察)
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][boxpick] 选卡 {chosen} → 点击已发(选卡即终结,'
                 '交回外循环)')
        return self.round_success(
            f'选卡 {chosen}(选卡即终结,交回外循环)',
            wait=_OVERLAY_ANIM_WAIT_S)

    def _read_card_names(self, screen) -> list[tuple[str, int]]:
        """OCR 卡名行 → [(卡名, 卡 x 中心)] 按 x 升序(2-8 字过滤,与原
        执行器读卡半逐位同式;识别域 = screen_info 区域-卡名行单一源)。"""
        rect = _area_rect(self.ctx, '区域-卡名行', CwScreenBoxPick.SCREEN_NAME)
        names: list[tuple[str, int]] = []
        if rect is not None:
            for r in _ocr(self.ctx, screen, rect):
                if 2 <= len(r.data) <= 8:
                    names.append((r.data, r.center.x))
        names.sort(key=lambda t: t[1])
        return names

    def _decide_card_index(self, names: list[str]) -> int:
        """选卡决策(决策面原位消费,不搬家):局内 = 策略契约
        ``decide_box_card``(fail-closed:异常留证上抛/越界上抛,禁无声
        回落);局外 = kernel ``pick_equipment`` 机器空键(纯通用输出
        先验排序)。"""
        match = self.ctx.cw_match
        if match is not None:
            try:
                # 写槽 → 零参决策(终态契约 §2.7:写槽以本分支将调用 decide
                # 为前提;同访问覆盖写,三分语义 details §2.3;桩无 gs → 跳过
                # 写,fail-closed 判据照走)。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    ChannelSig,
                )
                if getattr(match, 'gs', None) is not None:
                    match.gs.write_logic(
                        match.gs.box_card_names,
                        list(names),
                        produced_by='CwScreenBoxPick',
                        sig=ChannelSig(family='logic_action',
                                       actor='CwScreenBoxPick',
                                       mode='compute'))
                idx = match.strategy.decide_box_card().idx
            except Exception:   # noqa: BLE001  留证后显式上抛,禁无声回落
                import traceback

                log.error('[cw!][boxpick] decide_box_card 异常(留证后上抛):\n%s',
                          traceback.format_exc())
                raise
            if not (0 <= idx < len(names)):
                raise ValueError(
                    f'decide_box_card 返回越界索引 {idx}(实读卡数 '
                    f'{len(names)});策略契约违约 fail-closed,禁回落内联选卡')
            return idx
        # 局外(无策略面):机器空键 = 纯 base 排序(与局内未锁态同构,
        # 打分单一源 = kernel/cw_equip_value)。
        from sr_od.application.currency_war.kernel.cw_equip_value import (
            pick_equipment,
        )
        return pick_equipment(names)
