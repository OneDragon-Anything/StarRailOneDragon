"""货币战争 策略状态模型(GameState + Action + 前瞻 simulate)。

策略采用「评估函数 + 贪心改进」架构(v2 决策链 = decision_v2 四层:
候选生成→硬过滤→板面评分→预算仲裁;判据单一源 = kernel):
- evaluate(state) 给局面打分(羁绊/经济/站位/角色质量);
- 决策在硬规则门内,贪心选 eval 提升最大的动作;前瞻用 simulate(state, action)。

字段多由实机 OCR 填充(见 strategy_design.md §8 接线);未填(None/默认)时决策安全降级。

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

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of

# 卖出回金 = 招募费(cost)× 合成倍数,economy_research.md §2(strategy/)。1星=cost 🟢 BWIKI+4399+用户权威;
# 2星=cost×3−1、3星=cost×9−1、4星=cost×27−1(合成成本扣1手续费;2星用户印象「少1」,
# 3/4星推测同逻辑 🟡 待 hook 实机核 —— 拖卡到出售区看显示金额)。
_SELL_MULT: dict[int, int] = {1: 1, 2: 3, 3: 9, 4: 27}   # 星级 → cost 倍数(3合1:1星1/2星3/3星9/4星27 张基础副本);sell_refund 对 star≥2 且 cost≥2 再 −1 手续费(cost=1 exempt,见 sell_refund)
BENCH_CAPACITY: int = 9  # 备战栏固定 9 槽(design doc 实测;不随等级变)
# deployed 槽位语义(ADR-0392):定长 10 槽表——下标 0-3 = 前排槽 1-4、
# 4-9 = 后排槽 1-6。后排实际格数随布局档 6/7/8 变(cw_back_layout,
# = 6+(cap−level),ADR-0385)——超过 6 的扩展格属画面布局域,不进本表示
# (表长恒 10;取舍与理由见 ADR-0392「后排布局档取舍」节)。
DEPLOYED_FRONT_CAPACITY: int = 4
DEPLOYED_BACK_CAPACITY: int = 6
DEPLOYED_CAPACITY: int = DEPLOYED_FRONT_CAPACITY + DEPLOYED_BACK_CAPACITY

# 购买经验机制(ADR-0129;用户实测口述 2026-08-15,A5+;telemetry 多局 XP 分母 4/6/20/40 对拍一致):
# 「购买经验」每点一次 +XP_PER_BUY 经验、花小额金币(按钮实读 state.level_up_cost);经验攒够当前级
# 门槛自动升级,溢出结转。等级门槛表(升下一级所需总经验):
XP_PER_BUY: int = 4
XP_TO_NEXT_LEVEL: dict[int, int] = {3: 4, 4: 6, 5: 20, 6: 40, 7: 52, 8: 72, 9: 84}
XP_CLICK_COST_FALLBACK: int = 4   # 单击经验花金兜底(level_up_cost OCR 缺失时;telemetry lv5 实测 4 金/击)

# 刷新商店实付金 = 基价常量(建模值,非 OCR 读数)。出处:多局 decisions.jsonl
# 相邻决策行金差对账(只含 LevelUp+Refresh 的最小对账对)全部 = 2,不随金币/
# 次数/等级变;invest_effects.md「刷新 45% 概率免费 → 期望刷价 1.1」隐含基价
# 2(2×0.55=1.1)。右下角「文本-刷新金币数」rect 实际读到的是面板徽标
# (数值 = min(gold//10,5) = 利息公式,非刷价;三流对拍定谳,ADR-0456)——
# 该 OCR 已退出 read_game_state 主链(cw_observation),决策/对账统一消费本常量。
# 消费点沿用 ``or 2`` 兜底语义:字段恒为基价,兜底分支不再触发,零行为波及。
REFRESH_COST_BASE: int = 2


def xp_apply_clicks(level: int, xp_cur: int, clicks: int,
                    xp_per_buy: int = XP_PER_BUY) -> tuple[int, int]:
    """N 次「购买经验」后的期望 (level, xp_cur)(纯函数;XP 期望态账本的推进算子)。

    语义 = ADR-0129 单一源:每击 +xp_per_buy 经验;攒满当前级门槛即升级、
    溢出结转(与 cw_state LevelUp 动作应用 / sim 轮末升级清零结转同规则)。
    封顶 10 级 = 生产 live 语义(10 级后购买经验无效;sim 侧 LEVEL_CAP=9
    是已知建模分歧,勿混用)。

    [字段定义] level = 游戏玩家等级 1-10(整局单调,坐标系 = 游戏 XP 条);
    xp_cur = 当前级已攒经验;取值时机 = 意图应用时纯推算(非执行期现读);
    写入端 = CwScreenPrep XP 期望态账本。clicks ≤ 0 → 原值返回(无意图零推进)。
    """
    if clicks <= 0 or level >= 10:
        return level, xp_cur   # 封顶/零意图:购买经验无效,零推进(live 语义)
    cur = xp_cur + clicks * xp_per_buy
    while level < 10:
        need = XP_TO_NEXT_LEVEL.get(level, 4)
        if cur < need:
            break
        cur -= need
        level += 1
    return level, cur


def xp_clicks_to_level(level: int, xp_cur: int,
                       xp_per_buy: int = XP_PER_BUY) -> int:
    """当前级攒到**恰升 1 级**所需的最少购买经验次数(纯函数)。

    = ceil((need − cur) / xp_per_buy);cur 已达门槛 → 1(再点一次即升)。
    消费端 = CwScreenPrep 直接 LevelUp 动作(腾席链「循环点至 level+1、
    首次验证成功即停」通道):progressed=True 时实际击数 = 本值。
    已升满 10 级 → 0(点击无效,调用方零推进)。
    """
    if level >= 10:
        return 0
    need = XP_TO_NEXT_LEVEL.get(level, 4)
    gap = need - xp_cur
    if gap <= 0:
        return 1
    return (gap + xp_per_buy - 1) // xp_per_buy

# 保血阈值(策略校准参数,ADR-0203/0204 从 config 迁入代码单一源;值随实机校准走 git,不走用户 yml)。
# **保守起步,待实机校准**:A1-A4 = 40(低难不变,可适当卖血保经济);A5+ 升阶(高难敌人更凶 → 更早弃息保血)。
HP_SAFE_THRESHOLD: int = 40    # 保血阈值默认(未检测职级时;语义「安全地板」,kernel 单一源)
DIFFICULTY_HP_TABLE: dict[str, int] = {
    "A1": 40, "A2": 40, "A3": 40, "A4": 40,
    "A5": 45, "A6": 50, "A7": 52, "A8": 55,
}


@dataclass
class ShopCard:
    """商店一张牌。"""
    x: int               # 牌位中心 x(购买点击坐标)
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
class BenchChar:
    """备战栏/已上阵角色(= strategy/06 的 ``Unit``;加 ``equips``)。"""
    slot: int
    char_id: str = ""    # 角色id(SIFT/OCR 名);未知 ""
    faction: str = "?"   # 阵营
    star: int = 1        # 星级
    position_pref: str = "back"  # 命途定位 front/back(来自 get_role_position)
    # Sequence(快照拷贝语义落码(ADR-0465 §9):TurnState 快照拷贝侧固化为 tuple;session/state
    # 活对象仍 list)——读点(deploy_bench 装备校验/reconcile 配对)均为
    # Sequence 消费,写端仅 session/state 活对象(list 语义保留)。
    equips: list[str] | tuple[str, ...] = field(default_factory=list)
    # 占槽物品标记(部署伪槽修复批 ②,防线字段;B1 返工=显式标记形态):
    # True = 该槽画面是物品(箱/典籍/书册卡/揭示卡等)非角色。坐标系 =
    # 备战栏 1-based slot(与 slot 字段同系);取值时机 = 部署装配期快照;
    # 写入端 = 部署装配点(cw_op_deploy.assemble_bench_list 构造时显式写),
    # 识别来源 = obs 单一源精确档(cw_identity_obs.bench_item_slots
    # fuzzy=False)的命中产出;obs 未命中的槽位恒 False(缺省),与本字段
    # 无关的 char_id='' 不触发(kernel 对 True 恒 held、拒因 'item_slot',
    # 「照旧上」fail-open 语义不涉本字段)。sim 不产伪槽:缺省 False 零差。
    is_item_slot: bool = False


def snapshot_copy(bc: BenchChar) -> BenchChar:
    """TurnState 快照语义的元素拷贝(落码判据见 ADR-0465 §9):浅拷贝 + equips 固化
    为 tuple——视图/快照帧与 session.tracked_*(就地写端=shop.py
    mutate_bench_deployed 星级/装备拼接、deploy_bench 装备覆盖)断开
    对象别名,「快照不在帧间存活」由机制保证而非消费纪律约定。
    成本已量化(ADR-0465 §9):每次 decide_prep ~19 元素 ×6 字段 <20µs,
    占帧预算 <0.1%。隔离锁=test_cw_migration_budget_authority(迁移哨兵)。"""
    from dataclasses import replace
    return replace(bc, equips=tuple(bc.equips or ()))


@dataclass
class GameState:
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
    hp: int | None = None  # 小队生命值(锁血决策用)。**None 化(ADR-0491)**:无真值即 None——读不到且 session 无沿用真值(last_hp_real)时 = None,不再兜底 100(ADR-0282「开局兜底 100」由 ADR-0491 正式废止:开局血量随难度/词缀变不恒 100,兜底值是「看起来像真值」的假值)。读不到但有真值 → 对账层沿用 last_hp_real(int)。消费点对 None 一律保守(血线触发条件不触发/授权位门 fail-closed),hp_readable/hp_trusted 两位语义不变。默认构造 GameState()=未观测态(hp=None;hp_readable 默认 True 仅供 sim 恒真读帧约定,真读帧由读取端显式写)。开局无真值帧由对账层填**初值表先验**(实证档 A8/108 → 82/62,readable=False,先验非真读;ADR-0559,cw_opening_hp),无实证档仍 None)
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
    # 3 位面 boss 名(strategy/06;session.briefing_bosses 同步)。
    # 元素 None = 该位面徽章态无身份(ADR-0398,boss_fit 跳过 None 项)
    plane_bosses: list[str | None] = field(default_factory=list)
    # 开局环境 + 敌人词缀(select_comp / mechanics_fit 用;decide_event 选完写 active_env,实机 OCR 写 enemy_affixes)
    active_env: str = ""                       # 已选投资环境名(如"昼之半神概念股";ENV_COMP_AFFINITY 用)
    enemy_affixes: list[str] = field(default_factory=list)   # 当前位面/节点敌人词缀(MECHANIC_COUNTERS/SYNERGIES 用)
    # 持有装备名(OCR 装备区填;comp 相关 equip_fit 用,详 cw_comps)。阶段 4 接线前默认空。
    equips: list[str] = field(default_factory=list)
    front_max: int = 4    # 前/后排槽位上限(满 10 = 4 前 + 6 后)
    back_max: int = 6
    # 商店开态概率条真值 {费用档 1-5: 概率}(轮岗接线:投资环境轮岗每备战阶段随机
    # 翻倍一档,概率条直接印在商店上,OCR 即真值;None=未读/商店关 → _sample_cost 退基线表)
    refresh_probs: dict[int, float] | None = None
    # 节点序列由 cw_node_reader.NodeSlot 承载(read_node_sequence 直连消费方)。
    dual_track_phase: bool = False           # ADR-0209 双轨期(P1 未定型;方向层接管起值源(ADR-0465) = cw_intention 权威派生经装配边界回填,读端 committed_from)
    focus_factions: set[str] | None = None   # ADR-0209 flex 收敛白名单(方向刷新写入,ADR-0583;evaluate 消费)
    active_strategies: list[str] = field(default_factory=list)  # 已持有投资策略(局中选,可多张;影响经济/难度)
    # 动作v2 账本(契约包 C1,步2):显式动作(SellDeployed/SwapDeploy/
    # CompTransaction)的执行结果逐条记录(applied/rejected + reason)
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

    def copy(self) -> GameState:
        return deepcopy(self)

    def max_units(self) -> int:
        """可上阵数:deploy_cap 真值(= level + 宝钻,ADR-0286)优先,level 兜底;封顶 10(4前+6后)。

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

        席满判定正本 = BoardState 派生(kernel/cw_board_state.bench_is_full,
        同式同源);本类无警告位字段(「备战席已满」警告太短暂不可靠采样,
        通道退役有测试墓碑,§3.2.5)。
        """
        return bench_occupied(self.bench) >= BENCH_CAPACITY


def rebuild_deployed_from_board(board: dict[str, int], back_max: int = 6,
                               max_count: int | None = None) -> list[BenchChar | None]:
    """从 board(OCR 阵营计数真值)重建 ``deployed`` 槽位表(ADR-0392;下标
    0-3=前排/4-9=后排,按 position_pref 路由落槽)→ ``deployed_count()``
    对齐实际阵上数。

    旧 ``read_game_state`` 不填 deployed → 恒 ``[]`` → 所有门失效,本 helper 从 board
    重建 deployed。
    max_count(= level)cap —— 多羁绊角色在 board 多阵营计数(大丽花=击破+盛会之星算 2),
    sum(board) > 实际 deployed(level)→ deployed_count 虚高 → _saving_for_interest + bench-space 门
    **误触**(board 没满却当满 → 不买 target 到 bench → 被 block)。cap at level = 实际 deployed 上限。
    """
    compact: list[BenchChar] = []
    back_left = back_max
    for faction, count in board.items():
        for _ in range(count):
            if max_count is not None and len(compact) >= max_count:
                return deployed_from_compact(compact)
            pref = "back" if back_left > 0 else "front"
            if back_left > 0:
                back_left -= 1
            compact.append(BenchChar(slot=0, faction=faction, star=1,
                                     position_pref=pref))
    return deployed_from_compact(compact)


# ===== bench 槽位语义 helpers(ADR-0316;消费端唯一合法入口)=====


def iter_occupied(bench: list[BenchChar | None]):
    """迭代占用槽(滤 None)——bench 迭代单一源,禁止裸 ``for b in bench``。"""
    return (b for b in bench if b is not None)


def bench_occupied(bench: list[BenchChar | None]) -> int:
    """bench 占用槽数(容量判据单一源,禁止 ``len(bench)``)。"""
    return sum(1 for b in bench if b is not None)


def bench_place(bench: list[BenchChar | None], bc: BenchChar) -> int | None:
    """放入首个空槽(买入落位语义);无空槽返回 None(=bench_full 拒)。

    放置时归一 ``bc.slot = 下标+1``(物理槽位 1-9,与 live 读链
    ``read_bench_chars`` 的 1-based 槽号同坐标系)。
    """
    for i, b in enumerate(bench):
        if b is None:
            bc.slot = i + 1
            bench[i] = bc
            return i
    return None


def bench_clear(bench: list[BenchChar | None], idx: int) -> BenchChar | None:
    """清空占用槽(卖出/上阵语义:置 None 不移位);空槽/越界返回 None。"""
    if 0 <= idx < len(bench) and bench[idx] is not None:
        bc = bench[idx]
        bench[idx] = None
        return bc
    return None


def pad_bench(bench: list[BenchChar | None]) -> list[BenchChar | None]:
    """pad None 到定长 BENCH_CAPACITY(就地补足,返回同引用)。"""
    while len(bench) < BENCH_CAPACITY:
        bench.append(None)
    return bench


def bench_from_compact(chars: list[BenchChar]) -> list[BenchChar | None]:
    """紧缩序列 → 槽位表(顺序放置;BenchChar.slot 已带 1-based 物理槽号
    时按槽放置)。旧语料/紧缩构造入槽位模型的适配单一源。"""
    bench: list[BenchChar | None] = [None] * BENCH_CAPACITY
    for bc in chars:
        # 形状双源防御(ADR-0316 持久态契约):输入可能是 pad 态(定长 9 含
        # None,如 mutate_bench_deployed 就地 pad 后的 exec_state_of(session).tracked_bench_chars)
        # 或紧凑态(无 None)——两种形态都是本适配源的输入域,None 直接跳过。
        if bc is None:
            continue
        slot = bc.slot if 1 <= bc.slot <= BENCH_CAPACITY else None
        if slot is not None and bench[slot - 1] is None:
            bench[slot - 1] = bc
        else:
            bench_place(bench, bc)
    return bench


# ===== deployed 槽位语义 helpers(ADR-0392;消费端唯一合法入口)=====


def iter_occupied_deployed(deployed: list[BenchChar | None]):
    """迭代占用槽(滤 None)——deployed 迭代单一源,禁止裸 ``for d in deployed``。"""
    return (d for d in deployed if d is not None)


def iter_deployed_slots(deployed: list[BenchChar | None]):
    """迭代 (槽位下标, 占用角色) 对(滤 None)——deployed_idx 生成端用
    (索引 = 槽位下标,生成期=执行期恒稳,ADR-0392)。"""
    return ((i, d) for i, d in enumerate(deployed) if d is not None)


def deployed_occupied(deployed: list[BenchChar | None]) -> int:
    """deployed 占用槽数(容量判据单一源,禁止 ``len(deployed)``——定长下
    len 恒 DEPLOYED_CAPACITY)。"""
    return sum(1 for d in deployed if d is not None)


def deployed_slot_no(idx: int) -> int:
    """槽位下标 → 排内 1-based 槽号信息位(0-3→前排 1-4;4-9→后排 1-6)。"""
    return idx - DEPLOYED_FRONT_CAPACITY + 1 if idx >= DEPLOYED_FRONT_CAPACITY \
        else idx + 1


def deployed_place(deployed: list[BenchChar | None], bc: BenchChar) -> int | None:
    """放入指定排的首个空槽(上场落位语义):position_pref='front' → 前排区
    0-3,'back' → 后排区 4-9(ADR-0392);放置时归一 ``bc.position_pref``、
    ``bc.slot``(排内 1-based 槽号信息位)与实际落位下标一致。首选排满时
    落全局首个空槽兜底,兜底跨排时 pref 随落位改写(写端治本,ADR-0605
    §5.2:sell_recorded 通道解析键 = deployed_idx→(排,槽号) 固定双射换算
    后按条目 pref/slot 命中,信息位与下标错位必漏匹配误归 unexplained;
    权威槽位 = 下标,信息位恒为派生,与 _apply_row_to_char 换排归一同向)。
    兜底保持「合法动作必成功」(旧行为 append 不看排,排容量门在上游)。
    无任何空槽返回 None。入口防御 pad(短列表=紧缩前缀,兼容旧构造;
    同 mutate_bench_deployed 的 pad_bench 入口防御)。
    """
    pad_deployed(deployed)
    lo, hi = ((0, DEPLOYED_FRONT_CAPACITY) if bc.position_pref == 'front'
              else (DEPLOYED_FRONT_CAPACITY, DEPLOYED_CAPACITY))
    for rng in (range(lo, hi), range(DEPLOYED_CAPACITY)):
        for i in rng:
            if deployed[i] is None:
                bc.position_pref = ('front' if i < DEPLOYED_FRONT_CAPACITY
                                    else 'back')
                bc.slot = deployed_slot_no(i)
                deployed[i] = bc
                return i
    return None


def deployed_clear(deployed: list[BenchChar | None], idx: int) -> BenchChar | None:
    """清空占用槽(卖出/下场语义:置 None 不移位,ADR-0392);空槽/越界返回 None。"""
    if 0 <= idx < len(deployed) and deployed[idx] is not None:
        bc = deployed[idx]
        deployed[idx] = None
        return bc
    return None


def pad_deployed(deployed: list[BenchChar | None]) -> list[BenchChar | None]:
    """pad None 到定长 DEPLOYED_CAPACITY(就地补足,返回同引用;紧缩前缀
    顺延占用 0..n-1——旧紧缩构造兼容,ADR-0392)。"""
    while len(deployed) < DEPLOYED_CAPACITY:
        deployed.append(None)
    return deployed


def deployed_from_compact(chars: list[BenchChar]) -> list[BenchChar | None]:
    """紧缩序列 → 槽位表(按 position_pref 路由落槽)。旧语料/紧缩构造入
    槽位模型的适配单一源(None 直接跳过——形状双源防御,同 bench_from_compact)。"""
    deployed: list[BenchChar | None] = [None] * DEPLOYED_CAPACITY
    for bc in chars:
        if bc is None:
            continue
        deployed_place(deployed, bc)
    return deployed


def deployed_to_compact(deployed: list[BenchChar | None]) -> list[BenchChar]:
    """槽位表 → 紧缩占用序(槽位序)。sim 账本/遥测序列化保持紧缩序的
    单一出口(下游 checks/视图零迁移,ADR-0392 同 ADR-0316 bench 决策)。"""
    return [d for d in deployed if d is not None]


# ===== Action(动作;simulate 前瞻用) =====
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
# 双族对照表(CW 的「动作」有两族,同名类坐标系不同基——跨族阅读时对撞,
# 类头已按约定标「≠ 另一族」):
#   ┌─────────────────────┬──────────────────────────────┬──────────────────────────────┐
#   │ 同名类               │ 族 A(cw_state,本模块)        │ 族 B(prep_actions,执行器)   │
#   ├─────────────────────┼──────────────────────────────┼──────────────────────────────┤
#   │ SellBench           │ bench_idx=槽位表下标 0-8      │ slot=物理槽位 1-9            │
#   │ DeployMove          │ bench_idx=槽位表下标 0-8      │ from_slot/to_slot=物理槽位   │
#   │                     │                             │   (前排 1-4/后排 1-N)        │
#   │ SellDeployed        │ deployed_idx=槽位表下标 0-9   │ row+slot=物理排+槽位         │
#   │                     │   (front 0-3/back 4-9)       │                              │
#   └─────────────────────┴──────────────────────────────┴──────────────────────────────┘
#   换算:bench 域 族 A 下标 = 族 B 物理槽位 − 1;deployed 域(ADR-0392)
#   族 A 下标 = (row='front': slot−1 | row='back': 4+slot−1)。
#
# 两个坐标系的关键差异(为什么有两族):族 A 是**状态坐标系**(GameState
# 容器的下标,sim 与策略层用);族 B 是**画面坐标系**(屏幕物理槽位,执行器
# 拖拽/点击用)。bench/deployed 两域族 A 均为定长槽位表(ADR-0316/0392),
# 下标恒稳——生成期索引 = 执行期索引。

@dataclass
class BuyCard:
    card: ShopCard
    reason: str = ''   # 买入分类(① 账本 reason 单一源;line/bridge_seed/p2_core/pair/engine/board_focus/emergency/swap/plan;''=旧调用未标)


@dataclass
class SellBench:
    """bench 卖出动作。

    [坐标系] bench_idx = bench 槽位表下标 0-8(ADR-0316;
    ≠ prep_actions.SellBench.slot 的物理槽位 1-9)。

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
    prep 域载体(cw_prep_actions.SellBench)无 expect 字段,不涉本校验。
    锁面 = test_cw_sell_reason_matrix.py(reason/归因面)与
    test_cw_sell_window_launch.py(TestFundingHoldFallback 兜底位
    expect+income 正锁)。
    """
    bench_idx: int
    # [索引定义] 坐标系: bench 槽位表下标 0-8(ADR-0316 定长 9 槽,空槽 None;
    #             ≠ prep_actions.SellBench.slot 的物理槽位 1-9)
    #             取值时机: 生成期=执行期(槽位表恒稳,卖出置 None 不移位)
    income: int | None = None   # 创建时预期回金(sell_refund 口径;None=未标)
    expect: str = ''           # 代际校验期望名(''=不校验,不符→拒绝)
    reason: str = ''           # 卖出通道记录字段(记录非指令,仿 LevelUp.auth_basis 形态;
    #                            ''=未标,缺省形态)。现役发射侧唯一承重值 =
    #                            line_switch_collapse(线账闭合孤儿证明标记,
    #                            cw_prep_actions.SELL_BENCH_REASONS;纯归因
    #                            通道值填充已随 2026-09-08 用户归因遥测删除
    #                            指令拆除);sim 账本 SellBench 行
    #                            sell_reason 键转录本字段,检查器孤儿豁免
    #                            分支据此判定(豁免键集 = cw_prep_actions
    #                            .SELL_BENCH_ORPHAN_REASONS,与发射登记门
    #                            分离的独立闭集,T-180)。
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
#   通道名(entry 换线塌缩出口)兼孤儿证明标记(T-141 方案审乙′:
#   商店发射位仅在「本轮义务登记 ∧ 已出基座」证明在场时打标,授予
#   必须伴随登记簿线账闭合事件,防窗口段回归洗白——证明载体与边界
#   申报见 ADR-0591 §4)。
# 四键只辖「卖出排除面/被保留集登记件」的帧;缺省 '' 恒不豁免
# ——豁免面按分键收敛,禁全开(T3 同轮保留修复批设计约束;三键形态
# = ADR-0585 批 3,N7 豁免面与分键同批消除误报窗口;三→四键 =
# T-141 方案审零阻断放行的语义演进,出处 = 2026-09-08 同轮交互
# 方案审 + ADR-0591)。
# 发射侧填充现状(T-165 起两通道分键):两类放行键(T3 末位牺牲/
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


@dataclass
class LevelUp:
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
class DeployMove:
    """bench → 上阵(某排)。

    [坐标系] bench_idx = bench 槽位表下标 0-8(ADR-0316;
    ≠ prep_actions.DeployMove.from_slot/to_slot 的物理槽位 1-N)。
    """
    bench_idx: int
    # [索引定义] 坐标系: bench 槽位表下标 0-8(ADR-0316;同 SellBench.bench_idx)
    #             取值时机: 生成期=执行期(槽位表恒稳;simulate/mutate 按
    #             下标读槽并置 None)
    to_row: str      # "front" / "back"
    faction: str     # 该角色阵营(上阵后 board[faction] += 1)


@dataclass
class RefreshShop:
    cost: int = 0    # 刷新花费(实机 OCR 补)
    # 触发源**记录**字段(非指令;先例 = LevelUp.
    # auth_basis / SellBench.income 的「记录不是指令」形态——执行层
    # 不读此字段,行为零改动)。值域(发射位单一源 = mandate_v1/shop
    # R1 发射位,今日唯一刷新发射点;L2 补位=买卡、L3 末位=升级,
    # 结构上不产刷新动作,槽位留作未来发射点扩展):
    # - 'r1'                 = 息线门 R1(域外常规承诺账);
    # - 'must_spend_r1_yielded' = 必花域内 R1 切分线(20 号稿/ADR-0528
    #   核算账降排序 yielded 支);
    # - '' = 旧调用/未标(引擎 obs 归 'other' 桶)。
    reason: str = ''


@dataclass
class CloseShop:
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
class PickEvent:
    """选事件选项(投资环境/策略/遭遇/补给)。

    refresh(T-162 重立,ADR-0600;旧「ADR-0146 缺口1 阈值建议」已随 ADR-0519
    C10 退役,现判据 = 零阈值结构存在性,推导与优势论证见 ADR-0600 §3.2 +
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
class FillSpec:
    """人口缺口填位描述(CompTransaction.fill 元素 / 独立填位动作共用)。

    [坐标系] idx 双义随 source:bench 源=槽位下标 0-8 / shop 源=state.shop
    列表下标(契约包 C1 冻结,详见下)。

    契约包 C1(冻结):``source`` = 'bench' | 'shop'(shop 时 ``idx`` 为
    ``state.shop`` 列表索引);``row`` = 'front' | 'back'。
    在 CompTransaction.fill 中,**bench 源的 idx = 槽位下标(0-8,定长稳定,
    ADR-0316)**——生成期索引 = 执行期索引,天然免疫 pop 漂移(F3 根治)。
    填位候选池 = 迁移(deploy/undeploy/sell)后的 bench 槽位表(deploy/sell
    清槽、undeploy 放回首个空槽),校验/应用端按同一视图解析。

    ``expect``(代际校验;草案级扩字段,默认 ''=不
    校验):提案生成时该 idx 指向内容的期望名(bench 源 = char_id,
    shop 源 = card.name)——提案生成→应用之间槽位内容可能已变,应用时
    不符 → 整事务拒绝(stale_proposal),不套用陈旧引用。
    """

    source: str                        # 'bench' | 'shop'(shop 时带 card 索引)
    idx: int
    row: str                           # 'front' | 'back'
    expect: str = ''
    # 代际校验期望名(''=不校验;见 docstring)。expect-whitelist: 草案级
    # 字段——发射点尚未接线,属「待发射点补赋值」观察位;
    # 接线时删本豁免(静态锁 test_expect_fields_have_writers_or_whitelist 督办)


@dataclass
class SellDeployed:
    """卖场上单位(deployed 生命周期开口;不再'只增不减')——契约包 C1。

    [坐标系] deployed_idx = state.deployed **槽位表**下标 0-9(ADR-0392;
    front 0-3 / back 4-9,空槽 None,卖出置 None 不移位——索引跨动作组
    恒稳;≠ prep_actions.SellDeployed 的 row+slot 物理排槽位,
    换算 front:idx=slot−1 / back:idx=4+slot−1)。
    """
    deployed_idx: int
    # [索引定义] 坐标系: deployed 槽位表下标 0-9(ADR-0392 定长 10 槽,空槽
    #             None;≠ prep_actions.SellDeployed 的 row+slot 物理排槽位)
    #             取值时机: 生成期=执行期(槽位表恒稳,卖出置 None 不移位)
    income: int | None = None  # 预期回金(sell_refund 口径;None=未标;记录非指令,同 SellBench)
    reason: str = ''           # 账本 reason(如 'evict_replaced'/'plugin_recycle')
    expect: str = ''           # 遥测观测字段(ADR-0392 降级:槽位恒稳后不再承担
                               # 拦截漂移职责,记录生成期期望名供判读对照;
                               # 校验保留——名不符仍是跨代际提案的拒绝信号)


@dataclass
class SwapDeploy:
    """bench ↔ deployed 换位(场上场下对调;装备随人走)——契约包 C1。

    [坐标系] deployed_idx = state.deployed 槽位表下标 0-9(ADR-0392)/
    bench_idx = bench 槽位表下标 0-8(两域均定长槽位表,索引恒稳;换算见
    Action 节约定块双族对照表)。

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


@dataclass
class CompTransaction:
    """整档组合替换事务(转型讨论两步解耦的第 1 步,原子执行)——契约包 C1。

    [坐标系] deploy/sell 的 bench 侧=槽位下标 0-8;undeploy/sell 的
    deployed 侧=槽位表下标 0-9(ADR-0392)——均按事务前状态解析且槽位
    恒稳(字段口径节冻结)。

    一次敲定:换谁上、谁下、谁直接卖、谁进 bench(完整方案预定义)。
    语义保证:sim 执行时整体应用,任一子步资源不足(金/槽)则整个事务拒绝,
    不产生半档中间态。

    字段口径(步2 实现批声明):
    - ``deploy``/``undeploy``/``sell`` 的索引均按**事务前状态**解析
      (bench_idx → state.bench,deployed_idx → state.deployed);
    - 同域索引不得重复;deploy(bench) 与 sell(bench) 不得指向同槽,
      undeploy 与 sell(deployed) 不得指向同槽;
    - ``fill`` 的 bench 源按**后置 bench**解析(见 FillSpec);
    - 金校验 = 卖出收入(sell_refund 口径)− shop 填位费用(card_cost)
      后 gold ≥ 0;
    - 槽校验 = 终态 bench ≤ BENCH_CAPACITY、终态 deployed ≤ max_units()、
      终态 front ≤ front_max / back ≤ back_max(冻结 invariant)。
    """
    deploy: list[tuple[int, str]]      # [(bench_idx, 'front'|'back')] 新档成员上场
    undeploy: list[int]                # 旧档成员 deployed_idx 列表(下场)
    sell: list[tuple[int, str]]        # [(idx, 'bench'|'deployed')] 直接卖出项
    fill: list[FillSpec] | None = None # 人口缺口填位(第 2 步可同轮或下轮;None=另行走常规填位)
    reason: str = ''                   # 账本(如 'evolve:DOT2→仙舟3'/'branch_pivot')
    # 代际校验期望名(草案级扩字段,默认 None=不校验):
    # 与 deploy/undeploy/sell 的索引**同序**对齐;应用时 idx 指向内容与
    # 期望不符 → 整事务拒绝(stale_proposal)。空串项跳过该项校验。
    expect_deploy: list[str] | None = None    # 对齐 deploy 的 bench_idx 序;expect-whitelist:草案级(发射点未接线)
    expect_undeploy: list[str] | None = None  # 对齐 undeploy 序;expect-whitelist:草案级(发射点未接线)
    expect_sell: list[str] | None = None      # 对齐 sell 序(按给定序,不分域);expect-whitelist:草案级(发射点未接线)
    # ↑ 三者接线时删行内豁免标记(静态锁 test_expect_fields_have_writers_or_whitelist 督办);
    # 事务整批拒语义现由 _resolve_comp_transaction 全量校验承担


Action = (BuyCard | SellBench | LevelUp | DeployMove | RefreshShop | CloseShop
          | PickEvent | SellDeployed | SwapDeploy | CompTransaction)
# 动作集 v2(契约包 C1,步2)+ CloseShop 终结动作(ADR-0517 商店恒可用终结)


@dataclass
class MatchOutcome:
    """一局货币战争的终局结算(框架构造,局终收口消费:跨局分配器/runs summary;/§11.4)。

    ⚠️ 字段全默认 —— **P1 由 run loop 用 ``MatchOutcome()`` 桩构造**(生命周期
    钩子随 ADR-0583 收编删除后,消费面 = cw_loop 局终分支,
    字段已被真实数据填充);**真实 outcome 填充(结算屏 OCR 读终局 HP/位面/轮次/通关)依赖结算屏
    OCR 探查(现 run loop 是「点空白加速 → 继续挑战」,未见独立结算屏)。
    """
    won: bool = False        # 是否通关(3 位面全清)
    final_plane: int = 1     # 到达位面
    final_round: int = 1     # 位面内轮次
    final_hp: int = 0        # 终局小队 HP


def _card_to_bench(card: ShopCard, position_pref: str = "back") -> BenchChar:
    """买的牌落 bench。"""
    return BenchChar(slot=0, char_id=card.name, faction=card.faction,
                     star=card.star, position_pref=position_pref)


def _merge_bench(bench: list[BenchChar | None],
                 deployed: list[BenchChar] | None = None) -> None:
    """3 合 1 升星:同名同星 ≥3(全场域 bench+deployed)→ 合并为 1 个 star+1。

    游戏机制:招募 3 个相同星级同名角色自动升星。⚠️ **合并域 = 全场**——
    deploy_bench L427 用户口径「3合1 是全场」;live 实证(2026-08-18 r17):
    tracking 只看 bench 预估 2★,其中 1-2 张已 deploy → 与游戏全场口径错位 →
    「预估 2★ 读回 1★」star 回退停机钩子两度触发。合成载体:场上同名卡
    升星优先(触发处常见态),无场上卡则 bench 首张升星。

    ADR-0316 槽位语义:bench 侧被合成的份**置 None 腾槽**(对照画面:
    三份合成后腾出槽);ADR-0392:deployed 侧同样按身份置 None(deployed
    亦为槽位表);合成载体留在原槽位。

    deployed=None(旧调用兼容)= 只看 bench(等价旧行为)。
    """
    pools: list[list] = [bench]
    if deployed is not None:
        pools.append(deployed)
    # 不动点循环:两轮上限在级联合并(3×1★→2★→…)不够;while 直到
    # 一轮无合并——游戏语义即如此,且级联有限(星≤5)自然终止
    while True:
        merged_any = False
        occupied = [c for c in bench if c is not None]
        for c in occupied + [d for d in (deployed or []) if d is not None]:
            if not c.char_id:
                continue
            # 全场同名同星组(对象引用,跨池)
            group = [x for p in pools for x in (p if p is bench else p)
                     if x is not None and x.char_id == c.char_id
                     and x.star == c.star]
            if len(group) < 3:
                continue
            take = group[:3]
            # 载体:场上优先(身份比较——dataclass 值相等会让 `in` 误真)
            carrier = next((x for x in take
                            if deployed is not None
                            and any(x is y for y in deployed)), take[0])
            carrier.star += 1
            # 合成装备继承(C6 装备守恒,🟡 游戏侧「合成吃装去向」未见实机证据,
            # 按随载体继承建模保账本守恒——同 sell 回收的保守假设口径):
            for x in take:
                if x is not carrier:
                    carrier.equips = list(carrier.equips) + list(x.equips)
            # 删其余两张:bench/deployed 侧均按身份置 None(ADR-0316/0392
            # 槽位语义,同名同星 dataclass 值相等会删错对象,身份索引)
            for x in take:
                if x is carrier:
                    continue
                if any(x is b for b in bench):
                    for i, b in enumerate(bench):
                        if b is x:
                            bench[i] = None
                            break
                elif deployed is not None:
                    _idx = next((i for i, y in enumerate(deployed)
                                 if y is x), None)
                    if _idx is not None:
                        deployed[_idx] = None
            merged_any = True
            break   # 重扫(列表已变)
        if not merged_any:
            break


def card_cost(card: ShopCard) -> int:
    """牌的费用:OCR 读到用真值,未知按 3 估(费用 1-5 中位)。"""
    return card.cost or 3


def will_merge_on_buy(card: ShopCard, bench: list[BenchChar | None],
                      deployed: list[BenchChar] | None = None) -> bool:
    """买第 3 份同名同 1★ 即合成(S3/H3 口径,ADR-0325)。

    判据 = ``_merge_bench`` 分组键同口径:**同名同 1★ 计数(全场
    bench∪deployed)==2 且待买为 1★**——买后恰达 3 份触发合并。
    显式**不用星级加权**(1 个 2★ 加权 2 但同星计数=1,不合成交
    bench 净 +1;旧 candidates.will_merge 加权判据的误标例)。
    消费点:candidates.will_merge(生成侧)。ADR-0453 起满栏
    购买门/执行侧(simulate)改走一般式 merge_buy_completes/merge_buy_k
    (k 可 >1);本函数保留 = k=1 特例的生成侧标记语义。
    """
    if (card.star or 1) != 1:
        return False
    n = 0
    for b in bench or []:
        if b is not None and b.char_id == card.name and b.star == 1:
            n += 1
    for d in deployed or []:
        if d is not None and d.char_id == card.name and d.star == 1:
            n += 1
    return n == 2


def same_star_count(name: str, star: int,
                    bench: list[BenchChar | None],
                    deployed: list[BenchChar] | None = None) -> int:
    """全场域同名同星计数(bench∪deployed;``_merge_bench`` 分组键同口径)。"""
    n = 0
    for b in bench or []:
        if b is not None and b.char_id == name and b.star == star:
            n += 1
    for d in deployed or []:
        if d is not None and d.char_id == name and d.star == star:
            n += 1
    return n


def merge_material_reject_reason(name: str, star: int,
                                 bench: list[BenchChar | None],
                                 deployed: list[BenchChar] | None = None,
                                 ) -> str:
    """bench 侧卖出通道的合成素材拒入守卫(返回拒因键,'' = 可卖)。

    判据:``c_excl = same_star_count(name, star, bench∪deployed) − 1``
    (含自身全场域计数再扣 victim 自己)``≥ 1`` ⇒ 拒入资格集,拒因键
    ``merge_material_guard``——与部署侧 ``cw_deploy_logic.
    swap_sell_exclusion_reason`` 的拒因闭集**同名同键**(同一守卫语义
    的两个卖出路径实现点;计数单一源 = ``same_star_count``,禁消费方
    手搓同式)。辖域 = bench 四卖出通道(M4 燃料/凑息卖/支付变现/
    换线塌缩),各通道原有资格谓词不动,只追加本子谓词。
    数学依据:同名同星满 3 即自动升星且不变量「场上同名同星 ≤1」
    (merge_mechanics.md §1/§2)⇒ c_excl≥2 稳态不可达,守卫生效域
    恒为 c_excl=1(2/3 合成进度,差最后一张)——卖出即销毁距 2★
    差一张的确定性进度期权,fail-closed 不卖。辖星 = 1(升星链语义
    不在本守卫辖域;2★ 成件全场唯一,子谓词恒放行)。
    设计出处:ADR-0558(合成素材拒入守卫,与部署侧 merge_material_guard
    同键);案发对账 = g_20260906_081836 / g_20260906_095111 两局 P2r1
    (2/3 进度素材被燃料类资格卖断)。
    """
    if (star or 1) != 1:
        return ''
    return ('merge_material_guard'
            if same_star_count(name, 1, bench, deployed) - 1 >= 1 else '')


def merge_material_stale_names(bench: list[BenchChar | None],
                               deployed: list[BenchChar] | None = None,
                               ) -> tuple[str, ...]:
    """滞留素材名集(分键 ``merge_material_stale`` 的判定单一源)。

    判定:全场域(bench∪deployed)同名同 1★ 计数 ≥2 的名 = 存在 2/3
    合成进度素材对;计数单一源 = ``same_star_count``(与
    ``merge_material_reject_reason`` 同源,禁消费方手搓同式)。
    辖星 = 1(2★ 成件全场唯一,不构成素材对,同守卫口径)。
    排序 = 字母序去重(确定性计数,禁集合迭代序入账本)。
    「滞留」语义:对在场即 2/3 进度悬置;持续 N 轮计数仍增长 = N 轮
    未合成(合成后计数停止增长,轮差分归零)——轮级时长由消费端按
    键差分判读,本函数只答「当前帧哪些名滞留」。设计出处:ADR-0558
    §4 滞留显影欠账(G-B1 第四级)。
    """
    names = {b.char_id or '' for b in bench or []
             if b is not None and (b.star or 1) == 1}
    names |= {d.char_id or '' for d in deployed or []
              if d is not None and (d.star or 1) == 1}
    return tuple(sorted(n for n in names if n
                        and same_star_count(n, 1, bench, deployed) >= 2))


def count_merge_material_blocked(counters: dict, name: str,
                                 dedup_names: set[str] | None = None,
                                 ) -> None:
    """拒因分键 ``merge_material_guard_blocked`` 的**事件口径**计数单一源。

    口径(C1,三审整改定谳):拦截**事件**计数,非评估次数——同一决策
    帧内同一素材名只计 1(帧内多通道资格评估、投影读(P56 liquid_
    refund)/腾席环重试对同名重复触达均去重),跨帧滞留素材每次新触达
    仍计。去重载体 = ``dedup_names``(调用方按帧创建并传入;None =
    无去重的单评语境,测试/离线直调)。评估次数口径为已废弃的实装
    偏差(ADR-0558 §4「拦截事件判读」被投影读/重试环污染的整改)。
    """
    if dedup_names is not None:
        if name in dedup_names:
            return
        dedup_names.add(name)
    counters['merge_material_guard_blocked'] = \
        counters.get('merge_material_guard_blocked', 0) + 1


def merge_buy_k(name: str, star: int,
                bench: list[BenchChar | None],
                deployed: list[BenchChar] | None,
                shop: list[ShopCard] | None = None) -> int:
    """满栏合成买的一次点击购买张数 k(merge_mechanics.md §2.5 单一源)。

    k = min(店内同名同星张数, 3 − 已有数 mod 3)——上限口径「绝不多买」:
    只买到触发一次合成所需的量。返回值不含「是否真触发合成」判断
    (那由 ``merge_buy_completes`` 判);店内外身份计数共用
    ``same_star_count``/同键过滤,禁消费方各自手搓(双源漂移温床)。

    消费点:candidates/arbiter 满栏购买门(ADR-0453)/simulate 满栏多买
    (执行侧)/shop.py 买入意图记录(执行账 k×单价)。
    """
    star_n = star or 1
    own = same_star_count(name, star_n, bench, deployed) % 3
    in_shop = sum(1 for c in shop or []
                  if getattr(c, 'name', '') == name
                  and (getattr(c, 'star', 1) or 1) == star_n)
    return min(in_shop, 3 - own)


def merge_buy_completes(name: str, star: int,
                        bench: list[BenchChar | None],
                        deployed: list[BenchChar] | None,
                        shop: list[ShopCard] | None = None) -> bool:
    """本次点击(买 k = ``merge_buy_k`` 张)是否恰好完成一次合成。

    判据 = 同名同星计数(备战栏+场上)+ 本次购买 ≥ 3(ADR-0453 允许条件,
    merge_mechanics §2.5);等价于 k == 3 − 已有数 mod 3。不满足 → 满栏
    照旧拒买(ADR-0283 守卫语义保留为兜底)。

    own≥1 门(T-184,ADR-0619):own=0(全场 bench∪deployed
    无同名同星)时合成买不成立,按满栏非合成买拒收——merge_mechanics
    §2.5 的满栏例外以「已有素材/载体在场、买入可完成合成」为前提,
    own=0 时首张买入既无空槽落位、也无进行中的合成可完成,游戏侧该
    点击被拒(金不扣、牌不下架)。缺此门的旧形态:own=0+店内 3 张
    误判可合成 → k=3 全为尾挂张、合成载体落 idx9 被 ``del bench[9:]``
    截删,双账同错且共同偏离游戏拒买真值。边界:§2.5「连升同理」
    (own=0 于基础星、栏满连买 3 张)为自标低置信口述未亲见,本门
    按拒买语义实现;若拖动对账网实证连升可行,须回本单一源改门。
    """
    own = same_star_count(name, star or 1, bench, deployed) % 3
    if own == 0:
        return False
    k = merge_buy_k(name, star, bench, deployed, shop)
    return own + k >= 3


def _apply_full_bench_merge_buy(bench: list[BenchChar | None],
                                deployed: list[BenchChar] | None,
                                card: ShopCard,
                                shop: list[ShopCard] | None) -> int | None:
    """满栏合成买分支应用(``simulate`` 与 ``mutate_bench_deployed`` 共用
    单一源,T-182)。

    调用语境 = ``bench_place`` 失败(bench 无空槽)后的满栏买入;前置 =
    该买完成一次合成(``merge_buy_completes``,不满足 = 满栏拒买,
    ADR-0283 兜底)。应用 = k = ``merge_buy_k`` 张临时挂槽位表尾参与
    ``_merge_bench``(3 合 1 是全场;own+k ≡ 0 mod 3,合成本身恒耗尽
    尾挂张),截回定长 9。载体落点语义依赖 own≥1:own=1/2 时合成组
    含场内张,载体落在 idx<9 或场上,截断不伤;own=0 域(全尾挂、
    载体落 idx9 必被截删)由 ``merge_buy_completes`` 的 own≥1 门排除
    (T-184,ADR-0619)。返回应用张数 k;前置不满足返回 None(调用方
    据此 no-op)。

    双账同构依据(T-182,2026-09-09 05:52 运行局双响事故):满栏时游戏
    对完成合成的买入**接受并合成**(金照扣、bench 素材被消费腾槽、场上
    载体升星)——投影与 tracked 两本账必须同走本分支;旧 tracked 侧
    丢件不合成使两账结构性分叉,守卫在同 visit 下一动作(投影侧已腾槽、
    豁免条件失效)对拍误炸。
    """
    _name = card.name
    _star = card.star or 1
    if not merge_buy_completes(_name, _star, bench, deployed, shop):
        return None
    _k = max(1, merge_buy_k(_name, _star, bench, deployed, shop))
    for _ in range(_k):
        bench.append(_card_to_bench(card))
    _merge_bench(bench, deployed)   # 全场域(3合1 是全场)
    del bench[BENCH_CAPACITY:]
    return _k


def sell_refund(star: int, cost: int) -> int:
    """卖出回金(economy_research.md §2(strategy/);用户 2026-08-12 提醒卖出金币重要 + 核 2星)。

    - 1星 = cost(🟢 BWIKI「按其费用获得回收金币」+ 4399 + 用户,权威;无合成 → 无手续费 → 买卖净0)。
    - 2星 = cost×3、3星 = cost×9、4星 = cost×27(合成成本),**star≥2 且 cost≥2 再 −1 手续费**。
    - **cost=1 exempt(无手续费)**:🟢 2026-08-13 live 实测 2★1费 万敌 出售 = **+3 金**(cost×3,无 −1;
      sell-star 停机钩子 + VLM 读出售按钮「金币+3」)。用户:1费 2星不减、**2费开始才减1**(手续费 cost 相关
      非纯 star)。故 −1 条件 = ``star>=2 and cost>=2``。
    - 🟡 cost≥2 的 −1(2★2费=5)+ 3/4星 仍用户记忆 / 推测,待多 cost live 核;cost=1 各星已定(全额退)。
      (该置信度分层已在设计件登记并处置:docs/develop/currency_war/archive/design/IMPL_FIX_LEMMAS.md 头注数值锚点行
      置信度标 + IMPL_DESIGN.md §2.2 line_switch_sell 卖面保守端取值;live 核定检查项=同设计件 §5.4 实机验证阶梯。)
    """
    refund = max(cost, 1) * _SELL_MULT.get(star, 1)
    if star >= 2 and cost >= 2:
        refund -= 1   # 合成手续费:仅 star≥2 且 cost≥2(cost=1 exempt,实测 2★1费=3 无费;用户「2费开始减1」)
    return max(refund, 0)


def bench_char_cost(bc: BenchChar) -> int:
    """备战角色的招募费(sell_refund / 经济决策用):char_id 已识别 → 查 CHARACTERS;未知 → 3(中费保守估)。

    公共名(跨模块私有符号收敛:跨模块消费统一走本名;
    下划线旧名保留为别名,存量消费点不破)。"""
    c = CHARACTERS.get(bc.char_id) if getattr(bc, 'char_id', '') else None
    return c.cost if c and c.cost else 3


#: 旧内部名别名(存量消费点 = cw_state 模块内 / sim.engine_p1 /
#: telemetry.schema;接缝面批后新代码一律用公共名 bench_char_cost)
_bench_char_cost = bench_char_cost


def _recount_board(deployed: list[BenchChar]) -> dict[str, int]:
    """deployed 生命周期重算板面(动作 v2,契约包 C1):卖/换/事务后
    board 必须与 deployed 名单一致——本函数是 cw_state 侧的派生单一源。

    口径(ADR-0312,W50 口径统一):**羁绊全集 + 星徽装备贡献**——
    factions+flows+independent,开拓者按排归一,装备羁绊(星徽/卡带)
    计入;与实机 ``board_from_tracked``(= 游戏左面板真值口径)同源,
    per-unit 标签函数单一源 = ``cw_bond_equips.unit_bond_tags``。
    未识别身份(char_id 空/'?'/不在注册表)→ 回退 ``faction`` 字段
    单标签(空/'?' 不计,生产 OCR 空板同形)。值漂移由 checks 的
    board↔deployed 一致性锁双向暴露。"""
    from sr_od.application.currency_war.kernel.cw_bond_equips import unit_bond_tags
    out: dict[str, int] = {}
    for d in (deployed or []):
        if d is None:   # ADR-0392 槽位表空槽
            continue
        tags = unit_bond_tags(d)
        if tags:
            for t in tags:
                out[t] = out.get(t, 0) + 1
            continue
        # 身份未知兜底:faction 字段单标签(旧主阵营口径的未知路径,保留)
        f = getattr(d, 'faction', '') or ''
        if f and f != '?':
            out[f] = out.get(f, 0) + 1
    return out


def _apply_row_to_char(bc: BenchChar, to_row: str) -> None:
    """记录实际站位 + 开拓者换排形态归一(DeployMove/动作 v2 单一源)。

    拖到另一排 = 命途切换(前台记忆/后台欢愉),羁绊随之变 → char_id
    同步换成目标排形态,faction 跟随首阵营(下游 board/装备计算自然对)。
    """
    bc.position_pref = to_row
    from sr_od.application.currency_war.data.cw_chars import get_char as _get_char
    from sr_od.application.currency_war.data.cw_chars import (
        is_trailblazer,
        trailblazer_form,
    )
    if bc.char_id and is_trailblazer(bc.char_id):
        bc.char_id = trailblazer_form(bc.char_id, to_row)
        _tc = _get_char(bc.char_id)
        if _tc is not None and _tc.factions:
            bc.faction = _tc.factions[0]


def _log_action(s: GameState, action_name: str, result: str,
                reason: str = '', **extra) -> None:
    """动作 v2 账本写入(契约包 C1 冻结 invariant:拒绝记录进账本)。"""
    entry: dict = {'action': action_name, 'result': result}
    if reason:
        entry['reason'] = reason
    entry.update(extra)
    s.action_log.append(entry)


def board_unique_key(bc: BenchChar) -> str | None:
    """板上同名唯一性判据键(设计裁定:场上同角色仅 1)。

    - ``char_id`` 空 = 未知身份 → None(不参与查重——两个未知不是可证明的重复);
    - 开拓者各排形态(char_id 随排切换)归一为同一键(场上同样仅 1 个开拓者);
    - 其余 = char_id 本身。
    """
    cid = getattr(bc, 'char_id', '') or ''
    if not cid:
        return None
    from sr_od.application.currency_war.data.cw_chars import is_trailblazer
    return '__trailblazer__' if is_trailblazer(cid) else cid


def _resolve_comp_transaction(
        s: GameState, tx: CompTransaction) -> tuple[str, dict]:
    """CompTransaction 全量校验(原子性前置;不改动状态)。

    返回 ``(reject_reason, plan)``:reject_reason 空 = 通过,plan 含
    后续应用所需的对象引用快照与终态计数(引用快照防应用中途索引漂移)。
    校验项见 CompTransaction docstring(金/槽/索引域/排上限)。
    """
    n_b = bench_occupied(s.bench)   # ADR-0316:容量=占用数
    n_d = deployed_occupied(s.deployed)   # ADR-0392:容量=占用数(非 len)
    und = list(tx.undeploy or [])
    dep = list(tx.deploy or [])
    sell = list(tx.sell or [])
    fill = list(tx.fill or [])
    dep_b = [i for i, _r in dep]
    dep_rows = [r for _i, r in dep]
    sell_b = [i for i, d in sell if d == 'bench']
    sell_d = [i for i, d in sell if d == 'deployed']
    # 索引域:范围+占用(bench=槽位下标 0-8 且须占用;deployed=槽位下标
    # 0-9 且须占用,ADR-0392)+ 同域去重 + 跨子步互斥
    for label, idxs in (('undeploy', und), ('deploy', dep_b),
                        ('sell_bench', sell_b),
                        ('sell_deployed', sell_d)):
        pool = s.bench if 'bench' in label or label == 'deploy' else s.deployed
        if any(not 0 <= i < len(pool) or pool[i] is None for i in idxs):
            return f'{label}_idx_out_of_range', {}
        if len(set(idxs)) != len(idxs):
            return f'{label}_dup_idx', {}
    if set(dep_b) & set(sell_b):
        return 'deploy_sell_bench_overlap', {}
    if set(und) & set(sell_d):
        return 'undeploy_sell_deployed_overlap', {}
    for _i, r in dep:
        if r not in ('front', 'back'):
            return f'deploy_row_invalid:{r}', {}
    for f in fill:
        if f.source not in ('bench', 'shop'):
            return f'fill_source_invalid:{f.source}', {}
        if f.row not in ('front', 'back'):
            return f'fill_row_invalid:{f.row}', {}
    # 引用快照(应用阶段按身份操作,索引不再漂移)
    und_chars = [s.deployed[i] for i in und]
    dep_chars = [(s.bench[i], r) for (i, r) in dep]
    sell_b_chars = [s.bench[i] for i in sell_b]
    sell_d_chars = [s.deployed[i] for i in sell_d]
    # 代际校验:提案生成→应用之间 bench/deployed 序
    # 可能已被同批先行动作改变——expect 序列与索引同序对齐,idx 指向
    # 内容与提案不符 → 整事务拒绝(stale_proposal),不套用陈旧引用。
    if tx.expect_deploy is not None:
        if len(tx.expect_deploy) != len(dep):
            return 'stale_proposal:expect_deploy_len', {}
        for (i, _r), name in zip(dep, tx.expect_deploy, strict=False):
            if name and s.bench[i].char_id != name:
                return (f'stale_proposal:deploy_bench:{name}'
                        f'!={s.bench[i].char_id}'), {}
    if tx.expect_undeploy is not None:
        if len(tx.expect_undeploy) != len(und):
            return 'stale_proposal:expect_undeploy_len', {}
        for i, name in zip(und, tx.expect_undeploy, strict=False):
            if name and s.deployed[i].char_id != name:
                return (f'stale_proposal:undeploy:{name}'
                        f'!={s.deployed[i].char_id}'), {}
    if tx.expect_sell is not None:
        if len(tx.expect_sell) != len(sell):
            return 'stale_proposal:expect_sell_len', {}
        for (i, dom), name in zip(sell, tx.expect_sell, strict=False):
            actual = (s.bench[i] if dom == 'bench' else s.deployed[i])
            if name and actual.char_id != name:
                return (f'stale_proposal:sell_{dom}:{name}'
                        f'!={actual.char_id}'), {}
    # 金:卖出收入 − shop 填位费用(sell_refund / card_cost 单一源)
    income = sum(sell_refund(c.star, _bench_char_cost(c))
                 for c in sell_b_chars + sell_d_chars)
    shop_fill_cards: list[ShopCard] = []
    for f in fill:
        if f.source == 'shop':
            if not 0 <= f.idx < len(s.shop):
                return f'fill_shop_idx_out_of_range:{f.idx}', {}
            if f.expect and s.shop[f.idx].name != f.expect:
                return (f'stale_proposal:fill_shop:{f.expect}'
                        f'!={s.shop[f.idx].name}'), {}
            shop_fill_cards.append(s.shop[f.idx])
    fill_cost = sum(card_cost(c) for c in shop_fill_cards)
    if s.gold + income - fill_cost < 0:
        return (f'gold_short:{s.gold}+{income}-{fill_cost}<0', {})
    # bench 容量:终态 = 现 − deploy − sell_bench + undeploy
    # (填位只出不入:bench 源出队,shop 源买后即上,净 0)
    n_bench_final = n_b - len(dep_b) - len(sell_b) + len(und)
    if n_bench_final > BENCH_CAPACITY:
        return f'bench_overflow:{n_bench_final}>{BENCH_CAPACITY}', {}
    # 后置 bench(fill bench 源的解析域,ADR-0316):**槽位表视图**——迁移
    # (deploy/sell 清槽、undeploy 放回首个空槽)后的 bench,与 _apply 应用
    # 序同式构造(sell → undeploy → deploy)。fill 的 bench 源 idx 直接按
    # 槽位下标解析(定长稳定,生成期=执行期,无 pop 漂移——F3 根治)。
    _gone_b = set(dep_b) | set(sell_b)
    post_bench: list[BenchChar | None] = list(s.bench)
    for i in sell_b:
        post_bench[i] = None            # 步 1:sell 的 bench 槽清空
    for i in dep_b:
        post_bench[i] = None            # 步 2:deploy 源清槽(ADR-0380
        # 件③:先于 undeploy 放回,与 _apply 应用序同式——否则 bench 满
        # 时 undeploy 放回落空,fill 的槽位解析与真实应用错位)
    for c in und_chars:
        bench_place(post_bench, c)      # 步 3:undeploy 放回首个空槽
    for f in fill:
        if f.source == 'bench':
            if not 0 <= f.idx < BENCH_CAPACITY or post_bench[f.idx] is None:
                return (f'fill_bench_idx_out_of_range:{f.idx}', {})
            if f.expect and post_bench[f.idx].char_id != f.expect:
                return (f'stale_proposal:fill_bench:{f.expect}'
                        f'!={post_bench[f.idx].char_id}'), {}
    # deployed 上限(冻结 invariant)与排上限
    n_dep_final = n_d - len(und) - len(sell_d) + len(dep_b) + len(fill)
    if n_dep_final > s.max_units():
        return f'deploy_cap_exceeded:{n_dep_final}>{s.max_units()}', {}
    _removed_front = sum(1 for c in und_chars + sell_d_chars
                         if c.position_pref == 'front')
    _added_front = sum(1 for r in dep_rows + [f.row for f in fill]
                       if r == 'front')
    n_front_final = s.front_count() - _removed_front + _added_front
    if n_front_final > s.front_max:
        return f'front_overflow:{n_front_final}>{s.front_max}', {}
    n_back_final = n_dep_final - n_front_final   # 总终态 − 前排终态
    if n_back_final > s.back_max:
        return f'back_overflow:{n_back_final}>{s.back_max}', {}
    # 同名唯一性(场上同角色仅 1):终态 deployed 名单
    # 查重——留下的旧档 + deploy 新上 + fill 填位(bench 源/买后即上)。
    # 任一重复 → 整事务拒绝(reason='duplicate_on_board',进 action_log;
    # board/factions 虚高的污染源,A/B 实测旧臂 54% 轮同名重复)。
    _gone_d = set(und) | set(sell_d)
    final_keys: set[str] = set()
    _final_units: list[BenchChar | None] = [
        d for i, d in enumerate(s.deployed)
        if d is not None and i not in _gone_d]   # ADR-0392:槽位表滤 None
    _final_units += [c for c, _r in dep_chars]
    _final_units += [post_bench[f.idx] for f in fill
                     if f.source == 'bench'
                     and 0 <= f.idx < BENCH_CAPACITY
                     and post_bench[f.idx] is not None]
    for c in _final_units:
        k = board_unique_key(c)
        if k is None:
            continue
        if k in final_keys:
            return f'duplicate_on_board:{k}', {}
        final_keys.add(k)
    for card in shop_fill_cards:
        if not card.name:
            continue
        if card.name in final_keys:
            return f'duplicate_on_board:{card.name}', {}
        final_keys.add(card.name)
    return '', {
        'und_chars': und_chars, 'dep_chars': dep_chars,
        'sell_bench_chars': sell_b_chars, 'sell_deployed_chars': sell_d_chars,
        'fill': fill, 'post_bench': post_bench,
        'shop_fill_cards': shop_fill_cards,
        'income': income, 'fill_cost': fill_cost,
    }


def _tx_state_view(bench: list[BenchChar],
                   deployed: list[BenchChar]) -> GameState:
    """mutate_bench_deployed 侧的事务校验视图:共享 bench/deployed 引用,
    金/上限取宽松值(金 10^9、level 10)——本函数域只做**索引域/身份
    转移校验**(金/cap/排上限的权威校验在 simulate 侧,GameState 全字段
    才是校验域;此处宽松 = 不因缺上下文误拒合法转移)。"""
    view = GameState()
    view.gold = 10 ** 9
    view.level = 10
    view.bench = bench
    view.deployed = deployed   # ADR-0392:槽位表引用(bench/deployed 均含 None)
    return view


def _remove_by_identity(pool: list, target) -> None:
    """按身份索引删除(shop 等紧缩表专用;同名同星 dataclass 值相等会删错
    对象,同 _merge_bench 纪律)。bench/deployed 槽位表勿用——用
    ``_bench_clear_by_identity`` / ``_deployed_clear_by_identity``
    (置 None 不移位,ADR-0316/0392)。"""
    _idx = next((i for i, y in enumerate(pool) if y is target), None)
    if _idx is not None:
        del pool[_idx]


def _bench_clear_by_identity(bench: list[BenchChar | None],
                             target: BenchChar) -> None:
    """bench 槽位表按身份清槽(ADR-0316:置 None 不移位)。"""
    for i, b in enumerate(bench):
        if b is target:
            bench[i] = None
            return


def _deployed_clear_by_identity(deployed: list[BenchChar | None],
                                target: BenchChar) -> None:
    """deployed 槽位表按身份清槽(ADR-0392:置 None 不移位)。"""
    for i, d in enumerate(deployed):
        if d is target:
            deployed[i] = None
            return


def _apply_comp_transaction(s: GameState, tx: CompTransaction,
                            plan: dict) -> None:
    """应用已校验通过的事务(就地;调用前必须经 _resolve_comp_transaction)。

    应用序:sell → deploy 源清槽 → undeploy → deploy → fill(填位的 bench
    源按后置 bench 槽位表(plan['post_bench'])解析——ADR-0316 槽位下标,
    不 pop 不移位;ADR-0380 件③:deploy 源清槽先于 undeploy 放回,
    否则 bench 满时保留件被静默丢弃——单位守恒)。
    终态重算 board(_recount_board 单一源)。
    卖出单位的装备回收进 ``state.equips``(owned 池;🟡 游戏侧「卖带装
    单位装备去向」未见实机证据,暂按回收建模保装备守恒,待 live 核)。
    """
    for c in plan['sell_bench_chars'] + plan['sell_deployed_chars']:
        s.gold += sell_refund(c.star, _bench_char_cost(c))
        s.equips.extend(c.equips)
        _bench_clear_by_identity(s.bench, c)
        _deployed_clear_by_identity(s.deployed, c)   # ADR-0392:置 None 不移位
    # ADR-0380 件③:deploy 源清槽先于 undeploy 放回——旧序
    # (undeploy 先)在 bench 满时 bench_place 无空槽返回 None,保留件
    # 被**静默删除**(无退款/不回池,单位守恒违约;终态容量校验只看
    # 终态看不见中间态溢出)。清槽提前只影响中间态,终态与旧序一致;
    # post_bench 构造(_resolve)同式同步。
    for c, _row in plan['dep_chars']:
        _bench_clear_by_identity(s.bench, c)
    for c in plan['und_chars']:
        _deployed_clear_by_identity(s.deployed, c)
        bench_place(s.bench, c)
    for c, row in plan['dep_chars']:
        _apply_row_to_char(c, row)
        deployed_place(s.deployed, c)   # ADR-0392:按排路由落槽(替代 append)
    post_bench = plan['post_bench']
    # 索引漂移防御:shop fill 按校验期已解析的
    # 卡对象消费(``plan['shop_fill_cards']``,与 fill 的 shop 源子序列同序)
    # ——**禁在 fill 循环内按下标现读 ``s.shop[f.idx]`` 再 remove**:前一笔
    # remove 左移列表,后续 f.idx 全部失效 → 买错卡(错档部署)+记错账
    # (sim ledger_consistency 金不守恒实证:两笔 2费 fill 被
    # 读成 2费+4费,Δ−6 vs 记账−4)。
    _shop_fills = iter(plan['shop_fill_cards'])
    for f in plan['fill']:
        if f.source == 'bench':
            # ADR-0316:bench 源 idx = 槽位下标,post_bench 是迁移后槽位表
            # 视图(与 s.bench 同槽位)——按身份清槽,不 pop 不移位。
            if not 0 <= f.idx < len(post_bench) \
                    or post_bench[f.idx] is None:
                continue   # 校验已过;防御性兜底
            c = post_bench[f.idx]
            _bench_clear_by_identity(s.bench, c)
            _apply_row_to_char(c, f.row)
            deployed_place(s.deployed, c)   # ADR-0392 槽位落位
        else:   # shop:买后即上(卡对象取自校验期解析——见上方索引漂移注)
            card = next(_shop_fills, None)
            if card is None:
                continue
            s.gold -= card_cost(card)
            _remove_by_identity(s.shop, card)
            bc = _card_to_bench(card)
            _apply_row_to_char(bc, f.row)
            deployed_place(s.deployed, bc)   # ADR-0392 槽位落位
    s.board = _recount_board(s.deployed)


def effective_hp_threshold(state: GameState) -> int:
    """实际保血阈值:selected_difficulty(职级)检测到且 ``DIFFICULTY_HP_TABLE`` 有对应键 → 取覆盖值;
    否则回退 ``HP_SAFE_THRESHOLD``(40)。

    高难(A8)敌人更凶 → 阈值调高,更早弃息保血。阈值表是策略校准参数(代码常量,
    ADR-0204 从 config 迁入 —— 用户对「A7 该在 52 血弃息」没有个人意见,不属用户偏好)。

    ⚖️ ADR-0176(桥接拆除):P2+ 位面上浮不再用手写 ×1.25/×1.5(ADR-0174 桥),
    改由 18 号首达生存模型解出 —— ``plane_hp_ratio``(hp_floor(P_win 地板比),随板强/剩余日程
    变化:强板 ratio→1 不盲目抬阈值,弱板长程 ratio 升高更早保血)。P1 分母恒等 → 对 base
    精确零漂移(M57 验证行为保持)。
    """
    from sr_od.application.currency_war.kernel.cw_first_passage import (
        board_tier_of,
        plane_hp_ratio,
    )
    from sr_od.application.currency_war.kernel.cw_plane_table import (
        NODES_PER_PLANE,
        TOTAL_NODES,
    )

    diff = (getattr(state, "selected_difficulty", "") or "").strip()
    base = int(DIFFICULTY_HP_TABLE.get(diff, HP_SAFE_THRESHOLD))
    if state.plane <= 1:
        return base
    # 剩余战斗日程估计(位面×轮次 → 节点序;round_num 越界防御夹 [1, NODES_PER_PLANE])
    t = (min(3, state.plane) - 1) * NODES_PER_PLANE + min(max(1, state.round_num), NODES_PER_PLANE) - 1
    nodes_left = max(1, TOTAL_NODES - t)
    ratio = plane_hp_ratio(board_tier_of(state.level), nodes_left, plane=state.plane)
    return min(100, int(base * ratio))



def simulate(state: GameState, action: Action) -> GameState:
    """前瞻:返回应用 action 后的**新** GameState(不改原 state)。

    买入落 bench(3 合 1 自动升星);上阵(DeployMove)把角色从 bench 移到 deployed +
    board[faction]+=1(保留身份/站位供 char_quality 与站位分流用)。

    C6 装备守恒对账(W38):装备相关动作(BuyCard/SellBench/SellDeployed/
    SwapDeploy/CompTransaction)执行前后跑账本快照比对——mismatch 记
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
                                         SwapDeploy, CompTransaction))
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
            # 分支应用单一源 = _apply_full_bench_merge_buy(T-182:与运行时
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
                s.gold += sell_refund(sold.star, _bench_char_cost(sold))
                # 装备回收进 owned 池(C6 装备守恒;与 SellDeployed/
                # CompTransaction 同一建模假设——卖带装单位装备回收,
                # 🟡 待 live 核。修复前本分支漏回收 = 账本凭空消失,
                # EquipsLedger 对账必报)。
                s.equips.extend(sold.equips)
    elif isinstance(action, LevelUp):
        # 真实语义(ADR-0129):一次「购买经验」= +XP_PER_BUY 经验、-单击金币;攒够当前级门槛自动
        # 升级(跨级结转溢出)。旧模型「一次动作 = 升 1 级 + 扣整级大金」与机制不符 → 升级门过度
        # 保守(以为要点 36-60 金,实际每击 4-8 金)→ 升级滞后 live 实锤(M15 进位面 2 真实 lv5)。
        if s.level < 10:  # 封顶 10 级
            s.gold -= action.cost
            _cur = s.xp_progress[0] if s.xp_progress else 0
            _cur += XP_PER_BUY
            while s.level < 10:
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
                s.gold += sell_refund(sold.star, _bench_char_cost(sold))
                # 装备回收进 owned 池(🟡 同 _apply_comp_transaction 假设,待 live 核)
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
    elif isinstance(action, CompTransaction):
        # 动作 v2(契约包 C1,步2):整档替换事务——先全量校验后应用,
        # 任一子步资源不足 → 整体拒绝(原状态返回 + 拒绝记录进账本,
        # 冻结 invariant:执行后无半档残留)。
        reject, plan = _resolve_comp_transaction(s, action)
        if reject:
            _log_action(s, 'CompTransaction', 'rejected',
                        reason=f'{reject}|tx_reason={action.reason or ""}')
        else:
            _apply_comp_transaction(s, action, plan)
            _log_action(s, 'CompTransaction', 'applied', reason=action.reason,
                        income=plan['income'], fill_cost=plan['fill_cost'])
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

    与 ``simulate`` 的区别:``simulate`` 返回新 ``GameState`` copy(前瞻语义,含 gold/level/shop 全字段);
    本函数**就地改** bench/deployed 两个列表,只做身份/星级/站位转移(buy→bench+merge / deploy→deployed /
    sell→置 None),供运行时执行点(shop.buy / deploy_bench verify / _handle_bench_full sell)同步
    ``session.bench``/``session.deployed``。转移规则与 simulate 一致(单一源,避双源漂移)。
    ADR-0316/0392:bench/deployed 均为槽位表(定长 9/10,None=空槽)——入口防御性 pad。
    LevelUp/RefreshShop/PickEvent 不影响 bench/deployed → no-op。

    ``shop``(缺省 None = 零漂移兼容):调用方的当前店面视图。提供时,
    满栏合成买(T-182)与 simulate 同分支单一源——满栏时游戏对完成合成
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
        # GameState 域,本函数不管——与 simulate 单一源规则一致)
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
    elif isinstance(action, CompTransaction):
        # 动作 v2(契约包 C1):转移部分原子应用(金/排上限校验在
        # simulate 侧,这里只做 bench/deployed 身份同步;shop 源填位
        # 的卡数据不在本函数域——生产执行点买牌走 BuyCard,故剥离
        # shop 填位后再校验/应用,bench 侧转移不受影响)。
        _tx = action
        if action.fill and any(f.source == 'shop' for f in action.fill):
            _tx = CompTransaction(
                deploy=action.deploy, undeploy=action.undeploy,
                sell=action.sell,
                fill=[f for f in action.fill if f.source == 'bench'],
                reason=action.reason)
        reject, plan = _resolve_comp_transaction(
            _tx_state_view(bench, deployed), _tx)
        if reject:
            return   # 原子:拒绝即整体不动
        for c in plan['sell_bench_chars']:
            _bench_clear_by_identity(bench, c)
        for c in plan['sell_deployed_chars']:
            _deployed_clear_by_identity(deployed, c)
        for c in plan['und_chars']:
            _deployed_clear_by_identity(deployed, c)
            bench_place(bench, c)
        for c, row in plan['dep_chars']:
            _bench_clear_by_identity(bench, c)
            _apply_row_to_char(c, row)
            deployed_place(deployed, c)   # ADR-0392:按排路由落槽
        post_bench = plan['post_bench']
        for f in plan['fill']:
            if f.source == 'bench' \
                    and 0 <= f.idx < len(post_bench) \
                    and post_bench[f.idx] is not None:
                c = post_bench[f.idx]   # ADR-0316 槽位下标;不 pop 不移位
                _bench_clear_by_identity(bench, c)
                _apply_row_to_char(c, f.row)
                deployed_place(deployed, c)   # ADR-0392:按排路由落槽

# ===== 位面节点序列台账(session 级权威表) ================================
# 权威依据(用户口述,最高权威):位面内节点类型与数量**只有投资环境选择能改变**
# (变异位唯一)→ 同一位面内节点序列是常量,可以「进位面时读一次建档 + 投资环境
# 选完后重读刷新」,此后每帧备战画面**查表**得当前节点类型,逐帧识别降级为校验。
# 旧逐帧识别的三类噪声(标签出现在即将到来节点下方 / 高亮态 Hu 不匹配 / 商店
# 遮挡坏帧)因此只影响校验票,不再直接污染决策输入。


@dataclass
class PlaneNodeLedger:
    """本局 per-plane 节点序列台账 + 逐帧校验的去重/豁免状态。

    宿主:``ExecState.plane_node_ledger``(kernel/cw_exec_state.py;经
    :func:`get_node_ledger` 惰性建。载体生命周期 = 一局,无跨局污染)。
    """

    #: 键 = 位面号(1-based);值 = 节点类型序列,**下标 i(0-based)= 该位面第 i+1 轮**
    #: 的类型 token(battle/supply/encounter/reward/boss,与
    #: ``cw_node_reader.NodeSlot.node_type`` / ``GameState.node_type`` 同词汇表;
    #: None = 该位次未识别占位,合并时被后续非 None 读数覆盖)。
    #: 取值时机:写入端每次整行重读时快照(见各写入端);读端 = 备战帧查
    #: ``seq[round_num - 1]``。
    #: 写入端:①位面详情采集(CwScreenPlaneIntel,进位面时的两源互证产物);
    #: ②投资环境选择完成后重读备战节点行(CwScreenInvestEnv,变异窗后的权威刷新)。
    seq_by_plane: dict[int, list[str | None]] = field(default_factory=dict)

    #: 每序列的写入来源('plane_detail' = 位面详情采集 / 'prep_row' = 备战节点行),
    #: 判读侧区分表值的采集通道用(位面详情=彩色渲染态全量,备战行=含 past 遮挡)。
    seq_source: dict[int, str] = field(default_factory=dict)

    #: 位面 → 位面详情底部明文「敌人难度 N」参考值。**只存参考**——生产难度
    #: 主源 = 备战旗牌两级管线(ADR-0449),本字段供离线对拍/缺口排查。
    difficulty_ref: dict[int, int] = field(default_factory=dict)

    #: 投资环境变异窗豁免截止(time.monotonic 时刻;0.0 = 无窗)。窗内查表与
    #: 逐帧校验的不一致**不落**缺陷台账——环境选择到节点行重读之间节点行
    #: 正在合法变异(用户口述:投资环境是唯一变异源),不一致是预期而非识别错误。
    #: 写入端:CwScreenInvestEnv 确认前开窗、重读刷新台账后关窗(置 0)。
    env_grace_until: float = 0.0

    #: 已落过缺陷的 (plane, round) 键集(逐帧校验每帧都会跑,同一不一致只落一行)。
    defect_seen: set[str] = field(default_factory=set)


def get_node_ledger(session: object) -> PlaneNodeLedger | None:
    """取执行侧载体上的台账,无则惰性建(None session → None,调用方跳过)。

    宿主 = ``ExecState.plane_node_ledger``(产生者 = 画面 op 采集/重读
    写入端,归执行侧载体;读写全经本函数与 :func:`ledger_node_type`,
    消费点禁直摸载体字段)。
    """
    if session is None:
        return None
    ex = exec_state_of(session)
    ledger = ex.plane_node_ledger
    if ledger is None:
        ledger = PlaneNodeLedger()
        ex.plane_node_ledger = ledger
    return ledger


def ledger_node_type(session: object, plane: int | None,
                     round_num: int | None) -> str | None:
    """查表:当前位面第 ``round_num`` 轮的节点类型(1-based round → 0-based 下标)。

    表缺 / 位面轮越界 / 该位次未识别(None)→ None(调用方退逐帧识别链,
    **不猜**)。boss 位在序列里存 'boss' token(写入端按「首领=位面最后节点」
    位置先验回填,与既有 boss 语义门同源)。
    """
    ledger = (None if session is None
              else exec_state_of(session).plane_node_ledger)
    if ledger is None or not plane or not round_num:
        return None
    seq = ledger.seq_by_plane.get(int(plane))
    if not seq:
        return None
    idx = int(round_num) - 1
    if not 0 <= idx < len(seq):
        return None
    return seq[idx]


def ledger_update_plane(session: object, plane: int, seq: list[str | None],
                        source: str) -> bool:
    """按位合并写入一位面的序列(**同位次新非 None 覆盖,None 保旧**)。

    合并而非覆盖的原因:备战行/详情条的 past 与 boss 位识别恒 None(Hu 不对
    当前/过去/头像生效)→ 整表覆盖会把已识别位洗成 None;逐位合并让多位面
    多时点的读数渐进拼出全序列(投资环境变异位由最新的非 None 读数天然覆盖)。
    序列变长(如环境加节点)时右侧扩展。返回是否有实际变化(判读用)。
    """
    ledger = get_node_ledger(session)
    if ledger is None or not plane or not seq:
        return False
    old = ledger.seq_by_plane.get(int(plane)) or []
    n = max(len(old), len(seq))
    merged: list[str | None] = []
    changed = False
    for i in range(n):
        new_v = seq[i] if i < len(seq) else None
        old_v = old[i] if i < len(old) else None
        v = new_v if new_v is not None else old_v
        merged.append(v)
        if v != old_v:
            changed = True
    ledger.seq_by_plane[int(plane)] = merged
    if changed or ledger.seq_source.get(int(plane)) != source:
        ledger.seq_source[int(plane)] = source
    return changed


def fill_boss_by_position(seq: list[str | None]) -> list[str | None]:
    """序列副本的最右 None 位回填 'boss'(位置先验:首领 = 位面最后节点)。

    只在 boss 位经详情条「首领节点」标签验证过的写入端调用(CwScreenPlaneIntel);
    备战行重读等未经标签验证的写入端不回填(boss 位在备战行为 past 态,
    回填无依据)。原序列不动,返回副本。
    """
    out = list(seq)
    if out and out[-1] is None:
        out[-1] = 'boss'
    return out


# ===== 布局/报警的策略侧支撑(15 号稿批 C 落地审修订)=====
# 两个入口供 strategies 面消费(strategies 合法桶 = data/kernel/app,
# 不得直依 obs):①布局未知态计数复位的槽式转发(obs 侧在 resolve 时
# 注册真实现);②台账 token → 生产词汇表(BloodAlarmTracker 掉血窗
# 判读用;与 obs._NODE_TYPE_KEYWORDS 方向不同表:那边 OCR 源词→token,
# 本表 token→生产词,单一源=本表)。

NODE_TOKEN_TO_WORD: dict[str, str] = {
    'battle': '普通战斗', 'encounter': '遭遇', 'boss': 'boss',
    'elite': '精英', 'supply': '补给', 'reward': '奖励',
    'megastar': '巨星', 'invest': '投资',
}

_layout_unknown_reset: Callable[[], None] | None = None


def reset_layout_unknown_state() -> None:
    """复位布局未知态计数(槽式转发;obs.cw_back_layout 在 resolve 时
    注册真实现,未注册=noop。新局起点由策略 create_session 调用,
    防跨局残留让开局提前吃冻结)。"""
    fn = _layout_unknown_reset
    if fn is not None:
        fn()
