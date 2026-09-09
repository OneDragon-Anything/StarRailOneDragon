"""统一观察架构:画面 op 基类(试点步骤 1,实机侧)。

设计正本 = ``docs/develop/currency_war/design/统一观察架构-画面op基类设计.md``
(下称「架构设计」):本类承载 §5 的六段生命周期(observe→reconcile→decide→
act→on_outcome→验证)与 §6.4 的落地登记钩子注册表(带触发时点轴),是
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

on_outcome 触发时点轴(§6.4-R-E):登记件分两型——**落地回执门(默认)**:
applied/progressed 为触发前提,未落地不触发;**发射型(例外,逐件显式
申报)**:点击发射即置位、不等验效,在册成员申报面 = EMIT_TRIGGERED_
DECLARED(新成员入册须先改该表再登记,禁静默选型)。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 触发时点轴·落地回执门(默认):applied/progressed 为触发前提(§6.5-1)。
OUTCOME_TRIGGER_LANDED: str = 'outcome'
#: 触发时点轴·发射型(例外):点击发射即置位、不等验效(§6.5-4)。
OUTCOME_TRIGGER_EMITTED: str = 'emit'

#: 发射型登记件在册申报面(§6.4 触发时点轴;键 = 登记件名,值 = 出处申报)。
#: 在册两件 = 攻击第 1 轮 F-3 裁决口径(架构设计 §6.4-R-E「在册成员两件
#: (F3)」):遭遇刷新计数 + 策略屏逐卡刷新计数,同型同口径「随点击置位
#: 不等验效」。两屏 op 均未迁移(§9.2 迁移序,现子类仅 CwScreenPrep),
#: 先以申报面登记占位;策略屏迁移时其写端(CwScreenInvestStrategy 刷新链)
#: 入本面接线注册,禁静默新增发射型成员。
EMIT_TRIGGERED_DECLARED: dict[str, str] = {
    'encounter_refresh_used': (
        'CwScreenEncounter 刷新链(架构设计 §6.4-R-E 在册两件①;现役语义'
        ' = 「发出点击即置位,防点偏未生效重入屏反复尝试」,证据词'
        ' refresh_click,验效失败帧仍 +1)'),
    'strategy_refresh_used': (
        'CwScreenInvestStrategy 刷新链(架构设计 §6.4-R-E 在册两件②;'
        '逐卡 dict[str,int],策略屏迁移批其写端入本面接线,随点击置位'
        '不等验效)'),
}


@dataclass
class ActionOutcome:
    """动作落地回执(§6.4 钩子契约输入面)。

    - ``action``:触发登记的意图对象(词表成员,§6.1);
    - ``progressed``:落地回执(实机 = 执行器 F3 验证链回执;sim = applied,
      §6.3——规则性拒绝两域同判;sim 批对齐动作端口协议的 ExecResult
      .applied 语义);
    - ``detail``:执行摘要(经验账本等登记件的解析输入);
    - ``evidence``:落地时点证据(发射型 = 点击发射词,如 refresh_click)。
    """

    action: Any
    progressed: bool
    detail: str = ''
    evidence: str = ''


@dataclass
class _OutcomeHook:
    """注册表条目:钩子 + 触发时点型 + 申报名(发射型须入 EMIT_TRIGGERED_\
DECLARED)。"""

    hook: Callable[[ActionOutcome], None]
    trigger: str
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

    意图 → 落地,回执 = ``(progressed, detail)``(落地判定在回执内,是
    on_outcome 的触发前提;sim 批对齐动作端口协议的 ExecResult.applied
    语义,§6.3)。验真锚语义(§6.2)封在实机实现内,不出端口。
    """

    def execute(self, op: CwScreenOpBase, action: Any) -> tuple[bool, str]:
        """执行一个意图并回执落地判定。"""
        ...


class CwScreenOpBase(SrOperation):
    """画面 op 基类:六段生命周期 + on_outcome 落地登记注册表。

    - 六段(§5.1):observe(适配器①)→ reconcile(对账)→ decide(策略
      消费)→ act(适配器②)→ on_outcome(落地登记)→ 验证;单帧段
      (observe/reconcile)每访问一次,decide→act→on_outcome→验证在单动作
      决策循环内逐动作迭代(备战 op 的 visit 语义;期望态两步由 decide/act
      段记预期、下一轮 reconcile 段核对闭环)。
    - 注册表(§6.4):按意图类型登记,基类在动作落地回执点统一触发;
      触发时点轴见模块 docstring。
    - 适配器位:observation_adapter/action_adapter 可注入(构造参数);
      None = 子类缺省(实机适配器,内部复用现役识别链/点击链)。兼容注:
      ``__new__`` 绕道构造的测试桩经 getattr 兜底读位,缺位 = 直连现役链
      (与旧路径同语义,行为面等价)。
    - 段迹:``_lifecycle_trace`` 只增不改,六段各留一字段名(生命周期锁与
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

    # ---- on_outcome 落地登记注册表(§6.4)----

    def register_outcome_hook(self, action_type: type,
                              hook: Callable[[ActionOutcome], None], *,
                              trigger: str = OUTCOME_TRIGGER_LANDED,
                              name: str = '') -> None:
        """登记一个落地登记钩子(按意图具体类型分派)。

        - trigger 缺省 = 落地回执门(progressed 为触发前提);
        - 发射型必须显式传 ``trigger=OUTCOME_TRIGGER_EMITTED`` 且 name 已入
          EMIT_TRIGGERED_DECLARED 申报面(§6.4-R-E:逐件显式申报,禁静默
          选型)——违规登记直接炸错,不静默收下。
        """
        if trigger not in (OUTCOME_TRIGGER_LANDED, OUTCOME_TRIGGER_EMITTED):
            raise ValueError(f'未知触发时点型:{trigger!r}'
                             f'(合法值 = outcome/emit,§6.4 触发时点轴)')
        if trigger == OUTCOME_TRIGGER_EMITTED and name not in EMIT_TRIGGERED_DECLARED:
            raise ValueError(
                f'发射型钩子 {name or action_type.__name__} 未入在册申报面'
                f' EMIT_TRIGGERED_DECLARED(§6.4:发射型逐件显式申报,'
                f'新成员先改申报表再登记;在册 = '
                f'{sorted(EMIT_TRIGGERED_DECLARED)})')
        registry = self._ensure_hook_registry()
        registry.setdefault(action_type, []).append(
            _OutcomeHook(hook=hook, trigger=trigger, name=name))

    def fire_outcome_hooks(self, action: Any, progressed: bool,
                           detail: str = '', *,
                           evidence: str = '') -> int:
        """动作落地时点统一触发(§6.4)。

        落地回执门钩子仅在 ``progressed`` 时触发(未落地不触发,§6.5-1
        语义不变承诺);发射型钩子不经本口(由执行链在点击发射点调
        :meth:`fire_emit_hooks`)。注册表缺席(__new__ 桩形态)或该意图
        未登记 = 零动作。返回触发钩子数(锁/遥测消费)。
        """
        if not progressed:
            return 0
        registry = getattr(self, '_outcome_hooks', None)
        if not registry:
            return 0
        outcome = ActionOutcome(action=action, progressed=True,
                                detail=detail, evidence=evidence)
        fired = 0
        for spec in registry.get(type(action), ()):
            if spec.trigger != OUTCOME_TRIGGER_LANDED:
                continue   # 发射型归 fire_emit_hooks,不在落地回执口混触
            spec.hook(outcome)
            fired += 1
        return fired

    def fire_emit_hooks(self, action: Any, *, evidence: str = '') -> int:
        """发射型钩子触发口(执行链在**点击发射时点**调用;§6.5-4:随点击
        置位不等验效,验效失败不影响该登记)。与落地与否解耦:本口不看
        progressed。返回触发钩子数。"""
        registry = getattr(self, '_outcome_hooks', None)
        if not registry:
            return 0
        outcome = ActionOutcome(action=action, progressed=False,
                                detail='', evidence=evidence or 'emit')
        fired = 0
        for spec in registry.get(type(action), ()):
            if spec.trigger != OUTCOME_TRIGGER_EMITTED:
                continue
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

    # ---- 六段生命周期模板(§5.1)----

    def run_lifecycle(self) -> OperationRoundResult:
        """六段生命周期模板:observe→reconcile→decide→act→on_outcome→验证。

        单帧段(observe/reconcile)每访问一次;后四段在子类的单动作决策
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
        """段迹登记(六段时点轴;只增不改,锁与判读消费)。"""
        trace = getattr(self, '_lifecycle_trace', None)
        if trace is None:
            trace = []
            self._lifecycle_trace = trace
        trace.append(segment)

    # ---- 六段子类钩子(试点步骤 1 由 CwScreenPrep 以现役逻辑实现)----

    def lifecycle_observe(self) -> tuple[Any, OperationRoundResult | None]:
        """段1 observe:适配器①取观察 payload(§5.1)。

        含过渡相位检查位(§3.4:主循环每帧 observe 先查过渡相位表,命中 =
        轻处理交回主循环)。返回 ``(payload, 早退轮次 | None)``;早退非
        None 时后续段不执行。
        """
        raise NotImplementedError('lifecycle_observe 是画面 op 的必实现段'
                                  '(§5.1;适配器①分派)')

    def lifecycle_reconcile(self, payload: Any) -> None:
        """段2 reconcile:对账(§5.1)——payload 写入 BoardState +
        reconcile_pending_observation 核对口 + 入口暂存对账族消费。
        缺省空实现(观察轻的画面无对账面)。"""
        return None

    def lifecycle_decision_cycle(self, payload: Any) -> OperationRoundResult:
        """段3-6:单动作决策循环——decide→act→on_outcome→验证 逐动作迭代。

        迭代语义(终结出口/投影推进/失败恢复)归画面 op 自身(§5.2:
        CwScreenPrep 五段是本生命周期的原型)。
        """
        raise NotImplementedError('lifecycle_decision_cycle 是画面 op 的必实现段'
                                  '(§5.1;段3-6 逐动作迭代)')
