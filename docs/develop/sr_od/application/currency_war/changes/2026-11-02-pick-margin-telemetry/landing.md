# 候选分量遥测 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 改动文件全过;受影响测试全量一次通过;测试仓同步;逐文件点名 commit;提交后 `git show --stat` 复核入库面 = 申报面。

## 3.1 全量落地(单阶段小批)

**范围**:design §2.1-2.4 全部——双通道(词表动作类 margin 字段[cw_vocab 两 Param 类,kw_only+action_key_exclude 照 route_tag 先例;flow.py :425/:485 拷入;决策钩子签名改传 result——基类 cw_strategy.py:267+bridge.py:372 覆写+wrapper :133 消费]+部署私有槽[select_deployment 纯函数+可选收集出参 margin_out;entry._step5_deploy 在 deploy_diff 后写槽;帧定界 = bridge.decide_prep_screen 入口清 + payload 读后清;槽声明 mandate_state.py 含定义注释]);三面观测键与边界值表(部署键形含挑战者板签名/无挑战者 null 形态);decision_payload 新增顶层键 pick_margin/deploy_margin;strategy-telemetry.md 键表随批修复漂移(回填 2 行+新增 2 行+:27 主句两类来源+键数统一——泛化面含 decision_payload.py:3/:184 与 bridge.py:373 计数;基类 docstring cw_strategy.py:270-272 主句同批同步)。单帧测试(值序/竞争域次名/excluded 不入/边界值表全形态/定型分层记法与四边界/虚拟 4 调用点不传出参不写槽/入口清与读后清帧定界)。
**边界**:纯观测(评分函数/比较语义/决策结果零变;收集面加变量与字段拷贝如实申报);遭遇面退出(design §0);不做商店逐牌与部署搜索过程。
**设计依据**:design.md 全篇。
**文件面**(预期;落地核):`kernel/cw_vocab.py`;`strategies/impl/flow.py`;`strategies/impl/mandate_v1/bridge.py`;`strategies/impl/cw_strategy.py`(钩子签名+docstring);`strategies/impl/mandate_v1/invest_env.py`;`strategies/impl/mandate_v1/invest_strategy.py`;`strategies/impl/mandate_v1/deploy_search.py`(段 3 收集出参);`strategies/impl/mandate_v1/mandate.py`(select_deployment 出参);`strategies/impl/mandate_v1/entry.py`(_step5_deploy 写槽);`strategies/impl/mandate_v1/mandate_state.py`(槽声明);`strategies/impl/mandate_v1/decision_payload.py`(键+计数);`strategy-docs/strategy-telemetry.md`;测试仓镜像(margin 断言:invest_env 断言落 test_invest_strategy.py 既有形态/test_deploy_search/test_select_deployment/test_entry/test_decision_payload/test_cw_strategy)。
**依赖**:无。
**优先级建议**:0
**完成判据**:design §2.5 全条目;L1 全绿;完成前常规检查。
**验收凭据形式**:测试名 + L1。

## 末阶段:正本更新

**范围**:strategy-telemetry.md 键表与纪律修订已随 3.1 主批落地(键表回填+新增+主句两类来源+键数统一);末阶段仅迭代 README 进度与收口核。
**设计依据**:design.md §2.1/§2.3。
**文件面**:本迭代 README.md;strategy-telemetry.md(若 3.1 有残留)。
**依赖**:3.1。
**优先级建议**:0
**完成判据**:键有单一源登记且三处口径一致(码/键表/正文计数);完成前常规检查。
**验收凭据形式**:文档对照 + 三处口径一致性核。

## 正本更新清单

- `strategy-docs/strategy-telemetry.md`:键表回填 transition_candidates/member_rank + 新增 pick_margin/deploy_margin 行 + :27 主句改两类来源(现读键/产物透传键)+ 键数统一 ← 3.1
- `strategies/impl/cw_strategy.py`:270-272 基类 docstring 主句两类来源(与正本纪律同步,防码级漂移)← 3.1
- `strategies/impl/mandate_v1/decision_payload.py`::3 与 :184 键数计数随批统一;`strategies/impl/mandate_v1/bridge.py`:373 docstring 同 ← 3.1
