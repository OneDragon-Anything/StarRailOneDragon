"""MCP 配置修改工具:通用入口 + app_id 路由到领域方法(写穿 ctx + 校验前置)。

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


def make_add_config_item(backend: SrBackendContext) -> Callable:
    """构造 ``add_config_item`` tool。"""
    async def add_config_item(
        app_id: Annotated[str, Field(description="app 配置 id,如 standalone_app")],
        list_field: Annotated[str, Field(description="列表字段名(plan_list/app_list)")],
        item_dict: Annotated[dict, Field(description="列表项 dict(经 from_dict 反序列化)")],
        idx: Annotated[int | None, Field(description="插入下标(0 基):插到现有第 idx 项之前;None=尾部追加。列表有序的场景(如开拓力计划按顺序执行)用 idx 控制执行顺位")] = None,
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前实例)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认组")] = None,
    ) -> dict:
        """加一个数据类列表项(如 standalone_app 应用)。操作类(会改配置文件)。

        通用入口,按 ``app_id`` 路由到该 config 的领域方法,写入前校验,不合法拒绝。
        ``idx`` 控制有序列表的插入位置(缺省尾部追加)。增删改配置前建议先调
        ``describe_config`` 查字段结构、合法值与只读项;当前配置值用 ``get_config`` 读。

        Returns:
            ``{success, error}`` 或 ``{success: True, app_id, list_field, id(新项标识)}``。
        """
        ctx = backend.ctx
        entry = get_entry(app_id)
        if entry is None:
            return {'success': False, 'error': f'不支持的 app_id: {app_id}'}
        if 'add' not in entry.supported_ops or entry.add is None:
            return {'success': False, 'error': f'{app_id} 不支持 add'}
        expected_list = 'plan_list' if entry.item_kind == 'dataclass' else 'app_list'
        if list_field != expected_list:
            return {'success': False, 'error': f'list_field 应为 {expected_list},实际 {list_field}'}
        if idx is not None and idx < 0:
            return {'success': False, 'error': f'idx 应为非负下标(0 基),实际 {idx}'}
        try:
            config = entry.get_config(ctx, instance_idx, group_id)
            item = entry.item_from_dict(item_dict)
            err = entry.validate_item(ctx, item)
            if err:
                return {'success': False, 'error': err}
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
            return {'success': True, 'app_id': app_id, 'list_field': list_field, 'id': new_id}
        except Exception as e:  # noqa: BLE001
            return {'success': False, 'error': str(e)}
    return add_config_item


def make_delete_config_item(backend: SrBackendContext) -> Callable:
    """构造 ``delete_config_item`` tool。"""
    async def delete_config_item(
        app_id: Annotated[str, Field(description="app 配置 id,如 standalone_app")],
        list_field: Annotated[str, Field(description="列表字段名")],
        item_id: Annotated[str, Field(description="项标识:standalone_app/_group 用 app_id;dataclass 路由用 plan_id 或下标(见 list_app_configs 的 id_kind)")],
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前实例)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认组")] = None,
    ) -> dict:
        """删一个数据类列表项。操作类(会改配置文件),不可逆性低(删前确认项标识)。

        增删改配置前建议先调 ``describe_config`` 查字段结构;项标识的取值口径
        (id_kind)用 ``list_app_configs`` 查。

        Returns:
            ``{success, error}`` 或 ``{success: True, app_id, list_field, id}``。
        """
        ctx = backend.ctx
        entry = get_entry(app_id)
        if entry is None:
            return {'success': False, 'error': f'不支持的 app_id: {app_id}'}
        if 'delete' not in entry.supported_ops or entry.delete is None:
            return {'success': False, 'error': f'{app_id} 不支持 delete'}
        expected_list = 'plan_list' if entry.item_kind == 'dataclass' else 'app_list'
        if list_field != expected_list:
            return {'success': False, 'error': f'list_field 应为 {expected_list},实际 {list_field}'}
        try:
            config = entry.get_config(ctx, instance_idx, group_id)
            deleted = entry.delete(config, item_id)
            if not deleted:
                return {'success': False, 'error': f'未找到 id={item_id}'}
            return {'success': True, 'app_id': app_id, 'list_field': list_field, 'id': item_id}
        except Exception as e:  # noqa: BLE001
            return {'success': False, 'error': str(e)}
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
    ) -> dict:
        """按项标识原位更新一个数据类列表项。操作类(会改配置文件)。

        适用于「全量补齐型」列表(如历战余响计划:全部周本关卡常驻,只改次数不增删
        条目)——原位替换保持顺序,写入前校验,不合法拒绝。增删条目用
        ``add_config_item`` / ``delete_config_item``;改前建议先 ``get_config``
        读现有条目、``describe_config`` 查字段结构。

        Returns:
            ``{success, error}`` 或 ``{success: True, app_id, list_field, id}``。
        """
        ctx = backend.ctx
        entry = get_entry(app_id)
        if entry is None:
            return {'success': False, 'error': f'不支持的 app_id: {app_id}'}
        if 'update' not in entry.supported_ops or entry.update is None:
            return {'success': False, 'error': f'{app_id} 不支持 update(增删用 add/delete)'}

        expected_list = 'plan_list' if entry.item_kind == 'dataclass' else 'app_list'
        if list_field != expected_list:
            return {'success': False, 'error': f'list_field 应为 {expected_list},实际 {list_field}'}
        try:
            config = entry.get_config(ctx, instance_idx, group_id)
            item = entry.item_from_dict(item_dict)
            err = entry.validate_item(ctx, item)
            if err:
                return {'success': False, 'error': err}
            updated = entry.update(config, item_id, item)
            if not updated:
                return {'success': False, 'error': f'未找到 id={item_id}'}
            return {'success': True, 'app_id': app_id, 'list_field': list_field, 'id': item_id}
        except Exception as e:  # noqa: BLE001
            return {'success': False, 'error': str(e)}
    return update_config_item


def make_get_config(backend: SrBackendContext) -> Callable:
    """构造 ``get_config`` tool(读配置字段/全 data)。"""
    async def get_config(
        app_id: Annotated[str, Field(description="app 配置 id,如 standalone_app")],
        key: Annotated[str | None, Field(description="字段名;None=返全 data")] = None,
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认")] = None,
    ) -> dict:
        """读配置字段或全部 data。观察类(只读,不改任何状态)。

        字段结构与合法值用 ``describe_config`` 查;可用配置清单用 ``list_app_configs``。

        Returns:
            key 传入 → ``{success: True, app_id, key, value(字段值)}``;
            key 省略 → ``{success: True, app_id, data(全部字段 dict)}``;失败 ``{success, error}``。
        """
        ctx = backend.ctx
        entry = get_entry(app_id)
        if entry is None:
            return {'success': False, 'error': f'不支持的 app_id: {app_id}'}
        try:
            config = entry.get_config(ctx, instance_idx, group_id)
            if key:
                return {'success': True, 'app_id': app_id, 'key': key, 'value': config.data.get(key)}
            return {'success': True, 'app_id': app_id, 'data': dict(config.data)}
        except Exception as e:  # noqa: BLE001
            return {'success': False, 'error': str(e)}
    return get_config


def make_set_config(backend: SrBackendContext) -> Callable:
    """构造 ``set_config`` tool(写简单/enum 字段 + 校验只读)。"""
    async def set_config(
        app_id: Annotated[str, Field(description="app 配置 id,如 standalone_app")],
        key: Annotated[str, Field(description="字段名(如 active_app_id)")],
        value: Annotated[str | int | bool, Field(description="字段值")],
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认")] = None,
    ) -> dict:
        """写配置的简单字段(开关/下拉/输入)。操作类(会改配置文件)。

        只读字段(run_times/plan_id 等运行态)拒绝;写穿 ctx 缓存实例并落盘。
        列表项的增/删/改用 ``add_config_item`` / ``delete_config_item`` /
        ``update_config_item``;改前建议先调 ``describe_config`` 查字段结构、
        合法值与只读项。

        Returns:
            ``{success: True, app_id, key, value}`` 或 ``{success: False, error(只读/不合法原因,
            enum 错误会附可用值列表)}``。
        """
        ctx = backend.ctx
        entry = get_entry(app_id)
        if entry is None:
            return {'success': False, 'error': f'不支持的 app_id: {app_id}'}
        if 'set' not in entry.supported_ops:
            return {'success': False, 'error': f'{app_id} 不支持 set'}
        try:
            config = entry.get_config(ctx, instance_idx, group_id)
            if hasattr(config, '_RO_FIELDS') and key in config._RO_FIELDS:
                return {'success': False, 'error': f'{key} 是只读字段(运行态/身份),不可 set'}
            if entry.field_schema and key not in entry.field_schema:
                return {'success': False, 'error': f'{key} 不在 {app_id} 的可改字段中(可用: {list(entry.field_schema.keys())})'}
            if entry.field_schema and key in entry.field_schema:
                field_meta = entry.field_schema[key]
                if field_meta.get('type') == 'enum' and 'enum_cls' in field_meta:
                    valid_values = [m.value.value for m in field_meta['enum_cls']]
                    if value not in valid_values:
                        return {'success': False, 'error': f'{key} 值 {value} 不合法(可用: {valid_values})'}
            config.update(key, value)
            config.save()
            return {'success': True, 'app_id': app_id, 'key': key, 'value': value}
        except Exception as e:  # noqa: BLE001
            return {'success': False, 'error': str(e)}
    return set_config


def make_describe_config(backend: SrBackendContext) -> Callable:
    """构造 ``describe_config`` tool(返回结构化 schema,智能体一看就懂)。"""
    async def describe_config(
        app_id: Annotated[str, Field(description="app 配置 id,如 standalone_app")],
        category: Annotated[str | None, Field(description="可选:查特定 category 的 mission_type 合法值(SR 暂无 category 路由,保留参数)")] = None,
        instance_idx: Annotated[int | None, Field(description="实例 idx(idx N→config/0N:idx 1→config/01 账号01;None=当前)")] = None,
        group_id: Annotated[str | None, Field(description="组 id;None=默认")] = None,
    ) -> dict:
        """描述配置结构(可改字段 / 只读字段 / 列表项结构 / 加项示例)。观察类(只读)。

        返回 set_fields(可改 + enum options) + ro_fields(只读) + list_fields
        (item 结构 + add_example)——据此可直接生成正确的 set/add 调用。
        当前配置值用 ``get_config`` 读;不知道有哪些 app_id 时先 ``list_app_configs``。

        Returns:
            ``{success, app_id, description, set_fields, ro_fields, list_fields, note}``。
            ``set_fields``: 字段名 → ``{type, options(下拉合法值, value 为 set 时要传的
            字符串)}``;``ro_fields``: 只读字段名列表;``list_fields[]``: ``{field(列表
            字段名), item_fields(项内字段结构), add_example(可直接改用的加项示例)} ``。
        """
        ctx = backend.ctx
        entry = get_entry(app_id)
        if entry is None:
            return {'success': False, 'error': f'不支持的 app_id: {app_id}'}
        try:
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

            return {
                'success': True,
                'app_id': app_id,
                'description': entry.description,
                'set_fields': set_fields,
                'ro_fields': sorted(ro_fields),
                'list_fields': list_fields,
                'note': '所有 options 的 value 是 set/add 时要传的字符串(非 label);set_fields 与 ro_fields 互斥',
            }
        except Exception as e:  # noqa: BLE001
            return {'success': False, 'error': str(e)}
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
    ) -> dict:
        """列出可改配置的 app_id 清单。观察类(只读)。

        配置路由的首次发现入口:返回每个 config 的 app_id + description +
        supported_ops + item_kind + id_kind——``item_kind`` 说明列表项类型
        (dataclass/str/dict),``id_kind`` 说明项标识字段名,照此生成正确的
        add/delete/update 调用;字段级结构再进 ``describe_config``。

        Returns:
            ``{success, configs[]}``;``configs[]`` 元素: ``{app_id, description,
            supported_ops(支持的操作,如 set/add/delete), item_kind(列表项类型
            dataclass/str/dict), id_kind(项标识字段名)}``。
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
        return {'success': True, 'configs': configs}
    return list_app_configs
