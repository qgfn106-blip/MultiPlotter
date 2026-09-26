# -*- coding: utf-8 -*-
"""参数校验与规格化。

这里只放「纯函数」：输入数据、输出数据或抛出 ``ValueError``，
不依赖任何实例状态，也不碰 Matplotlib。

公开 API
--------
数组与网格
    ``as_1d_array`` / ``check_same_length`` / ``broadcast_to_length``
    ``mesh_coordinates``
矢量场
    ``field_coordinates`` / ``field_coordinates_3d`` / ``field_norm``
    ``shrink_field`` / ``integrate_streamline``
表格
    ``table_shape`` / ``table_style_array`` / ``table_cell_keys``
    ``resolve_highlight`` / ``compare``
配置读取
    ``is_nonempty`` / ``first_nonempty`` / ``first_defined``
格式化
    ``format_value``
"""

from __future__ import annotations

import numpy as np

# ----------------------------------------------------------------------
# 数组与网格
# ----------------------------------------------------------------------


def as_1d_array(value, name):
    """把标量或数组转换为一维数组，维度不对就报错。"""

    array = np.atleast_1d(np.asarray(value))

    if array.ndim != 1:
        raise ValueError(
            f"{name}必须是标量或一维数组，"
            f"当前维度为{array.ndim}"
        )

    return array


def check_same_length(*arrays):
    """检查多个数组长度是否一致。"""

    lengths = [len(array) for array in arrays]

    if len(set(lengths)) != 1:
        raise ValueError(
            f"数组长度必须一致，当前长度为：{lengths}"
        )


def broadcast_to_length(value, length, name):
    """把标量、单元素数组或指定长度数组转换成指定长度数组。"""

    array = np.asarray(value)

    if array.ndim == 0:
        return np.full(length, array.item())

    array = np.atleast_1d(array)

    if len(array) == 1:
        return np.full(length, array[0])

    if len(array) != length:
        raise ValueError(
            f"{name}必须是标量、长度为1的数组，"
            f"或长度为{length}的数组；"
            f"当前长度为{len(array)}"
        )

    return array


def mesh_coordinates(x, y, z):
    """检查并统一处理曲面/等高线的坐标。

    支持两种写法：

    * ``x``、``y`` 是一维坐标 -> 自动 ``meshgrid``，
      ``z`` 形状必须是 ``(len(y), len(x))``；
    * ``x``、``y`` 已经是二维网格 -> 三者形状必须完全一致。

    返回 ``(X, Y, Z)``。
    """

    x = np.asarray(x)
    y = np.asarray(y)
    z = np.asarray(z)

    if z.ndim != 2:
        raise ValueError(
            "z必须是二维数组，"
            "例如形状为(len(y), len(x))"
        )

    # x、y是一维坐标
    if x.ndim == 1 and y.ndim == 1:
        expected_shape = (len(y), len(x))

        if z.shape != expected_shape:
            raise ValueError(
                f"z的形状应该是{expected_shape}，"
                f"但实际得到的是{z.shape}"
            )

        X, Y = np.meshgrid(x, y)

    # x、y已经是二维网格
    elif x.ndim == 2 and y.ndim == 2:
        if x.shape != z.shape or y.shape != z.shape:
            raise ValueError(
                "当x、y为二维网格时，"
                "x、y、z的形状必须完全一致"
            )

        X, Y = x, y

    else:
        raise ValueError(
            "x和y必须同时是一维数组，"
            "或者同时是二维网格数组"
        )

    return X, Y, z


# ----------------------------------------------------------------------
# 矢量场
# ----------------------------------------------------------------------


def field_coordinates(x, y, u, v, name="矢量场"):
    """检查并统一处理二维矢量场的坐标与分量。

    支持两种写法：

    * ``x``、``y`` 是一维坐标 -> 自动 ``meshgrid``，
      ``u``、``v`` 形状必须是 ``(len(y), len(x))``；
    * ``x``、``y`` 是二维网格 -> 四者形状必须完全一致。

    返回 ``(X, Y, U, V)``。
    """

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)

    if u.ndim != 2 or v.ndim != 2:
        raise ValueError(
            f"{name}的 u、v 必须是二维数组，"
            f"当前维度为 {u.ndim}、{v.ndim}"
        )

    if u.shape != v.shape:
        raise ValueError(
            f"{name}的 u、v 形状必须一致，"
            f"当前为 {u.shape} 与 {v.shape}"
        )

    # x、y 是一维坐标
    if x.ndim == 1 and y.ndim == 1:
        expected_shape = (len(y), len(x))

        if u.shape != expected_shape:
            raise ValueError(
                f"{name}的 u、v 形状应该是{expected_shape}，"
                f"但实际得到的是{u.shape}"
            )

        X, Y = np.meshgrid(x, y)

    # x、y 已经是二维网格
    elif x.ndim == 2 and y.ndim == 2:
        if x.shape != u.shape or y.shape != u.shape:
            raise ValueError(
                "当x、y为二维网格时，"
                "x、y、u、v的形状必须完全一致，"
                f"当前为 {x.shape}、{y.shape}、{u.shape}、{v.shape}"
            )

        X, Y = x, y

    else:
        raise ValueError(
            "x和y必须同时是一维数组，"
            "或者同时是二维网格数组"
        )

    return X, Y, u, v


def field_coordinates_3d(x, y, z, u, v, w, name="三维矢量场"):
    """检查并统一处理三维矢量场的坐标与分量。

    支持两种写法：

    * ``x``、``y``、``z`` 是一维坐标 -> 自动展开成网格，
      ``u``、``v``、``w`` 形状必须是下面两种之一（第三个下标是 z）：

      - ``(len(x), len(y), len(z))`` 对应 ``indexing="ij"``
      - ``(len(y), len(x), len(z))`` 对应 ``indexing="xy"``

    * ``x``、``y``、``z`` 是三维网格 -> 六者形状必须完全一致。

    返回 ``(X, Y, Z, U, V, W)``。
    """

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    w = np.asarray(w, dtype=float)

    for array, axis_name in ((u, "u"), (v, "v"), (w, "w")):
        if array.ndim != 3:
            raise ValueError(
                f"{name}的 {axis_name} 必须是三维数组，"
                f"当前维度为 {array.ndim}"
            )

    if not (u.shape == v.shape == w.shape):
        raise ValueError(
            f"{name}的 u、v、w 形状必须一致，"
            f"当前为 {u.shape}、{v.shape}、{w.shape}"
        )

    # x、y、z 是一维坐标
    if x.ndim == 1 and y.ndim == 1 and z.ndim == 1:
        # 兼容两种网格约定，靠形状自动判断：
        #
        #   indexing="ij" 的 meshgrid -> (len(x), len(y), len(z))
        #   indexing="xy" 的 meshgrid -> (len(y), len(x), len(z))
        #
        # 两种情况下 u[..., 2] 都对应 z（第三个下标是 z），
        # 所以画面和物理含义一致，只是前两个轴的顺序不同。
        shape_ij = (len(x), len(y), len(z))
        shape_xy = (len(y), len(x), len(z))

        if len(set(shape_ij)) == 1 and len(set(shape_xy)) == 1:
            # 三个轴长度相同，无法区分，统一按 ij 处理并提示
            print(
                "[MultiPlotter] 提示：三维坐标三个轴长度相同，"
                "无法自动判断网格约定，已按 numpy.meshgrid(..., "
                "indexing='ij') 处理。"
            )

        if u.shape == shape_ij:
            X = np.broadcast_to(x.reshape(-1, 1, 1), shape_ij).copy()
            Y = np.broadcast_to(y.reshape(1, -1, 1), shape_ij).copy()
            Z = np.broadcast_to(z.reshape(1, 1, -1), shape_ij).copy()

        elif u.shape == shape_xy:
            X = np.broadcast_to(x.reshape(1, -1, 1), shape_xy).copy()
            Y = np.broadcast_to(y.reshape(-1, 1, 1), shape_xy).copy()
            Z = np.broadcast_to(z.reshape(1, 1, -1), shape_xy).copy()

        else:
            raise ValueError(
                f"{name}的 u、v、w 形状与一维坐标不匹配，"
                f"当前为{u.shape}。\n"
                "一维坐标下 u、v、w 的形状必须是下面两种之一：\n"
                f"  {shape_ij}  对应 numpy.meshgrid(x, y, z, indexing='ij')\n"
                f"  {shape_xy}  对应 numpy.meshgrid(x, y, z, indexing='xy')\n"
                "两种写法都要求“第三个下标是 z”。"
            )

    # x、y、z 已经是三维网格
    elif x.ndim == 3 and y.ndim == 3 and z.ndim == 3:
        if x.shape != u.shape or y.shape != u.shape or z.shape != u.shape:
            raise ValueError(
                "当x、y、z为三维网格时，"
                "x、y、z、u、v、w的形状必须完全一致，"
                f"当前为 {x.shape}、{y.shape}、{z.shape}、{u.shape}"
            )

        X, Y, Z = x, y, z

    else:
        raise ValueError(
            "x、y、z必须同时是一维数组，"
            "或者同时是三维网格数组"
        )

    return X, Y, Z, u, v, w


def field_norm(u, v, w=None):
    """计算矢量场大小，用于按模长着色。"""

    norm = np.sqrt(u ** 2 + v ** 2)

    if w is not None:
        norm = np.sqrt(norm ** 2 + w ** 2)

    return norm


def shrink_field(x, y, z, u, v, w, density=18):
    """把三维矢量场按密度抽稀，避免箭头过密。

    参数顺序为 ``(x, y, z, u, v, w)``，返回抽稀后同样的六元组。
    一维坐标会被当成网格轴来处理，先展开成网格再统一抽稀。
    """

    X, Y, Z = (np.asarray(x), np.asarray(y), np.asarray(z))

    u = np.asarray(u)
    v = np.asarray(v)
    w = np.asarray(w)

    # 一维轴 -> 三维网格，形状统一为 (len(z), len(y), len(x))
    if X.ndim == 1 and Y.ndim == 1 and Z.ndim == 1:
        shape = u.shape

        X = np.broadcast_to(X.reshape(1, 1, -1), shape)
        Y = np.broadcast_to(Y.reshape(1, -1, 1), shape)
        Z = np.broadcast_to(Z.reshape(-1, 1, 1), shape)

    if X.ndim != 3:
        raise ValueError(
            "三维矢量场抽稀前，坐标必须是一维轴或三维网格，"
            f"当前维度为{X.ndim}"
        )

    if not (X.shape == Y.shape == Z.shape == u.shape == v.shape == w.shape):
        raise ValueError(
            "抽稀前 x、y、z、u、v、w 的形状必须完全一致，"
            f"当前为 {X.shape}、{Y.shape}、{Z.shape}、"
            f"{u.shape}、{v.shape}、{w.shape}"
        )

    nz, ny, nx = X.shape

    step = max(
        1,
        int(round(max(nx, ny, nz) / max(int(density), 1))),
    )

    selection = np.s_[::step, ::step, ::step]

    return (
        np.asarray(X)[selection].ravel(),
        np.asarray(Y)[selection].ravel(),
        np.asarray(Z)[selection].ravel(),
        u[selection].ravel(),
        v[selection].ravel(),
        w[selection].ravel(),
    )


def integrate_streamline(point, field, step, direction, bound, max_steps):
    """用四阶龙格-库塔法（RK4）积分一条流线的轨迹。

    参数
    ----
    point
        起始点 ``(x, y, z)``
    field
        可调用对象 ``field(x, y, z) -> (u, v, w)``
    step
        积分步长（数据坐标单位）
    direction
        ``+1`` 或 ``-1``，表示正向或反向积分
    bound
        边界 ``((xmin, xmax), (ymin, ymax), (zmin, zmax))``
    max_steps
        最大步数，防止死循环

    返回形状为 ``(n, 3)`` 的轨迹数组；
    起点本身就在边界外、或积分不出两个点时返回 ``None``。
    """

    def inside(current):
        for value, (low, high) in zip(current, bound):
            if not (low <= value <= high):
                return False
        return True

    if not inside(point):
        return None

    trajectory = [np.asarray(point, dtype=float)]
    current = np.asarray(point, dtype=float)

    def derivative(state):
        velocity = np.asarray(
            field(state[0], state[1], state[2]),
            dtype=float,
        )

        if velocity.shape != (3,):
            raise ValueError(
                "三维流线场函数必须返回长度为3的(u, v, w)"
            )

        return velocity

    for _ in range(int(max_steps)):
        k1 = derivative(current)
        k2 = derivative(current + 0.5 * step * direction * k1)
        k3 = derivative(current + 0.5 * step * direction * k2)
        k4 = derivative(current + step * direction * k3)

        nxt = current + (
            step * direction / 6.0
        ) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

        if not inside(nxt):
            break

        trajectory.append(nxt)
        current = nxt

    if len(trajectory) < 2:
        return None

    return np.asarray(trajectory)


# ----------------------------------------------------------------------
# 表格
# ----------------------------------------------------------------------


def table_shape(cell_text):
    """检查表格文本并返回 ``(text, 行数, 列数)``。

    ``cell_text`` 可以是二维列表、二维 NumPy 数组，
    也允许传入一维列表（按单列处理）。
    """

    text = np.asarray(cell_text, dtype=object)

    if text.ndim == 1:
        text = text.reshape(-1, 1)

    if text.ndim != 2:
        raise ValueError(
            "cell_text 必须是二维列表或二维数组，"
            f"当前维度为 {text.ndim}"
        )

    if text.size == 0:
        raise ValueError("cell_text 不能为空")

    return text, text.shape[0], text.shape[1]


def table_style_array(value, rows, columns, name):
    """把表格样式参数整理成 ``(rows, columns)`` 的二维数组。

    支持：

    * 标量 / 单个颜色值 -> 整张表统一使用
    * 按列给出（长度=列数） -> 逐列铺开
    * 按行给出（长度=行数） -> 逐行铺开
    * 完整二维数组 -> 原样使用
    """

    if value is None:
        return None

    array = np.asarray(value, dtype=object)

    if array.ndim == 0:
        return np.full((rows, columns), array.item(), dtype=object)

    if array.ndim == 1:
        if array.size == columns:
            return np.tile(array, (rows, 1))

        if array.size == rows:
            return np.tile(array.reshape(-1, 1), (1, columns))

        raise ValueError(
            f"{name} 是一维数组时长度必须等于行数({rows})"
            f"或列数({columns})，当前长度为{array.size}"
        )

    if array.ndim == 2:
        if array.shape != (rows, columns):
            raise ValueError(
                f"{name} 的形状应该是{(rows, columns)}，"
                f"当前为{array.shape}"
            )

        return array

    raise ValueError(f"{name} 的维度不能超过2")


def table_cell_keys(table, rows, columns):
    """列出表格里所有数据单元格（不含表头）的坐标键。"""

    keys = []

    for row in range(rows):
        for column in range(columns):
            if (row, column) in table.get_celld():
                keys.append((row, column))

    return keys


def compare(value, operator, reference):
    """比较两个数，供表格条件高亮使用。

    支持的操作符：``>``、``>=``、``<``、``<=``、``==``、``!=``
    """

    if operator == ">":
        return value > reference
    if operator == ">=":
        return value >= reference
    if operator == "<":
        return value < reference
    if operator == "<=":
        return value <= reference
    if operator == "==":
        return value == reference
    if operator == "!=":
        return value != reference

    raise ValueError(f"不支持的比较运算符：{operator}")


#: 表格条件高亮支持的比较运算符。
HIGHLIGHT_OPERATORS = (">", ">=", "<", "<=", "==", "!=")


def resolve_highlight(highlight, rows, columns):
    """把 ``highlight`` 参数解析成 ``(单元格集合, 条件字典)``。

    支持：

    * ``None`` -> 不高亮
    * ``(row, col)`` -> 单个单元格
    * ``[(0, 1), (2, 3)]`` -> 多个单元格
    * ``{">=": 100}`` -> 条件高亮（对数值单元格生效）
    """

    if highlight is None:
        return set(), None

    # 条件写法
    if isinstance(highlight, dict):
        allowed = set(HIGHLIGHT_OPERATORS)
        unknown = set(highlight) - allowed

        if unknown:
            raise ValueError(
                "highlight 条件只支持 "
                f"{sorted(allowed)}，当前多出：{sorted(unknown)}"
            )

        if len(highlight) != 1:
            raise ValueError(
                "highlight 条件字典只能写一个比较运算符"
            )

        operator = next(iter(highlight))

        return set(), {
            "op": operator,
            "value": highlight[operator],
        }

    # 单个单元格
    if (
        isinstance(highlight, (tuple, list))
        and len(highlight) == 2
        and all(isinstance(item, (int, np.integer)) for item in highlight)
    ):
        highlight = [tuple(int(item) for item in highlight)]

    if not isinstance(highlight, (list, tuple, set, np.ndarray)):
        raise TypeError(
            "highlight 必须是 None、(row, col)、"
            "单元格序列或条件字典，"
            f"当前为{type(highlight).__name__}"
        )

    cells = set()

    for item in highlight:
        if (
            not isinstance(item, (tuple, list, np.ndarray))
            or len(item) != 2
        ):
            raise ValueError(
                "highlight 里的每个元素都必须是 (row, col)，"
                f"当前为{item!r}"
            )

        row, column = int(item[0]), int(item[1])

        if not (0 <= row < rows and 0 <= column < columns):
            raise ValueError(
                f"高亮单元格({row}, {column})超出表格范围："
                f"行数{rows}、列数{columns}"
            )

        cells.add((row, column))

    return cells, None


# ----------------------------------------------------------------------
# 配置读取
# ----------------------------------------------------------------------


def is_nonempty(value):
    """判断配置值是否算作“已设置”。

    ``None``、空字符串、空字典、空列表、空元组都算作未设置。
    """

    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, (dict, list, tuple, set)):
        return len(value) > 0

    return True


def first_nonempty(configs, key, default=None):
    """返回当前子图中第一个非空配置值。

    空字符串、``None``、空字典都会被跳过；所有配置都为空时返回 ``default``。
    """

    for config in configs:
        value = config.get(key)

        if is_nonempty(value):
            return value

    return default


def first_defined(configs, key, default=None):
    """返回当前子图中第一个“显式写出”的配置值。

    只要配置里出现了这个键，就返回它的值（空字符串也算显式写出），
    所有配置都没有这个键时才返回 ``default``。

    因此「设置了空字符串」和「没有设置」会被区分开。
    例如饼图会把 ``xlabel`` 设置成空字符串，用来表示不要显示坐标轴标题。
    """

    for config in configs:
        if key in config:
            return config[key]

    return default


# ----------------------------------------------------------------------
# 格式化
# ----------------------------------------------------------------------


def format_value(value, fmt):
    """用 ``'.2f'`` 或 ``'%.2f'`` 两种格式串格式化数值标签。"""

    try:
        if "%" in str(fmt):
            return str(fmt) % value
        return format(value, str(fmt))
    except (TypeError, ValueError):
        return str(value)


__all__ = [
    "HIGHLIGHT_OPERATORS",
    "as_1d_array",
    "check_same_length",
    "broadcast_to_length",
    "mesh_coordinates",
    "field_coordinates",
    "field_coordinates_3d",
    "field_norm",
    "shrink_field",
    "integrate_streamline",
    "table_shape",
    "table_style_array",
    "table_cell_keys",
    "compare",
    "resolve_highlight",
    "is_nonempty",
    "first_nonempty",
    "first_defined",
    "format_value",
]
