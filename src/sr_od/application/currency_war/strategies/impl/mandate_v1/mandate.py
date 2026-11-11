"""cw4 骨架义务执行器(M1-M7)——换核后落地;执行序规格=02_mandate_layer §3。

单一 executor(每备战期骨架 pass),执行序(02_mandate_layer §3):
M5(开局板)→ M2(线成员买入)→ M4(腾席卖出)
→ M1(同帧部署)→ M3(升级整批)→ M1′(新人口位补部署)→ M6
(富余转压牌库)→ M7(装备转移)。

四硬约束检查点(02_mandate_layer §4 唯一合法拦截集,封闭于①-④):①可负担(金域
g≥c,整批合计)/②席位(board/bench 槽位、等级 cap、同名同星≤1)/
③S 预留(整买目标预留金不被非 S 组成动作吃掉;覆盖 EV 买入面+M6)
/④不可逆护栏(卖出线内/骨架/插件件不在骨架动作集)。
HP 不进任何检查点([39])。

M2→M4 重试环(R8-8/R11-5):买入遇 bench 满触发 M4 腾席,单帧闭环,
重试上限 ≤B=9(bench 容量注册表直读);M4 本次 0 发出 ⇒ 立即放弃
+遥测(不再重调)。M6 席位失败=单帧单评不入环
(R12-2/R21-4)。

动作标记:骨架动作 mandate=True(遥测可分离统计;R14-4:mandate=
pass 归属单一语义)。

D-C44(共根组 1):部署/买入意图的输入契约 = **买入结算后 bench/cap/
dup 黑板全量现读**——本执行器每帧从 PrepObservation 现读重建,不以
跨帧快照/旧集为输入(与 P24 补部署执行守卫互补:守卫管动作,估值管判断,
D-dup 谓词 = mandate_v1 deploy_plan.has_deployable 同源去重,发出×执行单一源)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_economy import (
    REFRESH_COST_BASE,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    locked_buy_cap_hold,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (
    count_merge_material_blocked,
    merge_material_reject_reason,
    same_star_count,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionFurnaceUseParam,
    CwActionLuckyTokenUseParam,
    CwActionOpenShopParam,
    CwActionPerfectProjectorUseParam,
    CwActionPrecisionWrenchUseParam,
    CwActionPrivilegeCardUseParam,
    CwActionSellBenchParam,
    CwActionStaffProjectorUseParam,
    CwActionWearEquipParam,
    CwActionWrenchUseParam,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    contracts,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    sell as crit_sell,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

# 卖出排除仲裁单一源:装配 A 与动作发出登记 API 本体在
# sell_gate;本模块保留兼容再出口(sell_hold_exclusions 凑息排除集——
# Z1 身份面已随统一让位优先级迭代 3.4 退役,语义 = 循环防线全资格面;
# T3 垫保簿 stall_buys_* 三函数 shim,签名零断链)。
# 消费位已全量迁移 sell_exclusions
# (窗口段 API)。冗余别名 = 刻意再出口(PEP 484 re-export 形态)。
from sr_od.application.currency_war.strategies.impl.mandate_v1.sell_gate import (
    consume_on_sell,
    dead_pair_exit_release,
    empty_board_sell_blocked,
    register_launch,
    sell_exclusions,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.sell_gate import (
    sell_hold_exclusions as sell_hold_exclusions,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.sell_gate import (
    stall_protect_active as _sell_gate_stall_protect_active,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import predicates
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
    saturation_line,
)

#: 装备/工具原子类集(M7 发出序回排适用范围;原子通路,R8 按消耗品各立类)
_EQUIP_ATOM_TYPES: tuple[type, ...] = (
    CwActionWearEquipParam, CwActionFurnaceUseParam, CwActionPrivilegeCardUseParam, CwActionWrenchUseParam, CwActionPrecisionWrenchUseParam,
    CwActionStaffProjectorUseParam, CwActionPerfectProjectorUseParam, CwActionLuckyTokenUseParam,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        GameState,
        Unit,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

# (M1″ seam 门常量 M1P_SEAM_VERIFIED 与 cw4_m1p_seam_verified/
#  cw4_m1p_arm_pending/cw4_m1p_plan_pending 载体已随部署统一批丁纳入统一管理时删除:
#  emit_swap_redeploy 发射缝随 kernel swap 机器退役,门与分键失去判读对象
#  ——kernel swap 机器行已随统一部署搜索退役。)

# ===== M2 停摆续段缓存:非变异动作白名单·备战域(必花分支重试风暴防线;
# 商店域同构缓存随商店期腾席卖射停用删除——席满缺员形态在商店域
# 表达为关店返回主循环,无重复帧面,本集独存备战域)=====
# 跳过条件 = 可判定谓词「帧间动作全在本集 ∧ 同段」,非任何计数阈值。
# 白名单外动作一律视为变异 ⇒ 缓存失效 ⇒ 全量重推导(保守端 = 现行为)。
# ⚠️ 守卫:加入新动作型前须验证其执行语义不动 bench/deployed/k/敌缀/
# 意图集——现行唯一成员依据:CwActionLevelUpParam(买经验点击)只动 xp/level/gold;
# prep 其余动作(CwActionSellBenchParam/CwActionMoveUnitParam…)均触 φ 分量,禁入。
M2_STALL_NONVARIANT_PREP_ACTIONS: frozenset[str] = frozenset({'CwActionLevelUpParam'})

# bench 容量 B(R8-8 重试上限;kernel/cw_state.BENCH_CAPACITY 单一源,
# R196 症6:本地重定义删除,消费=import 符号名——第二源构成快照巧合双源)


@dataclass
class Emitted:
    """发出项(动作 + 标记面;mandate=pass 归属,R14-4)。"""

    action: CwAction
    mandate: bool = True
    reason: str = ''
    funding_support: bool = False


@dataclass
class MandateFrame:
    """骨架 pass 输入帧(D-C44:黑板全量现读,每帧重建、零跨帧快照)。

    **状态容器形状(现行基准形态)**:
    - ``bench`` = 占席条目紧缩序(状态容器 ``BenchSlot``,kind != 'empty',
      物理槽序;占位件 kind 面在域内,身份经 ``cw_exec_state.
      bench_slot_unit`` 解包读口取——faction/position_pref 不入形状的
      注册表派生口径在消费点落位);
    - ``deployed`` = 行域单位紧缩序(deployed 视图两子表的状态容器
      ``Unit``,前排在前;char_id/star/equips 直读);
    ``deploy_cap`` 真值源 = ``max_units_of`` 派生链(R4 统一:level+宝钻、
    封顶 = 4+back_max 动态真值〔GameState.back_layout,值域 10-13〕,
    与 shop 侧同链单源;双源漂移修复——旧观察
    复合 ``obs.deploy_vacancy+len(deployed)`` 已废),state 缺读=None。
    """

    gold: int
    level: int
    bench: list[BenchSlot]
    deployed: list[Unit]
    deploy_cap: int | None
    node_type: str | None
    stop_flag: bool
    k_members: tuple[str, ...]
    round_num: int = 1      # 位面内轮次(M5 开局板适用范围=开局帧;状态容器 node 读口)
    # 装备域 owned 件名池快照(P4 观察接入调用):装配点 = entry.emit
    # 从状态容器 gs.equips 现读拷贝(全量含工具口径)。None =
    # 识别域未就绪(模板库/装备区缺失)或未供给,M7 装备穿戴放行判定按
    # 空保守关;[] = 真读到空。旧读点 = session.last_owned_equips 陈旧
    # 快照,已停用(消费面与计划产出位同帧同源,防门①与产出位双源漂移)。
    owned_equips: list[str] | None = None
    # 溢出告警旗标:备战席满告警在场 = 存在未安置
    # 溢出角色,出战点击被游戏忽略(prep.md 告警节,launch_dead 三连实证)。
    # 装配点 = entry.emit 从状态容器 overflow_warning 直传(观察写端单一源);
    # 缺省 False = 旧构造点/店域帧门关(fail-open 向常规决策,语义同值)。
    overflow_warning: bool = False

    @property
    def bench_free(self) -> int:
        return max(0, BENCH_CAPACITY - len(self.bench))

    @property
    def deploy_vacancy(self) -> int:
        """板面空位(cap 缺读=0 保守侧:R4 单一真值源改造后 cap 可 None,
        缺读不虚构空位——空位按 0 收紧部署候选,不向部署面放行幻影位)。"""
        if self.deploy_cap is None:
            return 0
        return max(0, self.deploy_cap - len(self.deployed))

    @property
    def bench_names(self) -> list[str]:
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            bench_slot_unit,
        )
        return [(u.char_id if (u := bench_slot_unit(b)) is not None else '')
                or '' for b in self.bench]

    @property
    def deployed_names(self) -> list[str]:
        return [d.char_id or '' for d in self.deployed]


# ===== 四硬约束检查点(§3.2;唯一合法拦截集)=====

def check_affordable(gold: int, cost: int, *, batch_cost: int | None = None,
                     ) -> tuple[bool, str]:
    """①可负担:资源余额 ≥ 动作成本(金域 g≥c;整批成本按 M3 批量合计)。"""
    need = batch_cost if batch_cost is not None else cost
    if gold < need:
        return False, f'gold {gold} < cost {need}'
    return True, ''


def check_seats(bench_free: int, deploy_vacancy: int, needs_bench: bool,
                needs_board: bool, name: str, deployed_names: list[str],
                ) -> tuple[bool, str]:
    """②席位:board/bench 槽位、等级 cap、同名同星≤1(穷举对象列:
    M1/M2/M3/M5/M6,R21-4/R32-3)。"""
    if needs_bench and bench_free <= 0:
        return False, 'bench_full'
    if needs_board and deploy_vacancy <= 0:
        return False, 'board_full'
    if name and name in deployed_names:
        return False, 'same_name_on_board'   # 同名上阵禁(游戏拒收;D-dup 面)
    return True, ''


def check_s_reserve(gold: int, cost: int, s_reserve: int,
                    ) -> tuple[bool, str]:
    """③S 预留:待执行整买目标的预留金不被非 S 组成动作吃掉
    (覆盖 EV 买入面序 3-5+M6;M2 序 1/2 义务不受限,[41])。"""
    if gold - cost < s_reserve:
        return False, 's_reserve'
    return True, ''


def check_irreversible(name: str, k_members: tuple[str, ...]) -> tuple[bool, str]:
    """④不可逆护栏:M4 候选过滤——卖出线内/骨架/插件件不在骨架动作集
    (留在 EV 层 fail-closed)。线内件(∈K)禁卖。"""
    if name and name in k_members:
        return False, 'line_member'
    return True, ''


# ===== M4 判据(燃料件支配卖出;P41 零参数,mandate 邻位,R2-2)=====

def _phase_key(state: GameState) -> tuple:
    """(plane, round_num) 相位键状态容器读(读口单一源;载体 = prep 链结构化
    段 2 起 gs 单形态)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        plane_of,
        round_num_of,
    )
    return (plane_of(state), round_num_of(state))


def _deployed_units_of(state: GameState) -> list:
    """上场单位域状态容器读(行域紧缩;benchchar-retirement P4 状态容器形)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        deployed_rows_of,
    )
    front, back = deployed_rows_of(state)
    return [d for d in (*front, *back) if d is not None]


def _slot_cid(b) -> str:
    """占席条目 → 身份名(单位 = 内嵌 Unit.char_id;占位件 = '')。
    本模块 BenchSlot 解包单一读点(P4 状态容器形)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    u = bench_slot_unit(b)
    return (getattr(u, 'char_id', '') or '') if u is not None else ''


def _slot_unit(b):
    """占席条目 → 内嵌 Unit(占位件/None 洞 = None;P4 状态容器形解包口,
    跨模块消费经本名——shop.py 合成对计数等身份+星级双读位共用)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    return bench_slot_unit(b)


def _slot_star(b) -> int:
    """占席条目 → 星级(占位件缺省 1,资格门先拒,值不被消费)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    u = bench_slot_unit(b)
    return int(getattr(u, 'star', 1) or 1) if u is not None else 1


def _bench_container_idx(state: GameState, victim: BenchSlot) -> int | None:
    """动作发出面状态容器下标解析·bench 域(条目对位:生产链 = 同帧同对象身份
    相等;测试/合成链可能等值重建 → 数据类值相等兜底,两道都过才认,
    失配 = 陈旧帧 fail-closed 禁猜位)。"""
    view = state.bench.value
    if view is None or victim is None:
        return None
    for i, s in enumerate(view.slots):
        if s is victim or s == victim:
            return i
    return None


def _bench_container_idx_by_compact(state: GameState, pos: int) -> int | None:
    """动作发出面状态容器下标解析·bench 域(紧缩位键 → 状态容器下标;unified-action-
    factory 换算收尾,位键 = 紧缩占席序下标
    〔物理槽序〕,状态容器下标 = 第 pos+1 个占用槽的下标——对位失配
    (越界/视图漂移)= 陈旧/carry 帧禁猜位,返回 None)。

    [索引定义] pos = 紧缩占席序 0 基下标(消费方 = criteria/sell
    三通道的候选位键);占用判定 = ``slot_occupies``(kind 口)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        slot_occupies,
    )
    if pos < 0:
        return None
    view = state.bench.value
    if view is None:
        return None
    k = 0
    for i, s in enumerate(view.slots):
        if s is None or not slot_occupies(s.kind):
            continue
        if k == pos:
            return i
        k += 1
    return None


def _deployed_container_idx(state: GameState, victim: Unit) -> int | None:
    """动作发出面状态容器下标解析·deployed 域(条目对位:生产链 = 同帧同对象
    身份相等,测试/合成链等值重建兜底;前排命中 = 下标 0-3,后排 = 4+
    排内 1 基〔SellDeployed 坐标域扩展:值域随 back_capacity_of 动态
    6-9,扩格帧后排 7-9 可寻址,旧定长 10 截断退役〕;失配 None =
    fail-closed 跳过)。
    场上同名唯一性不变量下,值相等对位与旧 (身份,槽号) 键等价。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        DEPLOYED_FRONT_CAPACITY,
    )
    view = state.deployed.value
    if view is None or victim is None:
        return None
    for i, u in enumerate(view.front_slots or []):
        if u is victim or (u is not None and u == victim):
            return i
    for j, u in enumerate(view.back_slots or []):
        if u is victim or (u is not None and u == victim):
            return DEPLOYED_FRONT_CAPACITY + j
    return None


def fuel_sell_candidates(bench: list[BenchSlot],
                         k_members: tuple[str, ...],
                         state: GameState,
                         *,
                         exclude_names: frozenset[str] | set[str] = frozenset(),
                         defer_names: frozenset[str] | set[str] = frozenset(),
                         merge_guard_release: frozenset[str] | set[str] = frozenset(),
                         counters: dict | None = None,
                         dedup_names: set[str] | None = None,
                         ) -> list[BenchSlot]:
    """fuel_sell 对象集:备战席可腾位候选(物理谓词 + 循环防线;
    统一让位优先级迭代 3.4 收缩后的形态)。

    输入域 = 占席条目域(状态容器 ``BenchSlot`` 紧缩序,占位件 kind 面在域内;
    身份/星级经 ``bench_slot_unit`` 解包读口,benchchar-retirement P4
    状态容器形)。

    **身份资格面退役申报(3.4,dismantle §3)**:原身份/代理资格门随静态
    不许卖名单退役整段删除——``zero_overlap`` 门(K 线内禁卖)/一星门
    (总纲 §2.4「不设仅一星代理过滤」用户决定:凑钱卖出按统一序列取用,
    一星全额退口径归预算投影/凑钱目标算术)/``bench_effect_qualified``
    检查(挂后台效果资格,四消费位的第四处)——「谁不该卖」改由统一
    让位序列(criteria/priority.sell_order)与消费位硬约束承载;M4 腾席环
    的 ``check_irreversible``(硬约束④不可逆护栏)不变。``k_members``
    形参保留 = 死库存买侧防线与消费位兼容读面。

    ``exclude_names`` = **循环防线装配位**(窗口段/L1 同轮禁卖/种子年龄
    豁免,单一入口 = ``sell_gate.sell_exclusions``;总纲 §2.4 保留项)——
    原身份段装配内容(义务基座 ∪ 保护集 ∪ registry 核心)已随身份段
    退役消失,参数保留 = 保留项防线的消费通道(同 visit 卖回防线 P78-1
    经由本位生效);消费位传装配 A 现值,禁自建第二排除面。

    保留资格面(物理谓词/循环防线,总纲 §2.4 保留项):

    - 占位件恒拒(腾席资格物理门):备战槽非角色占位
      物品(补给箱/星徽秘典/典籍书册等,状态容器槽位 kind 非 'unit' 识别
      防线 = 观察写端 kind 落位)恒不入候选——
      游戏真值 = 占位件无卖出交互且无金币现值(实机采证 2026-09-12:
      同参数拖拽出售,角色 9 连全卖、箱零效果;宝箱面 = 4 选 1 装备面板,
      无金币现值、无出售项),任何星级不可变现。与部署侧 ``cw_deploy_
      logic`` 'item_slot' 恒 held 同谓词同向(该面防误上,本面防误卖),
      判读先于其余资格门。生产观察层 SIFT 不产占位件条目,sim 假环境经
      观察面把占位件直喂 bench——本门 = 卖出发出前唯一资格防线;判据
      单一源已上收为跨通道共享谓词 ``predicates.item_slot_unsellable``
      (凑息/支付变现通道同门消费,禁第三处内联复制)。

    - 空板止损守卫(单一源 = sell_gate.empty_board_sell_blocked):
      板空帧腾席卖出分支同弱劣拒帧 → 本函数返空,消费位走各自既有「无
      候选」诚实停摆路径(m2_retry_exhausted/bench_full/{prefix}_no_fuel)。

    - 合成素材拒入守卫(G-S1):候选 1★ 与场上(deployed 域,
      ``state`` 现读;bench 域含自身)另有同名同星副本 ⇒ 2/3 合成进度
      素材,拒因键 ``merge_material_guard``(单一源 = ``cw_state.
      merge_material_reject_reason``,与部署侧同键)拒入燃料集——防
      g_20260906_081836 P2r1 案发形态(同名 2★ 唯一升级路径被腾席通道
      卖断)。``counters`` 非 None 时拒因同键计数(键 ``merge_material_
      guard_blocked``);计数 = 事件口径(C1 整改:同帧同名只计 1,去重
      载体 = ``dedup_names``——腾席环 while 重试对同一滞留素材重复触达
      不再重复 +1,单一源 = ``cw_state.count_merge_material_blocked``)。

    - ``merge_guard_release``(缺省空集 = 零漂移端):死库存素材对
      释放集——G-S1 判据处的**条件旁路**(先旁路后装配):拒因命中 ∧
      名在释放集 ⇒ 跳过拒入、不计数(资格子谓词旁路,非新通道;单一源
      = sell_gate.dead_pair_exit_release,消费位禁自算第二份)。

    ``defer_names``(T3 同轮保留=末位牺牲序;M4 腾席转化类放行,非绝对
    禁卖):集合内名字降为候选**末位**——存在非保候选时 victim 恒取
    非保件(被保件零成本存活);被保件是唯一燃料 ⇒ 照常放行卖出(为
    义务买入腾位的转化类清算,非自旋)。命中销账:消费端对被保件调
    ``stall_buys_consume``(单一源 = sell_gate.consume_on_sell,账闭合
    随统一簿 close_on_sell 分键承载);``fuel_victim_protect_demoted``
    = 本场景的转化类豁免分键词汇(cw_vocab.SELL_BENCH_CONVERT_REASONS
    成员;保留键——T3 防线键非身份保护键,归循环防线保留清单,
    dismantle §3 遥测键面核对结论)。稳定排序:仅把被保件
    移尾,不改既有相对序——defer 空集时逐位等价旧序(零漂移)。

    带默认排序:slot 升序(确定性)。
    """
    _deployed = _deployed_units_of(state)
    if empty_board_sell_blocked(_deployed, counters=counters):
        return []
    out = []
    for b in bench:
        # 占位件恒拒(资格物理门,先于其余资格门短路):占席物品不可卖、
        # 无金币现值,判据单一源 = predicates.item_slot_unsellable
        #(跨通道共享谓词;语义出处 = 本函数 docstring「占位件恒拒」段)。
        if predicates.item_slot_unsellable(b):
            continue
        name = _slot_cid(b)
        star = _slot_star(b)
        if name in exclude_names:
            continue
        if merge_material_reject_reason(name, star, bench, _deployed) \
                and name not in merge_guard_release:
            if counters is not None:
                count_merge_material_blocked(counters, name, dedup_names)
            continue
        out.append(b)
    # T3 末位牺牲序:被保件稳定移尾(非绝对禁卖——唯一燃料帧照常放行)
    out.sort(key=lambda b: _slot_cid(b) in defer_names)
    return out


# ===== T3 同轮保留集(N3 登记集卖侧读端;买后同轮即卖净零自旋修复)=====
# 载体单一源 = 统一动作发出登记簿(属性 = STALL_BUYS_ATTR,见 sell_gate 注;
# 四因类登记簿,本节函数 = 兼容 shim,本体单一源在
# sell_gate)。语义 = 末位牺牲序,非绝对禁卖:凑息回拉通道跳过被保件
# (门槛7 保证缺口 ≤ 其他可变现件总和,跳过无损);M4 腾席/支付变现
# 为转化类,仅降序放行;line_switch 候选集 ⊂ 旧线成员,垫件零重叠永不
# 在旧线,结构无关。生命周期四出口编号对齐(方案 v3 §3.1/
# 定稿序;旧在码注释「①部署销/②卖出销」错位于本批统一):①卖出销
# (consume_on_sell)/②部署销(prune_on_deploy)/②′合成销
# (consume_on_merge,V2-05)/③轮界销(读端就地过期)。


def stall_buys_register(session, name: str, round_num: int) -> None:
    """买入登记兼容 shim(写端单一源 = sell_gate.register_launch,
    本节只保 T3 时代签名:垫保分支(T5/出口③)动作发出点调用零改动)。"""
    register_launch(session, name, cause='stall_protect',
                    round_num=round_num)


def stall_protect_active(session, current_round: int | None, *,
                         counters: dict | None = None) -> frozenset[str]:
    """T3 垫保视图兼容 shim(读端单一源 = sell_gate.stall_protect_active;
    轮界过期与 close_on_round/t3_protect_expired_round 分键语义原样)。"""
    return _sell_gate_stall_protect_active(session, current_round,
                                           counters=counters)


def stall_buys_consume(session, name: str) -> None:
    """卖出即销兼容 shim(生命周期出口①;本体 = sell_gate.consume_on_sell,
    close_on_sell 分键随统一簿生效)。容旧 set 载体(兼容未升级会话)。"""
    consume_on_sell(session, name)


# ===== 轮内卖出登记(泄金阶梯档 2 候选集新鲜度排除)=====
# 场景 = 同轮「卖X→买回X→再卖X」净零自旋(模拟批#5 s108 实证):凑息
# 卖出抬高金位过 g* 后,同轮压牌库分支把刚卖的件买回,金位与席面净零循环
# 烧动作。载体与 kernel GameState.round_fresh_buys 同构键式
# {'phase': (plane, round_num), 'names': set[str]},位面/轮次推进自动
# 失效;方向 = 排除向(过度排除上界 ≤1 轮,轮界自动过期,有界可判读)。
# 写端 = 各卖出动作发出点(prep 凑息/M4/wanted 分支2 + entry 晶矿路径 M4;
# 商店域 _note_sell 收尾随商店期卖射停用删除——本载体现覆盖
# 「备战同轮卖 → 商店买回」的换手排除面);读端 = shop 档 2(M6)候选集。
# entry 域
# funding 兜底/line_switch 卖出本批不登记:换线/筹资语境的买回另属
# 线账语义(资金兜底卖持有件后买回 = P78-5 豁免面自身管辖;换线卖出
# 后买回新线件 = 义务通道非压牌库),实证病灶(s108)无该域样本,扩域留
# 观测键(m6_round_sold_excluded)判读后裁决(覆盖面申报)。

#: 轮内卖出登记载体属性(session 级字段名;StrategyState 具名字段族外的
#: 键式 dict 载体,形态与 kernel GameState.round_fresh_buys 同构)。
ROUND_SOLD_ATTR: str = 'cw4_round_sold_names'


def record_round_sold(session, state: GameState, name: str) -> None:
    """轮内卖出登记(档 2 新鲜度排除写端;卖出动作发出点逐名调用)。

    ``state`` 仅取 (plane, round_num) 键维(经 ``_phase_key`` 状态容器读口,
    缺维按 None 键 = 不跨轮误命中);
    ``name`` 空串跳过。同一发出批多个卖出意图逐名入集(漏记 =
    买回环切不断,防抖失效静默)。
    """
    if not name:
        return
    reg = getattr(session, ROUND_SOLD_ATTR, None)
    phase = _phase_key(state)
    if not isinstance(reg, dict) or reg.get('phase') != phase:
        reg = {'phase': phase, 'names': set()}
        setattr(session, ROUND_SOLD_ATTR, reg)
    reg['names'].add(name)


def round_sold_names(session, state: GameState) -> frozenset[str]:
    """读当前位面轮内有效卖出名集(跨轮 = 空集,自动失效;读端不销账
    ——过期由键式相位失配整体作废,无逐名生命周期面)。"""
    reg = getattr(session, ROUND_SOLD_ATTR, None)
    if not isinstance(reg, dict):
        return frozenset()
    phase = _phase_key(state)
    if reg.get('phase') != phase:
        return frozenset()
    names = reg.get('names')
    return frozenset(names) if isinstance(names, set) else frozenset()


def sold_this_round(session, state: GameState, name: str) -> bool:
    """本轮已卖名判定(L2 卖后禁买统一判定 helper)。
    薄封装 ``round_sold_names`` 单一源(档 2 载体零新载体
    零新阈值);全买入分支候选过滤位统一经本 helper 消费,禁分支层手搓
    第二读法(防「第七分支绕过新鲜度」复发形态)。"""
    return bool(name) and name in round_sold_names(session, state)


# (dominance_buy_eligible 资格门已随 dominance_buy 通道整删——富余买入
#  并入 M6 一星兜底带(shop.py),金位面 = M6 富余判定(gold > g*)、
#  席位面 = M6 现行席位维承载,comp-structure-unification 3.4,
#  press-stockpile §1;金维支配论证与 P76 甲/P78-1 基准随通道归档,
#  原文考古走 git 历史。)


# ===== 买入死库存防线(G-S1 买侧对偶)=====

def dead_stock_pair_buy_reject_reason(name: str, star: int,
                                      bench: list[BenchSlot | None],
                                      deployed: list[Unit] | None = None,
                                      k_members: tuple[str, ...] = (),
                                      ) -> str:
    """非定向 1★ 买入资格子谓词:买入将制造「同名 1★ 第二张死库存对」
    时拒(返回拒因键 ``dead_stock_pair``,'' = 可买;API 形态与
    ``cw_merge_simulate.merge_material_reject_reason`` 同形——判据本体
    单点,计数归消费位,键 ``dead_stock_pair_blocked`` 事件口径)。

    判据(全称谓词,零参数):拒 ⟺ star=1 ∧ name∉K ∧
    ``same_star_count(name, 1, bench, deployed) == 1``。C 为全场域
    (bench∪deployed)同名同 1★ 计数(计数单一源 = ``same_star_count``,
    与 G-S1 卖侧同源,禁消费方手搓同式),逐值验证:
    - C=0:买入后 C=1,单张 1★ 全额可退件零锁席,放行;
    - C=1:买入后 C=2——G-S1(cw_merge_simulate.
      ``merge_material_reject_reason``)按「2/3 合成进度
      期权 fail-closed 不卖」把该对**两成员都**永久拒卖;对非线内名
      该对无第三张来源(义务面不含 ⇒ M2/m2_merge_completion 不买它)
      ⟹ 无合成意图的确定性死库存对,每对锁 2 席。买侧断新生对 =
      C 在 {0,1} 上单调(0→1 许,1→2 禁),该名 G-S1 拒卖集构造性
      恒空,死库存不可达;
    - C=2:买入即同名同星满 3 自动合成 2★(全场 C 3→1 净释放席位,
      merge_mechanics §2;G-S1 覆盖星 = 1 同款口径),是消对修复动作,
      放行——禁误伤;
    - name∈K(线内/义务基座成员):任意 C 放行——线内同名对 = 合法
      合成素材,第三张由 m2_merge_completion 通道管辖(免席门),本
      谓词与该通道零交集。参照系与 G-S1 卖侧同键族(K 成员性 +
      same_star_count),防双源。

    为什么(实证):死库存对 = 席位死锁的直接成因之一——G-S1 保护
    对无合成意图的非线内名属过度保护,卖侧放行(改 G-S1 语义)与
    买侧断新生(本谓词)两案中取后者:保守向、零触碰已登记守卫语义、
    与 G-S1 退出通道(方向③)正交不互斥。s77091 型案例:
    R1 死金压牌库买入阿格莱雅×2、R5 dominance 连买绯英成对,两对锁席
    九轮,缺口件(仙舟#3)无兑付通道致 form_ok 九连 False。

    边界:覆盖 1★ 买入(2★ 直出不成对恒放行);覆盖「非定向」分支(候选
    资格维,消费位 = M6 一星兜底带 / ②(b) 死金压牌库燃料类 prio 的
    候选过滤),义务通道(M2/m2_merge_completion/prio0 缺口/prio1
    持有档)零消费;``bench`` 含 ``None`` 槽形态与 ``same_star_count``
    签名对齐。
    """
    if (star or 1) != 1:
        return ''
    if not name or name in k_members:
        return ''
    if same_star_count(name, 1, bench, deployed) == 1:
        return 'dead_stock_pair'
    return ''


# (P88 买侧收窄全套已退役整删——comp-structure-unification 3.4,
#  press-stockpile §3:富余金占位买入通道(dominance_buy)并入 M6 一星
#  兜底带后,原特殊帧(终局锁定 ∧ 未成型 ∧ 上场满员)从「禁买」变
#  「兜底带可买、席位紧张让位序列末位让路」;1★ 全额退 + 让位序末位档
#  = 占位件可无成本即时让出,所防「席位阻断」在现行防线栈中无剩余真实
#  形态(死库存对真凶另由本模块 dead_stock_pair_buy_reject_reason 断
#  新生防线根治,兜底带内同拦截)。退役符号 = PRESS_NARROWED_ARMS /
#  swap_transition_narrow_frame / kernel swap_bond_gate_domain_of /
#  tools/cw/proofs/p88_check.py;命题留档 = proofs/p88.md 文首退役标注。
#  原文考古走 git 历史。)


# (core_single_card_buy_eligible 已随 C1 支退役整删——统一让位优先级
#  迭代 3.4,C1 单卡核心囤积规则作废,dismantle §2;契约键
#  ('mandate','core_single_card_buy_eligible') 同批清除。)


# (M1″ 终局阵容锁定转型域部署执行放行判定族——_deploy_advances_form /
#  _redeploy_emission_allowed(P79-3 三轴门)/ _bond_gate_recalc_allowed
#  (发射帧复算统一门)——已随部署统一批丁纳入统一管理时删除:在发射层重新回答
#  「要不要换」的部署问题已由统一部署搜索定型单属承载(部署定型单属的
#  违例面裁定;P79 消解,math_proofs 索引行随批处置)。)


# ===== executor 本体 =====

def run_mandate(frame: MandateFrame,
                session: StrategySession,
                state: GameState,
                registry: DecisionV2Registry | None = None,
                ) -> list[Emitted]:
    """骨架 pass(§3.1 执行序;返回发出列表,执行序=列表序)。

    ``state`` = 决策状态容器 gs(prep 链结构化段 2;R4:arm1
    消费位的 cap 真值在消费点现读 ``max_units_of`` 派生链——单一真值源,
    与 shop 侧同链)。域读经读口族与字段对照表。

    ``registry`` = 上下文注册表注入(等级帽单一源,第 4 消费位
    登记待办的收尾):M3 链 ``lv9_stop`` 消费位读注入表的 ``level_max``,
    禁回读缺省表。
    ``None`` 回读 ``DEFAULT_REGISTRY`` 与 entry/shop ``_reg`` 通道同款
    约定(直调/测试面兼容,生产链经 entry.emit 恒注入);备战栈无 sim
    调用方,本通道无 sim 路径。

    计数键(state_of(session).cw4_counters;键登记单一源=下述各键写点注释,
    原 design_telemetry 键节已删档):
    m2_retry_exhausted / m6_bench_full /
    m6_overflow_strand / bench_full_buy_abandon(R196 症4 落地:M2 bench
    满放弃买入帧的「bench 满拒买」事件计数,与 m2_retry_exhausted 的
    环终止计数分键——前者量事件帧,后者量重试环耗竭;两键按
    事件粒度:续段缓存命中帧不增,量级骤降 ≠ 风暴消失,判读协议随批
    声明;观测对 m2_stall_cache_hit / m2_stall_cache_rederive 与重复帧
    键 m2_stall_repeat_frame 同期新增,语义与商店域一致)/
    dead_pair_exit_sold_m4_fuel /
    dead_pair_exit_sold_interest(释放成员实际卖出笔数,键族单一源 =
    sell_gate 键族清单)。(死锁计数键 deadlock_only_transition_victim
    已随身份保护判据退役删除——统一让位优先级迭代 3.4。)

    备战期开店标志已随迭代 2026-10-12-prep-shop-workflow-redesign 批
    3.6/3.7 停用删除(防活锁职责 = 商店会话标记 shop_handled 承接;
    历史 counter 键 shop_latch_skip_* / equip_latch_skip_m7 随标志停用
    停产)。
    """
    counters = getattr(state_of(session), 'cw4_counters', None)
    if not isinstance(counters, dict):
        counters = {}
        state_of(session).cw4_counters = counters

    # 上下文注册表(等级帽单一源,收尾):M3 链 lv9_stop 消费注入表,
    # 禁回读缺省表;None→
    # 缺省表 = entry/shop _reg 通道同款直调兼容约定(生产链恒注入,
    # 备战栈无 sim 路径)。
    _reg = registry
    if _reg is None:
        from sr_od.application.currency_war.kernel.cw_registry import (
            DEFAULT_REGISTRY,
        )
        _reg = DEFAULT_REGISTRY

    # 续段 token 读清协议(备战域):入口读取后立即清除,token 供
    # 下方 M2 停摆块命中判定消费;任何调用方首帧(槽空/型外/序号不等)
    # 默认全量重推导。
    _st = state_of(session)
    _frame_token = _st.cw4_frame_action_record
    _st.cw4_frame_action_record = None

    def _count(key: str) -> None:
        counters[key] = counters.get(key, 0) + 1

    def _emit_open_shop(tag: str) -> None:
        """开店意图动作发出点(备战期开店标志已删除(随停用)——会话
        标记〔shop_handled〕承接防活锁,本位恒发出)。"""
        out.append(Emitted(CwActionOpenShopParam(), True, tag))

    out: list[Emitted] = []
    k = frame.k_members

    # T3 同轮保留集卖侧读端(prep 域;单一源 = stall_protect_active,
    # 轮界过期名就地销账 t3_protect_expired_round)。计算位 = 溢出告警门
    # 之前(门先消费 defer_names;单点计算,禁同帧双算致轮界过期名重复
    # 销账计数——原「凑息接入调用之前」计算位随门前置上移,凑息块消费同变量)。
    _t3_protect = stall_protect_active(session, frame.round_num,
                                       counters=counters)

    # ---- 溢出告警门(用户定案;强收窄先于一切分支)----
    # 告警在场 = 存在未安置溢出角色,此刻出战点击被游戏忽略(launch_dead
    # 停机钩子三连实证,prep.md 告警节)→ 本帧决策输出强收窄为单动作
    # CwActionSellBenchParam(腾位后溢出卡自动入自由槽,下入口帧告警消失恢复常规决策):
    # CwActionStartBattleParam 禁发、买面/凑息/部署全冻结。候选与释放同源
    # (wanted_close 分支 2 先例:fuel_sell_candidates 全守卫——占位件
    # 恒拒/合成素材拒入/T3 降序;身份资格面已随统一让位优先级迭代 3.4
    # 退役,零新增排除面,reason 沿用 m4_fuel_sell,构造事实分键
    # overflow_clear_sell/overflow_no_fuel)。
    # 候选空集 = fail-closed 空批(禁乱卖被守卫件),返回主循环,环级无
    # 进展守卫兜底。
    if frame.overflow_warning:
        # 循环防线装配(窗口段/L1 同轮禁卖/种子豁免;身份段已随统一
        # 让位优先级迭代 3.4 退役——装配自动收缩)。
        _ov_excl = sell_exclusions(session, k, channel='m4_fuel',
                                   cap_hold=locked_buy_cap_hold(state),
                                   current_round=frame.round_num)
        # 释放集同参同源(N3;与腾席分支同一装配单点)。
        _ov_release = dead_pair_exit_release(
            session, k, frame.bench, frame.deployed, frame.round_num,
            cap_hold=locked_buy_cap_hold(state), counters=counters)
        _ov_cands = fuel_sell_candidates(frame.bench, k, state=state,
                                         exclude_names=_ov_excl,
                                         defer_names=_t3_protect,
                                         merge_guard_release=_ov_release,
                                         counters=counters)
        if _ov_cands:
            # 轮内卖出登记(档 2 新鲜度排除写端,与 M4/凑息分支同口径)。
            _ov_c0 = _slot_cid(_ov_cands[0])
            record_round_sold(session, state, _ov_c0)
            if _ov_c0 in _ov_release:
                _count('dead_pair_exit_sold_m4_fuel')
            _vidx = _bench_container_idx(state, _ov_cands[0])
            if _vidx is None:
                _count('overflow_clear_sell_stale_idx')
                return []
            _count('overflow_clear_sell')
            return [Emitted(CwActionSellBenchParam(bench_idx=_vidx,
                                      reason='m4_fuel_sell'), True,
                            'm4_fuel_sell')]
        _count('overflow_no_fuel')
        return []

    # M5 开局板(§2.9 无数学面:开局帧(round_num≤1)板空且有 bench 件;
    # 载体 = 统一部署搜索 + 差分执行器链,阶段 5/6 丁与 entry 第 6 步/
    # 出战链同链,旧七桶 _deployable 前置随选人族纳入统一管理时删除)
    deploy_intent_emitted = False
    if frame.round_num <= 1 and not frame.deployed and frame.bench:
        deploy_intent_emitted = _emit_unified_deploy(
            out, session, 'm5_opening_board')

    # ---- 规则②(a) 凑息卖 prep 接入调用----
    # 触发 = gold < g*(利息帽 resolved 口径;买断制局 g*=0 自然全关,B2
    # 利息帽维度修正)。判据单一源 = criteria/sell.sell_for_interest 零改
    #(金位缺口触发/目标量止盈/资格谓词族/刚买件优先/血线地板禁令全
    # 继承,B3 禁第二套卖件通道)。state 必传(N1):血线地板判据输入,
    # 漏传 = sell.py 首闸 fail-closed 返回 blood_floor,prep 凑息结构性
    # 哑火(Z1 回归测试以「须产生 CwActionSellBenchParam」断言兜住此漏接)。
    # 接入调用位 = 备战环首个 _emit_open_shop 发出之前:CwActionOpenShopParam 是帧稳定
    # 契约截断点(M7 回排申报在案,truncate_frame_stable 其后必截),
    # 卖出须先于本轮开店到账,与 M4「prep 卖出恒先于本轮买入」域序
    # 一致;(a) 先于全部买面动作求值(Z1 分支序:义务分支之外的先手)。
    # 载体 = Emitted(CwActionSellBenchParam, True):发出载体 reason 归因面已随
    # 2026-09-08 用户归因遥测删除指令拆除(缺省 '' 未标;契约条目 =
    # flow/action_exec.md §1)。
    # exclude = sell_exclusions(session, k, channel='interest',
    # current_round=frame.round_num):装配 A 全量形态(单一入口
    # sell_gate)。身份段(义务基座 ∪ 保护集 ∪ registry 核心)已随统一
    # 让位优先级迭代 3.4 退役——凑息资格不再做身份排除(凑息 = 统一
    # 序列取用形态的前身通道,身份承载归让位序);现役构成 = 循环防线
    # (窗口段 press/垫保登记,活跃 = 登记轮==当前轮;②(b) 动态登记的
    # F1 终局阵容锁定清空语义废除(P78-3 证其错误),修法 = 轮界过期;
    # L1 同轮硬面;种子年龄豁免)。
    # defer = T3 同轮保留(垫保在凑息是绝对跳过 = 通道对价语义,与窗口
    # 段排除是两个面,sell.py:140-148)。
    _cap_resolved = _cap_of(session)
    # 合成素材拦截去重集(帧级,C1 事件口径):本帧所有守卫触达位
    #(②(a) 凑息资格评估 / M4 腾席环)共享,与 shop 侧 _mm_dedup 同款
    #——凑息分支先触达首计后,腾席环对同一素材不再重复计数。
    _mm_dedup: set[str] = set()
    _dp_release: frozenset[str] = frozenset()
    if frame.gold < saturation_line(_cap_resolved):
        if contracts.ensure_contract(
                ('sell', 'sell_for_interest'),
                contracts.ContractCtx(gold=frame.gold), counters):
            # 释放集同参同源(N3:cap_hold 与本位装配同一现读;凑息通道
            # 消费释放成员 = P78-5′ 对价豁免条款照常覆盖,无新增豁免需求)。
            _dp_release = dead_pair_exit_release(
                session, k, frame.bench, frame.deployed, frame.round_num,
                cap_hold=locked_buy_cap_hold(state), counters=counters)
            _t1_slots, _t1_key = crit_sell.sell_for_interest(
                frame.gold, list(frame.bench), _cap_resolved, k,
                state=state,
                exclude_names=sell_exclusions(session, k,
                                              channel='interest',
                                              cap_hold=locked_buy_cap_hold(
                                                  state),
                                              current_round=frame.round_num),
                defer_names=_t3_protect,
                merge_guard_release=_dp_release,
                counters=counters,
                dedup_names=_mm_dedup)
        else:
            # 契约核验失败 = fail-closed 弃权零发出,分键暴露(同 shop
            # 消费位形态;禁新契约键,复用同键 ('sell','sell_for_interest'))
            _t1_slots, _t1_key = [], 'contract_abstain'
            _count('t1_interest_prep_contract_abstain')
        if not _t1_key and _t1_slots:
            _t1_name_of = {i: _slot_cid(b)
                           for i, b in enumerate(frame.bench)}
            for _s in _t1_slots:
                # 状态容器下标解析(换算收尾,见 _bench_container_idx_by_compact):
                # 失配 = 陈旧/carry 帧,fail-closed 跳过该候选。
                _vidx = _bench_container_idx_by_compact(state, _s)
                if _vidx is None:
                    continue
                # Emitted.reason = route_tag 透传载体填充(
                # 桥伴带到执行侧动作):interest_prep = 凑息分支构造事实,
                # 只作 S1 清键路由消费(白名单外,仅经路径 (ii) S2 已登记∧
                # 腾席翻正清键,义务优先)——非归因遥测(治理立场
                # 对表:tag=内部路由键,非放行证据;卖出资格单一源 =
                # sell_exclusions 零触碰)。
                # 轮内卖出登记(档 2 新鲜度排除写端;凑息卖出抬高金位后
                # 同轮压牌库买回 = s108 净零自旋,写端防抖见 helper 注)。
                record_round_sold(session, state, _t1_name_of.get(_s, ''))
                if _t1_name_of.get(_s, '') in _dp_release:
                    _count('dead_pair_exit_sold_interest')
                out.append(Emitted(CwActionSellBenchParam(bench_idx=_vidx,
                                             reason='interest_prep'), True,
                                   'interest_prep'))
            _count('t1_interest_prep_emit')

    # (dominance_buy 前置开店段已随通道整删——富余买入并入 M6 一星
    #  兜底带,comp-structure-unification 3.4,press-stockpile §1;
    #  富余帧开店意图由下方 M6 段承载,原文考古走 git 历史。)

    # M2 线成员买入(+M2→M4 重试环 R8-8)
    missing = [m for m in k
               if m not in set(frame.bench_names) | set(frame.deployed_names)]
    # T3 同轮保留集卖侧读端已上移至 ②(a) 凑息接入调用前(单点计算声明见彼处)。
    # (开店标志跳过分支已停用删除(随备战期开店标志)——会话标记
    # 承接防活锁;run_mandate 现为测试面已登记函数。)
    if missing and not frame.stop_flag:
        ok, _why = check_seats(frame.bench_free, frame.deploy_vacancy,
                               needs_bench=True, needs_board=False,
                               name='', deployed_names=frame.deployed_names)
        if not ok:
            # 现场腾席:M4 fuel_sell(R8-8:环内意图=线内件(序 1/2)独占)
            # dedup = 拦截事件口径(C1):帧级去重集,while 重试环对同一
            # 滞留素材重复评估只计 1。
            # 续段缓存(商店域 M4 块同款):上帧动作 ∈ 备战域白名单
            # ∧ token/标志序号均 == 当前段序号 ∧ 标志结论=腾席无候选 ⇒ 扫描
            # 输入逐项不变 ⇒ while 环重放必再失败(环注释原语义),跳过
            # 环与两事件键;计数从帧粒度回到事件粒度,命中帧改计
            # m2_stall_repeat_frame(+m2_stall_cache_hit)。
            _seg = _st.cw4_segment_serial
            _latch = _st.cw4_m2_stall_latch
            if (_frame_token is not None
                    and _frame_token[0] in M2_STALL_NONVARIANT_PREP_ACTIONS
                    and _frame_token[1] == _seg
                    and _latch is not None and _latch[0]
                    and _latch[1] == _seg):
                _count('m2_stall_cache_hit')
                _count('m2_stall_repeat_frame')
            else:
                # _mm_dedup 帧级去重集已上移至 ②(a) 接入调用前创建(两守卫
                # 触达位共享,声明见彼处)。
                # 循环防线装配(窗口段/L1 同轮禁卖/种子豁免,单一入口
                # sell_gate;身份段已随统一让位优先级迭代 3.4 退役——
                # 装配自动收缩):腾席候选的线内件拦截由硬约束④
                # check_irreversible 承载(不变),T3 同轮保护仍走
                # defer_names(转化类末位牺牲,通道对价语义不动)。
                _m4_excl = sell_exclusions(session, k, channel='m4_fuel',
                                           cap_hold=locked_buy_cap_hold(
                                               state),
                                           current_round=frame.round_num)
                # 释放集同参同源(N3;腾席环内逐次评估共享本帧释放集,
                # 名×轮去重面在单点函数内)。
                _m4_release = dead_pair_exit_release(
                    session, k, frame.bench, frame.deployed, frame.round_num,
                    cap_hold=locked_buy_cap_hold(state), counters=counters)
                retries = 0
                freed = False
                no_fuel = False    # 标志写条件承载:环以「候选空集」退出(
                                   # 不可逆拒/正常腾出 ≠ 本结论,不写标志)
                bench = list(frame.bench)
                while retries < BENCH_CAPACITY:
                    cands = fuel_sell_candidates(bench, k, state=state,
                                                 exclude_names=_m4_excl,
                                                 counters=counters,
                                                 defer_names=_t3_protect,
                                                 dedup_names=_mm_dedup,
                                                 merge_guard_release=_m4_release)
                    if not cands:
                        no_fuel = True
                        break       # 0 发出 ⇒ 立即放弃(状态未变,重放必再失败)
                    victim = cands[0]
                    _vname = _slot_cid(victim)
                    ok4, _ = check_irreversible(_vname, k)
                    if not ok4:
                        # 硬约束④不可逆护栏命中(防御位):身份排除面
                        # (zero_overlap)退役后线内件可达候选集——护栏
                        # 语义不变(线内件禁卖),处置由「终环」改「跳过
                        # 该件继续找可腾件」(旧形态该分支不可达,候选集
                        # 构造性不含线内件;改跳过使护栏与腾席目标兼容)。
                        bench = [b for b in bench if b is not victim]
                        continue
                    # T3 末位牺牲序命中 + 卖出销账(唯一燃料帧放行转化;
                    # 销账行为面保留)。Emitted.reason = route_tag 透传
                    # 载体填充:m4_fuel_sell = 腾席分支构造
                    # 事实,白名单内——落地经路径 (i) 清 S1 开店标志;
                    # 非归因遥测(治理立场对表,资格面零触碰)。
                    # CwActionSellBenchParam.reason = 卖出通道记录字段(登记门键,
                    # 记录非指令),归因证据层随动作发出点填充。
                    if _vname in _t3_protect:
                        stall_buys_consume(session, _vname)
                    # 轮内卖出登记(档 2 新鲜度排除写端;腾席卖出后同轮
                    # 压牌库买回 = 净零席面自旋,写端防抖见 helper 注)。
                    record_round_sold(session, state, _vname)
                    if _vname in _m4_release:
                        _count('dead_pair_exit_sold_m4_fuel')
                    _vidx = _bench_container_idx(state, victim)
                    if _vidx is None:
                        # 状态容器下标失配(陈旧/carry 帧)= 换手循环输入失真,
                        # fail-closed 终止环(重放必再失败,同 no_fuel 形态)。
                        no_fuel = True
                        break
                    out.append(Emitted(CwActionSellBenchParam(bench_idx=_vidx,
                                                 reason='m4_fuel_sell'), True,
                                       'm4_fuel_sell'))
                    bench = [b for b in bench if b is not victim]
                    freed = True
                    retries += 1
                    # 腾席后席位复检(静态:卖 1 件 ⇒ bench_free+1)
                    if BENCH_CAPACITY - len(bench) > 0:
                        break
                if not freed or BENCH_CAPACITY - len(bench) <= 0:
                    _count('m2_retry_exhausted')
                    _count('bench_full_buy_abandon')   # 环终止仍满 ⇒ 事件帧
                    if no_fuel:
                        _count('m2_stall_cache_rederive')
                        _st.cw4_m2_stall_latch = (True, _seg)
                    # (死锁计数键 deadlock_only_transition_victim 已随
                    # 身份保护判据退役删除——统一让位优先级迭代 3.4:保护
                    # 集买面消费位全退役后该纯计数键无判读对象。)
                else:
                    _emit_open_shop('m2_buy')
        else:
            ok1, _ = check_affordable(frame.gold, cheapest_member_cost(frame))
            if ok1:
                _emit_open_shop('m2_buy')
            # 金不足侧:funding_support 变现通道在 EV pass(criteria/sell)

    # M1 同帧部署(买入完成后立即评估成对上阵;载体 = 统一部署链,
    # _emit_unified_deploy 单一源;板满帧由差分执行器交换交互承载)
    if not deploy_intent_emitted and frame.deploy_vacancy > 0:
        _emit_unified_deploy(out, session, 'm1_deploy')

    # (升级整批 M3 段与 M1′ 升级后补部署段不落本决策链——升级判据
    # 内核 = criteria/levelup.upgrade_trigger 单判据三分派(最优概率带,
    # 触发键 stay_gate/natural),动作发出点收拢为 entry.py 备战第 4 步
    # 升级检查(商店会话保留升级意图出口转场关店)。升级后补部署无独立
    # 对应分支:十段全扫单动作循环下第 4 步命中即返回,升级帧结构性
    # 到不了部署步——行为经下帧 M1 空槽补位收敛(deploy_vacancy 更新后
    # M1 命中,零卖出成本接管)。)

    # (M1″ 板满换阵补部署意图块已随部署统一批丁纳入统一管理时删除:板满帧换人 =
    # 统一部署搜索定型 + 差分执行器交换交互(entry 第 6 步承载),被换下
    # 者回 bench 由卖出场景处置——统一部署搜索定型单属;板满帧
    # 本测试面骨架的部署面由 M1/M5 空槽臂 + entry 生产链承载。)

    # M6 富余转压牌库(存在性=金>g*;档匹配 fail-closed ⇒ 不买
    # +富余滞留遥测;席位失败=单帧单评,R21-4)。stop_flag 已摘
    #(泄金阶梯档 2,摘旗扩域,对抗审查 落点
    # 三处消费位之一):富余段转化期帧(线未齐)压牌库买合法,[13]
    # 停手线纪律由候选集判据本体承载(stockpile_buy P49 档匹配
    # fail-closed + P56 s_reserve 下界 + 线内副本排除,全保留);
    # 窗口语义维持在产 ω 塌缩带(tier_search_window,shop 侧消费,
    # 本位 emit CwActionOpenShopParam 转店后重过)。
    if frame.gold > saturation_line(_cap_of(session)):
        ok, _ = check_seats(frame.bench_free, frame.deploy_vacancy,
                            needs_bench=True, needs_board=False,
                            name='', deployed_names=frame.deployed_names)
        if not ok:
            _count('m6_bench_full')
        else:
            from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
                provisional,
            )
            if provisional.is_none('T_SEARCH_A'):
                _count('m6_overflow_strand')
            else:
                _emit_open_shop('m6_stock')

    # M7 装备转移(常态:关键装备穿上场单位;D-B 释放判据 = kernel
    # cw_equip_env.resolve_wear_release 五行表;计划产出位 =
    # kernel/cw_equip_wear_plan(自执行器模块迁居);载体 =
    # CwActionWearEquipParam 原子序[R2 原子通路,RunEquip 组合壳停用])。
    # 装备动作放行判定 = 变换可能性两件套:
    # ①可穿存在性(m7_wearable_exists):owned 快照里有注册表已登记且非
    #   工具类的件。快照源 = 决策帧 owned_equips(P4 观察接入调用)。
    # ②备战期标志(cw4_m7_equipped_phase)**随原子化停用**(依据 =
    #   计划构造 kernel 化 + 决策侧逐帧现算):
    #   逐帧现算形态下动作发出面天然收敛——每件 CwActionWearEquipParam 执行后逻辑态
    #   (owned 摘件)落黑板,计划随帧收缩至空;同 phase 一次标志与「逐件
    #   序」互斥(标志在首件后挡死余件)。0 穿重发环(2026-09-03 组合壳
    #   活锁病灶)由两层既有防线承接:visit 动作数上限 + 环级无进展守卫
    #   (恒指纹 3 环停机保留证据),确定性出口不减。
    if frame.owned_equips \
            and m7_wearable_exists(frame.owned_equips):
        from sr_od.application.currency_war.kernel.cw_equip_wear_plan import (
            _build_equip_wear_plan,
        )
        _build = _build_equip_wear_plan(session, registry)
        if _build.fail_reason:
            # 资源前置缺失(黑板帧/装备观察域未就绪)= 未发出通道,标志不置,
            # 下帧重派(与组合壳时代 round_fail 同形)。
            _count('equip_plan_resource_missing')
        else:
            for _step in _build.steps:
                out.append(Emitted(
                    CwActionWearEquipParam(item_name=_step.item_name,
                              char_name=_step.char_name,
                              row=_step.row, slot=_step.slot),
                    True, 'm7_equip_transfer'))
            if not _build.steps:
                # 空计划具名 NOOP(合法稳态)。
                _count('equip_plan_empty_noop')

    # M7.5 工具消费动作发出点已物理移出本执行器(审 A1 主案):
    # 动作发出点 = entry.emit ②证明 pass 与③升档器求值位之间(判据单一源
    # = kernel/cw_equip_env.evaluate_tool_actions + G1 准入;自原子化起
    # 按裁决 1 逐件产工具原子类,RunTools 组合壳停用)。

    # M7 发出序回排(实机局 g_20260904_010335 1-6/1-7 漏发定案的原子化
    # 形态):装备/工具原子(自原子化起 = 截断类,aftermath 含穿着即合成/
    # 网格 reflow,不可静态预测)若落在同帧其他截断点/终点(如 CwActionOpenShopParam)
    # 之后 ⇒ 截断器其后必截,穿戴被静默丢弃。修法 = 动作发出组织面回排:
    # 装备/工具原子插到**其他**截断点/终点之前,执行序(先穿后开店)与
    # 发出序一致。分类单一源 = entry.classify_frame_stability(函数内
    # 延迟 import 防模块环)。
    if any(isinstance(e.action, _EQUIP_ATOM_TYPES) for e in out):
        from sr_od.application.currency_war.strategies.impl.mandate_v1.entry import (
            classify_frame_stability,
        )
        equips = [e for e in out if isinstance(e.action, _EQUIP_ATOM_TYPES)]
        rest = [e for e in out if not isinstance(e.action, _EQUIP_ATOM_TYPES)]
        cut = next((i for i, e in enumerate(rest)
                    if classify_frame_stability(e.action)
                    in ('truncation', 'terminal')), len(rest))
        # 组内序:穿戴先行、工具随后(炉烧死库存与穿戴互不依赖,但
        # 先穿后烧与 M7.5 原组内序等价)
        equips.sort(key=lambda e: 0 if isinstance(e.action, CwActionWearEquipParam) else 1)
        out = rest[:cut] + equips + rest[cut:]

    return out


# (mark_equip_pass_executed / mark_tools_pass_executed 备战期标志写点已随
#  组合壳 RunEquip/RunTools 删除停用(unified-action-factory):
#  M7/M7.5 逐帧现算形态下逐件逻辑态使判据面天然收敛,同 phase 一次标志与
#  逐件序互斥;载体字段 cw4_m7_equipped_phase/cw4_tools_phase 同批删除,
#  0 穿活锁防线归 visit 动作数上限 + 环级无进展守卫。)


# (M1″ 板满换阵补部署动作发出点 emit_swap_redeploy(含 emit_swap 首对 SellDeployed
#  形态/转型域 swap 链)已随部署统一批丁纳入统一管理时删除:板满帧换人 = 统一部署
#  搜索定型 + 差分执行器交换交互,被换下者回 bench 由卖出场景处置——
#  kernel swap 机器随统一部署搜索退役;SellDeployed 在役
#  发出点自此收敛为三处(卖出评估器 deployed 支/计划变量执行位/同名
#  异星换),与部署段正本(24 号稿 §1.4)发出点清单同口径。)


# ============================================================
# 部署选人纯函数接口(统一让位优先级判定的结构抽取,判据零改动;
# 接口契约正本 = strategy-docs/32_unified_sell_priority.md §1〔部署先行〕
# 与 24_deploy_segment.md §1.4〔三路共用定型〕)
# ============================================================


@dataclass(frozen=True)
class PrepContext:
    """部署定型上下文装配(:func:`select_deployment` 的只读输入面)。

    阶段 5/6 丁:旧选人读口字段(target_comp 等历史字段/board_
    counts/deploy_cap/locked_factions/recipe_floor_lock_exempt/window_
    blocked_names)随七桶选人族纳入统一管理时删除——统一部署搜索的消费面 = 状态容器
    现读(session_ref/gs_ref 两引用),窗口谓词/上场锁过滤在搜索段 0
    (枚举硬约束)。生产装配 = :func:`assemble_prep_context`;虚拟重算
    = :func:`select_deployment` 的 ``virtual_bench``/``virtual_field``
    传参(panel_from_virtual 面板替换承载)。
    """

    session_ref: object | None = None
    """搜索面板装配引用(统一部署搜索:select_deployment 面板装配的
    session 入参;虚拟重算 = 面板替换承载,本字段仅供生产路径)。"""
    gs_ref: object | None = None
    """搜索面板装配引用(同上;gs = 决策状态容器)。"""


def assemble_prep_context(session: StrategySession, gs: GameState,
                          frame: MandateFrame) -> PrepContext:
    """PrepContext 生产装配(session/gs 两引用;状态容器读口过滤归搜索
    段 0,本装配零散读)。"""
    return PrepContext(session_ref=session, gs_ref=gs)


def select_deployment(frame: MandateFrame,
                      prep: PrepContext,
                      *,
                      virtual_bench: list | None = None,
                      virtual_field: list | None = None,
                      margin_out: dict | None = None,
                      ) -> dict[str, tuple[str, int]]:
    """部署定型(统一部署搜索内核;消费接口契约 = target_board = 角色名
    → (排, 选定星)——星维承载
    就位粒度名+排+星;档 1 名集消费 = ``frozenset(target)``;正本 =
    strategy-docs/24_deploy_segment.md §1)。

    生产路径(= 三路共用定型:卖出评估器/获取让位/出战链)面板装配 =
    ``deploy_search.build_deploy_panel``(段 0 硬约束过滤:唯一性键
    归一/窗口谓词/上场锁/召唤物/未知件);虚拟路径(获取让位评估的
    快照+X 置入;24 号稿 §1.4 虚拟路径契约)= ``virtual_bench``/``virtual_field``
    传升星
    连锁模拟产物(SimAcquisition 两半),窗口谓词共享、成员域分窗
    声明(部署枚举池 = 全部真实单位)。

    ``margin_out`` = 可选次名分量收集出参(挑边差距遥测的私有槽通道;
    遥测正本 = strategy-docs/strategy-telemetry.md ``deploy_margin`` 行:
    透传段 3 收集,纯函数零状态写;真实出口 =
    entry._step5_deploy 传入,虚拟 4 调用点[shop 获取让位×2/
    sell_candidates/supply]不传即零写入——sell_candidates 与 entry
    实参形态相同,分流只能由调用侧承载)。

    评分函数纯函数(接口契约:消费状态容器状态,sim 可跑,禁 IO;
    24 号稿 §1.1 末条);
    rng 局面哈希播种(同一状态容器状态 → 同一 target,跨帧稳定)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        deploy_search,
    )
    if virtual_bench is not None or virtual_field is not None:
        panel = deploy_search.panel_from_virtual(
            prep.session_ref, prep.gs_ref,
            virtual_bench, virtual_field or [])
    else:
        panel = deploy_search.build_deploy_panel(
            prep.session_ref, prep.gs_ref, frame)
    return deploy_search.search_deploy_target(panel, margin_out=margin_out)


# ============================================================
# 局面快照与虚拟置牌(统一让位优先级判定;获取角色流程与卖出触发
# 的部署重排共享输入。契约定案:局面快照纯计算,禁状态容器深拷贝)
# ============================================================


@dataclass(frozen=True)
class SimAcquisition:
    """虚拟置牌 + 升星连锁模拟的产物(:func:`simulate_acquired_units`)。

    [索引定义] ``bench`` 每项 = (原紧缩占席序下标, 虚拟 BenchSlot):
    下标坐标系 = 调用方传入 ``bench``(紧缩占席序)的 0 基下标,取值时机
    = 生成期快照;合成素材项从列表消失、存活项与合成载体**保持原下标**
    (载体留原位语义,与 kernel ``_merge_bench`` 同构)——消费位据此把
    虚拟尾牌还原回当前状态容器槽位(置入的新牌 origin = len(bench) 哨兵,
    不映射状态容器)。``field`` = 虚拟场上单位(传入 deployed 紧缩行序,
    升星载体原位 replace)。
    """

    bench: list[tuple[int, BenchSlot]]
    field: list[Unit]


def snapshot_frame(gs: GameState) -> MandateFrame:
    """局面只读快照(状态容器一次只读取 → MandateFrame)。

    消费面 = 获取角色流程与卖出触发的部署重排(:func:`select_deployment`
    的局面输入)。与 entry.emit 装配段的两处刻意差,均出自虚拟重算
    零遥测红线(acquisition-and-sell 问题约束节:journal/策略遥测/
    决策帧三通道零写入):
    - K 空窗回退不展开——回退命中会写 ``prep_k_fallback_*`` 计数;
      快照路径的 ``k_members`` 只承载 MandateFrame 形参完备性,
      select_deployment(方向经 prep.target_comp 取)与统一序列判据
      零消费,omit 无行为差;
    - owned_equips 不读(M7 域输入,部署定型与让位排序零消费;None
      缺省 = 识别域未就绪保守关的既有语义,此处语义无关)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_entries_of,
        deployed_rows_of,
        gold_of,
        level_of,
        max_units_of,
        node_kind_of,
        round_num_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.sell_candidates import (
        sell_line_membership,
    )
    front, back = deployed_rows_of(gs)
    return MandateFrame(
        gold=gold_of(gs),
        level=level_of(gs),
        bench=list(bench_entries_of(gs)),
        deployed=[d for d in (*front, *back) if d is not None],
        deploy_cap=max_units_of(gs),
        node_type=node_kind_of(gs),
        stop_flag=False,
        # k_members 读口 = 统一线内名单(单一准入 §2.1:候选 ∪ 配方 ∪
        # 锁定线并集;换源不消亡,保留面消费 = 溢出告警门卖出装配/
        # cheapest_member_cost 金需求侧)。复用阶段 1 成员判定函数,
        # 禁手搓第二份名单。
        k_members=tuple(sorted(sell_line_membership(gs))),
        round_num=int(round_num_of(gs) or 1),
        overflow_warning=bool(gs.overflow_warning.value))


def simulate_acquired_units(bench: list[BenchSlot],
                            deployed: list[Unit],
                            name: str, star: int) -> SimAcquisition:
    """虚拟置牌 + 升星连锁模拟(获取角色流程第 2-3 步;纯函数零副作用)。

    机制全集口径(与 11 号稿 §1 M2b / kernel ``_merge_bench`` 分组键
    同一规则,总纲 §2.3):同名同星计数 = 场上+备战混合,计数达 3 合成
    向高一级推进(2★ 满三合 3★,3★ 终态不再合成),连锁到不再触发;
    合成组含场上件则场上副本承载升星(``_merge_bench`` 载体规则)。
    装备继承/效果/羁绊重算等其余联动不模拟【拍,总纲 §2.3】——虚拟
    产物零 equips,仅承载「谁在场、几星」的让位判定主轴。

    新牌恒追加于备战位尾部(席满帧 = 溢出置入,由升星净释放或末位
    让路消解——merge_mechanics §2.5 满栏合成买同款净释放语义;合成
    释放量由调用方以 ``len(产物 bench) < len(传入 bench)`` 判读)。
    """
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        Unit,
    )
    # 工作副本 = (原下标, 裸 Unit);场上侧 = (排位下标, 裸 Unit)。
    v_bench: list[tuple[int, Unit]] = []
    for i, b in enumerate(bench):
        u = bench_slot_unit(b)
        if u is not None and u.char_id:
            v_bench.append((i, Unit(char_id=str(u.char_id),
                                    star=int(u.star or 1))))
    v_field: list[tuple[int, Unit]] = [
        (i, Unit(char_id=str(d.char_id), star=int(d.star or 1)))
        for i, d in enumerate(deployed)
        if d is not None and d.char_id]
    if name:
        v_bench.append((len(bench), Unit(char_id=name,
                                         star=int(star or 1))))
    # 不动点连锁(轻量计数形态;分组键 = 同名同星,场上项先入组 =
    # 载体扫描序,逐级重扫直到不再触发)。分组/摘除按**当前列表位次**
    # 承载(origin 是 provenance 不参与位次运算——合成消耗后列表收缩,
    # 按位次降序摘除才与收缩后的下标空间一致)。
    while True:
        groups: dict[tuple[str, int], list[tuple[int, int]]] = {}
        for dom, pool in ((0, v_field), (1, v_bench)):
            for pos, (_origin, u) in enumerate(pool):
                groups.setdefault((str(u.char_id), int(u.star or 1)),
                                  []).append((dom, pos))
        merged = False
        for (cname, cstar), locs in groups.items():
            if cstar >= 3 or len(locs) < 3:
                continue
            take = locs[:3]
            carrier_dom, carrier_pos = take[0]
            for dom, pos in sorted(take[1:], reverse=True):
                (v_field if dom == 0 else v_bench).pop(pos)
            pool = v_field if carrier_dom == 0 else v_bench
            pool[carrier_pos] = (pool[carrier_pos][0],
                                 Unit(char_id=cname, star=cstar + 1))
            merged = True
            break   # 结构已变,重扫
        if not merged:
            break
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
    )
    return SimAcquisition(
        bench=[(i, BenchSlot(kind='unit', unit=u)) for i, u in v_bench],
        field=[u for _i, u in v_field])


def m7_wearable_exists(owned: list[str]) -> bool:
    """M7 装备穿戴放行判定①:owned 存在穿戴类件(注册表已登记 ∧ 非工具类)。

    为什么不是「owned 非空」:快照写端按 全量含工具件,持有面
    非空 ≠ 存在可穿件;谓词必须是变换面(穿上会改变装备分布)存在性。
    未登记名(识别对齐缺失)按不可穿保守侧处理——与执行侧 wearable 过滤
    同口径(EQUIPMENTS.get 命中才进穿戴决策)。工具类名单一源 =
    ``cw_equipment_data.EQUIP_TOOL_CATEGORY``(执行侧同源消费)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIP_TOOL_CATEGORY,
        EQUIPMENTS,
    )
    return any(
        (eq := EQUIPMENTS.get(n)) is not None
        and eq.category != EQUIP_TOOL_CATEGORY
        for n in owned)


def _cap_of(session: StrategySession) -> int:
    """cap_resolved 现读(单一源 = kernel.cw_economy.cap_resolved_of_
    session;多消费位归一:商店线 R1/R2 的 g*、升级资金线门下界
    saturation_line、富余线 G_must 共用同一 resolved 链;投资覆写语境归一)。"""
    from sr_od.application.currency_war.kernel.cw_economy import (
        cap_resolved_of_session,
    )
    return cap_resolved_of_session(session)


def _s_reserve(frame: MandateFrame, session: StrategySession) -> int:
    """S 预留下界 = s_line 组装值(s_line 单一源,P48 ② 结构形状)。

    R196 症6 实装(替换旧 ``b_target(0, 0, 0)`` 退化形):S = B + 息饱和线
    分量 + Σ_w 窗口预留卡价 + E[刷费]×2,逐分量现读——

    - B(整买目标批成本):prep 帧 xp 未观测(frame 无 xp 快照)⇒ 整买
      目标未立 ⇒ B=0。**非静默 0**——分量级 None 期申报:xp_progress
      是 heavy 读字段,MandateFrame 未载;载入批落位前 B 构造性 0;
    - 息饱和线分量 = ``saturation_line(cap_resolved)``(canonical 行 10⑤⑥
      条件式的调用方供给 resolved 值,默认局 50);
    - 窗口预留卡价:窗口预留槽未标定 ⇒ 空列表(缺输入不计,保守下界);
    - E[刷费]×2 = 双刷预算,按 ``shop_refresh_cost`` 建模基价
      (REFRESH_COST_BASE:值恒基价 2)。

    默认局 = 0+50+0+4 = 54(旧值恒 0 系 b_target 零参退化,非规格)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.s_line import (
        s_line,
    )
    return s_line(0, _cap_of(session), [], REFRESH_COST_BASE)


def cheapest_member_cost(frame: MandateFrame) -> int:
    """线成员最廉成本(注册表派生,R196 症6:字面量 3 改单一源)。

    = K 成员在 CHARACTERS 注册表的最低 cost;成员全部未注册 ⇒
    ``bench_char_cost`` 同款保守估 3(未知名中费估,注册表先例)。
    消费面 = 硬约束①的金需求侧(entry 支付支撑通道)。
    """
    costs = [ch.cost for m in frame.k_members
             if (ch := CHARACTERS.get(m)) is not None and ch.cost]
    if costs:
        return min(costs)
    # 成员全部未注册(探针/语料名)⇒ 中费保守估 3(bench_char_cost 同款
    # 注册表先例:未知名 → 3)
    return 3
# (发出侧部署拒因分键族(DEPLOY_EMIT_*/_deploy_cap_full_gate/_record_
#  _deploy_emit_held/_emit_deploy_moves/_deployable)已随部署统一批丁丁批
#  纳入统一管理时删除:七桶选人族的拒因闭集与板满前置门随选人退役——选人 = 统一
#  部署搜索定型,「还有部署可做」= 差分非空(launch_deploy_pending 族,
#  发射抑制谓词随选人退役);deploy_cap_full/deploy_emit_
#  held_* 键族失去判读对象随批停产,板满帧部署由差分执行器交换交互承载。)


def _emit_unified_deploy(out: list, session: StrategySession,
                        tag: str) -> bool:
    """统一部署链动作发出(run_mandate 测试面 M1/M5 臂;阶段 5/6 丁:
    部署面 = 统一搜索定型 + 差分执行器,与 entry 第 6 步/出战链同链
    单一源 = deploy_plan.battle_chain_deploy_params;返回是否产出动作)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.deploy_plan import (
        battle_chain_deploy_params,
    )
    for _a in battle_chain_deploy_params(session):
        out.append(Emitted(_a, True, tag))
    return bool(out)


