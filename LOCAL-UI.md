# Jarvis Local UI

Interfaz web local para [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) con
estética HUD futurista, streaming de tokens y conexión directa a tu motor local
(Ollama, llama.cpp, etc.).

Este repositorio es una copia de OpenJarvis más la carpeta [`web/`](./web), que
contiene la interfaz y su pequeño backend FastAPI.

> **GitHub Pages:** https://cheche2813.github.io/jarvis-local-ui/
>
> Pages solo puede alojar archivos estáticos. La página carga y se ve completa,
> pero **el agente necesita que el backend Python + Ollama esté ejecutándose en tu
> PC** (o expuesto con un túnel HTTPS). La propia interfaz incluye un engranaje
> para configurar esa URL.

---

## Cómo funciona

```
Navegador (localhost o GitHub Pages)
        │  SSE /api/chat
        ▼
server.py (FastAPI, 127.0.0.1:8765)
        │  SDK de OpenJarvis
        ▼
Ollama (qwen3.5:2b u otro modelo local)
```

- La UI se sirve desde `web/index.html`.
- El backend `web/server.py` usa el SDK de OpenJarvis y hace streaming SSE.
- CORS está limitado a `https://cheche2813.github.io` y `localhost/127.0.0.1`.

## Uso local (recomendado)

1. Asegúrate de tener Ollama activo y el modelo descargado:

   ```powershell
   ollama pull qwen3.5:2b
   ```

2. Arranca el servidor:

   ```powershell
   C:\Users\Cheche\OpenJarvis\web\start-jarvis-ui.cmd
   ```

   O directamente:

   ```powershell
   C:\Users\Cheche\OpenJarvis\src\.venv\Scripts\python.exe C:\Users\Cheche\OpenJarvis\web\server.py
   ```

3. Abre <http://127.0.0.1:8765>. El navegador se abre solo cuando el motor está listo.

## Conectar GitHub Pages con tu PC (túnel)

GitHub Pages no ejecuta Python. Para usar el agente desde la página publicada,
expón el backend local con un túnel HTTPS:

### Cloudflare Tunnel (gratis, sin cuenta para túneles rápidos)

```powershell
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://127.0.0.1:8765
```

Copia la URL `https://algo.trycloudflare.com` que aparece en la consola.

### ngrok

```powershell
ngrok http 8765
```

Copia la URL `https://....ngrok-free.app`.

### En la página de GitHub Pages

1. Abre <https://cheche2813.github.io/jarvis-local-ui/>.
2. Pulsa el engranaje (arriba a la derecha).
3. Pega la URL HTTPS del túnel y pulsa **Guardar y conectar**.
4. Mantén abiertos el servidor local y el túnel mientras uses la página.

También puedes pasar la URL por query string:

```
https://cheche2813.github.io/jarvis-local-ui/?api=https://tu-tunel.trycloudflare.com
```

> La URL se guarda en `localStorage`. Los túneles rápidos cambian de URL cada vez
> que se reinician, así que actualízala cuando haga falta.

## Seguridad

- El túnel expone tu Jarvis local a Internet mientras esté activo. Úsalo solo
  mientras lo necesites y ciérralo después.
- No hay autenticación en el backend: cualquiera con la URL del túnel puede
  hablar con tu agente. Para uso continuado, añade un token o usa Cloudflare
  Access.
- CORS solo acepta el origen de esta página de GitHub Pages y localhost.

## Estructura relevante

| Ruta | Descripción |
| --- | --- |
| `web/index.html` | Interfaz completa (UI, frases mientras piensa, streaming, configuración de backend). |
| `web/server.py` | Backend FastAPI + SSE + CORS. |
| `web/start-jarvis-ui.cmd` | Lanzador de Windows. |
| `.github/upstream-workflows/` | Workflows originales de OpenJarvis, desactivados para evitar que el despliegue de docs sobrescriba esta UI. |

## Publicación en GitHub Pages

Pages se publica desde la rama **`gh-pages`**, que contiene únicamente el
contenido de `web/` en la raíz. No se necesita ningún workflow de Actions.

Para actualizar la página después de cambiar `web/`:

```powershell
git subtree push --prefix web origin gh-pages
```

Si `git subtree` no está disponible, puedes generar la rama así:

```powershell
git subtree split --prefix web -b gh-pages
git push origin gh-pages
```

La rama `main` conserva todo el código de OpenJarvis; `gh-pages` es solo el
artefacto estático que sirve GitHub Pages.

## Notas

- Las frases de "conocimiento general" que aparecen mientras el modelo piensa
  son contenido curado en `index.html`; no las genera el modelo.
- El historial se guarda en el navegador (`localStorage`).
- Probado con Ollama + `qwen3.5:2b` en Windows 11.

## Licencia

El código de OpenJarvis se distribuye bajo Apache 2.0. Consulta [`LICENSE`](./LICENSE).
