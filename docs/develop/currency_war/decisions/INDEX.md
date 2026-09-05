# ADR 归档索引

> 代码注释引用 `ADR-NNNN` 时,实体文件在本目录(docs/develop/currency_war/decisions/ 已随重构收口移档)。
> 检索:按 NNNN 排序;内容索引见 SWITCH_INVENTORY.md 任务 1 与各引用注释的语义描述。
> 两系并存:0N 系(0007-NNNN,原 ADR 主序列)与 dd 系(dd-NNN,统一迁移期决策序列)同目录并存,均一决策一文件;新增归档追加于对应分节末尾。

## 0N 系 ADR

| 文件 | 标题 |
|---|---|
| [0007-deploy-deterministic-cv-verify.md](0007-deploy-deterministic-cv-verify.md) | 0007. deploy 确定性部署(CV 占用 → 拖空槽 → CV 验源槽空) |
| [0012-observation-loop-sift-reconcile.md](0012-observation-loop-sift-reconcile.md) | 0012. 观测回路:deploy 后 SIFT 真实身份纠 tracking 漂移 |
| [0014-economy-leveling-remove-board-strong-gate.md](0014-economy-leveling-remove-board-strong-gate.md) | 0014. 经济 leveling:`_saving_for_level` 去 `_board_strong` 门(弱板也攒级) |
| [0017-research-evidence-base.md](0017-research-evidence-base.md) | 0017. 货币战争机制研究证据基(经济 / 装备 / A8 阵容) |
| [0019-max-units-dynamic-back-row.md](0019-max-units-dynamic-back-row.md) | 0019. 团队规模上限 = level + 财富宝钻/诅咒;后排槽位非固定 6 |
| [0021-phase-skeleton-faction-agnostic.md](0021-phase-skeleton-faction-agnostic.md) | 0021. 阶段节奏骨架 = 阵容无关骨架 × 阵容参数 |
| [0027-equip-owned-sift-template-detection.md](0027-equip-owned-sift-template-detection.md) | 0027. 装备 owned icon 检测用 cw_equip SIFT 模板匹配(推翻 VLM 球体误判) |
| [0044-equip-verify-avatar-slot-cv-diff.md](0044-equip-verify-avatar-slot-cv-diff.md) | 0044. equip_all 验穿用 avatar-slot CV-diff(替 count-verify) |
| [0049-below-avatar-icon-fixed-32px.md](0049-below-avatar-icon-fixed-32px.md) | 0049. below-avatar 装备 icon 固定 ~32px(98px 模板 scale 0.33) |
| [0055-shop-cards-sift-vlm-locate.md](0055-shop-cards-sift-vlm-locate.md) | 0055. 商店牌识别 OCR → SIFT(开拓者自定义名)+ 肖像区 VLM 定位 |
| [0081-static-data-auto-write-guard.md](0081-static-data-auto-write-guard.md) | 0081. 静态游戏数据 auto-write 守卫:garbage 拒 + existing 不覆盖 |
| [0091-refresh-prob-live-ocr-authoritative.md](0091-refresh-prob-live-ocr-authoritative.md) | 0091. 商店刷新概率表 REFRESH_PROB 实机 OCR 落地(推翻 placeholder) |
| [0092-acquirability-theoretical-not-observed.md](0092-acquirability-theoretical-not-observed.md) | 0092. select_comp 可得性用理论概率(refresh_prob)非观察(shop_supply) |
| [0094-strategy-merge-single-source.md](0094-strategy-merge-single-source.md) | 0094. 策略三轴重设计与 14 重复 → 净贡献合并入 14 + 删 15(单一源) |
| [0095-strategy-design-round1-av-correction.md](0095-strategy-design-round1-av-correction.md) | 0095. 策略方案定型轮 1:玩法修正(限时 AV / 掉血归因 / commit 渐进 / COMP 扩充)+ review HIGH 折进 |
| [0096-optionality-vs-commit-reconciliation.md](0096-optionality-vs-commit-reconciliation.md) | 0096. optionality/α(t) 与 commit 不矛盾 —— 管不同决策(eval vs pivot) |
| [0097-strategy-impl-wiring-nodeplan-transition-streak.md](0097-strategy-impl-wiring-nodeplan-transition-streak.md) | ADR 0097 · 策略实现接线轮(node_plan / evaluate α-blend 接法 / transition_tempo / streak 杠杆 / A4.3 牌池) |
| [0098-comp-viability-star-dimension.md](0098-comp-viability-star-dimension.md) | ADR 0098 · comp_viability 加 star 维度(star_achievement) |
| [0099-deploy-position-pref.md](0099-deploy-position-pref.md) | 0099. deploy 按角色前后台属性选排(替 0007「前排优先」) |
| [0101-equip-wear-comp-key-equips.md](0101-equip-wear-comp-key-equips.md) | 0101 — EquipAll 穿戴接 comp.key_equips 优先(替 naive wearable[0]) |
| [0103-target-matching-full-synergies.md](0103-target-matching-full-synergies.md) | 0103 — target comp 牌归属用全羁绊匹配(治本流派/阵营断裂) |
| [0109-pool-copies-canonical-27-9.md](0109-pool-copies-canonical-27-9.md) | 0109 牌池副本数定案(1/2费=27 / 3/4/5费=9;弃 V4.2 银狼档) |
| [0110-acquirability-pool-aware.md](0110-acquirability-pool-aware.md) | 0110 acquirability 牌池感知(P(≥1张)扣 1/v + held 副本消耗;review#6) |
| [0111-sell-refund-cost-based.md](0111-sell-refund-cost-based.md) | 0111 sell_refund cost-based(1星=cost / 2星=cost×3−1 / 3星=cost×9−1) |
| [0112-read-star-shape-circularity.md](0112-read-star-shape-circularity.md) | 0112 read_star 形状过滤(area100 + 圆度>0.55;治装饰误判,对新角色鲁棒) |
| [0113-read-star-triple-criteria.md](0113-read-star-triple-criteria.md) | 0113 read_star 三联判据(a>120 + circ>0.45 + aspect0.85-1.15;迭代 0112,治实战金星漏检) |
| [0114-read-star-tm-v-filter.md](0114-read-star-tm-v-filter.md) | ADR-0114:read_star 改 TM 模板匹配 + V>150 滤暗金衣服 |
| [0115-read-star-circ-relax-bench9.md](0115-read-star-circ-relax-bench9.md) | ADR-0115:read_star circ 阈值放宽 0.35→0.25(备战-9 边槽假阴) |
| [0116-read-star-thresh-back6-edge.md](0116-read-star-thresh-back6-edge.md) | ADR-0116:read_star TM thresh 0.50→0.45 解后排-6 边槽第2星漏(迭代 ADR-0114) |
| [0117-streak-direction-win-streak-break-interest.md](0117-streak-direction-win-streak-break-interest.md) | ADR-0117:streak 方向驱 plan —— 连胜破息保连胜(C 杠杆 3 winning half,R2-4b) |
| [0118-buyshopcards-supply-bail-area.md](0118-buyshopcards-supply-bail-area.md) | ADR-0118:BuyShopCards 补给 overlay bail 改用 screen_info area(治备战「返回补给阶段」假阳 → 死循环) |
| [0119-loop-supply-node-flow.md](0119-loop-supply-node-flow.md) | ADR-0119:Loop 补给节点流程 —— 点「返回补给阶段」进补给屏(替 supply 停机 hook) |
| [0120-deploy-center-drag-unified.md](0120-deploy-center-drag-unified.md) | 0120. deploy 中心拖+hold0 推翻 avatar 假设(DragCwChar 统一拖拽;5.1.9 重诊) |
| [0121-sell-refund-fee-cost-dependent.md](0121-sell-refund-fee-cost-dependent.md) | 0121. sell_refund 手续费 cost 相关(1费 exempt;2费+ star≥2 才减1) |
| [0122-battle-prep-idmark-overlay-substate.md](0122-battle-prep-idmark-overlay-substate.md) | 0122 · 备战 id_mark + overlay/子态区分(前台区域被盖;子态独立屏) |
| [0123-prep-director-observation-loop.md](0123-prep-director-observation-loop.md) | ADR-0123 备战编排从固定序列改为观察驱动决策环(PrepDirector) |
| [0124-buy-tempo-exception.md](0124-buy-tempo-exception.md) | ADR-0124 买牌 tempo 例外:未成型 commit 放行板直接增强散牌 |
| [0125-no-dead-money-duplicate-buys.md](0125-no-dead-money-duplicate-buys.md) | ADR-0125 板上同角色重复买入禁令(死钱防沉) |
| [0126-level-plan-live-calibration.md](0126-level-plan-live-calibration.md) | ADR-0126 节点等级计划 live 校准:A8 需更高人口节奏 |
| [0128-user-rhythm-batch1.md](0128-user-rhythm-batch1.md) | 0128 用户人玩节奏落地批次 1(连胜不对称/1费集星免费/boss前花完/comp停留D) |
| [0129-xp-click-model-and-level-from-xp.md](0129-xp-click-model-and-level-from-xp.md) | 0129 购买经验单击模型 + XP 反推真等级 |
| [0130-deploy-hold-scatter-p3-encounter-equip-values.md](0130-deploy-hold-scatter-p3-encounter-equip-values.md) | 0130 部署散牌留 bench(执行器对齐 planner)+ P3 避高难遭遇 + 装备价值补缺 |
| [0131-invest-economy-effect-model.md](0131-invest-economy-effect-model.md) | 0131 投资策略经济效果建模(EconomyEffect;替 REFRESH_DISCOUNT_STRATEGIES 错名单) |
| [0132-invest-card-effect-collection.md](0132-invest-card-effect-collection.md) | 0132 投资卡效果原文采集(invest_cards.jsonl;ground truth 回流) |
| [0133-strategy-full-ingest-registry-prior.md](0133-strategy-full-ingest-registry-prior.md) | 0133 投资策略全量 ingest(315)+ decide_event 注册表先验 |
| [0134-strategy-comp-match.md](0134-strategy-comp-match.md) | 0134 策略选卡 comp 匹配分(strategy_bindings 派生;2026-09-04 存量 review 删除后因活引用恢复) |
| [0136-m16-deploy-not-full-loop-fix.md](0136-m16-deploy-not-full-loop-fix.md) | 0136 M16 死循环修复(未达上限弹窗勾选缺失 + 备战席已满警告环入口感知) |
| [0137-codex-new-items-merge.md](0137-codex-new-items-merge.md) | 0137 图鉴采集数据并入注册表(6 策略 + 1 环境;doc 315 外版本新条目) |
| [0138-ocr-name-lcs-matching.md](0138-ocr-name-lcs-matching.md) | 0138 OCR 名归一用框架 LCS 相似匹配(str_utils,非全等) |
| [0142-economy-reclassify-and-eval.md](0142-economy-reclassify-and-eval.md) | ADR-0142: 投资策略效果全量评估落地 —— 9 条经济效果错装类目归位 + 评估表建立 |
| [0143-pick-value-baseline.md](0143-pick-value-baseline.md) | ADR-0143: 选卡价值基准分(pick_value)——评估表进注册表 + decide_event 消费 |
| [0144-env-pick-value.md](0144-env-pick-value.md) | ADR-0144: 环境侧选卡价值分接入(env_eval 83 条)——env 恒 0 分问题终结 |
| [0147-roll-affordability-gate.md](0147-roll-affordability-gate.md) | ADR-0147: roll 可负担性门 —— P2 满血连刷烧金终结 |
| [0148-p2-rebuild-gold-floor.md](0148-p2-rebuild-gold-floor.md) | ADR-0148: P2+ 穷金重建门限(rush_level 降档 interest_first) |
| [0150-plaza-api-invest-two-layer.md](0150-plaza-api-invest-two-layer.md) | 0150 投资策略/环境切 plaza API base × overlay 两层架构 |
| [0151-semantic-strategy-bindings.md](0151-semantic-strategy-bindings.md) | 0151 策略语义绑定逐卡手建模(↺ ADR-0134 文本扫描派生) |
| [0152-plaza-methodology-comp-refactor.md](0152-plaza-methodology-comp-refactor.md) | 0152 · comp 域 plaza 驱动重构(方法论提炼 → 模型适配) |
| [0155-horizon-dp-seam.md](0155-horizon-dp-seam.md) | ADR-0155 经济/节奏层换形:日程 DP(影子接缝落地,V1 涌现验证过) |
| [0156-joint-action-bundle-seam.md](0156-joint-action-bundle-seam.md) | ADR-0156 战术层选择机制换形:回合内联合行动束(影子接缝落地) |
| [0157-pool-belief-layer.md](0157-pool-belief-layer.md) | ADR-0157 牌池余量信念层 v0(Beta 滤波 + 缺席证据) |
| [0158-trailblazer-form-by-row.md](0158-trailblazer-form-by-row.md) | ADR-0158 开拓者形态按排归一(羁绊计算修正) |
| [0159-formation-cost-calculator.md](0159-formation-cost-calculator.md) | ADR-0159 成型成本计算器(攻略空间度量衡;17 号提案) |
| [0168-outcome-model-disposition.md](0168-outcome-model-disposition.md) | ADR-0168 02 号处置:主体被取代(superseded),salvage 校准环境落地 v0 |
| [0170-run-allocator-v0.md](0170-run-allocator-v0.md) | ADR-0170 跨局分配层 v0(RunAllocator Thompson + 必死局回收;05 号) |
| [0171-line-tribunal-v0.md](0171-line-tribunal-v0.md) | ADR-0171 战略假设审判层 v0(预注册假设+序贯证据判决;20 号) |
| [0173-boss-spend-skeleton-unlock.md](0173-boss-spend-skeleton-unlock.md) | ADR-0173: boss 前花尽三豁免(骨架买兜底 boss 场解锁) |
| [0174-p2-floor-hp-planekey-pivotfilter.md](0174-p2-floor-hp-planekey-pivotfilter.md) | ADR-0174: P2 策略专项——地板硬下限 + HP 位面键控 + pivot 位面过滤 |
| [0175-empty-board-battle-guard.md](0175-empty-board-battle-guard.md) | ADR-0175: 空板出战守卫(强度表首个消费) |
| [0176-plane-ratio-model-derived.md](0176-plane-ratio-model-derived.md) | ADR-0176: 0174 位面乘子桥拆除——保血阈值上浮改由 18 号首达模型导出 |
| [0177-mechanism-audit-first-report.md](0177-mechanism-audit-first-report.md) | ADR-0177: 机制常数核对器完整落地(redesign 23 号处置)——首份审计报告 + 实测升级 |
| [0180-decision-determinism-j0.md](0180-decision-determinism-j0.md) | ADR-0180: 决策确定性验收落地(redesign 46 号处置:J0 体检 + CI 护栏) |
| [0183-subsumption-survey-j0.md](0183-subsumption-survey-j0.md) | ADR-0183: 子承普查落地(redesign 49 号 J0):单一源缺口检出 + HP_LOSS 双源统一 + CI 护栏 |
| [0184-exhaustive-check-tier1.md](0184-exhaustive-check-tier1.md) | ADR-0184: Tier-1 穷举检查器 v0 落地(redesign 28 号处置:金零进展死锁 absence 证明) |
| [0186-censoring-stage-decompose.md](0186-censoring-stage-decompose.md) | ADR-0186: 删失感知统计层 v0 落地(redesign 48 号处置:stage 分解 + J0 首份报告) |
| [0199-difficulty-account-v0.md](0199-difficulty-account-v0.md) | ADR-0199: 难度账本与价值地图 v0 落地(redesign 36 号处置:记账恒等式+场合依赖定价) |
| [0202-effect-ledger-v0.md](0202-effect-ledger-v0.md) | ADR-0202: 既持效果台账 v0 落地(redesign 53 号处置:现金日程+机制突变+免费额度) |
| [0205-survey18-landing.md](0205-survey18-landing.md) | ADR-0205: 投资效果全量调研落地(纠错 + v2 字段 + 台账/难度路由) |
| [0208-horizon-seam-cutover.md](0208-horizon-seam-cutover.md) | ADR-0208: HORIZON_SEAM 切流执行(DP 姿态替换静态节点表) |
| [0209-dual-track-architecture.md](0209-dual-track-architecture.md) | ADR-0209: 阵容选择架构重构——双轨过渡 + 信号定型(用户六轮指导定稿) |
| [0210-docs-truth-model.md](0210-docs-truth-model.md) | 0210 文档真值模型:develop=as-built 无状态 / game/research=证据层 / 进度外置 |
| [0211-two-direction-rulings-rejected.md](0211-two-direction-rulings-rejected.md) | 0211 玩法方向裁定:优势布局钻钞 farming 与砂里淘金电表流均不采纳(用户裁定) |
| [0212-sources-archive-playbook-dissolution.md](0212-sources-archive-playbook-dissolution.md) | 0212 · 外部存档层(sources)定名与 playbook 溶解归位 |
| [0213-prepphase-observation-layer.md](0213-prepphase-observation-layer.md) | ADR-0213:PrepPhase 观测层重构——「稳定→全面识别→决策→执行」单循环 |
| [0214-quantum-portal-channel.md](0214-quantum-portal-channel.md) | ADR-0214: 量子框架为 portal 专属通道;非 portal 局期望启动率≈0(r107 审计D) |
| [0215-crop-first-default-false.md](0215-crop-first-default-false.md) | 0215 - one_dragon OCR crop_first 框架默认 True→False(全图 OCR 缓存复用) |
| [0217-framework-boot-shop-weight.md](0217-framework-boot-shop-weight.md) | ADR-0217: 过渡框架启动判定纳入商店在售半权(r105) |
| [0218-depth-delta-pool.md](0218-depth-delta-pool.md) | 0218 sim 板深条件化实机Δ池+板深语义修正(校准层真机制化) |
| [0219-scatter-fill-retraction.md](0219-scatter-fill-retraction.md) | 0219 P1 散件填充落地又撤回(bench≠上阵代理伪影) |
| [0220-deploy-cap-diamond-stacking.md](0220-deploy-cap-diamond-stacking.md) | 0220 deploy cap 合法域反转:宝钻可叠加,cap<level 才是真异常 |
| [0221-boss-window-board-faction-buy.md](0221-boss-window-board-faction-buy.md) | ADR-0221 boss 窗板面集中买与档位排序 |
| [0222-bridge-pool-v40-alignment.md](0222-bridge-pool-v40-alignment.md) | ADR-0222 过渡桥池 V4.0 口径对齐(狼狩/贝洛伯格入池;引擎阵营单一源) |
| [0223-levelup-total-cost-gate.md](0223-levelup-total-cost-gate.md) | ADR-0223 破息窗 LevelUp 总成本门 |
| [0224-buy-guard-star-weighted-copies.md](0224-buy-guard-star-weighted-copies.md) | ADR-0224 买牌守卫 copies 星级加权 |
| [0225-p1-formation-checkpoint-fence.md](0225-p1-formation-checkpoint-fence.md) | ADR-0225 P1 成型检查点与集中买配方围栏 |
| [0226-deploy-fence-bridge-derived.md](0226-deploy-fence-bridge-derived.md) | ADR-0226 deploy 围栏随桥派生集 |
| [0227-redesign-header-ruling-archive.md](0227-redesign-header-ruling-archive.md) | ADR-0227 redesign 裁定史归档(头部瘦身) |
| [0228-research-comps-layer-dissolution.md](0228-research-comps-layer-dissolution.md) | ADR-0228 撤销 research/comps 打法卡层(final_comps 十类为单一源) |
| [0229-telemetry-quality-3d-view.md](0229-telemetry-quality-3d-view.md) | ADR-0229 遥测判读三维同屏(角色星级+装备分配入 tiers 视图) |
| [0230-telemetry-gap-wiring.md](0230-telemetry-gap-wiring.md) | ADR-0230 遥测采集缺口接线(session→state 统一回写) |
| [0231-replay-harness-line-strategy.md](0231-replay-harness-line-strategy.md) | ADR-0231 回放对拍器升级(LineStrategy 忠实还原 + 分歧分桶) |
| [0232-tier-completing-deploy-first.md](0232-tier-completing-deploy-first.md) | ADR-0232 部署 tgt 序内补档优先(tier-completing deploy first) |
| [0233-sim-event-gold-deployed-proxy.md](0233-sim-event-gold-deployed-proxy.md) | ADR-0233 sim 校准层双修:事件金注入 + deployed 代理 |
| [0234-node-type-coldstart-table-fallback.md](0234-node-type-coldstart-table-fallback.md) | ADR-0234 结算 node_type 首节点冷启动兜底(开局槽序表) |
| [0235-telemetry-audit-p0-batch.md](0235-telemetry-audit-p0-batch.md) | ADR-0235 遥测审计 P0 批修复(node_type 词汇统一/槽序表写入/同轮左移锚定/abandoned 兜底) |
| [0236-telemetry-audit-p1-batch.md](0236-telemetry-audit-p1-batch.md) | ADR-0236 遥测审计 P1 批(gold 轨迹回合去重 + decisions 并列取末帧) |
| [0237-bench-full-deadlock-progress-guarantee.md](0237-bench-full-deadlock-progress-guarantee.md) | ADR-0237 腾席链死循环修复(gold 真值等待上限 + 全保护强制卖) |
| [0238-inter-step-observation-no-gate.md](0238-inter-step-observation-no-gate.md) | ADR-0238 步间观察不过稳定门(维持现状 + 升级判据) |
| [0239-settlement-node-type-authoritative.md](0239-settlement-node-type-authoritative.md) | ADR-0239 结算屏自身解析节点类型(生产链死亡的治本修复) |
| [0240-coldstart-direction-gate.md](0240-coldstart-direction-gate.md) | ADR-0240 冷启动首购方向门(pair_wants 板面空分支) |
| [0241-recipe-refresh-window-widen.md](0241-recipe-refresh-window-widen.md) | ADR-0241 配方找件刷新窗口提前(r5→r3;两窗空隙修补) |
| [0242-sim-ledger-isomorphism.md](0242-sim-ledger-isomorphism.md) | ADR-0242 sim 判读同构基建(账本/checks/快照池/CLI/seed 重放) |
| [0243-bridge-deploy-identity.md](0243-bridge-deploy-identity.md) | ADR-0243 桥期 deploy 身份:四桥映射补全 hunt3/dot_belog(r373) |
| [0244-shop-unk-stop-restore.md](0244-shop-unk-stop-restore.md) | ADR-0244 shop 未识别卡恢复停机留证(撤销 r34 降级) |
| [0245-production-checks-integration.md](0245-production-checks-integration.md) | ADR-0245 生产遥测接 checks(栈判别+检查子集适配) |
| [0247-sift-two-phase-lazy-ransac.md](0247-sift-two-phase-lazy-ransac.md) | ADR-0247: SIFT 识别两阶段惰性 RANSAC(观测层性能优化,决策语义逐位等价) |
| [0248-opening-copy-buy.md](0248-opening-copy-buy.md) | ADR-0248 开局轮同名副本放行(r383b) |
| [0249-sim-execution-layer-agent.md](0249-sim-execution-layer-agent.md) | ADR-0249 sim 执行层代理:deploy 围栏单一源(r390) |
| [0250-stall-watch-battle-grace.md](0250-stall-watch-battle-grace.md) | ADR-0250 stall watch 战斗窗口宽限(局54 哨兵误报根治) |
| [0251-deploy-fence-cap-roomy.md](0251-deploy-fence-cap-roomy.md) | ADR-0251 配方围栏富余放行:cap 紧张才拦散牌(r387) |
| [0252-opening-round-equip-hold.md](0252-opening-round-equip-hold.md) | ADR-0252 开局轮装备 hold:gen 散件攒到战斗轮再穿(r388) |
| [0253-deploy-fills-cap-check.md](0253-deploy-fills-cap-check.md) | ADR-0253 deploy_fills_cap 检查项:r387 类 bug 的 sim 常态防线(r391) |
| [0254-equip-layer-sim-agent.md](0254-equip-layer-sim-agent.md) | ADR-0254 装备层执行代理:sim 接 decide_supply+equip_allocation(r393) |
| [0255-transition-formation-metrics.md](0255-transition-formation-metrics.md) | ADR-0255 过渡阵容成型指标:引擎乐高/配方档/三人组三层(r394/r394b/r394c) |
| [0256-sellbench-income-field.md](0256-sellbench-income-field.md) | ADR-0256: SellBench.income 生产补采(sim↔生产账本卖出回金对齐,r381) |
| [0257-opening-hold-target-vacuum.md](0257-opening-hold-target-vacuum.md) | ADR-0257: 开局装备 hold 的 target 真空修正(对抗审查 R3;r388 补丁) |
| [0258-deploy-ignition-sort.md](0258-deploy-ignition-sort.md) | ADR-0258: deploy 点火增量排序(四体系判据进场位;r404-A1) |
| [0259-deploy-dedup-round-names.md](0259-deploy-dedup-round-names.md) | ADR-0259: deploy 同名去重扩到本轮已上名单(重复件占位根修;r404-A2) |
| [0260-buy-engine-seed-gate.md](0260-buy-engine-seed-gate.md) | ADR-0260: 买侧引擎件放行通道(engine_seed;A3 修复1) |
| [0261-deploy-stock-engine-diagnosis.md](0261-deploy-stock-engine-diagnosis.md) | ADR-0261: deploy 引擎件存量躺 bench 诊断——根因在 op 侧,纯函数不改(A3 修复2) |
| [0262-streak-gold-truth-table.md](0262-streak-gold-truth-table.md) | ADR-0262: streak_gold 连胜金换实测真值表(表化 + 边界锁) |
| [0263-summon-hook-overlay-guard.md](0263-summon-hook-overlay-guard.md) | ADR-0263: summon 停机钩子 区域可见性守卫(通用 overlay 遮挡判定) |
| [0264-gate-fast-confirm-overlay-baseline.md](0264-gate-fast-confirm-overlay-baseline.md) | ADR-0264: 稳定门提速——指纹快 poll 骨架 × 用户流程知识加速器(融合终裁) |
| [0265-equip-component-reserve-p1.md](0265-equip-component-reserve-p1.md) | 0265 - 装备合成组件保留(P1 不入穿戴池) |
| [0266-levelup-interest-engine-gate.md](0266-levelup-interest-engine-gate.md) | 0266 - 升级门息引擎前置(追级资格 = 息引擎已立) |
| [0267-round-buy-sell-mutex.md](0267-round-buy-sell-mutex.md) | 0267 - 同轮买卖互斥 + engine_seed 容量门(决策通道振荡 F1 根治) |
| [0268-delta-pool-starvation-guard.md](0268-delta-pool-starvation-guard.md) | 0268 Δ池防饥饿守卫 + 快照补样 + 池标定检查(批③ F1;r409) |
| [0269-prep-frame-two-stage-upper-screens.md](0269-prep-frame-two-stage-upper-screens.md) | ADR-0269: is_prep_like_frame 两段式(上层屏显式排除) |
| [0271-sim-bench-pop-on-deploy.md](0271-sim-bench-pop-on-deploy.md) | 0271 sim bench pop 语义修正:上阵即弹出(批⑦ F1;ADR-0219 第四次命中根治;r410) |
| [0272-sim-pool-no-cost-truncation.md](0272-sim-pool-no-cost-truncation.md) | 0272 sim 牌池 4/5 费去截断(批④ F1,实机已裁决;r411) |
| [0273-runs-summary-fallback.md](0273-runs-summary-fallback.md) | 0273 - runs.jsonl 局终汇总多路径兜底(批⑧ F2 断流修复) |
| [0274-boss-round-bench-free-chain.md](0274-boss-round-bench-free-chain.md) | 0274 - 腾席链三改:boss 轮禁升级 + 卖件优先 + 真缺人口/息引擎前置(口述[32]) |
| [0275-levelup-cost-flat4.md](0275-levelup-cost-flat4.md) | 0275 - level_up_cost 通道裁决:OCR 区位无错(stylized 不可检)+ 成本模型统一 flat-4 |
| [0276-sim-merge-and-session-wiring.md](0276-sim-merge-and-session-wiring.md) | 0276 sim 3合1 merge 接入 + session 结算补写(批⑩最大杠杆;批⑩ F3/F4/F5、批⑤ F4) |
| [0277-sim-boss-win-calibration.md](0277-sim-boss-win-calibration.md) | 0277 sim boss 胜分支 + win 侧校准(批⑪最大杠杆;批⑪ F1/F2 + 检查项) |
| [0279-battle-rung-delta-pool.md](0279-battle-rung-delta-pool.md) | 0279 battle Δ池按 rung 一维分桶(批⑬最大杠杆;批⑬ F1-F4/F7 + 检查项) |
| [0280-carry-bench-gate.md](0280-carry-bench-gate.md) | 0280 carry 腾位门:bench 满时降保护集卖最弱件买 carry(批⑯ F3/F4) |
| [0281-back-layout-level-model.md](0281-back-layout-level-model.md) | 0281 后排布局模型重审:7/9/10/11 档全系幻影,选档改 level 驱动 + 系统单位恒最右 |
| [0282-hp-three-layers.md](0282-hp-three-layers.md) | 0282 hp 三层:对账保旧 + 决策沿用真值 + 记录分字段 |
| [0283-sim-bench-capacity-guard.md](0283-sim-bench-capacity-guard.md) | 0283 sim bench 超容买守卫(批⑰ F6) |
| [0284-sim-shop-slot-consumption.md](0284-sim-shop-slot-consumption.md) | 0284 sim 商店槽消费语义(批㉒最大杠杆;批㉒ F1/F3/F5) |
| [0285-sim-reading-criteria-two-fixes.md](0285-sim-reading-criteria-two-fixes.md) | 0285 sim 判读口径两小修 + A/B 分辨率底(批㉑ F1/F3/F5 + 批㉒ F4 合卷) |
| [0286-sim-truth-three-forks.md](0286-sim-truth-three-forks.md) | ADR-0286: sim↔生产三活跃分叉合批(xp 真值化 + 轮岗建模 + cap 真值接线) |
| [0287-sim-deploy-after-buy.md](0287-sim-deploy-after-buy.md) | ADR-0287: sim 部署时序对齐生产序(买后部署)+ HP 上界钳制 |
| [0288-bond-fallback-channel.md](0288-bond-fallback-channel.md) | ADR-0288: [31] 凑档降级通道(买侧 + 部署侧 else 分支) |
| [0289-sim-checks-repayment.md](0289-sim-checks-repayment.md) | 0289. 检查项清偿批:29 批压测 123 条设计落地 cw_sim_checks |
| [0290-decision-framework-candidate-scoring.md](0290-decision-framework-candidate-scoring.md) | 0290 - 决策框架治本:候选生成 × 期望评分 × 预算仲裁(取代通道堆叠) |
| [0291-decision-v2-skeleton.md](0291-decision-v2-skeleton.md) | 0291 - 决策框架 v2 骨架落地(ADR-0290 四层实现 + 0/N 买入根因修复) |
| [0292-reward-delta-pool-sampling.md](0292-reward-delta-pool-sampling.md) | 0292 reward/supply Δ池采样真值化(EARLY_WIN_DELTA 摘除 reward 通道)+ 批㉗ F4 胖尾证伪 |
| [0294-red-repair-bundle.md](0294-red-repair-bundle.md) | 0294. 红项修复合卷:engine_seed 年龄豁免 + phantom_equip sim 过滤 + 工作树收编 |
| [0296-candidate-coverage-sell-synthesize.md](0296-candidate-coverage-sell-synthesize.md) | 0296. 决策框架 v2 候选生成补完:sell 通道语义对齐 + synthesize 独立通道 |
| [0298-equip-value-table-debt-clearance.md](0298-equip-value-table-debt-clearance.md) | 0298. 装备价值表数据债清偿(批㉛ F2):3 死名裁决为表残留并删除 |
| [0303-decision-v2-merge.md](0303-decision-v2-merge.md) | 0303 - 决策框架 v2 合流批(危机批常量上移 registry + copy_swap 守卫×目标件豁免) |
| [0306-delta-pool-expansion.md](0306-delta-pool-expansion.md) | 0306 - Δ池扩容批:解锁 hp 类杠杆的总闸(口径裁决+胜率外推+桶覆盖披露+换锚) |
| [0307-boss-hp0-semantics-reversal.md](0307-boss-hp0-semantics-reversal.md) | ADR-0307 boss 败局 hp==0 语义改判:违规→删失披露(批41 推翻批40) |
| [0308-node-win-rate-ladder.md](0308-node-win-rate-ladder.md) | ADR-0308: sim 回退层节点胜率换 W31 实测节点×轮次阶梯 |
| [0309-board-by-row-and-bench-equip-ledger.md](0309-board-by-row-and-bench-equip-ledger.md) | ADR-0309 契约 C6 落地:按排聚合单一源 + bench 装备 tracking 对账 |
| [0310-decision-v2-sole-carrier.md](0310-decision-v2-sole-carrier.md) | 0310 - 载体迁移:decision_v2 唯一策略载体 + 纪律族移植 + registry 双注册 |
| [0311-combination-readiness-unified.md](0311-combination-readiness-unified.md) | 0311 组合选择 readiness 统一维度(删 DOT2 特殊逻辑) |
| [0312-board-caliber-unification.md](0312-board-caliber-unification.md) | ADR-0312: 羁绊口径统一(全集+星徽装备贡献)与 Δ池桶键对齐 |
| [0313-blood-alarm-semantics-final.md](0313-blood-alarm-semantics-final.md) | ADR-0313: 掉血报警语义定稿(报警非 ALL IN 触发 / 自然窗时限 / 血边际跳窗 / 三臂战斗节点计数器) |
| [0314-carry-gate-weak-order.md](0314-carry-gate-weak-order.md) | ADR-0314: carry_gate 卖弱序定稿(absent_mergeable 判据适配 + 种子死锁豁免 + 保护集口径修正) |
| [0315-liquidity-cashout-channel.md](0315-liquidity-cashout-channel.md) | ADR-0315: 金不足变现通道(压库件「活期存款」变现凑金) |
| [0316-bench-slot-semantics.md](0316-bench-slot-semantics.md) | ADR-0316: bench 槽位语义模型(定长 9 槽,空槽留 None 不紧缩) |
| [0317-board-unique-guard-and-stale-proposal.md](0317-board-unique-guard-and-stale-proposal.md) | ADR-0317: 场上同名唯一守卫 + 提案代际校验(游戏规则级约束下沉 cw_state;C1 契约漏洞补口) |
| [0318-system-card-ontology.md](0318-system-card-ontology.md) | ADR-0318: 体系卡本体论(SystemCard 实体模型:判据/引擎/星级/吃怕字段语义) |
| [0319-evolution-intention-state-machines.md](0319-evolution-intention-state-machines.md) | ADR-0319: 阵容演进引擎与终局意向的语义定稿(evolution_step 发显式 CompTransaction / 意向锁线只写囤货) |
| [0320-privilege-unification-followup.md](0320-privilege-unification-followup.md) | ADR-0320: 特权逻辑统一化续记(泛化清除:注册表派生五处+停手裁决;ADR-0311 的落地续篇) |
| [0321-form-tiers-authority-ruling.md](0321-form-tiers-authority-ruling.md) | ADR-0321: form_tiers 下限的权威源裁决(v2 教义 vs plaza 实证) |
| [0322-equip-assign-identity-release-plan.md](0322-equip-assign-identity-release-plan.md) | ADR-0322: equip_assign 恒等约束的拆分批放开计划 |
| [0323-line-deploy-chain-fixes.md](0323-line-deploy-chain-fixes.md) | ADR-0323: 万敌锁而不投的部署链三修(演进去重 + flows 目标集 + 围栏序/跳过语义) |
| [0324-bench-capacity-double-count-fix.md](0324-bench-capacity-double-count-fix.md) | ADR-0324:bench_capacity 双重计数修复(N1) |
| [0325-s3-same-star-merge-exemption.md](0325-s3-same-star-merge-exemption.md) | ADR-0325:S3 同星豁免——合并买入的容量例外(H3 口径) |
| [0326-rejection-remediation-loopback.md](0326-rejection-remediation-loopback.md) | ADR-0326:「拒绝→补裁决」通用回连机制(层4 末段补偿趟) |
| [0327-sell-priority-key-unified.md](0327-sell-priority-key-unified.md) | ADR-0327:S5 统一卖件弱序(sell_priority_key + AD9-2-3 守卫) |
| [0328-r408-mutex-timing-registration.md](0328-r408-mutex-timing-registration.md) | ADR-0328:r408 同轮互斥时序缺口修复(登记点=动作采纳处 + 执行域对齐) |
| [0329-w62-live-wiring-batch.md](0329-w62-live-wiring-batch.md) | ADR-0329:W62 实机接线批(恢复局锁定态直接出战 + d2 卖通道生产接线 + 退出 op 投资策略屏修复) |
| [0331-exit-op-invest-strategy-stuck-mechanism-fix.md](0331-exit-op-invest-strategy-stuck-mechanism-fix.md) | ADR-0331:退出 op 投资策略屏卡点机制根修(分支顺序 + OCR lcs 收紧) |
| [0333-board-concentration.md](0333-board-concentration.md) | 0333 - 体系集中度(d2 意向批;候选层配方亲和) |
| [0334-delta-pool-boss-anchor-sensitivity.md](0334-delta-pool-boss-anchor-sensitivity.md) | 0334 - Δ池扩容:boss 桶真值锚 + sim 敏感化验证(W73) |
| [0335-runs-summary-stop-write-point.md](0335-runs-summary-stop-write-point.md) | 0335 - runs.jsonl stop 路径写端治本:收口迁 after_operation_done(W75) |
| [0336-delete-line-strategy.md](0336-delete-line-strategy.md) | 0336 - 旧策略栈删除:line_strategy + 配套模块 |
| [0338-direct-line-lock-qualification.md](0338-direct-line-lock-qualification.md) | ADR-0338: 直通终局线锁线资格门(②羁绊信号不构成直通资格) |
| [0340-merge-progress-scoring.md](0340-merge-progress-scoring.md) | ADR-0340:断买修复评分层最小件(3合1 中间进度显影 + 溢出金断买检查器) |
| [0341-p1-final-line-lock-gate.md](0341-p1-final-line-lock-gate.md) | ADR-0341: P1 锁线资格门(终局专属线的③/④证据收紧) |
| [0342-strategy-dead-early-stop.md](0342-strategy-dead-early-stop.md) | 0342 - 恢复局策略失活早停 + 失活检查项 + hoard 口径单一源(W103 三件) |
| [0343-formed-stop-discipline.md](0343-formed-stop-discipline.md) | ADR-0343:成型停手纪律([13] 停手线的显式门)+ W105 P2-4 因果判别 |
| [0344-delta-pool-pipeline.md](0344-delta-pool-pipeline.md) | 0344 - Δ池语料管线治本(局终自动再生 + 池新鲜度检查) |
| [0345-delta-pool-locks-regen-robust.md](0345-delta-pool-locks-regen-robust.md) | 0345 - reward/supply Δ池锁 regen-robust 化(W111) |
| [0346-phase-shadow-observation.md](0346-phase-shadow-observation.md) | ADR-0346:相位影子观测(经济循环总模型步①;FORM/HOARD/SPEND 派生上线,零消费) |
| [0347-switch-authority-phase-ev.md](0347-switch-authority-phase-ev.md) | ADR-0347:切授权——相位地板 + EV 授权 + [12] 门收编总账 + DP 首次接线(经济循环总模型步②a) |
| [0348-overheat-reward-battle-guard.md](0348-overheat-reward-battle-guard.md) | ADR-0348:扑满守卫——「经济过热」类环境 reward 节点按「奖励型战斗」处理(轻投入凑羁绊,禁深花保血) |
| [0349-switch-dispatch-vd-batch-caliber.md](0349-switch-dispatch-vd-batch-caliber.md) | ADR-0349:切调度——V_D 批口径 + V_level k 放大 + 三通道接线 + 追赶态退场 + refresh 附庸闸清偿(经济循环总模型步③) |
| [0350-retire-sealed-factions-scoring.md](0350-retire-sealed-factions-scoring.md) | ADR-0350:清债——评分层五家人上人改四体系 + 已封存桥删除(W124-H2) |
| [0351-sim-streak-gold-reward-node-caliber.md](0351-sim-streak-gold-reward-node-caliber.md) | 0351 sim 连胜金口径修正(奖励/补给轮不计数不发金) |
| [0352-buy-side-ev-gate-calibration.md](0352-buy-side-ev-gate-calibration.md) | ADR-0352:EV 门买侧 V/C 量级标定(组合跳变计值 + C 回档折中口径) |
| [0353-fallback-gate-structural-engines.md](0353-fallback-gate-structural-engines.md) | 0353 form_ok 兜底门结构判据(兜底局相位切换看阵容完成度) |
| [0354-levelup-gate-auth-basis-criterion.md](0354-levelup-gate-auth-basis-criterion.md) | ADR-0354: 检查器 levelup_interest_engine_gate 判据重定义(读授权依据) |
| [0355-anchor-rebuild-bab146c6.md](0355-anchor-rebuild-bab146c6.md) | 0355. sim 基线锚重建(W140:三批断链影响后换锚 bab146c6) |
| [0356-exit-gold-floor-and-streak-floor-caliber.md](0356-exit-gold-floor-and-streak-floor-caliber.md) | ADR-0356:出口金底线=P10 状态函数判定;连胜破息地板保留+口径标定挂账 |
| [0357-p1-intention-locks-transition-pair.md](0357-p1-intention-locks-transition-pair.md) | 0357 P1 意向锁定产物=过渡配方体系对(终局 comp 锁定移至 P2+) |
| [0358-owned-pool-transport-chain.md](0358-owned-pool-transport-chain.md) | ADR-0358: owned 穿戴池搬运链(装备持有面进决策快照) |
| [0359-buy-channel-lock-target-constraint.md](0359-buy-channel-lock-target-constraint.md) | 0359 买侧通道锁定目标约束(降级+末轮围栏) |
| [0360-evolve-lock-target-protection.md](0360-evolve-lock-target-protection.md) | 0360 — evolve 换血事务的锁定目标件保护 |
| [0361-p2-vd-dp-window-opportunity-cost.md](0361-p2-vd-dp-window-opportunity-cost.md) | 0361 P2 段 V_D 修法(DP 窗授权 + 机会成本口径 + 存活收益口径) |
| [0362-delta-pool-plane-key-sim-p2-segment.md](0362-delta-pool-plane-key-sim-p2-segment.md) | 0362 Δ池 plane 维键化 + sim P2 位面段(案 a 最小可用) |
| [0363-evolve-engine-lower-bound-final-freeze.md](0363-evolve-engine-lower-bound-final-freeze.md) | 0363 — evolve 换档的引擎下界守卫与末轮演进冻结(S1 型修法) |
| [0364-sim-invest-injection.md](0364-sim-invest-injection.md) | ADR-0364: sim 投资策略/环境语料注入 |
| [0365-redesign-removal-archive.md](0365-redesign-removal-archive.md) | ADR-0365: redesign.md 砍除与内容归档 |
| [0366-plane-rounds-single-source.md](0366-plane-rounds-single-source.md) | 0366 — 位面轮数单一源 nodes_of_plane(口径断层修复:决策面 per-plane 真值) |
| [0367-qlock-transition-pair-protection.md](0367-qlock-transition-pair-protection.md) | 0367 — ①资格锁定局的过渡对保护副方向 |
| [0368-dp-horizon-plane-schedule.md](0368-dp-horizon-plane-schedule.md) | 0368 — DP 视界位面槽序重排(位面日程自适应) |
| [0369-p1-pair-missing-refresh-budget.md](0369-p1-pair-missing-refresh-budget.md) | ADR-0369:P1 体系对缺件找牌预算(候选 b:pair 缺件驱动) |
| [0370-levelup-relative-account-zero-fix.md](0370-levelup-relative-account-zero-fix.md) | ADR-0370: 升级相对账零修法裁决(never-2 残差非升级授权滥用) |
| [0371-evolve-engine-completion-guard.md](0371-evolve-engine-completion-guard.md) | 0371 — evolve 引擎补完守卫(「拥有≥门槛却从未同时上场」修法) |
| [0372-p1-early-buy-gate.md](0372-p1-early-buy-gate.md) | 0372 — P1 早期新件买入门(双条件窗:缺件密度 × 息档口径) |
| [0373-sole-engine-sell-guard.md](0373-sole-engine-sell-guard.md) | 0373 — 卖侧唯一体系引擎守卫(S2 恶化谱系) |
| [0374-gate-extend-zero-fix.md](0374-gate-extend-zero-fix.md) | 0374 — 门内集扩展 + cap 体系偏好:四格 A/B 否决,零修法裁决 |
| [0375-seele-guard-scope.md](0375-seele-guard-scope.md) | 0375 — 希儿系守卫辖域补全(卖侧守卫 + 演进保护集) |
| [0376-distinct-pref-zero-fix.md](0376-distinct-pref-zero-fix.md) | 0376 — ≥20 段 distinct 新件偏好:前提证伪 + 亲和放宽 A/B 否决,零修法裁决 |
| [0377-p2-combat-calibrated-settlement.md](0377-p2-combat-calibrated-settlement.md) | 0377 — P2 段 sim 战斗存活层参数化(胜率×形态 + 分段掉血带 + 案 b 对拍锚) |
| [0379-intent-pair-misalignment-zero-fix.md](0379-intent-pair-misalignment-zero-fix.md) | 0379 — 意向谱系根修(派生对与终局成型体系错位):持有信号信息论不可早期判,零修法裁决 |
| [0380-sell-floor-exec-guard.md](0380-sell-floor-exec-guard.md) | 0380 — 卖侧下界守卫执行点补全 + CompTransaction 单位守恒修复(own_gap 演进谱系) |
| [0381-engine-completion-dedup-distinct-owned.md](0381-engine-completion-dedup-distinct-owned.md) | 0381 — 补完修法①②:deploy 列表同名去重(实 bug)+ owned 口径 distinct |
| [0382-engine-completion-graded-undeploy.md](0382-engine-completion-graded-undeploy.md) | 0382 — 补完保护集分级(136 型构造闭死修法:缺口持续门 + 分级降级换血) |
| [0383-completion-owned-onboard-attribution-rejudged.md](0383-completion-owned-onboard-attribution-rejudged.md) | 0383 — 144 归因重判:补完触发口径无 bug,零修法 + ADR-0381 不变量表述修订 |
| [0384-compensator-sell-floor-plan.md](0384-compensator-sell-floor-plan.md) | 0384 — 补偿器卖件组批量下界过滤(136 型聚合窗补偿通道闭合) |
| [0385-back-layout-cap-diff-formula.md](0385-back-layout-cap-diff-formula.md) | 0385 后排布局选档勘误:双通道对账(公式 + CV 实测;推翻 0281 level 驱动) |
| [0386-offtarget-sell-engine-fence.md](0386-offtarget-sell-engine-fence.md) | 0386 deploy 层 off-target 卖出振荡熔断(引擎/配方围栏同源禁卖) |
| [0387-equip-asset-telemetry-wear-synthesis.md](0387-equip-asset-telemetry-wear-synthesis.md) | 0387 装备资产遥测影响面(run 26 追加取证三件)+ 穿着合成对账等价豁免 |
| [0388-stop-brake-semantics.md](0388-stop-brake-semantics.md) | 0388 停机刹车语义:stop_running 后执行流不得再落地动作(跨钩子族根修) |
| [0389-deployed-row-identification-live-art.md](0389-deployed-row-identification-live-art.md) | ADR-0389:部署排识别「现场 art 才可信」+ CV 左端三值判据 |
| [0390-back-7slots-centered-layout.md](0390-back-7slots-centered-layout.md) | ADR-0390:后排 7 格几何勘误——整排居中重排(推翻「6 格右扩」登记) |
| [0391-equipment-policy-integration.md](0391-equipment-policy-integration.md) | ADR-0391:装备策略接入第一批——P14 期望模型生产化(防误合成守卫/回收去向/λ 埋点/囤缺锚点) |
| [0392-deployed-slot-semantics.md](0392-deployed-slot-semantics.md) | ADR-0392: deployed 槽位语义模型(定长 10 槽,front 0-3 / back 4-9,空槽留 None 不紧缩) |
| [0393-sim-equip-allocation-call-shape.md](0393-sim-equip-allocation-call-shape.md) | 0393 装备分配 sim 调用形态保真(plane + occupied 补齐) |
| [0394-sim-supply-two-step-semantics.md](0394-sim-supply-two-step-semantics.md) | 0394 sim 补给选卡「恒 idx0」伪影修复(生产两步语义接产) |
| [0395-read-debounce-cap-wiring.md](0395-read-debounce-cap-wiring.md) | 0395 CV/OCR 读数防抖热修:cap 通道接线域防抖读(W218) |
| [0396-stop-guard-controller-layer.md](0396-stop-guard-controller-layer.md) | 0396 停机刹车语义框架级重写:controller 层停机守卫(停机后零游戏输入) |
| [0397-briefing-boss-plane-order-fix.md](0397-briefing-boss-plane-order-fix.md) | 0397 开局局简报 boss 位面错序修复:boss 采集主通道切 CollectPlaneIntel(W219) |
| [0398-boss-node-emblem-form-fix.md](0398-boss-node-emblem-form-fix.md) | 0398 CollectPlaneIntel boss 节点定位改特征判:详情条「首领」标签验证 + 徽章态分流(W221) |
| [0399-p2-handoff-observation-phase0.md](0399-p2-handoff-observation-phase0.md) | 0399 P2 承接快照 Phase 0(观测层立起 + 档位离线标定) |
| [0400-p1-final-window-handoff-gate.md](0400-p1-final-window-handoff-gate.md) | 0400 P1 末窗承接门(设计件 08 Phase 1 落地:formed_stop 承接维 + EV 承接缺口项) |
| [0401-p2-form-star-component.md](0401-p2-form-star-component.md) | 0401 — P2 胜率模型 form 星级分量(ADR-0377 扩展:core2 因果通道补建) |
| [0402-filler-star-channel.md](0402-filler-star-channel.md) | 0402 产星通道(方案 A filler_star 期权分 + 方案 B 同名副本方向门豁免) |
| [0403-boss-hp-projection.md](0403-boss-hp-projection.md) | ADR-0403 承接门 hp 维 boss 投影(最小可验第一步) |
| [0404-delta-pool-boss-star-depth-key.md](0404-delta-pool-boss-star-depth-key.md) | ADR-0404 Δ池 boss 桶键改净星深(v10 重生成) |
| [0405-final-window-star-directed-auth.md](0405-final-window-star-directed-auth.md) | ADR-0405 末窗星级定向授权(W232 挂账 C 项落地) |
| [0406-stop-guard-manual-endpoint-local-exemption.md](0406-stop-guard-manual-endpoint-local-exemption.md) | 0406 停机守卫手动端点本地豁免:run 收口期不再清全局停机闩(W243,W241 A1b) |
| [0407-delta-pool-encounter-rung-key.md](0407-delta-pool-encounter-rung-key.md) | ADR-0407 Δ池 encounter 桶键 depth→rung(v11 重生成)+ 板深维分辨力裁决 |
| [0408-early-pace-precommit-bias.md](0408-early-pace-precommit-bias.md) | ADR-0408 假设 A:r3/r4 投资节奏前置(early_pace 评分偏置) |
| [0409-directed-refresh-budget.md](0409-directed-refresh-budget.md) | ADR-0409 M-A 定向 D 牌授权窗(W249 诊断修法:刷新维的搜索成本授权) |
| [0410-formed-stop-target-whitelist-boss-node-agnostic.md](0410-formed-stop-target-whitelist-boss-node-agnostic.md) | ADR-0410: formed_stop 目标件白名单 + boss 轮升级禁令删除([32] 口径定调) |
| [0411-handoff-flag-family-cleanup.md](0411-handoff-flag-family-cleanup.md) | ADR-0411 承接门 flag 家族清理:四通道从验证态转正式行为 |
| [0412-ma-name-chase-transition-member-extension.md](0412-ma-name-chase-transition-member-extension.md) | ADR-0412 M-A 追名判据扩展:未锁线并入当前活跃过渡组合成员名(W260/W263) |
| [0413-ma-game-cap-non-binding.md](0413-ma-game-cap-non-binding.md) | ADR-0413 M-A game_cap 非约束轴裁定:第二跳吞吐量级的真瓶颈在窗口结构而非局级封顶(W274) |
| [0414-takeover-collect-plane-intel-op.md](0414-takeover-collect-plane-intel-op.md) | ADR-0414: 接管补采独立 op(TakeoverCollectPlaneIntel)与 loop 内实采块的同源双触发 |
| [0415-sim-segment-checks.md](0415-sim-segment-checks.md) | ADR-0415: sim 段级检验形态——轮数窗口 + 段级检查表(`_SEGMENT_CHECKS`) |
| [0416-shop-merge-preview-observation.md](0416-shop-merge-preview-observation.md) | ADR-0416: 升星预览✦观测读取(ShopCard.merge_preview,评分层接线挂账) |
| [0417-obs-readchain-paddle-align-badge-priority.md](0417-obs-readchain-paddle-align-badge-priority.md) | ADR-0417: 观测读链修复——部署对齐以 paddle X 为准 + board 裁决徽标优先(W287) |
| [0418-gate-min-round-advance.md](0418-gate-min-round-advance.md) | ADR-0418 handoff_gate_min_round 前移 8→6:承接门家族授权窗加宽兑换落地(W288) |
| [0419-match-start-state-reset.md](0419-match-start-state-reset.md) | ADR-0419: 新局开始全量状态重置(残留 match 容器入口弃置) |
| [0420-merge-effect-frame-gate-cap-domain.md](0420-merge-effect-frame-gate-cap-domain.md) | 0420 star 合成特效帧态门 + cap 域外双帧一致采信(W292,W285 抽样批3 立项) |
| [0421-nameless-honor-promo-screen-exit-branch.md](0421-nameless-honor-promo-screen-exit-branch.md) | ADR-0421: 无名勋礼购买推广页建档与返回大世界退出分支(W293) |
| [0422-version-announcement-carousel-exit-branch.md](0422-version-announcement-carousel-exit-branch.md) | ADR-0422: 版本公告轮播建档 + BackToNormalWorldPlus/入口流程补退出分支(W301) |
| [0423-no-combat-process-telemetry.md](0423-no-combat-process-telemetry.md) | ADR-0423: 战斗过程细节不采集(观测面拒绝决策) |
| [0424-sim-coarse-two-state-battle-model.md](0424-sim-coarse-two-state-battle-model.md) | 0424 sim 战斗类节点切换粗参数胜负模型(两态离散 + plaza 收缩 + 验证门锚定) |
| [0425-p1-vd-benefit-calibration.md](0425-p1-vd-benefit-calibration.md) | ADR-0425:P1 段 V_D 收益侧骨架值治理(战斗数槽序表推导 + 条件掉血遥测拟合) |
| [0426-unformed-posture-release.md](0426-unformed-posture-release.md) | ADR-0426:未成型期姿态泄息通道(release)——FLIP 双谓词辖域、预算三方合并与死分支教训 |
| [0427-target-copy-press-channel.md](0427-target-copy-press-channel.md) | ADR-0427:W300 目标外同名副本判定规则(press 通道)——守卫收拢、[11] 地板裁决与评分路由悬置 |
| [0428-hp-trusted-flip-guard.md](0428-hp-trusted-flip-guard.md) | ADR-0428:hp_trusted 可信位——FLIP 假帧守卫区分「沿用真值」与「100 兜底」 |
| [0429-gate-v2-line-switch-wiring.md](0429-gate-v2-line-switch-wiring.md) | ADR-0429:C4 存活轮数门接入 v2 换线通道 |
| [0430-directed-flip-obligation-and-merge-exempt.md](0430-directed-flip-obligation-and-merge-exempt.md) | ADR-0430:FLIP 义务预算消费定向化与合成豁免完备式——W393 攻击的两处收紧 |
| [0431-hp-down-guard-battle-fact.md](0431-hp-down-guard-battle-fact.md) | ADR-0431:hp 下行守卫——「幅度 × 战斗事实」联合判据与复现确认通道 |
| [0432-recipe-fence-hard-ordering.md](0432-recipe-fence-hard-ordering.md) | ADR-0432:购买围栏硬排序——配方件存在性围栏(方向一) |
| [0433-form-break-sell-blocked.md](0433-form-break-sell-blocked.md) | ADR-0433:成型后过渡件不拆——[13] 停手线的卖/下场侧缺口径(方向二) |
| [0434-below-floor-spend-gate.md](0434-below-floor-spend-gate.md) | ADR-0434:花的时机判据——息线以下支出门与三例外(方向三) |
| [0435-gate-precollapse-retry.md](0435-gate-precollapse-retry.md) | ADR-0435:环入口 gate 12s 满超时的时序竞争修复——预收探针前置重试 |
| [0436-revoke-exit1-intent-evidence.md](0436-revoke-exit1-intent-evidence.md) | ADR-0436:撤销出口①的意图证据三条件合取——N_req 闭式替代拍死计数 |
| [0437-dup-concentration-third-copy.md](0437-dup-concentration-third-copy.md) | ADR-0437:同名牌集中度约束——差一张时散买让位(第三张硬优先) |
| [0438-merge-completion-exempt.md](0438-merge-completion-exempt.md) | ADR-0438 · 非正分门 merge 完成豁免(第三张副本 3合1 完成素材语义) |
| [0439-sim-economy-income-caliber.md](0439-sim-economy-income-caliber.md) | 0439 sim 收入口径修正(败轮节点金 + 奖励轮 base/streak 成对) |
| [0440-w370-batchc-two-state-dp-dual-source-unification.md](0440-w370-batchc-two-state-dp-dual-source-unification.md) | ADR-0440:W370 机制欠账清偿·批 C——DP 两态化 + PLANE_LOSS_SCALE 双源合一 + W375 重标定覆写 |
| [0441-boss-tax-plane2-anchor.md](0441-boss-tax-plane2-anchor.md) | ADR-0441: P2 boss 税 p75 位面锚暂不激活维持 34 + 位面锚消费点接线兑现 |
| [0442-transition-focus-carrier.md](0442-transition-focus-carrier.md) | ADR-0442 · P1 过渡收敛目标载体(transition_focus)与三层贯彻 |
| [0443-c1-directed-spend-rejected.md](0443-c1-directed-spend-rejected.md) | ADR-0443:c1_directed_spend_enabled 破息分支——概念定谳否决,永不实现 |
| [0444-c1-asset-channel-rejected.md](0444-c1-asset-channel-rejected.md) | ADR-0444:c1_asset_channel_enabled 资产臂——定谳清理,删码留档 |
| [0445-economy-cycle-reserve-model.md](0445-economy-cycle-reserve-model.md) | ADR-0445:经济循环总模型(储备制·溢余义务·通道容量) |
| [0446-pair-completion-buy-signal.md](0446-pair-completion-buy-signal.md) | ADR-0446:配对完成度买牌信号——合并 A/B 实测定谳退回(删码留档) |
| [0447-sim-economy-eventgold-recalib.md](0447-sim-economy-eventgold-recalib.md) | 0447 sim 经济校准:事件金状态分布总闸重整定 + delta 臂回退接粗模型(W493) |
| [0448-blood-budget-levelup-stop.md](0448-blood-budget-levelup-stop.md) | ADR-0448: 血预算停手·停升级线(P2 停升级 + P1 停追级)进决策层(W523) |
| [0449-difficulty-banner-two-stage-reader.md](0449-difficulty-banner-two-stage-reader.md) | ADR-0449: 备战难度旗牌读数器两级管线(W526) |
| [0450-xy-paddle-positional-parse.md](0450-xy-paddle-positional-parse.md) | ADR-0450: 备战 x/y 读数器位置感知解析 + 语义约束验证器(W529) |
| [0451-blood-budget-downgrade-refresh-stop.md](0451-blood-budget-downgrade-refresh-stop.md) | ADR-0451: 血预算停手·第二波(P1 末窗支出降格 + 搜索型刷新停付)进决策层(W532) |
| [0452-board-sift-positional-adjudication.md](0452-board-sift-positional-adjudication.md) | ADR-0452: 板面 SIFT 识别的位置感知裁决(中心归属门)与变体模板逐文件掩码 |
| [0453-fullbench-mergebuy-gate.md](0453-fullbench-mergebuy-gate.md) | 0453 满栏合成买:ADR-0283 硬守卫升级为「触发合成则允许」(W544) |
| [0454-char-detail-split-overlay-gates.md](0454-char-detail-split-overlay-gates.md) | ADR-0454: 角色详情档按形态拆分 + UPPER_SCREENS 扩容(浮窗/提示门漏) |
| [0455-refresh-streak-upscale-none-semantics.md](0455-refresh-streak-upscale-none-semantics.md) | ADR-0455: 刷新费/连胜读取器对齐放大管线 + 刷新费 None 语义 |
| [0456-refresh-fee-base-price-andon-plan-attempt.md](0456-refresh-fee-base-price-andon-plan-attempt.md) | ADR-0456: 刷新费基价模型(REFRESH_COST_BASE=2)+ 安灯三态分流(2026-09-04 存量 review 删除后因活引用恢复) |
| [0457-hp-trust-consumption-gate.md](0457-hp-trust-consumption-gate.md) | ADR-0457: hp 可信位消费门(血线谓词 fail-closed)+ hp 读链放大回退与覆盖值位同写 |
| [0458-director-v2-loop-lifecycle-six.md](0458-director-v2-loop-lifecycle-six.md) | ADR-0458: DirectorV2 并行循环落地 + 生命周期六件套计数清零时机表(阶段2批②) |
| [0459-p1-pair-target-materialization.md](0459-p1-pair-target-materialization.md) | ADR-0459: P1 配方锁帧 target 载体物化(pair_target_comp) |
| [0460-observation-wiring-disclosure-keys-run-id.md](0460-observation-wiring-disclosure-keys-run-id.md) | ADR-0460: 观测接线批——披露键进 decisions 遥测 / obs_conflicts 补 run_id / 简报行归属 |
| [0461-affix-consumption-gates.md](0461-affix-consumption-gates.md) | ADR-0461 · 词缀消费面三钩子:锁线环境判据 + 库藏生锈穿戴豁免 + opening hold 收窄 |
| [0462-phase-field-spec-entry-sequence.md](0462-phase-field-spec-entry-sequence.md) | ADR-0462: 规范入口序列「先清场、再识别、后动作」+ 备战观测逐阶段字段规格 |
| [0463-economy-obligation-posture-admission.md](0463-economy-obligation-posture-admission.md) | ADR-0463:经济循环总模型——O1 备战空位填补通道 + 存息姿态准入门 |
| [0464-batch1-equivalence-criteria-substitution.md](0464-batch1-equivalence-criteria-substitution.md) | ADR-0464:重构批 1 等价性判据替换——回放对拍退场,单帧锁 + 全量绿 + 零漂移锚重跑接管 |
| [0465-batch3-budget-takeover-dp-retirement.md](0465-batch3-budget-takeover-dp-retirement.md) | ADR-0465: 迁移批 3 预算收权——义务模型归位优化层核,确定性费用查表替换 DP 姿态供给 |
| [0466-batch4-default-stack-retirement.md](0466-batch4-default-stack-retirement.md) | ADR-0466: 迁移批 4 commit-1——default 栈退役(default_strategy 本体删除)+ 继承解体 + 执行性钩子平移自持 + strategy_id 值域收敛 |
| [0467-batch4-dual-track-readsource-committed-from.md](0467-batch4-dual-track-readsource-committed-from.md) | ADR-0467: 批 4 commit-2/3——双轨读口换 committed_from 权威派生(C7 零漂移 + C5 显式传参,实测零行为差) |
| [0468-overflow-tier-truncation.md](0468-overflow-tier-truncation.md) | ADR-0468: 溢余消费的息档边界截断+结转(tier_truncated_spend) |
| [0469-batch4-fw-startup-retirement-orphan-fields.md](0469-batch4-fw-startup-retirement-orphan-fields.md) | ADR-0469: 批 4 commit-4——framework_startup_v2 开关退役(生产链全断,删码)+ v1-only session 孤儿字段断尾 + 悬置开关验证排期落账 |
| [0470-p1-terminal-release-stoploss.md](0470-p1-terminal-release-stoploss.md) | ADR-0470: P1 血预算停付防线的终止分支(止损转支出,terminal_release) |
| [0471-sim-level-cap-decision-alignment-and-break-interest-taxonomy.md](0471-sim-level-cap-decision-alignment-and-break-interest-taxonomy.md) | ADR-0471: sim 满级升级拒付对齐与破息例外谱收编 |
| [0473-skip-fence-scope-narrowing-residual-fill.md](0473-skip-fence-scope-narrowing-residual-fill.md) | ADR-0473: skip_fence 互斥辖域收窄——轮级禁运改「通道级+显式保留集」残余补部署(F1 病理修复)+ 检查器扩窗 r2-r9 |
| [0474-death-window-allocator-v6.md](0474-death-window-allocator-v6.md) | ADR-0474: 死亡窗支出分配器 v6 落码(P_t 正式模型→decision_v2/allocator) |
| [0475-probability-calibrated-refresh-budget.md](0475-probability-calibrated-refresh-budget.md) | ADR-0475: 概率校准的刷新预算(塌缩带归零 + 有望帧分位帽) |
| [0476-channel-margin-ranking-overlay-a.md](0476-channel-margin-ranking-overlay-a.md) | ADR-0476: 通道边际排序(溢余义务帧升级/刷新优先级显式化,overlay A) |
| [0477-buylayer-takeover-strategy-v1-retirement.md](0477-buylayer-takeover-strategy-v1-retirement.md) | ADR-0477 买层接管:strategy_v1 待删桶退役,腾席判据迁 kernel 单一源 |
| [0478-segment-checker-boundary-boss-floor-overflow-tolerance.md](0478-segment-checker-boundary-boss-floor-overflow-tolerance.md) | ADR-0478: 段级检查器边界两修——[6] boss 窗地板授权豁免 + [17] 溢余容忍带 |
| [0479-production-segment-check-wiring.md](0479-production-segment-check-wiring.md) | ADR-0479 段级检查接入生产局遥测路径(P2 血降堆金检查 + 判读 CLI 接线) |
| [0480-p2-spend-authorization.md](0480-p2-spend-authorization.md) | ADR-0480: 位面 2 支出授权(W757 v2 设计落码;默认关+双钥匙开臂挂账) |
| [0481-p2-spend-auth-v31-two-channel.md](0481-p2-spend-auth-v31-two-channel.md) | ADR-0481: 位面 2 支出授权 v3.1 重挂(W762 判定②后调判据;两通道+预算带对齐+末窗收窄) |
| [0482-two-layer-authority-order.md](0482-two-layer-authority-order.md) | ADR-0482: 知识权威序改两层——口述退出权威链,策略命题以证明/实证为准 |
| [0483-p2-spend-auth-v32-net-expense.md](0483-p2-spend-auth-v32-net-expense.md) | ADR-0483: 位面 2 支出授权 v3.2(W772 判定分支 2 后出手面修正:梯级重排+净支出闸+保留金公式化) |
| [0484-p1-iface-v2-impl.md](0484-p1-iface-v2-impl.md) | ADR-0484: P1→P2 接口机制 v2 落码(W774 五项:锁线摇摆代价门/carry 装备义务/遭遇备战授权/连败金流/血线三带) |
| [0485-battle-speed-toggle-and-wait-trim.md](0485-battle-speed-toggle-and-wait-trim.md) | ADR-0485: 实机效率双杠杆——战斗倍速自动开关与固定等待压缩 |
| [0486-cw-match-archive.md](0486-cw-match-archive.md) | ADR-0486: 按局存档(match archive)——终局旁路装配单局自包含档案 |
| [0487-p1-iface-verdict-cleanup.md](0487-p1-iface-verdict-cleanup.md) | ADR-0487: P1→P2 接口机制五开关定谳清理(W793 判定②确认无效,删码留档) |
| [0488-sim-observation-hard-dependency-keys.md](0488-sim-observation-hard-dependency-keys.md) | ADR-0488: sim 观测硬依赖键补齐(bench_full_flag / board_next_tier / 分配器帧位披露) |
| [0490-r1-hp-read-fullpath-gate.md](0490-r1-hp-read-fullpath-gate.md) | ADR-0490: read_game_state 全量路径(phase=None)恢复 hp 真读——r1 备战帧 hp_readable 恒 False 的识别根因修复 |
| [0491-hp-truth-three-source-semantics.md](0491-hp-truth-three-source-semantics.md) | ADR-0491: hp 真值来源语义(真读/结算/规则)与 r1 备战行规则标注 |
| [0492-p2-spend-auth-verdict-cleanup.md](0492-p2-spend-auth-verdict-cleanup.md) | ADR-0492: 位面 2 支出授权(p2_spend_auth)定谳清理(W785 判定②,删码留档) |
| [0493-death-domain-valuation-recalibration.md](0493-death-domain-valuation-recalibration.md) | ADR-0493: 死亡域估值路径三缺陷修复(W810 审查定谳;视界真值/饱和区分度/机会成本面值重标定) |
| [0494-p1-tier-push-objective.md](0494-p1-tier-push-objective.md) | ADR-0494 · P1 档位推进目标函数(W803 实施批;缺口差分+死线+散装门+r6 预算承诺) |
| [0495-hp-nullable-state.md](0495-hp-nullable-state.md) | ADR-0495: GameState.hp None 化(无真值即 None,开局兜底 100 正式废止) |
| [0496-piece-value-phase1-weight-calibration.md](0496-piece-value-phase1-weight-calibration.md) | ADR-0496 · 件价值 Phase 1 权重标定(w_activation=1.0 / w_retention=0.0 定谳;B 分量无可行标定值,位置成本硬门挂账) |
| [0497-piece-value-bench-reserve-gate.md](0497-piece-value-bench-reserve-gate.md) | ADR-0497 · 件价值买前 bench 容量预检硬门(reserve 推导落码;ADR-0496 开臂前置件) |
| [0498-junk-first-sacrifice-synthesis.md](0498-junk-first-sacrifice-synthesis.md) | ADR-0498: 变宝为废·牺牲合成先行(装备合成排序器) |
| [0499-spend-gate-three-round-verdict.md](0499-spend-gate-three-round-verdict.md) | ADR-0499: 支出门（买侧收门）落码与三轮 A/B 终局定性 |
| [0500-dead-tag-adjudication.md](0500-dead-tag-adjudication.md) | ADR-0500 死 tag 判死清理(爆发速杀) |
| [0501-single-round-latency-batch3.md](0501-single-round-latency-batch3.md) | ADR-0501: 单局时长效率第三批——phase_round 死分支删除 + 备战决策结果缓存 + 买牌边界固定开销压缩 |
| [0502-equip-grant-priority-chain.md](0502-equip-grant-priority-chain.md) | ADR-0502: 装备合成发放辖域优先链——可行性守卫 > 承伤序 > core-first > 集中度 |
| [0503-crisis-release-arm.md](0503-crisis-release-arm.md) | ADR-0503 危机金出口臂(危机态存息 posture 降级 + release 让位例外) |
| [0504-spend-receipt-contract.md](0504-spend-receipt-contract.md) | ADR-0504 预算-回执契约(姿态授权包 + 执行回执 + 对账门) |
| [0505-entry-overlay-clear-single-source.md](0505-entry-overlay-clear-single-source.md) | ADR-0505: 入场清场清单单一源化与星徽秘典/补给改道 |
| [0506-crisis-refresh-invariant.md](0506-crisis-refresh-invariant.md) | ADR-0506: 危机帧刷新通道不变式(P36-a) |
| [0507-rb-signal-pricing-deleted.md](0507-rb-signal-pricing-deleted.md) | ADR-0507: R-B 三信号商店件定价——两轮 A/B 判负整机制删码(W947) |
| [0508-crisis-band-reserve-downgrade.md](0508-crisis-band-reserve-downgrade.md) | ADR-0508: 危机带储备线降档(P36-a′) |
| [0509-stagnation-transform-arm.md](0509-stagnation-transform-arm.md) | ADR-0509: W948 转型臂——停滞评估臂(锁线可改判语义)+ P2 入口弱占位 |
| [0510-must-die-band-opportunity-cost.md](0510-must-die-band-opportunity-cost.md) | ADR-0510 · 必死子带机会成本重定价(死亡域 I 项退役) |
| [0511-signal-layer-falsified-memory.md](0511-signal-layer-falsified-memory.md) | ADR-0511: 信号层判死记忆契约(falsified)——缓期挂账,随首个判死写入端批次落地 |
| [0512-power-model-scope-sim-only.md](0512-power-model-scope-sim-only.md) | ADR-0512: 战力模型范围——唯一消费者=sim 战斗结算层,决策层永不消费 |
| [0513-cw3-seam-fix-behavior-changes.md](0513-cw3-seam-fix-behavior-changes.md) | 0513 - cw3 接缝修复批行为变更(供给-消费接缝五点 + 多刷×段上限口径收敛) |
| [0514-andon-gold-close-unit-row-source.md](0514-andon-gold-close-unit-row-source.md) | 0514 - 安灯钩子关店金数据源改 spend_ledger 单元行(exec_fail 误停根治) |
| [0515-rung-value-retirement.md](0515-rung-value-retirement.md) | 0515 - rung_value 档位流退役(V̄_net 链因子重接地·增量 B) |
| [0516-vbar-retirement-path-ledger.md](0516-vbar-retirement-path-ledger.md) | 0516 - V̄ 链退役 + 刷新/升级决策改路径总账比较(形式二;禁胜率建模,三修正) |
| [0517-single-action-screen-op.md](0517-single-action-screen-op.md) | 0517 - 画面 op 单动作循环架构(入口观察+逐动作决策循环+终结 op;玩家十条裁定,accepted) |
| [0518-single-action-implementation.md](0518-single-action-implementation.md) | 0518 - 单动作循环实施批(ADR-0517 迁移落码:处置表/测试重锚/w614 新哨兵锚/备战投影验证阶梯) |
| [0519-empirical-scores-retirement.md](0519-empirical-scores-retirement.md) | 0519 - 组3-7 幸存经验量清账(「未证即退役」:意图族/事件面加减分族/经济干支 C 退役+B 改注+P58 骨架,accepted) |

## dd 系决策

| 文件 | 标题 |
|---|---|
| [dd-001-ab-baseline-gate.md](dd-001-ab-baseline-gate.md) | DD-001:旧决策包删除时序——A/B 过线前不得物理删除(批 1 拆 1a/1b 两段) |
| [dd-002-rotation-doubling-semantics.md](dd-002-rotation-doubling-semantics.md) | DD-002:轮岗突变语义勘误——选择后每备战阶段 100% 生效;20% 是观测频率不是机制概率 |
| [dd-003-cross-plane-node-count-defect.md](dd-003-cross-plane-node-count-defect.md) | DD-003:跨位面剩余节点数实现缺陷登记——`total_remaining_nodes` 对全部位面写死 9,L 换轨前必修 |
| [dd-004-encounter-refresh-execution-wiring.md](dd-004-encounter-refresh-execution-wiring.md) | DD-004:遭遇分支刷新执行链接线——决策建议字段长期无消费端,接线并登记触发源缺位 |
| [dd-005-buy-landing-real-empty-slot-semantics.md](dd-005-buy-landing-real-empty-slot-semantics.md) | DD-005:买牌期望态落点判据对齐「真实空槽优先」——快照过期不再误停线 |
| [dd-006-settle-read-chain-boss-win-form.md](dd-006-settle-read-chain-boss-win-form.md) | DD-006:结算读点链 boss 胜局形态修复——失败页分支抢走页1 + 填充率页2 假值 + killed 兜底误判 |
| [dd-007-plane-fallback-endpoint-discipline.md](dd-007-plane-fallback-endpoint-discipline.md) | DD-007:P2 回退先验端点纪律对称化——未揭晓位面回退统一取结构上端(9) |
| [dd-008-cost-tier-star-goal-heuristic-retired.md](dd-008-cost-tier-star-goal-heuristic-retired.md) | DD-008:费用档星目标启发式废弃——星目标决策权回归成型档显式要求 |
| [dd-009-legacy-mechanism-eviction.md](dd-009-legacy-mechanism-eviction.md) | DD-009:旧方案零引用机制整批清退——约 20 族默认关开关+影子比对残留删除 |
| [dd-010-equip-grid-two-state-fill-order-purify.md](dd-010-equip-grid-two-state-fill-order-purify.md) | DD-010:装备区识别重构——两态位移+填充序剪枝+画面守卫外移(识别器纯化) |
| [dd-011-op-anim-wait-gate-retirement.md](dd-011-op-anim-wait-gate-retirement.md) | DD-011:操作完成自等动画规范——稳定门(gate)进入退役 |
| [dd-012-delta-pool-artifact-purging-p15-refit.md](dd-012-delta-pool-artifact-purging-p15-refit.md) | DD-012:sim 校准语料伪影治理——Δ池与粗模型直方的结算瞬时 hp=0 伪读数剔除 |
| [dd-013-remove-locked-resume-enhanced.md](dd-013-remove-locked-resume-enhanced.md) | dd-013:删除 LOCKED_RESUME_ENHANCED 锁死续跑逃生机制 |
| [dd-014-blackboard-decision-interfaces.md](dd-014-blackboard-decision-interfaces.md) | dd-014:黑板模式决策接口落地——decide_prep_screen/decide_shop_screen(session 签名)+ 观察写路径收编 + match 建立前移 |
| [dd-015-equip-drag-failure-degrade.md](dd-015-equip-drag-failure-degrade.md) | DD-015:装备拖拽失败降级——失败件局内拉黑 + 跳过继续 + 后排拖点随布局档修正 |
| [dd-016-residual-fill-deploy-p24.md](dd-016-residual-fill-deploy-p24.md) | DD-016:cap 空槽补部署——P24 残余补部署支配接线到部署执行层 |
| [dd-017-p3b-orchestration-takeover.md](dd-017-p3b-orchestration-takeover.md) | DD-017:W971 P3b 编排切换——开局编排接线/overlay 分发接管/纯分发器接管备战商店/ctx 信箱退役 |
| [dd-018-shop-cost-badge-digit.md](dd-018-shop-cost-badge-digit.md) | DD-018:商店牌费用徽章数字识别——cost 信源从 roster 查表翻转为画面直读,2星/3星直出缺口闭环 |
| [dd-019-p4-battle-wait-op-expected-state.md](dd-019-p4-battle-wait-op-expected-state.md) | DD-019 · W971 P4 战斗等待 op 与期望态 infra 落地 |
| [dd-020-series-decision-contract.md](dd-020-series-decision-contract.md) | dd-020:序列决策契约——动作发射接口统一升序列/次(备战 decide_prep_screen 单动作→list,同构商店)+ fail-stop/帧稳定截断冻结 |
| [dd-021-board-count-underestimate-fix.md](dd-021-board-count-underestimate-fix.md) | DD-021: board 阵营计数系统性低估修复——计数源五级优先(徽标>XY>容错>徽标重读>身份底座) |
| [dd-022-decisions-expected-paths.md](dd-022-decisions-expected-paths.md) | DD-022 · decisions.jsonl 期望态标记(expected_paths 字段) |
| [dd-023-plane-intel-start-plane-timing.md](dd-023-plane-intel-start-plane-timing.md) | DD-023 · 位面情报采集时序修正(备战帧先定起始位面) |
| [dd-024-gate-module-retirement.md](dd-024-gate-module-retirement.md) | DD-024: gate 模块退役——cw_observation_gate 消费清零后删除(W971/P5 清尾) |
| [dd-025-frame-horizon-vgap.md](dd-025-frame-horizon-vgap.md) | DD-025:R1 刷新门 V̄ 比较项换帧级 horizon 现算(修 A)——rounds_left_est=5 常数退役出 cw4 消费链 |
| [dd-026-r2-interest-floor.md](dd-026-r2-interest-floor.md) | DD-026:R2 预算门息线 floor 落码(修 R2)——刷新门预留组装补位 P40 规范口径,b_target 零参退化退役出刷新消费位 |
| [dd-027-m7-equip-emission-gate.md](dd-027-m7-equip-emission-gate.md) | DD-027: M7 装备转移发射门——持有面谓词换变换面谓词 + 备战期装备闩 |
| [dd-029-screen-rename-merged-regen.md](dd-029-screen-rename-merged-regen.md) | DD-029: 画面改名只改分文件漏再生 merged——运行时加载源漂移致「选择伙伴」遮罩下部署死局 |
| [dd-030-no-progress-guard.md](dd-030-no-progress-guard.md) | DD-030:备战环无进展守卫——环级活性不变量 |
| [dd-031-strategy-live-probe-heartbeat.md](dd-031-strategy-live-probe-heartbeat.md) | dd-031: 策略失活早停误杀定谳与判据重写(心跳 = sid 行或载体行) |
| [dd-032-p56-t1-buy-face-wiring.md](dd-032-p56-t1-buy-face-wiring.md) | DD-032:P56 可变现息线下界 + T1 凑息卖语义重写落码(姊妹缺口收口) |
| [dd-033-economic-freeze-fix.md](dd-033-economic-freeze-fix.md) | dd-033 经济冻结型败局三病灶治本(目标空窗/姿态脱钩/弱面选线) |
| [dd-034-supply-confirm-merge-buy-crisis-level-yield.md](dd-034-supply-confirm-merge-buy-crisis-level-yield.md) | dd-034 断供供给确认加速/合并完成买入/危机带经验让位(第 7 局复盘三候选) |
| [dd-035-line-feasibility-supply-infeasible-exit.md](dd-035-line-feasibility-supply-infeasible-exit.md) | dd-035 P2 锁线可行性三维护栏 + 撤销出口③(供给不可行降级) |
| [dd-036-settlement-damage-rows-temp-collection.md](dd-036-settlement-damage-rows-temp-collection.md) | dd-036 结算屏逐角色伤害行临时采集链路(ΔV_2★ 数据面)——立撤完整周期 |
| [dd-037-deploy-launch-exec-contract-seam.md](dd-037-deploy-launch-exec-contract-seam.md) | DD-037: 部署「发射×执行」契约接缝——发射门与执行器共用单一源谓词,no-op 状态可区分 |
| [dd-038-decision-v2-package-deletion.md](dd-038-decision-v2-package-deletion.md) | DD-038: decision/ 整包删除(42 文件)+ mandate_v1 单核直替 + 注册面封闭集(用户裁定 2026-09-04,b94e9cfb;回溯建档) |
| [0520-openshop-seed-fork-retirement.md](0520-openshop-seed-fork-retirement.md) | ADR-0520: OpenShop 播种层双源分叉治本——tracked_bench 旧账退役+播种期对账接线+守卫两属消息分离(第二局双 HIT 定谳) |
| [0521-p2-locked-buy-membership.md](0521-p2-locked-buy-membership.md) | ADR-0521: P2 锁线购买口径切换——locked_comp 建立后买入 membership 单一源切换锁定采购集,锁内成员不再被拒 non_line(第四局七轮 0 买实证;策略审查 0545 打回补档) |
| [0522-w209-swap-arm-jurisdiction.md](0522-w209-swap-arm-jurisdiction.md) | ADR-0522: W209 换阵卖出义务臂+ADR-0386 辖域桥接裁决(演进层换血落地前 deploy 通道承接,§9 swap 落地让位)+P18 型命题挂账 |
| [0523-dual-ledger-guard-two-tier.md](0523-dual-ledger-guard-two-tier.md) | ADR-0523: 双账守卫两级分型——多集等价⇒WARNING+tracked重播种不炸环,真分歧维持炸出+槽位漂移/坏槽号双分键(第八局HIT定谳) |
| [0524-eval-table-ordinal-reform.md](0524-eval-table-ordinal-reform.md) | ADR-0524: 评估表体系定序改形落地(16 号稿相位 2b)——品质回落纯字典序翻转+五表声明降格(定序器/定序门/支配性优先序/planner 档位语义) |

> 豁免声明(2026-09-05,策略审查十九跳 D2):P1 消费臂落码波(14 号稿 v4.x 系列)的行为决策史以 14 号稿 §11 处置记录为单一载体,不另立批级 ADR;该豁免仅辖本波,后续波次如沿用须重声明。
| 0525 | exit3-stall-fuel-filler | 出口③ Φ_stall 过渡件垫件出口(有界成本结构改善授权) | 已实施 |
| [0526-equip-wear-release-strategy.md](0526-equip-wear-release-strategy.md) | ADR-0526: 装备穿戴策略语义落码——hold 触发权归策略侧+释放判据表五行+词缀条件优先层(18 号稿,零漂移锁面在案) | 已实施 |
| [ADR-0529-invest-strategy-entry-reprobe.md](ADR-0529-invest-strategy-entry-reprobe.md) | ADR-0529: 投资策略屏入口锚动画帧复探——单探测 round_fail 退役(20/21 局同型失败治本;首探 miss→短窗新截图复探,超窗仍 miss 才 fail),与 cw_loop N5 分发复探同族 | 已实施 |
| [0530-board-full-swap-redeploy.md](0530-board-full-swap-redeploy.md) | ADR-0530: 板满换阵补部署(M1″)——kernel swap 计划谓词单一源+发射位 seam 门已开闸(M1P_SEAM_VERIFIED=True,5edcf324)+卖出通道统一义务集排除(含 fresh 生产写点接线) | 已实施 |
| [0531-opening-narrow-tool-consume.md](0531-opening-narrow-tool-consume.md) | ADR-0531: 装备策略残余落码——opening hold 释放门收窄(O1/O2 逐件判定,支配性论证零新参数)+ 工具件消费判据面(冷启动分支炉准入+扳手闸,G1 发射位准入 fail-closed,遥测 row1/row2 分键)(21 号稿) | 已实施 |
| [0532-tool-exec-channel-open.md](0532-tool-exec-channel-open.md) | ADR-0532: 工具件消费执行通道建成开臂——RunTools 发射位(M7.5,执行位闩)+ CwOpTools 执行 op(炉死库存/特权卡栏内拖法,消耗确认通道三分支)+ TOOL_EXEC_CHANNEL_READY 开臂(拒因分键照可见) | 已实施 |
| [ADR-0533-must-spend-phase-latch-l3-reject-reasons.md](ADR-0533-must-spend-phase-latch-l3-reject-reasons.md) | ADR-0533: 必花域备战期闩(曾入域豁免保持,治「花光」义务域边界蒸发)+L3 资格拒分键落盘+prep xp 现读透传+form_score 回退源+实机遥测两件接线(三局濒死同构排查修批) | 已实施 |
| [0534-swap-transition-arm.md](0534-swap-transition-arm.md) | ADR-0534: 转型臂(M1″ swap 谓词触发域扩展)——锁线后线未成型板满帧 fenced victim 经守恒门(五体系∪护盾)+合成素材守卫+1★ 限卖逐件放行,发射⇔执行单一判定函数内聚,SWAP_TRANSITION_ARM_ENABLED 单点回滚与 seam 门切割,seam 对齐增行 15-17 | 已实施 |
