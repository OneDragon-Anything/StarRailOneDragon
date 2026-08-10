# 未验证(dormant,货币战争自主推进期代码,需进对应画面按 skill review 重审后才能信)

"""货币战争 全员装备 op:read_equips 多列 owned → 过滤工具 → drag 穿戴类 → 前排角色头像 → count 验穿。

**机制(D-36~D-40)**:drag **穿戴类**装备(排除工具)→ 前排角色头像 (743,350) = 穿(D-36 轮滑鞋验)。
装备 owned = **多列规则网格**(col1 x1800-1918 + col2 x1660-1800 + ...,D-40),**无空槽**(「+」=星徽 icon D-38)。
read_equips(thr7)名准+无假阳(D-39,4/4 click 验),覆盖多列(区域 = screen_info「区域-道具装备」x1620-1918,D-40)。

**avatar-slot CV-diff 验穿(R19治本③,已替 count-verify)**:drag 前后对比目标 avatar 下方 mini icon 区
(CV diff > 阈值 = 穿[新装或合成都变 icon],不变 = drag 落空)。**robust 合成消耗2件/列reflow/read漏检**
(count-verify D-41 实测报3实4 失真:合成消耗2件 → column count 扰;avatar below-icon 变化直接观测,免受其扰)。

**dormant**:未接 BattlePrepCycle,待多列/三态完整建档 + 跨局面验证后激活。

**前置**:已在「货币战争-备战」,角色详情面板关(出售 不可见 —— 角色详情面板遮 col2;装备详情面板不遮 icon D-37)。
"""
import time
from pathlib import Path
from typing import ClassVar

import numpy as np

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_equipment import (
    EQUIPMENTS,
    load_equip_templates,
    read_equips,
)
from sr_od.application.currency_war.cw_obs_core import _area_rect
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# 工具类装备(拆装扳手/冶金炉/随便骰子等,非 drag 穿;D-34 单独处理)
_TOOL_CATEGORIES: set[str] = {'工具'}


class EquipAll(SrOperation):
    """备战:read_equips 多列 owned → 过滤工具 → drag 穿戴类 → 前排角色头像 → avatar-slot CV-diff 验穿。

    装备库区域 = screen_info「区域-道具装备」(多列 x1620-1918,D-40;坐标维护 yml 非硬编码)。
    avatar-slot 验穿(R19治本③,替 count-verify):drag 前后对比目标 avatar 下方 mini icon 区 CV-diff,
    变了=穿(新装/合成都变),不变=落空。robust 合成消耗2件/列reflow/read漏检(D-41 count-verify 报3实4 失真)。
    前置:已在「货币战争-备战」(角色详情面板关 —— 装备详情面板不遮 icon D-37)。**dormant**(未接 cycle,待多列/三态完整建档后激活)。
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
        # avatar-slot CV-diff 验穿(R19治本③/D-41:替 count-verify —— robust 合成消耗2件/列reflow/read漏检;
        # drag 前后对比目标 avatar 下方 mini icon 区,变了=穿[新装或合成],不变=drag 落空/非穿戴)
        equipped = 0
        while equipped < len(self.FRONT_AVATARS):
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
            target = self.FRONT_AVATARS[equipped]
            # 目标 avatar 下方 mini icon 区(drag 前 crop;D-41 测 below-icon y=479)
            bx, by = target.x, self.BELOW_ICON_Y
            pre_below = cur[by - self.BY_HALF:by + self.BY_HALF, bx - self.BX_HALF:bx + self.BX_HALF]
            log.info('[cw-equip] drag %s @(%d,%d) → 前排 avatar (%d,%d)', name, cx, cy, target.x, target.y)
            self.ctx.controller.drag_to(start=Point(cx, cy), end=target, duration=1.5, hold_time=0.5)
            time.sleep(1.5)  # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
            post = self.screenshot()
            post_below = post[by - self.BY_HALF:by + self.BY_HALF, bx - self.BX_HALF:bx + self.BX_HALF]
            diff = float(np.abs(pre_below.astype(np.int16) - post_below.astype(np.int16)).mean())
            if diff > self.BELOW_DIFF_THRESHOLD:
                equipped += 1
                log.info('[cw-equip] %s 穿了(avatar below-icon diff=%.1f > %.1f)',
                         name, diff, self.BELOW_DIFF_THRESHOLD)
            else:
                log.info('[cw-equip] %s drag 未变(diff=%.1f ≤ %.1f)→ 停(bug#1 落空/非穿戴)',
                         name, diff, self.BELOW_DIFF_THRESHOLD)
                break
        return self.round_success(f'装备 {equipped} 件到前排 avatar')
