"""Configuration-driven multi-agent collaboration orchestration."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


class OrchestrationConfig:
    def __init__(self, root: Path = ROOT):
        self.root = root

    def _read(self, relative: str) -> Any:
        with (self.root / relative).open(encoding="utf-8") as handle:
            return json.load(handle)

    def agents(self) -> list[str]:
        return self._read("config/agent-collaboration.json")["agents"]

    def collaboration(self) -> dict[str, Any]:
        return self._read("config/agent-collaboration.json")

    def schedules(self) -> dict[str, Any]:
        return self._read("config/schedules.json")

    def workflow(self, workflow_id: str = "requirement-to-release") -> dict[str, Any]:
        return self._read(f"config/workflows/{workflow_id}.json")

    def validate(self) -> list[str]:
        errors = []
        collaboration = self.collaboration()
        known = set(collaboration.get("agents", []))
        for agent in known:
            if not (self.root / "agents" / f"{agent}.md").is_file():
                errors.append(f"missing agent markdown: {agent}.md")
        workflow = self.workflow()
        stages = workflow.get("stages", [])
        ids = {stage.get("id") for stage in stages}
        for stage in stages:
            if stage.get("agent") and stage.get("agent") not in known:
                errors.append(f"unknown agent in stage: {stage.get('id')}")
            for agent in stage.get("parallel", []) + stage.get("optional", []):
                if agent not in known:
                    errors.append(f"unknown agent in stage: {stage.get('id')}")
            for field in ("on_success", "on_failure"):
                target = stage.get(field)
                if target and target not in ids:
                    errors.append(f"unknown {field} target: {target}")
        for job in self.schedules().get("jobs", []):
            if not job.get("id") or not job.get("event") or not isinstance(job.get("cron"), dict):
                errors.append("schedule jobs require id, event and cron")
            elif not {"hour", "minute"}.issubset(job["cron"]):
                errors.append(f"schedule missing hour/minute: {job.get('id')}")
        return errors

    def health(self) -> dict[str, Any]:
        errors = self.validate()
        return {"ok": not errors, "agents": self.agents(), "workflow": self.workflow()["id"], "errors": errors}

    def dispatch_project_manager_tasks(self) -> dict[str, Any]:
        """Inspect workflow progress and enqueue the next actionable agent task."""
        runtime = self.root / "runtime"
        runtime.mkdir(exist_ok=True)
        queue_file = runtime / "orchestration-tasks.json"
        try:
            queue = json.loads(queue_file.read_text(encoding="utf-8")) if queue_file.exists() else []
        except json.JSONDecodeError:
            queue = []
        active = next((item for item in queue if item.get("status") in {"queued", "in_progress"}), None)
        if active:
            return {"created": False, "reason": "active_task_exists", "task": active}
        workflow = self.workflow()
        completed = {item.get("stage") for item in queue if item.get("status") == "completed"}
        stage = next((item for item in workflow["stages"] if item.get("id") not in completed), None)
        if not stage:
            return {"created": False, "reason": "workflow_complete"}
        agents = stage.get("parallel") or stage.get("optional") or [stage.get("agent")]
        agents = [agent for agent in agents if agent]
        task = {"id": f"pm-{datetime.now().strftime('%Y%m%d%H%M%S')}", "stage": stage["id"], "agents": agents, "status": "queued", "created_at": datetime.now().isoformat(timespec="seconds"), "source": "project-manager-hourly"}
        queue.append(task)
        queue_file.write_text(json.dumps(queue[-200:], ensure_ascii=False, indent=2), encoding="utf-8")
        return {"created": True, "task": task}


orchestration_config = OrchestrationConfig()
