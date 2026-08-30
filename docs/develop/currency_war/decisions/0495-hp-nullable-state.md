# ADR-0495: GameState.hp None 化(无真值即 None,开局兜底 100 正式废止)

## 状态
accepted (2026-08-30)

## 背景
ADR-0282 建 hp 三层读链时,决策层保留「全无真值(开局)兜底 100」——
`GameState.hp: int = 100` 默认值 + `hp_readable/hp_trusted` 两位保真。
ADR-0491 已证伪「r1 开局恒满血 100」前提并废止 r1 语境的兜底,但兜底
形态本身仍留在对账层(`reconcile_hp` 返回 `(100, False)`)与字段默认值里:

1. **默认值看起来像真值**:`GameState()` 构造即得 `hp=100`,任何漏接
   保真位的新消费点都会把 100 当真值消费——整类「默认值毒化」失效面
   无法从类型上排除;
2. **两位 False + 值 100 的假值帧**仍会在沿读链产生(值与位分离,靠
   消费纪律而非结构保证不毒化);
3. W807 遗留建议:把「诚实未知」下沉到决策态本身(99 处 `.hp` 消费
   改型,单开一批)。

## 决策
`GameState.hp: int | None = None`——**无真值即 None**:

1. **对账层**:`reconcile_hp` 全无真值返回 `(None, False)`(原
   `(100, False)`);读不到但有真值仍沿用 `last_hp_real`(int)。
2. **消费点统一保守适配**(非策略行为面改动,是 None 语义落地):
   血线触发条件(`< 阈值`)None → 不触发;授权/许可条件(`>= 阈值`)
   None → 拒绝;期望存活轮(`rounds_alive`)None → 0;可信位门
   (`hp_decision_trusted`)fail-closed 不变。
3. **遥测直通**:recorder 的 r1 特例臂退役——producer 不再产兜底 100,
   `trace.hp = state.hp` 直通(schema `hp: int | None` 既有)。
4. **sim 账本行口径不动**:sim hp 是模拟真值(帧恒真读,`hp_readable`
   默认 True 的约定仅服务 sim/离线帧),零改动。
5. **默认构造语义**:`GameState()` = 未观测态(hp=None);个别局外
   防御构造点(投资环境/策略 handler)的「满血档」语义改为构造点显式
   声明 `GameState(hp=100, hp_readable=True)`。
6. **历史档案**:r1 兜底 100 帧按局反推真值回填(规则(按局)语义,
   真值源=各局 r1 结算屏),见 `.debug/temp/currency_war/w823_hp_none_cure/`。

## Considered Options
- **A(采纳)hp: int | None 默认 None**:「诚实未知」进类型系统,消费点
  显式处理 None,默认值毒化类失效整体消除;改型一次性覆盖全部消费点。
- B(拒)保留 int 默认 100 + 靠两位过滤:值位分离靠纪律不靠结构,
  漏接位的新消费点继续中毒(ADR-0282 Option A 拒绝理由同样成立)。
- C(拒)None 化但保留对账层 100 兜底:毒化源头仍在,遥测仍需 r1 特例臂,
  半吊子改型。
- D(拒)GameState 加 `hp_known()` 谓词、字段保 int:调用面更绕,
  等价 None 化的语义但不进类型,漏判形态不变。

## 后果
- `hp_readable/hp_trusted` 两位语义不变(真读/结算/沿用标注);决策
  消费口径 `hp_readable or hp_trusted` 零改。
- 血线谓词在无真值帧的方向:触发类不触发(不基于未知做激进动作)、
  许可类拒绝(未知不放行)——与既有 fail-closed 取向一致(ADR-0428)。
- 测试:W823 None 化锁(`test_cw_w823_hp_none.py`)+ ADR-0282 锁④
  改判(兜底 100 → None,依据本 ADR)。
