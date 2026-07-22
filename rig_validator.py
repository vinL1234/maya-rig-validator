from PySide6 import QtCore, QtGui, QtWidgets
from maya import OpenMayaUI as omui
from shiboken6 import wrapInstance
import maya.cmds as cmds
import maya.api.OpenMaya as om


WINDOW_NAME = "RigValidatorWindow"
ERROR_COLOR = QtGui.QColor(220, 70, 70)
DETAIL_COLOR = QtGui.QColor(128, 128, 128)
ROOT_COLOR = QtGui.QColor(70, 130, 180)

CHECK_COLUMN = 0
RESULT_COLUMN = 1
DETAILS_COLUMN = 2
FIX_COLUMN = 3
STATUS_COLUMN = 4


def get_maya_main_window():
    """Return Maya's main window as a Qt widget."""
    main_window_ptr = omui.MQtUtil.mainWindow()
    if main_window_ptr is None:
        return None
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


class RigValidatorWindow(QtWidgets.QDialog):

    def __init__(self, parent=get_maya_main_window()):
        super().__init__(parent)
        self.setObjectName(WINDOW_NAME)
        self.setWindowTitle("Rig Validator")
        self.resize(780, 560)

        self.results_are_stale = False
        self.ignore_scene_changes = False
        self.scene_callback_ids = []
        self.watched_node_handles = set()

        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.update_default_naming_values()
        self.update_naming_inputs()
        self.install_global_scene_callbacks()

    def create_widgets(self):
        """Create all widgets."""
        self.title_label = QtWidgets.QLabel("Rig Validator")
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)

        self.options_group = QtWidgets.QGroupBox("Scan Options")
        self.duplicate_names_checkbox = QtWidgets.QCheckBox(
            "Duplicate Names"
        )
        self.controller_transforms_checkbox = QtWidgets.QCheckBox(
            "Controller Transforms"
        )
        self.naming_rules_checkbox = QtWidgets.QCheckBox(
            "Naming Rules"
        )
        self.root_names_checkbox = QtWidgets.QCheckBox(
            "Root Joints"
        )

        self.node_type_combo = QtWidgets.QComboBox()
        self.node_type_combo.addItems(
            [
                "Controller Name",
                "Mesh Name",
                "Joint Name",
            ]
        )

        self.naming_mode_combo = QtWidgets.QComboBox()
        self.naming_mode_combo.addItems(
            [
                "Prefix",
                "Suffix",
                "Prefix + Suffix",
            ]
        )

        # Editable combo boxes let the user choose a preset value
        # or type a custom prefix/suffix.
        self.prefix_combo = QtWidgets.QComboBox()
        self.prefix_combo.setEditable(True)
        self.prefix_combo.addItems(
            [
                "",
                "L_",
                "R_",
                "C_",
                "CHR_",
                "ENV_",
                "PROP_",
                "FK_",
                "IK_",
            ]
        )
        self.prefix_combo.setCurrentText("")
        self.prefix_combo.lineEdit().setPlaceholderText(
            "Choose or type a prefix"
        )

        self.suffix_combo = QtWidgets.QComboBox()
        self.suffix_combo.setEditable(True)
        self.suffix_combo.addItems(
            [
                "",
                "_CTRL",
                "_JNT",
                "_GEO",
                "_GRP",
                "_LOC",
                "_MSH",
                "_OFF",
                "_SDK",
            ]
        )
        self.suffix_combo.setCurrentText("_CTRL")
        self.suffix_combo.lineEdit().setPlaceholderText(
            "Choose or type a suffix"
        )

        self.select_all_checkbox = QtWidgets.QCheckBox(
            "Select All Scan Options"
        )
        self.scan_button = QtWidgets.QPushButton("Scan")
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.setEnabled(False)
        self.apply_fixes_button = QtWidgets.QPushButton(
            "Apply Selected Fixes"
        )

        self.result_label = QtWidgets.QLabel("Scan Results")
        self.status_label = QtWidgets.QLabel("Status: Ready")

        self.result_table = QtWidgets.QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(
            ["Fix?", "Result", "Details", "Fix", "Status"]
        )
        self.result_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.result_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )
        self.result_table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
        )
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setAlternatingRowColors(True)

        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(
            CHECK_COLUMN,
            QtWidgets.QHeaderView.ResizeToContents,
        )
        header.setSectionResizeMode(
            RESULT_COLUMN,
            QtWidgets.QHeaderView.ResizeToContents,
        )
        header.setSectionResizeMode(
            DETAILS_COLUMN,
            QtWidgets.QHeaderView.Stretch,
        )
        header.setSectionResizeMode(
            FIX_COLUMN,
            QtWidgets.QHeaderView.Stretch,
        )
        header.setSectionResizeMode(
            STATUS_COLUMN,
            QtWidgets.QHeaderView.ResizeToContents,
        )

        self.scan_checkboxes = (
            self.duplicate_names_checkbox,
            self.controller_transforms_checkbox,
            self.naming_rules_checkbox,
            self.root_names_checkbox,
        )

    def create_layouts(self):
        """Arrange widgets."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.title_label)
        main_layout.addSpacing(8)

        options_layout = QtWidgets.QVBoxLayout(self.options_group)

        first_row = QtWidgets.QHBoxLayout()
        first_row.addWidget(self.duplicate_names_checkbox)
        first_row.addWidget(self.controller_transforms_checkbox)
        first_row.addWidget(self.root_names_checkbox)
        first_row.addStretch()
        options_layout.addLayout(first_row)

        second_row = QtWidgets.QHBoxLayout()
        second_row.addWidget(self.naming_rules_checkbox)
        second_row.addWidget(self.node_type_combo)
        second_row.addWidget(self.naming_mode_combo)
        second_row.addWidget(self.prefix_combo, stretch=1)
        second_row.addWidget(self.suffix_combo, stretch=1)
        options_layout.addLayout(second_row)
        options_layout.addWidget(self.select_all_checkbox)

        main_layout.addWidget(self.options_group)

        action_layout = QtWidgets.QHBoxLayout()
        action_layout.addWidget(self.scan_button)
        action_layout.addWidget(self.refresh_button)
        action_layout.addWidget(self.apply_fixes_button)
        main_layout.addLayout(action_layout)

        main_layout.addSpacing(8)
        main_layout.addWidget(self.result_label)
        main_layout.addWidget(self.result_table)
        main_layout.addWidget(self.status_label)

    def create_connections(self):
        """Connect signals."""
        self.scan_button.clicked.connect(self.scan_selected)
        self.refresh_button.clicked.connect(self.refresh_results)
        self.apply_fixes_button.clicked.connect(
            self.apply_selected_fixes
        )
        self.select_all_checkbox.toggled.connect(
            self.set_all_options
        )
        self.naming_rules_checkbox.toggled.connect(
            self.update_naming_inputs
        )
        self.naming_mode_combo.currentTextChanged.connect(
            self.update_naming_inputs
        )
        self.node_type_combo.currentTextChanged.connect(
            self.update_default_naming_values
        )

        for checkbox in self.scan_checkboxes:
            checkbox.stateChanged.connect(self.update_select_all)

        self.result_table.cellDoubleClicked.connect(
            self.handle_table_double_click
        )

    def install_global_scene_callbacks(self):
        """Install callbacks for scene-wide structural changes."""
        self.remove_scene_callbacks()

        callback_specs = (
            (om.MDagMessage.addParentAddedCallback, self.on_parent_changed),
            (om.MDagMessage.addParentRemovedCallback, self.on_parent_changed),
        )

        for add_callback, callback_function in callback_specs:
            try:
                callback_id = add_callback(callback_function)
                self.scene_callback_ids.append(callback_id)
            except Exception as error:
                cmds.warning(f"Could not install DAG callback: {error}")

        for message_type in (
            om.MSceneMessage.kAfterOpen,
            om.MSceneMessage.kAfterNew,
        ):
            try:
                callback_id = om.MSceneMessage.addCallback(
                    message_type,
                    self.on_scene_replaced,
                )
                self.scene_callback_ids.append(callback_id)
            except Exception as error:
                cmds.warning(f"Could not install scene callback: {error}")

    def register_result_name_callbacks(self):
        """Watch result nodes and their ancestors for name changes."""
        self.remove_name_callbacks()
        self.watched_node_handles.clear()

        node_paths = set()

        for row in range(self.result_table.rowCount()):
            result_item = self.result_table.item(row, RESULT_COLUMN)
            if result_item is None:
                continue

            row_data = result_item.data(QtCore.Qt.UserRole)
            if not row_data:
                continue

            node_name = row_data.get("node")
            if not node_name or not cmds.objExists(node_name):
                continue

            parts = [part for part in node_name.split("|") if part]
            current_path = ""
            for part in parts:
                current_path += "|" + part
                if cmds.objExists(current_path):
                    node_paths.add(current_path)

        for node_path in node_paths:
            try:
                selection = om.MSelectionList()
                selection.add(node_path)
                node_object = selection.getDependNode(0)
                handle = om.MObjectHandle(node_object)
                handle_hash = handle.hashCode()

                if handle_hash in self.watched_node_handles:
                    continue

                name_callback_id = om.MNodeMessage.addNameChangedCallback(
                    node_object,
                    self.on_node_renamed,
                )
                destroyed_callback_id = (
                    om.MNodeMessage.addNodeDestroyedCallback(
                        node_object,
                        self.on_node_destroyed,
                    )
                )
                self.scene_callback_ids.extend(
                    [name_callback_id, destroyed_callback_id]
                )
                self.watched_node_handles.add(handle_hash)
            except Exception as error:
                cmds.warning(
                    f"Could not watch node '{node_path}': {error}"
                )

    def remove_name_callbacks(self):
        """Remove node-name callbacks while keeping global callbacks."""
        # Reinstalling all callbacks is simpler and prevents duplicate IDs.
        self.remove_scene_callbacks()
        self.install_global_scene_callbacks()


    def remove_scene_callbacks(self):
        """Remove every Maya callback owned by this window."""
        for callback_id in self.scene_callback_ids:
            try:
                om.MMessage.removeCallback(callback_id)
            except Exception:
                pass

        self.scene_callback_ids = []
        self.watched_node_handles.clear()

    def on_node_renamed(self, node, previous_name, client_data=None):
        """Handle a watched node or ancestor being renamed."""
        self.mark_results_stale("A watched node was renamed")

    def on_node_destroyed(self, client_data=None):
        """Handle a watched result node being deleted."""
        self.mark_results_stale("A watched node was deleted")

    def on_parent_changed(self, child, parent, client_data=None):
        """Handle DAG parenting changes."""
        self.mark_results_stale("The DAG hierarchy changed")

    def on_scene_replaced(self, client_data=None):
        """Clear results after opening or creating a scene."""
        if self.ignore_scene_changes:
            return

        self.result_table.setRowCount(0)
        self.results_are_stale = False
        self.refresh_button.setEnabled(False)
        self.apply_fixes_button.setEnabled(True)
        self.status_label.setText(
            "Status: Scene changed. Run a new scan."
        )

    def mark_results_stale(self):
        """Mark table results as outdated and prevent unsafe fixes."""
        reason="Scene data changed"
        if self.ignore_scene_changes:
            return
        if self.result_table.rowCount() == 0:
            return
        if self.results_are_stale:
            return

        self.results_are_stale = True
        self.refresh_button.setEnabled(True)
        self.apply_fixes_button.setEnabled(False)
        self.status_label.setText(
            f"Status: {reason}. Please refresh the scan results."
        )

        stale_brush = QtGui.QBrush(DETAIL_COLOR)
        for row in range(self.result_table.rowCount()):
            for column in range(self.result_table.columnCount()):
                item = self.result_table.item(row, column)
                if item is not None:
                    item.setForeground(stale_brush)
                    item.setToolTip(
                        "This result may be outdated. Click Refresh."
                    )

    def refresh_results(self):
        """Run the selected checks again and rebuild callbacks."""
        self.scan_selected()

    def closeEvent(self, event):
        """Clean up callbacks when the window closes."""
        self.remove_scene_callbacks()
        super().closeEvent(event)

    def set_all_options(self, checked):
        """Set all scan options to the same checked state."""
        for checkbox in self.scan_checkboxes:
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)
        self.update_naming_inputs()

    def update_select_all(self):
        """Synchronize the Select All checkbox."""
        all_checked = True
        for checkbox in self.scan_checkboxes:
            if not checkbox.isChecked():
                all_checked = False
                break

        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(all_checked)
        self.select_all_checkbox.blockSignals(False)

    def update_naming_inputs(self):
        """Enable naming controls based on the selected rule."""
        enabled = self.naming_rules_checkbox.isChecked()
        naming_mode = self.naming_mode_combo.currentText()

        self.node_type_combo.setEnabled(enabled)
        self.naming_mode_combo.setEnabled(enabled)

        use_prefix = naming_mode in (
            "Prefix",
            "Prefix + Suffix",
        )
        use_suffix = naming_mode in (
            "Suffix",
            "Prefix + Suffix",
        )

        self.prefix_combo.setEnabled(
            enabled and use_prefix
        )
        self.suffix_combo.setEnabled(
            enabled and use_suffix
        )

    def update_default_naming_values(self):
        """Set a useful default suffix for the selected node type."""
        default_suffixes = {
            "Controller Name": "_CTRL",
            "Mesh Name": "_GEO",
            "Joint Name": "_JNT",
        }

        node_type = self.node_type_combo.currentText()
        default_suffix = default_suffixes.get(node_type, "")

        self.suffix_combo.setCurrentText(default_suffix)

    def scan_selected(self):
        """Run all selected checks."""
        selected = []
        for checkbox in self.scan_checkboxes:
            if checkbox.isChecked():
                selected.append(checkbox)

        if not selected:
            self.status_label.setText(
                "Status: Please select at least one scan option"
            )
            return

        if self.naming_rules_checkbox.isChecked():
            naming_mode = self.naming_mode_combo.currentText()
            prefix = self.prefix_combo.currentText().strip()
            suffix = self.suffix_combo.currentText().strip()

            if naming_mode in ("Prefix", "Prefix + Suffix"):
                if not prefix:
                    self.status_label.setText(
                        "Status: Please enter a prefix"
                    )
                    self.prefix_combo.setFocus()
                    return

            if naming_mode in ("Suffix", "Prefix + Suffix"):
                if not suffix:
                    self.status_label.setText(
                        "Status: Please enter a suffix"
                    )
                    self.suffix_combo.setFocus()
                    return

        self.ignore_scene_changes = True
        try:
            self.result_table.setRowCount(0)
            total_issues = 0

            if self.duplicate_names_checkbox.isChecked():
                total_issues += self.append_duplicate_name_results()
            if self.controller_transforms_checkbox.isChecked():
                total_issues += self.append_transform_results()
            if self.naming_rules_checkbox.isChecked():
                total_issues += self.append_naming_rule_results()
            if self.root_names_checkbox.isChecked():
                total_issues += self.append_root_joint_results()
        finally:
            self.ignore_scene_changes = False

        self.results_are_stale = False
        self.refresh_button.setEnabled(False)
        self.apply_fixes_button.setEnabled(True)
        self.register_result_name_callbacks()

        self.status_label.setText(
            f"Status: Scan complete - {total_issues} issue(s) found"
        )

    def make_item_read_only(self, item):
        """Remove editing from a table item."""
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)

    def add_result_row(
        self,
        result_text,
        details="",
        fix_text="",
        status="",
        node_name=None,
        fix_type=None,
        checkable=True,
        fix_editable=False,
        bold=False,
        color=None,
        tooltip=None,
    ):
        """Add one validation result row."""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)

        check_item = QtWidgets.QTableWidgetItem()
        result_item = QtWidgets.QTableWidgetItem(result_text)
        details_item = QtWidgets.QTableWidgetItem(details)
        fix_item = QtWidgets.QTableWidgetItem(fix_text)
        status_item = QtWidgets.QTableWidgetItem(status)

        result_item.setData(
            QtCore.Qt.UserRole,
            {
                "node": node_name,
                "fix_type": fix_type,
            },
        )

        if checkable:
            check_item.setFlags(
                QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsUserCheckable
            )
            check_item.setCheckState(QtCore.Qt.Unchecked)
        else:
            check_item.setFlags(
                QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
            )

        self.make_item_read_only(result_item)
        self.make_item_read_only(details_item)
        self.make_item_read_only(status_item)

        if not fix_editable:
            self.make_item_read_only(fix_item)

        items = (
            check_item,
            result_item,
            details_item,
            fix_item,
            status_item,
        )

        if bold:
            for item in items:
                font = item.font()
                font.setBold(True)
                item.setFont(font)

        if color is not None:
            brush = QtGui.QBrush(color)
            result_item.setForeground(brush)
            status_item.setForeground(brush)

        if tooltip:
            for item in items:
                item.setToolTip(tooltip)

        for column, item in enumerate(items):
            self.result_table.setItem(row, column, item)

        return row

    def add_section(self, title, count):
        """Add a section heading spanning all columns."""
        if self.result_table.rowCount():
            self.result_table.insertRow(self.result_table.rowCount())

        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        self.result_table.setSpan(row, 0, 1, 5)

        item = QtWidgets.QTableWidgetItem(f"{title}: {count}")
        self.make_item_read_only(item)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.result_table.setItem(row, 0, item)

    def append_duplicate_name_results(self):
        """Add duplicate names with editable default fixes."""
        duplicates = find_duplicate_names()
        count = 0

        for paths in duplicates.values():
            count += len(paths)

        self.add_section("Duplicated Objects", count)

        for short_name, paths in duplicates.items():
            for index, path in enumerate(paths, start=1):
                parent_path = "|".join(path.split("|")[:-1])
                suggested_name = f"{short_name}_{index:02d}"

                self.add_result_row(
                    result_text=short_name,
                    details=parent_path,
                    fix_text=suggested_name,
                    status="Duplicate",
                    node_name=path,
                    fix_type="rename_duplicate",
                    checkable=True,
                    fix_editable=True,
                    bold=True,
                    color=ERROR_COLOR,
                    tooltip=path,
                )

        return count

    def append_transform_results(self):
        """Add controllers whose transforms are not at defaults."""
        invalid_controllers = self.find_invalid_controller_transforms()
        self.add_section(
            "Invalid Controller Transforms",
            len(invalid_controllers),
        )

        for controller, errors in invalid_controllers.items():
            self.add_result_row(
                result_text=controller.split("|")[-1],
                details=", ".join(errors),
                fix_text="Reset Transform",
                status="Invalid Transform",
                node_name=controller,
                fix_type="reset_transform",
                checkable=True,
                fix_editable=False,
                bold=True,
                color=ERROR_COLOR,
                tooltip=controller,
            )

        return len(invalid_controllers)

    def append_naming_rule_results(self):
        """Add naming-rule results for controllers, meshes, or joints."""
        node_type = self.node_type_combo.currentText()
        naming_mode = self.naming_mode_combo.currentText()
        prefix = self.prefix_combo.currentText().strip()
        suffix = self.suffix_combo.currentText().strip()

        invalid_nodes = []

        for node in find_naming_nodes(node_type):
            short_name = node.split("|")[-1]

            if not is_valid_name(
                short_name,
                naming_mode,
                prefix,
                suffix,
            ):
                invalid_nodes.append(node)

        section_title = f"Invalid {node_type}s"
        self.add_section(section_title, len(invalid_nodes))

        for node in invalid_nodes:
            short_name = node.split("|")[-1]
            suggested_name = build_suggested_name(
                short_name,
                naming_mode,
                prefix,
                suffix,
            )

            details = f"{node_type} / {naming_mode}"

            self.add_result_row(
                result_text=short_name,
                details=details,
                fix_text=suggested_name,
                status="Invalid Name",
                node_name=node,
                fix_type="rename_node",
                checkable=True,
                fix_editable=True,
                bold=True,
                color=ERROR_COLOR,
                tooltip=node,
            )

        return len(invalid_nodes)

    def append_root_joint_results(self):
        """Display root-joint results without automatic fixes."""
        root_joints = find_root_joints()

        if len(root_joints) == 1:
            issue_count = 0
        elif not root_joints:
            issue_count = 1
        else:
            issue_count = len(root_joints)

        self.add_section("Root Joints", issue_count)

        if not root_joints:
            self.add_result_row(
                result_text="No root joint found",
                details="Create or identify it manually.",
                fix_text="Manual Review",
                status="Missing",
                checkable=False,
                color=ERROR_COLOR,
            )
            return issue_count

        for root_joint in root_joints:
            if len(root_joints) > 1:
                status = "Multiple Roots"
                color = ROOT_COLOR
                fix_text = "Manual Review"
            else:
                status = "Valid"
                color = DETAIL_COLOR
                fix_text = "No Fix Needed"

            self.add_result_row(
                result_text=root_joint.split("|")[-1],
                details="Root joint",
                fix_text=fix_text,
                status=status,
                node_name=root_joint,
                checkable=False,
                bold=True,
                color=color,
                tooltip=root_joint,
            )

        return issue_count

    def find_invalid_controller_transforms(self):
        """Return controllers with non-default transforms."""
        invalid_controllers = {}
        expected_values = {
            "translateX": 0,
            "translateY": 0,
            "translateZ": 0,
            "rotateX": 0,
            "rotateY": 0,
            "rotateZ": 0,
            "scaleX": 1,
            "scaleY": 1,
            "scaleZ": 1,
        }

        for controller in find_controllers():
            errors = []
            for attribute, expected_value in expected_values.items():
                current_value = cmds.getAttr(
                    f"{controller}.{attribute}"
                )
                if current_value != expected_value:
                    errors.append(f"{attribute} = {current_value}")

            if errors:
                invalid_controllers[controller] = errors

        return invalid_controllers

    def handle_table_double_click(self, row, column):
        """Edit an editable Fix cell or select the Maya node."""
        if column == FIX_COLUMN:
            fix_item = self.result_table.item(row, FIX_COLUMN)
            if fix_item is not None:
                if fix_item.flags() & QtCore.Qt.ItemIsEditable:
                    self.result_table.editItem(fix_item)
                    return

        self.select_result(row)

    def select_result(self, row):
        """Select the Maya node stored in a result row."""
        result_item = self.result_table.item(row, RESULT_COLUMN)
        if result_item is None:
            return

        row_data = result_item.data(QtCore.Qt.UserRole)
        if not row_data:
            return

        node_name = row_data.get("node")
        if not node_name:
            return

        if not cmds.objExists(node_name):
            cmds.warning(f"Node no longer exists: {node_name}")
            return

        cmds.select(node_name, replace=True)

    def apply_selected_fixes(self):
        """Apply all checked fixes."""
        if self.results_are_stale:
            self.status_label.setText(
                "Status: Results are outdated. Click Refresh first."
            )
            return

        selected_fixes = []

        for row in range(self.result_table.rowCount()):
            check_item = self.result_table.item(row, CHECK_COLUMN)
            result_item = self.result_table.item(row, RESULT_COLUMN)

            if check_item is None or result_item is None:
                continue
            if check_item.checkState() != QtCore.Qt.Checked:
                continue

            row_data = result_item.data(QtCore.Qt.UserRole)
            if not row_data:
                continue

            fix_item = self.result_table.item(row, FIX_COLUMN)
            fix_text = ""
            if fix_item is not None:
                fix_text = fix_item.text().strip()

            selected_fixes.append(
                {
                    "node": row_data.get("node"),
                    "fix_type": row_data.get("fix_type"),
                    "fix_text": fix_text,
                }
            )

        if not selected_fixes:
            self.status_label.setText(
                "Status: Please check at least one result"
            )
            return

        # Rename children before parents because parent renaming changes paths.
        selected_fixes.sort(
            key=lambda data: (
                data["node"].count("|") if data["node"] else 0
            ),
            reverse=True,
        )

        success_count = 0
        failed_count = 0
        self.ignore_scene_changes = True
        cmds.undoInfo(openChunk=True)

        try:
            for fix_data in selected_fixes:
                success = self.apply_one_fix(fix_data)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
        finally:
            cmds.undoInfo(closeChunk=True)
            self.ignore_scene_changes = False

        # Rescan to refresh paths and remove resolved rows.
        self.scan_selected()
        self.status_label.setText(
            f"Status: {success_count} fixed, {failed_count} failed"
        )

    def apply_one_fix(self, fix_data):
        """Apply one selected fix."""
        node_name = fix_data["node"]
        fix_type = fix_data["fix_type"]
        fix_text = fix_data["fix_text"]

        if not node_name or not cmds.objExists(node_name):
            return False

        try:
            if fix_type in ("rename_duplicate", "rename_node"):
                return self.rename_node(node_name, fix_text)
            if fix_type == "reset_transform":
                return self.reset_controller_transform(node_name)
        except Exception as error:
            cmds.warning(str(error))

        return False

    def rename_node(self, node_name, new_name):
        """Rename a node after basic validation."""
        if not new_name:
            cmds.warning("Fix name cannot be empty.")
            return False
        if "|" in new_name:
            cmds.warning("A Maya short name cannot contain '|'.")
            return False
        if new_name == node_name.split("|")[-1]:
            return False

        cmds.rename(node_name, new_name)
        return True

    def reset_controller_transform(self, controller):
        """Reset translate/rotate to 0 and scale to 1."""
        expected_values = {
            "translateX": 0,
            "translateY": 0,
            "translateZ": 0,
            "rotateX": 0,
            "rotateY": 0,
            "rotateZ": 0,
            "scaleX": 1,
            "scaleY": 1,
            "scaleZ": 1,
        }

        failed_attributes = []
        for attribute, value in expected_values.items():
            try:
                cmds.setAttr(f"{controller}.{attribute}", value)
            except Exception:
                failed_attributes.append(attribute)

        if failed_attributes:
            cmds.warning(
                "Could not reset: " + ", ".join(failed_attributes)
            )
            return False

        return True


rig_validator_window = None


def find_duplicate_names():
    """Return duplicated DAG short names and their full paths."""
    all_nodes = cmds.ls(dag=True, long=True) or []
    name_map = {}

    for node in all_nodes:
        short_name = node.split("|")[-1]
        if short_name not in name_map:
            name_map[short_name] = []
        name_map[short_name].append(node)

    duplicate_names = {}
    for short_name, paths in name_map.items():
        if len(paths) > 1:
            duplicate_names[short_name] = paths

    return duplicate_names



def find_meshes():
    """Return unique transforms that own non-intermediate mesh shapes."""
    mesh_shapes = cmds.ls(
        type="mesh",
        long=True,
        noIntermediate=True,
    ) or []

    mesh_transforms = []
    seen_transforms = set()

    for mesh_shape in mesh_shapes:
        parents = cmds.listRelatives(
            mesh_shape,
            parent=True,
            fullPath=True,
        ) or []

        if not parents:
            continue

        transform = parents[0]

        if transform in seen_transforms:
            continue

        seen_transforms.add(transform)
        mesh_transforms.append(transform)

    return mesh_transforms


def find_naming_nodes(node_type):
    """Return nodes for the selected naming category."""
    if node_type == "Controller Name":
        return find_controllers()

    if node_type == "Mesh Name":
        return find_meshes()

    if node_type == "Joint Name":
        return cmds.ls(type="joint", long=True) or []

    return []


def is_valid_name(short_name, naming_mode, prefix, suffix):
    """Return whether a short name matches the selected rule."""
    if naming_mode == "Prefix":
        return short_name.startswith(prefix)

    if naming_mode == "Suffix":
        return short_name.endswith(suffix)

    if naming_mode == "Prefix + Suffix":
        return (
            short_name.startswith(prefix)
            and short_name.endswith(suffix)
        )

    return True


def build_suggested_name(
    short_name,
    naming_mode,
    prefix,
    suffix,
):
    """Build an editable default name for the Fix column."""
    suggested_name = short_name

    if naming_mode in ("Prefix", "Prefix + Suffix"):
        if not suggested_name.startswith(prefix):
            suggested_name = prefix + suggested_name

    if naming_mode in ("Suffix", "Prefix + Suffix"):
        if not suggested_name.endswith(suffix):
            suggested_name = suggested_name + suffix

    return suggested_name

def find_root_joints():
    """Return joints whose parent is not another joint."""
    roots = []
    iterator = om.MItDag(
        om.MItDag.kDepthFirst,
        om.MFn.kJoint,
    )

    while not iterator.isDone():
        dag_path = iterator.getPath()
        parent_path = om.MDagPath(dag_path)
        parent_path.pop()

        if not parent_path.hasFn(om.MFn.kJoint):
            roots.append(dag_path.fullPathName())

        iterator.next()

    return roots


def find_controllers():
    """Return unique transforms that own nurbsCurve shapes."""
    curve_shapes = cmds.ls(type="nurbsCurve", long=True) or []
    controllers = []
    seen_controllers = set()

    for curve_shape in curve_shapes:
        parent_transforms = cmds.listRelatives(
            curve_shape,
            parent=True,
            fullPath=True,
        ) or []

        if not parent_transforms:
            continue

        controller = parent_transforms[0]
        if controller in seen_controllers:
            continue

        seen_controllers.add(controller)
        controllers.append(controller)

    return controllers


def show_rig_validator():
    """Close an old window and display a new validator."""
    global rig_validator_window
    maya_main_window = get_maya_main_window()

    if maya_main_window is not None:
        old_window = maya_main_window.findChild(
            QtWidgets.QDialog,
            WINDOW_NAME,
        )
        if old_window is not None:
            old_window.close()
            old_window.deleteLater()

    rig_validator_window = RigValidatorWindow()
    rig_validator_window.show()


show_rig_validator()
