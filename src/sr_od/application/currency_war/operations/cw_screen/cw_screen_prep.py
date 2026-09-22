"""备战执行器 CwScreenPrep:画面执行 / 对账接线(依赖 obs/ 识别工具箱,
留 app 合法向)。

对账职责 = 纯观察审计族(羁绊显示,heavy 定型帧
消费,留守观察 node);动作上报的对账归一走 op 自上报(上报函数族)+
观察边界 cw_reconcile 兜底。

形态(两 node 直继承 SrOperation):观察 node = 环装配前置(执行器构建
/缓存复位)+ 环入口清场 + 开商店收起 + heavy 观察 → CwScreenPrepObs
(可选域经 report_screen_prep_obs 落容器)+ 事件 overlay 交回早退 +
接管补采委派 + 纯观察审计族;决策动作 node = 单动作决策循环(无防御
上限,用户裁定:不收敛 = 策略实现 bug)。书册卡的开卡时机归策略实现管
(用户裁定 2026-09-19):观察链产 kind='bookcard' 槽位,策略器 entry ①
卡片臂发射终结动作,本画面 op 不再代发。
"""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchView,
    ChannelSig,
    OreSight,
    game_state_of,
    gs_of_ctx,
    node_ordinal_of,
    observe_node_anchor,
)
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.kernel.cw_overlay_registry import (
    derive_clearable,
    derive_decision,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PrepObservation,
)
from sr_od.application.currency_war.kernel.cw_screen_report.prep import (
    CwScreenPrepObs,
    report_screen_prep_obs,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionObsParam,
    CwActionOpenShopParam,
    CwActionStartBattleParam,
    action_key,
)
from sr_od.application.currency_war.obs.currency_war_cv import slot_occupied
from sr_od.application.currency_war.obs.cw_faction_obs import (
    compare_factions,
    read_displayed_factions,
    report_faction_reconcile,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    ensure_portrait_templates,
    read_ore_sights,
)
from sr_od.application.currency_war.obs.cw_observation import (
    board_from_tracked,
    build_prep_node_chain,
    read_deploy_cap,
    read_deployed_count,
    read_node_sequence,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
    action_op_class_for,
)
from sr_od.application.currency_war.operations.cw_op.cw_obs_action import (
    CwObsOverlayBail,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_bookcard_action import (
    CwActionOpenBookcardOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_box_action import (
    CwActionOpenBoxOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_open_shop_action import (
    CwActionOpenShopOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_start_battle_action import (
    CwActionStartBattleOp,
)
from sr_od.application.currency_war.prep_actions import (
    PrepActionExecutor,
    StopBrakeShortCircuit,
    row_area_centers,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        CurrencyWarMatch,
    )

# ===== 环入口清场段:环入口可一键关闭的 overlay 注册表(唯一消费方 = 本文件
# _clear_entry_overlays;单一源仍是 ``cw_overlay_registry.derive_clearable()``
# 派生桥接)=====
#: 只收「无决策语义的弹窗/面板」——星徽秘典/补给已 decision 化(关闭即丢
#: 决策内容,C1 红线),从清场集消失,改走 event_overlay bail → 0i 选卡 /
#: CwScreenSupplyNode 消化;投资环境/投资策略/选择伙伴/盛会之星/祈愿试炼
#: 等交互 overlay 同理,不进派生集。
ENTRY_OVERLAY_CLOSE: dict[str, str] = {
    spec.screen_name: spec.close_area for spec in derive_clearable()
}
#: 清场轮数上限(每轮:逐屏锚探 → 命中点关闭 → settle;无命中即出)。
ENTRY_OVERLAY_CLEAR_ROUNDS: int = 4
#: 点关闭后的画面过渡等待(秒)。
ENTRY_OVERLAY_SETTLE_S: float = 1.0


def faction_display_ok_debug_line(row_count: int, ocr_skip_count: int,
                                  suspects: list[str],
                                  computed_missing_count: int) -> str:
    """羁绊显示对账 ok 分支的 debug 行(纯函数,零决策)。

    疑截断行名非空时随行附列——纯计数留不下「哪几行被疑」,mismatch=0
    的稳定态行名不可考(复盘 g_20260903_232823 §4:恒 4 行疑截断无档)。
    只在非空时附带,空列表保持旧行形(计数后无括号段)。
    """
    return (f'[cw][director] faction_display reconcile: '
            f'ok({row_count}行) '
            f'ocr_skip={ocr_skip_count} '
            f'trunc_suspect={len(suspects)}'
            + (f'({",".join(suspects)})' if suspects else '')
            + f' computed_missing={computed_missing_count}')


class CwScreenPrep(SrOperation):
    """备战决策环(两 node 形态):观察 node(环装配前置 + 清场 + heavy
    观察 → CwScreenPrepObs 可选域 report 落容器 + 事件 overlay 早退 +
    接管补采委派 + 纯观察审计族)→ 决策动作 node(单动作决策循环整体:
    决策(容器 game state 直读,F3 形状校验)→ 执行(机械执行无成败
    回执;终结 op 发出即交回外循环)→ 逻辑态直写(动作 op 自上报))。
    决策循环无防御上限(用户裁定:不收敛 = 策略实现 bug)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-备战决策环')
        self._executor: PrepActionExecutor | None = None
        self._bench_pts = []                        # screen_info 槽位中心(首步惰性读)
        # on_outcome 落地登记注册表随画面 op 基类退役:本 op 级登记件原两件
        # = 经验期望账本推进(CwActionLevelUpParam/CwActionOpenShopParam 两通道),随
        # 期望账拆除退役——「未落地不计数」防线
        # 由逻辑态直写(买经验自上报)与观察覆盖
        # 承接。执行器内
        # 登记件(刷新计数组免费闸 record_refresh_execution、免战牌
        # consume_use,现役接线点 = cw_op_buy_cards 执行落地门/kernel
        # apply_op_effect 上报路径)留守执行器(该执行链为双路径共链,
        # 迁移即生产行为变化;免费闸/随点击置位等语义以现役位置逐字保绿)。

    # ===== 观察(只由现成 reader 产出)=====

    def _observe(self, heavy: bool, screen: MatLike | None = None) -> PrepObservation:
        """组装备战观察(heavy = 画面 op 入口单次——期望态
        重建的唯一读屏点,即对账;调用点 = 单轮入口 / reobserve_in_visit
        (CwActionObs 环内重观察在册通道))。旧「每个执行过的游戏动作后必调 heavy」契约已
        随单动作循环退役:逐动作零读屏,期望态由上报函数族(kernel)纯计算
        推进,动作后首读的光标 parking 职责随之迁移(入口观察 park 一次;
        执行侧读数性通道——卖出回金遥测等——的局部 park 由动作实现层自理)。

        screen 传入时(调用方持有已验证稳定帧时)复用该帧不重截——稳定帧的
        全图 OCR 已按 id(image) 缓存,本方法所有 crop_first=False 读取
        (id_mark 判定/observe_full)全部缓存命中,heavy 观察的 OCR 成本归零;
        且观察的就是「已验证稳定」的那一帧,而非稳定后又隔一拍的帧。
        """
        if heavy:
            self.park_cursor()
        screen = screen if screen is not None else self.screenshot()
        obs = PrepObservation()
        if not self._bench_pts:
            self._bench_pts = row_area_centers(self.ctx, '备战栏')
        # 轻:晶矿/箱/典籍/overlay/占用(每步现读)
        # 晶矿读带两帧持存交叉验证(奖励域防幻检):瞬态特效假圆下一帧
        # 即消失,不采信;本帧原始读数(含黑名单过滤)存为下帧 prev
        #(实例属性跨步存活;CwScreenPrep 每备战环重建 → 跨环不残留,
        # 语义 = 环内连续帧)。
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            filter_persistent_ores,
        )
        _spheres_raw = read_ore_sights(self.ctx, screen)
        _prev_spheres = getattr(self, '_prev_spheres_raw', None)
        _sph_list = (filter_persistent_ores(_spheres_raw, _prev_spheres)
                     if _prev_spheres else _spheres_raw)
        self._prev_spheres_raw = _spheres_raw
        # (箱/典籍/书册卡占槽物品的识别与 kind 细分已随 P6 观察链直产移驻
        #  读链 read_bench_view(同帧 _bench_item_kind_by_slot)——轻段不再
        #  现读三族槽号集,heavy 观察少三次冗余扫描,写端语义不变。)
        obs.shop_open = self.round_by_find_area(
            screen, SHOP_SCREEN_NAME, '按钮-收起', crop_first=False).is_success
        # 事件 overlay(挡操作:deploy/equip 全灭根因,live 2026-08-15):检测到即由环 bail 交外环。
        # 扫描集单一源 = kernel/cw_overlay_registry 的 decision 派生段(B 面切换,
        # 零成员变化):锚 = spec.anchor_area,tag = spec.bail_tag,消费方拼
        # '事件overlay:' 前缀。命中即短路;break 语义与手写清单时代一致。
        # 遍历序 = 注册表声明序(与旧手写序不同但行为等价):各 decision overlay
        # 是全屏顶层弹窗,单帧锚互斥(历史帧组 ≤1 命中实证),先命中哪个即哪个
        # overlay 在场;且任一 decision overlay 在场的外层行为相同(即刻 bail 交
        # 外环 handler),序只影响多命中假想帧的 tag 归属。
        for _spec in derive_decision():
            if self.round_by_find_area(
                    screen, _spec.screen_name, _spec.anchor_area,
                    crop_first=False).is_success:
                obs.event_overlay = _spec.bail_tag
                break
        # (席空数 = 容器 bench_free_slots 派生,前排槽数 =
        #  row_area_centers 现算;front/back_occupied = 对拍腿识别轻字段,
        #  消费在观察链内部存续。)
        front_pts = row_area_centers(self.ctx, '前排')
        back_pts = row_area_centers(self.ctx, '后排')
        obs.front_occupied = {i + 1 for i, p in enumerate(front_pts)
                              if slot_occupied(screen, int(p.x), int(p.y))}
        obs.back_occupied = {i + 1 for i, p in enumerate(back_pts)
                             if slot_occupied(screen, int(p.x), int(p.y))}
        # 重:身份/星级/cap(入口 heavy + 环内 CwActionObs 重观察)
        if heavy:
            # 可重定位读取(身份/gold==0 重读/substate)进组装层
            # 单一源(observe_full);director 保留副作用编排(session 写/审计/
            # 缓存——单写者原则)。
            from sr_od.application.currency_war.obs.cw_observe_full import (
                observe_full,
            )
            _of = observe_full(self.ctx, screen, tier='heavy',
                               source='director', op=self,
                               shop_open=obs.shop_open,   # gold 仅 shop 开态可信门
                               session=self._session())   # SIFT 三层漏斗(session 优先匹配)
            # P6 观察链直产:observe_full 回传容器形状(备战席 BenchView /
            # 上场位 (前排, 后排) Unit 行)。templates 未加载 → None → 下方
            # 换空载体(与旧 [] 等价:对账空读可清账、容器写端 carry)。
            _bench_view = _of.get('bench_view')
            _deployed_rows = _of.get('deployed_rows')
            _wr, _bench_obs, _dep_rows = self._reconcile_tracking(
                _bench_view, _deployed_rows, screen)
            _st = _of.get('read_receipt')
            session = self._session()
            # PrepObservation 消费切换转适配器:
            # 决策读自 GameState 容器单例(read_game_state 漏斗直写;
            # 旧 last_state 装配源契约随装配源迁移终结,换源核销;
            # obs.state 视图槽已随黑板槽退役消亡)。
            if session is not None:
                from sr_od.application.currency_war.kernel.cw_reconcile import (
                    is_merge_effect_window,
                )
                _gs_obs = gs_of_ctx(getattr(self, 'ctx', None), session)
                # 备战帧节点锚定(迭代 2026-09-20-node-advance-action-report
                # design §2.4 写端 1,攻击 F1 定谳):heavy 观察回执携带本帧
                # plane/round → observe_node_anchor(处置规则 = kernel
                # helper 单一源:first_anchor/advance 补推/reanchor/
                # stale_dropped)。锚定输入与旧备战腿同源(read_phase_round
                # 直读/缓存/守卫语义不变);漏斗已退出推进域,本写端 = 干净
                # 备战帧的唯一生产锚定点(外循环仲裁路径的 prep_clean 漏斗读
                # 不挂锚定,攻击 R4 辖域界定)。读数缺位/局外 = 跳过(禁猜,
                # best-effort 不阻塞观察链)。
                if _st is not None and _st.plane is not None \
                        and _st.round_num is not None:
                    with contextlib.suppress(Exception):
                        observe_node_anchor(
                            _gs_obs,
                            node_ordinal_of(int(_st.plane), int(_st.round_num)),
                            trigger_screen='货币战争-备战',
                            actor='CwScreenPrep')
                # 备战渠道签名:备战帧观察写入 = 渠道①,actor=本 op、
                # screen=备战建档名、quality=真读标记(承接现役真读/兜底可分
                # 语义)。
                _prep_sig = ChannelSig(family='obs', actor='CwScreenPrep',
                                       screen='货币战争-备战', mode='read',
                                       quality={'bench': 'real_read'})
                # 备战席观察写端(观察写端=本屏;P6 直产):read_bench_view
                # 直产容器视图(占位件 kind 识别期细分,零换形),对账门后
                # 副本随写(星级保旧/装备续接同帧共享)。
                # 空视图 = 失读非全空(overlay 残留/动画帧/识别退化)——
                # 走 carried(失读保旧值;宁缺勿造,先例=商店空牌面观察漏斗
                # shop_cards 分支),禁把「9 槽全空」当 observation 入记录
                # (席空数派生误报 free=9 污染席满决策)。
                if _bench_obs is not None and any(
                        s.kind != 'empty' for s in _bench_obs.slots):
                    # 合成特效窗态门:星爆动画窗(≥2 帧)内 read_star 读旧星
                    # (reconcile_tracking 防抖同口径,读数物理不可信)——本帧
                    # **不写观察**(保 bench 的 logic 逻辑态值,失读保旧值的
                    # 同族语义),下帧干净帧实读覆盖:逻辑态与实读一致 = 零缺陷
                    # 行;失配 = 逻辑态 bug 留证。原「挂起预期顺延核对」的
                    # 防噪声语义由此承接(原核对半随 expected 机制废除)。
                    if is_merge_effect_window(screen):
                        log.info('[cw][gs] 合成特效窗内读数不可信 → 本帧观察'
                                 '不写(保 logic 逻辑态值,下帧干净帧覆盖)')
                    else:
                        _gs_obs.observe(_gs_obs.bench, _bench_obs, sig=_prep_sig)
                else:
                    _gs_obs.carry(_gs_obs.bench,
                                  frame=(f'p{_st.plane}-r{_st.round_num}'
                                         if _st is not None else ''),
                                  sig=ChannelSig(
                                      family='obs', actor='CwScreenPrep',
                                      screen='货币战争-备战', mode='carried'))
                # 上场席位观察写端(与 bench 写端同环同纪律;P6 直产):
                # 行域直产自读链(排归属 = 行参承载),空行域 = 失读非全空
                # → carry,禁「全场无人」假观察;特效窗门同 bench
                # (star 读数物理不可信);front_row/back_row 观察照写。
                _dep_carried_sig = ChannelSig(
                    family='obs', actor='CwScreenPrep',
                    screen='货币战争-备战', mode='carried')
                if _dep_rows is not None and (_dep_rows[0] or _dep_rows[1]):
                    if is_merge_effect_window(screen):
                        # 与 bench 特效窗门同语义:窗内不写(保 logic 逻辑态值,
                        # 下帧干净帧实读覆盖),不落 carried 假新鲜度。
                        pass
                    else:
                        _gs_obs.observe(_gs_obs.front_row, _dep_rows[0],
                                        sig=_prep_sig)
                        _gs_obs.observe(_gs_obs.back_row, _dep_rows[1],
                                        sig=_prep_sig)
                else:
                    _dep_frame = (f'p{_st.plane}-r{_st.round_num}'
                                  if _st is not None else '')
                    _gs_obs.carry(_gs_obs.front_row,
                                  frame=_dep_frame,
                                  sig=_dep_carried_sig)
                    _gs_obs.carry(_gs_obs.back_row,
                                  frame=_dep_frame,
                                  sig=_dep_carried_sig)
                # 备战帧现行链写端:slots 由 observe_full
                # heavy 回传(原弃槽点改造),写容器在 director 侧(单写者
                # 原则);逐格映射/写门/基线回填语义见函数 docstring。
                _write_prep_node_chain(session, _of.get('node_slots'),
                                       _prep_sig)
                # 装备库存观察写端:owned
                # 采集已归位本入口观察链(observe_full heavy),写端随迁本
                # 装配点——原写点 = prep_actions._build_equip_wear_plan 两
                # 分支,随其三路现读退役消失。全量名单入记录(采集层无权
                # 丢数据,工具件照录);失读(None)= 识别域未就绪
                # 不写保现值(宁缺勿造,同 bench 空集守卫族;装备区读不受
                # 合成特效窗影响,无需 is_merge_effect_window 门)。
                if _of.get('owned_equips') is not None:
                    # gs.equips 观察写端即单一源,商店线权重/
                    # flow 打分/库存 ±1 腿全部读容器。
                    _gs_obs.observe(_gs_obs.equips,
                                    list(_of.get('owned_equips')),
                                    sig=_prep_sig)
                if _of.get('occupied_equips') is not None:
                    # 穿戴位置观察写端:采集产物 {(row, slot): [件名]} → 容器键
                    # 'front:1' 形态(tuple 键 JSON 序列化不安全);失读
                    # None 不写保现值(同 owned 守卫族,宁缺勿造)。
                    _gs_obs.observe(
                        _gs_obs.occupied_equips,
                        {f'{row}:{int(slot)}': list(names)
                         for (row, slot), names
                         in _of.get('occupied_equips').items()},
                        sig=_prep_sig)
                # 晶矿点击目标观察写端(空读照写 count=0——空读 = 真无晶矿,
                # 跳写会留上一帧残留假晶矿坐标喂进点击载荷(幽灵晶矿);
                # 两帧持存防抖已在 _sph_list 现读链完成(本点只做形态搬运)。
                _sph_pts = tuple((color, int(p.x), int(p.y), int(r))
                                 for color, p, r in _sph_list)
                _gs_obs.observe(
                    _gs_obs.spheres,
                    OreSight(
                        count=len(_sph_pts),
                        colors=tuple(dict.fromkeys(
                            c for c, _p, _r in _sph_list)),
                        points=_sph_pts),
                    sig=_prep_sig)
                # 溢出告警观察写端(2026-09-15 实机建档 prep.md 告警/溢出节):横幅 = 游戏侧权威信号(出战被游戏忽略的
                # 处理门,策略消费 = mandate 溢出门强收窄);溢出位 SIFT =
                # 入位对象身份旁路(CwActionSellBenchParam 溢出腿;缺读 '' = 未识别,
                # 腿降级槽留空等下帧)。两读独立;横幅在场 = 唯一门语义,
                # 身份只作 tracked 闭合不作门。
                _ov_hit = self.round_by_find_area(
                    screen, '货币战争-备战', '告警-备战席已满',
                    crop_first=False).is_success
                _ov_id = ''
                if _ov_hit:
                    # ensure_portrait_templates 保持模块级导入:函数内重绑定
                    # 会遮蔽 _observe 前段的引用(ruff F823 实证)。
                    from sr_od.application.currency_war.kernel.cw_obs_core import (
                        _area_rect,
                    )
                    from sr_od.application.currency_war.obs.cw_identity_obs import (
                        identify_slots,
                    )
                    _ov_rect = _area_rect(self.ctx, '区域-溢出角色',
                                          '货币战争-备战')
                    _ov_tmpl = ensure_portrait_templates(self.ctx)
                    if _ov_rect is not None and _ov_tmpl is not None:
                        _ov_chars = identify_slots(screen, _ov_tmpl,
                                                   [(1, _ov_rect)], '')
                        if _ov_chars:
                            _ov_id = _ov_chars[0].char_id or ''
                _gs_obs.observe(_gs_obs.overflow_warning, _ov_hit,
                                sig=_prep_sig)
                _gs_obs.observe(_gs_obs.overflow_card, _ov_id,
                                sig=_prep_sig)
            # substate 消费:observe_full 的可读性
            # 标注落 PrepObservation(下游对账/日志可判)。
            obs.substate = _of.get('substate') or {}
            # ⚠ 以下 cap/双源审计用 heavy 段
            # 开头的旧 screen,而回执可能来自 gold 重读的 0.3-0.9s
            # 后异帧——跨帧对拍在轮转动画窗内可假分歧(低概率,
            # 留证非阻塞);重读仅在 shop 开态,窗口缩小。
            cap = read_deploy_cap(self.ctx, screen)
            _audit_level = _st.level if _st is not None else None
            # 观察冲突审计(2026-08-16 立,2026-08-23 再适配):财富宝钻官方
            # 效果「拥有即可使团队规模上限+1,无论是否被角色穿戴」可叠加
            # (局38 r2 实证 cap5/lv3=两宝钻)。布局与 cap 无关(level 驱动)
            # 后本检查只剩:
            # - cap < level → 不可能(读错/毒化)→ 留证;
            # - cap ≥ level → 合法(cap>level=宝钻叠加,debug 记宝钻数)。
            if cap is not None and _audit_level is not None \
                    and cap < _audit_level:
                from sr_od.application.currency_war.kernel.cw_observe import (
                    obs_conflict,
                )
                obs_conflict('deploy_cap_vs_level', _audit_level, cap, screen,
                             verdict=('留证-cap<level不可能(cap或level读错;'
                                      '处理:看截图读「区域-部署数」X/Y 原文核 X>Y guard '
                                      '是否该拒,level 查 XP 反推是否一致;'
                                      '确认 reader 缺陷则修 read_deploy_cap/level 守卫;'
                                      '单次按 OCR 噪声忽略,复现 ≥3 次才排期)'),
                             source='paddle_cap')
            elif cap is not None and _audit_level is not None:
                # cap>level(宝钻/钻石叠加)不只
                # 是经济信息——口述
                # 公式「后台格数 = 6+(cap−level)」使 cap 差直接驱动布局选档
                # (cw_back_layout.select_back_layout,含 7 格未建档留证)。
                # cap==level 是常态(无宝钻),别打
                # "宝钻×0"误导判读;仅真叠加(cap>level)才记
                if cap > _audit_level:
                    log.debug('[cw][obs] cap=%d(宝钻×%d 叠加,合法;后排扩展 +%d 格)',
                              cap, cap - _audit_level, cap - _audit_level)
            dep_n = read_deployed_count(self.ctx, screen)
            _cv_occ = len(obs.front_occupied) + len(obs.back_occupied)
            # (frame.deploy_vacancy 为 frame 属性现算,仲裁值仅在下方
            #  对拍注册面就地消费。)
            # deployed 总数双源对拍(同帧全齐):paddle X(读 deployed_count)
            # vs CV 占用(front+back)。
            # ⚠️ board 的 X 是「该阵营在场人数」非「角色数」——
            # 一个角色贡献多阵营(藿藿=仙舟+治疗,4 人可贡献 11 阵营次),
            # board_sum 系统性 ≥ 部署数,board 根本给不出角色数 →
            # **移出对拍**,对拍保持双源(paddle X vs CV 占用)。
            if dep_n is not None:
                # 对拍裁决迁仲裁注册面(15_observation_multisource_arbitration.md;
                # 注册键 deployed_count,
                # 计数类取低值+spread>1 告警带):divergent 判定经注册面,
                # 留证行/分键仍在此处按键发射——行数/field/新旧值/verdict
                # 文本逐字节不变(零行为验收对拍)。
                from sr_od.application.currency_war.obs.cw_arbitration import (
                    arbitrate,
                )
                _value, _verdict, _divergent = arbitrate(
                    'deployed_count',
                    {'paddle_x': dep_n, 'cv_occupied': _cv_occ})
                if _divergent:
                    from sr_od.application.currency_war.kernel.cw_observe import (
                        obs_conflict,
                    )
                    obs_conflict('deployed_count_2src',
                                 {'paddle_x': dep_n, 'cv_occupied': _cv_occ},
                                 'spread>1', screen,
                                 verdict=('留证-双源分歧(处理:看截图数前排+后排占用实数,'
                                          '与 paddle X 对拍;哪源对修哪源——paddle 对→CV '
                                          '阈值/遮挡误漏,CV 对→X/Y 拆框;'
                                          '消费侧板满门已按取低值仲裁'
                                          '(cw_observation.arbitrate_deployed_count);'
                                          '单次按噪声忽略,同局 ≥3 次排期修)'),
                                 source='director_heavy')
                    # 不一致率分键(防静默;裁决事件层,与上方证据层行分键)
                    try:
                        from sr_od.application.currency_war.telemetry.defects import (
                            record_deployed_count_2src_divergence,
                        )
                        record_deployed_count_2src_divergence(
                            dep_n, _cv_occ, 'director_heavy')
                    except Exception:   # noqa: BLE001  遥测 best-effort
                        pass
        return obs

    def reobserve_in_visit(self) -> PrepObservation:
        """访问内重观察(CwActionObs 动作执行通道;screens/op-layer.md §1.1 读屏点
        规范的在册例外):决策环内策略显式发射 CwActionObs 才触发的
        heavy 观察链重跑——漏斗直写容器 = 观察边界对账(「重新观察上报」)。

        辖域 = 最小重观察:入口专属段(环入口清场/开商店收起/接管补采/
        纯观察审计族)不在本通道,仍归观察 node;帧代次标注归决策循环
        写点(本方法零帧代次写);event_overlay 由调用方裁决(动作 op 抛
        CwObsOverlayBail 交回外循环重分发)。唯一调用方 = CwActionObsOp。
        """
        return self._observe(heavy=True)

    def _reconcile_tracking(self, bench: BenchView | None,
                            deployed, screen=None) -> tuple:
        """环入口对账(read≠tracking 漂移是既有 bug 源 → SIFT 真值重置 tracking)。

        统一走公共 ``cw_reconcile.reconcile_tracking``(空读守卫/漂移留证/
        obs_conflict JSONL 单一实现,star 用 read_star 实机金星)。载体 =
        P6 直产容器形状(备战席 BenchView / 上场位 (前排, 后排) Unit 行);
        失读 None → 空视图/空行承载(旧链 [] 语义:对账空读可清账,非
        「读失败不辖」)。

        Returns:
            ``(是否写回, 门后 bench 视图, 门后 deployed 行)`` —— 门后副本
            供同帧容器观察写端消费(星级保旧/装备续接随副本共享)。
        """
        session = self._session()
        if session is None:
            return False, bench, deployed
        from sr_od.application.currency_war.kernel.cw_reconcile import (
            reconcile_tracking,
        )
        return reconcile_tracking(
            session,
            bench if bench is not None else BenchView(),
            deployed if deployed is not None else ([], []),
            screen, source='director', ctx=self.ctx)

    def _reconcile_faction_display(self, obs: PrepObservation) -> None:
        """备战稳定帧羁绊显示对账(cw_faction_obs 接线;零决策:不一致仅落
        缺陷台账,不纠漂不重读——羁绊状态以计算侧为主源,显示只作对账票)。

        computed 侧 = ``board_from_tracked``(session tracked_deployed,全集
        主源;None=含未知身份算不出 → 宁缺勿造跳过);显示侧 = 左侧羁绊面板
        OCR(cw_faction_obs.read_displayed_factions,只读可视条目)。截断/
        OCR 失读/残名按 cw_faction_obs 口径不评不判错,仅计数随 refs 披露;
        ``computed_missing`` 形态(compare 第四态)同为留证不判错,
        report_faction_reconcile 只转发 mismatch 行。节奏 = heavy 定型帧
        消费,全程 best-effort。
        """
        try:
            session = self._session()
            if session is None:
                return
            computed = board_from_tracked(
                list(gs_of_ctx(getattr(self, 'ctx', None), session).tracked_books.deployed or []))
            if computed is None:
                return
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return
            reading = read_displayed_factions(self.ctx, frame)
            result = compare_factions(computed, reading.entries,
                                      reading.unreadable)
            # 台账行 plane/round = 容器读口。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                plane_of,
                round_num_of,
            )
            _gs = gs_of_ctx(getattr(self, 'ctx', None), session)
            plane = int(plane_of(_gs))
            round_num = int(round_num_of(_gs))
            if result.mismatch_count <= 0:
                # 不一致为零也留一条 debug(含不评口径计数),频率统计靠台账
                # 数据说话,不在此落账;行名并入见 faction_display_ok_debug_line
                log.debug(faction_display_ok_debug_line(
                    len(result.rows), len(result.ocr_skipped),
                    list(result.truncation_suspects),
                    sum(1 for r in result.rows
                        if r.verdict == "computed_missing")))
                return
            refs = [
                {'field': 'ocr_skipped', 'value': ','.join(result.ocr_skipped)},
                {'field': 'unmatched', 'value': ','.join(reading.unmatched)},
                {'field': 'truncated', 'value': str(reading.truncated)},
                {'field': 'truncation_suspects',
                 'value': ','.join(result.truncation_suspects)},
                {'field': 'computed_missing',
                 'value': ','.join(r.faction for r in result.rows
                                   if r.verdict == 'computed_missing')},
            ]
            n = report_faction_reconcile(
                result, plane=plane, round_num=round_num,
                gap_large=True,
                verdict=('留证-羁绊面板显示计数与计算侧不一致(计算侧= tracked '
                         '全集主源,显示只作对账票;零决策记账不纠漂。已知不评:'
                         '面板底部截断/OCR 失读/残名/computed_missing 均只计数'
                         '不判错;单次与复现同级 L1,复现计数见台账行)'),
                refs=refs,
                reader_source='faction_display_reconcile',
            )
            log.debug(f'[cw-director] faction_display reconcile: '
                      f'{result.mismatch_count} mismatch → {n} 行台账')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] faction_display reconcile skip: {e}')

    def _session(self) -> StrategySession | None:
        match = getattr(self.ctx, 'cw_match', None)
        return match.session if (match is not None and match.session is not None) else None

    def _match(self) -> CurrencyWarMatch | None:
        return getattr(self.ctx, 'cw_match', None)

    # ===== 备战单轮 op(拆内环;两 node 形态)=====
    # 外循环(cw_loop)是唯一循环:备战画面在 → 外循环每轮调本 op 一轮。
    # 观察 node = 数据观察 + 对账;决策动作 node = 单动作决策循环
    # (决策→执行→逻辑态直写,循环内零读屏;终结 op 交回外循环)。
    # 期望态由逻辑态直写承载逐动作推进;稳定性由外循环每轮重识别保证
    # (特效帧/overlay 弹出在轮间自然可见);无进展留证归外循环 stall
    # 防线(cw_loop 备战分支)。

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """环装配前置 + 数据观察 + 对账(纯观察审计族留守本 node)。

        序列:执行器构建 + 缓存复位 → 环入口清场(ENTRY_OVERLAY_CLOSE =
        过渡相位表「可一键关闭」子集)→ 开商店收起探针 → heavy 观察 →
        CwScreenPrepObs 装配(可选域经 :func:`report_screen_prep_obs` 在
        原写点位落容器:链域在 heavy 观察链内、接管域在补采簇内,字段在
        场才写)→ 帧代次标注 → 事件 overlay 交回早退 → 接管补采 →
        审计族消费。书册卡不再入口代清:识别 kind 进容器,开卡时机由
        策略器 entry ① 卡片臂裁决(用户裁定 2026-09-19,发射的
        CwActionOpenBookcardParam 为终结动作,交回语义与原入口代发一致)。"""
        match = self._match()
        if match is None or match.strategy is None:
            return self.round_fail(status='无 cw_match(对局未初始化)')
        session = match.session
        self._executor = PrepActionExecutor(self, self.ctx)

        # —— 数据观察:清场 + 开商店合法态收起(读互斥:hp 关态可读)→ heavy 全量观察写 session
        self._clear_entry_overlays()
        self._try_collapse_open_shop()
        obs = self._observe(heavy=True)
        # 帧代次标注:入口 heavy 主观察帧 = full;消费归
        # 决策入口(含经 overlay 防线反弹的 pick 子路径)。
        game_state_of(session).frame_class_prep = 'full'
        if obs.event_overlay is not None:
            # overlay 在场 → 交回外循环重识别分发(无计数;对应 loop 0x 分支/op 接管)
            log.info(f'[cw][director] 事件 overlay({obs.event_overlay})→ 交回外循环分发')
            return self.round_success(f'事件overlay({obs.event_overlay})交回外循环分发', wait=0.8)
        # 接管局补采委派(挂点随观察段平移;编排单一源 =
        # CwEntryPlaneIntel,本 op 只判触发与透传,详见方法注释)
        _tk = self._delegate_plane_intel_if_needed(session)
        if _tk is not None:
            return _tk
        # —— 对账段:本轮入口 heavy 观察 = 纯观察审计族消费点
        #      (羁绊显示;零决策)。
        #      「入口观察即对账」时点存续,per-action
        #      heavy 重读契约已灭。动作上报的对账归一 = 逻辑态直写
        #      (op 自上报)+ 观察边界 cw_reconcile 兜底;
        #      错卖类不可逆损害窗口的收窄手段 = 执行侧
        #      tracked 账随动,同商店线双账口径。
        #      审计链留守观察 node(观察处理,不进 report——依赖读帧的
        #      识别域载荷不迁 kernel)。
        self._v2_post_frame_accounting(obs, session)
        #      模态恢复路径由三既有防线承接:①部署放行判定(前置谓词:
        #      bench_free>0 才发席耗动作,模态源头收敛);②环入口清场
        #      (_clear_entry_overlays,残留模态一键关);③外循环无进展
        #      守卫(动作批签名计数)。派生席满判定单一源 =
        #      kernel.cw_game_state.bench_is_full(决策/拦截消费面);
        #      破墙主动探测不复活——派生席满≠模态在场(持 9 席是合法
        #      运营态,按席满主动腾席会打穿策略持仓);hp 消费统一经
        #      decision_hp 门前真值+施门。
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作')
    def act(self) -> OperationRoundResult:
        """单动作决策循环整体(前身份 = 序列消费 +
        每动作落地后 heavy 重观察的保守口径)。

        形态:入口 heavy 一次观察 → 逐动作『决策(容器=逻辑态)→ F3
        校验 → 执行 → 逻辑态直写』循环,循环内零读屏(在册例外 =
        CwActionObs 环内重观察:策略显式发射才触发宿主观察链重跑,
        帧代次标 full 后原地续决策)。已知画面出口
        (CwActionOpenShopParam/CwActionStartBattleParam/CwActionOpenBoxParam)= 终结 op,执行即本访问结束
        交回外循环(下次入口重观察);CwActionObs 执行见事件 overlay =
        CwObsOverlayBail 交回外循环重分发(路由归外循环)。
        验证段+恢复原语分支退役(用户裁定 2026-09-10):
        动作机械执行(无成败回执),无进展治理归外循环 stall
        防线,落地判定归观察侧 reconcile。决策循环无防御上限
        (用户裁定:不收敛 = 策略实现 bug)。
        """
        match = self._match()
        session = match.session
        # 段序号置位(备战期开始;唯一置位点 = 本 prep 访问循环入口):
        # 访问 = 腾席拒绝结论的输入不变性段,入口 +1 使上一访问/上一域
        #(商店 visit/破墙段)残留的续段 token/结论闩按序号不等自动失效。
        # 状态对象缺席(第三方策略面/桩)= 无缓存载体,跳过置位(决策核
        # 侧冷建自 0 起,行为 = 恒重推导,保守端安全;缺席退缺省口径)。
        _st_seg = strategy_state_of(session)
        if _st_seg is not None:
            _st_seg.cw4_segment_serial += 1
        while True:
            # —— 决策(容器 game state 直读;动作后逻辑态 =
            #      kernel 写口统一直写)
            try:
                result = match.strategy.decide_prep_screen()
            except Exception as e:  # noqa: BLE001  策略异常 = 本轮 fail(外循环 retry 链兜)
                log.warning(f'[cw!][director] decide_prep_screen 异常: {e}')
                return self.round_fail(status=f'策略决策异常: {e}')
            if not isinstance(result, CwAction):
                log.warning(f'[cw!][director] 策略输出非 CwAction: '
                            f'{type(result).__name__}')
                return self.round_fail(status='策略输出非 CwAction(F3)')
            if isinstance(result, CwActionObsParam) \
                    and result.scope == 'outer_loop':
                # 交回外循环重新观察(空发射帧显式信号;原 HoldFrame 收编
                # 进 obs scope 口径,用户裁定 2026-09-20):拦截型——不进
                # validate/执行器/动作注册表/续段 token/动作记录,round
                # 返回形态与等待时长与原 HoldFrame 分支逐字一致。系统级
                # stall_watch/NODE-DWELL 哨兵对其透明;系统并无「连续空
                # 发射计数器」,stall 防线哨兵只对无进展留证。
                return self.round_success('本帧无动作(Obs:outer_loop),交回外循环重观察', wait=1.0)
            action = result
            # F3 校验:参数非法交回留证;执行前输入契约检查,非动作后判效
            err = self._executor.validate(action)
            key = action_key(action)
            if err is not None:
                log.warning(f'[cw!][director] 参数非法 {key}: {err} → 拒绝,交回外循环留证')
                return self.round_success(f'参数非法 {key}:{err},交回外循环留证', wait=1.0)
            # —— 执行(机械执行,无成败回执;发出即职责完成)
            #      执行体 = _act_execute_default(现役点击链 / 流程编排分流)。
            try:
                self._act_execute_default(action)
            except StopBrakeShortCircuit as e:
                # 刹车短路:停机标志已设,动作未发出 →
                # 交回外循环,下轮 loop 顶见 STOP 退出(原回执 False 通道
                # 已退役改停机短路异常)。
                log.info(f'[cw][director] 停机刹车({e}),动作未发出 → 交回外循环')
                return self.round_success(f'停机刹车({e}),动作未发出,交回外循环', wait=1.0)
            except CwObsOverlayBail as e:
                # 环内重观察发现事件 overlay(CwActionObs 执行回执):
                # 画面识别与路由归外循环,环内不消化 → 交回重分发
                # (观察 node 同语义早退;无计数;帧代次不写——交回后
                # 下次入口观察重标)。
                log.info(f'[cw][director] {e} → 交回外循环重分发')
                return self.round_success(f'{e},交回外循环重分发', wait=0.8)
            except Exception as e:  # noqa: BLE001  执行异常上抛 = 本轮 fail
                log.warning(f'[cw!][director] 执行异常 {key}: {e}')
                return self.round_fail(status=f'执行异常 {key}: {e}')
            # 续段 token 写入(生产 prep 循环执行位;CwActionOpenShopParam 分支与
            # 执行器分支在此合流):发出即写。状态对象缺席 = 无缓存载体,跳过
            # (缺席退缺省口径)。
            _st_tok = strategy_state_of(session)
            if _st_tok is not None:
                _st_tok.cw4_frame_action_record = (
                    type(action).__name__, _st_tok.cw4_segment_serial)
            # —— 结束判定 → 交回外循环(动画等待已由执行器/编排内建)
            #      终结集与等待时长改读注册表 op 类
            #      terminal/terminal_wait 类属性(消费点经注册表读类属性,
            #      禁消费点私表)。
            _op_cls = action_op_class_for(action)
            if _op_cls.terminal:
                return self._terminal_exit(action, key, _op_cls)
            # —— 动作逻辑态由动作 op 自上报独占直写,本环不再直写
            #      (op 已写,本处再写即双记)。假账风险由下一入口
            #      heavy reconcile 以实读纠逻辑态承担(观察赢)。
            # 直写帧代次:同 visit 内续动作直写 = none,
            # 不重复触发方向刷新;CwActionObs = 访问内重观察(新观察写点)
            # = full(方向重估触发,同入口帧;贵段消费侧键守卫限频每
            # game-round 恰一次,环内多次重观察不放大方向刷新成本)。
            game_state_of(session).frame_class_prep = (
                'full' if isinstance(action, CwActionObsParam) else 'none')

    # ===== 已锁语义的现役载体位置:bench 空集守卫/合成特效窗门在
    # _observe 识别链内,免费闸/免战牌在执行器内,同节点去重在
    # cw_loop 备战分支挂点 =====

    def _terminal_exit(self, action: CwAction, key: str,
                       op_cls: type[SrOperation]) -> OperationRoundResult:
        """终结动作交回:终结判定与等待时长改读
        注册表 op 类 ``terminal``/
        ``terminal_wait`` 类属性(消费点经注册表读类属性,禁消费点私表)。
        交回 detail 文案逐动作保持原样(零行为)。

        调用契约 = 仅 ``op_cls.terminal`` 为真时进入;非终结动作到达 =
        终结集与消费面失配,响亮暴露。
        """
        if op_cls is CwActionStartBattleOp:
            # 出战提前终结(发出即终结——点击序列完成即交回外循环
            # 战斗分支;点击序列事实经执行器 last_launch_ok 旁路供 cw_loop
            # 发射核)。
            return self.round_success('出战(交回外循环战斗分支)',
                                      wait=op_cls.terminal_wait)
        if op_cls is CwActionOpenShopOp:
            # 显式开店路径在本执行体内完成完整商店访问(开→买波→收店)
            # 后已回备战帧;仅买波失败路径店开态交回外循环重识别;
            # 受限仲裁路径执行完仍在备战帧。
            return self.round_success(f'{key} ✓,交回外循环重识别',
                                      wait=op_cls.terminal_wait)
        if op_cls is CwActionOpenBoxOp:
            # CwActionOpenBoxParam 终结化:开箱即引入新事实(武装箱选择画面
            # 出现,与刷新终结结构语义同构)→ 本访问交回,外循环按
            # 武装箱选择画面分发新画面 op 选卡。交回等待 =
            # CwActionOpenBoxOp.terminal_wait(与 ``_open_box`` 动画等待
            # ``_OVERLAY_ANIM_WAIT_S`` 等价,等价测试锁 = test_cw_unified_action_3)。
            return self.round_success(f'{key} ✓(交回:武装箱选择画面分发)',
                                      wait=op_cls.terminal_wait)
        if op_cls is CwActionOpenBookcardOp:
            # 开卡终结(用户裁定 2026-09-19 发射位迁策略器 entry ① 卡片臂,
            # 原画面 op 入口清场代交回通道撤销):弹专家邀请函 = 新事实 →
            # 本访问交回,外循环 0k 分发 CwScreenExpertInvite 选卡。
            return self.round_success(f'{key} ✓(交回:专家邀请函弹窗分发)',
                                      wait=op_cls.terminal_wait)
        raise AssertionError(
            f'[cw][director] 非终结动作进入终结出口:{type(action).__name__}'
            '(终结集与消费面失配,响亮暴露)')

    def _act_execute_default(self, action: CwAction) -> None:
        """现役点击链缺省执行体(决策循环执行位)。CwActionOpenShopParam = 流程层商店编排
        [spend 单元记账 + _open_shop_phase];其余 = 执行器机械执行。
        机械摘要仅落各分支的执行日志(log.info 行)。"""
        if isinstance(action, CwActionStartBattleParam):
            # 出战意图执行 = 统一执行器(face=armed:屏态复验→浮层安全检查
            # →部署原子序→出战点击链——策略前置
            # 发射位的意图在此落执行)。
            from sr_od.application.currency_war.operations.cw_loop import (
                launch_battle_unified,
            )
            _, _detail_lbu = launch_battle_unified(self, self.ctx,
                                                   face='armed')
            log.info(f'[cw][director] {action_key(action)} → {_detail_lbu}')
            return
        if isinstance(action, CwActionOpenShopParam):
            if getattr(action, 'restricted_spend', False):
                # 受限访问(发射帧仲裁意图执行;金出口族出口 B):仲裁单元
                # 自含预检/域判/预算闸/第三载体行,语义单一源 = cw_loop
                # _launch_frame_arbitration(意图化仅换宿主,函数原样复用)。
                from sr_od.application.currency_war.operations.cw_loop import (
                    _launch_frame_arbitration,
                )
                _arb = _launch_frame_arbitration(self)
                _detail = (
                    f"仲裁访问(zone={_arb.get('zone')} "
                    f"executed={_arb.get('executed')} "
                    f"gate_blocks={_arb.get('gate_blocks')})")
                log.info(f'[cw][director] {action_key(action)} → '
                         f'{_detail}')
                return
            _, detail = self._open_shop_phase()
            log.info(f'[cw][director] {action_key(action)} → {detail}')
            return
        self._executor.execute(action)
        _detail = getattr(self._executor, 'last_detail', '')
        log.info(f'[cw][director] {action_key(action)} → {_detail}')

    def _delegate_plane_intel_if_needed(self, session: StrategySession
                                        ) -> OperationRoundResult | None:
        """接管补采委派(挂点 = op 观察 node;编排单一源 =
        CwEntryPlaneIntel:门/开关详情屏/委派实采/真值落容器写门全在编排侧)。

        触发谓词 = gs.plane_bosses 空(本局尚无位面序真值;不引入显式
        失效标记——重复委派由编排的真值跳过门兜住,委派失败交外循环
        失败链,无自带计数/放弃分支)。「节点条可读」守卫 = 半开帧
        (过场/overlay)不委派、等下轮免费重判、不烧失败链。
        委派结果透传:成功 = round_success 交回外循环重识别;失败 =
        round_fail 走外循环既有失败链(重试/熔断),不自旋。
        """
        _gs = gs_of_ctx(getattr(self, 'ctx', None), session)
        if _gs.plane_bosses.value:
            return None
        _tk_slots = None
        with contextlib.suppress(Exception):
            _tk_slots = read_node_sequence(self.ctx, self.last_screenshot)
        if _tk_slots is None:
            return None   # 节点条不可读(半开帧)→ 等下轮免费重判
        from sr_od.application.currency_war.operations.cw_entry.cw_entry_plane_intel import (
            CwEntryPlaneIntel,
        )
        log.info('[cw][director] 新局 boss/词缀无实采真值 → 委派 CwEntryPlaneIntel'
                 '(接管编排)')
        return self.round_by_op_result(
            CwEntryPlaneIntel(self.ctx).execute(),
            status='接管补采委派,交回外循环重识别')

    def _clear_entry_overlays(self) -> None:
        """环入口清场前置段(规范入口序列「先清场、再识别、后动作」):
        环入口先逐屏探可一键关闭的 overlay(注册表 = ``ENTRY_OVERLAY_CLOSE``,
        单一源 = ``cw_overlay_registry.derive_clearable()`` 派生桥接;
        锚判定走现有 screen 体系),命中即点其关闭按钮,拿干净备战画面再进
        全量识别——识别与 overlay 状态交织是死读与冲突噪声的共同根。只收
        「无决策语义的弹窗/面板」;投资环境/策略等交互 overlay 有专属
        handler,关闭即丢决策内容,不进注册表、仍走既有 event_overlay
        bail → 外环消化路径。
        fail-open:截图/识别/点击任一异常静默返回(=现行为,外循环重判兜底)。"""
        from one_dragon.base.screen import screen_utils
        for _ in range(ENTRY_OVERLAY_CLEAR_ROUNDS):
            try:
                frame = self.screenshot()
            except Exception:   # noqa: BLE001  离线契约
                return
            _hit = None
            for _name in ENTRY_OVERLAY_CLOSE:
                try:
                    if screen_utils.get_match_screen_name(
                            ctx=self.ctx, screen=frame,
                            screen_name_list=[_name],
                            crop_first=False) is not None:
                        _hit = _name
                        break
                except Exception:   # noqa: BLE001  离线契约
                    return
            if _hit is None:
                return
            _area = ENTRY_OVERLAY_CLOSE[_hit]
            log.info(f'[cw][director] P0 清场:{_hit} 在场 → 点 {_area}')
            try:
                self.round_by_find_and_click_area(
                    frame, _hit, _area, success_wait=0.5)
            except Exception:   # noqa: BLE001  离线契约
                return
            time.sleep(ENTRY_OVERLAY_SETTLE_S)

    def _try_collapse_open_shop(self) -> bool:
        """环入口遇开商店稳定态(战斗胜利后新回合游戏可能自动开)→
        收起返回 True;非开态(真特效/overlay)返回 False。

        防线定位(0n 分支落地后):主防线已前移至外循环 0n 分支
        (cw_loop `_shop_open_anchors_hit` 路由,商店态禁部署/出战调度);
        本守卫降级为纵深防御二层——0n 分支漏收帧(如「备战阶段」OCR
        抖动)或入口绕过路由时兜底,语义不变。

        唯一调用方 = 观察 node 环入口,开商店收起探针仅此一探(自动开
        商店晚于本探的帧交外循环 0n 路由兜住,入口不做有限窗重试)。

        HP/gold 读取语义要求关态。
        离线契约:探测/点击异常 → False(放行,不让离线 mock 测试炸掉)。
        """
        try:
            _sc = self.screenshot()
            if not self.round_by_find_area(
                    _sc, SHOP_SCREEN_NAME, '按钮-收起',
                    crop_first=False).is_success:
                return False
            log.info('[cw][director] 环入口开商店态(合法态非特效)→ 收起')
            self.round_by_find_and_click_area(
                _sc, SHOP_SCREEN_NAME, '按钮-收起', success_wait=1.0)
            return True
        except Exception:   # noqa: BLE001  离线契约
            return False

    # ===== 流程层商店编排(整段买牌解体的承接)=====

    def _open_shop_phase(self) -> tuple[bool, str]:
        """CwActionOpenShopParam 动作的流程层编排。

        显式开店:open_shop(幂等,已开不点)→ visit_open_shop(商店访问
        编排单一源:入口观察 → 商店单动作循环 → 关店收编进商店画面 op
        → 节点探针)。受限访问(restricted_spend)在 _act_execute_default
        截流,不经本方法。波循环失败路径不开收(店留着交上层/外环重新识别)。
        """
        from sr_od.application.currency_war.operations.cw_op.cw_op_open_shop import (
            open_shop,
        )
        match = self._match()
        if match is None:
            return False, '无 cw_match(对局未初始化)'
        # 验证废除(用户裁定 2026-09-10:调用方不问成败):
        # open_shop 的验关型失败回执消费删除——发出即职责完成,店实际开没开
        # 由下一帧观察侧对账自然闭环(0n 三锚/备战帧读互斥)。
        _ = open_shop(self)
        return self.visit_open_shop()

    # ===== [临时段·特殊投资策略商店停机钩子](od-dev-stop-hooks §2.1
    # 临时捕获类;用户 2026-09-10 指令:候逐条确定的特殊投资策略在场时,
    # 进入商店画面处理即停机。2026-09-16 裁定:直接停机人工采集,不再
    # 代码落截图/转储/flag。删除面 = 本整段(名单常量+防重集合+方法)
    # + visit_open_shop 首部挂点两行,不留开关/flag/配置)=====

    #: 候逐条确定的特殊投资策略名单(硬编码,不建配置;名字 = 注册表规范名,
    #: 同 cw_investments.STRATEGY_EFFECTS 键空间。名单可先于注册表建模面——
    #: 未建模的名字进不了效果清单,在册匹配是唯一判定,前瞻占位无害)。
    _SPEC_INVEST_WATCH_NAMES: ClassVar[frozenset[str]] = frozenset({
        '采购专员·金', '采购专员·彩', '双手狸开键盘！', '商业间谍', '躺平',
        '长期主义', '长期主义+', '超发货币', '成长基金', '伟大征服', '降本增效',
        '概率事件', '远见', '市场干预', '固定理财+', '返利', '返利+',
        '经验就是财富',
    })
    #: 防重停集合(进程内存):键 = 当次在场∩名单的规范名 frozenset——同组合
    #: 只停一次,组合变化(新名单效果入场)视为新组合再停;重启清零 = 允许重停。
    _SPEC_INVEST_CAPTURED: ClassVar[set[frozenset[str]]] = set()

    def _spec_invest_shop_stop_hook(self) -> str | None:
        """特殊投资策略商店停机钩子(临时捕获;触发 = 效果清单含名单效果)。

        2026-09-16 用户裁定:直接停机,采集改手动——不代码落盘。
        停机后画面原样保持(店开着):人工看画面 / MCP 截图补帧,对照
        效果注册表逐条确定该组合下商店改写/计数/经验行为,结论回填效果
        规格 verdict/notes;采够后删本整段(含 visit_open_shop 挂点两行),
        不留开关。框架截图([stop] 行)即现场帧。
        """
        match = self._match()
        session = match.session if match is not None else None
        if session is None:
            return None
        gs = gs_of_ctx(getattr(self, 'ctx', None), session)
        hit = sorted({e.spec.name for e in gs.effects.entries
                      if e.spec.name in self._SPEC_INVEST_WATCH_NAMES})
        if not hit:
            return None
        combo = frozenset(hit)
        if combo in self._SPEC_INVEST_CAPTURED:
            return None
        self._SPEC_INVEST_CAPTURED.add(combo)   # 先占位:同组合恰停一次
        log.warning('[cw!][spec-invest-hook] 特殊投资策略 %s 在场 → 停机,'
                    '人工采集(画面原样保持,处理流程见本段注释)', hit)
        rc = getattr(self.ctx, 'run_context', None)
        if rc is not None:
            rc.stop_running(reason='hook:spec_invest_shop',
                            save_screenshot=True)
        return f'特殊投资策略停机:{",".join(hit)}(人工采集)'

    # ===== [临时段结束] =====

    def visit_open_shop(self) -> tuple[bool, str]:
        """店已开态的商店访问编排(外循环 0n 分支入口)。

        语义 = 「从店已开状态进入」(单动作循环的入口形态):
        入口观察现读当前牌面重建期望态 → 策略器逐动作决策(买/卖/升/刷)
        → CwActionCloseShopParam 终结收店交回(收店点击由商店画面 op
        执行体承担)。**不调 open_shop**——店已开由外循环
        0n 三 id_mark 锚判定确认,直接跳过开店动作(比依赖 open_shop
        幂等性更进一步:已开连点都不发);「收不收」由策略器基于期望态
        决定(CwActionCloseShopParam = 商店画面 op 的一等终结动作),路由层不硬编码收起。

        (访问内 hp 决策消费统一经 decision_hp 容器读口,显式开店路径与
        0n 路径同源。)

        编排单一源归属:本方法 = 商店访问尾段(商店画面 op run → 节点
        探针)的唯一编排点,显式开店路径与 0n 转交路径共用。节点探针
        挂点 = 商店画面 op 完成后(店确定关的可靠时点;实现住商店域
        ``cw_screen_buy_cards.probe_node_type``,本方法只持调用位)。
        失败路径不开收(店留着交上层重新识别,同 _open_shop_phase)。
        """
        # [临时钩子挂点] 特殊投资策略商店采集停机(采够删:整段 = 上方
        # _spec_invest_shop_stop_hook 临时段 + 本两行);触发即已停机留证,
        # 返回失败回执不进买牌循环——零 click,画面原样保持待 AI 接管。
        if (_spec_stop := self._spec_invest_shop_stop_hook()) is not None:
            return False, _spec_stop
        match = self._match()
        if match is None:
            return False, '无 cw_match(对局未初始化)'
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_buy_cards import (
            probe_node_type,
            run_buy_waves,
        )
        _rr, ledger = run_buy_waves(self, match)
        if _rr is not None or ledger is None:
            return (False, f'买牌循环未完成'
                    f'({_rr.status if _rr is not None else "无产出"})')
        probe_node_type(self)
        return True, '买牌访问完成'

    def _v2_post_frame_accounting(self, obs: PrepObservation,
                                  session: StrategySession) -> None:
        """新环 heavy 定型帧上的纯观察审计族(零决策)。

        输入 = 本帧 obs;每通道内部 best-effort,异常不阻塞环。覆盖:
        羁绊显示。动作期望账通道(paddle 审计/
        drag_expect/买牌期望/经验/装备期望)不属本口——动作上报的对账
        归一 = 逻辑态直写(op 自上报)+ 观察边界
        cw_reconcile 兜底。
        """
        with contextlib.suppress(Exception):
            self._reconcile_faction_display(obs)


def _write_prep_node_chain(session: object, slots: list | None,
                           sig: ChannelSig) -> None:
    """备战帧现行链写端(语义正本 =
    game_state/chain-observation.md §3,quality=prep_row)。

    挂点 = 备战入口 heavy 观察的节点行读(director 侧写容器,组装层
    单写者原则只回传 slots)。写端 = :func:`report_screen_prep_obs`
    ``node_path_chain`` 域(kernel 屏文件:node_path 双写 + 基线幂等回填,
    evidence='prep_row'/'prep_row_first' 原值);其后的台账变异窗关闭与
    链 diff 触发留本侧——台账经 ``get_node_ledger(session)`` 访问
    (session 通道,kernel 屏文件只有 gs 无 session)。

    变异窗语义:对齐 clean 读成功即关 env_grace_until(投资环境原短窗
    重读职责由本读承接);diff 触发(窗内豁免清候选,窗关后
    按两帧确认补比对)。纯观测写点:异常不阻塞观察链。
    """
    _chain = build_prep_node_chain(session, slots)
    if _chain is None:
        return
    try:
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            get_node_ledger,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            maybe_emit_chain_diff,
        )
        gs = game_state_of(session)
        report_screen_prep_obs(gs, CwScreenPrepObs(node_path_chain=_chain),
                               sig=sig)
        ledger = get_node_ledger(session)
        was_open = (ledger is not None
                    and ledger.env_grace_until > time.monotonic())
        if ledger is not None:
            ledger.env_grace_until = 0.0
        # 链 diff 触发(窗内豁免清候选,窗关后按两帧确认补比对)
        maybe_emit_chain_diff(gs, snapshot=False,
                              in_mutation_window=was_open, sig=sig)
    except Exception:   # noqa: BLE001  观测写点 best-effort,不阻塞观察链
        pass

