# ScreenDepresso

Aplicativo de captura e anotação de imagens para **Windows 10/11 x64** e **Ubuntu/GNOME em X11**, em Python e PySide6.

## Instalar e executar

Requer Python 3.11+ e uma sessão gráfica X11. No Ubuntu, instale os componentes de sistema, se necessário:

```bash
sudo apt install python3-venv libegl1 libgl1 libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxcb-xinerama0
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/screendepresso
```

Com `uv`, use `uv sync --frozen --extra dev` e `uv run screendepresso`.

## Uso

- Tela inteira: botão ou **Ctrl+Shift+1** captura todos os monitores. O menu do botão permite escolher apenas um monitor.
- Janela: botão ou **Ctrl+Shift+2**, depois escolha uma janela na grade de miniaturas.
- Região: botão ou **Ctrl+Shift+3**, arraste a seleção; **Esc** cancela.
- Editor: escolha a ferramenta e arraste na imagem. Texto pede o conteúdo ao clicar. Use Desfazer para reverter operações.
- Copiar envia a versão editada para a área de transferência. Mantenha o aplicativo aberto para servir os dados da área de transferência no X11.
- Salvar exporta PNG/JPEG e adiciona a versão editada ao histórico.
- Capturas originais são persistidas automaticamente em `$XDG_DATA_HOME/screendepresso`, ou `~/.local/share/screendepresso`. Cada captura abre em uma aba própria. Clique duas vezes em uma miniatura do workspace para abrir uma imagem em outra aba ou voltar à aba existente, preservando as edições.

## Limitações atuais

Captura de janela copia sua área visível da tela. Após a escolha por miniatura, o aplicativo tenta trazê-la para a frente. Janelas sempre acima e conteúdo protegido ainda podem aparecer ou impedir a captura. No X11, a captura usa a área do cliente, sem a decoração do gerenciador de janelas. A versão inicial não captura conteúdo oculto ou minimizado. Atalhos em conflito são informados na barra de status. O ícone de bandeja depende do suporte do GNOME (extensão AppIndicator); a janela e os atalhos não dependem dele. Ao fechar a janela, escolha minimizar em segundo plano, encerrar ou cancelar.

O workspace é local e pode conter dados sensíveis. O limite padrão é de 25 imagens; imagens mais antigas são movidas para a lixeira ao salvar novas imagens ou aplicar outro limite nas configurações. Desfoque é um efeito visual, não uma garantia de remoção de informação sensível. Wayland não é suportado nesta versão. Escala mista entre monitores ainda precisa de validação em hardware real.

## Testes

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Esses testes verificam anotações, recorte, desfoque, desfazer e persistência do histórico. Captura real, atalhos e área de transferência precisam também de teste manual em GNOME/X11: abra outra janela, teste as três capturas, edite, copie para outro aplicativo, exporte e reabra a imagem.

## Instalador e atualizações (v0.7.2)

O pacote `.deb` é destinado a **Ubuntu 24.04+ x86_64, em X11**. Inclui o runtime Python e bibliotecas Python: não é necessário instalar ferramentas de desenvolvimento ou compilar a aplicação.

As versões publicadas ficam em [Releases](https://github.com/NadsonJR/ScreenDepresso/releases). Depois de baixar o pacote:

```bash
sudo apt install ./screendepresso_0.7.2_amd64.deb
```

Abra **ScreenDepresso** no menu de aplicativos. Para atualizar, use **Settings → Updates → Check for updates → Download and install**. Todo o fluxo acontece na própria aba, com a opção de manter a versão atual. A consulta e o download ocorrem em segundo plano; o pacote é verificado pelo tamanho e SHA-256 do manifesto da release e instalado pelo `apt`, com autorização via Polkit. Salve suas edições e use **Restart application** ao concluir a atualização. O histórico permanece no diretório de dados do usuário. Cancelar a autorização não instala a nova versão.

O atualizador consulta releases estáveis e rejeita versões iguais ou anteriores. Requer HTTPS e acesso ao GitHub. O SHA-256 verifica integridade em relação ao manifesto servido pelo GitHub; não é uma assinatura independente do publicador. Nenhuma credencial é incluída no instalador.

O workflow também executa o build automaticamente em pushes relevantes na `main`, além da execução manual. Nessas execuções, o instalador fica disponível nos artefatos do GitHub Actions; a publicação pública continua restrita às tags de versão.

### Publicar uma nova versão (mantenedores)

1. Atualize `__version__` em `screendepresso/__init__.py` e execute `uv lock`.
2. Faça commit e push das mudanças.
3. Crie e envie uma tag correspondente, por exemplo `git tag v0.7.2` e `git push origin v0.7.2`.
4. O workflow **Build installers** executa os testes, constrói o `.deb` no Ubuntu 24.04, instala e testa o executável empacotado, e publica a release com `.deb`, `SHA256SUMS` e `update.json`. A publicação só ocorre após os checks passarem.

Código, instaladores e metadados de atualização ficam no próprio repositório público `NadsonJR/ScreenDepresso`.

O workflow usa o `GITHUB_TOKEN` automático do Actions com permissão `contents: write` para criar releases no mesmo repositório. Não é necessário configurar `RELEASES_TOKEN` ou criar outro repositório. A execução manual e os pushes na `main` geram artefatos de build; tags de versão publicam releases após os checks passarem. Aumente a versão a cada lançamento; não substitua pacotes de uma versão já distribuída.

### Build reproduzível com Docker (mantenedores)

```bash
docker build -f packaging/Dockerfile -t screendepresso-builder .
mkdir -p dist
docker run --rm -v "$PWD/dist:/output" screendepresso-builder sh -c 'cp /app/dist/*.deb /app/dist/update.json /app/dist/SHA256SUMS /output/'
```

O Dockerfile faz build, instala e verifica o pacote. Em redes corporativas, use os argumentos de proxy padrão do Docker e o segredo opcional `environment_ca` para adicionar a CA autorizada ao ambiente de build; mantenha verificação TLS e de assinaturas APT habilitada. O certificado do ambiente de build não é copiado para o aplicativo.

Para remover o aplicativo, use `sudo apt remove screendepresso`. O histórico do usuário é preservado.

## Edição e configurações (0.3.1)

- **Ctrl+Z** desfaz; **Ctrl+Y** refaz. Uma nova edição após desfazer descarta o caminho de refazer.
- Após inserir uma anotação, o editor entra em **Selecionar**. Arraste o objeto para mover; arraste uma das duas alças para redimensionar ou ajustar as extremidades de uma seta. **Delete** exclui o objeto selecionado. Dê duplo clique no texto para editar seu conteúdo. O recorte preserva as anotações como objetos e também pode ser desfeito.
- A seta aparece como seta durante o arraste, inclusive na horizontal ou vertical.
- **Desfoque** preserva a região selecionada e desfoca o restante da imagem. Ajuste a intensidade de **1 a 100** no menu do próprio botão. No modo padrão, todas as áreas nítidas são combinadas e a intensidade vale para a camada inteira; o modo em sequência permanece disponível no mesmo menu.
- **Configurações → Hotkeys** permite alterar os três atalhos globais, inclusive usar Print. Atalhos duplicados ou ocupados são rejeitados; os anteriores são restaurados se o novo registro falhar. As alterações entram em vigor ao salvar.
- **Configurações → Arquivos** define o diretório das novas capturas, do histórico e o destino inicial de exportação. O padrão continua sendo `$XDG_DATA_HOME/screendepresso` ou `~/.local/share/screendepresso`. Arquivos antigos não são movidos; selecione o diretório anterior para vê-los novamente no histórico.
- **Configurações → Atualizações → Verificar atualizações** inicia a consulta de versões do GitHub.

As preferências ficam em `$XDG_CONFIG_HOME/screendepresso/settings.json` ou `~/.config/screendepresso/settings.json`. Anotações permanecem editáveis enquanto a imagem está aberta no editor. PNG/JPEG e o histórico de imagens são rasterizados; reabri-los não recupera as camadas de edição. Salve antes de trocar de imagem ou encerrar o aplicativo.

Os testes de atalhos globais usam um servidor X11 virtual isolado quando `Xvfb` está instalado (`sudo apt install xvfb`). Sem ele, esse teste é explicitamente marcado como ignorado; o workflow do Actions instala o servidor para executá-lo.

## Interface e texto direto na imagem (0.3.1)

A interface usa tons escuros, barra superior de ações, ferramentas na lateral esquerda e imagem centralizada. O botão **Histórico** abre ou recolhe a lista de capturas à direita. A ferramenta ativa fica destacada; a faixa acima da imagem mostra instruções de uso.

Para inserir texto, selecione **A**, arraste a caixa na imagem e digite nela. Um clique simples também cria uma caixa com tamanho inicial. Use **Ctrl+Enter** ou clique fora para confirmar; **Esc** cancela; Enter sozinho insere uma nova linha. O duplo clique sobre um texto existente abre a edição no próprio local. Use Selecionar para mover ou redimensionar a caixa. O texto usa tamanho de fonte estável de 24 px e quebra de linha dentro da caixa.

Não há popup de texto. A imagem permanece visível durante a edição, e copiar/salvar confirma o texto pendente antes de exportar. Confirmar uma anotação conta como uma operação de desfazer/refazer; uma caixa vazia ou cancelada não altera a imagem.

### Colagem, desfoque e idiomas

- **Paste image / Ctrl+V** insere a imagem da área de transferência como uma camada sobre a imagem aberta. Ela pode ser movida, redimensionada, excluída e desfeita/refeita. Imagens grandes são ajustadas ao tamanho da tela de edição; a transparência é preservada. Sem uma imagem aberta, a colagem inicia uma nova imagem.
- O slider **Blur strength** e o campo numérico aceitam intensidades de **1 a 100**. Selecione o objeto de desfoque e ajuste o controle para modificar um efeito existente. O valor também define a intensidade do próximo efeito. A área selecionada continua nítida.
- A interface usa **English** por padrão. Em **Settings → Language**, escolha **English** ou **Português (Brasil)** e salve. Menus, ferramentas, configurações e mensagens mudam imediatamente; a preferência é mantida ao reabrir o aplicativo.

## Marcadores numerados e cores (0.4.0)

- Selecione **Numbered markers** (ícone **1**) na barra lateral. Clique para inserir o próximo número ou arraste do centro do círculo até o ponto que deseja indicar. A ferramenta continua ativa para inserir **1, 2, 3…** sem precisar selecioná-la a cada vez.
- Para ajustar um marcador existente, use **Select / move**: arraste o círculo para reposicioná-lo sem mudar o alvo; arraste a alça na ponta do indicador para apontar para outro objeto. Arrastar o segmento move o conjunto.
- **Marker color…** altera a cor de todos os marcadores da imagem e dos próximos marcadores. Os números usam contraste claro ou escuro automaticamente.
- Ao excluir um marcador, os restantes são renumerados sem lacunas. Desfazer/refazer restaura tanto a sequência quanto as mudanças de posição e cor. Uma nova imagem começa em 1.
- **Rectangle color…** altera o retângulo selecionado e define a cor dos próximos, sem mudar outros retângulos existentes. Se nenhum retângulo estiver selecionado, apenas a cor dos próximos é alterada.

Os controles também estão traduzidos em **Português (Brasil)**. Marcadores e retângulos permanecem objetos editáveis durante a sessão; copiar ou exportar inclui os números, indicadores e cores na imagem final.

### Dicas ao passar o mouse

Mantenha o cursor sobre um botão ou controle para ver o nome da função. As dicas incluem atalhos quando disponíveis, como **Save (Ctrl+S)**, **Paste image (Ctrl+V)** e **Undo (Ctrl+Z)**. Estão disponíveis nas barras superior e lateral, no menu, nos controles de cor e desfoque e nas configurações. As dicas seguem o idioma escolhido em **Settings → Language**.

## Menus de cor nas ferramentas laterais (0.4.1)

Os botões laterais de **Arrow**, **Rectangle** e **Numbered markers** têm dois controles: clique no ícone para selecionar a ferramenta; clique na pequena seta ao lado para abrir seu menu de cor. O próprio ícone exibe a cor atual.

- **Arrow color…** e **Rectangle color…** alteram o objeto selecionado do tipo correspondente e a cor dos próximos objetos desse tipo. Outros objetos existentes mantêm suas cores.
- **Marker color…** continua alterando todos os marcadores da imagem e os próximos marcadores.
- Mudar ou cancelar uma cor preserva a seleção; as alterações podem ser desfeitas e refeitas. Os menus e dicas acompanham o idioma escolhido.

A barra superior usa um disquete para **Save** e duas folhas sobrepostas para **Copy image**. A ferramenta **Select / move** usa uma mão aberta.

## Interface simplificada e segundo plano (0.4.2)

- Abra a pequena seta do botão lateral **Blur outside selection** para ajustar **Blur strength** de 1 a 100. O controle continua alterando o efeito selecionado e a intensidade dos próximos efeitos; a seta principal do botão ativa a ferramenta.
- **Crop** fica somente na barra superior. O botão X lateral foi removido; **Delete** continua excluindo o objeto selecionado.
- A barra de menus Settings / Updates / About foi removida. As configurações permanecem no botão superior **Settings**, e as atualizações também estão disponíveis na aba **Updates** das configurações. O menu do ícone da bandeja inclui Settings, Check for updates e About.
- Ao fechar pelo X da janela, o aplicativo pergunta se deseja **Minimize to tray**, **Quit** ou **Cancel**. Minimizar preserva a imagem em edição e os atalhos globais de captura. Clique no ícone da bandeja ou use **Open** no menu dele para reabrir o editor. **Quit** no menu da bandeja encerra explicitamente o aplicativo e libera os atalhos.
- No GNOME, o ícone da bandeja depende do suporte a AppIndicator (normalmente já disponível no Ubuntu). Se não houver suporte, a opção muda para **Minimize to taskbar** e mantém a janela minimizada, com acesso pela barra de tarefas. O aplicativo não fica oculto sem um caminho para reabri-lo.

Se o Ubuntu/GNOME não mostrar ícones de bandeja, instale a extensão de integração pelo sistema e habilite-a nas Extensões do GNOME:

```bash
sudo apt install gnome-shell-extension-appindicator
```

Não é necessário configurar inicialização automática para continuar em segundo plano após minimizar; o processo atual permanece ativo até a opção de encerrar. A visibilidade real do ícone e o comportamento do painel devem ser conferidos no GNOME; os testes cloud exercitam as escolhas de fechar, restaurar, manter os serviços e o fallback sem bandeja.

## Windows e versão no rodapé (0.5.0)

A mesma aplicação agora possui backend Windows para capturar tela inteira, janela visível ou região, atalhos globais via RegisterHotKey, edição, histórico, área de transferência, bandeja e preferências. A versão atual fica sempre no canto inferior direito, mesmo quando a barra de status mostra outra mensagem.

### Instalar no Windows

Baixe `screendepresso_0.7.2_windows_amd64_setup.exe` nas [Releases](https://github.com/NadsonJR/ScreenDepresso/releases). Execute o instalador e abra ScreenDepresso no menu Iniciar. Requer Windows 10 (build 19041 ou posterior) ou Windows 11, de 64 bits. Não é necessário instalar Python ou ferramentas de build.

A instalação é por usuário em `%LOCALAPPDATA%\Programs\ScreenDepresso`; capturas ficam por padrão em `%LOCALAPPDATA%\ScreenDepresso\captures` e as preferências em `%LOCALAPPDATA%\ScreenDepresso\settings.json`. O desinstalador preserva capturas e preferências. As variáveis XDG de testes continuam podendo sobrescrever esses diretórios.

Use **Settings → Updates** para atualizar. O atualizador seleciona o instalador Windows, verifica tamanho e SHA-256 e inicia o assistente de instalação. Salve suas edições antes de confirmar: a aplicação será encerrada para permitir substituir seus arquivos. O instalador oferece reabri-la ao terminar. O instalador baixado permanece temporariamente no diretório temporário do usuário.

Este primeiro instalador Windows não possui assinatura Authenticode. O Windows pode mostrar um aviso do SmartScreen; baixe somente os arquivos da release oficial. O SHA-256 verifica integridade em relação ao manifesto; não substitui uma assinatura do publicador.

### Desenvolvimento e publicação

No Windows, use Python 3.12 e Inno Setup 6 no computador de build:

```powershell
uv sync --frozen --extra dev --extra build
uv run python packaging/build_windows.py
```

O workflow **Build installers** executa jobs independentes em Ubuntu 24.04 e Windows Server 2022. O Windows inclui testes das APIs nativas de atalhos, captura e enumeração de janelas; o job também instala silenciosamente o `.exe` gerado e executa o smoke test do aplicativo instalado. A publicação da tag depende do sucesso de ambos os jobs e valida os checksums antes de juntar os metadados em `update.json`.

Revisão manual recomendada no Windows real: capturar três modos, trocar atalhos, copiar/colar em outro aplicativo, minimizar/restaurar pela bandeja e atualizar pelo instalador. Capturas de janelas continuam incluindo o que está visível na tela; janelas minimizadas não são oferecidas. Monitores com escalas diferentes e janelas entre monitores exigem validação no hardware correspondente; a composição usa coordenadas lógicas do desktop Qt.

## Instância única (0.5.1)

O aplicativo permite apenas uma instância por perfil de usuário, tanto no Windows quanto no Linux. Ao abri-lo novamente pelo atalho ou instalador, a segunda abertura solicita que a primeira restaure o editor e termina sem criar outra janela ou registrar atalhos novamente. A imagem em edição é preservada, inclusive quando o aplicativo estava minimizado na bandeja.

A proteção usa uma trava no diretório das preferências e um canal local de ativação restrito ao usuário. A trava não expira enquanto o processo permanece vivo, mesmo após muito tempo minimizado. Encerrar libera a trava; depois de uma queda ou encerramento forçado, a próxima abertura recupera a trava e o canal abandonados automaticamente. Não é necessário excluir arquivos manualmente.

Se a primeira instância ainda estiver iniciando, a ativação será entregue quando ela estiver pronta. Se estiver em execução mas seu canal de ativação não responder, a segunda abertura apenas informa que o aplicativo já está aberto; ela não inicia uma instância adicional. O comando `--version` continua disponível sem abrir o editor.

## Abas de capturas (0.6.0)

Cada print fica em uma aba, sem substituir a captura anterior. Alterne entre elas clicando no título ou usando **Ctrl+Tab** / **Ctrl+Shift+Tab**. Arraste as abas para reordenar.

Cada aba mantém seus objetos editáveis, seleção, intensidade de desfoque, cores, posição de rolagem e histórico de desfazer/refazer. Salvar, copiar, colar e os atalhos de edição atuam somente na aba ativa. Abrir uma captura já aberta pelo histórico seleciona a aba existente.

Um **asterisco** no título indica alterações não salvas. Use o botão de fechar na aba ou **Ctrl+W**; se houver alterações, escolha salvar, descartar ou cancelar. Quando não há imagens abertas, a barra de abas fica oculta, pronta para a próxima captura. Fechar uma aba não exclui imagens do histórico. As abas ficam na memória durante a sessão; ao encerrar o aplicativo, salve as edições que deseja manter.

## Balões, texto e zoom (0.6.1)

- **Speech balloon**: arraste na imagem para desenhar um balão. A seta do próprio botão lateral abre os modelos **Speech**, **Rounded**, **Thought** e **Shout**, além das cores de preenchimento e contorno. Selecione o balão para alterar seu modelo ou cores; use os controles nos cantos para redimensionar e o controle da ponta para indicar outro objeto.
- **Text**: a seta do botão lateral permite escolher fonte, tamanho de **6 a 200 px** e cor. Os controles também alteram um texto selecionado. Arraste uma caixa e digite; **Ctrl+Enter** confirma, **Esc** cancela e um clique duplo permite editar novamente. A caixa cresce conforme o conteúdo; textos que excedem a imagem ampliam a tela com transparência, preservando todas as linhas e o tamanho escolhido. Essa expansão pode ser desfeita.
- **Zoom**: use o slider no canto inferior esquerdo para visualizar de **10% a 400%**. O zoom fica salvo por aba durante a sessão e não modifica a resolução das imagens copiadas ou exportadas. Desenho, seleção, recorte e texto usam as coordenadas originais mesmo com zoom.

Menus, dicas e controles estão disponíveis em inglês e português BR.

## Scroll, setas, camada de desfoque e atualizações (0.6.2)

- O **scroll do mouse** amplia/reduz a captura em passos de 10%, entre 10% e 400%, mantendo o ponto sob o cursor. Use **Shift+scroll** para rolar a imagem. O slider acompanha o valor e o zoom continua independente por aba.
- A seta do botão **Arrow** abre os modelos **Classic arrow**, **Filled arrow**, **Double arrow**, **Dashed arrow** e **Line**, além do seletor de cor. Selecionar um objeto existente permite mudar seu modelo e cor sem redesenhar.
- **Shared blur layer** é o padrão: a imagem é desfocada uma única vez, preservando a união de todas as áreas selecionadas; anotações ficam por cima e a intensidade vale para toda a camada. Para restaurar o comportamento anterior, escolha **Sequential blur (legacy)** no menu do desfoque. Esse modo aplica cada efeito em sequência, com intensidades individuais. A escolha é independente por aba, não exclui os objetos e pode ser desfeita. Os dois renderizadores ficam separados em `screendepresso/blur.py`.
- **Settings → Updates → Check for updates** consulta automaticamente ao abrir o popup, sem botão de consulta dentro dele. Se houver nova versão, aparece **Download and install**; durante o download, uma barra mostra o progresso em bytes. Tamanho, origem e SHA-256 continuam sendo verificados.
- Ao concluir, **Restart application** permite escolher quando reiniciar. No Ubuntu, o pacote é instalado mediante autorização do sistema antes de oferecer o reinício. No Windows, o download verificado fica pronto e o botão inicia a instalação e reabre o aplicativo. Salve as edições antes de reiniciar. A proteção de instância única aguarda o encerramento do processo anterior.

## Retângulos e modelos de marcadores (0.6.3)

Abra o menu do botão **Rectangle** para escolher a cor, a **Border thickness** (1–40 px), ativar **Rounded corners** e ajustar o **Corner radius** (1–100 px). Desative a opção para desenhar cantos retos. Em retângulos pequenos, espessura e raio são limitados pelo tamanho da forma para evitar bordas cortadas. Os controles modificam o retângulo selecionado e definem o padrão dos próximos desenhos na mesma aba.

O menu de **Numbered markers** oferece seis modelos: **Classic circle**, **Flat circle**, **Square marker**, **Diamond marker**, **Outlined circle** e **Hexagon marker**. É possível misturar modelos na mesma imagem, mantendo uma única sequência de números. Escolher um modelo altera o marcador selecionado e o padrão dos próximos; a cor continua sendo comum a todos os marcadores da imagem. Centro, linha e ponta mantêm os controles de movimento existentes.

Todas as opções aparecem na prévia durante o desenho, funcionam com zoom e podem ser desfeitas/refeitas. Os menus acompanham o idioma escolhido nas configurações.

## Vários monitores, miniaturas e seleção de região (0.6.4)

**Full screen** e o atalho global capturam a área completa dos monitores, respeitando suas posições, inclusive telas à esquerda ou acima da principal. Abra a seta do botão para escolher **All monitors** ou um monitor específico, identificado pelo nome e pela resolução. O menu é atualizado quando aberto; monitores desconectados são informados, sem retornar uma captura parcial silenciosamente.

Com escalas diferentes, a composição usa a maior densidade de pixels entre os monitores selecionados. Os demais são ajustados a essa escala comum para preservar o alinhamento com a seleção de região; espaços sem monitor ficam transparentes. Capturar um único monitor mantém sua resolução nativa. A validação automatizada cobre posições negativas, telas empilhadas, espaços entre telas e escala fracionária; ainda é recomendável conferir configurações físicas de escala mista no hardware de uso.

**Window** abre uma grade de miniaturas. Clique duas vezes ou escolha uma prévia e confirme em **Capture selected window**. As miniaturas usam a captura nativa da janela quando disponível, com fallback para a área visível do desktop. Janelas minimizadas não entram na seleção. A janela escolhida é ativada e sua posição é consultada novamente antes de capturar. Cancelar restaura o editor e preserva todas as abas.

**Region** abre uma sobreposição independente em cada monitor, usando a geometria completa em vez da área de trabalho reduzida pelas barras do sistema. No X11, a sobreposição ignora o reposicionamento do gerenciador de janelas, evitando que o GNOME desloque a imagem para cima do dock. A seleção pode atravessar monitores; **Esc** cancela e libera o mouse e o teclado.

## Atualizações dentro das configurações (0.6.5)

Abra **Settings → Updates** e clique em **Check for updates**. Um indicador de carregamento ocupa o lugar do botão durante a consulta. Se não houver atualização, o botão volta e a mensagem informa que a versão instalada já é a mais recente.

Quando uma versão nova é encontrada, o painel mostra o número e o tamanho do pacote, com **Download and install** ou **Keep current version**. Manter a versão atual encerra a oferta e permite verificar novamente depois. Baixar e instalar inicia o download imediatamente, sem confirmação adicional.

Progresso, erros, instalação e **Restart application** aparecem na mesma aba. Salve suas edições antes de reiniciar; o aviso fica no próprio painel. O Ubuntu continua solicitando autorização do sistema para instalar o pacote, e o instalador Windows continua sendo iniciado no momento do reinício. As validações de origem, tamanho e SHA-256 e a proteção de instância única foram preservadas.

As configurações podem ser fechadas durante a operação. Ao reabrir a aba, o painel mantém o progresso ou o estado de pronto para reiniciar. O comando de atualização na bandeja abre essa mesma aba, sem uma segunda janela de atualização. As opções gerais de salvar/cancelar configurações são substituídas por **Close** enquanto a aba Updates estiver selecionada.

## Workspace e idiomas (0.6.6)

O painel **Workspace** substitui o histórico e mostra miniaturas das imagens no diretório configurado. Um clique seleciona a imagem para as ações; um clique duplo abre ou restaura sua aba. **Duplicate** (**Ctrl+D**) cria uma cópia independente no mesmo diretório; **Delete** move a imagem selecionada para a lixeira do sistema. Abas abertas preservam seus pixels e edições mesmo quando o arquivo original sai do workspace.

Arraste uma miniatura para a imagem em edição para adicioná-la como uma camada que pode ser movida, redimensionada e desfeita/refeita. O arraste copia a imagem, preservando o arquivo de origem. Também funciona com zoom e sobre a área vazia do editor. Miniaturas são carregadas em pequenos lotes; mudanças no diretório são observadas automaticamente e **Refresh** permite atualizar manualmente.

Em **Settings → Files**, escolha **25** (padrão), **50**, **75**, **100** ou **No limit**. O limite conta imagens PNG, JPEG, WebP, BMP, GIF e TIFF no próprio diretório, incluindo cópias e imagens externas com esses formatos. Ao salvar/duplicar uma imagem ou aplicar um novo limite/diretório, as mais antigas são movidas para a lixeira, mantendo o limite escolhido. A data de modificação define a ordem. Subpastas, arquivos de outros tipos e links simbólicos não são removidos automaticamente.

Diretórios existentes não são reduzidos apenas ao iniciar ou atualizar o aplicativo: se já excederem o limite, o painel informa que ele será aplicado no próximo salvamento. Para preservar todos os arquivos no diretório, selecione **No limit** antes de salvar novas imagens. Se a lixeira estiver indisponível, os arquivos são preservados e o painel informa que não foi possível aplicar o limite. Não há fallback para exclusão permanente.

A interface inclui traduções revisadas em inglês e português BR, com o catálogo brasileiro do Qt incluído nos instaladores para diálogos de arquivos e menus de contexto. Trocar o idioma atualiza os controles, status e placeholders sem traduzir nomes de arquivos, fontes nem o conteúdo escrito nas imagens. Quantidades decimais usam o formato do idioma selecionado. Mensagens externas do sistema operacional continuam sujeitas ao idioma do sistema.

## Menus de contexto e notas de atualização (0.6.7)

Clique com o botão direito em uma aba para **Close all tabs**, **Close this tab** ou **Close other tabs**. A ação usa a aba clicada, mesmo quando outra está ativa. Abas com edições não salvas mantêm as opções de salvar, descartar ou cancelar. Cancelar interrompe o fechamento das abas restantes; abas já fechadas continuam fechadas. Fechar todas retorna ao editor vazio, sem abas visíveis, preservando os arquivos no Workspace.

No **Workspace**, clique com o botão direito na miniatura para **Duplicate** ou **Delete**. Os três botões superiores foram substituídos por um ícone de atualização no canto superior direito. **Ctrl+D**, **Delete**, atualização automática e arraste para o editor continuam disponíveis. Excluir ainda move para a lixeira do sistema.

Em **Settings → Updates**, clique em **Release notes** para expandir as notas da versão instalada na própria aba. As notas acompanham o aplicativo, funcionam offline e seguem o idioma escolhido. Uma versão nova disponível não substitui essas notas pelas da versão ainda não instalada.

## Desenho contínuo e macOS (0.7.0)

Seta, retângulo, texto, balão e desfoque permanecem ativos após criar um objeto. Continue clicando/arrastando para adicionar outros, inclusive sobre objetos anteriores. Para mover, redimensionar ou reeditar texto com duplo clique, escolha **Select / move**. Texto é confirmado com Ctrl+Enter (Command+Enter no Mac), clique fora ou troca de ferramenta; Esc cancela apenas o texto atual. Desfazer/refazer preserva a ferramenta ativa. O comportamento dos marcadores numerados foi mantido.

Em **Settings → Updates**, a versão instalada fica centralizada e os botões ficam na mesma linha, incluindo **Release notes**.

### macOS 15 ou posterior

Há instaladores DMG separados para **Apple Silicon (arm64)** e **Intel (amd64)** nas Releases. Baixe o pacote correspondente ao seu Mac, abra o DMG e arraste **ScreenDepresso.app** para **Applications/Aplicativos**. Não é necessário Python, pip, X11 ou compilar. O workflow usa runners macOS nativos em ambas as arquiteturas para executar os testes, montar os DMGs, copiar o app e verificar a abertura do pacote instalado.

Esta primeira versão usa assinatura ad hoc e **não é notarizada pela Apple**. O Gatekeeper pode exigir **Ajustes do Sistema → Privacidade e Segurança → Abrir Mesmo Assim** na primeira abertura. Distribuição assinada/notarizada exige certificado Developer ID e credenciais de notarização do proprietário. Nenhuma credencial Apple foi incluída no código.

Na primeira captura, permita o ScreenDepresso em **Ajustes do Sistema → Privacidade e Segurança → Gravação de Tela e Áudio do Sistema** (o nome pode variar conforme a versão/idioma do macOS) e reabra o app. Capturas não gravam áudio. Sem a permissão, o app mostra instruções, preservando a edição atual. Captura de tela inteira/região usa o desktop do Qt, inclusive Retina e múltiplos monitores; captura de janela usa o utilitário nativo `screencapture`, com miniaturas via Quartz. Conteúdo protegido pelo macOS pode não ser capturado.

Os atalhos globais usam Carbon, sem Xlib e sem monitorar todas as teclas. O padrão é **Command+Shift+1/2/3**, seguindo a convenção do Qt: `Ctrl` no formato de configuração corresponde a Command no Mac e `Meta` a Control. Teclas ausentes no Mac, como Print e F21–F35, são recusadas ao configurar. O ícone da bandeja fica na barra de menus. Configurações e capturas ficam em `~/Library/Application Support/ScreenDepresso`, respeitando diretórios personalizados.

O atualizador escolhe o DMG da arquitetura em execução e verifica origem, tamanho e SHA-256. Ao terminar, **Open installer** abre o DMG. Salve suas edições, encerre o app, substitua-o em Aplicativos e abra a nova versão. A substituição pelo Finder é manual nesta primeira versão; as configurações e o workspace são preservados.

Os testes automatizados do macOS não concedem permissão de gravação de tela: a validação real de capturas, atalhos físicos, múltiplos monitores e permissões deve ser feita numa sessão de usuário no Mac.

## Identidade visual (0.7.1)

A 0.7.1 aplica o guia de identidade visual: paleta escura, fonte de interface do sistema, ícones desenhados com traços consistentes, barra superior agrupada, ferramentas com rótulos, propriedades contextuais e rodapé legível. Botões e inputs têm foco visível. Os estados ativos usam uma variação mais escura do azul para manter contraste AA nos rótulos. O desenho dos controles nativos da janela é preservado em cada plataforma.

A barra contextual expõe apenas propriedades já suportadas pelas ferramentas atuais: cores e estilos de setas, espessura/cantos de retângulos, fonte/tamanho/cor do texto, modelos e cores de balões/marcadores e intensidade/modo do desfoque. Os menus dos próprios botões continuam disponíveis. Os exemplos de novas ferramentas e propriedades citados no mockup não adicionam novas operações ao mecanismo de edição nesta versão.

Sem imagem, o editor oferece **Capture screen**, **Open image** e **Paste image**, além de aceitar arraste. Abrir uma imagem não a move nem a duplica no Workspace. Em janelas compactas, as barras usam ícones com tooltips e o overflow nativo do Qt; a barra contextual admite rolagem horizontal. A interface respeita escalonamento HiDPI/Retina e usa símbolos nativos de atalhos no macOS.

### Versão substituída

Os instaladores da 0.7.0 foram substituídos pela [0.7.1](https://github.com/NadsonJR/ScreenDepresso/releases/tag/v0.7.1), conforme solicitado. A página da 0.7.0 agora informa a substituição; sua tag de código foi preservada no histórico, sem renomear binários de outra versão.

## Desfoque em imagens grandes (0.7.2)

O editor reutiliza a camada de desfoque enquanto você desenha, move ou redimensiona áreas nítidas. A tela pinta a área visível diretamente, evitando criar uma imagem completa a cada movimento. O cálculo de resolução completa é feito em segundo plano, com apenas um trabalhador e cancelamento de solicitações que ainda não iniciaram quando surge uma mais recente.

Enquanto o cálculo termina, uma prévia temporária de até 262 mil pixels mantém a edição disponível; as áreas nítidas e anotações continuam sendo desenhadas na resolução original. O rodapé mostra **Preparing full-resolution blur…**. A prévia temporária é substituída automaticamente pela camada exata. Não há novo popup ou ajuste obrigatório.

**Copiar e salvar sempre usam a resolução completa e o mesmo filtro Gaussiano anterior.** Se acionados antes do cálculo terminar, aguardam a camada completa; a prévia reduzida nunca é exportada. Copiar/salvar também evitam renderizar a mesma imagem várias vezes por operação.

O cache é compartilhado entre abas, com orçamento de 256 MiB; uma camada individual maior pode ocupar o cache sozinha. Assim ele não cresce a cada região ou valor de intensidade. Mudanças na imagem, recorte, intensidade e desfazer/refazer invalidam ou reutilizam a camada correta. O modo **Sequential blur (legacy)** mantém sua ordem original de composição e reutiliza o prefixo anterior à última camada; sequências longas ainda podem precisar de cálculos adicionais ao alterar objetos anteriores.

Veja [a investigação e os benchmarks reproduzíveis](docs/BLUR_PERFORMANCE.md). Os valores medem o renderizador em memória num ambiente Linux, não o FPS completo do aplicativo nem gravação de arquivos. Builds e testes funcionais também são executados no Windows e nas duas arquiteturas macOS.
