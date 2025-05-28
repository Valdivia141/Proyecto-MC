from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import sqlite3

app = Flask(__name__)

# Conexión a la base de datos
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Crear la tabla productos si no existe
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL,
            categoria_id INTEGER,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            fecha TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER,
            producto_id INTEGER,
            cantidad INTEGER,
            subtotal REAL,
            FOREIGN KEY (venta_id) REFERENCES ventas(id),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    ''')

    conn.commit()
    conn.close()


# Página principal
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/productos')
def productos():
    conn = get_db_connection()
    productos = conn.execute('''
        SELECT productos.*, categorias.nombre AS categoria_nombre
        FROM productos
        LEFT JOIN categorias ON productos.categoria_id = categorias.id
    ''').fetchall()

    categorias = conn.execute('SELECT * FROM categorias').fetchall()
    conn.close()
    return render_template('productos.html', productos=productos, categorias=categorias)

# Ruta para agregar categorias
@app.route('/categorias', methods=['GET', 'POST'])
def categorias():
    conn = get_db_connection()

    if request.method == 'POST':
        nombre = request.form['nombre']
        conn.execute('INSERT INTO categorias (nombre) VALUES (?)', (nombre,))
        conn.commit()

    categorias = conn.execute('SELECT * FROM categorias').fetchall()
    conn.close()
    return render_template('categorias.html', categorias=categorias)


# Ruta para agregar producto
@app.route('/agregar', methods=['POST'])
def agregar():
    nombre = request.form['nombre']
    precio = request.form['precio']
    stock = request.form['stock']
    categoria_id = request.form['categoria_id']

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO productos (nombre, precio, stock, categoria_id) VALUES (?, ?, ?, ?)',
        (nombre, precio, stock, categoria_id)
    )
    conn.commit()
    conn.close()
    return redirect('/productos')

# Ruta para agregar clientes
@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    conn = get_db_connection()
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        conn.execute('INSERT INTO clientes (nombre, correo) VALUES (?, ?)', (nombre, correo))
        conn.commit()
    clientes = conn.execute('SELECT * FROM clientes').fetchall()
    conn.close()
    return render_template('clientes.html', clientes=clientes)

# Ruta para ventas
@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    conn = get_db_connection()

    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        productos_cantidades = request.form.getlist('producto')  # IDs productos
        cantidades = request.form.getlist('cantidad')  # cantidades

        fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Insertar venta
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO ventas (fecha, cliente_id) VALUES (?, ?)',
            (fecha, cliente_id)
        )
        venta_id = cursor.lastrowid

        # Insertar detalle_ventas
        for producto_id, cantidad in zip(productos_cantidades, cantidades):
            if int(cantidad) > 0:
                cursor.execute(
                    'INSERT INTO detalle_ventas (venta_id, producto_id, cantidad) VALUES (?, ?, ?)',
                    (venta_id, producto_id, cantidad)
                )
                # Opcional: Actualizar stock en productos
                cursor.execute(
                    'UPDATE productos SET stock = stock - ? WHERE id = ?',
                    (cantidad, producto_id)
                )
        conn.commit()
        conn.close()
        return redirect('/ventas')

    # GET: mostrar formulario
    clientes = conn.execute('SELECT * FROM clientes').fetchall()
    productos = conn.execute('SELECT * FROM productos WHERE stock > 0').fetchall()
    conn.close()
    return render_template('ventas.html', clientes=clientes, productos=productos)

# Ruta para lista de ventas
@app.route('/historial_ventas')
def historial_ventas():
    conn = get_db_connection()
    
    # Obtener todas las ventas con info de cliente
    ventas = conn.execute('''
        SELECT ventas.id, ventas.fecha, clientes.nombre AS cliente_nombre
        FROM ventas
        JOIN clientes ON ventas.cliente_id = clientes.id
        ORDER BY ventas.fecha DESC
    ''').fetchall()
    
    # Para cada venta, obtener detalle productos + cantidades
    ventas_detalle = {}
    for venta in ventas:
        detalles = conn.execute('''
            SELECT productos.nombre, detalle_ventas.cantidad, productos.precio
            FROM detalle_ventas
            JOIN productos ON detalle_ventas.producto_id = productos.id
            WHERE detalle_ventas.venta_id = ?
        ''', (venta['id'],)).fetchall()
        ventas_detalle[venta['id']] = detalles
    
    conn.close()
    return render_template('historial_ventas.html', ventas=ventas, ventas_detalle=ventas_detalle)

# Mostrar formulario para editar producto
@app.route('/editar_producto/<int:producto_id>', methods=['GET', 'POST'])
def editar_producto(producto_id):
    conn = get_db_connection()
    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    categorias = conn.execute('SELECT * FROM categorias').fetchall()

    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = float(request.form['precio'])
        stock = int(request.form['stock'])
        categoria_id = int(request.form['categoria_id'])
        
        conn.execute('''
            UPDATE productos
            SET nombre = ?, precio = ?, stock = ?, categoria_id = ?
            WHERE id = ?
        ''', (nombre, precio, stock, categoria_id, producto_id))
        conn.commit()
        conn.close()
        return redirect(url_for('productos'))

    conn.close()
    return render_template('editar_producto.html', producto=producto, categorias=categorias)

# Ruta para eliminar producto
@app.route('/eliminar_producto/<int:producto_id>')
def eliminar_producto(producto_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM productos WHERE id = ?', (producto_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('productos'))

@app.route('/eliminar_categoria/<int:categoria_id>')
def eliminar_categoria(categoria_id):
    conn = get_db_connection()

    # Verificar si hay productos con esta categoría
    productos = conn.execute('SELECT COUNT(*) FROM productos WHERE categoria_id = ?', (categoria_id,)).fetchone()[0]

    if productos > 0:
        conn.close()
        return "No se puede eliminar esta categoría porque está asignada a productos.", 400

    # Si no hay productos, eliminar la categoría
    conn.execute('DELETE FROM categorias WHERE id = ?', (categoria_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('categorias'))

@app.route('/eliminar_cliente/<int:cliente_id>')
def eliminar_cliente(cliente_id):
    conn = get_db_connection()

    # Verificar si hay ventas con este cliente
    ventas = conn.execute('SELECT COUNT(*) FROM ventas WHERE cliente_id = ?', (cliente_id,)).fetchone()[0]

    if ventas > 0:
        conn.close()
        return "No se puede eliminar este cliente porque tiene ventas registradas.", 400

    conn.execute('DELETE FROM clientes WHERE id = ?', (cliente_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('clientes'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
