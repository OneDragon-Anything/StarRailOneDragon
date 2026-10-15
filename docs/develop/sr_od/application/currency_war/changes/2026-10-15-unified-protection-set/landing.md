# 统一保护集(买卖身份同源) 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(CW 快速集:`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面;
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.0 基线批:改前对照数据采集(先于一切代码改动)

**范围**:当前 HEAD(改动前代码)采集基线——①seed 20261012 单局对拍基线(`cw_sim_match_drive.py` 跑局,逐轮买卡序列存档);②冒烟批点亮率/成型率/形态达标率/通关率/存活带基线(`test_sim_smoke_batch.py -s` 统计行存档);③凑息观测现状读数(现有日志面,可缺省申报)。边界:**不改任何代码**(纯采集;统计面扩展归 3.4——基线期用现有字段 + 人工读档)。
**设计依据**:design.md §2.6
**文件面**:`.debug/temp/currency_war/sim_review_1/baseline/`(产物目录,不污染既有对照数据)
**依赖**:无
**优先级建议**:0(最先执行——基线数据随代码改动永久失真)
**完成判据**:
- 基线产物两件齐(对拍序列 + 冒烟统计)且落盘路径在交付报告申报;
- 完成前常规检查(本文首节)中「测试同步/提交」两项不适用(纯采集),ruff 不适用(无代码改动)。
**验收凭据形式**:基线产物文件 + 路径申报

## 3.1 策略层批:过渡锁定状态槽 + 保护集函数

**范围**:新增 `StrategyState.transition_locked_systems` 状态槽与写点(策略层决策入口前置段,与 `refresh_line_if_needed` 同点,幂等只增;清空点 = 进位面 2 配方对退场同点);新增 `protection_membership` 保护集函数,宿主 = **新模块 `strategies/impl/mandate_v1/protection.py`**(需消费策略层符号:line_members_view/贯穿件;贯穿件常量 `CROSS_LINE_KEEP_NAMES` 自 shop.py 迁入本模块,shop 回导);点亮判定复用现役支持度链与希儿系单一源(`seele_system_formed`/`is_seele_system_member`),**禁新写第四份希儿系判定**;点亮判定域 = 持有域(bench∪deployed)。边界:不动任何买/卖消费点(归 3.2/3.3),不动 `committed_authority` 本体。
**设计依据**:design.md §2.1
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate_state.py`(状态槽)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/bridge.py`(写点)、`src/sr_od/application/currency_war/strategies/impl/flow.py`(清空点)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/protection.py`(新建)、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/shop.py`(仅常量迁出)、测试仓单帧测试
**依赖**:无
**优先级建议**:0
**完成判据**:
- 单帧:仙舟 3 人在场 → 锁定槽含仙舟;卖退 1 人不掉锁定;量子 3 件无希儿 → 不锁希儿系(design §2.6 对应两条);
- 现役 `_p1_system_support`/`_seele_system_support`/`seele_system_formed` 消费面零行为变化(只新增不改动);
- 完成前常规检查(本文首节)。
**验收凭据形式**:单帧测试名 + 测试输出

## 3.2 买面批:序 1 名单接线 + 囤货臂 + ④通道退役

**范围**:未锁定序 1 名单并集保护集过渡域成员;义务面/囤货面拆分(**义务面 = 现行口径零变化**;囤货面 = 新增成员期权级:`m2_stockpile` 遍历域收窄义务面、`M2b` 保持宽集、`_dg_gap` 缺口集推导域同步随义务面);**四类目标件排除面比对域收窄义务面**(M6 压牌库/press_buy_deployable/垫件补位支/`ev_buy` 入参——囤货面成员恢复压牌库/凑星通道);**新囤货臂**(位次 = M2b 后、序 2 前;守卫 = 未锁定帧;命中 = 保护集成员 ∧ 未持有首副本;门序 = 1★ 全额退 → 金 → 席/置换;买因 `protection_hoard`;出口键三键,design §2.2);`missing` 推导改义务面;P60 告警对象面收窄义务面;②(b) prio1/prio2 判定迁移保护集口径(prio0 缺口集 `_dg_gap` 同步;注册表扩员成员优先档位移申报);**C1 候选过滤不动**(直判 `CORE_SINGLE_CARD_REGISTRY`,零行为变化);④转投分支整条退役;`line_identity_tier` 消费迁移(②(b) prio 与 D7 拒因 @shop.py + hold 登记资格硬闸分档 @sell_gate.py,档位表见 design §2.4;C1 除外)后函数退役,D7 键序 `transition_char` 退役 + `protection_member_rejected` 新增;`sell_hold_exclusion_names` 之 hold 登记名字腿迁移(→ 保护集 ∪ registry 核心,归本阶段);两个衍生计数键重定义为保护集口径(写点宿主:`transition_hold_locked_frame` @ shop.py、`deadlock_only_transition_victim` @ mandate.py)。边界:锁定态买面不动;卖面其余消费点不动(归 3.3);现行名单成员待遇零变化。
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

**范围**:`sell_line_membership` 保持现行口径(base/P78-5 减法②/P96 (b) 腿基准,不扩域);保护集经独立消费口并入卖出资格装配 A 身份段(替换静态持有两集中的 ④放行集,registry 核心保留);`sell_hold_exclusion_names` 余下四消费面逐点迁移(funding 兜底池判定集 → 保护集 ∪ registry 核心/垫件谓词 → 非保护集/P78-5′ 腿② → 保护集/会话内筹资腿② → 保护集,design §2.3 表),函数退役;Z1 排除集同步;新增 `interest_round_protected_block` 观测键(写点 = entry.py 节末凑息段,判定式三合取见 design §2.3)。边界:排序键结构不动;八场景参数表结构不动;自救/换血豁免不动;P78 条款本体不动(兜底池构成随身份源迁移)。
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

## 3.4 验证批:对拍 + 冒烟批对照 + prereg 对照

**范围**:验证通道 = pytest 冒烟批(SimBackend 库形态)+ `cw_sim_match_drive.py` 单局带遥测落盘(A/B 批跑通道挂起期间的申报替代,design §2.6)。改前基线已由 3.0 采集(3.4 消费其产物,不在本阶段重采);改后同口径对照。指标纪律:金类(出口金)/hp 只作报警观察,不作对照判据。边界:不改 src 策略代码(缺陷回 3.2/3.3 修复批);测试仓统计面扩展授权(冒烟统计行补点亮率/成型率/killed 聚合字段,或独立聚合脚本读 `-s` 输出,落地批择一并申报)。
**设计依据**:design.md §2.5、§2.6
**文件面**:`.debug/` 下验证产物目录;`sr-od-test/test/sr_od/application/currency_war/sim/test_sim_smoke_batch.py`(统计面扩展,若取此形态);`sr-od-test/test/sr_od/application/currency_war/strategies/impl/mandate_v1/test_dead_stock_pair.py`(P96 行为线对照,只读);skill 脚本调用(不改动)
**依赖**:3.0、3.2、3.3
**优先级建议**:8
**完成判据**:
- 复现局买卡序列:爻光/饮月被买入(design §2.6 预测锚;seed 20261012 = 病灶局同一局,对拍即病灶翻转验证;基线 = 3.0 产物);
- prereg 对照集(design §2.6,判据先 commit 后跑批):四体系点亮率/引擎成型率/位面 1 形态达标率/通关率不劣于基线;存活报警线(hp 低点带/位面 2 入口率)劣化即停;
- **既有验收线保全清单逐条对照**(design §2.6 表七条:P56+T1 改域申报回填占比/命题 A 八项+目标②组全量/FM-1 补登记/零漂移豁免/P86 验收线/P96 行为线语义判修(载体 = test_dead_stock_pair.py)/M6 子门确认);
- 全部对照数字落交付报告(基线值 + 改后值 + 判定)。
**验收凭据形式**:交付报告(数字对照表)

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
- `strategy-docs/11_shop_decisions.md` §4.0/§4.1(场景资格面身份源 = 保护集;静态持有两集「维持现状」裁决由本迭代推翻的申报;五消费面迁移;凑息观测键登记) ← 3.3
- `strategy-docs/12_line_and_intention.md` §1.2/§3/§4(§1.2/§4:过渡域候选/锁定状态语义 + 义务面/囤货面拆分 as-built;§3:TRANSITION_PACK「保留为未锁定期判据输入」引用面的退役收口) ← 3.1、3.2、3.3
- `math_proofs.md` P41 行(判定域修正申报,非新命题)+ P78 行(③④构成迁移随迁注)+ P96 行(行为测试载体指针勘误:`test_cw_dead_pair_exit` → `test_dead_stock_pair.py`) ← 3.3
- `knowledge/cw_line_facts.py` TRANSITION_PACK 及档位标签**符号删除**(身份消费面清零后;配方对引用面按清点裁决) ← 末阶段
- 观测键登记(`transition_hold_locked_frame`/`deadlock_only_transition_victim` 重定义口径) ← 3.2
