# required-deployed-retirement 进度

> 迭代目录 = `docs/develop/sr_od/application/currency_war/changes/2026-11-06-required-deployed-retirement/`。
> 判据单一源 = design.md；本文件只记状态与指针。

## 阶段

- [x] 阶段 1 设计：design.md 定稿（2026-11-06；论证链 = 字段排查会话五轮用户裁定）
- [x] 阶段 2 对抗审查：轮 1（外部，10 攻击点：阻断 1/应修 4/可选 5）——B1 阻断触发方案重设计（折条 → L1 两层支配编码）；轮 2（修订方案再攻击，外部通道失联、五向自完成）——A 等价域收窄 + 两处新序申报 / B 实现规格验证（_L1_SCALE 兼容/浮点安全）/ C·D 白厄两面验证通过 / E 火花线自纠错（锚 ∈ 欢愉池，虚惊）；attack.md
- [x] 阶段 3 落地（2026-11-06，本批 commit 见 git）：fp 折法源替换（named 统一表达式 + G1 白厄守卫 `if not core_faction_reqs: return 0.0`）+ 部署两层编码（`_L1_NAMED_SCALE=1e9`/`_L1_TIER_SCALE=1e8`、灭零特判删除、白厄 members 支保持 1e9 域、圈人锚层）+ 字段删除/墓碑注记（沿 equip_taboos 先例）+ import 期断言四条（`_validate_anchor_invariants`：终局锚非空/过渡锚空/锚可达/过渡 core ≤9）+ 测试六处 + 快照重生成 + EXTRACTOR_VERSION v1→v2
- [x] 阶段 4 正本（同批）：12 号篇（过渡库字段合并措辞 + 锁定语义点名件折条）、10 号稿存留表（required_deployed 退役登记，沿 equip_taboos 格式——注：该表原无此字段行，系 or-reqs-retirement 漏更，本批补登记）、24 号部署篇（分值域两层支配编码 + 段 1 圈人锚层措辞）、comp-definition.md（成型判据「AND 档 + 点名件（锚/core）」）、proofs/p87 退役指针横幅（沿 P42 先例）

## 验收凭据（design §2.7 对照）

- grep `required_deployed` 三域清零（src/tools 零活引用；命中均为墓碑/退役注记豁免）✓
- 行为对照基线（`.debug/temp/rd_baseline_*.json`，gitignored 留档）：1395 构局面（终局 21 线 × 65 板 + 过渡 10 条目 × 3 构局）——过渡条目 fp 逐位等价（③）0 漂移、希儿线 fp 逐位等价（④）0 漂移、终局缺锚帧 fp 降折 102 条（①方向 = n/(n+1)，抽值核对）、L1 两层差异面留档（②）
- 窄子集测试全绿（98 passed）：test_cw_comps（含希儿 fp 五值曲线恒过 = ④数值不变实证 + `carry_anchor == '希儿'` 结构锁）/ test_cw_transition_library（required 不变量断言删）/ test_deploy_search（`test_l1_two_layer_named_dominance`：满点名件板 ≥1e9 恒压缺点名件板 + 缺锚板保留档位层部分分 + 部分点名件过渡板 ≥5e8 压缺锚终局板 + 同缺点名件档位层先决）/ test_select_deployment（桩改 `plaza_carry='瓦尔特'` 锚承载，断言重锚 members 满编唯一）/ test_faction_migration_identity（快照整文件重生成后 7 passed，docstring 注明「required-deployed-retirement 后基线」）/ test_cw_invest_channels / test_faction_derivation_locks / test_cw_batch_stats_p1_proxy
- 下游消费域点名绿：test_intention（过渡锁定消费 fp）+ test_sell_window_launch 15 passed；sim 域 509 passed（含 test_corpus_extract/test_features，EXTRACTOR_VERSION v2 不破坏装配）
- 空羁绊线恒 0 断言（G1）：import 期 `_validate_anchor_invariants` 四条全过（21 锚非空/10 过渡锚空/锚全库可达/core m∈{1..5} ≤9）

## 遗留登记

- 全量 L1 待并行批稳定后补跑（当前 CW 域批量收集 89 errors = sim 后端装配冲突——`--co` 纯收集 3824 条零错、单文件跑零错，证为并行批在飞文件的 session 装配冲突非本批引入；沿 comp-data-row-cleanup 先例登记）
- 本批就地处置的设计未覆盖意外（小事，按设计精神）：
  1. **test_cw_batch_stats_p1_proxy 预存在红**（or-reqs-retirement 镜像漏改，非本批引入——HEAD 上即 ImportError）：`_materialized_snapshot` 引用已退役符号 `pair_target_comp`，且 skill 脚本侧已声明 p1_pair 快照现算分支恒回退镜像（配方决策层退役）。处置 = 用例改造为 locked_comp 终局线载体锁「快照现算优先」（翻正/压制两分支）+ p1_pair 帧行为锁（恒回退镜像）；快照构造器改统一表达式（= 本批 :160 行职责）。
  2. **受克恒等断言退役**：快照整文件重生成抹掉 `punished` 留档轴（生成面早已不产出），`test_migration_identity_line_static` 的受克段（直写表 vs 旧机器恒等验证）随之删除——其使命（3.2 直写表迁移验证）已完成，受克现行行为 = pick_common 直写表 + 档 0 键交集。
