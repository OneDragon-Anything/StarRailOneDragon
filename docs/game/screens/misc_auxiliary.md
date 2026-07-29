---
gameplay_name: 兜底/辅助画面(参照 ZZZ 补 SR 漏点)
last_updated: 2026-07-29
source: 对比 ZZZ `docs/game/screens/`(loading/对话/兑换码/警告/快捷手册)+ SR screen_info(多无独立,靠 common + 结构)
---

# 兜底/辅助画面(参照绝区零补 SR 漏点)

对比 ZZZ docs/game/screens/(~33 画面 doc),SR 漏建以下通用 / 兜底画面(screen_info 多无独立,靠 `common` + 结构识别)。这些是 bot 识别的盲区(无固定文字特征),按 screen-onboarding「兜底画面」方法处理。

## loading(加载画面)

- 黑屏 + 进度条 / lore tip(游戏 lore 文字)。
- 出现:各传送 / 进玩法 / 切场景 / 启动。
- 兜底识别:无固定文字,靠结构(黑屏 + 进度 / tip)。
- SR 覆盖:`guide` 的「等待加载-XX」area(花萼/饰品/历战/模拟宇宙传送后加载)部分覆盖;通用 loading 未独立建。
- 待实拍 + 可能建模(screen_info 加 `loading` screen)。

## 对话(NPC 对话)

- 下方对话框 + NPC 名 + 选项。
- 出现:大世界 interact NPC / 剧情对话 / 任务对话。
- 兜底识别:对话框结构(NPC 名不固定,无固定文字)。
- SR 覆盖:`common`(对话框-确认)部分覆盖;通用对话未独立建。
- 待实拍 + 建模(对话 screen,含选项 / 确认)。

## 兑换码输入

- 兑换码输入框 + 确认 / 兑换。
- 出现:设置 / 活动兑换码入口。
- SR 无 screen_info。
- 待实拍 + 建模(兑换码输入流程,输入框 + 确认 + 兑换结果)。

## 警告弹窗(游戏前详阅)

- 启动时健康 / 防沉迷警告(「游戏前详阅」)。
- SR 无 screen_info(`enter_game` 覆盖登录态,警告未建)。
- 待实拍(启动时一闪,手动截)。

## 快捷手册(日常)

- 日常玩法快捷入口(一键日常集合)。
- ZZZ 有(`快捷手册` / `快捷手册-日常`)。SR 对应?:`guide` 的「行动摘要」TAB 可能是类似功能(日常汇总),待确认。
- 待实拍 + 确认是否 SR 有对应玩法。

## 备注 / 待查

- 这些是 SR 通用 / 兜底画面,screen_info 多无独立(靠 `common` + 结构),bot 识别靠兜底方法(screen-onboarding「兜底画面」:loading / 对话 无固定文字特征但结构固定)。
- **待实拍 + 必要时建模**:loading / 对话 可补 screen_info(结构锚点);兑换码 / 警告 / 快捷手册 视 bot 覆盖需求。
- **ZZZ 参照**:ZZZ docs/game/screens/ 对 loading/对话/兑换码/警告/快捷手册 各有独立 doc,SR 可后续细化(每画面独立 doc + 实拍归档)。
- **common screen**:`common`(通用画面:左上角标题 + 对话框-确认)是这些兜底画面的部分基础,可扩展。
