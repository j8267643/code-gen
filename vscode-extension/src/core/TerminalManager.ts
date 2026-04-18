import * as vscode from 'vscode';

export interface TerminalCommand {
    command: string;
    cwd?: string;
    description?: string;
}

export interface TerminalOutput {
    command: string;
    stdout: string;
    stderr: string;
    exitCode: number | null;
}

export class TerminalManager {
    private _terminals: Map<string, vscode.Terminal> = new Map();
    private _outputBuffer: Map<string, string> = new Map();

    async executeCommand(cmd: TerminalCommand): Promise<TerminalOutput> {
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

    async executeInBackground(command: string, cwd?: string): Promise<string> {
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
        } catch (error: any) {
            throw new Error(`Command failed: ${error.message}\n${error.stderr || ''}`);
        }
    }

    getOrCreateTerminal(name: string): vscode.Terminal {
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

    showTerminal(name: string = 'CodeGen'): void {
        const terminal = this.getOrCreateTerminal(name);
        terminal.show();
    }

    hideTerminal(name: string = 'CodeGen'): void {
        const terminal = this._terminals.get(name);
        if (terminal) {
            terminal.hide();
        }
    }

    disposeTerminal(name: string = 'CodeGen'): void {
        const terminal = this._terminals.get(name);
        if (terminal) {
            terminal.dispose();
            this._terminals.delete(name);
        }
    }

    sendTextToTerminal(text: string, name: string = 'CodeGen', addNewLine: boolean = true): void {
        const terminal = this.getOrCreateTerminal(name);
        terminal.sendText(text, addNewLine);
    }

    async runPythonScript(script: string, args: string[] = []): Promise<string> {
        const command = `python "${script}" ${args.join(' ')}`;
        return this.executeInBackground(command);
    }

    async runNpmScript(script: string): Promise<string> {
        const command = `npm run ${script}`;
        return this.executeInBackground(command);
    }

    async installDependencies(packageManager: 'npm' | 'yarn' | 'pnpm' = 'npm'): Promise<string> {
        const command = `${packageManager} install`;
        return this.executeInBackground(command);
    }

    async gitCommand(args: string): Promise<string> {
        const command = `git ${args}`;
        return this.executeInBackground(command);
    }

    getWorkingDirectory(): string | undefined {
        return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    }

    async detectPackageManager(): Promise<'npm' | 'yarn' | 'pnpm'> {
        const fs = require('fs').promises;
        const cwd = this.getWorkingDirectory();
        
        if (!cwd) {
            return 'npm';
        }

        try {
            await fs.access(`${cwd}/pnpm-lock.yaml`);
            return 'pnpm';
        } catch {}

        try {
            await fs.access(`${cwd}/yarn.lock`);
            return 'yarn';
        } catch {}

        return 'npm';
    }

    async listFiles(dir: string = '.'): Promise<string> {
        const command = process.platform === 'win32' ? 'dir' : 'ls -la';
        return this.executeInBackground(command, dir);
    }

    dispose(): void {
        for (const terminal of this._terminals.values()) {
            terminal.dispose();
        }
        this._terminals.clear();
    }
}
