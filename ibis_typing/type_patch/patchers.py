"""Type patch generators."""

import functools
import importlib
import logging
import re
from collections.abc import Callable
from pathlib import Path
from types import FunctionType, MethodType, ModuleType
from typing import cast

from attrs import frozen

logger = logging.getLogger(__name__)


@frozen
class PatchedModuleWriter:
    target_module: ModuleType
    patchers: list[Callable[[str], str]]

    def write_patched_module(self):
        logger.info("Writing type-patched module")
        logger.info(f"\t{self.target_module.__name__}")
        current = Path(cast(str, self.target_module.__file__))
        backup = current.with_suffix(".py.bak")

        original_impl = backup.read_text() if backup.exists() else current.read_text()
        backup.write_text(original_impl)

        patched_impl = functools.reduce(
            lambda x, f: f(x),
            self.patchers,
            original_impl,
        )
        # Remove the current file to avoid collisions with uv hard-links.
        current.unlink()
        current.write_text(patched_impl)


@frozen
class MethodOverloadPatcher:
    cls_patch: type

    def __call__(self, module_impl: str) -> str:
        patch_impl = read_patch_impl(self.cls_patch)

        cls = self.cls_patch.__bases__[0]
        name = get_method_name(self.cls_patch)
        logger.info("@overload")
        logger.info(f"{cls.__qualname__}.{name}()")

        patch_body = get_class_body(patch_impl, cls=self.cls_patch.__name__)
        cls_body = get_class_body(module_impl, cls=cls.__name__)

        patch = self.apply_patch(name, cls_body, patch_body)

        return module_impl.replace(cls_body, patch)

    @classmethod
    def apply_patch(cls, method: str, cls_body: str, patch_body: str) -> str:
        method_def = "\n" + " " * 4 + f"def {method}("

        cls_clean = remove_overloads(cls_body, method=method)
        head, tail = cls_clean.rsplit(method_def, 1)
        patch = patch_body.rsplit(method_def, 1)[0]

        return head + patch + method_def + tail


def read_patch_impl(cls_patch: type | Callable) -> str:
    module = importlib.import_module(cls_patch.__module__)
    path = module.__file__
    assert path
    return Path(path).read_text()


def get_method_name(cls_patch: type) -> str:
    """Get the name of the last declared method of the class."""
    return next(
        name
        for name, method in reversed(vars(cls_patch).items())  # type: ignore
        if (callable(method) and method.__module__ == cls_patch.__module__)
        or (
            isinstance(method, property)
            and method.fget.__module__ == cls_patch.__module__
        )
    )


def get_class_body(module_impl: str, *, cls: str) -> str:
    """Extract class code body from module code body.

    >>> module = '''from __future__ import annotations
    ... class Foo():
    ...     def bar(self) -> int:
    ...         return 42'''
    >>> body = get_class_body(module, cls="Foo")
    >>> print(body)
    <BLANKLINE>
        def bar(self) -> int:
            return 42
    """
    m = re.search(
        rf"\nclass {cls}.*?\):(.*?)(?=\n\n\n|\Z)",
        module_impl,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert m
    return m.group(1)


@frozen
class MethodSelfReturnTypePatcher:
    """Patches methods returning instances of its own type."""

    method: MethodType

    def __call__(self, module_impl: str) -> str:
        method = self.method
        logger.info(f"{method.__qualname__}() -> Self")

        return self.apply_patch(module_impl, self.method)

    @classmethod
    def apply_patch(cls, module_impl: str, method: MethodType) -> str:
        pattern = re.compile(
            rf"(def {method.__name__}\(\s*self(?!:)[^)]*?\) -> ).+?:",
        )
        replacement = r"\1Self:"
        if not pattern.findall(module_impl):
            raise LookupError(f"Method {method.__qualname__} not found.")

        return re.sub(
            pattern.pattern,
            replacement,
            module_impl,
            flags=re.MULTILINE,
        )


@frozen
class FunctionOverloadPatcher:
    function: FunctionType

    def __call__(self, module_impl: str) -> str:
        fun = self.function
        logger.info("@overload")
        logger.info(f"{fun.__name__}()")

        patch_impl = read_patch_impl(fun)

        return self.apply_patch(fun.__name__, module_impl, patch_impl)

    @classmethod
    def apply_patch(cls, name: str, module_impl: str, patch_impl: str) -> str:
        module_impl = remove_overloads(module_impl, method=name)
        patch = find_function_overload_patch(name, patch_impl)
        target = find_function_overload_target(name, module_impl)

        return module_impl.replace(target, patch + target)


def remove_overloads(code: str, *, method: str) -> str:
    """Remove method overloads from a code block.

    >>> module = '''from typing import overload
    ... class Foo:
    ...     @overload
    ...     def bar(self) -> int: ...
    ...     @overload
    ...     def bar(self, x: int) -> int: ...
    ...     def bar(self, x: int = 0) -> int:
    ...         return x'''
    >>> clean = remove_overloads(module, method="bar")
    >>> print(clean)
    from typing import overload
    class Foo:
        def bar(self, x: int = 0) -> int:
            return x
    """
    pattern = re.compile(
        rf"\s+@overload\s+def {method}.*?: \.\.\.",
        flags=re.MULTILINE | re.DOTALL,
    )
    return pattern.sub(r"", code)


def find_function_overload_patch(name: str, patch_impl: str) -> str:
    patch_re = re.compile(
        r"\n\n" + rf"(@overload\ndef {name}[([].*)" + rf"def {name}[([]",
        flags=re.DOTALL,
    )
    match = patch_re.search(patch_impl)
    if not match:
        raise LookupError(f"Function {name} not found.")
    return match.group(1)


def find_function_overload_target(name: str, module_impl: str) -> str:
    target_re = re.compile(
        r"(?<=\n\n)" + r"(?:@.*\n)*" + rf"def {name}[([]",
    )
    match = target_re.search(module_impl)
    if not match:
        raise LookupError(f"Function {name} not found.")
    return match.group(0)


@frozen
class TypeCheckingModulePatcher:
    """Add TYPE_CHECKING code to a module.

    >>> module = '''from __future__ import annotations
    ... if TYPE_CHECKING:
    ...     from typing import overload'''
    >>> patch = '''from __future__ import annotations
    ... if TYPE_CHECKING:
    ...     from typing import Self'''
    >>> patcher = TypeCheckingModulePatcher(__file__)
    >>> patched = patcher.apply_patch(module, patch)
    >>> print(patched)
    from __future__ import annotations
    if TYPE_CHECKING:
        from typing import Self
        from typing import overload
    """

    typed_module_file: str

    def __call__(self, module_impl: str) -> str:
        path = Path(self.typed_module_file)
        logger.info("if TYPE_CHECKING: ...")

        patch_impl = path.read_text()
        return self.apply_patch(module_impl, patch_impl)

    @classmethod
    def apply_patch(cls, module_impl: str, patch_impl: str) -> str:
        target = "if TYPE_CHECKING:"
        patch = target + patch_impl.split(target, 1)[1]
        assert target in module_impl
        return (
            module_impl.replace(target, patch)
            if patch not in module_impl
            else module_impl
        )


@frozen
class TypingOverloadImportPatcher:
    """Import @overload in target module.

    >>> patcher = TypingOverloadImportPatcher()
    >>> print(patcher("if TYPE_CHECKING: ..."))
    from typing import overload
    if TYPE_CHECKING: ...
    """

    def __call__(self, module_impl: str) -> str:
        target = "if TYPE_CHECKING:"
        overload_import = "from typing import overload\n"
        patch = overload_import + target
        assert target in module_impl
        return (
            module_impl.replace(target, patch)
            if patch not in module_impl
            else module_impl
        )
