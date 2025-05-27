# Configurações visuais e constantes
CANVAS_CONFIG = {
    "width": 1200,
    "height": 700,
    "directed": True,
    "node": {
        "labelProperty": "label",
        "shape": "box",
        "font": {"size": 12},
        "margin": 10,
        "borderWidth": 2,
        "color": "#e6f3ff"
    },
    "link": {"renderLabel": True},
    "physics": {"enabled": True},
    "backgroundColor": "#dcdcdc"  # Cinza bem claro
}

COLORS = {
    "primary": "#0066cc",
    "background": "#f8f9fa",
    "tax_border": "#cc0000",
    "default_border": "#333333"
}

# Adicionar estilos para a seção de import/export
EXPORT_STYLES = {
    "button": {
        "background": "#4CAF50",
        "color": "white"
    },
    "warning": {
        "background": "#FFF3CD",
        "color": "#856404"
    }
}

FLOWCHART_LAYOUTS = {
    "Hierárquico": {
        "hierarchical": {
            "enabled": True,
            "direction": "LR",  # Left-to-Right
            "sortMethod": "directed",
            "nodeSpacing": 300,
            "levelSeparation": 180
        }
    },
    "Ordenado por Fluxo": {
        "hierarchical": {
            "enabled": True,
            "direction": "LR",
            "sortMethod": "hubsize",
            "nodeSpacing": 200
        }
    },
    "Circular": {
        "layout": {
            "randomSeed": 42,
            "improvedLayout": True
        }
    }
}