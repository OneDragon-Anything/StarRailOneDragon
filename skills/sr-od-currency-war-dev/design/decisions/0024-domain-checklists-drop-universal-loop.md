# 0024 - 通用开发循环撤销:开工/收尾归项目级,checklist 域自管理

- **Status**: accepted(2026-08-27;用户裁决「改策略有策略自己的 checklist,改模拟有模拟的 checklist」「开工和收尾都属于项目级规范,暂时不要,由每个模块自管理」;部分推翻 0002/0016/0017 的全局 8 步 checklist 设计)
- **Context**:SKILL.md 的 8 步「必做 checklist」实际是按策略迭代循环长出来的(判读上局/改前读文档/实机锚点都是策略步),非策略任务(修 op/数据采集/sim 基建)要么空转策略步要么漏自己的域步。用户逐层点破:①「分层测试看上去主要都是策略的」——五层验证里 sim/telemetry 跨局/单帧锁三层实质是策略验证;②通用开工(读进度树/查钩子)与收尾(ruff/全量测试)属项目级规范(AGENTS.local 恢复步骤 / 项目 AGENTS 提交前验证三步已载),skill 里再放一份=双源。
- **Considered Options**:
  1. 保留全局 checklist,域内容打标记——错配仍在,非策略任务继续空转。
  2. 拆「开工三步+域步+收尾门」三层,通用步留 SKILL.md——通用步与 AGENTS 层双源。
  3. **通用步全部撤除,checklist 完全域自管理**(选)。
- **Decision**:
  1. 删 SKILL.md 8 步 checklist;分诊表改为路由到各域 checklist(策略→strategy-work §0,sim→sim-testing §0)。
  2. 「验证工作台」节收缩为「验证(测试分层)」:只留 L1/L2/L3 测试分层命令(两域共用的项目级测试入口)+ 域阶梯指针;策略验证阶梯(文档对照/sim/telemetry 跨局/单帧锁/实机)整体归 strategy-work §4。
  3. 开工通用步不再入 skill(单一源 = AGENTS.local 恢复步骤 + od-dev-stop-hooks);收尾通用验证不再入 skill(单一源 = 项目 AGENTS 提交前验证三步)。SKILL.md 留一行指针声明这个分工。
  4. 原 checklist 各步去向:步 3/4/6/8 → strategy-work §0;步 1/2/5/7 → 通用层(AGENTS/防坑清单/§文档同步)已有承载,不迁。
- **Consequences**:
  - 正:checklist 与任务类型对齐(策略轮没做完策略的步才算未完成);SKILL.md 正文不含策略专属内容,与「策略单一源=strategy-work」声明名副其实;双源消除。
  - 负:非策略域(runtime-ops/telemetry-reading/data-collection/compo-knowledge)暂无自带 checklist——按需后补,当前它们的任务以「门」(判读三问/重启四步/验收单)承载时序;分诊表成为唯一路由器,新增任务型入口必须进表。
  - 关联:0002 的工作流+全局 checklist 设计、「没做完 8 步不算完成」完成门措辞(0017)随之失效;0016 的「checklist 留正文」判据改为「域 checklist 留域文档」。
