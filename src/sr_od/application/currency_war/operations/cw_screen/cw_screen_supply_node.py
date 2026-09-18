
"""货币战争 补给节点画面 op(旧补给节点执行器退役批内联)。

补给阶段 = 动态 N 选 1 装备 + 确认(通常 4 选 1;「全都要」类效果减 2 列、「人身意外险」类
加补给阶段可增列,augment 改写下实测 3-5 不等——历史「3 选 1」「实测 5」均为特例表述,
列数以 read_supply_options 实际识别为准,禁写死)。

动作(T#99 已接 decide_supply):``read_supply_options`` OCR 每列(角色+装备)→ ``decide_supply`` 按
target_comp.key_equips 契合 + 装备通用价值选最优列 → 点该列卡身 + 确认。读不到选项 → CARD_BODY 兜底。
钻(红/蓝=基本赢)视觉判定 + has_diamond 待补;刷新按钮实存(「剩余次数」文锚
左侧圆钮,``_REFRESH_BTN_DX`` 文本锚定,decide_supply 规则 2「全无钻+刷新未用
→刷新找钻」消费)。

**ADR-0517 刷新 = 终结动作**:decide_supply 建议刷新 ∧「刷新未用」→ 点钮一次
(点击后本动作即返回,op 交回外循环重进 = 入口重建,新装备面由重进后的
入口观察现读承载——「节点内刷后重读再选」的循环形态与「终结→外循环重进
→入口重建」语义连续)。节点内至多刷 1 次的硬限制由容器
``supply_refresh_used`` 计数承载(>0 = 已用;发射即记不等验效,跨外环
重建存活——carried 融合语义;**容器计数内联写留守决策体**,本屏无注册表
登记件)。锚读缺 = 零点击 + 照常置位已用(流程收敛:零动作空转活锁防线,
语义与旧码一致)。

选定+确认时点经 cw_telemetry.set_last_supply_pick 暂存选择快照
(char/equip/has_diamond/refreshed + 实际识别选项清单),供 overlay 消失后
cw_loop 合成 supply 遥测行消费(synthetic_supply 合成行)。

T#103:确认按钮进 screen_info(货币战争-补给 按钮-确认);卡身点击点由 read_supply_options 按列返回。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node = 节点完成门(``_in_node``,miss = overlay 消失 /
进了下一节点 = 节点完成,success 交回外层)+ 选项一次读(每访问恰一次,与
现役决策体读同帧等价,迁移不增加读屏)→ ``report_screen_supply_node_obs``
落容器 ``supply``(空 = 读缺 CARD_BODY 兜底路径,闸在 report 内)→ obs 挂
实例属性进决策 node。决策动作 node = 节点完成复检(每轮新帧)→ 零参决策
(候选自容器槽)→ 点卡身 + 确认 / 刷新终结交回 → ``round_wait`` 循环推进
(不烧节点重试预算,无防御上限)。``chosen_supply`` = 确认即写特殊口径
(选定中转暂存宿主已退役,直写是载体消亡后的唯一形态)留守决策体真选分支;
本屏 sim 腿 = 引擎补给决策段已在但 sim 接线未接,等价判据主承重 = 实机
在册行为锁。
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
        self._refresh_used = False   # 无 match 局外兜底实例态(生产读源 = 容器 supply_refresh_used 计数)
        # 观察结果(观察 node 产物,决策动作 node 消费)与点卡定位点载体
        # (obs 只载选项数据进容器;点击点 = 现役读链产物,经实例属性跨
        # node 传递,决策轮不重读不重算)。
        self._obs: CwScreenSupplyNodeObs | None = None
        self._sup_opts: list | None = None

    def _in_node(self, screen) -> bool:
        # 还在补给屏 = 标识-补给阶段 area 命中(位置区分,非全屏 LCS:防「补给阶段」与「备战阶段」共享「阶段」误匹配)。
        return self.round_by_find_area(screen, '货币战争-补给', '标识-补给阶段', crop_first=False).is_success

    def _read_refresh_anchor(self, screen) -> Point | None:
        """「剩余次数：N」文本锚(刷新圆钮文本锚定用;遭遇屏
        ``read_encounter_refresh_count`` 同族形态)。

        OCR 带 = 建档「文本-剩余次数」pc_rect 外扩余量(x ±30 / y ±15,固定常量:
        防文字框与建档 rect 边缘相切时漏配;rect 单一真相源 = screen_info)。
        ``crop_first=False`` 全帧识别按带过滤(避开小框裁剪漏检)。
        正则命中 → 文本中心;读不到 → None(调用方失败安全:零点击 + 照常
        置位已用旗标)。纯读。
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
            if _REMAIN_RE.search(text):
                return Point(int(mrl.max.center.x), int(mrl.max.center.y))
        return None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """节点完成门 + 选项一次读 → report 落容器。

        门 miss = 已不在本节点画面(overlay 消失 / 进了下一节点)→ 节点
        完成,success 交还外层(出口验真 = 本门判定本身,纯观察面;
        chosen_supply 已改确认即写,门处无写动作)。在门内 → 选项一次读
        → ``report_screen_supply_node_obs`` 落容器 ``supply``(空 = 读缺
        CARD_BODY 兜底路径,不写,闸在 report 内;match/gs 缺席的局外
        兜底路径跳过 report)→ obs + 点卡定位点挂实例属性。"""
        screen = self.last_screenshot
        if not self._in_node(screen):
            return self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)')
        opts = read_supply_options(self.ctx, screen)
        obs = CwScreenSupplyNodeObs(in_node=True,
                                    options=[o for o, _pt in opts],
                                    screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_supply_node_obs(_gs, obs)
        self._obs = obs
        self._sup_opts = list(opts)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=8)
    def act(self) -> OperationRoundResult:
        """节点完成复检 → 单动作(刷新终结交回 ∨ 选卡+确认)→ round_wait。

        每轮 node runner 新帧复检节点完成门(round_wait 不计节点重试预算,
        不收敛 = 策略 bug 响亮暴露,无防御上限);overlay 消失 = 节点完成,
        success 交还外层。"""
        if not self._in_node(self.last_screenshot):
            return self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)')
        if self._do_action():
            # 刷新 = 终结动作:点钮后本访问交回(外循环重进 = 入口重建,
            # 新装备面由重进后的入口观察现读承载,ADR-0517 语义连续)。
            return self.round_success('建议刷新终结交回(重进重建入口)', wait=1.5)
        return self.round_wait(wait=1.5)

    def _do_action(self) -> bool:
        """决策 + 单动作体(零参:候选与点击点自观察轮实例载体消费)。

        T#99:``decide_supply`` 按 target_comp.key_equips 契合 + 装备通用价值
        选(替代盲点 CARD_BODY);读不到选项 → CARD_BODY 兜底。刷新分支
        点圆钮后终结交回(Returns True);选卡分支点卡身 + 确认机械半经
        工厂(统一动作工厂批4:体迁 ``cw_overlay_pick_action.SupplyPickOp``,
        方法级替身缝保留)。Returns: True = 刷新已发(终结交回)。
        """
        match = self.ctx.cw_match
        opts = self._sup_opts or []
        # 刷新已用读源 = 容器 supply_refresh_used 计数(>0 = 已用)。无 match
        # 退实例态(测试/离线路径;实例态在外环每次新建 op 下失效 = 仅局外
        # 兜底,不承生产语义)。
        if match is not None:
            _refresh_used = int(match.gs.supply_refresh_used.value or 0) > 0
        else:
            _refresh_used = self._refresh_used
        target = CwScreenSupplyNode.CARD_BODY
        reason = 'no-options(CARD_BODY 兜底)'
        refresh_target = None
        # 本轮选定快照(选卡确认后合成决策帧的 extra 载荷;None=兜底点卡
        # 路径/刷新路径——决策帧照写但不带选择字段,读端按 None 分型)。
        # 只本地拷贝,不动 _LAST_SUPPLY_PICK 暂存槽(其唯一消费者仍是
        # cw_loop 合成结算行,提前消费=结算行断粮)。
        picked: dict | None = None
        if match is not None and opts:
            # 零参决策(写槽已由观察轮 report 落容器 supply;决策调用形态
            # 不变,同访问覆盖写)。
            from sr_od.application.currency_war.kernel.cw_vocab import (
                CwActionPickSupplyParam,
                CwActionRefreshSupplyParam,
            )
            _gs = match.gs
            pick = match.strategy.decide_supply()
            if isinstance(pick, CwActionRefreshSupplyParam) and not _refresh_used:
                # 只刷一次(容器计数 >0 = 已用;kernel 刷新闸同源同值,本闸
                # = handler 侧同口径保留)。
                _anchor = self._read_refresh_anchor(self._obs.screen if self._obs is not None else None)
                self._refresh_used = True
                # live 刷新发射即容器计数 +1(发射即记不等验效——含下方锚
                # 读缺零点击路径,同旗标置位时点;本点 = 决策体记录面留守
                # 原位,本屏无注册表登记件,无双计面)。
                try:
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        ChannelSig,
                    )
                    _gs_r = match.gs
                    _gs_r.write_logic(
                        _gs_r.supply_refresh_used,
                        int(_gs_r.supply_refresh_used.value or 0) + 1,
                        produced_by='CwScreenSupplyNode',
                        evidence='refresh_click',
                        sig=ChannelSig(family='logic_action',
                                       actor='CwScreenSupplyNode',
                                       mode='compute'))
                except Exception as e:   # noqa: BLE001  记录面失败不阻塞节点动作
                    log.warning(f'[cw-supply] 刷新计数记录失败(不阻塞): {e}')
                reason = pick.reason
                if _anchor is None:
                    # 文本锚读缺 → 零点击 + 照常置位已用(流程收敛语义与旧码一致:
                    # 零点击不重掷,靠烧旗标让下轮照常选装;不烧旗标 =
                    # 「建议刷新→锚读缺→零动作」每轮空转的活锁形态,fake
                    # 渠道行为锁实证)。
                    log.warning('[cw-supply] 建议刷新但「剩余次数」文本锚读缺 → '
                                '零点击,照常置位已用(下轮按非刷新重选)')
                    return False
                refresh_target = Point(_anchor.x + CwScreenSupplyNode._REFRESH_BTN_DX,
                                       _anchor.y)
            elif isinstance(pick, CwActionPickSupplyParam) and 0 <= pick.idx < len(opts):
                target = opts[pick.idx][1]
                reason = pick.reason
                # 选定快照(角色/装备/钻;refreshed=刷新是否已用;附实际识别
                # 选项清单)——现役消费方 = 到账登记(equip)。
                _opt = opts[pick.idx][0]
                picked = {'char': _opt.char, 'equip': _opt.equip,
                          'has_diamond': _opt.has_diamond,
                          'refreshed': _refresh_used}
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
            log.info('[cw-supply] options=%s pick=%s %s click@(%d,%d)',
                     [(o.char, o.equip, o.has_diamond) for o, _ in opts],
                     type(pick).__name__, reason, target.x, target.y)
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
        # CwActionRefreshSupplyParam 建议的执行半,与遭遇屏 _try_refresh 同类,
        # pick execute 语义 = 点卡选中 → 确认)。派发实例仅作注册表解析键
        #(机械参数 target/picked 经 env 传递;无 match 兜底路径同形派发)。
        from sr_od.application.currency_war.kernel.cw_vocab import (
            CwActionPickSupplyParam,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, match=match, target=target,
                                  picked=picked)
        action_op_for(CwActionPickSupplyParam(idx=0), self.ctx, _env).execute()
        return False
