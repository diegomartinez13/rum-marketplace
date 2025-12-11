"""
Request Timing Middleware
Logs the time taken for each HTTP request to the console.
"""

import time
from django.utils.deprecation import MiddlewareMixin


class RequestTimingMiddleware(MiddlewareMixin):
    """
    Middleware that logs request timing information to the console.
    
    Output format:
    [HH:MM:SS] METHOD /path/ - XXX.XXms - STATUS
    """
    
    def process_request(self, request):
        """Store the start time when request begins."""
        request._start_time = time.time()
    
    def process_response(self, request, response):
        """Calculate and log the request duration."""
        if hasattr(request, '_start_time'):
            duration_ms = (time.time() - request._start_time) * 1000
            
            # Get current time for the log
            current_time = time.strftime('%H:%M:%S')
            
            # Get request details
            method = request.method
            path = request.path
            status = response.status_code
            
            # Color coding for terminal (ANSI codes)
            # Green for success, Yellow for redirect, Red for errors
            if 200 <= status < 300:
                status_color = '\033[92m'  # Green
            elif 300 <= status < 400:
                status_color = '\033[93m'  # Yellow
            else:
                status_color = '\033[91m'  # Red
            
            reset_color = '\033[0m'
            method_color = '\033[94m'  # Blue for method
            time_color = '\033[96m'    # Cyan for time
            
            # Format duration
            if duration_ms < 100:
                duration_str = f'{duration_ms:6.2f}ms'
            else:
                duration_str = f'{duration_ms:6.1f}ms'
            
            # Log the request (filter to show only relevant requests)
            # Skip static files and admin requests for cleaner output
            if not path.startswith('/static/') and not path.startswith('/admin/'):
                print(
                    f'[{current_time}] '
                    f'{method_color}{method:4s}{reset_color} '
                    f'{path:40s} '
                    f'{time_color}{duration_str}{reset_color} '
                    f'{status_color}{status}{reset_color}'
                )
        
        return response


class MessagingTimingMiddleware(MiddlewareMixin):
    """
    Middleware that ONLY logs messaging-related requests.
    Use this for focused message speed analysis.
    
    Output format:
    [HH:MM:SS] METHOD /path/ - XXX.XXms - STATUS | Details
    """
    
    def process_request(self, request):
        """Store the start time when request begins."""
        request._start_time = time.time()
    
    def process_response(self, request, response):
        """Calculate and log the request duration for messaging endpoints."""
        if hasattr(request, '_start_time'):
            path = request.path
            
            # Only log messaging-related requests
            if '/messages/' in path or '/conversation/' in path:
                duration_ms = (time.time() - request._start_time) * 1000
                
                current_time = time.strftime('%H:%M:%S')
                method = request.method
                status = response.status_code
                
                # Color coding
                if 200 <= status < 300:
                    status_color = '\033[92m'  # Green
                elif 300 <= status < 400:
                    status_color = '\033[93m'  # Yellow
                else:
                    status_color = '\033[91m'  # Red
                
                reset_color = '\033[0m'
                method_color = '\033[94m'  # Blue
                time_color = '\033[96m'    # Cyan
                
                # Determine request type for clearer output
                if method == 'POST':
                    action = '📤 SEND'
                elif 'poll' in path or 'fetch' in path:
                    action = '📥 POLL'
                else:
                    action = '📄 LOAD'
                
                # Format duration with color based on speed
                if duration_ms < 50:
                    speed_indicator = '\033[92m⚡'  # Green lightning - fast
                elif duration_ms < 200:
                    speed_indicator = '\033[93m●'   # Yellow dot - okay
                else:
                    speed_indicator = '\033[91m●'   # Red dot - slow
                
                print(
                    f'[{current_time}] '
                    f'{method_color}{method:4s}{reset_color} '
                    f'{path:45s} '
                    f'{time_color}{duration_ms:7.2f}ms{reset_color} '
                    f'{status_color}{status}{reset_color} '
                    f'{speed_indicator}{reset_color} {action}'
                )
        
        return response

