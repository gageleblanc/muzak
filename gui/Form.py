# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.2.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QLineEdit,
    QListView, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QSplitter, QStatusBar,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget)

class Ui_Morganizr(object):
    def setupUi(self, Morganizr):
        if not Morganizr.objectName():
            Morganizr.setObjectName(u"Morganizr")
        Morganizr.resize(800, 624)
        self.actionAbout = QAction(Morganizr)
        self.actionAbout.setObjectName(u"actionAbout")
        self.centralwidget = QWidget(Morganizr)
        self.centralwidget.setObjectName(u"centralwidget")
        self.groupBox = QGroupBox(self.centralwidget)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setGeometry(QRect(10, 10, 771, 331))
        self.verticalLayout = QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.splitter = QSplitter(self.groupBox)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.SearchPathInput = QLineEdit(self.splitter)
        self.SearchPathInput.setObjectName(u"SearchPathInput")
        self.SearchPathInput.setBaseSize(QSize(1024, 768))
        self.splitter.addWidget(self.SearchPathInput)
        self.addPathButton = QPushButton(self.splitter)
        self.addPathButton.setObjectName(u"addPathButton")
        self.splitter.addWidget(self.addPathButton)
        self.scanButton = QPushButton(self.splitter)
        self.scanButton.setObjectName(u"scanButton")
        self.splitter.addWidget(self.scanButton)

        self.verticalLayout.addWidget(self.splitter)

        self.scannedFilesTabs = QTabWidget(self.groupBox)
        self.scannedFilesTabs.setObjectName(u"scannedFilesTabs")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.verticalLayout_3 = QVBoxLayout(self.tab)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.listView_2 = QListView(self.tab)
        self.listView_2.setObjectName(u"listView_2")

        self.verticalLayout_3.addWidget(self.listView_2)

        self.scannedFilesTabs.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.verticalLayout_2 = QVBoxLayout(self.tab_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.listView = QListView(self.tab_2)
        self.listView.setObjectName(u"listView")

        self.verticalLayout_2.addWidget(self.listView)

        self.scannedFilesTabs.addTab(self.tab_2, "")

        self.verticalLayout.addWidget(self.scannedFilesTabs)

        self.groupBox_2 = QGroupBox(self.centralwidget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setGeometry(QRect(10, 350, 781, 232))
        self.gridLayout = QGridLayout(self.groupBox_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.textEdit = QTextEdit(self.groupBox_2)
        self.textEdit.setObjectName(u"textEdit")

        self.gridLayout.addWidget(self.textEdit, 0, 0, 1, 1)

        Morganizr.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(Morganizr)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 21))
        self.menuMorganizr = QMenu(self.menubar)
        self.menuMorganizr.setObjectName(u"menuMorganizr")
        Morganizr.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(Morganizr)
        self.statusbar.setObjectName(u"statusbar")
        Morganizr.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuMorganizr.menuAction())
        self.menuMorganizr.addAction(self.actionAbout)

        self.retranslateUi(Morganizr)

        self.scannedFilesTabs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Morganizr)
    # setupUi

    def retranslateUi(self, Morganizr):
        Morganizr.setWindowTitle(QCoreApplication.translate("Morganizr", u"Morganizr", None))
        self.actionAbout.setText(QCoreApplication.translate("Morganizr", u"About", None))
        self.groupBox.setTitle(QCoreApplication.translate("Morganizr", u"Scan Settings", None))
        self.addPathButton.setText(QCoreApplication.translate("Morganizr", u"Add", None))
        self.scanButton.setText(QCoreApplication.translate("Morganizr", u"Scan", None))
        self.scannedFilesTabs.setTabText(self.scannedFilesTabs.indexOf(self.tab), QCoreApplication.translate("Morganizr", u"Music Files", None))
        self.scannedFilesTabs.setTabText(self.scannedFilesTabs.indexOf(self.tab_2), QCoreApplication.translate("Morganizr", u"All Files", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Morganizr", u"Logs", None))
        self.menuMorganizr.setTitle(QCoreApplication.translate("Morganizr", u"Morganizr", None))
    # retranslateUi

    def addScanPath(self):
        print("Add scan path")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    Morganizr = QMainWindow()
    ui = Ui_Morganizr()
    ui.setupUi(Morganizr)
    Morganizr.show()
    sys.exit(app.exec_())
