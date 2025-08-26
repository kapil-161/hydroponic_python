cmake_minimum_required(VERSION 3.16)
project(HydroponicCSVEditor VERSION 1.0.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets Charts)

qt6_standard_project_setup()

set(SOURCES
    main.cpp
    mainwindow.cpp
    csvtablemodel.cpp
    csvtableview.cpp
    hierarchicalfilemodel.cpp
    timeseriesplotwidget.cpp
)

set(HEADERS
    mainwindow.h
    csvtablemodel.h
    csvtableview.h
    hierarchicalfilemodel.h
    timeseriesplotwidget.h
)

qt6_add_executable(HydroponicCSVEditor ${SOURCES} ${HEADERS})

target_link_libraries(HydroponicCSVEditor 
    PRIVATE Qt6::Core Qt6::Widgets Qt6::Charts)

if(WIN32)
    set_property(TARGET HydroponicCSVEditor PROPERTY WIN32_EXECUTABLE TRUE)
endif()