#include "csvtableview.h"
#include <QApplication>
#include <QClipboard>
#include <QHeaderView>
#include <QMimeData>

CSVTableView::CSVTableView(QWidget *parent)
    : QTableView(parent)
    , m_csvModel(nullptr)
{
    setupModel();
    setupView();
    createContextMenu();
}

CSVTableView::~CSVTableView()
{
}

void CSVTableView::setupModel()
{
    m_csvModel = new CSVTableModel(this);
    setModel(m_csvModel);
    
    connect(m_csvModel, &CSVTableModel::dataModified, this, &CSVTableView::onDataModified);
}

void CSVTableView::setupView()
{
    // Selection behavior
    setSelectionBehavior(QAbstractItemView::SelectRows);
    setSelectionMode(QAbstractItemView::ExtendedSelection);
    
    // Headers
    horizontalHeader()->setStretchLastSection(true);
    horizontalHeader()->setSectionResizeMode(QHeaderView::Interactive);
    verticalHeader()->setDefaultSectionSize(25);
    
    // Editing
    setEditTriggers(QAbstractItemView::DoubleClicked | 
                   QAbstractItemView::EditKeyPressed);
    
    // Appearance
    setAlternatingRowColors(true);
    setGridStyle(Qt::SolidLine);
    setSortingEnabled(false); // Disable sorting to preserve row order
    
    // Enable drag and drop for row reordering
    setDragDropMode(QAbstractItemView::InternalMove);
    setDefaultDropAction(Qt::MoveAction);
}

void CSVTableView::createContextMenu()
{
    setContextMenuPolicy(Qt::DefaultContextMenu);
    
    m_contextMenu = new QMenu(this);
    
    m_insertRowAboveAction = new QAction("Insert Row Above", this);
    m_insertRowBelowAction = new QAction("Insert Row Below", this);
    m_deleteRowsAction = new QAction("Delete Selected Rows", this);
    m_duplicateRowsAction = new QAction("Duplicate Selected Rows", this);
    
    m_contextMenu->addAction(m_insertRowAboveAction);
    m_contextMenu->addAction(m_insertRowBelowAction);
    m_contextMenu->addSeparator();
    m_contextMenu->addAction(m_duplicateRowsAction);
    m_contextMenu->addAction(m_deleteRowsAction);
    m_contextMenu->addSeparator();
    
    m_copyAction = new QAction("Copy", this);
    m_copyAction->setShortcut(QKeySequence::Copy);
    m_pasteAction = new QAction("Paste", this);
    m_pasteAction->setShortcut(QKeySequence::Paste);
    m_clearAction = new QAction("Clear", this);
    m_clearAction->setShortcut(QKeySequence::Delete);
    
    m_contextMenu->addAction(m_copyAction);
    m_contextMenu->addAction(m_pasteAction);
    m_contextMenu->addAction(m_clearAction);
    
    // Connect actions
    connect(m_insertRowAboveAction, &QAction::triggered, this, &CSVTableView::insertRowAbove);
    connect(m_insertRowBelowAction, &QAction::triggered, this, &CSVTableView::insertRowBelow);
    connect(m_deleteRowsAction, &QAction::triggered, this, &CSVTableView::deleteSelectedRows);
    connect(m_duplicateRowsAction, &QAction::triggered, this, &CSVTableView::duplicateSelectedRows);
    connect(m_copyAction, &QAction::triggered, this, &CSVTableView::copySelection);
    connect(m_pasteAction, &QAction::triggered, this, &CSVTableView::pasteSelection);
    connect(m_clearAction, &QAction::triggered, this, &CSVTableView::clearSelection);
}

void CSVTableView::contextMenuEvent(QContextMenuEvent *event)
{
    // Enable/disable actions based on selection
    bool hasSelection = !selectionModel()->selectedIndexes().isEmpty();
    bool hasRowSelection = !selectionModel()->selectedRows().isEmpty();
    
    m_deleteRowsAction->setEnabled(hasRowSelection);
    m_duplicateRowsAction->setEnabled(hasRowSelection);
    m_copyAction->setEnabled(hasSelection);
    m_clearAction->setEnabled(hasSelection);
    
    // Check clipboard for paste action
    const QClipboard *clipboard = QApplication::clipboard();
    const QMimeData *mimeData = clipboard->mimeData();
    m_pasteAction->setEnabled(mimeData->hasText());
    
    m_contextMenu->exec(event->globalPos());
}

void CSVTableView::keyPressEvent(QKeyEvent *event)
{
    if (event->key() == Qt::Key_Delete || event->key() == Qt::Key_Backspace) {
        clearSelection();
        return;
    }
    
    if (event->matches(QKeySequence::Copy)) {
        copySelection();
        return;
    }
    
    if (event->matches(QKeySequence::Paste)) {
        pasteSelection();
        return;
    }
    
    QTableView::keyPressEvent(event);
}

void CSVTableView::setSearchText(const QString &searchText)
{
    m_searchText = searchText.toLower();
    
    // Simple search highlighting - you could extend this with proper filtering
    if (m_searchText.isEmpty()) {
        clearSelection();
        return;
    }
    
    // Find and select all cells containing the search text
    QItemSelection selection;
    for (int row = 0; row < m_csvModel->rowCount(); ++row) {
        for (int col = 0; col < m_csvModel->columnCount(); ++col) {
            QModelIndex index = m_csvModel->index(row, col);
            QString cellText = m_csvModel->data(index).toString().toLower();
            if (cellText.contains(m_searchText)) {
                selection.select(index, index);
            }
        }
    }
    
    selectionModel()->select(selection, QItemSelectionModel::ClearAndSelect);
    
    // Scroll to first match
    if (!selection.isEmpty()) {
        scrollTo(selection.first().topLeft());
    }
}

void CSVTableView::insertRowAbove()
{
    int currentRow = currentIndex().row();
    if (currentRow < 0) currentRow = 0;
    
    m_csvModel->insertRow(currentRow);
    selectRow(currentRow);
}

void CSVTableView::insertRowBelow()
{
    int currentRow = currentIndex().row();
    if (currentRow < 0) currentRow = m_csvModel->rowCount() - 1;
    
    m_csvModel->insertRow(currentRow + 1);
    selectRow(currentRow + 1);
}

void CSVTableView::deleteSelectedRows()
{
    QModelIndexList selectedRows = selectionModel()->selectedRows();
    if (selectedRows.isEmpty()) return;
    
    // Sort rows in descending order to remove from bottom up
    QList<int> rows;
    for (const QModelIndex &index : selectedRows) {
        rows.append(index.row());
    }
    std::sort(rows.rbegin(), rows.rend());
    
    for (int row : rows) {
        m_csvModel->removeRow(row);
    }
}

void CSVTableView::duplicateSelectedRows()
{
    QModelIndexList selectedRows = selectionModel()->selectedRows();
    if (selectedRows.isEmpty()) return;
    
    // Get unique row indices and sort them
    QSet<int> rowSet;
    for (const QModelIndex &index : selectedRows) {
        rowSet.insert(index.row());
    }
    QList<int> rows = rowSet.values();
    std::sort(rows.rbegin(), rows.rend()); // Sort descending
    
    // Duplicate rows from bottom to top to maintain indices
    for (int row : rows) {
        m_csvModel->duplicateRow(row);
    }
}

void CSVTableView::copySelection()
{
    QModelIndexList selectedIndexes = selectionModel()->selectedIndexes();
    if (selectedIndexes.isEmpty()) return;
    
    // Group by rows and sort
    QMap<int, QMap<int, QString>> data;
    for (const QModelIndex &index : selectedIndexes) {
        data[index.row()][index.column()] = m_csvModel->data(index).toString();
    }
    
    // Build clipboard text
    QString clipboardText;
    for (auto rowIt = data.begin(); rowIt != data.end(); ++rowIt) {
        QStringList rowData;
        const QMap<int, QString> &columns = rowIt.value();
        
        int maxCol = columns.lastKey();
        for (int col = 0; col <= maxCol; ++col) {
            rowData.append(columns.value(col, ""));
        }
        
        clipboardText += rowData.join("\t") + "\n";
    }
    
    QApplication::clipboard()->setText(clipboardText);
}

void CSVTableView::pasteSelection()
{
    QModelIndex startIndex = currentIndex();
    if (!startIndex.isValid()) return;
    
    QString clipboardText = QApplication::clipboard()->text();
    if (clipboardText.isEmpty()) return;
    
    QStringList rows = clipboardText.split('\n', Qt::SkipEmptyParts);
    
    for (int i = 0; i < rows.count(); ++i) {
        QStringList columns = rows.at(i).split('\t');
        int targetRow = startIndex.row() + i;
        
        // Insert row if necessary
        while (targetRow >= m_csvModel->rowCount()) {
            m_csvModel->insertRow(m_csvModel->rowCount());
        }
        
        // Paste data
        for (int j = 0; j < columns.count(); ++j) {
            int targetCol = startIndex.column() + j;
            if (targetCol < m_csvModel->columnCount()) {
                QModelIndex targetIndex = m_csvModel->index(targetRow, targetCol);
                m_csvModel->setData(targetIndex, columns.at(j));
            }
        }
    }
    
    resizeColumnsToContent();
}

void CSVTableView::clearSelection()
{
    QModelIndexList selectedIndexes = selectionModel()->selectedIndexes();
    
    for (const QModelIndex &index : selectedIndexes) {
        m_csvModel->setData(index, QString());
    }
}

void CSVTableView::onDataModified()
{
    resizeColumnsToContent();
}

void CSVTableView::resizeColumnsToContent()
{
    resizeColumnsToContents();
    
    // Ensure minimum column width
    for (int i = 0; i < m_csvModel->columnCount(); ++i) {
        if (columnWidth(i) < 80) {
            setColumnWidth(i, 80);
        }
    }
}