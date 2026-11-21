"""Small runtime boundary for explicit listener and HTTPS proxy configuration."""
import ipaddress
from urllib.parse import urlsplit


def https_origin(value):
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.path not in ('', '/') or parsed.query
                or parsed.fragment or any(c.isspace() for c in value)):
            raise ValueError
        parsed.port  # Reject malformed/out-of-range ports.
        return value.rstrip('/')
    except (ValueError, TypeError):
        raise ValueError('CHATIDY_PUBLIC_ORIGIN benötigt eine gültige HTTPS-Origin.') from None


def trusted_proxies(environment):
    raw = environment.get('CHATIDY_TRUSTED_PROXIES', '')
    if not raw:
        return ()
    try:
        networks = tuple(ipaddress.ip_network(value.strip(), strict=True) for value in raw.split(','))
        if any(network.prefixlen == 0 for network in networks):
            raise ValueError
        return networks
    except ValueError:
        raise ValueError('CHATIDY_TRUSTED_PROXIES benötigt explizite IPs oder CIDR-Netze, kein /0.') from None


def listener(environment):
    mode = environment.get('CHATIDY_AUTH_REQUIRED', '0')
    if mode not in ('0', '1'):
        raise ValueError('CHATIDY_AUTH_REQUIRED darf nur 0 oder 1 sein.')
    host = environment.get('CHATIDY_HOST', '127.0.0.1')
    if host not in ('127.0.0.1', '0.0.0.0'):
        raise ValueError('CHATIDY_HOST darf nur 127.0.0.1 oder 0.0.0.0 sein.')
    proxies = trusted_proxies(environment)
    origin = environment.get('CHATIDY_PUBLIC_ORIGIN', '')
    if mode == '0' and (origin or proxies or host != '127.0.0.1'):
        raise ValueError('Ohne Anmeldung sind nur lokaler Loopback und keine Proxy-Einstellungen erlaubt.')
    if mode == '1':
        https_origin(origin)
    if host == '0.0.0.0' and not proxies:
        raise ValueError('Container-Listener benötigt explizite vertrauenswürdige Proxys.')
    try:
        port = int(environment.get('CHATIDY_PORT', '8877'))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise ValueError('CHATIDY_PORT muss zwischen 1 und 65535 liegen.') from None
    return host, port


def proxy_request_allowed(headers, peer, environment):
    """Never derive identity, host or origin from client-supplied forwarding data.

    When configured, every application request must come from the allowlisted
    immediate proxy with exactly one HTTPS proto/host header. XFF is ignored.
    """
    try:
        proxies = trusted_proxies(environment)
        forwarded = [name.lower() for name in headers
                     if name.lower() == 'forwarded' or name.lower().startswith('x-forwarded-')]
        if not proxies:
            return not forwarded
        if not any(ipaddress.ip_address(peer) in network for network in proxies):
            return False
        if any(name not in ('x-forwarded-proto', 'x-forwarded-host', 'x-forwarded-for')
               for name in forwarded):
            return False
        for name in ('X-Forwarded-Proto', 'X-Forwarded-Host', 'X-Forwarded-For'):
            if len(headers.get_all(name, [])) > 1:
                return False
        origin = urlsplit(https_origin(environment.get('CHATIDY_PUBLIC_ORIGIN', '')))
        return (headers.get('X-Forwarded-Proto') == 'https'
                and headers.get('X-Forwarded-Host') == origin.netloc)
    except (ValueError, TypeError):
        return False
