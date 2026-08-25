# 0310 - 载体迁移:decision_v2 唯一策略载体 + 纪律族移植 + registry 双注册

- **Status**: accepted(2026-08-25;裁决终版第三选项落地;**取代 ADR-0290 的渐进迁移安排**——四层框架本体不变,迁移机制改双注册 A/B 窗口)
- **Context**:策略层重构裁决(对抗史:裁决简报→AD6 攻击 10 条→AD7 审查 4 件→裁决终版)定调:
  修复路线经 41 处 locked_line 消费实测不成立,「更便宜的等效手段」不存在(AD6 A9)。
  ADR-0290 的渐进迁移(并行开关→锁迁移→删通道)预设 decision_v2 骨架长期挂靠
  LineStrategy(继承复用战略层+执行钩子)——该形态有三病(AD6 A1/A2/A4):假独立
  (MRO 仍含 LineStrategy)、本体论渗透(candidates 经 LineStrategy 静态谓词读
  locked_line/桥池/线库)、简报对策略主体沉默。裁决第三选项:**废弃
  line_strategy.py(1844 行),decision_v2 成为唯一策略载体;执行纪律族(应急/
  boss_breaker/carry_gate/catchup)移植进 decision_v2 并语义重接**。
- **Considered Options**:
  1. **修复路线(locked_line 消费面收敛)**——拒绝:41 处消费实测不成立(裁决要点 1)。
  2. **渐进迁移维持(ADR-0290 原安排:骨架继承+锁逐步迁移)**——拒绝:继承挂靠=假独立,
     本体论渗透随每批加码;且窗口验收指标无过程目标锚(AD6 A7)。
  3. **载体迁移+纪律族移植+双注册(裁决终版采纳)**——**采纳**:
     - decision_v2 去掉 LineStrategy 继承,独立 CwStrategy 实现(继承 DefaultCwStrategy
       只复用**执行性钩子**——球/箱/遭遇/补给/巨星/伙伴/prep 步级;战略/备战自持);
     - 层1 换源:信号/锁线→cw_intention(W34);体系/组合→cw_system_cards(W32);
       阵容演进→cw_evolution(W33,evolution_step 进决策循环发显式 cw_state v2 动作);
       目标件→hoard_target_set+COMP_LIBRARY v2(W25);插件消费→PLUGIN_LIBRARY(W25);
     - 纪律族语义重接(见 Decision);
     - registry 双注册 A/B 窗口(AD6 A7):新旧策略同 StrategyManager 注册,config
       `strategy_id` 切换;旧文件停用不删——删除门槛=sim A/B 验收通过即删
        (2026-08-25 用户裁定,不等实机;详 Decision 5)。
- **Decision**:
  1. **继承解耦**:`DecisionV2Strategy(DefaultCwStrategy)`;decision_v2 包
     (strategy/candidates/discipline)零 line_strategy import(锁测试断言)。
  2. **纪律族移植+语义重接对照**(strategy_v4 点4/点7/点12 逐条;载体
     `decision_v2/discipline.py`):
     - 应急:hp≤emergency_hp 绝对档+rebirth 地板([18] 保留重生基数)——常量原样;
     - boss_breaker:P1 r≥5 遭遇预备窗/boss 节点 → war 模式+破息地板 10(连胜 EV
       降 5,r308 移植);围栏从 RECIPE_FACTIONS 换意向线 form_tiers∪sub_tiers;
     - carry_gate:carry 从 line_of(locked_line).carry 换 ``intention_core``
       (COMP_LIBRARY v2 锁定套核心);保护集从桥池名单换 hoard 目标集;
     - catchup:pop_baseline+等级门判定原样(r232);执行侧由层2 过滤+层4 地板承载;
     - 掉血三臂(点4〔修A2〕冻结语义):连续 2 场战斗失败/滚动 3 节点 ≥20/滚动
       5 节点 ≥30;非战斗节点不计入不重置;
     - **hp 报警语义**:报警=处置梯度(war+保血通道),**永不单独触发 ALL IN**
       (blood_alarm 分支 allin 字面 False);
     - **位面末 ALL IN 限定**([18]):boss 节点+轮=位面节点数是**唯一**清零地板
       的路径(DisciplineView.arbiter_registry);
     - **保血通道**(点12):报警+遭遇/boss 硬节点 → war 态放行 refresh(弃息 D)。
  3. **评分/仲裁分工**:纪律视图(registry 派生副本)只作用于层2 过滤与层4 地板;
     层3 评分恒用原 registry(ALL IN 窗不扭曲息 EV 平台语义)。
  4. **意向驱动节流**:update_target 段级重入守卫(sim 每轮最多 8 段重入,
     miss 计数分母=轮)。
  5. **旧件处置**:line_strategy.py 标 deprecated 头注(暂不删;C5 兼容契约
     =**窗口期脚手架,清理批随删降级**:config 切 ``line_v2`` 的回退开关在
     A/B 基线对照期全程可用);禁止在旧文件新增功能。**删除门槛=sim A/B
     验收通过**(新策略 P1 域行为正确且不劣于旧基线即删,leader 裁定,
     不等实机——2026-08-25 用户裁定,旧策略删除权下放 leader;双注册即
     删除门槛的判据来源:A/B 基线对照臂)。
  6. **兼容垫片(显式遗留,步 5 锁迁移后删)**:candidates 的
     ``_legacy_target_names``(旧线库/桥池目标集派生)与 discipline 的
     locked_line 方向门回退——仅旧载体形态 session(``v3_hoard`` 缺失且
     locked_line/bridge_id 已设,即旧锁单测直调形态)可及;生产新载体
     update_target 每轮写 v3_hoard,恒走意向源。
- **Consequences**:
  - 正:本体论渗透根除(载体与线库/桥池解耦);纪律族每条可单帧锁;cw_intention/
    cw_system_cards/cw_evolution/COMP_LIBRARY v2 五模块在决策循环内实际点火
    (此前纯查询面+锁测试);回退开关全程可用。
  - 正:ADR-0290 四层框架(候选×评分×仲裁)本体不变——本 ADR 只换迁移机制与层1
    数据源,ADR-0291/0293/0295-0305 的框架锁继续有效(语义化迁移:标签集并入
    'plugin'、registry hash 重记)。
  - 负:A/B 窗口期双载体并存,旧锁(桥池本体论的 ADR-0299/0300 直调单测)靠
    兼容垫片保活——步 5 锁迁移时须一并清偿垫片,防双源长期漂移。
  - 风险:纪律族重接版未经 sim A/B 标定(骨架语义,v1 常量镜像);评分表对战意的
    显影依赖层3 现有项,意向线特定的目标件进度项可能不足——归步 5 验收批。
