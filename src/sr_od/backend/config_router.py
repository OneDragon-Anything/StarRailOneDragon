"""Config 修改路由表:app_id → 领域方法 / 校验 / 写穿取 config / describe schema。

通用 MCP 入口(set/add/update/delete/describe_config_item)按 app_id 路由到各 config 的领域方法,
**不裸写 data**(覆写 save() 的 config 会丢写)。handler 写穿 ctx 内同一缓存实例
(经 run_context.get_config 等),写入前校验,不合法拒绝。

详见 `docs/superpowers/specs/2026-07-24-mcp-config-design.md`(v5) +
`docs/superpowers/specs/2026-07-25-mcp-config-describe-design.md`(v5)。

SR 适配说明:照搬自上游 backend(``6a577983``)。上游的 ``charge_plan`` / ``notorious_hunt``
路由依赖其专属模块(``ChargePlanItem`` / ``NotoriousHuntConfig`` / ``compendium_service``),
SR 无对应实现 —— 已剔除。SR 已接入 ``trailblaze_power``(体力计划,``@dataclass`` 风格项 +
领域方法 ``TrailblazePowerConfig.add_plan_item``);后续同类配置在此补对应 RouterEntry。
"""
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from one_dragon.base.config.config_item import ConfigItem
from sr_od.application.trailblaze_power.trailblaze_power_config import (
    TrailblazePowerConfig,
    TrailblazePowerPlanItem,
)

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


# === RouterEntry ===

@dataclass
class RouterEntry:
    """单个 app config 的路由条目。

    各 callable 延迟 import(避免循环);无循环依赖的(如 trailblaze_power)直接模块级 import。
    field_schema / item_schema 集中声明(不散落 config 类)。
    """

    app_id: str
    description: str
    item_from_dict: Callable[[dict], object]
    get_config: Callable[['SrContext', int | None, str | None], object]
    validate_item: Callable[['SrContext', object], str | None]
    add: Callable[[object, object, int | None], None]  # idx=插入下标(None=尾部);列表有序的 config 位置即执行顺位
    delete: Callable[[object, str], bool]
    id_kind: str  # 'plan_id' / 'idx' / 'app_id'
    item_kind: str = 'dataclass'  # 'dataclass' / 'str' / 'dict'
    supported_ops: tuple[str, ...] = ('get', 'set', 'add', 'delete', 'describe')
    field_schema: dict[str, dict] | None = None
    item_schema: list[dict] | None = None


# === Enum 反射 helper ===

def _enum_options(enum_cls: type[Enum]) -> list[dict]:
    """从 Enum 类反射 options: [{label, value}]。value = ConfigItem.value(智能体传这个)。"""
    return [
        {'label': m.value.label, 'value': m.value.value}
        for m in enum_cls
        if isinstance(m.value, ConfigItem)
    ]


# === describe schema 组装 helper ===

def _build_set_fields(
    config: object, field_schema: dict[str, dict] | None, ro_fields: set[str] | None,
) -> list[dict]:
    """组装 set_fields(可改字段:name + type + value + options + desc)。

    从 field_schema 声明取 type/enum/desc;从 config.data 取当前值。
    只读字段(_RO_FIELDS)排除。
    """
    if field_schema is None:
        return []
    ro = ro_fields or set()
    result: list[dict] = []
    for name, meta in field_schema.items():
        if name in ro:
            continue
        field: dict[str, Any] = {
            'name': name,
            'type': meta.get('type', 'str'),
            'value': getattr(config, name, None) if not isinstance(getattr(config, name, None), property) else config.data.get(name),  # type: ignore[attr-defined]
            'desc': meta.get('desc', ''),
        }
        if meta.get('type') == 'enum' and 'enum_cls' in meta:
            field['options'] = _enum_options(meta['enum_cls'])
        elif 'options_source' in meta:
            field['note'] = f"合法值来源: {meta['options_source']}"
        result.append(field)
    return result


def _build_list_fields(
    entry: 'RouterEntry', ro_item_fields: list[str] | None,
) -> list[dict]:
    """组装 list_fields(item 结构 + add_example)。

    item_schema 优先(提供 enum/options/applicability/note);反射补 name+default。
    add_example 过滤 ro_item_fields。enum_cls 展开为 options。
    """
    if entry.item_schema is None:
        return []

    # 深拷贝 item_schema 并展开 enum_cls → options
    expanded_fields: list[dict] = []
    for f in entry.item_schema:
        ef = dict(f)
        if 'enum_cls' in ef:
            enum_cls = ef.pop('enum_cls')
            if isinstance(enum_cls, type) and issubclass(enum_cls, Enum):
                ef['options'] = _enum_options(enum_cls)
            elif isinstance(enum_cls, str):
                ef['options_source'] = enum_cls  # '从 compendium 取' 等描述
        expanded_fields.append(ef)

    # add_example: 从 expanded_fields 构造最小 dict(过滤 ro)
    ro = set(ro_item_fields or [])
    example: dict[str, Any] = {}
    for f in expanded_fields:
        if f['name'] in ro:
            continue
        if f.get('required') or 'default' in f:
            example[f['name']] = f.get('default', '')

    return [{
        'name': 'plan_list' if entry.item_kind == 'dataclass' else 'app_list',
        'id_kind': entry.id_kind,
        'id_source': (
            f"get_config 读 list.{entry.id_kind}(add 时自动生成,不要传)" if entry.id_kind == 'plan_id'
            else "get_config 读 data 里该列表的下标(0 基,顺序即下标);delete 时传 str(idx)" if entry.id_kind == 'idx'
            else "get_config 读 list"
        ),
        'item_kind': entry.item_kind,
        'item_fields': expanded_fields,
        'note': '未列字段(tab_name 等)由 dataclass 默认值自动补,add 时可不传',
        'ro_item_fields': ro_item_fields or [],
        'add_example': example,
        'validate_hint': _validate_hint_for(entry.app_id),
    }]


def _validate_hint_for(app_id: str) -> str:
    """各 config 的校验提示。"""
    hints = {
        'standalone_app': 'app_id 必须已注册(is_app_registered)',
        '_group': 'app_id 必须已注册;add 不支持(app 由注册注入)',
        'trailblaze_power': 'mission_id 须能被指南数据解析(get_mission_by_unique_id);plan_times≥1;0≤run_times≤plan_times',
    }
    return hints.get(app_id, '')


def _ro_item_fields_for(app_id: str) -> list[str]:
    """各 config 的 item 级只读字段(add 时不需要/不能传的字段)。"""
    # trailblaze_power:计划项全部字段均可显式传入,无自动生成标识 —— 无只读项。
    return []


# === standalone_app helpers ===

def _standalone_app_get_config(
    ctx: 'SrContext', instance_idx: int | None, group_id: str | None,
) -> object:
    return ctx.standalone_app_config


def _standalone_app_item_from_dict(data: dict) -> str:
    return data.get('app_id', '')


def _standalone_app_validate_item(ctx: 'SrContext', item: str) -> str | None:
    if not ctx.run_context.is_app_registered(item):
        return f'app_id {item} 未注册(不在应用列表)'
    return None


def _standalone_app_add(config: object, item: str, idx: int | None = None) -> None:
    # 独立应用列表同样有序(一条龙组执行顺序);越界切片天然落到尾部(handler 已挡负数)
    if idx is None:
        config.app_list = config.app_list + [item]  # type: ignore[attr-defined]
    else:
        config.app_list = config.app_list[:idx] + [item] + config.app_list[idx:]  # type: ignore[attr-defined]


def _standalone_app_delete(config: object, item: str) -> bool:
    old_len = len(config.app_list)  # type: ignore[attr-defined]
    config.app_list = [a for a in config.app_list if a != item]  # type: ignore[attr-defined]
    return len(config.app_list) < old_len  # type: ignore[attr-defined]


# === _group helpers ===

def _group_get_config(
    ctx: 'SrContext', instance_idx: int | None, group_id: str | None,
) -> object:
    idx = instance_idx if instance_idx is not None else ctx.current_instance_idx
    return ctx.app_group_manager.get_one_dragon_group_config(idx)


def _group_validate_item(ctx: 'SrContext', item: str) -> str | None:
    if not ctx.run_context.is_app_registered(item):
        return f'app_id {item} 未注册(不在应用列表)'
    return None


def _group_add(_config: object, _item: str) -> None:
    raise ValueError('_group 不支持 add(app 由注册注入)')


def _group_delete(config: object, app_id: str) -> bool:
    for item in config._all_apps:  # type: ignore[attr-defined]
        if item.app_id == app_id:  # type: ignore[attr-defined]
            config.remove_app(app_id)  # type: ignore[attr-defined]
            return True
    return False


# === trailblaze_power helpers(体力计划) ===

def _trailblaze_power_get_config(
    ctx: 'SrContext', instance_idx: int | None, group_id: str | None,
) -> object:
    # 当前实例写穿 ctx 缓存实例 —— 一条龙开拓力 app 用的就是 ctx.power_config,
    # 经此写入的计划对下一次 run 立即生效,无需重启。其他实例按需构造(落盘生效)。
    idx = instance_idx if instance_idx is not None else ctx.current_instance_idx
    if idx == ctx.current_instance_idx:
        return ctx.power_config
    return TrailblazePowerConfig(ctx.guide_data, idx)


def _trailblaze_power_item_from_dict(data: dict) -> object:
    # mission 关联不在本步做(需 ctx,由 add_plan_item 统一处理,与 init_plan_list 同源)
    return TrailblazePowerPlanItem(
        mission_id=data.get('mission_id', ''),
        team_num=data.get('team_num', 0),
        support=data.get('support', 'none'),
        plan_times=data.get('plan_times', 0),
        run_times=data.get('run_times', 0),
        diff=data.get('diff', 0),
        file_num=data.get('file_num', 0),
        team_name=data.get('team_name', ''),
    )


def _trailblaze_power_validate_item(ctx: 'SrContext', item: object) -> str | None:
    # mission_id 可解析性由 add_plan_item 校验(需 guide_data,与 init_plan_list 同源);
    # 这里只做数值边界,提前拦截明显的坏参数
    if not item.mission_id:  # type: ignore[attr-defined]
        return 'mission_id 不能为空'
    if item.plan_times < 1:  # type: ignore[attr-defined]
        return f'plan_times 必须≥1,实际 {item.plan_times}'  # type: ignore[attr-defined]
    if item.run_times < 0 or item.run_times > item.plan_times:  # type: ignore[attr-defined]
        return (f'run_times 须在 0~plan_times 内,'
                f'实际 run_times={item.run_times}, plan_times={item.plan_times}')  # type: ignore[attr-defined]
    return None


def _trailblaze_power_add(config: object, item: object, idx: int | None = None) -> None:
    # add_plan_item 内部校验 mission 可解析与插入位置越界,失败抛 ValueError(handler 转 error);
    # 一条龙按 plan_list 顺序执行,插入位置 = 执行顺位
    config.add_plan_item(item, idx)  # type: ignore[attr-defined]


def _trailblaze_power_delete(config: object, item_id: str) -> bool:
    # item_id = plan_list 下标(0 基,str 传入);越界返回 False(handler 报未找到)
    try:
        idx = int(item_id)
    except ValueError:
        raise ValueError(f'item_id 应为 plan_list 下标数字,实际 {item_id!r}') from None
    if idx < 0 or idx >= len(config.plan_list):  # type: ignore[attr-defined]
        return False
    config.delete_plan(idx)  # type: ignore[attr-defined]  # 内部 save 落盘
    return True


# === ROUTES(含 field_schema + item_schema) ===

def _build_routes() -> dict[str, RouterEntry]:
    """延迟构建 ROUTES(enum_cls 需要 import,避免模块级循环)。"""
    return {
        'standalone_app': RouterEntry(
            app_id='standalone_app',
            description='独立应用列表',
            item_from_dict=_standalone_app_item_from_dict,
            get_config=_standalone_app_get_config,
            validate_item=_standalone_app_validate_item,
            add=_standalone_app_add,
            delete=_standalone_app_delete,
            id_kind='app_id',
            item_kind='str',
            supported_ops=('get', 'set', 'add', 'delete', 'describe'),
            field_schema={
                'active_app_id': {'type': 'str', 'desc': '当前激活的独立应用', 'options_source': 'config.app_list(动态,先 get_config 读)'},
            },
            item_schema=[
                {'name': 'app_id', 'type': 'str', 'required': True, 'note': '必须已注册(is_app_registered)'},
            ],
        ),
        '_group': RouterEntry(
            app_id='_group',
            description='一条龙应用组',
            item_from_dict=_standalone_app_item_from_dict,
            get_config=_group_get_config,
            validate_item=_group_validate_item,
            add=_group_add,
            delete=_group_delete,
            id_kind='app_id',
            item_kind='dict',
            supported_ops=('get', 'delete', 'describe'),
            item_schema=[
                {'name': 'app_id', 'type': 'str', 'required': True, 'note': '必须已注册'},
                {'name': 'enabled', 'type': 'bool', 'required': False, 'note': '经 set_app_enable 改,v1 无 MCP 入口'},
            ],
        ),
        'trailblaze_power': RouterEntry(
            app_id='trailblaze_power',
            description='开拓力体力计划:plan_list 计划项(mission_id/plan_times/run_times 等)+ loop 循环开关;'
                        '一条龙按 plan_list 顺序执行,add 的 idx 插入位置即执行顺位(默认尾部);'
                        'add/delete 写穿当前实例缓存,下一次一条龙 run 立即生效,无需重启',
            item_from_dict=_trailblaze_power_item_from_dict,
            get_config=_trailblaze_power_get_config,
            validate_item=_trailblaze_power_validate_item,
            add=_trailblaze_power_add,
            delete=_trailblaze_power_delete,
            id_kind='idx',
            item_kind='dataclass',
            supported_ops=('get', 'set', 'add', 'delete', 'describe'),
            field_schema={
                'loop': {'type': 'bool', 'desc': '计划全部完成后是否自动重置 run_times 循环执行'},
            },
            item_schema=[
                {'name': 'mission_id', 'type': 'str', 'required': True,
                 'note': '关卡唯一 id:「生存索引 {分类} {关卡} {区域}」;'
                         '材料→关卡反查用 dungeon_drop_const.find_missions_by_material 的三元组拼出'},
                {'name': 'plan_times', 'type': 'int', 'required': True,
                 'note': '计划通关次数(缺口÷单次产量,向上取整)'},
                {'name': 'run_times', 'type': 'int', 'required': False, 'default': 0,
                 'note': '已完成次数;新计划传 0'},
                {'name': 'team_num', 'type': 'int', 'required': False, 'default': 0,
                 'note': '使用配队编号,0=游戏内当前配队'},
                {'name': 'support', 'type': 'str', 'required': False, 'default': 'none',
                 'note': '支援角色,"none"=不带支援'},
                {'name': 'diff', 'type': 'int', 'required': False, 'default': 0,
                 'note': '难度,0=自动选最高'},
            ],
        ),
    }


_ROUTES: dict[str, RouterEntry] | None = None


def _routes() -> dict[str, RouterEntry]:
    """延迟初始化 ROUTES(避免模块级 import 循环)。"""
    global _ROUTES
    if _ROUTES is None:
        _ROUTES = _build_routes()
    return _ROUTES


def get_entry(app_id: str) -> RouterEntry | None:
    """按 app_id 取路由条目;未注册返 None(handler 拒绝)。"""
    return _routes().get(app_id)


def all_entries() -> dict[str, RouterEntry]:
    """返回全部路由(供 list_app_configs 遍历)。"""
    return _routes()
