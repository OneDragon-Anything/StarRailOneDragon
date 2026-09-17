# 策略器终态契约 交付报告（T-5 策略终态切换）

- 状态:**pending_review**(待对抗验收;T-6/7/8 依赖本件)
- 提交:主仓 `32f7061b6`(终态切换落码)/ 测试仓 `97404cce`(测试翻新)
- 工程门:改面 ruff 全过;`sr-od-test` CW 全量 **508 passed**(0 failed);逐文件 add;`git show --stat` 入库面 = 申报面

## 1. 落地面(对照 landing §3.5 范围)

### 1.1 构造注入 + 12 零参入口(契约 §2.1)

- ABC `CwStrategy`:12 抽象全零参(此前 10 个仍带 options 形参,本批收敛);
  `create_session`/`create_state` 退役维持;docstring 成员计数勘误(「入口 11/成员 13」→ abstract 12,普查清单项)。
- **状态宿主接线(新增机制,申报)**:`state` 改 property,setter 同步写
  `gs.strategy_state`——零参管线以 `self.gs` 为宿主时 `state_of(gs)` 解析到
  同一状态对象、`game_state_of(gs)` 本体直通。动机:mandate 三遍编排内部
  ~148 处 `state_of(session)`/`game_state_of(session)`,若宿主传 `self.state`
  会让 kernel 侧 `game_state_of` 冷建**一次性空容器**(幽灵 gs,判据全盲);
  传 `self.gs` + setter 接线 = 单一来源两处引用。不变量
  `gs.strategy_state is strat.state`(构造与事后重赋值两路径都过 setter);
  T-6 session 退役后 gs 宿主保留为管线约定。
- 行为变化申报(边缘路径,3 处):①encounter 建议闸拒绝分支与「刷新发射后
  重读失败」分支,选卡改由 per-visit 位置 True 后重调判定(旧形态 = 建议帧
  占位 idx=左卡;新形态 = 「按原评分选」评分 argmax,与该分支自身日志语义
  一致);②invest 三闸全败帧 = handler 同访问重调 `decide_invest_strategy()`
  落选卡,策略侧 scratch 同帧去重(建议帧首调发建议、紧随重调落选卡后清键)
  ——等价旧 PickEvent「idx + refresh_slots 并载、闸败回退选卡」,正常识别
  路径选卡零漂移;③正常路径主判据零变化(kernel 纯函数零触碰)。

### 1.2 输出统一单动作词表(契约 §2.2)

- 九 Pick 子类全部接线:flow 七入口 + bridge `decide_encounter` 覆写体 + invest 双相。
- **invest 双相拆分落实现**(原 NotImplementedError 桩):候选读
  `gs.invest_strategy_opts`/`invest_env_opts`;kernel `decide_event` 包装转
  `PickInvest(idx)` 或 `RefreshInvestCards(slots)`;commit_signals 喂入随迁。
- 三刷新动作化:encounter 刷新旗标输入源 = `gs.encounter_refreshed_in_visit`
  per-visit 位(details §2.3 读点声明,禁累计计数);supply = 容器累计计数
  派生(flow 原样);invest = kernel refresh_slots 产生条件原样。
- HoldFrame:`decide_prep_screen` 空发射返回 `HoldFrame()`(None 退役);
  prep 两路径分支判等对象替换 + round 日志文本更新;stall 失实声明三副本
  修正(ABC docstring + cw_screen_prep 两处,现声明 = 哨兵透明、无计数器)。
- kernel 纯函数零触碰:`decide_event` 族返回 Pick 族现状不动;`Action` 联合
  摘 PickEvent(策略词表退役;类保留 = kernel 返回载体 + sim 脚本动作,
  类 docstring 申报)。

### 1.3 十二调用点(契约 §2.7)

- prep×2(buy_cards 循环 + prep handler 两路径)+ 十 pick handler:全部
  「写槽 → `strategy.decide_X()` 零参 → 按动作类型分发」;写槽以该分支将
  调用 decide 为前提(三分语义);encounter 刷新链 = 同访问二次覆盖写槽;
  per-visit 位写点 = 首调前置段 False + 建议处置后 True(fail-loud 直写)。
- buy_cards 循环 `decide_shop_action()` 零参;shop/prep 双形态壳删除
  (干净断);驱动器 `decide_shop_screen`(sim/回放/序列锁)形参保留为
  兼容宿主,内部走零参单动作核。
- 五注册行换键名(`Encounter/Supply/Megastar/Partner/Planner Pick` → 词表
  子类型),注册表结构零改动;`PICK_ACTION_TYPES`/`CW_ACTION_TYPES` 收敛
  单表(注册完备锁遍历单一源 = `CW_ACTION_TYPES`)。

### 1.4 本批修复的 S3 遗留生产断点(申报)

1. `decide_wish_trial` 返回裸 int × handler 读 `.idx` → AttributeError 被
   try/except 吞 → **恒选第 1 张**(静默行为回归,实机未暴露);
2. `decide_star_tome` 同型 → bookcard 无守卫 → op 崩;
3. `decide_box_card` 同型 → box_pick fail-closed 上抛;
4. 桥 `decide_encounter` 旧 5 参签名 × handler 零参调用 → 遭遇屏 TypeError。
   四处均随本批零参化 + 词表化收敛消除(尚无实机暴露即修复,如实申报)。

## 2. 验证(对照 §2.8)

- L1 全量:508 passed(翻新后;含四格 encounter、invest 拆分同帧对照、
  handler 行为锁、注册完备锁单表版)。
- handler 级行为锁:遭遇刷新语义(发射计数/前置闸/重决策恰两次)、invest
  逐卡三闸(闸 1 计数/闸 2 容器账/终结交回单决策)、supply 刷新单点计数、
  env 选卡时点写——全部翻新为词表动作驱动后通过。
- 普查对账(快速面):旧式 decide 调用(src)零残留;策略层 kernel pick
  返回零残留(mandate_v1/encounter.py 搁置件除外,桥 docstring 在案);
  PickEvent 残留 = kernel 返回载体 + sim 脚本动作 + 注释引用(申报形态)。
- L3 语义等价:508 全绿即语义锁面通过(正式 L3 复跑归 T-7)。

## 3. 未竟面(依赖后续阶段,非本批辖)

- **T-6**:StrategySession 类本体退役(kernel 桶 game_state_of 收尾 +
  mandate 管线 session 形参体系终局形态裁决——gs 宿主 vs 显式 state/gs 双参)。
- **T-7**:L3 正式复跑 + 回放旁证(现行 `--run` 面 plan 串 diff)+ 实机
  一局 smoke(锚 = journal 动作行;候实机窗口,不阻代码收口)。
- **T-8**:正本批量更新(flow/README、session.md、fields.md、screens/、
  strategy-docs/13 篇等预登记面)+ 全正本树普查对账(词表清单见 landing
  末阶段)。
- 行为变化登记回执:§1.1 三处边缘路径 delta + §1.4 四处断点修复,待
  验收对账后随 T-8 入正本清单。
