# 欢愉契约条件腿建模(银狼选择触发回调) 迭代设计(总纲)

## 0. 元信息

- 迭代目标:把欢愉契约条件腿从「临时翻来源测量仪表」升格为**正式模型**——银狼策划
  选择上报(头号玩家选项触发)时,欢愉契约在册即授予条件腿单位;模型入库即条件腿
  定谳,`JOY_PROVISIONAL_KIND` 临时闩退役。
- 用户裁定(2026-09-21):①模型逻辑 = 「银狼选择动作上报(证据闩防重)时,若欢愉契约
  在册 → `gain_character(随机[火花, 开拓者·欢愉], 1★, rand=True)`」;②本批先出迭代
  设计,对抗审后实施;③**weaken 兜底档整体退役**——「没找到证据的就是不存在」:
  头号玩家原文二分法(修改自身费用/获得妙妙小道具),weaken 分类无原文依据、
  实机 185 jsonl 零出现(问询澄清 2026-09-21),分类器/打分/上报三处一并剔除。
- 效果原文(`data/cw_invest_data.py:451`,id=1201,效果原文直读源):「获得
  【银狼LV.999】,她每次触发独立羁绊【头号玩家】选项时,获得【火花】或
  【开拓者·欢愉】。」
- 状态:草案(r1 攻击 11 条处置完毕,候复审)
- 文档清单:无详设(单文档方案,本篇即完整设计)

## 1. 问题与动机

### 现状症状(锚 = 文件::符号,路径根 = `src/sr_od/application/currency_war/`)

1. **条件腿无模型,临时仪表空转**:欢愉契约条件腿(每次头号玩家选项触发随机获得
   火花/开拓者·欢愉其一,两件均 4 费、`cw_chars.py:150-151` 在册)以
   `GiftGrant.chars_conditional` 声明性数据在册(`cw_investments.py:1577-1580`),
   无引擎;采证期临时协议 = `on_env_gained` 欢愉契约分支对 bench/equips 值不变翻
   来源 + `joy_contract_provisional` 标记行(`cw_gain_chain.py` JOY_PROVISIONAL_KIND,
   立项出处 = changes/2026-09-18-yinlang-exclusive-loop/design.md「欢愉契约(1201)
   条件腿——采证期运行协议」节;迁移史 = 投资两屏批 landing「provisional 闩随
   on_env_gained 迁 kernel」)。**遥测实况:185 个 jsonl 全量扫描零命中**——仪表
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

- 头号玩家 = 银狼LV.999 专属独立羁绊(`cw_factions.py:105`,档位 (1,)),效果 =
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
  识别不可达,真值归观察覆盖;
- **条件腿族面边界(核三申报)**:ENV_GIFTS `chars_conditional` 非空条目共 7 个
  环境(量子同频/公司/持续伤害/战技点/星核猎手/欢愉契约/命运圣杯,含特邀专家:银狼),
  同属「条件腿声明性数据无引擎」族——本批只建模欢愉契约,理由 = 唯一已落地的触发
  观测面(planner 上报);其余环境触发事件(升星时/累计利息/晶矿计数/一役后/圣杯
  试炼)均无观测面,逐件建模 vs 统一条件腿框架候族批裁决,禁逐件无声展开。

## 2. 方案(完整设计)

### 2.1 模型(一句话)

**银狼策划选择上报落地相(每次头号玩家选项触发恰一次)时,若 `active_env` 归一
等于「欢愉契约」→ `gain_character(随机[火花, 开拓者·欢愉], 1★, rand=True)`。**

### 2.2 实现面

1. **rider 落点与失败语义**:`report_action_pick_planner_param` 落地相内、腿型分派
   **之前**(触发语义 = 弹窗出现即触发,与选择哪条腿无关)。授予调
   `cw_gain_chain.gain_character`(import 方向合法:action_report → kernel 链,与
   pick_invest_env 同构;cw_gain_chain 不反向 import action_report,零循环)。
   evidence = `joy_conditional:<单位名>`;producer 沿用 `_PLANNER_PRODUCER`。
   **调用点级 best-effort(显式裁定)**:rider 调用包 try/except——异常 log +
   缺陷留证(`kind = 'joy_conditional_grant_failed'`)后照常继续腿型分派。理由 =
   授予与选项应用是两条独立因果,授予失败不得拖垮选项应用;这是「链原语零吞错」
   纪律的**调用点级显式例外**(链内部照旧零吞错,与 §2.1/§2.4 登记腿 best-effort
   同族先例),随正本更新在 gain-chain.md §6 申报。
2. **随机单位采样**:rng 注入先例同骇客改件(`roll_hacker_mod` 形态)——报告函数
   新增 `rng: random.Random | None = None` 关键字参数,缺省 None = 实机未播种
   (采样是猜测,sim 传流键 = 世界真值,同一上报函数两副面孔);`random.choice`
   均匀二选一,披露键注释就地申报(均匀分布未实测,候校准)。
3. **rand 语义(按实码口径)**:授予体含采样(二选一)→ `rand=True`;`anchor_aware_write`
   的 rand 形参**优先于锚定状态**(`rand or not prep_anchored` 短路)——rand=True
   **全通道 logic_rand,锚定前后同通道**(采样纪律正参推论,gain-chain.md §5)。
   可验证性如实申报:授予无失配网辖,校准面 = `logic_rand_outcome` 行(模型选中
   单位 vs 观察实见单位的成对数据)+ 观察覆盖;**不存在**「锚定后失配网」验证路径。
4. **在册判定**:`normalize_invest_name(gs.active_env.value or '') == '欢愉契约'`
   (两侧归一,防形变);`active_env` 为空/其他环境 = 不授予。
5. **落位**:走 `gain_character` 固定时序(落位 → 回调 → 单级合成/溢出落位)——
   条件腿单位是 4 费角色,正常参与 3 合 1;溢出善后归策略面(链纪律不变)。
6. **临时闩退役(design 获得链批裁定「定谳后必须撤」的兑现)**:删除
   `cw_gain_chain.py` 的 `JOY_PROVISIONAL_KIND` 常量、`on_env_gained` 欢愉契约
   翻来源分支(值不变 write_logic_rand 两域 + 标记行)与返回值中的
   `provisional_mark` 效果名项;模块 docstring 失败安全/条件腿自述同步改写。
   撤除后 `on_env_gained` 欢愉契约仅走 chars_immediate 腿(银狼LV.999 入链)。
7. **weaken 兜底档退役(裁定③)**:剔除面全清单——①`cw_events.py`
   `classify_planner_leg` 关键词降级分支(「弱化/降低敌人」→ weaken)与
   `PLANNER_LEG_WEAKEN` 常量及腿型词表注释:含弱化词且装备名锚未命中的卡文改落
   **unknown**(留证行,失败显影方向——静默零记账变响亮申报);②`decide_planner`
   弱化档打分(55 分常数)**及其 docstring 三层定序自述**删除,打分两档制 =
   升费档 > 装备档(含弱化词未知名卡文按装备档回落);③`pick_planner.py` weaken
   派发分支删除(终态兜底零写保留,reason 改 `unrouted_leg_zero_write`,不再以
   weaken 命名)**+ 模块 docstring(:19-20)与函数 docstring(:67)的 weaken 字样
   同步**;④`cw_overlay_pick_action.py` 腿型注释同步。破解芯片碰撞治理(装备域锚
   先行)不受影响;退役判据 = 全仓 grep weaken 残留清零(sim 零消费已核)。

### 2.3 触发计数正确性(证据闩语义)

- 落地相门(`evidence == EVIDENCE_OVERLAY_CLOSED`)的正常保证者 = 「画面 op 生命
  周期内正常单次到达重入裁决出口」(载荷消费序:落地相执行前 `_confirm_pending`
  置 False、`_pending_leg`/`_pick_param` 清空);rider 随该门触发,**零新闩**;
- **失效通道如实申报**:落地相内部异常上抛(零吞错面)+ act 节点重试
  (`node_max_retry_times=5`)→ 载荷重建 → 落地相可二次执行 → rider 重复授予,
  走 logic_rand 静默自愈(观察覆盖),journal/合成被污染至下帧覆盖为止。既有腿
  同暴露此通道(升费腿有三态守卫、装备腿无);判读面以 `joy_conditional:` evidence
  前缀计数为候校准。不做实例级拒再入(新闩成本 > 异常路径收益,重试路径本身 =
  异常态);
- **弹窗选项族与 weaken 档退役(2026-09-21 用户问询澄清 + 裁定③)**:原文二分法 =
  「修改自身费用 / 获得妙妙小道具」;代码的 weaken 档 = 防御性兜底分类(选项卡文含
  「弱化/降低敌人」且装备名锚未命中时降级入桶),无原文依据、实机零出现 → **随本批
  整体退役**(§2.2-7)。rider 计数不受影响:落地相 = 弹窗出现即触发,与卡类无关;
- 发射相(evidence 缺省)不触发 rider(零写);
- rider 在腿型分派前执行,**调用点级 best-effort**(§2.2-1:try/except + 留证),
  授予失败不阻塞各腿;链内部零吞错语义不变。

### 2.4 已知边界(如实申报)

- **接管局**:active_env 接管局无写端(C 类不种,gs-opening-seed §2.2),条件腿
  在接管段不可达——授予不入账,真值归观察覆盖;
- **3★5 费狼尊接管后**:弹窗是否停止 = 游戏行为未实证;若停止则触发自然归零,
  模型无需特判(op 不报 = 不授予);
- **授予分布**:均匀二选一系原文「或」+ GiftGrant「随机获得」的建模口径,分布
  形态未实测;`logic_rand_outcome` 行自然校准(候选集仅两成员,判读面自证);
- **授予星级 1★ 先验**:原文未标,沿既定约定;观察覆盖纠偏;
- **落地相二次执行通道**:§2.3 失效通道(异常重试 → 重复授予,rand 静默自愈)——
  判读以 evidence 前缀计数校准。

### 2.5 行为变化申报

1. **条件腿授予的记账与校准面**:此前条件腿授予仅观察静默覆盖(零可见性);模型
   入库后授予以 `gain_character` 落账(placement/合成行,evidence `joy_conditional:*`,
   **全通道 logic_rand——rand=True 优先于锚定状态,锚定前后同通道**)。可验证性 =
   `logic_rand_outcome` 行(模型选中单位 vs 观察实见单位的成对校准数据)+ 观察覆盖;
   **无失配网辖**(采样面本义,非缺陷);
2. **bench 压力建模化**:高频触发下条件腿单位持续入 bench(可参与合成)——容器
   从「观察后知」变「触发即知」,策略器消费面获得真实时序;
3. **临时闩退役**:joy_contract_provisional 标记行与 bench/equips 翻来源行为消失;
   相关历史判读口径(以标记行识别欢愉契约局)改用 `joy_conditional` evidence 前缀;
4. **journal 增量**:每次头号玩家触发且欢愉契约在册 +2~4 行(落位/合成,随合成
   级数);欢愉契约在册时旧闩的 -3 行(两翻面+一标记)相抵。
5. **weaken 档退役申报(裁定③)**:①含弱化词且装备名未命中的卡文从「静默零记账」
   变「unknown 留证行」(更响亮,失败显影方向);②`decide_planner` 对此类卡文从
   55 分变装备档回落分——决策影响极小(升费卡通常 100 分占优,弱化卡文本无实机
   出现记录);③`report_action_pick_planner_param` 终态兜底 reason 更名
   `unrouted_leg_zero_write`。

### 2.6 测试面

- **通道语义(rand=True 恒 logic_rand)**:种子容器 + 欢愉契约在册 + 落地相上报 →
  授予落 bench source=logic_rand;`gs.prep_anchored = True` 直赋后同路径
  **source 仍 = logic_rand**(rand 形参优先于闩,与既有臂 3 锁同语义)——授予校准
  面断言 = 覆盖时落 `logic_rand_outcome` 行(零 observe_vs_logic_mismatch);
- **在册判定**:active_env 空/其他环境 → 零授予;欢愉契约 → 恰一次授予;
- **rng 注入**:同 seed 同单位;两候选均可达;
- **触发计数封闭清单**:落地相入口 `{equip, upgrade, unknown}` 各断言 rider 恰一次
  授予;发射相断言零授予;`leg_type=''` 直调落地相断言 rider 仍触发(兜底形态);
- **weaken 退役锁**:`classify_planner_leg('使后续节点【弱化】')` → `('unknown','')`
  (不再 weaken);含弱化词已知装备名(破解芯片)仍 → equip(碰撞治理不回退);
  `decide_planner` 对无名弱化卡文零弱化档分;`report_action_pick_planner_param`
  终态兜底 reason = `unrouted_leg_zero_write`;
- **时序锁**:授予走获得链固定时序(落位 → 回调 → 合成);
- **rider 失败语义**:gain_character 注入异常(桩)→ 腿型分派照常执行 + 
  `joy_conditional_grant_failed` 缺陷行;
- **撤闩**:`on_env_gained` 欢愉契约仅 immediate 腿(零翻面/零标记行);
  `JOY_PROVISIONAL_KIND` 全仓(src)零引用(grep 断言经由台账面/源码禁扫纪律的
  等价形式:对欢愉契约落地调用断言零 provisional 行);
- **既有测试随迁**:joy 临时闩断言唯一面 = `test_cw_yinlang_phase32.py`
  (:456-475 留证行 + :23-24 文件头注释)改写(判定「测试过时」纪律,commit
  message 注明);新增 rider 测试落 `test_cw_gain_chain.py`(链行为锁归并)或
  新文件,随批申报。

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
