"""货币战争 位面情报采集 op(2026-08-26 佩佩局实证链的产品化)。

职责:在备战画面开位面详情,一次采集三类情报:
- **三位面 boss**:依次点三张位面卡 → 每卡点最右(boss)节点 → 详情条
  类型名标签验「首领」→ 大图标 SIFT 对拍 boss_avatar 20 模板(用户方案:
  「点击最后的节点,下方会有更大的图标」——锁态小图 SIFT 特征塌缩认不出,
  大图标破局:增熵 9:1、绘师 5:2 断层命中)。**boss 节点两种渲染态
  (W221/ADR-0398,run 29/30 同夜实证)**:头像态(节点=红框头像,大图标
  SIFT 断层命中)与**徽章态**(节点=通用金色徽章、详情条=「首领节点」+
  通用描述,**本屏无任何身份信息**——run 30 位面 1 带内 9 圆逐圆 SIFT
  全拒 + 大图标 SIFT 未命中 12 次实证)→ 徽章态位面记 None 跳过
  (``conclude_plane_boss`` 分流),不 retry 空转;
- **敌人词缀**:位面详情词缀横条随采(词缀只在简报/位面详情/敌人信息
  浮层三画面,备战无此条——首版误判备战常驻,空读两轮后用户纠正);
- **位面节点带**:``read_plane_detail_nodes`` 读选中位面节点(类型/序)。

为什么需要(2026-08-26 实证链):
- **简报读数的位面映射错位**:12:12 简报读 [巨鹿,造梦互动,深穹智械],
  位面详情逐位面亲证真值 = [巨鹿,**增熵**,**绘师**](用户确认)——简报三卡
  排列≠位面序,``plane_bosses[plane-1]`` 按序消费从第一天起就打错位面
  2/3 的 boss(boss_fit 错 boss)。修复裁决:boss 采集主通道改本 op,
  简报读数降级候选集(ADR-0397 已接线:本 op = 开局局/接管局统一实采通道)。

入口/出口契约:
- 入口:备战屏(检测 id_mark 备战标识-购买经验);由调用方在备战态调起。
  ⚠️ 必须是**定型备战帧**——boss 战后位面过场的半开备战帧点不开详情
  (22:17/22:22 两轮实跑 12 retry 全空证);调用方(battle_loop 接管补采)
  自带 2 次重试账,过场帧首试失败后下个稳定备战帧再试。
- 出口:回备战屏(X 点击后验位面详情 id_mark 消失=真转移);采集结果经
  ``ctx.cw_plane_bosses``/``cw_plane_affixes`` 中转(与 ``cw_briefing_*``
  同模式;消费接线批待做,本 op 只负责采集)。

节点图:两节点,round 语义驱动(同 HandleBriefing 形态):
- ``采集``(start):入口核对(备战→点节点图标开详情 / 已在详情续采;点
  **任意**节点图标都开——不依赖 current 锚,1-7 帧当前槽 V 未过亮门无锚
  实证)→ 三位面循环(点卡→点boss节点→读大图标 SIFT,状态在 self,
  round_wait 自环)→ 三位面齐 → 转 ``关闭``。
- ``关闭``:点 X → 验 id_mark 消失 → 写 ctx 中转 → success。

坐标全走 screen_info area(位面卡×3/boss大图标/词缀横条/关闭/两屏
id_mark/两个节点条);boss 节点圆由 ``read_plane_detail_nodes`` 动态定位
(节点数随位面/投资策略变:位面1=9,位面2/3=7,不硬编码)。
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


#: 详情条节点类型名 area(位面详情屏;boss 定位验证锚)
_LABEL_AREA: str = '文本-节点类型名'


def conclude_plane_boss(label: str | None, sift_name: str | None) -> tuple[str, str | None]:
    """单位面 boss 读取结论(纯函数,W221/ADR-0398 测试锁锚)。

    输入:详情条节点类型名 OCR(``label``)+ boss 大图标 SIFT 结果(``sift_name``)。
    返回 ``(action, value)``:
    - ``('record', boss名)``:标签=首领 且 SIFT 命中 → 头像态(run29 型)真值;
    - ``('skip', None)``:标签=首领 但 SIFT 未命中 → **徽章态**(run30 型:最右
      节点=通用金色徽章,详情条只有「首领节点」+通用描述,本屏无身份信息;
      渲染确定性,重点也不会变)→ 记 None 跳过,不 retry 空转;
    - ``('retry', 原因)``:标签未读出(过渡帧/OCR 失败)或非首领(点到的不是
      boss 节点——节点带误读/布局变的兜底,位置先验失效信号)。
    """
    if not label:
        return 'retry', '详情条类型名未读出(过渡帧/OCR失败)'
    if '首领' not in label.replace(' ', ''):
        return 'retry', f'点到的非首领节点(标签={label}),位置先验失效兜底'
    if sift_name is None:
        return 'skip', None
    return 'record', sift_name


class CollectPlaneIntel(SrOperation):
    """位面详情:一次采集位面情报(三 boss 大图标 SIFT + 词缀横条 + 节点带;
    接管局补采主通道,亦开局校准通用)。"""

    SCREEN_NAME: ClassVar[str] = _PD_SCREEN

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-位面情报采集')
        self._plane_bosses: list[str | None] = [None, None, None]   # 位面1..3
        self._cur_plane: int = 0          # 0-based 当前采集位面索引
        self._affixes: list[str] = []     # 词缀横条(位面详情屏,随 boss 同开读取)

    # ---- 内部工具 -------------------------------------------------------

    def _area_center(self, area_name: str, screen_name: str = _PD_SCREEN) -> Point | None:
        """screen_info area → 中心点(坐标单一源;无 area → None)。"""
        from sr_od.application.currency_war.cw_obs_core import _area_rect
        r = _area_rect(self.ctx, area_name, screen_name)
        if r is None:
            return None
        return Point((r.x1 + r.x2) // 2, (r.y1 + r.y2) // 2)

    def _boss_node_center(self) -> Point | None:
        """当前位面节点条的最右(boss)节点圆心(read_plane_detail_nodes 动态定位)。

        位置先验(最右=首领):run 30 反例帧反而证实——点最右圆详情条显
        「1-9 首领节点」(徽章态身份缺失但**位置仍是首领**,ADR-0398);
        点击后再由详情条标签验证(conclude_plane_boss),先验失效走 retry 兜底。
        """
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
            _log.info('[cw-plane-intel] 位面%d 大图标 SIFT 未命中(拒判保守)',
                      self._cur_plane + 1)
            return None
        name, good = hit
        _log.info('[cw-plane-intel] 位面%d boss=%s(SIFT 好匹配 %d)',
                  self._cur_plane + 1, name, good)
        return name

    # ---- 节点图(round 语义驱动,同 HandleBriefing 形态) -----------------

    @operation_node(name='采集', is_start_node=True, node_max_retry_times=12)
    def collect(self) -> OperationRoundResult:
        """入口核对 + 三位面采集循环(状态在 self;round_wait 自环推进)。

        分支序:①已在位面详情(重跑/续采)→ 采集循环;②备战 → 点当前
        节点图标开详情(round_wait 等开);③其它屏 → retry 等。
        采集循环(每位面):点卡 → 点 boss 节点(最右,位置先验)→ 详情条
        标签验「首领」+ 大图标 SIFT → 头像态命中记录 / 徽章态记 None 跳过 /
        标签异常 retry;三位面齐 → success(转关闭)。
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
                # 点**任意节点图标**都开位面详情(建档实锤;入口不依赖 current
                # 锚——22:09 实跑 1-7 帧当前槽 V 未过亮门无锚,首版依赖 current
                # retry 耗尽失败)。优先 current,无则首个检出圆。
                cur = next((s for s in (slots or []) if s.state == 'current'), None) or (
                    slots[0] if slots else None)
                if cur is None:
                    return self.round_retry('节点条未读出(非clean帧),重读')
                from sr_od.application.currency_war.cw_obs_core import _area_rect
                r = _area_rect(self.ctx, '区域-节点条', _PREP_SCREEN)
                ox, oy = (r.x1, r.y1) if r is not None else (544, 24)
                self.ctx.controller.click(Point(cur.cx + ox, cur.cy + oy))
                time.sleep(1.5)   # MCP click 异步 ~1s + 开屏动画
                return self.round_wait('已点节点图标,等位面详情开')
            return self.round_retry('非备战非位面详情,等画面')

        # —— 在位面详情:采集循环 ——
        # 词缀横条(位面详情屏底部):首位面采集时同帧读一次(词缀不随位面
        # 卡切换变;备战画面无此条,词缀只在简报/位面详情/敌人信息浮层)。
        if not self._affixes and self._cur_plane == 0:
            from sr_od.application.currency_war.cw_briefing_obs import (
                read_detail_affixes,
            )
            self._affixes = read_detail_affixes(self.ctx, screen)
            if self._affixes:
                _log.info('[cw-plane-intel] 词缀随采(位面详情横条):%s', self._affixes)
        if self._cur_plane >= 3:
            _miss = [str(i + 1) for i, b in enumerate(self._plane_bosses) if b is None]
            if _miss:
                _log.info('[cw-plane-intel] 位面%s boss 未取得(徽章态/读取失败),'
                          'boss_fit 对应位面走中性(尽力采披露)', ','.join(_miss))
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
        # ③ 读详情条:类型名标签验「首领」→ 大图标 SIFT → 结论分流(W221/ADR-0398)
        self.screenshot()
        from sr_od.application.currency_war.cw_observation import (
            read_detail_node_type_label,
        )
        label = read_detail_node_type_label(self.ctx, self.last_screenshot)
        name: str | None = None
        if label and '首领' in label.replace(' ', ''):
            name = self._read_boss_big_icon()
            if name is None:
                # 半更新帧防误跳:skip 是终局结论(徽章态恒 None,重试无意义),
                # 但「标签已更新而大图标未换」的过渡帧会把头像态误判 skip →
                # 再截一帧复读一次(零点击成本)仍 miss 才下徽章态结论。
                time.sleep(0.5)
                self.screenshot()
                name = self._read_boss_big_icon()
        action, val = conclude_plane_boss(label, name)
        if action == 'retry':
            return self.round_retry(f'位面{self._cur_plane + 1} {val}')
        if action == 'skip':
            _log.info('[cw-plane-intel] 位面%d 首领节点=徽章态(无头像无名,本屏无身份)'
                      '→ 记 None 跳过,不空转重试(W221/ADR-0398)', self._cur_plane + 1)
        self._plane_bosses[self._cur_plane] = val
        _log.info('[cw-plane-intel] 采集进度:%s', self._plane_bosses)
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
        self.ctx.cw_plane_affixes = list(self._affixes)   # type: ignore[attr-defined]
        _log.info('[cw-plane-intel] 采集完成 plane_bosses=%s affixes=%s(ctx 中转)',
                  self._plane_bosses, self._affixes)
        return self.round_success(f'位面情报采集:boss={self._plane_bosses} 词缀={self._affixes}')
