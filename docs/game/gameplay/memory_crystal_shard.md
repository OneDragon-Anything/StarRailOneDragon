---
gameplay_name: 领取记忆残晶
app_id: memory_crystal_shard
last_updated: 2026-09-02
source: `application/memory_crystal_shard/` + `config/custom_combine_op/memory_crystal_shard.yml`
involves_screens: [大世界]
---

# 领取记忆残晶(memory_crystal_shard)

每日到翁法罗斯「永恒圣城」奥赫玛的**追忆残像**处互动,领取记忆残晶。bot 流程是**自定义组合指令**(`config/custom_combine_op/memory_crystal_shard.yml`),与 [trick_snack](misc_apps.md) / [buy_xianzhou_parcel](buy_xianzhou_parcel.md) 同款 CustomCombineOp 薄壳。

## 玩法机制

- 追忆残像:翁法罗斯地图上的可交互残像,互动后获得记忆残晶(具体刷新周期 / 残晶用途以游戏内说明为准,bot 侧未深究)。
- 领取动作:对残像按交互键 → 弹出领取画面 → 点击确认(画面中下部)。

## bot 流程(CustomCombineOp `memory_crystal_shard`)

`back_to_world_plus` → `transport`(翁法罗斯/「永恒圣城」奥赫玛/1/流憩大厅)→ `wait in_world 20` → `move`×2(2401,1420 → 2442,1433)→ `wait 3s` → `slow_move`×3((2456,1456)×2 → (2472,1471),重复同点慢走 = 绕障碍保持行进的录制走法)→ `interact world_single_line 开启追忆残像` → `wait 3s` → `click(960,980)` → `wait 3s` → `click(960,980)` → `back_to_world_plus`。

## 涉及画面

- **大世界**(已建档):传送落地 / 走位 / `移动交互-单行` 交互提示(「开启追忆残像」)。
- **领取画面**(未建档,待实拍):`click(960,980)` 点击的确认/领取画面——形态未归档(疑似通用领取/推进交互,与 trick_snack 路线2 的同坐标点击同族);连续点两次 = 走完两段领取流程。

## 备注 / 待查

- **无 fixture 归档**:追忆残像交互态 + 领取画面均未实拍(待每日首次领取时采集)。
- **click(960,980) 语义未实拍确认**:按路由时序(wait 3s ×2)推断为「领取确认 + 关闭」两段;若某日只弹一段,第二次点击落空无害(点空白)。
- **走位坐标**为 large_map_recorder 录制路线(ol 路径含重复同点 slow_move),地图改动时需重录。
- **重复运行行为未验证**:route 未标 allow_fail——若残像已领取(交互提示不出现),`interact` 会走到超时 FAIL;该 app 不在每日一条龙套件里,重复运行场景未实证,靠调度上每日一次规避。
