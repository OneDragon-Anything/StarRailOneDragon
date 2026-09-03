# P18 逐件证明验证报告

日期:2026-09(验证批);验证人:数学验证子代理;只读验证,未改任何 proofs/ 或代码文件。

## 0. 对象声明(先读索引定位,防编号撞车)

- 索引行:`docs/game/currency_war/research/math_proofs.md` 第 30 行:
  **P18 = 门辖帧(release 消费门激活)内,候选生成器输出集不含凑息向卖档(off_target/for_gold);不声明「帧内金不涨」**,
  状态「已证(集合过滤不变式,代码路径穷举)」,指向 `proofs/p18-release-gate-no-interest-sell.md`。
- 实际文件与索引行**一一对应,无编号撞车**(P19 为同批姊妹命题,对象不同,无重叠)。
- 本命题是**代码结构不变式**类命题(辖域=候选生成器输出集),非数值期望类——五门中③④按其性质降格为「机制语义对账」与「机检锁实证」。

## 1. 五门判定

### 门① 内部推导(逐步核)— **通过**

证明三步主链逐条重推:
1. 「SellBench 唯一生成点 = bench 循环,tag=None 即不生成」——推导有效(若唯一生成点被门拦截,输出集必不含该档)。
2. 「`_sell_tag` 全部返回值恒经 `_release_sell_gate`,无绕过 return」——推导有效,是全证明的关键支点。
3. 「门是纯过滤(∈{off_target,for_gold}∧门开→None;∉集合→透传),不产生不改写候选」——与 1/2 组合后结论必然成立。

④(判据单一源)与⑤(反例四路构造)为补强论证,逻辑无洞;反例表四路分类完备(生成器内/豁免面/辖域外/前提不满足)。

### 门② 锚点直调(逐项回代码 + 脚本重跑)— **内容全对,但锚点行号/前提全部过时**

逐项核对现行代码(`decision_v2/candidates.py`、`posture_release.py`、`kernel/cw_registry.py`):

| 证明锚点 | 现行代码 | 判定 |
|---|---|---|
| 门 `_release_sell_gate` = `candidates.py:366-389` | 现在在 **455-478**;行为逐行一致(tag ∉ 两档透传 / ∈两档 ∧ 门开 → None) | ✅ 语义成立,行号漂移 |
| `_sell_tag` = `:392-427`,末行恒 `return _release_sell_gate(...)` | 现在在 **481-518**,末行(518)仍恒经门,无绕过路径 | ✅ 关键支点成立 |
| 生成器卖段唯一生成点 = `:463-481` bench 循环 | 现在在 **556-574**;逐核 `generate_candidates` 全部动作类(买/兜底/卖/升级/刷新/部署/合成),SellBench 仍只在 bench 循环产生 | ✅ 成立 |
| `spend_gate_active` = `posture_release.py:225-237`,定义为 `registry.release_spend_gate_enabled ∧ session.v3_release is not None` | 现在在 **765-775**;**定义已变**:`release_spend_gate_enabled` 注册表字段**已被删除**(ADR-0426 增补 D 第 4 态清理,`cw_registry.py:949-951` 注释留档;A/B 开臂结案,消费门恒接线),现定义 = `session.v3_release is not None` | ⚠️ 前提过时,但**方向是强化**:门不再依赖开关,恒接线 |
| `sell_tag_priority` 只有三档 | `cw_registry.py:48-50` 仍恰为 off_target/for_gold/free_bench 三档,无新增涨金向档 | ✅ 辖集完备性成立 |
| 锁 B `test_release_gate_spares_free_bench_sell` | 存在于 `sr-od-test/.../test_cw_release_endgame.py:563/579` | ✅ 见门④ |

另:守卫链较证明写作时**新增** `form_break_sell_blocked`(`candidates.py:497`,ADR-0433)——提前返回 None,只会减少候选,不削弱不变式;证明守卫清单未列,属可补记项。

**脚本重跑**:`uv run pytest` 直跑两条锁 B(`test_release_frame_blocks_interest_motivated_sells` + `test_release_gate_spares_free_bench_sell`)→ **2 passed(3.42s)**,可复现。

### 门③ 建模对象 vs 玩法文档 — **通过(按命题性质降格为机制语义对账)**

- 「卖候选返金/涨金向」的动机语义:对照 `research/economy.md` §3(卖出退金规则单一源 = `cw_state.sell_refund`,1★全额/2★×3/3★×9,与生成器卖段 `income=sell_refund(...)` 同源)——「卖出会涨金」的建模前提与机制文档一致。
- 「凑息(息义务)与花钱向相悖」:对照 economy.md 收入公式行(利息 = gold//10,上限 5)——release 帧抑制「卖件凑金吃息」的行为语义与息律机制自洽;证明明示与 v1 `_maybe_sell_for_interest` 跳卖语义同构。
- 命题边界声明「不辖演进事务卖/谷底回滚卖」与代码结构(演进引擎在 `strategy` 发射点,不经生成器)一致,非文档性假设。

### 门④ 实证 vs 账本 — **通过(命题自声明纯文档批;以机检锁代实证)**

- 证明头部如实声明「纯文档批,代码路径穷举,无实验数据」——无虚报实证。
- 检验点 1(单帧实例,锁 B):存在且本轮重跑通过(见门②)。
- 检验点 2(辖集完备性静态断言「辖集 ⊇ sell_tag_priority 涨金向档」):**未落地为机检**——现仅靠人工核对三档字面量,证明自己提出的可机检项没有对应测试。见修正建议。
- 检验点 3(豁免面锚 free_bench 仍生成):锁存在且通过。
- 检验点 4(边界字面检验,禁表述为「帧内金不涨」):证明自身边界段与索引行表述均合规。

### 门⑤ 参数溯源(各常量;公理判定)— **通过,一处前提常量已失效**

- 门体**零调参**:辖集字面量 `('off_target','for_gold')` 是结构常量非阈值;判据单源 `session.v3_release`(由 `evaluate_release` 每轮入口写入)——符合零调参公理。
- 前提常量 `registry.release_spend_gate_enabled`:**已随 ADR-0426 增补 D 删除**——证明命题定义、边界第 3 条(「默认 False 时恒空洞真」)、反例表第 4 行(「开关关帧」)均引用该常量,现已失效;但失效方向是**强化**(门恒接线,命题辖域扩大为所有 release 帧,无空洞臂)。
- 超额收益隔离:命题显式声明「不声明帧内金不涨」并枚举三个金账豁免面——无过度声明。
- 纯金流:命题不涉金流数值,仅集合不变式,N/A(合规)。

## 2. 最终判决

**命题成立(经现行代码重推导 + 锁 B 重跑双重确认);证明文件需勘误更新,不影响结论方向。**

- 不变式本体:✅ 成立且较证明写作时**更强**(开关删除后门恒接线,无空洞臂)。
- 证明文件状态:**内容过时**——①前提定义引用已删除的注册表字段;②全部行号锚点漂移(366→455 等);③边界第 3 条与反例表第 4 行的「开关关帧」分支失效;④守卫清单缺 `form_break_sell_blocked`(不削弱命题)。

## 3. 修正建议(供命题维护方采纳;本验证批未改动)

1. **勘误前提定义**:命题的「门辖帧」改为 ≜ `spend_gate_active(session, registry) = True`(即 `session.v3_release is not None`),删除 `release_spend_gate_enabled` 合取项,并注明 ADR-0426 增补 D 后门恒接线、命题辖域扩大。
2. **刷新全部行号锚点**(candidates.py 455-478/481-518/556-574;posture_release.py 765-775),或改用符号名锚(建议后者,抗漂移)。
3. **删/改边界第 3 条与反例表第 4 行**:开关臂已不存在,「恒空洞真」表述失效;保留一句历史注即可。
4. **补记 `form_break_sell_blocked`**(ADR-0433)入守卫清单注记:提前返回 None,不削弱不变式。
5. **落地检验点 2 的静态机检**:向 `sell_tag_priority` 新增涨金向档时自动校验辖集字面量同步——一条参数化测试即可(遍历 `sell_tag_priority`,涨金向档 ⊆ 门辖集),这是证明自提但未兑现的唯一检验点。
