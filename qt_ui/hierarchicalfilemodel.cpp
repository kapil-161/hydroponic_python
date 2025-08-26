#include "hierarchicalfilemodel.h"
#include <QDir>
#include <QFileInfo>
#include <QRegularExpression>
#include <QIcon>
#include <QApplication>
#include <QStyle>

// TreeItem implementation
TreeItem::TreeItem(const QString &data, const QString &filePath, TreeItem *parent)
    : m_itemData(data), m_filePath(filePath), m_parentItem(parent)
{
}

TreeItem::~TreeItem()
{
    qDeleteAll(m_childItems);
}

void TreeItem::appendChild(TreeItem *item)
{
    m_childItems.append(item);
}

TreeItem *TreeItem::child(int row)
{
    if (row < 0 || row >= m_childItems.size())
        return nullptr;
    return m_childItems.at(row);
}

int TreeItem::childCount() const
{
    return m_childItems.count();
}

int TreeItem::columnCount() const
{
    return 1; // Only one column for the tree
}

QString TreeItem::data() const
{
    return m_itemData;
}

QString TreeItem::filePath() const
{
    return m_filePath;
}

TreeItem *TreeItem::parentItem()
{
    return m_parentItem;
}

int TreeItem::row() const
{
    if (m_parentItem)
        return m_parentItem->m_childItems.indexOf(const_cast<TreeItem*>(this));
    return 0;
}

void TreeItem::setFilePath(const QString &filePath)
{
    m_filePath = filePath;
}

// HierarchicalFileModel implementation
HierarchicalFileModel::HierarchicalFileModel(const QString &inputDirectory, QObject *parent)
    : QAbstractItemModel(parent), m_inputDirectory(inputDirectory)
{
    m_rootItem = new TreeItem("Root");
    setupModelData();
}

HierarchicalFileModel::~HierarchicalFileModel()
{
    delete m_rootItem;
}

QVariant HierarchicalFileModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid())
        return QVariant();

    TreeItem *item = static_cast<TreeItem*>(index.internalPointer());

    if (role == Qt::DisplayRole) {
        return item->data();
    } else if (role == Qt::DecorationRole) {
        // Add icons based on level
        TreeItem *parent = item->parentItem();
        if (!parent || parent == m_rootItem) {
            // Crop level - use crop icons
            if (item->data().startsWith("LET")) return QIcon("📥"); // Lettuce
            if (item->data().startsWith("TOM")) return QIcon("🍅"); // Tomato
            if (item->data().startsWith("BAS")) return QIcon("🌿"); // Basil
        } else if (parent->parentItem() == m_rootItem) {
            // Experiment level
            return QIcon("🧪");
        } else if (parent->parentItem() && parent->parentItem()->parentItem() == m_rootItem) {
            // Topic level
            return QIcon("📂");
        } else {
            // File level
            return QIcon("📄");
        }
    }

    return QVariant();
}

Qt::ItemFlags HierarchicalFileModel::flags(const QModelIndex &index) const
{
    if (!index.isValid())
        return Qt::NoItemFlags;

    return QAbstractItemModel::flags(index);
}

QVariant HierarchicalFileModel::headerData(int section, Qt::Orientation orientation, int role) const
{
    if (orientation == Qt::Horizontal && role == Qt::DisplayRole && section == 0)
        return "Hydroponic Configuration Files";

    return QVariant();
}

QModelIndex HierarchicalFileModel::index(int row, int column, const QModelIndex &parent) const
{
    if (!hasIndex(row, column, parent))
        return QModelIndex();

    TreeItem *parentItem;
    if (!parent.isValid())
        parentItem = m_rootItem;
    else
        parentItem = static_cast<TreeItem*>(parent.internalPointer());

    TreeItem *childItem = parentItem->child(row);
    if (childItem)
        return createIndex(row, column, childItem);
    else
        return QModelIndex();
}

QModelIndex HierarchicalFileModel::parent(const QModelIndex &index) const
{
    if (!index.isValid())
        return QModelIndex();

    TreeItem *childItem = static_cast<TreeItem*>(index.internalPointer());
    TreeItem *parentItem = childItem->parentItem();

    if (parentItem == m_rootItem)
        return QModelIndex();

    return createIndex(parentItem->row(), 0, parentItem);
}

int HierarchicalFileModel::rowCount(const QModelIndex &parent) const
{
    TreeItem *parentItem;
    if (parent.column() > 0)
        return 0;

    if (!parent.isValid())
        parentItem = m_rootItem;
    else
        parentItem = static_cast<TreeItem*>(parent.internalPointer());

    return parentItem->childCount();
}

int HierarchicalFileModel::columnCount(const QModelIndex &parent) const
{
    Q_UNUSED(parent)
    return 1;
}

void HierarchicalFileModel::refreshModel()
{
    beginResetModel();
    delete m_rootItem;
    m_rootItem = new TreeItem("Root");
    m_fileStructure.clear();
    setupModelData();
    endResetModel();
}

QString HierarchicalFileModel::getFilePath(const QModelIndex &index) const
{
    if (!index.isValid())
        return QString();

    TreeItem *item = static_cast<TreeItem*>(index.internalPointer());
    return item->filePath();
}

bool HierarchicalFileModel::isFile(const QModelIndex &index) const
{
    if (!index.isValid())
        return false;

    TreeItem *item = static_cast<TreeItem*>(index.internalPointer());
    return !item->filePath().isEmpty() && QFileInfo(item->filePath()).isFile();
}

void HierarchicalFileModel::setupModelData()
{
    parseCSVFiles();
    
    // Build tree structure: Crop -> Experiment -> Topic -> File
    for (auto cropIt = m_fileStructure.begin(); cropIt != m_fileStructure.end(); ++cropIt) {
        const QString &crop = cropIt.key();
        TreeItem *cropItem = new TreeItem(crop, QString(), m_rootItem);
        m_rootItem->appendChild(cropItem);
        
        const auto &experiments = cropIt.value();
        for (auto expIt = experiments.begin(); expIt != experiments.end(); ++expIt) {
            const QString &experiment = expIt.key();
            TreeItem *expItem = new TreeItem(experiment, QString(), cropItem);
            cropItem->appendChild(expItem);
            
            const auto &topics = expIt.value();
            for (auto topicIt = topics.begin(); topicIt != topics.end(); ++topicIt) {
                const QString &topic = topicIt.key();
                QString formattedTopic = formatTopicName(topic);
                TreeItem *topicItem = new TreeItem(formattedTopic, QString(), expItem);
                expItem->appendChild(topicItem);
                
                const QStringList &files = topicIt.value();
                for (const QString &file : files) {
                    QString fileName = QFileInfo(file).baseName();
                    QString fullPath = QDir(m_inputDirectory).filePath(file);
                    TreeItem *fileItem = new TreeItem(fileName, fullPath, topicItem);
                    topicItem->appendChild(fileItem);
                }
            }
        }
    }
}

void HierarchicalFileModel::parseCSVFiles()
{
    QDir dir(m_inputDirectory);
    if (!dir.exists()) {
        return;
    }
    
    QStringList csvFiles = dir.entryList(QStringList() << "*.csv", QDir::Files);
    
    // Pattern: CROP_EXPERIMENT_TOPIC.csv
    QRegularExpression re("^([A-Z]{3})_([A-Z0-9_]+)_(.+)\\.csv$");
    
    for (const QString &file : csvFiles) {
        QRegularExpressionMatch match = re.match(file);
        if (match.hasMatch()) {
            QString crop = match.captured(1);
            QString experiment = match.captured(2);
            QString topic = match.captured(3);
            
            m_fileStructure[crop][experiment][topic].append(file);
        }
    }
}

QString HierarchicalFileModel::formatTopicName(const QString &topic) const
{
    // Convert snake_case to Title Case
    QStringList words = topic.split('_');
    QStringList formattedWords;
    
    for (const QString &word : words) {
        if (!word.isEmpty()) {
            QString formatted = word.toLower();
            formatted[0] = formatted[0].toUpper();
            formattedWords.append(formatted);
        }
    }
    
    return formattedWords.join(' ');
}