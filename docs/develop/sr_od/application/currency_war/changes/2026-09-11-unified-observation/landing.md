# 统一观察架构余项收口 落地

## 3.1 五相位屏迁移(账本 T-8)

**范围**:投资环境 `CwScreenInvestEnv`、投资策略 `CwScreenInvestStrategy`、战斗等待 `CwScreenBattleWait`、简报 `CwScreenBriefing`、BOSS 简报 `CwScreenBossBriefing` 迁 `CwScreenOpBase` 生命周期(装配点分流 + 五段钩子转录 + 实机适配器①封口 + 投资策略 `strategy_refresh_used` 登记件收编注册表)。边界:不含相位 1 深度统一、sim 接线、旧路径退役、收尾五屏(阶段三)、推进型基类(阶段二)。
**设计依据**:design.md §2;details/五相位屏迁移详设.md(逐屏五段表与语义保真点)。
**文件面**:`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_invest_env.py`、`cw_screen_invest_strategy.py`、`cw_screen_battle_wait.py`、`cw_screen_briefing.py`、`cw_screen_boss_briefing.py`;`cw_screen_op_base.py`(仅当登记申报面需增改);新锁文件与桩辅助在 `sr-od-test/test/sr_od/app/currency_war/`。
**依赖**:无。
**优先级建议**:8(对齐账本 T-8)。
**完成判据**:
- 五 op 均 `CwScreenOpBase` 子类 ∧ 各屏 start 节点方法顶部装配点分流(投资两屏/简报/BOSS 简报 = `handle`,战斗等待 = `wait()`;两端口完整在场 → `run_lifecycle`;缺省 None = 旧路径)——对照详设逐屏表(行为对照 = 详设「方案」节五段映射与语义保真点;重入裁决归属 = 总纲契约 6:分流前共享段,不进 observe/适配器①);
- 投资策略 `strategy_refresh_used` 收编接线锁(触发点唯一 + 随点击置位不等验效,B5-④ 策略屏同型断言)+ 登记语义对拍锁(值/evidence/produced_by 逐位);豁免留守锁(`active_env`/`active_strategies`/效果账本登记不入注册表收编面);
- 战斗等待在册行为锁经 `execute()` 走新路径全绿(B2-③ 主门);
- **投资环境/投资策略/简报/BOSS 简报新路径行为锁**(四屏各一,装两端口经 `execute()` 走新路径:段迹形态 + 单轮动作/确认置位行为;模板同构 = `test_cw_obs_arch_event_screens.py` :170-184 段迹断言、:247-259 单动作重试)——架构设计 §9.1-F2 主门 (a)「在册行为锁走新路径」扩至全五屏;
- **写入流对拍锁**(架构设计 §9.1-F2 主门 (b) 落地面):`active_env` 选卡时点写(值/写时点 = 点卡前/produced_by)、`active_strategies` 重入裁决出口 append(值/时点)、简报三字段 session 写(词缀幂等辖「读+采」/boss 恒覆写/难度仅 None 写)逐位对拍;结算观察半直写(D-94 时序)经战斗等待在册行为锁的轨迹断言承载;
- **判别单一源消费面锁**(`is_boss_briefing_texts` 消费点集合迁移前后不变:消费点 = `cw_loop.py:1989`/`cw_screen_battle_wait.py:218,:222`/`cw_screen_boss_briefing.py:69`,后两处本阶段辖域;防转录顺手复制判别逻辑);
- sim 腿不适用例外清单逐屏落测试 docstring(T-8 判据原文);
- §12 通用工程门(od-dev-progress-tracking §12;含 `ruff check` 仅改动文件、测试纪律)。
**验收凭据形式**:新锁文件全绿(命名沿 `test_cw_obs_arch_*.py` 系)+ L1 快速集命令输出(`uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"`)。

## 3.2 推进型基类收编

**范围**:`CwProgressionScreenOp` 改继承 `CwScreenOpBase` + 变体五段钩子缺省实现(空决策合同逐字保留)+ `handle` 顶部分流;11 子类零改动随之收敛。边界:不改任何子类文件;不改变体骨架语义(预算 2/重入裁决/免锚形态)。
**设计依据**:details/推进型基类收编详设.md。
**文件面**:`src/sr_od/application/currency_war/operations/cw_screen/_progression_base.py`;新锁文件在 `sr-od-test/test/sr_od/app/currency_war/`。
**依赖**:无(与阶段一不同文件面,可并行派工)。
**优先级建议**:5。
**完成判据**:
- 变体结构锁:`CwProgressionScreenOp` 是 `CwScreenOpBase` 子类 ∧ 11 子类 AST 全量为其后代 ∧ `handle` 含分流判据 ∧ 变体五段钩子在(observe 早退语义 + decide 空申报);
- 既有行为锁原样保绿(锁红先按详设「测试与锁面」节重推锁语义,修锁在报告对照表申报);
- 写入流对拍:本阶段无适用面(空决策合同零写端,如实申报;design.md §2.2-4);
- §12 通用工程门(同上)。
**验收凭据形式**:变体结构锁 + 相关锁 + L1 快速集输出。

## 3.3 收尾屏迁移

**范围**:位面过渡 `CwScreenPlaneTransition`、武装箱弹窗 `CwScreenArmoryBox`、未达上限弹窗 `CwScreenDeployNotFull`、等待1-1 `CwScreenWaitOneOne`、位面情报采集 `CwScreenPlaneIntel` 直迁 `CwScreenOpBase`(转录手法同先例;位面情报采集保留双节点图)。边界:不含相位 1 深度统一、sim 接线、旧路径退役;五屏均不重挂变体。
**设计依据**:design.md §2;details/收尾屏迁移详设.md(逐屏五段表)。
**文件面**:`src/sr_od/application/currency_war/operations/cw_screen/` 对应五文件;新锁文件在 `sr-od-test/test/sr_od/app/currency_war/`。
**依赖**:3.1 + 3.2(收口锁判据需三阶段全量交付后才成立——iteration-design §3.1「判据依赖另一阶段未完成部分 = 排进依赖」;五屏直迁手法本身无技术前置,先例已在册)。
**优先级建议**:3。
**完成判据**:
- 五 op 结构锁(同阶段一判据第一条口径,适用子集;分流措辞 = 各屏 start 节点方法顶部,位面情报采集 = `collect()` 节点首行);
- 位面情报采集纯函数三件既有测试锁原样保绿 + 双节点图边保留断言;
- sim 腿不适用例外清单逐屏落测试 docstring;
- 写入流对拍:本阶段无适用面(五屏零 BoardState 写端;位面情报采集 ctx 中转原样,如实申报;design.md §2.2-4);
- **收口锁**:cw_screen 全目录画面 op 均为 `CwScreenOpBase` 后代(AST 断言,落本阶段锁文件)——B4 判据第 1 条的 `cw_screen/` 目录达成凭据(达成面收窄:B4 点名清单余 `cw_op/` 商店系三件 `CwOpBuyCards`/`CwOpOpenShop`/`CwOpCloseShop` 直继 `SrOperation`,不在本迭代,挂账归后续批;design.md §2.1-4);
- §12 通用工程门(同上)。
**验收凭据形式**:锁文件 + L1 快速集输出。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:`docs/develop/currency_war/design/统一观察架构-画面op基类设计.md`(若账本 T-25 文档树迁移批已先落地,按其新址执行)。
**依赖**:全部落地阶段(3.1/3.2/3.3)。
**优先级建议**:0。
**完成判据**:清单清零;正本与实现一致(文档对照 review)。
**验收凭据形式**:文档对照 review(逐条清单项 diff)。

## 正本更新清单

- 《统一观察架构-画面op基类设计》§5.2 对应/替代关系表:事件屏行尾「投资两屏/结算/简报相位未迁屏现状不动」句 → 全量已迁现状 + 推进型变体收编行 ← 阶段一/二/三
- 同上 §3.4 收编映射表:简报/BOSS 简报/位面详情/敌人情报/中断弹窗行「迁移前现状不动」口径 → 已迁现状(宿主 = 基类驱动过渡 op/直迁 op) ← 阶段一/三
- 同上 §6.4 触发时点轴在册两件②:策略屏逐卡刷新计数「策略屏迁移批其写端入本面接线」→ 已接线 ← 阶段一
- 同上 §9.2 迁移步骤 4:余下画面顺序申报 → 余项收口完成态(含「相位 1 深度统一仍待独立批」的指针更新) ← 阶段三
- 同上 §2.5/§9.1:并存期双路径清单(旧路径退役候批面)按三阶段结果刷新 ← 阶段三
- 同上头部修订块(:33 v10 对照说明/:34-35 v5-v9 对照说明/:46 §12 联动清单「禁静默改」)与 §11 开放问题编号解码(:1098-1101「现行单一源」指针):四处 `.debug/temp/currency_war/*` 指针 → re-anchor 至持久位置——四件(开放问题清单/修订对照说明/T-217 流程hook设计/T-225 交付报告)正文已核实与 `recovered/` 副本逐字一致,可自 `recovered/` 取正文落正本同域持久目录(目标位置由执行批按文档区结构定;禁指 `changes/`〔正本禁引〕与 `.debug/`〔易失〕),或 ADR 化收编 ← 末阶段
