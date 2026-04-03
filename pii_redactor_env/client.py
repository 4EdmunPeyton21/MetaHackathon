"""
pii_redactor_env/client.py
---------------------------
Client for the PII Redactor environment.

Subclasses ``EnvClient`` so that training frameworks (TRL, torchforge, etc.)
and the inference agent can communicate with the server via WebSocket or HTTP.
"""

from __future__ import annotations

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

from pii_redactor_env.models import PIIAction, PIIObservation, PIIState


class PIIRedactorEnv(EnvClient[PIIAction, PIIObservation, PIIState]):
    """
    Client for the PII Redactor OpenEnv environment.

    Usage (async)::

        async with PIIRedactorEnv(base_url="http://localhost:7860") as client:
            result = await client.reset()
            result = await client.step(PIIAction(action_type="bash", command="ls"))

    Usage (sync)::

        with PIIRedactorEnv(base_url="http://localhost:7860").sync() as client:
            result = client.reset()
            result = client.step(PIIAction(action_type="bash", command="ls"))
    """

    def _step_payload(self, action: PIIAction) -> dict:
        """
        Serialize a PIIAction into the JSON payload sent to the server.

        Args:
            action: The action to serialize.

        Returns:
            Dict with ``action_type`` and ``command`` keys.
        """
        return {
            "action_type": action.action_type.value,
            "command": action.command,
        }

    def _parse_result(self, payload: dict) -> StepResult[PIIObservation]:
        """
        Deserialize the server's step response into a StepResult.

        Args:
            payload: Raw JSON response from the server's ``/step`` endpoint.

        Returns:
            StepResult containing the PIIObservation, reward, and done flag.
        """
        obs = PIIObservation(**payload.get("observation", {}))
        return StepResult(
            observation=obs,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> PIIState:
        """
        Deserialize the server's state response into a PIIState.

        Args:
            payload: Raw JSON response from the server's ``/state`` endpoint.

        Returns:
            PIIState instance.
        """
        return PIIState(**payload)
