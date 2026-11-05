# 批 B：线 carry 单名锚统一（详设）

## 问题与约束

「这条线的 carry（核心输出角色）是谁」这一信息现存六处承载，口径分裂：

| 承载处 | 语义 | 与 `carry_anchor()` 关系 |
|---|---|---|
| `Comp.plaza_carry` 字段 | 聚类真值（统计事实；n<5 无聚类置空） | 权威源（非空直读） |
| `CARRY_ANCHOR_FALLBACK`（3 条） | 空值线攻略明文补全 | 组成部分（设计合理：不覆写聚类真值，两层证据互不污染） |
| `line_select.LINE_ANCHOR`（21 行手编表） | 攻略重述口径 | **20/21 纯复制**；唯一真分歧 = 火花星间旅人（表值花火 vs 聚类锚火花） |
| `equip_allocation`（**两处**：priority_order 分支的 plaza_carry 并集、缺省分支的 order 首位）/ `cw_equip_env`（一处，`in present` 判定） | 装备优先序第一人（plaza_carry 直读 + core 序兜底） | **不查 fallback**（空值 3 线无装备优先人） |
| `cw_plugins.cross_line_skeleton`（carries 集合） | 边界卡排除「线级定义件」 | 读聚类集合（`getattr(c, 'plaza_carry', '')`） |
| `cw_loop._allocator_update`（第六处） | 分配器 arm 键换算（`getattr(_c, 'plaza_carry', '')`） | 不查 fallback（空值 3 线 arm_id 恒空 → 终局 update 恒跳过） |

版本重跑 plaza 聚类后 plaza_carry 更新，六处不联动。

**全库验证数据（2026-11-05 脚本核实，作为本批行为申报的依据）**：

- `plaza_carry ∉ core_chars` 全库仅 1 条：火花星间旅人（火花 ∉ core，core[0] = 花火）；
- fallback 三线（银枝群攻/追击飞霄/专家桑博DOT）的 fallback 值**全部恰等于** 各自
  `core_chars[0]`——现行「本地实现不查 fallback 仍零行为差」靠此巧合成立；
- `carry_anchor ≠ core[0]` 共 3 条：火花星间旅人、巡海击破（波提欧 vs 不死途）、
  双王圣杯（Saber vs 吉尔伽美什）。

**分配器键空间的病灶本质（第六处深挖）**：`ThompsonAllocator.from_plaza`（
cw_run_allocator.py）用 `family_share` 的**键**建 arms——arm 键空间定义在初始化侧，
而 `_allocator_update` 侧用 plaza_carry 角色名匹配。cw_loop:1777 注释自述 57-A1
修过「键值不配对恒 no-op（62 局零累积实证）」——「阵容→arm 键」换算散在两侧正是
该 bug 的根，也是读口层立法的适用场景（键空间映射是派生概念）。

### intention_core 的定性（本批不动它，声明分工）

`cw_intention.intention_core`（plaza_carry ∈ core_chars 者优先，否则 core[0]）
**不是 carry 读口的冗余副本**，是独立概念「意向核心」——撤销计数 miss 计数的具名
单核，docstring 明示设计意图「∈core 约束保证 miss 计数良定义（避免花火/瓦尔特类
共享件在多线间产生噪声信号）」。它与 carry_anchor 全库仅火花线 1 处分歧（该线上
两者取值不同正是两个概念的真实语义差：意向核心拒绝不在 core 的聚类锚）。本批在
intention_core docstring 补一行分工声明，实现体不动。

约束：总纲契约 §2.3-2——评分锚读法 = 分歧登记表 ∘ carry_anchor，评分锚行为保真。

## 方案

### 1. LINE_ANCHOR 降为分歧登记表（line_select.py）

```python
#: 评分锚与 ``cw_comps.carry_anchor`` 的分歧登记（仅列不同值的线；
#: 默认读法 = 登记表 → carry_anchor()，20/21 线走默认）。
#: 火花星间旅人：攻略明文花火主C（BV 转录注）vs 聚类锚火花——评分口径取
#: 攻略重述（持有花火点亮该线证据的历史行为保真）；聚类真值不动（plaza_carry
#: 字段语义 = 层间交叉核对基准）。
_LINE_ANCHOR_DIVERGENCE: dict[str, str] = {
    '火花星间旅人': '花火',
}


def rating_anchor(comp: Comp) -> str:
    """评分锚（线分 CARRY_ANCHOR 档的具名核心；读法单一源）。"""
    return _LINE_ANCHOR_DIVERGENCE.get(comp.name) or carry_anchor(comp)
```

- 原 21 行表删除；`line_score_breakdown` 的 `anchor = LINE_ANCHOR[comp.name]` 改
  `anchor = rating_anchor(comp)`。
- `_validate_line_anchor` 改校验：登记表键 ⊆ COMP_LIBRARY 线名集、值 ∈
  CHARACTERS 注册表（手编写错名 import 即炸的防线保持）。
- `cw_line_scales.py` CARRY_ANCHOR 常量 docstring 指针
  （「基准判定表 = line_select.LINE_ANCHOR」）同步改为
  「基准判定读口 = line_select.rating_anchor」。

行为论证：20 套走 carry_anchor 与原表值相同（复制关系）；火花线经登记表取花火 =
原表值——**评分锚逐位保真，零漂移**。

### 2. 装备优先序三处统一（equip_allocation 两处 + cw_equip_env 一处）

plaza_carry 直读（含 order 首位回退）改读 `carry_anchor(comp)`：

- 18 条非空线：carry_anchor ≡ plaza_carry，零漂移；
- **3 条空值线（银枝/飞霄/桑博）：缺陷修复，非行为膨胀**——三条线的攻略均有装备
  明文（银枝 = 火力风暴潮 + 冷笑话引擎，77006068 直读注；飞霄 = 火力风暴潮×2，
  76883466 直读注；桑博装备公式 = 靴×2 + 物质分解液，final_dot_kafka.md 装备
  公式节），现状 bot 因装备语境不查 fallback 从未执行过这些明文（「无优先人」是
  漏读缺陷的表现，非知识真空——用户 2026-11-05 裁定指正）。统一后按攻略明文
  carry 优先拿 key 装备 = 攻略知识落地；幅度 = 装备分配的接收者顺序，不影响
  配对守卫/穿戴门等安全面。

### 3. 分配器键换算单一源（第六处收编；cw_run_allocator / cw_loop）

**键空间实测（已定死，无分支悬念）**：`_get_or_init_allocator` 的 arms 键 =
`PLAZA_CARRY_CLUSTERS` 中 `n_posts >= 15` 的聚类 carry 名（cw_loop 初始化
`share = {c.carry: c.n_posts / total for ... if c.n_posts >= 15}`，17 键）——
键空间即 carry 名空间，读口 `arm_key_of(comp) = carry_anchor(comp)` 落
cw_run_allocator 一处（cw_loop 仅改调）。

- `_allocator_update` 改调该读口，删除本地 `getattr(_c, 'plaza_carry', '')`。
- **行为申报（实测口径）：收编零漂移**——fallback 三线（银枝/飞霄/桑博，聚类
  <5 无簇）与 4 条低篇数线（巡海击破/龙丹战技点/昼神阿雅/DOT队，簇 8-12 篇
  <15）的 carry_anchor 值均 ∉ arms 键空间，防线 `arm_id not in
  self._allocator.arms` 照拦 → update 维持跳过，与现状一致；∈ 键空间的 14 线
  carry_anchor ≡ plaza_carry，换算值不变。收编收益 = 删第六处本地 getattr +
  键换算单一源（57-A1「键不配对」病灶的结构根治），行为面零变化。
- 落地验证：allocator 初始化日志的 arms 键列表与上式对照记入验收凭据。

### 4. cross_line_skeleton 统一（cw_plugins.py）

`carries = {c.plaza_carry for c in COMP_LIBRARY if getattr(c, 'plaza_carry', '')}`
改 `{carry_anchor(c) for c in COMP_LIBRARY if carry_anchor(c)}`。

行为论证：新增的 fallback 三人（银枝/飞霄/桑博）经核对**均不在**
W16_MAJORITY_LINES 的任何键集（不止边界组），边界卡排除逻辑输出不变——零漂移。
语义上统一后「线级定义件」口径完整（fallback 线的 carry 也是定义件）。

### 5. intention_core 分工声明（cw_intention.py）

docstring 补分工行（见 §问题与约束节），实现体不动。

## 关键取舍

1. **评分锚不直接改读 carry_anchor（火花线走登记表）**：两口径（聚类真值 vs 攻略
   重述）是真实语义差，不是冗余——登记表把 21 行复制压缩为 1 行真分歧，行为保真；
   覆写 plaza_carry 会破坏两层证据互不污染的既有设计。
2. **intention_core 不统一**：∈core 约束是 miss 计数良定义的刻意语义（共享件跨线
   噪声防御）；统一会把火花线 miss 计数核心从花火换成火花（跨线共享件正是它要防
   的噪声源）。
3. **装备优先序的行为变化接受申报而非规避**：规避方案（装备语境维持不查 fallback）
   会保留第五种本地读法，与收敛目标冲突；该变化方向与 fallback 的攻略明文语义
   一致。
4. **分配器键换算收编而非豁免申报**：影子期不构成豁免理由——57-A1 的恒 no-op 历史
   证明散在两侧的键换算已在产生真实 bug；读口化一次治本。
