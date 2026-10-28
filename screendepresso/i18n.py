"""English is the default; preferences select English or Brazilian Portuguese."""
from pathlib import Path
import sys
from PySide6.QtCore import QTranslator, QLibraryInfo, QLocale
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget, QApplication, QLabel, QAbstractButton, QLineEdit, QPlainTextEdit, QTabWidget, QDockWidget, QToolBar, QComboBox, QStatusBar

# English source strings and their Brazilian Portuguese translations.
CATALOG = {
 'Settings…': 'Configurações…', 'Settings': 'Configurações', 'Updates…': 'Atualizações…',
 'About': 'Sobre', 'Actions': 'Ações', 'Save': 'Salvar', 'Copy image': 'Copiar imagem',
 'Paste image': 'Colar imagem', 'Undo': 'Desfazer', 'Redo': 'Refazer', 'Crop': 'Recortar',
 'Full screen': 'Tela inteira', 'Window': 'Janela', 'Region': 'Região',
 'Tools': 'Ferramentas', 'Select / move': 'Selecionar / mover', 'Arrow': 'Seta',
 'Rectangle': 'Retângulo', 'Text — drag and type': 'Texto — arraste e digite',
 'Blur outside selection': 'Desfocar fora da seleção', 'Crop selection': 'Recorte',
 'Delete object (Delete)': 'Excluir objeto (Delete)', 'Blur strength:': 'Intensidade do desfoque:',
 'Arrow • Drag on the image to draw': 'Seta • Arraste na imagem para desenhar',
 'Select • Drag to move; use handles to resize': 'Selecionar • Arraste para mover; use as alças para redimensionar',
 'Text • Drag a box and type; Ctrl+Enter confirms; Esc cancels': 'Texto • Arraste a caixa e digite; Ctrl+Enter confirma; Esc cancela',
 'Rectangle • Drag on the image to draw': 'Retângulo • Arraste na imagem para desenhar',
 'Crop • Drag the area you want to keep': 'Recorte • Arraste a região que deseja manter',
 'Blur • Drag the area you want to keep sharp': 'Desfoque • Arraste a região que deseja preservar nítida',
 'No image • Capture a screen to get started': 'Nenhuma imagem • Capture uma tela para começar',
 'Clipboard does not contain an image.': 'A área de transferência não contém uma imagem.',
 'Image copied. Keep the application open to provide clipboard data.': 'Imagem copiada. Mantenha o aplicativo aberto para disponibilizar a área de transferência.',
 'Save image': 'Salvar imagem', 'Could not save the capture.': 'Não foi possível salvar a captura.',
 'Could not save to this path or format.': 'Não foi possível salvar nesse caminho ou formato.',
 'Capture window': 'Capturar janela', 'Visible window (unobstructed):': 'Janela visível (sem obstruções):',
 'Window capture': 'Captura de janela', 'No windows available.': 'Nenhuma janela disponível.',
 'Capture unavailable. Run in an X11 session.': 'Captura indisponível. Execute numa sessão X11.',
 'Capture error': 'Erro de captura', 'Quit': 'Sair', 'Open': 'Abrir', 'Capture ': 'Capturar ',
 'Hotkeys unavailable: ': 'Atalhos indisponíveis: ',
 'This MVP requires an X11 session. Select Ubuntu on Xorg at login.': 'Este MVP requer uma sessão X11. Selecione Ubuntu on Xorg no login.',
 'Type here…': 'Digite aqui…',
 'Ctrl+Enter confirms • Esc cancels • Click outside to confirm': 'Ctrl+Enter confirma • Esc cancela • Clique fora para confirmar',
 'Hotkeys': 'Atalhos', 'Files': 'Arquivos', 'Updates': 'Atualizações',
 'Directory for new captures and exports:': 'Diretório para novas capturas e exportações:',
 'Browse…': 'Escolher…',
 'Check for updates': 'Verificar atualizações', 'Capture directory': 'Diretório das capturas',
 'Use a combination with Ctrl, Alt, Shift or Meta.': 'Use uma combinação com Ctrl, Alt, Shift ou Meta.',
 'Choose a letter, number, F1–F35, Print or a navigation key.': 'Escolha letra, número, F1–F35, Print ou uma tecla de navegação.',
 'Invalid hotkeys': 'Atalhos inválidos', 'Invalid directory': 'Diretório inválido',
 'Each capture must have a different hotkey.': 'Cada captura deve ter um atalho diferente.',
 'Enter an absolute directory path.': 'Informe um diretório absoluto.',
 'Could not stop the previous hotkeys.': 'Não foi possível encerrar os atalhos anteriores.',
 'Hotkey is in use by another application. Choose another combination.': 'Atalho ocupado por outro aplicativo. Escolha outra combinação.',
 'Duplicate hotkeys.': 'Atalhos duplicados.', 'Key unavailable on this keyboard: ': 'Tecla não disponível neste teclado: ',
 'Invalid update version.': 'Versão de atualização inválida.', 'Download destination is not allowed.': 'Destino de download não permitido.',
 'Updates are only available for Linux x86_64.': 'Atualização disponível somente para Linux x86_64.',
 'Invalid package source.': 'Origem do pacote inválida.', 'Invalid package metadata.': 'Metadados do pacote inválidos.',
 'Update manifest exceeds the size limit.': 'Manifesto de atualização excede o limite.',
 'Download is larger than the announced package.': 'Download maior que o pacote anunciado.',
 'SHA-256 verification failed. The package was discarded.': 'Falha na verificação SHA-256. O pacote foi descartado.',
 'Update ScreenDepresso': 'Atualizar ScreenDepresso', 'Installed version: ': 'Versão instalada: ',
 'Checking published versions on GitHub…': 'Consultando versões publicadas no GitHub…',
 'Install update': 'Instalar atualização', 'Download and install version ': 'Baixar e instalar a versão ',
 '?\nUbuntu will request administrator authorization. Your captures will be preserved.': '?\nO Ubuntu solicitará autorização de administrador. Suas capturas serão preservadas.',
 'Downloading and verifying the package…': 'Baixando e verificando o pacote…',
 'You are on the latest version (': 'Você está na versão mais recente (', 'New version: ': 'Nova versão: ',
 'Download and install': 'Baixar e instalar', 'Verified package saved to:\n': 'Pacote verificado salvo em:\n',
 '\nInstall it using the Ubuntu package manager.': '\nInstale pelo gerenciador de pacotes do Ubuntu.',
 'Waiting for Ubuntu authorization and installation…': 'Aguardando autorização e instalação pelo Ubuntu…',
 'Could not start the Ubuntu installer.': 'Não foi possível iniciar o instalador do Ubuntu.',
 'Update installed. Close and reopen ScreenDepresso to use the new version.\nSave your edits before closing.': 'Atualização instalada. Feche e abra o ScreenDepresso para usar a nova versão.\nSalve suas edições antes de fechar.',
 'Installation was cancelled or failed. The current version remains available.\n': 'Instalação cancelada ou malsucedida. A versão atual continua disponível.\n',
 'Could not complete the update. Check your connection and try again.': 'Não foi possível concluir a atualização. Verifique a conexão e tente novamente.',
 'Update': 'Atualização', 'Language': 'Idioma', 'Interface language:': 'Idioma da interface:',
 'Language changes apply immediately when you save.': 'A alteração de idioma é aplicada imediatamente ao salvar.',
 'Select a blur effect to change its strength.': 'Selecione um efeito de desfoque para alterar a intensidade.',
 'Cancel': 'Cancelar', 'Close': 'Fechar', 'Yes': 'Sim', 'No': 'Não',
 '&Save': '&Salvar', '&Cancel': '&Cancelar', '&Open': '&Abrir', '&Close': '&Fechar', '&Yes': '&Sim', '&No': '&Não',
 'File name:': 'Nome do arquivo:', 'Files of type:': 'Arquivos do tipo:', 'Look in:': 'Examinar:',
 'Name': 'Nome', 'Size': 'Tamanho', 'Type': 'Tipo', 'Date Modified': 'Data de modificação',
 'Show ': 'Mostrar ', 'All Files (*)': 'Todos os arquivos (*)', 'Choose': 'Escolher',
}
CATALOG.update({'Capture full screen': 'Capturar tela inteira', 'Capture window': 'Capturar janela', 'Capture region': 'Capturar região', 'Unsupported language': 'Idioma não suportado'})
CATALOG.update({
 'Blur strength (1–100)': 'Intensidade do desfoque (1–100)',
 'Click a capture to open it in the editor.': 'Clique em uma captura para abri-la no editor.',
 'Arrow color…': 'Cor da seta…',
 'Arrow color': 'Cor da seta',
 'Rectangle color…': 'Cor do retângulo…',
 'Rectangle color': 'Cor do retângulo',
 'Change the selected rectangle and the color of new rectangles.': 'Altere o retângulo selecionado e a cor dos novos retângulos.',
 'Numbered markers': 'Marcadores numerados',
 'Marker color…': 'Cor dos marcadores…',
 'Marker color': 'Cor dos marcadores',
 'Change the color of all markers in this image.': 'Altere a cor de todos os marcadores desta imagem.',
 'Numbers • Click for the next number; drag from the circle to its target': 'Números • Clique para o próximo número; arraste do círculo até o alvo',
 'Basic colors': 'Cores básicas', '&Basic colors': '&Cores básicas',
 'Custom colors': 'Cores personalizadas', '&Custom colors': 'Cores &personalizadas',
 '&Add to Custom Colors': '&Adicionar às cores personalizadas',
 '&Pick Screen Color': '&Capturar cor da tela', 'Select Color': 'Selecionar cor',
 'Hu&e:': '&Matiz:', '&Sat:': '&Saturação:', '&Val:': '&Valor:',
 '&Red:': '&Vermelho:', '&Green:': '&Verde:', 'Bl&ue:': '&Azul:',
 'A&lpha channel:': 'Canal a&lfa:', 'HTML:': 'HTML:',
})
CATALOG.update({
 'Close ScreenDepresso': 'Fechar ScreenDepresso',
 'Keep ScreenDepresso running in the background or quit?': 'Manter o ScreenDepresso em segundo plano ou encerrar?',
 'Minimizing keeps your image and capture hotkeys available. Save your edits before quitting.': 'Minimizar mantém a imagem e os atalhos de captura disponíveis. Salve suas edições antes de encerrar.',
 'The system tray is unavailable. The window will remain minimized in the taskbar.': 'A bandeja do sistema está indisponível. A janela ficará minimizada na barra de tarefas.',
 'Minimize to tray': 'Minimizar para a bandeja',
 'Minimize to taskbar': 'Minimizar para a barra de tarefas',
})
CATALOG.update({
 'Application version': 'Versão do aplicativo',
 'This key is not supported on Windows.': 'Esta tecla não é suportada no Windows.',
 'Could not register global hotkeys.': 'Não foi possível registrar os atalhos globais.',
 'Updates are only available for Windows and Linux x86_64.': 'Atualizações disponíveis somente para Windows e Linux x86_64.',
 '?\nThe app will close to install the update. Save your edits first. Your captures will be preserved.': '?\nO aplicativo será fechado para instalar a atualização. Salve suas edições antes. Suas capturas serão preservadas.',
 'Installer started. The application will now close.': 'Instalador iniciado. O aplicativo será fechado agora.',
})
CATALOG.update({
 'Could not create the application instance lock.': 'Não foi possível criar a trava de instância do aplicativo.',
 'Could not start the application activation channel.': 'Não foi possível iniciar o canal de ativação do aplicativo.',
 'ScreenDepresso is already running. Open it from the tray or taskbar.': 'O ScreenDepresso já está em execução. Abra-o pela bandeja ou pela barra de tarefas.',
})
CATALOG.update({
 'New capture': 'Nova captura',
 'Capture {number}': 'Captura {number}',
 'Switch between captures. Drag tabs to reorder.': 'Alterne entre capturas. Arraste as abas para reordenar.',
 'Close tab': 'Fechar aba',
 'Close Tab': 'Fechar aba',
 'Next tab': 'Próxima aba',
 'Previous tab': 'Aba anterior',
 'Save changes before closing this tab?': 'Salvar alterações antes de fechar esta aba?',
 'Discard': 'Descartar', '&Discard': '&Descartar',
 'Could not open this image.': 'Não foi possível abrir esta imagem.',
})
CATALOG.update({
 'Speech balloon': 'Balão de fala',
 'Speech': 'Fala oval', 'Rounded': 'Arredondado', 'Thought': 'Pensamento', 'Shout': 'Grito',
 'Balloon fill color…': 'Cor de preenchimento do balão…',
 'Balloon outline color…': 'Cor do contorno do balão…',
 'Balloon • Drag to draw; move the tail handle to point at an object': 'Balão • Arraste para desenhar; mova a ponta para apontar para um objeto',
 'Font family': 'Fonte', 'Font size': 'Tamanho da fonte', 'Text color…': 'Cor do texto…',
 'Zoom': 'Zoom', 'Zoom the active capture (10–400%)': 'Zoom da captura ativa (10–400%)',
})
CATALOG.update({
 'Classic arrow': 'Seta clássica', 'Filled arrow': 'Seta preenchida',
 'Double arrow': 'Seta dupla', 'Dashed arrow': 'Seta tracejada', 'Line': 'Linha',
 'Shared blur layer': 'Camada única de desfoque',
 'Sequential blur (legacy)': 'Desfoque em sequência (anterior)',
 'Download progress': 'Progresso do download',
 '?\nSave your edits before restarting. Your captures will be preserved.': '?\nSalve suas edições antes de reiniciar. Suas capturas serão preservadas.',
 'Download verified. Restart to install the update and reopen the application. Save your edits first.': 'Download verificado. Reinicie para instalar a atualização e reabrir o aplicativo. Salve suas edições antes.',
 'Update installed. Restart the application to use the new version. Save your edits first.': 'Atualização instalada. Reinicie o aplicativo para usar a nova versão. Salve suas edições antes.',
 'Restart application': 'Reiniciar aplicativo',
 'Restart now? Unsaved edits will be lost.': 'Reiniciar agora? Edições não salvas serão perdidas.',
 'Could not restart the application. Try again.': 'Não foi possível reiniciar o aplicativo. Tente novamente.',
})
CATALOG.update({
 'Border thickness': 'Espessura da borda',
 'Rounded corners': 'Cantos arredondados', 'Corner radius': 'Raio dos cantos',
 'Classic circle': 'Círculo clássico', 'Flat circle': 'Círculo sólido',
 'Square marker': 'Marcador quadrado', 'Diamond marker': 'Marcador em losango',
 'Outlined circle': 'Círculo com contorno', 'Hexagon marker': 'Marcador hexagonal',
 'Numbers • Click for the next number; drag from the marker to its target': 'Números • Clique para o próximo número; arraste do marcador até o alvo',
})
CATALOG.update({
 'All monitors': 'Todos os monitores',
 'Capture the complete virtual desktop.': 'Capturar toda a área de exibição dos monitores.',
 'Monitor {number}': 'Monitor {number}', 'Primary': 'Principal',
 'Choose a window preview to capture.': 'Escolha uma prévia de janela para capturar.',
 'Double-click a preview to capture that window.': 'Clique duas vezes em uma prévia para capturar a janela.',
 'Capture selected window': 'Capturar janela selecionada',
 'Could not bring the selected window to the foreground.': 'Não foi possível trazer a janela selecionada para a frente.',
 'The selected window is no longer available.': 'A janela selecionada não está mais disponível.',
 'The selected area is outside the available monitors.': 'A área selecionada está fora dos monitores disponíveis.',
 'The selected monitor is no longer available.': 'O monitor selecionado não está mais disponível.',
 'The desktop image is too large to capture.': 'A imagem da área de trabalho é grande demais para capturar.',
 'Screen capture is unavailable for monitor: ': 'Captura de tela indisponível no monitor: ',
})
CATALOG.update({
 'Keep current version': 'Manter versão atual',
 'Keeping the current version: ': 'Mantendo a versão atual: ',
 'Restarting the application…': 'Reiniciando o aplicativo…',
})
CATALOG.update({
 'Workspace': 'Workspace', 'Duplicate': 'Duplicar', 'Delete': 'Excluir', 'Refresh': 'Atualizar',
 'No limit': 'Sem limite', 'Maximum images in workspace:': 'Máximo de imagens no workspace:',
 'Invalid workspace limit.': 'Limite do workspace inválido.',
 'When saving images or applying a new limit, the oldest images are moved to the system trash. Subfolders are not changed.': 'Ao salvar imagens ou aplicar um novo limite, as imagens mais antigas são movidas para a lixeira do sistema. As subpastas não são alteradas.',
 'Existing files stay in the previous directory. Workspace shows the selected directory.': 'Os arquivos existentes permanecem no diretório anterior. O workspace mostra o diretório selecionado.',
 'This image is no longer available in the workspace.': 'Esta imagem não está mais disponível no workspace.',
 'Could not move this image to the system trash.': 'Não foi possível mover esta imagem para a lixeira do sistema.',
 'Could not read the workspace: {details}': 'Não foi possível ler o workspace: {details}',
 'Could not load the thumbnail.': 'Não foi possível carregar a miniatura.',
 'Created a copy of {name}.': 'Uma cópia de {name} foi criada.',
 'Could not duplicate the image: {details}': 'Não foi possível duplicar a imagem: {details}',
 'Moved {name} to the system trash.': '{name} foi movida para a lixeira do sistema.',
 'Could not delete the image: {details}': 'Não foi possível excluir a imagem: {details}',
 'Duplicate selected image (Ctrl+D)': 'Duplicar imagem selecionada (Ctrl+D)',
 'Move selected image to the system trash (Delete)': 'Mover imagem selecionada para a lixeira do sistema (Delete)',
 'Refresh workspace thumbnails': 'Atualizar miniaturas do workspace',
 'Double-click to open an image. Drag a thumbnail onto the editor to add it as an editable image.': 'Clique duas vezes para abrir uma imagem. Arraste uma miniatura para o editor para adicioná-la como imagem editável.',
 'Images: {count} • Limit: {limit}': 'Imagens: {count} • Limite: {limit}',
 'Could not apply the workspace limit: {details}': 'Não foi possível aplicar o limite do workspace: {details}',
 'The limit will be applied when an image is saved.': 'O limite será aplicado ao salvar uma imagem.',
 'Could not open the dropped image.': 'Não foi possível abrir a imagem arrastada.',
 'capture.png': 'captura.png',
 '&Look in:': '&Examinar:', 'Files of &type:': 'Arquivos do &tipo:',
 'File &name:': '&Nome do arquivo:', 'Show hidden files': 'Mostrar arquivos ocultos',
 'Show &hidden files': 'Mostrar arquivos &ocultos', '&New Folder': '&Nova pasta',
 '&Rename': '&Renomear', '&Delete': 'E&xcluir', 'Show Date Modified': 'Mostrar data de modificação',
 'Show Size': 'Mostrar tamanho', 'Show Type': 'Mostrar tipo',
})
CATALOG.update({
 'Close all tabs': 'Fechar todas as abas',
 'Close this tab': 'Fechar essa aba',
 'Close other tabs': 'Fechar outras abas',
 'Release notes': 'Notas de atualização',
 'Read release notes for the installed version': 'Ler notas de atualização da versão instalada',
 'What’s new in version {version}': 'Novidades da versão {version}',
 'Right-click an image tab to close all tabs, only that tab, or all other tabs.': 'Clique com o botão direito em uma aba de imagem para fechar todas as abas, somente essa aba ou as outras abas.',
 'Tabs with unsaved edits still offer Save, Discard and Cancel. Cancel stops closing the remaining tabs.': 'Abas com edições não salvas continuam oferecendo Salvar, Descartar e Cancelar. Cancelar interrompe o fechamento das abas restantes.',
 'Right-click a workspace thumbnail to duplicate it or move it to the system trash. Keyboard shortcuts and dragging images into the editor are preserved.': 'Clique com o botão direito em uma miniatura do workspace para duplicá-la ou movê-la para a lixeira do sistema. Os atalhos de teclado e o arraste de imagens para o editor foram preservados.',
 'Refresh workspace thumbnails using the icon in the upper-right corner.': 'Atualize as miniaturas do workspace pelo ícone no canto superior direito.',
 'Read the installed version’s release notes in Settings → Updates, even without an internet connection.': 'Leia as notas da versão instalada em Configurações → Atualizações, mesmo sem conexão com a internet.',
})
CATALOG.update({
 'Allow ScreenDepresso in System Settings → Privacy & Security → Screen & System Audio Recording, then reopen the app.': 'Permita o ScreenDepresso em Ajustes do Sistema → Privacidade e Segurança → Gravação de Tela e Áudio do Sistema e reabra o aplicativo.',
 'Could not capture this window. Check Screen Recording permission and try again.': 'Não foi possível capturar esta janela. Verifique a permissão de gravação de tela e tente novamente.',
 'Could not register macOS global hotkeys.': 'Não foi possível registrar os atalhos globais do macOS.',
 'Updates support Windows/Linux x86_64 and macOS Intel/Apple Silicon.': 'As atualizações estão disponíveis para Windows/Linux x86_64 e macOS Intel/Apple Silicon.',
 'Open installer': 'Abrir instalador',
 'Could not open the installer. Try again.': 'Não foi possível abrir o instalador. Tente novamente.',
 'Download verified. Open the installer, quit ScreenDepresso, drag the new app to Applications to replace it, then reopen it. Save your edits first.': 'Download verificado. Abra o instalador, encerre o ScreenDepresso, arraste o novo app para Aplicativos para substituí-lo e reabra. Salve suas edições antes.',
 'Update controls appear side by side, with the installed version centered above them.': 'Os controles de atualização ficam lado a lado, com a versão instalada centralizada acima deles.',
 'Arrow, rectangle, text, balloon and blur tools stay active for repeated annotations. Choose Select/Move to edit existing objects.': 'As ferramentas de seta, retângulo, texto, balão e desfoque continuam ativas para adicionar vários objetos. Escolha Selecionar/Mover para editar objetos existentes.',
 'macOS 15 or later is supported on Apple Silicon and Intel, with native global hotkeys, screen permissions, window previews and DMG installers.': 'Suporte ao macOS 15 ou posterior em Apple Silicon e Intel, com atalhos globais nativos, permissões de tela, prévias de janelas e instaladores DMG.',
 'On macOS, updates are verified before opening the disk image. Quit the old app and replace it in Applications.': 'No macOS, as atualizações são verificadas antes de abrir a imagem de disco. Encerre o app antigo e substitua-o em Aplicativos.',
})
CATALOG.update({
 'Text': 'Texto', 'Blur': 'Desfoque', 'Balloon': 'Balão', 'Numbers': 'Números',
 'Drop an image here': 'Arraste uma imagem aqui',
 'Capture, open or paste an image to start editing.': 'Capture, abra ou cole uma imagem para começar a editar.',
 'Capture screen': 'Capturar tela', 'Open image': 'Abrir imagem', 'Images': 'Imagens',
 'Color': 'Cor', 'Style': 'Estilo', 'Outline': 'Contorno', 'Mode': 'Modo',
 'Select an object to edit its properties.': 'Selecione um objeto para editar suas propriedades.',
 'Image': 'Imagem',
})
CATALOG.update({
 'Updated dark interface following the ScreenDepresso visual identity guide, with consistent colors, typography and icons.': 'Interface escura renovada seguindo o guia de identidade visual do ScreenDepresso, com cores, tipografia e ícones consistentes.',
 'Labeled tools and a contextual properties bar preserve existing annotation controls, shortcuts and continuous drawing.': 'Ferramentas com rótulos e barra contextual de propriedades preservam os controles de anotação, atalhos e desenho contínuo.',
 'The empty editor offers capture, open, paste and image dropping. Compact windows use smaller toolbars and scrollable properties.': 'O editor vazio oferece captura, abertura, colagem e arraste de imagens. Janelas compactas usam barras menores e propriedades com rolagem.',
 'Version 0.7.0 remains available as a separate download if you prefer the previous design. Reinstall it manually to roll back.': 'A versão 0.7.0 continua disponível em um download separado para quem prefere o design anterior. Reinstale-a manualmente para voltar.',
})
REVERSE = {}
for english, translated in CATALOG.items():
    REVERSE.setdefault(translated, english)
_language = 'en'
_translator = None


def tr(source):
    english = REVERSE.get(source, source)
    return CATALOG.get(english, english) if _language == 'pt_BR' else english


def native_help(source):
    text = tr(source)
    if sys.platform == 'darwin':
        for portable in ('Ctrl+Enter', 'Ctrl+D', 'Ctrl+V'):
            native = QKeySequence(portable.replace('Enter', 'Return')).toString(QKeySequence.SequenceFormat.NativeText)
            text = text.replace(portable, native)
    return text


def mode_label(mode):
    return tr({'tela': 'Full screen', 'janela': 'Window', 'região': 'Region'}[mode])


def format_number(value, decimals=1):
    return QLocale('pt_BR' if _language == 'pt_BR' else 'en_US').toString(float(value), 'f', decimals)


class NativeTranslator(QTranslator):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.native = QTranslator(self)
        bundled = Path(__file__).parent/'translations/qtbase_pt_BR.qm'
        if not self.native.load(str(bundled)):
            self.native.load('qtbase_pt_BR', QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))

    def isEmpty(self):
        return False

    def translate(self, context, sourceText, disambiguation=None, n=-1):
        if sourceText in CATALOG or sourceText in REVERSE:
            return tr(sourceText)
        if _language == 'pt_BR':
            translated = self.native.translate(context, sourceText, disambiguation, n)
            if translated:
                return translated
        return sourceText


def translate_tree(root):
    root.setWindowTitle(tr(root.windowTitle()))
    for widget in [root] + root.findChildren(QAction) + root.findChildren(QLabel) + root.findChildren(QAbstractButton):
        if hasattr(widget, 'text') and hasattr(widget, 'setText'):
            widget.setText(tr(widget.text()))
        if isinstance(widget, QAction) and widget.property('toolLabel'):
            widget.setIconText(tr(widget.property('toolLabel')))
    for widget in [root] + root.findChildren(QWidget) + root.findChildren(QAction):
        shortcut = widget.property('hoverShortcut')
        help_source = widget.property('helpSource')
        if help_source:
            message = widget.property('statusMessage')
            text = tr(message) if message else native_help(help_source)
            widget.setToolTip(text)
            if isinstance(widget, QLabel):
                widget.setText(text)
        elif shortcut is not None:
            widget.setToolTip(widget.text() + (f' ({QKeySequence(shortcut).toString(QKeySequence.SequenceFormat.NativeText)})' if shortcut else ''))
        else:
            widget.setToolTip(tr(widget.toolTip()))
    for widget in [root] + root.findChildren(QDockWidget) + root.findChildren(QToolBar):
        if isinstance(widget, (QDockWidget, QToolBar)):
            widget.setWindowTitle(tr(widget.windowTitle()))
    for tabs in root.findChildren(QTabWidget):
        if tabs.objectName() == 'captureTabs':
            tabs.retranslate()
            continue
        for index in range(tabs.count()):
            tabs.setTabText(index, tr(tabs.tabText(index)))
            tabs.setTabToolTip(index, tr(tabs.tabToolTip(index)))
    for widget in root.findChildren(QLineEdit)+root.findChildren(QPlainTextEdit):
        widget.setPlaceholderText(tr(widget.placeholderText()))
    for combo in root.findChildren(QComboBox):
        if combo.property('translateItems'):
            for index in range(combo.count()):
                combo.setItemText(index, tr(combo.itemText(index)))
    for bar in root.findChildren(QStatusBar):
        if bar.currentMessage():
            bar.showMessage(tr(bar.currentMessage()))
    for widget in root.findChildren(QWidget):
        if widget.objectName() == 'workspaceView':
            widget.retranslate()
        elif widget.objectName() == 'updatesPanel':
            widget.render()
        elif widget.objectName() == 'contextBar':
            widget.refresh()
        elif widget.objectName() == 'emptyState':
            widget.retranslate()
    if hasattr(root, 'reflow_toolbars'):
        root.reflow_toolbars()


def set_language(language):
    global _language, _translator
    _language = language if language in ('en', 'pt_BR') else 'en'
    QLocale.setDefault(QLocale('pt_BR' if _language == 'pt_BR' else 'en_US'))
    app = QApplication.instance()
    if app is not None:
        if _translator is None:
            _translator = NativeTranslator(app)
            app.installTranslator(_translator)
        for widget in app.topLevelWidgets():
            translate_tree(widget)
