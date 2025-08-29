#!/bin/bash

# Hydroponic CSV Editor Launcher
# This script launches the HydroponicCSVEditor executable

echo "🌱 Launching Hydroponic CSV Editor..."
echo "=================================="

# Check if executable exists
if [ ! -f "build/HydroponicCSVEditor" ]; then
    echo "❌ Executable not found! Building first..."
    ./build.sh
    if [ $? -ne 0 ]; then
        echo "❌ Build failed!"
        exit 1
    fi
fi

# Launch the application
echo "🚀 Starting HydroponicCSVEditor..."
./build/HydroponicCSVEditor

echo "👋 HydroponicCSVEditor closed."