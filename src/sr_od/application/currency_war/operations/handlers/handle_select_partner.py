# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 选择伙伴 overlay 处理 op(从主循环拆出)。

「选择伙伴」overlay 会挡住出战 → stall。OCR 候选阵营标签定位候选 → 点候选立绘选中 → 确认选择。
必须在「确认选择/巨星」(RunMegastarNode)之前判断 —— 选择伙伴也有「确认选择」但候选是
stage 立绘(横排,阵营 label 行),非巨星的左候选(822,333)。

TODO:策略化选伙伴(按 target_comp.core_chars 评估候选,现取最左)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_decisions import PartnerOption
from sr_od.application.currency_war.cw_state import GameState
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleSelectPartner(SrOperation):
    """选择伙伴 overlay:OCR 候选 → 点候选立绘选中 → 确认选择。"""

    # 候选阵营标签行 y 过滤带(候选 label 在 y~362;排除标题 64 / 指令 130 / 详情 445 / 确认 582)。
    # 实测(2026-08-06 1-7 节点):候选 label 护盾/能量 在 y≈362;放宽 [340,400] 容变。
    LABEL_CY_LO: ClassVar[int] = 340
    LABEL_CY_HI: ClassVar[int] = 400
    # 候选 x 过滤带(候选立绘在画面中央 overlay,~450-1550)。**必须过滤 x**:左侧备战面板阵营 label
    # (列车同行/能量/仙舟/213... 在 x~106)也落在候选 y 行 → 不滤 x 会把 board label 当候选 → 点错(2026-08-06
    # 复看 OCR 发现 D-60 初版漏 x 过滤)。
    LABEL_CX_LO: ClassVar[int] = 450
    LABEL_CX_HI: ClassVar[int] = 1550
    # 候选立绘在 label 上方约 60px(label 362 → 立绘 302;实测点 (1127,300) 命中选中)。
    PORTRAIT_DY_ABOVE_LABEL: ClassVar[int] = 60
    # OCR 无候选时兜底(点画面中央立绘区;2026-08-06 实测 2 候选间隙 x≈1010,中央 x=960 可能落间隙,
    # 但兜底比 stall 强;真无候选极少)。
    FALLBACK_PORTRAIT: ClassVar[Point] = Point(960, 300)
    _EXCLUDE: ClassVar[set[str]] = {'选择伙伴', '攻略', '确认选择', '详情', '角色', '装备'}

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-选择伙伴')

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
            if (HandleSelectPartner.LABEL_CY_LO <= cy <= HandleSelectPartner.LABEL_CY_HI
                    and HandleSelectPartner.LABEL_CX_LO <= cx <= HandleSelectPartner.LABEL_CX_HI
                    and 2 <= len(text) <= 4 and text not in HandleSelectPartner._EXCLUDE):
                opts.append((text, cx, cy))
        opts.sort(key=lambda t: t[1])
        return opts

    def _find_text_center(self, screen, text: str) -> Point | None:
        """OCR 找 ``text`` 的 center(没找到 None)。用于「确认选择」定位(避开 round_by_ocr_and_click 的
        bug#1 裸 click —— D-64 改 mouse_move + click)。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        mrl = ocr_map.get(text)
        if mrl and mrl.max:
            return mrl.max.center
        return None

    @operation_node(name='选择伙伴', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-选择伙伴', '标识-选择伙伴').is_success:
            return self.round_fail('非选择伙伴屏')
        # D-61:已选择态(上轮选了没确认 / overlay 复现)→ 跳 candidate click(避免反取消);否则点 candidate。
        if not self.round_by_ocr(screen, '已选择').is_success:
            cands = self._read_candidates(screen)
            # T#99 接 decide_partner:候选 label 作 char_id 尽力匹配 target_comp.core_chars / 偏好。
            # ⚠️ 候选只有立绘、无角色名(label 是流派/role,非角色名;视觉大模型 2026-08-07 核实)→ char_id 多为
            # label → 多不命中 core_chars → idx=0(最左)。**真正接决策需 SIFT 立绘识别**(同 read_bench_chars,
            # CW 立绘库)喂真角色名 = 后续子项(候选位置视觉不稳,需 CV 卡框 / 多样本定网格)。
            options = [PartnerOption(idx=i, char_id=n) for i, (n, _cx, _cy) in enumerate(cands)]
            match = self.ctx.cw_match
            idx = 0
            reason = 'no-candidates(fallback)'
            if match is not None and options:
                _state = match.session.last_state or GameState()
                _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
                pick = match.strategy.decide_partner(options, _state, match.session, _cfg)
                idx = pick.idx if 0 <= pick.idx < len(cands) else 0
                reason = pick.reason
            log.info('[cw-partner] candidates=%s pick=idx%s %s', [o.char_id for o in options], idx, reason)
            if cands and 0 <= idx < len(cands):
                _name, cx, cy = cands[idx]
                portrait = Point(cx, cy - HandleSelectPartner.PORTRAIT_DY_ABOVE_LABEL)
            else:
                portrait = HandleSelectPartner.FALLBACK_PORTRAIT
            # D-64(bug#1 缓解):click 前 mouse_move(零移动),防 before_screenshot 移光标 → click 落空。
            self.ctx.controller.mouse_move(portrait)
            self.ctx.controller.click(portrait)
            time.sleep(0.7)
            # D-61(ADR-0009):验「已选择」才算选中;未选中 → retry(计 node_max_retry 兜底,不盲目 success)。
            if not self.round_by_ocr(self.screenshot(), '已选择').is_success:
                log.info('[cw-partner] candidate click 未选中(无「已选择」)→ round_retry')
                return self.round_retry(wait=1)
        else:
            log.info('[cw-partner] 已选择态 → 跳 candidate click')
        # 确认(D-64:mouse_move + click 缓解 bug#1 + 验 overlay 关)。原 round_by_ocr_and_click 的 click 被
        # bug#1 吞(before_screenshot 移光标)→ overlay 不关 flat-loop(2026-08-06 r6 stall;手动 click 即关)。
        confirm = self._find_text_center(self.screenshot(), '确认选择')
        if confirm is None:
            log.info('[cw-partner] 未找到 确认选择 → round_retry')
            return self.round_retry(wait=1)
        self.ctx.controller.mouse_move(confirm)
        self.ctx.controller.click(confirm)
        time.sleep(1.0)
        # D-64(ADR-0009):验 overlay 关(选择伙伴 消失 = 推进);没关 → 分情况。
        if self.round_by_ocr(self.screenshot(), '选择伙伴').is_success:
            # T#98:step 2「请选择强化角色」→ 点 stage 角色(前排-1)→ 确认(partner overlay 两步;
            # 旧码只做 step 1 select candidate → confirm,step 2 select strengthen target 缺 → flat-loop)。
            if self.round_by_find_area(self.screenshot(), '货币战争-巨星强化', '按钮-请选择强化角色').is_success:
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
                if self.round_by_find_area(self.screenshot(), '货币战争-选择伙伴', '标识-选择伙伴').is_success:
                    log.info('[cw-partner] step2 后 overlay 仍在 → round_retry')
                    return self.round_retry(wait=1)
                log.info('[cw-partner] step2 完成 → overlay 关')
                return self.round_success(wait=2)
            log.info('[cw-partner] 确认后 overlay 仍在 → round_retry(confirm 未落地,bug#1)')
            return self.round_retry(wait=1)
        return self.round_success(wait=2)
