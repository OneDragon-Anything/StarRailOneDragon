
"""货币战争 投资策略 3 选 1 op(从主循环拆出)。

OCR 3 张投资策略卡名 → 经 ``match.strategy.decide_invest``(委托 ``cw_events.decide_event``
打分)→ 点**最优**卡 + 确认。替代原"盲点中卡"(无策略)。

逐卡刷新执行链(T-162 重立,ADR-0600;旧 ADR-0146 刷新流曾随 ADR-0519 C10 整段删除):
``decide_event`` 帧级触发(零阈值结构判据:全精确分类 ∧ 无 S1/S2 ∧ max_N≠1,
推导见 ADR-0600 §3.2 + math_proofs P81)→ 返回 ``refresh_slots``
→ 逐槽读计数(现读 >0)→ 文本锚定点刷新圆钮 → 验效双通道 → 重读重分类 →
**用最终名集重调 decide_invest**(G1:重决策只经 flow.decide_invest 入口,
D*① 三参只在此解析;handler 禁直调 kernel 判据)→ 按最终决策选卡。投资策略屏
刷新是**逐卡刷新**(每卡独立按钮、独立计数,归档帧对实证);失败安全 = 停止
刷新照常选当前最优(与遭遇屏同款)。已发射槽集挂 ``exec_state_of(session)``
(局容器级),复位 = visit 起点单点(实例首帧入口锚验通过后清空)。

卡名按行过滤(2026-08-04 snap 实测):标题「请选择投资策略」顶(y≈98)、卡名中(y≈490,
center)、描述下(y≈520+)、「刷新次数1」底(y≈841)、「确认」底(y≈983);取 y≈490 行
短文本(2-8 字)即 3 张卡名,按 center-x 排序左→右。

点击 mechanics(2026-08-04 实测):点卡名(y≈474)**不选中**(疑似开详情,bot 点名 540+ 次从没
选中 → 确认灰 → 卡死 18min)→ 点**描述区**(CARD_CLICK_Y=545)才选中(同 invest_env:name 不
选中、描述区选中)。选中 → 确认。decide_event 仅用 state.board,投资策略 overlay 时 board 不可
读 → 空 board stub。

CARD_CLICK_Y + 确认坐标进 screen_info(``currency_war_invest_strategy``):``区域-卡牌描述行``
+ ``按钮-确认``,task#20 已完成;本 op 经 ``cw_obs_core.area_center`` 读,缺失才用兜底常量。
"""
import time
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_comps import augment_affinity
from sr_od.application.currency_war.kernel.cw_events import (
    decide_event,
    is_economy_engine,
)
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_investments import (
    get_strategy,
    is_blood_economy,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.obs.cw_node_obs import (
    pair_refresh_counts_to_slots,
    read_invest_refresh_counts,
)
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    confirm_and_verify,
    safe_click,
)
from sr_od.application.currency_war.telemetry import recorder, schema
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def _guard_classify(name: str, config) -> tuple[bool, bool, bool, bool]:
    """刷新链逐步守卫的单名分类(ADR-0600 §3.3;D*-free,纯函数可单测)。

    返回 ``(exact, blood, forbidden, top)``:
    - exact = 策略注册表归一后精确命中(轴钉死:环境名/形变名 → False = 不可
      分类,消费方停链 fail-closed——与 kernel 帧级闸同一严格轴);
    - blood/forbidden = F2 唯一 L1 守卫输入(L1 = 非血∧非禁);
    - top = 顶级判定(S1 定义型 ∨ S2 经济引擎档),新卡达顶级 → 链停(三选一
      已定,后续刷新边际为零)。
    帧级 D*-dependent 判据(对齐档 N/max_N)只在 kernel:handler 禁直调 kernel
    判据算刷新建议(G1——直调会丢 D*① 三参换基),本 helper 只服务执行期守卫
    与中断检查,不产决策。
    """
    st = get_strategy(name)
    forbidden = any(p in name
                    for p in (getattr(config, 'strategy_forbid', None) or []))
    if st is None:
        return False, False, forbidden, False
    blood = is_blood_economy(st.economy)
    top = bool(augment_affinity(name)) or is_economy_engine(st.economy)
    return True, blood, forbidden, top


class CwScreenInvestStrategy(SrOperation):
    """投资策略 3 选 1:OCR 卡名 → decide_invest 决策 → (按需逐卡刷新)→ 点最优卡 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-投资策略'   # screen_info 画面(currency_war_invest_strategy.yml)
    # 卡选中点击 Y:screen_info「区域-卡名行」center.y(=卡名选中行);常量=兜底。
    # V4.4 实测(2026-08-05,↺ 推翻 I16「卡底 820 选中」):**点卡名(y≈474)选中**(白边 + 确认亮)。
    # 实机点验:点中产阶级卡名(461,474) → 白边选中 → 点确认 → 推进备战 1-3(链路通)。
    # I16「卡底 820 才选中」错 —— 820 是刷新区/卡底,点没选中 → handle 点 820 不选中 → loop 反复卡死投资策略
    # (整局阻塞,实跑暴露)。旧 doc(2026-08-04「描述区 545 选中」/ I16「卡底 820」)均过时。
    CARD_CLICK_Y: ClassVar[int] = 474   # 兜底(卡名选中);首选 area_center('区域-卡名行')
    # 卡名行 center-y 过滤带(标题 y≈98 / 描述 y≈520+ / 刷新次数 y≈841 / 确认 y≈983)
    NAME_CY_LO: ClassVar[int] = 465
    NAME_CY_HI: ClassVar[int] = 505
    _EXCLUDE: ClassVar[set[str]] = {'请选择投资策略', '攻略', '返回备战界面', '图例', '确认', '刷新次数1'}
    # 确认按钮:screen_info「按钮-确认」center(task#20);常量=兜底。
    CONFIRM: ClassVar[Point] = Point(978, 983)   # 兜底;首选 area_center('按钮-确认')
    #: 入口锚复探窗(动画帧容忍,治本 20/21 局同型失败 2026-09-06 01:41:30 /
    #: 02:22:28「返回状态 非投资策略屏」):投资策略节点首访时派发帧 → 本 op
    #: 首帧之间落在「备战 → 金币过场动画 → overlay 淡入」过渡段(screen_flow_timing.md
    #: #11),首帧采样可 miss「标识-请选择投资策略」;旧实现单探测 miss 即
    #: round_fail(round_fail 不吃 node_max_retry_times,直接炸出整 op),外层
    #: 重试才自愈但每次触发哨兵报警+退出。修法与 cw_loop._invest_overlay_dispatch
    #: 同族(复探=短窗+新截图):首探 miss → 短窗后新截图复探,窗口内命中即
    #: 继续;超窗仍 miss 才 round_fail(防无限等真非目标屏)。决策记录 =
    #: ADR-0529。执行层时序常量(沿 CwLoop.INVEST_REPROBE_WAIT 先例),非策略数值。
    ENTRY_REPROBE_TIMES: ClassVar[int] = 4
    ENTRY_REPROBE_WAIT_S: ClassVar[float] = 0.8
    # 逐卡刷新圆钮 = 「刷新次数N」文本中心 + 固定偏移(ADR-0600 §3.4 文本锚定;
    # 单帧证据不足判文本漂移形态,固定 area 不可行——遭遇屏 _REFRESH_BTN_DX
    # 先例)。偏移实测收口(V7,归档帧 sr-od-test/screens/货币战争-投资策略/
    # default.webp CV 环亮像素质心):钮心 x≈{388,887,1386}、计数文本中心
    # x≈{477,975,1474}(y 同带 ≈855)→ dx ≈ −88。偏移错 → 验效双输 →
    # 失败安全照常选(能力退化非事故,复测即修)。
    _REFRESH_BTN_DX: ClassVar[int] = -88
    # 刷新后等待(执行层时序常量,非策略数值,沿 ADR-0529 先例;screen_flow_timing
    # #13:刷新动画 ~1s,旧实现 1.5s 覆盖)。
    REFRESH_ANIM_WAIT_S: ClassVar[float] = 1.5

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-投资策略')
        self._ocr_map: dict | None = None   # _read_options 存全图 OCR(ADR-0132 效果采集复用,零额外 OCR)
        # visit 起点单点复位旗标(实例级;ADR-0600 §3.3 复位语义/G6):实例首帧(入口锚验
        # 通过后)清一次 exec_state 已发射槽集,同 visit 重入(round_retry 同
        # 实例)不再清——防重入保留,跨 visit(新实例)必清。
        self._visit_reset_done: bool = False

    def _read_options(self, screen) -> list[tuple[str, int, int]]:
        """OCR 3 张卡的 ``(名字, center-x, center-y)``,按卡名行 y 过滤 + 左→右排序。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        self._ocr_map = ocr_map   # ADR-0132:采集复用(同一帧 OCR,不重跑)
        opts: list[tuple[str, int, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            if (CwScreenInvestStrategy.NAME_CY_LO <= cy <= CwScreenInvestStrategy.NAME_CY_HI
                    and 2 <= len(text) <= 8 and text not in CwScreenInvestStrategy._EXCLUDE):
                opts.append((text, mrl.max.center.x, cy))
        opts.sort(key=lambda t: t[1])
        return opts

    def _entry_anchor_hit(self, screen: MatLike) -> bool:
        """入口锚探测:screen_info id_mark「标识-请选择投资策略」命中(与
        cw_loop 0e 分发 / cw_entry 2b 分支同锚同源)。"""
        return self.round_by_find_area(
            screen, CwScreenInvestStrategy.SCREEN_NAME, '标识-请选择投资策略',
        ).is_success

    def _ensure_entry_screen(self) -> bool:
        """入口锚判定 + 动画帧复探(语义见 ENTRY_REPROBE_* 注):首帧 miss →
        短窗后新截图复探,窗口内命中即 True;超窗仍 miss 返回 False(调用方
        才报失败,防无限等真非目标屏)。"""
        screen = self.last_screenshot
        hit = self._entry_anchor_hit(screen)
        for _ in range(CwScreenInvestStrategy.ENTRY_REPROBE_TIMES):
            if hit:
                return True
            # 复探等待走可中断睡眠:裸 time.sleep 最坏 3.2s 不可停机中断,
            # 绕过框架停机加固(operation.py 停机延迟实证)。
            self._interruptible_sleep(CwScreenInvestStrategy.ENTRY_REPROBE_WAIT_S)
            screen = self.screenshot()
            hit = self._entry_anchor_hit(screen)
        # 末次复探结果必须消费:循环内 if 只判上一轮采样,最后一次采样的
        # 命中若不在此返回,会被整体丢弃(三审 off-by-one:锚恰在窗口末拍
        # 出现仍误报失败——恰是本复探窗要容忍的形态边缘)。
        return hit

    @operation_node(name='投资策略', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        if not self._ensure_entry_screen():
            # 超窗走 round_retry 而非 round_fail(二次治本,2026-09-06
            # 04:16:38 实证复探窗 3.2s 仍不够覆盖个别过渡段):retry 消耗
            # node_max_retry_times 预算有界自愈,且不产生 ERROR 行——
            # round_fail 会炸出整 op 并触发哨兵报警退出(20-22 局实证
            # 每次 fail 一次哨兵退出)。ADR-0529 原「拒 fail→retry」的
            # 前提(外层重试等价)被实证推翻,重审结论见 ADR 修订。
            return self.round_retry('投资策略屏未稳定,复探超窗重试')
        # visit 起点单点复位(ADR-0600 §3.3 复位语义/G6):实例首帧(入口锚验通过后)清空
        # exec_state 已发射槽集——三车道全覆盖:①同 visit 重入(round_retry
        # 同实例,本旗标已置位)不清 → 防重入保留;②失败终止 → 预算耗尽 op
        # 终止 → 下一 visit 新实例天然清,陈旧集不泄入;③确认成功 → 本 visit
        # 终结,下 visit 必清。旗标唯一职责 = 同 visit 防重入;「可否再刷」
        # 权威判定 = 逐卡计数现读(双保险不同源,观察赢规则照常辖)。
        if not self._visit_reset_done:
            self._visit_reset_done = True
            _m0 = self.ctx.cw_match
            if _m0 is not None:
                exec_state_of(_m0.session)._invest_refresh_used_slots.clear()
        screen = self.last_screenshot

        # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
        # #11,2026-09-02):「请选择投资策略」标题出现 1s 后画面(三卡)才稳定
        # (流转 = 备战 → 金币过场动画 → overlay 自动弹出)——入口帧可能在
        # 稳定期内,立即读刷新次数/卡名有读缺风险。等 1s 重截稳定帧再读
        # (与 cw_screen_invest_env #3 修复同型)。
        time.sleep(1.0)
        screen = self.screenshot()

        opts = self._read_options(screen)
        _first_ocr_map = self._ocr_map   # 首帧 OCR 存底(刷新链读缺时采集回退用,G10)
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        names = [n for n, _x, _y in opts]
        # 不可读 → 传空 GameState(decide_event 只用 board 判 DoT 克制,空 board = 不惩罚,安全)。
        match = self.ctx.cw_match
        if names:
            if match is not None:
                # ADR-0144:真状态替空 stub。决策输入消费切换(迁移批次二):
                # 值源 = BoardState 视图(cw_bs_view.strategy_input_state)。
                from sr_od.application.currency_war.kernel.cw_bs_view import (
                    strategy_input_state,
                )
                pick = match.strategy.decide_invest('strategy', names, strategy_input_state(match.session), match.session, config)
            else:
                # 防御:无 match(局外独立跑)。ADR-0519 C6/C9 后 decide_event 不读
                # hp/品质惩罚,hp 字段仅为 GameState 构造完整性。**显式跳过刷新链**
                # (ADR-0600 §3.3 防御路径):刷新链依赖 exec_state_of(match.session) 与
                # match 上下文,局外防御帧零行为增量(refresh_slots 不消费)。
                pick = decide_event(names, config, GameState(hp=100, hp_readable=True))
        else:
            pick = None

        # ===== 逐卡刷新执行链(ADR-0600 §3.3;参照 cw_screen_encounter live 先例:
        # 文本锚定钮 + 验效双通道 + 发射即置位防重入)=====
        _refreshed_slots: list[int] = []
        _refresh_noeffect = False
        _names_updated = False
        if (match is not None and pick is not None and pick.refresh_slots
                and opts):
            _ex = exec_state_of(match.session)
            _counts = read_invest_refresh_counts(self.ctx, screen, 'strategy')
            _slot_hits = (pair_refresh_counts_to_slots(
                _counts, [x for _n, x, _y in opts])
                if _counts else [None] * len(opts))
            for _i in pick.refresh_slots:
                if _i >= len(opts):
                    continue
                # 闸 1:逐卡计数现读 >0(权威闸,无缓存无假设口径——读缺按
                # 无授予处理,失败安全;预注册锁 10,ADR-0600 §5)。
                _hit = _slot_hits[_i] if _i < len(_slot_hits) else None
                if _hit is None or _hit[0] <= 0:
                    continue
                # 闸 2:同 visit 防重入(发射即记;复位 = visit 起点单点)。
                if _i in _ex._invest_refresh_used_slots:
                    continue
                # 闸 3:F2 唯一 L1 槽守卫(逐步重估:每步按当前名集重算——
                # 覆盖 L1={A,B} 刷 A 后 B 成唯一的序贯形态,预注册锁 14,ADR-0600 §5)。
                _l1_now = [j for j, (_ex_flag, _b, _f, _t) in
                           enumerate(_guard_classify(n, config) for n in names)
                           if _ex_flag and not _b and not _f]
                if _l1_now == [_i]:
                    continue
                # 点钮:该槽「刷新次数N」文本中心 + 偏移(safe_click 带 bug#1
                # mouse_move 缓解,遭遇屏同款)。
                _tx, _ty = _hit[1], _hit[2]
                safe_click(self, Point(_tx + CwScreenInvestStrategy._REFRESH_BTN_DX, _ty),
                           tag='cw-strat')
                _ex._invest_refresh_used_slots.add(_i)   # 发射即记(防重入优先,不等验效)
                time.sleep(CwScreenInvestStrategy.REFRESH_ANIM_WAIT_S)
                # 验效双通道(遭遇屏先例):①计数扣减(权威——次数由游戏扣,
                # 卡面碰巧同签名也认);②卡名签名变化(兜底)。双输 = 未生效
                # (点偏/无授予)→ 停止刷新照常选当前最优,不重试(失败安全)。
                _after = self.screenshot()
                _counts2 = read_invest_refresh_counts(self.ctx, _after, 'strategy')
                _slot2 = (pair_refresh_counts_to_slots(
                    _counts2, [x for _n, x, _y in opts])
                    if _counts2 else [None] * len(opts))
                _hit2 = _slot2[_i] if _i < len(_slot2) else None
                _opts2 = self._read_options(_after)   # 刷后重读全帧卡名(验效② + G10 采集)
                _eff = (_hit2 is not None and _hit2[0] < _hit[0]) or (
                    len(_opts2) == len(opts) and _opts2[_i][0] != names[_i])
                if not _eff:
                    _refresh_noeffect = True
                    self._ocr_map = _first_ocr_map   # 采集回退首帧(读缺帧不进 _cards)
                    log.warning(f'[cw-strat] 槽{_i}刷新未生效(计数 {_hit[0]}→'
                                f'{_hit2[0] if _hit2 is not None else None},卡名未变;'
                                f'点偏或无授予)→ 停止刷新照常选(失败安全)')
                    break
                # 生效:以刷后帧为当前事实(重读帧本就全帧 OCR,_ocr_map 已同步
                # 指向刷后帧 → G10 采集「刷后集合」成立);新卡重分类。
                if len(_opts2) != len(opts):
                    # 刷后帧读缺(碎片/过渡帧):刷新已生效(计数通道确认)但
                    # 新名不可知 → 名集不更新、不重决策(G1 语义:重决策必须用
                    # 最终名集,陈旧名 = 幻影卡),链停照常选(失败安全;采集
                    # 回退首帧)。
                    _refreshed_slots.append(_i)
                    self._ocr_map = _first_ocr_map
                    log.warning(f'[cw-strat] 槽{_i}刷新生效但刷后帧读缺'
                                f'(opts2={len(_opts2)})→ 停止刷新照常选(失败安全)')
                    break
                opts = _opts2
                names = [n for n, _x, _y in opts]
                _refreshed_slots.append(_i)
                _names_updated = True
                _new_exact, _nb, _nf, _ntop = _guard_classify(names[_i], config)
                if not _new_exact:
                    # 遇不可分类新卡(形变/env 名)即停:重决策帧级闸会 fail-closed,
                    # 刷新动作不回滚(已耗次数不回收),选卡走现状路径(残扫 #2)。
                    log.info(f'[cw-strat] 槽{_i}新卡不可分类({names[_i]!r})→ 停止刷新')
                    break
                if _ntop:
                    # 新卡达 S1/S2(顶级)→ 三选一已定,后续刷新边际为零,链停。
                    log.info(f'[cw-strat] 槽{_i}新卡达顶级({names[_i]!r})→ 停止刷新')
                    break
            if _names_updated:
                # 用最终名集重调 decide_invest(G1:重决策只经 flow 入口——
                # D*① 三参在此解析,handler 直调 kernel 判据会丢参换 D* 基;
                # 单帧锁 13 辖)。
                # 重算出的 refresh_slots 丢弃(每槽至多刷一次 + 链已停,ADR-0600 §3.3)。
                # CommitSignals 双喂为既有 telemetry 累积器零决策消费,判读侧按
                # 「同 visit 多次喂入」口径读(ADR-0600 §3.3 申报,禁为消重复改 flow)。
                pick = match.strategy.decide_invest(
                    'strategy', names, strategy_input_state(match.session),
                    match.session, config)

        if pick is not None and 0 <= pick.option_idx < len(opts):
            chosen, choose_x, choose_y = opts[pick.option_idx]
            reason = pick.reason
        elif opts:
            chosen, choose_x, choose_y, reason = opts[0][0], opts[0][1], opts[0][2], 'fallback(no-decision)'
        else:
            chosen, choose_x, choose_y, reason = '?', 920, 490, 'fallback(no-ocr)'
        # 刷新遥测后缀(零新通道,遭遇屏先例同构:逐槽后缀 + 未生效标记)。
        if _refreshed_slots:
            reason = reason + ''.join(f'+槽{i}刷新' for i in _refreshed_slots)
        if _refresh_noeffect:
            reason = f'{reason}+refresh-noeffect'
        log.info(f'[cw-strat] options={names} chose={chosen!r}@({choose_x},{choose_y}) reason={reason}')
        # 持卡注入面(session.active_strategies)的 append 已移至确认成功后
        #(本文件尾块;ADR-0598 幻影卡收口)——旧时序 append 先于点卡确认,
        # 确认失败轮(session.active_strategies 是息帽 resolved 链的输入源)
        # 留下幻影卡:幻影买断制 = 息线全关,比幻影 9/10 更烈。
        # ADR-0132 采集:候选全集 + 效果原文(描述带 y 505-835,排除卡名行/确认/刷新次数 UI)按卡分桶
        # → invest_cards.jsonl;未注册名告警(注册表只 T0 子集,315 长尾靠采集渐进补全)。
        # G10(ADR-0600 §3.3):发生刷新时 opts/_ocr_map 已指向刷后重读帧 → 本采集
        # = 刷后集合(chosen 按最终集合)——「版本感知额外收益」与 F6 事后再核对
        # 账锚两个申报的载体。**采集 = 实际所见帧**:多槽复合路径(前槽生效+后槽
        # 验效双输/读缺)下 _ocr_map 回退首帧而 opts/names 保持上一生效刷后帧,
        # 此时 effect_text 桶可能保留前帧描述、卡名恒准——遥测面混合口径,申报
        # 接受(落地审 F-B,ADR-0600 §4),不扩代码。
        _items = [(t, m.max.center.x, m.max.center.y)
                  for t, m in (self._ocr_map or {}).items() if m.max is not None]
        _anchors = [(i, x) for i, (_n, x, _y) in enumerate(opts)]
        _buckets = schema.bucket_card_texts(_anchors, _items,
                                                  CwScreenInvestStrategy.NAME_CY_HI, 835)
        _cards = [{"idx": i, "name": n, "x": x,
                   "effect_text": " | ".join(_buckets.get(i, [])), "chosen": n == chosen}
                  for i, (n, x, _y) in enumerate(opts)]
        recorder.record_invest_cards("strategy", _cards)
        for _c in _cards:
            if _c["name"] not in ('?',) and get_strategy(_c["name"]) is None:
                log.warning(f'[cw-strat] 投资策略名不在注册表(数据缺口,效果原文已采集): {_c["name"]!r}')

        # 点最优卡的**卡名**选中(Y 从 screen_info「区域-卡名行」center 读;缺失兜底 CARD_CLICK_Y=474)。
        # safe_click 带 bug#1 mouse_move 缓解(partner reset 根因同类)。
        _sel = area_center(self.ctx, '区域-卡名行', CwScreenInvestStrategy.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else CwScreenInvestStrategy.CARD_CLICK_Y
        target = Point(choose_x, _click_y)
        safe_click(self, target, tag='cw-strat')
        time.sleep(0.7)
        # 确认 + 验关(投资策略 消失 = overlay 关)。原「点了就 success」不验 → bug#1/卡未选中/隐藏多步 flat-loop
        # (partner reset 根因同类;write-operation「点了≠成了」;本 op docstring 已记「点名 540+ 次不选中→卡死 18min」)。
        # 确认 center 从 screen_info 读,缺失兜底。
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenInvestStrategy.SCREEN_NAME) or CwScreenInvestStrategy.CONFIRM
        _rr = confirm_and_verify(self, confirm_point=_confirm, entry_keyword='投资策略',
                                 tag='cw-strat')
        # 持卡本体追加 + 到账登记(§3.3 #22 ConfirmStrategy;粗粒度
        # expected,效果走台账不进 session 推进)。**append 只在确认落地
        # 成功后**(ADR-0598 幻影卡收口:确认失败轮 = round_retry,卡未
        # 到手不留幻影;下轮重入本节点重新选卡);去重防重复入列。
        # (原「chosen 只点不存」bug 的修复语义由本块承载。)
        if _rr.is_success and match is not None and chosen != '?':
            if chosen not in match.session.active_strategies:
                match.session.active_strategies.append(chosen)
            # BoardState 写端(迁移批次二,§3.4.4/§4 投资选择行):持有投资
            # 策略=本屏写入、局级累计(逐次选择追加);单次逻辑写入
            # (§3.4 申报豁免)。品质锚挂建模批(设计 §3.4.4)。
            from sr_od.application.currency_war.kernel.cw_board_state import (
                board_state_of,
            )
            board_state_of(match.session).write_logic(
                board_state_of(match.session).active_strategies,
                list(match.session.active_strategies),
                produced_by='CwScreenInvestStrategy')
            from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
                register_confirm_arrival,
            )
            register_confirm_arrival(match.session, 'ConfirmStrategy', chosen,
                                     produced_by='CwScreenInvestStrategy')
        return _rr
