"""MCP 配置修改工具:通用入口 + app_id 路由到领域方法(写穿 ctx + 校验前置)。

返回体方法论(P6/P15):校验/引用失败走 ConfigError 异常通道(文案带可用值/提示);
成功返回体只含增量信息(新增项 id / 变更后结构),入参回显(success/app_id/
list_field/key)与用法引导句(note→outputSchema 字段描述)不进返回体。

SR 适配:照搬自上游 backend(``6a577983``)。``_inject_category_options`` 依赖上游的
``compendium_service``(SR 无),且仅服务于已剔除的 charge_plan/notorious_hunt 路由 ——
SR 版改为 no-op(早返),待 SR 接入 category 类配置时再补。
"""
from collections.abc import Callable
from typing import Annotated

from pydantic import Field

from sr_od.backend.backend_context import SrBackendContext
from sr_od.backend.config_router import (
    _build_list_fields,
    _build_set_fields,
    _ro_item_fields_for,
    all_entries,
    get_entry,
)
from sr_od.backend.schemas import ConfigListOut, ConfigReadOut, ConfigSchemaOut


class ConfigError(Exception):
    """配置读写校验失败(app_id 不支持 / 操作不支持 / 字段或下标非法 / 项不存在)。

    文案带可用值或下一步提示;失败走异常通道,不占成功返回结构。
    """

    pass


def _require_entry(app_id: str, op: str | None = None):
    """按 app_id 取路由 entry;不存在或不支持该操作时 raise ConfigError。"""
    entry = get_entry(app_id)
    if entry is None:
        raise ConfigError(f'不支持的 app_id: {app_id}(可用清单用 list_app_configs 查)')
    if op is not None and op not in entry.supported_ops:
        raise ConfigError(f'{app_id} 不支持 {op}')
    return entry


def _require_list_field(entry, list_field: str) -> None:
    """校验 list_field 与 entry 的项类型匹配。"""
    expected = 'plan_list' if entry.item_kind == 'dataclass' else 'app_list'
    if list_field != expected:
        raise ConfigError(f'list_field 应为 {expected},实际 {list_field}')


def make_add_config_item(backend: SrBackendContext) -> Callable:
    """构造 ``add_config_item`` tool。"""
    async def add_config_item(
        app_id: Annotated[str, Field(description="app 配置 id,如 standalone_app")],
        list_field: Annotated[str, Field(description="列表字段名(plan_list/app_list)")],
        item_dict: Annotated[dict, Field(description="列表项 dict(经 from_dict 反序列化)")],
        idx: Annotated[int | None, Field(description="插入下标(0 基):插到现有第 idx 项之前;None=尾部追加。列表有序的场景(如开拓力计划按顺序执行)用 idx 控制执行顺位")] = None,
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前实例)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认组")] = None,
    ) -> str:
        """加一个数据类列表项(如 standalone_app 应用),返回新增项标识。操作类(会改配置文件)。

        通用入口,按 app_id 路由到该 config 的领域方法,写入前校验,不合法拒绝。
        idx 控制有序列表的插入位置(缺省尾部追加)。增删改配置前建议先调
        describe_config 查字段结构、合法值与只读项;当前配置值用 get_config 读。
        """
        ctx = backend.ctx
        entry = _require_entry(app_id, 'add')
        _require_list_field(entry, list_field)
        if idx is not None and idx < 0:
            raise ConfigError(f'idx 应为非负下标(0 基),实际 {idx}')
        config = entry.get_config(ctx, instance_idx, group_id)
        item = entry.item_from_dict(item_dict)
        err = entry.validate_item(ctx, item)
        if err:
            raise ConfigError(err)
        entry.add(config, item, idx)
        new_id: str | None = None
        if hasattr(config, 'plan_list') and config.plan_list:
            # 按 entry.id_kind 取项标识;项无该属性时(如开拓力计划项无 plan_id,
            # id_kind=idx)回退列表下标 —— 直接取 .plan_id 会让已成功的 add 被误报为失败。
            # 指定 idx 插入时新项就在 idx 处(越界已由 config 层校验),不能用尾下标
            new_id = getattr(config.plan_list[-1], entry.id_kind, None)
            if new_id is None and entry.id_kind == 'idx':
                new_id = str(idx if idx is not None else len(config.plan_list) - 1)
        elif entry.id_kind == 'app_id' and isinstance(item, str):
            new_id = item
        return f'已新增 {app_id}/{list_field} 项,标识 id={new_id}(delete/update 用该 id 定位)'
    return add_config_item


def make_delete_config_item(backend: SrBackendContext) -> Callable:
    """构造 ``delete_config_item`` tool。"""
    async def delete_config_item(
        app_id: Annotated[str, Field(description="app 配置 id,如 standalone_app")],
        list_field: Annotated[str, Field(description="列表字段名")],
        item_id: Annotated[str, Field(description="项标识:standalone_app/_group 用 app_id;dataclass 路由用 plan_id 或下标(见 list_app_configs 的 id_kind)")],
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前实例)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认组")] = None,
    ) -> str:
        """删一个数据类列表项,返回确认文案。操作类(会改配置文件),不可逆性低(删前确认项标识)。

        增删改配置前建议先调 describe_config 查字段结构;项标识的取值口径
        (id_kind)用 list_app_configs 查。
        """
        ctx = backend.ctx
        entry = _require_entry(app_id, 'delete')
        _require_list_field(entry, list_field)
        config = entry.get_config(ctx, instance_idx, group_id)
        deleted = entry.delete(config, item_id)
        if not deleted:
            raise ConfigError(f'未找到 id={item_id}')
        return f'已删除 {app_id}/{list_field} 项 id={item_id}'
    return delete_config_item


def make_update_config_item(backend: SrBackendContext) -> Callable:
    """构造 ``update_config_item`` tool(按 item_id 原位替换列表项)。"""
    async def update_config_item(
        app_id: Annotated[str, Field(description="app 配置 id,如 trailblaze_power")],
        list_field: Annotated[str, Field(description="列表字段名(plan_list)")],
        item_id: Annotated[str, Field(description="项标识,按 list_app_configs 的 id_kind(如 echo_of_war 用 mission_id)")],
        item_dict: Annotated[dict, Field(description="替换后的列表项完整 dict(全字段覆盖,未传字段取默认值)")],
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前实例)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认组")] = None,
    ) -> str:
        """按项标识原位更新一个数据类列表项,返回确认文案。操作类(会改配置文件)。

        适用于「全量补齐型」列表(如历战余响计划:全部周本关卡常驻,只改次数不增删
        条目)——原位替换保持顺序,写入前校验,不合法拒绝。增删条目用
        add_config_item / delete_config_item;改前建议先 get_config 读现有条目、
        describe_config 查字段结构。
        """
        ctx = backend.ctx
        entry = _require_entry(app_id, 'update')
        _require_list_field(entry, list_field)
        config = entry.get_config(ctx, instance_idx, group_id)
        item = entry.item_from_dict(item_dict)
        err = entry.validate_item(ctx, item)
        if err:
            raise ConfigError(err)
        updated = entry.update(config, item_id, item)
        if not updated:
            raise ConfigError(f'未找到 id={item_id}')
        return f'已更新 {app_id}/{list_field} 项 id={item_id}'
    return update_config_item


def make_get_config(backend: SrBackendContext) -> Callable:
    """构造 ``get_config`` tool(读配置字段/全 data)。"""
    async def get_config(
        app_id: Annotated[str, Field(description="app 配置 id,如 standalone_app")],
        key: Annotated[str | None, Field(description="字段名;None=返全 data")] = None,
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认")] = None,
    ) -> ConfigReadOut:
        """读配置字段或全部 data。观察类(只读,不改任何状态)。

        字段结构与合法值用 describe_config 查;可用配置清单用 list_app_configs。
        """
        ctx = backend.ctx
        entry = _require_entry(app_id)
        config = entry.get_config(ctx, instance_idx, group_id)
        if key:
            return ConfigReadOut(value=config.data.get(key))
        return ConfigReadOut(data=dict(config.data))
    return get_config


def make_set_config(backend: SrBackendContext) -> Callable:
    """构造 ``set_config`` tool(写简单/enum 字段 + 校验只读)。"""
    async def set_config(
        app_id: Annotated[str, Field(description="app 配置 id,如 standalone_app")],
        key: Annotated[str, Field(description="字段名(如 active_app_id)")],
        value: Annotated[str | int | bool, Field(description="字段值")],
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认")] = None,
    ) -> str:
        """写配置的简单字段(开关/下拉/输入),返回确认文案。操作类(会改配置文件)。

        只读字段(运行态/身份)拒绝;写穿 ctx 缓存实例并落盘,enum 字段值不合法时
        错误附可用值列表。列表项的增/删/改用 add_config_item /
        delete_config_item / update_config_item;改前建议先调 describe_config
        查字段结构、合法值与只读项。
        """
        ctx = backend.ctx
        entry = _require_entry(app_id, 'set')
        config = entry.get_config(ctx, instance_idx, group_id)
        if hasattr(config, '_RO_FIELDS') and key in config._RO_FIELDS:
            raise ConfigError(f'{key} 是只读字段(运行态/身份),不可 set')
        if entry.field_schema and key not in entry.field_schema:
            raise ConfigError(f'{key} 不在 {app_id} 的可改字段中(可用: {list(entry.field_schema.keys())})')
        if entry.field_schema and key in entry.field_schema:
            field_meta = entry.field_schema[key]
            if field_meta.get('type') == 'enum' and 'enum_cls' in field_meta:
                valid_values = [m.value.value for m in field_meta['enum_cls']]
                if value not in valid_values:
                    raise ConfigError(f'{key} 值 {value} 不合法(可用: {valid_values})')
        config.update(key, value)
        config.save()
        return f'已设置 {app_id}.{key}={value}(写穿缓存并已落盘,下一次运行立即生效)'
    return set_config


def make_describe_config(backend: SrBackendContext) -> Callable:
    """构造 ``describe_config`` tool(返回结构化 schema,智能体一看就懂)。"""
    async def describe_config(
        app_id: Annotated[str, Field(description="app 配置 id,如 standalone_app")],
        category: Annotated[str | None, Field(description="可选:查特定 category 的 mission_type 合法值(SR 暂无 category 路由,保留参数)")] = None,
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认")] = None,
    ) -> ConfigSchemaOut:
        """描述配置结构(可改字段 / 只读字段 / 列表项结构 / 加项示例)。观察类(只读)。

        返回 set_fields(可改 + enum options) + ro_fields(只读) + list_fields
        (item 结构 + add_example)——据此可直接生成正确的 set/add 调用。
        当前配置值用 get_config 读;不知道有哪些 app_id 时先 list_app_configs。
        """
        ctx = backend.ctx
        entry = _require_entry(app_id)
        config = entry.get_config(ctx, instance_idx, group_id)
        ro_fields: set[str] = set(getattr(config, '_RO_FIELDS', set()))

        # set_fields
        set_fields = _build_set_fields(config, entry.field_schema, ro_fields)

        # list_fields
        ro_item = _ro_item_fields_for(app_id)
        list_fields = _build_list_fields(entry, ro_item)

        # category 参数:查 mission_type 合法值(SR 当前无 category 路由,no-op)
        if category and list_fields:
            _inject_category_options(ctx, app_id, category, list_fields[0])

        return ConfigSchemaOut(
            description=entry.description,
            set_fields=set_fields,
            ro_fields=sorted(ro_fields),
            list_fields=list_fields,
        )
    return describe_config


def _inject_category_options(
    ctx: object, app_id: str, category: str, list_field: dict,
) -> None:
    """对 list_fields[0].item_fields 里 mission_type_name 注入 category 的合法值。

    SR 适配:上游版按 charge_plan/notorious_hunt 调 ``ctx.compendium_service`` 取合法值;
    SR 无 compendium_service 且这两条路由已剔除 → 当前无 category 路由,no-op 早返。
    待 SR 接入 category 类配置(如关卡分类)时,在此补对应领域查询。
    """
    return


def make_list_app_configs(backend: SrBackendContext) -> Callable:
    """构造 ``list_app_configs`` tool(列出可改配置,首次发现入口)。"""
    async def list_app_configs(
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前)")] = None,
    ) -> ConfigListOut:
        """列出可改配置的 app_id 清单(配置路由的首次发现入口)。观察类(只读)。

        返回每个 config 的 app_id + description + supported_ops + item_kind +
        id_kind:``item_kind`` 说明列表项类型(dataclass/str/dict),``id_kind``
        说明项标识字段名,照此生成正确的 add/delete/update 调用;字段级结构
        再进 describe_config。
        """
        configs: list[dict] = []
        for app_id, entry in all_entries().items():
            configs.append({
                'app_id': app_id,
                'description': entry.description,
                'supported_ops': list(entry.supported_ops),
                'item_kind': entry.item_kind,
                'id_kind': entry.id_kind,
            })
        return ConfigListOut(configs=configs)
    return list_app_configs
