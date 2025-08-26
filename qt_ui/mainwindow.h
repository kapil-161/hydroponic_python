#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QMenuBar>
#include <QToolBar>
#include <QStatusBar>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QSplitter>
#include <QTabWidget>
#include <QTreeView>
#include <QFileSystemModel>
#include "hierarchicalfilemodel.h"
#include "timeseriesplotwidget.h"
#include <QLabel>
#include <QPushButton>
#include <QLineEdit>
#include <QComboBox>
#include <QMessageBox>
#include <QFileDialog>
#include <QTextEdit>
#include <QGroupBox>
#include <QFormLayout>
#include <QSpinBox>
#include <QProcess>
#include <QProgressBar>
#include "csvtableview.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void openFile();
    void saveFile();
    void saveAsFile();
    void newFile();
    void addRow();
    void removeRow();
    void duplicateRow();
    void findDuplicates();
    void generateBatchFile();
    void runSimulation();
    void runMultiVarietySimulation();
    void onFileSelected(const QModelIndex &index);
    void onSimulationFinished(int exitCode, QProcess::ExitStatus exitStatus);
    QStringList getSelectedVarieties() const;
    QMap<QString, QStringList> getSelectedTreatments() const;
    QStringList generateTreatmentCombinations() const;
    QStringList parseTreatmentCombination(const QString &combo) const;
    void updateTreatmentPreview();
    void updateExperimentSettings();

private:
    void setupUI();
    void setupMenuBar();
    void setupToolBar();
    void setupStatusBar();
    void createFileExplorer();
    void createCSVEditor();
    void createBatchGenerator();
    void createResultsViewer();
    void createPlotViewer();
    void createTreatmentCategory(const QString &categoryName, const QStringList &options, const QStringList &defaults);
    void connectSignals();
    void updateWindowTitle();
    void showDuplicates(const QStringList &duplicates);
    bool maybeSave();
    void setCurrentFile(const QString &fileName);
    void loadCSVFile(const QString &fileName);
    void loadResultsFile(const QString &fileName);
    void loadMultipleTreatmentResults();
    void findLatestResults();
    void exportResults();
    void refreshResults();
    QStringList findTreatmentResultFiles() const;
    
    // UI Components
    QWidget *m_centralWidget;
    QSplitter *m_mainSplitter;
    QTabWidget *m_tabWidget;
    
    // File Explorer
    QTreeView *m_fileTree;
    QFileSystemModel *m_fileSystemModel;
    HierarchicalFileModel *m_hierarchicalModel;
    QGroupBox *m_fileExplorerGroup;
    
    // CSV Editor
    CSVTableView *m_csvTableView;
    QGroupBox *m_csvEditorGroup;
    QLineEdit *m_searchLineEdit;
    QPushButton *m_addRowButton;
    QPushButton *m_removeRowButton;
    QPushButton *m_duplicateRowButton;
    QPushButton *m_findDuplicatesButton;
    
    // Batch Generator
    QWidget *m_batchGeneratorGroup;
    QLineEdit *m_experimentNameEdit;
    QComboBox *m_cropTypeCombo;
    QWidget *m_treatmentSelectionGroup;
    QVBoxLayout *m_treatmentLayout;
    QScrollArea *m_treatmentScrollArea;
    QSpinBox *m_durationSpinBox;
    QTextEdit *m_batchPreview;
    QPushButton *m_generateBatchButton;
    QPushButton *m_runSimulationButton;
    
    // Results Viewer
    QWidget *m_resultsViewerGroup;
    CSVTableView *m_resultsTableView;
    QLabel *m_resultsInfoLabel;
    QPushButton *m_exportResultsButton;
    QPushButton *m_refreshResultsButton;
    
    // Time Series Plot
    QWidget *m_plotViewerGroup;
    TimeSeriesPlotWidget *m_plotWidget;
    
    // Menu and toolbar
    QAction *m_openAction;
    QAction *m_saveAction;
    QAction *m_saveAsAction;
    QAction *m_newAction;
    QAction *m_exitAction;
    
    // Status bar
    QLabel *m_statusLabel;
    QProgressBar *m_progressBar;
    
    // File handling
    QString m_currentFile;
    QString m_inputDirectory;
    QString m_resultsFile;
    
    // Process handling
    QProcess *m_simulationProcess;
};

#endif // MAINWINDOW_H