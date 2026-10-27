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
