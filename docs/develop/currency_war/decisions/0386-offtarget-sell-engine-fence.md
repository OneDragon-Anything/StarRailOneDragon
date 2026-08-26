# 0386 deploy 层 off-target 卖出振荡熔断(引擎/配方围栏同源禁卖)

- 状态: accepted
- 日期: 2026-08-26
- 来源: run 26(2026-08-26 12:20-12:57,P2r7 用户热键停局)崩坏局取证
  (`.debug/sr_od_mcp/main_server.log` 只读取证);同批姊妹条目
  ADR-0385(布局选档勘误,同局根因①)

## 背景(run 26 崩坏形态·根因②)

日志实锤:`sell-offtarget:藿藿(仙舟) ✓`×3 + `丹恒·饮月`×2 + `爻光`×1,
同期商店 plan 不停 `Buy(仙舟/藿藿/1)`/`Buy(仙舟/丹恒·饮月/2)`/
`Buy(仙舟/爻光/1)` = 买→卖→买循环;仙舟引擎三人组(藿藿/饮月/爻光 =
`_CORE_TRIO`)全下岗 + 列车 2→1。

机制钉死(两层目标视图分歧):

- **deploy 卖侧**:P2 定型(`plane≥2 → dual_track_phase=False`,
  `transition_framework` 清空)后 `_tgt_comp` 走 `session.target_comp`
  (终局 comp,希儿量子线,`target_factions=['减益','持续伤害','星核猎手',
  '昼之半神','盛会之星','量子同频']` 不含仙舟)→ `_sell_offtarget_deployed`
  把仙舟件判 off-target 卖出。r120 修复(decision_target 双轨单一入口)只辖
  双轨期,P2 定型期是缺口;
- **买侧**:cw_plan `_skeleton_buy_ok` 骨架纪律(仙舟∈骨架集
  `skeleton_factions()|{持续伤害,治疗}` 且 board+bench 已有存量 → 放行;
  ADR-0149 骨架例外不依赖 target)+ 演进层(`v3_intention` transition_pair
  的引擎体系对,仙舟 ∈ TRANSITION_TRAITS 引擎,ADR-0371 补完)在 P2 仍把
  仙舟件当**当前意图层正在买入的体系成员**。

**与根因①的关系(取证区分)**:卖出的拖拽全部「源槽变 ✓」成功——
off-target 误判的输入(SIFT 身份/羁绊)未被 8 格误读污染;修①不治愈②。
①放大 bench 滞留(幻影空位白拖),②造成引擎下岗(振荡卖出),独立成立。

## 决策

1. **熔断判据(纯函数 `deploy_bench.offtarget_sell_allowed`)**:off-target
   卖出候选 = 非 core ∧ 非 target 阵营交集 ∧ **非引擎/配方体系件**
   (羁绊 ∩ `_DEPLOY_FENCE` = RECIPE ∪ ENGINE,与散牌围栏同源)。
2. **依据(单一源原则)**:deploy 自己把该集合当围栏件**不许留 bench**
   (r263b/r357 `_DEPLOY_FENCE`),卖出判定不得同源反向——同模块两个相反
   判据正是振荡温床。真要换血走演进层显式 SellDeployed/CompTransaction
   (有保护集分级 ADR-0382/W202,G2 已成型引擎件恒不可动),不归 deploy 的
   机会性腾位通道(D-10)管。
3. **辖域**:仅 deploy op 执行层(`_sell_offtarget_deployed`),不触策略层
   目标源——sim 不建模该 op 通道,本修法对 sim 分布零影响(无需 A/B 锚
   重放;策略层目标统一见 Considered Options C)。

## Considered Options

- **A. deploy off-target 判定与商店/演进层同一目标源(决策层 target 单一
  入口)**:方向正确(P2 定型期买层未随定型收窄是更深一层的不一致),但是
  策略层架构件(买/演进/定型三态目标合流,涉 cw_plan/cw_evolution/cw_intention
  消费面),事故响应批不扩辖——留待意向谱系后续批;本批先落执行层熔断;
- **B. 卖出前逐件查「该件是否当前 shop plan 正在买入」**:拒绝——把执行层
  耦合到计划层瞬态(plan 每轮变,查早了不防轮间振荡),且围栏同源判据更
  简单更强(体系件无论哪轮买、无论哪个通道买都禁卖);
- **C. 扩大 target_factions 并集(把 RECIPE∪ENGINE 并进 deploy 的
  `_target_factions`)**:拒绝——该集合还进 `_is_tgt_char`(bench target
  计数/腾位理由),并集会让一切体系件都算「bench target」→ deploy-swap
  语义漂移;熔断只辖卖出面,语义最小。

## 影响

- `operations/prep/deploy_bench.py`:`offtarget_sell_allowed` 纯函数 +
  `_sell_offtarget_deployed` 集成(熔断日志 `off-target 卖出熔断(W209)`);
- 测试:新 `test_cw_w209_offtarget_sell_guard.py`(run 26 三件熔断/
  真 off-target 照卖(D-10 通道不废)/core·target 保留旧语义/保留集与
  `_DEPLOY_FENCE` 同源);
- run 27 实机验证锚点:仙舟件(引擎/配方体系成员)不再出现
  `sell-offtarget` 日志行;买→卖→买振荡消失。
