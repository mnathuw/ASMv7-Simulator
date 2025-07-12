# GUI interface for the application
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QFont
import sys
import os
import struct
import random
import assembly
import data
from dict import line_edit_dict, condition_dict, parse_labels, replace_memory, replace_memory_byte
import memory
from encoder import Encoder
from decoder import Decoder
from dict import SimulatorConfig
from memory import MemoryHierarchy


class RunCode(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal()
    def __init__(self):
        super().__init__()
        self._running = False
    def start_run_code(self):
        self._running = True
        while self._running:
            self.progress.emit()
            # Use proper timer instead of busy-wait loop
            import time
            time.sleep(0.1)  # 100ms delay - much more efficient than 500k iterations
        self.finished.emit()
    def stop_run_code(self):
        self._running = False

class CustomCheckBoxDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.data(QtCore.Qt.ItemDataRole.CheckStateRole) is not None:
            self.drawBackground(painter, option, index)
            self.drawCircle(painter, option, index)
        else:
            super().paint(painter, option, index)
    def drawBackground(self, painter, option, index):
        painter.save()
        painter.fillRect(option.rect, QtGui.QColor('darkGray'))
        painter.restore()
    def drawCircle(self, painter, option, index):
        checked = index.data(QtCore.Qt.ItemDataRole.CheckStateRole) == QtCore.Qt.CheckState.Checked
        rect = option.rect
        size = min(rect.width(), rect.height()) // 2
        circle_rect = QtCore.QRect(
            rect.left() + (rect.width() - size) // 2,
            rect.top() + (rect.height() - size) // 2,
            size,
            size
        )
        painter.save()
        if checked:
            painter.setBrush(QtGui.QColor('red'))
        else:
            painter.setBrush(QtGui.QColor('#DDDDDD'))
        painter.setPen(QtGui.QPen(QtGui.QColor('#DDDDDD'), 1))
        painter.drawEllipse(circle_rect)
        painter.restore()
    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.Type.MouseButtonRelease:
            if index.flags() & QtCore.Qt.ItemFlag.ItemIsEnabled and index.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable:
                current_value = index.data(QtCore.Qt.ItemDataRole.CheckStateRole)
                new_value = QtCore.Qt.CheckState.Checked if current_value == QtCore.Qt.CheckState.Unchecked else QtCore.Qt.CheckState.Unchecked
                model.setData(index, new_value, QtCore.Qt.ItemDataRole.CheckStateRole)
                return True
        return super().editorEvent(event, model, option, index)

class CustomDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None, input_value=0, highlight_column=0):
        super().__init__(parent)
        self.input = input_value
        self.highlight_column = highlight_column

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if self.input == 0 and self.highlight_column == 0 and index.column() == 0:
            option.backgroundBrush = QtGui.QBrush(QtGui.QColor("#DDDDDD"))
        if self.input == 0 and self.highlight_column == 1 and (index.column() == 1 or index.column() == 2):
            option.backgroundBrush = QtGui.QBrush(QtGui.QColor('gray'))

class CustomTableView(QtWidgets.QTableView):
    def __init__(self, parent=None, input_value=0):
        super().__init__(parent)
        self.setShowGrid(False)
        self.input = input_value
        self.delegate = CustomDelegate(self, input_value)
        self.setItemDelegate(self.delegate)

    def setHighlightColumn(self, column):
        self.delegate.highlight_column = column
        self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self.viewport())
        painter.setPen(QtGui.QColor(QtCore.Qt.GlobalColor.darkGray))
        column_count = self.model().columnCount()
        if self.input == 1:
            column = self.delegate.highlight_column
            x = self.columnViewportPosition(column) + self.columnWidth(column)
            painter.drawLine(x, 0, x, self.viewport().height())
        else:
            for column in range(column_count - 1):
                x = self.columnViewportPosition(column) + self.columnWidth(column)
                painter.drawLine(x, 0, x, self.viewport().height())

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1080, 720)

        # Add menu bar
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1080, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)

        # Status bar
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.scrollArea = QtWidgets.QScrollArea(parent=self.centralwidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 1060, 700))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.gridLayout = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(parent=self.scrollAreaWidgetContents)
        font = QtGui.QFont()
        font.setPointSize(24)
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.tabWidget = QtWidgets.QTabWidget(parent=self.scrollAreaWidgetContents)
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.tabWidget.setFont(font)
        self.tabWidget.setObjectName("tabWidget")
        self.tab_editor = QtWidgets.QWidget()
        self.tab_editor.setObjectName("tab_editor")
        self.CompileBtn = QtWidgets.QPushButton(parent=self.tab_editor)
        self.CompileBtn.setGeometry(QtCore.QRect(270, 10, 111, 51))
        self.CompileBtn.setObjectName("CompileBtn")
        self.QuitBtn = QtWidgets.QPushButton(parent=self.tab_editor)
        self.QuitBtn.setGeometry(QtCore.QRect(270, 190, 111, 51))
        self.QuitBtn.setObjectName("QuitBtn")
        self.StepBtn = QtWidgets.QPushButton(parent=self.tab_editor)
        self.StepBtn.setGeometry(QtCore.QRect(270, 130, 111, 51))
        self.StepBtn.setObjectName("StepBtn")
        self.ImportBtn = QtWidgets.QPushButton(parent=self.tab_editor)
        self.ImportBtn.setGeometry(QtCore.QRect(140, 10, 111, 51))
        self.ImportBtn.setObjectName("ImportBtn")
        self.ExportBtn = QtWidgets.QPushButton(parent=self.tab_editor)
        self.ExportBtn.setGeometry(QtCore.QRect(10, 10, 111, 51))
        self.ExportBtn.setObjectName("ExportBtn")
        self.RunBtn = QtWidgets.QPushButton(parent=self.tab_editor)
        self.RunBtn.setGeometry(QtCore.QRect(270, 70, 111, 51))
        self.RunBtn.setObjectName("RunBtn")
        self.stackedCodeWidget = QtWidgets.QStackedWidget(parent=self.tab_editor)
        self.stackedCodeWidget.setGeometry(QtCore.QRect(400, 0, 631, 601))
        self.stackedCodeWidget.setObjectName("stackedCodeWidget")
        self.pageCode_1 = QtWidgets.QWidget()
        self.pageCode_1.setObjectName("pageCode_1")
        self.CodeEditText = QtWidgets.QTextEdit(parent=self.pageCode_1)
        self.CodeEditText.setGeometry(QtCore.QRect(10, 20, 611, 571))
        self.CodeEditText.setObjectName("CodeEditText")
        self.stackedCodeWidget.addWidget(self.pageCode_1)
        self.pageCode_2 = QtWidgets.QWidget()
        self.pageCode_2.setObjectName("pageCode_2")
        self.CodeView = CustomTableView(parent=self.pageCode_2)
        self.CodeView.setGeometry(QtCore.QRect(10, 20, 611, 571))
        self.CodeView.setObjectName("CodeView")
        self.CodeView.verticalHeader().setVisible(False)
        self.CodeView.horizontalHeader().setVisible(False)
        self.stackedCodeWidget.addWidget(self.pageCode_2)

        self.CompileBtn.clicked.connect(self.show_code_view)
        self.RunBtn.clicked.connect(self.RunCode)
        self.QuitBtn.clicked.connect(self.Quit)
        self.StepBtn.clicked.connect(self.check_next_line)
        self.ImportBtn.clicked.connect(self.Import)
        self.ExportBtn.clicked.connect(self.Export)

        self.formLayoutWidget = QtWidgets.QWidget(parent=self.tab_editor)
        self.formLayoutWidget.setGeometry(QtCore.QRect(10, 80, 201, 511))
        self.formLayoutWidget.setObjectName("formLayoutWidget")
        self.Layout_registers = QtWidgets.QFormLayout(self.formLayoutWidget)
        self.Layout_registers.setContentsMargins(0, 0, 0, 0)
        self.Layout_registers.setObjectName("Layout_registers")
        self.r0_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r0_Label.setObjectName("r0_Label")
        self.Layout_registers.setWidget(0, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r0_Label)
        self.r1_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r1_Label.setObjectName("r1_Label")
        self.Layout_registers.setWidget(1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r1_Label)
        self.r1_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r1_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r1_LineEdit.setObjectName("r1_LineEdit")
        self.Layout_registers.setWidget(1, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r1_LineEdit)
        self.r2_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r2_Label.setObjectName("r2_Label")
        self.Layout_registers.setWidget(2, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r2_Label)
        self.r2_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r2_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r2_LineEdit.setObjectName("r2_LineEdit")
        self.Layout_registers.setWidget(2, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r2_LineEdit)
        self.r3_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r3_Label.setObjectName("r3_Label")
        self.Layout_registers.setWidget(3, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r3_Label)
        self.r3_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r3_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r3_LineEdit.setObjectName("r3_LineEdit")
        self.Layout_registers.setWidget(3, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r3_LineEdit)
        self.r4_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r4_Label.setObjectName("r4_Label")
        self.Layout_registers.setWidget(4, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r4_Label)
        self.r4_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r4_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r4_LineEdit.setObjectName("r4_LineEdit")
        self.Layout_registers.setWidget(4, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r4_LineEdit)
        self.r5_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r5_Label.setObjectName("r5_Label")
        self.Layout_registers.setWidget(5, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r5_Label)
        self.r5_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r5_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r5_LineEdit.setObjectName("r5_LineEdit")
        self.Layout_registers.setWidget(5, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r5_LineEdit)
        self.r6_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r6_Label.setObjectName("r6_Label")
        self.Layout_registers.setWidget(6, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r6_Label)
        self.r6_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r6_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r6_LineEdit.setObjectName("r6_LineEdit")
        self.Layout_registers.setWidget(6, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r6_LineEdit)
        self.r7_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r7_Label.setObjectName("r7_Label")
        self.Layout_registers.setWidget(7, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r7_Label)
        self.r7_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r7_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r7_LineEdit.setObjectName("r7_LineEdit")
        self.Layout_registers.setWidget(7, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r7_LineEdit)
        self.r8_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r8_Label.setObjectName("r8_Label")
        self.Layout_registers.setWidget(8, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r8_Label)
        self.r8_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r8_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r8_LineEdit.setObjectName("r8_LineEdit")
        self.Layout_registers.setWidget(8, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r8_LineEdit)
        self.r9_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r9_Label.setObjectName("r9_Label")
        self.Layout_registers.setWidget(9, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r9_Label)
        self.r9_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r9_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r9_LineEdit.setObjectName("r9_LineEdit")
        self.Layout_registers.setWidget(9, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r9_LineEdit)
        self.r10_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r10_Label.setObjectName("r10_Label")
        self.Layout_registers.setWidget(10, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r10_Label)
        self.r10_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r10_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r10_LineEdit.setObjectName("r10_LineEdit")
        self.Layout_registers.setWidget(10, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r10_LineEdit)
        self.r11_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r11_Label.setObjectName("r11_Label")
        self.Layout_registers.setWidget(11, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r11_Label)
        self.r11_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r11_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r11_LineEdit.setObjectName("r11_LineEdit")
        self.Layout_registers.setWidget(11, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r11_LineEdit)
        self.r12_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.r12_Label.setObjectName("r12_Label")
        self.Layout_registers.setWidget(12, QtWidgets.QFormLayout.ItemRole.LabelRole, self.r12_Label)
        self.r12_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r12_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r12_LineEdit.setObjectName("r12_LineEdit")
        self.Layout_registers.setWidget(12, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r12_LineEdit)
        self.sp_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.sp_Label.setObjectName("sp_Label")
        self.Layout_registers.setWidget(13, QtWidgets.QFormLayout.ItemRole.LabelRole, self.sp_Label)
        self.sp_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.sp_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.sp_LineEdit.setObjectName("sp_LineEdit")
        self.Layout_registers.setWidget(13, QtWidgets.QFormLayout.ItemRole.FieldRole, self.sp_LineEdit)
        self.lr_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.lr_Label.setObjectName("lr_Label")
        self.Layout_registers.setWidget(14, QtWidgets.QFormLayout.ItemRole.LabelRole, self.lr_Label)
        self.lr_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.lr_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lr_LineEdit.setObjectName("lr_LineEdit")
        self.Layout_registers.setWidget(14, QtWidgets.QFormLayout.ItemRole.FieldRole, self.lr_LineEdit)
        self.pc_Label = QtWidgets.QLabel(parent=self.formLayoutWidget)
        self.pc_Label.setObjectName("pc_Label")
        self.Layout_registers.setWidget(15, QtWidgets.QFormLayout.ItemRole.LabelRole, self.pc_Label)
        self.pc_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.pc_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.pc_LineEdit.setObjectName("pc_LineEdit")
        self.Layout_registers.setWidget(15, QtWidgets.QFormLayout.ItemRole.FieldRole, self.pc_LineEdit)
        self.r0_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget)
        self.r0_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.r0_LineEdit.setObjectName("r0_LineEdit")
        self.Layout_registers.setWidget(0, QtWidgets.QFormLayout.ItemRole.FieldRole, self.r0_LineEdit)

        line_edit_dict["r0"] = self.r0_LineEdit
        line_edit_dict["r1"] = self.r1_LineEdit
        line_edit_dict["r2"] = self.r2_LineEdit
        line_edit_dict["r3"] = self.r3_LineEdit
        line_edit_dict["r4"] = self.r4_LineEdit
        line_edit_dict["r5"] = self.r5_LineEdit
        line_edit_dict["r6"] = self.r6_LineEdit
        line_edit_dict["r7"] = self.r7_LineEdit
        line_edit_dict["r8"] = self.r8_LineEdit
        line_edit_dict["r9"] = self.r9_LineEdit
        line_edit_dict["r10"] = self.r10_LineEdit
        line_edit_dict["r11"] = self.r11_LineEdit
        line_edit_dict["r12"] = self.r12_LineEdit
        line_edit_dict["lr"] = self.lr_LineEdit
        line_edit_dict["sp"] = self.sp_LineEdit
        line_edit_dict["pc"] = self.pc_LineEdit

        self.formLayoutWidget_2 = QtWidgets.QWidget(parent=self.tab_editor)
        self.formLayoutWidget_2.setGeometry(QtCore.QRect(240, 300, 160, 138))
        self.formLayoutWidget_2.setObjectName("formLayoutWidget_2")
        self.Layout_condition = QtWidgets.QFormLayout(self.formLayoutWidget_2)
        self.Layout_condition.setContentsMargins(10, 10, 10, 10)
        self.Layout_condition.setObjectName("Layout_condition")
        self.n_Label = QtWidgets.QLabel(parent=self.formLayoutWidget_2)
        self.n_Label.setObjectName("n_Label")
        self.Layout_condition.setWidget(0, QtWidgets.QFormLayout.ItemRole.LabelRole, self.n_Label)
        self.n_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget_2)
        self.n_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.n_LineEdit.setObjectName("n_LineEdit")
        self.Layout_condition.setWidget(0, QtWidgets.QFormLayout.ItemRole.FieldRole, self.n_LineEdit)
        self.z_Label = QtWidgets.QLabel(parent=self.formLayoutWidget_2)
        self.z_Label.setObjectName("z_Label")
        self.Layout_condition.setWidget(1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.z_Label)
        self.z_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget_2)
        self.z_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.z_LineEdit.setObjectName("z_LineEdit")
        self.Layout_condition.setWidget(1, QtWidgets.QFormLayout.ItemRole.FieldRole, self.z_LineEdit)
        self.c_Label = QtWidgets.QLabel(parent=self.formLayoutWidget_2)
        self.c_Label.setObjectName("c_Label")
        self.Layout_condition.setWidget(2, QtWidgets.QFormLayout.ItemRole.LabelRole, self.c_Label)
        self.c_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget_2)
        self.c_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.c_LineEdit.setObjectName("c_LineEdit")
        self.Layout_condition.setWidget(2, QtWidgets.QFormLayout.ItemRole.FieldRole, self.c_LineEdit)
        self.v_Label = QtWidgets.QLabel(parent=self.formLayoutWidget_2)
        self.v_Label.setObjectName("v_Label")
        self.Layout_condition.setWidget(3, QtWidgets.QFormLayout.ItemRole.LabelRole, self.v_Label)
        self.v_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget_2)
        self.v_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.v_LineEdit.setObjectName("v_LineEdit")
        self.Layout_condition.setWidget(3, QtWidgets.QFormLayout.ItemRole.FieldRole, self.v_LineEdit)

        condition_dict["n"] = self.n_LineEdit
        condition_dict["z"] = self.z_LineEdit
        condition_dict["c"] = self.c_LineEdit
        condition_dict["v"] = self.v_LineEdit

        self.formLayoutWidget_4 = QtWidgets.QWidget(parent=self.tab_editor)
        self.formLayoutWidget_4.setGeometry(QtCore.QRect(240, 470, 161, 80))
        self.formLayoutWidget_4.setObjectName("formLayoutWidget_4")
        self.formLayout_2 = QtWidgets.QFormLayout(self.formLayoutWidget_4)
        self.formLayout_2.setContentsMargins(0, 0, 0, 0)
        self.formLayout_2.setObjectName("formLayout_2")
        self.cpsr_Label = QtWidgets.QLabel(parent=self.formLayoutWidget_4)
        self.cpsr_Label.setObjectName("cpsr_Label")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.ItemRole.LabelRole, self.cpsr_Label)
        self.cpsr_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget_4)
        self.cpsr_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.cpsr_LineEdit.setObjectName("cpsr_LineEdit")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.ItemRole.FieldRole, self.cpsr_LineEdit)
        self.spsr_Label = QtWidgets.QLabel(parent=self.formLayoutWidget_4)
        self.spsr_Label.setObjectName("spsr_Label")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.spsr_Label)
        self.spsr_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget_4)
        self.spsr_LineEdit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.spsr_LineEdit.setObjectName("spsr_LineEdit")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.ItemRole.FieldRole, self.spsr_LineEdit)

        self.tabWidget.addTab(self.tab_editor, "")
        self.tab_memory = QtWidgets.QWidget()
        self.tab_memory.setObjectName("tab_memory")
        self.groupBox = QtWidgets.QGroupBox(parent=self.tab_memory)
        self.groupBox.setGeometry(QtCore.QRect(940, 0, 91, 591))
        self.groupBox.setObjectName("groupBox")
        self.label_size_memory = QtWidgets.QLabel(parent=self.groupBox)
        self.label_size_memory.setGeometry(QtCore.QRect(0, 30, 81, 41))
        self.label_size_memory.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.label_size_memory.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter|QtCore.Qt.AlignmentFlag.AlignTop)
        self.label_size_memory.setObjectName("label_size_memory")
        self.label_memory_words_per_row = QtWidgets.QLabel(parent=self.groupBox)
        self.label_memory_words_per_row.setGeometry(QtCore.QRect(0, 140, 81, 61))
        self.label_memory_words_per_row.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.label_memory_words_per_row.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter|QtCore.Qt.AlignmentFlag.AlignTop)
        self.label_memory_words_per_row.setObjectName("label_memory_words_per_row")
        self.comboBox_memory_words_per_row = QtWidgets.QComboBox(parent=self.groupBox)
        self.comboBox_memory_words_per_row.setGeometry(QtCore.QRect(10, 210, 71, 22))
        self.comboBox_memory_words_per_row.setObjectName("comboBox_memory_words_per_row")
        self.comboBox_memory_words_per_row.addItem("")
        self.comboBox_memory_words_per_row.addItem("")
        self.comboBox_memory_words_per_row.addItem("")
        self.comboBox_memory_words_per_row.addItem("")
        self.comboBox_memory_words_per_row.setStyleSheet("QComboBox { background-color: white; }")
        self.comboBox_size_memory = QtWidgets.QComboBox(parent=self.groupBox)
        self.comboBox_size_memory.setGeometry(QtCore.QRect(10, 80, 71, 25))
        self.comboBox_size_memory.setObjectName("comboBox_size_memory")
        self.comboBox_size_memory.addItem("")
        self.comboBox_size_memory.addItem("")
        self.comboBox_size_memory.setStyleSheet("QComboBox { background-color: white; }")

        self.formLayoutWidget_5 = QtWidgets.QWidget(parent=self.tab_memory)
        self.formLayoutWidget_5.setGeometry(QtCore.QRect(10, 10, 251, 29))
        self.formLayoutWidget_5.setObjectName("formLayoutWidget_5")
        self.formLayout_4 = QtWidgets.QFormLayout(self.formLayoutWidget_5)
        self.formLayout_4.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignTop)
        self.formLayout_4.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignTop)
        self.formLayout_4.setContentsMargins(0, 0, 0, 0)
        self.formLayout_4.setObjectName("formLayout_4")
        self.Address_search_LineEdit = QtWidgets.QLineEdit(parent=self.formLayoutWidget_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Address_search_LineEdit.sizePolicy().hasHeightForWidth())
        self.Address_search_LineEdit.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        self.Address_search_LineEdit.setFont(font)
        self.Address_search_LineEdit.setObjectName("Address_search_LineEdit")
        self.formLayout_4.setWidget(0, QtWidgets.QFormLayout.ItemRole.FieldRole, self.Address_search_LineEdit)
        self.GotoAddr = QtWidgets.QPushButton(parent=self.formLayoutWidget_5)
        self.GotoAddr.setObjectName("GotoAddr")
        self.formLayout_4.setWidget(0, QtWidgets.QFormLayout.ItemRole.LabelRole, self.GotoAddr)
        self.Addrr_Mem_View = CustomTableView(parent=self.tab_memory, input_value=1)
        self.Addrr_Mem_View.setGeometry(QtCore.QRect(10, 50, 921, 541))
        self.Addrr_Mem_View.setObjectName("Addrr_Mem_View")
        self.Addrr_Mem_View.verticalHeader().setVisible(False)
        self.Addrr_Mem_View.horizontalHeader().setVisible(False)
        self.Addrr_Mem_View.verticalScrollBar().valueChanged.connect(self.on_scroll)
        # self.tabWidget.addTab(self.tab_memory, "")  # Hidden Memory tab

        # Add Cache Tab
        self.tab_cache = QtWidgets.QWidget()
        self.tab_cache.setObjectName("tab_cache")

        # Cache Configuration Group
        self.cache_config_group = QtWidgets.QGroupBox(parent=self.tab_cache)
        self.cache_config_group.setGeometry(QtCore.QRect(10, 10, 340, 200))
        self.cache_config_group.setTitle("Cache Configuration")
        self.cache_config_group.setObjectName("cache_config_group")

        # Cache Size
        self.cache_size_label = QtWidgets.QLabel(parent=self.cache_config_group)
        self.cache_size_label.setGeometry(QtCore.QRect(10, 30, 100, 25))
        self.cache_size_label.setText("Cache Size:")
        self.cache_size_combo = QtWidgets.QComboBox(parent=self.cache_config_group)
        self.cache_size_combo.setGeometry(QtCore.QRect(120, 30, 100, 25))
        self.cache_size_combo.addItems(["1KB", "2KB", "4KB", "8KB", "16KB", "32KB"])
        self.cache_size_combo.setCurrentText("1KB")

        # Block Size
        self.block_size_label = QtWidgets.QLabel(parent=self.cache_config_group)
        self.block_size_label.setGeometry(QtCore.QRect(10, 60, 100, 25))
        self.block_size_label.setText("Block Size:")
        self.block_size_combo = QtWidgets.QComboBox(parent=self.cache_config_group)
        self.block_size_combo.setGeometry(QtCore.QRect(120, 60, 100, 25))
        self.block_size_combo.addItems(["4B", "8B", "16B", "32B"])
        self.block_size_combo.setCurrentText("16B")

        # Associativity
        self.associativity_label = QtWidgets.QLabel(parent=self.cache_config_group)
        self.associativity_label.setGeometry(QtCore.QRect(10, 90, 100, 25))
        self.associativity_label.setText("Associativity:")
        self.associativity_combo = QtWidgets.QComboBox(parent=self.cache_config_group)
        self.associativity_combo.setGeometry(QtCore.QRect(120, 90, 100, 25))
        self.associativity_combo.addItems(["1", "2", "4", "8"])
        self.associativity_combo.setCurrentText("2")

        # Cache Policy
        self.cache_policy_label = QtWidgets.QLabel(parent=self.cache_config_group)
        self.cache_policy_label.setGeometry(QtCore.QRect(10, 120, 100, 25))
        self.cache_policy_label.setText("Replacement:")
        self.cache_policy_combo = QtWidgets.QComboBox(parent=self.cache_config_group)
        self.cache_policy_combo.setGeometry(QtCore.QRect(120, 120, 100, 25))
        self.cache_policy_combo.addItems(["LRU", "FIFO", "Random"])
        self.cache_policy_combo.setCurrentText("LRU")

        # Apply Configuration Button
        self.apply_cache_config_btn = QtWidgets.QPushButton(parent=self.cache_config_group)
        self.apply_cache_config_btn.setGeometry(QtCore.QRect(120, 160, 100, 30))
        self.apply_cache_config_btn.setText("Configure")

        # Import File Button
        self.import_file_btn = QtWidgets.QPushButton(parent=self.cache_config_group)
        self.import_file_btn.setGeometry(QtCore.QRect(10, 160, 100, 30))
        self.import_file_btn.setText("Import")
        self.import_file_btn.setToolTip("Import binary files from Demo folder to test cache performance")

        # Run Benchmark Button
        self.run_benchmark_btn = QtWidgets.QPushButton(parent=self.cache_config_group)
        self.run_benchmark_btn.setGeometry(QtCore.QRect(230, 160, 100, 30))
        self.run_benchmark_btn.setText("Analyze")
        self.run_benchmark_btn.setToolTip("Run automated benchmark testing across all configurations")

        # Cache Statistics Group
        self.cache_stats_group = QtWidgets.QGroupBox(parent=self.tab_cache)
        self.cache_stats_group.setGeometry(QtCore.QRect(360, 10, 250, 200))
        self.cache_stats_group.setTitle("Cache Statistics")
        self.cache_stats_group.setObjectName("cache_stats_group")

        # Statistics Layout
        self.stats_layout = QtWidgets.QFormLayout(self.cache_stats_group)
        self.stats_layout.setContentsMargins(10, 20, 10, 10)

        # Hit Rate
        self.hit_rate_label = QtWidgets.QLabel("Hit Rate:")
        self.hit_rate_value = QtWidgets.QLabel("0.00%")
        self.hit_rate_value.setStyleSheet("font-weight: bold; color: green;")
        self.stats_layout.addRow(self.hit_rate_label, self.hit_rate_value)

        # Miss Rate
        self.miss_rate_label = QtWidgets.QLabel("Miss Rate:")
        self.miss_rate_value = QtWidgets.QLabel("0.00%")
        self.miss_rate_value.setStyleSheet("font-weight: bold; color: red;")
        self.stats_layout.addRow(self.miss_rate_label, self.miss_rate_value)

        # Total Accesses
        self.total_accesses_label = QtWidgets.QLabel("Total Accesses:")
        self.total_accesses_value = QtWidgets.QLabel("0")
        self.stats_layout.addRow(self.total_accesses_label, self.total_accesses_value)

        # Cache Hits
        self.cache_hits_label = QtWidgets.QLabel("Cache Hits:")
        self.cache_hits_value = QtWidgets.QLabel("0")
        self.stats_layout.addRow(self.cache_hits_label, self.cache_hits_value)

        # Cache Misses
        self.cache_misses_label = QtWidgets.QLabel("Cache Misses:")
        self.cache_misses_value = QtWidgets.QLabel("0")
        self.stats_layout.addRow(self.cache_misses_label, self.cache_misses_value)

        # Reset Statistics Button
        self.reset_stats_btn = QtWidgets.QPushButton("Reset")
        self.reset_stats_btn.setGeometry(QtCore.QRect(620, 180, 120, 30))
        self.reset_stats_btn.setParent(self.tab_cache)

        # Cache Contents Table
        self.cache_contents_label = QtWidgets.QLabel(parent=self.tab_cache)
        self.cache_contents_label.setGeometry(QtCore.QRect(10, 220, 200, 25))
        self.cache_contents_label.setText("Cache Contents:")
        self.cache_contents_label.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Weight.Bold))

        self.cache_table = QtWidgets.QTableView(parent=self.tab_cache)
        self.cache_table.setGeometry(QtCore.QRect(10, 250, 1020, 340))
        self.cache_table.setObjectName("cache_table")
        self.cache_table.verticalHeader().setVisible(True)
        self.cache_table.horizontalHeader().setVisible(True)

        # Initialize cache table model
        self.cache_model = QtGui.QStandardItemModel(0, 7)
        self.cache_model.setHorizontalHeaderLabels(["Cache", "Set", "Way", "Valid", "Tag", "Data", "LRU"])
        self.cache_table.setModel(self.cache_model)

        # Set column widths
        self.cache_table.setColumnWidth(0, 60)   # Cache
        self.cache_table.setColumnWidth(1, 60)   # Set
        self.cache_table.setColumnWidth(2, 60)   # Way
        self.cache_table.setColumnWidth(3, 60)   # Valid
        self.cache_table.setColumnWidth(4, 120)  # Tag
        self.cache_table.setColumnWidth(5, 600)  # Data
        self.cache_table.setColumnWidth(6, 60)   # LRU

        # Add the cache tab to the tab widget
        self.tabWidget.addTab(self.tab_cache, "")

        # Connect cache configuration signals
        self.apply_cache_config_btn.clicked.connect(self.apply_cache_configuration)
        self.import_file_btn.clicked.connect(self.import_demo_file)
        self.reset_stats_btn.clicked.connect(self.reset_cache_statistics)
        self.run_benchmark_btn.clicked.connect(self.run_automated_benchmark)

        # Initialize cache simulator
        self.cache_simulator = None
        self.init_cache_simulator()

        self.gridLayout.addWidget(self.tabWidget, 1, 0, 1, 1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.gridLayout_2.addWidget(self.scrollArea, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        self.thread = QtCore.QThread()
        self.worker = RunCode()
        self.worker.moveToThread(self.thread)
        self.worker.progress.connect(self.check)
        self.worker.finished.connect(self.thread.quit)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # Connect tab change signal to update cache when cache tab is selected
        self.tabWidget.currentChanged.connect(self.on_tab_changed)

        self.model_code = QtGui.QStandardItemModel(0, 3)
        self.CodeView.setModel(self.model_code)
        self.CodeView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.model_code = self.add_header_model_code(self.model_code)

        self.model = QtGui.QStandardItemModel(0, 7)
        self.model = self.add_header_model_mem(self.model)

        self.model_2 = QtGui.QStandardItemModel(0, 7)
        self.model_2 = self.add_header_model_mem(self.model_2)

        self.model_4 = QtGui.QStandardItemModel(0, 7)
        self.model_4 = self.add_header_model_mem(self.model_4)

        self.model_8 = QtGui.QStandardItemModel(0, 7)
        self.model_8 = self.add_header_model_mem(self.model_8)

        self.model_byte = QtGui.QStandardItemModel(0, 7)
        self.model_byte = self.add_header_model_mem(self.model_byte)

        self.model_2_byte = QtGui.QStandardItemModel(0, 7)
        self.model_2_byte = self.add_header_model_mem(self.model_2_byte)

        self.model_4_byte = QtGui.QStandardItemModel(0, 7)
        self.model_4_byte = self.add_header_model_mem(self.model_4_byte)

        self.model_8_byte = QtGui.QStandardItemModel(0, 7)
        self.model_8_byte = self.add_header_model_mem(self.model_8_byte)

        self.current_index = 0
        self.current_index_x2 = 0
        self.current_index_x4 = 0
        self.current_index_x8 = 0
        self.current_index_byte = 0
        self.current_index_x2_byte = 0
        self.current_index_x4_byte = 0
        self.current_index_x8_byte = 0
        self.total_items = 1073741823
        self.items_per_batch = 100

        self.load_mem_x1()
        self.load_mem_x2()
        self.load_mem_x4()
        self.load_mem_x8()
        self.load_mem_x1_byte()
        self.load_mem_x2_byte()
        self.load_mem_x4_byte()
        self.load_mem_x8_byte()
        self.check_mem_per_row_option()

        # Initialize simulator state variables
        self.address = []
        self.memory_current_line = []
        self.pc = 0
        self.instruction_size = 4
        self.data_labels = []
        self.current_line_index = 0
        self.stacked = []
        self.have_compile = False

        delegate = CustomCheckBoxDelegate(self.CodeView)
        self.CodeView.setItemDelegateForColumn(0, delegate)

        self.GotoAddr.clicked.connect(self.search_memory)
        self.comboBox_memory_words_per_row.currentIndexChanged.connect(self.check_mem_per_row_option)
        self.comboBox_size_memory.currentIndexChanged.connect(self.check_mem_per_row_option)

    def add_header_model_code(self, model_code):
        label_bkpt = QtGui.QStandardItem()
        label_bkpt.setCheckState(QtCore.Qt.CheckState.Checked)
        label_bkpt.setData(QtCore.Qt.CheckState.Checked, QtCore.Qt.ItemDataRole.CheckStateRole)
        label_bkpt.setCheckable(False)
        label_bkpt.setFlags(label_bkpt.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_address_code = QtGui.QStandardItem('Address')
        label_address_code.setFlags(label_address_code.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_address_code.setBackground(QtGui.QColor('gray'))
        label_address_code.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label_opcode = QtGui.QStandardItem('Opcode')
        label_opcode.setFlags(label_opcode.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_opcode.setBackground(QtGui.QColor('gray'))
        label_opcode.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label_assembly = QtGui.QStandardItem('Assembly')
        label_assembly.setFlags(label_assembly.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_assembly.setBackground(QtGui.QColor('gray'))
        label_assembly.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        model_code.appendRow([label_bkpt, label_address_code, label_opcode, label_assembly])
        self.CodeView.setColumnWidth(0, 25)
        self.CodeView.setColumnWidth(1, 80)
        self.CodeView.setColumnWidth(2, 80)
        self.CodeView.setColumnWidth(3, 380)
        return model_code

    def add_header_model_mem(self, model):
        # self.Addrr_Mem_View.setSpan(0, 1, 1, 8)
        label_address = QtGui.QStandardItem('Address')
        label_address.setFlags(label_address.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_address.setBackground(QtGui.QColor('gray'))
        label_memory = QtGui.QStandardItem('Memory')
        label_memory.setFlags(label_memory.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_memory.setBackground(QtGui.QColor('gray'))
        label_space_1 = QtGui.QStandardItem(" ")
        label_space_1.setFlags(label_space_1.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_space_1.setBackground(QtGui.QColor('gray'))
        label_space_2 = QtGui.QStandardItem(" ")
        label_space_2.setFlags(label_space_2.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_space_2.setBackground(QtGui.QColor('gray'))
        label_space_3 = QtGui.QStandardItem(" ")
        label_space_3.setFlags(label_space_3.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_space_3.setBackground(QtGui.QColor('gray'))
        label_space_4 = QtGui.QStandardItem(" ")
        label_space_4.setFlags(label_space_4.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_space_4.setBackground(QtGui.QColor('gray'))
        label_space_5 = QtGui.QStandardItem(" ")
        label_space_5.setFlags(label_space_5.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_space_5.setBackground(QtGui.QColor('gray'))
        label_space_6 = QtGui.QStandardItem(" ")
        label_space_6.setFlags(label_space_6.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_space_6.setBackground(QtGui.QColor('gray'))
        label_space_7 = QtGui.QStandardItem(" ")
        label_space_7.setFlags(label_space_7.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        label_space_7.setBackground(QtGui.QColor('gray'))
        model.appendRow([label_address, label_memory, label_space_1, label_space_2, label_space_3, label_space_4, label_space_5, label_space_6, label_space_7])
        return model

    def check_mem_per_row_option(self):
        if self.comboBox_size_memory.currentIndex() == 0:
            if self.comboBox_memory_words_per_row.currentIndex() == 0:
                self.Addrr_Mem_View.setModel(self.model)
                self.Addrr_Mem_View.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
            if self.comboBox_memory_words_per_row.currentIndex() == 1:
                self.Addrr_Mem_View.setModel(self.model_2)
                self.Addrr_Mem_View.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
            if self.comboBox_memory_words_per_row.currentIndex() == 2:
                self.Addrr_Mem_View.setModel(self.model_4)
                self.Addrr_Mem_View.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
            if self.comboBox_memory_words_per_row.currentIndex() == 3:
                self.Addrr_Mem_View.setModel(self.model_8)
                self.Addrr_Mem_View.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        if self.comboBox_size_memory.currentIndex() == 1:
            if self.comboBox_memory_words_per_row.currentIndex() == 0:
                self.Addrr_Mem_View.setModel(self.model_byte)
                self.Addrr_Mem_View.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
            if self.comboBox_memory_words_per_row.currentIndex() == 1:
                self.Addrr_Mem_View.setModel(self.model_2_byte)
                self.Addrr_Mem_View.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
            if self.comboBox_memory_words_per_row.currentIndex() == 2:
                self.Addrr_Mem_View.setModel(self.model_4_byte)
                self.Addrr_Mem_View.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
            if self.comboBox_memory_words_per_row.currentIndex() == 3:
                self.Addrr_Mem_View.setModel(self.model_8_byte)
                self.Addrr_Mem_View.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
    def load_mem_x1(self):
        for i in range(self.current_index, min(self.current_index + self.items_per_batch * 8, self.total_items)):
            addr = QtGui.QStandardItem(format(i * 4, '08x'))
            addr.setFlags(addr.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            addr.setBackground(QtGui.QColor('gray'))
            mem_1 = QtGui.QStandardItem('aaaaaaaa')
            mem_1.setFlags(mem_1.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.model.appendRow([addr, mem_1])
        self.current_index += self.items_per_batch * 8
    def load_mem_x1_byte(self):
        for i in range(self.current_index_byte, min(self.current_index_byte + self.items_per_batch * 8, self.total_items)):
            addr = QtGui.QStandardItem(format(i * 4, '08x'))
            addr.setFlags(addr.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            addr.setBackground(QtGui.QColor('gray'))
            mem_1 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_1.setFlags(mem_1.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.model_byte.appendRow([addr, mem_1])
        self.current_index_byte += self.items_per_batch * 8
    def load_mem_x2(self):
        for i in range(self.current_index_x2, min(self.current_index_x2 + self.items_per_batch * 4, self.total_items)):
            addr = QtGui.QStandardItem(format(i * 8, '08x'))
            addr.setFlags(addr.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            addr.setBackground(QtGui.QColor('gray'))
            mem_1 = QtGui.QStandardItem('aaaaaaaa')
            mem_1.setFlags(mem_1.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_2 = QtGui.QStandardItem('aaaaaaaa')
            mem_2.setFlags(mem_2.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.model_2.appendRow([addr, mem_1, mem_2])
        self.current_index_x2 += self.items_per_batch * 4
    def load_mem_x2_byte(self):
        for i in range(self.current_index_x2_byte, min(self.current_index_x2_byte + self.items_per_batch * 4, self.total_items)):
            addr = QtGui.QStandardItem(format(i * 8, '08x'))
            addr.setFlags(addr.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            addr.setBackground(QtGui.QColor('gray'))
            mem_1 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_1.setFlags(mem_1.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_2 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_2.setFlags(mem_2.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.model_2_byte.appendRow([addr, mem_1, mem_2])
        self.current_index_x2_byte += self.items_per_batch * 4
    def load_mem_x4(self):
        for i in range(self.current_index_x4, min(self.current_index_x4 + self.items_per_batch * 2, self.total_items)):
            addr = QtGui.QStandardItem(format(i * 16, '08x'))
            addr.setFlags(addr.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            addr.setBackground(QtGui.QColor('gray'))
            mem_1 = QtGui.QStandardItem('aaaaaaaa')
            mem_1.setFlags(mem_1.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_2 = QtGui.QStandardItem('aaaaaaaa')
            mem_2.setFlags(mem_2.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_3 = QtGui.QStandardItem('aaaaaaaa')
            mem_3.setFlags(mem_3.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_4 = QtGui.QStandardItem('aaaaaaaa')
            mem_4.setFlags(mem_4.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.model_4.appendRow([addr, mem_1, mem_2, mem_3, mem_4])
        self.current_index_x4 += self.items_per_batch * 2
    def load_mem_x4_byte(self):
        for i in range(self.current_index_x4_byte, min(self.current_index_x4_byte + self.items_per_batch * 2, self.total_items)):
            addr = QtGui.QStandardItem(format(i * 16, '08x'))
            addr.setFlags(addr.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            addr.setBackground(QtGui.QColor('gray'))
            mem_1 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_1.setFlags(mem_1.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_2 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_2.setFlags(mem_2.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_3 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_3.setFlags(mem_3.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_4 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_4.setFlags(mem_4.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.model_4_byte.appendRow([addr, mem_1, mem_2, mem_3, mem_4])
        self.current_index_x4_byte += self.items_per_batch * 2
    def load_mem_x8(self):
        for i in range(self.current_index_x8, min(self.current_index_x8 + self.items_per_batch, self.total_items)):
            addr = QtGui.QStandardItem(format(i * 32, '08x'))
            addr.setFlags(addr.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            addr.setBackground(QtGui.QColor('gray'))
            mem_1 = QtGui.QStandardItem('aaaaaaaa')
            mem_1.setFlags(mem_1.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_2 = QtGui.QStandardItem('aaaaaaaa')
            mem_2.setFlags(mem_2.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_3 = QtGui.QStandardItem('aaaaaaaa')
            mem_3.setFlags(mem_3.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_4 = QtGui.QStandardItem('aaaaaaaa')
            mem_4.setFlags(mem_4.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_5 = QtGui.QStandardItem('aaaaaaaa')
            mem_5.setFlags(mem_5.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_6 = QtGui.QStandardItem('aaaaaaaa')
            mem_6.setFlags(mem_6.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_7 = QtGui.QStandardItem('aaaaaaaa')
            mem_7.setFlags(mem_7.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_8 = QtGui.QStandardItem('aaaaaaaa')
            mem_8.setFlags(mem_8.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.model_8.appendRow([addr, mem_1, mem_2, mem_3, mem_4, mem_5, mem_6, mem_7, mem_8])
        self.current_index_x8 += self.items_per_batch
    def load_mem_x8_byte(self):
        for i in range(self.current_index_x8_byte, min(self.current_index_x8_byte + self.items_per_batch, self.total_items)):
            addr = QtGui.QStandardItem(format(i * 32, '08x'))
            addr.setFlags(addr.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            addr.setBackground(QtGui.QColor('gray'))
            mem_1 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_1.setFlags(mem_1.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_2 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_2.setFlags(mem_2.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_3 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_3.setFlags(mem_3.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_4 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_4.setFlags(mem_4.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_5 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_5.setFlags(mem_5.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_6 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_6.setFlags(mem_6.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_7 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_7.setFlags(mem_7.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            mem_8 = QtGui.QStandardItem('aa' + " " + 'aa' + " " + 'aa' + " " + 'aa')
            mem_8.setFlags(mem_8.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.model_8_byte.appendRow([addr, mem_1, mem_2, mem_3, mem_4, mem_5, mem_6, mem_7, mem_8])
        self.current_index_x8_byte += self.items_per_batch
    def on_scroll(self, value):
        max_scroll = self.Addrr_Mem_View.verticalScrollBar().maximum()
        if value >= max_scroll and self.current_index < self.total_items:
            self.load_mem_x1()
            self.load_mem_x2()
            self.load_mem_x4()
            self.load_mem_x8()
            self.load_mem_x1_byte()
            self.load_mem_x2_byte()
            self.load_mem_x4_byte()
            self.load_mem_x8_byte()
    def search_memory(self):
        self.reset_search_memory(self.model)
        self.reset_search_memory(self.model_2)
        self.reset_search_memory(self.model_4)
        self.reset_search_memory(self.model_8)
        self.reset_search_memory(self.model_byte)
        self.reset_search_memory(self.model_2_byte)
        self.reset_search_memory(self.model_4_byte)
        self.reset_search_memory(self.model_8_byte)

        self.highlight_search_memory(self.model)
        self.highlight_search_memory(self.model_2)
        self.highlight_search_memory(self.model_4)
        self.highlight_search_memory(self.model_8)
        self.highlight_search_memory(self.model_byte)
        self.highlight_search_memory(self.model_2_byte)
        self.highlight_search_memory(self.model_4_byte)
        self.highlight_search_memory(self.model_8_byte)
    def reset_search_memory(self, model):
        for row in range(1, model.rowCount()):
            for col in range(1, model.columnCount()):
                if model.item(row, col):
                    model.item(row, col).setBackground(QtGui.QColor("white"))
    def highlight_search_memory(self, model):
        search_text = self.Address_search_LineEdit.text()
        if search_text:
            try:
                # Clean the search text - remove spaces and validate it's hex
                search_text_clean = search_text.strip().replace(" ", "")

                # Check if it's a valid hex string (only hex digits)
                if not all(c in '0123456789abcdefABCDEF' for c in search_text_clean):
                    # If not valid hex, just return without error
                    return

                # Convert to integer
                search_value = int(search_text_clean, 16)
                found = False

                for row in range(1, model.rowCount()):
                    item_addr = model.item(row, 0)
                    if item_addr:
                        addr_text = item_addr.text()
                        try:
                            addr_value = int(addr_text, 16)
                            if search_value == addr_value:
                                # Highlight the memory value column
                                if model.item(row, 1):
                                    model.item(row, 1).setBackground(QtGui.QColor("yellow"))
                                # Scroll to the found item
                                self.Addrr_Mem_View.scrollTo(model.index(row, 1))
                                found = True
                                break
                            elif row < model.rowCount() - 1:
                                # Check if address falls between this row and next
                                next_item_addr = model.item(row + 1, 0)
                                if next_item_addr:
                                    next_addr_text = next_item_addr.text()
                                    try:
                                        next_addr_value = int(next_addr_text, 16)
                                        if addr_value <= search_value < next_addr_value:
                                            # Address falls in this range, highlight this row
                                            if model.item(row, 1):
                                                model.item(row, 1).setBackground(QtGui.QColor("yellow"))
                                            self.Addrr_Mem_View.scrollTo(model.index(row, 1))
                                            found = True
                                            break
                                    except ValueError:
                                        continue
                        except ValueError:
                            continue

            except ValueError:
                # Invalid hex input, just ignore silently
                pass

    def check_code_assembly(self):
        text = self.CodeEditText.toPlainText()
        lines = text.split("\n")
        lines, data_lines = data.parse_data(lines)
        labels, lines_clean = parse_labels(lines)
        lines = [item for item in lines if item not in [" ", None]]
        lines = [' '.join(item.split()) for item in lines if item.strip()]
        lines_clean = [item for item in lines_clean if item not in [" ", None]]
        lines_clean = [' '.join(item.split()) for item in lines_clean if item.strip()]
        for index, line in enumerate(lines_clean, start=1):
            pc_binary = format(self.pc, '08x')
            self.address.append(pc_binary)
            self.pc += self.instruction_size
        self.data_labels, data_address, data_memory = data.process_data(data_lines, self.address)
        if data_address:
            self.address.extend(data_address)
        for index, line in enumerate(lines_clean, start=1):
            memory_line = memory.check_memory(self, line, self.address, lines_clean, self.data_labels)
            if memory_line:
                int_memory_line = Decoder(memory_line)
                memory_line = format(int_memory_line, '08x')
                self.memory_current_line.append(memory_line)
            memory_line_branch = memory.memory_branch(self, line, lines_clean, self.address, labels)
            if memory_line_branch:
                int_memory_line_branch = Decoder(memory_line_branch)
                memory_line_branch = format(int_memory_line_branch, '08x')
                self.memory_current_line.append(memory_line_branch)
            memory_line_stacked = memory.memory_stacked(self, line, lines_clean, self.address, labels)
            if memory_line_stacked:
                int_memory_line_stacked = Decoder(memory_line_stacked)
                memory_line_stacked = format(int_memory_line_stacked, '08x')
                self.memory_current_line.append(memory_line_stacked)
            if not memory_line and not memory_line_branch and not memory_line_stacked:
                # If no memory processing function handled the line, add a placeholder
                print(f"Warning: Line '{line}' could not be processed, adding placeholder memory")
                self.memory_current_line.append("00000000")
        if data_memory:
            self.memory_current_line.extend(data_memory)

        # Ensure address and memory arrays are synchronized
        # If there's a mismatch, add placeholder memory entries for missing entries
        address_count = len(self.address)
        memory_count = len(self.memory_current_line)
        if address_count > memory_count:
            missing_count = address_count - memory_count
            print(f"Warning: Adding {missing_count} placeholder memory entries to match {address_count} addresses")
            for i in range(missing_count):
                self.memory_current_line.append("00000000")
        elif memory_count > address_count:
            # This shouldn't happen, but if it does, truncate memory to match addresses
            print(f"Warning: Truncating {memory_count - address_count} excess memory entries")
            self.memory_current_line = self.memory_current_line[:address_count]

        if len(self.address) != len(self.memory_current_line):
            QtWidgets.QMessageBox.critical(None, "Error", "Error memory")
            self.Quit()
            return True
        replace_memory(self.model, self.address, self.memory_current_line)
        replace_memory(self.model_2, self.address, self.memory_current_line)
        replace_memory(self.model_4, self.address, self.memory_current_line)
        replace_memory(self.model_8, self.address, self.memory_current_line)
        replace_memory_byte(self.model_byte, self.address, self.memory_current_line)
        replace_memory_byte(self.model_2_byte, self.address, self.memory_current_line)
        replace_memory_byte(self.model_4_byte, self.address, self.memory_current_line)
        replace_memory_byte(self.model_8_byte, self.address, self.memory_current_line)
        for i in range(len(lines_clean)):
            line = lines_clean[i]
            if line.strip():
                _, arguments, label, flag_B, _, _, _, _, flag_T = assembly.check_assembly_line(self, lines_clean, line, self.address, self.memory_current_line, self.data_labels
                                                                                                    , self.model, self.model_2, self.model_4, self.model_8
                                                                                                    , self.model_byte, self.model_2_byte, self.model_4_byte, self.model_8_byte
                                                                                                    , self.stacked)
            if flag_B == 3:
                QtWidgets.QMessageBox.critical(None, "Error", "Out of range to POP!")
                return True
            if label != None and (label not in labels) and (label not in lines_clean):
                QtWidgets.QMessageBox.critical(None, "Error", "Label not found: " + label + " in line [" + line + "] in program")
                return True
            if flag_B or (arguments is None and flag_T):
                pass
            elif arguments is None:
                QtWidgets.QMessageBox.critical(None, "Error", "Command in line " + "[" + line + "]"+ " is invalid")
                return True
        self.Quit()
        return False

    def show_code_edit(self):
        self.worker.stop_run_code()
        self.stackedCodeWidget.setCurrentIndex(0)

    have_compile = False
    def show_code_view(self):
        text = self.CodeEditText.toPlainText()
        if not text:
            QtWidgets.QMessageBox.critical(None, "Error", "There is no code to compile")
            return
        if self.have_compile:
            return
        eror = self.check_code_assembly()
        if eror:
            return
        lines = text.split("\n")
        lines, data_lines = data.parse_data(lines)
        labels, lines_clean = parse_labels(lines)
        lines = [item for item in lines if item not in [" ", None]]
        lines = [' '.join(item.split()) for item in lines if item.strip()]
        lines_clean = [item for item in lines_clean if item not in [" ", None]]
        lines_clean = [' '.join(item.split()) for item in lines_clean if item.strip()]
        for index, line in enumerate(lines_clean, start=1):
            pc_binary = format(self.pc, '08x')
            self.address.append(pc_binary)
            self.pc += self.instruction_size
        self.data_labels, data_address, data_memory = data.process_data(data_lines, self.address)
        if data_address:
            self.address.extend(data_address)
        for index, line in enumerate(lines_clean, start=1):
            memory_line = memory.check_memory(self, line, self.address, lines_clean, self.data_labels)
            if memory_line:
                int_memory_line = Decoder(memory_line)
                memory_line = format(int_memory_line, '08x')
                self.memory_current_line.append(memory_line)
            memory_line_branch = memory.memory_branch(self, line, lines_clean, self.address, labels)
            if memory_line_branch:
                int_memory_line_branch = Decoder(memory_line_branch)
                memory_line_branch = format(int_memory_line_branch, '08x')
                self.memory_current_line.append(memory_line_branch)
            memory_line_stacked = memory.memory_stacked(self, line, lines_clean, self.address, labels)
            if memory_line_stacked:
                int_memory_line_stacked = Decoder(memory_line_stacked)
                memory_line_stacked = format(int_memory_line_stacked, '08x')
                self.memory_current_line.append(memory_line_stacked)
            if not memory_line and not memory_line_branch and not memory_line_stacked:
                # If no memory processing function handled the line, add a placeholder
                print(f"Warning: Line '{line}' could not be processed, adding placeholder memory")
                self.memory_current_line.append("00000000")
        if data_memory:
            self.memory_current_line.extend(data_memory)

        # Ensure address and memory arrays are synchronized
        # If there's a mismatch, add placeholder memory entries for missing entries
        address_count = len(self.address)
        memory_count = len(self.memory_current_line)
        if address_count > memory_count:
            missing_count = address_count - memory_count
            print(f"Warning: Adding {missing_count} placeholder memory entries to match {address_count} addresses")
            for i in range(missing_count):
                self.memory_current_line.append("00000000")
        elif memory_count > address_count:
            # This shouldn't happen, but if it does, truncate memory to match addresses
            print(f"Warning: Truncating {memory_count - address_count} excess memory entries")
            self.memory_current_line = self.memory_current_line[:address_count]

        replace_memory(self.model, self.address, self.memory_current_line)
        replace_memory(self.model_2, self.address, self.memory_current_line)
        replace_memory(self.model_4, self.address, self.memory_current_line)
        replace_memory(self.model_8, self.address, self.memory_current_line)
        replace_memory_byte(self.model_byte, self.address, self.memory_current_line)
        replace_memory_byte(self.model_2_byte, self.address, self.memory_current_line)
        replace_memory_byte(self.model_4_byte, self.address, self.memory_current_line)
        replace_memory_byte(self.model_8_byte, self.address, self.memory_current_line)
        mapping_addr_mem = {key: value for key, value in zip(self.address, self.memory_current_line)}
        address_index = 0
        for i in range(len(lines)):
            line = lines[i]
            if not line.endswith(':'):
                addr_text = self.address[address_index]
                address_index += 1
                bkpt = QtGui.QStandardItem()
                bkpt.setCheckable(True)
                bkpt.setCheckState(QtCore.Qt.CheckState.Unchecked)
                bkpt.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                addr = QtGui.QStandardItem(addr_text)
                opcode = QtGui.QStandardItem(mapping_addr_mem.get(addr_text))
                assembly = QtGui.QStandardItem("    " + line)
            if line.endswith(':'):
                bkpt = QtGui.QStandardItem()
                bkpt.setCheckable(False)
                bkpt.setCheckState(QtCore.Qt.CheckState.Unchecked)
                bkpt.setFlags(bkpt.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                addr = QtGui.QStandardItem(" ")
                opcode = QtGui.QStandardItem(" ")
                assembly = QtGui.QStandardItem(line.upper())
            addr.setFlags(addr.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            addr.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            addr.setBackground(QtGui.QColor('gray'))
            opcode.setFlags(opcode.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            opcode.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            opcode.setBackground(QtGui.QColor('gray'))
            assembly.setFlags(assembly.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.model_code.appendRow([bkpt, addr, opcode, assembly])
        self.highlight_line("00000000")
        self.stackedCodeWidget.setCurrentIndex(1)
        self.have_compile = True
        if self.thread.isRunning():
            self.worker.stop_run_code()

    bkpt = []
    def code_breakpoint(self):
        self.bkpt = []
        for row in range(1, self.model_code.rowCount()):
            item_checkbox = self.model_code.item(row, 0)
            item_line = self.model_code.item(row, 3)
            if item_checkbox.isCheckable() and item_checkbox.checkState() == QtCore.Qt.CheckState.Checked:
                line = item_line.text().strip()
                self.bkpt.append(line)

    def reset_backgroud_register(self):
        self.r0_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r1_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r2_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r3_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r4_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r5_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r6_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r7_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r8_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r9_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r10_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r11_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r12_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.sp_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.lr_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.pc_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.n_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.z_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.c_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.v_LineEdit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "ARMv7 Simulator"))
        self.CompileBtn.setText(_translate("MainWindow", "Compile"))
        self.QuitBtn.setText(_translate("MainWindow", "Quit"))
        self.StepBtn.setText(_translate("MainWindow", "Step"))
        self.RunBtn.setText(_translate("MainWindow", "Run"))
        self.r0_Label.setText(_translate("MainWindow", "r0"))
        self.r0_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r0_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r1_Label.setText(_translate("MainWindow", "r1"))
        self.r1_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r1_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r2_Label.setText(_translate("MainWindow", "r2"))
        self.r2_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r2_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r3_Label.setText(_translate("MainWindow", "r3"))
        self.r3_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r3_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r4_Label.setText(_translate("MainWindow", "r4"))
        self.r4_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r4_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r5_Label.setText(_translate("MainWindow", "r5"))
        self.r5_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r5_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r6_Label.setText(_translate("MainWindow", "r6"))
        self.r6_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r6_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r7_Label.setText(_translate("MainWindow", "r7"))
        self.r7_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r7_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r8_Label.setText(_translate("MainWindow", "r8"))
        self.r8_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r8_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r9_Label.setText(_translate("MainWindow", "r9"))
        self.r9_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r9_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r10_Label.setText(_translate("MainWindow", "r10"))
        self.r10_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r10_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r11_Label.setText(_translate("MainWindow", "r11"))
        self.r11_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r11_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.r12_Label.setText(_translate("MainWindow", "r12"))
        self.r12_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.r12_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.sp_Label.setText(_translate("MainWindow", "sp"))
        self.sp_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.sp_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.lr_Label.setText(_translate("MainWindow", "lr"))
        self.lr_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.lr_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.pc_Label.setText(_translate("MainWindow", "pc"))
        self.pc_LineEdit.setText(_translate("MainWindow", format(0, '08x')))
        self.pc_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.n_Label.setText(_translate("MainWindow", "N"))
        self.n_LineEdit.setText(_translate("MainWindow", "0"))
        self.n_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.z_Label.setText(_translate("MainWindow", "Z"))
        self.z_LineEdit.setText(_translate("MainWindow", "0"))
        self.z_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.c_Label.setText(_translate("MainWindow", "C"))
        self.c_LineEdit.setText(_translate("MainWindow", "0"))
        self.c_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.v_Label.setText(_translate("MainWindow", "V"))
        self.v_LineEdit.setText(_translate("MainWindow", "0"))
        self.v_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.cpsr_Label.setText(_translate("MainWindow", "CPSR"))
        self.cpsr_LineEdit.setText(_translate("MainWindow", "00000000"))
        self.cpsr_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.spsr_Label.setText(_translate("MainWindow", "SPSR"))
        self.spsr_LineEdit.setText(_translate("MainWindow", "00000000"))
        self.spsr_LineEdit.setStyleSheet("font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        self.ImportBtn.setText(_translate("MainWindow", "Import"))
        self.ExportBtn.setText(_translate("MainWindow", "Export"))
        self.label.setText(_translate("MainWindow", "Group 32: ARMv7 Simulator 💻"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_editor), _translate("MainWindow", "Editor"))
        # self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_memory), _translate("MainWindow", "Memory"))  # Hidden Memory tab
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_cache), _translate("MainWindow", "Cache"))

    pc = 0
    instruction_size = 4
    memory_current_line = []
    data_labels = []
    address = []
    current_line_index = 0
    row = []
    stacked = []
    def check(self):
        global pc
        text = self.CodeEditText.toPlainText()
        lines = text.split("\n")
        lines, _ = data.parse_data(lines)
        labels, lines = parse_labels(lines)
        lines = [item for item in lines if item not in ["", None]]
        lines = [' '.join(item.split()) for item in lines if item.strip()]
        mapping = {key: value for key, value in zip(self.address, lines)}
        self.code_breakpoint()

        # Initialize variables to avoid UnboundLocalError
        reg, arguments, label, flag_B, flag_N, flag_Z, flag_C, flag_V, flag_T = [], [], "", 0, "0", "0", "0", "0", False

        if self.current_line_index < len(lines):
            if len(self.address) == None or self.current_line_index >= len(self.address):
                return
            line = lines[self.current_line_index]
            if line.strip() in self.bkpt:
                if self.thread.isRunning():
                    self.worker.stop_run_code()
                return
            self.reset_backgroud_register()
            self.reset_highlight()
            pc_binary = self.address[self.current_line_index]
            self.pc_LineEdit.setText(pc_binary)
            if line.strip():
                reg, arguments, label, flag_B, flag_N, flag_Z, flag_C, flag_V, flag_T = assembly.check_assembly_line(self, lines, line, self.address, self.memory_current_line, self.data_labels
                                                                                                  , self.model, self.model_2, self.model_4, self.model_8
                                                                                                  , self.model_byte, self.model_2_byte, self.model_4_byte, self.model_8_byte
                                                                                                  , self.stacked)

            # Simulate cache access for memory operations
            if any(op in line.lower() for op in ['ldr', 'str', 'ldm', 'stm']):
                if self.current_line_index > 0 and self.current_line_index - 1 < len(self.address):
                    pc_addr = self.address[self.current_line_index - 1]
                    access_type = "read" if any(op in line.lower() for op in ['ldr', 'ldm']) else "write"
                    self.simulate_memory_access(pc_addr, access_type)

            # Simulate instruction fetch for all instructions (cache access)
            if self.current_line_index > 0 and self.current_line_index - 1 < len(self.address):
                pc_addr = self.address[self.current_line_index - 1]
                self.simulate_memory_access(pc_addr, "instruction_fetch")

            self.current_line_index += 1
        if flag_B == 2:
            self.stacked = []
        if label in labels:
            position = lines.index(labels[label][0])
            self.current_line_index = position
        elif label in lines:
            position = lines.index(label)
            self.current_line_index = position
        if self.current_line_index >= len(lines) or self.current_line_index >= len(self.address):
            self.worker.stop_run_code()
            self.reset_highlight()
            for row in range(1, self.model_code.rowCount()):
                item = self.model_code.item(row, 3)
                if item != None:
                    item.setBackground(QtGui.QColor('darkGray'))
            # Don't return here - let the register and flag updates happen below
        else:
            pc_binary = self.address[self.current_line_index]
            self.highlight_line(pc_binary)
        if flag_T:
            # Thumb mode - currently not implemented
            return
        elif arguments and len(reg) == len(arguments):
            for i in range(len(arguments)):
                reg_name = reg[i]
                line_edit = line_edit_dict.get(reg_name)
                if line_edit is not None:  # Check if the widget exists
                    result_int = int(arguments[i], 2)
                    result_str = format(result_int, '08x')
                    line_edit.setText(result_str)
                    line_edit.setStyleSheet("background-color: darkGray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        n_edit = condition_dict.get("n")
        z_edit = condition_dict.get("z")
        c_edit = condition_dict.get("c")
        v_edit = condition_dict.get("v")
        n_edit.setText(flag_N)
        z_edit.setText(flag_Z)
        c_edit.setText(flag_C)
        v_edit.setText(flag_V)
        if flag_N == '1':
            n_edit.setStyleSheet("background-color: darkGray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        else:
            n_edit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        if flag_Z == '1':
            z_edit.setStyleSheet("background-color: darkGray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        else:
            z_edit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        if flag_C == '1':
            c_edit.setStyleSheet("background-color: darkGray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        else:
            c_edit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        if flag_V == '1':
            v_edit.setStyleSheet("background-color: darkGray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
        else:
            v_edit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
    def reset_highlight(self):
        for row in range(1, self.model_code.rowCount()):
            item = self.model_code.item(row, 3)
            if item != None:
                item.setBackground(QtGui.QColor("gray"))
    def highlight_line(self, pc_binary):
        self.reset_highlight()
        search_value  = int(pc_binary, 16)
        for row in range(1, self.model_code.rowCount()):
            addr_line = self.model_code.item(row, 1)
            addr_line_text = addr_line.text()
            try:
                if search_value == int(addr_line_text, 16):
                    item = self.model_code.item(row, 3)
                    item.setBackground(QtGui.QColor("darkGray"))
            except ValueError:
                pass

    def check_next_line(self):
        if self.thread.isRunning():
            self.worker.stop_run_code()
        if self.stackedCodeWidget.currentIndex() == 0:
            QtWidgets.QMessageBox.critical(None, "Error", "Please compile code")
            self.Quit()
            return
        global current_line_index
        text = self.CodeEditText.toPlainText()
        lines = text.split("\n")
        lines, _ = data.parse_data(lines)
        labels, lines = parse_labels(lines)
        lines = [item for item in lines if item not in ["", None]]
        mapping = {key: value for key, value in zip(self.address, lines)}

        # Initialize variables to avoid UnboundLocalError
        reg, arguments, label, flag_B, flag_N, flag_Z, flag_C, flag_V, flag_T = [], [], "", 0, "0", "0", "0", "0", False

        if self.current_line_index < len(lines):
            self.reset_backgroud_register()
            self.reset_highlight()
            pc_binary = self.address[self.current_line_index]
            self.pc_LineEdit.setText(pc_binary)
            current_line = lines[self.current_line_index]
            if current_line.strip():
                reg, arguments, label, flag_B, flag_N, flag_Z, flag_C, flag_V, flag_T = assembly.check_assembly_line(self, lines, current_line, self.address, self.memory_current_line, self.data_labels
                                                                                                      , self.model, self.model_2, self.model_4, self.model_8
                                                                                                      , self.model_byte, self.model_2_byte, self.model_4_byte, self.model_8_byte
                                                                                                      , self.stacked)

                # Simulate cache access for instruction fetch
                pc_addr = self.address[self.current_line_index]
                self.simulate_memory_access(pc_addr, "instruction_fetch")

                # Simulate cache access for memory operations
                if any(op in current_line.lower() for op in ['ldr', 'str', 'ldm', 'stm']):
                    access_type = "read" if any(op in current_line.lower() for op in ['ldr', 'ldm']) else "write"
                    self.simulate_memory_access(pc_addr, access_type)

                self.current_line_index += 1
            if flag_B == 2:
                self.stacked = []
            if label in labels:
                position = lines.index(labels[label][0])
                self.current_line_index = position
            elif label in lines:
                position = lines.index(label)
                self.current_line_index = position
            if self.current_line_index >= len(lines):
                self.reset_highlight()
                for row in range(1, self.model_code.rowCount()):
                    item = self.model_code.item(row, 3)
                    if item != None:
                        item.setBackground(QtGui.QColor('darkGray'))
            else:
                pc_binary = self.address[self.current_line_index]
                self.highlight_line(pc_binary)
            if flag_T:
                pass
            elif arguments and len(reg) == len(arguments):
                for i in range(len(arguments)):
                    reg_name = reg[i]
                    line_edit = line_edit_dict.get(reg_name)
                    if line_edit is not None:  # Check if the widget exists
                        result_int = int(arguments[i], 2)
                        result_str = format(result_int, '08x')
                        line_edit.setText(result_str)
                        line_edit.setStyleSheet("background-color: darkGray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
            n_edit = condition_dict.get("n")
            z_edit = condition_dict.get("z")
            c_edit = condition_dict.get("c")
            v_edit = condition_dict.get("v")
            n_edit.setText(flag_N)
            z_edit.setText(flag_Z)
            c_edit.setText(flag_C)
            v_edit.setText(flag_V)
            if flag_N == '1':
                n_edit.setStyleSheet("background-color: darkGray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
            else:
                n_edit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
            if flag_Z == '1':
                z_edit.setStyleSheet("background-color: darkGray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
            else:
                z_edit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
            if flag_C == '1':
                c_edit.setStyleSheet("background-color: darkGray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
            else:
                c_edit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
            if flag_V == '1':
                v_edit.setStyleSheet("background-color: darkGray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")
            else:
                v_edit.setStyleSheet("background-color: gray; font-family: 'Open Sans', Verdana, Arial, sans-serif; font-size: 16px;")

    def RunCode(self):
        thread_connected = False
        if self.stackedCodeWidget.currentIndex() == 0:
            QtWidgets.QMessageBox.critical(None, "Error", "Please compile code")
            self.Quit()
            return
        if not self.thread.isRunning():
            if not thread_connected:
                self.thread.started.connect(self.worker.start_run_code)
                thread_connected = True
            self.thread.start()

    def Quit(self):
        # Quit button: Stop execution and reset all state (registers, flags, memory, etc.)
        # Note: The Run button preserves final results when execution completes
        self.worker.stop_run_code()
        self.show_code_edit()
        self.address = []
        self.memory_current_line = []
        self.instruction_size = 4
        self.reset_backgroud_register()
        self.reset_highlight()
        self.stacked = []
        self.r0_LineEdit.setText(format(0, '08x'))
        self.r1_LineEdit.setText(format(0, '08x'))
        self.r2_LineEdit.setText(format(0, '08x'))
        self.r3_LineEdit.setText(format(0, '08x'))
        self.r4_LineEdit.setText(format(0, '08x'))
        self.r5_LineEdit.setText(format(0, '08x'))
        self.r6_LineEdit.setText(format(0, '08x'))
        self.r7_LineEdit.setText(format(0, '08x'))
        self.r8_LineEdit.setText(format(0, '08x'))
        self.r9_LineEdit.setText(format(0, '08x'))
        self.r10_LineEdit.setText(format(0, '08x'))
        self.r11_LineEdit.setText(format(0, '08x'))
        self.r12_LineEdit.setText(format(0, '08x'))
        self.sp_LineEdit.setText(format(0, '08x'))
        self.lr_LineEdit.setText(format(0, '08x'))
        self.pc_LineEdit.setText(format(0, '08x'))
        self.pc = 0
        self.instruction_size = 4
        self.current_line_index = 0
        self.n_LineEdit.setText("0")
        self.z_LineEdit.setText("0")
        self.c_LineEdit.setText("0")
        self.v_LineEdit.setText("0")
        self.current_index = 0
        self.current_index_x2 = 0
        self.current_index_x4 = 0
        self.current_index_x8 = 0
        self.current_index_byte = 0
        self.current_index_x2_byte = 0
        self.current_index_x4_byte = 0
        self.current_index_x8_byte = 0
        self.model.clear()
        self.model = self.add_header_model_mem(self.model)
        self.model_2.clear()
        self.model_2 = self.add_header_model_mem(self.model_2)
        self.model_4.clear()
        self.model_4 = self.add_header_model_mem(self.model_4)
        self.model_8.clear()
        self.model_8 = self.add_header_model_mem(self.model_8)
        self.model_byte.clear()
        self.model_byte = self.add_header_model_mem(self.model_byte)
        self.model_2_byte.clear()
        self.model_2_byte = self.add_header_model_mem(self.model_2_byte)
        self.model_4_byte.clear()
        self.model_4_byte = self.add_header_model_mem(self.model_4_byte)
        self.model_8_byte.clear()
        self.model_8_byte = self.add_header_model_mem(self.model_8_byte)
        self.load_mem_x1()
        self.load_mem_x2()
        self.load_mem_x4()
        self.load_mem_x8()
        self.load_mem_x1_byte()
        self.load_mem_x2_byte()
        self.load_mem_x4_byte()
        self.load_mem_x8_byte()
        self.Address_search_LineEdit.setText(format(0, '08x'))
        self.row = []
        self.bkpt = []
        self.have_compile = False
        self.model_code.clear()
        self.model_code = self.add_header_model_code(self.model_code)

    def Export(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save File", "", "Text Files (*.txt);;Assembly Files (*.s)")
        if file_path:
            try:
                file_content = self.CodeEditText.toPlainText()
                with open(file_path, 'w') as file:
                    file.write(file_content)
                file_name = file_path.split('/')[-1]
                QtWidgets.QMessageBox.information(None, "Success", f"File {file_name} saved successfully")
            except Exception as e:
                QtWidgets.QMessageBox.critical(None, "Error", f"File {file_path}\n{e} save failed, please try again")
                self.Quit()

    def Import(self):
        if self.stackedCodeWidget.currentIndex() == 1:
            QtWidgets.QMessageBox.critical(None, "Error", "Please click Quit button to return to the editor tab")
            self.Quit()
            return
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Import File", "", "Assembly Files (*.s);;Text Files (*.txt);;Binary Files (*.bin)")
        if file_path:
            try:
                file_name = file_path.split('/')[-1]
                if file_name.split('\\')[-1]:  # Handle Windows paths
                    file_name = file_name.split('\\')[-1]

                if file_path.lower().endswith('.bin'):
                    # Handle binary file import
                    self._import_binary_file(file_path, file_name)
                else:
                    # Handle text/assembly file import
                    with open(file_path, 'r') as file:
                        file_content = file.read()
                    self.CodeEditText.setPlainText(file_content)
                    QtWidgets.QMessageBox.information(None, "Success", f"File {file_name} imported successfully")

            except Exception as e:
                QtWidgets.QMessageBox.critical(None, "Error", f"Open file {file_name}\n{e} failed, please try again")
                self.Quit()

    def _import_binary_file(self, file_path, file_name):
        """Import and process a binary (.bin) file"""
        try:
            with open(file_path, 'rb') as file:
                binary_data = file.read()

            # Convert binary to assembly representation for display
            assembly_text = self._binary_to_assembly_display(binary_data, file_name)
            self.CodeEditText.setPlainText(assembly_text)

            # Auto-compile the binary file
            self._compile_binary_file(binary_data, file_name)

            QtWidgets.QMessageBox.information(None, "Success",
                f"Binary file {file_name} imported and compiled successfully!\n"
                f"Size: {len(binary_data)} bytes\n"
                f"Instructions: {len(binary_data) // 4}\n"
                "Ready to run.")

        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "Error", f"Failed to import binary file {file_name}:\n{e}")

    def _binary_to_assembly_display(self, binary_data, file_name):
        """Convert binary data to assembly display format"""
        assembly_lines = [
            f"; Binary file: {file_name}",
            f"; Size: {len(binary_data)} bytes",
            f"; Instructions: {len(binary_data) // 4}",
            "",
            ".text",
            ""
        ]

        # Convert each 4-byte chunk to assembly representation
        for i in range(0, len(binary_data), 4):
            if i + 4 <= len(binary_data):
                # Read as little-endian 32-bit word
                instruction = struct.unpack('<I', binary_data[i:i+4])[0]
                address = i

                # Simple instruction decoding for display
                if instruction == 0:
                    asm_line = "NOP"
                else:
                    # Basic ARM instruction pattern recognition
                    condition = (instruction >> 28) & 0xF
                    inst_type = (instruction >> 25) & 0x7

                    if condition == 0xE:  # Always condition
                        if inst_type == 0x5:  # Branch
                            asm_line = f"B 0x{instruction & 0xFFFFFF:06X}"
                        elif inst_type == 0x2:  # Load/Store
                            asm_line = f"LDR/STR 0x{instruction:08X}"
                        elif inst_type == 0x0:  # Data processing
                            asm_line = f"DATA_OP 0x{instruction:08X}"
                        else:
                            asm_line = f"UNKNOWN 0x{instruction:08X}"
                    else:
                        condition_names = ["EQ", "NE", "CS", "CC", "MI", "PL", "VS", "VC",
                                         "HI", "LS", "GE", "LT", "GT", "LE", "AL", "NV"]
                        cond_name = condition_names[condition] if condition < 16 else "??"
                        asm_line = f"INST{cond_name} 0x{instruction:08X}"

                assembly_lines.append(f"    ; @0x{address:04X}: 0x{instruction:08X}")
                assembly_lines.append(f"    {asm_line}")
            else:
                # Handle incomplete instruction
                remaining = binary_data[i:]
                hex_str = ' '.join(f'{b:02X}' for b in remaining)
                assembly_lines.append(f"    ; Partial: {hex_str}")

        return '\n'.join(assembly_lines)

    def _compile_binary_file(self, binary_data, file_name):
        """Compile binary file directly into simulator memory"""
        # Reset simulator state
        self.address = []
        self.memory_current_line = []
        self.pc = 0
        self.instruction_size = 4

        # Convert binary to memory format
        for i in range(0, len(binary_data), 4):
            if i + 4 <= len(binary_data):
                # Address for this instruction
                pc_binary = format(self.pc, '08x')
                self.address.append(pc_binary)

                # Memory content (instruction)
                instruction = struct.unpack('<I', binary_data[i:i+4])[0]
                memory_line = format(instruction, '08x')
                self.memory_current_line.append(memory_line)

                self.pc += self.instruction_size

        # Update memory models
        self._update_memory_models()

        # Update code view
        self._update_code_view_from_binary(file_name)

        # Switch to compiled view
        self.stackedCodeWidget.setCurrentIndex(1)
        self.have_compile = True

    def _update_memory_models(self):
        """Update all memory models with current data"""
        try:
            replace_memory(self.model, self.address, self.memory_current_line)
            replace_memory(self.model_2, self.address, self.memory_current_line)
            replace_memory(self.model_4, self.address, self.memory_current_line)
            replace_memory(self.model_8, self.address, self.memory_current_line)
            replace_memory_byte(self.model_byte, self.address, self.memory_current_line)
            replace_memory_byte(self.model_2_byte, self.address, self.memory_current_line)
            replace_memory_byte(self.model_4_byte, self.address, self.memory_current_line)
            replace_memory_byte(self.model_8_byte, self.address, self.memory_current_line)
        except ImportError:
            # Fallback if memory module not available
            pass

    def _update_code_view_from_binary(self, file_name):
        """Update code view with binary file information"""
        # Clear existing code model
        self.model_code.clear()
        self.model_code = self.add_header_model_code(self.model_code)

        # Add binary file info as comments
        mapping_addr_mem = {key: value for key, value in zip(self.address, self.memory_current_line)}

        for i, (addr, mem) in enumerate(zip(self.address, self.memory_current_line)):
            bkpt = QtGui.QStandardItem()
            bkpt.setCheckable(True)
            bkpt.setCheckState(QtCore.Qt.CheckState.Unchecked)
            bkpt.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsUserCheckable)

            addr_item = QtGui.QStandardItem(addr)
            addr_item.setFlags(addr_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            addr_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            addr_item.setBackground(QtGui.QColor('gray'))

            opcode_item = QtGui.QStandardItem(mem)
            opcode_item.setFlags(opcode_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            opcode_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            opcode_item.setBackground(QtGui.QColor('gray'))

            assembly_item = QtGui.QStandardItem(f"    ; Binary instruction {i} from {file_name}")
            assembly_item.setFlags(assembly_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)

            self.model_code.appendRow([bkpt, addr_item, opcode_item, assembly_item])

        # Highlight first line
        if self.address:
            self.highlight_line("00000000")

    def close_event(self, event):
        super().close_event(event)
        self.worker.stop_run_code()

    def init_cache_simulator(self):
        """Initialize the cache simulator with default configuration"""
        try:
            # Import cache simulator modules from cache-simulator folder
            cache_path = os.path.join(os.path.dirname(__file__), 'cache-simulator')
            if cache_path not in sys.path:
                sys.path.append(cache_path)

            # Import from your existing cache simulator

            # Create a default configuration
            config = SimulatorConfig()

            # Initialize memory hierarchy with individual parameters
            self.memory_hierarchy = MemoryHierarchy(
                l1_block_size=32,  # Default block size
                l2_block_size=32,
                l1_cache_type='set_associative',
                l1_associativity=2,  # Default 2-way associative
                l1_size=4096  # Default 4KB
            )

            # Create wrapper for compatibility
            self.cache_simulator = CacheWrapper(self.memory_hierarchy)

            # Initialize data loaded flag
            self.cache_data_loaded = False

            self.update_cache_display()

        except ImportError as e:
            print(f"Cache simulator import error: {e}")
            # Try to run the existing cache simulator directly
            try:
                from main import CacheSimulator
                self.cache_simulator = CacheSimulator()
                self.memory_hierarchy = None
            except:
                self.cache_simulator = None
                self.memory_hierarchy = None

        except Exception as e:
            print(f"Cache simulator initialization error: {e}")
            self.cache_simulator = None
            self.memory_hierarchy = None

    def apply_cache_configuration(self):
        """Apply the selected cache configuration"""
        if not hasattr(self, 'memory_hierarchy') or not self.memory_hierarchy:
            return

        try:
            # Save current statistics and main memory data before reconfiguration
            current_stats = None
            main_memory_data = None
            data_was_loaded = getattr(self, 'cache_data_loaded', False)

            if hasattr(self, 'memory_hierarchy') and self.memory_hierarchy:
                current_stats = self.memory_hierarchy.get_statistics()
                # Preserve main memory data if it exists and data was previously loaded
                if data_was_loaded and hasattr(self.memory_hierarchy, 'main_memory') and self.memory_hierarchy.main_memory:
                    main_memory_data = self.memory_hierarchy.main_memory

            # Parse configuration values
            cache_size_str = self.cache_size_combo.currentText()
            block_size_str = self.block_size_combo.currentText()
            associativity_str = self.associativity_combo.currentText()
            replacement_policy = self.cache_policy_combo.currentText()

            # Extract numeric values
            cache_size = int(cache_size_str[:-2]) * 1024  # Convert KB to bytes
            l1_block_size = int(block_size_str[:-1])  # Remove 'B' suffix
            l2_block_size = 32  # Keep L2 block size constant
            associativity = int(associativity_str)

            # Determine cache type based on associativity
            if associativity == 1:
                l1_cache_type = 'direct'
            elif associativity >= cache_size // l1_block_size:
                l1_cache_type = 'fully_associative'
            else:
                l1_cache_type = 'set_associative'

            # Reinitialize memory hierarchy with new configuration
            self.memory_hierarchy = MemoryHierarchy(
                l1_block_size=l1_block_size,
                l2_block_size=l2_block_size,
                l1_cache_type=l1_cache_type,
                l1_associativity=associativity,
                l1_size=cache_size
            )

            # Restore main memory data if it existed and re-populate cache
            if main_memory_data and data_was_loaded:
                self.memory_hierarchy.main_memory = main_memory_data

                # Re-simulate memory accesses to populate the new cache configuration
                # This will load data into the cache with the new configuration
                self._resimulate_cache_accesses()

                print(f"Cache reconfigured - data reloaded into new cache structure")
            else:
                print(f"Cache reconfigured - no previous data to reload")

            # Update wrapper
            self.cache_simulator = CacheWrapper(self.memory_hierarchy)

            # Update cache display (this will show the new configuration with data if available)
            self.update_cache_display()

            # Update statistics display
            self._update_cache_statistics()

            # Configuration applied silently - no popup window
            print("Cache configuration applied successfully!")
            print(f"Configuration Details:")
            print(f"  - Cache Size: {cache_size_str} ({cache_size} bytes)")
            print(f"  - Block Size: {block_size_str} ({l1_block_size} bytes)")
            print(f"  - Associativity: {associativity_str}-way ({associativity} ways per set)")
            print(f"  - Cache Type: {l1_cache_type}")
            print(f"  - Replacement Policy: {replacement_policy}")
            print(f"  - Number of Sets: {cache_size // (l1_block_size * associativity)}")

            # Show information about data reload if main memory had data
            if main_memory_data and data_was_loaded:
                stats = self.memory_hierarchy.get_statistics()
                l1d_stats = stats['l1_dcache']
                l1i_stats = stats['l1_icache']
                total_accesses = l1d_stats['accesses'] + l1i_stats['accesses']
                print(f"  - Main memory data preserved and reloaded into new cache configuration")
                print(f"  - Cache populated with {total_accesses} memory accesses")

            print(f"Cache display updated - showing {self.cache_model.rowCount()} rows")

        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "Error",
                                         f"Failed to apply cache configuration: {e}")

    def _resimulate_cache_accesses(self):
        """Re-simulate memory accesses to populate cache with new configuration"""
        try:
            access_count = 0
            successful_accesses = 0

            # Simulate instruction fetches for loaded program
            # Start from base address 0x1000 (common program start)
            base_address = 0x1000

            # Simulate instruction fetches for up to 256 instructions (1KB of program)
            for i in range(0, 1024, 4):  # 4 bytes per instruction
                addr = base_address + i
                try:
                    success = self.simulate_memory_access(addr, "instruction_fetch")
                    access_count += 1
                    if success:
                        successful_accesses += 1
                except Exception as e:
                    # Continue with other accesses even if some fail
                    pass

            # Simulate data accesses for test patterns
            data_addresses = [0x2000, 0x8000, 0x10000]  # Common data regions
            for base_addr in data_addresses:
                for i in range(0, 256, 4):  # 64 data accesses per region
                    addr = base_addr + i
                    try:
                        access_type = "read" if i % 8 < 6 else "write"
                        success = self.simulate_memory_access(addr, access_type)
                        access_count += 1
                        if success:
                            successful_accesses += 1
                    except Exception as e:
                        # Continue with other accesses even if some fail
                        pass

            # Force update statistics after all accesses
            self._update_cache_statistics()

            print(f"Re-simulated cache accesses for new configuration")
            print(f"Attempted {access_count} memory accesses, {successful_accesses} successful")

            # Get final statistics to verify
            if hasattr(self, 'memory_hierarchy') and self.memory_hierarchy:
                stats = self.memory_hierarchy.get_statistics()
                l1d_accesses = stats['l1_dcache']['accesses']
                l1i_accesses = stats['l1_icache']['accesses']
                total_cache_accesses = l1d_accesses + l1i_accesses
                print(f"Final cache statistics: {total_cache_accesses} total accesses (L1D: {l1d_accesses}, L1I: {l1i_accesses})")

        except Exception as e:
            print(f"Error re-simulating cache accesses: {e}")

    def reset_cache_statistics(self):
        """Reset cache statistics"""
        if hasattr(self, 'memory_hierarchy') and self.memory_hierarchy:
            self.memory_hierarchy.reset_statistics()

        self.hit_rate_value.setText("0.00%")
        self.miss_rate_value.setText("0.00%")
        self.total_accesses_value.setText("0")
        self.cache_hits_value.setText("0")
        self.cache_misses_value.setText("0")

        # Reset data loaded flag
        self.cache_data_loaded = False

        self.update_cache_display()

    def import_demo_file(self):
        """Import a binary file from Demo folder to test cache performance"""
        try:
            # Get list of binary files from Demo folder
            demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Demo")
            if not os.path.exists(demo_path):
                QtWidgets.QMessageBox.warning(None, "Warning", "Demo folder not found")
                return

            # Find all binary files
            binary_files = [f for f in os.listdir(demo_path) if f.endswith('.bin')]

            if not binary_files:
                QtWidgets.QMessageBox.warning(None, "Warning", "No binary files found in Demo folder")
                return

            # Let user select a file
            file_name, ok = QtWidgets.QInputDialog.getItem(
                None, "Import Demo File",
                "Select a binary file to import:",
                binary_files, 0, False
            )

            if not ok or not file_name:
                return

            file_path = os.path.join(demo_path, file_name)

            # Check if cache is configured
            if not hasattr(self, 'memory_hierarchy') or not self.memory_hierarchy:
                QtWidgets.QMessageBox.warning(None, "Warning",
                                            "Cache not configured. Please apply cache configuration first.")
                return

            # Read and process the binary file
            with open(file_path, 'rb') as f:
                data = f.read()

            # Reset cache statistics for clean test
            self.reset_cache_statistics()

            # Load the binary data into main memory first!
            base_address = 0x1000  # Start loading from this address
            self.memory_hierarchy.main_memory.load_program(data, base_address)

            # Also load some test data at other addresses for more interesting cache behavior
            test_pattern = bytearray([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x11, 0x22,
                                     0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0x00])
            self.memory_hierarchy.main_memory.load_program(test_pattern * 4, 0x2000)  # 64 bytes
            self.memory_hierarchy.main_memory.load_program(test_pattern * 2, 0x8000)  # 32 bytes

            # Load the binary data and simulate instruction fetches
            base_address = 0x1000  # Start loading from this address

            # Process data in 4-byte chunks (instructions)
            for i in range(0, len(data), 4):
                chunk = data[i:i+4]
                address = base_address + i

                # Simulate instruction fetch (this will test the I-cache)
                self.simulate_memory_access(address, "instruction_fetch")

                # Create more diverse access patterns to use different cache sets/ways
                if i % 4 == 0:  # Every instruction, simulate data access
                    # Create addresses that map to different sets
                    # With 64 sets and 32-byte blocks, addresses 2048 apart map to different sets
                    data_addr = 0x2000 + (i // 4) * 2048  # This ensures different sets
                    self.simulate_memory_access(data_addr, "read")

                # Add some stack-like accesses (different address space)
                if i % 8 == 0:
                    stack_addr = 0x8000 + (i // 8) * 64  # Different region, different sets
                    self.simulate_memory_access(stack_addr, "read")

                # Add some high-memory accesses to create conflicts
                if i % 12 == 0:
                    high_addr = 0x10000 + (i // 12) * 32  # Same set as some base addresses
                    self.simulate_memory_access(high_addr, "read")

            # Update displays
            self.update_cache_display()
            self._update_cache_statistics()

            # Set flag to indicate data has been loaded
            self.cache_data_loaded = True

            # Show completion message
            stats = self.memory_hierarchy.get_statistics()
            l1d_stats = stats['l1_dcache']
            l1i_stats = stats['l1_icache']

            total_accesses = l1d_stats['accesses'] + l1i_stats['accesses']
            total_hits = l1d_stats['hits'] + l1i_stats['hits']
            hit_rate = (total_hits / total_accesses * 100) if total_accesses > 0 else 0

            QtWidgets.QMessageBox.information(None, "Import Complete",
                                            f"Successfully imported {file_name}\n"
                                            f"Processed {len(data)} bytes\n"
                                            f"Total cache accesses: {total_accesses}\n"
                                            f"Hit rate: {hit_rate:.2f}%")

        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "Error", f"Failed to import file: {e}")

    def on_tab_changed(self, index):
        """Handle tab changes"""
        if self.tabWidget.tabText(index) == "Cache":
            # Update cache display when cache tab is selected
            self._update_cache_statistics()
            # Only update display if we have cache data
            if hasattr(self, 'memory_hierarchy') and self.memory_hierarchy:
                stats = self.memory_hierarchy.get_statistics()
                if (stats['l1_dcache']['accesses'] > 0 or
                    stats['l1_icache']['accesses'] > 0):
                    self.update_cache_display()
                else:
                    # Show cache structure even when empty
                    self.update_cache_display()

    def update_cache_display(self):
        """Update the cache contents display"""
        if not hasattr(self, 'memory_hierarchy') or not self.memory_hierarchy:
            return

        # Clear existing model
        self.cache_model.clear()
        self.cache_model.setHorizontalHeaderLabels(["Cache", "Set", "Way", "Valid", "Tag", "Data", "LRU"])

        try:
            # Display L1 Data Cache
            self._add_cache_to_display("L1D", self.memory_hierarchy.l1_dcache)

            # Display L1 Instruction Cache
            self._add_cache_to_display("L1I", self.memory_hierarchy.l1_icache)

            # Display L2 Cache
            self._add_cache_to_display("L2", self.memory_hierarchy.l2_cache)

            # If no valid blocks to display, show cache structure info
            if self.cache_model.rowCount() == 0:
                self._add_cache_structure_info()

        except Exception as e:
            print(f"Error updating cache display: {e}")

    def _add_cache_structure_info(self):
        """Add cache structure information when no valid blocks exist"""
        try:
            # Get current configuration values from UI
            cache_size_str = self.cache_size_combo.currentText() if hasattr(self, 'cache_size_combo') else "4KB"
            block_size_str = self.block_size_combo.currentText() if hasattr(self, 'block_size_combo') else "32B"
            associativity_str = self.associativity_combo.currentText() if hasattr(self, 'associativity_combo') else "2"
            replacement_policy = self.cache_policy_combo.currentText() if hasattr(self, 'cache_policy_combo') else "LRU"

            # Calculate cache structure info
            cache_size = int(cache_size_str[:-2]) * 1024 if cache_size_str.endswith('KB') else 4096
            block_size = int(block_size_str[:-1]) if block_size_str.endswith('B') else 32
            associativity = int(associativity_str)
            num_sets = cache_size // (block_size * associativity)

            # Show comprehensive cache configuration
            config_info = [
                ("Configuration", "Setting", "Value", "Status", "Details", "", ""),
                ("Cache Size", cache_size_str, f"{cache_size} bytes", "CONFIGURED", f"{num_sets} sets total", "", ""),
                ("Block Size", block_size_str, f"{block_size} bytes", "CONFIGURED", f"Data granularity", "", ""),
                ("Associativity", f"{associativity}-way", f"{associativity} ways/set", "CONFIGURED", "LRU replacement" if replacement_policy == "LRU" else replacement_policy, "", ""),
                ("Replacement", replacement_policy, "Active", "CONFIGURED", "Cache eviction policy", "", "")
            ]

            # Add configuration header
            for info in config_info:
                row = []
                for i, text in enumerate(info):
                    item = QtGui.QStandardItem(text)
                    if i == 0:  # Configuration type
                        item.setBackground(QtGui.QColor("#BBDEFB"))  # Light blue
                        item.setForeground(QtGui.QColor("#1976D2"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        item.setFont(bold_font)
                        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    elif i == 3 and text == "CONFIGURED":  # Status column
                        item.setBackground(QtGui.QColor("#C8E6C9"))  # Light green
                        item.setForeground(QtGui.QColor("#388E3C"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        item.setFont(bold_font)
                        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    else:
                        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    row.append(item)
                self.cache_model.appendRow(row)

            # Add separator
            separator_row = []
            for i in range(7):
                item = QtGui.QStandardItem("=" * 10)
                item.setBackground(QtGui.QColor("#E0E0E0"))  # Neutral gray
                item.setForeground(QtGui.QColor("#616161"))
                bold_font = QFont()
                bold_font.setBold(True)
                item.setFont(bold_font)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                separator_row.append(item)
            self.cache_model.appendRow(separator_row)

            # Show L1D structure if available
            if hasattr(self, 'memory_hierarchy') and self.memory_hierarchy:
                l1d_sets = len(self.memory_hierarchy.l1_dcache.blocks)
                l1d_ways = len(self.memory_hierarchy.l1_dcache.blocks[0]) if l1d_sets > 0 else 0

                row = []
                row.append(QtGui.QStandardItem("L1D Cache"))
                row.append(QtGui.QStandardItem(f"{l1d_sets} sets"))
                row.append(QtGui.QStandardItem(f"{l1d_ways} ways"))
                row.append(QtGui.QStandardItem("EMPTY"))
                row.append(QtGui.QStandardItem("No data loaded"))
                row.append(QtGui.QStandardItem("Ready for data"))
                row.append(QtGui.QStandardItem("---"))

                # Set colors for empty cache
                for i, item in enumerate(row):
                    if i == 0:  # Cache name
                        item.setBackground(QtGui.QColor("#E3F2FD"))
                        item.setForeground(QtGui.QColor("#1565C0"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        item.setFont(bold_font)
                    elif i == 3:  # EMPTY status
                        item.setBackground(QtGui.QColor("#FFF8E1"))
                        item.setForeground(QtGui.QColor("#FF8F00"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        item.setFont(bold_font)
                    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                self.cache_model.appendRow(row)

                # Show L1I structure
                l1i_sets = len(self.memory_hierarchy.l1_icache.blocks)
                l1i_ways = len(self.memory_hierarchy.l1_icache.blocks[0]) if l1i_sets > 0 else 0

                row = []
                row.append(QtGui.QStandardItem("L1I Cache"))
                row.append(QtGui.QStandardItem(f"{l1i_sets} sets"))
                row.append(QtGui.QStandardItem(f"{l1i_ways} ways"))
                row.append(QtGui.QStandardItem("EMPTY"))
                row.append(QtGui.QStandardItem("No data loaded"))
                row.append(QtGui.QStandardItem("Ready for instructions"))
                row.append(QtGui.QStandardItem("---"))

                # Set colors for empty cache
                for i, item in enumerate(row):
                    if i == 0:  # Cache name
                        item.setBackground(QtGui.QColor("#FFF3E0"))
                        item.setForeground(QtGui.QColor("#EF6C00"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        item.setFont(bold_font)
                    elif i == 3:  # EMPTY status
                        item.setBackground(QtGui.QColor("#FFF8E1"))
                        item.setForeground(QtGui.QColor("#FF8F00"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        item.setFont(bold_font)
                    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                self.cache_model.appendRow(row)
            else:
                # Show basic structure when memory hierarchy is not initialized
                row = []
                row.append(QtGui.QStandardItem("Cache"))
                row.append(QtGui.QStandardItem("Not initialized"))
                row.append(QtGui.QStandardItem("---"))
                row.append(QtGui.QStandardItem("PENDING"))
                row.append(QtGui.QStandardItem("Apply configuration first"))
                row.append(QtGui.QStandardItem("---"))
                row.append(QtGui.QStandardItem("---"))

                # Set colors for pending state
                for i, item in enumerate(row):
                    if i == 0:  # Cache name
                        item.setBackground(QtGui.QColor("#FFEBEE"))
                        item.setForeground(QtGui.QColor("#C62828"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        item.setFont(bold_font)
                    elif i == 3:  # PENDING status
                        item.setBackground(QtGui.QColor("#FFCCBC"))
                        item.setForeground(QtGui.QColor("#D84315"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        item.setFont(bold_font)
                    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                self.cache_model.appendRow(row)

        except Exception as e:
            print(f"Error adding cache structure info: {e}")

    def _add_cache_to_display(self, cache_name, cache):
        """Add a specific cache to the display table - only show valid blocks with data"""
        valid_blocks_added = 0

        for set_idx, cache_set in enumerate(cache.blocks):
            for way_idx, block in enumerate(cache_set):
                # Only display valid cache blocks that actually contain data
                if not block.valid:
                    continue

                # Skip blocks that don't have meaningful data
                if not hasattr(block, 'data') or block.data is None:
                    continue

                row = []

                # Cache name with color coding
                cache_item = QtGui.QStandardItem(cache_name)
                cache_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

                # Color code by cache type - improved colors for better visibility
                if cache_name == "L1D":
                    cache_item.setBackground(QtGui.QColor("#E3F2FD"))  # Light blue - Data cache
                    cache_item.setForeground(QtGui.QColor("#1565C0"))
                    bold_font = QFont()
                    bold_font.setBold(True)
                    cache_item.setFont(bold_font)
                elif cache_name == "L1I":
                    cache_item.setBackground(QtGui.QColor("#FFF3E0"))  # Light orange - Instruction cache
                    cache_item.setForeground(QtGui.QColor("#EF6C00"))
                    bold_font = QFont()
                    bold_font.setBold(True)
                    cache_item.setFont(bold_font)
                elif cache_name == "L2":
                    cache_item.setBackground(QtGui.QColor("#F3E5F5"))  # Light purple - L2 cache
                    cache_item.setForeground(QtGui.QColor("#7B1FA2"))
                    bold_font = QFont()
                    bold_font.setBold(True)
                    cache_item.setFont(bold_font)

                row.append(cache_item)

                # Set index
                set_item = QtGui.QStandardItem(str(set_idx))
                set_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                row.append(set_item)

                # Way index
                way_item = QtGui.QStandardItem(str(way_idx))
                way_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                row.append(way_item)

                # Valid bit (always 1 since we only show valid blocks)
                valid_item = QtGui.QStandardItem("VALID")
                valid_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                valid_item.setBackground(QtGui.QColor("#C8E6C9"))  # Light green
                valid_item.setForeground(QtGui.QColor("#2E7D32"))
                bold_font = QFont()
                bold_font.setBold(True)
                valid_item.setFont(bold_font)
                row.append(valid_item)

                # Tag - improved formatting
                try:
                    if hasattr(block, 'tag') and block.tag is not None:
                        if isinstance(block.tag, str):
                            # Handle string tags
                            tag_value = int(block.tag, 16) if block.tag.startswith('0x') else int(block.tag)
                        else:
                            # Handle numeric tags
                            tag_value = int(block.tag)
                        tag_str = f"0x{tag_value:08X}"
                    else:
                        tag_str = "0x00000000"
                except (ValueError, TypeError):
                    tag_str = "0x00000000"

                tag_item = QtGui.QStandardItem(tag_str)
                tag_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                row.append(tag_item)

                # Data (show meaningful portion) - enhanced display
                try:
                    if isinstance(block.data, (list, tuple)) and len(block.data) > 0:
                        # Handle list/tuple of bytes
                        data_bytes = [int(b) & 0xFF for b in block.data[:8]]  # Show first 8 bytes
                        data_str = " ".join([f"{b:02X}" for b in data_bytes])
                        if len(block.data) > 8:
                            data_str += "..."
                    elif isinstance(block.data, (bytes, bytearray)) and len(block.data) > 0:
                        # Handle bytes and bytearray objects
                        data_bytes = block.data[:8]  # Show first 8 bytes
                        data_str = " ".join([f"{b:02X}" for b in data_bytes])
                        if len(block.data) > 8:
                            data_str += "..."
                    elif isinstance(block.data, str) and block.data.strip():
                        # Handle string representation
                        if block.data.startswith('0x'):
                            # Parse hex string
                            try:
                                hex_val = int(block.data, 16)
                                data_str = f"{hex_val:08X}"
                            except ValueError:
                                data_str = block.data[:16] + ("..." if len(block.data) > 16 else "")
                        else:
                            data_str = block.data[:16] + ("..." if len(block.data) > 16 else "")
                    elif isinstance(block.data, (int, float)):
                        # Handle numeric data
                        data_val = int(block.data) & 0xFFFFFFFF
                        data_str = f"{data_val:08X}"
                    else:
                        # Default representation for other data types
                        data_str = str(block.data)[:16]
                        if len(str(block.data)) > 16:
                            data_str += "..."

                except Exception:
                    # Skip blocks that can't be processed
                    continue

                # Only add blocks that have actual data to display
                if not data_str or data_str.strip() in ["", "00000000", "0", "00 00 00 00"]:
                    continue

                data_item = QtGui.QStandardItem(data_str)
                data_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
                row.append(data_item)

                # LRU information with color coding
                lru_str = str(getattr(block, 'lru_counter', 0))
                lru_item = QtGui.QStandardItem(lru_str)
                lru_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

                # Color code LRU values (lower = more recently used) - improved colors
                try:
                    lru_val = int(lru_str)
                    if lru_val == 0:
                        lru_item.setBackground(QtGui.QColor("#A5D6A7"))  # Fresh green - Most recent
                        lru_item.setForeground(QtGui.QColor("#1B5E20"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        lru_item.setFont(bold_font)
                    elif lru_val <= 2:
                        lru_item.setBackground(QtGui.QColor("#FFECB3"))  # Warm yellow - Moderate
                        lru_item.setForeground(QtGui.QColor("#F57C00"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        lru_item.setFont(bold_font)
                    else:
                        lru_item.setBackground(QtGui.QColor("#FFCDD2"))  # Light red - Least recent
                        lru_item.setForeground(QtGui.QColor("#C62828"))
                        bold_font = QFont()
                        bold_font.setBold(True)
                        lru_item.setFont(bold_font)
                except ValueError:
                    pass

                row.append(lru_item)

                self.cache_model.appendRow(row)
                valid_blocks_added += 1

                # Limit display to prevent UI slowdown - show only first 20 valid blocks per cache
                if valid_blocks_added >= 20:
                    # Add indication that there are more blocks
                    more_row = []
                    more_row.append(QtGui.QStandardItem(f"{cache_name}"))
                    more_row.append(QtGui.QStandardItem("..."))
                    more_row.append(QtGui.QStandardItem("..."))
                    more_row.append(QtGui.QStandardItem("MORE"))
                    more_row.append(QtGui.QStandardItem("..."))
                    more_row.append(QtGui.QStandardItem("Additional blocks exist"))
                    more_row.append(QtGui.QStandardItem("..."))

                    for item in more_row:
                        if item.text() == "MORE":
                            item.setBackground(QtGui.QColor("#E1F5FE"))
                            item.setForeground(QtGui.QColor("#0277BD"))
                            bold_font = QFont()
                            bold_font.setBold(True)
                            item.setFont(bold_font)
                        else:
                            item.setBackground(QtGui.QColor("#F5F5F5"))
                            item.setForeground(QtGui.QColor("#757575"))
                        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

                    self.cache_model.appendRow(more_row)
                    return  # Stop adding more blocks for this cache

        # If no valid blocks were added, add a summary row
        if valid_blocks_added == 0:
            row = []
            row.append(QtGui.QStandardItem(cache_name))
            row.append(QtGui.QStandardItem("All sets"))
            row.append(QtGui.QStandardItem("All ways"))
            row.append(QtGui.QStandardItem("NO DATA"))
            row.append(QtGui.QStandardItem("---"))
            row.append(QtGui.QStandardItem("Cache configured but empty"))
            row.append(QtGui.QStandardItem("---"))

            for item in row:
                if item.text() == "NO DATA":
                    item.setBackground(QtGui.QColor("#FFF8E1"))  # Light amber for NO DATA
                    item.setForeground(QtGui.QColor("#E65100"))  # Dark orange text
                elif item.text() == "Cache configured but empty":
                    item.setBackground(QtGui.QColor("#F5F5F5"))  # Light gray for status
                    item.setForeground(QtGui.QColor("#616161"))  # Medium gray text
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            self.cache_model.appendRow(row)

    def simulate_memory_access(self, address, access_type="read", update_display=True):
        """Simulate a memory access through the cache"""
        if not hasattr(self, 'memory_hierarchy') or not self.memory_hierarchy:
            return False

        try:
            # Convert address to integer if it's a string
            if isinstance(address, str):
                addr = int(address, 16)
            else:
                addr = address

            # Perform memory access through hierarchy
            if access_type.lower() == "instruction_fetch":
                # Instruction fetch from I-cache
                self.memory_hierarchy.read_instruction(addr)
            elif access_type.lower() == "read":
                # Data read from D-cache
                self.memory_hierarchy.read_data(addr)
            else:  # write
                # Data write to D-cache
                self.memory_hierarchy.write_data(addr, 0)  # Dummy value for simulation

            # Update cache display (less frequently to avoid performance issues)
            # Only update if explicitly requested and randomly selected
            if update_display and random.random() < 0.01:  # Update display 1% of the time
                self.update_cache_display()

            return True

        except Exception as e:
            print(f"Error in cache simulation for address 0x{addr:08X}: {e}")
            return False

    def _update_cache_statistics(self):
        """Update the cache statistics display"""
        if not hasattr(self, 'memory_hierarchy') or not self.memory_hierarchy:
            return

        try:
            stats = self.memory_hierarchy.get_statistics()

            # Calculate combined L1 statistics
            l1d_stats = stats['l1_dcache']
            l1i_stats = stats['l1_icache']

            total_l1_accesses = l1d_stats['accesses'] + l1i_stats['accesses']
            total_l1_hits = l1d_stats['hits'] + l1i_stats['hits']
            total_l1_misses = l1d_stats['misses'] + l1i_stats['misses']

            hit_rate = (total_l1_hits / total_l1_accesses * 100) if total_l1_accesses > 0 else 0
            miss_rate = (total_l1_misses / total_l1_accesses * 100) if total_l1_accesses > 0 else 0

            self.hit_rate_value.setText(f"{hit_rate:.2f}%")
            self.miss_rate_value.setText(f"{miss_rate:.2f}%")
            self.total_accesses_value.setText(str(total_l1_accesses))
            self.cache_hits_value.setText(str(total_l1_hits))
            self.cache_misses_value.setText(str(total_l1_misses))

        except Exception as e:
            print(f"Error updating cache statistics: {e}")

    def run_automated_benchmark(self):
        """Run automated benchmark testing across all configurations"""
        try:
            # Show progress dialog
            progress = QtWidgets.QProgressDialog("Running benchmark tests...", "Cancel", 0, 100, self.tabWidget)
            progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            # Get available binary files
            demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Demo")
            binary_files = [f for f in os.listdir(demo_path) if f.endswith('.bin')]

            if not binary_files:
                QtWidgets.QMessageBox.warning(None, "Warning", "No binary files found in Demo folder")
                return

            # Define test configurations based on Milestone 2 requirements
            test_configs = self._get_milestone2_configurations()

            results = []
            total_tests = len(binary_files) * len(test_configs)
            current_test = 0

            # Test each binary file with each configuration
            for binary_file in binary_files:
                for config in test_configs:
                    if progress.wasCanceled():
                        return

                    # Update progress
                    progress.setValue(int((current_test / total_tests) * 100))
                    progress.setLabelText(f"Testing {binary_file} with {config['name']}...")
                    QtCore.QCoreApplication.processEvents()

                    # Run single test
                    result = self._run_single_benchmark_test(binary_file, config)
                    if result:
                        results.append(result)

                    current_test += 1

            progress.setValue(100)
            progress.close()

            # Save results to CSV file
            self._save_benchmark_results(results)

            # Find and display optimal configurations
            self._display_optimal_configurations(results)

        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "Error", f"Benchmark failed: {e}")

    def _get_milestone2_configurations(self):
        """Get all cache configurations as per Milestone 2 requirements"""
        configs = []

        # L1 Cache configurations (1KB each for I and D)
        l1_sizes = ["1KB"]  # Milestone 2 requirement
        l1_block_sizes = ["4B", "8B", "16B", "32B"]  # Configurable as per requirements
        l1_types = ["1", "2", "4"]  # Direct (1), 2-way, 4-way associative

        # L2 Cache (16KB unified)
        l2_block_sizes = ["16B", "32B", "64B"]  # Configurable as per requirements

        config_id = 1
        for l1_size in l1_sizes:
            for l1_block_size in l1_block_sizes:
                for l1_assoc in l1_types:
                    for l2_block_size in l2_block_sizes:
                        configs.append({
                            'id': config_id,
                            'name': f"L1:{l1_size}-{l1_block_size}-{l1_assoc}way_L2:16KB-{l2_block_size}",
                            'l1_size': l1_size,
                            'l1_block_size': l1_block_size,
                            'l1_associativity': l1_assoc,
                            'l2_block_size': l2_block_size
                        })
                        config_id += 1

        return configs

    def _run_single_benchmark_test(self, binary_file, config):
        """Run a single benchmark test with given configuration"""
        try:
            # Apply configuration
            self.cache_size_combo.setCurrentText(config['l1_size'])
            self.block_size_combo.setCurrentText(config['l1_block_size'])
            self.associativity_combo.setCurrentText(config['l1_associativity'])

            # Apply cache configuration
            self.apply_cache_configuration()

            # Reset statistics
            self.reset_cache_statistics()

            # Load and run binary file
            demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Demo")
            file_path = os.path.join(demo_path, binary_file)

            with open(file_path, 'rb') as f:
                data = f.read()

            # Load program into memory
            base_address = 0x1000
            self.memory_hierarchy.main_memory.load_program(data, base_address)

            # Simulate instruction fetches and data accesses
            instruction_count = 0
            for i in range(0, len(data), 4):
                address = base_address + i
                # Simulate instruction fetch
                self.simulate_memory_access(address, "instruction_fetch")
                instruction_count += 1

                # Simulate some data accesses for realistic patterns
                if i % 16 == 0:  # Every 4th instruction does data access
                    data_addr = 0x2000 + i
                    self.simulate_memory_access(data_addr, "read")

            # Get final statistics
            stats = self.memory_hierarchy.get_statistics()

            # Calculate cost function as per Milestone 2
            l1_misses = stats['total_l1_misses']
            l2_misses = stats['l2_cache']['misses']
            write_backs = stats['total_write_backs']

            cost = 0.5 * l1_misses + l2_misses + write_backs

            return {
                'binary_file': binary_file,
                'config_name': config['name'],
                'config_id': config['id'],
                'l1_size': config['l1_size'],
                'l1_block_size': config['l1_block_size'],
                'l1_associativity': config['l1_associativity'],
                'l2_block_size': config['l2_block_size'],
                'l1_misses': l1_misses,
                'l2_misses': l2_misses,
                'write_backs': write_backs,
                'cost': cost,
                'instruction_count': instruction_count,
                'l1_hit_rate': (stats['l1_dcache']['hits'] + stats['l1_icache']['hits']) /
                              (stats['l1_dcache']['accesses'] + stats['l1_icache']['accesses']) * 100
                              if (stats['l1_dcache']['accesses'] + stats['l1_icache']['accesses']) > 0 else 0
            }

        except Exception as e:
            print(f"Error in benchmark test {config['name']} with {binary_file}: {e}")
            return None

    def _save_benchmark_results(self, results):
        """Save benchmark results to CSV file in Result folder"""
        try:
            import csv
            from datetime import datetime
            from pathlib import Path

            # Create Result folder if it doesn't exist
            results_dir = Path("Result")
            results_dir.mkdir(exist_ok=True)

            # Create results filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = results_dir / f"benchmark_results_{timestamp}.csv"

            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['binary_file', 'config_name', 'config_id', 'l1_size', 'l1_block_size',
                             'l1_associativity', 'l2_block_size', 'l1_misses', 'l2_misses',
                             'write_backs', 'cost', 'instruction_count', 'l1_hit_rate']

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for result in results:
                    writer.writerow(result)

            print(f"Benchmark results saved to {filename}")

        except Exception as e:
            print(f"Error saving benchmark results: {e}")

    def _display_optimal_configurations(self, results):
        """Find and display optimal configurations for each binary file"""
        if not results:
            return

        try:
            # Group results by binary file
            binary_results = {}
            for result in results:
                binary_file = result['binary_file']
                if binary_file not in binary_results:
                    binary_results[binary_file] = []
                binary_results[binary_file].append(result)

            # Find optimal configuration for each binary file
            optimal_configs = {}
            for binary_file, file_results in binary_results.items():
                # Find minimum cost configuration
                min_cost_result = min(file_results, key=lambda x: x['cost'])
                optimal_configs[binary_file] = min_cost_result

            # Create summary dialog
            summary_text = "MILESTONE 2 BENCHMARK RESULTS\n"
            summary_text += "=" * 50 + "\n\n"

            summary_text += "OPTIMAL CONFIGURATIONS BY PROGRAM:\n"
            summary_text += "-" * 40 + "\n"

            for binary_file, optimal in optimal_configs.items():
                summary_text += f"\nProgram: {binary_file}\n"
                summary_text += f"  Optimal Config: {optimal['config_name']}\n"
                summary_text += f"  Cost: {optimal['cost']:.2f}\n"
                summary_text += f"  L1 Misses: {optimal['l1_misses']}\n"
                summary_text += f"  L2 Misses: {optimal['l2_misses']}\n"
                summary_text += f"  Write-backs: {optimal['write_backs']}\n"
                summary_text += f"  L1 Hit Rate: {optimal['l1_hit_rate']:.2f}%\n"

            # Overall best configuration
            overall_best = min(results, key=lambda x: x['cost'])
            summary_text += f"\nOVERALL BEST CONFIGURATION:\n"
            summary_text += f"  Config: {overall_best['config_name']}\n"
            summary_text += f"  Program: {overall_best['binary_file']}\n"
            summary_text += f"  Minimum Cost: {overall_best['cost']:.2f}\n"

            # Cost function explanation
            summary_text += f"\nCOST FUNCTION: 0.5 × L1_misses + L2_misses + write_backs\n"
            summary_text += f"(As specified in Milestone 2 requirements)\n"

            # Show results dialog
            dialog = QtWidgets.QDialog()
            dialog.setWindowTitle("Benchmark Results - Milestone 2")
            dialog.setModal(True)
            dialog.resize(600, 500)

            layout = QtWidgets.QVBoxLayout(dialog)

            text_area = QtWidgets.QTextEdit()
            text_area.setPlainText(summary_text)
            text_area.setReadOnly(True)
            layout.addWidget(text_area)

            button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok)
            button_box.accepted.connect(dialog.accept)
            layout.addWidget(button_box)

            dialog.exec()

        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "Error", f"Error displaying results: {e}")

class CacheWrapper:
    """Wrapper class to make MemoryHierarchy compatible with existing UI code"""

    def __init__(self, memory_hierarchy):
        self.memory_hierarchy = memory_hierarchy
        self.stats = {'total_accesses': 0, 'hits': 0, 'misses': 0}

    def access(self, address, access_type="read"):
        """Access memory through the hierarchy"""
        try:
            if access_type.lower() == "read":
                # Simple heuristic: treat low addresses as instructions
                if address < 0x1000:
                    self.memory_hierarchy.read_instruction(address)
                else:
                    self.memory_hierarchy.read_data(address)
            else:
                self.memory_hierarchy.write_data(address, 0)

            # Update wrapper stats
            stats = self.memory_hierarchy.get_statistics()
            l1d_stats = stats['l1_dcache']
            l1i_stats = stats['l1_icache']

            self.stats['total_accesses'] = l1d_stats['accesses'] + l1i_stats['accesses']
            self.stats['hits'] = l1d_stats['hits'] + l1i_stats['hits']
            self.stats['misses'] = l1d_stats['misses'] + l1i_stats['misses']

            # Return True if it was a hit (simplified)
            return self.stats['hits'] > 0

        except Exception as e:
            print(f"Cache access error: {e}")
            return False

    def reset_stats(self):
        """Reset statistics"""
        if self.memory_hierarchy:
            self.memory_hierarchy.reset_statistics()
        self.stats = {'total_accesses': 0, 'hits': 0, 'misses': 0}

    @property
    def sets(self):
        """Return cache sets for display (L1D cache)"""
        if self.memory_hierarchy:
            return self.memory_hierarchy.l1_dcache.blocks
        return []


def main():
    """Main function to launch the ARMv7 Simulator GUI"""
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
