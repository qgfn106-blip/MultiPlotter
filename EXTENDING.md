# MultiPlotter 扩展开发指南

这份文档面向**要在 MultiPlotter 基础上做二次开发**的人：加一个新图层、
改默认样式、换主题、或者基于 `init()` 做自己的封装。

- 只想用现成图层：[README.md](README.md)、[API.md](API.md)
- 只想做动画：[ANIMATION.md](ANIMATION.md)
- 报错排查：[FAQ.md](FAQ.md)
- 配套可运行示例：[`examples/04_custom_layer.py`](examples/04_custom_layer.py)、
  测试 `tests/extension_test.py`

---

## 目录

- [1. 包结构](#1-包结构)
- [2. 一个图层是怎么画出来的](#2-一个图层是怎么画出来的)- [3. 图层契约：LayerSpec](#3-图层契约layerspec)
- [4. 单一注册操作：register_layer()](#4-单一注册操作register_layer)
- [5. 完整实战：新增一个 step 图层](#5-完整实战新增一个-step-图层)
- [6. 绘制处理器怎么写](#6-绘制处理器怎么写)
- [7. 接入 add_layer() / init() / PlotBuilder](#7-接入-add_layer--init--plotbuilder)
- [8. 让新图层支持动画](#8-让新图层支持动画)
- [9. 配置字典的字段契约](#9-配置字典的字段契约)
- [10. 注册时校验：validate_layer_config()](#10-注册时校验validate_layer_config)
- [11. 默认值的单一事实来源](#11-默认值的单一事实来源)
- [12. 样式与主题](#12-样式与主题)
- [13. 样式作用域：context 与 global](#13-样式作用域context-与-global)
- [14. 参数透传](#14-参数透传)- [15. 不用注册表的老路子：重写 _draw_layer](#15-不用注册表的老路子重写-_draw_layer)
- [16. 测试新图层](#16-测试新图层)
- [17. API 稳定性与版本兼容](#17-api-稳定性与版本兼容)
- [18. 常见错误与排查清单](#18-常见错误与排查清单)
- [19. 使用时需要特别注意的地方](#19-使用时需要特别注意的地方)
- [20. 需求清单里的 15 条注意事项](#20-需求清单里的-15-条注意事项)

---

## 1. 包结构

### 1.1 整个仓库

~~~text
MultiPlotter/
├── README.md                   # 快速开始：安装 / 最小 2D、3D、动画示例
├── API.md                      # 所有方法与参数的完整参考（第 0 ~ 27 章）
├── ANIMATION.md                # AnimationPlotter：更新模式、frame_data、保存
├── EXTENDING.md                # 本文件：包结构、图层契约、扩展开发
├── FAQ.md                      # 报错与常见现象排查
├── pyproject.toml              # 依赖声明与打包配置（唯一事实来源）
├── requirements.txt            # 只列运行依赖，方便 pip install -r
├── Multiplotter.py             # 兼容入口：只是转发，没有自己的实现
├── multiplotter/               # 包实现，见 1.2
├── examples/                   # 可直接运行的示例脚本
│   ├── README.md               #   运行方式、脚本与文档的对应关系、图片路径说明
│   ├── _common.py              #   公共工具：sys.path 设置与输出目录
│   ├── 01_quickstart.py        #   二维 / 三维 / 混排 / init() / 主题 / 生命周期
│   ├── 02_convective_heat_transfer.py   # 对流传热算例（README 第 5 章）
│   ├── 03_animation.py         #   三种 update_mode、frame_data、多子图
│   ├── 04_custom_layer.py      #   扩展开发：注册新的 step 图层
│   ├── 05_science_composition.py        # ScienceResult + SciencePlotter
│   └── output/                 #   示例输出（运行后生成）
└── tests/
    ├── images/                 # 文档引用的全部图片与动图
    ├── nohtml/                 # strip_html_docs.py 生成的无 HTML 副本
    ├── generate_*.py           # 生成示例图片与动图
    ├── extend_example.py       # 扩展开发示例（新增 step / trisurf）
    ├── renumber_images.py      # 给图片分配/同步顺序编号（稳定编号）
    ├── strip_html_docs.py      # 生成不含 HTML 的文档副本
    ├── readme_check.py         # 校验全部文档的路径 / 锚点 / 编号 / 表格
    └── *_test.py               # 测试套件，见 16 章
~~~

> 图片、动图与运行输出都放在 `tests/` 和 `examples/output/` 下，
> 包根目录只保留文档、依赖声明、兼容入口和包本身。

### 1.2 包内模块

~~~text
multiplotter/
    __init__.py                 # 公开 API 汇总（from multiplotter import ...）
    core.py                     # MultiPlotter：基础状态、_register_layer、draw
    builder.py                  # PlotBuilder：init() 会话
    styles.py                   # 主题 Theme、rcParams、中文字体
    layout.py                   # 坐标轴范围 / 比例 / 网格 / 三维视角
    validation.py               # 数组、网格、矢量场、表格的校验与规格化
    registries.py               # 图层注册表（单一事实来源）
    draw_2d.py                  # 二维图层：add_* + draw_*
    draw_3d.py                  # 三维图层：add_* + draw_*
    vector_fields.py            # quiver / streamplot / quiver3d / stream3d
    tables.py                   # 表格与单元格样式
    animation.py                # AnimationPlotter
    saving.py                   # 保存路径与动画 writer
    compat.py                   # Matplotlib 版本兼容
    science.py                  # 科研算法与绘图的组合接口
~~~

各模块职责一句话：

| 模块 | 职责 | 改它的时机 |
| --- | --- | --- |
| `core.py` | 跨图层的状态与流程 | 改 `draw()` 的整体行为 |
| `builder.py` | 参数装配（预设合并、数据映射、过滤） | 改 `init()` 的优先级规则 |
| `styles.py` | 主题、rcParams、中文字体 | 改默认外观 |
| `layout.py` | `view` 字典的所有键 | 新增坐标轴级别的设置 |
| `validation.py` | 纯函数校验 | 新增数据形状约定 |
| `registries.py` | kind 的注册与分派 | 新增内置图层 |
| `draw_2d.py` / `draw_3d.py` | 某个 kind 怎么画 | 改某个图层的画法 |
| `vector_fields.py` | 矢量场专用算法（抽稀、RK4） | 改流线积分策略 |
| `tables.py` | 表格样式 | 改表格外观 |
| `animation.py` | 帧调度与保存 | 改动画行为 |
| `saving.py` | 路径解析与 writer | 支持新的容器格式 |
| `compat.py` | 版本差异 | 适配新版 Matplotlib |
| `science.py` | 算法结果的组合绘图 | 加语义化的科研接口 |

关键设计只有一句话：**`add_*` 只登记配置，`draw()` 才真正画图。**

`MultiPlotter` 由四个 Mixin 组合而成，所以每个 `add_*` 都落在它所属的模块里：

~~~python
class MultiPlotter(
    TwoDLayersMixin,        # draw_2d.py
    ThreeDLayersMixin,      # draw_3d.py
    VectorFieldLayersMixin, # vector_fields.py
    TableLayersMixin,       # tables.py
):
    ...
~~~

---

## 2. 一个图层是怎么画出来的

这是理解全部代码的主线：

~~~text
① plotter.add_surface(X, Y, Z, subplot=0, ...)
      │
      ├─ 校验参数（validation.mesh_coordinates / as_1d_array ...）
      ├─ self._register_layer("surface", dimension=3, ...)
      │      └─ 打包成 config 字典 + self.plot_configs.append(config)
      └─ 只是"登记"，不画图
      │
② plotter.add_contour(...)  同样的过程，再 append 一条 config
      │
③ plotter.draw(show=False, save_path=...)
      │
      ├─ theme.rc_context()      ← 主题临时生效（style_scope="context"）
      ├─ plt.figure(...) + fig.add_gridspec(...)
      │
      └─ for subplot_index in range(total_slots):
             ├─ configs = 属于这个 subplot 的所有 config
             ├─ 检查这个 subplot 里 dimension 是否统一（2 维 / 3 维不能混）
             ├─ ax = fig.add_subplot(...)      ← 三维传 projection="3d"
             ├─ ax.set_facecolor(主题面板色)   ← 直接设属性，不靠 rcParams
             │
             ├─ for config in configs:
             │      self._draw_layer(ax, config)   ← 唯一的绘制分派点
             │            └─ handler = DRAW_REGISTRY[config["kind"]]
             │               handler(ax, config)   ← 真正的绘制
             │
             ├─ 汇总公共配置：title / xlabel / ylabel / zlabel
             ├─ layout.apply_view(...)             ← 范围、比例、网格
             └─ 记录 _explicit_limits / _dimension_by_subplot
~~~

两条重要推论：

1. **`add_*` 里绝对不能画图**，否则数据会在 `draw()` 之前就被画到旧画布上；
2. **`config` 字典就是 `add_*` 和绘制处理器之间的唯一契约**，
   字段名改了必须同步改处理器（见第 9 章）。

`_draw_layer()` 现在只有查表，没有 `if/elif`：

~~~python
def _draw_layer(self, ax, config):
    kind = config["kind"]
    dimension = config["dimension"]

    if dimension not in (2, 3):
        raise ValueError(f"dimension必须是2或3，当前为{dimension}")

    handler = self.DRAW_REGISTRY.get(kind)

    if handler is None or self._registered_dimension(kind) not in (None, dimension):
        raise ValueError(f"dimension={dimension}不支持kind={kind}")

    handler(ax, config)
~~~

---

## 3. 图层契约：LayerSpec

一个图层由 :class:`multiplotter.registries.LayerSpec` 完整描述：

| 字段 | 含义 | 必填 |
| --- | --- | --- |
| `kind` | 图层类型名 | ✅ |
| `dimension` | `2` 或 `3` | ✅ |
| `add_method` | `add_*` 方法名 | ✅ |
| `draw_handler` | `(ax, config) -> None` | ✅ |
| `defaults` | `init()` 用的默认参数 | 可空 |
| `passthrough` | 该 kind 专属的透传键 | 可空 |
| `aliases` | `init()` 的别名 | 可空 |
| `animatable` | 是否声明支持动画 | 默认 `True` |
| `description` | 一句话说明 | 可空 |

查看已注册的图层：

~~~python
from multiplotter import MultiPlotter

for spec in MultiPlotter.registered_layers():
    print(f"{spec['kind']:<12} dim={spec['dimension']} "
          f"add={spec['add_method']:<26} aliases={spec['aliases']}")

spec = MultiPlotter.get_layer_spec("surface")
print(spec.dimension, sorted(spec.passthrough), spec.animatable)
~~~

---

## 4. 单一注册操作：register_layer()

新增图层只需要**一次注册**：

~~~python
MultiPlotter.register_layer(
    kind="step",
    dimension=2,
    add_method="add_step",       # 省略时默认 "add_step"
    draw_handler=draw_step,      # (ax, config) -> None
    defaults={...},              # init() 的预设
    passthrough={"where"},       # 该 kind 专属的透传键
    aliases=("stairs",),         # init() 的别名
)
~~~

注册之后，下面这些**全部自动生效**，不用再改任何别的地方：

| 需要改的位置（重构前要改 7 处） | 注册后 |
| --- | --- |
| `SUPPORTED_2D_KINDS` / `SUPPORTED_3D_KINDS` | ✅ 自动 |
| `DRAW_REGISTRY`（绘制分派） | ✅ 自动 |
| `KIND_DEFAULTS`（`init()` 预设） | ✅ 自动 |
| `INIT_KIND_ALIASES`（别名） | ✅ 自动 |
| `PASSTHROUGH_BY_KIND`（透传白名单） | ✅ 自动 |
| `ADD_DISPATCH`（`add_layer()` 分派） | ✅ 自动 |
| `LAYER_SPECS`（完整契约） | ✅ 自动 |

`register_layer()` 会**立即校验契约**（见第 10 章），并且默认拒绝覆盖已注册的 kind：

~~~python
MultiPlotter.register_layer(kind="line", dimension=2, ...)
# ValueError: kind=line 已经注册过了（方法 add_plot）；确实要替换请传 overwrite=True
~~~

> 注册是**类级别**的。直接改 `MultiPlotter` 会影响所有实例；
> 只在子类里注册则只影响该子类。推荐做法是写一个子类：

~~~python
class MyPlotter(MultiPlotter):
    ...

MyPlotter.register_layer(kind="step", dimension=2, ...)

MyPlotter().add_layer(kind="step", ...)     # 可用
MultiPlotter().add_layer(kind="step", ...)  # ValueError: 不支持的kind
~~~

---

## 5. 完整实战：新增一个 step 图层

`add_step` 画阶梯线，对应 `Axes.step()`。

### 5.1 第一步：写绘制处理器

~~~python
def draw_step(ax, config):
    """签名固定为 (ax, config)，不依赖 self。"""
    ax.step(config["x"], config["y"], where=config["where"], **config["kwargs"])
~~~

### 5.2 第二步：写 `add_step`，只做校验 + 组装 config

~~~python
from multiplotter import MultiPlotter
from multiplotter.validation import as_1d_array, check_same_length


class MyPlotter(MultiPlotter):

    def add_step(
        self, x, y, subplot=0, title="", xlabel="X", ylabel="Y",
        label=None, legend=False, legend_kwargs=None, where="pre",
        view=None, **kwargs,
    ):
        x = as_1d_array(x, "x")
        y = as_1d_array(y, "y")
        check_same_length(x, y)

        if where not in ("pre", "post", "mid"):
            raise ValueError(f"where 只能是 pre/post/mid，当前为 {where!r}")

        # 所有 add_* 都必须通过 _register_layer 登记，不要自己 append
        return self._register_layer(
            "step",
            dimension=2,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            view=view,
            kwargs=kwargs,
            x=x,
            y=y,
            where=where,
        )
~~~

`_register_layer()` 会自动补上 `kind` / `dimension` / `subplot` / `title` /
`xlabel` / `ylabel` / `zlabel` / `label` / `legend` / `legend_kwargs` /
`axis` / `view` / `kwargs` 这些公共字段，并把其余键原样写进 config。

### 5.3 第三步：注册

~~~python
MyPlotter.register_layer(
    kind="step",
    dimension=2,
    add_method="add_step",
    draw_handler=draw_step,
    defaults={"linewidth": 2.2, "xlabel": "x", "ylabel": "y",
              "view": {"grid": True}},
    passthrough={"where", "color", "linestyle"},
    aliases=("stairs",),
)
~~~

### 5.4 第四步：用

~~~python
plotter = MyPlotter(ncols=1, figsize_per_plot=(6, 4), dpi=110)

# 三种入口全部可用
plotter.add_step(x, y, subplot=0, where="mid", title="直接调用")
plotter.add_layer(kind="step", x=x, y=y, subplot=0, where="mid")

session = MyPlotter.init(ncols=1, dpi=110)
session.add("stairs", {"x": x, "y": y}, where="mid")   # 别名也生效

fig, axes = plotter.draw(show=False)
~~~

完整可运行版本见 [`examples/04_custom_layer.py`](examples/04_custom_layer.py)。

---

## 6. 绘制处理器怎么写

### 6.1 签名与约束

~~~python
def draw_something(ax, config):
    ...
~~~

三条必须遵守的规则：

1. **只操作传入的 `ax`**，不要碰 `plt.gca()` / `plt.gcf()`（多子图时会画错位置）；
2. **颜色条用 `ax.figure.colorbar(...)`**，不要用 `plt.colorbar()`；
3. **不要缓存跨调用的状态**，每次 `draw()` 都可能传进新的 `ax`。
   确实需要缓存时挂在 `ax` 上（表格就是这么做的，见 `tables.TABLE_CACHE_ATTR`）。

### 6.2 关于 `**kwargs` 与标签

`config["kwargs"]` 是用户透传的原始参数；`label` 是显式参数，**不在里面**。
所以需要图例时要手动补回去：

~~~python
def draw_step(ax, config):
    kwargs = config["kwargs"].copy()

    if config["label"] is not None:
        kwargs["label"] = config["label"]

    ax.step(config["x"], config["y"], where=config["where"], **kwargs)
~~~

### 6.3 需要数值标签时

二维柱状图/直方图的柱顶数值已经有现成实现，直接复用：

~~~python
from multiplotter.draw_2d import add_2d_bar_labels, draw_bar

def draw_my_bar(ax, config):
    bars = ax.bar(config["x"], config["y"], **config["kwargs"])
    add_2d_bar_labels(ax, bars, config["y"], config)   # 读 show_values / value_format
~~~

三维版本是 `multiplotter.draw_3d.add_3d_bar_labels(ax, config)`，
它按 `value_selection` / `max_value_labels` / `value_threshold` 选择要标注的柱子。

### 6.4 需要按维度重新设置样式时

处理器拿不到 `dimension`（它在 `config["dimension"]` 里），
面板颜色已经由 `draw()` 设好，通常不需要重复设置。
如果需要，用：

~~~python
from multiplotter.styles import apply_theme_to_axes

apply_theme_to_axes(ax, config["dimension"], plotter.theme)
~~~

---

## 7. 接入 add_layer() / init() / PlotBuilder

注册之后这三条路径**自动打通**，原理如下。

### 7.1 `add_layer(kind=...)`

~~~python
ADD_DISPATCH = {
    "surface": "add_surface",
    "contour": "add_contour",
    ...
}
~~~

这张表由 `KIND_DEFAULTS` 自动生成（`registries.build_add_dispatch`），
`add_layer()` 只是 `getattr(self, ADD_DISPATCH[kind])(subplot=subplot, **kwargs)`。
没有注册的 kind 会走 `ADD_PLOT_FORWARD_KINDS` 转发给 `add_plot()`，
两者都不是就报 `ValueError: 不支持的kind`。

### 7.2 `init()` / `PlotBuilder`

`init()` 读 `KIND_DEFAULTS`（`(方法名, 默认参数)`）与 `INIT_KIND_ALIASES`：

~~~python
KIND_DEFAULTS["step"] = ("add_step", {"linewidth": 2.2, "xlabel": "x"})
INIT_KIND_ALIASES["stairs"] = "step"
~~~

`PlotBuilder.add("stairs", data, where="mid")` 的合并顺序是：

~~~text
KIND_DEFAULTS  <  init() 的全局样式  <  add() 的参数  <  add() 的 **kwargs
~~~

### 7.3 `PlotBuilder` 的参数过滤

`PlotBuilder.filter_call()` 允许三类键通过：

1. 目标方法签名里存在的参数；
2. `PASSTHROUGH_KEYS`（所有图层通用）；
3. `PASSTHROUGH_BY_KIND[kind]`（该 kind 专属）。

被丢弃的键会记录下来，**打印一次警告**，并可以用
`session.get_dropped_keys()` 查出来 —— 这样「全局样式里写了某个图层用不到的键」
不会让绘图直接报 `TypeError`，但也不会被静默吞掉。

---

## 8. 让新图层支持动画

动画**不需要额外注册**。`AnimationPlotter` 复用父类的 `draw()`，
所以只要新图层能通过 `draw()` 画出来，它就天然可动画化。

### 8.1 让图层能固定坐标轴范围

动画要求每个子图在 `view` 里写死 `xlim` / `ylim`（三维还要 `zlim`），
否则每帧自动缩放会让画面抖动：

~~~python
plotter.add_step(x, y, view={"xlim": (0, 10), "ylim": (-1.5, 1.5)})
~~~

### 8.2 选一种更新模式

| 模式 | 行为 | 适合 |
| --- | --- | --- |
| `"reset"` | 每帧先 `ax.clear()`，回调里重画一切 | 任意类型；通用但稍慢 |
| `"artists"` | 不清空，回调里 `set_data` / `set_offsets` 原地更新 | 折线、散点、箭头；最快 |
| `"append"` | 不清空，每帧把新对象累积上去 | 轨迹、粒子、覆盖层 |

~~~python
def update(ax, frame):
    # reset 模式：框架先 ax.clear()，这里必须重画内容
    ax.clear()
    ax.step(x, y + 0.1 * frame, where="mid")
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.5, 1.5)
    return ax,

plotter.animate(frames=20, update_mode="reset", blit=False,
                update_func=update, save_path="out/step.gif", fps=10)
~~~

### 8.3 多子图时回调会被调用多次

`animate(subplots=[0, 1])` 时，每一帧对**每个**子图都会调用一次回调，
所以回调必须靠传入的 `ax` 判断自己在画哪个子图：

~~~python
def update(ax, frame):
    if ax is plotter.get_axes(0):
        ax.clear(); ax.step(x, y + frame, where="mid"); return ax,
    ax.clear(); ax.plot(x, np.cos(x - frame / 10)); return ax,
~~~

### 8.4 自定义保存格式

`ANIMATION_WRITERS` 决定扩展名到 writer 的映射，
需要支持新容器时覆盖它即可（见 `multiplotter/saving.py`）：

~~~python
class MyAnimatedPlotter(AnimationPlotter):
    ANIMATION_WRITERS = dict(AnimationPlotter.ANIMATION_WRITERS)
    ANIMATION_WRITERS[".webp"] = "pillow"
~~~

---

## 9. 配置字典的字段契约

`config` 是内部契约：**字段名变更必须同步改处理器和测试**。

`_register_layer()` 保证一定存在的公共字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `kind` | str | 图层类型 |
| `dimension` | 2 / 3 | 维度 |
| `subplot` | int | 子图序号 |
| `title` / `xlabel` / `ylabel` / `zlabel` | str | 文案 |
| `label` | str / None | 图例标签 |
| `legend` | bool | 是否画图例 |
| `legend_kwargs` | dict | 图例参数（一定不是 `None`） |
| `axis` | str | `add_plot` 的 `axis` 参数（一定不是 `None`） |
| `view` | dict | 坐标轴设置（一定不是 `None`） |
| `kwargs` | dict | 用户透传的原始参数（一定不是 `None`） |

各图层自己追加的字段（部分）：

| kind | 专属字段 |
| --- | --- |
| `line` / `scatter` / `bar` / `hist` | `x`、`y`、`show_values`、`value_format`、`value_offset`、`value_kwargs` |
| `pie` | `x`（labels）、`y`（values） |
| `heatmap` | `data`、`tick_labels`、`show_heatmap_values`、`heatmap_value_format` |
| `image` | `image` |
| `contour` | `x`、`y`、`data`、`levels`、`line_levels`、`cmap`、`filled`、`alpha`、`contourf_kwargs`、`contour_kwargs`、`clabel`、`clabel_kwargs`、`colorbar`、`colorbar_kwargs` |
| `surface` | `x`、`y`、`data`、`light_enhance`、`colorbar`、`colorbar_kwargs` |
| `line3d` / `scatter3d` | `x`、`y`、`z`、`highlight_zorder` |
| `bar3d` / `hist3d` | `x`、`y`、`z`、`dx`、`dy`、`dz`、`value_selection`、`max_value_labels`、`value_threshold` |
| `quiver` / `streamplot` | `x`、`y`、`u`、`v`、`data`（模长）、`color_by_magnitude`、`vmin`、`vmax` |
| `quiver3d` / `stream3d` | `x`、`y`、`z`、`u`、`v`、`w`、`density` / `field_func`、`bound` |
| `table` | `cell_text`、`n_rows`、`n_cols`、`row_labels`、`col_labels`、`background_color`、`highlight_cells`、`highlight_condition` … |

> 命名约定：**矩阵数据统一放 `data`**（`surface`、`contour`、`heatmap`、
> `quiver` 的模长），**图像统一放 `image`**，**表格文本放 `cell_text`**。
> 这样绘制处理器可以按统一规则取值。

---

## 10. 注册时校验：validate_layer_config()

`register_layer()` 会立即校验契约本身：

~~~python
MultiPlotter.register_layer(kind="", dimension=2, draw_handler=f)
# ValueError: register_layer: kind 必须是非空字符串

MultiPlotter.register_layer(kind="x", dimension=4, draw_handler=f)
# ValueError: register_layer: dimension 必须是 2 或 3，当前为4

MultiPlotter.register_layer(kind="x", dimension=2, draw_handler=None)
# ValueError: register_layer: draw_handler 必须是可调用对象，签名形如 handler(ax, config)
~~~

运行期还可以校验一份具体的 `config`：

~~~python
from multiplotter import validate_layer_config

config = {"kind": "step", "dimension": 2, "subplot": 0, "view": {}}
validate_layer_config("step", config)     # 通过

validate_layer_config("step", {"kind": "step", "subplot": 0})
# ValueError: kind=step 的图层配置缺少必需字段：dimension
~~~

也可以走类方法（使用该子类自己的注册表）：

~~~python
MyPlotter.validate_layer_config("step", config)
~~~

检查项：

- 有 `kind`，且与传入的 kind 一致；
- 有 `dimension`，且是 2 或 3；
- 有 `subplot`，且能转成整数；
- 有 `view`；
- `dimension` 与注册表里该 kind 的维度一致；
- 该 kind 注册了绘制处理器。

如果只是想在开发期自检，可以在 `add_*` 末尾加一行：

~~~python
return self._register_layer("step", dimension=2, ...)
# 开发期自检（正式代码可以去掉，_register_layer 已经保证公共字段）
~~~

---

## 11. 默认值的单一事实来源

重构前同一个默认值散落在 5 个地方：`add_*` 的函数默认参数、`KIND_DEFAULTS`、
`INIT_STYLE_DEFAULTS`、`PASSTHROUGH_KEYS`、README 的预设说明。

现在分成**两件事**，各只有一个来源：

| 内容 | 唯一来源 | 含义 |
| --- | --- | --- |
| `init()` 时用什么预设 | `KIND_DEFAULTS` | 用户没写参数时的取值 |
| 哪些键算「已声明的全局样式键」 | `INIT_STYLE_DEFAULTS` | 用于发现拼写错误 |

### 11.1 为什么 `INIT_STYLE_DEFAULTS` 的值都是 `None`

这是一个**刻意的设计**，也是重构前最容易误解的地方：

~~~python
INIT_STYLE_DEFAULTS = {
    "cell_fontsize": None,     # 注意：None
    "legend": None,
    "cmap": None,
    ...
}
~~~

含义是「**值为 `None` 的全局样式键不会覆盖图层预设**」。
也就是说 `init()` 只合并用户**显式传入**的参数，
没传的键保持 `KIND_DEFAULTS` 里的预设。

这个语义由 `PlotBuilder.__init__` 保证：

~~~python
self.style = {
    key: value
    for key, value in dict(style or {}).items()
    if value is not None          # ← 只保留显式设置过的键
}
~~~

所以 `INIT_STYLE_DEFAULTS` 的实际用途是**键名清单**（尽早发现拼写错误），
而**不是**取值表。想改某个 kind 的默认行为，改 `KIND_DEFAULTS`。

### 11.2 避免文档与代码不一致

`KIND_DEFAULTS` 可以直接读出来对照文档：

~~~python
from multiplotter import MultiPlotter

for kind in ("surface", "bar", "table"):
    method, defaults = MultiPlotter.kind_presets(kind)
    print(kind, "->", method)
    for key, value in sorted(defaults.items()):
        print(f"    {key} = {value!r}")
~~~

测试里也可以加默认值快照（`tests/extension_test.py` 就用了这个思路）：

~~~python
def test_surface_defaults():
    method, defaults = MultiPlotter.kind_presets("surface")
    assert method == "add_surface"
    assert defaults["light_enhance"] is not None
    assert defaults["colorbar"] is True
~~~

---

## 12. 样式与主题

### 12.1 主题对象

~~~python
from multiplotter import Theme, TWO_D_THEME, SURFACE_THEME

print(TWO_D_THEME.facecolor)     # '#FFFFFF'
print(SURFACE_THEME.facecolor)   # '#000000'
print(sorted(TWO_D_THEME.rc)[:5])
~~~

`Theme` 有三个部分：

| 属性 | 作用 |
| --- | --- |
| `rc` | 通过 `matplotlib.rc_context()` 临时生效的 rcParams |
| `facecolor` | 坐标轴面板颜色，**直接设在 Axes 上**（二维白、三维黑） |
| `fonts` | 字体回退链（中文字体在前、西文在后） |

### 12.2 派生一个自定义主题

~~~python
from multiplotter import TWO_D_THEME

mine = TWO_D_THEME.with_overrides(
    {"axes.grid": False, "font.size": 11},
    name="paper",
    facecolor="#FFFFFF",
)
~~~

### 12.3 不用改源码就能换主题

重构前「换主题」只能改 `Multiplotter.py` 里的两个函数；
现在可以用子类包装，上游更新不受影响：

~~~python
from multiplotter import MultiPlotter

class PaperPlotter(MultiPlotter):
    """论文插图：无网格、白底、字号统一放大。"""

    def __init__(self, **kwargs):
        kwargs.setdefault("theme", {
            "axes.grid": False,
            "figure.facecolor": "#FFFFFF",
            "savefig.facecolor": "#FFFFFF",
            "font.size": 12,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "legend.fontsize": 10,
        })
        super().__init__(**kwargs)
~~~

### 12.4 只改单个子图

用 `PlotBuilder.for_subplot()`：

~~~python
session = MultiPlotter.init(ncols=2, dpi=110)
session.for_subplot(1, aspect="equal", legend=True)
~~~

### 12.5 字体

候选字体分三份表，最后拼成 `font.sans-serif` 回退链：

| 常量 | 内容 |
| --- | --- |
| `CHINESE_FONT_CANDIDATES` | 中文字体（Windows / macOS / **Linux** 各平台，25 项） |
| `SANS_FONT_CANDIDATES` | 西文字体（拉丁字母、数字、数学符号，17 项） |
| `FALLBACK_FONTS` | 无条件追加的兜底字体 |

顺序是**中文字体在前、西文字体在后**：matplotlib 会按顺序找第一个
含有该字形的字体，中文放前面才能保证中文不出方框。

~~~python
from multiplotter import (
    CHINESE_FONT_CANDIDATES, SANS_FONT_CANDIDATES, pick_sans_fonts,
)

print(pick_sans_fonts())                  # 当前系统选中的列表（带缓存）
print(pick_sans_fonts(refresh=True))      # 新装字体后强制重新扫描
print(CHINESE_FONT_CANDIDATES)            # 全部中文字体候选
print(SANS_FONT_CANDIDATES)               # 全部西文字体候选
~~~

`pick_chinese_fonts()` 是旧名字，与 `pick_sans_fonts()` 完全等价
（返回的都是完整回退链，而不只是中文字体），保留是为了兼容旧代码。

只有系统里**真实存在**的字体才会被选中，所以同一份代码在三个平台上都能
自动挑到合适的字体。如果系统里一个中文字体都没有，候选表仍会留在列表里 ——
这样用户之后装上字体**不用改代码**就能生效。

想彻底换掉字体，覆盖主题即可：

~~~python
from multiplotter import MultiPlotter

plotter = MultiPlotter(ncols=1, theme={"font.sans-serif": ["My Font"]})
~~~

Linux 各发行版的安装命令见 [README 的字体一节](README.md#字体)。

---

## 13. 样式作用域：context 与 global

### 13.1 默认不碰全局状态

~~~text
draw(style_scope="context")   # 默认
    with theme.rc_context():          # 进入
        fig = plt.figure(...)         # 主题生效
        ...                           # 创建所有 Axes
    # 退出上下文 -> 全局 plt.rcParams 自动恢复
~~~

好处：

- 多个 `MultiPlotter` 对象互不影响；
- 不覆盖用户在外部设置的 Matplotlib 风格；
- 服务端 / 多线程环境没有全局竞态；
- 每个对象真正拥有自己的样式；
- 不调用 `plt.style.use("default")`，不会重置用户的风格。

### 13.2 样式作用域：context 与 global

需要沿用旧行为时显式声明：

~~~python
plotter.draw(show=False, style_scope="global")
~~~

此时框架按维度调用全局样式函数：

~~~python
# multiplotter/styles.py
GLOBAL_STYLE_FUNCTIONS = {
    2: "matplotlib_option",
    3: "matplotlib_surface_option",
}

def apply_global_style(dimension):
    name = GLOBAL_STYLE_FUNCTIONS[3 if int(dimension) == 3 else 2]
    func = globals().get(name)     # ← 通过模块属性查找，可被 monkeypatch
    if callable(func):
        func()
    return name
~~~

**注意**：这里刻意用「模块属性查找」而不是直接引用函数对象，
所以下面这种旧写法仍然有效（`tests/extension_test.py` 就是这么测的）：

~~~python
import multiplotter.styles as styles

original = styles.matplotlib_option

def patched():
    original()
    plt.rcParams["axes.titlesize"] = 20

styles.matplotlib_option = patched
try:
    plotter.draw(show=False, style_scope="global")
finally:
    styles.matplotlib_option = original
~~~

> 包根目录的 `Multiplotter.py` 里也能读到 `matplotlib_option`
> （同一个函数对象的另一个引用），但**打补丁要打到 `multiplotter.styles`**，
> 因为全局样式路径是在那个模块里查找的。

| 作用域 | 生效范围 | 恢复时机 | 适用场景 |
| --- | --- | --- | --- |
| `"context"`（默认） | 创建 Figure / Axes 期间 | `draw()` 返回时 | 绝大多数场景 |
| `"global"` | 整个 Python 进程 | 不恢复（旧行为） | 需要后续代码都沿用该样式 |

### 13.3 优先直接设属性

能用 `Axes` / `Figure` 属性表达的样式就不要走 rcParams。本包已经这样做：

| 样式 | 实现方式 |
| --- | --- |
| 坐标轴面板颜色 | `ax.set_facecolor(...)`（按维度，互不干扰） |
| 网格 | `ax.grid(...)` |
| 坐标轴比例 | `ax.set_aspect(...)` |
| 三维视角 | `ax.view_init(...)` / `ax.set_box_aspect(...)` |
| 图例 | `ax.legend(...)` |
| 范围 | `ax.set_xlim(...)` 等 |

新增图层时请沿用这个原则。

---

## 14. 参数透传

### 14.1 哪些是框架参数，哪些会透传

| 类别 | 例子 | 行为 |
| --- | --- | --- |
| 框架参数 | `view`、`legend`、`legend_kwargs`、`axis`、`title`、`xlabel`、`subplot`、`show_values`、`value_format`、`light_enhance`、`colorbar`、`value_selection`、`mpl_kwargs` | **不会**透传，由框架消费 |
| 通用 artist 样式 | `color`、`alpha`、`linewidth`、`linestyle`、`marker`、`cmap`、`zorder`、`label` | 在 `PASSTHROUGH_KEYS` 里，会透传 |
| 各 kind 专属 | `where`、`drawstyle`、`interpolation`、`rstride`、`pivot`、`wedgeprops` | 在 `PASSTHROUGH_BY_KIND[kind]` 里，会透传 |
| `mpl_kwargs` 的内容 | 任意键，例如 `picker`、`gid`、`sketch_params` | **无条件**透传，见 14.4 |
| 其它 | — | 被丢弃，并打印一次警告 |

### 14.2 为什么要白名单

`add_*` 方法末尾都有 `**kwargs`，如果什么都不管地全透传，
那么「`init(cell_fontsize=11)` 之后画折线图」会在 `ax.plot()` 里报
`AttributeError: Line2D.set() got an unexpected keyword argument 'cell_fontsize'`，
而且报错位置离调用处很远。

白名单让这类问题**降级为警告**，并可用 `get_dropped_keys()` 查出：

~~~python
session = MultiPlotter.init(ncols=1, dpi=110, cell_fontsize=11)
session.add("line", {"x": x, "y": y})
# [PlotBuilder] kind=line 忽略了这些不适用于它的参数：['cell_fontsize']。

print(session.get_dropped_keys())     # {'line': ['cell_fontsize']}
~~~

> 这是「收窄表述」后的行为：**支持透传目标 Matplotlib 方法的大部分常用参数；
> 框架自身参数与少量版本相关参数由 MultiPlotter 单独处理**，
> 具体以方法签名、参数表和本节的注册表为准。

### 14.3 PASSTHROUGH_KEYS 与 PASSTHROUGH_BY_KIND —— 透传白名单

~~~python
from multiplotter import MultiPlotter

# 所有图层通用（artist 级别样式）
print(sorted(MultiPlotter.PASSTHROUGH_KEYS))

# 某个 kind 专属（对应 ax.step / ax.plot_trisurf 的真实参数）
print(sorted(MultiPlotter.PASSTHROUGH_BY_KIND.get("surface", ())))
~~~

新增 kind 时**不要手工维护这两张表**，注册时一起给出即可：

~~~python
MyPlotter.register_layer(
    kind="step", dimension=2, draw_handler=draw_step,
    passthrough={"where", "color", "linestyle"},   # 会写进 PASSTHROUGH_BY_KIND
)
~~~

确实需要给已有 kind 补键时：

~~~python
MultiPlotter.PASSTHROUGH_BY_KIND = dict(MultiPlotter.PASSTHROUGH_BY_KIND)
MultiPlotter.PASSTHROUGH_BY_KIND["line"] = (
    set(MultiPlotter.PASSTHROUGH_BY_KIND.get("line", ()))
    | {"drawstyle", "my_custom_key"}
)
~~~

### 14.4 完全透传：用 `mpl_kwargs` 字典

白名单的好处是能提前发现写错的键，代价是**没登记的新参数会被丢掉**。
如果某个参数确实要原样透传给 Matplotlib，又不想（或来不及）改白名单，
用 `mpl_kwargs` —— 它是框架参数，**内容绕开白名单，直接合并进底层调用**：

~~~python
# 三个入口都支持
plotter.add_plot(kind="line", x=x, y=y, mpl_kwargs={"picker": 5, "gid": "L1"})

plotter.add_layer(kind="line", x=x, y=y, mpl_kwargs={"picker": 5})

session = MultiPlotter.init(ncols=1)
session.add("line", {"x": x, "y": y}, mpl_kwargs={"picker": 5})
~~~

`picker` / `gid` 都是真实的 Matplotlib 参数，但不在白名单里：

| 写法 | 结果 |
| --- | --- |
| `add_plot(..., picker=5)` | ❌ 在 `init()` 会话里会被丢弃并警告 |
| `add_plot(..., mpl_kwargs={"picker": 5})` | ✅ 原样透传给 `ax.plot()` |

三条使用建议：

1. `mpl_kwargs` 的值必须是字典，否则抛 `TypeError`（早期失败，好过画出错图）。
2. 冲突时 **`mpl_kwargs` 优先**：同一个键既在 `**kwargs` 里又在 `mpl_kwargs` 里，
   以 `mpl_kwargs` 为准。
3. 常用参数还是建议登记进白名单 —— `mpl_kwargs` 是逃生舱，
   不是长期方案；它绕过了「拼写错误检查」这层保护。

如果只是想确认「哪些键会被丢」，用 `PlotBuilder` 的记录功能：

~~~python
session.add("line", {"x": x, "y": y}, drawstyle="steps-mid")
print(session.get_records()[-1]["dropped"])   # []  -> 没有被丢
print(session.get_dropped_keys())             # {'line': [...]} 汇总
~~~

### 14.5 版本兼容策略

不同 Matplotlib 版本支持的参数不同（例如
`streamplot(broken_streamlines=...)` 需要 3.6+、`view_init(roll=...)` 需要 3.6+）。
本包不散落 `try/except TypeError`，而是统一走 `multiplotter/compat.py`：

~~~python
from multiplotter.compat import call_with_supported, filter_kwargs, mpl_at_least

call_with_supported(ax.view_init, elev=30, azim=-60, roll=10)   # 低版本自动忽略 roll
kept, dropped = filter_kwargs(ax.streamplot, {"broken_streamlines": True})
print(mpl_at_least(3, 6))
~~~

新增图层时，如果用了「新版本才有」的参数，请用
`call_with_supported()` 调用，并让 `compat` 决定是否警告。
测试请覆盖常见参数（见 `tests/extension_test.py` 的做法）。

---

## 15. 不用注册表的老路子：重写 _draw_layer

如果你不想动注册表（例如只是临时改某个图层的画法），
仍然可以重写 `_draw_layer()`。**先调用 `super()` 处理其它 kind**：

~~~python
class MyPlotter(MultiPlotter):

    def _draw_layer(self, ax, config):
        if config["kind"] == "step":
            ax.step(config["x"], config["y"],
                    where=config["where"], **config["kwargs"])
            return

        super()._draw_layer(ax, config)
~~~

此时 `draw()` 会走你的分支；但如果没在注册表里登记，
`PlotBuilder` 的参数过滤和 `validate_layer_config()` 就认不出这个 kind。
所以**推荐优先用 `register_layer()`**，重写只作为兜底手段。

---

## 16. 测试新图层

### 16.1 三条最低要求

1. **能画出来**：`add_*` -> `draw(show=False)`，检查 `fig.axes` 数量；
2. **校验能拦住错误输入**：错误形状 / 非法枚举值要抛 `ValueError`；
3. **参数被正确透传**：检查 `get_dropped_keys()` 里没有你想要的键。

~~~python
import matplotlib
matplotlib.use("Agg")          # 无界面环境必须

import matplotlib.pyplot as plt
import numpy as np
from multiplotter import MultiPlotter


class MyPlotter(MultiPlotter):
    ...   # add_step + register_layer


def test_step_draws():
    plotter = MyPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    plotter.add_step([0, 1, 2, 3], [0, 1, 4, 9], where="mid")
    fig, axes = plotter.draw(show=False)
    assert len(fig.axes) == 1
    plt.close("all")


def test_step_rejects_bad_where():
    plotter = MyPlotter(ncols=1)
    try:
        plotter.add_step([0, 1], [0, 1], where="nope")
    except ValueError:
        return
    raise AssertionError("非法 where 应该抛 ValueError")


def test_step_passthrough():
    session = MyPlotter.init(ncols=1, dpi=50)
    session.add("step", {"x": [0, 1], "y": [0, 1]}, where="post")
    assert "where" not in session.get_dropped_keys().get("step", [])
~~~

### 16.2 契约自检

~~~python
def test_layer_spec():
    spec = MyPlotter.get_layer_spec("step")
    spec.validate()                       # 契约自洽
    assert spec.dimension == 2
    assert spec.add_method == "add_step"
    assert callable(spec.draw_handler)
~~~

### 16.3 动画

自定义 kind 只要在 `view` 里固定了范围，就能直接动画化：

~~~python
def test_step_animation():
    plotter = MyPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=50)
    plotter.add_step([0, 1, 2, 3], [0, 1, 4, 9],
                     view={"xlim": (0, 3), "ylim": (-1, 10)})
    plotter.draw(show=False)

    def update(ax, frame):
        ax.clear()
        ax.step([0, 1, 2, 3], [0, 1, 4, 9 + frame], where="mid")
        ax.set_xlim(0, 3)
        ax.set_ylim(-1, 10)
        return ax,

    plotter.animate(frames=5, update_mode="reset", blit=False,
                    update_func=update, save_path="_out/step.gif", fps=5)
~~~

### 16.4 跑全量测试

~~~bash
python tests/library_smoke_test.py     # 全部 add_* 示例的冒烟测试
python tests/init_test.py              # init() / PlotBuilder
python tests/field_table_test.py       # 矢量场与表格
python tests/extension_test.py         # 扩展开发
python tests/anim_api_test.py          # 动画
python tests/readme_check.py           # 文档图片路径 / 锚点 / 表格
~~~

---

## 17. API 稳定性与版本兼容

### 17.1 API 分层

| 标记 | 含义 | 可以依赖吗 |
| --- | --- | --- |
| **公开 API** | `from multiplotter import ...` 导出的名字 | ✅ 稳定，遵循语义化版本 |
| **扩展 API** | 注册表、Mixin、`Theme`、`register_layer()`、`validate_layer_config()`、`compat` | ✅ 稳定，扩展开发请用它 |
| **内部 API** | 以 `_` 开头的属性/方法、`config` 字段、`_register_layer`、`_draw_layer` | ⚠️ 可能随版本变化 |
| **实验性 API** | `multiplotter.science`（`ScienceResult` / `SciencePlotter` / `convective_heat_transfer`） | ⚠️ 接口可能调整 |

#### 公开 API

~~~python
from multiplotter import (
    MultiPlotter, AnimationPlotter, PlotBuilder,
    Theme, TWO_D_THEME, SURFACE_THEME, resolve_theme,
    pick_sans_fonts, pick_chinese_fonts,
    CHINESE_FONT_CANDIDATES, SANS_FONT_CANDIDATES,
    matplotlib_option, matplotlib_surface_option,
    DRAW_REGISTRY, LAYER_SPECS, LayerSpec, KIND_DEFAULTS, INIT_KIND_ALIASES,
    PASSTHROUGH_KEYS, PASSTHROUGH_BY_KIND, SUPPORTED_2D_KINDS,
    SUPPORTED_3D_KINDS, SUPPORTED_KINDS, ADD_DISPATCH,
    describe_layers, make_layer_spec, validate_layer_config,
    get_unique_filename, resolve_save_path, save_figure,
    resolve_animation_writer,
    MATPLOTLIB_MIN, MATPLOTLIB_TESTED, mpl_version, mpl_at_least,
    SciencePlotter, ScienceResult, convective_heat_transfer,
)
~~~

稳定的实例方法：`add_plot` / `add_pie` / `add_correlation_heatmap` /
`add_contour` / `add_surface` / `add_line3d` / `add_scatter3d` / `add_bar3d` /
`add_hist3d` / `add_quiver` / `add_streamplot` / `add_quiver3d` /
`add_stream3d` / `add_table` / `add_layer` / `draw` / `get_axes` / `clear` /
`close` / `init` / `kind_presets` / `register_layer` / `registered_layers` /
`get_layer_spec` / `validate_layer_config`，以及 `AnimationPlotter.animate` /
`stop_animation` / `get_animation` / `get_animation_params`。

#### 可以覆盖的类属性

| 属性 | 覆盖后效果 |
| --- | --- |
| `KIND_DEFAULTS` | 改 `init()` 的预设 |
| `INIT_KIND_ALIASES` | 改 / 加别名 |
| `PASSTHROUGH_KEYS` / `PASSTHROUGH_BY_KIND` | 改透传白名单 |
| `SUPPORTED_2D_KINDS` / `SUPPORTED_3D_KINDS` | 改 kind 集合（推荐改用 `register_layer`） |
| `DRAW_REGISTRY` | 换某个 kind 的绘制处理器 |
| `ADD_DISPATCH` | 改 `add_layer()` 的分派（推荐改用 `register_layer`） |
| `STYLE_SCOPES` | 改允许的 `style_scope` |
| `ANIMATION_WRITERS`（`AnimationPlotter`） | 加容器格式 |
| `UPDATE_MODES`（`AnimationPlotter`） | 改帧更新模式 |

#### 内部 API（不要依赖）

- 所有 `_` 前缀的方法：`_register_layer` / `_draw_layer` / `_get_dimension` /
  `_apply_view_with_record` / `_apply_subplot_*` / `_animation_frame` 等；
- `config` 字典的字段名（见第 9 章）；
- `_explicit_limits` / `_dimension_by_subplot` / `_subplot_axes` / `_figure`
  这些实例属性。

> 重写 `_draw_layer()` 仍然可用（见第 15 章），但请先 `super()`，
> 并且在升级时留意这一层的签名变化。

### 17.2 Matplotlib 版本支持范围

| 项 | 值 |
| --- | --- |
| 声明最低版本 | `matplotlib >= 3.5`（`multiplotter.MATPLOTLIB_MIN`） |
| 已测试版本 | 3.5 / 3.6 / 3.7 / 3.8 / 3.9 / 3.10（`MATPLOTLIB_TESTED`） |
| 运行期查询 | `multiplotter.mpl_version()`、`multiplotter.mpl_at_least(3, 6)` |

已知的版本差异（都由 `compat.py` 处理）：

| 参数 | 需要版本 | 低版本行为 |
| --- | --- | --- |
| `streamplot(broken_streamlines=...)` | 3.6+ | 忽略并打印提示 |
| `view_init(roll=...)` | 3.6+ | 忽略 `roll` |
| `bar_label()` | 3.4+ | 已在最低版本之上 |
| `set_box_aspect()` | 3.3+ | 已在最低版本之上 |

### 17.3 语义化版本与新增图层

- **补丁版本**：修 bug、修文档，不改行为；
- **次版本**：新增图层 / 新增参数 / 新增主题，保持向后兼容；
- **主版本**：重命名或删除公开 API、改 `config` 字段。

**新增图层是否需要同步测试？** 需要。至少覆盖：

1. `add_*` -> `draw()` 能出图；
2. 非法输入抛 `ValueError`；
3. `register_layer()` 的契约自洽（`spec.validate()`）；
4. 参数透传（`get_dropped_keys()`）；
5. 如果声明 `animatable=True`，加一个最小动画测试。

---

## 18. 常见错误与排查清单

| 现象 | 原因 | 改法 |
| --- | --- | --- |
| `ValueError: 不支持的kind：step` | 只写了 `add_step`，没有注册 | `register_layer(kind="step", ...)` |
| `ValueError: dimension=2不支持kind=step` | `dimension` 写反了（`register_layer` 传 3，`_register_layer` 传 2） | 两处保持一致 |
| `ValueError: kind=step 的图层配置缺少必需字段：dimension` | 自己 `append` 了 config，没走 `_register_layer` | 改用 `_register_layer` |
| `ValueError: register_layer: draw_handler 必须是可调用对象` | 传了模块名或字符串 | 传函数对象 `draw_step` |
| `TypeError: 'set' object is not ...` / 白名单报错 | `passthrough` 传成了字符串 `"where"` | 传集合 `{"where"}` |
| `KeyError: 'where'` 出现在处理器里 | `add_*` 没有把 `where` 写进 config | 在 `_register_layer(..., where=where)` 里补上 |
| 图例不显示 | `label` 没手动加回 `kwargs` | 见第 6.2 节 |
| 颜色条画到别的子图上 | 用了 `plt.colorbar()` | 改用 `ax.figure.colorbar(..., ax=ax)` |
| `[PlotBuilder] kind=step 忽略了这些参数` | 键不在签名也不在白名单 | 加进 `passthrough`，或确认是不是写错了 |
| 新增 kind 后 `init()` 报「不支持」 | 只注册了 handler，没给 `defaults` | `register_layer(defaults={...})` |
| 自定义图层动画不动 | 回调里没 `ax.clear()`（reset 模式） | 见第 8.2 节 |
| 动画报「必须固定坐标轴范围」 | 没在 `view` 里写 `xlim` / `ylim` | 加 `view={"xlim": ..., "ylim": ...}` |
| 二维三维混在一个 subplot | 一个 subplot 只能一种维度 | 拆到不同 subplot |
| `plt.rcParams` 被改掉了 | 用了 `style_scope="global"` | 去掉它，或接受该副作用 |
| 全局样式补丁不生效 | 补丁打在了 `Multiplotter` 模块上 | 打到 `multiplotter.styles`（第 13.2 节） |

### 自查流程

改完代码按顺序跑一遍：

~~~bash
python -c "import multiplotter; print(multiplotter.__version__)"   # 1. 能导入
python tests/extension_test.py                                     # 2. 扩展契约
python tests/library_smoke_test.py                                 # 3. 所有图层能出图
python tests/init_test.py                                          # 4. init() 预设
python tests/anim_api_test.py                                      # 5. 动画
python tests/readme_check.py                                       # 6. 文档路径/锚点
~~~

---

## 附：最小可复制模板

### 纯绘图版（注册一个新图层）

~~~python
# -*- coding: utf-8 -*-
"""新增一个 step 图层（二维阶梯线）。"""

import matplotlib
matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt

from multiplotter import MultiPlotter
from multiplotter.validation import as_1d_array, check_same_length


# ---------------- 1. 绘制处理器：签名固定 (ax, config) ----------------
def draw_step(ax, config):
    kwargs = config["kwargs"].copy()

    if config["label"] is not None:
        kwargs["label"] = config["label"]

    ax.step(config["x"], config["y"], where=config["where"], **kwargs)


# ---------------- 2. 子类：写 add_step + 注册 ----------------
class StepPlotter(MultiPlotter):

    def add_step(
        self, x, y, subplot=0, title="", xlabel="X", ylabel="Y",
        label=None, legend=False, legend_kwargs=None, where="pre",
        view=None, **kwargs,
    ):
        x = as_1d_array(x, "x")
        y = as_1d_array(y, "y")
        check_same_length(x, y)

        if where not in ("pre", "post", "mid"):
            raise ValueError(f"where 只能是 pre/post/mid，当前为 {where!r}")

        return self._register_layer(
            "step",
            dimension=2,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            view=view,
            kwargs=kwargs,
            x=x,
            y=y,
            where=where,
        )


StepPlotter.register_layer(
    kind="step",
    dimension=2,
    add_method="add_step",
    draw_handler=draw_step,
    defaults={"linewidth": 2.2, "xlabel": "x", "ylabel": "y"},
    passthrough={"where", "color", "linestyle"},
    aliases=("stairs",),
)


# ---------------- 3. 三种入口都能用 ----------------
if __name__ == "__main__":
    x = np.array([0, 1, 2, 3, 4])
    y = np.array([0, 1, 4, 2, 3])

    plotter = StepPlotter(ncols=1, figsize_per_plot=(6, 4), dpi=100)
    plotter.add_step(x, y, where="mid", title="step", label="阶梯", legend=True)
    plotter.draw(show=False, save_path="_out/step.png")

    session = StepPlotter.init(ncols=1, dpi=100, legend=True)
    session.add("stairs", {"x": x, "y": y}, where="post")
    session.draw(show=False)

    plt.close("all")
~~~

### 需要动画时

把基类换成 `AnimationPlotter` 即可（`register_layer` 的调用完全不变）：

~~~python
from multiplotter import AnimationPlotter


class AnimatedStepPlotter(AnimationPlotter):
    ...   # 同上的 add_step


AnimatedStepPlotter.register_layer(...)   # 同样的注册

plotter = AnimatedStepPlotter(ncols=1, figsize_per_plot=(6, 4))
plotter.add_step(x, y, view={"xlim": (0, 4), "ylim": (-1, 6)})   # 必须固定范围
plotter.draw(show=False)

plotter.animate(
    frames=20, update_mode="reset", blit=False, fps=10,
    update_func=lambda ax, frame: (
        ax.clear(),
        ax.step(x, y + 0.1 * frame, where="mid"),
        ax.set_xlim(0, 4), ax.set_ylim(-1, 6), ax,
    )[-1],
    save_path="_out/step.gif",
)
~~~

### 选择哪个基类

| 需求 | 基类 |
| --- | --- |
| 只要静态出图 | `MultiPlotter` |
| 需要动画 | `AnimationPlotter`（含 `MultiPlotter` 的全部能力） |
| 想改动画默认行为（如新增容器格式） | `AnimationPlotter` + 覆盖 `ANIMATION_WRITERS` |
| 想固定一套论文/报告风格 | `MultiPlotter` 子类 + `theme=` |
| 想把算法结果组合成多子图 | `multiplotter.science.SciencePlotter`（实验性） |

---

## 19. 使用时需要特别注意的地方

这一节汇总**容易踩坑、且从签名上看不出来**的行为。
每一条都写明「现象 -> 原因 -> 怎么做」。

### 19.1 `add_*` 只登记，不画图

~~~python
plotter.add_plot(kind="line", x=x, y=y)
# 此时画布上什么都没有 —— 这是设计如此
fig, axes = plotter.draw(show=False)      # 到这一步才真正绘制
~~~

因此不要在 `add_*` 之后、`draw()` 之前用 `plt.gca()` 去取坐标轴，那时还没有坐标轴。

### 19.2 一个 subplot 只能有一种维度

二维和三维图层放进同一个 `subplot` 会直接抛 `ValueError`：

~~~python
plotter.add_surface(X, Y, Z, subplot=0)
plotter.add_plot(kind="line", x=x, y=y, subplot=0)   # ValueError
~~~

拆到不同 subplot 即可。三维子图内部也**不能**混排二维图层。

### 19.3 动画必须固定坐标轴范围

`animate()` 默认要求每个参与动画的子图都在 `view` 里写死 `xlim` / `ylim`
（三维还要 `zlim`），否则报错。原因是每帧自动缩放会让画面抖动：

~~~python
plotter.add_plot(kind="line", x=x, y=y,
                 view={"xlim": (0, 6.3), "ylim": (-1.5, 1.5)})
~~~

三种解法：写进 `view`；在 `animate(xlim=..., ylim=...)` 里给；
或传 `allow_auto_limits=True` 用当前显示范围兜底。

### 19.4 `update_mode` 决定回调里要不要 `clear()`

| 模式 | 回调里要做什么 |
| --- | --- |
| `"reset"` | 框架已 `ax.clear()`，**必须重画**标题、范围、比例 |
| `"artists"` | 不要 `clear()`，用 `set_data()` / `set_offsets()` 原地更新 |
| `"append"` | 不要 `clear()`，每帧返回新对象让它累积 |

`"reset"` 模式下如果用 `blit=True`，回调必须返回真正被重绘的 artist，
否则 `blit` 会把画面画花（框架有自检，会给出提示）。

### 19.5 多子图动画时回调会被调用多次

`animate(subplots=[0, 1])` 时每帧对**每个**子图各调用一次回调，
所以回调要靠传入的 `ax` 判断自己在画哪个子图，不能假设只被调用一次。

### 19.6 回调里的 `plt.gca()` 可能指向别的画布

框架管理自己的 Figure，`plt.gca()` 取到的不一定是当前子图。
**只用传入的 `ax`**：

~~~python
def update(ax, frame):        # ✅
    ax.clear(); ...

def update(frame):            # ❌ 不要用 plt.gca()
    plt.gca().clear(); ...
~~~

### 19.7 `frame_data` 的键必须和 `frames` 对得上

`frame_data` 是字典时，帧号取自它的键。传了 `frames=60` 但字典只有 24 帧会报
`ValueError`；给 `frames` 一个序列但字典里缺键会报 `KeyError`。
最省事的写法是只传 `frame_data`，让框架自动取键。

另外，回调的第二个参数在给了 `frame_data` 时是**那一帧的数据**，不是帧号。

### 19.8 `draw()` 默认不修改全局 `plt.rcParams`

主题通过 `rc_context()` 临时生效。想沿用旧行为要显式写
`style_scope="global"`。反过来，如果你依赖「`draw()` 之后全局样式被改掉」，
升级后需要显式声明。

### 19.9 打补丁要打到 `multiplotter.styles`

全局样式函数是在 `multiplotter.styles` 模块里按属性名查找的，
所以 monkeypatch 必须打在那个模块上：

~~~python
import multiplotter.styles as styles      # ✅
styles.matplotlib_option = my_version

import Multiplotter                        # ❌ 改这个模块的同名引用无效
~~~

### 19.10 保存用 `fig.savefig()`，不要用 `plt.savefig()`

同时存在多个 Figure 时 `plt.savefig()` 会存错图。
框架内部已经统一用 `fig.savefig()`，手动保存时也请照做。

> **关于需求原文的表述**：`重构要求.txt` 第 (5) 条的小标题写的是
> 「使用 `plt.savefig()` 而不是 `fig.savefig()`」，但它紧接着列出的理由
> （多个 Figure 时保存错图、受当前 Figure 影响、测试环境不稳定、
> 不利于线程安全与对象化管理）恰恰都是 `plt.savefig()` 的缺点。
> 也就是说标题与理由互相矛盾，理由才是真正要解决的问题。
> 因此这里按**理由**的意图实现：统一使用 `fig.savefig()`。

### 19.11 `clear()` 默认不关闭画布

`clear()` 只清图层配置；`close()` 只关画布；两者都不做时 Figure 会一直留着。
循环出图请用 `draw(close_previous=True)`，或 `with MultiPlotter(...) as p:`。

### 19.12 `**kwargs` 有白名单，不是全部透传

框架参数（`view`、`legend`、`show_values`、`colorbar`、`light_enhance`…）
不会被透传；其余键要在目标方法签名或 `PASSTHROUGH_KEYS` /
`PASSTHROUGH_BY_KIND` 里。不在白名单里的键会被**丢弃并打印一次警告**，
可用 `PlotBuilder.get_dropped_keys()` 查出。

> 反过来说：白名单里的键也不保证目标 artist 一定接受。
> 例如 `cmap` 在通用白名单里（散点、热力图需要），
> 但 `ax.plot()` 的 `Line2D` 不接受 `cmap`，会抛 `AttributeError`。
> 所以「只给真正需要它的图层写这个参数」最稳妥。

### 19.13 部分 `init()` 预设到不了目标方法（已知问题）

`KIND_DEFAULTS` 里有 8 个预设键因为不在方法签名、也不在白名单里，
**实际不会生效**（重构前就是这样，`tests/defaults_test.py` 已登记）：

| kind | 失效的预设键 | 实际表现 |
| --- | --- | --- |
| `heatmap` | `colorbar`、`heatmap_text_size` | 颜色条仍会出现（绘制函数有兜底），文字大小退回 9 而不是 8 |
| `image` | `colorbar` | **不出现**颜色条（兜底是 `False`），文档里写的默认 `True` 未生效 |
| `surface` | `edgecolor` | 用 matplotlib 默认描边 |
| `bar3d` / `hist3d` | `edgecolor` | 同上 |
| `scatter3d` | `s`、`depthshade` | 点的大小与深度着色用 matplotlib 默认值 |

想让某个键生效，注册时把它写进 `passthrough`，或直接在 `add_*` 里显式传：

~~~python
session.add("scatter3d", {"x": x, "y": y, "z": z}, s=40, depthshade=True)
~~~

### 19.14 `init()` 的全局样式只认显式传入的键

`INIT_STYLE_DEFAULTS` 的值大多是 `None`，含义是「没传就不覆盖图层预设」。
所以 `init()` 不会把某个 kind 的预设重置成 `None`，
想改默认行为要改 `KIND_DEFAULTS`（或 `register_layer(defaults=...)`）。

### 19.15 `correlation` 不是真正的图层

`init(kind="correlation")` 是语法糖，最终走
`add_correlation_heatmap()` -> `add_plot(kind="heatmap")`。
它没有自己的绘制处理器，也不会出现在 `plot_configs` 里，
因此不能用 `validate_layer_config("correlation", ...)`。
这类 kind 由 `INIT_ONLY_KINDS` 标记，`LayerSpec.init_only` 为 `True`。

### 19.16 表格的 `cell_text` 必须是二维

一维列表会被当成「一行」或报形状错误，请包一层：`[[a, b], [c, d]]`。
`highlight` 的行列下标也是从 0 开始，越界会抛 `ValueError`。

### 19.17 曲面/等高线的 `z` 形状是 `(len(y), len(x))`

~~~text
x.shape == (100,)   y.shape == (80,)   ->   z.shape == (80, 100)
~~~

传反了会报形状不匹配。一维 `x` / `y` 会被自动 `meshgrid`。

### 19.18 中文是方框时先查字体

主题会自动跳过系统里没有的中文字体。若全部候选都缺失，中文就会显示成方框，
需要在操作系统层面装字体（见 [README 的字体一节](README.md#字体)），
装完重启 Python / Jupyter kernel（或调用 `pick_sans_fonts(refresh=True)`）。

### 19.19 注册是类级别的，但模块级导出会跟着一起变

`register_layer()` 改的是注册表对象本身（就地更新），所以下面三处
**始终指向同一份数据**，不会出现「一处注册、另一处看不到」：

~~~python
from multiplotter import MultiPlotter, DRAW_REGISTRY
import multiplotter, multiplotter.registries as registries

MultiPlotter.register_layer(kind="step", dimension=2, ...)

"step" in MultiPlotter.DRAW_REGISTRY       # True
"step" in DRAW_REGISTRY                    # True（同一个对象）
"step" in multiplotter.LAYER_SPECS         # True
"step" in registries.KIND_DEFAULTS         # True
~~~

不可变的 `SUPPORTED_2D_KINDS` / `SUPPORTED_3D_KINDS` / `SUPPORTED_KINDS`
（`frozenset` 没法就地改）也会被同步到这三处。
`tests/defaults_test.py` 里的「注册表三方一致」用例守着这个不变式。

> 反过来要注意：注册会影响**所有** `MultiPlotter` 实例。
> 想隔离就写在子类里，或在测试里用 `overwrite=True` 覆盖后再改回来。

### 19.20 重复注册同名 kind 会被拒绝

默认 `overwrite=False`，重复注册抛 `ValueError`。
这是为了防止误伤内置图层（例如把 `line` 的绘制处理器覆盖掉）。

---

## 20. 需求清单里的 15 条注意事项

`重构要求.txt` 第 (12) 条列出了「使用时需要特别注意的地方」15 条。
下面逐条对照，写明**结论**和**在哪一节展开**。
前 4 条与第 6 条在 [第 19 章](#19-使用时需要特别注意的地方) 已经展开，
这里只补上第 19 章没单独讲的几条。

| # | 注意事项 | 结论 | 详见 |
| --- | --- | --- | --- |
| 1 | 同一 subplot 不要混用二维和三维图层 | 会直接抛 `ValueError`，请拆到不同 subplot | [19.2](#192-一个-subplot-只能有一种维度) |
| 2 | `add_*()` 只登记配置，绘制要等 `draw()` | 设计如此，别在中间取坐标轴 | [19.1](#191-add_-只登记不画图) |
| 3 | 动画 `reset` 模式会清空坐标轴，回调必须重画 | 标题、范围、比例都要重设 | [19.4](#194-update_mode-决定回调里要不要-clear) |
| 4 | `artists` 模式要拿到正确的 artist 并返回 | 用 `set_data()` 原地更新并 `return` 它 | [19.4](#194-update_mode-决定回调里要不要-clear) |
| 5 | 三维动画通常不能 `blit=True` | 框架**自动**降级为 `blit=False` 并打印提示 | 见下 20.1 |
| 6 | 数据变化大时要显式设 `xlim/ylim/zlim` | 否则范围跳动或直接报错 | [19.3](#193-动画必须固定坐标轴范围) |
| 7 | `init()` 里未列入白名单的参数可能只警告不报错 | 用 `get_dropped_keys()` 查 | [19.12](#1912-kwargs-有白名单不是全部透传) |
| 8 | `**kwargs` 要区分框架参数与 Matplotlib 参数 | 框架参数不会被透传 | [19.12](#1912-kwargs-有白名单不是全部透传) |
| 9 | 多个绘图对象并存时注意全局状态 | 本包已隔离 rcParams，但仍建议**一个对象一段生命周期** | 见下 20.2 |
| 10 | 重复 `draw()` 是否关闭旧 Figure | 默认**不关**，用 `close_previous=True` | [19.11](#1911-clear-默认不关闭画布) |
| 11 | 表格 / 三维流线 / 高密度矢量场耗资源 | 有明确的规模上限与降规模手段 | 见下 20.3 |
| 12 | 版本相关参数不能假设到处可用 | 版本差异集中在 `compat.py`，会降级并提示 | 见下 20.4 |
| 13 | 新增图层不能只改 `SUPPORTED_*_KINDS` | 现在只需一次 `register_layer()` | 见下 20.5 |
| 14 | `config` 字段是内部契约，改名要同步改测试 | 用 `validate_layer_config()` 先验证 | 见下 20.6 |
| 15 | 不建议把单文件直接当稳定公共库发布 | 已经完成拆分，见下方状态说明 | 见下 20.7 |

### 20.1 三维动画的 blit

三维坐标轴（`Axes3D`）不支持 `blit`。传 `blit=True` 不会报错，
框架会**自动改成 `False`** 并打印一行提示：

~~~text
[AnimationPlotter] Axes3D 不支持 blit，已自动改为 blit=False
~~~

所以三维动画会比二维慢一些，这是 matplotlib 的限制，不是本包的问题。
想让三维动画快一点，可以降低 `dpi`、减少帧数、或把网格调粗。

### 20.2 多个绘图对象并存

本包**已经不再修改全局 `plt.rcParams`**（见 [19.8](#198-draw-默认不修改全局-pltrcparams)），
所以多个 `MultiPlotter` 对象之间不会互相改样式，
每个对象的主题是实例级的，互不影响。

但仍有两点要注意：

1. **`pyplot` 的当前 Figure 是全局的**。所以框架内部一律用
   `fig.savefig()` 而不是 `plt.savefig()`（见 [19.10](#1910-保存用-figsavefig不要用-pltsavefig)），
   你手动操作时也请用返回的 `fig` / `axes`，不要用 `plt.gca()`。
2. **一个对象建议走完一段完整生命周期**（`draw()` -> 用完 -> `close()`），
   而不是长期持有几十个对象。长期运行时用
   `draw(close_previous=True)` 或 `with MultiPlotter(...) as p:` 自动回收。

多线程 / 服务端环境下，`matplotlib` 本身不是线程安全的：
请**每个线程各自创建 Figure**，不要在多个线程间共享同一个 `MultiPlotter`。

### 20.3 资源消耗

下面这些用法会明显吃内存和 CPU，规模要自己控制：

| 用法 | 消耗来源 | 建议 |
| --- | --- | --- |
| 大表格 `add_table()` | 每个单元格是一个 `Text` 对象，渲染代价随行列数**乘积**增长 | 超过 ~50×20 就先汇总，别整表塞进去 |
| 三维流线 `add_stream3d()` | 每条流线都要 RK4 逐步积分，还会做深度排序 | 用 `n_seeds` / `step_size` / `max_steps` 控制条数与长度 |
| 高密度矢量场 `add_quiver()` / `add_quiver3d()` | 箭头数量是网格点数，稠密网格会画出几万个箭头 | 用 `density` 抽稀，或先把 `u` / `v` 降采样 |
| 细网格 `add_surface()` | 每个面片一个多边形，还叠加光照计算 | 网格取 100×100 以内；`light_enhance` 会额外算一次 |
| 动图保存 | 每帧都要完整渲染，GIF 还要逐帧编码 | 降 `dpi` / `fps` / `frames`，或用 `update_mode="artists"` |

### 20.4 版本相关参数

不同 `matplotlib` 版本支持的参数并不一致，
所以**不要假设某个参数在所有环境都可用**。
本包的处理方式是把版本差异集中到 `multiplotter/compat.py`：

~~~python
from multiplotter import mpl_version, mpl_at_least, MATPLOTLIB_MIN

mpl_version()              # 当前版本，例如 (3, 10, 6)
mpl_at_least(3, 7)         # 是否 >= 3.7
MATPLOTLIB_MIN             # 支持的最低版本 (3, 5)
~~~

框架在调用底层方法前会用 `filter_kwargs()` / `call_with_supported()`
过滤掉当前版本不支持的参数，并给出一行提示。
支持范围与策略见 [17.2 节](#172-matplotlib-版本支持范围)。

### 20.5 新增图层：从「改七处」到「注册一次」

早期版本新增一个图层要同步改 `SUPPORTED_*_KINDS`、`KIND_DEFAULTS`、
`DRAW_REGISTRY`、`ADD_DISPATCH`、`PASSTHROUGH_BY_KIND`、
`INIT_KIND_ALIASES` 等多处，漏一处就出问题。
现在**只需要一次 `register_layer()`**，它会一次性更新全部注册表：

~~~python
MultiPlotter.register_layer(
    kind="step", dimension=2, add_method="add_step",
    draw_handler=draw_step, defaults={"linewidth": 2.2},
    passthrough={"where"}, aliases=("stairs",),
)
~~~

详见 [第 4 章](#4-单一注册操作register_layer) 与
[第 5 章](#5-完整实战新增一个-step-图层) 的完整实战。

### 20.6 `config` 是内部契约

`draw()` 与各个 `draw_*` 处理器之间靠 `config` 字典传递数据，
它是**内部契约**：字段名一旦改动，所有读取该字段的处理器和测试都要同步改。

新增 / 修改图层时，先用 `validate_layer_config()` 确认契约完整：

~~~python
MultiPlotter.validate_layer_config("step", config)
# 检查 kind / dimension / subplot / view 齐不齐、维度对不对、
# 该 kind 有没有绘制处理器；缺什么就抛什么。
~~~

字段清单见 [第 9 章](#9-配置字典的字段契约)。

### 20.7 关于「当作稳定公共库发布」

需求里提到「不建议把这个单文件直接当作稳定公共库发布，
最好先完成模块拆分、测试补齐和 API 收敛」。这三件事的当前状态：

| 事项 | 状态 |
| --- | --- |
| 模块拆分 | ✅ 已按需求 (1) 的结构拆成 `multiplotter/` 包（见 [第 1 章](#1-包结构)） |
| 测试补齐 | ✅ 6 套测试（`tests/*_test.py`）+ `readme_check.py`，见 [第 16 章](#16-测试新图层) |
| API 收敛 | ✅ 已划出公开 / 扩展 / 实验性三层，见 [17.1](#171-api-分层) |
| 版本号 | `0.3.0`（尚未到 1.0，实验性 API 仍可能调整） |
| 打包 | ✅ `pyproject.toml` 声明依赖与打包，可直接 `pip install -e .` |

仍然**不建议**直接依赖 `multiplotter.science` 这类实验性 API 写生产代码，
它的接口还可能调整（见 [17.1](#171-api-分层)）。
