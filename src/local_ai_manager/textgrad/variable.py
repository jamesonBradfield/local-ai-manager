"""Text variables with gradient support."""

from __future__ import annotations

from enum import Enum
from typing import Any


class TextRole(str, Enum):
    """Role of a text variable in conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FEEDBACK = "feedback"


class TextVariable:
    """A text variable that can accumulate gradients.

    TextVariables represent pieces of text that participate in the
    optimization process. They can accumulate gradients (feedback)
    and be updated by an optimizer.

    Example:
        >>> var = TextVariable(
        ...     value="Write a haiku about nature",
        ...     role=TextRole.USER,
        ...     requires_grad=True
        ... )
        >>> var.backward("Make it more evocative")
        >>> print(var.grad)
        Make it more evocative
    """

    def __init__(
        self,
        value: str,
        role: TextRole = TextRole.USER,
        requires_grad: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a text variable.

        Args:
            value: The text content
            role: Role in conversation (system/user/assistant)
            requires_grad: Whether this variable should receive gradients
            metadata: Optional metadata dictionary
        """
        self.value = value
        self.role = role
        self.requires_grad = requires_grad
        self.grad: str | None = None
        self.prev_value: str | None = None
        self.metadata = metadata or {}
        self.update_count = 0

    def backward(self, grad: str) -> None:
        """Accumulate a gradient (feedback).

        Args:
            grad: The gradient/feedback text

        Raises:
            ValueError: If requires_grad is False
        """
        if not self.requires_grad:
            raise ValueError(f"Cannot accumulate gradients for variable with requires_grad=False")
        self.grad = grad

    def update(self, new_value: str) -> None:
        """Update the variable value.

        Stores the previous value for potential rollback.

        Args:
            new_value: The new text value
        """
        self.prev_value = self.value
        self.value = new_value
        self.update_count += 1
        # Clear gradient after update
        self.grad = None

    def rollback(self) -> bool:
        """Rollback to previous value.

        Returns:
            True if rollback succeeded, False if no previous value
        """
        if self.prev_value is None:
            return False
        self.value = self.prev_value
        self.prev_value = None
        self.update_count -= 1
        return True

    def to_message(self) -> dict[str, str]:
        """Convert to OpenAI-style message format.

        Returns:
            Dictionary with role and content keys
        """
        return {"role": self.role.value, "content": self.value}

    def copy(self) -> TextVariable:
        """Create a copy of this variable.

        Returns:
            New TextVariable with same properties
        """
        var = TextVariable(
            value=self.value,
            role=self.role,
            requires_grad=self.requires_grad,
            metadata=self.metadata.copy(),
        )
        var.grad = self.grad
        var.update_count = self.update_count
        return var

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TextVariable(role={self.role.value}, "
            f"requires_grad={self.requires_grad}, "
            f"updates={self.update_count}, "
            f"value='{self.value[:50]}...' if len(self.value) > 50 else '{self.value}')"
        )

    def __str__(self) -> str:
        """String representation showing value."""
        return self.value
