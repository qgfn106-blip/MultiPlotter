# -*- coding: utf-8 -*-
"""二维图层：登记（``add_*``）与绘制（``draw_*``）。

本模块包含三类内容：

1. **绘制处理器**：``draw_line`` / ``draw_scatter`` … 每个函数签名统一为
   ``(ax, config)``，只读 ``config``、只操作传入的 ``ax``，不碰实例状态。
2. **绘制注册表**：``DRAW_HANDLERS``，把 ``kind`` 映射到处理器，
   取代原先 ``_draw_layer`` 里的巨型 ``if/elif``。
3. **添加图层的 Mixin**：``TwoDLayersMixin``，提供 ``add_plot`` /
   ``add_pie`` / ``add_correlation_heatmap`` / ``add_contour``。

外部调用方式与重构前完全一致::

    plotter.add_plot(kind="line", x=x, y=y)
    plotter.add_contour(X, Y, Z, levels=30)
"""

from __future__ import annotations

import numpy as np

from .validation import format_value, mesh_coordinates

# ----------------------------------------------------------------------
# 数值标注辅助
# ----------------------------------------------------------------------


def add_2d_bar_labels(ax, container, values, config):
    """给二维柱状图/直方图打柱顶数值标签。"""

    if not config.get("show_values", False):
        return

    options = {
        "padding": config.get("value_offset", 3),
        "fontsize": 9,
    }

    user_options = config.get("value_kwargs") or {}
    options.update({
        key: value
        for key, value in user_options.items()
        if key not in {"ha", "va"}
    })

    labels = [
        format_value(value, config.get("value_format", ".2f"))
        for value in values
    ]

    ax.bar_label(container, labels=labels, **options)


def _labelled_kwargs(config):
    """取出 ``config["kwargs"]`` 的副本，并按需补上 ``label``。

    ``label`` 是 ``add_*`` 的显式参数，不会进 ``config["kwargs"]``，
    所以必须手动补回去，否则图例出不来。
    """

    kwargs = config["kwargs"].copy()

    if config["label"] is not None:
        kwargs["label"] = config["label"]

    return kwargs


# ----------------------------------------------------------------------
# 绘制处理器
# ----------------------------------------------------------------------


def draw_line(ax, config):
    """折线：``ax.plot``。"""

    ax.plot(config["x"], config["y"], **_labelled_kwargs(config))


def draw_scatter(ax, config):
    """散点：``ax.scatter``。"""

    ax.scatter(config["x"], config["y"], **_labelled_kwargs(config))


def draw_bar(ax, config):
    """柱状图：``ax.bar`` + 可选柱顶数值。"""

    bars = ax.bar(config["x"], config["y"], **_labelled_kwargs(config))

    add_2d_bar_labels(ax, bars, np.asarray(config["y"]), config)


def draw_hist(ax, config):
    """直方图：``ax.hist`` + 可选柱顶数值。"""

    counts, _edges, patches = ax.hist(config["x"], **_labelled_kwargs(config))

    if config.get("show_values", False):
        labels = [
            format_value(count, config.get("value_format", ".0f"))
            for count in counts
        ]

        options = {
            "padding": config.get("value_offset", 2),
            "fontsize": 8,
        }

        user_options = config.get("value_kwargs") or {}
        options.update({
            key: value
            for key, value in user_options.items()
            if key not in {"ha", "va"}
        })

        ax.bar_label(patches, labels=labels, **options)


def draw_pie(ax, config):
    """饼图：``ax.pie``。

    饼图不需要坐标轴标题，绘制后会清空 ``xlabel`` / ``ylabel``。
    """

    kwargs = config["kwargs"].copy()
    values = np.asarray(config["y"], dtype=float)
    labels = config.get("x")

    if config.get("show_values", True):
        kwargs.setdefault(
            "autopct",
            lambda percent: format_value(
                percent, config.get("value_format", ".1f")
            ) + "%",
        )
    else:
        kwargs.pop("autopct", None)

    value_kwargs = config.get("value_kwargs") or {}
    if value_kwargs and "textprops" not in kwargs:
        kwargs["textprops"] = value_kwargs

    if labels is not None:
        kwargs["labels"] = labels

    ax.pie(values, **kwargs)
    ax.set_aspect("equal", adjustable="box")

    ax.set_xlabel("")
    ax.set_ylabel("")


def draw_heatmap(ax, config):
    """热力图：``ax.imshow`` + 可选刻度标签、单元格数值与颜色条。"""

    kwargs = config["kwargs"].copy()
    heatmap_text_size = kwargs.pop(
        "heatmap_text_size", config.get("heatmap_text_size", 9)
    )
    colorbar = kwargs.pop("colorbar", True)
    colorbar_kwargs = kwargs.pop(
        "colorbar_kwargs", config.get("colorbar_kwargs") or {}
    )

    values = np.asarray(config["data"])
    labels = config.get("tick_labels")

    if labels is not None:
        if len(labels) != values.shape[1] or values.shape[0] != len(labels):
            raise ValueError("tick_labels长度必须与热力图矩阵的行列数一致")

        kwargs.setdefault(
            "vmin", -1 if config.get("correlation", False) else None
        )
        kwargs.setdefault(
            "vmax", 1 if config.get("correlation", False) else None
        )
        kwargs = {
            key: value for key, value in kwargs.items() if value is not None
        }

    image = ax.imshow(values, aspect="auto", **kwargs)

    if labels is not None:
        positions = np.arange(len(labels))
        ax.set_xticks(positions)
        ax.set_yticks(positions)
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_yticklabels(labels)

    if config.get("show_heatmap_values", False):
        fmt = config.get("heatmap_value_format", ".2f")
        threshold = np.nanmax(np.abs(values)) * 0.55

        for row in range(values.shape[0]):
            for col in range(values.shape[1]):
                value = values[row, col]
                text_color = "white" if abs(value) > threshold else "black"

                ax.text(
                    col,
                    row,
                    format_value(value, fmt),
                    ha="center",
                    va="center",
                    color=text_color,
                    fontsize=heatmap_text_size,
                )

    if colorbar:
        ax.figure.colorbar(image, ax=ax, **colorbar_kwargs)


def draw_image(ax, config):
    """图像：``ax.imshow`` + 可选颜色条。

    ``colorbar`` / ``colorbar_kwargs`` 是本框架的参数，
    不能透传给 ``imshow()``，所以这里先取出来。
    """

    kwargs = config["kwargs"].copy()

    colorbar = kwargs.pop("colorbar", False)
    colorbar_kwargs = kwargs.pop("colorbar_kwargs", None) or {}

    image = ax.imshow(config["image"], **kwargs)

    if colorbar:
        ax.figure.colorbar(image, ax=ax, **colorbar_kwargs)


def draw_contour(ax, config):
    """填充等高线 + 黑色等高线 + 可选数值标注与颜色条。"""

    X = config["x"]
    Y = config["y"]
    Z = config["data"]

    contourf = None

    # ---- 填充等高线 ----
    contourf_kwargs = config["contourf_kwargs"].copy()
    contourf_kwargs.setdefault("levels", config["levels"])
    contourf_kwargs.setdefault("cmap", config["cmap"])
    contourf_kwargs.setdefault("alpha", config["alpha"])

    if config["filled"]:
        contourf = ax.contourf(X, Y, Z, **contourf_kwargs)

    # ---- 黑色等高线 ----
    contour_kwargs = config["contour_kwargs"].copy()
    contour_kwargs.setdefault("levels", config["line_levels"])
    contour_kwargs.setdefault("colors", "black")
    contour_kwargs.setdefault("linewidths", 0.5)
    contour_kwargs.setdefault("alpha", 0.65)

    contour_lines = ax.contour(X, Y, Z, **contour_kwargs)

    # ---- 等高线数值 ----
    if config["clabel"]:
        clabel_kwargs = config["clabel_kwargs"].copy()
        clabel_kwargs.setdefault("inline", True)
        clabel_kwargs.setdefault("fontsize", 8)
        clabel_kwargs.setdefault("fmt", "%.1f")

        ax.clabel(contour_lines, **clabel_kwargs)

    # ---- 颜色条 ----
    if config["colorbar"] and contourf is not None:
        ax.figure.colorbar(
            contourf, ax=ax, **config["colorbar_kwargs"]
        )


#: 二维 ``kind`` -> 绘制处理器。
DRAW_HANDLERS = {
    "line": draw_line,
    "scatter": draw_scatter,
    "bar": draw_bar,
    "hist": draw_hist,
    "pie": draw_pie,
    "heatmap": draw_heatmap,
    "image": draw_image,
    "contour": draw_contour,
}

#: ``add_plot(kind=...)`` 支持的 kind。
ADD_PLOT_KINDS = frozenset({
    "line", "scatter", "bar", "hist", "pie", "heatmap", "image",
})


# ----------------------------------------------------------------------
# 添加图层（Mixin）
# ----------------------------------------------------------------------


class TwoDLayersMixin:
    """二维图层的 ``add_*`` 方法。

    依赖宿主类提供 ``_register_layer`` 与 ``_explicit_limits`` 等成员。
    """

    def add_plot(
        self,
        kind,
        x=None,
        y=None,
        image=None,
        data=None,
        subplot=0,
        title="",
        xlabel="",
        ylabel="",
        label=None,
        legend=True,
        legend_kwargs=None,
        axis="",
        show_values=False,
        value_format=".2f",
        value_offset=3,
        value_kwargs=None,
        tick_labels=None,
        view: dict = None,
        show_heatmap_values=False,
        heatmap_value_format=".2f",
        **kwargs,
    ):
        """添加普通二维图层。

        保留原来的 ``add_plot`` 调用方式，支持 ``line``、``scatter``、
        ``bar``、``hist``、``pie``、``heatmap``、``image``。

        示例::

            plotter.add_plot(
                kind="line", x=x, y=y, subplot=0,
                color="red", label="curve",
            )
        """

        if kind not in ADD_PLOT_KINDS:
            raise ValueError(
                f"add_plot不支持图像类型：{kind}；"
                f"请使用：{sorted(ADD_PLOT_KINDS)}"
            )
        if kind == "image" and "heatmap_text_size" in kwargs:
            raise TypeError(
                "heatmap_text_size 仅适用于 heatmap，不适用于 image"
            )

        return self._register_layer(
            kind,
            dimension=2,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            axis=axis,
            view=view,
            kwargs=kwargs,
            x=x,
            y=y,
            z=None,
            image=image,
            data=data,
            show_values=show_values,
            value_format=value_format,
            value_offset=value_offset,
            value_kwargs=value_kwargs or {},
            tick_labels=tick_labels,
            show_heatmap_values=show_heatmap_values,
            heatmap_value_format=heatmap_value_format,
        )

    def add_pie(
        self,
        labels,
        values,
        subplot=0,
        title="",
        xlabel="",
        ylabel="",
        label=None,
        legend=False,
        legend_kwargs=None,
        show_values=True,
        value_format=".1f",
        value_kwargs=None,
        colors=None,
        explode=None,
        autopct=None,
        startangle=90,
        view=None,
        **kwargs,
    ):
        """添加二维饼图。

        ``labels`` 是扇区名称，``values`` 是各扇区数值。饼图可以通过
        ``add_pie``、``add_plot(kind="pie")`` 或 ``add_layer(kind="pie")``
        调用。默认显示百分比；传入 ``show_values=False`` 可关闭扇区数值。
        """

        labels = list(labels) if labels is not None else None
        values = np.asarray(values, dtype=float).ravel()

        if values.size == 0:
            raise ValueError("饼图values不能为空")
        if not np.all(np.isfinite(values)):
            raise ValueError("饼图values必须全部是有限数值")
        if np.any(values < 0) or np.sum(values) <= 0:
            raise ValueError("饼图values必须为非负数且总和大于0")
        if labels is not None and len(labels) != values.size:
            raise ValueError("饼图labels长度必须与values一致")
        if explode is not None and len(explode) != values.size:
            raise ValueError("饼图explode长度必须与values一致")
        if colors is not None and len(colors) != values.size:
            raise ValueError("饼图colors长度必须与values一致")

        pie_kwargs = dict(kwargs)
        pie_kwargs.update({
            "colors": colors,
            "explode": explode,
            "startangle": startangle,
        })
        pie_kwargs = {
            key: value for key, value in pie_kwargs.items()
            if value is not None
        }

        if autopct is not None:
            pie_kwargs["autopct"] = autopct

        return self.add_plot(
            kind="pie",
            x=labels,
            y=values,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            view=view,
            show_values=show_values,
            value_format=value_format,
            value_kwargs=value_kwargs,
            **pie_kwargs,
        )

    def add_correlation_heatmap(
        self,
        data,
        labels=None,
        subplot=0,
        title="Correlation matrix",
        xlabel="Variables",
        ylabel="Variables",
        cmap="coolwarm",
        show_values=True,
        value_format=".2f",
        colorbar=True,
        colorbar_kwargs=None,
        tick_rotation=45,
        text_size=9,
        view=None,
        **kwargs,
    ):
        """添加带标签的相关性矩阵热力图。

        ``data`` 可以是形状为 ``(n_samples, n_features)`` 的原始样本，
        也可以是已经算好的方阵相关性矩阵。``labels`` 同时用于两个轴的
        刻度名称，并用来校验方阵维度。
        """

        values = np.asarray(data, dtype=float)

        if values.ndim != 2:
            raise ValueError("data必须是二维数组")

        if values.shape[0] != values.shape[1]:
            values = np.corrcoef(values, rowvar=False)

        if values.shape[0] != values.shape[1]:
            raise ValueError("相关性矩阵必须是方阵")

        if labels is None:
            labels = [f"feature_{i}" for i in range(values.shape[0])]

        labels = list(labels)

        if len(labels) != values.shape[0]:
            raise ValueError("labels长度必须等于相关性矩阵维度")

        return self.add_plot(
            kind="heatmap",
            data=values,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            cmap=cmap,
            vmin=-1,
            vmax=1,
            tick_labels=labels,
            show_heatmap_values=show_values,
            heatmap_value_format=value_format,
            heatmap_text_size=text_size,
            colorbar=colorbar,
            colorbar_kwargs=colorbar_kwargs or {"label": "Correlation"},
            view=view,
            **kwargs,
        )

    def add_contour(
        self,
        x,
        y,
        z,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        label=None,
        legend=False,
        legend_kwargs=None,
        axis="equal",
        levels=30,
        line_levels=None,
        cmap="viridis",
        filled=True,
        alpha=0.75,
        contourf_kwargs=None,
        contour_kwargs=None,
        clabel=True,
        clabel_kwargs=None,
        colorbar=True,
        colorbar_kwargs=None,
        view=None,
    ):
        """添加二维填充等高线和黑色等高线。

        示例::

            plotter.add_contour(
                X, Y, Z, subplot=1, levels=30, line_levels=15,
                cmap="viridis", clabel=True, colorbar=True,
                view={"aspect": "equal"},
            )
        """

        X, Y, Z = mesh_coordinates(x, y, z)

        if line_levels is None:
            line_levels = levels

        return self._register_layer(
            "contour",
            dimension=2,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            axis=axis,
            view=view,
            kwargs={},
            x=X,
            y=Y,
            z=None,
            data=Z,
            levels=levels,
            line_levels=line_levels,
            cmap=cmap,
            filled=filled,
            alpha=alpha,
            contourf_kwargs=contourf_kwargs or {},
            contour_kwargs=contour_kwargs or {},
            clabel=clabel,
            clabel_kwargs=clabel_kwargs or {},
            colorbar=colorbar,
            colorbar_kwargs=colorbar_kwargs or {},
        )


__all__ = [
    "TwoDLayersMixin",
    "DRAW_HANDLERS",
    "ADD_PLOT_KINDS",
    "add_2d_bar_labels",
    "draw_line",
    "draw_scatter",
    "draw_bar",
    "draw_hist",
    "draw_pie",
    "draw_heatmap",
    "draw_image",
    "draw_contour",
]
