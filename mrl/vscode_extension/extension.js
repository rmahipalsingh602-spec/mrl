const vscode = require('vscode');

const logo = [
  '███╗   ███╗██████╗ ██╗',
  '████╗ ████║██╔══██╗██║',
  '██╔████╔██║██████╔╝██║',
  '██║╚██╔╝██║██╔══██╗██║',
  '██║ ╚═╝ ██║██║  ██║███████╗',
  '╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝',
  'Neon Tri-Core :: Multi Runtime Language'
].join('\n');

function activate(context) {
  const showLogo = vscode.commands.registerCommand('mrl.showLogo', async () => {
    const document = await vscode.workspace.openTextDocument({
      language: 'plaintext',
      content: logo
    });
    await vscode.window.showTextDocument(document, { preview: false });
  });

  context.subscriptions.push(showLogo);
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
};