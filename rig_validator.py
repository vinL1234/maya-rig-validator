from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QListWidgetItem
from maya import OpenMayaUI as omui
from shiboken6 import wrapInstance
import maya.cmds as cmds

import maya.api.OpenMaya as om


WINDOW_NAME = "RigValidatorWindow"


def get_maya_main_window():
    """
    Return Maya's main window.
    """
    main_window_ptr = omui.MQtUtil.mainWindow()

    if main_window_ptr is None:
        return None

    return wrapInstance(
        int(main_window_ptr),
        QtWidgets.QWidget
    )


class RigValidatorWindow(QtWidgets.QDialog):

    def __init__(self, parent=get_maya_main_window()):
        super().__init__(parent)

        self.setObjectName(WINDOW_NAME)
        self.setWindowTitle("Rig Validator")
        self.resize(420, 500)

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self):
        """
        Create all UI widgets.
        """
        self.title_label = QtWidgets.QLabel(
            "Rig Validator"
        )
        self.title_label.setAlignment(
            QtCore.Qt.AlignCenter
        )

        self.scan_button = QtWidgets.QPushButton(
            "Scan Duplicate Names"
        )

        self.transform_scan_button = QtWidgets.QPushButton(
            "Scan Controller Transforms"
        )

        self.result_label = QtWidgets.QLabel(
            "Duplicate Objects"
        )

        self.result_list = QtWidgets.QListWidget()

        self.status_label = QtWidgets.QLabel(
            "Status: Ready"
        )

        self.naming_input = QtWidgets.QLineEdit()

        self.naming_input.setPlaceholderText(
            "Enter controller suffix, e.g. _CTRL"
        )

        self.naming_scan_button = QtWidgets.QPushButton(
            "Scan Controller Names"
        )

        

    def create_layouts(self):
        """
        Build the main layout.
        """
        main_layout = QtWidgets.QVBoxLayout(self)

        main_layout.addWidget(self.title_label)
        main_layout.addSpacing(10)

        main_layout.addWidget(self.scan_button)
        main_layout.addSpacing(10)

        main_layout.addWidget(self.transform_scan_button)
        main_layout.addSpacing(10)

        main_layout.addWidget(self.naming_input)
        main_layout.addWidget(self.naming_scan_button)
        main_layout.addSpacing(10)

        main_layout.addWidget(self.result_label)
        main_layout.addWidget(self.result_list)

        main_layout.addSpacing(10)
        main_layout.addWidget(self.status_label)


    def create_connections(self):
        """
        Connect signals and slots.
        """
        self.scan_button.clicked.connect(
            self.scan_duplicate_names
        )

        self.transform_scan_button.clicked.connect(
            self.scan_controller_transforms
        )

        self.result_list.itemDoubleClicked.connect(
            self.select_result
        )

        self.naming_scan_button.clicked.connect(
            self.scan_controller_names
        )


    def scan_controller_names(self):
        self.result_list.clear()

        self.result_label.setText("Invalid controller name")


        naming_rule = self.naming_input.text().strip()

        if not naming_rule:
            self.status_label.setText("Please enter a name suffix")

            return 
        
        controllers = find_controllers()

        invalid_names = []

        for controller in controllers:

            short_name = controller.split("|")[-1]

            if not short_name.endswith(naming_rule):

                invalid_names.append(controller)
                
        invalid_names_count = len(invalid_names)

        if invalid_names_count == 0:
            self.status_label.setText("Status: No invalid controller names")
        else:
            self.status_label.setText("Status: Found " + str(invalid_names_count) + " Invalid Controller names")

        item = QListWidgetItem("Number_of_invalid_suffix_controller_names:  " + str(invalid_names_count))
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.result_list.addItem(item)

        for invalid_name in invalid_names:
            short_name = invalid_name.split("|")[-1]

            self.result_list.addItem("  ")

            name_item = QListWidgetItem(short_name)
            name_item.setData(QtCore.Qt.UserRole, invalid_name)

            font = name_item.font()
            font.setBold(True)
            name_item.setFont(font)

            name_item.setForeground(QtGui.QBrush(QtGui.QColor(220, 70, 70)))
            name_item.setToolTip(invalid_name)
            self.result_list.addItem(name_item)

        print(invalid_names)

    def scan_controller_transforms(self):
        self.result_list.clear()


        self.result_label.setText("Invalid controller transforms")

        controllers = self.find_invalid_controller_transforms()

        invalid_count = len(controllers)

        if not controllers:
            self.status_label.setText("Status: All controller transforms are valid")
        else:
            self.status_label.setText("Status: Found " + str(invalid_count) + " invalid controllers")

        item = QListWidgetItem("Number_of_invalid_controller:  " + str(invalid_count))

        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.result_list.addItem(item)


        for controller,value in controllers.items():
            self.result_list.addItem("  ")

            #get the short ctrl name
            short_ctrl = controller.split("|")[-1]
            ctrl_item = QListWidgetItem(short_ctrl)
            ctrl_item.setData(QtCore.Qt.UserRole, controller)
            
            font = ctrl_item.font()
            font.setBold(True)
            ctrl_item.setFont(font)

            #font color
            ctrl_item.setForeground(QtGui.QBrush(QtGui.QColor(220, 70, 70)))
            ctrl_item.setToolTip(controller)
            self.result_list.addItem(ctrl_item)

            for errors in value: 
                error_item = QListWidgetItem(errors)
                error_item.setData(QtCore.Qt.UserRole, controller)

                error_item.setForeground(QtGui.QBrush(QtGui.QColor(128, 128, 128)))
                error_item.setToolTip(controller)
                self.result_list.addItem(error_item)

    
    def find_invalid_controller_transforms(self):
        controllers = find_controllers()

        invalid_controllers_count = 0

        invalid_controllers = {}
        axis = ["X", "Y", "Z"]
        att_set = ["translate", "rotate", "scale"]

        for controller in controllers:
            for aix in axis:
                for att in att_set:
                    cur_val = cmds.getAttr(controller + "." + att + aix)
                    expected_value = 0 if att != "scale" else 1

                    if cur_val != expected_value:
                        if controller not in invalid_controllers:
                            invalid_controllers[controller] = []
                            invalid_controllers_count += 1

                        invalid_controllers[controller].append("    " + att + aix + " = " + str(cur_val))
                        
        return invalid_controllers
    

    def scan_duplicate_names(self):
        """
        scan the duplicated names in the scene and print out in the list
        """
        self.result_list.clear()

        self.result_label.setText("Duplicate Objects")

        duplicates = find_duplicate_names()

        duplicate_count = 0

        item = QListWidgetItem("Number_of_invalid_names:  " + str(len(duplicates)))

        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.result_list.addItem(item)

        for short_name, paths in duplicates.items():
            for path in paths:
                dis_name = " -> ".join(
                    path.split("|")[1:]
                )

                self.result_list.addItem("  ")
                dup_item = QListWidgetItem(dis_name)
                dup_item.setData(QtCore.Qt.UserRole, path)
                
                font = dup_item.font()
                font.setBold(True)
                dup_item.setFont(font)

                dup_item.setForeground(QtGui.QBrush(QtGui.QColor(220, 70, 70)))

                self.result_list.addItem(dup_item)
                #self.result_list.addItem(path)
                duplicate_count += 1

        if duplicate_count == 0: 
            self.status_label.setText(
                "Status: no duplicate found"
            )
        else:
            self.status_label.setText(
                "Status: Found {} duplicated objects".format(
                    duplicate_count
                )
            )
        

    def select_result(self, item):
        """
        Print the selected result item.
        """
        #node_name = item.text()
        node_name = item.data(QtCore.Qt.UserRole)

        if node_name is None:
            return

        if not cmds.objExists(node_name):
            cmds.warning(
                "Node no longer exists: {}".format(node_name)
            )
            return
        
        cmds.select(node_name, replace=True)
    


rig_validator_window = None


def find_duplicate_names():
    all_nodes = cmds.ls(dag = True, long = True) or []

    name_map = {}

    for node in all_nodes:
        short_node = node.split("|")[-1]
        
        if short_node not in name_map:
            name_map[short_node] = []

        name_map[short_node].append(node)

    duplicates = {}

    for short_names, path in name_map.items():
        if len(path) > 1:
            duplicates[short_names] = path
    
    return duplicates

def find_controllers():
        controllers_shape = cmds.ls(type = "nurbsCurve", long = True) or []

        controller_list = []

        for controller in controllers_shape:
            controllers_trans = cmds.listRelatives(controller, parent = True, fullPath = True) or []

            if controllers_trans:
                if controllers_trans[0] not in controller_list:
                    controller_list.append(controllers_trans[0])

        return controller_list
        
def show_rig_validator():
    global rig_validator_window

    maya_main_window = get_maya_main_window()

    if maya_main_window is not None:
        old_window = maya_main_window.findChild(
            QtWidgets.QDialog,
            WINDOW_NAME
        )

        if old_window is not None:
            old_window.close()
            old_window.deleteLater()

    rig_validator_window = RigValidatorWindow()
    rig_validator_window.show()


show_rig_validator() 
