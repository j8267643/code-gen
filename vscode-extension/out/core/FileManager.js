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
exports.FileManager = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
class FileManager {
    constructor() {
        this._changes = [];
    }
    async readFile(filePath) {
        try {
            const uri = vscode.Uri.file(filePath);
            const document = await vscode.workspace.openTextDocument(uri);
            return document.getText();
        }
        catch (error) {
            // Try reading from disk
            return fs.promises.readFile(filePath, 'utf-8');
        }
    }
    async writeFile(filePath, content) {
        const uri = vscode.Uri.file(filePath);
        try {
            // Try to open existing document
            const document = await vscode.workspace.openTextDocument(uri);
            const edit = new vscode.WorkspaceEdit();
            const fullRange = new vscode.Range(document.positionAt(0), document.positionAt(document.getText().length));
            edit.replace(uri, fullRange, content);
            await vscode.workspace.applyEdit(edit);
            await document.save();
        }
        catch {
            // File doesn't exist or can't be opened, create it
            const edit = new vscode.WorkspaceEdit();
            edit.createFile(uri, { overwrite: true });
            edit.insert(uri, new vscode.Position(0, 0), content);
            await vscode.workspace.applyEdit(edit);
        }
    }
    async applyCodeEdit(filePath, search, replace) {
        const uri = vscode.Uri.file(filePath);
        try {
            const document = await vscode.workspace.openTextDocument(uri);
            const content = document.getText();
            if (!content.includes(search)) {
                return false;
            }
            const edit = new vscode.WorkspaceEdit();
            const startIndex = content.indexOf(search);
            const startPos = document.positionAt(startIndex);
            const endPos = document.positionAt(startIndex + search.length);
            const range = new vscode.Range(startPos, endPos);
            edit.replace(uri, range, replace);
            const success = await vscode.workspace.applyEdit(edit);
            if (success) {
                await document.save();
                this._changes.push({
                    filePath,
                    originalContent: search,
                    newContent: replace
                });
            }
            return success;
        }
        catch (error) {
            console.error('Error applying edit:', error);
            return false;
        }
    }
    async createFile(filePath, content) {
        try {
            const uri = vscode.Uri.file(filePath);
            const edit = new vscode.WorkspaceEdit();
            // Create parent directories if needed
            const dir = path.dirname(filePath);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
            edit.createFile(uri, { overwrite: false });
            edit.insert(uri, new vscode.Position(0, 0), content);
            const success = await vscode.workspace.applyEdit(edit);
            if (success) {
                const document = await vscode.workspace.openTextDocument(uri);
                await document.save();
                this._changes.push({
                    filePath,
                    originalContent: '',
                    newContent: content
                });
            }
            return success;
        }
        catch (error) {
            console.error('Error creating file:', error);
            return false;
        }
    }
    async deleteFile(filePath) {
        try {
            const uri = vscode.Uri.file(filePath);
            const edit = new vscode.WorkspaceEdit();
            edit.deleteFile(uri);
            const success = await vscode.workspace.applyEdit(edit);
            if (success) {
                this._changes.push({
                    filePath,
                    originalContent: 'File existed',
                    newContent: 'File deleted'
                });
            }
            return success;
        }
        catch (error) {
            console.error('Error deleting file:', error);
            return false;
        }
    }
    async getWorkspaceFiles(pattern = '**/*') {
        const files = await vscode.workspace.findFiles(pattern, '**/node_modules/**');
        return files.map(uri => uri.fsPath);
    }
    async getFileInfo(filePath) {
        try {
            const content = await this.readFile(filePath);
            const language = this.getLanguageFromPath(filePath);
            return {
                path: filePath,
                name: path.basename(filePath),
                content,
                language
            };
        }
        catch (error) {
            return null;
        }
    }
    getLanguageFromPath(filePath) {
        const ext = path.extname(filePath).toLowerCase();
        const languageMap = {
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascriptreact',
            '.tsx': 'typescriptreact',
            '.py': 'python',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.sql': 'sql',
            '.sh': 'shellscript',
            '.bash': 'shellscript',
            '.zsh': 'shellscript',
            '.ps1': 'powershell',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.dockerfile': 'dockerfile',
            '.tf': 'terraform',
            '.vue': 'vue',
            '.svelte': 'svelte'
        };
        return languageMap[ext] || 'plaintext';
    }
    async showDiff(filePath, originalContent, newContent) {
        const uri = vscode.Uri.file(filePath);
        const scheme = 'codegen-diff';
        // Create virtual document for original content
        const originalUri = uri.with({
            scheme,
            query: Buffer.from(originalContent).toString('base64')
        });
        // Show diff
        await vscode.commands.executeCommand('vscode.diff', originalUri, uri, `${path.basename(filePath)} (Changes)`, { preview: true });
    }
    async searchInFiles(query, pattern = '**/*') {
        const results = [];
        const files = await this.getWorkspaceFiles(pattern);
        for (const filePath of files) {
            try {
                const content = await this.readFile(filePath);
                if (content.includes(query)) {
                    const lines = content.split('\n');
                    for (let i = 0; i < lines.length; i++) {
                        if (lines[i].includes(query)) {
                            const uri = vscode.Uri.file(filePath);
                            const position = new vscode.Position(i, lines[i].indexOf(query));
                            results.push(new vscode.Location(uri, position));
                        }
                    }
                }
            }
            catch (error) {
                // Skip files that can't be read
            }
        }
        return results;
    }
    getRecentChanges() {
        return [...this._changes];
    }
    clearChanges() {
        this._changes = [];
    }
    async getCurrentFileContext() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return null;
        }
        const document = editor.document;
        return {
            path: document.fileName,
            name: path.basename(document.fileName),
            content: document.getText(),
            language: document.languageId
        };
    }
    async getSelectedCode() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return null;
        }
        const selection = editor.selection;
        if (selection.isEmpty) {
            return null;
        }
        return {
            code: editor.document.getText(selection),
            filePath: editor.document.fileName,
            language: editor.document.languageId
        };
    }
}
exports.FileManager = FileManager;
//# sourceMappingURL=FileManager.js.map