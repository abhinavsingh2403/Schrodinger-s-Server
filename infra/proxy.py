"""
proxy.py: Trusted Proxy Resolution, PROXY Protocol v1 Parsing, and Identity Security.

Pre-registered in SPEC.md Section 5.1, Section 5.3 and Risk R8.
Guarantees:
1. Docker Ingress / TCP Proxy Source-IP Preservation (PROXY Protocol v1).
2. Trusted Proxy Authorization: Only whitelisted proxies may provide client IP.
3. Anti-Spoofing: Untrusted clients attempting to forge PROXY or X-Forwarded-For
   headers have their headers strictly ignored, binding identity to the socket peer.
4. Privacy: Works with derive_visitor_id and get_masked_id to ensure raw IPs are never leaked.
"""

from __future__ import annotations

import ipaddress
import logging
import os
from typing import Any, List, Optional, Tuple, Union

logger = logging.getLogger("infra.proxy")

DEFAULT_TRUSTED_PROXIES = [
    ipaddress.ip_network("127.0.0.1/32"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]


def get_trusted_proxies(env_var: str = "TRUSTED_PROXIES") -> List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]:
    """Loads trusted proxy CIDRs from environment or returns private/loopback defaults."""
    env_val = os.environ.get(env_var, "").strip()
    if not env_val:
        return list(DEFAULT_TRUSTED_PROXIES)

    networks: List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]] = []
    for entry in env_val.split(","):
        clean = entry.strip()
        if not clean:
            continue
        try:
            if "/" not in clean:
                ip = ipaddress.ip_address(clean)
                clean = f"{clean}/32" if ip.version == 4 else f"{clean}/128"
            networks.append(ipaddress.ip_network(clean, strict=False))
        except ValueError:
            logger.warning("Invalid trusted proxy network specification: %r", clean)

    return networks if networks else list(DEFAULT_TRUSTED_PROXIES)


def is_trusted_proxy(
    ip_str: Optional[str],
    trusted_networks: Optional[List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]] = None,
) -> bool:
    """Checks whether an IP address belongs to an authorized trusted proxy."""
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        networks = trusted_networks if trusted_networks is not None else get_trusted_proxies()
        return any(ip in net for net in networks)
    except ValueError:
        return False


def format_proxy_v1(
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
) -> bytes:
    """Formats an HAProxy PROXY protocol v1 header string."""
    try:
        ip = ipaddress.ip_address(src_ip)
        family = "TCP4" if ip.version == 4 else "TCP6"
    except ValueError:
        family = "TCP4"

    return f"PROXY {family} {src_ip} {dst_ip} {int(src_port)} {int(dst_port)}\r\n".encode("ascii")


def parse_proxy_v1(data: bytes) -> Optional[Tuple[str, int, bytes]]:
    """
    Parses a PROXY protocol v1 header from incoming byte stream.
    
    Returns (src_ip, src_port, remainder_bytes) if valid header present.
    Returns None if stream does not begin with valid PROXY header.
    """
    if not (data.startswith(b"PROXY TCP4 ") or data.startswith(b"PROXY TCP6 ") or data.startswith(b"PROXY UNKNOWN")):
        return None

    crlf_pos = data.find(b"\r\n")
    if crlf_pos == -1:
        # Header not yet complete in this buffer
        return None

    line = data[:crlf_pos]
    remainder = data[crlf_pos + 2:]

    try:
        text = line.decode("ascii")
        parts = text.split()
        if len(parts) < 6:
            return None
        proto, family, src_ip, dst_ip, src_port, dst_port = parts[:6]
        if proto != "PROXY":
            return None
        # Validate source IP
        ipaddress.ip_address(src_ip)
        port = int(src_port)
        if not (1 <= port <= 65535):
            return None
        return src_ip, port, remainder
    except (UnicodeDecodeError, ValueError):
        return None


def extract_forwarded_ip(
    remote_ip: str,
    headers: Any,
    trusted_networks: Optional[List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]] = None,
) -> str:
    """
    Safely resolves client IP from X-Forwarded-For HTTP header ONLY if remote_ip is trusted.
    
    Security Guarantee:
    If remote_ip is NOT in trusted networks, any X-Forwarded-For header is strictly ignored,
    and remote_ip is returned directly to prevent client identity spoofing.
    """
    if not is_trusted_proxy(remote_ip, trusted_networks):
        # Untrusted peer: reject all client-supplied forwarding headers
        return remote_ip

    xff = ""
    if hasattr(headers, "get"):
        xff = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for") or ""
    elif isinstance(headers, dict):
        xff = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for") or ""

    if not xff:
        return remote_ip

    # Leftmost valid IP represents original client in standard chain
    for candidate in xff.split(","):
        cand = candidate.strip()
        try:
            ipaddress.ip_address(cand)
            return cand
        except ValueError:
            continue

    return remote_ip
