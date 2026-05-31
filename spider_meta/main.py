import json
import logging
import uuid
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from spider_meta.core.pipeline_orchestrator import PipelineOrchestrator
from spider_meta.core.dag_engine import DAGEngine
from spider_meta.core.worker_dispatcher import WorkerDispatcher
from spider_meta.config import check_hardware_limits
from spider_meta.modules.knowledge_retriever import KnowledgeRetriever
from spider_meta.modules.experience_manager import ExperienceManager
from spider_meta.services.llm_service import LLMService
from spider_meta.monitoring.metrics import metrics
from spider_meta.cost_guard import budget_mgr
from spider_meta.agents import router, get_local_agent, get_cloud_agent

# ============================================================
# Agent Router — 多智能体调度 API
# ============================================================

class RouterRouteRequest(BaseModel):
    task: str
    preferred_role: str = ""
    force_tier: str = ""       # "local" / "cloud" / ""


class RouterExecuteRequest(BaseModel):
    task: str
    preferred_role: str = ""
    force_tier: str = ""


class AgentExecuteRequest(BaseModel):
    task: str
    role: str
    tier: str = "auto"         # "local" / "cloud" / "auto"


@app.post("/router/route")
async def router_route(req: RouterRouteRequest):
    """路由决策：根据任务内容返回最优 Agent 分配"""
    result = router.route(
        task=req.task,
        preferred_role=req.preferred_role or None,
        force_tier=req.force_tier or None,
    )
    result["task"] = req.task
    return result


@app.post("/router/execute")
async def router_execute(req: RouterExecuteRequest):
    """一键路由 + 执行"""
    # 路由
    decision = router.route(
        task=req.task,
        preferred_role=req.preferred_role or None,
        force_tier=req.force_tier or None,
    )

    tier = decision["tier"]
    role = decision["role"]

    # 执行
    if tier == "local":
        agent = get_local_agent(role)
        exec_result = await agent.execute(req.task)
    else:
        agent = get_cloud_agent(role)
        exec_result = await agent.execute(req.task)

    return {
        "routing": decision,
        "execution": exec_result,
    }


@app.post("/agents/execute")
async def agent_execute(req: AgentExecuteRequest):
    """直接执行指定角色"""
    if req.tier == "local":
        agent = get_local_agent(req.role)
    elif req.tier == "cloud":
        agent = get_cloud_agent(req.role)
    else:
        # auto → 路由决策
        decision = router.route(req.task, preferred_role=req.role)
        if decision["tier"] == "local":
            agent = get_local_agent(decision["role"])
        else:
            agent = get_cloud_agent(decision["role"])

    result = await agent.execute(req.task)
    return result


@app.get("/router/status")
async def router_status():
    """Router 状态报告"""
    return router.report()


@app.get("/agents/roles")
async def list_agent_roles():
    """列出所有可用的 Agent 角色"""
    return {
        "roles": {
            name: {
                "tier": r.tier.value,
                "model": r.model,
                "skills": r.skills,
                "cost_per_million": r.cost_per_million,
                "fallback": r.fallback_role,
            }
            for name, r in router.roles.items()
        }
    }

# ---- 预算 & Token 成本 API ----

@app.get("/cost/report")
async def cost_report():
    """返回当前日/月预算消耗报告。"""
    return budget_mgr.report()


@app.get("/cost/pricing")
async def cost_pricing():
    """返回所有模型的定价表（¥/百万 tokens）。"""
    return {"pricing": budget_mgr.PRICING}


@app.get("/cost/status")
async def cost_status():
    """返回当前预算状态（ok / warning / critical）。"""
    report = budget_mgr.report()
    return {
        "status": report["status"],
        "daily_pct": report["daily"]["pct"],
        "monthly_pct": report["monthly"]["pct"],
    }
from spider_meta.plugins import PluginRegistry, SkillPlugin

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("meta-agent")


class TaskPlan(BaseModel):
    task_id: str = Field(default_factory=lambda: f"plan-{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    subtasks: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "pending"
    strategy: str = ""
    estimated_steps: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class AgentStep(BaseModel):
    step_id: int = 0
    thought: str = ""
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    tool_result: Optional[Any] = None


class AgentContext:
    def __init__(self, task: str, max_steps: int = 20):
        self.task = task
        self.max_steps = max_steps
        self.steps: List[AgentStep] = []
        self.session_id = f"session-{uuid.uuid4().hex[:8]}"
        self.started_at = datetime.now().isoformat()
        self.finished = False
        self.result = None

    def add_step(self, step: AgentStep):
        step.step_id = len(self.steps) + 1
        self.steps.append(step)

    def get_history(self) -> str:
        lines = []
        for s in self.steps:
            lines.append(f"Step {s.step_id}:")
            lines.append(f"  Thought: {s.thought}")
            if s.action:
                lines.append(f"  Action: {s.action}")
                lines.append(f"  Input: {json.dumps(s.action_input, ensure_ascii=False)}")
            if s.observation:
                lines.append(f"  Observation: {s.observation}")
            lines.append("")
        return "\n".join(lines)

    def to_summary(self) -> Dict:
        return {
            "session_id": self.session_id,
            "task": self.task,
            "steps_taken": len(self.steps),
            "finished": self.finished,
            "result": self.result,
            "duration": str(datetime.now() - datetime.fromisoformat(self.started_at)),
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict] = {}

    def register(self, name: str, func, description: str, parameters: Dict = None):
        self._tools[name] = {
            "func": func,
            "description": description,
            "parameters": parameters or {},
        }

    def get(self, name: str) -> Optional[Dict]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        return [{"name": k, "description": v["description"], "parameters": v["parameters"]} for k, v in self._tools.items()]


tools = ToolRegistry()
PluginRegistry.set_tool_registry(tools)


def register_builtin_tools():
    import subprocess

    async def execute_shell(command: str, timeout: int = 30) -> str:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
            return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\nrc={result.returncode}"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"

    async def read_file(path: str, encoding: str = "utf-8") -> str:
        from pathlib import Path
        p = Path(path)
        if not p.exists():
            return f"File not found: {path}"
        return p.read_text(encoding=encoding)[:50000]

    async def write_file(path: str, content: str, encoding: str = "utf-8") -> str:
        from pathlib import Path
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)
        return f"Written {len(content)} chars to {path}"

    async def list_files(directory: str = ".", pattern: str = "*") -> str:
        from pathlib import Path
        p = Path(directory)
        if not p.exists():
            return f"Directory not found: {directory}"
        files = list(p.glob(pattern))
        return "\n".join(str(f) for f in files[:100])

    async def search_files(path: str, keyword: str) -> str:
        from pathlib import Path
        results = []
        for f in Path(path).rglob("*"):
            if f.is_file() and f.stat().st_size < 1_000_000:
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if keyword in content:
                        lines = [f"{i+1}: {line}" for i, line in enumerate(content.split("\n")) if keyword in line]
                        results.append(f"{f}:\n" + "\n".join(lines[:5]))
                except Exception:
                    pass
        return "\n\n".join(results[:10]) or "No matches found"

    async def http_get(url: str) -> str:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=15)
            return f"Status: {resp.status_code}\n{resp.text[:5000]}"

    tools.register("shell", execute_shell, "Execute a shell command", {"command": "string", "timeout": "number"})
    tools.register("read_file", read_file, "Read file content", {"path": "string", "encoding": "string"})
    tools.register("write_file", write_file, "Write content to file", {"path": "string", "content": "string"})
    tools.register("list_files", list_files, "List files in directory", {"directory": "string", "pattern": "string"})
    tools.register("search_files", search_files, "Search keyword in files", {"path": "string", "keyword": "string"})
    tools.register("http_get", http_get, "Make HTTP GET request", {"url": "string"})


register_builtin_tools()


class MetaAgent:
    def __init__(self, llm_url: str = None, llm_model: str = None, llm_key: str = None):
        self.llm_url = llm_url or os.getenv("LLM_API_URL", "")
        self.llm_model = llm_model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.llm_key = llm_key or os.getenv("LLM_API_KEY", "")
        self.contexts: Dict[str, AgentContext] = {}

    def _build_system_prompt(self) -> str:
        tool_list = "\n".join(f"- {t['name']}: {t['description']}" for t in tools.list_tools())
        return f"""You are a Meta-Agent that solves complex tasks by breaking them down and using tools.

Available tools:
{tool_list}

Format your response as JSON:
{{
    "thought": "your reasoning",
    "action": "tool_name or 'finish'",
    "action_input": {{"param": "value"}} or null,
    "final_answer": "only if action is 'finish'"
}}"""

    def _build_step_prompt(self, ctx: AgentContext) -> List[Dict]:
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.append({"role": "user", "content": f"Task: {ctx.task}"})
        for step in ctx.steps:
            messages.append({"role": "assistant", "content": json.dumps({"thought": step.thought, "action": step.action, "action_input": step.action_input})})
            if step.observation:
                messages.append({"role": "user", "content": f"Observation: {step.observation}"})
        return messages

    async def _call_llm(self, messages: List[Dict]) -> Dict:
        if not self.llm_key:
            return self._simulate_llm(messages)
        import httpx
        payload = {"model": self.llm_model, "messages": messages, "temperature": 0.1, "max_tokens": 2048}
        headers = {"Authorization": f"Bearer {self.llm_key}"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.llm_url}/chat/completions", json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"thought": content, "action": "finish", "final_answer": content}

    def _simulate_llm(self, messages: List[Dict]) -> Dict:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        if "Observation:" in last_user:
            obs = last_user.replace("Observation:", "").strip()
            if "File not found" in obs or "No matches" in obs or "timed out" in obs:
                return {"thought": "Previous action failed, trying different approach", "action": "finish", "final_answer": f"Encountered error: {obs}"}
            return {"thought": "Got results, analyzing next step", "action": "finish", "final_answer": f"Task completed with observations: {obs[:500]}"}
        step_num = sum(1 for m in messages if m["role"] == "assistant")
        if step_num == 0:
            return {"thought": "Starting task analysis", "action": "list_files", "action_input": {"directory": "."}}
        return {"thought": f"Step {step_num}: analyzing current state", "action": "finish", "final_answer": f"Simulated completion after {step_num} steps"}

    async def execute_tool(self, action: str, action_input: Dict) -> str:
        tool = tools.get(action)
        if not tool:
            return f"Unknown tool: {action}"
        try:
            result = await tool["func"](**action_input)
            return str(result)[:5000]
        except Exception as e:
            return f"Tool error: {e}"

    async def run(self, task: str, max_steps: int = 20) -> AgentContext:
        ctx = AgentContext(task, max_steps)
        self.contexts[ctx.session_id] = ctx
        logger.info(f"Meta-Agent started: session={ctx.session_id}, task={task[:100]}")
        for i in range(max_steps):
            messages = self._build_step_prompt(ctx)
            response = await self._call_llm(messages)
            thought = response.get("thought", "")
            action = response.get("action", "finish")
            action_input = response.get("action_input") or {}
            step = AgentStep(thought=thought, action=action, action_input=action_input)
            if action == "finish":
                ctx.finished = True
                ctx.result = response.get("final_answer", thought)
                step.observation = f"Finished: {ctx.result}"
                ctx.add_step(step)
                logger.info(f"Session {ctx.session_id} finished in {len(ctx.steps)} steps")
                break
            else:
                observation = await self.execute_tool(action, action_input)
                step.observation = observation
                ctx.add_step(step)
        else:
            ctx.finished = True
            ctx.result = "Max steps reached"
            logger.warning(f"Session {ctx.session_id} reached max steps ({max_steps})")
        return ctx

    def get_session(self, session_id: str) -> Optional[AgentContext]:
        return self.contexts.get(session_id)


agent = MetaAgent()


class HealthResponse(BaseModel):
    status: str
    service: str
    model: str
    tools_count: int
    active_sessions: int


class TaskRequest(BaseModel):
    task: str
    max_steps: int = 20


class PlanningRequest(BaseModel):
    objective: str
    constraints: List[str] = Field(default_factory=list)


class PipelineExecuteRequest(BaseModel):
    task: str
    use_knowledge: bool = True
    use_experience: bool = True


class PipelineExecuteResponse(BaseModel):
    pipeline_id: str
    status: str
    result: Optional[str] = None
    subtasks_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    errors: List[str] = Field(default_factory=list)


class PipelineStatusResponse(BaseModel):
    pipeline_id: str
    status: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    current_phase: str = ""


class DAGExecuteRequest(BaseModel):
    task: str
    sop_task_ids: List[str] = Field(default_factory=list)


class WorkerRegisterRequest(BaseModel):
    worker_id: str
    skills: List[str]
    endpoint: str


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 5


# ---- 新增: SkillPlugin / Tool / Event HTTP 注册接口的请求模型 ----

class SkillRegisterRequest(BaseModel):
    name: str
    description: str = ""
    module_path: str = ""
    class_name: str = ""


class ToolRegisterRequest(BaseModel):
    name: str
    description: str = ""
    endpoint: str = ""


class EventSubscribeRequest(BaseModel):
    event_type: str
    callback_url: str = ""


class EventPublishRequest(BaseModel):
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- 硬件资源检查（立项协议） ----
    hw = check_hardware_limits()
    if hw["status"] == "critical":
        for c in hw.get("critical", []):
            logger.critical(f"[HARDWARE] {c}")
    for w in hw.get("warnings", []):
        logger.warning(f"[HARDWARE] {w}")

    # ---- 成本状态 ----
    cost_report = budget_mgr.report()
    logger.info(
        f"[COST] 日: ¥{cost_report['daily']['spent_rmb']:.4f}/{cost_report['daily']['budget_rmb']:.2f} "
        f"({cost_report['daily']['pct']:.0%}) | "
        f"月: ¥{cost_report['monthly']['spent_rmb']:.4f}/{cost_report['monthly']['budget_rmb']:.0f} "
        f"({cost_report['monthly']['pct']:.0%}) | "
        f"状态: {cost_report['status']}"
    )

    logger.info(
        f"[META-AGENT] model={agent.llm_model}, "
        f"llm_configured={bool(agent.llm_key)}, "
        f"tools={len(tools.list_tools())}, "
        f"status={hw['status']}"
    )
    yield


app = FastAPI(title="spider_meta", version="1.0.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok", service="meta-agent", model=agent.llm_model,
        tools_count=len(tools.list_tools()), active_sessions=len(agent.contexts),
    )


@app.post("/agent/run")
async def run_agent(req: TaskRequest):
    ctx = await agent.run(req.task, req.max_steps)
    return ctx.to_summary()


@app.post("/agent/plan")
async def create_plan(req: PlanningRequest):
    ctx = await agent.run(
        f"Create a detailed execution plan for: {req.objective}"
        + (f"\nConstraints: {', '.join(req.constraints)}" if req.constraints else ""),
        max_steps=10,
    )
    plan = TaskPlan(
        title=req.objective[:100], description=ctx.result or "",
        strategy=reagent_strategy(ctx), estimated_steps=len(ctx.steps),
    )
    return {"plan": plan.dict(), "session_id": ctx.session_id}


@app.get("/agent/sessions/{session_id}")
async def get_session(session_id: str):
    ctx = agent.get_session(session_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": ctx.session_id, "task": ctx.task, "finished": ctx.finished,
            "result": ctx.result, "steps": [s.dict() for s in ctx.steps]}


@app.get("/agent/sessions")
async def list_sessions():
    return [{"session_id": s.session_id, "task": s.task[:80], "finished": s.finished} for s in agent.contexts.values()]


@app.post("/pipeline/execute", response_model=PipelineExecuteResponse)
async def pipeline_execute(req: PipelineExecuteRequest):
    orchestrator = PipelineOrchestrator()
    result = await orchestrator.execute(req.task)
    status = orchestrator.get_pipeline_status(result.pipeline_id)
    return PipelineExecuteResponse(
        pipeline_id=result.pipeline_id, status=result.status.value,
        result=result.tree.description if result.tree else None,
        subtasks_count=status.total_tasks if status else 0,
        completed_count=status.completed_tasks if status else 0,
        failed_count=status.failed_tasks if status else 0, errors=result.errors,
    )


@app.get("/pipeline/status/{pipeline_id}", response_model=PipelineStatusResponse)
async def pipeline_status(pipeline_id: str):
    return PipelineStatusResponse(pipeline_id=pipeline_id, status="unknown")


@app.post("/dag/execute")
async def dag_execute(req: DAGExecuteRequest):
    orchestrator = PipelineOrchestrator()
    result = await orchestrator.execute(req.task)
    return {"pipeline_id": result.pipeline_id, "status": result.status.value,
            "subtasks": [st.model_dump() for st in result.tree.subtasks] if result.tree else []}


# ---- 全局 Worker 调度器 ----
dispatcher = WorkerDispatcher(redis_client=None)


@app.post("/workers/register")
async def register_worker(req: WorkerRegisterRequest):
    wc = dispatcher.register_worker(req.worker_id, req.skills, req.endpoint)
    return {"status": "registered", "worker_id": req.worker_id, "skills": wc.skills}


@app.get("/workers")
async def list_workers():
    return {"workers": [{"worker_id": wc.worker_id, "skills": wc.skills, "status": wc.status.value,
                          "load": wc.load, "active_tasks": wc.active_tasks, "endpoint": wc.endpoint}
                         for wc in dispatcher.get_all_workers().values()]}


@app.delete("/workers/{worker_id}")
async def unregister_worker(worker_id: str):
    dispatcher.unregister_worker(worker_id)
    return {"status": "unregistered", "worker_id": worker_id}


@app.post("/knowledge/search")
async def search_knowledge(req: KnowledgeSearchRequest):
    retriever = KnowledgeRetriever()
    results = await retriever.retrieve(req.query, req.top_k)
    return {"results": [r.model_dump() for r in results], "query": req.query}


@app.get("/metrics")
async def get_metrics():
    return metrics.report()


@app.get("/health/detailed")
async def detailed_health():
    return {"status": "ok", "service": "spider-meta",
            "modules": {"pipeline": "available", "dag": "available", "knowledge": "available", "experience": "available"}}


# ============================================================
# 机制3: SkillPlugin HTTP 注册接口
# ============================================================

@app.post("/skills/register")
async def register_skill_http(req: SkillRegisterRequest):
    """HTTP endpoint: register a SkillPlugin via module_path+class_name or local class."""
    if req.module_path and req.class_name:
        import importlib
        mod = importlib.import_module(req.module_path)
        cls = getattr(mod, req.class_name)
        if not issubclass(cls, SkillPlugin):
            raise HTTPException(400, f"{req.class_name} is not a SkillPlugin subclass")
        PluginRegistry.register(cls())
        return {"status": "registered", "skill": req.name or cls.name}
    existing = PluginRegistry.get(req.name)
    if existing:
        return {"status": "already_registered", "skill": req.name}
    raise HTTPException(400, "Provide module_path+class_name or ensure class is already imported")


@app.get("/skills")
async def list_skills():
    """List all registered SkillPlugins."""
    return {"skills": PluginRegistry.list_plugins()}


@app.post("/skills/{name}/activate")
async def activate_skill(name: str):
    """Activate a registered SkillPlugin."""
    plugin = PluginRegistry.get(name)
    if not plugin:
        raise HTTPException(404, f"Skill '{name}' not found")
    plugin.activate(context={})
    return {"status": "activated", "skill": name}


@app.post("/skills/{name}/execute")
async def execute_skill_http(name: str, req: Dict[str, Any] = None):
    """Execute a registered SkillPlugin."""
    plugin = PluginRegistry.get(name)
    if not plugin:
        raise HTTPException(404, f"Skill '{name}' not found")
    result = await plugin.execute(task=req or {})
    return {"status": "executed", "skill": name, "result": str(result)}


# ============================================================
# 机制2: Tool HTTP 注册接口
# ============================================================

@app.post("/tools/register")
async def register_tool_http(req: ToolRegisterRequest):
    """HTTP endpoint: register a Tool (remote endpoint or local function)."""
    if req.endpoint:
        async def remote_tool(**kwargs):
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.post(req.endpoint, json=kwargs, timeout=30)
                return r.json()
        tools.register(req.name, remote_tool, req.description)
    else:
        tools.register(req.name, lambda **kw: {"echo": kw, "tool": req.name}, req.description)
    return {"status": "registered", "tool": req.name}


@app.get("/tools")
async def list_tools():
    """List all registered Tools."""
    return {"tools": tools.list_tools()}


# ============================================================
# 机制4: Event HTTP 接口
# ============================================================

@app.post("/events/subscribe")
async def subscribe_event(req: EventSubscribeRequest):
    """HTTP endpoint: subscribe to an event type with optional webhook callback."""
    from spider_meta.core.event_bus import event_bus, EventType
    try:
        et = EventType(req.event_type)
    except ValueError:
        raise HTTPException(400, f"Unknown event type: {req.event_type}")

    async def webhook_handler(event):
        if req.callback_url:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(req.callback_url, json=event.payload, timeout=10)

    sub_id = event_bus.subscribe([et], webhook_handler)
    return {"status": "subscribed", "sub_id": sub_id, "event_type": req.event_type}


@app.post("/events/publish")
async def publish_event(req: EventPublishRequest):
    """HTTP endpoint: publish an event to all subscribers."""
    from spider_meta.core.event_bus import event_bus, EventType, Event
    try:
        et = EventType(req.event_type)
    except ValueError:
        raise HTTPException(400, f"Unknown event type: {req.event_type}")
    event = Event(event_type=et, source="http_api", payload=req.payload)
    notified = await event_bus.publish(event)
    return {"status": "published", "event_type": req.event_type, "notified": notified}


@app.get("/events/types")
async def list_event_types():
    """List all available event types."""
    from spider_meta.core.event_bus import EventType
    return {"event_types": [e.value for e in EventType]}


@app.get("/events/subscriptions")
async def list_subscriptions():
    """List all active event subscriptions."""
    from spider_meta.core.event_bus import event_bus
    return {"subscriptions": {sid: {"event_types": [e.value for e in sub.event_types],
                                      "priority": sub.priority}
                               for sid, sub in event_bus._subscribers.items()}}


def main():
    import uvicorn
    uvicorn.run("spider_meta.main:app", host="0.0.0.0", port=8003, log_level="info")


def reagent_strategy(ctx: AgentContext) -> str:
    actions = [s.action for s in ctx.steps if s.action]
    if not actions:
        return "direct"
    if "write_file" in actions and "shell" in actions:
        return "full_stack"
    if "search_files" in actions:
        return "research"
    if "http_get" in actions:
        return "api_integration"
    return "analysis"
