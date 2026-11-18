# 画面 op 与观察域(screen-op)

> 组件 = `operations/cw_screen/`(一画面一 op)+ `obs/`(一屏一解析器)。路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。

## 1. 画面 op(两 node 形态)

- **一画面一 op**,每屏独立类直继承框架 `SrOperation`(无共享基类),**两 node 形态**:观察 node(门 → 显式读屏〔唯一读屏点〕→ CwScreenXxxObs → `report_screen_*_obs` 落状态容器,`kernel/cw_screen_report/` 每屏一文件)→ 决策动作 node(落地复查 → 决策〔状态容器零参读;本帧无动作 = Obs outer_loop 口径〕→ 动作〔零读屏〕→ round_wait 循环无防御上限;**终结动作返回主循环**)。
- 备战(CwScreenPrep)特殊:heavy 观察+接管补采+审计留在观察侧的观察 node;决策动作 = 单动作 while 循环;商店编排(`_open_shop_phase`)。
- 行为规范、上报接口、形态分型、obs 工具箱的完整设计 = `docs/develop/sr_od/application/currency_war/screens/op-layer.md`(画面 op 层设计)+ `screens/README.md`(一画面一文档,能力矩阵与画面文档模板)——该目录后续批次迁移。

## 2. 观察域(obs/)

- **唯一读屏点**:画面 op 观察 node 的显式读屏(备战入口 heavy 观察 `obs/cw_observe_full::observe_full` 为其重型形态);决策环内已登记读屏例外只有两类——①策略显式发出 Obs(in_place) 触发的重观察;②终结分支返回前机械保留证据读(零决策零判效,读数只进缺陷台账)。
- 观察 node 上报 = `report_screen_*_obs` 落状态容器(`kernel/cw_screen_report/` 每屏一文件)。
- **坐标伴随域(用户裁定:观察必须产出坐标)**:观察域识别的「可选/可交互实体」(选项卡/备战栏条目/装备栏条目/晶矿/浮层按钮等),其上报事实一律携带画面坐标(cx/cy 或等价定位)——状态容器字段与 MCP extras 同源可得,坐标不得只存在于 extras。用途 = 动作原语参数面③类(动态坐标显式传参,见 SKILL.md §1.4)的坐标来源:动作 op 按坐标/idx 自取,零内部识别。写端 = 观察上报单点整表覆盖,随帧刷新;**禁逻辑写端**(动作后回填坐标——实体获得时点无画面读数),坐标缺席语义 = 发出面跳过自愈、下帧重派,禁回填猜值。先例:pick 族坐标伴随域(事件线选卡动作按 idx 自取坐标)、`owned_equip_xy`(穿装迁移设计稿 changes/wear-equip-param-surface/)。
- **观察层失约抛错**:决策入口消费的 payload 槽离屏 None = 观察层失约(如 shop payload 离屏)——显式报错,禁策略侧兜底。
- 识别器(`obs/recognizers/`)注册为 `analyze_screen` 的 extras 扩展,MCP 读数与画面 op 观察同一实现(双消费面,见 SKILL.md §1.4)。
- **识别不到就是 bug 停机闸**(与动作域「点完即写」同族规范):商店未识别卡、召唤物/物品未识别等观察域停机见 [guards.md](guards.md)。
