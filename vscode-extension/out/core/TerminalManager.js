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
exports.TerminalManager = void 0;
const vscode = __importStar(require("vscode"));
class TerminalManager {
    constructor() {
        this._terminals = new Map();
        this._outputBuffer = new Map();
    }
    async executeCommand(cmd) {
        return new Promise((resolve, reject) => {
            const terminal = this.getOrCreateTerminal('CodeGen');
            // Generate a unique marker for this command
            const marker = `__CODEGEN_OUTPUT_${Date.now()}__`;
            // Execute command and capture output
            const fullCommand = cmd.cwd
                ? `cd "${cmd.cwd}" && ${cmd.command} && echo "${marker}EXIT:$?"`
                : `${cmd.command} && echo "${marker}EXIT:$?"`;
            terminal.sendText(fullCommand);
            terminal.show();
            // For now, return a placeholder response
            // In a real implementation, you'd need to capture terminal output
            setTimeout(() => {
                resolve({
                    command: cmd.command,
                    stdout: 'Command executed in terminal',
                    stderr: '',
                    exitCode: 0
                });
            }, 100);
        });
    }
    async executeInBackground(command, cwd) {
        const { exec } = require('child_process');
        const util = require('util');
        const execAsync = util.promisify(exec);
        try {
            const { stdout, stderr } = await execAsync(command, {
                cwd: cwd || vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
                timeout: 60000,
                maxBuffer: 1024 * 1024 * 10 // 10MB
            });
            return stdout || stderr;
        }
        catch (error) {
            throw new Error(`Command failed: ${error.message}\n${error.stderr || ''}`);
        }
    }
    getOrCreateTerminal(name) {
        let terminal = this._terminals.get(name);
        if (!terminal || terminal.exitStatus !== undefined) {
            terminal = vscode.window.createTerminal({
                name: name,
                cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
            });
            this._terminals.set(name, terminal);
        }
        return terminal;
    }
    showTerminal(name = 'CodeGen') {
        const terminal = this.getOrCreateTerminal(name);
        terminal.show();
    }
    hideTerminal(name = 'CodeGen') {
        const terminal = this._terminals.get(name);
        if (terminal) {
            terminal.hide();
        }
    }
    disposeTerminal(name = 'CodeGen') {
        const terminal = this._terminals.get(name);
        if (terminal) {
            terminal.dispose();
            this._terminals.delete(name);
        }
    }
    sendTextToTerminal(text, name = 'CodeGen', addNewLine = true) {
        const terminal = this.getOrCreateTerminal(name);
        terminal.sendText(text, addNewLine);
    }
    async runPythonScript(script, args = []) {
        const command = `python "${script}" ${args.join(' ')}`;
        return this.executeInBackground(command);
    }
    async runNpmScript(script) {
        const command = `npm run ${script}`;
        return this.executeInBackground(command);
    }
    async installDependencies(packageManager = 'npm') {
        const command = `${packageManager} install`;
        return this.executeInBackground(command);
    }
    async gitCommand(args) {
        const command = `git ${args}`;
        return this.executeInBackground(command);
    }
    getWorkingDirectory() {
        return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    }
    async detectPackageManager() {
        const fs = require('fs').promises;
        const cwd = this.getWorkingDirectory();
        if (!cwd) {
            return 'npm';
        }
        try {
            await fs.access(`${cwd}/pnpm-lock.yaml`);
            return 'pnpm';
        }
        catch { }
        try {
            await fs.access(`${cwd}/yarn.lock`);
            return 'yarn';
        }
        catch { }
        return 'npm';
    }
    async listFiles(dir = '.') {
        const command = process.platform === 'win32' ? 'dir' : 'ls -la';
        return this.executeInBackground(command, dir);
    }
    dispose() {
        for (const terminal of this._terminals.values()) {
            terminal.dispose();
        }
        this._terminals.clear();
    }
}
exports.TerminalManager = TerminalManager;
//# sourceMappingURL=TerminalManager.js.map