# -*- coding: utf-8 -*-
"""默认值可达性测试：确保 ``KIND_DEFAULTS`` 里的预设真的能生效。

背景
----

``init()`` 的每个 kind 都有一份预设（``KIND_DEFAULTS``）。这些预设会作为
参数交给对应的 ``add_*`` 方法，而 ``PlotBuilder.filter_call()`` 只允许
三类键通过：

① 目标方法签名里存在的参数；
② ``PASSTHROUGH_KEYS``（通用 artist 样式）；
③ ``PASSTHROUGH_BY_KIND[kind]``（该 kind 专属）。

如果某个预设键三类都不属于，它就会被过滤，预设写了等于没写。
本测试要求内置预设全部可达，避免默认样式在运行时悄悄失效；
新增 kind 时也能立刻发现「预设键漏登记」。

"""

import inspect
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multiplotter import INIT_ONLY_KINDS, MultiPlotter  # noqa: E402

def reachable_keys(kind, method_name, defaults):
    """返回 ``defaults`` 里能真正到达目标方法的键。"""

    method = getattr(MultiPlotter, method_name)

    signature = inspect.signature(method)
    allowed = {
        name
        for name, parameter in signature.parameters.items()
        if name != "self"
        and parameter.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    }

    passthrough = set(MultiPlotter.PASSTHROUGH_KEYS)
    passthrough |= set(MultiPlotter.PASSTHROUGH_BY_KIND.get(kind, ()))

    return {key for key in defaults if key in allowed or key in passthrough}


def test_defaults_are_reachable():
    """每个 kind 的预设键要么能生效，要么在已知清单里。"""

    failures = []

    for kind, (method_name, defaults) in sorted(
        MultiPlotter.KIND_DEFAULTS.items()
    ):
        if not hasattr(MultiPlotter, method_name):
            failures.append(f"{kind}: 目标方法 {method_name} 不存在")
            continue

        unreachable = set(defaults) - reachable_keys(
            kind, method_name, defaults
        )
        if unreachable:
            failures.append(
                f"{kind}: 预设键 {sorted(unreachable)} 到不了 {method_name}()，"
                "请把它们加进 PASSTHROUGH_BY_KIND（注册时用 passthrough=）"
                "或写进方法签名"
            )

    assert not failures, "预设可达性检查失败：\n  " + "\n  ".join(failures)


def test_passthrough_entries_are_strings():
    """白名单里的键必须都是字符串，避免注册时写错类型。"""

    for kind, keys in MultiPlotter.PASSTHROUGH_BY_KIND.items():
        assert isinstance(keys, (set, frozenset, list, tuple)), (
            f"{kind} 的 passthrough 必须是序列，当前为 {type(keys).__name__}"
        )

        for key in keys:
            assert isinstance(key, str), (
                f"{kind} 的 passthrough 里有非字符串键：{key!r}"
            )


def collect_snapshot():
    """把每个 kind 的默认值契约整理成可比较的普通数据结构。

    只取「结构化」的部分：kind、维度、目标方法、预设键值、透传键。
    ``draw_handler`` 是函数对象没法比较，所以只记录它是否存在。
    """

    snapshot = {}

    for kind in sorted(MultiPlotter.LAYER_SPECS):
        spec = MultiPlotter.get_layer_spec(kind)
        method, defaults = MultiPlotter.kind_presets(kind)
        passthrough = MultiPlotter.PASSTHROUGH_BY_KIND.get(kind)

        snapshot[kind] = {
            "dimension": int(spec.dimension),
            "add_method": spec.add_method,
            "aliases": sorted(spec.aliases),
            "animatable": bool(spec.animatable),
            "init_only": bool(spec.init_only),
            "has_draw_handler": spec.draw_handler is not None,
            # 值统一转成可 JSON 序列化的形式
            "presets": {
                key: _jsonable(value)
                for key, value in sorted(defaults.items())
            },
            "passthrough": sorted(passthrough) if passthrough else [],
        }

    return snapshot


def _jsonable(value):
    """把预设值转成能稳定比较的形式（dict 排序、tuple 变 list）。"""

    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in sorted(value.items())}

    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]

    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(item) for item in value)

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    # 其它对象（例如某个 LightSource 配置）只记录类型名，保证可比较
    return f"<{type(value).__name__}>"


def test_defaults_match_snapshot():
    """需求 (8)：为每个 kind 增加默认值快照测试。

    与 ``tests/defaults_snapshot.json`` 比对，任何预设 / 维度 / 透传键的
    改动都会让这个用例失败，从而逼着改动者同步更新文档与测试。
    """

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "defaults_snapshot.json")

    assert os.path.isfile(path), (
        f"缺少快照文件 {path}；"
        "运行 python tests/defaults_test.py --update-snapshot 生成"
    )

    with open(path, encoding="utf-8") as handle:
        expected = json.load(handle)

    actual = collect_snapshot()

    if actual != expected:
        # 逐 kind 找出差异，报错信息要能直接定位
        problems = []
        all_kinds = sorted(set(actual) | set(expected))

        for kind in all_kinds:
            before = expected.get(kind)
            now = actual.get(kind)

            if before is None:
                problems.append(f"{kind}: 新增了 kind（快照里没有）")
                continue

            if now is None:
                problems.append(f"{kind}: kind 被删除了")
                continue

            for field in sorted(set(before) | set(now)):
                if before.get(field) != now.get(field):
                    problems.append(
                        f"{kind}.{field}:\n"
                        f"      快照: {before.get(field)}\n"
                        f"      当前: {now.get(field)}"
                    )

        raise AssertionError(
            "默认值契约与快照不一致（改了默认值就要同步更新文档与快照）：\n  "
            + "\n  ".join(problems)
            + "\n\n确认改动无误后执行："
            "\n  python tests/defaults_test.py --update-snapshot"
        )


def test_every_kind_has_a_spec():
    """每个 kind 都要有契约，且契约自洽。

    ``init()`` 专有的聚合 kind（如 ``correlation``）没有自己的绘制处理器，
    它们靠 ``init_only`` 标记区分。
    """

    for kind in MultiPlotter.KIND_DEFAULTS:
        spec = MultiPlotter.get_layer_spec(kind)
        spec.validate()
        assert spec.dimension in (2, 3)

        if spec.init_only:
            assert spec.draw_handler is None, (
                f"{kind} 标了 init_only，不应该有绘制处理器"
            )
            assert spec.kind in INIT_ONLY_KINDS, (
                f"{kind} 的 init_only=True，但没有登记进 INIT_ONLY_KINDS"
            )
        else:
            assert callable(spec.draw_handler), (
                f"{kind} 不是 init_only，但缺少绘制处理器"
            )

    # 反向检查：INIT_ONLY_KINDS 里的每个 kind 都要真的标记
    for kind in INIT_ONLY_KINDS:
        assert kind in MultiPlotter.LAYER_SPECS, (
            f"INIT_ONLY_KINDS 里的 {kind} 没有对应的 LayerSpec"
        )
        assert MultiPlotter.LAYER_SPECS[kind].init_only


def test_documented_presets_match_code():
    """抽查几个文档里重点写过的预设，避免文档与代码脱节。"""

    method, defaults = MultiPlotter.kind_presets("surface")
    assert method == "add_surface"
    assert defaults["light_enhance"] is not None
    assert defaults["colorbar"] is True

    method, defaults = MultiPlotter.kind_presets("bar")
    assert method == "add_plot"
    assert defaults["show_values"] is True

    method, defaults = MultiPlotter.kind_presets("table")
    assert method == "add_table"


def test_registration_keeps_every_view_in_sync():
    """``register_layer()`` 之后，三方注册表必须一致。

    注册表在三个地方被引用：

    * ``MultiPlotter.X``（类属性，库内部用）；
    * ``multiplotter.registries.X``（模块级常量）；
    * ``multiplotter.X``（包的 re-export，``from multiplotter import ...``）。

    如果注册时用 ``cls.X = dict(cls.X)`` 重新绑定，后两者会停留在旧对象上，
    于是用户 ``from multiplotter import DRAW_REGISTRY`` 之后再注册图层，
    看到的还是注册前的表 —— 与「单一注册入口」的承诺矛盾。

    测试里用一个临时 kind，最后无论成败都清理掉，避免污染其它测试。
    """

    import multiplotter
    import multiplotter.registries as reg

    kind = "_sync_probe"

    #: 就地更新的字典：注册后直接 pop 即可还原。
    MUTATED = (
        "DRAW_REGISTRY",
        "LAYER_SPECS",
        "KIND_DEFAULTS",
        "ADD_DISPATCH",
        "PASSTHROUGH_BY_KIND",
    )

    #: 需要三方同步的不可变派生量。
    SYNCED = ("SUPPORTED_2D_KINDS", "SUPPORTED_3D_KINDS", "SUPPORTED_KINDS")

    def handler(ax, config):        # pragma: no cover - 只注册不绘制
        return None

    original_sizes = {
        name: len(getattr(MultiPlotter, name)) for name in MUTATED
    }
    original_synced = {
        name: getattr(MultiPlotter, name) for name in SYNCED
    }

    assert kind not in MultiPlotter.LAYER_SPECS, "探针 kind 残留，上次没清理"

    MultiPlotter.register_layer(
        kind=kind,
        dimension=3,
        add_method="add_sync_probe",
        draw_handler=handler,
        defaults={"linewidth": 3.0},
        passthrough={"probe_key"},
    )

    try:
        # 探针注册为 3D，所以它在除 SUPPORTED_2D_KINDS 之外的每个表里都该出现
        present = [
            name for name in MUTATED + SYNCED
            if name != "SUPPORTED_2D_KINDS"
        ]

        for name in present:
            assert kind in getattr(MultiPlotter, name), (
                f"{name} 没更新到类属性"
            )
            assert kind in getattr(reg, name), (
                f"{name} 没同步到 multiplotter.registries"
            )
            assert kind in getattr(multiplotter, name), (
                f"{name} 没同步到 multiplotter 包（from-import 会拿到旧值）"
            )

        # 注册为 3D，三方都不该把它列进 2D
        for module in (MultiPlotter, reg, multiplotter):
            assert kind not in module.SUPPORTED_2D_KINDS, (
                f"{module.__name__}.SUPPORTED_2D_KINDS 不该含 3D 的 {kind}"
            )

        # 字典类注册表应当是同一个对象，而不是各持一份副本
        assert MultiPlotter.LAYER_SPECS is reg.LAYER_SPECS
        assert reg.LAYER_SPECS is multiplotter.LAYER_SPECS

        assert multiplotter.SUPPORTED_KINDS == (
            multiplotter.SUPPORTED_2D_KINDS
            | multiplotter.SUPPORTED_3D_KINDS
        )

        # 描述接口要能看到新图层
        assert any(
            row["kind"] == kind for row in multiplotter.describe_layers()
        )
    finally:
        for name in MUTATED:
            getattr(MultiPlotter, name).pop(kind, None)

        for name, value in original_synced.items():
            setattr(MultiPlotter, name, value)
            setattr(reg, name, value)
            setattr(multiplotter, name, value)

    for name, size in original_sizes.items():
        assert len(getattr(MultiPlotter, name)) == size, f"{name} 没还原干净"


def main():
    """脚本方式运行：``python tests/defaults_test.py``。

    加 ``--update-snapshot`` 时只重新生成默认值快照，不跑测试。
    """

    if "--update-snapshot" in sys.argv:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "defaults_snapshot.json")
        snapshot = collect_snapshot()

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2,
                      sort_keys=True)
            handle.write("\n")

        print(f"已更新快照：{path}（{len(snapshot)} 个 kind）")
        return 0

    tests = [
        ("预设可达性", test_defaults_are_reachable),
        ("白名单键类型", test_passthrough_entries_are_strings),
        ("默认值快照", test_defaults_match_snapshot),
        ("每个 kind 都有契约", test_every_kind_has_a_spec),
        ("文档预设抽查", test_documented_presets_match_code),
        ("注册表三方一致", test_registration_keeps_every_view_in_sync),
    ]

    failed = 0

    for name, func in tests:
        try:
            func()
        except AssertionError as exc:
            failed += 1
            print(f"[FAIL] {name}\n       {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[ERROR] {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"[PASS] {name}")

    print()

    if failed:
        print(f"{failed}/{len(tests)} 项失败")
        return 1

    print(f"全部通过（{len(tests)}/{len(tests)}）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
