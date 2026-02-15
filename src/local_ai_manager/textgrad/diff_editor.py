"""Interactive diff editor for user feedback."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

if TYPE_CHECKING:
    from .variable import TextVariable


class DiffEditor:
    """Interactive diff editor for collecting user feedback.

    Provides a Rich-based interface for users to:
    - View current output
    - Edit to desired target
    - Provide critique/feedback
    - Accept or reject changes

    Example:
        >>> editor = DiffEditor()
        >>> target = await editor.edit_interactively(
        ...     current_output="Hello world",
        ...     iteration=1,
        ...     variables=[system_var, user_var]
        ... )
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize diff editor.

        Args:
            console: Rich console instance (creates default if None)
        """
        self.console = console or Console()

    async def edit_interactively(
        self,
        current_output: str,
        iteration: int,
        variables: list[TextVariable],
        max_iterations: int = 10,
    ) -> tuple[str, str | None]:
        """Interactive editing session.

        Args:
            current_output: Current model output
            iteration: Current iteration number
            variables: Input variables being optimized
            max_iterations: Maximum iterations allowed

        Returns:
            Tuple of (target_output, critique_text)
            If converged, target_output == current_output
        """
        self.console.clear()

        # Show header
        self._show_header(iteration, max_iterations)

        # Show variables
        self._show_variables(variables)

        # Show current output
        self._show_output(current_output, "Current Output")

        # Present options
        self.console.print("\n[bold]Options:[/bold]")
        self.console.print("1. [green]Accept[/green] - Output is good (converged)")
        self.console.print("2. [yellow]Edit[/yellow] - Modify to desired output")
        self.console.print("3. [blue]Critique[/blue] - Describe what needs changing")
        self.console.print("4. [red]Abort[/red] - Cancel optimization")

        choice = Prompt.ask(
            "\nSelect option",
            choices=["1", "2", "3", "4"],
            default="2",
        )

        if choice == "1":
            # Accept as-is
            return current_output, None

        elif choice == "2":
            # Edit to desired output
            target = self._edit_output(current_output)
            return target, None

        elif choice == "3":
            # Provide critique
            critique = self._provide_critique(current_output)
            # Use LLM to generate target from critique
            target = await self._generate_target_from_critique(current_output, critique)
            return target, critique

        else:
            # Abort
            raise WorkflowAborted("User aborted optimization")

    def _show_header(self, iteration: int, max_iterations: int) -> None:
        """Show iteration header."""
        progress = f"[bold blue]Iteration {iteration + 1}/{max_iterations}[/bold blue]"
        self.console.print(Panel(progress, style="blue"))

    def _show_variables(self, variables: list[TextVariable]) -> None:
        """Show input variables."""
        table = Table(title="Input Variables", show_header=True)
        table.add_column("Role", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Grad", style="green")

        for var in variables:
            grad_status = "✓" if var.grad else "-"
            value = var.value[:100] + "..." if len(var.value) > 100 else var.value
            table.add_row(var.role.value, value, grad_status)

        self.console.print(table)

    def _show_output(self, output: str, title: str) -> None:
        """Show output in a panel."""
        # Try to detect and syntax highlight
        syntax = self._detect_syntax(output)

        if syntax:
            panel = Panel(
                Syntax(output, syntax, theme="monokai", word_wrap=True),
                title=title,
                border_style="green" if "Current" in title else "yellow",
            )
        else:
            panel = Panel(
                output,
                title=title,
                border_style="green" if "Current" in title else "yellow",
            )

        self.console.print(panel)

    def _detect_syntax(self, text: str) -> str | None:
        """Detect programming language for syntax highlighting."""
        # Simple heuristics
        if text.strip().startswith(("def ", "class ", "import ", "from ")):
            return "python"
        if text.strip().startswith(("function", "const", "let", "var")):
            return "javascript"
        if "{" in text and "}" in text and ";" in text:
            return "json"
        return None

    def _edit_output(self, current: str) -> str:
        """Allow user to edit output.

        In a real implementation, this would open an external editor
        like vim/emacs or provide inline editing.
        """
        self.console.print("\n[yellow]Edit Mode:[/yellow]")
        self.console.print("Enter desired output below (type 'EDITOR' to use $EDITOR):")

        user_input = Prompt.ask("Desired output", default=current)

        if user_input.upper() == "EDITOR":
            # Open external editor
            import os
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as f:
                f.write(current)
                temp_path = f.name

            editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
            os.system(f'{editor} "{temp_path}"')

            with open(temp_path, "r") as f:
                result = f.read()

            os.unlink(temp_path)
            return result

        return user_input

    def _provide_critique(self, current: str) -> str:
        """Collect critique from user."""
        self.console.print("\n[blue]Critique Mode:[/blue]")
        self.console.print("Describe what needs to change:")

        critique = Prompt.ask("Your feedback")
        return critique

    async def _generate_target_from_critique(
        self,
        current: str,
        critique: str,
    ) -> str:
        """Generate target output from critique using LLM.

        This is a placeholder - in practice, would use the LLM function.
        """
        self.console.print(f"\n[yellow]Generating target from critique...[/yellow]")

        # For now, return current with critique appended
        # In real implementation, would call LLM to apply changes
        return f"{current}\n\n[Applied changes: {critique}]"

    def show_convergence(
        self,
        final_output: str,
        iterations: int,
        converged: bool,
    ) -> None:
        """Show final convergence status."""
        if converged:
            self.console.print(
                f"\n[green bold]✓ Converged after {iterations} iterations![/green bold]"
            )
        else:
            self.console.print(
                f"\n[yellow bold]⚠ Did not converge after {iterations} iterations[/yellow bold]"
            )

        self._show_output(final_output, "Final Output")

    def show_comparison(
        self,
        original: str,
        optimized: str,
    ) -> None:
        """Show side-by-side comparison."""
        table = Table(title="Before / After Comparison")
        table.add_column("Original Prompt", style="red")
        table.add_column("Optimized Prompt", style="green")

        orig = original[:500] + "..." if len(original) > 500 else original
        opt = optimized[:500] + "..." if len(optimized) > 500 else optimized

        table.add_row(orig, opt)
        self.console.print(table)


class WorkflowAborted(Exception):
    """Exception raised when user aborts workflow."""

    pass
