# Guia de Deployment com Stlite

## O que é Stlite?

Stlite é uma versão do Streamlit que roda completamente no navegador usando WebAssembly (Pyodide). Não requer servidor - o aplicativo inteiro roda no lado do cliente.

## Opções de Deployment

### 1. Standalone HTML (Recomendado para Demo)

Cria um único arquivo HTML que contém toda a aplicação.

**Vantagens:**
- Sem necessidade de servidor
- Pode ser hospedado em qualquer CDN
- Funciona offline após primeiro carregamento
- Ideal para GitHub Pages

**Limitações:**
- Tamanho do arquivo pode ser grande
- Primeira carga pode ser lenta (download do Pyodide)
- Algumas bibliotecas Python podem não funcionar

### 2. Stlite Sharing

Hospedagem gratuita online em https://edit.share.stlite.net/

**Vantagens:**
- Mais fácil para compartilhar
- Interface de edição online
- Não precisa de setup local

**Limitações:**
- Limitado a arquivos menores
- Precisa de internet

### 3. GitHub Pages

Hospedar versão stlite no GitHub Pages.

**Vantagens:**
- Gratuito
- URL personalizada
- Versionamento com Git

## Estrutura de Arquivo Standalone

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Calculadora de Emissões CMP</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@0.89.1/build/stlite.css"/>
</head>
<body>
    <div id="root"></div>
    <script type="module">
        import { mount } from "https://cdn.jsdelivr.net/npm/@stlite/browser@0.89.1/build/stlite.js";
        
        mount({
            requirements: [
                "pandas",
                "plotly",
                "networkx",
                "openpyxl"
            ],
            entrypoint: "app.py",
            files: {
                "app.py": `[código do app.py aqui]`,
                "database.py": `[código do database.py aqui]`,
                // ... outros arquivos
            },
            streamlitConfig: {
                "theme.base": "light",
                "theme.primaryColor": "#4c8061",
                "client.toolbarMode": "viewer"
            }
        }, document.getElementById("root"));
    </script>
</body>
</html>
```

## Limitações Conhecidas

### Bibliotecas Não Suportadas
- `openai-whisper` (requer binários não disponíveis em Pyodide)
- `pydub` (processamento de áudio)
- `streamlit-agraph` (pode não funcionar)

### Soluções
1. Criar versão simplificada sem chatbot
2. Usar apenas features core (unidades, fluxos, sankey)
3. Remover dependências problemáticas

## Próximos Passos

1. Criar versão simplificada do app para stlite
2. Testar em ambiente local
3. Deploy em GitHub Pages
4. Criar link para compartilhamento

## Recursos

- Documentação Stlite: https://github.com/whitphx/stlite
- Exemplos: https://edit.share.stlite.net/
- Deploy Guide: https://github.com/whitphx/stlite#use-stlite-on-your-web-page-stlitebrowser
