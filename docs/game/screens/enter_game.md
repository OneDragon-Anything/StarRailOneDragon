---
screen_name: 进入游戏
screen_id: enter_game
appears_in: [登录流程]
last_updated: 2026-07-29
source_image: 待实拍（open_game 自动登录到大世界,登录画面一闪未截；归档 screens/进入游戏/*.webp）
pc_alt: false
multi_screens: [enter_game, enter_game_choose_account, enter_game_logout_dialog]
---

# 进入游戏(enter_game)

游戏启动登录界面。账号密码登录 / 选账号 / 开始游戏 / 登出。**不锁光标**(`pc_alt=false`)。3 个 screen 子态。

## 何时出现 + 状态流转

- **入口**:启动游戏(`open_game`)→ 进入游戏画面(账号输入态)。
- **流转**(动作 → 下一态):
  - 输入账号 + 密码 + 同意 → 「进入游戏」/「开始游戏」→ `enter_game_choose_account`(选账号)→ 选账号 → 加载 → 大世界。
  - 已登录(记住)→「点击进入」/「开始游戏」→ 选账号 → 大世界。
  - 「登出」→ `enter_game_logout_dialog`(退出登陆弹窗)→ 退出 / 退出并保留记录 → 回账号输入态。

## 识别特征(稳定锚点)

- **文本-开始游戏**(text "开始游戏")、**文本-点击进入**(text "点击进入"):`enter_game` 已登录态锚点。
- **国服-账号密码**(text "账号密码")、**国服-账号密码进入游戏**(text "进入游戏"):账号输入态锚点。
- **标题-退出登录**(`enter_game_logout_dialog`):登出弹窗锚点。
- `pc_alt=false`。
- 易变:账号手机号 / 邮箱、版本号、公告。

## 可交互元素(screen_info area)

**enter_game(进入游戏,14 area)**:
| area | 说明 |
|---|---|
| 国服-账号输入区域 / 密码输入区域(text 输入手机号/邮箱、输入密码) | 账号密码输入 |
| 国服-同意按钮 / 文本-同意-旧 | 同意协议 |
| 国服-账号密码 / 国服-账号密码进入游戏 | 账号密码登录 tab + 进入游戏 |
| 文本-开始游戏 / 文本-点击进入 | 已登录态开始 |
| 按钮-登出 / 按钮-登出确定 | 登出 |

**enter_game_choose_account(选择账号,2 area)**:按钮-进入游戏、按钮-登陆其他账号。

**enter_game_logout_dialog(退出登陆,3 area)**:标题-退出登录、按钮-退出并保留登陆记录、按钮-退出。

## 识别快照(待实拍)

- **未实拍**:`open_game(enter=True)` 自动登录到大世界,登录画面一闪而过未截。识别快照(匹配画面 + area + OCR + vision)待现场手动分解登录步骤实拍归档(`screens/进入游戏/账号输入态.webp` 等)。
- 按 screen_info + enter_game op 代码记入流转(上),area 全集见各 yml。

## 备注 / 待查
- **待实拍 vision**:登录画面未截,vision(账号输入框 / 同意勾选 / 开始游戏按钮布局)待 `open_game(enter=False)` 停在登录态实拍,或手动分解登录步骤截图。
- **国服 / 国际服差异**:`enter_game` 的 area 多带「国服-」前缀(账号密码登录),国际服可能不同(账号体系不同)—— 待核对。
- **多子态**:enter_game 含账号输入态 / 已登录开始态(点击进入/开始游戏)→ 实拍各态 + choose_account / logout_dialog 各一张。
- **open_game 自动登录**:bot 的 `OpenAndEnterGame` op 自动处理登录(输入账号 / 同意 / 进游戏),不停留中间态 —— 抓登录中间态要 `enter=False` 停在 ready 态或手动分解(skill「截图获取」)。
