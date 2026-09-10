
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
钻(红/蓝=基本赢)视觉判定 + has_diamond 待补;刷新按钮实存(REFRESH_BTN 图标式,
decide_supply 规则 2「全无钻+刷新未用→刷新找钻」消费)。

**ADR-0517 适配申报(§8.4 裁决建议按建议落)**:本节点已按单动作架构语义
运转——每轮 ``handle`` = 入口重观察(``_in_node`` 验证 + ``read_supply_options``
现读)→ 单动作决策(``decide_supply`` 一选)→ 执行;**刷新 = 终结 op**(点击
后本动作即返回,``round_retry`` 重进节点 = 入口重建,新装备面由重进后的
选项现读承载——「节点内刷后重读再选」的循环形态与「终结→外循环重进→
入口重建」语义连续)。节点内至多刷 1 次的硬限制由 ``_supply_refresh_used``
session 实态承载(carried 融合:跨外环重建存活,§8.4 与商店 §3.1 对称)。

T#103:确认按钮进 screen_info(货币战争-补给 按钮-确认);卡身点击点由 read_supply_options 按列返回。

**行为等价红线(旧节点基类退役批)**:补给节点流转(节点屏↔补给屏)/committed-but-verifying
语义/node_max_retry_times=8 预算/ADR-0264 关态稳定基线预置,全部原样平移(原基类
_run_node 循环内联进 handle,零行为变更)。

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(cw_game_ports 两端口完整在场 → 五段生命周期新路径;
缺省 None = 生产直连旧路径,handle 原序列,生产行为零变化 §9.1)。迁移手法
单一源 = 盛会之星先例(CwScreenMegastar,reviews/T-215-r1.md 验收):decide+act
内聚于现役动作体 ``_do_action``(detour/刷新/选卡确认三形态,两路径共享零转录);
本屏无 on_outcome 落地登记件(§6.4 收编面无补给行;``supply_refresh_used``
BoardState 字段位 = 先申报禁静默、无写端,cw_board_state.py 字段行自注
「收窄待证」——执行侧防重入旗标 ``_supply_refresh_used`` 留守 _do_action,
不入注册表);chosen_supply 写端 = 出口验真通过分支单次逻辑写入豁免(§2.2/
§6.5-6)留守 observe 门完成分支。节点完成判定 = 下一轮 observe 门 ``_in_node``
复检(观察驱动节点循环,非生命周期验证段——用户裁定 2026-09-10 验证段废除,
confirm 点击系统性不生效 = 动作链 bug 根修动作链)。本屏 sim 腿 = 引擎补给
决策段已在(engine_p1 直调 kernel decide_supply,T5 接口收敛挂账)但本批未
接线(sim 接线批后续),等价判据主承重 = 实机在册行为锁(test_cw_runnode_retire
+ test_cw_board_state_consume + 本批锁 test_cw_obs_arch_event_screens_step3)。
"""
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.obs.cw_node_obs import read_supply_options
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class SupplyObservation:
    """补给屏观察 payload(五段之段1产物;试点步骤 3 实机转录形态)。

    本屏观察轻(B3 族批量「盛会之星型」):observe 段 = 节点完成门
    (``_in_node``;选项读取归 decide 段动作体 ``_do_action`` 现役内聚,
    避免新增读屏)——payload 仅携带帧引用(实机识别域载体,识别机制不出
    端口,架构设计 §2.1;sim 适配器落位 = sim 接线批,本批不建)。
    """

    screen: Any = None


class SupplyLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,试点步骤 3)。

    本屏 observe = 节点完成门已归 ``lifecycle_observe``;适配器仅装配帧
    引用。sim 实现 = sim 接线批辖域,本批不建。
    """

    def observe(self, op: 'CwScreenSupplyNode') -> SupplyObservation:
        return op._observe_frame()


class CwScreenSupplyNode(CwScreenOpBase):
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
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-补给节点')
        self._refresh_used = False   # r1 review#1:节点实例态(只刷一次;游戏规则补给可刷 1 次)
        # 适配器位缺省装配(试点步骤 3;先例 = CwScreenPrep/盛会之星):观察口 =
        # 实机适配器(现役节点完成门 + 帧引用封口);动作口 = None = 直连现役
        # 动作体 ``_do_action``(基类「None = 子类缺省实现自担」;注入替位 =
        # 构造后直接赋值,测试桩)。on_outcome 注册表:本屏无落地登记件
        #(§6.4 收编面无补给行,见模块 docstring 申报;注册表缺席 = 零动作)。
        self._observation_adapter = SupplyLiveObservationAdapter()

    def _observe_frame(self) -> SupplyObservation:
        """轻观察帧装配(实机适配器①封口内容):节点完成门在 observe 段,
        本方法仅携带当前帧引用(选项读取归 ``_do_action`` 现役内聚)。"""
        return SupplyObservation(screen=self.last_screenshot)

    @operation_node(name='补给节点', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        """committed-but-verifying 节点循环(旧基类逻辑内联,零行为变更)。

        每轮:验证完成(已离开本节点画面)→ success;否则做一动作 → round_retry(计预算,超 → FAIL)。
        """
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run):
        # cw_game_ports 两端口完整在场(= 测试 harness 显式装配)→ 五段生命
        # 周期新路径;缺省 None = 生产直连旧路径(下方原序列,试点等价门
        # 通过前生产行为零变化)。判据用装配完整性(安装协议两端口成对),
        # 不新建开关机制(开关生命周期纪律,strategy-work §3)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        screen = self.last_screenshot
        # 验证完成:已不在本节点画面 = overlay 消失 / 进了下一节点 → 节点完成,交还外层。
        if not self._in_node(screen):
            # 出口验真通过(补给屏已关)= 上轮选定确认落地 → 写记录面。
            self._record_chosen_supply()
            # (gate 清尾批 2026-09-03:原此处向已退役的 gate 稳定门预置基线;
            #  wait_stable_frame 在 旧内环拆除后已无生产调用方,基线写端
            #  无读端 → 调用删除。外循环重判兜底,等待语义不变。)
            return self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)')
        # 仍在节点内 = 上轮选定确认未落地 → 丢弃上轮选定暂存(防陈旧选
        # 跨轮/跨节点误写;本轮选定会重新暂存)。
        self._pop_pending_chosen_supply()
        # 仍在节点内 → 做一个动作;round_retry 重跑本节点(计 node_max_retry_times 预算,超 → FAIL bail)。
        self._do_action(screen)
        return self.round_retry(wait=1.5)

    def _pop_pending_chosen_supply(self) -> tuple[str, str, bool] | None:
        """取走补给选定暂存(取即清;无 match = 无会话载体 → None)。"""
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is None:
            return None
        _st = exec_state_of(_match.session)
        _picked = _st._pending_chosen_supply
        _st._pending_chosen_supply = None
        return _picked

    def _record_chosen_supply(self) -> None:
        """出口验真(标识-补给阶段消失)后写 ``chosen_supply``(设计 §3.4.5
        单选事件屏 chosen_* 写端;单次逻辑写入,§3.4 申报豁免)。

        值 = 节点级选定暂存(写点 = _do_action 真选分支;载体与生命周期见
        ``ExecState._pending_chosen_supply``)。暂存空 = 兜底点卡/刷新轮,
        照 chosen_tome 真选守卫不写(None 保持「无记录」)。记录面失败不
        阻塞节点完成。"""
        _picked = self._pop_pending_chosen_supply()
        if _picked is None:
            return
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is None:
            return
        try:
            from sr_od.application.currency_war.kernel.cw_board_state import (
                ChannelSig,
                board_state_of,
            )
            _bs = board_state_of(_match.session)
            _bs.write_logic(_bs.chosen_supply, _picked,
                            produced_by='CwScreenSupplyNode',
                            sig=ChannelSig(family='logic_action',
                                           actor='CwScreenSupplyNode',
                                           mode='compute'))
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞
            log.warning(f'[cw-supply] chosen_supply 记录失败(不阻塞): {e}')

    def _in_node(self, screen) -> bool:
        # 还在补给屏 = 标识-补给阶段 area 命中(位置区分,非全屏 LCS:防「补给阶段」与「备战阶段」共享「阶段」误匹配)。
        return self.round_by_find_area(screen, '货币战争-补给', '标识-补给阶段', crop_first=False).is_success

    def _should_supply_detour(self, match) -> bool:
        """本补给节点还没做过 detour?优先 session 态(跨外环重建存活,
        同 _supply_refresh_used 惯例),无 match 退实例态。"""
        if match is not None:
            return not getattr(exec_state_of(match.session), '_supply_detour_done', False)
        return not getattr(self, '_detour_done', False)

    def _mark_supply_detour(self, match) -> None:
        if match is not None:
            exec_state_of(match.session)._supply_detour_done = True
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
        # ② (detour 采集性 decisions 快照行已随 decisions 流写入端退役删除
        #     ——删除波 1;detour 帧的现役证据 = journal 备战腿派生行。)
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
        _refresh_used = exec_state_of(match.session)._supply_refresh_used if match is not None else self._refresh_used
        target = CwScreenSupplyNode.CARD_BODY
        reason = 'no-options(CARD_BODY 兜底)'
        refresh_target = None
        # 本轮选定快照(选卡确认后合成决策帧的 extra 载荷;None=兜底点卡
        # 路径/刷新路径——决策帧照写但不带选择字段,读端按 None 分型)。
        # 只本地拷贝,不动 _LAST_SUPPLY_PICK 暂存槽(其唯一消费者仍是
        # cw_loop 合成结算行,提前消费=结算行断粮)。
        picked: dict | None = None
        if match is not None and opts:
            # 决策输入消费切换(迁移批次二):BoardState 视图
            # (kernel/cw_bs_view.strategy_input_state)替 last_state 直读。
            from sr_od.application.currency_war.kernel.cw_bs_view import (
                strategy_input_state,
            )
            _state = strategy_input_state(match.session)
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = match.strategy.decide_supply(
                [o for o, _ in opts], _state, match.session, _cfg,
                refresh_used=_refresh_used)
            if pick.refresh and not _refresh_used:   # 只刷一次(r1#1+r2#2:session 级)
                refresh_target = CwScreenSupplyNode.REFRESH_BTN
                self._refresh_used = True
                exec_state_of(match.session)._supply_refresh_used = True
                reason = pick.reason
            elif 0 <= pick.idx < len(opts):
                target = opts[pick.idx][1]
                reason = pick.reason
                # 选定快照(角色/装备/钻;refreshed=刷新是否已用;附实际识别
                # 选项清单)——现役消费方 = 到账登记(equip)。(旧流暂存槽
                # set_last_supply_pick 已随 outcomes 合成行退役删除——删除波 1。)
                _opt = opts[pick.idx][0]
                picked = {'char': _opt.char, 'equip': _opt.equip,
                          'has_diamond': _opt.has_diamond,
                          'refreshed': _refresh_used}
                # BoardState 选定暂存(chosen_supply 出口验真后写端的中转,
                # 设计 §3.4.5):此处只暂存不写——写点在 handle 出口验真
                # (标识-补给阶段消失)通过后,照 chosen_tome「出口验真后写」
                # 口径;重入轮入口会先清本暂存,恒反映最近一次确认尝试。
                exec_state_of(match.session)._pending_chosen_supply = (
                    _opt.char, _opt.equip, _opt.has_diamond)
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
        # (选卡确认后合成 decisions 快照行已随 decisions 流写入端退役删除
        #  ——删除波 1;选定事实现役归宿 = journal chosen 域 + 到账登记。)

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 3,先例 = 盛会之星)----

    def lifecycle_observe(self
                          ) -> tuple[SupplyObservation,
                                     OperationRoundResult | None]:
        """段1 observe:节点完成门(``_in_node``)→ 轻观察 payload。已离开
        本节点画面 = 节点完成,早退交还外层(旧 handle 首闸逐位转录,含
        chosen 写端挂点与完成语义);仍在节点内 = 先弃上轮陈旧选定暂存
        (重入轮入口防跨轮/跨节点误写,旧 handle 语句逐位转录)→ 观察
        payload 交后续段。"""
        screen = self.last_screenshot
        if not self._in_node(screen):
            # 出口验真通过(补给屏已关)= 上轮选定确认落地 → 写记录面。
            self._record_chosen_supply()
            return (SupplyObservation(screen=screen),
                    self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)'))
        # 仍在节点内 = 上轮选定确认未落地 → 丢弃上轮选定暂存(防陈旧选
        # 跨轮/跨节点误写;本轮选定会重新暂存)。
        self._pop_pending_chosen_supply()
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_frame())
        return obs, None

    def lifecycle_decision_cycle(self, payload: SupplyObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作内聚):decide+act 内聚于 ``_do_action`` 现役动作体
        (detour/刷新/选卡确认三形态一次一动作;决策/遥测/session 写端/
        到账登记全部原位,两路径共享零转录)。段5 on_outcome = 本屏无落地
        登记件(注册表缺席 = 零动作,见 __init__ 申报);节点完成判定 =
        下一轮 observe 段 ``_in_node`` 复检(观察驱动节点循环:round_retry
        重入后由观察门读新帧世界事实,非生命周期验证段——用户裁定
        2026-09-10 验证段废除),round_retry 计 node_max_retry_times=8
        预算不变,故段迹到 act 为止。"""
        self._lifecycle_mark('decide')
        _adp = self._action_port()
        if _adp is not None:
            _adp.execute(self, None)   # 注入替位(测试桩);动作体归一
        else:
            self._do_action(payload.screen)
        self._lifecycle_mark('act')
        # 仍在节点内 → round_retry 重跑本节点(计预算,超 → FAIL bail)。
        return self.round_retry(wait=1.5)
