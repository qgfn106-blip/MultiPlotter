# -*- coding: utf-8 -*-
"""示例脚本的公共工具：路径设置与输出目录。

这些脚本设计成可以**在包根目录直接运行**：

    python examples/01_quickstart.py

所以每个脚本都先调用 :func:`prepare`，它会把包根目录加入 ``sys.path``，
并返回 ``examples/output/`` 目录（不存在时自动创建）。
"""

import os
import sys

#: 包根目录（本文件在 examples/ 下）。
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: 示例输出目录。
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def prepare(headless=True):
    """把包根目录加入 ``sys.path``，返回输出目录路径。

    ``headless=True`` 时使用 Agg 后端，脚本不会弹窗，适合批量运行。
    """

    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    if headless:
        import matplotlib

        matplotlib.use("Agg")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    return OUTPUT_DIR


def output(name):
    """返回输出目录下某个文件的完整路径。"""

    return os.path.join(OUTPUT_DIR, name)
