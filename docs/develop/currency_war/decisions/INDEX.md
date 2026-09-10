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
| [0525-exit3-stall-fuel-filler.md](0525-exit3-stall-fuel-filler.md) | ADR-0525:出口③ Φ_stall 过渡件垫件出口(有界成本结构改善授权) | 已实施(2026-09-05,落地审零阻断) |
| [0526-equip-wear-release-strategy.md](0526-equip-wear-release-strategy.md) | ADR-0526: 装备穿戴策略语义落码——hold 触发权归策略侧+释放判据表五行+词缀条件优先层(18 号稿,零漂移锁面在案) | 已实施 |
| [ADR-0527-box-pick-arm-emission.md](ADR-0527-box-pick-arm-emission.md) | ADR-0527:武装箱选卡臂发射位(OpenBox 假成功判据 + 臂缺位根修) | 已实施(2026-09-05,第十八局停场热修;落地审由编排者后续走) |
| [ADR-0528-must-spend-zone-yield.md](ADR-0528-must-spend-zone-yield.md) | ADR-0528:必花域内停付线让位 + 息线门整门降排序 + R1 域内残形切分线 | 已实施(裁定 2026-09-05,20 号稿 v2.1 落码批) |
| [ADR-0529-invest-strategy-entry-reprobe.md](ADR-0529-invest-strategy-entry-reprobe.md) | ADR-0529: 投资策略屏入口锚动画帧复探——单探测 round_fail 退役(20/21 局同型失败治本;首探 miss→短窗新截图复探,超窗仍 miss 才 fail),与 cw_loop N5 分发复探同族 | 已实施 |
| [0530-board-full-swap-redeploy.md](0530-board-full-swap-redeploy.md) | ADR-0530: 板满换阵补部署(M1″)——kernel swap 计划谓词单一源+发射位 seam 门已开闸(M1P_SEAM_VERIFIED=True,5edcf324)+卖出通道统一义务集排除(含 fresh 生产写点接线) | 已实施 |
| [0531-opening-narrow-tool-consume.md](0531-opening-narrow-tool-consume.md) | ADR-0531: 装备策略残余落码——opening hold 释放门收窄(O1/O2 逐件判定,支配性论证零新参数)+ 工具件消费判据面(冷启动分支炉准入+扳手闸,G1 发射位准入 fail-closed,遥测 row1/row2 分键)(21 号稿) | 已实施 |
| [0532-tool-exec-channel-open.md](0532-tool-exec-channel-open.md) | ADR-0532: 工具件消费执行通道建成开臂——RunTools 发射位(M7.5,执行位闩)+ CwOpTools 执行 op(炉死库存/特权卡栏内拖法,消耗确认通道三分支)+ TOOL_EXEC_CHANNEL_READY 开臂(拒因分键照可见) | 已实施 |
| [ADR-0533-must-spend-phase-latch-l3-reject-reasons.md](ADR-0533-must-spend-phase-latch-l3-reject-reasons.md) | ADR-0533: 必花域备战期闩(曾入域豁免保持,治「花光」义务域边界蒸发)+L3 资格拒分键落盘+prep xp 现读透传+form_score 回退源+实机遥测两件接线(三局濒死同构排查修批) | 已实施 |
| [0534-swap-transition-arm.md](0534-swap-transition-arm.md) | ADR-0534: 转型臂(M1″ swap 谓词触发域扩展)——锁线后线未成型板满帧 fenced victim 经守恒门(五体系∪护盾)+合成素材守卫+1★ 限卖逐件放行,发射⇔执行单一判定函数内聚,SWAP_TRANSITION_ARM_ENABLED 单点回滚与 seam 门切割,seam 对齐增行 15-17 | 已实施 |
| [0535-bt-disclose-replace-form-score.md](0535-bt-disclose-replace-form-score.md) | ADR-0535: B_t 替代 form_score 披露口径——决策关键帧零预测力定谳(boss 前 108/108、终局 90/90 恒 1.0 常数零方差),三方案①去封顶②engines+2★ 否决③B_t 成立(depth r=0.403 p<0.001 唯一显著代理),纯遥测不进判据+升格须过 ADR-0482 闸门 | 已实施 |
| [0536-encounter-e3-ev-criterion.md](0536-encounter-e3-ev-criterion.md) | ADR-0536: 遭遇核 E3 判据替换——EV(b)=V_r−Δλ_death·G_loss 落码 mandate_v1.decide_encounter 覆写(λ label 四态接死 fail 向选低难/刷新肢条件化非免费期权/双槽互锁开闸链 DSTAT_MAP+G_GOLD/基线核零触碰;现态恒 fail 向低难零刷新建议) | 已实施 |
| [0554-prep-exhaustion-battle-launch.md](0554-prep-exhaustion-battle-launch.md) | ADR-0554: 备战收益耗尽→出战臂——环级无进展守卫 RunDeploy 稳态 no-op 形态改判出战(备战等待零边际收益支配性论证,判据挂守卫既有计数零新参数;失败连击 3 放弃回落停机;三审整改:stale 连击 3 上限禁无界自旋) | 已实施(三审整改定稿:失败防线双限[同型连击3+总尝试6],第三轮复验零阻断 6df6ee73;注:0536→0554 跳号 18 系编号分配时序——0537~0553 已被并行批预占后回滚/未收口,编号不回收不补配) |
| [0555-equip-value-table-fill.md](0555-equip-value-table-fill.md) | ADR-0555: 装备价值表补值——策略层 key_equips 全量缺值清偿 16 名入表(批㉜ F4 两名对位锚 5/4 档+盲区 14 名)+检查披露扩全量(≥3 阈值除,第 16 名现身实证)+变体同档辖域;sim 追加件通道耦合披露挂账 | 已实施(落地审轻阻断 b00ac387 修正后放行) |
| [0556-unlocked-transition-t5-struct-layer.md](0556-unlocked-transition-t5-struct-layer.md) | ADR-0556: 未锁线转换通道 T5 纯结构判据——垫底级消费位第五触发源(P1 假现算出域+七条件触发核+cost-1 有意收窄+五触发源级内序+t3 分键族含 no_vacancy 拆键与 held 并入 fuel_ 口径申报;锚帧 g=47/23 L 实测;行为层 V_deploy 挂用户授权+效果基线补拍前置挂账) | 已实施(四轮对抗收敛+落地审阻-1 修复后放行) |
| [0557-sim-sink-launch-criteria-kernel.md](0557-sim-sink-launch-criteria-kernel.md) | ADR-0557: sim 决策下沉方案三混合——判据核 readiness_launch_decision 上收 kernel 单一源(cw_loop/engine_p1 双消费面删内联,armed 逐位等价锁)+ sim 发射帧短路决策段(金不花,消金出口族 A/B 结构性假阴性)+ 反假阴性哨兵(三形态红守卫移除即红);三审整改:sim 门收 armed 单键(admission 异常路径假阴性残留消除)+悬空出处收编 | 已实施(三审整改定稿) |
| [0558-merge-material-guard-bench-sell-channels.md](0558-merge-material-guard-bench-sell-channels.md) | ADR-0558: 合成素材拒入守卫(G-S1)——bench 四卖出通道+换线帧资格补「场上同名同星计数」维(c_excl≥1 拒入,与部署侧 merge_material_guard 同键单一源),两实机局案发对账治本;分期 A fail-closed(G-S2 无 W_2★ 标定源 PREREG 锁5 申报)+R2-5 accepted loss+P56 活期投影第五消费面申报 | 已实施(落地审两阻断修复后定稿) |
| [0559-opening-hp-prior-table.md](0559-opening-hp-prior-table.md) | ADR-0559: 开局血量初值表——遥测实证先验替代开局 hp=None(hp0_survey 133 局普查:A8/108 基础 82 零方差、开局不利 −20=62、时间刺客不改初值仅污染 1-1 读数;接对账层 reconcile_hp 开局分支,readable=False 不写 last_hp_real 真读零覆盖;非实证难度档维持 None 禁外推) | 已实施 |
| [0560-levelup-channel-budget-gate.md](0560-levelup-channel-budget-gate.md) | ADR-0560: 升级通道预算闸(P71-b 溢余段判据落码)——M3 三发射位量闸+ρ 公共源提升 criteria/refresh+必花域闸生效(要花≠花在哪)+M6 同帧挂起+posture/sim 检查器对账;推迟语义禁部分买;与 ADR-0528 闩的交互裁决在案(§5) | 已实施 |
| [0561-sim-shop-action-single-source.md](0561-sim-shop-action-single-source.md) | ADR-0561: sim 商店动作执行切 simulate 单一源——Buy/SellBench 切源(装备回收行为修正申报)+LevelUp/RefreshShop 保留面显式申报(LEVEL_CAP 冻结/免费刷 sim-only)+零漂移对拍 60 局逐位恒等+防回漂三锁(sim review §A 根因 1 消解) | 已实施 |
| [0562-0n-shop-branch-strategy-delegated.md](0562-0n-shop-branch-strategy-delegated.md) | ADR-0562: 外循环 0n 开商店分支处理改交商店访问路径——硬编码收起退役(违 ADR-0517 终结语义+无谓往返),委托 CwScreenPrep.visit_open_shop(店已开入口:入口观察→策略器决策→CloseShop 终结);hp fail-closed 不覆盖;分键 branch_shop_open_collapse 拆 hit/visit_ok/visit_fail | 已实施 |
| [0563-session-responsibility-separation-atomic-switch.md](0563-session-responsibility-separation-atomic-switch.md) | ADR-0563: session 职责分离一次性原子切换——三类状态分离(观察28/策略器52+账外9+scratch/执行16→ExecState 局容器+kernel 访问口旁表)+create_state 非 abstract 工厂+kernel 工厂注入槽(依赖矩阵锁禁 TYPE_CHECKING 边,§7.2-6 候选改落法)+退役 5 项带前置;遥测 schema 零改全读点换访问函数 | 已实施 |
| [0564-recipe-floor-lock-line-exempt.md](0564-recipe-floor-lock-line-exempt.md) | ADR-0564: 配方底线门「锁定线语境豁免」——门判定收敛 kernel 单一函数 recipe_floor_holds(+xianzhou_supply_exists 四条件谓词+档值常量上提),五处消费点全量接线(kernel/op 主循环/装配段/P24/swap),新参缺省 False 逐位同旧,遥测双写 deploy_emit_/deploy_exec_ 键族,sim 4 调用点接线(_rf 独立 try 隔离),A/B 判据 G1-G6 预注册+P1 帧不豁免占位裁决挂期限 | 已实施 |
| [0565-levelup-level-cap-single-source.md](0565-levelup-level-cap-single-source.md) | ADR-0565: 等级帽单一源(lv9_stop 收 level_max)——策略面游戏定义量第二源(LEVEL_CAP=9 假「同值」注)纠错,删常量+4 消费位注册表接线(shop×2/entry 本批,mandate 在飞文件面过渡缺省通道挂账收严),sim 注入视图零漂移,契约回显改口径,4 锁按存在性纪律改写带红证 | 已实施 |
| [0566-launch-frame-arbitrage-batch1.md](0566-launch-frame-arbitrage-batch1.md) | ADR-0566: 发射帧受限消费仲裁(金出口族出口 B 溢出段,批 1)——armed 短路帧保留消费权:确将发射路径独占插入仲裁段(armed∧浮层闸∧双锚预检∧发射核之前,I-2 位次钉死),既有评估栈全序复用+单动作预算闸(花后金位≥g*,P70 Δ息=0 辖域,花穿息线出辖),带内 fail-closed;生产/sim 判定语义单一源(kernel/cw_launch_arbitrage),哨兵升级「自由决策段零执行∧仲裁段外零消费」(红证在案),N-1 观测载体如实降格(sim 逐帧强断言+生产总量弱对账);armed 判据/发射核/守卫零改动,无开关(P70 已证) | 已实施(批 1 落码;A/B 对照读数归 gold_exit_family/batch1_ab) |
| [0567-loss-nodes-per-settlement-row.md](0567-loss-nodes-per-settlement-row.md) | ADR-0567: loss_nodes 逐结算行化(战斗腿口径,SCHEMA v8)——同轮补给+战斗掉血不再被净额抵减/整条漏记,rounds 链零变化,可信门+合成行 0 值防御,旧不变量解除与两链分叉形态声明;合成行写端洞登记不修(cw_loop),p72 F11/sim-design P72-6 口径注同步 v8 勘误指针 | 已实施 |
| [0568-wish-trial-grail-hooks-retirement.md](0568-wish-trial-grail-hooks-retirement.md) | ADR-0568: 祈愿试炼圣杯采集钩子退役——删 B1 钉屏停机/B2 被动采集恢复自动选卡实跑(r104-r116 已实跑行为的恢复,钩子期=零采样异常态);**显式接受风险=自动选卡可能选中崩盘型任务最坏输掉该局**(停机代价更大+wish_trial 遥测=智能选择主采样通道+惩罚型未采样禁写规避);shots 积压 577 帧/902MB 保留未分拣候智能选择批分拣;S2/S3/S4/S5+D1/D4 挂账在案 | 已实施 |
| [0569-c1-core-single-card-dominance-channel.md](0569-c1-core-single-card-dominance-channel.md) | ADR-0569: C1 直通核心卡支配性支(并列支配通道,dominance 邻位)——锁线态 registry 名单核心卡(希儿/银狼LV.999,谓词式唯一入选规则)1★ 全额退+L 项零损+席位放行囤入;P25 占位接管全域 4 处(占位函数/契约键/BYPASS_TABLE 行/测试 fixture 键)+对拍测试双向化(反向断言补齐带红证);数值支挂账不落码(01 §7 P25 钩子行改指);开店闩不消费;三键分账+拒因拆键 core_candidate_rejected | 已实施 |
| [0570-launch-quality-load-bearing-conjunction.md](0570-launch-quality-load-bearing-conjunction.md) | ADR-0570: 达标臂 armed 成型质量合取(B_t 通道承重结构维)——armed = 配方完备∧〔承重满额∨部署计划不可得 fail-open〕,承重判据零自由参数(comp.all_factions 视图承重计数≥槽位占用=板面零线外件),计划不可得出口=has_deployable 判空单一源严格子集方向防守卫停摆;原候选 2★ 数/装备覆盖重校作废(00 §1+P62),P63 只作方向锚禁作判据资格,待标定项显式(推迟行为观测/视图偏差面);停手链/镜像写端/仲裁段零改申报 | 已实施 |
| [0571-t88-dataflow-relink-r1-qualified-set-and-budget-disclosure.md](0571-t88-dataflow-relink-r1-qualified-set-and-budget-disclosure.md) | ADR-0571: 决策环数据流断链修复(双缺陷)——R1 合格集 inf 污染根修(任一不可追成员错判全空→剔除后合格集语义,实机 0 刷店定谳+假说推翻)+ W611 预算投影遥测写点(assembly 键戳轮界/执行回执位 spent 只计刷新宁窄勿虚)+ 装配纪律披露面豁免裁决(四字段+键戳禁决策消费,grep 守卫锁)+ F5 reason 并入键戳清零 + must_spend 值域扩;5 锁红证在案,存量锁 2 例重推,L3/混合峰锁语义勘误随批 | 已实施 |
| [0572-p74-locked-line-reachability-gate.md](0572-p74-locked-line-reachability-gate.md) | ADR-0572: 锁线不可达窗口线外激活件可达性门(P74 命题草案 v3,再审通过候落码)——门=E_rounds 三态(kernel 逐字单一源:关/弱开期望超窗/强开当前等级缺口费用档字面零);强域=强开窗+e0→1 激活件+零成本合取(1★全额退/loss_exact==0/席位/帧级不置换/非C1)⟹除席位+未售回角+锁线延迟≤1帧(可回收机制论证,N1)外弱支配;e1→2+ 恒禁买+弱域 fail-closed 占位(01 §7 P74 行在册,owner/期限/回炉认领);断供型=门测量盲区划出(病灶帧行为零改变如实申报,修复载体指认=drought 姊妹位,衔接换线评估/生存模式,N2);落码前置=strong_open 开火性计数(0 命中→空集命题申报);v2 方案审 12 项+再审 N1/N2 收敛(报告=t90_reachability_gate/方案审.md,复算=t90_recalc.py) | 已立项(命题草案 v3 再审通过候落码;零代码) |
| [0573-m2-stall-segment-cache-and-event-telemetry.md](0573-m2-stall-segment-cache-and-event-telemetry.md) | ADR-0573: M2 停摆续段缓存与停摆计数事件粒度(T-82 必花臂重试风暴治本)——腾席无候选结论的输入不变续段跳过扫描(单槽 token+段序号+域白名单,φ 字典废除,伪命中承重=段标识比较非读清);m2 两事件键帧粒度→事件粒度+m2_stall_cache_hit/rederive/repeat_frame 观测对(量级骤降≠风暴消失判读协议);merge_material_guard_blocked 零变化申报(P56 投影位正交承载,防伪问题重提);T1-T7 锁+双探针红证+同池成对 A/B 逐位恒等(hit=90) | 已实施 |
| [0574-entry-chain-jade-detail-popup-guard.md](0574-entry-chain-jade-detail-popup-guard.md) | ADR-0574: 入口链星琼详情弹窗守卫(双锚 AND+X 关闭,模块级共享助手同构列车补给先例,4 挂点)+交替循环上界闭合(列车补给助手 round_wait→round_retry,框架 WAIT 归零语义实证)+白名单补 3 屏防误路由;活体验收:死局现场 20.4s 具名 FAIL(原 134s 无名超时)+S2 采样支持领取目标修正挂账 | 已实施 |
| [0575-ep-dominance-gate-closed-frame-e01.md](0575-ep-dominance-gate-closed-frame-e01.md) | ADR-0575: 锁线门关帧线外激活租约买(P75 ε-支配第三命题草案;ADR-0572 v3 §5 独立候选登记的立项件)——门关域(0<E_rounds≤R_rem,kernel 逐字;E=0 完成态出辖)线外 e0→1 激活件在租约合取(1★全额退/loss_exact==0 全视界/店内无锁线缺件严格版/席位可容/非C1/非合并素材/带内出辖危机[位面覆盖表钉死]/非弹药效果载体,12 原子)下买弱支配禁买,ε=租约成本流六项闭集(买帧息损恒等 0+租金≤1金/帧+锁线延迟≤1 备战轮+席位 1 槽+末角≤c_x+租约冻结分支申报),核心=可回收机制论证(N1 零件:funding_support_sell 降序回收+T3 保护登记同载体+凑息回拉绝对跳过=自旋免疫);买入=租金为零的免费退款期权(行权归部署域,散牌围栏放行未核);与 0572 按 e_rounds 三态+完成态出辖互斥(强开=P74/关=本件/弱开=共同 fail-closed/E=0=出辖分键),双计数开火性联动+判读规则五件(strong_open_seen/hit 预期 0/lease_admitted 预期>0);drought 姊妹位(v3 首选载体)正交并行不互辖;01 §7 P75 钩子行已登记 | 已立项(命题草案 v2——T-103 方案审成立候落码,1 再审前置+4 中+6 低随批收敛候再审;零代码) |
| [0576-p72-full-band-budget-gate-landing.md](0576-p72-full-band-budget-gate-landing.md) | ADR-0576: P72 全段预算闸落码(升级支出量闸全段化+检查器三处对齐)——闸换 P72 (3a) 强读式(τ=interest 单一源直消费,删 g≤g* 空过分支=签名 A 真洞,溢余段逐字退化零漂移)+ALL IN 豁免支(plane_last_battle 同谓词同帧,闸签名增 session 四调用位同步)+支A 兑现链放行(schedule_upgrade ①臂同步锚对第三消费位);P39 接缝处置=承担项换位:支B(ΔV_band 数值完备账)+支A②(has_deployable 接线)挂账不落码(P39 禁令,fail-closed 只收窄,owner+期限入 01 §7),全段放行域由 (3a)∪支A 承载;检查器三处对齐(g* 息帽单一源禁读 state.cap/决策帧金逐击重放/ρ 过渡配方同源解析+ALL IN 镜像位面长 rows 现推);契约锚更新;ci_smoke 复绿验收线+既有锁重推记录 | 已实施(commit 候编排者统一门) |
| [0577-t100-hp-event-model-v9.md](0577-t100-hp-event-model-v9.md) | ADR-0577: T-100 遥测数据病统一件(SCHEMA v9)——hp 真值链事件模型落地:hp_pay 执行回执两通道逐击采集(mode 注册表派生+真值对账 defect+grep 守卫禁决策消费)+段界重锚(resume 帧锚两链,重锚差显影不进 loss_nodes)+合成行一律退出步进链(先验「陈旧直到证伪」,182456 取证链鬼值定谳)+终局腿(runs.final_hp=0 兜底)+ts 三边界;025608 重装配 −43→−19/死亡条目 −1 回落产出,182456 保持 −19 鬼值 −33 不再捏造,v8 T1/T2 锁按存在性纪律重推(−33→−19),死字段 effects_from_strategies/xp_click_hp_cost 随批清退 | 已实施(commit 候编排者统一门) |
| [0578-t99-blood-economy-avoid-and-xp-gate.md](0578-t99-blood-economy-avoid-and-xp-gate.md) | ADR-0578: T-99 血本位两件落地(选择层 [40]① 回避 + 执行通道 [40]② 血闸)——decide_event 候选排除三态触发序(L1 可入选非血集/L2 blood-forced/L3 全禁退化零漂移,reason 锚 +blood-avoided/blood-forced)+ is_blood_economy 注册表派生谓词(族={奋斗协议,不等价交换},名字陷阱与补偿型字段反向钉死)+ resolve_strategy_canonical 候选级解析(N2 挂点,env 名 ADR-0144b 同款守卫)+ blood_xp_gate 支付能力闸(裁定字面全量口径 ⌈need/4⌉×6,N1 拍板,满级分支在公式本体,hp 不可信 fail-closed)+ prep 批入口闸与逐击地板/过冲 fail-closed(实付上界=授权血成本,24→72 过冲结构性消灭)+ cw4 三消费位串联(拒因分键独立);N5/R2 解锁包件①辖域收窄(lv≥5);R4 授权书括号注勘误挂账;T1-T10+红证在案 | 已实施(commit 候编排者统一门) |
| [0579-deep-replay-telemetry-three-gaps.md](0579-deep-replay-telemetry-three-gaps.md) | ADR-0579: 深度复盘遥测三缺口(用户需求「每次画面op调用的观察数据和决策动作」)——①candidate_scores 供数恢复(孤儿缓存根因=两次重构删光生产者;写点=flow.update_target 重入守卫体内逐候选 line_completion_feasibility;字段改名 _telemetry_ 前缀自带隔离,守卫=命中点计数锁;轮入口快照时序申报)②op_journal.jsonl kind=action 逐动作执行回执行(apply_action_outcome 唯一写点,expected_delta=全量展平叶级 diff 零漏报,400B 行帽)③kind=op 非决策 op enter/exit 成对行(位面过渡/战斗等待已接线,孤儿行容缺);禁入决策输入 grep 守卫扩族+每局 500 行软上限+独立流体积纪律;语义张力声明(C7:v1/v2 时代为选线器决策输入,今日恢复供数+禁消费=反转,未来合法消费须先撤守卫) | 已实施(commit 候编排者统一门) |
| [0580-t115-early-economy-discipline-four-rules.md](0580-t115-early-economy-discipline-four-rules.md) | ADR-0580: T-115 早期经济纪律四规则——①奖励帧升级抑制(kernel/cw_reward_node 谓词单一源,四消费位=shop M3 臂前/shop 必花域变体/mandate M3 触发块/entry posture 授权链首位,分键 reward_node_defer 族,扑满守卫=PLAZA_PORTALS 派生环境名单,v3_piggy_reward 死字段复活)②凑息/压库二选一(裁定 409 禁死囤:(a) prep 接线复用 sell_for_interest 单一源判据零改,(b) 死金地板压库买入奖励帧辖,双臂互斥+卖出资格集排除 Z1=义务集∪静态持有两集∪动态登记,动态集锁线定型清空 F1;funding_support_sell 有意不扩 F2)③核心卡恒买(裁定 410,C1 前件扩展+身份分层 helper,未锁线放行席/金硬闸,auth_basis :unlocked 可辨)④转线前瞻放行(裁定 408②,TRANSITION_PACK carry/partial 单一源,未定型期辖,1★ 硬闸,拒因键 transition_component D7 键序);[16]② sim 检查器五处豁免对齐(segments×2/ledger/ADR-0560 逐处处置,收编口径=ADR-0471 节点无关+授权通道,supply 侧随仲裁①显影退役);证据链如实(用户审阅在先,旧复盘重判在后) | 已实施(commit 候编排者统一门) |
| [0581-start-match-code-hash-gate.md](0581-start-match-code-hash-gate.md) | ADR-0581: 起局前置码哈希结构闸(T-106 混合码事故的结构防线)——sys.modules 已加载码面近似×工作树 vs HEAD 逐文件哈希(CRLF 归一+LC_ALL=C)×fail-closed,三态清单拒起局;覆盖边界如实申报(起局时刻 ≈43% 包文件已加载,延迟模块不在场=纪律防线非完备机制,扩「包文件树 vs HEAD」候后续批);Δ池豁免锚定完整相对路径+指纹校验另行看守;code_hash_gate 缺省开+save 持久化 | 已实施(commit 候编排者统一门) |
| [0582-delta-pool-synthetic-supply-pairing-filter.md](0582-delta-pool-synthetic-supply-pairing-filter.md) | ADR-0582: T-118 Δ池生成器治理——合成行/低可信行退出 hp 差分配对(共享配对件 pool.pair_outcome_rows_to_pool 单件同源,build_pool/_pool_from_replay 双池接线保指纹收敛判据)+ conf 门死亡腿账如实申报(101 行/约 −75 对)+ battle rung 真值锚随批重推(BATTLE_RUNG_TRUTH −11.5/−6.3→−9.73/−3.24,含毒语料产物重推非跟绿)+ 镜像律锁落 fixture 层快照只许缺席断言;supply P1 128→1/P2 47→0 域消失,ADR-0292 红家底与 smoke 门转绿,指纹 04d9cd7a→a0722904;邻接差分残余弱点/+2 回退幻影/n300 旧锚不可比登记不修 | 已实施(commit 候编排者统一门) |
| [0583-strategy-contract-reshape-direction-internalization.md](0583-strategy-contract-reshape-direction-internalization.md) | ADR-0583: 策略契约重塑——CwStrategy 去策略专属语义(方向节拍内化 + 生命周期收编)——ABC 重塑为抽象 12(冷建 1+备战/商店/pick 11)+非 abstract 工厂 create_state=保留总成员 13(独特面 20 口径修正),删 update_target/on_match_start/on_round_end/on_match_end/decide_prep_action/decide_shop_screen;方向重估内化 _refresh_direction(键守卫贵段每 game-round 恰一次+便宜视图段),触发=黑板帧代次标注 full/view/none(prep/shop_frame_class 具名写点,读后即清,D6 策略器零新鲜度宣告),finalize 买后 _post 暂存 view 帧 pick 入口消费(Z1 逐位同源);生命周期收编 create_session 唯一冷建口(FORM 迁入)+on_round_end 拆两半(观察半 battle_wait 即时直写 _write_settlement_observation/策略半 pending_round_outcomes 惰性 drain 处理即清);行为收敛显式申报=方向驱动输入 hp 门统一 pre→post gated(编排者裁决修法②,治 r68 同门病灶族,候选评分遥测同步移门,sim 结构性免疫由 L7 门锁承载);无前提对抗双审零阻断,7 新锁+18 桩迁移,实施批新发现达标臂暂存帧窗口经编排者裁决并入收敛族申报(§5.5 终文本) | 已实施(commit 候编排者统一门) |
| [0584-progression-screen-ops-empty-decision-form.md](0584-progression-screen-ops-empty-decision-form.md) | ADR-0584: 推进型画面 op 化(T-121,用户架构裁定 2026-09-07)——纯推进画面(无选择面∧无投影账)一律立独立 op,形态=空决策(入口观察+单次推进+交回;零策略器问询/零期望态/零决策行;新 op 单尝试重试预算归外循环;基类 _progression_base,A 族 10 op 新立);dispatch 包装 _dispatch_screen_op=外循环唯一新增结构(留证帧+op_journal enter/exit+结果映射,on_result 调用点邻接闭包承载分支守卫钩子,0n 元组适配/0j·3c 链形透传,推荐面 33 调用点全接);遥测归属对齐=op 调用流全分支统一落(0p/0r/0s 补行,0n op='商店访问'行=S11 对齐关键行),心跳恰三载体行不变(N1 计数修正),S11 消灭=双载体并存(op 行直读 11+显式开店 OpenShop 决策行段 3,复盘口径 14;现行 match-review 0n 错标纠正归编者后补);三处硬 Point 坐标 area 化(中心=原 Point 落盘实测,实机帧对拍腿归验证局);决策帧挂点锁改包装形(N2)+三处接线烟雾锁改写+journal 基数重测记录与触顶退化留档(软上限已由用户裁定删除另批) | 已实施(主仓 8c746f79+7fca8245 含 §5 三载体扩展;联合快速层终验候批 1 落地) |
| [0585-sell-arbitration-single-source.md](0585-sell-arbitration-single-source.md) | ADR-0585: 卖出通道排除仲裁单一源(T-126 跨件半问升级件;P78 批 1 命题入册)——4 通道×9 发射位×5 装配形态收拢单一装配 sell_exclusions(A 三段:身份/窗口/通道对价)+发射登记 LaunchCause 闭集(12 臂映射+四出口生命周期:卖出销/部署销/合成销/轮界销,五键账闭合分键)+reason 枚举闭集(5 值×9 发射位);P78-5′ 按 V3-04 精化入册(必要条件两腿+充分授权分离,M4 腿实现依赖申报);契约正本断链处置=批 4 在 flow/action_exec.md §1 新建 SellBench reason 条目+首次落档申报+dd-020 重锚,词表漂移勘误义务(以实码 18 项为准,同批勘误 action_exec.md 与 entry.py docstring);Z1 吸收/F2 拆三块修订/ADR-0580 §7 可回收修订注 | 四批全部落码(批 1-2 命题+身份段 10168c1f;批 3 窗口段 d5887403;批 4 收官:reason 载体+契约落档+9 位填充+五案锁/矩阵,纯遥测增益判定零变) |
| [0586-telemetry-deep-review-directory-layout.md](0586-telemetry-deep-review-directory-layout.md) | 0586 遥测与深评目录布局裁定(deep_review+telemetry 三段布局,game id 主轴,旧根退役,软上限删除关联) | 已实施(d98ccac5;三审 M5 as-built 勘误:matches 实作平铺/关联节修正) |
| [0587-shop-open-frame-node-type-ledger.md](0587-shop-open-frame-node-type-ledger.md) | ADR-0587: 店开帧 node_type 台账制——无条件滞后拷贝退役(C2 缺陷:店开帧拷 session.last_node_type,写点节拍晚于本轮店开恒拿上轮值,战斗帧误开②(b)+误抑制M3;改 ledger_node_type 查表+None fail-open+第二拷贝点删除;负向申报=连续硬节点段侥幸开门变诚实关门+M3校正+硬节点门首次拿真值;sim 双盲禁 A/B,验收=单帧锁+相邻锁) | 已实施(方案审零阻断后实施批落地) |
| [0588-run-boundary-attribution.md](0588-run-boundary-attribution.md) | ADR-0588: run_id 铸造边界对齐进局时刻(开局遥测行归属治本)——ensure_run_started 幂等门(空/收口/容器 token 三分支)+_RUN_MATCH token+入口链简报锚/投资环境/投资策略三分支选卡前铸造+loop 认领;start_run 本体零改动;历史 45+X 档案 invest 归属重算脚本(tools/cw/repair_invest_attribution.py,owner=首个收口≥行 ts,recovered/无收口行人工审单列,dry-run 默认+--apply 显式);装配端 ts 窗口兜底弃用;ADR-0460 选项 B 如实翻案(动了时序、门控拆风险后果) | 已实施(方案审零阻断后实施批落地) |
| [0589-budget-gate-realize-decision-frame-disclosure.md](0589-budget-gate-realize-decision-frame-disclosure.md) | ADR-0589: budget-gate 检查器支A realize 决策帧真值披露(T-133 假阳定谳修复)——引擎 LevelUp 执行点披露 dec_board_full/dec_bench_2star 两观测键(单动作架构执行点=发射帧;零 rng/零状态写入,w614 digest 锚零位移),检查器按击读披露真值豁免、无键账本(生产回放/历史批次)回退行末近似(直调单测零改动兼容);供给半环写端在位锁(快速层);行为零漂移(闸拒计数批前后逐位一致 seed18=14/22=8/10=8);后果申报=闸 0 判读不再携带「奖励帧支A批不存在」信息,掩蔽三件套=本批→sim node_type 可见性批(独立批)→策略域候裁(支A奖励帧豁免 vs ADR-0580 抑制张力) | 已实施(落地审三文件零阻断;commit 候 T-136 序) |
| [0590-deploy-yield-transition.md](0590-deploy-yield-transition.md) | ADR-0590: 部署面让渡决策(T-127 R2,方案 v3.1 收官)——锁线域装配级键集收窄(读法 D 单一源五消费位:核心羁绊∪已达成档承载弹性键,计数源=deployed_bond_counts/tier 源=FACTIONS)+转型域资格族统一(释放件无论 fenced 走转型臂资格族,基座臂提前返回封堵,arm 恒 transition)+守恒门锁线域默认保留(切终局线档随候裁批另立 ADR-0433 修订)+P79-3 执行条件发射门(压席成员存在∧保守形态档关键件[面板口径读法 b],defer 分键 redeploy_cost_gate_defer 与资格拒因分列)+P79-4 让渡序(结构档边际贡献升序→星级→板槽位序,校准值忘归人 0/希儿 2 首件=忘归人)+显式参数 REDEPLOY_TRANSITION_ENABLED 缺省保守(候裁行=进度账本 T-127)+分键闭集扩 target_keep/buy_membership+G1 准入 board_full 口径顺手修(占用数 vs max_units 禁物理门)+02 号稿 §7 姊妹出口句(R2 首项) | 已实施(方案三轮对抗零阻断;病灶局帧复演 victim=忘归人/up=罗刹;commit 候编排者统一门) |
| [0591-line-switch-orphan-exemption-key.md](0591-line-switch-orphan-exemption-key.md) | ADR-0591: 同轮买卖检查器豁免面补「线账闭合孤儿清算」键(T-141;P78-2a 账闭合语义对齐批)——SELL_BENCH_CONVERT_REASONS 三键→四键(+line_switch_collapse,通道名兼证明标记,双消费检查器自动同边)+义务类登记写点补全(ADR-0585 §6 在途件提前落,义务件有账可闭 close_on_switch 真实运转)+shop 四卖出发射位账闭合证明打标(镜像簿证明载体,sell_gate 禁碰偏差申报含等价性论证与回迁挂账)+entry 两处 funding 兜底位 funding_hold_liquidated 载体回填(三审三波 F6);F1/F2 事实纠错勘误正文持久索引(凑息回拉非 M4 腾席/M4 三位已接全量 A);防洗白边界=键授予必须伴随登记簿线账闭合事件 | 已实施(方案审零阻断放行;commit 候编排者统一门) |
| [0593-self-cert-loop-migration-suspect-detectors.md](0593-self-cert-loop-migration-suspect-detectors.md) | ADR-0593: 自证循环迁移(T-153,用户批准方案 2026-09-08)——检查器豁免边自算复核降级(9 判定核 C1/C2/C4/C5/C7:自算复核通过才豁免,失配=可疑项条目+不豁免,unverifiable 豁免照旧防翻旧案;C3 判据本体保留/D6 语境归检测器;判定核单一源=新件 sim/checks/selfcalc 复核三态)+可疑项检测器集 D1-D11(sim/checks/suspects,条目三要素:模式定位/自算 vs 自报对照/裁决问句;跨轮 streak 锚+交叉引用行,禁独立附录)+生成侧三披露键(engine_p1 执行点 dec_engines_count/dec_sell_in_line/dec_bench_wait_member,ADR-0589 同构零 rng 零状态写入;未锁线期名册不可解析=键 False 属语境缺失非证据)+复盘骨架生成器(tools/cw/review_skeleton.py,可疑项预填插节点小节判定三槽前)+merge_round_rows 动作并集并 SellBench(检测器生产覆盖面);决策路径零变化(决策面不读披露键 grep 守卫在岗)。编号溯源:初拟 0592 与 T-139 批并发撞号,本批让位改 0593(丢失更新事故当场修复,T-139 行原文归还) | 已实施(commit 候编排者统一门) |
| [0595-delta-pool-defense-guards.md](0595-delta-pool-defense-guards.md) | Δ池快照生成器数据防线：fake_/sim_ run 隔离+语料塌缩守卫（事故=假局微型语料经局终再生钩覆盖提交快照） | 已采纳 |
| [0596-prep-flag-state-machine.md](0596-prep-flag-state-machine.md) | ADR-0596: 备战决策环旗标状态机(T-159,用户九步初稿机制化;方案 v2.1 两轮对抗放行)——S1 开店闩改造(不退役,清键三路径封闭枚举:白名单 tag 落地/S2 在册∧腾席翻正任意 tag 义务优先/消费臂门 1,纯金变更永不清)+S2 wanted 残差旗标新增(商店域席满残差点置位 obligation 类+备战端四门序闭环消费臂:门0 stop_flag/missing 镜像→门1 席空闲先重进→腿1 部署→腿2 M4 卖角色→裁决放弃,键式字段×4 节点推进自动干净)+S3 不立变量(单向上位:纯函数幂等求值即脏标记,墓碑锁防双源)+route_tag 透传载体(PrepAction 基类 kw_only 字段+Emitted.reason 填值+桥伴带,T-153 治理对表=内部路由键非放行证据,sim 检测器零消费 grep 证)+RunTools 发射位物理移出 run_mandate(entry.emit ②③之间,同批删 M7.5 原块防双发射,dd-027 回排特例消除)+迁移 B 球席满前置谓词两腿(bench_free>0 ∨ 球均不占席按占席颜色集判定,缺省空集=宁多收球不误卖与 adapter 在库裁决同向,颜色→占席机制面待实机实证后登记收紧,腾席/残留跳过结构保活;2026-09-02 裁定容忍语义承载占席球面)+终止性三支柱(bench 件永久消耗/燃料不可再生/金来源封闭),B+1 安全阀降格=纵深防御非紧界;禁开/tags 治理/测试 29 新锁+8 改写;sim 同 seed 对拍零漂移(执行流程层结构性不可见无判据权);编号溯源:实施批初拟引用 0593 与 T-153 撞号自查纠正,统一门分配 0596(0594=T-143 烧号) | 已实施(落地审需修轻已修:M1 球谓词恢复两腿+N2/N3/N4/N7 文字面;修后快速层 0 红;commit 候编排者统一门) |
| [0597-t155-invest-econ-engine-and-dstar.md](0597-t155-invest-econ-engine-and-dstar.md) | ADR-0597: T-155 投资选卡新判据(用户裁定 2026-09-08「优先经济,然后是终局阵容」)——S2 经济引擎档(持续通道字段闭集谓词 is_economy_engine,域带 111-119 压 S3 上界 110/S1 120 之下,档内 PICK_VALUE 归一定序;一次性金/期权/难度/血本位不入,直算命中 38 条对账)+ S3 终局对齐源换 D* 级联(_invest_d_star:①锁线单判/detect_signals ②③④ 资产信号;五门裁决=evicted+weak_planes 继承、P2 缓锁/H1 环境/P1 ①资格过滤不继承;①层排除反投资自证;decide_event 签名 target_comp→locked_comp/demoted_endgame/evicted 参数组,flow.decide_invest 从 ist 解析传参,kernel 纯函数守恒)+ CommitSignals 纯遥测零消费零改(C5 现状即合规);双臂同 seed A/B 24×2 出口金/存活/[13]停手/通关四线逐位不降+经济档占比 0→19.1%;方案正本 v2.1 两轮对抗+轻量复核 R1-R3(v2.2)。编号溯源:实施批初拟 0596 与 T-159 批撞号,本批让位改 0597(ADR-0593 同款事故,INDEX 读时序实测) | 已实施(commit 候编排者统一门) |
| [0598-interest-cap-override-dead-link.md](0598-interest-cap-override-dead-link.md) | ADR-0598: T-160 息帽覆写死链修复(F1 方案审放行)——cap_resolved_of_session 单一源切 aggregate_economy(session.active_strategies)(None/0 判别只认 None,买断制 0 禁真值折叠;并持 max=ADR-0131)+ registry 预算面三处随批接线(reserve_cap floor 去 registry 参/assembly BudgetView.interest_floor/换线 e_rounds 可负担窗 session 参数线程化,None 形态退注册表零漂移)+ 幻影卡收口(持卡 append 移 confirm_and_verify 成功后)+ sim 检查器覆写语境观测键(sess_active_strategies 行键,τ 聚合解析,键缺席零漂移)+ 随批清理(cw4_cap_override 死字段删码墓碑+grep 锁/cw_plane_table.interest 死码删/MechanismMutation 未实现引用修正/cw_replay 补持卡回读);边界申报=get_node_goal 标量投影缝 session=None 恒 base cap(结构性)/锚 A1 后段未中+金出口族未随 cap=0 联动(升级车道吸金合法 hp 全段变好,刷新/升级竞速挂账期限化归全 planes 批或实机持卡局判读,ADR §4)/H5 利息上调臂流动性下降如实记;验证=L1 全绿+零漂移臂 200/200 逐位一致+买断制/利息上调 A/B 各 200/臂+演示局重放死链双跑边界对照(凑息卖 Sell×7 全消失);文件面 15 src+13 test 逐文件点名见 ADR §6 | 已实施(commit 候编排者统一门) |
| [0599-s2-wanted-precondition-and-p43-unwired-closure.md](0599-s2-wanted-precondition-and-p43-unwired-closure.md) | ADR-0599: T-161 备战攻击中低危修复包(F2 修改后放行/F3 拆半,方案审 T161方案审.md 裁决全落)——F2=S2 载体四元化(+在店快照:「在店缺员 (名, 费用)」置位时点子集,写点经 _shop_candidates 同一闭包计算,M2 最便宜卡口径/cost 兜 3/空名不进集;禁臂时点现读 state.shop=obs 备战阶段清空会闷死闭环,方案审 F2-1 阻断级)+消费臂门 0′ 前件(∃still_missing 在店快照 ∧ check_affordable ①号本体金臂时点现读;不满足=hold 零发射 S2 保留至键失配,禁早清防 late-flip 错杀)+语义收缩申报(S2 收窄「所见义务的买入闭环」,关闭重开→店内刷新碰牌隐性通道)+hold 计数键 wanted_precond_hold+刷新终结竞态残余窗口接受入册;F3=放行半(WIN_STREAK_BREAK_INTEREST 死常量+economy_score docstring 死句删除,零行为,cw_replay 改动前后逐位一致+grep 清零)+登记半三件(①激活腿结构性不可接线证明链=Δp 被 ADR-0516 封锁全库无合法生产者,四候选面逐面排除+支配消参被 P43 P2 表封死,「已证未接线」以此定性关闭 ②默认腿=保息已由现行息线判据承载 ③P48 §⑤联动按「消费方引用即登记」落账;禁 fail-closed 悬置占位,连败止血禁开)+economy_score 死函数另批登记;验证=前件五态锁+16 预期红转绿 37 全绿+L1 快速层 3184 passed+回放逐位门;12 篇 as-built 批面禁碰随统一门处置 | 已实施(commit 候编排者统一门) |
| [0600-t162-invest-refresh-criterion.md](0600-t162-invest-refresh-criterion.md) | ADR-0600: T-162 投资刷新能力恢复(事件面刷新判据重立;ADR-0519 C10 退役后换推导重立,非恢复旧阈值)——帧级触发(候选恰 3 ∧ 全精确分类[G7 策略轴+LCS 形变 fail-closed] ∧ 非 env 帧[F9 结构检测零 kind 参] ∧ 无 S1/S2 ∧ max_N≠1[J6 被禁不计]) + 槽级动作集(非顶级 − N≥2 对齐槽保护[混合档判别式 G3] − 唯一 L1 槽[F2 kernel 静态;序贯形态 handler 锁 14 承载]);逐槽弱占优推导 + math_proofs P81(条件结构命题,前提 V2 免费性/V3 重掷分布实机挂账,证伪 → 停用回退恒不刷);执行链 = cw_screen_invest_strategy 逐卡刷新(计数现读闸/发射即记防重入/验效双通道/重决策唯一入口 = flow.decide_invest[G1,锁 13 变异判别实证]/visit 起点单点复位三车道/J8 申报),env 屏观察写入一处零执行链;观察通道 = cw_node_obs reader(list 形态 OCR+正则族+x 就近配对容差)+screen_info 两档;PickEvent+refresh_slots 默认兼容;13_pick_family.md:18 刷新期权指针对账(P40 语义一致换 P81 载体);方案四轮对抗 14→11→8→0+落地审(F-A 三同步即本件,F-B 申报接受) | 已实施(commit 候编排者统一门) |
| [0601-action-op-mechanical-execution.md](0601-action-op-mechanical-execution.md) | ADR-0601: 动作 op=机械执行,画面/失败判断属分发层(T-164 批A 用户裁定 2026-09-08 原文收编)——11 违规实例四形态清查(画面判断跳过/失败自调度/换路编排/前置自判)+商店域参考实现(execute 机械执行+project 纯计算+守卫零读屏);区分线定谳=D2 三分(入口板满失配/幻影满板 fail 化 vs 批内动态停保留[机械安全边界判据:截断剩余≠跳过整批])+C2 晚帧重放豁免(与发射面同函数同参,治本形三段计划下发归后续批)+C3 replan 删除(计划失效 STATUS_PLAN_STALE 交回重派)+C4 失败记忆单一源上提(熔断删,守卫同签名计数兜底)+S1/S2 死代码下线(模态金 spheres 断喂登记);报告语义硬化=弃执行禁记 round_success+失败状态具名常量分键;批A 五项落码(E2/E3/D1/D2/D3)+bench 空 (0,True,None) 契约补全与行为锁;注释出处指针 T-164→ADR-0601 § 全量回填表在 §6。**修订(T-174/ADR-0609)**:§3 D2 增补板满失配窄豁免分支+§5「执行位现读不可信」论断按双源仲裁真值改写辖域(对幻影满板成立/对板满失配不成立)**修订(T-164 C1)**:§3 补 C1 条+§4-9 实施面——equip 求值块上提分发段(_build_equip_wear_plan 计划随指令下发,op 四 kernel 判据零引用 grep 锁)+空计划具名 NOOP(闩照置,dd-027 活锁闭合)+装备版 STATUS_PLAN_STALE(tools C3 同形)+回退路径一并计划化+哨兵双挂点单一源,方案审+轻复审两轮放行 | 已实施(主仓 f465c39dd+测试仓 a18a2612;本 ADR 为三审事后决策 why 补立;T-174 修订随 ADR-0609 批;T-164 C1 修订随本批) |
| [0602-sentinel-tree-kill-and-rescan-assert.md](0602-sentinel-tree-kill-and-rescan-assert.md) | ADR-0602: T-132 哨兵杀净=树终杀+杀后复扫断言+cycle_restart 两消费点收口(2026-09-08 武装链断事故决策 why)——collect_tree psutil children(recursive) 树收编(防后代 cmdline 漂移,psutil 单机制不引 taskkill/CIM;祖先方向不收编申报)+复扫断言(KILL_RESCAN_MAX=3 有界重试,仍非空 exit 2;停净双判据=「[杀净]…复扫零残留 ✅」∨「[杀净] 无需杀」,落地审 F1 修原单判据在已停净场景不可达)+AccessDenied 归 exit 2 契约(TerminateProcess 原子,杀不动=视作存活交复扫轮,禁 traceback 退 1 契约外,落地审 F2)+supervise/start_app 两单点 terminate 换 kill_pids_tree 复用缝(杀语义单一源,杀净失败透传 2 归前置失败桶)+否决面(--kill-all 旗标重名零增益/守卫侧识别哑孤儿不可检测/手册单行拦不住遗忘/第二杀机制)+verify 两盲区申报(同名双实例计 1 件/哑孤儿 cmdline 命中即绿,exit 0≠信道活,活性=pos 心跳/job 结算);第五缺口纯口径=autonomous-loop §3 消费协议第④步补位硬收尾+§2 模板问句落 `rewatch --verify N` 机械命令;注释易失索引「T-132 方案审」→本文 § 全量回填表在 §6 | 已实施(落地审 F1/F2/F5 已修;commit 候编排者统一门;实弹验收挂账本 T-132 待验行) |
| [0603-t149-guarantee-floor.md](0603-t149-guarantee-floor.md) | ADR-0603: T-149 保底金门(用户直接指令 2026-09-08「0金过P1是垃圾设计」)——升级豁免支(支A/ALL IN)放行输出加「花后 ≥ 1 息档(10 金)」下界:10=息档宽机制判等式(interest 斜率倒数,g<10 首息恒 0)+最小绑定支配论证零拍定;出辖三支(终局域=r_remaining 单一源查表/生存域=p1_blood_floor 让位=真花光唯一合法通道/买断制 cap=0 息账消解);值载体=DEFAULT_REGISTRY.boss_floor 同值异据共享(彼据=release 生存边际 ADR-0426,断言只锁同值不锁同据);拒因分键 guarantee_floor_defer(与 blocked 分离可归因);(3a) 路径零漂移;域③重入册=math_proofs P83(避让 P81/P82)+P72/P80/P68/p10 收窄指针行;[28] 50 线恢复表征地位不升闸门(双字段并读);判据节 prereg 十条+买入三臂分键观测项,跑批候 T-169 重锚;残扫2低项随批勘误(p10 §④→§②/engine_p1 进场继承块注纯语义定位);strategy-work §6 prereg 完整性硬门落点;方案 v2 对抗审 14 项闭合+轻确认 2 低项零阻断。编号溯源:0602 空闲未占用,按任务书指派取 0603(防与并行批撞号,0593/0596/0597 三次撞号前科) | 已实施(commit 候编排者统一门;A/B 跑批候 T-169 重锚) |
| [0604-t165-leak-ladder-and-allin-filter.md](0604-t165-leak-ladder-and-allin-filter.md) | ADR-0604: T-165 P2 转化期经济·泄金阶梯(档 0-3)+ALL IN 窗 XP 类别过滤——档 0 支配性优先序摘旗三处(dominance fn/M6 shop/M6 prep,stop_flag 触发前置移除判据本体不动,[13] 纪律由候选集承载)+档 1 可上场非定向买新臂 press_buy_deployable(锁线钉 _ist.locked_comp/围栏可落非垫件类 F12/金地板 g−cost≥g*/P72 拒帧挂起复用 ADR-0560/登记闭集第 13 臂 press)+档 2 压库摘旗扩域(窗口维持在产 ω 塌缩带 #11/轮内新鲜度排除=同轮卖X买回X禁 s108 实证,键式相位载体 SWAP_FRESH_BUYS 同构,写端 M4 族全收口 entry 球路径含,funding/line_switch 不登记面申报)+档 3 刷新降末档(本体零改);ALL IN 过滤=kernel all_in_xp_domain_hit(P21 域=停升级线单一源 P1=11/P2=21,D1 口径差申报禁第二套血线表)+P72 闸 ALL IN 支收窄(非支A XP 拒,分键 all_in_xp_category_filtered,位次先于 ADR-0603 保底门,[18] kernel 支掩蔽等价申报 F5);必答 #7/#17(T-161 不触发声明/P78-1 承压/奖励帧资格/C1 criteria)+F16 NORMAL 限定申报;hp 闸批零偷跑移交总图第 5 步;落地审 D1/D3/D4/D5 闭环 D2/D6/D8/D9 挂账 D7 归编排者裁 | 已实施(落地审需修小修已闭环;A/B 跑批候 T-169 重锚) |
| [0605-t109-departures-v10-and-075840-verdicts.md](0605-t109-departures-v10-and-075840-verdicts.md) | ADR-0605: T-109/T-100 遥测数据病合并批——离场派生列 v10 + 复盘 075840 三件定谳(①真缺口修 ②申报 ③反证):①场上件离场定谳=执行期 deploy 换血卖出无逐件遥测(决策时点卖出已在案;Saber 实锤 08:00:18→08:00:42 帧差),修=match_archive 装配端纯读派生 departures 列(身份多重集差,通道闭集 sell_recorded/merge_promoted/unexplained,感知纠噪边界申报),运行时写点修复候 cw_op_deploy 解冻批;②+64 金未建模收入=P2 轮界 18 差分唯一离群,唯一性关联降本增效选卡(1/1 vs 0/6,注册表 sell_refund×2 精算 58 vs 64 ±6 未闭合+板面未售矛盾),申报候选挂一帧定谳,禁未证建模;③「hp 帧读漏补给回血」反证(冲突帧 obs_conflict_hp__32006c4d.png 视觉实证 HUD=1,17=合成行陈旧快照 ADR-0577 §3.3 同型鬼值),零修+读数链形态锁;附带观察=胜战臂与行动值扣血机制注张力候 ADR-0431 线;T-100 残余件全收口(T-88 复核/v9 回落已锁;armed 分母键=entry.py 禁碰面候解冻批) | 已实施(commit 候编排者统一门) |
| [0606-levelup-cap-mandate-wiring-closeout.md](0606-levelup-cap-mandate-wiring-closeout.md) | ADR-0606: 等级帽单一源收口(T-26;收 ADR-0565 两笔挂账)——mandate 备战 M3 第 4 消费位接线(run_mandate 加 registry 注入参,entry.emit 链下传,lv9_stop 传 _reg.level_max/level_spend_blocked 传 _reg,lv9_stop 收严必填过渡缺省通道拆除)+level_spend_blocked 同族裸缺省调用位接线;零行为变更申报(mandate 位仅 live prep 可达,注入值=缺省表同值;停付线字段与 level_max 无关);两把注册表注入变异锁(同帧换表判定必翻转:level_max 9/11 视图翻转 l3_reject_level_cap/vd_p2_loss 30 视图翻转 crisis_level_spend_defer),变异态打红+还原绿在案;level_spend_blocked 函数级 None 通道保留(entry/shop _reg 同款约定),新消费位禁依赖缺省 | 已实施(commit 候编排者统一门) |
| [0607-entry-chain-popup-guard-registry-and-claim-target.md](0607-entry-chain-popup-guard-registry-and-claim-target.md) | ADR-0607: 入口链弹窗守卫注册表化与领取目标修正(T-101/T-102;闭环 ADR-0574 §2.4 两挂账)——EntryPopupGuardSpec 数据表+try_handle_entry_popups 单函数(四挂点收敛单行,序位=元组序 supply→jade→badge,序位锁 L6 元组重排即红)+星徽详情守卫落位(双锚 AND@0.9 防御面,不预建变体分支;判据分叉调和=入口 AND vs 对局内 1d OR 禁顺手统一,OverlaySpec 复用否决)+jade 薄包装删除(零调用死代码,supply 薄包装留给 back_to_normal_world_plus)+领取点击目标修正(中央徽章区→文本-领取提示 S2 实证点;旧 rect 改名「区域-中央徽章危险区」留档作负向断言坐标单一源,L1/L2 相位窗口负向锁);变异红证两件(序位重排→L6 红/点击回退→负向红)实证在案;非目标=退局 op 无守卫/大世界侧 detail 不接;S3 空白采样挂账含四处锚面回填义务 | 已实施(commit 候编排者统一门;实机 E2E 挂当日未领取窗口) |
| [0608-t171-seele-support-downgrade.md](0608-t171-seele-support-downgrade.md) | ADR-0608: T-171批序2希儿系支持度端口降档——_seele_system_support单一源分级公式(希儿∉手=0,否则min(1,max(量/2,贝/2)),去重成员计数=羁绊激活语义合成零扰动,0.5为推导后果非拍定)替换「到手即1.0」旧口径(ADR-0519 C2 post-state取代关系);坐标系声明=同文件两套计数口径并存(希儿系去重成员vs星级当量,分歧裁决交T-166 R2,双向测试卡口);池来源口径(用户定稿六名vs注册表4+4两源差异挂F8确认);挂确认指针(只计放大器读法+量2量3张力,数值不可分辨纯语义归属);中间态申报(批2→1窗口三不);验收指针(11锁+变异2红;原13锁4红,消费面2条与Formula格1/格3同断言删并、文件名改机制主题名test_cw_seele_support.py,落地审八维);测试重锚记录(frozen_pair_snapshot_lifecycle锁存在性纪律正当重推) | 已实施(commit候编排者统一门) |
| [0610-deploy-front-invariant-and-rowfix-exemption.md](0610-deploy-front-invariant-and-rowfix-exemption.md) | ADR-0610: T-174 奖励节点停机根因——部署出口不变量+板满失配窄豁免+0j 预算复位收紧(方案 v2 经方案审放行,必改 F-1/F-2/F-4 全落)——对账翻案(T-159 旗标环已覆盖已激活,收取臂缺失归层不成立;冻结根因=①r241 换排纠正与主循环前排保证对「前排非空」无单一所有权,pref=back 全员形态纠正拖空前排 op 仍 success ②0j 恢复被板满失配闸短路 r250 永不可达);F1=禁清空前排守卫(计数=调用内动态维护[方案审 F-1 钉死,静态读法双前角色形态复发同型 bug]+r250 后置补位(路径无关,函数头读数结构不变量「补位触发⟺r241 无涉及前排完成移动」)+execute 收尾 2.0s 后 CV 现读出口断言「上阵≥1⇒前排≥1」辖 DEPLOYED/NOOP[方案审 F-2 钉死]);F2=板满失配窄豁免(门值∧前排4槽全空∧后排非系统单位 fresh 现读三合取→场内换排修复→复验→STATUS_ROWFIX_RECOVERED,分键 board_full_front_empty_rowfix;窄度红线=前排有人仍 fail/PHANTOM 永不豁免[L4b 负锁]/身份不可得不豁免;ADR-0601 §3 D2 增补+§5 辖域改写随批);F3=0j 复位条件收紧(ExecState.last_prep_battle_launch_ok 三态,StartBattle 验证失败环外循环仍 success=True 的实证形态不复位);Considered Options=a 收取臂(能力已在且实测工作,第二实现+零作用)/b 排除腿过渡(已存在且非缺口,违开关生命周期门)/d 决策层前排预检(不变量第二实现)均否决;登记 2 条(r241 want 口径不消费 comp 覆盖 ADR-0139 挂账/出口断言 DD-030 幻影残留有界);验收=10 新锁全绿(9 原批+L1c back-full 不误计守卫分键,落地审 F-C 随批)+变异 5 发亲测打红(静态计数→L1b[L1 对静态/动态计数不具判别力,落地审 F-B 勘误]/守卫移除→L1/断言禁用→L2b/复位回退→L6/PHANTOM 豁免→L4b)+L7 回归面 220+锁绿+id_mark 零漂移;sim 结构性不可见声明(纯 operations 层,不可 A/B 只可实机);画面档=停机帧 fixture 归档+analyze_screen 离线回读零漂移 | 已实施(commit 候编排者统一门;实机验收=连续 ≥2 局 P1 全轮次推进挂账) |
| [0609-t83-prep-node-ledger-write-and-heal-longline.md](0609-t83-prep-node-ledger-write-and-heal-longline.md) | ADR-0609: T-83 P2备战时点节点条观测链修复+结算tooltip「长线作战」回血分量补链——缺口1(P2备战轮台账miss 18/24,p26标定批披露)根因=PlaneNodeLedger写入端缺位(写点②投资环境重读仅开局触发/写点①位面详情仅接管局触发,正常局P2/P3序列恒无写入者;实机4局对照钉死结构性:正常局P1全命中P2 r1-r6全miss,接管局P2反命中),修=备战帧heavy观察加写点③(槽idx 0-based与台账seq下标同基零换算,last_state.plane位面键,投资环境变异窗守卫,轮位对齐门=current槽idx==round_num-1防漏检圆槽枚举左移错位合并,按位合并None保旧,best-effort);否决面=扩写点①(交互成本+接管通道契约稀释)/recorder逐帧回退(第二读链+店开帧结构性None)/只登记不修(判读原文已定性修后自动回填);**消费面全清单申报(落地审需修闭环)**=ledger_node_type在役6处随P2填表全激活:遥测2(p26采样/flow掉血回落)+决策级4(state.node_type查表优先翻转=策略主输入/三票校验P2激活=L0安灯停线新触发面/buy_cards②(b)发射臂与M3抑制P2可达/equip_all装备释放判据P2可达)——口径=P2补齐P1同等查表制的一致性增益,代码不回退,P2判据发射质量挂实机判读;sim申报=全落operations/遥测层,模拟器双重结构性不可见,禁sim A/B验收;缺口2(tooltip幅度=链差+2,败面19/20)机制定谳=「长线作战」战斗结算回血+2(ADR-0241口述+连胜轨迹;败面也+2⇒口述「胜利」限定被数据收窄为每场结算回血,已回指针勘误ADR-0241)+heal_longline六点补链(解析器已读但RoundOutcome/schema缺字段静默丢弃→补RoundOutcome/read_round_outcome/battle_wait页1暂存×2+合并键/schema/recorder),L_node对比恒等式(链差=掉血两分量+回血)行内三量齐;验证=写点③构造场景锁6用例(含轮位对齐门锁)变异短路5/5红+对齐门松开红+heal_longline锁3用例两处变异分别红,点名测试33文件全绿+全改动文件ruff绿 | 已实施(落地审需修2项+建议修1项闭环;commit 候编排者统一门;miss率复测挂下批sim/实机台账读数) |
| [0611-t165-round-mutex-unified-latch.md](0611-t165-round-mutex-unified-latch.md) | ADR-0611: T-165 振荡回归热修——同轮买卖互斥统一闩(L1买后禁卖/L2卖后禁买/L3豁免分键结构化;双批103/114条违例泵形态根治=r408不变量载体化恢复)——L1读源定谳fresh_buys_of(方案审A3考古:r408「本轮已买」半边存活于cw4_swap_fresh_buys,每笔买入无条件写先于合并捷径,hold拒收/捷径/未映射三形态天然覆盖,登记簿退守因类账本+T3 defer视图)+垫保与换线孤儿双carve-out(垫保不升硬面=P78-5′转化类放行保持[A1];孤儿清算=P78-2a账闭合豁免语境[B1],四批复测全部同轮买卖对5/6/9/9例100%为该形态=在野承重实证)+义务镜像簿载体定谳(登记簿被同帧先到装配A读点就地销账不可辨「曾义务」,scratch轮戳簿跨销账存活,簿键/读口/证明集自shop上移sell_gate单一源[T-141回迁候兑现])+C2读端自治fail-closed(相位从黑板帧last_state/shop_state_frame自行解析,不消费current_round形参=None漏接线不再静默放行[对V2-09显式翻转];三分支=相位匹配名集/失配空集/帧缺排除当前记录全集,读取零销账)+L2统一过滤位(档2新鲜度排除扩域全臂,12过滤位收口14映射键,逐臂分键<arm>_round_sold_excluded[M6键名零断链,ADR-0604 §3-5载体],B2①同轮孤儿买回被禁=意图内)+A4硬闸(未映射reason抛错,静默跳过=绕过登记与穷举断言地基为假;臂计数12/13→14对现值校正)+L3 convert_reason结构化分键(值域三放行键,恰4发射位填充,line_switch_collapse留reason不迁[ADR-0591 §4打标语义耦合],检查器按键分工不并读零双源,''恒不豁免,引擎转录面C4随行)+B4机械件(P24误注修正,P24=残余补部署支配无买入命题,锚换[41]+P76甲+P78-1);B2②P60换手写端缺口承重声明(entry域funding/line_switch卖出不入轮内卖出登记=换手形态承重结构,未来补全写端批须同场处置禁静默杀死换手);L1/L2权威序=发射侧mandate行为判据/kernel侧v2_round_sold执行对账,不合一声报;方案对抗审17项(A1-A5阻断5/B1-B5/C1-C7)全闭合,Considered Options含②a先卖后买维持弃用(二阶候补)/垫保入硬面否决(语义改判须独立对抗审)/dominance豁免否决(P78-1定义性抵消)/复测批600-899否决(r2撞车改900-1199);验收=七测试文件181用例全绿(新锁22条)+六变异红对在案+四批复测no_same_round/oscillation_xp_cap双零(300-599复跑/600-899配对×2/900-1199独立,同池指纹0e091d4d)+独立复扫同轮买卖对100%孤儿豁免语境零真互斥+保全线8项带内(出口金/[28]299-300/出口hp/形态凑齐率−2pp噪声带/boss胜率略升/degrade 27与37局噪声带/osc共现不可判读合规/同池指纹)+B5交叉分键首份同键数据(reason×引擎身份,dominance→pair 2658/off 2077为大头);判读留痕=attacks/t165_leak_ladder/判读留痕.md(易失档,持久结论以本ADR §5为准) | 已实施(落地审F1/F2/F3收口闭环;commit候编排者统一门;P4相邻轮种子回卖=同族第二形态独立候批) |
| [0612-delta-pool-collapse-baseline-committed.md](0612-delta-pool-collapse-baseline-committed.md) | ADR-0612: Δ池塌缩守卫基线来源修正——守卫基线改 git HEAD 提交版优先(盘面兜底),治「塌缩自我延续」(2026-09-08 三次静默覆写先于守卫入库=时序穿透;守卫在场下 286/48 微语料再生持续放行=基线读盘面对提交真值失明;条件方向/唯一入口/测试锁核查无误,退役申报否决)——真文件终验基线回 16391/2246+微源即拒;基线来源变异红证亲测;工作树塌缩件还原与 n300 锚重推(替换 T-169 批钉在塌缩指纹 0e091d4d 的 ANCHOR_REGISTRY_N300)归编排者另批 | 已实施(commit 候编排者统一门;塌缩件禁入 commit 为互补约束) |
| [0613-t171-seele-form-port-or.md](0613-t171-seele-form-port-or.md) | ADR-0613: T-171批序1希儿系形态端口OR语义——Comp双字段(or_legs析取档组+required_deployed carry在板,缺省空=非希儿对逐字节不变)+form_progress虚拟腿折法(OR组一条虚拟腿取组内max/carry逐名0/1腿,fp=1.0⟺成型谓词单一源契约保持,四观测面全经readiness_form_ok一条链)+pair_target_comp希儿对重构(form_tiers只放他体系档,放大器两腿挂SEELE_OR_LEGS=((量子同频,2),(贝洛伯格,2))常量单一源,零新参数=文档定义行档位);取代ADR-0459「桥池档+量子配方档」AND全档条款(先例=0608→0519形态),全仓内联位收口(cw_evolution._comp_formed委托readiness_form_ok,空档短路保反甲白厄语义);两端口切分机械锁(form链禁_seele_system_support);5低项F1-F5随批吸收+批外C1支持度docstring量2/量3张力挂账指针;中间态申报批1→3窗口(OR更早达成而冻结未接,摇摆或压保持读数,换入门/冻结接缝未辖);验收=16锁全绿+变异OR退AND亲测10红还原绿+A/B同seed配对seeds1500-1599双臂同池460e6031(希儿系对出口form_ok 1/3→3/4,seed1509 False→True,非希儿89/97→89/96不劣化,degrade_recover_mutex配对逐局一致4局;n<20只报告+方向读数,≥600大批候T-169重锚) | 已实施(commit候编排者统一门;批3冻结接缝前置=T-166 R2) |
| [0614-evolution-grade-swap-arm.md](0614-evolution-grade-swap-arm.md) | ADR-0614: T-168演进层换血提案接线·最小等效通道=演进降级换血臂——ADR-0382分级语义接入换血机器参数化面(evolution_swap_arm_trigger准入三元单一源:锁线∧转型域[fp缺读/≥1.00臂关]∧板满∧bench在册采购集件,装配级缺省计算+执行侧SIFT域重算覆写=发射⇔执行同值)+star_guard武装让位(可读星级>1进结构守卫评估,其余守卫全保留,星级不可读恒拒,非武装帧逐位同旧);零新发射位零双发射(M1″既有发射位/sim引擎块单点不变,胜出者仍P79-4让渡序1★恒先=只在无1★可卖帧扩容victim集);上core半边复用既有部署链(RunDeploy→CwOpDeploy卖出臂+部署/sim=引擎转录+轮末残余补上,bench翻正S1清键deploy_launch自愈);卖出代价轴重推(P41往返净0闭合在武装帧失效,正当性=板满席满线未成卡死态的槽期权+core上板完成度收益支配2★线外件持有价值;P61辖域注=B_t严格增腿独立承载收敛,证明批回填挂账);Considered否决=整体接线evolution_step(第二决策面+CompTransaction通道零提案喂入休眠)/独立发射位(双发射+第二可行性门)/三元只观测(泄漏)/持久门(与form-advancing轴双重收窄反向);as-built双指针=flow/action_exec.md第三例外+strategy-docs/14落码回记二;验收=新锁6(T-21准入常驻锁)+变异4红还原绿+邻锁重推1(lesion帧star_guard显影消失=臂激活伴生面,胜出者逐位不变)+swap族76绿+L1绿+A/B同seed配对④22→30(+8pp,8翻正×0翻退)执行354→386 star_guard189→1/不相交④+6pp/abandon帧正值口径6206→6154(锁线3423→3371/未锁2783=2783逐位/帧集978=978,未达标如实申报+量纲论证=上游状态量非输出量) | 已实施(落地审F1/F2收口+F3-F6随批;commit候编排者统一门;evolution_step死代码本体处置归后续批防第二决策面) |
| [0615-zero-settlement-self-id-and-t181-verdicts.md](0615-zero-settlement-self-id-and-t181-verdicts.md) | ADR-0615: T-181 outcomes断流定谳勘误+零结算段自标识列v11+决策独有段时序插位——定谳勘误(T-178落地审F2报「17:44后断流」不成立:210431零StartBattle发射/012536出战4次未成战,结算帧从未发生,零行=正确行为;rounds_survived=收口时点state.round_num冻结值投影)+v11装配端纯读列settlement_gap(决策帧≥1∧结算行=0的段自标识{decision_frames,claimed_rounds_survived},segments/endgame.segment_summaries双面;空段/含合成行来源段不标注[合成行在场=有结算记录形态,ADR-0577先验不重复])+assign_games时序插位(决策独有段旧法整体补尾+归组并入games[-1]无时序门=temp亲测错组实证g_20260909_053235=[053235,210431]夺段,v11 bump重装配必显影故随批治本;段首ts跨两流单遍成账插回时序位,ts缺失补尾退化/同ts按run_id平手/孤立续局语义不变);Considered否决=修结算链(前提证伪)/离线补行(decisions.hp冻结值非真值,合成=schema9退役鬼值同款)/归组加ts相邻性门(治标于门,插位治本于序);验证=新锁3+变异2发(注解停用→主锁红/插位停用→M1锁红)还原绿+live temp副本端到端(g_165445=[165445,210431 gap={79,6}]/g_053235=[053235])+archive68绿+受影响面100绿+L1绿(1红=T-168并行在途时点态,锁重推后零红);跨层指针=rounds_survived写点语义(cw_loop局终收口)与停滞根因(备战炼狱/出战未成战)归行为层另批 | 已实施(commit候编排者统一门;存量档案bump生效后首次load重装配=纠偏到时序真值) |
| [0616-t166-pair-direction-predicate-ontology.md](0616-t166-pair-direction-predicate-ontology.md) | ADR-0616: T-166六面合并设计件——配方对方向判据四层谓词结构条件决策本体入册(证据中性计票×在任优先×form_ok冻结×可行性门;命题1a在任优先严格大于单席易手/1b冻结解冻闭集p1_pair域恰三项含comp锁定取代+F=1⟹对非空不变式孤儿态构造消除/2计票封闭双量纲四象限+归一化比值+希儿系第④格换算式(T-171双口径卡口随本件入册闭合)/3可行性门E≤R_rem后置合取+断供降格「已知晚触发域」+p1_pair域无早退通道诚实申报+s995同帧同闸/4 V_slot>0席位外部性否决dominance_buy_eligible本体单点收紧两消费位同收/5让渡资格余量公式+守恒门双保险+off-direction量词收窄);变异七件M1-M7+消解矩阵+s995三分判读;P84五条款对账(双向禁改/三谓词独立分界);验收基线修正口径(同帧混排伪影高估2倍,真实未成型3.0%/relapse 8.3-8.7%/26局锚种子段[2500,2800))+D12检测器扩展义务;§12.13接口项=ADR-0613物化变更致希儿系对E/form_ok偏开分量联审义务候T-171批3冻结接缝;行号锚符号名双锚条款(在飞活跃文件禁按行号直改);ADR-0357前提证伪记账(支持度只增被T2/T3证伪,两对象分立非滞回复活);编号溯源:初拟0615与T-181批并发撞号让位改0616 | 已立项·批1(意向层核心)已落码 4800a0afc+落地审accept(命题R2已过方案审F1-F11折入+编排者核销);批2(买侧命题4:mandate.py dominance_buy_eligible 本体 V_slot 收窄未落码,该文件面 T-190 批B 在飞)/批3(部署面命题5)/复测批候派(实施序=ADR-0616 §8,批1=第3步已完) |
| [0617-fullbench-merge-buy-dual-ledger-isomorphism.md](0617-fullbench-merge-buy-dual-ledger-isomorphism.md) | ADR-0617: T-182 满栏合成买双账同构(2026-09-09 05:52 运行局守卫误炸双响事故)——根因定谳 expected 正确/tracked 漏记(m2_merge_completion 满栏帧 own=2 走 §2.5:游戏接受并合成[bench 素材消费腾槽/场上载体升星],投影 simulate 正确建模,旧 tracked mutate 满栏丢件不合成→两账结构性分叉;守卫满栏豁免按投影侧占用判定,同 visit 下一动作落腾出槽 8<9 逃出豁免对拍误炸;复发=商店入口播种取自 tracked 账非屏幕);金链逐动作证据链(屏读金 61→59/51→48 交叉对账,journal gold/bench_used=投影字段非游戏回读——口径精确化按落地审 F-3);修=满栏合成买分支单一源化(`_apply_full_bench_merge_buy` 自 simulate 抽出,mutate_bench_deployed 加可选 shop 参与 simulate 同分支,shop=None/未识别名零漂移维持丢件)+守卫逻辑零改动+ADR-0518「席位门后满栏分支生产不可达」声明证伪更正(m2 合成完成买=§2.5 常态生产入口)+豁免面收窄申报(剩非合成满栏买像素差 fail-open 残余窗)+T-59 副本面兼容声明(≤2 同名同星同场合法态,重放载荷即含绯英×2/花火×2);转呈=merge_preview=0×m2_merge_completion 并存疑点归 mandate_v1 提案侧(journal 锚点随文);验证=新锁 6(事故帧重放×2 守卫静默+变异自检+k2 同构+两零漂移)+外部变异 4 红复原绿+受影响 62 绿+CW 快速集 3395 绿+ruff 净+落地审全技术门放行 | 已实施(落地审需修文档三同步闭环;commit 候编排者统一门) |
| [0618-p86-no-target-three-arms.md](0618-p86-no-target-three-arms.md) | ADR-0618: P86 无目标期三臂判据落码(T-177)——FALLBACK_COMP_NAME 四面退役(①hoard 终支换三臂+墓碑注/②economy 兜底锚退役维持缺省 3 费+申报/③P1 门绯英恒 no-op 支删除[死分支断言测试化]/④DirectionView.fallback_comp 字段删除)+三臂判据 kernel 单一源 no_target_arms(甲臂=强锁门逐字[promote_candidates 禁入]/乙臂=cov≥2∧非单卡身份资格核+非合并素材第五前件+四谓词核,发射位先于 M2 承载三层仲裁序[层1 授权面收窄 C_x={l_d}/层3 声明序;覆盖数降序否决测试化]/丙臂=守息缺省合法空带 source 证据)+k_members 三下游换源(错向囤积与必花烧费同帧族结构性消失)+契约面最小触碰(k_fallback_band/source 六例带维度+_s_reserve_line_formed 合法空扩展=裁决②落地必要件,编排者追认)+LAUNCH_CAUSE_BY_ARM+hub_option_buy(hold,15 键穷举重推);Considered=F-1 竞争域二选一裁 a(可发射快判,合取不过不获挤占权)/M2 通道承载乙臂否决/店面遍历序否决/v1 空洞形态否决;已知缺口=缓锁豁免角漏授(corner_defer 显影,M2 自纠)/家族集中轴判读守/hub 名集载体已挂读端归部署域;验证=新锁 30+变异 3 红还原绿+重推 5 文件语义重推+L1 3437 绿+sim A/B 同 seed 配对(案发帧错向囤积 2→0/带内烧费 5→0/枢纽发射 1>0/headline 噪声带;manifest=.debug/temp 易失,结论以本 ADR 为准) | 已实施(落地审 F-1 修+F-2~F-6 随批+F-9 加固;commit 候编排者统一门,与批序3 共占面统落) |
| [0619-own0-fullbench-merge-buy-gate.md](0619-own0-fullbench-merge-buy-gate.md) | ADR-0619: T-184 满栏合成买 own=0 边界门(改动三审 C1 转呈)——own=0(全场 bench∪deployed 无同名同星)+店内同名同星 3 张的满栏域,merge_buy_completes 判 own+k=0+3≥3 通过 → 挂尾 3 张自合成、载体(2★)落 idx9 被 del bench[9:] 截删,双账同构静默偏离游戏真值(满栏 own=0 首张无空槽无合成进行中,游戏应拒);根因=§2.5 满栏例外缺「已有素材/载体在场」前提门;修=判定单一源 merge_buy_completes 加 own≥1 门(own==0→False,四消费点同源生效:simulate/tracked mutate/engine_p1 预检/cw_merge_simulate,零第二套判据;merge_buy_k 保持纯张数函数)+数学闭合(门后合成组必含场内张,截断恒不伤;own=0 域整体排除)+§2.5「连升同理」低置信张力存照(ADR-0482 未证口述按待证假设,拒买保守端,对账网实证翻案须回单一源改门);Considered=A 门拒(取)/B own=0 机制论证后修截断序(否:唯一依据连升低置信口述与 §2.5 常态条款相抵+表示层特例复杂度)/C 不修留档(否:幻影账喂决策);生产行为无变更(提案侧六门下 own=0 域不可达,本门=模型正确性修正+防御纵深);执行侧 k 记账位拒买帧不可达(buy_click_ineffective/applied 门);验证=新锁 1+既有 6 锁回归+变异环(摘门恰 1 failed 27==30 病灶形态/还原 7 passed,落地审独立复演同型)+受影响 84 绿+CW 快速集 3445 绿(首跑 1 瞬态红=并行批所有物,孤立复跑绿)+ruff 净+落地审技术门零阻断 | 已实施(落地审需修文档三同步随本 ADR 闭环;commit 候编排者统一门) |
| [0620-invest-registry-drift-adjudication.md](0620-invest-registry-drift-adjudication.md) | ADR-0620: T-157 注册表维护批②③定谳——大裁员免费刷新 6v5(直调:base 官方卡文 cw_invest_data.py:134=6〔plaza:202101,API 生成层〕vs overlay cw_investments.py:217 free_refresh_burst=5;裁 6 为准,权威序=base 官方文本>手工 overlay>文档转述〔G5 原则,本 ADR 为决策正本〕;5=手建模漂移,值纠偏+入口漂移标注注释申报候裁归建模批;测试仓无 5 锁零波及;实证分键线挂 C4 不在本件展开,实证材料在库 match_g_20260828_161135)+「经济类环境 16/83」无出处清理(唯一载体=cw_investments.py:1198 头注;数对出自 ADR-0144 评估产物 env_eval_full.tsv 已灭失,ADR 本文只承 47/83;注册表 ENV_CATEGORY 直调=经济 15/83、带 EconomyEffect 环境 0 条,分类口径≠评估口径禁互替;处置=删「,economy 16」申报候裁,禁用 15 原位替换伪造口径);玩法文档面对账零冲突(docs 全树负验证);零代码改动 | 定谳入册(代码面两项申报候裁) |
| [0621-seele-static-form-or-fold.md](0621-seele-static-form-or-fold.md) | ADR-0621: T-171 批序4 希儿系静态套成型判据 OR 口径——病灶=静态套 AND 完全体(量4∧贝2)与文档口径(transition_combos.md:27 希儿在场∧量2∨贝2 不设完全体门槛)分裂,锁线对 form_ok 1/11 vs 对照 81/89;修=判据常量真源归位注册表数据层(cw_comps.SEELE_OR_LEGS/SEELE_CARRY_CHAR,intention 侧改指已随 T-35 批落地,对象身份接线锁守卫单一源)+静态条目挂 or_legs/required_deployed 与 ADR-0613 pair 同构+form_progress OR 组承接同键档位(键级辖域;档级承接否决:量4 回 AND 账=病灶回归;清空 form_tiers 否决:囤货采购集/_line_hoard/locked_faction_scope/换线距离账读键值面);量2/量3 文档内张力候玩家(改档=常量一处+恒等锁两侧+_seele_system_support ÷2 分母第三表面 cw_intention.py:583-587 同步回改);验证=病灶帧 fp 0.625→1.0+变异 M1=8/M2=10/M3=1 红还原绿(网格①恒真式不计红证)+13 锁/域 265/L1 3468 绿+落地审 13 锁断言手工重算全对 | 已实施(落地审 B-1 本 ADR 立档+B-2 注释锚/B-3 第三表面指针/B-4 负例/B-5 桥池不变量锁随批闭环;commit 候编排者统一门) |
| [0622-refresh-cost-live-ocr-authoritative.md](0622-refresh-cost-live-ocr-authoritative.md) | ADR-0622: 刷新费现场识别为准(玩家裁定2026-09-09「必须靠现场识别为准,不能靠事后推导」)——金币差倒推退役(只证偏差/同窗归因/P1r9+level5-6证据域约束一并作废),写端=商店开态刷新钮标价现场OCR(reader参照cw_node_obs先例,数字规则修复,失败=None禁兜底);推翻ADR-0456徽标退役的「不重建」延伸;干净备战屏价签(文本-刷新金币数已建档)维持不识别(该区域读数实为利息徽标,ADR-0456定谳;裁决现落设计文档§3.3.4);落地批已实施(2026-09-09):建档文本-刷新价格[1584,513,1664,558](MCP,5归档帧8x精测)+reader cw_shop_refresh_obs(两级管线/可信域[1,9]/O→0图标规则/0恒拒信)+测试11 passed含5真帧锁恒读2+波及域零新增红;挂起=实机shop-open帧回验候有局批+主链接线候迁移批次一 | 已实施(挂起两项在案) |
| [0623-round-start-income-t1a-single-source.md](0623-round-start-income-t1a-single-source.md) | ADR-0623: 轮首收入 T1a kernel 单一源函数族(统一观察架构 §7-T1/T2 搬迁 kernel 半部)——round_start_income 四分支(supply→reward→败补→常规,与引擎 elif 序同构)+reward_base_gold 平面感知键(P1{1:3,2:4}/P2r1 与 P3r1=5,消 P2r1/P3r1 单键误返 3 hazard)+loss_compensation_base(记账口径=玩家裁定平面感知键,待玩家确认)+RoundStartIncome 分解账+LostNodeRef;win_reward_mult 参数化施于连胜分量含奖励轮(修复 sim 零消费挂账 kernel 半部,引擎半部=T1b);net_income 处置(方案审 F4-①)=(a)委托改造+传参简化(P1 规划投影,消费点数值逐位不变,等价性锁在册;6 消费点全传 streak=0/lost=None 近似不落值),round_base_income 降薄别名;败补判别执行(方案审 F4-②)=分桶重放 146 局(tools/cw/loss_comp_bucket_replay.py,判据值独立内联)**数据不足定谳**:P1r1/r2 败局阶梯零样本(低轮位恒胜)+boss 桶 n=1+节点序把败轮类型与下一节点类型结构性绑定(类型差分与到账项差分不可分),记录模型维持玩家裁定口径+待玩家确认,补采口径=孤立败轮对照局×{P1r1,P1r2,boss 跨位面}≥5 局/桶;附加观察=差分窗恒见 +5 公共项(候选=下一节点基础金轮首入账)归到账时序三点差分实验;Considered 含 (b)纯申报否决/签名加 plane 强形态否决(并行批在飞+规划语义等价)/改判类型表否决(证据混杂)/宣称已证否决(零样本造假);申报表=统一观察架构 §7.1 | 已实施(T1b=sim 引擎改调+live 写端指派另批;待玩家确认行在案) |
| [0624-dominance-settlement-line-floor.md](0624-dominance-settlement-line-floor.md) | ADR-0624: T-193 dominance_buy 买后金下限地板(结算线地板)——穿线破息修复(病灶三批实证 24 事件全含 dominance 笔,唯一无买后线检查臂);谓词 check_settlement_line(gold−cost≥g*,g*=saturation_line(cap_resolved) 禁字面)+dominance 臂消费位(候选级分键 dominance_settlement_floor_reject,拒后 continue 试更便宜候选=顺序贪心预算封顶零批状态)+档 1 内联地板同谓词迁移(行为不变)+②(b) 另一形状不合流;授权=结构+纪律面与 EV 解耦(W-(i) 冻结口径单调不增+P70 溢余带零损域封回+守息例外闭集完整性+ADR-0604 档1 无开关先例),候选 B 通道豁免否决(改例外正本反题+损失当轮不可逆+无 fail-closed);W-(i) 席位级联反例如实入册(冻结口径非逐帧保证);残余面让位 C1:unlocked(候裁走 ADR-0580 修订)与义务臂;S-2 mandate 面陈旧声明两项+谓词归位=阶段化缓置候批1落地后编排者补;验证=新锁 8 先红后绿(修复前 6 failed 含 E2E 发射级 2 笔穿线行为红)+变异 2 红证+F3 no-op+F5 边界反例入锁 | 已实施(落地审候编排者另派,commit 候其结论) |
| [0625-core-seat-vacate-always-buy.md](0625-core-seat-vacate-always-buy.md) | ADR-0625: T-115 恒买腾席支——席满帧静默弃买违 ADR-0580 规则③裁定且零显影(未锁线腿 break 无键/锁线腿帧级前件 bench 维循环外拦死/④腿 break 无键;病灶 s8r8 金95 希儿在售 8 刷零买零卖);修=资格门收窄 core_single_card_buy_eligible(locked_buy) 席位维下放循环内+三腿共享腾席 helper(sell_exclusions(m4_fuel)∪fuel_sell_candidates 单一源,卖 1 张即止,转化=下一迭代原臂原判据买入)+无 victim 诚实停摆(骨架义务>裁定族)+金闸双桶分键(候裁4 默认案=卖前金读,均显影不动作)+尾键 for-else 收窄(席满停摆不落数值域键)+判红检测器(写端位出口键完备性,计数式轮级回退红则 Σseen>Σ出口键,批级桶分布披露)+②(b) 外门席满支卫生键(候裁1 移位案);种子显影键直调无单一源=申报回退候裁禁静默(残注③);Considered=仅检测器否决/现状否决/帧门前 helper 否决;验证=新锁①-⑨族+旧锁重推(bench_full 判锁层订正+EmissionFace 9→10+Manifest 5→6)+守卫移除两把红还原绿+受影响面/快速集全绿+ruff 净 | 已实施(commit 候编排者统一门;落地审由编排者另派) |
| [0626-p77-spot2-comparator-and-s-reserve-consideration.md](0626-p77-spot2-comparator-and-s-reserve-consideration.md) | ADR-0626: T-122 P77 缺口面装载——①缺口面1 比较子落码(j=1 帧同名 2★ 直出现货经 spot2_direct_out_card 过账放行:DIY=2×基价+c_eff·E vs 现货=徽章实付,P77 §2.2 原式零新参数;p=0 帧不可评 fail-closed;席/金闸序与 1★ 同序;j=2 维持 M2b 拒禁对称重开);②缺口面3 对价载体(reencounter_window_frames 单一源+s_reserve 拒帧再遇窗累计 m6_s_reserve_remeet_frames_sum,纯遥测,让路裁决归 P56);③V_slot 维持 fail-closed(u/U_X 未标定,P77 §7【拟】#3);④A/B 载体落位测试仓(fixtures/cw_ab.py 加载/切换/对照三面+tools/cw_ab_batch.py 驱动,基线臂 monkeypatch 关比较子,对照手段不进生产代码);⑤假环境直出 2★ 通道(rules.SHOP_DIRECT_OUT_2STAR_P=0.05 校准层演练偏置,env_version 终态 v6 合流=直出+投资注入双语义(编排者二次裁决 2026-09-10;v5 短暂挂直出单语义未出版),机制锚 merge_mechanics §2.6/§2.7);Considered=生产开关否决/本批装 V_slot 否决/j=2 扩域否决/s_reserve 让路否决;验证=新锁 16 先红后绿+受影响面 99 绿+两仓 ruff 净+A/B 确认性对拍(判据锚先于跑批落盘,无数值裁决权) | 已实施(commit 候编排者统一门;落地审由编排者另派) |
| [0627-t190-press-narrowed-transition-domain.md](0627-t190-press-narrowed-transition-domain.md) | ADR-0627: T-190 批B 锁线转型域收窄落码——店侧 S_spec 买因辖域前置(P88 调和引理实现批;编号溯源:初拟 0626 与 P77 批撞号让位改 0627)——mandate.swap_transition_narrow_frame 域谓词单一源(kernel _swap_transition_domain_of 同一谓词,禁第二份合取,谓词翻转双向单一源锁)+PRESS_NARROWED_ARMS={dominance_buy,hub_option_buy}⊆买因闭集(豁免=闭集∖S_spec 结构性承载,13 键差集闭集锁,新臂入映射即红强制分类)+dominance 位停发分键 press_narrowed_transition_domain(将发射笔帧级口径,防辖域覆盖比>1 判读畸变;T-193 结算线分键候选级零扰动)+hub 位防御性哨兵独立分键(空开火面申报,判读禁并桶)+prep OpenShop 位仅登记对称观测零行为+M6 两域零触碰(ADR-0604 档2 回填出口不动)+dominance_buy_eligible docstring 双引注(ADR-0616 命题4+P88 调和引理,回滚合法依据封堵);后落批三义务申报(批序=T-166批1/T-193/T-115 先行叠加/基线重测=批D 须 post-批1+批B 码重测/replay 首发点=8 局差分重放 57 帧零分歧域外零行为面实证,D 帧样本缺挂复测批,digest 漂移改差分口径);Considered=宽口径/档1投影/门级分键口径/内联第二份合取/引开关/并入T-166批2 均否决;验证=新锁14+变异三连红还原绿+受影响面241绿+P88/P89复算7/7与9/9+ruff净 | 已实施(commit 候编排者统一门;落地审由编排者另派) |
| [0628-p76-sandwich-evidence-gate.md](0628-p76-sandwich-evidence-gate.md) | ADR-0628: T-124 P76 锁线夹界证据门落码(§5.5 夹界判据替换序数门+no_budget 预算解耦;规约态语义修正零生产行为变化)——evidence_gate 判定改 P76 §4.4 可计算夹界(θ̂_suff=clamp(E[P′]+(O⁺+F⁺+B⁺−C−D)/Δ+ε₂,0,1) 右侧全上界+ε₂ 夹界余量,P≥θ̂_suff⇒锁不劣;θ̂_nec=clamp(E[P′]−(C+D)/Δ,0,1) 右侧下界,P<θ̂_nec⇒锁劣;带内未决维持现状;suff 原始值>1⇒A-丁.2 病态域出口不进单线锁判定独立分键;闭式解<0 域 α 截 0 无条件锁=「应最早锁」结构涌现)+refresh_budget 否决分支删除仅作试验数条件(§5.5.2 锁线是配置承诺不是购买)+Δ/ε₂ 入 provisional 新槽位 V_C_MINUS_V_F/E2_CONCENTRATION_BAND 缺省 None(§7 #1 数值门禁消费,None 期「不可评」+成因分键仿 theta_unavailable,NMF §5.3 禁渗漏为否决;Δ≤0 丁.4 域外同归不可评);C 项载体钉差分口径 H_{−*}(修正 4);Considered=维持序数/零参数部分裁决三值语义/本批接线/本批 A/B(门零消费点全链结构性不可见,移交接线批同批)均否决;词表闭集 complete/sandwich_suff/band/below_nec/pathological/unavailable[成因] 替换 no_budget/p_complete_zero;验证=新锁 14 先红后绿+受影响面全绿+两仓 ruff 净 | 已实施(落地审候编排者另派,commit 候统一门) |
