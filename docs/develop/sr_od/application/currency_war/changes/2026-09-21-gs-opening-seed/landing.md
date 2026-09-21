# 容器开局种子底座与锚定闩 落地

## 3.1 种子底座 + 锚定闩 + carry 收窄(kernel)

**范围**:`kernel/cw_game_state.py` 新增 `seed_opening_state(gs)`(A 类字段逐一种子,
design §2.2 A 表为准;mode='compute'、journal 过滤键 `actor='GsOpeningSeed'`)并在
`game_state_of` **两个缓存单例建支**冷建后接线(`session=None` 一次性支**不种**);
新增非 Field 簿记位 `prep_anchored` 与读口 `prep_anchored_of(session)`(直构容器视同
未锚定;测试置闩专口 = 直赋,design §2.4);`kernel/cw_reconcile.py` 在
`tracked_account_observed=True` 写回成功点同点置闩;**carry 守卫收窄**(现值来源
logic_rand 不沿用,design §2.5 末条)。附:A 类字段定义注释补「开局种子底座」语义
一句;§2.5 census 穷举清单与实码核对(grep 全量 logic_action 写端,发现清单外即回修
设计)。**不含**:获得链改动(3.2)、读口 None 分支删除(不删,注释标注)。
**设计依据**:design.md §2.2(A/B/C 分诊表)/§2.3/§2.4/§2.5
**文件面**:`src/sr_od/application/currency_war/kernel/cw_game_state.py`、
`src/sr_od/application/currency_war/kernel/cw_reconcile.py`、
`sr-od-test/test/sr_od/application/currency_war/test_cw_game_state*.py`
**依赖**:invest-landing-chain 主落地已入库(`0358aa60a`,字段名以 HEAD 为准)
**优先级建议**:5
**完成判据**:
- 行为对照 design §2.3/§2.4/§2.5:冷建容器含全部 A 类种子(值/produced_by/evidence/
  mode 断言);B/C 类字段仍 None;`prep_anchored` 缺省 False;reconcile 写回成功点
  置闩;`game_state_of(None)` 支与直构容器不种;carry 对 logic_rand 来源不沿用、
  非 rand 来源存量行为不变;
- 观察覆盖种子不进失配三分流,差异落 `logic_rand_outcome` 行(design §2.7);
- census 核对清单随批提交(清单外写端 = 回修设计,禁自行拍板);
- 通用工程门:照 `sr-od-test/README.md`「提交」节(ruff + 受影响测试 + 相关全量)。
**验收凭据形式**:测试名(`test_cw_game_state*` 种子/闩/carry 新用例)+ census 清单。

## 3.2 获得链通道规则接线 + 缺陷 kind 退役

**范围**:`kernel/cw_gain_chain.py` 新增 `_select_write(gs, rand)` 单一收口
(未锚定 → 随机态,design §2.5),**全部写选择点改经收口(落地时 grep 计数为准,
含在飞 invest-landing-chain 批新增原语——见 design §2.8 次序协调)**;删除
`DEFECT_BENCH_UNOBSERVED`/`DEFECT_EQUIPS_UNOBSERVED` 常量与两处发射分支及对应
`detail` 档生产路径(模块头失败安全自述同步);`sr-od-test` 的 `test_cw_gain_chain.py`
未观察用例改写为种子路径断言,**rand 透传双臂用例随改**(直构未闩断言 logic_rand /
置闩断言按形参,置闩 = 测试专口直赋,design §2.4)。接管局同构断言(经 `game_state_of`
缓存单例支)。**不含**:其他消费点(pick_supply/装备后果桥)迁移(队列①另批)。
**设计依据**:design.md §2.5/§2.6-1/2/3/§2.7/§2.8
**文件面**:`src/sr_od/application/currency_war/kernel/cw_gain_chain.py`、
`sr-od-test/test/sr_od/application/currency_war/test_cw_gain_chain.py`
**依赖**:3.1(与在飞 invest-landing-chain 批的文件次序在进度账本定序)
**优先级建议**:5
**完成判据**:
- 行为对照 design §2.5/§2.6:未锚定期链写全走随机态且首观察零三分流行;锚定后失配网
  原样生效;两缺陷 kind 全仓零发射(grep 断言);grep 写选择计数 = 收口计数(清单随批);
- 通用工程门:照 `sr-od-test/README.md`「提交」节(ruff + 受影响测试 + 相关全量)。
**验收凭据形式**:测试名(`test_cw_gain_chain` 改写用例)+ 收口计数清单。

## 3.2b 效果账本桥锚定前写道收口(人力重组路径)

**范围**:择道 helper 归位 `cw_game_state.py` 公开(命名实现者定,语义 = 未锚定 →
write_logic_rand;`cw_gain_chain._select_write` 改为同源委托,行为零变化);
`cw_effect_inventory.py::apply_board_rewrite` 的 SELL_ALL 容器清空写经锚定闩择道
(未锚定 → rand,design §2.5 census 效果账本桥行裁定 + §2.6-9)。**不含**:UPGRADE_ALL
(零写)、其余桥写端(锚定后可达,天然合规)、`cw_effect_inventory` 内部两选择点
(census 登记不收口)。
**设计依据**:design.md §2.5(census 效果账本桥行)/§2.6-9
**文件面**:`src/sr_od/application/currency_war/kernel/cw_game_state.py`、
`src/sr_od/application/currency_war/kernel/cw_effect_inventory.py`、
`src/sr_od/application/currency_war/kernel/cw_gain_chain.py`(委托改写)、
`sr-od-test/test/sr_od/application/currency_war/` 相关测试
**依赖**:3.1、3.2
**优先级建议**:5
**完成判据**:
- 行为对照 design §2.5/§2.6-9:未锚定(种子容器)选人力重组 → 清空写 source=logic_rand、
  首观察零三分流行;置闩后 → logic、失配网生效;其余 STRATEGY_EFFECTS 与桥写端回归臂
  行为不变;
- 通用工程门:照 `sr-od-test/README.md`「提交」节(ruff + 受影响测试 + 相关全量)。
**验收凭据形式**:测试名(人力重组双臂 + 回归臂)。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:3.1、3.2。
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- `game_state/fields.md`:§2(两态制)+ 新增「开局种子底座」小节(含 rand 通道语义
  例外立据:种子/未锚定期链写供直接消费,锚定后恢复「消费前重观察」纪律,design §2.6-8) ← 3.1
- `game_state/fields.md`:§2.2 失读处置①(carry)守卫收窄语义(随机态来源不沿用) ← 3.1
- `game_state/fields.md`:§3.1.6 相关行(hp 开局三写端时序:种子→先验→真读) ← 3.1
- `game_state/fields.md`:§3.2.x A 类字段行(阵容/经济/溢出/环境/刷新计数组)种子语义 ← 3.1
- `game_state/gain-chain.md`:§2.1/§2.3(通道规则提及)、§6(失败安全:未观察条目改写为种子+闩语义;缺陷 kind 词表退役) ← 3.2
- `game_state/README.md`:两态制总述提及种子底座与锚定闩 ← 末阶段
- `architecture.md`:GameState 行(种子底座/锚定闩一句话) ← 末阶段
