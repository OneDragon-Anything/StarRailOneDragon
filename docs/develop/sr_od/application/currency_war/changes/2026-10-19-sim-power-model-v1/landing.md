# sim 战斗结算机制化(战力模型 v1)落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(测试仓 `sr-od-test`,相关子集;sim/训练管线改动至少跑 `sr-od-test/test/sr_od/application/currency_war/sim` 子集);
- 训练/抽取脚本不进 src 主包运行路径(power_model/ 内,产物落 `.debug`,零主流程副作用);
- 测试零真实副作用:fixture 入测试仓,禁读本机易失产物(项目测试规范);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 语料抽取器(旧流)+ 语料盘点

**范围**:①许可集普查:逐目录裁定 source(实机/sim)——已核实实机 = `telemetry/live/`(712/90 行);待盘点候选 = `.debug/currency_war/p3_ab/` 4 目录与 `2026-09-21-gs1-exit-channel-ab/` smoke 2 目录;`telemetry/sim/` 全目录默认排除(铁律 2);普查清单与逐目录裁定记录随产物。②decisions/outcomes 行 → 训练样本行:canonical 口径(join 键/快照规则/去重与降级/坏局排除/标签);字段映射按实况(`state.board`/`state.deployed`,无 `board_factions`;顶层 `target_comp` 覆盖率统计上报);双侧同源特征函数(design §2.2 表全量)+ 两侧对齐测试;③幅度样本表产出(败局 hp 结算行+协变量+删失标记,供 3.4);④丢弃按 source×位面分桶披露 + 产物头部源指纹。**不含**:journal 通道(3.8)、训练本身(3.2)。
**设计依据**:design.md §2.1/§2.2/§2.3/§2.4;输入守卫先例 = sim-power-model §8.1 第 1 项(解析后路径精确相等断言)。
**文件面**:`src/sr_od/application/currency_war/sim/power_model/`(新增);`sr-od-test/test/sr_od/application/currency_war/sim/`(新增测试)。
**依赖**:无。
**优先级建议**:8
**完成判据**:
- 许可集普查清单 + 逐目录 source 裁定记录产出;
- 三数重钉(战斗类结局/有标签/胜事件)写入产物头部;
- 双侧同源对齐测试通过;`target_comp` 覆盖率与值域构成统计产出(注册套名/组合标签两族);
- 幅度样本表产出;丢弃分桶表 + MNAR 缺失率披露产出;
- 完成前常规检查(本节首)。
**验收凭据形式**:测试名 + 产物头部指纹与分桶表 + 普查清单。

## 3.2 训练与校准脚本

**范围**:离线训练 logistic(符号约束:过渡分档/总星深/核心星深 ≥ 0,难度 ≤ 0;终局取大与 node_type/round 自由)+ LOCO + 校准曲线 + df=tr(Ĥ) 预算核算 + **按裁剪序装配**(design §2.2)+ **预算重钉门**(重钉 < 6 → 挂起交用户三选一,见 design §2.1)。产出 = 权重常量表草案 + 校准报告。
**设计依据**:design.md §2.2/§2.3;sim-power-model §4.3/§5.3。
**文件面**:`sim/power_model/`(训练脚本);`sr-od-test` 对应测试。
**依赖**:3.1
**优先级建议**:8
**完成判据**:
- 校准报告产出:三数重钉实数 + LOCO 分节点类结果 + 校准曲线 + 最终参数清单(含裁剪序装配过程与砍单申报,如有);
- 权重常量表可复现(重跑训练脚本 → 同一权重);
- 若触发预算重钉门:挂起报告产出且账本置 wait,不自行降级;
- 完成前常规检查(本节首)。
**验收凭据形式**:校准报告 + 权重表(数字对照)。

## 3.3 模型查询面子包

**范围**:`power_model/` 查询面(板面快照/GameState → win_p 与特征向量);权重常量表入库;依赖方向锁(AST 静态白名单断言 + 重导出审计 + data/ 零产物 + sim/replay 目录隔离测试)。**不含**:结算接线(3.7)。
**设计依据**:design.md §2.5;sim-power-model §6.2。
**文件面**:`src/sr_od/application/currency_war/sim/power_model/`;`sr-od-test/test/sr_od/application/currency_war/sim/`。
**依赖**:3.2
**优先级建议**:7
**完成判据**:
- 依赖锁断言测试全绿(白名单外零引用/零重导出/零 data/ 产物);
- 查询面单测:同输入同输出;特征缺省 None = 旧行为等价;
- 完成前常规检查(本节首)。
**验收凭据形式**:测试名(依赖锁 + 单测)。

## 3.4 幅度层条件化(估计与采样器,不接线)

**范围**:位面×节点类型离散直方重估 + 达成度均值匹配系数(协变量 = 过渡达成度分档;每节点类型 intercept/slope/池均值,CI 含 0 退常数;非P1 分层斜率样本不足同退常数)+ boss 钳制与删失纪律(截断观测不入直方)+ 伪影档剔除;独立采样器模块 + 单测(区间/地板/钳制/退化常数路径);CALIB 语义版本常量。**不含**:settle_battle 接线(3.7)。
**设计依据**:design.md §2.4;前代同构参照 `git show 8c9e8aafc~1` cw_coarse_battle 直方/_LOSS_FIT 段。
**文件面**:`src/sr_od/application/currency_war/sim/power_model/`;`sr-od-test/test/sr_od/application/currency_war/sim/`。
**依赖**:3.1(幅度样本表)
**优先级建议**:7
**完成判据**:
- 直方与系数表从语料可再生(重跑估计脚本 → 同表);
- 采样器单测覆盖:常规/地板/钳制/斜率退化常数四路径;
- 版本常量就位(CALIB 递增纪律);
- 完成前常规检查(本节首)。
**验收凭据形式**:系数表(数字对照)+ 测试名。

## 3.5 难度特征供给核查(无新生成面)

**范围**:核查 sim 对局难度特征供给链——查询面读到的 enemy_difficulty = RunConfig 写入现值(match 级常量;现役写点 `_update_difficulty_flag`/`_record_difficulty` 语义不变,零新增写点);缺失指示仅真缺失行置位;监控「结构性缺失」缺省判定申报(新生成对局缺省路径难度恒在)。逐战斗难度采样(位面×轮次耦合)为正本 §6.7 deferred 面,不在本阶段。
**设计依据**:design.md §2.5/§2.8-6;sim-power-model §6.5/§6.7。
**文件面**:`src/sr_od/application/currency_war/sim/power_model/`(核查脚本);`sr-od-test/test/sr_od/application/currency_war/sim/`。
**依赖**:3.3
**优先级建议**:6
**完成判据**:
- 核查记录:新生成 sim 对局中查询面难度读数 = RunConfig 值(非空率 100%);
- 缺失指示单测(仅真缺失置位);
- 零新增写点核对(现役难度记账测试全绿);
- 完成前常规检查(本节首)。
**验收凭据形式**:核查记录 + 测试名。

## 3.6 影子接线 + 输入分布监控落位

**范围**:sim 账本双写 `model_win_p` 与现行常量披露位;跑批产出分歧分布(按节点/达成度分段)+ 外推段对照表;输入分布监控两类报警(结构性缺失 vs 真漂移)落位。**不改掷定**。
**设计依据**:design.md §2.3 影子期门/§2.5/§2.8-2;sim-power-model §6.3/§6.5。
**文件面**:`src/sr_od/application/currency_war/sim/cw_sim_battle.py`(账本披露位);`src/sr_od/application/currency_war/sim/power_model/`;`sr-od-test/test/sr_od/application/currency_war/sim/`。
**依赖**:3.3、3.5
**优先级建议**:6
**完成判据**:
- sim 批账本含双披露字段;
- 分歧分布 + 外推段对照表产出并交编排者判读(转正门的判读材料);
- 监控两类报警可演示(结构性缺失不触发动作/真漂移超阈报警);
- 完成前常规检查(本节首)。
**验收凭据形式**:披露字段样例 + 分歧报告 + 报警演示记录。

## 3.7 胜负面与幅度层接入

**范围**:`settle_battle` 胜负常量换注入 win_p(全域接管,无回退分支;掷点仍走 M13 流键)+ 败局扣血换幅度层采样器(伤害随机量消耗序重排按流键纪律申报)。前置门 = 3.6 影子判读收敛 **∧ 转正量化门达标(design §2.3:LOCO 校准 + 判别力存在性)**(编排者裁决,非本阶段自查)。
**设计依据**:design.md §2.4/§2.5;sim-power-model §6.1。
**文件面**:`src/sr_od/application/currency_war/sim/cw_sim_battle.py`;`sr-od-test/test/sr_od/application/currency_war/sim/`。
**依赖**:3.3、3.4、3.6(影子判读收敛 + 转正门达标)
**优先级建议**:5
**完成判据**:
- 接线测试:注入 win_p 驱动胜负频率(统计对照);幅度层采样路径生效(直方值域);
- M13 流键消耗序不变性测试(同 seed 同局可复现性保持;幅度消耗序重排已申报);
- 测试仓 sim 子集全量一次通过;
- 完成前常规检查(本节首)。
**验收凭据形式**:测试名 + 统计对照数字。

## 3.8 journal 增量抽取通道

**范围**:journal 写行 → 训练样本行抽取器;字段映射规格小节随抽取器交付(标签 = hp 结算写行差分 **与 hp_floor 事件行并读**;板面从 `state.values.deployed` 重计;run_id 水位对局切分);幂等;产物带源指纹。测试用测试仓内 journal fixture,**禁读本机易失产物**。**不含**:重训自动化(里程碑触发纪律照 sim-power-model §8 第 8 项)。
**设计依据**:design.md §2.7。
**文件面**:`src/sr_od/application/currency_war/sim/power_model/`;`sr-od-test/test/sr_od/application/currency_war/sim/`(含 fixture)。
**依赖**:3.1
**优先级建议**:4
**完成判据**:
- 字段映射规格小节入库并过验收;
- 对测试仓 journal fixture 抽出训练样本行,与旧流产物同表结构;
- 幂等测试(重复抽取零增量);
- 完成前常规检查(本节首)。
**验收凭据形式**:规格小节 + fixture 抽取产物对照 + 测试名。

## 3.9 版本迁移申报 + win_model M1 supersede 停用 + 共生对照操作定义

**范围**:①`telemetry/cw_win_model.py` 影子件 supersede 停用(防双 P(win) 模型源;M1 现状影子不接线,停用低风险)+ 其特征/检查依赖面随停用清理;②幅度层/胜负层版本常量(CALIB 语义版本)迁移申报;③本迭代新增监控面(3.6 两类报警)的常驻归属登记;④共生对照机制操作定义文档化(正本 §8-9:模型外策略臂对照局配额/触发与判据),落 `sim-power-model.md` 同目录或迭代产物,防「策略朝模型认为好的方向演化」。**边界申报**:正本 §8 第 7 项所列 `sim/checks/` 目录与 `check_p2_*`/`check_boss_win_calibration` 检查不现役(该重锚面随实体消亡);`kernel/cw_anchor.py` 的 ANCHOR_REGISTRY 本体现役且含 battle_start/settlement 战斗类锚——本阶段「现存检查面普查」必含该注册表:全仓扫描与本迭代输出字段相关的现役检查与锚,逐个判重锚/失活/无关,普查记录即凭据。
**设计依据**:design.md §2.5/§2.7;sim-power-model §6.2-5/§6.5/§8 第 8/9 项。
**文件面**:`src/sr_od/application/currency_war/telemetry/cw_win_model.py` 及其依赖面;`src/sr_od/application/currency_war/kernel/cw_anchor.py`(如普查命中);`sim/power_model/`(监控归属);对应测试。
**依赖**:3.7
**优先级建议**:3
**完成判据**:
- M1 停用后全仓无消费面残留(ruff + 测试);
- 现存检查面普查记录产出(逐个重锚/失活/无关三态);
- 版本迁移申报 + 共生对照操作定义文档入库;
- 完成前常规检查(本节首)。
**验收凭据形式**:普查记录 + 测试名 + 文档。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:全部落地阶段。
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/currency_war/sim/sim-power-model.md`:§4.3 首期实装分配表(双轨达成度 14 设计位裁剪序版)+ 现状注记(as-built 化:已实施面/首期范围/deferred 面) ← 3.2/3.3/3.7 全部落地后
- `docs/develop/sr_od/application/currency_war/sim/sim-design.md`:§8.2 战斗结算行(随机输出面 → 模型胜负面 + 条件化幅度层描述) ← 3.7
- skill `sr-od-dev-currency-war` references/sim-testing.md:「sim 战斗结算=随机输出面」边界条目改写为模型口径(幅度/校准未验收面仍禁外推) ← 3.7
- `docs/develop/sr_od/application/currency_war/sim/sim-power-model.md` §2 四路径表/§6.1 接线点表:按当期结算形态重钉(原表引用的 cw_coarse_battle/engine_p1 已不存在) ← 3.9
