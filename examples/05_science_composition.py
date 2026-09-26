# -*- coding: utf-8 -*-
"""示例 5：科研组合接口（ScienceResult + SciencePlotter）。

对应文档：
    API.md 附录 A「科研组合接口（实验性 API）」
    README.md 第 5 章「科研算例：对流传热」

演示「自己的算法 + 本包的绘图」如何对接：
只要把结果打包成 ScienceResult，就能直接用 SciencePlotter 出图。

运行：
    python examples/05_science_composition.py
"""

import numpy as np
import matplotlib.pyplot as plt

from _common import output, prepare

prepare()

from multiplotter import (  # noqa: E402
    MultiPlotter,
    SciencePlotter,
    ScienceResult,
    convective_heat_transfer,
)


def own_solver(n=80, steps=250):
    """一个**自己的**求解器：二维热传导（显式差分）。

    重点是它只负责算，返回一个 ``ScienceResult``，
    完全不需要知道 MultiPlotter 的存在。
    """

    x = np.linspace(0.0, 1.0, n)
    y = np.linspace(0.0, 1.0, n)
    h = x[1] - x[0]

    # 初始条件：中心一个高斯热源
    X, Y = np.meshgrid(x, y, indexing="ij")
    T = np.exp(-((X - 0.5) ** 2 + (Y - 0.5) ** 2) / (2 * 0.08 ** 2))

    dt = 0.2 * h ** 2
    frames = {}

    for step in range(steps):
        T[1:-1, 1:-1] += dt * (
            (T[2:, 1:-1] - 2 * T[1:-1, 1:-1] + T[:-2, 1:-1]) / h ** 2
            + (T[1:-1, 2:] - 2 * T[1:-1, 1:-1] + T[1:-1, :-2]) / h ** 2
        )
        # 四壁固定为 0（Dirichlet）
        T[0, :] = T[-1, :] = T[:, 0] = T[:, -1] = 0.0

        if step % 25 == 0:
            frames[step] = T.copy()

    # 一些标量指标
    scalars = {
        "T_max": float(T.max()),
        "T_sum": float(T.sum() * h * h),
        "steps": float(steps),
        "grid": float(n),
    }

    return ScienceResult(
        name="二维热传导",
        fields={"T": T, "grad_x": np.gradient(T, h, axis=0)},
        scalars=scalars,
        frames=frames,
        metadata={"x": x, "y": y, "h": h, "dt": dt},
    )


def compose_own_result(result):
    """用 SciencePlotter 画自己的结果。"""

    painter = SciencePlotter(result, ncols=2, dpi=100)

    painter.plot_field("T", subplot=0, kind="contour", cmap="inferno",
                       colorbar=True, title="温度场（等高线）")
    painter.plot_field("T", subplot=1, kind="heatmap", cmap="magma",
                       title="温度场（热力图）")
    painter.plot_profile("T", subplot=2, axis="x", index=None,
                         title="中轴线剖面")
    painter.plot_series(subplot=3, title="标量指标")
    painter.plot_table(subplot=4, title="指标表")

    painter.draw(show=False, save_path=output("40_science_own_result.png"))

    print("[ok] 40_science_own_result.png")
    print("  ", result.summary())


def compose_convection():
    """同一个接口也能直接消费内置算例。"""

    result = convective_heat_transfer(ra=1e3, pr=0.71, n=48, steps=300)

    painter = SciencePlotter(result, ncols=2, dpi=100)
    painter.plot_field("T", subplot=0, cmap="inferno", colorbar=True,
                       title="温度场（Ra=1e3）")
    painter.plot_field("psi", subplot=1, kind="heatmap", cmap="RdBu_r",
                       title="流函数 ψ")
    painter.plot_table(subplot=2, title="对流传热指标")

    painter.draw(show=False, save_path=output("41_science_convection.png"))

    print("[ok] 41_science_convection.png")
    print("  ", result.summary())


def mix_with_raw_layers(result):
    """SciencePlotter 也能和普通 add_* 混用。"""

    x = result.metadata["x"]
    y = result.metadata["y"]

    # SciencePlotter 通过 __getattr__ 转发到内部的 MultiPlotter
    painter = SciencePlotter(result, ncols=2, dpi=100)

    painter.plot_field("T", subplot=0, kind="contour", cmap="inferno",
                       colorbar=True, title="来自 SciencePlotter")

    painter.add_contour(x, y, result.field("grad_x"), subplot=1,
                        cmap="coolwarm", levels=18, colorbar=True,
                        title="来自 add_contour()")

    painter.draw(show=False, save_path=output("42_science_mixed.png"))

    print("[ok] 42_science_mixed.png")


def plain_multiplotter(result):
    """完全不使用 science 模块，直接用 MultiPlotter —— 效果等价。"""

    x = result.metadata["x"]
    y = result.metadata["y"]

    plotter = MultiPlotter(ncols=1, figsize_per_plot=(6, 5), dpi=100)
    plotter.add_contour(
        x, y, result.field("T"), subplot=0,
        title="纯 MultiPlotter 写法", cmap="inferno",
        levels=22, colorbar=True,
        view={"aspect": "equal", "grid": False},
    )

    plotter.draw(show=False, save_path=output("43_science_plain.png"))

    print("[ok] 43_science_plain.png")


def main():
    result = own_solver()

    print("== 自己的求解器 ==")
    print("  ", result)
    print("  ", result.summary())

    compose_own_result(result)
    compose_convection()
    mix_with_raw_layers(result)
    plain_multiplotter(result)

    plt.close("all")
    print("\n完成，输出在 examples/output/")


if __name__ == "__main__":
    main()
