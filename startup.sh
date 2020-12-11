#!/bin/bash
nohup pipenv run uwsgi --ini SSOSystem.ini 1>serverlog/server.log 2>&1 &
