# 双层候选-锁定 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/ -m "not slow"` 相关子集;各阶段 L1 预期红集口径见阶段小节);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 过渡层:体系对候选机器

**范围**:`kernel/cw_intention.py` 配方对链候选化(update_p1_recipe:候选集每轮重算/p1_pair = 门控候选首位〔≥1.0 才写〕/对级声明序/**冻结域 = 双体系对全扫描·单体系对不冻结**/form_ok 冻结收敛/超窗解冻恢复);对级支持度 min 聚合与对级声明序派生;`mandate_state.py` 新槽 `transition_candidates`(索引定义注释);`strategies/impl/flow.py`(**路径:strategies/impl/ 下**)物化链改(无门控候选首位/冻结对/p1_early_pair fallback 取代)与进 P2 清空段核对;k_empty_window_fallback p1_lock_band 支同源切换;`session_scope.py` 重算接线;committed_authority 族/locked_buy_scope 族消费面核(行为无变化声明含回落帧)。单帧测试:候选重算/p1_pair 门控与回落帧行为/平手/解冻/进 P2 清空/有羁绊开局非空/committed 含回落帧等价/单体系对板面凑齐不冻结。
**边界**:只吃真实持有;不含终局层证据门与资格臂(3.2)、不含成员档双层装配(3.3);不动 P2 桥;不动 deploy_search(部署骨架全枚举现行);不动 bridge.py(两入口仅保持 transition_locked_systems 刷新,候选不经 bridge——写端单一 = 配方链)。
**设计依据**:design.md §2.3/§2.5/§2.6-4/5/6/§2.7。
**文件面**:`src/sr_od/application/currency_war/kernel/cw_intention.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate_state.py`;`src/sr_od/application/currency_war/strategies/impl/flow.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/session_scope.py`;测试仓 `kernel/test_intention.py`(:90-165 五测与 :298-326 域,必红改写)、`kernel/test_economy.py`(:686-693 pair_drought 域,必红改写)、新建 `test_cw_transition_candidates.py`。
**依赖**:无。
**优先级建议**:0
**完成判据**:
- design §2.3 全条目断言(p1_pair 门控候选首位/committed 含回落帧等价/冻结域 = 双体系对全扫描/单体系对不冻结/渐进第二席由候选并集承载);§2.7 不变式自检(判据族零改动);
- CW L1 预期红集 ⊆ design §2.8 必红清单(test_intention :90-165 五测与 :298-326 域/test_economy pair_drought 域/test_line_select :328-380 物化链与清空守卫域/test_mandate :41-52 opening_recipe 买面域/test_decision_payload :161-172 k_empty 直调域),清单外变红 = 停手;
- 完成前常规检查(本文首节)。
**验收凭据形式**:测试名 + L1 红集登记。

## 3.2 终局层:证据门与货架信号装载

**范围**:`line_select.py` compute_candidates 证据门参数(缺省关闭;候选快照消费开启版)+ 虚拟评估入口参数化 + evaluate_lock 空候选兜底分支;`shop.py` 货架单张资格买入臂(CARRY/骨架级 ∧ 虚拟 top3 资格 → 序 1 义务扩展臂 missing 后子序;reason = shelf_qualify_buy)+ 冷启动臂(双空窗引擎件 1 费见即买,会话内现算即停,reason = cold_start_buy)+ 买面名单源替换(实候选证据门版 ∪ 过渡候选);`sell_gate.py` 两 reason 入 LAUNCH_CAUSE_BY_ARM 闭集(A4 硬闸)。单帧测试:证据门(零证据线不入/持有点亮/环境命中/时点兜底空候选锁热度首线)、资格判据(CARRY 触发/插件不触发/虚拟 top3 资格/义务类 reason/子序)、冷启动臂(双空窗触发/会话内现算即停/序位)、货架消失退化、买入转实链路、开局空买面。
**边界**:虚拟评估零持久化;部署骨架现算保持缺省全量版(与快照分立,design §2.2-6);不触碰保护面/卖出资格/刷新/投资两屏;不含观测载荷(3.4)。
**设计依据**:design.md §2.2/§2.3-8/§2.5-1/§2.6-1/3/§2.7。
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/line_select.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/sell_gate.py`;测试仓 `test_line_select.py`(或并入新建,必红:证据门)、`test_shop_session_loop.py`/`test_acquire_yield.py`(必红改写)。
**依赖**:3.1(买面名单源的过渡候选部分)。
**优先级建议**:0
**完成判据**:
- design §2.2 全条目断言(资格判据/子序/退化/P77 对齐的可测行为——虚拟评估不写任何跨帧状态);
- CW L1 预期红集口径同 3.1;
- 完成前常规检查(本文首节)。
**验收凭据形式**:测试名 + L1 红集登记。

## 3.3 统一优先级:成员档双层装配

**范围**:`priority.py` 成员档双层名单(实候选证据门版 ∪ 过渡候选)与 `member_rank` 二元组化(含缺省 `(1, CANDIDATE_TOP_N)` 与补缺 :285-286);`sell_candidates.py` 过渡候选支(替换单配方支,凑息豁免名单同源)。单帧测试:双层名单/同档垫底/缺省值/重叠归终局/过渡完成品档 4/豁免域含过渡在建件。
**边界**:十档结构与键域 1..10 零改动;档 1/6/8/9/10 不分层;deploy_search 不动(部署骨架全枚举现行);完成品保护批断言全绿。
**设计依据**:design.md §2.4/§2.6-7/§2.7。
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/priority.py`;`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell_candidates.py`;测试仓 `test_priority.py`(必红改写)、`test_sell_candidates.py`(必红改写)。
**依赖**:3.1 与 3.2(终局半边名单 = 实候选证据门版,由 3.2 的 line_select 改动产生)。
**优先级建议**:1
**完成判据**:
- design §2.4 全条目断言;重叠归终元零特判核(rank 二元组字典序承载);完成品保护批既有断言全绿;
- CW L1 全绿(3.1/3.2 红集清零);
- 完成前常规检查(本文首节)。
**验收凭据形式**:测试名 + L1 全绿记录。

## 3.4 观测与注释面

**范围**:`decision_payload.py` 过渡候选与二元组 rank 导出;`telemetry/schema.py` 资格/冷启动 reason 分键注释;全仓口径注释 grep 跟改(单席/单一配方/**p1_early_pair/early_pair/单体系渐进/_progressive_second_seat 表述族**〔含 deploy_search.py:620-622 注释与 contracts.py:249 契约描述〕清零,语义排除新表合法命中)。
**边界**:不动运行逻辑;键生成零改动。
**设计依据**:design.md §2.6-7/§2.8。
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/decision_payload.py`;`src/sr_od/application/currency_war/telemetry/schema.py`;grep 确认的注释消费位(含 `test_no_target_three_arms.py`/`test_supply.py`/`supply/test_decide.py`/`test_prep_pipeline.py` 的 rank/档号表述跟改)。
**依赖**:3.3。
**优先级建议**:2
**完成判据**:
- 在役注释/测试表述面旧口径清零(「单席」「单一配方」类;语义排除);
- 完成前常规检查(本文首节;ruff)。
**验收凭据形式**:grep 清零记录 + ruff。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列文档。
**依赖**:3.1-3.4 全部。
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- `strategy-docs/12_line_and_intention.md`:§1.1 评分不设项「商店货架项」改写(货架信号装载位 = 单张买入估值,P77 对齐,方向评分仍零货架)+ **候选入选证据门条款**(§1.1/§1.2:零证据线不入候选,热度降为有证据线间排序);§1.2 候选管理补双层结构;§2 方向状态载体补 transition_candidates 槽与 opening_recipe_comp 行语义改写(候选首位物化);§3 配方对链候选制改写(单席易手/渐进通道 → 候选/上岗);§4 未锁定买面接线 K 名单源改写 ← 3.1/3.2
- `strategy-docs/11_shop_decisions.md`:买面名单源(实候选证据门版 ∪ 过渡候选 + 货架资格臂)、m2 纪律不变声明、资格 reason 义务类 ← 3.2
- `strategy-docs/32_unified_sell_priority.md`:成员档双层名单与 member_rank 二元组(含缺省)← 3.3
- `strategy-docs/24_deploy_segment.md`::30 附近「单体系渐进形态」语义锚与 deploy_search :620-622 注释死符号引用(_progressive_second_seat)改写(部署枚举形态不变,语义锚换源);**§1.4 k_members「候选 ∪ 配方 ∪ 锁定线并集」行的「配方」口径跟改**(单对物化 → 过渡候选并集)← 3.1
- `proofs/math_proofs.md` P-T166 行:四层谓词族退役改写(状态列「意向层核心已实现」→ 谓词族随双层候选批退役;实现面符号清单更新;验收载体死引用清理——test_cw_pair_predicate_layers.py 已不存在,现役载体 = test_intention :90-165)← 3.1
- `strategy-docs/01_math_framework.md`:**§3.7 四层谓词段改写**(宪法级判据行:配方对方向判据 = 四层谓词 → 候选排序键纯函数((支持度,声明序))口径;P-T166 权威指针随行改指退役登记)← 3.1
- `docs/game/currency_war/research/transition_combos.md`:补「四体系组合空间 = 策略过渡候选域」指引段(机制正文不动)← 3.1
- `strategy-docs/README.md`:12/32 号稿摘要若需反映双层/证据门结构则同步 ← 正本阶段
