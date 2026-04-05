FROM archlinux:latest

# Update and install build essentials + tools
RUN pacman -Syu --noconfirm \
    base-devel \
    devtools \
    nvchecker \
    jq \
    git \
    sudo \
    rclone \
    python-jq \
    python-toml \
    && pacman -Scc --noconfirm

# Create a builder user for makepkg/devtools
RUN useradd -m builder && \
    echo "builder ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Configure devtools to use a specific directory for chroots if needed
# But usually extra-x86_64-build handles this.

WORKDIR /workspace
CHOWN builder:builder /workspace

USER root
