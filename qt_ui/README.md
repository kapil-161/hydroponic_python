# Hydroponic CSV Editor

A Qt6-based GUI application for editing CSV configuration files for the hydroponic simulation system.

## Features

- **CSV File Explorer**: Browse and open CSV files from the input directory
- **Direct CSV Editing**: Edit CSV data in a spreadsheet-like interface
- **Row Operations**: Add, remove, duplicate rows with ease
- **Duplicate Detection**: Find and highlight duplicate rows
- **Search Functionality**: Search across all cells in the table
- **Batch File Generation**: Create batch files to run simulations
- **Simulation Runner**: Execute Python simulations directly from the GUI
- **Context Menu**: Right-click operations for efficient editing
- **Keyboard Shortcuts**: Copy, paste, delete operations

## Prerequisites

- Qt 6.9.1 or later
- MinGW (Windows) or GCC (Linux/macOS)
- CMake 3.16 or later
- Python 3.x (for running simulations)

## Building

### Windows (with MinGW)
1. Open Command Prompt in the `qt_ui` directory
2. Run: `build.bat`
3. The executable will be created in `build/HydroponicCSVEditor.exe`

### Linux/macOS
1. Open terminal in the `qt_ui` directory
2. Run: `./build.sh`
3. The executable will be created in `build/HydroponicCSVEditor`

### Manual Build
```bash
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
```

## Usage

1. **Launch the Application**: Run the executable
2. **Open CSV Files**: 
   - Use the file explorer on the left to browse CSV files
   - Double-click to open a file
   - Or use File → Open from the menu
3. **Edit Data**:
   - Double-click cells to edit
   - Use right-click context menu for row operations
   - Use Ctrl+C/Ctrl+V for copy/paste
   - Use the search bar to find specific data
4. **Save Changes**: Use File → Save or Ctrl+S
5. **Generate Batch Files**:
   - Configure experiment settings in the bottom panel
   - Click "Generate Batch File"
   - Click "Run Simulation" to execute

## Keyboard Shortcuts

- **Ctrl+N**: New file
- **Ctrl+O**: Open file
- **Ctrl+S**: Save file
- **Ctrl+Shift+S**: Save as
- **Ctrl+C**: Copy selection
- **Ctrl+V**: Paste
- **Delete**: Clear selection
- **Ctrl+Q**: Exit application

## File Structure

- `main.cpp`: Application entry point
- `mainwindow.*`: Main window implementation
- `csvtablemodel.*`: CSV data model
- `csvtableview.*`: Enhanced table view widget
- `CMakeLists.txt`: Build configuration
- `build.*`: Build scripts

## CSV File Format

The application supports standard CSV format:
- First row contains headers
- Comma-separated values
- Quoted fields for values containing commas or quotes
- UTF-8 encoding

## Troubleshooting

### Build Issues
- Ensure Qt6 is properly installed and in PATH
- Check that CMake can find Qt6: `cmake --find-package Qt6 Core`
- On Windows, ensure MinGW is in PATH

### Runtime Issues
- Verify all Qt6 DLLs are accessible
- Check that the `input` directory exists in the project root
- Ensure Python is accessible for simulation execution

## Configuration

The application automatically detects the `input` directory containing CSV files. You can modify the default path in `mainwindow.cpp` if needed.

## Simulation Integration

The application integrates with the existing Python simulation system:
- Generates platform-specific batch files (.bat for Windows, .sh for Unix)
- Executes `cropgro_cli.py` with appropriate parameters
- Displays simulation progress and results