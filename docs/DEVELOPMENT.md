# Desenvolvimento e publicação

O [README](../README.md) contém o guia de instalação e uso. As mudanças por versão ficam no [CHANGELOG](../CHANGELOG.md).

## Ambiente de desenvolvimento

Requer **Python 3.11+**. As dependências incluem PySide6 6.12+, Pillow 13 e os componentes específicos de cada plataforma. O workflow usa Python 3.12; use as dependências travadas em `uv.lock` para reproduzir o ambiente.

```bash
uv sync --frozen --extra dev
uv run screendepresso
```

No Linux, use uma sessão X11. Se faltarem bibliotecas do sistema no Ubuntu, instale:

```bash
sudo apt install python3-venv libegl1 libgl1 libglib2.0-0t64 libgssapi-krb5-2 libfontconfig1 libdbus-1-3 libpulse0 libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-randr0 libxcb-xfixes0 libxcb-sync1 libxcb-xkb1 libxcb-util1
```

Como alternativa ao uv:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/screendepresso
```

No Windows, use `.venv\Scripts\python` e `.venv\Scripts\screendepresso` nos comandos equivalentes. No macOS, as dependências PyObjC são selecionadas automaticamente.

## Testes

```bash
QT_QPA_PLATFORM=offscreen uv run --frozen pytest -q
```

Em um Linux sem sessão PipeWire configurada, use o backend de áudio empregado pelo CI:

```bash
QT_QPA_PLATFORM=offscreen QT_AUDIO_BACKEND=pulseaudio uv run --frozen pytest -q
```

No PowerShell:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
uv run --frozen pytest -q
```

Os testes cobrem edição, renderização, configurações, workspace, abas, atualização e instância única. Testes nativos são executados na plataforma correspondente. Os testes de atalhos X11 usam um servidor virtual quando `Xvfb` está instalado (`sudo apt install xvfb`); sem ele, são marcados como ignorados. O Actions instala essa dependência.

O executável aceita `--version` e `--smoke-test`. Para testar, use um perfil isolado: o smoke test cria capturas e altera configurações no perfil selecionado. Exemplo para o pacote Linux instalado:

```bash
screendepresso --version
smoke_profile=$(mktemp -d)
XDG_CONFIG_HOME="$smoke_profile/config" XDG_DATA_HOME="$smoke_profile/data" screendepresso --smoke-test
```

No PowerShell, defina `XDG_CONFIG_HOME` e `XDG_DATA_HOME` para pastas temporárias antes de executar o teste. No macOS instalado, use o executável em `/Applications/ScreenDepresso.app/Contents/MacOS/ScreenDepresso`; pelo código-fonte, use `uv run --frozen screendepresso --smoke-test` com essas variáveis configuradas.

O smoke test verifica interface, edição, área de transferência e workspace. Também codifica quadros sintéticos em MP4 com MPEG-4 e decodifica o arquivo com os plugins Qt/FFmpeg incluídos. Não solicita acesso à tela nem ao microfone. Captura/áudio reais e os diálogos de consentimento devem ser validados em sessão gráfica.

Para desempenho do desfoque, veja [BLUR_PERFORMANCE.md](BLUR_PERFORMANCE.md):

```bash
uv run --frozen python packaging/benchmark_blur.py
uv run --frozen python packaging/benchmark_blur.py --mode sequential --sizes 7680x4320
```

## Gerar instaladores

Instale também as dependências de build:

```bash
uv sync --frozen --extra dev --extra build
```

| Pacote | Ambiente de build | Comando |
|---|---|---|
| Ubuntu `.deb` | Ubuntu 24.04 x86_64 | `uv run --frozen python packaging/build_deb.py` |
| Windows `.exe` | Windows x64, Inno Setup 6 | `uv run --frozen python packaging/build_windows.py` |
| macOS `.dmg` | macOS 15+, na arquitetura desejada | `uv run --frozen python packaging/build_macos.py` |

Os scripts usam PyInstaller e escrevem em `dist/`. Os pacotes incluem runtime Python, dependências, tradução do Qt e avisos de terceiros. O Windows instala por usuário; o macOS recebe assinatura ad hoc, sem notarização Apple.

### Build Ubuntu com Docker

```bash
docker build -f packaging/Dockerfile -t screendepresso-builder .
mkdir -p dist
docker run --rm -v "$PWD/dist:/output" screendepresso-builder sh -c 'cp /app/dist/*.deb /app/dist/update.json /app/dist/SHA256SUMS /output/'
```

O Dockerfile faz build, instala e verifica o pacote. Em redes corporativas, use os argumentos de proxy padrão do Docker e o segredo opcional `environment_ca` para adicionar uma CA autorizada ao ambiente de build. Mantenha a verificação TLS e de assinaturas APT habilitada. O certificado do ambiente de build não é copiado para o aplicativo.

## CI e publicação

O workflow [Build installers](../.github/workflows/release.yml) executa em PRs para `main`, pushes relevantes na `main`, tags `v*` e acionamento manual. Os jobs usam Ubuntu 24.04, Windows Server 2022, macOS Apple Silicon e macOS Intel.

Cada job executa testes, gera o instalador, instala-o e testa o executável empacotado. A publicação verifica hashes/tamanhos dos quatro pacotes e combina os manifestos em `update.json` e `SHA256SUMS`. Execuções sem tag disponibilizam artefatos no Actions; **somente tags publicam releases**.

Para publicar:

1. Atualize `__version__` em `screendepresso/__init__.py` e execute `uv lock`.
2. Registre as mudanças no início do [CHANGELOG](../CHANGELOG.md), em ordem decrescente de versão.
3. Atualize [packaging/RELEASE_NOTES.md](../packaging/RELEASE_NOTES.md) com as notas da versão a publicar e o link para o histórico completo. Esse arquivo é usado como corpo da release; não acrescente nele todo o histórico.
4. Atualize as notas offline em `screendepresso/release_notes.py`, suas traduções em `screendepresso/i18n.py` e os testes relevantes.
5. Execute os testes e envie as alterações para `main`.
6. Crie uma tag igual à versão do código e envie-a. Substitua `X.Y.Z` pelo número escolhido:

   ```bash
   git tag -a vX.Y.Z -m 'ScreenDepresso X.Y.Z'
   git push origin vX.Y.Z
   ```

7. Aguarde os quatro builds e a publicação. Confira instaladores, checksums e manifesto em [Releases](https://github.com/NadsonJR/ScreenDepresso/releases).

O workflow usa o `GITHUB_TOKEN` automático com `contents: write` apenas na publicação. Código, instaladores e metadados ficam no próprio repositório; não é necessário configurar `RELEASES_TOKEN` nem outro repositório. Aumente a versão a cada lançamento; não substitua pacotes já distribuídos.

## Validação manual

Em uma sessão de usuário de cada plataforma, confira capturas de tela/janela/região, vários monitores, atalhos globais, copiar/colar em outros apps, bandeja, gravação com pausa/microfone e atualização pelo instalador. No macOS, confira a primeira solicitação e a recusa/concessão das permissões de tela e microfone. No Windows, confira a restauração da instância existente e a atualização pelo instalador. Configurações físicas de escala mista devem ser testadas no hardware correspondente.
