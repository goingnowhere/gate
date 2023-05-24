
# podman build ./.devcontainer --tag dev --build-arg GID=$(id -g) --build-arg UID=$(id -u) --build-arg USER=$(id -un)
# podman run -it --rm --name dev --mount src=/home/freddie,target=/home/freddie,type=bind --hostuser freddie --user freddie --userns=keep-id dev bash

FROM docker.io/ubuntu:23.04


RUN apt-get update && \
    apt-get install -y \
        sudo curl wget git apt-transport-https ca-certificates gnupg software-properties-common build-essential \
    && \
    apt-get clean autoclean && \
    rm -rf /var/lib/{apt,dpkg,cache,log}

RUN apt-get update && \
    apt-get install -y \
        python3 python3-pip virtualenv python3-setuptools \
    && \
    apt-get clean autoclean && \
    rm -rf /var/lib/{apt,dpkg,cache,log}

RUN curl -sS https://starship.rs/install.sh | sh


RUN wget -q "https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb" && \
    dpkg -i packages-microsoft-prod.deb && \
    rm packages-microsoft-prod.deb && \
    apt-get update && \
    apt-get install -y \
        powershell zsh \
    && \
    apt-get clean autoclean && \
    rm -rf /var/lib/{apt,dpkg,cache,log} && \



RUN apt-get update && \
    apt-get install -y \
        podman podman-docker podman-compose && \
    apt-get clean autoclean && \
    rm -rf /var/lib/{apt,dpkg,cache,log}


RUN apt-get update && \
    apt-get install -y \
        nodejs npm
    && \
    apt-get clean autoclean && \
    rm -rf /var/lib/{apt,dpkg,cache,log}


ARG NPM_GLOBAL=/usr/local/share/npm-global
ENV PATH=${NPM_GLOBAL}/bin:${PATH}
RUN if ! cat /etc/group | grep -e "^npm:" > /dev/null 2>&1; then groupadd -r npm; fi && \
    umask 0002 && \
    mkdir -p ${NPM_GLOBAL} && \
    touch /usr/local/etc/npmrc && \
    chown root:npm ${NPM_GLOBAL} /usr/local/etc/npmrc && \
    chmod g+s ${NPM_GLOBAL} && \
    npm config -g set prefix ${NPM_GLOBAL} && \
    npm install -g \
        eslint tslint-to-eslint-config typescript yarn webpack babel-cli && \
    yarn set version stable && \
    npm cache clean --force > /dev/null 2>&1



ARG GID
ARG UID
ARG USER
ARG SHELL=/bin/bash

RUN userdel -r ubuntu

RUN groupadd -g ${GID} ${USER} && \
    useradd --system --no-create-home -g $GID -u $UID -s ${SHELL} ${USER} && \
    groupmod -a -U ${USER} sudo && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USER} && \
    groupmod -a -U ${USER} npm

USER $USER

# RUN umask 0002 && \
#     npm config -g set prefix ${NPM_GLOBAL}
