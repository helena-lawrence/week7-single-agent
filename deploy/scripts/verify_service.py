"""Fail CI if ECS rolled the service back to a previous task revision."""
import json
import subprocess
import sys


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python verify_service.py cluster service expected_task_definition_arn")
    cluster, service, expected = sys.argv[1:]
    result = subprocess.run(
        ["aws", "ecs", "describe-services", "--cluster", cluster, "--services", service,
         "--output", "json", "--no-cli-pager"],
        check=True, text=True, capture_output=True,
    )
    data = json.loads(result.stdout)
    if data.get("failures") or not data.get("services"):
        raise SystemExit(f"Cannot read ECS service: {data.get('failures')}")
    svc = data["services"][0]
    actual = svc["taskDefinition"]
    if actual != expected:
        raise SystemExit(f"ECS task revision mismatch (possibly rolled back): expected {expected}; actual {actual}")
    if svc.get("runningCount", 0) < svc.get("desiredCount", 0):
        raise SystemExit("ECS service has fewer running tasks than desired")
    print(f"Verified ECS {service} at {actual}; running {svc['runningCount']}/{svc['desiredCount']}")


if __name__ == "__main__":
    main()
