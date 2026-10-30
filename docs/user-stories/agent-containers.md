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

1. As an agentdev user I want to be able to deploy agentdev-deploy docker image on my servers that allows me to:
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

`agentdev-devcontainer` image: agentdev's image that bundles all needed scripts. It runs the persistent services from its entrypoint and supplies the create, start, and attach lifecycle commands through its Dev Container metadata. Scripts include customization points via environment variables and executable files in ordered hook directories (`/etc/agentdev/hooks/{created,started,attached}.d/`), without replacing managed runtime files.

The three sub-scenarios above are the supported adoption modes:

- **Full adoption** — `/agentdev:template-consume` copies the descriptor, Compose file, and workflows; it remains supported and uses the same published runtime.
- **Direct** — a descriptor references `agentdev-devcontainer` by tag and digest and copies no lifecycle script.
- **Derived** — a custom image starts `FROM agentdev-devcontainer` and adds tooling and hooks.

See [Dev Container runtime](../knowledge/data/architecture/devcontainer-runtime.md).

## Image tree

```text
ubuntu
└── ubuntu-ansible
    └── agentdev-base          lifecycle-neutral: tools, staged catalog, validators
        ├── agentdev-deploy        single-project runtime, no Dev Containers client
        └── agentdev-devcontainer  Dev Container runtime and lifecycle commands
```

`agentdev-base` replaces `agent-desktop`, and `agentdev-deploy` replaces `agent-opencode`; the old names are no longer published.
