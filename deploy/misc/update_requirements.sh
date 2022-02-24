#!/bin/bash
python3 -m pip install --upgrade yolk3k
echo "Updating requirements.txt... (takes time)"
cat requirements.txt \
 | awk -F"=" '{print $1}' \
 | while read P; \
 do yolk -V $P \
 | awk '{print $1"=="$2}' >> reqtmp; \
 done
 mv reqtmp requirements.txt
