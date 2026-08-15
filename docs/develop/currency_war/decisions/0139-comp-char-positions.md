# 0139 comp 特定站位覆盖命途默认(char_positions;复查 #9 落地)

## Status

accepted(2026-08-15;攻略复查 #9)

## Context

站位此前只按命途 position_pref 静态分流(cw_chars 注册表),但攻略有 comp 特定的实证站位要求:绯英体系**爻光必须后台**(UP 反向论证:后台跑条给绯英多开大总伤更高,前台倍率<20% 残血版);万敌单C **万敌独前排**(燃血角斗场吃受击);追击飞霄 **知更鸟前台**(支撑中后期,生存位优先前台)。

## Considered Options

- 落点:只改 plan 层(_pick_deploy_row)vs plan+执行器(deploy_bench _bench_pos)都接 —— 后者(RunDeploy 组合动作走执行器内部选排,只改 plan 会漂移)。
- 数据:每角色全局字段 vs **comp 级 char_positions**(同一角色不同 comp 要求不同,如爻光在绯英必后台、别处未必)→ comp 级。

## Decision

1. Comp.char_positions: dict[str, str](角色→front/back;空=全按命途默认)。
2. 三处消费同语义:plan `_pick_deploy_row(state, bc, target_comp)`(覆盖 pref)+ 策略层腾席链传 target + deploy_bench `_bench_pos` 填充处覆盖。
3. 数据:绯英欢愉{爻光:back} / 万敌单C{万敌:front} / 追击飞霄{知更鸟:front}(攻略实证,来源注释)。

验证:覆盖测试 2 项(无 comp 按默认/有 comp 覆盖)+ 数据在库断言;CW 全套 395 passed。
