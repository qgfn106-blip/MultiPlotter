# -*- coding: utf-8 -*-
"""绘图契约回归测试：确认重构没有改变既有绘图行为。

背景
----
重构的硬约束是「类方法原有功能不受影响、绘制代码不变」。
本测试把这个约束固化成可执行断言：

1. **登记阶段**：每个代表性 ``add_*`` 调用产生的 ``config`` 字典
   （字段名与取值）必须与基线一致；
2. **绘制阶段**：``draw()`` 之后，Figure / Axes / artist 的可观测属性
   （子图数、线数、面片数、标题、坐标轴标签、范围、图例、颜色条）必须一致。

``tests/contract_baseline.json`` 是基线快照。
早期版本曾用一份「重构前」的基线确认过等价性（唯一两处预期差异是
每个图层的 ``view`` 由 ``None`` 归一化为 ``{}``，以及 ``draw()`` 不再改全局
rcParams）；那份一次性基线在收尾时被删除，这里改为**长期保留**的回归基线。

用法::

    python tests/contract_test.py                  # 校验
    python tests/contract_test.py --update         # 重新生成基线
"""

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from multiplotter import MultiPlotter  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "contract_baseline.json")

# ----------------------------------------------------------------------
# 共用数据
# ----------------------------------------------------------------------

X = np.linspace(0.0, 6.0, 24)
Y = np.sin(X)
Y2 = np.cos(X)

GRID_AXIS = np.linspace(-2.0, 2.0, 12)
GRID_X, GRID_Y = np.meshgrid(GRID_AXIS, GRID_AXIS)
GRID_Z = np.exp(-(GRID_X ** 2 + GRID_Y ** 2))

FIELD_X = np.linspace(0.0, 2.0 * np.pi, 14)
FIELD_Y = np.linspace(0.0, 2.0 * np.pi, 11)
FIELD_XX, FIELD_YY = np.meshgrid(FIELD_X, FIELD_Y)
FIELD_U = -np.sin(FIELD_XX) * np.cos(FIELD_YY)
FIELD_V = np.cos(FIELD_XX) * np.sin(FIELD_YY)

TABLE_ROWS = [["a", "1.0"], ["b", "2.0"], ["c", "3.0"]]
HIST_DATA = np.array([1.0, 1.5, 2.0, 2.0, 2.5, 3.0, 3.5, 4.0])


def build_plotter():
    """返回一个统一的二维/三维混合画布。"""

    return MultiPlotter(ncols=3, figsize_per_plot=(4.0, 3.0), dpi=60)


#: 每个场景：名字 -> (往 plotter 上挂图层的函数, 该场景关注的子图号)
SCENARIOS = {}


def scenario(name, subplot=0):
    def decorator(func):
        SCENARIOS[name] = (func, subplot)
        return func

    return decorator


@scenario("line", subplot=0)
def _line(plotter):
    plotter.add_plot(
        kind="line", x=X, y=Y, subplot=0,
        title="line", xlabel="x", ylabel="y",
        color="#1976D2", linewidth=2.0, marker="o",
        label="sin", legend=True,
        view={"xlim": (0.0, 6.0), "ylim": (-1.5, 1.5), "grid": True},
    )


@scenario("scatter", subplot=0)
def _scatter(plotter):
    plotter.add_plot(
        kind="scatter", x=X, y=Y, subplot=0,
        title="scatter", xlabel="x", ylabel="y",
        color="#E64A19", s=30, alpha=0.7, label="pts", legend=True,
        view={"xlim": (0.0, 6.0), "ylim": (-1.5, 1.5)},
    )


@scenario("bar", subplot=0)
def _bar(plotter):
    plotter.add_plot(
        kind="bar", x=np.arange(5.0), y=np.array([3.0, 1.0, 4.0, 2.0, 5.0]),
        subplot=0, title="bar", xlabel="i", ylabel="v",
        show_values=True, value_format=".1f",
        view={"grid": True},
    )


@scenario("hist", subplot=0)
def _hist(plotter):
    plotter.add_plot(
        kind="hist", x=HIST_DATA, subplot=0,
        title="hist", xlabel="v", ylabel="n",
        bins=6, show_values=True,
    )


@scenario("pie", subplot=0)
def _pie(plotter):
    plotter.add_pie(
        labels=["a", "b", "c"], values=[3.0, 2.0, 1.0],
        subplot=0, title="pie", startangle=90,
    )


@scenario("heatmap", subplot=0)
def _heatmap(plotter):
    plotter.add_plot(
        kind="heatmap", data=GRID_Z, subplot=0,
        title="heatmap", xlabel="x", ylabel="y",
        cmap="viridis", colorbar=True,
        view={"aspect": "equal"},
    )


@scenario("image", subplot=0)
def _image(plotter):
    plotter.add_plot(
        kind="image", image=GRID_Z, subplot=0,
        title="image", xlabel="x", ylabel="y",
        cmap="magma",
    )


@scenario("contour", subplot=0)
def _contour(plotter):
    plotter.add_contour(
        GRID_X, GRID_Y, GRID_Z, subplot=0,
        title="contour", xlabel="x", ylabel="y",
        levels=8, line_levels=6, cmap="viridis",
        clabel=True, colorbar=True,
        view={"aspect": "equal"},
    )


@scenario("surface", subplot=0)
def _surface(plotter):
    plotter.add_surface(
        GRID_X, GRID_Y, GRID_Z, subplot=0,
        title="surface", xlabel="x", ylabel="y", zlabel="z",
        cmap="turbo", light_enhance=True, colorbar=True,
        view={"elev": 30, "azim": -60, "box_aspect": (1, 1, 0.7)},
    )


@scenario("line3d", subplot=0)
def _line3d(plotter):
    plotter.add_line3d(
        X, Y, np.sin(X), subplot=0,
        title="line3d", xlabel="x", ylabel="y", zlabel="z",
        color="crimson", linewidth=2.5, marker="o",
        label="h", legend=True,
        view={"elev": 25, "azim": -55},
    )


@scenario("scatter3d", subplot=0)
def _scatter3d(plotter):
    plotter.add_scatter3d(
        X, Y, np.cos(X), subplot=0,
        title="scatter3d", xlabel="x", ylabel="y", zlabel="z",
        color="teal", label="p", legend=True,
    )


@scenario("bar3d", subplot=0)
def _bar3d(plotter):
    plotter.add_bar3d(
        np.arange(3.0), np.arange(3.0), np.zeros(3),
        np.full(3, 0.6), np.full(3, 0.6), np.array([1.0, 2.0, 3.0]),
        subplot=0, title="bar3d", xlabel="x", ylabel="y", zlabel="z",
        show_values=True,
    )


@scenario("hist3d", subplot=0)
def _hist3d(plotter):
    plotter.add_hist3d(
        HIST_DATA, HIST_DATA * 1.5, subplot=0,
        title="hist3d", xlabel="x", ylabel="y", zlabel="z",
    )


@scenario("quiver", subplot=0)
def _quiver(plotter):
    plotter.add_quiver(
        FIELD_X, FIELD_Y, FIELD_U, FIELD_V, subplot=0,
        title="quiver", xlabel="x", ylabel="y",
        colorbar=True, view={"aspect": "equal"},
    )


@scenario("streamplot", subplot=0)
def _streamplot(plotter):
    plotter.add_streamplot(
        FIELD_X, FIELD_Y, FIELD_U, FIELD_V, subplot=0,
        title="streamplot", xlabel="x", ylabel="y",
        cmap="turbo", colorbar=True, view={"aspect": "equal"},
    )


@scenario("quiver3d", subplot=0)
def _quiver3d(plotter):
    # 三维矢量场要求 u / v / w 是三维数组 (nx, ny, nz)
    axis = np.linspace(0.0, 2.0 * np.pi, 8)
    gx, gy, gz = np.meshgrid(axis, axis, axis, indexing="ij")
    u = -np.sin(gx) * np.cos(gy)
    v = np.cos(gx) * np.sin(gy)
    w = 0.3 * np.sin(gz)

    plotter.add_quiver3d(
        axis, axis, axis, u, v, w, subplot=0, title="quiver3d",
        xlabel="x", ylabel="y", zlabel="z",
    )


@scenario("stream3d", subplot=0)
def _stream3d(plotter):
    def field(x, y, z):
        """解析矢量场：三维流线是「解析场」的积分结果。"""

        return (
            -np.sin(x) * np.cos(y),
            np.cos(x) * np.sin(y),
            0.3 * np.sin(z),
        )

    axis = np.linspace(0.0, 2.0 * np.pi, 8)
    gx, gy, gz = np.meshgrid(axis, axis, axis, indexing="ij")
    # u / v / w 在这里只用来确定积分域的边界，取值由 field_func 提供
    zeros = np.zeros_like(gx)

    plotter.add_stream3d(
        axis, axis, axis, zeros, zeros, zeros,
        subplot=0, title="stream3d",
        xlabel="x", ylabel="y", zlabel="z",
        field_func=field,
        n_seeds=4, max_steps=120, line_width=1.5,
    )


@scenario("table", subplot=0)
def _table(plotter):
    plotter.add_table(
        TABLE_ROWS, subplot=0, title="table",
        col_labels=["k", "v"], highlight={"<": 2.0},
        view={"xlim": (0.0, 1.0), "ylim": (0.0, 1.0)},
    )


# ======================================================================
# 快照
# ======================================================================

def jsonable(value):
    """把 config 里的值转成可稳定比较、可 JSON 序列化的形式。"""

    if isinstance(value, np.ndarray):
        # 数值数组记录数值，字符串 / object 数组（例如表格的 cell_text）
        # 记录前几个元素本身即可。
        if value.dtype.kind in "fiub":
            preview = [round(float(item), 6) for item in value.ravel()[:12]]
        else:
            preview = [str(item) for item in value.ravel()[:12]]

        return {
            "__ndarray__": True,
            "dtype": str(value.dtype),
            "shape": list(value.shape),
            "flat": preview,
        }

    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in sorted(value.items())}

    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]

    if isinstance(value, (set, frozenset)):
        return sorted(jsonable(item) for item in value)

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return f"<{type(value).__name__}>"


def axes_facts(ax):
    """采集一个 Axes 上可观测的绘制结果。"""

    facts = {
        "is_3d": hasattr(ax, "get_zlim"),
        "title": ax.get_title(),
        "xlabel": ax.get_xlabel(),
        "ylabel": ax.get_ylabel(),
        "n_lines": len(ax.lines),
        "n_patches": len(ax.patches),
        "n_collections": len(ax.collections),
        "n_texts": len(ax.texts),
        "n_images": len(ax.images),
        "n_tables": len(ax.tables),
        "has_legend": ax.get_legend() is not None,
    }

    facts["xlim"] = [round(float(item), 4) for item in ax.get_xlim()]
    facts["ylim"] = [round(float(item), 4) for item in ax.get_ylim()]

    if facts["is_3d"]:
        facts["zlabel"] = ax.get_zlabel()
        facts["zlim"] = [round(float(item), 4) for item in ax.get_zlim()]
        facts["elev"] = round(float(ax.elev), 3)
        facts["azim"] = round(float(ax.azim), 3)

    return facts


def run_scenario(name):
    """跑一个场景，返回 ``{config, axes}`` 两部分快照。"""

    builder, subplot = SCENARIOS[name]
    plotter = build_plotter()
    builder(plotter)

    configs = [jsonable(dict(config)) for config in plotter.plot_configs]

    fig, axes = plotter.draw(show=False)
    facts = axes_facts(axes[subplot])

    # 颜色条在 draw() 里以独立 Axes 出现，数量也要盯住
    facts["figure_axes"] = len(fig.axes)

    plt.close("all")

    return {"configs": configs, "axes": facts}


def collect():
    """跑全部场景，返回完整快照。"""

    return {name: run_scenario(name) for name in sorted(SCENARIOS)}


def find_differences(actual, expected):
    """比较当前快照与基线，返回人类可读的差异列表。"""

    problems = []
    all_names = sorted(set(actual) | set(expected))

    for name in all_names:
        if name not in expected:
            problems.append(f"{name}: 新增场景（基线里没有）")
            continue

        if name not in actual:
            problems.append(f"{name}: 场景消失")
            continue

        before, now = expected[name], actual[name]

        if before["configs"] != now["configs"]:
            for index, (old, new) in enumerate(
                zip(before["configs"], now["configs"])
            ):
                for field in sorted(set(old) | set(new)):
                    if old.get(field) != new.get(field):
                        problems.append(
                            f"{name}.configs[{index}].{field}:\n"
                            f"        基线: {old.get(field)}\n"
                            f"        当前: {new.get(field)}"
                        )

        for field in sorted(set(before["axes"]) | set(now["axes"])):
            if before["axes"].get(field) != now["axes"].get(field):
                problems.append(
                    f"{name}.axes.{field}:\n"
                    f"        基线: {before['axes'].get(field)}\n"
                    f"        当前: {now['axes'].get(field)}"
                )

    return problems


def test_contract_matches_baseline():
    """pytest 入口：登记阶段与绘制阶段都必须与基线一致。"""

    assert os.path.isfile(BASELINE), (
        f"缺少基线文件 {BASELINE}；"
        "运行 python tests/contract_test.py --update 生成"
    )

    with open(BASELINE, encoding="utf-8") as handle:
        expected = json.load(handle)

    problems = find_differences(collect(), expected)

    assert not problems, (
        "绘图契约与基线不一致：\n  " + "\n  ".join(problems)
        + "\n\n如果是刻意改动绘图行为，确认后执行："
        "\n  python tests/contract_test.py --update"
    )


def main():
    update = "--update" in sys.argv
    actual = collect()

    if update:
        with open(BASELINE, "w", encoding="utf-8") as handle:
            json.dump(actual, handle, ensure_ascii=False, indent=2,
                      sort_keys=True)
            handle.write("\n")

        print(f"已更新基线：{BASELINE}（{len(actual)} 个场景）")
        return 0

    if not os.path.isfile(BASELINE):
        print(f"缺少基线文件 {BASELINE}；"
              "运行 python tests/contract_test.py --update 生成")
        return 1

    with open(BASELINE, encoding="utf-8") as handle:
        expected = json.load(handle)

    problems = find_differences(actual, expected)

    print(f"对比 {len(actual)} 个场景的 config 与绘制结果")

    if problems:
        print(f"\n发现 {len(problems)} 处差异：")
        for item in problems:
            print("  -", item)
        print("\n如果是有意改动绘图行为，确认后执行："
              "\n  python tests/contract_test.py --update")
        return 1

    print("全部一致：登记阶段与绘制阶段都没有变化")
    return 0


if __name__ == "__main__":
    sys.exit(main())
