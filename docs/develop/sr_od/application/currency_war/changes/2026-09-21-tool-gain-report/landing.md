# 工具上报获得链接入 落地

> 阶段小节 = 账本立任务的唯一源。设计依据 = [design.md](design.md)(定稿)。

## 3.1 工具上报落码批(tool_use.py 七上报 + 零写退役 + 申报表收口)

**范围**:①新建 `kernel/cw_action_report/tool_use.py` 七上报函数(语义单一源 =
design.md §2.2 表;记账载体 = `gs.equips` 合并单笔写;冶金炉 rng 关键字带缺省 +
采样池 = `cw_sim_equips.furnace_reroll` 同源 + 披露键 `furnace_mutate_pool_v0_same_category`
+ 变异后果采证行;投影仪走 `gain_character`(producer=`CwActionToolUseReport`,
费用门前置查);特权卡 char 腿/令牌 fail-closed 留证);②`zero_writes.py` 七函数
退役;③`cw_tool_use_action.py` import 切换 + 文案同步;④`cw_affix_effects.py`
EQUIP_WRITE_SIDES 词表扩展第五形 `report:<函数名>`(校验器同步)+ 逐行终值
(design §2.3 表);⑤cw_vocab 七类 docstring、cw_equip_env/cw_effect_inventory/
cw_game_state(consumables 指针)/cw_projection_audit 注释面同步(design §2.6);
⑥测试(design §2.5:逐工具写端锁/采样对拍锁/走链锁/变异不走链锁/fail-closed 锁/
词表校验锁/回归)。
**边界**:不动 gain-chain 3.2(pick_invest 接线);不动并行批在飞面(`vopt.py`/
`cw_screen_battle_wait.py`/`cw_op_settle_confirm.py`);正本文档归末阶段。
**设计依据**:design.md §2.0–§2.5(全分支与失败安全)。
**文件面**:design.md §2.6 所列 src 文件(除正本文档);`sr-od-test/` 对应测试。
**依赖**:gain-chain 3.1(已落地,cw_gain_chain.py 在库)。
**优先级建议**:9
**完成判据**:
- design §2.5 测试面全项绿;zero_writes 七函数归零;`EQUIP_WRITE_SIDES` 校验锁绿;
- L1 全量通过(`$env:PYTHONPATH='src'; uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow and not legacy_baseline" -q`)。
**验收凭据形式**:测试名 + L1。

## 末阶段:正本更新

**范围**:①`flow/action_ops.md` 七工具行(上报 = 容器写形态);②`game_state/fields.md`
§3.2.15(equips 工具写端注)/§3.2.16(consumables 死字段清偿指针);③设计 §2.6
所列注释面复核(随 3.1 已落的免重复)。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:3.1。
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/currency_war/flow/action_ops.md`:七工具行(零写 → 容器写形态)← 3.1
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`:§3.2.15 工具写端注 / §3.2.16 死字段清偿指针 ← 3.1
