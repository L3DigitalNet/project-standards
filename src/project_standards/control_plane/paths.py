"""Canonical scalar primitives specific to the consumer control plane."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

_CATALOG_MAJOR_PATTERN_TEXT = r"^[1-9][0-9]*$"
_CATALOG_MAJOR_PATTERN = re.compile(_CATALOG_MAJOR_PATTERN_TEXT, re.ASCII)


def _pydantic_string_schema[T](
    scalar_type: type[T],
    validator: Callable[[str], T],
    serializer: Callable[[T], str],
) -> CoreSchema:
    string_schema = core_schema.str_schema(
        pattern=_CATALOG_MAJOR_PATTERN_TEXT,
        strict=True,
    )
    validated_string = core_schema.no_info_after_validator_function(
        validator,
        string_schema,
    )
    return core_schema.json_or_python_schema(
        json_schema=validated_string,
        python_schema=core_schema.union_schema(
            [core_schema.is_instance_schema(scalar_type), validated_string]
        ),
        serialization=core_schema.plain_serializer_function_ser_schema(
            serializer,
            return_schema=core_schema.str_schema(),
            when_used="always",
        ),
    )


@dataclass(frozen=True, slots=True)
class CatalogMajor:
    """Represent the canonical positive-integer catalog compatibility line."""

    value: str
    major: int = field(init=False)

    def __post_init__(self) -> None:
        if _CATALOG_MAJOR_PATTERN.fullmatch(self.value) is None:
            raise ValueError("catalog major must be a canonical positive ASCII integer")
        object.__setattr__(self, "major", int(self.value))

    @classmethod
    def _from_string(cls, value: str) -> Self:
        return cls(value)

    @staticmethod
    def _to_string(value: CatalogMajor) -> str:
        return value.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Self],
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Expose strict validation and string serialization to Pydantic."""
        return _pydantic_string_schema(cls, cls._from_string, cls._to_string)
