#!/usr/bin/env bash
set -euo pipefail

# Egress firewall wrapper, inert unless ENABLE_FIREWALL=true; runs before dockerd so the
# flush keeps the engine's rules. Only deploy admits a proxy.
# Spec: firewall, standalone-opencode-runtime.

allowlist="${FIREWALL_ALLOWLIST:-/etc/agentdev/firewall-allowlist.txt}"
init_firewall="${AGENTDEV_INIT_FIREWALL:-/usr/local/bin/init-firewall.sh}"
web_ports="${AGENTDEV_OPENCODE_PORT:-4096},${AGENTDEV_XPRA_PORT:-14500}"
domain_re='^(\*\.)?[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$'
cidr_re='^([0-9]{1,3}\.){3}[0-9]{1,3}/([0-9]|[12][0-9]|3[0-2])$'

fail() {
  echo "runtime-firewall: $*" >&2
  exit 1
}

if [[ ${ENABLE_FIREWALL:-false} != true ]]; then
  echo "runtime-firewall: ENABLE_FIREWALL is not 'true'; the firewall stays inert"
  exit 0
fi

validate_allowlist() {
  local line number=0
  [[ -f $allowlist ]] || fail "allowlist $allowlist does not exist"
  while IFS= read -r line || [[ -n $line ]]; do
    number=$((number + 1))
    line="${line%%#*}"
    line="${line//[[:space:]]/}"
    [[ -z $line || $line == github-meta || $line =~ $domain_re ]] ||
      fail "$allowlist:$number: '$line' is neither github-meta nor a domain name"
  done <"$allowlist"
}

read_proxy_cidrs() {
  local cidr
  proxy_cidrs=()
  for cidr in ${AGENTDEV_TRUSTED_PROXY_CIDRS//,/ }; do
    [[ $cidr =~ $cidr_re ]] || fail "AGENTDEV_TRUSTED_PROXY_CIDRS entry '$cidr' is not an IPv4 CIDR"
    proxy_cidrs+=("$cidr")
  done
  ((${#proxy_cidrs[@]} > 0)) ||
    fail "ENABLE_FIREWALL=true requires AGENTDEV_TRUSTED_PROXY_CIDRS, or the proxy cannot reach $web_ports"
}

# Inbound: only the trusted proxy sources reach the web ports.
allow_proxy_ingress() {
  local cidr
  for cidr in "${proxy_cidrs[@]}"; do
    iptables -A INPUT -p tcp -s "$cidr" -m multiport --dports "$web_ports" -j ACCEPT
  done
}

# Nested containers' traffic is forwarded, not output, so the allowlist is applied
# again in DOCKER-USER, which dockerd keeps and consults before its own rules.
filter_nested_egress() {
  iptables -N DOCKER-USER 2>/dev/null || iptables -F DOCKER-USER
  iptables -A DOCKER-USER -m state --state ESTABLISHED,RELATED -j RETURN
  iptables -A DOCKER-USER -o docker0 -j RETURN
  iptables -A DOCKER-USER -o br-+ -j RETURN
  iptables -A DOCKER-USER -m set --match-set allowed-domains dst -j RETURN
  iptables -A DOCKER-USER -j REJECT --reject-with icmp-admin-prohibited
}

validate_allowlist
if [[ ${AGENTDEV_RUNTIME_MODE:-} == deploy ]]; then
  read_proxy_cidrs
fi
FIREWALL_ALLOWLIST="$allowlist" "$init_firewall"
if [[ ${AGENTDEV_RUNTIME_MODE:-} == deploy ]]; then
  allow_proxy_ingress
  echo "runtime-firewall: proxy sources ${proxy_cidrs[*]} may reach ports $web_ports"
fi
filter_nested_egress
