#!/bin/bash
echo "WARNING: This will replace the test database with data from production!"
read -p "Are you sure (y/n)? " -r
echo    # (optional) move to a new line
if [[ $REPLY = "y" ]]
then
    export PASSWORD=`cat /srv/racedb_secrets/MYSQL_ROOT_PASSWORD_FILE`
    ssh roanne.scrw.ca "docker exec \`docker ps | grep racedb_db | awk '{print \$1}'\` /usr/bin/mysqldump -u root --password=\`cat /srv/racedb_secrets/MYSQL_ROOT_PASSWORD_FILE\` racedb" > /srv/racedb_secrets/restore.sql
    docker exec `docker ps | grep racedb_db | awk '{print $1}'` /bin/bash -c "cat /run/secrets/restore.sql | /usr/bin/mysql -u root --password=$PASSWORD racedb"
    rm -f /srv/racedb_secrets/restore.sql
fi
