# Подоплёка — временная площадка для чтения

© 2026 Алексей Алексин и Александра Костюченко. Все права защищены.

Публичная редакция энциклопедии от31.10.2026:78 статей,24 SVG,35 скачиваний(29 DOCX). Старые query-string адреса обслуживаются с HTTP200 без JavaScript-переадресации. Учётные записи, редактор, почта и базы данных не перенесены.

Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60 --graceful-timeout 25`. Health: `/healthz`. Build: `pip install --require-hashes -r requirements.txt`.

Free Render может засыпать после простоя; это временное восстановление чтения, не SLA.
