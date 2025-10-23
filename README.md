# ansible-orchestrator

**Description :**  
Orchestrateur simple pour exécuter des tâches sur une VM Debian.
---

## VM

- **OS :** Debian
- **Connexion SSH / Protocole TCP :** NAT + redirection de port
  - Port hôte : `2222`
  - Port invité : `22`

---

## Commande à exécuter

```bash
python main.py -f todos.yml -i inventory.yml
