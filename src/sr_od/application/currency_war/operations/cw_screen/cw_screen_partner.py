# live-verified 2026-08-13:CwScreenPartner 端到端跑通(step1 候选 click 早前实测;step2 点中心立绘
# (960,300)→「已选择」→ 确认 → overlay 关,live 验)。原自主推进期代码,已 review + live 验,可信。

# r104(2026-08-20):SIFT 立绘识别接入(portrait_plaza 库)——候选真身喂 decide_partner,
# core_chars 匹配真正生效(此前 label 流派名恒不命中 → 恒 idx=0 最左盲点)。

"""货币战争 选择伙伴 overlay 处理 op(从主循环拆出)。

「选择伙伴」overlay 会挡住出战 → stall。OCR 候选阵营标签定位候选 → SIFT 立绘识别
真身 → decide_partner 按策略选 → 点候选立绘选中 → 确认选择。

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(cw_game_ports 两端口完整在场 → 五段生命周期新路径;
缺省 None = 生产直连旧路径,handle 原序列,生产行为零变化 §9.1)。迁移手法
单一源 = 盛会之星先例(CwScreenMegastar,reviews/T-215-r1.md 验收;T-215-r1
§五.5 统一形态注意项 = lifecycle_observe 消费 ``_observation_port()`` 位):
门后选卡+确认链纯移入 ``_handle_overlay``(两路径共享零转录);本屏无
on_outcome 落地登记件(§6.4 收编面无事件屏 chosen 行;chosen_partner =
选择 handler 单次逻辑写入豁免 §2.2/§6.5-6,留守共享体);单轮内完成
选卡→确认→验关,轮次结果自共享体直返(段迹到 act)。本屏 sim 腿 =
不适用(F11 例外清单:sim 无对应画面段,事件浮层族即时落定),等价判据
主承重 = 实机在册行为锁(test_cw_partner_overlay_dispatch + 本批锁
test_cw_obs_arch_event_screens_step3)。
"""
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_events import PartnerOption
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class PartnerObservation:
    """伙伴屏观察 payload(五段之段1产物;试点步骤 3 实机转录形态)。

    observe 段 = 入口门 + 帧引用(候选 OCR/SIFT 读取归共享动作体现役内聚,
    避免新增读屏;实机识别域载体,识别机制不出端口,架构设计 §2.1;sim
    适配器 = 不适用,F11 例外清单)。
    """

    screen: Any = None


class PartnerLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,试点步骤 3)。

    本屏 observe = 入口门已归 ``lifecycle_observe``;适配器仅装配帧引用。
    sim 实现 = 不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenPartner') -> PartnerObservation:
        return op._observe_frame()


class CwScreenPartner(CwScreenOpBase):
    """选择伙伴 overlay:OCR 候选 → 点候选立绘选中 → 确认选择。"""

    # 候选阵营标签行 y 过滤带(候选 label 在 y~362;排除标题 64 / 指令 130 / 详情 445 / 确认 582)。
    # 实测(2026-08-06 1-7 节点):候选 label 护盾/能量 在 y≈362;放宽 [340,400] 容变。
    LABEL_CY_LO: ClassVar[int] = 340
    LABEL_CY_HI: ClassVar[int] = 400
    # 候选 x 过滤带(候选立绘在画面中央 overlay,~450-1550)。**必须过滤 x**:左侧备战面板阵营 label
    # (列车同行/能量/仙舟/213... 在 x~106)也落在候选 y 行 → 不滤 x 会把 board label 当候选 → 点错(2026-08-06
    LABEL_CX_LO: ClassVar[int] = 450
    LABEL_CX_HI: ClassVar[int] = 1550
    # 候选立绘在 label 上方约 60px(label 362 → 立绘 302;实测点 (1127,300) 命中选中)。
    PORTRAIT_DY_ABOVE_LABEL: ClassVar[int] = 60
    # OCR 无候选时兜底(点画面中央立绘区;2026-08-06 实测 2 候选间隙 x≈1010,中央 x=960 可能落间隙,
    # 但兜底比 stall 强;真无候选极少)。⚠️ 待实机核(坐标单一源清点项):
    # 本兜底与 step2 中央立绘 (960,300) 均为实测字面量未 area 化(本批实机
    # 纪律不可测,建档挂账实机批)。
    FALLBACK_PORTRAIT: ClassVar[Point] = Point(960, 300)
    _EXCLUDE: ClassVar[set[str]] = {'选择伙伴', '攻略', '确认选择', '详情', '角色', '装备'}

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-列车同行')
        # 适配器位缺省装配(试点步骤 3;先例 = CwScreenPrep/盛会之星):观察口 =
        # 实机适配器(入口门 + 帧引用封口);动作口 = None = 直连现役共享体
        # ``_handle_overlay``(选卡+确认多步链,无单意图 act 分派面——注入
        # 替位归 sim 接线批与动作回执双协议合流批)。on_outcome 注册表:本屏
        # 无落地登记件(§6.4 收编面无事件屏 chosen 行,见模块 docstring)。
        self._observation_adapter = PartnerLiveObservationAdapter()
        # 确认已发待重入裁决标志(验证废除形态):重入裁决见 handle 顶部
        #(两步链的最终确认也置位,标识不在 = overlay 关 = 链完结)。
        self._confirm_pending: bool = False

    def _observe_frame(self) -> PartnerObservation:
        """轻观察帧装配(实机适配器①封口内容):入口门在 observe 段,
        本方法仅携带当前帧引用(候选读取归共享体现役内聚)。"""
        return PartnerObservation(screen=self.last_screenshot)

    def _read_candidates(self, screen) -> list[tuple[str, int, int]]:
        """OCR 候选 ``(阵营名, label center-x, label center-y)``,按 label 行 y 过滤 + 左→右排序。

        候选 label 是 2-4 字阵营名(护盾/能量/仙舟/列车同行...)在固定 y 行;排除标题/指令/详情等。
        """
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        opts: list[tuple[str, int, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cx = mrl.max.center.x
            cy = mrl.max.center.y
            if (CwScreenPartner.LABEL_CY_LO <= cy <= CwScreenPartner.LABEL_CY_HI
                    and CwScreenPartner.LABEL_CX_LO <= cx <= CwScreenPartner.LABEL_CX_HI
                    and 2 <= len(text) <= 4 and text not in CwScreenPartner._EXCLUDE):
                opts.append((text, cx, cy))
        opts.sort(key=lambda t: t[1])
        return opts

    def _identify_portraits(self, screen, cands: list[tuple[str, int, int]]) -> list[str]:
        """r104:SIFT 立绘识别候选真身(portrait_plaza 库)→ 每候选 char_id(''=未识别)。

        候选立绘区 = label 上方大区域(立绘中心 ≈ label y-60,向上扩 ~200px);
        识别失败回落 label 流派名(旧行为)。真身识别让 decide_partner 的
        core_chars 匹配真正生效(此前 label 名恒不命中 → 恒 idx=0)。
        """
        try:
            from one_dragon.utils import os_utils
            from sr_od.application.currency_war.obs.currency_war_char_id import (
                identify_character,
                load_avatar_templates,
            )
            portrait_dir = Path(os_utils.get_path_under_work_dir(
                'assets', 'template', 'currency_war', 'portrait_plaza'))
            if not portrait_dir.is_dir():
                return [n for n, _cx, _cy in cands]
            templates = load_avatar_templates(portrait_dir)
            out: list[str] = []
            for _name, cx, cy in cands:
                # 立绘区:候选中心上方(立绘主体在 label 上方 ~40-260px 带)
                y1 = max(0, cy - 260)
                y2 = max(y1 + 40, cy - 30)
                x1 = max(0, cx - 110)
                x2 = min(screen.shape[1], cx + 110)
                crop = screen[y1:y2, x1:x2]
                if crop.size == 0:
                    out.append(_name)
                    continue
                cid, _inl = identify_character(crop, templates)
                out.append(cid if cid else _name)
            return out
        except Exception:   # noqa: BLE001  SIFT 失败回落 label 名(旧行为)
            return [n for n, _cx, _cy in cands]

    def _find_text_center(self, screen, text: str) -> Point | None:
        """OCR 找 ``text`` 的 center(没找到 None)。用于「确认选择」定位(避开 round_by_ocr_and_click 的
        bug#1 裸 click —— 改 mouse_move + click)。

        主源 = 建档「按钮-确认选择」rect 约束 OCR(坐标单一真相源 = screen_info;
        命中即该按钮文本实际位置,与全屏 OCR 同帧同词同点)。rect 内未命中
        (布局漂移/step2 异位形态)→ 降级全屏 OCR 兜底腿(原行为,miss 语义不变)。
        """
        _area = self.ctx.screen_loader.get_area('货币战争-列车同行', '按钮-确认选择')
        if _area is not None and _area.pc_rect is not None:
            ocr_map = self.ctx.ocr_service.get_ocr_result_map(
                image=screen, rect=_area.pc_rect, color_range=None, crop_first=False,
            )
            mrl = ocr_map.get(text)
            if mrl and mrl.max:
                return mrl.max.center
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        mrl = ocr_map.get(text)
        if mrl and mrl.max:
            return mrl.max.center
        return None

    @operation_node(name='选择伙伴', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run):
        # cw_game_ports 两端口完整在场(= 测试 harness 显式装配)→ 五段生命
        # 周期新路径;缺省 None = 生产直连旧路径(下方原序列,试点等价门
        # 通过前生产行为零变化)。
        # 重入裁决(观察驱动,验证废除形态)先于分流:确认已发 → 标识不在 =
        # overlay 已关(两步链完结)→ success 交回;标识在 = 确认未落地 →
        # 重走(计节点预算)。
        if self._confirm_pending:
            self._confirm_pending = False
            if not self.round_by_find_area(
                    self.last_screenshot, '货币战争-列车同行',
                    '标识-选择伙伴').is_success:
                return self.round_success(wait=2)
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-列车同行', '标识-选择伙伴').is_success:
            return self.round_fail('非选择伙伴屏')
        return self._handle_overlay(screen)

    def _handle_overlay(self, screen) -> OperationRoundResult:
        """门后选卡+确认链(旧 handle 门后体纯移入,两路径共享零转录;
        试点步骤 3,先例 = 盛会之星 ``_do_action`` 共享式)。chosen_partner
        写端 = 选择 handler 单次逻辑写入豁免留守(§2.2);验关半拆除
        (用户裁定 2026-09-10:动作 op 禁验证)——落地由 handle 顶部重入
        裁决承载,本方法内轮次结果恒 retry/守卫语义。"""
        if not self.round_by_ocr(screen, '已选择').is_success:
            cands = self._read_candidates(screen)
            # r104:SIFT 立绘识别真身 → decide_partner 的 core_chars 匹配真正生效
            # (此前 label 流派名恒不命中 → 恒 idx=0;立绘库/identify_character 基建已有)。
            # 识别失败回落 label 名(旧行为)。
            _char_ids = self._identify_portraits(screen, cands) if cands else []
            options = [PartnerOption(idx=i, char_id=n) for i, n in enumerate(_char_ids)]
            match = self.ctx.cw_match
            idx = 0
            reason = 'no-candidates(fallback)'
            if match is not None and options:
                # 决策输入消费切换(迁移批次二):BoardState 视图
                # (kernel/cw_bs_view.strategy_input_state)替 last_state 直读。
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    board_state_of,
                )
                _state = board_state_of(match.session)
                _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
                pick = match.strategy.decide_partner(options, _state, match.session, _cfg)
                idx = pick.idx if 0 <= pick.idx < len(cands) else 0
                reason = pick.reason
            log.info('[cw-partner] candidates=%s pick=idx%s %s', [o.char_id for o in options], idx, reason)
            # (伙伴候选面存证行已随 exogenous 流写入端退役删除——删除波 1。)
            # r358d(遥测接线):伙伴选择落 session(复盘维度;选中确认后写)。
            if match is not None and options and 0 <= idx < len(options):
                match.session.chosen_partner = options[idx].char_id or ''
                # BoardState 写端(迁移批次二,§3.4.5:各屏选卡写入
                # chosen_*;单次逻辑写入,§3.4 申报豁免)。
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    ChannelSig,
                    board_state_of,
                )
                board_state_of(match.session).write_logic(
                    board_state_of(match.session).chosen_partner,
                    match.session.chosen_partner,
                    produced_by='CwScreenPartner',
                    sig=ChannelSig(family='logic_action',
                                   actor='CwScreenPartner', mode='compute'))
            if cands and 0 <= idx < len(cands):
                _name, cx, cy = cands[idx]
                portrait = Point(cx, cy - CwScreenPartner.PORTRAIT_DY_ABOVE_LABEL)
            else:
                portrait = CwScreenPartner.FALLBACK_PORTRAIT
            self.ctx.controller.mouse_move(portrait)
            self.ctx.controller.click(portrait)
            time.sleep(0.7)
            # 选中态验拆除(验证废除):点立绘后不重读「已选择」判「选中
            # 与否」——下一轮重入由顶部「已选择」观察裁决(未选中 = 重入
            # 重点,计节点预算;观察在动作前 = 合法重判)。
            return self.round_retry('候选立绘点击已发,重入观察裁决', wait=1)
        else:
            log.info('[cw-partner] 已选择态 → 跳 candidate click')
        # bug#1 吞(before_screenshot 移光标)→ overlay 不关 flat-loop(2026-08-06 r6 stall;手动 click 即关)。
        confirm = self._find_text_center(self.screenshot(), '确认选择')
        if confirm is None:
            log.info('[cw-partner] 未找到 确认选择 → round_retry')
            return self.round_retry(wait=1)
        self.ctx.controller.mouse_move(confirm)
        self.ctx.controller.click(confirm)
        time.sleep(1.0)
        # (原「到账登记」ConfirmPartner 块已随 ADR-0651 两态制废除:
        #  chosen_partner 写端 = 候选选中时点的 session 写 + write_logic
        #  直写(本 handler),无挂账登记环节。retry 轮重复确认零副作用。)
        # step2 观察(T#98,伙伴 overlay 两步链):确认后弹出「请选择强化角色」
        # = 还有第二步 → 选强化目标 + 确认(观察分支:发现第二步并处理,
        # 非判效)。step2 确认后不再原地判「overlay 关没关」——统一机械交回,
        # 由 handle 顶部重入裁决(标识不在 = 链完结 → success 交回)。
        if self.round_by_find_area(self.screenshot(), '货币战争-盛会之星',
                                   '按钮-请选择强化角色').is_success:
            # step2 strengthen target = overlay 中心立绘(~960,300;click-test 实锤:非 stage 前排(overlay 覆盖不可点)
            # / 非 bench(不可点)。中心立绘 = 玩家角色 portrait → 点击选中「已选择」→ 确认即关 overlay)。
            target = Point(960, 300)
            log.info(f'[cw-partner] step2 请选择强化角色 → 点中心立绘 {target}')
            self.ctx.controller.mouse_move(target)
            self.ctx.controller.click(target)
            time.sleep(0.7)
            confirm2 = self._find_text_center(self.screenshot(), '确认选择')
            if confirm2 is not None:
                self.ctx.controller.mouse_move(confirm2)
                self.ctx.controller.click(confirm2)
                time.sleep(1.0)
        # 机械交回(验证废除):step1/step2 确认是否落地由下一轮重入裁决
        #(handle 顶部 pending 分支);未落地轮重走已选择态分支(计预算)。
        self._confirm_pending = True
        return self.round_retry(wait=1)

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 3,先例 = 盛会之星)----

    def lifecycle_observe(self
                          ) -> tuple[PartnerObservation,
                                     OperationRoundResult | None]:
        """段1 observe:入口门(标识-选择伙伴,旧 handle 首闸逐位转录)→
        轻观察 payload。门失败 = round_fail 早退(与旧 handle 同 status),
        后续段不执行。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-列车同行', '标识-选择伙伴').is_success:
            return PartnerObservation(screen=screen), self.round_fail('非选择伙伴屏')
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_frame())
        return obs, None

    def lifecycle_decision_cycle(self, payload: PartnerObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作内聚):decide+act 内聚于 ``_handle_overlay`` 共享体
        (候选 OCR/SIFT/决策/遥测/session 写端/到账登记/step2 链全部原位,
        两路径共享零转录)。段5 on_outcome = 本屏无落地登记件(注册表缺席
        = 零动作,见 __init__ 申报);出口验真/轮次结果语义在共享体内逐位
        保留(段迹到 act)。"""
        self._lifecycle_mark('decide')
        rs = self._handle_overlay(payload.screen)
        self._lifecycle_mark('act')
        return rs
