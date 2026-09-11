# ADR-0645: T-290+T-291 回放器两小件——意向 latch 回读恢复面 + 判读卫生(fake 过滤/拼接警示)

- 状态:已实施(工作树;入库走 committer,本 commit 即本批随统一门补档;落地审=reviews/T-290-落地审.md accept 零阻断)
- 关联:ADR-0231(回放对拍器升级先例)、ADR-0598(回读面语义升级走 ADR 先例)、ADR-0571(披露面纪律,本批范围裁决依据)、`telemetry/knowledge/cw_serialize.py`(serialize_intention 单一源,本批为其反向)、`flow.py`(`_refresh_direction_views` 派生式正本)、`kernel/cw_intention.py`(IntentionState/LineTrack/pair_target_comp/p1_early_pair)
- 立项正本:`.debug/temp/currency_war/T-286-交付报告.md` §3(回放器语义缺口消歧说明)+ §3.3(两条立项建议)+ `reviews/T-286-落地审.md`(accept 含勘误)

## 背景

回放器(cw_replay.py)重放历史档案行时只恢复 session 的部分状态,`v3_intention`(战略意向 latch)从不回读——实跑中意向由方向刷新逐步置位,回放侧缺恢复面,导致锁定/聚焦帧的分支级决策(买什么卡/买不买)与实跑结构性不可比:T-286 基线全档案 16 分歧行、单局 `run_20260911_043101` 5 分歧行,其中 p2r1 锁线追买臂不点火、p1r9 灾难帧误报。LIMITS 文案当时写「旧记录(decision_v2 前)无 v3_* 态」——消歧正本(T-286 §3)证实实况是「**有态不读**」:档案行携 v3_intention 全量序列化(serialize_intention 产物),缺的只是回读代码。

判读卫生面两处缺口:测试注入的 `fake_` 前缀 run 行(schema 可能异常、动作非真实局产物)混入 best 基准与跨局拼接体(基线中 p2r3 OpenBox 假局污染行即此);无 `--run` 时静默回放「全档案跨 run 拼接体」,判读者易误读为单局决策序列。

## 决策

1. **意向反序列化恢复面**(`_intention_from_trace`):trace 行 `v3_intention` dict → IntentionState,是 serialize_intention 的反向——容器形状还原(list→tuple/set、tracks 子 dict→LineTrack、锁时机计数 int 化),其余标量直灌。宽容读法:缺字段走 dataclass 缺省、当前类不认识的键忽略、LineTrack 子键同式过滤——档案跨 schema 版本不炸(实测旧 schema 行 18 键缺 3 冻结键可读)。
2. **target 派生视图补拍**(`_materialize_target_comp`):实跑中 `flow._refresh_direction_views` 在 prep 入口把意向物化为 `state_of(session).target_comp`,回放不跑方向刷新故补同一拍产物——派生式与彼处逐字同构(get_comp(locked_comp) 优先;P1 无 comp 锁按 p1_pair 空窗取 p1_early_pair 物化配方伪 comp)且复用同一派生源函数,禁第二实现。P1 面辖域判定需快照 plane,故 `main()` 调用序调整:`sess.shop_state_frame = st` 先于 `_restore_session`(黑板先就位;调用序契约入测试锁)。
3. **None 行残源回退**:v3_intention=None 的行(旧记录/无意向帧)不写意向、维持默认态演化;以行携顶层 `target_comp` 标签(locked_comp 直名或「过渡配方·A+B」形态,即 `_target_comp_label` 产物)作残源解析,解析失败(旧命名/注册表缺项)= None 诚实缺省。
4. **范围裁决——两处不回读**:①预算 latch(v3_release_budget/reason)不回读——遥测披露面字段,禁任何决策判据消费(单一源=assembly._disclose_budget 注释+ADR-0571+守卫锁 test_cw_budget_disclosure),决策消费的预算=TurnState 幂等投影逐帧现算;p1r9 转一致亦实证回读意向即可对齐。②focus_factions 不回读——生产写端为零(全仓仅声明+一处透传读),无态可回。
5. **fake_ 前缀恒过滤**:main() best 选取与 run 计数前过滤 `fake_` 行(fake=测试注入数据,不属真实回放语料);显式 `--run` 优先级高于过滤(id 等值判断在过滤之后,指向真实 run 照常)。
6. **两处拼接警示**(纯提示面零决策行为):无 `--run` → 打「回放对象 = N 个 run 的跨局拼接体…已过滤 fake_ 测试行 M 行;单局判读请加 --run」;`--run` 过滤/查档后零行 → 打「无真实回放行(id 不存在,或为 fake_ 测试数据已被过滤)」。
7. **LIMITS 文案勘误**:「旧记录无 v3 态」→「v3_intention dict 在案的行回读恢复,仅 None 行从默认态演化」;低置信「兜底毒值」→「state 存的是当时读数而非兜底毒值(历史档案逐行核伪),⚠ 只降该行判读置信,不改决策输入」(T-286 毒值假设证伪口径)。

## Considered Options

(前两条从 T-286 §3.3 立项建议直接承接,均采纳)

- **恢复面补意向字段小批(T-286 §3.3 条 1)**:采纳,即本 ADR 决策 1-4、7——做完后锁定后帧的回放才具备回归判读力。
- **回放判读卫生小件(T-286 §3.3 条 2)**:采纳,即本 ADR 决策 5-6——fake 过滤+拼接警示均纯提示面,零决策行为。
- **预算 latch 回读**:否决——见决策 4①;禁披露面消费是 ADR-0571 在册纪律,且单局实证回读意向即可对齐(p1r9 灾难帧转一致),无预算 latch 需求。
- **focus_factions 映射回读(T-286 立项候选)**:否决——见决策 4②;无生产写端则无态可回,回读面无意义。
- **fake 行仅警示不过滤**:否决——fake 行 schema 可能异常且动作非真实局产物,留入 best 基准即污染跨局拼接与单局判读基线(基线 p2r3 污染行实证);测试注入数据本就不属回放语料。

## 后果

- 回放对结构性不可比缺陷改善实证(落地审两口径亲跑复现):单局 5→2 分歧行(p1r9 灾难帧、p1r7 聚焦件误买转一致);全档案 16→4(p2r1 锁线追买臂点火,p2r3 假局污染行消失)。锁定/聚焦帧分支级决策可比成立。
- 残余分歧两类如实申报(非本批缺口):p1r4 多一笔 LvUp=升级检查依赖 exec_state/xp 经验账等 session 面尚未回读(T-286 LIMITS 预告域的相邻缺口,是否立项候编排者裁量);笔级多买/换买残差按 docstring「分歧 ≠ 变好变差,从首发点判读」口径消费。
- fake 行(基线档案 251 行)只过滤不物理清理,仍在案;若需物理清理另行走数据卫生批。
- 回放警示头/过滤行为有测试锁承载(test_cw_replay_session_restore.py 6 用例),防回归。

## 验证

- 新锁 6(test_cw_replay_session_restore.py):反序列化形状(tuple/set/LineTrack/未知键忽略)/锁定行回读+target 物化/P1 配方物化(连带锁「黑板先于回读」调用序契约)/None 行标签残源回退+缺标签诚实缺省/fake 过滤+拼接警示头/--run 指向 fake 的空行警示;入库时亲跑 6 passed(2.67s)。
- 落地审独立复现(reviews/T-290-落地审.md):反序列化反向性 21 字段亲核、派生式与 flow 同源同构亲核、范围裁决两边界亲证、两口径效果亲跑复现、L1 快速集全量 3338 passed/1 skipped、ruff 通过、档案 hash 复核无陈旧基线。
- 入库时冒烟:单局 `--run run_20260911_043101 --diff` 亲跑回放器可用(5→2 分歧行与交付报告一致)。
