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
3. **分域即分治**:同构但不共用的域(如遗器/光锥)各自持完整实现副本,
   零跨域 import;复制面靠既有测试锁定行为。是否归并的评估时机 = 第三份
   同构复制出现时(跨件半问),不做预防性抽象。

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
- 三线各自完整实现,不抽共用底层;三条线都落地后再评估是否域内归并。

## 5. 域内 op 清单

| 域 | op | 状态 |
|---|---|---|
| character | UpgradeCharacterOp / UpgradeTraceOp | 可用(auto_farm/fill_generic 消耗路线全链未实测) |
| character | CharacterLightConeRecognizer(识别器) | 注册可用 |
| character | FarmCharacterAscensionMaterialOp | 立项候实机窗 |
| light_cone | EquipLightConeOp / UpgradeLightConeOp / SuperimposeLightConeOp / OpenLightConeReplaceOp | 可用 |
| light_cone | FarmLightConeMaterialOp | 可用(全链实机验证过,原 FarmMaterialOp 改名迁入) |
| relic | EquipRelicOp / EquipRelicEnhanceOp / SelectBagRelicOp / OpenRelicReplaceOp | 可用(抢件 allow_take_over=True 全链候实机窗) |
