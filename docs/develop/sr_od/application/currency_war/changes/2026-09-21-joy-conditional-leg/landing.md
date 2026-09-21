# 欢愉契约条件腿建模 落地

## 3.1 条件腿 rider + 临时闩退役

**范围**:`kernel/cw_action_report/pick_planner.py`——`report_action_pick_planner_param`
新增 `rng` 关键字参数(缺省 None);落地相内、腿型分派前加条件腿 rider
(`active_env` 归一 == 欢愉契约 → `gain_character(random.choice([火花, 开拓者·欢愉]),
1, rand=True)`,evidence = `joy_conditional:<单位名>`);发射相零触发。
`kernel/cw_gain_chain.py`——删除 `JOY_PROVISIONAL_KIND` 常量、`on_env_gained`
欢愉契约翻来源分支与 provisional_mark effects 项,docstring 同步。**不含**:头号玩家
两选项本体模型改动、sim 接线、comp 评估消费。
**设计依据**:design.md §2.1-§2.4/§2.6
**文件面**:`src/sr_od/application/currency_war/kernel/cw_action_report/pick_planner.py`、
`src/sr_od/application/currency_war/kernel/cw_gain_chain.py`、
`sr-od-test/test/sr_od/application/currency_war/` 相关测试(test_cw_gain_chain/
test_cw_yinlang_phase32 及新测试文件,随批申报)
**依赖**:开工前核 tool-gain-report 在飞面(design §2.7)
**优先级建议**:5
**完成判据**:
- 行为对照 design §2.2-§2.5:双臂通道(未闩=rand/置闩=logic)、在册判定、rng 注入
  确定性、全腿型计数、发射相零触发、时序锁;
- 撤闊:`on_env_gained` 欢愉契约仅 immediate 腿,provisional 行零发射(design §2.6);
- 通用工程门:照 `sr-od-test/README.md`「提交」节(ruff + 受影响测试 + 相关全量)。
**验收凭据形式**:测试名(rider 双臂/在册判定/撤闩断言)+ 全绿运行。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:3.1。
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- `game_state/gain-chain.md`:§3 欢愉契约条件腿条目(临时闩标记面 → planner 触发
  回调模型,临时闩退役) ← 3.1
- `game_state/strategy-env-impacts.md`:欢愉契约行(若有;条件腿模型指针) ← 3.1(落地时核实该篇是否辖此面)
- `docs/game/currency_war/research/`(若条件腿机制结论入册:证据分级随实测) ← 视 3.1 实测,候选项
