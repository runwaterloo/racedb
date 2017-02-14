#!/bin/bash
if [ "$#" -ne 1 ]; then
        echo "Usage: ./debug.sh on|off"
        exit 1
        fi

if [ $1 == 'on' ]
    then
        sed -i s/"DEBUG = False"/"DEBUG = True"/g racedb/settings.py
elif [ $1 == 'off' ]
    then
        sed -i s/"DEBUG = True"/"DEBUG = False"/g racedb/settings.py
else
    echo "Usage: ./debug.sh on|off"
    exit 1
fi
