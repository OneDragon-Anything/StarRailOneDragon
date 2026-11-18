# 备战交互链迁移 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级；工作区有并行批在飞文件绝不卷入），commit message 含阶段号与任务 id（已立账时）；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 状态机宿主迁移（零行为）

**范围**：按 design.md §2.3：①`CurrencyWarMatch` 加五个 additive 流程态字段（尾部带默认值追加；定义注释写「取值时机/写入端/消费边界」，`is_new_match` 注释 = handle_init 逐 execute 重判语义）；②主循环 handle_init 改写 Match 字段（兜底建局先 `establish_new_match` 后写；`locked_sync_done` 不重置）+ 三处 run 级读取点（SettlementState/兜底门/恢复检测门）与候选判定输入改读 Match 字段；③**备战链内五符号全部读写点**改指 Match 字段（含候选门 :1357 / 锁定门 :1389 读取、锁解除写 :1394、三标志置位、候选撤回两处）及链内含符号文本的行内注释同步清理；④`prep_actions.py` 发出核证据位读写（:630 getattr 读 / :639 置 True 写）改指 `ctx.cw_match.locked_sync_done`——读侧 Match 缺席按 False 同语义，写侧结构性不可达（locked_resume=True 蕴含 Match 在场，段3b 第 0 查门保证）随注释申报；同文件 `locked_resume_sync_and_battle` docstring 内的「(R3)」会话标识顺手清理（注释规范）；⑤失效写方法保留不删（战斗帧确认点 :1237 不动）；⑥既有测试同步（`test_prep_actions.py` 证据位断言改 Match）。行为零变化：写入节奏 per-run 重判/重置不变，只换宿主。
**设计依据**：design.md §2.3
**文件面**：`src/sr_od/application/currency_war/strategies/impl/cw_strategy.py`、`operations/cw_loop.py`、`prep_actions.py`、`CwStrategy` 契约 docstring（禁读字段清单登记）、sr-od-test 相关测试
**依赖**：无
**优先级建议**：1
**完成判据**：
- 五字段落 Match；`grep -E '_cw_resume_candidate|_cw_locked_resume|_cw_locked_round|_cw_locked_sync_done|_is_new_match' src/sr_od/application/currency_war/operations/cw_loop.py` 零命中（含 import）；
- 行为回归 = `test_prep_actions.py` 四路径既有回归通过（备战分支现无既有测试，实况申报；护栏缺口由 3.2/3.3 六剧本承接）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：grep 复核 + prep_actions 四路径回归通过记录

## 3.2 三段链迁移（一次切换：画面 op 吸收 + 主循环坍缩）

**范围**：按 design.md §2.1/§2.2/§2.4/§2.6/§2.7-4——**原子迁移，禁拆分**（中间态双探针互双发）：①`CwScreenPrep` 观察 node **最顶部**（先于 match 缺席门/清场/收店探针）加子态识别四查（0 锁定确认态 / a 返回按钮 OCR lcs 0.9 / b 探针〔候选过判即失效写→点商店→判定→候选撤回〕/ c 补给分流），非常规子态跳过全部既有前置段；b 查非锁定收店后按序跑齐前置段落常规路径；②决策动作 node 顶部（`cw4_segment_serial` 置位行之前）特殊流程三处置（点返回 / `locked_resume_sync_and_battle` 同步步+出战 / 分流点击；a/c 点击成败均交回不落段4），失效写 actor 改指 `CwScreenPrep`，计数器写点迁 `cw4_counters` 分键（None 守卫）；③主循环备战分支删三段链（返回投资策略点击 / 候选+探针+锁定出战 / 补给分流）与战斗窗置位（回调统一承载），保留横幅守卫/双识别标志识别/兜底清/停点/回调/派发；链外关联清理：`_invalidate_tracked_on_takeover` docstring 写点登记改写（:533-536，备战帧点已迁）、:1242 阶段一前导注释（「返回投资策略选择」分支挪位说明）同步改写；④`kernel/cw_game_state.py` `tracked_account_observed` 字段注释写入端登记随迁更新；⑤本阶段提交六剧本首批（3.3 目标文件先行落**第 4/6 剧本**——剧本 6 即锁定重派发帧经第 0 查直达断言 = 阻断面护栏）。wait 值与防线参数沿 design §2.6 对照表随迁。
**设计依据**：design.md §2.1、§2.2、§2.4、§2.6、§2.7-1/-3/-4/-6
**文件面**：`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_prep.py`、`operations/cw_loop.py`、`kernel/cw_game_state.py`（注释）、sr-od-test 六剧本文件（首批）
**依赖**：3.1
**优先级建议**：2
**完成判据**：
- 主循环备战分支 = design §2.1 坍缩形态；`grep -nE '_cw_back_btn_count|resume_candidate|probe_resolve|locked_resume_sync_and_battle' src/sr_od/application/currency_war/operations/cw_loop.py` 零命中（含 import）；`grep -n '按钮-返回补给阶段'` 零命中；`grep -n '返回投资策略选择'` 唯一合法残留 = 暗色锁定分发分支的 area 名「按钮-返回投资策略选择」（:943 一带，本批不迁移面）；
- 画面 op 四查 + 三处置在位；非常规子态零前置段接触、锁定重入帧经第 0 查直达段3b（首批剧本断言通过）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：首批剧本（第 4/6 剧本）+ 既有回归（prep_actions 四路径）通过记录

## 3.3 harness 回归集补齐 + 既有同步收尾

**范围**：按 design.md §2.8 补齐六剧本（3.2 首批之外：常规帧零变化 / 返回按钮帧 / 探针非锁定续常规 / 补给未确认+已确认），全量为行为级断言（点击/上报/零前置段接触/交回/重派发）。首步验证 fixture 帧资产现值可用，不可用则剧本内构造（零真实副作用）。主循环侧无既有测试需同步（实况申报）。
**设计依据**：design.md §2.8
**文件面**：`sr-od-test/test/sr_od/application/currency_war/operations/cw_screen/cw_screen_prep/test_prep_special_flow.py`
**依赖**：3.2
**优先级建议**：3
**完成判据**：
- 六剧本全绿且行为级断言，fast_sleep 包裹，零真实副作用；
- 既有回归全绿（prep_actions 四路径）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：六剧本回归集测试

## 3.4 收口核签

**范围**：①全量相关子集复跑一次通过；②grep 复核三段链零残留；③实机项裁定：实现与测试中暴露 harness 覆盖不了的实机形态（探针真实时序/锁定局渲染差异）→ 按用户裁定记入货币战争待办（不阻批），无暴露则本阶段仅核签记录。
**设计依据**：design.md §0（用户裁定②）、§2.5（sim 申报表）
**文件面**：核签记录（迭代内 reports/）
**依赖**：3.1、3.2、3.3
**优先级建议**：4
**完成判据**：
- 相关回归子集全量一次通过；
- grep 复核通过；
- 实机项裁定落档（记账或「无暴露」申报）；
- 完成前常规检查（本文首节；本阶段无代码改动，提交项仅核签文件）。
**验收凭据形式**：核签记录文件

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。flow/ 审阅批在飞——落笔前对表已改段，以本迭代规范文本为准合入。
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1-3.4 全部
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

**skills 侧 flow/**：

- `skills/sr-od-dev-currency-war/references/flow/loop.md`：§3 备战分支进入序整体改写（三段链迁 CwScreenPrep 特殊流程段的 as-built 申报 + §2.2-4 停点模式不处置三段链的新语义申报）；§1 职责边界注「备战分支交互链」残余违例消解 ← 3.2
- `skills/sr-od-dev-currency-war/references/flow/screen-op.md`：特殊流程段消费首批实例申报（备战四查/三处置 + §2.7-1 两条扩展修订：段1 识别性点击读屏例外新类、段2 = 子态流程事实写语义）+ 三子态不拆独立 op 的豁免引用 + 「上报先于处理」「识别+上报合并一个 node」线性序在子态分支的例外申报（:10/:15 两行同步） ← 3.2
- `skills/sr-od-dev-currency-war/references/flow/guards.md`：联动核对（重派网/兜底清/外环 fail-streak 与备战分支坍缩后的交界 + 失败链形态变化申报） ← 3.2

**docs 侧**：

- `docs/develop/sr_od/application/currency_war/flow/outer_loop.md:117`：锁定直出战宿主表述（cw_loop → CwScreenPrep 段3b） ← 3.2
- `docs/develop/sr_od/application/currency_war/screens/README.md:164`：同上宿主表述 ← 3.2
- `docs/develop/sr_od/application/currency_war/strategy-docs/27_transit_screens.md:12`：同上宿主表述 ← 3.2（14_p1 历史归档自带勘误注，不改）
- `docs/game/screens/currency_war_supply.md:19`：补给分流判定与点击宿主表述 ← 3.2
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：:840 恢复锁定写入方 / :1027-1031 tracked_account_observed 写端语义 / :1034-1035 写入方登记行（现登记过期函数名 `_mark_session_resumed`，随更新订正为现役写点两确认点分流）/ §6.4 接管观察态失效宿主表述 ← 3.2/末阶段

**src 侧（随代码阶段同步，不占末阶段）**：

- `kernel/cw_game_state.py` `tracked_account_observed` 字段注释写入端登记 ← 3.2

**过程件**：

- `.debug/progress/CW跨迭代挂账.md` §二.7②：销账（落地批指针 = 本迭代目录）；新增⑤：浮层闸门/屏态复验退役论证（本批显式维持后再移交）——登记时点 = 3.2（维持裁定落定即登记，防批中断移交义务悬空），收尾只补论证指针；新增⑥：跨 run 锁定帧/停点后续跑探针链失活（既有形态保留申报，design §2.3 残余面）← 3.4 收口登记
