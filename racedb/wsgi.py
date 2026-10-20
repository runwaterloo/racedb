"""
WSGI config for racedb project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import site
import sys

site.addsitedir("/usr/local/venv/racedb/lib/python3.6/site-packages")
sys.path.append("/srv/racedb")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
