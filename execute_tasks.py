import os
import logging
import paramiko
import yaml
import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_ssh(host, user, password, cmd, port=22, use_sudo=False):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user, password=password)

    if use_sudo:
        cmd = f"sudo -S -p '' bash -c '{cmd}'"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdin.write(password + "\n")
        stdin.flush()
    else:
        stdin, stdout, stderr = ssh.exec_command(cmd)

    output = stdout.read().decode("utf-8")
    error = stderr.read().decode("utf-8")
    exit_code = stdout.channel.recv_exit_status()

    ssh.close()
    return output, error, exit_code


def execute_tasks(inventory, todos):
    for name, machine in inventory.get("hosts", {}).items():
        ip = machine["ssh_address"]
        port = machine.get("ssh_port", 22)
        user = machine["identifier"]["ssh_user"]
        password = machine["identifier"]["ssh_password"]

        logging.info(f"Connexion à {name} ({ip}:{port})...")

        for task in todos:
            module = task.get("module")
            params = task.get("params", {})

            try:
                if module == "command":
                    cmd = params.get("command") or params.get("cmd")
                    output, error, exit_code = run_ssh(ip, user, password, cmd, port, use_sudo=params.get("sudo", False))

                elif module == "apt":
                    pkg = params["name"]
                    state = params.get("state", "present")
                    
                    if state == "present":
                        cmd = f"apt-get update && apt-get install -y {pkg}"
                    else:
                        cmd = f"apt-get remove -y {pkg}"
                    
                    output, error, exit_code = run_ssh(ip, user, password, cmd, port, use_sudo=True)

                elif module == "service":
                    svc = params["name"]
                    state = params.get("state", "started")

                    if svc == "docker" and state == "started":
                        check_cmd = "command -v docker"
                        output, error, exit_code = run_ssh(ip, user, password, check_cmd, port, use_sudo=False)
                        
                        if exit_code != 0:
                            install_cmd = "apt-get update && apt-get install -y docker.io && systemctl enable docker"
                            output, error, exit_code = run_ssh(ip, user, password, install_cmd, port, use_sudo=True)

                    action = "start" if state == "started" else "stop"
                    if state == "restarted":
                        action = "restart"
                    elif state == "reloaded":
                        action = "reload"
                    
                    cmd = f"systemctl {action} {svc}"
                    output, error, exit_code = run_ssh(ip, user, password, cmd, port, use_sudo=True)
                    
                elif module == "sysctl":
                    attr = params["attribute"]
                    value = params["value"]
                    permanent = params.get("permanent", False)
                    
                    cmd = f"sysctl -w {attr}={value}"
                    if permanent:
                        cmd += f" && echo '{attr}={value}' >> /etc/sysctl.conf"
                    
                    output, error, exit_code = run_ssh(ip, user, password, cmd, port, use_sudo=True)

            except Exception as e:
                logging.error(f"[{name}] Erreur {module} : {e}")

        logging.info(f"Fin des tâches pour {name}\n")


@click.command()
@click.option("-f", "--file", "tasks_file", required=True)
@click.option("-i", "--inventory", "inventory_file", required=True)
def main(tasks_file, inventory_file):
    execute_tasks(load_yaml(inventory_file), load_yaml(tasks_file))

if __name__ == "__main__":
    main()