# 行迹侧接入：周本按名包装 + 花萼共用口径（详设）

## 问题与约束
- 边界：本篇只管行迹侧（agent 层）怎么消费周本核心与花萼机制；核心 op 本体见 weekly-core.md。总纲接口契约：核心纯参数（support 由本层翻译 'none'→None）；配队解析在带 mission 语义的层；`team_num=0` = 沿用当前编队。
- 消费场景：行迹升级 op 材料判停（`MATERIAL_CAPPED`）后，调用方（agent）获用户授权做手动刷补料——周本材料走周本包装 op，花萼材料走既有 `FarmLightConeMaterialOp` 委托链。行迹 op 本体不内嵌刷取导航（负责人裁定：手动刷出 op 边界）。

## 方案

### 1. 周本按名挑战包装 `ChallengeEchoOfWarByName`（新增，echo_of_war 包）

构造签名（MCP 契约）：
```python
def __init__(self, ctx: SrContext, mission: str, plan_times: int = 1):
```
- `mission`：周本关卡中文名（如「坏灭的喜剧」）或 mission_id；解析链 = `get_war_mission_list(ctx.guide_data)`（echo_of_war_config.py:10-17）按 display_name 包含匹配 / unique_id 精确匹配；多命中 → `ValueError` 带候选列表；零命中 → `ValueError` 带可选值清单。
- `plan_times`：成功次数，>=1 校验。
- **配队不从参数传，固定查周本计划**：按 mission_id 取 `EchoOfWarConfig.plan_list` 项（echo_of_war_config.py:45-57 全量补齐保证必存在），读其 `team_num`/`support`；**`support='none'` 在此处翻译为 None 再传核心**（编排层翻译先例 echo_of_war_app.py:93；ChooseSupportInTeam 只认 None，choose_support_in_team.py:45）；计划项 `team_num=0` 时运行日志显式报「计划配队=0，将沿用当前编队」（授权显性化——当前编队可能是上个玩法残留，周本败场照扣开拓力）。用户改配队去计划/GUI 改，单一源不双轨，不设 override 参数。
- 不带回调（MCP 契约）。
- `op_name = '历战余响 <关卡名> 次数 <plan_times>'`（照 ChallengeEchoOfWar 先例，challenge_ehco_of_war.py:44-50）。

节点链（一次流转一节点）：
1. **回大世界**：`BackToNormalWorldPlus`（起点任意可控画面——行迹面板态/大世界均可；幂等性依据其 docstring「起点任意可控画面」）
2. **传送**：`GuideTransport(mission)` → until 挑战副本-历战余响挑战态
3. **委托核心**：`ChallengeEchoOfWarCore(ctx, team_num=计划项.team_num, plan_times, support=计划项.support翻译值).execute()`——核心 status 全名单**八类**逐一显式分支（全名单见 weekly-core.md status 出口表）：`已完成计划次数`/`超时胜利已退出`/`连败放弃` → `round_success(同名)`（超时胜利分支日志透传 成功N/计划M）；`本周次数耗尽` → **清 `ctx.echo_of_war_run_record.left_times = 0`**（镜像 challenge_ehco_of_war.py:112 的 app 侧同款职责——带 mission 语义层的正当记账动作）→ `round_success('本周次数耗尽')`；`开拓力不足` → `round_success(同名)`；`有阵亡角色已复活` → `round_success(同名)`；`不在历战余响挑战画面`/`战斗超时无结算` → `round_fail` 原样透传；**未列明的任何 status（核心内子 op 自身失败等）一律 `round_fail` 原样透传**
4. **收尾回大世界**（仅核心 success 分支走本节点）：`BackToNormalWorldPlus` → `round_success('已返回大世界')`

终点：核心 success 分支终点**恒为大世界，终态 status 恒为「已返回大世界」**（对外契约单一，mock 断言按此口径）；核心 fail 分支原样透传、不收尾导航（画面停原地，交调用方处置）。
运行日志：启动时打印计划配队与消耗预估（`mission.power × plan_times` 开拓力 + 周本次数）；完成链打印实际消耗（成功次数 × `mission.power` 开拓力 + 周本次数）供调用方向用户汇报（总纲「明确不解决」声明的记账缺口由日志承载）。
副作用行：消耗周本挑战次数与开拓力，真实不可逆；调用方发起前须向用户说明并获同意。
类 docstring 注明：起点任意（自行回大世界导航）；配队取自周本计划该关卡项（0 = 沿用当前编队）。

### 2. 花萼共用口径（零新建）

- 行迹侧花萼缺料手动刷 = 既有 `FarmLightConeMaterialOp`（材料反查 → 副本直达 → 委托 `UseTrailblazePower(skip_transport=true)`，全链实机验证依据：探索存证与 game-coach「已建成的养成 op」节实跑记录）——本迭代**不新建**花萼挑战件，不与体力计划机制重复建库。
- 失败形态适配**不在本迭代**（用户裁定：开拓力 app 接入外溢）——归外溢迭代 `docs/develop/sr_od/application/trailblaze_power/changes/use-trailblaze-power-rehome/`（占位已立，含设计草案）；落地前行迹花萼手动路径遇战斗失败有卡死风险（挂账声明）。
- 配队口径：`FarmLightConeMaterialOp` 维持 `team_num` 参数（默认 0 = 当前编队，choose_team.py:30）；**花萼手动路径不解析计划、默认当前编队**（花萼赤难度低接受；体力计划的配队解析在编排层既有代码，本迭代不引入）。
- 花萼赤难度低，「防打不过」的配队诉求主战场是周本——花萼维持现状口径。

### 3. 行迹侧推荐链（文档口径，随落地更新 game-coach）

缺料推荐顺位更新为：①通用材料补全（op 内，默认开）→ ②花萼券刷（op 内 auto_farm 券刷四态已实现；**连刷次数参数为占位、券耗常量未按实测回填（现写 3，实测 1/次）——归 trace-upgrade-rework 外溢迭代**，占位期内可用性以实跑为准）→ ③授权手动刷周本 = `run_operation(ChallengeEchoOfWarByName)`（本迭代新增）→ ④手动刷花萼 = `FarmLightConeMaterialOp` → ⑤挂一条龙计划。②在券刷可用时优先于 ③（券刷零战斗时间成本）。

## 关键取舍
- **包装 op 查计划而非核心读计划**——核心保持 mission 无关（起点已就位，不知道自己是哪个本）；配置换算必须有 mission 语义，归属包装层。备选「核心带 `mission_id` 可选参数自行查计划」被否：让核心绑配置读取，破坏纯参数契约与资源窗口入口的通用性。
- **不设配队 override 参数**——计划是配队单一源；临时换队走计划/GUI。备选「包装加 team_num 可选覆盖」被否：双轨配队源必然漂移。
- **TP 传送入口而非资源窗口入口**——TP 从任意起点无条件可用（包装起点=任意画面）；资源窗口由行迹「快速刷取」按钮进入（缺料路径的产物：requirement.md 资源窗口节 + screen-flow.md 快速刷取节；「独立常态入口」未见档）且依赖行迹面板态，与「核心退出、入口无关」的裁定不配套。备选「资源窗口行二进入」被否：入口条件耦合行迹上下文。
- **收尾统一走 BackToNormalWorldPlus**——核心 success 分支落点两个（挑战画面/大世界复活点），包装不分支处理，统一走节点 4 后成功终态 status 恒为「已返回大世界」（对外契约单一；BackToNormalWorldPlus 起点任意可控画面，覆盖两种落点）。备选「阵亡分支跳过收尾」被否：对外 status 双轨。核心 fail 分支原样透传不收尾（失败属异常态，画面交调用方处置）。
- **support 翻译定死在包装读计划时**——编排层翻译是家族既有先例（echo_of_war_app.py:93），核心另做兜底归一防线；备选「只靠核心归一」被否：翻译语义属「计划值→机制值」换算，归 mission 语义层。
