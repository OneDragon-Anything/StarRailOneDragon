# 0130 部署散牌留 bench(执行器对齐 planner)+ P3 避高难遭遇 + 装备价值补缺

## Status

accepted(2026-08-15;用户节奏批次 2:§7-1 开场囤 bench + 攻略复查 #3/#7)

## Context

1. **deploy 执行器是 deploy-all**:`_deploy_deterministic` 把每个备战角色无差别上阵(仅按前后排属性分流),完全不消费 planner `_should_deploy` 的部署决策(target 才上 / 同阵营成对才上)。M14/M15 遥测实锤:买单张散牌全部上场 → 板 7 阵营散装 → **fp 冻结 0.25 的 spread 种子**(用户节奏 §7-1:「开场买牌囤 bench,不上阵」)。
2. **decide_encounter 无 plane 维度**(复查 #3):P3 高难遭遇(7-3/7-4)一次 -70 血且无增益回报(经济运营:18/核心机制:26),成型也不该赌;且 diff_norm=(difficulty-1)/2 对「其四」(=4) 越界到 1.5。
3. **_EQUIP_VALUE 缺核心装备**(复查 #7):火力风暴潮/高周波电锯/冷笑话引擎/翁瓦克 全 0 分 → 补给/装备决策系统性低估 core 装(风暴潮 = 伤害征服核心乘区)。

## Considered Options

- 散牌过滤:消费 plan 的 pending_deploys(bench_idx 映射脆,plan 模拟槽位与运行时漂)vs 在执行器按 `_should_deploy` 同语义重判(身份 SIFT 现读,真值)→ 后者。
- 未识别角色(SIFT miss):留 bench(严防 spread)vs 照旧上 → 照旧上(无法判 target/阵营,且防板空;SIFT 71 库可靠,miss 少)。
- 板完全空且无 target 无对:全留(纯囤)vs 上 1 个 → 上 1 个(body > 空板,防白掉血)。

## Decision

1. `deploy_bench._deploy_deterministic`:rest(off-target)过滤 —— target 上、同阵营成对(board+bench 计数≥2)上、未识别照旧上、板空保底 1 个;被扣下的记 log(`散牌留 bench`)。
2. `decide_encounter._score`:diff_norm 钳 0..1;plane==3 → 难度项恒为罚(-0.5×diff_norm,成型不赌)。
3. `_EQUIP_VALUE` 补:火力风暴潮 6 / 高周波电锯 5 / 冷笑话引擎 4 / 翁瓦克 4。
4. `TRANSITION_FACTIONS` 扩表(复查 #2,必修三前期公式):+银河学者(挖矿经济)/+治疗(保 1-5 关生存)—— 旧表仅 5 伤害系,经济/生存过渡被当 spread 罚。

验证:CW 全套 378 passed;部署过滤行为 M17 live 验(散牌留 bench log + 板阵营数下降 + fp 轨迹)。
