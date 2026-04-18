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
exports.AIService = void 0;
const vscode = __importStar(require("vscode"));
class AIService {
    constructor(config) {
        this.config = config;
    }
    updateConfig(config) {
        this.config = config;
    }
    async *streamChat(messages) {
        if (!this.config.apiKey) {
            throw new Error('API key not configured. Please set your API key in settings.');
        }
        // Support for different providers
        if (this.config.baseUrl?.includes('openai')) {
            yield* this.streamOpenAI(messages);
        }
        else if (this.config.baseUrl?.includes('anthropic') || this.config.model.includes('claude')) {
            yield* this.streamAnthropic(messages);
        }
        else {
            // Default to simulated response for demo
            yield* this.simulateResponse(messages);
        }
    }
    async *streamOpenAI(messages) {
        const url = this.config.baseUrl || 'https://api.openai.com/v1/chat/completions';
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.config.apiKey}`
            },
            body: JSON.stringify({
                model: this.config.model,
                messages: messages,
                max_tokens: this.config.maxTokens,
                temperature: this.config.temperature,
                stream: true
            })
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`API Error: ${error}`);
        }
        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error('Failed to get response reader');
        }
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done)
                break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]')
                        return;
                    try {
                        const json = JSON.parse(data);
                        const content = json.choices?.[0]?.delta?.content;
                        if (content) {
                            yield content;
                        }
                    }
                    catch (e) {
                        // Ignore parsing errors
                    }
                }
            }
        }
    }
    async *streamAnthropic(messages) {
        const url = this.config.baseUrl || 'https://api.anthropic.com/v1/messages';
        // Convert messages to Anthropic format
        const systemMessage = messages.find(m => m.role === 'system')?.content || '';
        const conversationMessages = messages.filter(m => m.role !== 'system');
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': this.config.apiKey,
                'anthropic-version': '2023-06-01'
            },
            body: JSON.stringify({
                model: this.config.model,
                max_tokens: this.config.maxTokens,
                temperature: this.config.temperature,
                system: systemMessage,
                messages: conversationMessages.map(m => ({
                    role: m.role,
                    content: m.content
                })),
                stream: true
            })
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`API Error: ${error}`);
        }
        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error('Failed to get response reader');
        }
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done)
                break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]')
                        return;
                    try {
                        const json = JSON.parse(data);
                        const content = json.delta?.text;
                        if (content) {
                            yield content;
                        }
                    }
                    catch (e) {
                        // Ignore parsing errors
                    }
                }
            }
        }
    }
    async *simulateResponse(messages) {
        // Demo mode - simulate streaming response
        const lastMessage = messages[messages.length - 1];
        const text = lastMessage.content;
        const responses = {
            '分析': `I'll analyze this code for you.

This appears to be a well-structured module with clear separation of concerns. Here are my observations:

1. **Architecture**: The code follows a modular design pattern
2. **Code Quality**: Clean and readable with proper naming conventions
3. **Potential Improvements**:
   - Consider adding more error handling
   - Add type hints for better maintainability
   - Include unit tests for critical functions

Would you like me to suggest specific improvements?`,
            'fix': `I can help fix issues in your code. Let me analyze the problems:

\`\`\`python
# Fixed version
def improved_function():
    try:
        result = process_data()
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
\`\`\`

Key changes made:
1. Added proper error handling with try-except
2. Added logging for debugging
3. Return None on error instead of crashing

Let me know if you need more specific fixes!`,
            'improve': `Here are some improvements for your code:

\`\`\`python
# Optimized version
from typing import Optional, List
from functools import lru_cache

@lru_cache(maxsize=128)
def optimized_function(data: str) -> Optional[dict]:
    \"\"\"Process data with caching for better performance.\"\"\"\n    if not data:
        return None
    
    result = {
        'processed': data.upper(),
        'length': len(data),
        'timestamp': time.time()
    }
    return result
\`\`\`

Improvements:
1. Added type hints for better IDE support
2. Implemented caching with @lru_cache
3. Added docstring for documentation
4. Improved input validation
5. Better return type handling`,
            'explain': `Let me explain this code:

This code implements a **provider pattern** for managing webview content in VS Code extensions. Here's how it works:

1. **Purpose**: Creates and manages the sidebar webview interface
2. **Key Components**:
   - \`resolveWebviewView\`: Initializes the webview
   - \`_getHtmlForWebview\`: Generates the HTML content
   - Message handlers for communication

3. **Communication Flow**:
   - Webview sends messages via \`vscode.postMessage\`
   - Extension receives and processes messages
   - Extension sends responses back to webview

4. **Security**: Uses CSP (Content Security Policy) and nonces for safe script execution`
        };
        // Find matching response
        let responseText = responses['explain'];
        for (const [key, value] of Object.entries(responses)) {
            if (text.toLowerCase().includes(key)) {
                responseText = value;
                break;
            }
        }
        // Stream the response word by word
        const words = responseText.split(/(\s+)/);
        for (const word of words) {
            yield word;
            await new Promise(resolve => setTimeout(resolve, 20));
        }
    }
    static getDefaultConfig() {
        const config = vscode.workspace.getConfiguration('codegen');
        return {
            apiKey: config.get('apiKey') || '',
            model: config.get('model') || 'claude-3-sonnet-20240229',
            baseUrl: config.get('baseUrl') || '',
            maxTokens: config.get('maxTokens') || 4096,
            temperature: config.get('temperature') || 0.7
        };
    }
}
exports.AIService = AIService;
//# sourceMappingURL=AIService.js.map