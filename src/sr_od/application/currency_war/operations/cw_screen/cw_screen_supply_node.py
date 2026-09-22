
"""货币战争 补给节点画面 op(旧补给节点执行器退役批内联)。

补给阶段 = 动态 N 选 1 装备 + 确认(通常 4 选 1;「全都要」类效果减 2 列、「人身意外险」类
加补给阶段可增列,augment 改写下实测 3-5 不等——历史「3 选 1」「实测 5」均为特例表述,
列数以 read_supply_options 实际识别为准,禁写死)。

动作(T#99 已接 decide_supply):``read_supply_options`` OCR 每列(角色+装备)→ ``decide_supply`` 按
target_comp.key_equips 契合 + 装备通用价值选最优列 → 点该列卡身 + 确认。读不到选项 → CARD_BODY 兜底。
钻(红/蓝=基本赢)视觉判定 + has_diamond 待补;刷新按钮实存(「剩余次数」文锚
左侧圆钮,``_REFRESH_BTN_DX`` 文本锚定,decide_supply 规则 2「全无钻+刷新剩余
>0 →刷新找钻」消费)。

**ADR-0517 刷新 = 终结动作**:decide_supply 建议刷新 ∧ 剩余闸放行 → 点钮一次
(点击后本动作即返回,op 交回外循环重进 = 入口重建,新装备面由重进后的
入口观察现读承载)。**刷新闸 = 剩余语义观察真值**(用户裁定 2026-09-21,
全域规范 = ``op-layer.md`` §1.4):闸读源 = 容器 ``supply_refresh_left``
(观察 node 同帧「剩余次数：N」读数经 report 摄入,读缺跳写);剩余 ≤0 或
None = 拒绝 → 重调一次决策按原评分选(单轮内有界);锚读缺 → 容器留旧值
+ 无点击点 → 同拒绝面。原实例旗标/已用计数写点随剩余闸退役(考古走 git)。

T#103:确认按钮进 screen_info(货币战争-补给 按钮-确认);卡身点击点由 read_supply_options 按列返回。

形态:观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node 另承载节点条锚定(顶部「备战阶段 X-Y」→
``observe_node_anchor``;锚定写端在册 = `screens/op-layer.md` §2.1;
节点条锚定四分支处置规则表正本 = `game_state/node-derivation.md`
(E10 行)——补给「自动弹」形态的唯一锚定点)。观察 node = 节点完成门(``_in_node``,miss = overlay 消失 /
进了下一节点 = 节点完成,success 交回外层)+ 选项一次读(每访问恰一次,与
现役决策体读同帧等价,迁移不增加读屏)→ ``report_screen_supply_node_obs``
落容器 ``supply``(空 = 读缺 CARD_BODY 兜底路径,闸在 report 内)→ obs 挂
实例属性进决策 node。决策动作 node = 零参决策(候选自容器槽)→ 刷新终结
交回 / 选卡派发即 ``round_success`` 终结(派发即终结正本 =
`screens/op-layer.md` §1.1、`flow/action_ops.md` §4.5:动作 op 确认
点击后立即上报完整结果,零重入裁决、零落地相补写面——确认未生效 =
代码 bug,overlay 残留由外循环按当前画面重识别重派)。``chosen_supply``
= 确认即写特殊口径(选定中转暂存宿主已退役,直写是载体消亡后的唯一
形态)留守决策体真选分支,派发前写(``op-layer.md`` §2.2 动作事实边界
硬规则);本屏 sim 腿 = 引擎补给决策段已在但 sim 接线未接,等价判据
主承重 = 实机在册行为锁。
"""
import re
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_events import (
    normalize_registry_equip_name,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    observe_node_anchor,
)
from sr_od.application.currency_war.kernel.cw_screen_report.supply_node import (
    CwScreenSupplyNodeObs,
    report_screen_supply_node_obs,
)
from sr_od.application.currency_war.obs.cw_node_obs import read_supply_options
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# 「剩余次数：N」正则(遭遇/投资屏 reader 同款形态,cw_node_obs._REMAIN_RE 族;
# 全角/半角冒号都认,OCR 渲染不一)。
_REMAIN_RE = re.compile(r'剩余次数\s*[：:]\s*(\d+)')

# 补给屏顶部节点条「备战阶段 X-Y」读数正则(cw_observation.read_phase_round
# 核心同款 "1-3" 形态;该 reader 绑备战屏 A_PHASE 区且带 last-known 缓存/
# 单调守卫,补给屏锚定不经它——禁猜语义下读不得即跳过,不吃兜底值)。
_NODE_BAR_RE = re.compile(r'(\d)\s*-\s*(\d)')


class CwScreenSupplyNode(SrOperation):
    """补给节点:点卡身选中 + 确认,overlay 消失(门 miss)= 节点完成。"""

    CARD_BODY: ClassVar[Point] = Point(900, 550)  # 补给卡 body 不开对话(沿用 HandleSupply)
    # 刷新圆钮 = 「剩余次数：N」文本左侧固定偏移(遭遇屏 _REFRESH_BTN_DX 同族先例,
    # 文本锚定;运行时锚 = 建档「文本-剩余次数」rect 约束 OCR,单一真相源 =
    # screen_info)。偏移实测收口(归档帧 sr-od-test/screens/货币战争-补给/
    # {default,双排装备,col3_selected}.webp CV 双法:HoughCircles 钮心
    # (1314.5-1315.5,983.5) r≈22-24 亮/灰态稳定;文本框中心 (1414,982.5)/建档
    # rect 中心 (1415.5,983))→ dx ≈ -99.5 取 -100,dy=0。偏移错 → 刷新未命中,
    # 重读 = 原 options,重决策结果天然等价(照常选卡;失败安全同遭遇屏先例)。
    # (原固定常量 (974,854) 经归档帧复测落在卡列下方空白区 = 失效坐标,删除。)
    _REFRESH_BTN_DX: ClassVar[int] = -100
    # 刷新文本锚 = 建档「文本-剩余次数」area(货币战争-补给;OCR 带 rect 单一源)。
    _REFRESH_TEXT_AREA: ClassVar[str] = '文本-剩余次数'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-补给节点')
        # 观察结果(观察 node 产物,决策动作 node 消费)与点卡/刷新钮定位点
        # 载体(obs 只载选项数据进容器;点击点 = 现役读链产物,经实例属性
        # 跨 node 传递,决策轮不重读不重算)。
        self._obs: CwScreenSupplyNodeObs | None = None
        self._sup_opts: list | None = None
        self._refresh_point: Point | None = None

    def _in_node(self, screen) -> bool:
        # 还在补给屏 = 标识-补给阶段 area 命中(位置区分,非全屏 LCS:防「补给阶段」与「备战阶段」共享「阶段」误匹配)。
        return self.round_by_find_area(screen, '货币战争-补给', '标识-补给阶段', crop_first=False).is_success

    def _read_refresh_anchor(self, screen) -> tuple[int, Point] | None:
        """「剩余次数：N」文本锚双出(剩余次数 + 文本中心点;遭遇屏
        ``read_encounter_refresh_count`` 同族形态)。

        OCR 带 = 建档「文本-剩余次数」pc_rect 外扩余量(x ±30 / y ±15,固定常量:
        防文字框与建档 rect 边缘相切时漏配;rect 单一真相源 = screen_info)。
        ``crop_first=False`` 全帧识别按带过滤(避开小框裁剪漏检)。
        正则命中 → (N, 文本中心);读不到 → None(调用方失败安全:读数与
        点击点同读同缺——count=None 进容器读缺跳写,point=None 走闸拒绝面)。
        纯读;观察 node 调用一次,决策轮消费实例载体,零新增截图。
        """
        if screen is None:
            # 无帧(fake 渠道桩替读链环境):按锚读缺走失败安全,不喂 None 给
            # 真 OCR 引擎(会崩 predict_det,痕 = 'NoneType' object has no
            # attribute 'shape')。生产路径 screen 恒来自 screenshot() 非空。
            return None
        _area = self.ctx.screen_loader.get_area('货币战争-补给',
                                                CwScreenSupplyNode._REFRESH_TEXT_AREA)
        if _area is None or _area.pc_rect is None:
            return None
        _r = _area.pc_rect
        _band = Rect(max(0, _r.x1 - 30), max(0, _r.y1 - 15),
                     _r.x2 + 30, _r.y2 + 15)
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=_band, color_range=None, crop_first=False,
        )
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            m = _REMAIN_RE.search(text)
            if m:
                return int(m.group(1)), Point(int(mrl.max.center.x),
                                              int(mrl.max.center.y))
        return None

    def _read_node_bar(self, screen) -> int | None:
        """顶部节点条「备战阶段 X-Y」读数(视觉实证 V3:顶部节点条屏显,
        备战屏 A_PHASE 识别区不含该位置,故本屏独立建档「标识-备战阶段」)。

        OCR 带 = 建档 pc_rect 外扩余量(x ±30 / y ±15,与 _read_refresh_anchor
        同款;crop_first=False 全帧识别按带过滤,防小框裁剪漏检)。
        正则命中 + 值域内(plane∈1-3/round≤9,与 read_phase_round 值域守卫
        同源——OCR 抓错源当 miss)→ 序号 (plane-1)*9+round;读不得/值域外
        → None(调用方 = 跳过,禁猜)。纯读。
        """
        if screen is None:
            return None
        _area = self.ctx.screen_loader.get_area('货币战争-补给', '标识-备战阶段')
        if _area is None or _area.pc_rect is None:
            return None
        _r = _area.pc_rect
        _band = Rect(max(0, _r.x1 - 30), max(0, _r.y1 - 15),
                     _r.x2 + 30, _r.y2 + 15)
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=_band, color_range=None, crop_first=False,
        )
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            m = _NODE_BAR_RE.search(text)
            if m:
                plane, rnd = int(m.group(1)), int(m.group(2))
                if 1 <= plane <= 3 and 1 <= rnd <= 9:
                    return (plane - 1) * 9 + rnd
        return None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """节点完成门 + 选项一次读 → report 落容器。

        门 miss = 已不在本节点画面(overlay 消失 / 进了下一节点)→ 节点
        完成,success 交还外层(出口验真 = 本门判定本身,纯观察面;
        chosen_supply 已改确认即写,门处无写动作)。在门内 → 选项一次读
        + 刷新剩余次数同帧读(与选项同帧同源,零新增截图)→
        ``report_screen_supply_node_obs`` 落容器 ``supply`` +
        ``supply_refresh_left``(选项空 = 读缺 CARD_BODY 兜底路径,整函数
        早退不写,闸在 report 内;match/gs 缺席的局外兜底路径跳过
        report)→ obs + 点卡/刷新钮定位点挂实例属性。"""
        screen = self.last_screenshot
        if not self._in_node(screen):
            return self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)')
        opts = read_supply_options(self.ctx, screen)
        anchor = self._read_refresh_anchor(screen)
        refresh_left = anchor[0] if anchor is not None else None
        self._refresh_point = anchor[1] if anchor is not None else None
        obs = CwScreenSupplyNodeObs(in_node=True,
                                    options=[o for o, _pt in opts],
                                    refresh_left=refresh_left,
                                    screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        # 节点条锚定(补给「自动弹」形态——结算确认直接弹补给屏,无备战帧
        # 可锚——的唯一锚定点;divert 形态 = 备战帧已锚,本读数走处置规则表
        # reanchor/stale_dropped 分支承接,处置规则表正本 = `game_state/node-derivation.md`(E10 行))。
        # 读不得/局外 gs 缺席 = 跳过(禁猜;best-effort)。
        _ordinal = self._read_node_bar(screen)
        if _ordinal is not None and _gs is not None:
            observe_node_anchor(_gs, _ordinal,
                                trigger_screen='货币战争-补给',
                                actor='CwScreenSupplyNode')
        if _gs is not None:
            report_screen_supply_node_obs(_gs, obs)
        self._obs = obs
        self._sup_opts = list(opts)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=8)
    def act(self) -> OperationRoundResult:
        """分发身份安全网 + 单动作(刷新终结交回 ∨ 选卡派发即终结)。

        门 miss = 已离开本节点画面(分发身份安全网:确认链已发即离开 =
        节点完成)→ success 交还外层。动作两分支均终结本访问:刷新点钮后
        交回(外循环重进 = 入口重建);选卡经动作 op 确认点击后立即上报
        完整结果,派发即 round_success 终结(正本 = `screens/op-layer.md`
        §1.1、`flow/action_ops.md` §4.5,零重入
        裁决、零落地相补写面)。"""
        if not self._in_node(self.last_screenshot):
            return self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)')
        if self._do_action():
            return self.round_success('动作已发,本访问终结交回(外循环重进重建入口)',
                                      wait=1.5)
        return self.round_wait(wait=1.5)

    def _do_action(self) -> bool:
        """决策 + 单动作体(零参:候选与点击点自观察轮实例载体消费)。

        T#99:``decide_supply`` 按 target_comp.key_equips 契合 + 装备通用价值
        选(替代盲点 CARD_BODY);读不到选项 → CARD_BODY 兜底。刷新分支 =
        剩余闸放行(容器 ``supply_refresh_left`` >0 且锚点在位)才点圆钮,
        点后 2s 终结交回;闸拒绝 → 重调一次决策按原评分选(单轮内有界)。
        选卡分支点卡身 + 确认机械半经工厂(统一动作工厂批4:体迁
        ``cw_overlay_pick_action.CwActionPickSupplyOp``,方法级替身缝保留),
        确认点击后动作 op 立即上报完整结果,派发即终结。
        Returns: True = 动作已发(终结交回)。
        """
        match = self.ctx.cw_match
        opts = self._sup_opts or []
        target = CwScreenSupplyNode.CARD_BODY
        reason = 'no-options(CARD_BODY 兜底)'
        refresh_target = None
        # 派发实例真实选中下标(上报 param 即真实选择;兜底/刷新轮 = 0 占位)。
        param_idx = 0
        # 开出内容载荷(空串 = 兜底点卡路径/装备名未解析——报告侧按「内容未知/未解析」分型翻来源留证)。
        picked_char = ''
        picked_norm_item = ''
        # 本轮选定快照(选定事实现场载荷;None=兜底点卡路径/刷新路径)。
        # 现役消费面 = 零(选定事实现场载荷,遥测接线候批)。
        picked: dict | None = None
        if match is not None and opts:
            # 零参决策(写槽已由观察轮 report 落容器 supply;决策调用形态
            # 不变,同访问覆盖写)。
            from sr_od.application.currency_war.kernel.cw_vocab import (
                CwActionPickSupplyParam,
                CwActionRefreshSupplyParam,
            )
            _gs = match.gs
            # 刷新剩余闸读源 = 容器 supply_refresh_left(观察轮 report 摄入
            # 的同帧读数;None = 未观察/读缺,≤0 = 已刷尽)。
            _left = _gs.supply_refresh_left.value
            pick = match.strategy.decide_supply()
            if isinstance(pick, CwActionRefreshSupplyParam) \
                    and not (_left is not None and int(_left) > 0
                             and self._refresh_point is not None):
                # 对照闸拒绝 → 重调一次决策按原评分选(单轮内有界;
                # kernel 刷新闸同源同值,本面 = 读缺/锚点缺不一致兜底)。
                pick = match.strategy.decide_supply()
                if isinstance(pick, CwActionRefreshSupplyParam):
                    # 重调仍建议刷新 = 闸数据不一致面,零点击终结交回
                    #(外循环重进 = 入口重建重试观察,不空转本节点预算)。
                    log.warning('[cw-supply] 建议刷新但剩余闸拒绝(left=%r)'
                                ' → 零点击终结交回(外循环重进重试观察)',
                                _left)
                    return True
            if isinstance(pick, CwActionRefreshSupplyParam):
                # 剩余闸放行:点圆钮一次后终结交回(外循环重进 = 入口重建,
                # 新装备面由重进后的入口观察现读承载,ADR-0517)。
                refresh_target = Point(
                    self._refresh_point.x + CwScreenSupplyNode._REFRESH_BTN_DX,
                    self._refresh_point.y)
                reason = pick.reason
            elif isinstance(pick, CwActionPickSupplyParam) and 0 <= pick.idx < len(opts):
                target = opts[pick.idx][1]
                reason = pick.reason
                param_idx = pick.idx
                # 选定快照(角色/装备/钻;refresh_left=容器剩余次数现值快照,
                # 可 None——布尔键随计数闸消亡,left 供读端按剩余分型,无
                # 「本局初始授予数」基线故携带而非推导)——
                # 选定事实现场载荷,现役消费面 = 零(见上方组装点注释)。
                _opt = opts[pick.idx][0]
                picked = {'char': _opt.char, 'equip': _opt.equip,
                          'has_diamond': _opt.has_diamond,
                          'refresh_left': _left}
                # 开出内容载荷(归一件名 = 注册表级分层归一
                # ``normalize_registry_equip_name`` 现算:精确快道 →
                # containment longest-first → 相似救援唯一命中;多/零命中
                # = '' 禁猜,报告侧翻来源留证)。
                picked_char = _opt.char
                picked_norm_item = normalize_registry_equip_name(_opt.equip)
                # GameState 选定记录(chosen_supply)——**确认即写**(口径分叉
                # 显式申报:supply 直写,chosen_tome 维持「出口验真后写」家族
                # 口径不变——差异理由 = supply 的中转暂存宿主已随执行层状态
                # 类目退役,直写是暂存载体消亡后的唯一形态;chosen_tome 无
                # 暂存载体。确认未落地窗内容器短暂持未落地值:容器
                # chosen_supply 无决策读者,低危可接受;兜底点卡/刷新轮不写
                # = 真选守卫(与本分支互斥)。)
                try:
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        ChannelSig,
                    )
                    _gs.write_logic(
                        _gs.chosen_supply,
                        (_opt.char, _opt.equip, _opt.has_diamond),
                        produced_by='CwScreenSupplyNode',
                        sig=ChannelSig(family='logic_action',
                                       actor='CwScreenSupplyNode',
                                       mode='compute'))
                except Exception as e:   # noqa: BLE001  记录面失败不阻塞节点动作
                    log.warning(f'[cw-supply] chosen_supply 记录失败(不阻塞): {e}')
            log.info('[cw-supply] options=%s pick=%s %s left=%s click@(%d,%d)',
                     [(o.char, o.equip, o.has_diamond) for o, _ in opts],
                     type(pick).__name__, reason, _left, target.x, target.y)
        else:
            log.info('[cw-supply] opts=%d match=%s → CARD_BODY 兜底', len(opts), match is not None)
        # bug#1 缓解:click 前 mouse_move 到目标(零移动),防 before_screenshot 移光标 → click 落空。
        if refresh_target is not None:
            self.ctx.controller.mouse_move(refresh_target)
            self.ctx.controller.click(refresh_target)
            # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
            # #19,2026-09-02):补给屏刷新后 2s 画面稳定——原 0.6s 依赖「下一轮
            # wait 1.5s」合计 2.1s,余量仅 0.1s,重掷动画尾帧可能被读(选项读缺
            # → 决策建立在残缺选项上)。等满 2s 再交回。
            time.sleep(2.0)
            return True
        # 点卡选中 → 确认机械半经工厂(刷新圆钮机械点击留守上方——刷新链 =
        # CwActionRefreshSupplyParam 建议的执行半,
        # pick execute 语义 = 点卡选中 → 确认)。派发实例携真实选中下标与
        # 开出内容载荷(上报 param 即真实选择+内容;动作 op 确认点击后
        # 立即一口写 owned/单位腿/后果腿;无 match 兜底路径同形派发,
        # 内容空 = 报告侧内容未知分型)。派发即终结。
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, match=match, idx=param_idx,
                                  target=target, picked=picked)
        _param = CwActionPickSupplyParam(idx=param_idx,
                                         char_name=picked_char,
                                         norm_item=picked_norm_item)
        action_op_for(_param, self.ctx, _env).execute()
        return True
