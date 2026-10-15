# 统一保护集(买卖身份同源) 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(CW 快速集:`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面;
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 策略层批:过渡锁定状态槽 + 保护集函数

**范围**:新增 `StrategyState.transition_locked_systems` 状态槽与写点(策略层决策入口前置段,与 `refresh_line_if_needed` 同点,幂等只增;清空点 = 进位面 2 配方对退场同点);新增 `protection_membership` 保护集函数,宿主 = **新模块 `strategies/impl/mandate_v1/protection.py`**(需消费策略层符号:line_members_view/贯穿件;贯穿件常量 `CROSS_LINE_KEEP_NAMES` 自 shop.py 迁入本模块,shop 回导);`knowledge/cw_line_facts._bond_members` 公开化为 `bond_members`(零行为,成员枚举单一源,消除跨层同式复写授权);点亮判定复用现役支持度链(`_p1_system_support`/`_seele_system_support`,**持有域**),**复用面不含 `seele_system_formed`**(板面域,成型停手语义,与持有域选定相反;其现役消费不动),希儿系成员判定单一源 = `is_seele_system_member`。边界:不动任何买/卖消费点(归 3.2/3.3),不动 `committed_authority` 本体。
**设计依据**:design.md §2.1
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate_state.py`(状态槽)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/bridge.py`(写点)、`src/sr_od/application/currency_war/strategies/impl/flow.py`(清空点)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/protection.py`(新建)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`(仅常量迁出)、`src/sr_od/application/currency_war/knowledge/cw_line_facts.py`(bond_members 公开化)、测试仓单帧测试
**依赖**:无
**优先级建议**:0
**完成判据**:
- 单帧:仙舟 3 人在场 → 锁定槽含仙舟;卖退 1 人不掉锁定;量子 3 件无希儿 → 不锁希儿系;**量子件全在 bench 未上阵 → 锁**(持有域分辨用例,拦「误实现成板面域」)(design §2.6 对应各条);
- 现役 `_p1_system_support`/`_seele_system_support`/`seele_system_formed` 消费面零行为变化(只新增不改动);
- 完成前常规检查(本文首节)。
**验收凭据形式**:单帧测试名 + 测试输出

## 3.2 买面批:序 1 名单接线 + 囤货臂 + ④通道退役

**范围**:未锁定序 1 名单并集保护集过渡域成员;义务面/囤货面拆分(**义务面 = 现行口径零变化**;囤货面 = 新增成员期权级:`m2_stockpile` 循环遍历域收窄义务面(含 `_fund_or_none` 筹资腿,囤货面退出义务类买入)、`M2b` 保持宽集、`_dg_gap` 缺口集推导域同步随义务面);**四类目标件排除面比对域收窄义务面**(M6 压牌库/press_buy_deployable/垫件补位支/`ev_buy` 入参——囤货面成员恢复压牌库/凑星通道);**新囤货臂**(位次 = M2b 后、序 2 前;守卫 = 未锁定帧;命中 = 保护集成员 ∧ 未持有首副本;门序 = 1★ 全额退 → 金 → 席/置换;买因 `protection_hoard`;出口键三键,design §2.2);`missing` 推导改义务面;P60 告警对象面收窄义务面;P91/P92 同族申报落地(P91 费用带输入随宽集扩员/P92 拦刷随义务面收窄同步);②(b) prio1/prio2 判定迁移保护集口径(prio0 缺口集 `_dg_gap` 同步;注册表扩员成员优先档位移申报);**C1 候选过滤改直判 `CORE_SINGLE_CARD_REGISTRY`(行为零变化,line_identity_tier 符号随改判摘除)**;④转投分支整条退役;`line_identity_tier` 消费迁移(②(b) prio 与 D7 拒因 @shop.py + hold 登记资格硬闸分档 @sell_gate.py,档位表见 design §2.4;C1 除外)后函数退役,D7 键序调用点 k_members 实参收窄义务面、`transition_char` 键随④删除 + `protection_member_rejected` 新增(非义务面成员被硬闸拒时落);`sell_hold_exclusion_names` 之 hold 登记名字腿迁移(→ 保护集 ∪ registry 核心,归本阶段);两个衍生计数键重定义为保护集口径(写点宿主:`transition_hold_locked_frame` @ shop.py、`deadlock_only_transition_victim` @ mandate.py)。边界:锁定态买面不动;卖面其余消费点不动(归 3.3);现行名单成员待遇零变化。
**设计依据**:design.md §2.2、§2.3(hold 腿行)、§2.4
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate.py`(计数键写点)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/sell_gate.py`(hold 登记腿 + line_identity_tier 消费迁移)、`src/sr_od/application/currency_war/kernel/cw_card_identity.py`(退役面)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/buy.py`(ev_buy 入参)、测试仓
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 单帧:r3 牌面(风堇/藿藿/青雀/佩拉/爻光,帧态六元组 fixture)→ 必发 `BuyCard 爻光`(囤货臂);r6 牌面含饮月 → 必发 `BuyCard 饮月`(design §2.6;帧态从复现局 r3/r6 决策帧提取固化,含方向态);
- ④分支/`transition_release_names`/`line_identity_tier` 代码与消费点零残留(grep 清零申报;sell_gate.py 两点已归本阶段,余点归 3.3 后由 3.3 判据收口);
- 受影响的既有单帧/流程测试逐条判语义后修(引设计出处,禁机械跟绿);
- 完成前常规检查(本文首节)。
**验收凭据形式**:单帧测试名 + grep 清零申报(sell_gate 两点外)+ 受影响测试全绿

## 3.3 卖面批:保护集进资格装配 + 身份面/义务基座拆分

**范围**:`sell_line_membership` 保持现行口径(base/P78-5 减法②/P96 (b) 腿基准,不扩域);保护集经独立消费口并入卖出资格装配 A 身份段(装配单一源 = `sell_gate.identity_exclusions`,`mandate.sell_hold_exclusions` 为薄再出口随迁;替换静态持有两集中的 ④放行集,registry 核心保留);`sell_hold_exclusion_names` 余下四消费面逐点迁移(funding 兜底池判定集 → 保护集 ∪ registry 核心/垫件谓词 → 非保护集/P78-5′ 腿② → 保护集 ∪ registry 核心/会话内筹资腿② → 保护集 ∪ registry 核心,design §2.3 表),函数退役;Z1 排除集同步;升级变现候选池过滤保护集,`_bench_liquid_gold` 攒批资金推导同步剔除保护件(design §2.5-5);新增 `interest_round_protected_block` 观测键(写点 = entry.py 节末凑息段,判定式三合取见 design §2.3,反事实支枚举域 = 凑息候选池同域)。边界:排序键结构不动;八场景参数表结构不动;自救/换血豁免不动;P78 条款本体不动(兜底池构成随身份源迁移)。
**设计依据**:design.md §2.3、§2.4
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell_candidates.py`、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/sell_gate.py`(兜底池判定集)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate.py`(排除集装配)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/entry.py`(凑息观测键写点 + P78-5′ 腿②)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`(筹资腿②)、`src/sr_od/application/currency_war/kernel/cw_card_identity.py`(退役面收口)、测试仓
**依赖**:3.1、3.2(身份消费面 grep 清零的收口判据)
**优先级建议**:5
**完成判据**:
- 单帧:席满 + 手上椒丘 + 店内杂件 → 置换卖杂件,椒丘不在卖出候选;凑息缺口场景全保护档 → 零卖出 + 观测键计数(design §2.6);
- **兜底对账断言**:全场保护档帧(椒丘构造),P78-5 兜底豁免对保护件可放行(两分支必要条件满足时)——兜底池 = 保护集 ∪ registry 核心的直接验证;
- P78 既有豁免通道测试全绿(自救/换血/兜底);
- `sell_hold_exclusion_names`/`line_identity_tier`/`transition_release_names` 全仓 grep 清零(3.2 与本阶段合计);
- 完成前常规检查(本文首节)。
**验收凭据形式**:单帧测试名 + 兜底对账断言 + grep 全清零申报 + 既有 P78 测试全绿

## 3.4 验证批:改后局验证 + 冒烟批 + 观察集读数

**范围**:验证通道 = pytest 冒烟批(SimBackend 库形态)+ `cw_sim_match_drive.py` 单局带遥测落盘(A/B 批跑通道挂起期间的申报替代,design §2.6;用户裁定 2026-10-15:不采改前基线,验证 = 改后行为断言 + 观察集读数)。复现局(seed 20261012 = 病灶局)改后跑,锚定预测行为;冒烟批跑通收统计;观察集读数落交付报告。边界:不改 src 策略代码(缺陷回 3.2/3.3 修复批);测试仓统计面扩展授权(冒烟统计行补点亮率/成型率/killed 聚合字段,或独立聚合脚本读 `-s` 输出,落地批择一并申报)。
**设计依据**:design.md §2.5、§2.6
**文件面**:`.debug/` 下验证产物目录;`sr-od-test/test/sr_od/application/currency_war/sim/test_sim_smoke_batch.py`(统计面扩展,若取此形态);`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_dead_stock_pair.py`(P96 行为线对照,只读);skill 脚本调用(不改动)
**依赖**:3.2、3.3
**优先级建议**:8
**完成判据**:
- 复现局(design §2.6 预测锚;seed 20261012 = 病灶局同一局):爻光/饮月被买入、椒丘不被卖(锚定行为断言);
- 冒烟批全量跑通(逐 seed 收口无崩溃),统计行齐;
- **既有验收线保全清单逐条对照**(design §2.6 表七条:P56+T1 改域申报回填占比/命题 A 八项+目标②组全量/FM-1 补登记/零漂移豁免/P86 验收线/P96 行为线语义判修(载体 = test_dead_stock_pair.py)/M6 子门确认)——读数 vs 门要求逐条判定;
- 观察集读数落交付报告(点亮率/成型率/形态达标率/通关率/存活带/凑息失败频率,绝对值报告无对照)。
**验收凭据形式**:交付报告(读数表 + 保全判定)

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本;含 **TRANSITION_PACK 全仓消费点清点与逐点裁决**(身份消费面已随 3.2/3.3 退役;非身份活消费——`cw_deploy_logic.py` fw_carry/`cw_recipe`/`cw_transition` 等——逐点定迁移或保留,清点清单进交付报告)。
**设计依据**:本文件「正本更新清单」节 + design.md §2.4
**文件面**:清单所列正本文档;`knowledge/cw_line_facts.py` 及清点出的非身份消费文件
**依赖**:3.1-3.4 全部
**优先级建议**:0
**完成判据**:清单清零;清点清单零未裁决项;正本与实现一致
**验收凭据形式**:文档对照 review + 清点清单

## 正本更新清单

- `strategy-docs/01_math_framework.md` §3.2(P41 ② 燃料件判定的重叠域 = 保护集;骨架件条款的实现指认) ← 3.3
- `strategy-docs/11_shop_decisions.md` §1(序 1 名单三态重述:未锁定候选态含过渡域全体 + 囤货臂;④转投分支退役注) ← 3.2
- `strategy-docs/11_shop_decisions.md` §4.0/§4.1/§6.5(§4.0/§4.1:场景资格面身份源 = 保护集;静态持有两集「维持现状」裁决由本迭代推翻的申报;五消费面迁移;凑息观测键登记。§6.5:凑息门改域申报与占比回填) ← 3.3、3.4
- `strategy-docs/12_line_and_intention.md` §1.2/§3/§4(§1.2/§4:过渡域候选/锁定状态语义 + 义务面/囤货面拆分 as-built;§3:TRANSITION_PACK「保留为未锁定期判据输入」引用面的退役收口) ← 3.1、3.2、3.3
- `math_proofs.md` P41 行(判定域修正申报,非新命题)+ P78 行(③④构成迁移随迁注)+ P96 行(行为测试载体指针勘误:`test_cw_dead_pair_exit` → `test_dead_stock_pair.py`)+ `proofs/p86` 单篇(TRANSITION_PACK/line_identity_tier 符号名引用随退役勘误) ← 3.3
- `knowledge/cw_line_facts.py` TRANSITION_PACK 及档位标签**符号删除**(身份消费面清零后;配方对引用面按清点裁决) ← 末阶段
- 观测键登记(`transition_hold_locked_frame`/`deadlock_only_transition_victim` 重定义口径) ← 3.2
