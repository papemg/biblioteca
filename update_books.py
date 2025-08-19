#!/usr/bin/env python3
"""
Book List Update Script (Python Version)

This script helps you quickly commit and push changes to your book list.
Usage: python update_books.py [commit message]

If no commit message is provided, it will use a default one with timestamp.
"""

import subprocess
import sys
import os
from datetime import datetime

# ANSI color codes for pretty output
class Colors:
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    BLUE = '\033[34m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def log(message, color=Colors.RESET):
    """Print colored message to console"""
    print(f"{color}{message}{Colors.RESET}")

def run_command(command, description):
    """Run a shell command and handle errors"""
    try:
        log(f"{Colors.BLUE}{description}...{Colors.RESET}")
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=True
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Error: {e.stderr.strip() if e.stderr else str(e)}", Colors.RED)
        return False

def check_git_repo():
    """Check if current directory is a git repository"""
    try:
        subprocess.run(
            "git rev-parse --git-dir", 
            shell=True, 
            capture_output=True, 
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        log("❌ This is not a Git repository. Please run 'git init' first.", Colors.RED)
        return False

def check_books_file():
    """Check if books.md file exists"""
    if not os.path.exists('books.md'):
        log("❌ books.md file not found. Please create it first.", Colors.RED)
        return False
    return True

def get_commit_message():
    """Get commit message from command line args or generate default"""
    if len(sys.argv) > 1:
        return ' '.join(sys.argv[1:])
    
    # Generate default commit message with timestamp
    now = datetime.now()
    date = now.strftime("%b %d, %Y")
    time = now.strftime("%I:%M %p")
    
    return f"Update book list - {date} at {time}"

def has_changes():
    """Check if there are any uncommitted changes"""
    try:
        result = subprocess.run(
            "git status --porcelain", 
            shell=True, 
            capture_output=True, 
            text=True
        )
        return len(result.stdout.strip()) > 0
    except:
        return False

def show_help():
    """Display help information"""
    help_text = f"""
{Colors.BOLD}📚 Book List Update Script (Python){Colors.RESET}

Usage:
  python update_books.py [commit message]

Examples:
  python update_books.py                           # Uses automatic commit message
  python update_books.py "Added 5 new books to wishlist"
  python update_books.py "Finished reading Dune"

This script will:
1. Add all changes to git
2. Create a commit with your message (or auto-generated one)
3. Push the changes to GitHub

Make sure you're in a git repository and have a books.md file.

Options:
  --help, -h    Show this help message
"""
    print(help_text)

def main():
    """Main function"""
    # Check for help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        return
    
    log(f"{Colors.BOLD}📚 Book List Update Script (Python){Colors.RESET}\n")
    
    # Check prerequisites
    if not check_git_repo() or not check_books_file():
        sys.exit(1)
    
    # Check if there are any changes
    if not has_changes():
        log("✨ No changes detected. Your book list is up to date!", Colors.GREEN)
        return
    
    commit_message = get_commit_message()
    log(f"📝 Commit message: \"{commit_message}\"\n")
    
    # Git workflow steps
    steps = [
        ("git add .", "Adding changes to staging area"),
        (f'git commit -m "{commit_message}"', "Creating commit"),
        ("git push", "Pushing to GitHub")
    ]
    
    # Execute each step
    for command, description in steps:
        if not run_command(command, description):
            log("\n❌ Update failed. Please check the error above.", Colors.RED)
            sys.exit(1)
    
    log("\n✅ Book list updated successfully!", Colors.GREEN)
    log("🌐 Your changes should be live on GitHub Pages in a few minutes.", Colors.YELLOW)

if __name__ == "__main__":
    main()