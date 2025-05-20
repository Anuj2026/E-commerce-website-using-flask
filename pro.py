import os
import razorpay
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session,url_for, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

app.secret_key = 'your_secret_key'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

razorpay_client = razorpay.Client(auth=("rzp_test_6JyrBQ7OgMa9Zg", "oachPtLVfbNrgTPf0tDp8e8i"))

def get_db_connection():
    try:
        conn = sqlite3.connect('dbshoes.db')
        conn.row_factory = sqlite3.Row
        print("Database connected successfully.")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None
 
@app.before_request
def before_request_func():
    if not hasattr(app, 'db_initialized'):
       
        print("Initializing database...")
       
        app.db_initialized = True  # runs if true

def test_db_connection():
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")  
        conn.close()
        print("Database connection is working.")
    except Exception as e:
        print(f"Database connection failed: {e}")


@app.route("/", methods=["GET", "POST"])
def homepage():
    """Homepage"""
    if request.method == "GET":
        return render_template("homepage.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        pnumber = request.form.get("pnumber")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

      
        if not username or not pnumber or not password or not confirmation:
            return render_template("apology.html", message="All fields are required.")
        if password != confirmation:
            return render_template("apology.html", message="Passwords do not match.")

       
        hash = generate_password_hash(password)
        try:
            conn = get_db_connection()
            if conn is None:
                raise Exception("Database connection failed.")

     
            cursor = conn.cursor()
            cursor.execute("INSERT INTO user (user_name, phone_number, hash) VALUES (?, ?, ?)", (username, pnumber, hash))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return render_template("apology.html", message=f"Database error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            return render_template("apology.html", message=f"Unexpected error: {e}")

       
        session["id"] = user_id
        return redirect("/address")


@app.route("/address", methods=["GET", "POST"])
def address():
    if request.method == "GET":
        return render_template("address.html")
    else:

        unit_number = request.form.get("unit_number")
        street_number = request.form.get("street_number")
        address_line1 = request.form.get("address_line1")
        address_line2 = request.form.get("address_line2")
        city = request.form.get("city")
        region = request.form.get("region")
        postal_code = request.form.get("postal_code")
        country_id = request.form.get("country_id")  

        if not street_number or not address_line1 or not city or not region or not postal_code or not country_id:
            return render_template("apology.html", message="All required fields must be filled out.")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

          
            cursor.execute("""
                INSERT INTO address (unit_number, street_number, address_line1, address_line2, city, region, postal_code, country_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (unit_number, street_number, address_line1, address_line2, city, region, postal_code, country_id))
            conn.commit()

            address_id = cursor.lastrowid

            
            user_id = session.get("id")
            cursor.execute("INSERT INTO user_address (user_id, address_id, is_default) VALUES (?, ?, ?)", 
                           (user_id, address_id, 1))  
            conn.commit()

            conn.close()

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return render_template("apology.html", message=f"Database error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            return render_template("apology.html", message=f"Unexpected error: {e}")

       
        return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM user WHERE user_name = ?", (request.form.get("username"),)).fetchall()
        conn.close()

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username or password. Please try again.", "danger") 
            return redirect("/login")  

        session["id"] = rows[0]["id"]
        session["is_admin"] = rows[0]["is_admin"]

        if session["is_admin"]:
            flash("You have been logged in as Admin!", "success")
            return render_template("admin_dashboard.html")
        else:
            flash("You have successfully logged in as User!", "success")
            return render_template("homepage.html")
    return render_template("login.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "GET":
        return render_template("contact.html")
    else:
        return render_template("contact.html")

@app.route('/search', methods=["GET", "POST"])
def search():
    template_mapping = {
        "formal shoes": ("formal_shoes", 1),
        "formals shoes": ("formal_shoes", 1),
        "office shoes": ("formal_shoes", 1),
        "formals shoe": ("formal_shoes", 1),
        "sneakers": ("sneakers", 2),
        "shoes": ("sneakers", 2),
        "sneakers": ("sneakers", 2),
        "hills": ("hills", 3),
        "kids shoes": ("kids_shoes", 4),
        "formal": ("formal_shoes", 1),
        "formals": ("formal_shoes", 1),
        "sneaker": ("sneakers", 2),
        "hill": ("hills", 3),
        "heels": ("hills", 3),
        "heel": ("hills", 3),
        "hills": ("hills", 3),
        "kids": ("kids_shoes", 4)
    }

    if request.method == "POST":
        prompt = request.form.get("prompt", "").lower().strip()

        if not prompt:
            return render_template("not-found.html")

        search_terms = [term.strip() for term in prompt.split(',')]

        for term in search_terms:
            template_data = template_mapping.get(term)

            if template_data:
                template, category_id = template_data
                conn = get_db_connection()
                products = conn.execute('SELECT * FROM product_item WHERE category_id = ?', (category_id,)).fetchall()
                conn.close()
                return render_template(f"{template}.html", products=products)

        return render_template("not-found.html")

    return redirect("/")    

#Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route('/formal_shoes')
def show_formal_shoes():
    conn = get_db_connection()
    
    products = conn.execute('SELECT * FROM product_item WHERE category_id = ?', (1,)).fetchall()
    conn.close()
    
    return render_template('formal_shoes.html', products=products)


@app.route('/sneakers')
def show_sneakers():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM product_item WHERE category_id = ?', (2,)).fetchall()
    conn.close()
    
    return render_template('sneakers.html', products=products)

@app.route('/hills')
def show_hills():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM product_item WHERE category_id = ?', (3,)).fetchall()
    conn.close()
    
    return render_template('hills.html', products=products)

@app.route('/kids_shoes')
def show_kids_shoes():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM product_item WHERE category_id = ?', (4,)).fetchall()
    conn.close()
    
    return render_template('kids_shoes.html', products=products)




@app.route('/add_to_cart', methods=["POST"])
def add_to_cart():
    if 'id' not in session:
        return redirect(url_for('login', message="Please log in to add items to your cart."))

    product_item_id = request.form.get('product_item_id')
    quantity = request.form.get('quantity')
    print(f"Product Item ID: {product_item_id}")
    print(f"Quantity: {quantity}")

   
    if not product_item_id or not quantity:
        return "Quantity cannot be match", 400

    user_id = session['id'] 

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        
        cart = cursor.execute("SELECT id FROM shopping_cart WHERE user_id = ?", (user_id,)).fetchone()
        
      
        if not cart:
            cursor.execute("INSERT INTO shopping_cart (user_id) VALUES (?)", (user_id,))
            cart_id = cursor.lastrowid  # Get the last inserted row ID (cart ID)
        else:
            cart_id = cart['id']  # If a cart exists, get the cart ID

       
        cart_item = cursor.execute("SELECT qty FROM shopping_cart_item WHERE cart_id = ? AND product_item_id = ?", 
                                   (cart_id, product_item_id)).fetchone()

        if cart_item:
            cursor.execute("UPDATE shopping_cart_item SET qty = qty + ? WHERE cart_id = ? AND product_item_id = ?", 
                           (quantity, cart_id, product_item_id))
        else:
            cursor.execute("INSERT INTO shopping_cart_item (cart_id, product_item_id, qty) VALUES (?, ?, ?)", 
                           (cart_id, product_item_id, quantity))
        
        conn.commit()  
        conn.close()  
        return redirect(url_for('show_cart'))  

    except Exception as e:
        print(f"Error: {e}")
        return "Internal Server Error", 500


@app.route("/cart")
def show_cart():
    if 'id' not in session:
        return redirect(url_for('login', next='cart'))

    conn = get_db_connection()
    cart_items = conn.execute("""
        SELECT sci.id AS cart_item_id, sci.qty, pi.name, pi.price, pi.product_image, pi.description
        FROM shopping_cart_item sci
        JOIN product_item pi ON sci.product_item_id = pi.id
        JOIN shopping_cart sc ON sc.id = sci.cart_id
        WHERE sc.user_id = ?
    """, (session['id'],)).fetchall()

    conn.close()

    # Calculate total price for the items in the cart (for display only)
    total_price = sum([item['price'] * item['qty'] for item in cart_items])

    # Log the cart items and total price
    print("Cart items:", cart_items)
    print("Total price:", total_price)

    
    payment_amount = 1  

    return render_template('cart.html', cart_items=cart_items, total_price=total_price, payment_amount=payment_amount)

@app.route('/remove_from_cart', methods=["POST"])
def remove_from_cart():
    if 'id' not in session:
        return redirect(url_for('login', message="Please log in to remove items from your cart."))

    cart_item_id = request.form.get('cart_item_id')
    print(f"Removing Cart Item ID: {cart_item_id}")

    if not cart_item_id:
        return "Bad Request: Missing cart item ID", 400

    conn = get_db_connection()
    conn.execute("DELETE FROM shopping_cart_item WHERE id = ?", (cart_item_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('show_cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'id' not in session:
        return redirect('/login')

    user_id = session['id']

    conn = get_db_connection()
    cart_items = conn.execute("""
        SELECT sci.qty, pi.price, pi.product_image, pi.name, pi.description
        FROM shopping_cart_item AS sci
        JOIN product_item AS pi ON sci.product_item_id = pi.id
        JOIN shopping_cart AS sc ON sci.cart_id = sc.id
        WHERE sc.user_id = ?
    """, (user_id,)).fetchall()
    conn.close()

 
    total_price = sum(item['price'] * item['qty'] for item in cart_items)

    if request.method == "GET":
        return render_template('order.html', cart_items=cart_items, total_price=total_price)
    else:
        return render_template('order.html', cart_items=cart_items, total_price=total_price)



@app.route("/account")
def account():
    if "id" not in session:
        return redirect(url_for("login"))
    return render_template("account.html")


#
#admin code
#
@app.route("/admin/manage_users")
def manage_users():
    """Display all users for admin to manage"""
    if not session.get("is_admin"):  # Only allow admins
        return redirect(url_for("login"))

    conn = get_db_connection()
    users = conn.execute("SELECT * FROM user").fetchall()  # Fetch all users from the user table
    conn.close()

    return render_template("admin_dashboard.html", users=users)

@app.route("/admin/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    """Edit a user's details and address"""
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    
    conn = get_db_connection()
    
    
    user = conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()

    address = conn.execute("SELECT * FROM address WHERE id = (SELECT address_id FROM user_address WHERE user_id = ?)", (user_id,)).fetchone()

    if request.method == "POST":
        new_username = request.form.get("username")
        new_phone = request.form.get("phone_number")

        #  address
        unit_number = request.form.get("unit_number")
        street_number = request.form.get("street_number")
        address_line1 = request.form.get("address_line1")
        address_line2 = request.form.get("address_line2")
        city = request.form.get("city")
        region = request.form.get("region")
        postal_code = request.form.get("postal_code")

        conn.execute("UPDATE user SET user_name = ?, phone_number = ? WHERE id = ?",
                     (new_username, new_phone, user_id))

        conn.execute("""
            UPDATE address
            SET unit_number = ?, street_number = ?, address_line1 = ?, address_line2 = ?, city = ?, region = ?, postal_code = ?
            WHERE id = (SELECT address_id FROM user_address WHERE user_id = ?)
        """, (unit_number, street_number, address_line1, address_line2, city, region, postal_code, user_id))

        conn.commit()
        conn.close()
        return redirect(url_for("manage_users"))

    conn.close()
    return render_template("edit_user.html", user=user, address=address)


@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):
    """Delete a user"""
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    
    conn = get_db_connection()
    conn.execute("DELETE FROM user WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("manage_users"))

@app.route('/admin/products', methods=['GET', 'POST'])
def manage_products():
    if 'id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    if not session.get('is_admin', False):
        return redirect(url_for('homepage'))  # Redirect non-admin users to homepage

    conn = get_db_connection()

    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        qty_in_stock = request.form['qty_in_stock']
        category_id = request.form['category_id']
        product_image = request.form['product_image']
        sku = request.form['sku'] 
        
        
        conn.execute('INSERT INTO product_item (name, description, price, qty_in_stock, category_id, SKU, product_image) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (name, description, price, qty_in_stock, category_id, sku, product_image))
        conn.commit()

  
    products = conn.execute('SELECT * FROM product_item').fetchall()
    conn.close()

    return render_template('admin_products.html', products=products)

@app.route('/admin/products/edit/<int:id>', methods=['POST', 'GET'])
def edit_product(id):
    conn = get_db_connection()

   
    product = conn.execute('SELECT * FROM product_item WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        qty_in_stock = request.form['qty_in_stock']
        category_id = request.form['category_id']
        product_image = request.form['product_image']
        sku = request.form['sku']

        conn.execute('UPDATE product_item SET name = ?, description = ?, price = ?, qty_in_stock = ?, category_id = ?, SKU = ?, product_image = ? WHERE id = ?',
                     (name, description, price, qty_in_stock, category_id, sku, product_image, id))
        conn.commit()
        conn.close()
        return redirect(url_for('manage_products'))

    conn.close()
    return render_template('edit_product.html', product=product)


@app.route('/profile', methods=["GET", "POST"])
def profile():

    if 'id' not in session:
        return redirect(url_for('login'))

    user_id = session['id']
    conn = get_db_connection()

    if request.method == "POST":
        new_username = request.form['username']
        new_phone_number = request.form['phone_number']
        
       
        conn.execute("""
            UPDATE user SET user_name = ?, phone_number = ?
            WHERE id = ?
        """, (new_username, new_phone_number, user_id))
        
        address_id = request.form['address_id']  # The hidden field with the address ID
        new_unit_number = request.form['unit_number']
        new_street_number = request.form['street_number']
        new_address_line1 = request.form['address_line1']
        new_address_line2 = request.form['address_line2']
        new_city = request.form['city']
        new_region = request.form['region']
        new_postal_code = request.form['postal_code']
        new_country_id = request.form['country_id']

        # Update the user's address details in the database
        conn.execute("""
            UPDATE address SET unit_number = ?, street_number = ?, address_line1 = ?, address_line2 = ?, city = ?, region = ?, postal_code = ?, country_id = ?
            WHERE id = ?
        """, (new_unit_number, new_street_number, new_address_line1, new_address_line2, new_city, new_region, new_postal_code, new_country_id, address_id))

        conn.commit()
        flash("Profile and address updated successfully.", "success")

    user = conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()

    address = conn.execute("""
        SELECT a.id, a.unit_number, a.street_number, a.address_line1, a.address_line2, a.city, a.region, a.postal_code, a.country_id
        FROM address a
        JOIN user_address ua ON a.id = ua.address_id
        WHERE ua.user_id = ?
    """, (user_id,)).fetchone()

    conn.close()

    return render_template('profile.html', user=user, address=address)


if __name__ == "__main__":
    app.run(debug=True)
