"""货币战争 策略状态模型(GameState + Action + 前瞻 simulate)。

策略采用「评估函数 + 贪心改进」架构(见 cw_decisions.evaluate / plan):
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

# 卖出回金(按星级;粗估,实机校准)。⚠️ star3=5 是占位 —— 实际应为 cost×9(1星=cost、2星=cost×3、3星=cost×9,
# review agent 🟡 推算);A4 实现时改 cost-based sell_refund(star,cost)(需 BenchChar 带 cost),替换此表。
SELL_VALUE: dict[int, int] = {1: 1, 2: 3, 3: 5}
BENCH_CAPACITY: int = 9  # 备战栏固定 9 槽(design doc 实测;不随等级变)


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
    """备战栏/已上阵角色。"""
    slot: int
    char_id: str = ""    # 角色id(SIFT/OCR 名);未知 ""
    faction: str = "?"   # 阵营
    star: int = 1        # 星级
    position_pref: str = "back"  # 命途定位 front/back(来自 get_role_position)


@dataclass
class GameState:
    """一回合决策时的局面快照(由 OCR 填充 + bot 跟踪)。"""
    gold: int = 0
    round_num: int = 1     # 位面内轮次 1-6
    level: int = 1         # 玩家等级 = 可上阵数上限(封顶 10)
    plane: int = 1         # 位面 1/2/3
    difficulty: str = ""   # 本局难度 A1..A8(匹配开始从难度确认屏检测;"" = 未检测 → 阈值回退默认;effective_hp_threshold 用)
    hp: int = 100          # 小队生命值(锁血决策用;未知默认 100)
    # board = 已上阵阵营计数(OCR 左面板)。deployed = bot 跟踪的已上阵角色(含身份/站位)。
    board: dict[str, int] = field(default_factory=dict)
    # board_next_tier = 各阵营「下个 tier 阈值」(左面板 "X/Y" 的 Y;doc 13 FactionState.next_tier)。
    # 聚焦裁切 OCR 才稳读(全屏把 "2/3" 误读 "213")。comp/progress 评分用「距下个 tier 几人」;默认空(未接/未读到)。
    board_next_tier: dict[str, int] = field(default_factory=dict)
    deployed: list[BenchChar] = field(default_factory=list)
    shop: list[ShopCard] = field(default_factory=list)
    bench: list[BenchChar] = field(default_factory=list)
    bosses: list[str] = field(default_factory=list)
    # 开局环境 + 敌人词缀(select_comp / mechanics_fit 用;decide_event 选完写 active_env,实机 OCR 写 enemy_affixes)
    active_env: str = ""                       # 已选投资环境名(如"昼之半神概念股";ENV_COMP_AFFINITY 用)
    enemy_affixes: list[str] = field(default_factory=list)   # 当前位面/节点敌人词缀(MECHANIC_COUNTERS/SYNERGIES 用)
    # 持有装备名(OCR 装备区填;comp 相关 equip_fit 用,详 cw_comps)。阶段 4 接线前默认空。
    equips: list[str] = field(default_factory=list)
    front_max: int = 4    # 前/后排槽位上限(满 10 = 4 前 + 6 后)
    back_max: int = 6
    # OCR「备战席已满」警告(True 时硬门必破;None/False 用 BENCH_CAPACITY 兜底)
    bench_full_flag: bool | None = None

    def copy(self) -> GameState:
        return deepcopy(self)

    def max_units(self) -> int:
        """可上阵数 = 等级(机制确定),封顶 10。"""
        return min(self.level, self.front_max + self.back_max)

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


# ===== Action(动作;simulate 前瞻用) =====

@dataclass
class BuyCard:
    card: ShopCard


@dataclass
class SellBench:
    bench_idx: int   # bench 列表索引


@dataclass
class LevelUp:
    cost: int        # 本次升等级花费(由外部按 LEVEL_UP_COST_TABLE 估)


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
    """选事件选项(投资环境/策略/遭遇/补给)。"""
    option_idx: int
    reason: str = ""


Action = BuyCard | SellBench | LevelUp | DeployMove | RefreshShop | PickEvent


@dataclass
class MatchOutcome:
    """一局货币战争的终局结算(框架构造,传给 ``CwStrategy.on_match_end``;D-34/§11.4)。

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


def _merge_bench(bench: list[BenchChar]) -> None:
    """3 合 1 升星:同名同星 ≥3 → 合并为 1 个 star+1(就地改 bench)。

    游戏机制:招募 3 个相同星级同名角色自动升星。bench 里凑齐即合并。
    """
    i = 0
    while i < len(bench):
        bc = bench[i]
        if not bc.char_id:
            i += 1
            continue
        # 找同名同星
        same = [j for j, c in enumerate(bench) if c.char_id == bc.char_id and c.star == bc.star]
        if len(same) >= 3:
            # 保留 same[0](升 star),删 same[1], same[2]
            bench[same[0]].star += 1
            del bench[same[2]]
            del bench[same[1]]
            # 不推进 i(升星后可能再凑?一般不会,但重来更稳)
        else:
            i += 1


def card_cost(card: ShopCard) -> int:
    """牌的费用:OCR 读到用真值,未知按 3 估(费用 1-5 中位)。"""
    return card.cost or 3


def sell_refund(star: int) -> int:
    """卖出回金(按星级)。"""
    return SELL_VALUE.get(star, 1)


def effective_hp_threshold(state: GameState, config) -> int:
    """实际保血阈值:difficulty 检测到且 ``config.difficulty_hp_override`` 有对应键 → 取覆盖值;
    否则回退 ``config.hp_safe_threshold``(默认 40 = cw_decisions.HP_DANGER)。

    向后兼容:difficulty 未检测("")或无对应覆盖键 → 回退 hp_safe_threshold,**行为与加 difficulty
    前完全一致**(detection 未接线时零行为变化)。高难(A8)敌人更凶 → 阈值调高,更早弃息保血
    (决策见 docs/game/currency_war/decisions.md D-32)。detection 接线(难度确认屏 OCR →
    state.difficulty)是后续 game 接线任务;本函数 + GameState.difficulty 是其离线地基。
    """
    diff = (getattr(state, "difficulty", "") or "").strip()
    override = getattr(config, "difficulty_hp_override", None) or {}
    if diff and diff in override:
        return int(override[diff])
    return int(getattr(config, "hp_safe_threshold", 40))



def simulate(state: GameState, action: Action) -> GameState:
    """前瞻:返回应用 action 后的**新** GameState(不改原 state)。

    买入落 bench(3 合 1 自动升星);上阵(DeployMove)把角色从 bench 移到 deployed +
    board[faction]+=1(保留身份/站位供 char_quality 与站位分流用)。
    """
    s = state.copy()
    if isinstance(action, BuyCard):
        s.gold -= card_cost(action.card)
        s.bench.append(_card_to_bench(action.card))
        _merge_bench(s.bench)
        # 买走该槽位 → 从 shop 移除(否则 plan 贪心会重买同一张堆星,sim 不反映"槽位空了")
        s.shop = [c for c in s.shop if c.x != action.card.x]
    elif isinstance(action, SellBench):
        if 0 <= action.bench_idx < len(s.bench):
            sold = s.bench.pop(action.bench_idx)
            s.gold += sell_refund(sold.star)
    elif isinstance(action, LevelUp):
        if s.level < 10:  # 封顶 10 级
            s.gold -= action.cost
            s.level += 1
    elif isinstance(action, DeployMove):
        if 0 <= action.bench_idx < len(s.bench):
            bc = s.bench.pop(action.bench_idx)
            bc.position_pref = action.to_row  # 记录实际站位
            s.deployed.append(bc)
            s.board[action.faction] = s.board.get(action.faction, 0) + 1
    elif isinstance(action, RefreshShop):
        s.gold -= action.cost
        # shop 内容变化未知(随机),不模拟具体牌;仅扣金
    # PickEvent 不在本模拟范围(event 单独决策)
    return s
