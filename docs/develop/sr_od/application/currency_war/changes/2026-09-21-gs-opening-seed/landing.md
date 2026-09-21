# 容器开局种子底座与锚定闩 落地

## 3.1 种子底座 + 锚定闩(kernel)

**范围**:`kernel/cw_game_state.py` 新增 `seed_opening_state(gs)`(A 类字段逐一种子,
design §2.2 A 表为准)并在 `game_state_of` 单例冷建点接线;新增非 Field 簿记位
`prep_anchored` 与读口 `prep_anchored_of(session)`;`kernel/cw_reconcile.py` 在
`tracked_account_observed=True` 写回成功点同点置闩。附:A 类字段定义注释补「开局
种子底座」语义一句;§2.5 前置逻辑写端 grep 全量核查(锚定前可达的 logic_action 写端
清单申报,发现第三处按同规则收口或申报豁免)。**不含**:获得链改动(3.2)、读口
None 分支删除(不删,注释标注)。
**设计依据**:design.md §2.2(A/B/C 分诊表)/§2.3/§2.4/§2.5
**文件面**:`src/sr_od/application/currency_war/kernel/cw_game_state.py`、
`src/sr_od/application/currency_war/kernel/cw_reconcile.py`、
`sr-od-test/test/sr_od/application/currency_war/test_cw_game_state*.py`
**依赖**:无
**优先级建议**:5
**完成判据**:
- 行为对照 design §2.3/§2.4:冷建容器含全部 A 类种子(值/produced_by/evidence/mode
  断言);B/C 类字段仍 None;`prep_anchored` 缺省 False;reconcile 写回成功点置闩;
  直构 `GameState()` 路径不种(草稿容器行为不变);
- 观察覆盖种子不产失配缺陷行(design §2.7);
- 前置写端核查清单落 design §2.5 追记(或独立核查记录,随批提交);
- 通用工程门:改文件 `ruff check` 通过;`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 全绿。
**验收凭据形式**:测试名(`test_cw_game_state*` 种子/闩新用例)+ 核查清单。

## 3.2 获得链通道规则接线 + 缺陷 kind 退役

**范围**:`kernel/cw_gain_chain.py` 新增 `_select_write(gs, rand)` 单一收口
(未锚定 → 随机态,design §2.5),四处写选择(:294/:354/:430/:480 附近)全部改经
收口;删除 `DEFECT_BENCH_UNOBSERVED`/`DEFECT_EQUIPS_UNOBSERVED` 常量与两处发射分支
及对应 `detail` 档生产路径(bench/equips 在 A 类域不再 None;模块头失败安全自述同步);
`sr-od-test` 的 `test_cw_gain_chain.py` 未观察用例改写为种子路径断言(未锚定 → 链写
source=logic_rand + 观察覆盖静默 + GainOutcome 正常;锚定后 rand=False 走 logic、
模拟失配可产缺陷行)。接管局同构断言(经 `game_state_of` 兜底路径)。**不含**:
其他消费点(pick_supply/装备后果桥)迁移(队列①另批)。
**设计依据**:design.md §2.5/§2.6-1/2/3/§2.7
**文件面**:`src/sr_od/application/currency_war/kernel/cw_gain_chain.py`、
`sr-od-test/test/sr_od/application/currency_war/test_cw_gain_chain.py`
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 行为对照 design §2.5/§2.6:未锚定期链写全走随机态且首观察零失配行;锚定后失配网
  原样生效;两缺陷 kind 全仓零发射(grep 断言);
- 通用工程门:同 3.1。
**验收凭据形式**:测试名(`test_cw_gain_chain` 改写用例)。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:3.1、3.2。
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- `game_state/fields.md`:§2(两态制)+ 新增「开局种子底座」小节 ← 3.1
- `game_state/fields.md`:§3.2.x A 类字段行(阵容/经济/溢出/环境/刷新计数组)种子语义 ← 3.1
- `game_state/gain-chain.md`:§2.1/§2.3(通道规则提及)、§6(失败安全:未观察条目改写为种子+闩语义;缺陷 kind 词表退役) ← 3.2
- `game_state/README.md`:两态制总述提及种子底座与锚定闩 ← 末阶段
- `architecture.md`:GameState 行(种子底座/锚定闩一句话) ← 末阶段
