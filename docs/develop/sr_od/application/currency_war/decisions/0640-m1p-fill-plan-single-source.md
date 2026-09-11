# ADR-0640: T-279 M1″ 卖出后补部署消费计划单一源——装配单一源契约延伸至部署补上段

## 状态

已实施(工作树;入库走 committer 不自带 commit;落地审由编排者另派)

## 背景

C-A2 强信号缺口 2/263(局 18 P2r4 黄泉@same_row + 局 58 P2r5 佩拉@next_row,verdict=repair_face;T-190 批 C 遗留①,T-271 结算立卡):M1″ 换血链的**计划面**(`select_swap_plan`,target 视图 = `all_factions`/锁线转型域收窄键集)与**执行面**(轮末补部署——sim `engine_p1.py` 手搓 `_tf = comp.factions` 字面;生产 `cw_op_deploy.py` deterministic fill 消费 `deploy_target_sets` = comp.factions ∪ FRAMEWORK_FACTIONS)用两套 target 视图。义务买入件(带已达成弹性键)被计划判进 up 桶、被执行面判进 rest 桶,单空槽补部署被改判给另一件,义务金买入件整局滞留且零处置记录——违 P51 B6/01 §3.8「等待件部署 d=0」既证口径。机制在两局名字级逐位复现(T-279_probe2/3.py 对照重放,方案对抗审独立复核)。

装配单一源契约(ADR-0530/ADR-0534)明文辖**卖出臂两侧**;部署补上段是其漏管消费位。本 ADR 把契约**延伸**至部署补上段,写成新裁决条文(不引旧条文充当明文依据)。

## 决策

1. **R1-a 直投(首选快路径)**:m1p 卖出成功帧,卖出后板面 ≡ 计划假想板面(同一 victim、同帧无漂移),计划已对该假想态算好 up 集——直接部署 `plan.up_bench` 名单,无需重选。sim = `_m1p_plan_fill_deploy`;生产 = mandate 发射位透传计划载荷(`cw4_m1p_plan_pending`:`sell`/`up` 名单 + `trans_domain` 域事实 + `occ` 计划时点占用数),`_deploy_deterministic` 消费。直投前提 = **名字级单通道三点式**(对抗审 F2 钉定;禁跨通道 board 字典全等——ADR-0590 决策1 OCR 欠计先例会打穿校验):①victim 身份 = 卖出臂实际卖出名序 == 计划卖序(单 victim;多卖帧/卖出失败帧显式定义走 R1-b);②up 成员仍在 bench(SIFT/占用名集);③占用数与计划假想一致(计划时点占用 −1)∧ 容量可容。
2. **R1-b 重 derive(生产主路径/防御态)**:装配单一源 `assemble_swap_plan_inputs` 对**卖出后现读状态**重 derive,替换手搓第二份(sim `_tf/_tc/_fw/_lf`;生产 `deploy_target_sets` 独立装配),再走各自既有补部署机器。**域辖域钉定**:`transition_domain` 参数把计划时点转型域事实(`SwapPlanContext.transition_domain` 装配快照)传入重 derive——域谓词含 board_full 腿,卖出后帧 board_full 翻假,现算必丢收窄辖域,而收窄辖域是计划时点事实不可从卖出后状态重推(局 18 实证:收窄键集 up=[黄泉]=计划 pick、all_factions up=[丹恒·腾荒];不钉定则防御路径复现缺口)。钉定仍经装配函数单一传导收窄,消费位零内联第二份。
3. **分工二选一裁决(对抗审 F1)**:**维持现分工**(裁决支 b)——卖谁仍由执行侧卖出臂现读仲裁(ADR-0590 后果⑤在册分工:发射=存在性,执行=逐件),计划载荷仅作部署段核对与快路径准入、**不改卖出仲裁权**;生产事实主路径 = R1-b 重 derive,R1-a 仅 victim 同名快路径。携 sell_names 收拢 victim 仲裁(支 a)被否决(见 Considered)。
4. **辖域(对抗审 F4)**:R1 钉 m1_swap_redeploy 轮(sim+生产)。非 m1p 显式动作轮(CompTransaction 等)维持现状围栏 fill 原目标集——同款双源暴露面在彼处无 C-A2 分母、无本案证据,通用化收口归后续卡(证据义务 = R2 up_names 落地后扫显式动作轮义务件滞留),该卡同时收口 sim 手搓视图与生产 `deploy_target_sets` 的框架阵营并集分歧(对抗审 F5)。
5. **R2 遥测扩面**:m1p 记录追加 `up_names`(上序名单,名字级;`swap_plan_up_names` 单一换算——`up_bench` 是 ctx.bench 下标非名字,对抗审 F3)。追加键下游零迁移(记录 dict 无 schema 白名单,消费面全 `.get`)。C-A2 消费后义务件处置四态直读(计划含它未执行/计划未含它/已部署/已离席),gap_plan_active 可定谳。sim/生产两处 m1p 记录形状注释(函数 docstring + 账本键表)随批改写。
6. **数学先行**:「执行=计划」等价 = 条件式【推】(对抗审 F3 修正形态):同装配函数 + 同 select 函数 + **前提面成立**(victim 同名卖出、bench 占用序稳定、板面无漂移)⟹ up 集逐位一致;前提破走 R1-b,等价性断言只在前提成立帧作单帧锁,断言对象用名字集。零新数值判据、零新常数——本修复 = 结构契约恢复,行为收益面引既证命题(P51 B6 d=0/P24 支配不裁谁上/P61)不新证。

## Considered Options

- **携 sell_names 收拢 victim 仲裁(F1 支 a)**:否决——改变在册发射⇔执行分工(ADR-0590 后果⑤),卖出臂资格判定/保护域/让渡序全链随之重对账,行为面远超本案缺口;契约变更收益(直投命中率)未经量化,先以「核对不仲裁」形态兑现,分工收拢候生产遥测证据后另裁。
- **跨通道 board 字典全等作直投校验**:否决(F2)——计划假想板面 = 注册表派生,执行侧读数 = SIFT/OCR 链,跨通道全等在 OCR 欠计帧恒失败 → R1-a 死代码化;名字级单通道三点式两边同域。
- **R1-b 通用化一次收口(非 m1p 显式动作轮同批切换)**:否决(F4)——通用切换把未锁域全语料 fill 目标集从窄(comp.factions ∪ 框架)换宽(all_factions ⊃),弹性键件成批翻入 tgt 桶,deploy 围栏该吃「买面视图」还是「成型面视图」无 ADR 裁过;丢框架并集可复现 r70「保血资产买了不上场被卖」病灶。证据先行后续卡另裁。
- **重 derive 不钉域(域谓词现算)**:否决——卖出后 board_full 翻假 → 转型域判假 → all_factions 全量,局 18 形态防御路径仍部署 [丹恒·腾荒] ≠ 计划 [黄泉],缺口在防御路径复现;域事实是计划时点快照,必须经装配参数钉定。
- **plan.up_bench 下标直接跨层透传**:否决(F3)——下标坐标系 = 装配时点 ctx.bench 紧缩占用序,跨帧/跨域引用脆;`swap_plan_up_names` 单点换名后载荷/记录/断言全走名字集。

## 验证

- 新锁(test_cw_swap_plan.py):m1p 记录 `up_names` 记录锁;R1-a 直投等价锁(前提显式断言:victim 名一致 + 占用序稳定;断言对象 = 名字集,`m1p.up_names == 实际补部署名单`);R1-b 防御锁(前提破帧缺口仍被补、走重 derive 路径);mandate 计划载荷透传锁(发射置位四键 + 非 m1p 帧复位)。
- 守卫移除验证:拔 `_m1p_plan_fill_deploy` 的 R1-a 分支(退回旧 `_residual_fill_deploy` 路径)重跑等价锁必红(锁红由直投行为本体承载)。
- 两例重放对照:probe2/probe3(只读)复跑基线不漂移;等价锁帧形态与局 18/局 58 缺口形态同构(锁线转型域 + 板满 + 义务件带达成弹性键)。
- 点名域 `uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"` + ruff 本工文件(结果见交付报告 §四)。
