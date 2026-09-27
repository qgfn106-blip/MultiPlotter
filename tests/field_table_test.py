# -*- coding: utf-8 -*-
"""矢量场（quiver / streamplot / quiver3d / stream3d）与表格（table）的测试。

用法：

    python field_table_test.py

全部通过时退出码为 0。
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# 本脚本位于 tests/，把包根目录加入 sys.path，才能导入 Multiplotter
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from Multiplotter import AnimationPlotter, MultiPlotter  # noqa: E402
from _test_paths import output_dir  # noqa: E402

OUT = output_dir("field-table")

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

passed = 0
failed = 0


def check(name, condition, extra=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"[PASS] {name} {extra}")
    else:
        failed += 1
        print(f"[FAIL] {name} {extra}")


def expect_error(name, exc_type, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exc_type as exc:
        check(name, True, f"-> {type(exc).__name__}")
    except Exception as exc:
        check(name, False, f"-> 抛出了 {type(exc).__name__}: {exc}")
    else:
        check(name, False, "-> 没有报错")


# ======================================================================
# 共用数据
# ======================================================================

# 二维涡旋场 + 均匀流（经典圆柱绕流风格）
NX, NY = 60, 50
AX = np.linspace(-2, 2, NX)
AY = np.linspace(-2, 2, NY)
MESH_X, MESH_Y = np.meshgrid(AX, AY)

RADIUS_SQ = MESH_X ** 2 + MESH_Y ** 2 + 0.35
FIELD_U = 1.0 - MESH_Y ** 2 / RADIUS_SQ
FIELD_V = MESH_X * MESH_Y / RADIUS_SQ

# 三维涡旋场
# u、v、w 支持两种网格约定（第三个下标都是 z）：
#   np.meshgrid(x, y, z, indexing="ij") -> (len(x), len(y), len(z))
#   np.meshgrid(x, y, z, indexing="xy") -> (len(y), len(x), len(z))
NZ = 24
AZ = np.linspace(-1.5, 1.5, NZ)
MESH_3D_X, MESH_3D_Y, MESH_3D_Z = np.meshgrid(AX, AY, AZ, indexing="ij")
FIELD_3D_U = -MESH_3D_Y
FIELD_3D_V = MESH_3D_X
FIELD_3D_W = 0.4 * np.ones_like(MESH_3D_Z)


def vortex_3d(x, y, z):
    """三维涡旋 + 沿 z 的均匀流，作为流线积分的解析场。"""
    return (-y, x, 0.4)


# ======================================================================
# 1. add_quiver
# ======================================================================

def test_quiver_basic():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(5, 4), dpi=60)
    plotter.add_quiver(
        MESH_X, MESH_Y, FIELD_U, FIELD_V, subplot=0,
        title="二维速度场", xlabel="x", ylabel="y",
        scale=18, cmap="turbo", colorbar=True,
        colorbar_kwargs={"label": "|V|"},
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
    )
    fig, axes = plotter.draw(show=False)
    check("add_quiver 二维网格可绘制", len(fig.axes) == 2,
          f"fig.axes={len(fig.axes)}（含颜色条）")
    plt.close("all")


def test_quiver_1d_axes():
    """x、y 传一维坐标时自动 meshgrid。"""
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=60)
    plotter.add_quiver(AX, AY, FIELD_U, FIELD_V, subplot=0)
    plotter.draw(show=False)
    check("add_quiver 支持一维坐标", True)
    plt.close("all")


def test_quiver_fixed_color():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=60)
    plotter.add_quiver(MESH_X, MESH_Y, FIELD_U, FIELD_V, subplot=0,
                       color="#1976D2", color_by_magnitude=False)
    plotter.draw(show=False)
    check("add_quiver 固定颜色可用", True)
    plt.close("all")


def test_quiver_errors():
    expect_error(
        "quiver: color 与 color_by_magnitude 冲突时报错",
        ValueError,
        MultiPlotter().add_quiver,
        MESH_X, MESH_Y, FIELD_U, FIELD_V, color="red",
    )
    expect_error(
        "quiver: u 为一维时报错",
        ValueError,
        MultiPlotter().add_quiver,
        MESH_X, MESH_Y, FIELD_U[0], FIELD_V,
    )
    expect_error(
        "quiver: u、v 形状不一致时报错",
        ValueError,
        MultiPlotter().add_quiver,
        MESH_X, MESH_Y, FIELD_U, FIELD_V[:, :-1],
    )
    expect_error(
        "quiver: 一维坐标与 u 形状不匹配时报错",
        ValueError,
        MultiPlotter().add_quiver,
        AX, AY, FIELD_U[:, :-1], FIELD_V[:, :-1],
    )


# ======================================================================
# 2. add_streamplot
# ======================================================================

def test_streamplot():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(5, 4), dpi=60)
    plotter.add_streamplot(
        MESH_X, MESH_Y, FIELD_U, FIELD_V, subplot=0,
        title="流线", xlabel="x", ylabel="y",
        density=1.4, line_width=1.4, cmap="turbo", arrowsize=1.2,
        colorbar=True,
        colorbar_kwargs={"label": "|V|"},
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
    )
    fig, axes = plotter.draw(show=False)
    check("add_streamplot 可绘制", len(fig.axes) == 2)
    plt.close("all")


def test_streamplot_fixed_color():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=60)
    plotter.add_streamplot(MESH_X, MESH_Y, FIELD_U, FIELD_V, subplot=0,
                           color="#388E3C", color_by_magnitude=False,
                           density=(1, 1.5))
    plotter.draw(show=False)
    check("add_streamplot 固定颜色 + density 元组可用", True)
    plt.close("all")


def test_streamplot_errors():
    expect_error(
        "streamplot: 退化成一条线时报错",
        ValueError,
        MultiPlotter().add_streamplot,
        MESH_X[:1], MESH_Y[:1], FIELD_U[:1], FIELD_V[:1],
    )
    expect_error(
        "streamplot: color 冲突时报错",
        ValueError,
        MultiPlotter().add_streamplot,
        MESH_X, MESH_Y, FIELD_U, FIELD_V, color="red",
    )


# ======================================================================
# 3. add_quiver3d
# ======================================================================

def test_quiver3d():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(5, 5), dpi=60)
    plotter.add_quiver3d(
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        subplot=0, title="三维矢量场", xlabel="x", ylabel="y", zlabel="z",
        density=10, length=0.5, cmap="turbo", colorbar=True,
        colorbar_kwargs={"label": "|V|"},
        view={"xlim": (-2, 2), "ylim": (-2, 2), "zlim": (-1.5, 1.5),
              "elev": 24, "azim": -60},
    )
    fig, axes = plotter.draw(show=False)
    check("add_quiver3d 可绘制", len(fig.axes) == 2)
    plt.close("all")


def test_quiver3d_1d_axes():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=60)
    plotter.add_quiver3d(
        AX, AY, AZ, FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        subplot=0, density=8,
        view={"xlim": (-2, 2), "ylim": (-2, 2), "zlim": (-1.5, 1.5)},
    )
    plotter.draw(show=False)
    check("add_quiver3d 支持一维坐标", True)
    plt.close("all")


def test_quiver3d_1d_mismatch():
    """一维坐标时 u 的第三个下标必须是 z。"""
    # 把 z 轴换到第一个下标：既不是 ij 也不是 xy 约定，应报错
    expect_error(
        "quiver3d: 一维坐标下 z 轴位置不对时报错",
        ValueError,
        MultiPlotter().add_quiver3d,
        AX, AY, AZ,
        FIELD_3D_U.T, FIELD_3D_V.T, FIELD_3D_W.T,
    )


def test_quiver3d_errors():
    expect_error(
        "quiver3d: 维度不对时报错",
        ValueError,
        MultiPlotter().add_quiver3d,
        MESH_X, MESH_Y, MESH_X, FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
    )
    expect_error(
        "quiver3d: u、v、w 形状不一致时报错",
        ValueError,
        MultiPlotter().add_quiver3d,
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W[:, :, :-1],
    )
    expect_error(
        "quiver3d: density 非正时报错",
        ValueError,
        MultiPlotter().add_quiver3d,
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W, density=0,
    )


# ======================================================================
# 4. add_stream3d
# ======================================================================

def test_stream3d():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(5, 5), dpi=60)
    plotter.add_stream3d(
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        subplot=0, title="三维流线",
        xlabel="x", ylabel="y", zlabel="z",
        field_func=vortex_3d,
        n_seeds=8, step_size=0.05, max_steps=400,
        line_width=2.0, cmap="turbo", color_by_speed=True,
        colorbar=True,
        colorbar_kwargs={"label": "|V|"},
        view={"xlim": (-2, 2), "ylim": (-2, 2), "zlim": (-1.5, 1.5),
              "elev": 24, "azim": -60},
    )
    fig, axes = plotter.draw(show=False)
    check("add_stream3d 可绘制", len(fig.axes) == 2)
    plt.close("all")


def test_stream3d_fixed_color_seeds():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=60)
    plotter.add_stream3d(
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        subplot=0, field_func=vortex_3d,
        seeds=[(1.0, 0.0, -1.0), (0.0, 1.0, 1.0)],
        color="#7B1FA2", color_by_speed=False, line_width=2.5,
        both_directions=False,
        view={"xlim": (-2, 2), "ylim": (-2, 2), "zlim": (-1.5, 1.5)},
    )
    plotter.draw(show=False)
    check("add_stream3d 指定 seeds + 固定颜色可用", True)
    plt.close("all")


def test_stream3d_errors():
    expect_error(
        "stream3d: 缺少 field_func 时报错",
        ValueError,
        lambda: MultiPlotter().add_stream3d(
            MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
            FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        ).draw(show=False),
    )
    expect_error(
        "stream3d: step_size 非正时报错",
        ValueError,
        MultiPlotter().add_stream3d,
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        field_func=vortex_3d, step_size=0,
    )
    expect_error(
        "stream3d: seeds 形状不对时报错",
        ValueError,
        lambda: MultiPlotter().add_stream3d(
            MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
            FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
            field_func=vortex_3d, seeds=[(1.0, 0.0)],
        ).draw(show=False),
    )
    expect_error(
        "stream3d: 驻点场积不出流线时报错",
        ValueError,
        lambda: MultiPlotter().add_stream3d(
            MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
            FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
            field_func=lambda x, y, z: (0.0, 0.0, 0.0),
            seeds=[(1.0, 0.0, 0.0)],
        ).draw(show=False),
    )


# ======================================================================
# 5. add_table
# ======================================================================

TABLE_DATA = [
    ["准确率", "0.812", "0.873", "+0.061"],
    ["召回率", "0.774", "0.845", "+0.071"],
    ["F1", "0.792", "0.858", "+0.066"],
    ["推理耗时(ms)", "48.2", "41.5", "-6.7"],
]


def test_table_basic():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(6, 3), dpi=60)
    plotter.add_table(
        TABLE_DATA, subplot=0, title="模型对比",
        col_labels=["指标", "基线", "改进", "提升"],
        loc="center",
    )
    fig, axes = plotter.draw(show=False)
    check("add_table 基础表格可绘制", len(fig.axes) == 1)
    plt.close("all")


def test_table_full_style():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(6, 3), dpi=60)
    plotter.add_table(
        TABLE_DATA, subplot=0, title="精细化样式",
        col_labels=["指标", "基线", "改进", "提升"],
        col_width=[1.6, 1.0, 1.0, 1.0],
        cell_align="center",
        cell_fontsize=10,
        cell_height=0.1,
        background_color="#FFFFFF",
        text_color="#263238",
        edge_color="#B0BEC5",
        edge_width=0.9,
        header_background="#1976D2",
        header_text_color="#FFFFFF",
        row_label_background="#ECEFF1",
        zebra_color="#F5F5F5",
        highlight=[(0, 3), (1, 3), (2, 3)],
        highlight_color="#C8E6C9",
        highlight_text_color="#1B5E20",
        highlight_bold=True,
    )
    fig, axes = plotter.draw(show=False)
    check("add_table 全样式可用", len(fig.axes) == 1)
    plt.close("all")


def test_table_condition_highlight():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(6, 3), dpi=60)
    plotter.add_table(
        TABLE_DATA, subplot=0, title="条件高亮",
        col_labels=["指标", "基线", "改进", "提升"],
        row_labels=["A", "B", "C", "D"],
        highlight={"<": 0.80},
        highlight_color="#FFCDD2",
    )
    plotter.draw(show=False)
    check("add_table 条件高亮可用", True)
    plt.close("all")


def test_table_bbox_and_axis():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(6, 3), dpi=60)
    plotter.add_table(
        TABLE_DATA, subplot=0,
        col_labels=["指标", "基线", "改进", "提升"],
        bbox=[0.02, 0.05, 0.96, 0.9],
        axis_off=False,
        zebra_color={"rows": [0, 2], "color": "#FFF3E0"},
    )
    plotter.draw(show=False)
    check("add_table bbox + 指定斑马纹行可用", True)
    plt.close("all")


def test_table_1d_and_column_colors():
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    plotter.add_table(
        ["0.91", "0.85", "0.88"], subplot=0,
        col_labels=["得分"],
        row_labels=["甲", "乙", "丙"],
        background_color=["#E3F2FD", "#FFFDE7", "#E8F5E9"],
        text_color=["#0D47A1", "#F57F17", "#1B5E20"],
    )
    plotter.draw(show=False)
    check("add_table 一维数据 + 按行配色可用", True)
    plt.close("all")


def test_table_errors():
    expect_error(
        "table: col_labels 长度不对时报错",
        ValueError,
        MultiPlotter().add_table,
        TABLE_DATA, col_labels=["a", "b"],
    )
    expect_error(
        "table: row_labels 长度不对时报错",
        ValueError,
        MultiPlotter().add_table,
        TABLE_DATA, row_labels=["a", "b"],
    )
    expect_error(
        "table: col_width 长度不对时报错",
        ValueError,
        MultiPlotter().add_table,
        TABLE_DATA, col_width=[1, 2],
    )
    expect_error(
        "table: background_color 形状不对时报错",
        ValueError,
        MultiPlotter().add_table,
        TABLE_DATA, background_color=["#000", "#111"],
    )
    expect_error(
        "table: 高亮单元格越界时报错",
        ValueError,
        MultiPlotter().add_table,
        TABLE_DATA, highlight=[(9, 9)],
    )
    expect_error(
        "table: 非法比较运算符时报错",
        ValueError,
        MultiPlotter().add_table,
        TABLE_DATA, highlight={"~=": 1},
    )
    expect_error(
        "table: cell_text 为空时报错",
        ValueError,
        MultiPlotter().add_table,
        [],
    )
    expect_error(
        "table: bbox 长度不对时报错",
        ValueError,
        MultiPlotter().add_table,
        TABLE_DATA, bbox=[0.1, 0.2],
    )


# ======================================================================
# 6. add_layer 统一入口
# ======================================================================

def test_add_layer_new_kinds():
    plotter = MultiPlotter(ncols=2, figsize_per_plot=(5, 4), dpi=60)
    plotter.add_layer(kind="quiver", x=MESH_X, y=MESH_Y,
                      u=FIELD_U, v=FIELD_V, subplot=0,
                      view={"xlim": (-2, 2), "ylim": (-2, 2)})
    plotter.add_layer(kind="streamplot", x=MESH_X, y=MESH_Y,
                      u=FIELD_U, v=FIELD_V, subplot=1,
                      view={"xlim": (-2, 2), "ylim": (-2, 2)})
    plotter.add_layer(kind="table", cell_text=TABLE_DATA, subplot=2,
                      col_labels=["指标", "基线", "改进", "提升"])
    plotter.add_layer(kind="quiver3d", x=MESH_3D_X, y=MESH_3D_Y, z=MESH_3D_Z,
                      u=FIELD_3D_U, v=FIELD_3D_V, w=FIELD_3D_W, subplot=3,
                      density=6,
                      view={"xlim": (-2, 2), "ylim": (-2, 2),
                            "zlim": (-1.5, 1.5)})
    plotter.add_layer(kind="stream3d", x=MESH_3D_X, y=MESH_3D_Y, z=MESH_3D_Z,
                      u=FIELD_3D_U, v=FIELD_3D_V, w=FIELD_3D_W, subplot=3,
                      field_func=vortex_3d, n_seeds=5,
                      view={"xlim": (-2, 2), "ylim": (-2, 2),
                            "zlim": (-1.5, 1.5)})
    plotter.draw(show=False)
    check("add_layer 支持全部新 kind", True)
    plt.close("all")


# ======================================================================
# 7. 动画
# ======================================================================

def test_quiver_animation():
    """二维涡旋随时间旋转，用 set_UVC 原地更新。"""
    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(5, 4), dpi=60)
    plotter.add_quiver(
        MESH_X, MESH_Y, FIELD_U, FIELD_V, subplot=0,
        title="旋转矢量场", xlabel="x", ylabel="y",
        scale=18, cmap="turbo",
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
    )
    plotter.draw(show=False)

    ax = plotter.get_axes(0)
    quiver = ax.collections[0]

    def update(frame):
        angle = frame * np.pi / 10
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        qu = FIELD_U * cos_a - FIELD_V * sin_a
        qv = FIELD_U * sin_a + FIELD_V * cos_a
        quiver.set_UVC(qu, qv)
        return quiver,

    target = os.path.join(OUT, "quiver.gif")
    plotter.animate(
        frames=12, interval=100, blit=True, update_mode="artists",
        update_func=update, save_path=target, fps=8, dpi=60,
    )
    check("矢量场动画（set_UVC）可保存", os.path.isfile(target))
    plt.close("all")


def test_quiver3d_animation():
    """三维矢量场用 set_segments 原地更新（旋转）。"""
    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(5, 5), dpi=60)
    plotter.add_quiver3d(
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        subplot=0, title="旋转三维矢量场",
        density=8, length=0.5, cmap="turbo",
        view={"xlim": (-2, 2), "ylim": (-2, 2), "zlim": (-1.5, 1.5),
              "elev": 24, "azim": -60},
    )
    plotter.draw(show=False)

    ax = plotter.get_axes(0)
    ax.view_init(elev=24, azim=-60)

    def update(frame):
        ax.view_init(elev=24, azim=-60 + frame * 15)
        return ax,

    target = os.path.join(OUT, "quiver3d.gif")
    plotter.animate(
        frames=10, interval=100, blit=False, update_mode="artists",
        update_func=update, save_path=target, fps=8, dpi=60,
    )
    check("三维矢量场动画可保存", os.path.isfile(target))
    plt.close("all")


def test_streamplot_animation():
    """流线用 reset 模式逐帧重算（matplotlib 的 streamplot 不能原地更新）。"""
    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(5, 4), dpi=60)
    plotter.add_streamplot(
        MESH_X, MESH_Y, FIELD_U, FIELD_V, subplot=0,
        title="流线随时间旋转",
        density=1.2, line_width=1.2, cmap="turbo",
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
    )
    plotter.draw(show=False)

    def update(ax, frame):
        angle = frame * np.pi / 12
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        qu = FIELD_U * cos_a - FIELD_V * sin_a
        qv = FIELD_U * sin_a + FIELD_V * cos_a
        ax.streamplot(MESH_X, MESH_Y, qu, qv, density=1.2,
                      color=np.hypot(qu, qv), cmap="turbo", linewidth=1.2)
        ax.set_title(f"流线旋转 step={frame + 1}")
        return ax,

    target = os.path.join(OUT, "streamplot.gif")
    plotter.animate(
        frames=8, interval=120, blit=False, update_mode="reset",
        update_func=update, save_path=target, fps=6, dpi=60,
    )
    check("流线动画（reset 模式）可保存", os.path.isfile(target))
    plt.close("all")


def animation_subplot_motion(path, ncols, nrows=1):
    """
    把动图按子图切块，返回每个子图的帧间总变化量。

    用来验证「每个参与动画的子图都在动」。
    """

    from PIL import Image, ImageSequence

    im = Image.open(path)
    frames = [np.asarray(f.convert("RGB"), dtype=float)
              for f in ImageSequence.Iterator(im)]
    height, width = frames[0].shape[:2]

    cell_w = width / ncols
    cell_h = height / nrows
    motion = []

    for row in range(nrows):
        for col in range(ncols):
            y0, y1 = int(row * cell_h), int((row + 1) * cell_h)
            x0, x1 = int(col * cell_w), int((col + 1) * cell_w)

            total = 0.0
            for i in range(len(frames) - 1):
                total += float(
                    np.abs(frames[i][y0:y1, x0:x1]
                           - frames[i + 1][y0:y1, x0:x1]).mean()
                )
            motion.append(total)

    return motion


def test_multi_subplot_animation_all_move():
    """多子图动画：每个参与动画的子图都必须逐帧变化。

    这是针对一个真实 bug 的回归测试：
    框架曾经只对 subplots[0] 执行 clear + 回调重画，
    导致其它子图一直停在 draw() 时的第一帧（看起来"不动"）。
    """

    # 用双涡对：涡核位置随 phase 改变，流线形态会真的变化
    def vortex_pair(x, y, phase, orbit_radius=1.0, core=0.3, strength=1.0):
        u = np.zeros_like(x, dtype=float)
        v = np.zeros_like(y, dtype=float)

        for sign in (1.0, -1.0):
            cx = sign * orbit_radius * np.cos(phase)
            cy = sign * orbit_radius * np.sin(phase)
            dx, dy = x - cx, y - cy
            radius_sq = dx ** 2 + dy ** 2 + 1e-9
            factor = (1.0 - np.exp(-radius_sq / core ** 2)) / radius_sq
            u += -sign * strength * dy * factor
            v += sign * strength * dx * factor

        return u, v

    start_u, start_v = vortex_pair(MESH_X, MESH_Y, 0.0)

    plotter = AnimationPlotter(ncols=2, figsize_per_plot=(5, 4), dpi=60)
    plotter.add_quiver(
        MESH_X, MESH_Y, start_u, start_v, subplot=0,
        scale=6, cmap="turbo", width=0.006,
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
    )
    plotter.add_streamplot(
        MESH_X, MESH_Y, start_u, start_v, subplot=1,
        density=1.2, line_width=1.2, cmap="turbo",
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
    )
    plotter.draw(show=False)

    quiver_ax = plotter.get_axes(0)

    def update(ax, frame):
        phase = np.deg2rad(frame * 30.0)
        qu, qv = vortex_pair(MESH_X, MESH_Y, phase)
        speed = np.hypot(qu, qv)

        if ax is quiver_ax:
            ax.quiver(MESH_X, MESH_Y, qu, qv, speed,
                      cmap="turbo", scale=6, width=0.006)
            ax.set_title(f"箭头 phase={frame * 30}°")
        else:
            ax.streamplot(MESH_X, MESH_Y, qu, qv, density=1.2,
                          color=speed, cmap="turbo", linewidth=1.2)
            ax.set_title(f"流线 phase={frame * 30}°")

        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2)
        ax.set_aspect("equal")
        return ax,

    target = os.path.join(OUT, "multi_subplot_motion.gif")
    plotter.animate(
        subplots=[0, 1],
        frames=5, interval=120, blit=False, update_mode="reset",
        update_func=update, save_path=target, fps=5, dpi=60,
    )
    plt.close("all")

    check("多子图动画可保存", os.path.isfile(target))

    motion = animation_subplot_motion(target, ncols=2)
    check("左子图（箭头）在动", motion[0] > 5.0,
          f"-> 变化量={motion[0]:.2f}")
    check("右子图（流线）也在动", motion[1] > 5.0,
          f"-> 变化量={motion[1]:.2f}")


def test_subplots_param_recorded():
    """动画参数里要能看到参与了哪些子图。"""
    plotter = AnimationPlotter(ncols=2, figsize_per_plot=(4, 3), dpi=50)
    plotter.add_plot(kind="line", x=MESH_X[0], y=MESH_Y[0], subplot=0,
                     view={"xlim": (-2, 2), "ylim": (-2, 2)})
    plotter.add_plot(kind="line", x=MESH_X[0], y=MESH_Y[0], subplot=1,
                     view={"xlim": (-2, 2), "ylim": (-2, 2)})
    plotter.draw(show=False)

    plotter.animate(
        subplots=[0, 1], frames=2, update_mode="reset", blit=False,
        update_func=lambda ax, frame: ax.plot([0, 1], [0, 1]),
    )
    params = plotter.get_animation_params()
    check("get_animation_params 记录了 subplots",
          params.get("subplots") == [0, 1], f"-> {params.get('subplots')}")
    plt.close("all")


def test_table_animation():
    """表格用 set_text 逐帧更新单元格。"""
    frame_data = {
        frame: [
            ["准确率", f"{0.80 + 0.01 * frame:.3f}"],
            ["召回率", f"{0.75 + 0.02 * frame:.3f}"],
        ]
        for frame in range(6)
    }

    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    plotter.add_table(
        frame_data[0], subplot=0, title="指标变化",
        col_labels=["指标", "数值"],
        axis_off=True,
        # 表格也需要固定坐标轴范围，否则动画每帧会重新缩放
        view={"xlim": (0.0, 1.0), "ylim": (0.0, 1.0)},
    )
    plotter.draw(show=False)

    ax = plotter.get_axes(0)
    table = ax._multiplotter_table_cache[0]

    def update(ax, text):
        table.get_celld()[(0, 1)].get_text().set_text(str(text[0][1]))
        table.get_celld()[(1, 1)].get_text().set_text(str(text[1][1]))
        return table,

    target = os.path.join(OUT, "table.gif")
    plotter.animate(
        frame_data=frame_data, interval=300, blit=False,
        update_mode="append",
        update_func=update, save_path=target, fps=3, dpi=60,
    )
    check("表格动画可保存", os.path.isfile(target))
    plt.close("all")


def test_table_animation_via_api():
    """用类自带的 _update_table 更新表格文本。"""
    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    plotter.add_table(
        TABLE_DATA, subplot=0, title="API 更新",
        col_labels=["指标", "基线", "改进", "提升"],
    )
    plotter.draw(show=False)
    ax = plotter.get_axes(0)
    config = plotter.plot_configs[0]

    config["frame_text"] = np.asarray(TABLE_DATA, dtype=object).copy()
    config["frame_text"][0, 1] = "0.900"
    plotter._update_table(ax, config)

    table = ax._multiplotter_table_cache[0]
    value = table.get_celld()[(0, 1)].get_text().get_text()
    check("_update_table 能就地更新单元格", value == "0.900", f"-> {value}")
    plt.close("all")


# ======================================================================
# 运行
# ======================================================================

def main():
    tests = [
        ("quiver 基础", test_quiver_basic),
        ("quiver 一维坐标", test_quiver_1d_axes),
        ("quiver 固定颜色", test_quiver_fixed_color),
        ("quiver 参数校验", test_quiver_errors),
        ("streamplot 基础", test_streamplot),
        ("streamplot 固定颜色", test_streamplot_fixed_color),
        ("streamplot 参数校验", test_streamplot_errors),
        ("quiver3d 基础", test_quiver3d),
        ("quiver3d 一维坐标", test_quiver3d_1d_axes),
        ("quiver3d 形状错位", test_quiver3d_1d_mismatch),
        ("quiver3d 参数校验", test_quiver3d_errors),
        ("stream3d 基础", test_stream3d),
        ("stream3d 指定起点", test_stream3d_fixed_color_seeds),
        ("stream3d 参数校验", test_stream3d_errors),
        ("table 基础", test_table_basic),
        ("table 全样式", test_table_full_style),
        ("table 条件高亮", test_table_condition_highlight),
        ("table bbox/斑马纹行", test_table_bbox_and_axis),
        ("table 一维数据", test_table_1d_and_column_colors),
        ("table 参数校验", test_table_errors),
        ("add_layer 新 kind", test_add_layer_new_kinds),
        ("动画 quiver", test_quiver_animation),
        ("动画 quiver3d", test_quiver3d_animation),
        ("动画 streamplot", test_streamplot_animation),
        ("动画 多子图都要动", test_multi_subplot_animation_all_move),
        ("动画 subplots 记录", test_subplots_param_recorded),
        ("动画 table", test_table_animation),
        ("table set_text API", test_table_animation_via_api),
    ]

    for name, func in tests:
        try:
            func()
        except Exception as exc:
            check(name, False, f"-> 异常 {type(exc).__name__}: {exc}")

    print()
    print(f"通过 {passed} 项，失败 {failed} 项")

    shutil.rmtree(OUT, ignore_errors=True)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
