# invest-landing-chain 落地

## 3.1 获得链扩员与文件拆分(kernel;零生产接线)

**范围**:新建 `kernel/cw_gain_effects.py`(骇客采样池 + `_apply_effect_hacker_wolf` 效果体改走链原语 + `PICK_INVEST_EFFECTS`);`kernel/cw_gain_chain.py` 扩员(`gain_invest_strategy` 原语三段式含无效载荷零写留证前置与持卡面按名字去重追加/`on_strategy_gained` 回调/新缺陷 kind `DEFECT_STRATEGY_REGISTER` 与 `pick_invest_invalid_payload`;`gain_invest_env` 保持直写零闸),按详设搬家常量与工作池面。**旧上报面(`cw_action_report/pick_invest.py`)与两屏画面 op 零改动**——本阶段新增代码无生产消费方,存量行为零变化。
**设计依据**:design.md §2.4、§2.8-2/3/4;details/gain-chain-file-split.md 全篇
**文件面**:`src/sr_od/application/currency_war/kernel/cw_gain_chain.py`;`src/sr_od/application/currency_war/kernel/cw_gain_effects.py`(新);测试 `sr-od-test/test/sr_od/application/currency_war/test_cw_gain_chain.py`(扩)
**依赖**:无
**优先级建议**:5
**完成判据**:
- 行为对照 design.md §2.4(三段式时序;注册按名字去重追加;无效载荷零写留证;登记腿 best-effort 与 defect kind;骇客效果体走 `gain_character`/`gain_equipment`,改件后果经 `on_equipment_gained` 回调;标记域前后值快照比对与现行 written 集逐位等价;`gain_invest_env` 保持直写零闸)
- 拆分零行为:效果表键集不变(`{'骇客专家:银狼'}`);采样池成员/种子可复现不变
- 通用工程门(项目测试规范 §10)
**验收凭据形式**:`uv run pytest sr-od-test/test/sr_od/application/currency_war/test_cw_gain_chain.py` 全绿(新原语具名锁:注册去重追加/无效载荷留证/登记腿 session=None 跳过/burst/回调触发),CW 域全量不红

## 3.2 投资两屏切换(词表/上报/动作 op/画面 op/容器;含测试迁移)

**范围**:①`cw_vocab.py` 拆类(Strategy/Env 两 param 类,source 删除,三表同步)+ `cw_action_registry.py` 两行;②上报函数拆文件(`pick_invest.py` 删 → `pick_invest_strategy.py`/`pick_invest_env.py`,分步写法废)+ 机械连带 `pick_planner.py` 的 `EVIDENCE_OVERLAY_CLOSED` import 改就地自持(design §2.5,仅两行);③`CwActionPickInvestOp` 机械链后立即按 param 类型自上报完整结果(session 自 ctx 取);④`cw_strategy.py`/`flow.py` 决策入口返回类型拆分(`_decide_invest` 加 param 类参数);⑤`cw_screen_report/invest_strategy.py`/`invest_env.py` obs 加刷新槽载荷 + report 摄入 `*_left`;⑥两屏画面 op:删 1s 稳定帧/重入裁决确认腿/`_append_confirmed_strategy`/`_log_env_refresh_counts`/fallback(no-ocr) 盲发路径(空候选 round_fail 显式失败),观察一次读全,闸输入改 obs,派发后 `round_success` 终结;⑦`cw_game_state.py` 字段 `*_used` → `*_left`(invest 两屏,注释随批重写);⑧`cw_projection_audit.py` basis 行(active_strategies/`*_left`);⑨周边注释清面(design §2.9 三处)+ 全仓 grep 消费点清零(见完成判据范围);⑩`sr-od-test` 受影响测试迁移 + 新增立即上报/终结交回/持卡面按名字去重/无效载荷留证/left 字段具名锁 + dup 断言改写。
**设计依据**:design.md §2.1(行为面)、§2.2、§2.3、§2.5、§2.6、§2.8 全条、§2.9
**文件面**:`src/sr_od/application/currency_war/kernel/`(vocab/game_state/projection_audit/cw_action_report/cw_screen_report);`src/sr_od/application/currency_war/operations/`(cw_op/cw_overlay_pick_action.py、cw_op/cw_action_registry.py、cw_screen/cw_screen_invest_strategy.py、cw_screen/cw_screen_invest_env.py);`src/sr_od/application/currency_war/strategies/impl/`(cw_strategy.py、flow.py);`src/sr_od/application/currency_war/kernel/cw_action_report/pick_planner.py`(仅 EVIDENCE_OVERLAY_CLOSED 就地自持两行);`src/sr_od/application/currency_war/obs/cw_observe.py`、`obs/cw_observation.py`(仅限 §2.9 核实结论为改动时的最小接线);§2.9 所列注释面;测试 `sr-od-test/test/sr_od/application/currency_war/` 下必改面 = `test_cw_yinlang_phase32.py`/`test_cw_obs_arch_phase_screens.py`/`test_cw_unified_action_4.py`/`test_cw_gain_chain.py`/`test_cw_screen_report_ports.py`(obs 载荷形状锁),其余测试文件按需不受此列
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 行为对照 design.md §2.5(确认点击发出即结果已写入 game state)、§2.6(派发后 `round_success` 终结;无 `_confirm_pending`/重入裁决确认腿/fallback 盲发)、§2.2(观察载荷含刷新槽;1s 稳定帧零残留;决策环零识别)、§2.8 十条申报各有具名测试锁或申报落文档
- 旧符号零残留(范围收窄,对抗审 A1):`CwActionPickInvestParam`/`report_action_pick_invest_param`/`PICK_INVEST_SOURCE_*`/`strategy_refresh_used`/`env_refresh_used` 全仓(src + sr-od-test)零命中;`EVIDENCE_OVERLAY_CLOSED` 清零面 = pick_invest.py 删除 + pick_planner.py 就地自持(pick_equip/pick_supply 就地同名常量及范围外屏消费不属本迭代清零面);docs 正本旧字段名归末阶段清零
- 通用工程门(项目测试规范 §10)
**验收凭据形式**:`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 全绿;grep 清零输出(按上列范围)

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本
**设计依据**:本文件「正本更新清单」节
**文件面**:清单所列正本文档
**依赖**:3.1、3.2
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致
**验收凭据形式**:文档对照 review

## 正本更新清单

- `flow/action_ops.md` §2.3(落地登记注册表段清理:`cw_screen_op_base.py`/`EMIT_TRIGGERED_DECLARED` 全仓零命中死符号,申报面收窄为 encounter)、§4.5(PickInvest 行拆两行 + PickSupply/PickPlanner/PickEquip 行形态更新 + 欠账标注摘除)、§4.6(刷新计数申报面句)← 3.2
- `screens/op-layer.md` §1.1(出口语义:投资两屏确认 = 终结交回;读屏点例外注记)、§1.2(上报 = 点完即写结果,不是只记日志)、§2.2(动作事实边界:投资环境域收窄条款扩为投资两屏)、§3 注(「投资两屏共用 CwActionPickInvestParam 行」句改两行)、§4(刷新计数记账归属改观察 report 摄入 + 策略屏闸口径 ≤0 = 尽)← 3.2
- `flow/action_exec.md` §2(pick 族段:pick_invest 拆两行、立即上报、两相废除)、§2.1(「点击即上报」升格通用并引 action_ops 条款)← 3.2
- `game_state/gain-chain.md` §1(不管清单撤策略原语条)、§2(四原语:新增 gain_invest_strategy 含无效载荷拒绝与持卡面去重追加;env 零闸口径不变)、§3(四枚举回调)、§5(链入口初值补策略)、§7(级联体消费点撤策略屏腿)、§8(接入面双支 + 文件拆分注记)← 3.1/3.2
- `game_state/fields.md` §3.4.3(env_refresh_left 剩余语义 + 观察写端;active_env 写时点 = 动作执行时)、§3.4.4(strategy_refresh_left 同款;active_strategies 同)← 3.2
- `screens/invest_strategy.md` §2/§3/§4/§5/§6/§9(观察一次读全;动作面表:立即上报/终结交回;状态上报面:三桥迁链登记腿;left 字段)← 3.2
- `screens/invest_env.md` §2/§4/§6(同款同步;log 通道升格 obs)← 3.2
- `screens/README.md` §5.5(选卡动作执行载体段:两相例外收窄至策划屏;`_emit_refresh_click` 死锚顺手修)、§6(投资两屏行:确认即终结)← 3.2
- `flow/README.md` §1 图(pick 族上报句)、§2.2(如有 pick_invest 形状引用)← 3.2
- 代码注释清面复核:`_overlay_confirm.py::register_confirm_arrival`(ConfirmStrategy 死键行)/`cw_effect_inventory.py`(板面重写桥挂点注释)/`cw_investments.py`(加油站 burst 挂点注释)/`cw_action_report/zero_writes.py`(pick_invest 迁移史注)← 3.2
