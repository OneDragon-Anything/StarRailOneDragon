# ADR-0459: P1 配方锁帧 target 载体物化(pair_target_comp)

# ADR-0459: P1 配方锁帧 target 载体物化(pair_target_comp)

- **Status**: accepted → **勘误重裁中(2026-08-30,W608 对抗审计)**。审计实证:①兑换引用的「成型标尺首次点亮」系事后判据——预注册 M3 原窗=r5-r7,局22 点亮在 p1r8,窗内仅 0.65;②「⑳+2 从未点亮」被证伪——基线局 run_20260829_025301(旧代码 target_comp 全程空串)p1r9 同样 fs=1.0+formed_stop 且板面同款,form_score 为 deployed 纯观测与补丁无关;③M2「买即上车」系选择性举证——姬子·启行×2 买入后躺 bench 至 p2r7 阵亡 8+ 轮未上板。**重裁协议**:补 1-2 局带补丁配方锁局,按预注册原窗(r5-r7)判 M3,M2 改量化指标「配方件躺 bench 轮数/局」;窗内仍 0 命中且 M2 无方向 → 按预注册 revert 链撤本 commit。commit 暂留依据=107 行纯增量、未被证明有害、物化本身(M1)过硬、判定先于 commit 时序干净。审计=W608(w608_ladder_adversarial/REPORT.md)
## Context

ADR-0357 把 P1 意向锁定产物定为过渡配方体系对(`IntentionState.p1_pair`)、终局 comp 锁定移 P2+ 后,实机载体上出现断线:`session.target_comp` 唯一写端(decision_v2/strategy.update_target)只从 `ist.locked_comp` 取值,配方锁局该字段恒空 → `session.target_comp` 恒 None。既有 target 消费者(部署选人 `cw_deploy_logic.select_deployments` 的 target_factions/target_cores 注入、评分管线 `decision_v2/scoring._deploy_pipeline`、投资/补给/巨星/伙伴钩子)从此在 P1 配方锁局全盲。实机实证(局20/21/22,run_20260829_*):引擎件买入后躺 bench 至位面末、板面散脸 12-13 羁绊、r5 进窗成型 0/3(sim 基线 58-67%);decisions.target_comp 列全程空串。r100 配方机制(cw_recipe.decision_target)设计过同类载体,但只接在已退役的 default 栈;decision_v2 侧框架写入者(ADR-0442 保留休眠)默认关且非本断线前提。

## Decision

在 `decision_v2.strategy.update_target` 写端增两行:`locked_comp` 空且 `plane==1 且 ist.p1_pair` 非空时,调 `cw_intention.pair_target_comp(tuple(ist.p1_pair))` 把已锁配方对物化为伪 comp 写入 `session.target_comp`。①锁局 locked_comp 优先;P2+/空对不物化。伪 comp 口径(单一源,零新标定):factions=体系键展开(希儿系→量子同频+贝洛伯格,与 locked_faction_scope 同式);core_chars=_pair_members 全成员;form_tiers=cw_bridge_pool.BRIDGE_POOL 精确匹配(键集合相等整组取该桥 engine_bonds),无桥条目(希儿系组合)逐体系取桥池档+量子配方档;level_plan 不设(升级账退默认);name=`过渡配方·A+B`(与 ADR-0357 账本标签同形)。

## Considered Options

1. **写端单点物化(本策)**——一处写端+纯派生函数,既有消费者零改动接通;方向选择不动,非 ADR-0442 删除的 transition_focus(从零选收敛方向+三层贯彻)变体复活;不需 framework_startup 休眠基建。
2. 在各消费者(cw_deploy_logic/scoring)逐点读 ist.p1_pair——多处改、口径易漂移,否决。
3. 复用 cw_recipe.recipe_comp(旧栈载体)——其前置(dual_track_phase/transition_framework)在 decision_v2 不成立且框架启动已定谳休眠(ADR-0442),复活成本高,否决。
4. 等 W571 阶段2 DirectorV2——循环接口重建不解决值域断,且排期(⑳+2 实战复盘后)与 P1 出口质量主线错位,否决(详见 .debug/temp/currency_war/w578_target_comp_wire/DESIGN.md §3)。
5. **列车档双源分歧裁决(条件3 专项)**:列车同行档在 BRIDGE_POOL(train_dot)=2、在 cw_recipe._RECIPES=4(「数据口径主流档」)。本策取**桥池**:语义层不同——BRIDGE_POOL 是「配方对位面内配方档」(数据底=transition_combos 调研 81/41/31 篇,与伪 comp 消费面 form_progress/部署点火同语义);_RECIPES 4列车是「框架单独成型档」。二者并存有合流价值但不属本批;若后续判读确认应合流,走独立单源化批(单一源收敛,先例 ADR-0204 配置面收敛)。
6. 加默认关开关——开关生命周期门不允许:无「行为输入未就绪」前提(方向已由意向层锁死,标定全引既有单一源);A/B 以 off=worktree 冻结快照实现零漂移对照,不占 registry 开关。

## Consequences

- 行为可见面:P1 decisions.target_comp 列由 '' 变 `过渡配方·A+B`(判读增强;W570r findings「target_comp 恒空=无定向」读数按此勘误——空=未锁终局线的常态语义);投资/装备/巨星/伙伴钩子开始朝配方对定向([21] 语义正确,此前配方锁局全盲)。
- 验证:新锁 6(test_cw_p1_pair_target_wire.py,含部署传导对照锁);受影响锁集 97 passed;预注册 sim A/B 判定门槛与兑换纪律见 .debug/temp/currency_war/w578_target_comp_wire/PRE_REGISTRATION.md(判定前禁 commit)。
- 回滚=删写端两行+函数,无状态迁移。
