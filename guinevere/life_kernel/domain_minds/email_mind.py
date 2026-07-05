"""Email domain mind — LK-012.

Implements the email action graph and policy engine for Guinevere's Living Autonomy
Kernel. The ``EmailMind`` class classifies outgoing email by risk, routes it through a
LangGraph subgraph, and only ever queues low-risk email. Sensitive and dangerous
messages are blocked by policy; no real email API is ever called.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, cast

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import NotRequired, TypedDict

if TYPE_CHECKING:
    from guinevere.life_kernel.hermes_brain import HermesBrain

logger = structlog.get_logger(__name__)


#: Subjects that are candidates for auto-queued low-risk email.
LOW_RISK_SUBJECTS = {
    "system notification",
    "status update",
    "admin alert",
    "automated report",
}

#: Regex for dangerous content: API keys, bearer tokens, password literals.
DANGEROUS_PATTERN = re.compile(
    r"("
    r"sk-[A-Za-z0-9]+"
    r"|Bearer\s+[A-Za-z0-9\-_\.]+"
    r"|password\s*[:=]"
    r"|api[_-]?key\s*[:=]"
    r"|token\s*[:=]\s*[A-Za-z0-9\-_\.]+"
    r"|auth\s*code\s*[:=]?\s*\d+"
    r"|otp\s*[:=]?\s*\d+"
    r"|payment\s*confirmed"
    r"|cvv\s*[:=]?\s*\d{3,4}"
    r")",
    re.IGNORECASE,
)

#: Regex for sensitive content: PII, financial, health, personal identifiers.
SENSITIVE_PATTERN = re.compile(
    r"("
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    r"|\b\d{3}-\d{2}-\d{4}\b"
    r"|\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"
    r"|\+?\d{1,3}[\s-]?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}"
    r"|\b(?:diagnosis|symptom|prescription|patient|medical record)\b"
    r"|\b(?:salary|invoice|bank|account number|transfer|payment)\b"
    r"|\b(?:personal|private|confidential)\b"
    r")",
    re.IGNORECASE,
)


class EmailState(TypedDict, total=False):
    """State schema for the email domain mind subgraph.

    All fields are optional so the graph can be invoked with partial state and
    filled in by the classify/approve/send nodes.
    """

    email_id: str
    subject: str
    body: str
    to: str
    sensitivity: NotRequired[str]
    status: NotRequired[str]
    reason: NotRequired[str]


class EmailMind:
    """Policy-driven email domain mind.

    ``EmailMind`` provides a deterministic risk classification for outgoing email,
    a placeholder send path that never touches a real email provider, and a
    LangGraph subgraph that encodes the routing policy:

    - low_risk  -> classify -> send (auto)
    - sensitive -> classify -> approve (needs review) -> send
    - dangerous -> classify -> END (blocked)

    Args:
        hermes_brain: Optional ``HermesBrain`` instance for future LLM-based
            sensitivity classification. Currently stored but not used by the
            deterministic v1 policy.
    """

    def __init__(self, hermes_brain: HermesBrain | None = None) -> None:
        """Initialise the email domain mind.

        Args:
            hermes_brain: Optional Hermes brain bridge for future classification.
        """
        self.hermes_brain = hermes_brain
        self._logger = structlog.get_logger(__name__)
        self._logger.info(
            "email_mind_init",
            hermes_brain=hermes_brain is not None,
        )

    @staticmethod
    def _normalize(text: str) -> str:
        """Return lower-cased text for case-insensitive matching."""
        return text.lower().strip()

    def classify_sensitivity(self, email: dict[str, Any]) -> str:
        """Classify an email as low_risk, sensitive, or dangerous.

        The classification is deterministic and rule-based:

        - Dangerous content is checked first and always wins.
        - Sensitive content is detected next.
        - Low-risk subjects that contain no sensitive body content are low risk.
        - Unknown subjects default to sensitive -- only explicit low-risk subjects auto-send.

        Args:
            email: Dict with at least ``subject`` and ``body`` keys.

        Returns:
            One of ``"low_risk"``, ``"sensitive"``, or ``"dangerous"``.
        """
        subject = self._normalize(email.get("subject", ""))
        body = email.get("body", "") or ""
        combined = f"{subject}\n{body}"

        if DANGEROUS_PATTERN.search(combined):
            return "dangerous"

        is_low_risk_subject = subject in LOW_RISK_SUBJECTS
        has_sensitive = SENSITIVE_PATTERN.search(combined) is not None

        if has_sensitive:
            return "sensitive"

        if is_low_risk_subject and not has_sensitive:
            return "low_risk"

        # Default fallback: unknown email content is treated as sensitive.
        # Only explicit LOW_RISK_SUBJECTS may auto-send.
        return "sensitive"

    def send(self, email: dict[str, Any]) -> dict[str, Any]:
        """Placeholder send path that never calls a real email API.

        Low-risk email is logged as queued. Sensitive and dangerous emails are
        blocked with an explanatory reason.

        Args:
            email: Dict with at least ``subject`` and ``body`` keys.

        Returns:
            Dict describing the queued/blocked outcome.
        """
        risk = self.classify_sensitivity(email)

        if risk == "low_risk":
            self._logger.info(
                "email_send_intent_queued",
                subject=email.get("subject"),
                to=email.get("to"),
                risk="low",
            )
            return {"status": "queued", "risk": "low"}

        if risk == "sensitive":
            reason = (
                "Sensitive email blocked pending operator review: "
                "contains personal correspondence, PII, financial, or health data."
            )
            self._logger.warning(
                "email_send_blocked_sensitive",
                subject=email.get("subject"),
                to=email.get("to"),
                reason=reason,
            )
            return {
                "status": "blocked",
                "risk": "sensitive",
                "reason": reason,
            }

        reason = (
            "Dangerous email blocked: contains credentials, secrets, "
            "tokens, payment confirmations, or auth codes."
        )
        self._logger.warning(
            "email_send_blocked_dangerous",
            subject=email.get("subject"),
            to=email.get("to"),
            reason=reason,
        )
        return {
            "status": "blocked",
            "risk": "dangerous",
            "reason": reason,
        }

    async def classify_node(self, state: EmailState) -> dict[str, Any]:
        """Graph node that classifies the email and sets initial status.

        Args:
            state: Current email subgraph state.

        Returns:
            Updates for ``sensitivity`` and ``status``.
        """
        email = {
            "subject": state.get("subject", ""),
            "body": state.get("body", ""),
            "to": state.get("to", ""),
        }
        sensitivity = self.classify_sensitivity(email)

        self._logger.info(
            "email_classify_node",
            email_id=state.get("email_id"),
            sensitivity=sensitivity,
        )

        return {
            "sensitivity": sensitivity,
            "status": "classified",
        }

    async def approve_node(self, state: EmailState) -> dict[str, Any]:
        """Graph node that marks sensitive email as pending review.

        Marks sensitive email as pending review and records it. Does NOT route to
        send_node -- sensitive email is recorded/escalated, not auto-sent.

        Args:
            state: Current email subgraph state.

        Returns:
            Updates for ``status`` and ``reason``.
        """
        self._logger.info(
            "email_approve_node_review",
            email_id=state.get("email_id"),
            sensitivity=state.get("sensitivity"),
        )
        return {
            "status": "pending_approval",
            "reason": "Awaiting operator review before sending sensitive email.",
        }

    async def send_node(self, state: EmailState) -> dict[str, Any]:
        """Graph node that executes the placeholder send path.

        Args:
            state: Current email subgraph state.

        Returns:
            Updates for ``status`` and, when blocked, ``reason``.
        """
        email = {
            "subject": state.get("subject", ""),
            "body": state.get("body", ""),
            "to": state.get("to", ""),
        }
        result = self.send(email)

        self._logger.info(
            "email_send_node",
            email_id=state.get("email_id"),
            status=result["status"],
            risk=result.get("risk"),
        )

        update: dict[str, Any] = {"status": result["status"]}
        if "reason" in result:
            update["reason"] = result["reason"]
        return update

    def build_graph(self) -> CompiledStateGraph[EmailState, Any, Any, Any]:
        """Build and compile the email domain mind LangGraph subgraph.

        The graph has three nodes:

        - ``classify_node``: runs ``classify_sensitivity`` and writes the result.
        - ``approve_node``: marks sensitive email as pending approval.
        - ``send_node``: executes the placeholder send path.

        Routing:

        - ``low_risk`` -> ``send_node``
        - ``sensitive`` -> ``approve_node`` -> ``END`` (recorded, not sent)
        - ``dangerous`` -> ``END``

        Returns:
            Compiled LangGraph StateGraph.
        """
        self._logger.info("email_build_graph")

        builder = StateGraph(EmailState)

        builder.add_node("classify_node", self.classify_node)
        builder.add_node("approve_node", self.approve_node)
        builder.add_node("send_node", self.send_node)

        builder.add_edge(START, "classify_node")

        def route_from_classify(state: EmailState) -> str:
            """Route from classification based on sensitivity."""
            sensitivity = state.get("sensitivity")
            if sensitivity == "low_risk":
                return "send_node"
            if sensitivity == "sensitive":
                return "approve_node"
            return cast(str, END)

        builder.add_conditional_edges(
            "classify_node",
            route_from_classify,
            {
                "send_node": "send_node",
                "approve_node": "approve_node",
                END: END,
            },
        )

        builder.add_edge("approve_node", END)
        builder.add_edge("send_node", END)

        return builder.compile()
