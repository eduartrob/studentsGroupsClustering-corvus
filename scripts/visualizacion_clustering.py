# -*- coding: utf-8 -*-
"""
Módulo de Visualización y Validación de Clustering K-Means
Creado para: Visualizar y validar los resultados del agrupamiento de alumnos.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, silhouette_samples, pairwise_distances

def generar_visualizaciones_clustering(X, labels, perfiles=None, save_path="visualizaciones_clustering.png"):
    """
    Genera un dashboard de visualizaciones para validar y analizar un clustering de K-Means.
    
    Parámetros:
    -----------
    X : array-like o DataFrame de forma (n_muestras, n_características)
        El dataset de entrada (ej. calificaciones de materias).
    labels : array-like de forma (n_muestras,)
        Las etiquetas de cluster asignadas a cada muestra.
    perfiles : list, opcional
        Nombres de los perfiles correspondientes a los clusters 0, 1, 2, 3.
        Por defecto es ["Experto", "Avanzado", "Intermedio", "Básico"].
    save_path : str, opcional
        Ruta donde se guardará la imagen del dashboard.
    """
    if perfiles is None:
        perfiles = ["Experto (0)", "Avanzado (1)", "Intermedio (2)", "Básico (3)"]
    else:
        # Asegurar que tengan el número del cluster
        perfiles = [f"{p} ({i})" for i, p in enumerate(perfiles)]

    # Convertir X a numpy array si es DataFrame
    X_arr = np.asarray(X)
    n_samples, n_features = X_arr.shape
    n_clusters = len(np.unique(labels))

    # Configuración de estilos y paleta premium
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 13,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'figure.titlesize': 16,
        'font.family': 'sans-serif'
    })
    
    # Paleta de colores premium (Experto=Indigo, Avanzado=Emerald, Intermedio=Amber, Básico=Rose)
    colors = ['#1e3a8a', '#10b981', '#f59e0b', '#f43f5e']
    if n_clusters > len(colors):
        colors = sns.color_palette("muted", n_clusters)
    else:
        colors = colors[:n_clusters]

    # Crear figura y subplots (3 filas x 2 columnas)
    fig, axes = plt.subplots(3, 2, figsize=(15, 18))
    fig.suptitle("Dashboard de Validación y Visualización de Clustering de Estudiantes", y=0.98, fontweight='bold')

    # -------------------------------------------------------------------------
    # 1. MÉTODO DEL CODO (Elbow Method)
    # -------------------------------------------------------------------------
    ax_elbow = axes[0, 0]
    inertias = []
    k_range = range(1, 11)
    
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_arr)
        inertias.append(km.inertia_)
        
    ax_elbow.plot(k_range, inertias, marker='o', color='#4f46e5', linewidth=2.5, markersize=8, label='Inercia')
    
    # Resaltar el punto K=n_clusters (codo)
    if n_clusters in k_range:
        idx = n_clusters - 1
        ax_elbow.scatter(n_clusters, inertias[idx], color='#dc2626', s=200, zorder=5, 
                          edgecolors='black', linewidth=2, label=f'K={n_clusters} Seleccionado')
        ax_elbow.annotate(f'Codo (K={n_clusters})', 
                          xy=(n_clusters, inertias[idx]), 
                          xytext=(n_clusters + 1, inertias[idx] + (max(inertias)*0.1)),
                          arrowprops=dict(facecolor='black', shrink=0.08, width=1, headwidth=6))

    ax_elbow.set_title("1. Método del Codo para Selección de K", fontweight='bold', pad=10)
    ax_elbow.set_xlabel("Número de Clusters (K)")
    ax_elbow.set_ylabel("Inercia (Suma de distancias al cuadrado)")
    ax_elbow.set_xticks(k_range)
    ax_elbow.legend()

    # -------------------------------------------------------------------------
    # 2. COEFICIENTE DE SILUETA (Silhouette Score vs K)
    # -------------------------------------------------------------------------
    ax_sil_k = axes[0, 1]
    sil_scores = []
    k_range_sil = range(2, 11)
    
    for k in k_range_sil:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_arr)
        score = silhouette_score(X_arr, km.labels_)
        sil_scores.append(score)
        
    ax_sil_k.plot(k_range_sil, sil_scores, marker='s', color='#06b6d4', linewidth=2.5, markersize=8, label='Silueta Promedio')
    
    # Resaltar el punto K=n_clusters
    if n_clusters in k_range_sil:
        idx_sil = n_clusters - 2
        ax_sil_k.scatter(n_clusters, sil_scores[idx_sil], color='#dc2626', s=200, zorder=5, 
                          edgecolors='black', linewidth=2, label=f'K={n_clusters} (Score: {sil_scores[idx_sil]:.3f})')
        ax_sil_k.annotate(f'K={n_clusters}\nScore: {sil_scores[idx_sil]:.3f}', 
                          xy=(n_clusters, sil_scores[idx_sil]), 
                          xytext=(n_clusters + 1, sil_scores[idx_sil] - 0.05),
                          arrowprops=dict(facecolor='black', shrink=0.08, width=1, headwidth=6))
                          
    ax_sil_k.set_title("2. Coeficiente de Silueta por Número de Clusters", fontweight='bold', pad=10)
    ax_sil_k.set_xlabel("Número de Clusters (K)")
    ax_sil_k.set_ylabel("Silhouette Score (Coeficiente de Silueta)")
    ax_sil_k.set_xticks(k_range_sil)
    ax_sil_k.legend()

    # -------------------------------------------------------------------------
    # 3. VISUALIZACIÓN 2D DE CLUSTERS CON PCA
    # -------------------------------------------------------------------------
    ax_pca = axes[1, 0]
    
    # Reducir dimensionalidad a 2D
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_arr)
    
    # Calcular centroides en el espacio original y transformarlos a PCA
    centroids_orig = np.array([X_arr[labels == i].mean(axis=0) for i in range(n_clusters)])
    centroids_pca = pca.transform(centroids_orig)
    
    # Graficar puntos por cluster
    for i in range(n_clusters):
        points = X_pca[labels == i]
        ax_pca.scatter(points[:, 0], points[:, 1], color=colors[i], label=perfiles[i], 
                       alpha=0.8, edgecolors='w', s=70, zorder=3)
        
    # Graficar los centroides
    ax_pca.scatter(centroids_pca[:, 0], centroids_pca[:, 1], marker='X', color='black', 
                   s=250, zorder=10, edgecolors='white', linewidth=1.5, label='Centroides')
    
    # Anotar centroides
    for i, (cx, cy) in enumerate(centroids_pca):
        ax_pca.annotate(f"C{i}", xy=(cx, cy), xytext=(cx + 0.15, cy + 0.15),
                        fontweight='bold', fontsize=11, color='black',
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8, ec="black"))

    # Mostrar porcentaje de varianza explicada
    var_exp = pca.explained_variance_ratio_ * 100
    ax_pca.set_title(f"3. Visualización de Clusters con PCA (Varianza Exp: {sum(var_exp):.1f}%)", fontweight='bold', pad=10)
    ax_pca.set_xlabel(f"Componente Principal 1 ({var_exp[0]:.1f}%)")
    ax_pca.set_ylabel(f"Componente Principal 2 ({var_exp[1]:.1f}%)")
    ax_pca.legend(title="Perfiles de Estudiantes")

    # -------------------------------------------------------------------------
    # 4. SILHOUETTE PLOT PARA K=n_clusters
    # -------------------------------------------------------------------------
    ax_sil_plot = axes[1, 1]
    
    # Coeficientes individuales y promedio
    sample_silhouette_values = silhouette_samples(X_arr, labels)
    avg_silhouette_score = silhouette_score(X_arr, labels)
    
    y_lower = 10
    for i in range(n_clusters):
        # Filtrar y ordenar los valores de silueta para el cluster i
        ith_cluster_sil_vals = sample_silhouette_values[labels == i]
        ith_cluster_sil_vals.sort()
        
        size_cluster_i = ith_cluster_sil_vals.shape[0]
        y_upper = y_lower + size_cluster_i
        
        # Rellenar el área de silueta del cluster
        ax_sil_plot.fill_betweenx(np.arange(y_lower, y_upper), 0, ith_cluster_sil_vals,
                                  facecolor=colors[i], edgecolor=colors[i], alpha=0.7)
        
        # Etiqueta del cluster en la mitad del bloque
        ax_sil_plot.text(-0.05, y_lower + 0.5 * size_cluster_i, perfiles[i].split()[0], 
                         fontweight='bold', fontsize=9, ha='right', va='center')
        
        # Siguiente cluster
        y_lower = y_upper + 10
        
    ax_sil_plot.set_title(f"4. Análisis de Silueta para K={n_clusters} (Promedio: {avg_silhouette_score:.3f})", fontweight='bold', pad=10)
    ax_sil_plot.set_xlabel("Coeficiente de Silueta")
    ax_sil_plot.set_ylabel("Perfil / Cluster")
    
    # Línea vertical del promedio global
    ax_sil_plot.axvline(x=avg_silhouette_score, color="#dc2626", linestyle="--", linewidth=1.5,
                        label=f'Promedio Global ({avg_silhouette_score:.2f})')
    ax_sil_plot.set_yticks([])  # Quitar ticks del eje Y por legibilidad
    ax_sil_plot.set_xlim([-0.1, 1.0])
    ax_sil_plot.legend(loc='lower right')

    # -------------------------------------------------------------------------
    # 5. MAPA DE CALOR DE DISTANCIAS ENTRE CENTROIDES
    # -------------------------------------------------------------------------
    ax_heat = axes[2, 0]
    
    # Calcular matriz de distancias
    dist_matrix = pairwise_distances(centroids_orig)
    
    # Nombres de fila/columna limpios
    nombres_corta = [p.split()[0] for p in perfiles]
    df_dist = pd.DataFrame(dist_matrix, index=nombres_corta, columns=nombres_corta)
    
    sns.heatmap(df_dist, annot=True, fmt=".2f", cmap="YlOrRd", cbar_kws={'label': 'Distancia Euclidiana'},
                ax=ax_heat, square=True, linewidths=0.5, annot_kws={"size": 11, "weight": "bold"})
    
    ax_heat.set_title("5. Distancia entre Centroides de Clusters", fontweight='bold', pad=10)
    ax_heat.set_xlabel("Perfil de Destino")
    ax_heat.set_ylabel("Perfil de Origen")

    # -------------------------------------------------------------------------
    # 6. TABLA / RESUMEN DE CLUSTERS
    # -------------------------------------------------------------------------
    ax_table = axes[2, 1]
    ax_table.axis('off')  # No dibujar ejes, solo la tabla
    
    # Contar muestras y promedios por característica
    resumen_data = []
    for i in range(n_clusters):
        cluster_mask = (labels == i)
        count = sum(cluster_mask)
        pct = (count / n_samples) * 100
        
        # Calcular medias en el espacio original
        medias = X_arr[cluster_mask].mean(axis=0)
        
        row = {
            "Perfil (Cluster)": perfiles[i],
            "Alumnos": f"{count} ({pct:.1f}%)",
        }
        for f_idx in range(min(n_features, 3)):  # Mostrar hasta las 3 primeras variables
            row[f"Media Var {f_idx+1}"] = f"{medias[f_idx]:.2f}"
            
        resumen_data.append(row)
        
    df_resumen = pd.DataFrame(resumen_data)
    
    # Dibujar la tabla
    tabla = ax_table.table(cellText=df_resumen.values, colLabels=df_resumen.columns, 
                           cellLoc='center', loc='center')
    
    # Ajustar estilos de la tabla
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1.1, 2.2)
    
    # Cabecera en negrita y coloreada
    for (row, col), cell in tabla.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#1e293b')
        elif col == 0:
            # Color del perfil correspondiente
            cell.set_text_props(weight='bold', color=colors[row-1])
            
    ax_table.set_title("6. Resumen Estadístico por Perfil", fontweight='bold', pad=10)

    # Ajustar espaciado y guardar/mostrar
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches='tight')
    print(f"Dashboard de visualizaciones guardado exitosamente en: '{save_path}'")
    plt.show()

# -------------------------------------------------------------------------
# Ejecución de Ejemplo
# -------------------------------------------------------------------------
if __name__ == "__main__":
    # Simular datos como indica el ejemplo del usuario
    np.random.seed(42)
    
    # Simulación de 100 estudiantes con 3 materias (calificaciones de 0 a 10)
    # Generamos clusters diferenciados para que las métricas tengan sentido
    cluster_1 = np.random.normal(loc=9.0, scale=0.8, size=(25, 3))   # Expertos
    cluster_2 = np.random.normal(loc=7.5, scale=0.8, size=(30, 3))   # Avanzados
    cluster_3 = np.random.normal(loc=6.0, scale=1.0, size=(25, 3))   # Intermedios
    cluster_4 = np.random.normal(loc=4.5, scale=1.2, size=(20, 3))   # Básicos
    
    X_ejemplo = np.vstack([cluster_1, cluster_2, cluster_3, cluster_4])
    X_ejemplo = np.clip(X_ejemplo, 0, 10) # Limitar calificaciones de 0 a 10
    
    # Entrenar K-Means con K=4
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    labels_ejemplo = kmeans.fit_predict(X_ejemplo)
    
    # Mapeo de clusters según su promedio general de calificaciones (de mayor a menor)
    cluster_means = [X_ejemplo[labels_ejemplo == i].mean() for i in range(4)]
    sorted_indices = np.argsort(cluster_means)[::-1] # Índices ordenados de mayor promedio a menor
    
    # Reordenar etiquetas para que:
    # 0 = Experto, 1 = Avanzado, 2 = Intermedio, 3 = Básico
    label_mapping = {old_label: new_label for new_label, old_label in enumerate(sorted_indices)}
    labels_ordenadas = np.array([label_mapping[l] for l in labels_ejemplo])
    
    # Nombres de perfiles ordenados
    nombres_perfiles = ["Experto", "Avanzado", "Intermedio", "Básico"]
    
    # Generar visualizaciones
    generar_visualizaciones_clustering(
        X=X_ejemplo,
        labels=labels_ordenadas,
        perfiles=nombres_perfiles,
        save_path="visualizaciones_clustering.png"
    )
