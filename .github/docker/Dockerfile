FROM archlinux:base-devel

# Update and install build essentials + tools
RUN pacman -Syu --noconfirm \
    devtools \
    git \
    sudo \
    && pacman -Scc --noconfirm

# Create a builder user for makepkg/devtools
RUN useradd -m builder && \
    echo "builder ALL=(ALL) NOPASSWD: /usr/bin/pacman" >> /etc/sudoers

USER root
