# 克制表直写（详设）

## 问题与约束

- 本主题边界：选卡三选一的克制减分机器（`pick_common.counter_pick_penalty` 及其三件套数据源）；不涉词缀效果本体（affix_effects 域）、不涉词缀吃怕的线分面（affix_line_score 另一通道，不动）。
- 总纲契约 A：受克判定消费 `core_faction_reqs`（faction-priority 详设的档 0 读口）。
- 现状证据（2026-11-04 核实）：
  - 三张表 = 词缀映射表 `AFFIX_MECHANIC_MAP`（词缀→机制标签，27 键）+ 克制表 `MECHANIC_COUNTERS`（标签→打法特征，12 键）+ 改名层 `LINE_FACTION_TO_MECH`（羁绊名→打法特征，3 对：减益/燃血恒等、持续伤害→DoT 改名）。
  - 生产者仅 3 特征（DoT/减益/燃血）；与克制表值域求交非空的仅 2 行（净化→[DoT,减益]、掉血削上限→[燃血]）；其余 10 行克制 + 若干词缀死条目（映射到不存在标签，如紧急止血→爆发机会）恒零行为。
  - `merged_mechanic_tables` 生产消费点唯一 = `counter_pick_penalty`（pick_common.py）。

## 方案

### 1. 新表（唯一数据源，直写；宿主 = `strategies/impl/mandate_v1/pick_common.py`——判定消费近旁；减分常量 `COUNTER_PICK_PENALTY` 本体在 `kernel/cw_line_scales.py`（数值单一源），表侧只引用）

```python
#: 词缀 → 它克制的羁绊名(直写,无中间层;活链路 2 条的如实迁移)
AFFIX_COUNTERS_FACTIONS: dict[str, list[str]] = {
    '净化身心': ['持续伤害', '减益'],   # 克 DOT队/专家桑博DOT/黄泉减益/千冶减益
    '永久创伤': ['燃血'],              # 克 万敌单C
}
```

**拆表声明**：克制数据按消费语义拆**两张独立表**——本表（选卡减分：词缀→羁绊名，命中即减分不分级，与现行 `counter_pick_penalty` 语义逐位一致）与 3.3 的 `TRANSIT_AFFIX_PENALTY`（过渡候选减分：词缀/boss→羁绊名，统一减分制，见 transition-library 详设）。理由：同一词缀对不同羁绊的克制强度在现行登记里本就分档（量子熄火×希儿量子 = 重开级而×圣杯系 = 一般怕档；净化身心×DOT 系 = 重开级而×其余减益线 = 一般档）——单一键承载不了跨羁绊分级；两表数据源与消费点均不同（本表 = 选卡减分活链路迁移，彼表 = 克制登记判读投影），各自单一源、互不演进。

### 2. 判定逻辑（替换 `punished_mechs_of` + `counter_pick_penalty`）

```python
def counter_pick_penalty(opt: str, core_factions: frozenset[str]) -> int:
    """选项名含词缀关键词 ∧ 该词缀克制名单与阵容档 0 羁绊键有交集 → -750。

    core_factions = core_faction_reqs 键集(契约 A;候选首位线/锁定线现读,
    无方向线帧传空集 = 减分不触发,保守缺省同现行)。"""
    for affix, countered in AFFIX_COUNTERS_FACTIONS.items():
        if affix in opt and not core_factions.isdisjoint(countered):
            return COUNTER_PICK_PENALTY
    return 0
```

词缀匹配沿用现行子串包含语义（OCR 容错）。**调用点改写式**（`punished_mechs_of` 删除后两处消费必须照此改，禁照抄旧调用——旧第二参值域是机制属性名 {DoT,减益,燃血}，新第二参是羁绊键集，语义换轴）：

```python
# invest_env.py:337,347 / invest_strategy.py:281,338 现行：
#   punished = punished_mechs_of(anchor) → counter_pick_penalty(_opt, punished)
# 改写为（落地形态：循环外单帧单读键集 + None 防护——内联裸取在零证据帧
# anchor=None 会 AttributeError，与判定自身「保守缺省」要求矛盾）：
core_factions = frozenset(anchor.core_faction_reqs) if anchor else frozenset()
# （循环内）counter_pick_penalty(_opt, core_factions)
```

### 3. 删除清单

- `LINE_FACTION_TO_MECH`、`punished_mechs_of`（pick_common.py）；
- `MECHANIC_COUNTERS`、`AFFIX_MECHANIC_MAP`、`merged_mechanic_tables`（cw_comps.py）；
- `cw_comps.py` 头部「debuff=buff 知识例证」行内注释随表迁出（正卡农据 = final_comps 各篇，git 历史可溯）；
- 对应测试（克制机器三件套的求交/映射断言）随源删除；`RUST_AFFIX_NAME`（库藏生锈，cw_equip_env 消费）不在删除面——它属穿戴语义域非克制域。

### 4. 跨羁绊克制的重立口径（本迭代不做，留声明）

将来「速度抑制克鞋队」类（右侧是打法特征非羁绊名）立项形态 = **阵容画像直接产出受克特征集**（从装备/引擎/输出模式推导的单一源），表值写什么特征名由该源头定；禁复活羁绊名→特征改名层（依据：消费先行先例——无生产者的值域是死重，本迭代删除的 10 行即为先例）。

### 5. 残留口径与恒等判据载体

- 判据域限定：**`src/` 生产代码三张表符号零残留**（含 `src/sr_od/application/currency_war/currency_war_config.py`（currency_war/ 根，非 config/ 子目录）注释 :37 一处随手清理，及 `data/affix_effects_data.py:11`、`obs/cw_briefing_obs.py:54/90/357`、`kernel/cw_affinity_table.py:97` 的注释/字符串残留一并列入本阶段文件面清理）；文档引用（strategy-docs 13/29/16 号稿、docs/game 4 处）**不在本阶段文件面**——归权威版本更新批统一清理（清单已列）；
- 恒等判据载体 = faction-priority 详设 §7 迁移恒等测试的**受克判定输出断言**（活链路 2 条 × 21 线的判定值比对——3.1 中间态已将受克输出纳入快照面，3.2 复用同一断言位）。

## 关键取舍

- **放弃「补全中间层（给 9 个无生产者特征建阵容侧推导）」**：按字段准入先例（消费先行），先有消费者再落数据；现状 10 行零生效的占位即「接入前数据先登记」的违例形态（与「护盾件(类)」死条目、过渡池三常量同类先例），不保留占位。
- **放弃「克制表值域统一到羁绊名以外再抽象一层」**：现役 2 条的右侧天然是羁绊名（净化克的就是 DoT 系/减益系阵容），直写零翻译成本；抽象层的全部历史收益为负（本次删除物即证据）。
