# 欢愉契约条件腿建模(银狼选择触发回调) 迭代设计(总纲)

## 0. 元信息

- 迭代目标:把欢愉契约条件腿从「临时翻来源测量仪表」升格为**正式模型**——银狼策划
  选择上报(头号玩家选项触发)时,欢愉契约在册即授予条件腿单位;模型入库即条件腿
  定谳,`JOY_PROVISIONAL_KIND` 临时闩退役。
- 用户裁定(2026-09-21):①模型逻辑 = 「银狼选择动作上报(证据闩防重)时,若欢愉契约
  在册 → `gain_character(随机[火花, 开拓者·欢愉], 1★, rand=True)`」;②本批先出迭代
  设计,对抗审后实施。
- 效果原文(`data/cw_invest_data.py:451`,id=1201,效果原文直读源):「获得
  【银狼LV.999】,她每次触发独立羁绊【头号玩家】选项时,获得【火花】或
  【开拓者·欢愉】。」
- 状态:草案(候对抗审)
- 文档清单:无详设(单文档方案,本篇即完整设计)

## 1. 问题与动机

### 现状症状(锚 = 文件::符号,路径根 = `src/sr_od/application/currency_war/`)

1. **条件腿无模型,临时仪表空转**:欢愉契约条件腿(每次头号玩家选项触发随机获得
   火花/开拓者·欢愉其一,两件均 4 费、`cw_chars.py:150-151` 在册)以
   `GiftGrant.chars_conditional` 声明性数据在册(`cw_investments.py:1577-1580`),
   无引擎;采证期临时协议 = `on_env_gained` 欢愉契约分支对 bench/equips 值不变翻
   来源 + `joy_contract_provisional` 标记行(`cw_gain_chain.py` JOY_PROVISIONAL_KIND,
   银狼批 design §2.7② 立项)。**遥测实况:185 个 jsonl 全量扫描零命中**——仪表
   未采到任何数据(欢愉契约在已录局几乎未被选),被动等数据不成立。
2. **临时闩与种子底座新交互冗余**:开局种子底座(gs-opening-seed 批,fields.md
   §2.6)后,新局选欢愉契约时 bench/equips 已是 rand 态——翻来源动作冗余化;仅
   P2/P3(锚定后)选卡场景翻面仍有差异捕获作用。
3. **策略价值未入账**:plaza 数据欢愉契约关联三套 comp(绯英欢愉 0.7/狼尊欢愉
   0.6/火花星间旅人 0.6),两套以条件腿单位为核心件——条件腿触发频率是策略评估
   真输入,当前不可见。

### 根因归层

**语义层**——条件腿的触发事件(头号玩家选项弹窗被处理)已有精确的工程观测面
(银狼策划选择动作上报,证据闩防重),但「触发 → 授予」的因果从未建模;临时闩是
建模前的测量代偿。

### 关键机制事实(依据就地标注)

- 头号玩家 = 银狼LV.999 专属独立羁姻(`cw_factions.py:105`,档位 (1,)),效果 =
  2★ 起「骇入」:每次触发在「修改自身费用 / 获得妙妙小道具(骇客改件族)」间选择,
  3★5 费狼尊接管(原文存档 `docs/game/currency_war/data/characters/银狼LV.999.md`);
- 触发观测面已存在:银狼策划选择动作上报 `report_action_pick_planner_param`
  (`kernel/cw_action_report/pick_planner.py:58`,两相形态,落地相 = 重入裁决出口
  `EVIDENCE_OVERLAY_CLOSED` 证据闩,每次弹窗恰一次,腿型分派
  equip/upgrade/unknown/weaken);
- 触发前置自隐含:弹窗只在银狼LV.999 ≥2★ 出现(原文),op 触发即隐含前置,模型
  无需另判星级;
- 欢愉契约在册 = `gs.active_env`(match 级,投资环境落地时写);欢愉契约送 1★
  银狼LV.999,合成到 2★ 后条件腿才开始,时序天然成立。

### 解决到哪 / 明确不解决

解决:条件腿授予建模(触发回调 + 随机授予 + 获得链固定时序)与临时闩退役。

明确不解决(防外溢):

- 头号玩家两选项本体(升费腿/改件腿)的既有模型不动;
- 条件腿授予的**频率统计与策略消费**(comp 评估面)不在本批——本批只保证授予
  如实入账;
- sim 引擎对 planner 选择链的接线(rng 流键注入的 sim 侧消费)不在本批(报告
  函数 rng 注入缺省 None = 实机猜测语义,与骇客改件采样同约定);
- 接管局局限如实申报(§2.6-4):接管局 `active_env` 无写端(C 类不种),条件腿
  识别不可达,真值归观察覆盖。

## 2. 方案(完整设计)

### 2.1 模型(一句话)

**银狼策划选择上报落地相(每次头号玩家选项触发恰一次)时,若 `active_env` 归一
等于「欢愉契约」→ `gain_character(随机[火花, 开拓者·欢愉], 1★, rand=True)`。**

### 2.2 实现面

1. **rider 落点**:`report_action_pick_planner_param` 落地相内、腿型分派**之前**
   (触发语义 = 弹窗出现即触发,与选择哪条腿无关;unknown/weaken 腿同样计数——
   它们同样经过头号玩家弹窗)。授予调 `cw_gain_chain.gain_character`(import 方向
   合法:action_report → kernel 链,与 pick_invest_env 同构;cw_gain_chain 不反向
   import action_report,零循环)。evidence = `joy_conditional:<单位名>`;
   producer 沿用 `_PLANNER_PRODUCER`。
2. **随机单位采样**:rng 注入先例同骇客改件(`roll_hacker_mod` 形态)——报告函数
   新增 `rng: random.Random | None = None` 关键字参数,缺省 None = 实机未播种
   (采样是猜测,sim 传流键 = 世界真值,同一上报函数两副面孔);`random.choice`
   均匀二选一,披露键注释就地申报(均匀分布未实测,候校准)。
3. **rand 语义**:授予体含采样(二选一)→ `rand=True`(design 获得链 §5 纪律:
   效果体含采样 → 对其发起的子链传 rand=True);未锚定期经 `anchor_aware_write`
   亦落 rand,通道一致。
4. **在册判定**:`normalize_invest_name(gs.active_env.value or '') == '欢愉契约'`
   (两侧归一,防形变);`active_env` 为空/其他环境 = 不授予。
5. **落位**:走 `gain_character` 固定时序(落位 → 回调 → 单级合成/溢出落位)——
   条件腿单位是 4 费角色,正常参与 3 合 1;溢出善后归策略面(链纪律不变)。
6. **临时闩退役(design 获得链批裁定「定谳后必须撤」的兑现)**:删除
   `cw_gain_chain.py` 的 `JOY_PROVISIONAL_KIND` 常量、`on_env_gained` 欢愉契约
   翻来源分支(值不变 write_logic_rand 两域 + 标记行)与 GainOutcome 的
   `provisional_mark` effects 项;模块 docstring 失败安全/条件腿自述同步改写。
   撤除后 `on_env_gained` 欢愉契约仅走 chars_immediate 腿(银狼LV.999 入链)。

### 2.3 触发计数正确性(证据闩语义)

- 落地相门(`evidence == EVIDENCE_OVERLAY_CLOSED`)即既有家族的每次弹窗恰一次
  语义(重入裁决出口「入口词不在 = overlay 已关」),rider 直接受益,零新闩;
- **弹窗选项族与 weaken 档定性(2026-09-21 用户问询澄清)**:原文二分法 = 「修改
  自身费用 / 获得妙妙小道具」两.option;代码的 weaken 档 =
  **防御性兜底分类**(选项卡文含「弱化/降低敌人」且装备名锚未命中时降级入桶——
  来源疑为妙妙小道具装备卡的卡文关键词,如破解芯片族;`classify_planner_leg`
  关键词降级 `cw_events.py:975`),**无游戏原文依据、实机零出现**(185 jsonl 零
  命中),非实证卡类。rider 计数不受影响:落地相 = 弹窗出现即触发,与卡类无关
  ——原文二分法下该语义反而更干净;
- 发射相(evidence 缺省)不触发 rider(零写);
- rider 在腿型分派前执行,与腿型零耦合——但**排序上置于各腿之前、失败不阻塞
  各腿**(授予与选项应用是两条独立因果;gain_character 异常上抛语义不变,
  §获得链零吞错纪律)。

### 2.4 已知边界(如实申报)

- **接管局**:active_env 接管局无写端(C 类不种,gs-opening-seed §2.2),条件腿
  在接管段不可达——授予不入账,真值归观察覆盖;
- **3★5 费狼尊接管后**:弹窗是否停止 = 游戏行为未实证;若停止则触发自然归零,
  模型无需特判(op 不报 = 不授予);
- **授予分布**:均匀二选一系原文「或」+ GiftGrant「随机获得」的建模口径,分布
  形态未实测;`logic_rand_outcome` 行自然校准(候选集仅两成员,判读面自证);
- **授予星级 1★ 先验**:原文未标,沿既定约定;观察覆盖纠偏。

### 2.5 行为变化申报

1. **锚定后选欢愉契约的新可见性**:此前条件腿授予仅观察静默覆盖;模型入库后
   授予以 `gain_character` 落账(placement/合成行,evidence `joy_conditional:*`),
   锚定后写 logic 通道——若模型与真值不符将走失配网(真信号);
2. **bench 压力建模化**:高频触发下条件腿单位持续入 bench(可参与合成)——容器
   从「观察后知」变「触发即知」,策略器消费面获得真实时序;
3. **临时闩退役**:joy_contract_provisional 标记行与 bench/equips 翻来源行为消失;
   相关历史判读口径(以标记行识别欢愉契约局)改用 `joy_conditional` evidence 前缀;
4. **journal 增量**:每次头号玩家触发且欢愉契约在册 +2~4 行(落位/合成,随合成
   级数);欢愉契约在册时旧闩的 -3 行(两翻面+一标记)相抵。

### 2.6 测试面

- **双臂通道**:种子容器(未闩)+ 欢愉契约在册 + 落地相上报 → 授予落 bench
  source=logic_rand;`gs.prep_anchored = True` 直赋后 → source=logic;
- **在册判定**:active_env 空/其他环境 → 零授予;欢愉契约 → 恰一次授予;
- **rng 注入**:同 seed 同单位;两候选均可达;
- **全腿型计数**:equip/upgrade/unknown/weaken 四腿落地相均触发 rider(弹窗 =
  触发语义);发射相零触发;
- **时序锁**:授予走获得链固定时序(落位 → 回调 → 合成);
- **撤闩**:`on_env_gained` 欢愉契约仅 immediate 腿(零翻面/零标记行);
  `JOY_PROVISIONAL_KIND` 全仓(src)零引用(grep 断言经由台账面/源码禁扫纪律的
  等价形式:对欢愉契约落地调用断言零 provisional 行);
- **既有测试随迁**:`test_cw_gain_chain`/`test_cw_yinlang_phase32` 中 joy 临时闩
  断言改写(判定「测试过时」纪律,commit message 注明)。

### 2.7 与相邻批的关系

- **gs-opening-seed(已闭环)**:本批消费其 `anchor_aware_write`/种子底座/锚定闩,
  §2.6-8 rand 语义例外的立据面自然覆盖本批授予;
- **invest-landing-chain(已闭环)**:`cw_gain_effects.py`/`gain_invest_strategy`
  与本批零交叠(挂点 = `pick_planner.py`,该批只动了 planner 升费腿的既有语义,
  未动其上报签名);
- **tool-gain-report(在飞)**:文件面交叠核查开工前执行(其 `tool_use.py` 在飞);
- **银狼批(已闭环)**:挂点函数 = 其交付的 `report_action_pick_planner_param`,
  本批只增 rider 与 rng 形参,腿型分派本体零改动——在其交付语义上纯增量。

## 2.8 定谳语义

本批落地 = 欢愉契约条件腿**定谳**(临时闩撤除条件达成):授予行为由原文 +
触发观测面直接建模,残余不确定(分布形态/授予时点/星级先验)全部处于
「观察与 outcome 行自然校准」辖域,无需再持测量仪表。验收后正本
(gain-chain.md §3 条件腿标记面条目)随末阶段改写为本模型。
