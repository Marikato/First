# Vinted Deal Monitor

Monitoriza o Vinted em tempo real com filtros personalizados e destaca os melhores deals automaticamente.

## Instalação

```bash
pip install -r requirements.txt
```

> **Nota:** Este monitor tem de correr na tua própria máquina (casa/VPN). O Vinted bloqueia pedidos de servidores cloud.

## Uso Rápido

```bash
# Iniciar monitorização contínua
python main.py

# Ver os monitores configurados
python main.py list

# Adicionar novo monitor (modo interativo)
python main.py add

# Remover um monitor
python main.py remove "Nike Air Max"

# Verificar uma vez e sair
python main.py check
```

## Configuração (`monitors.json`)

```json
{
  "country": "pt",
  "check_interval": 60,
  "monitors": [
    {
      "name": "Nike Air Max",
      "search_text": "nike air max",
      "price_to": 60,
      "price_from": 10,
      "order": "newest_first"
    },
    {
      "name": "Levi's 501",
      "search_text": "levis 501",
      "price_to": 40,
      "order": "newest_first"
    }
  ]
}
```

### Campos disponíveis por monitor

| Campo | Tipo | Descrição |
|---|---|---|
| `name` | string | Nome do monitor (obrigatório) |
| `search_text` | string | Texto de pesquisa |
| `price_to` | número | Preço máximo em € |
| `price_from` | número | Preço mínimo em € |
| `order` | string | `newest_first` ou `price_low_to_high` |
| `per_page` | inteiro | Itens por pesquisa (default: 24) |
| `catalog_ids` | lista | IDs de categoria Vinted |
| `brand_ids` | lista | IDs de marca Vinted |
| `size_ids` | lista | IDs de tamanho Vinted |
| `status_ids` | lista | IDs de condição (1=novo, 2=muito bom, 3=bom, 4=razoável) |

### Países suportados

`pt`, `fr`, `es`, `de`, `uk`, `it`, `be`, `nl`, `pl`, `cz`

## Sistema de Deals

O monitor classifica cada item com base no preço vs. o `price_to` configurado:

| Badge | Condição |
|---|---|
| 🔥 FIRE DEAL | Preço ≤ 40% do máximo |
| ✨ GREAT DEAL | Preço ≤ 60% do máximo |
| 👍 GOOD DEAL | Preço ≤ 80% do máximo |
| NEW | Item novo sem contexto de preço |

## Notificações Discord

Adiciona o teu webhook ao `monitors.json`:

```json
{
  "discord_webhook": "https://discord.com/api/webhooks/ID/TOKEN",
  ...
}
```

**Como criar um webhook no Discord:**
1. Vai às definições do canal → Integrações → Webhooks
2. Clica em "Novo Webhook"
3. Copia o URL e cola no `monitors.json`

Cada deal novo aparece como um embed colorido no canal:
- 🔥 Borda vermelha → Fire Deal
- ✨ Borda amarela → Great Deal
- 👍 Borda verde → Good Deal
- 🆕 Borda azul → Item novo

## Proxy (Opcional)

Se correres de um servidor ou VPN:

```bash
python main.py --proxy http://user:pass@host:port
```

## Como funciona

1. Lê os monitores do `monitors.json`
2. A cada `check_interval` segundos, pesquisa no Vinted
3. Guarda os IDs vistos em `~/.vinted_seen.json` para não repetir
4. Mostra apenas itens novos com o badge de deal correspondente
5. Atualiza a config automaticamente sem reiniciar
