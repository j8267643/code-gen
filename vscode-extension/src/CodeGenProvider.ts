import * as vscode from 'vscode';
import { getNonce } from './getNonce';
import { AIService, Message } from './ai/AIService';
import { FileManager } from './core/FileManager';
import { TerminalManager } from './core/TerminalManager';

export class CodeGenProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'codegen.sidebarProvider';
    private _view?: vscode.WebviewView;
    private _context?: vscode.ExtensionContext;
    private _aiService: AIService;
    private _messageHistory: Message[] = [];
    private _fileManager: FileManager;
    private _terminalManager: TerminalManager;

    constructor(private readonly _extensionUri: vscode.Uri) {
        this._aiService = new AIService(AIService.getDefaultConfig());
        this._fileManager = new FileManager();
        this._terminalManager = new TerminalManager();
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;
        this._context = context as any;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            console.log('CodeGen: Received message:', data.type, data);
            try {
                switch (data.type) {
                    case 'sendMessage':
                        await this.handleUserMessage(data.text);
                        break;
                    case 'applyCode':
                        await this.applyCode(data.code);
                        break;
                    case 'copyCode':
                        await vscode.env.clipboard.writeText(data.code);
                        this.sendMessage({ type: 'showNotification', message: 'Code copied to clipboard' });
                        break;
                    case 'openFile':
                        await this.openFile(data.filePath);
                        break;
                    case 'executeCommand':
                        await this.executeCommand(data.command);
                        break;
                    case 'getSettings':
                        this.sendSettings();
                        break;
                    case 'saveSettings':
                        await this.saveSettings(data.settings);
                        break;
                    case 'clearChat':
                        this._messageHistory = [];
                        break;
                    case 'newTask':
                        this._messageHistory = [];
                        this.sendMessage({ type: 'clearChat' });
                        break;
                    default:
                        console.log('CodeGen: Unknown message type:', data.type);
                }
            } catch (error) {
                console.error('CodeGen: Error handling message:', error);
                this.sendMessage({ type: 'error', text: String(error) });
            }
        });

        // Send initial settings
        this.sendSettings();
    }

    public sendMessage(message: any) {
        if (this._view) {
            this._view.webview.postMessage(message);
        }
    }

    public clearTask() {
        this._messageHistory = [];
        this.sendMessage({ type: 'clearChat' });
    }

    public openSettings() {
        this.sendMessage({ type: 'openSettings' });
    }

    public showHistory() {
        this.sendMessage({ type: 'showHistory' });
    }

    public focusChatInput() {
        this.sendMessage({ type: 'focusChatInput' });
    }

    public addToChat(context: { type: string; content: string; filePath: string; language: string }) {
        this.sendMessage({
            type: 'addToChat',
            context: context
        });
    }

    private async handleUserMessage(text: string) {
        // Update AI service config
        this._aiService.updateConfig(AIService.getDefaultConfig());
        const config = AIService.getDefaultConfig();

        // Get current file context
        const currentFile = await this._fileManager.getCurrentFileContext();
        const selectedCode = await this._fileManager.getSelectedCode();

        // Build system message with context
        let systemMessage = `You are CodeGen AI, an intelligent coding assistant integrated into VS Code.
You help users with coding tasks, code analysis, debugging, and file operations.

Capabilies:
- Read and write files in the workspace
- Execute terminal commands
- Analyze code and suggest improvements
- Explain code functionality
- Fix bugs and errors
- Generate documentation`;

        if (currentFile) {
            systemMessage += `\n\nCurrent file: ${currentFile.path} (${currentFile.language})`;
        }

        if (selectedCode) {
            systemMessage += `\n\nSelected code:\n\`\`\`${selectedCode.language}\n${selectedCode.code}\n\`\`\``;
        }

        // Build messages array with system context
        const messages: Message[] = [
            { role: 'system', content: systemMessage },
            ...this._messageHistory.slice(-10),
            { role: 'user', content: text }
        ];

        // Show loading state
        this.sendMessage({ type: 'setLoading', loading: true });

        try {
            let fullResponse = '';
            
            // Stream the response
            for await (const chunk of this._aiService.streamChat(messages)) {
                fullResponse += chunk;
                this.sendMessage({
                    type: 'streamMessage',
                    text: fullResponse,
                    isComplete: false
                });
            }

            // Mark as complete
            this.sendMessage({
                type: 'streamMessage',
                text: fullResponse,
                isComplete: true
            });

            // Add to history
            this._messageHistory.push({ role: 'user', content: text });
            this._messageHistory.push({ role: 'assistant', content: fullResponse });

            // Keep history manageable
            if (this._messageHistory.length > 20) {
                this._messageHistory = this._messageHistory.slice(-20);
            }
        } catch (error) {
            this.sendMessage({
                type: 'error',
                text: `Error: ${error}`
            });
        } finally {
            this.sendMessage({ type: 'setLoading', loading: false });
        }
    }

    private async applyCode(code: string) {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            const selection = editor.selection;
            await editor.edit(editBuilder => {
                if (!selection.isEmpty) {
                    editBuilder.replace(selection, code);
                } else {
                    editBuilder.insert(selection.start, code);
                }
            });
            this.sendMessage({ type: 'showNotification', message: 'Code applied' });
        }
    }

    private async openFile(filePath: string) {
        const document = await vscode.workspace.openTextDocument(filePath);
        await vscode.window.showTextDocument(document);
    }

    private async executeCommand(command: string) {
        const terminal = vscode.window.activeTerminal || vscode.window.createTerminal('CodeGen');
        terminal.show();
        terminal.sendText(command);
    }

    private sendSettings() {
        const config = vscode.workspace.getConfiguration('codegen');
        this.sendMessage({
            type: 'settings',
            settings: {
                apiKey: config.get<string>('apiKey') || '',
                model: config.get<string>('model') || 'claude-3-sonnet-20240229',
                baseUrl: config.get<string>('baseUrl') || '',
                maxTokens: config.get<number>('maxTokens') || 4096,
                temperature: config.get<number>('temperature') || 0.7,
                enableKnowledgeGraph: config.get<boolean>('enableKnowledgeGraph') || true,
                autoApprove: config.get<boolean>('autoApprove') || false
            }
        });
    }

    private async saveSettings(settings: any) {
        const config = vscode.workspace.getConfiguration('codegen');
        await config.update('apiKey', settings.apiKey, true);
        await config.update('model', settings.model, true);
        await config.update('baseUrl', settings.baseUrl, true);
        await config.update('maxTokens', settings.maxTokens, true);
        await config.update('temperature', settings.temperature, true);
        await config.update('enableKnowledgeGraph', settings.enableKnowledgeGraph, true);
        await config.update('autoApprove', settings.autoApprove, true);
        this.sendMessage({ type: 'showNotification', message: 'Settings saved' });
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        const nonce = getNonce();

        return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline' ${webview.cspSource}; script-src 'nonce-${nonce}';">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeGen AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg-primary: var(--vscode-editor-background);
            --bg-secondary: var(--vscode-sideBar-background);
            --bg-tertiary: var(--vscode-titleBar-inactiveBackground);
            --bg-hover: var(--vscode-list-hoverBackground);
            --fg-primary: var(--vscode-foreground);
            --fg-secondary: var(--vscode-descriptionForeground);
            --border: var(--vscode-panel-border);
            --accent: var(--vscode-focusBorder);
            --button-bg: var(--vscode-button-background);
            --button-fg: var(--vscode-button-foreground);
            --button-hover: var(--vscode-button-hoverBackground);
            --input-bg: var(--vscode-input-background);
            --input-fg: var(--vscode-input-foreground);
            --input-border: var(--vscode-input-border);
            --error: var(--vscode-errorForeground);
            --success: var(--vscode-testing-iconPassed);
            --warning: var(--vscode-testing-iconQueued);
            --font-mono: var(--vscode-editor-font-family);
            --font-ui: var(--vscode-font-family);
            --font-size: var(--vscode-font-size);
        }

        body {
            font-family: var(--font-ui);
            font-size: var(--font-size);
            color: var(--fg-primary);
            background: var(--bg-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Scrollbar Styling */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--fg-secondary);
        }

        /* Main Layout */
        .app-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }

        /* Top Navigation Bar */
        .nav-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 16px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            min-height: 44px;
        }

        .nav-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .nav-brand {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            font-size: 14px;
        }

        .nav-brand-icon {
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .nav-right {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .nav-btn {
            width: 32px;
            height: 32px;
            border: none;
            background: transparent;
            color: var(--fg-secondary);
            cursor: pointer;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            transition: all 0.15s ease;
        }

        .nav-btn:hover {
            background: var(--vscode-toolbar-hoverBackground);
            color: var(--fg-primary);
        }

        .nav-btn:active {
            transform: scale(0.95);
        }

        .nav-divider {
            width: 1px;
            height: 20px;
            background: var(--border);
            margin: 0 4px;
        }

        /* Main Content Area */
        .main-content {
            flex: 1;
            display: flex;
            overflow: hidden;
            position: relative;
        }

        /* Chat Area */
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Task Info Bar */
        .task-info-bar {
            display: flex;
            align-items: center;
            padding: 8px 16px;
            background: var(--bg-tertiary);
            border-bottom: 1px solid var(--border);
            font-size: 12px;
            color: var(--fg-secondary);
            gap: 12px;
        }

        .task-info-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .task-info-label {
            font-weight: 500;
        }

        /* Messages Container */
        .messages-scroll {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }

        .messages-container {
            display: flex;
            flex-direction: column;
            gap: 20px;
            max-width: 900px;
            margin: 0 auto;
        }

        /* Empty State */
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100%;
            text-align: center;
            padding: 40px 20px;
        }

        .empty-state-icon {
            font-size: 56px;
            margin-bottom: 20px;
            opacity: 0.6;
        }

        .empty-state-title {
            font-size: 22px;
            font-weight: 600;
            color: var(--fg-primary);
            margin-bottom: 8px;
        }

        .empty-state-subtitle {
            font-size: 14px;
            color: var(--fg-secondary);
            margin-bottom: 32px;
            max-width: 400px;
            line-height: 1.6;
        }

        .quick-actions-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            max-width: 500px;
            width: 100%;
        }

        .quick-action-card {
            padding: 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: left;
        }

        .quick-action-card:hover {
            border-color: var(--accent);
            background: var(--bg-hover);
            transform: translateY(-1px);
        }

        .quick-action-card:active {
            transform: translateY(0);
        }

        .quick-action-icon {
            font-size: 20px;
            margin-bottom: 8px;
        }

        .quick-action-title {
            font-weight: 600;
            font-size: 13px;
            margin-bottom: 4px;
            color: var(--fg-primary);
        }

        .quick-action-desc {
            font-size: 11px;
            color: var(--fg-secondary);
            line-height: 1.4;
        }

        /* Message Styles */
        .message {
            display: flex;
            gap: 12px;
            animation: messageSlideIn 0.3s ease;
        }

        @keyframes messageSlideIn {
            from { 
                opacity: 0; 
                transform: translateY(12px); 
            }
            to { 
                opacity: 1; 
                transform: translateY(0); 
            }
        }

        .message-avatar {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 14px;
            font-weight: 600;
            flex-shrink: 0;
        }

        .message.user .message-avatar {
            background: var(--bg-tertiary);
            color: var(--fg-primary);
        }

        .message.assistant .message-avatar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .message-content-wrapper {
            flex: 1;
            min-width: 0;
        }

        .message-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }

        .message-author {
            font-weight: 600;
            font-size: 13px;
            color: var(--fg-primary);
        }

        .message-time {
            font-size: 11px;
            color: var(--fg-secondary);
        }

        .message-content {
            line-height: 1.7;
            color: var(--fg-primary);
            word-wrap: break-word;
        }

        .message.user .message-content {
            color: var(--fg-primary);
        }

        /* Code Block Styling */
        .code-block-wrapper {
            margin: 12px 0;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border);
            background: var(--bg-secondary);
        }

        .code-block-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            background: var(--bg-tertiary);
            border-bottom: 1px solid var(--border);
        }

        .code-block-lang {
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 600;
            color: var(--fg-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .code-block-actions {
            display: flex;
            gap: 6px;
        }

        .code-block-btn {
            padding: 4px 12px;
            border: none;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .code-block-btn.primary {
            background: var(--button-bg);
            color: var(--button-fg);
        }

        .code-block-btn.primary:hover {
            background: var(--button-hover);
        }

        .code-block-btn.secondary {
            background: transparent;
            color: var(--fg-secondary);
            border: 1px solid var(--border);
        }

        .code-block-btn.secondary:hover {
            background: var(--bg-hover);
            color: var(--fg-primary);
        }

        .code-block-btn:active {
            transform: scale(0.95);
        }

        .code-block-body {
            padding: 16px;
            overflow-x: auto;
        }

        .code-block-body pre {
            margin: 0;
            font-family: var(--font-mono);
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .code-block-body code {
            font-family: var(--font-mono);
        }

        /* Inline Code */
        .inline-code {
            background: var(--bg-tertiary);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--accent);
        }

        /* Input Area */
        .input-area {
            padding: 12px 16px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
        }

        .input-container {
            display: flex;
            align-items: flex-end;
            gap: 8px;
            background: var(--input-bg);
            border: 1px solid var(--input-border);
            border-radius: 12px;
            padding: 8px 12px;
            transition: border-color 0.2s ease;
        }

        .input-container:focus-within {
            border-color: var(--accent);
        }

        .input-wrapper {
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .context-hint {
            font-size: 11px;
            color: var(--fg-secondary);
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .message-input {
            width: 100%;
            background: transparent;
            border: none;
            color: var(--input-fg);
            font-family: var(--font-ui);
            font-size: 14px;
            resize: none;
            outline: none;
            line-height: 1.5;
            max-height: 150px;
        }

        .message-input::placeholder {
            color: var(--fg-secondary);
        }

        .send-button {
            width: 36px;
            height: 36px;
            border: none;
            background: var(--button-bg);
            color: var(--button-fg);
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            flex-shrink: 0;
            transition: all 0.15s ease;
        }

        .send-button:hover:not(:disabled) {
            background: var(--button-hover);
            transform: scale(1.05);
        }

        .send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .send-button:active:not(:disabled) {
            transform: scale(0.95);
        }

        /* Status Bar */
        .status-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 6px 16px;
            background: var(--bg-primary);
            border-top: 1px solid var(--border);
            font-size: 11px;
            color: var(--fg-secondary);
            min-height: 28px;
        }

        .status-left {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--success);
        }

        .status-dot.loading {
            background: var(--warning);
            animation: pulse 1.5s ease infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        .status-right {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        /* Settings Panel */
        .settings-overlay {
            display: none;
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--bg-primary);
            z-index: 10;
        }

        .settings-overlay.active {
            display: flex;
            flex-direction: column;
        }

        .settings-header {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            gap: 12px;
        }

        .settings-back-btn {
            width: 32px;
            height: 32px;
            border: none;
            background: transparent;
            color: var(--fg-secondary);
            cursor: pointer;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }

        .settings-back-btn:hover {
            background: var(--vscode-toolbar-hoverBackground);
            color: var(--fg-primary);
        }

        .settings-title {
            font-size: 16px;
            font-weight: 600;
        }

        .settings-body {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }

        .settings-section {
            margin-bottom: 28px;
        }

        .settings-section-title {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--fg-secondary);
            margin-bottom: 12px;
        }

        .setting-item {
            margin-bottom: 16px;
        }

        .setting-label {
            display: block;
            font-weight: 500;
            font-size: 13px;
            margin-bottom: 6px;
            color: var(--fg-primary);
        }

        .setting-description {
            font-size: 11px;
            color: var(--fg-secondary);
            margin-bottom: 8px;
            line-height: 1.4;
        }

        .setting-input {
            width: 100%;
            padding: 8px 12px;
            background: var(--input-bg);
            border: 1px solid var(--input-border);
            color: var(--input-fg);
            border-radius: 6px;
            font-family: var(--font-ui);
            font-size: 13px;
            transition: border-color 0.2s ease;
        }

        .setting-input:focus {
            outline: none;
            border-color: var(--accent);
        }

        .setting-input::placeholder {
            color: var(--fg-secondary);
            opacity: 0.6;
        }

        .save-settings-btn {
            width: 100%;
            padding: 10px 20px;
            background: var(--button-bg);
            color: var(--button-fg);
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            margin-top: 20px;
        }

        .save-settings-btn:hover {
            background: var(--button-hover);
        }

        .save-settings-btn:active {
            transform: scale(0.98);
        }

        /* Notification Toast */
        .toast {
            position: fixed;
            bottom: 48px;
            left: 50%;
            transform: translateX(-50%) translateY(20px);
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 13px;
            z-index: 100;
            opacity: 0;
            transition: all 0.3s ease;
            pointer-events: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .toast.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }

        /* Loading Indicator */
        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 4px 0;
        }

        .typing-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--fg-secondary);
            animation: typingBounce 1.4s infinite ease-in-out;
        }

        .typing-dot:nth-child(1) { animation-delay: 0s; }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typingBounce {
            0%, 80%, 100% { 
                transform: translateY(0);
                opacity: 0.4;
            }
            40% { 
                transform: translateY(-6px);
                opacity: 1;
            }
        }

        /* Hidden utility */
        .hidden {
            display: none !important;
        }

        /* Markdown-like formatting */
        .message-content h1,
        .message-content h2,
        .message-content h3 {
            margin-top: 12px;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .message-content h1 { font-size: 18px; }
        .message-content h2 { font-size: 16px; }
        .message-content h3 { font-size: 14px; }

        .message-content p {
            margin-bottom: 8px;
        }

        .message-content ul,
        .message-content ol {
            margin-left: 20px;
            margin-bottom: 8px;
        }

        .message-content li {
            margin-bottom: 4px;
        }

        .message-content strong {
            font-weight: 600;
        }

        .message-content em {
            font-style: italic;
        }

        .message-content blockquote {
            border-left: 3px solid var(--accent);
            padding-left: 12px;
            margin: 8px 0;
            color: var(--fg-secondary);
        }

        /* Responsive */
        @media (max-width: 600px) {
            .quick-actions-grid {
                grid-template-columns: 1fr;
            }
            
            .nav-brand span {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Navigation Bar -->
        <div class="nav-bar">
            <div class="nav-left">
                <div class="nav-brand">
                    <div class="nav-brand-icon">🤖</div>
                    <span>CodeGen AI</span>
                </div>
            </div>
            <div class="nav-right">
                <button class="nav-btn" title="新建任务" onclick="newTask()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                </button>
                <div class="nav-divider"></div>
                <button class="nav-btn" title="历史记录" onclick="showHistory()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                </button>
                <button class="nav-btn" title="设置" onclick="toggleSettings()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                    </svg>
                </button>
            </div>
        </div>

        <!-- Task Info Bar -->
        <div class="task-info-bar">
            <div class="task-info-item">
                <span class="task-info-label">模型:</span>
                <span id="task-model">Claude 3.5 Sonnet</span>
            </div>
            <div class="task-info-item">
                <span class="task-info-label">消息:</span>
                <span id="message-count">0</span>
            </div>
            <div class="task-info-item">
                <span id="context-file" class="hidden">📄 <span id="context-filename"></span></span>
            </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
            <!-- Chat Area -->
            <div class="chat-area" id="chat-area">
                <!-- Messages -->
                <div class="messages-scroll" id="messages-scroll">
                    <div class="messages-container" id="messages-container">
                        <!-- Empty State -->
                        <div class="empty-state" id="empty-state">
                            <div class="empty-state-icon">🚀</div>
                            <div class="empty-state-title">开始你的编程之旅</div>
                            <div class="empty-state-subtitle">
                                我是你的AI编程助手，可以帮助你编写代码、分析问题、重构优化、生成文档等
                            </div>
                            <div class="quick-actions-grid">
                                <div class="quick-action-card" onclick="sendQuick('请解释这段代码的功能')">
                                    <div class="quick-action-icon">📖</div>
                                    <div class="quick-action-title">解释代码</div>
                                    <div class="quick-action-desc">分析代码逻辑和功能</div>
                                </div>
                                <div class="quick-action-card" onclick="sendQuick('请帮我修复这段代码的问题')">
                                    <div class="quick-action-icon">🔧</div>
                                    <div class="quick-action-title">修复问题</div>
                                    <div class="quick-action-desc">发现并修复代码错误</div>
                                </div>
                                <div class="quick-action-card" onclick="sendQuick('请优化和改进这段代码')">
                                    <div class="quick-action-icon">⚡</div>
                                    <div class="quick-action-title">优化代码</div>
                                    <div class="quick-action-desc">提升性能和可读性</div>
                                </div>
                                <div class="quick-action-card" onclick="sendQuick('请为这段代码生成文档')">
                                    <div class="quick-action-icon">📝</div>
                                    <div class="quick-action-title">生成文档</div>
                                    <div class="quick-action-desc">创建代码说明文档</div>
                                </div>
                            </div>
                        </div>
                        <!-- Messages will be inserted here -->
                        <div id="messages-list"></div>
                    </div>
                </div>

                <!-- Input Area -->
                <div class="input-area">
                    <div class="input-container">
                        <div class="input-wrapper">
                            <div class="context-hint" id="context-hint" style="display: none;">
                                <span>📎</span>
                                <span id="context-hint-text"></span>
                            </div>
                            <textarea 
                                class="message-input" 
                                id="message-input" 
                                placeholder="输入消息，按 Enter 发送，Shift+Enter 换行..."
                                rows="1"
                            ></textarea>
                        </div>
                        <button class="send-button" id="send-button" onclick="sendMessage()" title="发送">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Settings Overlay -->
            <div class="settings-overlay" id="settings-overlay">
                <div class="settings-header">
                    <button class="settings-back-btn" onclick="toggleSettings()">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="15 18 9 12 15 6"></polyline>
                        </svg>
                    </button>
                    <div class="settings-title">设置</div>
                </div>
                <div class="settings-body">
                    <div class="settings-section">
                        <div class="settings-section-title">API 配置</div>
                        <div class="setting-item">
                            <label class="setting-label" for="setting-apiKey">API Key</label>
                            <div class="setting-description">你的AI服务API密钥</div>
                            <input type="password" class="setting-input" id="setting-apiKey" placeholder="sk-...">
                        </div>
                        <div class="setting-item">
                            <label class="setting-label" for="setting-model">模型</label>
                            <div class="setting-description">使用的AI模型名称</div>
                            <input type="text" class="setting-input" id="setting-model" value="claude-3-sonnet-20240229">
                        </div>
                        <div class="setting-item">
                            <label class="setting-label" for="setting-baseUrl">自定义API地址</label>
                            <div class="setting-description">可选的自定义API基础URL</div>
                            <input type="text" class="setting-input" id="setting-baseUrl" placeholder="https://api.example.com">
                        </div>
                    </div>

                    <div class="settings-section">
                        <div class="settings-section-title">生成参数</div>
                        <div class="setting-item">
                            <label class="setting-label" for="setting-maxTokens">最大Token数</label>
                            <div class="setting-description">单次响应的最大Token数量</div>
                            <input type="number" class="setting-input" id="setting-maxTokens" value="4096" min="100" max="8192">
                        </div>
                        <div class="setting-item">
                            <label class="setting-label" for="setting-temperature">Temperature</label>
                            <div class="setting-description">控制响应的随机性 (0-1，越高越随机)</div>
                            <input type="number" class="setting-input" id="setting-temperature" value="0.7" step="0.1" min="0" max="1">
                        </div>
                    </div>

                    <div class="settings-section">
                        <div class="settings-section-title">高级选项</div>
                        <div class="setting-item">
                            <label class="setting-label" for="setting-enableKnowledgeGraph">知识图谱</label>
                            <div class="setting-description">启用知识图谱集成功能</div>
                            <select class="setting-input" id="setting-enableKnowledgeGraph">
                                <option value="true">启用</option>
                                <option value="false">禁用</option>
                            </select>
                        </div>
                        <div class="setting-item">
                            <label class="setting-label" for="setting-autoApprove">自动批准</label>
                            <div class="setting-description">自动批准文件编辑和命令执行</div>
                            <select class="setting-input" id="setting-autoApprove">
                                <option value="false">手动确认</option>
                                <option value="true">自动批准</option>
                            </select>
                        </div>
                    </div>

                    <button class="save-settings-btn" onclick="saveSettings()">保存设置</button>
                </div>
            </div>
        </div>

        <!-- Status Bar -->
        <div class="status-bar">
            <div class="status-left">
                <div class="status-dot" id="status-dot"></div>
                <span id="status-text">就绪</span>
            </div>
            <div class="status-right">
                <span id="status-version">v0.1.0</span>
            </div>
        </div>

        <!-- Toast Notification -->
        <div class="toast" id="toast"></div>
    </div>

    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        let isLoading = false;
        let currentStreamElement = null;
        let messageCount = 0;

        // DOM Elements
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        const messagesList = document.getElementById('messages-list');
        const emptyState = document.getElementById('empty-state');
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');
        const messageCountEl = document.getElementById('message-count');
        const messagesScroll = document.getElementById('messages-scroll');
        const toast = document.getElementById('toast');

        // Auto-resize textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        });

        // Handle keyboard shortcuts
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Send message
        function sendMessage() {
            const text = messageInput.value.trim();
            if (!text || isLoading) return;

            // Hide empty state
            emptyState.classList.add('hidden');

            // Add user message
            addMessage('user', text);
            
            // Clear input
            messageInput.value = '';
            messageInput.style.height = 'auto';

            // Send to extension
            vscode.postMessage({ type: 'sendMessage', text: text });
            
            // Set loading state
            setLoading(true);
        }

        // Quick action
        function sendQuick(text) {
            messageInput.value = text;
            sendMessage();
        }

        // New task
        function newTask() {
            vscode.postMessage({ type: 'newTask' });
        }

        // Show history
        function showHistory() {
            vscode.postMessage({ type: 'history' });
        }

        // Toggle settings
        function toggleSettings() {
            const overlay = document.getElementById('settings-overlay');
            const chatArea = document.getElementById('chat-area');
            
            if (overlay.classList.contains('active')) {
                overlay.classList.remove('active');
                chatArea.style.display = 'flex';
            } else {
                overlay.classList.add('active');
                chatArea.style.display = 'none';
                vscode.postMessage({ type: 'getSettings' });
            }
        }

        // Save settings
        function saveSettings() {
            const settings = {
                apiKey: document.getElementById('setting-apiKey').value,
                model: document.getElementById('setting-model').value,
                baseUrl: document.getElementById('setting-baseUrl').value,
                maxTokens: parseInt(document.getElementById('setting-maxTokens').value),
                temperature: parseFloat(document.getElementById('setting-temperature').value),
                enableKnowledgeGraph: document.getElementById('setting-enableKnowledgeGraph').value === 'true',
                autoApprove: document.getElementById('setting-autoApprove').value === 'true'
            };
            
            vscode.postMessage({ type: 'saveSettings', settings: settings });
            showToast('设置已保存');
            toggleSettings();
        }

        // Add message to chat
        function addMessage(role, content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + role;
            
            const avatar = role === 'user' ? '你' : 'AI';
            const avatarIcon = role === 'user' ? '👤' : '🤖';
            const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            messageDiv.innerHTML = \`
                <div class="message-avatar">\${avatarIcon}</div>
                <div class="message-content-wrapper">
                    <div class="message-header">
                        <span class="message-author">\${avatar}</span>
                        <span class="message-time">\${time}</span>
                    </div>
                    <div class="message-content" id="msg-\${Date.now()}">\${formatContent(content)}</div>
                </div>
            \`;
            
            messagesList.appendChild(messageDiv);
            scrollToBottom();
            updateMessageCount();
            
            return messageDiv;
        }

        // Update streaming message
        function updateStreamingMessage(content) {
            if (!currentStreamElement) {
                currentStreamElement = addMessage('assistant', '');
            }
            const contentDiv = currentStreamElement.querySelector('.message-content');
            contentDiv.innerHTML = formatContent(content);
            scrollToBottom();
        }

        // Format content with code blocks
        function formatContent(content) {
            // Handle code blocks
            content = content.replace(/\`\`\`(\w*)\n([\s\S]*?)\`\`\`/g, function(match, lang, code) {
                const escapedCode = escapeHtml(code.trimEnd());
                return \`
                    <div class="code-block-wrapper">
                        <div class="code-block-header">
                            <span class="code-block-lang">\${lang || 'text'}</span>
                            <div class="code-block-actions">
                                <button class="code-block-btn primary" onclick="applyCode(this)">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                                    应用
                                </button>
                                <button class="code-block-btn secondary" onclick="copyCode(this)">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                                    复制
                                </button>
                            </div>
                        </div>
                        <div class="code-block-body">
                            <pre><code>\${escapedCode}</code></pre>
                        </div>
                    </div>
                \`;
            });
            
            // Handle inline code
            content = content.replace(/\`([^\`]+)\`/g, '<code class="inline-code">$1</code>');
            
            // Handle line breaks
            content = content.replace(/\n/g, '<br>');
            
            return content;
        }

        // Escape HTML
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Scroll to bottom
        function scrollToBottom() {
            messagesScroll.scrollTop = messagesScroll.scrollHeight;
        }

        // Update message count
        function updateMessageCount() {
            messageCount = document.querySelectorAll('.message').length;
            messageCountEl.textContent = messageCount;
        }

        // Set loading state
        function setLoading(loading) {
            isLoading = loading;
            
            if (loading) {
                statusDot.classList.add('loading');
                statusText.textContent = '思考中...';
                sendButton.disabled = true;
                
                // Show typing indicator if no current stream
                if (!currentStreamElement) {
                    const indicator = document.createElement('div');
                    indicator.className = 'message assistant';
                    indicator.id = 'typing-indicator';
                    indicator.innerHTML = \`
                        <div class="message-avatar">🤖</div>
                        <div class="message-content-wrapper">
                            <div class="typing-indicator">
                                <div class="typing-dot"></div>
                                <div class="typing-dot"></div>
                                <div class="typing-dot"></div>
                            </div>
                        </div>
                    \`;
                    messagesList.appendChild(indicator);
                    scrollToBottom();
                }
            } else {
                statusDot.classList.remove('loading');
                statusText.textContent = '就绪';
                sendButton.disabled = false;
                currentStreamElement = null;
                
                // Remove typing indicator
                const indicator = document.getElementById('typing-indicator');
                if (indicator) indicator.remove();
            }
        }

        // Clear chat
        function clearChat() {
            messagesList.innerHTML = '';
            emptyState.classList.remove('hidden');
            messageCount = 0;
            messageCountEl.textContent = '0';
            currentStreamElement = null;
        }

        // Apply code
        function applyCode(btn) {
            const codeBlock = btn.closest('.code-block-wrapper');
            const code = codeBlock.querySelector('code').textContent;
            vscode.postMessage({ type: 'applyCode', code: code });
            showToast('代码已应用');
        }

        // Copy code
        function copyCode(btn) {
            const codeBlock = btn.closest('.code-block-wrapper');
            const code = codeBlock.querySelector('code').textContent;
            vscode.postMessage({ type: 'copyCode', code: code });
            showToast('代码已复制到剪贴板');
        }

        // Show toast notification
        function showToast(message) {
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        // Handle messages from extension
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.type) {
                case 'setLoading':
                    setLoading(message.loading);
                    break;
                case 'streamMessage':
                    updateStreamingMessage(message.text);
                    if (message.isComplete) {
                        setLoading(false);
                    }
                    break;
                case 'error':
                    setLoading(false);
                    addMessage('assistant', '❌ ' + message.text);
                    break;
                case 'settings':
                    document.getElementById('setting-apiKey').value = message.settings.apiKey || '';
                    document.getElementById('setting-model').value = message.settings.model;
                    document.getElementById('setting-baseUrl').value = message.settings.baseUrl || '';
                    document.getElementById('setting-maxTokens').value = message.settings.maxTokens;
                    document.getElementById('setting-temperature').value = message.settings.temperature;
                    document.getElementById('setting-enableKnowledgeGraph').value = message.settings.enableKnowledgeGraph ? 'true' : 'false';
                    document.getElementById('setting-autoApprove').value = message.settings.autoApprove ? 'true' : 'false';
                    break;
                case 'clearChat':
                    clearChat();
                    break;
                case 'showNotification':
                    showToast(message.message);
                    break;
                case 'openSettings':
                    if (!document.getElementById('settings-overlay').classList.contains('active')) {
                        toggleSettings();
                    }
                    break;
                case 'focusChatInput':
                    messageInput.focus();
                    break;
                case 'updateModel':
                    document.getElementById('task-model').textContent = message.model;
                    break;
                case 'setContext':
                    if (message.file) {
                        document.getElementById('context-file').classList.remove('hidden');
                        document.getElementById('context-filename').textContent = message.file;
                        document.getElementById('context-hint').style.display = 'flex';
                        document.getElementById('context-hint-text').textContent = '当前文件: ' + message.file;
                    } else {
                        document.getElementById('context-file').classList.add('hidden');
                        document.getElementById('context-hint').style.display = 'none';
                    }
                    break;
            }
        });

        // Initialize
        console.log('CodeGen AI Assistant initialized');
    </script>
</body>
</html>`;
    }
}