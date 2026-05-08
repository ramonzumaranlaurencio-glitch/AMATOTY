#!/usr/bin/env python3
# Script to write the redesigned docs/index.html
import os

HTML = '''\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AMATOTY \u2013 International Marketplace</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="alternate" hreflang="en" href="en/">
<link rel="alternate" hreflang="es" href="es/">
<link rel="alternate" hreflang="pt" href="pt/">
<link rel="alternate" hreflang="x-default" href="index.html">
<link rel="stylesheet" href="assets/style.css">
<script src="assets/i18n.js"></script>
<style>
:root{
  --navy:#0b2545;--navy-mid:#1d3d6e;--accent:#ff9900;--accent-dark:#c97a00;
  --accent-soft:#febd69;--white:#ffffff;--off-white:#f7f9fc;--muted:#5a6a7e;
  --border:#dde3ec;--ink:#0d1b2a;--radius:14px;
  --shadow:0 4px 24px rgba(11,37,69,.10);
}
/* HERO */
.site-hero{position:relative;width:100%;min-height:520px;border-radius:20px;overflow:hidden;margin-bottom:48px;box-shadow:0 12px 48px rgba(11,37,69,.22);}
.site-hero-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 40%;}
.site-hero-overlay{position:absolute;inset:0;background:linear-gradient(90deg,rgba(11,37,69,.88) 0%,rgba(11,37,69,.65) 55%,rgba(11,37,69,.15) 100%);}
.site-hero-content{position:relative;z-index:2;padding:64px 52px;max-width:640px;}
.site-hero-eyebrow{display:inline-block;background:var(--accent);color:#111;font-size:.78em;font-weight:900;letter-spacing:.12em;text-transform:uppercase;padding:4px 14px;border-radius:6px;margin-bottom:18px;}
.site-hero-content h1{font-size:2.6em;font-weight:900;color:var(--white);margin:0 0 16px;line-height:1.18;}
.site-hero-content p{font-size:1.12em;color:rgba(255,255,255,.88);margin:0 0 30px;line-height:1.7;}
.site-hero-cta{display:inline-flex;align-items:center;gap:10px;background:var(--accent);color:#111;font-weight:900;font-size:1.05em;padding:14px 30px;border-radius:10px;text-decoration:none;box-shadow:0 4px 16px rgba(255,153,0,.40);transition:background .2s,transform .15s;}
.site-hero-cta:hover{background:var(--accent-dark);color:#fff;transform:translateY(-2px);}
.site-hero-sub{margin-top:14px;font-size:.9em;color:rgba(255,255,255,.6);}
/* STATS BAR */
.stats-bar{display:flex;gap:0;margin-bottom:48px;border-radius:var(--radius);overflow:hidden;border:1px solid var(--border);background:var(--white);box-shadow:var(--shadow);}
.stat-item{flex:1;padding:22px 16px;text-align:center;border-right:1px solid var(--border);}
.stat-item:last-child{border-right:none;}
.stat-num{font-size:2em;font-weight:900;color:var(--navy);line-height:1;}
.stat-lbl{font-size:.82em;color:var(--muted);margin-top:4px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;}
/* SECTION */
.sec-title{font-size:1.5em;font-weight:900;color:var(--navy);margin:0 0 6px;}
.sec-sub{font-size:.95em;color:var(--muted);margin:0 0 28px;}
.sec-header{text-align:center;margin-bottom:32px;}
.sec-label{display:inline-block;background:var(--off-white);border:1px solid var(--border);color:var(--navy-mid);font-size:.75em;font-weight:900;letter-spacing:.1em;text-transform:uppercase;padding:4px 12px;border-radius:6px;margin-bottom:10px;}
.site-section{padding:48px 0;border-top:1px solid var(--border);}
/* PROCESS */
.process-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;}
.process-card{background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:22px 18px;text-align:center;box-shadow:var(--shadow);}
.process-icon{font-size:2em;margin-bottom:10px;}
.process-card h3{font-size:.95em;font-weight:900;color:var(--navy);margin:0 0 6px;}
.process-card p{font-size:.83em;color:var(--muted);margin:0;line-height:1.5;}
/* CAROUSEL */
.vc3d-wrap{position:relative;width:100%;max-width:900px;margin:0 auto;}
.vc3d-scene{perspective:1100px;height:420px;position:relative;overflow:hidden;border-radius:16px;}
.vc3d-track{position:absolute;inset:0;transform-style:preserve-3d;}
.vc3d-card{position:absolute;left:50%;width:min(480px,88vw);transform:translateX(-50%);border-radius:16px;overflow:hidden;cursor:pointer;user-select:none;transition:transform .45s cubic-bezier(.4,0,.2,1),opacity .45s,box-shadow .3s;background:var(--white);border:1px solid var(--border);}
.vc3d-card img{width:100%;height:200px;object-fit:cover;display:block;}
.vc3d-card-body{padding:16px 20px 18px;}
.vc3d-card-body h3{margin:0 0 6px;font-size:1em;font-weight:800;color:var(--ink);}
.vc3d-card-body p{margin:0;font-size:.88em;color:var(--muted);line-height:1.45;}
.vc3d-card-body a{display:inline-block;margin-top:12px;background:var(--accent);color:#111;padding:7px 20px;border-radius:8px;font-size:.85em;font-weight:800;text-decoration:none;transition:background .2s;}
.vc3d-card-body a:hover{background:var(--accent-dark);color:#fff;}
.vc3d-nav{display:flex;justify-content:center;gap:12px;margin-top:16px;}
.vc3d-btn{background:var(--navy);color:#fff;border:none;border-radius:50%;width:40px;height:40px;font-size:1.1em;cursor:pointer;transition:background .2s;display:flex;align-items:center;justify-content:center;}
.vc3d-btn:hover{background:var(--accent);color:#111;}
.vc3d-dots{display:flex;justify-content:center;gap:7px;margin-top:10px;}
.vc3d-dot{width:8px;height:8px;border-radius:50%;background:var(--border);cursor:pointer;transition:background .2s;}
.vc3d-dot.active{background:var(--accent);}
/* OYE BONITA */
.ob-banner{display:flex;align-items:center;gap:40px;background:var(--navy);border-radius:var(--radius);padding:40px 44px;box-shadow:var(--shadow);}
.ob-banner-text{flex:1;color:#fff;}
.ob-banner-text h2{font-size:1.6em;font-weight:900;margin:0 0 10px;color:#fff;}
.ob-banner-text p{font-size:1em;color:rgba(255,255,255,.78);margin:0 0 22px;line-height:1.65;}
.ob-banner-text a{display:inline-block;background:var(--accent);color:#111;font-weight:900;padding:12px 28px;border-radius:10px;text-decoration:none;font-size:.95em;transition:background .2s;}
.ob-banner-text a:hover{background:var(--accent-dark);color:#fff;}
.ob-banner-img{flex:0 0 220px;}
.ob-banner-img img{width:100%;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,.28);}
/* BLOG */
.blog-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px;}
.blog-card{background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:22px;box-shadow:var(--shadow);display:flex;flex-direction:column;}
.blog-card h3{font-size:1em;font-weight:800;color:var(--ink);margin:0 0 8px;}
.blog-card p{font-size:.88em;color:var(--muted);margin:0 0 16px;flex:1;line-height:1.5;}
.blog-badge{display:inline-block;padding:3px 10px;border-radius:6px;font-size:.76em;font-weight:900;margin-bottom:10px;}
.badge-red{background:#fee2e2;color:#991b1b;}
.badge-orange{background:#ffedd5;color:#9a3412;}
.badge-green{background:#dcfce7;color:#166534;}
.blog-card a.btn-sm{display:inline-block;background:var(--off-white);border:1px solid var(--border);color:var(--navy);padding:7px 16px;border-radius:8px;font-size:.84em;font-weight:700;text-decoration:none;transition:background .2s;align-self:flex-start;}
.blog-card a.btn-sm:hover{background:var(--navy);color:#fff;}
/* TRUST */
.trust-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;}
.trust-item{display:flex;align-items:flex-start;gap:14px;}
.trust-icon{font-size:1.6em;margin-top:2px;flex-shrink:0;}
.trust-item h4{font-size:.93em;font-weight:900;color:var(--navy);margin:0 0 4px;}
.trust-item p{font-size:.84em;color:var(--muted);margin:0;line-height:1.45;}
/* TESTIMONIAL */
.testimonial-card{background:var(--navy);color:rgba(255,255,255,.9);border-radius:var(--radius);padding:32px 36px;text-align:center;box-shadow:var(--shadow);font-style:italic;font-size:1.08em;line-height:1.7;}
.testimonial-card cite{display:block;margin-top:14px;font-style:normal;font-size:.83em;color:var(--accent-soft);font-weight:700;}
/* COMPARADOR */
.comparador{width:100%;border-collapse:collapse;border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow);}
.comparador th{background:var(--navy);color:#fff;padding:12px 14px;font-size:.85em;letter-spacing:.06em;text-transform:uppercase;}
.comparador td{padding:11px 14px;font-size:.92em;border-top:1px solid var(--border);}
.comparador tr:nth-child(even) td{background:var(--off-white);}
.comparador .highlight td{background:#fff7e6;font-weight:700;}
/* CTA FINAL */
.cta-final{background:linear-gradient(135deg,var(--navy) 0%,var(--navy-mid) 100%);border-radius:var(--radius);padding:48px 40px;text-align:center;box-shadow:var(--shadow);}
.cta-final h2{font-size:1.7em;font-weight:900;color:#fff;margin:0 0 10px;}
.cta-final p{font-size:1em;color:rgba(255,255,255,.75);margin:0 0 26px;}
.cta-final-btns{display:flex;justify-content:center;gap:14px;flex-wrap:wrap;}
.cta-btn-primary{display:inline-block;background:var(--accent);color:#111;font-weight:900;padding:13px 30px;border-radius:10px;text-decoration:none;font-size:.98em;transition:background .2s;}
.cta-btn-primary:hover{background:var(--accent-dark);color:#fff;}
.cta-btn-ghost{display:inline-block;border:2px solid rgba(255,255,255,.35);color:#fff;font-weight:700;padding:12px 28px;border-radius:10px;text-decoration:none;font-size:.98em;transition:border-color .2s,background .2s;}
.cta-btn-ghost:hover{border-color:#fff;background:rgba(255,255,255,.10);}
/* RESPONSIVE */
@media(max-width:700px){
  .site-hero{min-height:380px;}
  .site-hero-content{padding:38px 24px;}
  .site-hero-content h1{font-size:1.7em;}
  .stats-bar{flex-direction:column;}
  .stat-item{border-right:none;border-bottom:1px solid var(--border);}
  .stat-item:last-child{border-bottom:none;}
  .vc3d-scene{height:370px;}
  .vc3d-card img{height:160px;}
  .ob-banner{flex-direction:column;padding:28px 22px;gap:22px;}
  .ob-banner-img{flex:none;width:140px;margin:0 auto;}
  .cta-final{padding:30px 20px;}
}
</style>
<script src="assets/product_ai_guard.js"></script>
<script src="assets/platform_catalog.js"></script>
<script src="assets/banner_carousel.js" defer></script>
</head>
<body data-product="" data-page-title="page_title_home">
<header><h1>AMATOTY</h1><nav>
  <a href="index.html" data-i18n="nav_home">Home</a>
  <a href="category/index.html" data-i18n="nav_categories">Categories</a>
  <a href="smart-search.html" data-i18n="nav_smart_search">Smart Search</a>
  <a href="product-platform.html" data-i18n="nav_product_panel">Product Panel</a>
  <a href="blog/index.html" data-i18n="nav_blog">Blog</a>
  <a href="about.html" data-i18n="nav_about">About us</a>
  <a href="affiliate-disclosure.html">Affiliate disclosure</a>
  <a href="contact.html" data-i18n="nav_contact">Contact</a>
</nav></header>
<main>

<!-- HERO -->
<div class="site-hero">
  <img class="site-hero-img" src="assets/port-hero.png" alt="AMATOTY International Marketplace \u2013 global sourcing and product discovery">
  <div class="site-hero-overlay"></div>
  <div class="site-hero-content">
    <span class="site-hero-eyebrow">International Marketplace</span>
    <h1>Productos reales,<br>analizados con criterio</h1>
    <p>Encontramos los mejores productos del mercado global &mdash; probados, comparados y verificados. Sin publicidad enga&ntilde;osa, solo lo que realmente vale la pena.</p>
    <a href="smart-search.html" class="site-hero-cta">&#128269; Buscar con Smart Search</a>
    <p class="site-hero-sub">M&aacute;s de 500 productos evaluados &middot; Env&iacute;o internacional disponible</p>
  </div>
</div>

<!-- STATS BAR -->
<div class="stats-bar">
  <div class="stat-item"><div class="stat-num">500+</div><div class="stat-lbl">Productos evaluados</div></div>
  <div class="stat-item"><div class="stat-num">3</div><div class="stat-lbl">Idiomas</div></div>
  <div class="stat-item"><div class="stat-num">100%</div><div class="stat-lbl">Reviews honestos</div></div>
  <div class="stat-item"><div class="stat-num">24/7</div><div class="stat-lbl">Disponible global</div></div>
</div>

<div id="catalogBannerCarousel" data-banner-carousel data-banner-fallback="assets/productos.json" data-banner-max="8" style="display:none"></div>

<!-- CAROUSEL VERTICAL 3D -->
<div class="site-section">
  <div class="sec-header">
    <span class="sec-label">Selecci&oacute;n del mes</span>
    <h2 class="sec-title">Productos destacados</h2>
    <p class="sec-sub">Curados por nuestro equipo. Cambia la selecci&oacute;n desde el panel Admin &rarr; Productos &rarr; Carruseles por P&aacute;gina.</p>
  </div>
  <div class="vc3d-wrap" id="vc3d">
    <div class="vc3d-scene" id="vc3dScene" aria-label="Carrusel de productos destacados" role="region">
      <div class="vc3d-track" id="vc3dTrack"></div>
    </div>
    <div class="vc3d-nav">
      <button class="vc3d-btn" id="vc3dPrev" aria-label="Anterior">&#9650;</button>
      <button class="vc3d-btn" id="vc3dNext" aria-label="Siguiente">&#9660;</button>
    </div>
    <div class="vc3d-dots" id="vc3dDots"></div>
  </div>
</div>
<script>
(function(){
  var F=[
    {img:"assets/home.jpg",title:"Oye Bonita \u2013 Diagn\u00f3stico Facial",text:"IA facial: conoce tu tipo de piel y recibe rutina personalizada.",href:"oye-bonita.html"},
    {img:"assets/placeholder.png",title:"Smart Search con IA",text:"Busca cualquier producto con imagen, voz o texto. Resultados globales.",href:"smart-search.html"},
    {img:"assets/kitchen.jpg",title:"Mini Blender Port\u00e1til",text:"Batidos en cualquier lugar. Compacto, recargable y silencioso.",href:"blog/portable-mini-blender-review.html"},
    {img:"assets/placeholder.png",title:"Car Seat Gap Organizer",text:"Nunca m\u00e1s pierdas nada entre los asientos. Dise\u00f1o universal.",href:"blog/car-seat-gap-organizer-review.html"},
    {img:"assets/placeholder.png",title:"Kitchen Food Saver",text:"Conserva alimentos frescos m\u00e1s tiempo. Ahorra dinero.",href:"blog/kitchen-food-saver-gadget-review.html"},
    {img:"assets/placeholder.png",title:"Mini Aspiradora de Escritorio",text:"Limpia teclado y espacios peque\u00f1os al instante. Sin cables.",href:"blog/mini-vacuum-cleaner-review.html"}
  ];
  var AM=3800,tr=document.getElementById("vc3dTrack"),do_=document.getElementById("vc3dDots"),sc=document.getElementById("vc3dScene"),cu=0,ti=null,ty=null;
  function build(C){
    tr.innerHTML="";do_.innerHTML="";
    C.forEach(function(c,i){
      var e=document.createElement("div");e.className="vc3d-card";e.dataset.idx=i;
      e.innerHTML="<img src='"+c.img+"' alt='"+c.title+"' loading='lazy' onerror=\"this.src='assets/placeholder.png'\">"
        +"<div class='vc3d-card-body'><h3>"+c.title+"</h3><p>"+c.text+"</p><a href='"+c.href+"'>Ver m\u00e1s &rarr;</a></div>";
      e.addEventListener("click",function(){goTo(i);});tr.appendChild(e);
      var d=document.createElement("span");d.className="vc3d-dot"+(i===0?" active":"");
      d.addEventListener("click",function(){goTo(i);});do_.appendChild(d);
    });
    var aC=tr.querySelectorAll(".vc3d-card"),aD=do_.querySelectorAll(".vc3d-dot"),tot=C.length;
    function lay(){
      var h=sc.offsetHeight,g=h/2.6;
      aC.forEach(function(card,i){
        var d=i-cu;if(d>tot/2)d-=tot;if(d<-tot/2)d+=tot;
        var a=Math.abs(d),act=d===0;
        card.style.transform="translateX(-50%) translateY("+(h/2-110+d*g)+"px) translateZ("+(act?0:-a*90)+"px) scale("+(act?1:Math.max(.62,1-a*.18))+") rotateY("+(act?0:(d>0?6:-6))+"deg)";
        card.style.opacity=act?1:Math.max(.15,1-a*.35);
        card.style.zIndex=100-a*10;
        card.style.boxShadow=act?"0 16px 48px rgba(11,37,69,.28)":"0 2px 12px rgba(0,0,0,.07)";
      });
      aD.forEach(function(dot,i){dot.classList.toggle("active",i===cu);});
    }
    function goTo(i){cu=((i%tot)+tot)%tot;lay();}
    function nxt(){goTo(cu+1);}function prv(){goTo(cu-1);}
    document.getElementById("vc3dNext").onclick=function(){nxt();rst();};
    document.getElementById("vc3dPrev").onclick=function(){prv();rst();};
    sc.addEventListener("touchstart",function(e){ty=e.touches[0].clientY;},{passive:true});
    sc.addEventListener("touchend",function(e){if(ty===null)return;var dy=e.changedTouches[0].clientY-ty;if(Math.abs(dy)>40){dy<0?nxt():prv();rst();}ty=null;},{passive:true});
    document.addEventListener("keydown",function(e){if(e.key==="ArrowDown"){nxt();rst();}if(e.key==="ArrowUp"){prv();rst();}});
    function strt(){ti=setInterval(nxt,AM);}function rst(){clearInterval(ti);strt();}
    lay();strt();window.addEventListener("resize",lay);
  }
  fetch("assets/carousels.json")
    .then(function(r){return r.ok?r.json():Promise.reject();})
    .then(function(data){var h=(data.home||[]).map(function(c){return{img:c.img||"assets/placeholder.png",title:c.title||"",text:c.text||"",href:c.href||"#"};});build(h.length?h:F);})
    .catch(function(){build(F);});
})();
</script>

<!-- COMO EVALUAMOS -->
<div class="site-section">
  <div class="sec-header">
    <span class="sec-label">Nuestro m&eacute;todo</span>
    <h2 class="sec-title">&iquest;C&oacute;mo evaluamos los productos?</h2>
    <p class="sec-sub">Un proceso riguroso para que solo te lleguen recomendaciones que valen la pena.</p>
  </div>
  <div class="process-grid">
    <div class="process-card"><div class="process-icon">&#128270;</div><h3>Problema real</h3><p>Identificamos necesidades cotidianas con alta demanda.</p></div>
    <div class="process-card"><div class="process-icon">&#128202;</div><h3>Selecci&oacute;n verificada</h3><p>Solo productos con buenas rese&ntilde;as y utilidad comprobada.</p></div>
    <div class="process-card"><div class="process-icon">&#129514;</div><h3>Prueba real</h3><p>Los evaluamos en condiciones de uso cotidiano.</p></div>
    <div class="process-card"><div class="process-icon">&#9878;&#65039;</div><h3>Comparativa honesta</h3><p>Destacamos pros, contras y alternativas disponibles.</p></div>
    <div class="process-card"><div class="process-icon">&#9989;</div><h3>Solo lo mejor</h3><p>Recomendamos lo que usar&iacute;amos en nuestro propio hogar.</p></div>
  </div>
</div>

<!-- TOP PICKS -->
<div class="site-section">
  <div class="sec-header">
    <span class="sec-label">Top del mes</span>
    <h2 class="sec-title">Top picks del mes</h2>
    <p class="sec-sub">Los productos m&aacute;s valorados por nuestra comunidad.</p>
  </div>
  <div id="top-picks-list" class="grid"></div>
</div>

<!-- OYE BONITA -->
<div class="site-section">
  <div class="ob-banner">
    <div class="ob-banner-text">
      <h2>&#10024; Oye Bonita &mdash; Diagn&oacute;stico Facial IA</h2>
      <p>Sube tu foto, descubre tu tipo de piel y recibe una rutina de belleza personalizada. Una asesora digital que trabaja para ti las 24 horas.</p>
      <a href="oye-bonita.html">Probar ahora &mdash; es gratis</a>
    </div>
    <div class="ob-banner-img">
      <img src="assets/home.jpg" alt="Oye Bonita diagn&oacute;stico facial con IA">
    </div>
  </div>
</div>

<!-- PRO RECOMMENDATION -->
<div class="site-section" style="display:none" id="pro-section">
  <div class="sec-header">
    <span class="sec-label">Recomendaci&oacute;n PRO</span>
    <h2 class="sec-title">Soluci&oacute;n real a un problema actual</h2>
  </div>
  <div id="pro-recommendation" class="producto-recomendado" style="max-width:480px;margin:0 auto;"></div>
</div>
<script>
PlatformCatalog.hydrateHome({fallbackUrl:"assets/trending_products.json",limit:24});
document.getElementById("pro-recommendation").addEventListener("DOMSubtreeModified",function(){
  if(this.children.length>0)document.getElementById("pro-section").style.display="";
},{once:true});
</script>

<!-- COMPARADOR -->
<div class="site-section">
  <div class="sec-header">
    <span class="sec-label">Comparativa r&aacute;pida</span>
    <h2 class="sec-title">&iquest;Cu&aacute;l producto es para ti?</h2>
  </div>
  <table class="comparador">
    <thead><tr><th>Producto</th><th>Mejor para</th><th>Problema que resuelve</th><th>Categor&iacute;a</th></tr></thead>
    <tbody>
      <tr class="highlight"><td><strong>Portable Mini Blender</strong></td><td>Salud y practicidad</td><td>Batidos en cualquier lugar</td><td>Cocina</td></tr>
      <tr><td>Car Seat Gap Organizer</td><td>Organizaci&oacute;n en el auto</td><td>Objetos que caen entre asientos</td><td>Autom&oacute;vil</td></tr>
      <tr><td>Kitchen Food Saver Gadget</td><td>Ahorro y orden</td><td>Desperdicio de comida</td><td>Cocina</td></tr>
      <tr><td>Home Cable Organizer</td><td>Escritorio limpio</td><td>Cables sueltos y desorden</td><td>Hogar</td></tr>
    </tbody>
  </table>
</div>

<!-- BLOG -->
<div class="site-section">
  <div class="sec-header">
    <span class="sec-label">Blog</span>
    <h2 class="sec-title">&Uacute;ltimos an&aacute;lisis</h2>
    <p class="sec-sub">Reviews detallados con pruebas reales y comparativas honestas.</p>
  </div>
  <div class="blog-grid">
    <div class="blog-card">
      <span class="blog-badge badge-red">&#11088; Recomendado</span>
      <h3>Portable Mini Blender</h3>
      <p>Ideal para quienes buscan salud y rapidez. Compacto, USB recargable, 300ml.</p>
      <a class="btn-sm" href="blog/portable-mini-blender-review.html">Leer an&aacute;lisis &rarr;</a>
    </div>
    <div class="blog-card">
      <span class="blog-badge badge-orange">&#128293; M&aacute;s vendido</span>
      <h3>Car Seat Gap Organizer</h3>
      <p>Evita perder objetos entre los asientos. Universal, f&aacute;cil instalaci&oacute;n.</p>
      <a class="btn-sm" href="blog/car-seat-gap-organizer-review.html">Leer an&aacute;lisis &rarr;</a>
    </div>
    <div class="blog-card">
      <span class="blog-badge badge-green">&#128176; Ahorro</span>
      <h3>Kitchen Food Saver Gadget</h3>
      <p>Reduce el desperdicio de comida hasta un 30%. Apto para refrigerador.</p>
      <a class="btn-sm" href="blog/kitchen-food-saver-gadget-review.html">Leer an&aacute;lisis &rarr;</a>
    </div>
  </div>
</div>

<!-- GALLERY -->
<div class="site-section" id="gallery-section" style="display:none">
  <div class="sec-header"><span class="sec-label">Galer&iacute;a</span><h2 class="sec-title">Galer&iacute;a verificada de productos</h2></div>
  <div id="product-gallery" class="grid"></div>
</div>
<script>
document.getElementById("product-gallery").addEventListener("DOMSubtreeModified",function(){
  if(this.children.length>0)document.getElementById("gallery-section").style.display="";
},{once:true});
</script>

<!-- TESTIMONIAL -->
<div class="site-section">
  <div class="testimonial-card">
    &ldquo;Probamos el organizador de cables y realmente mi escritorio se ve m&aacute;s limpio. Las comparativas son honestas y el an&aacute;lisis es detallado. &iexcl;Recomendado!&rdquo;
    <cite>&mdash; Lector verificado &middot; Lima, Per&uacute;</cite>
  </div>
</div>

<!-- TRUST -->
<div class="site-section">
  <div class="sec-header">
    <span class="sec-label">Transparencia</span>
    <h2 class="sec-title">&iquest;Por qu&eacute; confiar en AMATOTY?</h2>
  </div>
  <div class="trust-grid">
    <div class="trust-item"><span class="trust-icon">&#128300;</span><div><h4>Solo productos probados</h4><p>Evaluamos cada producto antes de publicar cualquier recomendaci&oacute;n.</p></div></div>
    <div class="trust-item"><span class="trust-icon">&#128203;</span><div><h4>Comparativas honestas</h4><p>Sin publicidad encubierta. Mostramos pros, contras y alternativas.</p></div></div>
    <div class="trust-item"><span class="trust-icon">&#128260;</span><div><h4>Actualizaciones semanales</h4><p>El cat&aacute;logo se actualiza constantemente con nuevos an&aacute;lisis.</p></div></div>
    <div class="trust-item"><span class="trust-icon">&#128100;</span><div><h4>Reviewed by Edwin Sumaran</h4><p>Product Research &amp; Practical Reviews &middot; Experiencia verificada.</p></div></div>
  </div>
</div>

<!-- CTA FINAL -->
<div class="site-section">
  <div class="cta-final">
    <h2>&iquest;Listo para comprar mejor?</h2>
    <p>Explora nuestro cat&aacute;logo, usa el buscador inteligente o revisa el blog para encontrar el producto perfecto para ti.</p>
    <div class="cta-final-btns">
      <a href="category/index.html" class="cta-btn-primary">Ver categor&iacute;as</a>
      <a href="smart-search.html" class="cta-btn-ghost">Smart Search &rarr;</a>
    </div>
  </div>
</div>

</main>
<footer>
  <p>As an Amazon Associate, I earn from qualifying purchases.</p>
  <p>Author: Edwin Sumaran &middot; AMATOTY International Marketplace</p>
</footer>
<script src="assets/lca_tracker.js"></script>
<script src="assets/ai_chat.js" defer></script>
</body>
</html>
'''

out = os.path.join(os.path.dirname(__file__), 'docs', 'index.html')
with open(out, 'w', encoding='utf-8', newline='\n') as f:
    f.write(HTML)
print(f'Written {len(HTML)} chars to {out}')
print('Has BOM:', HTML.startswith('\ufeff'))
