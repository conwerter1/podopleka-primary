"""Temporary, fixed-destination CA validation for the owned Fornex migration.
© 2026 Алексей Алексин и Александра Костюченко. Все права защищены.
"""
import http.client
import re
import time

EXPIRES_AT = 1793895893  # 2026-11-05 16:24:53 UTC; no automatic extension.
ORIGIN_IP = '5.187.6.111'
ORIGIN_HOST = 'xn--80ahsdnbed7n.xn--p1ai'
PREFIXES = ('/.well-known/acme-challenge/', '/.well-known/pki-validation/')
VALID_PATH = re.compile(r'/\.well-known/(?:acme-challenge/[A-Za-z0-9_-]{16,128}|pki-validation/[A-Za-z0-9_-]{16,128}\.txt)\Z')

def challenge_response(environ, *, connection_factory=None, now=None):
    path = environ.get('PATH_INFO', '/')
    if not path.startswith(PREFIXES):
        return None
    method = environ.get('REQUEST_METHOD', 'GET')
    headers = [('Content-Type', 'text/plain; charset=utf-8'), ('Cache-Control', 'no-store'),
               ('X-Content-Type-Options', 'nosniff'), ('X-Podopleka-Validation', 'fornex-80-143155')]
    def result(status, body=b''):
        return status, headers + [('Content-Length', str(len(body)))], b'' if method == 'HEAD' else body
    if method not in ('GET', 'HEAD'):
        headers.append(('Allow', 'GET, HEAD'))
        return result(405)
    if (time.time() if now is None else now) >= EXPIRES_AT:
        return result(404)
    if not VALID_PATH.fullmatch(path) or environ.get('QUERY_STRING', ''):
        return result(404)
    factory = connection_factory or http.client.HTTPConnection
    connection = None
    try:
        connection = factory(ORIGIN_IP, 80, timeout=5)
        connection.request('GET', path, headers={'Host': ORIGIN_HOST, 'Accept-Encoding': 'identity',
                                               'User-Agent': 'Podopleka-domain-validation/2026'})
        response = connection.getresponse()
        if response.status != 200:
            return result(404 if response.status == 404 else 502)
        body = response.read(2049)
        if not body or len(body) > 2048 or any(byte not in (9, 10, 13) and not 32 <= byte <= 126 for byte in body):
            return result(502)
        if body.lstrip().lower().startswith((b'<html', b'<!doctype', b'<?php')):
            return result(502)
        return result(200, body)
    except (OSError, http.client.HTTPException):
        return result(503)
    finally:
        if connection is not None:
            connection.close()
