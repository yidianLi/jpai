"""Run a configured workflow and persist every stage artifact."""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from .orchestration import orchestration_config
from ..services.llm_service import LLMService


def _input(root: Path) -> str:
    folder = root / "docs" / "requirements"
    files = sorted(folder.glob("**/*")) if folder.exists() else []
    return "\n\n".join(f"## {p.name}\n{p.read_text(encoding='utf-8')}" for p in files if p.is_file()) or "请基于当前项目 README 和工作流配置，提出待办需求。"


async def run_workflow(workflow_id: str = "requirement-to-release") -> dict:
    root = orchestration_config.root
    task_id = f"task-{datetime.now():%Y%m%d-%H%M%S}"
    run = root / ".ai-agents" / "runs" / task_id
    (run / "input").mkdir(parents=True)
    (run / "outputs").mkdir()
    (run / "logs").mkdir()
    source = _input(root)
    (run / "input" / "requirements.md").write_text(source, encoding="utf-8")
    state = {"task_id": task_id, "workflow": workflow_id, "status": "running", "stages": []}
    (run / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    previous = source
    needs_attention = False
    llm = LLMService()
    for stage in orchestration_config.workflow(workflow_id)["stages"]:
        agents = stage.get("parallel") or stage.get("optional") or [stage.get("agent")]
        agents = [a for a in agents if a]
        for agent in agents:
            prompt_file = root / "agents" / f"{agent}.md"
            prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
            output = await llm.chat(f"上游产物:\n{previous}\n\n请按你的角色完成当前阶段，输出可交接的 Markdown 产物。", prompt)
            if not output:
                needs_attention = True
                output = f"# {stage['id']}\n\n模型未配置或不可用，等待人工处理。\n"
            target = run / "outputs" / f"{stage['id']}-{agent}.md"
            target.write_text(output, encoding="utf-8")
            previous = output
            state["stages"].append({"stage": stage["id"], "agent": agent, "status": "succeeded", "output": str(target.relative_to(run))})
            (run / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    state["status"] = "waiting_approval" if needs_attention else "succeeded"
    report = f"# Workflow Report\n\n- Task: `{task_id}`\n- Status: {state['status']}\n- Stages: {len(state['stages'])}\n"
    (run / "final-report.md").write_text(report, encoding="utf-8")
    (run / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"task_id": task_id, "status": state["status"], "run_dir": str(run)}


def run_workflow_sync(workflow_id: str = "requirement-to-release"):
    return asyncio.run(run_workflow(workflow_id))
