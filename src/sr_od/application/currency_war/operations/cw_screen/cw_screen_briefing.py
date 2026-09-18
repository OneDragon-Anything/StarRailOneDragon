"""货币战争 简报 op(开局序列第一步)。

简报观察(敌人词缀/位面序 boss/敌人难度)+ 词缀效果采集(best-effort)
+ 点「下一步」,完成承诺 = 固定时长(BRIEFING_SETTLE_S,锚后 ~1s)。

下游链路(不变):容器 ``enemy_affixes`` → mechanics_fit;
``plane_bosses``(位面序真值,ADR-0397)→ boss_fit。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation):
观察 node = 画面身份门(id_mark「标识-本场对局首领」,miss = round_fail
交回外循环重判)+ 三读数一次读 → ``report_screen_briefing_obs`` 落容器
(三闸在 report 内:词缀幂等「容器已有不重写」/ boss 恒覆写 / 敌人难度
仅 None 写;match/gs 缺席跳过)→ obs 挂实例属性进决策 node。**词缀效果
点采与效果账本登记留守观察侧**(依赖 OCR 逐词缀点采,摸帧逻辑不进
kernel):幂等门辖「读+采」——容器已有词缀不重读不重采不重登记;
boss 恒重读(不做已存跳过守卫——守卫会把上一局残留当本局真值,retry
重跑同屏重读成本 = 一次区域 OCR,可接受);难度仅容器缺值时读(恒稳
开局基线)。决策动作 node = 重入裁决顶部(「下一步」已发 → 标识不在 =
已离开简报 → success 交回(wait=BRIEFING_SETTLE_S);标识在 = 点击未
落地 → 重点)→ 点「下一步」+ 置位 → round_wait 循环推进(不烧节点重试
预算;不收敛 = 策略实现 bug 响亮暴露,无防御上限)。本屏 sim 腿 = 不
适用(sim 无对应画面段),等价判据主承重 = 实机在册行为锁 + 写入流
对拍(锁面 = sr-od-test test_cw_obs_arch_phase_screens.py)。
"""
import contextlib
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult

# 日志走框架 logger 'OneDragon'(裸模块 logger 无 handler,日志不可见)。
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_screen_report.briefing import (
    CwScreenBriefingObs,
    report_screen_briefing_obs,
)
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
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenBriefing(SrOperation):
    """简报:识别简报 → 读词缀/boss/难度(report 落容器)+ 词缀效果采集 → 点下一步(重入裁决交回)。"""

    #: screen_info 画面(currency_war_briefing.yml):id_mark 标识-本场对局首领
    #: + 按钮-下一步 + 区域-词缀行 + 区域-首领行。
    SCREEN_NAME: ClassVar[str] = '货币战争-简报'
    MARK_AREA: ClassVar[str] = '标识-本场对局首领'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-简报(开局序列)')
        # 「下一步」已发待重入裁决标志:重入裁决住决策动作 node 顶部——
        # 标识不在 = 已离开简报(过渡完成)→ success 交回;标识在 =
        # 点击未落地 → 重点。
        self._click_pending: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费)。
        self._obs: CwScreenBriefingObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """画面身份门 + 三读数一次读 → report 落容器(词缀效果点采/登记留守观察侧)。

        门 miss = round_fail 早退交编排壳按步分流(现役首闸同 status)。
        门 hit → 三读数一次读(同帧同源)→ ``report_screen_briefing_obs``
        落容器(三闸在 report 内)→ obs 挂实例属性。词缀幂等门辖「读+采」:
        容器已有(重入/retry)不重读,避免重复采效果点击;效果点采失败
        不阻塞推进(best-effort;write_affix_effects 本轮内存不生效,
        下轮 import 生效)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, CwScreenBriefing.SCREEN_NAME, CwScreenBriefing.MARK_AREA,
                crop_first=False).is_success:
            return self.round_fail('非简报屏')
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        # 敌人词缀(名+center,mechanics_fit 输入):幂等门辖「读+采」。
        _affixes_pos: list[tuple[str, Point]] = []
        if _gs is not None and not _gs.enemy_affixes.value:
            _affixes_pos = read_affixes_with_pos(self.ctx, screen)
            if _affixes_pos:
                log.info('简报词缀读得(观察): %s', [n for n, _ in _affixes_pos])
                # 词缀效果采集(随迁职责):每词缀点采 OCR 效果,与注册表
                # 比对,新名/不一致 → 截图 + 写回注册表(best-effort)。
                with contextlib.suppress(Exception):
                    _updates = self._collect_affix_effects(dict(_affixes_pos))
                    if _updates:
                        write_affix_effects(_updates)
                # 词缀运行时登记挂点(效果账本 source='affix';与读+采同一
                # 幂等守卫辖内——容器已有词缀的重入轮不重登记,登记体自身
                # 再按在册条目幂等兜底)。命中结构化注册(cw_affix_effects
                # .AFFIX_EFFECT_SPECS)才入账本;best-effort 失败不阻塞点
                # 「下一步」(登记面纪律 = effect-domain.md §7.3)。
                try:
                    from sr_od.application.currency_war.kernel.cw_affix_effects import (
                        register_affixes_from_names,
                    )
                    _reg = register_affixes_from_names(
                        _match.session, [n for n, _ in _affixes_pos])
                    if _reg:
                        log.info('[cw-briefing] 词缀效果账本登记: %s', _reg)
                except Exception as e:   # noqa: BLE001  登记面失败不阻塞
                    log.warning(f'[cw-briefing] 词缀效果账本登记失败(不阻塞): {e}')
        # 位面序真值:每次进简报屏都重读(report 恒覆写,防跨局残留);
        # 读得 → LCS 清洗归一(boss_fit 消费端规范名);读空 → obs 记空
        #(report 写 None,防跨局残留假真值)。
        _bosses = read_bosses(self.ctx, screen)
        _cleaned = clean_boss_names_by_lcs(_bosses) if _bosses else None
        if _bosses:
            log.info('简报首领读得(位面序,LCS 清洗后,观察): %s', _cleaned)
        else:
            # 空读也要可见:「read_bosses 恒空」vs「幂等跳过」可区分。
            log.info('简报首领未读到(read_bosses 空:区域-首领行 OCR 无 4-8 字中文名)')
        # 敌人难度数值(简报「敌人难度N」;恒稳开局基线,容器已有不重读——
        # 逐帧旗牌真读(observation)到达即覆盖)。
        _diff: int | None = None
        if _gs is not None and _gs.enemy_difficulty.value is None:
            _diff = read_briefing_enemy_difficulty(self.ctx, screen)
            if _diff is not None:
                log.info('简报敌人难度读得(观察): %s', _diff)
        obs = CwScreenBriefingObs(
            on_screen=True,
            enemy_affixes=[n for n, _ in _affixes_pos],
            plane_bosses=list(_cleaned) if _cleaned else None,
            enemy_difficulty=_diff,
            screen=screen)
        if _gs is not None:
            report_screen_briefing_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=10)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 点「下一步」+ 置位 → round_wait。

        重入裁决(观察驱动,验证废除形态):上轮「下一步」已发 → 标识不在
        = 已离开简报 → success 交回;标识在 = 点击未落地 → 重点。循环推进
        = round_wait(不烧节点重试预算;不收敛 = 策略实现 bug 响亮暴露,
        无防御上限)。"""
        if self._click_pending:
            self._click_pending = False
            if not self.round_by_find_area(
                    self.last_screenshot, CwScreenBriefing.SCREEN_NAME,
                    CwScreenBriefing.MARK_AREA, crop_first=False).is_success:
                log.info('[cw-flow-briefing] 已离开简报(重入观察裁决,观察直写容器完成)')
                return self.round_success('已离开简报(重入观察裁决)',
                                          wait=BRIEFING_SETTLE_S)
        # 点「下一步」离开简报(下一画面由上层编排/入口链调度)。
        _click = self.round_by_find_and_click_area(
            self.last_screenshot, CwScreenBriefing.SCREEN_NAME, '按钮-下一步',
            success_wait=2, crop_first=False,
        )
        if not _click.is_success:
            return self.round_retry('未找到「下一步」按钮')
        # 机械交回(验证废除:不读屏判「是否已转移」——已离开与否由下一轮
        # 重入的标识观察裁决,裁决 success 的交回等待 = BRIEFING_SETTLE_S,
        # 锚后动画完结口径不变)。
        self._click_pending = True
        return self.round_wait('点「下一步」已发,重入观察裁决')

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
