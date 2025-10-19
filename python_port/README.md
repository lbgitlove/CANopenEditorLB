# Python Port Workspace

This directory hosts planning assets and the implementation for porting the
CANopenNode Editor from C# to Python 3.

## Structure
- `config/` – Default configuration templates committed to version control.
- `data/` – Sanitized reference EDS/XDD files and canonical CANopenNode `.c`/`.h` fixtures.
- `docs/` – Analysis, requirements, porting guide, and environment setup notes.
- `src/canopen_node_editor/` – Python package containing application code.
- `tests/` – Pytest suite for validating the Python implementation.
- `requirements.txt` – Python dependencies required for development.

## Getting Started
1. Follow the [Phase 0 environment setup](docs/environment_setup.md) to create a
   dedicated virtual environment.
2. Activate the environment and install dependencies:
   ```bash
   pip install -r python_port/requirements.txt
   ```
3. Launch the editor GUI:
   ```bash
   python -m canopen_node_editor
   ```
   The command boots the Qt application with dockable object dictionary, PDO editor, validation report view, and a command palette. Use Ctrl+K to open the palette or View → Toggle Dark Mode to switch themes.

## Running Tests

Use pytest (with pytest-qt) to run both logic and GUI smoke tests:
```bash
PYTHONPATH=python_port/src pytest python_port/tests
```

## Current Status

- ✅ Phase 0 – environment and scaffolding complete.
- ✅ Phase 1 – core data model, format parsers, validation engine, and CANopenNode `.c`/`.h` export covered by regression tests.
- ✅ Phase 2 – application services for settings, profile discovery, network management, and HTML reporting.
- ✅ Phase 3 – Qt GUI with tabbed workspace, dockable tools, theming, and command palette.
