"""货币战争 星徽秘典四选一画面 op(原 overlay 族内联实现落位,NAMING §2 BookcardOp 行)。

OCR 卡名 → decide_star_tome 选卡(点卡即选,弹窗自关);入口 id_mark 校验 +
出口验真转移 + 完成承诺固定时长(06-overlays §4)。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两
段直继承 SrOperation。观察 node = 入口门(标识-星徽秘典,miss = round_fail
交回外循环重判)+ 卡阵营名一次读(全屏 OCR「X星徽」去后缀,x 升序;入口帧
一次读,与现役决策体读同帧等价)→ ``report_screen_bookcard_obs`` 落容器
``star_tome_opts``(空候选不写,闸在 report 内)→ obs 挂实例属性进决策
node。决策动作 node = 重入裁决顶部(选卡点击已发 → 弹窗不在 = 选卡落地
→ 此刻才写 chosen_tome + 到账登记 + success 交回;在 = 点击未落地 → 清
标志重走重选)→ 决策从容器零参读 → 点卡(星徽卡-N area 近邻锚)→
round_wait 循环(不烧节点重试预算,无防御上限)。chosen_tome 与 ConfirmTome
到账登记 = 重入裁决点留守(动作事实边界,不进 report;ConfirmTome 逻辑
推进 = owned 本体直推);本屏 sim 腿 = 不适用(sim 无对应画面段,事件浮层
族即时落定),等价判据主承重 = 实机在册行为锁(test_cw_game_state_consume chosen_tome 锁 +
test_cw_screen_two_node_family 形态锁;典籍通道真 op 锁补档 =
开放设计注,见 screens/bookcard.md §9)。
"""
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.bookcard import (
    CwScreenBookcardObs,
    report_screen_bookcard_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickStarTomeParam,
)
from sr_od.application.currency_war.operations.cw_screen.cw_flow_const import (
    CW_OVERLAY_SETTLE_S,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenBookcard(SrOperation):
    """星徽秘典四选一:OCR 卡名 → decide_star_tome 选卡(点卡即选,弹窗自关)。

    现役逻辑内联在 cw_loop 0i 分支(无独立 handler op),本批按现役读法直写:
    全屏 OCR 取「XX星徽」名 → 策略打分(target 阵营/board 已有/配方框架),
    无命中 fallback 卡1(06-overlays §4:决策待定,策略归口批 B 定)。
    点击坐标走 screen_info 星徽卡-1..4 area(OCR x 近邻匹配 area,不硬编码)。
    """

    SCREEN_NAME: ClassVar[str] = '货币战争-星徽秘典弹窗'
    MARK_AREA: ClassVar[str] = '标识-星徽秘典'
    CARD_AREAS: ClassVar[tuple[str, ...]] = ('星徽卡-1', '星徽卡-2', '星徽卡-3', '星徽卡-4')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-星徽秘典')
        # 选卡点击已发待重入裁决的星徽名(验证废除形态):重入裁决由决策
        # 动作 node 顶部承载(弹窗不在 = 选卡落地)→ 此刻才写 chosen_tome
        # + 到账登记;弹窗仍在 = 点击未落地 → 重走重选(不留幻影登记)。
        self._pick_pending: str | None = None
        # 观察结果(观察 node 产物,决策动作 node 消费)与候选原始坐标
        # (点卡 x 近邻锚输入,不入 obs 契约)。
        self._obs: CwScreenBookcardObs | None = None
        self._cards: list[tuple[str, int]] = []

    def _read_card_factions(self, screen) -> list[tuple[str, int]]:
        """全屏 OCR 取「XX星徽」卡名 → [(阵营名, x 中心)] 左→右(现役 0i 读法)。"""
        ocr = self.ctx.ocr_service.get_ocr_result_list(screen, crop_first=False)
        cards: list[tuple[str, int]] = []
        for o in ocr:
            t = (o.data or '').strip()
            if t.endswith('星徽') and len(t) > 2:
                cards.append((t[:-2], o.x + o.w // 2))
        cards.sort(key=lambda c: c[1])
        return cards

    def _card_point(self, idx: int, faction_x: int | None) -> Point | None:
        """卡身点击点 = 星徽卡-N area 中心;OCR x 已知时取 x 近邻 area(防 area 序与画面序错位)。"""
        centers: list[Point] = []
        for area in self.CARD_AREAS:
            pt = area_center(self.ctx, area, self.SCREEN_NAME)
            if pt is None:
                return None
            centers.append(pt)
        if faction_x is not None:
            idx = min(range(len(centers)),
                      key=lambda i: abs(centers[i].x - faction_x))
        return centers[idx]

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + 卡阵营名一次读 → report 落容器。

        门 miss = round_fail 早退(与现役首闸同 status,交回外循环重判)。
        门后卡名 OCR 一次读 → ``report_screen_bookcard_obs``(空候选不写,
        闸在 report 内);match/gs 缺席的局外兜底路径跳过 report(决策走
        决策面 fallback 分支,分支原样)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success:
            return self.round_fail('非星徽秘典画面')
        cards = self._read_card_factions(screen)
        obs = CwScreenBookcardObs(on_screen=True,
                                  options=[c[0] for c in cards],
                                  screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_bookcard_obs(_gs, obs)
        self._obs = obs
        self._cards = cards
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=5)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 零参决策 → 点卡 → round_wait。

        重入裁决(观察驱动,验证废除形态):上轮选卡已发 → 弹窗不在 =
        选卡落地 → 补写 chosen_tome + 到账登记 + success 交回;弹窗仍在 =
        点击未落地 → 重走(重读重选)。"""
        if self._pick_pending is not None:
            _p = self._pick_pending
            self._pick_pending = None
            if not self.round_by_find_area(
                    self.last_screenshot, self.SCREEN_NAME, self.MARK_AREA,
                    crop_first=False).is_success:
                self._settle_picked_tome(_p)
                return self.round_success('星徽秘典选卡完成(重入观察裁决)',
                                          wait=CW_OVERLAY_SETTLE_S)
        cards = self._cards
        idx, pick_name = 0, '(fallback卡1)'
        if cards:
            _match = getattr(self.ctx, 'cw_match', None)
            if _match is not None:
                # 零参决策(写槽已由 report 落容器 star_tome_opts;决策调用
                # 形态不变)。
                _decided = _match.strategy.decide_star_tome().idx
                if 0 <= _decided < len(cards):
                    idx, pick_name = _decided, cards[_decided][0]
        # 近邻匹配锚 = 选中卡的 OCR x(决策后取,防把候选首位当选中位)
        faction_x = cards[idx][1] if idx < len(cards) else None
        target = self._card_point(idx, faction_x)
        if target is None:
            return self.round_fail('星徽秘典缺「星徽卡-N」建档')
        log.info('[cw-flow-bookcard] 候选=%s → 选 %s @(%s,%s)',
                 [c[0] for c in cards] or 'OCR未读到', pick_name, target.x, target.y)
        # 选卡链经工厂(pick-op-unify 批:点卡即选机械链迁入
        # ``CwActionPickStarTomeOp``,本 op 只决策;定位点决策半现算经 env
        # 显式传入)。派发实例携真实选中下标(上报 param 即真实选择;
        # fallback = 0)。
        # 机械交回(验证废除):弹窗关没关由下一轮重入裁决(本方法顶部
        # _pick_pending 分支),chosen_tome/ConfirmTome 到账随裁决出口。
        # round_wait 推进循环(不烧节点重试预算,无防御上限)。
        self._pick_pending = pick_name
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, idx=idx, target=target)
        action_op_for(CwActionPickStarTomeParam(idx=idx), self.ctx,
                      _env).execute()
        return self.round_wait('选卡点击已发,重入观察裁决')

    def _settle_picked_tome(self, pick_name: str) -> None:
        """重入裁决出口的登记面(弹窗已关 = 选卡落地):到账登记(ConfirmTome:
        owned += 星徽)+ chosen_tome 写端。装备名与注册表对齐
        「X星徽」(OCR 卡名已去「星徽」后缀作阵营名,回拼;已是全名则原样)。"""
        if not pick_name or pick_name == '(fallback卡1)':
            return
        from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
            register_confirm_arrival,
        )
        _eq_name = pick_name if pick_name.endswith('星徽') else f'{pick_name}星徽'
        _sess = getattr(getattr(self.ctx, 'cw_match', None), 'session', None)
        register_confirm_arrival(_sess, 'ConfirmTome', _eq_name,
                                 produced_by='CwScreenBookcard')
        # GameState 写端(chosen_tome = 卡名,选卡落地后写;单次逻辑写入,
        # 申报豁免;CwScreenMegastar chosen_megastar 同式)。候选读取链在役
        # +建档在册,tome 非「暂无画面建档」屏——写端自此接通。
        if _sess is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
                game_state_of,
            )
            # 渠道②签名(②类属 = op 类名;R5 W1 起必填,ADR-0634)
            game_state_of(_sess).write_logic(
                game_state_of(_sess).chosen_tome,
                pick_name,
                produced_by='CwScreenBookcard',
                sig=ChannelSig(family='logic_action',
                               actor='CwScreenBookcard', mode='compute'))
