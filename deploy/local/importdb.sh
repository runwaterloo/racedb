# Usage ./importdb.sh <path_to_sql_dump>
cat $1 | docker exec -i mariadb sh -c 'mariadb -u racedb -pCHANGEME racedb'
