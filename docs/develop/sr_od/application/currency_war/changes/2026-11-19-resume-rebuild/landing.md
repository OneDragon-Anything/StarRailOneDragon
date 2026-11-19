# 恢复局机制重整 落地

## 1. 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（CW 域全量 = `uv run pytest sr-od-test/test/sr_od/application/currency_war/ -q`；判定看退出码/日志文件，禁管道 tail）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（并行会话在飞——**pathspec 形态 `git commit -m "..." -- <本批文件>`，提交前 `git diff --cached --stat` 核对暂存面**）；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 2. 任务

### 2.1 T-1 字段收敛 + 重建判据（机制闭环）

**范围**：按 design.md §2.2/§2.4：①`CurrencyWarMatch` 字段面：新增 `opened_via`（缺省 `'new_game'`）/ `created_run_id`（缺省 None）/ `probed`（缺省 False）——声明注释按 §9（坐标系/取值时机/写入端）；删 `is_new_match`、`resume_probe_pending`；②`establish_new_match`：内部先 ensure_run_started 幂等前置 → 记 `created_run_id`（恒非 None）；加 `opened_via` 参数——三生产调用点显式传参（入口链 `_establish_match_once`=`new_game` / loop `handle_init` 兜底=`takeover` / 商店防御兜底 `cw_screen_shop.py::CwScreenShop.observe`=`takeover`）；③loop `handle_init` 重建判据：容器存在 ∧ `created_run_id != 当前 run` → 先 `discard_stale_match_container` 再 `establish_new_match(takeover)`（discard 显式前置）；④消费点迁移：SettlementState 新局标记注入与战斗帧恢复检测门改 `opened_via == 'takeover'`（等价映射表见 design §2.6——旧 `is_new_match=True` ≙ takeover，方向禁反）；⑤探针门初步化：`CwScreenPrep` b 查改 `opened_via == 'takeover'` ∧ `not probed`（探后置 True）——本阶段机制即闭环，T-2 只做细化与回归；⑥测试：字段写入三路径断言 / 重建判据保留-重建矩阵（design §2.4 六场景）/ 消费点迁移等价断言 / 探针门基础用例。
**设计依据**：design.md §2.2、§2.4、§2.6
**文件面**：`strategies/impl/cw_strategy.py`、`strategies/impl/cw_strategy_manager.py`、`operations/cw_loop.py`、`operations/cw_entry/cw_entry_start.py`、`operations/cw_screen/cw_screen_shop.py`、`operations/cw_screen/cw_screen_prep.py`、sim 直构两点（skill 脚本 cw_sim_match_drive.py / 测试仓 test/harness/sim_backend_runner.py——缺省值零改动核对，如需显式传参则改）、sr-od-test 相关测试
**依赖**：无
**优先级建议**：1
**完成判据**：机制闭环（重建+必探全场景正确）+ CW 域全量一次通过 + ruff + 常规检查
**验收凭据形式**：新测试 + 全量复跑记录

### 2.2 T-2 探针链细化（失效写挂点 + 纯函数退役 + 失活回归）

**范围**：按 design.md §2.3：①接管失效写挂「探针分支进入即写」（触达面扩大申报进注释）；②`resume_candidate` 纯函数退役（`obs/cw_resume_lock.py` 路径——**非 kernel/**；轮次读数保留于 locked_round 遥测链；模块头申报判据变化）；③两个失活场景回归用例（重跑重建后锁定重裁决；停点后再跑探针照跑）+ 第三形态（app fail 残留容器）回归；④`locked_resume`/`locked_sync_done` 配对链既有断言零回归确认。
**设计依据**：design.md §2.3、§2.4（失活消解）
**文件面**：`operations/cw_screen/cw_screen_prep.py`、`obs/cw_resume_lock.py`、sr-od-test test_prep_special_flow / test_cw_loop 相关
**依赖**：T-1
**优先级建议**：2
**完成判据**：失活场景回归全绿 + CW 域全量一次通过 + ruff + 常规检查
**验收凭据形式**：回归测试 + 复跑记录

### 2.3 T-3 停点分模式（loop 出口分叉，零 app 改动）

**范围**：按 design.md §2.5：①loop 停点段按 `env_config.is_debug` 分叉（读取点单点 = 停点段）：True → 现出口文本；False → `round_success(f'{STATUS_HANDOFF_PREFIX}停点重开')` 交 app 异常交接形态；②app 侧**零改动**（三形态判定自动承接——核验后如有缺口如实上报不代修）；③交接批修订：交接批 design §2.5 判定表「其余」行补「非 debug 停点已改走交接出口」+ §2.6 条目语义修订；④交接批测试同步两处：`test_currency_war_app.py` 用例③改 `is_debug=True` 前提 + 新增 False 分支用例；`test_cw_loop.py` 停点出口文本断言同步（False 分支带交接前缀）；⑤测试：is_debug 两分支（halt 交回 / 交接前缀交出→exit 被调）。
**设计依据**：design.md §2.5、裁定 4/6
**文件面**：`operations/cw_loop.py`（停点段）、交接批 `design.md`（§2.5/§2.6）、sr-od-test test_currency_war_app.py / test_cw_loop.py
**依赖**：T-1
**优先级建议**：3
**完成判据**：停点分模式测试绿 + CW 域全量一次通过 + ruff + 常规检查
**验收凭据形式**：新测试 + 复跑记录

### 2.4 T-4 收尾核签

**范围**：①CW 域全量复跑一次通过；②grep 复核（宿主限定口径：Match 宿主 `is_new_match`/`resume_probe_pending` 零残留——**SettlementState/战斗等待 op 的同名字段为值注入语义不在删除面**；`opened_via` 显式传参恰三处 + 缺省兜底形态登记；探针门单一条件）；③sim 回归零影响确认（直构容器保留断言 + 探针可达 0）；④实机项落档：游戏锁定残局能否点 X 退局确认；继续进度路径接管实机单跑复核；⑤核签记录落 reports/。
**设计依据**：design.md 全文
**文件面**：核签记录（迭代内 reports/）
**依赖**：T-1、T-2、T-3
**优先级建议**：4
**完成判据**：全量一次通过；grep 复核通过；实机项落档；常规检查（无代码改动，提交项仅核签文件）
**验收凭据形式**：核签记录文件

### 2.5 T-5 正本更新 + 挂账板（末位阶段）

**范围**：正本更新清单（§3）+ 挂账板动作（§4）逐条。flow/ 审阅批在飞——落笔前对表已改段。
**依赖**：T-1..T-4
**优先级建议**：5
**完成判据**：清单清零；挂账动作全落板；正本与实现一致
**验收凭据形式**：文档对照 review

## 3. 正本更新清单（T-5 执行）

1. `flow/loop.md`：结束出口表停点行按分模式修订；恢复局裁决链描述段重写（per-run 重置 → opened_via 事实 + created_run_id 重建判据 + 必经裁决）；
2. `flow/screen-op.md`「备战（CwScreenPrep）特殊」行：段1 四查 b 查触发门表述更新（opened_via ∧ probed）；
3. `flow/entry-exit.md`：停点弃局语义涉及段同步；
4. `obs/cw_resume_lock.py` 模块头：判据变化同步（T-2 已改，T-5 复核）；
5. `prep_actions.py` `launch_battle_unified` docstring 隐藏前提段：注释引用改 opened_via 口径（「恢复检测链(cw_resume_lock.is_new_match)恒走新状态容器」过期——重整后各接管路径容器均新建，前提强化，论证依据更新）；
6. `currency_war_config.py` max_rounds 配置注释：非 debug 行为变化（弃局回大厅）申报；
7. 挂账板 §二.7⑥ 销账（两失活场景 + 第三形态经重整消解，凭据 = 本迭代核签记录）。

## 4. 挂账板动作（T-5 执行）

1. §二.7⑥ 销账；
2. 实机类新增：游戏锁定残局能否点 X 退局确认；继续进度接管实机单跑复核；
3. §二.7 内过时导航行订正（指向旧三字段机制的表述）。
