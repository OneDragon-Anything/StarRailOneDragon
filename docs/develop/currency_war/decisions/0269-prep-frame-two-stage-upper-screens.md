# ADR-0269: is_prep_like_frame 两段式(上层屏显式排除)

- **Status**: accepted
- **Date**: 2026-08-24

## Context

r330 帧态门 `cw_obs_core.is_prep_like_frame` 是白名单双屏判定(备战/开商店),
被 summon/bookcard/layout/star 四个停机/采集钩子共用。局72 12:57 伙伴误拖实锤:
**选择伙伴**等上层画面在场时,底层备战 UI(含 id_mark)往往仍可见 → 双屏判定
照样命中备战 → 钩子在中间态放行,上层画面被当备战帧误操作。

对抗裁决(决策时对抗)确认中间态形态:上层画面 = 盖在备战底层之上的
画面/弹窗(选择伙伴/祈愿试炼/事件类/详情类……),不是「非备战帧」的
对立屏——单靠备战双屏白名单结构性看不见它们。对抗报告同时证:上层判定
与备战判定同帧复用全图 OCR 缓存(`crop_first=False`),逐屏判定的增量
OCR 成本可忽略。

## Considered Options

1. **两段式(采纳)** —— 第一段逐屏遍历 `UPPER_SCREENS` 常量(22 个上层屏
   screen_name 全名,从 assets/game_data/screen_info yml 核对),任一命中 →
   False;全部未命中 → 第二段再判备战/开商店双屏。
2. **单次调用合并名单(拒绝,对抗审查轴①硬伤)** —— 把上层名单+备战屏
   合成一次 `get_match_screen_name` 调用:框架按注册序返**首个**命中,
   备战注册在前则上层帧照样先中备战 → 等于没改。必须显式两段。
3. **黑名单反向(上层屏判 not-in)与 1 同构** —— 实现即两段式第一段,
   无独立方案。
4. **上层屏只列「曾出事」的(选择伙伴一条)** —— 名单不全会留同类中间态
   缺口(下一个上层画面再误触再补);按画面注册表全量列,一次封类。

## Decision

- `cw_obs_core` 新增 `UPPER_SCREENS: tuple[str, ...]`(22 屏,按 screen_info
  screen_name 全名):选择伙伴/祈愿试炼/遭遇节点/投资策略/投资环境/盛会之星/
  位面过渡/积分奖励/简报/中断挑战弹窗/未达上限警告/提示-前台无角色/武装箱弹窗/
  商店刷新概率表/攻略码输入弹窗/备战-角色详情/星徽详情/星徽秘典弹窗/补给/
  难度确认/阵容编辑/模式选择。
- `is_prep_like_frame` 改两段:第一段**逐屏单调用** `get_match_screen_name`
  (`screen_name_list=[name]`),任一命中短路返回 False;第二段原双屏判定。
  best-effort 语义不变(异常 → False)。
- 消费点零改动:四个钩子(summon/bookcard/layout/star)与 cw_reconcile 均调
  同一函数,两段式自动生效。

## Consequences

- 上层画面在场的帧不再被判为 prep-like:钩子中间态误触(局72 伙伴误拖类)
  从判定层根治;真发现延迟至多一个上层画面周期(关闭后下一帧)。
- OCR 成本:上层判定复用全图 OCR 缓存,对抗报告证可忽略;逐屏判定引入的
  额外 CPU 为模板匹配(id_mark)量级。
- 新上层画面入 screen_info 后需同步进 `UPPER_SCREENS`(锁测试
  `test_upper_screens_names_registered` 防名单名手写错字静默失配,但不防
  「新增画面忘进名单」——新画面建档 checklist 自查)。
- 锁测试 `test_cw_adr0269_prep_two_stage.py`:三态(上层命中→False /
  上层未中+备战中→True / 全未中→False)+ 短路性 + 名单注册性。
