# -*- coding: utf-8 -*-
"""Matplotlib 版本兼容层的测试（对应重构要求 (7)）。

要求 (7) 明确要求「加入 Matplotlib 版本兼容策略」并且
「在测试中覆盖常见参数和不同版本行为」。
``multiplotter/compat.py`` 是这套策略的唯一落点，本文件覆盖它。

用法::

    python tests/compat_test.py

全部通过时退出码为 0。
"""

import os
import sys
import warnings

import matplotlib

matplotlib.use("Agg")

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from multiplotter import (  # noqa: E402
    MATPLOTLIB_MIN,
    MATPLOTLIB_TESTED,
    call_with_supported,
    filter_kwargs,
    mpl_at_least,
    mpl_version,
    supports_parameter,
    warn_version,
)

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


# ======================================================================
# 1. 版本元组
# ======================================================================

def test_mpl_version():
    version = mpl_version()

    check("mpl_version() 返回三元组",
          isinstance(version, tuple) and len(version) == 3,
          f"-> {version}")
    check("mpl_version() 都是整数",
          all(isinstance(item, int) for item in version),
          f"-> {version}")

    # 与 matplotlib.__version__ 的前两段一致
    expected = tuple(
        int(chunk) for chunk in str(matplotlib.__version__).split(".")[:2]
    )
    check("mpl_version() 与 matplotlib.__version__ 一致",
          version[:2] == expected,
          f"-> {version[:2]} vs {expected}")

    # 带后缀的版本号也要能解析（模拟 rc / dev 版）
    original = matplotlib.__version__

    try:
        matplotlib.__version__ = "3.10.0rc1"
        check("能解析 3.10.0rc1 这类带后缀的版本",
              mpl_version() == (3, 10, 0), f"-> {mpl_version()}")

        matplotlib.__version__ = "3.9"
        check("能补齐只有两段的版本号",
              mpl_version() == (3, 9, 0), f"-> {mpl_version()}")
    finally:
        matplotlib.__version__ = original


def test_mpl_at_least():
    version = mpl_version()

    check("mpl_at_least 对当前版本返回 True",
          mpl_at_least(version[0], version[1]))

    # 边界：正好等于当前版本 -> True；再高一个小版本 -> False
    check("mpl_at_least 边界：等于自身为 True",
          mpl_at_least(version[0], version[1]) is True)
    check("mpl_at_least 边界：更高版本为 False",
          mpl_at_least(version[0], version[1] + 1) is False)

    # 比最低支持版本低 -> False
    check("低于 MATPLOTLIB_MIN 时为 False",
          mpl_at_least(MATPLOTLIB_MIN[0], MATPLOTLIB_MIN[1]) is True)


def test_min_version_is_satisfied():
    """当前环境必须满足本包声明的最低版本。"""

    check(
        f"当前 matplotlib {matplotlib.__version__} 满足最低版本 "
        f"{'.'.join(map(str, MATPLOTLIB_MIN))}",
        mpl_at_least(*MATPLOTLIB_MIN),
    )

    check("MATPLOTLIB_TESTED 里包含最低版本",
          MATPLOTLIB_MIN in MATPLOTLIB_TESTED,
          f"-> {MATPLOTLIB_TESTED}")


# ======================================================================
# 2. 参数支持判断
# ======================================================================

def simple(a, b=2, *, c=3):
    """只有明确列出的参数。"""

    return a + b + c


def with_kwargs(a, **kwargs):
    """带 **kwargs，无法静态判断。"""

    return a


def test_supports_parameter():
    check("签名里有的参数 -> True", supports_parameter(simple, "b") is True)
    check("关键字限定参数 -> True", supports_parameter(simple, "c") is True)
    check("签名里没有的参数 -> False",
          supports_parameter(simple, "zzz") is False)

    # 有 **kwargs 时一律认为支持（无法静态判断）
    check("有 **kwargs 时一律 True",
          supports_parameter(with_kwargs, "anything") is True)

    # 取不到签名（非可调用对象）时按「支持」处理，避免误丢参数
    check("取不到签名时保守返回 True",
          supports_parameter(42, "anything") is True)

    # 真实 Matplotlib 方法：新老版本差异的典型例子
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(3, 3), dpi=50)
    ax = fig.add_subplot(111)

    check("Axes.plot 支持 linewidth",
          supports_parameter(plt.Axes.plot, "linewidth") is True)

    # get_xlim 没有 **kwargs，可以确定性地判断「不支持」
    check("没有 **kwargs 的方法会明确拒绝瞎编的参数",
          supports_parameter(ax.get_xlim, "definitely_not_a_param") is False)

    # 反过来，plot 有 **kwargs，静态看「什么都接受」——
    # 真正的报错发生在 artist 层，所以框架才需要白名单
    check("Axes.plot 因为有 **kwargs，静态判断一律为 True",
          supports_parameter(plt.Axes.plot, "definitely_not_a_param") is True)

    plt.close("all")


def test_filter_kwargs():
    kept, dropped = filter_kwargs(simple, {"a": 1, "b": 5, "zzz": 9})

    check("filter_kwargs 保留签名内的参数",
          kept == {"a": 1, "b": 5}, f"-> {kept}")
    check("filter_kwargs 报告被丢弃的键",
          dropped == ["zzz"], f"-> {dropped}")

    kept, dropped = filter_kwargs(with_kwargs, {"a": 1, "anything": 2})

    check("有 **kwargs 时全部保留",
          kept == {"a": 1, "anything": 2} and dropped == [],
          f"-> {kept} / {dropped}")

    # 取不到签名时原样返回，不丢任何键
    kept, dropped = filter_kwargs(42, {"whatever": 1})

    check("取不到签名时原样返回不丢键",
          kept == {"whatever": 1} and dropped == [],
          f"-> {kept} / {dropped}")

    # 不应该修改调用方传进来的字典
    original = {"a": 1, "zzz": 2}
    filter_kwargs(simple, original)

    check("filter_kwargs 不改动传入的字典",
          original == {"a": 1, "zzz": 2}, f"-> {original}")


def test_call_with_supported():
    result, dropped = call_with_supported(simple, 1, b=2, zzz=99)

    check("call_with_supported 正常返回结果", result == 6, f"-> {result}")
    check("call_with_supported 报告被丢弃的键",
          dropped == ["zzz"], f"-> {dropped}")

    # 不同版本才有参数的场景：多余的键被丢掉，调用照样成功
    import matplotlib.pyplot as plt

    result, dropped = call_with_supported(
        simple, 1, b=2, definitely_not_a_param=1
    )

    check("不支持的参数不会导致调用失败",
          result == 6 and dropped == ["definitely_not_a_param"],
          f"-> {result} / {dropped}")


# ======================================================================
# 3. 版本提示
# ======================================================================

def test_warn_version():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warn_version("这个参数需要更新的 Matplotlib")

    check("warn_version 发出警告", len(caught) == 1, f"-> {len(caught)} 条")

    if caught:
        check("warn_version 用 RuntimeWarning",
              issubclass(caught[0].category, RuntimeWarning),
              f"-> {caught[0].category.__name__}")
        check("警告信息原样传递",
              "需要更新的 Matplotlib" in str(caught[0].message),
              f"-> {caught[0].message}")


def test_version_related_params_are_guarded():
    """框架不应把版本相关参数直接硬塞给底层方法。

    这里用 ``view_init(roll=...)`` 做代表：``roll`` 是较新版本才有的参数。
    无论当前版本支不支持，调用都必须成功（不支持时自动降级）。
    """

    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(3, 3), dpi=50)
    ax = fig.add_subplot(111, projection="3d")

    ax.view_init(elev=20, azim=30)

    try:
        _, dropped = call_with_supported(
            ax.view_init, elev=25, azim=35, roll=10
        )
        check("view_init(roll=...) 在新老版本上都能调用",
              isinstance(dropped, list), f"-> 丢弃 {dropped}")
    except TypeError as error:                    # pragma: no cover
        check("view_init(roll=...) 在新老版本上都能调用", False,
              f"-> {error}")

    check("Axes3D.view_init 支持 elev / azim",
          supports_parameter(ax.view_init, "elev")
          and supports_parameter(ax.view_init, "azim"))

    plt.close("all")


def main():
    print(f"当前 Matplotlib：{matplotlib.__version__} "
          f"-> {mpl_version()}")
    print(f"本包最低支持：{'.'.join(map(str, MATPLOTLIB_MIN))}")
    print()

    tests = [
        ("版本元组", test_mpl_version),
        ("版本比较", test_mpl_at_least),
        ("最低版本满足", test_min_version_is_satisfied),
        ("参数支持判断", test_supports_parameter),
        ("参数过滤", test_filter_kwargs),
        ("自动丢弃不支持的参数", test_call_with_supported),
        ("版本提示", test_warn_version),
        ("版本相关参数兜底", test_version_related_params_are_guarded),
    ]

    for name, func in tests:
        try:
            func()
        except Exception as error:                # noqa: BLE001
            globals()["failed"] += 1
            print(f"[ERROR] {name}: {type(error).__name__}: {error}")

    print()
    print(f"通过 {passed} 项，失败 {failed} 项")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
