#include "mainwindow.h"
#include <QApplication>
#include <QDir>
#include <QStandardPaths>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , m_centralWidget(nullptr)
    , m_mainSplitter(nullptr)
    , m_tabWidget(nullptr)
    , m_fileTree(nullptr)
    , m_fileSystemModel(nullptr)
    , m_hierarchicalModel(nullptr)
    , m_csvTableView(nullptr)
    , m_simulationProcess(nullptr)
{
    setWindowTitle("Hydroponic CSV Editor");
    setMinimumSize(1200, 800);
    resize(1600, 1000);
    
    // Set input directory to the project's input folder
    // Try going up two levels (from build -> qt_ui -> hydroponic_python -> input)
    m_inputDirectory = QDir::currentPath() + "/../../input";
    
    if (!QDir(m_inputDirectory).exists()) {
        // Try one level up (from qt_ui -> hydroponic_python -> input)
        m_inputDirectory = QDir::currentPath() + "/../input";
        
        if (!QDir(m_inputDirectory).exists()) {
            // Try in current directory
            m_inputDirectory = QDir::currentPath() + "/input";
            
            if (!QDir(m_inputDirectory).exists()) {
                m_inputDirectory = QDir::currentPath();
            }
        }
    }
    
    setupUI();
    setupMenuBar();
    setupToolBar();
    setupStatusBar();
    connectSignals();
    
    m_statusLabel->setText("Ready");
}

MainWindow::~MainWindow()
{
    if (m_simulationProcess && m_simulationProcess->state() != QProcess::NotRunning) {
        m_simulationProcess->kill();
        m_simulationProcess->waitForFinished(3000);
    }
}

void MainWindow::setupUI()
{
    m_centralWidget = new QWidget;
    setCentralWidget(m_centralWidget);
    
    // Main splitter (horizontal: file explorer on left, tabs on right)
    m_mainSplitter = new QSplitter(Qt::Horizontal);
    
    // Create file explorer
    createFileExplorer();
    
    // Create tab widget for the main content
    m_tabWidget = new QTabWidget;
    
    // Create the different panels
    createCSVEditor();
    createBatchGenerator();
    createResultsViewer();
    createPlotViewer();
    
    // Add tabs
    m_tabWidget->addTab(m_csvEditorGroup, "📄 CSV Editor");
    m_tabWidget->addTab(m_batchGeneratorGroup, "⚙️ Batch Runner");
    m_tabWidget->addTab(m_resultsViewerGroup, "📊 Results Viewer");
    m_tabWidget->addTab(m_plotViewerGroup, "📈 Time Series Plot");
    
    // Add widgets to splitter
    m_mainSplitter->addWidget(m_fileExplorerGroup);
    m_mainSplitter->addWidget(m_tabWidget);
    
    // Set splitter proportions (file explorer: tabs = 1:3)
    m_mainSplitter->setSizes({300, 900});
    
    // Main layout
    QVBoxLayout *mainLayout = new QVBoxLayout;
    mainLayout->addWidget(m_mainSplitter);
    m_centralWidget->setLayout(mainLayout);
}

void MainWindow::createFileExplorer()
{
    m_fileExplorerGroup = new QGroupBox("Configuration Files");
    
    m_fileTree = new QTreeView;
    
    // Use hierarchical model instead of file system model
    m_hierarchicalModel = new HierarchicalFileModel(m_inputDirectory, this);
    m_fileTree->setModel(m_hierarchicalModel);
    
    // Configure tree view appearance
    m_fileTree->setAnimated(true);
    m_fileTree->setIndentation(20);
    m_fileTree->setExpandsOnDoubleClick(true);
    m_fileTree->header()->setStretchLastSection(true);
    m_fileTree->setAlternatingRowColors(true);
    
    // Expand the first level (crop types) by default
    m_fileTree->expandToDepth(0);
    
    QVBoxLayout *fileLayout = new QVBoxLayout;
    fileLayout->addWidget(m_fileTree);
    m_fileExplorerGroup->setLayout(fileLayout);
}

void MainWindow::createCSVEditor()
{
    m_csvEditorGroup = new QGroupBox("CSV Editor");
    
    // Search bar
    QHBoxLayout *searchLayout = new QHBoxLayout;
    searchLayout->addWidget(new QLabel("Search:"));
    m_searchLineEdit = new QLineEdit;
    m_searchLineEdit->setPlaceholderText("Search in table...");
    searchLayout->addWidget(m_searchLineEdit);
    searchLayout->addStretch();
    
    // Buttons
    m_addRowButton = new QPushButton("Add Row");
    m_removeRowButton = new QPushButton("Remove Row");
    m_duplicateRowButton = new QPushButton("Duplicate Row");
    m_findDuplicatesButton = new QPushButton("Find Duplicates");
    
    QHBoxLayout *buttonLayout = new QHBoxLayout;
    buttonLayout->addWidget(m_addRowButton);
    buttonLayout->addWidget(m_removeRowButton);
    buttonLayout->addWidget(m_duplicateRowButton);
    buttonLayout->addWidget(m_findDuplicatesButton);
    buttonLayout->addStretch();
    
    // CSV Table
    m_csvTableView = new CSVTableView;
    
    QVBoxLayout *csvLayout = new QVBoxLayout;
    csvLayout->addLayout(searchLayout);
    csvLayout->addLayout(buttonLayout);
    csvLayout->addWidget(m_csvTableView);
    m_csvEditorGroup->setLayout(csvLayout);
}

void MainWindow::createBatchGenerator()
{
    m_batchGeneratorGroup = new QWidget; // Changed from QGroupBox for tabs
    
    // Settings section
    QGroupBox *settingsGroup = new QGroupBox("Simulation Settings");
    QFormLayout *formLayout = new QFormLayout;
    
    m_experimentNameEdit = new QLineEdit("EXP001_2024");
    m_experimentNameEdit->setToolTip("Enter experiment identifier (e.g., EXP001_2024)");
    formLayout->addRow("Experiment Name:", m_experimentNameEdit);
    
    m_cropTypeCombo = new QComboBox;
    m_cropTypeCombo->addItems({"LET (Lettuce)", "TOM (Tomato)", "BAS (Basil)"});
    m_cropTypeCombo->setToolTip("Select crop type for simulation");
    formLayout->addRow("Crop Type:", m_cropTypeCombo);
    
    m_durationSpinBox = new QSpinBox;
    m_durationSpinBox->setRange(1, 365);
    m_durationSpinBox->setValue(90);
    m_durationSpinBox->setSuffix(" days");
    m_durationSpinBox->setToolTip("Maximum simulation duration");
    formLayout->addRow("Duration:", m_durationSpinBox);
    
    settingsGroup->setLayout(formLayout);
    
    // Batch preview section
    QGroupBox *previewGroup = new QGroupBox("Batch File Preview");
    m_batchPreview = new QTextEdit;
    m_batchPreview->setMaximumHeight(120);
    m_batchPreview->setReadOnly(true);
    m_batchPreview->setStyleSheet("font-family: monospace; background-color: #f8f8f8;");
    
    QVBoxLayout *previewLayout = new QVBoxLayout;
    previewLayout->addWidget(m_batchPreview);
    previewGroup->setLayout(previewLayout);
    
    // Action buttons
    m_generateBatchButton = new QPushButton("📄 Generate Batch File");
    m_runSimulationButton = new QPushButton("▶️ Run Simulation");
    m_runSimulationButton->setEnabled(false);
    m_runSimulationButton->setStyleSheet("QPushButton:enabled { background-color: #4CAF50; color: white; font-weight: bold; }");
    
    QHBoxLayout *batchButtonLayout = new QHBoxLayout;
    batchButtonLayout->addWidget(m_generateBatchButton);
    batchButtonLayout->addWidget(m_runSimulationButton);
    batchButtonLayout->addStretch();
    
    // Main layout with better spacing
    QVBoxLayout *batchLayout = new QVBoxLayout;
    batchLayout->setContentsMargins(10, 10, 10, 10);
    batchLayout->setSpacing(15);
    batchLayout->addWidget(settingsGroup);
    batchLayout->addWidget(previewGroup);
    batchLayout->addLayout(batchButtonLayout);
    batchLayout->addStretch(); // Push everything to top
    m_batchGeneratorGroup->setLayout(batchLayout);
}

void MainWindow::createResultsViewer()
{
    m_resultsViewerGroup = new QWidget; // Changed from QGroupBox to QWidget for tabs
    
    // Info label with better styling
    m_resultsInfoLabel = new QLabel("No results loaded. Run a simulation to see results.");
    m_resultsInfoLabel->setStyleSheet("color: gray; font-style: italic; padding: 10px; background-color: #f5f5f5; border-radius: 5px;");
    m_resultsInfoLabel->setAlignment(Qt::AlignCenter);
    
    // Results table with more space
    m_resultsTableView = new CSVTableView;
    m_resultsTableView->setAlternatingRowColors(true);
    m_resultsTableView->setSelectionBehavior(QAbstractItemView::SelectRows);
    
    // Buttons with icons and better styling
    m_refreshResultsButton = new QPushButton("🔄 Refresh Results");
    m_exportResultsButton = new QPushButton("💾 Export to CSV");
    m_exportResultsButton->setEnabled(false);
    
    QHBoxLayout *resultsButtonLayout = new QHBoxLayout;
    resultsButtonLayout->addWidget(m_refreshResultsButton);
    resultsButtonLayout->addWidget(m_exportResultsButton);
    resultsButtonLayout->addStretch();
    
    // Main layout with better spacing
    QVBoxLayout *resultsLayout = new QVBoxLayout;
    resultsLayout->setContentsMargins(10, 10, 10, 10);
    resultsLayout->setSpacing(10);
    resultsLayout->addWidget(m_resultsInfoLabel);
    resultsLayout->addWidget(m_resultsTableView, 1); // Give table maximum space
    resultsLayout->addLayout(resultsButtonLayout);
    m_resultsViewerGroup->setLayout(resultsLayout);
}

void MainWindow::createPlotViewer()
{
    m_plotViewerGroup = new QWidget;
    
    // Create the time series plot widget
    m_plotWidget = new TimeSeriesPlotWidget;
    
    // Simple layout - the plot widget handles its own layout
    QVBoxLayout *plotLayout = new QVBoxLayout;
    plotLayout->setContentsMargins(5, 5, 5, 5);
    plotLayout->addWidget(m_plotWidget);
    m_plotViewerGroup->setLayout(plotLayout);
}

void MainWindow::setupMenuBar()
{
    QMenuBar *menuBar = this->menuBar();
    
    // File Menu
    QMenu *fileMenu = menuBar->addMenu("&File");
    
    m_newAction = new QAction("&New", this);
    m_newAction->setShortcut(QKeySequence::New);
    fileMenu->addAction(m_newAction);
    
    m_openAction = new QAction("&Open", this);
    m_openAction->setShortcut(QKeySequence::Open);
    fileMenu->addAction(m_openAction);
    
    fileMenu->addSeparator();
    
    m_saveAction = new QAction("&Save", this);
    m_saveAction->setShortcut(QKeySequence::Save);
    fileMenu->addAction(m_saveAction);
    
    m_saveAsAction = new QAction("Save &As...", this);
    m_saveAsAction->setShortcut(QKeySequence::SaveAs);
    fileMenu->addAction(m_saveAsAction);
    
    fileMenu->addSeparator();
    
    m_exitAction = new QAction("E&xit", this);
    m_exitAction->setShortcut(QKeySequence::Quit);
    fileMenu->addAction(m_exitAction);
}

void MainWindow::setupToolBar()
{
    QToolBar *toolBar = addToolBar("Main Toolbar");
    toolBar->addAction(m_newAction);
    toolBar->addAction(m_openAction);
    toolBar->addAction(m_saveAction);
    toolBar->addSeparator();
}

void MainWindow::setupStatusBar()
{
    m_statusLabel = new QLabel("Ready");
    m_progressBar = new QProgressBar;
    m_progressBar->setVisible(false);
    
    statusBar()->addWidget(m_statusLabel);
    statusBar()->addPermanentWidget(m_progressBar);
}

void MainWindow::connectSignals()
{
    // Menu actions
    connect(m_newAction, &QAction::triggered, this, &MainWindow::newFile);
    connect(m_openAction, &QAction::triggered, this, &MainWindow::openFile);
    connect(m_saveAction, &QAction::triggered, this, &MainWindow::saveFile);
    connect(m_saveAsAction, &QAction::triggered, this, &MainWindow::saveAsFile);
    connect(m_exitAction, &QAction::triggered, this, &QWidget::close);
    
    // File tree
    connect(m_fileTree, &QTreeView::doubleClicked, this, &MainWindow::onFileSelected);
    
    // CSV editor buttons
    connect(m_addRowButton, &QPushButton::clicked, this, &MainWindow::addRow);
    connect(m_removeRowButton, &QPushButton::clicked, this, &MainWindow::removeRow);
    connect(m_duplicateRowButton, &QPushButton::clicked, this, &MainWindow::duplicateRow);
    connect(m_findDuplicatesButton, &QPushButton::clicked, this, &MainWindow::findDuplicates);
    
    // Search
    connect(m_searchLineEdit, &QLineEdit::textChanged, m_csvTableView, &CSVTableView::setSearchText);
    
    // Batch generator
    connect(m_generateBatchButton, &QPushButton::clicked, this, &MainWindow::generateBatchFile);
    connect(m_runSimulationButton, &QPushButton::clicked, this, &MainWindow::runSimulation);
    connect(m_experimentNameEdit, &QLineEdit::textChanged, this, &MainWindow::updateExperimentSettings);
    connect(m_cropTypeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged), this, &MainWindow::updateExperimentSettings);
    connect(m_durationSpinBox, QOverload<int>::of(&QSpinBox::valueChanged), this, &MainWindow::updateExperimentSettings);
    
    // Results viewer
    connect(m_refreshResultsButton, &QPushButton::clicked, this, &MainWindow::refreshResults);
    connect(m_exportResultsButton, &QPushButton::clicked, this, &MainWindow::exportResults);
}

void MainWindow::openFile()
{
    if (!maybeSave()) return;
    
    QString fileName = QFileDialog::getOpenFileName(
        this,
        "Open CSV File",
        m_inputDirectory,
        "CSV Files (*.csv);;All Files (*)"
    );
    
    if (!fileName.isEmpty()) {
        loadCSVFile(fileName);
    }
}

void MainWindow::saveFile()
{
    if (m_currentFile.isEmpty()) {
        saveAsFile();
    } else {
        if (m_csvTableView->csvModel()->saveToFile(m_currentFile)) {
            m_statusLabel->setText("File saved successfully");
        } else {
            QMessageBox::warning(this, "Save Error", "Could not save file.");
        }
    }
}

void MainWindow::saveAsFile()
{
    QString fileName = QFileDialog::getSaveFileName(
        this,
        "Save CSV File",
        m_inputDirectory,
        "CSV Files (*.csv);;All Files (*)"
    );
    
    if (!fileName.isEmpty()) {
        if (m_csvTableView->csvModel()->saveToFile(fileName)) {
            setCurrentFile(fileName);
            m_statusLabel->setText("File saved successfully");
        } else {
            QMessageBox::warning(this, "Save Error", "Could not save file.");
        }
    }
}

void MainWindow::newFile()
{
    if (!maybeSave()) return;
    
    m_csvTableView->csvModel()->clear();
    setCurrentFile(QString());
    m_statusLabel->setText("New file created");
}

void MainWindow::addRow()
{
    int currentRow = m_csvTableView->currentIndex().row();
    if (currentRow < 0) currentRow = m_csvTableView->csvModel()->rowCount();
    
    m_csvTableView->csvModel()->insertRow(currentRow);
    m_csvTableView->selectRow(currentRow);
}

void MainWindow::removeRow()
{
    QModelIndexList selected = m_csvTableView->selectionModel()->selectedRows();
    if (selected.isEmpty()) {
        QMessageBox::information(this, "Remove Row", "Please select a row to remove.");
        return;
    }
    
    // Remove in reverse order to maintain indices
    QList<int> rows;
    for (const QModelIndex &index : selected) {
        rows.append(index.row());
    }
    std::sort(rows.rbegin(), rows.rend());
    
    for (int row : rows) {
        m_csvTableView->csvModel()->removeRow(row);
    }
}

void MainWindow::duplicateRow()
{
    int currentRow = m_csvTableView->currentIndex().row();
    if (currentRow < 0) {
        QMessageBox::information(this, "Duplicate Row", "Please select a row to duplicate.");
        return;
    }
    
    m_csvTableView->csvModel()->duplicateRow(currentRow);
    m_csvTableView->selectRow(currentRow + 1);
}

void MainWindow::findDuplicates()
{
    QStringList duplicates = m_csvTableView->csvModel()->findDuplicateRows();
    showDuplicates(duplicates);
}

void MainWindow::generateBatchFile()
{
    QString experimentName = m_experimentNameEdit->text();
    QString cropTypeText = m_cropTypeCombo->currentText();
    QString cropType = cropTypeText.split(" ").first(); // Extract "LET" from "LET (Lettuce)"
    int duration = m_durationSpinBox->value();
    
    if (experimentName.isEmpty()) {
        QMessageBox::warning(this, "Generate Batch", "Please enter an experiment name.");
        return;
    }
    
    // Generate batch file content
    QString batchContent;
#ifdef Q_OS_WIN
    batchContent = QString(
        "@echo off\n"
        "echo Running Hydroponic Simulation...\n"
        "echo Experiment: %1\n"
        "echo Crop Type: %2\n"
        "echo Duration: %3 days\n"
        "echo.\n"
        "cd /d \"%~dp0\"\n"
        "python cropgro_cli.py --experiment %2_%1 --days %3 --output-csv outputs/%2_%1_results.csv\n"
        "if %ERRORLEVEL% EQU 0 (\n"
        "    echo Simulation completed successfully!\n"
        ") else (\n"
        "    echo Simulation failed with error code %ERRORLEVEL%\n"
        ")\n"
        "pause\n"
    ).arg(experimentName, cropType, QString::number(duration));
#else
    batchContent = QString(
        "#!/bin/bash\n"
        "echo \"Running Hydroponic Simulation...\"\n"
        "echo \"Experiment: %1\"\n"
        "echo \"Crop Type: %2\"\n"
        "echo \"Duration: %3 days\"\n"
        "echo\n"
        "cd \"$(dirname \"$0\")\"\n"
        "python3 cropgro_cli.py --experiment %2_%1 --days %3 --output-csv outputs/%2_%1_results.csv\n"
        "if [ $? -eq 0 ]; then\n"
        "    echo \"Simulation completed successfully!\"\n"
        "else\n"
        "    echo \"Simulation failed with error code $?\"\n"
        "fi\n"
        "read -p \"Press Enter to continue...\"\n"
    ).arg(experimentName, cropType, QString::number(duration));
#endif
    
    m_batchPreview->setPlainText(batchContent);
    
    // Save batch file
    QString batchFileName;
#ifdef Q_OS_WIN
    batchFileName = QString("run_simulation_%1_%2.bat").arg(cropType, experimentName);
#else
    batchFileName = QString("run_simulation_%1_%2.sh").arg(cropType, experimentName);
#endif
    
    QString batchPath = QDir::currentPath() + "/" + batchFileName;
    QFile batchFile(batchPath);
    if (batchFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QTextStream out(&batchFile);
        out << batchContent;
        batchFile.close();
        
#ifndef Q_OS_WIN
        // Make script executable on Unix systems
        batchFile.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner |
                                QFileDevice::ReadGroup | QFileDevice::ExeGroup |
                                QFileDevice::ReadOther | QFileDevice::ExeOther);
#endif
        
        m_runSimulationButton->setEnabled(true);
        m_statusLabel->setText(QString("Batch file created: %1").arg(batchFileName));
    } else {
        QMessageBox::warning(this, "Generate Batch", "Could not create batch file.");
    }
}

void MainWindow::runSimulation()
{
    if (m_simulationProcess && m_simulationProcess->state() != QProcess::NotRunning) {
        QMessageBox::information(this, "Simulation", "A simulation is already running.");
        return;
    }
    
    QString experimentName = m_experimentNameEdit->text();
    QString cropTypeText = m_cropTypeCombo->currentText();
    QString cropType = cropTypeText.split(" ").first(); // Extract "LET" from "LET (Lettuce)"
    
    m_simulationProcess = new QProcess(this);
    connect(m_simulationProcess, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &MainWindow::onSimulationFinished);
    
    QString fullExperimentName = QString("%1_%2").arg(cropType, experimentName);
    QString outputFileName = QString("outputs/%1_results.csv").arg(fullExperimentName);
    QString dailyOutputFileName = QString("outputs/%1_daily_results.csv").arg(fullExperimentName);
    
    QStringList arguments;
    arguments << "cropgro_cli.py";
    arguments << "--cultivar" << fullExperimentName;
    arguments << "--days" << QString::number(m_durationSpinBox->value());
    arguments << "--output-csv" << outputFileName;  // Generate experiment-specific daily CSV
    
    // Store expected output filenames for results loading
    m_resultsFile = QDir::currentPath() + "/" + outputFileName;
    
    m_progressBar->setVisible(true);
    m_progressBar->setRange(0, 0); // Indeterminate progress
    m_statusLabel->setText("Running simulation...");
    m_runSimulationButton->setEnabled(false);
    
    m_simulationProcess->setWorkingDirectory(QDir::currentPath() + "/..");
    m_simulationProcess->start("python3", arguments);
    
    if (!m_simulationProcess->waitForStarted()) {
        // Try python instead of python3
        m_simulationProcess->start("python", arguments);
    }
}

void MainWindow::onFileSelected(const QModelIndex &index)
{
    if (m_hierarchicalModel && m_hierarchicalModel->isFile(index)) {
        QString filePath = m_hierarchicalModel->getFilePath(index);
        if (!filePath.isEmpty() && filePath.endsWith(".csv", Qt::CaseInsensitive)) {
            if (maybeSave()) {
                loadCSVFile(filePath);
                // Switch to CSV Editor tab
                m_tabWidget->setCurrentIndex(0);
            }
        }
    }
}

void MainWindow::onSimulationFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    m_progressBar->setVisible(false);
    m_runSimulationButton->setEnabled(true);
    
    if (exitStatus == QProcess::NormalExit && exitCode == 0) {
        m_statusLabel->setText("Simulation completed successfully!");
        QMessageBox::information(this, "Simulation", "Simulation completed successfully!");
        
        // Automatically load the results and switch to plot tab
        findLatestResults();
        m_tabWidget->setCurrentIndex(3); // Switch to Time Series Plot tab
    } else {
        m_statusLabel->setText("Simulation failed!");
        QMessageBox::warning(this, "Simulation", 
            QString("Simulation failed with exit code %1").arg(exitCode));
    }
    
    if (m_simulationProcess) {
        m_simulationProcess->deleteLater();
        m_simulationProcess = nullptr;
    }
}

void MainWindow::updateExperimentSettings()
{
    // Update batch preview when settings change
    m_runSimulationButton->setEnabled(false);
    m_batchPreview->clear();
}

void MainWindow::loadCSVFile(const QString &fileName)
{
    if (m_csvTableView->csvModel()->loadFromFile(fileName)) {
        setCurrentFile(fileName);
        m_statusLabel->setText(QString("Loaded: %1").arg(QFileInfo(fileName).fileName()));
    } else {
        QMessageBox::warning(this, "Open Error", "Could not open file.");
    }
}

void MainWindow::setCurrentFile(const QString &fileName)
{
    m_currentFile = fileName;
    updateWindowTitle();
}

void MainWindow::updateWindowTitle()
{
    QString title = "Hydroponic CSV Editor";
    if (!m_currentFile.isEmpty()) {
        title += " - " + QFileInfo(m_currentFile).fileName();
    }
    setWindowTitle(title);
}

bool MainWindow::maybeSave()
{
    // For now, just return true. You could add unsaved changes detection here
    return true;
}

void MainWindow::showDuplicates(const QStringList &duplicates)
{
    if (duplicates.isEmpty()) {
        QMessageBox::information(this, "Find Duplicates", "No duplicate rows found.");
    } else {
        QString message = QString("Found %1 duplicate row(s):\n\n%2")
                         .arg(duplicates.count())
                         .arg(duplicates.join("\n"));
        QMessageBox::information(this, "Find Duplicates", message);
    }
}

void MainWindow::loadResultsFile(const QString &fileName)
{
    if (m_resultsTableView->csvModel()->loadFromFile(fileName)) {
        m_resultsFile = fileName;
        m_exportResultsButton->setEnabled(true);
        
        QFileInfo fileInfo(fileName);
        int rows = m_resultsTableView->csvModel()->rowCount();
        int cols = m_resultsTableView->csvModel()->columnCount();
        
        m_resultsInfoLabel->setText(QString("Results loaded: %1 (%2 rows, %3 columns)")
                                   .arg(fileInfo.fileName())
                                   .arg(rows)
                                   .arg(cols));
        m_resultsInfoLabel->setStyleSheet("color: green; font-weight: bold;");
        
        // Load data into plot widget
        if (m_plotWidget) {
            m_plotWidget->loadDataFromModel(m_resultsTableView->csvModel());
        }
        
        m_statusLabel->setText(QString("Results loaded: %1").arg(fileInfo.fileName()));
    } else {
        QMessageBox::warning(this, "Load Results", "Could not load results file.");
    }
}

void MainWindow::findLatestResults()
{
    // First, try to find experiment-specific results file if we have one stored
    if (!m_resultsFile.isEmpty() && QFile::exists(m_resultsFile)) {
        loadResultsFile(m_resultsFile);
        return;
    }
    
    // Generate expected filename based on current settings
    QString experimentName = m_experimentNameEdit->text();
    QString cropTypeText = m_cropTypeCombo->currentText();
    QString cropType = cropTypeText.split(" ").first();
    QString fullExperimentName = QString("%1_%2").arg(cropType, experimentName);
    
    // Look for experiment-specific results in outputs directory first
    QDir outputsDir(QDir::currentPath() + "/../outputs");
    if (outputsDir.exists()) {
        // Try exact experiment match first
        QString experimentResultsPath = outputsDir.filePath(QString("%1_results.csv").arg(fullExperimentName));
        if (QFile::exists(experimentResultsPath)) {
            loadResultsFile(experimentResultsPath);
            return;
        }
        
        // Look for any files matching the experiment name pattern
        QStringList filters;
        filters << QString("%1_results*.csv").arg(fullExperimentName);
        filters << QString("%1_daily_results*.csv").arg(fullExperimentName);
        filters << "*.csv";  // Fallback to any CSV
        QFileInfoList files = outputsDir.entryInfoList(filters, QDir::Files, QDir::Time);
        
        if (!files.isEmpty()) {
            // Load the most recent file
            loadResultsFile(files.first().absoluteFilePath());
            return;
        }
    }
    
    // Try experiment-specific files in main directory as fallback
    QString experimentResultsPath = QDir::currentPath() + "/../" + fullExperimentName + "_results.csv";
    if (QFile::exists(experimentResultsPath)) {
        loadResultsFile(experimentResultsPath);
        return;
    }
    
    // Try generic simulation_results.csv as final fallback
    QString genericResultsPath = QDir::currentPath() + "/../simulation_results.csv";
    if (QFile::exists(genericResultsPath)) {
        loadResultsFile(genericResultsPath);
        return;
    }
    
    // No results found
    m_resultsInfoLabel->setText("No results found. Run a simulation to generate results.");
    m_resultsInfoLabel->setStyleSheet("color: gray; font-style: italic;");
    m_exportResultsButton->setEnabled(false);
}

void MainWindow::exportResults()
{
    if (m_resultsFile.isEmpty()) {
        QMessageBox::information(this, "Export Results", "No results to export.");
        return;
    }
    
    QString fileName = QFileDialog::getSaveFileName(
        this,
        "Export Results",
        QDir::currentPath(),
        "CSV Files (*.csv);;All Files (*)"
    );
    
    if (!fileName.isEmpty()) {
        if (m_resultsTableView->csvModel()->saveToFile(fileName)) {
            QMessageBox::information(this, "Export Results", "Results exported successfully!");
        } else {
            QMessageBox::warning(this, "Export Results", "Could not export results.");
        }
    }
}

void MainWindow::refreshResults()
{
    findLatestResults();
}