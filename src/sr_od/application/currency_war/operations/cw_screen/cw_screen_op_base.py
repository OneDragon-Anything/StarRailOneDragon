"""统一观察架构:画面 op 基类(试点步骤 1,实机侧)。

设计正本 = ``docs/develop/sr_od/application/currency_war/design/统一观察架构-画面op基类设计.md``
(下称「架构设计」):本类承载 §5 的五段生命周期(observe→reconcile→
decide→act→on_outcome)与 §6.4 的落地登记钩子注册表(单一发射口),是
「两个适配器 + 一份共用中段」结构(§1.1)的 op 侧机制骨架。

试点范围申报(架构设计 §9.2 迁移步骤 1,实机侧):

- 本文件只含**机制**(生命周期模板/注册表/端口协议位);画面语义(锚/区域/
  交互时序)归实机适配器与子类,策略判据归策略器(§5.3:基类不含策略语义、
  不含画面知识);
- 实机适配器(步骤 1)内部复用现役识别链/点击链,不新建读屏/点击实现
  (§9.2:抽提不重写);
- sim 适配器 = **接口空位**:ScreenObservationPort/ScreenActionPort 协议在
  此,实现归步骤 2(sim 桶);sim 驱动基类的依赖边裁决 = 架构设计 §5.3-F8
  选项③(sim-driver 住 app 根,sim→operations 边不产生);
- 并存纪律(§9.1):装配点(观察/动作端口模块槽 ``observation_source``/
  ``action_sink``,§2.5)缺省 None = 生产直连旧路径(子类 run 原序列),
  生产行为零变化。半装配(单端口在场)申报:分流判据 = 两端口完整在场,
  单端口在场 = 走旧路径——其中观察口单装时旧路径 ``_observe`` 内部分流
  仍消费观察口(「旧决策环 + 端口观察」混合态,行为确定);动作口单装
  时旧路径零消费动作口(纯旧路径)。装配协议强制成对(单装配守卫,卸载
  双清复位,见 ``cw_game_ports`` 安装协议),半装配仅可能经直改模块槽
  发生,生产不可达。等价门(§9.1 主门)通过前双路径并存,旧路径退役归
  等价门通过后的后续批。本文件不消费端口——装配点分流判据的调用点
  留在子类 run 入口(端口消费封闭集守卫的信号面保持干净)。

on_outcome 触发契约(用户终裁 2026-09-10 最严读法,架构设计 §6.4
v12):**单一发射口,发射即触发**——两 fire 口(落地回执门/发射型)合并,
落地回执门(原 OUTCOME_TRIGGER_LANDED 型)退役:发出即职责完成,登记在
发射时点触发;「动作是否落地」的判定完全归观察侧 reconcile 对账(挂起
预期 vs 下一帧实读,失配 → 纠偏/缺陷台账,§6.5-1),动作层不携带成败/落地
信息(端口回执 ``(progressed, detail)`` 与 ``ActionOutcome.progressed``
均退役)。登记件逐件申报面 = ``EMIT_TRIGGERED_DECLARED``(原「选型申报」
随两型制退役,逐件发射语义申报纪律保留:新登记件入册先改申报面)。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 登记件逐件申报面(§6.4;键 = 登记件名,值 = 发射时点/口径出处申报)。
#: 现行契约登记件一律发射型(单一发射口,发射即触发),本面 = 逐件申报
#: 纪律的载体(新成员先改本面再登记,禁静默新增;原「选型闸」语义随两型
#: 制退役)。在册成员:
#: - 遭遇刷新计数 + 策略屏逐卡刷新计数(原 F-3 裁决两件,口径续行):
#:   随点击置位不等验效,选择落地不置位(防点偏未生效重入屏反复尝试)。
EMIT_TRIGGERED_DECLARED: dict[str, str] = {
    'encounter_refresh_used': (
        'CwScreenEncounter 刷新链(架构设计 §6.4-R-E 在册两件①;现役语义'
        ' = 「发出点击即置位,防点偏未生效重入屏反复尝试」,证据词'
        ' refresh_click,验效失败帧仍 +1;试点步骤 2 已接线)'),
    'strategy_refresh_used': (
        'CwScreenInvestStrategy 刷新链(架构设计 §6.4-R-E 在册两件②;'
        '逐卡 dict[str,int],策略屏迁移批其写端入本面接线,随点击置位'
        '不等验效)'),
}


@dataclass
class ActionOutcome:
    """动作发射登记件(§6.4 钩子契约输入面;单一发射口)。

    - ``action``:触发登记的意图对象(词表成员,§6.1);
    - ``detail``:机械执行摘要(经验账本等登记件的解析输入;非成败回执——
      调用方不问成败);
    - ``evidence``:发射时点证据(如 refresh_click)。
    - 原 progressed(落地回执)位已退役删除:登记正确性
      防线 = 发射即登记 + 观察侧 reconcile 对账(§6.5-1)。
    """

    action: Any
    detail: str = ''
    evidence: str = ''


@dataclass
class _OutcomeHook:
    """注册表条目:钩子 + 申报名(登记件须入 EMIT_TRIGGERED_DECLARED)。"""

    hook: Callable[[ActionOutcome], None]
    name: str


class ScreenObservationPort(Protocol):
    """观察适配器端口(架构设计 §2 观察端口契约的 op 侧装配位)。

    实机实现 = 现役识别链封口(识别机制不出端口,契约三则 §2.1);sim
    实现(步骤 2)= 引擎真值映射(§2.4,经 synthesize_from_game_state +
    帧供给双落)。返回值 = 本画面的观察 payload(备战画面 = PrepObservation
    族;共用中段只认类型不认来源)。
    """

    def observe(self, op: CwScreenOpBase) -> Any:
        """取一帧观察 payload(实机 = 识别链;sim = 真值合成)。"""
        ...


class ScreenActionPort(Protocol):
    """动作适配器端口(架构设计 §6 动作端口契约的 op 侧装配位)。

    意图 → 机械执行,**执行无返回**(最严读法:发出即职责完成,
    调用方不问成败;端口回执 ``(progressed, detail)`` 退役)。「是否落地」
    不是适配器的输出,落地判定完全归观察侧 reconcile 对账(挂起预期 vs
    下一帧实读,§6.2/§6.5-1);执行异常仍上抛(框架异常路径,非验证)。
    """

    def execute(self, op: CwScreenOpBase, action: Any) -> None:
        """机械执行一个意图(无返回;落地判定归观察侧)。"""
        ...


class CwScreenOpBase(SrOperation):
    """画面 op 基类:五段生命周期 + on_outcome 落地登记注册表。

    - 五段(§5.1):observe(适配器①)→ reconcile(对账)→ decide(策略
      消费)→ act(适配器②)→ on_outcome(发射登记);单帧段
      (observe/reconcile)每访问一次,decide→act→on_outcome 在单动作
      决策循环内逐动作迭代(备战 op 的 visit 语义;期望态两步由 decide/act
      段记预期、下一轮 reconcile 段核对闭环)。
    - 验证不是生命周期段(用户裁定 2026-09-10):「动作 op 只管机械执行,
      禁止做任何验证,也禁止在画面 op 做验证。如果观察正确,动作 op 没生效,
      那就是动作 op 有 bug,不应该为了 bug 增加验证这种复杂度。」动作未
      生效的处置归动作层本身(修动作适配器的可靠性:点击链坐标/时序/确认
      序列),生命周期不设验证段、不设「验证失败→重试/恢复」分支;落地
      判定完全归观察侧 reconcile 对账(适配器只机械执行,成败/落地
      回执退役,§6.2/§6.5-1)。
    - 注册表(§6.4):按意图类型登记,基类在动作发射点统一触发(单一
      发射口,发射即触发);逐件申报面 = EMIT_TRIGGERED_DECLARED。
    - 适配器位:observation_adapter/action_adapter 可注入(构造参数);
      None = 子类缺省(实机适配器,内部复用现役识别链/点击链)。兼容注:
      ``__new__`` 绕道构造的测试桩经 getattr 兜底读位,缺位 = 直连现役链
      (与旧路径同语义,行为面等价)。
    - 段迹:``_lifecycle_trace`` 只增不改,五段各留一字段名(生命周期锁与
      离线判读消费;旧路径不写迹)。
    """

    def __init__(self, ctx: SrContext, op_name: str, *,
                 observation_adapter: ScreenObservationPort | None = None,
                 action_adapter: ScreenActionPort | None = None) -> None:
        SrOperation.__init__(self, ctx, op_name=op_name)
        # 可注入适配器位(§9.2 迁移步骤 1);None = 子类缺省实机适配器,
        # 在子类 __init__ 装配。
        self._observation_adapter = observation_adapter
        self._action_adapter = action_adapter
        self._outcome_hooks: dict[type, list[_OutcomeHook]] = {}
        self._lifecycle_trace: list[str] = []

    # ---- 适配器位读取(getattr 兜底 = __new__ 测试桩形态兼容)----

    def _observation_port(self) -> ScreenObservationPort | None:
        """观察适配器位;None = 直连现役识别链(子类缺省实现自担)。"""
        return getattr(self, '_observation_adapter', None)

    def _action_port(self) -> ScreenActionPort | None:
        """动作适配器位;None = 直连现役点击链(子类缺省实现自担)。"""
        return getattr(self, '_action_adapter', None)

    # ---- on_outcome 落地登记注册表(§6.4;单一发射口)----

    def register_outcome_hook(self, action_type: type,
                              hook: Callable[[ActionOutcome], None], *,
                              name: str = '') -> None:
        """登记一个发射登记钩子(按意图具体类型分派;单一发射型)。

        - ``name`` 必须已入 ``EMIT_TRIGGERED_DECLARED`` 申报面(§6.4:逐件
          显式申报发射时点/口径,禁静默新增)——未申报登记直接炸错,不
          静默收下。原触发时点轴选型参数(落地门/发射型)已随两型制
          退役:登记件一律发射型,发射即触发。
        """
        if name not in EMIT_TRIGGERED_DECLARED:
            raise ValueError(
                f'登记钩子 {name or action_type.__name__} 未入逐件申报面'
                f' EMIT_TRIGGERED_DECLARED(§6.4:登记件逐件显式申报,'
                f'新成员先改申报表再登记;在册 = '
                f'{sorted(EMIT_TRIGGERED_DECLARED)})')
        registry = self._ensure_hook_registry()
        registry.setdefault(action_type, []).append(
            _OutcomeHook(hook=hook, name=name))

    def fire_outcome_hooks(self, action: Any, detail: str = '', *,
                           evidence: str = '') -> int:
        """动作发射时点统一触发(§6.4;单一发射口,发射即触发)。

        两 fire 口(落地回执门/发射型)合并后的唯一触发口:该意图类型的
        全部登记件在本口发射时点触发,与落地与否解耦(发出即职责
        完成;「未落地不计数」防线由观察侧 reconcile 对账承接,§6.5-1)。
        注册表缺席(__new__ 桩形态)或该意图未登记 = 零动作。返回触发
        钩子数(锁/遥测消费)。
        """
        registry = getattr(self, '_outcome_hooks', None)
        if not registry:
            return 0
        outcome = ActionOutcome(action=action, detail=detail,
                                evidence=evidence)
        fired = 0
        for spec in registry.get(type(action), ()):
            spec.hook(outcome)
            fired += 1
        return fired

    def _ensure_hook_registry(self) -> dict[type, list[_OutcomeHook]]:
        """注册表惰性取存(__new__ 绕道构造的测试桩兼容)。"""
        registry = getattr(self, '_outcome_hooks', None)
        if registry is None:
            registry = {}
            self._outcome_hooks = registry
        return registry

    # ---- 五段生命周期模板(§5.1)----

    def run_lifecycle(self) -> OperationRoundResult:
        """五段生命周期模板:observe→reconcile→decide→act→on_outcome。

        单帧段(observe/reconcile)每访问一次;后三段在子类的单动作决策
        循环内逐动作迭代。早退(观察段交回)时后续段不执行。各段执行经
        :meth:`_lifecycle_mark` 留段迹(只增不改)。
        """
        self._lifecycle_mark('observe')
        payload, early = self.lifecycle_observe()
        if early is not None:
            return early
        self._lifecycle_mark('reconcile')
        self.lifecycle_reconcile(payload)
        return self.lifecycle_decision_cycle(payload)

    def _lifecycle_mark(self, segment: str) -> None:
        """段迹登记(五段时点轴;只增不改,锁与判读消费)。"""
        trace = getattr(self, '_lifecycle_trace', None)
        if trace is None:
            trace = []
            self._lifecycle_trace = trace
        trace.append(segment)

    # ---- 五段子类钩子(试点步骤 1 由 CwScreenPrep 以现役逻辑实现)----

    def lifecycle_observe(self) -> tuple[Any, OperationRoundResult | None]:
        """段1 observe:适配器①取观察 payload(§5.1)。

        含过渡相位检查位(§3.4:主循环每帧 observe 先查过渡相位表,命中 =
        轻处理交回主循环)。返回 ``(payload, 早退轮次 | None)``;早退非
        None 时后续段不执行。
        """
        raise NotImplementedError('lifecycle_observe 是画面 op 的必实现段'
                                  '(§5.1;适配器①分派)')

    def lifecycle_reconcile(self, payload: Any) -> None:
        """段2 reconcile:对账(§5.1)——payload 写入 GameState(观察赢,
        ADR-0651 两态制)+ 入口暂存对账族消费。
        缺省空实现(观察轻的画面无对账面)。"""
        return None

    def lifecycle_decision_cycle(self, payload: Any) -> OperationRoundResult:
        """段3-5:单动作决策循环——decide→act→on_outcome 逐动作迭代。

        迭代语义(终结出口/逻辑态直写推进)归画面 op 自身(§5.2:CwScreenPrep
        五段是本生命周期的原型);动作未生效归动作层处置(修动作适配器,
        §5.1 验证段废除裁定),不在本循环留验证残段。
        """
        raise NotImplementedError('lifecycle_decision_cycle 是画面 op 的必实现段'
                                  '(§5.1;段3-5 逐动作迭代)')
