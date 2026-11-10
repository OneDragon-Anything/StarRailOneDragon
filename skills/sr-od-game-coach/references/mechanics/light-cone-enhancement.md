# 光锥养成与装备(light-cone-enhancement)

光锥养成三件事:升级(经验+信用点)/ 晋阶(突破等级上限)/ 叠影(同名合成)。
装备 = 把光锥装到角色身上。本文给决策规则与操作路由。

## 升级与晋阶

- 升级消耗 稀薄以太(拟造花萼·金/以太之蕾)+ 信用点;0→80 合计约 1597
  以太 + 71 万信用点
- 晋阶在 20/30/40/50/60/70 级各一次,消耗 永寿幼芽/天华/荣枝 系列 +
  「XX之钥」——**钥的命途跟随光锥命途**(智识光锥用智识之钥,出自对应命途
  之蕾),材料刷取副本随光锥命途走,查具体光锥用 cone_lookup(with_ascension)
- 晋阶材料与角色行迹材料同源(永寿系列/之蕾),可与角色养成共用体力规划

## 决策规则

- **升级优先级**:主 C 光锥先拉 80(吃白值攻击/生命);辅助光锥 70 级够用
  ——光锥技能数值只随叠影走、不随等级,辅助吃技能效果不吃白值
- **叠影**:同名光锥合成,每合一把 +1 叠影,S5 满。叠影只提升光锥技能
  数值(被动效果),不提升白值——对「数值型」技能(增伤/回复百分比)收益
  线性直接,优先叠主 C 在用的专武/高价值光锥;合成不可逆,喂之前确认
  被合成件没有装在别的角色身上
- **星级**:5 星 > 4 星优先养成;3 星光锥只做过渡,不投入叠影

## 装备与更换(操作路由)

agent 全程可自动化,链路与可用工具:

| 步骤 | 用什么 |
|---|---|
| 导航到角色详情 | MCP `goto_screen(target_screen_name='角色-详情')`——从大世界/菜单/任意已建档屏自动路由 |
| 选中目标角色 | op `sr_od.operations.select_character.SelectCharacterOp(cn_name='角色名')` |
| 切到光锥 TAB | op `sr_od.operations.switch_character_tab.SwitchCharacterTabOp(tab_name='光锥')` |
| 查看当前光锥 | 优先米游社 API `mys_get_characters`(注意数据有延迟);要实时确认用 MCP `analyze_screen`——画面为「角色-光锥」时 extras 返回 光锥名/命途/等级/叠影N阶/技能名/白值 |
| 装备/更换光锥 | op `sr_od.operations.equip_light_cone.EquipLightConeOp(cone_name='光锥名', rank=叠影, level=等级)`(rank/level 可选,同名多副本时精确定位) |
| 升级光锥到上限 | op `sr_od.operations.upgrade_light_cone.UpgradeLightConeOp(fill_generic, auto_farm)` |

- op 经 MCP `run_operation(op_id='<模块路径>.<类名>', args={...})` 调用,
  op_id 见上表(如 `sr_od.operations.equip_light_cone.EquipLightConeOp`)
- `EquipLightConeOp` 幂等:当前角色已装备目标光锥时直接成功;内置滚动
  扫描(12 屏预算)找件、未装备件优先(不抢他人装备)、选中验证与结果核对。
  同名多副本时用 rank/level 入参精确定位(读得出且不符的件被排除,
  读不出的件保留兜底排在确认匹配件之后)
- `UpgradeLightConeOp` **消耗真实材料**(以太+信用点,拉满约 1597 以太 +
  71 万信用点),fill_generic=通用材料填充、auto_farm=材料不足自动刷——
  两者发起前必须向用户确认消耗
- 备料:以太之蕾(稀薄以太)+ 按光锥命途的之蕾(晋阶钥),查单把光锥的
  材料总量用 cone_lookup(with_ascension=true)

## 与遗器养成的分工

光锥只管「装对 + 拉满 + 叠影」三件事,没有词条随机性(遗器才有刷词条
问题);角色养成顺序通常是 角色/行迹 → 光锥 → 遗器,决策细节见
damage-and-affix.md 与 relic-enhancement.md。
