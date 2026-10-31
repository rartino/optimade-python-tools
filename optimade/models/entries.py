from datetime import datetime
from typing import Annotated, Any, ClassVar, Literal

from pydantic import BaseModel, field_validator, model_validator

from optimade.models.jsonapi import Attributes, Relationships, Resource
from optimade.models.optimade_json import (
    BaseRelationshipResource,
    DataType,
    Relationship,
    ValidIdentifier,
)
from optimade.models.utils import OptimadeField, StrictField, SupportLevel

__all__ = (
    "EntryRelationships",
    "EntryResourceAttributes",
    "EntryResource",
    "EntryInfoProperty",
    "EntryInfoResource",
)


class TypedRelationship(Relationship):
    _req_type: ClassVar[str]

    @field_validator("data", mode="after")
    @classmethod
    def check_rel_type(
        cls, data: BaseRelationshipResource | list[BaseRelationshipResource]
    ) -> list[BaseRelationshipResource]:
        if not isinstance(data, list):
            # All relationships at this point are empty-to-many relationships in JSON:API:
            # https://jsonapi.org/format/1.0/#document-resource-object-linkage
            raise ValueError("`data` key in a relationship must always store a list.")

        if any(obj.type != cls._req_type for obj in data):
            raise ValueError("Object stored in relationship data has wrong type")

        return data


class ReferenceRelationship(TypedRelationship):
    _req_type: ClassVar[Literal["references"]] = "references"


class StructureRelationship(TypedRelationship):
    _req_type: ClassVar[Literal["structures"]] = "structures"


class FileRelationship(TypedRelationship):
    _req_type: ClassVar[Literal["files"]] = "files"


class EntryRelationships(Relationships):
    """This model wraps the JSON API Relationships to include type-specific top level keys."""

    references: Annotated[
        ReferenceRelationship | None,
        StrictField(
            description="Object containing links to relationships with entries of the `references` type.",
        ),
    ] = None

    structures: Annotated[
        StructureRelationship | None,
        StrictField(
            description="Object containing links to relationships with entries of the `structures` type.",
        ),
    ] = None

    files: Annotated[
        FileRelationship | None,
        StrictField(
            description="Object containing links to relationships with entries of the `files` type.",
        ),
    ] = None


class EntryResourceAttributes(Attributes):
    """Contains key-value pairs representing the entry's properties."""

    immutable_id: Annotated[
        str | None,
        OptimadeField(
            description="""The entry's immutable ID (e.g., an UUID). This is important for databases having preferred IDs that point to "the latest version" of a record, but still offer access to older variants. This ID maps to the version-specific record, in case it changes in the future.

- **Type**: string.

- **Requirements/Conventions**:
    - **Support**: OPTIONAL support in implementations, i.e., MAY be `null`.
    - **Query**: MUST be a queryable property with support for all mandatory filter features.

- **Examples**:
    - `"8bd3e750-b477-41a0-9b11-3a799f21b44f"`
    - `"fjeiwoj,54;@=%<>#32"` (Strings that are not URL-safe are allowed.)""",
            support=SupportLevel.OPTIONAL,
            queryable=SupportLevel.MUST,
        ),
    ] = None

    last_modified: Annotated[
        datetime | None,
        OptimadeField(
            description="""Date and time representing when the entry was last modified.

- **Type**: timestamp.

- **Requirements/Conventions**:
    - **Support**: SHOULD be supported by all implementations, i.e., SHOULD NOT be `null`.
    - **Query**: MUST be a queryable property with support for all mandatory filter features.
    - **Response**: REQUIRED in the response unless the query parameter `response_fields` is present and does not include this property.

- **Example**:
    - As part of JSON response format: `"2007-04-05T14:30:20Z"` (i.e., encoded as an [RFC 3339 Internet Date/Time Format](https://tools.ietf.org/html/rfc3339#section-5.6) string.)""",
            support=SupportLevel.SHOULD,
            queryable=SupportLevel.MUST,
        ),
    ]

    @field_validator("immutable_id", mode="before")
    @classmethod
    def cast_immutable_id_to_str(cls, value: Any) -> str:
        """Convenience validator for casting `immutable_id` to a string."""
        if value is not None and not isinstance(value, str):
            value = str(value)

        return value


class EntryResource(Resource):
    """The base model for an entry resource."""

    id: Annotated[
        str,
        OptimadeField(
            description="""An entry's ID as defined in section Definition of Terms.

- **Type**: string.

- **Requirements/Conventions**:
    - **Support**: MUST be supported by all implementations, MUST NOT be `null`.
    - **Query**: MUST be a queryable property with support for all mandatory filter features.
    - **Response**: REQUIRED in the response.

- **Examples**:
    - `"db/1234567"`
    - `"cod/2000000"`
    - `"cod/2000000@1234567"`
    - `"nomad/L1234567890"`
    - `"42"`""",
            support=SupportLevel.MUST,
            queryable=SupportLevel.MUST,
        ),
    ]

    type: Annotated[
        str,
        OptimadeField(
            description="""The name of the type of an entry.

- **Type**: string.

- **Requirements/Conventions**:
    - **Support**: MUST be supported by all implementations, MUST NOT be `null`.
    - **Query**: MUST be a queryable property with support for all mandatory filter features.
    - **Response**: REQUIRED in the response.
    - MUST be an existing entry type.
    - The entry of type `<type>` and ID `<id>` MUST be returned in response to a request for `/<type>/<id>` under the versioned base URL.

- **Example**: `"structures"`""",
            support=SupportLevel.MUST,
            queryable=SupportLevel.MUST,
        ),
    ]

    attributes: Annotated[
        EntryResourceAttributes,
        StrictField(
            description="""A dictionary, containing key-value pairs representing the entry's properties, except for `type` and `id`.
Database-provider-specific properties need to include the database-provider-specific prefix (see section on Database-Provider-Specific Namespace Prefixes).""",
        ),
    ]

    relationships: Annotated[
        EntryRelationships | None,
        StrictField(
            description="""A dictionary containing references to other entries according to the description in section Relationships encoded as [JSON API Relationships](https://jsonapi.org/format/1.0/#document-resource-object-relationships).
The OPTIONAL human-readable description of the relationship MAY be provided in the `description` field inside the `meta` dictionary of the JSON API resource identifier object, and the OPTIONAL kind of relationship in its `role` field.""",
        ),
    ] = None


# The JSON type that a Property Definition (OPTIMADE >= 1.2) MUST give as the first
# element of `type` for each OPTIMADE data type in `x-optimade-type`.
_PROPERTY_DEFINITION_JSON_TYPES: dict[DataType, str] = {
    DataType.STRING: "string",
    DataType.INTEGER: "integer",
    DataType.FLOAT: "number",
    DataType.BOOLEAN: "boolean",
    DataType.TIMESTAMP: "string",
    DataType.LIST: "array",
    DataType.DICTIONARY: "object",
}


class EntryInfoProperty(BaseModel):
    """Description of a property in an entry listing info endpoint (`/info/<entry_type>`).

    Since OPTIMADE v1.2, each property is described by a full Property Definition, in
    which `type` is a JSON Schema type list (e.g. `["integer", "null"]`) and the
    OPTIMADE data type is given by `x-optimade-type`.
    The earlier form, in which `type` is a single OPTIMADE data type (e.g. `"integer"`),
    is also accepted.
    Other Property Definition keys are not modelled here and are ignored.

    """

    description: Annotated[
        str,
        StrictField(description="A human-readable description of the entry property"),
    ]

    unit: Annotated[
        str | None,
        StrictField(
            description="""The physical unit of the entry property.
This MUST be a valid representation of units according to version 2.1 of [The Unified Code for Units of Measure](https://unitsofmeasure.org/ucum.html).
It is RECOMMENDED that non-standard (non-SI) units are described in the description for the property.
In a Property Definition (OPTIMADE >= 1.2), the unit is instead given by `x-optimade-unit`.""",
        ),
    ] = None

    sortable: Annotated[
        bool | None,
        StrictField(
            description="""Defines whether the entry property can be used for sorting with the "sort" parameter.
If the entry listing endpoint supports sorting, this key MUST be present for sortable properties with value `true`.
In a Property Definition (OPTIMADE >= 1.2), this is instead given by the `sortable` key of `x-optimade-implementation`.""",
        ),
    ] = None

    type: Annotated[
        DataType | list[str] | None,
        StrictField(
            title="Type",
            description="""The type of the property's value.

In a Property Definition (OPTIMADE >= 1.2), this MUST be a list of one or two elements, where the first element is the JSON type corresponding to `x-optimade-type` (`"boolean"`, `"string"`, `"integer"`, `"number"`, `"array"` or `"object"`), and the optional second element MUST be `"null"`, specifying that the property can be `null`.

In the earlier form (OPTIMADE < 1.2), this MUST be any of the types defined in the Data types section.
For the purpose of compatibility with future versions of this specification, a client MUST accept values that are not `string` values specifying any of the OPTIMADE Data types, but MUST then also disregard the `type` field.
Note, if the value is a nested type, only the outermost type should be reported.
E.g., for the entry resource `structures`, the `species` property is defined as a list of dictionaries, hence its `type` value would be `list`.""",
        ),
    ] = None

    x_optimade_type: Annotated[
        str | None,
        StrictField(
            alias="x-optimade-type",
            optimade_version=">= 1.2",
            description="""The OPTIMADE data type of the property's value in a Property Definition.
MUST be one of `"string"`, `"integer"`, `"float"`, `"boolean"`, `"timestamp"`, `"list"`, `"dictionary"` or the name of a namespace-specific data type that starts with an underscore followed by the provider-specific prefix.""",
        ),
    ] = None

    @field_validator("type", mode="after")
    @classmethod
    def check_json_schema_type(
        cls, value: DataType | list[str] | None
    ) -> DataType | list[str] | None:
        """Check the list form of `type` used in Property Definitions."""
        if not isinstance(value, list):
            return value
        if not 1 <= len(value) <= 2:
            raise ValueError(
                f"`type` must be a list of one or two elements, not {value!r}."
            )
        if value[0] not in _PROPERTY_DEFINITION_JSON_TYPES.values():
            raise ValueError(
                f"The first element of `type` must be one of "
                f"{sorted(set(_PROPERTY_DEFINITION_JSON_TYPES.values()))}, not {value[0]!r}."
            )
        if len(value) == 2 and value[1] != "null":
            raise ValueError(
                f"The second element of `type` must be 'null', not {value[1]!r}."
            )
        return value

    @model_validator(mode="after")
    def check_type_matches_x_optimade_type(self) -> "EntryInfoProperty":
        """Check that a list `type` gives the JSON type of a standard `x-optimade-type`."""
        if isinstance(self.type, list) and self.x_optimade_type is not None:
            try:
                data_type = DataType(self.x_optimade_type)
            except ValueError:
                # Namespace-specific data types may use any JSON type.
                return self
            expected = _PROPERTY_DEFINITION_JSON_TYPES.get(data_type)
            if expected is not None and self.type[0] != expected:
                raise ValueError(
                    f"`type` {self.type!r} does not match `x-optimade-type` "
                    f"{self.x_optimade_type!r}, which requires {expected!r}."
                )
        return self

    @staticmethod
    def resolve_data_type(
        type_: DataType | list[str] | str | None,
        x_optimade_type: str | None = None,
    ) -> DataType | None:
        """Return the OPTIMADE data type described by the `type` and
        `x-optimade-type` values of an entry info property, in either form.

        A standard `x-optimade-type` is used as is.
        Otherwise, including for namespace-specific data types, the data type is
        derived from `type`, mapping a JSON type (e.g. `"number"`) to its OPTIMADE
        counterpart (e.g. `float`); note that this cannot tell a `timestamp` from a
        `string`.

        Parameters:
            type_: The value of `type`.
            x_optimade_type: The value of `x-optimade-type`, if any.

        Returns:
            The OPTIMADE data type, or `None` if it cannot be determined
            (including when it is `unknown`).

        """
        data_type = None
        if x_optimade_type is not None:
            try:
                data_type = DataType(x_optimade_type)
            except ValueError:
                pass
        if data_type is None:
            if isinstance(type_, list):
                data_type = DataType.from_json_type(type_[0]) if type_ else None
            elif type_ is not None:
                try:
                    data_type = DataType(type_)
                except ValueError:
                    pass
        return None if data_type is DataType.UNKNOWN else data_type


class EntryInfoResource(BaseModel):
    id: Annotated[
        str,
        StrictField(
            optimade_version=">= 1.2",
            description="Must precisely match the entry type name for the given info endpoint.",
        ),
    ]

    type: Annotated[
        str,
        StrictField(
            optimade_version=">= 1.2",
            description="The type of this response.",
            default="info",
        ),
    ]

    formats: Annotated[
        list[str],
        StrictField(
            description="List of output formats available for this type of entry."
        ),
    ]

    description: Annotated[str, StrictField(description="Description of the entry.")]

    properties: Annotated[
        dict[ValidIdentifier, EntryInfoProperty],
        StrictField(
            description="A dictionary describing queryable properties for this entry type, where each key is a property name.",
        ),
    ]

    output_fields_by_format: Annotated[
        dict[str, list[ValidIdentifier]],
        StrictField(
            description="Dictionary of available output fields for this entry type, where the keys are the values of the `formats` list and the values are the keys of the `properties` dictionary.",
        ),
    ]
