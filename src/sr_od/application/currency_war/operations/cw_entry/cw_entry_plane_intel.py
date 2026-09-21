"""货币战争 接管补采位面情报 op(编排单一源,独立可调起入口)。

职责:接管场景(对局进行中但容器无位面序真值——MCP 重启丢内存 /
bot 未走过简报链 / 人工要补)下,一键完成「进位面详情 → 委派实采 →
关闭位面详情」。两条调用路共用本份编排:①CwScreenPrep 观察 node 触发
委派(触发谓词 = 容器无位面真值);②MCP ``run_operation`` 手动调起。

节点图(四 node,@node_from 显式边):
- ``门``(start):对局中(session 在)→ 画面合法(备战/位面详情,其它屏
  = 调用时机错误快速 fail 并存证截图,不空转 retry 烧预算)→ 真值跳过
  (容器已有位面真值 → 零点击直通成功,防手动调起白开白关详情屏;放在
  屏幕门之后,错屏先报错屏,别让跳过门吞掉真实状态信号);
- ``打开位面详情``:已在详情屏直通(委派失败详情屏留场的自愈分支——
  失败后不加专用清理,下一轮再进时跳过打开直接委派);备战屏点当前
  节点图标开详情(点任意节点图标都开,不依赖 current 锚;证据 =
  位面详情标题出现);
- ``委派识别``:CwScreenPlaneIntel 6 node 管线执行,结果透传(失败 =
  本 op round_fail 交调用方失败链,不自旋);
- ``关闭位面详情``:点 X 验标题消失(真转移)→ success。

真值落容器 = 子 op 上报节点的写门(kernel 屏文件唯一一份);本 op 零
容器写。坐标全走 screen_info area;fixture 验证用 sr-od-test/screens
存档帧离线跑,不触实机。
"""
import logging
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_game_state import (
    gs_of_ctx,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_log = logging.getLogger(__name__)

#: 位面详情屏 id_mark(cw_screen_plane_intel 同名常量的本地引用,免循环依赖)
_PD_SCREEN: str = '货币战争-位面详情'
_PREP_SCREEN: str = '货币战争-备战'

# 用户定值等待:备战点节点图标 → 位面详情开屏动画落定(~3s,再由
# 「标题出现」证据判定;不足时走 node 重试账)。
_DETAIL_OPEN_WAIT_S: float = 3.0
_CLOSE_WAIT_S: float = 1.5


#: 真值跳过门的直通终局状态(门节点返回该状态 = 零点击直通成功;
#: 门 → 打开 的边按状态匹配,本状态无出边 → op 以此状态终结)。
_GATE_PASS_STATUS: str = '门通过(session 在、画面合法、无位面真值)'


class CwEntryPlaneIntel(SrOperation):
    """接管补采编排:门 → 打开位面详情 → 委派实采 → 关闭(独立调起入口)。"""

    STATUS_DONE: ClassVar[str] = '接管补采完成(位面真值已落容器)'
    STATUS_SKIP: ClassVar[str] = '容器已有位面真值,跳过补采'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-接管补采位面情报')

    def _session(self) -> object | None:
        """当前对局 session(cw_match 为 None = 不在对局中)。"""
        match_ctx = getattr(self.ctx, 'cw_match', None)
        return getattr(match_ctx, 'session', None) if match_ctx is not None else None

    def _area_center(self, area_name: str, screen_name: str = _PD_SCREEN) -> Point | None:
        """screen_info area → 中心点(坐标单一源;无 area → None)。"""
        from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
        r = _area_rect(self.ctx, area_name, screen_name)
        if r is None:
            return None
        return Point((r.x1 + r.x2) // 2, (r.y1 + r.y2) // 2)

    @operation_node(name='门', is_start_node=True, node_max_retry_times=3)
    def gate(self) -> OperationRoundResult:
        """对局中 → 画面合法 → 真值跳过(三重门,零点击)。"""
        sess = self._session()
        if sess is None:
            self.save_screenshot()
            return self.round_fail('ctx.cw_match 无对局 session(不在对局中),无法补采')

        screen = self.last_screenshot
        in_pd = self.round_by_find_area(
            screen, _PD_SCREEN, '标识-位面详情标题', crop_first=False).is_success
        in_prep = self.round_by_find_area(
            screen, _PREP_SCREEN, '备战标识-购买经验', crop_first=False).is_success
        if not in_pd and not in_prep:
            self.save_screenshot()   # 存证:调用者看 status 即知画面错在哪
            return self.round_fail(
                f'不在货币战争对局画面(需{_PREP_SCREEN}或{_PD_SCREEN}),无法补采')

        # 真值已在(简报链早前采过/上一轮本 op 成功)→ 零点击直接结论。
        if gs_of_ctx(self.ctx, sess).plane_bosses.value:
            _log.info('[cw-takeover] %s:%s', self.STATUS_SKIP,
                      gs_of_ctx(self.ctx, sess).plane_bosses.value)
            return self.round_success(self.STATUS_SKIP)
        return self.round_success(_GATE_PASS_STATUS)

    @node_from(from_name='门', status=_GATE_PASS_STATUS)
    @operation_node(name='打开位面详情', node_max_retry_times=3)
    def open_detail(self) -> OperationRoundResult:
        """已在详情屏直通(留场自愈);备战屏点当前节点图标开详情
        (证据 = 位面详情标题出现)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(
                screen, _PD_SCREEN, '标识-位面详情标题',
                crop_first=False).is_success:
            return self.round_success('已在位面详情屏(留场自愈直通)')

        if not self.round_by_find_area(
                screen, _PREP_SCREEN, '备战标识-购买经验',
                crop_first=False).is_success:
            return self.round_fail(
                f'不在货币战争对局画面(需{_PREP_SCREEN}或{_PD_SCREEN})')
        from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
        from sr_od.application.currency_war.obs.cw_observation import (
            read_node_sequence,
        )
        slots = read_node_sequence(self.ctx, screen)
        cur = next((s for s in (slots or []) if s.state == 'current'), None) or (
            slots[0] if slots else None)
        if cur is None:
            return self.round_retry('备战节点条未读出(半开帧/渲染态),重试')
        r = _area_rect(self.ctx, '区域-节点条', _PREP_SCREEN)
        # 兜底字面量:area 缺失(离线/档案损坏)时的节点条原点(1080p 实测值)
        ox, oy = (r.x1, r.y1) if r is not None else (544, 24)
        self.ctx.controller.click(Point(cur.cx + ox, cur.cy + oy))
        time.sleep(_DETAIL_OPEN_WAIT_S)
        screen = self.screenshot()
        if self.round_by_find_area(
                screen, _PD_SCREEN, '标识-位面详情标题',
                crop_first=False).is_success:
            return self.round_success('位面详情已打开')
        return self.round_retry('点节点图标后位面详情未打开,重试')

    @node_from(from_name='打开位面详情')
    @operation_node(name='委派识别')
    def delegate(self) -> OperationRoundResult:
        """委派 CwScreenPlaneIntel 6 node 管线,结果透传(失败不自旋)。"""
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_plane_intel import (
            CwScreenPlaneIntel,
        )
        return self.round_by_op_result(
            CwScreenPlaneIntel(self.ctx).execute(), status='位面详情实采')

    @node_from(from_name='委派识别')
    @operation_node(name='关闭位面详情', node_max_retry_times=3)
    def close_detail(self) -> OperationRoundResult:
        """点 X 关位面详情(验标题消失 = 真转移)→ success(交回外循环)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, _PD_SCREEN, '标识-位面详情标题',
                crop_first=False).is_success:
            return self.round_success('已不在位面详情屏')
        x = self._area_center('按钮-关闭位面详情')
        if x is None:
            return self.round_fail('关闭按钮 area 缺失')
        self.ctx.controller.click(x)
        time.sleep(_CLOSE_WAIT_S)
        screen = self.screenshot()
        if self.round_by_find_area(
                screen, _PD_SCREEN, '标识-位面详情标题',
                crop_first=False).is_success:
            return self.round_retry('点X未关,重试')
        return self.round_success(CwEntryPlaneIntel.STATUS_DONE)
