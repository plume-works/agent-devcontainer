ARG BASE_IMAGE
FROM ${BASE_IMAGE}

COPY --chmod=0755 fixture-tool /usr/local/bin/fixture-tool
COPY --chmod=0755 hooks/ /etc/agentdev/hooks/
# A documented setting, overridden by the derived image.
ENV AGENTDEV_SKIP_XPRA=1
