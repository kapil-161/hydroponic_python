#ifndef TIMESERIESPLOTWIDGET_H
#define TIMESERIESPLOTWIDGET_H

#include <QtWidgets/QWidget>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QFormLayout>
#include <QtWidgets/QLabel>
#include <QtWidgets/QComboBox>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QScrollArea>
#include <QtWidgets/QGroupBox>
#include <QtCharts/QChartView>
#include <QtCharts/QChart>
#include <QtCharts/QLineSeries>
#include <QtCharts/QValueAxis>
#include <QtCharts/QDateTimeAxis>
#include <QtCharts/QScatterSeries>
#include <QtCharts/QSplineSeries>
#include <QtCharts/QLegend>
#include <QMap>
#include <QStringList>
#include "csvtablemodel.h"


class TimeSeriesPlotWidget : public QWidget
{
    Q_OBJECT

public:
    explicit TimeSeriesPlotWidget(QWidget *parent = nullptr);
    ~TimeSeriesPlotWidget();

    void loadDataFromModel(CSVTableModel *model);
    void clearPlot();
    void resetChart();
    void debugChartState();

private slots:
    void onParameterSelectionChanged();
    void onChartTypeChanged();
    void onShowLegendChanged();
    void onAutoScaleChanged();
    void exportChart();

private:
    void setupUI();
    void createParameterControls();
    void createChart();
    void updateChart();
    void setupChartAppearance();
    void addSeriesToChart(const QString &parameterName, const QColor &color);
    QColor getColorForParameter(int index);
    QString formatParameterName(const QString &parameterName);
    
    // UI Components
    QVBoxLayout *m_mainLayout;
    QHBoxLayout *m_controlsLayout;
    QVBoxLayout *m_parametersLayout;
    
    // Controls
    QGroupBox *m_parametersGroup;
    QScrollArea *m_parametersScrollArea;
    QWidget *m_parametersWidget;
    QComboBox *m_chartTypeCombo;
    QCheckBox *m_showLegendCheck;
    QCheckBox *m_autoScaleCheck;
    QPushButton *m_exportButton;
    QPushButton *m_clearAllButton;
    QPushButton *m_selectAllButton;
    
    // Chart
    QChartView *m_chartView;
    QChart *m_chart;
    QValueAxis *m_axisX;
    QValueAxis *m_axisY;
    QDateTimeAxis *m_dateAxisX;
    
    // Data
    CSVTableModel *m_dataModel;
    QMap<QString, QCheckBox*> m_parameterCheckboxes;
    QMap<QString, QLineSeries*> m_series;
    QStringList m_availableParameters;
    QStringList m_selectedParameters;
    
    // Chart settings
    enum ChartType {
        LineChart,
        SplineChart,
        ScatterChart
    };
    ChartType m_chartType;
    bool m_showLegend;
    bool m_autoScale;
};

#endif // TIMESERIESPLOTWIDGET_H