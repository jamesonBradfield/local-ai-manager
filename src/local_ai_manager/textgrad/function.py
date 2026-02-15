"""LLM functions for forward/backward passes."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .variable import TextVariable


class LLMFunction:
    """Wraps llama-server calls as differentiable text functions.

    LLMFunction provides forward and backward passes for text optimization.
    The forward pass generates text using a language model, while the
    backward pass computes text gradients via critique.

    Example:
        >>> func = LLMFunction(
        ...     forward_model="nanbeige-3b",
        ...     backward_model="qwen3-14b",
        ...     temperature=0.7
        ... )
        >>> output = await func.forward(variables)
        >>> gradients = await func.backward(output, target, variables)
    """

    def __init__(
        self,
        forward_model: str,
        backward_model: str | None = None,
        optimizer_model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        base_url: str = "http://localhost:8080",
    ) -> None:
        """Initialize LLM function.

        Args:
            forward_model: Model ID for generation
            backward_model: Model ID for critique (None = use forward_model)
            optimizer_model: Model ID for updates (None = use forward_model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            base_url: Base URL for llama-server API
        """
        self.forward_model = forward_model
        self.backward_model = backward_model or forward_model
        self.optimizer_model = optimizer_model or forward_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.base_url = base_url.rstrip("/")

    async def forward(
        self,
        variables: list[TextVariable],
        system_prompt: str | None = None,
    ) -> str:
        """Execute forward pass (generation).

        Args:
            variables: List of input text variables
            system_prompt: Optional system prompt override

        Returns:
            Generated text output
        """
        import httpx

        # Build messages from variables
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        for var in variables:
            messages.append(var.to_message())

        # Call llama-server completion endpoint
        payload = {
            "model": self.forward_model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "stream": False,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=300.0,
            )
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"]

    async def backward(
        self,
        output: str,
        target: str,
        variables: list[TextVariable],
    ) -> dict[str, str]:
        """Execute backward pass (compute gradients).

        Since llama-server doesn't expose raw logits, we use an LLM
        to generate critiques as text gradients.

        Args:
            output: Current model output
            target: Target/desired output
            variables: Input variables that need gradients

        Returns:
            Dictionary mapping variable roles to gradient text
        """
        import httpx

        # Build critique prompt
        critique_prompt = self._build_critique_prompt(output, target, variables)

        # Generate critique using backward model
        payload = {
            "model": self.backward_model,
            "messages": [{"role": "user", "content": critique_prompt}],
            "temperature": 0.3,  # Lower temp for deterministic critique
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=300.0,
            )
            response.raise_for_status()
            data = response.json()

        critique = data["choices"][0]["message"]["content"]

        # Parse critique into per-variable gradients
        return self._parse_gradients(critique, variables)

    def _build_critique_prompt(
        self,
        output: str,
        target: str,
        variables: list[TextVariable],
    ) -> str:
        """Build prompt for critique generation."""
        var_descriptions = []
        for i, var in enumerate(variables):
            if var.requires_grad:
                var_descriptions.append(f"Variable {i + 1} ({var.role.value}): {var.value[:200]}")

        prompt = f"""You are a prompt optimization assistant. Analyze the difference between the current output and target output, then provide specific feedback on how to improve each input variable.

CURRENT OUTPUT:
{output[:1000]}

TARGET OUTPUT:
{target[:1000]}

INPUT VARIABLES:
{chr(10).join(var_descriptions)}

Provide your feedback as a JSON object with the variable role as the key and the feedback as the value. Example format:

{{
    "system": "Make the prompt more concise",
    "user": "Add more context about the user's domain"
}}

Respond ONLY with valid JSON, no additional text:"""

        return prompt

    def _parse_gradients(
        self,
        critique: str,
        variables: list[TextVariable],
    ) -> dict[str, str]:
        """Parse critique into per-variable gradients.

        Expects JSON format from LLM response.
        Falls back to string splitting if JSON parsing fails.
        """
        gradients = {}

        # Try to parse as JSON first
        try:
            # Find JSON block in the response
            critique_stripped = critique.strip()
            if "{" in critique_stripped and "}" in critique_stripped:
                start = critique_stripped.find("{")
                end = critique_stripped.rfind("}") + 1
                json_str = critique_stripped[start:end]
                parsed = json.loads(json_str)

                if isinstance(parsed, dict):
                    for var in variables:
                        if var.requires_grad and var.role.value in parsed:
                            gradients[var.role.value] = str(parsed[var.role.value])
                    return gradients
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: simple parsing - look for "VARIABLE N" or "(role):" patterns
        lines = critique.split("\n")

        for i, var in enumerate(variables):
            if not var.requires_grad:
                continue

            role_key = var.role.value

            for line in lines:
                line = line.strip()
                if f"({role_key}):" in line.lower() or line.lower().startswith(f"{role_key}:"):
                    if ":" in line:
                        gradient = line.split(":", 1)[1].strip()
                        if gradient:
                            gradients[role_key] = gradient
                            break

            if role_key not in gradients and var.requires_grad:
                gradients[role_key] = critique[:500]

        return gradients

    async def optimize_step(
        self,
        variable: TextVariable,
        gradient: str,
        learning_rate: float = 1.0,
    ) -> str:
        """Apply gradient to update a variable.

        Args:
            variable: Variable to update
            gradient: Gradient/feedback text
            learning_rate: How much to apply the gradient (0.0-2.0)

        Returns:
            Updated variable value
        """
        import httpx

        update_prompt = f"""You are optimizing a prompt. Given the current text and feedback, provide an improved version.

CURRENT TEXT:
{variable.value}

FEEDBACK:
{gradient}

INSTRUCTIONS:
- Maintain the same general intent and style
- Incorporate the feedback to improve the text
- Be specific and actionable
- Keep similar length to the original

Provide only the improved text, no explanation:"""

        payload = {
            "model": self.optimizer_model,
            "messages": [{"role": "user", "content": update_prompt}],
            "temperature": 0.5,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=300.0,
            )
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"LLMFunction(forward={self.forward_model}, "
            f"backward={self.backward_model}, "
            f"temp={self.temperature})"
        )
