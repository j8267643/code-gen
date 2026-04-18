# CodeGen AI Assistant

AI-powered coding assistant for VS Code, inspired by Cline.

## Features

- **AI Chat Interface**: Interactive chat with streaming responses
- **Code Analysis**: Explain, fix, and improve code with AI
- **File Operations**: Read, write, and edit files directly
- **Terminal Integration**: Execute commands in integrated terminal
- **Context Awareness**: Automatically includes current file and selection context
- **Settings Management**: Configure API keys, models, and preferences

## Installation

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Click "Install from VSIX"
4. Select the compiled extension file

Or install from source:
```bash
cd vscode-extension
npm install
npm run compile
# Press F5 to open Extension Development Host
```

## Configuration

Open settings (Cmd/Ctrl+,) and search for "CodeGen":

- `codegen.apiKey`: Your AI service API key
- `codegen.model`: Model to use (default: claude-3-sonnet-20240229)
- `codegen.baseUrl`: Custom API base URL (optional)
- `codegen.maxTokens`: Maximum tokens for responses
- `codegen.temperature`: Temperature for responses (0-1)
- `codegen.autoApprove`: Auto-approve file edits

## Usage

### Chat Interface
- Click the CodeGen icon in the Activity Bar
- Type your message and press Enter
- View streaming AI responses

### Quick Actions
Select code and right-click to:
- **Explain with CodeGen**: Get code explanation
- **Fix with CodeGen**: Fix issues in code
- **Improve with CodeGen**: Optimize code
- **Add to CodeGen**: Add selection to chat context

### Keyboard Shortcuts
- `Cmd/Ctrl + '`: Add selection to chat / Focus chat input

### Commands
- `CodeGen: New Task`: Clear chat history
- `CodeGen: Settings`: Open settings panel
- `CodeGen: History`: View chat history

## Supported AI Providers

- Anthropic Claude (default)
- OpenAI GPT
- Custom API endpoints

## Project Structure

```
vscode-extension/
├── src/
│   ├── extension.ts          # Main extension entry
│   ├── CodeGenProvider.ts    # Webview provider
│   ├── getNonce.ts           # CSP nonce generator
│   ├── ai/
│   │   └── AIService.ts      # AI service integration
│   └── core/
│       ├── FileManager.ts    # File operations
│       └── TerminalManager.ts # Terminal integration
├── out/                      # Compiled JavaScript
├── package.json              # Extension manifest
└── tsconfig.json             # TypeScript config
```

## Development

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch for changes
npm run watch

# Debug
Press F5 in VS Code
```

## License

MIT
