# ADR-0557: sim 决策下沉方案三混合——判据核上收 kernel 单一源 + sim 发射短路行为消费(反假阴性)

- 状态:已实施(两小批落地;三审整改定稿:sim 门收 armed 单键消除 admission 异常路径假阴性残留、悬空出处收编本 ADR)
- 关联:14 号稿 §9.6(达标即出战臂/发射核 launch_prepared_battle 单一发射函数)、00_framework(包依赖矩阵 LEGAL_EDGES:sim 桶不可依 operations 桶)、ADR-0554(备战收益耗尽出战臂,同发射核第二消费面)、cw_launch_admission.py(kernel 判据核宿主,G1 准入三元先例)

## 1. 背景与问题

生产达标臂(线成型 fp≥1.0 ∧ 战斗就绪)发射帧**短路备战动作链**(金不花);sim(engine_p1)原先行内只记 'launch' 观测键、决策照常跑金照花 ⇒ 金出口族改动在严格同池 A/B 的 ledger 上 pre/post 逐位一致 = **结构性假阴性**。同族事故两次实证(form_ok 镜像族无写者恒 False、AB r2/r3 归因报告)——根都是「sim 可见性靠第二写者自觉」。

## 2. Considered Options

- **A(否决)消费决策整体下沉策略层(方案一)**:方向正确但达标臂发射意图迁入 decide_shop_screen 动作域需扩展动作合法域+重排备战单轮决策序,与消费臂 v4 三检查点叠加回归,一次性批面过大。保留为终态方向(独立策略批收敛)。
- **B(否决)engine_p1 复刻等价逻辑对拍(方案二)**:本缺口全部分量在「接线与短路语义不可见」而非判据公式分叉(谓词早已 kernel 单一源且 sim 已直调)——复刻只造语义双源,把 form_ok 类故障制度化。
- **C(采纳)方案三混合**:判据核恰一处实现上收 kernel,cw_loop(执行面)与 engine_p1(行为消费面)为同一函数的两个消费面;差异全部属执行/观测皮肤,不含判据语义。长期收敛方案一终态,届时判据核保持策略与 sim 的共同谓词源。

## 3. 两小批架构(已实施)

- **小批① 判据核上收(零策略语义变化)**:`readiness_launch_decision(state, comp, *, line_members) -> {armed, auth_basis, admission}` 纯函数入 kernel/cw_launch_admission.py;cw_loop 备战分支与 engine_p1 发射建模块删内联直调同一函数;armed 语义 = 上收前内联式逐位等价(测试仓等价锁:30 状态扫描+None/阈值边界)。
- **小批② sim 短路行为消费**:engine_p1 发射帧(判据核 armed ∧ 战斗类节点)本轮短路决策段(不跑 decide_shop_screen,金不花;部署代理块照常 = 与生产 RunDeploy+StartBattle 同构);'launch' 行 short_circuited 分键;短路帧 m1p 恒 None(生产无该决策帧,结构性无帧盲区,申报口径入 strategy-work 验证节)。
- **反假阴性哨兵**:sim/checks/launch.py check_sim_launch_short_circuit(发射帧分键缺位/决策照常/金照花三形态红;spend 位 buys 嵌套 dict 展平求和,防红路径崩成非结构化)——守卫移除即红。

## 4. 边界申报

- sim 门 = **armed 单键**(三审整改:原 admission 非 None 门在预估异常路径留下「生产短路金不花、sim 决策照常」的假阴性残留,恰为本批声称消除的结构根);admission 仅作 victim 观测位,异常吞 None 不影响短路。
- sim 无屏态过期/浮层/执行失败面:ok 恒 True;战斗就绪在 sim = 节点为战斗类。
- 执行失败/浮层/C1 计数/闩面:执行层皮肤,sim 不建模(非缺陷)。

## 5. 风险与后果

- **池基线断裂(确定)**:小批② 起 sim 金流对齐生产短路语义,池指纹对照链断裂;短路前批读数须按「短路前基线」口径标注,下批 sim = 新基线首批(申报义务在编排者派对照批任务书时声明)。
- 新金出口臂禁落 operations(落位纪律):判据入 kernel/strategies,sim 天然消费;A/B 报告必带 sim 可观测性声明(单一源 = strategy-work「验证」节)。
