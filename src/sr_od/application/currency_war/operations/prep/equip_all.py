# 未验证(货币战争自主推进期代码,已接 cycle + live 验穿;需按 od-dev-write-operation skill review 重审后才能信)

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
from pathlib import Path
from typing import ClassVar

import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_equipment import (
    EQUIPMENTS,
    load_equip_templates,
    load_equip_tm_grays,
    read_equips,
)
from sr_od.application.currency_war.cw_identity_obs import read_row_equipped
from sr_od.application.currency_war.cw_obs_core import _area_rect
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# 工具类装备(拆装扳手/冶金炉/随便骰子等,非 drag 穿;D-34 单独处理)
_TOOL_CATEGORIES: set[str] = {'工具'}


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
        equip_dir = Path(__file__).resolve().parents[6] / 'assets/template/cw_equip'
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
        equip_dir = Path(__file__).resolve().parents[6] / 'assets/template/cw_equip'
        if not equip_dir.is_dir():
            log.warning(f'[cw-equip] cw_equip 模板库不存在 {equip_dir}')
            return None
        grays = load_equip_tm_grays(equip_dir)
        self.ctx.cw_equip_tm_grays = grays
        log.info(f'[cw-equip] 加载 {len(grays)} 个 cw_equip TM grays(缓存 ctx)')
        return grays

    def _drag_equip(self, start: Point, target: Point) -> tuple[bool, float]:
        """单次 drag 穿戴 + bug#1 mitigation + avatar-slot CV-diff 验穿。返 (是否穿上, diff)。

        bug#1 缓解(2026-08-11 加,live A8 实跑诊断):drag 前 ``mouse_move(start)``(零移动)——
        ``before_screenshot`` 把光标移角落做截图卫生,紧接 drag 会因光标移动中被游戏判拖拽落空(memory bug#1 /
        CLAUDE.md);先 mouse_move 到起点 + 稍顿,drag 从起点零移动出发,避间歇落空(同 run_supply_node:65 /
        buy_store_item:42 / run_megastar_node:82 模式)。CV-diff 验穿(R19):drag 前后对比目标 avatar 下方
        mini icon 区,变了=穿(robust 合成消耗/reflow,替 count-verify)。**每次调取自己的 pre 基线截图**
        (紧贴 drag,非用 loop 顶部 cur —— 基线越紧贴 drag,微变化越不被漏)。
        """
        cur = self.screenshot()
        self.ctx.controller.mouse_move(start)
        time.sleep(0.2)
        self.ctx.controller.drag_to(start=start, end=target, duration=1.5, hold_time=0.5)
        time.sleep(1.5)  # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        post = self.screenshot()
        diff = _below_icon_diff(cur, post, target.x, self.BELOW_ICON_Y, self.BX_HALF, self.BY_HALF)
        return diff > self.BELOW_DIFF_THRESHOLD, diff

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
            wearable = [(n, p) for n, p, _ in hits
                        if EQUIPMENTS.get(n) is not None and EQUIPMENTS[n].category not in _TOOL_CATEGORIES]
            if not wearable:
                log.info('[cw-equip] 无穿戴候选(count=%d,全工具/空)→ 停', len(hits))
                break
            name, (cx, cy) = wearable[0]
            target = self.FRONT_AVATARS[slot_idx - 1]
            log.info('[cw-equip] drag %s @(%d,%d) → 前排-%d avatar (%d,%d)[空槽]',
                     name, cx, cy, slot_idx, target.x, target.y)
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
