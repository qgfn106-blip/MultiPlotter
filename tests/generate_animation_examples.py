# -*- coding: utf-8 -*-
"""生成 README 中 AnimationPlotter 章节引用的动图与预览图。

用法（在本文件夹下运行）：

    python generate_animation_examples.py

生成：

    images/26_animation_sine.gif        简单示例：正弦波平移
    images/27_animation_sine_preview.png 简单示例的末帧预览
    images/28_animation_fourier.gif      复杂示例：正弦波 -> 方波
    images/29_animation_fourier_preview.png 复杂示例的末帧预览

只依赖 numpy、matplotlib 和 Pillow。
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)                                  # 包根目录（tests 的上一层）
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(TESTS_DIR, "images")
sys.path.insert(0, BASE_DIR)

from Multiplotter import AnimationPlotter  # noqa: E402

os.makedirs(IMAGES_DIR, exist_ok=True)


def out(name):
    return os.path.join(IMAGES_DIR, name)


def save_animation(plotter, filename, **kwargs):
    """
    保存动图。

    这里传 save_path 而不是 save=True：save=True 走的是
    MultiPlotter 的“同名自动加序号”逻辑，重复运行会生成
    animation_sine_1.gif 之类的文件。为了保证 README 引用的文件名固定，
    先删掉旧文件再保存。
    """
    target = out(filename)

    if os.path.exists(target):
        os.remove(target)

    plotter.animate(save_path=target, **kwargs)
    return target


def reset_style():
    plt.style.use("default")
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "SimHei",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


# ======================================================================
# 1. 简单示例：正弦波平移
# ======================================================================

def example_sine():
    reset_style()

    x = np.linspace(0, 2 * np.pi, 240)

    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(6.4, 3.6), dpi=100)
    plotter.add_plot(
        kind="line", x=x, y=np.sin(x), subplot=0,
        title="正弦波平移：line + scatter",
        xlabel="x", ylabel="y",
        # 动画必须固定坐标轴范围，否则每帧会自动缩放
        view={"xlim": (0, 2 * np.pi), "ylim": (-1.6, 1.6), "grid": True},
    )
    plotter.draw(show=False)

    ax = plotter.get_axes(0)
    line = ax.lines[0]
    point = ax.plot([], [], "o", ms=9, color="#E64A19", zorder=5)[0]

    def update(frame):
        """帧数据 = 相位；只改已有对象的数据，不重建。"""
        phase = frame / 20 * np.pi
        line.set_data(x, np.sin(x - phase))
        point.set_data([x[-1]], [float(np.sin(x[-1] - phase))])
        return line, point

    save_animation(
        plotter,
        "26_animation_sine.gif",
        frames=48,
        interval=40,
        blit=True,
        update_mode="artists",
        update_func=update,
        fps=20,
        dpi=75,
    )
    # 保存末帧作为静态预览图
    plotter.get_animation()._func(47)
    plotter._fig.savefig(out("27_animation_sine_preview.png"), dpi=110,
                         bbox_inches="tight")
    plt.close("all")


# ======================================================================
# 2. 复杂示例：正弦波 -> 方波（傅里叶级数逐项叠加）
# ======================================================================

def square_wave_partial(x, harmonics):
    """
    方波的傅里叶部分和：

        f(x) = (4/pi) * sum_{k=1,3,5,...} sin(k x) / k

    叠加的项越多，越接近方波（吉布斯现象会一直存在，所以不会完全拟合）。
    """
    total = np.zeros_like(x)

    for k in range(1, harmonics + 1, 2):
        total += np.sin(k * x) / k

    return (4.0 / np.pi) * total


def example_fourier_square_wave():
    reset_style()

    x = np.linspace(0, 2 * np.pi, 260)
    target = np.sign(np.sin(x))          # 理想方波，仅用于对比

    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(7.2, 4.0), dpi=100)
    plotter.add_plot(
        kind="line", x=x, y=square_wave_partial(x, 1), subplot=0,
        title="正弦波 -> 方波：傅里叶级数逐项叠加",
        xlabel="x", ylabel="y",
        view={"xlim": (0, 2 * np.pi), "ylim": (-1.6, 1.6), "grid": True},
    )
    plotter.add_plot(
        kind="line", x=x, y=target, subplot=0,
        color="#B0BEC5", linewidth=1.4, linestyle="--",
        label="理想方波", legend=True,
        legend_kwargs={"loc": "lower right"},
    )
    plotter.draw(show=False)

    ax = plotter.get_axes(0)
    partial_line = ax.lines[0]
    ax.lines[1].set_label("理想方波")

    # 已经画好的两条线在每帧里原地更新，所以用 artists 模式 + blit
    def update(frame):
        harmonics = 2 * frame + 1          # 1, 3, 5, ... 逐项增加
        partial_line.set_data(x, square_wave_partial(x, harmonics))
        ax.set_title(
            f"正弦波 -> 方波：已叠加 {harmonics} 项"
            f"（1, 3, 5, … 奇次谐波）"
        )
        return partial_line, ax.title

    save_animation(
        plotter,
        "28_animation_fourier.gif",
        frames=20,
        interval=120,
        blit=True,
        update_mode="artists",
        update_func=update,
        fps=5,
        dpi=75,
    )

    # 末帧（39 项谐波）的静态预览
    plotter.get_animation()._func(19)
    plotter._fig.savefig(out("29_animation_fourier_preview.png"), dpi=110,
                         bbox_inches="tight")
    plt.close("all")


def main():
    example_sine()
    print("[ok] 26_animation_sine.gif / 27_animation_sine_preview.png")

    example_fourier_square_wave()
    print("[ok] 28_animation_fourier.gif / 29_animation_fourier_preview.png")

    for name in (
        "26_animation_sine.gif",
        "27_animation_sine_preview.png",
        "28_animation_fourier.gif",
        "29_animation_fourier_preview.png",
    ):
        path = out(name)
        size = os.path.getsize(path)
        print(f"    {name}: {size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
