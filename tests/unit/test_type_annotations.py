"""Test that all type annotations in all application modules can be resolved without NameError."""

import importlib
import inspect
import os
import typing


def test_all_modules_type_annotations():
    """Ensure all functions and classes across app/ and bot.py have valid, importable type hints."""
    modules = ["bot"]
    for root, _, files in os.walk("app"):
        for file in files:
            if file.endswith(".py"):
                rel = os.path.relpath(os.path.join(root, file), ".")
                if rel.endswith("/__init__.py"):
                    modname = rel[:-12].replace("/", ".")
                else:
                    modname = rel[:-3].replace("/", ".")
                modules.append(modname)

    failures = []
    for modname in set(modules):
        try:
            mod = importlib.import_module(modname)
        except Exception as e:
            failures.append(f"Failed to import {modname}: {e}")
            continue

        for name, obj in inspect.getmembers(mod):
            if inspect.isfunction(obj) and getattr(obj, "__module__", None) == modname:
                try:
                    typing.get_type_hints(obj)
                except Exception as e:
                    failures.append(f"{modname}.{name}: {e}")
            elif inspect.isclass(obj) and getattr(obj, "__module__", None) == modname:
                try:
                    typing.get_type_hints(obj)
                except Exception as e:
                    failures.append(f"class {modname}.{name}: {e}")

    assert not failures, "Unresolvable type hints found:\n" + "\n".join(failures)
