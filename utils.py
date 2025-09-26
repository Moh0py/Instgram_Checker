# By Moh0py dev github.com/Moh0py
import logging
import time
import random
import re
from colorama import Fore, Style, init

init(autoreset=True)


def setup_logging(level=logging.INFO):
    """
    Set up logging configuration with timestamp and level formatting
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger instance
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('instagram_checker.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)


def random_delay(min_seconds=None, max_seconds=None, logger=None, default_min=2.0, default_max=5.0):
    """
    Apply random delay to avoid rate limiting and detection
    
    Args:
        min_seconds: Minimum delay time
        max_seconds: Maximum delay time
        logger: Logger instance for debug messages
        default_min: Default minimum delay if min_seconds is None
        default_max: Default maximum delay if max_seconds is None
    """
    min_sec = min_seconds if min_seconds is not None else default_min
    max_sec = max_seconds if max_seconds is not None else default_max
    
    delay = random.uniform(min_sec, max_sec)
    
    if logger:
        logger.debug(f"Applying random delay: {delay:.2f} seconds")
    
    time.sleep(delay)


def validate_username(username):
    """
    Validate Instagram username according to platform rules
    
    Instagram username rules:
    - 1-30 characters long
    - Only letters, numbers, underscores, and periods
    - Cannot start or end with underscore or period
    - Cannot contain consecutive periods or underscores
    
    Args:
        username: Username string to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not username or not isinstance(username, str):
        return False
    
    if not (1 <= len(username) <= 30):
        return False
    
    if not re.match(r'^[a-zA-Z0-9._]+$', username):
        return False
    
    if username.startswith(('.', '_')) or username.endswith(('.', '_')):
        return False
    
    if '..' in username or '__' in username:
        return False
    
    return True


def print_colored_message(message, color):
    """
    Print colored message to console using colorama
    
    Args:
        message: Message text to display
        color: Color name (red, green, blue, yellow, cyan, magenta, white)
    """
    color_map = {
        'red': Fore.RED,
        'green': Fore.GREEN,
        'blue': Fore.BLUE,
        'yellow': Fore.YELLOW,
        'cyan': Fore.CYAN,
        'magenta': Fore.MAGENTA,
        'white': Fore.WHITE,
        'black': Fore.BLACK
    }
    
    color_code = color_map.get(color.lower(), Fore.WHITE)
    print(f"{color_code}{message}{Style.RESET_ALL}")


def format_results_summary(available_count, unavailable_count, error_count):
    """
    Format and display results summary with colors
    
    Args:
        available_count: Number of available usernames
        unavailable_count: Number of unavailable usernames
        error_count: Number of errors encountered
    """
    total = available_count + unavailable_count + error_count
    
    print_colored_message("\n" + "="*60, "white")
    print_colored_message("FINAL SUMMARY", "white")
    print_colored_message("="*60, "white")
    print_colored_message(f"✅ Available: {available_count}", "green")
    print_colored_message(f"❌ Unavailable: {unavailable_count}", "red")
    print_colored_message(f"⚠️  Errors: {error_count}", "yellow")
    print_colored_message(f"📊 Total Checked: {total}", "cyan")
    
    if total > 0:
        success_rate = ((available_count + unavailable_count) / total) * 100
        print_colored_message(f"🎯 Success Rate: {success_rate:.1f}%", "blue")
    
    print_colored_message("="*60, "white")


def create_sample_usernames_file(filename="sample_usernames.txt", count=20):
    """
    Create a sample file with usernames for testing
    
    Args:
        filename: Output filename
        count: Number of sample usernames to generate
    """
    sample_usernames = [
        "test_user_123",
        "available_name_456",
        "sample_username",
        "check_this_name",
        "instagram_test",
        "username_checker",
        "available_user",
        "test_account_2024",
        "sample_profile",
        "check_availability",
        "new_user_test",
        "username_validator",
        "profile_checker",
        "account_tester",
        "user_availability",
        "name_checker_tool",
        "instagram_validator",
        "profile_test_user",
        "account_checker_2024",
        "username_test_tool"
    ]
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# Sample usernames for Instagram Username Checker\n")
        f.write("# Lines starting with # are ignored\n\n")
        
        for i, username in enumerate(sample_usernames[:count], 1):
            f.write(f"{username}\n")
    
    print_colored_message(f"Created sample file: {filename} with {min(count, len(sample_usernames))} usernames", "green")


def get_user_input_usernames():
    """
    Get usernames from user input (interactive mode)
    
    Returns:
        List of usernames entered by user
    """
    print_colored_message("\n📝 Enter usernames to check (one per line, empty line to finish):", "cyan")
    usernames = []
    
    while True:
        try:
            username = input("Username: ").strip()
            if not username:
                break
            if validate_username(username):
                usernames.append(username)
                print_colored_message(f"✅ Added: {username}", "green")
            else:
                print_colored_message(f"❌ Invalid username format: {username}", "red")
        except KeyboardInterrupt:
            print_colored_message("\n\n⚠️  Input cancelled by user", "yellow")
            break
    
    return usernames


def display_banner():
    """Display application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                 Instagram Username Checker                   ║
║                     Version 1.0 v                            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print_colored_message(banner, "cyan")


if __name__ == "__main__":
    display_banner()
    
    test_usernames = ["valid_user", "invalid..user", "_invalid", "valid123", "toolongusernamethatexceedslimit"]
    
    print_colored_message("\n🧪 Testing username validation:", "yellow")
    for username in test_usernames:
        is_valid = validate_username(username)
        status = "✅ Valid" if is_valid else "❌ Invalid"
        print_colored_message(f"{status}: {username}", "green" if is_valid else "red")
    
    print_colored_message("\n🎨 Testing colored output:", "yellow")
    colors = ["red", "green", "blue", "yellow", "cyan", "magenta", "white"]
    for color in colors:
        print_colored_message(f"This is {color} text", color)
    
    create_sample_usernames_file()
