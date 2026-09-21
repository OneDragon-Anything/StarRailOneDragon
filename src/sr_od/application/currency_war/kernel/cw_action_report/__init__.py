"""货币战争动作上报函数族包(每动作一个文件,专辖该动作的容器
上报语义;2026-09-18 用户裁定自 cw_game_state 拆出)。

规约:词表类 ``CwActionXxxParam`` 恰有一个具名上报函数
``report_action_<snake>_param``(snake = 去前缀/后缀转下划线,
机械可推导;完备锁 = sr-od-test test_cw_action_report_contract,
经包级属性解析)。文件布局:
- 有容器写语义的动作 = 一动作一文件(文件名 = snake);
- ``level_up_shop`` = level_up 同字段双类型别名,独立文件保持
  文件名均一;
- 工具原子七类 = ``tool_use``(机械半同构一族一文件,容器写形态);
- 零写动作族 = ``zero_writes``(策略统一,不逐类开文件);
- 刷新执行计数组 ``record_refresh_execution`` 与刷新上报同文件
  (refresh_shop,语义同主)。

依赖方向:本包 → cw_game_state(容器/渠道签名/值类型/读口),
反向模块级零 import(懒加载惯例同 kernel 既有纪律)。
``__getattr__`` = 命名规约 lazy 解析(模块名 = snake;未命中依次落
``tool_use`` / ``zero_writes`` 族模块),包级直取合法;生产 op 直调面
建议直接 import 具名模块(文件归属显式)。
"""

# ============================================================ 动作上报接口(每动作一个具名函数)
#
# 命名规约 = ``report_action_<snake>_param``:词表类 ``CwActionXxxParam`` 去前后缀
# 转 snake,机械可推导(完备锁测试遍历 CW_ACTION_TYPES 逐类断言函数在场)。
# 消费面 = 实机动作 op(组装时已知自身类型,直调本函数)与 sim/回放引擎入口
# (一行委托分支串)。**禁新增按类型聚合的转移函数**——语义全部住本函数族,
# 分派只允许出现在「手里攥着任意 param 流」的引擎入口。
#
# 双域腿统一申报(摊平批):原商店腿(apply_shop_action_logic 分支)与备战腿
# (apply_prep_action_logic 分支)为同一动作语义的历史两份,本函数族合一:
# - 容器写统一**原生 BenchSlot 形态**(legacy roundtrip 丢 box/tome kind 细分,
#   原 prep 腿注释在案);cleared 槽 = kind 'empty';
# - 溢出入位腿 = 容器状态条件(overflow_warning 在场),域无关携带;
# - 装备回收(C6 装备守恒)统一携带——原备战域缺口(原由执行侧
#   apply_op_effect SellDeployed 分支单边承担),op 自上报后单点化;
# - expect 代际校验统一携带(live 提案 expect 恒 '' = 零行为);
# - 出参统一 LogicOutcome(拒绝 = applied=False + reason + 零容器写;
#   live 调用方可忽略出参,零行为)。
# 域级跳写纪律不变:gold/xp/level 未读(None)该域跳写,值留观察覆盖。

import importlib

_ZERO_WRITE_MODULE = 'zero_writes'
_TOOL_USE_MODULE = 'tool_use'



def __getattr__(name: str):
    """命名规约 lazy 解析(``report_action_<snake>_param`` → 同名
    模块;未命中依次落工具族/零写族模块)。ModuleNotFoundError 之外的导入
    异常原样上抛(目标模块真实损坏必须响亮,禁吞)。"""
    if name.startswith('report_action_') and name.endswith('_param'):
        snake = name[len('report_action_'):-len('_param')]
        for mod_name in (snake, _TOOL_USE_MODULE, _ZERO_WRITE_MODULE):
            try:
                mod = importlib.import_module(
                    f'{__name__}.{mod_name}')
            except ModuleNotFoundError:
                continue
            fn = getattr(mod, name, None)
            if fn is not None:
                return fn
    raise AttributeError(
        f'module {__name__!r} has no attribute {name!r}')
