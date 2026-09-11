"""货币战争 简报 op(W971 P3b:观察收敛单 op,01-opening §1)。

开局序列第一步:简报观察(词缀/敌人难度/三 boss)+ 词缀效果采集(best-effort)
+ 点「下一步」。P3b 起本 op 内联完整现役逻辑(原 ``HandleBriefing`` 退役):
- 观察写局状态 **直写 session**(01-opening §1:替代 ctx 信箱;match 已由
  入口链 ``establish_new_match`` 前移建立,W971 §2.1——session 必在);
- 词缀效果采集仍 best-effort(失败不阻塞点「下一步」,01 §1);
- 完成承诺 = 固定时长(BRIEFING_SETTLE_S,#1 锚后 ~1s)。

下游链路(不变):session.briefing_affixes → state.enemy_affixes → mechanics_fit;
session.briefing_bosses(位面序真值,ADR-0397)→ state.plane_bosses → boss_fit。

统一观察架构逐屏迁移(账本 T-8 五相位屏;架构设计 §9.1 并存纪律):本类是
CwScreenOpBase 子类,handle 顶部装配点分流(重入裁决**之后**,先例锚 =
cw_screen_encounter.py :241-251 重入裁决 / :252-258 装配点分流;总纲契约 6):
cw_game_ports 两端口完整在场 → 五段生命周期新路径;缺省 None = 生产直连
旧路径(原序列,生产行为零变化)。五段形态:observe = 标识门(miss 未发 →
fail 交编排壳;实机适配器① = 轻观察封口,盛会之星同式);decide+act 内聚
``_read_and_advance``(词缀/ boss / 难度三字段 session 直写 + 词缀效果点采
+ 点「下一步」置位,两路径共享零转录);reconcile/on_outcome = 空申报。
写端保持「session 写 + relay 载体中继」现役形态(相位 1 深度统一 = 不解决
面,总纲 §1)。三字段三种写语义逐字保真:词缀幂等守卫辖「读+采」(session
非空跳过读与点采)/ boss 恒覆写(防跨局残留)/ 敌人难度仅 None 时写。
本屏 sim 腿 = 不适用(F11 例外清单:sim 无对应画面段),等价判据主承重 =
实机在册行为锁 + 写入流对拍(锁面 = sr-od-test
test_cw_obs_arch_phase_screens.py)。
"""
import contextlib
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult

# 日志走框架 logger 'OneDragon'(裸模块 logger 无 handler,日志不可见——W222 先例)。
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
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
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class BriefingObservation:
    """简报观察 payload(五段之段1产物;T-8 实机转录形态)。

    过渡相位屏轻观察(详设 §4):标识门判定在段内(门失败 → round_fail
    早退交编排壳按步分流);payload 仅携带稳定帧引用(三字段读链的同帧
    载体;实机识别域载体,不出端口——sim 适配器落位时该域 = None 帧语义,
    F11 例外清单本批不建)。
    """

    screen: Any = None


class BriefingLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,T-8)。

    轻观察封口(先例 = 盛会之星轻观察适配器):标识门须在段内产出早退轮次,
    归 ``lifecycle_observe``;适配器仅装配稳定帧引用。sim 实现 = 不适用
    (F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenBriefing') -> BriefingObservation:
        return BriefingObservation(screen=op.last_screenshot)


class CwScreenBriefing(CwScreenOpBase):
    """简报:识别简报 → 读词缀/boss/难度直写 session → 词缀效果采集 → 点下一步(出口验真转移)。"""

    #: screen_info 画面(currency_war_briefing.yml):id_mark 标识-本场对局首领
    #: + 按钮-下一步 + 区域-词缀行 + 区域-首领行。
    SCREEN_NAME: ClassVar[str] = '货币战争-简报'
    MARK_AREA: ClassVar[str] = '标识-本场对局首领'

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-简报(开局序列)')
        # 适配器位缺省装配(先例 = CwScreenPrep/CwScreenEncounter):观察口 =
        # 实机适配器(轻观察封口);动作口 = None = 直连现役动作体(基类
        # 「None = 子类缺省实现自担」)。on_outcome 注册表:本屏无登记件
        # (三字段 session 直写 = 观察写端,非动作发射登记;写端切换 =
        # 相位 1 深度统一辖域,本批留守)。
        self._observation_adapter = BriefingLiveObservationAdapter()
        # 「下一步」已发待重入裁决标志(验证废除形态,用户裁定 2026-09-10):
        # 重入裁决见 handle 顶部——标识不在 = 已离开简报(过渡完成)→
        # success 交回编排壳;标识在 = 点击未落地 → 重点(计节点预算)。
        self._click_pending: bool = False

    @operation_node(name='简报', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        _mark_hit = self.round_by_find_area(
            screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success
        # 重入裁决(观察驱动,验证废除形态):上轮「下一步」已发 → 标识不在
        # = 已离开简报 → success 交回;标识在 = 点击未落地 → 重点。两路径
        # 共用(分流前挂,先于五段 lifecycle 的 observe 门;总纲契约 6,
        # 先例锚 cw_screen_encounter.py :241-251/:252-258)。
        if self._click_pending:
            self._click_pending = False
            if not _mark_hit:
                log.info('[cw-flow-briefing] 已离开简报(重入观察裁决,观察直写 session 完成)')
                return self.round_success('已离开简报(重入观察裁决)',
                                          wait=BRIEFING_SETTLE_S)
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run/
        # CwScreenEncounter.handle):两端口完整在场 → 五段生命周期新路径;
        # 缺省 None = 生产直连旧路径(下方原序列,生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        # ① 识别简报:id_mark「标识-本场对局首领」(简报独有,is_precise)。
        #    非简报屏(接管局/序列中后段首帧分流)→ fail 交编排壳按步分流。
        if not _mark_hit:
            return self.round_fail('非简报屏')
        return self._read_and_advance(screen)

    def _read_and_advance(self, screen) -> OperationRoundResult:
        """简报观察 + 推进内聚体(五段 decide+act 两路径共享零转录;旧
        handle :72-124 逐位平移):词缀(幂等守卫辖「读+采」)/ boss(恒
        覆写)/ 敌人难度(仅 None 写)三字段 session 直写 + 词缀效果点采
        + 点「下一步」+ 置位(落地判定归下一轮重入裁决)。"""
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
                # 词缀运行时登记挂点(效果账本 source='affix';与上面读+采同一
                # 幂等守卫辖内——session 已有词缀的重入轮不重登记,登记体自身
                # 再按在册条目幂等兜底)。命中结构化注册(cw_affix_effects
                # .AFFIX_EFFECT_SPECS)才入账本;best-effort 失败不阻塞点
                # 「下一步」(与采集同纪律,登记面纪律=effect-domain.md §7.3)。
                try:
                    from sr_od.application.currency_war.kernel.cw_affix_effects import (
                        register_affixes_from_names,
                    )
                    _reg = register_affixes_from_names(
                        _session, [n for n, _ in _affixes_pos])
                    if _reg:
                        log.info('[cw-briefing] 词缀效果账本登记: %s', _reg)
                except Exception as e:   # noqa: BLE001  登记面失败不阻塞
                    log.warning(f'[cw-briefing] 词缀效果账本登记失败(不阻塞): {e}')
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

        # (开局简报三读数 exogenous 存证行已随 exogenous 流写入端退役删除
        #  ——删除波 1;三读数 session 直写照常,判读面经 journal 开局域。)

        # ③ 点「下一步」离开简报(下一画面由上层编排/入口链调度)。
        _click = self.round_by_find_and_click_area(
            screen, self.SCREEN_NAME, '按钮-下一步',
            success_wait=2, crop_first=False,
        )
        if not _click.is_success:
            return self.round_retry('未找到「下一步」按钮')
        # ④ 机械交回(验证废除:不读屏判「是否已转移」——已离开与否由下一轮
        # 重入的标识观察裁决,裁决 success 的交回等待 = BRIEFING_SETTLE_S,
        # #1 锚后动画完结口径不变)。
        self._click_pending = True
        return self.round_retry('点「下一步」已发,重入观察裁决')

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

    # ---- 五段生命周期(统一观察架构 §5.1;T-8,先例 = CwScreenEncounter)----

    def lifecycle_observe(self
                          ) -> tuple[BriefingObservation,
                                     OperationRoundResult | None]:
        """段1 observe:标识门(id_mark「标识-本场对局首领」;miss 未发 →
        round_fail 早退交编排壳按步分流,旧 handle 首闸逐位转录)→ 轻观察
        payload。重入裁决不在本段(总纲契约 6:留守 handle 分流前共享段)。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else BriefingObservation(screen=self.last_screenshot))
        _mark_hit = self.round_by_find_area(
            self.last_screenshot, self.SCREEN_NAME, self.MARK_AREA,
            crop_first=False).is_success
        if not _mark_hit:
            return obs, self.round_fail('非简报屏')
        return obs, None

    def lifecycle_decision_cycle(self, payload: BriefingObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作决策循环):decide+act 内聚 ``_read_and_advance``
        (三字段 session 写 + 词缀点采 + 点「下一步」,两路径共享零转录);
        on_outcome = 本屏无登记件(注册表缺席 = 零动作,__init__ 申报)。
        轮次终结出口 = 确认机械交回 round_retry(落地判定归下一轮重入裁决,
        验证废除形态)。"""
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        rs = self._read_and_advance(payload.screen)
        self._lifecycle_mark('on_outcome')
        return rs
