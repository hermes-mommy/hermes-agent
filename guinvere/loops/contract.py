"""Sub-agent task contract — structured delegation prompts.

Defines the ``TaskContract`` Pydantic model and helpers to build
contracts and convert them into delegation prompts with standard
sections: TASK, EXPECTED OUTCOME, REQUIRED TOOLS, MUST DO,
MUST NOT DO, CONTEXT.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger()


class TaskContract(BaseModel):
    """Structured contract for delegating a task to a sub-agent.

    All fields define the boundaries and expectations for the
    sub-agent's work.  ``status`` and ``result`` track execution
    lifecycle.
    """

    agent_id: str
    category: str
    task_description: str
    expected_output: str
    required_tools: list[str] = Field(default_factory=list)
    must_do: list[str] = Field(default_factory=list)
    must_not_do: list[str] = Field(default_factory=list)
    context_files: list[str] = Field(default_factory=list)
    output_path: str | None = None
    status: str = "pending"
    result: str | None = None


def build_contract(
    agent_id: str,
    category: str,
    task: str,
    **kwargs: str | list[str] | None,
) -> TaskContract:
    """Build a ``TaskContract`` from required fields and optional overrides.

    Args:
        agent_id: The target sub-agent identifier.
        category: Agent category (e.g. "deep-logic").
        task: Task description.
        **kwargs: Additional fields matching ``TaskContract`` attributes
            (expected_output, required_tools, must_do, must_not_do,
            context_files, output_path).

    Returns:
        A fully populated ``TaskContract`` instance.
    """
    raw_output_path = kwargs.get("output_path")
    output_path: str | None = raw_output_path if isinstance(raw_output_path, str) else None

    contract = TaskContract(
        agent_id=agent_id,
        category=category,
        task_description=task,
        expected_output=str(kwargs.get("expected_output", f"Completed: {task}")),
        required_tools=_as_list(kwargs.get("required_tools")),
        must_do=_as_list(kwargs.get("must_do")),
        must_not_do=_as_list(kwargs.get("must_not_do")),
        context_files=_as_list(kwargs.get("context_files")),
        output_path=output_path,
    )
    logger.info("contract_built",
                agent_id=agent_id,
                category=category,
                task=task)
    return contract


def _as_list(value: str | list[str] | None) -> list[str]:
    """Normalise a value to a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def contract_to_prompt(contract: TaskContract) -> str:
    """Generate a structured delegation prompt from a task contract.

    The prompt follows the standard Guinevere delegation format
    with TASK, EXPECTED OUTCOME, REQUIRED TOOLS, MUST DO,
    MUST NOT DO, and CONTEXT sections.

    Args:
        contract: The ``TaskContract`` to convert.

    Returns:
        A multi-line prompt string ready for delegation.
    """
    sections: list[str] = []

    sections.append(f"## TASK\n{contract.task_description}")

    sections.append(f"## EXPECTED OUTCOME\n{contract.expected_output}")

    if contract.required_tools:
        tools = "\n".join(f"- {tool}" for tool in contract.required_tools)
        sections.append(f"## REQUIRED TOOLS\n{tools}")

    if contract.must_do:
        must_do = "\n".join(f"- {item}" for item in contract.must_do)
        sections.append(f"## MUST DO\n{must_do}")

    if contract.must_not_do:
        must_not = "\n".join(f"- {item}" for item in contract.must_not_do)
        sections.append(f"## MUST NOT DO\n{must_not}")

    if contract.context_files:
        context = "\n".join(f"- {f}" for f in contract.context_files)
        sections.append(f"## CONTEXT\nRelevant files:\n{context}")

    if contract.output_path:
        sections.append(f"## OUTPUT\nWrite results to: {contract.output_path}")

    prompt = "\n\n".join(sections)
    logger.info("contract_to_prompt_generated",
                agent_id=contract.agent_id,
                sections=len(sections))
    return prompt
