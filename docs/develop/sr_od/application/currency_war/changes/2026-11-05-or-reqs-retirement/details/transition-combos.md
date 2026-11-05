# 过渡羁绊构造块与组合条目生成（详设）

## 问题与约束

- 边界：重构 `TRANSITION_LIBRARY`（4 条单体系条目 → 10 条组合条目）与配套读口（`TRANSITION_ENTRY_KIND` / `transition_member_set`）；**不动**候选计分/锁定机器本体（`update_transition_candidates` 的排序、top3、fp≥1.0 即锁逻辑逐行保持）、不动冷启动回退/保护/囤货/部署圈人的调用结构（它们经 `transition_member_set` / `transition_active_entries` 单一读口自动跟随）。
- 总纲契约 B：计分核心提纯为纯函数 `transition_scores(held, sources)`，实机帧与虚拟帧共用。
- 总纲契约 C：本篇先行（旧「希儿引擎」条目随之退役），详设三后行。
- 用户裁定（2026-11-05）：**锁定域 = 组合条目**。一个过渡阵容 = 两个过渡羁绊的完整组合，凑出两个羁绊（组合条目 fp ≥ 1.0）才锁定；单羁绊构造块不是条目、永不锁定——单羁绊凑出的局保持软方向（候选继续活动、买面双向），直到组合凑齐或终局锁定统一退役。
- 游戏知识依据（transition_combos.md 两两组合实证表，Early 647 帖）：实证表覆盖 6 种组合形态——三过渡互组 3 种（仙舟3+DOT2 84 帖最大配方、仙舟3+列车2 40、列车2+DOT2 16）+ 希儿系×三过渡 3 种（列车2+希儿系 13、仙舟3+希儿系 3、DOT2+希儿系 2）；含希儿组合的实证粒度只到希儿系级（量/贝归属未分），用户裁定按希儿系实证整体拆分全枚举 C(5,2)=10；「没有希儿时量子/贝不能独立当过渡（28 帖全部含希儿）」——量子/贝构造块必须点名希儿（混合型），不可做纯羁绊块。

## 方案

### 1. 构造块（模块级新结构，cw_comps.py）

```python
@dataclass(frozen=True)
class TransitionBond:
    """过渡羁绊构造块：组合条目的生成原料；不是阵容、不进 TRANSITION_LIBRARY、不可锁定。"""
    name: str                        # 块短名（组合条目名与 parts 索引的组成部分）
    bond: str                        # 羁绊规范名（组合条目 faction_reqs 档 0 键）
    tier: int                        # 达标人数阈值（体系判据档 = FACTIONS[...].tiers[0] 口径，沿 3.3 裁定）
    named: tuple[str, ...]           # 点名件（空 = 羁绊型：不限定人）
    need_star: tuple[tuple[str, int], ...]   # 点名件星级目标（键 ⊆ named；frozen 结构用 tuple 对）
    hybrid: bool                     # 羁绊半边是否计入持有分（点名型 False / 羁绊型与混合型 True）
```

五块数值表（知识源沿 3.3 条目表 + transition_combos.md 四体系表；费段已核 `CHARACTERS.cost` 与 cw_shop_odds 位面 1 费段）：

| 块名 | bond | tier | named | need_star | hybrid | 依据 |
|---|---|---|---|---|---|---|
| 仙舟3 | 仙舟 | 3 | 爻光, 藿藿, 丹恒·饮月 | 三人各 2★ | False | 「仙舟3 = 三人组的同义词，95% 帖含全三人组」；凑数仙舟件非证据（点名型） |
| DOT2 | 持续伤害 | 2 | （空） | （空） | True | 用户裁定「DOT 不限定人」 |
| 列车2 | 列车同行 | 2 | 姬子·启行, 三月七 | （空） | False | 「线定义件引导（姬子在场才值得朝列车走）」；任意列车成员非证据 |
| 希儿量2 | 量子同频 | 2 | 希儿 | 希儿 3★ | True | 「没有希儿时量子不能独立当过渡」；放大器经羁绊半边覆盖 |
| 希儿贝2 | 贝洛伯格 | 2 | 希儿 | 希儿 3★ | True | 同上 |

**计分成员域**（构造块的派生属性，单一源函数）：

```python
def bond_score_members(block: TransitionBond) -> set[str]:
    """块的计分成员域：named ∪ (羁绊全体注册成员，若 hybrid 或无名件)。
    点名型（named 非空 ∧ 非 hybrid）= 羁绊半边不计（仙舟凑数件/任意列车成员不是证据）；
    羁绊型（named 空）与混合型 = 羁绊半边计入。成员口径 = bond_members 的阵营∪流派全集（现行 transition_member_set 同式）。"""
```

### 2. 组合条目生成（建库期，cw_comps.py）

```python
TRANSITION_BONDS: tuple[TransitionBond, ...] = (仙舟3, DOT2, 列车2, 希儿量2, 希儿贝2)

#: 组合条目名 → 两块名（transition_member_set 的 combo 展开单一源）
TRANSITION_COMBO_PARTS: dict[str, tuple[str, str]] = {}

def _build_transition_combos() -> list[Comp]:
    out: list[Comp] = []
    for a, b in itertools.combinations(TRANSITION_BONDS, 2):
        core = list(dict.fromkeys((*a.named, *b.named)))   # 保序去重（希儿双修两块点名合并为一人）
        name = f'{a.name}+{b.name}'
        TRANSITION_COMBO_PARTS[name] = (a.name, b.name)
        out.append(Comp(
            name=name,
            core_chars=core,
            faction_reqs={0: {a.bond: a.tier, b.bond: b.tier}},   # 两键 AND；五块键互斥，无冲突
            required_deployed=tuple(core),   # 点名件全部在板（沿 3.3 建库自动填规则，生成期显式填）
            need_star={n: s for blk in (a, b) for n, s in blk.need_star},
        ))
    return out

TRANSITION_LIBRARY: list[Comp] = _build_transition_combos()   # 恒 10 条，C(5,2)
```

- 生成条目名清单（telemetry `sess_p1_pair` / `transition_locked` 存条目名，名字空间稳定）：
  仙舟3+DOT2 / 仙舟3+列车2 / 仙舟3+希儿量2 / 仙舟3+希儿贝2 / DOT2+列车2 / DOT2+希儿量2 / DOT2+希儿贝2 / 列车2+希儿量2 / 列车2+希儿贝2 / 希儿量2+希儿贝2。
- 旧条目名（仙舟铁三角/廉价DOT/列车骨架/希儿引擎）退役；旧对局回放读旧名时 `transition_entry_of` 返 None、`transition_active_entries` 跳过——历史数据兼容。
- **成型语义**：组合条目 fp = (块A羁绊达标进度 + 块B羁绊达标进度 + required 逐名)/N——fp ≥ 1.0 ⟺ 两羁绊都凑齐 ∧ 点名件全在板。例：仙舟3+DOT2 = 仙舟≥3 ∧ DOT≥2 ∧ 铁三角三人在板；希儿量2+希儿贝2 = 量≥2 ∧ 贝≥2 ∧ 希儿在板（双修雏形）。
- **单羁绊不锁的机制承载**：构造块不进 `TRANSITION_LIBRARY`——候选计分/锁定域 = 库内组合条目，单羁绊凑出时任何组合条目 fp < 1.0（另一键必缺），自然不锁。无需任何特判。
- 人口可行性核对（位面 1 lv5-6 ≈ 5-6 人，cw_economy 位面-等级骨架）：最大组合 仙舟3+希儿量2 = 铁三角三人 + 希儿 + 2 量子放大件 = 6 人，可行；希儿量2+希儿贝2 = 希儿 + 2量 + 2贝 = 5 人，可行。

### 3. 读口改造（cw_intention.py）

- `TRANSITION_ENTRY_KIND` 表**删除**（三型知识收进构造块的 `hybrid`/`named` 字段，组合条目恒为 combo 型）。
- `transition_member_set(comp)` 改造：查 `TRANSITION_COMBO_PARTS[comp.name]` → 两块 `bond_score_members` 并集（集合语义天然按角色去重——一名角色跨点名与多羁绊阵营只计 1 分，沿 3.3 混合型口径）。未知名（防御态）返空集。
- `transition_library_buy_now_union` / `transition_member_union` / `transition_active_entries`：经上述单一读口自动跟随，零改动（并集幂等：组合并集 = 五块域并集，冷启动回退面与现状等值）。
- **旧建库自动填循环删除**（cw_comps.py 现行 `for _entry in TRANSITION_LIBRARY: if _entry.core_chars and not _entry.required_deployed: ...`）——新库生成期显式填 `required_deployed`，该循环对新库幂等空转，随旧库退役删除。
- `update_transition_candidates` 主体零改动；唯一重构 = 计分与排序核心提出为契约 B 的纯函数：

```python
def transition_scores(held: frozenset[str] | set[str],
                      sources: tuple[str, ...]) -> list[tuple[str, float]]:
    """过渡组合条目计分与排序（纯函数）：持有分（计分成员域 ∩ held 计数）+ 词缀/boss 减分面，
    过滤总分 > 0，按（分数降序, 注册序）返回有序全序列表。
    实机帧（update_transition_candidates）与虚拟帧（货架资格臂，详设四）各自切片取前 N
    （纯切片）；排序键在函数内单一实现——禁调用侧自排（tie-break 分叉 = 虚拟候选序与
    实机锁定序分叉）。"""
```

`update_transition_candidates` 内部改为：`ranked = transition_scores(_owned_chars(gs), sources)` → 取前 `_TRANSITION_CANDIDATE_TOP_N` 写槽 → 锁定逻辑逐行保持。

- 词缀减分表 `TRANSIT_AFFIX_PENALTY` 数据零改动（键 = 羁绊名，组合条目档 0 键 = 两块键，自动命中）；注释「克希儿引擎」改「克量子同频/贝洛伯格键的组合条目」。粒度行为：量子熄火等 5 词缀命中**含量子/贝键的 7 条组合**（含希儿量2 块的 4 条 ∪ 含希儿贝2 块的 4 条，双修条「希儿量2+希儿贝2」两边都含、按条目只计 1 次），各减一次——克希儿局希儿组合全压、其余 3 条组合（仙舟3+DOT2 / 仙舟3+列车2 / DOT2+列车2）自然上位（减分制设计语义；7 + 3 = 10 = 库容）。

### 4. 建库校验（`_build_transition_combos` 生成后自检，import 即炸）

1. 库长 = C(5,2) = 10；`TRANSITION_COMBO_PARTS` 键集 = 条目名集；
2. 五块 `bond` 互斥（两两组合无键冲突——生成器结构保证，校验防御手改）；
3. `named` ∪ `need_star` 键 ∈ `CHARACTERS` 注册表；
4. `need_star` 键 ⊆ `named`；
5. 点名件费段位面 1 可刷（沿 3.3 硬约束：lv1-3 仅 1 费 / lv4 起 1-3 费 / lv5 起 4 费——现五块点名件 1-3 费，全过；校验以 `CHARACTERS.cost <= 3` 表达，与费段真值表的对应关系就地注释）。

### 5. 行为变化申报

1. 过渡候选域 4 → 10 条；锁定对象 = 组合条目（两羁绊完整组合）；
2. 单羁绊局永不锁（过渡锁定态恒空）——保护/囤货按候选并集保持软方向，直到组合凑齐或终局锁定退役；对照实证（Early 纯 1/2 费层 328 帖中两两组合 140、四种都不含 49，其余约 139 帖为单体系中间态）——中间态局买面比现行宽（现行锁单条目后收窄为单方向）；
3. 词缀减分粒度：希儿系 1 条 → 含量子/贝键的 7 条组合各命中（见 §3）；
4. 过渡锁定态可锁组合形态（如「仙舟3+DOT2」），保护/囤货域 = 该组合两块的计分成员域并集。

## 关键取舍

- **放弃「5 单条 + 10 组合并存、都可锁定」**（上一稿方案）：单条目可锁会复现「先锁单条、组合永不升级」的方向缺口；用户裁定单羁绊不是阵容——构造块降为生成原料，问题结构性消失。
- **放弃「锁后可升级为严格超集」**：违反「锁后不换、不解、不重评」契约（3.3 用户裁定），引入新特判；组合制下锁定的方向已含两羁绊，升级需求基本消失。
- **放弃手写 10 条组合**：构造式生成单源（仙舟三人名单只写一处），手写 10 条 = 名单多胞胎（同块点名在 4 条组合里重复 4 次），违反字段准入判据 3。
- **放弃「组合条目带档 1」**：过渡语义 = 低门槛快锁（3.3 数值口径裁定），过渡条目只填档 0；档位推进（仙舟3→5 等）属「成型后的场况插件」纪律（transition_combos.md「加法升级原则」节），归部署/买牌机器状态驱动，不预枚举。
- **保留 kernel 结算侧谓词族不动**（契约 D）：`seele_system_formed`（希儿 ∧ 量2∨贝2）在结算键/胜率模型/A-B 工具的观测语义独立成立；过渡决策侧拆两条组合承载后，两侧判据口径差异（观测侧「任一」vs 决策侧「组合」）就地注释声明，非双源——一个是观测语言、一个是决策条目。
