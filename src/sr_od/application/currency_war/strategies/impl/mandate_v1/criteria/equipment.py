"""criteria/equipment——装备面(墓碑模块;M7 基础穿戴义务在 mandate)。

本模块原三判据面(wear_release/keep_policy/endgame_context)系
「设计先行、接线未做」的占位:自入库(换核批1)起生产调用点为零,
R189-5 修复池 D-B/D-P3 两项的定谳程序(P7 对账/实机对拍)均未执行;
已随 equipment 三死判据面退役批物理删除(裁定与考古账:原 ADR 档已删,git da3a7370ce 可溯)。
现行落点:

- D-B 非 key_equips 穿戴释放:生产单一源 = kernel
  ``cw_equip_env.resolve_wear_release`` 五行表(prep_actions 消费;
  18 号稿/ADR-0526),硬节点释放语义活载体 = row3 + O1 战斗前置门
  (21 号稿/ADR-0531)。
- keep_policy(P42 ③):命题在册已证(01_math_framework §3.6「近兑现张
  任何时刻绝不喂」)但生产落码载体缺位——kernel ``classify_item_hold``
  无兑现距离维度,现行架构无「组件定向喂件」决策位;已删占位对 d*>1
  默认返回「喂」,与命题「默认保留不喂」方向相反且缺「P3 boss 掉落流
  终止冗余件开放」例外,禁作命题种子复用。
- endgame_context(D-P3):修复池项 OPEN 挂账不变(定谳手段 = 实机 boss
  掉血分布对拍,从未执行);已删占位的 r_remaining<=3 系未证拍定值随之
  作废,复活须先「对拍定谳→三形态标注→落码」全流程。
"""
from __future__ import annotations
