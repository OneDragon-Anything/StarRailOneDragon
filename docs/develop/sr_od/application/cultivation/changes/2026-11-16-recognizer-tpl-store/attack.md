# recognizer-tpl-store 设计对抗报告

> 三核并攻（核一无前提 / 核二规范遵循 / 核三治本），各自独立读码实证。本文件为对抗过程区，
> `changes/` 外禁引。每攻击点标注修订去向（design/landing §节）；全部攻击点已吸收进修订稿。

## 总结论

三核一致判定：方向与骨架成立（归层、store 化、范围豁免、零消费方主张、符号锚点经全仓 grep 复验相符），
需修订后定稿——无推翻性发现。攻击点合计 18 条：高 1 / 中 5 / 低 12。

## 核一·无前提攻击（含实现者试读）

试读结论：三阶段凭 design+landing 能开工；符号/行号/调用点/零消费方主张逐项实证相符。

### A1 `superimpose_tpls` 构建语义写错：「归一 24×24 灰度」与现状不符，照做即行为变化 [高] → 已修 design §2.2
- 现状函数体只做 RGB→灰度、保留盘上原始 26×26 尺寸，无运行时缩放（light_cone_list_recognizer.py:459-473；
  资产实测 shape=(26,26,3)；:447 注释「归一 26×26 紧圆窗灰度裁片」）。design 映射表写「归一 24×24」会改 TM 分数分布、
  违背零变化承诺。伴生：`_SUPERIMPOSE_NORM_SIZE = (24,24)`（:455）为全仓零引用死常量，迁/删未提及。
- 修订：映射表数据源改「原函数体迁入，无运行时缩放」；死常量随迁删除并进 3.1 grep 归零清单。

### A2 「一行委托」名单过宽，与映射表自相矛盾 [中] → 已修 design §2.4
- `_tm_template_lists`/`_tm_templates_all_lists`/`_tm_templates_for_pos` 是不读 global 的组合 helper
  （light:391-396、relic:375-381/384-402），无对应 store 视图。修订：委托名单收窄为 `_tm_templates_all`（两域）与
  `_superimpose_templates`（光锥）；三个 helper 函数体/签名均不动。

### A3 `sr_relic_sets.py:16` docstring 指向退役模块，不在文件面/清单/grep 判据内 [中] → 已修 landing 3.2
- 「识别模板规范库见 config/relic_templates.py」持久指针悬空。修订：3.2 范围与文件面补该文件（仅此注释行改指 store）。

### A4 SrContext property 构造实参未落纸；loader 实例身份变化可观测但无害，应写明 [低] → 已修 design §2.3
- property 体 = `LightConeTplStore(self.template_loader)`；原 iter 用临时 `TemplateLoader()`，收归后卡面库
  TemplateInfo 进入共享 loader 字典（无功能消费方枚举该字典，驻留面等价）。修订：§2.3/§2.5 落纸。

### A5 调用点清单漏 3 处；「recognize 内各 1 处」对遗器不准（在 `_recognize`:270） [低] → 已修 design §2.4
### A6 §2.3 依据指针失真：`init_controller` 方法体内无 import；真先例 = `__init__` 体内（221/225）与
`currency_war_strategy_plugin_dirs` cached_property 体内 [低] → 已修 design §2.3
### A7 生产侧现建实例 7 处非 6 处（5 文件） [低] → 已修 design §2.8

## 核二·规范遵循

### A1 landing 文件面测试仓路径缺 `operations/` 段（3.1/3.2），design↔landing 失同步 [中] → 已修 landing
- 实测两域识别器测试在 `.../<域>/operations/` 下；新 store 测试路径（域根、无 operations）是对的，勿一并改。
- 规范出处：iteration-design.md §5-4（文件面真实路径）、§3.1（文件面 = 派工边界）。

### A2 §2.3 依据先例锚错误（同核一 A6） [中] → 已修 design §2.3
### A3 调用点清单漏 3 处（同核一 A5） [低] → 已修 design §2.4
### A4 取舍③计数失准（同核一 A7） [低] → 已修 design §2.8
### A5 §2.7 既有失败清单无依据标注、「id_mark 32 条」无出处且与文件粒度判据不齐 [低] → 已修 design §2.7
### A6 删除测试文件未挂「src 指针对账」工序（sr-od-test/README「删除测试的工序」为强制级） [低] → 已修 landing 首节

### 专项裁定：「2026-11-16 排查会话」措辞不构成违规
- 非 §5-3 过程叙事（卡点措辞「本轮/修订后/已改」类，design 无）；是 §2.1 明文要求的「用户裁定指针」
  （无 ADR 时日期+会话为唯一可行指针，裁定内容已全文内联，指针死亡不损自足）。
- 残留建议：§1.1/§2.5 的日期戳对可核性零贡献（git 命令/口径清单已是持久出处），可删 → 已删。

## 核三·治本核验

### A1 归层成立，但「store 化消灭传参错位 bug 类别」不成立 [低] → 已修 design §1.2
- 修掉传参错位的是测试重写（§2.6）；store 化消灭的是其掩盖机制（口径依赖）与 loose 动态属性静默兼容
  （`getattr(ctx, 'relic_templates', None)`）。修订：§1.2 补一句区分，防读者记混两类修复。

### A2 ctx 级 first-caller-wins 依然存在，「测试隔离 = 新建实例」与 §2.6 有内部张力 [中] → 已修 design §2.2
- owner 基准/pos 子集走 session 共享 store，非新建实例；无害性依据（视图 = 静态资产 + mys 常量表派生、
  构建与 ctx 实例无关）已核实成立但未落纸。残余边界：构建期 bug 仍只由首触测试暴露，可接受，应写明。
- 修订：§2.2 构建纪律改分层表述（隔离两档 + 内容确定性依据 + 残余边界）。

### A3 危险变体恰好只有这 9 处，无需升格；其余同族落豁免判据，§1.3 未列全 [低] → 已修 design §1.3
- 全 src grep 实证：CW 域 `_COST_DIGIT_TEMPLATES`/`_ENV_PORTAL_EFFECTS` 不收 ctx、内容确定性派生，落豁免判据；
  one_dragon 键控/确定性 memo 族（yaml_operator cached_yaml_data 带 invalidate、i18、lru_cache 族）属公共包治理，
  另批走公共包同步流程，非本项目 changes/ 范围。

### A4 验收口径：双口径 diff 是间接代理；基线条款两处失真风险 [中] → 已修 design §2.7 + landing 3.1/3.3
- ①补「重写测试单跑（冷路径）必过」——结构保证，直接钉死本案回归形态；②基线改「3.1 开工前、当次 HEAD
  双口径各跑一次的新鲜失败清单（留档）」，design 冻结清单仅作漂移参考（防并行批在飞导致清单漂移误判）。

### A5 SIFT 迁 store 与裁定②不冲突（判读：裁定含义 = 不落实例/类状态，模块归属随单一源落 store 模块）；
「生产行为零变化」需申报 loader 实例身份统一这一处良性偏差 [低] → 已修 design §2.2/§2.5/§2.8

## 附：三核确认无误项（抽样锚点全命中）

- 全局行号（light 346/456/634-636、relic 329/606-608）、`match_owner` 709/677、TM 常量族（100/106、90/96、绳 92/96）、
  slow_marks.txt:53-54、`_fake_ctx` 两处现状（光锥有 template_loader 字段、遗器裸靠动态属性副作用）；
- 零消费方主张（iter_*/dataclass/SUB_DIR/`relic_template_id` 全仓仅识别器 + config 自身）、git 考古
  （fb0c1bb6c 与 4000456f 同批，时间戳差 1 秒）；正本更新清单 7 条目标全部真实存在且确指退役模块；
- 四节齐/七件齐/进度只住 README/判据可验证/无「看情况/待定」表述/`SrTestContext extends SrContext`（薄委托判据成立）。
