#include "mainwindow.h"
#include <QApplication>
#include <QDir>
#include <QStandardPaths>
#include <QRegularExpression>
#include <QScrollArea>
#include <QGroupBox>
#include <functional>
#include <algorithm>

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
    
    // Initialize treatment preview
    updateTreatmentPreview();
    
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
    
    // Treatment selection group for factorial experiments
    m_treatmentSelectionGroup = new QWidget;
    QVBoxLayout *treatmentMainLayout = new QVBoxLayout(m_treatmentSelectionGroup);
    
    QLabel *treatmentLabel = new QLabel("🧪 Experimental Treatments:");
    treatmentLabel->setStyleSheet("font-weight: bold; color: #2E8B57;");
    treatmentMainLayout->addWidget(treatmentLabel);
    
    // Create scrollable area for treatments
    m_treatmentScrollArea = new QScrollArea;
    m_treatmentScrollArea->setMaximumHeight(200);
    m_treatmentScrollArea->setWidgetResizable(true);
    m_treatmentScrollArea->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    
    QWidget *treatmentWidget = new QWidget;
    m_treatmentLayout = new QVBoxLayout(treatmentWidget);
    
    // Create treatment categories
    createTreatmentCategory("🌱 Varieties", {"EXP001_2024", "EXP002_2024", "EXP003_2024"}, {"EXP001_2024"});
    createTreatmentCategory("🌡️ Temperature (°C)", {"20", "23", "26", "29"}, {"23"});
    createTreatmentCategory("💧 Nitrogen (mg/L)", {"150", "200", "250", "300"}, {"200"});
    createTreatmentCategory("🔬 pH Levels", {"5.5", "6.0", "6.5", "7.0"}, {"6.0"});
    createTreatmentCategory("💡 Light Hours", {"12", "14", "16", "18"}, {"16"});
    createTreatmentCategory("💨 CO2 (ppm)", {"400", "800", "1200", "1600"}, {"1200"});
    createTreatmentCategory("🧪 EC (dS/m)", {"1.2", "1.5", "1.8", "2.1"}, {"1.5"});
    
    m_treatmentScrollArea->setWidget(treatmentWidget);
    treatmentMainLayout->addWidget(m_treatmentScrollArea);
    
    // Add treatment combination info
    QLabel *infoLabel = new QLabel("💡 Select treatments to create factorial combinations");
    infoLabel->setStyleSheet("color: #666; font-size: 11px; font-style: italic;");
    treatmentMainLayout->addWidget(infoLabel);
    
    formLayout->addRow("Treatments:", m_treatmentSelectionGroup);
    
    m_durationSpinBox = new QSpinBox;
    m_durationSpinBox->setRange(1, 365);
    m_durationSpinBox->setValue(90);
    m_durationSpinBox->setSuffix(" days");
    m_durationSpinBox->setToolTip("Maximum simulation duration");
    formLayout->addRow("Duration:", m_durationSpinBox);
    
    settingsGroup->setLayout(formLayout);
    
    // Treatment combinations preview
    QGroupBox *combinationsGroup = new QGroupBox("📋 Treatment Combinations");
    QTextEdit *combinationsPreview = new QTextEdit;
    combinationsPreview->setMaximumHeight(100);
    combinationsPreview->setReadOnly(true);
    combinationsPreview->setObjectName("combinationsPreview");
    combinationsPreview->setStyleSheet("font-family: monospace; background-color: #f0f8ff; border: 1px solid #4169E1;");
    combinationsPreview->setPlainText("Select treatments to see combinations...");
    
    QVBoxLayout *combinationsLayout = new QVBoxLayout;
    combinationsLayout->addWidget(combinationsPreview);
    combinationsGroup->setLayout(combinationsLayout);
    
    // Batch preview section
    QGroupBox *previewGroup = new QGroupBox("📄 Batch File Preview");
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
    batchLayout->addWidget(combinationsGroup);
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
    
    QPushButton *loadMultipleButton = new QPushButton("📊 Load All Treatments");
    loadMultipleButton->setToolTip("Load and compare all treatment results");
    connect(loadMultipleButton, &QPushButton::clicked, this, &MainWindow::loadMultipleTreatmentResults);
    
    QHBoxLayout *resultsButtonLayout = new QHBoxLayout;
    resultsButtonLayout->addWidget(m_refreshResultsButton);
    resultsButtonLayout->addWidget(m_exportResultsButton);
    resultsButtonLayout->addWidget(loadMultipleButton);
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

void MainWindow::createTreatmentCategory(const QString &categoryName, const QStringList &options, const QStringList &defaults)
{
    // Create group box for this treatment category
    QGroupBox *categoryGroup = new QGroupBox(categoryName);
    categoryGroup->setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; }");
    
    // Create horizontal layout for checkboxes
    QHBoxLayout *categoryLayout = new QHBoxLayout(categoryGroup);
    categoryLayout->setSpacing(10);
    
    // Add checkboxes for each option
    for (const QString &option : options) {
        QCheckBox *optionCheck = new QCheckBox(option);
        QString cleanCategory = categoryName.split(" ").first();
        cleanCategory.remove(QRegularExpression("[^A-Za-z]"));
        optionCheck->setObjectName(QString("%1_%2").arg(cleanCategory, option));
        
        // Set default selections
        if (defaults.contains(option)) {
            optionCheck->setChecked(true);
        }
        
        // Add tooltip with treatment information
        QString tooltip = QString("Include %1 = %2 in experimental design").arg(categoryName, option);
        optionCheck->setToolTip(tooltip);
        
        // Connect to update preview when changed
        connect(optionCheck, &QCheckBox::toggled, this, &MainWindow::updateTreatmentPreview);
        
        categoryLayout->addWidget(optionCheck);
    }
    
    categoryLayout->addStretch();
    m_treatmentLayout->addWidget(categoryGroup);
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
    
    // Get selected treatment combinations
    QStringList combinations = generateTreatmentCombinations();
    if (combinations.isEmpty()) {
        QMessageBox::warning(this, "Generate Batch", "No treatment combinations selected.");
        return;
    }
    
    // Clean up old batch files before creating new ones
    QDir currentDir(QDir::currentPath());
    QStringList batchFilters;
#ifdef Q_OS_WIN
    batchFilters << "run_simulation_*.bat";
#else
    batchFilters << "run_simulation_*.sh";
#endif
    
    QFileInfoList oldBatchFiles = currentDir.entryInfoList(batchFilters, QDir::Files);
    int deletedCount = 0;
    for (const QFileInfo &fileInfo : oldBatchFiles) {
        if (QFile::remove(fileInfo.absoluteFilePath())) {
            deletedCount++;
            qDebug() << "MainWindow: Deleted old batch file:" << fileInfo.fileName();
        } else {
            qDebug() << "MainWindow: Failed to delete old batch file:" << fileInfo.fileName();
        }
    }
    
    if (deletedCount > 0) {
        qDebug() << "MainWindow: Cleaned up" << deletedCount << "old batch files";
        m_statusLabel->setText(QString("Cleaned up %1 old batch file(s)").arg(deletedCount));
    }
    
    // Generate batch file content for multiple treatment combinations
    QString batchContent;
    QString singleOutputFile = QString("outputs/%1_%2_combined_results.csv").arg(cropType, experimentName);
    
#ifdef Q_OS_WIN
    batchContent = "@echo off\n"
                  "echo Running Multi-Treatment Hydroponic Experiment...\n"
                  "echo Base Experiment: " + experimentName + "\n"
                  "echo Crop Type: " + cropType + "\n"
                  "echo Duration: " + QString::number(duration) + " days\n"
                  "echo Total Treatments: " + QString::number(combinations.size()) + "\n"
                  "echo Output File: " + singleOutputFile + "\n"
                  "echo.\n"
                  "cd /d \"%~dp0\"\n\n";
    
    // Create temporary directory for individual treatment files
    batchContent += "if not exist temp_treatments mkdir temp_treatments\n\n";
    
    for (int i = 0; i < combinations.size(); ++i) {
        QString combo = combinations[i];
        QString treatmentId = QString("T%1").arg(i + 1, 2, 10, QChar('0'));
        QString tempOutputFile = QString("temp_treatments/treatment_%1.csv").arg(treatmentId);
        
        // Simple approach: run same simulation with different treatment IDs
        batchContent += QString(
            "echo [%1/%2] Running Treatment %8: %3\n"
            "python cropgro_cli.py --cultivar %4_%5 --days %6 --treatment-id %8 --output-csv %7\n"
            "if %ERRORLEVEL% NEQ 0 (\n"
            "    echo Treatment %8 failed!\n"
            "    pause\n"
            "    exit /b 1\n"
            ")\n"
            "echo Treatment %8 completed successfully!\n"
            "echo.\n\n"
        ).arg(QString::number(i + 1), QString::number(combinations.size()), combo, cropType, experimentName, QString::number(duration), tempOutputFile, treatmentId);
    }
    
    // Combine all treatment files into single CSV with Treatment_ID column
    batchContent += "echo Combining all treatments into single CSV file...\n";
    batchContent += "echo Date,Day,System_ID,Crop_ID,Treatment_ID";
    
    // Add headers from first treatment file (excluding Date, Day, System_ID, Crop_ID which are already added)
    batchContent += ",ETO_Ref_mm,ETC_Prime_mm,Transpiration_mm,Water_Total_L,Tank_Volume_L,Temp_C,Solar_Rad_MJ,VPD_kPa,WUE_kg_m3,pH,EC,RZT_C,RZT_Growth_Factor,RZT_Nutrient_Factor,V_Stage,Leaf_Number,Leaf_Area_m2,Avg_Leaf_Area_cm2,CO2_umol_mol,VPD_Actual_kPa,Env_Photo_Factor,Env_Transp_Factor,N-NO3_mg_L,P-PO4_mg_L,K_mg_L,Ca_mg_L,Mg_mg_L,LAI,Growth_Stage,Total_Biomass_g,Integrated_Stress,Temperature_Stress,Water_Stress,Nutrient_Stress,Nitrogen_Stress,Salinity_Stress > " + singleOutputFile + "\n";
    
    // Combine all treatment files
    batchContent += "for %%f in (temp_treatments\\treatment_*.csv) do (\n";
    batchContent += "    for /f \"skip=1 tokens=1-4,* delims=,\" %%a in (%%f) do (\n";
    batchContent += "        echo %%a,%%b,%%c,%%d," + QString("%1_%2").arg(cropType, experimentName) + "_%%~nf,%%e >> " + singleOutputFile + "\n";
    batchContent += "    )\n";
    batchContent += ")\n\n";
    
    // Clean up temporary files
    batchContent += "echo Cleaning up temporary files...\n";
    batchContent += "rmdir /s /q temp_treatments\n\n";
    
    batchContent += "echo All treatments completed and combined successfully!\n";
    batchContent += "echo Combined results saved to: " + singleOutputFile + "\n";
    batchContent += "pause\n";
#else
    batchContent = "#!/bin/bash\n"
                  "echo \"Running Multi-Treatment Hydroponic Experiment...\"\n"
                  "echo \"Base Experiment: " + experimentName + "\"\n"
                  "echo \"Crop Type: " + cropType + "\"\n"
                  "echo \"Duration: " + QString::number(duration) + " days\"\n"
                  "echo \"Total Treatments: " + QString::number(combinations.size()) + "\"\n"
                  "echo \"Output File: " + singleOutputFile + "\"\n"
                  "echo\n"
                  "cd \"$(dirname \"$0\")\"\n\n";
    
    // Create temporary directory for individual treatment files
    batchContent += "mkdir -p temp_treatments\n\n";
    
    for (int i = 0; i < combinations.size(); ++i) {
        QString combo = combinations[i];
        QString treatmentId = QString("T%1").arg(i + 1, 2, 10, QChar('0'));
        QString tempOutputFile = QString("temp_treatments/treatment_%1.csv").arg(treatmentId);
        
        // Simple approach: run same simulation with different treatment IDs
        batchContent += QString(
            "echo \"[%1/%2] Running Treatment %8: %3\"\n"
            "python3 cropgro_cli.py --cultivar %4_%5 --days %6 --treatment-id %8 --output-csv %7\n"
            "if [ $? -ne 0 ]; then\n"
            "    echo \"Treatment %8 failed!\"\n"
            "    read -p \"Press Enter to continue...\"\n"
            "    exit 1\n"
            "fi\n"
            "echo \"Treatment %8 completed successfully!\"\n"
            "echo\n\n"
        ).arg(QString::number(i + 1), QString::number(combinations.size()), combo, cropType, experimentName, QString::number(duration), tempOutputFile, treatmentId);
    }
    
    // Combine all treatment files into single CSV with Treatment_ID column
    batchContent += "echo \"Combining all treatments into single CSV file...\"\n";
    batchContent += "echo \"Date,Day,System_ID,Crop_ID,Treatment_ID,ETO_Ref_mm,ETC_Prime_mm,Transpiration_mm,Water_Total_L,Tank_Volume_L,Temp_C,Solar_Rad_MJ,VPD_kPa,WUE_kg_m3,pH,EC,RZT_C,RZT_Growth_Factor,RZT_Nutrient_Factor,V_Stage,Leaf_Number,Leaf_Area_m2,Avg_Leaf_Area_cm2,CO2_umol_mol,VPD_Actual_kPa,Env_Photo_Factor,Env_Transp_Factor,N-NO3_mg_L,P-PO4_mg_L,K_mg_L,Ca_mg_L,Mg_mg_L,LAI,Growth_Stage,Total_Biomass_g,Integrated_Stress,Temperature_Stress,Water_Stress,Nutrient_Stress,Nitrogen_Stress,Salinity_Stress\" > " + singleOutputFile + "\n";
    
    // Combine all treatment files
    batchContent += "for file in temp_treatments/treatment_*.csv; do\n";
    batchContent += "    treatment_id=$(basename \"$file\" .csv | sed 's/treatment_//')\n";
    batchContent += "    tail -n +2 \"$file\" | while IFS=, read -r date day system_id crop_id rest; do\n";
    batchContent += "        echo \"$date,$day,$system_id,$crop_id," + QString("%1_%2").arg(cropType, experimentName) + "_${treatment_id},$rest\" >> " + singleOutputFile + "\n";
    batchContent += "    done\n";
    batchContent += "done\n\n";
    
    // Clean up temporary files
    batchContent += "echo \"Cleaning up temporary files...\"\n";
    batchContent += "rm -rf temp_treatments\n\n";
    
    batchContent += "echo \"All treatments completed and combined successfully!\"\n";
    batchContent += "echo \"Combined results saved to: " + singleOutputFile + "\"\n";
    batchContent += "read -p \"Press Enter to continue...\"\n";
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
    
    // Set working directory to the hydroponic_python root
    QString workingDir = QDir::currentPath();
    // If we're in qt_ui/build, go up two levels to reach hydroponic_python
    if (workingDir.endsWith("/qt_ui/build")) {
        workingDir = QDir::currentPath() + "/../..";
    } else if (workingDir.endsWith("/qt_ui")) {
        workingDir = QDir::currentPath() + "/..";
    } else {
        workingDir = QDir::currentPath() + "/..";
    }
    
    QStringList arguments;
    arguments << "cropgro_cli.py";
    arguments << "--cultivar" << fullExperimentName;
    arguments << "--days" << QString::number(m_durationSpinBox->value());
    arguments << "--output-csv" << outputFileName;  // Generate experiment-specific daily CSV
    
    qDebug() << "MainWindow: Executing simulation command:";
    qDebug() << "MainWindow: Working directory:" << workingDir;
    qDebug() << "MainWindow: Command: python3" << arguments.join(" ");
    
    // Store expected output filenames for results loading
    m_resultsFile = workingDir + "/" + outputFileName;
    
    m_progressBar->setVisible(true);
    m_progressBar->setRange(0, 0); // Indeterminate progress
    m_statusLabel->setText("Running simulation...");
    m_runSimulationButton->setEnabled(false);
    
    qDebug() << "MainWindow: Setting working directory to:" << workingDir;
    m_simulationProcess->setWorkingDirectory(workingDir);
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
        QString errorOutput = "";
        if (m_simulationProcess) {
            errorOutput = m_simulationProcess->readAllStandardError();
            qDebug() << "MainWindow: Simulation stderr:" << errorOutput;
            qDebug() << "MainWindow: Simulation stdout:" << m_simulationProcess->readAllStandardOutput();
        }
        
        m_statusLabel->setText("Simulation failed!");
        QString errorMessage = QString("Simulation failed with exit code %1").arg(exitCode);
        if (!errorOutput.isEmpty()) {
            errorMessage += QString("\n\nError details:\n%1").arg(errorOutput);
        }
        QMessageBox::warning(this, "Simulation", errorMessage);
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
        // Try combined results file first (for multi-treatment experiments)
        QString combinedResultsPath = outputsDir.filePath(QString("%1_combined_results.csv").arg(fullExperimentName));
        if (QFile::exists(combinedResultsPath)) {
            loadResultsFile(combinedResultsPath);
            return;
        }
        
        // Try exact experiment match (single treatment)
        QString experimentResultsPath = outputsDir.filePath(QString("%1_results.csv").arg(fullExperimentName));
        if (QFile::exists(experimentResultsPath)) {
            loadResultsFile(experimentResultsPath);
            return;
        }
        
        // Look for any files matching the experiment name pattern
        QStringList filters;
        filters << QString("%1_combined_results.csv").arg(fullExperimentName);
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

QMap<QString, QStringList> MainWindow::getSelectedTreatments() const
{
    QMap<QString, QStringList> treatments;
    
    // Find all checkboxes in the treatment layout
    QList<QCheckBox*> checkboxes = m_treatmentSelectionGroup->findChildren<QCheckBox*>();
    
    for (QCheckBox *checkbox : checkboxes) {
        if (checkbox->isChecked()) {
            QString objectName = checkbox->objectName();
            QStringList parts = objectName.split("_");
            if (parts.size() >= 2) {
                QString category = parts[0];
                QString value = parts.mid(1).join("_");
                treatments[category].append(value);
            }
        }
    }
    
    return treatments;
}

QStringList MainWindow::generateTreatmentCombinations() const
{
    QMap<QString, QStringList> treatments = getSelectedTreatments();
    QStringList combinations;
    
    if (treatments.isEmpty()) {
        return combinations;
    }
    
    // Generate all possible combinations (factorial design)
    QStringList categories = treatments.keys();
    QList<QStringList> allValues;
    
    for (const QString &category : categories) {
        allValues.append(treatments[category]);
    }
    
    // Recursive combination generation
    std::function<void(int, QStringList)> generateCombos = [&](int categoryIndex, QStringList currentCombo) {
        if (categoryIndex >= categories.size()) {
            QString comboStr;
            for (int i = 0; i < categories.size(); ++i) {
                if (!comboStr.isEmpty()) comboStr += "_";
                comboStr += QString("%1:%2").arg(categories[i], currentCombo[i]);
            }
            combinations.append(comboStr);
            return;
        }
        
        for (const QString &value : allValues[categoryIndex]) {
            QStringList newCombo = currentCombo;
            newCombo.append(value);
            generateCombos(categoryIndex + 1, newCombo);
        }
    };
    
    generateCombos(0, QStringList());
    return combinations;
}

QStringList MainWindow::parseTreatmentCombination(const QString &combo) const
{
    QStringList cliParams;
    
    // Parse the combination string like "Varieties:EXP001_2024_Temperature:23_Nitrogen:200_pH:6.0_Light:16_CO2:1200_EC:1.5"
    QStringList parts = combo.split("_");
    
    for (const QString &part : parts) {
        if (part.contains(":")) {
            QStringList keyValue = part.split(":");
            if (keyValue.size() == 2) {
                QString category = keyValue[0].toLower();
                QString value = keyValue[1];
                
                // Map treatment categories to CLI parameters
                if (category == "temperature") {
                    cliParams << QString("--temperature %1").arg(value);
                } else if (category == "nitrogen") {
                    cliParams << QString("--nitrogen %1").arg(value);
                } else if (category == "ph") {
                    cliParams << QString("--ph %1").arg(value);
                } else if (category == "light") {
                    cliParams << QString("--light-hours %1").arg(value);
                } else if (category == "co2") {
                    cliParams << QString("--co2 %1").arg(value);
                } else if (category == "ec") {
                    cliParams << QString("--ec %1").arg(value);
                }
                // Skip varieties as they're handled differently
            }
        }
    }
    
    return cliParams;
}

void MainWindow::updateTreatmentPreview()
{
    QStringList combinations = generateTreatmentCombinations();
    QTextEdit *preview = m_batchGeneratorGroup->findChild<QTextEdit*>("combinationsPreview");
    
    if (preview) {
        if (combinations.isEmpty()) {
            preview->setPlainText("No treatments selected. Choose treatment levels to see combinations.");
        } else {
            QString previewText = QString("🧪 %1 Treatment Combinations:\n\n").arg(combinations.size());
            for (int i = 0; i < std::min(static_cast<int>(combinations.size()), 10); ++i) {
                previewText += QString("%1. %2\n").arg(i + 1).arg(combinations[i].replace("_", " | "));
            }
            if (combinations.size() > 10) {
                previewText += QString("... and %1 more combinations").arg(combinations.size() - 10);
            }
            preview->setPlainText(previewText);
        }
    }
}

QStringList MainWindow::getSelectedVarieties() const
{
    QStringList varieties;
    QMap<QString, QStringList> treatments = getSelectedTreatments();
    if (treatments.contains("Varieties")) {
        varieties = treatments["Varieties"];
    }
    return varieties;
}

void MainWindow::runMultiVarietySimulation()
{
    // Future implementation for running multiple treatment combinations
    QStringList combinations = generateTreatmentCombinations();
    
    if (combinations.isEmpty()) {
        QMessageBox::warning(this, "Multi-Treatment Simulation", 
                           "No treatment combinations selected. Please select treatments first.");
        return;
    }
    
    // For now, show info about what would be run
    QString message = QString("Would run %1 treatment combinations:\n\n").arg(combinations.size());
    for (int i = 0; i < std::min(5, static_cast<int>(combinations.size())); ++i) {
        message += QString("• %1\n").arg(combinations[i].replace("_", " | "));
    }
    if (combinations.size() > 5) {
        message += QString("... and %1 more\n").arg(combinations.size() - 5);
    }
    message += "\nThis feature will be fully implemented to run all combinations automatically.";
    
    QMessageBox::information(this, "Multi-Treatment Simulation", message);
}

QStringList MainWindow::findTreatmentResultFiles() const
{
    QStringList resultFiles;
    QString experimentName = m_experimentNameEdit->text();
    QString cropTypeText = m_cropTypeCombo->currentText();
    QString cropType = cropTypeText.split(" ").first();
    
    // Look for combined results file first (new format)
    QDir outputsDir(QDir::currentPath() + "/../outputs");
    if (outputsDir.exists()) {
        QString combinedFile = outputsDir.filePath(QString("%1_%2_combined_results.csv").arg(cropType, experimentName));
        if (QFile::exists(combinedFile)) {
            resultFiles.append(combinedFile);
            return resultFiles;
        }
        
        // Fallback to individual treatment files (old format)
        QStringList filters;
        filters << QString("%1_%2_T*_results.csv").arg(cropType, experimentName);
        
        QFileInfoList files = outputsDir.entryInfoList(filters, QDir::Files, QDir::Time);
        for (const QFileInfo &fileInfo : files) {
            resultFiles.append(fileInfo.absoluteFilePath());
        }
    }
    
    return resultFiles;
}

void MainWindow::loadMultipleTreatmentResults()
{
    QStringList treatmentFiles = findTreatmentResultFiles();
    
    if (treatmentFiles.isEmpty()) {
        QMessageBox::information(this, "Load Multiple Treatments", 
                               "No treatment result files found. Run multi-treatment experiments first.");
        return;
    }
    
    // Check if we have a combined file (new format)
    if (treatmentFiles.size() == 1 && treatmentFiles[0].contains("combined_results")) {
        // Load the combined file directly
        loadResultsFile(treatmentFiles[0]);
        m_resultsInfoLabel->setText("Combined treatment results loaded (new format)");
        m_resultsInfoLabel->setStyleSheet("color: green; font-weight: bold;");
        m_tabWidget->setCurrentIndex(3);
        return;
    }
    
    // Handle old format (multiple individual files)
    QString combinedData;
    bool isFirstFile = true;
    QString headers;
    
    for (const QString &filePath : treatmentFiles) {
        QFileInfo fileInfo(filePath);
        QString treatmentId = fileInfo.baseName().split("_").last().remove("results");
        
        QFile file(filePath);
        if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
            QTextStream in(&file);
            QString content = in.readAll();
            QStringList lines = content.split('\n', Qt::SkipEmptyParts);
            
            if (isFirstFile) {
                // Add Treatment_ID column to headers
                headers = lines[0] + ",Treatment_ID\n";
                combinedData += headers;
                isFirstFile = false;
            }
            
            // Add data rows with treatment ID
            for (int i = 1; i < lines.size(); ++i) {
                if (!lines[i].trimmed().isEmpty()) {
                    combinedData += lines[i] + "," + treatmentId + "\n";
                }
            }
        }
    }
    
    // Save combined file temporarily and load it
    QString tempFile = QDir::tempPath() + "/combined_treatments.csv";
    QFile outFile(tempFile);
    if (outFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QTextStream out(&outFile);
        out << combinedData;
        outFile.close();
        
        // Load the combined file
        loadResultsFile(tempFile);
        
        m_resultsInfoLabel->setText(QString("Combined %1 treatment results loaded (legacy format)").arg(treatmentFiles.size()));
        m_resultsInfoLabel->setStyleSheet("color: blue; font-weight: bold;");
        
        // Switch to plot tab to show comparison
        m_tabWidget->setCurrentIndex(3);
    }
}