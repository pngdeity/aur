FROM archlinux:base-devel@sha256:6d08b7067286234b755a28340b6bd89f3a2289233dbca3c361464f27ecae8f08

RUN pacman -Syu --noconfirm \
    devtools \
    git \
    sudo \
    jq \
    nvchecker \
    openssh \
    pacman-contrib \
    rsync \
    gnupg \
    && pacman -Scc --noconfirm

RUN useradd -m builder && \
    echo "builder ALL=(ALL) NOPASSWD: /usr/bin/pacman" >> /etc/sudoers && \
    echo "builder ALL=(ALL) NOPASSWD: /usr/bin/makechrootpkg" >> /etc/sudoers

USER root
