# 0121. sell_refund 手续费 cost 相关(1费 exempt;2费+ star≥2 才减1)

- **Status**: accepted(2026-08-13)
- **原编号**: D-121
- **关联**: economy_research §2 / sell_refund(``cw_state``)/ sell-star 停机钩子(已删)

## Context

``sell_refund`` 旧公式:``refund = cost × _SELL_MULT[star]``;``star≥2`` 一刀切 ``−1``(手续费)。依据 = 用户印象「2星少1金币」+ economy_research §2 内部矛盾修正(L83「2★=cost×3 即免费」vs L93「2★以上不免费」→ 取 −1 = 亏1金)。

2026-08-13 sell-star 停机钩子触发(board 上飞霄/万敌/椒丘 2★),AI 接手实机核售价:click 万敌(back-1 figure center)开详情面板 → VLM(zai GLM-4.5V)读出售按钮 = **金币图标 + "+3"**。万敌 2★ cost=1 → ``cost×3 = 3``(**无 −1**)。用户澄清:**1费 2星不减**;**2费开始才减1**(手续费 cost 相关,非纯 star)。

故旧 ``star≥2`` 一刀切 −1 **把 1费 也 −1 了(错)**;economy_research §2 矛盾的真相 = L83 对(1费/cost×3 全额退)、L93 描述的是 cost≥2 场景。

## Decision Drivers

- live 实测:2★ cost=1 万敌 出售 = +3(``cost×3``,无 −1),VLM 读「金币+3」客观确认。
- 用户(玩法权威):1费不减、2费开始减1 → 手续费 cost 相关。
- economy_research §2 矛盾由此消解(L83 全额退 对;L93 指 cost≥2)。
- sell_refund 影响 cw_decisions 卖决策(interest threshold,L835)+ simulate(gold 结算,L303):1费角色卖价被低估(少1金)→ 少估利息跳档动机。

## Considered Options

1. **旧 ``star≥2`` 一刀切 −1**(推翻)—— 1费角色误 −1(实测 2★1费=3 非 2)。
2. **全删 −1(全额退,无费)**(否决)—— 与用户「2费开始减1」矛盾;2费+ 实测/记忆有 −1。
3. **−1 仅 ``star≥2 且 cost≥2``**(采用)—— 1费 exempt(实测)+ 2费+ −1(用户),消解 §2 矛盾。

## Decision

**3**。``sell_refund``:

```python
refund = max(cost, 1) * _SELL_MULT.get(star, 1)   # {1:1, 2:3, 3:9, 4:27}
if star >= 2 and cost >= 2:
    refund -= 1   # 合成手续费:仅 star≥2 且 cost≥2(cost=1 exempt)
return max(refund, 0)
```

- cost=1 各星:**全额退**(1★=1、2★=3、3★=9、4★=27)。2★1费 live 实测 +3。
- cost≥2 star≥2:``cost×mult − 1``(2★2费=5、2★3费=8、3★3费=26…)。
- 1★ 任何 cost:= cost(无合成,无费;权威 BWIKI)。

## Consequences

- **正向**:1费角色(飞霄/万敌/椒丘/三月七 等 CW 主力多 1费)卖价修正(+1 金);卖决策 / 利息跳档估算更准。
- **待 live 核**:cost≥2 的 −1(2★2费=5)是用户记忆,未实测(本局板无 cost≥2 2★);3/4星 cost=1 全额(=9/27)是规则外推,未实测。下轮遇 cost≥2 2★ / 3★ 再核。
- 删 sell-star 停机钩子(``battle_prep.buy`` L51-67):售价已验(2★1费=3),钩子任务完成(AGENTS.local.md「临时钩子用完即删」)。

## Links
- economy_research §2(售价表;矛盾 L83/L93 由本 ADR 消解)。
- sell_refund(``cw_state.py``)= 卖决策(cw_decisions)+ simulate 结算(cw_state)用。
- sell-star 停机钩子(已删,本 ADR 的验证手段)。
