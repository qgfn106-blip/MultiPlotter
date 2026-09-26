# -*- coding: utf-8 -*-
"""三维图层：登记（``add_*``）与绘制（``draw_*``）。

结构与 :mod:`multiplotter.draw_2d` 对称：

* ``DRAW_HANDLERS`` 注册表把三维 ``kind`` 映射到 ``(ax, config)`` 处理器；
* ``ThreeDLayersMixin`` 提供 ``add_surface`` / ``add_line3d`` /
  ``add_scatter3d`` / ``add_bar3d`` / ``add_hist3d``。
"""

from __future__ import annotations

import numpy as np
from matplotlib import cm
from matplotlib.colors import LightSource, Normalize, PowerNorm

from .validation import (
    as_1d_array,
    broadcast_to_length,
    check_same_length,
    format_value,
    mesh_coordinates,
)

# ----------------------------------------------------------------------
# 数值标注辅助
# ----------------------------------------------------------------------

#: ``value_selection`` 支持的全部取值。
VALUE_SELECTIONS = ("auto", "all", "top", "extrema", "threshold", "none")


def _select_value_indices(heights, config):
    """按 ``value_selection`` 选出要标注的柱子下标。"""

    count = len(heights)
    selection = config.get("value_selection", "auto")
    max_labels = config.get("max_value_labels", 20)
    threshold = config.get("value_threshold")

    if selection == "none":
        return np.array([], dtype=int)

    if selection == "all":
        return np.arange(count)

    if selection == "threshold":
        if threshold is None:
            raise ValueError(
                "value_selection='threshold' requires value_threshold"
            )
        return np.flatnonzero(np.abs(heights) >= float(threshold))

    if selection not in {"auto", "top", "extrema"}:
        raise ValueError(
            "value_selection must be one of: "
            + ", ".join(VALUE_SELECTIONS)
        )

    limit = count if max_labels is None else max(2, int(max_labels))
    ranked = np.argsort(np.abs(heights))[::-1]

    if selection == "extrema":
        return np.unique(
            [int(np.argmax(heights)), int(np.argmin(heights))]
        )

    if selection == "top":
        return ranked[:limit]

    if count <= limit:
        return np.arange(count)

    return np.unique(
        np.r_[ranked[:limit], np.argmax(heights), np.argmin(heights)]
    )


def add_3d_bar_labels(ax, config):
    """给三维柱状图/直方图打柱顶数值标签。"""

    if not config.get("show_values", False):
        return

    heights = np.asarray(config["dz"], dtype=float)
    indices = _select_value_indices(heights, config)

    if len(indices) == 0:
        return

    options = {"fontsize": 8, "ha": "center", "va": "bottom", "color": "black"}
    options.update(config.get("value_kwargs") or {})

    offset = float(config.get("value_offset", 0.03))
    scale = max(
        float(np.ptp(heights)),
        float(np.max(np.abs(heights))),
        1.0,
    )
    offset_value = offset * scale

    dx = np.asarray(config["dx"], dtype=float)
    dy = np.asarray(config["dy"], dtype=float)

    for index in np.asarray(indices, dtype=int):
        height = heights[index]

        ax.text(
            config["x"][index] + dx[index] / 2,
            config["y"][index] + dy[index] / 2,
            config["z"][index] + height + offset_value,
            format_value(height, config.get("value_format", ".2f")),
            **options,
        )


def _resolve_colormap(cmap, error_message):
    """把颜色映射名称或对象统一成可调用的 Colormap。"""

    import matplotlib.pyplot as plt

    if isinstance(cmap, str):
        return plt.get_cmap(cmap)

    if not callable(cmap):
        raise TypeError(error_message)

    return cmap


# ----------------------------------------------------------------------
# 绘制处理器
# ----------------------------------------------------------------------


def draw_surface(ax, config):
    """三维曲面：``ax.plot_surface`` + 可选光照增强与颜色条。"""

    X = config["x"]
    Y = config["y"]
    Z = config["data"]

    kwargs = config["kwargs"].copy()
    scalar_map = None
    light_enhance = config.get("light_enhance")

    if light_enhance:
        light_options = (
            light_enhance.copy() if isinstance(light_enhance, dict) else {}
        )

        light_source = LightSource(
            azdeg=light_options.pop("azdeg", 315),
            altdeg=light_options.pop("altdeg", 55),
        )

        gamma = light_options.pop("gamma", 0.65)
        vert_exag = light_options.pop("vert_exag", 1.8)
        blend_mode = light_options.pop("blend_mode", "soft")

        vmin = light_options.pop("vmin", np.percentile(Z, 2))
        vmax = light_options.pop("vmax", np.percentile(Z, 98))
        cmap = light_options.pop("cmap", kwargs.get("cmap", cm.turbo))

        # LightSource.shade() 要求 cmap 可调用，
        # 因此字符串形式的颜色映射名在这里先转换一次。
        cmap = _resolve_colormap(
            cmap,
            "light_enhance中的cmap必须是颜色映射名称字符串，"
            "或者可调用的Matplotlib Colormap对象",
        )

        norm = PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)

        face_colors = light_source.shade(
            Z,
            cmap=cmap,
            norm=norm,
            vert_exag=vert_exag,
            blend_mode=blend_mode,
        )

        # 将光照结果真正传入曲面
        kwargs["facecolors"] = face_colors
        kwargs["shade"] = False

        scalar_map = cm.ScalarMappable(norm=norm, cmap=cmap)
        scalar_map.set_array(Z)

    surface = ax.plot_surface(X, Y, Z, **kwargs)

    if config["label"] is not None:
        surface.set_label(config["label"])

    if config.get("colorbar", False):
        colorbar_mappable = scalar_map if scalar_map is not None else surface

        ax.figure.colorbar(
            colorbar_mappable, ax=ax, **config["colorbar_kwargs"]
        )


def draw_line3d(ax, config):
    """三维曲线：``ax.plot``，默认给一个大 ``zorder`` 压在曲面之上。"""

    kwargs = config["kwargs"].copy()

    if config["label"] is not None:
        kwargs["label"] = config["label"]

    # 三维的遮挡由 artist 的绘制顺序决定，zorder 影响的是“谁后画”。
    # 在曲面之上画轨迹时给一个大 zorder，轨迹才不会被曲面盖住。
    kwargs.setdefault("zorder", config["highlight_zorder"])

    ax.plot(config["x"], config["y"], config["z"], **kwargs)


def draw_scatter3d(ax, config):
    """三维散点：``ax.scatter``，同样支持 ``highlight_zorder``。"""

    kwargs = config["kwargs"].copy()

    if config["label"] is not None:
        kwargs["label"] = config["label"]

    kwargs.setdefault("zorder", config["highlight_zorder"])

    ax.scatter(config["x"], config["y"], config["z"], **kwargs)


def draw_bar3d(ax, config):
    """三维柱状图：``ax.bar3d`` + 可选柱顶数值。"""

    kwargs = config["kwargs"].copy()

    bars = ax.bar3d(
        config["x"],
        config["y"],
        config["z"],
        config["dx"],
        config["dy"],
        config["dz"],
        **kwargs,
    )

    if config["label"] is not None:
        bars.set_label(config["label"])

    add_3d_bar_labels(ax, config)


def draw_hist3d(ax, config):
    """三维直方图：按柱高自动着色后调用 ``ax.bar3d``。"""

    kwargs = config["kwargs"].copy()
    heights = np.asarray(config["dz"], dtype=float)

    # cmap 只用于自动着色，不直接传给 bar3d
    cmap = kwargs.pop("cmap", cm.viridis)

    if "color" not in kwargs:
        if np.allclose(heights.min(), heights.max()):
            norm = Normalize(vmin=heights.min() - 1, vmax=heights.max() + 1)
        else:
            norm = Normalize(vmin=heights.min(), vmax=heights.max())

        cmap = _resolve_colormap(
            cmap,
            "cmap必须是颜色映射名称字符串，"
            "或者可调用的Matplotlib Colormap对象",
        )

        kwargs["color"] = cmap(norm(heights))

    bars = ax.bar3d(
        config["x"],
        config["y"],
        config["z"],
        config["dx"],
        config["dy"],
        config["dz"],
        **kwargs,
    )

    if config["label"] is not None:
        bars.set_label(config["label"])

    add_3d_bar_labels(ax, config)


#: 三维 ``kind`` -> 绘制处理器。
DRAW_HANDLERS = {
    "surface": draw_surface,
    "line3d": draw_line3d,
    "scatter3d": draw_scatter3d,
    "bar3d": draw_bar3d,
    "hist3d": draw_hist3d,
}


# ----------------------------------------------------------------------
# 添加图层（Mixin）
# ----------------------------------------------------------------------


class ThreeDLayersMixin:
    """三维图层的 ``add_*`` 方法。"""

    def add_surface(
        self,
        x,
        y,
        z,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        zlabel="Z",
        label=None,
        legend=False,
        legend_kwargs=None,
        colorbar=False,
        colorbar_kwargs=None,
        light_enhance=None,
        view=None,
        **kwargs,
    ):
        """添加三维曲面。

        示例::

            plotter.add_surface(
                X, Y, Z, subplot=0, cmap="turbo",
                edgecolor="none", light_enhance=True,
            )
        """

        X, Y, Z = mesh_coordinates(x, y, z)

        return self._register_layer(
            "surface",
            dimension=3,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            zlabel=zlabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            axis="",
            view=view,
            kwargs=kwargs,
            x=X,
            y=Y,
            z=None,
            data=Z,
            colorbar=colorbar,
            colorbar_kwargs=colorbar_kwargs or {},
            light_enhance=light_enhance,
        )

    def add_line3d(
        self,
        x,
        y,
        z,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        zlabel="Z",
        label=None,
        legend=False,
        legend_kwargs=None,
        view: dict = None,
        highlight_zorder=100,
        show_values=False,
        value_format=".2f",
        value_offset=0.03,
        value_kwargs=None,
        **kwargs,
    ):
        """添加三维曲线，适合绘制梯度下降轨迹。

        与曲面叠加时，三维的遮挡关系由“谁后画”决定，
        本方法默认给它一个较大的 ``zorder``（``highlight_zorder=100``），
        让轨迹压在曲面之上，不会被曲面挡住。
        """

        x = as_1d_array(x, "x")
        y = as_1d_array(y, "y")
        z = as_1d_array(z, "z")

        check_same_length(x, y, z)

        return self._register_layer(
            "line3d",
            dimension=3,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            zlabel=zlabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            axis="",
            view=view,
            kwargs=kwargs,
            x=x,
            y=y,
            z=z,
            data=None,
            highlight_zorder=highlight_zorder,
            show_values=show_values,
            value_format=value_format,
            value_offset=value_offset,
            value_kwargs=value_kwargs or {},
        )

    def add_scatter3d(
        self,
        x,
        y,
        z,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        zlabel="Z",
        label=None,
        legend=False,
        legend_kwargs=None,
        view: dict = None,
        highlight_zorder=101,
        show_values=False,
        value_format=".0f",
        value_offset=0.03,
        value_kwargs=None,
        **kwargs,
    ):
        """添加三维散点。

        ``x``、``y``、``z`` 可以是标量，也可以是一维数组。

        与曲面叠加时同样会默认给一个较大的 ``zorder``
        （``highlight_zorder=101``，比 ``add_line3d`` 的 100 更大，
        保证起点/终点标记画在轨迹之上）。
        """

        x = as_1d_array(x, "x")
        y = as_1d_array(y, "y")
        z = as_1d_array(z, "z")

        check_same_length(x, y, z)

        return self._register_layer(
            "scatter3d",
            dimension=3,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            zlabel=zlabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            axis="",
            view=view,
            kwargs=kwargs,
            x=x,
            y=y,
            z=z,
            data=None,
            highlight_zorder=highlight_zorder,
            show_values=show_values,
            value_format=value_format,
            value_offset=value_offset,
            value_kwargs=value_kwargs or {},
        )

    def add_bar3d(
        self,
        x,
        y,
        z,
        dx,   # dx dy dz 为每个小立方体在三个维度上的边长
        dy,
        dz,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        zlabel="Z",
        label=None,
        legend=False,
        legend_kwargs=None,
        view: dict = None,
        show_values=False,
        value_format=".2f",
        value_offset=0.03,
        value_kwargs=None,
        value_selection="auto",
        max_value_labels=20,
        value_threshold=None,
        **kwargs,
    ):
        """添加三维柱状图。

        ``x``、``y``、``z`` 为每个柱子的起始坐标；
        ``dx``、``dy``、``dz`` 为柱子的宽度、深度和高度。
        """

        x = as_1d_array(x, "x")
        y = as_1d_array(y, "y")
        z = as_1d_array(z, "z")

        check_same_length(x, y, z)

        n = len(x)

        dx = broadcast_to_length(dx, n, "dx")
        dy = broadcast_to_length(dy, n, "dy")
        dz = broadcast_to_length(dz, n, "dz")

        return self._register_layer(
            "bar3d",
            dimension=3,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            zlabel=zlabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            axis="",
            view=view,
            kwargs=kwargs,
            x=x,
            y=y,
            z=z,
            dx=dx,
            dy=dy,
            dz=dz,
            data=None,
            show_values=show_values,
            value_format=value_format,
            value_offset=value_offset,
            value_kwargs=value_kwargs or {},
            value_selection=value_selection,
            max_value_labels=max_value_labels,
            value_threshold=value_threshold,
        )

    def add_hist3d(
        self,
        x,
        y,
        bins=10,
        range=None,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        zlabel="Count",
        label=None,
        legend=False,
        legend_kwargs=None,
        view: dict = None,
        show_values=False,
        value_format=".0f",
        value_offset=0.03,
        value_kwargs=None,
        value_selection="auto",
        max_value_labels=20,
        value_threshold=None,
        **kwargs,
    ):
        """添加三维直方图。

        通过 ``numpy.histogram2d`` 统计二维样本，
        再使用三维柱状图显示每个网格中的样本数量。
        """

        x = as_1d_array(x, "x")
        y = as_1d_array(y, "y")

        check_same_length(x, y)

        counts, x_edges, y_edges = np.histogram2d(
            x, y, bins=bins, range=range
        )

        x_pos, y_pos = np.meshgrid(
            x_edges[:-1], y_edges[:-1], indexing="ij"
        )
        dx_grid, dy_grid = np.meshgrid(
            np.diff(x_edges), np.diff(y_edges), indexing="ij"
        )

        x_pos = x_pos.ravel()
        y_pos = y_pos.ravel()
        dx_values = dx_grid.ravel()
        dy_values = dy_grid.ravel()
        heights = counts.ravel()

        # 高度为0的柱子不绘制，避免图形拥挤
        valid = heights > 0

        return self._register_layer(
            "hist3d",
            dimension=3,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            zlabel=zlabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            axis="",
            view=view,
            kwargs=kwargs,
            x=x_pos[valid],
            y=y_pos[valid],
            z=np.zeros(np.sum(valid)),
            dx=dx_values[valid],
            dy=dy_values[valid],
            dz=heights[valid],
            data=counts,
            x_edges=x_edges,
            y_edges=y_edges,
            show_values=show_values,
            value_format=value_format,
            value_offset=value_offset,
            value_kwargs=value_kwargs or {},
            value_selection=value_selection,
            max_value_labels=max_value_labels,
            value_threshold=value_threshold,
        )


__all__ = [
    "ThreeDLayersMixin",
    "DRAW_HANDLERS",
    "VALUE_SELECTIONS",
    "add_3d_bar_labels",
    "draw_surface",
    "draw_line3d",
    "draw_scatter3d",
    "draw_bar3d",
    "draw_hist3d",
]
