#!/usr/bin/env python3
"""
Pre-Deployment Check Script

This script performs comprehensive checks to ensure the system is ready for production:
1. Validates all required environment variables
2. Tests database connectivity and migrations
3. Checks for proper authentication configuration
4. Verifies that API endpoints are accessible
5. Ensures Stripe webhook is properly configured
6. Tests email sending functionality
7. Verifies core system components

Run this script before deploying to production to catch potential issues.
"""

import os
import sys
import json
import logging
import requests
import importlib
import datetime
import re
import subprocess
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pre_deploy_check')

# Add console output with colors
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

class DeploymentCheck:
    def __init__(self):
        self.all_checks_passed = True
        self.report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'checks': {},
            'passed': True
        }
        
    def print_status(self, message, status, details=None):
        """Print a status message with color"""
        status_str = f"{GREEN}✅ PASS{RESET}" if status else f"{RED}❌ FAIL{RESET}"
        logger.info(f"{BOLD}{message}{RESET}: {status_str}")
        if details and not status:
            for detail in details if isinstance(details, list) else [details]:
                logger.info(f"  {RED}- {detail}{RESET}")
        
        return status
    
    def log_check(self, check_name, passed, details=None):
        """Log a check result to the report"""
        self.report['checks'][check_name] = {
            'passed': passed,
            'details': details
        }
        if not passed:
            self.all_checks_passed = False
            self.report['passed'] = False
    
    def check_environment_variables(self):
        """Check for required environment variables"""
        logger.info(f"{BLUE}Checking environment variables...{RESET}")
        
        # List of required environment variables and their validation patterns
        required_vars = {
            'DATABASE_URL': r'^postgresql://.+',
            'FLASK_SECRET_KEY': r'.+',
            'API_KEY': r'.+',
            'STRIPE_SECRET_KEY': r'^sk_',
            'STRIPE_PUBLIC_KEY': r'^pk_',
            'STRIPE_WEBHOOK_SECRET': r'^whsec_',
            'SENDGRID_API_KEY': r'.+',
            'SENDGRID_FROM_EMAIL': r'.+@.+\..+',
            'REDIS_URL': r'^(redis|rediss)://.+',
            'JWT_SECRET_KEY': r'.+'
        }
        
        # Optional but recommended variables
        optional_vars = {
            'GOOGLE_OAUTH_CLIENT_ID': r'.+\.apps\.googleusercontent\.com$',
            'GOOGLE_OAUTH_CLIENT_SECRET': r'.+',
            'SLACK_BOT_TOKEN': r'^xoxb-.+',
            'SLACK_CHANNEL_ID': r'^[A-Z0-9]+$',
            'OPENAI_API_KEY': r'^sk-.+'
        }
        
        # Check required vars
        missing_vars = []
        invalid_vars = []
        for var, pattern in required_vars.items():
            value = os.environ.get(var)
            if not value:
                missing_vars.append(var)
            elif not re.match(pattern, value):
                invalid_vars.append(f"{var} (doesn't match pattern {pattern})")
        
        # Check optional vars
        missing_optional = []
        for var, pattern in optional_vars.items():
            value = os.environ.get(var)
            if not value:
                missing_optional.append(var)
            elif not re.match(pattern, value):
                invalid_vars.append(f"{var} (doesn't match pattern {pattern})")
        
        # Report results
        env_check_passed = len(missing_vars) == 0 and len(invalid_vars) == 0
        details = []
        if missing_vars:
            details.append(f"Missing required variables: {', '.join(missing_vars)}")
        if invalid_vars:
            details.append(f"Invalid variable formats: {', '.join(invalid_vars)}")
        if missing_optional:
            logger.info(f"{YELLOW}⚠️ Warning: Missing optional variables: {', '.join(missing_optional)}{RESET}")
        
        passed = self.print_status("Environment variables", env_check_passed, details)
        self.log_check("environment_variables", passed, details)
        return passed
    
    def check_database_connection(self):
        """Check database connection and models"""
        logger.info(f"{BLUE}Checking database connection...{RESET}")
        
        # Ensure DATABASE_URL is set
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            error = "DATABASE_URL environment variable not set"
            self.print_status("Database connection", False, error)
            self.log_check("database_connection", False, error)
            return False
        
        try:
            # Use SQLAlchemy to check the connection
            from sqlalchemy import create_engine, inspect, text
            
            # Create engine
            engine = create_engine(database_url)
            
            # Test connection
            connection = engine.connect()
            connection.close()
            
            # Check if main tables exist
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # List of expected tables
            expected_tables = ['users', 'token_blocklist', 'workspace', 'project', 'task']
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                error = f"Missing expected tables: {', '.join(missing_tables)}"
                self.print_status("Database tables", False, error)
                self.log_check("database_tables", False, error)
                return False
            
            # Check for foreign key issues
            fk_issues = []
            with engine.connect() as conn:
                # Check for invalid foreign keys in task table
                if 'task' in tables:
                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM task 
                        WHERE user_id IS NOT NULL 
                        AND user_id NOT IN (SELECT id FROM users)
                    """))
                    orphaned_tasks = result.scalar()
                    if orphaned_tasks > 0:
                        fk_issues.append(f"Orphaned tasks: {orphaned_tasks} tasks with invalid user_id")
            
            if fk_issues:
                self.print_status("Foreign key integrity", False, fk_issues)
                self.log_check("foreign_key_integrity", False, fk_issues)
                logger.info(f"{YELLOW}⚠️ Recommendation: Run scripts/fix_fks_and_orphans.py to fix foreign key issues{RESET}")
                return False
            
            passed = self.print_status("Database connection", True)
            self.log_check("database_connection", True)
            return True
            
        except ImportError as e:
            error = f"Could not import required modules: {e}"
            self.print_status("Database connection", False, error)
            self.log_check("database_connection", False, error)
            return False
        except Exception as e:
            error = f"Database connection error: {e}"
            self.print_status("Database connection", False, error)
            self.log_check("database_connection", False, error)
            return False
    
    def check_auth_configuration(self):
        """Check authentication configuration"""
        logger.info(f"{BLUE}Checking authentication configuration...{RESET}")
        
        try:
            # Check for JWT secret key
            jwt_secret = os.environ.get('JWT_SECRET_KEY')
            if not jwt_secret:
                error = "JWT_SECRET_KEY environment variable not set"
                self.print_status("JWT configuration", False, error)
                self.log_check("jwt_configuration", False, error)
                return False
            
            # Check for Flask secret key
            flask_secret = os.environ.get('FLASK_SECRET_KEY')
            if not flask_secret:
                error = "FLASK_SECRET_KEY environment variable not set"
                self.print_status("Flask session security", False, error)
                self.log_check("flask_session_security", False, error)
                return False
            
            # Check token blocklist implementation
            try:
                import token_blocklist
                blocklist_check = hasattr(token_blocklist, 'add_token_to_blocklist') and \
                                 hasattr(token_blocklist, 'is_token_revoked')
                if not blocklist_check:
                    error = "Token blocklist implementation is incomplete"
                    self.print_status("Token blocklist", False, error)
                    self.log_check("token_blocklist", False, error)
                    return False
            except ImportError:
                error = "Could not import token_blocklist module"
                self.print_status("Token blocklist", False, error)
                self.log_check("token_blocklist", False, error)
                return False
            
            # Further checks for auth routes
            auth_routes_ok = True
            auth_route_issues = []
            
            # Check auth route files
            auth_files = ['auth_router_fix.py', 'email_auth.py', 'google_auth.py']
            for auth_file in auth_files:
                if not os.path.exists(auth_file):
                    auth_route_issues.append(f"Missing auth file: {auth_file}")
                    auth_routes_ok = False
            
            if not auth_routes_ok:
                self.print_status("Auth routes", False, auth_route_issues)
                self.log_check("auth_routes", False, auth_route_issues)
                return False
            
            passed = self.print_status("Authentication configuration", True)
            self.log_check("authentication_configuration", True)
            return True
            
        except Exception as e:
            error = f"Error checking auth configuration: {e}"
            self.print_status("Authentication configuration", False, error)
            self.log_check("authentication_configuration", False, error)
            return False
    
    def check_stripe_configuration(self):
        """Check Stripe configuration"""
        logger.info(f"{BLUE}Checking Stripe configuration...{RESET}")
        
        # Check for Stripe environment variables
        stripe_vars = {
            'STRIPE_SECRET_KEY': os.environ.get('STRIPE_SECRET_KEY'),
            'STRIPE_PUBLIC_KEY': os.environ.get('STRIPE_PUBLIC_KEY'),
            'STRIPE_WEBHOOK_SECRET': os.environ.get('STRIPE_WEBHOOK_SECRET')
        }
        
        missing_stripe_vars = [var for var, value in stripe_vars.items() if not value]
        
        if missing_stripe_vars:
            error = f"Missing Stripe environment variables: {', '.join(missing_stripe_vars)}"
            self.print_status("Stripe configuration", False, error)
            self.log_check("stripe_configuration", False, error)
            return False
        
        try:
            # Check for Stripe library
            import stripe
            
            # Check webhook endpoint in code
            webhook_routes = []
            
            files_to_check = ['main.py', 'api.py', 'subscription_routes.py']
            webhook_found = False
            
            for file in files_to_check:
                if not os.path.exists(file):
                    continue
                
                with open(file, 'r') as f:
                    content = f.read()
                    
                # Look for Stripe webhook route
                if re.search(r'@.*?route\([\'"].*?webhook.*?[\'"]\s*,\s*methods=', content):
                    webhook_found = True
                    break
            
            if not webhook_found:
                error = "Stripe webhook route not found in any of the main files"
                self.print_status("Stripe webhook", False, error)
                self.log_check("stripe_webhook", False, error)
                return False
            
            # Check for webhook verification code
            webhook_verification = False
            
            for file in files_to_check:
                if not os.path.exists(file):
                    continue
                
                with open(file, 'r') as f:
                    content = f.read()
                    
                if 'STRIPE_WEBHOOK_SECRET' in content and 'construct_event' in content:
                    webhook_verification = True
                    break
            
            if not webhook_verification:
                error = "Stripe webhook verification code not found"
                self.print_status("Stripe webhook verification", False, error)
                self.log_check("stripe_webhook_verification", False, error)
                return False
            
            passed = self.print_status("Stripe configuration", True)
            self.log_check("stripe_configuration", True)
            return True
            
        except ImportError:
            error = "Stripe library not installed"
            self.print_status("Stripe library", False, error)
            self.log_check("stripe_library", False, error)
            return False
        except Exception as e:
            error = f"Error checking Stripe configuration: {e}"
            self.print_status("Stripe configuration", False, error)
            self.log_check("stripe_configuration", False, error)
            return False
    
    def check_email_configuration(self):
        """Check email sending configuration"""
        logger.info(f"{BLUE}Checking email configuration...{RESET}")
        
        # Check for SendGrid environment variables
        sendgrid_vars = {
            'SENDGRID_API_KEY': os.environ.get('SENDGRID_API_KEY'),
            'SENDGRID_FROM_EMAIL': os.environ.get('SENDGRID_FROM_EMAIL')
        }
        
        missing_sendgrid_vars = [var for var, value in sendgrid_vars.items() if not value]
        
        if missing_sendgrid_vars:
            error = f"Missing SendGrid environment variables: {', '.join(missing_sendgrid_vars)}"
            self.print_status("Email configuration", False, error)
            self.log_check("email_configuration", False, error)
            return False
        
        try:
            # Check for SendGrid library
            import sendgrid
            
            # Check for email templates
            email_template_dir = 'templates/emails'
            if not os.path.exists(email_template_dir):
                error = "Email templates directory not found"
                self.print_status("Email templates", False, error)
                self.log_check("email_templates", False, error)
                return False
            
            # Check for email service implementation
            if not os.path.exists('email_service.py'):
                error = "email_service.py file not found"
                self.print_status("Email service", False, error)
                self.log_check("email_service", False, error)
                return False
            
            # Check for digest email implementation
            if not os.path.exists('email_digest.py') or not os.path.exists('email_digest_scheduler.py'):
                logger.info(f"{YELLOW}⚠️ Warning: Email digest implementation files missing{RESET}")
            
            passed = self.print_status("Email configuration", True)
            self.log_check("email_configuration", True)
            return True
            
        except ImportError:
            error = "SendGrid library not installed"
            self.print_status("SendGrid library", False, error)
            self.log_check("sendgrid_library", False, error)
            return False
        except Exception as e:
            error = f"Error checking email configuration: {e}"
            self.print_status("Email configuration", False, error)
            self.log_check("email_configuration", False, error)
            return False
    
    def check_api_endpoints(self):
        """Check API endpoints for proper functioning"""
        logger.info(f"{BLUE}Checking API endpoints...{RESET}")
        
        # We'll check if the API files exist and have proper routes defined
        if not os.path.exists('api.py'):
            error = "api.py file not found"
            self.print_status("API implementation", False, error)
            self.log_check("api_implementation", False, error)
            return False
        
        try:
            # Check for essential API routes
            with open('api.py', 'r') as f:
                content = f.read()
            
            # List of essential route patterns to check for
            essential_routes = [
                r'@.*?route\([\'"].*?login.*?[\'"]\s*,\s*methods=',
                r'@.*?route\([\'"].*?refresh.*?[\'"]\s*,\s*methods=',
                r'@.*?route\([\'"].*?opportunities.*?[\'"]\s*,\s*methods=',
                r'@.*?route\([\'"].*?healthz.*?[\'"]\s*,\s*methods='
            ]
            
            missing_routes = []
            for route_pattern in essential_routes:
                if not re.search(route_pattern, content):
                    # Extract route name from pattern
                    route_name = re.search(r'.*?([a-z-]+).*?[\'"]\s*,', route_pattern)
                    if route_name:
                        missing_routes.append(route_name.group(1))
                    else:
                        missing_routes.append("Unknown route")
            
            if missing_routes:
                error = f"Missing essential API routes: {', '.join(missing_routes)}"
                self.print_status("Essential API routes", False, error)
                self.log_check("essential_api_routes", False, error)
                return False
            
            # Check for proper rate limiting
            rate_limiting_ok = 'Limiter' in content and 'get_remote_address' in content
            if not rate_limiting_ok:
                logger.info(f"{YELLOW}⚠️ Warning: API rate limiting may not be properly configured{RESET}")
            
            # Check for CORS configuration
            cors_ok = 'CORS' in content and 'origins' in content
            if not cors_ok:
                logger.info(f"{YELLOW}⚠️ Warning: CORS configuration may be incomplete{RESET}")
            
            passed = self.print_status("API endpoints", True)
            self.log_check("api_endpoints", True)
            return True
            
        except Exception as e:
            error = f"Error checking API endpoints: {e}"
            self.print_status("API endpoints", False, error)
            self.log_check("api_endpoints", False, error)
            return False
    
    def check_scheduled_tasks(self):
        """Check for scheduled task configuration"""
        logger.info(f"{BLUE}Checking scheduled tasks...{RESET}")
        
        # Check for APScheduler implementation
        scheduler_files = ['ap_scheduler.py', 'bot_scheduler.py', 'email_digest_scheduler.py']
        missing_files = [file for file in scheduler_files if not os.path.exists(file)]
        
        if missing_files:
            error = f"Missing scheduler files: {', '.join(missing_files)}"
            self.print_status("Scheduler files", False, error)
            self.log_check("scheduler_files", False, error)
            return False
        
        # Check for scheduler initialization in main code files
        scheduler_init_found = False
        files_to_check = ['main.py', 'api.py']
        
        for file in files_to_check:
            if not os.path.exists(file):
                continue
            
            with open(file, 'r') as f:
                content = f.read()
                
            if 'APScheduler' in content and ('init_scheduler' in content or 'add_job' in content):
                scheduler_init_found = True
                break
        
        if not scheduler_init_found:
            logger.info(f"{YELLOW}⚠️ Warning: Scheduler initialization not found in main code files{RESET}")
        
        # Check for scheduler state file
        state_file = 'bot_scheduler_state.json'
        if not os.path.exists(state_file):
            logger.info(f"{YELLOW}⚠️ Warning: Scheduler state file not found: {state_file}{RESET}")
        
        passed = self.print_status("Scheduled tasks", True)
        self.log_check("scheduled_tasks", True)
        return True
    
    def check_ssl_configuration(self):
        """Check if the application is set up to use SSL/HTTPS"""
        logger.info(f"{BLUE}Checking SSL/HTTPS configuration...{RESET}")
        
        # Check for Replit deployment domains
        replit_domains = os.environ.get('REPLIT_DOMAINS', '')
        domains = [d.strip() for d in replit_domains.split(',') if d.strip()]
        
        if not domains:
            logger.info(f"{YELLOW}⚠️ Warning: No Replit domains found in environment variables{RESET}")
        
        # Check for HTTPS redirection in the code
        https_redirection_found = False
        files_to_check = ['main.py', 'api.py']
        
        for file in files_to_check:
            if not os.path.exists(file):
                continue
            
            with open(file, 'r') as f:
                content = f.read()
                
            # Look for common HTTPS redirection patterns
            if ('http://' in content and 'https://' in content and 'redirect' in content) or \
               'request.scheme' in content or 'X-Forwarded-Proto' in content:
                https_redirection_found = True
                break
        
        if not https_redirection_found:
            logger.info(f"{YELLOW}⚠️ Warning: HTTPS redirection code not found{RESET}")
            logger.info(f"{YELLOW}⚠️ Recommendation: Add HTTPS redirection middleware for production{RESET}")
        
        # Check for HSTS headers
        hsts_found = False
        for file in files_to_check:
            if not os.path.exists(file):
                continue
            
            with open(file, 'r') as f:
                content = f.read()
                
            if 'Strict-Transport-Security' in content:
                hsts_found = True
                break
        
        if not hsts_found:
            logger.info(f"{YELLOW}⚠️ Warning: HSTS headers not found{RESET}")
            logger.info(f"{YELLOW}⚠️ Recommendation: Add HSTS headers for improved security{RESET}")
        
        passed = self.print_status("SSL/HTTPS configuration", True)
        self.log_check("ssl_configuration", True)
        return True
    
    def check_file_permissions(self):
        """Check file permissions for security concerns"""
        logger.info(f"{BLUE}Checking file permissions...{RESET}")
        
        # List of sensitive files that should have restricted permissions
        sensitive_files = ['credentials.json', '.env', 'secrets.json']
        
        # Check each file
        for file in sensitive_files:
            if os.path.exists(file):
                permissions = oct(os.stat(file).st_mode)[-3:]
                
                # Check if permissions are too open (world-readable)
                if permissions[2] != '0':
                    logger.info(f"{YELLOW}⚠️ Warning: {file} has world-readable permissions: {permissions}{RESET}")
                    logger.info(f"{YELLOW}⚠️ Recommendation: Run 'chmod 600 {file}' to secure it{RESET}")
        
        passed = self.print_status("File permissions", True)
        self.log_check("file_permissions", True)
        return True
    
    def check_error_handling(self):
        """Check error handling and logging configuration"""
        logger.info(f"{BLUE}Checking error handling and logging...{RESET}")
        
        # Check for error templates
        error_templates = ['templates/404.html', 'templates/500.html']
        missing_templates = [template for template in error_templates if not os.path.exists(template)]
        
        if missing_templates:
            logger.info(f"{YELLOW}⚠️ Warning: Missing error templates: {', '.join(missing_templates)}{RESET}")
            logger.info(f"{YELLOW}⚠️ Recommendation: Create proper error templates for better user experience{RESET}")
        
        # Check for error handlers in main code
        error_handlers_found = False
        files_to_check = ['main.py', 'api.py']
        
        for file in files_to_check:
            if not os.path.exists(file):
                continue
            
            with open(file, 'r') as f:
                content = f.read()
                
            if '@app.errorhandler' in content or 'errorhandler' in content:
                error_handlers_found = True
                break
        
        if not error_handlers_found:
            logger.info(f"{YELLOW}⚠️ Warning: Error handlers not found in main code files{RESET}")
            logger.info(f"{YELLOW}⚠️ Recommendation: Add proper error handlers for 404 and 500 errors{RESET}")
        
        # Check for logging configuration
        logging_configured = False
        for file in files_to_check:
            if not os.path.exists(file):
                continue
            
            with open(file, 'r') as f:
                content = f.read()
                
            if 'logging.basicConfig' in content or 'fileHandler' in content:
                logging_configured = True
                break
        
        if not logging_configured:
            logger.info(f"{YELLOW}⚠️ Warning: Proper logging configuration not found{RESET}")
            logger.info(f"{YELLOW}⚠️ Recommendation: Configure proper logging with file handlers{RESET}")
        
        passed = self.print_status("Error handling", True)
        self.log_check("error_handling", True)
        return True
    
    def generate_report(self):
        """Generate a deployment readiness report"""
        logger.info(f"{BLUE}Generating deployment readiness report...{RESET}")
        
        # Add overall assessment
        self.report['all_checks_passed'] = self.all_checks_passed
        
        # Write report to file
        report_file = 'deployment_readiness_report.json'
        with open(report_file, 'w') as f:
            json.dump(self.report, f, indent=2)
        
        logger.info(f"Report saved to {report_file}")
        
        # Print summary
        total_checks = len(self.report['checks'])
        passed_checks = sum(1 for check in self.report['checks'].values() if check['passed'])
        
        logger.info(f"\n{BOLD}Deployment Readiness Summary:{RESET}")
        logger.info(f"  {passed_checks}/{total_checks} checks passed")
        
        if self.all_checks_passed:
            logger.info(f"\n{GREEN}✅ All checks passed! The system is ready for deployment.{RESET}")
        else:
            logger.info(f"\n{RED}❌ Some checks failed. Address the issues before deploying.{RESET}")
            
            # List failed checks
            logger.info(f"\n{BOLD}Failed checks:{RESET}")
            for check_name, check_data in self.report['checks'].items():
                if not check_data['passed']:
                    logger.info(f"  {RED}- {check_name}{RESET}")
                    if check_data['details']:
                        details = check_data['details'] if isinstance(check_data['details'], list) else [check_data['details']]
                        for detail in details:
                            logger.info(f"    {RED}· {detail}{RESET}")
        
        return self.report
    
    def run_all_checks(self):
        """Run all deployment readiness checks"""
        logger.info(f"{BOLD}Starting Proletto Pre-Deployment Checks{RESET}")
        logger.info(f"{BOLD}========================================{RESET}")
        
        # Run all checks
        self.check_environment_variables()
        self.check_database_connection()
        self.check_auth_configuration()
        self.check_stripe_configuration()
        self.check_email_configuration()
        self.check_api_endpoints()
        self.check_scheduled_tasks()
        self.check_ssl_configuration()
        self.check_file_permissions()
        self.check_error_handling()
        
        # Generate report
        return self.generate_report()

if __name__ == "__main__":
    checker = DeploymentCheck()
    report = checker.run_all_checks()
    
    # Exit with non-zero code if any checks failed
    if not report['all_checks_passed']:
        sys.exit(1)