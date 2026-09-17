
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
钻(红/蓝=基本赢)视觉判定 + has_diamond 待补;刷新按钮实存(「剩余次数」文锚
左侧圆钮,``_REFRESH_BTN_DX`` 文本锚定,decide_supply 规则 2「全无钻+刷新未用
→刷新找钻」消费)。

**ADR-0517 适配申报(§8.4 裁决建议按建议落)**:本节点已按单动作架构语义
运转——每轮 ``handle`` = 入口重观察(``_in_node`` 验证 + ``read_supply_options``
现读)→ 单动作决策(``decide_supply`` 一选)→ 执行;**刷新 = 终结 op**(点击
后本动作即返回,``round_retry`` 重进节点 = 入口重建,新装备面由重进后的
选项现读承载——「节点内刷后重读再选」的循环形态与「终结→外循环重进→
入口重建」语义连续)。节点内至多刷 1 次的硬限制由容器
``supply_refresh_used`` 计数承载(>0 = 已用;发射即记不等验效,跨外环
重建存活——carried 融合语义,§8.4 与商店 §3.1 对称)。

T#103:确认按钮进 screen_info(货币战争-补给 按钮-确认);卡身点击点由 read_supply_options 按列返回。

**行为等价红线(旧节点基类退役批)**:补给节点流转(节点屏↔补给屏)/committed-but-verifying
语义/node_max_retry_times=8 预算/ADR-0264 关态稳定基线预置,全部原样平移(原基类
_run_node 循环内联进 handle,零行为变更)。

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(cw_game_ports 两端口完整在场 → 五段生命周期新路径;
缺省 None = 生产直连旧路径,handle 原序列,生产行为零变化 §9.1)。迁移手法
单一源 = 盛会之星先例(CwScreenMegastar,验收评审):decide+act
内聚于现役动作体 ``_do_action``(刷新/选卡确认两形态,两路径共享零转录);
本屏无 on_outcome 落地登记件(§6.4 收编面无补给行;``supply_refresh_used``
live 写端 = ``_do_action`` 刷新分支单点直写容器(渠道② logic_action,
发射即记不等验效;注册表缺席 = 本点唯一,无双计面;sim 侧 observe 通道
在写,两源同域));chosen_supply 写端 = 选定确认时点(真选分支)确认即写
单次逻辑写入豁免(§2.2/§6.5-6)。节点完成判定 = 下一轮 observe 门 ``_in_node``
复检(观察驱动节点循环,非生命周期验证段——用户裁定 2026-09-10 验证段废除,
confirm 点击系统性不生效 = 动作链 bug 根修动作链)。本屏 sim 腿 = 引擎补给
决策段已在(engine_p1 直调 kernel decide_supply,T5 接口收敛挂账)但本批未
接线(sim 接线批后续),等价判据主承重 = 实机在册行为锁(test_cw_runnode_retire
+ test_cw_game_state_consume + 本批锁 test_cw_obs_arch_event_screens_step3)。
"""
import re
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.obs.cw_node_obs import read_supply_options
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext

# 「剩余次数：N」正则(遭遇/投资屏 reader 同款形态,cw_node_obs._REMAIN_RE 族;
# 全角/半角冒号都认,OCR 渲染不一)。
_REMAIN_RE = re.compile(r'剩余次数\s*[：:]\s*(\d+)')


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
    """

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
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-补给节点')
        self._refresh_used = False   # 无 match 局外兜底实例态(生产读源 = 容器 supply_refresh_used 计数)
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
            # (出口验真 = 本门判定本身,纯观察面;chosen_supply 已改确认
            #  即写,门处无写动作。gate 清尾批 2026-09-03:原此处向已退役
            #  的 gate 稳定门预置基线;wait_stable_frame 在 旧内环拆除后已
            #  无生产调用方,基线写端无读端 → 调用删除。外循环重判兜底,
            #  等待语义不变。)
            return self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)')
        # 仍在节点内 → 做一个动作;round_retry 重跑本节点(计 node_max_retry_times 预算,超 → FAIL bail)。
        self._do_action(screen)
        return self.round_retry(wait=1.5)

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

    def _do_action(self, screen) -> None:
        # T#99 接 decide_supply:OCR 补给选项(每列=角色+装备,动态列数)→ 策略按
        # target_comp.key_equips 契合 + 装备通用价值选(替代盲点 CARD_BODY)。钻识别双通道
        # ✅(SIFT 主+文本兜底,cw_node_obs);刷新按钮 = 「剩余次数」文锚左侧
        # _REFRESH_BTN_DX 偏移点,无钻+未刷 → 点刷新重掷。
        match = self.ctx.cw_match
        opts = read_supply_options(self.ctx, screen)
        # 刷新已用读源 = 容器 node_screen_refresh.supply_refresh_used 计数
        #(>0 = 已用,旗标 bool 语义平移;live 写端 = 下方刷新分支单点,
        # sim observe 通道同域)。无 match 退实例态(测试/离线路径;
        # 实例态在外环每次新建 op 下失效 = 仅局外兜底,不承生产语义)。
        if match is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            _refresh_used = int(game_state_of(
                match.session).supply_refresh_used.value or 0) > 0
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
            # 决策输入消费切换(迁移批次二):GameState 视图
            # (kernel/cw_game_state.game_state_of)替 last_state 直读。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            _state = game_state_of(match.session)
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = match.strategy.decide_supply(
                [o for o, _ in opts], _state, match.session, _cfg,
                refresh_used=_refresh_used)
            if pick.refresh and not _refresh_used:   # 只刷一次(容器计数 >0 = 已用)
                _anchor = self._read_refresh_anchor(screen)
                self._refresh_used = True
                # live 刷新发射即容器计数 +1(渠道② logic_action;发射即记
                # 不等验效——含下方锚读缺零点击路径,同旧旗标置位时点;本屏
                # 无 on_outcome 注册件,本点 = 唯一容器写点,无双计面)。
                try:
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        ChannelSig,
                        game_state_of,
                    )
                    _gs_r = game_state_of(match.session)
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
                    # 旧码点失效常量 (974,854) 同样零效果,靠烧旗标让下轮照常
                    # 选装;不烧旗标 = 「建议刷新→锚读缺→零动作」每轮空转烧尽
                    # 节点预算的活锁形态,fake 渠道行为锁实证)。
                    log.warning('[cw-supply] 建议刷新但「剩余次数」文本锚读缺 → '
                                '零点击,照常置位已用(下轮按非刷新重选)')
                    return
                refresh_target = Point(_anchor.x + CwScreenSupplyNode._REFRESH_BTN_DX,
                                       _anchor.y)
            elif 0 <= pick.idx < len(opts):
                target = opts[pick.idx][1]
                reason = pick.reason
                # 选定快照(角色/装备/钻;refreshed=刷新是否已用;附实际识别
                # 选项清单)——现役消费方 = 到账登记(equip)。
                _opt = opts[pick.idx][0]
                picked = {'char': _opt.char, 'equip': _opt.equip,
                          'has_diamond': _opt.has_diamond,
                          'refreshed': _refresh_used}
                # GameState 选定记录(chosen_supply,§3.4.5)——**确认即写**
                #(单次逻辑写入豁免,渠道签名照 chosen_* 家族 logic_action)。
                # 口径分叉显式申报:supply 直写,chosen_tome 维持「出口验真
                # 后写」家族口径不变——差异理由 = supply 的中转暂存宿主已随
                # 执行层状态类目退役(git 历史可溯),直写是暂存载体消亡后的
                # 唯一形态;chosen_tome 无暂存载体。确认未落地窗内容器短暂持
                # 未落地值:容器 chosen_supply 无决策读者(仅写点与字段定义),
                # 低危可接受;兜底点卡/刷新轮不写 = 真选守卫(与本分支互斥)。
                try:
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        ChannelSig,
                    )
                    _state.write_logic(
                        _state.chosen_supply,
                        (_opt.char, _opt.equip, _opt.has_diamond),
                        produced_by='CwScreenSupplyNode',
                        sig=ChannelSig(family='logic_action',
                                       actor='CwScreenSupplyNode',
                                       mode='compute'))
                except Exception as e:   # noqa: BLE001  记录面失败不阻塞节点动作
                    log.warning(f'[cw-supply] chosen_supply 记录失败(不阻塞): {e}')
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
        # 点卡选中 → 确认机械半经工厂(统一动作工厂批4:体迁
        # ``cw_overlay_pick_action.SupplyPickOp``,方法级替身缝保留;刷新圆钮
        # 机械点击留守上方——刷新链 = SupplyPick.refresh 决策的执行半,与
        # 遭遇屏 _try_refresh 同类,§2.5 pick execute 语义 = 点卡选中 → 确认)。
        # 派发实例仅作注册表解析键(机械参数 target/picked 经 env 传递;
        # 无 match 兜底路径同形派发)。
        from sr_od.application.currency_war.kernel.cw_events import SupplyPick
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, match=match, target=target,
                                  picked=picked)
        action_op_for(SupplyPick(idx=0)).execute(_env)

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 3,先例 = 盛会之星)----

    def lifecycle_observe(self
                          ) -> tuple[SupplyObservation,
                                     OperationRoundResult | None]:
        """段1 observe:节点完成门(``_in_node``)→ 轻观察 payload。已离开
        本节点画面 = 节点完成,早退交还外层(旧 handle 首闸逐位转录,含
        完成语义;出口验真 = 本门判定本身,纯观察面——chosen_supply 已改
        确认即写,门处无写动作)。"""
        screen = self.last_screenshot
        if not self._in_node(screen):
            return (SupplyObservation(screen=screen),
                    self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)'))
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_frame())
        return obs, None

    def lifecycle_decision_cycle(self, payload: SupplyObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作内聚):decide+act 内聚于 ``_do_action`` 现役动作体
        (刷新/选卡确认两形态一次一动作;决策/遥测/session 写端/
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
