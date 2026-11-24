"""Página del celular: HTML ligero, sin recursos externos ni datos personales.

El texto de los casos se inserta con ``textContent`` desde el JSON de la ronda,
nunca como HTML. Cada navegador guarda un identificador aleatorio para votar
una vez por ronda; no se pide nombre, correo ni cuenta.
"""

PAGINA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Feria de los Ecos · Timeless Glitch</title>
<style>
  :root { --fondo:#0d201a; --panel:#173a2e; --borde:#edb957; --crema:#fff3d2; --verde:#82de9e; --rojo:#ff8f86; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--fondo); color:var(--crema); font-family:system-ui, sans-serif;
         min-height:100vh; display:flex; justify-content:center; }
  main { width:100%; max-width:480px; padding:18px 16px 32px; }
  h1 { color:var(--borde); font-size:1.35rem; margin:4px 0 2px; letter-spacing:.04em; }
  .ronda { color:#b9d3c6; font-size:.9rem; margin-bottom:14px; }
  .tablilla { background:#f3e8d6; color:#3a2412; border:4px solid #7a4a24; border-radius:10px; padding:14px; }
  .tablilla h2 { margin:0 0 8px; font-size:1.05rem; color:#6b3a14; }
  .tablilla p { margin:6px 0; line-height:1.35; }
  .fuente { font-size:.92rem; color:#5a3a1c; font-style:italic; }
  h3 { color:var(--borde); margin:20px 0 10px; font-size:1.05rem; }
  .opciones { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .opciones.una { grid-template-columns:1fr; }
  button { font:inherit; font-size:1.05rem; padding:14px 10px; border-radius:10px; border:3px solid var(--borde);
           background:#7a4f2b; color:var(--crema); min-height:54px; }
  button.elegido { background:var(--borde); color:#2a1a0c; font-weight:700; }
  button:disabled { opacity:.45; }
  #enviar { width:100%; margin-top:20px; background:#2f6b4a; border-color:var(--verde); }
  .aviso { margin-top:16px; padding:12px; border-radius:10px; background:var(--panel); text-align:center; }
  .ok { border:3px solid var(--verde); }
  .error { border:3px solid var(--rojo); }
  .sello { font-size:3rem; line-height:1; }
  .oculto { display:none; }
</style>
</head>
<body>
<main>
  <h1>Feria de los Ecos</h1>
  <div class="ronda" id="ronda">Conectando con La Copa…</div>
  <section id="votar" class="oculto">
    <div class="tablilla">
      <h2 id="titulo"></h2>
      <p id="tablilla"></p>
      <p class="fuente" id="fuente"></p>
    </div>
    <h3>1. ¿Qué haces con este mensaje?</h3>
    <div class="opciones" id="decisiones"></div>
    <h3>2. ¿Qué tipo de información es?</h3>
    <div class="opciones una" id="categorias"></div>
    <button id="enviar" disabled>Enviar mi voz</button>
  </section>
  <div id="estado" class="aviso oculto"></div>
</main>
<script>
(function () {
  var base = location.pathname.replace(/\\/$/, "");
  var clave = "tg_feria_dispositivo";
  var dispositivo = null;
  try { dispositivo = localStorage.getItem(clave); } catch (e) {}
  if (!dispositivo) {
    var bytes = new Uint8Array(16);
    (window.crypto || window.msCrypto).getRandomValues(bytes);
    dispositivo = Array.prototype.map.call(bytes, function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
    try { localStorage.setItem(clave, dispositivo); } catch (e) {}
  }
  var ronda = 0, votada = 0, eleccion = {};
  var $ = function (id) { return document.getElementById(id); };

  function aviso(texto, tipo, sello) {
    var caja = $("estado");
    caja.className = "aviso " + (tipo || "");
    caja.textContent = "";
    if (sello) { var s = document.createElement("div"); s.className = "sello"; s.textContent = sello; caja.appendChild(s); }
    var p = document.createElement("div"); p.textContent = texto; caja.appendChild(p);
  }

  function botones(contenedor, opciones, campo) {
    var caja = $(contenedor); caja.textContent = "";
    opciones.forEach(function (op) {
      var b = document.createElement("button");
      b.type = "button"; b.textContent = op[1];
      b.onclick = function () {
        eleccion[campo] = op[0];
        Array.prototype.forEach.call(caja.children, function (x) { x.className = ""; });
        b.className = "elegido";
        $("enviar").disabled = !(eleccion.decision && eleccion.categoria);
      };
      caja.appendChild(b);
    });
  }

  function mostrar(datos) {
    $("ronda").textContent = "Ronda " + datos.ronda + " · " + datos.caso.titulo;
    if (datos.ronda === ronda) {
      if (!datos.abierta && votada !== ronda) { $("votar").className = "oculto"; aviso("La votación se cerró. Mira el resultado en la pantalla grande.", "", "⏳"); }
      return;
    }
    ronda = datos.ronda; eleccion = {};
    $("titulo").textContent = datos.caso.titulo;
    $("tablilla").textContent = datos.caso.tablilla;
    $("fuente").textContent = "Fuente: " + datos.caso.fuente;
    botones("decisiones", datos.decisiones, "decision");
    botones("categorias", datos.categorias, "categoria");
    $("enviar").disabled = true;
    var yaVoto = false;
    try { yaVoto = localStorage.getItem("tg_feria_voto") === base + "#" + ronda; } catch (e) {}
    if (yaVoto) { votada = ronda; $("votar").className = "oculto"; aviso("Ya votaste en esta ronda. ¡Gracias!", "ok", "✓"); }
    else if (datos.abierta) { $("votar").className = ""; $("estado").className = "aviso oculto"; }
    else { $("votar").className = "oculto"; aviso("Espera a que empiece la siguiente ronda.", "", "⏳"); }
  }

  function consultar() {
    fetch(base + "/ronda", { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(mostrar)
      .catch(function () { $("ronda").textContent = "Sin conexión con La Copa. Reintentando…"; });
  }

  $("enviar").onclick = function () {
    $("enviar").disabled = true;
    fetch(base + "/voto", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dispositivo: dispositivo, ronda: ronda, decision: eleccion.decision, categoria: eleccion.categoria }) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok) {
          votada = ronda;
          try { localStorage.setItem("tg_feria_voto", base + "#" + ronda); } catch (e) {}
          $("votar").className = "oculto";
          aviso("¡Voz recibida! Mira cómo responde La Copa en la pantalla grande.", "ok", "✓");
        } else { aviso(res.j.mensaje || "No se pudo registrar tu voz.", "error"); $("enviar").disabled = false; }
      })
      .catch(function () { aviso("Sin conexión. Inténtalo otra vez.", "error"); $("enviar").disabled = false; });
  };

  consultar();
  setInterval(consultar, 3000);
})();
</script>
</body>
</html>
"""
