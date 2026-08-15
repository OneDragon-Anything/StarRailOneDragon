# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

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

from sr_od.application.currency_war.cw_chars import CHARACTERS

# 卖出回金 = 招募费(cost)× 合成倍数,economy_research.md §2。1星=cost 🟢 BWIKI+4399+用户权威;
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
    """备战栏/已上阵角色(= strategy/13 §13.2 的 ``Unit``;加 ``equips``)。"""
    slot: int
    char_id: str = ""    # 角色id(SIFT/OCR 名);未知 ""
    faction: str = "?"   # 阵营
    star: int = 1        # 星级
    position_pref: str = "back"  # 命途定位 front/back(来自 get_role_position)
    equips: list[str] = field(default_factory=list)


@dataclass
class NodeInfo:
    """位面节点序列中的一项(strategy/13 §13.2 node_path;)。

    纯图标无文字 → 需视觉/CV 建图标模板(§13.9 待核);未接 OCR 时 node_path 为空。
    """
    type: str = ""                          # 节点类型:战斗/精英/boss/补给/遭遇/投资/奖励
    status: str = "future"                  # "past"/"current"/"future"


@dataclass
class GameState:
    """一回合决策时的局面快照(由 OCR 填充 + bot 跟踪)。"""
    gold: int = 0
    round_num: int = 1     # 位面内轮次 1-6
    node_type: str | None = None   # 当前节点类型(boss/补给/遭遇/巨星/投资/战斗/精英/奖励;顶部标签 OCR;None=未识别)
    enemy_difficulty: int | None = None   # 当前敌人难度(左上角 文本-难度;boss 血量 base×1.052^难度)。None=未读到(stylized OCR 常空)
    level: int = 1         # 玩家等级 = 可上阵数上限(封顶 10)
    # None = 未读到(shop 态/动画)。level 升级时机决策用(替代纯 _expected_level 估)。
    xp_progress: tuple[int, int] | None = None
    level_up_cost: int | None = None      # 买一次经验的花费(文本-购买经验金币数;None=未读到,用 XP_CLICK_COST_FALLBACK 兜底)
    shop_refresh_cost: int = 2            # 刷新一次花费(文本-刷新金币数;默认 2,投资策略可减免;未读到保 2)
    streak: int | None = None             # 连胜/连败数(带符号:正=连胜 / 负=连败,结算「连胜×N」前缀=方向,fixture 核实 2026-08-11;None=未读到)
    plane: int = 1         # 位面 1/2/3
    selected_difficulty: str = ""   # 本局职级 A1..A8 / A8-1..A8-50(难度确认屏检测;""=未检测→阈值回退默认;effective_hp_threshold 用;strategy/13 §13.7 两阶难度:此=职级,enemy_difficulty=数值)
    hp: int = 100          # 小队生命值(锁血决策用;未知默认 100)
    # board = 已上阵阵营计数(OCR 左面板)。deployed = bot 跟踪的已上阵角色(含身份/站位)。
    board: dict[str, int] = field(default_factory=dict)
    # board_next_tier = 各阵营「下个 tier 阈值」(左面板 "X/Y" 的 Y;doc 13 FactionState.next_tier)。
    # 聚焦裁切 OCR 才稳读(全屏把 "2/3" 误读 "213")。comp/progress 评分用「距下个 tier 几人」;默认空(未接/未读到)。
    board_next_tier: dict[str, int] = field(default_factory=dict)
    deployed: list[BenchChar] = field(default_factory=list)
    shop: list[ShopCard] = field(default_factory=list)
    bench: list[BenchChar] = field(default_factory=list)
    plane_bosses: list[str] = field(default_factory=list)   # 3 位面 boss 名(= 简报屏「3 阵营」;current_boss 派生;strategy/13 §13.2/§13.5)
    # 开局环境 + 敌人词缀(select_comp / mechanics_fit 用;decide_event 选完写 active_env,实机 OCR 写 enemy_affixes)
    active_env: str = ""                       # 已选投资环境名(如"昼之半神概念股";ENV_COMP_AFFINITY 用)
    enemy_affixes: list[str] = field(default_factory=list)   # 当前位面/节点敌人词缀(MECHANIC_COUNTERS/SYNERGIES 用)
    # 持有装备名(OCR 装备区填;comp 相关 equip_fit 用,详 cw_comps)。阶段 4 接线前默认空。
    equips: list[str] = field(default_factory=list)
    front_max: int = 4    # 前/后排槽位上限(满 10 = 4 前 + 6 后)
    back_max: int = 6
    # OCR「备战席已满」警告(True 时硬门必破;None/False 用 BENCH_CAPACITY 兜底)
    bench_full_flag: bool | None = None
    node_path: list[NodeInfo] = field(default_factory=list)   # 本位面节点序列(纯图标,需视觉;§13.9 待核)
    match_type: str | None = None            # 标准博弈/超频博弈(模式选择屏;None=未读到)
    plane_modifiers: list[str] = field(default_factory=list)  # 当前位面特殊修正(如「战个痛快」;§13.9 待核各 plane)
    shop_locked: bool = False                # 商店是否锁定
    active_strategies: list[str] = field(default_factory=list)  # 已持有投资策略(局中选,可多张;影响经济/难度)
    megastar_char: str | None = None         # 巨星绑定角色(巨星节点)
    partner_char: str | None = None          # 选择的伙伴(选择伙伴节点)

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

    @property
    def current_boss(self) -> str | None:
        """当前位面 boss(派生 = plane_bosses[plane-1];strategy/13 §13.2)。无 boss 数据/越界 → None。"""
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


@dataclass
class SellBench:
    bench_idx: int   # bench 列表索引


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
    """选事件选项(投资环境/策略/遭遇/补给)。"""
    option_idx: int
    reason: str = ""


Action = BuyCard | SellBench | LevelUp | DeployMove | RefreshShop | PickEvent


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


def sell_refund(star: int, cost: int) -> int:
    """卖出回金(economy_research.md §2;用户 2026-08-12 提醒卖出金币重要 + 核 2星)。

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


def effective_hp_threshold(state: GameState, config) -> int:
    """实际保血阈值:selected_difficulty(职级)检测到且 ``config.difficulty_hp_override`` 有对应键 → 取覆盖值;
    否则回退 ``config.hp_safe_threshold``(默认 40 = cw_decisions.HP_DANGER)。

    向后兼容:selected_difficulty 未检测("")或无对应覆盖键 → 回退 hp_safe_threshold,**行为与加 difficulty
    前完全一致**(detection 未接线时零行为变化)。高难(A8)敌人更凶 → 阈值调高,更早弃息保血
    (决策见 docs/develop/currency_war/decisions/INDEX.md )。detection 接线(难度确认屏 OCR →
    state.selected_difficulty)是后续 game 接线任务;本函数 + GameState.selected_difficulty 是其离线地基。
    """
    diff = (getattr(state, "selected_difficulty", "") or "").strip()
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
            s.gold += sell_refund(sold.star, _bench_char_cost(sold))
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
            bc = s.bench.pop(action.bench_idx)
            bc.position_pref = action.to_row  # 记录实际站位
            s.deployed.append(bc)
            s.board[action.faction] = s.board.get(action.faction, 0) + 1
    elif isinstance(action, RefreshShop):
        s.gold -= action.cost
        # shop 内容变化未知(随机),不模拟具体牌;仅扣金
    # PickEvent 不在本模拟范围(event 单独决策)
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
        _merge_bench(bench)
    elif isinstance(action, SellBench):
        if 0 <= action.bench_idx < len(bench):
            bench.pop(action.bench_idx)
    elif isinstance(action, DeployMove):
        if 0 <= action.bench_idx < len(bench):
            bc = bench.pop(action.bench_idx)
            bc.position_pref = action.to_row
            deployed.append(bc)
