# Python Port Requirements

## 1. General Goals
- Recreate the CANopenNode Editor functionality in Python 3 with cross-platform support (Windows, Linux, macOS).
- Prioritize compatibility with the CANopenNode stack, specifically the legacy CANopenNode `.c`/`.h` export workflow.
- Deliver an intuitive, modern graphical interface while preserving power-user features from the C# version.
- Maintain a modular architecture separating core data model logic from the GUI layer.

## 2. Technical Stack
- **Language**: Python 3.11+
- **GUI Toolkit**: PySide6 (Qt 6 bindings) for native-looking, flexible UI components including docking, tree/list views, and dialogs.
- **Packaging & Environment**:
  - Use `poetry` or `pip` with virtual environments; repository will maintain `requirements.txt` for pip consumers.
  - Structure project as installable package (`canopen_node_editor`) with entry point script.
- **Testing**: pytest for unit/integration tests; consider using pytest-qt for GUI-level regression tests.
- **Build/Distribution**: Provide PyInstaller or Briefcase configuration for desktop bundling after MVP.

## 3. Core Functional Requirements
### 3.1 Device Management
- Load, create, and save CANopen device descriptions in EDS (INI) and XDD/XDC/XPD XML formats.
- Support multiple devices open simultaneously via tabbed workspace.
- Track modification state per device; prompt to save when closing or exiting.
- Persist MRU list and application preferences in a per-user config directory.

### 3.2 Object Dictionary Editing
- Display object dictionary in hierarchical view with filtering, sorting, and customizable columns.
- Allow editing of indices/subindices with validation against CANopen rules and data types.
- Provide dialogs to insert predefined profile objects and new custom entries.
- Support layout persistence (column widths/order) per user.

### 3.3 PDO Configuration
- Visualize and edit TPDO/RPDO mappings, COB-IDs, sync/cycle parameters, and mapping entries.
- Reflect validation feedback (invalid mapping lengths, conflicts) inline.
- Offer auto-mapping helpers similar to existing tooling.

### 3.4 Profiles and Modules
- Load default and user-defined profile templates from application and user directories.
- Merge module definitions into existing devices with conflict detection and resolution options.

### 3.5 Reporting and Validation
- Provide validation summary with warnings/errors comparable to the C# report view.
- Generate HTML/PDF reports for documentation.
- Offer search/filter for warnings and navigation to offending items.

### 3.6 CANopenNode Legacy Export (Priority)
- Implement `.c` and `.h` source/header generation matching current C# output for compatibility with the legacy CANopenNode stack.
- Allow export of single device or network set with user-selectable output directory.
- Include regression tests comparing sample outputs between C# and Python implementation.

## 4. User Experience Requirements
- Modern UI theme leveraging Qt's Fusion/Dark style with optional theme switch.
- Responsive layout supporting large tables and resizable panels.
- Keyboard shortcuts mirroring C# app where practical (Ctrl+O, Ctrl+S, etc.).
- Dockable panes for object dictionary, PDO view, properties editor.
- Command palette (Ctrl+K) for quick action search and execution.
- Status bar for context-sensitive feedback and validation summary.

## 5. Non-Functional Requirements
- **Performance**: Handle large object dictionaries (1k+ entries) without UI freezes (use background threads for heavy operations).
- **Reliability**: Robust error handling for malformed files and export failures.
- **Extensibility**: Clean separation to support future export targets (e.g., CANopenNode driver code).
- **Internationalization**: Prepare for future localization (use translation-friendly string handling).
- **Documentation**: Provide user guide and developer docs alongside code.

## 6. Project Structure
```
python_port/
  README.md                 # Port overview and setup instructions
  requirements.txt          # Python dependencies for pip users
  docs/
    csharp_analysis.md      # (symlink or copy) analysis reference
    requirements.md         # This document
    porting_guide.md        # Migration steps
  src/canopen_node_editor/  # Python package with modules
  tests/                    # pytest suite
```

## 7. Dependencies (initial)
Runtime dependencies are declared in `setup.cfg` so that installing the project
automatically provides the required libraries:
- `pyside6`
- `qt-material` (optional modern theming)
- `pydantic` (data model validation)
- `platformdirs` (user configuration directories)
- `jinja2` (HTML reporting templates)

The `requirements.txt` file retains the editable install (`-e .`) alongside the
test tooling (`pytest`, `pytest-qt`) to streamline developer onboarding. Update
both configuration files when adding or removing dependencies.
