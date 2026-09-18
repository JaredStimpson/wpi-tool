from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    AnalysisConfig,
    ConfigurationError,
    MatrixConfig,
    OutputsConfig,
    RunConfig,
    VariationConfig,
    load_config,
    save_config,
)
from ..excel.connection import XlwingsWorkbook
from ..matrix import display_saaty
from ..models import RunPlan, RunSummary
from ..plotting import save_tornado
from ..sensitivity import build_run_plan, run_excel_analysis


class AnalysisWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, config: AnalysisConfig, results_root: Path) -> None:
        super().__init__()
        self.config = config
        self.results_root = results_root
        self.cancel_requested = False

    @Slot()
    def run(self) -> None:
        try:
            summary = run_excel_analysis(
                self.config,
                self.results_root,
                progress=lambda done, total, label: self.progress.emit(done, total, label),
                cancelled=lambda: self.cancel_requested,
            )
            self.finished.emit(summary)
        except Exception as exc:
            self.failed.emit(str(exc))

    @Slot()
    def cancel(self) -> None:
        self.cancel_requested = True


class MainWindow(QMainWindow):
    def __init__(self, preset: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("WPI Sensitivity Analyzer")
        self.resize(1180, 760)
        self._preset_path: Path | None = preset
        self._plan: RunPlan | None = None
        self._thread: QThread | None = None
        self._worker: AnalysisWorker | None = None
        self._build_ui()
        self._build_actions()
        if preset:
            self.load_preset(preset)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        header = QHBoxLayout()
        title = QLabel("WPI Sensitivity Analyzer")
        title.setStyleSheet("font-size: 20px; font-weight: 600")
        self.workbook_status = QLabel("No workbook")
        self.connection_status = QLabel("● Disconnected")
        self.connection_status.setAccessibleName("Excel connection status: disconnected")
        self.protection_status = QLabel("🛡 Working-copy protection on")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.workbook_status)
        header.addWidget(self.connection_status)
        header.addWidget(self.protection_status)
        root_layout.addLayout(header)

        body = QHBoxLayout()
        self.navigation = QListWidget()
        self.navigation.setFixedWidth(220)
        for label in ("1  Workbook setup", "2  Comparisons", "3  Run analysis", "4  Results"):
            self.navigation.addItem(QListWidgetItem(label))
        self.navigation.currentRowChanged.connect(self._navigate)
        body.addWidget(self.navigation)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._setup_page())
        self.pages.addWidget(self._comparisons_page())
        self.pages.addWidget(self._run_page())
        self.pages.addWidget(self._results_page())
        body.addWidget(self.pages, 1)
        root_layout.addLayout(body, 1)
        self.setCentralWidget(root)
        self.navigation.setCurrentRow(0)
        self.statusBar().showMessage("Ready")

    def _setup_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        workbook_box = QGroupBox("Workbook")
        form = QFormLayout(workbook_box)
        workbook_row = QHBoxLayout()
        self.workbook_edit = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.choose_workbook)
        workbook_row.addWidget(self.workbook_edit)
        workbook_row.addWidget(browse)
        form.addRow("Workbook path", workbook_row)
        self.worksheet_edit = QLineEdit()
        form.addRow("Worksheet", self.worksheet_edit)
        layout.addWidget(workbook_box)

        ranges = QGroupBox("Pairwise matrix and outputs")
        range_form = QFormLayout(ranges)
        self.matrix_edit = QLineEdit("C5:G9")
        self.row_labels_edit = QLineEdit("B5:B9")
        self.column_labels_edit = QLineEdit("C4:G4")
        self.output_values_edit = QLineEdit("M5:M10")
        self.output_labels_edit = QLineEdit("L5:L10")
        self.winner_edit = QLineEdit()
        self.weights_edit = QLineEdit()
        for label, widget in (
            ("Matrix values", self.matrix_edit),
            ("Row labels", self.row_labels_edit),
            ("Column labels", self.column_labels_edit),
            ("Output values", self.output_values_edit),
            ("Output labels", self.output_labels_edit),
            ("Winner cell (optional)", self.winner_edit),
            ("Property weights (optional)", self.weights_edit),
        ):
            range_form.addRow(label, widget)
        layout.addWidget(ranges)
        self.validation_label = QLabel("Enter a workbook and ranges, then validate.")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)
        buttons = QHBoxLayout()
        validate = QPushButton("Validate configuration")
        validate.clicked.connect(self.validate_workbook)
        continue_button = QPushButton("Continue to Comparisons →")
        continue_button.clicked.connect(lambda: self.navigation.setCurrentRow(1))
        buttons.addWidget(validate)
        buttons.addStretch()
        buttons.addWidget(continue_button)
        layout.addLayout(buttons)
        layout.addStretch()
        return page

    def _comparisons_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        controls = QHBoxLayout()
        self.variation_combo = QComboBox()
        self.variation_combo.addItem("Adjacent Saaty-scale values", "saaty_steps")
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 8)
        self.steps_spin.setValue(1)
        controls.addWidget(QLabel("Variation"))
        controls.addWidget(self.variation_combo)
        controls.addWidget(QLabel("Steps"))
        controls.addWidget(self.steps_spin)
        controls.addStretch()
        layout.addLayout(controls)
        self.comparisons_table = QTableWidget(0, 7)
        self.comparisons_table.setHorizontalHeaderLabels(
            ("Use", "Comparison", "Input", "Reciprocal", "Baseline", "Low", "High")
        )
        self.comparisons_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.comparisons_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.comparisons_table)
        self.comparison_summary = QLabel("Validate a workbook to build comparisons.")
        layout.addWidget(self.comparison_summary)
        next_button = QPushButton("Continue to Run analysis →")
        next_button.clicked.connect(lambda: self.navigation.setCurrentRow(2))
        layout.addWidget(next_button, alignment=Qt.AlignmentFlag.AlignRight)
        return page

    def _run_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.workload = QLabel("No validated run plan.")
        self.workload.setStyleSheet("font-size: 16px; font-weight: 600")
        layout.addWidget(self.workload)
        protection = QGroupBox("Protection options")
        protection_layout = QVBoxLayout(protection)
        for text in (
            "Use a temporary workbook copy",
            "Restore after every comparison",
            "Verify restored outputs against baseline",
            "Write each result immediately",
            "Stop when restoration fails",
        ):
            checkbox = QCheckBox(text)
            checkbox.setChecked(True)
            checkbox.setEnabled(False)
            protection_layout.addWidget(checkbox)
        layout.addWidget(protection)
        result_row = QHBoxLayout()
        self.results_edit = QLineEdit(str(Path.cwd() / "results"))
        choose_results = QPushButton("Choose…")
        choose_results.clicked.connect(self.choose_results)
        result_row.addWidget(self.results_edit)
        result_row.addWidget(choose_results)
        layout.addWidget(QLabel("Results folder"))
        layout.addLayout(result_row)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        run_controls = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel safely")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_analysis)
        self.run_button = QPushButton("Run analysis (F5)")
        self.run_button.clicked.connect(self.start_analysis)
        run_controls.addStretch()
        run_controls.addWidget(self.cancel_button)
        run_controls.addWidget(self.run_button)
        layout.addLayout(run_controls)
        layout.addStretch()
        return page

    def _results_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        heading = QLabel("Results")
        heading.setStyleSheet("font-size: 18px; font-weight: 600")
        layout.addWidget(heading)
        self.results_summary = QLabel(
            "Completed and partial runs appear in the selected results folder. "
            "The CSV log is the durable source for charts and reports."
        )
        self.results_summary.setWordWrap(True)
        layout.addWidget(self.results_summary)
        layout.addStretch()
        return page

    def _build_actions(self) -> None:
        open_action = QAction("Open workbook", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.choose_workbook)
        save_action = QAction("Save preset", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_preset)
        load_action = QAction("Load preset", self)
        load_action.triggered.connect(self.choose_preset)
        run_action = QAction("Run", self)
        run_action.setShortcut(QKeySequence("F5"))
        run_action.triggered.connect(self.start_analysis)
        menu = self.menuBar().addMenu("File")
        menu.addActions((open_action, load_action, save_action))
        self.addActions((open_action, save_action, run_action))

    def _navigate(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    def choose_workbook(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose WPI workbook", "", "Excel workbooks (*.xlsx *.xlsm *.xlsb)"
        )
        if path:
            self.workbook_edit.setText(path)
            self.workbook_status.setText(Path(path).name)

    def choose_results(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose results folder")
        if path:
            self.results_edit.setText(path)

    def current_config(self) -> AnalysisConfig:
        return AnalysisConfig(
            workbook=self.workbook_edit.text().strip(),
            worksheet=self.worksheet_edit.text().strip(),
            matrix=MatrixConfig(
                self.matrix_edit.text().strip(),
                self.row_labels_edit.text().strip(),
                self.column_labels_edit.text().strip(),
            ),
            outputs=OutputsConfig(
                self.output_values_edit.text().strip(),
                self.output_labels_edit.text().strip(),
                self.winner_edit.text().strip() or None,
                property_weights=self.weights_edit.text().strip() or None,
            ),
            variation=VariationConfig(steps=self.steps_spin.value()),
            run=RunConfig(),
        )

    def validate_workbook(self) -> None:
        config = self.current_config()
        self.statusBar().showMessage("Validating with Excel…")
        QApplication.processEvents()
        workbook = None
        try:
            workbook = XlwingsWorkbook(config.resolved_workbook(), visible=False)
            self._plan = build_run_plan(workbook, config)
            self._populate_comparisons()
            plan = self._plan
            self.validation_label.setText(
                f"✓ Valid {len(plan.labels)}×{len(plan.labels)} matrix with "
                f"{len(plan.comparisons)} independent comparisons and "
                f"{len(plan.outputs)} outputs."
            )
            self.connection_status.setText("● Validated")
            self.workload.setText(
                f"{sum(item.enabled for item in plan.comparisons)} comparisons • "
                f"{plan.evaluation_count} Excel evaluations • {len(plan.outputs)} outputs"
            )
            self.statusBar().showMessage("Configuration valid", 5000)
        except Exception as exc:
            self._plan = None
            self.validation_label.setText(f"⚠ {exc}")
            self.connection_status.setText("● Warning")
            QMessageBox.warning(self, "Validation failed", str(exc))
            self.statusBar().showMessage("Validation failed", 5000)
        finally:
            if workbook is not None:
                workbook.close()

    def _populate_comparisons(self) -> None:
        assert self._plan is not None
        self.comparisons_table.setRowCount(len(self._plan.comparisons))
        for row, item in enumerate(self._plan.comparisons):
            enabled = QTableWidgetItem("✓")
            enabled.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            values = (
                enabled,
                QTableWidgetItem(item.name),
                QTableWidgetItem(item.input_cell),
                QTableWidgetItem(item.reciprocal_cell),
                QTableWidgetItem(display_saaty(item.baseline)),
                QTableWidgetItem(display_saaty(item.low)),
                QTableWidgetItem(display_saaty(item.high)),
            )
            for column, value in enumerate(values):
                self.comparisons_table.setItem(row, column, value)
        self.comparison_summary.setText(
            f"{len(self._plan.comparisons)} enabled comparisons in original matrix order."
        )

    def choose_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load preset", "", "JSON presets (*.json)")
        if path:
            self.load_preset(Path(path))

    def load_preset(self, path: Path) -> None:
        try:
            config = load_config(path)
        except ConfigurationError as exc:
            QMessageBox.warning(self, "Preset error", str(exc))
            return
        self._preset_path = path
        self.workbook_edit.setText(str(config.resolved_workbook(path)))
        self.worksheet_edit.setText(config.worksheet)
        self.matrix_edit.setText(config.matrix.values)
        self.row_labels_edit.setText(config.matrix.row_labels)
        self.column_labels_edit.setText(config.matrix.column_labels)
        self.output_values_edit.setText(config.outputs.values)
        self.output_labels_edit.setText(config.outputs.labels)
        self.winner_edit.setText(config.outputs.winner or "")
        self.weights_edit.setText(config.outputs.property_weights or "")
        self.steps_spin.setValue(config.variation.steps)
        self.workbook_status.setText(Path(config.workbook).name)
        self.statusBar().showMessage(f"Loaded {path.name}", 5000)

    def save_preset(self) -> None:
        path = self._preset_path
        if path is None:
            selected, _ = QFileDialog.getSaveFileName(
                self, "Save preset", "wpi-preset.json", "JSON presets (*.json)"
            )
            if not selected:
                return
            path = Path(selected)
        if (
            path.exists()
            and path != self._preset_path
            and (
                QMessageBox.question(self, "Overwrite preset?", f"Replace {path.name}?")
                != QMessageBox.StandardButton.Yes
            )
        ):
            return
        try:
            save_config(self.current_config(), path)
            self._preset_path = path
            self.statusBar().showMessage(f"Saved {path.name}", 5000)
        except Exception as exc:
            QMessageBox.warning(self, "Could not save preset", str(exc))

    def start_analysis(self) -> None:
        if self._plan is None:
            QMessageBox.information(
                self,
                "Validate first",
                "Validate the workbook configuration before running an analysis.",
            )
            self.navigation.setCurrentRow(0)
            return
        if self._thread is not None:
            return
        results_root = Path(self.results_edit.text()).expanduser().resolve()
        results_root.mkdir(parents=True, exist_ok=True)
        self._thread = QThread(self)
        self._worker = AnalysisWorker(self.current_config(), results_root)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._analysis_progress)
        self._worker.finished.connect(self._analysis_finished)
        self._worker.failed.connect(self._analysis_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread_finished)
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setRange(0, self._plan.evaluation_count)
        self.progress.setValue(0)
        self.statusBar().showMessage("Starting analysis…")
        self._thread.start()

    @Slot()
    def cancel_analysis(self) -> None:
        if self._worker is not None:
            self._worker.cancel_requested = True
            self.cancel_button.setEnabled(False)
            self.statusBar().showMessage("Cancellation requested; restoring current comparison…")

    @Slot(int, int, str)
    def _analysis_progress(self, completed: int, total: int, label: str) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(completed)
        self.statusBar().showMessage(f"{completed}/{total}: {label}")

    @Slot(object)
    def _analysis_finished(self, summary: object) -> None:
        run_summary = cast(RunSummary, summary)
        run_directory = Path(run_summary.run_directory)
        chart_message = ""
        if run_summary.status == "completed" and self._plan is not None:
            try:
                chart = save_tornado(
                    run_directory / "results.csv",
                    self._plan.outputs[0].name,
                    run_directory / "tornado.png",
                )
                chart_message = f"\nTornado chart: {chart.name}"
            except Exception as exc:
                chart_message = f"\nChart generation warning: {exc}"
        self.results_summary.setText(
            f"Run {run_summary.status}. Completed {run_summary.completed_evaluations}/"
            f"{run_summary.expected_evaluations} evaluations. Restoration verified: "
            f"{run_summary.restoration_verified}.\nFolder: {run_directory}{chart_message}"
        )
        self.navigation.setCurrentRow(3)
        self.statusBar().showMessage(f"Analysis {run_summary.status}", 10000)

    @Slot(str)
    def _analysis_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Analysis could not start", message)
        self.statusBar().showMessage("Analysis failed", 10000)

    @Slot()
    def _thread_finished(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
