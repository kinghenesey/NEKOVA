// =============================================================
// NEKOVA Language — VS Code Extension  (v1.9.5)
// =============================================================
// Commands:
//   nekova.runFile     F5          Run the active .nk file
//   nekova.runWatch    Ctrl+F5     Run with --watch (auto-rerun)
//   nekova.openRepl                Open NEKOVA REPL
//   nekova.fmtFile     Shift+Alt+F Format active file
//   nekova.checkFile               Lint active file
//   nekova.testFile                Run active file (executes test/expect blocks)
//   nekova.debugFile                Debug active file
//   nekova.newProject              Scaffold a new project

const vscode = require('vscode');

// ── Helpers ────────────────────────────────────────────────────────────────

function getPython() {
    const config = vscode.workspace.getConfiguration('nekova');
    return config.get('pythonPath', 'python');
}

function getActiveNkFile(showError = true) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        if (showError) vscode.window.showErrorMessage('No active file open.');
        return null;
    }
    const filepath = editor.document.fileName;
    if (!filepath.endsWith('.nk')) {
        if (showError) vscode.window.showErrorMessage('This is not a NEKOVA (.nk) file.');
        return null;
    }
    return filepath;
}

function getOrCreateTerminal(name) {
    // Reuse existing terminal if open
    for (const t of vscode.window.terminals) {
        if (t.name === name) {
            t.show();
            return t;
        }
    }
    const terminal = vscode.window.createTerminal(name);
    terminal.show();
    return terminal;
}

function quoteArg(s) {
    // Cross-platform quoting — wrap in double quotes, escape inner quotes
    return '"' + s.replace(/"/g, '\\"') + '"';
}

// ── Commands ───────────────────────────────────────────────────────────────

function cmdRunFile() {
    const filepath = getActiveNkFile();
    if (!filepath) return;
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA Run');
    terminal.sendText(`${py} -m nekova run ${quoteArg(filepath)}`);
}

function cmdRunWatch() {
    const filepath = getActiveNkFile();
    if (!filepath) return;
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA Watch');
    terminal.sendText(`${py} -m nekova run ${quoteArg(filepath)} --watch`);
}

function cmdOpenRepl() {
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA REPL');
    terminal.sendText(`${py} -m nekova repl`);
}

async function cmdFmtFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;
    const filepath = editor.document.fileName;
    if (!filepath.endsWith('.nk')) {
        vscode.window.showErrorMessage('This is not a NEKOVA (.nk) file.');
        return;
    }
    // Save first
    await editor.document.save();
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA');
    terminal.sendText(`${py} -m nekova fmt ${quoteArg(filepath)}`);
}

function cmdCheckFile() {
    const filepath = getActiveNkFile();
    if (!filepath) return;
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA Check');
    terminal.sendText(`${py} -m nekova check ${quoteArg(filepath)}`);
}

function cmdTestFile() {
    // NEKOVA has no separate "test a single file" CLI mode — test/expect
    // blocks inside a .nk file execute automatically as part of normal
    // interpretation, so this runs the file the same way runFile does.
    // It's a distinct command for discoverability on test-oriented files.
    const filepath = getActiveNkFile();
    if (!filepath) return;
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA Test');
    terminal.sendText(`${py} -m nekova run ${quoteArg(filepath)}`);
}

function cmdDebugFile() {
    const filepath = getActiveNkFile();
    if (!filepath) return;
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA Debug');
    terminal.sendText(`${py} -m nekova debug ${quoteArg(filepath)}`);
}

async function cmdNewProject() {
    const name = await vscode.window.showInputBox({
        prompt: 'Project name',
        placeHolder: 'myapp'
    });
    if (!name) return;

    const template = await vscode.window.showQuickPick(
        [
            { label: 'default',   description: 'Blank NEKOVA project' },
            { label: 'web',       description: 'Web server with routes' },
            { label: 'ai',        description: 'AI-native — think / remember' },
            { label: 'fullstack', description: 'Web + AI + SQLite database' }
        ],
        { placeHolder: 'Choose a template' }
    );
    if (!template) return;

    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA');
    terminal.sendText(
        `${py} -m nekova new ${quoteArg(name)} --template ${template.label}`
    );

    vscode.window.showInformationMessage(
        `Creating NEKOVA project "${name}" [${template.label}]...`
    );
}

// ── Format on save ─────────────────────────────────────────────────────────

function registerFormatOnSave(context) {
    return vscode.workspace.onWillSaveTextDocument(event => {
        const config = vscode.workspace.getConfiguration('nekova');
        if (!config.get('formatOnSave', false)) return;
        const doc = event.document;
        if (!doc.fileName.endsWith('.nk')) return;

        // Note: Full format-on-save requires a DocumentFormattingEditProvider.
        // For now, run fmt in terminal as a best-effort approach.
        const py = getPython();
        const terminal = getOrCreateTerminal('NEKOVA');
        terminal.sendText(`${py} -m nekova fmt ${quoteArg(doc.fileName)}`);
    });
}

// ── Status bar ─────────────────────────────────────────────────────────────

function createStatusBar(context) {
    const config = vscode.workspace.getConfiguration('nekova');
    if (!config.get('showStatusBar', true)) return null;

    const statusBar = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Left, 100
    );
    statusBar.text = '$(zap) NEKOVA';
    statusBar.tooltip = 'NEKOVA v1.9.5 — Connected Forge by SYNEKCOT Tech\nClick to run file';
    statusBar.command = 'nekova.runFile';

    vscode.window.onDidChangeActiveTextEditor(editor => {
        if (editor && editor.document.fileName.endsWith('.nk')) {
            // Show AI provider in status bar
            const provider = vscode.workspace
                .getConfiguration('nekova')
                .get('aiProvider', 'auto');
            statusBar.text = `$(zap) NEKOVA [${provider}]`;
            statusBar.show();
        } else {
            statusBar.hide();
        }
    }, null, context.subscriptions);

    return statusBar;
}

// ── Activate ───────────────────────────────────────────────────────────────

function activate(context) {
    console.log('NEKOVA Language extension v1.9.5 activated');

    // Register commands
    const commands = [
        vscode.commands.registerCommand('nekova.runFile',    cmdRunFile),
        vscode.commands.registerCommand('nekova.runWatch',   cmdRunWatch),
        vscode.commands.registerCommand('nekova.openRepl',   cmdOpenRepl),
        vscode.commands.registerCommand('nekova.fmtFile',    cmdFmtFile),
        vscode.commands.registerCommand('nekova.checkFile',  cmdCheckFile),
        vscode.commands.registerCommand('nekova.testFile',   cmdTestFile),
        vscode.commands.registerCommand('nekova.debugFile',  cmdDebugFile),
        vscode.commands.registerCommand('nekova.newProject', cmdNewProject),
    ];

    // Status bar
    const statusBar = createStatusBar(context);
    if (statusBar) {
        commands.push(statusBar);
        // Trigger initial check
        if (vscode.window.activeTextEditor &&
            vscode.window.activeTextEditor.document.fileName.endsWith('.nk')) {
            statusBar.show();
        }
    }

    // Format on save
    commands.push(registerFormatOnSave(context));

    context.subscriptions.push(...commands);

    // Welcome message on first activation
    const shown = context.globalState.get('nekova.welcomeShown_1.9.5');
    if (!shown) {
        vscode.window.showInformationMessage(
            'NEKOVA v1.9.5 — now with prompt blocks and retry/fallback. Press F5 to run any .nk file.',
            'Open REPL', 'New Project'
        ).then(choice => {
            if (choice === 'Open REPL')    cmdOpenRepl();
            if (choice === 'New Project')  cmdNewProject();
        });
        context.globalState.update('nekova.welcomeShown_1.9.5', true);
    }
}

function deactivate() {}

module.exports = { activate, deactivate };