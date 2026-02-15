"""Optimizer for updating text variables based on gradients."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .function import LLMFunction
    from .variable import TextVariable


@dataclass
class OptimizerStep:
    """Record of an optimization step."""

    iteration: int
    variable_role: str
    old_value: str
    new_value: str
    gradient: str
    loss: float | None = None


class TextOptimizer:
    """Optimizes text variables using gradients.

    TextOptimizer applies gradients to update text variables,
    tracking the optimization history for analysis and rollback.

    Example:
        >>> optimizer = TextOptimizer(
        ...     llm_function=func,
        ...     learning_rate=1.0,
        ...     momentum=0.9
        ... )
        >>> await optimizer.step(variables)
    """

    def __init__(
        self,
        llm_function: LLMFunction,
        learning_rate: float = 1.0,
        momentum: float = 0.0,
        max_history: int = 100,
    ) -> None:
        """Initialize optimizer.

        Args:
            llm_function: LLM function for applying gradients
            learning_rate: Step size for updates (0.0-2.0)
            momentum: Momentum for gradient accumulation (0.0-1.0)
            max_history: Maximum number of steps to keep in history
        """
        self.llm_function = llm_function
        self.lr = learning_rate
        self.momentum = momentum
        self.max_history = max_history
        self.history: list[OptimizerStep] = []
        self.momentum_buffer: dict[str, str] = {}

    async def step(
        self,
        variables: list[TextVariable],
    ) -> list[TextVariable]:
        """Execute one optimization step.

        Args:
            variables: List of variables to optimize

        Returns:
            Updated list of variables
        """
        updated = []

        for var in variables:
            if not var.requires_grad or not var.grad:
                updated.append(var)
                continue

            # Apply momentum if enabled
            if self.momentum > 0:
                grad = self._apply_momentum(var)
            else:
                grad = var.grad

            # Scale gradient by learning rate
            if self.lr != 1.0:
                grad = await self._scale_gradient(var, grad, self.lr)

            # Update variable using LLM
            new_value = await self.llm_function.optimize_step(var, grad, self.lr)

            # Record step
            step = OptimizerStep(
                iteration=len(self.history),
                variable_role=var.role.value,
                old_value=var.value,
                new_value=new_value,
                gradient=grad,
            )
            self.history.append(step)

            # Trim history if needed
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history :]

            # Update variable
            var.update(new_value)
            updated.append(var)

        return updated

    def _apply_momentum(self, var: TextVariable) -> str:
        """Apply momentum to gradient.

        Args:
            var: Variable with current gradient

        Returns:
            Momentum-adjusted gradient
        """
        role = var.role.value

        if role not in self.momentum_buffer:
            self.momentum_buffer[role] = var.grad or ""
            return var.grad or ""

        # Combine current gradient with momentum buffer
        prev = self.momentum_buffer[role]
        curr = var.grad or ""

        # Simple text combination (in practice, might use embeddings)
        if self.momentum >= 0.5:
            # Keep more of previous gradient
            combined = f"{prev} Additionally: {curr}"
        else:
            # Keep more of current gradient
            combined = f"{curr} (Previous concern: {prev})"

        self.momentum_buffer[role] = combined
        return combined

    async def _scale_gradient(
        self,
        var: TextVariable,
        grad: str,
        scale: float,
    ) -> str:
        """Scale gradient by learning rate.

        For text, we adjust the intensity of the feedback.

        Args:
            var: Variable being optimized
            grad: Gradient text
            scale: Learning rate (0.0-2.0)

        Returns:
            Scaled gradient text
        """
        if scale == 1.0:
            return grad

        if scale < 0.5:
            return f"Slightly adjust: {grad}"
        elif scale > 1.5:
            return f"IMPORTANT - Major change needed: {grad}"
        else:
            return grad

    def rollback(self, steps: int = 1) -> bool:
        """Rollback last N optimization steps.

        Args:
            steps: Number of steps to rollback

        Returns:
            True if rollback succeeded
        """
        if steps > len(self.history):
            return False

        # Rollback in reverse order
        for _ in range(steps):
            if not self.history:
                break
            step = self.history.pop()
            # Note: Actual rollback of variables would need reference
            # This is simplified - full implementation needs variable tracking

        return True

    def get_history(self) -> list[OptimizerStep]:
        """Get optimization history.

        Returns:
            List of optimization steps
        """
        return self.history.copy()

    def clear_history(self) -> None:
        """Clear optimization history."""
        self.history.clear()
        self.momentum_buffer.clear()

    def __repr__(self) -> str:
        """String representation."""
        return f"TextOptimizer(lr={self.lr}, momentum={self.momentum}, history={len(self.history)})"
