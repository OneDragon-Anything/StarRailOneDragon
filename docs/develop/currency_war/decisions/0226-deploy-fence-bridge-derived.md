# ADR-0226 deploy 围栏随桥派生集

## Status

accepted(2026-08-22;r357)

## Context

局44 r2 实锤:四飞霄(狼狩,hunt3 桥件)全被 deploy 侧 r263b 旧四阵营围栏(RECIPE_FACTIONS)按「非配方件+配方未满」摁 bench——板面 2/5 空槽打仗 + bench 7(金花的件坐冷板凳)。ADR-0222 把狼狩/贝洛伯格入桥与引擎,但 deploy 侧围栏没跟上 = 集成缺口。

## Decision Drivers

- 买侧与 deploy 侧的「合法过渡件」判定必须同源,否则买来的引擎件上不了场
- r263b 纪律(配方饥饿期散件不上板稀释深度)本身正确,错在围栏集过期

## Considered Options

1. deploy 围栏也加狼狩/贝洛伯格手抄:又一处手抄双源
2. **围栏 = RECIPE ∪ ENGINE(桥派生单一源 import)**(选):_DEPLOY_FENCE 模块常量,桥池扩容自动跟随;纯散阵营(欢愉/公司/盛会/夜半)仍拒(纪律保持)
3. 撤 deploy 围栏(配方饥饿期全放):回到散件稀释深度的老病

## Decision

选 2。锁:test_cw_r357_deploy_fence.py(桥阵营过/散阵营拒)。
