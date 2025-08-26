@echo off
echo Building Hydroponic CSV Editor...
echo.

REM Check if build directory exists
if not exist "build" (
    mkdir build
)

cd build

REM Configure with CMake
echo Configuring with CMake...
cmake .. -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release

if %ERRORLEVEL% NEQ 0 (
    echo CMake configuration failed!
    pause
    exit /b 1
)

REM Build the project
echo Building project...
cmake --build . --config Release

if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Executable location: build/HydroponicCSVEditor.exe
echo.
pause