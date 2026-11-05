# design/overview — sr-od-version-update-adaptation

## 定位

游戏版本更新后,项目适配跟进的总入口 skill。版本更新带来的适配项会随时间累积,SKILL.md 是路由器:总流程 checklist + 适配项路由表;每个适配项的详细方法放 `references/<主题>.md`,按需加载。

## 边界

- 管「版本更新后跟什么、怎么跟」的清单与方法;单个 op / app 的开发纪律归 od-dev-write-operation / od-dev-write-application;玩法知识归 docs/game。
- 货币战争玩法内单位(牌桌角色 / 装备)是另一套注册表体系,归 sr-od-dev-currency-war;本 skill 只管本体角色数据。
- 客户端更新本身归 od-mihoyo-launcher;本 skill 只要求「能进大世界」这个前置态。

## 构成

- `SKILL.md`:总流程 checklist + 适配项路由表(含未建档项的去向:调研 → 确认 → 补档 → 实施)。
- `references/character-data-entry.md`:新角色数据录入(character_const 字段规则、头像模板、验证)。

## 决策与动机

- **路由器式结构**:适配项随版本增长(新角色只是第一项),全塞 SKILL.md 会持续膨胀;references 按需加载控制注入 token,新适配项按固定结构补档即可扩展。
- **新角色数据独立成项**:几乎每版本都发生,且入口分散(character_const 常量 + 头像模板两处);漏一处只是识别能力降级不报错——OCR 读名是主通道、头像特征是兜底,漏头像时运行期仅日志报「角色头像文件缺失」,所以验证节要求两条通道都过。
- **头像获取只写公开路径**:获取方式写「优先本机可用 skill 目录里的头像获取类 skill,否则游戏内裁切 + 实机验证门」。游戏内裁切是否可用由验证门实测裁决,方法差异不进 skill 正文。
- **官方数据的快照纪律**:character_const.py 本身就是数据快照(提交进仓),符合官方 API skill 的「先快照再消费」纪律;官方词条可能空壳 / 占位 / 前瞻,录入判据回指 characters.md「已知坑」。
- **id 即稳定锚**:Character.id 被用户 config yaml 与头像目录引用,改 id = 静默断链,所以规则里明确「定了不改」,新增前先 grep 防撞。
