# 旧账卫生与运维收编 迭代设计（总纲）

## 0. 元信息
- 迭代目标：账本 `2026-09-11-cw-clear-run` 中非 state 链、非观察架构的旧账卫生与运维任务（T-13/T-14/T-16..T-27，共 14 项；T-15 属观察架构域不在其列）全部阶段化，按账本 deps 与文件面互斥真实排布为可独立验收的阶段序列（本迭代对应账本任务 T-33；背景 = 旧账交接检查点 `会话交接检查点-20260911.md` §未竟清单）。
- 状态：定稿（待复验；对抗审 13 项发现已逐条裁决落盘，记档见 attack.md §四）
- 正本落盘声明：本文件与 landing/details 引用的 `T-280-交付报告.md`、`T-322-实施-交付报告.md` 原始出处为 `.debug/temp/currency_war/`（临时区易失），定稿批已复制落盘至 `details/sources/`（附溯源 README）——下文引用一律指落盘正本，temp 路径仅作原始出处注记。
- 文档清单：
  - details/execution-seam-projection.md —— 执行缝账务与投影播种（T-16/T-17）
  - details/strategy-qualification.md —— 腾席资格面与代理收窄（T-18/T-20）
  - details/sim-baseline.md —— sim 基线校准、账本立卡与宝钻联动（T-21/T-22/T-23）
  - details/free-refresh-onboarding.md —— 免费刷新机制建档接入（T-13）
  - details/docs-hygiene.md —— 悬空引用清理与文档树迁移（T-24/T-25）
  - details/live-verification-and-rulings.md —— 实机验证族/用户亲核/候裁（T-14/T-26/T-27）

## 1. 问题与动机
- 现状症状：旧账（2026-09-06 redesign 账本）交接后，14 项卫生与运维任务已在现账本带预注册判据（`dag.py card T-<N>` 可查），但缺三样组织面东西：
  1. **统一设计**：各任务的文件面、与两个姊妹迭代（unified-state / unified-observation）的域边界、修复深度（点状修复 vs 结构改动）无单一声明面；
  2. **wait 任务阶段化**：6 项外部等待任务（T-13/T-14/T-16/T-18/T-26/T-27）的条件与复查时机散在账本 cond 字段，未写进可派工的阶段小节；
  3. **文件面互斥未排布**：多处真实冲突未串行化——`mandate_v1/shop.py` 被 T-18/T-20/T-24 三批触及；`mandate_v1/mandate.py` 被 T-16（m3_levelup_batch 段）/T-18（fuel_sell_candidates 及其调用点，mandate.py:248）两批触及；`operations/cw_screen/cw_screen_prep.py` 被 T-16（执行缝入账模块修点子集）与 T-23（back_size 消费位）两批触及；`sim/runner.py` 被 T-22/T-23 两批触及；doc 旧树被 T-24/T-25 与在飞迁移批（T-29/T-30）触及；`sim/engine_p1.py` 被 T-21/T-23 两批触及。（T-17 残余修复面 = kernel/cw_reconcile.py 单文件——三层落码面已由旧账 T-308 入库收窄，与 T-16 无文件交叠，仅 IC-2 语义排序在案；互斥清单只列真实同文件冲突，排布见 §3 依赖边清单。）
- 根因归层：**流程层**——旧账交接的批次化缺口，不是代码表示/语义缺陷（各任务自身的根因归层在其详设逐个给出：六份详设各任务节「根因归层」行；T-19 归层见 §2 内联设计）。
- 解决到哪：14 任务每任务一张阶段小节（landing.md §3.x），完成判据 = 账本 T-\<N\> criteria 预注册（追认式映射：阶段小节与账本一对一，设计改 → 小节改 → 账本 note/criteria 跟改，禁两处各自演化）；依赖与复查时机显式写进阶段小节；文件面互斥以依赖边或互斥声明排布。
- 明确不解决：state 链（unified-state 迭代，账本 T-1..T-7/T-9..T-12）；观察架构（unified-observation 迭代，账本 T-8/T-15）；策略行为调优（本迭代修复类任务均为正确性/账务/资格面，零策略行为语义——T-280 报告 §③ 已申报其批零策略语义，同口径约束全迭代）；实机通关（T-28）本身。

## 2. 方案
- 系统级变化：**零架构变化**。14 批各自为点状修复/校准/清理/建档/核证，独立可验收；编排序 = landing.md 阶段序。
- **域边界声明（与两个姊妹迭代的接口契约，全迭代约束）**：
  - unified-state 域（kernel/cw_state.py 本体 = W8 切割对象；mandate_v1 决策面 = W6 统一容器对象；cw4 键载体 = T-4 对象）：本迭代任务在这些面只做**点状修复/校准/清理**，禁结构性改动；凡修复需要动域结构 → 停手，回任务书指认的设计依据章节提请修订（停手令，见 iteration-design.md §5 硬规则 2）。
  - unified-observation 域（obs/ 读面结构、相位屏统一观察基类 = 账本 T-8/T-15）：同上；本迭代允许触碰 obs/ 下**值计算语义**（如 T-23 的 back_layout 容量值源），禁动读面结构。
  - 跨迭代互斥：在飞窗口互斥由编排者控制。时序主张（按 T-308 后世界态改写）：**T-17 残余修复（= P3 小修，涉 kernel/cw_reconcile.py 单文件）先于 unified-state 的 W6 开工**——W6 的 applied-gate 复用 cw_reconcile.py，禁在其上叠批。原主张「T-17 必须先于 W6/W7/W8 开工落库」废止：其标注依据 T-280-交付报告.md §③ 冲突时序段（现落盘于 details/sources/）原文只含「排当前在飞批 commit 入库之后（禁半-tree 叠批）」，通篇无 W6/W7/W8 字样，属外推挂引用名下；其核心前提「T-17 改动面含 kernel/cw_state.py（W8 切割对象）」已被 T-308 交付推翻（方案申报面实际收窄 = cw_state.py 零触碰，见 bd27989d4 入库笔）。该在飞批即时序条款所辖批本身（T-308 落码批），入库条件已于 2026-09-11 12:42 兑现。
  - **编排者裁决（2026-09-12 迭代设计定稿时，原文照录）**：「sim 门辖域=用户裁定 state 链(T-1..T-7、T-9..T-12、T-15)全 done 前禁一切 sim 批,故 T-17 的「连续批跑 0 WARNING 取证」段显式挂 sim 门后执行,不构成 W6 前置;W6 前置仅残余修复+复验」。
  - 与 r5-migration-plan.md §2 并行约束的相容性：时序窗真实存在（W6 = T-5 进入门 = W5 绿 + T-4 键载体绿，卡面与 r5 §2 一致；T-4 门 = C1-C8 候用户裁决，T-1 wait 在案）；r5「同一时刻最多两波在飞」辖 unified-state 波间，不禁止外部卫生批插窗；W5 已于旧账闭环，无第三方文件域冲突源——不相容的只是已废止的旧依据与 sim 门辖域含糊，经上条裁决后无冲突。
- **跨详设接口契约（总纲定死，详设不得各自演化）**：
  - **IC-1 腾席资格单源**：T-18 定谳的 `fuel_sell_candidates` 生产资格面 = T-20 `seat_recoverable` 代理收窄的判定基准单源。T-20 落码引用该资格面，禁平行第二实现。
  - **IC-2 执行缝账务包络**：T-16 备战帧金动作入账落点 = T-17 S1/S2 落地后的 pad 态布局契约与 guard 形状。**契约本体已由旧账 T-308 落码批入库（bd27989d4；语义锚 = flow/projection_contract.md）**——T-16 的前置收窄为：①开工前对已入库契约做一次复核（读 HEAD 确认 guard 形状与 pad 态语义）；②候 T-17 残余修复（P3 小修，cw_reconcile.py 健康门拒绝分支）落库，以残余修复后形状为修点定谳基准（该小修与 T-16 文件面不相交，串行为保守排布）。禁在其前置入账形状上开工的旧表述随契约入库失效。
  - **IC-3 sim 基线锚申报**：T-21/T-22/T-23 任一改变 sim 行为或账本行语义 → 批交付必附段表登记/池指纹申报（A/B 可比性；规程先例 = 旧账 T-307/T-313 A/B 对拍段表登记）。
  - **IC-4 文档路径基线**：T-25 迁移完成 = `docs/develop/currency_war/` 旧路径废止，此后一切文档写批用新地址；迁移前开工的文档写批用旧路径、随 T-25 迁移。
  - **IC-5 悬空引用处置口径**：已删除 ADR 的残留引用 = 改写为纯语义描述或删除引用；禁重建 ADR、禁改 ADR 历史原文（immutable 先例，T-322 落地审申报「ADR 历史原文不改」）；新 ADR 候用户命令（AGENTS.md 决策记录条）。
  - **IC-6 屏幕读面边界**：T-13 建档/读链接入走 screen_info + 现行读链；统一观察基类迁移属 unified-observation 迭代（T-8），本迭代禁做结构性迁移。
  - **IC-7 免费刷新计数载体单源**：效果授予的免费刷新**计数载体归 unified-state 效果线**（账本 T-9..T-12，尤其 T-11「条件判定型免费刷新效果结构化 wire」）。`data/cw_invest_data.py` 在册的是 PlazaAugment **效果文本**（`effect='获得N次免费刷新'` 字符串），非可消费计数载体——T-13 消费段以效果线 wire 产出为唯一计数源；效果线未落期间消费段只允许屏读通道 + 候裁，禁在执行面自造第二计数源（防双源，attack.md F6 裁决）。
- **全局工程约定（各阶段完成判据引用，代号 GC）**：
  - **GC-1 留树面对账**：每阶段开工前 `git status` 逐文件核对本阶段文件面；在飞 hunks 逐文件避让申报或候其入库；禁半-tree 叠批（先例 = T-280-交付报告.md §③「排当前在飞批 commit 入库之后」）。
  - **GC-2 commit 卫生**：逐文件点名 `git add`（禁 add -A/目录级）；message 含任务 id 与阶段名；只 commit 不 push（AGENTS.md worker 批 commit 授权）。
  - **GC-3 测试口径**：ruff 只查本批修改的文件；CW 子集 = `uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"`；全量仅 commit 前跑（测试分层单一源 = sr-od-currency-war-dev skill **SKILL.md**「单一源地图·测试分层」行；references/strategy-work.md「验证」为其下游指针）。
  - **GC-4 ADR 用户命令制**：凡上游材料出现「落码批 ADR」义务（如 T-280 报告 §③ 证明归宿声明），一律转为交付报告技术方案节 + 代码注释义务；注释引用只指既有 ADR；新 ADR 候用户命令。
- **T-19 内联设计（单件微修，无详设）**：`tools/cw/review_skeleton.py` 对 `merge_round_rows` 的死引用修复。**根因归层**：流程层（模块搬移后引用同步缺口——导入路径失效，非语义缺陷）。修法边界 = 将该引用改为函数现居模块的合法导入路径；若函数定义位已不存在，则以复盘骨架的最小语义等价实现补齐并在注释声明出处。唯一行为判据 = 脚本亲跑复现通过。零其他改动（依据 = 旧账 T-296 卡「零行为工具面修复」；文件面 = tools/cw/review_skeleton.py）。
- 详设划分：6 份（清单见 §0）。实现某阶段只读本总纲 + 该阶段 landing.md 小节指向的详设。

## 3. 账本依赖边清单（F3 定稿必修；账本动作申报，由编排者落账）

> 账本 14 张阶段卡前置现仅 T-33，landing/本总纲声明的阶段间关系在账本零建边——「ready 首行派单」口径下 T-16/T-20/T-24/T-25 会与其前置并行放出，单源契约只活在散文里（attack.md F3）。下表按 od-dev-progress-tracking §5 分判列出全部应建边；**landing 各阶段小节「依赖」字段与本节一一对应**。本批无账本写权限，落账由编排者执行。

| 依赖边（依赖方 dep 被依赖方） | 类型 | 依据 |
|---|---|---|
| T-16 dep T-17 | 语义单源（IC-2） | 入账落点复用 pad 态契约与 guard 形状；契约本体已由 T-308 入库（bd27989d4），开工基准 = T-17 残余修复落库后形状 |
| T-20 dep T-18 | 语义单源（IC-1） | 收窄基准 = T-18 定谳资格面，禁平行第二实现 |
| T-24 dep T-30 | 文件互斥（recovered 树） | changes/2026-09-11-unified-state/details/recovered 文件在 T-30 范围；**T-30 已 done 仍记边，固化排布** |
| T-25 dep T-29 | 文件互斥（doc 树） | changes/ 找回面落定，防新文档落错树 |
| T-25 dep T-30 | 文件互斥（doc 树） | 同上 |
| T-23 dep T-21 | 文件互斥（sim/engine_p1.py） | landing §3.5/§3.7 互斥排序 |
| T-23 dep T-22 | 文件互斥（sim/runner.py） | landing §3.6/§3.7 互斥排序 |
| T-18 dep T-24 | 文件互斥（mandate_v1/shop.py） | T-24 清引用先行（landing §3.2/§3.8；T-20 经 T-18 传递覆盖） |

**账本动作申报**（编排者逐条执行）：

1. 建边（8 条）：`dag.py dep T-16 --add T-17`；`dep T-20 --add T-18`；`dep T-24 --add T-30`；`dep T-25 --add T-29`；`dep T-25 --add T-30`；`dep T-23 --add T-21`；`dep T-23 --add T-22`；`dep T-18 --add T-24`。
2. 末阶段卡（F12，正本更新批现无卡可派）：`dag.py add "legacy-hygiene-ops 末阶段：正本更新" --module 支撑 --dep T-13,T-14,T-16,T-17,T-18,T-19,T-20,T-21,T-22,T-23,T-24,T-25,T-26,T-27 --criteria "landing.md 正本更新清单清零；正本与实现一致（文档对照 review）"`（建议 T-33 验收时即立）。
3. T-24 计数快照勘正（F13，criteria 括号计数为记账时点快照）：`dag.py note T-24 "criteria 括号计数(20处/11文件)为记账时点快照已过期：定稿时点实测 25处/12文件（不含本迭代 attack.md 自引）；机械判据 0 命中不受影响，以开工时 grep 重跑为准"`。
4. T-17 卡语义注记（F1，防按旧详设重做已入库面）：`dag.py note T-17 "三层方案+顺路面三件已由旧账 T-308 落码批入库（bd27989d4，落地审 accept）；本任务=残余收尾：①P3 小修(cw_reconcile 健康门拒绝分支 sorted 混型防御+返回值 docstring)②连续批跑 0 WARNING 取证(挂 sim 门，不构成 W6 前置)③实机候窗回归④T-308 凭据与 criteria 对账记档；禁重做已入库面"`。
