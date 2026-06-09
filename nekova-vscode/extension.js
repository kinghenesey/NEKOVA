// =============================================================
// NEKOVA Language — VS Code Extension Entry Point
// =============================================================
// This file activates the NEKOVA VS Code extension.
// Syntax highlighting is handled by the tmLanguage grammar.
// This file adds extra features like commands and snippets.

const vscode = require('vscode');

function activate(context) {
    console.log('NEKOVA Language extension activated!');

    // ── Register NEKOVA Run command ───────────────────────
    let runCommand = vscode.commands.registerCommand(
        'nekova.runFile',
        function() {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showErrorMessage(
                    'No active NEKOVA file to run.');
                return;
            }

            const filepath = editor.document.fileName;
            if (!filepath.endsWith('.nk')) {
                vscode.window.showErrorMessage(
                    'This is not a NEKOVA (.nk) file.');
                return;
            }

            // Run in terminal
            const terminal = vscode.window.createTerminal(
                'NEKOVA');
            terminal.show();
            terminal.sendText(
                `nekova "${filepath}"`);
        }
    );

    // ── Register NEKOVA REPL command ──────────────────────
    let replCommand = vscode.commands.registerCommand(
        'nekova.openRepl',
        function() {
            const terminal = vscode.window.createTerminal(
                'NEKOVA REPL');
            terminal.show();
            terminal.sendText('nekova repl');
        }
    );

    // ── Status bar item ───────────────────────────────────
    const statusBar = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Left, 100);
    statusBar.text = '$(zap) NEKOVA';
    statusBar.tooltip = 'NEKOVA Language v1.1.0 — Connected Forge by SYNEKCOT Tech';
    statusBar.command = 'nekova.runFile';

    // Show status bar for .nk files
    vscode.window.onDidChangeActiveTextEditor(editor => {
        if (editor &&
            editor.document.fileName.endsWith('.nk')) {
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
