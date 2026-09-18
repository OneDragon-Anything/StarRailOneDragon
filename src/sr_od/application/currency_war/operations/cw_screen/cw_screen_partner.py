# 机制更正(2026-09-15 实机事故,详见 docs/game/screens/currency_war_choose_partner.md):
# 旧「选中态 gate」= 全屏 OCR 找「已选择」(LCS 阈值按关键词归一,3 字词与
# 本屏常驻的指令长句/「请选择强化角色」共享子序列「选择」即达 0.5)→ 本屏
# 恒误命中,op 恒跳过点选、对置灰确认钮原样重试 → P1-r1 十八连 fail 卡死
# (确认钮置灰被游戏拒绝)。本版废除选中态读数,改「点选候选 → 确认」脉冲 +
# overlay 关闭完成门(推进信号 = 标识消失,不依赖任何未实锤的选中态呈现);
# 未选中态正判定 = 建档「提示-请选择强化角色」区域命中(置灰伴随文案)。

# r104(2026-08-20):SIFT 立绘识别接入(portrait_plaza 库)——候选真身喂 decide_partner,
# core_chars 匹配真正生效(此前 label 流派名恒不命中 → 恒 idx=0 最左盲点)。

"""货币战争 选择伙伴 overlay 处理 op(从主循环拆出)。

「选择伙伴」overlay 会挡住出战 → stall。OCR 候选阵营标签定位候选 → SIFT 立绘识别
真身 → decide_partner 按策略选 → 「点选候选 → 确认」脉冲(同轮先点选后确认,
确认被拒形态有界重试,见 ``_handle_overlay``)→ overlay 关 = 完成门(标识消失)。

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(cw_game_ports 两端口完整在场 → 五段生命周期新路径;
缺省 None = 生产直连旧路径,handle 原序列,生产行为零变化 §9.1)。迁移手法
单一源 = 盛会之星先例(CwScreenMegastar,验收评审统一形态注意项 = lifecycle_observe 消费 ``_observation_port()`` 位):
门后选卡+确认链纯移入 ``_handle_overlay``(两路径共享零转录);本屏无
on_outcome 落地登记件(§6.4 收编面无事件屏 chosen 行;chosen_partner =
选择 handler 单次逻辑写入豁免 §2.2/§6.5-6,留守共享体);轮次结果自共享体
直返(段迹到 act)。本屏 sim 腿 =
不适用(F11 例外清单:sim 无对应画面段,事件浮层族即时落定),等价判据
主承重 = 实机行为锁(test_cw_obs_arch_event_screens_step3 迁移结构锁 +
test_cw_partner_select_confirm_flow 选选流序/确认被拒有界重试锁)。
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
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
    """选择伙伴 overlay:OCR 候选 → decide_partner 选 → 「点选候选→确认」脉冲 → 标识消失 = 完成。"""

    # 候选阵营标签行 y 过滤带(候选 label 在 y~362;排除标题 64 / 指令 130 / 详情 445 / 确认 582)。
    # 实测(2026-08-06 1-7 节点):候选 label 护盾/能量 在 y≈362;放宽 [340,400] 容变。
    LABEL_CY_LO: ClassVar[int] = 340
    LABEL_CY_HI: ClassVar[int] = 400
    # 候选 x 过滤带(候选立绘在画面中央 overlay,~450-1550)。**必须过滤 x**:左侧备战面板阵营 label
    # (列车同行/能量/仙舟/213... 在 x~106)也落在候选 y 行 → 不滤 x 会把 board label 当候选 → 点错(2026-08-06
    LABEL_CX_LO: ClassVar[int] = 450
    LABEL_CX_HI: ClassVar[int] = 1550
    # 确认被拒脉冲上限:未选中提示持续在场时,「点选→确认」脉冲达到该次数即
    # 显式 round_fail 交外环重判(禁原样无限重试;2026-09-15 实机卡死形态的
    # 针对性防线。取值 < 节点预算 10,先于预算耗尽给出精确失败原因)。
    CONFIRM_REJECT_MAX: ClassVar[int] = 4
    # screen_info area 名(currency_war_partner.yml;坐标单一真相源)。
    A_CANDIDATE_STRIP: ClassVar[str] = '候选-卡区'
    A_UNSELECTED_HINT: ClassVar[str] = '提示-请选择强化角色'
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
        # 选定点位(本执行内一次决策缓存):重入轮复用同点位重点选,不重跑
        # SIFT/决策/session 写(单执行内点位稳定,防跨轮决策抖动换候选)。
        self._pick_point: Point | None = None
        # 「点选→确认」脉冲计数(确认被拒防线的有界重试预算,见 CONFIRM_REJECT_MAX)。
        self._confirm_pulses: int = 0

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
        (布局漂移)→ 降级全屏 OCR 兜底腿(原行为,miss 语义不变)。
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

    def _unselected_hint_present(self, screen) -> bool:
        """未选中态正判定:建档「提示-请选择强化角色」区域命中。

        该提示 = 确认钮置灰态的伴随文案(区域约束 OCR,rect 内无他词,无
        全屏 LCS 误匹配面)。选中态呈现在档材料零实拍(旧档「已选择文字 +
        高亮边框」记载经像素比对证伪,见 screen doc)→ 只把提示在场作
        「确定未选中」的正判定,选中与否不作读数判定 —— 推进语义由
        「点选→确认」脉冲 + overlay 关闭完成门承载。
        """
        return self.round_by_find_area(
            screen, '货币战争-列车同行', CwScreenPartner.A_UNSELECTED_HINT,
        ).is_success

    def _pick_point_for(self, cand: tuple[str, int, int]) -> Point | None:
        """候选点击点位:x = 候选 label 中心(运行时动态,随候选数分布),
        y = 建档「候选-卡区」带中心(坐标单一真相源)。区域缺失 = None,
        调用方显式失败(禁裸坐标兜底)。

        两帧实测(2026-09-15 事故帧 1-1 与 1-9 档 fixture)卡带 y≈165-440,
        带中心 y≈302 落立绘区内;旧 offset「label cy-60」实点 y≈315,恰在
        立绘底边(~307)下方卡体死区 —— 点击几何不可靠的根源之一,故 y
        改由建档带锚定,布局漂移可经 analyze_screen 对账暴露。
        """
        area = self.ctx.screen_loader.get_area(
            '货币战争-列车同行', CwScreenPartner.A_CANDIDATE_STRIP)
        if area is None or area.pc_rect is None:
            return None
        _name, cx, _cy = cand
        return Point(cx, (area.pc_rect.y1 + area.pc_rect.y2) // 2)

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
        """门后「点选候选 → 确认」脉冲链(两路径共享零转录;先例 = 巨星
        ``_do_action`` 选卡一次 + 重确认形态)。chosen_partner 写端 = 选择
        handler 单次逻辑写入豁免留守(§2.2);落地判定由 handle 顶部重入
        裁决承载(标识不在 = overlay 关 = 完成),本方法内轮次结果恒
        retry/守卫语义。

        每轮脉冲(机制出处 = 模块头更正注):
        1. 未选中提示在场(置灰实锤)∧ 脉冲已达上限 → 显式 fail(确认被拒
           形态有界重试,禁原样无限重试烧预算/烧外环);
        2. 首轮决策一次(候选 OCR/SIFT/decide/session 写)定同一点位;
        3. 提示在场(含重入轮)= 未选中实证 → 点候选卡(单选语义重点
           已选卡无反选面;提示不在 = 不重点选,防未知选中呈现被扰动);
        4. 点确认(bug#1 缓解 = mouse_move + click);确认是否落地由下一轮
           重入裁决,不原地判选中态。"""
        unselected = self._unselected_hint_present(screen)
        if unselected and self._confirm_pulses >= CwScreenPartner.CONFIRM_REJECT_MAX:
            log.info('[cw-partner] 确认被拒形态:未选中提示持续在场 %s 轮 → 显式失败交外环',
                     self._confirm_pulses)
            return self.round_fail(
                '伙伴确认被拒(未选中提示持续在场,确认钮置灰;候选选中未生效)')
        if self._pick_point is None:
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
                # 写槽 → 零参决策(终态契约 §2.7:写槽以本分支将调用 decide
                # 为前提;同访问覆盖写,三分语义 details §2.3)。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    ChannelSig,
                )
                match.gs.write_logic(
                    match.gs.partner_opts,
                    list(options),
                    produced_by='CwScreenPartner',
                    sig=ChannelSig(family='logic_action',
                                   actor='CwScreenPartner', mode='compute'))
                pick = match.strategy.decide_partner()
                idx = pick.idx if 0 <= pick.idx < len(cands) else 0
                reason = pick.reason
            log.info('[cw-partner] candidates=%s pick=idx%s %s', [o.char_id for o in options], idx, reason)
            # r358d(遥测接线):伙伴选择落容器(chosen_partner,gs 单一源
            # ——终态契约 §B:session 份退役;选中确认后写)。
            if match is not None and options and 0 <= idx < len(options):
                # GameState 写端(迁移批次二,§3.4.5:各屏选卡写入
                # chosen_*;单次逻辑写入,§3.4 申报豁免)。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    ChannelSig,
                )
                match.gs.write_logic(
                    match.gs.chosen_partner,
                    options[idx].char_id or '',
                    produced_by='CwScreenPartner',
                    sig=ChannelSig(family='logic_action',
                                   actor='CwScreenPartner', mode='compute'))
            if not cands or not (0 <= idx < len(cands)):
                # 无候选(OCR 未命中任何候选标签)= 无可依据的选中点 →
                # 显式失败交外环重判,禁兜底盲点中央坐标(该点可能落在候选
                # 间隙点空,静默重入空转;坐标单一真相源)。
                return self.round_fail('伙伴屏无候选(OCR 未命中候选标签),禁兜底盲点')
            point = self._pick_point_for(cands[idx])
            if point is None:
                # 建档缺失(候选-卡区 area 不在)= 无建档依据的选中点 →
                # 显式失败(坐标单一真相源,禁裸坐标兜底;补档走 MCP 工具)。
                return self.round_fail('伙伴屏建档缺失:候选-卡区(禁裸坐标兜底)')
            self._pick_point = point
        # 「点选候选 → 确认」脉冲链经工厂(统一动作工厂批4:体迁
        # ``cw_overlay_pick_action.PartnerPickOp``,方法级替身缝保留)。
        # 决策半(候选 OCR/SIFT/decide/chosen 写端/确认被拒守卫/点位解析)
        # 留守上方;选中态标记与脉冲计数宿主仍是本 op,经 env.op 消费。
        # 派发实例仅作注册表解析键(机械输入 = unselected 实证 + 本 op
        # 状态,经 env 传递)。
        from sr_od.application.currency_war.kernel.cw_vocab import (
            CwActionPickPartnerParam,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, unselected=unselected)
        action_op_for(CwActionPickPartnerParam(idx=0), self.ctx,
                      _env).execute()
        return _env.round_result

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
        (候选 OCR/SIFT/决策/遥测/session 写端/「点选→确认」脉冲链全部原位,
        两路径共享零转录)。段5 on_outcome = 本屏无落地登记件(注册
        表缺席 = 零动作,见 __init__ 申报);出口验真/轮次结果语义在共享体
        内逐位保留(段迹到 act)。"""
        self._lifecycle_mark('decide')
        rs = self._handle_overlay(payload.screen)
        self._lifecycle_mark('act')
        return rs
