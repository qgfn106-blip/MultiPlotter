# -*- coding: utf-8 -*-
"""生成 README 中矢量场与表格章节引用的图片与动图。

用法（在本文件夹下运行）：

    python generate_field_examples.py

生成（编号由 renumber_images.py 按 README 出现顺序统一分配）：

    19_vector_2d_example.png        二维矢量场（速度场 + 流线）
    20_tensor_field_example.png     二维有限元张量场（涡旋的速度梯度张量）
    21_vector_3d_example.png        三维矢量场（箭头 + RK4 流线）
    24_table_example.png            表格（精细化样式 + 条件高亮）
    22_vector_2d_animated.gif       二维矢量场动画（流场旋转）
    23_vector_3d_animated.gif       三维矢量场动画（视点旋转）
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)                                  # 包根目录（tests 的上一层）
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(TESTS_DIR, "images")
sys.path.insert(0, BASE_DIR)

from Multiplotter import AnimationPlotter, MultiPlotter  # noqa: E402

os.makedirs(IMAGES_DIR, exist_ok=True)


def out(name):
    return os.path.join(IMAGES_DIR, name)


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


def save_current(name):
    plt.gcf().savefig(out(name), bbox_inches="tight")
    plt.close("all")


# ======================================================================
# 共用场函数
# ======================================================================

# ---- 二维：涡旋 + 剪切流的叠加，用来展示箭头与流线 ----
VORTEX_X = np.linspace(-2.0, 2.0, 41)
VORTEX_Y = np.linspace(-2.0, 2.0, 41)
VORTEX_MESH_X, VORTEX_MESH_Y = np.meshgrid(VORTEX_X, VORTEX_Y)


def vortex_2d(x, y, strength=1.0, core=0.35):
    """
    Lamb-Oseen（高斯涡）速度场。

        u = -strength * y * (1 - exp(-r^2 / core^2)) / r^2
        v =  strength * x * (1 - exp(-r^2 / core^2)) / r^2

    core 很小时中心接近刚体旋转、外围接近自由涡。
    """
    radius_sq = x ** 2 + y ** 2 + 1e-12
    factor = (1.0 - np.exp(-radius_sq / core ** 2)) / radius_sq

    return -strength * y * factor, strength * x * factor


def vortex_pair(x, y, phase, orbit_radius=1.0, core=0.30, strength=1.0):
    """
    一对反号高斯涡绕共同中心旋转（真实的时间相关流场）。

    注意：单个 Lamb-Oseen 涡是**旋转对称**的，把速度场绕原点旋转任意角度，
    得到的还是同一个场（|V| 的差异只有 1e-16 量级），
    所以「旋转涡场」的流线在数学上完全不变——动画里看起来就是静止的。

    双涡对则不同：两个涡核的位置随 phase 改变，
    流线形态会明显变化（水平 → 斜向 → 垂直），这才适合做流线动画。
    """
    u = np.zeros_like(x, dtype=float)
    v = np.zeros_like(y, dtype=float)

    for sign in (1.0, -1.0):
        # 两个涡核共用同一相位，位置始终关于原点对称
        cx = sign * orbit_radius * np.cos(phase)
        cy = sign * orbit_radius * np.sin(phase)

        dx = x - cx
        dy = y - cy
        radius_sq = dx ** 2 + dy ** 2 + 1e-9
        factor = (1.0 - np.exp(-radius_sq / core ** 2)) / radius_sq

        # 环量相反：一个逆时针、一个顺时针
        u += -sign * strength * dy * factor
        v += sign * strength * dx * factor

    return u, v


def vortex_velocity_gradient(x, y, strength=1.0, core=0.35):
    """
    计算涡旋速度场的梯度张量分量（解析解）。

    返回：

        du_dx, du_dy, dv_dx, dv_dy

    线性代数里就是雅可比矩阵 J = [[du/dx, du/dy], [dv/dx, dv/dy]]，
    有限元里常见的小变形张量取它的对称部分
    epsilon = (J + J^T) / 2，反对称部分对应涡量。
    """
    radius_sq = x ** 2 + y ** 2 + 1e-12
    radius = np.sqrt(radius_sq)

    exp_term = np.exp(-radius_sq / core ** 2)
    factor = (1.0 - exp_term) / radius_sq

    # d(factor)/d(r^2)
    d_factor_d_r2 = (
        exp_term / core ** 2
        - (1.0 - exp_term) / radius_sq
    ) / radius_sq

    # u = -s * y * factor, v = s * x * factor
    du_dx = -strength * y * 2.0 * x * d_factor_d_r2
    du_dy = -strength * (factor + y * 2.0 * y * d_factor_d_r2)

    dv_dx = strength * (factor + x * 2.0 * x * d_factor_d_r2)
    dv_dy = strength * x * 2.0 * y * d_factor_d_r2

    # 避免中心点除零产生的噪声
    near_center = radius < 1e-6

    if np.any(near_center):
        du_dy = np.where(near_center, -strength * factor, du_dy)
        dv_dx = np.where(near_center, strength * factor, dv_dx)

    return du_dx, du_dy, dv_dx, dv_dy


FLOW_U, FLOW_V = vortex_2d(VORTEX_MESH_X, VORTEX_MESH_Y)
DU_DX, DU_DY, DV_DX, DV_DY = vortex_velocity_gradient(
    VORTEX_MESH_X, VORTEX_MESH_Y,
)

# 小变形张量（对称部分）与旋转张量（反对称部分）
STRAIN_XX = DU_DX
STRAIN_XY = 0.5 * (DU_DY + DV_DX)
SPIN_XY = 0.5 * (DV_DX - DU_DY)

# ---- 三维：涡旋 + 上升流 ----
GRID_3D = np.linspace(-2.0, 2.0, 21)
GRID_3D_Z = np.linspace(-1.5, 1.5, 15)
MESH_3D_X, MESH_3D_Y, MESH_3D_Z = np.meshgrid(
    GRID_3D, GRID_3D, GRID_3D_Z, indexing="ij",
)
FIELD_3D_U, FIELD_3D_V = vortex_2d(
    MESH_3D_X, MESH_3D_Y, strength=1.2, core=0.6,
)
FIELD_3D_W = 0.45 * np.ones_like(MESH_3D_Z)


def field_3d(x, y, z):
    """三维涡旋场，供 add_stream3d 做 RK4 积分。"""
    u, v = vortex_2d(x, y, strength=1.2, core=0.6)
    return u, v, 0.45


# ---- 表格数据：某次模型压缩实验 ----
TABLE_ROW_LABELS = ["准确率", "召回率", "F1", "参数量(M)", "推理耗时(ms)"]

TABLE_DATA = [
    ["0.812", "0.873", "0.883", "+0.071"],
    ["0.774", "0.845", "0.856", "+0.082"],
    ["0.792", "0.858", "0.869", "+0.077"],
    ["25.6", "12.8", "8.4", "-67.2%"],
    ["48.2", "41.5", "33.7", "-30.1%"],
]


# ======================================================================
# 1. 二维矢量场：箭头 + 流线
# ======================================================================

def example_vector_2d():
    reset_style()

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(5.6, 4.6), dpi=72)

    # 左：箭头，按速度模长着色（颜色本身就表示速度大小）
    plotter.add_quiver(
        VORTEX_MESH_X, VORTEX_MESH_Y, FLOW_U, FLOW_V, subplot=0,
        title="二维涡旋速度场（箭头按模长着色）",
        xlabel="x", ylabel="y",
        scale=16, cmap="turbo",
        colorbar=True,
        colorbar_kwargs={"label": "|V|", "shrink": 0.85},
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
        width=0.004,
    )

    # 右：流线，按速度着色
    plotter.add_streamplot(
        VORTEX_MESH_X, VORTEX_MESH_Y, FLOW_U, FLOW_V, subplot=1,
        title="同一流场的流线（颜色表示速度）",
        xlabel="x", ylabel="y",
        density=1.6, line_width=1.3, cmap="turbo", arrowsize=1.1,
        colorbar=True,
        colorbar_kwargs={"label": "|V|", "shrink": 0.85},
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
    )

    plotter.draw(show=False)
    save_current("19_vector_2d_example.png")


# ======================================================================
# 2. 二维张量场：速度梯度张量的对称部分
# ======================================================================

def example_tensor_field():
    reset_style()

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(5.6, 4.6), dpi=72)

    # 左：正应变 εxx 的填充等值线 + 剪应变 εxy 的黑色等值线，
    #     两者都用物理坐标（meshgrid 的结果），叠加不会错位
    contour_levels = np.linspace(
        float(np.min(STRAIN_XY)), float(np.max(STRAIN_XY)), 9,
    )
    plotter.add_contour(
        VORTEX_MESH_X, VORTEX_MESH_Y, STRAIN_XX, subplot=0,
        title="正应变 εxx 云图 + 剪应变 εxy 等值线",
        xlabel="x", ylabel="y",
        levels=24, line_levels=contour_levels, cmap="RdBu_r",
        filled=True, alpha=0.85,
        contour_kwargs={"colors": "#263238", "linewidths": 0.7,
                        "alpha": 0.8},
        clabel=True,
        clabel_kwargs={"inline": True, "fontsize": 6.5, "fmt": "%.1f",
                       "colors": "#263238"},
        colorbar=True,
        colorbar_kwargs={"label": "εxx", "shrink": 0.85},
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
    )

    # 右：张量的主轴方向 —— 每点的特征向量
    #     对称张量 [[εxx, εxy], [εxy, -εxx]] 的特征向量方向为
    #     (cos θ, sin θ)，其中 2θ = atan2(2εxy, 2εxx)。
    theta = 0.5 * np.arctan2(2.0 * STRAIN_XY, 2.0 * STRAIN_XX)
    principal_x = np.cos(theta)
    principal_y = np.sin(theta)

    plotter.add_quiver(
        VORTEX_MESH_X, VORTEX_MESH_Y,
        principal_x, principal_y, subplot=1,
        title="张量主轴方向场（每点的特征向量）",
        xlabel="x", ylabel="y",
        scale=24, cmap="coolwarm", color_by_magnitude=False,
        color="#37474F",
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
        width=0.004,
    )

    plotter.draw(show=False)
    save_current("20_tensor_field_example.png")


# ======================================================================
# 3. 三维矢量场：箭头 + RK4 流线
# ======================================================================

def example_vector_3d():
    reset_style()

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(5.6, 5.2), dpi=72)

    view_3d = {
        "xlim": (-2, 2), "ylim": (-2, 2), "zlim": (-1.5, 1.5),
        "elev": 22, "azim": -58, "box_aspect": (1, 1, 0.65),
    }

    # 左：三维箭头
    plotter.add_quiver3d(
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        subplot=0,
        title="三维矢量场（箭头按模长着色）",
        xlabel="x", ylabel="y", zlabel="z",
        density=11, length=0.45, cmap="turbo", colorbar=True,
        colorbar_kwargs={"label": "|V|", "shrink": 0.7},
        view=view_3d,
    )

    # 右：RK4 积分的三维流线
    plotter.add_stream3d(
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        subplot=1,
        title="同一场的三维流线（RK4 积分）",
        xlabel="x", ylabel="y", zlabel="z",
        field_func=field_3d,
        n_seeds=9, seed_radius=0.55,
        step_size=0.05, max_steps=500,
        line_width=2.0,
        # 这里固定颜色：绕涡轴一圈的速度几乎相同，
        # 按速度着色会让颜色条范围被压得很窄，反而看不清。
        color="#C62828", color_by_speed=False,
        view=view_3d,
    )

    plotter.draw(show=False)
    save_current("21_vector_3d_example.png")


# ======================================================================
# 4. 表格
# ======================================================================

def example_table():
    reset_style()

    plotter = MultiPlotter(ncols=1, figsize_per_plot=(9.0, 4.2), dpi=80)

    plotter.add_table(
        TABLE_DATA,
        subplot=0,
        title="模型压缩实验结果",
        row_labels=TABLE_ROW_LABELS,
        col_labels=["基线", "剪枝", "量化", "变化"],
        col_width=[1.0, 1.0, 1.0, 1.1],
        cell_align="center",
        cell_fontsize=11,
        cell_height=0.115,
        background_color="#FFFFFF",
        text_color="#263238",
        edge_color="#B0BEC5",
        edge_width=0.9,
        header_background="#1976D2",
        header_text_color="#FFFFFF",
        header_fontsize=11.5,
        row_label_background="#ECEFF1",
        row_label_text_color="#263238",
        zebra_color="#F5F7F9",
        # 最后一列是“变化”，整列高亮成绿色
        highlight=[(0, 3), (1, 3), (2, 3), (3, 3), (4, 3)],
        highlight_color="#C8E6C9",
        highlight_text_color="#1B5E20",
        highlight_bold=True,
        bbox=[0.02, 0.06, 0.96, 0.82],
        view={"xlim": (0.0, 1.0), "ylim": (0.0, 1.0)},
    )

    plotter.draw(show=False)
    save_current("24_table_example.png")


# ======================================================================
# 5. 动图：二维流场旋转
# ======================================================================

def example_vector_2d_animated():
    """二维矢量场动画。

    这里必须用**真正随时间变化**的流场（双涡对）。
    单个高斯涡是旋转对称的，绕轴旋转后还是同一个场，
    流线在数学上完全不变，动画会看起来像静止的（曾经踩过这个坑）。
    """
    reset_style()

    plotter = AnimationPlotter(ncols=2, figsize_per_plot=(5.4, 4.4),
                               dpi=85)

    # 初始时刻（phase=0）的双涡对流场
    pair_u, pair_v = vortex_pair(VORTEX_MESH_X, VORTEX_MESH_Y, 0.0)

    plotter.add_quiver(
        VORTEX_MESH_X, VORTEX_MESH_Y, pair_u, pair_v, subplot=0,
        title="双涡对（箭头）",
        xlabel="x", ylabel="y",
        scale=6, cmap="turbo",
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
        width=0.006,
    )
    plotter.add_streamplot(
        VORTEX_MESH_X, VORTEX_MESH_Y, pair_u, pair_v, subplot=1,
        title="同一时刻的流线",
        xlabel="x", ylabel="y",
        density=1.4, line_width=1.2, cmap="turbo", arrowsize=1.1,
        view={"xlim": (-2, 2), "ylim": (-2, 2), "aspect": "equal"},
    )
    plotter.draw(show=False)

    quiver_ax = plotter.get_axes(0)

    def update(ax, frame):
        """两个子图都用 reset 模式：clear 之后各自重画。

        注意：update_mode="reset" 会对每个参与动画的子图都执行一次
        ax.clear()，所以**两个子图都必须在这里重画**，
        漏掉哪个哪个就会变成空白（箭头子图最容易漏）。
        """
        # 每帧把双涡对转过 18°，流线形态随之改变
        phase = np.deg2rad(frame * 18.0)
        qu, qv = vortex_pair(VORTEX_MESH_X, VORTEX_MESH_Y, phase)
        speed = np.hypot(qu, qv)

        if ax is quiver_ax:
            ax.quiver(
                VORTEX_MESH_X, VORTEX_MESH_Y, qu, qv, speed,
                cmap="turbo", scale=6, width=0.006,
            )
            ax.set_xlim(-2, 2)
            ax.set_ylim(-2, 2)
            ax.set_aspect("equal")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_title(f"双涡对（箭头，phase {frame * 18}°）")
        else:
            ax.streamplot(
                VORTEX_MESH_X, VORTEX_MESH_Y, qu, qv,
                density=1.4, color=speed, cmap="turbo",
                linewidth=1.2, arrowsize=1.1,
            )
            ax.set_xlim(-2, 2)
            ax.set_ylim(-2, 2)
            ax.set_aspect("equal")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_title(f"同一时刻的流线（phase {frame * 18}°）")

        return ax,

    target = out("22_vector_2d_animated.gif")

    if os.path.exists(target):
        os.remove(target)

    plotter.animate(
        subplots=[0, 1],
        frames=10, interval=160, blit=False, update_mode="reset",
        update_func=update,
        save_path=target, fps=6, dpi=70,
    )
    plotter.stop_animation()
    plt.close("all")


# ======================================================================
# 6. 动图：三维矢量场视点旋转
# ======================================================================

def example_vector_3d_animated():
    reset_style()

    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(6.4, 5.6),
                               dpi=85)

    view_3d = {
        "xlim": (-2, 2), "ylim": (-2, 2), "zlim": (-1.5, 1.5),
        "elev": 22, "azim": -60, "box_aspect": (1, 1, 0.65),
    }

    plotter.add_quiver3d(
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        subplot=0,
        title="三维矢量场",
        xlabel="x", ylabel="y", zlabel="z",
        density=10, length=0.45, cmap="turbo",
        colorbar=True,
        colorbar_kwargs={"shrink": 0.7, "label": "|V|"},
        view=view_3d,
    )
    plotter.add_stream3d(
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        subplot=0,
        xlabel="x", ylabel="y", zlabel="z",
        field_func=field_3d,
        n_seeds=8, seed_radius=0.5, step_size=0.05, max_steps=500,
        line_width=1.8, color="#E64A19",
        color_by_speed=False,
        view=view_3d,
    )
    plotter.draw(show=False)

    ax = plotter.get_axes(0)

    # update_mode="reset" 会先 ax.clear()，
    # 所以每帧必须把箭头和流线重新画一遍，只改视角是不够的。
    ep = 0.06

    # 和 add_quiver3d 一样先按 density 抽稀，否则 21x21x15 的网格
    # 会画出 6000 多支箭头，既看不清也把流线埋掉了
    qx, qy, qz, qu, qv, qw = MultiPlotter._shrink_field(
        MESH_3D_X, MESH_3D_Y, MESH_3D_Z,
        FIELD_3D_U, FIELD_3D_V, FIELD_3D_W,
        density=10,
    )
    magnitudes = np.linalg.norm(np.column_stack([qu, qv, qw]), axis=1)
    norm = Normalize(vmin=float(magnitudes.min()),
                     vmax=float(magnitudes.max()))
    cmap_obj = plt.get_cmap("turbo")

    # 预先用与 add_stream3d 相同的算法（Fibonacci 球面撒点 + RK4）积出流线，
    # 逐帧复用，避免每帧重新积分。
    bounds = ((-2.0, 2.0), (-2.0, 2.0), (-1.5, 1.5))

    seed_config = {
        "bound": bounds,
        "seeds": None,
        "n_seeds": 8,
        "seed_radius": 0.5,
        "seed": 0,
    }
    seeds = plotter._build_seeds(seed_config)
    streams = []

    for point in seeds:
        forward = plotter._integrate_streamline(
            point, field_3d, step=0.05, direction=1.0,
            bound=bounds, max_steps=500,
        )
        backward = plotter._integrate_streamline(
            point, field_3d, step=0.05, direction=-1.0,
            bound=bounds, max_steps=500,
        )

        if forward is None:
            continue

        if backward is not None and len(backward) > 1:
            trajectory = np.vstack([backward[::-1][:-1], forward])
        else:
            trajectory = forward

        streams.append(np.asarray(trajectory))

    def update(ax, frame):
        angle = -60 + frame * 18

        ax.clear()
        ax.quiver(
            qx, qy, qz, qu, qv, qw,
            colors=cmap_obj(norm(magnitudes)),
            length=0.45, normalize=True, arrow_length_ratio=0.3,
        )

        # 流线用更大的 zorder，避免被箭头盖住
        for trajectory in streams:
            ax.plot(trajectory[:, 0], trajectory[:, 1], trajectory[:, 2],
                    color="#E64A19", linewidth=2.6, zorder=100)

        # 稍微内缩坐标轴，避免旋转到侧面时箭头被裁掉
        ax.set_xlim(-2 + ep, 2 - ep)
        ax.set_ylim(-2 + ep, 2 - ep)
        ax.set_zlim(-1.5 + ep, 1.5 - ep)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("z")
        ax.view_init(elev=22, azim=angle)
        ax.set_box_aspect((1, 1, 0.65))
        ax.grid(True)
        ax.set_title(f"三维矢量场 + 流线（视点旋转 {frame * 18}°）")

        return [ax]

    target = out("23_vector_3d_animated.gif")

    if os.path.exists(target):
        os.remove(target)

    plotter.animate(
        subplots=[0],
        frames=20, interval=140, blit=False, update_mode="reset",
        update_func=update,
        save_path=target, fps=7, dpi=70,
    )
    plotter.stop_animation()
    plt.close("all")


def main():
    example_vector_2d()
    print("[ok] 19_vector_2d_example.png")

    example_tensor_field()
    print("[ok] 20_tensor_field_example.png")

    example_vector_3d()
    print("[ok] 21_vector_3d_example.png")

    example_table()
    print("[ok] 24_table_example.png")

    example_vector_2d_animated()
    print("[ok] 22_vector_2d_animated.gif")

    example_vector_3d_animated()
    print("[ok] 23_vector_3d_animated.gif")

    for name in (
        "19_vector_2d_example.png",
        "20_tensor_field_example.png",
        "21_vector_3d_example.png",
        "24_table_example.png",
        "22_vector_2d_animated.gif",
        "23_vector_3d_animated.gif",
    ):
        print(f"    {name}: {os.path.getsize(out(name)) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
