
"""货币战争 补给节点 RunNode(从 ``HandleSupply`` 升级为节点生命周期 owner)。

补给阶段 = 3 选 1 装备 + 确认。RunNode 化后:每轮**验证**"还在补给屏?"(关键词在)→ 点卡身 +
确认 → ``round_retry``;overlay 消失(关键词没了)= 节点完成 → ``round_success``;超预算(点不动)
→ FAIL bail(**不无限烧**,旧 HandleSupply 盲单发失败也回 success → flat loop 无限 round_wait 烧预算)。

动作(T#99 已接 decide_supply):``read_supply_options`` OCR 每列(角色+装备)→ ``decide_supply`` 按
target_comp.key_equips 契合 + 装备通用价值选最优列 → 点该列卡身 + 确认。读不到选项 → CARD_BODY 兜底。
钻(红/蓝=基本赢)视觉判定 + has_diamond 待补;supply 无刷新按钮(decide_supply 传 refresh_used=True)。

T#103:确认按钮进 screen_info(货币战争-补给 按钮-确认);卡身点击点由 read_supply_options 按列返回。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_node_obs import read_supply_options
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.operations.run_nodes.run_node import RunNode
from sr_od.context.sr_context import SrContext


class RunSupplyNode(RunNode):
    """补给节点:点卡身选中 + 确认,**验证 overlay 消失**才完成。"""

    CARD_BODY: ClassVar[Point] = Point(900, 550)  # 补给卡 body 不开对话(沿用 HandleSupply)
    # 刷新按钮(图标式,VLM 判定 + refresh_ui_samples.jsonl 多局稳定坐标;2026-08-17)
    REFRESH_BTN: ClassVar[Point] = Point(974, 854)

    def __init__(self, ctx: SrContext):
        RunNode.__init__(self, ctx, op_name='货币战争-补给节点')
        self._refresh_used = False   # r1 review#1:节点实例态(只刷一次;游戏规则补给可刷 1 次)

    @operation_node(name='补给节点', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        return self._run_node()

    def _in_node(self, screen) -> bool:
        # 还在补给屏 = 标识-补给阶段 area 命中(位置区分,非全屏 LCS:防「补给阶段」与「备战阶段」共享「阶段」误匹配)。
        return self.round_by_find_area(screen, '货币战争-补给', '标识-补给阶段', crop_first=False).is_success

    def _collect_refresh_ui(self, screen) -> None:
        """[采集钩子·临时,采完删]补给屏刷新 UI 标定(缺口1 第三屏;矛盾仲裁)。

        代码注释断言「supply 无刷新按钮」(refresh_used=True 跳过找钻),但游戏规则文档
        (advantage_layouts.md,用户口径)说「补给可刷 1 次(未出钻建议重刷)」—— 用数据仲裁:
        OCR 找「刷新次数N|剩余次数:N」记次数+坐标;整屏 cw_shot_unique 存档(VLM 离线核按钮)。
        有按钮 → refresh_used 改 False + 点击流(ADR-0146 同款);无 → 注释转正实锤。
        """
        try:
            from sr_od.application.currency_war.cw_observe import cw_shot_unique
            cw_shot_unique(screen, 'supply_refresh_ui')
            import re as _re

            ocr_map = self.ctx.ocr_service.get_ocr_result_map(
                image=screen, rect=None, color_range=None, crop_first=False)
            for _t, _m in ocr_map.items():
                _mm = _re.search(r'(?:刷新次数|剩余次数)[：:]?\s*(\d+)', _t)
                if _mm and _m.max is not None:
                    import json as _json
                    from datetime import datetime as _dt
                    from pathlib import Path as _P
                    _p = _P('.debug/temp/currency_war/refresh_ui_samples.jsonl')
                    _p.parent.mkdir(parents=True, exist_ok=True)
                    with _p.open('a', encoding='utf-8') as _f:
                        _f.write(_json.dumps({
                            'ts': _dt.now().isoformat(timespec='seconds'),
                            'kind': 'supply', 'count': int(_mm.group(1)),
                            'text_x': int(_m.max.center.x), 'text_y': int(_m.max.center.y),
                            'text': _t,
                        }, ensure_ascii=False) + '\n')
                    log.info('[cw-supply] 刷新UI采集: %s @(%d,%d)', _t, _m.max.center.x, _m.max.center.y)
                    break
        except Exception:   # noqa: BLE001  采集 best-effort,绝不阻塞补给流程
            pass

    def _do_action(self, screen) -> None:
        self._collect_refresh_ui(screen)
        # T#99 接 decide_supply:OCR 补给选项(每列=角色+装备)→ 策略按 target_comp.key_equips 契合 + 装备
        # 通用价值选(替代盲点 CARD_BODY)。钻识别双通道 ✅(SIFT 主+文本兜底,cw_node_obs)。
        # 刷新按钮 ✅ 实锤(2026-08-17 VLM 判建档图 + refresh_ui_samples 多局数据:图标按钮
        # @≈(974,854),「剩余次数:1」——补给可刷 1 次;旧注释「无刷新按钮」作废,OCR 钩子
        # 找不到是因为按钮是**图标**非文字)。钻重刷链激活:无钻+未刷 → 点刷新重掷。
        opts = read_supply_options(self.ctx, screen)
        match = self.ctx.cw_match
        # r2 review#2:实例态在外环每次新建 RunSupplyNode 下失效 → 挂 match.session
        # (正式字段,非 Optional)读;r10 review#3:getattr 兜底删(拼错字段名会静默
        # False 掩盖接线错误)。无 match 退实例态(测试/离线路径)。
        _refresh_used = match.session._supply_refresh_used if match is not None else self._refresh_used
        target = RunSupplyNode.CARD_BODY
        reason = 'no-options(CARD_BODY 兜底)'
        refresh_target = None
        if match is not None and opts:
            _state = match.session.last_state or GameState()
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = match.strategy.decide_supply(
                [o for o, _ in opts], _state, match.session, _cfg,
                refresh_used=_refresh_used)
            if pick.refresh and not _refresh_used:   # 只刷一次(r1#1+r2#2:session 级)
                refresh_target = RunSupplyNode.REFRESH_BTN
                self._refresh_used = True
                match.session._supply_refresh_used = True
                reason = pick.reason
            elif 0 <= pick.idx < len(opts):
                target = opts[pick.idx][1]
                reason = pick.reason
            log.info('[cw-supply] options=%s pick=idx%s %s click@(%d,%d)',
                     [(o.char, o.equip, o.has_diamond) for o, _ in opts], pick.idx, reason, target.x, target.y)
        else:
            log.info('[cw-supply] opts=%d match=%s → CARD_BODY 兜底', len(opts), match is not None)
        # bug#1 缓解:click 前 mouse_move 到目标(零移动),防 before_screenshot 移光标 → click 落空。
        if refresh_target is not None:
            self.ctx.controller.mouse_move(refresh_target)
            self.ctx.controller.click(refresh_target)
            time.sleep(0.6)   # 等重掷动画;下一轮 loop 重新读选项
            return
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target)
        time.sleep(0.6)
        # 确认(supply 按钮-确认 area;T#103 area 化)
        self.round_by_find_and_click_area(self.screenshot(), '货币战争-补给', '按钮-确认', success_wait=1.5)


