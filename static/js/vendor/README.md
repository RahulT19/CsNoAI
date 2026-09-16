# Vendored third-party JavaScript

## `chart.min.js`

A **tree-shaken build of Chart.js 4.4.1** containing only the components this
dashboard actually uses, rather than the 200 KB `chart.umd.min.js` distribution
that registers every chart type, scale and plugin.

Registered: `LineController`, `LineElement`, `PointElement`, `LinearScale`,
`CategoryScale`, `Filler`, `Tooltip`. Everything else — bar/pie/radar/bubble
controllers, the time and logarithmic scales, the legend, title, subtitle and
decimation plugins — is excluded by the bundler.

| Build | Raw | Gzipped |
| :--- | ---: | ---: |
| Upstream `chart.umd.min.js` | 200.6 KB | 68.0 KB |
| This build | 156.5 KB | 54.8 KB |

It is **vendored, not fetched from a CDN**, so the dashboard renders with no
internet connection at all — the same reasoning behind the scraper's offline
HTML corpus. It also removes a third-party origin from the page.

### Reproducing it

```bash
npm install chart.js@4.4.1 esbuild
cat > entry.js <<'JS'
import { Chart, LineController, LineElement, PointElement,
         LinearScale, CategoryScale, Filler, Tooltip } from "chart.js";
Chart.register(LineController, LineElement, PointElement,
               LinearScale, CategoryScale, Filler, Tooltip);
window.Chart = Chart;
JS
npx esbuild entry.js --bundle --minify --format=iife --target=es2019 \
  --outfile=static/js/vendor/chart.min.js
```

Chart.js is MIT licensed. See <https://github.com/chartjs/Chart.js>.
