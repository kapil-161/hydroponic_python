#ifndef CSVTABLEVIEW_H
#define CSVTABLEVIEW_H

#include <QTableView>
#include <QHeaderView>
#include <QMenu>
#include <QAction>
#include <QContextMenuEvent>
#include <QKeyEvent>
#include "csvtablemodel.h"

class CSVTableView : public QTableView
{
    Q_OBJECT

public:
    explicit CSVTableView(QWidget *parent = nullptr);
    ~CSVTableView();
    
    CSVTableModel* csvModel() const { return m_csvModel; }
    void setSearchText(const QString &searchText);

protected:
    void contextMenuEvent(QContextMenuEvent *event) override;
    void keyPressEvent(QKeyEvent *event) override;

private slots:
    void insertRowAbove();
    void insertRowBelow();
    void deleteSelectedRows();
    void duplicateSelectedRows();
    void copySelection();
    void pasteSelection();
    void clearSelection();
    void onDataModified();

private:
    void setupModel();
    void setupView();
    void createContextMenu();
    void resizeColumnsToContent();
    
    CSVTableModel *m_csvModel;
    QMenu *m_contextMenu;
    
    QAction *m_insertRowAboveAction;
    QAction *m_insertRowBelowAction;
    QAction *m_deleteRowsAction;
    QAction *m_duplicateRowsAction;
    QAction *m_copyAction;
    QAction *m_pasteAction;
    QAction *m_clearAction;
    
    QString m_searchText;
};

#endif // CSVTABLEVIEW_H