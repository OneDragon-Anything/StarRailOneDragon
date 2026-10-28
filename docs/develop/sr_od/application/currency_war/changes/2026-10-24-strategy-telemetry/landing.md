# 策略遥测 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号与任务 id；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 采集骨架：信封 + kernel 决策上下文槽 + 基类捕获缝 + sink 装配槽
**范围**：新增 `kernel/cw_decision_ctx.py`（决策上下文槽：set/take）；新增 `telemetry/strategy_telemetry.py` 写盘闭包（含 run_id 补齐与局外零写判断）；`cw_strategy.py` 增显式 14 入口闭集包裹（含 in-flight 守卫）、`decision_payload()` 钩子、`set_decision_sink` 槽与装配函数；`decision_assembly.py` 生产装配；顺带勘误 `cw_strategy.py` docstring 决策入口计数（:14「15」→14，与 :82 对齐）。**不含**：mandate_v1 payload（3.3）、`note_action_receipt` 读侧（3.2）、渲染（3.4）。
**设计依据**：details/capture-store.md §1、§2（槽定义）、§3（钩子签名）、§4、§5
**文件面**：`kernel/cw_decision_ctx.py`（新）、`strategies/impl/cw_strategy.py`、`telemetry/strategy_telemetry.py`（新）、`src/sr_od/application/currency_war/decision_assembly.py`、sr-od-test 对应测试文件
**依赖**：无
**优先级建议**：9
**完成判据**：
- 行为对照 capture-store §1/§2/§4/§5：注入 sink 后单次 decide 调用产出一行记录，信封键闭集齐全（envelope 不含 run_id、sink 补齐）、dtag 格式 `<strategy_id>:<dseq>`；`decide_shop_screen` 不被包裹；super() 嵌套链（decide_shop_action → flow 基类实现）恰一条记录；空动作返回清槽；sink 异常不改变 decide 返回值；局外（run_id 空）零写；纯单测（不注入 sink）零文件副作用
- 完成前常规检查（本文首节）
**验收凭据形式**：新增单测名清单 + 一样本记录行 JSON

## 3.2 dtag 进回执
**范围**：`note_action_receipt` 读决策上下文槽，非 None 并入 `receipt['dtag']`（take 语义，读后清）；受阻回执（reason 非空）同形态断言；槽测试复位口 `reset_decision_tag()` 与 sr-od-test conftest 复位登记。
**设计依据**：details/capture-store.md §2
**文件面**：`kernel/cw_game_state.py`（`note_action_receipt` 函数体内）、`kernel/cw_decision_ctx.py`（复位口）、sr-od-test 受影响测试与 conftest
**依赖**：3.1
**优先级建议**：8
**完成判据**：
- 回执行含 dtag 且与同帧信封 dtag 同值；受阻回执/重试链多回执/跨测试残留三形态断言齐（后者 = conftest 复位后零 dtag 残留）；
- 完成前常规检查（本文首节）
**验收凭据形式**：测试名 + 一条含 dtag 的 journal 回执行样例

## 3.3 mandate_v1 v1 payload
**范围**：`MandateV1Strategy.decision_payload` 覆写（direction / k_members+k_fallback / window，capture-store §3 三键，k_members 算法含 K 空窗回退分支并记 `k_fallback` 标注）；新篇 `strategy-docs/strategy-telemetry.md`（信封键闭集 + mandate_v1 payload 键表语义）；`strategy-docs/README.md` 分篇登记。
**设计依据**：details/capture-store.md §3
**文件面**：`strategies/impl/mandate_v1/bridge.py`（或 mandate_v1 包内新小模块）、`docs/develop/sr_od/application/currency_war/strategy-docs/strategy-telemetry.md`（新）、`docs/develop/sr_od/application/currency_war/strategy-docs/README.md`、sr-od-test 对应测试
**依赖**：3.1
**优先级建议**：7
**完成判据**：
- sim 局任一决策帧的 payload 三键与 gs/state 现读直算一致（抽查手核一帧）；k_members 含回退分支且 `k_fallback.hit` 与 `cw_intention.k_empty_window_fallback` 直调一致；window 结论与 `_entry_window_open` 直调一致；锁定帧 `candidates=[]` 语义正确；键表含「章级同键多实例 FIFO 错位为已知降级」申报句；
- 完成前常规检查（本文首节）
**验收凭据形式**：测试名 + sim 局样例记录行 + 手核对照摘录

## 3.4 渲染按需装配
**范围**：渲染器 `--strategy-telemetry` 发现/加载/两级 join（动作级 dtag + 章级 ENTRY_SCREEN_MAP）/动作节「策略依据」小节/章级「策略依据」小节/章尾未落地与失配注记/局头策略遥测行（含未归属计数）+ 三态降级；`ENTRY_SCREEN_MAP` 常量（render-assembly §2 表直译）；渲染器配套修订 = `SCREEN_REGISTRY` 补 sim 广播行「货币战争-星徽秘典弹窗」+ `CwScreenBookcard` 行键集修复（box_card_names → star_tome_opts，存量错行）；测试锁面扩展现有渲染测试文件。迭代内义务（非正本清单项）：同步 `changes/2026-10-16-journal-review-renderer/details/render-spec.md` 章内结构（该文件寿命 = 迭代，禁入正本清单）。
**设计依据**：details/render-assembly.md
**文件面**：`tools/cw/replay_to_md.py`、`sr-od-test/test/tools/test_replay_render.py`、`changes/2026-10-16-journal-review-renderer/details/render-spec.md`（迭代内同步）
**依赖**：3.2（dtag 进回执；payload 空记录走降级块，不硬依 3.3）
**优先级建议**：7
**完成判据**：
- 无策略文件：报告与改动前渲染逐字节一致，**例外仅书卡章 0 观察键集修复面**（旧渲染器对照 diff 逐 hunk 归类：目标改动 + 书卡键集例外，无其他差异）；
- 有策略文件：动作级依据块 dtag 对应（含重试链一节多依据形态）、章级小节按映射表归章（含同键多章 FIFO）、指纹失配（含 op 名域归一）与未落地注记、局头行三态齐全；星徽秘典弹窗章注册生效；
- 完成前常规检查（本文首节）
**验收凭据形式**：测试名 + sim 局渲染样本 diff 对照

## 3.5 端到端验证（sim 全链 + 生产装配位核读）
**范围**：核验 `cw_sim_match_drive.py` 在 recorder 重定向后 sink 落点随根（如需脚本侧显式注入则补一行装配）；跑一局 sim，journal 回执 dtag ↔ strategy jsonl ↔ 渲染报告依据块三方一致抽查；`decision_assembly.py` 生产装配位代码核读。
**设计依据**：details/capture-store.md §4；details/render-assembly.md §1
**文件面**：`skills/sr-od-currency-war-dev/scripts/cw_sim_match_drive.py`（如需）、验证产物落 `.debug/`
**依赖**：3.1、3.2、3.3、3.4
**优先级建议**：5
**完成判据**：
- 三方一致抽查：同一 dtag 在 journal 回执、strategy jsonl、报告依据块三处语义一致（局 id + dtag 样本摘录）；
- 完成前常规检查（本文首节，如有代码改动）
**验收凭据形式**：三方对照摘录（局 id + dtag 样本）

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1-3.5
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`（回执契约节，~:2157：dtag 键语义；正本家 = 代码注释自指 `cw_game_state.py:1384-1385`） ← 3.2（已完成 3.2）
- `docs/develop/sr_od/application/currency_war/strategy-docs/strategy-telemetry.md`（新篇：信封键闭集 + mandate_v1 payload 键表；3.3 已建，收尾核对） ← 3.3（已完成 3.3）
- `docs/develop/sr_od/application/currency_war/strategy-docs/README.md`（分篇入口登记新篇） ← 3.3（已完成 3.3）
- `skills/sr-od-currency-war-dev/references/match-review.md`（报告结构：动作节「策略依据」小节 + 章级「策略依据」小节 + 章尾注记 + 局头策略遥测行） ← 3.4（已完成 3.4）
