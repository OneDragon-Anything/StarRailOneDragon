"""货币战争 统一动作词表 + sim 推演内核机制面。

**统一词表(unified-action-factory 批2b 归一)**:全仓动作单一坐标系、
单一真相源 = 本模块。动作类型总和别名 ``CwAction``(union,非基类——
继承基类已摊平,见下方定义处说明) + 全动作类 + ``CW_ACTION_TYPES``
运行时元组 + ``action_key`` 幂等键函数同居此处;原族B 词表
(kernel/cw_prep_actions,物理槽位 1 基)已随归一退役,该模块现仅承载
备战观察视图 PrepObservation 与采晶矿挑选 kernel 纯函数。坐标系裁定 =
容器槽位表下标(族A 口径,0 基;ADR-0316/0392)——发射面从容器槽位表
读口直接取下标构造动作;物理槽位号仅存观察写入边与执行坐标边两边界
(design.md §2.6 换算归属)。例外 = 坐标参数化机械动作(CwActionWearEquipParam/
工具原子类):row/slot 字段按定义 = 画面物理排槽位 1 基(执行器拖点
直取画面 area;字段注释逐类声明)。

**局面表示单一载体 = 容器 GameState**(kernel/cw_game_state,实机真值
记录模型):sim 引擎/实机操作链/策略决策同吃容器,域写入 = 观察链漏斗
或逻辑态直写(上报函数族)。旧推演内核帧及其帧→容器合成口已随
benchchar-retirement P5 退役——帧↔容器映射契约正本(game_state/fields.md
§9)随帧失去载体;测试种子 = 测试仓 builder 直写容器域(与观察链同写入口)。

策略为纯规则路线(用户裁定 2026-09-12):规则直接产出动作,决策零模拟
试探。原单步动作应用器 ``simulate``(整帧副本纯函数)已删除——期望态
推进单一源 = 容器逻辑态直写(kernel/cw_action_report 上报函数族
+ 合成升星腿);动作语义验证 = 投影直锁(M1,test_cw_shop_projection_logic):
- 现役策略(mandate_v1)决策 = mandate_v1/shop.decide_shop_action
  (容器读,纯规则分支),期望态推进 = 容器逻辑态直写
  (上报函数族,合成升星腿内聚 buy_card 上报)。

字段多由 sim 环境剧本/重放档案构造填充;未填(None/默认)时决策安全降级。

**board 模型**(ADR-0312 口径统一):
- ``board`` = 已上阵羁绊计数(**全集口径**:factions+flows+independent+星徽装备
  贡献,per-unit 单一源 = ``cw_bond_equips.unit_bond_tags``;观察真值 =
  游戏左面板,观察侧双源仲裁 = ADR-0417;口径 = 羁绊全集,非主阵营单标签)。
- 容器 GameState 中 board = **派生量**(禁独立手写):front_row/back_row
  行写端挂钩 ``GameState._resync_board_delta`` 增量重算;派生漂移由观察
  覆盖采新(board_derived_adopt,安灯不响——派生量以观察为真值源)。
  未知身份单位(注册表外/OCR 误读)在容器派生路径**零贡献**(Unit 不存
  阵营,禁 faction 双源),其面板羁绊经观察覆盖采新入账;
  ``cw_bond_equips._recount_board`` 的 faction 兜底归其 faction 字段
  载体(装备授予/sim 代理面),非容器路径口径。
- ``deployed`` = bot 自己跟踪的已上阵角色(含 char_id/star/站位),用于 char_quality 评估
  已上阵的优先角色 + 站位分流。两者在已知身份域一致(deployed 按羁绊全集聚合 == board)。
- CwActionDeployMoveParam 更新 deployed(槽位落位 = 载荷 (to_row, to_slot)
  直落,ADR-0392 坐标系;目标槽有人 = 交换交互);board 不随
  CwActionDeployMoveParam 独立写(旧 ``_recount_board`` 写端已退役,容器侧随行写端挂钩重算)。
- CwActionBuyCardParam 后做 3 合 1 升星(同名同星 ≥3 → 合并为 star+1)。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

# ===== 候裁9 词汇迁移·旧路径转发(过渡 shim)=====
# 本批按定谳记录把共享词汇迁入语义宿主;下列 import 同时是
# 本模块自身运行时的供给面。旧路径消费仅剩并行在飞批文件,待其落库
# 后由收尾段 sweep 改指新居并删除本转发声明;禁新增旧路径消费。
from sr_od.application.currency_war.kernel.cw_bond_equips import (  # noqa: E402
    _recount_board,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (  # noqa: E402
    board_unique_key,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_economy import (  # noqa: E402
    DIFFICULTY_HP_TABLE,  # noqa: F401
    HP_SAFE_THRESHOLD,  # noqa: F401
    REFRESH_COST_BASE,  # noqa: F401
    XP_CLICK_COST_FALLBACK,  # noqa: F401
    bench_char_cost,  # noqa: F401
    effective_hp_threshold,  # noqa: F401
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
    bench_place,
    deployed_slot_no,
    fill_boss_by_position,  # noqa: F401
    get_node_ledger,  # noqa: F401
    ledger_node_type,  # noqa: F401
    ledger_update_plane,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (  # noqa: E402
    _apply_full_bench_merge_buy,  # noqa: F401
    _merge_bench,
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
    # 「商店牌-slot」坐标(布局双源同族,ADR-0646 bench 版的商店牌行对应)。
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


# ===== 统一词表(动作类全集;sim 引擎推进/执行链逻辑态直写/守卫消费) =====
#
# ── 索引字段定义约定(本族一切 idx/slot/index 字段的单一源;AGENTS.md 硬约束
#    「索引/槽位字段必须带定义注释」的正文展开)──────────────────────────
#
# 注释模板(三行,坐标系/取值时机必填;防线字段另加写入端):
#   bench_idx: int
#   # [索引定义] 坐标系: <哪个容器的下标 / 画面物理槽位及基>
#   #            取值时机: <生成期快照(执行期重校验,见 expect) | 生成期=执行期(恒稳) | 事务前快照 | 执行期现读>
#   #            写入端: <发射点函数/模块>(仅 expect/锚定类防线字段必填)
#
# 坐标系(unified-action-factory 批2b 归一后单一):bench/deployed 域动作
# 携**容器槽位表下标**(定长槽位表 ADR-0316/0392,下标恒稳——生成期索引 =
# 执行期索引);发射面从容器读口(bench_view_slots_of/deployed_rows_of 系)
# 直接取下标构造动作。物理槽位号(Unit.slot / BenchSlot 内嵌 Unit.slot
# 信息位,1 基)仅存两边界,
# 各只允许一处换算函数:①观察写入边(observe/reconcile 写链);
# ②执行坐标边(executor 单点;kernel 助手 = ``cw_exec_state
# .deployed_row_slot``/``deployed_idx_of``)。坐标参数化机械动作
# (CwActionWearEquipParam/工具原子类,见备战域节)的 row/slot 字段 = 画面物理排槽位,
# 属动作参数定义,不在换算边辖域。

# ``route_tag`` 字段契约(原 CwAction 基类唯一字段,摊平后逐动作类重声明):
# 策略内部路由键(发射分支的构造事实,不随时间漂移、不维护状态),只回答
# 「该次落地该不该清 S1 开店闩」的环路控制路由问题,非卖出资格面(资格
# 单一源 = sell_gate 装配 A)、非放行证据(禁检查器采信)。值域现役 =
# m4_fuel_sell / interest_prep(单帧锁 test_route_tag_whitelist 锁映射表);
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

    [坐标系] bench_idx = bench 槽位表下标 0-8(ADR-0316 定长 9 槽)。

    sim↔生产账本 income 对齐:sim 侧卖出回金按
    ``cost`` 1:1(cw_sim L630);生产真值 = ``sell_refund(star, cost)``
    (2★×3+手续费)。两侧本就不同源——sim 简化只对 1★ 准。补采:
    ``income`` 字段记录**创建时的预期回金**(策略侧算 sell_refund),
    账本/经济对账消费;未传 = None(sim 与旧调用兼容,sim 侧仍按
    自己的 cost 口径执行,不读此字段——它是**记录**不是**指令**)。

    ``expect``(ADR-0317 代际校验第三块,ADR-0326 §1.7 激活;''=不校验):
    提案生成时该槽位指向内容的期望名(char_id)——提案生成→应用之间
    槽位内容可能已变,应用时不符 → no-op + stale_proposal 语义
    (对齐 CwActionSellDeployedParam/CwActionSwapDeployParam 既有守卫形态)。
    **防线写入端核查(ADR-0326 §1.7;N3② 勘误,ADR-0585 批 4)**:发射点
    = mandate_v1/shop.py 卖出发射位(M2 腾席两处/凑息回拉/funding 变现
    /funding 兜底,逐位带 expect 写入;原「remediation 两补偿器」表述
    无实码对应,全仓 grep 仅本 docstring 自引用,锁面引用同勘误);
    prep 域发射位(mandate_v1/entry)构造留 expect 缺省 ''(不校验形态,
    归一前族B 载体无本字段的等价延续)。
    锁面 = test_cw_sell_reason_matrix.py(reason/归因面)与
    test_cw_sell_window_launch.py(TestFundingHoldFallback 兜底位
    expect+income 正锁)。
    """
    bench_idx: int
    # [索引定义] 坐标系: bench 槽位表下标 0-8(ADR-0316 定长 9 槽,空槽 None)
    #             取值时机: 生成期=执行期(槽位表恒稳,卖出置 None 不移位)
    income: int | None = None   # 创建时预期回金(sell_refund 口径;None=未标)
    expect: str = ''           # 代际校验期望名(''=不校验,不符→拒绝)
    reason: str = ''           # 卖出通道记录字段(记录非指令,仿 CwActionLevelUpParam.auth_basis 形态;
    #                            ''=未标,缺省形态)。承重值 = SELL_BENCH_REASONS
    #                            通道键(r9 争金归因证据层:失败/压线局的卖出
    #                            通道占比是归因下钻的直接证据;纯归因);
    #                            line_switch_collapse 兼孤儿证明标记,检查器
    #                            孤儿豁免分支据此判定(豁免键集 =
    #                            SELL_BENCH_ORPHAN_REASONS,与发射登记门
    #                            分离的独立闭集)。
    convert_reason: str = ''   # 转化类豁免分键(结构化证明键,ADR-0611):
    #                            值域收窄为本批两类放行键 ⊂
    #                            SELL_BENCH_CONVERT_REASONS 闭集——
    #                            fuel_victim_protect_demoted(M4 腾席被保
    #                            垫件末位牺牲)/ funding_support_stall_
    #                            convert + funding_hold_liquidated(筹资
    #                            变现两键);仅放行位填写,''=未标恒不豁免。
    #                            line_switch_collapse 不入本字段:孤儿证明
    #                            打标语义与豁免资格耦合留在 reason(ADR-0591
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
#   最后手段变现,ADR-0585;本键辖「持有件变现」非 T3 垫件转化,豁免
#   理由同为非自旋——义务筹资的资产重组,凑息缺口偏好账不授同款豁免);
# - line_switch_collapse: 线账闭合孤儿清算(P78-2a 账闭合事件「线账
#   闭合」:K 支持度重排致义务成员出基座,登记账就地销账,其后通道按
#   P78 INV 清算,1★ 往返净损 0 非自旋,r408 振荡意图不触犯)。键 =
#   通道名(entry 换线塌缩出口)兼孤儿证明标记(方案审乙′:
#   商店发射位仅在「本轮义务登记 ∧ 已出基座」证明在场时打标,授予
#   必须伴随登记簿线账闭合事件,防窗口段回归洗白——证明载体与边界
#   申报见 ADR-0591 §4)。
# 四键只辖「卖出排除面/被保留集登记件」的帧;缺省 '' 恒不豁免
# ——豁免面按分键收敛,禁全开(T3 同轮保留修复批设计约束;三键形态
# = ADR-0585 批 3,N7 豁免面与分键同批消除误报窗口;三→四键 =
# 方案审零阻断放行的语义演进,出处 = 2026-09-08 同轮交互
# 方案审 + ADR-0591)。
# 发射侧填充现状(两通道分键起):两类放行键(T3 末位牺牲/
# funding 两键)经 CwActionSellBenchParam.convert_reason 结构化字段填充(值域收窄,
# 见字段注);line_switch_collapse 仍在役于 reason(孤儿证明打标制 +
# entry 换线塌缩通道位)。检查器按键分工判定,禁单键并读双源;
# 键集保留 = 检查器豁免面单一源(键语义/豁免边不变,可核查面三格:
# 缺省 ''/plain 值/跨轮陈旧恒不豁免)。
SELL_BENCH_CONVERT_REASONS: frozenset[str] = frozenset({
    'fuel_victim_protect_demoted',
    'funding_support_stall_convert',
    'funding_hold_liquidated',
    'line_switch_collapse',
})


# 卖出发射位值域闭集(发射登记门:各 CwActionSellBenchParam 发射位的 reason 承重键
# 必须是本集成员;值 = 通道名,与该发射位 Emitted.reason/route_tag 同键
# 单一词汇)。新增发射位先在此登记再接线(值漂移由发射面行为锁暴露,
# 归因消费面按本集分桶)。记录非指令:零行为消费面,资格单一源不变
# (sell_gate 装配 A)。
# (unified-action-factory 批2b 自 kernel/cw_prep_actions 迁居,与
# SELL_BENCH_CONVERT_REASONS 同居;来源语义与登记门不变。)
SELL_BENCH_REASONS: frozenset[str] = frozenset({
    'line_switch_collapse',     # 线账闭合孤儿清算(ADR-0591 证明打标制)
    'm4_fuel_sell',             # M4 腾席/压库溢出清位(腾席臂构造事实)
    'interest_prep',            # T-115 凑息卖出(金位缺口触发)
    'funding_support',          # 支付筹资卖出(义务买金币位保障)
})


# 检查器孤儿豁免键集(同轮买后卖检查的孤儿清算豁免边;**与上方发射位
# 值域登记门 SELL_BENCH_REASONS 分离的独立闭集**):两集当前同值
# 但语义不同源——发射登记门的新增值不得静默放大豁免面(豁免面若随
# 登记门生长即成振荡防空洞;同轮买卖振荡零容忍 = ADR-0267/0593 治理
# 立场)。当前值 = line_switch_collapse(线账闭合孤儿清算证明标记,
# 授予须伴随登记簿线账闭合事件,ADR-0591 §4)。三消费位 = sim/checks
# /ledger 的 check_no_same_round_buy_sell 与 check_oscillation_xp_cap、
# sim/checks/suspects 的 d1_same_round_pair_review(检查器/复盘面同键
# 集,禁借道发射登记门)。值漂移由 test_cw_sell_reason_matrix 暴露。
SELL_BENCH_ORPHAN_REASONS: frozenset[str] = frozenset({
    'line_switch_collapse',
})


# S1 清键白名单 route_tag 闭集(备战旗标状态机 ADR-0596 §3.3 路径 (i)
# 卖出类;部署类由动作类型 CwActionDeployMoveParam 承载 = route_tag_of,不占本集)。
# 宿主 = kernel 词表:值域闭集单一源——策略器清键路由(mandate_v1)与
# 框架侧防御位误标检出(cw_screen_buy_cards 的 s1_reset_mischannel
# 计数)双消费同取此源(operations 禁触策略实现包常量)。
# equip_transfer_sell = 预留 tag(审 D3:M7 伴随卖人发生在组合 op 内部、
# 无现役 prep 域发射位,留作枚举完备性,禁虚找挂点)。凑息/压库类 tag
# 不入白名单:其触发重开只能经路径 (ii)(S2 在册 ∧ 腾席翻正,义务
# 优先,猎点 14)。
S1_RESET_ROUTE_TAGS: frozenset[str] = frozenset({
    'm4_fuel_sell',
    'equip_transfer_sell',
})


@dataclass
class CwActionLevelUpParam:
    cost: int        # 本次「购买经验」单击花金(ADR-0129:一次点击 = +XP_PER_BUY 经验,非整级;凑够门槛才升级)
    auth_basis: str = ''
    # 授权依据**记录**字段(非指令;ADR-0354):
    # 放行臂名('pop_slot'=①[33]人口位 / 'dp'=②DP 花费授权 /
    # 'static_ev'=③静态 EV 平台账;''=未过 ev.levelup_ev_authorized 的
    # 旧调用/未接线路径)。由 arbiter 升级门与 remediation 补偿臂在
    # **放行时**写入(sim 账本 actions 侧序列化为 CwActionLevelUpParam 行的 auth 键,
    # 检查器 levelup_interest_engine_gate 消费)。仿 CwActionSellBenchParam.income
    # 「记录不是指令」形态——执行层不读此字段,行为零改动。
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionLevelUpShopParam:
    """商店开画面专用升级意图(W970 §4.1.3 / W971 §2.8.2:CwActionLevelUpParam 拆 CwActionLevelUpShopParam)。

    唯一产出者 = ``decide_shop_screen``(商店屏接口);兼容期旧入口(已随退役批删除)
    ``decide_prep`` 仍产出基类 ``CwActionLevelUpParam``——两入口行为由构造保证等价,
    类型拆分只为执行器/遥测/对拍**消歧**(商店屏动作 vs 备战屏腾席链
    升级)。**刻意设计成无新字段的子类**:执行器(shop 买牌循环)与
    sim/simulate 全部按 ``isinstance(a, CwActionLevelUpParam)`` 消费,子类零改动兼容;
    对拍口径 = CwActionLevelUpShopParam ≡ CwActionLevelUpParam(同字段逐项全等,类型归一后比较)。
    """

    # 显式重声明继承字段:kwarg 签名审计(ast 静态)不追 dataclass 继承链,
    # 不重声明则 decide_shop_screen 的 CwActionLevelUpShopParam(cost=…, auth_basis=…)
    # 构造被误判 kwargs 违例(2026-09-02 L3 暴露)。
    cost: int = 0
    auth_basis: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})



@dataclass
class CwActionDeployMoveParam:
    """bench → 上阵(排 + 排内槽;完整落位意图入载荷)。

    [坐标系] bench_idx = bench 槽位表下标 0-8(ADR-0316 定长 9 槽);
    落位 = (to_row, to_slot) 载荷直指——落位决策权归策略层,执行器与
    容器写侧按载荷直落,禁执行边现读首空位;下标换算单一源 =
    kernel ``deployed_idx_of``。拖拽语义 = 游戏规则:目标槽空 = 放置,
    有角色 = 交换交互(被占位角色回本载荷源槽);执行层不判断占位、
    不拒、禁静默换槽,唯一失败形态 = 拖拽未生效(观察对账显影)。
    ``faction`` = 上阵后 board 阵营计数所需,发射位从容器槽位表
    角色对象现取(simulate 的 CwActionDeployMoveParam 分支消费此字段)。
    """
    bench_idx: int
    # [索引定义] 坐标系: bench 槽位表下标 0-8(ADR-0316;同 CwActionSellBenchParam.bench_idx)
    #             取值时机: 生成期=执行期(槽位表恒稳;simulate/mutate 按
    #             下标读槽并置 None)
    to_row: str      # "front" / "back"
    to_slot: int
    # [索引定义] 坐标系: 排内 1 基画面槽号(前排 1-4 / 后排 1-6,与装备族
    #             CwActionWearEquipParam.slot 同坐标系;与 to_row 合成完整
    #             落位,表下标 = deployed_idx_of(to_row, to_slot))
    #             取值时机: 生成期快照(发射位从 kernel 指派/容器现值算出;
    #             执行期与容器写侧按载荷直落,不再现读)
    faction: str     # 该角色阵营(上阵后 board[faction] += 1)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionRefreshShopParam:
    cost: int = 0    # 刷新花费(实机 OCR 补)
    # 触发源**记录**字段(非指令;先例 = CwActionLevelUpParam.
    # auth_basis / CwActionSellBenchParam.income 的「记录不是指令」形态——执行层
    # 不读此字段,行为零改动)。值域(发射位单一源 = mandate_v1/shop
    # R1 发射位,今日唯一刷新发射点;L2 补位=买卡、L3 末位=升级,
    # 结构上不产刷新动作,槽位留作未来发射点扩展):
    # - 'r1'                 = 息线门 R1(域外常规承诺账);
    # - 'must_spend_r1_yielded' = 必花域内 R1 切分线(核算账降排序
    #   yielded 支);
    # - '' = 旧调用/未标(引擎 obs 归 'other' 桶)。
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionCloseShopParam:
    """关店终结动作(ADR-0517 决策 4/5/6:商店画面的恒可用终结 op)。

    单动作架构(ADR-0517)下「无动作可做」的表达 = 策略器主动选关店终结
    op,取代旧「空序列 = 决策完成」契约;全函数契约(决策 5)要求动作空间
    至少含一个恒可用终结(决策 6)——本类即商店画面的该终结。执行侧语义
    = 本画面 op 结束、交回外循环(关店点击由编排壳 CwOpCloseShop 承担,
    与旧「空序列触发关店」同一落点);``simulate`` 对其 no-op(期望态随
    终结作废,由下一次入口观察重建)。
    """
    reason: str = ''   # 账本 reason(''=默认)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickEventParam:
    """选事件选项(投资环境/策略/遭遇/补给)。

    refresh(重立判据,ADR-0600;旧「阈值建议」判据已退役,
    现判据 = 零阈值结构存在性,推导与优势论证见 ADR-0600 §3.2 +
    math_proofs P81,env kind 不启用见 ADR-0600 §2/§4):「建议刷新」布尔 =
    ``refresh_slots`` 非空。**纯建议**——是否真刷由 handler 决定(逐槽计数
    现读 >0 才点;刷新失败/次数 0 → 照常选当前最优,失败安全 = 现状行为)。

    终态契约 §2.2 策略词表退役:策略 12 入口产出 = per-screen Pick 子类
    (选卡)+ 三刷新动作(刷新建议),本类**不再由策略器发射**;现役
    居民 = kernel ``decide_event`` 纯函数返回载体 + sim 既有脚本动作
    (引擎零策略构造,§2.7 申报)。
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
    #             取值时机: 生成期快照(kernel 帧级触发判定一次算出)
    #             写入端: cw_events.decide_event(ADR-0600 §3.1;空元组 = 不建议;
    #             环境屏恒空 = 执行不启用)。消费端 = CwScreenInvestStrategy
    #             槽序循环(逐槽计数现读闸 + 已发射槽集防重入)。
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionSellDeployedParam:
    """卖场上单位(deployed 生命周期开口;不再'只增不减')——契约包 C1。

    [坐标系] deployed_idx = state.deployed **槽位表**下标 0-9(ADR-0392;
    front 0-3 / back 4-9,空槽 None,卖出置 None 不移位——索引跨动作组
    恒稳)。
    """
    deployed_idx: int
    # [索引定义] 坐标系: deployed 槽位表下标 0-9(ADR-0392 定长 10 槽,空槽
    #             None)
    #             取值时机: 生成期=执行期(槽位表恒稳,卖出置 None 不移位)
    income: int | None = None  # 预期回金(sell_refund 口径;None=未标;记录非指令,同 CwActionSellBenchParam)
    reason: str = ''           # 账本 reason(如 'evict_replaced'/'plugin_recycle')
    expect: str = ''           # 遥测观测字段(ADR-0392 降级:槽位恒稳后不再承担
                               # 拦截漂移职责,记录生成期期望名供判读对照;
                               # 校验保留——名不符仍是跨代际提案的拒绝信号)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionSwapDeployParam:
    """bench ↔ deployed 换位(场上场下对调;装备随人走)——契约包 C1。

    [坐标系] deployed_idx = state.deployed 槽位表下标 0-9(ADR-0392)/
    bench_idx = bench 槽位表下标 0-8(两域均定长槽位表,索引恒稳)。

    装备随人走 = 换位移动单位对象本身(``equips`` 字段随对象迁移,
    无单独装备转移步骤);上场者落目标排(``to_row``/行域承载),
    开拓者按目标排做形态归一(同 CwActionDeployMoveParam 语义,单一源)。
    """
    deployed_idx: int
    # [索引定义] 坐标系: deployed 槽位表下标 0-9(ADR-0392,恒稳)
    bench_idx: int
    # [索引定义] 坐标系: bench 槽位表下标 0-8(ADR-0316,恒稳)
    #             取值时机(两者): 生成期=执行期(槽位表恒稳;expect_* 为
    #             遥测观测字段,ADR-0392 降级——记录生成期期望名供判读)
    reason: str = ''
    # 遥测观测字段(ADR-0392 降级的代际校验):跨轮登记的提案
    # 在槽位表下索引恒稳;名不符仍是跨代际换人提案的拒绝信号。
    expect_deployed: str = ''  # 期望下场者名
    expect_bench: str = ''     # 期望上场者名
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


Action = (CwActionBuyCardParam | CwActionSellBenchParam | CwActionLevelUpParam | CwActionDeployMoveParam | CwActionRefreshShopParam | CwActionCloseShopParam
          | CwActionSellDeployedParam | CwActionSwapDeployParam)


# ===== 统一词表·备战域动作(unified-action-factory 批2b 自
#       kernel/cw_prep_actions 迁居;类体逐字保留,基类引用翻 CwAction)=====
#
# 通用坐标系声明(装备域两类目标,全族共用):
# - 装备源件 = owned 装备网格内 icon,按 ``item_name`` 机械现读定位
#   (执行坐标边合法现读;坐标不入动作——网格 reflow 会使坐标失真,
#   名字定位是唯一稳锚)。
# - 角色目标槽位 ``row``/``slot``:row ∈ 'front'|'back'(画面物理排);
#   slot = 画面物理槽位 1 基(前排 1-4 / 后排 1-选档 N;非列表下标)。
#   取值时机 = 生成期快照(发射位从备战观察/容器槽位表现读;同一 visit
#   内 tracked 账随动,槽位跨动作组恒稳——置 None 不移位坐标系,
#   ADR-0392)。

@dataclass
class CwActionCollectOreParam:
    """点晶矿(R4 坐标参数化机械动作:载荷 = 有序晶矿坐标点击列表)。

    ``points`` = 按点击顺序排列的晶矿心坐标 (x, y)(1080p 游戏空间)。挑选
    逻辑(大晶矿优先/上界截断)归决策侧 kernel 单一源 = :func:`cw_prep_actions
    .select_ore_clicks`,发射位调用之;执行器纯机械逐个点,零读屏
    零排序。逻辑态按载荷精确摘晶矿(坐标匹配,容器 spheres 域)。
    """
    points: tuple[tuple[int, int], ...] = ()
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionOpenBoxParam:
    """开补给箱(点「开启」→ 弹武装箱 overlay;开箱即腾席)。slot=None → 第一箱。"""
    slot: int | None = None
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionOpenTomeParam:
    """开秘密典籍(点槽两次:选中→开启 → 弹星徽四选一;开典籍即腾席+loop 0i 接管选卡)。

    建档:投资策略「秘密典籍」给的红金典籍道具占备战席 1 槽(类补给箱);
    选卡决策在 loop 0i handler(板上阵营匹配),本动作只负责把典籍点开。slot=None → 第一典籍。
    """
    slot: int | None = None
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionOpenBookcardParam:
    """开书册卡(点槽「开启」→ 弹专家邀请函五选一;开卡即腾席)。

    书册卡 = 备战席占槽道具(与补给箱/秘密典籍并列第三件;R10 归位备战
    词表,与 CwActionOpenBoxParam/CwActionOpenTomeParam 同签名,design.md §2.6 R10)。选卡决策不在
    本执行链——点完开启本动作即交回,专家邀请函弹窗由外循环按画面分发
    ``CwScreenExpertInvite`` 选卡(选卡决策单一源 = kernel
    ``cw_events.choose_expert_index``,普查迁移批 2 自画面 op 迁入)。
    发射位 = 策略器 entry ① prep 实体面卡片臂(容器 bench 槽位 kind
    'bookcard' 触发;原「备战环入口清场段 ``cw_screen_prep._clear_prep_cards``
    代发」已按用户裁定 2026-09-19 撤销——开卡时机归策略实现管)。
    终结动作(弹专家邀请函 = 引入新事实,交回外循环重观察)。slot=None → 第一张书册卡。
    """
    slot: int | None = None
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionWearEquipParam:
    """穿装备(装备库 owned 件 → 目标角色物理槽位;R2 穿戴原子通路)。

    计划构造 = kernel ``build_equip_wear_plan``(自执行器模块迁居,
    决策侧逐帧现算);发射序即执行序(决策核逐帧取首项)。逻辑态 =
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
    """特权赋予卡(R8;双腿)。

    - target_kind='equip'(库存腿,现役执行臂):确定变换 = target 件
      名替换为对应·特权名(映射单一源 = ``cw_effect_inventory.
      privilege_counterpart``;上报 = equips 合并单笔写 = 移除工具 ∧
      变换同笔,写端 = ``cw_action_report.tool_use``);
    - target_kind='char'(拖角色腿):**fail-closed 不支持**(用户裁定
      2026-09-21 按不能拖角色处理候实机测试)——上报侧收到 char 腿 =
      零写留证(tool_privilege_worn_unsupported);判据面现役只产库存腿,
      穿域桥 ``transform_worn_equip_to_privilege`` 留守。
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
    +1 金 = 贡献算术,获得回执窗在册)。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionStaffProjectorUseParam:
    """员工投影仪(R8 投影仪按型号两类之一):target = 角色槽位
    (在备战席创造该角色 1 星复制);费用门 = 3 费及以下(门表单一源 =
    ``cw_affix_effects`` 投影仪费用门行),门由发射位判据面辖。上报 =
    复制走获得链 ``gain_character``(落位 → 回调 → 3 合 1 升星判断;
    复制触发三合一 = 口述·权威 2026-09-21)+ equips 移除工具合并腿,
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

    ⚠️ 发射位挂账(裁决 1/R9 纪律):作用对象判据面现役 fail-closed
    永不进准入(``cw_equip_env.evaluate_tool_actions`` rc_missing 拒因
    在册)——类随族立档 + 注册行,发射位禁无判据发射;判据面建模批
    补档(知识缺口登记 = ``flow/action-logic-state.md`` §7 好运令牌行)。
    上报侧 = 零写留证(tool_token_not_admitted 注记,写端随 R9 判据批)。
    """
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionOpenShopParam:
    """开商店意图(EnsureShop 意图退役后的承接形态)。

    显式开店 → 流程层编排商店访问(open_shop 幂等开店 → 入口观察 →
    decide_shop_action 逐动作循环 → CwOpCloseShop → 节点探针)。

    restricted_spend=True:受限访问(发射帧仲裁意图,金出口族出口 B;
    判定单一源 = 策略前置发射位经 kernel in_launch_spend_zone)→ 买波带
    预算闸(花后金位跌破息线即拒)→ 关店,本帧不发射(次帧复判)。
    """
    restricted_spend: bool = False
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionStartBattleParam:
    """出战(环出口;含未达上限确认)。零转移验证机械单发:点击序列发出即交回
    (未发出 = 找不到按钮返 False),转移与否由交回后下一帧观察裁决。CwActionStartBattleParam 豁免屏蔽。"""
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


# 动作全集白名单(统一词表运行时元组;注册完备锁的遍历单一源,批4
# 消费 = 逐类断言注册表解析可命中。新动作加入全集时同步此处——漏登记
# ⚠️ 教训(原 PREP_ACTION_TYPES 先例):**新增动作必须同步登记本白名单**
# —— 选择族动作化(策略器终态契约;落地 landing §3.1 纯新增零消费,
#       decide 接线归终态切换批)=====

# 选择族公共契约(原 PickOption 基类,摊平后 12 个叶子逐类重声明 idx/reason):
# ``idx`` = 该画面候选槽位序号,坐标系 = 对应 payload 槽 options 列表下标
# (0 基,与写槽时 OCR 顺序一致,槽位表恒稳);取值时机 = 生成期快照。
# 12 类全量在注册表分发(pick-op-unify 批收编,零上报例外撤销):执行 op =
# ``CwActionPickXxxOp``(机械链 = 选中 → 确认/点卡即选,op 内自上报,零写);
# 确认后容器写(chosen_*/Confirm* 到账)留守画面 op;``PickExpertInviteParam.idx``
# = -1 语义 = 现金为王(非候选槽下标)。


@dataclass
class CwActionPickEncounterParam:
    """遭遇节点选择(替代 EncounterPick;刷新建议另发 CwActionRefreshNodeOptionsParam)。"""
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
    """补给节点选择(替代 SupplyPick;刷新建议另发 CwActionRefreshSupplyParam)。

    开出内容载荷(银狼闭环迭代 design.md §2.2 确定性通道·通道宿主迁移,
    照 PickInvest 载荷扩展先例):``char_name`` = 选中列角色名
    (read_supply_options roster 校验产物;'' = 列无角色/兜底点卡路径);
    ``norm_item`` = 选中列装备归一件名(``normalize_equip_name``,OCR 原始
    名不静默改写由 handler 持有;'' = 未解析)。两字段不入动作实例键
    (归因载荷不改变动作身份,``route_tag`` 先例);上报落地相按实际开出
    内容应用(单位腿 + 装备后果腿,pick_supply 两相语义)。
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
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionPickInvestParam:
    """投资选择(投资策略/投资环境两入口共用,替代 CwActionPickEventParam;逐卡刷新
    建议另发 CwActionRefreshInvestCardsParam)。

    双屏分流载荷(银狼闭环迭代 design.md §2.3):``source`` = 发射屏别
    ('strategy'=投资策略屏 / 'portal'=投资环境屏;''=未分流——上报只登记
    意图,落地分派零动作);``norm_name`` = 选中卡归一规范名
    (``normalize_invest_name``,OCR 原始名不静默改写由 handler 持有)。
    上报分步语义:策略屏确认落地 → 入 ``gs.active_strategies`` + 效果
    分派;portal 确认落地 → 只走效果分派,禁入持卡面(防 portal 卡污染
    持卡经济聚合)。两字段不入动作实例键(归因载荷不改变动作身份,同
    ``route_tag`` 先例)。
    """
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    source: str = field(default='', kw_only=True,
                        metadata={'action_key_exclude': True})
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
    """命运卜者强化三选一选择(契约扩员 12→15 新增;普查迁移批 2)。"""
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
    """专家邀请函选卡选择(契约扩员 12→15 新增;普查迁移批 2)。

    [索引定义] idx 取值域扩展:0..3 = 候选卡区下标(卡-1..卡-4);
    **-1 = 现金为王**(经济兜底,非候选卡槽下标;kernel
    ``choose_expert_index`` 契约原样,handler 据此点「卡-现金为王」区)。
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
class CwActionPickEquipParam:
    """选择装备三选一选择(契约扩员 12→15 新增;普查迁移批 2)。

    选中件载荷(银狼闭环迭代 design.md §2.2 确定性通道·通道宿主迁移,
    照 PickInvest 载荷扩展先例):``norm_item`` = 选中卡装备归一件名
    (``normalize_equip_name``,OCR 原始卡名不静默改写由 handler 持有;
    '' = 未解析)。不入动作实例键(归因载荷不改变动作身份,``route_tag``
    先例);上报落地相装备腿 = 入栏 + 获得后果链,未解析 = 值不变翻来源
    (pick_equip 两相语义)。
    """
    idx: int
    # [索引定义] 坐标系: 该画面候选槽位序号,坐标系 = 对应 payload 槽
    #             options 列表下标(0 基,与写槽时 OCR 顺序一致,槽位表恒稳);
    #             取值时机 = 生成期快照(原 PickOption 基类契约,摊平后逐类
    #             重声明;``reason`` = 归因记录字段,''=未标)。
    reason: str = ''
    norm_item: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionRefreshNodeOptionsParam:
    """遭遇节点刷新建议(替代 EncounterPick.refresh 旗标):策略建议点击
    节点刷新钮。encounter 刷新链 = 同访问重决策——发射本动作前须以重读
    产物覆盖写槽再决策(刷新链分屏形态申报,禁沿用旧槽内容)。"""
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionRefreshSupplyParam:
    """补给节点刷新建议(替代 SupplyPick.refresh 旗标):supply 刷新链 =
    发射后交回重入型(重入访问走常规写槽→决策起点链)。"""
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class CwActionRefreshInvestCardsParam:
    """投资逐卡刷新建议(替代 CwActionPickEventParam.refresh_slots):**纯建议**——
    是否真刷由 handler 决定(逐槽计数现读 >0 才点,失败安全 = 现状)。

    [索引定义] slots = 待刷新投资卡槽位序号集,坐标系 = 投资界面卡槽
                物理排位(0 基);取值时机 = 生成期快照。三闸点击链
                留在画面 handler。"""
    slots: tuple[int, ...] = ()
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


#: CwActionObsParam.scope 值域闭集(观察口径单一源;消费端 = 备战决策环
#: 分支判等,in_place 走执行器、outer_loop 拦截交回;F3 静态校验同取本源)。
OBS_SCOPES: frozenset[str] = frozenset({'in_place', 'outer_loop'})


@dataclass
class CwActionObsParam:
    """重观察动作(策略发射 → 请求新鲜观察,口径由 ``scope`` 选择)。

    - ``scope='in_place'``(缺省):**当前画面重新观察上报**——执行体 =
      宿主画面 op 的 heavy 观察链重跑(漏斗直写容器 = 观察边界对账,
      「观察赢」),决策环原地续跑:访问不重启、段序号不置位、外循环
      零往返。帧代次标注 'full'(方向重估触发,同入口帧;贵段消费侧有
      每 game-round 恰一次键守卫限频)。重观察发现事件 overlay 在场 =
      抛 CwObsOverlayBail 交回外循环重分发(画面识别与路由归外循环,
      环内不消化;捕获点 = ``cw_screen_prep.act``)。
    - ``scope='outer_loop'``:**交回外循环重新观察**——决策环在
      validate/执行器之前拦截(不进执行器、不进动作注册表、不写续段
      token/动作记录),round_success(wait=1.0) 交回外循环重观察。
      本口径收编原 ``HoldFrame`` 空发射帧通道(用户裁定 2026-09-20
      HoldFrame 删除:两通道同为「观察请求」,口径差异收进参数;空发射
      语义 = 本帧无动作可发,交回让外循环重判/等待,自旋防护 = 交回后
      归外循环 stall 防线)。

    零容器动作写语义:in_place 口径的容器更新通道 = 观察漏斗本体
    (read_game_state 直写),``report_action_obs_param`` = 零写族占位
    (命名规约完备锁对象)。现役接线域 = 备战决策环(CwScreenPrep);
    in_place 在其他决策域发射 = 宿主能力缺失 AssertionError 响亮暴露
    (策略器 bug)。
    """
    scope: str = 'in_place'   # 观察口径,值域闭集 = OBS_SCOPES('in_place' 环内重观察 / 'outer_loop' 交回外循环重观察)
    reason: str = ''   # 归因记录字段(非指令;''=未标)
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


# (HoldFrame 已删除,用户裁定 2026-09-20:空发射帧通道收编进
#  CwActionObsParam(scope='outer_loop'),两观察口径统一为一个动作类型;
#  历史形态考古走 git 历史。)
    reason: str = ''
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})



# 动作类型总和(union 类型别名,**非基类**;继承基类已摊平,每动作一个
# 独立 dataclass。本名仅为既有 ``CwAction`` 注解面与 ``isinstance(x,
# CwAction)`` 判定的零改动兼容保留;Python 3.10+ union isinstance 合法)。
CwAction = (
        CwActionBuyCardParam | CwActionSellBenchParam | CwActionLevelUpParam | CwActionLevelUpShopParam |
        CwActionDeployMoveParam | CwActionRefreshShopParam | CwActionCloseShopParam | CwActionSellDeployedParam |
        CwActionSwapDeployParam | CwActionCollectOreParam | CwActionOpenBoxParam | CwActionOpenTomeParam |
        CwActionOpenBookcardParam | CwActionWearEquipParam | CwActionFurnaceUseParam | CwActionPrivilegeCardUseParam |
        CwActionWrenchUseParam | CwActionPrecisionWrenchUseParam | CwActionStaffProjectorUseParam | CwActionPerfectProjectorUseParam |
        CwActionLuckyTokenUseParam | CwActionStartBattleParam | CwActionOpenShopParam | CwActionPickEventParam |
        CwActionPickEncounterParam | CwActionPickSupplyParam | CwActionPickInvestParam | CwActionPickMegastarParam |
        CwActionPickPartnerParam | CwActionPickPlannerParam | CwActionPickStarTomeParam | CwActionPickWishTrialParam |
        CwActionPickBoxCardParam | CwActionPickFortuneParam | CwActionPickExpertInviteParam | CwActionPickEquipParam |
        CwActionRefreshNodeOptionsParam | CwActionRefreshSupplyParam | CwActionRefreshInvestCardsParam |
        CwActionObsParam
)
# ——漏登记时执行面 validate 拒「未知动作类型」,动作从未真正执行
# (CwActionOpenTomeParam 曾漏登记,数百次拒绝被误读为执行失败;登记是入口门)。
CW_ACTION_TYPES: tuple = (
    CwActionBuyCardParam, CwActionSellBenchParam, CwActionLevelUpParam, CwActionLevelUpShopParam, CwActionDeployMoveParam, CwActionRefreshShopParam,
    CwActionCloseShopParam, CwActionSellDeployedParam,
    CwActionCollectOreParam, CwActionOpenBoxParam, CwActionOpenTomeParam, CwActionOpenBookcardParam,
    CwActionWearEquipParam,
    CwActionFurnaceUseParam, CwActionPrivilegeCardUseParam, CwActionWrenchUseParam, CwActionPrecisionWrenchUseParam,
    CwActionStaffProjectorUseParam, CwActionPerfectProjectorUseParam, CwActionLuckyTokenUseParam,
    CwActionStartBattleParam,
    CwActionOpenShopParam,
    # 选择族动作化(终态契约;decide 接线归终态切换批,本批纯落型;
    # CwActionPickFortuneParam/CwActionPickExpertInviteParam/CwActionPickEquipParam = 契约扩员 12→15 新增,普查迁移批 2)
    CwActionPickEncounterParam, CwActionPickSupplyParam, CwActionPickInvestParam, CwActionPickMegastarParam, CwActionPickPartnerParam,
    CwActionPickPlannerParam, CwActionPickStarTomeParam, CwActionPickWishTrialParam, CwActionPickBoxCardParam,
    CwActionPickFortuneParam, CwActionPickExpertInviteParam, CwActionPickEquipParam,
    CwActionRefreshNodeOptionsParam, CwActionRefreshSupplyParam, CwActionRefreshInvestCardsParam,
    CwActionObsParam,
)

#: 选择族收敛单表(终态契约 §2.7):pick 子类型单表(9+3,契约扩员
#: 12→15 后十二个),供 handler 分派/注册完备锁遍历(三刷新动作走各自
#: 既有点击链不入本表;Obs = 观察请求语义,不属选择族)。
PICK_ACTION_TYPES: tuple = (
    CwActionPickEncounterParam, CwActionPickSupplyParam, CwActionPickInvestParam, CwActionPickMegastarParam, CwActionPickPartnerParam,
    CwActionPickPlannerParam, CwActionPickStarTomeParam, CwActionPickWishTrialParam, CwActionPickBoxCardParam,
    CwActionPickFortuneParam, CwActionPickExpertInviteParam, CwActionPickEquipParam,
)


def action_key(action: CwAction) -> str:
    """动作实例键(屏蔽计数粒度 = 动作类型 + 参数;CwActionSellBenchParam(3) 与 CwActionSellBenchParam(5) 各自计数)。

    带 ``action_key_exclude`` metadata 的字段不入键(现役 =
    CwActionSellBenchParam.reason 卖出归因 + CwAction.route_tag 发射臂路线标签
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


def mutate_bench_deployed(bench: list,
                          deployed: list,
                          action: Action,
                          shop: list[ShopCard] | None = None) -> None:
    """就地应用 action 的 bench/deployed 转移到持久跟踪状态(运行时同步用)。

    本函数**就地改** bench/deployed 两个列表,只做身份/星级/站位转移(buy→bench+merge / deploy→deployed /
    sell→置 None),供运行时执行点(shop.buy / deploy_bench verify / _handle_bench_full sell)同步
    tracked 主账。gold/shop/XP 期望态不在此辖:
    容器逻辑态直写 = 上报函数族(report_action_<snake>_param,动作语义单一源,避双源漂移)。
    P1 起容器原生形状(benchchar-retirement §2.3):bench =
    ``list[BenchSlot | None]``(定长 9,None=洞,卖出/上阵置 None 不移位)/
    deployed = ``list[Unit | None]``(定长 10,下标 = deployed_idx 动作坐标
    恒稳,排归属由下标派生,ADR-0392);入口防御性补 None 到定长(旧紧缩
    构造兼容,禁借迁移改索引语义)。
    CwActionLevelUpParam/CwActionRefreshShopParam/CwActionPickEventParam 不影响 bench/deployed → no-op。

    「占用」判定口径(§2.4 字段映射约定):bench 侧 = ``kind == 'unit'``
    (占位件槽非角色,恒不参与卖/上/合——卖恒拒/部署恒 held 防线的
    tracked 侧镜像,kind 面单一收口);deployed 侧 = ``is not None``。

    ``shop``(缺省 None = 零漂移兼容):调用方的当前店面视图。提供时,
    满栏合成买走 ``_apply_full_bench_merge_buy`` 单一源——满栏时游戏对完成合成
    的买入接受并合成(bench 素材被消费腾槽),tracked 侧同走
    ``_apply_full_bench_merge_buy``,不再丢件漏记;未提供或未识别牌
    (name 空,无法判合成对象)时维持旧丢件行为。
    """
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        deployed_idx_of,
        trailblazer_row_unit,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        Unit,
    )
    while len(bench) < BENCH_CAPACITY:
        bench.append(None)
    while len(deployed) < DEPLOYED_CAPACITY:
        deployed.append(None)
    if isinstance(action, CwActionBuyCardParam):
        _placed = bench_place(
            bench,
            BenchSlot(kind='unit', unit=Unit(char_id=action.card.name or '',
                                             star=int(action.card.star or 1))),
        ) is not None
        if not _placed and shop is not None and (action.card.name or ''):
            _apply_full_bench_merge_buy(bench, deployed, action.card, shop)
        _merge_bench(bench, deployed)   # 全场域(live tracking 与 simulate 同源)
    elif isinstance(action, CwActionSellBenchParam):
        # ADR-0317 代际校验(与 simulate 同源):expect 非空且不符 →
        # 陈旧提案 no-op(不移除)
        if 0 <= action.bench_idx < len(bench):
            _s = bench[action.bench_idx]
            if (_s is not None and _s.kind == 'unit'
                    and _s.unit is not None
                    and (not action.expect
                         or _s.unit.char_id == action.expect)):
                bench[action.bench_idx] = None   # 保洞:置 None 不移位
    elif isinstance(action, CwActionDeployMoveParam):
        _tgt = (bench[action.bench_idx]
                if 0 <= action.bench_idx < len(bench) else None)
        if (_tgt is not None and _tgt.kind == 'unit'
                and _tgt.unit is not None):
            # 同名唯一性守卫(W43 裁决 1,与 simulate 同源):已在场同名不上
            # (游戏拒收同名部署,swap 换入同名也同拒)。
            _u = _tgt.unit
            _k = board_unique_key(_u)
            if _k is not None and any(board_unique_key(d) == _k
                                      for d in deployed if d is not None):
                return
            # 落位 = 载荷 (to_row, to_slot) 直落(换算单一源 =
            # ``deployed_idx_of``,与执行拖点/容器写侧同源;拖拽语义 =
            # 游戏规则:目标空 = 放置,有人 = 交换——被占位单位回源
            # bench 槽,与 ``CwActionSwapDeployParam`` 换位契约同语义);
            # 禁静默换槽(不另寻空位),载荷槽越出定长表/跨排 = 不写
            # (陈旧载荷,交观察对账)。
            from dataclasses import replace
            _slot = int(action.to_slot)
            _idx = deployed_idx_of(action.to_row, _slot)
            if not (0 <= _idx < DEPLOYED_CAPACITY) \
                    or deployed_slot_no(_idx) != _slot:
                return
            bench[action.bench_idx] = None   # 保洞:置 None 不移位
            # 开拓者形态切换(同 simulate 语义,归一核单一源)
            _u2 = trailblazer_row_unit(_u, action.to_row)
            _occ = deployed[_idx]
            deployed[_idx] = replace(_u2, slot=_slot)
            if _occ is not None:
                bench[action.bench_idx] = BenchSlot(
                    kind='unit', unit=replace(_occ, slot=action.bench_idx + 1))
    elif isinstance(action, CwActionSellDeployedParam):
        # 动作 v2(契约包 C1):runtime 跟踪侧只做身份转移(金/装备归
        # sim/容器域其他写点,本函数不管——与 simulate 单一源规则一致)
        if 0 <= action.deployed_idx < len(deployed) \
                and deployed[action.deployed_idx] is not None \
                and (not action.expect
                     or deployed[action.deployed_idx].char_id == action.expect):
            deployed[action.deployed_idx] = None
            # ADR-0392:置 None 不移位(deployed_idx 恒稳;陈旧提案=代际不符 no-op)
    elif isinstance(action, CwActionSwapDeployParam):
        if 0 <= action.deployed_idx < len(deployed) \
                and deployed[action.deployed_idx] is not None \
                and 0 <= action.bench_idx < len(bench):
            _bs = bench[action.bench_idx]
            if _bs is None or _bs.kind != 'unit' or _bs.unit is None:
                return
            out_unit = deployed[action.deployed_idx]
            in_unit = _bs.unit
            # 代际校验 + 同名唯一性(W43 裁决 1/2,与 simulate 同源)
            if ((action.expect_deployed
                 and out_unit.char_id != action.expect_deployed)
                    or (action.expect_bench
                        and in_unit.char_id != action.expect_bench)):
                return   # 陈旧提案 no-op
            _k = board_unique_key(in_unit)
            if _k is not None and any(
                    board_unique_key(d) == _k
                    for _i, d in enumerate(deployed)
                    if d is not None and _i != action.deployed_idx):
                return
            # 上场者继承下场者排(排归属由下标派生,§2.1 口径)+ 开拓者
            # 形态归一(归一核单一源);槽位信息位随落位归一(frozen replace)。
            from dataclasses import replace
            _row = ('front' if action.deployed_idx < DEPLOYED_FRONT_CAPACITY
                    else 'back')
            deployed[action.deployed_idx] = replace(
                trailblazer_row_unit(in_unit, _row),
                slot=deployed_slot_no(action.deployed_idx))
            bench[action.bench_idx] = BenchSlot(
                kind='unit', unit=replace(out_unit, slot=action.bench_idx + 1))




# ===== 布局未知态的策略侧支撑(15 号稿批 C 落地审修订)=====
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
