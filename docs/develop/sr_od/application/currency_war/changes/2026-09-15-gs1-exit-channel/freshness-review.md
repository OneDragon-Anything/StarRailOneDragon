# 2026-09-15-gs1-exit-channel 设计新鲜度复查报告

复查日期:2026-09-20 基底。方法:通读 design.md(199 行)/landing.md(65 行)全部事实主张,逐条对码(grep + 读码 + git log),只读代码,未实施任何改动。

## 总判定

**修订后可实施**(一句话):**任务前提「落地 0/4 未实施」已失真——阶段 3.2 已于 2026-09-15 由 T-253 落码(commit `0a563186a`,含持久获取账/释放集单点/四通道旁路/方向④两键/行为锁测试),设计符号面与现行代码高度贴合(30+ 符号全存活,仅 1 处路径漂移);剩余阶段 3.1(P96 证明单篇)/3.3(A/B 确认)/末阶段(正本更新)未做,但 landing 原文把它们排在"3.2 之前/之后"的语义已被推翻,须按"补做"修订后执行,照原文直接实施会对已落地的 3.2 重复开发。**

## 逐条失真清单(9 条)

| # | 位置 | 主张 | 现状(证据) | 建议修订 |
|---|---|---|---|---|
| 1 | 任务前提/landing 全文 | 落地 0/4,3.2 待实施 | **3.2 已落地**:commit `0a563186a`(2026-09-15)"T-253: G-S1 死库存退出通道落码——持久获取账+释放集单点函数+四通道 G-S1 条件旁路+方向④纯计数两键";`sell_gate.py:618-815`(ACQUISITION_LEDGER_ATTR/dead_pair_exit_release)、`mandate.py:399/494`、`criteria/sell.py:139/266/372`、`shop.py:986`、`entry.py:581-1369`、测试 `sr-od-test/test/sr_od/app/currency_war/test_cw_dead_pair_exit.py`(446+ 行,行为锁①-⑤全覆盖) | 3.2 节改标"已落地(T-253,commit 0a563186a)",文件面加注"勿重复实施";完成判据改"对照已落码核验" |
| 2 | design §2.2.1 | `cw_line_facts.py:66` 缇宝 `('量子','partial')` | 文件已迁 `knowledge/cw_line_facts.py`,值在 **:64**;档位值本身不变 | 路径改 `knowledge/cw_line_facts.py:64` |
| 3 | design §2.1.5 | 判据签名 `dead_pair_exit_release(session, base, bench, deployed, current_round)`,base 由调用方传 | 现役签名 `(session, k_members, bench, deployed, current_round, *, cap_hold=None, counters=None)`(`sell_gate.py:688-694`),**base 改为函数内 `_resolve_base` 自解析**,且新增 `cap_hold` 形参(T-307/R1 ADR-0647 截断集口径,晚于本设计;`:703-706` N3 钉死同帧同参) | 判据规格签名行改为现役签名;(b) 基准语义不变(仍 = `_resolve_base` 输出) |
| 4 | design §2.1.5 遥测表 | kept 子键 = `kept_k`/`kept_age`/`kept_identity`/`kept_chain` 四分 | 现役 = `_k`/`_no_entry`/`_young`/`_identity`/`_chain` 五分(`sell_gate.py:640-644`,N2 把 kept_age 拆为 no_entry[账覆盖缺口] 与 young[真窗内]) | 遥测表更新为五子键;landing 3.3 锚点②「kept_age 为主保留因」相应改读 `_young`+`_no_entry` |
| 5 | design §2.1.5 | C1 =「同帧同名去重」 | 现役 = **名×轮去重**(相位簿 `cw4_dead_pair_exit_frame`,同轮商店/备战两域同名算同一事件;`sell_gate.py:728-731`) | 去重口径表述改为名×轮 |
| 6 | design §2.1.5 获取账规格 | 写端全因类无条件写,未提星级辖 | 现役 `register_acquisition` **星级辖 1★**(star≠1 拒登记,N1 规格,防 2★/3★ 覆盖刷新 1★ 对轮戳致晚释放;`sell_gate.py:670-683`) | 规格补一句星级辖 1★ |
| 7 | design §2.1.5 遥测 | `dead_pair_exit_sold` 按通道分键(未列通道名) | 现役通道闭集 = `m4_fuel`/`interest`/`funding`/`line_switch`(`shop.py:130`、`mandate.py:1244-1245`) | 键表补通道枚举 |
| 8 | landing 3.1 | P96 候编号,单篇先行 | **P96 不存在**:proofs/ 目录无 p96 文件,`math_proofs.md` 索引止于 P95(:100-105);但已落地代码注释多处引用「数学论证 = proofs P96」(`sell_gate.py:620/630/695` 等)——**引用先于被引物存在,数学先行硬门被倒置** | 3.1 仍需执行(补立 P96 单篇 + 索引行),或若裁定不立则清理代码内 P96 引用;优先补立 |
| 9 | landing 3.2 依赖 | T-243(买侧防线 shop.py 消费位接线)为在飞前置 | 已解决:shop.py 两处消费位在役(`shop.py:1614`、`:1936` 直调 `dead_stock_pair_buy_reject_reason`) | 依赖行改"已兑付" |

其余全部事实主张核对**不失真**(抽样列举):`merge_material_reject_reason`(`cw_merge_simulate.py:456`,判据「计数−1≥1 拒」同文)、`same_star_count`(:428)、`dead_stock_pair_buy_reject_reason`(`mandate.py:670`,C=1 分支同文)、`fuel_sell_candidates`(`mandate.py:393`,merge_guard_release 缺省空集零漂移)、`SEED_WINDOW_ROUNDS=2`/`SEED_ACQUISITIONS_ATTR`/`register_seed_acquisition`(`sell_gate.py:480-538`)、`CORE_SINGLE_CARD_REGISTRY`(`cw_comps.py:447`)、`transition_release_names`/`sell_hold_exclusion_names`(`cw_card_identity.py:43/57`)、发射登记簿四出口(`register_launch`/`_expire_and_read`/`prune_on_deploy`/`consume_on_merge`,`sell_gate.py:197-430`)、`swap_sell_exclusion_reason`(`cw_deploy_logic.py:916`,部署侧同键)、`count_merge_material_blocked`(`cw_merge_simulate.py:505`)、`empty_board_sell_blocked`(`sell_gate.py:1050`)、`bench_effect_qualified`(`statefn/predicates.py:362`)、`dominance_buy_eligible`(`mandate.py:613`)、`merge_buy_k`(`cw_merge_simulate.py:525`)、`m2_merge_completion` 通道(`shop.py:122/:1575`)、`pair_target_comp`(`cw_intention.py:1125`)、方向④两遥测键(`shop.py:1118-1119`、`mandate.py:1603`)。landing 3.2 文件面 4 个路径全部现存有效(benchchar-retirement 改了 bench 容器形状,`fuel_sell_candidates` 已适配 `list[BenchSlot]`,与 landing 文件面无冲突)。

## 逐阶段判定表

| 阶段 | 判定 | 说明 |
|---|---|---|
| 3.1 命题单篇 P96 | **需修订后补做** | 单篇与索引行均不存在(失真#8);代码已引 P96,补做即闭合引用悬空;范围/完成判据原文仍可用,取号 P96 空闲可直接用 |
| 3.2 落码 | **已被 T-253 实施完毕(失真#1)** | 不是"被取代"而是"已执行",且与设计判据实质一致(三合取/旁路序/零漂移端/行为锁①-⑤全在);存在 5 处规格级偏差(失真#3-#7),属实现期细化(N1/N2/N3 登记),建议回写 design 判据规格段使其 as-built 对齐 |
| 3.3 sim A/B 确认 | **可照原样实施(小修)** | 未做(.debug/temp/currency_war 无 T-253 对拍产物);前置已全部兑付(#9);仅需把锚点②的 kept_age 改读 kept_young/kept_no_entry(#4) |
| 末阶段 正本更新 | **可照原样实施** | 未做:strategy-docs/11_shop_decisions.md 与 02_mandate_layer.md 均零提及 dead_pair/获取账/方向④维持现状裁决(grep 无命中);正本更新清单 4 条原文有效 |

## 实现者试读结论

凭原文 landing **不能直接开工**:照 3.2 原文实施 = 对已落地代码重复开发(最高危误读);3.1/3.3/末阶段按原文可开工,但 3.3 需先修锚点键名。按本报告修订清单改 landing 后,剩余三阶段均可无歧义开工。

## 附:修订清单(汇总)

1. landing 3.2 标"已落地(T-253/commit 0a563186a)",完成判据改为对照核验;
2. landing 3.3 锚点②:`kept_age` → `kept_young` + `kept_no_entry`;
3. design §2.2.1 路径 `cw_line_facts.py:66` → `knowledge/cw_line_facts.py:64`;
4. design §2.1.5 判据签名改现役形态(k_members + cap_hold,base 内解析);
5. design §2.1.5 遥测表 kept 子键改五分、sold 补通道闭集、C1 口径改名×轮去重;
6. design §2.1.5 获取账规格补「星级辖 1★」;
7. 优先补做 3.1(P96)以闭合代码内既有引用。
