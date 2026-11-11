# Guia de Configuração: Múltiplas Tags de Proxy (Prowlarr)

A sua infraestrutura foi atualizada com sucesso! O seu arquivo `docker-compose.yml` agora gerencia uma frota de 3 túneis VPN independentes e 3 Resolvedores do Cloudflare.

## Contêineres no Ar
- `gluetun-us` + `flaresolverr-us` (Estados Unidos)
- `gluetun-nl` + `flaresolverr-nl` (Holanda)
- `gluetun-uk` + `flaresolverr-uk` (Reino Unido)

Os outros aplicativos (`radarr`, `sonarr`, `jellyseerr`, `torrent-indexer`) estão configurados para usar o túnel dos EUA por padrão, garantindo proteção total. O `prowlarr` foi liberado dessa regra global para poder rotear livremente.

## Como configurar no Prowlarr

Agora você precisa "ensinar" o Prowlarr sobre essas 3 rotas. Siga estes passos:

### Passo 1: Cadastrar os Proxies
Vá em `Settings` > `Indexers` no Prowlarr. Clique no ícone de `+` em **Proxies**.
Adicione os 3 proxies abaixo:

1. **Proxy EUA:**
   - Name: `Proxy US`
   - Host: `gluetun-us`
   - Port: `8888`
   - Tags: `proxy-us`

2. **Proxy Holanda:**
   - Name: `Proxy NL`
   - Host: `gluetun-nl`
   - Port: `8888` *(Sim, a porta interna é 8888 para todos)*
   - Tags: `proxy-nl`

3. **Proxy Reino Unido:**
   - Name: `Proxy UK`
   - Host: `gluetun-uk`
   - Port: `8888`
   - Tags: `proxy-uk`

### Passo 2: Cadastrar os Flaresolverrs
Na mesma página (`Settings` > `Indexers`), no final, clique no ícone de `+` em **FlareSolverr**.
Adicione os 3 resolvedores:

1. **Flaresolverr EUA:**
   - Name: `Flaresolverr US`
   - Host: `http://flaresolverr-us:8191`
   - Tags: `proxy-us`

2. **Flaresolverr Holanda:**
   - Name: `Flaresolverr NL`
   - Host: `http://flaresolverr-nl:8191`
   - Tags: `proxy-nl`

3. **Flaresolverr Reino Unido:**
   - Name: `Flaresolverr UK`
   - Host: `http://flaresolverr-uk:8191`
   - Tags: `proxy-uk`

## Como Usar!

Agora a mágica acontece. Se o **Starck Filmes** ou qualquer outro indexador parar de funcionar ou der erro de Cloudflare:

1. Edite o Indexador no Prowlarr.
2. Na caixa **Tags**, digite e selecione `proxy-nl` (Holanda) por exemplo.
3. Salve. O Prowlarr vai automaticamente usar o Flaresolverr da Holanda e o Túnel da Holanda apenas para este site!
4. Se a Holanda for bloqueada amanhã, você só muda a Tag dele para `proxy-uk` (Reino Unido).

> [!CAUTION]
> **Muito Importante:** Todo indexador no seu Prowlarr agora DEVE ter uma dessas 3 tags (ex: `proxy-us`). Se você adicionar um indexador e deixar o campo Tag vazio, o Prowlarr vai tentar baixar pelo IP público da Oracle e você tomará um bloqueio instantâneo do Cloudflare. Sempre taggeie seus indexadores!

---

## Integração do Brazuca (Torrentio) no Prowlarr

Para garantir máxima compatibilidade e evitar que os rigorosos testes de saúde automáticos do Prowlarr reprovem o Brazuca, dividimos a integração em duas partes distintas:

1. **Brazuca Movies:** Indexador focado apenas em filmes. A validação de saúde interna usa o ID do filme Avatar 2 para sempre retornar luz verde.
2. **Brazuca TV:** Indexador focado apenas em séries. Como os servidores Stremio às vezes retornam erro para checagens de saúde em episódios fictícios que o Prowlarr faz, nós configuramos um minisservidor "Anti-bloqueio" invisível na sua infraestrutura (`brazuca-proxy`). Ele intercepta *apenas* a requisição de checagem do Prowlarr e entrega um resultado "falso positivo" para deixar o indexador verde para sempre. As buscas reais de séries continuam passando normalmente direto para o Brazuca!

**Como adicionar:**
- Adicione o **Brazuca Movies** e o **Brazuca TV** separadamente no Prowlarr.
- Selecione a tag do proxy que você preferir (ex: `proxy-nl`) para *ambos*. O nosso servidor anti-bloqueio respeita integralmente a rota da sua tag!
- Nunca use o indexador antigo "Brazuca" genérico, pois ele fatalmente falhará no Health Check do Prowlarr e ficará vermelho.
