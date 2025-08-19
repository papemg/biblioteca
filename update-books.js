#!/usr/bin/env node

/**
 * Book List Update Script
 * 
 * This script helps you quickly commit and push changes to your book list.
 * Run with: node update-books.js [commit message]
 * 
 * If no commit message is provided, it will use a default one with timestamp.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Colors for console output
const colors = {
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    red: '\x1b[31m',
    blue: '\x1b[34m',
    reset: '\x1b[0m',
    bold: '\x1b[1m'
};

function log(message, color = colors.reset) {
    console.log(`${color}${message}${colors.reset}`);
}

function runCommand(command, description) {
    try {
        log(`${colors.blue}${description}...${colors.reset}`);
        const output = execSync(command, { encoding: 'utf8', stdio: 'pipe' });
        if (output.trim()) {
            console.log(output.trim());
        }
        return true;
    } catch (error) {
        log(`❌ Error: ${error.message}`, colors.red);
        return false;
    }
}

function checkGitRepo() {
    try {
        execSync('git rev-parse --git-dir', { stdio: 'pipe' });
        return true;
    } catch {
        log('❌ This is not a Git repository. Please run "git init" first.', colors.red);
        return false;
    }
}

function checkBooksFile() {
    if (!fs.existsSync('books.md')) {
        log('❌ books.md file not found. Please create it first.', colors.red);
        return false;
    }
    return true;
}

function getCommitMessage() {
    const args = process.argv.slice(2);
    
    if (args.length > 0) {
        return args.join(' ');
    }
    
    // Generate default commit message with timestamp
    const now = new Date();
    const date = now.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
    const time = now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    return `Update book list - ${date} at ${time}`;
}

function hasChanges() {
    try {
        const status = execSync('git status --porcelain', { encoding: 'utf8' });
        return status.trim().length > 0;
    } catch {
        return false;
    }
}

function main() {
    log(`${colors.bold}📚 Book List Update Script${colors.reset}\n`);
    
    // Check prerequisites
    if (!checkGitRepo() || !checkBooksFile()) {
        process.exit(1);
    }
    
    // Check if there are any changes
    if (!hasChanges()) {
        log('✨ No changes detected. Your book list is up to date!', colors.green);
        return;
    }
    
    const commitMessage = getCommitMessage();
    log(`📝 Commit message: "${commitMessage}"\n`);
    
    // Git workflow
    const steps = [
        ['git add .', 'Adding changes to staging area'],
        [`git commit -m "${commitMessage}"`, 'Creating commit'],
        ['git push', 'Pushing to GitHub']
    ];
    
    for (const [command, description] of steps) {
        if (!runCommand(command, description)) {
            log('\n❌ Update failed. Please check the error above.', colors.red);
            process.exit(1);
        }
    }
    
    log('\n✅ Book list updated successfully!', colors.green);
    log('🌐 Your changes should be live on GitHub Pages in a few minutes.', colors.yellow);
}

// Show help if requested
if (process.argv.includes('--help') || process.argv.includes('-h')) {
    console.log(`
📚 Book List Update Script

Usage:
  node update-books.js [commit message]

Examples:
  node update-books.js                    # Uses automatic commit message
  node update-books.js "Added 5 new books to wishlist"
  node update-books.js "Finished reading Dune"

This script will:
1. Add all changes to git
2. Create a commit with your message (or auto-generated one)
3. Push the changes to GitHub

Make sure you're in a git repository and have a books.md file.
`);
    process.exit(0);
}

main();