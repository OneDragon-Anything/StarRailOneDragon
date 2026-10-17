
"""货币战争 补给节点画面 op(旧补给节点执行器已停用,逻辑内联于此)。

补给阶段 = 动态 N 选 1 装备 + 确认(通常 4 选 1;「全都要」类效果减 2 列、「人身意外险」类
加补给阶段可增列,augment 改写下实测 3-5 不等——历史「3 选 1」「实测 5」均为特例表述,
列数以 read_supply_options 实际识别为准,禁写死)。

动作:``read_supply_options`` OCR 每列(角色+装备)→ 策略层决策
(``match.strategy.decide_supply()``,判据单一源 =
``strategies/impl/mandate_v1/supply.py`` 三级字典序:钻>终局角色>装备;
三级全空才刷,次数闸内嵌 decide)→ 点该列卡身 + 确认。读不到选项 →
CARD_BODY 兜底。钻(红/蓝/财富宝钻)视觉判定(SIFT 主通道 + 文本兜底);
刷新按钮实存(「剩余次数」文锚左侧圆钮,``_REFRESH_BTN_DX`` 文本锚定)。

**刷新 = 终结动作**:decide_supply 建议刷新 ∧ 对照闸放行 → 点钮一次
(点击后本动作即返回,op 返回主循环重进 = 入口重建,新装备面由重进后的
入口观察现读承载)。**对照闸 = 剩余语义观察真值**(用户裁定,
全域规范 = ``op-layer.md`` §1.4):闸读源 = 容器 ``supply_refresh_left``
(观察 node 同帧「剩余次数：N」读数经 report 摄入,读缺跳写);判据侧
次数闸已内嵌 decide(仅剩余 ≥1 才可能返刷新建议),本面 = 对照兜底——
锚读缺(无点击点)时重调一次(纯函数同输出仍建议刷)→ 零点击结束本次访问。
原实例旗标/已用计数写点随剩余闸停用。

T#103:确认按钮进 screen_info(货币战争-补给 按钮-确认);卡身点击点由 read_supply_options 按列返回。

形态:观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node 另承载节点条锚定(顶部「备战阶段 X-Y」→
``observe_node_anchor``;锚定写端已登记 = `screens/op-layer.md` §2.1;
节点条锚定四分支处置规则表正本 = `game_state/node-derivation.md`
(E10 行)——补给「自动弹」形态的唯一锚定点)。观察 node = 节点完成门(``_in_node``,miss = overlay 消失 /
进了下一节点 = 节点完成,success 结束本次访问外层)+ 选项一次读(每访问恰一次,与
现役决策体读同帧等价,迁移不增加读屏)→ ``report_screen_supply_node_obs``
落容器 ``supply``(空 = 读缺 CARD_BODY 兜底路径,闸在 report 内)→ obs 挂
实例属性进决策 node。决策动作 node = 零参决策(候选自容器槽)→ 刷新终结
结束本次访问 / 选卡派发即 ``round_success`` 终结(点击发出后即结束本次访问正本 =
`screens/op-layer.md` §1.1、`flow/action_ops.md` §4.5:动作 op 确认
点击后立即上报完整结果,零落地复查、零旧机制补写面——确认未生效 =
代码 bug,overlay 残留由外循环按当前画面重识别重派)。``chosen_supply``
= 确认即写特殊口径(选定中转暂存宿主已停用,直写是载体消亡后的唯一
形态)留在决策体真选分支,派发前写(``op-layer.md`` §2.2 动作事实边界
硬规则);本屏 sim 腿 = 观察腿在产(生成器产物经同名 report 落容器)、
决策腿未接(sim 局 act 恒走 CARD_BODY 兜底),等价判据
主要支撑 = 实机已登记行为测试。
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
from sr_od.application.currency_war.kernel.cw_node_schedule import (
    NodePos,
    node_round_cap,
)
from sr_od.application.currency_war.kernel.cw_screen_report.supply_node import (
    CwScreenSupplyNodeObs,
    report_screen_supply_node_obs,
)
from sr_od.application.currency_war.obs.cw_node_obs import read_supply_options
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

# 「剩余次数：N」正则(遭遇/投资屏 reader 同款形态,cw_node_obs._REMAIN_RE 族;
# 全角/半角冒号都认,OCR 渲染不一)。
_REMAIN_RE = re.compile(r'剩余次数\s*[：:]\s*(\d+)')

# 补给屏顶部节点条「备战阶段 X-Y」读数正则(cw_observation.read_phase_round
# 核心同款两位数形态 "1-3"/修饰局 "1-10";该 reader 绑备战屏 A_PHASE 区且带
# last-known 缓存/单调守卫,补给屏锚定不经它——禁猜语义下读不得即跳过,
# 不吃兜底值)。
_NODE_BAR_RE = re.compile(r'(\d{1,2})\s*-\s*(\d{1,2})')


class CwScreenSupplyNode(CwOperation):
    """补给节点:点卡身选中 + 确认,overlay 消失(门 miss)= 节点完成。"""

    CARD_BODY: ClassVar[Point] = Point(900, 550)  # 补给卡 body 不开对话(沿用 HandleSupply)
    # 刷新圆钮 = 「剩余次数：N」文本左侧固定偏移(遭遇屏 _REFRESH_BTN_DX 同族先例,
    # 文本锚定;运行时锚 = 建档「文本-剩余次数」rect 约束 OCR,单一真相源 =
    # screen_info)。偏移实测收尾(归档帧 sr-od-test/screens/货币战争-补给/
    # {default,双排装备,col3_selected}.webp CV 双法:HoughCircles 钮心
    # (1314.5-1315.5,983.5) r≈22-24 亮/灰态稳定;文本框中心 (1414,982.5)/建档
    # rect 中心 (1415.5,983))→ dx ≈ -99.5 取 -100,dy=0。偏移错 → 刷新未命中,
    # 重读 = 原 options,重决策结果天然等价(照常选卡;失败安全同遭遇屏先例)。
    # (原固定常量 (974,854) 经归档帧复测落在卡列下方空白区 = 失效坐标,删除。)
    _REFRESH_BTN_DX: ClassVar[int] = -100
    # 刷新文本锚 = 建档「文本-剩余次数」area(货币战争-补给;OCR 带 rect 单一源)。
    _REFRESH_TEXT_AREA: ClassVar[str] = '文本-剩余次数'

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='货币战争-补给节点')
        # 观察结果(观察 node 产物,决策动作 node 消费)与点卡/刷新钮定位点
        # 载体(obs 只载选项数据进容器;点击点 = 现役读链产物,经实例属性
        # 跨 node 传递,决策轮不重读不重算)。
        self._obs: CwScreenSupplyNodeObs | None = None
        self._sup_opts: list | None = None
        self._refresh_point: Point | None = None
        # 来源 C 形态门(T-27 利息条件腿,中途审查复裁):观察轮节点条
        # 锚定返回 'reanchor' = 备战帧已锚本节点(常规形态,基座 = 备战帧
        # gs.gold 观察=领取前真值);'advance'/'first_anchor' = 本节点首次
        # 锚定发生在补给屏(「自动弹」形态,无备战帧)→ 基座宁缺不计数。
        # 误分类方向恒宁缺(常规但备战锚 OCR 失读 → advance → 漏计一刻,
        # 宁缺勿造向),无多计向。
        self._prep_anchored: bool = False

    def _in_node(self, screen) -> bool:
        # 还在补给屏 = 标识-补给阶段 area 命中(位置区分,非全屏 LCS:防「补给阶段」与「备战阶段」共享「阶段」误匹配)。
        return self.round_by_find_area(screen, '货币战争-补给', '标识-补给阶段', crop_first=False).is_success

    def _read_refresh_anchor(self, screen) -> tuple[int, Point] | None:
        """「剩余次数：N」文本锚双出(剩余次数 + 文本中心点;遭遇屏
        ``read_encounter_refresh_count`` 同族形态)。

        OCR 带 = 建档「文本-剩余次数」pc_rect 外扩余量(x ±30 / y ±15,固定常量:
        防文字框与建档 rect 边缘相切时漏配;rect 单一真相源 = screen_info)。
        ``crop_first=False`` 全帧识别按带过滤(避开小框裁剪漏检)。
        正则命中 → (N,文本中心);读不到 → None(调用方失败安全:读数与
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

    def _read_node_bar(self, screen) -> NodePos | None:
        """顶部节点条「备战阶段 X-Y」读数(视觉实证 V3:顶部节点条屏显,
        备战屏 A_PHASE 识别区不含该位置,故本屏独立建档「标识-备战阶段」)。

        OCR 带 = 建档 pc_rect 外扩余量(x ±30 / y ±15,与 _read_refresh_anchor
        同款;crop_first=False 全帧识别按带过滤,防小框裁剪漏检)。
        正则命中 + 值域内(plane∈1-3/round ≤ node_round_cap(场字段现值),
        与 read_phase_round 值域守卫同源——OCR 抓错源当 miss)→ **节点序位
        元组 (plane, rnd) 直返**(键表示下读数即键,零坐标换算,迭代
       -abolish-node-ordinal design §2.5;越域位面形态由 kernel
        锚定位面在表守卫丢弃留存证据)。
        读不得/值域外 → None(调用方 = 跳过,禁猜)。纯读。
        """
        if screen is None:
            return None
        _area = self.ctx.screen_loader.get_area('货币战争-补给', '标识-备战阶段')
        if _area is None or _area.pc_rect is None:
            return None
        _r = _area.pc_rect
        _band = Rect(max(0, _r.x1 - 30), max(0, _r.y1 - 15),
                     _r.x2 + 30, _r.y2 + 15)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        _seqs = _gs.node_seq_by_plane.value if _gs is not None else None
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=_band, color_range=None, crop_first=False,
        )
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            m = _NODE_BAR_RE.search(text)
            if m:
                plane, rnd = int(m.group(1)), int(m.group(2))
                if 1 <= plane <= 3 and 1 <= rnd <= node_round_cap(plane, _seqs):
                    return plane, rnd
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
        # 读屏点改道(sim 统一 3.3 金路径生成器批):装了后端 → 生成器产物
        #(经同名 report 落容器);否则执行原读链(选项 + 刷新锚同帧一次读)。
        obs = cw_sim_ports.sim_or_live_observation(
            '货币战争-补给', self._observe_live)
        self._obs = obs
        return self.round_success()

    def _observe_live(self) -> CwScreenSupplyNodeObs:
        """live 观察读链(读屏点改道原样迁移;sim 生成器产物不走本链)。"""
        screen = self.last_screenshot
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
        # 来源 C 形态门随本锚定判(T-27 利息条件腿,中途审查复裁):
        # 处置 token = 'reanchor' → 备战帧已锚本节点 = 常规形态(基座 =
        # 备战帧 gs.gold 观察,领取前真值);'advance'/'first_anchor' →
        # 本节点首次锚定发生在补给屏 = 「自动弹」形态 → 基座宁缺不计数。
        # 误分类方向恒宁缺(常规但备战锚失读 → advance → 漏计一刻,
        # 宁缺勿造向),无多计向。基座本体不在观察轮读——计数刻(领取
        # 完成后)现读 gs.gold 即备战帧观察值(补给访问期无金写端,零漂移)。
        _pos = self._read_node_bar(screen)
        if _pos is not None and _gs is not None:
            _anchor_token = observe_node_anchor(_gs, _pos,
                                                trigger_screen='货币战争-补给',
                                                actor='CwScreenSupplyNode')
            self._prep_anchored = (_anchor_token == 'reanchor')
        if _gs is not None:
            report_screen_supply_node_obs(_gs, obs)
        self._sup_opts = list(opts)
        return obs

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=8)
    def act(self) -> OperationRoundResult:
        """分发身份安全网 + 单动作(刷新结束本次访问 ∨ 选卡点击发出后即结束本次访问)。

        门 miss = 已离开本节点画面(分发身份安全网:确认链已发即离开 =
        节点完成)→ success 交还外层。动作两分支均终结本访问:刷新点钮后
        结束本次访问(外循环重进 = 入口重建);选卡经动作 op 确认点击后立即上报
        完整结果,派发即 round_success 终结(正本 = `screens/op-layer.md`
        §1.1、`flow/action_ops.md` §4.5,零重入
        裁决、零旧机制补写面)。"""
        if not self._in_node(self.last_screenshot):
            return self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)')
        if self._do_action():
            return self.round_success('动作已发,本访问终结交回(外循环重进重建入口)',
                                      wait=1.5)
        return self.round_wait(wait=1.5)

    def _do_action(self) -> bool:
        """决策 + 单动作体(零参:候选与点击点自观察轮实例载体消费)。

        决策 = 策略层单一源(``match.strategy.decide_supply()`` →
        ``strategies/impl/mandate_v1/supply.py`` 三级字典序);读不到选项
        → CARD_BODY 兜底。刷新分支 = 剩余对照闸放行(容器
        ``supply_refresh_left`` >0 且锚点在位)才点圆钮,点后 2s 结束本次访问;
        建议刷但对照闸拒绝 → 重调一次(纯函数同输入同输出仍建议刷)→
        零点击结束本次访问。
        选卡分支点卡身 + 确认机械半经工厂(注册表 ``action_op_for`` 派发
        ``cw_pick_supply_action.CwActionPickSupplyOp``,替身缝 = 工厂派发调用点),
        确认点击后动作 op 立即上报完整结果,点击发出后即结束本次访问。
        Returns: True = 动作已发(结束本次访问)。
        """
        match = self.ctx.cw_match
        opts = self._sup_opts or []
        # 导入无条件置顶:派发段(下方 CARD_BODY 兜底路径)也构造
        # CwActionPickSupplyParam,分支内导入会使兜底路径 UnboundLocalError
        #(sim 局 = 声明姿态「act 恒走 CARD_BODY 兜底」,模块头已登记)。
        from sr_od.application.currency_war.kernel.cw_vocab import (
            CwActionPickSupplyParam,
            CwActionRefreshSupplyParam,
        )
        target = CwScreenSupplyNode.CARD_BODY
        reason = 'no-options(CARD_BODY 兜底)'
        refresh_target = None
        # 派发实例真实选中下标(上报 param 即真实选择;兜底/刷新轮 = 0 占位)。
        param_idx = 0
        # 开出内容载荷(空串 = 兜底点卡路径/装备名未解析——报告侧按「内容未知/未解析/无装备名列」分型)。
        picked_char = ''
        picked_norm_item = ''
        # 列内附加装备归一件名(画面 y 序;默认 () = 单装备布局/兜底路径)。
        picked_extra_norm: tuple[str, ...] = ()
        # 本轮选定快照(选定事实现场载荷;None=兜底点卡路径/刷新路径)。
        # 现役消费面 = 零(选定事实现场载荷,遥测接线候批)。
        picked: dict | None = None
        if match is not None and opts:
            # 零参决策(写槽已由观察轮 report 落容器 supply;决策调用形态
            # 不变,同访问覆盖写)。
            _gs = match.gs
            # 剩余对照闸读源 = 容器 supply_refresh_left(观察轮 report 摄入
            # 的同帧读数;None = 未观察/读缺,≤0 = 已刷尽)。
            _left = _gs.supply_refresh_left.value
            pick = match.strategy.decide_supply()
            if isinstance(pick, CwActionRefreshSupplyParam) \
                    and not (_left is not None and int(_left) > 0
                             and self._refresh_point is not None):
                # 对照闸拒绝 → 重调一次(判据侧次数闸已内嵌 decide,同输入
                # 同输出仍建议刷;本面 = 刷新锚点缺失对照兜底)。
                pick = match.strategy.decide_supply()
                if isinstance(pick, CwActionRefreshSupplyParam):
                    # 重调仍建议刷新 = 刷新锚点缺失面,零点击结束本次访问
                    #(外循环重进 = 入口重建重试观察,不空转本节点预算)。
                    log.warning('[cw-supply] 建议刷新但剩余闸拒绝(left=%r)'
                                ' → 零点击终结交回(外循环重进重试观察)',
                                _left)
                    return True
            if isinstance(pick, CwActionRefreshSupplyParam):
                # 剩余闸放行:点圆钮一次后结束本次访问(外循环重进 = 入口重建,
                # 新装备面由重进后的入口观察现读承载)。
                refresh_target = Point(
                    self._refresh_point.x + CwScreenSupplyNode._REFRESH_BTN_DX,
                    self._refresh_point.y)
                reason = pick.reason
            elif isinstance(pick, CwActionPickSupplyParam) and 0 <= pick.idx < len(opts):
                target = opts[pick.idx][1]
                reason = pick.reason
                param_idx = pick.idx
                # 选定快照(角色/首件装备/附加装备/钻;refresh_left=容器剩
                # 余次数现值快照,可 None——布尔键随计数闸消亡,left 供读端
                # 按剩余分型,无「本局初始授予数」基线故携带而非推导)——
                # 选定事实现场载荷,现役消费面 = 零(遥测接线候批;复盘
                # 渲染方 = tools/cw/replay_to_md.py「画面-补给」画面章)。
                _opt = opts[pick.idx][0]
                picked = {'char': _opt.char, 'equip': _opt.equip,
                          'has_diamond': _opt.has_diamond,
                          'extra_equips': _opt.extra_equips,
                          'refresh_left': _left}
                # 开出内容载荷(归一件名 = 注册表级分层归一
                # ``normalize_registry_equip_name`` 现算:精确快道 →
                # containment longest-first → 相似救援唯一命中;多/零命中
                # = '' 禁猜,报告侧逐件翻来源留存证据)。
                picked_char = _opt.char
                picked_norm_item = normalize_registry_equip_name(_opt.equip)
                picked_extra_norm = tuple(
                    normalize_registry_equip_name(e)
                    for e in _opt.extra_equips)
                # GameState 选定记录(chosen_supply)——**确认即写**(口径分叉
                # 显式申报:supply 直写,chosen_tome 维持「出口验真后写」家族
                # 口径不变——差异理由 = supply 的中转暂存宿主已随执行层状态
                # 类目停用,直写是暂存载体消亡后的唯一形态;chosen_tome 无
                # 暂存载体。确认未落地窗内容器短暂持未落地值:容器
                # chosen_supply 无决策读者,低危可接受;兜底点卡/刷新轮不写
                # = 真选守卫(与本分支互斥)。)值 = (角色,装备名列表)
                # 2 元组(OCR 原文 y 序;不带钻字段——有没有钻石让消费侧
                # 自行按名单派生,写端单点本分支)。
                try:
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        ChannelSig,
                    )
                    _gs.write_logic(
                        _gs.chosen_supply,
                        (_opt.char, (_opt.equip, *_opt.extra_equips)),
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
        # 防吞点击:click 前 mouse_move 到目标(零移动),防 before_screenshot 移光标 → click 落空。
        if refresh_target is not None:
            self.ctx.controller.mouse_move(refresh_target)
            self.ctx.controller.click(refresh_target)
            # 用户口述口径(docs/game/currency_war/research/screen_flow_timing.md
            # #19):补给屏刷新后 2s 画面稳定——原 0.6s 依赖「下一轮
            # wait 1.5s」合计 2.1s,余量仅 0.1s,重掷动画尾帧可能被读(选项读缺
            # → 决策建立在残缺选项上)。等满 2s 再结束本次访问。
            time.sleep(2.0)
            return True
        # 点卡选中 → 确认机械半经工厂(刷新圆钮机械点击留在上方——刷新链 =
        # CwActionRefreshSupplyParam 建议的执行半,
        # pick execute 语义 = 点卡选中 → 确认)。派发实例携真实选中下标与
        # 开出内容载荷(上报 param 即真实选择+内容;动作 op 确认点击后
        # 立即一口写 owned/单位腿/后果腿;无 match 兜底路径同形派发,
        # 内容空 = 报告侧内容未知分型)。点击发出后即结束本次访问。
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, match=match, idx=param_idx,
                                  target=target, picked=picked)
        _param = CwActionPickSupplyParam(idx=param_idx,
                                         char_name=picked_char,
                                         norm_item=picked_norm_item,
                                         extra_norm_items=picked_extra_norm)
        action_op_for(_param, self.ctx, _env).execute()
        # 来源 C 计数刻 = 领取补给动作完成后(收入已入账,推算+计数归组
        # 清晰;T-27 设计 §2.5)。
        self._count_interest_after_pick(match)
        return True

    def _count_interest_after_pick(self, match) -> None:
        """领取完成刻的息推算计数(T-27 来源 C;best-effort,失败不阻塞
        节点收尾)。

        - 基座金 = 备战帧 gs.gold 观察(常规形态:出战/进补给节点前最后
          备战帧观察;「获取补给之后」定谳下即领取前真值,补给访问期无
          金写端零漂移,计数刻现读即该值)。形态门 = ``_prep_anchored``
          (观察轮节点条锚定 token 判,见 ``_observe_live``):「自动弹」
          形态(本节点首次锚定发生在补给屏,无备战帧)宁缺不计数——中途
          审查复裁(设计稿 v2.4 微批 §2.5 来源 C,原「货币计数定点读」
          前提经帧证据证伪后改签);接管局形态(进入时补给已被领取)同归
          宁缺(披露面);
        - 刷新分支/对照闸拒绝路径不经本方法(领取未发生即终结本访问,
          外循环重入重观察)→ 天然防补给 op 重入双计;
        - cap/flat 推算单一源 = estimate_node_interest(kernel 公式纯读,
          经 obs/cw_settlement_obs 惰性 import——避免补给模块级拉入结算
          obs 读链外的重导入面,函数内惰性为本包既有破环纪律);
        - sig = logic_hook 族,actor = 本 op 类名,组号
          'supply-node:env-grant'(宿主 op 申报,台账归组可对账)。
        """
        if match is None:
            return   # 局外兜底路径无容器,零计数
        try:
            from sr_od.application.currency_war.kernel.cw_env_grants import (
                check_env_interest_grants,
            )
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
            )
            from sr_od.application.currency_war.obs.cw_settlement_obs import (
                estimate_node_interest,
            )
            _gs = match.gs
            _base_gold = (_gs.gold.value if self._prep_anchored else None)
            _est = estimate_node_interest(_gs, _base_gold)
            if _est is None:
                log.info('[cw-supply] 息推算基座缺失(自动弹形态/金未观察)'
                         '→ 宁缺不计数')
                return
            _gs.effects.record_interest_earned(int(_est))
            granted = check_env_interest_grants(
                _gs,
                ChannelSig(family='logic_hook',
                           actor='CwScreenSupplyNode',
                           group_id='supply-node:env-grant'))
            if granted is not None:
                log.info(f'[cw-supply] 利息条件发放:{granted}'
                         f'(累计息{_gs.effects.interest_earned})')
        except Exception as e:   # noqa: BLE001  计数面不阻塞节点动作
            log.warning(f'[cw-supply] 补给息计数失败(不阻塞): {e}')
