"""货币战争 策略插件机制(CwStrategy ABC + StrategySession + CurrencyWarMatch)。

把货币战争的「决策大脑」抽象成**可替换的 ``CwStrategy`` 对象**(对标 app 插件):
换对象 = 换打法,不动框架。唯一注册核 = mandate_v1(注册壳 =
``strategies/mandate_v1_strategy.py``;注册面封闭集依据 = ``flow/README.md`` §2.1)。

设计见 ``docs/develop/currency_war/strategy/07_plugin.md``;决策见
``docs/develop/sr_od/application/currency_war/decisions/INDEX.md`` 。本模块**纯逻辑**:所有钩子只吃
容器 ``GameState``/选项 + 出 ``Action``/``Pick``,**绝不碰屏幕 / ``ctx.controller``**(读屏与点击
是框架职责)→ 策略可离线 unit 测、可 replay。

四个组件(本模块 3 个 + manager):
- ``CwStrategy`` —— ABC,大脑接口(契约形状见 ADR-0583:每局冷建 2
  + 分画面决策入口 11 = abstract 12,外加非 abstract 工厂 ``create_state``
  1 = 保留总成员 13;零策略专属语义——方向重估节拍/意向 target 机器
  是具体策略实现的私事,不在基类契约面上)。
- ``StrategySession`` —— 每局跨步状态(框架新建 / 局终销毁;策略读写)。
- ``CurrencyWarMatch`` —— 运行时持有 strategy+session 的轻容器,挂 ``ctx.cw_match``。
- ``StrategyManager``(``cw_strategy_manager.py``)—— 约定式文件扫描发现 + 去重 + 实例化。
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    MegastarOption,
    PartnerOption,
    PlannerOption,
    SupplyOption,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import StrategySession
from sr_od.application.currency_war.kernel.cw_vocab import (
    Action,
    PickBoxCard,
    PickEncounter,
    PickInvest,
    PickMegastar,
    PickPartner,
    PickPlanner,
    PickStarTome,
    PickSupply,
    PickWishTrial,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_vocab import CwAction
    from sr_od.context.sr_context import SrContext

# 注解中的 ``CurrencyWarConfig`` 刻意不 import 真类型:config 属 app 桶,本模块
# 归 strategies 包实现层,与 cw_strategy_manager 同层(策略统一迁移批二勘误落位:接口是
# ops/sim/impl 三方共享契约,非实现本体;本模块禁依 app 桶);config 实例由调用方按参
# 注入,下面绑定只是注解名的文档性占位(字符串;「刻意字符串注解」先例 =
# 期 0b kernel/cw_strategy_session 的 SrContext 处理)。
CurrencyWarConfig = 'CurrencyWarConfig'

#: 策略器私有状态的泛型参数(设计正本 §1/§8.5/§8.6-6,迁移批次三「下沉
#: 策略实现层」):StrategyState 归**策略实现层私有**,框架策略器基类仅以
#: 泛型参数携带(本 ABC = 设计所称「策略器基类」,``BaseStrategy[TState]``
#: 形态的落位),框架(kernel/one_dragon)不感知具体类型、零 import 具体
#: 类——具体绑定由各策略实现在自己的类声明上完成(内置 =
#: ``strategies/impl/mandate_v1/mandate_state.StrategyState``,经
#: CwFlowStrategy 链绑定)。布局守卫 = sr-od-test 布局/泛型约束锁。
_TState = TypeVar('_TState')


class CwStrategy(ABC, Generic[_TState]):
    """一整套货币战争局内打法(可替换的决策大脑;终态契约:构造注入 + 零参入口)。

    **终态契约**(2026-09-16-strategy-terminal-contract;用户裁定干净断不留壳):
    - **构造注入**:每局冷建 ``Strategy(gs, config)``——``self.gs`` 当局容器
      单例只读引用、``self.config`` 按参注入、``self.state`` 策略器私有状态
      实例(缺省 None,子类覆写 :meth:`_create_state` 定制)、``self.rng``
      (``config.strategy_seed`` None → 0 固定种子,禁静默翻转为熵种子)。
      构造即唯一冷建口;``create_session``/``create_state`` 工厂退役。
    - **实例不跨局**:局容器弃置 = 实例连带回收(引导漏斗每局 instantiate);
      异常路径残留容器弃置守卫(:func:`discard_stale_match_container`)保留。
    - **零参入口 12**:备战/商店/invest 双相/pick 族八屏——决策输入一律
      ``self.gs`` 自取,会话残余依赖由 §3.2/§3.3 重复账退役清偿。
    - **输出统一**:单一 ``CwAction``(选择族 per-screen 子类型 + 三刷新动作
      + HoldFrame,无 None)。

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

    # ===== 构造注入(唯一冷建口;终态契约 §2.1)=====

    def __init__(self, gs: GameState, config: CurrencyWarConfig) -> None:
        """每局冷建(引导漏斗 ``cls(gs, config)`` 调用;实例不跨局)。

        ``self.state`` 经 :meth:`_create_state` 工厂冷建(缺省 None;子类
        覆写定制私有状态类型)。rng:``strategy_seed`` None → 0 固定种子
        (None→0 语义保持现状,禁静默翻转为熵种子)。
        """
        self.gs = gs
        self.config = config
        self.state = self._create_state()
        seed = getattr(config, 'strategy_seed', None)
        self.rng = random.Random(seed if seed is not None else 0)

    def _create_state(self) -> _TState | None:
        """策略器私有状态工厂钩子(缺省 None;子类覆写返回其私有状态类型,
        基类不感知具体字段)。生命周期 = 一局(实例不跨局 → 状态天然隔离)。"""
        return None
        return None

    # ===== 分画面决策入口(ADR-0517 目标模型:op 的策略接触面 = 入口观察
    #       + 策略器单动作循环;入口按画面塑形,方向重估时机是实现私事)=====

    @abstractmethod
    def decide_prep_screen(self) -> CwAction:
        """备战画面黑板决策(单动作;空发射帧返回 HoldFrame,None 退役)。"""

    @abstractmethod
    def decide_shop_action(self) -> Action:
        """商店单动作决策(恒可用终结 = CloseShop,恒不 None)。观察帧缺失 =
        观察层失约,实现须抛错(禁静默按空态决策)。"""

    @abstractmethod
    def decide_invest_strategy(self, options: list[str]) -> PickInvest:
        """投资策略 3 选 1(options = OCR 卡名列表;原 decide_invest 双相拆分)。"""

    @abstractmethod
    def decide_invest_env(self, options: list[str]) -> PickInvest:
        """投资环境 3 选 1(与策略相共用 PickInvest;原 decide_invest 双相拆分)。"""

    @abstractmethod
    def decide_supply(self, options: list[SupplyOption]) -> PickSupply:
        """补给选装备(带钻优先等语义在 kernel 纯函数,入口负责包装)。"""

    @abstractmethod
    def decide_encounter(self, options: list[EncounterOption]) -> PickEncounter:
        """遭遇难度选(刷新建议 = RefreshNodeOptions 动作,非布尔位)。"""

    @abstractmethod
    def decide_megastar(self, options: list[MegastarOption]) -> PickMegastar:
        """巨星选候选。"""

    @abstractmethod
    def decide_partner(self, options: list[PartnerOption]) -> PickPartner:
        """选择伙伴。"""

    @abstractmethod
    def decide_planner(self, options: list[PlannerOption]) -> PickPlanner:
        """银狼策划事件 3 选 1。"""

    @abstractmethod
    def decide_star_tome(self, options: list[str]) -> PickStarTome:
        """星徽典籍四选一(返回动作子类型,handler 翻译既有点击链)。"""

    @abstractmethod
    def decide_wish_trial(self, options: list[str]) -> PickWishTrial:
        """祈愿试炼选卡(返回动作子类型)。"""

    @abstractmethod
    def decide_box_card(self, names: list[str]) -> PickBoxCard:
        """武装箱/节点弹窗装备卡 4 选 1(返回动作子类型)。"""


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


def discard_stale_match_container(ctx: SrContext, reason: str) -> bool:
    """上一局残留的 match 容器在**新局开始信号**处丢弃(迁移审计 w289(git 历史)/ADR-0419)。

    背景(迁移审计 w285(git 历史) 抽样判读):正常流程局终回大厅会置 ``ctx.cw_match = None``(cw_loop
    分支 3c),下一局 ``RunLoop.handle_init`` 见 None 新建 session —— 状态天然全新。但
    **异常路径**(run 被停机/崩溃在上局对局中、进程未重启)残留非 None 的旧容器;此时
    下一次入口链 ``CwEntryStart`` 开的是一局**新对局**,而
    ``handle_init`` 的续跑判定(``ctx.cw_match is None``)会把旧 session 整体延用:
    level 单调守卫拿上局 ``last_level_obs=5`` 打新局 plane1 的真读(迁移审计 w285(git 历史) cap_vs_level
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
                 '本局 session 全量重建(ADR-0419)', reason)
    ctx.cw_match = None
    if _RESET_PHASE_ROUND_CACHE is not None:
        _RESET_PHASE_ROUND_CACHE()
    return True


# gated_hp(结算 HP 新鲜度门薄委托)已随终态契约 §A 防御锚退役删除
# (2026-09-17):现役消费点 = kernel/cw_hp_policy.decision_hp(gs 直读);
# prep 环入口/终饰写侧预施门已随前置迭代写点退役清零(该文件残留注释
# 为历史锚,随 T-2 docstring 桶清偿)。

