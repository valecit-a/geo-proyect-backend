"""
Utilidades para manejo de moneda y conversiones
"""

# Valor de la UF en CLP (actualizar periódicamente)
# Fuente: Banco Central de Chile
# Valor aproximado a noviembre 2025
VALOR_UF_CLP = 37500.0  # ~$37,500 CLP por UF

def uf_to_clp(uf_value: float) -> float:
    """
    Convierte un valor en UF a pesos chilenos (CLP)
    
    Args:
        uf_value: Valor en UF
        
    Returns:
        Valor en CLP
    """
    return uf_value * VALOR_UF_CLP


def clp_to_uf(clp_value: float) -> float:
    """
    Convierte un valor en pesos chilenos (CLP) a UF
    
    Args:
        clp_value: Valor en CLP
        
    Returns:
        Valor en UF
    """
    return clp_value / VALOR_UF_CLP


def format_uf(uf_value: float) -> str:
    """
    Formatea un valor en UF con separador de miles
    
    Args:
        uf_value: Valor en UF
        
    Returns:
        String formateado (ej: "4.500 UF")
    """
    return f"{uf_value:,.0f} UF".replace(",", ".")


def format_clp(clp_value: float) -> str:
    """
    Formatea un valor en CLP con separador de miles
    
    Args:
        clp_value: Valor en CLP
        
    Returns:
        String formateado (ej: "$150.000.000")
    """
    return f"${clp_value:,.0f}".replace(",", ".")
