#!/usr/bin/env python3
"""Utilitaires partagés pour la génération et la validation de catalogues Flux de Fichiers."""
import hashlib
import json
import re
from pathlib import Path
from typing import Any

OTHER_TYPES = {
    "preset",
    "resource.font",
    "resource.image",
    "resource.audio",
    "resource.color",
    "resource.language",
    "resource.template",
}
ALLOWED_TYPES = {"app", "plugin", "block", "flow", "pack"} | OTHER_TYPES
ALLOWED_DEPENDENCIES = {
    "plugin": {"app"},
    "flow": {"plugin"} | OTHER_TYPES,
    "pack": {"app", "plugin", "flow"} | OTHER_TYPES,
}

ID_RE = re.compile(r"^[a-z0-9]+([.-][a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
)
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
OCTAL_MODE_RE = re.compile(r"^0[0-7]{3}$")
OP_ID_RE = re.compile(r"^[a-z0-9]+([._-][a-z0-9]+)*$")
BINARY_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")

SECTION_ORDER = {
    "app": 0,
    "plugin": 1,
    "block": 2,
    "flow": 3,
    "preset": 4,
    "resource.font": 5,
    "resource.image": 6,
    "resource.audio": 7,
    "resource.color": 8,
    "resource.language": 9,
    "resource.template": 10,
    "pack": 11,
}


def is_safe_relative(raw: object) -> bool:
    """Vérifie qu'un chemin est relatif, sans traversée ni caractères de contrôle."""
    if not isinstance(raw, str) or not raw or raw.startswith("/") or "\\" in raw or "\x00" in raw:
        return False
    parts = Path(raw).parts
    return bool(parts) and all(part not in ("", ".", "..") for part in parts)


def sha256_file(path: Path) -> str:
    """Calcule l'empreinte SHA-256 hexadécimale d'un fichier."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    """Lit et décode un fichier JSON UTF-8."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    """Écrit un document JSON formaté de manière déterministe."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class LocalSchemaValidator:
    """Validateur JSON Schema hors-réseau : utilise `jsonschema` si disponible, sinon repli stdlib."""

    def __init__(self, schema_dir: Path) -> None:
        self.schema_dir = schema_dir
        self.schemas: dict[str, dict[str, Any]] = {}
        self.by_id: dict[str, dict[str, Any]] = {}
        for path in sorted(schema_dir.glob("*.json")):
            doc = load_json(path)
            if isinstance(doc, dict):
                self.schemas[path.name] = doc
                if isinstance(doc.get("$id"), str):
                    self.by_id[doc["$id"]] = doc
        self._registry = self._build_jsonschema_registry()

    def has_jsonschema(self) -> bool:
        return self._registry is not None

    def _build_jsonschema_registry(self):
        try:
            import jsonschema  # noqa: F401
            from referencing import Registry, Resource
            from referencing.jsonschema import DRAFT202012
        except ImportError:
            return None

        resources = []
        for name, doc in self.schemas.items():
            res = Resource.from_contents(doc, default_specification=DRAFT202012)
            if isinstance(doc.get("$id"), str):
                resources.append((doc["$id"], res))
            resources.append((name, res))
        return Registry().with_resources(resources)

    def check_schemas_compile(self) -> list[str]:
        errors: list[str] = []
        if self._registry is None:
            return errors
        from jsonschema import Draft202012Validator

        for name, doc in self.schemas.items():
            try:
                Draft202012Validator.check_schema(doc)
            except Exception as exc:  # pragma: no cover - dépend de jsonschema
                errors.append(f"schema/{name} : schéma invalide ({exc})")
        return errors

    def validate(self, schema_name: str, instance: Any) -> list[str]:
        if schema_name not in self.schemas:
            return [f"schéma introuvable : {schema_name}"]
        if self._registry is not None:
            from jsonschema import Draft202012Validator

            validator = Draft202012Validator(self.schemas[schema_name], registry=self._registry)
            errs = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
            return [
                f"{'/'.join(str(p) for p in err.path) or '<racine>'} : {err.message}"
                for err in errs[:5]
            ]
        return self._validate_stdlib(self.schemas[schema_name], self.schemas[schema_name], instance, "<racine>")

    def _resolve_ref(self, root_schema: dict[str, Any], ref: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
        if "#" in ref:
            file_part, pointer = ref.split("#", 1)
        else:
            file_part, pointer = ref, ""
        target_root = root_schema if not file_part else self.schemas.get(file_part) or self.by_id.get(file_part)
        if not isinstance(target_root, dict):
            return None
        node: Any = target_root
        if pointer.startswith("/"):
            for raw_seg in pointer[1:].split("/"):
                seg = raw_seg.replace("~1", "/").replace("~0", "~")
                if isinstance(node, dict) and seg in node:
                    node = node[seg]
                else:
                    return None
        return (target_root, node) if isinstance(node, dict) else None

    @staticmethod
    def _matches_type(value: Any, expected: str) -> bool:
        if expected == "object":
            return isinstance(value, dict)
        if expected == "array":
            return isinstance(value, list)
        if expected == "string":
            return isinstance(value, str)
        if expected == "boolean":
            return isinstance(value, bool)
        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected == "null":
            return value is None
        return True

    def _validate_stdlib(
        self, root_schema: dict[str, Any], schema: dict[str, Any], value: Any, path: str
    ) -> list[str]:
        errors: list[str] = []
        if "$ref" in schema:
            resolved = self._resolve_ref(root_schema, schema["$ref"])
            if resolved is None:
                return [f"{path} : $ref introuvable ({schema['$ref']})"]
            return self._validate_stdlib(resolved[0], resolved[1], value, path)

        if "const" in schema and value != schema["const"]:
            errors.append(f"{path} : doit valoir {schema['const']!r}")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path} : valeur {value!r} hors enum {schema['enum']!r}")
        if "type" in schema:
            types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(self._matches_type(value, t) for t in types):
                errors.append(f"{path} : type attendu {schema['type']!r}, reçu {type(value).__name__}")
                return errors

        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                errors.append(f"{path} : longueur < {schema['minLength']}")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                errors.append(f"{path} : longueur > {schema['maxLength']}")
            if "pattern" in schema and not re.search(schema["pattern"], value):
                errors.append(f"{path} : ne respecte pas le motif {schema['pattern']!r}")

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path} : valeur < {schema['minimum']}")
            if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
                errors.append(f"{path} : valeur <= {schema['exclusiveMinimum']}")
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(f"{path} : valeur > {schema['maximum']}")

        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                errors.append(f"{path} : moins de {schema['minItems']} élément(s)")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                errors.append(f"{path} : plus de {schema['maxItems']} élément(s)")
            if schema.get("uniqueItems"):
                encoded = [json.dumps(x, sort_keys=True) for x in value]
                if len(encoded) != len(set(encoded)):
                    errors.append(f"{path} : éléments en double interdits")
            if isinstance(schema.get("items"), dict):
                for idx, item in enumerate(value):
                    errors.extend(self._validate_stdlib(root_schema, schema["items"], item, f"{path}[{idx}]"))

        if isinstance(value, dict):
            for req in schema.get("required", []):
                if req not in value:
                    errors.append(f"{path} : champ requis manquant ({req})")
            if "maxProperties" in schema and len(value) > schema["maxProperties"]:
                errors.append(f"{path} : plus de {schema['maxProperties']} propriétés")
            props = schema.get("properties", {})
            addl = schema.get("additionalProperties", True)
            prop_names_schema = schema.get("propertyNames")
            for k, v in value.items():
                child_path = f"{path}/{k}" if path != "<racine>" else k
                if isinstance(prop_names_schema, dict):
                    errors.extend(self._validate_stdlib(root_schema, prop_names_schema, k, f"{child_path}(key)"))
                if k in props:
                    errors.extend(self._validate_stdlib(root_schema, props[k], v, child_path))
                elif addl is False:
                    errors.append(f"{path} : propriété non autorisée ({k})")
                elif isinstance(addl, dict):
                    errors.extend(self._validate_stdlib(root_schema, addl, v, child_path))
            for dep_key, dep_reqs in schema.get("dependentRequired", {}).items():
                if dep_key in value:
                    for req in dep_reqs:
                        if req not in value:
                            errors.append(f"{path} : {req} requis quand {dep_key} est présent")

        if "oneOf" in schema:
            branch_errors = [self._validate_stdlib(root_schema, b, value, path) for b in schema["oneOf"]]
            valid_count = sum(1 for be in branch_errors if not be)
            if valid_count != 1:
                sample = branch_errors[0][0] if branch_errors and branch_errors[0] else "aucune branche valide"
                errors.append(f"{path} : doit correspondre à exactement 1 schéma oneOf ({valid_count} valide(s), ex: {sample})")

        if "anyOf" in schema:
            branch_errors = [self._validate_stdlib(root_schema, b, value, path) for b in schema["anyOf"]]
            if not any(not be for be in branch_errors):
                errors.append(f"{path} : ne correspond à aucune branche anyOf")

        for sub in schema.get("allOf", []):
            errors.extend(self._validate_stdlib(root_schema, sub, value, path))

        if "if" in schema:
            if not self._validate_stdlib(root_schema, schema["if"], value, path):
                if "then" in schema:
                    errors.extend(self._validate_stdlib(root_schema, schema["then"], value, path))
            elif "else" in schema:
                errors.extend(self._validate_stdlib(root_schema, schema["else"], value, path))

        return errors
