"""
auth_gateway - AstrBot 用户授权网关插件

核心职责：
1. 拦截关键操作事件，暂停等待用户确认
2. 生成一次性授权令牌（token）
3. 验证授权令牌后才允许执行操作
4. 记录所有授权操作到 .ai-workspace/audit/

设计原则：
- 用户始终是决策终点
- 关键操作必须有显式用户授权
- 单次令牌默认，可配置会话级令牌
"""

import json
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from astrbot.api import star, llm_tool
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain
from astrbot.core import logger

AUDIT_DIR = r"E:\软件开发\.ai-workspace\audit"
TOKEN_TTL_SECONDS = 300


class Main(star.Star):
    def __init__(self, context: star.Context) -> None:
        self.context = context
        self._pending_authorizations: dict = {}
        self._tokens: dict = {}
        os.makedirs(AUDIT_DIR, exist_ok=True)
        logger.info("auth_gateway 插件初始化成功")

    def _generate_token(self) -> str:
        return uuid.uuid4().hex[:16]

    def _audit_log(self, record: dict):
        date_str = datetime.now().strftime("%Y%m%d")
        path = os.path.join(AUDIT_DIR, f"auth_{date_str}.jsonl")
        record["logged_at"] = datetime.now().isoformat()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def request_authorization(
        self, user_id: str, action: str, target: str, description: str = ""
    ) -> dict:
        req_id = uuid.uuid4().hex[:12]
        token = self._generate_token()
        expires_at = (
            datetime.now() + timedelta(seconds=TOKEN_TTL_SECONDS)
        ).isoformat()
        auth_req = {
            "req_id": req_id,
            "user_id": user_id,
            "action": action,
            "target": target,
            "description": description,
            "token": token,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at,
        }
        self._pending_authorizations[req_id] = auth_req
        self._tokens[token] = auth_req
        self._audit_log({"event": "auth_requested", **auth_req})
        return auth_req

    def confirm_authorization(self, user_id: str, req_id: str) -> str:
        req = self._pending_authorizations.get(req_id)
        if not req:
            return None
        if req["user_id"] != user_id:
            return None
        if datetime.fromisoformat(req["expires_at"]) < datetime.now():
            req["status"] = "expired"
            self._audit_log({"event": "auth_expired", **req})
            return None
        req["status"] = "confirmed"
        req["confirmed_at"] = datetime.now().isoformat()
        self._audit_log({"event": "auth_confirmed", **req})
        return req["token"]

    def validate_token(self, token: str) -> dict:
        req = self._tokens.get(token)
        if not req:
            return None
        if req["status"] != "confirmed":
            return None
        if datetime.fromisoformat(req["expires_at"]) < datetime.now():
            req["status"] = "expired"
            self._audit_log({"event": "auth_expired", **req})
            return None
        req["status"] = "consumed"
        req["consumed_at"] = datetime.now().isoformat()
        self._audit_log({"event": "auth_consumed", **req})
        return req

    @filter.confirm("确认授权")
    async def confirm_auth_command(self, event: AstrMessageEvent) -> None:
        """确认待授权请求：授权确认 <请求ID>"""
        yield event.plain_result(
            "❓ 请提供授权请求ID：\n格式：授权确认 <请求ID>\n"
            "可通过「查看待授权」获取请求ID列表。"
        )

    @filter.command("查看待授权")
    async def list_pending_auth(self, event: AstrMessageEvent) -> None:
        user_id = event.get_user_id()
        pending = [
            v for v in self._pending_authorizations.values()
            if v["status"] == "pending" and v["user_id"] == user_id
        ]
        if not pending:
            yield event.plain_result("✅ 当前没有待确认的授权请求")
            return
        msg = "📋 待确认授权列表:\n\n"
        for i, req in enumerate(pending, 1):
            msg += (
                f"{i}. [{req['req_id']}] {req['action']} -> {req['target']}\n"
                f"   描述: {req['description']}\n"
                f"   过期: {req['expires_at']}\n\n"
            )
        msg += "回复「授权确认 <请求ID>」来确认授权"
        yield event.plain_result(msg)

    @filter.command("授权确认")
    async def do_confirm(self, event: AstrMessageEvent) -> None:
        user_id = event.get_user_id()
        args = event.get_message_str().strip().split()
        if len(args) < 2:
            yield event.plain_result("❌ 格式：授权确认 <请求ID>")
            return
        req_id = args[1]
        token = self.confirm_authorization(user_id, req_id)
        if token:
            yield event.plain_result(
                f"✅ 授权已确认！\n请求: {req_id}\n令牌: {token}\n"
                f"有效期: {TOKEN_TTL_SECONDS}秒"
            )
        else:
            yield event.plain_result(
                "❌ 授权确认失败。可能原因：\n"
                "- 请求ID 不存在\n"
                "- 已过期\n"
                "- 用户不匹配"
            )

    @filter.command("验证令牌")
    async def do_validate(self, event: AstrMessageEvent) -> None:
        args = event.get_message_str().strip().split()
        if len(args) < 2:
            yield event.plain_result("❌ 格式：验证令牌 <token>")
            return
        token = args[1]
        req = self.validate_token(token)
        if req:
            yield event.plain_result(
                f"✅ 令牌有效\n操作: {req['action']}\n目标: {req['target']}"
            )
        else:
            yield event.plain_result("❌ 令牌无效或已过期")

    @filter.command("审计日志")
    async def view_audit(self, event: AstrMessageEvent) -> None:
        files = sorted(
            [f for f in os.listdir(AUDIT_DIR) if f.startswith("auth_")],
            reverse=True,
        )
        if not files:
            yield event.plain_result("📋 暂无审计日志")
            return
        latest = files[0]
        path = os.path.join(AUDIT_DIR, latest)
        lines = []
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        last = lines[-10:] if len(lines) > 10 else lines
        msg = f"📋 审计日志 ({latest}) 最近 {len(last)} 条:\n\n"
        for line in last:
            try:
                rec = json.loads(line)
                msg += (
                    f"[{rec.get('logged_at','')}] "
                    f"{rec.get('event','?')} | "
                    f"{rec.get('action','')} -> {rec.get('target','')} | "
                    f"status={rec.get('status','')}\n"
                )
            except Exception:
                msg += line
        yield event.plain_result(msg)

    @llm_tool("require_user_authorization")
    async def require_user_authorization(
        self, action: str, target: str, description: str = ""
    ) -> str:
        req = await self.request_authorization(
            user_id="llm_tool_call",
            action=action,
            target=target,
            description=description,
        )
        return json.dumps({
            "req_id": req["req_id"],
            "status": "pending",
            "message": f"需要用户授权: {action} -> {target}。请求ID: {req['req_id']}",
        }, ensure_ascii=False)

    @llm_tool("check_authorization_token")
    async def check_authorization_token(self, token: str) -> str:
        req = self.validate_token(token)
        if req:
            return json.dumps({"valid": True, "action": req["action"], "target": req["target"]})
        return json.dumps({"valid": False, "error": "令牌无效或已过期"})
