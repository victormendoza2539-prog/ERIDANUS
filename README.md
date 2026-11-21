ERIDANUS — Gabinete de Curiosidades

Proyecto 3: Tienda Full-Stack con Persistencia CSV, Pandas y Dashboard

Proyecto académico desarrollado para la materia de Programación IV.

Descripción

ERIDANUS es una tienda virtual de artículos científicos, históricos y educativos, inspirada en los antiguos gabinetes de curiosidades.

Su catálogo incluye instrumentos astronómicos, modelos paleontológicos, artículos de exploración geográfica, maquetas arqueológicas, materiales didácticos y coleccionables.

El proyecto integra una API REST desarrollada con FastAPI, persistencia de datos en archivos CSV, análisis de ventas mediante Pandas y un dashboard interactivo construido con Chart.js.

Tecnologías utilizadas

Python: lenguaje de programación del backend.

FastAPI: desarrollo de la API REST.

Pandas: procesamiento y análisis de ventas.

CSV: almacenamiento persistente del inventario y las transacciones.

HTML5: estructura de la interfaz.

CSS3: diseño y personalización visual.

JavaScript: interacción con el usuario.

Fetch API: comunicación entre frontend y backend.

Chart.js: visualización de indicadores y gráficas.

Funcionalidades

1. Catálogo de productos

Consulta de productos desde la API.

Visualización de nombres, categorías, descripciones, precios y existencias.

Búsqueda de artículos por nombre.

Filtrado por categorías.

Compra de productos desde la interfaz.

2. Administración del inventario

Registro de nuevos productos.

Consulta del inventario.

Eliminación de productos.

Actualización automática de existencias después de cada compra.

Persistencia del inventario en productos.csv.

3. Registro de ventas

Cada compra genera una transacción que se almacena en ventas.csv, incluyendo fecha, producto, precio, cantidad e importe total.

El sistema verifica las existencias antes de procesar la compra.

4. Análisis de datos con Pandas

El backend procesa el historial de ventas para calcular:

Ingresos acumulados.

Número de transacciones.

Unidades vendidas.

Ticket promedio.

Producto más vendido.

Ingresos por producto.

Ingresos por categoría.

5. Observatorio de ERIDANUS

Dashboard interactivo que presenta:

Tarjetas con indicadores de ventas.

Gráfica de barras de ingresos por producto.

Gráfica de dona de ingresos por categoría.

Actualización de datos mediante Fetch API.

Actualización de las gráficas después de realizar compras.

Estructura del proyecto

ERIDANUS/
├── main.py
├── analitica.py
├── productos.csv
├── ventas.csv
├── fuentes_productos.csv
├── index.html
├── app.js
├── styles.css
├── locustfile.py
├── requirements.txt
├── README.md
├── .gitignore
└── img/

La carpeta img/ se utilizará para almacenar las fotografías del catálogo.

Instalación

1. Clonar el repositorio

git clone https://github.com/victormendoza2539-prog/ERIDANUS.git
cd ERIDANUS

2. Instalar las dependencias

Es necesario contar con Python instalado.

python -m pip install -r requirements.txt

3. Iniciar FastAPI

uvicorn main:app --reload

La API estará disponible en:

http://127.0.0.1:8000

La documentación interactiva de Swagger se encuentra en:

http://127.0.0.1:8000/docs

4. Ejecutar la tienda

Abrir index.html utilizando la extensión Live Server de Visual Studio Code.

Mantener FastAPI en ejecución mientras se utiliza la interfaz.

La conexión del frontend está configurada para consultar la API local en el puerto 8000.

Endpoints principales

Método

Endpoint

Descripción

GET

/productos

Consultar catálogo

GET

/productos/{producto_id}

Consultar producto

POST

/productos

Registrar producto

POST

/productos/{producto_id}

Comprar producto

DELETE

/productos/{producto_id}

Eliminar producto

GET

/analitica/resumen

Consultar indicadores

GET

/analitica/por-producto

Analizar ventas por producto

GET

/analitica/por-categoria

Analizar ventas por categoría

Persistencia de datos

El proyecto utiliza dos archivos principales:

productos.csv almacena la información del catálogo y las existencias.

ventas.csv conserva el historial de transacciones, utilizado posteriormente por Pandas.

El inventario se mantiene después de reiniciar el servidor.

Pruebas realizadas

Durante el desarrollo se verificaron:

Consulta de productos desde FastAPI.

Registro de compras y descuento de existencias.

Persistencia de datos después de reiniciar el servidor.

Creación y eliminación de productos desde la interfaz.

Cálculo de indicadores mediante Pandas.

Visualización de ventas de distintas categorías en Chart.js.

Estado del proyecto

El sistema cuenta con las funcionalidades principales implementadas. La documentación de precios comerciales y la incorporación de fotografías al catálogo se encuentran en desarrollo.

Autoría

Proyecto académico de Programación IV.

Repositorio: https://github.com/victormendoza2539-prog/ERIDANUS