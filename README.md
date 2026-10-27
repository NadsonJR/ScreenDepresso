# ScreenDepresso

MVP de captura e anotação de imagens para **Ubuntu/GNOME em X11**, em Python e PySide6.

## Instalar e executar

Requer Python 3.10+ e uma sessão gráfica X11. No Ubuntu, instale os componentes de sistema, se necessário:

```bash
sudo apt install python3-venv libegl1 libgl1 libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxcb-xinerama0
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/screendepresso
```

Com `uv`, use `uv sync --frozen --extra dev` e `uv run screendepresso`.

## Uso

- Tela inteira: botão ou **Ctrl+Shift+1**.
- Janela: botão ou **Ctrl+Shift+2**, depois escolha a janela na lista.
- Região: botão ou **Ctrl+Shift+3**, arraste a seleção; **Esc** cancela.
- Editor: escolha a ferramenta e arraste na imagem. Texto pede o conteúdo ao clicar. Use Desfazer para reverter operações.
- Copiar envia a versão editada para a área de transferência. Mantenha o aplicativo aberto para servir os dados da área de transferência no X11.
- Salvar exporta PNG/JPEG e adiciona a versão editada ao histórico.
- Capturas originais são persistidas automaticamente em `$XDG_DATA_HOME/screendepresso`, ou `~/.local/share/screendepresso`. Clique no histórico para abrir uma imagem; alterações ainda não salvas são descartadas ao trocar de imagem.

## Limitações atuais

Captura de janela copia sua área visível da tela, sem a decoração. Janelas sobrepostas aparecem na captura; mantenha a janela escolhida visível. A versão inicial não captura conteúdo oculto ou minimizado. Atalhos em conflito são informados na barra de status. O ícone de bandeja depende do suporte do GNOME (extensão AppIndicator); a janela e os atalhos não dependem dele. Ao fechar a janela, escolha minimizar em segundo plano, encerrar ou cancelar.

O histórico é local e sem expiração automática; pode conter dados sensíveis. Desfoque é um efeito visual, não uma garantia de remoção de informação sensível. Wayland não é suportado nesta versão. Escala mista entre monitores ainda precisa de validação em hardware real.

## Testes

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Esses testes verificam anotações, recorte, desfoque, desfazer e persistência do histórico. Captura real, atalhos e área de transferência precisam também de teste manual em GNOME/X11: abra outra janela, teste as três capturas, edite, copie para outro aplicativo, exporte e reabra a imagem.

## Instalador e atualizações (v0.4.2)

O pacote `.deb` é destinado a **Ubuntu 24.04+ x86_64, em X11**. Inclui o runtime Python e bibliotecas Python: não é necessário instalar ferramentas de desenvolvimento ou compilar a aplicação.

As versões publicadas ficam em [Releases](https://github.com/NadsonJR/ScreenDepresso/releases). Depois de baixar o pacote:

```bash
sudo apt install ./screendepresso_0.4.2_amd64.deb
```

Abra **ScreenDepresso** no menu de aplicativos. Para atualizar, use **Updates… → Check for updates → Download and install**. A consulta e o download ocorrem em segundo plano; o pacote é verificado pelo tamanho e SHA-256 do manifesto da release e instalado pelo `apt`, com autorização via Polkit. Salve suas edições, feche e reabra o aplicativo após atualizar. O histórico permanece no diretório de dados do usuário. Cancelar a autorização não instala a nova versão.

O atualizador consulta releases estáveis e rejeita versões iguais ou anteriores. Requer HTTPS e acesso ao GitHub. O SHA-256 verifica integridade em relação ao manifesto servido pelo GitHub; não é uma assinatura independente do publicador. Nenhuma credencial é incluída no instalador.

O workflow também executa o build automaticamente em pushes relevantes na `main`, além da execução manual. Nessas execuções, o instalador fica disponível nos artefatos do GitHub Actions; a publicação pública continua restrita às tags de versão.

### Publicar uma nova versão (mantenedores)

1. Atualize `__version__` em `screendepresso/__init__.py` e execute `uv lock`.
2. Faça commit e push das mudanças.
3. Crie e envie uma tag correspondente, por exemplo `git tag v0.4.2` e `git push origin v0.4.2`.
4. O workflow **Build Linux installer** executa os testes, constrói o `.deb` no Ubuntu 24.04, instala e testa o executável empacotado, e publica a release com `.deb`, `SHA256SUMS` e `update.json`. A publicação só ocorre após os checks passarem.

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
- **Desfoque** preserva a região selecionada e desfoca o restante da imagem. Ajuste a intensidade de **1 a 100** no campo abaixo das ferramentas; com um efeito de desfoque selecionado, o ajuste modifica esse efeito e pode ser desfeito.
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
