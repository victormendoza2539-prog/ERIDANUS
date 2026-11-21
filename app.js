const API_URL = "http://127.0.0.1:8000/productos";
const API_BASE = "http://127.0.0.1:8000";
const catalogo = document.getElementById("catalogo");
const tablaProductos = document.getElementById("tablaProductos");
const totalProductos = document.getElementById("totalProductos");
const formProducto = document.getElementById("formProducto");
const filtroCategoria = document.getElementById("filtroCategoria");
const busqueda = document.getElementById("busqueda");
const mensaje = document.getElementById("mensaje");
let productos = [];
let graficaProductos = null;
let graficaCategorias = null;
const moneda = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function avisar(texto, error = false) {
  mensaje.textContent = texto;
  mensaje.classList.toggle("error", error);
}

async function solicitar(url, opciones) {
  const respuesta = await fetch(url, opciones);
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    const detalle = typeof datos.detail === "string" ? datos.detail : `Error HTTP ${respuesta.status}`;
    throw new Error(detalle);
  }
  return datos;
}

async function cargarProductos() {
  try {
    productos = await solicitar(API_URL);
    totalProductos.textContent = `${productos.length} productos`;
    const actual = filtroCategoria.value;
    const categorias = [...new Set(productos.map(p => p.categoria).filter(Boolean))].sort();
    filtroCategoria.replaceChildren(new Option("Todas las categorías", ""), ...categorias.map(c => new Option(c, c)));
    filtroCategoria.value = categorias.includes(actual) ? actual : "";
    mostrarCatalogo();
    mostrarInventario();
  } catch (error) {
    avisar(`No se pudo conectar con FastAPI: ${error.message}`, true);
  }
}

function mostrarCatalogo() {
  catalogo.replaceChildren();
  const texto = busqueda.value.trim().toLocaleLowerCase("es");
  const visibles = productos.filter(p => (!filtroCategoria.value || p.categoria === filtroCategoria.value) &&
    `${p.nombre} ${p.descripcion || ""}`.toLocaleLowerCase("es").includes(texto));
  if (!visibles.length) {
    const vacio = document.createElement("p");
    vacio.textContent = "No hay productos que coincidan con la búsqueda.";
    catalogo.append(vacio);
    return;
  }
  for (const p of visibles) {
    const tarjeta = document.createElement("article");
    tarjeta.className = "product-card";
    const imagen = document.createElement("div");
    imagen.className = "product-image";
    const placeholder = document.createElement("span");
    placeholder.className = "image-placeholder";
    placeholder.textContent = "✦";
    imagen.append(placeholder);
    if (p.imagen && /^img\/[a-zA-Z0-9_./-]+$/.test(p.imagen) && !p.imagen.includes("..")) {
      const foto = document.createElement("img");
      foto.src = p.imagen;
      foto.alt = p.nombre;
      foto.loading = "lazy";
      foto.addEventListener("load", () => placeholder.remove());
      foto.addEventListener("error", () => foto.remove());
      imagen.append(foto);
    }
    const cuerpo = document.createElement("div");
    cuerpo.className = "product-body";
    const categoria = document.createElement("span");
    categoria.className = "category";
    categoria.textContent = p.categoria || "Curiosidades";
    const titulo = document.createElement("h3");
    titulo.textContent = p.nombre;
    const descripcion = document.createElement("p");
    descripcion.className = "description";
    descripcion.textContent = p.descripcion || "Una pieza singular de nuestra colección.";
    const pie = document.createElement("div");
    pie.className = "product-footer";
    const precio = document.createElement("span");
    precio.className = "price";
    precio.textContent = moneda.format(p.precio);
    const stock = document.createElement("span");
    stock.className = "stock";
    stock.textContent = `${p.cantidad} disponibles`;
    pie.append(precio, stock);
    const comprar = document.createElement("button");
    comprar.className = "btn primary";
    comprar.textContent = p.cantidad > 0 ? "Comprar 1 unidad" : "Agotado";
    comprar.disabled = p.cantidad <= 0;
    comprar.addEventListener("click", () => comprarProducto(p.id, comprar));
    cuerpo.append(categoria, titulo, descripcion, pie, comprar);
    tarjeta.append(imagen, cuerpo);
    catalogo.append(tarjeta);
  }
}

function mostrarInventario() {
  tablaProductos.replaceChildren();
  for (const p of productos) {
    const fila = document.createElement("tr");
    for (const valor of [p.id, p.nombre, moneda.format(p.precio), p.cantidad]) {
      const celda = document.createElement("td");
      celda.textContent = valor;
      fila.append(celda);
    }
    const acciones = document.createElement("td");
    const boton = document.createElement("button");
    boton.className = "btn danger";
    boton.textContent = "Eliminar";
    boton.addEventListener("click", () => eliminarProducto(p.id, p.nombre));
    acciones.append(boton);
    fila.append(acciones);
    tablaProductos.append(fila);
  }
}

async function comprarProducto(id, boton) {
  if (!confirm("¿Confirmas la compra de una unidad?")) return;
  boton.disabled = true;
  try {
    const resultado = await solicitar(`${API_URL}/${id}?cantidad=1`, { method: "POST" });
    avisar(`Compra registrada. Total: ${moneda.format(resultado.venta.total)}. ¡Gracias!`);
    await Promise.all([cargarProductos(), cargarObservatorio()]);
  } catch (error) {
    avisar(`No se pudo realizar la compra: ${error.message}`, true);
    boton.disabled = false;
  }
}

formProducto.addEventListener("submit", async event => {
  event.preventDefault();
  const nuevo = {
    nombre: document.getElementById("nombre").value.trim(),
    categoria: document.getElementById("categoria").value.trim() || "Curiosidades",
    precio: Number(document.getElementById("precio").value),
    cantidad: Number(document.getElementById("cantidad").value),
    descripcion: document.getElementById("descripcion").value.trim(),
    imagen: document.getElementById("imagen").value.trim()
  };
  try {
    await solicitar(API_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(nuevo) });
    formProducto.reset();
    avisar("Producto agregado correctamente.");
    await cargarProductos();
  } catch (error) {
    avisar(`No se pudo guardar: ${error.message}`, true);
  }
});

async function eliminarProducto(id, nombre) {
  if (!confirm(`¿Eliminar definitivamente «${nombre}» del inventario?`)) return;
  try {
    await solicitar(`${API_URL}/${id}`, { method: "DELETE" });
    avisar("Producto eliminado correctamente.");
    await cargarProductos();
  } catch (error) {
    avisar(`No se pudo eliminar: ${error.message}`, true);
  }
}

filtroCategoria.addEventListener("change", mostrarCatalogo);
busqueda.addEventListener("input", mostrarCatalogo);
document.addEventListener("DOMContentLoaded", () => {
  cargarProductos();
  cargarObservatorio();
});
document.getElementById("actualizarObservatorio").addEventListener("click", cargarObservatorio);

async function cargarObservatorio() {
  const estado = document.getElementById("mensajeObservatorio");
  estado.textContent = "Actualizando indicadores…";
  estado.classList.remove("error");
  try {
    const [resumen, porProducto, porCategoria] = await Promise.all([
      solicitar(`${API_BASE}/analitica/resumen`),
      solicitar(`${API_BASE}/analitica/por-producto`),
      solicitar(`${API_BASE}/analitica/por-categoria`)
    ]);
    document.getElementById("kpiIngresos").textContent = moneda.format(resumen.ingresos_totales);
    document.getElementById("kpiTransacciones").textContent = resumen.transacciones;
    document.getElementById("kpiUnidades").textContent = resumen.unidades_vendidas;
    document.getElementById("kpiTicket").textContent = moneda.format(resumen.ticket_promedio);
    const lider = resumen.producto_mas_vendido;
    document.getElementById("kpiEstrella").textContent = lider ? `${lider.nombre} · ${lider.unidades} unidades` : "Sin ventas todavía";
    if (typeof Chart === "undefined") {
      throw new Error("Chart.js no se cargó. Comprueba tu conexión a Internet.");
    }
    // Es obligatorio destruir la instancia previa antes de crear otra.
    if (graficaProductos) { graficaProductos.destroy(); graficaProductos = null; }
    if (graficaCategorias) { graficaCategorias.destroy(); graficaCategorias = null; }
    const barras = porProducto.slice(0, 10);
    graficaProductos = new Chart(document.getElementById("graficaProductos"), {
      type: "bar",
      data: {
        labels: barras.map(p => p.producto),
        datasets: [{ label: "Ingresos (MXN)", data: barras.map(p => p.ingresos), backgroundColor: "#244f42", borderRadius: 5 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { callback: valor => moneda.format(valor) } }, x: { ticks: { maxRotation: 45, minRotation: 0 } } } }
    });
    graficaCategorias = new Chart(document.getElementById("graficaCategorias"), {
      type: "doughnut",
      data: {
        labels: porCategoria.map(c => c.categoria),
        datasets: [{ label: "Ingresos (MXN)", data: porCategoria.map(c => c.ingresos),
          backgroundColor: ["#244f42", "#b39252", "#638a77", "#a46c55", "#7089a0", "#9b879e", "#c6bca7"] }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } }
    });
    estado.textContent = resumen.transacciones ? "Indicadores actualizados con el historial de ventas." : "Todavía no hay ventas; las gráficas se llenarán con las primeras compras.";
  } catch (error) {
    estado.textContent = `No se pudo actualizar el Observatorio: ${error.message}`;
    estado.classList.add("error");
  }
}
