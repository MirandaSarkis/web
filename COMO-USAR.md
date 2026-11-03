# Cómo actualizar la web

Todo lo que se ve en **mirandasarkis.com** sale de la carpeta `contenido/`.
Cada vez que subís o cambiás algo ahí, la web se vuelve a armar y publicar sola
en unos 2 o 3 minutos. Podés ver el avance en la pestaña **Actions** del repositorio.

## Dónde va cada cosa

```
contenido/
├── inicio/        portada.jpg + inicio.txt (crédito de la foto y la frase de presentación)
├── muestras/      una carpeta por muestra: "2024. Sostener el fuego"
├── obras/         una carpeta por técnica ("1 Cerámica", "2 Dibujo"…)
│                  y adentro una carpeta por obra o serie: "01 La danza"
├── textos/        statement.txt
├── bio/           bio.txt, cv.txt y retrato.jpg
├── prensa/        prensa.txt
└── contacto/      contacto.txt
```

## Sumar una obra

1. Entrá a la carpeta de la técnica (por ejemplo `contenido/obras/1 Cerámica`).
2. Tocá **Add file → Upload files** y arrastrá las fotos *y* la ficha.
   En "nombre de la carpeta" escribí algo como `31 Nombre de la obra/` antes de los archivos
   (o creá primero la ficha con **Add file → Create new file** escribiendo `31 Nombre de la obra/ficha.txt`).
3. Abajo, tocá **Commit changes**. Listo.

El número del principio de la carpeta (`31`) solo sirve para ordenar: no se ve en la web.

### La ficha

Se llama `ficha.txt` (también sirve un `ficha.docx` de Word) y tiene este formato:

```
Título: La danza
Técnica: Cerámica
Medidas: 17 x 12,5 x 11 cm
Año: 2024
Registro: Francisco Liguori
Formato: Tríptico            (opcional)
---
Acá va el texto de la obra, si tiene. Dejá una línea en blanco entre párrafos.
```

Lo que va debajo de la línea `---` es el texto largo. Si no hay texto, no hace falta la línea.

### Las fotos

- Se ordenan por nombre: `01.jpg`, `02.jpg`, `03.jpg`… La primera es la que aparece en la grilla.
- Si una foto tiene que llevar su propio título debajo (por ejemplo, cada dibujo de una serie),
  nombrala así: `03 El final - Grafito sobre papel - 21 x 15 cm - 2023.jpg`.
- Para un detalle: `04 La danza (detalle).jpg`.
- No hace falta achicarlas: la web las reduce sola. Pero conviene que no pasen de 4 o 5 MB
  para que el repositorio no se llene (el límite recomendado es 1 GB en total).

## Sumar una muestra

Una carpeta en `contenido/muestras/` con el año adelante (`2027. Nombre de la muestra`),
las fotos numeradas y una `ficha.txt`:

```
Título: Nombre de la muestra
Año: 2027
Lugar: Galería, ciudad
Curaduría: Nombre
Texto: Nombre de quien escribió el texto
Registro: Nombre de quien sacó las fotos
Firma: Nombre, mes de 2027
---
El texto de la muestra, en párrafos.
```

Las líneas `Clave: valor` que pongas arriba (Curaduría, Texto, Registro…) aparecen en la ficha
de la muestra en el mismo orden.

### Videos de una muestra

Poné el video en la carpeta de la muestra con el nombre `video.mp4`. Si querés elegir la imagen
que se ve antes de darle play, agregá una foto con el mismo nombre: `video.jpg`.

- Si hay más de uno, nombralos `video.mp4`, `video entrevista.mp4`, etc. Lo que va después de
  "video" aparece como epígrafe ("Entrevista").
- Tienen que pesar menos de 25 MB para subirlos desde la página de GitHub (y nunca más de 100 MB).
  Para videos más largos, subilos a YouTube o Vimeo y agregá en la ficha una línea
  `Video: https://vimeo.com/...`.
- Mejor en formato .mp4: los .mov pueden no verse en todos los navegadores.

## Prensa, CV y contacto

- `prensa/prensa.txt`: una nota por bloque, separadas por una línea en blanco
  (`Medio:`, `Título:`, `Link:`).
- `bio/cv.txt`: cada sección empieza con `#` y cada línea es `año | texto`.
  Para cursiva, rodeá el texto con guiones bajos: `_Sostener el fuego_`.
- `contacto/contacto.txt`: bloques separados por una línea en blanco; la primera línea es el título.

## Si algo no aparece

En **Actions** se ve cada publicación. Si una sale con una cruz roja, abrila: al final
dice qué archivo no se pudo leer. Los avisos (por ejemplo, una obra sin fotos) también aparecen ahí.
