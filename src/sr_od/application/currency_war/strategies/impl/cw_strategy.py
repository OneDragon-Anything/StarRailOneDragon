"""货币战争 策略插件机制(CwStrategy ABC + StrategySession + CurrencyWarMatch)。

把货币战争的「决策大脑」抽象成**可替换的 ``CwStrategy`` 对象**(对标 app 插件):
换对象 = 换打法,不动框架。唯一注册核 = mandate_v1(注册壳 =
``strategies/mandate_v1_strategy.py``;注册面封闭集依据 = ``flow/README.md`` §2.1)。

设计见 ``docs/develop/currency_war/strategy/07_plugin.md``;决策见
``docs/develop/sr_od/application/currency_war/decisions/INDEX.md`` 。本模块**纯逻辑**:所有钩子只吃
容器 ``GameState``/选项 + 出 ``Action``/``Pick``,**绝不碰屏幕 / ``ctx.controller``**(读屏与点击
是框架职责)→ 策略可离线 unit 测、可 replay。

四个组件(本模块 3 个 + manager):
- ``CwStrategy`` —— ABC,大脑接口(终态契约:构造注入 + 零参入口
  abstract 14,无工厂成员;零策略专属
  语义——方向重估节拍/意向 target 机器是具体策略实现的私事,不在基类契约面上)。
- ``StrategySession`` —— 每局跨步状态(框架新建 / 局终销毁;策略读写)。
- ``CurrencyWarMatch`` —— 运行时持有 strategy+session 的轻容器,挂 ``ctx.cw_match``。
- ``StrategyManager``(``cw_strategy_manager.py``)—— 约定式文件扫描发现 + 去重 + 实例化。
"""
from __future__ import annotations

import contextlib
import functools
import random
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_decision_ctx import (
    reset_decision_tag,
    set_decision_tag,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import StrategySession
from sr_od.application.currency_war.kernel.cw_vocab import (
    Action,
    CwActionObsParam,
    CwActionPickBoxCardParam,
    CwActionPickEncounterParam,
    CwActionPickExpertInviteParam,
    CwActionPickFortuneParam,
    CwActionPickInvestEnvParam,
    CwActionPickInvestStrategyParam,
    CwActionPickMegastarParam,
    CwActionPickPartnerParam,
    CwActionPickPlannerParam,
    CwActionPickStarTomeParam,
    CwActionPickSupplyParam,
    CwActionPickWishTrialParam,
    CwActionRefreshInvestCardsParam,
    CwActionRefreshNodeOptionsParam,
    CwActionRefreshSupplyParam,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_vocab import CwAction
    from sr_od.context.sr_context import SrContext

# 注解中的 ``CurrencyWarConfig`` 刻意不 import 真类型:config 属 app 层,本模块
# 归 strategies 包实现层,与 cw_strategy_manager 同层(策略统一迁移批二勘误落位:接口是
# ops/sim/impl 三方共享契约,非实现本体;本模块禁依 app 层);config 实例由调用方按参
# 注入,下面绑定只是注解名的文档性占位(字符串;「刻意字符串注解」先例 =
# 期 0b kernel/cw_strategy_session 的 SrContext 处理)。
CurrencyWarConfig = 'CurrencyWarConfig'

#: 策略器私有状态的泛型参数(设计正本 §1/§8.5/§8.6-6「下沉
#: 策略实现层」):StrategyState 归**策略实现层私有**,框架策略器基类仅以
#: 泛型参数携带(本 ABC = 设计所称「策略器基类」,``BaseStrategy[TState]``
#: 形态的落位),框架(kernel/one_dragon)不感知具体类型、零 import 具体
#: 类——具体绑定由各策略实现在自己的类声明上完成(内置 =
#: ``strategies/impl/mandate_v1/mandate_state.StrategyState``,经
#: CwFlowStrategy 链绑定)。布局守卫 = sr-od-test 布局/泛型约束测试。
_TState = TypeVar('_TState')


# ===== 策略遥测捕获缝(capture-store §1;信封契约 = design.md §2)=====

#: 决策入口显式闭集(14 个;包裹面唯一依据,禁名称前缀通配——前缀规则会把
#: ``decide_shop_screen`` 序列驱动器(返回 list)卷入「恰一动作」信封语义,
#: 且无法从名字区分生产/非生产面)。闭集 = 本模块抽象入口全集。
DECISION_ENTRY_NAMES: frozenset[str] = frozenset({
    'decide_prep_screen', 'decide_shop_action', 'decide_invest_strategy',
    'decide_invest_env', 'decide_supply', 'decide_encounter', 'decide_megastar',
    'decide_partner', 'decide_planner', 'decide_star_tome', 'decide_wish_trial',
    'decide_box_card', 'decide_fortune', 'decide_expert_invite',
})

#: DecisionRecord 行格式版本(envelope.schema_version;信封键闭集演进时递增)。
DECISION_RECORD_SCHEMA_VERSION: int = 1


def _node_envelope(gs: GameState | None) -> dict[str, Any] | None:
    """gs.node 现读 → 信封 node 键值 ``{plane, round_num, kind}``;
    缺(未观察/无容器)= None(null 帧,渲染侧不入章级挂载)。"""
    node = getattr(gs, 'node', None)
    value = getattr(node, 'value', None)
    if value is None:
        return None
    # 归因键一律 getattr 容缺(桩形态 NodeKey 无属性不抛、不丢记录)。
    return {
        'plane': getattr(value, 'plane', None),
        'round_num': getattr(value, 'round_num', None),
        'kind': getattr(value, 'kind', None),
    }


def _wrap_decision_entry(fn: Callable[..., Any]) -> Callable[..., Any]:
    """单决策入口包裹(捕获缝本体;语义 = capture-store §1/§2):

    in-flight 守卫(super() 复用基类实现的内层直通,嵌套归属 = 最外层
    一条)→ dseq 自增 → 原方法 → 信封 + payload 钩子 + sink 落盘
    (全 best-effort,遥测故障不毒化决策返回值)→ kernel 槽操作
    (空动作清槽防陈旧 dtag / 非空动作盖 dtag 供回执读取)→ 原样返回。
    决策入口抛异常的帧不落记录(异常照常上抛;异常面已有各自留证通道)。
    """

    @functools.wraps(fn)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        if getattr(self, '_decision_in_flight', False):
            return fn(self, *args, **kwargs)   # super() 嵌套内层:直通不记录
        self._decision_in_flight = True
        try:
            self._dseq_counter += 1   # 自增先于调用(构造清零;实例不跨局 → 按局天然清零)
            dseq: int = self._dseq_counter
            dtag = f'{self.STRATEGY_ID}:{dseq}'
            result = fn(self, *args, **kwargs)
            # payload 钩子异常降级 {}(capture-store §3;信封构造为容缺
            # 读取、不可抛,不与之合并守卫面)。
            try:
                payload = self.decision_payload()
            except Exception as e:  # noqa: BLE001  载荷故障降级,不毒化决策
                payload = {}
                log.debug(f'[cw-strategy] decision_payload skip: {e}')
            envelope = {
                'strategy_id': self.STRATEGY_ID,
                'schema_version': DECISION_RECORD_SCHEMA_VERSION,
                'dseq': dseq,
                'dtag': dtag,
                'entry': fn.__name__,
                'node': _node_envelope(self.gs),
                'ts': datetime.now().isoformat(timespec='seconds'),
                'emitted': [{
                    'op': type(result).__name__,
                    'reason': getattr(result, 'reason', ''),
                    'route_tag': getattr(result, 'route_tag', ''),
                }],
            }   # 键闭集不含 run_id——run_id 归 sink 落盘前补齐(策略包禁依 telemetry)
            sink = _DECISION_SINK
            if sink is not None:
                try:
                    sink({'envelope': envelope, 'payload': payload})
                except Exception as e:  # noqa: BLE001  记录层故障不毒化决策
                    log.debug(f'[cw-strategy] decision sink skip: {e}')
            try:
                if isinstance(result, CwActionObsParam):
                    # 空动作(两 scope 均不产回执)→ 主动清槽,防陈旧 dtag。
                    reset_decision_tag()
                else:
                    set_decision_tag(dtag)
            except Exception as e:  # noqa: BLE001  槽故障不毒化决策
                log.debug(f'[cw-strategy] decision tag slot skip: {e}')
            return result
        finally:
            self._decision_in_flight = False

    wrapper._decision_recorded = True   # 防双包标记(__init_subclass__ 检查)
    return wrapper


class CwStrategy(ABC, Generic[_TState]):
    """一整套货币战争局内打法(可替换的决策大脑;终态契约:构造注入 + 零参入口)。

    **终态契约**(2026-09-16-strategy-terminal-contract;用户裁定干净断不留壳):
    - **构造注入**:每局冷建 ``Strategy(gs, config)``——``self.gs`` 当局容器
      单例只读引用、``self.config`` 按参注入、``self.state`` 策略器私有状态
      实例(缺省 None,子类覆写 :meth:`_create_state` 定制)、``self.rng``
      (``config.strategy_seed`` None → 0 固定种子,禁静默翻转为熵种子)。
      构造即唯一冷建口;``create_session``/``create_state`` 工厂停用。
    - **实例不跨局**:局容器弃置 = 实例连带回收(引导漏斗每局 instantiate);
      异常路径残留容器弃置守卫(:func:`discard_stale_match_container`)保留。
    - **零参入口 14**:备战/商店/invest 双相/pick 族八屏 + 契约扩员两屏
      (命运卜者强化/专家邀请函;三 overlay 选卡判据扩员,原选择装备口
      已删除(随该屏误判修正))——决策输入一律
      ``self.gs`` 自取,会话残余依赖
      由 §3.2/§3.3 重复账治理偿还。
    - **输出统一**:单一 ``CwAction``(选择族 per-screen 子类型 + 三刷新动作
      + 重观察 CwActionObsParam(scope='in_place' 环内 / 'outer_loop' 结束本次访问,
      后者承载原 HoldFrame 空动作发出语义),无 None)。

    兼容裁定:注册面封闭集 {mandate_v1},第三方存量策略在新契约下不兼容 =
    显式破坏申报(flow/README §2.4)。
    """

    # ===== 元数据(类属性;扫描时读,无 _const.py sidecar —— 策略比应用简单)=====
    STRATEGY_ID: str = ""        # 唯一 id(如 "default"/"aggressive_rush"),去重键;空 = 中间辅助 ABC 不注册
    STRATEGY_NAME: str = ""      # GUI 显示名(如 "内置默认策略")
    AUTHOR: str = ""             # 参赛者/作者
    VERSION: str = "0.1"         # 语义化版本
    DESCRIPTION: str = ""        # 一句话描述打法
    # 扫描器内部:True = 中间辅助 ABC,不注册;非展示元数据(§11.5)
    _abstract: bool = False

    def __init_subclass__(cls, **kwargs) -> None:
        """子类创建时对显式闭集内、**定义于本类**的入口包记录 wrapper
        (捕获缝挂载点,结构上不可漏报——不靠实现自觉调用)。

        - 只包本类 `__dict__` 里的实现:基类 ``@abstractmethod`` 声明不包
          (包裹只发生在具体实现类);继承所得(已包过)不再进本类 dict。
        - 带 ``_decision_recorded`` 标记不包(防双包);abstract 重声明不包
          (无实现可记录)。
        """
        super().__init_subclass__(**kwargs)
        for name in DECISION_ENTRY_NAMES:
            fn = cls.__dict__.get(name)
            if (not callable(fn)
                    or getattr(fn, '_decision_recorded', False)
                    or getattr(fn, '__isabstractmethod__', False)):
                continue
            setattr(cls, name, _wrap_decision_entry(fn))

    # ===== 构造注入(唯一冷建口;终态契约 §2.1)=====

    def __init__(self, gs: GameState, config: CurrencyWarConfig) -> None:
        """每局冷建(引导漏斗 ``cls(gs, config)`` 调用;实例不跨局)。

        ``self.state`` 经 :meth:`_create_state` 工厂冷建(缺省 None;子类
        覆写定制私有状态类型)。rng:``strategy_seed`` None → 0 固定种子
        (None→0 语义保持现状,禁静默翻转为熵种子)。
        """
        self.gs = gs
        self.config = config
        self.state = self._create_state()   # 经下方 setter 同源接线 gs 宿主
        seed = getattr(config, 'strategy_seed', None)
        self.rng = random.Random(seed if seed is not None else 0)
        # 捕获缝实例态(capture-store §1):dseq = 决策序号(信封 dtag 基数,
        # 按局清零——实例不跨局);in-flight 旗 = super() 嵌套链内层直通守卫。
        self._dseq_counter: int = 0
        self._decision_in_flight: bool = False

    @property
    def state(self) -> _TState | None:
        """策略器私有状态(实例属性;终态契约 §2.4「strategy_state → 实例」)。

        setter 同步 ``gs.strategy_state`` 宿主接线:零参 decide 管线
        (mandate 三遍编排)以 self.gs 为宿主传递,``state_of(gs)`` 经本
        接线解析到**同一**状态对象、``game_state_of(gs)`` 本体直通——
        单一来源两处引用,禁第二状态对象(构造/事后重赋值两路径都过
        setter,不变量恒成立)。
        """
        return self._state

    @state.setter
    def state(self, value: _TState | None) -> None:
        self._state = value
        with contextlib.suppress(AttributeError):
            # 容器为桩面(不可附着)→ 跳过;legacy session 形态仍可用。
            self.gs.strategy_state = value

    def _create_state(self) -> _TState | None:
        """策略器私有状态工厂钩子(缺省 None;子类覆写返回其私有状态类型,
        基类不感知具体字段)。生命周期 = 一局(实例不跨局 → 状态天然隔离)。"""
        return None

    def decision_payload(self) -> dict:
        """决策载荷钩子(捕获缝出口收载荷;缺省 {} = 零载荷,子类覆写)。

        wrapper 在原方法返回后调用,异常降级 {}(capture-store §3)。
        载荷只许「出口后 gs/state 现读」,禁依赖决策入口内部局部量
        (更细域内量由策略经私有 state 槽自存、钩子里读)。
        """
        return {}

    # ===== 分画面决策入口(目标模型:op 的策略接触面 = 入口观察
    #       + 策略器单动作循环;入口按画面塑形,方向重估时机是实现私事)=====

    @abstractmethod
    def decide_prep_screen(self) -> CwAction:
        """备战画面黑板决策(单动作,None 停用;空动作发出 = CwActionObsParam
        scope='outer_loop' 返回主循环重新观察——原 HoldFrame 并入,用户裁定
        2026-09-20;环内重观察 = scope='in_place',宿主观察链重跑后原地
        续决策,不返回主循环)。"""

    @abstractmethod
    def decide_shop_action(self) -> Action:
        """商店单动作决策(恒可用终结 = CwActionCloseShopParam,恒不 None)。观察帧缺失 =
        观察层失约,实现须抛错(禁静默按空态决策)。"""

    @abstractmethod
    def decide_invest_strategy(self) -> CwActionPickInvestStrategyParam | CwActionRefreshInvestCardsParam:
        """投资策略 3 选 1(原 decide_invest 双相拆分;候选读
        ``gs.invest_strategy_opts`` 槽,离屏 None = 观察层失约抛错)。
        刷新建议 = CwActionRefreshInvestCardsParam 动作(候选卡逐卡槽位);选卡 =
        CwActionPickInvestStrategyParam(两型互斥输出;词表按屏拆类,
        投资两屏迁移批)。"""

    @abstractmethod
    def decide_invest_env(self) -> CwActionPickInvestEnvParam | CwActionRefreshInvestCardsParam:
        """投资环境 3 选 1(选卡 = CwActionPickInvestEnvParam,屏别独立
        词表类;候选读 ``gs.invest_env_opts`` 槽;刷新建议 =
        CwActionRefreshInvestCardsParam 整组槽)。"""

    @abstractmethod
    def decide_supply(self) -> CwActionPickSupplyParam | CwActionRefreshSupplyParam:
        """补给选装备(候选读 ``gs.supply`` payload 槽;刷新建议 =
        CwActionRefreshSupplyParam 动作,非布尔位)。"""

    @abstractmethod
    def decide_encounter(self) -> CwActionPickEncounterParam | CwActionRefreshNodeOptionsParam:
        """遭遇选档(候选读 ``gs.encounter`` payload 槽;判据单一源 =
        策略层 ``mandate_v1/encounter_pick.decide``;刷新建议 =
        CwActionRefreshNodeOptionsParam 动作,非布尔位)。"""

    @abstractmethod
    def decide_megastar(self) -> CwActionPickMegastarParam:
        """巨星选候选(候选读 ``gs.megastar_opts`` 槽)。"""

    @abstractmethod
    def decide_partner(self) -> CwActionPickPartnerParam:
        """选择伙伴(候选读 ``gs.partner_opts`` 槽)。"""

    @abstractmethod
    def decide_planner(self) -> CwActionPickPlannerParam:
        """银狼策划事件 3 选 1(候选读 ``gs.planner_opts`` 槽)。"""

    @abstractmethod
    def decide_star_tome(self) -> CwActionPickStarTomeParam:
        """星徽秘典四选一(候选读 ``gs.star_tome_opts`` 槽;返回动作子类型,
        handler 翻译既有点击链)。"""

    @abstractmethod
    def decide_wish_trial(self) -> CwActionPickWishTrialParam:
        """祈愿试炼选卡(候选读 ``gs.wish_trial_opts`` 槽;返回动作子类型)。"""

    @abstractmethod
    def decide_box_card(self) -> CwActionPickBoxCardParam:
        """武装箱/节点弹窗装备卡 4 选 1(候选读 ``gs.box_card_names`` 槽;
        返回动作子类型)。"""

    # —— 契约扩员区(三 overlay 选卡判据并入 kernel + handler
    #    改写槽→零参 decide;事件面登记 =
    #    strategy-docs/13_pick_family.md §2 E16-E18)——

    @abstractmethod
    def decide_fortune(self) -> CwActionPickFortuneParam:
        """命运卜者强化三选一(候选读 ``gs.fortune_opts`` 槽,OCR 卡文;
        返回动作子类型)。"""

    @abstractmethod
    def decide_expert_invite(self) -> CwActionPickExpertInviteParam:
        """专家邀请函选卡(候选读 ``gs.expert_invite`` 弹窗载体槽;
        idx = -1 表现金为王,值域扩展见 CwActionPickExpertInviteParam 注)。"""


@dataclass
class CurrencyWarMatch:
    """运行时持有 strategy + session 的轻容器,挂 ``ctx.cw_match``(子 op 都拿得到 ``self.ctx``)。

    生命周期:``CwLoop.__init__`` 每局创建 → 挂 ctx → 每个契约调用点收到的 session 就是它 →
    局终置 ``ctx.cw_match = None``(防跨局污染)。

    ``gs``/``performance`` = 终态契约前置落位(landing §3.1):容器正身挂
    Match(策略器终态改持只读引用,ops 取容器 = 「取当局事实」语义)、
    观测统计归框架侧。本批 additive 填充——消费接线归终态切换批,
    现役读面仍走 session 旁口。
    """
    strategy: CwStrategy
    session: StrategySession
    gs: GameState | None = None   # 终态契约:当局容器正身(3.1 additive 缺省
                                  # None=迁移期测试/防御路径旧构造容忍;
                                  # 3.5 终态切换收紧必填,生产漏斗已填充)
    performance: object | None = None

    def __post_init__(self) -> None:
        # 策略器状态兜底附着:策略未覆写 create_session(直用裸 session)
        # 而状态工厂已注册(mandate_v1 在场)→ 附着当局状态对象。恢复局
        # 冷启动契约(session.md §3.2)不变——附着的是**新建**状态对象;
        # 第三方策略无工厂注册 → 保持 None(其策略器沿用惰性建模式)。
        from sr_od.application.currency_war.kernel.cw_strategy_session import (
            ensure_strategy_state_attached,
        )
        ensure_strategy_state_attached(self.session)


#: obs 读口注入槽(缺省关):清 obs 模块级 last-known-good 缓存的回调。
#: 分包依赖矩阵禁 decision→obs 直依,生产装配点 = app/decision_assembly
#: ``install_obs_ports()``(CurrencyWarApp.__init__ 接通);未注入 = 跳过
#: 缓存清理(容器弃置语义不受影响,session 全量重建承担状态隔离)。
_RESET_PHASE_ROUND_CACHE: Callable[[], None] | None = None


def set_obs_reset_hook(reset_phase_round_cache: Callable[[], None]) -> None:
    """装配点注入 obs 缓存清理回调(幂等,可重复调用覆盖)。"""
    global _RESET_PHASE_ROUND_CACHE
    _RESET_PHASE_ROUND_CACHE = reset_phase_round_cache


#: 策略遥测 sink 注入槽(缺省 None = 零写,纯单测零副作用):决策信封
#: 落盘回调(实现住 telemetry/strategy_telemetry,写盘与 run_id 供给都
#: 归彼处——策略包禁 import telemetry,槽位与写盘分离,capture-store §4)。
#: 生产装配点 = app/decision_assembly ``install_obs_ports()`` 同位;
#: sim 侧注入 = cw_sim_match_drive 装配段(recorder 重定向同段)。
_DECISION_SINK: Callable[[dict], None] | None = None


def set_decision_sink(fn: Callable[[dict], None] | None) -> None:
    """装配点注入决策信封落盘回调(None = 关,幂等可重复覆盖)。"""
    global _DECISION_SINK
    _DECISION_SINK = fn


def discard_stale_match_container(ctx: SrContext, reason: str) -> bool:
    """上一局残留的 match 容器在**新局开始信号**处丢弃(迁移审计)。

    背景(迁移审计抽样判读):正常流程局终回大厅会置 ``ctx.cw_match = None``(cw_loop
    分支 3c),下一局 ``RunLoop.handle_init`` 见 None 新建 session —— 状态天然全新。但
    **异常路径**(run 被停机/崩溃在上局对局中、进程未重启)残留非 None 的旧容器;此时
    下一次入口链 ``CwEntryStart`` 开的是一局**新对局**,而
    ``handle_init`` 的续跑判定(``ctx.cw_match is None``)会把旧 session 整体延用:
    level 单调守卫拿上局 ``last_level_obs=5`` 打新局 plane1 的真读(迁移审计cap_vs_level
    抽样 4/4 实证)、tracked 角色/streak/hp 对账锚全部跨局带毒——obs_conflict 三层
    (level/cap_vs_level/phase_round)329 张的残留源。

    本函数只在「确凿是新一局」的调用点用(难度确认/模式选择/简报三屏只在无保存局的
    新局路径出现;「继续进度」恢复同一物理局不触发)→ 把容器置 None,随后的
    handle_init 走新建分支实现**全量重置 by construction**(StrategySession 每字段
    回默认值,不存在漏清字段面);模块级观测缓存(plane/round last-known-good)由
    handle_init 既有的 ``reset_phase_round_cache()`` 清。

    Returns: True = 发现已弃置(本局起为全新 session);False = 无残留(幂等直过)。
    """
    if getattr(ctx, 'cw_match', None) is None:
        return False
    from one_dragon.utils.log_utils import log as _log
    _log.warning('[cw-entry] 检测到上一局残留 match 容器(%s)→ 弃置,'
                 '本局 session 全量重建', reason)
    ctx.cw_match = None
    if _RESET_PHASE_ROUND_CACHE is not None:
        _RESET_PHASE_ROUND_CACHE()
    return True


# gated_hp(结算 HP 新鲜度门薄委托)已删除;现役消费点 =
# kernel/cw_hp_policy.decision_hp(gs 直读);
# prep 环入口/终饰写侧预施门已删除(该文件残留注释为历史锚)。

