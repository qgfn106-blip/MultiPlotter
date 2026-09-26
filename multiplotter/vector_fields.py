# -*- coding: utf-8 -*-
"""矢量场图层：二维箭头/流线、三维箭头/流线。

三维流线没有现成的 Matplotlib 接口，这里用四阶龙格-库塔法（RK4）
对解析矢量场积分，得到空间中的轨迹线。

公开 API
--------
绘制处理器
    ``draw_quiver`` / ``draw_streamplot`` / ``draw_quiver3d`` / ``draw_stream3d``
辅助
    ``build_seeds`` / ``draw_colored_polyline`` / ``speed_along``
登记
    ``VectorFieldLayersMixin``
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize

from .validation import (
    field_coordinates,
    field_coordinates_3d,
    field_norm,
    integrate_streamline,
    shrink_field,
)

# ----------------------------------------------------------------------
# 辅助
# ----------------------------------------------------------------------


def build_seeds(config):
    """生成三维流线的起点。

    优先使用用户给定的 ``seeds``；否则在边界盒内侧的球面上均匀撒点
    （Fibonacci 球面 + 少量随机扰动，结果可复现）。
    """

    bound = config["bound"]

    if config["seeds"] is not None:
        seeds = np.atleast_2d(config["seeds"])

        if seeds.shape[1] != 3:
            raise ValueError(
                "seeds 必须是 (n, 3) 的坐标，"
                f"当前形状为{seeds.shape}"
            )

        return seeds

    n_seeds = config["n_seeds"]

    if n_seeds < 1:
        raise ValueError(f"n_seeds 至少为1，当前为{n_seeds}")

    center = np.array([(low + high) / 2.0 for low, high in bound])
    span = np.array([(high - low) / 2.0 for low, high in bound])
    radius = float(config["seed_radius"])

    rng = np.random.default_rng(config["seed"])

    indices = np.arange(n_seeds) + 0.5
    phi = np.arccos(1.0 - 2.0 * indices / n_seeds)
    theta = np.pi * (1.0 + 5.0 ** 0.5) * indices

    unit = np.column_stack([
        np.cos(theta) * np.sin(phi),
        np.sin(theta) * np.sin(phi),
        np.cos(phi),
    ])

    # 加上一点随机扰动，避免所有流线过于规整
    unit = unit + 0.05 * rng.normal(size=unit.shape)
    unit /= np.linalg.norm(unit, axis=1, keepdims=True)

    return center + unit * (span * radius)


def draw_colored_polyline(ax, trajectory, values, cmap, norm, line_width,
                          extra_kwargs=None):
    """把一条折线按数值着色后画出来。

    三维的 ``Axes3D`` 没有直接支持“按标量给折线分段着色”的接口，
    这里把折线按线段拆开，每段单独画一条 ``Line3D``。
    """

    extra_kwargs = extra_kwargs or {}

    for index in range(len(trajectory) - 1):
        segment = trajectory[index:index + 2]
        color = cmap(norm(0.5 * (values[index] + values[index + 1])))

        ax.plot(
            segment[:, 0],
            segment[:, 1],
            segment[:, 2],
            color=color,
            linewidth=line_width,
            **extra_kwargs,
        )


def speed_along(trajectory, field):
    """计算流线每个点上的速度大小，用于按速度着色。"""

    speeds = np.empty(len(trajectory), dtype=float)

    for index, point in enumerate(trajectory):
        speed = np.asarray(
            field(point[0], point[1], point[2]), dtype=float
        )
        speeds[index] = float(np.linalg.norm(speed))

    return speeds


def _check_color_conflict(color, color_by, flag_name):
    """``color`` 与「按数值着色」互斥，提前报错比画错图友好。"""

    if color is not None and color_by:
        raise ValueError(
            f"color 与 {flag_name}=True 冲突："
            "固定颜色时请设置 "
            f"{flag_name}=False"
        )


# ----------------------------------------------------------------------
# 绘制处理器
# ----------------------------------------------------------------------


def draw_quiver(ax, config):
    """二维矢量场箭头：``ax.quiver``。"""

    kwargs = config["kwargs"].copy()
    quiver_kwargs = {"pivot": config["pivot"]}

    if config["scale"] is not None:
        quiver_kwargs["scale"] = config["scale"]

    if config["color_by_magnitude"]:
        # 用模长决定箭头颜色，并保留颜色条所需的归一化
        vmin = config.get("vmin")
        vmax = config.get("vmax")

        if vmin is None:
            vmin = float(np.min(config["data"]))

        if vmax is None:
            vmax = float(np.max(config["data"]))

        norm = Normalize(vmin=float(vmin), vmax=float(vmax))
        quiver_kwargs["angles"] = kwargs.pop("angles", "xy")

        quiver = ax.quiver(
            config["x"],
            config["y"],
            config["u"],
            config["v"],
            config["data"],
            cmap=config["cmap"],
            norm=norm,
            **quiver_kwargs,
            **kwargs,
        )

        if config["colorbar"]:
            ax.figure.colorbar(
                quiver, ax=ax, **config["colorbar_kwargs"]
            )
    else:
        if config["color"] is not None:
            quiver_kwargs["color"] = config["color"]

        quiver = ax.quiver(
            config["x"],
            config["y"],
            config["u"],
            config["v"],
            **quiver_kwargs,
            **kwargs,
        )

    if config["label"] is not None:
        quiver.set_label(config["label"])


def draw_streamplot(ax, config):
    """二维矢量场流线：``ax.streamplot``。"""

    kwargs = config["kwargs"].copy()

    stream_kwargs = {
        "density": config["density"],
        "linewidth": config["line_width"],
        "arrowsize": config["arrowsize"],
        "arrowstyle": config["arrowstyle"],
        "maxlength": config["maxlength"],
        "integration_direction": config["integration_direction"],
    }

    if config["color_by_magnitude"]:
        stream_kwargs["color"] = config["data"]
        stream_kwargs["cmap"] = config["cmap"]
    elif config["color"] is not None:
        stream_kwargs["color"] = config["color"]

    # matplotlib 3.6 以下没有 broken_streamlines 参数，低版本自动忽略
    stream, dropped = _streamplot_with_optional(
        ax,
        config,
        stream_kwargs,
        kwargs,
        {"broken_streamlines": config["broken_streamlines"]},
    )

    if dropped:
        from .compat import warn_version

        warn_version(
            "当前 Matplotlib 不支持 streamplot(broken_streamlines=...)；"
            f"已忽略该参数（{dropped}）。",
            stacklevel=4,
        )

    if config["colorbar"] and config["color_by_magnitude"]:
        ax.figure.colorbar(
            stream.lines, ax=ax, **config["colorbar_kwargs"]
        )


def _streamplot_with_optional(ax, config, stream_kwargs, kwargs, optional):
    """先带可选参数调用 ``streamplot``，不支持时退回不带可选参数的调用。"""

    try:
        stream = ax.streamplot(
            config["x"],
            config["y"],
            config["u"],
            config["v"],
            **optional,
            **stream_kwargs,
            **kwargs,
        )
        return stream, []

    except TypeError:
        stream = ax.streamplot(
            config["x"],
            config["y"],
            config["u"],
            config["v"],
            **stream_kwargs,
            **kwargs,
        )
        return stream, sorted(optional)


def draw_quiver3d(ax, config):
    """三维矢量场箭头：``ax.quiver``（先按密度抽稀）。"""

    kwargs = config["kwargs"].copy()

    # 按密度抽稀，避免箭头重叠
    qx, qy, qz, qu, qv, qw = shrink_field(
        config["x"],
        config["y"],
        config["z"],
        config["u"],
        config["v"],
        config["w"],
        density=config["density"],
    )

    quiver_kwargs = {
        "length": config["length"],
        "normalize": config["normalize"],
        "arrow_length_ratio": config["arrow_length_ratio"],
    }

    if config["color_by_magnitude"]:
        # Axes3D.quiver 没有 Axes.quiver 的 C 参数，
        # 所以这里先把模长映射成 RGBA，再交给 colors=，
        # 颜色条用单独的 ScalarMappable。
        norm = Normalize(
            vmin=float(np.min(config["data"])),
            vmax=float(np.max(config["data"])),
        )
        cmap_obj = plt.get_cmap(config["cmap"])
        magnitudes = field_norm(qu, qv, qw)

        quiver = ax.quiver(
            qx, qy, qz, qu, qv, qw,
            colors=cmap_obj(norm(magnitudes)),
            **quiver_kwargs,
            **kwargs,
        )

        if config["colorbar"]:
            color_mappable = cm.ScalarMappable(norm=norm, cmap=cmap_obj)
            color_mappable.set_array(magnitudes)

            ax.figure.colorbar(
                color_mappable, ax=ax, **config["colorbar_kwargs"]
            )
    else:
        if config["color"] is not None:
            quiver_kwargs["color"] = config["color"]

        quiver = ax.quiver(
            qx, qy, qz, qu, qv, qw, **quiver_kwargs, **kwargs
        )

    if config["label"] is not None:
        quiver.set_label(config["label"])


def draw_stream3d(ax, config):
    """三维矢量场流线：RK4 积分解析场得到轨迹线。"""

    # kwargs 只属于其它分支，这里单独取一份，避免误引用
    stream_kwargs = config["kwargs"].copy()

    # 用连续场做 RK4 积分，所以需要一个解析的场函数
    field = config["field_func"]

    if field is None:
        raise ValueError(
            "三维流线需要矢量场的解析表达式：\n"
            "  add_stream3d(..., field_func=lambda x, y, z: (u, v, w))\n"
            "只有离散网格时请改用 add_quiver3d()。"
        )

    seeds = build_seeds(config)
    trajectories = []

    for point in seeds:
        forward = integrate_streamline(
            point,
            field,
            step=config["step_size"],
            direction=1.0,
            bound=config["bound"],
            max_steps=config["max_steps"],
        )

        if config["both_directions"]:
            backward = integrate_streamline(
                point,
                field,
                step=config["step_size"],
                direction=-1.0,
                bound=config["bound"],
                max_steps=config["max_steps"],
            )

            if backward is not None and forward is not None:
                trajectory = np.vstack([backward[::-1][:-1], forward])
            else:
                trajectory = forward
        else:
            trajectory = forward

        if trajectory is not None and len(trajectory) >= 2:
            # 驻点或几乎停滞的轨迹没有意义，直接丢掉
            speeds = speed_along(trajectory, field)

            if float(np.max(speeds)) <= 1e-9:
                continue

            trajectories.append(trajectory)

    if not trajectories:
        raise ValueError(
            "没有积分出任何三维流线，请检查：\n"
            "  1) seeds 是否落在边界内部；\n"
            "  2) 矢量场是否在起点附近为0（驻点）；\n"
            "  3) step_size 是否过大导致一步跨出边界。"
        )

    color_mappable = None

    if config["color_by_speed"]:
        cmap_obj = plt.get_cmap(config["cmap"])
        all_speeds = np.concatenate([
            speed_along(trajectory, field) for trajectory in trajectories
        ])
        norm = Normalize(
            vmin=float(np.min(all_speeds)),
            vmax=float(np.max(all_speeds)),
        )

        for trajectory in trajectories:
            draw_colored_polyline(
                ax,
                trajectory,
                speed_along(trajectory, field),
                cmap_obj,
                norm,
                config["line_width"],
                stream_kwargs,
            )

        color_mappable = cm.ScalarMappable(norm=norm, cmap=cmap_obj)
        color_mappable.set_array(all_speeds)
    else:
        line_kwargs = dict(stream_kwargs)
        line_kwargs["linewidth"] = config["line_width"]

        if config["color"] is not None:
            line_kwargs["color"] = config["color"]

        first_line = None

        for trajectory in trajectories:
            line, = ax.plot(
                trajectory[:, 0],
                trajectory[:, 1],
                trajectory[:, 2],
                **line_kwargs,
            )

            if first_line is None:
                first_line = line

        if config["label"] is not None and first_line is not None:
            first_line.set_label(config["label"])

    if config["colorbar"] and color_mappable is not None:
        ax.figure.colorbar(
            color_mappable, ax=ax, **config["colorbar_kwargs"]
        )


#: 矢量场 ``kind`` -> 绘制处理器（二维 + 三维）。
DRAW_HANDLERS = {
    "quiver": draw_quiver,
    "streamplot": draw_streamplot,
    "quiver3d": draw_quiver3d,
    "stream3d": draw_stream3d,
}


# ----------------------------------------------------------------------
# 添加图层（Mixin）
# ----------------------------------------------------------------------


class VectorFieldLayersMixin:
    """矢量场图层的 ``add_*`` 方法。"""

    def add_quiver(
        self,
        x,
        y,
        u,
        v,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        label=None,
        legend=False,
        legend_kwargs=None,
        axis="equal",
        view=None,
        scale=None,
        color=None,
        cmap="viridis",
        color_by_magnitude=True,
        vmin=None,
        vmax=None,
        colorbar=False,
        colorbar_kwargs=None,
        pivot="tail",
        **kwargs,
    ):
        """添加二维矢量场箭头图。

        ``x``、``y`` 可以是：

        * 一维坐标：自动 ``meshgrid``，``u``、``v`` 形状需为
          ``(len(y), len(x))``
        * 二维网格：``u``、``v`` 形状需与 ``x``、``y`` 完全一致

        常见用法（流体力学流场）::

            plotter.add_quiver(
                X, Y, U, V, subplot=0, title="速度场",
                scale=30, cmap="turbo", colorbar=True,
                colorbar_kwargs={"label": "|V|"},
                view={"xlim": (0, 1), "ylim": (0, 1)},
            )

        动画时可以用 ``Axes.quiver`` 的 ``set_UVC()`` 原地更新。
        """

        X, Y, U, V = field_coordinates(x, y, u, v)
        magnitude = field_norm(U, V)

        _check_color_conflict(color, color_by_magnitude, "color_by_magnitude")

        return self._register_layer(
            "quiver",
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
            x=X,
            y=Y,
            z=None,
            u=U,
            v=V,
            w=None,
            data=magnitude,
            scale=scale,
            color=color,
            cmap=cmap,
            color_by_magnitude=color_by_magnitude,
            vmin=vmin,
            vmax=vmax,
            colorbar=colorbar,
            colorbar_kwargs=colorbar_kwargs or {},
            pivot=pivot,
        )

    def add_streamplot(
        self,
        x,
        y,
        u,
        v,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        label=None,
        legend=False,
        legend_kwargs=None,
        axis="equal",
        view=None,
        density=1.2,
        line_width=1.4,
        cmap="viridis",
        color=None,
        color_by_magnitude=True,
        arrowsize=1.2,
        arrowstyle="-|>",
        maxlength=4.0,
        integration_direction="both",
        broken_streamlines=True,
        colorbar=False,
        colorbar_kwargs=None,
        **kwargs,
    ):
        """添加二维矢量场流线图。

        流线由 Matplotlib 的 ``Axes.streamplot()`` 计算，
        起点是自动撒的，所以非常适合展示流体流动的方向和漩涡。

        注意：

        * ``streamplot`` 要求网格至少是 2x2 且不能退化成一条线；
        * 网格很密时 ``density`` 会自动按网格大小缩放，
          也可以传 ``(density_x, density_y)``；
        * matplotlib 3.6 以下不支持 ``broken_streamlines`` 参数，
          低版本会自动忽略并给出提示。
        """

        X, Y, U, V = field_coordinates(x, y, u, v)
        magnitude = field_norm(U, V)

        if X.shape[0] < 2 or X.shape[1] < 2:
            raise ValueError(
                "streamplot 的网格至少需要 2x2，"
                f"当前形状为{X.shape}"
            )

        _check_color_conflict(color, color_by_magnitude, "color_by_magnitude")

        return self._register_layer(
            "streamplot",
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
            x=X,
            y=Y,
            z=None,
            u=U,
            v=V,
            w=None,
            data=magnitude,
            density=density,
            line_width=line_width,
            cmap=cmap,
            color=color,
            color_by_magnitude=color_by_magnitude,
            arrowsize=arrowsize,
            arrowstyle=arrowstyle,
            maxlength=maxlength,
            integration_direction=integration_direction,
            broken_streamlines=broken_streamlines,
            colorbar=colorbar,
            colorbar_kwargs=colorbar_kwargs or {},
        )

    def add_quiver3d(
        self,
        x,
        y,
        z,
        u,
        v,
        w,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        zlabel="Z",
        label=None,
        legend=False,
        legend_kwargs=None,
        view=None,
        density=18,
        length=0.8,
        normalize=True,
        color=None,
        cmap="viridis",
        color_by_magnitude=True,
        colorbar=False,
        colorbar_kwargs=None,
        arrow_length_ratio=0.3,
        **kwargs,
    ):
        """添加三维矢量场箭头图。

        ``x``、``y``、``z`` 可以是一维坐标（自动生成网格）或三维网格，
        ``u``、``v``、``w`` 需与网格形状一致。

        ``density`` 控制抽稀：网格很密时只保留大约 ``density`` 个箭头/每轴，
        避免箭头糊成一团。

        动画时可以用 ``Axes3D.quiver`` 的 ``set_segments()`` 原地更新。
        """

        X, Y, Z, U, V, W = field_coordinates_3d(x, y, z, u, v, w)

        _check_color_conflict(color, color_by_magnitude, "color_by_magnitude")

        if int(density) < 1:
            raise ValueError(f"density 必须是正整数，当前为{density}")

        magnitudes = field_norm(U, V, W)

        return self._register_layer(
            "quiver3d",
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
            z=Z,
            u=U,
            v=V,
            w=W,
            data=magnitudes,
            density=density,
            length=length,
            normalize=normalize,
            color=color,
            cmap=cmap,
            color_by_magnitude=color_by_magnitude,
            colorbar=colorbar,
            colorbar_kwargs=colorbar_kwargs or {},
            arrow_length_ratio=arrow_length_ratio,
        )

    def add_stream3d(
        self,
        x,
        y,
        z,
        u,
        v,
        w,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        zlabel="Z",
        label=None,
        legend=False,
        legend_kwargs=None,
        view=None,
        seeds=None,
        field_func=None,
        n_seeds=8,
        seed_radius=0.6,
        step_size=0.04,
        max_steps=600,
        both_directions=True,
        line_width=2.0,
        cmap="viridis",
        color=None,
        color_by_speed=True,
        colorbar=False,
        colorbar_kwargs=None,
        seed=0,
        **kwargs,
    ):
        """添加三维矢量场流线（对三维场做 RK4 积分得到空间中的轨迹线）。

        为什么不用 Matplotlib 的 ``streamplot``：它只支持二维。
        三维流线需要自己积分，这里用四阶龙格-库塔法逐步推进，
        遇到边界或步数上限就停止。

        参数
        ----
        seeds
            起点坐标，形如 ``[(x, y, z), ...]``；
            给了 ``seeds`` 就忽略 ``n_seeds`` / ``seed_radius``
        field_func
            矢量场的解析表达式 ``field_func(x, y, z) -> (u, v, w)``；
            三维流线靠它做 RK4 积分，必须提供。
            如果只有离散网格数据，请改用 ``add_quiver3d()``
        n_seeds
            自动撒点数量（默认 8 条流线）
        seed_radius
            自动撒点时，起点分布在以域中心为球心、
            半径为 ``seed_radius`` 的球面上
        step_size
            积分步长（数据坐标单位）
        max_steps
            单条流线最多积分多少步
        both_directions
            ``True`` 时正反两个方向都积分并拼接
        line_width
            流线线宽（同一条流线用同一线宽）
        cmap
            按速度着色时使用的颜色映射
        color
            固定颜色；与 ``color_by_speed=True`` 冲突
        color_by_speed
            ``True`` 时按流线经过位置的速度着色
        seed
            自动撒点的随机种子，保证结果可复现

        说明：网格只用来确定域的边界（min / max），不参与插值，
        所以流线是「解析场」的积分结果。
        """

        X, Y, Z, U, V, W = field_coordinates_3d(x, y, z, u, v, w)

        _check_color_conflict(color, color_by_speed, "color_by_speed")

        if float(step_size) <= 0:
            raise ValueError(f"step_size 必须大于0，当前为{step_size}")

        if int(max_steps) < 2:
            raise ValueError(f"max_steps 至少为2，当前为{max_steps}")

        bound = (
            (float(np.min(X)), float(np.max(X))),
            (float(np.min(Y)), float(np.max(Y))),
            (float(np.min(Z)), float(np.max(Z))),
        )

        return self._register_layer(
            "stream3d",
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
            z=Z,
            u=U,
            v=V,
            w=W,
            data=field_norm(U, V, W),
            seeds=None if seeds is None else np.asarray(seeds, dtype=float),
            field_func=field_func,
            n_seeds=int(n_seeds),
            seed_radius=float(seed_radius),
            step_size=float(step_size),
            max_steps=int(max_steps),
            both_directions=both_directions,
            line_width=line_width,
            cmap=cmap,
            color=color,
            color_by_speed=color_by_speed,
            colorbar=colorbar,
            colorbar_kwargs=colorbar_kwargs or {},
            seed=seed,
            bound=bound,
        )


__all__ = [
    "VectorFieldLayersMixin",
    "DRAW_HANDLERS",
    "build_seeds",
    "draw_colored_polyline",
    "speed_along",
    "draw_quiver",
    "draw_streamplot",
    "draw_quiver3d",
    "draw_stream3d",
]
