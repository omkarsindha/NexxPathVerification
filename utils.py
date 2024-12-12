def is_valid_port(port):
    """ Simple port validation. Returns bool """
    return 1 <= port <= 65535

def is_valid_ip(ip_str):
    """Simple IPv4 address validation that excludes loopback addresses. Returns bool"""
    parts = ip_str.split('.')
    # Check for standard IPv4 format and range, then exclude loopback range
    if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) < 256 for part in parts):
        # Exclude loopback address range (127.x.x.x)
        if parts[0] == "127":
            return False
        return True
    return False