# 05 观测、对账与遥测

> 「读画面→GameState→对账→反馈→落盘」的观测闭环。本篇:obs 模块家族 / cw_reconcile / cw_performance / cw_telemetry / 日志格式。核心哲学:观测驱动非预测驱动(README §哲学)。

## 1. 观测模块家族(按屏分工)

| 模块 | 屏/对象 | 产出 |
|---|---|---|
| `cw_observation` | 备战屏 | `read_game_state` → GameState(gold/hp/level/board/shop/bench/deployed…) |
| `cw_obs_core` | 共享基础设施 | screen_info 区域读取 + OCR helper |
| `cw_observation_gate` | 稳定门原语(ADR-0213) | `wait_stable_frame`:时间稳定窗(屏判定+per-area 像素指纹首尾一致)+ 三 profile(关态/开态/弹窗态);gate 是「等画面稳定」的单一实现(旧 sleep/单锚/轮询 已删,ADR-0216);末帧供调用方复用(全图 OCR 按 id(image) 缓存贯穿);提速=融合终裁(ADR-0264):骨架 `fast_confirm`(锚命中后确认轮纯 CV 只比指纹、变化即回锚定,min_stable_s 真实测量;False 回退旧完整门)+ 加速器(segment='op_settle' 操作段 2s 预估等待=指纹基线重置点,再快 poll 确认窗)+ `preset_stable_baseline`(overlay 验关成功帧预置基线,首锚消费,仍须锚+指纹一致);不做纯信任放行 |
| `cw_observe_full` | 组装层(ADR-0213) | `observe_full`:一次全面识别(state/board/bench/deployed/hp/gold/节点行/shop;含 substate 与 gold==0 重读),director 与 recognizer 共源 |
| `cw_identity_obs` | 备战屏视觉身份(SIFT,非 OCR) | bench/deployed 角色身份 |
| `cw_node_obs` | 节点选项 overlay | EncounterOption/SupplyOption/MegastarOption/PartnerOption |
| `cw_settlement_obs` | 结算屏 | 战后小队 HP(观测回路输入;失败屏 hp=0 conf=1.0) |
| `cw_briefing_obs` | 开局简报屏 | 敌人词缀 + 位面首领 + 基础敌难 |
| `cw_node_reader` | 备战顶部节点行(纯 CV) | 节点序列类型(奖励/战斗/遭遇/补给/巨星/boss…) |
| `cw_observe` | 可观测框架 | 统一日志 + 截图 |

**读取互斥**:gold 只在 shop 开态、HP 只在关态可读——由 EnsureShopOpen/Closed 动作显式管理,框架校验读取前置态。设计原则:签名 + 失败语义(字段 OCR 失败 → None/上回合值 + confidence=0,不抛错)+ sanity bounds(越界字段本回合作废防级联)。

**部署数与羁绊计数是两个量(ADR-0417)**:board(`_board_pairs`/`board_from_tracked`)是**羁绊计数**(多阵营角色重复计),不是部署角色数;部署数对齐/重建目标 = 舞台 paddle「X/Y」的 X(`read_deployed_count`,几何上不含底部商店行/备战栏;paddle 读不到 → 跳过对齐,宁缺勿造)。board 双源裁决:computed(tracked 身份全集)做底座,可视行徽标(左栏 OCR)在**备战帧**(`is_prep_like_frame`)且徽标解析 honest 时优先覆入(徽标=画面事实);overlay/动画帧徽标与 computed 均不可靠 → 不裁不覆只留证,等备战帧自愈。paddle X 的 OCR 已知形变(人形图标并入 X 成前缀 '1')由图标前缀守卫归一。

**升星预览✦(ADR-0416)**:`read_shop_cards` 每张牌附带 `merge_preview`(`cw_identity_obs.read_merge_preview`)——商店牌 art 顶部✦数 = 已持同名同星副本份数(买第 3 张即 3合1),是 bot tracking merge_progress 的视觉印证(观测冗余信号,`ShopCard` 字段注释载语义)。0 为双义(真无副本 ∨ fail-silent 读不到,模板缺失即恒 0),消费方按「未观测」对待;评分层尚未接此信号(decision_v2 merge_progress 走 bot tracking),sim 不建模。

**合成特效帧态门(ADR-0420)**:star 读数(`read_star`)在 3合1 星爆动画/拖拽合成过渡窗内会采到「已合成」的中间帧——旧值才是真值。`cw_identity_obs.is_merge_effect_frame` 是全帧行为判定门(纯 CV、无 ctx 依赖),双签名任一命中即为特效帧:①星爆粒子签名=前排棋盘带(`_MERGE_EFFECT_FRONT_BAND`)内严橙金窗口(复用升星预览✦的 `_PREVIEW_GOLD_LO/_HI`)连通域面积过 `_MERGE_EFFECT_COMP_MIN_AREA` 者计数达 `_MERGE_EFFECT_GOLD_MIN_COMPS`;②满席警告横幅签名=`_BENCH_FULL_BANNER_RECT` 带内红主导(R−max(G,B) 过 `_BANNER_RED_DOM_DIFF`)占比达 `_BANNER_RED_DOM_MIN`(拖拽合成过渡)。挂点在 `cw_reconcile.reconcile_tracking` 的采新确认分支前置——特效帧保旧读数且防抖计数**冻结不推进**(非清零:门后干净回退帧仍可构成新确认);门漏检退化为无门的原防抖行为,判据异常返 False 不拦。

**deploy_cap 域外双帧一致采信(ADR-0420)**:`read_deploy_cap_debounced` 的防抖域(`|cap−level| ≤ `_CAP_DIFF_MAX`,见 `cw_back_layout`)之外不再一律拒绝——域外值重读一帧,两帧一致且落在绝对上界 `DEPLOY_CAP_ABS_MAX`(前台+后台实拍板面上界)之内即采信并 obs_conflict 留证;三类恒拒:**cap<level**、**超绝对上界**、**两帧不一致**(瞬时误读族防线不降级)。域内直采路径不变。

**规范入口序列与逐阶段字段规格(ADR-0462)**:观测按「先清场(P0 零业务识别,环入口 `_clear_entry_overlays` 点关闭注册表 `ENTRY_OVERLAY_CLOSE` 中无决策语义的 overlay)→ 干净备战期(`prep_clean`,全量基线,hp 真读主路径)→ 动作期(`prep_shop_open` 仅买牌决策所需;overlay 帧只读该 overlay 决策内容)」组织;逐字段 gate 单一源 = `cw_observation_gate.PHASE_FIELD_SPEC`(`read_game_state` 的 `phase` 参数;None=全量=无阶段语义;未注册阶段 fail-open 全量+告警)。hp 读取门唯一来源 = spec('hp' ∈ spec 才 OCR,否则 reconcile 沿用,ADR-0282 语义不变);paddle cap/count 在 gate 路径合并单读(`resolve_paddle_pair`,防抖核 `_debounce_cap` 单一源)。冲突证据行带 `obs_phase` 阶段键——判读按阶段分类:清场期/overlay 期来源的冲突行应 ≈0(这些阶段不跑备战识别链),>0 即有调用点在错误阶段跑全量识别。

## 2. cw_reconcile:对账公共层

tracking(内存 dead-reckoning)vs 读到的真值,多层校准(L0 内存跟踪 → L1 全图 OCR 对比 → L2 不一致兜底递进[裁剪再识/点击探查/定向重读] → L3 递进到底仍不一致 = 上游出错信号,保守恢复不硬猜)。环入口对账一步;单笔动作后验证互补回合总账。

## 3. cw_performance:观测反馈层

- **RoundOutcome(双侧观测)**:自身侧(hp_after 差分 + 置信度)+ 敌方侧(击杀/伤害,可观测时)+ comp_tag + intentional_fold 标记。
- **PerformanceTracker**:`recent_hp_loss_trend` = **归一化**掉血趋势(hp_delta / expected_drop(node_type),全部样本进同一条 trend——归一化而非按节点类型完全划分:消除「打 boss 掉得多=我弱」偏差又不丢样本/不震荡);intentional_fold 排除(防故意输污染);comp_tag 过滤(pivot 后旧 comp 降权);低置信不进 trend;冷启动(差分样本不足)→ None,调用方退静态先验。
- **comp_viability**(评已 commit 阵容):先验(成型度/装备/机制)× 先验权重 + 观测 × obs_weight(随观测轮次上升);评 candidate 用纯先验 comp_prior(双签名,02 §2)。
- **死局检测**:HP 低 + trend 高 + 下节点锁不住血三门。

## 4. cw_telemetry:决策迹采集

三路 jsonl(`.debug/temp/currency_war/replay/`):**outcomes**(每节点结算;含板深快照 board_before/bench_count,r339)、**decisions**(每决策点 state 快照 + 候选分 + 选择 + 理由;live 扩容字段:active_strategies / dp_posture 影子 / ledger_fingerprint / megastar·encounter·supply pick)、**runs**(局摘要,含免费窗口登记字段)。默认 `enabled=False` 门控,config `debug_telemetry` 一开全收。外生事件(节点转换/弹窗)与执行失败事件各自落盘(能力画像/预案触发频率语料)。

**查询端(判读单一源,CLI)**:`python -m sr_od.application.currency_war.cw_telemetry query --recent N [--run ID] --view rounds|supply|anomalies|tiers|planexec|hp|economy|all`——rounds=逐轮 hp/gold/买/board;supply=全波牌面 vs 购买(配方件标★,refresh 波不丢);tiers=羁绊激活档+角色构成(星级)+装备分配三维同屏(ADR-0229);anomalies=异常标记(金滞留/单轮掉血过深/plan_error;阈值常量 `ABN_*` 见 cw_telemetry);hp=掉血×板深分解(与 sim hp_events 同构,r339);economy=金轨迹/滞留轮标记。**`checks` 子命令**(ADR-0245):`cw_telemetry checks --recent N`——生产局秒级自检(栈判别:v2 栈跑 coldstart 检查,default 栈跳过;违规带 run_id 溯源)。**`--sim-batch BATCH`**:查 sim 批次账本(目录结构与生产 replay 同构,视图零分叉;board 系字段恒空、ts=轮序号等 sim 语义差异见 `--help`)。复盘新需求 = 新视图/查询参数,不写一次性脚本。**判读方法论(看什么/三维/保真位先行)单一源 = `sr-od-currency-war-dev` skill 的 telemetry-reading。**

**采集器分工**:decisions/outcomes/runs 三路 jsonl 由 telemetry 采集(plan 视角);`cw_match_recorder` = **画面真值旁路采集器**(识别器视角:bot 实跑/人类手打对局的关键帧结构化提取,OCR 锚词门控+内容哈希去重;人类演示对拍语料与「计划 vs 实际」对拍用,§5)。

**回放语义**:replay = 把录制的 state 喂给策略比对决策——**回归测试与调试工具,不是胜率裁判**(obs 序列是当时策略产生的,换策略后游戏演化路径本就不同;真实 A/B 必须实机,07 §replay)。

## 5. 离线分析工具(消费 telemetry / replay)

- `cw_replay`:决策回放 harness(对历史局 GameState 快照重放 decide_prep,`--diff` 与当时实跑 actions 对比;支持 line/default 双策略,ADR-0231);
- `cw_weight_search`:CEM 权重搜索(防退化三件套);
- `cw_divergence_stats`:影子 DP 姿态 vs 生产姿态分歧频率(人机问询触发门数据源);
- `cw_match_recorder`:对局采集器(§4;离线重放模式可对历史截图目录重跑提取)。历史局审计通道 = decisions.jsonl(写路径在 telemetry recorder;live vs 旧 v1 plan 的对拍器已随 strategy_v1 退役,ADR-0477)。
- `telemetry/match_archive`:按局存档(ADR-0486)——终局旁路把一个游戏局(可跨多个 run 段,game_id 按段首帧继承)装配为自包含档案 `replay/matches/match_<game_id>.json` + `matches/index.jsonl` 摘要索引。触发 = 局终钩子(battle_loop 调 `assemble_pending`)+ CLI `assemble [--game]` 兜底;查询 CLI `--match <game_id>` 直读档案(切片物化后复用同一套视图函数,输出与 `--run` 一致),`--recent` 读索引;水位线实现旧数据不回填;写盘 tmp+rename 原子。保留策略(记账未实现):index 永久,档案超窗口可删留行、可从 replay 原始流重装配。

## 6. 日志格式标准(可检索;单一源)

CW 实机运行/识别加结构化日志,**两族前缀**(识别/观测层走 helper,流程/模块层直打):

**A 族(识别/观测层,经 `cw_observe.cw_log` helper)**:

- `[cw][op][step][target] fields` —— **普通**(常规识别结果 / 观测流程);`step`/`target` 可空,退化形态 `[cw][op] fields` 合法且常见
- `[cw!][op][step][target] fields` —— **需关注**(漏检 / 顺序异常 / UNKNOWN 未建档画面 / 观察冲突;`attn=True`)

字段:`[op]` 模块(read_equipped/read_equips/deploy/equip_all/recognize 等)/ `[step]` 节点 / `[target]` 对象(slot=前排-1 / screen=备战 / char=飞霄);状态标记 `MISS=[名(val)]`(漏检)/ `UNKNOWN screen=`(未建档)/ `FOUND=`(找到);`| shot=<名>` 配对截图(定位画面)。打点直接调全局 `cw_log` / `cw_shot`(`cw_observe`),**不透传 logger 参数**。

**B 族(执行/策略流程层,模块内直打)**:`[cw-<tag>]` 前缀,一模块一 tag——`[cw-deploy]`(deploy_bench)/`[cw-equip]`(equip_all)/`[cw-loop]`(battle_loop)/`[cw-pivot]`·`[cw-target]`(策略选线)/`[cw-director]`·`[cw-prep]`(备战编排)/`[cw-shop]`·`[cw-plan]`(买牌规划)/`[cw-entry]`·`[cw-exit]`(进出对局)/ handler 各自 tag(`[cw-partner]`/`[cw-env]`/`[cw-strat]`/`[cw-box]`/`[cw-sphere]`/`[cw-briefing]`/`[cw-wish]`/`[cw-megastar]`/`[cw-supply]`/`[cw-encounter]`/`[cw-armbox]`/`[cw-clean]`)及基建 tag(`[cw-hook]`/`[cw-alloc]`/`[cw-strategy]`/`[cw-drag]`/`[cw-settle]`/`[cw-snap]`)。普通用 info;**需关注用 `log.warning`**(同前缀)。

**检索口径**(方括号在 grep 里是字符类,须转义或用前缀匹配):

- 全 CW(两族通吃):`grep "\[cw"` —— 注意 `grep "\[cw\]"` 只匹配 A 族,**检索不到 `[cw-…]` B 族**
- 漏检:`grep "\[cw!\].*MISS"` / 未建档画面:`grep "\[cw!\].*UNKNOWN"`
- 某模块流程:`grep "\[cw-deploy\]"`(tag 见上)

落点:`read_equipped` MISS(装备 below 漏检)/ `read_equips` 顺序异常(owned 栏识别到后面但前面漏;布局:第一行独立[冶金炉多了左堆],下面从上到下、从右到左,跳格=前面漏检)/ `recognize` UNKNOWN(未建档画面)。logger 统一走框架 `log_utils.log`(全局;`cw_log` 即其封装)。
