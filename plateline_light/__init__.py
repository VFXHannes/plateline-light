"""Plateline -- batch camera setup from video plates.

Edition is decided by what the build script packs. The Pro zip contains
`metadata.py`, `folder_import.py` and `proxy.py`; the Light zip contains none of
them. Presence of a module *is* the feature flag, so there is nothing to keep in
sync and no dead code in the Light build.

Every optional module extends the base through registration hooks -- a lens
reader in `core`, panel sections in `ui` -- so `core` and `ui` never reference
them. Adding a Pro feature means adding a module and a build-list entry.

Deliberately no `bl_info` -- Blender 4.2+ installs this as an extension and
reads `blender_manifest.toml` instead, where a stray `bl_info` is ignored at
best and flagged during review at worst.
"""

from . import core, ui


def _optional(name):
    try:
        module = __import__(f"{__package__}.{name}", fromlist=[name])
    except ImportError:
        return None
    return module


metadata = _optional("metadata")
folder_import = _optional("folder_import")
proxy = _optional("proxy")

IS_PRO = proxy is not None

# core and ui first: the optional modules register into them.
_modules = [m for m in (core, ui, metadata, folder_import, proxy) if m is not None]


def register():
    for module in _modules:
        module.register()


def unregister():
    for module in reversed(_modules):
        module.unregister()
