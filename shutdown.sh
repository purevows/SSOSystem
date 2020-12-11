#!/bin/bash
nohup pipenv run uwsgi --stop serverlog/uwsgi.pid 1>serverlog/server.log 2>&1 &
