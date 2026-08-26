"""货币战争 位面详情 boss 采集 op(2026-08-26 佩佩局实证链的产品化)。

职责:在备战画面开位面详情 → 依次点三张位面卡 → 每卡点最右(boss)节点
→ 详情条大图标 SIFT 对拍 boss_avatar 20 模板 → 三位面 boss 全量采集。

为什么需要(2026-08-26 实证链):
- **简报读数的位面映射错位**:12:12 简报读 [巨鹿,造梦互动,深穹智械],
  位面详情逐位面亲证真值 = [巨鹿,**增熵**,**绘师**](用户确认)——简报三卡
  排列≠位面序,``plane_bosses[plane-1]`` 按序消费从第一天起就打错位面
  2/3 的 boss(boss_fit 错 boss)。修复裁决:boss 采集主通道改本 op,
  简报读数降级(接线批待裁决,本 op 先立)。
- **节点条小图认不出锁态**:位面 2/3 boss 节点是锁态紫框剪影,SIFT 特征
  塌缩(钢铁4 vs 增熵3 不断层且真值不在前二);**详情条大图标**(选中
  boss 节点后出现,~107px,特征 70+)破局——增熵 9:1、绘师 5:2 断层
  命中(用户方案:「点击最后的节点,下方会有更大的图标」)。

入口/出口契约:
- 入口:备战屏(检测 id_mark 备战标识-购买经验);由调用方在备战态调起。
- 出口:回备战屏(X 点击后验位面详情 id_mark 消失=真转移);采集结果经
  ``ctx.cw_plane_bosses`` 中转(与 ``cw_briefing_bosses`` 同模式;消费接线
  批待做,本 op 只负责采集)。

节点图:两节点,round 语义驱动(同 HandleBriefing 形态):
- ``采集``(start):入口核对(备战→点当前节点开详情 / 已在详情续采)→
  三位面循环(点卡→点boss节点→读大图标 SIFT,状态在 self,round_wait
  自环)→ 三位面齐 → 转 ``关闭``。
- ``关闭``:点 X → 验 id_mark 消失 → 写 ctx 中转 → success。

坐标全走 screen_info area(位面卡×3/boss大图标/关闭/两个屏 id_mark/
两个节点条);boss 节点圆由 ``read_plane_detail_nodes`` 动态定位(节点数
随位面/投资策略变:位面1=9,位面2/3=7,不硬编码)。
"""
import logging
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_log = logging.getLogger(__name__)

#: 位面详情屏(画面档 docs/game/screens/货币战争-位面详情.md)
_PD_SCREEN: str = '货币战争-位面详情'
_PREP_SCREEN: str = '货币战争-备战'
#: 三张位面卡 area(点位面卡中心切换选中;节点带随选中位面切换)
_PLANE_CARD_AREAS: tuple[str, ...] = ('按钮-位面卡1', '按钮-位面卡2', '按钮-位面卡3')


class CollectPlaneBosses(SrOperation):
    """位面详情:逐位面采集 boss(三卡循环+大图标 SIFT;接管局/开局校准通用)。"""

    SCREEN_NAME: ClassVar[str] = _PD_SCREEN

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-位面详情boss采集')
        self._plane_bosses: list[str | None] = [None, None, None]   # 位面1..3
        self._cur_plane: int = 0          # 0-based 当前采集位面索引

    # ---- 内部工具 -------------------------------------------------------

    def _area_center(self, area_name: str, screen_name: str = _PD_SCREEN) -> Point | None:
        """screen_info area → 中心点(坐标单一源;无 area → None)。"""
        from sr_od.application.currency_war.cw_obs_core import _area_rect
        r = _area_rect(self.ctx, area_name, screen_name)
        if r is None:
            return None
        return Point((r.x1 + r.x2) // 2, (r.y1 + r.y2) // 2)

    def _boss_node_center(self) -> Point | None:
        """当前位面节点条的最右(boss)节点圆心(read_plane_detail_nodes 动态定位)。"""
        from sr_od.application.currency_war.cw_observation import (
            read_plane_detail_nodes,
        )
        slots = read_plane_detail_nodes(self.ctx, self.last_screenshot)
        if not slots:
            return None
        s = slots[-1]
        from sr_od.application.currency_war.cw_obs_core import _area_rect
        r = _area_rect(self.ctx, '区域-节点条', _PD_SCREEN)
        ox, oy = (r.x1, r.y1) if r is not None else (385, 514)
        return Point(s.cx + ox, s.cy + oy)

    def _read_boss_big_icon(self) -> str | None:
        """详情条 boss 大图标 → SIFT 对拍 boss_avatar 库 → boss 名 | None。

        大图标 area「区域-boss大图标」(~107px,特征 70+ vs 节点小图 ~17);
        未命中 → None(记日志留证;SIFT 断层判据防次名撞分)。
        """
        import cv2 as _cv2

        from sr_od.application.currency_war.cw_node_reader import match_boss_sift
        from sr_od.application.currency_war.cw_obs_core import _area_rect
        r = _area_rect(self.ctx, '区域-boss大图标', _PD_SCREEN)
        if r is None:
            return None
        from sr_od.application.currency_war import cw_observation as _cwo
        if not _cwo._BOSS_TEMPLATES:
            _cwo.read_plane_detail_nodes(self.ctx, self.last_screenshot)   # 懒加载预热
            if not _cwo._BOSS_TEMPLATES:
                return None
        patch = self.last_screenshot[r.y1:r.y2, r.x1:r.x2]
        gray = _cv2.cvtColor(patch, _cv2.COLOR_RGB2GRAY)
        hit = match_boss_sift(gray, _cwo._BOSS_TEMPLATES)
        if hit is None:
            _log.info('[cw-plane-boss] 位面%d 大图标 SIFT 未命中(拒判保守)',
                      self._cur_plane + 1)
            return None
        name, good = hit
        _log.info('[cw-plane-boss] 位面%d boss=%s(SIFT 好匹配 %d)',
                  self._cur_plane + 1, name, good)
        return name

    # ---- 节点图(round 语义驱动,同 HandleBriefing 形态) -----------------

    @operation_node(name='采集', is_start_node=True, node_max_retry_times=12)
    def collect(self) -> OperationRoundResult:
        """入口核对 + 三位面采集循环(状态在 self;round_wait 自环推进)。

        分支序:①已在位面详情(重跑/续采)→ 采集循环;②备战 → 点当前
        节点图标开详情(round_wait 等开);③其它屏 → retry 等。
        采集循环(每位面):点卡 → 点 boss 节点 → 读大图标 → 未命中
        round_retry(重点);命中 → 下一位面;三位面齐 → success(转关闭)。
        """
        screen = self.last_screenshot
        _in_pd = self.round_by_find_area(
            screen, _PD_SCREEN, '标识-位面详情标题', crop_first=False).is_success
        if not _in_pd:
            if self.round_by_find_area(screen, _PREP_SCREEN, '备战标识-购买经验',
                                       crop_first=False).is_success:
                from sr_od.application.currency_war.cw_observation import (
                    read_node_sequence,
                )
                slots = read_node_sequence(self.ctx, screen)
                cur = next((s for s in (slots or []) if s.state == 'current'), None)
                if cur is None:
                    return self.round_retry('备战节点条无当前槽(非clean帧),重读')
                from sr_od.application.currency_war.cw_obs_core import _area_rect
                r = _area_rect(self.ctx, '区域-节点条', _PREP_SCREEN)
                ox, oy = (r.x1, r.y1) if r is not None else (544, 24)
                self.ctx.controller.click(Point(cur.cx + ox, cur.cy + oy))
                time.sleep(1.5)   # MCP click 异步 ~1s + 开屏动画
                return self.round_wait('已点节点图标,等位面详情开')
            return self.round_retry('非备战非位面详情,等画面')

        # —— 在位面详情:采集循环 ——
        if self._cur_plane >= 3:
            return self.round_success('三位面采集完')
        # ① 点位面卡(选中当前采集位面)
        card = self._area_center(_PLANE_CARD_AREAS[self._cur_plane])
        if card is None:
            return self.round_fail(f'位面卡 area 缺失:{_PLANE_CARD_AREAS[self._cur_plane]}')
        self.ctx.controller.click(card)
        time.sleep(1.5)
        # ② 点该位面 boss 节点(动态定位;节点带随选中位面变)
        screen = self.screenshot()
        boss_pt = self._boss_node_center()
        if boss_pt is None:
            return self.round_retry('节点条未读出(切卡动画中),重读')
        self.ctx.controller.click(boss_pt)
        time.sleep(1.5)
        # ③ 读大图标 SIFT(命中即证详情条已更新到该位面 boss)
        self.screenshot()
        name = self._read_boss_big_icon()
        if name is None:
            return self.round_retry(f'位面{self._cur_plane + 1} 大图标未命中,重点')
        self._plane_bosses[self._cur_plane] = name
        _log.info('[cw-plane-boss] 采集进度:%s', self._plane_bosses)
        self._cur_plane += 1
        return self.round_wait(f'位面{self._cur_plane}完成,下一位面')

    @node_from(from_name='采集')   # 首跑教训:无显式边时「采集」success 被当 op 终点,关闭节点漏跑(画面留在位面详情)
    @operation_node(name='关闭并回写', node_max_retry_times=6)
    def close_and_report(self) -> OperationRoundResult:
        """点 X 关位面详情(验 id_mark 消失=真转移)→ 结果写 ctx 中转 → success。"""
        screen = self.screenshot()
        if self.round_by_find_area(screen, _PD_SCREEN, '标识-位面详情标题',
                                   crop_first=False).is_success:
            x = self._area_center('按钮-关闭位面详情')
            if x is None:
                return self.round_fail('关闭按钮 area 缺失')
            self.ctx.controller.click(x)
            time.sleep(1.5)
            screen = self.screenshot()
            if self.round_by_find_area(screen, _PD_SCREEN, '标识-位面详情标题',
                                       crop_first=False).is_success:
                return self.round_retry('点X未关,重试')
        # 已离开位面详情 → 写中转(消费接线批挂账)
        self.ctx.cw_plane_bosses = list(self._plane_bosses)   # type: ignore[attr-defined]
        _log.info('[cw-plane-boss] 采集完成 plane_bosses=%s(ctx.cw_plane_bosses 中转)',
                  self._plane_bosses)
        return self.round_success(f'boss采集:{self._plane_bosses}')
