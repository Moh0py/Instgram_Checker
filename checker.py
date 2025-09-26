# By Moh0py dev github.com/Moh0py
import requests
import json
import os
import csv
import random
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from colorama import init, Fore, Style

init(autoreset=True)

from utils import setup_logging, random_delay, validate_username, print_colored_message, format_results_summary


class InstagramUsernameChecker:
    """
    Instagram Username Checker Class
    
    Features:
    - Check username availability via Instagram API
    - Fallback to profile page checking
    - Proxy support for anonymity
    - Multi-threading for batch processing
    - Rate limiting and random delays
    - Comprehensive result logging and export
    """
    
    def __init__(self, proxy: Optional[str] = None, max_workers: int = 3,
                 min_delay: float = 2.0, max_delay: float = 5.0, verbose: bool = False):
        """
        Initialize Instagram Username Checker
        
        Args:
            proxy: Proxy URL (http://proxy:port)
            max_workers: Maximum concurrent threads
            min_delay: Minimum delay between requests
            max_delay: Maximum delay between requests
            verbose: Enable verbose logging
        """
        self.session = requests.Session()
        self.proxy = {'http': proxy, 'https': proxy} if proxy else None
        self.max_workers = max_workers
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.verbose = verbose
        
        level = logging.DEBUG if verbose else logging.INFO
        self.logger = setup_logging(level=level)
        
        self.available_usernames = []
        self.unavailable_usernames = []
        self.errors = []
        
        self.setup_session()
        
    def setup_session(self):
        """Set up requests session with headers and proxy configuration"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),  
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        })
        
        if self.proxy:
            self.session.proxies.update(self.proxy)
            self.logger.info(f"Proxy configured: {list(self.proxy.values())[0]}")
            if self.verbose:
                print_colored_message(f"🔒 Using Proxy: {list(self.proxy.values())[0]}", "blue")
        else:
            self.logger.info("No proxy - using direct connection")
        
        self.logger.info("Session setup completed with dynamic User-Agent")
    
    def random_delay(self, min_seconds: Optional[float] = None, max_seconds: Optional[float] = None):
        """Apply random delay using class defaults"""
        random_delay(min_seconds, max_seconds, self.logger, self.min_delay, self.max_delay)
    
    def check_username_via_profile(self, username: str) -> Tuple[Optional[bool], str]:
        """
        Check username availability via Instagram profile page
        This is used as a fallback method when API fails
        
        Args:
            username: Username to check
            
        Returns:
            Tuple of (availability_status, status_message)
        """
        try:
            url = f"https://www.instagram.com/{username}/"
            response = self.session.get(url, timeout=15, allow_redirects=True)
            
            if response.status_code == 404:
                return True, "Available (404 - Profile)"
            elif response.status_code == 200:
                content = response.text.lower()
                
                taken_indicators = [
                    f'"username":"{username.lower()}"',
                    '"id":"',
                    '"edge_owner_to_timeline_media":{',
                    '"biography":',
                    '"profile_pic_url":'
                ]
                
                not_found_indicators = [
                    "sorry, this page isn't available",
                    "the link you followed may be broken",
                    "page not found",
                    '"graphql":{"user":null}',
                    "this page isn't available"
                ]
                
                has_user_data = any(ind in content for ind in taken_indicators)
                has_not_found = any(ind in content for ind in not_found_indicators)
                
                if has_user_data and not has_not_found:
                    return False, "Taken (Profile)"
                elif has_not_found:
                    return True, "Available (not found page)"
                else:
                    if '"user":{"id"' in content or ('"username"' in content and '"full_name"' in content):
                        return False, "Taken (JSON user)"
                    return True, "Available (unclear - small page)"
            else:
                return None, f"HTTP {response.status_code} (Profile)"
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error for {username} in Profile: {e}")
            return None, f"Network error: {str(e)}"
    
    def check_username_via_signup_api(self, username: str) -> Tuple[Optional[bool], str]:
        """
        Check username availability via Instagram signup API
        This is the primary method with highest reliability
        
        Args:
            username: Username to check
            
        Returns:
            Tuple of (availability_status, status_message)
        """
        for attempt in range(3):
            try:
                if self.proxy:
                    self.session.proxies.update(self.proxy)
                
                csrf_resp = self.session.get("https://www.instagram.com/", timeout=10)
                csrf_token = csrf_resp.cookies.get('csrftoken', 'missing')
                
                if self.verbose:
                    self.logger.debug(f"CSRF Token for {username}: {csrf_token}")
                
                if csrf_token == 'missing':
                    self.logger.warning(f"CSRF token missing for {username}, attempt {attempt+1}")
                    if attempt == 2:
                        return None, "CSRF token failed after retries"
                
                url = "https://www.instagram.com/api/v1/users/check_username/"
                headers = {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrf_token,
                    'X-Instagram-AJAX': '1',
                    'Referer': 'https://www.instagram.com/accounts/web_create_ajax/attempt/',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': 'https://www.instagram.com',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin'
                }
                data = {'username': username}
                
                response = self.session.post(url, data=data, headers=headers, timeout=10)
                self.logger.debug(f"API Response for {username} (attempt {attempt+1}): Status {response.status_code}")
                
                if self.verbose and response.status_code == 200:
                    try:
                        result = response.json()
                        print_colored_message(f"📊 API Response for {username}: {json.dumps(result, indent=2)}", "blue")
                    except:
                        pass
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        if result.get('available', False):
                            return True, "Available (API ✅)"
                        elif 'errors' in result and 'username' in result.get('errors', {}):
                            return False, "Taken (API error ❌)"
                        elif 'available' in result and not result['available']:
                            return False, "Taken (API ❌)"
                        else:
                            self.logger.warning(f"Unclear API response for {username}: {result}")
                    except json.JSONDecodeError:
                        self.logger.warning(f"JSON decode failed for {username}: {response.text[:100]}")
                elif response.status_code == 400:
                    return False, "Taken (400 - invalid/unavailable ❌)"
                elif response.status_code in [403, 429]:
                    self.logger.warning(f"API blocked for {username}: {response.status_code}")
                    self.random_delay(3, 6)
                    continue
                else:
                    self.logger.warning(f"Unexpected API status for {username}: {response.status_code}")
                    
            except requests.exceptions.ProxyError as e:
                self.logger.error(f"Proxy error for {username}: {e}")
                self.session.proxies.clear()  
                if attempt < 2:
                    self.random_delay(2, 4)
                else:
                    return None, f"Proxy failed: {str(e)}"
            except requests.exceptions.RequestException as e:
                self.logger.error(f"API error for {username} (attempt {attempt+1}): {e}")
                if attempt < 2:
                    self.random_delay(2, 4)
                else:
                    return None, f"API failed after retries: {str(e)}"
        
        return None, "API exhausted - fallback to Profile"
    
    def check_single_username(self, username: str, use_api: bool = True) -> Dict:
        """
        Check a single username availability
        
        Args:
            username: Username to check
            use_api: Whether to use API method first
            
        Returns:
            Dictionary with check results
        """
        username = username.strip().lower()
        
        if not validate_username(username):
            result = {
                'username': username,
                'available': False,
                'status': 'Invalid format (1-30 chars, alphanumeric + _/. , no leading/trailing special)',
                'method': 'validation',
                'timestamp': datetime.now().isoformat()
            }
            self.errors.append(result)
            print_colored_message(f"❓ {username} - ERROR: Invalid format", "yellow")
            return result
        
        print_colored_message(f"🔍 Checking: {username}", "cyan")
        self.logger.info(f"Checking {username}")
        
        is_available, status = None, ""
        
        if use_api:
            is_available, status = self.check_username_via_signup_api(username)
            if is_available is not None:
                self.random_delay()
        
        if is_available is None:
            is_available, status = self.check_username_via_profile(username)
        
        available = is_available if is_available is not None else False
        
        result = {
            'username': username,
            'available': available,
            'status': status,
            'method': 'API' if use_api and 'API' in status else 'Profile',
            'timestamp': datetime.now().isoformat()
        }
        
        if available:
            self.available_usernames.append(result)
            print_colored_message(f"✅ + {username} - AVAILABLE {status}", "green")
        elif not available and is_available is not None:
            self.unavailable_usernames.append(result)
            print_colored_message(f"❌ - {username} - TAKEN {status}", "red")
        else:
            self.errors.append(result)
            print_colored_message(f"⚠️  ? {username} - ERROR: {status}", "yellow")
        
        return result
    
    def check_usernames_batch(self, usernames: List[str], use_api: bool = True) -> List[Dict]:
        """
        Check multiple usernames in parallel
        
        Args:
            usernames: List of usernames to check
            use_api: Whether to use API method first
            
        Returns:
            List of result dictionaries
        """
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_username = {
                executor.submit(self.check_single_username, username, use_api): username 
                for username in usernames
            }
            
            for future in tqdm(as_completed(future_to_username), total=len(usernames), desc="Progress", colour="blue"):
                try:
                    result = future.result()
                    results.append(result)
                    self.random_delay(0.5, 1.5)
                except Exception as e:
                    username = future_to_username[future]
                    self.logger.error(f"Thread error for {username}: {e}")
                    error_result = {
                        'username': username,
                        'available': False,
                        'status': f'Thread error: {str(e)}',
                        'method': 'error',
                        'timestamp': datetime.now().isoformat()
                    }
                    results.append(error_result)
                    self.errors.append(error_result)
                    print_colored_message(f"⚠️  ? {username} - THREAD ERROR: {str(e)}", "yellow")
        
        return results
    
    def check_usernames_from_file(self, filename: str) -> List[Dict]:
        """
        Load usernames from file and check them
        
        Args:
            filename: Path to file containing usernames (one per line)
            
        Returns:
            List of result dictionaries
        """
        if not os.path.exists(filename):
            print_colored_message(f"Error: File '{filename}' not found.", "red")
            self.logger.error(f"File not found: {filename}")
            return []
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                usernames = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            print_colored_message(f"Loaded {len(usernames)} usernames from {filename}", "cyan")
            self.logger.info(f"Loaded {len(usernames)} usernames from {filename}")
        except Exception as e:
            print_colored_message(f"Error reading file '{filename}': {e}", "red")
            self.logger.error(f"File read error: {e}")
            return []
        
        return self.check_usernames_batch(usernames)
    
    def check_usernames_list(self, usernames: List[str], use_api: bool = True) -> List[Dict]:
        """
        Check a provided list of usernames
        
        Args:
            usernames: List of usernames to check
            use_api: Whether to use API method first
            
        Returns:
            List of result dictionaries
        """
        if not usernames:
            print_colored_message("No usernames provided.", "yellow")
            return []
        
        print_colored_message(f"Checking {len(usernames)} provided usernames...", "cyan")
        return self.check_usernames_batch(usernames, use_api)
    
    def generate_username_variations(self, base: str, count: int = 10) -> List[str]:
        """
        Generate username variations based on a base name
        
        Args:
            base: Base username to generate variations from
            count: Number of variations to generate
            
        Returns:
            List of generated username variations
        """
        if not validate_username(base):
            print_colored_message(f"Base username '{base}' is invalid.", "yellow")
            return []
        
        variations = [base]
        suffixes = ['1', '2', '3', '4', '5', '_', '.', 'official', 'real', 'new', 'pro', 'hq', 'x', 'xx']
        prefixes = ['the', 'real', 'official', 'new', 'x']
        
        for i in range(1, count):
            variation_type = random.choice(['suffix', 'prefix', 'number', 'combo'])
            
            if variation_type == 'suffix':
                suffix = random.choice(suffixes)
                variation = f"{base}{suffix}"
            elif variation_type == 'prefix':
                prefix = random.choice(prefixes)
                variation = f"{prefix}{base}"
            elif variation_type == 'number':
                number = random.randint(1, 999)
                variation = f"{base}{number}"
            else:  
                suffix = random.choice(suffixes)
                number = random.randint(1, 99)
                variation = f"{base}{suffix}{number}"
            
            if validate_username(variation) and variation not in variations:
                variations.append(variation)
        
        print_colored_message(f"Generated {len(variations)} valid variations for base '{base}'", "cyan")
        return variations
    
    def save_results(self, output_dir: str = ".", save_csv: bool = True) -> None:
        """
        Save all results to various file formats
        
        Args:
            output_dir: Directory to save results
            save_csv: Whether to save CSV format
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"instagram_check_{timestamp}"
        
        if self.available_usernames:
            avail_file = os.path.join(output_dir, f"{prefix}_available.txt")
            with open(avail_file, 'w', encoding='utf-8') as f:
                f.write("AVAILABLE USERNAMES\n" + "="*50 + "\n\n")
                for res in self.available_usernames:
                    f.write(f"{res['username']} - {res['status']} ({res['method']})\n")
            print_colored_message(f"✅ Saved {len(self.available_usernames)} available usernames to: {avail_file}", "green")
        
        if self.unavailable_usernames:
            unavail_file = os.path.join(output_dir, f"{prefix}_unavailable.txt")
            with open(unavail_file, 'w', encoding='utf-8') as f:
                f.write("UNAVAILABLE USERNAMES\n" + "="*50 + "\n\n")
                for res in self.unavailable_usernames:
                    f.write(f"{res['username']} - {res['status']} ({res['method']})\n")
            print_colored_message(f"❌ Saved {len(self.unavailable_usernames)} unavailable usernames to: {unavail_file}", "red")
        
        if self.errors:
            error_file = os.path.join(output_dir, f"{prefix}_errors.txt")
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write("ERRORS\n" + "="*50 + "\n\n")
                for res in self.errors:
                    f.write(f"{res['username']} - {res['status']} ({res['method']})\n")
            print_colored_message(f"⚠️  Saved {len(self.errors)} errors to: {error_file}", "yellow")
        
        if save_csv:
            csv_file = os.path.join(output_dir, f"{prefix}_results.csv")
            all_results = self.available_usernames + self.unavailable_usernames + self.errors
            if all_results:
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['username', 'available', 'status', 'method', 'timestamp'])
                    writer.writeheader()
                    writer.writerows(all_results)
                print_colored_message(f"📊 Saved CSV report to: {csv_file}", "cyan")
        
        json_file = os.path.join(output_dir, f"{prefix}_summary.json")
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_checked': len(self.available_usernames) + len(self.unavailable_usernames) + len(self.errors),
            'available_count': len(self.available_usernames),
            'unavailable_count': len(self.unavailable_usernames),
            'error_count': len(self.errors),
            'available_usernames': [r['username'] for r in self.available_usernames],
            'unavailable_usernames': [r['username'] for r in self.unavailable_usernames],
            'error_usernames': [r['username'] for r in self.errors],
            'configuration': {
                'proxy_used': self.proxy is not None,
                'max_workers': self.max_workers,
                'min_delay': self.min_delay,
                'max_delay': self.max_delay,
                'verbose': self.verbose
            }
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print_colored_message(f"📋 Saved JSON summary to: {json_file}", "blue")
        print_colored_message(f"\n🎉 All results saved to directory: {output_dir}", "green")
        
        format_results_summary(
            len(self.available_usernames),
            len(self.unavailable_usernames), 
            len(self.errors)
        )
    
    def clear_results(self):
        """Clear all stored results"""
        self.available_usernames.clear()
        self.unavailable_usernames.clear()
        self.errors.clear()
        print_colored_message("🧹 Results cleared", "yellow")
    
    def get_stats(self) -> Dict:
        """
        Get current statistics
        
        Returns:
            Dictionary with current stats
        """
        total = len(self.available_usernames) + len(self.unavailable_usernames) + len(self.errors)
        return {
            'total_checked': total,
            'available': len(self.available_usernames),
            'unavailable': len(self.unavailable_usernames),
            'errors': len(self.errors),
            'success_rate': ((len(self.available_usernames) + len(self.unavailable_usernames)) / total * 100) if total > 0 else 0
        }


if __name__ == "__main__":
    print_colored_message("🧪 Testing Instagram Username Checker", "cyan")
    
    checker = InstagramUsernameChecker(verbose=True, max_workers=2)
    
    test_usernames = ["test_user_12345", "available_name_test", "sample_username_check"]
    
    print_colored_message(f"\n🔍 Testing with {len(test_usernames)} usernames...", "yellow")
    results = checker.check_usernames_list(test_usernames)
    
    stats = checker.get_stats()
    print_colored_message(f"\n📊 Test Results: {stats}", "blue")
    
    checker.save_results("./test_results")
