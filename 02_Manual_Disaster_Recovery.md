# Manual de Sobrevivência: Backup e Restauração (Disaster Recovery) 🛡️

Este documento é o seu plano de recuperação de desastres. Se a Oracle Cloud deletar a sua instância, o seu HD queimar, ou o servidor for irremediavelmente corrompido, este manual garantirá que você reconstrua 100% da sua infraestrutura de mídia em menos de 15 minutos, sem perder históricos, senhas ou configurações.

---

## ⚙️ Como o Backup Funciona Atualmente

O sistema possui um backup automatizado rodando silenciosamente na sua VPS da Oracle.

### O que é salvo?
Toda a pasta `/home/ubuntu/configs` é backupeada. Isso inclui:
- A "planta baixa" do servidor (`docker-compose.yml`).
- Os bancos de dados e configurações internas de todos os aplicativos (Radarr, Sonarr, Prowlarr, Jellyseerr, NPM, etc).
- Certificados SSL do Nginx Proxy Manager.
- A configuração do servidor anti-bloqueio Nginx do Brazuca TV (`brazuca-proxy`).

> [!NOTE]
> **Pastas Ignoradas:** As pastas de `cache` e `transcodes` do Jellyfin são propositalmente ignoradas durante o backup para que o arquivo gerado seja leve (~270MB) e o upload seja rápido. Os seus filmes também não entram no backup, pois já estão seguros nativamente no Google Drive.

### A Mecânica (Automação)
1. **Agendamento:** Um serviço nativo do Linux (`systemd timer`) dispara o script `/home/ubuntu/scripts/backup_configs.sh` todos os dias exatamente às **04:00 da manhã** (Horário de Brasília).
2. **Consistência Segura:** O script paralisa todos os contêineres Docker momentaneamente para evitar que bancos de dados SQLite sejam corrompidos se forem lidos no exato momento de uma gravação.
3. **Compactação:** A pasta inteira é zipada no formato `.tar.gz`.
4. **Religamento:** O Docker é religado instantaneamente (Downtime geral < 20 segundos).
5. **Nuvem:** O `rclone` assume o comando e faz o upload invisível do arquivo zipado direto para o seu Google Drive na pasta `Homelab_Backups`.
6. **Faxina:** O Rclone deleta do Google Drive qualquer backup que seja mais antigo que 7 dias, evitando que o seu armazenamento encha com lixo antigo.

---

## 🆘 Guia de Restauração (Como reviver o servidor)

Se você perdeu tudo e está olhando para um servidor ou PC completamente "cru" e recém-formatado, siga estes passos para clonar a infraestrutura anterior:

### Passo 1: Preparar o Terreno (Requisitos Básicos)
No novo servidor (Oracle, AWS, PC Local), instale as ferramentas base:
1. Instale o **Docker** e o **Docker Compose**.
2. Instale o **Rclone**.
3. Configure o Rclone executando `rclone config` e reconecte a sua conta do Google Drive com o exato mesmo nome de antes (`gdrive`).

### Passo 2: O Resgate
Navegue até a pasta onde deseja reconstruir a infraestrutura (recomendado `/home/ubuntu` na Oracle, ou na sua pasta de usuário local).

1. Crie a pasta de destino temporária:
   ```bash
   mkdir -p /home/ubuntu/backups
   ```
2. Puxe o último backup do seu Google Drive via Rclone:
   ```bash
   rclone copy gdrive:Homelab_Backups /home/ubuntu/backups
   ```
   *(Caso não queira usar o comando rclone, você pode simplesmente baixar o `.tar.gz` pelo aplicativo do Google Drive no seu celular/PC e enviar para a máquina via app cliente SSH como o Termux ou SFTP).*

### Passo 3: A Ressurreição
Com o arquivo `.tar.gz` em mãos, vamos desempacotar:

1. Extraia o conteúdo na raiz do seu usuário:
   ```bash
   tar -xzvf /home/ubuntu/backups/homelab_backup_DATA_AQUI.tar.gz -C /home/ubuntu/
   ```
2. Isso criará automaticamente a pasta `/home/ubuntu/configs` com tudo lá dentro intacto.
3. Entre na pasta e ligue a infraestrutura:
   ```bash
   cd /home/ubuntu/configs
   docker compose up -d
   ```

> [!TIP]
> **A Mágica:** Neste exato momento, o Docker fará o download da internet das "carcaças" dos aplicativos mais atualizados e injetará nelas o "cérebro" que acabamos de extrair do backup. Tudo subirá no ar perfeitamente, sem necessidade de refazer login em contas ou reconfigurar indexadores no Prowlarr.

### Passo 4: Ajustes Finais de Rede (Pós-Restauração)
Como você mudou de máquina, a única coisa que realmente mudou foi o seu endereço na rede. Faça o seguinte check-up:

- **DuckDNS:** Se o novo servidor tiver um IP Público diferente da Oracle original, o contêiner do DuckDNS vai automaticamente atualizar seu domínio (`yourdomain.duckdns.org`) em menos de 5 minutos, apontando para a nova máquina. Apenas aguarde.
- **Tailscale:** O Tailscale no novo servidor precisará ser logado e autenticado novamente. Rode `sudo tailscale up` na máquina nova para ingressá-la na sua malha. *Atenção:* Como o IP `100.x.x.x` da máquina nova será diferente da antiga, você deve abrir o `docker-compose.yml`, procurar onde estava o IP `100.x.x.x` antigo nas portas expostas e substituir pelo seu NOVO IP do Tailscale, rodando `docker compose up -d` em seguida para aplicar a mudança.
- **Montagem do Google Drive:** Lembre-se de configurar a montagem contínua do Google Drive (o script de Rclone mount) no servidor novo, pois o Jellyfin precisa da pasta `/home/ubuntu/GoogleDrive` pronta para ler os filmes.

---

## 📱 Recuperação do Worker Android (Termux)

Se o celular que funciona como worker (Motorola E7+) precisar ser restaurado — seja por formatação, falha no sistema, ou migração para outro dispositivo — existem **duas estratégias** de restore, dependendo se o Termux está ou não instalado.

### Pré-requisito comum: Backup descompactado no celular

Ambos os scripts esperam encontrar o backup extraído em `/sdcard/Download/TermuxBackup/`. O backup semanal automático (domingos às 03:00) salva o snapshot em `gdrive:Blackhole/Backups_Termux/`. Para extrair:

```bash
# No celular, baixe o snapshot mais recente do Google Drive
# e extraia para a pasta esperada:
mkdir -p /sdcard/Download/TermuxBackup
tar -xzvf termux-snapshot-YYYY-MM-DD_HH-MM.tar.gz -C /sdcard/Download/TermuxBackup/
```

### Estratégia 1: `restore.sh` — Recuperação total (sem Termux)

**Quando usar:** Celular formatado, Termux **não está instalado**, ou você está partindo do zero absoluto (acesso via ADB shell ou recovery customizado).

**Shebang:** `#!/system/bin/sh` — roda fora do ambiente Termux, exportando manualmente o prefixo.

**O que ele faz:**
1. Define `$PREFIX` apontando para `/data/data/com.termux/files/usr`
2. Copia `.ssh`, `.config`, `.termux`, scripts `.sh`, `.py` e `templates/` para o home do Termux
3. Instala todos os pacotes: `openssh`, `python`, `transmission`, `tailscale`, `rclone`, `tmux`, `termux-services`, `jq`
4. Instala o **wrapper anti-zumbi** do Transmission
5. Instala pacotes Python: `flask`, `requests`
6. Ao final, **inicia todos os serviços**: `termux-wake-lock` → `start-proxy` → `start_servers.sh`

```bash
# Executar via ADB shell (conectado por USB ou WiFi):
adb shell
cd /sdcard/Download/TermuxBackup
sh restore.sh
```

### Estratégia 2: `restore2.sh` — Recuperação parcial (com Termux)

**Quando usar:** O Termux **já está instalado** e funcionando, mas os scripts/configs foram perdidos ou corrompidos. Ideal para recuperação rápida onde você quer fazer o grosso do trabalho via SSH depois.

**Shebang:** Nenhum — roda **dentro** do ambiente Termux, usando `~` e as variáveis de ambiente já configuradas.

**O que ele faz:**
1. Copia os mesmos arquivos do backup usando caminhos relativos (`~`)
2. Instala os mesmos pacotes e wrapper anti-zumbi
3. Instala os pacotes Python
4. Ao final, **inicia apenas o SSHD**, permitindo que você se conecte remotamente e termine a configuração manualmente

```bash
# Executar de dentro do Termux (app aberto no celular):
cd /sdcard/Download/TermuxBackup
bash restore2.sh
# Depois, de outro dispositivo na rede Tailscale:
ssh worker
# E finalizar com start_servers.sh para subir todos os serviços
```

### Resumo das diferenças

| | `restore.sh` | `restore2.sh` |
|---|---|---|
| **Contexto** | Fora do Termux (ADB/recovery) | Dentro do Termux |
| **Shebang** | `#!/system/bin/sh` | Nenhum |
| **Caminhos** | Absolutos (`$PREFIX/../home/`) | Relativos (`~`) |
| **Serviços ao final** | Todos (proxy + workers + transmission) | Apenas SSH |
| **Uso típico** | Celular zerado, reconstrução total | Scripts perdidos, recuperação rápida |

---

## 🖥️ Configurações de BIOS e Wake-on-LAN (PC Desktop)

Se a bateria da placa-mãe (CR2032) zerar, ocorrer uma queda abrupta de energia ou a BIOS resetar para os padrões de fábrica, siga esta tabela para reativar o Wake-on-LAN (WOL) e a recuperação automática de energia na placa-mãe **MSI H310M PRO-M2 (MS-7B28)** com placa de rede integrada **Intel I219-V**:

### 1. `Settings \ Advanced \ Wake Up Event Setup`
| Opção | Valor | Finalidade |
|---|---|---|
| **`Wake Up Event By`** | **`[BIOS]`** | **Obrigatório.** Se estiver em `[OS]`, a placa-mãe ignora o sinal de rede para ligar quando desligada. |
| **`Resume By Onboard Intel LAN`** | **`[Enabled]`** | **Obrigatório.** Habilita a escuta do Magic Packet pelo chip de rede Intel integrado (I219-V). |
| **`Resume By PCI-E Device`** | **`[Disabled]`** | **Obrigatório.** Evita que a placa de vídeo AMD Radeon (PEG0 / amdgpu) trave ao desligar o PC. |
| `Resume By RTC Alarm` | `[Disabled]` | Evita inicializações automáticas por timer. |
| `Resume By USB Device` | `[Disabled]` | Evita que o PC ligue por toque acidental em mouse/teclado. |

### 2. `Settings \ Advanced \ Power Management Setup`
| Opção | Valor | Finalidade |
|---|---|---|
| **`ErP Ready`** | **`[Disabled]`** | **Obrigatório.** Se estiver `[Enabled]`, corta a alimentação de standby (+5VSB), apagando a placa de rede com o PC desligado. |
| **`Restore after AC Power Loss`** | **`[Power On]`** ou **`[Last State]`** | Faz o PC ligar sozinho assim que a energia da tomada voltar após o no-break descarregar. |

### 3. `Settings \ Boot`
| Opção | Valor | Finalidade |
|---|---|---|
| **`Fast Boot` / `MSI Fast Boot`** | **`[Disabled]`** | Garante que o hardware de rede seja inicializado apropriadamente em todos os desligamentos. |

> [!TIP]
> **Diagnóstico Rápido pelos LEDs:**
> Com o PC desligado (mas conectado à tomada/no-break), olhe para a porta RJ-45 na traseira do PC:
> - **LED aceso (verde/laranja):** Hardware pronto e em escuta.
> - **LED 100% apagado:** Falha de alimentação em standby — a BIOS perdeu as configurações acima (ou ErP está ativado).

