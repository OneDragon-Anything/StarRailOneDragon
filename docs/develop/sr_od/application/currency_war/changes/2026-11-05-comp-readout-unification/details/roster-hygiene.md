# 批 D：双列回声清理与 shared_chars 语义诚实化（详设）

## 问题与约束

- **双列回声**：core∩shared ≠ ∅ 的套数约 18/21（双王圣杯 4 人、列车 A/B 与龙丹/
  大黑塔/追击飞霄各 3 人等）——按 shared_chars 旧声明语义（「与其他阵容共享的 core」）
  如实登记的行，但该跨阵容语义零消费，双列成员在所有消费面被 core 列覆盖
  （members 去重 core 位在前、`derive_member_priority` core 胜、送卡档位机器 core
  档胜、布尔判定无差）——系统性数据噪声。
- **声明语义已死**：shared_chars docstring「与其他阵容共享的 core（转型可复用）」——
  转型机制已被配方体系取代（2026-11 配方层退役收尾），零消费者读跨阵容含义；活的
  语义 = 「第二档终局成员」（进终局成员集/采购面/送卡 20 分档，与 core 的区别 =
  装备 key 件绑定/不卖保护/证据 4000 档/优先级 0 档等身份行为包只挂 core）。

约束：**依赖批 A**（members 的 `dict.fromkeys` 对双列清理天然鲁棒——清理前后
`comp.members` 输出恒等；批 A 先落地 = 本批的行为锚，无需人肉推 14+ 处等价性）。

## 方案

### 1. 双列回声清理（数据批）

- 规则：`shared_chars` 列中与 `core_chars` 重复的名字删除（双列 → core 单列）；
  shared−core 非空的真第二档成员不动。
- 全库 21 套逐套执行，删除处带一行交叉核对注（如「三月七 shared 列回声清理：
  core 列在册，members/优先级/档位全消费面输出不变〔批 A 锚〕」）。
- 行为论证：members 输出恒等（fromkeys 去重）；`derive_member_priority` 的
  setdefault 顺序（core 先填）对 core∪shared 交集中的名字本来就取 core 档；
  送卡档位机器取最高档 core。全部 `.shared_chars` 读点（16 处）经逐点审计：14 处
  违例点全经并集/set 语义（批 A 已收编），2 处合法内联（derive_member_priority
  两档语义、送卡档位机器三名单扫描）对双列成员的输出均由 core 压过——回声清理
  后输出全部不变（脚本全库预演恒等）。

### 2. shared_chars docstring 诚实化（cw_comps.py 字段注释）

改写为活语义：

```
shared_chars: list[str]  # 第二档终局成员(进终局成员集/采购面/送卡 shared 档;
                         # 身份行为包——装备 key 件绑定/不卖保护/优先级 0 档——
                         # 只挂 core,这是与 core 的语义边界)
```

沿革（跨阵容共享标注的历史语义）归 git 历史，注释不写变更史。

### 3. comp-definition.md schema 表更新（归位声明）

本批**不直接改** `skills/sr-od-dev-currency-war/references/comp-definition.md`
（skill 文档 = 正本，修改归 landing 末阶段「正本更新批」）：其 schema 分层语义表
「成员」行措辞由正本更新批对齐本批定稿（shared = 第二档终局成员）并补读口层立法
三条与读口清单。本详设只留本指针，批 D 文件面不含该文件。

### 4. 回声防线（建库校验）

批 D 收尾加建库校验：`core∩shared = ∅`（`__post_init__` 或库级校验）——防回声
数据重现（双列清理后无校验 = 下次手编数据又能无声写回双列）。

## 关键取舍

- **清理 vs 保留双列作为「跨阵容共享」标注**：该语义零消费（全库 grep 核实），
  保留 = 持续为死语义付数据噪声成本；将来若转型类机制立项需要跨阵容关系，从
  plaza 统计/FINAL_COMPS 文档重新提取（版本重跑流程本就重 derive）。
- **本批与批 A 的顺序锁死**（依赖声明）：反序执行 = 在 14+ 处手写下人肉推等价性，
  批 A 的 fromkeys 锚失效。
