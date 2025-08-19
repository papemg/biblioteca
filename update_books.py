#!/usr/bin/env python3
"""
Enhanced Book List Update Script with Logging

This script helps you quickly commit and push changes to your book list
while automatically tracking changes in a log file.

Usage: python update_books.py [commit message]

Features:
- Automatically detects book additions, removals, and status changes
- Creates detailed logs in books_log.json
- Supports rollback functionality
- Generates commit messages based on detected changes
"""

import subprocess
import sys
import os
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Set

# ANSI color codes for pretty output
class Colors:
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    BLUE = '\033[34m'
    PURPLE = '\033[35m'
    CYAN = '\033[36m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

class BookTracker:
    def __init__(self):
        self.log_file = 'books_log.json'
        self.books_file = 'books.md'
        self.current_books = {'wanted': set(), 'owned': set()}
        self.previous_books = {'wanted': set(), 'owned': set()}
        
    def log(self, message, color=Colors.RESET):
        """Print colored message to console"""
        print(f"{color}{message}{Colors.RESET}")

    def run_command(self, command, description, capture_output=True):
        """Run a shell command and handle errors"""
        try:
            if description:
                self.log(f"{Colors.BLUE}{description}...{Colors.RESET}")
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=capture_output, 
                text=True, 
                check=True
            )
            if result.stdout.strip() and capture_output:
                print(result.stdout.strip())
            return result.stdout if capture_output else True
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            if error_msg:
                self.log(f"❌ Error: {error_msg}", Colors.RED)
            else:
                self.log(f"❌ Command failed: {command}", Colors.RED)
            return None

    def parse_books_from_markdown(self, content: str) -> Dict[str, Set[str]]:
        """Extract books from markdown content"""
        books = {'wanted': set(), 'owned': set()}
        
        # Regex to match book entries: - [x] **Title** by *Author*
        pattern = r'- \[([ x])\] \*\*(.*?)\*\* by \*(.*?)\*'
        matches = re.findall(pattern, content)
        
        for status, title, author in matches:
            book_entry = f"{title} by {author}"
            if status == 'x':
                books['owned'].add(book_entry)
            else:
                books['wanted'].add(book_entry)
        
        return books

    def get_current_books(self) -> Dict[str, Set[str]]:
        """Get current books from the markdown file"""
        try:
            with open(self.books_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.parse_books_from_markdown(content)
        except FileNotFoundError:
            self.log(f"❌ {self.books_file} not found", Colors.RED)
            return {'wanted': set(), 'owned': set()}

    def get_previous_books(self) -> Dict[str, Set[str]]:
        """Get previous books from git history"""
        try:
            # Get the last committed version of books.md
            result = self.run_command(
                f"git show HEAD:{self.books_file}", 
                None, 
                capture_output=True
            )
            if result:
                return self.parse_books_from_markdown(result)
        except:
            pass
        return {'wanted': set(), 'owned': set()}

    def detect_changes(self) -> Dict[str, List[str]]:
        """Detect what changed between previous and current book lists"""
        self.current_books = self.get_current_books()
        self.previous_books = self.get_previous_books()
        
        changes = {
            'books_added_to_wanted': [],
            'books_removed_from_wanted': [],
            'books_added_to_owned': [],
            'books_removed_from_owned': [],
            'books_bought': [],  # moved from wanted to owned
            'books_returned': [] # moved from owned to wanted
        }
        
        # Find additions and removals
        changes['books_added_to_wanted'] = list(
            self.current_books['wanted'] - self.previous_books['wanted']
        )
        changes['books_removed_from_wanted'] = list(
            self.previous_books['wanted'] - self.current_books['wanted']
        )
        changes['books_added_to_owned'] = list(
            self.current_books['owned'] - self.previous_books['owned']
        )
        changes['books_removed_from_owned'] = list(
            self.previous_books['owned'] - self.current_books['owned']
        )
        
        # Detect books that moved from wanted to owned (bought)
        potential_bought = set(changes['books_added_to_owned']) & set(changes['books_removed_from_wanted'])
        changes['books_bought'] = list(potential_bought)
        
        # Remove bought books from regular additions/removals
        changes['books_added_to_owned'] = [
            book for book in changes['books_added_to_owned'] 
            if book not in potential_bought
        ]
        changes['books_removed_from_wanted'] = [
            book for book in changes['books_removed_from_wanted'] 
            if book not in potential_bought
        ]
        
        # Detect books that moved from owned to wanted (returned/sold)
        potential_returned = set(changes['books_added_to_wanted']) & set(changes['books_removed_from_owned'])
        changes['books_returned'] = list(potential_returned)
        
        # Remove returned books from regular additions/removals
        changes['books_added_to_wanted'] = [
            book for book in changes['books_added_to_wanted'] 
            if book not in potential_returned
        ]
        changes['books_removed_from_owned'] = [
            book for book in changes['books_removed_from_owned'] 
            if book not in potential_returned
        ]
        
        return changes

    def load_log(self) -> List[Dict]:
        """Load existing log entries"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_log(self, log_entries: List[Dict]):
        """Save log entries to file"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(log_entries, f, indent=2, ensure_ascii=False)

    def add_log_entry(self, changes: Dict[str, List[str]], commit_message: str):
        """Add a new log entry"""
        log_entries = self.load_log()
        
        timestamp = datetime.now().isoformat()
        
        entry = {
            'timestamp': timestamp,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'commit_message': commit_message,
            'changes': changes,
            'totals_after': {
                'wanted': len(self.current_books['wanted']),
                'owned': len(self.current_books['owned']),
                'total': len(self.current_books['wanted']) + len(self.current_books['owned'])
            }
        }
        
        log_entries.append(entry)
        self.save_log(log_entries)
        
        return entry

    def generate_commit_message(self, changes: Dict[str, List[str]], custom_message: str = None) -> str:
        """Generate a commit message based on detected changes"""
        if custom_message:
            return custom_message
        
        messages = []
        
        if changes['books_bought']:
            count = len(changes['books_bought'])
            messages.append(f"📚 Bought {count} book{'s' if count > 1 else ''}")
        
        if changes['books_added_to_wanted']:
            count = len(changes['books_added_to_wanted'])
            messages.append(f"🛒 Added {count} book{'s' if count > 1 else ''} to wishlist")
        
        if changes['books_added_to_owned']:
            count = len(changes['books_added_to_owned'])
            messages.append(f"📖 Added {count} owned book{'s' if count > 1 else ''}")
        
        if changes['books_removed_from_wanted']:
            count = len(changes['books_removed_from_wanted'])
            messages.append(f"🗑️ Removed {count} book{'s' if count > 1 else ''} from wishlist")
        
        if changes['books_removed_from_owned']:
            count = len(changes['books_removed_from_owned'])
            messages.append(f"📤 Removed {count} owned book{'s' if count > 1 else ''}")
        
        if changes['books_returned']:
            count = len(changes['books_returned'])
            messages.append(f"↩️ Returned {count} book{'s' if count > 1 else ''}")
        
        if not messages:
            return f"📝 Update book list - {datetime.now().strftime('%b %d, %Y at %I:%M %p')}"
        
        return " • ".join(messages)

    def print_changes_summary(self, changes: Dict[str, List[str]]):
        """Print a summary of detected changes"""
        self.log(f"\n{Colors.BOLD}📊 Changes Detected:{Colors.RESET}\n")
        
        if changes['books_bought']:
            self.log(f"{Colors.GREEN}📚 Books Bought ({len(changes['books_bought'])}):{Colors.RESET}")
            for book in changes['books_bought']:
                self.log(f"  • {book}", Colors.GREEN)
            print()
        
        if changes['books_added_to_wanted']:
            self.log(f"{Colors.BLUE}🛒 Added to Wishlist ({len(changes['books_added_to_wanted'])}):{Colors.RESET}")
            for book in changes['books_added_to_wanted']:
                self.log(f"  • {book}", Colors.BLUE)
            print()
        
        if changes['books_added_to_owned']:
            self.log(f"{Colors.CYAN}📖 Added to Owned ({len(changes['books_added_to_owned'])}):{Colors.RESET}")
            for book in changes['books_added_to_owned']:
                self.log(f"  • {book}", Colors.CYAN)
            print()
        
        if changes['books_removed_from_wanted']:
            self.log(f"{Colors.YELLOW}🗑️ Removed from Wishlist ({len(changes['books_removed_from_wanted'])}):{Colors.RESET}")
            for book in changes['books_removed_from_wanted']:
                self.log(f"  • {book}", Colors.YELLOW)
            print()
        
        if changes['books_removed_from_owned']:
            self.log(f"{Colors.PURPLE}📤 Removed from Owned ({len(changes['books_removed_from_owned'])}):{Colors.RESET}")
            for book in changes['books_removed_from_owned']:
                self.log(f"  • {book}", Colors.PURPLE)
            print()
        
        if changes['books_returned']:
            self.log(f"{Colors.RED}↩️ Books Returned ({len(changes['books_returned'])}):{Colors.RESET}")
            for book in changes['books_returned']:
                self.log(f"  • {book}", Colors.RED)
            print()

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        # Check if it's a git repository
        if not self.run_command("git rev-parse --git-dir", None):
            self.log("❌ This is not a Git repository. Please run 'git init' first.", Colors.RED)
            return False
        
        # Check if books.md exists
        if not os.path.exists(self.books_file):
            self.log(f"❌ {self.books_file} file not found. Please create it first.", Colors.RED)
            return False
        
        return True

    def has_changes(self) -> bool:
        """Check if there are any uncommitted changes to books.md"""
        try:
            result = self.run_command(
                f"git status --porcelain {self.books_file}", 
                None, 
                capture_output=True
            )
            return bool(result and result.strip())
        except:
            return False

    def has_any_changes(self) -> bool:
        """Check if there are any uncommitted changes to any files"""
        try:
            result = self.run_command("git status --porcelain", None)
            return bool(result and result.strip())
        except:
            return False

def show_help():
    """Display help information"""
    help_text = f"""
{Colors.BOLD}📚 Enhanced Book List Update Script{Colors.RESET}

Usage:
  python update_books.py [commit message]

Examples:
  python update_books.py                           # Auto-detects changes and generates message
  python update_books.py "Added 5 new books to wishlist"
  python update_books.py "Finished reading Dune"

Features:
  • 🔍 Automatically detects book additions, removals, and purchases
  • 📊 Maintains detailed logs in books_log.json
  • 🎯 Generates smart commit messages based on changes
  • 📈 Tracks statistics over time for dashboard integration

Change Types Detected:
  📚 Books bought (moved from wanted to owned)
  🛒 Books added to wishlist
  📖 Books added to owned collection
  🗑️ Books removed from wishlist
  📤 Books removed from owned collection
  ↩️ Books returned (moved from owned to wanted)

This script will:
1. Analyze changes in your book list
2. Log detailed changes with timestamps
3. Generate appropriate commit messages
4. Push changes to GitHub

Options:
  --help, -h     Show this help message
  --log          Show recent log entries
  --stats        Show collection statistics
  --debug        Show git status and file information for troubleshooting
"""
    print(help_text)

def show_recent_logs(tracker: BookTracker, limit: int = 10):
    """Show recent log entries"""
    log_entries = tracker.load_log()
    
    if not log_entries:
        tracker.log("📝 No log entries found.", Colors.YELLOW)
        return
    
    tracker.log(f"\n{Colors.BOLD}📋 Recent Changes (last {min(limit, len(log_entries))}):{Colors.RESET}\n")
    
    for entry in log_entries[-limit:]:
        date = entry['date']
        time = entry['time']
        message = entry['commit_message']
        changes = entry['changes']
        
        tracker.log(f"{Colors.CYAN}{date} {time}{Colors.RESET} - {message}")
        
        # Show change counts
        change_counts = []
        if changes.get('books_bought'):
            change_counts.append(f"📚 {len(changes['books_bought'])} bought")
        if changes.get('books_added_to_wanted'):
            change_counts.append(f"🛒 +{len(changes['books_added_to_wanted'])} wanted")
        if changes.get('books_added_to_owned'):
            change_counts.append(f"📖 +{len(changes['books_added_to_owned'])} owned")
        if changes.get('books_removed_from_wanted'):
            change_counts.append(f"🗑️ -{len(changes['books_removed_from_wanted'])} wanted")
        if changes.get('books_removed_from_owned'):
            change_counts.append(f"📤 -{len(changes['books_removed_from_owned'])} owned")
        
        if change_counts:
            tracker.log(f"  {' • '.join(change_counts)}", Colors.RESET)
        
        tracker.log(f"  Total: {entry['totals_after']['wanted']} wanted, {entry['totals_after']['owned']} owned\n")

def show_stats(tracker: BookTracker):
    """Show collection statistics"""
    log_entries = tracker.load_log()
    current_books = tracker.get_current_books()
    
    tracker.log(f"\n{Colors.BOLD}📊 Collection Statistics:{Colors.RESET}\n")
    
    # Current totals
    wanted_count = len(current_books['wanted'])
    owned_count = len(current_books['owned'])
    total_count = wanted_count + owned_count
    
    tracker.log(f"Current Collection:")
    tracker.log(f"  🛒 Wanted: {wanted_count} books", Colors.BLUE)
    tracker.log(f"  📚 Owned: {owned_count} books", Colors.GREEN)
    tracker.log(f"  📖 Total: {total_count} books", Colors.BOLD)
    
    if log_entries:
        # Calculate totals from logs
        total_bought = sum(len(entry['changes'].get('books_bought', [])) for entry in log_entries)
        total_added_wanted = sum(len(entry['changes'].get('books_added_to_wanted', [])) for entry in log_entries)
        total_added_owned = sum(len(entry['changes'].get('books_added_to_owned', [])) for entry in log_entries)
        
        tracker.log(f"\nActivity Summary:")
        tracker.log(f"  📚 Total books bought: {total_bought}", Colors.GREEN)
        tracker.log(f"  🛒 Total added to wishlist: {total_added_wanted}", Colors.BLUE)
        tracker.log(f"  📖 Total added to owned: {total_added_owned}", Colors.CYAN)
        tracker.log(f"  📝 Total log entries: {len(log_entries)}", Colors.YELLOW)
        
        if log_entries:
            first_entry = log_entries[0]['date']
            last_entry = log_entries[-1]['date']
            tracker.log(f"  📅 Tracking since: {first_entry}", Colors.PURPLE)

def main():
    """Main function"""
    tracker = BookTracker()
    
    # Check for help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        return
    
    # Check for log flag
    if '--log' in sys.argv:
        show_recent_logs(tracker)
        return
    
    # Check for stats flag
    if '--stats' in sys.argv:
        show_stats(tracker)
        return
    
    # Check for debug flag
    if '--debug' in sys.argv:
        tracker.log("🔍 Debug mode - showing current git status:", Colors.CYAN)
        tracker.run_command("git status", None, capture_output=False)
        tracker.log("\n📁 Current directory contents:", Colors.CYAN)
        tracker.run_command("ls -la", None, capture_output=False)
        if os.path.exists(tracker.log_file):
            tracker.log(f"\n📝 Log file exists: {tracker.log_file}", Colors.GREEN)
        else:
            tracker.log(f"\n📝 Log file does not exist: {tracker.log_file}", Colors.YELLOW)
        return
    
    tracker.log(f"{Colors.BOLD}📚 Enhanced Book List Update Script{Colors.RESET}\n")
    
    # Check prerequisites
    if not tracker.check_prerequisites():
        sys.exit(1)
    
    # Check if there are any changes to books.md specifically
    if not tracker.has_changes():
        if tracker.has_any_changes():
            tracker.log("⚠️  There are uncommitted changes to other files, but no changes to books.md", Colors.YELLOW)
            tracker.log("This script is designed to track book list changes only.", Colors.YELLOW)
            tracker.log("Please commit other changes separately or use regular git commands.", Colors.YELLOW)
            return
        else:
            tracker.log("✨ No changes detected. Your book list is up to date!", Colors.GREEN)
            return
    
    # Detect changes
    changes = tracker.detect_changes()
    
    # Check if any meaningful changes were detected
    has_meaningful_changes = any(changes[key] for key in changes.keys())
    
    if not has_meaningful_changes:
        tracker.log("📝 Changes detected but no book modifications found. Proceeding with regular commit...", Colors.YELLOW)
        changes = {key: [] for key in changes.keys()}  # Reset to empty lists
    else:
        tracker.print_changes_summary(changes)
    
    # Get commit message
    custom_message = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else None
    commit_message = tracker.generate_commit_message(changes, custom_message)
    
    tracker.log(f"💬 Commit message: \"{commit_message}\"\n")
    
    # Add log entry
    if has_meaningful_changes:
        log_entry = tracker.add_log_entry(changes, commit_message)
        tracker.log(f"📝 Logged changes to {tracker.log_file}", Colors.GREEN)
    
    # Git workflow steps - only add books.md and books_log.json
    steps = [
        (f"git add {tracker.books_file}", "Adding book list changes to staging area"),
    ]
    
    # Add log file if it exists and has meaningful changes
    if has_meaningful_changes and os.path.exists(tracker.log_file):
        steps.append((f"git add {tracker.log_file}", "Adding log file changes"))
    
    steps.extend([
        (f'git commit -m "{commit_message}"', "Creating commit"),
        ("git push", "Pushing to GitHub")
    ])
    
    # Execute each step
    for command, description in steps:
        result = tracker.run_command(command, description)
        if result is None:
            # If it's the log file addition that failed, try without it
            if "books_log.json" in command:
                tracker.log("⚠️  Could not add log file, continuing without it...", Colors.YELLOW)
                continue
            else:
                tracker.log("\n❌ Update failed. Please check the error above.", Colors.RED)
                
                # Show git status for debugging
                tracker.log("\n🔍 Current git status:", Colors.CYAN)
                tracker.run_command("git status", None, capture_output=False)
                sys.exit(1)
    
    tracker.log("\n✅ Book list updated successfully!", Colors.GREEN)
    tracker.log("🌐 Your changes should be live on GitHub Pages in a few minutes.", Colors.YELLOW)
    
    if has_meaningful_changes:
        tracker.log(f"📊 View logs with: python {sys.argv[0]} --log", Colors.CYAN)
        tracker.log(f"📈 View stats with: python {sys.argv[0]} --stats", Colors.CYAN)

if __name__ == "__main__":
    main()
    