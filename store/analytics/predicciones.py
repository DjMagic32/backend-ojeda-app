import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from ..models import Pedido, Producto, Usuario

def realizar_predicciones():
    # Cargar datos
    pedidos = Pedido.objects.select_related('tienda', 'usuario').prefetch_related('items__producto').all()
    data = []
    for pedido in pedidos:
        for item in pedido.items.all():
            data.append({
                'tienda': pedido.tienda.nombre,
                'producto': item.producto.nombre,
                'ventas': item.cantidad,
                'mes': pedido.creado.strftime('%Y-%m'),
                'comprador': pedido.usuario.username,
                'genero': pedido.usuario.genero,
                'ingresos_minimos': pedido.usuario.ingresos_minimos_mensuales
            })

    if not data:  # Si no hay datos, retorna predicciones y valores de prueba vacíos
        return [], []

    df = pd.DataFrame(data)

    # Preprocesar datos
    if 'genero' not in df or df.empty:  # Verificar si la columna existe y si hay datos
        return [], []

    df['genero'] = df['genero'].map({'M': 0, 'F': 1, 'O': 2}).fillna(-1)  # Rellena valores vacíos con -1
    # TODO: Consider alternative strategies for handling missing 'genero',
    # e.g., mode imputation or treating as a distinct category.
    df['mes'] = pd.to_datetime(df['mes']).dt.month  # Convertir mes a valores numéricos
    X = df[['ventas', 'mes', 'genero', 'ingresos_minimos']].fillna(0)  # Maneja valores faltantes
    # TODO: For 'ingresos_minimos', investigate if mean/median imputation
    # or a more sophisticated imputation method would be more appropriate than fillna(0).
    # TODO: Features like 'tienda' and 'comprador' (currently loaded but unused)
    # could be valuable if properly encoded (e.g., one-hot, target encoding).
    y = df['producto']

    # Dividir datos en entrenamiento y prueba
    if X.empty or y.empty:
        return [], []  # Retorna valores vacíos si no hay datos suficientes

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Entrenar modelo
    clf = RandomForestClassifier()
    clf.fit(X_train, y_train)

    # Evaluar modelo
    accuracy = clf.score(X_test, y_test)
    print(f'Accuracy: {accuracy}')

    # Realizar predicciones
    predicciones = clf.predict(X_test)
    return predicciones, y_test

# TODO: This script defines a prediction function but does not currently integrate
# its execution or results with the main application (e.g., via an admin command,
# a scheduled Celery task, or an API endpoint). Further work is needed to make
# these predictions usable.
