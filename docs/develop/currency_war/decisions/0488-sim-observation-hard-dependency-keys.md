# ADR-0488: sim 观测硬依赖键补齐(bench_full_flag / board_next_tier / 分配器帧位披露)

## 背景

兑现链 v2 开关组(设计单一源 = `docs/develop/currency_war/prereg/w795_realization_design/REPORT.md` v2/v3 + 同目录 `PREREG_兑现链A_B.md` v3,自 `.debug/temp/` 迁入)落码后,W802 实施批在 REPORT §观测硬依赖边界声明中登记三项判读数据源缺口,归后继批清偿;W797 假设审计(`.debug/temp/currency_war/w797_assumption_audit/REPORT.md` §5,未迁移)实测确认三面不可测:

- `bench_full_flag` 生产决策帧恒 null——席满轮与腾席动作对齐不可评(D1 弱序量产对账依赖,锁 #10);
- ADR-0474 死亡窗分配器帧位无任何落盘消费面——`session.v3_alloc_frame` 每帧覆写但零披露,D2 接管只能金账反推(锁 #11);
- `board_next_tier` 恒空——「距下档几人」供给诊断面为空(Δp_tier 档位分解标定批前置;按 W803 勘误 N2 措辞:标定批前置,不阻塞开臂,M1 主判据局级聚合可算)。

## 决策

在 sim 引擎观测态(账本 `decisions.jsonl` 行)补五个观测键,全部为**纯披露、零决策消费**(禁观测改变决策状态):

| 键 | 位置 | 语义与消费方 |
|---|---|---|
| `state.bench_full_flag` | 账本行 state | 满栏旗标,**轮内逐决策段 OR 聚合**(生产 `merge_round_rows` 读端同式「任一帧置 1」;实测轮入口快照 40 局 0 亮、OR 聚合 10/360 行亮——bench 在轮内买入段才填满,入口快照系统性漏亮)。消费 = 锁 #10 D1 弱序量产对账。sim 满观测恒 bool(生产 bool\|None 的 None 态在 sim 不存在) |
| `state.board_next_tier` | 账本行 state | 各阵营下档阈值,决策入口快照;判据单一源 = `FACTIONS[].tiers` 取 >count 最小档(与 obs/cw_observation computed 支同一式,helper `_board_next_tier_of`)。消费 = Δp_tier 档位分解标定批(`realization_delta_p_tier` 标定前置) |
| `sim.alloc_frame` + `sim.alloc_active_any` | 账本行 sim | ADR-0474 分配器帧位披露:frame = 轮终帧 `session.v3_alloc_frame` 末值,active_any = 轮内任一段接管 OR。消费 = 锁 #11 D2 接管可观测性/D2 开臂验收 |
| `state.p1_downgrade_active` | 账本行 state | 末窗支出降格触发面(`p1_directed_downgrade_active`,session=None 裸评估不置闩)。消费 = W797 不可测项 A5 的 sim 触发面对账源 |
| `state.refresh_probs` + 行顶 `sess_active_env` | 账本行 | 轮岗概率条真值(None=未掷中)/投资环境名。生产分别覆盖 21% 与恒空的 sim 全量对账源 |

配套:`check_observation_keys_live` 哨兵入批检注册表(键缺失/形状错/分配域非法/OR-帧位自洽破,双向合成锁);结构锁非行为锁,不锁分布数值。

## Considered Options

- **board_next_tier 也做轮内 OR/逐帧**(否决):标定消费要的是「决策时点板面距下档距离」,入口快照与生产 computed 支同口径;多段快照增噪无消费方。
- **分配器接管做成生产 telemetry 写端**(本批不做,声明边界):生产写端在 ops 桶(recorder/`_extra`),超出本批文件面(sim 引擎观测态+checks+测试仓);sim 侧先行,PREREG v3 判据本就以 sim 批为数据源。
- **只登记不做**(否决):三键是 PREREG v3 判读硬依赖,登记≠清偿;纯披露零漂移,延迟无收益。

## 后果

- 行为零变更:全部键为纯观测披露,sim 决策/结算路径零触碰(策略/allocator/realization 桶零改动);回归 = 既有检查网全绿。
- W797 不可测 10 项逐项判定见 `.debug/temp/currency_war/w806_obs_keys/REPORT.md`:五项本批落地或已覆盖(`bench_full_flag`/`board_next_tier`/分配器遥测/`p1_downgrade_active`/`refresh_probs`+`sess_active_env`),`state.streak` 已有(前批资产),四项机制未建模不可行(`plane_modifiers`/`megastar_char`+`partner_char`/`focus_factions`)——sim 未建模对应玩法机制,观测键无从谈起,可行性以建模为前提另立项。
- 新检查 `observation_keys_live` 随批自动扫;键面断线=判读死输入,自此有报警面。
