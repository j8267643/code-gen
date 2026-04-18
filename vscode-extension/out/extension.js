"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const CodeGenProvider_1 = require("./CodeGenProvider");
function activate(context) {
    console.log('CodeGen AI Assistant is now active');
    // Create provider instance
    const provider = new CodeGenProvider_1.CodeGenProvider(context.extensionUri);
    // Register webview view provider
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(CodeGenProvider_1.CodeGenProvider.viewType, provider, {
        webviewOptions: { retainContextWhenHidden: true }
    }));
    // Register commands
    context.subscriptions.push(vscode.commands.registerCommand('codegen.newTask', async () => {
        provider.clearTask();
    }));
    context.subscriptions.push(vscode.commands.registerCommand('codegen.settings', () => {
        provider.openSettings();
    }));
    context.subscriptions.push(vscode.commands.registerCommand('codegen.history', () => {
        provider.showHistory();
    }));
    context.subscriptions.push(vscode.commands.registerCommand('codegen.addToChat', async () => {
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
    }));
    context.subscriptions.push(vscode.commands.registerCommand('codegen.explainCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
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
    }));
    context.subscriptions.push(vscode.commands.registerCommand('codegen.fixCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
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
    }));
    context.subscriptions.push(vscode.commands.registerCommand('codegen.improveCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
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
    }));
    context.subscriptions.push(vscode.commands.registerCommand('codegen.focusChatInput', () => {
        provider.focusChatInput();
    }));
    // Set context to show views
    vscode.commands.executeCommand('setContext', 'codegen.enabled', true);
}
function deactivate() {
    console.log('CodeGen AI Assistant is now deactivated');
}
//# sourceMappingURL=extension.js.map