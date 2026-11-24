# Containers stories

## Developer of agentdev

1. As a developer of agentdev I want to be able to have the following workflow:

   - clone the repo
   - open in vscode
   - reopen in devcontainer
   - my checkout is available and agentdev plugins are used from checkout, not devcontainer seed.

1. As a developer of agentdev I want CI reviews for repo changes to run in same image as devcontainer
1. As a developer of agentdev I want to deploy devcontainer in Coder workspace

## Agentdev user

1. As an agentdev user I want to be able to deploy a container image on my servers (plume-works' Coder template image; this repository no longer publishes `agentdev-deploy`) that allows me to:
   - use agentdev skills and tools
   - use agentdev rules and practices as a foundation
   - have claude/codex/opencode work inside of the container
   - develop other repo (Repo Under Development, RUD) inside of it
   - initialize RUD to have only things that have to be independent: iwe kb, CI jobs: kb, review, builds.
   - RUD CI should be able to utilize agentdev's docker image
   - RUD should be able to override rules with its own
   - RUD can have its own minor devcontainer for testing (e.g. expo app, ROS app)

1. As an agentdev user I want be able to have a custom container image for my custom tooling derived from agentdev. I want to still be able to use all the features of the agentdev. Sub-scenarios:
   1. I have full copy of devcontainer (as current template-consume, how Dr.QP currently does it)
   1. I have repo that only has iwe kb and CI adopted, the rest is coming as devcontainer derived from agentdev-devcontainer image
   1. I have my own devcontainer derived from agentdev-devcontainer image

`agentdev-devcontainer` image: agentdev's image that bundles all needed scripts. It is built on `ghcr.io/plume-works/devcontainer-base`, whose systemd runs the persistent services, and it supplies the create, start, and attach lifecycle commands through its Dev Container metadata. Scripts include customization points via environment variables and executable files in ordered hook directories (`/etc/agentdev/hooks/{created,started,attached}.d/`), without replacing managed runtime files.

Sub-scenarios 2 and 3 are the supported adoption modes; a full copy of the devcontainer is not supported:

- **Direct** — a descriptor references `agentdev-devcontainer` by tag and digest and copies no lifecycle script.
- **Derived** — a custom image starts `FROM agentdev-devcontainer` and adds tooling and hooks.

## Image tree

```text
ghcr.io/plume-works/devcontainer-base   systemd, Docker engine, toolchain, agents
└── agentdev-devcontainer               Xpra, pinned tools, staged catalog, firewall, lifecycle commands
```
