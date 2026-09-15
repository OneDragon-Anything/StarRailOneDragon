"""货币战争 统一动作词表 + sim 推演内核机制面。

**统一词表(unified-action-factory 批2b 归一)**:全仓动作单一坐标系、
单一真相源 = 本模块。基类 ``CwAction`` + 全动作类 + ``CW_ACTION_TYPES``
运行时元组 + ``action_key`` 幂等键函数同居此处;原族B 词表
(kernel/cw_prep_actions,物理槽位 1 基)已随归一退役,该模块现仅承载
备战观察视图 PrepObservation 与点球挑选 kernel 纯函数。坐标系裁定 =
容器槽位表下标(族A 口径,0 基;ADR-0316/0392)——发射面从容器槽位表
读口直接取下标构造动作;物理槽位号仅存观察写入边与执行坐标边两边界
(design.md §2.6 换算归属)。例外 = 坐标参数化机械动作(WearEquip/
工具原子类):row/slot 字段按定义 = 画面物理排槽位 1 基(执行器拖点
直取画面 area;字段注释逐类声明)。

**推演内核正式类型 = ``CwSimFrame``**(sim 模拟环境的局面帧;旧注入
包家族 cw_sim_invest/cw_sim_piggy 已随 sim 重做删除面退役,本类现役
消费面见下「终态消费面声明」):sim 引擎整局推进的状态载体,
机制契约 = 字段集/转移规则/copy-on-write 试探语义(动作被拒返回原帧副本
续用),机制本体永不物理删除;与容器 GameState(实机真值记录模型)的
表示分界、单向同步契约与逐字段映射对账正本 =
docs/develop/sr_od/application/currency_war/game_state/fields.md §9。

**终态消费面声明**(过渡期双职责已收口):实机执行链的观察工作载体
职责随 last_state 链退役批终结——session.last_state 槽已删除,三写点
与 OCR 填帧链的局内事实宿主 = 容器单例(喂入 = read_game_state 漏斗
``_feed_board_state`` / sim 合成口 ``synthesize_from_game_state``)。
本类现役消费面 = 推演内核(sim 引擎/engine runner/机制等价性验证锁 M1
/假环境动作语义逻辑态推算),实机操作链零持有;退役指针(申报面 =
kernel/cw_intention.py ``committed_authority`` 形态注)已兑现。

策略为纯规则路线(用户裁定 2026-09-12):规则直接产出动作,决策零模拟
试探。本文件的 ``simulate`` 是单步动作应用器(纯函数),消费面终态 =
sim 引擎整局推进 / 假游戏环境动作语义逻辑态推算 / 规则实现等价性验证
(锁 M1)——策略域与实机操作链零消费:
- 现役策略(mandate_v1)决策 = mandate_v1/shop.decide_shop_action
  (容器读,纯规则分支),期望态推进 = 容器逻辑态直写
  (``cw_game_state.apply_shop_action_logic`` + 合成升星腿)。

字段多由 sim 环境剧本/重放档案构造填充;未填(None/默认)时决策安全降级。

**board 模型**(ADR-0312 口径统一):
- ``board`` = 已上阵羁绊计数(**全集口径**:factions+flows+independent+星徽装备
  贡献,per-unit 单一源 = ``cw_bond_equips.unit_bond_tags``;对齐实机
  ``board_from_tracked`` = 游戏左面板真值;口径 = 羁绊全集,非主阵营单标签)。
- ``deployed`` = bot 自己跟踪的已上阵角色(含 char_id/star/站位),用于 char_quality 评估
  已上阵的优先角色 + 站位分流。两者应一致(deployed 按羁绊全集聚合 == board)。
- simulate(DeployMove) 同时更新 deployed(槽位落位 deployed_place,ADR-0392)与 board(_recount_board 重算)。
- simulate(BuyCard) 后做 3 合 1 升星(同名同星 ≥3 → 合并为 star+1)。
"""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field


# ===== 候裁9 词汇迁移·旧路径转发(过渡 shim)=====
# 本批按定谳记录把共享词汇迁入语义宿主;下列 import 同时是
# 本模块自身运行时的供给面。旧路径消费仅剩并行在飞批文件,待其落库
# 后由收尾段 sweep 改指新居并删除本转发声明;禁新增旧路径消费。
from sr_od.application.currency_war.kernel.cw_exec_state import (  # noqa: E402
    BENCH_CAPACITY,  # noqa: F401
    DEPLOYED_BACK_CAPACITY,  # noqa: F401
    DEPLOYED_CAPACITY,  # noqa: F401
    DEPLOYED_FRONT_CAPACITY,  # noqa: F401
    PlaneNodeLedger,  # noqa: F401
    BenchChar,  # noqa: F401
    _apply_row_to_char, bench_from_compact,  # noqa: F401
    bench_occupied, bench_place, deployed_from_compact,  # noqa: F401
    deployed_occupied, deployed_place, deployed_slot_no,  # noqa: F401
    fill_boss_by_position, get_node_ledger, iter_occupied,  # noqa: F401
    iter_deployed_slots, iter_occupied_deployed, ledger_node_type,  # noqa: F401
    ledger_update_plane,  # noqa: F401
    pad_bench, pad_deployed, rebuild_deployed_from_board,  # noqa: F401
    snapshot_copy,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (  # noqa: E402
    _apply_full_bench_merge_buy, _merge_bench,  # noqa: F401
    count_merge_material_blocked, merge_buy_completes, merge_buy_k,  # noqa: F401
    merge_material_reject_reason, merge_material_stale_names,  # noqa: F401
    same_star_count, star_base_copies, will_merge_on_buy,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_economy import (  # noqa: E402
    DIFFICULTY_HP_TABLE, HP_SAFE_THRESHOLD, MAX_PLAYER_LEVEL,  # noqa: F401
    REFRESH_COST_BASE,  # noqa: F401
    XP_CLICK_COST_FALLBACK, XP_PER_BUY, XP_TO_NEXT_LEVEL,  # noqa: F401
    bench_char_cost, card_cost, effective_hp_threshold,  # noqa: F401
    sell_refund, xp_apply_clicks, xp_clicks_to_level,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_bond_equips import (  # noqa: E402
    _recount_board,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (  # noqa: E402
    board_unique_key,  # noqa: F401
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
    # 升星预览✦数(商店牌 art 头顶显影,ADR-0416):= 已持同名同星副本份数,
    # 买第 3 张即 3合1 升星——bot tracking merge_progress 的视觉印证(观测层冗余信号)。
    # 坐标系 = 商店牌-N area crop 顶部带本地像素(read_merge_preview);取值时机 = 进店帧快照。
    # 0 = 无✦,**双义**(真无副本 ∨ 读不到 fail-silent)——消费方按「未观测」对待,
    # 不得当「确认无副本」做否定性决策;sim 不建模(恒 0,视觉信号离线无源)。
    merge_preview: int = 0
    # cost 的信源(费用徽章数字识别批,2026-09-02):'badge'=画面费用徽章直读
    # (费用读数=实付价,星级=读数÷roster 费的倍数 {1,3,9}→1/2/3★);
    # 'roster'=roster 查表(sim/replay 构造路径缺省);
    # 'roster_fallback'=徽章失读/倍数推不出,退回 roster 查表按原费用记 1★。
    # 供金账对账区分「徽章直读」与「查表派生」(2星/3星直出识别缺口闭环,
    # merge_mechanics §2.6/§2.7)。
    cost_source: str = 'roster'


@dataclass
class CwSimFrame:
    """一回合决策时的局面快照(由 OCR 填充 + bot 跟踪)。"""
    gold: int = 0
    round_num: int = 1     # 位面内轮次 1-6
    node_type: str | None = None   # 当前节点类型(boss/补给/遭遇/巨星/投资/战斗/精英/奖励;顶部标签 OCR;None=未识别)
    enemy_difficulty: int | None = None   # 当前敌人难度(左上角 文本-难度,两级管线读法见 ADR-0449;boss 血量 base×1.052^难度)。None=未读到(补给帧无旗牌/管线未命中;合理带 [20,300] 外拒信)
    # 难度真伪保真位(读链翻转后真读/回退可分,对齐 hp_readable 模式):
    # True=当轮逐帧真读(备战「文本-难度」OCR 命中);False=回退简报恒值(session,
    # 开局写死 ≈108 不随轮爬升)或双源皆无。判读侧据此过滤:**False 帧的值别当
    # 「难度 vs 轮次」爬升曲线样本**。
    enemy_difficulty_live: bool = False
    level: int = 1         # 玩家等级 = 可上阵数上限基准(封顶 10)
    # level 值来源保真位(对齐 hp_readable 模式):
    # True=等级来自真实观测(OCR 直读或 XP 分母反推至少一源可读);False=纯
    # ``_expected_level`` 启发式兜底值(OCR 与 XP 双失读)——遥测上「兜底 4」与
    # 「真读 4」此前不可分,判读侧据此过滤 False 帧的 level 曲线样本。
    # 默认 True 仅供 sim 恒真读帧约定与旧档案缺省(按现有判读处理),真读帧由
    # 读取端(read_game_state)显式写。
    level_readable: bool = True
    # None = 未读到(shop 态/动画)。level 升级时机决策用(替代纯 _expected_level 估)。
    xp_progress: tuple[int, int] | None = None
    # 部署上限真值(= level + 财富宝钻数,可叠加;实机局实证)。
    # None=未读到/防抖拒信 → max_units() 兜底 level(ADR-0286)。防抖门在
    # cw_observation.read_deploy_cap_debounced(cap<level 或 |cap-level|>2 重读一帧,仍异拒)。
    deploy_cap: int | None = None
    level_up_cost: int | None = None      # 买一次经验的花费(文本-购买经验金币数;None=未读到,用 XP_CLICK_COST_FALLBACK 兜底)
    shop_refresh_cost: int = REFRESH_COST_BASE  # 刷新实付金 = 基价 2(REFRESH_COST_BASE 建模常量,注释见其声明)。不再由 OCR 填充——「文本-刷新金币数」rect 读的是面板徽标(=min(gold//10,5) 利息数值)非刷价(ADR-0456);字段保留为消费点契约(全 ``or 2``,值恒基价零波及)
    streak: int | None = None             # 连胜/连败数(带符号:正=连胜 / 负=连败,结算「连胜×N」前缀=方向,fixture 核实 2026-08-11;None=未读到)
    plane: int = 1         # 位面 1/2/3
    selected_difficulty: str = ""   # 本局职级 A1..A8 / A8-1..A8-50(难度确认屏检测;""=未检测→阈值回退默认;effective_hp_threshold 用;两阶难度详 docs/game/gameplay/currency_war.md:此=职级,enemy_difficulty=数值)
    hp: int | None = None  # 小队生命值(锁血决策用)。**None 化(ADR-0491)**:无真值即 None——读不到且 session 无沿用真值(last_hp_real)时 = None,不再兜底 100(「开局兜底 100」旧语义已废止:开局血量随难度/词缀变不恒 100,兜底值是「看起来像真值」的假值)。读不到但有真值 → 对账层沿用 last_hp_real(int)。消费点对 None 一律保守(血线触发条件不触发/授权位门 fail-closed),hp_readable/hp_trusted 两位语义不变。默认构造 CwSimFrame()=未观测态(hp=None;hp_readable 默认 True 仅供 sim 恒真读帧约定,真读帧由读取端显式写)。开局无真值帧由对账层填**初值表先验**(实证档 A8/108 → 82/62,readable=False,先验非真读;ADR-0559,cw_opening_hp),无实证档仍 None)
    # hp 值来源可读位(ADR-0282;False=读不到,hp 此时为沿用值/兜底值;遥测保真,决策不用)。
    # 两来源,True 时可信度等同真读:
    # ①真读=OCR 备战 HP 区;②结算=结算屏「小队生命值」经新鲜度门写入。
    # r1(位面1轮次1)备战帧血量画面可见:读到的值即真读;读失败(重试后
    # 仍 miss)=诚实未知,telemetry 层 trace.hp=None,严禁 100 兜底
    # (shop._r1_retry_read_hp + recorder 写入口径)。
    hp_readable: bool = True
    # hp 值可信位(ADR-0282 对账层语义细分;ADR-0431 帧龄门收紧):True=hp
    # 是可信值(真读且过下行守卫的帧,或**同节点内**沿用了 session.last_hp_real
    # 真值的帧——shop 开态帧间无战斗,值必然未变);False=跨节点沿用帧
    # (期间可能发生未观测战斗)/被下行守卫拒信帧(SUSPECT 态)/「开局全无
    # 真值兜底 100」的假值帧。写入点唯一=read_game_state(按对账结果 +
    # last_hp_real_node==当前节点号派生)。默认 False=未知帧按不可信处理
    # (保守);决策消费=posture_release.flip_hit 假帧守卫(hp_readable or
    # hp_trusted:同节点沿用真值帧可评估,兜底 100 帧仍拒;谓词口径零改)。
    hp_trusted: bool = False
    # gold/board 可读保真位(ADR-0213;对齐 hp_readable
    # 模式——int/dict 契约下动画帧 miss 与真值不可区分;消费方
    # 遥测/对拍用,决策默认不用)。
    gold_readable: bool = True     # gold 是否真读到(False=0 是 miss 兜底)
    board_readable: bool = True    # board 是否真读到(⚠ 空 dict 双义:真清空≠动画空——真清空时本位仍 True)
    # board = 已上阵阵营计数(OCR 左面板)。deployed = bot 跟踪的已上阵角色(含身份/站位)。
    board: dict[str, int] = field(default_factory=dict)
    # board_next_tier = 各阵营「下个 tier 阈值」(左面板 "X/Y" 的 Y;doc 13 FactionState.next_tier)。
    # 聚焦裁切 OCR 才稳读(全屏把 "2/3" 误读 "213")。comp/progress 评分用「距下个 tier 几人」;默认空(未接/未读到)。
    board_next_tier: dict[str, int] = field(default_factory=dict)
    # deployed = 槽位语义模型(ADR-0392):**定长 DEPLOYED_CAPACITY(10)槽表**,
    # 元素 BenchChar | None(空槽);下标 0-3 = 前排槽 1-4、4-9 = 后排槽 1-6
    # (BenchChar.position_pref='front'/'back' 与 slot 1-based 排内槽号保留为
    # 信息位;权威槽位 = 下标)。卖出/下场置 None 不移位 → deployed_idx 跨
    # 动作组恒稳(同轮多笔 SellDeployed 不可能再漂移);容量判据 = 占用数
    # (``deployed_occupied``),**禁止 len(deployed)**;迭代一律
    # ``iter_occupied_deployed``(裸 for 会撞 None)。
    deployed: list[BenchChar | None] = field(default_factory=list)
    shop: list[ShopCard] = field(default_factory=list)
    # bench = 槽位语义模型(ADR-0316):**定长 BENCH_CAPACITY(9)槽表**,
    # 元素 BenchChar | None(空槽);列表下标 0-8 = 物理槽位 1-9 减一
    # (BenchChar.slot 保留 1-based 屏幕槽号,信息位;权威槽位=下标)。
    # 卖出/上阵置 None 不移位 → 索引跨动作组稳定(同轮多笔 SellBench
    # 不可能再漂移);容量判据 = 占用数(``bench_occupied``),**禁止
    # len(bench)**;迭代一律 ``iter_occupied``(裸 for 会撞 None)。
    bench: list[BenchChar | None] = field(default_factory=list)
    # bench 是否真读到(对齐 board_readable 门模式;消费口 = 合成口
    # cw_game_state.synthesize_from_game_state 的 bench 写门)。空表双义与
    # board 同形:「真真空(全部署)」≠「漏斗未读」——v1 漏斗不读 bench
    # 身份(read_game_state,席位通道声明见 cw_observation._feed_board_state),
    # 其帧恒带默认空表,合成若不设门会把容器内 prep 装配环的真读观察
    # 覆盖成「9 槽全空」(未读域≠真空域;禁拿 CwSimFrame 兜底默认值当
    # 观察)。sim 真值帧恒可读(缺省 True),行为不变。
    bench_readable: bool = True
    # 3 位面 boss 名(strategy/06;session.briefing_bosses 同步)。
    # 元素 None = 该位面徽章态无身份(ADR-0398,boss_fit 跳过 None 项)
    plane_bosses: list[str | None] = field(default_factory=list)
    # 开局环境 + 敌人词缀(select_comp / mechanics_fit 用;decide_event 选完写 active_env,实机 OCR 写 enemy_affixes)
    active_env: str = ""                       # 已选投资环境名(如"昼之半神概念股";ENV_COMP_AFFINITY 用)
    enemy_affixes: list[str] = field(default_factory=list)   # 当前位面/节点敌人词缀(MECHANIC_COUNTERS/SYNERGIES 用)
    # 持有装备名(OCR 装备区填;comp 相关 equip_fit 用,详 cw_comps)。阶段 4 接线前默认空。
    equips: list[str] = field(default_factory=list)
    front_max: int = 4    # 前排槽位上限(恒 4,非观察事实;板容量封顶 = 4 + back_max,见下)
    # [供数收口] 本字段 = 全部容量消费的供数收口(max_units 封顶/back_overflow
    # 阈值/back_left 空位/排路由),动态真值 = BoardState.back_layout(三信号
    # 裁决,值域 6-9:平常 6,宝钻/召唤物扩展上限 9,机制正本 =
    # board_structure.md;6/7/8/9 四档均已交互建档,>9 域外按 8 格超集 + superset 标记
    # 运行)。默认 6 = 机制基线,仅作容器空壳引导窗兜底,勿当真值源。
    back_max: int = 6
    # 商店开态概率条真值 {费用档 1-5: 概率}(轮岗接线:投资环境轮岗每备战阶段随机
    # 翻倍一档,概率条直接印在商店上,OCR 即真值;None=未读/商店关 → _sample_cost 退基线表)
    refresh_probs: dict[int, float] | None = None
    # 节点序列由 cw_node_reader.NodeSlot 承载(read_node_sequence 直连消费方)。
    # (dual_track_phase/focus_factions 两字段已随 last_state 链退役批删除
    #  (对账表 E 类行 30/31 兑现,不迁容器):双轨判定真家 =
    #  cw_intention.committed_from(session) 权威派生;flex 白名单真家 =
    #  StrategyState.focus_factions(方向刷新写入),决策读端走策略态。
    #  帧回填点(原 cw_op_buy_cards 装配位)同批删除。)
    active_strategies: list[str] = field(default_factory=list)  # 已持有投资策略(局中选,可多张;影响经济/难度)
    # 动作v2 账本(契约包 C1,步2):显式动作(SellDeployed/SwapDeploy)
    # 的执行结果逐条记录(applied/rejected + reason)
    # ——事务拒绝必须可见(checks 消费;冻结 invariant「拒绝记录进账本」)。
    # 三消费面:策略不读(决策禁依赖账本);遥测经 sim ledger 的 actions
    # 序列化间接可见;sim 代理 = 本字段自身(simulate 写、cw_sim 转录)。
    # 旧动作(BuyCard 等)不记(零行为变化)。
    action_log: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        """bench/deployed 槽位模型(ADR-0316/0392):构造/反序列化 pad None
        到定长 9/10(紧缩前缀顺延占用 0..n-1——旧紧缩构造兼容,与 pad_bench
        同式)。

        传入超长(>定长)= 非法输入,保留原样由容量检查暴露(不静默截断)。
        """
        if len(self.bench) < BENCH_CAPACITY:
            self.bench = list(self.bench) \
                + [None] * (BENCH_CAPACITY - len(self.bench))
        if len(self.deployed) < DEPLOYED_CAPACITY:
            self.deployed = list(self.deployed) \
                + [None] * (DEPLOYED_CAPACITY - len(self.deployed))

    def copy(self) -> CwSimFrame:
        return deepcopy(self)

    def max_units(self) -> int:
        """可上阵数:deploy_cap 真值(= level + 宝钻,ADR-0286)优先,level 兜底;
        封顶 = front_max + back_max = 4 + back_max(back_max 动态真值 =
        BoardState.back_layout,值域 6-9 → 封顶值域 10-13;基线局 4+6=10)。

        全部消费点(decision_v2/kernel/operations)经本单点收口——cap 接线只改此处即全接。
        deploy_cap < level(防抖漏网噪声)视为不可信,兜底 level。
        """
        base = (self.deploy_cap
                if self.deploy_cap is not None and self.deploy_cap >= self.level
                else self.level)
        return min(base, self.front_max + self.back_max)

    def deployed_count(self) -> int:
        return deployed_occupied(self.deployed)   # ADR-0392:占用数,非 len

    def front_count(self) -> int:
        return sum(1 for c in self.deployed
                   if c is not None and c.position_pref == "front")

    def back_count(self) -> int:
        return sum(1 for c in self.deployed
                   if c is not None and c.position_pref == "back")

    def bench_is_full(self) -> bool:
        """备战席是否满 = 占用派生(bench_occupied >= BENCH_CAPACITY,§3.2.5)。

        席满判定正本 = BoardState 派生(kernel/cw_game_state.bench_is_full,
        同式同源);本类无警告位字段(「备战席已满」警告太短暂不可靠采样,
        通道退役有测试墓碑,§3.2.5)。
        """
        return bench_occupied(self.bench) >= BENCH_CAPACITY


def bench_clear(bench: list[BenchChar | None], idx: int) -> BenchChar | None:
    """清空占用槽(卖出/上阵语义:置 None 不移位);空槽/越界返回 None。"""
    if 0 <= idx < len(bench) and bench[idx] is not None:
        bc = bench[idx]
        bench[idx] = None
        return bc
    return None


def deployed_clear(deployed: list[BenchChar | None], idx: int) -> BenchChar | None:
    """清空占用槽(卖出/下场语义:置 None 不移位,ADR-0392);空槽/越界返回 None。"""
    if 0 <= idx < len(deployed) and deployed[idx] is not None:
        bc = deployed[idx]
        deployed[idx] = None
        return bc
    return None


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
# 执行期索引);发射面从容器槽位表读口(bench_slots_of/deployed_slots_of)
# 直接取下标构造动作。物理槽位号(BenchChar.slot 信息位,1 基)仅存两边界,
# 各只允许一处换算函数:①观察写入边(observe/reconcile 写链);
# ②执行坐标边(executor 单点;kernel 助手 = ``cw_exec_state
# .deployed_row_slot``/``deployed_idx_of``)。坐标参数化机械动作
# (WearEquip/工具原子类,见备战域节)的 row/slot 字段 = 画面物理排槽位,
# 属动作参数定义,不在换算边辖域。

@dataclass
class CwAction:
    """货币战争动作标记基类(策略 → 框架的单步意图载体;统一词表全类
    公共祖先,sim 侧运行时 isinstance 检查统一用本基类)。

    ``route_tag`` = 发射臂路线标签(备战旗标状态机 §3.3;桥
    ``bridge.decide_from_turn`` 从 ``Emitted.reason`` 透传,动作自带、
    无时序错位面)。定位 = 策略内部路由键(发射分支的构造事实,不随
    时间漂移、不维护状态),只回答「该次落地该不该清 S1 开店闩」的
    环路控制路由问题,**非**卖出资格面(资格单一源 = sell_gate 装配 A)
    、非放行证据(治理立场对表:禁检查器采信)。值域:现役发射位
    = m4_fuel_sell / interest_prep(单帧锁
    ``test_route_tag_whitelist`` 锁映射表)。kw_only 缺省 '' ⇒ 构造调用
    全向后兼容(归一前族A 类无本字段,sim 构造面零改动)。
    """
    route_tag: str = field(default='', kw_only=True,
                           metadata={'action_key_exclude': True})


@dataclass
class BuyCard(CwAction):
    card: ShopCard
    reason: str = ''   # 买入分类(① 账本 reason 单一源;line/bridge_seed/p2_core/pair/engine/board_focus/emergency/swap/plan;''=旧调用未标)


@dataclass
class SellBench(CwAction):
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
    (对齐 SellDeployed/SwapDeploy 既有守卫形态)。
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
    reason: str = ''           # 卖出通道记录字段(记录非指令,仿 LevelUp.auth_basis 形态;
    #                            ''=未标,缺省形态)。现役发射侧唯一承重值 =
    #                            line_switch_collapse(线账闭合孤儿证明标记,
    #                            SELL_BENCH_REASONS;纯归因
    #                            通道值填充已随 2026-09-08 用户归因遥测删除
    #                            指令拆除);sim 账本 SellBench 行
    #                            sell_reason 键转录本字段,检查器孤儿豁免
    #                            分支据此判定(豁免键集 =
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
    #                            并读零双源;sim 账本 SellBench 行
    #                            convert_reason 键转录本字段(engine_p1
    #                            转录块)后检查器方可读。


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
# funding 两键)经 SellBench.convert_reason 结构化字段填充(值域收窄,
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


# 卖出发射位值域闭集(2026-09-08 用户归因遥测删除指令后 = 唯一承重
# 值)。原 ADR-0585 §3 批 4 的 5 通道值中,仅 line_switch_collapse 有
# 存活填充位(凑息回拉换线闭合卖出载体+商店孤儿证明打标链);其余
# 通道值/转化特化值的发射位填充已全撤,无填充位的枚举值不保留。
# 转化特化值单一源 = 上方 SELL_BENCH_CONVERT_REASONS(同轮买卖
# 检查豁免键集,保留)。新增发射位先在此登记再接线(登记门:值漂移
# 由 test_cw_sell_reason_matrix 双向暴露)。
# (unified-action-factory 批2b 自 kernel/cw_prep_actions 迁居,与
# SELL_BENCH_CONVERT_REASONS 同居;来源语义与登记门不变。)
SELL_BENCH_REASONS: frozenset[str] = frozenset({
    'line_switch_collapse',     # 线账闭合孤儿清算(ADR-0591 证明打标制)
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


@dataclass
class LevelUp(CwAction):
    cost: int        # 本次「购买经验」单击花金(ADR-0129:一次点击 = +XP_PER_BUY 经验,非整级;凑够门槛才升级)
    auth_basis: str = ''
    # 授权依据**记录**字段(非指令;ADR-0354):
    # 放行臂名('pop_slot'=①[33]人口位 / 'dp'=②DP 花费授权 /
    # 'static_ev'=③静态 EV 平台账;''=未过 ev.levelup_ev_authorized 的
    # 旧调用/未接线路径)。由 arbiter 升级门与 remediation 补偿臂在
    # **放行时**写入(sim 账本 actions 侧序列化为 LevelUp 行的 auth 键,
    # 检查器 levelup_interest_engine_gate 消费)。仿 SellBench.income
    # 「记录不是指令」形态——执行层不读此字段,行为零改动。


@dataclass
class LevelUpShop(LevelUp):
    """商店开画面专用升级意图(W970 §4.1.3 / W971 §2.8.2:LevelUp 拆 LevelUpShop)。

    唯一产出者 = ``decide_shop_screen``(商店屏接口);兼容期旧入口(已随退役批删除)
    ``decide_prep`` 仍产出基类 ``LevelUp``——两入口行为由构造保证等价,
    类型拆分只为执行器/遥测/对拍**消歧**(商店屏动作 vs 备战屏腾席链
    升级)。**刻意设计成无新字段的子类**:执行器(shop 买牌循环)与
    sim/simulate 全部按 ``isinstance(a, LevelUp)`` 消费,子类零改动兼容;
    对拍口径 = LevelUpShop ≡ LevelUp(同字段逐项全等,类型归一后比较)。
    """

    # 显式重声明继承字段:kwarg 签名审计(ast 静态)不追 dataclass 继承链,
    # 不重声明则 decide_shop_screen 的 LevelUpShop(cost=…, auth_basis=…)
    # 构造被误判 kwargs 违例(2026-09-02 L3 暴露)。
    cost: int = 0
    auth_basis: str = ''



@dataclass
class DeployMove(CwAction):
    """bench → 上阵(某排)。

    [坐标系] bench_idx = bench 槽位表下标 0-8(ADR-0316 定长 9 槽)。
    上阵落位物理槽 = 执行坐标边现读首空位(kernel ``empty_deploy_slots``
    同式);``faction`` = 上阵后 board 阵营计数所需,发射位从容器槽位表
    角色对象现取(simulate 的 DeployMove 分支消费此字段)。
    """
    bench_idx: int
    # [索引定义] 坐标系: bench 槽位表下标 0-8(ADR-0316;同 SellBench.bench_idx)
    #             取值时机: 生成期=执行期(槽位表恒稳;simulate/mutate 按
    #             下标读槽并置 None)
    to_row: str      # "front" / "back"
    faction: str     # 该角色阵营(上阵后 board[faction] += 1)


@dataclass
class RefreshShop(CwAction):
    cost: int = 0    # 刷新花费(实机 OCR 补)
    # 触发源**记录**字段(非指令;先例 = LevelUp.
    # auth_basis / SellBench.income 的「记录不是指令」形态——执行层
    # 不读此字段,行为零改动)。值域(发射位单一源 = mandate_v1/shop
    # R1 发射位,今日唯一刷新发射点;L2 补位=买卡、L3 末位=升级,
    # 结构上不产刷新动作,槽位留作未来发射点扩展):
    # - 'r1'                 = 息线门 R1(域外常规承诺账);
    # - 'must_spend_r1_yielded' = 必花域内 R1 切分线(核算账降排序
    #   yielded 支);
    # - '' = 旧调用/未标(引擎 obs 归 'other' 桶)。
    reason: str = ''


@dataclass
class CloseShop(CwAction):
    """关店终结动作(ADR-0517 决策 4/5/6:商店画面的恒可用终结 op)。

    单动作架构(ADR-0517)下「无动作可做」的表达 = 策略器主动选关店终结
    op,取代旧「空序列 = 决策完成」契约;全函数契约(决策 5)要求动作空间
    至少含一个恒可用终结(决策 6)——本类即商店画面的该终结。执行侧语义
    = 本画面 op 结束、交回外循环(关店点击由编排壳 CwOpCloseShop 承担,
    与旧「空序列触发关店」同一落点);``simulate`` 对其 no-op(期望态随
    终结作废,由下一次入口观察重建)。
    """
    reason: str = ''   # 账本 reason(''=默认)


@dataclass
class PickEvent(CwAction):
    """选事件选项(投资环境/策略/遭遇/补给)。

    refresh(重立判据,ADR-0600;旧「阈值建议」判据已退役,
    现判据 = 零阈值结构存在性,推导与优势论证见 ADR-0600 §3.2 +
    math_proofs P81,env kind 不启用见 ADR-0600 §2/§4):「建议刷新」布尔 =
    ``refresh_slots`` 非空。**纯建议**——是否真刷由 handler 决定(逐槽计数
    现读 >0 才点;刷新失败/次数 0 → 照常选当前最优,失败安全 = 现状行为)。
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


@dataclass
class SellDeployed(CwAction):
    """卖场上单位(deployed 生命周期开口;不再'只增不减')——契约包 C1。

    [坐标系] deployed_idx = state.deployed **槽位表**下标 0-9(ADR-0392;
    front 0-3 / back 4-9,空槽 None,卖出置 None 不移位——索引跨动作组
    恒稳)。
    """
    deployed_idx: int
    # [索引定义] 坐标系: deployed 槽位表下标 0-9(ADR-0392 定长 10 槽,空槽
    #             None)
    #             取值时机: 生成期=执行期(槽位表恒稳,卖出置 None 不移位)
    income: int | None = None  # 预期回金(sell_refund 口径;None=未标;记录非指令,同 SellBench)
    reason: str = ''           # 账本 reason(如 'evict_replaced'/'plugin_recycle')
    expect: str = ''           # 遥测观测字段(ADR-0392 降级:槽位恒稳后不再承担
                               # 拦截漂移职责,记录生成期期望名供判读对照;
                               # 校验保留——名不符仍是跨代际提案的拒绝信号)


@dataclass
class SwapDeploy(CwAction):
    """bench ↔ deployed 换位(场上场下对调;装备随人走)——契约包 C1。

    [坐标系] deployed_idx = state.deployed 槽位表下标 0-9(ADR-0392)/
    bench_idx = bench 槽位表下标 0-8(两域均定长槽位表,索引恒稳)。

    装备随人走 = 换位移动 BenchChar 对象本身(``equips`` 字段随对象迁移,
    无单独装备转移步骤);上场者继承下场者的排(``position_pref``),
    开拓者按目标排做形态归一(同 DeployMove 语义,单一源)。
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


Action = (BuyCard | SellBench | LevelUp | DeployMove | RefreshShop | CloseShop
          | PickEvent | SellDeployed | SwapDeploy)


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
class ClickSpheres(CwAction):
    """点奖励球(R4 坐标参数化机械动作:载荷 = 有序球坐标点击列表)。

    ``points`` = 按点击顺序排列的球心坐标 (x, y)(1080p 游戏空间,与
    ``PrepObservation.spheres`` 的 Point 同系)。挑选逻辑(大球优先/
    上界截断)归决策侧 kernel 单一源 = :func:`cw_prep_actions
    .select_sphere_clicks`,发射位调用之;执行器纯机械逐个点,零读屏
    零排序。逻辑态按载荷精确摘球(坐标匹配,
    ``cw_screen_prep._project_prep_obs``)。
    """
    points: tuple[tuple[int, int], ...] = ()


@dataclass
class OpenBox(CwAction):
    """开补给箱(点「开启」→ 弹武装箱 overlay;开箱即腾席)。slot=None → 第一箱。"""
    slot: int | None = None


@dataclass
class OpenTome(CwAction):
    """开秘密典籍(点槽两次:选中→开启 → 弹星徽四选一;开典籍即腾席+loop 0i 接管选卡)。

    建档:投资策略「秘密典籍」给的红金典籍道具占备战席 1 槽(类补给箱);
    选卡决策在 loop 0i handler(板上阵营匹配),本动作只负责把典籍点开。slot=None → 第一典籍。
    """
    slot: int | None = None


@dataclass
class OpenBookcard(CwAction):
    """开书册卡(点槽「开启」→ 弹专家邀请函五选一;开卡即腾席)。

    书册卡 = 备战席占槽道具(与补给箱/秘密典籍并列第三件;R10 归位备战
    词表,与 OpenBox/OpenTome 同签名,design.md §2.6 R10)。选卡决策不在
    本执行链——点完开启本动作即交回,专家邀请函弹窗由外循环按画面分发
    ``CwScreenExpertInvite`` 选卡(选卡决策单一源 =
    ``cw_screen_expert_invite.choose_expert_index`` 原位);本批发射位 =
    备战环入口清场段(``cw_screen_prep._clear_prep_cards``),是否升
    director 门控留策略侧定。slot=None → 第一张书册卡。
    """
    slot: int | None = None


@dataclass
class WearEquip(CwAction):
    """穿装备(装备库 owned 件 → 目标角色物理槽位;R2 穿戴原子通路)。

    计划构造 = kernel ``build_equip_wear_plan``(自执行器模块迁居,
    决策侧逐帧现算);发射序即执行序(决策核逐帧取首项)。逻辑态 =
    ``obs.owned_equips`` 摘件(视觉域,与 OpenBox/OpenTome 同形);
    穿没穿归观察写入边对账(裁决 3 零比对出生:体内零 CV-diff 验穿)。
    ``char_name`` = 目标角色注册名('' = front-only 回退步,拖点 =
    前排空槽 avatar,与 EquipWearStep 契约同形)。
    """
    item_name: str
    char_name: str
    row: str            # 'front' | 'back'(见上方通用坐标系声明)
    slot: int           # 画面物理槽位 1 基(前排 1-4 / 后排 1-N)


@dataclass
class FurnaceUse(CwAction):
    """冶金炉(R8 按消耗品各立类;双模式)。

    - target_kind='equip':拖装备 = 原地变异同类型随机(target =
      装备库 owned 件,``item_name``;产物不可预知 → 随机面观察收口,
      ``EQUIP_WRITE_SIDES['冶金炉']`` 负写端在册);
    - target_kind='char':拖角色 = 全拆 + 每件变异随机(target =
      角色槽位,``row``/``slot``;确定面 = 穿戴域 → 库存域全量迁移,
      变异产物 = 随机面观察收口)。
    """
    target_kind: str    # 'equip' | 'char'(作用对象模式;值域封闭)
    item_name: str = ''  # target_kind='equip':装备库 owned 件名
    row: str = ''        # target_kind='char':见上方通用坐标系声明
    slot: int = 0        # target_kind='char':画面物理槽位 1 基


@dataclass
class PrivilegeCardUse(CwAction):
    """特权赋予卡(R8;双腿)。

    - target_kind='equip'(库存腿,现役执行臂):确定变换 = target 件
      名替换为对应·特权名(映射单一源 = ``cw_effect_inventory.
      privilege_counterpart``,写端 = ``transform_equip_to_privilege``);
    - target_kind='char'(拖角色腿):该角色已穿进阶装备随机一件变
      特权——「哪件被选」= 随机面 → 逻辑态只写工具 −1,选定后确定面
      归观察收口(``transform_worn_equip_to_privilege`` 桥在册)。
    """
    target_kind: str    # 'equip' | 'char'(值域封闭,同 FurnaceUse)
    item_name: str = ''  # target_kind='equip':被变换的进阶成品件名
    row: str = ''        # target_kind='char':见上方通用坐标系声明
    slot: int = 0        # target_kind='char':画面物理槽位 1 基


@dataclass
class WrenchUse(CwAction):
    """拆装扳手(R8):target = 角色槽位(取下该角色全部穿戴,装备归属
    面回区);工具消耗品 −1(用后消失)。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基


@dataclass
class PrecisionWrenchUse(CwAction):
    """精密拆装扳手(R8):target = 角色槽位(同 WrenchUse);无限次用,
    工具库存面不递减(重复获得改 +1 金 = 贡献算术,获得回执窗在册)。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基


@dataclass
class StaffProjectorUse(CwAction):
    """员工投影仪(R8 投影仪按型号两类之一):target = 角色槽位
    (在备战席创造该角色 1 星复制);费用门 = 3 费及以下(门表单一源 =
    ``cw_affix_effects`` 投影仪费用门行),门由发射位判据面辖。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基


@dataclass
class PerfectProjectorUse(CwAction):
    """完美投影仪(R8 投影仪按型号两类之二):target = 角色槽位
    (同 StaffProjectorUse 但无费用门)。"""
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基


@dataclass
class LuckyTokenUse(CwAction):
    """好运令牌(R8):拖到角色 → 从其推荐进阶装备中获得一件。

    ⚠️ 发射位挂账(裁决 1/R9 纪律):作用对象判据面现役 fail-closed
    永不进准入(``cw_equip_env.evaluate_tool_actions`` rc_missing 拒因
    在册)——类随族立档 + 注册行,发射位禁无判据发射;判据面建模批
    补档(知识缺口登记 = ``flow/action-logic-state.md`` §7 好运令牌行)。
    """
    row: str            # 见上方通用坐标系声明
    slot: int           # 画面物理槽位 1 基


@dataclass
class OpenShop(CwAction):
    """开商店意图(W970 批 C/§4.3.6;EnsureShop 意图退役后的承接形态)。

    read_only=False:显式开店 → 流程层编排商店动作循环(观察→decide_shop_screen
    →波执行→空序列 CwOpCloseShop→节点探针)。
    read_only=True:读数性开店(腾席链 b 取 gold 真值 / 开态清洁面板)→
    CwOpOpenShop(幂等:已开不点)→ 商店观察刷新 → **不调商店决策** →
    CwOpCloseShop → 回备战(M-6 门保持:free=0 不进买牌)。
    """
    read_only: bool = False


@dataclass
class StartBattle(CwAction):
    """出战(环出口;含未达上限确认;验证=备战标识消失)。StartBattle 豁免屏蔽。"""


# 动作全集白名单(统一词表运行时元组;注册完备锁的遍历单一源,批4
# 消费 = 逐类断言注册表解析可命中。新动作加入全集时同步此处——漏登记
# ⚠️ 教训(原 PREP_ACTION_TYPES 先例):**新增动作必须同步登记本白名单**
# ——漏登记时执行面 validate 拒「未知动作类型」,动作从未真正执行
# (OpenTome 曾漏登记,数百次拒绝被误读为执行失败;登记是入口门)。
CW_ACTION_TYPES: tuple = (
    BuyCard, SellBench, LevelUp, LevelUpShop, DeployMove, RefreshShop,
    CloseShop, SellDeployed,
    ClickSpheres, OpenBox, OpenTome, OpenBookcard,
    WearEquip,
    FurnaceUse, PrivilegeCardUse, WrenchUse, PrecisionWrenchUse,
    StaffProjectorUse, PerfectProjectorUse, LuckyTokenUse,
    StartBattle,
    OpenShop,
)


def action_key(action: CwAction) -> str:
    """动作实例键(屏蔽计数粒度 = 动作类型 + 参数;SellBench(3) 与 SellBench(5) 各自计数)。

    带 ``action_key_exclude`` metadata 的字段不入键(现役 =
    SellBench.reason 卖出归因 + CwAction.route_tag 发射臂路线标签
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
            return type(action).__name__   # 无字段 dataclass(StartBattle 等)→ 裸名
        return f'{type(action).__name__}({params})'
    return type(action).__name__


def _card_to_bench(card: ShopCard, position_pref: str = "back") -> BenchChar:
    """买的牌落 bench。"""
    return BenchChar(slot=0, char_id=card.name, faction=card.faction,
                     star=card.star, position_pref=position_pref)


def _log_action(s: CwSimFrame, action_name: str, result: str,
                reason: str = '', **extra) -> None:
    """动作 v2 账本写入(契约包 C1 冻结 invariant:拒绝记录进账本)。"""
    entry: dict = {'action': action_name, 'result': result}
    if reason:
        entry['reason'] = reason
    entry.update(extra)
    s.action_log.append(entry)


def simulate(state: CwSimFrame, action: Action) -> CwSimFrame:
    """单步动作应用(纯函数):返回应用 action 后的**新** CwSimFrame
    (不改原 state)。消费位 = sim 引擎整局逐步推进 / 假游戏环境动作转移 /
    规则实现等价性验证(锁 M1 等);策略决策零消费(纯规则路线)。

    买入落 bench(3 合 1 自动升星);上阵(DeployMove)把角色从 bench 移到 deployed +
    board[faction]+=1(保留身份/站位供 char_quality 与站位分流用)。

    C6 装备守恒对账(W38):装备相关动作(BuyCard/SellBench/SellDeployed/
    SwapDeploy)执行前后跑账本快照比对——mismatch 记
    action_log(``EquipsLedger`` 条目,checks/遥测可见),不静默(cw_bench_equips 单一源)。
    """
    from sr_od.application.currency_war.kernel.cw_bench_equips import (
        ledger_mismatch,
        state_equips_multiset,
    )
    s = state.copy()
    pad_bench(s.bench)   # ADR-0316 定长不变量:调用方可能构造短 bench
    # (直接赋值绕过 __post_init__);copy 不触发 __post_init__,入口防御 pad
    pad_deployed(s.deployed)   # ADR-0392 同理(deployed 槽位表定长 10)
    _equips_action = isinstance(action, (BuyCard, SellBench, SellDeployed,
                                         SwapDeploy))
    _pre_equips = state_equips_multiset(state) if _equips_action else None
    if isinstance(action, BuyCard):
        # ADR-0316 槽位语义:买入放首个空槽;无空槽=拒(bench_full 语义
        # 不变——金不扣、牌不下架,整动作 no-op)。
        # S3(ADR-0325):**合并买入**例外——满员也通,新卡临时挂槽位表
        # 尾部参与 _merge_bench(合成后恒被消费置 None),再截回定长 9。
        # ADR-0453:满栏判据从「买第 3 份同名 1★(k=1)」升级为
        # merge_mechanics §2.5 一般式——k = min(店内张数, 3−已有数 mod 3)
        # 张一次买入(游戏自动多买,无价格优惠:金账按 k×单价记全款),
        # 判据单一源 = merge_buy_completes(不满足仍拒,ADR-0283 兜底)。
        new_bc = _card_to_bench(action.card)
        placed = bench_place(s.bench, new_bc) is not None
        if not placed:
            _name = action.card.name
            _star = action.card.star or 1
            # 分支应用单一源 = _apply_full_bench_merge_buy(与运行时
            # tracked mutate 共用,双账同构;判据面不变 = merge_buy_completes
            # 不满足仍拒,ADR-0283 兜底)。
            _k = _apply_full_bench_merge_buy(s.bench, s.deployed,
                                             action.card, s.shop)
            if _k is None:
                return state.copy()
            s.gold -= card_cost(action.card) * max(1, _k)
            # 合成恰耗尽本次 k 张(own+k ≡ 0 mod 3),尾部临时槽恒被清,
            # 截回定长 9;店侧 k 张同身份牌全部下架(自动多买语义)。
            _left = max(1, _k)
            _kept: list[ShopCard] = []
            for c in s.shop:
                if _left > 0 and c.name == _name \
                        and (c.star or 1) == _star:
                    _left -= 1
                    continue
                _kept.append(c)
            s.shop = _kept
        else:
            s.gold -= card_cost(action.card)
            _merge_bench(s.bench, s.deployed)   # 全场域(3合1 是全场;deploy_bench L427 口径)
            # 买走该槽位 → 从 shop 移除(否则 plan 贪心会重买同一张堆星,sim 不反映"槽位空了")
            s.shop = [c for c in s.shop if c.x != action.card.x]
    elif isinstance(action, SellBench):
        # ADR-0316:校验槽占用后置 None(索引跨动作组稳定)
        # ADR-0317 代际校验第三块(ADR-0326 §1.7):expect 非空且与槽内名
        # 不符 = 陈旧提案 → no-op + stale_proposal 语义(对齐
        # SellDeployed/SwapDeploy 既有守卫;emit 端=remediation 补偿器)
        _tgt = (s.bench[action.bench_idx]
                if 0 <= action.bench_idx < len(s.bench) else None)
        if _tgt is not None and action.expect \
                and _tgt.char_id != action.expect:
            _log_action(s, 'SellBench', 'rejected',
                        reason=(f'stale_proposal:{action.expect}'
                                f'!={_tgt.char_id}'),
                        char=_tgt.char_id)
        else:
            sold = bench_clear(s.bench, action.bench_idx)
            if sold is not None:
                s.gold += sell_refund(sold.star, bench_char_cost(sold))
                # 装备回收进 owned 池(C6 装备守恒;与 SellDeployed
                # 同一建模假设——卖带装单位装备回收,🟡 待 live 核。
                # 修复前本分支漏回收 = 账本凭空消失,EquipsLedger
                # 对账必报)。
                s.equips.extend(sold.equips)
    elif isinstance(action, LevelUp):
        # 真实语义(ADR-0129):一次「购买经验」= +XP_PER_BUY 经验、-单击金币;攒够当前级门槛自动
        # 升级(跨级结转溢出)。旧模型「一次动作 = 升 1 级 + 扣整级大金」与机制不符 → 升级门过度
        # 保守(以为要点 36-60 金,实际每击 4-8 金)→ 升级滞后 live 实锤(M15 进位面 2 真实 lv5)。
        if s.level < MAX_PLAYER_LEVEL:  # 封顶 10 级(单一源 MAX_PLAYER_LEVEL)
            s.gold -= action.cost
            _cur = s.xp_progress[0] if s.xp_progress else 0
            _cur += XP_PER_BUY
            while s.level < MAX_PLAYER_LEVEL:
                _need = XP_TO_NEXT_LEVEL.get(s.level, 4)
                if _cur < _need:
                    break
                _cur -= _need
                s.level += 1
            s.xp_progress = (_cur, XP_TO_NEXT_LEVEL.get(s.level, _cur))
    elif isinstance(action, DeployMove):
        _target = (s.bench[action.bench_idx]
                   if 0 <= action.bench_idx < len(s.bench) else None)
        if _target is not None:
            _k = board_unique_key(_target)
            # 同名唯一性(W43 裁决 1):单卡上场同理——已在场同名 → 拒绝
            # (进 action_log;bench 同名副本是 3合1 素材,合成走 bench 域)。
            if _k is not None and any(board_unique_key(d) == _k
                                       for d in iter_occupied_deployed(s.deployed)):
                _log_action(s, 'DeployMove', 'rejected',
                            reason=f'duplicate_on_board:{_k}')
            else:
                bc = bench_clear(s.bench, action.bench_idx)
                # 站位记录 + 开拓者换排形态归一(单一源 helper)
                _apply_row_to_char(bc, action.to_row)
                deployed_place(s.deployed, bc)   # ADR-0392:按排路由落槽
                # ADR-0312:**增量**全集计数——board 可能来自
                # OCR 真值而 deployed 尚空(生产 read_game_state 填充序),
                # 全量重算会抹掉 OCR 提供的计数;单位标签 = unit_bond_tags
                # 全集(星徽/卡带贡献在内)。
                from sr_od.application.currency_war.kernel.cw_bond_equips import (
                    unit_bond_tags,
                )
                _tags = unit_bond_tags(bc)
                if not _tags:
                    _f = getattr(bc, 'faction', '') or ''
                    _tags = (_f,) if _f and _f != '?' else ()
                for _t in _tags:
                    s.board[_t] = s.board.get(_t, 0) + 1
    elif isinstance(action, SellDeployed):
        # 动作 v2(契约包 C1,步2):卖场上单位——deployed 生命周期开口。
        if 0 <= action.deployed_idx < len(s.deployed) \
                and s.deployed[action.deployed_idx] is not None:   # ADR-0392 空槽拒
            _tgt = s.deployed[action.deployed_idx]
            # 代际校验(expect=遥测观测字段,ADR-0392):名不符 = 跨代际提案 → 拒绝不套用
            if action.expect and _tgt.char_id != action.expect:
                _log_action(s, 'SellDeployed', 'rejected',
                            reason=(f'stale_proposal:{action.expect}'
                                    f'!={_tgt.char_id}'),
                            char=_tgt.char_id)
            else:
                sold = deployed_clear(s.deployed, action.deployed_idx)
                # ADR-0392:置 None 不移位(deployed_idx 跨动作组恒稳)
                # income 是记录非指令(同 SellBench 口径):sim 侧按 sell_refund 执行
                s.gold += sell_refund(sold.star, bench_char_cost(sold))
                # 装备回收进 owned 池(🟡 游戏侧「卖带装单位装备去向」
                # 未见实机证据,按回收建模保装备守恒,待 live 核)
                s.equips.extend(sold.equips)
                s.board = _recount_board(s.deployed)
                _log_action(s, 'SellDeployed', 'applied', reason=action.reason,
                            char=sold.char_id)
        else:
            _log_action(s, 'SellDeployed', 'rejected',
                        reason=f'deployed_idx_out_of_range:{action.deployed_idx}',
                        char='')
    elif isinstance(action, SwapDeploy):
        # 动作 v2(契约包 C1,步2):场上场下对调,装备随人走(对象迁移)。
        if 0 <= action.deployed_idx < len(s.deployed) \
                and s.deployed[action.deployed_idx] is not None \
                and 0 <= action.bench_idx < len(s.bench) \
                and s.bench[action.bench_idx] is not None:
            out_char = s.deployed[action.deployed_idx]
            in_char = s.bench[action.bench_idx]
            # 代际校验(W43 裁决 2):跨轮登记的换位提案 idx 已指向别人 → 拒绝
            if (action.expect_deployed
                    and out_char.char_id != action.expect_deployed) \
                    or (action.expect_bench
                        and in_char.char_id != action.expect_bench):
                _log_action(s, 'SwapDeploy', 'rejected',
                            reason=(f'stale_proposal:'
                                    f'{action.expect_deployed}/{action.expect_bench}'
                                    f'!={out_char.char_id}/{in_char.char_id}'))
            else:
                # 同名唯一性(W43 裁决 1):上场者与场上其余单位同名 → 拒绝
                _k = board_unique_key(in_char)
                if _k is not None and any(
                        board_unique_key(d) == _k
                        for _i, d in iter_deployed_slots(s.deployed)
                        if _i != action.deployed_idx):
                    _log_action(s, 'SwapDeploy', 'rejected',
                                reason=f'duplicate_on_board:{_k}')
                else:
                    _row = out_char.position_pref
                    s.deployed[action.deployed_idx] = in_char   # 槽位语义:原槽对调
                    s.bench[action.bench_idx] = out_char
                    # 上场者继承下场者的排(含开拓者形态归一);下场者保留原
                    # position_pref 记录(回 bench 后不消费,再上场时重写)
                    _apply_row_to_char(in_char, _row)
                    in_char.slot = deployed_slot_no(action.deployed_idx)
                    s.board = _recount_board(s.deployed)
                    _log_action(s, 'SwapDeploy', 'applied', reason=action.reason,
                                in_char=in_char.char_id, out_char=out_char.char_id)
        else:
            _log_action(s, 'SwapDeploy', 'rejected',
                        reason=(f'idx_out_of_range:'
                                f'd{action.deployed_idx}/b{action.bench_idx}'))
    elif isinstance(action, RefreshShop):
        s.gold -= action.cost
        # shop 内容变化未知(随机),不模拟具体牌;仅扣金
    # PickEvent 不在本模拟范围(event 单独决策)
    if _pre_equips is not None:
        # C6 装备守恒对账:mismatch 记账本(禁静默;漂移由 checks/测试锁暴露)
        _diffs = ledger_mismatch(_pre_equips, state_equips_multiset(s))
        if _diffs:
            _log_action(s, 'EquipsLedger', 'mismatch',
                        reason=f'{type(action).__name__}:{",".join(_diffs)}')
    return s


def mutate_bench_deployed(bench: list[BenchChar | None],
                          deployed: list[BenchChar],
                          action: Action,
                          shop: list[ShopCard] | None = None) -> None:
    """就地应用 action 的 bench/deployed 转移到持久跟踪状态(运行时同步用)。

    与 ``simulate`` 的区别:``simulate`` 返回新 ``CwSimFrame`` copy(整帧副本
    语义,含 gold/level/shop 全字段);
    本函数**就地改** bench/deployed 两个列表,只做身份/星级/站位转移(buy→bench+merge / deploy→deployed /
    sell→置 None),供运行时执行点(shop.buy / deploy_bench verify / _handle_bench_full sell)同步
    ``session.bench``/``session.deployed``。转移规则与 simulate 一致(单一源,避双源漂移)。
    ADR-0316/0392:bench/deployed 均为槽位表(定长 9/10,None=空槽)——入口防御性 pad。
    LevelUp/RefreshShop/PickEvent 不影响 bench/deployed → no-op。

    ``shop``(缺省 None = 零漂移兼容):调用方的当前店面视图。提供时,
    满栏合成买与 simulate 同分支单一源——满栏时游戏对完成合成
    的买入接受并合成(bench 素材被消费腾槽),tracked 侧同走
    ``_apply_full_bench_merge_buy``,不再丢件漏记;未提供或未识别牌
    (name 空,无法判合成对象)时维持旧丢件行为。
    """
    pad_bench(bench)
    pad_deployed(deployed)
    if isinstance(action, BuyCard):
        _placed = bench_place(bench, _card_to_bench(action.card)) is not None
        if not _placed and shop is not None and (action.card.name or ''):
            _apply_full_bench_merge_buy(bench, deployed, action.card, shop)
        _merge_bench(bench, deployed)   # 全场域(live tracking 与 simulate 同源)
    elif isinstance(action, SellBench):
        # ADR-0317 代际校验(与 simulate 同源):expect 非空且不符 →
        # 陈旧提案 no-op(不移除)
        if 0 <= action.bench_idx < len(bench) \
                and bench[action.bench_idx] is not None \
                and (not action.expect
                     or bench[action.bench_idx].char_id == action.expect):
            bench_clear(bench, action.bench_idx)
    elif isinstance(action, DeployMove):
        _tgt = (bench[action.bench_idx]
                if 0 <= action.bench_idx < len(bench) else None)
        if _tgt is not None:
            # 同名唯一性守卫(W43 裁决 1,与 simulate 同源):已在场同名不上
            _k = board_unique_key(_tgt)
            if _k is not None and any(board_unique_key(d) == _k
                                      for d in iter_occupied_deployed(deployed)):
                return
            bc = bench_clear(bench, action.bench_idx)
            _apply_row_to_char(bc, action.to_row)
            # 开拓者形态切换(同 simulate 语义,单一源 helper)
            deployed_place(deployed, bc)   # ADR-0392:按排路由落槽
    elif isinstance(action, SellDeployed):
        # 动作 v2(契约包 C1):runtime 跟踪侧只做身份转移(金/装备归
        # CwSimFrame 域,本函数不管——与 simulate 单一源规则一致)
        if 0 <= action.deployed_idx < len(deployed) \
                and deployed[action.deployed_idx] is not None \
                and (not action.expect
                     or deployed[action.deployed_idx].char_id == action.expect):
            deployed_clear(deployed, action.deployed_idx)
            # ADR-0392:置 None 不移位(deployed_idx 恒稳;陈旧提案=代际不符 no-op)
    elif isinstance(action, SwapDeploy):
        if 0 <= action.deployed_idx < len(deployed) \
                and deployed[action.deployed_idx] is not None \
                and 0 <= action.bench_idx < len(bench) \
                and bench[action.bench_idx] is not None:
            out_char = deployed[action.deployed_idx]
            in_char = bench[action.bench_idx]
            # 代际校验 + 同名唯一性(W43 裁决 1/2,与 simulate 同源)
            if ((action.expect_deployed
                 and out_char.char_id != action.expect_deployed)
                    or (action.expect_bench
                        and in_char.char_id != action.expect_bench)):
                return   # 陈旧提案 no-op
            _k = board_unique_key(in_char)
            if _k is not None and any(
                    board_unique_key(d) == _k
                    for _i, d in iter_deployed_slots(deployed)
                    if _i != action.deployed_idx):
                return
            _row = out_char.position_pref
            deployed[action.deployed_idx] = in_char   # 槽位语义:原槽对调
            bench[action.bench_idx] = out_char
            _apply_row_to_char(in_char, _row)
            in_char.slot = deployed_slot_no(action.deployed_idx)




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
