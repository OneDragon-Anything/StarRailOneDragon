# 设计对抗报告

## 第 1 轮（三核：无前提攻击 / 规范遵循 / 治本核验）

- 审对象：design.md + landing.md 草案（fc80e4455）
- **三核总评**：归层成立（per-run 重置抹局级事实，源码逐行验证）、方向成立、无阻断级事实失误（核三口径）；核一口径 4 阻断全部集中在「每次运行重建」的实现判据——**「运行」边界未定义**。最重关切「接管局在策略器侧能否跑」**核过**：缺口接管机制（tracked 失效写→商店门→heavy 重锚）、效果账本接管披露（零驱动降级）、环境授予最佳猜测、观察域自愈、level 守卫、补采谓词全部现役在位，接管局跑的是降级决策非崩溃路径——用户「补不到算了」裁定与系统现状精确对齐。

### 裁定汇总表

| 编号 | 来源 | 发现 | 处置 |
|---|---|---|---|
| A1 | 核一阻断1 + 核三§2-3 | 候选 b「运行内标志天然 per-run」不成立——ctx 跨 run 存活，需清位方且带脏窗口（入口链置位后 loop 未跑即停 → 标志残留 → 下局直撞误判保留脏容器 → 游戏若重启过锁定漏检） | 采纳：判据定稿**候选 a 变体**——容器记 `created_run_id`（establish 内部 ensure 前置再记，恒非 None），handle_init 比对不等 → 显式 discard + establish(takeover)；None = 外部装配保留 |
| A2 | 核一阻断2 + 核二§1-1 + 核三§2-6（三核同点） | sim 写入端失实：establish_new_match 无 sim 调用方；sim 容器 = 两处直接构造吃缺省值；重建判据会把裸构造容器弃掉 → sim 后端脱钩全崩 | 采纳：缺省值方向定稿（`opened_via` 缺省 `new_game` / `created_run_id` 缺省 None）→ **sim 直构点零改动**；T-4 grep 口径改「显式传参恰三处 + 缺省兜底登记」 |
| A3 | 核一阻断3 + 核二2-2 + 核三§2-2（三核同点） | opened_via 落地面指向不存在的调用方；漏列第四生产调用点（商店防御兜底 `cw_screen_shop.py::CwScreenShop.observe`） | 采纳：写入端三处（入口链/loop 兜底/商店防御，第三处=takeover 局外兜底语义）+ 缺省兜底登记 |
| A4 | 核一阻断4 + 核二2-4/2-3 | 停点分叉与交接批「max_rounds 不设常量」冲突（app 无判据识别该形态）；交接批修订面漏判定表（§2.5 非 §2.6）；交接批测试用例③与停点文本断言将被打红未列同步 | 采纳：**零 app 改动方案**（核三建议）——非 debug 停点在 loop 出口直接以交接前缀文本交出 → 三形态判定自动承接；不设常量维持；修订面修正（判定表补句 + 用例③改 is_debug 前提 + 新增 False 用例 + 停点文本断言同步） |
| B1 | 核三§2-1 | is_new_match 名实偏差：旧 True 集合 = 兜底建容器 ≙ takeover 而非 new_game——机械迁移会语义翻转 | 采纳：等价映射表（True↔takeover / False↔new_game）进 design §2.6，迁移判据按 takeover 方向写死 |
| B2 | 核一修订2 + 核三面3 | handle_init 弃旧建新必须显式 discard 前置（establish 幂等直过不弃旧，否则重整静默失效） | 采纳：landing T-1 ③ 写明先 discard 再 establish |
| B3 | 核一修订3 + 核三§2-5 | 手动逐轮验证工作流变更未申报（target 每轮重选振荡 + 探针每轮一次；现状注释明写靠跨 run 延用） | 采纳：§2.4 申报接受（裁定③字面覆盖），相关注释随批改写（T-5 清单补 prep_actions/establish/handle_init 注释） |
| B4 | 核一存疑1 + 核二2-5 + 核三§2-4（三核同点） | 「弃局重开」无自动承载机制（app 单次运行 + 应用组当日跳过）——实现二义 | 采纳：语义定稿「弃局回大厅，重开由下一次 app 运行承担」；同 run 自动重开属未来多局调度批 |
| B5 | 核二2-7 | T-4 grep 会被同名字段假阳性卡死（SettlementState/战斗等待 op 的 is_new_match 为值注入语义不随删除） | 采纳：复核口径宿主限定（Match 宿主零残留） |
| B6 | 核二2-6 | T-1 删字段中间态未定义 | 采纳：阶段重划——T-1 即完成探针门初步化（机制闭环），T-2 只做细化与失活回归 |
| B7 | 核二2-1 | landing 路径错：cw_resume_lock 在 obs/ 非 kernel/ | 采纳：已改 |
| B8 | 核一修订8 + 核二提示1 | resume_candidate 签名迁移未写；「必裁」黑话未定义 | 采纳：resume_candidate 退役（判据变化模块头申报）；「必裁」表述改「接管局必经探针裁决」 |
| B9 | 核二2-8 + 核一修订7 | prep_actions.py 过时注释引用未列修订面（is_new_match 引用将过期） | 采纳：T-5 清单补（前提强化，论证依据更新为 opened_via 口径） |
| B10 | 核二提示5 | max_rounds 配置用户语义变化未申报 | 采纳：§2.5 申报 + 配置注释随批同步（T-5） |
| B11 | 核二提示6 | 草案五开放点违反「带开放问题的定稿不存在」 | 采纳：§2.10 收敛声明——全部定稿，无遗留 |

### 存疑与驳回

- 核一存疑2（stale-flag 子形态）：候选 a 定稿后该形态消失，无需裁定。
- 核三§3-2（手动逐轮开口子）：按裁定②③字面不接受开口子，申报即可（B3）；未来调试需要再裁。
- 核二提示2/3（验收凭据形式字段缺、影响面申报节缺）：前者本批 landing 补齐，后者为域级实践漂移提请规范侧，本批不个体加。
- 核二提示7（AGENTS §10 所指 terminology.md 不存在）：terminology.md 已于 2026-11-19 解散删除（用户裁定 b），AGENTS 指针行同步删除属另一会话在飞面——非本批问题不动。

## 第 2 轮（双核：核销 + 新眼）

- 审对象：第 1 轮修订稿 design.md + landing.md（f4538e8b0）
- **核 A（核销）**：第 1 轮裁定 A1-A4/B1-B11 处置全部落实、无走样；另抓 N1-N4 四项修订面遗漏（与核 B R 系大面积重合，合并处置，不单列）。
- **核 B（新眼）**：1 阻断 + 7 修订 + 2 存疑；总评「需再修（轻），修完可进第 3 轮判据专项复核，无需再发全稿对抗」。

### 裁定汇总表

| 编号 | 发现 | 处置 |
|---|---|---|
| B-1 | establish 内 ensure_run_started 与建容器的先后未定序：若 ensure 前置，match=None 铸段后入口链三分支 ensure（传容器）再铸段 → created_run_id（第一段）≠ handle_init 时点 run → 每局入口链首 execute 误判重建 | 采纳：design §2.4 三段式定稿（先建容器 → ensure(match=新容器) → 记 created_run_id，落法唯一禁变体）；landing T-1 ② 同步 |
| R-1 | 重建判据缺 None 守卫：外部装配容器（sim 直构）created_run_id=None，`!= 当前 run` 对 None 恒真 → sim 容器被误弃 | 采纳：判据自足式（容器存在 ∧ created_run_id is not None ∧ != 当前 run），None 短路为保留；design §2.4 + landing T-1 ③ |
| R-2 | difficulty 配套缺口：入口链 establish 调用点在难度读取之前，establish 时难度恒空 | 采纳：难度读取段挪到 establish 之前（同节点相邻段），establish 传 `ctx.cw_selected_difficulty or ''`；design §2.4 + landing T-1 ② |
| R-3 | 保留集合漏「上次运行未收尾残留」子集；重建路径遥测时序副作用（铸造点前移/双段 journal）未申报 | 采纳：design §2.4 补保留集合括注 + 遥测时序副作用申报（空段零 journal 行、口径注释随批同步，已知代价接受） |
| R-4 | landing T-1 判据与 design 修订不同步（缺 None 守卫/三段式/difficulty 挪序），注释同步项漏列（battle_wait 注入注释 / telemetry 铸造口径 / cw_strategy 禁读清单 / handle_init 手动逐轮段） | 采纳：landing T-1 范围与文件面全量同步 |
| R-5 | 停点 is_debug 两分支测试不显式 monkeypatch 则断言随环境缺省值随机红 | 采纳：landing T-3 ⑤ 补显式 monkeypatch 纪律 |
| R-6 | 停点弃局后游戏侧真清还是留保存局未核验——留保存局则下次开局走接管而非新局（玩家预期偏差） | 采纳：landing T-4 ④ 实机清单补「停点弃局后下次开局应无继续进度弹窗」核验项 |
| R-7 | landing §3 正本路径不完整（skill references 缺全前缀）、loop.md §6「非退出触发边界」段漏点名、T-1 注释改写项漏复核位 | 采纳：§3 补 skills 全前缀 + §6 段改写点名 + 新增注释同步复核项 |
| N1-N4 | 核 A 修订面遗漏四项（landing T-1 判据/文件面未随 design 修订同步、测试前提、实机清单等，与 R-2/R-4~R-6 重合） | 合并处置于对应 R 行落点，不单列 |
| Q-1 | 停点弃局后游戏侧保存局存留形态存疑 | 转 T-4 ④ 实机核验项（R-6 落点），实机回填 |
| Q-2 | SettlementState 新局标记字段是否随批改名存疑 | 默认案定稿：字段名不改（design §2.6——避免实现期两可，宿主限定 grep 口径与之兼容） |

### 修订面落点

- design.md：§2.4 重写（三段式定稿 + None 守卫 + difficulty 挪序 + 保留集合括注 + close_run 依赖脚注 + 遥测时序副作用申报 + 手动逐轮申报）；§2.6 重写（等价性如实化——SettlementState 不改名 + takeover 集合扩容为有意变更 + relaunch 30s GRACE 窗错标申报）。
- landing.md：T-1 范围/文件面、T-3 ⑤、T-4 ④、§3（见上表 R-4~R-7 行）。

## 第 3 轮（判据专项核销，单核）

- 审对象：第 2 轮修订稿 design.md §2.2/§2.4/§2.6/§2.7 + landing.md T-1（358230cca）
- **总评**：「需再修（轻）后进定稿」——判据本体全部核过可实现且方向正确；必修一处事实订正 + 一处插槽澄清（均已落，表述级，不触判据本体）。

### 判据核销表（摘要）

| # | 判据 | 结论 | 要点 |
|---|---|---|---|
| 1 | establish 三段式可实现性 + 禁前置论证 | PASS | 幂等门/容器构造/ensure 铸段自赋证据齐；入口链三分支 ensure（简报/投资环境/投资策略）传容器，「ensure 前置必二次铸段 → created_run_id 错位」论证在真实代码成立 |
| 2 | handle_init 六场景判据闭合 + None 短路 + discard 前置 | PASS | 六场景逐个走查结果与设计表一致；establish 幂等直过不弃旧 → discard 显式前置必要；discard+establish 衔接有生产先例（cw_screen_shop） |
| 3 | 消费点迁移方向（旧 True ≙ takeover） | PASS | 宿主限定 grep 全集（一写入点 + 三消费点）方向正确；SettlementState/战斗等待 op 同名字段甄别与 B5/Q-2 裁定吻合 |
| 4 | 缺省值方向与 sim 零改动 | PASS | 两直构点路径属实、裸构造吃缺省；「不探针 + handle_init 保留」方向正确 |
| 5 | close_run 依赖脚注 | PARTIAL → 已订正 | 框架全路径收尾属实；但「唯一不 close 分支该分支无容器」与代码不符——假局提前 return 分支可带容器触发且不清容器（该残留 = 保留集合括注已申报的无害形态，判据体系无洞）；脚注订正对齐括注 |
| 6 | difficulty 挪序可实现性 | PASS | 同节点相邻段换序无副作用依赖；establish 职级就地吸收接住已读难度，语义连续 |
| 7 | run_record 零副作用 | PASS | 运行记录只 import 框架 AppRunRecord，period/当日跳过判定与 CW telemetry run 零耦合 |

### 新发现与处置

1. **真假局提前 return 分支可带容器**（核销 5）→ design §2.4 脚注订正（已落）。
2. **establish 内 ensure 插槽未定**：若 ensure 插在容器赋值后、就地吸收段前，吸收 journal 行落重建路径「空段」，§2.4 副作用申报③失真 → landing T-1 ② 插槽澄清（ensure 在吸收段之后，已落）。
3. **「继续进度 × 假局残留容器」组合判保留**（opened_via 沿旧值，非六场景表第 5 行的兜底建 takeover）——与保留集合括注申报一致，非洞；表述澄清记录在案，不改判据。
