# By Moh0py dev github.com/Moh0py
import argparse
import sys
import os
from typing import List

from checker import InstagramUsernameChecker
from utils import (
    display_banner, 
    print_colored_message, 
    get_user_input_usernames, 
    create_sample_usernames_file,
    validate_username
)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Instagram Username Checker - Check username availability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --usernames test_user sample_name check_this
  %(prog)s --file usernames.txt --proxy http://proxy:8080
  %(prog)s --generate myname --count 15
  %(prog)s --interactive --verbose
  %(prog)s --create-sample --sample-count 25
        """
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--usernames', '-u',
        nargs='+',
        help='List of usernames to check'
    )
    input_group.add_argument(
        '--file', '-f',
        type=str,
        help='File containing usernames (one per line)'
    )
    input_group.add_argument(
        '--generate', '-g',
        type=str,
        help='Generate variations of a base username'
    )
    input_group.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive mode - enter usernames manually'
    )
    input_group.add_argument(
        '--create-sample',
        action='store_true',
        help='Create a sample usernames file for testing'
    )
    
    parser.add_argument(
        '--count', '-c',
        type=int,
        default=10,
        help='Number of variations to generate (default: 10)'
    )
    parser.add_argument(
        '--sample-count',
        type=int,
        default=20,
        help='Number of sample usernames to create (default: 20)'
    )
    
    parser.add_argument(
        '--proxy', '-p',
        type=str,
        help='Proxy URL (e.g., http://proxy:8080)'
    )
    parser.add_argument(
        '--no-api',
        action='store_true',
        help='Skip API method, use only profile checking'
    )
    
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=3,
        help='Maximum concurrent threads (default: 3)'
    )
    parser.add_argument(
        '--min-delay',
        type=float,
        default=2.0,
        help='Minimum delay between requests in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--max-delay',
        type=float,
        default=5.0,
        help='Maximum delay between requests in seconds (default: 5.0)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='./results',
        help='Output directory for results (default: ./results)'
    )
    parser.add_argument(
        '--no-csv',
        action='store_true',
        help='Skip CSV export'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Skip saving results to files'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Quiet mode - minimal output'
    )
    
    return parser.parse_args()


def validate_proxy(proxy: str) -> bool:
    """Validate proxy URL format"""
    if not proxy:
        return True
    
    valid_prefixes = ['http://', 'https://', 'socks4://', 'socks5://']
    return any(proxy.startswith(prefix) for prefix in valid_prefixes)


def main():
    """Main execution function"""
    args = parse_arguments()
    
    if not args.quiet:
        display_banner()
    
    if args.proxy and not validate_proxy(args.proxy):
        print_colored_message("❌ Invalid proxy format. Use: http://proxy:port", "red")
        sys.exit(1)
    
    if args.create_sample:
        filename = "sample_usernames.txt"
        create_sample_usernames_file(filename, args.sample_count)
        print_colored_message(f"\n✅ Sample file created: {filename}", "green")
        print_colored_message(f"💡 Now you can run: python {sys.argv[0]} --file {filename}", "cyan")
        return
    
    try:
        checker = InstagramUsernameChecker(
            proxy=args.proxy,
            max_workers=args.workers,
            min_delay=args.min_delay,
            max_delay=args.max_delay,
            verbose=args.verbose and not args.quiet
        )
    except Exception as e:
        print_colored_message(f"❌ Failed to initialize checker: {e}", "red")
        sys.exit(1)
    
    usernames = []
    
    if args.usernames:
        usernames = args.usernames
        if not args.quiet:
            print_colored_message(f"📝 Checking {len(usernames)} provided usernames", "cyan")
    
    elif args.file:
        if not os.path.exists(args.file):
            print_colored_message(f"❌ File not found: {args.file}", "red")
            sys.exit(1)
        
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                usernames = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if not args.quiet:
                print_colored_message(f"📂 Loaded {len(usernames)} usernames from {args.file}", "cyan")
        except Exception as e:
            print_colored_message(f"❌ Error reading file: {e}", "red")
            sys.exit(1)
    
    elif args.generate:
        if not validate_username(args.generate):
            print_colored_message(f"❌ Invalid base username: {args.generate}", "red")
            sys.exit(1)
        
        usernames = checker.generate_username_variations(args.generate, args.count)
        if not args.quiet:
            print_colored_message(f"🎲 Generated {len(usernames)} variations of '{args.generate}'", "cyan")
    
    elif args.interactive:
        if not args.quiet:
            print_colored_message("🔄 Interactive mode - Enter usernames manually", "cyan")
        usernames = get_user_input_usernames()
        if not usernames:
            print_colored_message("❌ No valid usernames entered", "yellow")
            sys.exit(0)
    
    valid_usernames = []
    invalid_count = 0
    
    for username in usernames:
        if validate_username(username):
            valid_usernames.append(username)
        else:
            invalid_count += 1
            if not args.quiet:
                print_colored_message(f"⚠️  Skipping invalid username: {username}", "yellow")
    
    if not valid_usernames:
        print_colored_message("❌ No valid usernames to check", "red")
        sys.exit(1)
    
    if invalid_count > 0 and not args.quiet:
        print_colored_message(f"⚠️  Skipped {invalid_count} invalid usernames", "yellow")
    
    if not args.quiet:
        print_colored_message(f"\n🚀 Starting check for {len(valid_usernames)} usernames...", "green")
        if args.proxy:
            print_colored_message(f"🔒 Using proxy: {args.proxy}", "blue")
        if args.no_api:
            print_colored_message("⚠️  API method disabled - using profile checking only", "yellow")
    
    try:
        results = checker.check_usernames_list(valid_usernames, use_api=not args.no_api)
    except KeyboardInterrupt:
        print_colored_message("\n\n⚠️  Process interrupted by user", "yellow")
        if not args.quiet:
            stats = checker.get_stats()
            print_colored_message(f"📊 Partial results: {stats}", "blue")
    except Exception as e:
        print_colored_message(f"\n❌ Error during checking: {e}", "red")
        sys.exit(1)
    
    if not args.quiet:
        stats = checker.get_stats()
        print_colored_message(f"\n📊 Final Statistics:", "white")
        print_colored_message(f"   Total Checked: {stats['total_checked']}", "cyan")
        print_colored_message(f"   Available: {stats['available']}", "green")
        print_colored_message(f"   Unavailable: {stats['unavailable']}", "red")
        print_colored_message(f"   Errors: {stats['errors']}", "yellow")
        print_colored_message(f"   Success Rate: {stats['success_rate']:.1f}%", "blue")
    
    if not args.no_save:
        try:
            checker.save_results(args.output, save_csv=not args.no_csv)
        except Exception as e:
            print_colored_message(f"❌ Error saving results: {e}", "red")
    
    if args.quiet:
        stats = checker.get_stats()
        print(f"Checked: {stats['total_checked']}, Available: {stats['available']}, "
              f"Unavailable: {stats['unavailable']}, Errors: {stats['errors']}")


def interactive_menu():
    """Interactive menu for advanced usage"""
    display_banner()
    
    while True:
        print_colored_message("\n" + "="*50, "white")
        print_colored_message("INTERACTIVE MENU", "white")
        print_colored_message("="*50, "white")
        print_colored_message("1. Check usernames from list", "cyan")
        print_colored_message("2. Check usernames from file", "cyan")
        print_colored_message("3. Generate and check variations", "cyan")
        print_colored_message("4. Create sample file", "cyan")
        print_colored_message("5. Configure settings", "cyan")
        print_colored_message("6. Exit", "cyan")
        
        try:
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == '1':
                usernames = get_user_input_usernames()
                if usernames:
                    checker = InstagramUsernameChecker(verbose=True)
                    checker.check_usernames_list(usernames)
                    checker.save_results()
            
            elif choice == '2':
                filename = input("Enter filename: ").strip()
                if os.path.exists(filename):
                    checker = InstagramUsernameChecker(verbose=True)
                    checker.check_usernames_from_file(filename)
                    checker.save_results()
                else:
                    print_colored_message(f"File not found: {filename}", "red")
            
            elif choice == '3':
                base = input("Enter base username: ").strip()
                if validate_username(base):
                    count = int(input("Number of variations (default 10): ") or "10")
                    checker = InstagramUsernameChecker(verbose=True)
                    variations = checker.generate_username_variations(base, count)
                    checker.check_usernames_list(variations)
                    checker.save_results()
                else:
                    print_colored_message("Invalid base username", "red")
            
            elif choice == '4':
                count = int(input("Number of sample usernames (default 20): ") or "20")
                create_sample_usernames_file("sample_usernames.txt", count)
            
            elif choice == '5':
                print_colored_message("Configuration options:", "yellow")
                print_colored_message("- Proxy support", "white")
                print_colored_message("- Thread count adjustment", "white")
                print_colored_message("- Delay settings", "white")
                print_colored_message("- Verbose mode", "white")
                print_colored_message("Use command-line arguments for configuration", "cyan")
            
            elif choice == '6':
                print_colored_message("👋 Goodbye!", "green")
                break
            
            else:
                print_colored_message("Invalid choice. Please select 1-6.", "yellow")
                
        except KeyboardInterrupt:
            print_colored_message("\n\n👋 Goodbye!", "green")
            break
        except ValueError:
            print_colored_message("Invalid input. Please enter a number.", "yellow")
        except Exception as e:
            print_colored_message(f"Error: {e}", "red")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        interactive_menu()
    else:
        main()
