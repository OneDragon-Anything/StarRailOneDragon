
"""货币战争 全员装备 op:read_equips 多列 owned → 过滤工具 → drag 穿戴类 → 前排角色头像 → count 验穿。

**机制(D-36~D-40)**:drag **穿戴类**装备(排除工具)→ 前排角色头像 (743,350) = 穿(D-36 轮滑鞋验)。
装备 owned = **多列规则网格**(col1 x1800-1918 + col2 x1660-1800 + ...,D-40),**无空槽**(「+」=星徽 icon D-38)。
read_equips(thr7)名准+无假阳(D-39,4/4 click 验),覆盖多列(区域 = screen_info「区域-道具装备」x1620-1918,D-40)。

**avatar-slot CV-diff 验穿(R19治本③,已替 count-verify)**:drag 前后对比目标 avatar 下方 mini icon 区
(CV diff > 阈值 = 穿[新装或合成都变 icon],不变 = drag 落空)。**robust 合成消耗2件/列reflow/read漏检**
(count-verify D-41 实测报3实4 失真:合成消耗2件 → column count 扰;avatar below-icon 变化直接观测,免受其扰)。

**已接 cycle**(CwScreenPrep 备战单轮 ③,live A8 实跑):装备量受 bug#1 drag 间歇落空影响。
bug#1 根治(W849 批,台账 6/6「retry 仍败」证明原地 retry 失败相关):拖前稳帧确认
(``_wait_stable_frame``)+ 落空补救链(``_wear_with_recovery``:坐标现读重定位 + 按压/移动参数逐档升级)。

**前置(外层判干净)**:建档画面判定确认「货币战争-备战」(入口 + 每次拖拽循环重入点)。
面板/浮窗态各有独立建档且盖备战 id_mark(角色详情面板盖右下「出战」)→ 判不出备战
即非干净,直接停;识别器 read_equip_grid 纯识别,画面状态判断统一在本层。
"""
import time
from collections.abc import Callable
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

# ===== 拖拽失败降级(dd-015;复盘 g_20260902_181254 修复项 A)=====
# 实证形态:同一(源件→目标)拖拽 diff=0.0 连败 4 轮,每轮整个装备步骤
# 中止(~18s/轮)且无跨轮记忆。修法三件:失败计数登记(session 级,跨轮
# 存活)→ 连败达限拉黑该(件,角色)对;单件失败跳过继续穿下一件(不再
# break 中止整批);拖点坐标错配修正见 ``CwOpEquipAll._slot_drag_point``。
DRAG_FAIL_BLACKLIST_LIMIT: int = 2   # 同一对连败达此次数 → 拉黑
_EQUIP_MAX_WEAR_ITERS: int = 20      # 穿戴主循环硬上限(防异常态空转;量级=owned 件数×2)


def equip_drag_key(item_name: str, char_name: str) -> tuple[str, str]:
    """装备拖拽失败记忆键(纯函数):(装备名, 角色名)。

    粒度取「件×角色」而非「件×槽位」:角色在场槽位一轮内稳定,而
    分配候选(alloc)只携带 角色+件名,槽位要到拖拽前才解析——键与
    过滤面同构才能在 alloc 生成后立即过滤拉黑对。
    """
    return (item_name, char_name)


def register_equip_drag_failure(counts: dict, key: tuple[str, str]) -> bool:
    """登记一次拖拽失败 → 返回是否已达拉黑线(纯函数,dd-015)。

    ``counts`` = session.equip_drag_fail_counts(局级持久,跨轮累积);
    同一对达 ``DRAG_FAIL_BLACKLIST_LIMIT`` 后恒返回 True(幂等拉黑)。
    """
    counts[key] = counts.get(key, 0) + 1
    return counts[key] >= DRAG_FAIL_BLACKLIST_LIMIT


def filter_alloc_blacklisted(alloc: list, counts: dict) -> list:
    """分配序列剔除已拉黑的(件→角色)对(纯函数,dd-015)。

    ``alloc`` 元素 = (角色名, 件名)(``equip_allocation`` 产出口径);
    拉黑对按 ``equip_drag_key`` 命中且计数达 ``DRAG_FAIL_BLACKLIST_LIMIT``
    才剔除——失败 1 次的对保留(补救链重试一次,再败才拉黑)。
    """
    return [pair for pair in alloc
            if counts.get(equip_drag_key(pair[1], pair[0]), 0)
            < DRAG_FAIL_BLACKLIST_LIMIT]

# ===== bug#1 drag 落空根治参数(replay/defect_ledger.jsonl drag 条目实证)=====
# 台账形态:retry 仍败 6/6 —— 原地 retry 与首拖共用同一帧读出的坐标与同一时序,
# 失败是**相关**的(首拖因画面未稳/按压未识别落空时,原地同参重拖同样落空),
# 「retry 一次」的独立性假设不成立 → 治本 = 稳帧确认 + 坐标现读重定位 + 参数升级。
DRAG_HOLD_TIME: float = 0.5    # 首拖按压保持秒数(拾取识别窗;升级档见 _WEAR_RETRY_PARAMS)
DRAG_DURATION: float = 1.5     # 首拖移动时长秒数
# 补救链每档(hold_time, duration):逐档加长按压与移动,对抗拾取识别窗的间歇漏识
_WEAR_RETRY_PARAMS: list[tuple[float, float]] = [(0.5, 1.5), (0.8, 2.0), (1.1, 2.5)]
_SETTLE_DIFF_THRESHOLD: float = 2.0   # 稳帧判据:相邻两帧全图像素差均值 < 阈值 = 画面已稳


def register_equip_worn(session, item_name: str, char_name: str,
                        row: str, slot: int,
                        produced_by: str = 'CwOpEquipAll') -> None:
    """装备分布期望态(§3 B-6 行 M7 装备拖拽;DD-019 后果节「装备分布」缺口)。

    落点已验(avatar-slot CV-diff 判穿)后调:``last_owned_equips`` −1 件 +
    ``tracked_deployed`` 目标角色 equips +1 件(字段本体推进)+ 两条目登记
    (owned 减/角色 equips 增;值带「待实读」= prep_obs 覆盖点可信读只清账
    不 diff)。槽位坐标系:deployed 槽位表下标 = 前排 slot−1 / 后排
    DEPLOYED_FRONT_CAPACITY+slot−1(与 apply_op_effect SellDeployed 同式)。
    best-effort:session 缺失 / infra 异常不阻塞穿戴主循环。
    """
    if session is None:
        return
    try:
        from sr_od.application.currency_war.kernel.cw_expected_state import (
            ExpectedEntry,
            expected_round_key,
            register_expected,
        )
        from sr_od.application.currency_war.kernel.cw_state import (
            DEPLOYED_FRONT_CAPACITY,
        )
        owned = list(getattr(session, 'last_owned_equips', None) or [])
        if item_name in owned:
            owned.remove(item_name)
            session.last_owned_equips = owned
        idx = (slot - 1 if row == 'front'
               else DEPLOYED_FRONT_CAPACITY + slot - 1)
        dep = list(getattr(session, 'tracked_deployed', None) or [])
        if 0 <= idx < len(dep) and dep[idx] is not None:
            dep[idx].equips = list(getattr(dep[idx], 'equips', None) or []) \
                + [item_name]
        at_round = expected_round_key(session)
        register_expected(session, ExpectedEntry(
            path=f'owned[{item_name}]', value='−1(穿戴,待实读)',
            produced_by=produced_by, at_round=at_round, kind='owned'))
        register_expected(session, ExpectedEntry(
            path=f'tracked_deployed[{idx}]',
            value=f'{char_name} 穿{item_name}(待实读)',
            produced_by=produced_by, at_round=at_round, kind='tracked'))
    except Exception as e:  # noqa: BLE001  观测面不阻塞穿戴
        log.info('[cw-equip] 装备分布期望登记跳过: %s', e)


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

    纯函数(可离线 fixture 测):crop below-icon 区 → 两帧像素绝对差均值。``CwOpEquipAll`` 用它判 drag
    是否落地穿(robust 合成消耗2件/列reflow/read漏检,替 count-verify D-41)。默认 below_y/bx_half/by_half
    对齐 ``CwOpEquipAll`` 类常量(D-41 测 below-icon y=479),测试可直接调。

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

    comp 驱动穿戴(替 naive ``wearable[0]``):CwOpEquipAll 优先穿 target comp 的关键装备
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
    「攒给成型核心」的机会成本被压制。纯谓词;消费点=CwOpEquipAll hold 过滤
    分支(开关=registry.rust_wear_release_enabled,默认关=零漂移)。
    """
    if not gate:
        return False
    return '库藏生锈' in set(enemy_affixes or [])


class CwOpEquipAll(SrOperation):
    """备战:read_equips 多列 owned → 过滤工具 → drag 穿戴类 → 前排**空**角色头像(P0-2 占位检测)→ avatar-slot CV-diff 验穿。

    装备库区域 = screen_info「区域-道具装备」(多列 x1620-1918,D-40;坐标维护 yml 非硬编码)。
    **P0-2 drag 前占位检测**:``read_row_equipped`` 读前排 avatar 已穿 → 只往空槽 drag(``_empty_slots``,
    修原 ``target=FRONT_AVATARS[equipped]`` 按已穿计数索引 → 已穿槽被覆盖)。
    avatar-slot 验穿(R19治本③,替 count-verify):drag 前后对比目标 avatar 下方 mini icon 区 CV-diff,
    变了=穿(新装/合成都变),不变=落空。robust 合成消耗2件/列reflow/read漏检(D-41 count-verify 报3实4 失真)。
    前置:已在「货币战争-备战」(角色详情面板关 —— 装备详情面板不遮 icon D-37)。**已接 cycle**(CwScreenPrep 备战单轮 ③);bug#1 根治 = 拖前稳帧确认 + 落空补救链(坐标现读重定位 + 参数升级)。
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

    def _wait_stable_frame(self, interval: float = 0.3,
                           budget_s: float = 1.2) -> MatLike:
        """拖前稳帧确认:等相邻两帧全图像素差均值 < 阈值(画面动画收尾)再拖。

        根因关系:drag 坐标来自截图现读;若备战面板入场/上件 reflow 动画未收尾,
        帧内 icon 位置与终态错位 → 按压抓空(drag 物理落空形态之一)。预算耗尽
        仍未稳 → 放行返回当前帧(不卡死流程;落空由补救链兜底)。
        """
        deadline = time.time() + budget_s
        prev = self.screenshot()
        while time.time() < deadline:
            time.sleep(interval)
            cur = self.screenshot()
            diff = float(np.abs(prev.astype(np.int16) - cur.astype(np.int16)).mean())
            if diff < _SETTLE_DIFF_THRESHOLD:
                return cur
            prev = cur
        return prev

    def _drag_equip(self, start: Point, target: Point,
                    verify_y: int | None = None,
                    hold_time: float = DRAG_HOLD_TIME,
                    duration: float = DRAG_DURATION) -> tuple[bool, float]:
        """单次 drag 穿戴 + 拖前稳帧确认 + avatar-slot CV-diff 验穿。返 (是否穿上, diff)。

        ``verify_y`` = 目标 avatar 的 below-icon 中心 y(默认前排 479;后排按 avatar_to_below
        = rect.y2+14,ADR-0154 后排支持)。``hold_time``/``duration`` = 按压保持/移动时长
        (补救链逐档升级,常量 _WEAR_RETRY_PARAMS)。拖前 ``_wait_stable_frame`` 确认画面已稳
        (动画未收尾时按压抓空 = 落空主形态);稳帧结果直接用作 CV-diff 基准帧。
        """
        cur = self._wait_stable_frame()
        self.ctx.controller.mouse_move(start)
        time.sleep(0.2)
        self.ctx.controller.drag_to(start=start, end=target,
                                    duration=duration, hold_time=hold_time)
        time.sleep(1.5)  # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        # 光标 parking(审计 R4):drag 终点=目标 avatar,光标停其上 → Director heavy observe 的
        # read_deployed_chars SIFT 同 rect 读被遮。park 后再验穿截图(diff 裁剪区在 avatar 下方,
        # park 不影响 diff)。UID 黑块 = 中立区。
        self.park_cursor(after_wait=0.1)
        post = self.screenshot()
        vy = self.BELOW_ICON_Y if verify_y is None else verify_y
        diff = _below_icon_diff(cur, post, target.x, vy, self.BX_HALF, self.BY_HALF)
        return diff > self.BELOW_DIFF_THRESHOLD, diff

    def _wear_with_recovery(self, start: Point, target: Point, verify_y: int | None,
                            relocate: Callable[[], Point | None]) -> tuple[bool, float]:
        """单件穿戴 + 落空补救链(bug#1 根治;替原地同参 retry)。

        台账实证(replay/defect_ledger.jsonl drag 条目,6/6 retry 仍败):原地 retry 与
        首拖共用同一帧坐标/同一时序 → 失败相关。补救链每次重试前:① park 光标
        ② ``relocate()`` 现读坐标(列 reflow/首读动画帧错位自愈)③ 参数升级
        (_WEAR_RETRY_PARAMS 逐档)。``relocate`` 返 None = 件已不在 owned(被合成消耗/
        reflow miss)→ 立即放弃本件(交还主循环 stall 语义,不硬撑)。全档仍败 →
        (False, 末次 diff),交由主循环停手并进哨兵归因。
        """
        cur_start = start
        diff = 0.0
        for attempt, (hold, dur) in enumerate(_WEAR_RETRY_PARAMS):
            if attempt > 0:
                self.park_cursor(after_wait=0.1)
                fresh = relocate()
                if fresh is None:
                    log.info('[cw-equip] 补救链:件已不在 owned(消耗/reflow)→ 放弃本件')
                    return False, diff
                if (fresh.x, fresh.y) != (cur_start.x, cur_start.y):
                    log.info('[cw-equip] 补救链重定位 (%d,%d)→(%d,%d)',
                             cur_start.x, cur_start.y, fresh.x, fresh.y)
                cur_start = fresh
                log.info('[cw-equip] 补救重试 #%d hold=%.1f dur=%.1f', attempt, hold, dur)
            landed, diff = self._drag_equip(cur_start, target, verify_y,
                                            hold_time=hold, duration=dur)
            if landed:
                return True, diff
        return False, diff

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

        dd-015 排障修正:后排 area 前缀原硬编码「后排」(6 槽档),而占用读侧
        (M7 ``_row_specs``)与部署侧均走 ``select_back_layout`` 档位前缀
        (「后排7槽」/「后排8槽」,ADR-0385)——布局非 6 槽时槽号→rect 错配
        半个槽位,拖点落在邻槽(装备穿到别人身上/落空,diff 恒 0.0 假失败,
        复盘 g_20260902_181254 A 条「back-3 拖点坐标可疑」的坐标侧根因)。
        修正 = 与占用读侧同源(布局选档单一入口);读档失败退 6 槽基线。
        """
        if row == 'front':
            if 1 <= slot <= len(self.FRONT_AVATARS):
                return self.FRONT_AVATARS[slot - 1], self.BELOW_ICON_Y
            return None
        _pfx = '后排'
        try:
            from sr_od.application.currency_war.obs.cw_back_layout import (
                select_back_layout as _sel_bl,
            )
            _pfx = _sel_bl(self.ctx, self.screenshot())[1] or _pfx
        except Exception:   # noqa: BLE001  选档失败退 6 槽基线(旧行为)
            pass
        slots = _ctx_slots(self.ctx, _pfx, 10)
        for idx, r in slots:
            if idx == slot:
                return Point((r.x1 + r.x2) // 2, r.y1 + 21), r.y2 + 14
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
        from sr_od.application.currency_war.telemetry import defects as cw_telemetry
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
        # 前置(外层判干净):建档画面判定。面板/浮窗态各有独立建档且盖备战 id_mark
        # (角色详情面板盖右下「出战」)→ 判不出「货币战争-备战」即非干净,不识别;
        # 识别器 read_equip_grid 纯识别,画面状态判断统一在本层(单一源)。
        current = self.check_and_update_current_screen(
            screen, screen_name_list=[self.SCREEN_NAME])
        if current != self.SCREEN_NAME:
            log.info('[cw-equip] 当前画面 %s 非干净备战 → 停(下轮再装)', current)
            return self.round_success('非干净备战画面,跳过')
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
        from sr_od.application.currency_war.decision.decision_v2.prep_brain import (
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
        # W880 装备环境信号单源(设计 §2.2):构造点唯一 = 本处,一次打包传递;
        # 生锈豁免(门)、fill3(量)、变宝为废(序)三个变体一律吃 signals,
        # 不再各自摸 state;state 缺失(离线/旧栈)= 空集 → 判据安全默认不启用。
        from sr_od.application.currency_war.kernel.cw_equip_env import (
            apply_equip_env_variants as _apply_env_variants,
        )
        from sr_od.application.currency_war.kernel.cw_equip_env import (
            build_equip_env_signals,
        )
        _equip_signals = build_equip_env_signals(_st_hold)
        _rust_release = _rust_release_active(
            sorted(_equip_signals.enemy_affixes),
            _reg_eq.rust_wear_release_enabled)
        _transition_hold = _transition_hold_active(_tgt_comp, _form, _dual, _opening_round)
        # fill 防线③(设计 §3.1):过渡期 hold(非生锈豁免态)不激活 fill——
        # hold 语义(攒给成型核心)优先,防两套意图打架
        _fill_hold = bool(_transition_hold and not _rust_release)
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
            # 「过渡持有→核心转移」不在本 op 实现:装备不能角色间直拖(机制纠正),
            # 转移唯一途径 = 卖角色(装备全额回区)或拆装扳手(消耗工具)——
            # 未来表达 = 决策器输出(卖角色+重买/重穿,或扳手两段),见
            # docs/game/currency_war/research/equipment_mechanics.md「装备转移机制」节。
            equipped = 0
            stall = 0
            _wear_iters = 0   # dd-015:穿戴硬上限计数(失败继续后 stall 不再兜底中止)
            _stop_reason = ''   # 零穿戴哨兵(W596)归因字段:本轮为何停手
            _owned_last: list[str] = []   # 哨兵输入:循环内最后一次 owned 全量快照
            _snap_logged = False   # 每次装备只记一遍快照(循环重读不重复记)
            # dd-015:拖拽失败记忆(session 级,跨轮累积;无 session 时局部 dict
            # ——单轮内拉黑仍生效,只是不跨轮)
            _fail_counts: dict = {}
            if (_match is not None and _match.session is not None):
                _fail_counts = _match.session.equip_drag_fail_counts
            while stall < 2 and _wear_iters < _EQUIP_MAX_WEAR_ITERS:
                _wear_iters += 1
                cur = self.screenshot()
                if self.check_and_update_current_screen(
                        cur, screen_name_list=[self.SCREEN_NAME]) != self.SCREEN_NAME:
                    log.info('[cw-equip] 画面漂移(面板/浮窗开)→ 停')
                    _stop_reason = '画面非干净备战'
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
                # W880 装备分配入口(kernel/cw_equip_env.apply_equip_env_
                # variants;fill3 量变体与变宝为废序变体已随各自开关族删除
                # ——旧方案清退批,清查报告 OLD_MIX_AUDIT §1.3,现=基分配
                # equip_allocation 直通零漂移;W849 拖拽执行链零触碰)。
                alloc, _env_actions = _apply_env_variants(
                    _equip_signals, _reg_eq, _match.session, _tgt_comp,
                    deployed, [n for n, _ in wearable], occupied_m7,
                    hold_active=_fill_hold)
                if _transition_hold and _rust_release:
                    # W607 H2②(ADR-0461):库藏生锈在场,owned 滞留=主动喂敌
                    # (competitors.md:45)→ hold 豁免,分配序列全量穿戴。
                    log.info('[cw-equip] 库藏生锈在场 → hold 豁免(owned 滞留喂敌),全量穿戴')
                # (P1→P2 接口机制·②分配义务 hold 豁免已随五开关定谳清理
                # 删除,ADR-0487:过渡期 hold 过滤恢复无条件既有语义。)
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
                # dd-015:剔除已拉黑(件→角色)对后再取队首(失败 1 次的保留,
                # 补救链重试一次;再败即拉黑,不再进后续轮次的 alloc)
                alloc = filter_alloc_blacklisted(alloc, _fail_counts)
                if not alloc:
                    log.info('[cw-equip] 分配对全部拉黑(拖拽连败,dd-015)→ 停;'
                             ' 拉黑集=%s', sorted(_fail_counts))
                    _stop_reason = '分配对全部拉黑(drag 连败,dd-015)'
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
                    # 日志与行为对齐(593-596 语义修正,原为 break):单角色坐标缺失
                    # 只跳过该分配项,不中断整轮穿戴。同一分配项会反复顶到队首,
                    # stall 计数防死循环(连续 2 次定位不了 → 出循环交哨兵归因)。
                    log.info('[cw-equip] %s 槽位坐标缺失 → 跳过该分配项', char_name)
                    stall += 1
                    _stop_reason = f'{char_name} 槽位坐标缺失'
                    continue
                entry = next(((n, p) for n, p in wearable if n == want), None)
                if entry is None:
                    stall += 1   # owned 列 reflow 瞬时 miss → 再读一次
                    continue
                name, (cx, cy) = entry
                target, verify_y = target_pv
                log.info('[cw-equip] M7 drag %s @(%d,%d) → %s(%s-%d) [%s]',
                         name, cx, cy, char_name, d_used.position_pref, d_used.slot,
                         'key' if (_tgt_comp and name in _tgt_comp.key_equips) else 'gen')

                def _relocate_item(_want: str = want,
                                   _tmpl=templates,
                                   _rect=equip_rect) -> Point | None:
                    """补救链坐标现读:件被合成消耗/列 reflow 后,首读坐标作废 → 现读。

                    默认参绑定当轮值(ruff B023:闭包不绑循环变量)。
                    """
                    _hits = read_equips(self.screenshot(), _tmpl, equip_rect=_rect)
                    _e = next(((n, p) for n, p, _ in _hits if n == _want), None)
                    return Point(_e[1][0], _e[1][1]) if _e is not None else None

                landed, diff = self._wear_with_recovery(Point(cx, cy), target,
                                                        verify_y, _relocate_item)
                if landed:
                    equipped += 1
                    key = (d_used.position_pref or 'back', int(d_used.slot or 1))
                    occupied_m7.setdefault(key, []).append(name)
                    stall = 0
                    # 装备分布期望态(§3 B-6;落点已验后才登记)
                    if _match is not None and _match.session is not None:
                        register_equip_worn(_match.session, name, char_name,
                                            d_used.position_pref or 'back',
                                            int(d_used.slot or 1))
                    log.info('[cw-equip] %s → %s 穿了(diff=%.1f)', name, char_name, diff)
                else:
                    # dd-015:失败不中止整批——登记失败(≥2 次拉黑该对,跨轮存活),
                    # 跳过继续穿下一件。原 break 语义(复盘 g_20260902_181254 A 条
                    # 实证:单件连败 → 当轮其余 8-10 件全不穿)废弃;真持续失败由
                    # 拉黑过滤自然收敛(全部拉黑 → 上分支停),硬上限 _EQUIP_MAX_
                    # WEAR_ITERS 兜底防异常态空转。
                    # 定谳(2026-09-02,临时捕获钩子已删):该场景主根因 = M7 分配
                    # 把阵营星徽分给同阵营角色(游戏装备不上,diff=0,机制见
                    # equipment_mechanics §6 星徽 add-if-absent)——分配层已加同阵营
                    # 排除,本降级只兜未知失败(设备/画面态偶发)。
                    _bl = register_equip_drag_failure(
                        _fail_counts, equip_drag_key(name, char_name))
                    if _bl:
                        log.warning('[cw!][equip] %s → %s 拖拽连败 %d 次 → 拉黑(dd-015,'
                                    ' diff=%.1f;后排拖点已随布局档修正)',
                                    name, char_name,
                                    _fail_counts[equip_drag_key(name, char_name)], diff)
                    else:
                        log.info('[cw-equip] %s 补救链仍败(diff=%.1f)→ 跳过继续下一件(dd-015)',
                                 name, diff)
                    _stop_reason = 'drag 落空(失败继续,dd-015)'
                    break
            # 零穿戴哨兵(W596/W593 方案②;纯观测,不停机零行为变更)
            self._zero_wear_sentinel(equipped, _owned_last, _stop_reason)
            return self.round_success(f'M7 装备 {equipped} 件(角色级分配)')
        # ===== 旧 front-only 流程(身份读失败 fallback;原 ADR-0101 key_equips 优先)=====
        # dd-015:回退路径失败记忆(session 级;键=(件名,''),与主路径键空间不交——
        # 两路径互斥,M7 要求 deployed 身份可读,回退路径恰是其读失败分支)。
        _fail_counts_fb: dict = {}
        if _match is not None and _match.session is not None:
            _fail_counts_fb = _match.session.equip_drag_fail_counts
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
            if self.check_and_update_current_screen(
                    cur, screen_name_list=[self.SCREEN_NAME]) != self.SCREEN_NAME:
                log.info('[cw-equip] 画面漂移(面板/浮窗开)→ 停')
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
            # dd-015:回退路径同主路径纪律——拉黑件不重试,失败继续下一槽。
            # 回退路径无角色身份(拖点=空槽 avatar),拉黑键取 (件名, '')。
            wearable = [(n, p) for n, p in wearable
                        if _fail_counts_fb.get(equip_drag_key(n, ''), 0)
                        < DRAG_FAIL_BLACKLIST_LIMIT]
            if not wearable:
                log.info('[cw-equip] 回退路径候选全拉黑(dd-015)→ 停')
                break
            name, (cx, cy) = wearable[0]
            _tag = 'key_equip优先' if (_key_equips and name in _key_equips) else '通用'
            target = self.FRONT_AVATARS[slot_idx - 1]
            log.info('[cw-equip] drag %s @(%d,%d) → 前排-%d avatar (%d,%d)[空槽] [%s]',
                     name, cx, cy, slot_idx, target.x, target.y, _tag)

            def _relocate_front(_tmpl=templates, _rect=equip_rect,
                                _keys=_key_equips) -> Point | None:
                """补救链坐标现读(旧 front-only 路径):现读 owned 同优先序取最新坐标。

                默认参绑定当轮值(ruff B023:闭包不绑循环变量)。
                """
                _hits = read_equips(self.screenshot(), _tmpl, equip_rect=_rect)
                _wear = [(n, p) for n, p, _ in _hits
                         if EQUIPMENTS.get(n) is not None
                         and EQUIPMENTS[n].category not in _TOOL_CATEGORIES]
                _wear = _prioritize_wearable(_wear, _keys)
                return Point(_wear[0][1][0], _wear[0][1][1]) if _wear else None

            landed, diff = self._wear_with_recovery(Point(cx, cy), target, None,
                                                    _relocate_front)
            if landed:
                equipped += 1
                # 装备分布期望态(§3 B-6;回退路径无角色身份,槽=前排空槽序号)
                if _match is not None and _match.session is not None:
                    register_equip_worn(_match.session, name, '',
                                        'front', slot_idx)
                log.info('[cw-equip] %s 穿了(前排-%d below-icon diff=%.1f > %.1f)',
                         name, slot_idx, diff, self.BELOW_DIFF_THRESHOLD)
                continue
            # dd-015:失败不中止——登记(≥2 次拉黑该件,回退键=(件名,'')),
            # 继续下一空槽。真持续失败由拉黑过滤收敛(候选全拉黑 → 上分支停)。
            _bl_fb = register_equip_drag_failure(_fail_counts_fb,
                                                 equip_drag_key(name, ''))
            if _bl_fb:
                log.warning('[cw!][equip] %s 拖拽连败 → 拉黑(dd-015 回退路径, diff=%.1f)',
                            name, diff)
            else:
                log.info('[cw-equip] %s 补救链仍败(diff=%.1f)→ 继续下一槽(dd-015)', name, diff)
        return self.round_success(f'装备 {equipped} 件到前排 avatar(空槽 {slots})')
