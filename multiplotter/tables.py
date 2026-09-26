# -*- coding: utf-8 -*-
"""二维表格图层：``add_table`` 与 ``draw_table``。

表格是本项目里参数最多的一个图层，所以单独成模块。
它同时负责：

* 数据校验（文本形状、行列标题、列宽、``bbox``）；
* 样式规格化（底色/文字颜色支持标量、按行、按列、完整二维数组）；
* 单元格高亮（显式单元格 + 条件高亮）；
* 动画复用（同一个 ``Axes`` 上重复画表格时复用同一个 ``Table``，
  这样 ``set_text()`` 才能原地更新）。
"""

from __future__ import annotations

import numpy as np

from .validation import (
    compare,
    format_value,
    resolve_highlight,
    table_shape,
    table_style_array,
)

#: 表格对象在 ``Axes`` 上的缓存属性名。
TABLE_CACHE_ATTR = "_multiplotter_table_cache"


def get_table(ax, config):
    """取得（必要时新建）表格对象。

    同一个坐标轴重复画表格时复用同一个 ``Table``，
    这样动画里才能用 ``set_text()`` 原地更新单元格内容。
    """

    cache = getattr(ax, TABLE_CACHE_ATTR, None)

    if cache is None:
        cache = {}
        setattr(ax, TABLE_CACHE_ATTR, cache)

    key = config["subplot"]

    if key in cache:
        return cache[key]

    table = ax.table(
        cellText=config["cell_text"],
        rowLabels=config["row_labels"],
        colLabels=config["col_labels"],
        loc=config["loc"],
        cellLoc=config["cell_align"],
        bbox=config["bbox"],
        **config["table_kwargs"],
    )

    # 单元格字体
    for cell in table.get_celld().values():
        cell.set_fontsize(config["cell_fontsize"])

    cache[key] = table

    return table


def update_table(ax, config):
    """更新表格文本，供动画逐帧调用。

    文本来源优先取 ``config["frame_text"]``，
    没有时退回 ``config["cell_text"]``。
    """

    table = get_table(ax, config)
    rows = config["n_rows"]
    columns = config["n_cols"]

    frame_text = config.get("frame_text")

    if frame_text is None:
        text = np.asarray(config["cell_text"], dtype=object)
    else:
        text = np.asarray(frame_text, dtype=object)

    if text.shape != (rows, columns):
        raise ValueError(
            f"frame_text 的形状应该是{(rows, columns)}，"
            f"当前为{text.shape}"
        )

    for row in range(rows):
        for column in range(columns):
            cell = table.get_celld().get((row, column))

            if cell is not None:
                cell.get_text().set_text(str(text[row, column]))

    return table


def _apply_borders(table, config):
    """统一边框颜色与线宽。"""

    for cell in table.get_celld().values():
        cell.set_edgecolor(config["edge_color"])
        cell.set_linewidth(config["edge_width"])


def _apply_cell_colors(table, config):
    """应用单元格底色与文字颜色（支持标量 / 按行 / 按列 / 二维数组）。"""

    background = config["background_color"]
    text_colors = config["text_color"]

    if background is None and text_colors is None:
        return

    for row in range(config["n_rows"]):
        for column in range(config["n_cols"]):
            cell = table.get_celld().get((row, column))

            if cell is None:
                continue

            if background is not None:
                cell.set_facecolor(background[row, column])

            if text_colors is not None:
                cell.get_text().set_color(text_colors[row, column])


def _apply_zebra(table, config):
    """应用斑马纹。

    ``zebra_color`` 可以是颜色（对奇数行生效），
    也可以是 ``{"rows": [...], "color": "..."}`` 指定行号。
    """

    zebra_color = config["zebra_color"]
    zebra_rows = None
    zebra_fill = None

    if isinstance(zebra_color, dict):
        zebra_rows = zebra_color.get("rows")
        zebra_fill = zebra_color.get("color")
    elif zebra_color is not None:
        zebra_fill = zebra_color
        zebra_rows = list(range(1, config["n_rows"], 2))

    if zebra_fill is None or not zebra_rows:
        return

    for row in zebra_rows:
        row = int(row)

        if not 0 <= row < config["n_rows"]:
            continue

        for column in range(config["n_cols"]):
            cell = table.get_celld().get((row, column))

            if cell is not None:
                cell.set_facecolor(zebra_fill)


def _apply_headers(table, config):
    """应用列标题与行标题的配色与加粗。"""

    for column in range(config["n_cols"]):
        cell = table.get_celld().get((-1, column))

        if cell is None:
            continue

        cell.set_facecolor(config["header_background"])
        cell.set_text_props(
            color=config["header_text_color"],
            weight="bold" if config["header_bold"] else "normal",
            fontsize=config["header_fontsize"],
        )

    for row in range(config["n_rows"]):
        cell = table.get_celld().get((row, -1))

        if cell is None:
            continue

        cell.set_facecolor(config["row_label_background"])
        cell.set_text_props(
            color=config["row_label_text_color"],
            weight="bold" if config["row_label_bold"] else "normal",
        )


def _apply_highlight(table, config):
    """应用单元格高亮：显式指定的单元格 + 满足条件的数值单元格。"""

    highlight_cells = set(config["highlight_cells"])
    condition = config["highlight_condition"]

    if condition is not None:
        for row in range(config["n_rows"]):
            for column in range(config["n_cols"]):
                try:
                    number = float(config["cell_text"][row, column])
                except (TypeError, ValueError):
                    continue

                if compare(number, condition["op"], condition["value"]):
                    highlight_cells.add((row, column))

    for cell_key in highlight_cells:
        cell = table.get_celld().get(cell_key)

        if cell is None:
            continue

        cell.set_facecolor(config["highlight_color"])
        cell.set_text_props(
            color=config["highlight_text_color"],
            weight="bold" if config["highlight_bold"] else "normal",
        )


def _apply_axis_visibility(ax, config):
    """表格不需要坐标轴。"""

    if config["axis_off"]:
        ax.set_axis_off()
    else:
        ax.set_xticks([])
        ax.set_yticks([])


def draw_table(ax, config):
    """绘制二维表格（样式 -> 表头 -> 高亮 -> 坐标轴）。"""

    table = get_table(ax, config)

    _apply_borders(table, config)
    _apply_cell_colors(table, config)
    _apply_zebra(table, config)
    _apply_headers(table, config)
    _apply_highlight(table, config)
    _apply_axis_visibility(ax, config)


#: 表格 ``kind`` -> 绘制处理器。
DRAW_HANDLERS = {"table": draw_table}


# ----------------------------------------------------------------------
# 添加图层（Mixin）
# ----------------------------------------------------------------------


class TableLayersMixin:
    """表格图层的 ``add_table``。"""

    def add_table(
        self,
        cell_text,
        subplot=0,
        title="",
        xlabel="",
        ylabel="",
        row_labels=None,
        col_labels=None,
        loc="center",
        bbox=None,
        cell_align="center",
        cell_fontsize=10,
        cell_height=0.09,
        col_width=None,
        background_color=None,
        text_color=None,
        edge_color="#90A4AE",
        edge_width=0.8,
        header_background="#1976D2",
        header_text_color="#FFFFFF",
        header_fontsize=None,
        header_bold=True,
        row_label_background="#ECEFF1",
        row_label_text_color="#263238",
        row_label_bold=True,
        zebra_color=None,
        highlight=None,
        highlight_color="#FFE082",
        highlight_text_color="#263238",
        highlight_bold=True,
        axis_off=True,
        show_values=False,
        value_format=None,
        auto_edges=True,
        view=None,
        **kwargs,
    ):
        """添加二维表格，支持较细的美化设置。

        参数说明（按「数据 -> 布局 -> 配色 -> 强调」分组）：

        **数据**

        ``cell_text``
            表格内容。可以是二维列表/数组，也可以传一维列表（按单列处理）。
        ``row_labels`` / ``col_labels``
            行/列标题，长度必须等于行数/列数；``None`` 时自动编号 ``1..n``。
        ``show_values`` / ``value_format``
            为 ``True`` 时把单元格里的数字按 ``value_format`` 重新格式化。

        **布局**

        ``loc``
            表格在坐标轴中的位置：``"center"`` / ``"upper left"`` 等。
        ``bbox``
            用 ``[x, y, width, height]`` 精确指定位置（坐标轴坐标 0~1），
            给了 ``bbox`` 时 ``loc`` 不再起作用。
        ``cell_align``
            单元格文字对齐：``left`` / ``center`` / ``right``。
        ``cell_fontsize`` / ``header_fontsize``
            单元格与表头字号。
        ``cell_height`` / ``col_width`` / ``auto_edges``
            行高、列宽比例、是否使用紧凑边框。

        **配色**

        ``background_color`` / ``text_color``
            单元格底色与文字颜色，可以传标量、按列、按行或完整二维数组。
        ``edge_color`` / ``edge_width``
            边框颜色与线宽。
        ``header_*`` / ``row_label_*``
            表头与行标题配色、加粗。
        ``zebra_color``
            斑马纹颜色；也可以给 ``{"rows": [...], "color": "..."}``。

        **单元格强调**

        ``highlight``
            需要高亮的单元格，支持三种写法：

            * ``(row, col)`` —— 单个单元格
            * ``[(0, 1), (2, 3)]`` —— 多个单元格
            * ``{">=": 100}`` —— 按条件（对数值单元格生效）

            条件字典支持 ``>``、``>=``、``<``、``<=``、``==``、``!=``。
        ``highlight_color`` / ``highlight_text_color`` / ``highlight_bold``
            高亮单元格的底色、文字颜色与加粗。

        **其他**

        ``axis_off``
            ``True`` 时隐藏坐标轴（表格通常不需要坐标轴）。
        ``view``
            与其它图层一致的坐标轴设置。
        """

        text, rows, columns = table_shape(cell_text)

        # ---------- 行列标题 ----------
        if row_labels is None:
            row_labels = [f"行{i + 1}" for i in range(rows)]
        else:
            row_labels = list(row_labels)

            if len(row_labels) != rows:
                raise ValueError(
                    f"row_labels 长度必须等于行数({rows})，"
                    f"当前为{len(row_labels)}"
                )

        if col_labels is None:
            col_labels = [f"列{i + 1}" for i in range(columns)]
        else:
            col_labels = list(col_labels)

            if len(col_labels) != columns:
                raise ValueError(
                    f"col_labels 长度必须等于列数({columns})，"
                    f"当前为{len(col_labels)}"
                )

        # ---------- 单元格文字 ----------
        frame_text = None

        if value_format is not None:
            formatted = np.empty((rows, columns), dtype=object)

            for row in range(rows):
                for column in range(columns):
                    value = text[row, column]

                    try:
                        number = float(value)
                    except (TypeError, ValueError):
                        formatted[row, column] = str(value)
                    else:
                        formatted[row, column] = format_value(
                            number, value_format
                        )

            frame_text = formatted

        # ---------- 布局 ----------
        if cell_height is not None and float(cell_height) <= 0:
            raise ValueError(
                f"cell_height 必须大于0，当前为{cell_height}"
            )

        if col_width is not None:
            widths = list(col_width)

            if len(widths) != columns:
                raise ValueError(
                    f"col_width 长度必须等于列数({columns})，"
                    f"当前为{len(widths)}"
                )

            if any(float(width) <= 0 for width in widths):
                raise ValueError("col_width 里的每个宽度都必须大于0")

            # matplotlib 用相对比例，这里归一化到总和为列数，便于理解
            total = sum(float(width) for width in widths)
            widths = [float(width) * columns / total for width in widths]
        else:
            widths = [1.0] * columns

        if bbox is not None:
            bbox = [float(item) for item in bbox]

            if len(bbox) != 4:
                raise ValueError(
                    "bbox 必须是 [x, y, width, height] 四个数，"
                    f"当前为{bbox}"
                )

            if bbox[2] <= 0 or bbox[3] <= 0:
                raise ValueError("bbox 的宽度和高度必须大于0")

        # ---------- 配色 / 强调 ----------
        background_array = table_style_array(
            background_color, rows, columns, "background_color"
        )
        text_array = table_style_array(
            text_color, rows, columns, "text_color"
        )
        highlight_cells, highlight_condition = resolve_highlight(
            highlight, rows, columns
        )

        table_kwargs = dict(kwargs)

        if auto_edges:
            table_kwargs.setdefault("edges", "closed")

        return self._register_layer(
            "table",
            dimension=2,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            label=None,
            legend=False,
            legend_kwargs={},
            axis="",
            view=view,
            kwargs={},
            x=None,
            y=None,
            z=None,
            data=text,
            cell_text=text,
            frame_text=frame_text,
            axis_off=axis_off,
            n_rows=rows,
            n_cols=columns,
            row_labels=row_labels,
            col_labels=col_labels,
            loc=loc,
            bbox=bbox,
            cell_align=cell_align,
            cell_fontsize=cell_fontsize,
            cell_height=cell_height,
            col_widths=widths,
            background_color=background_array,
            text_color=text_array,
            edge_color=edge_color,
            edge_width=edge_width,
            header_background=header_background,
            header_text_color=header_text_color,
            header_fontsize=header_fontsize or cell_fontsize,
            header_bold=header_bold,
            row_label_background=row_label_background,
            row_label_text_color=row_label_text_color,
            row_label_bold=row_label_bold,
            zebra_color=zebra_color,
            highlight_cells=highlight_cells,
            highlight_condition=highlight_condition,
            highlight_color=highlight_color,
            highlight_text_color=highlight_text_color,
            highlight_bold=highlight_bold,
            show_values=show_values,
            value_format=value_format,
            auto_edges=auto_edges,
            table_kwargs=table_kwargs,
        )


__all__ = [
    "TableLayersMixin",
    "DRAW_HANDLERS",
    "TABLE_CACHE_ATTR",
    "get_table",
    "update_table",
    "draw_table",
]
