import json
import re
import streamlit as st
from fractions import Fraction

# === Configuración de acceso ===
usuarios_autorizados = {
    "APMK": "349672",   # Nutrióloga
    "PRK": "128495"     # Desarrollador
}

# === Fracciones ===
unicode_fracciones = {
    "½": Fraction(1, 2), "⅓": Fraction(1, 3), "¼": Fraction(1, 4),
    "¾": Fraction(3, 4), "⅔": Fraction(2, 3), "⅕": Fraction(1, 5),
    "⅖": Fraction(2, 5), "⅗": Fraction(3, 5), "⅘": Fraction(4, 5),
    "⅙": Fraction(1, 6), "⅚": Fraction(5, 6), "⅛": Fraction(1, 8),
    "⅜": Fraction(3, 8), "⅝": Fraction(5, 8), "⅞": Fraction(7, 8)
}
unicode_rev = {v: k for k, v in unicode_fracciones.items()}

def convertir_a_fraccion(cantidad_str: str) -> Fraction:
    if cantidad_str in unicode_fracciones:
        return unicode_fracciones[cantidad_str]
    elif "/" in cantidad_str:
        return Fraction(cantidad_str)
    else:
        return Fraction(float(cantidad_str))

def fraccion_a_string(frac: Fraction) -> str:
    if frac.denominator == 1:
        return str(frac.numerator)
    enteros = frac.numerator // frac.denominator
    resto = Fraction(frac.numerator % frac.denominator, frac.denominator)
    unicode = unicode_rev.get(resto, str(resto))
    return f"{enteros} {unicode}" if enteros > 0 else unicode

def multiplicar_cantidad(alimento: str, escalar: float) -> str:
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?|[½¼¾⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]|[0-9]+/[0-9]+)\s+(.*)", alimento)
    if not match:
        return alimento
    cantidad_str, descripcion = match.groups()
    cantidad = convertir_a_fraccion(cantidad_str)
    resultado = cantidad * Fraction(str(escalar))
    nueva_cadena = fraccion_a_string(resultado)
    return f"{nueva_cadena} {descripcion}"

def multiplicar_alimentos(lista_alimentos, escalar: float):
    return [multiplicar_cantidad(alimento, escalar) for alimento in lista_alimentos]

def cargar_grupos(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# === UI helpers ===
TIEMPOS = [("Tiempo 1", "t1"), ("Tiempo 2", "t2"), ("Tiempo 3", "t3")]

def render_fila_tiempo(nombre_visible: str, key_prefix: str, grupos_dict: dict) -> dict:
    """Una sola fila con N inputs (uno por grupo) -> {id_grupo_str: escalar_float}"""
    ids_ordenados = sorted(grupos_dict.keys(), key=lambda x: int(x))
    cols = st.columns(len(ids_ordenados), gap="small")
    escalares = {}
    for col, gid in zip(cols, ids_ordenados):
        nombre = grupos_dict[gid]["nombre"]
        with col:
            val = st.number_input(
                label=nombre,
                min_value=0.0,
                step=0.25,
                value=float(st.session_state.get(f"{key_prefix}_esc_{gid}", 0.0)),
                key=f"{key_prefix}_esc_{gid}",
                help="0 = no incluir"
            )
            escalares[gid] = float(val)
    return escalares

def generar_bloques_por_tiempo(grupos: dict, captura_por_tiempo: dict) -> dict:
    """
    Devuelve un dict {Tiempo: [ '• Grupo: item1, item2, ...', ... ]}
    """
    salida = {}
    for nombre_visible, _prefix in TIEMPOS:
        lineas = []
        escalares = captura_por_tiempo.get(nombre_visible, {})
        for gid in sorted(grupos.keys(), key=lambda x: int(x)):
            esc = escalares.get(gid, 0.0)
            if esc and esc > 0:
                grupo = grupos[gid]
                nombre = grupo["nombre"]
                items = multiplicar_alimentos(grupo["alimentos"], esc)
                lineas.append(f"• {nombre}: " + ", ".join(items))
        if lineas:
            salida[nombre_visible] = lineas
    return salida

# === Interfaz Web ===
st.set_page_config(page_title="APMK", layout="wide")
st.title("🔐 APMK - Generador de Plan Alimenticio (3 tiempos)")

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
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

else:
    st.markdown("### ✅ Bienvenida a APMK")

    # Cargar catálogo
    try:
        grupos = cargar_grupos("grupos.json")
    except FileNotFoundError:
        st.error("No se encontró 'grupos.json' en el directorio actual.")
        st.stop()

    # --- Botones de acción (Generar / Reiniciar)
    c1, c2 = st.columns([1, 1])
    with c1:
        generar_click = st.button("Generar plan", use_container_width=True)
    with c2:
        if st.button("Reiniciar", use_container_width=True):
            # Poner todos los inputs t1/t2/t3 en 0.0 y recargar
            for k in list(st.session_state.keys()):
                if k.startswith("t1_esc_") or k.startswith("t2_esc_") or k.startswith("t3_esc_"):
                    st.session_state[k] = 0.0
            st.rerun()

    # Captura compacta por tiempo (una fila con todos los grupos)
    for nombre_visible, key_prefix in TIEMPOS:
        st.subheader(nombre_visible)
        _ = render_fila_tiempo(nombre_visible, key_prefix, grupos)

    # Generar salida agrupada
    if generar_click:
        captura = {
            "Tiempo 1": {gid: float(st.session_state.get(f"t1_esc_{gid}", 0.0)) for gid in grupos.keys()},
            "Tiempo 2": {gid: float(st.session_state.get(f"t2_esc_{gid}", 0.0)) for gid in grupos.keys()},
            "Tiempo 3": {gid: float(st.session_state.get(f"t3_esc_{gid}", 0.0)) for gid in grupos.keys()},
        }
        bloques = generar_bloques_por_tiempo(grupos, captura)

        if not bloques:
            st.warning("No hay elementos para mostrar (todos con escalar 0).")
        else:
            st.markdown("### 🍽️ Plan generado:")
            for nombre_tiempo in ["Tiempo 1", "Tiempo 2", "Tiempo 3"]:
                if nombre_tiempo in bloques:
                    st.markdown(f"**{nombre_tiempo}**")
                    for linea in bloques[nombre_tiempo]:
                        st.write(linea)
                    st.markdown("")  # espacio entre bloques
