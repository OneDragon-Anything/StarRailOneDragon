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
- 刷新上报 = refresh_shop(计数腿:付费/全量两计数经效果账本
  ``record_refresh`` 单口,免费腿 = 容器字段 free_refresh_left 判定扣减,
  payload 随机态 = kernel 采样器 write_logic_rand)。

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
# 消费面 = 实机动作 op(组装时已知自身类型,直调本函数)与商店序列驱动器
# (回放/既有序列锁消费面)直调。**禁新增按类型聚合的转移函数**——语义
# 全部住本函数族,现无任何聚合分派点(正本口径 =
# game_state/logic-updates/README.md 总则 1)。
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
import random
from collections.abc import Callable

_ZERO_WRITE_MODULE = 'zero_writes'
_TOOL_USE_MODULE = 'tool_use'


# ============================================================ 动作腿采样 rng 提供槽
# (sim 统一迭代 3.4 运行器装配缝;T-2 偏差申报的注入点归属。
#  实机缺省 None = 采样未播种口径零变化——上报函数 ``rng=None`` 回退
#  自掷随机(采样是猜测);sim 装配后由运行器经本槽注入流键 rng
#  (采样即世界真值,全程确定性)。先例 = ``cw_event_hooks`` 事件槽
#  「模块级槽 + 缺省关 + 装配点显式接通」。)

_ACTION_RNG_PROVIDER: Callable[[str], random.Random] | None = None


def set_action_rng_provider(
        fn: Callable[[str], random.Random] | None) -> None:
    """注入动作腿采样 rng 提供者(注入槽模式,None = 关,缺省态)。

    ``fn(tool) -> random.Random``:``tool`` = 采样腿具名键(如
    'collect_ore'/'refresh_shop'),每次采样调用取一个新 rng,调用方
    (sim 装配方)负责键序确定性。
    """
    global _ACTION_RNG_PROVIDER
    _ACTION_RNG_PROVIDER = fn


def provided_action_rng(tool: str) -> random.Random | None:
    """取动作腿采样注入 rng(未装配 = None,调用方回退自掷)。"""
    return None if _ACTION_RNG_PROVIDER is None \
        else _ACTION_RNG_PROVIDER(tool)


def action_sampling_rng(tool: str, rng: random.Random | None,
                        _fallback: random.Random | None = None
                        ) -> random.Random:
    """上报函数采样 rng 统一解析口(显式传入 > 注入槽 > 缺省回退)。

    ``_fallback`` = 模块自持的历史缺省(如 tool_use 的共享实例);None =
    现掷 ``random.Random()``(实机未播种口径)。
    """
    if rng is not None:
        return rng
    injected = provided_action_rng(tool)
    if injected is not None:
        return injected
    return _fallback if _fallback is not None else random.Random()



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
