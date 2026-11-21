#!/usr/bin/env python3
"""Utilitaires partagés pour la génération et la validation de catalogues Forgearr."""
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

OTHER_TYPES = {
    "preset",
    "resource.font",
    "resource.image",
    "resource.audio",
    "resource.subtitle",
    "resource.color",
    "resource.language",
    "resource.template",
}
ALLOWED_TYPES = {"app", "plugin", "block", "flow", "script", "pack"} | OTHER_TYPES
ALLOWED_DEPENDENCIES = {
    "plugin": {"app"},
    "flow": {"plugin", "script"} | OTHER_TYPES,
    "pack": {"app", "plugin", "flow", "script"} | OTHER_TYPES,
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
    "script": 4,
    "preset": 5,
    "resource.font": 6,
    "resource.image": 7,
    "resource.audio": 8,
    "resource.subtitle": 9,
    "resource.color": 10,
    "resource.language": 11,
    "resource.template": 12,
    "pack": 13,
}


def is_safe_relative(raw: object) -> bool:
    """Vérifie qu'un chemin est relatif, sans traversée ni caractères de contrôle."""
    if not isinstance(raw, str) or not raw or raw.startswith("/") or "\\" in raw or "\x00" in raw:
        return False
    parts = Path(raw).parts
    return bool(parts) and all(part not in ("", ".", "..") for part in parts)


MAX_ICON_BYTES = 16 * 1024
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ICON_ELEMENTS = {"g", "path", "circle", "ellipse", "rect", "line", "polyline", "polygon"}
ICON_ATTRIBUTES = {
    "viewBox", "width", "height", "fill", "stroke", "stroke-width", "stroke-linecap",
    "stroke-linejoin", "stroke-miterlimit", "stroke-dasharray", "stroke-opacity",
    "fill-opacity", "fill-rule", "clip-rule", "opacity", "transform", "d", "cx", "cy", "r",
    "rx", "ry", "x", "y", "x1", "y1", "x2", "y2", "points",
}
ICON_FORBIDDEN_VALUE_CHARS = set(":&<>\\")


def is_icon_path(raw: object) -> bool:
    """Chemin relatif sûr d'un fichier d'icône : il se termine par .svg."""
    return is_safe_relative(raw) and str(raw).endswith(".svg")


def svg_icon_problems(text: str) -> list[str]:
    """Liste blanche des icônes SVG (ADR 0024 de Forgearr) : même règle que le central.

    Seuls des éléments de dessin et des attributs de géométrie, de remplissage et de trait sont
    admis, sans texte, style, lien, script ni gestionnaire d'événement.
    """
    if len(text.encode("utf-8")) > MAX_ICON_BYTES:
        return [f"plus de {MAX_ICON_BYTES} octets"]
    if "<!" in text or "<?" in text:
        return ["déclaration, commentaire ou instruction interdits"]
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        return [f"SVG mal formé ({error})"]
    namespace = "{" + SVG_NAMESPACE + "}"
    if root.tag != namespace + "svg":
        return ["l'élément racine doit être svg dans l'espace de noms SVG (xmlns)"]
    problems: list[str] = []
    for element in root.iter():
        if element is not root:
            tag = element.tag if isinstance(element.tag, str) else ""
            name = tag[len(namespace):] if tag.startswith(namespace) else tag
            if name == "svg":
                problems.append("svg imbriqué")
            elif name not in ICON_ELEMENTS:
                problems.append(f"élément interdit « {name} »")
        for key, value in element.attrib.items():
            if key not in ICON_ATTRIBUTES:
                problems.append(f"attribut interdit « {key} »")
            elif ICON_FORBIDDEN_VALUE_CHARS & set(value):
                problems.append(f"valeur interdite pour « {key} »")
        if (element.text or "").strip() or (element.tail or "").strip():
            problems.append("texte interdit")
    return problems


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


# --- Variables exposées par les plugins (ADR 0025 de Forgearr) -------------------------------
# Ces règles reproduisent `validate_exposed` et `validate_requirements` du central
# (shared/src/exposed_variables.rs) : le central revalide à la synchronisation et écarte tout
# contrat invalide, cette vérification évite de publier une opération qu'il refuserait.

RESERVED_NAMESPACES = {"nodes"}
MAX_EXPOSED_VARIABLES = 128
MAX_REQUIREMENTS = 32
MAX_PATH_SEGMENTS = 8
MAX_NAME_LEN = 64
MAX_DEPRECATION_LEN = 300
EXPOSED_KINDS = {"text", "multiline", "number", "boolean", "choice"}
IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")
CONTRACT_VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
# Segment de chemin dans `mediaInfo` : clé, éventuellement suivie de `[*]`, `[n]` ou `[clé=valeur]`.
PATH_SEGMENT_RE = re.compile(
    r"^[A-Za-z0-9_-]+(\[(\*|[0-9]+|@?[A-Za-z0-9_-]+=[A-Za-z0-9_ -]+)\])?$"
)
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")
SELECTOR_RE = re.compile(r"^([^\[]*)\[(.*)\]$")


def _literal_matches(value: Any, expected: str) -> bool:
    expected = expected.strip()
    if isinstance(value, bool):
        return str(value).lower() == expected.lower()
    if isinstance(value, str):
        return value.lower() == expected.lower()
    if isinstance(value, (int, float)):
        return str(value) == expected
    return False


def _collect_values(current: Any, segments: list[str], out: list[Any]) -> None:
    if not segments:
        out.append(current)
        return
    head, rest = segments[0], segments[1:]
    selector = SELECTOR_RE.match(head)
    if selector:
        key, inside = selector.group(1), selector.group(2)
        target = current if key == "" else (current.get(key) if isinstance(current, dict) else None)
        if not isinstance(target, list):
            return
        if inside == "*":
            for item in target:
                _collect_values(item, rest, out)
        elif "=" in inside:
            filter_key, filter_value = inside.split("=", 1)
            filter_key = filter_key.strip()
            for item in target:
                if isinstance(item, dict) and filter_key in item and _literal_matches(item[filter_key], filter_value):
                    _collect_values(item, rest, out)
        elif inside.isdigit() and int(inside) < len(target):
            _collect_values(target[int(inside)], rest, out)
        return
    if isinstance(current, dict) and head in current:
        _collect_values(current[head], rest, out)


def query_values(root: Any, query: str) -> list[Any]:
    """Valeurs désignées par une requête (`a.b`, `arr[*]`, `arr[0]`, `arr[type=video].codec`).

    Reproduit `extract_json_values` du central, que le moteur utilise pour lire une variable exposée.
    """
    out: list[Any] = []
    _collect_values(root, [s for s in query.split(".") if s], out)
    return out


def first_value(root: Any, query: str) -> Any:
    """Première valeur non nulle désignée par la requête, ou None."""
    return next((v for v in query_values(root, query) if v is not None), None)


def contract_major(version: object) -> int | None:
    if not isinstance(version, str) or not CONTRACT_VERSION_RE.match(version):
        return None
    return int(version.split(".")[0])


def _is_dotted_identifier(name: object) -> bool:
    if not isinstance(name, str):
        return False
    parts = name.split(".")
    return 1 <= len(parts) <= MAX_PATH_SEGMENTS and all(
        len(part) <= MAX_NAME_LEN and IDENTIFIER_RE.match(part) for part in parts
    )


def _is_media_path(path: object) -> bool:
    if not isinstance(path, str):
        return False
    parts = path.split(".")
    return 1 <= len(parts) <= MAX_PATH_SEGMENTS and all(PATH_SEGMENT_RE.match(part) for part in parts)


def _names_overlap(a: str, b: str) -> bool:
    return a.startswith(b + ".") or b.startswith(a + ".")


def exposes_problems(exposes: object) -> list[str]:
    """Problèmes d'un bloc `exposes` ; vide s'il serait accepté par le central."""
    if not isinstance(exposes, dict):
        return ["exposes doit être un objet"]
    namespace = exposes.get("namespace")
    if not isinstance(namespace, str) or len(namespace) > MAX_NAME_LEN or not IDENTIFIER_RE.match(namespace):
        return [f"espace de noms invalide ({namespace!r})"]
    if namespace in RESERVED_NAMESPACES:
        return [f"espace de noms réservé ({namespace!r})"]
    if contract_major(exposes.get("contractVersion")) is None:
        return [f"contractVersion invalide ({exposes.get('contractVersion')!r}) : MAJEUR.MINEUR.CORRECTIF attendu"]
    variables = exposes.get("variables", [])
    if not isinstance(variables, list):
        return ["exposes.variables doit être une liste"]
    if len(variables) > MAX_EXPOSED_VARIABLES:
        return [f"au plus {MAX_EXPOSED_VARIABLES} variables exposées"]
    problems: list[str] = []
    seen: list[str] = []
    for variable in variables:
        name = variable.get("name") if isinstance(variable, dict) else None
        if not _is_dotted_identifier(name):
            problems.append(f"nom de variable exposée invalide ({name!r})")
            continue
        if not _is_media_path(variable.get("path")):
            problems.append(f"chemin invalide pour la variable exposée {name!r} ({variable.get('path')!r})")
        if variable.get("type", "text") not in EXPOSED_KINDS:
            problems.append(f"type invalide pour la variable exposée {name!r} (un secret ne peut pas être exposé)")
        if name in seen:
            problems.append(f"variable exposée {name!r} déclarée deux fois")
        elif any(_names_overlap(name, earlier) for earlier in seen):
            problems.append(f"{name!r} est à la fois une valeur et un groupe d'autres variables")
        seen.append(name)
    names = {v.get("name") for v in variables if isinstance(v, dict)}
    for variable in variables:
        problem = _deprecation_problem(variable, names)
        if problem:
            problems.append(problem)
    return problems


def _deprecation_problem(variable: object, names: set[Any]) -> str | None:
    """`deprecated` : message non vide borné ; `replacedBy` exige `deprecated` et désigne une autre variable du contrat."""
    if not isinstance(variable, dict) or not _is_dotted_identifier(variable.get("name")):
        return None
    name = variable["name"]
    message = variable.get("deprecated")
    replacement = variable.get("replacedBy")
    message_ok = message is None or (
        isinstance(message, str) and bool(message.strip()) and len(message) <= MAX_DEPRECATION_LEN
    )
    replacement_ok = replacement is None or (
        message is not None and replacement != name and replacement in names
    )
    if message_ok and replacement_ok:
        return None
    return (
        f"dépréciation invalide pour la variable exposée {name!r} (message non vide de "
        f"{MAX_DEPRECATION_LEN} caractères au plus ; replacedBy exige deprecated et désigne une autre variable du contrat)"
    )


def requirements_problems(requirements: object) -> list[str]:
    """Problèmes d'une liste `runtime.requires` d'un script ; vide si le central l'accepterait."""
    if not isinstance(requirements, list):
        return ["requires doit être une liste"]
    if len(requirements) > MAX_REQUIREMENTS:
        return [f"au plus {MAX_REQUIREMENTS} dépendances"]
    problems: list[str] = []
    seen: set[str] = set()
    bound: dict[str, tuple[Any, Any]] = {}
    for requirement in requirements:
        entry = requirement if isinstance(requirement, dict) else {}
        reference = entry.get("variable")
        if not _is_dotted_identifier(reference) or "." not in reference:
            problems.append(f"référence de dépendance invalide ({reference!r}) : espace.nom attendu")
            continue
        if reference in seen:
            problems.append(f"dépendance {reference!r} déclarée deux fois")
        seen.add(reference)
        # Un espace de noms ne se lie qu'à un fournisseur et à une version majeure (le script lit une seule exposition).
        namespace = reference.split(".")[0]
        contract = (entry.get("provider"), entry.get("contractMajor", 1))
        if bound.setdefault(namespace, contract) != contract:
            problems.append(
                f"l'espace de noms {namespace!r} est lié à deux fournisseurs ou à deux versions de contrat différents"
            )
        provider = entry.get("provider")
        if not isinstance(provider, str) or not SAFE_ID_RE.match(provider) or len(provider) > MAX_NAME_LEN:
            problems.append(f"fournisseur invalide pour {reference!r} ({provider!r})")
        repository = entry.get("repository")
        if repository is not None:
            index_url = repository.get("indexUrl") if isinstance(repository, dict) else None
            repo_id = repository.get("id") if isinstance(repository, dict) else None
            if (
                not isinstance(repo_id, str)
                or not SAFE_ID_RE.match(repo_id)
                or not isinstance(index_url, str)
                or not index_url.startswith(("https://", "http://"))
                or not index_url.endswith("/index.json")
                or any(ch.isspace() for ch in index_url)
            ):
                problems.append(f"dépôt de dépendance invalide pour {reference!r}")
    return problems


def exposes_breaking_changes(old: object, new: object) -> list[str]:
    """Changements cassants entre deux versions d'un `exposes` : variable retirée, renommée ou de type changé.

    Chacun impose une montée de version majeure du contrat (ADR 0025). Retirer une variable déjà dépréciée
    dans la version précédente n'en est pas un : c'est la fin de la fenêtre de dépréciation.
    """
    if not isinstance(old, dict) or not isinstance(new, dict):
        return []
    new_by_name = {
        v.get("name"): v for v in new.get("variables", []) if isinstance(v, dict)
    }
    changes: list[str] = []
    for variable in old.get("variables", []):
        if not isinstance(variable, dict):
            continue
        name = variable.get("name")
        current = new_by_name.get(name)
        if current is None:
            if not variable.get("deprecated"):
                changes.append(f"variable {name!r} retirée ou renommée sans avoir été dépréciée")
        elif current.get("type", "text") != variable.get("type", "text"):
            changes.append(f"variable {name!r} : type {variable.get('type', 'text')!r} → {current.get('type', 'text')!r}")
    if old.get("namespace") != new.get("namespace"):
        changes.append(f"espace de noms {old.get('namespace')!r} → {new.get('namespace')!r}")
    return changes
