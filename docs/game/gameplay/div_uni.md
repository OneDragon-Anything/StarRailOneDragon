---
gameplay_name: 差分宇宙(千面英雄)
app_id: div_uni
last_updated: 2026-07-29
source: WebSearch 攻略 + `application/div_uni/` 代码(仅饰品提取 op)
bot_coverage: 部分覆盖(仅饰品提取;Roguelike 演算未实现)
involves_screens: [饰品提取, 战斗画面]
---

# 差分宇宙 / 千面英雄(div_uni)

2.3 版本常驻 Roguelike,模拟宇宙的迭代版。通关模拟宇宙第三世界解锁。三模式:**常规演算**(随机方程/祝福/首领)+ **周期演算**(每周首通额外拟合值)+ **位面饰品提取**。核心:方程(公式)+ 祝福 + 奇物构建。

## ⚠️ bot 覆盖范围(重要)

`application/div_uni/` **只实现了饰品提取** op(`ornamenet_extraction` + `choose_oe_file` + `choose_oe_support`),**差分宇宙 Roguelike 演算(常规/周期)未实现**:
- ✅ 饰品提取(见 [ornamenet_extraction](ornamenet_extraction.md))—— div_uni/operations 下唯一 op。
- ❌ 常规演算 / 周期演算 Roguelike(方程/祝福/奇物/位面推进)—— 无 app,bot 不跑。

> 即:bot 用 div_uni 目录的 op 支持「饰品提取」(消耗体力刷位面饰品),但差分宇宙本身的 Roguelike 玩法(打怪推进位面)未自动化。

## 玩法机制(攻略)

- **Roguelike**:方程(公式)+ 祝福 + 奇物构建,推进位面击败首领。
- **三模式**:
  - **常规演算**:初始方程/祝福/每位面首领随机。
  - **周期演算**:每周更新(奇物/方程/Boss),每周首通额外拟合值。
  - **位面饰品提取**:刷位面饰品(消耗体力/沉浸器)。
- **拟合值 + 拟合等级**:通关常规/周期演算获拟合值,升拟合等级领奖励。
- **千面英雄奖励**(V3.x+):共 ~3500 星琼(拟合等级 1080 + 稳态数组 1000 + 可能性画廊 1030 + 常规演算 390)。
- V4.0 洞察模式 + 拟合翻倍活动。

## bot 流程(仅饰品提取)

`application/div_uni/operations/`:
- `ChallengeOrnamentExtraction`:`choose_oe_file`(选套装存档)→ `choose_oe_support`(选支援)→ 挑战(战斗)。详见 [ornamenet_extraction](ornamenet_extraction.md)。
- 由 `trailblaze_power` app 调度(execute_plan)。

## 画面

- **饰品提取** `ornamenet_extraction` screen(见 [ornamenet_extraction](ornamenet_extraction.md))。
- 差分宇宙 Roguelike 演算画面(方程/祝福/奇物/位面)**未建模**(bot 未覆盖,无 screen_info)。

## 备注 / 待查

- **Roguelike 未覆盖**:差分宇宙常规/周期演算(方程/祝福/奇物/位面推进)bot 未实现 —— 若要覆盖需新建 app(参考 sim_universe 的 auto_run/move 模式)。
- **千面英雄版本演进**:V3.x 千面英雄 / V4.0 洞察模式,bot 跟进待评估。
- **饰品提取复用**:div_uni 目录的 op 是为「饰品提取」服务(差分宇宙下的饰品提取模式),非 Roguelike 本体。
- **拟合等级奖励**:bot 不领(未覆盖演算),用户手动。

## 参考来源

- [差分宇宙千面英雄攻略工具(官方)](https://sr.mihoyo.com/news/154494)
- [百度百科 差分宇宙](https://baike.baidu.com/item/差分宇宙/67322812)
- [萌娘百科 差分宇宙](https://zh.moegirl.org.cn/差分宇宙)
- [BWiki 差分宇宙](https://wiki.biligame.com/sr/差分宇宙)
