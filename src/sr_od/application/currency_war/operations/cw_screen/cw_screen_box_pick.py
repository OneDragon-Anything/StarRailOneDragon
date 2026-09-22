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
独立确认钮);点卡名带下方一点(y=290,避「查看详情」按钮)。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation):
观察 node = 入口锚复验(「标识-请选择」,分发即门,op 内机械复验防误派;
miss 未发 = round_fail 交回外循环按画面重分发)+ OCR 卡名行读数(2-8 字
过滤,x 升序;空 = 变体字型/动画帧读缺 = 未发出通道 round_fail 交回
外循环重派,禁盲点首卡兜底——选错不可逆,读数闸属观察处理)→
``CwScreenBoxPickObs`` → ``report_screen_box_pick_obs`` 写槽
``box_card_names`` 落容器(原决策半内联写点收编;「写槽以本访问将决策
为前提」由门 + 非空闸保证,桩无 gs → 跳过写、决策照走)→ obs 与原始
读数(x 坐标对)挂实例属性进决策动作 node。决策动作 node = 选卡决策
(``_decide_card_index`` 决策半原位消费,失败契约不变)→ 选卡链经
``CwActionPickBoxCardOp`` 派发(pick-op-unify 批:点卡选中即确认 + 动画
等待迁入动作 op)→ 选卡即终结交回(单选族例外,screen_op.md §7;
选卡落地由下一帧观察覆盖,无重入裁决旗标)。
"""
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect, _ocr
from sr_od.application.currency_war.kernel.cw_screen_report.box_pick import (
    CwScreenBoxPickObs,
    report_screen_box_pick_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickBoxCardParam,
)
from sr_od.application.currency_war.prep_actions import _OVERLAY_ANIM_WAIT_S
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
        # 观察结果(观察 node 产物,决策动作 node 消费)。
        self._obs: CwScreenBoxPickObs | None = None
        # OCR 原始读数 [(卡名, 卡 x 中心), ...](x 升序;点击定位要
        # x 坐标,容器槽只收卡名表,x 对留守本 op 不进容器)。
        self._cards: list[tuple[str, int]] = []

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口锚复验 + OCR 卡名 → report 落容器(obs/读数挂实例属性)。

        两道闸(现役单 node 首闸/读数闸逐位平移):锚 miss = 非本画面;
        卡名空 = 未发出通道(变体字型/动画帧)——都 fail 交回外循环重派
        (重观察语境禁猜,禁盲点首卡),report 不调(容器不进盲值)。"""
        screen = self.last_screenshot
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
        self._cards = names
        obs = CwScreenBoxPickObs(on_screen=True,
                                 card_names=[n for n, _ in names],
                                 screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            # 写槽原位调用(原决策半内联写点收编:同访问覆盖写,写点
            # 前提「本访问将决策」由两道闸保证;桩无 gs → 跳过写,
            # fail-closed 判据照走)。
            report_screen_box_pick_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=5)
    def act(self) -> OperationRoundResult:
        """选卡决策 → 选卡链经工厂派发 → 选卡即终结交回。

        pick-op-unify 批:点卡选中即确认 + 动画等待迁入
        ``CwActionPickBoxCardOp``(选卡落地归下一帧观察覆盖);本 op 只
        决策(fail-closed 契约不变)与交回。派发实例携真实选中下标
        (上报 param 即真实选择)。"""
        idx = self._decide_card_index([n for n, _ in self._cards])
        chosen, choose_x = self._cards[idx]
        card_point = Point(choose_x, CwScreenBoxPick.CARD_Y)
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, idx=idx, target=card_point)
        action_op_for(CwActionPickBoxCardParam(idx=idx), self.ctx,
                      _env).execute()
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
        """选卡决策(决策面原位消费,不搬家;写槽半已收编至观察 node 的
        report 调用,本方法只决策):局内 = 策略契约 ``decide_box_card``
        (fail-closed:异常留证上抛/越界上抛,禁无声回落);局外 =
        kernel ``pick_equipment`` 机器空键(纯通用输出先验排序)。"""
        match = self.ctx.cw_match
        if match is not None:
            try:
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
