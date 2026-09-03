# SCHEMA_3KEYS_REPORT —— telemetry schema 三键批(判前锁 v6 行 7/11/13 解除)

> 批目标:三键(f7_contingency_armed / depsilon_advisor_violation /
> f7_exempt_emission)进 `src/sr_od/application/currency_war/telemetry/schema.py`
> 判读面,A/B 重跑前最后一项 v6 阻塞解除。规格单一源 = IMPL_DESIGN §5.1
> 行 7/11/13 原文 + design_telemetry.md 对应键节。

## 落法(逐键,对齐 §5.1 原文哪一句)

三键均按设计原文落**判读面**(键名常量 + 语义 docstring),非记录端写键:
v6 三行判据均为 text 行「telemetry schema 含该键」(ab_core_swap.py
`_v6_row_specs` 行 7/11/13 的 `ok` lambda 直查 schema.py 文本);行为面/
计数端载体(decision 层计数器、audit/provisional.py 槽位)属并行批敏感面
(cw4/),本批禁碰、未碰。

1. **f7_contingency_armed(行 7)**:对齐原文「f7_contingency_armed 置位/
   复位事件进判前锁记录格式(门红事件 id+归因批 id+时间戳)」。落法 =
   `F7_CONTINGENCY_ARMED` 键名常量 + `F7_CONTINGENCY_ARMED_EVENT_FIELDS`
   记录格式字段单一源(gate_red_event_id / attribution_batch_id / ts;
   复位事件={结案结论,(a)-(d) 处置分支},按键节口径异于置位三件)。
   行为面载体声明留在 docstring(provisional.py 槽位、判读批只产建议事件、
   sim/实机同槽不分叉)。
2. **depsilon_advisor_violation(行 11)**:对齐原文「键>0 ⇔ 门/检测两路
   实现漂移」(R56-2 定谳漂移哨兵)。落法 = `DEPSILON_ADVISOR_VIOLATION`
   键名常量,docstring 含现行计数对象(R59-1 收窄=非豁免族顾问动作发射
   ∧瞬时检测域)、阈=0 即红、退出三面合取红判据腿、signal-only 分键
   禁合并。
3. **f7_exempt_emission(行 13)**:对齐原文「观察键(F7 豁免发射计量,
   R59-1)——计数对象=真濒死帧[R40-1 三支完备式,含其与 D_ε 交]上 F7
   越过 D_ε 门的动作发射,分键含真濒死∧D_ε 子态;观察级不进门(禁复用
   三键)」。落法 = `F7_EXEMPT_EMISSION` 键名常量,docstring 含计数对象、
   三不复用面、⑱(e) 行为锚(豁免发射帧 depsilon_advisor_violation 不计
   而本键 +1)。

另加 `F7_DEPSILON_OBS_KEYS` 三键域元组(v6 text 锚对象单一源,防手写名单
漂移),循 schema.py 既有形态(RHO_SYSTEM_KEYS 同款:常量+中文 docstring
+持久出处)。

## 验证数字(亲跑)

- ruff:`uv run ruff check src/sr_od/application/currency_war/telemetry/schema.py`
  → All checks passed。
- v6 检查单(亲跑 `ab_core_swap.v6_checklist()`):行 7/11/13 状态全部
  **已落地**(修改前均未落地——schema.py grep 三键零命中)。
- 测试:`test_cw_schema_f7_depsilon_keys.py`(本批新增最小锁,4 例)+
  `test_cw_v6_cleanup.py` + `test_cw_zero_refresh_fix.py` → **40 passed**
  (5.27s);telemetry 回归 `test_cw_telemetry.py` +
  `test_cw_telemetry_archive.py` → **88 passed**(6.82s)。

## 文件面与边界

- 改动:`src/sr_od/application/currency_war/telemetry/schema.py`(新增
  「F7 / D_ε 判读面观察键」段,插在 ρ 观测段与序列化段之间)+
  `sr-od-test/test/sr_od/app/currency_war/test_cw_schema_f7_depsilon_keys.py`
  (新增)+ 本报告。
- 增量约束遵守:动工前 `git diff` 确认该文件在飞改动 = ev_arm 接线
  (另一批),本批只在现态之上追加,零回退。
- 未碰:cw4/、sim/、kernel/、decision_v2/、recorder.py(三键无需记录端)、
  冻结族/契约、git。
