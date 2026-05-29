#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  YouTube Trends Finder - VERSION PERSONAL                        ║
║  Creado por Emanuel Arano | IA & Trading                         ║
║  youtube.com/@EmanuelAranoIATrading                              ║
╠══════════════════════════════════════════════════════════════════╣
║  Encuentra tendencias en YouTube para subirse a la ola           ║
╚══════════════════════════════════════════════════════════════════╝

QUE HACE:
  Analiza que esta trending en YouTube ahora mismo y sugiere
  ideas de videos/shorts para aprovechar las tendencias del momento.

DIFERENCIA CON youtube_nicho_finder.py:
  - youtube_nicho_finder.py → nichos a largo plazo (estrategia)
  - youtube_trends_finder.py → tendencias de HOY (tactica)

INSTALACION:
  pip install google-api-python-client pandas tabulate

CONFIGURACION:
  Reemplaza TU_API_KEY_AQUI con tu API key de Google Cloud
  Instrucciones: console.cloud.google.com → YouTube Data API v3

GitHub: github.com/farano90/crypto-alertas-bot
"""

import sys
import time
import os
from datetime import datetime
from googleapiclient.discovery import build
import pandas as pd
from tabulate import tabulate

# ─────────────────────────────────────────────
#  CONFIGURACION - MODIFICA ESTO
# ─────────────────────────────────────────────

# Tu API Key de YouTube (la misma que usas en youtube_nicho_finder.py)
API_KEY = "PON AQUI TU API KEY DE YOUTUBE"

# ─────────────────────────────────────────────
#  PAISES DISPONIBLES
# ─────────────────────────────────────────────

PAISES = {
    "1": {"codigo": "MX", "nombre": "Mexico"},
    "2": {"codigo": "ES", "nombre": "Espana"},
    "3": {"codigo": "AR", "nombre": "Argentina"},
    "4": {"codigo": "CO", "nombre": "Colombia"},
    "5": {"codigo": "US", "nombre": "Estados Unidos"},
    "6": {"codigo": "CL", "nombre": "Chile"},
    "7": {"codigo": "PE", "nombre": "Peru"},
    "8": {"codigo": "VE", "nombre": "Venezuela"},
}

# ─────────────────────────────────────────────
#  CATEGORIAS DE YOUTUBE
# ─────────────────────────────────────────────
# Estos son los IDs oficiales de categorias de YouTube
# El usuario puede agregar mas desde:
# developers.google.com/youtube/v3/docs/videoCategories

CATEGORIAS = {
    "1":  {"id": "0",  "nombre": "Todas las categorias"},
    "2":  {"id": "1",  "nombre": "Cine y animacion"},
    "3":  {"id": "2",  "nombre": "Automoviles"},
    "4":  {"id": "10", "nombre": "Musica"},
    "5":  {"id": "15", "nombre": "Mascotas y animales"},
    "6":  {"id": "17", "nombre": "Deportes"},
    "7":  {"id": "20", "nombre": "Gaming"},
    "8":  {"id": "22", "nombre": "Personas y blogs"},
    "9":  {"id": "23", "nombre": "Comedia"},
    "10": {"id": "24", "nombre": "Entretenimiento"},
    "11": {"id": "25", "nombre": "Noticias y politica"},
    "12": {"id": "26", "nombre": "Estilo de vida"},
    "13": {"id": "27", "nombre": "Educacion"},
    "14": {"id": "28", "nombre": "Ciencia y tecnologia"},
    "15": {"id": "29", "nombre": "ONG y activismo"},
}

# ─────────────────────────────────────────────
#  CONEXION CON LA API
# ─────────────────────────────────────────────

def conectar_api():
    """Crea la conexion con la API de YouTube."""
    try:
        youtube = build("youtube", "v3", developerKey=API_KEY)
        print("Conexion con YouTube API exitosa\n")
        return youtube
    except Exception as e:
        print(f"Error conectando con la API: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────
#  OBTENER VIDEOS TRENDING
# ─────────────────────────────────────────────

def obtener_trending(youtube, pais_codigo: str, categoria_id: str,
                     max_resultados: int = 20) -> list[dict]:
    """
    Obtiene los videos mas populares en YouTube ahora mismo.

    Parametros:
        youtube: conexion con la API
        pais_codigo: codigo del pais (MX, ES, AR, etc)
        categoria_id: ID de categoria de YouTube (0 = todas)
        max_resultados: cuantos videos traer (max 50)

    Retorna:
        Lista de videos trending con sus estadisticas
    """
    try:
        params = {
            "part":       "snippet,statistics,contentDetails",
            "chart":      "mostPopular",
            "regionCode": pais_codigo,
            "maxResults": max_resultados,
            # Nota: relevanceLanguage no es compatible con chart=mostPopular
            # Los resultados son los videos mas vistos en esa region sin filtro de idioma
        }
        # Solo agregar categoria si no es "todas"
        if categoria_id != "0":
            params["videoCategoryId"] = categoria_id

        respuesta = youtube.videos().list(**params).execute()
        return respuesta.get("items", [])

    except Exception as e:
        print(f"Error obteniendo trending: {e}")
        return []


def obtener_trending_por_keyword(youtube, keyword: str, pais_codigo: str,
                                  max_resultados: int = 10) -> list[dict]:
    """
    Busca videos recientes y populares sobre una keyword especifica.
    Util para ver que contenido esta funcionando en tu nicho ahora mismo.

    Parametros:
        keyword: tema a buscar
        pais_codigo: codigo del pais
        max_resultados: cuantos videos traer
    """
    try:
        # Buscar videos de las ultimas 48 horas ordenados por relevancia
        from datetime import datetime, timedelta
        hace_48h = (datetime.utcnow() - timedelta(hours=48)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        respuesta = youtube.search().list(
            part="snippet",
            q=keyword,
            type="video",
            order="viewCount",
            regionCode=pais_codigo,
            publishedAfter=hace_48h,
            maxResults=max_resultados,
            relevanceLanguage="es",
        ).execute()

        ids = [item["id"]["videoId"] for item in respuesta.get("items", [])]
        if not ids:
            return []

        # Obtener estadisticas de esos videos
        detalles = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(ids),
        ).execute()

        return detalles.get("items", [])

    except Exception as e:
        print(f"Error buscando keyword '{keyword}': {e}")
        return []


# ─────────────────────────────────────────────
#  ANALIZAR Y PROCESAR VIDEOS
# ─────────────────────────────────────────────

def parsear_duracion(duracion_iso: str) -> int:
    """Convierte duracion ISO 8601 a segundos totales."""
    import re
    patron = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = patron.match(duracion_iso)
    if not match:
        return 0
    horas = int(match.group(1) or 0)
    minutos = int(match.group(2) or 0)
    segundos = int(match.group(3) or 0)
    return horas * 3600 + minutos * 60 + segundos


def clasificar_formato(segundos: int) -> str:
    """
    Clasifica el video segun su duracion para saber que formato hacer.

    Esto es util para decidir si hacer un Short o un video largo
    basandose en lo que esta funcionando en tendencia.
    """
    if segundos <= 60:
        return "SHORT"
    elif segundos <= 300:
        return "Video corto (1-5 min)"
    elif segundos <= 1200:
        return "Video medio (5-20 min)"
    else:
        return "Video largo (+20 min)"


def calcular_score_tendencia(vistas: int, likes: int,
                              comentarios: int, horas_desde_publicacion: float) -> int:
    """
    Calcula un score de tendencia del 1 al 100.

    Factores:
    - Vistas totales (peso 40%)
    - Ratio likes/vistas - engagement (peso 30%)
    - Velocidad de crecimiento - vistas por hora (peso 30%)

    Un video con pocas horas y muchas vistas tiene score muy alto
    porque esta creciendo rapido = es tendencia real.
    """
    score = 0

    # Factor 1: Vistas totales (40 puntos)
    if vistas >= 1_000_000:   score += 40
    elif vistas >= 500_000:   score += 32
    elif vistas >= 100_000:   score += 24
    elif vistas >= 50_000:    score += 16
    elif vistas >= 10_000:    score += 8
    else:                     score += 2

    # Factor 2: Engagement ratio likes/vistas (30 puntos)
    if vistas > 0:
        ratio = likes / vistas * 100
        if ratio >= 5:    score += 30
        elif ratio >= 3:  score += 22
        elif ratio >= 1:  score += 14
        elif ratio >= 0.5:score += 7
        else:             score += 2

    # Factor 3: Velocidad de crecimiento vistas/hora (30 puntos)
    if horas_desde_publicacion > 0:
        vistas_por_hora = vistas / horas_desde_publicacion
        if vistas_por_hora >= 50_000:  score += 30
        elif vistas_por_hora >= 10_000:score += 22
        elif vistas_por_hora >= 1_000: score += 14
        elif vistas_por_hora >= 100:   score += 7
        else:                          score += 2

    return min(score, 100)


def procesar_videos(videos: list) -> list[dict]:
    """
    Procesa la lista de videos y extrae la informacion relevante.
    Calcula el score de tendencia y sugiere el formato a replicar.
    """
    resultados = []

    for video in videos:
        try:
            snippet    = video.get("snippet", {})
            stats      = video.get("statistics", {})
            content    = video.get("contentDetails", {})

            titulo     = snippet.get("title", "")[:60]
            canal      = snippet.get("channelTitle", "")[:25]
            publicado  = snippet.get("publishedAt", "")
            video_id   = video.get("id", "")

            vistas     = int(stats.get("viewCount", 0))
            likes      = int(stats.get("likeCount", 0))
            comentarios= int(stats.get("commentCount", 0))

            duracion_iso = content.get("duration", "PT0S")
            segundos     = parsear_duracion(duracion_iso)
            formato      = clasificar_formato(segundos)

            # Calcular horas desde publicacion
            from datetime import datetime, timezone
            if publicado:
                pub_dt = datetime.fromisoformat(
                    publicado.replace("Z", "+00:00")
                )
                ahora = datetime.now(timezone.utc)
                horas = (ahora - pub_dt).total_seconds() / 3600
            else:
                horas = 24

            score = calcular_score_tendencia(vistas, likes, comentarios, horas)

            url_video = f"https://www.youtube.com/watch?v={video_id}"

            resultados.append({
                "Score":       score,
                "Formato":     formato,
                "Titulo":      titulo,
                "Canal":       canal,
                "Vistas":      f"{vistas:,}",
                "Likes":       f"{likes:,}",
                "Hace (hrs)":  f"{horas:.1f}",
                "URL":         url_video,
            })

        except Exception:
            continue

    return resultados


# ─────────────────────────────────────────────
#  GENERAR IDEAS DE CONTENIDO
# ─────────────────────────────────────────────

def generar_ideas(resultados: list[dict], nicho: str) -> list[str]:
    """
    Analiza los videos trending y genera ideas concretas de contenido
    que puedes hacer para subirte a la tendencia.

    La idea es simple: si un video sobre X esta en tendencia,
    tu puedes hacer TU VERSION sobre X en tu nicho.
    """
    ideas = []

    # Contar formatos que estan funcionando
    formatos = {}
    for r in resultados:
        fmt = r["Formato"]
        formatos[fmt] = formatos.get(fmt, 0) + 1

    formato_ganador = max(formatos, key=formatos.get) if formatos else "Video corto"

    # Mapeo de formatos a acciones concretas
    accion_formato = {
        "SHORT":                "Graba un Short de 30-60 segundos sobre este tema",
        "Video corto (1-5 min)":"Graba un video corto de 2-3 minutos sobre este tema",
        "Video medio (5-20 min)":"Graba un video de 10-15 minutos explicando este tema",
        "Video largo (+20 min)": "Graba un video largo o en vivo sobre este tema",
    }
    accion = accion_formato.get(formato_ganador, "Graba un video sobre este tema")

    ideas.append(f"Formato ganador HOY: {formato_ganador}")
    ideas.append(f"Accion recomendada: {accion}")

    # Top 3 videos con mas score
    top3 = sorted(resultados, key=lambda x: x["Score"], reverse=True)[:3]

    ideas.append("\nTop 3 ideas concretas para tu canal basadas en tendencias:")

    for i, video in enumerate(top3, 1):
        titulo_original = video["Titulo"]
        score = video["Score"]
        vistas = video["Vistas"]
        horas = video["Hace (hrs)"]

        # Urgencia segun score
        if score >= 80:
            urgencia = "ACTUA HOY - tendencia explosiva"
        elif score >= 60:
            urgencia = "Esta semana - tendencia fuerte"
        else:
            urgencia = "Proximos dias - tendencia moderada"

        # Generar idea adaptada al nicho del usuario
        # Detectar palabras clave del titulo para personalizar la idea
        titulo_lower = titulo_original.lower()

        if "live" in titulo_lower or "en vivo" in titulo_lower:
            idea_adaptada = (
                f"Haz un video EN VIVO sobre {nicho}. "
                f"Muestra el mercado en tiempo real mientras explicas tu estrategia."
            )
        elif "analysis" in titulo_lower or "analisis" in titulo_lower:
            idea_adaptada = (
                f"Graba un analisis de {nicho} en este momento. "
                f"Explica que ves en el grafico y cual es tu perspectiva."
            )
        elif "gold" in titulo_lower or "oro" in titulo_lower:
            idea_adaptada = (
                f"El oro esta en tendencia junto con crypto. "
                f"Graba un video comparando oro vs {nicho} como inversion."
            )
        elif "trading" in titulo_lower:
            idea_adaptada = (
                f"Graba un video de trading de {nicho}. "
                f"Muestra una operacion real o un analisis de entrada."
            )
        elif "bitcoin" in titulo_lower or "btc" in titulo_lower:
            idea_adaptada = (
                f"Bitcoin esta en tendencia. Graba tu analisis de BTC "
                f"aplicando tu estrategia de {nicho}."
            )
        elif "forex" in titulo_lower:
            idea_adaptada = (
                f"El forex esta en tendencia junto con crypto. "
                f"Graba un video sobre como operar {nicho} vs forex."
            )
        else:
            idea_adaptada = (
                f"Adapta este tema a tu nicho de {nicho}. "
                f"Haz TU VERSION en espanol de este contenido."
            )

        ideas.append(f"\n  {i}. Basado en: '{titulo_original[:50]}...'")
        ideas.append(f"     {video['Canal']} | {vistas} vistas en {horas} horas")
        ideas.append(f"     Score: {score}/100 | {urgencia}")
        ideas.append(f"     Idea para tu canal: {idea_adaptada}")

    # Consejo final
    ideas.append("\nCONSEJO CLAVE:")
    ideas.append(
        f"  Casi toda la competencia en tendencia es en ingles o hindi."
    )
    ideas.append(
        f"  Hacer este contenido en espanol te da ventaja sobre {len(resultados)} canales encontrados."
    )
    ideas.append(
        f"  El mercado hispanohablante tiene 500 millones de personas"
        f" y muy pocos creadores de calidad en {nicho}."
    )

    return ideas


# ─────────────────────────────────────────────
#  MOSTRAR RESULTADOS
# ─────────────────────────────────────────────

def mostrar_resultados(resultados: list[dict], pais: str,
                       categoria: str, nicho: str = ""):
    """
    Muestra los resultados en tabla ordenada por score
    y exporta a CSV con todos los links.
    """
    if not resultados:
        print("\nNo se encontraron resultados.")
        print("Intenta con otra categoria o pais.")
        return

    df = pd.DataFrame(resultados)
    df = df.sort_values("Score", ascending=False).reset_index(drop=True)

    print("\n" + "="*70)
    print(f"  VIDEOS EN TENDENCIA — {pais} — {categoria}")
    print(f"  Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*70)

    # Mostrar tabla sin URL para que se vea limpio
    columnas = ["Score", "Formato", "Titulo", "Canal",
                "Vistas", "Likes", "Hace (hrs)"]
    print(tabulate(
        df[columnas].head(15),
        headers="keys",
        tablefmt="rounded_outline",
        showindex=True,
    ))

    # Exportar CSV con URLs
    nombre_csv = f"trends_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df.to_csv(nombre_csv, index=False, encoding="utf-8-sig")
    print(f"\nResultados exportados a: {nombre_csv}")
    print("Abre el CSV para ver los links de cada video")

    # Mostrar ideas de contenido
    if nicho:
        print("\n" + "─"*70)
        print("  IDEAS DE CONTENIDO PARA TU CANAL")
        print("─"*70)
        ideas = generar_ideas(resultados, nicho)
        for idea in ideas:
            print(f"  {idea}")

    # Resumen
    print("\n" + "─"*70)
    print("  COMO INTERPRETAR EL SCORE:")
    print("  80-100  Tendencia explosiva, actua HOY")
    print("  60-79   Tendencia fuerte, actua esta semana")
    print("  40-59   Tendencia moderada, vale la pena considerar")
    print("  0-39    Poco momentum, no es prioridad")
    print("─"*70)


# ─────────────────────────────────────────────
#  MENU INTERACTIVO
# ─────────────────────────────────────────────

def pedir_pais() -> dict:
    """Pregunta al usuario en que pais quiere buscar tendencias."""
    print("""
  Paises disponibles:
  1. Mexico
  2. Espana
  3. Argentina
  4. Colombia
  5. Estados Unidos
  6. Chile
  7. Peru
  8. Venezuela
""")
    while True:
        opcion = input("  Selecciona el pais (1-8): ").strip()
        if opcion in PAISES:
            return PAISES[opcion]
        print("  Opcion invalida. Escribe un numero del 1 al 8.")


def pedir_categoria() -> dict:
    """Pregunta al usuario en que categoria buscar."""
    print("""
  Categorias disponibles:
  1.  Todas las categorias (recomendado para ver tendencias generales)
  2.  Cine y animacion
  3.  Automoviles
  4.  Musica
  5.  Mascotas y animales
  6.  Deportes
  7.  Gaming
  8.  Personas y blogs
  9.  Comedia
  10. Entretenimiento
  11. Noticias y politica
  12. Estilo de vida
  13. Educacion
  14. Ciencia y tecnologia
  15. ONG y activismo
""")
    while True:
        opcion = input("  Selecciona la categoria (1-15): ").strip()
        if opcion in CATEGORIAS:
            return CATEGORIAS[opcion]
        print("  Opcion invalida. Escribe un numero del 1 al 15.")


def pedir_tipo_busqueda() -> str:
    """Pregunta que tipo de analisis quiere hacer el usuario."""
    print("""
  Que quieres analizar?

  1. Trending general
     Ver los videos mas populares en YouTube ahora mismo en tu pais
     Util para: descubrir temas virales del momento

  2. Trending en mi nicho
     Buscar que esta funcionando ahora mismo en tu tema especifico
     Util para: saber de que hablar esta semana en tu canal

  3. Ambos (recomendado)
     Primero ves las tendencias generales y luego las de tu nicho
     Util para: vision completa de oportunidades
""")
    while True:
        opcion = input("  Selecciona (1/2/3): ").strip()
        if opcion in ["1", "2", "3"]:
            return opcion
        print("  Opcion invalida. Escribe 1, 2 o 3.")


def pedir_nicho() -> str:
    """Pregunta el nicho del canal del usuario."""
    print("""
  Cual es el tema de tu canal?
  Escribe una o dos palabras que describan tu contenido.

  Ejemplos:
    trading crypto
    moda femenina
    recetas saludables
    desarrollo personal
    gaming minecraft
    tecnologia python
""")
    while True:
        nicho = input("  Tu nicho: ").strip()
        if nicho:
            return nicho
        print("  Por favor escribe el tema de tu canal.")


# ─────────────────────────────────────────────
#  FUNCION PRINCIPAL
# ─────────────────────────────────────────────

def main():
    print("="*70)
    print("  YouTube Trends Finder - Emanuel Arano | IA & Trading")
    print("  youtube.com/@EmanuelAranoIATrading")
    print("="*70)
    print("""
  Encuentra que esta en tendencia en YouTube AHORA MISMO
  para que puedas crear contenido que aproveche el momento.

  DIFERENCIA CON youtube_nicho_finder.py:
    nicho_finder   → estrategia a largo plazo (que nicho abrir)
    trends_finder  → tactica de hoy (de que hablar esta semana)
""")

    # Verificar API key
    if API_KEY == "TU_API_KEY_AQUI":
        print("ERROR: Debes configurar tu API_KEY en el archivo")
        print("Instrucciones en la parte superior del script")
        sys.exit(1)

    # Conectar con la API
    youtube = conectar_api()

    # Menu interactivo
    print("─"*70)
    print("  CONFIGURACION")
    print("─"*70)

    pais      = pedir_pais()
    categoria = pedir_categoria()
    tipo      = pedir_tipo_busqueda()

    nicho = ""
    if tipo in ["2", "3"]:
        nicho = pedir_nicho()

    # Confirmacion
    print("\n" + "─"*70)
    print("  CONFIGURACION CONFIRMADA")
    print("─"*70)
    print(f"  Pais:      {pais['nombre']}")
    print(f"  Categoria: {categoria['nombre']}")
    tipo_txt = {"1": "Trending general",
                "2": "Trending en mi nicho",
                "3": "Ambos"}
    print(f"  Analisis:  {tipo_txt[tipo]}")
    if nicho:
        print(f"  Nicho:     {nicho}")
    print()

    confirmar = input("  Empezar analisis? (s/n): ").strip().lower()
    if confirmar != "s":
        print("  Cancelado.")
        sys.exit(0)

    todos_resultados = []

    # ── Trending general ─────────────────────────────────────────
    if tipo in ["1", "3"]:
        print("\n" + "─"*70)
        print(f"  Obteniendo trending general en {pais['nombre']}...")
        print("─"*70)
        videos = obtener_trending(
            youtube, pais["codigo"], categoria["id"], max_resultados=20
        )
        if videos:
            resultados = procesar_videos(videos)
            todos_resultados.extend(resultados)
            mostrar_resultados(
                resultados,
                pais["nombre"],
                categoria["nombre"],
                nicho
            )
        else:
            print("  No se encontraron videos trending.")

        time.sleep(1)

    # ── Trending en el nicho ─────────────────────────────────────
    if tipo in ["2", "3"] and nicho:
        print("\n" + "─"*70)
        print(f"  Buscando tendencias en tu nicho: '{nicho}'...")
        print("─"*70)
        videos_nicho = obtener_trending_por_keyword(
            youtube, nicho, pais["codigo"], max_resultados=10
        )
        if videos_nicho:
            resultados_nicho = procesar_videos(videos_nicho)
            todos_resultados.extend(resultados_nicho)
            mostrar_resultados(
                resultados_nicho,
                pais["nombre"],
                f"Nicho: {nicho}",
                nicho
            )
        else:
            print(f"  No se encontraron videos recientes sobre '{nicho}'.")
            print("  Intenta con keywords mas generales.")

    print("\nAnalisis completado")
    print("="*70)


if __name__ == "__main__":
    main()
