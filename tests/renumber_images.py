# -*- coding: utf-8 -*-
"""给 tests/images/ 里的图片分配顺序编号，并同步更新所有文档与脚本里的引用。

编号规则（**稳定编号**）
------------------------
拆分文档之后，「按出现顺序重新编号」会把已经定好的编号整体打乱：
第 25 章（动画）的图搬到了 ANIMATION.md，而第 26/27 章的图还在 API.md，
于是按文件扫描出来的顺序和现有编号并不一致，一跑就把 26~31 全部改名。

所以这里改成**稳定编号**：

* 已经有 ``NN_`` 前缀的图片**保留原编号**，不动；
* 只有新增的、还没有编号的图片才分配新编号，
  按它们在文档里出现的先后，依次取当前**最小的空号**；
* 文档引用统一跟着最终编号走。

这样重复执行是幂等的，新增图片时也只会新增编号，
不会让已有图片改名、不会让文档里已经贴出去的链接失效。

用法：

    python renumber_images.py          # 预演
    python renumber_images.py --apply  # 执行
"""

import io
import os
import re
import sys

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)                                  # 包根目录（tests 的上一层）
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(TESTS_DIR, "images")

#: 扫描**新图顺序**用的文档，顺序即优先级。
#:
#: API.md 最前：它保留了原始章节顺序（第 0 章 -> 第 27 章），
#: 新图多半先出现在这里。
ORDER_DOCS = [
    "API.md",
    "ANIMATION.md",
    "README.md",
    "EXTENDING.md",
    "FAQ.md",
    os.path.join("examples", "README.md"),
]

#: 需要同步更新图片引用的文件（相对包根目录）。
REFERENCE_FILES = [
    "README.md",
    "API.md",
    "ANIMATION.md",
    "EXTENDING.md",
    "FAQ.md",
    os.path.join("examples", "README.md"),
    os.path.join("tests", "generate_examples.py"),
    os.path.join("tests", "generate_animation_examples.py"),
    os.path.join("tests", "generate_compare_examples.py"),
    os.path.join("tests", "generate_field_examples.py"),
    os.path.join("tests", "extend_example.py"),
    os.path.join("tests", "readme_check.py"),
    os.path.join("tests", "library_smoke_test.py"),
    os.path.join("tests", "field_table_test.py"),
    os.path.join("tests", "extension_test.py"),
    os.path.join("tests", "anim_api_test.py"),
]

PREFIX_PATTERN = re.compile(r"^(\d{2})_")
IMAGE_SUFFIXES = (".png", ".gif")


def split_name(filename):
    """把 ``18_foo.png`` 拆成 ``(18, "foo.png")``；没编号时编号为 ``None``。"""

    match = PREFIX_PATTERN.match(filename)

    if match:
        return int(match.group(1)), filename[match.end():]

    return None, filename


def iter_reference_files():
    """产出需要更新引用的文件路径。"""

    for name in REFERENCE_FILES:
        path = os.path.join(BASE_DIR, name)

        if os.path.isfile(path):
            yield path


def scan_document_order():
    """按文档出现顺序返回裸文件名列表（去重、保持顺序）。"""

    order = []

    for name in ORDER_DOCS:
        path = os.path.join(BASE_DIR, name)

        if not os.path.isfile(path):
            continue

        text = io.open(path, encoding="utf-8").read()

        refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
        refs += re.findall(r"<img[^>]*src=[\"']([^\"']+)[\"']", text)

        for ref in refs:
            # 文档里的图片引用形如 tests/images/01_xxx.png
            if "images/" not in ref:
                continue

            bare = split_name(os.path.basename(ref))[1]

            if bare not in order:
                order.append(bare)

    return order


def index_images():
    """扫描 images/ 目录，返回 ``{裸名: (编号, 真实文件名)}``。"""

    index = {}

    for filename in sorted(os.listdir(IMAGES_DIR)):
        if not filename.endswith(IMAGE_SUFFIXES):
            continue

        number, bare = split_name(filename)
        index.setdefault(bare, (number, filename))

    return index


def build_plan():
    """返回 ``(最终编号表, 重命名计划, 未引用清单)``。

    ``最终编号表`` 是 ``{裸名: 编号}``，``重命名计划`` 是
    ``[(旧文件名, 新文件名)]``。
    """

    order = scan_document_order()
    index = index_images()

    assigned = {}
    used = set()

    # 1) 已有编号的图片：保留原编号
    for bare, (number, _filename) in index.items():
        if number is not None:
            assigned[bare] = number
            used.add(number)

    # 2) 还没编号的图片：按文档出现顺序补空号
    unnumbered = [
        bare for bare in order
        if bare in index and assigned.get(bare) is None
    ]

    # 目录里存在但文档没引用的未编号图片，放到最后，保证也能拿到编号
    leftovers = [
        bare for bare in sorted(index)
        if assigned.get(bare) is None and bare not in unnumbered
    ]

    candidate = 1

    for bare in unnumbered + leftovers:
        while candidate in used:
            candidate += 1

        assigned[bare] = candidate
        used.add(candidate)

    # 3) 重命名计划（只涉及真正要改名的文件）
    renames = []

    for bare, (number, filename) in sorted(index.items()):
        final = assigned.get(bare)

        if final is None:
            continue

        new_name = f"{final:02d}_{bare}"

        if new_name != filename:
            renames.append((filename, new_name))

    unused = sorted(bare for bare in index if bare not in set(order))

    return order, index, assigned, renames, unused


def build_regex(bare):
    """构造幂等正则：既能匹配裸名，也能匹配已编号的名字。"""

    stem, suffix = os.path.splitext(bare)

    return re.compile(r"(\d{2}_)?" + re.escape(stem) + re.escape(suffix))


def main():
    apply_changes = "--apply" in sys.argv

    order, index, assigned, renames, unused = build_plan()

    print(
        f"文档引用 {len(order)} 张图片，"
        f"images/ 目录里有 {len(index)} 个文件\n"
    )

    print(f"{'编号':>4}  {'状态':<8} {'文件名'}")
    print("-" * 78)

    for bare in sorted(assigned, key=lambda name: (assigned[name], name)):
        number, filename = index.get(bare, (None, "（磁盘上没有）"))
        state = "已有" if number == assigned[bare] else "待改名"
        was = "" if number is None else f"（原 {number:02d}）"

        print(f"{assigned[bare]:>4}  {state:<8} {bare} {was}")

    if renames:
        print(f"\n需要重命名 {len(renames)} 个文件：")

        for old_name, new_name in renames:
            print(f"  {old_name} -> {new_name}")
    else:
        print("\n所有已编号图片的编号都是稳定的，无需重命名。")

    if unused:
        print("\n目录里存在但文档未引用的图片：")

        for bare in unused:
            print(f"  - {index[bare][1]}")

    print("\n引用替换检查：")

    for path in iter_reference_files():
        content = io.open(path, encoding="utf-8").read()
        hits = sum(len(build_regex(bare).findall(content)) for bare in assigned)
        print(f"  {os.path.relpath(path, BASE_DIR)}: 命中 {hits} 处")

    if not apply_changes:
        print("\n这是预演。确认无误后加 --apply 执行。")
        return

    # ---------------- 1) 先替换所有文本引用 ----------------
    print("\n更新引用：")

    for path in iter_reference_files():
        content = io.open(path, encoding="utf-8").read()
        original = content

        for bare, number in assigned.items():
            content = build_regex(bare).sub(
                f"{number:02d}_{bare}", content
            )

        name = os.path.relpath(path, BASE_DIR)

        if content != original:
            io.open(path, "w", encoding="utf-8").write(content)
            print(f"  {name}: 已更新")
        else:
            print(f"  {name}: 无需更新")

    # ---------------- 2) 再改文件名 ----------------
    print("\n重命名文件：")

    for old_name, new_name in renames:
        old_path = os.path.join(IMAGES_DIR, old_name)
        new_path = os.path.join(IMAGES_DIR, new_name)

        if os.path.exists(new_path):
            print(f"  跳过（目标已存在）: {new_name}")
            continue

        os.rename(old_path, new_path)
        print(f"  {old_name} -> {new_name}")

    print("\n完成。建议接着执行：python tests/readme_check.py")


if __name__ == "__main__":
    main()
