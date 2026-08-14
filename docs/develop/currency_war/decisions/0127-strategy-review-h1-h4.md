# ADR-0127 策略 review round-3 修订:H1-H4(3合1 窗口/tempo 收敛/MC 约束/等级锚点)

- 日期:2026-08-15
- 状态:已接受(基于 review 探针实证)

## 背景

策略三轮调优(ADR-0124/0125/0126 + room 扩展)review 发现 4 HIGH 交互缺陷,均有探针复现:

## 决策

1. **H1 3合1 窗口可达化**:游戏合并 = 全场(deployed+bench)。旧 bench>=2 窗口从 shop 不可达
   (第 1/2 张被拦,计数起不来)→ 已上阵单位锁死 1★。新语义:总副本≥3 不买;场上同名时仅
   target/core 继续集(散牌不集 = M8 死钱根因保持被挡)。
2. **H2 tempo 例外收敛化**:阵营计数只用 board(deployed 真值,旧含 bench → 买进单张反向维持
   例外开启 = spread 吸引子,fp 冻结 <0.4);删 cost≥3 无阵营分支(OCR 失败 cost 默认 3 自动放行);
   priority 角色豁免保留。saving gate 例外同收紧 + fp 守卫(成型即关,补齐 ADR-0124 声明)。
3. **H3 MC 约束对齐**:_best_buy_deploy_eval(MC D 牌估值)应用与真实买相同约束(死钱副本不买),
   旧对真实买家会拒的牌照估分 → 刷新期望系统性乐观 → 每轮刷满 cap 烧金(M10 25刷6买)。
4. **H4 等级锚点软化**:P2 r5-9 9→8。M8(lv9 破 2-7)锚点疑幽灵(telemetry p2r1 lv10 与收入模型
   矛盾);收入模型(均值 ~10/轮,上限 13)不支持 lv6→9(178 金)。ADR-0126 部分撤回。

## 后果

- 集星路径打通(P3 chase_star 前提);tempo 例外现在 converge 导向;refresh 烧金受控;
- P1 r7-9 lv7 与 P2 早期 lv8 保留(中等节奏,收入可支撑)
- 验证:M13+ 对局 buys/refresh 比、fp 轨迹、boss HP
