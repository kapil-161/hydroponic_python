#include <QApplication>
#include <QStyleFactory>
#include <QDir>
#include "mainwindow.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    
    app.setApplicationName("Hydroponic CSV Editor");
    app.setApplicationVersion("1.0.0");
    app.setOrganizationName("Hydroponic Systems");
    
    // Set application icon and style
    app.setStyle(QStyleFactory::create("Fusion"));
    
    MainWindow window;
    window.show();
    
    return app.exec();
}