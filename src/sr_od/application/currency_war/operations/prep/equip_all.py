
"""货币战争 全员装备 op:read_equips 多列 owned → 过滤工具 → drag 穿戴类 → 前排角色头像 → count 验穿。

**机制(D-36~D-40)**:drag **穿戴类**装备(排除工具)→ 前排角色头像 (743,350) = 穿(D-36 轮滑鞋验)。
装备 owned = **多列规则网格**(col1 x1800-1918 + col2 x1660-1800 + ...,D-40),**无空槽**(「+」=星徽 icon D-38)。
read_equips(thr7)名准+无假阳(D-39,4/4 click 验),覆盖多列(区域 = screen_info「区域-道具装备」x1620-1918,D-40)。

**avatar-slot CV-diff 验穿(R19治本③,已替 count-verify)**:drag 前后对比目标 avatar 下方 mini icon 区
(CV diff > 阈值 = 穿[新装或合成都变 icon],不变 = drag 落空)。**robust 合成消耗2件/列reflow/read漏检**
(count-verify D-41 实测报3实4 失真:合成消耗2件 → column count 扰;avatar below-icon 变化直接观测,免受其扰)。

**已接 cycle**(BattlePrepCycle ③,live A8 实跑):装备量受 bug#1 drag 间歇落空影响 → drag 前 mouse_move + 落空 retry(2026-08-11 live 诊断加)。

**前置**:已在「货币战争-备战」,角色详情面板关(出售 不可见 —— 角色详情面板遮 col2;装备详情面板不遮 icon D-37)。
"""
import time
from typing import ClassVar

import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_comps import (
    equip_alloc_empty_reason,
    equip_allocation,
)
from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
from sr_od.application.currency_war.obs.currency_war_char_id import (
    load_avatar_templates,
)
from sr_od.application.currency_war.obs.cw_equipment import (
    EQUIPMENTS,
    load_equip_templates,
    load_equip_tm_grays,
    read_equips,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    _ctx_slots,
    read_deployed_chars,
    read_row_equipped,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# 工具类装备(拆装扳手/冶金炉/随便骰子等,非 drag 穿;D-34 单独处理)
_TOOL_CATEGORIES: set[str] = {'工具'}


def _owned_wearable_names(hits: list) -> list[str]:
    """read_equips 命中 → 穿戴类 owned 名单(工具类过滤;ADR-0358 搬运链写端)。

    与主流程 ``wearable`` 同过滤口径(非工具类即穿戴候选);W92 修法 A:owned
    持有面原先有读点、无写链,决策/遥测全盲(3,061 条 decisions 里 state.equips
    0 条非空)——本函数供 ``equip_all`` 写 ``session.last_owned_equips``。
    """
    return [n for n, _, _ in hits
            if EQUIPMENTS.get(n) is not None
            and EQUIPMENTS[n].category not in _TOOL_CATEGORIES]


def _below_icon_diff(
    screen_pre: MatLike, screen_post: MatLike, avatar_x: int,
    below_y: int = 479, bx_half: int = 35, by_half: int = 30,
) -> float:
    """drag 前后目标 avatar 下方 mini icon 区的像素差均值(>阈值=穿了;R19 CV-diff 验穿)。

    纯函数(可离线 fixture 测):crop below-icon 区 → 两帧像素绝对差均值。``EquipAll`` 用它判 drag
    是否落地穿(robust 合成消耗2件/列reflow/read漏检,替 count-verify D-41)。默认 below_y/bx_half/by_half
    对齐 ``EquipAll`` 类常量(D-41 测 below-icon y=479),测试可直接调。

    实测验证(D-56,飞霄 0→1→2→3 件 fixture):连续态(加 icon)diff 28-41(>>阈值 8.0),同态 0.0。
    """
    pre = screen_pre[below_y - by_half:below_y + by_half, avatar_x - bx_half:avatar_x + bx_half]
    post = screen_post[below_y - by_half:below_y + by_half, avatar_x - bx_half:avatar_x + bx_half]
    return float(np.abs(pre.astype(np.int16) - post.astype(np.int16)).mean())


def _empty_slots(occupied: dict[int, list[str]], count: int) -> list[int]:
    """已穿槽位 dict → 空槽位序号列表(1-based;P0-2 drag 前占位检测)。

    ``occupied`` = ``read_row_equipped`` 结果(``{slot_idx: [装备名]}``,slot_idx 1-based);槽不在 dict = 空。
    纯函数(可离线测):只往空槽 drag,避免覆盖已穿装备(原 bug:``target = FRONT_AVATARS[equipped]``
    按已穿计数索引 → 已穿槽被覆盖)。
    """
    return [i for i in range(1, count + 1) if i not in occupied]


def _prioritize_wearable(
    wearable: list[tuple[str, tuple[int, int]]],
    key_equips: list[str] | None,
) -> list[tuple[str, tuple[int, int]]]:
    """穿戴候选按 target_comp.key_equips 优先排序(命脉件在前,其余原序)。

    comp 驱动穿戴(替 naive ``wearable[0]``):EquipAll 优先穿 target comp 的关键装备
    (如反甲流需 3 以牙还牙甲 / 阿雅需 2 反重力皮靴),而非 read_equips 返回的第一个。无 target /
    无 key_equips → 原序(等价旧行为)。``key_equips`` 可含重复 → 按 multiplicity 消费(命中的重复件也优先,
    但不超额)。与 ``equip_fit`` 同源(``comp.key_equips`` 出发,不设通用 equip_score;决策见 ADR-0101)。
    """
    if not key_equips:
        return wearable
    remaining = list(key_equips)
    prioritized: list[tuple[str, tuple[int, int]]] = []
    rest: list[tuple[str, tuple[int, int]]] = []
    for name, pos in wearable:
        if name in remaining:
            prioritized.append((name, pos))
            remaining.remove(name)   # 消费一个 multiplicity(重复件不超额优先)
        else:
            rest.append((name, pos))
    return prioritized + rest


def _transition_hold_active(tgt_comp, form: float, dual: bool, opening_round: bool) -> bool:
    """过渡期装备 hold 总门(r70 × r388 × 对抗审查 R3 修正)。

    - r388:开局轮(P1 r≤2)hold **无条件生效**——key_equips 白名单来自
      target,target 真空(重启后首局,skill 明载 target 重选断档)时白名单
      为空;旧判 ``tgt_comp is not None`` 会让 r388/r70 两条 hold 全不
      生效,r388 所修的「开局乱穿」恰在这最高频窗口残留(ADR-0257)。
    - r70:已定型(target 在)且 0<form<COMMIT_FRAC 且非双轨 → hold。
    - W607 起 ``opening_round`` 实参由 :func:`_opening_hold_active` 产出
      (H3 收窄+H2② 生锈豁免在调用侧组合,本函数语义不变)。
    """
    if opening_round:
        return True
    from sr_od.application.currency_war.kernel.cw_comps import COMMIT_FRAC
    return tgt_comp is not None and 0.0 < form < COMMIT_FRAC and not dual


def _opening_hold_active(round_num: int | None, node_type: str | None,
                         battle_gate: bool, battle_nodes: frozenset[str]) -> bool:
    """W607 H3:opening hold 收窄(ADR-0461)。

    r388/ADR-0257 的 hold 辖域=P1 r≤2,by-design 前提=开局轮是奖励轮
    无战斗——局22 r2 StartBattle 实证前提只对 r1 成立(r2 起是白板挨打,
    W593 闸门①)。收窄后:hold 仅当 r≤2 **且当前节点非战斗类**;战斗类
    名单=registry.opening_hold_battle_nodes(词汇表=GameState.node_type
    顶部标签 OCR)。降级路径(有锁):``round_num`` 缺失(P1 之外/读不到)
    → False(同旧「非开局轮」);``node_type`` 缺失(OCR/台账都空)→
    **维持现状 hold**(观察缺失不改变既有行为,宁缺勿错);开关关
    (battle_gate=False)→ 逐位旧行为(零漂移锚)。
    """
    if round_num is None or round_num > 2:
        return False
    if not battle_gate:
        return True
    if node_type is None:
        return True
    return node_type not in battle_nodes


def _rust_release_active(enemy_affixes: list[str] | None, gate: bool) -> bool:
    """W607 H2②:库藏生锈在场时豁免装备 hold(ADR-0461)。

    备战席每 1 件未穿装备 → 敌方造成伤害 +3%、受到伤害 -4%,最多 10 件
    (competitors.md:45,游戏内实采)——滞留的边际代价随件数单调上升,
    「攒给成型核心」的机会成本被压制。纯谓词;消费点=EquipAll hold 过滤
    分支(开关=registry.rust_wear_release_enabled,默认关=零漂移)。
    """
    if not gate:
        return False
    return '库藏生锈' in set(enemy_affixes or [])


class EquipAll(SrOperation):
    """备战:read_equips 多列 owned → 过滤工具 → drag 穿戴类 → 前排**空**角色头像(P0-2 占位检测)→ avatar-slot CV-diff 验穿。

    装备库区域 = screen_info「区域-道具装备」(多列 x1620-1918,D-40;坐标维护 yml 非硬编码)。
    **P0-2 drag 前占位检测**:``read_row_equipped`` 读前排 avatar 已穿 → 只往空槽 drag(``_empty_slots``,
    修原 ``target=FRONT_AVATARS[equipped]`` 按已穿计数索引 → 已穿槽被覆盖)。
    avatar-slot 验穿(R19治本③,替 count-verify):drag 前后对比目标 avatar 下方 mini icon 区 CV-diff,
    变了=穿(新装/合成都变),不变=落空。robust 合成消耗2件/列reflow/read漏检(D-41 count-verify 报3实4 失真)。
    前置:已在「货币战争-备战」(角色详情面板关 —— 装备详情面板不遮 icon D-37)。**已接 cycle**(BattlePrepCycle ③);装备量受 bug#1 drag 间歇落空影响 → mouse_move + retry 缓解。
    """

    SCREEN_NAME: ClassVar[str] = '货币战争-备战'
    # drag 落点:前排-1 avatar(D-36 确认 drag 到角色头像穿,非详情装备槽 D-23)。
    # screen_info 前排-1..4 x:743/887/1033/1179,y~350(头像)。
    FRONT_AVATARS: ClassVar[list[Point]] = [
        Point(743, 350), Point(887, 350), Point(1033, 350), Point(1179, 350),
    ]
    # avatar-slot 验穿(D-41/R19):目标 avatar 下方 mini icon 区(已装备显示处;D-41 测 y=479),
    # drag 前后 CV-diff → 变了=穿(新装/合成),不变=落空。robust 合成/reflow/read漏检(替 count-verify)。
    BELOW_ICON_Y: ClassVar[int] = 479             # 前排 avatar 下方 mini icon 中心 y(avatar y350 → below 479)
    BY_HALF: ClassVar[int] = 30                   # below-icon crop 半高
    BX_HALF: ClassVar[int] = 35                   # below-icon crop 半宽
    BELOW_DIFF_THRESHOLD: ClassVar[float] = 8.0   # drag 前后 diff 阈值(>阈值=穿了;待跨局面调)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-全员装备')

    def _get_templates(self):
        """加载 cw_equip SIFT 模板(缓存 ctx.cw_equip_templates,首次 load 后复用)。"""
        cached = getattr(self.ctx, 'cw_equip_templates', None)
        if cached is not None:
            return cached
        base = get_project_root() / 'assets/template'
        equip_dir = base / 'currency_war' / 'equip_plaza'   # 混合库(plaza 官方+手工补充)
        if not equip_dir.is_dir():
            equip_dir = base / 'currency_war' / 'equip_legacy'
        if not equip_dir.is_dir():
            log.warning(f'[cw-equip] cw_equip 模板库不存在 {equip_dir}')
            return None
        templates = load_equip_templates(equip_dir)
        self.ctx.cw_equip_templates = templates
        log.info(f'[cw-equip] 加载 {len(templates)} 个 cw_equip 模板(缓存 ctx)')
        return templates

    def _get_tm_grays(self):
        """加载 cw_equip TM grays(缓存 ctx.cw_equip_tm_grays;``read_row_equipped`` 读 avatar 已穿用)。

        与 ``_get_templates`` 互补:后者 SIFT keypoint/descriptor(read_equips owned 列用);本函数返
        简单 gray(``matchTemplate`` 用,read_equipped_below below-avatar mini icon 用)。两套同源(`assets/template/cw_equip`)。
        """
        cached = getattr(self.ctx, 'cw_equip_tm_grays', None)
        if cached is not None:
            return cached
        base = get_project_root() / 'assets/template'
        equip_dir = base / 'currency_war' / 'equip_plaza'   # 混合库(同 _get_templates)
        if not equip_dir.is_dir():
            equip_dir = base / 'currency_war' / 'equip_legacy'
        if not equip_dir.is_dir():
            log.warning(f'[cw-equip] cw_equip 模板库不存在 {equip_dir}')
            return None
        grays = load_equip_tm_grays(equip_dir)
        self.ctx.cw_equip_tm_grays = grays
        log.info(f'[cw-equip] 加载 {len(grays)} 个 cw_equip TM grays(缓存 ctx)')
        return grays

    def _drag_equip(self, start: Point, target: Point,
                    verify_y: int | None = None) -> tuple[bool, float]:
        """单次 drag 穿戴 + bug#1 mitigation + avatar-slot CV-diff 验穿。返 (是否穿上, diff)。

        ``verify_y`` = 目标 avatar 的 below-icon 中心 y(默认前排 479;后排按 avatar_to_below
        = rect.y2+14,ADR-0154 后排支持)。bug#1 缓解(2026-08-11 加,live A8 实跑诊断):drag 前
        ``mouse_move(start)``(零移动)。CV-diff 验穿(R19):drag 前后对比目标 avatar 下方
        mini icon 区,变了=穿(robust 合成消耗/reflow,替 count-verify)。
        """
        cur = self.screenshot()
        self.ctx.controller.mouse_move(start)
        time.sleep(0.2)
        self.ctx.controller.drag_to(start=start, end=target, duration=1.5, hold_time=0.5)
        time.sleep(1.5)  # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        # 光标 parking(审计 R4):drag 终点=目标 avatar,光标停其上 → Director heavy observe 的
        # read_deployed_chars SIFT 同 rect 读被遮。park 后再验穿截图(diff 裁剪区在 avatar 下方,
        # park 不影响 diff)。UID 黑块 = 中立区。
        self.park_cursor(after_wait=0.1)
        post = self.screenshot()
        vy = self.BELOW_ICON_Y if verify_y is None else verify_y
        diff = _below_icon_diff(cur, post, target.x, vy, self.BX_HALF, self.BY_HALF)
        return diff > self.BELOW_DIFF_THRESHOLD, diff

    def _get_avatar_templates(self):
        """加载立绘 SIFT 模板(ADR-0154 M7 身份用;缓存 ctx.cw_portrait_templates,与 deploy_bench 同源)。"""
        cached = getattr(self.ctx, 'cw_portrait_templates', None)
        if cached is not None:
            return cached
        base = get_project_root() / 'assets/template'
        portrait_dir = base / 'currency_war' / 'portrait_plaza'
        if not portrait_dir.is_dir():
            return None
        templates = load_avatar_templates(portrait_dir)
        self.ctx.cw_portrait_templates = templates
        log.info(f'[cw-equip] 加载 {len(templates)} 个 avatar 模板(M7 身份,缓存 ctx)')
        return templates

    def _slot_drag_point(self, row: str, slot: int) -> tuple[Point, int] | None:
        """(row, slot) → (avatar 拖拽点, below 验穿 y);ADR-0154 后排支持。

        前排用实测常量 FRONT_AVATARS(D-36 验,y350)+ BELOW_ICON_Y=479(D-41 验);
        后排从 screen_info rect 推导:drag_y = rect.y1+21(前排 329→350 校准外推),
        verify_y = rect.y2+14(avatar_to_below 同式,前排 467→481≈479 互证)。
        """
        if row == 'front':
            if 1 <= slot <= len(self.FRONT_AVATARS):
                return self.FRONT_AVATARS[slot - 1], self.BELOW_ICON_Y
            return None
        slots = _ctx_slots(self.ctx, '后排', 10)
        for idx, r in slots:
            if idx == slot:
                return Point((r.x1 + r.x2) // 2, r.y1 + 21), r.y2 + 14
        return None

    def _transfer_pair(self, deployed, occupied_m7, tgt_comp, deployed_by_name):
        """r90 C6:找一对转移(key_equip:非核心持有者 → 目标核心)。

        攻略装备转移常态(#9「龙丹装备转给火花」/#4「给景元的装备先让银枝用」/
        #31/#44/#232):过渡期 key_equips 穿在当前 5 人(r70 语义)是**待迁资产**;
        target 核心到场且有空槽 → 迁。返 (holder描述, 件名, src below-icon点, 核心名,
        dst avatar点) 或 None。
        r99 必修:本方法曾误接 `@operation_node(name='全员装备', is_start_node=True)`
        (r90 插入时装饰器错位)→ 被框架当起始节点无参调用 → TypeError 每轮崩
        (局19 r1 EquipAll ×7 连崩实证)。装饰器已归位 equip_all。
        """
        if tgt_comp is None or not tgt_comp.key_equips:
            return None
        for cc in tgt_comp.core_chars:
            ds = deployed_by_name.get(cc) or []
            d = next((x for x in ds if x.char_id == cc), None)
            if d is None:
                continue
            d_row, d_slot = d.position_pref or 'back', int(d.slot or 1)
            dst_pv = self._slot_drag_point(d_row, d_slot)
            if dst_pv is None:
                continue
            if len(occupied_m7.get((d_row, d_slot), [])) >= 3:
                continue   # 该核心槽满 → 试下一核心
            for (row, slot), names in occupied_m7.items():
                holder = next((x for x in deployed
                               if (x.position_pref or 'back') == row
                               and int(x.slot or 1) == slot), None)
                if holder is None or not holder.char_id:
                    continue
                if holder.char_id in tgt_comp.core_chars:
                    continue   # 已在核心身上 → 不动
                for n in names:
                    if n in tgt_comp.key_equips:
                        src_pv = self._slot_drag_point(row, slot)
                        if src_pv is None:
                            continue
                        # 源 = 持有者 avatar 下方 below-icon(穿着件所在;近似取 below 中心)
                        return (f'{holder.char_id}({row}-{slot})', n,
                                Point(src_pv[0].x, src_pv[1]), cc, dst_pv)
        return None

    def _zero_wear_sentinel(self, equipped: int, owned_names: list[str],
                            stop_reason: str) -> None:
        """零穿戴哨兵(W596/W593 方案②;纯观测,零行为变更)。

        触发面(DESIGN §五):本 op 结束时 worn_added==0 且 owned 有**可穿**件
        (工具类过滤,与穿戴决策同口径)且 state.round_num≥3 → defect_ledger 记
        ``equip_zero_wear`` 一条(带 owned 名单与 stop 原因;severity 走通道缺省
        L2 观测,不停机)。病灶出处:局22(r3~r9 连续零穿戴无一报警,排查靠
        三段证据合围)——本哨兵让下次复发当轮可查台账归因。
        round<3 不触发:r1~r2 开局 hold(ADR-0257)零穿戴是 by design。
        无 state(run 上下文缺失/离线)静默跳过。
        """
        if equipped > 0:
            return
        wearable_owned = [n for n in owned_names
                          if EQUIPMENTS.get(n) is not None
                          and EQUIPMENTS[n].category not in _TOOL_CATEGORIES]
        if not wearable_owned:
            return
        from sr_od.application.currency_war.telemetry import cw_telemetry
        _match = getattr(self.ctx, 'cw_match', None)
        st = getattr(getattr(_match, 'session', None), 'last_state', None)
        if st is None or int(getattr(st, 'round_num', 0) or 0) < 3:
            return
        cw_telemetry.record_defect(
            surface='equip', kind='equip_zero_wear',
            expected='owned 有可穿件且 round>=3:本 op 至少穿 1 件',
            observed=(f'worn_added=0 owned={wearable_owned} '
                      f'stop_reason={stop_reason or "循环自然结束(stall)"}'),
            plane=int(getattr(st, 'plane', 1) or 1),
            round_num=int(st.round_num),
            note=('观测面不停机;stop_reason=过渡期hold 为 by design 残留,'
                  '其余原因(分配方案空/drag 落空/pool_empty)出现即查执行链'))

    @operation_node(name='全员装备', is_start_node=True, node_max_retry_times=5)
    def equip_all(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # 前置:角色详情面板关(出售 可见 = 角色详情面板开,遮 col2;装备详情面板不遮 icon D-37)
        if self.round_by_ocr(screen, '出售', lcs_percent=0.8).is_success:
            log.info('[cw-equip] 角色详情面板开(出售可见)→ 停(下轮关时再装)')
            return self.round_success('角色详情面板开,跳过')
        templates = self._get_templates()
        if templates is None:
            return self.round_fail('cw_equip 模板库未加载')
        # 装备库区域 = screen_info「区域-道具装备」(多列 owned icon,D-40;坐标单一源 yml)
        rect = _area_rect(self.ctx, '区域-道具装备', self.SCREEN_NAME)
        if rect is None:
            return self.round_fail('screen_info 区域-道具装备 缺失')
        equip_rect = (rect.x1, rect.y1, rect.x2, rect.y2)
        # P0-2 drag 前占位检测:读前排 avatar 已穿(read_row_equipped below-avatar TM)→ 只往空槽 drag。
        # 修原 bug:target=FRONT_AVATARS[equipped] 按已穿计数索引 → 已穿槽被覆盖。空槽序号 1-based → FRONT_AVATARS[slot-1]。
        tmpl_grays = self._get_tm_grays()
        if tmpl_grays is None:
            return self.round_fail('cw_equip TM grays 未加载(无法读槽位占位)')
        # ===== M7 装备角色级分配(ADR-0154;方法论 M7:装备是角色特定的)=====
        # 身份(SIFT read_deployed_chars,**立绘模板**非装备模板)+ 两排已穿(read_row_equipped)
        # → equip_allocation(carry 先拿 key_equips 按序 → 其余 core → 剩余兜底)→ 逐件 drag 到
        # **该角色 avatar**(前排实测常量/后排 screen_info 推导)+ below CV-diff 验穿。
        # 身份读失败 → 退回旧 front-only 流程(robust;offline fixture 也走旧路径)。
        avatar_templates = self._get_avatar_templates()
        deployed = (read_deployed_chars(self.ctx, screen, avatar_templates)
                    if avatar_templates is not None else [])
        _match = self.ctx.cw_match
        _tgt_comp = (_match.session.target_comp
                     if (_match is not None and _match.session is not None) else None)
        # ⚖️ 过渡期持有语义修正(r70 审计刀②,替 2026-08-16 旧指示):旧版 form<COMMIT_FRAC
        # 全 P1 攒仓库 = 白板打 8 个战斗节点 + r9 boss(每场稳定掉血的确定性损失;r70 实证
        # P1 八战掉 62 血)。修正:过渡期**穿给当前上场的 5 人**——key_equips 命中件照穿
        # (未来迁给核心只付一次性拆卸),非 key 散件穿给当前板面高战力者(carry 优先);
        # 「攒给成型核心」只在**已定型**(非双轨)且 form 低时保留。
        _form = 0.0
        if _tgt_comp is not None and deployed:
            from sr_od.application.currency_war.kernel.cw_comps import (
                form_progress,
            )
            from sr_od.application.currency_war.kernel.cw_state import GameState
            _st = (_match.session.last_state if _match is not None else None) or GameState()
            _form = form_progress(_tgt_comp, _st)
        # W629-R1 扩口(批 2):state/last_state 通道读点点名迁移——
        # committed 读端唯一化(decision_v2.prep_brain.committed_from,
        # 内部 = cw_intention 权威派生);本处旧形为 last_state 通道裸直读
        # 双轨字段(在「session 读点」守卫措辞之外,W623 D3 活证据),随本批
        # 并入守卫辖域(state 通道 grep 锁,test_cw_w620/w628)。
        from sr_od.application.currency_war.decision_v2.prep_brain import (
            committed_from as _committed_from,
        )
        _dual = (not _committed_from(_match.session,
                                     _match.session.last_state)
                 if (_match is not None
                     and getattr(_match.session, 'last_state', None)
                     is not None) else True)   # 缺供给 = 双轨保守侧(D2)
        # r388(用户 live 质问「1-2 就乱装备」):开局轮(r≤2,奖励
        # 节点无战斗)穿装备零战斗变现,且阵容未起步(form≈0 时
        # 分配语义退化为「谁在场谁独占」——r2 一人穿 2 件实证);
        # key_equips 命中件照穿(命中即阵容意图明确),gen 散件
        # 攒到 r3 战斗轮再穿。与 r70「P1 白板也该穿」不冲突:
        # 白板 8 战指的是 r3+ 战斗期,不含奖励轮。
        # R3 修正(ADR-0257):开局 hold 不再依赖 target 存在。
        _st_hold = (getattr(_match.session, 'last_state', None)
                    if _match is not None else None)
        _round_now = (_st_hold.round_num
                      if (_st_hold is not None
                          and getattr(_st_hold, 'plane', 1) == 1) else None)
        # W607 H3/H2②(ADR-0461):hold 收窄+生锈豁免,开关走策略 registry
        # (DecisionV2Strategy 注入臂可达;default 栈无 registry 属性 → 缺省表
        # =全关,零漂移)。
        from sr_od.application.currency_war.kernel.cw_registry import (
            DEFAULT_REGISTRY,
        )
        from sr_od.application.currency_war.kernel.cw_state import ledger_node_type
        _reg_eq = (getattr(getattr(_match, 'strategy', None), 'registry', None)
                   or DEFAULT_REGISTRY)
        _node_type = (getattr(_st_hold, 'node_type', None)
                      if _st_hold is not None else None)
        if _node_type is None and _st_hold is not None and _round_now is not None:
            _node_type = ledger_node_type(_match.session,
                                          getattr(_st_hold, 'plane', 1),
                                          _round_now)
        _opening_round = _opening_hold_active(
            _round_now, _node_type,
            _reg_eq.opening_hold_battle_gate_enabled,
            _reg_eq.opening_hold_battle_nodes)
        _rust_release = _rust_release_active(
            list(getattr(_st_hold, 'enemy_affixes', []) or []) if _st_hold is not None else [],
            _reg_eq.rust_wear_release_enabled)
        _transition_hold = _transition_hold_active(_tgt_comp, _form, _dual, _opening_round)
        if _transition_hold:
            log.info('[cw-equip] 过渡期持有(opening=%s node=%s rust_release=%s form=%.2f):'
                     '非 key_equips 不穿(攒给成型核心)',
                     _opening_round, _node_type, _rust_release, _form)
        if deployed:
            # W209g 断点③:后排装备读槽随布局选档(旧硬编码 10 与布局档自相
            # 矛盾——deploy 拖 8 格坐标、装备读固定槽;select_back_layout
            # 双通道单一源,ADR-0385/0387)。
            from sr_od.application.currency_war.obs.cw_back_layout import (
                select_back_layout as _sel_bl,
            )
            _bk_n, _bk_pfx = _sel_bl(self.ctx, screen)
            _row_specs = (('front', '前排', 4), ('back', _bk_pfx, _bk_n))
            occupied_m7: dict[tuple[str, int], list[str]] = {}
            for row, prefix, n in _row_specs:
                row_occ = read_row_equipped(self.ctx, screen, tmpl_grays, prefix, n)
                for k, v in row_occ.items():
                    occupied_m7[(row, k)] = list(v)
            deployed_by_name: dict[str, list] = {}
            for d in deployed:
                if d.char_id:
                    deployed_by_name.setdefault(d.char_id, []).append(d)
            log.info('[cw-equip] M7 角色级分配:deployed=%s occupied=%s',
                     [(d.char_id, d.position_pref, d.slot) for d in deployed],
                     {f'{r}{s}': '+'.join(v) for (r, s), v in occupied_m7.items() if v})
            # ===== r90 C6 装备转移前置遍(攻略装备转移常态;≤3 件/次,落空即停) =====
            # 每件转移后重读两排占用(画面已变);below CV-diff 验落(同主循环验穿)。
            for _ in range(3):
                if self.round_by_ocr(self.screenshot(), '出售', lcs_percent=0.8).is_success:
                    log.info('[cw-equip] 转移遍:角色详情面板开 → 停')
                    break
                tp = self._transfer_pair(deployed, occupied_m7, _tgt_comp, deployed_by_name)
                if tp is None:
                    break
                holder_desc, tname, src_pt, cc_name, (dst_pt, dst_vy) = tp
                log.info('[cw-equip] C6 转移 %s 的 %s → %s(key_equip 过渡持有→核心)',
                         holder_desc, tname, cc_name)
                landed, diff = self._drag_equip(src_pt, dst_pt, dst_vy)
                if not landed:
                    # below-icon 拖拽起点是近似坐标,可能没抓中 → retry 一次
                    landed, diff = self._drag_equip(src_pt, dst_pt, dst_vy)
                if landed:
                    log.info('[cw-equip] C6 转移落(%s→%s,diff=%.1f);重读占用', tname, cc_name, diff)
                    _cur = self.screenshot()
                    occupied_m7 = {}
                    for row, prefix, n in _row_specs:   # W209g 断点③:随布局选档
                        row_occ = read_row_equipped(self.ctx, _cur, tmpl_grays, prefix, n)
                        for k, v in row_occ.items():
                            occupied_m7[(row, k)] = list(v)
                else:
                    log.info('[cw-equip] C6 转移 %s 落空(diff=%.1f,below 拖拽近似未中)→ 停本遍', tname, diff)
                    break
            equipped = 0
            stall = 0
            _stop_reason = ''   # 零穿戴哨兵(W596)归因字段:本轮为何停手
            _owned_last: list[str] = []   # 哨兵输入:循环内最后一次 owned 全量快照
            _snap_logged = False   # 每次装备只记一遍快照(循环重读不重复记)
            while stall < 2:
                cur = self.screenshot()
                if self.round_by_ocr(cur, '出售', lcs_percent=0.8).is_success:
                    log.info('[cw-equip] 角色详情面板开 → 停')
                    _stop_reason = '角色详情面板开'
                    break
                hits = read_equips(cur, templates, equip_rect=equip_rect)
                _owned_last = [n for n, _, _ in hits]
                wearable = [(n, p) for n, p, _ in hits
                            if EQUIPMENTS.get(n) is not None
                            and EQUIPMENTS[n].category not in _TOOL_CATEGORIES]
                # ADR-0358(W92 修法 A)搬运链写端:owned 持有面快照进 session,
                # 供 _pseudo_state 拷入决策 state.equips(持有面遥测/特征可见)。
                # 每次现读都覆写(穿戴后 owned 减少,末次读=最新持有面)。
                # W209g 断点②(ADR-0387 追加):写端**全量 hits**(工具进快照,
                # 采集层无权丢数据);过滤只辖 wearable 穿戴决策。
                if _match is not None and _match.session is not None:
                    _match.session.last_owned_equips = [n for n, _, _ in hits]
                if not _snap_logged:
                    # ADR-0391 λ 标定埋点(P14 假设表 λ 行「待遥测标定」的数据源):
                    # 每轮备战首次读板记 owned 全量快照(含工具;发放流只在
                    # 奖励/补给/投资策略/遭遇后事件点出现)——离线 diff 相邻轮
                    # 快照 = 各节点发放件数 → λ 与事件条件化修正(P14 记账)。
                    _st_ref = (getattr(_match.session, 'last_state', None)
                               if _match is not None else None)
                    _own_ct: dict[str, int] = {}
                    for n, _, _ in hits:
                        _own_ct[n] = _own_ct.get(n, 0) + 1
                    log.info('[cw!][grant] plane=%s round=%s owned=%s',
                             getattr(_st_ref, 'plane', '?'),
                             getattr(_st_ref, 'round_num', '?'), _own_ct)
                    # 判读锚点(P14 检验点 2):「缺什么囤什么」——目标 K 的
                    # 组件需求 − 当前库存正差,判读/值守按此报装备面。
                    if _tgt_comp is not None and _tgt_comp.key_equips:
                        from sr_od.application.currency_war.data.cw_synthesis import (
                            hoard_gaps,
                        )
                        gaps = hoard_gaps(list(_tgt_comp.key_equips),
                                          [n for n, _, _ in hits])
                        log.info('[cw!][hoard] gaps=%s', gaps or '库存已覆盖需求')
                    _snap_logged = True
                if not wearable:
                    log.info('[cw-equip] 无穿戴候选(count=%d,全工具/空)→ 停', len(hits))
                    _stop_reason = 'pool_empty(无穿戴候选)'
                    break
                alloc = equip_allocation(
                    _tgt_comp, deployed,
                    [n for n, _ in wearable], occupied_m7)
                if _transition_hold and _rust_release:
                    # W607 H2②(ADR-0461):库藏生锈在场,owned 滞留=主动喂敌
                    # (competitors.md:45)→ hold 豁免,分配序列全量穿戴。
                    log.info('[cw-equip] 库藏生锈在场 → hold 豁免(owned 滞留喂敌),全量穿戴')
                if _transition_hold and not _rust_release:
                    # 过渡期:过滤掉 gen 兜底项(分配序列中非 key_equips 命中的),只穿命脉件
                    _keys = set(_tgt_comp.key_equips) if _tgt_comp else set()
                    alloc = [a for a in alloc if a[1] in _keys]
                    if not alloc:
                        log.info('[cw-equip] 过渡期无 key_equips 命中(全攒着)→ 停')
                        _stop_reason = '过渡期hold:无 key_equips 命中(全攒着)'
                        break
                if not alloc:
                    # W596/W593 方案③:分配空做结构化归因(pool_empty/capacity_full/
                    # pairing_guard/no_deployed/unknown),替旧的一句话两义日志。
                    _empty_reason = equip_alloc_empty_reason(
                        _tgt_comp, deployed, [n for n, _ in wearable], occupied_m7)
                    log.info('[cw-equip] 分配方案空 原因=%s(owned=%s)→ 停',
                             _empty_reason, [n for n, _ in wearable])
                    _stop_reason = f'分配方案空:{_empty_reason}'
                    break
                char_name, want = alloc[0]
                ds = deployed_by_name.get(char_name) or []
                target_pv: tuple[Point, int] | None = None
                for d in ds:
                    pv = self._slot_drag_point(d.position_pref or 'back', int(d.slot or 1))
                    if pv is not None:
                        target_pv = pv
                        d_used = d
                        break
                if target_pv is None:
                    log.info('[cw-equip] %s 槽位坐标缺失 → 跳过该角色', char_name)
                    _stop_reason = f'{char_name} 槽位坐标缺失'
                    break
                entry = next(((n, p) for n, p in wearable if n == want), None)
                if entry is None:
                    stall += 1   # owned 列 reflow 瞬时 miss → 再读一次
                    continue
                name, (cx, cy) = entry
                target, verify_y = target_pv
                log.info('[cw-equip] M7 drag %s @(%d,%d) → %s(%s-%d) [%s]',
                         name, cx, cy, char_name, d_used.position_pref, d_used.slot,
                         'key' if (_tgt_comp and name in _tgt_comp.key_equips) else 'gen')
                landed, diff = self._drag_equip(Point(cx, cy), target, verify_y)
                if not landed:
                    landed, diff = self._drag_equip(Point(cx, cy), target, verify_y)   # bug#1 retry
                if landed:
                    equipped += 1
                    key = (d_used.position_pref or 'back', int(d_used.slot or 1))
                    occupied_m7.setdefault(key, []).append(name)
                    stall = 0
                    log.info('[cw-equip] %s → %s 穿了(diff=%.1f)', name, char_name, diff)
                else:
                    log.info('[cw-equip] %s retry 仍败(diff=%.1f)→ 停(bug#1 持续 or 后排坐标偏差)',
                             name, diff)
                    _stop_reason = 'drag 落空 retry 仍败(bug#1 持续/坐标偏差)'
                    break
            # 零穿戴哨兵(W596/W593 方案②;纯观测,不停机零行为变更)
            self._zero_wear_sentinel(equipped, _owned_last, _stop_reason)
            return self.round_success(f'M7 装备 {equipped} 件(角色级分配)')
        # ===== 旧 front-only 流程(身份读失败 fallback;原 ADR-0101 key_equips 优先)=====
        occupied = read_row_equipped(self.ctx, screen, tmpl_grays, '前排', len(self.FRONT_AVATARS))
        if occupied:
            log.info('[cw-equip] 前排已穿槽(跳过不覆盖): %s',
                     {k: '+'.join(v) for k, v in sorted(occupied.items())})
        slots = _empty_slots(occupied, len(self.FRONT_AVATARS))
        if not slots:
            log.info('[cw-equip] 前排 avatar 全已穿 → 无空槽,停')
            return self.round_success('前排 avatar 全已穿,跳过')
        # avatar-slot CV-diff 验穿(R19治本③/D-41:替 count-verify —— robust 合成消耗2件/列reflow/read漏检;
        # drag 前后对比目标 avatar 下方 mini icon 区,变了=穿[新装或合成],不变=drag 落空/非穿戴)
        equipped = 0
        for slot_idx in slots:
            cur = self.screenshot()
            if self.round_by_ocr(cur, '出售', lcs_percent=0.8).is_success:
                log.info('[cw-equip] 角色详情面板开 → 停')
                break
            hits = read_equips(cur, templates, equip_rect=equip_rect)
            unknown = [n for n, _, _ in hits if EQUIPMENTS.get(n) is None]
            if unknown:
                log.warning('[cw-equip] read_equips 命中但不在 EQUIPMENTS registry(名对齐缺失?R18 P1): %s',
                            sorted(set(unknown)))
            # 过滤工具类(拆装扳手/冶金炉等非 drag 穿,D-32 拆/转化副作用)
            # ⚠️ 过滤只辖**穿戴决策**(wearable);采集写端(W209g 断点②,
            # ADR-0387 追加)**全量**进 last_owned_equips——旧版把过滤后列表
            # 写快照,冶金炉/扳手从不进决策快照(owned 恒空实证,run 26 两件
            # 工具躺着无人知)。采集层无权丢数据,消费侧各自过滤。
            wearable = [(n, p) for n, p, _ in hits
                        if EQUIPMENTS.get(n) is not None and EQUIPMENTS[n].category not in _TOOL_CATEGORIES]
            # ADR-0358(W92 修法 A)搬运链写端(旧 front-only 路径同链)
            if _match is not None and _match.session is not None:
                _match.session.last_owned_equips = [n for n, _, _ in hits]
            if not wearable:
                log.info('[cw-equip] 无穿戴候选(count=%d,全工具/空)→ 停', len(hits))
                break
            # comp 驱动穿戴(ADR-0101):优先穿 target_comp.key_equips 命脉件,替 naive wearable[0]。
            _key_equips = (_tgt_comp.key_equips if _tgt_comp is not None else None)
            wearable = _prioritize_wearable(wearable, _key_equips)
            name, (cx, cy) = wearable[0]
            _tag = 'key_equip优先' if (_key_equips and name in _key_equips) else '通用'
            target = self.FRONT_AVATARS[slot_idx - 1]
            log.info('[cw-equip] drag %s @(%d,%d) → 前排-%d avatar (%d,%d)[空槽] [%s]',
                     name, cx, cy, slot_idx, target.x, target.y, _tag)
            landed, diff = self._drag_equip(Point(cx, cy), target)
            if landed:
                equipped += 1
                log.info('[cw-equip] %s 穿了(前排-%d below-icon diff=%.1f > %.1f)',
                         name, slot_idx, diff, self.BELOW_DIFF_THRESHOLD)
                continue
            # bug#1 间歇落空 → retry 一次(同件同槽;bug#1 随机,retry 可能成,2026-08-11 live A8 诊断)
            log.info('[cw-equip] %s drag 未变(diff=%.1f ≤ %.1f)→ retry(bug#1?)',
                     name, diff, self.BELOW_DIFF_THRESHOLD)
            landed2, diff2 = self._drag_equip(Point(cx, cy), target)
            if landed2:
                equipped += 1
                log.info('[cw-equip] %s retry 穿了(前排-%d diff=%.1f)', name, slot_idx, diff2)
                continue
            # retry 仍败 = 真问题(bug#1 持续 / 非穿戴 / 槽满),停(避免空转烧时间)
            log.info('[cw-equip] %s retry 仍败(diff=%.1f)→ 停(bug#1 持续 or 非穿戴)',
                     name, diff2)
            break
        return self.round_success(f'装备 {equipped} 件到前排 avatar(空槽 {slots})')
