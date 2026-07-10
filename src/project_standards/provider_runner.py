"""Load packaged standard manifests and dispatch their declared Python providers.

The runner executes only Python import entrypoints. Documentation-only declarations
are metadata, while command and workflow providers fail closed instead of crossing a
shell or external-process boundary this runner does not own.
"""

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


def load_packaged_standard_manifest(
    standard_id: str, *, bundles_dir: Path = BUNDLES_DIR
) -> StandardManifest:
    """Load a standard manifest from the installed bundle tree.

    Missing and invalid manifests raise ``ManifestError`` so callers can map every
    package-manifest failure to the adopt CLI's exit code 3 boundary.
    """
    path = bundles_dir / standard_id / "standard.toml"
    if not path.is_file():
        raise ManifestError(f"packaged standard manifest missing: {path}")
    try:
        return load_standard_manifest(path)
    except StandardManifestError as exc:
        raise ManifestError(f"cannot load packaged standard manifest {path}: {exc}") from exc


def _run_python_provider(provider: ProviderBlock, argv: list[str]) -> int:
    """Invoke one Python provider with isolated arguments and return its process status."""
    if provider.kind is not ProviderKind.PYTHON:
        raise ManifestError(
            f"unsupported executable provider kind {provider.kind.value} "
            f"for operation {provider.operation.value}"
        )

    entrypoint = provider.entrypoint
    if entrypoint is None or entrypoint.count(":") != 1:
        raise ManifestError(f"malformed Python provider entrypoint: {entrypoint!r}")
    module_name, attribute_name = entrypoint.split(":")
    if not module_name or not attribute_name:
        raise ManifestError(f"malformed Python provider entrypoint: {entrypoint!r}")

    try:
        module = import_module(module_name)
    except Exception as exc:
        raise ManifestError(f"cannot import Python provider {entrypoint}: {exc}") from exc

    try:
        candidate = getattr(module, attribute_name)
    except AttributeError as exc:
        raise ManifestError(
            f"Python provider module {module_name!r} has no attribute {attribute_name!r}"
        ) from exc
    except Exception as exc:
        raise ManifestError(f"cannot resolve Python provider {entrypoint}: {exc}") from exc
    if not callable(candidate):
        raise ManifestError(f"Python provider {entrypoint} is not callable")
    provider_main = cast("Callable[[list[str]], object]", candidate)

    try:
        result = provider_main(list(argv))
    except Exception as exc:
        raise ManifestError(f"Python provider {entrypoint} failed: {exc}") from exc

    if (
        isinstance(result, bool)
        or not isinstance(result, int)
        or not 0 <= result <= _MAX_PROCESS_EXIT_CODE
    ):
        raise ManifestError(f"Python provider {entrypoint} returned invalid exit code {result!r}")
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
