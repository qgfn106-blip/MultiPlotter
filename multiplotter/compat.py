# -*- coding: utf-8 -*-
"""Matplotlib 版本兼容层。

把「不同 Matplotlib 版本支持的参数不一样」这件事收敛到这一个模块，
其它模块不要自己写 ``try/except TypeError`` 去猜版本。

公开 API
--------
``mpl_version()``            当前 Matplotlib 版本元组
``mpl_at_least(major, minor)``
``supports_parameter(func, name)``
``filter_kwargs(func, kwargs)``
``call_with_supported(func, *args, **kwargs)``
"""

from __future__ import annotations

import inspect
import warnings

import matplotlib

#: 本包声明支持的最低 Matplotlib 版本。
MATPLOTLIB_MIN = (3, 5)

#: 本包在这些版本上做过测试。
MATPLOTLIB_TESTED = ((3, 5), (3, 6), (3, 7), (3, 8), (3, 9), (3, 10))


def mpl_version():
    """返回 ``(major, minor, micro)`` 形式的 Matplotlib 版本元组。

    非数字后缀（例如 ``3.10.0rc1``）会被安全忽略。
    """

    parts = []

    for chunk in str(matplotlib.__version__).split(".")[:3]:
        digits = ""

        for char in chunk:
            if char.isdigit():
                digits += char
            else:
                break

        parts.append(int(digits) if digits else 0)

    while len(parts) < 3:
        parts.append(0)

    return tuple(parts)


def mpl_at_least(major, minor):
    """当前版本是否不低于 ``major.minor``。"""

    return mpl_version()[:2] >= (int(major), int(minor))


def supports_parameter(func, name):
    """判断 ``func`` 是否接受名为 ``name`` 的关键字参数。

    同时认两种情况：

    * 显式写在签名里的参数；
    * 签名里有 ``**kwargs``（此时一律认为接受，因为无法静态判断）。
    """

    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return True

    parameters = signature.parameters

    if name in parameters:
        return True

    return any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )


def filter_kwargs(func, kwargs):
    """按 ``func`` 的真实签名过滤 ``kwargs``。

    返回 ``(可用参数, 被丢弃的键名列表)``。
    只丢弃「签名里没有、也没有 **kwargs」的键，避免把
    ``Axes.set() got an unexpected keyword argument`` 这类错误抛给用户。
    """

    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return dict(kwargs), []

    accepts_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )

    if accepts_kwargs:
        return dict(kwargs), []

    accepted = {
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    }

    kept = {key: value for key, value in kwargs.items() if key in accepted}
    dropped = sorted(set(kwargs) - set(kept))

    return kept, dropped


def call_with_supported(func, *args, **kwargs):
    """调用 ``func``，自动丢弃它不支持的参数。

    返回 ``(结果, 被丢弃的键名列表)``。
    用于 ``view_init(roll=...)``、``streamplot(broken_streamlines=...)``
    这类「新版本才有」的参数。
    """

    kept, dropped = filter_kwargs(func, kwargs)

    return func(*args, **kept), dropped


def warn_version(message, stacklevel=3):
    """统一的版本兼容提示（只警告，不抛异常）。"""

    warnings.warn(message, RuntimeWarning, stacklevel=stacklevel)


__all__ = [
    "MATPLOTLIB_MIN",
    "MATPLOTLIB_TESTED",
    "mpl_version",
    "mpl_at_least",
    "supports_parameter",
    "filter_kwargs",
    "call_with_supported",
    "warn_version",
]
