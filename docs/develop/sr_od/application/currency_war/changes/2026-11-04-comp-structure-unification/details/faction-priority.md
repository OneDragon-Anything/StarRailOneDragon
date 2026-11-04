# 羁绊优先级结构（详设）

## 问题与约束

- 本主题边界：`Comp` 的羁绊要求字段（form_tiers/sub_tiers）及其全部消费面的结构统一；不涉阵容数值知识、不涉克制机器本体（见 counter-tables 详设）、不涉 flex_factions 的存废（保留，见取舍）。
- 总纲契约：本篇产出的 `core_faction_reqs`（档 0 读口）被 counter-tables（受克判定）与 transition-library（过渡条目结构）消费。
- 现状约束（2026-11-04 会话逐点核实）：
  - `form_tiers` 消费 10+ 处（成型/部署 L1/囤货键/投资通道/选卡受克/面板主羁绊）；`sub_tiers` 消费 5 处（部署 L2/囤货键）。
  - 两处消费面直接排除副档：投资通道 `_faction_hit_bonus`（设计文本三层规则 form/flex/未命中，无副档分支）、轮廓计数 `all_factions`（= factions ∪ flex）。排除为历史遗留非设计裁定（字段后加，消费面未接）。
  - 副档值域 `int | tuple[int,int]` 的 tuple 形态全库零使用。
  - 现行迁移期双源先例：`member_priority` 字段因「20/20 恒派生零手编」退役为 `derive_member_priority` 现算——字段收敛有先例可循。

## 方案

### 1. 数据结构

```python
@dataclass
class Comp:
    faction_reqs: dict[int, dict[str, int]] = field(default_factory=dict)
    """羁绊要求(优先级结构):键 = 优先级档(0 最高,档号小 = 重要),
    值 = {羁绊规范名: 目标人数(几人激活算达标)}。
    - 档 0 = 核心羁绊层:同档多键 = 需要多个核心羁绊,等权、全部凑齐才成型;
    - 档 ≥1 = 加分层(原 sub_tiers):进部署次层与采购面,不进成型判定;
    - 档 0 可缺席(非羁绊成型阵容,如反甲白厄)。"""
```

`form_tiers` 与 `sub_tiers` 字段删除（不留兼容读法——项目规范禁双源）。

### 2. 语义三规则（全行为定义）

1. **只有档 0 参与成型判定**：`form_progress` 只读档 0，逐键 `min(板面人数, 目标)/目标` 取均值；档 0 空 → 成型度恒 0（装备流走轮数兜底，与现行 form_tiers={} 语义一致）。
2. **档 ≥1 是加分层**：部署搜索次优先层（L2）与囤货采购面包含；不影响成型结论。
3. **档内无次序**：键书写顺序零语义（「首键当主派」约定废止；其最后消费面随体系配方机器在 transition-library 详设中退役）。**过渡期例外（3.1→3.3 之间）**：`cw_intention.py:544` 的首键读法暂存（`next(iter(c.form_tiers))` 改读 `core_faction_reqs` 首键），行为不变的前提 = 迁移规则 `{0: form_tiers}` 保持插入序（dict 构造保序，语言保证）；3.3 随体系配方机器整体退役该读点。

### 3. 统一读口（消费端代码的唯一入口）

```python
@property
def core_faction_reqs(self) -> dict[str, int]:
    """档 0:核心羁绊层(成型判据层)。"""
    return self.faction_reqs.get(0, {})

@property
def bonus_faction_reqs(self) -> dict[str, int]:
    """档 ≥1 合并:加分层(部署次层/采购面)。档号升序合并——同一羁绊
    不跨档(建库校验),故合并顺序不产生覆盖歧义,仅为确定的遍历序。"""
    out: dict[str, int] = {}
    for p in sorted(self.faction_reqs):
        if p:
            out.update(self.faction_reqs[p])
    return out

@property
def factions(self) -> list[str]:
    """核心羁绊键集(档 0 派生)。"""  # 替代原 form_tiers 键派生
    return list(self.core_faction_reqs.keys())

@property
def all_factions(self) -> set[str]:
    """阵容轮廓:核心 ∪ 副档 ∪ 弹性(行为修正点,见 §5)。"""
    return (set(self.factions) | set(self.bonus_faction_reqs)
            | set(self.flex_factions))
```

### 4. 消费面映射表（全部读点；「行为变化」= 迁移测试的显式断言面）

| 消费端 | 现状读法 | 新读法 | 行为 |
|---|---|---|---|
| 成型度 `form_progress` | form_tiers 等权均值 | core_faction_reqs 等权均值 | 恒等 |
| 部署搜索 L1（主层圈族/权重） | form_tiers | core_faction_reqs | 恒等 |
| 部署搜索 L2（次层完成度） | sub_tiers | bonus_faction_reqs（全档 ≥1 合并；将来更多档全进 L2，档号作 L2 内部次序） | 恒等 |
| 囤货采购集键（`_line_hoard` 等） | form ∪ sub 手写并集 | core ∪ bonus（统一读口） | 恒等 |
| 投资通道 `_faction_hit_bonus` | form/or 键=全档分；flex=降档；副档=0 | 档 0/or 键=全档分；**副档键=降档分（INVEST_SOFT 同 flex 规则）**；flex 不变 | **变化①**：副档键命中 0 → +30/0 |
| 阵容轮廓 `all_factions`（星徽购买分、开线资格） | factions ∪ flex（不含副档） | factions ∪ **bonus** ∪ flex | **变化②**：副档键计入轮廓 |
| 选卡受克判定 | form/or 键（经改名层） | **3.1 中间态**：`punished_mechs_of` 改读 `core_faction_reqs`（改名层保留，键集恒等 → 行为恒等）；**3.2 终态**：改名层删除，判定直写（契约 A，counter-tables 详设落地） | 恒等（两态均） |
| 面板主羁绊名（cw_intention 首键） | form_tiers 首键 | 随体系配方机器退役（transition-library 详设）；过渡期保留读 core_faction_reqs 首键不删行为 | 恒等 |
| **投资护栏指向集**（cw_intention `locked_faction_scope`:1467） | form_tiers ∪ sub_tiers 键直读 | `core_faction_reqs ∪ bonus_faction_reqs` 键（护栏指向含副档键——轮廓语义同 §4 轮廓计数行的扩展） | 恒等（键集不变） |
| or_reqs 承接规则 | form_tiers 同键免 AND 账 | core_faction_reqs 同键免 AND 账（or_reqs 键 ⊆ 档 0，校验钉死） | 恒等 |
| **配方伪阵容构造**（cw_recipe.py `_RECIPES` ×3、cw_intention `pair_target_comp`） | `Comp(form_tiers=…)` 关键字构造 | 构造点同批改 `faction_reqs={0: …}`——**字段删除后关键字构造在 import 期即 TypeError，本表行是 3.1 的硬阻断项**；两处符号在 3.3 随配方机器整模块退役，3.1 仅做构造式迁移 | 恒等 |
| **线距离/换线经济学**（cw_line_switch.py `tier_progress`/`e_rounds`） | `getattr(comp, 'form_tiers', None)` **防御式读** | 改直读 `core_faction_reqs`——防御式读在字段删除后**静默归空**（tier_progress 恒空 → 线距离恒 0 → 判「已完成」），不报错且恒等测试原快照面不含线距离，**必须**：①改直读；②线距离进 §7 快照面 | 恒等（改造后） |

### 5. 建库期校验（`__post_init__` 扩展）

1. 全部羁绊名 ∈ 合法羁绊名白名单（= `cw_factions.FACTIONS` 注册表键全集；注意这不是 `_line_hoard` 的口径——后者是「档位键 ∩ 每角色阵营/流派非空」的成员圈定，不做白名单校验，两者是不同判定）；
2. 同一羁绊不得出现在两个档；
3. `or_reqs` 键 ⊆ 档 0 键集——**实施时点 = 3.3**（唯一违反者是 `pair_target_comp` 希儿系组合的动态构造（放大器键只挂 or_reqs 不进档 0，cw_intention.py:1025 评估域生产可达），该函数随配方决策层在 3.3 退役；3.1 实施会在 3.1→3.3 过渡期炸运行时构造帧——校验③随冲突源消失在 3.3 落地，不留特例）；
4. 档号非负、不跳档（连续 0..max）；
5. 值恒为正整数（tuple 区间形态随 sub_tiers 删除一并废止）。

### 6. 数据迁移（21 套，规则 + 全量核对）

机械规则：`faction_reqs = {0: form_tiers} ∪ ({1: sub_tiers} if sub_tiers else {})`——**所有键值不变**。迁移脚本生成 21 套对照表（本详设附录随落地批产出，人工过目后入库）。flex_factions 与优先级键的重叠（列车·护盾、黄泉·击破等）为合法形态，保持原样。

### 7. 迁移恒等测试设计

**快照构造（核心设计，非目标描述）**：
- **fixture 板面集**：脚本生成，每条线 3 个代表板面 + 全局 2 个混合板面 = 65 个板面 fixture，JSON 入测试仓（`sr-od-test/test/sr_od/application/currency_war/kernel/fixtures/faction_migration_snapshots.json`）；生成脚本落点 = 同目录 `gen_faction_snapshots.py`（测试仓工具，迁移前运行一次产出期望 JSON 后随仓提交）；
- **板面构造规则**：零羁绊板 = 空/杂牌成员；**半成型板 = 每个档 0 键各上 ⌈目标人数/2⌉ 名该羁绊注册成员**（成员取注册表该羁绊成员名单前 N 名，构造确定性）；成型板 = 各键达标人数；混合板 = 两线成员各半；
- **流程**：迁移**前**在旧代码上跑快照脚本（板面 fixture × 21 套 → 成型度/部署 L1/L2/囤货采购集/**线距离**（cw_line_switch 防御读改造项）/**受克判定输出**（3.1 中间态行为面）/投资通道逐卡加分），期望值写入 JSON；迁移后测试读 JSON 逐位断言；
- **变化①②（§4 表）**按新语义生成期望并单列断言（标注「副档语义修正」），其余全部恒等断言。测试面挂 `test_faction_derivation_locks.py` 同域。

## 关键取舍

- **放弃「每羁绊连续权重」**（如减益 0.7/巡海 0.3）：用户 2026-11-04 裁定同角色侧档位制（core/shared 二档先例 + member_rank 两档投影），档间是强度分层非数值加权；连续权重引入标定负担且无消费面。
- **放弃「把 flex 并入最低优先级档」**：flex 语义 = 容忍（不追求不拒绝），优先级 = 要求（主动凑），正交维度；派生检查（21 线 flex vs 成员自带阵营并集，恒等 0、双向大差异——flex 含成员派生不出的实证条目 6 线，成员自带未收的远多于已收）证实 flex 是 plaza 板面分布的真手编知识，不可派生、不可混装。
- **放弃「维持副档 0 分零漂移」**：副档两处排除是历史遗留（§问题与约束），按优先级本义（同种东西强弱阶梯、所有消费面降档包含）修正——用户 2026-11-04 纠正裁定。
