1. El Método del Codo (Elbow Method)
Explicación sencilla (¿Qué significa?): Imagina que tienes que organizar la ropa de tu clóset. Si la separas en 1 sola pila gigante, no te sirve de nada. Si haces 50 pilas pequeñas (una por cada playera), tampoco es práctico. El método del codo te ayuda a encontrar el número ideal de pilas. Graficas una línea y, en el punto donde la curva se dobla como un "codo" (en tu caso dio 4), ese es el número perfecto de grupos: Experto, Avanzado, Intermedio y Básico.
Tecnología que se usa:
Lógica: La librería de Machine Learning scikit-learn en Python (usando el algoritmo KMeans y su propiedad .inertia_).
Gráfico: La librería de dibujo matplotlib (para trazar la línea).
Tema de Minería de Datos:
Búsqueda de hiperparámetros en Aprendizaje No Supervisado: Como la computadora no sabe de antemano qué grupos existen, este método le ayuda a definir la estructura del modelo estadístico de forma automatizada.

2. Coeficiente de Silueta (Silhouette Score)
Explicación sencilla (¿Qué significa?): Es el control de calidad de tus grupos. Mide qué tan bien acomodado está cada alumno. Si pusiste a un alumno con bajas calificaciones en el grupo de los "Expertos", la silueta bajará porque ese alumno está fuera de lugar. Queremos que el promedio de esta gráfica sea lo más cercano a 1 (que significa que todos están perfectamente ubicados con sus iguales y lejos de los otros grupos).
Tecnología que se usa:
scikit-learn (usando la función silhouette_score()).
Tema de Minería de Datos:
Validación de modelos de Clustering: En minería de datos no basta con agrupar; necesitas comprobar científicamente si los grupos creados tienen sentido o si el algoritmo mezcló cosas que no debía.

3. Visualización en 2D con PCA (Análisis de Componentes Principales)
Explicación sencilla (¿Qué significa?): Tus estudiantes tienen calificaciones en muchas materias (Matemáticas, Programación, BD, etc.). No podemos hacer una gráfica de 4 o 5 dimensiones porque nuestros ojos solo ven en 2D (alto y ancho). PCA es como tomarle una foto desde arriba a esos datos y proyectar la sombra en una hoja de papel (2D) sin perder la información más importante. En esta gráfica ves a tus alumnos como puntitos de 4 colores diferentes agrupados en "manchas" separadas.
Tecnología que se usa:
scikit-learn (clase PCA para achicar las dimensiones) y matplotlib / seaborn (para pintar los puntitos de colores en la pantalla).
Tema de Minería de Datos:
Reducción de dimensionalidad: Es una técnica clave cuando tienes bases de datos con muchas columnas (variables) y necesitas simplificarlas para poder analizarlas, limpiarlas o graficarlas.

4. Silhouette Plot (Gráfico de Silueta por grupo)
Explicación sencilla (¿Qué significa?): En lugar de darte un promedio general de todo el salón, esta gráfica te muestra el detalle grupo por grupo. Si el bloque del grupo Experto es ancho y va hacia la derecha, significa que sus alumnos son muy parecidos entre sí (grupo muy unido). Si ves barras apuntando hacia la izquierda (valores negativos), significa que esos alumnos específicos están mal agrupados y se parecen más a otro perfil.
Tecnología que se usa:
scikit-learn (método silhouette_samples()) y matplotlib.
Tema de Minería de Datos:
Análisis de Cohesión y Separación: Evaluar la densidad y pureza interna de cada segmento de datos obtenido.

5. Mapa de calor de centroides (Heatmap)
Explicación sencilla (¿Qué significa?): Es una tabla coloreada que te dice qué tan lejos están los grupos entre sí. Por ejemplo, te confirma con números que el centro del grupo Experto está a una distancia muy grande (color rojo intenso) del centro del grupo Básico, mientras que el grupo Avanzado está más cerca (color amarillo/claro) del grupo Intermedio.
Tecnología que se usa:
La librería seaborn (usando la función heatmap()).
Tema de Minería de Datos:
Medidas de Similitud y Distancia: En minería de datos, casi todo se resuelve midiendo distancias. Este gráfico te permite interpretar qué tan diferentes son los patrones que la computadora descubrió.