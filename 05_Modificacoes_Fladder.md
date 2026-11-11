# Documentação de Modificações Personalizadas (Fladder)

Este documento detalha as alterações feitas no código fonte original do Fladder para atender a necessidades e integrações específicas.

---

## 1. Anel de Carregamento de Download (Integração com Transmission)

**Objetivo:** 
Exibir um anel de progresso percentual (% e ícone de loading) sobre os pôsteres no Dashboard do Seerr quando uma mídia correspondente estiver sendo baixada no Transmission.

**Lógica Utilizada:**
O aplicativo faz *polling* periódico a uma API personalizada do Transmission (hospedada em `yourdomain.duckdns.org/transmission-api`). 
Para descobrir se um filme da dashboard é o mesmo que está baixando, utilizamos um algoritmo de **Normalização de Strings**.
1. O título do TMDB (Jellyseerr) e o nome do arquivo do Torrent sofrem uma limpeza.
2. Acentos são removidos, letras são convertidas para minúsculas e pontuações/caracteres especiais são ignorados.
3. Comparamos se a string normalizada do título está contida no nome normalizado do torrent. 
4. Caso haja correspondência, o anel de loading e o status ("Baixando...", "Concluído", etc.) é renderizado por cima da imagem.
*Nota: Devido a bugs de layout onde a tela era pequena, o texto foi encapsulado em um widget `Flexible` para evitar o erro "right overflowed by 44 pixels".*

**Principais Arquivos Modificados:**
- `lib/screens/seerr/widgets/download_status_label.dart`: Contém toda a lógica de fetch da API do transmission e o tratamento visual do anel e percentual de progresso.
- `lib/screens/seerr/widgets/seerr_dashboard_poster.dart`: Modificado para injetar o `DownloadStatusLabel` na pilha (`Stack`) acima da imagem do pôster.

---

## 2. Filtro de Mídias Não Lançadas (Ocultar Lançamentos de Cinema)

**Objetivo:**
Esconder da tela de Descobertas (Trending, Popular) do Jellyseerr todos os filmes que ainda estão exclusivamente nos cinemas ou séries que ainda não foram ao ar, uma vez que eles não estão disponíveis para download via torrent.

**Lógica Utilizada:**
Após investigações, confirmou-se que embora a API do TMDB suporte o filtro `with_release_type` para encontrar lançamentos puramente digitais, o backend do Jellyseerr bloqueia parâmetros de URL não documentados.
Como solução de contorno eficaz, utilizamos uma **Heurística de Atraso em Dias**:
1. Criamos variáveis persistentes de estado (`seerrHideUnreleased` e `seerrDigitalReleaseDelay`) gerenciadas via Riverpod/SharedPreferences.
2. Quando a configuração está ativa, o aplicativo injeta uma restrição de data nas chamadas da API do Jellyseerr.
3. Para **Filmes**: Usa-se o parâmetro `primaryReleaseDateLte` calculado como `Data de Hoje - X Dias de Atraso` (Padrão: 45 dias). Isso faz a janela de cinema ser efetivamente "pulada".
4. Para **Séries**: Usa-se o parâmetro `firstAirDateLte` como a `Data de Hoje`, impedindo séries futuras de aparecerem.
5. As abas inerentes de conteúdos futuros ("Expected Movies" e "Expected Series") são ocultadas completamente da interface de Dashboard para poupar dados e limpar a UI.

**Principais Arquivos Modificados:**
- `lib/models/settings/client_settings_model.dart`: Adição das propriedades `seerrHideUnreleased` e `seerrDigitalReleaseDelay` (e regeração do `.freezed` via `build_runner`).
- `lib/screens/settings/client_sections/client_settings_dashboard.dart`: Inclusão do botão Toggle e do Slider numérico (0 a 90) para o usuário controlar a funcionalidade.
- `lib/providers/seerr_service_provider.dart`: Modificação dos métodos genéricos `discoverMovies` e `discoverTv`, bem como `discoverPopularMovies` e `discoverTrending` para injetar matematicamente as variáveis de data limite na API.
- `lib/providers/seerr_dashboard_provider.dart`: Condição para impedir o processamento das listas de "Expected" caso a configuração esteja habilitada.

---

## 3. Quick Request de Filmes (Serviço Padrão)

**Objetivo:**
Agilizar o processo de solicitação de filmes, permitindo pular a janela de configurações manuais (onde se escolhe o Servidor, Perfil de Qualidade e Pasta Raiz). Ideal para facilitar o uso por contas infantis ou automatizar opções comuns para usuários que sempre baixam na mesma configuração.

**Lógica Utilizada:**
Adicionamos campos específicos no `SeerrCredentialsModel` salvo no banco de dados local daquele usuário (Riverpod/SharedPreferences) para memorizar um ID de Servidor Radarr, Perfil e Diretório escolhido como padrão. 
Na interface de detalhes e do card de pôster, inserimos um interceptador na ação do botão **Request**. Se a flag `enableQuickRequest` estiver ligada (e o item for um filme), ele ignora a abertura do Modal (`SeerrRequestPopup`) e invoca o provedor de API injetando silenciosamente esses parâmetros pré-salvos.
Por segurança, a chave mestra para habilitar isso na tela de Configurações só é renderizada se a conta logada atender a **ambos os requisitos de proteção**: ter permissão administrativa (Admin ou AutoApproveMovie) e possuir "Cota de Filmes Ilimitada" (Sem limites numéricos).

**Principais Arquivos Modificados:**
- `lib/models/seerr_credentials_model.dart`: Inclusão das propriedades `enableQuickRequest`, `defaultRadarrServerId`, `defaultRadarrProfileId`, `defaultRadarrRootFolder`.
- `lib/screens/settings/widgets/seerr_quick_request_dialog.dart`: Nova tela (Dialog) criada para fornecer os dropdowns de seleção das pastas e perfis vindos da API do Radarr/Jellyseerr.
- `lib/screens/settings/profile_settings_page.dart`: Modificada para renderizar condicionalmente o botão que abre esse Dialog com base nos limites e permissões da classe `SeerrUserModel`.
- `lib/providers/seerr/seerr_request_provider.dart`: Novo método `submitQuickMovieRequest` que abstrai e pula toda a validação de UI, realizando o post REST diretamente.
- `lib/screens/seerr/widgets/seerr_poster_card.dart` e `lib/screens/seerr/seerr_details_screen.dart`: Interceptação do botão "Request" original.

---

## 4. Filtro Parental (Kids Mode)

**Objetivo:**
Adicionar uma camada de segurança por conta de usuário, onde contas de crianças fiquem completamente blindadas e isoladas de conteúdos adultos, exibindo apenas Animações e Filmes/Séries familiares (estilo Disney, Dreamworks).

**Lógica Utilizada:**
Como a API de Busca (Search) do Jellyseerr não recebe e nem retorna faixa etária (Livre, 12 anos, etc.), uma filtragem extra usando `genreIds` se provou a única alternativa inteligente, rápida e segura.
Criou-se uma chave booleana salva localmente por conta de usuário (no provedor principal `userProvider`).
- **Dashboard & Recomendações:** O Fladder injeta os gêneros 16 (Animação) e 10751 (Família) diretamente na API do TMDB/Jellyseerr. Toda a tela inicial é repovoada de forma nativa pela API para exibir apenas conteúdo infantil. Na seção de Tendências (Trending), que não suporta filtros de gêneros nativamente, o Fladder puxa secretamente a "Página 2" de Filmes Populares e a "Página 2" de Séries Populares, misturando-as dinamicamente para preservar a essência do "Trending" sem sobrepor os itens da página inicial.
- **Barra de Busca (Search):** O Fladder intercepta os resultados no lado do cliente. Exigimos que o filme/série contenha ao menos um gênero infantil (16, 10751 ou 10762) para poder aparecer, e destruímos da lista qualquer resultado que possua gêneros inapropriados (como 27-Terror, 80-Crime ou 53-Thriller). O bloqueio de busca acontece na velocidade da luz (memória local) sem precisar de requisições N+1.
- **Pedidos Recentes e Mídias Adicionadas:** Estas seções constroem imagens diretamente pelas IDs. O motor gerador de pôsteres (`fetchDashboardPosterFromIds`) foi blindado; caso ele detecte gêneros adultos no momento em que monta a imagem, ele aborta a renderização, ocultando completamente itens inapropriados das prateleiras de "Recentes".

**Principais Arquivos Modificados:**
- `lib/models/seerr_credentials_model.dart`: Adicionada a propriedade `enableKidsMode` vinculada ao usuário logado.
- `lib/seerr/seerr_models.dart`: O modelo `SeerrDiscoverItem` foi re-mapeado para ler e reter a lista `genreIds` que vem do TMDB (que antes era ignorada).
- `lib/screens/settings/profile_settings_page.dart`: Inclusão do "switch" visual de Liga/Desliga para configurar a conta, dentro da aba "Configurações de Perfil".
- `lib/providers/seerr_service_provider.dart`: Interceptação das quatro rotas de `Discover` (Trendings/Populares) para injetar strings de gêneros e re-codificação do método de `Search` para excluir resultados perigosos localmente.

## Solução Definitiva de Rastreio (Blackhole TMDB Tracking)

### O Problema do Blackhole
Em um setup tradicional, o Radarr/Sonarr envia o torrent via API para o cliente, recebe o Hash, e repassa esse Hash para o Jellyseerr rastrear o download pelo Fladder.
Como utilizamos uma estratégia de Blackhole (arquivos `.magnet` no Google Drive), o Radarr **não sabe o Hash**, portanto o pareamento do Fladder ficava dependente apenas do *Nome do Título*, que quebra frequentemente devido a traduções de idiomas (ex: "Marty Supreme" vs "Marty Supremo").

### A Solução
Criamos um pipeline de transporte de ID utilizando "arquivos carona" (`sidecar txt`) criados no momento do *Grab*, permitindo uma precisão de 100% no rastreio:

1. **Scripts Personalizados (Oracle VM - Radarr/Sonarr):**
   - Ao puxar um download, o Radarr/Sonarr invoca um script (`radarr_tmdb.sh` ou `sonarr_ids.sh`).
   - O script cria um arquivo `.txt` com o ID exato (TMDB ou TVDB), nomeado com o **mesmo título do release** (ex: `Nome.do.Filme.2025.tmdb.txt`).
   - Esse arquivo desce via Rclone pelo Google Drive acompanhando o `.magnet`.

2. **Worker no Celular (Termux - worker.sh):**
   - Antes de enviar o `.magnet` para o Transmission, o worker intercepta ambos os arquivos.
   - O script `worker.sh` calcula localmente o **verdadeiro InfoHash** do `.magnet` (via Python Base32) ou do `.torrent` (via `transmission-show`).
   - Ele renomeia o `.txt` associado para `<HASH>.tmdb.txt` e guarda numa pasta blindada `mappings/`.

3. **Transmission API (Termux - app.py):**
   - A API local que envia as estatísticas para fora agora lê o diretório `mappings/`.
   - Se houver um `.txt` compatível com o Hash do torrent ativo, a API injeta a propriedade `"tmdbId": "..."` diretamente no JSON de resposta.

4. **Fladder (Dart):**
   - A função `isMatchByIds` no `download_status_label.dart` lê a propriedade `tmdbId`/`tvdbId` da API e faz a correspondência garantida por ID.
   - O fallback de título `isMatchByTitle` foi refinado para higienizar pontuações e ter margem de tolerância de $\pm 1$ ano para cobrir casos residuais.

---

## 6. Fechamento do Ciclo de Volta (Importação Automática sem Retenção no Blackhole)

Além de viabilizar a telemetria visual de progresso no Fladder, o pipeline de sidecars foi expandido para resolver o gargalo de **retorno do Blackhole**:

- **O Problema:** Quando o download terminava, o `upload_gdrive.sh` subia os arquivos com o nome bruto da release ou com nomes internos do torrent. Em releases russas ou com formatações atípicas (ex: `Капитан Фантастик.720p.i. Ton.mkv` ou parênteses antes do ano), o scanner de Blackhole do Radarr/Sonarr acusava `Unknown Movie` e o download concluído ficava preso no Google Drive indefinidamente.
- **A Solução:**
  1. `radarr_tmdb.sh` e `sonarr_ids.sh` agora geram também um arquivo sidecar `.title.txt` contendo o nome canônico limpo (`Nome do Filme (Ano)` ou `Nome da Série`).
  2. O `worker.sh` arquiva esse mapeamento em `mappings/<HASH>.title.txt`.
  3. No gatilho de conclusão, o `upload_gdrive.sh` lê o hash, recupera o nome canônico e sobe o arquivo encapsulado dentro de `Downloads_Concluidos/<Titulo_Canonico_Ano>/`.
  4. O Radarr lê o nome da pasta em vez do nome do arquivo interno, identificando a mídia imediatamente e realizando a importação de forma 100% autônoma.
