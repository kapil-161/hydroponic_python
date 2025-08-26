#ifndef HIERARCHICALFILEMODEL_H
#define HIERARCHICALFILEMODEL_H

#include <QAbstractItemModel>
#include <QDir>
#include <QModelIndex>
#include <QVariant>
#include <QStringList>
#include <QMap>
#include <QVector>

class TreeItem
{
public:
    explicit TreeItem(const QString &data, const QString &filePath = QString(), TreeItem *parentItem = nullptr);
    ~TreeItem();

    void appendChild(TreeItem *child);
    TreeItem *child(int row);
    int childCount() const;
    int columnCount() const;
    QString data() const;
    QString filePath() const;
    int row() const;
    TreeItem *parentItem();
    void setFilePath(const QString &filePath);

private:
    QVector<TreeItem*> m_childItems;
    QString m_itemData;
    QString m_filePath;
    TreeItem *m_parentItem;
};

class HierarchicalFileModel : public QAbstractItemModel
{
    Q_OBJECT

public:
    explicit HierarchicalFileModel(const QString &inputDirectory, QObject *parent = nullptr);
    ~HierarchicalFileModel();

    // QAbstractItemModel interface
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    Qt::ItemFlags flags(const QModelIndex &index) const override;
    QVariant headerData(int section, Qt::Orientation orientation, int role = Qt::DisplayRole) const override;
    QModelIndex index(int row, int column, const QModelIndex &parent = QModelIndex()) const override;
    QModelIndex parent(const QModelIndex &index) const override;
    int rowCount(const QModelIndex &parent = QModelIndex()) const override;
    int columnCount(const QModelIndex &parent = QModelIndex()) const override;

    // Custom methods
    void refreshModel();
    QString getFilePath(const QModelIndex &index) const;
    bool isFile(const QModelIndex &index) const;

private:
    void setupModelData();
    void parseCSVFiles();
    QString formatTopicName(const QString &topic) const;
    
    TreeItem *m_rootItem;
    QString m_inputDirectory;
    
    // Structure: Crop -> Experiment -> Topic -> File
    QMap<QString, QMap<QString, QMap<QString, QStringList>>> m_fileStructure;
};

#endif // HIERARCHICALFILEMODEL_H