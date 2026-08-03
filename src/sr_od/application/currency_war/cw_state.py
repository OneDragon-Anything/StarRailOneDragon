"""货币战争 策略状态模型(GameState + Action + 前瞻 simulate)。

策略采用「评估函数 + 贪心改进」架构(见 cw_decisions.evaluate / plan):
- evaluate(state) 给局面打分(羁绊/经济/站位/角色质量);
- 决策在硬规则门内,贪心选 eval 提升最大的动作;前瞻用 simulate(state, action)。

字段多由实机 OCR 填充(见 strategy_design.md §8 接线);未填(None/默认)时决策安全降级。

**board 模型**(2026-08-03 review r1 修正):
- ``board`` = 已上阵阵营计数(OCR 左面板 read_active_synergies 填充)。
- ``deployed`` = bot 自己跟踪的已上阵角色(含 char_id/star/站位),用于 char_quality 评估
  已上阵的优先角色 + 站位分流。两者应一致(deployed 按阵营聚合计数 == board)。
- simulate(DeployMove) 同时更新 deployed(append) 与 board[faction]+=1。
- simulate(BuyCard) 后做 3 合 1 升星(同名同星 ≥3 → 合并为 star+1)。
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

# 卖出回金(按星级;粗估,实机校准)
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
    hp: int = 100          # 小队生命值(锁血决策用;未知默认 100)
    # board = 已上阵阵营计数(OCR 左面板)。deployed = bot 跟踪的已上阵角色(含身份/站位)。
    board: dict[str, int] = field(default_factory=dict)
    deployed: list[BenchChar] = field(default_factory=list)
    shop: list[ShopCard] = field(default_factory=list)
    bench: list[BenchChar] = field(default_factory=list)
    bosses: list[str] = field(default_factory=list)
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
