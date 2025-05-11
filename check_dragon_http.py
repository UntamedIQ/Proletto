#!/usr/bin/env python3
"""
Dragon HTTP Server Check

This script checks if an HTTP server is running on port 5002 and tries to
directly connect to it using a low-level socket connection to diagnose
networking issues.
"""

import socket
import time
import sys
import os

def is_port_in_use(port):
    """Check if a port is in use by attempting to bind to it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except OSError:
            return True

def test_http_connection(host, port):
    """Test a direct HTTP connection to the specified host and port."""
    try:
        start_time = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((host, port))
        connection_time = time.time() - start_time
        
        # Try to send a minimal HTTP request
        s.send(b"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n")
        
        # Try to receive a response
        response_start = time.time()
        data = s.recv(4096)
        response_time = time.time() - response_start
        
        s.close()
        
        print(f"✅ Successfully connected to {host}:{port}")
        print(f"  Connection time: {connection_time * 1000:.2f}ms")
        print(f"  Response time: {response_time * 1000:.2f}ms")
        print(f"  Response length: {len(data)} bytes")
        print(f"  Response preview: {data[:100].decode('utf-8', errors='ignore')}")
        
        return True
    except socket.timeout:
        print(f"❌ Timeout connecting to {host}:{port}")
        return False
    except ConnectionRefusedError:
        print(f"❌ Connection refused on {host}:{port}")
        return False
    except Exception as e:
        print(f"❌ Error connecting to {host}:{port}: {e}")
        return False

def check_process_listening_on_port(port):
    """Check what process is listening on the specified port."""
    try:
        # Try using lsof
        print(f"Checking processes listening on port {port}...")
        os.system(f"lsof -i :{port}")
        print("-" * 40)
        
        # Try using netstat
        os.system(f"netstat -tlnp 2>/dev/null | grep :{port}")
        print("-" * 40)
        
        # Try ss
        os.system(f"ss -tlnp | grep :{port}")
    except Exception as e:
        print(f"Error checking port processes: {e}")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5002
    
    if is_port_in_use(port):
        print(f"✅ Port {port} is in use")
        test_http_connection('localhost', port)
        check_process_listening_on_port(port)
    else:
        print(f"❌ Port {port} is not in use")
        print("This suggests no server is listening on this port.")
        print("Check if the Dragon server has started correctly.")