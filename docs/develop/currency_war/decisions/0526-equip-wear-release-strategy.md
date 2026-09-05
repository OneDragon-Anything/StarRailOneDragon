# ADR-0526: 装备穿戴策略语义落码——hold 触发权归策略侧 + 释放判据表 + 词缀条件优先层

## 背景

18 号稿(`docs/develop/currency_war/strategy-docs/18_equip_wear_semantics.md`,对抗两轮零阻断)
收编三件策略语义残余:①根11——执行层自持 hold 时机判断(`cw_op_equip_all._transition_hold_active`
等三函数),零上身哨兵 stop_reason 无辖域归域;②流程36——opening/committed 扣留的释放判据
散在执行层调用点,缺输出侧罚则词缀豁免行;③流程45——「软弱无力」局分配无「满 3 件优先
carry」约束(复盘 195720 F:7 件装备辅助 3 件 carry 1 件),词缀效果只有散文注册表、
无结构化谓词载体。

## 决策

按 18 号稿落码,四件:

1. **hold 触发权归策略侧**:三判据函数整编迁移至
   `kernel/cw_equip_env.resolve_wear_release`(释放判据表五行单一源),产出
   `WearReleaseDecision`(四行分量 + `hold` 布尔释放位)。执行层 `CwOpEquipAll`
   只消费 `hold`,禁在本层加第二套时机判断(与 ADR-0461 裁定 3 同理由)。
2. **释放判据表接线**(§2.1):row1 opening hold(H3 收窄)/ row2 committed hold
   (committed_from 权威 ∧ 0<form<COMMIT_FRAC;未定型帧不激活)/ row3 战斗节点释放
   (row1 否定支,不独立出字段)/ row4 生锈豁免(辖一切扣留)/ row5 输出侧罚则词缀
   豁免(只辖 committed 域——罚则结算时点不对称)。合并规则:扣留任一命中、豁免取
   并集;`hold = (opening ∧ ¬rust) ∨ (committed ∧ ¬rust ∧ ¬penalty)`。
3. **零上身哨兵辖域二分**(§1.2):`classify_zero_wear_stop_reason` 把 stop_reason
   归入四域(strategy_by_design / strategy_gap / execution / execution_pending
   兜底行),归域随 `equip_zero_wear` 遥测行落 `domain` 字段。
4. **词缀条件优先层**(§3):新结构化载体 `data/affix_wear_semantics_data.py`
   (与散文注册表互不触碰;prose_ref 名锚 + 值对拍锁 + 互检显警检测面;
   邻接排除族显式点名),`resolve_affix_priority_order` 求序(限输出侧罚则族;
   谓词涉及集合=在场角色全集;[9] 基序内重排不造第二套评分),经
   `equip_allocation` 新可选参数 `priority_order` 传入(缺省 None 零漂移;
   comp=None 强制 None;只在释放帧启用,扣留帧保持 carry 先拿零漂移)。

**脱落预防声明**(§1.2-3):分配器为 fill-only——occupied 仅作容量扣减,不触碰
任何已穿件(key 与否同判);重排只改「穿给谁」的次序,不可能取下已穿 key 件。
锁:`test_fill_only_never_removes_worn`。

## Considered Options

- **判据落点**:a) 留执行层(现状态,判据变更要动 op 文件,违反分层);
  b) 整编迁移 kernel 单一入口(选定)——迁移不改语义逐位(锁
  `test_zero_drift_without_affix_rows` 逐位对拍旧门真值表);
  c) 只加豁免行不动旧函数(判据两处散,第二个消费点必漂移)。
- **词缀载体**:a) 只挂账(病灶裸奔);b) 解析散文文本(OCR/措辞漂移脆弱);
  c) 结构化载体 + 名锚 + 对拍锁(选定,骑既有静态数据采集通路,D-81 守卫
  同族);d) 混入散文文件(被采集批整文件重写冲掉,禁)。
- **接口形态**:a) `equip_allocation` 内嵌词缀评分(执行层评分,禁);
  b) 新可选参数 `priority_order` 显式传入(选定,缺省零漂移);
  c) 复用 `apply_equip_env_variants` 序变体位(旧清退管道复活,语义混)。
- **row5 开关**:不加新 registry 开关、行为无条件化——行为输入已就绪
  (结构化载体+对拍锁在案),悬置默认关违反开关生命周期门
  (默认关 = 缺口继续裸奔);row4/H3 先例同为行为无条件化。

## 后果

- 正:释放判据单一源,哨兵归域可判读,「软弱无力」局凑满 carry 的分配语义落地;
  缺省路径(无词缀/扣留帧/comp=None)全部零漂移,有锁。
- 负/权衡:`output_penalty_release` 无开关(回退 = git revert);词缀层凑满语义
  的收益证明仍是待证假设(18 号稿 §3.5,P61 挂账,期限 = 本 ADR 收口起一个
  对局周期,超期未证 = 证完落码或退役换保守缺省)。
- 单帧锁:`test_cw_equip_wear_semantics_18.py`(判据表/二分/求序/分配器/对拍
  五组)+ `test_cw_r388_opening_hold.py`(矩阵改锁新入口)。
- 三同步:18 号稿 §6 as-built 回记;本 ADR;代码注释引 ADR-0526。
