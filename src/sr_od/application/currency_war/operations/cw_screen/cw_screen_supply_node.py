
"""货币战争 补给节点画面 op(旧补给节点执行器已停用,逻辑内联于此)。

补给阶段 = 动态 N 选 1 装备 + 确认(通常 4 选 1;「全都要」类效果减 2 列、「人身意外险」类
加补给阶段可增列,augment 改写下实测 3-5 不等——历史「3 选 1」「实测 5」均为特例表述,
列数以 read_supply_options 实际识别为准,禁写死;钻(红/蓝/财富宝钻)视觉判定
在观察读链 ``read_supply_options`` 内;刷新按钮实存(「剩余次数」文锚左侧圆钮,
``_REFRESH_BTN_DX`` 文本锚定)。

动作:观察 node 读屏一次(选项 + 刷新剩余同帧)→ report 落容器 → 决策动作
node 零参决策(``match.strategy.decide_supply()``,判据单一源 =
``strategies/impl/mandate_v1/supply.py`` 三级字典序:钻>终局角色>装备;
三级全空才刷,次数闸内嵌 decide)→ 空候选零点击终结 / 刷新终结 / 选卡派发。

**决策输入与门槛统一到 obs 载体**(根修,契约正本 = flow/README §2.2
pick 族「容器槽零参读」+ 同族 9 决策面 op 既成约定):候选与门槛读
``self._obs.options``(``CwScreenSupplyNodeObs.options``,两态同构——实机 =
``_observe_live`` 同帧产物,与执行载体同读链同帧;sim = 观察改道生成器产物
``cw_sim_obs_gen.gen_supply`` 吃容器现值组装)。空候选 = 零点击
``round_success`` 终结交回(外循环重进重建入口重读),**禁盲选派发**——
选卡确认不可逆消耗本节点(正本 = ``op-layer.md`` §1.1 出口③;同族先例 =
``cw_screen_encounter.act`` 空候选分支)。无 match 局外不设早退支(画面 op
不支持局外单独调用,缺上下文沿正常链路失败即预期)。

守卫(对齐遭遇屏双守卫,正本 = ``op-layer.md`` §1.1 出口③/§1.3):①决策
返回非 ``CwActionPickSupplyParam``(词表外/None)→ 具名 ``round_fail``
零盲发,消息含策略器原值 repr 留证;②``pick.idx`` 越界 →
``AssertionError`` 守卫断言禁钳位(越界放行会确认错卡不可逆)。两守卫均在
派发前、零点击。

机械执行两态(分流判别式 = ``cw_sim_ports.mechanical_io_allowed()``):实机
点击点 = 执行载体 ``_card_points[pick.idx][1]``(读链产物,经
``OverlayPickExecEnv.target`` 传入动作 op);sim = ``env.target`` 传 None
(动作 op 机械腿端口检查自动跳过,世界反应由上报声明链驱动:上报真内容 →
内容腿入账 → ``WorldDecl(pick_supply)`` → 后端读 ``chosen_supply`` 现值
派生宝钻腿)。``_card_points``/``_refresh_point`` = 实机专用执行载体:
只被机械执行消费,**禁承载决策输入、禁作决策门槛**。

**刷新 = 终结动作**:decide_supply 建议刷新 ∧ 对照闸放行 → 点钮一次后本访问
终结交回(op 返回主循环重进 = 入口重建,新装备面由重进后的入口观察现读承载,
访问内零重读零二次覆盖写零重决策)。**对照闸 = 剩余语义观察真值**(用户裁定,
全域规范 = ``op-layer.md`` §1.4):闸条件全式 = 容器 ``supply_refresh_left``
读数 ≥1(读缺跳写、容器留残值由逐访问覆盖语义承接)∧ 锚点分量(实机 =
``_refresh_point`` 在位,锚缺并入拒绝面防机械点击 None;sim = 无锚点条件,
恒过)。两态执行:实机 = 文本锚定点 + ``_REFRESH_BTN_DX`` 机械点击 + 2s 固定
等待(screen_flow_timing.md #19);sim = 「文本-剩余次数」area 点击(基类
sim 改道 ``click_answer`` → 后端 ``_handle_click_source`` →
``_supply_refresh``:剩余闸内嵌再验 + left−1 + 选项重掷经同名 report 落
容器;点击源语义权威源 = ``sim/sim-design.md`` §3.2)。
**对照闸拒绝**:重调一次决策(纯函数同输入同输出);仍建议刷 → 实机
``round_fail`` 交回(计入外循环 ``OP_FAIL_REDISPATCH_LIMIT``,防线先例 =
``cw_screen_encounter.act``)/ sim 零点击终结交回(拒绝仅剩 left 读缺形态,
重进重读即恢复)。

``chosen_supply`` = 确认即写特殊口径(选定中转暂存宿主已停用,直写是载体
消亡后的唯一形态)留在决策体真选分支,派发前写(``op-layer.md`` §2.2 动作
事实边界硬规则);数据源 = obs 载体(与执行载体同帧同源,两态一致)。
``_count_interest_after_pick`` = 来源 C 计数刻,零改动(读容器现读;sim 形态
门恒关 → 恒宁缺不计数,安全向)。

T#103:确认按钮进 screen_info(货币战争-补给 按钮-确认);卡身点击点由 read_supply_options 按列返回。

形态:观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node 另承载节点条锚定(顶部「备战阶段 X-Y」→
``observe_node_anchor``;锚定写端已登记 = `screens/op-layer.md` §2.1;
节点条锚定四分支处置规则表正本 = `game_state/node-derivation.md`
(E10 行)——补给「自动弹」形态的唯一锚定点)。观察 node = 节点完成门(``_in_node``,miss = overlay 消失 /
进了下一节点 = 节点完成,success 结束本次访问外层)+ 选项一次读(每访问恰一次,与
现役决策体读同帧等价,迁移不增加读屏)→ ``report_screen_supply_node_obs``
落容器 ``supply``(空 = 读缺零点击终结路径,闸在 report 内)→ obs 挂
实例属性进决策 node。决策动作 node = 空候选零点击终结 / 刷新终结 /
选卡派发,全部出口终结本访问(点击发出后即结束本次访问正本 =
`screens/op-layer.md` §1.1、`flow/action_ops.md` §4.5:动作 op 确认
点击后立即上报完整结果,零落地复查、零旧机制补写面——确认未生效 =
代码 bug,overlay 残留由外循环按当前画面重识别重派)。本屏 sim 腿 =
观察腿(生成器产物经同名 report 落容器)+ 决策腿(obs 载体两态同构)+
刷新腿(area 点击端口),等价判据支撑 = 实机已登记行为测试 + sim 两态
op 测试。
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
    SupplyOption,
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
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickSupplyParam,
    CwActionRefreshSupplyParam,
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
        # 观察结果(观察 node 产物,决策动作 node 消费)。决策输入与门槛
        # 唯一来源 = 本载体 ``options``(两态同构:实机 = _observe_live
        # 同帧产物;sim = 生成器产物),禁改挂其它载体。
        self._obs: CwScreenSupplyNodeObs | None = None
        # 实机专用执行载体 = 读链产物 [(选项, 点击点)]:只被机械执行消费
        # (``[idx][1]`` 取点传动作 op)。**禁承载决策输入、禁作决策门槛**——
        # 候选与门槛一律读 ``self._obs.options``(sim 观察改道不回填本载体,
        # 门槛挂错载体 = sim 策略器结构性不可达,决策链接线迭代根修对象)。
        # ``_refresh_point`` 同为执行载体(刷新钮文本锚点),处置同。
        self._card_points: list[tuple[SupplyOption, Point]] | None = None
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
        ``supply_refresh_left``(选项空 = 读缺零点击终结路径,整函数
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
        self._card_points = list(opts)
        return obs

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=8)
    def act(self) -> OperationRoundResult:
        """分发身份安全网 + 单动作(全部出口终结本访问/交回)。

        门 miss = 已离开本节点画面(分发身份安全网:确认链已发即离开 =
        节点完成)→ success 交还外层。动作出口两态全终结:空候选零点击
        终结交回;刷新点钮后结束本次访问(外循环重进 = 入口重建);选卡
        经动作 op 确认点击后立即上报完整结果,派发即 round_success 终结
        (正本 = `screens/op-layer.md` §1.1、`flow/action_ops.md` §4.5,
        零重入裁决、零旧机制补写面);对照闸拒绝防线 = 实机 round_fail /
        sim 零点击终结。"""
        if not self._in_node(self.last_screenshot):
            return self.round_success(f'{self.op_name} 节点完成(已离开本节点画面)')
        return self._do_action()

    def _refresh_gate_allows(self, left: int | None) -> bool:
        """刷新对照闸全式(两态分量不同,决策链接线迭代 design §2.2):
        容器 ``supply_refresh_left`` 读数 ≥1 ∧ 锚点分量——实机 =
        ``_refresh_point`` 在位(锚缺并入拒绝面,防「残值 ∧ 锚缺」帧机械
        点击 None,遭遇屏同款先例);sim = 无锚点条件(恒过,sim 腿不依赖
        锚点)。两态分流判别式 = ``cw_sim_ports.mechanical_io_allowed()``。
        纯读,零写。"""
        if left is None or int(left) < 1:
            return False
        return not (cw_sim_ports.mechanical_io_allowed()
                    and self._refresh_point is None)

    def _do_action(self) -> OperationRoundResult:
        """决策 + 单动作体(决策输入与门槛 = ``self._obs.options`` 载体)。

        决策 = 策略层单一源(``match.strategy.decide_supply()`` 零参,候选
        自容器 ``gs.supply`` 槽,判据 = mandate_v1 三级字典序)。出口:
        - 空候选 = 零点击 round_success 终结交回(禁盲选派发——选卡确认
          不可逆消耗本节点;重读由外循环重进重建入口承载);
        - 刷新(对照闸放行)= 点钮一次后终结交回:实机 = 锚点+dx 机械
          点击 + 2s 固定等待;sim = 「文本-剩余次数」area 点击经端口触发
          后端 ``_supply_refresh``;
        - 对照闸拒绝 → 重调一次(纯函数同输入同输出);仍建议刷 = 实机
          round_fail(计入外循环重派上限)/ sim 零点击终结交回;
        - 选卡 = 守卫①(词表外/None 具名 round_fail)②(idx 越界
          AssertionError 禁钳位)后派发确认链(动作 op),派发即终结。
        """
        obs = self._obs
        # 决策输入与门槛统一到 obs 载体(两态同构;先例 =
        # cw_screen_encounter.act 同款空候选分支在册)。
        options = obs.options if obs is not None else []
        if not options:
            log.info('[cw-supply] 候选读缺(options=%d) → 零点击终结交回重读',
                     len(options))
            return self.round_success('候选读缺,零点击终结交回重读', wait=1.5)
        # 无 match 局外不设早退支(先例 = cw_screen_encounter.act 注记;
        # op-layer.md §1.1:画面 op 不支持局外单独调用,缺上下文沿正常链路
        # 失败即预期,禁回填单跑防御分支)。
        match = self.ctx.cw_match
        _gs = match.gs
        # 剩余对照闸读源 = 容器 supply_refresh_left(观察轮 report 摄入的
        # 同帧读数;None = 未观察/读缺,≤0 = 已刷尽;读缺跳写容器留残值,
        # 由逐访问覆盖语义承接)。
        _left = _gs.supply_refresh_left.value
        pick = match.strategy.decide_supply()
        if isinstance(pick, CwActionRefreshSupplyParam) \
                and not self._refresh_gate_allows(_left):
            # 对照闸拒绝 → 重调一次(判据侧次数闸已内嵌 decide,同输入
            # 同输出仍建议刷;实机活面 = 刷新锚点缺失/残值∧锚缺,sim 活面
            # = left 读缺/残值形态)。
            pick = match.strategy.decide_supply()
            if isinstance(pick, CwActionRefreshSupplyParam):
                if cw_sim_ports.mechanical_io_allowed():
                    # 防线(实机):零点击 round_success 交回对「锚持续读缺 ∧
                    # 建议刷恒成立」无防护,round_fail 计入外循环
                    # OP_FAIL_REDISPATCH_LIMIT 有界收敛(防线先例 =
                    # cw_screen_encounter.act 同款)。
                    log.warning('[cw-supply] 重调仍建议刷新(对照闸拒绝,'
                                'left=%r) → round_fail 交回(计入重派上限)',
                                _left)
                    return self.round_fail('刷新锚点读缺,交回重读')
                # sim:无机械锚读缺面,拒绝仅剩 left 读缺形态,零点击终结
                # 交回(重进重读即恢复;先例 = 遭遇 sim 刷新腿零点击终结)。
                log.info('[cw-supply] 建议刷新但对照闸拒绝(sim,left=%r)'
                         ' → 零点击终结交回', _left)
                return self.round_success('建议刷新但对照闸拒绝,零点击终结交回',
                                          wait=1.5)
        if isinstance(pick, CwActionRefreshSupplyParam):
            # 剩余闸放行:刷新 = 终结动作(op-layer.md §1.4),两态分流判别
            # 式 = mechanical_io_allowed()。点钮后本访问终结交回,新选项由
            # 外循环重进后的入口观察现读承载。
            if cw_sim_ports.mechanical_io_allowed():
                target = Point(
                    self._refresh_point.x + CwScreenSupplyNode._REFRESH_BTN_DX,
                    self._refresh_point.y)
                log.info('[cw-supply] 建议刷新 → 圆钮@(%d,%d)(文本锚定)'
                         ' 点钮一次后终结交回', target.x, target.y)
                # 防吞点击:click 前 mouse_move 到目标(零移动),防
                # before_screenshot 移光标 → click 落空。
                self.ctx.controller.mouse_move(target)
                self.ctx.controller.click(target)
                # 用户口述口径(docs/game/currency_war/research/
                # screen_flow_timing.md #19):补给屏刷新后 2s 画面稳定
                # ——原 0.6s 依赖「下一轮 wait 1.5s」合计 2.1s,余量仅 0.1s,
                # 重掷动画尾帧可能被读(选项读缺 → 决策建立在残缺选项上)。
                # 等满 2s 再结束本次访问(固定等待归产生动画的操作)。
                time.sleep(2.0)
                return self.round_success(
                    '补给刷新已点,本访问终结交回(外循环重进重建入口)',
                    wait=1.5)
            # sim:刷新腿 = 点击源端口——「文本-剩余次数」area 点击经基类
            # sim 改道(→ 后端 ``_handle_click_source`` → ``_supply_refresh``:
            # 剩余闸内嵌再验 + left−1 + 选项重掷经同名 report 落容器)。
            # 点击后本访问终结交回,新选项由重进后的入口观察承载(生成器
            # 吃容器现值,零重采样漂移)。点击源语义权威源 =
            # sim/sim-design.md §3.2 点击源行。
            self.round_by_find_and_click_area(
                self.last_screenshot, '货币战争-补给',
                CwScreenSupplyNode._REFRESH_TEXT_AREA)
            return self.round_success(
                '补给刷新已点(sim area 点击),本访问终结交回', wait=1.5)
        # 守卫①(返回契约,op-layer.md §1.1 出口③):决策无有效输出(词表
        # 外/None)= 具名 fail 零盲发;消息含策略器原值 repr = 留存证据
        #(round_fail 消息经框架节点状态日志落盘,不另加独立日志行)。
        if not isinstance(pick, CwActionPickSupplyParam):
            return self.round_fail(
                f'decide_supply 决策无有效输出(词表外/None): {pick!r}')
        # 守卫②(值域,op-layer.md §1.3):idx 越界 = 策略器 bug,守卫断言
        # 响亮暴露,禁钳位——动作 op 执行即发出点击链,越界放行会确认
        # 错卡(不可逆),必须拦在派发前。
        if not (0 <= pick.idx < len(options)):
            raise AssertionError(
                f'[cw-supply] pick idx 越界(策略器 bug,禁钳位): '
                f'idx={pick.idx} len(options)={len(options)} pick={pick!r}')
        # 选定内容载荷自 obs 载体构造(决策输入单一源;与执行载体同帧同源
        # ——实机 _observe_live 同帧赋值,sim = 生成器产物,两态一致)。
        _opt = options[pick.idx]
        # 开出内容载荷(归一件名 = 注册表级分层归一
        # ``normalize_registry_equip_name`` 现算:精确快道 →
        # containment longest-first → 相似救援唯一命中;多/零命中
        # = '' 禁猜,报告侧逐件翻来源留存证据)。
        picked_char = _opt.char
        picked_norm_item = normalize_registry_equip_name(_opt.equip)
        picked_extra_norm = tuple(
            normalize_registry_equip_name(e)
            for e in _opt.extra_equips)
        # 选定快照(角色/首件装备/附加装备/钻;refresh_left=容器剩
        # 余次数现值快照,可 None——布尔键随计数闸消亡,left 供读端
        # 按剩余分型,无「本局初始授予数」基线故携带而非推导)——
        # 选定事实现场载荷,现役消费面 = 零(遥测接线候批;复盘
        # 渲染方 = tools/cw/replay_to_md.py「画面-补给」画面章)。
        picked = {'char': _opt.char, 'equip': _opt.equip,
                  'has_diamond': _opt.has_diamond,
                  'extra_equips': _opt.extra_equips,
                  'refresh_left': _left}
        # GameState 选定记录(chosen_supply)——**确认即写**(口径分叉
        # 显式申报:supply 直写,chosen_tome 维持「出口验真后写」家族
        # 口径不变——差异理由 = supply 的中转暂存宿主已随执行层状态
        # 类目停用,直写是暂存载体消亡后的唯一形态;chosen_tome 无
        # 暂存载体。确认未落地窗内容器短暂持未落地值:容器
        # chosen_supply 无决策读者,低危可接受;空候选/刷新轮不写
        # = 真选守卫(与本分支互斥)。)值 = (角色,装备名列表)
        # 2 元组(OCR 原文 y 序;不带钻字段——有没有钻石让消费侧
        # 自行按名单派生,写端单点本分支)。数据源 = obs 载体(两态一致)。
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
        log.info('[cw-supply] options=%s pick=idx%d %s left=%s',
                 [(o.char, o.equip, o.has_diamond) for o in options],
                 pick.idx, pick.reason, _left)
        # 机械执行两态:实机点击点 = 执行载体 ``_card_points[pick.idx][1]``
        # (读链产物);sim = None(动作 op 机械腿端口检查自动跳过,世界
        # 反应由上报声明链驱动)。
        _click_target = (self._card_points[pick.idx][1]
                         if cw_sim_ports.mechanical_io_allowed() else None)
        # 点卡选中 → 确认机械半经工厂(刷新圆钮机械点击留在上方——刷新链 =
        # CwActionRefreshSupplyParam 建议的执行半,
        # pick execute 语义 = 点卡选中 → 确认)。派发实例携真实选中下标与
        # 开出内容载荷(上报 param 即真实选择+内容;动作 op 确认点击后
        # 立即一口写 owned/单位腿/后果腿)。点击发出后即结束本次访问。
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, match=match, idx=pick.idx,
                                  target=_click_target, picked=picked)
        _param = CwActionPickSupplyParam(idx=pick.idx,
                                         char_name=picked_char,
                                         norm_item=picked_norm_item,
                                         extra_norm_items=picked_extra_norm)
        action_op_for(_param, self.ctx, _env).execute()
        # 来源 C 计数刻 = 领取补给动作完成后(收入已入账,推算+计数归组
        # 清晰;T-27 设计 §2.5)。
        self._count_interest_after_pick(match)
        return self.round_success('补给选卡确认链已派发,本访问终结交回',
                                  wait=1.5)

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
