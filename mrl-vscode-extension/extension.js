const fs = require('fs');
const path = require('path');
const vscode = require('vscode');

const DOCUMENT_SELECTOR = [{ language: 'mrl' }];
const SUPPORTED_FILE_EXTENSIONS = new Set(['.mrl', '.hi']);
const STATEMENT_KEYWORDS = new Set(['bolo', 'rakho', 'agar', 'jab', 'gino', 'function', 'call', 'import', 'install', 'ai', 'ui']);
const KEYWORD_DEFINITIONS = [
  ['mrl', 'Statement prefix', 'Prefix required at the start of executable MRL statements.'],
  ['bolo', 'Print statement', 'Prints the value of an expression.'],
  ['rakho', 'Variable assignment', 'Assigns a value to a variable.'],
  ['agar', 'Conditional block', 'Starts an if block.'],
  ['warna', 'Else branch', 'Starts the fallback branch of an if block.'],
  ['jab', 'Loop block', 'Starts a loop and is followed by tak.'],
  ['tak', 'Loop keyword', 'Completes the loop header in `mrl jab tak ...`.'],
  ['gino', 'Counted loop', 'Runs a counted loop such as `mrl gino i = 1 se 5` with an optional step.'],
  ['se', 'Range keyword', 'Connects the start and end values in a counted loop.'],
  ['kadam', 'Step keyword', 'Adds a custom step to a counted loop.'],
  ['khatam', 'Block terminator', 'Closes `agar`, `jab tak`, and `function` blocks.'],
  ['function', 'Function declaration', 'Declares a reusable function.'],
  ['call', 'Function call', 'Calls a previously declared function.'],
  ['import', 'Module import', 'Imports another MRL module.'],
  ['install', 'Package install', 'Installs an MRL package through the runtime.'],
  ['ai', 'AI command', 'Runs an AI prompt through the MRL AI runtime.'],
  ['sach', 'Boolean true', 'Represents the boolean value true.'],
  ['jhooth', 'Boolean false', 'Represents the boolean value false.'],
  ['aur', 'Logical and', 'Combines two conditions with logical AND.'],
  ['ya', 'Logical or', 'Combines two conditions with logical OR.'],
  ['nahi', 'Logical not', 'Negates the truthiness of a value or condition.'],
  ['ui', 'UI block', 'Starts an MRL UI declaration block.'],
  ['window', 'UI window', 'Used after `mrl ui` to define a window.'],
  ['button', 'UI element', 'Creates a button inside a UI window block.'],
  ['text', 'UI element', 'Creates a text label inside a UI window block.'],
  ['end', 'UI terminator', 'Closes a `ui window` block.']
];
const TRIGGER_CHARACTERS = Array.from('abcdefghijklmnopqrstuvwxyz_');

function activate(context) {
  const completionProvider = vscode.languages.registerCompletionItemProvider(
    DOCUMENT_SELECTOR,
    {
      provideCompletionItems(document, position) {
        const range = document.getWordRangeAtPosition(position, /[A-Za-z_][A-Za-z0-9_]*/);
        const prefix = range ? document.getText(range).toLowerCase() : '';
        const linePrefix = document.lineAt(position.line).text.slice(0, position.character);
        const inMrlStatement = /^\s*mrl\s+[A-Za-z_]*$/.test(linePrefix);

        const items = KEYWORD_DEFINITIONS
          .filter(([label]) => !prefix || label.startsWith(prefix))
          .filter(([label]) => {
            if (inMrlStatement) {
              return STATEMENT_KEYWORDS.has(label);
            }
            return true;
          })
          .map(([label, detail, documentation]) => {
            const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Keyword);
            item.detail = detail;
            item.documentation = new vscode.MarkdownString(documentation);
            item.insertText = label;
            item.range = range;
            item.sortText = `0_${label}`;
            return item;
          });

        if (!prefix && /^\s*$/.test(linePrefix)) {
          const statementItem = new vscode.CompletionItem('mrl statement', vscode.CompletionItemKind.Snippet);
          statementItem.detail = 'Start a new MRL statement';
          statementItem.insertText = new vscode.SnippetString('mrl ${1:bolo "Hello"}');
          statementItem.documentation = new vscode.MarkdownString('Inserts the `mrl` statement prefix with a starter command.');
          statementItem.sortText = '1_statement';
          items.push(statementItem);
        }

        return items;
      }
    },
    ...TRIGGER_CHARACTERS
  );

  const runCommand = vscode.commands.registerCommand('mrl.runFile', async (uri) => {
    await runMrlFile(uri);
  });

  context.subscriptions.push(completionProvider, runCommand);
}

async function runMrlFile(uri) {
  const targetUri = await resolveTargetUri(uri);
  if (!targetUri) {
    vscode.window.showErrorMessage('Open an .mrl or .hi file or select one in the explorer to run it.');
    return;
  }

  if (targetUri.scheme !== 'file') {
    vscode.window.showErrorMessage('Only files on disk can be executed by the MRL runner.');
    return;
  }

  const fileExtension = path.extname(targetUri.fsPath).toLowerCase();
  if (!SUPPORTED_FILE_EXTENSIONS.has(fileExtension)) {
    vscode.window.showErrorMessage('Run MRL File only supports .mrl or .hi files.');
    return;
  }

  const document = await vscode.workspace.openTextDocument(targetUri);
  if (document.isDirty) {
    const saved = await document.save();
    if (!saved) {
      vscode.window.showWarningMessage('Save the active .mrl or .hi file before running it.');
      return;
    }
  }

  const workspaceFolder = vscode.workspace.getWorkspaceFolder(targetUri);
  if (!workspaceFolder) {
    vscode.window.showErrorMessage('Open the folder that contains your MRL project before running a file.');
    return;
  }

  const executionTarget = await resolveExecutionTarget(workspaceFolder, targetUri);
  if (!executionTarget) {
    return;
  }

  const task = createRunTask(workspaceFolder, executionTarget.command, executionTarget.args, targetUri.fsPath);
  await vscode.tasks.executeTask(task);
}

async function resolveTargetUri(uri) {
  if (uri instanceof vscode.Uri) {
    return uri;
  }

  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    return undefined;
  }

  return editor.document.uri;
}

async function resolveExecutionTarget(workspaceFolder, targetUri) {
  const cliCommand = resolveCliCommand(targetUri);
  if (cliCommand) {
    return {
      command: cliCommand,
      args: [targetUri.fsPath]
    };
  }

  const runtimeScript = await resolveRuntimeScript(workspaceFolder, targetUri);
  if (!runtimeScript) {
    return undefined;
  }

  const pythonCommand = resolvePythonCommand(targetUri);
  if (!findExecutableOnPath(pythonCommand)) {
    const action = await vscode.window.showErrorMessage(
      'Unable to find the MRL CLI or a usable Python interpreter. Install `mrl` on PATH or configure the fallback settings.',
      'Open Settings'
    );
    if (action === 'Open Settings') {
      await vscode.commands.executeCommand('workbench.action.openSettings', 'mrl.commandPath');
    }
    return undefined;
  }

  return {
    command: pythonCommand,
    args: [runtimeScript, targetUri.fsPath]
  };
}

async function resolveRuntimeScript(workspaceFolder, targetUri) {
  const configuration = vscode.workspace.getConfiguration('mrl', targetUri);
  const configuredPath = configuration.get('runtimeScript', 'main.py').trim();
  const candidatePaths = [];

  if (path.isAbsolute(configuredPath)) {
    candidatePaths.push(configuredPath);
  } else {
    candidatePaths.push(path.join(workspaceFolder.uri.fsPath, configuredPath));
  }

  if (configuredPath === 'main.py') {
    const discovered = findUpwards(path.dirname(targetUri.fsPath), workspaceFolder.uri.fsPath, 'main.py');
    if (discovered && !candidatePaths.includes(discovered)) {
      candidatePaths.push(discovered);
    }
  }

  const runtimeScript = candidatePaths.find((candidate) => fs.existsSync(candidate));
  if (runtimeScript) {
    return runtimeScript;
  }

  const action = await vscode.window.showErrorMessage(
    `Unable to locate the MRL runtime script. Expected ${configuredPath}.`,
    'Open Settings'
  );
  if (action === 'Open Settings') {
    await vscode.commands.executeCommand('workbench.action.openSettings', 'mrl.runtimeScript');
  }

  return undefined;
}

function resolveCliCommand(targetUri) {
  const configuration = vscode.workspace.getConfiguration('mrl', targetUri);
  const configuredCommand = stripWrappingQuotes(configuration.get('commandPath', 'mrl').trim());
  if (!configuredCommand) {
    return undefined;
  }

  return findExecutableOnPath(configuredCommand) ? configuredCommand : undefined;
}

function resolvePythonCommand(targetUri) {
  const mrlConfiguration = vscode.workspace.getConfiguration('mrl', targetUri);
  const configuredPython = stripWrappingQuotes(mrlConfiguration.get('pythonPath', '').trim());
  if (configuredPython) {
    return configuredPython;
  }

  const pythonConfiguration = vscode.workspace.getConfiguration('python', targetUri);
  const pythonExtensionValue = stripWrappingQuotes(String(pythonConfiguration.get('defaultInterpreterPath', '') || '').trim());
  return pythonExtensionValue || 'python';
}

function createRunTask(workspaceFolder, command, args, filePath) {
  const execution = new vscode.ShellExecution(command, args, {
    cwd: workspaceFolder.uri.fsPath
  });
  const task = new vscode.Task(
    { type: 'mrl', action: 'runFile', file: path.basename(filePath) },
    workspaceFolder,
    `Run ${path.basename(filePath)}`,
    'MRL',
    execution
  );

  task.presentationOptions = {
    reveal: vscode.TaskRevealKind.Always,
    panel: vscode.TaskPanelKind.Dedicated,
    clear: true,
    showReuseMessage: false,
    focus: true
  };

  return task;
}

function stripWrappingQuotes(value) {
  if (value.startsWith('"') && value.endsWith('"')) {
    return value.slice(1, -1);
  }
  return value;
}

function findExecutableOnPath(command) {
  const trimmedCommand = stripWrappingQuotes(String(command || '').trim());
  if (!trimmedCommand) {
    return undefined;
  }

  if (path.isAbsolute(trimmedCommand)) {
    return fs.existsSync(trimmedCommand) ? trimmedCommand : undefined;
  }

  if (trimmedCommand.includes(path.sep) || trimmedCommand.includes(path.posix.sep)) {
    const resolvedPath = path.resolve(trimmedCommand);
    return fs.existsSync(resolvedPath) ? resolvedPath : undefined;
  }

  const pathEntries = String(process.env.PATH || '')
    .split(path.delimiter)
    .map((entry) => stripWrappingQuotes(entry.trim()))
    .filter(Boolean);

  for (const pathEntry of pathEntries) {
    for (const candidate of candidateExecutableNames(trimmedCommand)) {
      const resolvedCandidate = path.join(pathEntry, candidate);
      if (fs.existsSync(resolvedCandidate)) {
        return resolvedCandidate;
      }
    }
  }

  return undefined;
}

function candidateExecutableNames(command) {
  if (path.extname(command)) {
    return [command];
  }

  if (process.platform !== 'win32') {
    return [command];
  }

  const extensions = String(process.env.PATHEXT || '.EXE;.CMD;.BAT;.COM')
    .split(';')
    .map((extension) => extension.trim().toLowerCase())
    .filter(Boolean);

  return [command, ...extensions.map((extension) => `${command}${extension}`)];
}

function findUpwards(startDirectory, stopDirectory, fileName) {
  let currentDirectory = path.resolve(startDirectory);
  const resolvedStop = path.resolve(stopDirectory);

  while (currentDirectory.startsWith(resolvedStop)) {
    const candidate = path.join(currentDirectory, fileName);
    if (fs.existsSync(candidate)) {
      return candidate;
    }

    if (currentDirectory === resolvedStop) {
      break;
    }

    const parent = path.dirname(currentDirectory);
    if (parent === currentDirectory) {
      break;
    }
    currentDirectory = parent;
  }

  return undefined;
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
