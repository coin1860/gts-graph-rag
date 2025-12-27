"""BOI (Back Office Integration) Knowledge Graph Schema.
Defines node types, relationship types, and extraction patterns.
"""

from typing import TypedDict


class GraphSchema(TypedDict):
    """Schema definition for knowledge graph extraction."""

    node_types: list[str]
    relationship_types: list[str]
    patterns: list[tuple[str, str, str]]


# BOI-specific node types
BOI_NODE_TYPES = [
    "Microservice",      # properties: type, category, version
    "Event",             # properties: type, format
    "Component",         # e.g., IM (Integration Middleware), HTS
    "Interface",         # properties: protocol, format
    "Country",           # properties: region, code
    "File",              # properties: format, encoding
    "DownstreamSystem",  # properties: type, protocol
    "Database",          # properties: type, name
    "Queue",             # properties: type, name
    "API",               # properties: method, path
]

# BOI-specific relationship types
BOI_RELATIONSHIP_TYPES = [
    "TRIGGERS",          # Event triggers processing
    "ROUTES_TO",         # Routing logic
    "CALLS",             # Service invocation
    "STORES_TO",         # Data persistence
    "GENERATES",         # Output generation
    "SENT_VIA",          # Communication channel
    "DEPLOYED_FOR",      # Country deployment
    "CONSUMES_FROM",     # Queue consumption
    "PUBLISHES_TO",      # Queue publishing
    "DEPENDS_ON",        # Service dependency
    "RECEIVES_FROM",     # Data reception
    "TRANSFORMS",        # Data transformation
]

# Extraction patterns: (source_type, relationship, target_type)
BOI_PATTERNS = [
    # Event-driven patterns
    ("Event", "TRIGGERS", "Microservice"),
    ("Microservice", "GENERATES", "Event"),

    # Routing patterns
    ("Microservice", "ROUTES_TO", "Component"),
    ("Component", "ROUTES_TO", "Microservice"),

    # Service communication
    ("Microservice", "CALLS", "Microservice"),
    ("Microservice", "CALLS", "API"),
    ("Microservice", "DEPENDS_ON", "Microservice"),

    # Data flow
    ("Microservice", "STORES_TO", "Database"),
    ("Microservice", "STORES_TO", "DownstreamSystem"),
    ("Microservice", "RECEIVES_FROM", "DownstreamSystem"),

    # File handling
    ("Microservice", "GENERATES", "File"),
    ("File", "SENT_VIA", "Interface"),

    # Queue patterns
    ("Microservice", "PUBLISHES_TO", "Queue"),
    ("Microservice", "CONSUMES_FROM", "Queue"),

    # Deployment
    ("Microservice", "DEPLOYED_FOR", "Country"),
]


# Default BOI schema
BOI_SCHEMA: GraphSchema = {
    "node_types": BOI_NODE_TYPES,
    "relationship_types": BOI_RELATIONSHIP_TYPES,
    "patterns": BOI_PATTERNS,
}


def get_schema_for_org(custom_schema: dict | None = None) -> GraphSchema:
    """Get the graph schema for an organization.

    Args:
        custom_schema: Optional custom schema override

    Returns:
        GraphSchema dict with node_types, relationship_types, and patterns

    """
    if custom_schema:
        return {
            "node_types": custom_schema.get("node_types", BOI_NODE_TYPES),
            "relationship_types": custom_schema.get("relationship_types", BOI_RELATIONSHIP_TYPES),
            "patterns": custom_schema.get("patterns", BOI_PATTERNS),
        }
    return BOI_SCHEMA


def validate_schema(schema: dict) -> tuple[bool, str]:
    """Validate a custom graph schema.

    Args:
        schema: Schema dict to validate

    Returns:
        Tuple of (is_valid, error_message)

    """
    required_keys = ["node_types", "relationship_types", "patterns"]

    for key in required_keys:
        if key not in schema:
            return False, f"Missing required key: {key}"

    if not isinstance(schema["node_types"], list):
        return False, "node_types must be a list"

    if not isinstance(schema["relationship_types"], list):
        return False, "relationship_types must be a list"

    if not isinstance(schema["patterns"], list):
        return False, "patterns must be a list"

    # Validate patterns format
    for i, pattern in enumerate(schema["patterns"]):
        if not isinstance(pattern, (list, tuple)) or len(pattern) != 3:
            return False, f"Pattern {i} must be a tuple of (source, relationship, target)"

        source, rel, target = pattern
        if source not in schema["node_types"]:
            return False, f"Pattern {i}: source '{source}' not in node_types"
        if rel not in schema["relationship_types"]:
            return False, f"Pattern {i}: relationship '{rel}' not in relationship_types"
        if target not in schema["node_types"]:
            return False, f"Pattern {i}: target '{target}' not in node_types"

    return True, ""
