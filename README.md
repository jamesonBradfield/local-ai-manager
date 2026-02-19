# Local AI Manager

> **⚠️ BETA SOFTWARE ⚠️**
> 
> This is personal tooling that evolved into something shareable. It works for my daily use case but YMMV.
> 
> **Current Status:**
> - **Windows + Git Bash**: I use this daily. It works for me.
> - **Windows + PowerShell**: Should work, tested occasionally  
> - **Linux/macOS**: Code exists, completely untested. Good luck!

A Python-based management system for local LLM inference with automatic model discovery and Steam game integration.

Built because I was tired of PowerShell and wanted something cleaner.

## What This Actually Is

This is tooling I built for myself that:
- Auto-discovers GGUF models from `~/models`
- Manages llama-server lifecycle
- Pauses AI when I launch Steam games (saves VRAM)
- Has a config file instead of a million PowerShell scripts
- Supports speculative decoding for faster inference
- Includes TextGrad for automatic prompt optimization

I use it daily on Windows with Git Bash. It probably has bugs I haven't hit yet.

## Quick Start (What I Actually Test)

```bash
# Windows + Git Bash (this is what I use)
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager
./Install-LocalAI-Manager.ps1

# If it works:
local-ai start --background
local-ai status
```

## Requirements

- Python 3.10+
- Windows (this is what I use)
- llama-server.exe somewhere in PATH or ~/bin
- Steam installed via Scoop (for the game detection)

Linux/macOS? The code is there but I've never run it. You're in uncharted territory.

## What Works

Based on my actual daily usage:

✅ **Starting/stopping llama-server** - Works  
✅ **Auto-detecting models** - Works  
✅ **Steam game detection** - Works with Scoop Steam  
✅ **Config file management** - Works  
✅ **Basic CLI** - Works  

🤷 **PowerShell** - Should work, I test it sometimes  
🤷 **Everything else** - Implemented but not tested  

## Installation

### Windows (Git Bash) - What I Use

```bash
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager
./Install-LocalAI-Manager.ps1
```

### Windows (PowerShell)

```powershell
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager
.\Install-LocalAI-Manager.ps1
```

### Linux/macOS

```bash
# Clone it
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager

# Try the installer (I have no idea if this works)
./install.sh

# Let me know what breaks
```

## Usage

### Basic stuff that works

```bash
# List models it found
local-ai list-models

# Start with auto-selected model
local-ai start --background

# Check if it's running
local-ai status

# Stop it
local-ai stop

# Watch Steam and auto-manage AI
local-ai steam start
```

### Auto-start on login (Windows)

```bash
# This should work but admin rights needed
local-ai autostart enable
```

### Custom args

```bash
# Pass extra args to llama-server
local-ai start --extra-args "--repeat-penalty 1.1"
```

## Configuration

Config lives at `~/.config/local-ai/local-ai-config.json`:

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8080,
    "models_dir": "~/models",
    "default_model": "nanbeige-3b"
  },
  "models": [
    {
      "id": "nanbeige-3b",
      "name": "Nanbeige 3B",
      "filename_pattern": "(?i)Nanbeige.*3B.*Q4_K_M.*\\.gguf$",
      "ctx_size": 131072,
      "priority": 1
    }
  ]
}
```

## Speculative Decoding

Use a smaller draft model to accelerate generation with a larger model. This can provide 2-3x speedup on supported hardware.

### Setup

```json
{
  "models": [
    {
      "id": "qwen-0.5b",
      "name": "Qwen2.5 0.5B (Draft)",
      "filename_pattern": "(?i)Qwen.*0\\.5B.*\\.gguf$",
      "ctx_size": 32768,
      "priority": 5
    },
    {
      "id": "qwen-7b",
      "name": "Qwen2.5 7B (Main)",
      "filename_pattern": "(?i)Qwen.*7B.*Q4_K_M.*\\.gguf$",
      "ctx_size": 32768,
      "draft_model_id": "qwen-0.5b",
      "draft_ngram_min": 3,
      "priority": 1
    }
  ]
}
```

### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `draft_model_id` | string | `null` | ID of the draft model to use for speculative decoding |
| `draft_ngram_min` | integer | `3` | Minimum n-gram size for draft model matching |

The draft model should be significantly smaller than the main model (e.g., 0.5B for a 7B model) and from the same model family for best results.

## TextGrad (Prompt Optimization)

TextGrad is a text-based gradient descent framework for automatic prompt optimization. It uses LLM-generated feedback to iteratively improve prompts and outputs through gradient-like updates in text space.

### Basic Usage

```python
from local_ai_manager.textgrad import Variable, TextualGradientEngine

# Create variables with initial values
prompt = Variable(
    value="Explain quantum computing to a 10-year-old:",
    role_description="instruction",
    requires_grad=True
)

# Define a loss function using natural language feedback
engine = TextualGradientEngine()

# The engine evaluates and provides gradient feedback
loss = engine.compute_loss(
    prompt,
    target="Clear, accurate explanation with examples",
    evaluation_criteria=[
        "Uses age-appropriate analogies",
        "Avoids jargon without explanation",
        "Includes concrete examples"
    ]
)

# Apply gradients to improve the prompt
prompt = engine.step(prompt, loss, learning_rate=0.1)
print(prompt.value)  # Optimized prompt
```

### Workflow-Based Optimization

For complex multi-step tasks, use the Workflow optimizer:

```python
from local_ai_manager.textgrad import WorkflowOptimizer

workflow = WorkflowOptimizer()

# Add optimization steps
workflow.add_step(
    name="brainstorm",
    prompt="Generate 5 creative ideas for {topic}",
    output_role="raw_ideas"
)

workflow.add_step(
    name="refine",
    prompt="Evaluate and improve these ideas: {brainstorm}",
    output_role="refined_ideas",
    feedback_prompt="Are these ideas novel and actionable?"
)

# Optimize the entire workflow
result = workflow.optimize(
    inputs={"topic": "sustainable packaging"},
    num_iterations=3
)
```

### Diff Editor

Track changes between prompt iterations:

```python
from local_ai_manager.textgrad import DiffEditor

editor = DiffEditor()

# View changes between versions
changes = editor.compare(before="Explain ML", after="Explain machine learning with examples")
print(changes.summary)  # "Added context and specificity"
```

### Key Features

- **Natural Language Gradients**: Uses LLM feedback instead of numerical gradients
- **Variable Tracking**: Automatically tracks which outputs need optimization
- **Multi-Step Workflows**: Chain multiple optimization steps
- **Persistence**: Save and resume optimization sessions
- **Diff Visualization**: See exactly what changed between iterations

### Configuration

```python
from local_ai_manager.textgrad import TextualGradientConfig

config = TextualGradientConfig(
    llm_client=your_llm_client,  # Any OpenAI-compatible client
    max_iterations=10,
    convergence_threshold=0.01,
    verbose=True
)

engine = TextualGradientEngine(config=config)
```

## Troubleshooting

### Command not found

```bash
# Check if it's in PATH
which local-ai

# If not, add ~/.local/bin to PATH
export PATH="$PATH:$HOME/.local/bin"
```

### Server won't start

```bash
# Check logs
cat ~/.local/log/llama-server-*.log

# Try running llama-server directly to see the error
llama-server.exe --model ~/models/your-model.gguf
```

### Steam detection not working

Make sure Steam is installed via Scoop and logs to `~/scoop/apps/steam/current/logs/gameprocess_log.txt`

## What's Actually Tested

| Feature | Status | Notes |
|---------|--------|-------|
| Core server management | ✅ Works | Daily use |
| Git Bash integration | ✅ Works | Daily use |
| Model auto-discovery | ✅ Works | Daily use |
| Steam game detection | ✅ Works | With Scoop |
| Config file | ✅ Works | JSON-based |
| PowerShell | ⚠️ Sometimes | Tested occasionally |
| Autostart | ⚠️ Should work | Needs admin rights |
| Linux | ❓ Unknown | Code exists, never ran |
| macOS | ❓ Unknown | Code exists, never ran |

## Contributing

Found a bug? That's expected. Open an issue.

Want to fix Linux/macOS support? That would be awesome. PRs welcome.

Want to add features? Go for it, just don't break my daily workflow.

## Why I Built This

I had a dozen PowerShell scripts that were:
- Hard to maintain
- Scattered everywhere
- Required editing to change models
- Didn't handle Steam games well

Now I have:
- One config file
- A simple CLI
- Auto-detection of models
- Steam integration

It's not perfect but it's better than what I had.

## License

MIT - Do whatever you want. If it breaks, you get to keep both pieces.

## Support

This is a personal project I share because why not. I fix bugs when they annoy me. Use at your own risk.

If you want something production-ready with enterprise support, this isn't it.

---

**TL;DR:** Works for me on Windows with Git Bash. Everything else is bonus territory.
