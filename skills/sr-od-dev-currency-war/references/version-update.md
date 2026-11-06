# 货币战争版本更新适配清单

> 版本更新的总流程（确认客户端版本 → 清点新内容 → 对齐范围 → 汇总验证 → 分阶段提交）单一源 = `sr-od-version-update-adaptation` skill（其适配项路由表指向本篇）。本篇 = 总流程第 3 步「逐项适配」在货币战争（CW）域的展开清单。读者 = 智能体。

## Checklist（版本更新后 CW 侧必做，没做完不算完成）

1. ☐ **重采游戏数据**——重跑生成器全家，用内建 diff 驱动复核；判据 = 角色/投资/羁绊/装备/实战阵容五个域都有 diff 结论（有变化 → 逐项复核消费点；无变化 → 记「无 diff」），方法与生成器清单见 [data-collection.md](data-collection.md)。**含 carry 对账**：gen_plaza_comps 生成末尾的差异报告（聚类 carry vs 手判各线 core_chars[0]）逐差异线人裁定是否重排 core 序（首位 = 定义件契约，裁定后才动注册表）；「无簇」行（聚类 n<5）不进差异清单。
2. ☐ **重跑阵容知识**——赛季扩充会重划角色定位/羁绊/费用；按 compo-knowledge 的「版本更新重跑」流程执行（知识层各篇标版本重核 → 策略侧消费点按 diff 同步）；方法见 [compo-knowledge.md](compo-knowledge.md)。
3. ☐ **复核万金油角色名单**——见下节「万金油名单复核」，这条最易漏。
4. ☐ **核对版本敏感的策略注册表**——至少含：升级经验门槛表、牌池副本数、商店刷新概率表（三个域在 [data-collection.md](data-collection.md) 均有「版本更新需复核」类标注，逐项到该表核对采集方式）。
5. ☐ **测试回归**——`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`；红测逐条判断是代码过时还是测试过时，别直接改期望值。
6. ☐ **实机冒烟**——能进游戏时跑一轮受影响玩法（改了识别/注册表/策略判据的都算受影响）；与总流程第 4 步合并执行。

## 万金油名单复核（易漏项展开）

- **对象**：策略代码里的「万金油角色恒囤名单」（常量 `CROSS_LINE_KEEP_NAMES`，单一源 = `src/sr_od/application/currency_war/strategies/impl/mandate_v1/protection.py`）。
- **数据依据**：`docs/game/currency_war/research/stage_transitions.md` Q1 表——用官方投稿 API 三阶段阵容统计「前期角色留场到最终阵容的比率」，留场率全场最高、且与路线无关的角色构成「全程留用层」，名单即取自该层。
- **为什么版本更新必须复核**：该表的数据带版本基准（文内声明）；新版本的角色池/羁绊/费用变动会改变留场率排序——上个版本的全程留用角色可能掉层，新角色可能进入。名单不改 = 策略拿着过期结论禁卖/囤货。
- **复核步骤**：
  1. ☐ 用新版本数据重跑三阶段阵容统计（数据采集方式 = compo-knowledge 的 plaza 帖采集链），产出新 Q1 表；
  2. ☐ 对照新旧「全程留用层」：角色进出层则更新 `CROSS_LINE_KEEP_NAMES`，同步其在文档面的语义描述（值只在代码，文档只记依据）；
  3. ☐ 边界声明照旧检查：留场率统计的是上场口径（玩家倾向），名单语义是「通常不卖」——若该常量的消费语义在未来迭代中变化（如从恒囤改为优先级排序档），本步骤的复核对象随之指向新的消费点。
- **同源检查**：凡从 `stage_transitions.md` 派生的其他策略立场常量（按该文「策略层消费点」节逐条清点），版本更新后同样重核。

## 边界

- 本篇只管 CW 域；本体游戏（角色录入等）适配走 `sr-od-version-update-adaptation` 自己的路由表。
- 生成器怎么跑、数据在哪采，方法细节归 [data-collection.md](data-collection.md) 与 [compo-knowledge.md](compo-knowledge.md)，本篇不复制。
