"""货币战争 策略会话载体。

`StrategySession` = 一局跨步状态载体(纯 dataclass 字段,零行为;
框架每局新建、局终销毁)。职责单一(用户 2026-09-06 裁定,设计件
`docs/develop/sr_od/application/currency_war/flow/session.md` as-designed):本类**只承载
「从游戏画面观察到的数据」**(框架读屏与识别层守卫产生;策略器只读)
+ 框架设施(rng 种子契约锚 / performance 观测反馈)+ ``strategy_state``
黑盒引用。策略器推导产生的中间状态归实现包私有的状态对象
(mandate_v1 = ``StrategyState``,经 ``create_state`` 工厂按局冷建)。
执行层不设独立状态载体(执行层状态类目已退役,git 历史可溯):
op/流程侧产生的状态按其语义各自归位——局内事实写 GameState 容器
(Field 组与非 Field 簿记组,宿主 ``kernel/cw_game_state.py``),
防重入由决策面读容器计数自行裁决。

驻 kernel 理由:kernel 判据层以本类为观察数据载体消费(经
``strategy_state_of`` 访问函数取策略状态——None-safe 不冷建;kernel
不持有策略内部结构的字段注解,运行时零 impl 包 import,
TYPE_CHECKING 承载)。类体逐字段无 app 引用。
"""
from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from sr_od.application.currency_war.kernel.cw_performance import (
    PerformanceTracker,
)

#: 策略器状态工厂注入槽(kernel 不识策略状态具体类型——依赖矩阵禁 kernel→impl
#: 边,连 TYPE_CHECKING 引用也在分层纪律禁域(该纪律归 review 与代码规范
#: 守卫);先例 =
#: set_merge_effect_gate/set_obs_reset_hook 注入槽)。注册点 =
#: ``strategies/impl/mandate_v1/__init__``(包被导入即安装,三方策略不装
#: = 缺省关)。kernel 写路径(drive_intention/_bump_obs)经
#: :func:`strategy_state_lazy` 惰性取状态;读路径用 :func:`strategy_state_of`。
_STATE_FACTORY: Callable[[], object] | None = None


def install_strategy_state_factory(factory: Callable[[], object]) -> None:
    """注册策略器状态工厂(幂等覆盖;仅 impl 包装配点调用)。"""
    global _STATE_FACTORY
    _STATE_FACTORY = factory


def strategy_state_lazy(session: StrategySession) -> object | None:
    """kernel 写路径取状态:无状态对象时经注入工厂惰性冷建并写回。

    工厂未注册(第三方策略面)→ None(调用方保守跳过);与迁移前
    「动态属性惰性建」语义同构(原 cw_intention.py 惰性建先例)。"""
    return ensure_strategy_state_attached(session)


def ensure_strategy_state_attached(session) -> object:
    """读+惰性附着:无状态对象且工厂已注册 → 冷建并写回 session。

    装配点 = ``CurrencyWarMatch.__post_init__``(局容器建立即保证当局
    状态对象在位)+ kernel 写路径。工厂未注册 → None(不代建)。"""
    st = strategy_state_of(session)
    if st is not None:
        return st
    factory = _STATE_FACTORY
    if factory is None:
        return None
    st = factory()
    session.strategy_state = st
    return st


def strategy_state_of(session: StrategySession) -> object:
    """策略器状态访问函数(kernel/遥测/sim/ops 统一读口;设计 §3.1 条款 1)。

    返回 ``session.strategy_state``(黑盒引用;类型收窄注解以 object
    承载——依赖矩阵禁 kernel→impl 边,策略状态内部结构对 kernel 不
    可见,消费面走 getattr)。

    None 契约与调用方前提**(B4 收缩申报,「落位裁量」):
    None = 策略器状态未装配(裸构造 session 且工厂未注册 / 第三方策略
    未覆写 ``create_state``)。内置策略路径由 create_session 接线 +
    局容器 ``__post_init__`` 附着 + kernel 写路径
    惰性兜底保证在位。两类读面形态:

    - **判据/披露面**(kernel 判据、遥测披露键):字段在异型状态对象上
      可能缺席 → ``getattr(strategy_state_of(s), 'x', d)`` 防御形态,
      缺席退缺省(与迁移前动态属性缺席行为一致);
    - **行为面读点**(ops 主链决策输入等):直接解引用,辖**内置策略**;
      None 态解引用 = AttributeError **显式炸错**(mis-assembly 信号,
      不静默降级产 None 假数据)——「存量第三方策略零破坏」承诺收缩为
      「ABC 非 abstract 缺省不炸构造与 create_session」,不承诺框架行为
      面读点容忍 None 态。

    **禁直读 session 猜策略字段**——迁移后策略状态不在 session 上,
    遥测可见性唯一通道 = 本访问函数(session.md §3.1 条款 4)。
    """
    return getattr(session, 'strategy_state', None)


@dataclass(eq=False)
class StrategySession:
    """一局货币战争的观察数据载体(框架每局新建,局终销毁;/§11.4)。

    ``rng`` 可种子化(公平/replay;default=固定种子 0 的独立实例,确定
    性由构造保证,真实随机面由消费方显式注入);``performance`` 是观测
    反馈(掉血/胜负)。``strategy_state`` 是策略器状态黑盒引用(框架只
    搬运引用,不识内部;所有权归策略器)。``eq=False``:session 是身份
    对象(局容器/执行侧旁表按键引用),值相等语义无消费面。
    """
    # (last_state 槽已随 last_state 链退役批删除:三写点(备战观察×2/
    #  买牌融合段)与全部遗留读者已切容器单例(game_state_of);备战
    #  快照的现役宿主 = 容器,观察喂入 = read_game_state 漏斗。)
    # (终态契约 §A 防御缓存已删:结算 hp 锚 last_hp/last_hp_t、对账锚
    #  last_hp_real/last_hp_real_node、hp 下行拒信通道 hp_suspect、左移
    #  推断族 last_node_type/upcoming_types/nodeseq_probe_anchor、node
    #  识别值 node_type_current——真值职责归 gs(覆盖写端 + carried +
    #  node_kind_of 推导),失准走识别优化批,design §1.3。)
    # (终态契约 §A′ 探针族宿主迁移:plane_node_table/plane_node_table_plane/
    #  plane_lengths_seen session 份退役——单一源 = gs.node_books
    #  (NodeBooks,写端 = prep 采集,读端 = cw_plane_table 经桥)。)
    # (终态契约 §B:last_streak session 份退役——结算带符号真值由结算
    #  覆盖写端直入 gs.streak,economy/观察消费读容器。)
    # (终态契约 §B 重复账退役:active_strategies/active_env/last_owned_equips
    #  session 份已删——单一源 = gs(write_logic 选择写点),kernel/obs 消费读容器。)
    # (chosen_megastar/chosen_partner session 份已随终态契约 §B 退役:
    #  单一源 = gs.chosen_*(write_logic 选择写点),session 份零读者。)
    # (briefing_affixes/briefing_bosses session 份已随终态契约 §B 退役:
    #  单一源 = gs.enemy_affixes/gs.plane_bosses,写端 = 简报/位面详情采集/
    #  prep 补采直写;affixes 幂等辖读+采、bosses 恒覆写含读空清、保位
    #  None 不滤语义全部上移容器写端。)
    # (selected_difficulty/enemy_difficulty session 份已随终态契约 §B 退役:
    #  单一源 = gs.selected_difficulty/gs.enemy_difficulty,写端 = 入口链
    #  漏斗/briefing 写端直写。)
    # (active_env session 份已随终态契约 §B 退役——单一源 = gs.active_env。)
    # ⚠️ 显式种子化:default 禁止 OS 熵种子,default=
    # 固定种子 0 的独立实例;真实随机面由消费方显式注入——生产 run loop
    # 按 cw_config.strategy_seed 覆盖(operations/cw_loop.py)。
    # 本字段是公开随机接口的种子契约锚。
    rng: random.Random = field(default_factory=lambda: random.Random(0))
    performance: PerformanceTracker = field(default_factory=PerformanceTracker)  # 观测反馈(双侧 OCR)
    # (prep_obs_frame 黑板帧槽已随黑板退役删除——迭代
    #  2026-09-18-prep-obs-retirement 阶段 3.5:名单/装备/占用/晶矿全部容器
    #  域承载,策略器唯读容器契约归位;观察控制信号降级为备战环 op 局部
    #  对象,不经 session。)
    # (终态契约 §B:黑板帧刷新代次标注 prep_frame_class/shop_frame_class
    #  session 槽已退役——迁 gs 非 Field 双槽 frame_class_prep/
    #  frame_class_shop(值域/消费协议/写点面全量随迁,详 gs 字段注);
    #  语义:full = 入口主观察帧(方向重估全程);view = 派生帧(只刷视图);
    #  none = 逻辑态直写/续段/未持新观察。读后即清,消费 = flow 层
    #  _consume_*_direction_frame。)
    # pending_round_outcomes 槽已随消费侧 drain 退役整删——结算真值
    # 归宿 = gs 结算覆盖写端(apply_settlement_cover)+ performance.history。
    # —— 策略器状态黑盒引用(session.md §3.1 裁决 1)——
    # 类型由实现包自定义(mandate_v1 = StrategyState,§8.6-6 改名归位);
    # 框架经 create_state 工厂按局冷建、只搬运引用不识内部(所有权归策略器;
    # 生命周期 = 一局,局终随 session 销毁)。第三方策略未覆写 create_state
    # → None(其策略器沿用惰性建模式;B4 兼容承诺的收缩口径 = 「缺省 None
    # 不炸构造与 create_session」,不承诺框架行为面读点容忍 None 态——
    # None 契约与调用方前提见 strategy_state_of docstring/)。
    strategy_state: object = None
