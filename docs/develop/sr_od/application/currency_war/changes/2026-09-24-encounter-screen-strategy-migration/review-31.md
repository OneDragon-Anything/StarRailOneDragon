# 3.1 阶段验收报告

- 验收对象：项目仓 commit `56ed73db47a6298747c009b96f5bc389a47844c2`（4 文件）+ 测试仓 commit `c763b1c604af03a4cdd0bbe0a76b5968bf2a58c4`（1 文件）
- 验收人：独立干净上下文 reviewer；判据源 = design.md §2.2–§2.5/§2.12 + 现役核 `kernel/cw_encounter_selection.py` 直调对照
- 验收日期：2026-09-24

## 结论：通过（发现 1 条低严重度，不需返工）

入库面与申报面一致（`git show --stat` 两仓核对）；新核 `decide` 与现役核 `decide_encounter` 经 420 组同输入对拍零分歧，差异面全部落在 design 申报项内；测试 10 用例全绿、ruff 全绿、边界零侵入。

## 发现清单

**F1（低 / 文档性，不需返工）测试内锚点编号与 design §2.12 锚点编号错位**
- 位置：`sr-od-test/test/sr_od/application/currency_war/test_cw_encounter_pick.py:236`（「锚点 7:窗口不足独立态与因词」）、`:261`（「锚点 8:立场重拍回退态」）
- 事实与直调证据：design §2.12 锚点 7 = op 层「建议刷 ∧ 刷新圆钮锚读缺 → 重调后 `round_fail`」防线行为（属 3.2 范围，本批正确地未测试）；测试文件自己另编号的「锚点 7/8」实为 design §2.2 决策序语义（窗口不足独立态）与 §2.2/§2.3（重拍回退）。模块 docstring（:4）已声明「验收锚点 = design §2.12 锚点 1-6 + 立场重拍回退态」，口径自证无歧义，但两套「锚点 N」编号并存，后续阶段按编号检索会错位。
- 修正方向：可选——将测试注释中的「锚点 7/8」改称「§2.2 决策序第 1 条 / §2.2-§2.3 重拍回退」之类的语义指称，或在锚点 7 注释内补一句「≠ design §2.12 锚点 7（op 防线，归 3.2）」。不阻塞本批。

### 计划内未完成事项（非发现，防 3.2 漏做登记）
1. 两处旧指针 docstring 失指：`strategies/impl/mandate_v1/supply.py:12`、`kernel/cw_events.py:171` 仍写「检测集单一源 = cw_node_obs.DIAMOND_EQUIP_NAMES」——定义点已迁 `kernel/cw_obs_core.py`。landing.md §3.2 范围明文申报收口（「钻石检测集单一源表述两处」），3.1 未接线阶段不构成违规。
2. `kernel/cw_encounter_selection.py::game_start_reset` docstring「RunLoop handle_init 或首结算时调」为失实声明（design §2.1 孤儿申报：全仓零调用）——收口归 3.2 kernel 段注释收口面。

## 验收核对表

| # | 判据 | 结果 | 证据 |
|---|------|------|------|
| 1a | §2.2 决策序逐条核对（新核 vs 现役核同构） | ✓ | 逐分支静态对照 + 临时对拍脚本 420 组（14/16 窗口形态 × 7 候选集 × 刷新两臂，含 fill 双槽注入相）全等零分歧（脚本用后已删） |
| 1b | 窗口不足独立态 | ✓ | `decide` :240-242 先于 κ 评估；因词 `window-insufficient` 与 `kappa-不足` 分因（测试 :238-258） |
| 1c | κ_S 三态逐位同构 | ✓ | `_kappa_state` 两文件逐行一致（encounter_pick :104-130 vs cw_encounter_selection :297-323）：全删失→不足/全胜→足量/恰一胜→边缘（fill 分支删失优先、双槽 None 不激活） |
| 1d | cap 过滤在前 | ✓ | `decide` :250-263：`t > cap: continue` 先于经验层判断；边缘态 t≥3 全排除含五/六（测试 :110-116 + 测试有效性反事实实证：cap 失效则断言 idx 翻红） |
| 1e | t≥5 经验档层 | ✓ | `log.tier_cleared(t)` 通道与原核同构；测试 :160-178（正证据放行/败局行不放行） |
| 1f | 刷新阀两臂 | ✓ | `_empty_reachable_frame`：`left is not None and left >= 1` → Suggestion；None/0 → dark-fallback 最低档（测试 :121-156 三臂 + left=None fail-closed 对拍独立核） |
| 1g | 选档主序 + tiebreak + 输入序 | ✓ | `max(difficulty)` → `min((reward_tier, idx))`，与原核 :441-444 逐位同构；测试 :183-208（钻>装备>金币>末档 + 输入序先） |
| 1h | fail 向与归因串格式 | ✓ | `e3-simple\|` 前缀、`pick:t{k}\|kappa=<态>`、`refresh-valve:<因>`/`dark-fallback:<因>` 封闭三因 + `stance-unconfirmed`；`dark-install` 段不再产出（§2.3 申报一致）；对拍中 pick reason 验证为旧串声明段前缀 |
| 1i | 差异面 = 暗装门收窄与申报一致 | ✓ | 比值腿五门（F_MIN/G_BASE/DELTA_T/bar 双槽/D_enc 读点）与 d_win 提取退役；`refresh_used` 参 → `encounter_refresh_left` 闸内嵌（§2.2）；输出拆两 dataclass（§2.6）；空候选 `no-options`（§2.2）；立场门前置（§2.3）——五项差异全部 design 在册 |
| 2 | 立场常量区【拍】登记 | ✓ | encounter_pick :41-58：2026-09-24 过目记录 + 重拍语义（None → 回退态）+ 暂定值备注；`EDGE_CAP: int \| None = 2`；偏好序四档常量 :137-140；置 None 回退态测试 :263-276（两常量各测，恒最低档零刷新断言） |
| 3 | DIAMOND_EQUIP_NAMES 单一源 | ✓ | 全仓 grep：定义唯一点 = `kernel/cw_obs_core.py:50`，值零变化（frozenset 三名）；消费方 `cw_node_obs`/`cw_encounter_selection`/`encounter_pick` 均 import kernel；测试仓零引用 |
| 3b | 消费方行为等价 | ✓ | `cw_encounter_selection.py` diff 仅 reward_tier import 源行；`cw_node_obs.py` diff 仅定义迁出改 import + 注释收口；`any(d in t ...)` 消费语义与 frozenset 同值 = 零行为差 |
| 4a | 边界零侵入 | ✓ | 两 commit `git show --stat`：项目仓仅 4 申报文件；`flow.py`/`bridge.py`/`cw_events.py`/`mandate_v1/encounter.py`（EV 核）/sim 零触碰；工作区 src/ 零未提交改动（git status 证实） |
| 4b | 保留面未动 | ✓ | `claim_encounter_reward`/`record_settlement_row`/`SettlementRing`/`EncounterLog`/`game_start_reset`/`last_normal_battles`/`last_row` 全文在库且不在 diff 内 |
| 5 | 测试质量 | ✓ | 测试面 = 锚 1-6 语义 + 窗口独立态 + 重拍回退 + 注入面（fill 双键/未知键 KeyError/幂等/reset）+ 空候选，10 用例全绿（4.73s）；断言行为意图（idx/reason/类型）非巧合——测试有效性抽查实证：窗口口径误收奖励行 → κ 翻边缘断言必红；cap 失效 → idx 翻红；环行构造全部经生产单一写端 `record_settlement_row`；docstring 引 design §2.2-§2.5 + landing §3.1 |
| 6a | ruff | ✓ | 自跑 `uv run ruff check`（4 文件）：All checks passed |
| 6b | 类型注解 | ✓ | 函数签名/dataclass 字段全注解（`list[str]`/`X \| None` 形态）；模块级私有常量无注解与 kernel 先例一致 |
| 6c | 中文注释写为什么 | ✓ | 立场常量区/单一源迁移注释均含依据链（形态申报出处、生成文件蒸发风险、重拍触发器） |
| 6d | 无 **kwargs / 禁相对导入 | ✓ | 无构造函数 **kwargs（dataclass 字段显式）；`apply_calibration(**kw: object)` 为标定注入面函数，AGENTS §7 硬约束限定「构造函数」且 design §2.3 明文「未知键名抛错防线照旧」+ kernel 侧同款先例（`cw_encounter_selection.apply_calibration`），判合规；全部绝对导入，TYPE_CHECKING 仅注解用 |
| — | 未接线声明 | ✓ | `encounter_pick`/`EncounterPickDecision`/`EncounterRefreshSuggestion` 全仓 grep 零生产消费方；`mandate_v1/__init__.py` 未导出；生产行为零变化达成 |

### 对拍方法注记（供复核）
临时脚本将现役核标定槽注入为「比值腿恒过」形态（`F_MIN=1.0, G_BASE=1.0 → g^x≡1.0≥F_MIN`、bar 双槽定谳、`D_ENC_VARIANT='i'` 直读、`enemy_difficulty` observation 写入），使旧核 t≤4 分支与新核「能力态直判」结构等价后逐 fixture 对拍。声明差异面单独核验不入等价矩阵：空候选（新核 `no-options`）、`left=None` fail-closed（旧核参数无 None 形）、fill 双槽未定谳相（旧核 bar 键注入即激活，新核 None 不激活——该面在双核同注入相验证逐位同构）。`refresh_used` 与 `left` 映射：`left=1 ⟺ refresh_used=False`，`left=0 ⟺ refresh_used=True`。
