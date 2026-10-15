# 统一保护集(买卖身份同源) 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(CW 快速集:`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面;
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 kernel 批:过渡锁定状态槽 + 保护集函数

**范围**:新增 `StrategyState.transition_locked_systems` 状态槽与写点(策略层决策入口前置段,与 `refresh_line_if_needed` 同点,幂等只增;清空点 = 进位面 2 配方对退场同点);新增 `protection_membership` 保护集函数(域分派 + 四体系全体成员现算 + 候选/锁定/贯穿件并集);点亮判定复用现役支持度链与希儿系单一源(`seele_system_formed`/`is_seele_system_member`),**禁新写第四份希儿系判定**。边界:不动任何买/卖消费点(归 3.2/3.3),不动 `committed_authority` 本体,不写新希儿系公式。
**设计依据**:design.md §2.1
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate_state.py`(状态槽)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/bridge.py`(写点,refresh_line_if_needed 同点)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/flow.py`(清空点)、保护集函数宿主(落地批按依赖方向定:kernel `cw_intention.py` 或 `knowledge/cw_engine_facts.py`,申报)、测试仓单帧测试
**依赖**:无
**优先级建议**:0
**完成判据**:
- 单帧:仙舟 3 人在场 → 锁定槽含仙舟;卖退 1 人不掉锁定;量子 3 件无希儿 → 不锁希儿系(design §2.6 对应两条);
- 现役 `_p1_system_support`/`_seele_system_support`/`seele_system_formed` 消费面零行为变化(只新增不改动);
- 完成前常规检查(本文首节)。
**验收凭据形式**:单帧测试名 + 测试输出

## 3.2 买面批:序 1 名单接线 + 囤货臂 + ④通道退役

**范围**:未锁定序 1 名单并集保护集过渡域成员;义务面/囤货面拆分(义务 = 终局线成员 ∪ 贯穿件 ∪ 点亮体系成员,免息级;囤货 = 未点亮体系未持有首副本);**新囤货臂**(位次 = M2b 后、序 2 前;门序 = 未持有首副本 → 1★ 全额退 → 金 → 席/置换;买因 `protection_hoard`;出口键三键,design §2.2);`missing` 推导改义务面;P60 容量告警对象面收窄至义务面;④转投分支整条退役(committed 门/放行集/`transition_component_buy` 买因与出口键);`line_identity_tier` 四处消费迁移(②(b) prio1/C1 过滤/hold 分档/D7 拒因)后函数退役;两个衍生计数键重定义为保护集口径(`transition_hold_locked_frame`/`deadlock_only_transition_victim`)。边界:锁定态买面不动;卖面不动(归 3.3)。
**设计依据**:design.md §2.2、§2.4
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`、`src/sr_od/application/currency_war/kernel/cw_card_identity.py`(退役面)、`src/sr_od/application/currency_war/kernel/cw_intention.py`(计数键重定义)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/sell_gate.py`(买因登记)、测试仓
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 单帧:r3 牌面(风堇/藿藿/青雀/佩拉/爻光,帧态 fixture)→ 必发 `BuyCard 爻光`(囤货臂);r6 牌面含饮月 → 必发 `BuyCard 饮月`(design §2.6;帧态五元组从复现局 r3/r6 决策帧提取固化);
- ④分支/`transition_release_names`/`line_identity_tier` 代码与消费点零残留(grep 清零申报);
- 受影响的既有单帧/流程测试逐条判语义后修(引设计出处,禁机械跟绿);
- 完成前常规检查(本文首节)。
**验收凭据形式**:单帧测试名 + grep 清零申报 + 受影响测试全绿

## 3.3 卖面批:保护集进资格装配 + 身份面/义务基座拆分

**范围**:`sell_line_membership` 保持现行口径(它同时是装配 A 义务基座 base/P78-5 减法②/P96 (b) 腿基准,**不扩域**);保护集经独立消费口并入卖出资格装配 A 身份段(替换静态持有两集中的 ④放行集,registry 核心保留);Z1 凑息排除集同步替换;新增 `interest_round_protected_block` 观测键(写点 = entry.py 节末凑息段)。边界:排序键结构不动;八场景参数表结构不动;自救/换血/P78-5 豁免语义不动;P78 其余段(窗口/通道对价)不动。
**设计依据**:design.md §2.3、§2.4
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell_candidates.py`、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/sell_gate.py`、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate.py`(排除集装配)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/entry.py`(凑息观测键写点)、测试仓
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 单帧:席满 + 手上椒丘 + 店内杂件 → 置换卖杂件,椒丘不在卖出候选;凑息缺口场景全保护档 → 零卖出 + 观测键计数(design §2.6);
- **兜底对账断言**:全场保护档帧,P78-5 兜底池仍含非义务保护件(base 口径未扩,减法②不吞保护件);
- P78 既有豁免通道测试全绿(自救/换血/兜底);
- 完成前常规检查(本文首节)。
**验收凭据形式**:单帧测试名 + 兜底对账断言 + 既有 P78 测试全绿

## 3.4 验证批:对拍 + 冒烟批对照 + prereg 对照

**范围**:验证通道 = pytest 冒烟批(SimBackend 库形态,`test_sim_smoke_batch.py -s` 统计行)+ `cw_sim_match_drive.py` 单局带遥测落盘(skill scripts;A/B 批跑通道挂起期间的申报替代,design §2.6)。改前基线(当前 HEAD:seed 20261012 逐轮买卡序列 + 冒烟批点亮率基线)先跑先记;改后同口径对照。指标纪律:金类(出口金)/hp 只作报警观察,不作对照判据(p86 §5.1 键③)。边界:不改代码(纯验证;缺陷回 3.2/3.3 修复批)。
**设计依据**:design.md §2.5、§2.6
**文件面**:`.debug/` 下验证产物目录;skill 脚本调用(不改动)
**依赖**:3.2、3.3
**优先级建议**:8
**完成判据**:
- 复现局买卡序列:爻光/饮月被买入(design §2.6 预测锚);
- prereg 对照集(design §2.6,判据先 commit 后跑批):四体系点亮率/引擎成型率/位面 1 形态达标率/通关率不劣于基线;存活报警线(hp 低点带/位面 2 入口率)劣化即停;
- 全部对照数字落交付报告(基线值 + 改后值 + 判定)。
**验收凭据形式**:交付报告(数字对照表)

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本
**设计依据**:本文件「正本更新清单」节
**文件面**:清单所列正本文档
**依赖**:3.1-3.4 全部
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致
**验收凭据形式**:文档对照 review

## 正本更新清单

- `strategy-docs/01_math_framework.md` §3.2(P41 ② 燃料件判定的重叠域 = 保护集;骨架件条款的实现指认) ← 3.3
- `strategy-docs/11_shop_decisions.md` §1(序 1 名单三态重述:未锁定候选态含过渡域全体 + 囤货臂;④转投分支退役注) ← 3.2
- `strategy-docs/11_shop_decisions.md` §4.0/§4.1(场景资格面身份源 = 保护集;静态持有两集「维持现状」裁决由本迭代推翻的申报;凑息观测键登记) ← 3.3
- `strategy-docs/12_line_and_intention.md` §1.2/§4(过渡域候选/锁定状态语义;义务面/囤货面拆分 as-built) ← 3.1、3.2
- `math_proofs.md` P41 行(判定域修正申报,非新命题) ← 3.3
- `knowledge/cw_line_facts.py` TRANSITION_PACK 退役注(按 3.2/3.3 grep 实测结论) ← 3.3
- 观测键登记(`transition_hold_locked_frame`/`deadlock_only_transition_victim` 重定义口径) ← 3.2
