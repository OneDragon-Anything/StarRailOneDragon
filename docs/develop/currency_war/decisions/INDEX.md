# CW redesign 决策记录索引(dd-NNN)

> 类名已随 2026-09-03 命名迁移更替,对照 NAMING.md(本文为带日期决策记录,类名保持当时事实,未改)。

| 编号 | 标题 | Status | 日期 |
|------|------|--------|------|
| [dd-001](dd-001-ab-baseline-gate.md) | DD-001:旧决策包删除时序——A/B 过线前不得物理删除(批 1 拆 1a/1b 两段) | accepted | |
| [dd-002](dd-002-rotation-doubling-semantics.md) | DD-002:轮岗突变语义勘误——选择后每备战阶段 100% 生效;20% 是观测频率不是机制概率 | accepted | |
| [dd-003](dd-003-cross-plane-node-count-defect.md) | DD-003:跨位面剩余节点数实现缺陷登记——`total_remaining_nodes` 对全部位面写死 9,L 换轨前必修 | accepted | |
| [dd-004](dd-004-encounter-refresh-execution-wiring.md) | DD-004:遭遇分支刷新执行链接线——决策建议字段长期无消费端,接线并登记触发源缺位 | accepted | |
| [dd-005](dd-005-buy-landing-real-empty-slot-semantics.md) | DD-005:买牌期望态落点判据对齐「真实空槽优先」——快照过期不再误停线 | accepted | |
| [dd-006](dd-006-settle-read-chain-boss-win-form.md) | DD-006:结算读点链 boss 胜局形态修复——失败页分支抢走页1 + 填充率页2 假值 + killed 兜底误判 | accepted | |
| [dd-007](dd-007-plane-fallback-endpoint-discipline.md) | DD-007:P2 回退先验端点纪律对称化——未揭晓位面回退统一取结构上端(9) | superseded(见文末 SUPERSEDED 节) | |
| [dd-008](dd-008-cost-tier-star-goal-heuristic-retired.md) | DD-008:费用档星目标启发式废弃——星目标决策权回归成型档显式要求 | accepted | |
| [dd-009](dd-009-legacy-mechanism-eviction.md) | DD-009:旧方案零引用机制整批清退——约 20 族默认关开关+影子比对残留删除 | accepted | 2026-09-02 |
| [dd-010](dd-010-equip-grid-two-state-fill-order-purify.md) | DD-010:装备区识别重构——两态位移+填充序剪枝+画面守卫外移(识别器纯化) | accepted | 2026-09-02 |
| [dd-011](dd-011-op-anim-wait-gate-retirement.md) | DD-011:操作完成自等动画规范——稳定门(gate)进入退役 | accepted | 2026-09-02 |
| [dd-012](dd-012-delta-pool-artifact-purging-p15-refit.md) | DD-012:sim 校准语料伪影治理——Δ池与粗模型直方的结算瞬时 hp=0 伪读数剔除 + p15 重拟合 | accepted | 2026-09-02 |
| [dd-013](dd-013-remove-locked-resume-enhanced.md) | DD-013:删除 LOCKED_RESUME_ENHANCED 锁死续跑逃生机制——静默假成功事故面,由 open_shop fail-closed 验证取代 | accepted | 2026-09-02 |
| [dd-014](dd-014-blackboard-decision-interfaces.md) | DD-014:黑板模式决策接口落地——decide_prep_screen/decide_shop_screen(session 签名)+ 观察写路径收编 + match 建立前移 | accepted | 2026-09-02 |
| [dd-015](dd-015-equip-drag-failure-degrade.md) | DD-015:装备拖拽失败降级——失败件局内拉黑(≥2 次跨轮记忆)+ 跳过继续不中止整批 + 后排拖点随布局档修正 | accepted | 2026-09-02 |
| [dd-016](dd-016-residual-fill-deploy-p24.md) | DD-016:cap 空槽补部署——P24 残余补部署支配接线到部署执行层(留置散牌填空,同名禁双/cap 动态门保留) | accepted | 2026-09-02 |
| [dd-017](dd-017-p3b-orchestration-takeover.md) | DD-017:W971 P3b 编排切换——开局编排接线/overlay 分发接管/纯分发器接管备战商店(EnsureShop·RunBuyPhase 退役→OpenShop 形态)/ctx 信箱退役 | accepted | 2026-09-02 |
| [adr-0431](adr-0431-hp-down-guard-battle-fact.md) | ADR-0431(历史 ADR):hp 下行守卫——「幅度 × 战斗事实」联合判据与复现确认通道;2026-09-02 判据按机制重推导部分取代,见文内修订记录 | accepted(部分取代,见文内修订节) | 2026-08-28 |
| [dd-018](dd-018-shop-cost-badge-digit.md) | DD-018:商店牌费用徽章数字识别——cost 信源 roster 查表→画面直读翻转,2星/3星直出缺口闭环(倍数 {1,3,9} 推星级;多位数两级管线,文内修订节载用户费用体系澄清后的修正) | accepted | 2026-09-02 |
| [dd-019](dd-019-p4-battle-wait-op-expected-state.md) | DD-019:W971 P4 战斗等待 op 收编(battle_loop 1f/2/3/3b/5/6 → BattleWaitOp,状态机随迁,3c 收口留主循环)+ 期望态 infra 落地(expected_state 容器/apply_op_effect 两执行面同源/覆盖点 reconcile 留证/merge_simulate 引擎/雏形分道收编) | accepted | 2026-09-02 |
| [dd-020](dd-020-series-decision-contract.md) | DD-020:序列决策契约——动作发射接口统一升序列/次(备战 decide_prep_screen 单动作→list 同构商店)+ fail-stop/帧稳定截断/空批与控制流冻结;裸 list 形状,Decision/AtomOp 层留 sim/离线 | accepted | 2026-09-03 |
| [dd-021](dd-021-board-count-underestimate-fix.md) | DD-021:board 阵营计数系统性低估修复——计数源五级优先(徽标>XY>斜杠容错>徽标小格重读>身份底座),next_tier 改基于合并后计数+注册表推导 | accepted | 2026-09-03 |
| [dd-022](dd-022-decisions-expected-paths.md) | DD-022:decisions.jsonl 期望态标记——expected_paths 字段(决策时点挂起期望摘要,recorder 汇点 session 自取全决策面一次覆盖;读端三态:旧行无键/[]=无挂起/非空=有挂起;match_archive 聚合二期挂账) | accepted | 2026-09-03 |
| [dd-023](dd-023-plane-intel-start-plane-timing.md) | DD-023:位面情报采集时序修正——接管链备战帧先定起始位面(start_plane 裁剪,已通过位面跳过)+ 详情侧读不出直接位面级结论(删切卡动画重试等待)+ 用户定值等待(开屏 3s/切卡 2s) | accepted | 2026-09-03 |
| [dd-024](dd-024-gate-module-retirement.md) | DD-024:gate 模块退役——消费清零后删除 cw_observation_gate(活常量迁驻 cw_observation/cw_screen_prep,死基线写删;等待语义=判据化等待+外循环重判) | accepted | 2026-09-03 |
| [dd-025](dd-025-frame-horizon-vgap.md) | DD-025:R1 刷新门 V̄ 比较项换帧级 horizon 现算(修 A)——rounds_left_est=5 常数退役出 cw4 消费链,旧静态注入 24.7=r=5 特例;cw_registry 共享字段零触碰(decision_v2 冻结基线) | accepted | 2026-09-04 |
| [dd-026](dd-026-r2-interest-floor.md) | DD-026:R2 预算门息线 floor 落码(修 R2)——刷新门预留组装补位 P40 规范口径(g*+ρ),b_target 零参退化退役出刷新消费位;跨档破线刷无 L 旁路(生存面硬下界) | accepted | 2026-09-04 |
| [dd-027](dd-027-m7-equip-emission-gate.md) | DD-027:M7 装备转移发射门——持有面谓词换变换面谓词(m7_wearable_exists,owned 全量含工具件致非空即发永真)+ 备战期装备闩 cw4_m7_equipped_phase(实机 1-6 RunEquip 备战环活锁 204 帧定谳;空批出口 StartBattle 封死根因) | accepted | 2026-09-04 |
| [dd-029](dd-029-screen-rename-merged-regen.md) | DD-029:画面改名只改分文件漏再生 merged——运行时加载源漂移致「选择伙伴」遮罩下部署死局(merged 新鲜度锁 + AREA_NO_CONFIG 显式告警[框架层,编排者预批准] + cw_loop 分发锚 iter1 预检 + 事故帧路由 fixture;handler 归属澄清=CwScreenPartner 非专家邀请函) | accepted | 2026-09-04 |
| [dd-030](dd-030-no-progress-guard.md) | DD-030:备战环无进展守卫——环级活性不变量(连续 3 环同动作签名+状态指纹零推进→存证停机;闩模式升维替代第 4 个逐位闩,替换旧 PREP_STALL 留证线;三历史卡死签名重放全触发) | accepted | 2026-09-04 |
| [dd-032](dd-032-p56-t1-buy-face-wiring.md) | DD-032:P56 可变现息线下界 + T1 凑息卖语义重写落码(姊妹缺口收口)——s_reserve:=g*−Σ活期退金投影入买面两消费位;凑息卖改金位触发+目标量止盈,T_SEARCH_A 布尔门退役;P57 双读法参数化生产默认读法②;分键遥测四字段;双读法臂 A/B 三门达+方向预言破线 −23.6% | accepted | 2026-09-04 |
