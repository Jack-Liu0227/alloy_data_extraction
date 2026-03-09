import importlib
import pkgutil


def _auto_import_submodules(base_pkg_suffix: str):
    """
    Recursively import all modules under a subpackage in this package.
    As long as a module is imported, any @OPERATOR_REGISTRY.register()
    inside it will be executed automatically.
    """
    base_pkg_name = __name__ + base_pkg_suffix

    try:
        target_pkg = importlib.import_module(base_pkg_name)
    except ImportError:
        # If there is no target subpackage, just return.
        return

    # Recursively traverse all submodules / subpackages under the target package.
    for _, module_name, is_pkg in pkgutil.walk_packages(
        target_pkg.__path__, target_pkg.__name__ + "."
    ):
        # No need to distinguish is_pkg; package __init__ will also be imported.
        importlib.import_module(module_name)


# 1. Import operators and prompts modules automatically.
_auto_import_submodules(".operators")
_auto_import_submodules(".prompts")

# 2. If you want to provide an explicit entry point for external use, you can also expose a main
def main():
    _auto_import_submodules(".operators")
    _auto_import_submodules(".prompts")


__all__ = ["main"]
