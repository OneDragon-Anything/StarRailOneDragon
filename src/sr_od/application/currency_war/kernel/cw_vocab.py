"""货币战争 统一动作词表 + 期望态推进机制面。

**统一词表(unified-action-factory 归一)**:全仓动作单一坐标系、
单一真相源 = 本模块。动作类型总和别名 ``CwAction``(union,非基类——
继承基类已摊平,见下方定义处说明) + 全动作类 + ``CW_ACTION_TYPES``
运行时元组 + ``action_key`` 幂等键函数同居此处;原族B 词表
(kernel/cw_prep_actions,物理槽位 1 基)已停用,该模块现仅承载
备战观察视图 PrepObservation 与采晶矿挑选 kernel 纯函数。坐标系裁定 =
容器槽位表下标(族A 口径,0 基)——动作发出面从容器槽位表
读口直接取下标构造动作;物理槽位号仅存观察写入边与执行坐标边两边界
(物理槽位→槽位表下标换算归执行边纯函数)。例外 = 坐标参数化机械动作(CwActionWearEquipParam/
工具原子类):row/slot 字段按定义 = 画面物理排槽位 1 基(执行器拖点
直取画面 area;字段注释逐类声明)。

**局面表示单一载体 = 容器 GameState**(kernel/cw_game_state,实机真值
记录模型):sim 后端/实机操作链/策略决策同吃容器,域写入 = 观察链漏斗
或逻辑态直写(上报函数族)。旧推演内核帧及其帧→容器合成口已停用
(benchchar-retirement P5)——帧↔容器映射契约正本(game_state/fields.md
§9)随帧失去载体;测试种子 = 测试仓 builder 直写容器域(与观察链同写入口)。

策略为纯规则路线(用户裁定 2026-09-12):规则直接产出动作,决策零模拟
试探。原单步动作应用器 ``simulate``(整帧副本纯函数)已删除——期望态
推进单一源 = 容器逻辑态直写(kernel/cw_action_report 上报函数族
+ 合成升星分支);动作语义验证 = 投影测试(M1,test_shop_projection_logic):
- 现役策略(mandate_v1)决策 = mandate_v1/shop.decide_shop_action
  (容器读,纯规则分支),期望态推进 = 容器逻辑态直写
  (上报函数族,合成升星分支内聚 buy_card 上报)。

字段多由测试构造/重放档案填充;未填(None/默认)时决策安全降级。

**board 模型**(口径统一):
- ``board`` = 已上阵羁绊计数(**全集口径**:factions+flows+independent+星徽装备
  贡献,per-unit 单一源 = ``cw_bond_equips.unit_bond_tags``;观察真值 =
  游戏左面板,观察侧双源仲裁;口径 = 羁绊全集,非主阵营单标签)。
- 容器 GameState 中 board = **派生量**(禁独立手写):front_row/back_row
  行写端挂钩 ``GameState._resync_board_delta`` 增量重算;派生漂移由观察
  覆盖采新(board_derived_adopt,失配告警不响——派生量以观察为真值源)。
  未知身份单位(注册表外/OCR 误读)在容器派生路径**零贡献**(Unit 不存
  阵营,禁 faction 双源),其面板羁绊经观察覆盖采新入账;
  ``cw_bond_equips._recount_board`` 的 faction 兜底归其 faction 字段
  载体(装备授予/sim 后端板面基座刷新),非容器路径口径。
- ``deployed`` = bot 自己跟踪的已上阵角色(含 char_id/star/站位),用于 char_quality 评估
  已上阵的优先角色 + 站位分流。两者在已知身份域一致(deployed 按羁绊全集聚合 == board)。
- CwActionMoveUnitParam 更新 deployed(统一拖动:bench/场上全域,槽位
  落位 = 载荷直落,目标槽有人 = 交换交互);board 不独立写(容器侧
  随行写端挂钩重算)。
- CwActionBuyCardParam 后做 3 合 1 升星(同名同星 ≥3 → 合并为 star+1)。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

# ===== 旧路径转发(过渡 shim)=====
# 共享词汇已迁入语义宿主;下列 import 同时是本模块自身运行时的
# 供给面。旧路径消费仅剩在飞文件,其落库后删除本转发声明;禁新增旧路径消费。
from sr_od.application.currency_war.kernel.cw_bond_equips import (  # noqa: E402
    _recount_board,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (  # noqa: E402
    board_unique_key,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_economy import (  # noqa: E402
    REFRESH_COST_BASE,  # noqa: F401
    XP_CLICK_COST_FALLBACK,  # noqa: F401
    bench_char_cost,  # noqa: F401
    sell_refund,  # noqa: F401
    xp_apply_clicks,  # noqa: F401
    xp_clicks_to_level,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_exec_state import (  # noqa: E402
    BENCH_CAPACITY,  # noqa: F401
    DEPLOYED_BACK_CAPACITY,  # noqa: F401
    DEPLOYED_CAPACITY,  # noqa: F401
    DEPLOYED_FRONT_CAPACITY,  # noqa: F401
    PlaneNodeLedger,  # noqa: F401
    fill_boss_by_position,  # noqa: F401
    get_node_ledger,  # noqa: F401
    ledger_node_type,  # noqa: F401
    ledger_update_plane,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (  # noqa: E402
    _apply_full_bench_merge_buy,  # noqa: F401
    count_merge_material_blocked,  # noqa: F401
    merge_buy_completes,  # noqa: F401
    merge_buy_k,  # noqa: F401
    merge_material_reject_reason,  # noqa: F401
    merge_material_stale_names,  # noqa: F401
    same_star_count,  # noqa: F401
    star_base_copies,  # noqa: F401
    will_merge_on_buy,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_run_allocator import (  # noqa: E402
    MatchOutcome,  # noqa: F401
)


@dataclass
class ShopCard:
    """商店一张牌。"""
    x: int               # 牌位中心 x(购买点击坐标)
    # [索引定义] 物理槽位 = 商店牌行 1-5(左→右;坐标系 = screen_info
    # 「商店牌-N」area 序号,1 基);取值时机 = 生成期快照(进店观察帧,
    # 写入端 = read_shop_cards);0 = 未知(sim/replay 构造缺省)。
    # 语义:牌行是定长 5 格,payload 是紧凑列表(空槽跳过)而游戏买入后
    # 不压缩剩余卡位——紧凑下标 ≠ 物理槽位,执行点击必须按此槽号取
    # 「商店牌-slot」坐标(布局双源同族,bench 版的商店牌行对应)。
    slot: int = 0
    faction: str = "?"   # 阵营(OCR);未知 "?"
    name: str = ""       # 角色名(OCR);未知 ""
    cost: int = 0        # 费用(OCR);未知 0(eval 按默认 3 估,详见 cw_decisions)
    star: int = 1        # 商店里已是几星
    # cost 的信源(费用徽章数字识别批,2026-09-02):'badge'=画面费用徽章直读
    # (费用读数=实付价,星级=读数÷roster 费的倍数 {1,3,9}→1/2/3★);
    # 'roster'=roster 查表(sim/replay 构造路径缺省);
    # 'roster_fallback'=徽章失读/倍数推不出,退回 roster 查表按原费用记 1★。
    # 供金账对账区分「徽章直读」与「查表派生」(2星/3星直出识别缺口闭环,
    # merge_mechanics §2.6/§2.7)。
    cost_source: str = 'roster'


# ===== 统一词表(动作类全集;动作 op 直调上报函数推进/守卫消费) =====
#
# ── 索引字段定义约定(本族一切 idx/slot/index 字段的单一源;AGENTS.md 硬约束
#    「索引/槽位字段必须带定义注释」的正文展开)──────────────────────────
#
# 注释模板(三行,坐标系/取值时机必填;防线字段另加写入端):
#   bench_idx: int
#   # [索引定义] 坐标系: <哪个容器的下标 / 画面物理槽位及基>
#   #            取值时机: <生成期快照(执行期重校验,见 expect) | 生成期=执行期(恒稳) | 事务前快照 | 执行期现读>
#   #            写入端: <发出点函数/模块>(仅 expect/锚定类防线字段必填)
#
# 坐标系(unified-action-factory 归一后单一):bench/deployed 域动作携**容器槽位表
# 下标**(bench = BenchView.slots 下标 / deployed = DeployedView 子表下标,
# 恒稳——生成期索引 = 执行期索引);动作发出面从容器读口
# (bench_view_slots_of/deployed_rows_of 系)直接取下标构造动作。
# 画面物理槽位号(1 基)仅存两边界:①观察写入边(observe/reconcile
# 读链直产 (槽号, Unit) 对);②执行坐标边(deployed 下标→(排,排内
# 槽号)固定双射内联算术,0-3=前排 1-4 / 4-9=后排 1-6)。坐标参数化
# 机械动作(CwActionWearEquipParam/工具原子类,见备战域节)的 row/slot
# 字段 = 画面物理排槽位,属动作参数定义,不在换算边适用范围。

# ``route_tag`` 字段契约(原 CwAction 基类唯一字段,摊平后逐动作类重声明):
# 策略内部路由键(发出分支的构造事实,不随时间漂移、不维护状态),只回答
# 「该次落地该不该清 S1 开店标志」的环路控制路由问题,非卖出资格面(资格
# 单一源 = sell_gate 装配 A)、非放行证据(禁检查器采信)。值域现役 =
# m4_fuel_sell / interest_prep(单帧测试 test_route_tag_whitelist 校验映射表);
# kw_only 缺省 '' ⇒ 构造调用全向后兼容;action_key_exclude metadata =
# 不入动作实例键,幂等粒度 = 行为参数(route_tag 与归因字段同规)。


@dataclass
class CwActionBuyCardParam:
    card: ShopCard
    reason: str = ''   # 买入分类(① 账本 reason 单一源;line/bridge_seed/p2_core/pair/engine/board_focus/emergency/swap/plan;''=旧调用未标)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionSellBenchParam:
    """bench 卖出动作。

    [坐标系] bench_idx = bench 槽位表下标 0-8(定长 9 槽)。

    sim↔生产账本 income 对齐:sim 侧卖出回金按
    ``cost`` 1:1(cw_sim L630);生产真值 = ``sell_refund(star, cost)``
    (2★×3+手续费)。两侧本就不同源——sim 简化只对 1★ 准。补采:
    ``income`` 字段记录**创建时的预期回金**(策略侧算 sell_refund),
    账本/经济对账消费;未传 = None(sim 与旧调用兼容,sim 侧仍按
    自己的 cost 口径执行,不读此字段——它是**记录**不是**指令**)。

    ``expect``(代际校验第三块,激活;''=不校验):
    提案生成时该槽位指向内容的期望名(char_id)——提案生成→应用之间
    槽位内容可能已变,应用时不符 → no-op + stale_proposal 语义
    (对齐 CwActionSellDeployedParam 既有守卫形态)。
    **防线写入端核查(N3②)**:发出点
    = mandate_v1/shop.py 卖出动作发出点(M2 腾席两处/凑利息回拉/funding 变现
    /funding 兜底,逐位带 expect 写入;原「remediation 两补偿器」表述
    无实码对应,全仓 grep 仅本 docstring 自引用,测试面引用同勘误);
    prep 域动作发出点(mandate_v1/entry)构造留 expect 缺省 ''(不校验形态,
    族B 载体本无此字段,缺省即不校验)。
    测试面 = test_sell_window_launch.py(发出登记/窗口段仲裁)与
    test_shop_session_loop.py(筹资形态/兜底穷尽机会清单;原
    test_cw_sell_reason_matrix / TestFundingHoldFallback 两测试随测试批
    并入停用,expect+income 写端校验并入上述两文件)。
    """
    bench_idx: int
    # [索引定义] 坐标系: bench 槽位表下标 0-8(定长 9 槽,空槽 None)
    #             取值时机: 生成期=执行期(槽位表恒稳,卖出置 None 不移位)
    income: int | None = None   # 创建时预期回金(sell_refund 口径;None=未标)
    expect: str = ''           # 代际校验期望名(''=不校验,不符→拒绝)
    reason: str = ''           # 卖出通道记录字段(记录非指令,仿 CwActionLevelUpParam.auth_basis 形态;
    #                            ''=未标,缺省形态)。支撑值 = SELL_BENCH_REASONS
    #                            通道键(r9 争金归因证据层:失败/压线局的卖出
    #                            通道占比是归因下钻的直接证据;纯归因);
    #                            line_switch_collapse 兼孤儿证明标记
    #                            (豁免键集 = SELL_BENCH_ORPHAN_REASONS,
    #                            与发出登记门分离的独立闭集;原检查器
    #                            豁免消费面已停用)。
    convert_reason: str = ''   # 转化类豁免分键(结构化证明键):
    #                            值域收窄为现役两类放行键 ⊂
    #                            SELL_BENCH_CONVERT_REASONS 闭集——
    #                            fuel_victim_protect_demoted(M4 腾席被保
    #                            垫件末位牺牲)/ funding_support_stall_
    #                            convert + funding_hold_liquidated(筹资
    #                            变现两键);仅放行位填写,''=未标恒不豁免。
    #                            line_switch_collapse 不入本字段:孤儿证明
    #                            打标语义与豁免资格耦合留在 reason(
    #                            §4,防窗口段回归洗白),检查器按键分工判定
    #                            (转化类读本字段/孤儿读 reason),迁移期不
    #                            并读零双源。
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


# 转化类卖出豁免键集(同轮买后卖检查的豁免边;检查侧单一源):
# - fuel_victim_protect_demoted: M4 腾席通道,被保垫件为唯一燃料时的
#   放行卖出(为义务买入腾位,金转化成线成员,非净零自旋);
# - funding_support_stall_convert: 支付变现通道卖出被保垫件(为骨架
#   义务筹资,转化类,同上非自旋);
# - funding_hold_liquidated: 支付变现兜底豁免卖出 ③④ 持有件(P78-5
#   最后手段变现;本键覆盖「持有件变现」非 T3 垫件转化,豁免
#   理由同为非自旋——义务筹资的资产重组,凑利息缺口偏好账不授同款豁免);
# - line_switch_collapse: 线账闭合孤儿清算(P78-2a 账闭合事件「线账
#   闭合」:K 支持度重排致义务成员出基座,登记账就地销账,其后通道按
#   P78 INV 清算,1★ 往返净损 0 非自旋,r408 振荡意图不触犯)。键 =
#   通道名(entry 换线归零出口)兼孤儿证明标记(方案审乙′:
#   商店动作发出点仅在「本轮义务登记 ∧ 已出基座」证明在场时打标,授予
#   必须伴随登记簿线账闭合事件,防窗口段回归洗白——证明载体与边界
#   申报)。
# 四键只覆盖「卖出排除面/被保留集登记件」的帧;缺省 '' 恒不豁免
# ——豁免面按分键收敛,禁全开(各键独立消除各自误报窗口;扩键经
# 方案审零阻断放行,出处 = 2026-09-08 同轮交互方案审)。
# 发出侧填充现状:生产动作发出点现无 convert_reason 填充写点
# (T-165 两通道历史填充面已随后续通道重写退役,git 可溯)——字段按
# '' 缺省恒不豁免;line_switch_collapse 仍在役于 reason(孤儿证明
# 打标制 + entry 换线归零通道位)。键集保留 = 检查器豁免面词汇
# 单一源(键语义/豁免边不变;复活填充面先核检查器消费位再接线,
# 可核查面三格:缺省 ''/plain 值/跨轮陈旧恒不豁免)。
SELL_BENCH_CONVERT_REASONS: frozenset[str] = frozenset({
    'fuel_victim_protect_demoted',
    'funding_support_stall_convert',
    'funding_hold_liquidated',
    'line_switch_collapse',
})


# 卖出动作发出点值域闭集(发出登记门:各 CwActionSellBenchParam 动作发出点的 reason 支撑键
# 必须是本集成员;值 = 通道名,与该动作发出点 Emitted.reason/route_tag 同键
# 单一词汇)。新增动作发出点先在此登记再接线(值漂移由动作发出面行为测试暴露,
# 归因消费面按本集分桶)。记录非指令:零行为消费面,资格单一源不变
# (sell_gate 装配 A)。
SELL_BENCH_REASONS: frozenset[str] = frozenset({
    'line_switch_collapse',     # 线账闭合孤儿清算(证明打标制)
    'm4_fuel_sell',             # M4 腾席/压牌库溢出清位(腾席分支构造事实)
    'interest_prep',            # 凑利息卖出(金位缺口触发;十段工序第 8 步节末凑利息承继同键)
    'funding_support',          # 支付筹资卖出(义务买金币位保障)
    'self_rescue_sell',         # 溢出告警自救卖出(十段工序第 0 步态 3;自救扩展面)
    'ore_make_room',            # 晶矿腾位垫件卖出(十段工序第 3 步;垫件谓词过滤后取价值最小)
    'shop_swap',                # 席满买入六步流程卖旧(统一让位优先级迭代 3.2
                                # 置换账替换后的在役取用通道;词 = 机制指认保留名,
                                # 总纲 §2.8 黑话对照——旧店内置换账场景行已退役,
                                # 本键 = 六步流程卖旧动作的发出登记值)
})


# 检查器孤儿豁免键集(同轮买后卖检查的孤儿清算豁免边;**与上方动作发出点
# 值域登记门 SELL_BENCH_REASONS 分离的独立闭集**):两集当前同值
# 但语义不同源——发出登记门的新增值不得静默放大豁免面(豁免面若随
# 登记门生长即成振荡防空洞;同轮买卖振荡零容忍 = 治理
# 立场)。当前值 = line_switch_collapse(线账闭合孤儿清算证明标记,
# 授予须伴随登记簿线账闭合事件)。原三消费位(sim/checks/ledger 与
# sim/checks/suspects 检查器/复盘面同键集)已停用,
#——闭集保留为孤儿证明标记值域登记,禁借道发出登记门。
SELL_BENCH_ORPHAN_REASONS: frozenset[str] = frozenset({
    'line_switch_collapse',
})
# (S1 清键白名单 S1_RESET_ROUTE_TAGS 已停用删除;其双消费位
# 〔mandate_v1 清键路由与 cw_screen_shop 误标检出〕一并拆除,勿复活。)


@dataclass
class CwActionLevelUpParam:
    cost: int        # 本次「购买经验」单击花金(一次点击 = +XP_PER_BUY 经验,非整级;凑够门槛才升级)
    clicks: int = 1
    # 本动作携带的购买击数(整批发出形态;2026-10-17 迭代 design §2.2
    # 单帧原子:判据同帧重评后一次发整批,实付上界 = 发射时授权值)。
    # 缺省 1 = 单击形态(逐帧单击发出的兼容值;执行器按本字段连点)。
    auth_basis: str = ''
    # 授权依据**记录**字段(非指令):
    # 放行分支名(现值域 = criteria/levelup 触发键闭集:'stay_gate'=
    # 带下界>等级升级 / 'natural'=无未完成星级目标自然升级;''=未接线
    # 路径——停留刷新帧无键不发射)。
    # 由动作发出点在**放行时**写入(记录非指令——执行层不读此字段,行为
    # 零改动;sim 账本 actions 侧序列化为 auth 键)。仿
    # CwActionSellBenchParam.income「记录不是指令」形态。
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


# (CwActionDeployMoveParam 已随部署统一批戊批收编删除:统一拖动 = CwActionMoveUnitParam 承载全部 bench→board/换位交互——unified-deploy-order §2.7/§4; 执行 op/report/registry 同批退役。)
@dataclass
class CwActionRefreshShopParam:
    cost: int = 0    # 刷新花费(实机 OCR 补)
    # 触发源**记录**字段(非指令;先例 = CwActionLevelUpParam.
    # auth_basis / CwActionSellBenchParam.income 的「记录不是指令」形态——执行层
    # 不读此字段,行为零改动)。值域(动作发出点单一源 = mandate_v1/shop
    # R1 动作发出点,今日唯一刷新发出点;L2 补位=买卡、L3 末位=升级,
    # 结构上不产刷新动作,槽位留作未来发出点扩展):
    # - 'r1'                 = 利息线门 R1(域外常规承诺账);
    # - 'must_spend_r1_yielded' = 富余段内 R1 切分线(核算账降排序
    #   yielded 支);
    # - '' = 未标(缺省;原引擎 obs 'other' 桶归类已停用)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionCloseShopParam:
    """关店终结动作(/5/6:商店画面的恒可用终结 op)。

    单动作架构下「无动作可做」的表达 = 策略器主动选关店终结
    op,取代旧「空序列 = 决策完成」契约;全函数契约(决策 5)要求动作空间
    至少含一个恒可用终结(决策 6)——本类即商店画面的该终结。执行侧语义
    = 本画面 op 结束、返回主循环(关店点击由动作 op 执行体
    CwActionCloseShopOp 真机械执行:找「按钮-收起」miss = 幂等已关,
    命中 = 点击 + 固定等待 + leave_screen 清场上报);期望态随终结作废,
    由下一次入口观察重建(原单步应用器 ``simulate`` 已停用)。
    """
    reason: str = ''   # 账本 reason(''=默认)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickEventParam:
    """选事件选项(遭遇/补给等事件面单选;投资两屏 = 屏别独立词表类)。

    refresh: 「建议刷新」布尔 = ``refresh_slots`` 非空。判据 = 零阈值
    结构存在性,推导与优势论证见 math_proofs P81。**纯建议**——是否真刷
    由 handler 决定(逐槽计数现读 >0 才点;刷新失败/次数 0 → 照常选当前
    最优,失败安全 = 现状行为)。

    现役身份 = 词表 CwAction union 成员 + ``cw_action_report`` 上报通道
    函数 ``report_action_pick_event_param`` 的参数载体——策略器动作发出面 =
    per-screen Pick 子类(选卡)+ ``CwActionRefreshInvestCardsParam``
    (刷新建议),不经本类。
    """
    option_idx: int
    # [索引定义] 坐标系: 事件选项列表下标(画面选项序,左→右 0 起;
    #             cw_node_obs 读取时已按左→右排序)
    #             取值时机: 生成期快照(decide 时读到的选项序;执行期
    #             handler 按同一画面序点选,选项集跨代际变化时以画面为准)
    reason: str = ""
    refresh: bool = False
    refresh_slots: tuple[int, ...] = ()
    # [索引定义] 坐标系: 策略屏逐卡刷新槽位下标(同 option_idx 坐标系:画面
    #             选项序左→右 0-2,与 handler 逐卡刷新钮/逐卡计数一一对应)
    #             取值时机: 生成期快照(决策期帧级触发判定一次算出)
    #             写入端: 无现役生产端(投资刷新建议载体 =
    #             ``CwActionRefreshInvestCardsParam``);字段随本体保留。
    #             逐卡刷新消费契约参考 = CwScreenInvestStrategy 槽序循环
    #             (逐槽计数现读闸 + 已发出槽集防重入)。
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionSellDeployedParam:
    """卖场上单位(deployed 生命周期开口;不再'只增不减')——契约包 C1。

    [坐标系] deployed_idx = 前排 0-3 / 后排 4+(排内 1 基槽号——
    SellDeployed 坐标域扩展,unified-deploy-order §4 D4-2:值域随
    ``back_capacity_of`` 动态 6-9,扩格帧后排 7-9 可直卖;空槽 None,
    卖出置 None 不移位——索引跨动作组恒稳)。
    """
    deployed_idx: int
    # [索引定义] 坐标系: 前排 0-3 / 后排 4+ 排内 1 基(动态容量 6-9,
    #             back_capacity_of 现读;旧定长 10 截断已随坐标域扩展退役)
    #             取值时机: 生成期=执行期(槽位表恒稳,卖出置 None 不移位)
    income: int | None = None  # 预期回金(sell_refund 口径;None=未标;记录非指令,同 CwActionSellBenchParam)
    reason: str = ''           # 账本 reason(如 'evict_replaced'/'plugin_recycle')
    expect: str = ''           # 遥测观测字段(降级:槽位恒稳后不再承担
                               # 拦截漂移职责,记录生成期期望名供判读对照;
                               # 校验保留——名不符仍是跨代际提案的拒绝信号)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


# (CwActionSwapDeployParam 已随 kernel swap 机器/部署统一批戊批收编删除:场上去留 = 统一部署搜索定型 + 差分执行器,换位交互由统一拖动承载——unified-deploy-order §2.7/§4。)
@dataclass
class CwActionMoveUnitParam:
    """统一拖动(全域移动:front/back/bench 任意源 → 任意目标;部署统一批
    用户指令 2026-10-30「统一拖动角色 Op」——无纯「下场」动作废除,拖拽
    语义全域统一 = 游戏规则:目标空 = 放置,有角色 = 交换)。

    [坐标系] 单坐标系四元组 ``(src_domain, src_slot, dst_domain,
    dst_slot)``,域 ∈ {'front','back','bench'};front 槽 1-4 基 1 /
    back 槽 1-N 动态基 1(N = ``back_capacity_of`` 现值 6-9)/ bench
    槽 0-8 基 0(沿用 ``CwActionSellBenchParam.bench_idx`` 基 0)。
    越界 = fail-closed 拒发(执行 op 静态断言 + 上报口零写双防线)。

    能力全集:上场(bench→场上空槽)/ 换人(bench→场上占槽交换)/
    纯下场(场上→bench 空槽)/ 排错修正(场上→另一排一步)/ 备战席
    内部挪位。消费点 = 差分执行器、出战链、获取让位虚拟评估(详设
    unified-deploy-order §4 动作词表行)。

    ``faction`` 不入动作字段:上报侧从容器槽位表现读派生(统一拖动的
    容器写语义全部按源/目标域现值推演,faction 由 board 行写端挂钩
    重算承载,无需载荷携带)。
    """
    src_domain: str
    # 源域('front'|'back'|'bench')
    src_slot: int
    # [索引定义] 坐标系: front 1-4 / back 1-N 动态 / bench 0-8(基 0)
    #             取值时机: 生成期快照(发出点从容器读口现取;执行与
    #             上报按同一坐标直址,槽位表恒稳语义)
    dst_domain: str
    dst_slot: int
    # [索引定义] 坐标系: 同 src_slot(域内 1 基,bench 例外 0 基)
    #             取值时机: 生成期快照
    reason: str = ''   # 归因记录字段(非指令;''=未标)
    expect: str = ''   # 代际校验期望名(''=不校验,不符→拒绝;源槽
    #             期望名——与 CwActionSellBenchParam.expect 同形)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


Action = (CwActionBuyCardParam | CwActionSellBenchParam | CwActionLevelUpParam | CwActionRefreshShopParam | CwActionCloseShopParam
          | CwActionSellDeployedParam | CwActionMoveUnitParam)


# ===== 统一词表·备战域动作(类体逐字保留,基类引用翻 CwAction)=====
#
# 通用坐标系声明(装备域两类目标,全族共用):
# - 装备源件 = owned 装备网格内 icon,按 ``item_name`` 机械现读定位
#   (执行坐标边合法现读;坐标不入动作——网格 reflow 会使坐标失真,
#   名字定位是唯一稳锚)。
# - 角色目标槽位 ``row``/``slot``:row ∈ 'front'|'back'(画面物理排);
#   slot = 画面物理槽位 1 基(前排 1-4 / 后排 1-选档 N;非列表下标)。
#   取值时机 = 生成期快照(动作发出点从备战观察/容器槽位表现读;同一 visit
#   内 tracked 账随动,槽位跨动作组恒稳——置 None 不移位坐标系);

@dataclass
class CwActionCollectOreParam:
    """点晶矿(R4 坐标参数化机械动作:载荷 = 有序晶矿坐标点击列表)。

    ``points`` = 按点击顺序排列的晶矿心坐标 (x, y)(1080p 游戏空间)。挑选
    逻辑(大晶矿优先/上界截断)归决策侧 kernel 单一源 = :func:`cw_prep_actions
    .select_ore_clicks`,动作发出点调用之;执行器纯机械逐个点,零读屏
    零排序。逻辑态按载荷精确摘晶矿(坐标匹配,容器 spheres 域)。
    """
    points: tuple[tuple[int, int], ...] = ()
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionOpenBoxParam:
    """开补给箱(点「开启」→ 弹武装箱 overlay;开箱即腾席)。slot=None → 第一箱。"""
    slot: int | None = None   # [索引定义] slot = 备战栏画面物理槽位 1 基(area 序,坐标参数化机械动作族同系,screens README §4 二分);取值时机 = 发出期快照(决策半按容器 bench kind 槽位现算);None = op 内按 game state 容器现算首件槽(双出口守卫断言:gs 缺席/容器无该 kind 首槽 → AssertionError)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionOpenTomeParam:
    """开秘密典籍(点槽一次即开:单击即弹星徽四选一〔用户确认 2026-09-25 游戏实际口径〕;开典籍即腾席+外循环分发 CwScreenBookcard 接管选卡)。

    建档:投资策略「秘密典籍」给的红金典籍道具占备战席 1 槽(类补给箱);
    选卡决策在 CwScreenBookcard(板上阵营匹配),本动作只负责把典籍点开。slot=None → 第一典籍。
    """
    slot: int | None = None   # [索引定义] slot = 备战栏画面物理槽位 1 基(area 序,坐标参数化机械动作族同系,screens README §4 二分);取值时机 = 发出期快照(决策半按容器 bench kind 槽位现算);None = op 内按 game state 容器现算首件槽(双出口守卫断言:gs 缺席/容器无该 kind 首槽 → AssertionError)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionOpenBookcardParam:
    """开书册卡(点槽「开启」→ 弹专家邀请函五选一;开卡即腾席)。

    书册卡 = 备战席占槽道具(与补给箱/秘密典籍并列第三件;与
    CwActionOpenBoxParam/CwActionOpenTomeParam 同签名)。选卡决策不在
    本执行链——点完开启本动作即返回主循环,专家邀请函弹窗由外循环按画面分发
    ``CwScreenExpertInvite`` 选卡(选卡决策单一源 = kernel
    ``cw_events.choose_expert_index``,选卡决策收拢 kernel 单一源)。
    动作发出点 = 策略器 entry ① prep 实体面卡片分支(容器 bench 槽位 kind
    'bookcard' 触发;原「备战环入口清场段 ``cw_screen_prep._clear_prep_cards``
    代发」已按用户裁定 2026-09-19 撤销——开卡时机归策略实现管)。
    终结动作(弹专家邀请函 = 引入新事实,返回主循环重新观察)。slot=None → 第一张书册卡。
    """
    slot: int | None = None   # [索引定义] slot = 备战栏画面物理槽位 1 基(area 序,坐标参数化机械动作族同系,screens README §4 二分);取值时机 = 发出期快照(决策半按容器 bench kind 槽位现算);None = op 内按 game state 容器现算首件槽(双出口守卫断言:gs 缺席/容器无该 kind 首槽 → AssertionError)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionWearEquipParam:
    """穿装备(装备库 owned 件 → 目标角色物理槽位;R2 穿戴原子通路)。

    计划构造 = kernel ``build_equip_wear_plan``(决策侧逐帧现算);发出序即执行序(决策核逐帧取首项)。逻辑态 =
    ``obs.owned_equips`` 摘件(视觉域,与 CwActionOpenBoxParam/CwActionOpenTomeParam 同形);
    穿没穿归观察写入边对账(裁决 3 零比对出生:体内零 CV-diff 验穿)。
    ``char_name`` = 目标角色注册名('' = front-only 回退步,拖点 =
    前排空槽 avatar,与 EquipWearStep 契约同形)。
    """
    item_name: str
    char_name: str
    row: str            # 'front' | 'back'(见上方通用坐标系声明)
    slot: int           # 画面物理槽位 1 基(前排 1-4 / 后排 1-N)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionFurnaceUseParam:
    """冶金炉(R8 按消耗品各立类;双模式)。

    - target_kind='equip':拖装备 = 原地变异同类型随机(target =
      装备库 owned 件,``item_name``;上报 = rand 采样替换——同类别池
      write_logic_rand 合并单笔写,采样池 = ``cw_sim_equips.furnace_reroll``
      同源,写端 = ``cw_action_report.tool_use``);
    - target_kind='char':拖角色 = 全拆 + 每件变异随机(target =
      角色槽位,``row``/``slot``;①equips 采样链 rand 合并写 + ②行域
      穿戴清空 logic 写;变异面不走获得链不触发获得回调)。
    """
    target_kind: str    # 'equip' | 'char'(作用对象模式;值域封闭)
    item_name: str = ''  # target_kind='equip':装备库 owned 件名
    row: str = ''        # target_kind='char':见上方通用坐标系声明
    slot: int = 0        # target_kind='char':画面物理槽位 1 基
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPrivilegeCardUseParam:
    """特权赋予卡(R8;两条分支)。

    - target_kind='equip'(库存分支,现役执行分支):确定变换 = target 件
      名替换为对应·特权名(映射单一源 = ``cw_effect_inventory.
      privilege_counterpart``;上报 = equips 合并单笔写 = 移除工具 ∧
      变换同笔,写端 = ``cw_action_report.tool_use``);
    - target_kind='char'(拖角色入账分支):**fail-closed 不支持**(用户裁定
      2026-09-21 按不能拖角色处理待实机测试)——上报侧收到 char 分支 =
      零写留存证据(tool_privilege_worn_unsupported);判据面现役只产库存分支,
      穿域桥 ``transform_worn_equip_to_privilege`` 留在原位。
    """
    target_kind: str    # 'equip' | 'char'(值域封闭,同 CwActionFurnaceUseParam)
    item_name: str = ''  # target_kind='equip':被变换的进阶成品件名
    row: str = ''        # target_kind='char':见上方通用坐标系声明
    slot: int = 0        # target_kind='char':画面物理槽位 1 基
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionWrenchUseParam:
    """拆装扳手(R8):target = 角色槽位(取下该角色全部穿戴,装备归属
    面回区);工具消耗品 −1。上报 = 两笔 logic 合并写(equips = 移除工具
    ∧ 追加穿戴件;行域穿戴清空),写端 = ``cw_action_report.tool_use``。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPrecisionWrenchUseParam:
    """精密拆装扳手(R8):target = 角色槽位(同 CwActionWrenchUseParam);无限次用,
    工具库存面不递减(上报两笔 logic 同扳手,equips 不移除工具;重复获得改
    +1 金 = 贡献算术,获得回执窗已登记)。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionStaffProjectorUseParam:
    """员工投影仪(R8 投影仪按型号两类之一):target = 角色槽位
    (在备战席创造该角色 1 星复制);费用门 = 3 费及以下(门表单一源 =
    ``cw_affix_effects`` 投影仪费用门行),门由动作发出点判据面覆盖。上报 =
    复制走获得链 ``gain_character``(落位 → 回调 → 3 合 1 升星判断;
    复制触发三合一 = 口述·权威 2026-09-21)+ equips 移除工具合并分支,
    写端 = ``cw_action_report.tool_use``(费用门注册表现读前置查 =
    防御纵深)。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPerfectProjectorUseParam:
    """完美投影仪(R8 投影仪按型号两类之二):target = 角色槽位
    (同 CwActionStaffProjectorUseParam 但无费用门;上报同走获得链)。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionLuckyTokenUseParam:
    """好运令牌(R8):拖到角色 → 从其推荐进阶装备中获得一件。

    ⚠️ 动作发出点待办(裁决 1/R9 纪律):作用对象判据面现役 fail-closed
    永不进准入(``cw_equip_env.evaluate_tool_actions`` rc_missing 拒因
    已登记)——类随族立档 + 注册行,动作发出点禁无判据发出;判据面建模批
    补档(知识缺口登记 = ``flow/action-logic-state.md`` §7 好运令牌行)。
    上报侧 = 零写留存证据(tool_token_not_admitted 注记,写端随 R9 判据批)。
    """
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionOpenShopParam:
    """开商店意图(EnsureShop 意图停用后的承接形态;唯一普通形态)。

    显式开店 → 流程层编排商店访问(open_shop 幂等开店 → 商店画面 op:
    入口观察 → decide_shop_action 逐动作循环,关店并入进 op)。

    受限会话(出战就绪 ∧ 金超利息线)同走本普通开店形态:前置动作发出点发出
    普通开店动作,访问内消费 = 策略侧自限(flow.decide_shop_action 提案后
    经 kernel launch_arbitration_gate 谓词检;分层依据 = flow/README.md
    §1 决策控制分层铁律)——受限访问标记
    字段随动作发出帧仲裁段停用删除,本类 = 唯一开店动作形态。
    """
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionStartBattleParam:
    """出战(环出口;含未达上限确认)。零转移验证机械单发:点击序列发出即返回主循环
    (未发出 = 找不到按钮返 False),转移与否由返回后下一帧观察裁决。CwActionStartBattleParam 豁免屏蔽。"""
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


# 动作全集白名单(统一词表运行时元组;注册完备测试的遍历单一源;消费 = 逐类断言注册表解析可命中。新动作加入全集时同步此处——漏登记
# ⚠️ 教训(原 PREP_ACTION_TYPES 先例):**新增动作必须同步登记本白名单**
# —— 选择族动作化(策略器终态契约;落地 landing §3.1 纯新增零消费,
#       decide 接线归终态切换批)=====

# 选择族公共契约(原 PickOption 基类,摊平后 12 个叶子逐类重声明 idx/reason):
# ``idx`` = 该画面候选槽位序号,坐标系 = 对应 payload 槽 options 列表下标
# (0 基,与写槽时 OCR 顺序一致,槽位表恒稳);取值时机 = 生成期快照。
# 12 类全量在注册表分发(统一 pick-op 分发并入,零上报例外撤销):执行 op =
# ``CwActionPickXxxOp``(机械链 = 选中 → 确认/点卡即选,op 内自上报,零写);
# 确认后容器写(chosen_*/Confirm* 到账)留在画面 op;``PickExpertInviteParam.idx``
# = -1 语义 = 现金为王(非候选槽下标)。


@dataclass
class CwActionPickEncounterParam:
    """遭遇节点选择(策略层载体 =
    ``strategies/impl/mandate_v1/encounter_pick.py`` ``EncounterPickDecision``
    的动作包装;刷新建议另发 CwActionRefreshNodeOptionsParam)。"""
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickSupplyParam:
    """补给节点选择(策略层载体 = ``strategies/impl/mandate_v1/supply.py``
    ``SupplyDecision`` 的动作包装;刷新建议另发 CwActionRefreshSupplyParam)。

    开出内容载荷(确定性通道,照 PickInvest 载荷扩展先例):``char_name`` = 选中列角色名
    (read_supply_options roster 校验产物;'' = 列无角色/兜底点卡路径);
    ``norm_item`` = 选中列首件装备归一件名(``normalize_registry_equip_name``
    注册表级分层归一,OCR 原始名不静默改写由 handler 持有;'' = 未解析);
    ``extra_norm_items`` = 列内附加装备归一件名元组(画面 y 序 = norm_item
    之后;'' 元素 = 该件归一未解析,上报侧逐件 fail-closed;默认 () = 单
    装备布局,既有构造点零变化)。
    三字段不入动作实例键(归因载荷不改变动作身份,``route_tag`` 先例);
    动作 op 确认点击后立即上报,按实际开出内容应用(单位入账分支 + 装备入账分支
    0..n 件 + 后果链,即时单相,design §2.0B)。
    """
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    char_name: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})
    norm_item: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})
    extra_norm_items: tuple[str, ...] = field(default=(), kw_only=True,
                                              metadata={'action_key_exclude': True})
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickInvestStrategyParam:
    """投资策略屏选择(投资策略 3 选 1;投资环境屏 = CwActionPickInvestEnvParam)。

    拆类(用户裁定 2026-09-21:原两屏共用一词表类 + source 字符串运行时
    分流是绕路,每屏一词表类,上报族「一类恰一具名函数」机械规约回归,
    屏别分流靠类型)。``norm_name`` = 选中卡归一规范名
    (``normalize_invest_name``,OCR 原始名不静默改写由 handler 持有)。
    动作 op 点完确认**立即自上报完整结果**(写入 game state;用户裁定
    「选择动作执行就按成功处理,没有选到就是代码 bug」,原分步上报废除)。
    norm_name/route_tag 不入动作实例键(归因载荷不改变动作身份,同
    route_tag 先例)。
    """
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    norm_name: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickInvestEnvParam:
    """投资环境屏选择(投资环境 3 选 1;投资策略屏 = CwActionPickInvestStrategyParam)。

    拆类与上报语义同 CwActionPickInvestStrategyParam:点完确认立即自
    上报完整结果(获得投资环境 → gain_invest_env 整链)。
    """
    idx: int
    # [索引定义] 坐标系: 同 CwActionPickInvestStrategyParam.idx。
    reason: str = ''
    norm_name: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickMegastarParam:
    """盛会之星选择(替代 MegastarPick)。"""
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickPartnerParam:
    """列车同行伙伴选择(替代 PartnerPick)。"""
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickPlannerParam:
    """骇入策划选择(替代 PlannerPick)。"""
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickStarTomeParam:
    """星徽秘典选择(替代裸 int 返回)。"""
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickWishTrialParam:
    """祈愿试炼选择(替代裸 int 返回)。"""
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickBoxCardParam:
    """武装箱选择(替代裸 int 返回)。"""
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickFortuneParam:
    """命运卜者强化三选一选择(契约扩员 12→15 新增)。"""
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickExpertInviteParam:
    """专家邀请函选卡选择(契约扩员 12→15 新增)。

    [索引定义] idx 取值域扩展:0..3 = 候选卡区下标(卡-1..卡-4);
    **-1 = 现金为王**(经济兜底,非候选卡槽下标;kernel
    ``choose_expert_index`` 契约原样;动作 op 据此取容器 ``cash_point``
    点「卡-现金为王」区,op-layer.md §1.1 :35 坐标单一真相源 = 观察上报)。
    """
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionRefreshNodeOptionsParam:
    """遭遇节点刷新建议(策略层载体 =
    ``strategies/impl/mandate_v1/encounter_pick.py``
    ``EncounterRefreshSuggestion`` 的动作包装):策略建议点击
    节点刷新钮。encounter 刷新链 = 同访问重决策——发出本动作前须以重读
    产物覆盖写槽再决策(刷新链分屏形态申报,禁沿用旧槽内容)。"""
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionRefreshSupplyParam:
    """补给节点刷新建议(策略层载体 = ``strategies/impl/mandate_v1/supply.py``
    ``SupplyRefreshSuggestion`` 的动作包装):supply 刷新链 =
    发出后返回主循环重入型(重入访问走常规写槽→决策起点链)。"""
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionRefreshInvestCardsParam:
    """投资逐卡刷新建议(投资两屏刷新动作载体;**纯建议**)——
    是否真刷由 handler 决定(逐槽计数现读 >0 才点,失败安全 = 现状)。
    判据来源:策略屏 = 策略层 invest_strategy 刷新动作集(29 号稿 §4);
    环境屏 = invest_env 刷新三态(28 号稿 §4,slots = 全帧槽位哨兵)。

    [索引定义] slots = 待刷新投资卡槽位序号集,坐标系 = 投资界面卡槽
                物理排位(0 基);取值时机 = 生成期快照。三闸点击链
                留在画面 handler。"""
    slots: tuple[int, ...] = ()
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


#: CwActionObsParam.scope 值域闭集(观察口径单一源;消费端 = 备战决策环
#: 分支判等,in_place 走执行器、outer_loop 拦截并返回主循环;F3 静态校验同取本源)。
OBS_SCOPES: frozenset[str] = frozenset({'in_place', 'outer_loop'})


@dataclass
class CwActionObsParam:
    """重观察动作(策略发出 → 请求新鲜观察,口径由 ``scope`` 选择)。

    - ``scope='in_place'``(缺省):**当前画面重新观察上报**——执行体 =
      宿主画面 op 的 heavy 观察链重跑(漏斗直写容器 = 观察边界对账,
      「以实际观察为准」),决策环原地续跑:访问不重启、段序号不置位、外循环
      零往返。帧代次标注 'full'(方向重估触发,同入口帧;贵段消费侧有
      每 game-round 恰一次键守卫限频)。重观察发现事件 overlay 在场 =
      抛 CwObsOverlayBail 返回主循环重新分发(画面识别与路由归外循环,
      环内不消化;捕获点 = ``cw_screen_prep.act``)。
    - ``scope='outer_loop'``:**返回主循环重新观察**——决策环在执行器
      之前分支拦截(不进执行器、不进动作注册表、不写续段
      token/动作记录),round_success(wait=1.0) 返回主循环重新观察。
      本口径并入原 ``HoldFrame`` 空动作发出帧通道(用户裁定 2026-09-20
      HoldFrame 删除:两通道同为「观察请求」,口径差异收进参数;空发出
      语义 = 本帧无动作可发,返回主循环让外循环重判/等待,自旋防护 = 返回后
      归外循环 stall 防线)。

    零容器动作写语义:in_place 口径的容器更新通道 = 观察漏斗本体
    (read_game_state 直写),``report_action_obs_param`` = 零写族占位
    (命名规约完备测试对象)。现役接线域 = 备战决策环(CwScreenPrep);
    in_place 在其他决策域发出 = 宿主能力缺失 AssertionError 响亮暴露
    (策略器 bug)。
    """
    scope: str = 'in_place'   # 观察口径,值域闭集 = OBS_SCOPES('in_place' 环内重观察 / 'outer_loop' 返回主循环重新观察)
    reason: str = ''   # 归因记录字段(非指令;''=未标)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


# (HoldFrame 已删除,用户裁定 2026-09-20:空动作发出帧通道并入进
#  CwActionObsParam(scope='outer_loop'),两观察口径统一为一个动作类型,
#  旧形态已移除。)

# 动作类型总和(union 类型别名,**非基类**;继承基类已摊平,每动作一个
# 独立 dataclass。本名仅为既有 ``CwAction`` 注解面与 ``isinstance(x,
# CwAction)`` 判定的零改动兼容保留;Python 3.10+ union isinstance 合法)。
CwAction = (
        CwActionBuyCardParam | CwActionSellBenchParam | CwActionLevelUpParam |
        CwActionRefreshShopParam | CwActionCloseShopParam | CwActionSellDeployedParam |
        CwActionMoveUnitParam | CwActionCollectOreParam | CwActionOpenBoxParam | CwActionOpenTomeParam |
        CwActionOpenBookcardParam | CwActionWearEquipParam | CwActionFurnaceUseParam | CwActionPrivilegeCardUseParam |
        CwActionWrenchUseParam | CwActionPrecisionWrenchUseParam | CwActionStaffProjectorUseParam | CwActionPerfectProjectorUseParam |
        CwActionLuckyTokenUseParam | CwActionStartBattleParam | CwActionOpenShopParam | CwActionPickEventParam |
        CwActionPickEncounterParam | CwActionPickSupplyParam | CwActionPickInvestStrategyParam | CwActionPickInvestEnvParam | CwActionPickMegastarParam |
        CwActionPickPartnerParam | CwActionPickPlannerParam | CwActionPickStarTomeParam | CwActionPickWishTrialParam |
        CwActionPickBoxCardParam | CwActionPickFortuneParam | CwActionPickExpertInviteParam |
        CwActionRefreshNodeOptionsParam | CwActionRefreshSupplyParam | CwActionRefreshInvestCardsParam |
        CwActionObsParam
)
# ——漏登记时注册表解析拒「动作词表外类型」(AssertionError 响亮暴露),
# 动作从未真正执行(CwActionOpenTomeParam 曾漏登记,数百次拒绝被误读为
# 执行失败;登记是入口门)。
CW_ACTION_TYPES: tuple = (
    CwActionBuyCardParam, CwActionSellBenchParam, CwActionLevelUpParam, CwActionRefreshShopParam,
    CwActionCloseShopParam, CwActionSellDeployedParam,
    CwActionMoveUnitParam,
    CwActionCollectOreParam, CwActionOpenBoxParam, CwActionOpenTomeParam, CwActionOpenBookcardParam,
    CwActionWearEquipParam,
    CwActionFurnaceUseParam, CwActionPrivilegeCardUseParam, CwActionWrenchUseParam, CwActionPrecisionWrenchUseParam,
    CwActionStaffProjectorUseParam, CwActionPerfectProjectorUseParam, CwActionLuckyTokenUseParam,
    CwActionStartBattleParam,
    CwActionOpenShopParam,
    # 选择族动作化(终态契约;CwActionPickFortuneParam/
    # CwActionPickExpertInviteParam = 契约扩员新增;
    # CwActionPickEquipParam 已停用删除——选择装备屏不存在,勿复活)
    CwActionPickEncounterParam, CwActionPickSupplyParam, CwActionPickInvestStrategyParam, CwActionPickInvestEnvParam, CwActionPickMegastarParam, CwActionPickPartnerParam,
    CwActionPickPlannerParam, CwActionPickStarTomeParam, CwActionPickWishTrialParam, CwActionPickBoxCardParam,
    CwActionPickFortuneParam, CwActionPickExpertInviteParam,
    CwActionRefreshNodeOptionsParam, CwActionRefreshSupplyParam, CwActionRefreshInvestCardsParam,
    CwActionObsParam,
)

#: 选择族收敛单表(终态契约 §2.7):pick 子类型单表(12 个;原 13 个,
#: CwActionPickEquipParam 随选择装备屏误判停用删除),供 handler 分派/
#: 注册完备测试遍历(三刷新动作走各自既有点击链不入本表;Obs = 观察请求
#: 语义,不属选择族)。
PICK_ACTION_TYPES: tuple = (
    CwActionPickEncounterParam, CwActionPickSupplyParam, CwActionPickInvestStrategyParam, CwActionPickInvestEnvParam, CwActionPickMegastarParam, CwActionPickPartnerParam,
    CwActionPickPlannerParam, CwActionPickStarTomeParam, CwActionPickWishTrialParam, CwActionPickBoxCardParam,
    CwActionPickFortuneParam, CwActionPickExpertInviteParam,
)


def action_key(action: CwAction) -> str:
    """动作实例键(屏蔽计数粒度 = 动作类型 + 参数;CwActionSellBenchParam(3) 与 CwActionSellBenchParam(5) 各自计数)。

    带 ``action_key_exclude`` metadata 的字段不入键(现役 =
    CwActionSellBenchParam.reason 卖出归因 + CwAction.route_tag 发出分支路线标签
    [旗标状态机 §3.3]):幂等粒度 = 行为参数,归因/路由标签不改变动作实例
    身份——同槽位不同归因是同一动作,禁拆成两个幂等键。
    """
    import dataclasses

    if dataclasses.is_dataclass(action):
        params = dict(vars(action))
        for f in dataclasses.fields(action):
            if f.metadata.get('action_key_exclude'):
                params.pop(f.name, None)
        if not params:
            return type(action).__name__   # 无字段 dataclass(CwActionStartBattleParam 等)→ 裸名
        return f'{type(action).__name__}({params})'
    return type(action).__name__
# (席位同步聚合口已停用:
#  动作写主域(容器逻辑通道)即同步,第二账无可同步;执行点同步分支
#  同批删除,合成仿真自主域工作副本构造(cw_action_report 族)。)
# ===== 布局未知态的策略侧支撑(15 号稿审查修订)=====
# 布局未知态计数复位的槽式转发供 strategies 面消费(strategies 合法桶 =
# data/kernel/app,不得直依 obs:obs 侧在 resolve 时注册真实现)。

_layout_unknown_reset: Callable[[], None] | None = None


def reset_layout_unknown_state() -> None:
    """复位布局未知态计数(槽式转发;obs.cw_back_layout 在 resolve 时
    注册真实现,未注册=noop。新局起点由策略 create_session 调用,
    防跨局残留让开局提前吃冻结)。"""
    fn = _layout_unknown_reset
    if fn is not None:
        fn()



