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

Captura de janela copia sua área visível da tela, sem a decoração. Janelas sobrepostas aparecem na captura; mantenha a janela escolhida visível. A versão inicial não captura conteúdo oculto ou minimizado. Atalhos em conflito são informados na barra de status. O ícone de bandeja depende do suporte do GNOME (extensão AppIndicator); a janela e os atalhos não dependem dele. Fechar a janela encerra o aplicativo.

O histórico é local e sem expiração automática; pode conter dados sensíveis. Desfoque é um efeito visual, não uma garantia de remoção de informação sensível. Wayland não é suportado nesta versão. Escala mista entre monitores ainda precisa de validação em hardware real.

## Testes

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Esses testes verificam anotações, recorte, desfoque, desfazer e persistência do histórico. Captura real, atalhos e área de transferência precisam também de teste manual em GNOME/X11: abra outra janela, teste as três capturas, edite, copie para outro aplicativo, exporte e reabra a imagem.

## Instalador e atualizações (v0.2.1)

O pacote `.deb` é destinado a **Ubuntu 24.04+ x86_64, em X11**. Inclui o runtime Python e bibliotecas Python: não é necessário instalar ferramentas de desenvolvimento ou compilar a aplicação.

As versões publicadas ficam em [Releases](https://github.com/NadsonJR/ScreenDepresso/releases). Depois de baixar o pacote:

```bash
sudo apt install ./screendepresso_0.2.1_amd64.deb
```

Abra **ScreenDepresso** no menu de aplicativos. Para atualizar, use **Atualizações… → Verificar atualizações → Baixar e instalar**. A consulta e o download ocorrem em segundo plano; o pacote é verificado pelo tamanho e SHA-256 do manifesto da release e instalado pelo `apt`, com autorização via Polkit. Salve suas edições, feche e reabra o aplicativo após atualizar. O histórico permanece no diretório de dados do usuário. Cancelar a autorização não instala a nova versão.

O atualizador consulta releases estáveis e rejeita versões iguais ou anteriores. Requer HTTPS e acesso ao GitHub. O SHA-256 verifica integridade em relação ao manifesto servido pelo GitHub; não é uma assinatura independente do publicador. Nenhuma credencial é incluída no instalador.

O workflow também executa o build automaticamente em pushes relevantes na `main`, além da execução manual. Nessas execuções, o instalador fica disponível nos artefatos do GitHub Actions; a publicação pública continua restrita às tags de versão.

### Publicar uma nova versão (mantenedores)

1. Atualize `__version__` em `screendepresso/__init__.py` e execute `uv lock`.
2. Faça commit e push das mudanças.
3. Crie e envie uma tag correspondente, por exemplo `git tag v0.2.1` e `git push origin v0.2.1`.
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
