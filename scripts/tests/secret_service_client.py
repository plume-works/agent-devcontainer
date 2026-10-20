#!/usr/bin/env python3
"""
Store or look up one Secret Service item over a single D-Bus connection.

Run with the system interpreter, which carries PyGObject. Usage:
``secret_service_client.py store <attribute> <secret>`` or ``lookup <attribute>``.
"""

from __future__ import annotations

import sys

from gi.repository import Gio, GLib

SERVICE = 'org.freedesktop.secrets'
ROOT = '/org/freedesktop/secrets'


def call(bus: Gio.DBusConnection, path: str, interface: str, method: str, args: GLib.Variant):
    """Invoke one Secret Service method and return its unpacked reply."""
    reply = bus.call_sync(
        SERVICE, path, interface, method, args, None, Gio.DBusCallFlags.NONE, 5000, None
    )
    return reply.unpack()


def main() -> int:
    """Run the requested operation; exit 1 when a lookup finds nothing."""
    action, attribute = sys.argv[1], sys.argv[2]
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    _, session = call(
        bus,
        ROOT,
        'org.freedesktop.Secret.Service',
        'OpenSession',
        GLib.Variant('(sv)', ('plain', GLib.Variant('s', ''))),
    )
    attributes = {'agentdev-test': attribute}
    # Like go-keyring and libsecret: the empty-password login keyring unlocks without a prompt.
    call(
        bus,
        ROOT,
        'org.freedesktop.Secret.Service',
        'Unlock',
        GLib.Variant('(ao)', ([f'{ROOT}/collection/login'],)),
    )
    if action == 'store':
        secret = (session, b'', sys.argv[3].encode(), 'text/plain')
        properties = {
            'org.freedesktop.Secret.Item.Label': GLib.Variant('s', attribute),
            'org.freedesktop.Secret.Item.Attributes': GLib.Variant('a{ss}', attributes),
        }
        call(
            bus,
            f'{ROOT}/aliases/default',
            'org.freedesktop.Secret.Collection',
            'CreateItem',
            GLib.Variant('(a{sv}(oayays)b)', (properties, secret, True)),
        )
        return 0
    unlocked, _ = call(
        bus,
        ROOT,
        'org.freedesktop.Secret.Service',
        'SearchItems',
        GLib.Variant('(a{ss})', (attributes,)),
    )
    if not unlocked:
        return 1
    (secrets,) = call(
        bus,
        ROOT,
        'org.freedesktop.Secret.Service',
        'GetSecrets',
        GLib.Variant('(aoo)', (unlocked, session)),
    )
    print(bytes(secrets[unlocked[0]][2]).decode())
    return 0


if __name__ == '__main__':
    sys.exit(main())
