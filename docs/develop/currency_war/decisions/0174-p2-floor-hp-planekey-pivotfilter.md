# ADR-0174: P2 策略专项——地板硬下限 + HP 位面键控 + pivot 位面过滤

## Status

Accepted(2026-08-17,r11 #3/#4 + r20)

## Context

M55 首次健康进 P2(30 血 71 金)仍 P2-4 死。复盘(13149ea2)三层发现:①P2 备战被 OpenTome
活锁瘫痪(365 条决策全是重试,金闲置板冻结——独立修);②comp level_plan 停留意图(万敌单C
lv6=roll)压过 node lv8 地板 → P2 冻 lv6 硬吃两仗;③P2 敌强度(实测 P2-1 掉 19 vs P1 ~10,
影子 DP difficulty_scale 1.5-1.95× 佐证)在 live 零消费——急救阈值/刷新上限全部位面盲;
④hp 11 保命 pivot 选 DOT 队(注册表自注 P2 乏力、攻略明言被抽陀螺)。

## Decision Drivers

- 位面是 CW 敌强度的主结构变量,无视它的策略在 P2 系统性欠反应
- 攻略 meta:P2 玩法=升人口为主、80 血基准进 P2

## Considered Options

1. 全量等 18 号 first_passage 补 plane 参数 + DP 切流——正确但远水(影子模块未上线);
2. **live 最小硬门(选)**:三处定向修,不依赖影子批;
3. 激进位面重分层(每节点独立阈值表)——样本不足(54 局 P2 数据 n=2/档),过拟合风险。

## Decision

选 2,三件:
- **地板硬下限**(`_want_level_up`):comp roll/stable 停留意图只在 P1 压 node 地板;P2+ 落后
  地板即追级(追上后可继续 roll)。
- **HP 阈值位面键控**(`effective_hp_threshold`):P1 不变(兼容)/P2 ×1.25/P3 ×1.5——P2 敌
  强度先验首次进 live 消费。
- **pivot 位面过滤**(`maybe_pivot` 信号 3):Comp 增 `weak_planes` 维度;DOT队 标 (2,);
  保命候选按当前位面过滤(全滤光回退原池)。

## Consequences

- M57 实证:进 P2 lv7(旧版冻 lv6 的对照),活锁修复后 P2 备战流程恢复。
- HP 键控的生效面受 hp 接线滞后一环限制(备战帧常读不到,结算后下环生效)——记 18 号接线批次。
- weak_planes 目前仅 DOT队一条(攻略实证);其余 comp 待数据再标,不做无据标注。
