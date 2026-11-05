# 批 A：终局成员集读口 members（详设）

## 问题与约束

终局成员集（= core ∪ shared，注册表序去重，transition 不计）是策略侧多判据的输入，
无读口、14 处手写。语义同构已经双攻击者逐处核实（无一处含 transition、无一处顺序
反转、无额外过滤）；双列成员（core∩shared ≠ ∅，全库 18/21 套）靠各处写法天然去重
维持一致——该不变量活在 14 份手写默契里，无结构保证。

约束：

- 总纲划给的接口契约：读口 = `Comp.members` property，返回保序去重
  `tuple[str, ...]`；`predicates.line_members` 签名不变（薄委托）。
- 零行为漂移是本批最大资产——所有替换逐位等价。
- 行为安全网：`test_faction_migration_identity.py` +
  `fixtures/faction_migration_snapshots.json` 恒等快照（覆盖 hoard / board_line
  消费面，已核实）。
- **已知鸭型桩一处**（撤回「零鸭型桩」的总括声称）：test_sell_window_launch.py:105
  `SimpleNamespace(name='测试线', core_chars=('目标件',), shared_chars=())` 经
  shop 决策链（`decide_shop_action` → `direction_comp_of` → `predicates.
  line_members`）消费——薄委托后 `SimpleNamespace` 无 members 属性必红。该桩为本
  测试树唯一鸭型桩（其余 target_comp 赋值全部真 Comp / None，已逐一核对）。

### 14 处清单（定位 = 文件 + 函数/锚点；行号为设计基线快照、仅辅助）

| # | 位置 | 现形态 | 防御 |
|---|---|---|---|
| 1 | strategies/impl/mandate_v1/statefn/predicates.py `line_members` | 保序 tuple | 全 |
| 2 | strategies/impl/mandate_v1/session_scope.py `line_members_view` | 保序 tuple | 半 |
| 3 | strategies/impl/mandate_v1/criteria/refresh.py `_comp_members` | 保序 tuple | 半 |
| 4 | strategies/impl/mandate_v1/line_select.py `line_score_breakdown` | set | or-默认 |
| 5 | strategies/impl/mandate_v1/deploy_search.py L1 空羁绊分支 | set | or-默认 |
| 6 | strategies/impl/mandate_v1/deploy_search.py `_member_names_of` | frozenset | or-默认 |
| 7 | kernel/cw_intention.py `_line_hoard` | set | 直读 |
| 8 | kernel/cw_intention.py 义务面截断基准 `core_shared` | set | 直读 |
| 9 | kernel/cw_investments.py `strategy_faction_scope` 成员分支 | 布尔 | 直读 |
| 10 | strategies/impl/mandate_v1/criteria/priority.py 候选线并集 | set（两行式 fold） | 半 |
| 11 | strategies/impl/mandate_v1/criteria/sell_candidates.py 线内集 | set（两行式 fold） | 半 |
| 12 | strategies/impl/mandate_v1/shop.py 义务面买名单 | set（两行式 fold） | 半 |
| 13 | kernel/cw_launch_admission.py `sanctioned` 核准集 | set | 全 |
| 14 | kernel/cw_intention.py `hoard_target` 候选三线支 | set（两行式 fold） | 半 |

合法内联（不在清单、不替换）：cw_comps `derive_member_priority`（core/shared 两档
语义本身）、`_char_gift_tier` 三名单扫描（单点概念性枚举）。

## 方案

### 1. 读口定义（cw_comps.py，Comp 内、紧随 all_factions property）

```python
@property
def members(self) -> tuple[str, ...]:
    """终局成员集：core ∪ shared，注册表声明序去重（core 位在前）；
    transition_chars 不计（打工后卖，不构成终局成员）。
    消费语义锚 = strategy-docs/12_line_and_intention.md §2（line_members_view
    读口/禁第二读口径）与 strategy-telemetry `k_members` 行（锁定帧语义）。
    集合消费写 ``set(comp.members)``；序 = 注册表声明序（截断/排序 tie-break 消费）。"""
    return tuple(dict.fromkeys(tuple(self.core_chars)
                               + tuple(self.shared_chars)))
```

**docstring 措辞裁定**：不引「目标线 K」名号——该词在 P41 证明（K=core_chars）与
telemetry（core∪shared）口径不一致，且 predicates 现行引用的「01_math_framework
§2」为悬空引用（现行 01 号篇 §2 = 公理栈，无此概念）。读口只锚现行实现口径的正典
（12 号篇 §2 + telemetry k_members）。

### 2. 14 处替换（逐处新写法）

- #1 `predicates.line_members`：实现体改薄委托
  `return comp.members if comp is not None else ()`；**模块级 docstring（:1-5）与
  函数 docstring 双处**悬空引用修正（「01_math_framework §2『目标线 K』/§5.3」→
  12 号篇 §2 + strategy-telemetry `k_members`），并加一行「成员集单一源 =
  Comp.members，本函数只承载 None 语义与 strategies 层入口」。签名、返回类型、
  9+ 下游全部不动。
- #2 `session_scope.line_members_view`：`members = comp.members`（半防御删除）。
- #3 `refresh._comp_members`：函数删除（输出与 #1 同构）；调用点
  `_candidate_members` 改调 `comp.members`。同函数的「注册表外线名回退分支」
  随批申报死代码（配方层退役 + 锁定写入口 get_comp 校验后恒不可达），删除并在
  commit message 记指针。
- #4 `line_select`：`members = set(comp.members)`（后续 `- carry - key_items`
  差集表达式不变）。
- #5 deploy_search L1 空羁绊分支：`members = set(comp.members)`。
- #6 `_member_names_of`：`return frozenset(comp.members)`。
- #7 `_line_hoard`：`chars = set(comp.members)`（后续羁绊成员并入不变）。
- #8 义务面：`core_shared = set(comp.members)`（顺带消灭同函数内与 _line_hoard
  的重复并集计算）。
- #9 `strategy_faction_scope`：`if ch in comp.members:`（双层循环外提
  `comp.members` 一次，避免每角色重算）。
- #10 #11 #12（三处候选线 fold）：循环体改 `names |= set(c.members)` /
  `_cand_names |= set(_comp_c.members)`；候选解析失败的告警逻辑不动。
- #13 `sanctioned`：`set(comp.members)`（全防御删除）。
- #14 hoard 候选三线支：`chars |= set(c.members)`。

**死防御清理范围**：#1 #2 #3 #10 #11 #12 #13 #14 的 getattr/or-默认全部删除
（真 Comp 的 default_factory 保证字段恒在）。

**鸭型桩改造**：test_sell_window_launch.py:105 的 SimpleNamespace 桩补
`members=('目标件',)` 属性（或换真 Comp 构造——取改动更小者），随本批提交；改造
后该测试全绿为完成判据之一。

### 3. 验证与防线

- 替换后复核 grep（主判据 = 14 处逐一核对完成）：单行式
  `core_chars.*shared_chars|shared_chars.*core_chars` + 两行式形态
  `\.core_chars\)[\s\S]{0,120}\.shared_chars`（单向正则——#10/#11/#12/#14 替换前即
  core 行在前、shared 行在后的两行式 fold，全库无 shared 在前的反向形态，经复核
  确认）在 src/ 生产代码归零；测试仓期望值侧的手搓并集**刻意保留不换**（行为
  安全网，如 test_line_select 以手搓并集为期望值）。
- 行为锁：`faction_migration_snapshots` 恒等快照全量跑。
- **不新增**成员集构造断言测试（裁定：`members == 手搓并集` 属重述实现，测试纪律
  明禁；本批风险在「14 处替换漏/错」而非「一行 fromkeys 算错」，防线对准真实风险
  面——逐一核对 + 快照 + grep）。序契约（core 位在前）由 docstring 声明承载，
  不补专项用例。
- kernel DI 管道（cw_launch_admission 注入参、bridge 转接）本批不动：已裁定为
  独立后续迭代（design §1「明确不解决」）。

## 关键取舍

1. **property vs 模块函数 members_of**：选 property——Comp 同类纯投影（factions/
   all_factions/core_faction_reqs/bonus_faction_reqs）全走 property；模块函数族先例
   （carry_set/derive_key_equips）都是带外部依赖或兼容回退的重语义派生，members
   是对自身字段的纯投影。
2. **不新增构造断言测试**：理由见 §3；序契约不设专项用例（实现一行 fromkeys +
   docstring 声明，专项用例边际价值低于测试纪律成本）。
3. **返回 tuple 而非 set**：tuple→set 单向兼容（set 消费一次包装），反向要重建序；
   序是真实消费面（`_obligation_rank` tie-break、候选注册序终局裁定）。
4. **d1 schema 重构不做**：见总纲 §1「明确不解决」——transition_chars 退役后档位
   3 收 2 再定形；members 的消费契约（终局成员）在 d1 下不变、只换数据源，property
   是稳定接口。
