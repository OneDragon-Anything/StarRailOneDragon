"""行迹升级材料数量表(5 星角色统一固定表,分段口径)。

本文件由 skills/sr-od-dev-character-data/scripts/generate_trace_cost_const.py 从 BWIKI 角色页
「技能晋阶材料」节生成,**禁手改**(数据修正走重新生成)。
- 段名「A→B」= 技能等级 A 升到 B;解锁条件 = 角色晋阶段数(「1→2」需
  角色晋阶 1,以此类推)——行迹升级 op 的「可提升至N级」即受此约束。
- 全 5 星角色统一(游戏机制);4 星角色表未核对不覆盖。
- 普攻(上限更低)与秘技(1 级)段数不同,BWIKI 第二张表无材料行不覆盖,
  以游戏内界面实读为准。
- 可信度凭据:固化时与游戏内晋阶界面三重交叉验证吻合(终结技 1→8 累计
  信用点 192500 / 永恒之花 8 / 永寿荣枝 7 / 无穷假身的遗恨 1)。
"""

_TRACE_LEVELUP_COSTS: dict[str, dict[str, int]] = {
 "1→2": {
  "永寿幼芽": 3,
  "信用点": 2500
 },
 "2→3": {
  "丰饶之种": 3,
  "永寿幼芽": 6,
  "信用点": 5000
 },
 "3→4": {
  "生命之芽": 3,
  "永寿天华": 3,
  "信用点": 10000
 },
 "4→5": {
  "生命之芽": 5,
  "永寿天华": 4,
  "信用点": 20000
 },
 "5→6": {
  "生命之芽": 7,
  "永寿天华": 6,
  "信用点": 30000
 },
 "6→7": {
  "永恒之花": 3,
  "永寿荣枝": 3,
  "信用点": 45000
 },
 "7→8": {
  "无穷假身的遗恨": 1,
  "永恒之花": 5,
  "永寿荣枝": 4,
  "信用点": 80000
 },
 "8→9": {
  "命运的足迹": 1,
  "无穷假身的遗恨": 1,
  "永恒之花": 8,
  "信用点": 160000
 },
 "9→10": {
  "命运的足迹": 1,
  "无穷假身的遗恨": 1,
  "永恒之花": 14,
  "信用点": 300000
 }
}


def total_cost(from_level: int, to_level: int) -> dict[str, int]:
    """技能从 from_level 升到 to_level 的材料合计(半开区间,不含 from_level
    所在行,含 to_level 行;如 total_cost(1, 8) = 1→2 至 7→8 各段之和)。"""
    result: dict[str, int] = {}
    for seg_name, mats in _TRACE_LEVELUP_COSTS.items():
        a = int(seg_name.split('→')[0])
        if from_level < a + 1 <= to_level:
            for name, amount in mats.items():
                result[name] = result.get(name, 0) + amount
    return result
