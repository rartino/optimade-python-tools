import pytest
from pydantic import ValidationError

from optimade.models.entries import EntryInfoProperty, EntryRelationships
from optimade.models.optimade_json import DataType


def test_simple_relationships():
    """Make sure relationship resources are added to the correct relationship"""

    good_relationships = (
        {"references": {"data": [{"id": "dijkstra1968", "type": "references"}]}},
        {"structures": {"data": [{"id": "dijkstra1968", "type": "structures"}]}},
    )
    for relationship in good_relationships:
        EntryRelationships(**relationship)

    bad_relationships = (
        {"references": {"data": [{"id": "dijkstra1968", "type": "structures"}]}},
        {"structures": {"data": [{"id": "dijkstra1968", "type": "references"}]}},
    )
    for relationship in bad_relationships:
        with pytest.raises(ValidationError):
            EntryRelationships(**relationship)


def test_advanced_relationships():
    """Make sure the rules for the base resource 'meta' field are upheld"""

    relationship = {
        "references": {
            "data": [
                {
                    "id": "dijkstra1968",
                    "type": "references",
                    "meta": {
                        "description": "Reference for the search algorithm Dijkstra."
                    },
                }
            ]
        }
    }
    EntryRelationships(**relationship)

    # Both `description` and `role` are OPTIONAL keys of `meta`
    relationships = (
        {
            "references": {
                "data": [{"id": "dijkstra1968", "type": "references", "meta": {}}]
            }
        },
        {
            "structures": {
                "data": [
                    {"id": "struct1", "type": "structures", "meta": {"role": "input"}}
                ]
            }
        },
    )
    for relationship in relationships:
        EntryRelationships(**relationship)

    relationship = {
        "references": {
            "data": [{"id": "dijkstra1968", "type": "references", "meta": {"role": 1}}]
        }
    }
    with pytest.raises(ValidationError):
        EntryRelationships(**relationship)


def test_entry_info_property_legacy_form():
    """The form with a single OPTIMADE data type as `type` (OPTIMADE < 1.2)"""
    prop = EntryInfoProperty(description="Number of elements", type="integer")
    assert prop.type == DataType.INTEGER
    assert EntryInfoProperty.resolve_data_type(prop.type) == DataType.INTEGER


def test_entry_info_property_definition_form():
    """The Property Definition form (OPTIMADE >= 1.2), from the specification example"""
    definition = {
        "$id": "urn:uuid:10a05e55-0c20-4f68-89ad-35a18eb7076f",
        "title": "Number of elements",
        "x-optimade-type": "integer",
        "type": ["integer", "null"],
        "description": "Number of different elements in the structure as an integer.",
        "examples": [3],
        "x-optimade-property": {"property-format": "1.2"},
        "x-optimade-unit": "dimensionless",
        "x-optimade-implementation": {
            "sortable": True,
            "query-support": "all mandatory",
        },
        "x-optimade-requirements": {
            "support": "should",
            "sortable": False,
            "query-support": "all mandatory",
        },
    }
    prop = EntryInfoProperty(**definition)
    assert prop.type == ["integer", "null"]
    assert prop.x_optimade_type == "integer"
    assert (
        EntryInfoProperty.resolve_data_type(prop.type, prop.x_optimade_type)
        == DataType.INTEGER
    )


@pytest.mark.parametrize(
    "type_,x_optimade_type,expected",
    [
        (["string", "null"], "timestamp", DataType.TIMESTAMP),
        (["number"], "float", DataType.FLOAT),
        (["array", "null"], "list", DataType.LIST),
        (["object", "null"], "dictionary", DataType.DICTIONARY),
        (["boolean"], "boolean", DataType.BOOLEAN),
        # Without a standard `x-optimade-type`, the JSON type is used
        (["number", "null"], None, DataType.FLOAT),
        (["string"], "_exmpl_quantity", DataType.STRING),
        # `unknown` gives no usable data type
        (["string", "null"], "unknown", None),
    ],
)
def test_entry_info_property_data_type(type_, x_optimade_type, expected):
    """The OPTIMADE data type is resolved from `x-optimade-type` and `type`"""
    prop = EntryInfoProperty(
        description="x", type=type_, **{"x-optimade-type": x_optimade_type}
    )
    assert (
        EntryInfoProperty.resolve_data_type(prop.type, prop.x_optimade_type) == expected
    )


@pytest.mark.parametrize(
    "type_,x_optimade_type",
    [
        ([], None),
        (["notatype", "null"], None),
        (["string", "integer"], None),
        (["string", "null", "null"], None),
        (["null"], None),
        (["string", "null"], "integer"),
        (["integer"], "float"),
    ],
)
def test_entry_info_property_bad_type(type_, x_optimade_type):
    """Malformed `type` lists, and lists that contradict `x-optimade-type`, are rejected"""
    with pytest.raises(ValidationError):
        EntryInfoProperty(
            description="x", type=type_, **{"x-optimade-type": x_optimade_type}
        )
