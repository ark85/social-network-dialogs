import json
import os
import sys
import time
import urllib.error
import urllib.request

from zabbix_utils import ZabbixAPI

FACTORY_ADMIN_USERNAME = "Admin"
FACTORY_ADMIN_PASSWORD = "zabbix"
DOCKER_TEMPLATE_NAME = "Docker by Zabbix agent 2"
HOST_GROUP_NAME = "Docker"
BUILTIN_ZABBIX_SERVER_HOST = "Zabbix server"
API_RETRY_INTERVAL_SECONDS = 5


def main() -> None:
    url = get_zabbix_url()
    username = os.environ["ZABBIX_ADMIN_USERNAME"]
    password = os.environ["ZABBIX_ADMIN_PASSWORD"]
    wait_until_zabbix_responds(url)
    login_or_replace_factory_admin(url, username, password)
    zabbix_client = ZabbixAPI(url=url, user=username, password=password)
    remove_builtin_zabbix_server(zabbix_client)
    template_id = wait_for_template_id(zabbix_client)
    group_id = get_or_create_host_group(zabbix_client)
    create_or_update_docker_host(zabbix_client, template_id, group_id)


def get_zabbix_url() -> str:
    return os.environ.get("ZABBIX_URL", "http://zabbix-web:8080")


def wait_until_zabbix_responds(url: str) -> None:
    while True:
        try:
            payload = call_zabbix(url, "apiinfo.version", {})
        except (urllib.error.URLError, TimeoutError):
            print("waiting for Zabbix")
            time.sleep(API_RETRY_INTERVAL_SECONDS)
            continue
        if "result" in payload:
            return
        print("waiting for Zabbix")
        time.sleep(API_RETRY_INTERVAL_SECONDS)


def login_or_replace_factory_admin(url: str, username: str, password: str) -> None:
    if is_login_accepted(url, username, password):
        return
    if not is_login_accepted(url, FACTORY_ADMIN_USERNAME, FACTORY_ADMIN_PASSWORD):
        raise SystemExit("cannot log in as the configured admin or the initial Admin user")
    factory_client = ZabbixAPI(
        url=url,
        user=FACTORY_ADMIN_USERNAME,
        password=FACTORY_ADMIN_PASSWORD,
    )
    admin_user_id = factory_client.user.get(
        filter={"username": FACTORY_ADMIN_USERNAME},
        output=["userid"],
    )[0]["userid"]
    factory_client.user.update(
        userid=admin_user_id,
        username=username,
        passwd=password,
        current_passwd=FACTORY_ADMIN_PASSWORD,
    )


def is_login_accepted(url: str, username: str, password: str) -> bool:
    payload = call_zabbix(url, "user.login", {"username": username, "password": password})
    if "result" in payload:
        return True
    if are_credentials_rejected(payload):
        return False
    raise RuntimeError(payload.get("error"))


def get_or_create_host_group(zabbix_client: ZabbixAPI) -> str:
    groups = zabbix_client.hostgroup.get(filter={"name": HOST_GROUP_NAME}, output=["groupid"])
    if groups:
        return groups[0]["groupid"]
    created = zabbix_client.hostgroup.create(name=HOST_GROUP_NAME)
    print(f"created host group {HOST_GROUP_NAME}")
    return created["groupids"][0]


def create_or_update_docker_host(zabbix_client: ZabbixAPI, template_id: str, group_id: str) -> None:
    hostname = os.environ["ZABBIX_AGENT_HOSTNAME"]
    existing_hosts = zabbix_client.host.get(
        filter={"host": hostname},
        output=["hostid"],
        selectParentTemplates=["templateid"],
        selectHostGroups=["groupid"],
    )
    if not existing_hosts:
        zabbix_client.host.create(
            host=hostname,
            interfaces=[build_agent_interface()],
            groups=[{"groupid": group_id}],
            templates=[{"templateid": template_id}],
        )
        print(f"created host {hostname}")
        return

    host = existing_hosts[0]
    linked_template_ids = {template["templateid"] for template in host.get("parentTemplates") or []}
    current_group_ids = {group["groupid"] for group in host.get("hostgroups") or []}
    update = {}
    if template_id not in linked_template_ids:
        update["templates"] = [
            {"templateid": template_id},
            *[{"templateid": linked_template_id} for linked_template_id in linked_template_ids],
        ]
    if current_group_ids != {group_id}:
        update["groups"] = [{"groupid": group_id}]
    if not update:
        print(f"host {hostname} already matches the board")
        return

    zabbix_client.host.update(hostid=host["hostid"], **update)
    print(f"updated host {hostname}")


def remove_builtin_zabbix_server(zabbix_client: ZabbixAPI) -> None:
    hosts = zabbix_client.host.get(filter={"host": BUILTIN_ZABBIX_SERVER_HOST}, output=["hostid"])
    if not hosts:
        print("built-in Zabbix server host is already absent")
        return
    zabbix_client.host.delete([hosts[0]["hostid"]])
    print("removed built-in Zabbix server host")


def wait_for_template_id(zabbix_client: ZabbixAPI) -> str:
    while True:
        templates = zabbix_client.template.get(filter={"host": DOCKER_TEMPLATE_NAME}, output=["templateid"])
        if templates:
            return templates[0]["templateid"]
        print(f"waiting for template {DOCKER_TEMPLATE_NAME}")
        time.sleep(API_RETRY_INTERVAL_SECONDS)


def build_agent_interface() -> dict:
    return {
        "type": 1,
        "main": 1,
        "useip": 0,
        "ip": "",
        "dns": os.environ.get("ZABBIX_AGENT_DNS", "zabbix-agent"),
        "port": "10050",
    }


def call_zabbix(url: str, method: str, params: dict) -> dict:
    endpoint = url if url.endswith("api_jsonrpc.php") else url.rstrip("/") + "/api_jsonrpc.php"
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json-rpc"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def are_credentials_rejected(payload: dict) -> bool:
    message = json.dumps(payload.get("error", {})).casefold()
    return "incorrect user name or password" in message or "temporarily blocked" in message


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
