
"""货币战争 补给节点画面 op(旧补给节点执行器退役批内联)。

补给阶段 = 动态 N 选 1 装备 + 确认(通常 4 选 1;「全都要」类效果减 2 列、「人身意外险」类
加补给阶段可增列,augment 改写下实测 3-5 不等——历史「3 选 1」「实测 5」均为特例表述,
列数以 read_supply_options 实际识别为准,禁写死)。**完成验证模型 = op 内验证 + 节点预算**
(NAMING.md §6 选型判据「多步序列/每步可独立失败/历史卡死」侧):每轮**验证**"还在补给屏?"
(关键词在)→ 点卡身 + 确认 → ``round_retry``;overlay 消失(关键词没了)= 节点完成 →
``round_success``;超预算(点不动)→ FAIL bail(**不无限烧**,旧 HandleSupply 盲单发失败
也回 success → flat loop 无限 round_wait 烧预算)。

动作(T#99 已接 decide_supply):``read_supply_options`` OCR 每列(角色+装备)→ ``decide_supply`` 按
target_comp.key_equips 契合 + 装备通用价值选最优列 → 点该列卡身 + 确认。读不到选项 → CARD_BODY 兜底。
钻(红/蓝=基本赢)视觉判定 + has_diamond 待补;supply 无刷新按钮(decide_supply 传 refresh_used=True)。

T#103:确认按钮进 screen_info(货币战争-补给 按钮-确认);卡身点击点由 read_supply_options 按列返回。

**行为等价红线(旧节点基类退役批)**:补给节点流转(节点屏↔补给屏)/committed-but-verifying
语义/node_max_retry_times=8 预算/ADR-0264 关态稳定基线预置,全部原样平移(原基类
_run_node 循环内联进 handle,零行为变更)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.obs.cw_node_obs import read_supply_options
from sr_od.application.currency_war.obs.cw_observation import read_game_state
from sr_od.application.currency_war.telemetry import recorder as cw_telemetry
from sr_od.application.currency_war.telemetry.state import set_last_supply_pick
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenSupplyNode(SrOperation):
    """补给节点:点卡身选中 + 确认,**验证 overlay 消失**才完成。

    选定+确认时点经 cw_telemetry.set_last_supply_pick 暂存选择快照
    (char/equip/has_diamond/refreshed + 实际识别选项清单),供 overlay 消失后
    cw_loop 合成 supply 遥测行消费(synthetic_supply 合成行)。

    **主流程 = 采集 detour 完整循环(坐标 2026-08-27 实机冻结画面实测)**:
    识别补给画面(完成验证锚前置门)→ 点「返回备战界面」(货币战争-补给/
    按钮-返回备战界面,实测有效)→ 备战画面等待快照管线采集(1-2 帧;显式
    phase='supply_detour'+actions=[] 非购买轮语义)→ 点「按钮-返回补给阶段」
    (货币战争-备战,实测有效)重进 overlay(重试 3 次+OCR 文本兜底枪)→
    继续原选择流程。补给轮不驻留备战画面,不 detour 则战斗结算后状态是数据
    真空。实测时序(2026-08-27 冻结画面验证):回备战过渡 ~2.5s、重进过渡
    ~2s;已选择/剩余次数状态重进后保留(实测确认),故采集先行不丢选择进度。
    标记**仅在成功重进后**落(_mark_supply_detour):失败下轮重试整个 detour
    ——宁可见 FAIL bail 不带病把备战屏当补给屏跑(假完成会让外环把采集轮
    当购买轮消化)。
    """

    CARD_BODY: ClassVar[Point] = Point(900, 550)  # 补给卡 body 不开对话(沿用 HandleSupply)
    # 刷新按钮(图标式,VLM 判定 + refresh_ui_samples.jsonl 多局稳定坐标;2026-08-17)
    REFRESH_BTN: ClassVar[Point] = Point(974, 854)
    # detour 实测时序(2026-08-27 实机冻结画面验证):回备战过渡 ~2.5s、
    # 重进 overlay 过渡 ~2s;重进重试上限(area 版),area×3 全 miss 再 OCR 文本
    # 兜一枪(全败=本轮零选择动作交下轮重试整个 detour,标记仅成功后落——
    # 防带病降级成假完成)
    TO_PREP_SETTLE_S: ClassVar[float] = 2.5
    REENTER_SETTLE_S: ClassVar[float] = 2.0
    REENTER_TRIES: ClassVar[int] = 3

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-补给节点')
        self._refresh_used = False   # r1 review#1:节点实例态(只刷一次;游戏规则补给可刷 1 次)

    @operation_node(name='补给节点', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        """committed-but-verifying 节点循环(旧基类逻辑内联,零行为变更)。

        每轮:验证完成(已离开本节点画面)→ success;否则做一动作 → round_retry(计预算,超 → FAIL)。
        """
        screen = self.last_screenshot
        # 验证完成:已不在本节点画面 = overlay 消失 / 进了下一节点 → 节点完成,交还外层。
        if not self._in_node(screen):
            # ADR-0264 方案 B:overlay 关闭(已离开本节点画面)的验证帧
            # 预置为关态稳定基线——外层回备战分支的 gate 跳过「从零等
            # 2 轮」;gate 仍须过一次「锚命中+指纹一致」确认(不裸跳)。
            # best-effort(离线 mock 帧不阻塞)。
            from sr_od.application.currency_war.obs.cw_observation_gate import (
                PROFILE_CLOSED,
                preset_stable_baseline,
            )
            preset_stable_baseline(screen, profile=PROFILE_CLOSED)
            return self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)')
        # 仍在节点内 → 做一个动作;round_retry 重跑本节点(计 node_max_retry_times 预算,超 → FAIL bail)。
        self._do_action(screen)
        return self.round_retry(wait=1.5)

    def _in_node(self, screen) -> bool:
        # 还在补给屏 = 标识-补给阶段 area 命中(位置区分,非全屏 LCS:防「补给阶段」与「备战阶段」共享「阶段」误匹配)。
        return self.round_by_find_area(screen, '货币战争-补给', '标识-补给阶段', crop_first=False).is_success

    def _should_supply_detour(self, match) -> bool:
        """本补给节点还没做过 detour?优先 session 态(跨外环重建存活,
        同 _supply_refresh_used 惯例),无 match 退实例态。"""
        if match is not None:
            return not getattr(match.session, '_supply_detour_done', False)
        return not getattr(self, '_detour_done', False)

    def _mark_supply_detour(self, match) -> None:
        if match is not None:
            match.session._supply_detour_done = True
        else:
            self._detour_done = True

    def _supply_detour_collect(self, match) -> bool:
        """补给备战状态采集 detour(主流程第一步):回备战 → 采集快照 → 重进 overlay。

        标记仅在**成功重进**后落(_mark_supply_detour):失败不落,下轮重试
        整个 detour——宁可见节点预算烧尽 FAIL bail,不带病把备战屏当补给屏
        继续跑(假完成会让外环误派购买管线 = 采集轮变购买轮)。
        """
        # ① 返回备战界面(area 已建 + 实测有效:currency_war_supply 按钮-返回备战界面,
        #    2026-08-27 实机验证 → 备战画面出现;过渡 ~2.5s)
        rs = self.round_by_find_and_click_area(
            self.screenshot(), '货币战争-补给', '按钮-返回备战界面', success_wait=1.5)
        if rs is None or not rs.is_success:
            log.warning('[cw-supply] detour:「返回备战界面」点击 miss → 放弃本次采集')
            return False
        time.sleep(CwScreenSupplyNode.TO_PREP_SETTLE_S)
        # ② 显式采集性返回快照(标记 phase='supply_detour';actions=[] 非购买轮)
        try:
            _snap_screen = self.screenshot()
            # ADR-0462:已点「返回备战界面」+ settle = 干净备战帧 → P1 全量基线读
            _state = read_game_state(self.ctx, _snap_screen, phase='prep_clean')
            cw_telemetry.record_decision(
                _state, target_comp='', candidate_scores={}, eval_breakdown={},
                actions=[], gold_point=True,
                extra={'phase': 'supply_detour'})
            log.info('[cw-supply] detour 备战快照已落盘 p%sr%s hp=%s gold=%s',
                     getattr(_state, 'plane', '?'), getattr(_state, 'round_num', '?'),
                     getattr(_state, 'hp', '?'), getattr(_state, 'gold', '?'))
        except Exception as e:   # noqa: BLE001  观测不阻塞对局
            log.warning('[cw-supply] detour 快照记录失败(不阻塞): %s', e)
        # ③ 重进 overlay(实测:已选择/剩余次数状态重进后保留;备战屏「按钮-返回补给
        #    阶段」area 已建 + 实测有效;过渡 ~2s。area 全 miss 再用全屏 OCR 文本兜
        #    一枪——lcs_percent=0.8 防与「返回货币战争」误匹配)
        for i in range(CwScreenSupplyNode.REENTER_TRIES):
            rr = self.round_by_find_and_click_area(
                self.screenshot(), '货币战争-备战', '按钮-返回补给阶段',
                success_wait=1.5)
            time.sleep(CwScreenSupplyNode.REENTER_SETTLE_S)
            if rr is not None and rr.is_success and self._in_node(self.screenshot()):
                log.info('[cw-supply] detour 完成:回到补给界面(第 %d 次尝试)', i + 1)
                self._mark_supply_detour(match)
                return True
            if i == CwScreenSupplyNode.REENTER_TRIES - 1:
                self.round_by_ocr_and_click(self.screenshot(), '返回补给阶段',
                                            success_wait=1.5, lcs_percent=0.8)
                time.sleep(CwScreenSupplyNode.REENTER_SETTLE_S)
                if self._in_node(self.screenshot()):
                    log.info('[cw-supply] detour 完成:OCR 文本兜底回到补给界面')
                    self._mark_supply_detour(match)
                    return True
        log.warning('[cw!][cw-supply] detour:area×%d + OCR 兜底均未回到补给界面'
                    '(下轮重试;若持续=节点预算耗尽 FAIL bail)', CwScreenSupplyNode.REENTER_TRIES)
        return False

    def _do_action(self, screen) -> None:
        # T#99 接 decide_supply:OCR 补给选项(每列=角色+装备,动态列数)→ 策略按
        # target_comp.key_equips 契合 + 装备通用价值选(替代盲点 CARD_BODY)。钻识别双通道
        # ✅(SIFT 主+文本兜底,cw_node_obs);刷新按钮 @≈(974,854),无钻+未刷 → 点刷新重掷。
        match = self.ctx.cw_match
        # 主流程:首次进入先做备战状态采集 detour(detour 后用新帧读选项;
        # 未成功重进 → 本轮不做任何选择动作,防在备战屏盲点卡身/误触发购买语义)
        if self._should_supply_detour(match):
            if not self._supply_detour_collect(match):
                return
            screen = self.screenshot()
        opts = read_supply_options(self.ctx, screen)
        # r2 review#2:实例态在外环每次新建 op 下失效 → 挂 match.session
        # (正式字段,非 Optional)读;r10 review#3:getattr 兜底删(拼错字段名会静默
        # False 掩盖接线错误)。无 match 退实例态(测试/离线路径)。
        _refresh_used = match.session._supply_refresh_used if match is not None else self._refresh_used
        target = CwScreenSupplyNode.CARD_BODY
        reason = 'no-options(CARD_BODY 兜底)'
        refresh_target = None
        # 本轮选定快照(选卡确认后合成决策帧的 extra 载荷;None=兜底点卡
        # 路径/刷新路径——决策帧照写但不带选择字段,读端按 None 分型)。
        # 只本地拷贝,不动 _LAST_SUPPLY_PICK 暂存槽(其唯一消费者仍是
        # cw_loop 合成结算行,提前消费=结算行断粮)。
        picked: dict | None = None
        if match is not None and opts:
            _state = match.session.last_state or GameState()
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = match.strategy.decide_supply(
                [o for o, _ in opts], _state, match.session, _cfg,
                refresh_used=_refresh_used)
            if pick.refresh and not _refresh_used:   # 只刷一次(r1#1+r2#2:session 级)
                refresh_target = CwScreenSupplyNode.REFRESH_BTN
                self._refresh_used = True
                match.session._supply_refresh_used = True
                reason = pick.reason
            elif 0 <= pick.idx < len(opts):
                target = opts[pick.idx][1]
                reason = pick.reason
                # 选定+确认时点暂存选择快照(角色/装备/钻;refreshed=刷新
                # 是否已用),供 overlay 消失后 cw_loop 合成 supply 行消费。
                # 附**实际识别到的选项清单**(动态列数,不假定结构)——
                # 合成行与逐列内容对拍/漏读审计数据源。
                _opt = opts[pick.idx][0]
                picked = {'char': _opt.char, 'equip': _opt.equip,
                          'has_diamond': _opt.has_diamond,
                          'refreshed': _refresh_used,
                          'options': [{'char': o.char, 'equip': o.equip,
                                       'has_diamond': o.has_diamond}
                                      for o, _p in opts],
                          'n_options': len(opts)}
                set_last_supply_pick(_opt.char, _opt.equip, _opt.has_diamond,
                                     refreshed=_refresh_used,
                                     options=picked['options'])
            log.info('[cw-supply] options=%s pick=idx%s %s click@(%d,%d)',
                     [(o.char, o.equip, o.has_diamond) for o, _ in opts], pick.idx, reason, target.x, target.y)
        else:
            log.info('[cw-supply] opts=%d match=%s → CARD_BODY 兜底', len(opts), match is not None)
        # bug#1 缓解:click 前 mouse_move 到目标(零移动),防 before_screenshot 移光标 → click 落空。
        if refresh_target is not None:
            self.ctx.controller.mouse_move(refresh_target)
            self.ctx.controller.click(refresh_target)
            # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
            # #19,2026-09-02):补给屏刷新后 2s 画面稳定——原 0.6s 依赖「下一轮
            # wait 1.5s」合计 2.1s,余量仅 0.1s,重掷动画尾帧可能被读(选项读缺
            # → 决策建立在残缺选项上)。等满 2s 再返回。
            time.sleep(2.0)
            return
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target)
        time.sleep(0.6)
        # 确认(supply 按钮-确认 area;T#103 area 化)
        self.round_by_find_and_click_area(self.screenshot(), '货币战争-补给', '按钮-确认', success_wait=1.5)
        # 到账登记(§3.3 #18 ConfirmSupply):owned += 选中装备名(粗粒度
        # expected,单轮即回备战覆盖点实读清账;equip 未读到 = 无 item 不登记)。
        if match is not None and picked is not None and picked.get('equip'):
            from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
                register_confirm_arrival,
            )
            register_confirm_arrival(match.session, 'ConfirmSupply',
                                     picked['equip'],
                                     produced_by='CwScreenSupplyNode')
        # 补给轮决策帧(w941 判定:备战采集 detour 整局一次 → 后续补给轮
        # 恒零 decisions 行,轮窗边界模糊)。选卡确认后补记一帧合成快照:
        # 确认成功时点 overlay 已消 → 帧面=干净备战帧(read_game_state
        # prep_clean 同 detour 形态)。phase='supply_pick' = 本帧来源标注
        # (decisions 行无 source 字段——source='synthetic_supply' 是结算行
        # 词汇,telemetry/schema.py 本批禁碰;读端按 phase 分型)。
        # gold_point=False:gold_trajectory 每回合一采样,首补给轮 detour 帧已
        # 采过,本帧不重复入轨。观测失败不阻塞对局。
        try:
            _post_screen = self.screenshot()
            _post_state = read_game_state(self.ctx, _post_screen, phase='prep_clean')
            # 决策帧字段对齐(观察层数据移交批):选定快照进 extra
            # (supply_pick 键,形状与暂存槽一致)——决策行不再只有
            # 空壳快照,「这轮补给选了什么/牌面给了什么」单行可读,
            # 不用等 outcomes 合成行 join。观测失败不阻塞对局。
            _extra: dict = {'phase': 'supply_pick'}
            if picked is not None:
                _extra['supply_pick'] = dict(picked)
            cw_telemetry.record_decision(
                _post_state, target_comp='', candidate_scores={}, eval_breakdown={},
                actions=[], gold_point=False,
                extra=_extra)
            log.info('[cw-supply] 选卡确认后快照已落盘 p%sr%s hp=%s gold=%s',
                     getattr(_post_state, 'plane', '?'),
                     getattr(_post_state, 'round_num', '?'),
                     getattr(_post_state, 'hp', '?'), getattr(_post_state, 'gold', '?'))
        except Exception as e:   # noqa: BLE001  观测不阻塞对局
            log.warning('[cw-supply] 选卡确认后快照记录失败(不阻塞): %s', e)
