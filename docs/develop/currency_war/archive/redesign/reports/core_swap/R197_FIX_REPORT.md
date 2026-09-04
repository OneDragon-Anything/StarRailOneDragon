# R197_FIX_REPORT —— CW R197 对抗审查修复批(九症;A/B 前最后一道闸)

> 任务书=编排者 R197 修复批裁决(按 IMPL_ADV_R197.md 九症+OBS-1);登记节=design_telemetry「R197 修复批」节(含症2 裁决与预注册声明);本报告=逐症修注三元组与复验记录单一事实源。
> 文件面:src 侧 `decision/cw4/{entry,proof,bridge,shop}.py` + `sim/ab_core_swap.py`;测试 `test_cw4_mandate_v1.py` + `test_cw4_shop_line.py`;登记 `design_telemetry.md`(键节+索引 40 节+R197 节)。契约 v1/v2 正文零改动;冻结族/冻结残余 11 项/runner.py 零触碰(并行在飞让路保持)。

## 症2(高)换线权威 —— 编排者裁=方案 a 落地

- 规格:裁决文本(A/B 期换线共用基线权威;影子面发遥测不写 target_comp;判前锁声明两臂换线恒等;禁删影子机)。
- 代码:`bridge.py` 透传声明节补「两臂换线恒等」段;`proof.py` `should_switch`/`register_eviction` docstring 影子面声明(含「真实翻转不经 cw4 事件时回锁窗对真实翻转不设防,系方案 a 已裁形态,过线后批收口」);`entry.py` 换线登记位注释同款;`proof.py` `LineState.drought` 读端申报(cw4 无行为消费端,A/B 期纯遥测)。
- 预注册:`sim/ab_core_swap.py` 模块 docstring 新增预注册声明——两臂换线行为恒等(update_target 透传共用),臂间 ledger diff 归因域不含换线路径;步6 判前锁 v6 前置语句的一部分。

## 症1(高)发射序塌缩 —— 结构修三件

- 规格:IMPL_DESIGN §3.1 执行序 + §3.4「EV 只追加」(追加面=发射组织面);契约 v2 §3.2 OpenShop=截断点。
- 代码:
  1. `entry._merge_ev_before_frame_end(skeleton, ev)`:EV 卖面(SellBench 系 bench 域可续类)按依赖拓扑插到骨架**首个截断点/终点动作之前**;骨架/EV 内部序不变;无截断点 ⇒ 尾部追加(旧行为)。`emit()` 两臂分支的 EV 输出改收独立列表后经此合并。取「依赖拓扑」半边而非「整体先行」的裁量依据=最大限度保留 §3.4「义务先行」(骨架前缀 M5/M4 腾席仍先于 EV)——见登记节裁量①。
  2. 截断器尾丢弃计数:`entry.truncate_frame_stable` 与 `shop.truncate_shop_frame_stable` 任一截断路径(截断点/终点/词表外/复检失败/ClickSpheres 末批/合成触发)丢弃的尾动作逐个计数新键 `emitter_post_truncation_dropped`(键节 R197 补登,索引 40 节)——禁零计数静默。
  3. 测试真实性修(见下「测试」①)。
- 效果:换线生效帧(K 已翻 K′、新线缺口 ⇒ M2 发 OpenShop 的典型帧)的 protected_sell 发射先于 OpenShop,塌缩出口在生产主路径可达;被丢弃的尾动作(无论 EV 与否)有遥测。

## 症3(中高)商店波同槽双卖

- 规格:R196 症2 修复形态的商店侧对称(prep 侧 sold_slots/ev_conflict_dropped 同型)。
- 代码:`decide_shop_wave` 增 `sold_idxs`(bench 槽位表下标域):M4 腾席卖出登记;sell_for_interest/funding_support 提案对同 idx ⇒ 先到先得丢弃 + `ev_conflict_dropped` 计数(键复用,发射前丢弃语义与 prep 侧一致,键集零扩张)。小账:sell_for_interest 发射后 `gold += income`(与 M4 对称,买面金投影不再保守偏低)。
- 测试:`TestR197SameSlotGuard::test_same_wave_double_sell_dropped_not_failstop`——同波 M4+funding 对同填充件 idx 双卖,断言输出无重复 idx + 计数 ≥1(非 fail-stop)。

## 症4(中)复检载体 + 词表超集

- 规格:契约 §3.1 拖拽族行「名-槽一致性复检;前序动作累积静态推出,推不出即截断」;§3.3 fail-closed 附章「增补条目须回契约改版」。
- 代码:①`truncate_shop_frame_stable` 实装复检:SellBench/DeployMove/SwapDeploy 的 `bench_idx` 对生成期 bench 槽位表占用投影复检(前序卖出/拖出累积移除),SellDeployed 的 `deployed_idx` 同款(ADR-0392 置 None 不移位),`SellBench.expect`/`SellDeployed.expect` 名不符 ⇒ 截断 + `emitter_conditional_truncated` 计数(键复用);与 prep 侧 R196 复检同载体非双源(两域词表不同,复检各在各自发射器内)。②发射侧归一化:裸 `LevelUp` 进截断器前转 `LevelUpShop(cost=…, auth_basis=…)`(is-a,契约表既有行,字段保留);`_SHOP_CONTINUE` 收紧为 `(BuyCard, LevelUpShop)`,词表=契约 8 类,契约正文零改动。
- 测试:`test_drag_family_conditional_continue` 重写为判据语义锁(一致可续/同槽二次引用截断+计数/expect 不符截断/越界截断);新增 `test_levelup_normalized_to_levelupshop`(归一化+字段保留+词表锁)。

## 症5(中)A/B 公平性

- 规格:SIM_CONSUMPTION_MAP ③ 公平对拍判据;runner.simulate_core_ab 三锁先例。
- 代码:`ab_core_swap.py` 补 ①`new_core_self_pairing_gate`(mandate_v1 同工厂双臂,n≥10 缺省,ledger 逐位相等——确定性自检,与基线门对称);②`_require_single_fingerprint` 池指纹守卫挂三门(指纹集非单元素 ⇒ raise,对齐 runner.simulate_core_ab「显式失败优于静默对比」);③rng 中立升测试锁(见测试④);基线门/探针返回值补 `pool_fingerprint` 回显。harness 合流裁决仍待步6 前(载体申报保持,本批不裁)。
- 测试:④`test_rng_neutral_static_lock`(静态扫 cw4 包零 `random` 消费;运行期守卫不可行如实申报:局内 session rng 在引擎内按 seed 派生,臂侧不可达,同 seed 自配对对「消费 rng」构造性不敏感);⑤慢测 `test_new_core_self_pairing_n10`。

## 症6-9(低)

- 症6:shop funding `need = 3` 字面量删除 → `mandate.cheapest_member_cost`(MandateFrame 现读构造)注册表单一源;店价收敛逻辑保留。连带:既有 `test_sell_face_funding_support_both_arms` 金 1→0(旧 gold=1 与字面量 3 耦合;该 comp 含 1 费成员,need 注册表派生后 gold=1 已够最廉、筹资正确不触发——锁语义=「金不足」不变,锁红≠改动错的判读实例)。
- 症7:`LineState.evicted` 口径改「按到达证明 pass 的备战期帧」(实体面早退帧不步进,窗偏长方向保守,D_min 系备战期维);`drought` 读端申报=纯遥测影子面(同症2 裁决),行为接线=过线后批。
- 症8:`entry._CONDITIONAL_COMPOSITE` 死常量删除(_CONDITIONAL fallthrough 同效,分类语义不变);症8 其余两观察维持挂账未动。
- 症9:shop dominance(L359)/M6(L406 原行号)存在性门金口径改支出后投影金(`gold` 变量,同波 M4/M2/M3 支出后);实际支出安全由 check_affordable(投影金) 兜底,本改只正存在性计数键触发面口径;取实改而非注释申报的裁量=投影变量已在位零新计算(登记节裁量③);未加专项行为锁(构造 M3 支出压线确定性用例依赖 xp/cost 校准链,收益低)。

## OBS-1 复核

IMPL_DESIGN L625「R197 辖域标」grep 亲验 1 处命中,在位未动。

## 复验记录(全实测)

1. **cw4 全测试绿**:test_cw4_mandate_v1 + test_cw4_shop_line 快集(`-m "not slow"`)**97 passed, 1 deselected**(回声测试重写后经组装点 decide_from_turn 全链:换线生效帧 protected_sell 可达且先于 OpenShop;同槽冲突丢弃/异槽保留;截断丢弃计数正反锁)。
2. **三门(慢桶实测,4 passed / 27.7s)**:baseline_self_pairing n=20(零漂移)+ 新臂自配对 n=10(新增,零漂移+池指纹守卫在位)+ arm_diff n=6(相异实证,ledger_probe 可读)+ mandate 侧基线门 n=20。
3. **CW L1 全量**:`uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"` → **2370 passed, 2 skipped, 1 xpassed, 零红**(142s)。
4. **ruff**:改动 7 文件(cw4 四件+ab_core_swap+两测试)全过(autofix 三处:注解引号 UP037/非 Yoda SIM300/尾空白 W291)。

## 清洁门申报

- 冻结族零触碰、零新增度量面装置(唯一新键=截断器披露计数);冻结残余 11 项零触碰;契约 v1/v2 正文零改动;runner.py 零触碰;R196 工程裁量零翻案;IMPL_ADV_*.md 禁读纪律遵守(本批引注全部来自本轮亲读文件+行号)。
- 症8 挂账项(_lambda_quantile_armed 危险端 None 期盲区、should_switch 外部传参禁生产加注)未在本批范围,维持攻击报告挂账状态。
