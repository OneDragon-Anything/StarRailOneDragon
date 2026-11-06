# 2026-10-18-levelup-band-gate 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过(只对本阶段修改的文件跑,不对整个 src/);
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 相关子集);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面;
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 升级判据链整体重构

**范围**:升级链生产消费链一次性重构,不留阶段间悬空引用——`criteria/levelup.py` 触发收敛(三分布派)+ 资金门换口径 + 死代码级联清理(`prob_account_ok` 辅助族/`batch_form`/D-lv7 函数);`entry.py` `_levelup_fund_line_ok` 重写(现金口径单门)+ `_step3_level_up` 凑金衔接 + 升级侧兜底拼装删除;`shop.py` 升级意图出口同参核对;`criteria/contracts.py` + `criteria/__init__.py` 契约组与登记行更新(含 pop_slot/batch_form 契约清理);`criteria/predicates.py` 臂判定谓词删除;`audit/provisional.py` 槽登记清理;`kernel/cw_economy.py` 排程层人口位单臂删除;`kernel/cw_investments.py` `refresh_invest_active` 孤儿删除;`kernel/cw_vocab.py` auth_basis 值域注释;`kernel/cw_registry.py` `boss_floor` 字段删除;`mandate_state.py` `cw4_must_spend_phase`/`cw4_pop_slot_why` 字段删除。**受影响存量测试随本阶段改写**(语义演进,docstring 引 design §2.7;已知面:guarantee_floor 直测/ARM_MUST_SPEND/五臂优先序/defer 分键/臂元组/TestFundingHoldFallback/TestLevelupReserveGuard 资金面数字)。边界:不含新单帧 ①-⑩ 固化与预注册验证(阶段 3.2)、不含正本文档(末阶段;新写代码自带注释除外)。
**设计依据**:design.md §2.1-§2.5
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/levelup.py`、`criteria/contracts.py`、`criteria/__init__.py`、`criteria/predicates.py`、`audit/provisional.py`、`strategies/impl/mandate_v1/entry.py`、`strategies/impl/mandate_v1/shop.py`、`strategies/impl/mandate_v1/mandate_state.py`、`kernel/cw_economy.py`、`kernel/cw_investments.py`、`kernel/cw_vocab.py`、`kernel/cw_registry.py`、测试仓受影响测试文件
**依赖**:无
**优先级建议**:0
**完成判据**:
- 触发仅 `stay_gate`/`natural` 两键(与 design §2.1 三分派对应,分派 2 无键);五臂函数、`ARM_*` 常量、`guarantee_floor_gate`/`_levelup_floor_ok` 旧名、§2.3 全部级联项(谓词/辅助族/`refresh_invest_active`/孤儿字段/`batch_form`)在产路径消失;
- 资金门判定式与 design §2.2 逐式一致(下界单一源 saturation_line;无 liquid 预支;凑金域判定式两条件;gold_short = 凑金可达域);
- P21 无域内短路(危机带 ∧ 任意现金位帧均判定);zone_hit/`cw4_must_spend_phase` 判定路径消失;
- 两消费位(备战第 4 步/商店会话升级意图出口)走同一判据单一源无子集化;升级凑金路径无 P78-5 拼装调用、会话内筹资侧兜底保留(grep 可证);
- `boss_floor` 运行时消费点与字段定义清零;
- 受影响存量测试改写后与新增断言全绿;
- 完成前常规检查(本文首节)。
**验收凭据形式**:直接受影响测试子集通过 + grep 证据(旧符号零命中)+ 代码对照 review。

## 3.2 测试固化与预注册验证

**范围**:新单帧测试 ①-⑩(design §2.7 清单,docstring 引 design 节);预注册验证批:`cw_sim_match_drive.py` seed 1000-1019(n=20),按 design §2.8 判据出具读数报告——硬不变量 ①② 必须成立,观察面 ③④(含既有验收线保全清单各线的载体读数)描述性落盘。
**设计依据**:design.md §2.7/§2.8(含保全清单表)
**文件面**:`sr-od-test/test/sr_od/application/currency_war/`(测试仓)、`.debug/temp/`(验证批读数,临时产物)
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 单帧 ①-⑩ 全部存在且通过(行为锁:②板满带内不升/⑧危机带∧现金>线仍拦/⑨攒息期不发射);
- 预注册判据 ①② 成立(花后破线发射帧 = 0;发射帧现金 ≥ 线),读数报告落盘(含保全清单各线载体读数);
- 读数定案后新基线回写正本(11 号稿 §5)或 ADR 判据节(预注册批产物无长期载体,回写 = 定案义务);
- 慢速用例(≥2s)登记 `sr-od-test/slow_marks.txt`;
- 完成前常规检查(本文首节)。
**验收凭据形式**:测试名清单 + 预注册读数报告。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本;全量注释扫尾(design §2.6 关键词全集,含 `tools/cw/proofs/w178` 文档性引用注记)。**扫尾输入 = 关键词全集 ∪ T-1 验收偏差 6 申报清单 ∪ T-1 验收 F1(provisional.py `W_POP` 槽撤槽——人口位臂删除的级联漏项,验收 F1 批示归本阶段)**。
**设计依据**:design.md §2.6
**文件面**:清单所列正本文档 + 扫尾命中的代码注释
**依赖**:3.1、3.2
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致;全量测试一次通过。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- `strategy-docs/11_shop_decisions.md`:§2 重写(五臂→单判据/资金线门/排程分量行) ← 阶段 3.1
- `strategy-docs/11_shop_decisions.md`:§1 六序金约束门升级预留引用 ← 阶段 3.1
- `strategy-docs/11_shop_decisions.md`:§3 刷新分工行与富余段适用范围行(升级触发去向改「触发+资金门自然命中」/「出口阶梯」措辞按三层删除修正) ← 阶段 3.1
- `strategy-docs/11_shop_decisions.md`:§4.0 升级凑金行(凑金目标 = 保线缺口闭合,删除行内 P78-5 两条分支兜底豁免描述) ← 阶段 3.1
- `strategy-docs/11_shop_decisions.md`:§4.1 P78-5 升级侧兜底语义 ← 阶段 3.1
- `strategy-docs/20_large_balance_must_spend.md`:篇首 v2.2 摘要与出处行/§2.2/§3.1 出口三层删除+出口一层拦后去向/§3.2 白名单②/§3.5 动作发出点/§4 关系表/§6 键族/§7.1②/§7.2/§7.3/§7.4①与已裁决行/§7.5 停止付血线 ADR 待办关闭 + §7.5 表 195/196 两行失效待办关闭 ← 阶段 3.1
- `strategy-docs/02_mandate_layer.md`:M3 五臂行/拦截层行(保底金门+硬触发例外)/升格骨架行 ← 阶段 3.1
- `strategy-docs/14_p1_consume_arms.md`:§10 位次表 arm0 标注行 + §4.2 arm0 整节 ← 阶段 3.1
- `strategy-docs/17_stall_form_spend_authority.md`:§2.1 出口①行(arm0/arm1 引用、「升级维持现行静默」)与 §3.4 边界表 arm0/arm1 行 ← 阶段 3.1
- `strategy-docs/19_reinforce_channel_and_survival_discount.md`:出口①分工表述 ← 阶段 3.1
- `strategy-docs/12_line_and_intention.md`:升级触发引用行 ← 阶段 3.1
- `strategy-docs/01_math_framework.md`:LEVELUP_MISSING_SET_AGG【拟】清单行及相关引用行 ← 阶段 3.1
- `strategy-docs/22_prep_screen.md`:备战工序第 4 步 ← 阶段 3.1
- `strategy-docs/23_shop_screen.md`:商店会话升级意图出口 ← 阶段 3.1
- `strategy-docs/00_framework.md`:涉及旧口径的引用(如有) ← 阶段 3.1
- `strategy-docs/11_shop_decisions.md`:§5 新基线回写(T-2 预注册批读数定案材料 = `.debug/progress/2026-10-18-levelup-band-gate/reports/T-2-r1.md` §2.3/§2.4;**聚合遥测取数口径 = match_final.after.cw4_counters 单一源**,禁止探针汇总数直书) ← T-3
- `tools/cw/proofs/w178_p13_hold50_expected_account.py`:boss_floor 文档性引用注记 ← 末阶段扫尾
- 代码注释扫尾(design §2.6 关键词全集) ← 末阶段
