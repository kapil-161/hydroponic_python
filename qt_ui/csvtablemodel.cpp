#include "csvtablemodel.h"
#include <QFile>
#include <QTextStream>
#include <QDebug>
#include <QRegularExpression>

CSVTableModel::CSVTableModel(QObject *parent)
    : QAbstractTableModel(parent)
    , m_isModified(false)
{
}

CSVTableModel::~CSVTableModel()
{
}

int CSVTableModel::rowCount(const QModelIndex &parent) const
{
    Q_UNUSED(parent)
    return m_data.count();
}

int CSVTableModel::columnCount(const QModelIndex &parent) const
{
    Q_UNUSED(parent)
    return m_headers.count();
}

QVariant CSVTableModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() >= m_data.count() || 
        index.column() >= m_headers.count()) {
        return QVariant();
    }
    
    const QStringList &row = m_data.at(index.row());
    
    if (role == Qt::DisplayRole || role == Qt::EditRole) {
        if (index.column() < row.count()) {
            return row.at(index.column());
        } else {
            return QString(); // Empty cell
        }
    }
    
    return QVariant();
}

QVariant CSVTableModel::headerData(int section, Qt::Orientation orientation, int role) const
{
    if (role == Qt::DisplayRole) {
        if (orientation == Qt::Horizontal && section < m_headers.count()) {
            return m_headers.at(section);
        } else if (orientation == Qt::Vertical) {
            return QString::number(section + 1);
        }
    }
    return QVariant();
}

bool CSVTableModel::setData(const QModelIndex &index, const QVariant &value, int role)
{
    if (!index.isValid() || index.row() >= m_data.count() || 
        index.column() >= m_headers.count() || role != Qt::EditRole) {
        return false;
    }
    
    QStringList &row = m_data[index.row()];
    
    // Extend row if necessary
    while (row.count() <= index.column()) {
        row.append(QString());
    }
    
    row[index.column()] = value.toString();
    m_isModified = true;
    
    emit dataChanged(index, index);
    emit dataModified();
    return true;
}

Qt::ItemFlags CSVTableModel::flags(const QModelIndex &index) const
{
    if (!index.isValid()) {
        return Qt::NoItemFlags;
    }
    
    return Qt::ItemIsEnabled | Qt::ItemIsSelectable | Qt::ItemIsEditable;
}

bool CSVTableModel::loadFromFile(const QString &fileName)
{
    QFile file(fileName);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return false;
    }
    
    beginResetModel();
    
    m_data.clear();
    m_headers.clear();
    
    QTextStream in(&file);
    bool firstLine = true;
    
    while (!in.atEnd()) {
        QString line = in.readLine();
        QStringList fields = parseCsvLine(line);
        
        if (firstLine) {
            m_headers = fields;
            firstLine = false;
        } else {
            // Ensure all rows have the same number of columns as headers
            while (fields.count() < m_headers.count()) {
                fields.append(QString());
            }
            m_data.append(fields);
        }
    }
    
    // If no headers were found, create default ones
    if (m_headers.isEmpty() && !m_data.isEmpty()) {
        for (int i = 0; i < m_data.first().count(); ++i) {
            m_headers.append(QString("Column %1").arg(i + 1));
        }
    }
    
    m_isModified = false;
    endResetModel();
    
    return true;
}

bool CSVTableModel::saveToFile(const QString &fileName)
{
    QFile file(fileName);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return false;
    }
    
    QTextStream out(&file);
    
    // Write headers
    out << formatCsvLine(m_headers) << "\n";
    
    // Write data
    for (const QStringList &row : m_data) {
        out << formatCsvLine(row) << "\n";
    }
    
    m_isModified = false;
    return true;
}

void CSVTableModel::clear()
{
    beginResetModel();
    m_data.clear();
    m_headers.clear();
    m_isModified = false;
    endResetModel();
}

bool CSVTableModel::insertRows(int row, int count, const QModelIndex &parent)
{
    Q_UNUSED(parent)
    
    if (row < 0 || row > m_data.count()) {
        return false;
    }
    
    beginInsertRows(QModelIndex(), row, row + count - 1);
    
    for (int i = 0; i < count; ++i) {
        QStringList newRow;
        // Create empty cells for all columns
        for (int j = 0; j < m_headers.count(); ++j) {
            newRow.append(QString());
        }
        m_data.insert(row + i, newRow);
    }
    
    m_isModified = true;
    endInsertRows();
    emit dataModified();
    
    return true;
}

bool CSVTableModel::removeRows(int row, int count, const QModelIndex &parent)
{
    Q_UNUSED(parent)
    
    if (row < 0 || row >= m_data.count() || count <= 0) {
        return false;
    }
    
    int endRow = qMin(row + count - 1, m_data.count() - 1);
    
    beginRemoveRows(QModelIndex(), row, endRow);
    
    for (int i = endRow; i >= row; --i) {
        m_data.removeAt(i);
    }
    
    m_isModified = true;
    endRemoveRows();
    emit dataModified();
    
    return true;
}

void CSVTableModel::duplicateRow(int row)
{
    if (row < 0 || row >= m_data.count()) {
        return;
    }
    
    QStringList originalRow = m_data.at(row);
    insertRows(row + 1, 1);
    
    // Copy data to the new row
    for (int col = 0; col < originalRow.count(); ++col) {
        setData(index(row + 1, col), originalRow.at(col));
    }
}

QStringList CSVTableModel::findDuplicateRows()
{
    QStringList duplicates;
    QSet<QString> seenRows;
    
    for (int i = 0; i < m_data.count(); ++i) {
        QString rowString = m_data.at(i).join(",");
        if (seenRows.contains(rowString)) {
            duplicates.append(QString("Row %1: %2").arg(i + 1).arg(rowString));
        } else {
            seenRows.insert(rowString);
        }
    }
    
    return duplicates;
}

void CSVTableModel::setHeaders(const QStringList &headers)
{
    beginResetModel();
    m_headers = headers;
    endResetModel();
}

QStringList CSVTableModel::getHeaders() const
{
    return m_headers;
}

int CSVTableModel::findColumnByName(const QString &columnName) const
{
    return m_headers.indexOf(columnName);
}

QString CSVTableModel::getCellData(int row, int column) const
{
    if (row < 0 || row >= m_data.count() || column < 0 || column >= m_headers.count()) {
        return QString();
    }
    
    const QStringList &rowData = m_data.at(row);
    if (column < rowData.count()) {
        return rowData.at(column);
    }
    
    return QString();
}

void CSVTableModel::setCellData(int row, int column, const QString &value)
{
    QModelIndex idx = index(row, column);
    setData(idx, value);
}

QString CSVTableModel::parseCsvField(const QString &field) const
{
    QString result = field.trimmed();
    
    // Remove surrounding quotes if present
    if (result.startsWith('"') && result.endsWith('"')) {
        result = result.mid(1, result.length() - 2);
        // Unescape double quotes
        result.replace("\"\"", "\"");
    }
    
    return result;
}

QString CSVTableModel::formatCsvField(const QString &field) const
{
    QString result = field;
    
    // Quote field if it contains comma, quote, or newline
    if (result.contains(',') || result.contains('"') || result.contains('\n')) {
        result.replace("\"", "\"\""); // Escape quotes
        result = "\"" + result + "\""; // Wrap in quotes
    }
    
    return result;
}

QStringList CSVTableModel::parseCsvLine(const QString &line) const
{
    QStringList fields;
    QString currentField;
    bool inQuotes = false;
    
    for (int i = 0; i < line.length(); ++i) {
        QChar c = line.at(i);
        
        if (c == '"') {
            if (inQuotes && i + 1 < line.length() && line.at(i + 1) == '"') {
                // Escaped quote
                currentField += '"';
                i++; // Skip next quote
            } else {
                // Toggle quote mode
                inQuotes = !inQuotes;
            }
        } else if (c == ',' && !inQuotes) {
            // Field separator
            fields.append(parseCsvField(currentField));
            currentField.clear();
        } else {
            currentField += c;
        }
    }
    
    // Add the last field
    fields.append(parseCsvField(currentField));
    
    return fields;
}

QString CSVTableModel::formatCsvLine(const QStringList &fields) const
{
    QStringList formattedFields;
    for (const QString &field : fields) {
        formattedFields.append(formatCsvField(field));
    }
    return formattedFields.join(",");
}