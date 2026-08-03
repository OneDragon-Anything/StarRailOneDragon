"""货币战争 策略状态模型(GameState + Action + 前瞻 simulate)。

策略采用「评估函数 + 贪心改进」架构(见 cw_decisions.evaluate / plan):
- evaluate(state) 给局面打分(羁绊/经济/站位/角色质量);
- 决策在硬规则门内,贪心选 eval 提升最大的动作;前瞻用 simulate(state, action)。

字段多由实机 OCR 填充(见 strategy_design.md §8 接线);未填(None/默认)时决策安全降级。
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field


@dataclass
class ShopCard:
    """商店一张牌。"""
    x: int               # 牌位中心 x(购买点击坐标)
    faction: str = "?"   # 阵营(OCR);未知 "?"
    name: str = ""       # 角色名(OCR);未知 ""
    cost: int = 0        # 费用(OCR);未知 0(按默认 3 估)
    star: int = 1        # 商店里已是几星


@dataclass
class BenchChar:
    """备战栏/已拥有角色(bench 或已上阵)。"""
    slot: int
    char_id: str = ""    # 角色id(SIFT/OCR 名);未知 ""
    faction: str = "?"   # 阵营
    star: int = 1        # 星级
    position_pref: str = "back"  # 命途定位 front/back(来自 get_role_position)


@dataclass
class GameState:
    """一回合决策时的局面快照(由 OCR 填充)。"""
    gold: int = 0
    round_num: int = 1     # 位面内轮次 1-6
    level: int = 1         # 玩家等级 = 可上阵数上限
    plane: int = 1         # 位面 1/2/3
    hp: int = 100          # 小队生命值(锁血决策用;未知默认 100)
    # board = 已上阵角色的阵营计数(来自左面板 read_active_synergies,即"激活中的羁绊人数")
    board: dict[str, int] = field(default_factory=dict)
    shop: list[ShopCard] = field(default_factory=list)
    bench: list[BenchChar] = field(default_factory=list)
    bosses: list[str] = field(default_factory=list)
    # 槽位上限(满 10 = 4 前 + 6 后);等级低时更少,简化用 level 封顶
    front_max: int = 4
    back_max: int = 6

    def copy(self) -> GameState:
        return deepcopy(self)

    def max_units(self) -> int:
        """可上阵数 = 等级(机制确定),封顶 10。"""
        return min(self.level, self.front_max + self.back_max)

    def deployed_count(self) -> int:
        return sum(self.board.values())


# ===== Action(动作;simulate 前瞻用) =====

@dataclass
class BuyCard:
    card: ShopCard


@dataclass
class SellBench:
    bench_idx: int   # bench 列表索引


@dataclass
class LevelUp:
    cost: int        # 本次升等级花费(由外部按 LEVEL_UP_GOLD_COST 估)


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


def simulate(state: GameState, action: Action) -> GameState:
    """前瞻:返回应用 action 后的**新** GameState(不改原 state)。

    买入的牌先落 bench(未上阵);上阵靠 DeployMove。buy 不直接改 board —— 是否激活羁绊
    由后续 DeployMove 决定,plan() 会把"买 + 上阵"作为一个组合评估。
    """
    s = state.copy()
    if isinstance(action, BuyCard):
        s.gold -= (action.card.cost or 3)
        s.bench.append(_card_to_bench(action.card))
    elif isinstance(action, SellBench):
        if 0 <= action.bench_idx < len(s.bench):
            sold = s.bench.pop(action.bench_idx)
            # 卖出回金:按星级(1星~1金、2星~3金、3星~5金;粗估,实机校准)
            s.gold += {1: 1, 2: 3, 3: 5}.get(sold.star, 1)
    elif isinstance(action, LevelUp):
        s.gold -= action.cost
        s.level += 1
    elif isinstance(action, DeployMove):
        if 0 <= action.bench_idx < len(s.bench):
            s.bench.pop(action.bench_idx)
            s.board[action.faction] = s.board.get(action.faction, 0) + 1
    elif isinstance(action, RefreshShop):
        s.gold -= action.cost
        # shop 内容变化未知(随机),不模拟具体牌;仅扣金
    # PickEvent 不在本模拟范围(event 单独决策)
    return s
