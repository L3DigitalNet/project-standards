"""Load packaged standard manifests and dispatch their declared Python providers.

The runner executes only Python import entrypoints. Documentation-only declarations
are metadata, while command and workflow providers fail closed instead of crossing a
shell or external-process boundary this runner does not own.
"""

import re
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import cast

from project_standards.adopt.errors import ManifestError, UsageError
from project_standards.adopt.manifest import BUNDLES_DIR
from project_standards.standard_manifest import (
    ProviderBlock,
    ProviderKind,
    ProviderOperation,
    StandardManifest,
    StandardManifestError,
    load_standard_manifest,
)

_MAX_PROCESS_EXIT_CODE = 255
# Match StandardTable.id's KebabId grammar exactly so path lookup cannot accept an
# identifier that the manifest boundary later interprets differently.
_STANDARD_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_packaged_standard_manifest(
    standard_id: str, *, bundles_dir: Path = BUNDLES_DIR
) -> StandardManifest:
    """Load a standard manifest from the installed bundle tree.

    Missing and invalid manifests raise ``ManifestError`` so callers can map every
    package-manifest failure to the adopt CLI's exit code 3 boundary.
    """
    if _STANDARD_ID_RE.fullmatch(standard_id) is None:
        raise ManifestError("invalid packaged standard id")

    try:
        root = bundles_dir.resolve()
        bundle_path = root / standard_id
        resolved_bundle = bundle_path.resolve()
        manifest_path = bundle_path / "standard.toml"
        resolved_manifest = manifest_path.resolve()
    except (OSError, RuntimeError) as exc:
        raise ManifestError(
            f"cannot resolve packaged standard manifest ({type(exc).__name__})"
        ) from exc

    # Both checks are required: a bundle symlink can leave the package root, while
    # a manifest symlink can leave its otherwise-contained bundle.
    if not resolved_bundle.is_relative_to(root) or not resolved_manifest.is_relative_to(
        resolved_bundle
    ):
        raise ManifestError("packaged standard manifest escapes bundles directory")
    if not resolved_manifest.is_file():
        raise ManifestError(f"packaged standard manifest missing: {manifest_path}")
    try:
        return load_standard_manifest(manifest_path)
    except StandardManifestError as exc:
        raise ManifestError(f"packaged standard manifest is invalid: {manifest_path}") from exc


def _run_python_provider(provider: ProviderBlock, argv: list[str]) -> int:
    """Invoke one Python provider with isolated arguments and return its process status."""
    if provider.kind is not ProviderKind.PYTHON:
        raise ManifestError(
            f"unsupported executable provider kind {provider.kind.value} "
            f"for operation {provider.operation.value}"
        )

    # ProviderBlock owns and validates the module.path:object grammar before dispatch.
    entrypoint = cast("str", provider.entrypoint)
    module_name, attribute_name = entrypoint.split(":")

    try:
        module = import_module(module_name)
    except (Exception, SystemExit) as exc:
        raise ManifestError(
            f"cannot import Python provider {entrypoint} ({type(exc).__name__})"
        ) from exc

    try:
        candidate = getattr(module, attribute_name)
    except AttributeError as exc:
        raise ManifestError(
            f"Python provider module {module_name!r} has no attribute {attribute_name!r}"
        ) from exc
    except (Exception, SystemExit) as exc:
        raise ManifestError(
            f"cannot resolve Python provider {entrypoint} ({type(exc).__name__})"
        ) from exc
    if not callable(candidate):
        raise ManifestError(f"Python provider {entrypoint} is not callable")
    provider_main = cast("Callable[[list[str]], object]", candidate)

    try:
        result = provider_main(list(argv))
    except (Exception, SystemExit) as exc:
        raise ManifestError(f"Python provider {entrypoint} failed ({type(exc).__name__})") from exc

    if (
        isinstance(result, bool)
        or not isinstance(result, int)
        or not 0 <= result <= _MAX_PROCESS_EXIT_CODE
    ):
        raise ManifestError(
            f"Python provider {entrypoint} returned invalid exit code type {type(result).__name__}"
        )
    return result


def run_packaged_providers(
    standard_id: str,
    operation: ProviderOperation,
    argv: list[str],
    *,
    bundles_dir: Path = BUNDLES_DIR,
) -> int:
    """Run matching packaged Python providers in declared order and return the worst status."""
    manifest = load_packaged_standard_manifest(standard_id, bundles_dir=bundles_dir)
    providers = [provider for provider in manifest.providers if provider.operation is operation]
    if not providers:
        raise UsageError(f"{standard_id} does not declare provider operation {operation.value}")

    executable_providers = [
        provider for provider in providers if provider.kind is not ProviderKind.DOCUMENTATION_ONLY
    ]
    if not executable_providers:
        raise UsageError(
            f"{standard_id} does not declare executable provider operation {operation.value}"
        )

    return max(_run_python_provider(provider, argv) for provider in executable_providers)
