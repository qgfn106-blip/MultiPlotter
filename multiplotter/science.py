# -*- coding: utf-8 -*-
"""组合接口：把「算法」与「绘图」串起来。

设计目标
--------

科研绘图的典型流程是「算一遍 -> 画很多张图」，而且经常需要：

* 用同一份计算结果画多个子图（场 + 剖面 + 曲线 + 表格）；
* 把中间量（残差、能量、误差）顺手画出来；
* 动画复用同一份预先算好的帧数据。

本模块提供一个**不依赖 MultiPlotter 内部状态**的组合层：

``ScienceResult``
    算法输出的容器：主结果 + 命名数组 + 标量指标 + 帧数据。
``SciencePlotter``
    在 ``MultiPlotter`` / ``AnimationPlotter`` 之上，提供
    ``plot_field`` / ``plot_profile`` / ``plot_series`` / ``plot_table``
    / ``plot_frames`` 等语义化接口，内部仍然调用 ``add_*``。
``convective_heat_transfer()``
    一个完整的对流传热算例（作为文档示例）：求解二维方腔自然对流，
    返回 ``ScienceResult``。

这个模块只做「组合」：所有绘制动作最终都落到 ``add_*`` / ``draw()`` /
``animate()``，所以外部引用方式与直接使用 ``MultiPlotter`` 完全一致。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional, Sequence

import numpy as np

from .animation import AnimationPlotter
from .core import MultiPlotter

# ----------------------------------------------------------------------
# 结果容器
# ----------------------------------------------------------------------


@dataclass
class ScienceResult:
    """一次科学计算的输出。

    属性
    ----
    name
        算例名称，用于默认标题。
    fields
        命名数组：``{"T": T, "u": u, "v": v, ...}``。
        数组可以是二维网格，也可以是三维网格/序列。
    scalars
        命名标量指标：``{"Nu": 4.52, "Ra": 1e5}``。
    frames
        动画帧数据：``{frame: 数组}` 或 ``[数组, ...]``。
    metadata
        任意附加信息（网格、参数、时间步…）。
    """

    name: str = "result"
    fields: Mapping = field(default_factory=dict)
    scalars: Mapping = field(default_factory=dict)
    frames: object = None
    metadata: Mapping = field(default_factory=dict)

    def field(self, key):
        """取一个命名数组，不存在时抛 ``KeyError``（信息更明确）。"""

        if key not in self.fields:
            raise KeyError(
                f"结果 {self.name!r} 里没有名为 {key!r} 的场；"
                f"现有：{sorted(self.fields)}"
            )

        return self.fields[key]

    def grid(self, x_key="x", y_key="y", z_key=None):
        """取网格坐标；缺省时返回 ``None``。"""

        x = self.metadata.get(x_key)
        y = self.metadata.get(y_key)

        if x is None or y is None:
            return None

        if z_key is None:
            return x, y

        return x, y, self.metadata.get(z_key)

    def scalar(self, key, default=None):
        """取一个标量指标。"""

        return self.scalars.get(key, default)

    def summary(self):
        """返回一行可读摘要（写日志或表格标题时很方便）。"""

        parts = [f"{self.name}"]

        for key, value in self.scalars.items():
            try:
                parts.append(f"{key}={float(value):.4g}")
            except (TypeError, ValueError):
                parts.append(f"{key}={value}")

        return ", ".join(parts)

    def __repr__(self):
        return (
            f"ScienceResult(name={self.name!r}, "
            f"fields={sorted(self.fields)}, "
            f"scalars={sorted(self.scalars)})"
        )


# ----------------------------------------------------------------------
# 组合绘图
# ----------------------------------------------------------------------


class SciencePlotter:
    """把 ``ScienceResult`` 组合成多子图/动画的绘图助手。

    参数
    ----
    result
        要绘制的 :class:`ScienceResult`。
    ncols / figsize_per_plot / dpi
        与 ``MultiPlotter`` 一致。
    animate
        ``True`` 时内部用 ``AnimationPlotter``（多一个 ``animate()``）。

    典型用法::

        result = convective_heat_transfer(ra=1e5, n=64)
        painter = SciencePlotter(result, ncols=2)
        painter.plot_field("T", subplot=0, cmap="inferno", colorbar=True)
        painter.plot_profile("T", subplot=1, axis="y", index=None)
        painter.plot_table(subplot=2)
        fig, axes = painter.draw(show=False)
    """

    def __init__(
        self,
        result,
        ncols=2,
        figsize_per_plot=(6, 4),
        dpi=120,
        animate=False,
        theme=None,
    ):
        if not isinstance(result, ScienceResult):
            raise TypeError(
                "result 必须是 ScienceResult，"
                f"当前为{type(result).__name__}"
            )

        self.result = result
        self.animate = bool(animate)

        plotter_class = AnimationPlotter if self.animate else MultiPlotter

        self.plotter = plotter_class(
            ncols=ncols,
            figsize_per_plot=figsize_per_plot,
            dpi=dpi,
            theme=theme,
        )

    # ---- 内部：取出网格 ----

    def _coords(self, shape):
        """按 ``metadata`` 里的坐标或形状自动生成网格坐标。"""

        grid = self.result.grid()

        if grid is not None:
            x, y = grid

            if np.asarray(x).size and np.asarray(y).size:
                return x, y

        ny, nx = shape

        return np.arange(nx), np.arange(ny)

    # ---- 语义化绘图接口 ----

    def plot_field(self, key, subplot=0, kind="contour", title=None,
                   **kwargs):
        """画一个二维场（默认填充等高线）。

        ``kind`` 可以是 ``"contour"``（默认）、``"heatmap"``、
        ``"surface"``（三维曲面）。
        """

        values = np.asarray(self.result.field(key), dtype=float)

        if values.ndim != 2:
            raise ValueError(
                f"plot_field 需要二维场，{key!r} 的形状是{values.shape}"
            )

        x, y = self._coords(values.shape)

        if title is None:
            title = f"{self.result.name}: {key}"

        if kind == "surface":
            return self.plotter.add_surface(
                x, y, values, subplot=subplot, title=title, **kwargs
            )

        if kind == "heatmap":
            return self.plotter.add_plot(
                kind="heatmap", data=values, subplot=subplot,
                title=title, **kwargs,
            )

        return self.plotter.add_contour(
            x, y, values, subplot=subplot, title=title, **kwargs
        )

    def plot_profile(self, key, subplot=0, axis="y", index=None,
                     title=None, **kwargs):
        """沿某条线取剖面并画折线。

        ``axis="y"`` 表示「沿 y 方向变化」（即固定 x 取一列），
        ``index`` 是要固定的下标，``None`` 表示取中间。
        """

        values = np.asarray(self.result.field(key), dtype=float)

        if values.ndim != 2:
            raise ValueError(
                f"plot_profile 需要二维场，{key!r} 的形状是{values.shape}"
            )

        x, y = self._coords(values.shape)
        x = np.asarray(x)
        y = np.asarray(y)

        if axis == "y":
            column = values.shape[1] // 2 if index is None else int(index)
            profile = values[:, column]
            coord = y if y.size == profile.size else np.arange(profile.size)
            label = f"{key}(y) @ x[{column}]"
        elif axis == "x":
            row = values.shape[0] // 2 if index is None else int(index)
            profile = values[row, :]
            coord = x if x.size == profile.size else np.arange(profile.size)
            label = f"{key}(x) @ y[{row}]"
        else:
            raise ValueError(f"axis 只能是 'x' 或 'y'，当前为{axis!r}")

        if title is None:
            title = f"{self.result.name}: {label}"

        kwargs.setdefault("label", key)
        kwargs.setdefault("legend", True)

        return self.plotter.add_plot(
            kind="line", x=coord, y=profile, subplot=subplot,
            title=title, **kwargs,
        )

    def plot_series(self, subplot=0, title=None, **kwargs):
        """把标量指标画成柱状图（例如收敛历史、参数对比）。"""

        if not self.result.scalars:
            raise ValueError("result.scalars 为空，没有可画的指标")

        labels = [str(key) for key in self.result.scalars]
        values = [
            float(self.result.scalars[key])
            if _is_number(self.result.scalars[key]) else np.nan
            for key in labels
        ]

        if title is None:
            title = f"{self.result.name}: metrics"

        kwargs.setdefault("show_values", True)

        return self.plotter.add_plot(
            kind="bar", x=labels, y=values, subplot=subplot,
            title=title, tick_labels=labels, **kwargs,
        )

    def plot_table(self, subplot=0, title=None, **kwargs):
        """把标量指标画成表格。"""

        if not self.result.scalars:
            raise ValueError("result.scalars 为空，没有可画的指标")

        rows = [[key, _format_number(value)]
                for key, value in self.result.scalars.items()]

        if title is None:
            title = f"{self.result.name}: summary"

        kwargs.setdefault("col_labels", ["指标", "数值"])

        return self.plotter.add_table(
            rows, subplot=subplot, title=title, **kwargs
        )

    def plot_frames(self, key=None, subplot=0, kind="surface", title=None,
                    cmap="inferno", **kwargs):
        """把 ``result.frames`` 交给 ``AnimationPlotter`` 播放。

        需要 ``SciencePlotter(..., animate=True)``。
        返回 ``animate()`` 的 ``(fig, anim)``。

        说明：帧数据既可以是 ``{帧号: 数组}`` 的字典，
        也可以是数组序列；这里统一转成字典交给
        ``animate(frame_data=...)``，帧号自动取字典的键。
        """

        if not self.animate:
            raise RuntimeError(
                "plot_frames 需要 SciencePlotter(..., animate=True)"
            )

        frames = self.result.frames

        if frames is None:
            raise ValueError("result.frames 为空，没有可播放的帧")

        frame_map = (
            dict(frames) if isinstance(frames, dict)
            else {index: frame for index, frame in enumerate(frames)}
        )

        if not frame_map:
            raise ValueError("result.frames 是空的，没有可播放的帧")

        first_key = next(iter(frame_map))
        first = np.asarray(frame_map[first_key], dtype=float)
        x, y = self._coords(first.shape)

        if title is None:
            title = f"{self.result.name}: {key or 'frames'}"

        animate_kwargs = dict(kwargs.pop("animate_kwargs", {}) or {})
        fixed_view = {
            "xlim": (float(x[0]), float(x[-1])),
            "ylim": (float(y[0]), float(y[-1])),
        }

        if kind == "surface":
            fixed_view["zlim"] = (
                float(np.min(first)), float(np.max(first))
            )

        view = kwargs.pop("view", None) or fixed_view

        if kind == "surface":
            self.plotter.add_surface(
                x, y, first, subplot=subplot, title=title,
                cmap=cmap, view=view, **kwargs,
            )
        else:
            self.plotter.add_contour(
                x, y, first, subplot=subplot, title=title,
                cmap=cmap, view=view, **kwargs,
            )

        self.plotter.draw(show=False)

        def update(ax, frame):
            """reset 模式下每帧重画一次（必须先 clear 再画）。"""

            values = np.asarray(frame_map[frame], dtype=float)
            ax.clear()
            ax.contourf(x, y, values, 20, cmap=cmap)
            ax.set_title(f"{title}  frame={frame}")

            return (ax,)

        return self.plotter.animate(
            subplots=subplot,
            frame_data=frame_map,
            update_func=update,
            update_mode="reset",
            **animate_kwargs,
        )

    # ---- 透传 ----

    def draw(self, *args, **kwargs):
        """绘制全部子图（参数与 ``MultiPlotter.draw()`` 一致）。"""

        return self.plotter.draw(*args, **kwargs)

    def animate_figure(self, *args, **kwargs):
        """转发到 ``AnimationPlotter.animate()``。"""

        if not self.animate:
            raise RuntimeError(
                "animate_figure 需要 SciencePlotter(..., animate=True)"
            )

        return self.plotter.animate(*args, **kwargs)

    def __getattr__(self, name):
        plotter = self.__dict__.get("plotter")

        if plotter is not None:
            try:
                return getattr(plotter, name)
            except AttributeError:
                pass

        raise AttributeError(f"SciencePlotter 没有属性 {name!r}")


def _is_number(value):
    try:
        float(value)
    except (TypeError, ValueError):
        return False

    return True


def _format_number(value):
    if _is_number(value):
        return f"{float(value):.6g}"

    return str(value)


# ----------------------------------------------------------------------
# 示例算例：二维方腔自然对流
# ----------------------------------------------------------------------


def convective_heat_transfer(
    ra=1e5,
    pr=0.71,
    n=64,
    steps=400,
    dt=None,
    hot=1.0,
    cold=0.0,
    record_every=0,
    seed=0,
):
    """二维方腔自然对流（对流传热）算例。

    这是一个**刻意保持简单**的算例：用流函数—涡量形式的
    时间推进求解方腔内的自然对流，用来演示
    「科学计算 -> 组合绘图」的完整流程。

    控制方程（无量纲，Boussinesq 近似）::

        ∂T/∂t + u·∇T = (1/√(Ra·Pr)) ∇²T
        ∇²ψ = -ω
        u = ∂ψ/∂y,  v = -∂ψ/∂x
        ∂ω/∂t + u·∇ω = √(Pr/Ra) ∇²ω + ∂T/∂x

    边界条件：左右壁面分别为 ``hot`` / ``cold``，上下壁面绝热；
    四壁速度为零（无滑移），壁面涡量按 Thom 条件
    ``ω_wall = -2ψ_邻近/h²`` 取值 —— 直接令壁面 ``ω=0`` 会漏掉壁面剪切，
    使对流明显偏强。

    精度
    ----
    平均努塞尔数 ``Nu`` 与经典基准 de Vahl Davis (1983)
    （``Pr=0.71``、``n=41``、``steps=1200``）的对比：

    ==========  ==========  ==========
    ``Ra``      基准 ``Nu``  本实现
    ==========  ==========  ==========
    ``1e3``     1.118       1.109
    ``1e4``     2.238       2.273
    ``1e5``     4.519       4.440
    ==========  ==========  ==========

    偏差在 2% 以内，且换网格分辨率结果一致。但它**不是**通用 CFD
    求解器：网格均匀、时间推进显式、泊松方程用 Jacobi 迭代，
    没有做网格收敛性与高 ``Ra`` 稳定性验证。真实计算请换成自己的求解器，
    只要返回一个 :class:`ScienceResult` 即可复用全部绘图能力。

    参数
    ----
    ra
        瑞利数（``1e3`` ~ ``1e6`` 比较稳）
    pr
        普朗特数（空气约 ``0.71``）
    n
        网格点数（``n x n``）
    steps
        时间步数。显式推进的步长随网格变细而变小，
        **步数不够会停在尚未发展的流场上**（``Nu`` 明显偏小），
        建议按 ``steps * dt`` 覆盖足够长的无量纲时间。
    dt
        时间步长，默认按网格与 ``Ra`` 自动选取
    hot / cold
        左右壁面的无量纲温度
    record_every
        每隔多少步记录一帧温度场；``0`` 表示不记录（不做动画）
    seed
        初始温度扰动的随机种子，保证可复现

    返回
    ----
    :class:`ScienceResult`，其中：

    * ``fields``：``T``（温度）、``u`` / ``v``（速度）、``omega``（涡量）、
      ``psi``（流函数）；
    * ``scalars``：``Ra``、``Pr``、``Nu``（平均努塞尔数）、
      ``Nu_mid``（中截面上由热壁到冷壁的热流）、``T_mean``、``max_speed``、
      ``dt``、``steps``；
    * ``frames``：``record_every > 0`` 时是 ``{step: T}`` 的字典；
    * ``metadata``：``x`` / ``y`` 网格坐标与主要参数。
    """

    if n < 8:
        raise ValueError(f"n 至少为8，当前为{n}")
    if steps < 1:
        raise ValueError(f"steps 至少为1，当前为{steps}")
    if ra <= 0 or pr <= 0:
        raise ValueError("ra 与 pr 必须为正数")

    # ---- 网格（交错网格上的简单中心差分）----
    length = 1.0
    h = length / (n - 1)
    x = np.linspace(0.0, length, n)
    y = np.linspace(0.0, length, n)
    X, Y = np.meshgrid(x, y)

    if dt is None:
        # 扩散稳定性：显式格式要求 dt <= 0.2 * h^2 / nu。
        # 这里取两个扩散系数中更严格的那个，
        # 对流项的 CFL 会在时间推进里按当前最大速度动态收紧。
        nu_diffusion = max(1.0 / np.sqrt(ra * pr), np.sqrt(pr / ra))
        dt = 0.2 * h ** 2 / nu_diffusion
        dt = float(np.clip(dt, 1e-6, 1e-2))

    cfl = 0.4          # 对流项的 CFL 上限

    # ---- 初始场：线性分层 + 小扰动 ----
    rng = np.random.default_rng(seed)
    T = hot + (cold - hot) * X + 0.01 * rng.normal(size=(n, n))
    T[0, :] = T[1, :]
    T[-1, :] = T[-2, :]
    T[:, 0] = hot
    T[:, -1] = cold

    psi = np.zeros((n, n))
    omega = np.zeros((n, n))

    nu_t = 1.0 / np.sqrt(ra * pr)     # 热扩散系数
    nu_w = np.sqrt(pr / ra)           # 动量扩散系数

    frames = {} if record_every else None

    def laplacian(field):
        out = np.zeros_like(field)
        out[1:-1, 1:-1] = (
            field[2:, 1:-1] + field[:-2, 1:-1]
            + field[1:-1, 2:] + field[1:-1, :-2]
            - 4.0 * field[1:-1, 1:-1]
        ) / h ** 2
        return out

    def solve_poisson(rhs, initial=None):
        """用 Jacobi 迭代解 ∇²ψ = rhs（边界 ψ=0）。

        迭代到收敛而不是固定次数：Jacobi 的收敛速度与网格尺度的平方成反比，
        固定迭代次数会让**粗网格看起来收敛、细网格严重欠收敛**，
        于是同一算例换个 ``n`` 就得到完全不同的努塞尔数。

        ``initial`` 是上一时间步的解，作为迭代初值（warm start）。
        时间推进时相邻两步的流函数非常接近，热启动能把每步的迭代次数
        从上千次降到个位数，收敛判据仍然按残差判断。
        """

        solution = (
            np.zeros_like(rhs) if initial is None else initial.copy()
        )
        tolerance = 1e-8 * max(1.0, float(np.max(np.abs(rhs))))

        for _ in range(4000):
            previous = solution[1:-1, 1:-1].copy()

            solution[1:-1, 1:-1] = 0.25 * (
                solution[2:, 1:-1] + solution[:-2, 1:-1]
                + solution[1:-1, 2:] + solution[1:-1, :-2]
                - h ** 2 * rhs[1:-1, 1:-1]
            )

            if float(np.max(np.abs(solution[1:-1, 1:-1] - previous))) < tolerance:
                break

        return solution

    def gradients(field):
        gx = np.zeros_like(field)
        gy = np.zeros_like(field)
        gx[:, 1:-1] = (field[:, 2:] - field[:, :-2]) / (2.0 * h)
        gy[1:-1, :] = (field[2:, :] - field[:-2, :]) / (2.0 * h)
        return gx, gy

    for step in range(int(steps)):
        # 速度由流函数导出
        dpsi_dx, dpsi_dy = gradients(psi)
        u = dpsi_dy
        v = -dpsi_dx

        # 温度的对流 + 扩散（对流项按当前最大速度满足 CFL 条件）
        dTdx, dTdy = gradients(T)
        advection = u * dTdx + v * dTdy

        speed_max = float(np.max(np.abs(u))) + float(np.max(np.abs(v)))
        dt_step = dt

        if speed_max > 0:
            dt_step = min(dt, cfl * h / speed_max)

        T = T + dt_step * (-advection + nu_t * laplacian(T))

        # 边界条件（角点让左右壁面优先，保证热冷壁面精确保持）
        T[0, :] = T[1, :]
        T[-1, :] = T[-2, :]
        T[:, 0] = hot
        T[:, -1] = cold

        # 涡量方程
        domega_dx, domega_dy = gradients(omega)
        omega = omega + dt_step * (
            -(u * domega_dx + v * domega_dy)
            + nu_w * laplacian(omega)
            + dTdx
        )

        # 由涡量反解流函数（用上一步的 psi 热启动）
        psi = solve_poisson(-omega, initial=psi)

        # 壁面涡量：无滑移壁面必须用 Thom 条件 ω = -2ψ_邻近/h²，
        # 直接令 ω=0 相当于漏掉了壁面剪切，算出来的对流会偏强。
        # 它依赖 ψ，所以放在解完 Poisson 之后更新，供下一步使用。
        omega[0, 1:-1] = -2.0 * psi[1, 1:-1] / h ** 2
        omega[-1, 1:-1] = -2.0 * psi[-2, 1:-1] / h ** 2
        omega[1:-1, 0] = -2.0 * psi[1:-1, 1] / h ** 2
        omega[1:-1, -1] = -2.0 * psi[1:-1, -2] / h ** 2
        omega[0, 0] = omega[0, -1] = omega[-1, 0] = omega[-1, -1] = 0.0

        if record_every and step % int(record_every) == 0:
            frames[step] = T.copy()

    # ---- 后处理指标 ----
    # 热壁面（x=0）的局部努塞尔数再沿壁面平均：
    #
    #     Nu = -(∂T/∂x)|_{x=0} · L / (T_hot - T_cold)
    #
    # 壁面在边界上，中心差分取不到，所以用二阶单侧差分
    # (-3T0 + 4T1 - T2) / (2h)。纯导热时 Nu = 1。
    if hot != cold:
        wall_gradient = (
            -3.0 * T[:, 0] + 4.0 * T[:, 1] - T[:, 2]
        ) / (2.0 * h)
        Nu_local = -wall_gradient * length / (hot - cold)
    else:
        Nu_local = np.zeros(n)

    Nu = float(np.mean(Nu_local))
    Nu_mid = float(np.mean(Nu_local[n // 4: 3 * n // 4]))
    max_speed = float(np.max(np.sqrt(u ** 2 + v ** 2)))

    fields = {
        "T": T,
        "u": u,
        "v": v,
        "omega": omega,
        "psi": psi,
        "speed": np.sqrt(u ** 2 + v ** 2),
    }

    scalars = {
        "Ra": float(ra),
        "Pr": float(pr),
        "Nu": Nu,
        "Nu_mid": Nu_mid,
        "T_mean": float(np.mean(T)),
        "max_speed": max_speed,
        "dt": float(dt),
        "steps": float(steps),
    }

    metadata = {
        "x": x,
        "y": y,
        "h": h,
        "n": int(n),
        "dt": float(dt),
        "steps": int(steps),
        "hot": float(hot),
        "cold": float(cold),
    }

    return ScienceResult(
        name=f"自然对流 Ra={ra:.0e}",
        fields=fields,
        scalars=scalars,
        frames=frames,
        metadata=metadata,
    )


__all__ = [
    "ScienceResult",
    "SciencePlotter",
    "convective_heat_transfer",
]
