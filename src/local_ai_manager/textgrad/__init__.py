"""Textgrad - Text-based gradient descent for prompt optimization.

This module implements textgrad, a framework for optimizing prompts
using gradient descent in text space. It allows users to iteratively
improve prompts by providing feedback on model outputs.
"""

from .variable import TextVariable, TextRole
from .function import LLMFunction
from .optimizer import TextOptimizer, OptimizerStep
from .workflow import TextgradWorkflow, WorkflowResult
from .diff_editor import DiffEditor

__all__ = [
    "TextVariable",
    "TextRole",
    "LLMFunction",
    "TextOptimizer",
    "OptimizerStep",
    "TextgradWorkflow",
    "WorkflowResult",
    "DiffEditor",
]
