# 设计对抗报告·第三轮（收敛判定轮）

> 攻击对象：本目录 design.md（第二轮修订版）/ landing.md / README.md；权威源 = `game_state/node-derivation.md` §3.1、`assets/game_data/screen_info/currency_war_boss_briefing.yml`、代码实况（符号锚均在 `src/sr_od/application/currency_war/` 下，2026-09-20 工作树，逐处直调复核）。前两轮已处置发现（F1-F7 / R1-R5）不重报；本轮主任务 = 修订复验，次任务 = 新地面攻击。

## ① 结论行

**阻断 0 / 应修 1 / 低 1 / 零新发现（B 部分地面①②③④四个攻击面中三个零命中，一个命中即下述应修）**。

两轮修订（R1 双条件门 + v=None 行、R2 现役事实改写、R3 证据集同源条款）经代码逐处核验**全部成立**；新地面攻击在 landing 试读、共存窗口、行为申报、恢复局组合四个面上仅命中一处**范围划界缺口**（gs.node 观察镜像写端未被「漏斗退出节点域」的边界枚举覆盖）——不影响推进门模型本身的正确性，属切换批执行前必须补的文字边界，不构成阻断。

## ② A 部分：修订复验（逐条）

### R1（双条件门 + v=None 行 + 锁定臂表述）——**成立**

代码事实复核：

- `Field` 缺省 `source: FieldSource = 'observation'`（`kernel/cw_game_state.py:450`）、`node_ord: Field[int] = field(default_factory=Field)`（`:2383`）——新容器现态确为 `(None, 'observation')`，与 design §2.2 value 守卫论证的前提一致。
- `effective_node_ord` 双源皆 None 返 None（`:3138-3140`）——「value=None 时 candidate 无定义」的论证成立。

**E1-E18 全流转穷举（node_ord 的 (value, source) × 门判定 × candidate 可计算性）**：

| # | (value, source) 现态 | 到达场景 | 门判定 | candidate | 结论 |
|---|---|---|---|---|---|
| 1 | (None, observation) | 新容器/开局链（E1-E3 零上报零锚定）/恢复局锁定臂首战（`cw_loop.py` 锁定分支直出不经备战 op）/relaunch 残留结算屏首确认 | value=None → **挡** | 不可计算（effective=None） | ✓ 无 None+1 形态 |
| 2 | (v, observation) | 任一锚定后（E4 首锚定/E9 翻锚定/补推后） | **放行** | max(v, hist)+1 可计算 | ✓ |
| 3 | (v, logic) | 上报后未锚定（E7/E10/E11/E12/E13 确认后、下一锚定前） | source=logic → **挡** | — | ✓ 同节点重复上报结构挡 |
| 4 | (None, logic) | —— | —— | —— | **不可达**：原语写值 = candidate（gate 放行 ⇒ effective 非 None ⇒ 恒 int），logic 写端无 None 路径 |

四组合闭合，无第五组合。逐边走查（新模型）：E1/E2/E3/E5/E6/E15/E16/E17/E18 零上报零锚定，态恒 #1 ✓；E4 v=None 行建 1 ✓；E7/E8（快弹窗：确认上报 #3 → 弹窗 → 选卡 → 备战帧锚定 R==v 翻 #2）✓；E9 R==v 翻 ✓；E10 自动弹（结算确认证据=补给锚 → report #3 → 补给屏节点条 R==v 翻 #2 → 确认放行）与 divert（备战帧锚定 #2 → 补给屏 R==v 同值行 → 确认放行）两形态闭合 ✓；补给节点条误读旧值 R<v → 丢弃留证 → 确认被 source 挡 → 下一备战帧 R>v 补推，各节点 tick 恰一次（report 已 tick k+1、补推 tick k+2，`advance_node` 序相等去重无双发）✓；E11 miss 自愈同构 ✓；E12 奖励关确认（证据=boss 锚）→ report #3 → 简报 op 类型直定（见 R3）→ boss 备战帧 R==v 翻 ✓；E13 boss 确认（证据=位面过渡 OCR，白名单内 `cw_screen_battle_wait.py:288`）→ report (p+1,1) → 下位面备战帧 R==v 翻（非 R>v，序连续）✓；E14 恢复局三形态（备战帧先行 v=None 建值 / 弹窗先行无锚无报消化后补推 / 锁定臂首确认被 value 守卫挡 + 战后备战帧 v=None 行重建）——**锁定臂机制表述修正（§2.2「行为结论不变，机制表述以本段为准」）与门定义一致**，无 skew ✓。对抗探针（#2 态下 settle op 陈旧帧重入双推）：重开 gate 需 R==v 锚定 = 游戏确实已在新节点，而旧结算屏不可见 ⇒ 证据门挡；同节点重报被 #3 挡——「结构上不可能二推」主张在四组合全域成立。

### R2（REGISTERED_ACTORS 退役 → 现役事实改写）——**成立**

`_validate_sig`（`kernel/cw_game_state.py:353-361`）现值只校 `sig.family ∈ allowed_families`，docstring 明文「actor 仅作遥测/台账行的动作身份标注，不设白名单闸」；design §2.3 与 landing 3.1⑤ 已按此改写（「trigger op 类名/自由命名标识作 actor，无注册面」），全仓 grep `REGISTERED` 零命中与申报一致。修订与代码事实吻合。

### R3（证据集同源条款）——**成立（论证链闭合，同源同锚核码证实）**

条款成立的关键推理「简报锚命中 ⇒ 证据命中」逐件核码：

1. **白名单侧**（`operations/cw_screen/cw_screen_battle_wait.py`）：boss 路径条件 = ①模板锚 `('货币战争-BOSS简报', '标识-阵营徽记')`（`COMPLETION_ANCHORS:266`）∨ ②片段判别兜底 `is_boss_briefing_texts(read_ocr_texts(...))`（`:283-285`）∨ ③位面过渡全帧 OCR「点击空白处继续」（`:288`）。
2. **分派侧**：外循环 0p 分支（`operations/cw_loop.py:1546`）经画面识别 `name == '货币战争-BOSS简报'`，该屏 id_mark 组合 = 「提示-点击空白处继续」（OCR）∧「标识-阵营徽记」（模板）（`assets/game_data/screen_info/currency_war_boss_briefing.yml:5-16,33-44`，id_mark 全命中才算精准匹配）——**分派 ⇒ 徽记锚命中 ⇒ 白名单条件①**；位面过渡身份排他接管分支（`cw_loop.py:1571`）以 `is_boss_briefing_texts` 为接管判据 —— **接管分派 ⇒ 白名单条件②**。两条分派路径的判据均被白名单条件覆盖（白名单条件集 ⊇ 分派判据集），「同锚同源」成立——分派锚不是异锚，条款的核心前提没有断裂。
3. **时序侧**：结算确认 op 等待语义 = ③段同 helper「白名单命中即返，无独立短超时」（design §2.3），出口 = 白名单命中 / 终局锚 / fail（unknown bail / 轮次上限，`wait:708-723` 结构）。故「流转真发生至简报屏 ∧ op 存活 ⇒ 徽记/片段锚必被观测 ⇒ 上报先行于分派」；「证据 miss 且 op 退出」只能是 fail ⇒ run 失败 ⇒ 外循环无后续分派 ⇒ 类型直定无从触发。「锚识别失败 ⇒ 简报 op 同样不被分派」经第 2 点的包含关系成立（徽记 miss ∧ 片段 miss 排除两条分派路径）。**「证据 miss + 流转发生 + 简报 op 被分派」三方组合不可达，条款闭合。**
4. 附核：boss 简报帧先被白名单③（位面过渡 OCR）误吞的可能被分支序排他（`:286-287` 注释明示 boss 锚先行）——任一命中即上报，不产生错序。

### F1（锚定写端迁 CwScreenPrep 观察 node）——**成立（维持二轮复验）**

回执可达性（`cw_observe_full.py` → `GameStateReadReceipt` 携带 plane/round_num；`cw_screen_prep.py` 观察 node 可取回执）与 R4 表述修正（`cw_loop.py:598` 仲裁路径 prep 读在锚定之后）均与代码吻合，本轮无新反例。

### F2（推进生效原语 + prep_frame 遗迹删除）——**成立（维持二轮复验）**

`_tick_effect_boundary_impl`（`cw_game_state.py:3269-3280`）函数体不读 `prep_frame`；`settle_node_boundary_gold` 全仓仅 def + 注释（`cw_effect_inventory.py:1127`）零生产调用；漏斗尾段 `observe_screen_context:3090-3093` 仍传闸参 = 待删遗迹，design 申报与实况一致。原语「来源由调用方定（action=logic / 补推=observation）」参数化与 R1 门语义互洽（#3→#2 翻转链依赖此参数）。

### 修订后 design 内部一致性——**无打架**

处置表 v=None 行 ↔ 原语段（锚定补推 source=observation + 漏 tick 即永久漏发论证）↔ 写法边界段（不经通用 observe()、三分支显式处置）↔ 触发点段（trigger 封闭集 / 证据 miss 不上报）↔ §2.5 共存画像（3.2 后 source=logic 门挡 / 3.3 后部分放行，与 `Field` source 语义逐段对上）↔ §2.7 九条申报，交叉引用一致。candidate 表述（§2.2「max(value, hist)+1」= §2.3「effective_node_ord + 1」）同义。

## ③ B 部分：新地面攻击

### B1（应修）「漏斗彻底退出节点域写入」边界未划出 `gs.node` 观察镜像写端——字面执行 3.5 会拆掉 plane/round/hp 读口基底，保留则该句字面为假

- **位置**：design §2.4-1（「漏斗彻底退出节点域写入（上下文对/`top_bar_raw` 观察层保留）」）/ §2.7-5（「recorder 录帧副作用消失（漏斗彻底退出节点域写入）」）；landing 3.5（「漏斗 `observe_screen_context` 瘦身收口（上下文对/`top_bar_raw` 观察层保留，**节点域全退**）」）。
- **攻击**：观察漏斗内现存**两类**节点域写入：①退役范围内的 node_ord 推进腿 + 效果尾段（`observe_screen_context` 内 `_derive_node_*` 调用与 `:3090-3093` tick 调用）——design 明确退出；②**未被 design 任何文字提及的 `gs.node`（NodeKey 观察镜像）写端**：`obs/cw_observation.py:2575/2582`（读链 phase_round 全阶段必写，kind 继承合成）+ `observe_screen_context` 内留驻的商店查链类型写（`:3080-3089` 经 `_write_derived_node_type` 写 `gs.node.kind`，类型机制本迭代明示不动）。`gs.node` 字段名即「node」，字面读「节点域全退」会把 ② 一并拆掉——而 `gs.node` 是 plane/round/hp 读口的基底（`cw_game_state.py:3863-3880` `plane_of/round_of/hp` 均从 `gs.node.value` 派生）与现役消费点（`_defeat_latch_by_secondary:659`、`_shop_panel_type_target:3153-3157`），拆掉 = 决策层坐标全断。反之若实现者正确保留 ②，则「漏斗彻底退出节点域写入」「recorder 从此零节点域副作用」两句**字面为假**（recorder 经漏斗仍写 `gs.node` 镜像，仅推进域副作用消失）——§2.7-5 的验收主张按字面不可判定。design 全文（含 §2.5 退役清单）对 `gs.node` 镜像零提及，正本清单（landing）也无对应行。
- **依据**：`obs/cw_observation.py:2567-2587`（漏斗内 gs.node 写端）、`kernel/cw_game_state.py:3080-3089`（留驻类型写）、`:3863-3880`（读口基底）、`assets/.../` 无关；design §2.4-1 / §2.7-5 / landing 3.5 原文。
- **要求**：design §2.4-1/§2.7-5 与 landing 3.5 把「节点域」显式限定为「node_ord/node_hist_ord 推进域」，并增一行申报：`gs.node`（NodeKey 观察镜像，plane/round/kind）与商店查链类型写**留在漏斗**（观察层，非推进域；recorder 对其的写入属观察镜像非逻辑态副作用）；正本更新清单补 `node-derivation.md`/`fields.md` 对应句。纯文字边界修正，不动模型。

### B2（低）landing 3.2「②段改调本 op」的职责切分留两处未声明的归属

- **位置**：landing 3.2 范围句 / design §2.3 触发点 1。
- **内容**：②段现结构（`cw_screen_battle_wait.py:731-766`）除点击与 M39 外还内嵌：结算读点等待 1.5s + 重截、`_record_round_outcome`（入环/遥测）、`rounds_done` 指纹计数（`_st` 状态机字段）。op 化后这些留 battle_wait ②段还是随迁 op，design/landing 未声明——实现者可自行决定且两种都能跑，但 `settle_stay`/`rounds_done` 计数归属影响「重入帧不重复上报」判据（3.2 完成判据）的断言落点；另 op 内部等待轮次预算与 battle_wait `node_max_retry_times=400`/unknown bail 的关系未指定。建议 3.2 范围句补一句「读点/入环/计数留宿主 ②段，op 只辖点击+长按兜底+证据等待+上报」。
- **依据**：`cw_screen_battle_wait.py:731-766`；landing 3.2 原文。

### B-① landing 3.2/3.3/3.5 试读（凭阶段范围句 + design 引用节能否直接写码）

3.3/3.5 除 B1/B2 外可直写：3.3 的 until 插入点、调用点（`cw_overlay_pick_action.py` 确认链）、area 建档流程、两形态剧本判据齐备；3.5 的退役符号集封闭（grep 归零判据可判定）。3.2 的缺口即 B2。

### B-② 共存窗口第三状态

3.2 后（settle 门挡 + 旧腿全权）与 3.3 后（supply 部分放行 + 旧腿）两窗口逐一组合（补给自动弹/divert、快弹窗、恢复局、证据 miss）走查：新旧写端对 node_ord 的写均收敛到同序（hist 序相等去重 + 补推同经原语），未发现被漏画的第三状态；窗口内 R<v 留证噪声已在 design 申报。**零命中**。

### B-③ §2.7 九条 vs 现行代码逐条核

1-9 逐条对码复核成立（r2 已核 1/2/5/6/7/9，本轮补核 3：`apply_settlement_cover` 在读点段先于点击 ✓；4/8 挂 3.4/3.1 判据锁 ✓）。唯一缺口是 §2.7-5 的字面精度（= B1），非漏报的行为面。**除 B1 外零命中**。

### B-④ 恢复局接管链 × v=None 首锚定组合

锁定臂（首确认 value 守卫挡 → 战后备战帧 v=None 行重建）/ relaunch 残留结算屏（同路径）/ resume 撤回重锚（撤回后下一备战帧走 v=None 或 R>v 行）三组合在 A 部分穷举表 #1 行 + E14 走查覆盖，效果账本经原语尾段当帧补齐、无漏发窗口。**零命中**。

## ④ 收敛判定建议

**收敛（零阻断）**。两轮阻断项（F1/F2/R1/R2/R3）复验全部成立，门模型在 E1-E18 × (value, source) 全组合下无反例，证据集同源条款经同锚核码闭合。B1 为切换批（3.5）执行前的文字边界必改项（一句话限定 + 一行申报 + 正本清单补行），B2 为低优先级范围句补注——两者均可在定稿批顺手完成，不构成对方案模型本身的重开理由。建议：处置 B1（必改）+ B2（建议）后定稿收敛。
