"""Arma la web de Miranda Sarkis a partir de la carpeta `contenido/`.

Lee las carpetas y fichas, achica las fotos a tamaño web y escribe todo en `_site/`,
que es lo que GitHub Pages publica. Se corre solo con cada cambio (ver
.github/workflows/publicar.yml), pero también se puede correr a mano:

    python sitio/construir.py
"""
import html
import json
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None

RAIZ = Path(__file__).resolve().parent.parent
CONTENIDO = RAIZ / "contenido"
SITIO = RAIZ / "sitio"
SALIDA = RAIZ / "_site"

FOTO_MAX = 2000      # lado mayor de las fotos grandes
MINI_MAX = 900       # lado mayor de las miniaturas de la grilla de obras
EXT_FOTO = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}

avisos = []


def aviso(msg):
    avisos.append(msg)
    print("AVISO:", msg)


# ---------- utilidades ----------

def slug(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "x"


def nfc(t):
    return unicodedata.normalize("NFC", t)


def orden_natural(nombre):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", nfc(nombre))]


def sin_numero(nombre):
    """'03 La danza' -> 'La danza'; '2024. Sostener el fuego' -> 'Sostener el fuego'."""
    return re.sub(r"^\s*\d+[\s.\-_)]*\s*", "", nfc(nombre)).strip()


def leer_texto(path):
    """Devuelve el texto de un .txt, .md o .docx."""
    if path.suffix.lower() == ".docx":
        from docx import Document
        doc = Document(str(path))
        return "\n\n".join(p.text for p in doc.paragraphs)
    return path.read_text(encoding="utf-8-sig")


def buscar_ficha(carpeta, nombres=("ficha", "info", "datos")):
    for n in nombres:
        for ext in (".txt", ".md", ".docx"):
            p = carpeta / (n + ext)
            if p.exists():
                return p
    # si hay un único documento en la carpeta, se usa ese
    docs = [p for p in carpeta.iterdir() if p.suffix.lower() in (".txt", ".md", ".docx") and not p.name.startswith("~$")]
    return docs[0] if len(docs) == 1 else None


CLAVES = {
    "titulo": "titulo", "título": "titulo",
    "tecnica": "tecnica", "técnica": "tecnica", "tecnica y material": "tecnica", "técnica y material": "tecnica",
    "tecnica y materiales": "tecnica", "técnica y materiales": "tecnica", "material": "tecnica", "materiales": "tecnica",
    "medidas": "medidas", "año": "anio", "ano": "anio", "anio": "anio",
    "registro": "registro", "fotos": "registro", "foto": "registro",
    "formato": "formato", "lugar": "lugar",
    "subtitulo": "subtitulo", "subtítulo": "subtitulo",
    "epigrafe": "epigrafe", "epígrafe": "epigrafe",
    "firma": "firma", "pie de foto": "pie", "pie": "pie",
}


def leer_ficha(path):
    """Lee una ficha: líneas 'Clave: valor' arriba, y el texto largo debajo de una línea '---'.

    Devuelve (campos, filas, parrafos): `campos` son las claves conocidas,
    `filas` todas las líneas 'Clave: valor' en orden, y `parrafos` el texto de abajo.
    """
    if path is None:
        return {}, [], []
    texto = leer_texto(path).replace("\r\n", "\n")
    partes = re.split(r"\n\s*-{3,}\s*\n", "\n" + texto + "\n", maxsplit=1)
    cabeza = partes[0]
    cuerpo = partes[1] if len(partes) > 1 else ""
    campos, filas = {}, []
    lineas = cabeza.split("\n")
    for i, linea in enumerate(lineas):
        linea = linea.strip()
        if not linea:
            continue
        m = re.match(r"^([^:]{1,40}):\s*(.*)$", linea)
        if not m or (filas and len(linea) > 160):
            # sin '---': desde la primera línea que no es 'Clave: valor', todo es texto
            cuerpo = "\n".join(lineas[i:]) + "\n\n" + cuerpo
            break
        k, v = m.group(1).strip(), m.group(2).strip()
        filas.append((k, v))
        kk = CLAVES.get(k.lower())
        if kk and kk not in campos:
            campos[kk] = v
    parrafos = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", cuerpo)]
    # se descartan las fichas de piezas sueltas que vienen dentro del texto de una serie
    # ("Título: ...", "Medidas: ...") y los rótulos cortos como "Obras que componen la serie:"
    def es_ficha(p):
        m = re.match(r"^([^:]{1,40}):\s*(.*)$", p)
        return (m and CLAVES.get(m.group(1).strip().lower()) and len(p) < 140) or (p.endswith(":") and len(p) < 70)
    return campos, filas, [p for p in parrafos if p and not es_ficha(p)]


def medidas(m):
    m = (m or "").strip()
    if not m:
        return ""
    if m.lower() in ("variables", "medidas variables"):
        return "Medidas variables"
    m = m.replace("aproximadamente", "aprox.")
    m = re.sub(r"(?<=\d)\s*[xX×]\s*(?=\d)", " × ", m)
    m = re.sub(r"(\d)\s*cm\b", r"\1 cm", m)
    return m


def fotos_de(carpeta):
    fs = [p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in EXT_FOTO and not p.name.startswith(".")]
    return sorted(fs, key=lambda p: orden_natural(p.stem))


def guardar_foto(src, destino_rel, maximo=FOTO_MAX, mini=False):
    """Achica y guarda una foto en _site. Devuelve (ruta, ancho, alto[, ruta_mini])."""
    destino = SALIDA / destino_rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    except Exception as e:  # noqa: BLE001
        aviso(f"No pude abrir la foto {src.relative_to(RAIZ)}: {e}")
        return None
    im.thumbnail((maximo, maximo), Image.LANCZOS)
    im.save(destino, "JPEG", quality=84, optimize=True, progressive=True)
    res = [destino_rel, im.width, im.height]
    if mini:
        t = im.copy()
        t.thumbnail((MINI_MAX, MINI_MAX), Image.LANCZOS)
        mini_rel = str(Path(destino_rel).with_name("t-" + Path(destino_rel).name))
        t.save(SALIDA / mini_rel, "JPEG", quality=80, optimize=True, progressive=True)
        res.append(mini_rel)
    return res


def con_italicas(t):
    """Escapa el texto y convierte _así_ en cursiva."""
    t = html.escape(t, quote=False)
    return re.sub(r"(?<![\w])_(.+?)_(?![\w])", r"<em>\1</em>", t)


# ---------- secciones ----------

def leer_inicio():
    carpeta = CONTENIDO / "inicio"
    campos, _, parrafos = leer_ficha(buscar_ficha(carpeta, ("inicio", "ficha", "info")))
    fs = fotos_de(carpeta)
    if not fs:
        aviso("Falta la foto de portada en contenido/inicio/")
        return {"portada": None, "registro": "", "intro": " ".join(parrafos), "alt": ""}
    f = guardar_foto(fs[0], "img/portada.jpg", 2400)
    return {"portada": f, "registro": campos.get("registro", ""), "intro": " ".join(parrafos),
            "alt": campos.get("descripcion", campos.get("descripción", "")) or "Obra de Miranda Sarkis"}


def leer_muestras():
    base = CONTENIDO / "muestras"
    out, fotos = [], {}
    if not base.exists():
        return out, fotos
    for carpeta in sorted([c for c in base.iterdir() if c.is_dir()], key=lambda c: orden_natural(c.name), reverse=True):
        campos, filas, parrafos = leer_ficha(buscar_ficha(carpeta))
        titulo = campos.get("titulo") or sin_numero(carpeta.name)
        anio = campos.get("anio") or (re.match(r"^\s*(\d{4})", carpeta.name) or [None, ""])[1]
        mid = slug(titulo)
        especiales = {"titulo", "anio", "lugar", "subtitulo", "epigrafe", "firma"}
        ficha = [[k, v] for k, v in filas if CLAVES.get(k.lower()) not in especiales and v]
        m = {"id": mid, "titulo": titulo, "anio": anio, "lugar": campos.get("lugar", ""), "ficha": ficha}
        if campos.get("subtitulo"):
            m["subtitulo"] = campos["subtitulo"]
        if campos.get("epigrafe"):
            m["epigrafe"] = campos["epigrafe"]
        if campos.get("firma"):
            m["firma"] = campos["firma"]
        numerados = parrafos and all(re.match(r"^\d+\s*[.\-)]\s*", p) for p in parrafos)
        if numerados:
            m["pasajes"] = [re.sub(r"^\d+\s*[.\-)]\s*", "", p) for p in parrafos]
        elif parrafos:
            m["texto"] = parrafos
        else:
            m["texto"] = None
        lista = []
        for i, f in enumerate(fotos_de(carpeta)):
            r = guardar_foto(f, f"img/muestras/{mid}/{i + 1}.jpg")
            if r:
                lista.append(r)
        fotos[mid] = lista
        if not lista:
            aviso(f"La muestra '{titulo}' no tiene fotos")
        out.append(m)
    return out, fotos


def leer_obras():
    base = CONTENIDO / "obras"
    obras, cats = [], {}
    if not base.exists():
        return obras, cats
    for cat_dir in sorted([c for c in base.iterdir() if c.is_dir()], key=lambda c: orden_natural(c.name)):
        cat_nombre = sin_numero(cat_dir.name)
        cat = slug(cat_nombre)
        cats[cat] = cat_nombre
        for carpeta in sorted([c for c in cat_dir.iterdir() if c.is_dir()], key=lambda c: orden_natural(c.name)):
            campos, _, parrafos = leer_ficha(buscar_ficha(carpeta))
            titulo = campos.get("titulo") or sin_numero(carpeta.name)
            oid = "obra-" + slug(titulo)
            if any(o["id"] == oid for o in obras):
                oid += "-" + slug(cat)
            tec, med, anio = campos.get("tecnica", ""), medidas(campos.get("medidas", "")), campos.get("anio", "")
            items = []
            for i, f in enumerate(fotos_de(carpeta)):
                r = guardar_foto(f, f"img/obras/{oid[5:]}/{i + 1}.jpg", mini=True)
                if not r:
                    continue
                nombre = sin_numero(f.stem)
                if nombre and not re.fullmatch(r"[\d\s()._-]*", nombre) and not nombre.lower().startswith(("whatsapp", "img_", "_mg", "dsc")):
                    partes = [p.strip() for p in re.split(r"\s+-\s+", nombre) if p.strip()]
                    if len(partes) >= 2:
                        if len(partes) >= 3:
                            partes[2] = medidas(partes[2])
                        cap = " · ".join(partes)
                    else:
                        cap = " · ".join([x for x in (partes[0], tec, med, anio) if x])
                    items.append([r[0], r[1], r[2], cap, r[3], True])
                else:
                    cap = " · ".join([x for x in (titulo, tec, med, anio) if x])
                    items.append([r[0], r[1], r[2], cap, r[3], False])
            if not items:
                aviso(f"La obra '{titulo}' no tiene fotos: no se publica")
                continue
            o = {"id": oid, "cat": cat, "titulo": titulo, "anio": anio, "tec": tec, "med": med,
                 "cover": items[0][4], "items": items}
            if campos.get("formato"):
                o["nota"] = campos["formato"]
            if campos.get("registro"):
                o["registro"] = campos["registro"]
            if parrafos:
                o["texto"] = parrafos
            obras.append(o)
    return obras, cats


def leer_parrafos(rel):
    p = None
    for ext in (".txt", ".md", ".docx"):
        cand = CONTENIDO / (rel + ext)
        if cand.exists():
            p = cand
            break
    if not p:
        aviso(f"Falta contenido/{rel}.txt")
        return []
    texto = leer_texto(p).replace("\r\n", "\n")
    return [re.sub(r"\s*\n\s*", " ", x).strip() for x in re.split(r"\n\s*\n", texto) if x.strip()]


def leer_bio():
    carpeta = CONTENIDO / "bio"
    campos, _, parrafos = leer_ficha(buscar_ficha(carpeta, ("bio",)))
    fs = fotos_de(carpeta)
    retrato = guardar_foto(fs[0], "img/retrato.jpg", 1400) if fs else None
    return {"bio": parrafos, "retrato": retrato, "pie": campos.get("pie", "")}


def leer_cv():
    p = next((CONTENIDO / "bio" / ("cv" + e) for e in (".txt", ".md", ".docx") if (CONTENIDO / "bio" / ("cv" + e)).exists()), None)
    if not p:
        aviso("Falta contenido/bio/cv.txt")
        return []
    secciones = []
    for linea in leer_texto(p).replace("\r\n", "\n").split("\n"):
        linea = linea.strip()
        if not linea:
            continue
        if linea.startswith("#"):
            secciones.append([linea.lstrip("#").strip(), []])
        elif "|" in linea and secciones:
            anio, texto = linea.split("|", 1)
            secciones[-1][1].append([anio.strip(), con_italicas(texto.strip())])
        elif secciones:
            secciones[-1][1].append(["", con_italicas(linea)])
    return secciones


def leer_prensa():
    p = next((CONTENIDO / "prensa" / ("prensa" + e) for e in (".txt", ".md", ".docx") if (CONTENIDO / "prensa" / ("prensa" + e)).exists()), None)
    if not p:
        return []
    notas = []
    for bloque in re.split(r"\n\s*\n", leer_texto(p).replace("\r\n", "\n")):
        d = {}
        for linea in bloque.strip().split("\n"):
            m = re.match(r"^([^:]{1,20}):\s*(.*)$", linea.strip())
            if m:
                d[m.group(1).strip().lower()] = m.group(2).strip()
            elif re.match(r"^(https?://|www\.)", linea.strip()):
                d["link"] = linea.strip()
        link = d.get("link") or d.get("enlace") or d.get("url")
        if not link:
            continue
        if not link.startswith("http"):
            link = "https://" + link
        notas.append([d.get("medio", ""), d.get("título") or d.get("titulo") or "Nota", link])
    return notas


def leer_contacto():
    p = next((CONTENIDO / "contacto" / ("contacto" + e) for e in (".txt", ".md", ".docx") if (CONTENIDO / "contacto" / ("contacto" + e)).exists()), None)
    if not p:
        return []
    bloques = []
    for bloque in re.split(r"\n\s*\n", leer_texto(p).replace("\r\n", "\n").strip()):
        lineas = [l.strip() for l in bloque.split("\n") if l.strip()]
        if lineas:
            bloques.append({"titulo": lineas[0].rstrip(":"), "lineas": lineas[1:]})
    return bloques


# ---------- armado ----------

def main():
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    SALIDA.mkdir()

    inicio = leer_inicio()
    muestras, fotos = leer_muestras()
    obras, cats = leer_obras()
    bio = leer_bio()
    datos = {
        "SITIO": {"inicio": inicio, "retrato": bio["retrato"], "pie_retrato": bio["pie"], "contacto": leer_contacto()},
        "MUESTRAS": muestras, "FOTOS": fotos, "OBRAS": obras, "CATS": cats,
        "STATEMENT": leer_parrafos("textos/statement"), "BIO": bio["bio"], "CV": leer_cv(), "PRENSA": leer_prensa(),
    }
    js = "\n".join(f"const {k} = {json.dumps(v, ensure_ascii=False)};" for k, v in datos.items())
    plantilla = (SITIO / "plantilla.html").read_text(encoding="utf-8")
    pagina = plantilla.replace("/*__DATOS__*/", js)
    (SALIDA / "index.html").write_text(pagina, encoding="utf-8")

    dominio = (RAIZ / "CNAME")
    if dominio.exists():
        shutil.copy(dominio, SALIDA / "CNAME")
    (SALIDA / ".nojekyll").write_text("")

    n_fotos = sum(len(v) for v in fotos.values()) + sum(len(o["items"]) for o in obras)
    print(f"Listo: {len(muestras)} muestras, {len(obras)} obras, {n_fotos} fotos.")
    if avisos:
        print(f"{len(avisos)} aviso(s):")
        for a in avisos:
            print(" -", a)
    if "--estricto" in sys.argv and avisos:
        sys.exit(1)


if __name__ == "__main__":
    main()
