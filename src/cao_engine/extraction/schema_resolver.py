"""JSON Schema $ref Resolver

Resolves (dereferences) all $ref references in a JSON schema by expanding them inline.
This is required for Gemini API which doesn't support $ref keywords.

Example:
    BEFORE (with $ref):
    {
      "properties": {
        "documentId": {"$ref": "#/$defs/Identifier"}
      },
      "$defs": {
        "Identifier": {"type": "object", "properties": {"value": {"type": "string"}}}
      }
    }

    AFTER (resolved):
    {
      "properties": {
        "documentId": {"type": "object", "properties": {"value": {"type": "string"}}}
      }
    }
"""

import copy
from typing import Any


class SchemaResolver:
    """Resolves $ref references in JSON schemas."""

    def __init__(self, schema: dict[str, Any]):
        """Initialize with the full schema containing $defs.

        Args:
            schema: JSON schema dict with potential $defs section
        """
        self.schema = copy.deepcopy(schema)
        self.defs = schema.get("$defs", {})

    def resolve(self) -> dict[str, Any]:
        """Resolve all $ref references in the schema.

        Returns:
            Schema with all $ref expanded inline and unsupported keywords removed
        """
        # Start resolving from root
        resolved = self._resolve_node(self.schema)

        # Remove $defs section (no longer needed)
        if "$defs" in resolved:
            del resolved["$defs"]

        # Remove other unsupported keywords at root
        resolved = self._remove_unsupported_keywords(resolved)

        return resolved

    def _resolve_node(self, node: Any) -> Any:
        """Recursively resolve a node in the schema tree.

        Args:
            node: Can be dict, list, or primitive value

        Returns:
            Resolved node with all $ref expanded
        """
        if isinstance(node, dict):
            # Check if this node is a $ref
            if "$ref" in node:
                return self._resolve_ref(node["$ref"])

            # Otherwise, recursively resolve all properties
            resolved = {}
            for key, value in node.items():
                # Skip unsupported keywords
                if key in ["$schema", "$id", "title", "description", "examples"]:
                    continue

                resolved[key] = self._resolve_node(value)

            return resolved

        elif isinstance(node, list):
            # Resolve each item in the list
            return [self._resolve_node(item) for item in node]

        else:
            # Primitive value - return as-is
            return node

    def _resolve_ref(self, ref: str) -> dict[str, Any]:
        """Resolve a single $ref reference.

        Args:
            ref: Reference string like "#/$defs/Identifier"

        Returns:
            Resolved definition (with nested $refs also resolved)
        """
        # External file references (like "./../../condition.yaml") are not supported
        # Return empty object {} and let Gemini figure it out
        if not ref.startswith("#/"):
            # Skip external references - Gemini API doesn't support them
            return {"type": "object"}  # Return minimal valid schema

        # Split path: "#/$defs/Identifier" -> ["$defs", "Identifier"]
        path_parts = ref[2:].split("/")

        # Navigate to the definition
        current = self.schema
        for part in path_parts:
            if part not in current:
                # If definition not found, return minimal schema
                return {"type": "object"}
            current = current[part]

        # Make a copy and recursively resolve any nested $refs
        definition = copy.deepcopy(current)
        return self._resolve_node(definition)

    def _remove_unsupported_keywords(self, node: Any) -> Any:
        """Remove keywords not supported by Gemini API.

        Keywords to remove:
        - additionalProperties
        - $comment
        - $anchor
        - deprecated
        - const (Gemini doesn't support enum constraints with const)
        - oneOf (Gemini has limited support, simplify to first option)

        Args:
            node: Schema node

        Returns:
            Node with unsupported keywords removed
        """
        if isinstance(node, dict):
            # List of keywords to remove
            unsupported = ["additionalProperties", "$comment", "$anchor", "deprecated", "const", "discriminator"]

            # Special handling for oneOf - take first option only
            if "oneOf" in node and isinstance(node["oneOf"], list) and len(node["oneOf"]) > 0:
                # Replace node with first oneOf option
                first_option = node["oneOf"][0].copy()
                # Merge other properties from parent node
                for key, value in node.items():
                    if key != "oneOf" and key not in first_option:
                        first_option[key] = value
                node = first_option

            cleaned = {}
            for key, value in node.items():
                # Skip unsupported keywords AND fields starting with _ (metadata fields)
                if key not in unsupported and not key.startswith("_"):
                    cleaned[key] = self._remove_unsupported_keywords(value)

            return cleaned

        elif isinstance(node, list):
            return [self._remove_unsupported_keywords(item) for item in node]

        else:
            return node


def resolve_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Convenience function to resolve a schema.

    Args:
        schema: JSON schema with potential $ref and $defs

    Returns:
        Resolved schema with all $ref expanded inline

    Example:
        >>> from cao_engine.extraction.schema_resolver import resolve_schema
        >>> resolved = resolve_schema(SETU_SCHEMA)
    """
    resolver = SchemaResolver(schema)
    return resolver.resolve()
