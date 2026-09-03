"""货币战争 接管补采位面情报 op(独立可调起入口,W280)。

职责:在**接管场景**(对局进行中但 session 无位面序真值——MCP 重启丢内存 /
bot 未走过简报链 / 人工要补)一键完成「进位面详情 → 逐位面采集 → 写
session → 返回」,供 `run_operation` 单独调起,不等 cw_loop 的备战稳定帧
触发(W219 内联块只在 loop 对局轮里跑;重启后 loop 首局 target 重选断档期,
手动通道是唯一入口)。

组装口径(W277 已裁决,.debug/temp/currency_war/w277_plane_detail.md):
以「货币战争-位面详情」屏为唯一组装画面;难度不在此屏补(备战「文本-难度」
有独立现读通道);不用图鉴屏/敌人信息浮层兜底。

复用明细(不重造 reader):采集本体 = :class:`CwScreenPlaneIntel`
(三 boss 大图标 SIFT + 词缀横条 + 徽章态记 None 保位的全部分支逻辑都在它);
本 op 只做四件壳事:①入口门(不在备战/位面详情 → 快速 fail 并存证截图,
不空转 retry 烧预算);②session 真值跳过门(已有 briefing_bosses 不重复采,
零点击);③委派子 op;④结果落 session(briefing_bosses 保位写 3 槽;
briefing_affixes 仅空时写)+ 消费后清 ctx 中转池(防跨局判空泄漏,与
cw_loop 实采块同款收尾)。

写入端语义说明(ADR-0397 勘误节):session.briefing_bosses 的合法写入端两条,
语义同源(都是位面序真值)——①简报读数经 LCS 清洗后由 cw_loop ``__init__`` copy
(用户 2026-08-28 裁决:简报排列=位面序);②本 op / cw_loop 内联块的
CwScreenPlaneIntel 实采(**接管场景内存丢失重采**通道),保位/仅空写词缀/清池口径
逐条一致,由静态锁双面钉死防漂移;实采完成后与简报读数逐位面对账存证。

节点图(两节点,@node_from 显式边——首跑教训见 cw_screen_plane_intel.py 关闭节点):
- ``补采``(start):入口门 → 跳过门 → 委派 CwScreenPlaneIntel。
- ``写回session``:验已离开位面详情 → session 已有真值则不覆写只清池;
  中转池落 session(briefing_bosses 保位写 3 槽 / briefing_affixes 仅空时
  写)→ 清池 → success。池空时按真值两分支给结论(session 有真值=success /
  无=fail),不落任何写。

坐标全走 screen_info area;fixture 验证用 sr-od-test/screens 存档帧离线跑,
不触实机。
"""
import contextlib
import logging
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_log = logging.getLogger(__name__)

#: 位面详情屏 id_mark(cw_screen_plane_intel 同名常量的本地引用,免循环依赖)
_PD_SCREEN: str = '货币战争-位面详情'
_PREP_SCREEN: str = '货币战争-备战'


class CwEntryPlaneIntel(SrOperation):
    """接管补采:进位面详情实采位面情报并写 session(独立调起入口)。"""

    STATUS_DONE: ClassVar[str] = '接管补采完成(session 已落真值)'
    STATUS_SKIP: ClassVar[str] = 'session 已有真值,跳过补采'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-接管补采位面情报')

    def _session(self) -> object | None:
        """当前对局 session(cw_match 为 None = 不在对局中)。"""
        match_ctx = getattr(self.ctx, 'cw_match', None)
        return getattr(match_ctx, 'session', None) if match_ctx is not None else None

    @operation_node(name='补采', is_start_node=True, node_max_retry_times=3)
    def takeover(self) -> OperationRoundResult:
        """入口门 + 跳过门 + 委派 CwScreenPlaneIntel。

        入口契约:必须在备战或位面详情屏(对局中的合法画面);其它屏 =
        调用时机错误(局外/大厅/战斗中),快速 fail 并存证截图——cw_loop
        内联块的「等画面」重试语义属于 loop(有自己的节拍),独立入口空转
        retry 只会烧预算掩盖真实状态。
        """
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

        # 真值已在(cw_loop 早前采过/上一轮本 op 成功)→ 零点击直接结论。
        # 放在屏幕门之后:错屏时先报错屏,别让跳过门吞掉真实状态信号。
        if getattr(sess, 'briefing_bosses', None):
            _log.info('[cw-takeover] %s:%s', self.STATUS_SKIP, sess.briefing_bosses)
            return self.round_success(self.STATUS_SKIP)

        from sr_od.application.currency_war.operations.cw_flow.cw_screen_plane_intel import (
            CwScreenPlaneIntel,
        )
        _log.info('[cw-takeover] session 无位面序真值 → 委派 CwScreenPlaneIntel 实采')
        sub = CwScreenPlaneIntel(self.ctx)
        return self.round_by_op_result(sub.execute(), status='位面详情实采')

    @node_from(from_name='补采')
    @operation_node(name='写回session', node_max_retry_times=6)
    def write_back(self) -> OperationRoundResult:
        """中转池 → session(bosses 保位 3 槽 / affixes 仅空时写)→ 清池 → success。

        池空的两种来路:①跳过门直通(session 本有真值)→ success;
        ②实采成功却无产出(异常形态)→ fail。两种都不改 session——空表覆写
        会把已有真值抹成「无数据」。
        """
        bosses = getattr(self.ctx, 'cw_plane_bosses', None)
        affixes = getattr(self.ctx, 'cw_plane_affixes', None)
        if not bosses:
            sess = self._session()
            if sess is not None and getattr(sess, 'briefing_bosses', None):
                return self.round_success(CwEntryPlaneIntel.STATUS_SKIP)
            return self.round_fail('实采成功但无产出(ctx.cw_plane_bosses 空),不落 session')

        screen = self.screenshot()
        if self.round_by_find_area(screen, _PD_SCREEN, '标识-位面详情标题',
                                   crop_first=False).is_success:
            # CwScreenPlaneIntel 出口契约保证已回备战;仍见详情屏 = 转场未落地
            return self.round_retry('子op称成功但仍在位面详情屏,等转场')

        sess = self._session()
        if sess is None:
            return self.round_fail('写回时 cw_match.session 已消失(对局被清?)')

        # 已有真值保护:session 本有真值(cw_loop 早前采过 / 上一轮本 op
        # 成功)→ 中转池内容再新也只是重复或残留,**不覆写**,只清池。
        # 覆写 = 用陈旧池冲掉真值(W219「唯一写入端」退化成最后一写者赢)。
        if getattr(sess, 'briefing_bosses', None):
            self.ctx.cw_plane_bosses = None
            self.ctx.cw_plane_affixes = None
            _log.info('[cw-takeover] %s:已有真值不覆写,池已清',
                      CwEntryPlaneIntel.STATUS_SKIP)
            return self.round_success(CwEntryPlaneIntel.STATUS_SKIP)

        # 保位写(None=徽章态位面原样占槽,滤掉=后续位面名字左移错序,
        # W221/ADR-0398;与 cw_loop `_names = list(...)` 同口径)
        names = list(bosses)
        sess.briefing_bosses = names
        if affixes and not getattr(sess, 'briefing_affixes', None):
            sess.briefing_affixes = list(affixes)

        # 对账网:实采真值 vs 简报读数逐位面 LCS 比对存证(零决策行为;
        # 门控 config.briefing_reconcile,与 cw_loop 内联块同口径)。
        with contextlib.suppress(Exception):   # 对账 best-effort
            from sr_od.application.currency_war.currency_war_config import (
                CurrencyWarConfig,
            )
            from sr_od.application.currency_war.obs.cw_briefing_obs import (
                reconcile_briefing_vs_plane_intel,
            )
            _gate = CurrencyWarConfig(self.ctx.current_instance_idx).briefing_reconcile
            # 简报读数源 = session(P3b ctx 信箱退役:简报真值唯一写点 =
            # BriefingOp 写 session.briefing_bosses,ctx 槽不再承载)。
            reconcile_briefing_vs_plane_intel(
                getattr(sess, 'briefing_bosses', None), names, enabled=_gate)

        # 取走即清(防跨局残留被下局 `not getattr(ctx,...)` 判空误消费)
        self.ctx.cw_plane_bosses = None
        self.ctx.cw_plane_affixes = None
        _log.info('[cw-takeover] %s:bosses=%s affixes=%s',
                  CwEntryPlaneIntel.STATUS_DONE, names,
                  getattr(sess, 'briefing_affixes', None))
        return self.round_success(f'{CwEntryPlaneIntel.STATUS_DONE}:bosses={names}')
