import logging
from typing import List

from spider_meta.core.schemas import SubTask, TaskIntent, TaskTree

logger = logging.getLogger("meta-agent.decomposer")


class TaskDecomposer:
    def __init__(self, llm_service=None, max_depth: int = 3):
        self.llm_service = llm_service
        self.max_depth = max_depth
        self.knowledge_retriever = None

    async def decompose(self, task: str, context: dict = None) -> TaskTree:
        context = context or {}
        logger.info(f"Decomposing task: {task[:100]}")

        intent = await self._analyze_intent(task)

        knowledge_docs = []
        if self.knowledge_retriever and self.knowledge_retriever.settings.enable_knowledge_retrieval:
            if intent.intent_type in ("research", "analysis", "general"):
                try:
                    knowledge_docs = await self.knowledge_retriever.retrieve(task)
                except Exception as e:
                    logger.warning(f"Knowledge retrieval failed: {e}")

        subtasks = await self._generate_subtasks(intent)

        if knowledge_docs:
            for subtask in subtasks:
                if subtask.required_skill in ("search", "analysis"):
                    subtask.context["knowledge"] = [
                        {"doc_id": d.doc_id, "content": d.content, "score": d.score}
                        for d in knowledge_docs
                    ]

        for subtask in subtasks:
            subtask.context["depth"] = 0
            if self.max_depth > 0:
                children = await self._decompose_recursive(subtask, depth=0)
                if children:
                    subtask.context["children"] = [c.task_id for c in children]
                    subtasks.extend(children)

        tree = TaskTree(
            title=task[:200],
            description=task,
            subtasks=subtasks,
            max_depth=self.max_depth,
        )
        logger.info(f"Decomposition complete: {len(subtasks)} subtasks generated")
        return tree

    async def _analyze_intent(self, task: str) -> TaskIntent:
        if not task:
            return TaskIntent(
                original_task="",
                intent_type="general",
                complexity="simple",
                keywords=[],
                required_skills=["general"],
            )

        if self.llm_service:
            return await self._analyze_intent_llm(task)

        task_lower = task.lower()
        keywords = []
        intent_type = "general"
        required_skills = ["general"]

        research_keywords = ["search", "research", "investigate", "query", "lookup"]
        dev_keywords = ["develop", "code", "implement", "build", "create", "write"]
        analysis_keywords = ["analyze", "evaluate", "compare", "assess", "review"]
        cleanup_keywords = ["clean", "organize", "optimize", "refactor", "restructure"]

        if any(kw in task_lower for kw in research_keywords):
            intent_type = "research"
            required_skills = ["search"]
            keywords = [kw for kw in research_keywords if kw in task_lower]
        elif any(kw in task_lower for kw in dev_keywords):
            intent_type = "development"
            required_skills = ["coding"]
            keywords = [kw for kw in dev_keywords if kw in task_lower]
        elif any(kw in task_lower for kw in analysis_keywords):
            intent_type = "analysis"
            required_skills = ["analysis"]
            keywords = [kw for kw in analysis_keywords if kw in task_lower]
        elif any(kw in task_lower for kw in cleanup_keywords):
            intent_type = "cleanup"
            required_skills = ["cleanup"]
            keywords = [kw for kw in cleanup_keywords if kw in task_lower]

        complexity = "medium"
        if len(task) < 20:
            complexity = "simple"
        elif len(task) > 100:
            complexity = "complex"

        return TaskIntent(
            original_task=task,
            intent_type=intent_type,
            complexity=complexity,
            keywords=keywords,
            required_skills=required_skills,
        )

    async def _analyze_intent_llm(self, task: str) -> TaskIntent:
        prompt = f"Analyze the following task and return JSON with intent_type, complexity, keywords, required_skills: {task}"
        try:
            response = await self.llm_service(prompt)
            return TaskIntent(
                original_task=task,
                intent_type=response.get("intent_type", "general"),
                complexity=response.get("complexity", "medium"),
                keywords=response.get("keywords", []),
                required_skills=response.get("required_skills", ["general"]),
            )
        except Exception as e:
            logger.warning(f"LLM intent analysis failed: {e}, falling back to rule-based")
            return await self._analyze_intent(task)

    async def _generate_subtasks(self, intent: TaskIntent) -> List[SubTask]:
        if self.llm_service:
            return await self._generate_subtasks_llm(intent)

        templates = {
            "research": [
                {"title": "Information Collection", "description": "Collect relevant data and materials", "skill": "search", "duration": 20},
                {"title": "Data Organization", "description": "Organize and categorize collected information", "skill": "analysis", "duration": 15},
                {"title": "Report Generation", "description": "Generate research report", "skill": "general", "duration": 25},
            ],
            "development": [
                {"title": "Requirement Analysis", "description": "Analyze functional requirements and constraints", "skill": "analysis", "duration": 15},
                {"title": "Solution Design", "description": "Design technical solution and architecture", "skill": "coding", "duration": 30},
                {"title": "Implementation", "description": "Write code to implement features", "skill": "coding", "duration": 45},
                {"title": "Testing", "description": "Write tests and verify functionality", "skill": "coding", "duration": 20},
            ],
            "analysis": [
                {"title": "Data Collection", "description": "Collect data required for analysis", "skill": "search", "duration": 20},
                {"title": "Analysis Processing", "description": "Perform deep analysis on data", "skill": "analysis", "duration": 30},
                {"title": "Conclusion Output", "description": "Output analysis conclusions and recommendations", "skill": "general", "duration": 15},
            ],
            "cleanup": [
                {"title": "Scan and Identify", "description": "Scan and identify items to clean up", "skill": "cleanup", "duration": 15},
                {"title": "Execute Cleanup", "description": "Execute cleanup operations", "skill": "cleanup", "duration": 25},
                {"title": "Verify Results", "description": "Verify cleanup results", "skill": "general", "duration": 10},
            ],
            "general": [
                {"title": "Task Analysis", "description": "Analyze task objectives and scope", "skill": "general", "duration": 10},
                {"title": "Execution", "description": "Execute core task", "skill": "general", "duration": 30},
                {"title": "Result Verification", "description": "Verify task results", "skill": "general", "duration": 10},
            ],
        }

        template_list = templates.get(intent.intent_type, templates["general"])
        subtasks = []
        for i, tmpl in enumerate(template_list):
            dep = [subtasks[-1].task_id] if subtasks else []
            subtask = SubTask(
                title=tmpl["title"],
                description=tmpl["description"],
                required_skill=tmpl["skill"],
                est_duration=tmpl["duration"],
                dependency=dep,
            )
            subtasks.append(subtask)

        return subtasks

    async def _generate_subtasks_llm(self, intent: TaskIntent) -> List[SubTask]:
        prompt = f"Generate subtasks for intent_type={intent.intent_type}. Return JSON list of {{title, description, required_skill, est_duration}}."
        try:
            response = await self.llm_service(prompt)
            items = response.get("subtasks", [])
            subtasks = []
            for i, item in enumerate(items):
                dep = [subtasks[-1].task_id] if subtasks else []
                subtask = SubTask(
                    title=item.get("title", f"Subtask {i + 1}"),
                    description=item.get("description", ""),
                    required_skill=item.get("required_skill", "general"),
                    est_duration=item.get("est_duration", 15),
                    dependency=dep,
                )
                subtasks.append(subtask)
            return subtasks if subtasks else await self._generate_subtasks(intent)
        except Exception as e:
            logger.warning(f"LLM subtask generation failed: {e}, falling back to rule-based")
            return await self._generate_subtasks(intent)

    async def _decompose_recursive(self, subtask: SubTask, depth: int) -> List[SubTask]:
        if depth >= self.max_depth:
            return []

        if subtask.est_duration <= 30:
            return []

        logger.info(f"Recursively decomposing: {subtask.title} at depth {depth}")

        children = []
        child_templates = [
            {"title": f"{subtask.title} - Preparation", "description": f"Prepare resources for {subtask.title}", "duration": 10},
            {"title": f"{subtask.title} - Execution", "description": f"Execute core steps of {subtask.title}", "duration": subtask.est_duration - 10},
        ]

        for tmpl in child_templates:
            child = SubTask(
                title=tmpl["title"],
                description=tmpl["description"],
                required_skill=subtask.required_skill,
                est_duration=tmpl["duration"],
                dependency=[subtask.task_id],
                context={"depth": depth + 1, "parent_id": subtask.task_id},
            )
            children.append(child)

        for child in children:
            if depth + 1 < self.max_depth and child.est_duration > 30:
                grandchildren = await self._decompose_recursive(child, depth + 1)
                children.extend(grandchildren)

        return children

    def _infer_skill(self, subtask: SubTask) -> str:
        text = (subtask.title + subtask.description).lower()

        search_keywords = ["search", "research", "investigate", "query", "lookup", "collect"]
        coding_keywords = ["develop", "code", "implement", "build", "create", "write", "design"]
        analysis_keywords = ["analyze", "evaluate", "compare", "assess", "review", "process"]
        cleanup_keywords = ["clean", "organize", "optimize", "refactor", "restructure"]

        if any(kw in text for kw in search_keywords):
            return "search"
        if any(kw in text for kw in coding_keywords):
            return "coding"
        if any(kw in text for kw in analysis_keywords):
            return "analysis"
        if any(kw in text for kw in cleanup_keywords):
            return "cleanup"
        return "general"
