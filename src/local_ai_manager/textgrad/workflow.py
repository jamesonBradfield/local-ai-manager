"""Workflow orchestration for textgrad optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models import TextgradWorkflow as WorkflowConfig
    from .function import LLMFunction
    from .optimizer import OptimizerStep, TextOptimizer
    from .variable import TextVariable


@dataclass
class WorkflowResult:
    """Result of a textgrad workflow execution."""

    final_prompt: str
    iterations: int
    converged: bool
    history: list[dict[str, Any]] = field(default_factory=list)
    final_output: str = ""
    error: str | None = None


class TextgradWorkflow:
    """Orchestrates the textgrad optimization workflow.

    This class manages the full optimization loop:
    1. Forward pass (generate output)
    2. User feedback (diff editing)
    3. Backward pass (compute gradients)
    4. Optimizer step (update variables)
    5. Repeat until convergence

    Example:
        >>> workflow = TextgradWorkflow(config)
        >>> result = await workflow.optimize(
        ...     initial_prompt="Write a haiku",
        ...     user_context="about mountains",
        ...     interactive=True
        ... )
    """

    def __init__(
        self,
        config: WorkflowConfig,
        llm_function: LLMFunction | None = None,
        optimizer: TextOptimizer | None = None,
    ) -> None:
        """Initialize workflow.

        Args:
            config: Workflow configuration
            llm_function: LLM function (created from config if None)
            optimizer: Optimizer (created from config if None)
        """
        self.config = config
        self.llm_function = llm_function
        self.optimizer = optimizer
        self._current_iteration = 0
        self._convergence_history: list[float] = []

    async def optimize(
        self,
        initial_prompt: str,
        user_context: str = "",
        interactive: bool = True,
        progress_callback: callable | None = None,
    ) -> WorkflowResult:
        """Run the optimization workflow.

        Args:
            initial_prompt: Starting system prompt
            user_context: User's input/query
            interactive: Whether to use interactive diff editing
            progress_callback: Optional callback(iteration, output, target)

        Returns:
            WorkflowResult with final prompt and metadata
        """
        from .function import LLMFunction
        from .optimizer import TextOptimizer
        from .variable import TextRole, TextVariable

        # Initialize LLM function if not provided
        if self.llm_function is None:
            self.llm_function = LLMFunction(
                forward_model=self.config.forward_model_id,
                backward_model=self.config.backward_model_id,
                optimizer_model=self.config.optimizer_model_id,
            )

        # Initialize optimizer if not provided
        if self.optimizer is None:
            self.optimizer = TextOptimizer(
                llm_function=self.llm_function,
                learning_rate=1.0,
            )

        # Create variables
        variables = [
            TextVariable(
                value=initial_prompt,
                role=TextRole.SYSTEM,
                requires_grad=True,
            ),
            TextVariable(
                value=user_context,
                role=TextRole.USER,
                requires_grad=False,
            ),
        ]

        history = []
        output = ""

        try:
            for iteration in range(self.config.max_iterations):
                self._current_iteration = iteration

                # 1. Forward pass
                output = await self.llm_function.forward(variables)

                # 2. Get user feedback / target
                if interactive:
                    target = await self._get_user_feedback(output, iteration)
                else:
                    # Non-interactive: use convergence check
                    target = await self._auto_convergence_check(output)

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(iteration, output, target)

                # Check for convergence (skip if no target provided)
                if target is not None and self._check_convergence(output, target):
                    return WorkflowResult(
                        final_prompt=variables[0].value,
                        iterations=iteration + 1,
                        converged=True,
                        history=history,
                        final_output=output,
                    )

                # 3. Backward pass (use empty string as fallback if no target)
                gradients = await self.llm_function.backward(output, target or "", variables)

                # Apply gradients to variables
                for var in variables:
                    if var.role.value in gradients:
                        var.backward(gradients[var.role.value])

                # 4. Optimizer step
                variables = await self.optimizer.step(variables)

                # Record iteration
                history.append(
                    {
                        "iteration": iteration,
                        "output": output,
                        "target": target,
                        "gradients": gradients,
                        "system_prompt": variables[0].value,
                    }
                )

                # Update workflow config
                self.config.optimized_prompt = variables[0].value
                self.config.history = history
                self.config.workflow_version += 1

            # Max iterations reached without convergence
            return WorkflowResult(
                final_prompt=variables[0].value,
                iterations=self.config.max_iterations,
                converged=False,
                history=history,
                final_output=output,
            )

        except Exception as e:
            return WorkflowResult(
                final_prompt=variables[0].value if variables else initial_prompt,
                iterations=self._current_iteration,
                converged=False,
                history=history,
                error=str(e),
            )

    async def _get_user_feedback(self, output: str, iteration: int) -> str | None:
        """Get user feedback on current output.

        This method should be overridden or use the DiffEditor
        for interactive CLI usage.

        Args:
            output: Current model output
            iteration: Current iteration number

        Returns:
            Target/desired output, or None if no target provided
        """
        # Default: no target provided - user must supply one
        # In interactive mode, use DiffEditor to get target
        # In non-interactive mode, this causes the loop to continue
        # until max_iterations or manual convergence
        return None

    async def _auto_convergence_check(self, output: str) -> str | None:
        """Automatic convergence check (non-interactive mode).

        Uses heuristics or previous target to determine convergence.
        Returns None if no target is available (non-interactive mode).

        Args:
            output: Current model output

        Returns:
            Target output, or None if no target provided
        """
        # In non-interactive mode without a user-provided target,
        # we cannot determine convergence. Return None to skip
        # the convergence check and continue optimizing.
        return None

    def _check_convergence(self, output: str, target: str | None) -> bool:
        """Check if output has converged to target.

        Args:
            output: Current output
            target: Target output

        Returns:
            True if converged
        """
        if target is None:
            return False

        # Exact match
        if output == target:
            return True

        # Similarity check (simple version)
        # In practice, could use embeddings or other metrics
        if len(output) > 0 and len(target) > 0:
            similarity = self._text_similarity(output, target)
            return similarity >= self.config.convergence_threshold

        return False

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Simple Jaccard similarity on words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 and not words2:
            return 1.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def get_current_state(self) -> dict[str, Any]:
        """Get current workflow state.

        Returns:
            Dictionary with current state
        """
        return {
            "iteration": self._current_iteration,
            "max_iterations": self.config.max_iterations,
            "converged": False,
            "optimized_prompt": self.config.optimized_prompt,
            "history_length": len(self.config.history),
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TextgradWorkflow(id={self.config.id}, "
            f"iteration={self._current_iteration}/{self.config.max_iterations}, "
            f"forward={self.config.forward_model_id})"
        )
