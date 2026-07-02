# Clustering (Agrupamiento No Supervisado)
Algoritmo K-Means: Lo utilizaste para segmentar de 
forma automática al grupo de estudiantes en 4 clusters 
o perfiles de desempeño (Experto, Avanzado, Intermedio, Básico) 
según la similitud en la distancia de sus calificaciones.

Método del Codo (Elbow Method): Graficaste la Inercia 
(la suma de las distancias al cuadrado dentro de cada cluster) 
para diferentes valores de $K$. Buscaste el punto donde la curva 
se flexiona ("el codo") para justificar matemáticamente por 
qué el número óptimo de grupos era 4.

Coeficiente de Silueta (Silhouette Score): Métrica matemática de 
validación de clustering. Mide qué tan bien agrupado está un 
alumno respecto a su cluster (cohesión) y qué tan alejado 
está del cluster vecino (separación).

## ¿Por qué es No Supervisado?
No hay etiquetas previas: El algoritmo no recibe datos de entrenamiento 
etiquetados (es decir, al algoritmo no se le enseña de antemano 
qué estudiantes son "Expertos" o "Básicos").

## K-MEANS
Se inicializa de forma aleatoria: El algoritmo selecciona puntos de partida 
(centroides) al azar dentro del espacio de datos.
Pesa por distancia: Asigna cada punto de dato al centroide más 
cercano (generalmente usando distancia euclidiana).
Re-calcula el centro: Una vez asignados los puntos, se recalcula la 
posición del centroide como el promedio de todos los puntos 
asignados a ese grupo.
Itera: Repite los pasos 2 y 3 hasta que los centroides dejen de moverse 
o se alcance un número máximo de iteraciones.
Resultado: Los datos quedan particionados en $K$ grupos (clusters), 
donde cada grupo tiene una "cohesión" interna (puntos similares) 
y una "separación" externa (distante de otros grupos).