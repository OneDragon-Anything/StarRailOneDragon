# 恢复局机制重整 落地

## 1. 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集；CW 域全量 = `sr-od-test/test/sr_od/application/currency_war/`）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（并行会话在飞——**pathspec 形态 `git commit -m "..." -- <本批文件>`，提交前 `git diff --cached --stat` 核对暂存面**），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面；
- 测试判定看退出码/日志文件，禁管道 tail；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 2. 任务

### 2.1 T-1 字段收敛（opened_via + 删除面 + 写入端）

**范围**：按 design.md §2.2：①`CurrencyWarMatch` 新增 `opened_via: str`（`'new_game'` / `'takeover'`，声明注释按 §9 写坐标系与取值时机：容器建立时一次写入、运行内不变、消费 = CwScreenPrep 探针门）；②写入端：`establish_new_match` 加 `opened_via` 参数（缺省值与各调用点核对——入口链 `_establish_match_once` 传 `new_game`、loop `handle_init` 兜底传 `takeover`、sim 直建路径传 `new_game`（design §2.7 落地面勿漏））；③删 `is_new_match`（消费方逐个迁移：SettlementState 新局标记注入改读 `opened_via == 'new_game'`？或按各消费点语义改判据——逐点核对后定，报告申报）；④删 `resume_probe_pending`（T-2 换触发门，本阶段先删字段与既有读写，探针门临时态在 T-2 收口）；⑤`locked_resume`/`locked_sync_done`/`locked_round` 保留（`locked_sync_done` 配对不变量初版不动——design §2.8-5）；⑥每运行重建判据落地（design §2.4 候选 b：入口链建容器置一次性运行内标志，handle_init 见「非本次运行所建」容器弃旧建新传 `takeover`——具体载体落地定，报告申报）。
**设计依据**：design.md §2.2/§2.4
**文件面**：`strategies/impl/cw_strategy.py`（Match 定义）、`strategies/impl/cw_strategy_manager.py`（establish）、`operations/cw_loop.py`（handle_init）、`operations/cw_entry/cw_entry_start.py`（_establish_match_once 调用点）、sim 驱动器调用点、sr-od-test 相关测试
**依赖**：无
**优先级建议**：1
**完成判据**：字段面收敛 + 消费方迁移全 + CW 域全量一次通过 + ruff + 常规检查

### 2.2 T-2 探针裁决链重构（触发门 + 失活场景回归）

**范围**：按 design.md §2.3：①`CwScreenPrep` 段1 b 查触发门改 `opened_via == 'takeover'` ∧ 本次运行未探（去重标志一次写）；②`resume_candidate` 纯函数去留按 design §2.3 落地定（判据不再门控触发；轮次读数遥测保留倾向）；③裁决流程不变（商店可开性探针 / `probe_resolve` / 锁定确认 → 出战段 / 非锁定收店常规接管）；④接管失效写挂「探针分支进入即写」；⑤测试——`new_game` 永不探 / `takeover` 必探一次（去重）/ 两分支结论 / **两个失活场景回归**（重跑重建后锁定重裁决；停点后再跑探针照跑）。
**设计依据**：design.md §2.3、§2.4（失活消解推演）
**文件面**：`operations/cw_screen/cw_screen_prep.py`、`kernel/cw_resume_lock.py`、sr-od-test test_cw_loop/test_prep_special_flow 相关
**依赖**：T-1
**优先级建议**：2
**完成判据**：探针语义测试全绿 + 失活场景回归绿 + CW 域全量一次通过 + ruff + 常规检查

### 2.3 T-3 停点分模式 + 交接批 §2.6 修订

**范围**：按 design.md §2.5：①停点出口按 `env_config.is_debug` 分叉：True → 现语义（停屏交回，留局采样）；False → 弃局重开——`round_success` 交 app 交接节点按异常交接形态调 `CwEntryExit`（复用交接批机制）；②app 三形态判定表 max_rounds 行按模式分叉修订（`currency_war_app.py` `_exit_cleanup`）；③交接批 design §2.6 max_rounds 条目修订（「非退出触发、留局采样」→「is_debug 分叉」）+ 正本 `loop.md` §6 max_rounds 行随批订正（正本条目在 T-5 汇总执行，本阶段只改代码与交接批 design）；④测试——`is_debug` 两分支（halt 交回 / 弃局走交接）。
**设计依据**：design.md §2.5、裁定 4/6
**文件面**：`operations/cw_loop.py`（停点段）、`currency_war_app.py`（交接判定）、交接批 design.md、sr-od-test 相关
**依赖**：T-1
**优先级建议**：3
**完成判据**：停点分模式测试绿 + CW 域全量一次通过 + ruff + 常规检查

### 2.4 T-4 收尾核签

**范围**：①CW 域全量复跑一次通过；②grep 复核（`is_new_match`/`resume_probe_pending` 零残留；`opened_via` 写入点恰三处——入口链/loop 兜底/sim；探针门单一条件）；③sim 冒烟（sim 直建路径 `opened_via=new_game` 断言 + 既有 sim 回归零影响确认）；④实机项裁定：游戏锁定残局能否点 X 退局（讨论遗留待实机确认，记挂账板实机类，不阻批）+ 继续进度路径接管实机单跑复核；⑤核签记录落 reports/。
**设计依据**：design.md 全文
**文件面**：核签记录（迭代内 reports/）
**依赖**：T-1、T-2、T-3
**优先级建议**：4
**完成判据**：全量一次通过；grep 复核通过；实机项落档；常规检查（无代码改动，提交项仅核签文件）

### 2.5 T-5 正本更新 + 挂账板（末位阶段）

**范围**：①正本更新清单（本节 §3）逐条；②挂账板动作（本节 §4）。flow/ 审阅批在飞——落笔前对表已改段。
**依赖**：T-1..T-4
**优先级建议**：5
**完成判据**：清单清零；挂账动作全落板；正本与实现一致

## 3. 正本更新清单（T-5 执行）

1. `flow/loop.md`：结束出口表 max_rounds 行按停点分模式修订；恢复局裁决链描述段（handle_init 重置节奏 → opened_via 事实 + 必裁）重写；
2. `flow/screen-op.md`「备战（CwScreenPrep）特殊」行：段1 四查表述更新（b 查触发门 = opened_via）+ 探针语义（接管局必裁）；
3. `flow/entry-exit.md`：消费面/挂起局语义段如有涉及字段名同步；
4. `cw_resume_lock.py` 模块头：判据变化同步（resume_candidate 去留落地后）；
5. 挂账板 §二.7⑥ 销账（两个失活场景经重整消解，理由 + 本迭代凭据）。

## 4. 挂账板动作（T-5 执行）

1. §二.7⑥ 销账（重整消解，凭据 = 本迭代 landing/核签记录）；
2. 实机类新增：游戏锁定残局能否点 X 退局确认；继续进度接管实机单跑复核；
3. §二.7 内过时导航行订正（如有指向旧三字段机制的表述）。
