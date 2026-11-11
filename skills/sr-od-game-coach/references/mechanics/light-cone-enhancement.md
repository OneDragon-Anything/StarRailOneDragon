# 光锥养成与装备(light-cone-enhancement)

光锥养成三件事:升级(经验+信用点)/ 晋阶(突破等级上限)/ 叠影(同名合成)。
装备 = 把光锥装到角色身上。本文给决策规则与操作路由。

## 1. 决策规则

- **升级优先级**:光锥通常都应拉满 80 级;资源有限时优先拉主 C 在用的
  光锥(吃白值攻击/生命),其余的随后补满
- **星级**:角色合适的光锥就值得养成——有些光锥就是专门用 3 星的,不按
  星级一刀切
- **叠影**:同名光锥合成,合成后叠影数 = 主件阶数 + 各材料阶数(加法,
  非每合一把 +1;低阶材料可加高阶主件,1+1=2 / 2+1=3 实机验证),S5 满。
  一次合成最多置 4 件材料,可一次跳多阶;材料经验等级不继承。叠影只提升
  光锥技能数值(被动效果),不提升白值——对「数值型」技能(增伤/回复百分比)
  收益线性直接,优先叠主 C 在用的专武/高价值光锥;合成不可逆,喂之前确认
  被合成件没有装在别的角色身上(装备件不可作材料,游戏自动过滤)

## 2. 装备与更换(操作路由)

公共前置(装备与升级都从这里开始):

| 步骤 | 用什么 |
|---|---|
| 导航到角色详情 | MCP `goto_screen(target_screen_name='角色-详情')`——从大世界/菜单/任意已建档屏自动路由 |
| 选中目标角色 | op `sr_od.operations.select_character.SelectCharacterOp(cn_name='角色名')` |
| 切到光锥 TAB | op `sr_od.operations.switch_character_tab.SwitchCharacterTabOp(tab_name='光锥')` |
| 查看当前光锥 | 优先米游社 API `mys_get_characters`(注意数据有延迟);要实时确认用 MCP `analyze_screen`——画面为「角色-光锥」时 extras 返回 光锥名/命途/等级/叠影N阶/技能名/白值 |

换光锥按意图分三种情况,路由不同:

### 2.1. 情况 1:不知道要换什么——先浏览账号光锥清单

公共前置之后,打开替换列表看全清单再决定:

| 步骤 | 用什么 |
|---|---|
| 打开替换列表 | op `sr_od.application.cultivation.light_cone.operations.open_light_cone_replace.OpenLightConeReplaceOp()` → 成功状态 OPENED(列表已开且滚回顶部) |
| 读清单 | MCP `analyze_screen`——画面为「光锥-替换」时 extras.items 返回全列表,每件含 光锥名/命途/等级/叠影/占用者(owner) |
| 决策 | 结合「决策规则」与配队知识(damage-and-affix.md)从清单里选定目标 |
| 执行更换 | 走情况 2 或情况 3 的路由——后续 op 都支持从列表画面直接续跑,浏览后无需退出重进 |

浏览收尾(不再换装时):点列表右上角返回箭头回光锥 TAB(`click_game(x=1860, y=68)`,
画面「光锥-替换」建档「按钮-返回」)。**升级光锥前也必须收掉这个列表浮层**
(升级 op 检测到浮层会显式失败,见下节)。

### 2.2. 情况 2:知道要换什么,不确定账号里有没有/是否被占用——尝试换,不抢

公共前置 + 打开替换列表,然后:

op `sr_od.application.cultivation.light_cone.operations.equip_light_cone.EquipLightConeOp(cone_name='光锥名', rank=叠影?, level=等级?)`(rank/level 可选,同名多副本时精确定位)。结果解读:

- 成功(ALREADY_EQUIPPED / LIGHT_CONE_EQUIPPED)= 目标已装备当前角色;
- 失败「仅见已被装备的件」= 账号有但全部装在角色身上——**默认不占用他人
  装备**(allow_take_over=False),转情况 1 浏览另选,或向用户确认能否抢;
- 失败「未找到」= 账号没有此光锥。

### 2.3. 情况 3:明确要换什么,允许占用他人装备

op 同情况 2,加 `allow_take_over=True`——把别人身上的目标光锥换过来
(如「把停云的舞!舞!舞!换给布洛妮娅」)。仅当用户明确要求时使用:
抢走即改变他人配装,不会自动恢复。

- op 经 MCP `run_operation(op_id='<模块路径>.<类名>', args={...})` 调用,
  op_id 见上表(如 `sr_od.application.cultivation.light_cone.operations.equip_light_cone.EquipLightConeOp`)
- `EquipLightConeOp` 幂等:当前角色已装备目标光锥时直接成功;内置滚动
  扫描(12 屏预算)找件、选中验证与结果核对。同名多副本时用 rank/level
  入参精确定位(读得出且不符的件被排除,读不出的件保留兜底排在确认匹配
  件之后)

## 3. 升级光锥(操作路由)

升级 = 提升光锥等级(吃白值)与晋阶(突破等级上限),由同一个 op 完成:
op `sr_od.application.cultivation.light_cone.operations.upgrade_light_cone.UpgradeLightConeOp(fill_generic=False, auto_farm=False)`,
成功状态 LIGHT_CONE_CAPPED(光锥已到上限,或材料不足停在当前等级——日志注明)。

| 步骤 | 用什么 |
|---|---|
| 公共前置 | 同装备路由的导航部分,到光锥 TAB。⚠️ **替换列表浮层必须已收起**(浮层态入口显式失败,收法见装备路由情况 1 的浏览收尾) |
| 执行升级 | op `UpgradeLightConeOp(...)`——入口自动点 TAB 右下「强化」进晋阶界面,反复升级到满或判停,完成后自动关界面回光锥 TAB |

晋阶界面右下按钮三态(op 自动分流):

- 白底「快速升级」= 材料足,直接执行(材料构成与用量查 `cone_lookup`,
  见 1 节);
- 白底「使用通用材料补全」= 缺专属材料但通用材料够——点击弹「材料补全」
  确认框,以通用材料合成替代缺口(**通用材料是稀缺消耗品,梦之珠泪类,
  锄大地/活动来源**);
- 灰字禁用 = 专属与通用材料全缺,无法升级。

材料开关(默认全关——缺材料即判停并报告当前等级,零消耗;开启任一都是
真实消耗,**发起前必须向用户说明并获明确同意**):

- `auto_farm=True`:缺材料时自动「快速刷取」补材料继续升级——每次消耗
  开拓力 30 + 快速刷取券 3(**券不可自然恢复**),单次晋阶段最多连刷 10 次;
- `fill_generic=True`:缺专属材料时确认「材料补全」弹窗用通用材料合成
  替代;auto_farm 刷取预算耗尽后仍缺时,也可转此路线兜底。

满级说明:光锥 80 级后 TAB 页「强化」按钮仍在,op 进晋阶界面读到
「已提升至最高阶」后关闭收尾(状态同为 LIGHT_CONE_CAPPED,日志注明满级)——
对满级光锥调用本 op 是安全的零消耗操作。

**材料不足时(判停后)的手动刷材料**:不想烧快速刷取券(券不可恢复)或券
不足时,可走副本刷取补材料:

1. 进晋阶画面:光锥 TAB 点右下「强化」按钮(MCP `click_game(x=1825, y=992)`,
   画面「角色-光锥」建档「按钮-强化」);
2. op `sr_od.application.cultivation.light_cone.operations.farm_material.FarmLightConeMaterialOp(times=挑战次数)`——
   自动实读晋阶画面第一个缺料材料 → 经游戏内「获取途径」跳转对应副本 →
   委托开拓力挑战刷取。状态:FARMED(刷取完成)/ NO_LACKING(材料栏无缺料)/
   MATERIAL_NO_DUNGEON(缺料材料无可刷副本——途径均为敌人掉落/合成,
   无法跳转,只能实机获取);
3. 刷够后重调 `UpgradeLightConeOp` 继续升级。

⚠️ `times` × 10 开拓力(拟造花萼)为真实消耗,发起前必须向用户确认。
多个缺料材料时 op 每次只处理第一个缺料格,刷完重跑处理下一个。

- 备料(刷材料前算缺口):查单把光锥的材料总量、分段需求与刷取副本用
  `cone_lookup(with_ascension=true)`

## 4. 叠影光锥(操作路由)

叠影 = 同名光锥合成提升技能阶(规则见 1 节:主件阶数+材料阶数,加法,一次
合成最多置 4 件材料)。由 op 完成:
op `sr_od.application.cultivation.light_cone.operations.superimpose_light_cone.SuperimposeLightConeOp(
cone_name='主件光锥名', use_auto_place=True, material_count=1,
confirm_merge=False)`。

| 步骤 | 用什么 |
|---|---|
| 选中主件 | 在替换列表点选要叠影的那件。⚠️ 主件身份必须在这步定对:叠影视图本身不显示光锥名,op 靠「选中光锥名」OCR 在入口校验(不符显式失败,防合错) |
| 执行叠影 | op `SuperimposeLightConeOp(...)`——自动点「强化」进等级提升、切「叠影」TAB、置入材料、合成、关横幅,结束后停在叠影视图 |

材料放置双路径(`use_auto_place` 选,**默认自动置入**):

- `use_auto_place=True`(默认):点「自动置入」——游戏自动解锁并置入同名
  未装备副本**直到叠影上限**(rank3 实机一次 +2 到满阶 5;候选只给补到
  上限所需件数)。锁定副本会被自动解锁(游戏强制,弹「是否自动解锁以下
  高稀有度光锥」确认框,op 代答确认);被装备件不可作材料,游戏自动过滤。
- `use_auto_place=False` + `material_count=N`(≤4):受控单件放置,逐槽
  点选 N 件、每件阶数相加——适合只 +1 的精细控制(如只喂 1 张 rank1)。
  锁定件由 op 代解锁后置入(点详情面板锁标,无二次确认)。

消耗门(`confirm_merge`,默认 False):False = 只走到「可叠判定」即停,
零消耗(不放置材料);True = 置入材料并点「叠影」执行合成。合成不可逆,
且点「叠影」后弹「消耗光锥稀有度较高,是否继续?」确认框(3 星材料同文案,
实机验证),op 自动代答。**True 前调用方必须向用户说明消耗并获明确同意**。

结果解读:

- MERGED = 合成完成,仍可继续叠(多次提升重复运行本 op);
- MERGED_MAXED = 合成完成且已到满阶 5——满叠形态实证:材料区/自动置入/
  叠影按钮整体消失,右下仅剩「叠影已达最大值」标签,无「下阶段效果」;
- NEED_AUTH = 可叠但 confirm_merge=False,零消耗;
- MAXED = 开跑时已满阶,零消耗;
- 失败(消息带现场)= 选中件不是 cone_name / 画面不对 / 材料链路断
  (候选不足等)。

- op 经 MCP `run_operation(op_id='sr_od.application.cultivation.light_cone.operations.superimpose_light_cone.SuperimposeLightConeOp', args={...})` 调用;
  满阶主件发起 = 干净返回 MAXED(零消耗)
