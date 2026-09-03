"""货币战争 简报 op(W971 P3b:观察收敛单 op,01-opening §1)。

开局序列第一步:简报观察(词缀/敌人难度/三 boss)+ 词缀效果采集(best-effort)
+ 点「下一步」。P3b 起本 op 内联完整现役逻辑(原 ``HandleBriefing`` 退役):
- 观察写局状态 **直写 session**(01-opening §1:替代 ctx 信箱;match 已由
  入口链 ``establish_new_match`` 前移建立,W971 §2.1——session 必在);
- 词缀效果采集仍 best-effort(失败不阻塞点「下一步」,01 §1);
- 完成承诺 = DD-011 形态①固定时长(BRIEFING_SETTLE_S,#1 锚后 ~1s)。

下游链路(不变):session.briefing_affixes → state.enemy_affixes → mechanics_fit;
session.briefing_bosses(位面序真值,ADR-0397)→ state.plane_bosses → boss_fit。
"""
import contextlib
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult

# 日志走框架 logger 'OneDragon'(裸模块 logger 无 handler,日志不可见——W222 先例)。
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.obs.cw_briefing_obs import (
    clean_boss_names_by_lcs,
    load_affix_effects_from_file,
    read_affix_effect,
    read_affixes_with_pos,
    read_bosses,
    read_briefing_enemy_difficulty,
    save_affix_screenshot,
    write_affix_effects,
)
from sr_od.application.currency_war.operations.cw_screen.cw_flow_const import (
    BRIEFING_SETTLE_S,
)
from sr_od.application.currency_war.telemetry import recorder as cw_telemetry
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenBriefing(SrOperation):
    """简报:识别简报 → 读词缀/boss/难度直写 session → 词缀效果采集 → 点下一步(出口验真转移)。"""

    #: screen_info 画面(currency_war_briefing.yml):id_mark 标识-本场对局首领
    #: + 按钮-下一步 + 区域-词缀行 + 区域-首领行。
    SCREEN_NAME: ClassVar[str] = '货币战争-简报'
    MARK_AREA: ClassVar[str] = '标识-本场对局首领'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-简报(开局序列)')

    @operation_node(name='简报', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # ① 识别简报:id_mark「标识-本场对局首领」(简报独有,is_precise)。
        #    非简报屏(接管局/序列中后段首帧分流)→ fail 交编排壳按步分流。
        if not self.round_by_find_area(
                screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success:
            return self.round_fail('非简报屏')
        _match = getattr(self.ctx, 'cw_match', None)
        _session = _match.session if _match is not None else None

        # ② 读敌人词缀(名+center,A8 最高 4)→ session 直写(mechanics_fit 输入)。
        #    词缀幂等:session 已有(重入/retry)不重读,避免重复采效果点击。
        _affixes_pos: list[tuple[str, Point]] = []
        if _session is not None and not _session.briefing_affixes:
            _affixes_pos = read_affixes_with_pos(self.ctx, screen)
            if _affixes_pos:
                _session.briefing_affixes = [n for n, _ in _affixes_pos]
                log.info('简报词缀读得(写 session): %s', _session.briefing_affixes)
                # 词缀效果采集(01-opening §1 随迁职责):每词缀点采 OCR 效果,
                # 与注册表比对,新名/不一致 → 截图 + 写回注册表(best-effort:
                # 失败不阻塞点「下一步」;write_affix_effects 本轮内存不生效,下轮 import 生效)。
                with contextlib.suppress(Exception):
                    _updates = self._collect_affix_effects(dict(_affixes_pos))
                    if _updates:
                        write_affix_effects(_updates)
        # 位面序真值:每次进简报屏都重读覆写(不做「已存跳过」幂等守卫——守卫会把
        # 上一局残留当本局真值;retry 重跑同屏重读成本 = 一次区域 OCR,可接受)。
        # 读得 → LCS 清洗归一(boss_fit 消费端规范名)→ session 直写;读空 → 清 None
        #(防跨局残留假真值)。
        _bosses = read_bosses(self.ctx, screen)
        _cleaned = clean_boss_names_by_lcs(_bosses) if _bosses else None
        if _session is not None:
            _session.briefing_bosses = list(_cleaned) if _cleaned else None
        if _bosses:
            log.info('简报首领读得(位面序,LCS 清洗后,写 session): %s', _cleaned)
        else:
            # 空读也要可见:「read_bosses 恒空」vs「幂等跳过」可区分(W222 先例)。
            log.info('简报首领未读到(read_bosses 空:区域-首领行 OCR 无 4-8 字中文名)')
        # 敌人难度数值(简报「敌人难度N」→ session 直写 → state;3.5.2 接线)。
        if _session is not None and _session.enemy_difficulty is None:
            _diff = read_briefing_enemy_difficulty(self.ctx, screen)
            if _diff is not None:
                _session.enemy_difficulty = _diff
                log.info('简报敌人难度读得(写 session): %s', _diff)

        # 遥测存证(W518):开局简报三读数落 exogenous(kind='briefing',轮次 0 =
        # 简报在 loop 前;口径对齐原 cw_loop 位面简报分支/HandleBriefing 先例)。
        with contextlib.suppress(Exception):   # 遥测 best-effort
            cw_telemetry.record_exogenous(
                0, 'briefing',
                detail=f'affixes={getattr(_session, "briefing_affixes", None)}'
                       f' bosses={getattr(_session, "briefing_bosses", None)}'
                       f' difficulty={getattr(_session, "enemy_difficulty", None)}')

        # ③ 点「下一步」离开简报(下一画面由上层编排/入口链调度)。
        _click = self.round_by_find_and_click_area(
            screen, self.SCREEN_NAME, '按钮-下一步',
            success_wait=2, crop_first=False,
        )
        if not _click.is_success:
            return self.round_retry('未找到「下一步」按钮')
        # ④ 出口验真转移:仍在简报(标识仍命中)= 未转移 → round_retry;已离开 →
        # 固定时长交回(BRIEFING_SETTLE_S,#1 锚后动画完结)。
        if self.round_by_find_area(
                self.screenshot(), self.SCREEN_NAME, self.MARK_AREA,
                crop_first=False).is_success:
            return self.round_retry('点「下一步」后仍在简报屏(点击未生效),重点')
        log.info('[cw-flow-briefing] 已离开简报(观察直写 session 完成)')
        return self.round_success('已离开简报(写局状态完成)', wait=BRIEFING_SETTLE_S)

    def _collect_affix_effects(self, affixes_pos: dict[str, Point]) -> dict[str, str]:
        """固定采集:每词缀点采 OCR 效果 → 跟注册表文件(``affix_effects_data.py`` 最新)比,新名/不一致 → 截图 + 收集(写回注册表)。

        对比目标 = 注册表文件最新(``load_affix_effects_from_file``);没该词缀(新名)
        或效果不一致 → 存 tooltip 截图(``affix_shots/<词缀>.png``)+ 收集;一致 → 跳过。
        tooltip 机制(2026-08-05 实机):点词缀弹效果 tooltip(词缀条上方,切换不关旧)。
        """
        _registered = load_affix_effects_from_file()       # 注册表文件最新(对比目标)
        updates: dict[str, str] = {}
        for name, center in affixes_pos.items():
            self.ctx.controller.click(center)
            time.sleep(1.2)  # MCP click 异步(~1s 落地)+ tooltip 弹出动画
            _shot = self.screenshot()
            _effect = read_affix_effect(self.ctx, _shot, name)
            if not _effect:
                log.info('[cw-briefing] 词缀 %s 效果未采到(OCR 失败)', name)
                continue
            if _effect == _registered.get(name, ''):
                continue  # 注册表有且采到一致 → 跳过(已准,不用对账)
            save_affix_screenshot(_shot, name)             # 存截图(对账,文件名=词缀名)
            updates[name] = _effect
            log.info('[cw-briefing] 词缀 %s 与注册表不一致/新名(注册:%r 采到:%r)→ 截图 + 收集',
                     name, _registered.get(name, ''), _effect)
        return updates
