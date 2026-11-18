import json
import os
from pathlib import Path

mode = os.environ["DHCP_MODE"]
node = os.environ["NODE"]
socket = "/run/kea/kea-dhcp4-ctrl.sock"
test_ipxe = (
    "substring(option[77].hex,0,4) == 'iPXE' or "
    "substring(option[77].hex,1,4) == 'iPXE' or option[175].exists"
)
classes = [
    ("ipxe", test_ipxe, "http://192.168.30.14/alpine/boot.ipxe"),
    ("bios", "not member('ipxe') and substring(option[93].hex,0,2) == 0x0000", "undionly.kpxe"),
    ("uefi", "not member('ipxe') and (substring(option[93].hex,0,2) == 0x0007 or "
     "substring(option[93].hex,0,2) == 0x0009)", "ipxe.efi"),
]
peers = [
    {
        "name": name,
        "url": f"http://{name}:8000/",
        "role": role,
        "auto-failover": True,
    }
    for name, role in [("kea-primary", "primary"), ("kea-standby", "standby")]
]

def hook(filename):
    lib = Path("/usr/lib")
    for directory in [lib / "kea", *lib.glob("*/kea")]:
        candidate = directory / "hooks" / filename
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(filename)


def subnet(vlan):
    prefix = f"192.168.{vlan}"
    config = {
        "id": vlan,
        "subnet": f"{prefix}.0/24",
        "pools": [{"pool": f"{prefix}.100 - {prefix}.200"}],
        "option-data": [
            {"name": "routers", "data": f"{prefix}.1"},
            {"name": "domain-name-servers", "data": "1.1.1.1, 8.8.8.8"},
        ],
    }
    if vlan == 10 or mode == "direct":
        config["interface"] = f"lab.{vlan}"
    if vlan == 30:
        config["next-server"] = f"{prefix}.14"
        config["require-client-classes"] = [name for name, _, _ in classes]
        if mode == "relay":
            config["relay"] = {"ip-addresses": [f"{prefix}.2", f"{prefix}.3"]}
    return config

dhcp = {
    "interfaces-config": {
        "interfaces": ["lab.10", "lab.30"] if mode == "direct" else ["lab.10"],
    },
    "lease-database": {
        "type": "postgresql",
        "host": os.environ["DB_HOST"],
        "name": "keadb",
        "user": "kea",
        "password": os.environ["KEA_DB_PASSWORD"],
        "connect-timeout": 3,
        "tcp-user-timeout": 5000,
        "max-reconnect-tries": 60,
        "reconnect-wait-time": 1000,
        "retry-on-startup": True,
    },
    "control-socket": {"socket-type": "unix", "socket-name": socket},
    "valid-lifetime": 4000,
    "max-lifetime": 7200,
    "subnet4": [subnet(10), subnet(30)],
    "client-classes": [
        {
            "name": name,
            "test": expression,
            "only-if-required": True,
            "boot-file-name": filename,
            "option-data": [{"name": "boot-file-name", "data": filename}],
        }
        for name, expression, filename in classes
    ],
    "hooks-libraries": [
        {"library": hook("libdhcp_lease_cmds.so")},
        {
            "library": hook("libdhcp_ha.so"),
            "parameters": {
                "high-availability": [{
                    "this-server-name": "kea-primary" if node == "11" else "kea-standby",
                    "mode": "hot-standby",
                    "heartbeat-delay": 1000,
                    "max-response-delay": 3000,
                    "max-unacked-clients": 0,
                    "multi-threading": {"http-dedicated-listener": False},
                    "send-lease-updates": False,
                    "sync-leases": False,
                    "peers": peers,
                }]
            },
        },
    ],
    "loggers": [{"name": "kea-dhcp4", "output_options": [{"output": "stdout"}], "severity": "INFO"}],
}
control = {
    "http-host": "0.0.0.0",
    "http-port": 8000,
    "control-sockets": {"dhcp4": {"socket-type": "unix", "socket-name": socket}},
    "loggers": [{"name": "kea-ctrl-agent", "output_options": [{"output": "stdout"}], "severity": "INFO"}],
}
for filename, config in [
    ("kea-dhcp4.conf", {"Dhcp4": dhcp}),
    ("kea-ctrl-agent.conf", {"Control-agent": control}),
]:
    Path("/etc/kea", filename).write_text(json.dumps(config, indent=2) + "\n")
