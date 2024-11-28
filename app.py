from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Usar el backend no interactivo 'Agg'
import matplotlib.pyplot as plt
import os
from flask import url_for


app = Flask(__name__)

# Configurar CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Definir dimensiones fijas de la base
BASE_WIDTH = 900
BASE_LENGTH = 1000

def best_fit(new_rect, huecos):
    """Buscar el mejor hueco disponible para el nuevo rectángulo."""
    best_hueco = None
    min_residual_area = float('inf')  # Residuo más pequeño

    for i, (x, y, width, length) in enumerate(huecos):
        if new_rect[0] <= width and new_rect[1] <= length:
            residual_area = (width * length) - (new_rect[0] * new_rect[1])
            if residual_area < min_residual_area:
                best_hueco = (i, x, y, width, length)
                min_residual_area = residual_area

    return best_hueco

def plot_rectangles(rectangles, base_width, base_length, image_path):
    """Visualizar los rectángulos y guardar la imagen."""
    fig, ax = plt.subplots()
    ax.set_xlim(0, base_width)
    ax.set_ylim(0, base_length)

    base_rect = plt.Rectangle((0, 0), base_width, base_length, edgecolor='black', facecolor='none', lw=2)
    ax.add_patch(base_rect)

    # Dibujar los pedidos
    colors = ['red', 'green', 'blue', 'yellow', 'orange', 'pink']  
    for i, (x, y, width, length, order_cod) in enumerate(rectangles):
        color = colors[i % len(colors)]
        rect = plt.Rectangle((x, y), width, length, color=color, alpha=0.6)
        ax.add_patch(rect)

        ax.text(x + width / 2, y + length / 2, order_cod, ha='center', va='center', color='black')

    plt.gca().invert_yaxis()
    plt.title('Acomodo de Pedidos en Placa Base')
    plt.xlabel('Ancho (mm)')
    plt.ylabel('Largo (mm)')
    plt.grid()
    plt.savefig(image_path)  
    plt.close(fig) 


@app.route('/predict', methods=['POST'])
def accommodate_orders():
    data = request.get_json(force=True)

    if 'orders' not in data:
        return jsonify({'error': 'Falta lista de órdenes'}), 400

    orders = data['orders']

    total_area = BASE_WIDTH * BASE_LENGTH

    # Filtrar pedidos
    filtered_orders = pd.DataFrame(orders)
    filtered_orders = filtered_orders[(filtered_orders['width'] > 1) & (filtered_orders['length'] > 1)]

    if filtered_orders.empty:
        return jsonify({'error': 'No hay pedidos válidos para acomodar.'}), 400

    used_area = 0
    rectangles = []
    huecos = [(0, 0, BASE_WIDTH, BASE_LENGTH)]

    # Ordenar y acomodar pedidos
    filtered_orders['area'] = filtered_orders['width'] * filtered_orders['length']
    filtered_orders = filtered_orders.sort_values(by='area', ascending=False)

    for idx, order in filtered_orders.iterrows():
        width = order['width']
        length = order['length']
        new_rect = (width, length)

        best_hueco = best_fit(new_rect, huecos)

        if best_hueco:
            i, x, y, hueco_width, hueco_length = best_hueco
            rectangles.append((x, y, width, length, order['order_cod']))

            huecos.pop(i)
            if hueco_width - width > 0:
                huecos.append((x + width, y, hueco_width - width, length))
            if hueco_length - length > 0:
                huecos.append((x, y + length, hueco_width, hueco_length - length))

            used_area += width * length

    merma = total_area - used_area
    image_path = 'static/accommodation_plot.png'
    plot_rectangles(rectangles, BASE_WIDTH, BASE_LENGTH, image_path)

    # Convertir la lista de códigos de órdenes a una cadena de texto separada por comas
    accommodated_orders = ",".join([order_cod for _, _, _, _, order_cod in rectangles])

    print("Rectángulos acomodados:", rectangles)

    return jsonify({
        'placabase': [{
            'used_area': used_area,
            'merma': merma,
            'image_url': url_for('static', filename='accommodation_plot.png', _external=True),
            'orders_ac': accommodated_orders  # Ahora es una cadena de texto
        }]
    })


if __name__ == '__main__':
    # Asegúrate de crear la carpeta 'static' en tu proyecto para almacenar la imagen.
    if not os.path.exists('static'):
        os.makedirs('static')
    
    app.run(debug=True)
