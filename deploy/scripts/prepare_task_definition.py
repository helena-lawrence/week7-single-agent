"""Remove ECS read-only response fields before registering a new revision.

Usage: python prepare_task_definition.py input.json output.json required_container
"""
import json
import sys
from pathlib import Path

ALLOWED = {
    "family", "taskRoleArn", "executionRoleArn", "networkMode", "containerDefinitions",
    "volumes", "placementConstraints", "requiresCompatibilities", "cpu", "memory",
    "tags", "pidMode", "ipcMode", "proxyConfiguration", "inferenceAccelerators",
    "ephemeralStorage", "runtimePlatform", "enableFaultInjection"
}


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python prepare_task_definition.py input.json output.json required_container")
    source, destination, expected_name = sys.argv[1:]
    src = json.loads(Path(source).read_text(encoding="utf-8"))
    clean = {k: v for k, v in src.items() if k in ALLOWED and v is not None}
    names = {c.get("name") for c in clean.get("containerDefinitions", [])}
    if expected_name not in names:
        raise SystemExit(f"Expected ECS container {expected_name!r}; found {sorted(str(n) for n in names)}")
    if "FARGATE" not in clean.get("requiresCompatibilities", []):
        raise SystemExit("Task definition is not marked compatible with FARGATE")
    Path(destination).write_text(json.dumps(clean, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {destination}; containers: {', '.join(sorted(names))}")


if __name__ == "__main__":
    main()
