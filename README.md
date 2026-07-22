# Maya Rig Validator

A PySide6 validation tool for Autodesk Maya that helps identify common rigging
scene issues.

## Features

- Detects duplicate DAG node names and lists their full paths.
- Finds NURBS-curve controllers in the scene.
- Checks controller translate, rotate, and scale values.
- Validates controller naming using a configurable suffix.
- Selects reported nodes directly from the results list.
- Runs as a dock-friendly Maya dialog parented to Maya's main window.

## Requirements

- Autodesk Maya with Python 3 and PySide6 support
- Maya modules: `maya.cmds`, `maya.api.OpenMaya`, and `maya.OpenMayaUI`

PySide6 and shiboken6 are supplied by supported Maya installations and should
be imported from Maya's Python environment.

## Usage

Copy `rig_validator.py` to a folder available on Maya's Python path, then run:

```python
import rig_validator
rig_validator.show_rig_validator()
```

The script also opens the window automatically when executed directly in
Maya's Script Editor.

## Checks

### Duplicate Names

Scans DAG nodes by short name and reports every full path when more than one
object shares the same short name.

### Controller Transforms

Locates transform nodes with NURBS curve shapes and highlights controllers
whose transform values need review.

### Controller Naming

Checks controller names against a suffix entered in the UI, such as `_CTRL`.

