import json
import re
import streamlit as st
from fractions import Fraction

# === Configuración de acceso ===
usuarios_autorizados = {
    "APMK": "349672",   # Nutrióloga
    "PRK": "128495"     # Desarrollador
}

# === Diccionarios de fracciones ===
unicode_fracciones = {
    "½": Fraction(1, 2), "⅓": Fraction(1, 3), "¼": Fraction(1, 4),
    "¾": Fraction(3, 4), "⅔": Fraction(2, 3), "⅕": Fraction(1, 5),
    "⅖": Fraction(2, 5), "⅗": Fraction(3, 5), "⅘": Fraction(4, 5),
    "⅙": Fraction(1, 6), "⅚": Fraction(5, 6), "⅛": Fraction(1, 8),
    "⅜": Fraction(3, 8), "⅝": Fraction(5, 8), "⅞": Fraction(7, 8)
}
unicode_rev = {v: k for k, v in unicode_fracciones.items()}

# === Funciones ===
def convertir_a_fraccion(cantidad_str):
    if cantidad_str in unicode_fracciones:
        return unicode_fracciones[cantidad_str]
    elif "/" in cantidad_str:
        return Fraction(cantidad_str)
    else:
        return Fraction(float(cantidad_str))

def fraccion_a_string(frac):
    if frac.denominator == 1:
        return str(frac.numerator)
    enteros = frac.numerator // frac.denominator
    resto = Fraction(frac.numerator % frac.denominator, frac.denominator)
    unicode = unicode_rev.get(resto, str(resto))
    return f"{enteros} {unicode}" if enteros > 0 else unicode

def multiplicar_cantidad(alimento, escalar):
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?|[½¼¾⅓⅔]|[0-9]+/[0-9]+)\s+(.*)", alimento)
    if not match:
        return alimento
    cantidad_str, descripcion = match.groups()
    cantidad = convertir_a_fraccion(cantidad_str)
    resultado = Fraction(cantidad * escalar)
    nueva_cadena = fraccion_a_string(resultado)
    return f"{nueva_cadena} {descripcion}"

def multiplicar_alimentos(lista_alimentos, escalar):
    return [multiplicar_cantidad(alimento, escalar) for alimento in lista_alimentos]

def cargar_grupos(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def interpretar_input(texto):
    if not texto.strip():
        return {}
    pares = texto.split(",")
    return {int(p.split("*")[0]): float(p.split("*")[1]) for p in pares}

def generar_menu(grupos, instrucciones):
    resultado = []
    for grupo_id in sorted(grupos.keys(), key=int):
        grupo = grupos[grupo_id]
        nombre = grupo["nombre"]
        alimentos = grupo["alimentos"]
        escalar = instrucciones.get(int(grupo_id), 1)
        escalados = multiplicar_alimentos(alimentos, escalar)
        linea = f"• {nombre}: " + ", ".join(escalados)
        resultado.append(linea)
    return resultado

# === Interfaz Web ===
st.set_page_config(page_title="APMK", layout="wide")

st.title("🔐 APMK - Generador de Plan Alimenticio")

# --- Login simple ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    usuario = st.text_input("Usuario")
    contrasena = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if usuario in usuarios_autorizados and contrasena == usuarios_autorizados[usuario]:
            st.session_state.autenticado = True
            st.success("Acceso concedido ✅")
            st.experimental_rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")
else:
    st.markdown("### ✅ Bienvenida a APMK")
    texto = st.text_input("Multiplicadores por grupo (ej: 1*2,3*1.5):")
    grupos = cargar_grupos("grupos.json")

    if st.button("Generar plan"):
        try:
            instrucciones = interpretar_input(texto)
            resultado = generar_menu(grupos, instrucciones)
            st.markdown("### 🍽️ Plan generado:")
            for linea in resultado:
                st.write(linea)
        except Exception as e:
            st.error(f"Error: {str(e)}")
