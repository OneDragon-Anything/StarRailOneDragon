# 2026-09-15-gs1-exit-channel 落地

> 阶段小节 = 账本唯一源;立任务照各节 `dag.py add`,criteria 预注册指向本节。
> 设计依据统一指 [design.md](design.md);各节只写节号。

## 3.1 命题单篇与证明登记

**范围**:把 design.md §2.1 的数学重推正式化为 proofs 单篇(候选编号 P96,登记时按 math_proofs 索引实际空闲号取号,防撞号):命题 = 素材对退出判据的帧级支配 + N=3 载体寿命推导;含 V_opt 对偶定价推演(§2.1.1-§2.1.2)、支配论证(§2.1.3)、N 两侧边界唯一性(§2.1.4)、残余风险界(§2.1.7)。**单篇须显式声明时钟起点重基**:窗长沿用种子窗在册值(获取轮 ≤ r ≤ 获取轮+2),起点 = 较晚成员的持久获取账登记轮(非种子簿原义的种子获取轮)——防登记时被指偷换起点。方向④ §2.2 不立单篇(维持现状裁决,零数值结论;裁决记录随末阶段正本更新落 strategy-docs)。边界:不改策略代码、不改索引以外的正本。
**设计依据**:design.md §2.1 全节。
**文件面**:`docs/develop/sr_od/application/currency_war/proofs/p96-*.md`(新)、`proofs/math_proofs.md`(索引行)。
**依赖**:无。
**优先级建议**:7。
**完成判据**:
- 单篇命题/推导/边界与 design.md §2.1 一致,数值引用全部直调在册单一源(p41 二维表/P76 退货表/种子窗在册值),零新自由参数;时钟起点重基声明在篇;
- math_proofs 索引行状态如实(推导级/待对抗审);
- §12 通用工程门(引用,不复述)。
**验收凭据形式**:单篇文档对照 review + 索引行 diff。

## 3.2 释放谓词、持久获取账与通道接线落码

**范围**:①**持久获取账**(design.md §2.0/§2.1.5):session 属性 `{名: (位面, 最新获取轮)}`,写端 = `shop._emit_buy` 全因类无条件写(与种子登记同位先例),位面闭合 + 全场域活性闭合,与发射登记簿四出口解耦;②`fuel_sell_candidates` 增 `merge_guard_release` 形参(缺省空集零漂移)与 G-S1 旁路分支;③sell_gate 新单点函数 `dead_pair_exit_release`(判据 (a)(b)(c) 三合取,(b) 基准 = `_resolve_base` 输出)与四通道消费位接线;④遥测键 `dead_pair_exit_released`/`dead_pair_exit_guard_kept`(子键 kept_k/kept_age/kept_identity/kept_chain)/`dead_pair_exit_sold`(事件口径 C1 去重);⑤行为锁①-⑤(§2.1.5,含 ADR-0558 案发回归形态锁④与获取账生命周期锁⑤);⑥方向④纯计数键 `transition_hold_locked_frame`/`deadlock_only_transition_victim`(零行为,触发谓词按 §2.2.3)。链状态合取按 §2.1.7-2 随批并入(一次注册表读)。边界:不改 G-S1 本体、不改装配 A 各段、不改买侧防线谓词、不碰部署侧同键守卫。
**设计依据**:design.md §2.1.5(判据规格/获取账规格/接线位/遥测)、§2.1.7(边界与 fail-closed 方向)、§2.2.3(方向④遥测谓词)。
**文件面**:`src/sr_od/application/currency_war/strategies/impl/mandate_v1/sell_gate.py`(获取账+释放函数)、`strategies/impl/mandate_v1/shop.py`(获取账写端 + 消费位)、`strategies/impl/mandate_v1/mandate.py`、`strategies/impl/mandate_v1/criteria/sell.py`(三函数同旁路消费)、`sr-od-test/test/sr_od/app/currency_war/test_cw_dead_pair_exit.py`(新,行为锁①-⑤)。
**依赖**:3.1(单篇入册为先,数学先行硬门);**T-243**(账本在飞:买侧防线 shop.py 消费位接线)——本阶段与 T-243 同改 `shop.py`,按 iteration-design §1.1 挂同文件在飞最小前置:接线合入后再开工,或由编排者声明批序合并(同一 worker 承接两件)。
**优先级建议**:8。
**完成判据**:
- 行为对照 design.md §2.1.5:锁①-⑤ 全绿;锁④ = ADR-0558 案发形态(新购对立即触达)仍拒;锁⑤ = 发射登记簿四出口销账后获取账条目仍在;
- 装配 A 与 G-S1 本体 diff 为零(旁路只在 fuel 资格子谓词内;先旁路后装配的序由锁③序列断言钉死);
- 缺省形参零漂移:不传 `merge_guard_release` 时全量行为与改前逐位一致;
- 获取账写端全因类覆盖(A4 硬闸发射位单点);(b) 基准 = `_resolve_base` 输出与装配身份段同源;
- `uv run ruff check` 改动文件零告警;L1 快速集(SKILL.md 测试分层行)全绿;
- 遥测键落点与计数口径单一源(复用 `count_merge_material_blocked` 事件口径模式);
- §12 通用工程门(引用,不复述)。
**验收凭据形式**:测试名(行为锁①-⑤ + 零漂移锁)+ `cw_replay --diff` 漂移首发点核对(分歧帧全部落在释放集语义内)。

## 3.3 sim A/B 确认批

**范围**:同池同 seed 对拍(先跑改前基线批再改后批,池指纹逐位核对);验证载体 = 仍产素材对的种子(**base 退出孤儿对**:配方换型/换线场景,s77013 型换型局为已知高产出载体;**赠得对**低频);A/B 报告(必含 sim 可观测性声明:判据/资格谓词层 + 获取账写端 sim 可见;批辖域位面披露;效应量预期申报 = 买侧防线接线后 press/dominance 新生对断源,有效总体 = 孤儿对+赠得对,预期释放频次显著低于病灶局量级,见 design.md §2.1.6;s77091 轨迹的「素材对可腾/form_ok 兑付」复验**归买侧防线接线任务的死锁形态消除回归**,不作为本方向效应证据——该局在新批中素材对不再形成,无对象)。
**设计依据**:design.md §2.1.6(A/B 角色与有效总体申报)、strategy-work §4(改前基线→改后对照、锚点事前写)。
**文件面**:`.debug/temp/currency_war/` 下对拍产物与报告;账本凭据指针。
**依赖**:3.2(含其 T-243 前置——锚点语义依赖接线后世界)。
**优先级建议**:6。
**完成判据**:
- prereg 完整性硬门:报告逐条列出受本批影响的在册验收线(出口金/[13]/form_ok 尺/通关门/存活)并证明保全(design.md §2.3 申报面),缺清单 = 对抗审查直接打回;
- 方向一致 = 确认通过;不一致按三选一归因(实现 bug/机制理解错/sim 不可信声明),查不清不上实机;
- 锚点事前写在报告头,全为本方向专属观测量:①`dead_pair_exit_released` 释放频次(孤儿/赠得对载体上 >0);②`dead_pair_exit_guard_kept` 子键分布(kept_age 为主保留因);③素材对滞留轮数差分(`merge_material_stale_ge2` 轮级差分,改后下降);④`merge_material_guard_blocked` 按对在场时长归一的增速下降(该计数事件口径跨帧仍计触达、帧内去重,增速判读须按在场时长归一,禁裸计数对比);⑤`m2_retry_exhausted` 段内增量降;
- 有效总体稀薄帧的判读申报:released≈0 时按「总体稀薄非设计失效」归因(design.md §2.1.6),以行为锁与 kept/sold 键兑现为价值案例。
**验收凭据形式**:A/B 报告(对拍数字 + 锚点核对 + 可观测性声明)。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:3.1-3.3 全部。
**优先级建议**:0。
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/currency_war/proofs/math_proofs.md`:新命题索引行(状态、关键数字、复算对象) ← 3.1(登记),3.3 后回填 A/B 确认注
- `docs/develop/sr_od/application/currency_war/strategy-docs/11_shop_decisions.md`:§卖出资格/仲裁单一源节——素材燃料资格的释放子谓词(条件旁路 G-S1,四通道共享单点;基准 = 义务重买集)+ 获取账登记面语义 + 燃料件分类行补「意图载体死后退出」语义 ← 3.2
- `docs/develop/sr_od/application/currency_war/strategy-docs/02_mandate_layer.md`:§3 M4 行腾席资格描述句补释放子谓词指针(一句,不展开) ← 3.2
- `docs/develop/sr_od/application/currency_war/strategy-docs/11_shop_decisions.md`:§静态持有两集行补方向④维持现状裁决的语义记录(④ 件持有保护的辖域结论 + 条件化后续门触发谓词,写语义与判据、不引 changes/) ← 末阶段
