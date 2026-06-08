// =============================================================
// NEKOVA Language — VS Code Extension Entry Point
// =============================================================
// This file activates the NEKOVA VS Code extension.
// Syntax highlighting is handled by the tmLanguage grammar.
// This file adds extra features like commands and snippets.

const vscode = require('vscode');

function activate(context) {
    console.log('NEKOVA Language extension activated!');

    // ── Register NEKOVA Run command ─────────────────────────
    let runCommand = vscode.commands.registerCommand(
        'aion.runFile',
        function() {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showErrorMessage(
                    'No active NEKOVA file to run.');
                return;
            }

            const filepath = editor.document.fileName;
            if (!filepath.endsWith('.aion')) {
                vscode.window.showErrorMessage(
                    'This is not an NEKOVA file.');
                return;
            }

            // Run in terminal
            const terminal = vscode.window.createTerminal(
                'NEKOVA');
            terminal.show();
            terminal.sendText(
                `python main.py "${filepath}"`);
        }
    );

    // ── Register NEKOVA REPL command ────────────────────────
    let replCommand = vscode.commands.registerCommand(
        'aion.openRepl',
        function() {
            const terminal = vscode.window.createTerminal(
                'NEKOVA REPL');
            terminal.show();
            terminal.sendText('python main.py repl');
        }
    );

    // ── Status bar item ───────────────────────────────────
    const statusBar = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Left, 100);
    statusBar.text = '$(zap) NEKOVA';
    statusBar.tooltip = 'NEKOVA Language v1.0.0';
    statusBar.command = 'aion.runFile';

    // Show status bar for .aion files
    vscode.window.onDidChangeActiveTextEditor(editor => {
        if (editor &&
            editor.document.fileName.endsWith('.aion')) {
            statusBar.show();
        } else {
            statusBar.hide();
        }
    });

    context.subscriptions.push(
        runCommand,
        replCommand,
        statusBar
    );
}

function deactivate() {}

module.exports = { activate, deactivate };