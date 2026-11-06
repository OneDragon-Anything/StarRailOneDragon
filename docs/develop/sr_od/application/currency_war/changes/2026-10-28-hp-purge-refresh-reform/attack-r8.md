# 第 8 轮收敛验证报告（r8 · 极小范围定点核验）

- 日期：2026-10-28
- 范围：第 7 轮修复面逐条核验 + 全篇一致性抽查（非全量轮）。审查对象 = design.md、details/hp-purge.md、details/refresh-chain.md、details/shop-buy-reform.md、landing.md、README.md。
- 方法：现状 vs 验证清单逐条比对 + 代码锚直调复核（`strategies/impl/mandate_v1/` 下 shop.py/entry.py/contracts.py/lambda_death.py/predicates.py 及 sr-od-test 对应测试）。前七轮报告（attack-r1~r7.md）按纪律未读；迭代目录整体 untracked（git 无历史），未做 diff 基线比对。
- 结论：**发现 7 条（高 0 / 中 4 / 低 3），不触发定稿。** 发现集中在两个根因：①r7 行段重基线未按 iteration-design.md §5.4 全量同步到 landing 3.2/3.3 与 shop-buy-reform 边界（F-2/F-3/F-4）；②B-12「λ 表血带维」处置面欠精确（F-1）。修复后建议对修复面做一轮定点复验再收敛。

## 发现清单

### F-1【中】B-12「λ 表血带维」处置面与文件面/代码实况脱节（验证清单项 2/3/4 面）

- 位置：details/hp-purge.md:24（B 组例外段）、design.md:47（hp-purge 独占文件面）、landing.md:29（3.1 文件面）、details/hp-purge.md:48（§6 词表）。
- 现状：hp-purge.md:24 指派 B-12「λ 表血带维参数实在 `lambda_death.py` → 删除为零行为变化（直调核验），随删并申报」，但：
  1. **文件面漏收编**：`statefn/lambda_death.py` 未进总纲 §2.1 hp-purge 独占清单、未进 landing 3.1 文件面（两处只有 `statefn/predicates.py`）。文件面互斥契约（各详设不得触碰对方文件面）下，落地批对该文件无授权——B-12 执行必然撞墙或越权。
  2. **随删子集未排除保留锚**：代码直调——`predicates.py:126-185` 的 `p1_blood_floor`/`p2_blood_floor`（R-7 保留观测谓词，hp-purge.md:49 不过扫）与 `sr-od-test/.../test_levelup_prob_axis.py:406` 均导入 `lambda_death.HP_BAND_NEAR_DEATH` 作阈值单一源（predicates docstring 明令「禁本处字面量」，测试注释明锁「阈值单一源 = HP_BAND_NEAR_DEATH…非本地第二份」）；hp 清查件 B-11 行亦明示该依赖。字面执行「B-12 随删」（清查件 B-12 范围 = `:34-39 + :108-146`，含 HP_BAND_NEAR_DEATH/HP_BAND_MID 常量 + hp_band + make_key）会破坏 R-7 保留面与其测试锁。「删除为零行为变化」申报仅对 `make_key`/`hp_band`/`HP_BAND_MID`（零外部消费子集，直调核实 src 与测试均无调用）成立。
  3. **词表无兜底**：该文件被删符号（hp_band/make_key/HP_BAND_MID）不在 §6 清零词表，符号级残留扫描对此文件无验收兜底。
  4. 附带：hp-purge.md:24 末句「三态规则①不适用于该文件本体」的「该文件」存在两读（cw_first_passage.py 或 lambda_death.py），加剧随删子集范围不清。
- 修复方向：总纲 §2.1 与 landing 3.1 文件面收编 `statefn/lambda_death.py`；hp-purge.md:24 明确随删子集 = make_key/hp_band/HP_BAND_MID，`HP_BAND_NEAR_DEATH` 保留为 predicates 阈值锚（R-7 联动）；词表补该子集符号或改申报 diff 核对验收；澄清「该文件本体」指代。

### F-2【中】landing 3.2 文件面 shop.py 行段为旧基线（验证清单项 1/5）

- 位置：landing.md:43。
- 现状：`shop.py:1-249` + `shop.py:267` + `:1962-2080`；总纲口径（design.md:46，代码实核吻合：全文件 2080 行；ρ 别名段止于 :231-233）= `:1-233` + `:267-315` + `:1962-2080`。两处错：`:1-249` 把 shop-buy-reform 的 `_merge_pair_names` 段（:234-266 前半）错划给 3.2 → 两阶段文件面重叠冲突；`:267` 单行欠 scope——`p92_seat_recoverable` 函数体实为 :267-315 整段随门删除（代码直核实锚）。
- 修复：landing 3.2 文件面改为 `shop.py:1-233` + `shop.py:267-315` + `:1962-2080`。

### F-3【中】landing 3.3 文件面 shop.py 行段为旧基线（验证清单项 1/5）

- 位置：landing.md:57。
- 现状：`shop.py:250-1961`；总纲口径 = `:234-266`（合成腿谓词段）+ `:316-1961`（六序买入/M6:1543-1616/垫件/序 5/序 6/C1；代码直核 M6 注释起 :1543、块止 :1616）。`:250-1961` 起点切进 `_merge_pair_names` 函数体内、漏 :234-249 与 :267-315 缺口段归属。
- 修复：landing 3.3 文件面改为 `shop.py:234-266` + `:316-1961`。

### F-4【中】shop-buy-reform 边界行段为旧基线（验证清单项 1/5）

- 位置：details/shop-buy-reform.md:5。
- 现状：「≈L250-1961」；总纲口径 = `:234-266` + `:316-1961`。`_merge_pair_names` 函数体实为 :234-264（refresh-chain.md:21 的函数级锚 `:234-264` 与代码吻合、不算错），段界含尾空行至 :266。
- 修复：边界改为 `:234-266` + `:316-1961`。根因同 F-2/F-3：r7 行段重基线后 landing/详设未做全量同步复查（iteration-design.md §5.4）。

### F-5【低】refresh-chain.md:42 过程叙事残留「（对抗 B5）」（验证清单项 5）

- 现状：「ρ 实费档口径（对抗 B5）」——以对抗轮 issue 号标注主张来源，违反 iteration-design.md §5.3（无过程叙事）。同一口径在 design.md:71（实现口径申报行）已有无叙事版本。
- 修复：删「（对抗 B5）」括注，依据就地挂 design §3 实现口径申报行 / 裁定 #6 细化。

### F-6【低】`levelup_blood_gate_defer` 未入 §6 清零词表（验证清单项 3）

- 位置：details/hp-purge.md:48（词表）与 :50（处置声明）。
- 现状：词表（被删符号清单）无此键，仅 :50 处置声明提及「旧拒因键清零，新拒因键 = `xp_batch_payment_defer`」。按 §6 自身口径（词表 = 被删符号清单、符号级残留清零 = 完成必要条件），被删键应入表，否则残留扫描不兜底。代码实况：发射点 `levelup.py:387` 在 R-1 改名面内随批替换（风险有界），但 `levelup.py:314` docstring 提及与 `test_shop_session_loop.py:679` 断言不在扫描门兜底内。
- 修复：词表补 `levelup_blood_gate_defer`（`xp_batch_payment_defer` 为新增键，不扫）。

### F-7【低】landing 3.1 文件面把 contracts.py:88-106/:166-171 列为「hp 行级」，与 hp-purge「无需改码」申报相抵（验证清单项 2 面观察）

- 位置：landing.md:29 vs details/hp-purge.md:32-33 + design.md:49。
- 现状：hp-purge 两处申报「契约守卫面（contracts.py:88-106/:166-171）直调核验不读 H——无需改码，随行为变化申报」「保留不删」；总纲 §2.1 contracts.py 行级分配（3.1 = :243-246；3.2 = :252/:255/:261-267/:273/:279-291）均不含这两段。代码直调证实：:88-106（S 预留前提守卫）与 :166-171（K 投影域 p2plus 支）只读 k_members/k_target/k_fallback_* 字段与 `K_FALLBACK_SOURCE_THREE_ARM` 常量，无 H 读取——hp-purge 申报与代码吻合，landing 3.1 收录并标注「hp 行级」= 授权面虚胖 + 标签失真（design↔landing 失同步）。
- 修复：landing 3.1 文件面删 `:88-106/:166-171`，或改注「直调核验不读 H、无需改码——随行为变化申报」。

## 复查面清单（PASS 面，逐条给判定与证据）

| 清单项 | 判定 | 证据 |
|---|---|---|
| 1. shop.py 行段五处一致 | 2/5 过 | 总纲 §2.1（基准，代码实核吻合：2080 行 / `_merge_pair_names` :234-264 段尾 :266 / `p92_seat_recoverable` :267-315 / M6 :1543-1616 / 发射段 :1962-2080、免费支 :1963-1971、整级预留 :1981-1989、`r2_budget` 消费 :1994、P92 装配 :1996-2054、计数键 :2062-2065、`must_spend_r1_budget_fail` 在 r2 拒绝域 :2067）✓；refresh-chain 边界 ✓；shop-buy-reform 边界 ✗ = F-4；landing 3.2 ✗ = F-2；landing 3.3 ✗ = F-3。contracts.py 锚点面直调核对一致（:243-246 level_spend_blocked / :279-282 r2_card_reserve / :283-287 P92 契约行 / :288-291 qualified_member_costs），总纲 :279-291 与 landing 3.2 拆分同集 |
| 2. hp-purge 无「两消费位等值锁」义务残留 | 过 | hp-purge.md:33 明示「两行均无 H 值流，无『两消费位等值锁』义务」、design.md:46 同口径（三行 carve-out，随删/注释申报）；代码直调 :327（refresh_ev_budget 注释行）/ :373（docstring 引 `kernel.no_target_arms` 行）/ :996（`[], frozenset()` 字面空集调用行）均无 H 值流 ✓。landing 3.1 文件面：无 cw_first_passage.py ✓、有 entry.py:844-846（代码实核 = 血本位支付措辞块）✓、B 组连带注释面六件（obs/、operations/、currency_war_config.py、cw_entry_policy、cw_decision_trace、schema.py:460-465）全 ✓、cw_investments.py:1216 carve-out ✓。附 F-7 |
| 3. 词表与不过扫符号互斥完备 | 3/4 过 | `decision_hp`/`blood_xp_full_clicks`/`blood_xp_mode` 在不过扫（hp-purge.md:49）✓；`p1_blood_floor|p2_blood_floor`、`p2_handoff_*`（裸前缀不扫、精确列名走清查件表）、`refresh_ev_budget` 均未误列进清零词表 ✓；`levelup_blood_gate_defer` 缺席 = F-6 ✗ |
| 4. λ 表血带维表述一致 | 过（字面） | hp-purge.md:24（B-12 随删、删除为零行为变化、随删并申报）与 design §3 R-6 行（cw_first_passage 保留、λ 表血带维孤儿化申报）口径一致 ✓；A-10 行（hp-purge.md:19）含 entry.py:844-846 ✓。直调复核暴露 B-12 执行面缺口 = F-1 |
| 5. 过程叙事零残留 | 1+3 处残留 | 全 6 文件 grep「对抗\|攻击\|撤稿\|两度反复\|待决约束\|1-249\|250-1961\|B4\|B5\|A3\|G2」命中 6 处：design.md:10 与 README.md:14-15 为 iteration-design.md §2.1/§4 认可的状态字段值（不计残留）；refresh-chain.md:42 = F-5 ✗；shop-buy-reform.md:5 / landing.md:43 / landing.md:57 旧行段 = F-4/F-2/F-3 ✗。其余 token（攻击、撤稿、曾两度反复、待决约束、经对抗审确认、裸 B4/B5/A3/G2）零命中 ✓（hp-purge.md:49「清查件 B-4」为带连字符的清查件条目引用，非过程叙事） |
| 6. 裁定载体登记 | 过 | `.debug/temp/2026-10-28_CW修复工作清单.md`「补充裁决」节（:19-23）登记 R-1/R-3 用户裁决通过结果与行为口径（币种通式 / 删血项机制保留）✓；卷首（:3）与节头（:19）含迭代名指针 ✓ |

## 定稿判定

发现 7 条 > 0 → **不触发定稿**。按 iteration-design.md §5.4，行段重基线属「设计正文/判据/锚修订」，须 design↔landing↔详设全量反查——本轮实证该反查未走完（F-2/F-3/F-4 同根）。修复面完成修复后建议做一轮定点复验（r9）再收敛。
