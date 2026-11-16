# sr-od-game-coach 测试场景存档

> 用途：description（触发器）与正文路由修改后的复测题库。实测方法 = 起干净子 agent，只给 skill 目录摘要（不含会话历史），让它逐问判断「应加载哪些 skill」，对照下表预期。

## 2026-11-14 description v16 触发实测（10/10 判得出）

背景：v16 把触发口径改为「凡任务中出现崩铁游戏内容概念词（哪怕只作宾语、哪怕任务本体是执行或开发测试操作）」，源于实机漏触发案例（见 design/overview.md v16）。

### 正例（game-coach 应触发）

| 问法 | 预期加载 | 判定依据 |
|---|---|---|
| 「角色升级之后的奖励我打开了阿哈的画面，帮我用op领取这个奖励，测试一下这个op」（本案例原句） | game-coach + od-dev-write-operation | 双触发设计：开发方法归 write-operation，概念对齐归 coach；coach 侧命中「角色升级后的奖励怎么领」原文例句 + 兜底条款 |
| 「虚构叙事这期怎么配队」 | game-coach + sr-od-treasures-lightward | 选人配队归 coach，期次环境增益归 lightward |
| 「阿哈值得抽吗」 | 仅 game-coach | 抽卡投入决策原文命中；执行归 consume 不触发 |
| 「这个遗器『XX』是什么效果，谁能用」 | 仅 game-coach | 基础信息查询原文命中 |
| 「这个角色升到80级该用哪个op，材料不够去哪刷」 | 仅 game-coach | 养成操作路由原文命中 |
| 「ClaimCharacterAscReward 老是误判没有奖励，帮我修一下」 | game-coach + od-dev-write-operation | 修 op 归 write-operation；「误判没有奖励」含领奖励概念词，coach 先对齐「何时有奖励可领」 |

### 负例（game-coach 不应触发，或有据排除）

| 问法 | 预期 | 判定依据 |
|---|---|---|
| 「跑一下一条龙」 | 零加载 | 无游戏内容概念词、无游戏决策 |
| 「帮我买个小月卡」 | 仅 sr-od-game-consume | 消费执行归 consume（兄弟指路） |
| 「当前卡池来一发十连」 | 仅 sr-od-game-consume | 抽卡执行归 consume；「值不值得抽」的决策才归 coach |
| 「新版本出了，该适配的都跟一下」 | 仅 sr-od-dev-version-update-adaptation | 统筹入口归 adaptation，具体调研届时再载 coach |

### 复测注意

- 判断者只能看到目录摘要，禁止给它会话历史或本文件以外的场景知识。
- 「新版本适配」问法依赖 coach description 中「版本适配统筹 → adaptation」的指路句成立；改这句时须同步重测。
- 待补：官方 wiki 接口直查指路（sr-od-official-api，v16 修订新增）的双触发场景（「这期卡池 UP 是谁、概率多少」应同时命中 coach 投入决策与 official-api 取数）尚未实测。
