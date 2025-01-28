from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import pandas as pd
from reportlab.pdfgen import canvas
from datetime import datetime
import io
import os
import sqlitecloud
import ast
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access the environment variables

app = Flask(__name__)

# Secret key for flash messages
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')


# Load CSV files using pandas
# Open the connection to SQLite Cloud
api_key = os.getenv('SQLITE_CLOUD_API_KEY')
conn = sqlitecloud.connect(f"sqlitecloud://ckn0dvyvnz.g6.sqlite.cloud:8860/Raichur-hardware-database?apikey={api_key}")
cursor = conn.execute('SELECT * FROM pipes;')  # Query to fetch the pipes table
pipes_data = cursor.fetchall()
cursor = conn.execute('SELECT * FROM discounts;')  # Query to fetch the discounts table
discounts_data = cursor.fetchall()
conn.close()

# Convert the fetched data into a pandas DataFrame
discounts_columns = ['discounts', 'percent']  # Updated columns
pipes_columns = ['id', 'pipe_name', 'price']  # Updated columns
pipes_df = pd.DataFrame(pipes_data, columns=pipes_columns)
discounts_df = pd.DataFrame(discounts_data, columns=discounts_columns)

def get_matching_pipes(query):
    # Filter pipes that contain the search query (case-insensitive)
    return pipes_df[pipes_df['pipe_name'].str.contains(query, case=False, na=False)]['pipe_name'].tolist()

# Home route
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search_pipes', methods=['GET'])
def search_pipes_ajax():
    query = request.args.get('query', '')
    if query:
        try:
            # Get matching pipe names
            results = pipes_df[pipes_df['pipe_name'].str.contains(query, case=False, na=False)]['pipe_name'].tolist()
            return {'suggestions': results}
        except KeyError:
            return {'suggestions': []}
    return {'suggestions': []}

@app.route('/search', methods=['POST'])
def search():
    search_query = request.form.get('search', '')
    if search_query:
        # Get matching pipe suggestions from your database
        suggestions = get_matching_pipes(search_query)
        return jsonify({'suggestions': suggestions})
    return jsonify({'suggestions': []})

# Add to cart route
cart = []

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    pipe_name = request.form.get('pipe_name')
    quantity = request.form.get('quantity')
    if not pipe_name or not quantity or not quantity.isdigit() or int(quantity) <= 0:
        flash("Invalid pipe name or quantity.")
        return redirect(url_for('index'))
    cart.append({'pipe_name': pipe_name, 'quantity': int(quantity)})
    flash(f"Added {pipe_name} (x{quantity}) to the cart.")
    return redirect(url_for('index'))

# View cart route
@app.route('/cart', methods=['GET', 'POST'])
def view_cart():
    selected_discounts = request.form.getlist('discounts')
    total_price = 0

    # Extract discounts from the discounts_df DataFrame
    discounts = discounts_df['discounts'].tolist()

    # If the form has been submitted, calculate total price with discounts
    if selected_discounts:
        total_price = calculate_total_price(selected_discounts)

    return render_template('cart.html', cart=cart, discounts=discounts, total_price=total_price, selected_discounts=selected_discounts)

def calculate_total_price(selected_discounts):
    total_price = 0
    for item in cart:
        # Get the price of the pipe from the CSV
        pipe_data = pipes_df[pipes_df['pipe_name'] == item['pipe_name']]
        if not pipe_data.empty:
            price = pipe_data.iloc[0]['price']
            for discount_name in selected_discounts:
                # Get discount percentage from the discounts CSV
                discount_data = discounts_df[discounts_df['discounts'] == discount_name]
                if not discount_data.empty:
                    discount_percent = discount_data.iloc[0]['percent']
                    price -= price * (discount_percent / 100)  # Apply discount
            total_price += price * item['quantity'] 
        else:
            flash(f"Price information for {item['pipe_name']} is not available.")
    return total_price

# Edit discounts route
@app.route('/discounts', methods=['GET', 'POST'])
def edit_discounts():
    if request.method == 'POST':
        discount_name = request.form.get('discount_name')
        new_percent = request.form.get('new_percent')

        if discount_name and new_percent:
            try:
                new_percent_value = float(new_percent)
                conn = sqlitecloud.connect(f"sqlitecloud://ckn0dvyvnz.g6.sqlite.cloud:8860/Raichur-hardware-database?apikey={api_key}")
                conn.execute('UPDATE discounts SET percent = ? WHERE discounts = ?', (new_percent_value, discount_name))
                conn.commit()
                conn.close()
                # Update the DataFrame
                discounts_df.loc[discounts_df['discounts'] == discount_name, 'percent'] = new_percent_value
            except ValueError:
                flash("Invalid percentage value. Please enter a valid number.")

        return redirect(url_for('edit_discounts'))

    discounts = discounts_df[['discounts', 'percent']].to_dict(orient='records')
    return render_template('discounts.html', discounts=discounts)

# Calculate total price route
@app.route('/calculate_total', methods=['POST'])
def calculate_total():
    selected_discounts = request.form.getlist('discounts')
    if not cart:
        flash("Your cart is empty!")
        return redirect(url_for('view_cart'))

    total_price = calculate_total_price(selected_discounts)

    return render_template('cart.html', cart=cart, total_price=total_price, selected_discounts=selected_discounts)

@app.route('/generate-quotation', methods=['POST'])
def generate_quotation():

    # Get cart data, selected discounts, and customer details
    selected_discounts = request.form.getlist('discounts')
    total_price = float(request.form.get('total_price', 0.0))

    customer_name = request.form.get('customer_name', "N/A")
    delivery_place = request.form.get('delivery_place', "N/A")
    pin_code = request.form.get('pin_code', "N/A")
    distance = request.form.get('distance', "N/A")
    contact_number_1 = request.form.get('contact_number_1', "N/A")
    contact_number_2 = request.form.get('contact_number_2', "N/A")


    # Convert selected_discounts to a Python list if it's a string
    if isinstance(selected_discounts, str):
        try:
            selected_discounts = ast.literal_eval(selected_discounts)
        except Exception as e:
            print(f"Error converting selected_discounts: {e}")
            selected_discounts = []


    # Create an in-memory file to store the PDF
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(595.27, 841.89))  # A4 size
    page_width = 595
    page_height = 841

    # Add company details
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(page_width / 2, 800, "Quotation")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(460, 800, f"Date: {datetime.now().strftime('%d-%m-%Y')}")
    c.drawString(50, 800, "GST: 29AFCPD4874L1Z3")
    c.setFont("Helvetica", 12)
    c.drawCentredString(page_width / 2, 780, "CARE AGENCIES")
    c.drawCentredString(page_width / 2, 760, "12-10-49/1 Chandramouleshwara circle, lingsugur road, Raichur-584101")
    c.drawCentredString(page_width / 2, 740, "Phone: 9448129036 / 9449030030")
    c.line(50, 730, 545, 730)

    # Add customer details
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 710, "Customer Details:")
    c.setFont("Helvetica-Bold", 12)
    y_position = 690
    c.drawString(50, y_position, f"Name: {customer_name}")
    y_position -= 20
    c.drawString(50, y_position, f"Delivery Place: {delivery_place}")
    y_position -= 20
    c.drawString(50, y_position, f"Pin Code: {pin_code}")
    y_position -= 20
    c.drawString(50, y_position, f"Approx Distance: {distance} km")
    y_position -= 20
    c.drawString(50, y_position, f"Contact Number 1: {contact_number_1}")
    y_position -= 20
    c.drawString(50, y_position, f"Contact Number 2: {contact_number_2}")
    y_position -= 30

    # Add table headers
    c.drawString(50, y_position, "Product")
    c.drawString(280, y_position, "Rate per 6 mtrs")
    c.drawString(380, y_position, "Qty (meter)")
    c.drawString(480, y_position, "Total")
    y_position -= 5
    c.line(50, y_position, 545, y_position)  # Draw a line below the headers
    y_position -= 15

    # Add product data
    c.setFont("Helvetica", 12)
    grand_total = 0
    pipe_price_dict = pipes_df.set_index('pipe_name')['price'].to_dict()

    for item in cart:
        pipe_name = item['pipe_name']
        quantity = item['quantity']

        # Get price per meter from the dictionary
        if pipe_name in pipe_price_dict:
            price_per_meter = pipe_price_dict[pipe_name]
            rate_per_length = price_per_meter * 6
            total = price_per_meter * quantity
            parsed_discounts = []
            for d in selected_discounts:
                if d.startswith('['):
                    parsed_discounts.extend(json.loads(d))
                else:
                    parsed_discounts.append(d)
            # Filter valid discounts
            valid_discounts = discounts_df[discounts_df['discounts'].isin(parsed_discounts)]

            # Calculate total discount percentage
            if not valid_discounts.empty:
                total_discount_percent = valid_discounts['percent'].sum()
            else:
                total_discount_percent = 0
            # Apply the total discount
            discounted_total = total - (total * (total_discount_percent / 100))
            grand_total += discounted_total

            # Draw product row
            c.drawString(50, y_position, f"{pipe_name} PVC Pipe - Finolex")
            c.drawString(280, y_position, f"{rate_per_length:.2f}")
            c.drawString(380, y_position, f"{quantity} m")
            c.drawString(480, y_position, f"{discounted_total:.2f}")
            y_position -= 20
        else:
            # Handle missing price information
            c.drawString(50, y_position, pipe_name)
            c.drawString(200, y_position, "Price not available")
            c.drawString(350, y_position, "N/A")
            c.drawString(450, y_position, "N/A")
            y_position -= 20

    # Add a line below the last product
    c.line(50, y_position, 545, y_position)
    y_position -= 20

    # Display grand total
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y_position, "Grand Total:")
    c.drawString(450, y_position, f"{grand_total:.2f}/-")
    y_position -= 30

    # Footer
    c.setFont("Helvetica-Bold", 8)
    c.drawString(50, y_position, "Terms and Conditions:")
    y_position -= 10
    c.drawString(50, y_position, "1. The rates provided are for reference purposes only.")
    y_position -= 10
    c.drawString(50, y_position, "2. The Ruling rates at the time of dispatch will be applicable.")
    y_position -= 10
    c.drawString(50, y_position, "3. Material supply is subject to the delivery schedule of the respective companies.")
    y_position -= 10
    c.drawString(50, y_position, "4. Transportation and loading charges shall be borne by the buyer.")
    y_position -= 10
    c.drawString(50, y_position, "5. Unloading must be arranged by the buyer within a reasonable time after the material's arrival.")
    y_position -= 10
    c.drawString(50, y_position, "6. In case of F.O.R. (Free on Road), the vehicle will not travel on non-motorable roads or into fields.")
    y_position -= 10
    c.drawString(50, y_position, "7. All disputes are subject to Raichur jurisdiction.")
    y_position -= 10
    c.drawString(50, y_position, "8. The prices provided are inclusive of GST at 18%.")
    c.save()

    # Clear the cart after generating the quotation
    cart.clear()
    download_name = f"quotation_{customer_name}_{datetime.now().strftime('%Y-%m-%d')}.pdf"

    # Save the PDF to buffer and send it as a response
    pdf_buffer.seek(0)
    return send_file(pdf_buffer, as_attachment=True, download_name=download_name, mimetype='application/pdf')

# Load discounts for the discount dropdown
@app.context_processor
def load_discounts():
    try:
        discounts = discounts_df['discounts'].tolist()
    except KeyError:
        discounts = []
    return {'discounts': discounts}

app = Flask(__name__)
