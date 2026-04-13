"""Module auto-discovery and mounting for FastAPI.

Scans ``modules/`` for sub-packages that export:
- ``router``       – a FastAPI APIRouter instance
- ``MODULE_META``  – dict with at least ``name``, ``version``, ``prefix``

Each discovered router is mounted at ``/api/v1/{prefix}/``.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from fastapi import FastAPI

logger = logging.getLogger(__name__)

MODULES_DIR = Path(__file__).resolve().parent


def discover_and_mount_modules(app: FastAPI) -> list[dict]:
    """Walk the modules package, import each sub-package, and mount routers."""
    mounted: list[dict] = []

    for module_info in pkgutil.iter_modules([str(MODULES_DIR)]):
        if not module_info.ispkg:
            continue

        module_name = f"modules.{module_info.name}"
        try:
            mod = importlib.import_module(module_name)
        except Exception:
            logger.exception("Failed to import module %s", module_name)
            continue

        router = getattr(mod, "router", None)
        meta = getattr(mod, "MODULE_META", None)

        if router is None or meta is None:
            logger.debug("Skipping %s — no router or MODULE_META", module_name)
            continue

        prefix = meta.get("prefix", module_info.name)
        app.include_router(router, prefix=f"/api/v1/{prefix}", tags=[meta.get("name", prefix)])
        logger.info(
            "Mounted module '%s' v%s at /api/v1/%s/",
            meta.get("name"),
            meta.get("version"),
            prefix,
        )
        mounted.append(meta)

    return mounted
