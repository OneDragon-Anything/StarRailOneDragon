# 货币战争 COMP_LIBRARY · 起步阵容 roster(V4.4,2026-08-03)

> **起步 roster**,~8 套,覆盖易/中/难成型 + 各类机制(含 debuff=buff 的燃血)。
> **依据**:strategy_research.md §10(meta 阵容横评)+ cw_data/characters.md / factions.md(米游社 V4.4)。
> **⚠️ 全部待实玩校准**(用户:玩的次数不多,实玩增强了解)。`strength`/`form_difficulty`/`core_chars`/`form_tiers` 是起步估值,实机/replay 迭代。
> **`level_plan`(成型路线)留空** —— 按用户选的 B,等建库时填(每个 comp 的等级→该做什么)。
> **邪道非必需**(用户 2026-08-03):不标"邪道 A8 专项",物质分解液/反甲等只是可选强阵容/强装之一。

## 字段说明
- `factions`:核心阵营组合(查 cw_data/factions.md 31 羁绊)
- `core_chars`:核心角色(查 cw_data/characters.md 74 角色;起步估值待精确)
- `form_tiers`:成型 tier 目标(几人激活)
- `strength`:综合强度 S/A/B(版本强度,实玩校准)
- `form_difficulty`:成型难度 easy/medium/hard(用户强调关键维度:核心牌费用/典型成型轮次/转型成本)
- `key_equips`:关键装备(详 cw_data/equipment.md)
- `boss_weakness` / `affix_synergy`:克这阵容的 boss / **利这阵容的词缀**(MECHANIC_SYNERGIES,debuff=buff)
- `shared_chars`:与其他 comp 共享的核心(转型可复用)
- `transition_chars`:早期打工牌(后期卖)

## 起步 roster

### 1. 列车同行(姬子·启行)— easy / A
- factions: 列车同行
- core_chars: 姬子·启行(3费,V4.4 核心)+ 列车同行成员(待精确)
- form_tiers: {列车同行: 4}(4 人成型即稳)
- strength: A(research §10:4.4 meta 顶层,4 人成型稳定通关 A850)
- form_difficulty: **easy**(4 人成型、3 费核心,成型快)
- key_equips: 护盾反震类(research:一动反伤 140 亿)
- boss_weakness: (无明显,稳)
- shared_chars: 三月七(护盾,列车同行)
- 备注:护盾反震流,V4.4 最稳起步推荐。

### 2. 巡击青雀(仙舟 + 追击,神君海伤)— medium / A
- factions: 仙舟 + 追击
- core_chars: 青雀 + 知更鸟 + 仙舟追击 core(待精确)
- form_tiers: {仙舟: 7, 追击: 5}(神君层数)
- strength: A(research:最稳无弱点,神君海伤)
- form_difficulty: medium(仙舟 7 层需一定轮次,但低中费)
- boss_weakness: (无明显,稳)
- shared_chars: 知更鸟(盛会之星,多 comp 共用)

### 3. 昼神阿雅轮椅(昼之半神)— hard / S
- factions: 昼之半神
- core_chars: 阿格莱雅(1费,攻击力挂钩速度)+ 昼神成员(风堇/那刻夏/昔涟)
- form_tiers: {昼之半神: 6}
- strength: S(强,成型碾压)
- form_difficulty: **hard**(需 2 反重力皮靴 + 3 昼神,鞋+人都难凑)
- key_equips: **反重力皮靴 ×2**(速度,"找鞋战争")
- boss_weakness: **电视机(禁速)** —— MECHANIC_COUNTERS:禁速克速度依赖(详 10)
- shared_chars: 风堇(昼神+燃血,与万敌流共用)

### 4. 击破流萤(击破主 C)— medium-hard / A
- factions: 击破(星核猎手击破线)
- core_chars: 流萤(5费,击破主 C)
- form_tiers: {击破: 待定}
- strength: A
- form_difficulty: medium-hard(5 费核心,后期找)
- boss_weakness: (待实玩)

### 5. 贝洛伯格召唤(布洛妮娅)— medium / A
- factions: 贝洛伯格(+ 燃血独立:布洛妮娅大守护者)
- core_chars: 布洛妮娅(召唤可可利亚)+ 贝洛伯格成员
- form_tiers: {贝洛伯格: 待定}
- strength: A(召唤稳定输出)
- form_difficulty: medium
- shared_chars: 布洛妮娅(燃血,与万敌流共用)

### 6. 万敌单 C(夜之半神 + 燃血)— medium / A 【debuff=buff 典型】
- factions: 夜之半神 + 燃血
- core_chars: 万敌(夜之半神/燃血,前后台输出)+ 长夜月/遐蝶
- form_tiers: {夜之半神: 待定, 燃血: 待定}
- strength: A(research:中期区后期登神)
- form_difficulty: medium
- **affix_synergy: 正当防卫(反伤)/AoE/持续伤害 → 利燃血**(MECHANIC_SYNERGIES:反伤让燃血掉血 → 角斗场记录 → 伤害更高,详 10 万敌例)。**正当防卫局升权这套。**
- key_equips: 燃血星徽
- shared_chars: 风堇/长夜月(燃血,多 comp 共用)

### 7. DOT 队(持续伤害 + 减益)— easy / B
- factions: 持续伤害 + 减益
- core_chars: 卡芙卡(2费)/黄泉/桑博(低费 DoT)
- form_tiers: {持续伤害: 待定, 减益: 待定}
- strength: B(research:下限极高/上限低,稳但不爆)
- form_difficulty: **easy**(低费成型快,前期过渡强)
- boss_weakness: 净化身心环境(走 DoT 避,config dot_punish_envs)
- 备注:前期/低难保血利器;高难上限不足。

### 8. 反甲白厄(毁灭反甲)— medium-hard / A
- factions: 毁灭(+ 反甲装备线)
- core_chars: 白厄(毁灭)+ 反甲装备
- form_tiers: {毁灭: 待定}
- strength: A(research:A8 打得爽)
- form_difficulty: medium-hard(反甲装备成型)
- boss_weakness: **琥珀王/死龙/酒杯怪(反伤/高防)** —— MECHANIC_COUNTERS:克高频低单次(详 10)
- 备注:靠阵型(坦克前排吃伤触发反伤,P1-3 formation)。

## 维护
- **版本**:V4.4;版本更新 → 重抓 cw_data → 核对 factions/characters 变化 → 更新本 roster strength/core_chars/form_difficulty(research + 实玩)。
- **level_plan 填充**(阶段 2-4 建 COMP_LIBRARY 时):每 comp 的等级→动作(level_up/roll 找几费/stable)+ star_goals。
- **运行时**:select_comp 每回合跑,按 comp_score(多维:progress + boss_fit + env_fit + mechanics_fit 双向 + strength − weakness)+ 用户 4 优先轴 steer,选 target;同时备选 top-N(optionality)。
- **实玩校准优先**:strength/form_difficulty/core_chars 全是起步估值,replay + 实玩迭代(用户:玩的次数不多,边玩边校)。

## meta 校准(米游社 A8 流派简评 71465721,V3.7-3.8 基线 + V4.4 增补)

> 来源:[article/71465721](https://www.miyoushe.com/sr/article/71465721)(A8 流派简评,791 赞)🟡。**V3.7-3.8 基线**,流派结构 + 核心装备跨版本稳;具体强度 V4.4 有变(见下"V4.4 权威评级")。给 COMP_LIBRARY strength/form_difficulty 校准用。

### ⭐ V4.4 权威评级(2026-08-03,🟢 当前 meta,优先级最高)

> 来源:[article/76807134](https://www.miyoushe.com/sr/article/76807134) 4.4 攻略合集贴(07-19~07-31,维护到 4.7)。评级只考虑**试用 + 0命 C**(刚需2命不评)→ 对 bot(全池、无练度依赖)适配性好。**此表推翻 V3.8 基线**(阿雅 V3.8 最轮椅 → V4.4 降 B)。

| 评级 | 阵容 | COMP_LIBRARY 对应 | 校准动作 |
|---|---|---|---|
| **S(真神,试用爽玩)** | **姬子**(列车同行+反震+杨叔c) | 列车同行 | A→**S**;+ 反震/杨叔c 机制 |
| **S** | **红A / Archer 95**(命运圣杯) | (缺) | **新增** 命运圣杯红A comp,S |
| **A(强势)** | 绯英(欢愉)、希儿、**黄泉(减益)**、波提欧(击破)、饮月(龙丹)、双王 | 击破流萤 / DOT队 | 击破 B→**A**;减益(黄泉)单列 A |
| **B(一般,试用难)** | 狼尊、**阿雅**、追击、银枝、dot、**万敌** | 昼神阿雅/巡击青雀/万敌/DOT | 阿雅 S→**B**、万敌 A→**B**、追击青雀 A→**B** |

**关键认知(V4.4 vs V3.8 推翻点)**:
- **阿雅鞋修 V3.8 最轮椅 → V4.4 降 B**(可能因鞋修需反重力皮靴×2 + 速度投资,试用/0命下难成型;有装备仍强但不再顶层)。
- **姬子·启行 = V4.4 唯一 S 级轮椅之一**(列车同行 + 反震 + 杨叔c 多机制),是起步首选。
- **红A(Archer,命运圣杯)是新 S 级**(V4.4 联动),原 COMP_LIBRARY 缺,需补。
- 击破(V4.4 波提欧 A)、减益(黄泉 A)比 V3.7 加强。

### 三大主流派 + 核心装备(跨版本稳,V3.8 基线)
1. **鞋修流(V3.8 最主流/最轮椅)**:反重力皮靴 ×2 叠加速 + **光速螺旋桨**(3 昼之半神获得)。
   - **超速阿格莱雅 = 「目前最轮椅打法」(既通用又易成型还稳)** → COMP_LIBRARY 昼神阿雅 form_difficulty 应 **medium**(非 hard),strength S ✓。key_equips:反重力皮靴×2 + **光速螺旋桨**(当前缺,待补)。
   - 神速那刻夏(配大黑塔,左脚踩右脚):比阿雅难成型。
   - 跑断腿桑博(前期过渡权威,位面3乏力)。
2. **反击流(大数字)**:利用高难怪多动 + 受击反馈。
   - 万敌单C(前期坐牢需 1 命;V4.4 万敌 2→1费 + 燃血角斗场上调 → 比V3.7强):核心装备 热血沸腾拳/高周波电锯/火力风暴潮。
   - 反甲卡厄斯兰那(白厄):**怕红绿灯 + 酒杯怪**,需**以牙还牙甲 ×3**,反重力皮靴(三月七/丹恒腾荒)。→ COMP_LIBRARY 反甲白厄 boss_weakness 应加 **红绿灯**,key_equips 加 **以牙还牙甲×3**。
   - 铲平杰帕德(受击砸地反击,需群攻/列车同行星徽)。
3. **星徽羁绊流**:凑羁绊(狼狩/击破/仙舟/减益/群攻/银河学者/能量/追击/持续伤害/燃血)。
   - **仙舟**:3仙舟应付前两关,5稳过位面1,7稳过位面2,8-9通位面3。神君靠仙舟队员行动叠层。→ 仙舟可作为独立 comp(当前并入巡击青雀)。
   - **击破**:V3.7「A7稳过 A8稳不过」,V3.8 加强但需姬子+忘归人。6击破解锁四玩法(流萤/波提欧/姬子/10击破)。→ COMP_LIBRARY 击破流萤 strength 应 **B**(A8 乏力,非 A)。**⚠️ 此 V3.8 B 评估已被 V4.4 推翻**:V4.4 波提欧击破升 **A**(见上「V4.4 权威评级」表;V4.4 优先于 V3.8 基线)。
   - **追击**:纯后期,需 9 追击才超飞霄;前期走狼狩过渡。→ form_difficulty hard。
   - **燃血**:V3.7「羁绊伤害根本不行」(无遐蝶长夜月);**V4.4 加强**(角斗场上调 + 万敌1费)→ V4.4 比V3.7强。

### 跨流派核心装备(必出/强力,COMP_LIBRARY key_equips 用)
- **反重力皮靴 ×2**(鞋修核心:阿雅/桑博/那刻夏/彦卿)
- **光速螺旋桨**(3昼之半神,鞋修核心)
- **高周波电锯 + 火力风暴潮**(输出核心:万敌/杰帕德/黄泉/飞霄/那刻夏)
- **以牙还牙甲 ×3**(反甲流:白厄/杰帕德)
- **物质分解液**(桑博/青雀)、**追击星徽**(青雀无穷动)、**热血沸腾拳**(万敌)

### V4.4 当前 meta(2026-08 增补)
- **姬子·启行 = V4.4 新晋轮椅**([76726482](https://www.miyoushe.com/sr/article/76726482) 领航员姬子 / [76824096](https://www.miyoushe.com/sr/article/76824096) 姬子挂机流稳定 A850):赋予开拓同行角色助战技,高频伤害。→ COMP_LIBRARY 列车同行(姬子·启行)strength A/easy ✓ 印证,是 V4.4 顶层起步推荐。
- 命运圣杯羁绊(V4.4 新):远坂凛/吉尔伽美什/Saber/Archer,2/3/4/5 分级,圣杯祈愿给命运改件。

### S 级 comp 运营要点(逐角色攻略,V4.4)

**列车同行·姬子·启行**(S,bot 默认首选;[76824096](https://www.miyoushe.com/sr/article/76824096) A850 挂机流):
- 核心:姬子·启行(3费)+ 绑定三月七(助战技给20%生命护盾 + 列车攻击前台40%护盾 + 光轨反伤)。
- 初期过渡(位面1):2DOT+2减益(卡芙卡+椒丘+千冶·刃)/ 2DOT+2列车(艾丝妲+椒丘+三月七+饮月)/ 2DOT+3仙舟。拿到4列车直接用。
- 位面1 补给优先:**姬子·启行 > 折叠小刀 > 轮回鞋**。
- 中期(位面2):凑齐 **4 列车同行**(赢一半)。
- 成型(8人口):前台 姬子·启行+花火+瓦尔特+记忆主;后台 三月七+刻律德菈+千冶·刃+符玄/缇宝(9人口+缇宝+符玄)。
- **核心装备(输出装,非反甲!)**:冷笑话引擎(50%幸运一击)、火力风暴潮(攻击叠8%强度)、高周波电锯(40%幸运一击30%强度)、掩体生成枪(前台30%生命护盾)。
- 特点:**全程自动战斗、不凹开局、适应任何负面环境** → 完美 bot 默认 comp。
- 印证:7级3费=40%刷新概率、3费约14种(与 D牌期望表 v=13 略异,待核)。

**命运圣杯·红A**(S;[76924524](https://www.miyoushe.com/sr/article/76924524)):
- 核心:红A/Archer(高倍率九五核心,每行动6次给小队随机3角色发装备)+ 远坂凛(+150%攻击+战技点)。
- 阵容:红A(双电锯+风暴潮)+ 前台 凛+杨叔+主角 + 4战技点(花火/刻律)+ 刃(2减益)+ 缇宝/符玄/鸟(知更鸟加速)。
- **关键装备**:高周波电锯 ×2 + 火力风暴潮(通用 find 装;命运改件由圣杯祈愿自动给)。
- 运营:2-7到3-2 上9 找1张Archer+杨叔锁血;3-5 上10 找2星Archer 过遭遇4。
- 转支线:拿到圣杯转 → 5圣杯任务冲3星5费。
- 2星Archer最后一箭倍率3450%(10战技点)。
- **V4.4 攻略合集贴**([76807134](https://www.miyoushe.com/sr/article/76807134)):作者 V4.4 全攻略索引(黄泉76826405/龙丹76987716/波提欧76852576/开局77037489/红A76924524/狼尊76832783/d牌期望表77074467/姬子启行77151995…)。逐角色深挖 COMP_LIBRARY core_chars/key_equips 时按此入口。
  - 评级只考虑试用 + 0命 C(刚需2命不评)→ 对 bot(无练度依赖的 auto-chess)适配性好。

