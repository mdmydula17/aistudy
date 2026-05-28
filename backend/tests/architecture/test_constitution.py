import ast
import importlib
import pkgutil
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent.parent / "app"

FORBIDDEN_IMPORTS = {
    "app.api": {"app.crud", "app.models"},
    "app.graph": {"fastapi"},
    "app.ingestion": {"app.crud", "app.models", "app.api", "fastapi"},
    "app.exporter": {"app.crud", "app.models", "app.api", "fastapi"},
}


def _collect_python_files(package_path: Path) -> list[Path]:
    files = []
    for p in package_path.rglob("*.py"):
        if p.name == "__init__.py" and p.stat().st_size == 0:
            continue
        files.append(p)
    return files


def _get_module_imports(file_path: Path) -> list[str]:
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _resolve_package_name(file_path: Path) -> str:
    rel = file_path.relative_to(APP_ROOT.parent)
    parts = list(rel.with_suffix("").parts)
    return ".".join(parts)


class TestASTConstitution:
    def test_api_must_not_import_crud_or_models(self):
        api_dir = APP_ROOT / "api"
        if not api_dir.exists():
            return
        for f in _collect_python_files(api_dir):
            imports = _get_module_imports(f)
            for imp in imports:
                assert not imp.startswith("app.crud"), (
                    f"CONSTITUTION VIOLATION: {f.name} imports 'app.crud' "
                    f"(api layer must not access crud directly)"
                )
                assert not imp.startswith("app.models"), (
                    f"CONSTITUTION VIOLATION: {f.name} imports 'app.models' "
                    f"(api layer must not access models directly)"
                )

    def test_graph_must_not_import_fastapi(self):
        graph_dir = APP_ROOT / "graph"
        if not graph_dir.exists():
            return
        for f in _collect_python_files(graph_dir):
            imports = _get_module_imports(f)
            for imp in imports:
                assert not imp.startswith("fastapi"), (
                    f"CONSTITUTION VIOLATION: {f.name} imports 'fastapi' "
                    f"(graph layer must not depend on fastapi)"
                )

    def test_schemas_must_be_zero_dependency(self):
        schemas_dir = APP_ROOT / "schemas"
        if not schemas_dir.exists():
            return
        allowed_prefixes = ("pydantic", "typing", "datetime", "enum", "app.schemas")
        for f in _collect_python_files(schemas_dir):
            imports = _get_module_imports(f)
            for imp in imports:
                if imp.startswith("app.schemas"):
                    continue
                is_allowed = any(imp.startswith(p) for p in allowed_prefixes)
                assert is_allowed, (
                    f"CONSTITUTION VIOLATION: {f.name} imports '{imp}' "
                    f"(schemas must be zero-dependency pure Pydantic definitions)"
                )

    def test_crawler_must_not_import_business_layers(self):
        crawler_dir = APP_ROOT / "crawler"
        if not crawler_dir.exists():
            return
        forbidden = ("app.crud", "app.graph", "app.api", "app.models")
        for f in _collect_python_files(crawler_dir):
            imports = _get_module_imports(f)
            for imp in imports:
                for prefix in forbidden:
                    assert not imp.startswith(prefix), (
                        f"CONSTITUTION VIOLATION: {f.name} imports '{imp}' "
                        f"(crawler must not depend on business layers)"
                    )

    def test_crud_must_not_import_api_or_graph(self):
        crud_dir = APP_ROOT / "crud"
        if not crud_dir.exists():
            return
        forbidden = ("app.api", "app.graph", "app.crawler")
        for f in _collect_python_files(crud_dir):
            imports = _get_module_imports(f)
            for imp in imports:
                for prefix in forbidden:
                    assert not imp.startswith(prefix), (
                        f"CONSTITUTION VIOLATION: {f.name} imports '{imp}' "
                        f"(crud must not depend on api/graph/crawler)"
                    )

    def test_ingestion_must_not_import_business_layers(self):
        ingestion_dir = APP_ROOT / "ingestion"
        if not ingestion_dir.exists():
            return
        forbidden = ("app.crud", "app.models", "app.api", "fastapi")
        for f in _collect_python_files(ingestion_dir):
            imports = _get_module_imports(f)
            for imp in imports:
                for prefix in forbidden:
                    assert not imp.startswith(prefix), (
                        f"CONSTITUTION VIOLATION: {f.name} imports '{imp}' "
                        f"(ingestion must not depend on crud/models/api)"
                    )

    def test_exporter_must_not_import_business_layers(self):
        exporter_dir = APP_ROOT / "exporter"
        if not exporter_dir.exists():
            return
        forbidden = ("app.crud", "app.models", "app.api", "fastapi")
        for f in _collect_python_files(exporter_dir):
            imports = _get_module_imports(f)
            for imp in imports:
                for prefix in forbidden:
                    assert not imp.startswith(prefix), (
                        f"CONSTITUTION VIOLATION: {f.name} imports '{imp}' "
                        f"(exporter must not depend on crud/models/api)"
                    )
