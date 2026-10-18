"""货币战争 mandate_v1 策略器状态对象(StrategyState;session.md as-designed
§3.1 裁决 1 与设计正本 §8.5/§8.6-6 的落地载体)。

**命名归位**(§8.6-6):本类即设计所称 StrategyState,消费面一律
import StrategyState(历史名 MandateState 已无兼容别名)。**归属判据**(设计 §1):换一个
策略实现就不存在的字段归这里;归策略实现层私有,框架策略器基类仅以泛型
参数携带(``CwStrategy``/``CwFlowStrategy`` 链的 ``_TState``),kernel/
one_dragon 零 import 本类。

设计 §8.5 结构草图的五个语义槽在本类的落位(as-built 映射;草图 = 槽位
清单,本类 = 默认策略实现的全量 realization):

- **K 方向**(配方方向)→ ``target_comp``(锁定线槽,键面
  归一后 = 候选-锁定制终态单写者键)/``locked_line``/``bridge_id``/
  ``transition_framework``/``pending_deploys`` 意向面族;
- **义务账本** → ``cw4_fuel_filler_stall_buys``(统一发出登记簿,五出口
  生命周期)/``v3_release``(泄息指令)族;
- **CommitSignals** → ``commit_signals``(定型信号累积器〔评估数据表,
  §1.6 边界外保留项〕,投资选卡帧惰性建);
- **S1 开店标志/S2 wanted 残差** → 已删除
  (会话标记/会话循环承接);
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


@dataclass(frozen=True)
class ShopOpportunity:
    """未消费机会清单记录(shop_session §4.2:判据通过但被资源拦下的牌)。

    写入端 = 商店会话正常收工位(已接线);消费端 = 备战第 4
    步入口的解拦复核(判定函数 3.6 建造)。字段集 = 解拦判定所需最小面
    (金位解除线 = 注册表价 `price` 比对、`order_class` = 解拦后重评的
    归属序)。
    """

    card_name: str    # 牌名(注册表规范名)
    blocked_by: str   # 拦因闭集:'bench_full'(席满)| 'gold_short'(金不足)
    price: int        # 注册表价(金的解除线比对基准)
    order_class: str  # 买入序类(统一买入策略的序归属;值域随 3.6 接线枚举)


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

    # ===== 方向键面(键面归一:锁定线槽 = target_comp 终态单写者
    #       = session_scope.write_line_lock;配方物化链写端 =
    #       opening_recipe_comp;写读单一源 = session_scope 方向函数族)=====
    target_comp: Comp | None = None
    """锁定线槽(候选-锁定制的锁定产物,Comp 对象;None = 未锁定)。

    终态单写者 = ``session_scope.write_line_lock``(硬规则命中帧或时点
    兜底帧一次性写入,锁后只读——候选-锁定制无换目标);物化链
    (flow 层 P1 配方)写端已切 ``opening_recipe_comp``,两键互不覆写
    (P1 锁定局并集消费见 shop 序 1,line_and_upgrade §1.3)。kernel
    消费面经 ist.locked_comp 派生缓存续读(session_scope 同步)。"""
    # 待执行的部署意图(按 position_pref 决策落位)。
    pending_deploys: list = field(default_factory=list)
    # 过渡框架(仙舟/列车,''=未定):双轨期买/上/卖三侧的统一临时 target。
    # (现役无写端、消费面按 '' 缺省只读——历史保留键,读端见
    # cw_recipe/cw_deploy_logic。)
    transition_framework: str = ''

    # ===== 定型面(定型信号推导;局)=====
    # CommitSignals(定型信号累积器,评估数据表——§1.6 机器本体停用的
    # 边界外保留项;投资选卡帧惰性建并喂入,纯遥测决策面零消费)。
    commit_signals: object = None

    # ===== 相位面(v2 决策层相位元组;A2 改判迁出——活读端 =
    # 商店执行回执 decisions 行(写点 = cw_screen_shop),活写端 = sim 初始相位注入)=====
    v2_state: tuple | None = None
    locked_line: str | None = None                     # 锁定线 id(None=未锁)
    bridge_id: str | None = None                       # 当前桥线 id(None=无)

    # ===== 意向(v3 决策框架载体;局/轮)=====
    v3_intention: object = None      # cw_intention.IntentionState(终局阵容锁定/撤销状态机)
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
    # 载体,retirement.md §3 键归属已定案:全部键=策略行为键零效果域键,
    # 键全集登记底稿 = 逐键审计 256 字面+16 闭族+9 开放族)=====
    # 局终级全键聚合 = 局终域行载荷 MatchFinal.cw4_counters(cw_loop 两
    # 收尾点现读快照);sim 轮差分账本/A/B 披露照旧读本容器,不经流。
    cw4_counters: dict = field(default_factory=dict)

    # ===== 相位与镜像(每轮重算;write_shop_mirrors 写)=====
    # 相位观测缺省 = ''(absence 语义;live 初值 'FORM' 由 create_session
    # 唯一冷建口写入——生命周期并入;
    # sim 直构 session 不经冷建口 → 恒 '',两条路径的旧读数各自保真)。
    v3_phase: str = ''
    v3_form_ok: bool = False         # 镜像现读写端(write_shop_mirrors/sim 动作发出帧)
    v3_b_t: int = 0                  # 板面目标线支撑计数(每轮重算)
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

    # ===== 泄息指令与承接门(轮界清零)=====
    v3_release: object = None
    v3_release_round: int | None = None
    # 义务实花披露(遥测键 sess_release_spent 透传源):写端=商店执行
    # 回执位(cw_screen_shop.accrue_release_spent,首版只计刷新实花,
    # 「宁窄勿虚」口径申报,轮界清零承载=v3_disclosure_key
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

    # ===== 账外补充(实施时按 §6.1 并入的策略侧动态属性;产生者/消费
    # 面注释见原写入/读出点)=====
    # 储备富余披露(遥测键 sess_reserve_overflow 透传源;写端=economy_
    # cycle.disclose_budget,读端=recorder sess_* 透传 + cw_decision_
    # trace 披露族。披露面字段,禁决策判据消费)。
    v3_reserve_overflow: int = 0
    # 义务预算披露(遥测键 sess_release_budget 透传源;写端/读端同上)。
    v3_release_budget: int = 0
    # 义务来源披露(遥测键 sess_release_reason 透传源;写端=shop 富余段
    # 段「must_spend」帧内 last-wins + 披露键戳轮界清零,读端同上)。
    v3_release_reason: str = ''
    # 披露面轮键戳(轮界清零承载):坐标系=(plane, round) 二元组
    #(位面号/位面内轮次,均 1 基);取值时机=披露帧现读
    #(容器读口 plane_of/round_num_of);写入端=economy_cycle.
    # disclose_budget 单一写点(商店执行回执位只比较不写)。键戳 ≠
    # 当前 (plane, round) ⇒ v3_release_spent/v3_release_reason 清零并
    # 盖新戳。不复用 v3_release_round(泄息指令旧轮语义)。
    v3_disclosure_key: tuple[int, int] | None = None
    # ↺ 扑满节点识别标记:写者
    # = mandate_v1 奖励帧判定位(shop/mandate 两栈同值幂等写,值源 =
    # kernel.cw_reward_node.is_piggy_reward_frame);读面 = engine 轮快照
    # /telemetry schema piggy_reward。
    v3_piggy_reward: bool = False
    # 商店拒因遥测(shop.py 逐帧刷新;期望态即逻辑态后真值)。
    cw4_shop_rejects: dict = field(default_factory=dict)
    # M1″ seam 门唯一写点(mandate.py;值源 = M1P_SEAM_VERIFIED)。
    cw4_m1p_seam_verified: bool = False
    # 利息上限覆写单一源 = session.active_strategies 经 aggregate_economy
    # 聚合(cw_economy.cap_resolved_of_session 消费)。

    # ===== M2 停摆续段缓存(必花分支重试风暴;段标识/结论标志/帧动作
    # token 三载体;为什么需要 = 商店/备战帧循环对「输入不变 ⇒ 拒绝不变」
    # 的腾席拒绝无记忆重推导,把一次停摆事件逐帧放大成 N 个事件帧——
    # 缓存命中帧跳过扫描且事件键不增,恢复 P60 诚实停摆的事件粒度语义)=====
    # 段序号。构成:会话态单调递增 int;置位:各段入口 +1(商店 visit
    # 开始[商店画面 op 观察 node 入口 / bridge.decide_shop_screen
    # 入口=回放/序列测试]、备战期
    # 开始[生产 prep 访问循环入口]);比较:只作相等比较、不作阈值,
    # 递增值不承载任何决策量。段 = 停摆结论的输入不变性区间;跨段残留
    # token/标志按序号不等自动失效(域切换=必过段入口,跨域伪命中被同一
    # 比较拦截)。
    cw4_segment_serial: int = 0
    # M4 腾席拒绝结论标志:None=无结论。写入端=两决策位(shop/mandate 的
    # M2 停摆块)在「全量重推导得出腾席无候选」时写 (True,当前段序号);
    # 有候选但不可逆护栏拒=非本结论,不写。命中判定要求标志序号 == 当前
    # 段序号(与 token 序号两道独立,任一不等即失效重推导)。
    cw4_m2_stall_latch: tuple[bool, int] | None = None
    # 帧动作记录 token(载体单一源):None=无记录。写入端=动作执行/逻辑态直写
    # 层确认已执行后写 (动作型名 type().__name__,当前段序号),物理写入
    # 位三处:①生产商店循环(商店画面 op 决策动作 node 执行位);
    # ②序列驱动器(bridge.decide_shop_screen 逻辑态直写位);③生产 prep
    # 循环主环(cw_screen_prep 决策循环 CwActionOpenShopParam/执行器分支合流执行位)。
    # 调用方申报:备战期开店循环
    #(cw_screen_prep 开店分支逐动作调 decide_shop_action)无 token 写入
    # 无段序号置位 ⇒ 域内缓存恒不命中(保守端=现行为,读清单点覆盖
    # 无伪命中),收益面窄化,不接线。读清协议 = decide_shop_action 入口
    # 读取后立即清除(防重复消费);任何调用方首帧(槽空/型外/序号不等)
    # 默认全量重推导。
    cw4_frame_action_record: tuple[str, int] | None = None


    # ===== 账外补充·第二波(实施收尾扫描时按 §6.1 并入的策略侧动态
    # 属性;写入端均在 mandate_v1,消费面含执行侧经访问函数只读)=====
    # M1″ pending 分支(mandate 写,deploy 消费后清 None)。
    cw4_m1p_arm_pending: object = None
    # M1″ 计划载荷 pending(mandate 写):
    # {'sell': [victim 名], 'up': [上序名单],
    # 'trans_domain': 计划时点转型域事实, 'occ': 计划时点板占用数}。
    # 消费半停用(随部署机)(原部署段核对读端已删),现役零读端暴露
    # (已登记申报 = projection_contract.md §4.3);载荷仅作核对与快路径
    # 准入的历史形态申报,**不改卖出仲裁权**(卖谁 = 动作发出点按同一判定集
    # 现算,已登记分工维持,分工裁决)。
    cw4_m1p_plan_pending: object = None
    # 富余段相位标志(同值重入防抖)。
    cw4_must_spend_phase: object = None
    # pop 槽否向理由留决策迹(D-lv7)。
    cw4_pop_slot_why: str = ''
    # 近轮已卖名滚动账(P71 凑息卖去重)。
    cw4_recent_sold_names: list = field(default_factory=list)
    # 素材滞留首见轮账(名 → 首见帧轮次)。
    cw4_stale_seen_rounds: dict = field(default_factory=dict)
    # 本次商店访问已买名单(bridge 清账/op 落账跨层共享)。
    cw4_visit_bought_names: list = field(default_factory=list)
    # 统一发出登记簿(§3,P78 窗口段载体):
    # 名 → (买因,登记轮),买因闭集 = sell_gate.LAUNCH_CAUSES。前身 =
    # T3 垫保簿(N3 闭环登记契约,名→轮 dict)——T3 簿与 ②(b) 压牌库簿
    # 完全合一(编者裁);属性名沿用旧簿:执行侧 cw_op_deploy 按鸭子
    # 属性读本名(部署销/held 暴露,属性契约级接线禁 import 策略模块),
    # 改名 = 供给静默断裂,语义升级由本注释承载。
    # 写端单一源 = sell_gate.register_launch(shop 动作发出点 _emit_buy +
    # mandate.stall_buys_register 兼容 shim);读端单一源 =
    # sell_gate.active_window(窗口段,press/垫保两类,活跃 = 登记轮
    # ==当前轮)/ sell_gate.stall_protect_active(T3 单类视图)。
    # 生命周期四出口(方案 v3 §3.1;①卖出销/②部署销/②′合成销/
    # ③轮界销):consume_on_sell / prune_on_deploy / consume_on_merge /
    # 读端轮界过期;obligation/hold 类 τ=∞ 不轮界过期,由出口①②②′
    # 与换线闭合(close_on_switch)承载。账闭合按五键分键
    #(close_on_sell/deploy/merge/round/switch)落 cw4_counters。
    cw4_fuel_filler_stall_buys: dict = field(default_factory=dict)

    # ===== 备战旗标状态机(S1 开店标志/S2 wanted 残差已删除,由会话标记/
    #       会话循环承接;旗标族字段已删除——本节仅存存活字段)=====
    # 武装段受限访问旗(动作发出帧仲裁;前置动作发出点载体):True = 本武装段已产
    # 出受限访问意图(段 = 出战就绪连续期,失武装帧复位——复位后若再武装且
    # 仍命中,允许新段再访,合法形态例 = 访问内升级抬利息上限)。取值时机 =
    # 前置动作发出点逐帧现读现写。写端单一源 = bridge._launch_front_check。
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

    # ===== 节点作用域与方向状态键(session 作用域键基建批
    #       2026-10-12-prep-shop-workflow-redesign §3.1;读写单一源 =
    #       session_scope 模块函数族,节点作用域键的重置清单唯一所有者
    #       = session_scope._NODE_SCOPE_RESET_TABLE——新键登记进表,
    #       禁各自散写重置逻辑)=====
    # [索引定义] shop_handled = 「本节点已处理」商店会话标记
    # (shop_session §4.1):值 = 最后正常收工处理的节点号二元组
    # (位面,轮)(均 1 基);取值时机 = 正常收工帧现读生效节点序位
    # (写入端单一源 = session_scope.mark_shop_handled);None = 本节点
    # 未处理(局首天然缺省 = 未处理)。跨节点失效 = 节点边界重置清值
    # + 值比对双保险(session_scope.shop_handled_for_current_node)。
    shop_handled: tuple[int, int] | None = None
    # 未消费机会清单(shop_session §4.2):判据通过但被资源拦下的牌
    # 记录(ShopOpportunity 元组序,记录序 = 追加序);正常收工写、
    # 节点边界重置清空;读写单一源 = session_scope 存储函数族。
    shop_opportunities: tuple[ShopOpportunity, ...] = ()
    # [索引定义] node_boundary_last_pos = 节点边界处理函数的判重键:
    # 上次执行边界重置的生效节点序位 (位面,轮)(均 1 基);取值时机
    # = 边界函数执行时现读覆盖(写入端单一源 = session_scope.
    # handle_node_boundary);None = 本局尚未执行过边界处理。
    node_boundary_last_pos: tuple[int, int] | None = None
    # 「第二位面已启动」窗口谓词标志(line_and_upgrade §1.4 时点兜底
    # 载体):node_hist_pos 序位首入 (2,*) 段时置位,单调置位永不复位
    #(不进节点边界重置清单——历史事实非节点作用域态);消费端 = 3.7
    # 时点兜底,读布尔标志(session_scope.plane2_started_of)非位面
    # 元组字面量比较(宪法第 2 条合规的窗口谓词形态)。
    plane2_started: bool = False

    # ===== 方向状态键(契约 B;line_and_upgrade §3 载体落位;
    #       键面归一:锁定线槽 = target_comp〔意向面段,终态单写者 =
    #       session_scope.write_line_lock〕+ 候选快照 + opening_recipe_comp
    #       三键;line_locked_comp 过渡键已删除)=====
    # 候选 top3 快照(线名元组,分数降序——line_select 字典序:环境分级
    # → 持有证据级 → 攻略热度,注册序终局):每帧派生快照非持久状态,
    # 随方向证据签名重算自然更新;锁定写入时**清空**并停算(连带动作
    #③——锁定后读本键恒 = 空集,消费端无需另查锁定旗标)。
    line_candidates: tuple[str, ...] = ()
    # 过渡配方开局面键(契约 B 第三键):部署开局面数据源(P1 过渡
    # 配方,M5/P1),与锁定线槽互不覆写;键面归一后 = 配方对物化链
    # 唯一写端(flow 层 P1 物化写此键,session_scope 不搬运)。每备战
    # 期自写,非节点作用域键(节点边界不重置);P2 起物化链停写(窗口
    # 谓词覆盖),残留值不消费(direction_comp_of 的未锁回落仅在未锁定态
    # 被读,锁定态恒走锁定线)。
    opening_recipe_comp: Comp | None = None
    # 方向证据签名(上次评估签名;line_and_upgrade §3 步骤 2 幂等
    # 跳过的判据):签名同值跳过重算;节点边界重置置 None 失效(强制
    # 下帧重算)。写入端单一源 = session_scope.refresh_line_if_needed。
    line_eval_signature: tuple | None = None
    # [索引定义] p2_pick_baseline = P2 选卡完成侦测基线(frozenset;
    # None = 尚无任何方向重算帧)。取值时机 = **P1 滑动基线**(每次 P1
    # 方向重算帧现读覆写,进 P2 冻结——P1 期间获得的策略〔加场卡〕入
    # 基线不计增长;review-37 R2:P2 首帧快照会把先于首决策帧完成的
    # 开局三选一吞进基线)。写入端单一源 =
    # session_scope._update_p2_pick_done。非节点作用域键(时点兜底
    # 触发腿的单调事实基线,节点边界不清)。
    p2_pick_baseline: frozenset[str] | None = None
    # [索引定义] p2_strategy_pick_done = P2 起首次投资策略获得(「第 10
    # 结点起首次投资策略三选一完成帧」的判读层侦测:active_strategies
    # 相对 baseline 增长)单调旗标;置位后恒真(节点边界不清);消费端
    # = 时点兜底触发腿之二(line_select.evaluate_lock 经 session_scope
    # 传入)。
    p2_strategy_pick_done: bool = False

    # ===== 过渡锁定状态槽(统一保护集迭代 changes/2026-10-15-unified-
    #       protection-set design.md §2.1 新增;买/卖消费点归后续批接线,
    #       本槽现役零行为消费面)=====
    # [索引定义] transition_locked_systems = 过渡域已点亮体系的键集
    # (frozenset[str]):键坐标系 = 四体系键闭集——cw_engine_facts.
    # TRANSITION_TRAITS 三羁绊键(仙舟/列车同行/持续伤害)∪
    # cw_line_facts.SEELE_SYSTEM('希儿系');取值时机 = 策略层决策
    # 入口前置段逐帧现算(写入端单一源 =
    # protection.refresh_transition_locked_systems,bridge.py 两决策
    # 入口在 refresh_line_if_needed 同点调用)。语义 = **幂等只增不减**
    # (design §2.7 取舍:达成过的体系不因掉档失去锁定,防「掉档 →
    # 保护收缩 → 连锁卖」恶性循环,与终局侧「锁后不换」同构);清空点
    # 唯一 = 进位面 2(flow._refresh_direction 配方退场同点)。注意
    # 本槽 ≠ 买面锁定态消费(买面锁 = 终局锁定态
    # line_members_view.locked);点亮判定域 = 持有域(bench ∪
    # deployed),与板面域 seele_system_formed 在「bench 满持未上阵」
    # 帧异判为本设计选定行为。
    transition_locked_systems: frozenset[str] = frozenset()

    # ===== 商店会话读数协议与会话循环键(读写单一源 =
    #       criteria/shop_session 协议函数族与会话循环动作发出点——新键在
    #       session_scope._NODE_SCOPE_RESET_TABLE 显式登记的以表为准)=====
    # [索引定义] gold_ledger = 金位读数账面(shop_session §4.2 读数协议):
    # 真金最优估计;None = 失效待再锚定(节点边界重置/事件级失效触发置
    # None;会话入口实读再锚定覆写)。取值时机 = 会话入口锚定帧 + 记账
    # 钩子增量维护。备战域金位唯一供给(第 3 步攒批/第 7 步凑息/第 4 步
    # 解拦复核金位腿消费)。
    gold_ledger: int | None = None
    # 金位账面的 visit 锚定判重键:上次锚定时的商店访问段序号(对比
    # cw4_segment_serial——生产 op 观察 node 与 sim 驱动器两路均在访问
    # 入口 +1,单一锚定信号);-1 = 本局尚未锚定。非节点作用域键(节点
    # 边界不清——账面本身已清,判重键保留避免边界帧重复锚定日志)。
    gold_ledger_visit_serial: int = -1
    # 序 2 场况插件的会话累计额度(shop_session §2.2 序 2:会话开始帧
    # 快照 deploy_cap − deployed,买入递减,会话内不读现场——店内
    # deployed 恒定,现读每帧同值永不递减)。每 visit 入口重取快照
    # (店内 deployed 不变 ⇒ 与会话开始帧等值)。
    shop_plugin_budget: int = 0
    # 返利族 5 费购买计数(伴生入金:每购买 3 个 5 费角色 +3;局级单调)。
    shop_five_cost_buys: int = 0
    # 读数会话意图标记(shop_session §1 路径③):备战侧读数开店动作发出点
    # 置 True;收工消费——True ∧ 本会话零处理动作 ⇒ 不置标记(非处理性
    # 会话,同节点后续真实会话不受污染)。任意关店出口清位。
    shop_read_intent: bool = False
    # 本 visit 受限访问标记(P70 动作发出帧仲裁授权的溢出段消费;契约 A 豁免
    # 条款):visit 入口按 launch_restricted_session_active 现算快照——
    # 受限 visit 的关店不置标记、不受会话标记覆盖。
    shop_visit_restricted: bool = False
    # 会话内处理动作旗标(收工写标记的判定输入):本会话内任一处理
    # 动作(买/卖/刷)发出即 True;读数会话零处理 + 意图标记 ⇒ 收工
    # 不置标记。
    shop_session_processing: bool = False
    # 持有 3★ 名集快照(合成族失效的帧差检测基线;criteria/shop_session
    # .detect_merge_result_frame 单一写端)。
    held_3star_snapshot: dict = field(default_factory=dict)

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
