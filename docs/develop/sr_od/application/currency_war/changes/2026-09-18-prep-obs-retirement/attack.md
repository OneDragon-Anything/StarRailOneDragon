# 设计对抗报告

> 攻击对象：本迭代 design.md / details/cap-fix.md / details/obs-retirement.md / landing.md。
> 攻击规范：docs/develop/harness/iteration-design.md §7 三核。所有代码锚均已打开源码逐一核对。

## 发现清单

### 1. [critical] boxes/tomes 去向不可实施：容器无 `kind='tome'` 写点，bench kind 无法区分箱与典籍
**位置**：details/obs-retirement.md §阶段 3.5 字段去向表 `boxes`/`tomes` 行；design.md §2 终态表「宝箱/典籍占席」行。
**发现**：去向表称「识别 reader 保留，结果直写 bench（容器写端已有，cw_game_state.py:1450/1668/4759）」并「决策改读 bench kind 取首槽」。两点均不成立：
1. 所引三处锚（cw_game_state.py:1450/1668/4759）只写 `BenchSlot(kind='supply_box')`——全仓 grep `kind='tome'` 唯一命中是枚举声明本身（cw_game_state.py:548 的 `Literal[...]`），**tome kind 零实例化写点**，「容器写端已有」为虚假申报。
2. 读链把箱/典籍/书册卡全部并入 `is_item_slot=True`（cw_identity_obs.py:947、cw_screen_deploy.py:209），容器侧统一映射 `supply_box`（cw_game_state.py:1435 注释明文「箱/典籍/书册卡」一类）——**容器 bench kind 域无法区分 OpenBox 与 OpenTome 的触发物**，entry.py:458-461 的两臂分派（`obs.boxes` vs `obs.tomes`）没有等价的容器读法。批 5 删字段后 OpenTome 臂要么死、要么误开。
3. landing 3.5 的范围与完成判据均未列「boxes/tomes 决策读切换」这一行为变化，也无对应验收（判据只覆盖符号清零 grep）。
**依据**：cw_game_state.py:548/1435/1446-1451/1663-1668/4756-4759；cw_identity_obs.py:931/947；src/.../entry.py:458-461；全仓 ripgrep `kind='tome'` 仅 1 命中（枚举声明）。

### 2. [major] 字段消费面清单三处遗漏：批 5 删字段即断链或静默退化
**位置**：details/obs-retirement.md §阶段 3.2-2/3.2-3/3.4-3、§阶段 3.5 字段去向表。
**发现**：去向表与各阶段读端切换点漏了三个真实消费点：
1. **entry.py:674** `_owned_snap = list(getattr(obs, 'owned_equips', None) or [])`——②′ 工具消费发射位的 owned 快照源。3.2-3 只切了 entry.py:793 帧装配；landing 3.2 判据「grep 无 obs.owned_equips 消费」会红，但设计未回答这处怎么切（工具臂评估输入语义需设计裁定）。
2. **entry.py:492-495**——席自由分支的 `ClickSpheres` 发射同样消费 `obs.spheres`（`select_ore_clicks(obs.spheres, ...)`）；3.4-3 只列了 entry.py:507-509（探针分支）。漏切则批 4 容器域立好后决策仍读黑板旧值。
3. **cw_equip_wear_plan.py:182** `deployed = list(getattr(obs, 'deployed_chars', None) or [])`——M7 的 deployed 读点。批 1 只切 entry.py:607-608 与 wanted 臂；去向表称 `deployed_chars`「阶段 3.1 已切容器」，对 M7 这处不成立——批 5 删字段即断。
**依据**：entry.py:674/492-495/507-510/607-608；cw_equip_wear_plan.py:163-182 实读。

### 3. [major] `_ore_progress_sig` 是 spheres/bench_chars 的隐藏消费面，批 4/5 后静默退化
**位置**：details/obs-retirement.md §阶段 3.4-3、§阶段 3.5 字段去向表（`spheres`/`bench_chars` 行）。
**发现**：entry.py:170-186 `_ore_progress_sig` 经 `getattr(obs, 'bench_chars', None)` / `getattr(obs, 'spheres', None)` 取席计数与晶矿计数，构成席满让路门（ADR-0642）的成效重置签名。设计任何阶段均未提及其切换；批 5 删字段后 getattr 恒 None → 签名退化为「轮次单分量」，门成效重置逻辑静默失效（不崩溃、无报错）——正是本次事故同类的「静默失效」形态。
**依据**：entry.py:170-186（含 docstring「三分量全部 gs/obs 现成字段」）、496（`_prog_sig = _sphere_progress_sig(gs, obs)` 消费位）。

### 4. [major] 立新读口 `bench_free_of` 与既有 `bench_free_slots` 重复——第二源
**位置**：details/obs-retirement.md §阶段 3.3-1/3.3-2。
**发现**：kernel 已有同语义派生读口 `bench_free_slots(gs)`（cw_game_state.py:1085-1092，`slot_occupies` 口径天然把 unit/supply_box/tome 计入占席，正是设计要的「宝箱/典籍占席自动计入」）。设计未勘察该既有口，另立 `bench_free_of` 做同一计算，制造同族第二源（违反读口族单一源纪律，正本 BenchView docstring 明文「席空数派生……不入 schema」且已有实现）。且 3.3-2 的「读口 None 场景 → BENCH_CAPACITY」与新读口自身定义矛盾：`bench_slots_of` 恒返回定长表（未观察 = `[None]*9`），按 3.3-1 的「空槽计数」定义该读口永不返回 None，缺省分支不可达；既有 `bench_free_slots` 的 None（未观察）语义反而与 3.3-2 描述吻合——设计实际需要的就是既有口。
**依据**：cw_game_state.py:1080-1100（`slot_occupies`/`bench_free_slots`/`bench_is_full`）、4991-5000（`bench_slots_of` 恒定长表）。

### 5. [major] 「随实施取读口形态」= 未定稿措辞
**位置**：details/obs-retirement.md §阶段 3.3-3（前后排占用集现算）。
**发现**：原文「kernel 立读口或发射位内联现算，**随实施取读口形态**」——把结构决策留给实施者，直接违反 iteration-design.md §5 硬规则 2（实现者无需再设计；「看情况/待定/酌情」= 未定稿）。两种形态的单一源属性完全不同（读口入 kernel 读口族 vs 发射位内联第二份推导），不是等价写法。
**依据**：iteration-design.md §5 规则 2 与 §7 核一「试读」条；obs-retirement.md §阶段 3.3-3 原文。

### 6. [major] 投影腿退役后 `apply_prep_action_logic` 的调用位迁移未设计
**位置**：details/obs-retirement.md §阶段 3.5-3/3.5-2；landing 3.5 范围。
**发现**：3.5-3 删除 `_project_prep_obs` 的全部分支（名单/晶矿/装备/瞬态摘除），但 kernel 写口 `apply_prep_action_logic` 的现役调用点全部在**被删分支内部**（SellBench :996、DeployMove :1021、SellDeployed :1066、LevelUp :1081），黑板推进写点在 :1594-1595 与 :1758（`game_state_of(session).prep_obs = self._project_prep_obs(...)`）。删除后：① SellBench/DeployMove/SellDeployed/LevelUp 的容器逻辑态写由谁在哪调用——设计未答；② :1594/:1758 两个写点的替换形态（直调 kernel 写口？删除？）未申报；③ `_project_prep_obs` 函数本体存废未声明（词表外类型的 AssertionError 防线随函数存废）。实现者必须自行设计调用拓扑。
**依据**：cw_screen_prep.py:996/1021/1066/1081（kernel 写口调用位）、1093-1097（词表外 AssertionError）、1594-1595/1758（黑板推进写点）。

### 7. [major] cap-fix §1 锚错误：升级授权谓词消费位标成 entry.py，实际在 mandate.py
**位置**：details/cap-fix.md §方案-1（五类下游第 5 条）。
**发现**：原文「升级授权谓词（entry.py:1554/1568 消费 `len(frame.deployed)`/`frame.deployed`）」——entry.py 全文仅 1310 行，1554/1568 不存在；实际消费位是 mandate.py:1554（`predicates.arm1_existence(len(frame.deployed), ...)`）与 mandate.py:1583。行号恰好对上但文件张冠李戴，属于「依据标注与源码不符」的硬伤（按 §5 规则 1 该主张默认攻击目标，核对结果 = 锚伪）。
**依据**：entry.py 总行数 1310；mandate.py:1554/1583 实读。

### 8. [minor] bridge.py:174 锚偏移：决策入口实读点在 :179
**位置**：details/obs-retirement.md §阶段 3.5-2。
**发现**：`gs.prep_obs` 的决策入口读点实为 bridge.py:179（`obs = self.gs.prep_obs`）与 :180-184 的 None 抛错分支；:174 是 docstring 行。锚可用但应指向可执行行。
**依据**：bridge.py:168-184 实读。

### 9. [minor] landing 文件面两处不实/不实名
**位置**：landing.md §3.1 文件面、§3.4 文件面。
**发现**：① 3.1「kernel cw_game_state/cw_deploy_logic（仅当读口补缺，禁动谓词语义）」——条件式文件面（「仅当」），是否动文件留待实施者现场判断；② 3.4「kernel/ 逻辑态写口模块（ClickSpheres 分支）」未实名——`apply_prep_action_logic` 实际在 kernel/cw_game_state.py:2293（该文件已在同节列过），措辞暗示存在独立模块，误导文件面核对。另 3.2 的装备写端若按 obs-retirement 3.2-1「observe_full 的 occupied 采集产物由落黑板改 observe 上报容器」理解为改采集层，则 obs/cw_observe_full.py 不在 3.2 文件面——写端落点（采集层 vs director 装配点）表述含糊。
**依据**：cw_game_state.py:2293（`def apply_prep_action_logic`）；cw_screen_prep.py:635-637/737（现有装备写端在 director 装配点）。

### 10. [minor] cap-fix §6 等价性论证缺口：容器往返的派生字段差未论证
**位置**：details/cap-fix.md §方案-6（失读方向等价性论证）。
**发现**：§1 称「元素类型不变……下游零类型适配」，但 `bench_slots_of` 的元素经 `bench_slots_to_legacy` 重建：`faction` 不入容器（cw_game_state.py:1500-1502），出容器时按角色注册表重派生（原 SIFT BenchChar 的 faction 字段丢弃）；DeployMove 发射消费 `frame.bench[bi].faction`（mandate.py:2235）。§6 只核对失读/特效窗/未观察三态，未覆盖「同帧黑板 BenchChar vs 容器往返 BenchChar」的字段级等价（faction 重派生的取值域差异）。方向大概率等价（装配点同源），但主张无依据标注即默认攻击面。
**依据**：cw_game_state.py:1496-1530（`bench_slots_to_legacy` faction 重派生）；mandate.py:2228-2235。

### 11. [minor] 死码块的 obs 直读未申报处置，批 5 删字段后仅靠不可达性保护
**位置**：details/cap-fix.md §方案-5；details/obs-retirement.md §阶段 3.5。
**发现**：晶矿路径腾席死码块（entry.py:522-566）直读 `obs.spheres`（:524）、`obs.bench_chars`/`obs.deployed_chars`（:534-539），注释明文「禁删除……激活时恢复可达」。cap-fix 称「激活时随退役批换源」但未指明哪个阶段；3.5 字段删除后该块属性访问将 AttributeError——当前仅因 `SPHERE_OCCUPYING_COLORS` 空集而不可达。设计应显式申报：换源归属阶段（3.4 晶矿域立域时同步换 `obs.spheres` 读点最自然）或维持不可达保护的判据。
**依据**：entry.py:138/516-524/534-539 实读；cap-fix.md §方案-5 原文。

### 12. [minor] `state_gold_trusted`「消费面勘察为零」与在册消费指针矛盾
**位置**：details/obs-retirement.md §阶段 3.5 字段去向表 `state_gold_trusted` 行。
**发现**：去向表称「决策/策略消费面勘察为零（2026-09-18 全仓 grep）」。cw_observation.py:2180-2181 的 docstring 明文引导消费方「需要可信金判读的消费方走 gold_readable 位或备战观察链的 `prep_obs_frame.state_gold_trusted`」——代码消费为零属实，但该指针注释把此字段列为推荐读点；字段删除后此注释成僵尸指引，未列入清零/同步面（3.5-4 缓存清零清单亦不含）。
**依据**：cw_observation.py:2177-2184 实读。

## 结论

**需返工（未达定稿门槛）**。

- **核一·无前提**：实质发现 12 条。最重的是 #1（boxes/tomes 去向的容器写端申报为假、kind 域无法区分箱/典籍，批 5 按现设计落地即断 OpenTome/OpenBox 臂）与 #2/#3（消费面清单漏三处 + 一个静默退化的隐藏消费面——后者与本次事故的「静默失效」同形态，恰是本迭代声称要消灭的东西）。#5 是教科书式未定稿措辞。边界完整性（总纲 §1 vs 详设覆盖）结构上齐，但字段级去向表不可靠。
- **核二·规范遵循**：总纲三节齐、两份详设三部分齐、landing 七件齐、末阶段正本更新与清单齐、所引正本路径全部真实存在、无过程叙事措辞——结构合规。发现集中在依据标注质量：#7（锚文件张冠李戴）、#1（容器写端锚实证不符）、#8/#9（锚偏移/文件面不实名）。另 #9 的条件式文件面（「仅当读口补缺」）属判据可验收性瑕疵。
- **核三·治本核验**：归层「契约层」成立（名单双重身份 + 第三写端 + 无双写同步约束，事故链证据充分）；§2 读端切容器 + 写端收敛 kernel 是修根而非症状，方向正确。但 #4（无视既有 `bench_free_slots` 另立同语义第二读口）是「同族问题再犯一次」的实例——本迭代主线是消灭双源，方案里又造了一个双源；#3 的静默退化面说明「消费面勘察」这道工序本身没有对齐全仓 grep 的申报口径。

返工最小集：#1 必须重新设计（tome/box 的容器区分方案或改走保留识别直报）；#2/#3 补全消费面清单并逐点指派切换阶段；#4 改为复用 `bench_free_slots`（或论证弃用理由）；#5 定死形态；#6 补调用位拓扑；#7 修锚。其余 minor 随批修订。
