 #!/bin/bash
su - racedb -c '/usr/local/venv/racedb/bin/python /srv/racedb/manage.py collectstatic --noinput'
systemctl restart httpd
