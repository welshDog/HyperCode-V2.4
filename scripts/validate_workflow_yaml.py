from pathlib import Path
import sys
import yaml

class UniqueLoader(yaml.SafeLoader):
    pass

def construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"found duplicate key: {key}", key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping

UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
)

root = Path(__file__).resolve().parents[1]
failed = False
for path in sorted((root / ".github" / "workflows").glob("*.y*ml")):
    try:
        yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)
    except Exception as exc:
        failed = True
        print(f"{path}: {exc}")
if failed:
    sys.exit(1)
print("workflow-yaml-valid")
