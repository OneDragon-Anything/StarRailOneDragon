"""货币战争 简报 op(从入口大 op 拆出,一屏一 op)。

简报屏(对局开始前预览):3 位面 boss + 敌人词缀 + 本场对局首领。本 op 职责:
① 识别简报屏(id_mark ``标识-本场对局首领``,简报独有 is_precise);
② 读敌人词缀(``read_affixes``)+ 3 boss 名(``read_bosses``)→ 存 ctx 中转
   (待 loop 建 cw_match 时 copy 到 session);
③ 点「下一步」进投资环境。

词缀/boss 链路(下游):``ctx.cw_briefing_affixes``/``bosses`` → ``session.briefing_affixes``/``bosses``
→ ``state.enemy_affixes``/``bosses`` → ``mechanics_fit``/``boss_fit``
(详 ``cw_observation.read_affixes``/``read_bosses``)。简报在 loop 前(``cw_match=None``),
故词缀/boss 先临时中转 ctx,由 ``battle_loop.__init__`` 取走。

入口大 op(``StartCurrencyWarMatch.advance_to_prep``)只做调度:循环检测当前屏 → 调对应独立 op
(本 op / ``HandleInvestEnv`` 等),兼容新局/恢复局画面顺序不固定。
"""
import logging
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.cw_observation import (
    load_affix_effects_from_file,
    read_affix_effect,
    read_affixes_with_pos,
    read_bosses,
    save_affix_screenshot,
    write_affix_effects,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_log = logging.getLogger(__name__)


class HandleBriefing(SrOperation):
    """简报屏:识别简报 + 读敌人词缀/3 boss + 点下一步进投资环境(一屏一 op)。"""

    # screen_info 画面(currency_war_briefing.yml):id_mark 标识-本场对局首领 + 按钮-下一步
    # + 区域-词缀行 + 区域-首领行(词缀/boss 读取区)。
    SCREEN_NAME: ClassVar[str] = '货币战争-简报'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-简报')

    @operation_node(name='简报', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # ① 识别简报:id_mark「标识-本场对局首领」(简报独有,is_precise)。非简报 → fail。
        _hit = self.round_by_find_area(
            screen, HandleBriefing.SCREEN_NAME, '标识-本场对局首领', crop_first=False,
        ).is_success
        _log.info('[cw-briefing] enter round_by_find_area(标识-本场对局首领)=%s', _hit)
        if not _hit:
            return self.round_fail('非简报屏')

        # ② 读敌人词缀(名+center,A8 最高 4)+ 3 位面 boss 名 → ctx 中转(下游 mechanics_fit/boss_fit 输入)。
        # 幂等:retry 重跑同屏值不变,已存不重读(避免重复 log)。
        if not self.ctx.cw_briefing_affixes:
            _affixes_pos = read_affixes_with_pos(self.ctx, screen)
            if _affixes_pos:
                self.ctx.cw_briefing_affixes = [n for n, _ in _affixes_pos]
                _log.info('简报词缀读得: %s', self.ctx.cw_briefing_affixes)
                # 固定采集:每词缀点采 OCR 效果 → 跟注册表文件(affix_effects_data.py 最新)比,新名/描述不一致
                # → 存 tooltip 截图 + 写回注册表(write_affix_effects;本轮内存不生效,下轮 import 生效)。
                _updates = self._collect_affix_effects(dict(_affixes_pos))
                if _updates and write_affix_effects(_updates):
                    _log.info('[cw-briefing] %d 个词缀(新名/与注册表不一致)已写回注册表: %s',
                              len(_updates), list(_updates))
        if not self.ctx.cw_briefing_bosses:
            _bosses = read_bosses(self.ctx, screen)
            if _bosses:
                self.ctx.cw_briefing_bosses = _bosses
                _log.info('简报首领读得: %s', _bosses)

        # ③ 点「下一步」离开简报(下一画面由上层 advance 调度;新局经位面过场叠层到投资环境)。
        _click = self.round_by_find_and_click_area(
            screen, HandleBriefing.SCREEN_NAME, '按钮-下一步',
            success_wait=2, crop_first=False,
        )
        if not _click.is_success:
            return self.round_retry('未找到「下一步」按钮')
        # ④ 自检状态转移:op 结束以「真的离开简报」为准,非「点了」(点击可能未生效/未输入游戏)。
        # 仍在简报(标识仍命中)= 未转移 → round_retry(重跑本节点:再识别+重点+再验);已离开 → success。
        _screen2 = self.screenshot()
        if self.round_by_find_area(
                _screen2, HandleBriefing.SCREEN_NAME, '标识-本场对局首领', crop_first=False).is_success:
            return self.round_retry('点「下一步」后仍在简报屏(点击未生效),重点')
        _log.info('[cw-briefing] 已离开简报')
        return self.round_success('已离开简报')

    def _collect_affix_effects(self, affixes_pos: dict[str, Point]) -> dict[str, str]:
        """固定采集:每词缀点采 OCR 效果 → 跟注册表文件(``affix_effects_data.py`` 最新)比,新名/不一致 → 截图 + 收集(写回注册表)。

        **对比目标 = 注册表文件最新**(``load_affix_effects_from_file``,跨轮+本轮内都准);下游 mechanics_fit
        用内存 import(本轮旧,**下轮 import 生效**)。注册表文件没该词缀(新名)或有但效果不一致 → 存 tooltip
        截图(``affix_shots/<词缀>.png``,对账回查)+ 收集;一致 → 跳过。``write_affix_effects`` 写回注册表
        (本轮内存不更新,下轮生效)。tooltip 机制(2026-08-05 实机):点词缀弹效果 tooltip(词缀条上方,切换不关旧)。
        """
        _registered = load_affix_effects_from_file()       # 注册表文件最新(对比目标)
        updates: dict[str, str] = {}
        for name, center in affixes_pos.items():
            self.ctx.controller.click(center)
            time.sleep(1.2)  # MCP click 异步(~1s 落地)+ tooltip 弹出动画
            _shot = self.screenshot()
            _effect = read_affix_effect(self.ctx, _shot, name)
            if not _effect:
                _log.info('[cw-briefing] 词缀 %s 效果未采到(tooltip 未弹/OCR 失败)', name)
                continue
            if _effect == _registered.get(name, ''):
                continue  # 注册表有且采到一致 → 跳过(已准,不用对账)
            save_affix_screenshot(_shot, name)             # 存截图(对账,文件名=词缀名)
            updates[name] = _effect
            _log.info('[cw-briefing] 词缀 %s 与注册表不一致/新名(注册:%r 采到:%r)→ 截图 + 收集',
                      name, _registered.get(name, ''), _effect)
        return updates
