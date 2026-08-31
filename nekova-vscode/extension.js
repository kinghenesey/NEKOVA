// =============================================================
// NEKOVA Language — VS Code Extension  (v2.0.0)
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
//
// All terminal commands below invoke `<python> -m nekova_cli ...`,
// not `-m nekova`. The nekova/ package has no __main__.py, so
// `python -m nekova` fails outright with "No module named
// nekova.__main__" — meaning every single command in this extension
// was non-functional as originally shipped. nekova_cli is the real
// module the installed `nekova` console-script itself delegates to
// (see nekova_cli.py), and invoking it via `-m` works reliably
// regardless of whether that console script happens to be on PATH —
// it only depends on the configured nekova.pythonPath setting.

const vscode = require('vscode');
const { LanguageClient, TransportKind } = require('vscode-languageclient/node');

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
    terminal.sendText(`${py} -m nekova_cli run ${quoteArg(filepath)}`);
}

function cmdRunWatch() {
    const filepath = getActiveNkFile();
    if (!filepath) return;
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA Watch');
    terminal.sendText(`${py} -m nekova_cli run ${quoteArg(filepath)} --watch`);
}

function cmdOpenRepl() {
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA REPL');
    terminal.sendText(`${py} -m nekova_cli repl`);
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
    terminal.sendText(`${py} -m nekova_cli fmt ${quoteArg(filepath)}`);
}

function cmdCheckFile() {
    const filepath = getActiveNkFile();
    if (!filepath) return;
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA Check');
    terminal.sendText(`${py} -m nekova_cli check ${quoteArg(filepath)}`);
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
    terminal.sendText(`${py} -m nekova_cli run ${quoteArg(filepath)}`);
}

function cmdDebugFile() {
    const filepath = getActiveNkFile();
    if (!filepath) return;
    const py = getPython();
    const terminal = getOrCreateTerminal('NEKOVA Debug');
    terminal.sendText(`${py} -m nekova_cli debug ${quoteArg(filepath)}`);
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
        `${py} -m nekova_cli new ${quoteArg(name)} --template ${template.label}`
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
        terminal.sendText(`${py} -m nekova_cli fmt ${quoteArg(doc.fileName)}`);
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
    statusBar.tooltip = 'NEKOVA v2.0.0 — Connected Forge by SYNEKCOT Tech\nClick to run file';
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

// ── Language Server (Phase 26) ──────────────────────────────────────────────
// Replaces syntax-highlighting-only support with real inline errors, hover
// docs, and autocomplete — talking to `nekova lsp` (nekova/lsp/server.py)
// over the standard LSP stdio transport.

let client = null;

function startLanguageClient(context) {
    const config = vscode.workspace.getConfiguration('nekova');
    if (!config.get('enableLanguageServer', true)) return;

    const py = getPython();

    // Same command form as every other terminal command in this file
    // (see the note at the top of this file for why it's nekova_cli,
    // not nekova, after -m) — except here it's spawned directly as a
    // subprocess rather than sent to a terminal, since the language
    // client needs to own its stdio to speak the LSP protocol.
    const serverOptions = {
        run: {
            command: py,
            args: ['-m', 'nekova_cli', 'lsp'],
            transport: TransportKind.stdio,
        },
        debug: {
            command: py,
            args: ['-m', 'nekova_cli', 'lsp'],
            transport: TransportKind.stdio,
        },
    };

    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'nekova' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.nk'),
        },
    };

    client = new LanguageClient(
        'nekovaLanguageServer',
        'NEKOVA Language Server',
        serverOptions,
        clientOptions
    );

    client.start();
    context.subscriptions.push(client);
}

// ── Activate ───────────────────────────────────────────────────────────────

function activate(context) {
    console.log('NEKOVA Language extension v2.0.0 activated');

    // Language server (real diagnostics, hover, autocomplete)
    startLanguageClient(context);

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
    const shown = context.globalState.get('nekova.welcomeShown_2.0.0');
    if (!shown) {
        vscode.window.showInformationMessage(
            'NEKOVA v2.0.0 — the parser is now self-hosted: NEKOVA\'s own parser is written in NEKOVA (parser.nk), verified against the Python reference on real-world input including its own source. No editor-facing changes in this release. Press F5 to run any .nk file.',
            'Open REPL', 'New Project'
        ).then(choice => {
            if (choice === 'Open REPL')    cmdOpenRepl();
            if (choice === 'New Project')  cmdNewProject();
        });
        context.globalState.update('nekova.welcomeShown_2.0.0', true);
    }
}

function deactivate() {
    if (!client) return undefined;
    return client.stop();
}

module.exports = { activate, deactivate };