# 环境条件发放 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/ -m "not slow"` 相关子集);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号与任务 id;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 kernel 条件发放与登记表
**范围**:登记表 ENV_STREAK_GRANTS(三条校验)、GameState 新域 env_grants_done(种子/恢复/schema/审计四件套)、触发检查函数、宝钻获得回调函数(纯 kernel 面,无接线)。边界——不含 live/sim 接线、不含 supply 采纳。
**设计依据**:design.md §2;details/env-conditional-grant.md §1–§4。
**文件面**:`kernel/cw_investments.py`(ENV_STREAK_GRANTS + 校验)、`kernel/cw_game_state.py`(新域四件套)、`kernel/cw_env_grants.py`(新模块:触发检查 + 回调)、`kernel/cw_projection_audit.py`(完备性锁强制新域行)、`sr-od-test/test/sr_od/application/currency_war/test_cw_env_grants.py`(新)、`test_cw_game_state_opening_seed.py`(种子枚举扩员先例)。
**依赖**:无。
**优先级建议**:10
**完成判据**:
- 行为对照 ore-conditional §1–§4(域四件套/登记表三条校验/触发条件矩阵七序短路/随机态发放写行 + done 追加同 sig 相邻/equips 缺读不标 done 下结算重试/回调三写含 back_layout min9 与 None 防御);
- 双源类校验实证:ENV_STREAK_GRANTS 登记不存在的环境名或装备名 import 即炸;
- 快照→恢复后 `env_grants_done` 仍 tuple-of-tuple;恢复局(快照含 done)触发函数不再发;
- 完成前常规检查(本文首节)。
**验收凭据形式**:单测名(条件矩阵/发放写行 evidence/done 追加/回调三写/校验三条/种子恢复)。

## 3.2 live 接线
**范围**:battle_wait 结算覆盖调用点后接触发检查(sig = logic_hook 族 group 'battle-wait:env-grant');streak_after None 不调。边界——不动结算覆盖本体与观察链。
**设计依据**:details/env-conditional-grant.md §5(live 部分)。
**文件面**:`operations/cw_screen/cw_screen_battle_wait.py`、`sr-od-test/` 对应 battle_wait 结算测试文件(实测点名,无既有则新建命名申报)。
**依赖**:3.1。
**优先级建议**:5
**完成判据**:
- 触发检查调用点 = apply_settlement_cover 之后(次序断言真锁——**测试构造约束:fake 结算路径必须真实携带 streak_after 并走真覆盖写端,防 ore 迭代 R5 式假绿**);
- 随机态发放 + equips 观察整表覆盖纠偏测试(猜错自愈);
- streak_after None 的结算不调;
- 完成前常规检查(本文首节)。
**验收凭据形式**:测试名(调用点次序、发放写行、纠偏)+ grep 无旁路。

## 3.3 sim 接线 + supply 采纳
**范围**:结算路径触发检查接线;返回非 None → 宝钻回调;`_on_supply_picked` 裸 diamond_count 写替换为回调(缺口闭合,既有补给测试预期跟改)。
**设计依据**:details/env-conditional-grant.md §5(sim)/§4(回调);design.md §2 第 5 条。
**文件面**:`sim/cw_sim_backend.py`、`sr-od-test/test/sr_od/application/currency_war/test_cw_sim_backend.py`、涉及带钻补给的既有测试(申报)。
**依赖**:3.1。
**优先级建议**:5
**完成判据**:
- 行为对照 ore-conditional §5 sim 部分(触发在 streak observe 后;回调三写 diamond_count/deploy_cap/back_layout;宝钻裁决只认财富宝钻);
- 数值对照:深井角斗场 sim 局 5 连胜达成后 diamond_count +1、deploy_cap = level+1、back_layout +1(min9)、装备在库;同 seed 重放一致;
- supply 采纳后:带钻补给局三域同步(缺口闭合的行为面);
- 完成前常规检查(本文首节)。
**验收凭据形式**:测试名 + sim 局数值对照。

## 末阶段:正本更新
**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:3.1–3.3。
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单
- docs/develop/sr_od/application/currency_war/game_state/fields.md:新域 env_grants_done(条件发放已发标记)← 3.1
- docs/develop/sr_od/application/currency_war/game_state/gain-chain.md:环境发放族新增条件达成发放(ENV_STREAK_GRANTS 结算连胜触发器)← 3.1
- docs/develop/sr_od/application/currency_war/flow/projection_contract.md:状态面板行内联描述补 env_grants_done ← 3.1
- docs/develop/sr_od/application/currency_war/sim/sim-wiring.md:结算路径(连胜触发发放)+ 补给宝钻回调采纳 ← 3.3
- docs/game/currency_war/research/invest_effects.md:§1 批 4「行为条件流」新增深井角斗场条目(结算连胜触发、随机态获得财富宝钻、回调重算上限)← 3.3
