# 账户养成域(cultivation)设计正本

> 域定位:角色/光锥/遗器三条养成线的代码归位包。命名依据:游戏 UI 入口实名
> 「培养」,社区与 sr-od-game-coach 知识库统一用「养成」,两词同义。本文是
> 正本——写「系统现在就是这么设计的」,与代码现状同步维护。

## 1. 域结构

```
src/sr_od/application/cultivation/
├── character/operations/      # 角色线:升级/行迹/角色详情页光锥识别器
├── light_cone/
│   ├── operations/            # 光锥线:装备/升级/叠影/打开替换列表/缺料刷取
│   └── light_cone_list_recognizer.py   # 光锥替换列表自含识别器
└── relic/
    ├── operations/            # 遗器线:装备/强化/背包选件导航/打开替换列表
    └── relic_list_recognizer.py        # 遗器替换列表自含识别器
```

- op 注册与识别器注册靠 backend 扫描根(`sr_od.operations` + `sr_od.application`
  rglob 全深度)自动发现——域内新增 op/识别器放对位置即被注册,无需登记。
- op_id 形态 = `sr_od.application.cultivation.<域>.operations.<模块>.<类名>`。

## 2. 域归位组织约定(后续域照此办理)

1. **域判定**:一组代码服务同一玩法域(如逐光捡金 tl_* 系列)且与其它域
   无策略层耦合,即具备归位条件;通用工具(大世界兜底/op 基类/导航件)留
   `operations/` 平铺层,不为归位而归位。
2. **归位手法**:git mv 保历史 → import 三形态排查(from-import/模块对象
   import/import as)→ 测试仓镜像随迁(fixture 目录随测试文件走)→ 文档
   op_id 引用同步(op_id 前缀 + 裸类名双 grep 归零)→ 离线注册复验。
3. **分域即分治 + 域内共用件**:跨线大域(遗器/光锥/角色养成线)之间零
   import、不做预防性抽象、各自持完整实现副本——这一层不变;是否归并的
   评估时机 = 第三份同构复制出现时(跨件半问)。评估结论按两分法落地:
   - **策略差异留 op**:分支顺序、路由语义、计场时机、返回词表、收尾载体
     这类「为什么这么做不同」的实现,留在各线 op,禁用参数化糊弄成假同构;
   - **机械同构进域内 helper**:两线以上逐字/近字相同、差异可全参数表达、
     且经 op 实例属性访问可保测试缝的实现段,收进域根共用模块(本域首例 =
     `upgrade_common.py`,三升级 op 家族消费)。helper 三纪律:不持状态
     (状态归 op 账本属性)、不做线间策略分叉(三线合法不同的分支留 op
     节点图;三线同形的配置分支可入 helper)、一切识别/回合/账本访问与
     缝间调用经 op 属性(测试桩在 op 类上生效;helper 互调经 op 委托缝,
     禁直调兄弟 helper)。
   - **第四形态接入**:新升级类 op 构造自己的 spec 常量(`UpgradeLineSpec`
     线私有值)与薄委托私有方法,复用 helper 不复制实现;helper 缺新画面/
     新语义时扩参数(带向后兼容默认值),不 fork 副本;helper 变更须过全部
     已接入线测试。

## 3. 识别器自含口径(遗器/光锥)

- 两域识别器(`relic_list_recognizer` / `light_cone_list_recognizer`)各自
  完整持有:网格定位(等级文本锚点 + 轮廓补充 + 网格补位证据门槛——遗器侧
  末行带只出锚点位,光锥侧分组末行补位须过轮廓/等级文本证据)、masked 模板
  匹配身份层(双档级联:遗器 90/96px、光锥 100/106px,各自实机标定)、角标
  占用者匹配(SIFT)、本域模板库与缓存(遗器名称键 / 光锥 id 键卡面库单一
  入口)。
- **两域之间零 import**;差异化标定(列数/角标几何/等级文本形态)在各自
  文件内。兜底策略独立演进:遗器侧兜底重做(低置信门槛/重试标记/图像哈希
  对照三路线)不影响光锥侧。
- 修改任一域的定位/匹配算法后,该域的 owner 基准与识别器测试是行为锁
  (光锥 48 用例 / 遗器 33 用例),先过基准再调参。

## 4. 刷材料三线(接口契约)

- 光锥线 `FarmLightConeMaterialOp`(已实机验证):起点 = 光锥晋阶画面
  (光锥-等级提升),缺料栏红条判定 → 材料弹窗 → 游戏内「获取途径」跳转
  → 委托 UseTrailblazePower(skip_transport=true)。
- 角色突破线 `FarmCharacterAscensionMaterialOp` / 行迹线 `FarmTraceMaterialOp`
  (立项候实机窗):起点分别为角色晋阶画面/行迹画面,流程形态以实机摸底
  为前置(光锥线的红条标定不可直接外推——晋阶/行迹画面缺料栏形态未摸底)。
- 机械同构面已按 §2.3 两分法收进 `upgrade_common.py`;策略差异与识别建档
  覆盖仍各线自持。

## 5. 域内 op 清单

| 域 | op | 状态 |
|---|---|---|
| character | UpgradeCharacterOp / UpgradeTraceOp | 可用(fill_generic/farm_dungeon 消耗路线全链未实测;行迹线起点=面板态,详见 §6) |
| character | CharacterLightConeRecognizer(识别器) | 注册可用 |
| character | FarmCharacterAscensionMaterialOp | 立项候实机窗 |
| light_cone | EquipLightConeOp / UpgradeLightConeOp / SuperimposeLightConeOp / OpenLightConeReplaceOp | 可用 |
| light_cone | FarmLightConeMaterialOp | 可用(全链实机验证过,原 FarmMaterialOp 改名迁入) |
| relic | EquipRelicOp / EquipRelicEnhanceOp / SelectBagRelicOp / OpenRelicReplaceOp | 可用(抢件 allow_take_over=True 全链候实机窗) |

## 6. 升级 op 家族失败适配

角色晋阶线 / 光锥线 / 行迹线的「刷本路线」在战斗失败时自动继续,不再放弃:
失败画面委托共享失败继续件 `ResumeFromBattleFail`(challenge_mission 包,自带
新/旧两态失败画面分流,周本挑战核心同款)回挑战画面后重发。

- 角色晋阶线(`UpgradeCharacterOp`):失败分支在返回分类节点首位;预算检查
  **内联在失败分支**(重发环不经过升级循环的预算判停,必须在分支内)——预算内
  重发回「副本刷取」分流,预算耗尽关副本回大世界走既有 BACK_TO_WORLD 出口
  交重走入口链,由升级循环判停收尾;共享件失败原样透传交调用方。
- 光锥线(`UpgradeLightConeOp`):与角色线同构,重发回「副本刷取分流」;计场
  时机维持现状(点击时计,与角色线的进本计轮不统一,刻意保留)。
- 行迹线(`UpgradeTraceOp`):契约改面板态——起点 = 角色-行迹·面板态(agent
  在树态读节点三态、点开目标技能面板后调用),起跑闸以「简略描述」开关 +
  分类读区现读与 target 等值校验(不维护固定枚举,新命途分类免改码),不符
  显式失败(零消耗拦点错节点);终点 = 一切出口先关面板回树态(_final_status
  携带终态)。节点选择归 agent,op 不做技能树选择;手动刷本划出 op 边界
  (花萼侧调用方按行迹缺料自行导航,FarmTraceMaterialOp 立项前过渡态)。
- 券刷消耗实测定案:行迹材料出自拟造花萼(赤)= 开拓力 10 + 券 1/次(与角色
  晋阶线 30+3、光锥线 10+1 各自独立,勿互相复用常量)。
