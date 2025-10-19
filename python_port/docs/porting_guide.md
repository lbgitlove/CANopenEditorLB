# CANopenNode Editor Porting Guide

This guide outlines the recommended process for porting the legacy C# CANopenNode Editor to a modern Python 3 application. Follow the phases sequentially to ensure functional parity and maintainability.

## Phase 0 – Preparation
1. **Environment Setup**
   - Install Python 3.11+, Poetry or virtualenv, and Node.js (optional for UI tooling).
   - Clone the legacy repository and study the C# solution using the analysis notes.
2. **Create Python Project Skeleton**
   - Initialize `python_port/` directory structure (`src/`, `tests/`, `docs/`).
   - Add `requirements.txt` with initial dependency set.
   - Configure linting/formatting (`black`, `isort`, `ruff`) as desired.
3. **Data Samples**
   - Collect representative EDS/XDD files and existing `.c7h` outputs for regression comparison.

## Phase 1 – Core Data Model Port *(Status: Completed in Python port)*
1. **Define Domain Models**
   - Translate `libEDSsharp` classes into Python equivalents using dataclasses/Pydantic models.
   - Mirror enums/constants for object types, data types, access rights, PDO directions.
2. **Parsing Layer**
   - Implement EDS parser using Python's `configparser` (INI) with unit tests covering section/parameter mapping.
   - Implement XDD/XDC/XPD XML parser using `lxml` with schema validation where possible.
   - Ensure merged data produces a unified `Device` model matching C# structure.
3. **Validation & Rules Engine**
   - Port validation routines, including mandatory object checks, value constraints, and communication profile compliance.
   - Provide structured error/warning objects with codes and severities.
4. **Serialization & Export**
   - Implement writers for EDS and XML formats to confirm round-trip fidelity.
   - Generate CANopenNode `.c` and `.h` sources suitable for stack compilation; validate output against canonical fixtures.
5. **Testing**
   - Build extensive pytest suite covering parsing, validation, and export scenarios.

## Phase 2 – Application Services *(Status: Completed in Python port)*
1. **Settings & Persistence**
   - Develop configuration manager storing preferences/MRU in OS-appropriate directories (`appdirs`).
2. **Profile & Module Management**
   - Implement profile repository abstraction that scans install/user directories and exposes metadata.
   - Port module insertion logic with conflict detection.
3. **Network Management**
   - Design service to manage multiple `Device` instances, handle unsaved changes, and coordinate exports.
4. **Reporting**
   - Generate HTML reports using Jinja2 templates; include validation results and summary tables.

## Phase 3 – GUI Implementation *(Status: Completed in Python port)*
The Qt application now provides a tabbed workspace with dockable object dictionary, PDO editor, property inspector, validation report viewer, and a global command palette. A dark/light theme toggle is wired to Qt Material theming and preferences persist across sessions.

1. **UI Architecture**
   - Adopt Model-View-ViewModel (MVVM) or similar pattern to separate logic from Qt widgets.
   - Create main window with tabbed interface for multiple devices.
   - Implement dockable panels for object dictionary, PDO editor, property inspector.
2. **Views & Components**
   - Object Dictionary View: use `QTreeView` with custom models/delegates for editing and validation styling.
   - PDO View: use split panes with tables for TPDO/RPDO configuration and mapping details.
   - Reports View: embed HTML preview using `QTextBrowser` today with the option to upgrade to `QWebEngineView` later.
   - Dialogs: recreate new item/index dialogs, preferences, module selector using Qt Designer or code.
3. **User Experience Enhancements**
   - Apply modern theming (Qt Material) with optional dark mode toggle.
   - Integrate command palette / search to improve navigation.
4. **Accessibility & Localization**
   - Prepare translation files (`.ts`) and ensure UI texts are translatable.

## Phase 4 – Integration & QA
1. **Feature Parity Verification**
   - Compare behavior of Python app to C# version using checklists and sample projects.
   - Ensure `.c7h` export matches byte-for-byte for baseline fixtures.
2. **Automated Testing**
   - Add GUI smoke tests with pytest-qt and regression tests for exports.
   - Configure CI (GitHub Actions) to run linting, tests, and build artifacts.
3. **Documentation**
   - Author user manual and developer setup docs within `python_port/docs/`.
   - Provide migration notes for existing users.
4. **Packaging & Distribution**
   - Create installers/binaries for Windows/macOS/Linux as needed (PyInstaller/Briefcase).
   - Publish versioned releases and changelog.

## Phase 5 – Future Enhancements (Optional)
- Integrate CANopen network simulation hooks.
- Provide plugin interface for custom exporters or validators.
- Add telemetry/analytics respecting privacy to gather usage metrics.

## Deliverables Checklist
- [ ] Python package implementing core CANopen data model and exports.
- [ ] GUI application replicating editor workflows with modern UX.
- [ ] Automated test suite with >80% coverage on core logic.
- [ ] Verified parity for CANopenNode `.c7h` export.
- [ ] Comprehensive documentation set (analysis, requirements, user guide, developer guide).
