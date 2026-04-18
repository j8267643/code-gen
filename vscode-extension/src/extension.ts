import * as vscode from 'vscode';
import { CodeGenProvider } from './CodeGenProvider';

export function activate(context: vscode.ExtensionContext) {
    console.log('CodeGen AI Assistant is now active');

    // Create provider instance
    const provider = new CodeGenProvider(context.extensionUri);

    // Register webview view provider
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            CodeGenProvider.viewType,
            provider,
            {
                webviewOptions: { retainContextWhenHidden: true }
            }
        )
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('codegen.newTask', async () => {
            provider.clearTask();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codegen.settings', () => {
            provider.openSettings();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codegen.history', () => {
            provider.showHistory();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codegen.addToChat', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showInformationMessage('No active editor');
                return;
            }

            const selection = editor.document.getText(editor.selection);
            if (!selection) {
                vscode.window.showInformationMessage('No code selected');
                return;
            }

            provider.addToChat({
                type: 'code',
                content: selection,
                filePath: editor.document.fileName,
                language: editor.document.languageId
            });
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codegen.explainCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;

            const selection = editor.document.getText(editor.selection);
            if (!selection) {
                vscode.window.showInformationMessage('No code selected');
                return;
            }

            provider.sendMessage({
                type: 'explain',
                code: selection,
                language: editor.document.languageId
            });
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codegen.fixCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;

            const selection = editor.document.getText(editor.selection);
            if (!selection) {
                vscode.window.showInformationMessage('No code selected');
                return;
            }

            provider.sendMessage({
                type: 'fix',
                code: selection,
                language: editor.document.languageId
            });
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codegen.improveCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;

            const selection = editor.document.getText(editor.selection);
            if (!selection) {
                vscode.window.showInformationMessage('No code selected');
                return;
            }

            provider.sendMessage({
                type: 'improve',
                code: selection,
                language: editor.document.languageId
            });
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codegen.focusChatInput', () => {
            provider.focusChatInput();
        })
    );

    // Set context to show views
    vscode.commands.executeCommand('setContext', 'codegen.enabled', true);
}

export function deactivate() {
    console.log('CodeGen AI Assistant is now deactivated');
}
