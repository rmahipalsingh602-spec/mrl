# MRL Language Tools

MRL Language Tools is a Visual Studio Code extension for MRL (Multi Runtime Language). It adds language registration, syntax highlighting, snippets, keyword completions, and a command to run `.mrl` and `.hi` files. The runner prefers the installed `mrl` CLI and falls back to the Python runtime when needed.

## Features

- Automatic language detection for `.mrl` and `.hi` files
- Dedicated MRL file icons for `.mrl` and `.hi` files inside VS Code
- TextMate syntax highlighting for MRL keywords, comments, strings, numbers, and operators
- Language configuration with brackets, auto-closing pairs, comments, and indentation rules
- Built-in snippets for print, variables, counted loops, branching, functions, imports, and AI prompts
- Keyword IntelliSense for the MRL language surface
- `Run MRL File` command that executes the current file in the integrated terminal

## Requirements

- Visual Studio Code 1.85 or newer
- Recommended: install the `mrl` CLI so the extension can run files directly
- Fallback: Python available on your PATH, or configure `mrl.pythonPath`
- A fallback MRL runtime entry script, which defaults to `main.py` in the workspace root or an ancestor folder of the active file

## Installation

1. Install the MRL CLI from the repository root:

```bash
python -m pip install .
```

2. Open the `mrl-vscode-extension` folder in Visual Studio Code.
3. Run `npm install`.
4. Press `F5` to launch the Extension Development Host.
5. Open or create an `.mrl` or `.hi` file in the Extension Development Host.
6. If you want the MRL logo on files in Explorer and tabs, choose `Preferences: File Icon Theme` and select `MRL File Icons`.

## Usage

### Syntax highlighting

Create a file such as `hello.mrl` or `page.hi` and VS Code will automatically use the MRL grammar.

### File logo and icons

To make `.mrl` and `.hi` files show the MRL logo in VS Code:

1. Open `Preferences: File Icon Theme`
2. Select `MRL File Icons`

After that, files such as `index.mrl`, `main.mrl`, `home.hi`, and `page.hi` will use the MRL logo.

### IntelliSense and snippets

Type `Ctrl+Space` in an `.mrl` or `.hi` file to see MRL keyword completions. Type snippet prefixes like `print`, `loop`, `func`, or `ai` to insert common structures.

### Run MRL File

1. Open an `.mrl` or `.hi` file.
2. Run `MRL: Run MRL File` from the Command Palette, or click `Run MRL File` from the editor title.
3. The extension tries:

```bash
mrl <current-file>
```

4. If the MRL CLI is not available, it falls back to:

```bash
python main.py <current-file>
```

The command is executed inside the integrated terminal and uses the containing workspace folder as the working directory.

## Troubleshooting

- If the language mode does not switch automatically, run `Change Language Mode` and choose `MRL`.
- If the run command does not appear, reload the VS Code window after installing the extension.
- If Windows shows the file but not the MRL icon, reinstall the MRL setup so the file association for `.mrl` and `.hi` is written again.
- If the `Open in VS Code` right-click action fails on Windows, open VS Code once and enable the `code` shell command on PATH.

## Settings

- `mrl.commandPath`: Installed MRL CLI to use first. Default: `mrl`
- `mrl.pythonPath`: Python executable used to launch MRL files. Default: `python`
- `mrl.runtimeScript`: Fallback path to the MRL runtime script. Default: `main.py`

## Example

```mrl
mrl rakho launch_ready = sach

mrl agar launch_ready aur nahi jhooth
    mrl bolo "MRL 3.1 ready"
warna
    mrl bolo "Hold launch"
khatam

mrl gino wave = 1 se 5 kadam 2
    mrl bolo "Wave " + wave
khatam
```

## File Structure

```text
mrl-vscode-extension/
|-- .vscode/
|   |-- launch.json
|-- package.json
|-- extension.js
|-- language-configuration.json
|-- syntaxes/
|   |-- mrl.tmLanguage.json
|-- snippets/
|   |-- mrl.json
|-- README.md
```
