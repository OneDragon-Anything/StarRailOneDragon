"""货币战争 策略会话载体。

`StrategySession` = 一局跨步状态载体(纯 dataclass 字段,零行为;
框架每局新建、局终销毁)。职责单一(用户 2026-09-06 裁定,设计件
`docs/develop/sr_od/application/currency_war/flow/session.md` as-designed):本类**只承载
「从游戏画面观察到的数据」**(框架读屏与识别层守卫产生;策略器只读)
+ 框架设施(rng 种子契约锚 / performance 观测反馈)+ ``strategy_state``
黑盒引用。策略器推导产生的中间状态归实现包私有的状态对象
(mandate_v1 = ``MandateState``,经 ``create_state`` 工厂按局冷建);
执行层状态(op/流程侧产生:失败计数/防重入/对账期望账)归执行侧
载体(``kernel/cw_exec_state.py`` 的 ``ExecState``,挂局容器
``CurrencyWarMatch.exec_state``)。

驻 kernel 理由:kernel 判据层以本类为观察数据载体消费(经
``strategy_state_of`` 访问函数取策略状态、``exec_state_of`` 取执行侧
载体——kernel 不持有策略内部结构的字段注解,运行时零 impl 包 import,
TYPE_CHECKING 承载)。类体逐字段无 app 引用;``prep_obs_frame``/
``shop_state_frame``/``pending_buy_expect`` 相关注解字符串化(app 桶
类型仅注解引用)。
"""
from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    ActiveEffectInventory,
)
from sr_od.application.currency_war.kernel.cw_performance import (
    PerformanceTracker,
    RoundOutcome,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_prep_actions import PrepObservation
    from sr_od.application.currency_war.kernel.cw_state import GameState

#: 策略器状态工厂注入槽(kernel 不识 MandateState——依赖矩阵禁 kernel→impl
#: 边,连 TYPE_CHECKING 也被布局锁 test_cw_package_layout 判违规;先例 =
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

    None 契约与调用方前提**(B4 收缩申报,ADR-0563「落位裁量」):
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
    # 备战快照(read_game_state;给节点 overlay handler 读 comp 近似——
    # overlay 时 board 不可读,用上次备战读的近似)。
    last_state: GameState | None = None
    # 改用结算 HP(结算屏「小队生命值NN」可靠)给下回合 prep state.hp。
    last_hp: int | None = None
    # last_hp 的全局节点号((plane-1)*9+round):结算 hp 只在「紧邻上一节点」
    # 才可覆盖 prep 现读(低 conf 结算轮陈 hp 冻结毒化防线,P1 boss 赢→hp1
    # 进 P2 秒死 ×3 的观测链根因)。
    last_hp_t: int | None = None
    # ADR-0282(hp 三层·对账层):备战屏血量**最后真值**(read_game_state
    # 真值帧经 reconcile_hp 写;shop 开态读不到=保旧沿用,不是兜底 100)。
    # 与 last_hp(结算屏真值,gated_hp 新鲜度门消费)分工:本字段是备战
    # 现读域的对账锚。开局首真值帧前为 None。
    last_hp_real: int | None = None
    # last_hp_real 写入时的全局节点号(ADR-0431):hp_trusted 帧龄门的
    # 坐标系锚——同节点内沿用可信;跨节点=期间可能未观测战斗 → 降不可信。
    last_hp_real_node: int | None = None
    # hp 下行拒信复现确认通道状态(ADR-0431):{'value','node','count'}。
    # 识别质量通道,非策略输入。None=无活跃 suspect。
    hp_suspect: dict | None = None
    # 最近 node_type 真值:商店开态帧节点行被遮 → Director 在 shop 关态
    # heavy 读到时写此;shop.py 喂决策前拷入(仿 last_hp 模式)。
    last_node_type: str | None = None
    # 节点行 current 槽识别类型(read_node_sequence,备战画面权威源)——
    # cw_screen_prep 每次备战读节点行时写;结算观测回路(cw_screen_battle_wait)消费。
    node_type_current: str | None = None
    # 上帧 upcoming 槽类型序列(idx 升序)——current 高亮态 Hu 不匹配时
    # 左移推断用:本轮 current = 上帧 upcoming[0]。
    upcoming_types: list[str] | None = None
    # 开局帧完整槽序——离线统计源(位面典型节点表)+ 左移兜底参照;
    # 写入端在 cw_screen_prep._probe_node_type 首帧。
    plane_node_table: list[str] | None = None
    # ADR-0368:plane_node_table 是哪位面的表(每位面首帧重写时更新)。
    plane_node_table_plane: int | None = None
    # ADR-0368:本局已揭晓的位面轮数序列(每位面首帧 append)——
    # cw_plane_table.schedule_of 的真值源。
    plane_lengths_seen: list[int] | None = None
    # 左移推断的轮次锚——同轮多次 probe 不重做左移。
    nodeseq_probe_anchor: tuple | None = None
    # 上回合结算 streak(带符号 连胜+/连败-;结算观察半从结算「连胜×N」
    # 即时直写,ADR-0583)。给下回合 economy C 杠杆读(语义在前缀,备战 read_streak 无方向)。
    last_streak: int = 0
    # level 单调守卫(read_level OCR 间歇误读;等级局内只升不降,读出<上次
    # =误读用上次)。新局默认 0。识别层守卫状态。
    last_level_obs: int = 0
    # 已持有投资策略(局中选,可多张;选卡 handler 采集,read_game_state
    # 拷贝到 state 供 _refresh_cap 等消费)。
    active_strategies: list[str] = field(default_factory=list)
    # owned 穿戴池快照(ADR-0358):CwOpEquipAll 每轮 read_equips 后写;
    # _pseudo_state 拷入决策 state.equips → decisions 遥测可见。
    last_owned_equips: list[str] = field(default_factory=list)
    # 遥测接线(ADR-0229 缺口):选择类 handler 写 → read_game_state 回写
    # state 同名字段(复盘维度:巨星绑定/伙伴选择与 comp 匹配)。
    chosen_megastar: str = ''
    chosen_partner: str = ''
    # star 回退防抖(char → 已见次数;274 存证重读实证:合成动画窗 live 读
    # 1★)——首次回退 star 保旧不写回,连续第二次才采新确认。框架识别守卫。
    star_pending_regression: dict[str, int] = field(default_factory=dict)
    # 简报词缀(对局开始 debuff/boss 词缀;写入端 = CwScreenBriefing 内联
    # 直写(仅空时写);mechanics_fit 输入,ADR-0397/0398 保位勿滤)。
    briefing_affixes: list[str] = field(default_factory=list)
    # 本局职级(A1..A8;CwEntryStart 难度确认屏读 → loop copy;保血阈值)。
    selected_difficulty: str = ""
    # 敌人难度数值(简报「敌人难度N」读;read_game_state 填 state)。
    enemy_difficulty: int | None = None
    # 位面序 boss 真值(3 位面 boss 名;cw_loop 首个稳定备战帧 copy 自简报
    # LCS 清洗读数 + CwScreenPlaneIntel 实采;元素可 None = 徽章态采不到
    # 身份——保位勿滤,滤掉会让后续位面名字左移错位)。
    briefing_bosses: list[str | None] = field(default_factory=list)
    active_env: str = ""
    # ⚠️ 显式种子化(sim 确定性报告):default 禁止 OS 熵种子,default=
    # 固定种子 0 的独立实例;真实随机面由消费方显式注入——生产 run loop
    # 按 cw_config.strategy_seed 覆盖(operations/cw_loop.py),sim 引擎
    # 从局 seed 派生(sim/engine_p1.py)。本字段是公开随机接口的种子契约锚。
    rng: random.Random = field(default_factory=lambda: random.Random(0))
    performance: PerformanceTracker = field(default_factory=PerformanceTracker)  # 观测反馈(双侧 OCR)
    # —— 黑板模式观察帧容器(W971 §2 黑板模式,dd-014)——
    # prep_obs_frame:备战观察结果(PrepObservation 整帧)。生命周期 =
    # 新鲜快照(每次备战观察覆写)。写者白名单 = cw_screen_prep._observe /
    # 破警告派生帧 / 兼容期旧接口薄委托。读者 = decide_prep_screen(黑板
    # 决策唯一输入源)。
    prep_obs_frame: 'PrepObservation | None' = None   # noqa: F821, UP037
    # shop_state_frame:商店开画面融合观察态(GameState,波顶融合段产物)。
    # 生命周期 = 画面态(每次进商店波循环覆写)。写者白名单 =
    # buy_cards.run_buy_waves 波顶融合段 / sim 引擎。读者 = decide_shop_screen。
    shop_state_frame: 'GameState | None' = None   # noqa: F821, UP037
    # —— 黑板帧刷新代次标注(ADR-0583 §3.4;帧语义标注,属观察层产物)——
    # 值域 'full' | 'view' | 'none',缺省 'none'。坐标系:标注对象 = 同名黑板
    # 帧槽(prep_obs_frame / shop_state_frame)的最近一次写入。写者 = 流程
    # 观察段具名写点(cw_screen_prep 入口 heavy/破墙/投影/read_only 分支、
    # finalize 买后暂存;cw_op_buy_cards 商店 visit 首段/续段;sim engine_p1
    # 每决策段;写点清单 = ADR-0583 §3.4,守卫 = 契约形状锁 L6);
    # 策略器/驱动器零标注写点(帧类写'full'/'view' = 观察层专属身份,D6)。
    # 读者 = 策略器决策入口(flow 层 _consume_*_direction_frame),读后即复位
    # 'none'(消费即清;复位是读协议半部,非新鲜度宣告)。语义:full = 入口
    # 主观察帧(方向重估全程触发);view = 派生帧(只刷派生视图);
    # none = 投影/循环续段/pick 未持新观察(不触发刷新)。
    prep_frame_class: str = 'none'
    shop_frame_class: str = 'none'
    # 结算策略半待加工槽(ADR-0583 §2.5:旧 on_round_end 拆两半)。观察层在
    # 结算点(cw_screen_battle_wait 结算回路)追加 ``RoundOutcome``;策略器在
    # 下一次决策入口惰性 drain(flow 层 _drain_pending_round_outcomes),
    # 处理即清槽(每行只加工一次)。写者 = 观察层(单一写端);清者 = 策略器。
    # 生命周期 = 槽内行存活到下一决策入口(死亡局无后续入口则不加工——
    # 该四字段族零行为读端,零行为差申报见 ADR-0583 §2.5)。
    pending_round_outcomes: list[RoundOutcome] = field(default_factory=list)
    # —— 策略器状态黑盒引用(session.md §3.1 裁决 1)——
    # 类型由实现包自定义(mandate_v1 = StrategyState,§8.6-6 改名归位);
    # 框架经 create_state 工厂按局冷建、只搬运引用不识内部(所有权归策略器;
    # 生命周期 = 一局,局终随 session 销毁)。第三方策略未覆写 create_state
    # → None(其策略器沿用惰性建模式;B4 兼容承诺的收缩口径 = 「缺省 None
    # 不炸构造与 create_session」,不承诺框架行为面读点容忍 None 态——
    # None 契约与调用方前提见 strategy_state_of docstring/ADR-0563)。
    strategy_state: object = None

    # ---- 在场效果账本兼容读口(迁移批次三载体归一,设计 §5.1/§8.4)----
    # 正本 = ``BoardState.effects``(§8.4 单例字段;session 旁表同局同实例)。
    # 历史字段本体已从本类移除——原 ``session.effect_inventory`` 独立实例
    # 与 BoardState.effects 并存即双账本漂移面,归一后本属性只读透传,
    # 既有写点(prep_actions 升级标记)与读点(pick_bias)经属性零改动
    # 兼容。禁赋值(无 setter):账本写入一律经 inventory 方法
    # (register/tick/bump/consume_use/on_*),直挂实例 = 绕过单一实例。
    @property
    def effect_inventory(self) -> ActiveEffectInventory:
        """在场效果清单兼容读口(正本 = BoardState.effects,§5.1/§8.4)。"""
        from sr_od.application.currency_war.kernel.cw_board_state import (
            board_state_of,
        )
        return board_state_of(self).effects
