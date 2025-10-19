# Phase 0 Environment Setup

This document captures the exact steps for preparing a dedicated Python virtual
environment for the CANopenNode Editor port. Following these instructions
ensures a repeatable setup across contributors and CI agents.

## Prerequisites
- Python 3.11 or newer installed on the host machine
- `virtualenv` available (`pip install virtualenv` if missing)
- Git client

## Steps
1. **Create the virtual environment**
   ```bash
   python -m virtualenv .venv
   ```
2. **Activate the environment**
   - **Windows PowerShell**
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - **Windows Command Prompt**
     ```cmd
     .\.venv\Scripts\activate.bat
     ```
   - **macOS/Linux**
     ```bash
     source .venv/bin/activate
     ```
3. **Upgrade tooling inside the environment**
   ```bash
   python -m pip install --upgrade pip
   ```
4. **Install project dependencies**
   ```bash
   pip install -r python_port/requirements.txt
   ```
5. **Verify the bootstrap runs**
   ```bash
   python -m canopen_node_editor
   ```

The final command should print the resolved project directories, confirming the
package imports correctly within the isolated environment.
