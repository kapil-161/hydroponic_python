#include "timeseriesplotwidget.h"
#include <QApplication>
#include <QFileDialog>
#include <QMessageBox>
#include <QDateTime>
#include <QDebug>
#include <QPen>
#include <QBrush>

TimeSeriesPlotWidget::TimeSeriesPlotWidget(QWidget *parent)
    : QWidget(parent)
    , m_dataModel(nullptr)
    , m_chartType(LineChart)
    , m_showLegend(true)
    , m_autoScale(true)
{
    setupUI();
    createChart();
    setupChartAppearance();
}

TimeSeriesPlotWidget::~TimeSeriesPlotWidget()
{
}

void TimeSeriesPlotWidget::setupUI()
{
    m_mainLayout = new QVBoxLayout(this);
    m_mainLayout->setSpacing(10);
    m_mainLayout->setContentsMargins(10, 10, 10, 10);
    
    // Top controls
    QHBoxLayout *topControlsLayout = new QHBoxLayout;
    
    // Chart type selection
    topControlsLayout->addWidget(new QLabel("Chart Type:"));
    m_chartTypeCombo = new QComboBox;
    m_chartTypeCombo->addItems({"Line Chart", "Spline Chart", "Scatter Chart"});
    topControlsLayout->addWidget(m_chartTypeCombo);
    
    topControlsLayout->addSpacing(20);
    
    // Display options
    m_showLegendCheck = new QCheckBox("Show Legend");
    m_showLegendCheck->setChecked(true);
    topControlsLayout->addWidget(m_showLegendCheck);
    
    m_autoScaleCheck = new QCheckBox("Auto Scale");
    m_autoScaleCheck->setChecked(true);
    topControlsLayout->addWidget(m_autoScaleCheck);
    
    topControlsLayout->addStretch();
    
    // Export button
    m_exportButton = new QPushButton("📊 Export Chart");
    topControlsLayout->addWidget(m_exportButton);
    
    m_mainLayout->addLayout(topControlsLayout);
    
    // Main content layout
    QHBoxLayout *contentLayout = new QHBoxLayout;
    
    // Parameter selection panel
    createParameterControls();
    contentLayout->addWidget(m_parametersGroup, 0);
    
    // Chart view
    m_chartView = new QChartView;
    m_chartView->setRenderHint(QPainter::Antialiasing);
    m_chartView->setMinimumSize(600, 400);
    m_chartView->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    contentLayout->addWidget(m_chartView, 1);
    
    qDebug() << "TimeSeriesPlotWidget: Chart view created with size:" << m_chartView->size();
    
    m_mainLayout->addLayout(contentLayout, 1);
    
    // Connect signals
    connect(m_chartTypeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged), 
            this, &TimeSeriesPlotWidget::onChartTypeChanged);
    connect(m_showLegendCheck, &QCheckBox::toggled, this, &TimeSeriesPlotWidget::onShowLegendChanged);
    connect(m_autoScaleCheck, &QCheckBox::toggled, this, &TimeSeriesPlotWidget::onAutoScaleChanged);
    connect(m_exportButton, &QPushButton::clicked, this, &TimeSeriesPlotWidget::exportChart);
}

void TimeSeriesPlotWidget::createParameterControls()
{
    m_parametersGroup = new QGroupBox("Parameters to Plot");
    m_parametersGroup->setMaximumWidth(250);
    m_parametersGroup->setMinimumWidth(220);
    
    QVBoxLayout *groupLayout = new QVBoxLayout;
    
    // Selection buttons
    QHBoxLayout *buttonLayout = new QHBoxLayout;
    m_selectAllButton = new QPushButton("Select All");
    m_clearAllButton = new QPushButton("Clear All");
    buttonLayout->addWidget(m_selectAllButton);
    buttonLayout->addWidget(m_clearAllButton);
    
    connect(m_selectAllButton, &QPushButton::clicked, [this]() {
        for (auto checkbox : m_parameterCheckboxes) {
            checkbox->setChecked(true);
        }
        onParameterSelectionChanged();
    });
    
    connect(m_clearAllButton, &QPushButton::clicked, [this]() {
        for (auto checkbox : m_parameterCheckboxes) {
            checkbox->setChecked(false);
        }
        onParameterSelectionChanged();
    });
    
    groupLayout->addLayout(buttonLayout);
    
    // Scrollable parameter list
    m_parametersScrollArea = new QScrollArea;
    m_parametersWidget = new QWidget;
    m_parametersLayout = new QVBoxLayout(m_parametersWidget);
    
    m_parametersScrollArea->setWidget(m_parametersWidget);
    m_parametersScrollArea->setWidgetResizable(true);
    m_parametersScrollArea->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    
    groupLayout->addWidget(m_parametersScrollArea, 1);
    m_parametersGroup->setLayout(groupLayout);
}

void TimeSeriesPlotWidget::createChart()
{
    m_chart = new QChart;
    m_chart->setTitle("Hydroponic System Time Series Data");
    m_chart->setAnimationOptions(QChart::SeriesAnimations);
    
    // Axes
    m_axisX = new QValueAxis;
    m_axisX->setTitleText("Day");
    m_axisX->setLabelFormat("%d");
    
    m_axisY = new QValueAxis;
    m_axisY->setTitleText("Value");
    
    m_chart->addAxis(m_axisX, Qt::AlignBottom);
    m_chart->addAxis(m_axisY, Qt::AlignLeft);
    
    m_chartView->setChart(m_chart);
    
    qDebug() << "TimeSeriesPlotWidget: Chart created and set to chart view";
    qDebug() << "TimeSeriesPlotWidget: Chart view has chart:" << (m_chartView->chart() != nullptr);
}

void TimeSeriesPlotWidget::setupChartAppearance()
{
    // Chart theme and appearance
    m_chart->setTheme(QChart::ChartThemeLight);
    m_chart->legend()->setAlignment(Qt::AlignBottom);
    m_chart->legend()->setVisible(m_showLegend);
    
    // Chart view settings
    m_chartView->setRubberBand(QChartView::RectangleRubberBand);
    m_chartView->chart()->setBackgroundBrush(QBrush(QColor(248, 248, 248)));
}

void TimeSeriesPlotWidget::loadDataFromModel(CSVTableModel *model)
{
    if (!model) {
        qDebug() << "TimeSeriesPlotWidget: No model provided";
        return;
    }
    
    qDebug() << "TimeSeriesPlotWidget: Loading data from model with" << model->rowCount() << "rows and" << model->columnCount() << "columns";
    
    m_dataModel = model;
    
    // Clear existing parameters
    for (auto checkbox : m_parameterCheckboxes) {
        checkbox->deleteLater();
    }
    m_parameterCheckboxes.clear();
    m_availableParameters.clear();
    
    // Get available parameters (skip Day, Date columns)
    QStringList headers = model->getHeaders();
    qDebug() << "TimeSeriesPlotWidget: Headers from model:" << headers;
    QStringList excludeColumns = {"Date", "Day", "System_ID", "Crop_ID"};
    
    for (const QString &header : headers) {
        if (!excludeColumns.contains(header, Qt::CaseInsensitive)) {
            m_availableParameters.append(header);
        }
    }
    qDebug() << "TimeSeriesPlotWidget: Available parameters for plotting:" << m_availableParameters;
    
    // Create checkboxes for parameters
    for (const QString &param : m_availableParameters) {
        QCheckBox *checkbox = new QCheckBox(formatParameterName(param));
        checkbox->setObjectName(param);
        
        connect(checkbox, &QCheckBox::toggled, this, &TimeSeriesPlotWidget::onParameterSelectionChanged);
        
        m_parameterCheckboxes[param] = checkbox;
        m_parametersLayout->addWidget(checkbox);
    }
    
    m_parametersLayout->addStretch();
    
    // Auto-select some interesting parameters
    QStringList autoSelect = {"Total_Biomass_g", "LAI", "Growth_Stage", "pH", "Temp_C"};
    qDebug() << "TimeSeriesPlotWidget: Auto-selecting parameters:" << autoSelect;
    for (const QString &param : autoSelect) {
        if (m_parameterCheckboxes.contains(param)) {
            m_parameterCheckboxes[param]->setChecked(true);
            qDebug() << "TimeSeriesPlotWidget: Auto-selected parameter:" << param;
        } else {
            qDebug() << "TimeSeriesPlotWidget: Parameter not found for auto-select:" << param;
        }
    }
    
    qDebug() << "TimeSeriesPlotWidget: About to call onParameterSelectionChanged()";
    onParameterSelectionChanged();
    qDebug() << "TimeSeriesPlotWidget: loadDataFromModel completed";
}

void TimeSeriesPlotWidget::clearPlot()
{
    m_chart->removeAllSeries();
    m_series.clear();
    m_selectedParameters.clear();
}

void TimeSeriesPlotWidget::onParameterSelectionChanged()
{
    if (!m_dataModel) return;
    
    m_selectedParameters.clear();
    for (auto it = m_parameterCheckboxes.begin(); it != m_parameterCheckboxes.end(); ++it) {
        if (it.value()->isChecked()) {
            m_selectedParameters.append(it.key());
        }
    }
    
    updateChart();
}

void TimeSeriesPlotWidget::onChartTypeChanged()
{
    m_chartType = static_cast<ChartType>(m_chartTypeCombo->currentIndex());
    updateChart();
}

void TimeSeriesPlotWidget::onShowLegendChanged()
{
    m_showLegend = m_showLegendCheck->isChecked();
    m_chart->legend()->setVisible(m_showLegend);
}

void TimeSeriesPlotWidget::onAutoScaleChanged()
{
    m_autoScale = m_autoScaleCheck->isChecked();
    updateChart();
}

void TimeSeriesPlotWidget::updateChart()
{
    qDebug() << "TimeSeriesPlotWidget: updateChart() called";
    qDebug() << "TimeSeriesPlotWidget: dataModel exists:" << (m_dataModel != nullptr);
    qDebug() << "TimeSeriesPlotWidget: selected parameters:" << m_selectedParameters;
    
    if (!m_dataModel || m_selectedParameters.isEmpty()) {
        qDebug() << "TimeSeriesPlotWidget: No data model or selected parameters, clearing plot";
        clearPlot();
        return;
    }
    
    qDebug() << "TimeSeriesPlotWidget: Model has" << m_dataModel->rowCount() << "rows and" << m_dataModel->columnCount() << "columns";
    qDebug() << "TimeSeriesPlotWidget: Model headers:" << m_dataModel->getHeaders();
    
    clearPlot();
    
    // Find day column
    int dayColumn = m_dataModel->findColumnByName("Day");
    qDebug() << "TimeSeriesPlotWidget: Day column index:" << dayColumn;
    if (dayColumn == -1) {
        qDebug() << "TimeSeriesPlotWidget: Day column not found!";
        return;
    }
    
    // Add series for each selected parameter
    for (int i = 0; i < m_selectedParameters.size(); ++i) {
        const QString &paramName = m_selectedParameters.at(i);
        qDebug() << "TimeSeriesPlotWidget: Processing parameter:" << paramName;
        int paramColumn = m_dataModel->findColumnByName(paramName);
        qDebug() << "TimeSeriesPlotWidget: Parameter column index:" << paramColumn;
        
        if (paramColumn == -1) {
            qDebug() << "TimeSeriesPlotWidget: Parameter column not found:" << paramName;
            continue;
        }
        
        QColor color = getColorForParameter(i);
        addSeriesToChart(paramName, color);
        
        // Populate data
        QAbstractSeries *series = nullptr;
        if (m_chartType == LineChart) {
            series = new QLineSeries;
            qDebug() << "TimeSeriesPlotWidget: Created QLineSeries for" << paramName;
        } else if (m_chartType == SplineChart) {
            series = new QSplineSeries;
            qDebug() << "TimeSeriesPlotWidget: Created QSplineSeries for" << paramName;
        } else if (m_chartType == ScatterChart) {
            series = new QScatterSeries;
            qDebug() << "TimeSeriesPlotWidget: Created QScatterSeries for" << paramName;
        }
        
        if (!series) {
            qDebug() << "TimeSeriesPlotWidget: Failed to create series for" << paramName;
            continue;
        }
        
        series->setName(formatParameterName(paramName));
        // Set color using pen
        QPen pen(color);
        pen.setWidth(2);
        if (m_chartType == LineChart) {
            static_cast<QLineSeries*>(series)->setPen(pen);
        } else if (m_chartType == SplineChart) {
            static_cast<QSplineSeries*>(series)->setPen(pen);
        } else if (m_chartType == ScatterChart) {
            static_cast<QScatterSeries*>(series)->setBrush(QBrush(color));
        }
        
        // Add data points
        int pointCount = 0;
        for (int row = 0; row < m_dataModel->rowCount(); ++row) {
            QString dayStr = m_dataModel->getCellData(row, dayColumn);
            QString valueStr = m_dataModel->getCellData(row, paramColumn);
            
            bool dayOk, valueOk;
            qreal day = dayStr.toDouble(&dayOk);
            qreal value = valueStr.toDouble(&valueOk);
            
            if (dayOk && valueOk) {
                if (m_chartType == LineChart) {
                    static_cast<QLineSeries*>(series)->append(day, value);
                } else if (m_chartType == SplineChart) {
                    static_cast<QSplineSeries*>(series)->append(day, value);
                } else if (m_chartType == ScatterChart) {
                    static_cast<QScatterSeries*>(series)->append(day, value);
                }
                pointCount++;
            } else {
                qDebug() << "TimeSeriesPlotWidget: Invalid data at row" << row << "for" << paramName 
                         << "day:" << dayStr << "value:" << valueStr;
            }
        }
        qDebug() << "TimeSeriesPlotWidget: Added" << pointCount << "data points for parameter:" << paramName;
        
        if (pointCount == 0) {
            qDebug() << "TimeSeriesPlotWidget: No valid data points for" << paramName << "- skipping series";
            delete series;
            continue;
        }
        
        qDebug() << "TimeSeriesPlotWidget: Adding series to chart for parameter:" << paramName;
        m_chart->addSeries(series);
        series->attachAxis(m_axisX);
        series->attachAxis(m_axisY);
        
        m_series[paramName] = static_cast<QLineSeries*>(series);
        qDebug() << "TimeSeriesPlotWidget: Series added successfully";
    }
    
    qDebug() << "TimeSeriesPlotWidget: Total series added:" << m_series.size();
    
    // Auto-scale axes
    if (m_autoScale && !m_selectedParameters.isEmpty()) {
        // Find data ranges
        qreal minX = std::numeric_limits<qreal>::max();
        qreal maxX = std::numeric_limits<qreal>::lowest();
        qreal minY = std::numeric_limits<qreal>::max();
        qreal maxY = std::numeric_limits<qreal>::lowest();
        
        int dayColumn = m_dataModel->findColumnByName("Day");
        for (const QString &paramName : m_selectedParameters) {
            int paramColumn = m_dataModel->findColumnByName(paramName);
            if (paramColumn == -1) continue;
            
            for (int row = 0; row < m_dataModel->rowCount(); ++row) {
                bool dayOk, valueOk;
                qreal day = m_dataModel->getCellData(row, dayColumn).toDouble(&dayOk);
                qreal value = m_dataModel->getCellData(row, paramColumn).toDouble(&valueOk);
                
                if (dayOk && valueOk) {
                    minX = std::min(minX, day);
                    maxX = std::max(maxX, day);
                    minY = std::min(minY, value);
                    maxY = std::max(maxY, value);
                }
            }
        }
        
        if (minX <= maxX && minY <= maxY) {
            qreal xPadding = (maxX - minX) * 0.05;
            qreal yPadding = (maxY - minY) * 0.1;
            
            m_axisX->setRange(minX - xPadding, maxX + xPadding);
            m_axisY->setRange(minY - yPadding, maxY + yPadding);
            
            qDebug() << "TimeSeriesPlotWidget: Set axis ranges - X:" << minX - xPadding << "to" << maxX + xPadding 
                     << "Y:" << minY - yPadding << "to" << maxY + yPadding;
        } else {
            qDebug() << "TimeSeriesPlotWidget: Invalid data ranges for auto-scaling";
        }
    }
    
    qDebug() << "TimeSeriesPlotWidget: Chart update completed";
}

void TimeSeriesPlotWidget::addSeriesToChart(const QString &parameterName, const QColor &color)
{
    Q_UNUSED(parameterName)
    Q_UNUSED(color)
    // Implementation handled in updateChart
}

QColor TimeSeriesPlotWidget::getColorForParameter(int index)
{
    QList<QColor> colors = {
        QColor(31, 119, 180),   // Blue
        QColor(255, 127, 14),   // Orange
        QColor(44, 160, 44),    // Green
        QColor(214, 39, 40),    // Red
        QColor(148, 103, 189),  // Purple
        QColor(140, 86, 75),    // Brown
        QColor(227, 119, 194),  // Pink
        QColor(127, 127, 127),  // Gray
        QColor(188, 189, 34),   // Olive
        QColor(23, 190, 207)    // Cyan
    };
    
    return colors[index % colors.size()];
}

QString TimeSeriesPlotWidget::formatParameterName(const QString &parameterName)
{
    QString formatted = parameterName;
    formatted.replace('_', ' ');
    
    // Handle common abbreviations
    formatted.replace("Temp C", "Temperature (°C)");
    formatted.replace("LAI", "Leaf Area Index");
    formatted.replace("VPD", "Vapor Pressure Deficit");
    formatted.replace("RZT", "Root Zone Temperature");
    formatted.replace("WUE", "Water Use Efficiency");
    
    return formatted;
}

void TimeSeriesPlotWidget::exportChart()
{
    QString fileName = QFileDialog::getSaveFileName(
        this,
        "Export Chart",
        QString("hydroponic_chart_%1.png").arg(QDateTime::currentDateTime().toString("yyyyMMdd_hhmmss")),
        "PNG Images (*.png);;PDF Files (*.pdf);;SVG Files (*.svg)"
    );
    
    if (!fileName.isEmpty()) {
        QPixmap pixmap = m_chartView->grab();
        if (pixmap.save(fileName)) {
            QMessageBox::information(this, "Export Successful", 
                QString("Chart exported to: %1").arg(fileName));
        } else {
            QMessageBox::warning(this, "Export Failed", "Could not save chart image.");
        }
    }
}