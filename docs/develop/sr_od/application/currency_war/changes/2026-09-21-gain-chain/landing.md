# gain-chain 落地

## 3.1 链原语与回调(kernel)

**范围**:新建 `kernel/cw_gain_chain.py`——`gain_invest_env`/`gain_character`/`gain_equipment` 三原语 + `on_env_gained`/`on_character_gained`/`on_equipment_gained` 三枚举回调 + 单级合成函数(规则对齐 merge_simulate)+ 溢出落位 + `GainOutcome`;**零生产接线**(任何现有调用点不改)。
**设计依据**:design.md §2.1、§2.2、§2.3、§2.4、§2.7
**文件面**:`src/sr_od/application/currency_war/kernel/cw_gain_chain.py`(新);`sr-od-test/test/sr_od/application/currency_war/test_cw_gain_chain.py`(新)
**依赖**:无
**优先级建议**:5
**完成判据**:
- 行为对照 design.md §2.1(时序:落位 → 回调 → 升星 → 产物递归;溢出落位;池 = 备战∪上阵∪溢出)、§2.3(枚举内容;查无效果安静不写;advisor 分道)、§2.4(rand 透传与翻转)、§2.7(失败安全:未观察留证/溢出位被占留证)
- 单级×N 次终态与 merge_simulate 同池同输入对拍一致
- 通用工程门(项目测试规范 §10)
**验收凭据形式**:`uv run pytest sr-od-test/test/sr_od/application/currency_war/test_cw_gain_chain.py` 全绿(对拍/调用序桩测/rand 翻转/留证断言具名)

## 3.2 投资环境落地相接入

**范围**:`report_action_pick_invest_param` 增 `session: object | None = None` 参;portal 落地支改调 `gain_invest_env`;画面 op `_decide_and_act` 尾段删 active_env 写与 portal 登记块;`PICK_INVEST_EFFECTS` 删欢愉契约行;provisional 通道随枚举迁移;容器字段注释(`cw_game_state.py` overflow 两字段双写端)与 `kernel/cw_projection_audit.py` 对账 basis 行同步。策略屏支不动。
**设计依据**:design.md §2.5、§2.6
**文件面**:`src/sr_od/application/currency_war/kernel/cw_action_report/pick_invest.py`;`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_invest_env.py`;`src/sr_od/application/currency_war/kernel/cw_game_state.py`(仅 overflow 两字段注释);`src/sr_od/application/currency_war/kernel/cw_projection_audit.py`(仅 active_env/溢出 basis 行);测试 `sr-od-test/test/sr_od/application/currency_war/` 下 `test_cw_yinlang_phase32.py`/`test_cw_obs_arch_phase_screens.py`/`test_cw_unified_action_4.py`(按需)
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 行为对照 design.md §2.5(portal 支走链;strategy 支与发射相零变化;画面 op 尾段零容器写)
- §2.6 五条行为变化申报逐条有测试锁或留证(写时点迁移锁必具名)
- 通用工程门(项目测试规范 §10)
**验收凭据形式**:`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关文件全绿;`active_env 写时点` 断言名对照

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本
**设计依据**:本文件「正本更新清单」节
**文件面**:清单所列正本文档
**依赖**:3.1、3.2
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致
**验收凭据形式**:文档对照 review

## 正本更新清单

- `game_state/` 新篇 gain-chain.md(链式规范正本:原语/时序/随机态/失败安全/已知缺口标记)← 3.1/3.2
- `game_state/fields.md` §3.4.3(active_env 写端迁链;ADR-0598 写时点语义退役)← 3.2
- `game_state/fields.md` §3.2.20(溢出字段双写端声明:观察 + 获得链逻辑写端)← 3.2
- `game_state/fields.md` §5.1(效果账本写入挂点清单补获得链登记腿)← 3.2
- `game_state/effect-domain.md`(portal 效果登记挂点记述:画面 op → 获得链;**原无正本记述,本批首立**)← 3.2
- `game_state/action-logic-state.md` 事件单选族节(选择落地经获得链的表述改写)← 3.2
- `screens/op-layer.md` §2.2(动作事实边界条款:投资环境域收窄,裁定①)← 3.2
- `screens/invest_env.md` §2/§4/§6/§8(决策动作 node 零容器写;落地相链语义)← 3.2
- `flow/action_exec.md`、`flow/action_ops.md`(pick_invest 行形状)← 3.2
- 代码注释 ADR-0598 引用面清理(`cw_screen_invest_env.py` 等,grep 全仓定面)← 3.2
