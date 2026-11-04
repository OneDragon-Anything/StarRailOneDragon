# 富余买入并入压牌库与 P88 退役（详设）

## 问题与约束

- 本主题边界：商店买入侧的「富余金占位买入」通道归并与 P88 收窄机器退役；不涉压牌库判据本体（M6/死金的现行判据不动）、不涉统一让位序结构、不涉死库存防线（`dead_stock_pair_buy_reject_reason` 保留）。
- 总纲契约 D：仅依赖统一让位序现行契约（压牌库件 = 让位末位档，席位维由序列末位让路承载）。
- 现状证据（2026-11-04 会话核实）：
  - 三平行通道：dominance_buy（金>饱和线 ∧ bench_free>1 ∧ 线外 1★ 全额退，带 P88 特殊帧收窄——特殊帧 = 终局锁定 ∧ 未成型 ∧ 上场满员）/ 富余转压牌库（现行编号 M6；升星目标实费带，席位维度 = 让位序列承载）/ 死金压牌库（同族规则）；
  - M6 席位处理注释原文（shop.py:1893）：「压牌库判据的席位维由序列末位让路承载」——压牌库族已有统一席位答案；
  - P88 动机事故 s77091（占位买入锁席九轮）真凶 = 同名 1★ 死库存对触发不卖保护，已由买侧断新生防线（`dead_stock_pair_buy_reject_reason`，就在 dominance_buy 循环内生效）根治；
  - `PRESS_NARROWED_ARMS` 已缩至独苗（hub_option_buy 上轮迭代已并入序 1）；
  - 1★ 全额退（P76 甲：往返净损 0）+ 让位序末位档 = 占位件可无成本即时让出，P88 所防「席位阻断」在现行防线栈中无剩余真实形态。

## 方案

### 1. dominance_buy 通道删除

- `shop.py` 序 6 dominance_buy 分支（含 `_narrow_frame` 消费点与 `press_narrowed_transition_domain` 计数）；
- `mandate.py` 的 `dominance_buy_eligible`（本体 bench_free>1 收紧与金位门随通道消亡）与 ：958-979 的调用段（序 6 发出前的资格装配）；
- `dominance_buy` 契约键（宿主 `criteria/contracts.py:236`）与 `sell_gate.py:131` 的 `'dominance_buy': 'press'` 映射键（LAUNCH_CAUSE_BY_ARM 域内——删除后闭集对账测试 `test_sell_window_launch.py` 同步更新键集期望）；
- `tools/cw/proofs/p88_check.py`（import `swap_bond_gate_domain_of` :34 + 断言 `LAUNCH_CAUSE_BY_ARM['dominance_buy']=='press'` :87——P88 整体退役，验证脚本同批删除）；
- `test_dead_stock_pair.py` 中 `dominance_buy_eligible` 直调断言与 dominance_buy 发射断言（:187-195）——同步改写（经 M6 兜底带路径断言）或删除；
- `dominance_*` 计数键族逐键核对（M6/死金侧仍消费的保留）。

### 2. M6 压牌库带选择扩一条兜底

现行规则不动（升星目标实费带，`tier_w` 门槛与排除面不变），新增：**带内无货或无升星目标时，1★ 兜底带启用**——候选 = 与线内成员零重叠的 1★（`zero_overlap` 同规则，1★ 全额退属性由让位序档 10 末位天然承载）。买入后席位紧张时按让位序列末位让路（与 M6 现行席位维同规则，零新逻辑）。

### 3. P88 全套退役

- `mandate.swap_transition_narrow_frame`（mandate.py:683 起，单函数）；
- `cw_deploy_logic.swap_bond_gate_domain_of`（谓词源；确认无其他消费后删——`tools/cw/proofs/p88_check.py` 在删除清单，不计保留消费）；
- `PRESS_NARROWED_ARMS` 常量；
- `proofs/p88.md` **原地文首标注退役指针**（「本命题机制已随压牌库归并迭代退役，全文留档可溯」——不移动文件，git 历史与引用路径不断）；
- 测试删除：`test_sell_window_launch.py` 闭集对账中收窄集断言（S_spec 为现行常量名 `PRESS_NARROWED_ARMS`）、`test_front_window_predicates.py` 中**仅收窄域相关断言**随源删（该文件含非收窄域谓词测试 ×4，保留不动——按断言粒度删，不整文件删；**混合断言测试拆分**：`test_f9`（:229-245）捆绑统一让位优先级迭代 3.4「万金油退出义务买入面」的行为断言——只删其收窄旗断言部分，万金油行为断言保留〔另一迭代的验收锁，不动〕）；闭集本体（`LAUNCH_CAUSE_BY_ARM` 对账）保留并更新键集期望。

### 4. 行为变化申报（实机观察面——本迭代不做 A/B 模拟对照，用户 2026-11-04 裁定）

原特殊帧（终局锁定 ∧ 成型度<1 ∧ 上场满员——P88 收窄所防的帧）从「dominance 禁买」变为「1★ 兜底带可买、席位紧张让位序列自动处置」——买入手数在该特殊帧可能增加；死库存防线确保不重现 s77091 形态（断新生对在兜底带同拦截）。

## 关键取舍

- **放弃「保留 P88 改写为优先级语言」**（前议方案）：用户 2026-11-04 裁定「本质是压牌库，应由压牌库优先级覆盖」——让位序列已是该语义的现行载体，无需一段翻译；保留即维持双轨。
- **放弃「三通道全并为一」**：M6/死金判据本体各有其触发语境（升星窗口让位/死金状态），现行行为有据；只归并语义重复且带私有禁令的 dominance_buy。

### 风险兜底

本迭代不做 A/B 模拟对照（用户 2026-11-04 裁定）——行为退化发现通道 = 实机对局遥测判读（特殊帧买入手数/让位频率的异常上升）。实机观察确认退化后回滚方式 = 恢复 dominance_buy 独立通道（git revert 本阶段），不回滚结构批与 3.3。
- **与 3.3 的名单源耦合（总纲契约 D）**：M6 兜底带读的「线内成员」排除面 = 买面义务名单装配（`buy_members`/`obligation_members`，shop.py:884-904——注意现行 `k_members` 是单方向名单 :863-864，两层合成的是义务装配侧），该装配在 3.3 被改（配方半边 → 过渡层贡献）；落地顺序锁定 3.3 → 3.4，兜底带按 3.3 收尾态名单源实现，不出现「按旧名单实现再被 3.3 二次改写」的无对照窗口。
- P88 动机事故 s77091 的锁席成因叙事（死库存对，非席位占用）持久指针 = `mandate.py` `dead_stock_pair_buy_reject_reason` docstring（:644-649）。
