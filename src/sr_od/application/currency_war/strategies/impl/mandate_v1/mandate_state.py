"""货币战争 mandate_v1 策略器状态对象(StrategyState;session.md as-designed
§3.1 裁决 1 的落地载体 + 设计正本 §8.5/§8.6-6 改名归位,迁移批次三)。

**命名归位**(§8.6-6):本类即设计所称 StrategyState(原草板 StrategyMemory
的目标名)——类名已从历史名 MandateState 改名归位,类型本体、字段
集、生命周期零变化(历史名兼容别名已随迁移尾批清理,设计 §8.7 尾批
行;消费面一律 import StrategyState)。**归属判据**(设计 §1):换一个
策略实现就不存在的字段归这里;归策略实现层私有,框架策略器基类仅以泛型
参数携带(``CwStrategy``/``CwFlowStrategy`` 链的 ``_TState``),kernel/
one_dragon 零 import 本类。

设计 §8.5 结构草图的五个语义槽在本类的落位(as-built 映射;草图 = 槽位
清单,本类 = 默认策略实现的全量 realization):

- **K 方向**(配方方向)→ ``target_comp``/``locked_line``/``bridge_id``/
  ``transition_framework``/``target_drought``/``pending_deploys`` 意向面族;
- **义务账本** → ``cw4_fuel_filler_stall_buys``(统一发射登记簿,五出口
  生命周期)/``v3_release``(泄息指令)族;
- **CommitSignals** → ``commit_signals``(定型信号累积器,惰性建);
- **S1 开店闩** → ``cw4_shopped_phase``(同一备战期开店意图一次性);
- **S2 wanted 残差** → ``cw4_shop_wanted_pending``(+ ``cw4_wanted_
  abandon_phase``/``cw4_wanted_reopens`` 同族裁决态);
- **刷新推论** → ``v3_dir_refresh_used``/``v2_round_refreshes`` 等刷新
  计数与推论面;
- **S3 升级检查不立变量**——升级检查 = 期望态
  新鲜度派生,非存储旗标,本类禁新增对应字段。

职责来源裁定(用户 2026-09-06,session.md 头注):session 只承载「从游戏
画面观察到的数据」;策略推导产生的中间状态(目标意向/定型信号/回退集/
纪律计数/遥测分键容器/推导缓存)是**策略器的内容**,由实现包私有定义、
一局内存活、自己持有。框架经 ``CwStrategy.create_state`` 工厂钩子按局
创建实例、写入 ``session.strategy_state``,此后**框架只搬运引用,不读
不写其内部**(黑盒契约);类型定义、字段、更新语义全部在本实现包。

原 ``session.memory`` scratch dict 按设计 §6.3 随切换直接消解:一次性键落
本类的 ``scratch`` dict(纪律条款原样平移:键名加模块前缀、局级生命
周期、不入 decisions 遥测;高频共用/需类型与守卫的状态升本类具名字段)。

边界(kernel 消费面):kernel 判据层对策略状态的消费经
``kernel.cw_strategy_session.strategy_state_of`` 访问函数(返回
``StrategyState | None``,None = 无状态对象的裸构造/第三方策略面——
调用方按原 getattr 缺省语义保守处理),kernel 不持有本类字段注解、
运行时零本包 import(TYPE_CHECKING 承载)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )


@dataclass
class StrategyState:
    """mandate_v1 策略器一局状态(局首由工厂冷建,局终随 session 销毁)。

    即设计正本 §8.5 的 StrategyState(改名归位见模块 docstring;§8.5 五
    语义槽映射亦在彼)。生命周期契约(session.md §3.1 条款 2):每局新建
    即天然清零,禁跨局复用实例;意向状态机段级重入守卫
    (``v3_intention_key``)语义自原 session 字段原样平移,不变。字段
    分组与产生者/消费者/生命周期注释平移自原 ``kernel/cw_strategy_
    session.py`` 对应字段(语义零变更,值域与缺省一致——含
    on_match_start 原逐项初始化值,改由缺省值承载:状态对象每局冷建 =
    天然初值,清零段整体消失)。
    """

    # ===== 意向面(方向重估策略推导;局/轮;写者 = flow 层 _refresh_direction,
    #       内化——原 update_target 直调点收编进策略器决策入口)=====
    target_comp: Comp | None = None   # 战略层目标阵容(方向刷新维护)
    # 弃 target 重选(防 commit 锁死不可达 target:方向刷新重选)。
    target_drought: int = 0
    # 待执行的部署意图(按 position_pref 决策落位)。
    pending_deploys: list = field(default_factory=list)
    # 过渡框架(仙舟/列车,''=未定):双轨期买/上/卖三侧的统一临时 target。
    transition_framework: str = ''

    # ===== 定型面(定型信号推导;局)=====
    # CommitSignals(定型信号累积器;方向刷新首调时惰性建——
    # default_factory 会引环形导入,保留 None 惰性建模式)。
    commit_signals: object = None
    # 双轨期信号领先线 comp(囤牌方向;方向刷新每回合刷新)。
    stash_comp: object = None
    # 定型边沿(卖散上限放宽;decide_prep 一次性消费)。
    commit_flip_pending: bool = False
    # flex 收敛白名单(已铺 flex top2)。
    focus_factions: set[str] = field(default_factory=set)

    # ===== 相位面(v2 决策层相位元组;A2 改判迁出——活读端 =
    # cw_op_buy_cards decisions 行,活写端 = sim 初始相位注入)=====
    v2_state: tuple | None = None
    locked_line: str | None = None                     # 锁定线 id(None=未锁)
    bridge_id: str | None = None                       # 当前桥线 id(None=无)

    # ===== 意向(v3 决策框架载体;局/轮)=====
    v3_intention: object = None      # cw_intention.IntentionState(锁线/撤销状态机)
    v3_core_names: set = field(default_factory=set)   # 意向核心名集
    v3_mode: str = 'economy'         # 本轮模式('economy'|'war';纪律族每轮写)
    v3_last_intention_event: str = ''    # 意向事件去重(判读日志锚)
    v3_intention_key: tuple | None = None   # 意向状态机驱动轮键(段级重入守卫)

    # ===== 血预算拒付披露(遥测;局)=====
    v3_blood_budget_rejects: int = 0
    v3_blood_budget_refresh_rejects: int = 0

    # ===== P2 承接快照(位面)=====
    v3_handoff: object = None
    v3_handoff_plane: int | None = None

    # ===== 对账门声明(帧级全量重算;帧)=====
    v3_posture_unfulfilled: dict | None = None

    # ===== 策略行为观测分键(单一容器;策略 state=决策行 strategy-state
    # 载体,retirement.md §3 键收编定谳:全部键=策略行为键零效果域键,
    # 键全集登记底稿 = 逐键审计 256 字面+16 闭族+9 开放族)=====
    # 局终级全键聚合 = 局终域行载荷 MatchFinal.cw4_counters(cw_loop 两
    # 收口点现读快照);sim 轮差分账本/A/B 披露照旧读本容器,不经流。
    cw4_counters: dict = field(default_factory=dict)

    # ===== 相位与镜像(每轮重算;write_shop_mirrors 写)=====
    # 相位观测缺省 = ''(absence 语义;live 初值 'FORM' 由 create_session
    # 唯一冷建口写入——生命周期收编;
    # sim 直构 session 不经冷建口 → 恒 '',两条路径的旧读数各自保真)。
    v3_phase: str = ''
    v3_form_ok: bool = False         # 镜像现读写端(write_shop_mirrors/sim 发射帧)
    v3_b_t: int = 0                  # 板面目标线承重计数(每轮重算)
    v3_dp_posture: object = None     # DP 姿态轮缓存
    v3_mirror_key: tuple | None = None   # 镜像族轮键戳(单源=write_shop_mirrors)
    v3_formed_stop: bool = False     # 成型停手(行为面消费)

    # ===== 补偿/稳态簿记(局)=====
    v2_remedy_used: bool = False
    v2_steady_lv_used: bool = False
    v3_steady_lv_abandoned: int = 0
    v3_remedy_abandoned: int = 0

    # ===== 轮笔数披露(decisions/遥测判读面;轮)=====
    v2_round_refreshes: int = 0
    v2_round_p1_early: int = 0
    v2_round_p2_core: int = 0
    v2_round_press_exempt: int = 0
    v2_round_press_copy: int = 0

    # ===== 泄息指令与承接门(W332b/w227/;轮)=====
    v3_release: object = None
    v3_release_round: int | None = None
    # 义务实花披露(遥测键 sess_release_spent 透传源):写端=商店执行
    # 回执位(cw_op_buy_cards.accrue_release_spent,首版只计刷新实花,
    # 「宁窄勿虚」口径申报归 ),轮界清零承载=v3_disclosure_key
    # 键戳(economy_cycle.disclose_budget 写端);读端=recorder sess_*
    # 透传 + cw_decision_trace 披露族。披露面字段,禁决策判据消费
    v3_release_spent: int = 0
    v3_handoff_gap: int = 0
    v3_handoff_hp_proj: int | None = None

    # ===== 消费侧惰性建(缺省值 = 原惰性初值)=====
    # A/B 注册表注入通道(cw_economy._registry_of 消费;None=缺省表)。
    v3_registry: object = None
    # 定向刷新消耗计数(cw_registry 名单;局级累计)。
    v3_dir_refresh_used: int = 0
    # DP 姿态轮帧缓存(每段 decide_prep 覆写;None=本轮无决策段)。
    v3_alloc_frame: dict | None = None
    # 储备线披露(遥测键 sess_reserve_cap 透传源;写端=economy_cycle.
    # disclose_budget 每备战决策帧幂等覆写;读端=recorder sess_* 透传
    # + cw_decision_trace 披露族。披露面字段,禁决策判据消费
    v3_reserve_cap: int = 0

    # ===== 账外补充(实施批按 §6.1 收编的策略侧动态属性;产生者/消费
    # 面注释见原写入/读出点)=====
    # 储备溢余披露(遥测键 sess_reserve_overflow 透传源;写端=economy_
    # cycle.disclose_budget,读端=recorder sess_* 透传 + cw_decision_
    # trace 披露族。披露面字段,禁决策判据消费)。
    v3_reserve_overflow: int = 0
    # 义务预算披露(遥测键 sess_release_budget 透传源;写端/读端同上)。
    v3_release_budget: int = 0
    # 义务来源披露(遥测键 sess_release_reason 透传源;写端=shop 必花域
    # 段「must_spend」帧内 last-wins + 披露键戳轮界清零,读端同上)。
    v3_release_reason: str = ''
    # 披露面轮键戳(T-88 轮界清零承载):坐标系=(plane, round) 二元组
    #(位面号/位面内轮次,均 1 基);取值时机=披露帧现读
    #(容器读口 plane_of/round_num_of);写入端=economy_cycle.
    # disclose_budget 单一写点(商店执行回执位只比较不写)。键戳 ≠
    # 当前 (plane, round) ⇒ v3_release_spent/v3_release_reason 清零并
    # 盖新戳。不复用 v3_release_round(W332b 泄息指令旧轮语义)。
    v3_disclosure_key: tuple[int, int] | None = None
    # ↺ 扑满节点识别标记:写者
    # = mandate_v1 奖励帧判定位(shop/mandate 两栈同值幂等写,值源 =
    # kernel.cw_reward_node.is_piggy_reward_frame);读面 = engine 轮快照
    # /telemetry schema piggy_reward。
    v3_piggy_reward: bool = False
    # 商店拒因遥测(shop.py 逐帧刷新;期望态即逻辑态后真值)。
    cw4_shop_rejects: dict = field(default_factory=dict)
    # cw4 线级状态机(proof.LineState;_line_state 惰性建入口统一收口)。
    cw4_line_state: object = None
    # M1″ seam 门唯一写点(mandate.py;值源 = M1P_SEAM_VERIFIED)。
    cw4_m1p_seam_verified: bool = False
    # 换线排除集(cw4 换线判据族读;proof/line_switch 消费)。
    drought_excluded: set = field(default_factory=set)
    # 息帽覆写单一源 = session.active_strategies 经 aggregate_economy
    # 聚合(cw_economy.cap_resolved_of_session 消费)。

    # ===== M2 停摆续段缓存(T-82 必花臂重试风暴;段标识/结论闩/帧动作
    # token 三载体;为什么需要 = 商店/备战帧循环对「输入不变 ⇒ 拒绝不变」
    # 的腾席拒绝无记忆重推导,把一次停摆事件逐帧放大成 N 个事件帧——
    # 缓存命中帧跳过扫描且事件键不增,恢复 P60 诚实停摆的事件粒度语义)=====
    # 段序号。构成:会话态单调递增 int;置位:各段入口 +1(商店 visit
    # 开始[商店画面 op 观察 node=普通 visit 与发射帧仲裁段共用同一入口 /
    # bridge.decide_shop_screen 入口=sim/replay]、备战期
    # 开始[生产 prep 访问循环入口]);比较:只作相等比较、不作阈值,
    # 递增值不承载任何决策量。段 = 停摆结论的输入不变性区间;跨段残留
    # token/闩按序号不等自动失效(域切换=必过段入口,跨域伪命中被同一
    # 比较拦截)。
    cw4_segment_serial: int = 0
    # M4 腾席拒绝结论闩:None=无结论。写入端=两决策位(shop/mandate 的
    # M2 停摆块)在「全量重推导得出腾席无候选」时写 (True, 当前段序号);
    # 有候选但不可逆护栏拒=非本结论,不写。命中判定要求闩序号 == 当前
    # 段序号(与 token 序号两道独立,任一不等即失效重推导)。
    cw4_m2_stall_latch: tuple[bool, int] | None = None
    # 帧动作记录 token(载体单一源):None=无记录。写入端=动作执行/逻辑态直写
    # 层确认已执行后写 (动作型名 type().__name__, 当前段序号),物理写入
    # 位三处:①生产商店循环(商店画面 op 决策动作 node 执行位);
    # ②sim-replay 驱动器(bridge.decide_shop_screen 逻辑态直写位);③生产 prep
    # 循环主环(cw_screen_prep 决策循环 CwActionOpenShopParam/执行器分支合流执行位)。
    # 调用方申报:备战期开店循环
    #(cw_screen_prep 开店分支逐动作调 decide_shop_action)无 token 写入
    # 无段序号置位 ⇒ 域内缓存恒不命中(保守端=现行为,读清单点覆盖
    # 无伪命中),收益面窄化,不接线。读清协议 = decide_shop_action 入口
    # 读取后立即清除(防重复消费);任何调用方首帧(槽空/型外/序号不等)
    # 默认全量重推导。
    cw4_frame_action_record: tuple[str, int] | None = None


    # ===== 账外补充·第二波(实施批收尾扫描按 §6.1 收编的策略侧动态
    # 属性;写入端均在 mandate_v1,消费面含执行侧经访问函数只读)=====
    # M1″ pending 臂(mandate 写,deploy 消费后清 None)。
    cw4_m1p_arm_pending: object = None
    # M1″ 计划载荷 pending(mandate 写,deploy 消费后清 None;T-279 R1/
    # ):{'sell': [victim 名], 'up': [上序名单],
    # 'trans_domain': 计划时点转型域事实, 'occ': 计划时点板占用数}。
    # 消费面 = CwScreenDeploy 部署段(R1-a 直投核对 F2 名字级三点式 + R1-b
    # 域辖域钉定);载荷仅作核对与快路径准入,**不改卖出仲裁权**(卖谁
    # 仍由执行侧现读仲裁,在册分工维持,分工裁决)。
    cw4_m1p_plan_pending: object = None
    # 必花域相位闩(同值重入防抖)。
    cw4_must_spend_phase: object = None
    # pop 槽否向理由留决策迹(D-lv7)。
    cw4_pop_slot_why: str = ''
    # 上一备战期线名快照(k_switched 实值化基准)。
    cw4_prev_line_name: str = ''
    # 近轮已卖名滚动账(P71 凑息卖去重)。
    cw4_recent_sold_names: list = field(default_factory=list)
    # 备战期开店闩(同一备战期内开店意图一次性)。
    cw4_shopped_phase: object = None
    # 素材滞留首见轮账(名 → 首见帧轮次)。
    cw4_stale_seen_rounds: dict = field(default_factory=dict)
    # 本次商店访问已买名单(bridge 清账/op 落账跨层共享)。
    cw4_visit_bought_names: list = field(default_factory=list)
    # 统一发射登记簿(T-126 批 3;/§3,P78 窗口段载体):
    # 名 → (买因, 登记轮),买因闭集 = sell_gate.LAUNCH_CAUSES。前身 =
    # T3 垫保簿(N3 闭环登记契约,名→轮 dict)——T3 簿与 ②(b) 压库簿
    # 完全合一(编者裁);属性名沿用旧簿:执行侧 cw_op_deploy 按鸭子
    # 属性读本名(部署销/held 显影,属性契约级接线禁 import 策略模块),
    # 改名 = 供给静默断裂,语义升级由本注释与本批 ADR 承载。
    # 写端单一源 = sell_gate.register_launch(shop 发射位 _emit_buy +
    # mandate.stall_buys_register 兼容 shim);读端单一源 =
    # sell_gate.active_window(窗口段,press/垫保两类,活跃 = 登记轮
    # ==当前轮)/ sell_gate.stall_protect_active(T3 单类视图)。
    # 生命周期四出口(方案 v3 §3.1;①卖出销/②部署销/②′合成销/
    # ③轮界销):consume_on_sell / prune_on_deploy / consume_on_merge /
    # 读端轮界过期;obligation/hold 类 τ=∞ 不轮界过期,由出口①②②′
    # 与换线闭合(close_on_switch)承载。账闭合按五键分键
    #(close_on_sell/deploy/merge/round/switch)落 cw4_counters。
    cw4_fuel_filler_stall_buys: dict = field(default_factory=dict)

    # ===== T-159 备战旗标状态机(方案 v2.1 §3.1 载体层级裁决,
    # 收编:旗标语义域 = 跨画面访问的复查义务,必须比 visit 长、比对局短,
    # session 是唯一同时满足两界的现役层;全部键式,(位面, 轮次) 相等
    # 命中,节点推进自动失效,免战跳变/恢复局冷建零特判)=====
    # S2 wanted 残差旗标:((位面, 轮次), 买因类, 残差名单元组,
    # 在店快照)。唯一写点 = mandate.shop_wanted_defer(商店域席满残差
    # 产生时点);消费 = mandate.wanted_closure_emit(备战域闭环消费臂)
    # 与 mandate.mark_s1_route_check(路线 (ii) 判据读者,读载体长度
    # 判 S2 在册)——两消费点共三处触达。
    # 门序:门 0 镜像 → 门 0′ 前件 → 门 1 → 两腿 → 放弃。
    # 买因类 = LAUNCH_CAUSES 现役分类学(猎点 14,禁第二分类学),
    # 现役仅 obligation 类置位(press/EV 席满属 discretionary,排除在
    # 重进之外,§5.3 [13])。
    # 在店快照 = 置位时点「在店的缺员 (名, 费用)」子集(T-161 F2,
    # )。为什么置位时点快照而非臂时点现读:消费臂在备战域,
    # obs 对 spec 无商店域的阶段把 state.shop 清空(「没牌」观测真值,
    # ),现读恒空 = 闭环被前件永久闷死(T-161 方案审 F2-1
    # 阻断级发现)。费用 = 卡面费用(游戏定义量,节点内不变)随置位
    # 快照;金不在快照里,臂时点现读——节点内金会变(晶矿入账/他臂
    # 卖出退金),快照金会把「可负担」错钉在置位时点、错杀 late-flip。
    # 快照计算单一源 = shop.py 调用位经 _shop_candidates 同一闭包
    #(方案审 F2-6 禁第二份候选读法)。
    cw4_shop_wanted_pending: tuple | None = None
    # wanted 裁决放弃态:(位面, 轮次)。置位 = 消费臂两腿皆不可行或重进
    # 安全阀超限——本节点不再重进;节点推进键失配自动干净。
    cw4_wanted_abandon_phase: object = None
    # wanted 重进安全阀计数:(phase, n)。记账点 = 门 1 实清与两腿发射;
    # 上限 = mandate.WANTED_REOPEN_CAP(B+1,保守安全阀非紧界,§6.2)。
    cw4_wanted_reopens: tuple | None = None
    # S1 清键后的重进观测标记:(位面, 轮次)。写点 = mark_s1_route_check
    # 实清与 _wanted_reopen_budget;读点 = shop.decide_shop_action 的
    # shop_reopen_discretionary_actions 计数(B4 内容面观测,[28] 息基腿
    # 风险源监控)。纯遥测面,禁决策判据消费。
    cw4_reopen_armed_phase: object = None
    # 武装段受限访问旗(发射帧仲裁;前置发射位载体):True = 本武装段已产
    # 出受限访问意图(段 = armed 连续期,失武装帧复位——复位后若再武装且
    # 仍命中,允许新段再访,合法形态例 = 访问内升级抬息帽)。取值时机 =
    # 前置发射位逐帧现读现写。写端单一源 = bridge._launch_front_check。
    cw4_launch_spend_visited: bool = False

    # ===== 巨星节点候选点击防重入(执行层经 kernel 通道读写的策略器字段)=====
    # True = 本巨星节点内已点过候选(下一步 = 确认),防 re-dispatch 重入
    # 再点候选 → toggle 反选 → 确认无候选卡死。必须跨 re-dispatch 持久:
    # 落 op 实例 = 每次新建实例清零,即原始事故形态(session.md §2.4 B1
    # 定案);本类局级冷建天然承载该生命周期。复位时机 = 节点完成即复位
    # (observe 门 miss 巨星 overlay 时;巨星一局可多次触发,标记不跨节点
    # 保持)。访问通道契约:框架执行层读写经 kernel
    # ``cw_strategy_session.strategy_state_of``(None-safe 不冷建——状态
    # 对象缺席时读退 False/写跳过);**禁 impl 侧 ``state_of`` 从执行层
    # 调用**(其 None 冷建覆写属策略器装配语义,执行层不得触发)。写读点
    # = operations/cw_screen/cw_screen_megastar.py(复位/读/置位三点)。
    megastar_clicked: bool = False

    # ===== scratch(原 session.memory 消解宿主;§6.3 纪律平移)=====
    # 策略实现层私有 scratch——临时变量不再逐个升字段。纪律:
    # ①键名加模块前缀防冲突;②生命周期 = 局级(状态对象每局新建自然
    # 清零),节点级清理归使用者;③不入 decisions 遥测;④高频共用/需
    # 类型与守卫的状态仍应升具名字段;⑤禁重复框架已提供的对局事实。
    scratch: dict[str, Any] = field(default_factory=dict)


def state_of(session: StrategySession) -> StrategyState:
    """策略器侧状态读口:取 ``session.strategy_state`` 并收窄类型。

    终态契约 §2.6 过渡桥:入参即 StrategyState 本体 → 直返(零参 decide
    以 self.state 作宿主参传 mandate 链的通道)。None/异型(裸构造
    session、第三方策略未覆写 create_state)→ 惰性冷建并写回(与原
    cw_intention 惰性建同构;设计 §5.1 B4 兼容条款的实现面)。
    mandate_v1 链内统一经本函数消费状态对象。
    """
    if isinstance(session, StrategyState):
        return session   # 终态:状态本体直通
    st = getattr(session, 'strategy_state', None)
    if not isinstance(st, StrategyState):
        st = StrategyState()
        session.strategy_state = st
    return st


def ensure_strategy_state(strat: object, session: StrategySession,
                          initial_v2_state: tuple | None = None
                          ) -> StrategyState:
    """sim 侧统一构建口(设计 §3.4-1):经被测策略工厂补建状态对象。

    - ``strat`` 按鸭子类型取 ``create_state``(注解 object:注入桩可无该
      钩子,工厂不可得 → 冷建兜底);
    - ``session.strategy_state`` 已是 StrategyState → 直返(注入/进场态
      复用 session 通道);
    - 缺失 → 调 ``strat.create_state`` 工厂(与 live 同源生命周期);工厂
      不可得(注入桩)→ 冷建 StrategyState 兜底。**config 实参传 None**
      (sim 面无 config 可注入)——``create_state`` 工厂契约 = 可忽略
      config/容忍 None(见 flow.CwFlowStrategy.create_state docstring),
      工厂实现禁读 config 取值;
    - ``initial_v2_state`` 非 None → 初始相位经状态对象初始化入口写入
      (原 sim 直写 session.v2_state 的替代;禁裸 setattr session)。
    """
    st = getattr(session, 'strategy_state', None)
    if not isinstance(st, StrategyState):
        factory = getattr(strat, 'create_state', None)
        built = factory(None) if callable(factory) else None   # None 契约见 docstring
        st = built if isinstance(built, StrategyState) else StrategyState()
        session.strategy_state = st
    if initial_v2_state is not None:
        st.v2_state = initial_v2_state
    return st
