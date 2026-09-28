# -*- coding: utf-8 -*-
"""``MultiPlotter``：基础状态、图层登记与公共接口。

这个模块只保留「跨图层」的东西：

* 对象状态（``ncols`` / ``figsize_per_plot`` / ``dpi`` / ``theme``）；
* 图层登记入口 ``_register_layer``（``add_*`` 只做校验，不画图）；
* 绘制分派 ``_draw_layer``（查注册表，不再是一串 ``if/elif``）；
* 出图收尾 ``draw`` / ``get_axes`` / ``clear`` / ``close``；
* 会话构造 ``init`` / ``kind_presets``；
* 扩展入口 ``register_layer`` / ``validate_layer_config``。

各 kind 的 ``add_*`` 与 ``draw_*`` 分别在
:mod:`multiplotter.draw_2d`、:mod:`multiplotter.draw_3d`、
:mod:`multiplotter.vector_fields`、:mod:`multiplotter.tables`。
"""

from __future__ import annotations

import copy
import math
import operator
import os
import sys
from typing import Mapping, Optional

import numpy as np
import matplotlib.pyplot as plt

from . import registries
from .layout import apply_view
from .registries import (
    DRAW_REGISTRY,
    INIT_KIND_ALIASES,
    INIT_STYLE_DEFAULTS,
    KIND_DEFAULTS,
    LABELS_VALUES_KINDS,
    LAYER_SPECS,
    PASSTHROUGH_BY_KIND,
    PASSTHROUGH_KEYS,
    SUPPORTED_2D_KINDS,
    SUPPORTED_3D_KINDS,
    SUPPORTED_KINDS,
    ADD_PLOT_FORWARD_KINDS,
    LayerSpec,
    build_add_dispatch,
    build_layer_specs,
    describe_layers,
    make_layer_spec,
    validate_layer_config as _validate_layer_config,
)
from .saving import get_unique_filename, resolve_save_path, save_figure
from .styles import (
    apply_global_style,
    apply_theme_to_axes,
    bind_theme_to_figure,
    facecolor_for,
    matplotlib_option,
    matplotlib_surface_option,
    pick_chinese_fonts,
    resolve_theme,
)
from .validation import (
    as_1d_array,
    broadcast_to_length,
    check_same_length,
    field_coordinates,
    field_coordinates_3d,
    field_norm,
    first_defined,
    first_nonempty,
    format_value,
    integrate_streamline,
    is_nonempty,
    mesh_coordinates,
    resolve_highlight,
    shrink_field,
    table_cell_keys,
    table_shape,
    table_style_array,
)

# 绘制模块的处理器会通过注册表调用；这里导入 Mixin。
from .draw_2d import TwoDLayersMixin
from .draw_3d import ThreeDLayersMixin
from .tables import TableLayersMixin
from .vector_fields import VectorFieldLayersMixin

#: 旧名字 -> 新函数（保持 ``Multiplotter`` 模块的导入兼容）。
_pick_chinese_fonts = pick_chinese_fonts


class MultiPlotter(
    TwoDLayersMixin,
    ThreeDLayersMixin,
    VectorFieldLayersMixin,
    TableLayersMixin,
):
    """统一的二维/三维绘图类。

    支持的二维 kind：``line``、``scatter``、``bar``、``hist``、``pie``、
    ``heatmap``、``image``、``contour``、``quiver``、``streamplot``、``table``。

    支持的三维 kind：``surface``、``line3d``、``scatter3d``、``bar3d``、
    ``hist3d``、``quiver3d``、``stream3d``。

    每一个图层配置中都包含 ``config["kind"]`` 与 ``config["dimension"]``：

    * ``dimension=2``：二维图层
    * ``dimension=3``：三维图层

    同一个 ``subplot`` 中不能同时存在 ``dimension=2`` 和 ``dimension=3``。
    """

    # ---- 图层注册表（可以整体覆盖，见 register_layer）----
    DRAW_REGISTRY = DRAW_REGISTRY
    SUPPORTED_2D_KINDS = SUPPORTED_2D_KINDS
    SUPPORTED_3D_KINDS = SUPPORTED_3D_KINDS
    SUPPORTED_KINDS = SUPPORTED_KINDS
    KIND_DEFAULTS = KIND_DEFAULTS
    INIT_KIND_ALIASES = INIT_KIND_ALIASES
    PASSTHROUGH_KEYS = PASSTHROUGH_KEYS
    PASSTHROUGH_BY_KIND = PASSTHROUGH_BY_KIND
    INIT_STYLE_DEFAULTS = INIT_STYLE_DEFAULTS
    ADD_PLOT_FORWARD_KINDS = ADD_PLOT_FORWARD_KINDS
    LABELS_VALUES_KINDS = LABELS_VALUES_KINDS
    ADD_DISPATCH = registries.ADD_DISPATCH
    LAYER_SPECS = LAYER_SPECS

    #: ``draw()`` 默认的样式作用域。
    #:
    #: * ``"context"``（默认）：用 ``matplotlib.rc_context()`` 临时应用主题，
    #:   画完自动恢复全局 ``plt.rcParams``，不污染进程；
    #: * ``"global"``：像旧版本一样直接写全局 ``plt.rcParams``
    #:   （会调用 ``matplotlib_option()`` / ``matplotlib_surface_option()``）。
    STYLE_SCOPES = ("context", "global")

    def __init__(
        self,
        ncols=2,
        figsize_per_plot=(6, 4),
        dpi=120,
        theme=None,
    ):
        if ncols < 1:
            raise ValueError("ncols必须大于等于1")

        self.ncols = ncols
        self.figsize_per_plot = figsize_per_plot
        self.dpi = dpi

        # 实例级主题：None 表示用默认主题（浅色）。
        # 用 resolve_theme() 统一解析，支持名称 / Theme / rcParams 字典。
        self.theme = theme

        # 所有绘图数据和绘图参数都保存到这里
        self.plot_configs = []

        # 记录每个子图被显式写死的坐标轴范围，
        # 结构：{subplot序号: {"xlim": (...), "ylim": (...), "zlim": (...)}}
        # AnimationPlotter 用它检查动画的坐标轴范围是否固定
        self._explicit_limits = {}

        # 记录每个子图的维度：{subplot序号: 2或3}
        self._dimension_by_subplot = {}

        # draw() 之后记录 {subplot序号: Axes}，供 get_axes() 使用
        self._subplot_axes = {}

        # draw() 得到的 Figure，供 close() 使用
        self._figure = None

    @property
    def theme_name(self):
        """当前实例主题的名称。"""

        return resolve_theme(self.theme).name

    # ================================================================
    # 图层注册表扩展接口
    # ================================================================

    @classmethod
    def register_layer(
        cls,
        kind,
        dimension,
        add_method=None,
        draw_handler=None,
        defaults=None,
        passthrough=(),
        aliases=(),
        animatable=True,
        description="",
        overwrite=False,
    ):
        """一次性注册一个新图层。

        这是新增图层的**唯一入口**：注册之后

        * ``_get_dimension(kind)`` 能返回维度；
        * ``add_layer(kind=...)`` 能转发到 ``add_method``；
        * ``init()`` 能用 ``KIND_DEFAULTS`` 里的预设；
        * ``PlotBuilder`` 能把 ``passthrough`` 里的键透传给 Matplotlib；
        * ``draw()`` 能通过 ``draw_handler`` 真正画出来。

        参数
        ----
        kind
            图层类型名，例如 ``"step"``。
        dimension
            ``2`` 或 ``3``。
        add_method
            ``add_*`` 方法名，默认 ``f"add_{kind}"``。
        draw_handler
            ``(ax, config) -> None`` 的绘制函数。
        defaults
            ``init()`` 用的默认参数字典。
        passthrough
            该 kind 专属的透传键集合。
        aliases
            指向本 kind 的 ``init()`` 别名。
        animatable
            是否声明支持动画（默认 ``True``）。
        description
            一句话说明。
        overwrite
            已经注册过的 kind 默认不允许覆盖，避免误伤内置图层。

        返回
        ----
        ``cls``，方便链式调用。

        示例::

            MultiPlotter.register_layer(
                kind="step",
                dimension=2,
                add_method="add_step",
                draw_handler=draw_step,
                defaults={"linewidth": 2.2},
                passthrough={"where"},
            )
        """

        if add_method is None:
            add_method = f"add_{kind}"

        spec = make_layer_spec(
            kind=kind,
            dimension=dimension,
            add_method=add_method,
            draw_handler=draw_handler,
            defaults=defaults,
            passthrough=passthrough,
            aliases=aliases,
            animatable=animatable,
            description=description,
        )

        existing = cls.LAYER_SPECS.get(kind)

        if existing is not None and not overwrite:
            raise ValueError(
                f"kind={kind} 已经注册过了（方法 {existing.add_method}）；"
                "确实要替换请传 overwrite=True"
            )

        # ------------------------------------------------------------
        # 就地更新所有注册表。
        #
        # 这里刻意**不重新绑定**（不写 ``cls.X = dict(cls.X)``）：
        # ``multiplotter.DRAW_REGISTRY`` 这类模块级导出、以及
        # ``multiplotter.registries`` 里的同名常量，和类属性指向的是
        # **同一个对象**。一旦重新绑定，模块级导出就会停留在旧对象上，
        # 于是 ``from multiplotter import DRAW_REGISTRY`` 之后再注册图层，
        # 用户看到的还是注册前的注册表 —— 与「单一注册入口」的承诺矛盾。
        # 就地 dict.update() / [k] = v 能让三方始终一致。
        # 不可变的 frozenset 没法就地改，所以下面用 _sync_exports 同步。
        # ------------------------------------------------------------

        # 1) 注册表（绘制分派）
        cls.DRAW_REGISTRY[kind] = spec.draw_handler

        # 2) 维度集合（frozenset 不可变，先算出新值再统一同步）
        two_d = set(cls.SUPPORTED_2D_KINDS)
        three_d = set(cls.SUPPORTED_3D_KINDS)

        if spec.dimension == 2:
            two_d.add(kind)
            three_d.discard(kind)
        else:
            three_d.add(kind)
            two_d.discard(kind)

        new_two_d = frozenset(two_d)
        new_three_d = frozenset(three_d)

        # 3) init() 预设与别名
        cls.KIND_DEFAULTS[kind] = (spec.add_method, dict(spec.defaults))

        for alias in spec.aliases:
            cls.INIT_KIND_ALIASES[alias] = kind

        # 4) 透传白名单
        if spec.passthrough:
            cls.PASSTHROUGH_BY_KIND[kind] = set(spec.passthrough)

        # 5) add_layer 分派表与完整契约
        cls.LAYER_SPECS[kind] = spec
        cls.ADD_DISPATCH.clear()
        cls.ADD_DISPATCH.update(build_add_dispatch(cls.KIND_DEFAULTS))

        # 6) 把不可变的派生量同步到类、registries 模块与 multiplotter 包
        _sync_exports(
            cls,
            {
                "SUPPORTED_2D_KINDS": new_two_d,
                "SUPPORTED_3D_KINDS": new_three_d,
                "SUPPORTED_KINDS": new_two_d | new_three_d,
            },
        )

        return cls

    @classmethod
    def registered_layers(cls):
        """返回所有已注册图层的可读描述列表。"""

        return describe_layers(cls.LAYER_SPECS)

    @classmethod
    def get_layer_spec(cls, kind):
        """返回某个 kind 的 :class:`~multiplotter.registries.LayerSpec`。

        没有注册过就抛 ``ValueError``。
        """

        resolved = cls.INIT_KIND_ALIASES.get(kind, kind)
        spec = cls.LAYER_SPECS.get(resolved)

        if spec is None:
            raise ValueError(
                f"未知的kind：{kind}；"
                f"已注册：{sorted(cls.LAYER_SPECS)}"
            )

        return spec

    @classmethod
    def validate_layer_config(cls, kind, config):
        """校验一份图层 ``config`` 是否满足框架契约。

        缺少 ``kind`` / ``dimension`` / ``subplot``、维度写错、
        或该 kind 没有绘制处理器时都会抛 ``ValueError``。
        """

        return _validate_layer_config(
            kind, config, registry=cls.DRAW_REGISTRY, specs=cls.LAYER_SPECS
        )

    # ================================================================
    # 图层登记（所有 add_* 都走这里）
    # ================================================================

    def _register_layer(self, kind, **fields):
        """把一次 ``add_*`` 调用登记成一条 config。

        ``add_*`` 只做「校验 + 打包」，**绝对不画图**：
        真正绘制要等到 :meth:`draw`。

        参数中的 ``dimension`` / ``subplot`` 会被放进 config，
        其余键原样写入（``view`` / ``legend_kwargs`` 保证不是 ``None``）。
        """

        # ``mpl_kwargs``：显式声明的「原样透传给底层 Matplotlib 方法」的字典。
        #
        # 普通 ``**kwargs`` 在 init() 会话里要过白名单（防止把某个图层的
        # 专用参数当全局样式用），而 ``mpl_kwargs`` 绕开白名单，
        # 用来处理白名单没覆盖、但确实要透传的参数。
        # 它在这里被合并进 config["kwargs"]，所以绘制处理器无需感知它。
        #
        # 两种写法都要支持：
        #   * ``add_layer(kind=..., mpl_kwargs={...})``  显式关键字；
        #   * ``add_plot(..., mpl_kwargs={...})``        -> 落进 **kwargs 里。
        kwargs = fields.pop("kwargs", None) or {}
        mpl_kwargs = fields.pop("mpl_kwargs", None)

        if mpl_kwargs is None:
            mpl_kwargs = kwargs.pop("mpl_kwargs", None)
        else:
            # 两处都写了就合并，显式关键字优先
            nested = kwargs.pop("mpl_kwargs", None)

            if nested:
                merged = dict(nested)
                merged.update(mpl_kwargs)
                mpl_kwargs = merged

        config = {
            "kind": kind,
            "dimension": int(fields.pop("dimension")),
            "subplot": fields.pop("subplot", 0),
            "title": fields.pop("title", ""),
            "xlabel": fields.pop("xlabel", ""),
            "ylabel": fields.pop("ylabel", ""),
            "zlabel": fields.pop("zlabel", ""),
            "label": fields.pop("label", None),
            "legend": fields.pop("legend", False),
            "legend_kwargs": fields.pop("legend_kwargs", None) or {},
            "axis": fields.pop("axis", None) or "",
            "view": fields.pop("view", None) or {},
            "kwargs": kwargs,
        }

        if mpl_kwargs is not None:
            if not isinstance(mpl_kwargs, Mapping):
                raise TypeError(
                    "mpl_kwargs 必须是字典，"
                    f"当前为{type(mpl_kwargs).__name__}"
                )

            config["kwargs"].update(mpl_kwargs)

        config.update(fields)

        self.plot_configs.append(config)

        return self

    def _validate_plot_configs(self):
        """在创建 Figure 前统一校验已登记的图层配置。

        ``add_*`` 仍然保持轻量登记语义；这里负责检查所有公共配置字段，
        并把错误尽早绑定到具体图层，避免绘制到一半才失败。
        """

        for index, config in enumerate(self.plot_configs):
            kind = config.get("kind", "<unknown>")
            try:
                self.validate_layer_config(kind, config)
            except (TypeError, ValueError) as error:
                raise type(error)(
                    f"第 {index} 个图层（kind={kind!r}）配置无效：{error}"
                ) from error

            subplot = config["subplot"]
            try:
                normalized_subplot = operator.index(subplot)
            except TypeError:
                normalized_subplot = -1
            if isinstance(subplot, bool) or normalized_subplot < 0:
                raise ValueError(
                    f"第 {index} 个图层（kind={kind!r}）的 subplot "
                    f"必须是非负整数，当前为 {subplot!r}"
                )

    # ================================================================
    # 维度查询
    # ================================================================

    @classmethod
    def _get_dimension(cls, kind):
        """根据 ``kind`` 返回图层维度（2 或 3）。

        这里用 ``cls`` 而不是 ``MultiPlotter``，是为了让子类只覆盖
        ``SUPPORTED_2D_KINDS`` / ``SUPPORTED_3D_KINDS`` 就能注册新 kind。
        """

        if kind in cls.SUPPORTED_2D_KINDS:
            return 2

        if kind in cls.SUPPORTED_3D_KINDS:
            return 3

        raise ValueError(
            f"不支持的图像类型：{kind}；"
            f"二维支持：{sorted(cls.SUPPORTED_2D_KINDS)}；"
            f"三维支持：{sorted(cls.SUPPORTED_3D_KINDS)}"
        )

    # ================================================================
    # 坐标轴设置
    # ================================================================

    def _apply_view_with_record(self, ax, subplot_index, dimension, view,
                                axis=None):
        """应用坐标轴设置，并记录这个子图被写死的坐标轴范围。

        记录结果保存在 ``self._explicit_limits[subplot_index]``，
        供 ``AnimationPlotter`` 检查「动画前是否固定了坐标轴范围」。
        """

        explicit_limits = apply_view(
            ax, view, dimension=dimension, axis=axis
        )

        self._explicit_limits[subplot_index] = dict(explicit_limits)

        return explicit_limits

    # ================================================================
    # 统一添加入口
    # ================================================================

    @classmethod
    def kind_presets(cls, kind):
        """返回某个 kind 的预设参数副本。

        这里用 ``cls``，子类覆盖 ``KIND_DEFAULTS`` / ``INIT_KIND_ALIASES``
        后也能正确解析（否则子类新增的 kind 在 ``init()`` 里会报「不支持」）。

        返回 ``(方法名, 默认参数字典)``。
        """

        resolved = cls.INIT_KIND_ALIASES.get(kind, kind)

        if resolved not in cls.KIND_DEFAULTS:
            raise ValueError(
                f"未知的kind：{kind}；"
                f"支持：{sorted(cls.KIND_DEFAULTS)}"
            )

        method_name, defaults = cls.KIND_DEFAULTS[resolved]

        return method_name, copy.deepcopy(defaults)

    def add_layer(self, kind, subplot=0, **kwargs):
        """根据 ``kind`` 统一添加图层。

        分派规则由 ``ADD_DISPATCH``（从 ``KIND_DEFAULTS`` 生成）决定，
        所以**注册过的 kind 会自动出现在这里**，不用再改本方法。

        普通二维图层（``line`` / ``scatter`` / ``bar`` / ``hist`` /
        ``pie`` / ``heatmap`` / ``image``）仍然通过 :meth:`add_plot` 处理。
        """

        method_name = self.ADD_DISPATCH.get(kind)

        if method_name is not None:
            if kind in self.LABELS_VALUES_KINDS:
                # 专用接口使用 labels/values 命名，
                # 便于与其它高级图层方法保持一致。
                if "labels" in kwargs or "values" in kwargs:
                    return getattr(self, method_name)(
                        subplot=subplot, **kwargs
                    )
            else:
                return getattr(self, method_name)(subplot=subplot, **kwargs)

        if kind in self.ADD_PLOT_FORWARD_KINDS:
            return self.add_plot(kind=kind, subplot=subplot, **kwargs)

        raise ValueError(f"不支持的kind：{kind}")

    # ================================================================
    # 唯一的绘制分派方法
    # ================================================================

    def _draw_layer(self, ax, config):
        """所有图层都在这里分派绘制。

        通过 ``config["kind"]`` 在 ``DRAW_REGISTRY`` 里查处理器，
        通过 ``config["dimension"]`` 校验维度是否匹配。

        子类想加新图层时，**优先用** :meth:`register_layer` 注册，
        而不是重写本方法。
        """

        kind = config["kind"]
        dimension = config["dimension"]

        if dimension not in (2, 3):
            raise ValueError(
                f"dimension必须是2或3，"
                f"当前为{dimension}"
            )

        handler = self.DRAW_REGISTRY.get(kind)

        # 注册表里没有、或者维度写反了，都按「该维度不支持该 kind」报错
        if handler is None or self._registered_dimension(kind) not in (
            None, dimension,
        ):
            raise ValueError(
                f"dimension={dimension}不支持kind={kind}"
            )

        handler(ax, config)

    @classmethod
    def _registered_dimension(cls, kind):
        """返回注册表里该 kind 的维度；没注册过返回 ``None``。"""

        if kind in cls.SUPPORTED_2D_KINDS:
            return 2

        if kind in cls.SUPPORTED_3D_KINDS:
            return 3

        return None

    # ================================================================
    # 绘制入口
    # ================================================================

    def draw(
        self,
        show=True,
        save=False,
        save_path=None,
        save_path_name="分析结果",
        theme=None,
        style_scope="context",
        close_previous=False,
    ):
        """绘制所有二维和三维图层。

        同一个 ``subplot`` 不能混用二维和三维图层。

        保存方式::

            draw(show=False)                             # 只返回 Figure
            draw(show=False, save=True)                  # 保存到 分析结果/MultiPlotter.png
            draw(show=False, save_path="results/a.png")  # 保存到指定文件
            draw(show=False, save_path="results/")       # 保存到指定目录
            draw(show=False, save_path="results/a")      # 自动补上 .png

        传入 ``save_path`` 时不需要再传 ``save=True``，
        保存目录不存在会自动创建，同名文件会自动加序号。

        样式
        ----
        ``theme``
            本次绘制使用的主题：``None`` 用对象自己的主题，
            也可以是名称（``"default"`` / ``"surface"``）、
            :class:`~multiplotter.styles.Theme` 对象或 rcParams 字典。
        ``style_scope``
            ``"context"``（默认）在 ``matplotlib.rc_context()`` 里临时应用主题，
            画完自动恢复全局 ``plt.rcParams``；``"global"`` 则像旧版本一样
            直接写全局 ``plt.rcParams``（调用 ``matplotlib_option()``）。
        ``close_previous``
            ``True`` 时先关闭上一次 ``draw()`` 产生的 Figure，
            避免长期运行反复出图时积累资源。
        """

        if not self.plot_configs:
            raise ValueError("没有可绘制的配置")

        self._validate_plot_configs()

        if style_scope not in self.STYLE_SCOPES:
            raise ValueError(
                f"style_scope 必须是 {self.STYLE_SCOPES} 之一，"
                f"当前为{style_scope!r}"
            )

        resolved_theme = resolve_theme(
            self.theme if theme is None else theme
        )

        if close_previous:
            self.close()

        subplot_indexes = [
            config["subplot"] for config in self.plot_configs
        ]

        nplots = max(subplot_indexes) + 1
        nrows = math.ceil(nplots / self.ncols)
        total_slots = nrows * self.ncols

        # 主题只在创建 Figure / Axes 期间生效，退出后全局 rcParams 自动恢复。
        context = (
            resolved_theme.rc_context()
            if style_scope == "context"
            else _null_context()
        )

        with context:
            fig = plt.figure(
                figsize=(
                    self.figsize_per_plot[0] * self.ncols,
                    self.figsize_per_plot[1] * nrows,
                ),
                dpi=self.dpi,
                constrained_layout=True,
            )

            grid = fig.add_gridspec(nrows=nrows, ncols=self.ncols)

            # 每次 draw() 都重新记录坐标轴信息
            self._explicit_limits = {}
            self._dimension_by_subplot = {}

            axes = []

            for subplot_index in range(total_slots):
                row = subplot_index // self.ncols
                col = subplot_index % self.ncols

                configs = [
                    config
                    for config in self.plot_configs
                    if config["subplot"] == subplot_index
                ]

                # 当前子图没有配置时隐藏
                if not configs:
                    ax = fig.add_subplot(grid[row, col])
                    ax.set_visible(False)
                    axes.append(ax)
                    continue

                dimensions = {
                    config["dimension"] for config in configs
                }

                # 维度冲突检查
                if len(dimensions) > 1:
                    kinds = [
                        (config["kind"], config["dimension"])
                        for config in configs
                    ]

                    raise ValueError(
                        f"subplot={subplot_index}中"
                        "同时存在二维和三维图层，"
                        "维度冲突："
                        f"{kinds}。"
                        "请将二维和三维图层放到不同subplot中。"
                    )

                dimension = dimensions.pop()
                self._dimension_by_subplot[subplot_index] = dimension

                # 旧行为：按维度重新套用全局样式（会改全局 rcParams）。
                # apply_global_style() 通过模块属性查找样式函数，
                # 所以 monkeypatch multiplotter.styles.matplotlib_option
                # 依然能生效（见 EXTENDING.md 第 13 章）。
                if style_scope == "global":
                    apply_global_style(dimension)

                if dimension == 3:
                    ax = fig.add_subplot(grid[row, col], projection="3d")
                else:
                    ax = fig.add_subplot(grid[row, col])

                # 直接给 Axes 设面板颜色，不再依赖全局 rcParams
                apply_theme_to_axes(ax, dimension, resolved_theme)

                axes.append(ax)

                # 按配置添加顺序绘制图层
                for config in configs:
                    self._draw_layer(ax, config)

                self._apply_subplot_labels(ax, configs, dimension)
                self._apply_subplot_view(
                    ax, configs, subplot_index, dimension
                )
                self._apply_subplot_legend(ax, configs)

            # 保存图像：save_path 优先；只写 save=True 时保存到 分析结果/
            save_figure(
                fig,
                save_path=save_path,
                save=save,
                save_path_name=save_path_name,
                default_name="MultiPlotter",
            )

        axes_array = np.asarray(axes, dtype=object)

        self._figure = fig
        bind_theme_to_figure(fig, resolved_theme)
        self._subplot_axes = {
            int(index): ax
            for index, ax in enumerate(axes_array.ravel())
        }

        if show:
            plt.show()

        return fig, axes_array

    # ---- draw() 的三个收尾步骤（拆出来便于阅读与测试）----

    def _apply_subplot_labels(self, ax, configs, dimension):
        """汇总并设置子图的标题与坐标轴标签。"""

        # 使用当前子图中第一个非空公共配置
        title = first_nonempty(configs, "title", default="")

        # 坐标轴标签：使用图层里显式写出的值，没有写出时才使用默认标签。
        # 例如饼图会把 xlabel/ylabel 设置为空字符串，此时保持空白。
        xlabel = first_defined(configs, "xlabel", default="X")
        ylabel = first_defined(configs, "ylabel", default="Y")
        zlabel = first_defined(configs, "zlabel", default="Z")

        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        if dimension == 3:
            ax.set_zlabel(zlabel)

    def _apply_subplot_view(self, ax, configs, subplot_index, dimension):
        """应用坐标轴设置（范围、比例、网格、三维视角）。"""

        view_config = None

        for config in configs:
            if config.get("view"):
                view_config = config
                break

        if dimension == 3:
            if view_config is not None:
                self._apply_view_with_record(
                    ax, subplot_index, dimension, view_config.get("view")
                )
            else:
                ax.grid(True)

            return

        if view_config is not None:
            self._apply_view_with_record(
                ax,
                subplot_index,
                dimension,
                view_config.get("view"),
                axis=view_config.get("axis"),
            )
        else:
            axis = first_nonempty(configs, "axis", default=None)

            self._apply_view_with_record(
                ax, subplot_index, dimension, {}, axis=axis
            )

        if hasattr(ax, "spines"):
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

    @staticmethod
    def _apply_subplot_legend(ax, configs):
        """统一图例：取当前子图中第一个「要图例且有 label」的图层配置。"""

        legend_configs = [
            config
            for config in configs
            if config.get("legend", False) and config.get("label") is not None
        ]

        if legend_configs:
            ax.legend(**(legend_configs[0].get("legend_kwargs") or {}))

    # ================================================================
    # 坐标轴与生命周期
    # ================================================================

    def get_axes(self, subplot=0):
        """返回 ``draw()`` 之后指定 subplot 的 Axes 对象。

        方便在动画或后续微调里直接操作坐标轴::

            fig, axes = plotter.draw(show=False)
            ax = plotter.get_axes(0)
        """

        if not getattr(self, "_subplot_axes", None):
            raise RuntimeError("还没有可用的坐标轴，请先调用 draw()。")

        return self._get_subplot_axes(subplot)

    def _get_subplot_axes(self, subplot):
        """按 subplot 序号取得坐标轴，兼容调用方传入 ``subplot`` / ``ax``。"""

        if hasattr(subplot, "plot"):        # 直接传了 Axes
            return subplot

        if subplot not in self._subplot_axes:
            raise KeyError(
                f"subplot={subplot}不存在。"
                f"当前已经绘制的子图有：{sorted(self._subplot_axes)}。"
                "请先调用 draw()，并确认 subplot 序号正确。"
            )

        return self._subplot_axes[subplot]

    def clear(self, close_figures=None):
        """清除所有图层配置和坐标轴记录。

        ``close_figures``
            * ``None``（默认）：沿用旧行为，只清配置，不动 Figure；
            * ``True``：同时关闭 ``draw()`` 产生的 Figure，
              释放资源（长期运行或循环出图时建议打开）。

        只想关闭画布、保留配置时用 :meth:`close`。
        """

        self.plot_configs.clear()
        self._explicit_limits.clear()
        self._dimension_by_subplot.clear()
        self._subplot_axes.clear()

        if close_figures:
            self.close()

        return self

    def close(self):
        """关闭 ``draw()`` 产生的 Figure（保留图层配置）。

        多次 ``draw()`` 时旧 Figure 不会自动关闭（与旧行为一致），
        需要主动回收时调用本方法，或者用 ``draw(close_previous=True)``。
        """

        fig = getattr(self, "_figure", None)

        if fig is not None:
            try:
                plt.close(fig)
            except Exception:                           # noqa: BLE001
                pass

            self._figure = None

        self._subplot_axes = {}

        return self

    def __enter__(self):
        """支持 ``with MultiPlotter(...) as plotter:``，退出时自动关闭画布。"""

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

        return False

    # ================================================================
    # 会话构造
    # ================================================================

    @classmethod
    def init(
        cls,
        ncols=2,
        figsize_per_plot=(6, 4),
        dpi=120,
        style=None,
        subplot=0,
        title="",
        xlabel=None,
        ylabel=None,
        zlabel=None,
        xlim=None,
        ylim=None,
        zlim=None,
        theme=None,
        strict=False,
        **style_overrides,
    ):
        """创建一个「预设好全部绘图参数」的绘图会话（Builder）。

        只写一次初始化设置，之后调用 ``add()`` 时只需要给数据。

        参数
        ----
        ncols / figsize_per_plot / dpi
            画布布局与分辨率。
        style
            字典形式的全局样式覆盖；等价于直接把这些键作为关键字参数传进来。
        subplot / title
            默认子图序号与默认标题。
        xlabel / ylabel / zlabel
            默认坐标轴标签。
        xlim / ylim / zlim
            默认坐标轴范围，会写进 ``view``。
        theme
            主题（名称 / Theme 对象 / rcParams 字典）。
        strict
            是否让 ``init()`` 会话在发现未知或被过滤参数时直接抛出
            ``TypeError``。默认 ``False``，保持旧行为但发出标准警告。
        **style_overrides
            其它全局样式，可用的键见 ``INIT_STYLE_DEFAULTS``，
            例如 ``legend``、``grid``、``cell_fontsize``、``cmap``、
            ``show_values``、``colorbar``、``scale``、``axis`` 等。

        返回
        ----
        :class:`~multiplotter.builder.PlotBuilder` 对象，
        链式调用 ``add()`` 添加图层，``draw()`` 出图。
        """

        from .builder import PlotBuilder

        if isinstance(style, dict):
            style_overrides = {**style, **style_overrides}

        # 坐标轴范围既可以写成独立参数，也可以写在 style 里，
        # 这里统一收拢到 limits。
        limits = {"xlim": xlim, "ylim": ylim, "zlim": zlim}

        for axis_name in ("xlim", "ylim", "zlim"):
            if (limits[axis_name] is None
                    and style_overrides.get(axis_name) is not None):
                limits[axis_name] = style_overrides.pop(axis_name)

        return PlotBuilder(
            plotter_class=cls,
            ncols=ncols,
            figsize_per_plot=figsize_per_plot,
            dpi=dpi,
            style=style_overrides,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            zlabel=zlabel,
            limits=limits,
            theme=theme,
            strict=strict,
        )

    # ================================================================
    # 兼容旧代码的内部工具（实现见各模块，这里只做绑定）
    # ================================================================

    _matplotlib_save = staticmethod(
        lambda name, pathname="分析结果": save_figure(
            plt.gcf(), save=True, save_path_name=pathname, default_name=name
        )
    )

    _resolve_save_path = staticmethod(resolve_save_path)

    _as_1d_array = staticmethod(as_1d_array)
    _check_same_length = staticmethod(check_same_length)
    _broadcast_to_length = staticmethod(broadcast_to_length)
    _mesh_coordinates = staticmethod(mesh_coordinates)
    _field_coordinates = staticmethod(field_coordinates)
    _field_coordinates_3d = staticmethod(field_coordinates_3d)
    _field_norm = staticmethod(field_norm)
    _shrink_field = staticmethod(shrink_field)
    _integrate_streamline = staticmethod(integrate_streamline)
    _table_shape = staticmethod(table_shape)
    _table_style_array = staticmethod(table_style_array)
    _table_cell_keys = staticmethod(table_cell_keys)
    _resolve_highlight = staticmethod(resolve_highlight)
    _is_nonempty = staticmethod(is_nonempty)
    _first_nonempty = staticmethod(first_nonempty)
    _first_defined = staticmethod(first_defined)
    _format_value = staticmethod(format_value)

    # 坐标轴设置（实现见 multiplotter.layout）
    @staticmethod
    def _apply_3d_view(ax, view):
        from .layout import apply_3d_view

        return apply_3d_view(ax, view)

    @staticmethod
    def _apply_2d_view(ax, view, axis=None):
        from .layout import apply_2d_view

        return apply_2d_view(ax, view, axis=axis)

    @staticmethod
    def _apply_grid_style(ax, view):
        from .layout import apply_grid_style

        return apply_grid_style(ax, view)

    # 数值标注（实现见 multiplotter.draw_2d / draw_3d）
    @staticmethod
    def _add_2d_bar_labels(ax, container, values, config):
        from .draw_2d import add_2d_bar_labels

        return add_2d_bar_labels(ax, container, values, config)

    @staticmethod
    def _add_3d_bar_labels(ax, config):
        from .draw_3d import add_3d_bar_labels

        return add_3d_bar_labels(ax, config)

    # 表格（实现见 multiplotter.tables）
    @staticmethod
    def _get_table(ax, config):
        from .tables import get_table

        return get_table(ax, config)

    @staticmethod
    def _update_table(ax, config):
        from .tables import update_table

        return update_table(ax, config)

    # 矢量场（实现见 multiplotter.vector_fields）
    @staticmethod
    def _build_seeds(config):
        from .vector_fields import build_seeds

        return build_seeds(config)

    @staticmethod
    def _draw_colored_polyline(ax, trajectory, values, cmap, norm,
                               line_width, extra_kwargs=None):
        from .vector_fields import draw_colored_polyline

        return draw_colored_polyline(
            ax, trajectory, values, cmap, norm, line_width, extra_kwargs
        )

    @staticmethod
    def _speed_along(trajectory, field):
        from .vector_fields import speed_along

        return speed_along(trajectory, field)

    @staticmethod
    def _compare(value, operator, reference):
        from .validation import compare

        return compare(value, operator, reference)


class _null_context:
    """什么都不做的上下文管理器（``style_scope="global"`` 时使用）。"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


#: 注册表里那些**不可变**、需要三方同步的派生量。
#:
#: 字典类的注册表可以就地更新，所以它们天然一致；
#: 而 ``frozenset`` 只能整体替换，必须显式写到下面三个地方，
#: 否则 ``from multiplotter import SUPPORTED_KINDS`` 会拿到旧值。
_SYNCED_EXPORT_NAMES = (
    "SUPPORTED_2D_KINDS",
    "SUPPORTED_3D_KINDS",
    "SUPPORTED_KINDS",
)


def _sync_exports(cls, values):
    """把不可变的注册表派生量同步到类、registries 模块与包命名空间。

    ``register_layer()`` 会改 ``SUPPORTED_*`` 这类 ``frozenset``。
    它们在三个地方被引用：

    * ``MultiPlotter.SUPPORTED_KINDS``（库内部用）；
    * ``multiplotter.registries.SUPPORTED_KINDS``（模块级常量）；
    * ``multiplotter.SUPPORTED_KINDS``（``__init__`` 里 re-export 给用户）。

    只写类属性会让后两者停留在旧值，所以这里一次性同步三处。
    """

    for name, value in values.items():
        setattr(cls, name, value)

        if hasattr(registries, name):
            setattr(registries, name, value)

    # 包命名空间是 re-export，需要单独同步（延迟取模块避免循环依赖）
    package = sys.modules.get(__package__)

    if package is not None:
        for name in _SYNCED_EXPORT_NAMES:
            if hasattr(package, name):
                setattr(package, name, getattr(cls, name))


__all__ = [
    "MultiPlotter",
    "LayerSpec",
    "get_unique_filename",
    "resolve_save_path",
    "save_figure",
    "pick_chinese_fonts",
    "matplotlib_option",
    "matplotlib_surface_option",
    "facecolor_for",
    "os",
    "Optional",
]
