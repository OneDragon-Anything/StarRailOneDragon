# 0002. 「撞陌生画面 → 先建档」嵌进 debug 流程(不靠 screen-onboarding 被动触发)

- **Status**: accepted
- **Date**: 2026-08-05

## Context

`od-dev-screen-onboarding` 已在 description 加被动触发(「调试撞陌生画面 → 先建档」)。但 verifier 实测(2026-08-05,clean-context agent 排查「op 卡陌生画面」)显示:debug framing 的 agent **找 debug skill(`sr-od-dev-deciding-a-fix` 等),不找 screen-onboarding**(哪怕 description 加了被动触发)→ 单改 screen-onboarding description 对 debug 场景**低杠杆**。

根因:**debug 时 agent 的 skill 选择锚在「排查 bug → debug skill」,不会跳到「建档 skill」**。要让「撞陌生画面 → 先建档」生效,得把这条**嵌进 debug-automation 自己的流程**(debug 撞陌生画面时 agent 必经的 skill),而不是靠 screen-onboarding 被动被发现。

## Decision Drivers

- **触发位置 > 被动发现**:verifier 证据表明 debug framing 不主动发现建档 skill;把触发嵌进必经流程(debug-automation)才可靠。
- **单源不双写**:建档方法论正文在 `od-dev-screen-onboarding`(single source);debug-automation 只加「触发面 + 判据 + 转引」,不重写建档步骤。
- **防猜修回归**:画面认知不完整时猜 escape / 套兜底 / 改 op = 在猜的画面上修,必回归(下一个没猜到的交互又卡)。先建档搞清画面交互再改 op。

## Considered Options

1. **靠 screen-onboarding 的 description 被动触发**(原状 + 已补):pro 是不动 debug-automation;con 是 verifier 实测低杠杆(debug framing 不发现建档 skill)。
2. **debug-automation 加一节「撞陌生画面 → 先建档」+ 转引 screen-onboarding**(选中):把触发嵌进 debug 必经流程,可靠。
3. **在 debug-automation 重写建档方法论**:双写,违反单源;否决。

## Decision

选 **2**。debug-automation SKILL.md 加 §5「根因是『op 走到陌生画面』→ 先建档别猜修」:
- **判据**:定位到根因 = op 走到不完全认识其交互的画面 → 转建档(`od-dev-screen-onboarding`),先搞清画面全部可交互元素 + 各自点后跳哪,再回来改 op。
- **刹车判据**:说不出当前画面全部可交互元素 + 各自点后跳哪 → 先建档,别继续 debug framing 盲改。
- **点出易漏**:debug framing(尤其进度压力 / loop 紧迫感)下默认跳「快修 / 猜 escape」不触发建档 —— 正是要刹车的点。

附带:给 `sr-od-dev-deciding-a-fix` step 0(入口「确认故障机制」)加一句防御 —— 根因涉及陌生画面时,先确认画面交互认知完整再定修法(别在猜的画面上定修法)。这是 defense-in-depth:debug-automation 是主触发点(发现陌生画面时),deciding-a-fix step 0 兜底(决定修法前再确认一次画面认知)。

## Consequences

- **正向**:debug 撞陌生画面时可靠触发建档(嵌进必经流程,不靠被动发现);防猜修回归;建档方法论仍单源在 screen-onboarding。
- **负向**:debug-automation 新增一节(always-on 略增 ~10 行;值 —— 撞陌生画面不建档必回归,代价远高于多读 10 行)。
- **follow-up**:GREEN 验证 —— debug op 卡陌生画面时,agent 是否走「先建档」而非「猜修」。

## Links

- SKILL.md §5(撞陌生画面 → 先建档别猜修)。
- `od-dev-screen-onboarding`(建档方法论 single source;被动触发已补但 verifier 测出对 debug 场景低杠杆)。
- `sr-od-dev-deciding-a-fix` step 0(入口防御:画面认知完整再定修法)。
