"""Temporary public reader preserving the original query-string URLs.
© 2026 Алексей Алексин и Александра Костюченко. Все права защищены.
"""
from pathlib import Path
from urllib.parse import parse_qs, unquote
import hashlib
import json
import mimetypes
import os

BASE = Path(__file__).resolve().parent
INDEX = json.loads((BASE / 'content-index.json').read_text(encoding='utf-8'))
PUBLIC = BASE / 'public'
CONTENT = {}
for entry in INDEX['files']:
    path = entry['path']
    assert not path.startswith('/') and '..' not in Path(path).parts
    body = (PUBLIC / path).read_bytes()
    assert len(body) == entry['bytes'] and hashlib.sha256(body).hexdigest() == entry['sha256'], path
    CONTENT[path] = (body, entry['sha256'])
PAGES = INDEX['pages']
PRIVATE = {'login', 'register', 'account', 'editor', 'recover', 'logout', 'admin', 'payment', 'checkout'}
NOTICE = ('<!doctype html><html lang="ru"><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          '<title>Сервис временно недоступен — Подоплёка</title>'
          '<h1>Этот сервис временно недоступен</h1>'
          '<p>Сейчас доступны статьи и приложения для чтения. Работа с учётной записью временно приостановлена.</p>'
          '<p><a href="/">Открыть энциклопедию</a></p>'
          '<p>© 2026 Алексей Алексин и Александра Костюченко. Все права защищены.</p></html>').encode()

def resolve(path, query):
    if len(query) > 4096 or '\\' in path or '\x00' in path:
        return None, 400
    try:
        params = parse_qs(query, keep_blank_values=True, max_num_fields=32, strict_parsing=False)
        path = unquote(path, errors='strict')
    except (ValueError, UnicodeDecodeError):
        return None, 400
    if '\\' in path or '\x00' in path or '..' in path.split('/'):
        return None, 400
    if path in ('/', '/index.php', '/index.php/'):
        page_values = params.get('page', ['home'])
        if len(page_values) != 1:
            return None, 400
        page = page_values[0]
        if page in PRIVATE:
            return None, 503
        if page in PAGES:
            return PAGES[page], 200
        fields = {'article': ['id'], 'section': ['section'], 'download': ['id'],
                  'word-template': ['id'], 'figure': ['id', 'name']}.get(page)
        if not fields:
            return None, 404
        values = []
        for field in fields:
            value = params.get(field, [])
            if len(value) != 1:
                return None, 400
            values.append(value[0])
        target = INDEX['routes'].get(page, {}).get('|'.join(values))
        return (target, 200) if target else (None, 404)
    if path == '/healthz':
        return '__health__', 200
    target = INDEX['legacy_asset_aliases'].get(path, path.lstrip('/'))
    return (target, 200) if target in CONTENT else (None, 404)

def app(environ, start_response):
    method = environ.get('REQUEST_METHOD', 'GET')
    path, status = resolve(environ.get('PATH_INFO', '/'), environ.get('QUERY_STRING', ''))
    if method not in ('GET', 'HEAD'):
        path, status = None, 405
    headers = [('X-Content-Type-Options', 'nosniff'), ('Referrer-Policy', 'strict-origin-when-cross-origin'),
               ('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")]
    if path == '__health__':
        body = json.dumps({'status': 'ok', 'articles': 78, 'public_files': len(CONTENT)}).encode()
        kind = 'application/json; charset=utf-8'
        headers.append(('Cache-Control', 'no-store'))
    elif status != 200:
        if status == 503:
            body = NOTICE
            headers.append(('Retry-After', '3600'))
        else:
            body = CONTENT['404.html'][0]
        kind = 'text/html; charset=utf-8'
        headers.append(('Cache-Control', 'no-store'))
        if status == 405:
            headers.append(('Allow', 'GET, HEAD'))
    else:
        body, digest = CONTENT[path]
        kind = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        if path.endswith('.webmanifest'):
            kind = 'application/manifest+json'
        if kind.startswith('text/') or kind in ('application/json', 'image/svg+xml', 'application/manifest+json'):
            kind += '; charset=utf-8'
        etag = '"' + digest + '"'
        headers.extend([('ETag', etag), ('Cache-Control', 'public, max-age=60' if path.endswith('.html') else 'public, max-age=3600')])
        if environ.get('HTTP_IF_NONE_MATCH') == etag:
            start_response('304 Not Modified', headers)
            return [b'']
        if path.startswith('downloads/'):
            headers.append(('Content-Disposition', 'attachment; filename="' + Path(path).name + '"'))
    headers.extend([('Content-Type', kind), ('Content-Length', str(len(body)))])
    reason = {200: 'OK', 400: 'Bad Request', 404: 'Not Found', 405: 'Method Not Allowed', 503: 'Service Unavailable'}[status]
    start_response(str(status) + ' ' + reason, headers)
    return [b'' if method == 'HEAD' else body]

if __name__ == '__main__':
    from wsgiref.simple_server import make_server, WSGIRequestHandler
    class Quiet(WSGIRequestHandler):
        def log_message(self, *args):
            pass
    # Local inspection only. Render production uses Gunicorn, not this server.
    with make_server('127.0.0.1', int(os.environ.get('PORT', '18086')), app, handler_class=Quiet) as httpd:
        print('Local public-reader preview ready', flush=True)
        httpd.serve_forever()
