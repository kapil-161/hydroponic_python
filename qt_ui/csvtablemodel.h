#ifndef CSVTABLEMODEL_H
#define CSVTABLEMODEL_H

#include <QAbstractTableModel>
#include <QStringList>
#include <QVector>

class CSVTableModel : public QAbstractTableModel
{
    Q_OBJECT

public:
    explicit CSVTableModel(QObject *parent = nullptr);
    ~CSVTableModel();

    // QAbstractTableModel interface
    int rowCount(const QModelIndex &parent = QModelIndex()) const override;
    int columnCount(const QModelIndex &parent = QModelIndex()) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QVariant headerData(int section, Qt::Orientation orientation, int role = Qt::DisplayRole) const override;
    bool setData(const QModelIndex &index, const QVariant &value, int role = Qt::EditRole) override;
    Qt::ItemFlags flags(const QModelIndex &index) const override;
    
    // CSV operations
    bool loadFromFile(const QString &fileName);
    bool saveToFile(const QString &fileName);
    void clear();
    
    // Row operations
    bool insertRows(int row, int count, const QModelIndex &parent = QModelIndex()) override;
    bool removeRows(int row, int count, const QModelIndex &parent = QModelIndex()) override;
    void duplicateRow(int row);
    
    // Utility functions
    QStringList findDuplicateRows();
    void setHeaders(const QStringList &headers);
    QStringList getHeaders() const;
    int findColumnByName(const QString &columnName) const;
    
    // Data access
    QString getCellData(int row, int column) const;
    void setCellData(int row, int column, const QString &value);
    QVector<QStringList> getAllData() const { return m_data; }
    
signals:
    void dataModified();

private:
    QStringList m_headers;
    QVector<QStringList> m_data;
    bool m_isModified;
    
    QString parseCsvField(const QString &field) const;
    QString formatCsvField(const QString &field) const;
    QStringList parseCsvLine(const QString &line) const;
    QString formatCsvLine(const QStringList &fields) const;
};

#endif // CSVTABLEMODEL_H