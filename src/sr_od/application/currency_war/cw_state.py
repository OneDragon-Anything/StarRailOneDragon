"""货币战争 策略状态模型(GameState + Action + 前瞻 simulate)。

策略采用「评估函数 + 贪心改进」架构(见 cw_evaluate.evaluate / cw_plan.plan):
- evaluate(state) 给局面打分(羁绊/经济/站位/角色质量);
- 决策在硬规则门内,贪心选 eval 提升最大的动作;前瞻用 simulate(state, action)。

字段多由实机 OCR 填充(见 strategy_design.md §8 接线);未填(None/默认)时决策安全降级。

**board 模型**(2026-08-03 review r1 修正):
- ``board`` = 已上阵阵营计数(OCR 左面板 cw_observation.read_board 填充)。
- ``deployed`` = bot 自己跟踪的已上阵角色(含 char_id/star/站位),用于 char_quality 评估
  已上阵的优先角色 + 站位分流。两者应一致(deployed 按阵营聚合计数 == board)。
- simulate(DeployMove) 同时更新 deployed(append) 与 board[faction]+=1。
- simulate(BuyCard) 后做 3 合 1 升星(同名同星 ≥3 → 合并为 star+1)。
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_chars import CHARACTERS

# 卖出回金 = 招募费(cost)× 合成倍数,economy_research.md §2(strategy/)。1星=cost 🟢 BWIKI+4399+用户权威;
# 2星=cost×3−1、3星=cost×9−1、4星=cost×27−1(合成成本扣1手续费;2星用户印象「少1」+ 修 §2 内部矛盾,
# 3/4星推测同逻辑 🟡 待 hook 实机核 —— 拖卡到出售区看显示金额)。旧 SELL_VALUE{1:1,2:3,3:5} 占位(连1星都没按cost)→ 弃。
_SELL_MULT: dict[int, int] = {1: 1, 2: 3, 3: 9, 4: 27}   # 星级 → cost 倍数(3合1:1星1/2星3/3星9/4星27 张基础副本);sell_refund 对 star≥2 且 cost≥2 再 −1 手续费(cost=1 exempt,见 sell_refund)
BENCH_CAPACITY: int = 9  # 备战栏固定 9 槽(design doc 实测;不随等级变)

# 购买经验机制(ADR-0129;用户实测口述 2026-08-15,A5+;telemetry 多局 XP 分母 4/6/20/40 对拍一致):
# 「购买经验」每点一次 +XP_PER_BUY 经验、花小额金币(按钮实读 state.level_up_cost);经验攒够当前级
# 门槛自动升级,溢出结转。等级门槛表(升下一级所需总经验):
XP_PER_BUY: int = 4
XP_TO_NEXT_LEVEL: dict[int, int] = {3: 4, 4: 6, 5: 20, 6: 40, 7: 52, 8: 72, 9: 84}
XP_CLICK_COST_FALLBACK: int = 4   # 单击经验花金兜底(level_up_cost OCR 缺失时;telemetry lv5 实测 4 金/击)

# 保血阈值(策略校准参数,ADR-0203/0204 从 config 迁入代码单一源;值随实机校准走 git,不走用户 yml)。
# **保守起步,待实机校准**:A1-A4 = 40(低难不变,可适当卖血保经济);A5+ 升阶(高难敌人更凶 → 更早弃息保血)。
HP_SAFE_THRESHOLD: int = 40    # 保血阈值默认(未检测职级时;= cw_evaluate.HP_DANGER 同值,语义「安全地板」)
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


@dataclass
class BenchChar:
    """备战栏/已上阵角色(= strategy/06 的 ``Unit``;加 ``equips``)。"""
    slot: int
    char_id: str = ""    # 角色id(SIFT/OCR 名);未知 ""
    faction: str = "?"   # 阵营
    star: int = 1        # 星级
    position_pref: str = "back"  # 命途定位 front/back(来自 get_role_position)
    equips: list[str] = field(default_factory=list)


@dataclass
class GameState:
    """一回合决策时的局面快照(由 OCR 填充 + bot 跟踪)。"""
    gold: int = 0
    round_num: int = 1     # 位面内轮次 1-6
    node_type: str | None = None   # 当前节点类型(boss/补给/遭遇/巨星/投资/战斗/精英/奖励;顶部标签 OCR;None=未识别)
    enemy_difficulty: int | None = None   # 当前敌人难度(左上角 文本-难度;boss 血量 base×1.052^难度)。None=未读到(stylized OCR 常空)
    # 难度真伪保真位(批㉖ F1:读链翻转后真读/回退可分,对齐 hp_readable 模式):
    # True=当轮逐帧真读(备战「文本-难度」OCR 命中);False=回退简报恒值(session,
    # 开局写死 ≈108 不随轮爬升)或双源皆无。判读侧据此过滤:**False 帧的值别当
    # 「难度 vs 轮次」爬升曲线样本**(ADR 待 leader 定号,批㉖ F1 裁决)。
    enemy_difficulty_live: bool = False
    level: int = 1         # 玩家等级 = 可上阵数上限基准(封顶 10)
    # None = 未读到(shop 态/动画)。level 升级时机决策用(替代纯 _expected_level 估)。
    xp_progress: tuple[int, int] | None = None
    # 部署上限真值(= level + 财富宝钻数,可叠加;D-53/局38 r2 实证)。
    # None=未读到/防抖拒信 → max_units() 兜底 level(ADR-0286)。防抖门在
    # cw_observation.read_deploy_cap_debounced(cap<level 或 |cap-level|>2 重读一帧,仍异拒)。
    deploy_cap: int | None = None
    level_up_cost: int | None = None      # 买一次经验的花费(文本-购买经验金币数;None=未读到,用 XP_CLICK_COST_FALLBACK 兜底)
    shop_refresh_cost: int = 2            # 刷新一次花费(文本-刷新金币数;默认 2,投资策略可减免;未读到保 2)
    streak: int | None = None             # 连胜/连败数(带符号:正=连胜 / 负=连败,结算「连胜×N」前缀=方向,fixture 核实 2026-08-11;None=未读到)
    plane: int = 1         # 位面 1/2/3
    selected_difficulty: str = ""   # 本局职级 A1..A8 / A8-1..A8-50(难度确认屏检测;""=未检测→阈值回退默认;effective_hp_threshold 用;两阶难度详 docs/game/gameplay/currency_war.md:此=职级,enemy_difficulty=数值)
    hp: int = 100          # 小队生命值(锁血决策用;读不到时=沿用 last_hp_real / 开局兜底 100,ADR-0282)
    hp_readable: bool = True   # hp 是否真读到(False=读不到,ADR-0282:hp 此时为沿用值/兜底值;遥测保真,决策不用)
    # r319(ADR-0213 批次2):gold/board 可读保真位(对齐 hp_readable
    # 模式——int/dict 契约下动画帧 miss 与真值不可区分;消费方
    # 遥测/对拍用,决策默认不用)。
    gold_readable: bool = True     # gold 是否真读到(False=0 是 miss 兜底)
    board_readable: bool = True    # board 是否真读到(⚠ 空 dict 双义:真清空≠动画空——真清空时本位仍 True)
    # board = 已上阵阵营计数(OCR 左面板)。deployed = bot 跟踪的已上阵角色(含身份/站位)。
    board: dict[str, int] = field(default_factory=dict)
    # board_next_tier = 各阵营「下个 tier 阈值」(左面板 "X/Y" 的 Y;doc 13 FactionState.next_tier)。
    # 聚焦裁切 OCR 才稳读(全屏把 "2/3" 误读 "213")。comp/progress 评分用「距下个 tier 几人」;默认空(未接/未读到)。
    board_next_tier: dict[str, int] = field(default_factory=dict)
    deployed: list[BenchChar] = field(default_factory=list)
    shop: list[ShopCard] = field(default_factory=list)
    bench: list[BenchChar] = field(default_factory=list)
    plane_bosses: list[str] = field(default_factory=list)   # 3 位面 boss 名(= 简报屏「3 阵营」;current_boss 派生;strategy/06)
    # 开局环境 + 敌人词缀(select_comp / mechanics_fit 用;decide_event 选完写 active_env,实机 OCR 写 enemy_affixes)
    active_env: str = ""                       # 已选投资环境名(如"昼之半神概念股";ENV_COMP_AFFINITY 用)
    enemy_affixes: list[str] = field(default_factory=list)   # 当前位面/节点敌人词缀(MECHANIC_COUNTERS/SYNERGIES 用)
    # 持有装备名(OCR 装备区填;comp 相关 equip_fit 用,详 cw_comps)。阶段 4 接线前默认空。
    equips: list[str] = field(default_factory=list)
    front_max: int = 4    # 前/后排槽位上限(满 10 = 4 前 + 6 后)
    back_max: int = 6
    # OCR「备战席已满」警告(True 时硬门必破;None/False 用 BENCH_CAPACITY 兜底)
    bench_full_flag: bool | None = None
    # 商店开态概率条真值 {费用档 1-5: 概率}(r77 轮岗接线:投资环境轮岗每备战阶段随机
    # 翻倍一档,概率条直接印在商店上,OCR 即真值;None=未读/商店关 → _sample_cost 退基线表)
    refresh_probs: dict[int, float] | None = None
    # ⚖️ node_path + NodeInfo 已删(2026-08-16 review D3:0 写 0 读;节点序列实际由
    # cw_node_reader.NodeSlot 承载,read_node_sequence 直连消费方)。
    match_type: str | None = None            # 标准博弈/超频博弈(模式选择屏;None=未读到)
    plane_modifiers: list[str] = field(default_factory=list)  # 当前位面特殊修正(如「战个痛快」;§13.9 待核各 plane)
    shop_locked: bool = False                # 商店是否锁定
    dual_track_phase: bool = False           # ADR-0209 双轨期(P1 未定型;update_target 每回合刷新)
    focus_factions: set[str] | None = None   # ADR-0209 flex 收敛白名单(update_target 写入;evaluate 消费)
    active_strategies: list[str] = field(default_factory=list)  # 已持有投资策略(局中选,可多张;影响经济/难度)
    megastar_char: str | None = None         # 巨星绑定角色(巨星节点)
    partner_char: str | None = None          # 选择的伙伴(选择伙伴节点)
    # 动作v2 账本(契约包 C1,步2):显式动作(SellDeployed/SwapDeploy/
    # CompTransaction)的执行结果逐条记录(applied/rejected + reason)
    # ——事务拒绝必须可见(checks 消费;冻结 invariant「拒绝记录进账本」)。
    # 三消费面:策略不读(决策禁依赖账本);遥测经 sim ledger 的 actions
    # 序列化间接可见;sim 代理 = 本字段自身(simulate 写、cw_sim 转录)。
    # 旧动作(BuyCard 等)不记(零行为变化)。
    action_log: list[dict] = field(default_factory=list)

    def copy(self) -> GameState:
        return deepcopy(self)

    def max_units(self) -> int:
        """可上阵数:deploy_cap 真值(= level + 宝钻,ADR-0286)优先,level 兜底;封顶 10(4前+6后)。

        14 个消费点(cw_plan/cw_evaluate/cw_events)经本单点收口——cap 接线只改此处即全接。
        deploy_cap < level(防抖漏网噪声)视为不可信,兜底 level。
        """
        base = (self.deploy_cap
                if self.deploy_cap is not None and self.deploy_cap >= self.level
                else self.level)
        return min(base, self.front_max + self.back_max)

    def deployed_count(self) -> int:
        return len(self.deployed)

    def front_count(self) -> int:
        return sum(1 for c in self.deployed if c.position_pref == "front")

    def back_count(self) -> int:
        return sum(1 for c in self.deployed if c.position_pref == "back")

    def bench_is_full(self) -> bool:
        """备战席是否满:OCR 警告标志优先,否则按固定 9 槽。"""
        if self.bench_full_flag is not None:
            return self.bench_full_flag
        return len(self.bench) >= BENCH_CAPACITY

    @property
    def current_boss(self) -> str | None:
        """当前位面 boss(派生 = plane_bosses[plane-1];strategy/06)。无 boss 数据/越界 → None。"""
        if not self.plane_bosses:
            return None
        idx = self.plane - 1
        if 0 <= idx < len(self.plane_bosses):
            return self.plane_bosses[idx]
        return None


def rebuild_deployed_from_board(board: dict[str, int], back_max: int = 6,
                               max_count: int | None = None) -> list[BenchChar]:
    """从 board(OCR 阵营计数真值)重建 ``deployed`` 列表 → ``deployed_count()`` 对齐实际阵上数。

    (RC1 fix):旧 ``read_game_state`` 不填 deployed → 恒 ``[]`` → 所有门失效。本 helper 从 board
    重建 deployed。
    ****:max_count(= level)cap —— 多羁绊角色在 board 多阵营计数(大丽花=击破+盛会之星算 2),
    sum(board) > 实际 deployed(level)→ deployed_count 虚高 → _saving_for_interest + bench-space 门
    **误触**(board 没满却当满 → 不买 target 到 bench → 被 block)。cap at level = 实际 deployed 上限。
    """
    deployed: list[BenchChar] = []
    back_left = back_max
    for faction, count in board.items():
        for _ in range(count):
            if max_count is not None and len(deployed) >= max_count:
                return deployed
            pref = "back" if back_left > 0 else "front"
            if back_left > 0:
                back_left -= 1
            deployed.append(BenchChar(slot=len(deployed), faction=faction, star=1, position_pref=pref))
    return deployed


# ===== Action(动作;simulate 前瞻用) =====

@dataclass
class BuyCard:
    card: ShopCard
    reason: str = ''   # 买入分类(① 账本 reason 单一源;line/bridge_seed/p2_core/pair/engine/board_focus/emergency/swap/plan;''=旧调用未标)


@dataclass
class SellBench:
    """bench 卖出动作。

    r381(交接⑤,sim↔生产账本 income 对齐):sim 侧卖出回金按
    ``cost`` 1:1(cw_sim L630);生产真值 = ``sell_refund(star, cost)``
    (2★×3+手续费)。两侧本就不同源——sim 简化只对 1★ 准。补采:
    ``income`` 字段记录**创建时的预期回金**(策略侧算 sell_refund),
    账本/经济对账消费;未传 = None(sim 与旧调用兼容,sim 侧仍按
    自己的 cost 口径执行,不读此字段——它是**记录**不是**指令**)。
    """
    bench_idx: int   # bench 列表索引
    income: int | None = None   # 创建时预期回金(sell_refund 口径;None=未标)


@dataclass
class LevelUp:
    cost: int        # 本次「购买经验」单击花金(ADR-0129:一次点击 = +XP_PER_BUY 经验,非整级;凑够门槛才升级)


@dataclass
class DeployMove:
    """bench → 上阵(某排)。"""
    bench_idx: int
    to_row: str      # "front" / "back"
    faction: str     # 该角色阵营(上阵后 board[faction] += 1)


@dataclass
class RefreshShop:
    cost: int = 0    # 刷新花费(实机 OCR 补)


@dataclass
class PickEvent:
    """选事件选项(投资环境/策略/遭遇/补给)。

    refresh(ADR-0146 缺口1):三张最优分低于阈值时建议刷新(游戏规则:投资策略/环境/补给各可刷
    N 次,免费)。**纯建议**——是否真刷由 handler 决定(读「刷新次数N」OCR,次数>0 才点;
    刷新失败/次数 0 → 照常选当前最优,失败安全 = 现状行为)。
    """
    option_idx: int
    reason: str = ""
    refresh: bool = False


@dataclass
class FillSpec:
    """人口缺口填位描述(CompTransaction.fill 元素 / 独立填位动作共用)。

    契约包 C1(冻结):``source`` = 'bench' | 'shop'(shop 时 ``idx`` 为
    ``state.shop`` 列表索引);``row`` = 'front' | 'back'。
    在 CompTransaction.fill 中,**bench 源的 idx 按后置 bench 口径解析**
    (deploy/undeploy/sell 应用后的 bench 列表序)——事务语义里填位是
    第 2 步,第 1 步迁移后的 bench 才是填位候选池(步2 实现批声明的
    草案级细化,C1 允许)。

    ``expect``(W43 leader 裁决 2,代际校验;草案级扩字段,默认 ''=不
    校验):提案生成时该 idx 指向内容的期望名(bench 源 = char_id,
    shop 源 = card.name)——提案生成→应用之间槽位内容可能已变,应用时
    不符 → 整事务拒绝(stale_proposal),不套用陈旧引用。
    """

    source: str                        # 'bench' | 'shop'(shop 时带 card 索引)
    idx: int
    row: str                           # 'front' | 'back'
    expect: str = ''                   # 代际校验期望名(''=不校验)


@dataclass
class SellDeployed:
    """卖场上单位(deployed 生命周期开口;不再'只增不减')——契约包 C1。"""
    deployed_idx: int          # state.deployed 列表索引(定位锚,同 SellBench 口径)
    income: int | None = None  # 预期回金(sell_refund 口径;None=未标;记录非指令,同 SellBench)
    reason: str = ''           # 账本 reason(如 'evict_replaced'/'plugin_recycle')
    expect: str = ''           # 代际校验期望名(W43 裁决2;''=不校验,不符→拒绝)


@dataclass
class SwapDeploy:
    """bench ↔ deployed 换位(场上场下对调;装备随人走)——契约包 C1。

    装备随人走 = 换位移动 BenchChar 对象本身(``equips`` 字段随对象迁移,
    无单独装备转移步骤);上场者继承下场者的排(``position_pref``),
    开拓者按目标排做形态归一(同 DeployMove 语义,单一源)。
    """
    deployed_idx: int
    bench_idx: int
    reason: str = ''
    # 代际校验期望名(W43 裁决2;''=不校验):谷底回滚类「上轮登记、
    # 下轮才发」的提案跨了状态代际,idx 可能已指向别人——不符即拒绝。
    expect_deployed: str = ''  # 期望下场者名
    expect_bench: str = ''     # 期望上场者名


@dataclass
class CompTransaction:
    """整档组合替换事务(转型讨论两步解耦的第 1 步,原子执行)——契约包 C1。

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
    # 代际校验期望名(W43 leader 裁决 2;草案级扩字段,默认 None=不校验):
    # 与 deploy/undeploy/sell 的索引**同序**对齐;应用时 idx 指向内容与
    # 期望不符 → 整事务拒绝(stale_proposal)。空串项跳过该项校验。
    expect_deploy: list[str] | None = None    # 对齐 deploy 的 bench_idx 序
    expect_undeploy: list[str] | None = None  # 对齐 undeploy 序
    expect_sell: list[str] | None = None      # 对齐 sell 序(按给定序,不分域)


Action = (BuyCard | SellBench | LevelUp | DeployMove | RefreshShop | PickEvent
          | SellDeployed | SwapDeploy | CompTransaction)   # 动作集 v2(契约包 C1,步2)


@dataclass
class MatchOutcome:
    """一局货币战争的终局结算(框架构造,传给 ``CwStrategy.on_match_end``;/§11.4)。

    ⚠️ 字段全默认 —— **P1 由 run loop 用 ``MatchOutcome()`` 桩构造**(默认 ``on_match_end`` no-op,
    字段未被读);**真实 outcome 填充(结算屏 OCR 读终局 HP/位面/轮次/通关)属 P1.5**,依赖结算屏
    OCR 探查(现 run loop 是「点空白加速 → 继续挑战」,未见独立结算屏)。故 P1 此 dataclass 仅占位,
    待 P1.5 接线才被真实数据填充。
    """
    won: bool = False        # 是否通关(3 位面全清)
    final_plane: int = 1     # 到达位面
    final_round: int = 1     # 位面内轮次
    final_hp: int = 0        # 终局小队 HP


def _card_to_bench(card: ShopCard, position_pref: str = "back") -> BenchChar:
    """买的牌落 bench。"""
    return BenchChar(slot=0, char_id=card.name, faction=card.faction,
                     star=card.star, position_pref=position_pref)


def _merge_bench(bench: list[BenchChar], deployed: list[BenchChar] | None = None) -> None:
    """3 合 1 升星:同名同星 ≥3(全场域 bench+deployed)→ 合并为 1 个 star+1。

    游戏机制:招募 3 个相同星级同名角色自动升星。⚠️ **合并域 = 全场**——
    deploy_bench L427 用户口径「3合1 是全场」;live 实证(2026-08-18 r17):
    tracking 只看 bench 预估 2★,其中 1-2 张已 deploy → 与游戏全场口径错位 →
    「预估 2★ 读回 1★」star 回退停机钩子两度触发。合成载体:场上同名卡
    升星优先(触发处常见态),无场上卡则 bench 首张升星。

    deployed=None(旧调用兼容)= 只看 bench(等价旧行为)。
    """
    pools: list[list[BenchChar]] = [bench]
    if deployed is not None:
        pools.append(deployed)
    # 不动点循环(r6 review#1:两轮上限在级联合并 3×1★→2★→…不够;while 直到
    # 一轮无合并——游戏语义即如此,且级联有限(星≤5)自然终止)
    while True:
        merged_any = False
        for pool in pools:
            for c in list(pool):
                if not c.char_id:
                    continue
                # 全场同名同星组(对象引用,跨池)
                group = [x for p in pools for x in p
                         if x.char_id == c.char_id and x.star == c.star]
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
                # 删其余两张:**身份索引**删除(r6 review#2:list.remove 按值相等
                # 删第一个命中,同名同星 dataclass 值相等会删错对象)
                for x in take:
                    if x is carrier:
                        continue
                    for p in pools:
                        _idx = next((i for i, y in enumerate(p) if y is x), None)
                        if _idx is not None:
                            del p[_idx]
                            break
                merged_any = True
                break   # 重扫(列表已变)
            if merged_any:
                break
        if not merged_any:
            break


def card_cost(card: ShopCard) -> int:
    """牌的费用:OCR 读到用真值,未知按 3 估(费用 1-5 中位)。"""
    return card.cost or 3


def sell_refund(star: int, cost: int) -> int:
    """卖出回金(economy_research.md §2(strategy/);用户 2026-08-12 提醒卖出金币重要 + 核 2星)。

    - 1星 = cost(🟢 BWIKI「按其费用获得回收金币」+ 4399 + 用户,权威;无合成 → 无手续费 → 买卖净0)。
    - 2星 = cost×3、3星 = cost×9、4星 = cost×27(合成成本),**star≥2 且 cost≥2 再 −1 手续费**。
    - **cost=1 exempt(无手续费)**:🟢 2026-08-13 live 实测 2★1费 万敌 出售 = **+3 金**(cost×3,无 −1;
      sell-star 停机钩子 + VLM 读出售按钮「金币+3」)。用户:1费 2星不减、**2费开始才减1**(手续费 cost 相关
      非纯 star)。故 −1 条件 = ``star>=2 and cost>=2``(旧 ``star>=2`` 一刀切把 1费 也 −1 了,错)。
    - 🟡 cost≥2 的 −1(2★2费=5)+ 3/4星 仍用户记忆 / 推测,待多 cost live 核;cost=1 各星已定(全额退)。
    """
    refund = max(cost, 1) * _SELL_MULT.get(star, 1)
    if star >= 2 and cost >= 2:
        refund -= 1   # 合成手续费:仅 star≥2 且 cost≥2(cost=1 exempt,实测 2★1费=3 无费;用户「2费开始减1」)
    return max(refund, 0)


def _bench_char_cost(bc: BenchChar) -> int:
    """备战角色的招募费(sell_refund / 经济决策用):char_id 已识别 → 查 CHARACTERS;未知 → 3(中费保守估)。"""
    c = CHARACTERS.get(bc.char_id) if getattr(bc, 'char_id', '') else None
    return c.cost if c and c.cost else 3


def _recount_board(deployed: list[BenchChar]) -> dict[str, int]:
    """deployed 生命周期重算板面(动作 v2,契约包 C1):卖/换/事务后
    board 必须与 deployed 名单一致——本函数是 cw_state 侧的派生单一源
    (口径 = 主阵营聚合,空/未知阵营不计,与 cw_sim._board_counts_of 同形;
    跨模块不 import,值漂移由 checks 的 board↔deployed 一致性锁双向暴露)。"""
    out: dict[str, int] = {}
    for d in (deployed or []):
        f = getattr(d, 'faction', '') or ''
        if not f or f == '?':
            continue
        out[f] = out.get(f, 0) + 1
    return out


def _apply_row_to_char(bc: BenchChar, to_row: str) -> None:
    """记录实际站位 + 开拓者换排形态归一(DeployMove/动作 v2 单一源)。

    拖到另一排 = 命途切换(前台记忆/后台欢愉),羁绊随之变 → char_id
    同步换成目标排形态,faction 跟随首阵营(下游 board/装备计算自然对)。
    """
    bc.position_pref = to_row
    from sr_od.application.currency_war.cw_chars import get_char as _get_char
    from sr_od.application.currency_war.cw_chars import (
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
    """板上同名唯一性判据键(W43 leader 裁决 1:场上同角色仅 1;r404-A2 同源)。

    - ``char_id`` 空 = 未知身份 → None(不参与查重——两个未知不是可证明的重复);
    - 开拓者各排形态(char_id 随排切换)归一为同一键(场上同样仅 1 个开拓者);
    - 其余 = char_id 本身。
    """
    cid = getattr(bc, 'char_id', '') or ''
    if not cid:
        return None
    from sr_od.application.currency_war.cw_chars import is_trailblazer
    return '__trailblazer__' if is_trailblazer(cid) else cid


def _resolve_comp_transaction(
        s: GameState, tx: CompTransaction) -> tuple[str, dict]:
    """CompTransaction 全量校验(原子性前置;不改动状态)。

    返回 ``(reject_reason, plan)``:reject_reason 空 = 通过,plan 含
    后续应用所需的对象引用快照与终态计数(引用快照防应用中途索引漂移)。
    校验项见 CompTransaction docstring(金/槽/索引域/排上限)。
    """
    n_b, n_d = len(s.bench), len(s.deployed)
    und = list(tx.undeploy or [])
    dep = list(tx.deploy or [])
    sell = list(tx.sell or [])
    fill = list(tx.fill or [])
    dep_b = [i for i, _r in dep]
    dep_rows = [r for _i, r in dep]
    sell_b = [i for i, d in sell if d == 'bench']
    sell_d = [i for i, d in sell if d == 'deployed']
    # 索引域:范围 + 同域去重 + 跨子步互斥
    for label, idxs, n in (('undeploy', und, n_d), ('deploy', dep_b, n_b),
                           ('sell_bench', sell_b, n_b),
                           ('sell_deployed', sell_d, n_d)):
        if any(not 0 <= i < n for i in idxs):
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
    # 代际校验(W43 leader 裁决 2):提案生成→应用之间 bench/deployed 序
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
    # 后置 bench(fill bench 源的解析域:迁移后的 bench 对象序)
    _gone_b = set(dep_b) | set(sell_b)
    post_bench = [c for i, c in enumerate(s.bench) if i not in _gone_b] \
        + und_chars
    for f in fill:
        if f.source == 'bench' \
                and not 0 <= f.idx < len(post_bench):
            return (f'fill_bench_idx_out_of_range:{f.idx}'
                    f'>{len(post_bench)}', {})
        if f.source == 'bench' and 0 <= f.idx < len(post_bench) \
                and f.expect and post_bench[f.idx].char_id != f.expect:
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
    # 同名唯一性(W43 leader 裁决 1:场上同角色仅 1):终态 deployed 名单
    # 查重——留下的旧档 + deploy 新上 + fill 填位(bench 源/买后即上)。
    # 任一重复 → 整事务拒绝(reason='duplicate_on_board',进 action_log;
    # board/factions 虚高的污染源,W43 A/B 实测旧臂 54% 轮同名重复)。
    _gone_d = set(und) | set(sell_d)
    final_keys: set[str] = set()
    _final_units: list[BenchChar | None] = [
        s.deployed[i] for i in range(n_d) if i not in _gone_d]
    _final_units += [c for c, _r in dep_chars]
    _final_units += [post_bench[f.idx] for f in fill
                     if f.source == 'bench' and 0 <= f.idx < len(post_bench)]
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
    view.deployed = deployed
    return view


def _remove_by_identity(pool: list[BenchChar], target: BenchChar) -> None:
    """按身份索引删除(同名同星 dataclass 值相等会删错对象;同 _merge_bench 纪律)。"""
    _idx = next((i for i, y in enumerate(pool) if y is target), None)
    if _idx is not None:
        del pool[_idx]


def _apply_comp_transaction(s: GameState, tx: CompTransaction,
                            plan: dict) -> None:
    """应用已校验通过的事务(就地;调用前必须经 _resolve_comp_transaction)。

    应用序:sell → undeploy → deploy → fill(填位的 bench 源按后置 bench
    的 plan['post_bench'] 序解析)。终态重算 board(_recount_board 单一源)。
    卖出单位的装备回收进 ``state.equips``(owned 池;🟡 游戏侧「卖带装
    单位装备去向」未见实机证据,暂按回收建模保装备守恒,待 live 核)。
    """
    for c in plan['sell_bench_chars'] + plan['sell_deployed_chars']:
        s.gold += sell_refund(c.star, _bench_char_cost(c))
        s.equips.extend(c.equips)
        _remove_by_identity(s.bench, c)
        _remove_by_identity(s.deployed, c)
    for c in plan['und_chars']:
        _remove_by_identity(s.deployed, c)
        s.bench.append(c)
    for c, row in plan['dep_chars']:
        _remove_by_identity(s.bench, c)
        _apply_row_to_char(c, row)
        s.deployed.append(c)
    post_bench = plan['post_bench']
    for f in plan['fill']:
        if f.source == 'bench':
            if not 0 <= f.idx < len(post_bench):
                continue   # 校验已过;防御性兜底
            c = post_bench.pop(f.idx)
            _remove_by_identity(s.bench, c)
            _apply_row_to_char(c, f.row)
            s.deployed.append(c)
        else:   # shop:买后即上(card_cost 已在金校验扣除)
            card = s.shop[f.idx] if 0 <= f.idx < len(s.shop) else None
            if card is None:
                continue
            s.gold -= card_cost(card)
            s.shop.remove(card)
            bc = _card_to_bench(card)
            _apply_row_to_char(bc, f.row)
            s.deployed.append(bc)
    s.board = _recount_board(s.deployed)


def effective_hp_threshold(state: GameState) -> int:
    """实际保血阈值:selected_difficulty(职级)检测到且 ``DIFFICULTY_HP_TABLE`` 有对应键 → 取覆盖值;
    否则回退 ``HP_SAFE_THRESHOLD``(40)。

    高难(A8)敌人更凶 → 阈值调高,更早弃息保血。阈值表是策略校准参数(代码常量,
    ADR-0204 从 config 迁入 —— 用户对「A7 该在 52 血弃息」没有个人意见,不属用户偏好)。

    ⚖️ ADR-0176(r11 #4 桥接拆除):P2+ 位面上浮不再用手写 ×1.25/×1.5(ADR-0174 桥),
    改由 18 号首达生存模型解出 —— ``plane_hp_ratio``(hp_floor(P_win 地板比),随板强/剩余日程
    变化:强板 ratio→1 不盲目抬阈值,弱板长程 ratio 升高更早保血)。P1 分母恒等 → 对 base
    精确零漂移(M57 验证行为保持)。
    """
    from sr_od.application.currency_war.cw_first_passage import (
        board_tier_of,
        plane_hp_ratio,
    )
    from sr_od.application.currency_war.cw_horizon import NODES_PER_PLANE, TOTAL_NODES

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
    from sr_od.application.currency_war.cw_bench_equips import (
        ledger_mismatch,
        state_equips_multiset,
    )
    s = state.copy()
    _equips_action = isinstance(action, (BuyCard, SellBench, SellDeployed,
                                         SwapDeploy, CompTransaction))
    _pre_equips = state_equips_multiset(state) if _equips_action else None
    if isinstance(action, BuyCard):
        s.gold -= card_cost(action.card)
        s.bench.append(_card_to_bench(action.card))
        _merge_bench(s.bench, s.deployed)   # 全场域(3合1 是全场;deploy_bench L427 口径)
        # 买走该槽位 → 从 shop 移除(否则 plan 贪心会重买同一张堆星,sim 不反映"槽位空了")
        s.shop = [c for c in s.shop if c.x != action.card.x]
    elif isinstance(action, SellBench):
        if 0 <= action.bench_idx < len(s.bench):
            sold = s.bench.pop(action.bench_idx)
            s.gold += sell_refund(sold.star, _bench_char_cost(sold))
            # 装备回收进 owned 池(C6 装备守恒;与 SellDeployed/CompTransaction
            # 同一建模假设——卖带装单位装备回收,🟡 待 live 核。修复前本分支
            # 漏回收 = 账本凭空消失,EquipsLedger 对账必报)。
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
        if 0 <= action.bench_idx < len(s.bench):
            _k = board_unique_key(s.bench[action.bench_idx])
            # 同名唯一性(W43 裁决 1):单卡上场同理——已在场同名 → 拒绝
            # (进 action_log;bench 同名副本是 3合1 素材,合成走 bench 域)。
            if _k is not None and any(board_unique_key(d) == _k
                                      for d in s.deployed):
                _log_action(s, 'DeployMove', 'rejected',
                            reason=f'duplicate_on_board:{_k}')
            else:
                bc = s.bench.pop(action.bench_idx)
                # 站位记录 + 开拓者换排形态归一(单一源 helper;行为与旧内联版逐字等价)
                _apply_row_to_char(bc, action.to_row)
                s.deployed.append(bc)
                s.board[action.faction] = s.board.get(action.faction, 0) + 1
    elif isinstance(action, SellDeployed):
        # 动作 v2(契约包 C1,步2):卖场上单位——deployed 生命周期开口。
        if 0 <= action.deployed_idx < len(s.deployed):
            _tgt = s.deployed[action.deployed_idx]
            # 代际校验(W43 裁决 2):期望名不符 = 陈旧提案 → 拒绝不套用
            if action.expect and _tgt.char_id != action.expect:
                _log_action(s, 'SellDeployed', 'rejected',
                            reason=(f'stale_proposal:{action.expect}'
                                    f'!={_tgt.char_id}'),
                            char=_tgt.char_id)
            else:
                sold = s.deployed.pop(action.deployed_idx)
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
                and 0 <= action.bench_idx < len(s.bench):
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
                        for _i, d in enumerate(s.deployed)
                        if _i != action.deployed_idx):
                    _log_action(s, 'SwapDeploy', 'rejected',
                                reason=f'duplicate_on_board:{_k}')
                else:
                    _row = out_char.position_pref
                    s.deployed[action.deployed_idx] = in_char
                    s.bench[action.bench_idx] = out_char
                    # 上场者继承下场者的排(含开拓者形态归一);下场者保留原
                    # position_pref 记录(回 bench 后不消费,再上场时重写)
                    _apply_row_to_char(in_char, _row)
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


def mutate_bench_deployed(bench: list[BenchChar], deployed: list[BenchChar],
                          action: Action) -> None:
    """就地应用 action 的 bench/deployed 转移到持久跟踪状态(task#105 运行时同步用;/)。

    与 ``simulate`` 的区别:``simulate`` 返回新 ``GameState`` copy(前瞻语义,含 gold/level/shop 全字段);
    本函数**就地改** bench/deployed 两个列表,只做身份/星级/站位转移(buy→bench+merge / deploy→deployed /
    sell→pop),供运行时执行点(shop.buy / deploy_bench verify / _handle_bench_full sell)同步
    ``session.bench``/``session.deployed``。转移规则与 simulate 一致(单一源,避双源漂移)。
    LevelUp/RefreshShop/PickEvent 不影响 bench/deployed → no-op。
    """
    if isinstance(action, BuyCard):
        bench.append(_card_to_bench(action.card))
        _merge_bench(bench, deployed)   # 全场域(live tracking 与 simulate 同源)
    elif isinstance(action, SellBench):
        if 0 <= action.bench_idx < len(bench):
            bench.pop(action.bench_idx)
    elif isinstance(action, DeployMove):
        if 0 <= action.bench_idx < len(bench):
            # 同名唯一性守卫(W43 裁决 1,与 simulate 同源):已在场同名不上
            _k = board_unique_key(bench[action.bench_idx])
            if _k is not None and any(board_unique_key(d) == _k
                                      for d in deployed):
                return
            bc = bench.pop(action.bench_idx)
            _apply_row_to_char(bc, action.to_row)
            # 开拓者形态切换(同 simulate 语义,单一源 helper)
            deployed.append(bc)
    elif isinstance(action, SellDeployed):
        # 动作 v2(契约包 C1):runtime 跟踪侧只做身份转移(金/装备归
        # GameState 域,本函数不管——与 simulate 单一源规则一致)
        if 0 <= action.deployed_idx < len(deployed) \
                and (not action.expect
                     or deployed[action.deployed_idx].char_id == action.expect):
            deployed.pop(action.deployed_idx)   # 陈旧提案(代际不符)no-op
    elif isinstance(action, SwapDeploy):
        if 0 <= action.deployed_idx < len(deployed) \
                and 0 <= action.bench_idx < len(bench):
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
                    for _i, d in enumerate(deployed)
                    if _i != action.deployed_idx):
                return
            _row = out_char.position_pref
            deployed[action.deployed_idx] = in_char
            bench[action.bench_idx] = out_char
            _apply_row_to_char(in_char, _row)
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
            _remove_by_identity(bench, c)
        for c in plan['sell_deployed_chars']:
            _remove_by_identity(deployed, c)
        for c in plan['und_chars']:
            _remove_by_identity(deployed, c)
            bench.append(c)
        for c, row in plan['dep_chars']:
            _remove_by_identity(bench, c)
            _apply_row_to_char(c, row)
            deployed.append(c)
        post_bench = plan['post_bench']
        for f in plan['fill']:
            if f.source == 'bench' and 0 <= f.idx < len(post_bench):
                c = post_bench.pop(f.idx)
                _remove_by_identity(bench, c)
                _apply_row_to_char(c, f.row)
                deployed.append(c)
