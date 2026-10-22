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

agentdev-devcontainer image: agentdev's image that bundles all needed scripts. Scripts include customization points via env variables or replacement scripts in my devcontainer.

--

Image tree:

ubuntu
|--- agentdev-ansible
|--- agentdev-base (renamed agent-desktop, bundles plugins and basic tools)
|--- agentdev-deploy (renamed agent-opencode)
|--- agentdev-devcontainer (new image, includes all devcontainer scripts as described above)
