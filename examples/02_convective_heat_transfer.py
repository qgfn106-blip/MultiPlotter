# -*- coding: utf-8 -*-
"""示例 2：对流传热算例（算法 + 组合绘图）。

对应文档：
    README.md 第 5 章「科研算例：对流传热」

演示的核心思想是 **算法与绘图分离**：

    convective_heat_transfer()  只算，返回 ScienceResult
    SciencePlotter / MultiPlotter  只画，消费 ScienceResult

本脚本用三种粒度画同一个结果：

    1. SciencePlotter 的语义化接口（plot_field / plot_profile / plot_table）
    2. 直接用 MultiPlotter 的 add_* 组合（与 1 完全等价）
    3. AnimationPlotter 播放温度场的逐帧演化

运行：
    python examples/02_convective_heat_transfer.py
"""

import numpy as np
import matplotlib.pyplot as plt

from _common import output, prepare

prepare()

from multiplotter import (  # noqa: E402
    AnimationPlotter,
    MultiPlotter,
    SciencePlotter,
    convective_heat_transfer,
)


def solve():
    """跑算例，返回结果。

    参数按 de Vahl Davis (1983) 的标准二维方腔基准挑：
    Ra=1e4、Pr=0.71 时基准 Nu ≈ 2.238，这里取 n=41、steps=1200
    （显式时间推进需要足够多步才能到稳态，步数不够会明显偏小）。
    """

    print("正在求解二维方腔自然对流 ...")

    result = convective_heat_transfer(
        ra=1e4,           # 瑞利数
        pr=0.71,          # 普朗特数（空气）
        n=41,             # 网格 41 x 41
        steps=1200,       # 时间步数（不足会停在未发展的流场上）
        record_every=40,  # 每 40 步记录一帧，供动画使用
    )

    print("  ", result.summary())
    print("   基准：de Vahl Davis (1983) Ra=1e4 时 Nu ≈ 2.238")
    print("   fields:", sorted(result.fields))
    print("   frames:", 0 if result.frames is None else len(result.frames))

    return result


def with_science_plotter(result):
    """方式 1：SciencePlotter 的语义化接口。"""

    painter = SciencePlotter(result, ncols=2, dpi=100)

    painter.plot_field("T", subplot=0, cmap="inferno", colorbar=True)
    painter.plot_field("speed", subplot=1, kind="heatmap", cmap="viridis")
    painter.plot_profile("T", subplot=2, axis="x",
                         title="温度沿 x 的剖面（中间一行）")
    painter.plot_table(subplot=3)

    painter.draw(show=False, save_path=output("10_convection_panels.png"))

    print("[ok] 10_convection_panels.png")


def with_raw_layers(result):
    """方式 2：直接用 MultiPlotter 组合各种 add_*（与方式 1 等价）。"""

    x = result.metadata["x"]
    y = result.metadata["y"]

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6, 5), dpi=100)

    # 温度场：填充等高线 + 颜色条
    plotter.add_contour(
        x, y, result.field("T"), subplot=0,
        title="温度场 T", cmap="inferno", levels=24, line_levels=12,
        colorbar=True, colorbar_kwargs={"label": "T"},
        view={"aspect": "equal", "grid": False},
    )
    # 流线：用速度场画流线，颜色表示速度大小
    plotter.add_streamplot(
        x, y, result.field("u"), result.field("v"), subplot=1,
        title="流线（颜色 = 速度大小）", cmap="turbo", density=1.3,
        colorbar=True, colorbar_kwargs={"label": "|V|"},
        view={"aspect": "equal", "grid": False},
    )

    # 速度大小：热力图
    plotter.add_plot(
        kind="heatmap", data=result.field("speed"), subplot=2,
        title="速度大小 |V|", cmap="viridis",
        show_heatmap_values=False, colorbar=True,
        view={"aspect": "equal", "grid": False},
    )

    # 指标表格
    rows = [[key, f"{float(value):.6g}"]
            for key, value in result.scalars.items()]
    plotter.add_table(
        rows, subplot=3, title="算例指标",
        col_labels=["指标", "数值"],
        highlight={"<": 1.0}, highlight_color="#FFE082",
        view={"xlim": (0.0, 1.0), "ylim": (0.0, 1.0)},
    )

    plotter.draw(show=False, save_path=output("11_convection_raw.png"))

    print("[ok] 11_convection_raw.png")


def animated(result):
    """方式 3：播放温度场的逐帧演化。"""

    if not result.frames:
        print("[skip] 没有帧数据（record_every=0）")
        return

    frames = result.frames
    x = result.metadata["x"]
    y = result.metadata["y"]

    # 固定颜色范围，否则每帧的色标会跳
    all_values = np.concatenate([np.asarray(f).ravel()
                                 for f in frames.values()])
    levels = np.linspace(float(all_values.min()),
                         float(all_values.max()), 25)

    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(6, 5.5), dpi=90)
    plotter.add_contour(
        x, y, frames[next(iter(frames))], subplot=0,
        title="温度场演化", cmap="inferno", levels=levels,
        line_levels=0, clabel=False, colorbar=True,
        view={
            "aspect": "equal",
            "grid": False,
            "xlim": (float(x[0]), float(x[-1])),
            "ylim": (float(y[0]), float(y[-1])),
        },
    )

    plotter.draw(show=False)

    def update(ax, frame):
        """reset 模式：框架先 clear，这里必须重画内容。

        这里**不给** ``frame_data``，所以第二个参数是帧号（时间步），
        可以拿来查数据、也方便写进标题。
        如果传了 ``frame_data``，第二个参数会变成那一帧的**数据**本身
        （见 ANIMATION.md 的「frame_data」一节）。
        """

        values = np.asarray(frames[frame], dtype=float)

        ax.clear()
        ax.contourf(x, y, values, levels=levels, cmap="inferno")
        ax.set_aspect("equal")
        ax.set_xlim(float(x[0]), float(x[-1]))
        ax.set_ylim(float(y[0]), float(y[-1]))
        ax.set_title(f"温度场演化  step={frame}")

        return (ax,)

    plotter.animate(
        frames=list(frames.keys()),
        update_func=update,
        update_mode="reset",
        interval=120,
        save_path=output("12_convection_animation.gif"),
        fps=8,
        dpi=80,
    )

    print("[ok] 12_convection_animation.gif")


def main():
    result = solve()

    with_science_plotter(result)
    with_raw_layers(result)
    animated(result)

    plt.close("all")
    print("\n完成，输出在 examples/output/")


if __name__ == "__main__":
    main()
