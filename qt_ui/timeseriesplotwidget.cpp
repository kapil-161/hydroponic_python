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
    
    // Export button and debug button
    m_exportButton = new QPushButton("📊 Export Chart");
    topControlsLayout->addWidget(m_exportButton);
    
    QPushButton *debugButton = new QPushButton("🐛 Debug");
    topControlsLayout->addWidget(debugButton);
    connect(debugButton, &QPushButton::clicked, this, &TimeSeriesPlotWidget::debugChartState);
    
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
    m_axisY->setMin(0); // Always start Y-axis from 0
    
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
        QString displayName = formatParameterName(param);
        QCheckBox *checkbox = new QCheckBox(displayName);
        checkbox->setObjectName(param);
        
        // Add tooltip showing the original parameter name and formatted name
        QString tooltip = QString("Original: %1\nDisplay: %2").arg(param, displayName);
        checkbox->setToolTip(tooltip);
        
        connect(checkbox, &QCheckBox::toggled, this, &TimeSeriesPlotWidget::onParameterSelectionChanged);
        
        m_parameterCheckboxes[param] = checkbox;
        m_parametersLayout->addWidget(checkbox);
    }
    
    m_parametersLayout->addStretch();
    
    // Auto-select some interesting parameters (using exact column names from CSV)
    QStringList autoSelect = {"Total_Biomass_g", "LAI", "pH", "Temp_C", "VPD_kPa"};
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
    
    // Debug chart state after loading data
    debugChartState();
    
    qDebug() << "TimeSeriesPlotWidget: loadDataFromModel completed";
}

void TimeSeriesPlotWidget::clearPlot()
{
    // Clear all series from chart
    QList<QAbstractSeries*> allSeries = m_chart->series();
    for (QAbstractSeries* series : allSeries) {
        m_chart->removeSeries(series);
        delete series;  // Clean up memory
    }
    
    m_series.clear();
    // Note: Don't clear m_selectedParameters here as user selections should persist
    
    qDebug() << "TimeSeriesPlotWidget: Plot cleared, removed" << allSeries.size() << "series";
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
        
        // Ensure axes are properly attached
        if (!m_chart->axes(Qt::Horizontal).contains(m_axisX)) {
            m_chart->addAxis(m_axisX, Qt::AlignBottom);
        }
        if (!m_chart->axes(Qt::Vertical).contains(m_axisY)) {
            m_chart->addAxis(m_axisY, Qt::AlignLeft);
        }
        
        series->attachAxis(m_axisX);
        series->attachAxis(m_axisY);
        
        // Store series reference (don't cast scatter/spline to line series as they're different types)
        // Just store the base QLineSeries pointer for line series, nullptr for others
        if (m_chartType == LineChart) {
            m_series[paramName] = static_cast<QLineSeries*>(series);
        } else {
            m_series[paramName] = nullptr;  // Don't store for non-line series to avoid casting issues
        }
        qDebug() << "TimeSeriesPlotWidget: Series added successfully";
    }
    
    qDebug() << "TimeSeriesPlotWidget: Total series added:" << m_series.size();
    
    // Update Y-axis title with units based on selected parameters
    updateYAxisTitle();
    
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
            qreal yPadding = maxY * 0.1; // Use percentage of max value for better scaling
            
            // Always start Y-axis from 0 for better visual context
            qreal yMin = 0.0;
            qreal yMax = maxY + yPadding;
            
            // Handle special case where all values are negative
            if (maxY < 0) {
                yMin = minY - yPadding;
                yMax = 0.0;
            }
            
            m_axisX->setRange(minX - xPadding, maxX + xPadding);
            m_axisY->setRange(yMin, yMax);
            
            qDebug() << "TimeSeriesPlotWidget: Set axis ranges - X:" << minX - xPadding << "to" << maxX + xPadding 
                     << "Y:" << yMin << "to" << yMax << "(forced Y-min to 0)";
        } else {
            qDebug() << "TimeSeriesPlotWidget: Invalid data ranges for auto-scaling";
        }
    }
    
    // Force chart refresh and ensure it's visible
    m_chartView->update();
    m_chartView->repaint();
    m_chartView->show();
    
    // Ensure the chart view has proper size
    if (m_chartView->size().width() < 100 || m_chartView->size().height() < 100) {
        m_chartView->resize(600, 400);
        qDebug() << "TimeSeriesPlotWidget: Resized chart view to:" << m_chartView->size();
    }
    
    qDebug() << "TimeSeriesPlotWidget: Chart update completed - forcing refresh";
}

void TimeSeriesPlotWidget::addSeriesToChart(const QString &parameterName, const QColor &color)
{
    Q_UNUSED(parameterName)
    Q_UNUSED(color)
    // Implementation handled in updateChart - this method kept for interface compatibility
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
    
    // Add units and format parameter names with proper scientific notation
    QMap<QString, QString> parameterUnits = {
        // Environmental parameters
        {"ETO Ref mm", "Reference ET (mm/day)"},
        {"ETC Prime mm", "Crop ET (mm/day)"},
        {"Transpiration mm", "Transpiration (mm/day)"},
        {"Temp C", "Temperature (°C)"},
        {"Solar Rad MJ", "Solar Radiation (MJ/m²/day)"},
        {"VPD kPa", "Vapor Pressure Deficit (kPa)"},
        {"VPD Actual kPa", "Actual VPD (kPa)"},
        {"CO2 umol mol", "CO₂ Concentration (μmol/mol)"},
        {"RZT C", "Root Zone Temperature (°C)"},
        
        // Water and solution parameters
        {"Water Total L", "Total Water (L)"},
        {"Tank Volume L", "Tank Volume (L)"},
        {"WUE kg m3", "Water Use Efficiency (kg/m³)"},
        {"pH", "pH"},
        {"EC", "Electrical Conductivity (dS/m)"},
        
        // Nutrient parameters
        {"N-NO3 mg L", "Nitrate-N (mg/L)"},
        {"P-PO4 mg L", "Phosphate-P (mg/L)"},
        {"K mg L", "Potassium (mg/L)"},
        {"Ca mg L", "Calcium (mg/L)"},
        {"Mg mg L", "Magnesium (mg/L)"},
        
        // Plant growth parameters
        {"Total Biomass g", "Total Biomass (g)"},
        {"LAI", "Leaf Area Index"},
        {"Leaf Number", "Leaf Number"},
        {"Leaf Area m2", "Leaf Area (m²)"},
        {"Avg Leaf Area cm2", "Average Leaf Area (cm²)"},
        {"V Stage", "Vegetative Stage"},
        {"Growth Stage", "Growth Stage"},
        
        // Stress and factor parameters
        {"RZT Growth Factor", "RZT Growth Factor"},
        {"RZT Nutrient Factor", "RZT Nutrient Factor"},
        {"Env Photo Factor", "Environmental Photo Factor"},
        {"Env Transp Factor", "Environmental Transp Factor"},
        {"Integrated Stress", "Integrated Stress Factor"},
        {"Temperature Stress", "Temperature Stress Factor"},
        {"Water Stress", "Water Stress Factor"},
        {"Nutrient Stress", "Nutrient Stress Factor"},
        {"Nitrogen Stress", "Nitrogen Stress Factor"},
        {"Salinity Stress", "Salinity Stress Factor"}
    };
    
    // Check if we have a specific unit mapping
    if (parameterUnits.contains(formatted)) {
        return parameterUnits[formatted];
    }
    
    // Handle common abbreviations for unmapped parameters
    formatted.replace("LAI", "Leaf Area Index");
    formatted.replace("VPD", "Vapor Pressure Deficit");
    formatted.replace("RZT", "Root Zone Temperature");
    formatted.replace("WUE", "Water Use Efficiency");
    
    return formatted;
}

void TimeSeriesPlotWidget::updateYAxisTitle()
{
    if (m_selectedParameters.isEmpty()) {
        m_axisY->setTitleText("Value");
        return;
    }
    
    // Extract units from selected parameters
    QStringList units;
    QMap<QString, QString> unitMap = {
        {"Total_Biomass_g", "g"},
        {"LAI", ""},
        {"Temp_C", "°C"},
        {"pH", ""},
        {"VPD_kPa", "kPa"},
        {"VPD_Actual_kPa", "kPa"},
        {"Water_Total_L", "L"},
        {"Tank_Volume_L", "L"},
        {"WUE_kg_m3", "kg/m³"},
        {"EC", "dS/m"},
        {"ETO_Ref_mm", "mm/day"},
        {"ETC_Prime_mm", "mm/day"},
        {"Transpiration_mm", "mm/day"},
        {"Solar_Rad_MJ", "MJ/m²/day"},
        {"RZT_C", "°C"},
        {"N-NO3_mg_L", "mg/L"},
        {"P-PO4_mg_L", "mg/L"},
        {"K_mg_L", "mg/L"},
        {"Ca_mg_L", "mg/L"},
        {"Mg_mg_L", "mg/L"},
        {"Leaf_Area_m2", "m²"},
        {"Avg_Leaf_Area_cm2", "cm²"},
        {"CO2_umol_mol", "μmol/mol"}
    };
    
    for (const QString &param : m_selectedParameters) {
        QString unit = unitMap.value(param, "");
        if (!unit.isEmpty() && !units.contains(unit)) {
            units.append(unit);
        }
    }
    
    QString yAxisTitle;
    if (units.isEmpty()) {
        yAxisTitle = "Value";
    } else if (units.size() == 1) {
        yAxisTitle = QString("Value (%1)").arg(units.first());
    } else {
        yAxisTitle = QString("Value (%1)").arg(units.join(", "));
    }
    
    m_axisY->setTitleText(yAxisTitle);
    qDebug() << "TimeSeriesPlotWidget: Updated Y-axis title to:" << yAxisTitle;
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

void TimeSeriesPlotWidget::resetChart()
{
    if (m_chart) {
        clearPlot();
        
        // Remove and recreate axes
        m_chart->removeAxis(m_axisX);
        m_chart->removeAxis(m_axisY);
        
        delete m_axisX;
        delete m_axisY;
        
        // Recreate axes
        m_axisX = new QValueAxis;
        m_axisX->setTitleText("Day");
        m_axisX->setLabelFormat("%d");
        
        m_axisY = new QValueAxis;
        m_axisY->setTitleText("Value");
        m_axisY->setMin(0); // Always start Y-axis from 0
        
        m_chart->addAxis(m_axisX, Qt::AlignBottom);
        m_chart->addAxis(m_axisY, Qt::AlignLeft);
        
        setupChartAppearance();
        
        qDebug() << "TimeSeriesPlotWidget: Chart reset completed";
    }
}

void TimeSeriesPlotWidget::debugChartState()
{
    qDebug() << "=== Chart Debug Info ===";
    qDebug() << "Chart widget visible:" << isVisible();
    qDebug() << "Chart widget size:" << size();
    qDebug() << "Chart view size:" << m_chartView->size();
    qDebug() << "Chart has series:" << (m_chart ? m_chart->series().count() : 0);
    qDebug() << "Chart has horizontal axes:" << (m_chart ? m_chart->axes(Qt::Horizontal).count() : 0);
    qDebug() << "Chart has vertical axes:" << (m_chart ? m_chart->axes(Qt::Vertical).count() : 0);
    qDebug() << "Data model valid:" << (m_dataModel != nullptr);
    if (m_dataModel) {
        qDebug() << "Data model rows:" << m_dataModel->rowCount();
        qDebug() << "Data model cols:" << m_dataModel->columnCount();
    }
    qDebug() << "Selected parameters:" << m_selectedParameters;
    qDebug() << "Available parameters:" << m_availableParameters;
    qDebug() << "========================";
}

