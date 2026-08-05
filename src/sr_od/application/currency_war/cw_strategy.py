"""货币战争 策略插件机制(CwStrategy ABC + StrategySession + CurrencyWarMatch)。

把货币战争的「决策大脑」抽象成**可替换的 ``CwStrategy`` 对象**(对标 app 插件):
换对象 = 换打法,不动框架。内置具现 ``DefaultCwStrategy``(``strategies/default_strategy.py``)
= 今天打法(薄委托既有模块函数,P1 零行为变化)。

设计见 ``docs/game/currency_war/strategy/11_strategy_plugin.md``;决策见
``docs/game/currency_war/decisions.md`` D-34。本模块**纯逻辑**:所有钩子只吃
``GameState``/选项 + 出 ``Action``/``Pick``,**绝不碰屏幕 / ``ctx.controller``**(读屏与点击
是框架职责)→ 策略可离线 unit 测、可 replay。

四个组件(本模块 3 个 + manager):
- ``CwStrategy`` —— ABC,大脑接口(3 生命周期 + 8 决策 + create_session = 12 钩子,全 abstract)。
- ``StrategySession`` —— 每局跨步状态(框架新建 / 局终销毁;策略读写)。
- ``CurrencyWarMatch`` —— 运行时持有 strategy+session 的轻容器,挂 ``ctx.cw_match``。
- ``StrategyManager``(``cw_strategy_manager.py``)—— 约定式文件扫描发现 + 去重 + 实例化。
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from sr_od.application.currency_war.cw_decisions import (
    EncounterOption,
    EncounterPick,
    MegastarOption,
    MegastarPick,
    PartnerOption,
    PartnerPick,
    SupplyOption,
    SupplyPick,
)
from sr_od.application.currency_war.cw_performance import (
    PerformanceTracker,
    RoundOutcome,
)
from sr_od.application.currency_war.cw_state import (
    Action,
    GameState,
    MatchOutcome,
    PickEvent,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
    from sr_od.application.currency_war.cw_comps import Comp


class CwStrategy(ABC):
    """一整套货币战争局内打法(可替换的决策大脑;D-34/§11.3)。

    **无状态策略**:实例**不持有可变的每局状态**,所有跨步状态走 ``StrategySession``(框架每局
    新建、传入每个钩子、局终销毁)。收益:实例可反复 instantiate、可 unit 测(喂构造好的 state)、
    无隐藏实例状态 → 不会跨局泄漏。

    本 ABC 的钩子**全 abstract**(纯接口,ABC 自身不含内置逻辑);内置具现见 ``DefaultCwStrategy``。
    自定义策略两条路:① 继承 ``CwStrategy`` 自己实现全部钩子(完整自研打法);② 继承
    ``DefaultCwStrategy`` 只覆盖关心的几个(其余继承内置,低门槛、比赛友好)。

    **构造无参**(继承默认 ``object.__init__``):策略跨局跨账号复用,**不收 ctx/config** —— 配置每次
    调用按参传入;``StrategyManager`` 经 ``cls()`` 实例化。可变每局状态一律走 ``session``,非实例属性。
    """

    # ===== 元数据(类属性;扫描时读,无 _const.py sidecar —— 策略比应用简单)=====
    STRATEGY_ID: str = ""        # 唯一 id(如 "default"/"aggressive_rush"),去重键;空 = 中间辅助 ABC 不注册
    STRATEGY_NAME: str = ""      # GUI 显示名(如 "内置默认策略")
    AUTHOR: str = ""             # 参赛者/作者
    VERSION: str = "0.1"         # 语义化版本
    DESCRIPTION: str = ""        # 一句话描述打法
    # 扫描器内部:True = 中间辅助 ABC(如 RushBase(DefaultCwStrategy)),不注册;非展示元数据(§11.5)
    _abstract: bool = False

    # ===== 生命周期钩子 =====

    @abstractmethod
    def create_session(self, config: CurrencyWarConfig) -> StrategySession:
        """每局开始(run loop)调一次。返回空白 ``StrategySession``(rng 留默认,由 run loop 按
        ``config.strategy_seed`` 覆盖)。策略可覆盖以注入自己的 session 子类 / 初始 memory。"""

    @abstractmethod
    def on_match_start(self, state: GameState, session: StrategySession,
                       config: CurrencyWarConfig) -> None:
        """每局开始(loop 首次截图后)。初始化跨步状态(如设初始 target 意向)。P1 默认 no-op。"""

    @abstractmethod
    def on_round_end(self, state: GameState, session: StrategySession,
                     config: CurrencyWarConfig, obs: RoundOutcome) -> None:
        """每场战斗后(观测驱动)。默认 ``session.performance.record(obs)``。
        ⚠️ P1 不被调用(框架不构造 RoundOutcome,观测回路属 P1.5)。"""

    @abstractmethod
    def on_match_end(self, session: StrategySession, config: CurrencyWarConfig,
                     outcome: MatchOutcome) -> None:
        """每局结束。局终收尾(策略可学习/记日志;比赛评分钩子)。P1 默认 no-op(outcome 桩)。"""

    # ===== 决策钩子 =====

    @abstractmethod
    def update_target(self, state: GameState, session: StrategySession,
                      config: CurrencyWarConfig) -> None:
        """战略层:选/转型 target_comp。框架在每个备战回合 ``decide_prep`` **之前**调一次。
        实现写 ``session.target_comp``(首轮选;其后按信号 pivot;无强信号保持)。"""

    @abstractmethod
    def decide_prep(self, state: GameState, session: StrategySession,
                    config: CurrencyWarConfig) -> list[Action]:
        """备战 shop 计划(买/升/D牌/deploy/卖)。读 ``session.target_comp`` 作战略导向、
        ``session.rng`` 作蒙特卡洛。"""

    @abstractmethod
    def decide_invest(self, kind: Literal["strategy", "env"], options: list[str],
                      state: GameState, session: StrategySession,
                      config: CurrencyWarConfig) -> PickEvent:
        """投资策略/投资环境 3 选 1(``kind`` 区分;P1 两 kind 走同一默认实现)。``options``=OCR 卡名列表。"""

    @abstractmethod
    def decide_supply(self, options: list[SupplyOption], state: GameState,
                      session: StrategySession, config: CurrencyWarConfig,
                      refresh_used: bool = False) -> SupplyPick:
        """补给选装备/出钻。⚠️ OCR 未就绪(P1 钩子存在 + 默认委托,handler 不 rewire,随阶段5)。"""

    @abstractmethod
    def decide_encounter(self, options: list[EncounterOption], state: GameState,
                         session: StrategySession, config: CurrencyWarConfig,
                         refresh_used: bool = False) -> EncounterPick:
        """遭遇难度/词缀避开。⚠️ D-35 后 dormant(遭遇=普通战斗无选项 UI);纯逻辑+测试暂留。"""

    @abstractmethod
    def decide_megastar(self, options: list[MegastarOption], state: GameState,
                        session: StrategySession, config: CurrencyWarConfig) -> MegastarPick:
        """巨星选候选。⚠️ OCR 未就绪(P1 钩子存在 + 默认委托,handler 不 rewire,候选 char_id 空 → idx=0)。"""

    @abstractmethod
    def decide_partner(self, options: list[PartnerOption], state: GameState,
                       session: StrategySession, config: CurrencyWarConfig) -> PartnerPick:
        """选择伙伴。⚠️ OCR 未就绪(P1 钩子存在 + 默认委托,handler 不 rewire,char_id 空 → idx=0)。"""

    @abstractmethod
    def decide_boss_priority(self, bosses: list[str], state: GameState,
                             session: StrategySession, config: CurrencyWarConfig) -> list[str]:
        """boss 克制调整阵营优先级。⚠️ 全代码库零调用(缺 boss OCR + dispatch),随阶段5。"""


@dataclass
class StrategySession:
    """一局货币战争的跨步状态(框架每局新建,局终销毁;策略读写;D-34/§11.4)。

    策略实例无状态,所有可变每局状态放这。``rng`` 可种子化(公平/replay);``performance`` 是观测
    反馈(掉血/胜负);``memory`` 是策略私有 scratch(连胜计数/「这轮攒金升8」意图等 escape hatch)。
    """
    target_comp: Comp | None = None        # 战略层目标阵容(update_target 维护)
    rng: random.Random = field(default_factory=random.Random)  # 可种子化(公平/replay);蒙特卡洛 D 牌用
    performance: PerformanceTracker = field(default_factory=PerformanceTracker)  # 观测反馈(双侧 OCR)
    memory: dict[str, Any] = field(default_factory=dict)       # 策略私有 scratch(核心领域实体走正规类型,不塞这)
    # 进度镜像(跨步看趋势用;每回合框架刷新;P1 框架未填,策略暂勿依赖)
    plane: int = 1
    round_num: int = 1
    # 简报词缀(对局开始 debuff/boss 词缀;loop __init__ 从 ctx.cw_briefing_affixes copy;mechanics_fit 输入)
    briefing_affixes: list[str] = field(default_factory=list)
    # 简报首领(3 位面 boss 名;loop __init__ 从 ctx.cw_briefing_bosses copy;boss_fit 输入)
    briefing_bosses: list[str] = field(default_factory=list)
    # 已选投资环境名(如"昼之半神概念股";HandleInvestEnv 选后写;update_target copy 到 state → env_fit 输入)。D-58
    active_env: str = ""


@dataclass
class CurrencyWarMatch:
    """运行时持有 strategy + session 的轻容器,挂 ``ctx.cw_match``(子 op 都拿得到 ``self.ctx``)。

    生命周期:``CurrencyWarRunLoop.__init__`` 每局创建 → 挂 ctx → 每个钩子收到的 session 就是它 →
    局终置 ``ctx.cw_match = None``(防跨局污染)。
    """
    strategy: CwStrategy
    session: StrategySession
