# ADR-0462: 规范入口序列「先清场、再识别、后动作」+ 备战观测逐阶段字段规格

> **引用勘误(2026-09-04 ADR 存量 review)**:`.debug/` 归档 → 本目录(decisions/)同名 ADR。文内出现处按此对照读取。

## 状态

accepted(2026-08-30)

## 背景

用户 directive:「商店开态不需要读取血量,要分清每个画面要读取的信息」,及两条主干级规范:
①战斗结束进新节点备战,第一步应关闭所有 overlay 拿干净备战画面做全量识别基线,再进后续动作;②overlay 帧只识别「该 overlay 决策需要的内容」,禁止跑备战画面字段识别。

现状违反该规范的实证(设计档 `.debug/temp/currency_war/w609_screen_field_spec/DESIGN.md`,fixture 实测):

- **识别与 overlay 状态交织**:开店后整条全字段识别链照跑——hp 死读(商店开态结构性遮挡,6fc1fd4c 已跳)、node_type 死读(节点行被遮恒 None,shop.py 自己用 session 拷贝兜住,OCR 却每帧照付);
- **同帧重复管线**:deploy cap 与 deployed_count 对同一「X/Y」指示各跑一条完整 paddle 管线(fixture 42–182ms×2/帧);
- **纯留证读常驻**:streak 在 session 已有结算真值时每帧仍 OCR(79–93ms);
- **动作期与基线期不分**:难度/连胜/部署数等整轮不变的字段在开店动作期反复重读;
- **冲突噪声主源嫌疑**:overlay/过渡帧跑备战识别 → reader 失读/约束拒 → obs_conflict 逐帧留证(探针 3 张 fixture 数秒 16 行;每局 ~105 行噪声),且证据行无阶段归属,无法按「规范是否落地」归零判定。

单次 `read_game_state` 冷帧实测:开店帧 2285ms / 干净备战帧 ~1300ms;每商店轮被调 3–5 次。

## 决策

1. **规范入口序列(流程面)**:备战环入口增加 P0 清场前置段(`PrepDirector._clear_entry_overlays`)——逐屏探注册表 `ENTRY_OVERLAY_CLOSE`(画面名→关闭按钮 area,锚判定走现有 screen 体系),命中即点关闭,拿干净备战画面再进 gate/识别。只收「无决策语义的弹窗/面板」;投资环境/投资策略/选择伙伴/盛会之星/祈愿试炼等交互 overlay 有专属 handler(关闭即丢决策内容),不进注册表,仍走既有 event_overlay bail → 外环消化。fail-open:任一异常静默返回(=现行为,gate 帧态门继续兜底)。
2. **逐阶段字段规格(识别面)**:`read_game_state(ctx, screen, phase=None)` 增加阶段参数;规格单一源 = `cw_observation_gate.PHASE_FIELD_SPEC`:
   - `prep_clean`(P1 干净备战期,gate PROFILE_CLOSED stable 帧,每节点一次基线):全量字段 + **hp 真读主路径**(收编 6fc1fd4c 先例为规格单一源:'hp' ∈ spec 才 OCR,否则一律对账沿用,不留两处门控);
   - `prep_shop_open`(P2a 开店动作期):仅买牌决策所需(gold 稳定门/牌面/概率条/level/xp/升费/board/bench_full);hp 与 node_type 结构必空,cap/deployed/难度/连胜以 P1 基线或 session 为准;
   - `battle_or_transit`:仅位面轮次(消费面=恢复对局检测,只需 plane/round);
   - phase=None = 全量路径 = 现行为逐行不变(存量测试零波及);未注册阶段名 → warning + 全量(fail-open,未知态不猜)。
3. **paddle 合并单读**:阶段 gate 路径用 `resolve_paddle_pair` 一次解析产出 (X, cap),cap 过抽出的防抖核 `_debounce_cap`(与 `read_deploy_cap_debounced` 单一源,语义逐行一致);phase=None 全量路径保持两读不变。
4. **噪声判定位**:`cw_observe` 增加观测阶段上下文(`set_obs_phase`/`current_obs_phase`),read_game_state 入口置位/结束清位,obs_conflict 证据行带 `obs_phase` 键。归零判据:**P0 清场期/overlay 期来源的冲突行 ≈ 0**(这些阶段整条备战识别链不跑);P1/P2a 合法冲突 ≤ 个位数/局。
5. **调用点接线**:shop.py 买前/主环→`prep_shop_open`、买后收起重估→`prep_clean`;battle_loop 恢复对局检测→`battle_or_transit`(on_match_start 为 no-op 已核);run_supply_node detour 快照→`prep_clean`;遥测存证(recorder/observe_full)保持全量。

## 影响

- 开店动作期单次观测冷帧 2285→1082ms(−53%,fixture 实测,工具 `cold_compare_probe.py`);干净备战期与全量持平(基线读即全量语义,设计如此)。
- 遥测可按 obs_phase 分类统计冲突行,规范落地效果可判定。
- 跳过集全部有消费面证明(DESIGN §5.2):hp→reconcile 沿用;node_type→shop.py session 拷贝;cap/deployed/难度/连胜→P1 基线/session;牌面/概率条→该阶段物理不存在。
- Snapshot 契约对齐:跳过字段落 None/空(「空容器=观测真值」分义不变),`classification.name` 与阶段键同键域,DirectorV2 observe 端口可直接复用。

## Considered Options

- **参数化 gate(选定)vs 拆分多函数(read_prep/read_shop_open/…)**:拆分复制对账/hp 三层等共享段,漂移面大;参数化在单链内逐段 gate,phase=None 精确保持现行为,新阶段渐进接线。
- **自动关闭交互 overlay vs 注册表只收无决策语义面板(选定)**:交互 overlay 的关闭重进由 handler 承载且各有状态语义,自动关闭引入重入竞态;规范收益(干净帧识别)对弹窗类已成立。
- **read_game_state 内部自判阶段 vs 调用点显式传(选定)**:调用点都刚跑完 gate,锚命中即阶段,零额外识别;内部自判需再付锚 OCR 且可能与调用点的 gate 判定不一致。
- **金稳定门收窄到花金决策点**:v2 设计曾列,本批不做(行为面敏感,单独立项)。

## 验证

- 新锁 13(test_cw_w609_phase_field_spec):阶段 gate 生效(mock 计数,读取集/跳过集精确断言)、phase=None 全量基线锁、未知阶段 fail-open、hp 单一门控源级锁、paddle 合并等价、obs_phase 落盘/复位、注册表健康(yml area 存在性+交互 overlay 排除)、清场段接线与 fail-open。
- fixture 消费面对拍:三帧全量 vs gated 读取集字段逐一同值(hp DIFF 为预期改进:prep_clean 真读 84/73 vs 全量路径沿用 100)。
- CW 域全集 + ruff;实机验证挂账:下局起相邻决策间隔对照(基线 14–36s)+ obs_conflict 按 obs_phase 的噪声归零判定,数据回填 DESIGN。

## 遗留

- 金稳定门最坏 +1.5s/次的收窄(只在花金决策点过门)单独立项。
- 清场注册表目前 6 屏;新 overlay 出现时按「有登记关闭按钮且无决策语义」判据补表。
- 子态注册表(W571 阶段1 批1a)落地时,PHASE_FIELD_SPEC/ENTRY_OVERLAY_CLOSE 随注册表收拢(键域已对齐,纯搬家)。
