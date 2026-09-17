"""货币战争 星徽秘典四选一画面 op(原 overlay 族内联实现落位,NAMING §2 BookcardOp 行)。

OCR 卡名 → decide_star_tome 选卡(点卡即选,弹窗自关);入口 id_mark 校验 +
出口验真转移 + 完成承诺固定时长(06-overlays §4)。

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(两端口完整在场 → 五段生命周期新路径;缺省 None =
生产直连旧路径,生产行为零变化 §9.1)。迁移手法单一源 = 盛会之星先例
(验收评审统一形态注意项 = lifecycle_observe
消费 ``_observation_port()`` 位):门后读卡+选卡+验关链纯移入
``_handle_overlay``(两路径共享零转录);本屏无 on_outcome 落地登记件
(§6.4 收编面无事件屏 chosen 行;chosen_tome = 出口验真通过分支单次逻辑
直写(write_logic,ADR-0651 两态制),留守共享体;ConfirmTome 逻辑推进
= owned 本体直推,非注册表辖)。本屏 sim 腿 = 不适用(F11 例外清单:sim 无对应画面段,
事件浮层族即时落定),等价判据主承重 = 实机在册行为锁
(test_cw_fake_channels_outerloop 典籍通道真 op 锁 +
test_cw_game_state_consume chosen_tome 锁 + 本批锁
test_cw_obs_arch_event_screens_step3)。
"""
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    safe_click,
)
from sr_od.application.currency_war.operations.cw_screen.cw_flow_const import (
    CW_OVERLAY_SETTLE_S,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class BookcardObservation:
    """星徽秘典观察 payload(五段之段1产物;试点步骤 3 实机转录形态)。

    observe 段 = 入口门 + 帧引用(卡名 OCR 读取归共享动作体现役内聚;实机
    识别域载体,不出端口,架构设计 §2.1;sim 适配器 = 不适用,F11 例外
    清单)。
    """

    screen: Any = None


class BookcardLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,试点步骤 3)。

    本屏 observe = 入口门已归 ``lifecycle_observe``;适配器仅装配帧引用。
    sim 实现 = 不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenBookcard') -> BookcardObservation:
        return op._observe_frame()


class CwScreenBookcard(CwScreenOpBase):
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
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-星徽秘典')
        # 适配器位缺省装配(试点步骤 3;先例 = CwScreenPrep/盛会之星):观察口 =
        # 实机适配器(入口门 + 帧引用封口);动作口 = None = 直连现役共享体
        # ``_handle_overlay``(多步链,无单意图 act 分派面)。on_outcome 注册
        # 表:本屏无落地登记件(§6.4 收编面无事件屏 chosen 行,见模块
        # docstring)。
        self._observation_adapter = BookcardLiveObservationAdapter()
        # 选卡点击已发待重入裁决的星徽名(验证废除形态):重入裁决由入口门
        # 承载(弹窗不在 = 选卡落地)→ 此刻才写 chosen_tome + 到账登记;
        # 弹窗仍在 = 点击未落地 → 重走重选(计节点预算,不留幻影登记)。
        self._pick_pending: str | None = None

    def _observe_frame(self) -> BookcardObservation:
        """轻观察帧装配(实机适配器①封口内容):入口门在 observe 段,
        本方法仅携带当前帧引用(卡名读取归共享体现役内聚)。"""
        return BookcardObservation(screen=self.last_screenshot)

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

    @operation_node(name='星徽秘典', is_start_node=True, node_max_retry_times=5)
    def handle(self) -> OperationRoundResult:
        # 重入裁决(观察驱动,验证废除形态):上轮选卡已发 → 弹窗不在 =
        # 选卡落地 → 补写 chosen_tome + 到账登记 + success 交回;弹窗仍在 =
        # 点击未落地 → 重走(计节点预算)。
        if self._pick_pending is not None:
            _p = self._pick_pending
            self._pick_pending = None
            if not self.round_by_find_area(
                    self.last_screenshot, self.SCREEN_NAME, self.MARK_AREA,
                    crop_first=False).is_success:
                self._settle_picked_tome(_p)
                return self.round_success('星徽秘典选卡完成(重入观察裁决)',
                                          wait=CW_OVERLAY_SETTLE_S)
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run):
        # cw_game_ports 两端口完整在场(= 测试 harness 显式装配)→ 五段生命
        # 周期新路径;缺省 None = 生产直连旧路径(下方原序列,试点等价门
        # 通过前生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success:
            return self.round_fail('非星徽秘典画面')
        return self._handle_overlay(screen)

    def _handle_overlay(self, screen) -> OperationRoundResult:
        """门后读卡+选卡+机械交回链(旧 handle 门后体纯移入,两路径共享零
        转录;试点步骤 3,先例 = 盛会之星 ``_do_action`` 共享式)。验关半
        拆除(用户裁定 2026-09-10):选卡点击发出 → 固定等待 → round_retry,
        落地裁决由 handle 顶部重入入口门承载(chosen/到账登记 = 重入裁决点
        ``_settle_picked_tome``)。"""
        cards = self._read_card_factions(screen)
        idx, pick_name = 0, '(fallback卡1)'
        if cards:
            _match = getattr(self.ctx, 'cw_match', None)
            if _match is not None:
                # 写槽 → 零参决策(终态契约 §2.7:写槽以本分支将调用 decide
                # 为前提;同访问覆盖写,三分语义 details §2.3)。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    ChannelSig,
                )
                _match.gs.write_logic(
                    _match.gs.star_tome_opts,
                    [c[0] for c in cards],
                    produced_by='CwScreenBookcard',
                    sig=ChannelSig(family='logic_action',
                                   actor='CwScreenBookcard', mode='compute'))
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
        safe_click(self, target, tag='cw-flow-bookcard')
        time.sleep(1.0)   # 点卡即选,弹窗自关(现役 0i 实测口径)
        # 机械交回(验证废除):弹窗关没关由下一轮重入入口门裁决
        #(裁决点 = handle 顶部 _pick_pending 分支)。
        self._pick_pending = pick_name
        return self.round_retry('选卡点击已发,重入观察裁决')

    def _settle_picked_tome(self, pick_name: str) -> None:
        """重入裁决出口的登记面(弹窗已关 = 选卡落地):到账登记(§3.3 #28
        ConfirmBook:owned += 星徽)+ chosen_tome 写端。装备名与注册表对齐
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
        # GameState 写端(P3-6 批次二落地审;§3.4.5:星徽秘典弹窗=卡名,
        # 选卡写入 chosen_tome;单次逻辑写入,§3.4 申报豁免;CwScreenMegastar
        # chosen_megastar 同式)。候选读取链在役+建档在册,tome 非「暂无
        # 画面建档」屏——写端自此接通。
        if _sess is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
                game_state_of,
            )
            # 渠道②签名(§3.2.1 ②类属 = op 类名;R5 W1 起必填,ADR-0634)
            game_state_of(_sess).write_logic(
                game_state_of(_sess).chosen_tome,
                pick_name,
                produced_by='CwScreenBookcard',
                sig=ChannelSig(family='logic_action',
                               actor='CwScreenBookcard', mode='compute'))

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 3,先例 = 盛会之星)----

    def lifecycle_observe(self
                          ) -> tuple[BookcardObservation,
                                     OperationRoundResult | None]:
        """段1 observe:入口门(标识-星徽秘典,旧 handle 首闸逐位转录)→
        轻观察 payload。门失败 = round_fail 早退(与旧 handle 同 status),
        后续段不执行。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success:
            return (BookcardObservation(screen=screen),
                    self.round_fail('非星徽秘典画面'))
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_frame())
        return obs, None

    def lifecycle_decision_cycle(self, payload: BookcardObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作内聚):decide+act 内聚于 ``_handle_overlay`` 共享体
        (卡名 OCR/decide_star_tome/近邻锚/点卡/验关/chosen 与到账登记全部
        原位,两路径共享零转录)。段5 on_outcome = 本屏无落地登记件(注册
        表缺席 = 零动作,见 __init__ 申报);出口验真/轮次结果语义在共享体
        内逐位保留(段迹到 act)。"""
        self._lifecycle_mark('decide')
        rs = self._handle_overlay(payload.screen)
        self._lifecycle_mark('act')
        return rs

