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

# === Funciones de cantidad ===
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

# === Carga de catálogo ===
def cargar_grupos(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# === UI helpers ===
TIEMPOS = ["Tiempo 1", "Tiempo 2", "Tiempo 3"]

def render_fila_tiempo(nombre_tiempo: str, grupos_dict: dict) -> dict:
    """
    Dibuja una fila con 7 inputs (uno por grupo) y regresa {id_grupo_str: escalar_float}
    """
    # Ordenar por ID numérico para mantener el orden del JSON
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
                value=0.0,
                key=f"{nombre_tiempo}_esc_{gid}",
                help="0 = no incluir"
            )
            escalares[gid] = float(val)
    return escalares

def generar_plan_por_tiempos(grupos: dict, captura_por_tiempo: dict) -> list:
    """
    Recorre tiempos y grupos; multiplica cuando escalar > 0 y arma las líneas del machote.
    """
    resultado = []
    for t in TIEMPOS:
        escalares = captura_por_tiempo.get(t, {})
        # Mantener orden por ID
        for gid in sorted(grupos.keys(), key=lambda x: int(x)):
            esc = escalares.get(gid, 0.0)
            if esc and esc > 0:
                grupo = grupos[gid]
                nombre = grupo["nombre"]
                alimentos = grupo["alimentos"]
                escalados = multiplicar_alimentos(alimentos, esc)
                linea = f"• {t} – {nombre}: " + ", ".join(escalados)
                resultado.append(linea)
    return resultado

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

    # Captura compacta por tiempo (una fila con 7 inputs)
    st.subheader("Tiempo 1")
    escalares_t1 = render_fila_tiempo("t1", grupos)

    st.subheader("Tiempo 2")
    escalares_t2 = render_fila_tiempo("t2", grupos)

    st.subheader("Tiempo 3")
    escalares_t3 = render_fila_tiempo("t3", grupos)

    # Botón generar
    if st.button("Generar plan"):
        try:
            captura_por_tiempo = {
                "Tiempo 1": escalares_t1,
                "Tiempo 2": escalares_t2,
                "Tiempo 3": escalares_t3
            }
            resultado = generar_plan_por_tiempos(grupos, captura_por_tiempo)

            if not resultado:
                st.warning("No hay elementos para mostrar (todos con escalar 0).")
            else:
                st.markdown("### 🍽️ Plan generado:")
                for linea in resultado:
                    st.write(linea)

                # Exportaciones
                # CSV sencillo: cada línea en una fila
                import pandas as pd
                df_out = pd.DataFrame({"plan": resultado})
                csv = df_out.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Descargar CSV",
                    data=csv,
                    file_name="plan_3_tiempos.csv",
                    mime="text/csv"
                )

                # JSON estructurado
                json_out = json.dumps({"plan": resultado}, ensure_ascii=False, indent=2)
                st.download_button(
                    "Descargar JSON",
                    data=json_out,
                    file_name="plan_3_tiempos.json",
                    mime="application/json"
                )

        except Exception as e:
            st.error(f"Error: {str(e)}")

    st.caption("Tip: usa 0.25 / 0.5 / 0.75 / 1 / 1.5, etc. Si pones 0, el grupo no se incluye.")
