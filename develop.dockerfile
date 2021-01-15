#The FROM instruction initializes a new build stage and sets the Base Image for subsequent instructions.
FROM python:latest

#The MAINTAINER instruction sets the Author field of the generated images.
MAINTAINER gzlujiantao

#The RUN instruction will execute any commands in a new layer on top of the current image and commit the results.
#RUN <command> (shell form, the command is run in a shell, which by default is /bin/sh -c on Linux or cmd /S /C on Windows)
#RUN ["executable", "param1", "param2"] (exec form)
COPY ./ssosystem/requirements.txt ./
COPY ./basic_sources/sources.list /etc/apt
ADD ./basic_sources/fonts.tar.gz /usr/share/fonts/truetype
RUN ["/bin/bash", "-c", "useradd -u 1000 -m -s /bin/bash dockeruser"]
RUN ["/bin/bash", "-c", "cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/shanghai' > /etc/timezone"]
# RUN ["/bin/bash", "-c", "apt-get update && apt-get install -y vim"]
RUN ["/bin/bash", "-c", "pip install --no-cache-dir -r requirements.txt -i https://mirrors.ustc.edu.cn/pypi/web/simple"]

#The WORKDIR instruction sets the working directory for any RUN, CMD, ENTRYPOINT, COPY and ADD instructions that follow it in the Dockerfile.
WORKDIR /usr/src/app

#The VOLUME instruction creates a mount point with the specified name and marks it as holding externally mounted volumes from native host or other containers.
#The value can be a JSON array, VOLUME ["/var/log/"], or a plain string with multiple arguments, such as VOLUME /var/log or VOLUME /var/log /var/db.
VOLUME /usr/src/app

#The USER instruction sets the user name (or UID) and optionally the user group (or GID) to use when running the image and for any RUN, CMD and ENTRYPOINT instructions that follow it in the Dockerfile.
#USER <user>[:<group>]
#USER <UID>[:<GID>]
USER dockeruser

#The ADD instruction copies new files, directories or remote file URLs from <src> and adds them to the filesystem of the image at the path <dest>.
#ADD [--chown=<user>:<group>] <src>... <dest>
#ADD [--chown=<user>:<group>] ["<src>",... "<dest>"]
#ADD

#The COPY instruction copies new files or directories from <src> and adds them to the filesystem of the container at the path <dest>.
#COPY [--chown=<user>:<group>] <src>... <dest>
#COPY [--chown=<user>:<group>] ["<src>",... "<dest>"]
#COPY requirements.txt ./
#COPY DailyReport.ini ./
#COPY server ./server

#An ENTRYPOINT allows you to configure a container that will run as an executable.
#ENTRYPOINT ["executable", "param1", "param2"]
#ENTRYPOINT command param1 param2
#ENTRYPOINT

#The EXPOSE instruction informs Docker that the container listens on the specified network ports at runtime.
EXPOSE 8000

#The main purpose of a CMD is to provide defaults for an executing container.There can only be one CMD instruction in a Dockerfile. If you list more than one CMD then only the last CMD will take effect.
#CMD ["executable","param1","param2"] (exec form, this is the preferred form)
#CMD ["param1","param2"] (as default parameters to ENTRYPOINT)
#CMD command param1 param2 (shell form)
CMD ["/bin/bash", "-c", "uwsgi --ini SSOSystem.ini 1>serverlog/server.log 2>&1"]
