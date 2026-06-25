from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import jsonify
from flask import Response
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime
from flask import make_response
from flask import render_template


from xhtml2pdf import pisa
from io import BytesIO

from flask import send_file

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

import os

from db import get_connection

from db import get_connection

app = Flask(__name__)
app.secret_key = "jondhale_secret_key"


@app.route("/")
def home():

    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():

    username = request.form["username"]
    password = request.form["password"]

    conn = get_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE username=%s
        AND password=%s
        """,
        (username,password)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return redirect("/dashboard")

    return "Invalid Username or Password"


@app.route("/dashboard")
def dashboard():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Total stock from inventory
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total_kg
        FROM wood_inventory
        WHERE unit = 'kg'
    """)
    total_kg = cursor.fetchone()["total_kg"]

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total_ton
        FROM wood_inventory
        WHERE unit = 'ton'
    """)
    total_ton = cursor.fetchone()["total_ton"]

    # Incoming today (KG)
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM incoming_wood
        WHERE unit = 'kg'
        AND DATE(created_at) = CURDATE()
    """)
    incoming_kg = cursor.fetchone()["total"]

    # Incoming today (Ton)
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM incoming_wood
        WHERE unit = 'ton'
        AND DATE(created_at) = CURDATE()
    """)
    incoming_ton = cursor.fetchone()["total"]

    # Outgoing today (KG)
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM outgoing_wood
        WHERE unit = 'kg'
        AND DATE(created_at) = CURDATE()
    """)
    outgoing_kg = cursor.fetchone()["total"]

    # Outgoing today (Ton)
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM outgoing_wood
        WHERE unit = 'ton'
        AND DATE(created_at) = CURDATE()
    """)
    outgoing_ton = cursor.fetchone()["total"]

    # Incoming revenue
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS incoming_revenue
        FROM incoming_wood
    """)
    incoming_revenue = cursor.fetchone()["incoming_revenue"]

    # Outgoing revenue
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS outgoing_revenue
        FROM outgoing_wood
    """)
    outgoing_revenue = cursor.fetchone()["outgoing_revenue"]

    # Recent transactions
    cursor.execute("""
        SELECT
            DATE_FORMAT(created_at, '%d-%m-%Y') AS date,
            wood_name,
            quantity,
            unit,
            status
        FROM (
            SELECT
                iw.created_at,
                wi.wood_name,
                iw.quantity,
                iw.unit,
                'Incoming' AS status
            FROM incoming_wood iw
            JOIN wood_inventory wi
                ON iw.wood_id = wi.id

            UNION ALL

            SELECT
                ow.created_at,
                wi.wood_name,
                ow.quantity,
                ow.unit,
                'Outgoing' AS status
            FROM outgoing_wood ow
            JOIN wood_inventory wi
                ON ow.wood_id = wi.id
        ) AS transactions
        ORDER BY created_at DESC
        LIMIT 10
    """)

    recent_transactions = cursor.fetchall()
    
    # Company Settings
    cursor.execute("""
    SELECT company_name, gst_number, address, logo
    FROM settings
    WHERE id = 1
""")

    settings = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        settings=settings,
        total_kg=total_kg,
        total_ton=total_ton,
        incoming_kg=incoming_kg,
        incoming_ton=incoming_ton,
        outgoing_kg=outgoing_kg,
        outgoing_ton=outgoing_ton,
        incoming_revenue=incoming_revenue,
        outgoing_revenue=outgoing_revenue,
        recent_transactions=recent_transactions
    )
    
@app.route("/dashboard-data/<period>")
def dashboard_data(period):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if period == "today":
        condition = "DATE(created_at) = CURDATE()"

    elif period == "week":
        condition = "YEARWEEK(created_at, 1) = YEARWEEK(CURDATE(), 1)"

    else:
        condition = """
            MONTH(created_at) = MONTH(CURDATE())
            AND YEAR(created_at) = YEAR(CURDATE())
        """

    # Incoming KG
    cursor.execute(f"""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM incoming_wood
        WHERE unit = 'kg' AND {condition}
    """)
    incoming_kg = cursor.fetchone()["total"]

    # Incoming Ton
    cursor.execute(f"""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM incoming_wood
        WHERE unit = 'ton' AND {condition}
    """)
    incoming_ton = cursor.fetchone()["total"]

    # Outgoing KG
    cursor.execute(f"""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM outgoing_wood
        WHERE unit = 'kg' AND {condition}
    """)
    outgoing_kg = cursor.fetchone()["total"]

    # Outgoing Ton
    cursor.execute(f"""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM outgoing_wood
        WHERE unit = 'ton' AND {condition}
    """)
    outgoing_ton = cursor.fetchone()["total"]

    # Incoming Revenue
    cursor.execute(f"""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM incoming_wood
        WHERE {condition}
    """)
    incoming_revenue = cursor.fetchone()["total"]

    # Outgoing Revenue
    cursor.execute(f"""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM outgoing_wood
        WHERE {condition}
    """)
    outgoing_revenue = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    return jsonify({
        "incoming_kg": incoming_kg,
        "incoming_ton": incoming_ton,
        "outgoing_kg": outgoing_kg,
        "outgoing_ton": outgoing_ton,
        "incoming_revenue": incoming_revenue,
        "outgoing_revenue": outgoing_revenue
    })


from flask import jsonify

@app.route("/chart-data/<period>")
def chart_data(period):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if period == "today":
        incoming_condition = "DATE(iw.created_at) = CURDATE()"
        outgoing_condition = "DATE(ow.created_at) = CURDATE()"

    elif period == "week":
        incoming_condition = """
            YEARWEEK(iw.created_at, 1)
            = YEARWEEK(CURDATE(), 1)
        """

        outgoing_condition = """
            YEARWEEK(ow.created_at, 1)
            = YEARWEEK(CURDATE(), 1)
        """

    else:
        incoming_condition = """
            MONTH(iw.created_at) = MONTH(CURDATE())
            AND YEAR(iw.created_at) = YEAR(CURDATE())
        """

        outgoing_condition = """
            MONTH(ow.created_at) = MONTH(CURDATE())
            AND YEAR(ow.created_at) = YEAR(CURDATE())
        """

    cursor.execute(f"""
        SELECT
            wi.wood_name,
            COALESCE(SUM(iw.quantity), 0) AS incoming
        FROM incoming_wood iw
        JOIN wood_inventory wi ON iw.wood_id = wi.id
        WHERE {incoming_condition}
        GROUP BY wi.wood_name
    """)

    incoming = cursor.fetchall()

    cursor.execute(f"""
        SELECT
            wi.wood_name,
            COALESCE(SUM(ow.quantity), 0) AS outgoing
        FROM outgoing_wood ow
        JOIN wood_inventory wi ON ow.wood_id = wi.id
        WHERE {outgoing_condition}
        GROUP BY wi.wood_name
    """)

    outgoing = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "incoming": incoming,
        "outgoing": outgoing
    })

@app.route("/wood-type-data")
def wood_type_data():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            wood_name,
            quantity
        FROM wood_inventory
    """)
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)


from flask import request, render_template

@app.route("/inventory")
def inventory():

    search_query = request.args.get("search", "").strip()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # -------------------------
    # INVENTORY LIST (WITH SEARCH)
    # -------------------------
    if search_query:
        cursor.execute("""
            SELECT *,
            CASE
                WHEN stock_kg <= minimum_stock
                THEN 'Low Stock'
                ELSE 'In Stock'
            END AS stock_status
            FROM wood_inventory
            WHERE wood_name LIKE %s
            ORDER BY wood_name
        """, (f"%{search_query}%",))
    else:
        cursor.execute("""
            SELECT *,
            CASE
                WHEN stock_kg <= minimum_stock
                THEN 'Low Stock'
                ELSE 'In Stock'
            END AS stock_status
            FROM wood_inventory
            ORDER BY wood_name
        """)

    inventory = cursor.fetchall()

    # -------------------------
    # TOTAL TYPES
    # -------------------------
    cursor.execute("""
        SELECT COUNT(*) AS total_types
        FROM wood_inventory
    """)
    total_types = cursor.fetchone()["total_types"]

    # -------------------------
    # TOTAL KG
    # -------------------------
    cursor.execute("""
        SELECT COALESCE(SUM(quantity),0) AS total_kg
        FROM wood_inventory
        WHERE unit='kg'
    """)
    total_kg = cursor.fetchone()["total_kg"]

    # -------------------------
    # TOTAL TON
    # -------------------------
    cursor.execute("""
        SELECT COALESCE(SUM(quantity),0) AS total_ton
        FROM wood_inventory
        WHERE unit='ton'
    """)
    total_ton = cursor.fetchone()["total_ton"]

    # -------------------------
    # INVENTORY VALUE
    # -------------------------
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount),0) AS inventory_value
        FROM wood_inventory
    """)
    inventory_value = cursor.fetchone()["inventory_value"]

    # -------------------------
    # LOW STOCK COUNT
    # -------------------------
    cursor.execute("""
        SELECT COUNT(*) AS low_stock
        FROM wood_inventory
        WHERE stock_kg <= minimum_stock
    """)
    low_stock = cursor.fetchone()["low_stock"]

    # -------------------------
    # COMPANY SETTINGS
    # -------------------------
    cursor.execute("""
        SELECT company_name, gst_number, address, logo
        FROM settings
        WHERE id = 1
    """)
    settings = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "WoodInventory.html",
        settings=settings,
        inventory=inventory,
        total_types=total_types,
        total_kg=total_kg,
        total_ton=total_ton,
        inventory_value=inventory_value,
        low_stock=low_stock,
        search_query=search_query
    )

@app.route("/add_wood", methods=["POST"])
def add_wood():

    
    wood_name = request.form["wood_name"]
    wood_type = request.form["wood_type"]

    quantity = float(request.form["quantity"])
    unit = request.form["unit"]

    rate = float(request.form["rate"])
    total_amount = float(request.form["total_amount"])

    minimum_stock = request.form.get("minimum_stock", 0)

    # Convert everything to KG for inventory tracking
    if unit == "ton":
        stock_kg = quantity * 1000
    else:
        stock_kg = quantity

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO wood_inventory (
            
            wood_name,
            wood_type,
            quantity,
            unit,
            rate,
            total_amount,
            stock_kg,
            minimum_stock
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        
        wood_name,
        wood_type,
        quantity,
        unit,
        rate,
        total_amount,
        stock_kg,
        minimum_stock
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/inventory")


@app.route("/update_wood", methods=["POST"])
def update_wood():

    wood_id = request.form["wood_id"]

    
    wood_name = request.form["wood_name"]
    wood_type = request.form["wood_type"]

    quantity = float(request.form["quantity"])
    unit = request.form["unit"]

    rate = float(request.form["rate"])
    total_amount = float(request.form["total_amount"])

    minimum_stock = request.form.get("minimum_stock", 0)

    # Convert to KG
    if unit == "ton":
        stock_kg = quantity * 1000
    else:
        stock_kg = quantity

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE wood_inventory
        SET
            
            wood_name=%s,
            wood_type=%s,
            quantity=%s,
            unit=%s,
            rate=%s,
            total_amount=%s,
            stock_kg=%s,
            minimum_stock=%s
        WHERE id=%s
    """, (
        
        wood_name,
        wood_type,
        quantity,
        unit,
        rate,
        total_amount,
        stock_kg,
        minimum_stock,
        wood_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/inventory")

@app.route("/delete_wood/<int:id>")
def delete_wood(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM incoming_wood WHERE wood_id=%s",
        (id,)
    )

    cursor.execute(
        "DELETE FROM outgoing_wood WHERE wood_id=%s",
        (id,)
    )

    cursor.execute(
        "DELETE FROM wood_inventory WHERE id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/inventory")


@app.route("/incoming")
def incoming():

    page = request.args.get('page', 1, type=int)
    per_page = 5

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Dropdown data
    cursor.execute("""
        SELECT id, wood_name, rate
        FROM wood_inventory
    """)
    inventory = cursor.fetchall()

    # Count total records
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM incoming_wood
    """)
    total_records = cursor.fetchone()["total"]

    total_pages = (total_records + per_page - 1) // per_page

    offset = (page - 1) * per_page

    # History table data
    cursor.execute("""
        SELECT
            iw.*,
            wi.wood_name
        FROM incoming_wood iw
        JOIN wood_inventory wi
            ON iw.wood_id = wi.id
        ORDER BY iw.id DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))

    incoming_entries = cursor.fetchall()
    
    # Settings
    cursor.execute("""
        SELECT company_name, gst_number, address, logo
        FROM settings
        WHERE id = 1
    """)
    settings = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "IncomingWood.html",
        settings=settings,
        inventory=inventory,
        incoming_entries=incoming_entries,
        page=page,
        total_pages=total_pages
    )

@app.route("/update_incoming", methods=["POST"])
def update_incoming():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE incoming_wood
        SET
            supplier_name=%s,
            contact_number=%s,
            quantity=%s,
            unit=%s,
            rate=%s,
            total_amount=%s,
            payment_status=%s
        WHERE id=%s
    """, (
        request.form["supplier_name"],
        request.form["contact_number"],
        request.form["quantity"],
        request.form["unit"],
        request.form["rate"],
        request.form["total_amount"],
        request.form["payment_status"],
        request.form["id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/incoming")

@app.route("/delete_incoming/<int:id>")
def delete_incoming(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM incoming_wood WHERE id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    
    return redirect("/incoming")




from io import BytesIO
from flask import make_response
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


@app.route("/incoming_pdf/<int:id>")
def incoming_pdf(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Company Details
    cursor.execute("""
        SELECT *
        FROM settings
        WHERE id = 1
    """)
    company = cursor.fetchone()

    # Incoming Entry
    cursor.execute("""
        SELECT
            iw.*,
            wi.wood_name
        FROM incoming_wood iw
        JOIN wood_inventory wi
            ON iw.wood_id = wi.id
        WHERE iw.id=%s
    """, (id,))

    entry = cursor.fetchone()

    cursor.close()
    conn.close()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    elements = []

    # ==================================
    # COMPANY HEADER
    # ==================================

    elements.append(
        Paragraph(
            f"<b>{company['company_name']}</b>",
            styles["Title"]
        )
    )

    elements.append(
        Paragraph(
            f"GST Number : {company['gst_number']}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"Address : {company['address']}",
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 15))

    # ==================================
    # TITLE
    # ==================================

    title_table = Table(
        [["INCOMING WOOD RECEIPT"]],
        colWidths=[520]
    )

    title_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))

    elements.append(title_table)

    elements.append(Spacer(1, 15))

    # ==================================
    # SUPPLIER DETAILS
    # ==================================

    details_data = [
        ["Supplier Name", entry["supplier_name"]],
        ["Contact Number", entry["contact_number"]],
        ["Invoice Number", entry["invoice_number"]],
        ["Payment Status", entry["payment_status"]]
    ]

    details_table = Table(
        details_data,
        colWidths=[170, 350]
    )

    details_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold')
    ]))

    elements.append(details_table)

    elements.append(Spacer(1, 20))

    # ==================================
    # WOOD DETAILS TABLE
    # ==================================

    wood_table = Table(
        [
            [
                "Wood Name",
                "Quantity",
                "Unit",
                "Rate",
                "Amount"
            ],
            [
                entry["wood_name"],
                str(entry["quantity"]),
                entry["unit"].upper(),
                f"₹ {entry['rate']}",
                f"₹ {entry['total_amount']}"
            ]
        ],
        colWidths=[180, 80, 80, 80, 100]
    )

    wood_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))

    elements.append(wood_table)

    elements.append(Spacer(1, 20))

    # ==================================
    # TOTAL SECTION
    # ==================================

    total_table = Table(
        [
            ["Grand Total", f"₹ {entry['total_amount']}"]
        ],
        colWidths=[400, 120]
    )

    total_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (1,0), 'CENTER')
    ]))

    elements.append(total_table)

    elements.append(Spacer(1, 60))

    # ==================================
    # SIGNATURE
    # ==================================

    signature_table = Table(
        [["", ""]],
        colWidths=[350, 170]
    )

    signature_table.setStyle(TableStyle([
        ('LINEABOVE', (1,0), (1,0), 1, colors.black)
    ]))

    elements.append(signature_table)

    elements.append(
        Paragraph(
            "<para alignment='right'><b>Authorized Signature</b></para>",
            styles["Normal"]
        )
    )

    # ==================================
    # BUILD PDF
    # ==================================

    doc.build(elements)

    pdf = buffer.getvalue()

    buffer.close()

    response = make_response(pdf)

    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        f"inline; filename=IncomingWood_{id}.pdf"
    )

    return response


@app.route("/add_incoming_wood", methods=["POST"])
def add_incoming_wood():

    wood_id = request.form["wood_id"]
    quantity = float(request.form["quantity"])
    unit = request.form["unit"]

    rate = float(request.form["rate"])
    total_amount = float(request.form["total_amount"])

    conn = get_connection()
    cursor = conn.cursor()

    # Save Incoming Entry
    cursor.execute("""
        INSERT INTO incoming_wood
        (
            wood_id,
            supplier_name,
            contact_number,
            gst_number,
            purchase_order_no,
            quantity,
            unit,
            rate,
            total_amount,
            payment_status,
            invoice_number
        )
        VALUES
        (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s
        )
    """, (
        wood_id,
        request.form["supplier_name"],
        request.form["contact_number"],
        request.form["gst_number"],
        request.form["purchase_order_no"],
        quantity,
        unit,
        rate,
        total_amount,
        request.form["payment_status"],
        request.form["invoice_number"]
    ))

    # Update Inventory Stock
    cursor.execute("""
        UPDATE wood_inventory
        SET
            quantity = quantity + %s,
            total_amount = total_amount + %s
        WHERE id = %s
    """, (
        quantity,
        total_amount,
        wood_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/incoming")


@app.route("/outgoing")
def outgoing():

    page = request.args.get("page", 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Inventory Dropdown
    cursor.execute("""
        SELECT
            id,
            wood_name,
            quantity,
            rate,
            unit
        FROM wood_inventory
    """)
    inventory = cursor.fetchall()

    # Total Records
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM outgoing_wood
    """)
    total_records = cursor.fetchone()["total"]

    total_pages = (total_records + per_page - 1) // per_page

    # Paginated History
    cursor.execute("""
        SELECT
            ow.*,
            wi.wood_name
        FROM outgoing_wood ow
        JOIN wood_inventory wi
            ON ow.wood_id = wi.id
        ORDER BY ow.id DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))

    outgoing_entries = cursor.fetchall()

    # Settings
    cursor.execute("""
        SELECT company_name, gst_number, address, logo
        FROM settings
        WHERE id = 1
    """)
    settings = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "OutgoingWood.html",
        settings=settings,
        inventory=inventory,
        outgoing_entries=outgoing_entries,
        page=page,
        total_pages=total_pages
    )

@app.route("/add_outgoing_wood", methods=["POST"])
def add_outgoing_wood():

    conn = get_connection()
    cursor = conn.cursor()

    wood_id = request.form["wood_id"]
    customer_name = request.form["customer_name"]
    contact_number = request.form["contact_number"]
    gst_number = request.form["gst_number"]
    dispatch_order_no = request.form["dispatch_order_no"]

    dispatch_date = request.form.get("dispatch_date")  # optional
    quantity = int(request.form["quantity"])
    unit = request.form["unit"]
    rate = float(request.form["rate"])
    total_amount = float(request.form["total_amount"])

    payment_mode = request.form["payment_mode"]
    payment_status = request.form.get("payment_status", "Pending")

    # ---------------- STOCK CHECK ----------------
    cursor.execute("""
        SELECT quantity
        FROM wood_inventory
        WHERE id=%s
    """, (wood_id,))

    stock = cursor.fetchone()

    if not stock or stock[0] < quantity:
        cursor.close()
        conn.close()
        return "Insufficient Stock"

    # ---------------- INSERT ----------------
    cursor.execute("""
        INSERT INTO outgoing_wood (
            wood_id,
            customer_name,
            contact_number,
            gst_number,
            dispatch_order_no,
            dispatch_date,
            quantity,
            unit,
            rate,
            total_amount,
            payment_mode,
            payment_status
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        wood_id,
        customer_name,
        contact_number,
        gst_number,
        dispatch_order_no,
        dispatch_date,
        quantity,
        unit,
        rate,
        total_amount,
        payment_mode,
        payment_status
    ))

    # ---------------- UPDATE STOCK ----------------
    cursor.execute("""
        UPDATE wood_inventory
        SET quantity = quantity - %s
        WHERE id = %s
    """, (quantity, wood_id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/outgoing")



@app.route("/update_outgoing", methods=["POST"])
def update_outgoing():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE outgoing_wood
        SET
            wood_id=%s,
            customer_name=%s,
            contact_number=%s,
            quantity=%s,
            unit=%s,
            rate=%s,
            total_amount=%s,
            payment_status=%s
        WHERE id=%s
    """, (
        request.form["wood_id"],
        request.form["customer_name"],
        request.form["contact_number"],
        request.form["quantity"],
        request.form["unit"],
        request.form["rate"],
        request.form["total_amount"],
        request.form["payment_status"],
        request.form["id"]
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/outgoing#history")


@app.route("/delete_outgoing/<int:id>")
def delete_outgoing(id):

    conn = get_connection()
    cursor = conn.cursor()

    # Get outgoing entry details first
    cursor.execute("""
        SELECT
            wood_id,
            quantity,
            total_amount
        FROM outgoing_wood
        WHERE id = %s
    """, (id,))

    entry = cursor.fetchone()

    if entry:

        wood_id = entry[0]
        quantity = entry[1]
        total_amount = entry[2]

        # Restore stock back to inventory
        cursor.execute("""
            UPDATE wood_inventory
            SET
                quantity = quantity + %s,
                total_amount = total_amount + %s
            WHERE id = %s
        """, (
            quantity,
            total_amount,
            wood_id
        ))

        # Delete outgoing history
        cursor.execute("""
            DELETE FROM outgoing_wood
            WHERE id = %s
        """, (id,))

        conn.commit()

    cursor.close()
    conn.close()

    return redirect("/outgoing#history")

@app.route("/outgoing_pdf/<int:id>")
def outgoing_pdf(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Company Details
    cursor.execute("""
        SELECT *
        FROM settings
        WHERE id = 1
    """)
    company = cursor.fetchone()

    # Outgoing Entry
    cursor.execute("""
        SELECT
            ow.*,
            wi.wood_name
        FROM outgoing_wood ow
        JOIN wood_inventory wi
            ON ow.wood_id = wi.id
        WHERE ow.id = %s
    """, (id,))

    entry = cursor.fetchone()

    cursor.close()
    conn.close()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    elements = []

    # ==================================
    # COMPANY HEADER
    # ==================================

    elements.append(
        Paragraph(
            f"<b>{company['company_name']}</b>",
            styles["Title"]
        )
    )

    elements.append(
        Paragraph(
            f"GST Number : {company['gst_number']}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"Address : {company['address']}",
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 15))

    # ==================================
    # TITLE
    # ==================================

    title_table = Table(
        [["OUTGOING WOOD DISPATCH RECEIPT"]],
        colWidths=[520]
    )

    title_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))

    elements.append(title_table)

    elements.append(Spacer(1, 15))

    # ==================================
    # CUSTOMER DETAILS
    # ==================================

    details_data = [
        ["Customer Name", entry["customer_name"]],
        ["Contact Number", entry["contact_number"]],
        ["Dispatch Order No", entry["dispatch_order_no"]],
        ["Payment Mode", entry["payment_mode"]],
        ["Payment Status", entry["payment_status"]]
    ]

    details_table = Table(
        details_data,
        colWidths=[170, 350]
    )

    details_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold')
    ]))

    elements.append(details_table)

    elements.append(Spacer(1, 20))

    # ==================================
    # WOOD DETAILS TABLE
    # ==================================

    wood_table = Table(
        [
            [
                "Wood Name",
                "Quantity",
                "Unit",
                "Rate",
                "Amount"
            ],
            [
                entry["wood_name"],
                str(entry["quantity"]),
                entry["unit"].upper(),
                f"₹ {entry['rate']}",
                f"₹ {entry['total_amount']}"
            ]
        ],
        colWidths=[180, 80, 80, 80, 100]
    )

    wood_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))

    elements.append(wood_table)

    elements.append(Spacer(1, 20))

    # ==================================
    # TOTAL SECTION
    # ==================================

    total_table = Table(
        [
            ["Grand Total", f"₹ {entry['total_amount']}"]
        ],
        colWidths=[400, 120]
    )

    total_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (1,0), 'CENTER')
    ]))

    elements.append(total_table)

    elements.append(Spacer(1, 60))

    # ==================================
    # SIGNATURE
    # ==================================

    signature_table = Table(
        [["", ""]],
        colWidths=[350, 170]
    )

    signature_table.setStyle(TableStyle([
        ('LINEABOVE', (1,0), (1,0), 1, colors.black)
    ]))

    elements.append(signature_table)

    elements.append(
        Paragraph(
            "<para alignment='right'><b>Authorized Signature</b></para>",
            styles["Normal"]
        )
    )

    # ==================================
    # BUILD PDF
    # ==================================

    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)

    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        f"inline; filename=OutgoingWood_{id}.pdf"
    )

    return response

@app.route("/suppliers")
def suppliers():

    search_query = request.args.get("search", "").strip()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if search_query:

        query = """
            SELECT *
            FROM suppliers
            WHERE supplier_name LIKE %s
            OR contact_person LIKE %s
            OR phone LIKE %s
            OR email LIKE %s
            OR gst LIKE %s
            OR city LIKE %s
        """

        search_term = f"%{search_query}%"

        cursor.execute(
            query,
            (
                search_term,
                search_term,
                search_term,
                search_term,
                search_term,
                search_term
            )
        )

    else:
        cursor.execute("SELECT * FROM suppliers")

    suppliers = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS total FROM suppliers")
    total_suppliers = cursor.fetchone()["total"]
    
    # Company Settings
    cursor.execute("""
    SELECT company_name, gst_number, address, logo
    FROM settings
    WHERE id = 1
""")

    settings = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "SupplierManagement.html",
        settings=settings,
        suppliers=suppliers,
        total_suppliers=total_suppliers,
        search_query=search_query
    )

@app.route("/delete_supplier/<int:id>")
def delete_supplier(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM suppliers WHERE id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/suppliers")

@app.route("/update_supplier", methods=["POST"])
def update_supplier():

    supplier_id = request.form["supplier_id"]

    supplier_name = request.form["supplier_name"]
    contact_person = request.form["contact_person"]
    phone = request.form["phone"]
    email = request.form["email"]
    gst = request.form["gst"]
    address = request.form["address"]
    city = request.form["city"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE suppliers
        SET supplier_name=%s,
            contact_person=%s,
            phone=%s,
            email=%s,
            gst=%s,
            address=%s,
            city=%s
        WHERE id=%s
    """,
    (
        supplier_name,
        contact_person,
        phone,
        email,
        gst,
        address,
        city,
        supplier_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/suppliers")


@app.route("/customers")
def customers():

    search = request.args.get("search", "")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if search:
        cursor.execute("""
            SELECT *
            FROM customers
            WHERE customer_name LIKE %s
            OR phone LIKE %s
            OR gst LIKE %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))
    else:
        cursor.execute("SELECT * FROM customers")

    customers = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS total FROM customers")
    total_customers = cursor.fetchone()["total"]
    
    # Company Settings
    cursor.execute("""
    SELECT company_name, gst_number, address, logo
    FROM settings
    WHERE id = 1
""")

    settings = cursor.fetchone()

    conn.close()

    return render_template(
        "CustomerManagement.html",
        settings=settings,
        customers=customers,
        total_customers=total_customers,
        search_query=search
    )


@app.route("/add_customer", methods=["POST"])
def add_customer():

    customer_name = request.form["customer_name"]
    contact_person = request.form["contact_person"]
    phone = request.form["phone"]
    city = request.form["city"]
    gst = request.form["gst"]
    email = request.form["email"]
    address = request.form["address"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO customers
        (customer_name, contact_person, phone,
        city, gst, email, address)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        customer_name,
        contact_person,
        phone,
        city,
        gst,
        email,
        address
    ))

    conn.commit()
    conn.close()

    return redirect("/customers")


@app.route("/update_customer", methods=["POST"])
def update_customer():

    customer_id = request.form["customer_id"]

    customer_name = request.form["customer_name"]
    contact_person = request.form["contact_person"]
    phone = request.form["phone"]
    city = request.form["city"]
    gst = request.form["gst"]
    email = request.form["email"]
    address = request.form["address"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE customers
        SET customer_name=%s,
            contact_person=%s,
            phone=%s,
            city=%s,
            gst=%s,
            email=%s,
            address=%s
        WHERE id=%s
    """, (
        customer_name,
        contact_person,
        phone,
        city,
        gst,
        email,
        address,
        customer_id
    ))

    conn.commit()
    conn.close()

    return redirect("/customers")


@app.route("/delete_customer/<int:id>")
def delete_customer(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM customers WHERE id=%s",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/customers")

@app.route("/reports")
def reports():

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if from_date and to_date:
        date_condition = """
            WHERE DATE(created_at) BETWEEN %s AND %s
        """
        params = (from_date, to_date)
    else:
        date_condition = ""
        params = ()

    # Revenue (Sales)

    cursor.execute(f"""
        SELECT COALESCE(SUM(total_amount),0) AS revenue
        FROM outgoing_wood
        {date_condition}
    """, params)

    total_revenue = cursor.fetchone()["revenue"]

    # Purchase Cost

    cursor.execute(f"""
        SELECT COALESCE(SUM(total_amount),0) AS purchase_cost
        FROM incoming_wood
        {date_condition}
    """, params)

    purchase_cost = cursor.fetchone()["purchase_cost"]

    # Imports KG / Ton

    cursor.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN LOWER(unit)='kg' THEN quantity ELSE 0 END),0) AS import_kg,
            COALESCE(SUM(CASE WHEN LOWER(unit)='ton' THEN quantity ELSE 0 END),0) AS import_ton
        FROM incoming_wood
        {date_condition}
    """, params)

    imports = cursor.fetchone()

    total_imports_kg = imports["import_kg"]
    total_imports_ton = imports["import_ton"]

    # Exports KG / Ton

    cursor.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN LOWER(unit)='kg' THEN quantity ELSE 0 END),0) AS export_kg,
            COALESCE(SUM(CASE WHEN LOWER(unit)='ton' THEN quantity ELSE 0 END),0) AS export_ton
        FROM outgoing_wood
        {date_condition}
    """, params)

    exports = cursor.fetchone()

    total_exports_kg = exports["export_kg"]
    total_exports_ton = exports["export_ton"]

    # Profit

    total_profit = total_revenue - purchase_cost
    
    
    # Top Customers

    cursor.execute(f"""
    SELECT
        customer_name,
        SUM(total_amount) AS sales
    FROM outgoing_wood
    {date_condition}
    GROUP BY customer_name
    ORDER BY sales DESC
    LIMIT 5
""", params)

    top_customers = cursor.fetchall()


# Top Suppliers

    cursor.execute(f"""
    SELECT
        supplier_name,

        SUM(
            CASE WHEN LOWER(unit)='kg'
            THEN quantity ELSE 0 END
        ) AS supply_kg,

        SUM(
            CASE WHEN LOWER(unit)='ton'
            THEN quantity ELSE 0 END
        ) AS supply_ton

    FROM incoming_wood
    {date_condition}

    GROUP BY supplier_name

    ORDER BY
        SUM(CASE WHEN LOWER(unit)='kg' THEN quantity ELSE 0 END) +
        SUM(CASE WHEN LOWER(unit)='ton' THEN quantity ELSE 0 END) DESC

    LIMIT 5
""", params)

    top_suppliers = cursor.fetchall()
    
    # Company Settings
    cursor.execute("""
    SELECT company_name, gst_number, address, logo
    FROM settings
    WHERE id = 1
""")

    settings = cursor.fetchone()
    

    cursor.close()
    conn.close()

    return render_template(
        "RequirementAna.html",
        settings=settings,
        total_revenue=total_revenue,
        total_profit=total_profit,
        total_imports_kg=total_imports_kg,
        total_imports_ton=total_imports_ton,
        total_exports_kg=total_exports_kg,
        total_exports_ton=total_exports_ton,
        top_customers=top_customers,
        top_suppliers=top_suppliers,
        from_date=from_date,
        to_date=to_date
    )
    
@app.route("/export-pdf")
def export_pdf():

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    if not from_date or not to_date:
        return "Please select both dates."

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    params = (from_date, to_date)

    # ==========================
    # Total Revenue
    # ==========================

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount),0) AS revenue
        FROM outgoing_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    total_revenue = cursor.fetchone()["revenue"]

    # ==========================
    # Purchase Cost
    # ==========================

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount),0) AS purchase_cost
        FROM incoming_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    purchase_cost = cursor.fetchone()["purchase_cost"]

    total_profit = total_revenue - purchase_cost

    # ==========================
    # Total Imports
    # ==========================

    cursor.execute("""
        SELECT
            COALESCE(SUM(
                CASE WHEN unit='kg'
                THEN quantity ELSE 0 END
            ),0) AS import_kg,

            COALESCE(SUM(
                CASE WHEN unit='ton'
                THEN quantity ELSE 0 END
            ),0) AS import_ton

        FROM incoming_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    imports = cursor.fetchone()

    # ==========================
    # Total Exports
    # ==========================

    cursor.execute("""
        SELECT
            COALESCE(SUM(
                CASE WHEN unit='kg'
                THEN quantity ELSE 0 END
            ),0) AS export_kg,

            COALESCE(SUM(
                CASE WHEN unit='ton'
                THEN quantity ELSE 0 END
            ),0) AS export_ton

        FROM outgoing_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    exports = cursor.fetchone()

    # ==========================
    # Incoming Details
    # ==========================

    cursor.execute("""
        SELECT
            wi.wood_name,
            iw.supplier_name,
            iw.quantity,
            iw.unit,
            iw.rate,
            iw.total_amount,
            DATE(iw.created_at) AS date

        FROM incoming_wood iw

        JOIN wood_inventory wi
            ON iw.wood_id = wi.id

        WHERE DATE(iw.created_at)
        BETWEEN %s AND %s

        ORDER BY iw.created_at DESC
    """, params)

    incoming_records = cursor.fetchall()

    # ==========================
    # Outgoing Details
    # ==========================

    cursor.execute("""
        SELECT
            wi.wood_name,
            ow.customer_name,
            ow.quantity,
            ow.unit,
            ow.rate,
            ow.total_amount,
            DATE(ow.created_at) AS date

        FROM outgoing_wood ow

        JOIN wood_inventory wi
            ON ow.wood_id = wi.id

        WHERE DATE(ow.created_at)
        BETWEEN %s AND %s

        ORDER BY ow.created_at DESC
    """, params)

    outgoing_records = cursor.fetchall()

    


    
    # Get company settings
    cursor.execute("""
    SELECT company_name, gst_number, address, logo
    FROM settings
    WHERE id = 1
""")

    settings = cursor.fetchone()

    cursor.close()
    conn.close()

    # ==========================
    # Render HTML Template
    # ==========================

    html = render_template(
        "report_pdf.html",
        settings=settings,

        from_date=from_date,
        to_date=to_date,

        total_revenue=total_revenue,
        purchase_cost=purchase_cost,
        total_profit=total_profit,
        current_date=datetime.now().strftime("%d-%m-%Y"),

        imports=imports,
        exports=exports,

        incoming_records=incoming_records,
        outgoing_records=outgoing_records,

        
    )

    # ==========================
    # Convert HTML To PDF
    # ==========================

    pdf = BytesIO()

    pisa.CreatePDF(
        html,
        dest=pdf
    )

    response = make_response(
        pdf.getvalue()
    )

    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        f"attachment; filename=Jondhale_Report_{from_date}_to_{to_date}.pdf"
    )

    return response


@app.route("/export-incoming-pdf")
def export_incoming_pdf():

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    if not from_date or not to_date:
        return "Please select both dates."

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    params = (from_date, to_date)

    # ==========================
    # Total Revenue
    # ==========================

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount),0) AS revenue
        FROM outgoing_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    total_revenue = cursor.fetchone()["revenue"]

    # ==========================
    # Purchase Cost
    # ==========================

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount),0) AS purchase_cost
        FROM incoming_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    purchase_cost = cursor.fetchone()["purchase_cost"]

    total_profit = total_revenue - purchase_cost

    # ==========================
    # Total Imports
    # ==========================

    cursor.execute("""
        SELECT
            COALESCE(SUM(
                CASE WHEN unit='kg'
                THEN quantity ELSE 0 END
            ),0) AS import_kg,

            COALESCE(SUM(
                CASE WHEN unit='ton'
                THEN quantity ELSE 0 END
            ),0) AS import_ton

        FROM incoming_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    imports = cursor.fetchone()

    # ==========================
    # Total Exports
    # ==========================

    cursor.execute("""
        SELECT
            COALESCE(SUM(
                CASE WHEN unit='kg'
                THEN quantity ELSE 0 END
            ),0) AS export_kg,

            COALESCE(SUM(
                CASE WHEN unit='ton'
                THEN quantity ELSE 0 END
            ),0) AS export_ton

        FROM outgoing_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    exports = cursor.fetchone()

    # ==========================
    # Incoming Details
    # ==========================

    cursor.execute("""
        SELECT
            wi.wood_name,
            iw.supplier_name,
            iw.quantity,
            iw.unit,
            iw.rate,
            iw.total_amount,
            DATE(iw.created_at) AS date

        FROM incoming_wood iw

        JOIN wood_inventory wi
            ON iw.wood_id = wi.id

        WHERE DATE(iw.created_at)
        BETWEEN %s AND %s

        ORDER BY iw.created_at DESC
    """, params)

    incoming_records = cursor.fetchall()
    html = render_template(
        "incoming_report.html",
        settings=settings,

        from_date=from_date,
        to_date=to_date,

        total_revenue=total_revenue,
        purchase_cost=purchase_cost,
        total_profit=total_profit,
        current_date=datetime.now().strftime("%d-%m-%Y"),

        imports=imports,
        exports=exports,

        incoming_records=incoming_records,
    )

    # ==========================
    # Convert HTML To PDF
    # ==========================

    pdf = BytesIO()

    pisa.CreatePDF(
        html,
        dest=pdf
    )

    response = make_response(
        pdf.getvalue()
    )

    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        f"attachment; filename=Jondhale_Report_{from_date}_to_{to_date}.pdf"
    )

    return response



    
    
@app.route("/export-outgoing-pdf")
def export_outgoing_pdf():

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    if not from_date or not to_date:
        return "Please select both dates."

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    params = (from_date, to_date)

    # ==========================
    # Total Revenue
    # ==========================

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount),0) AS revenue
        FROM outgoing_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    total_revenue = cursor.fetchone()["revenue"]

    # ==========================
    # Purchase Cost
    # ==========================

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount),0) AS purchase_cost
        FROM incoming_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    purchase_cost = cursor.fetchone()["purchase_cost"]

    total_profit = total_revenue - purchase_cost

    # ==========================
    # Total Imports
    # ==========================

    cursor.execute("""
        SELECT
            COALESCE(SUM(
                CASE WHEN unit='kg'
                THEN quantity ELSE 0 END
            ),0) AS import_kg,

            COALESCE(SUM(
                CASE WHEN unit='ton'
                THEN quantity ELSE 0 END
            ),0) AS import_ton

        FROM incoming_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    imports = cursor.fetchone()

    # ==========================
    # Total Exports
    # ==========================

    cursor.execute("""
        SELECT
            COALESCE(SUM(
                CASE WHEN unit='kg'
                THEN quantity ELSE 0 END
            ),0) AS export_kg,

            COALESCE(SUM(
                CASE WHEN unit='ton'
                THEN quantity ELSE 0 END
            ),0) AS export_ton

        FROM outgoing_wood
        WHERE DATE(created_at) BETWEEN %s AND %s
    """, params)

    exports = cursor.fetchone()

    # ==========================
    # Incoming Details
    # ==========================

    cursor.execute("""
        SELECT
            wi.wood_name,
            ow.customer_name,
            ow.quantity,
            ow.unit,
            ow.rate,
            ow.total_amount,
            DATE(ow.created_at) AS date

        FROM outgoing_wood ow

        JOIN wood_inventory wi
            ON ow.wood_id = wi.id

        WHERE DATE(ow.created_at)
        BETWEEN %s AND %s

        ORDER BY ow.created_at DESC
    """, params)

    outgoing_records = cursor.fetchall()
    html = render_template(
        "outgoing_report.html",
        settings=settings,

        from_date=from_date,
        to_date=to_date,

        total_revenue=total_revenue,
        purchase_cost=purchase_cost,
        total_profit=total_profit,
        current_date=datetime.now().strftime("%d-%m-%Y"),

        imports=imports,
        exports=exports,

        outgoing_records=outgoing_records
        

        
    )

    # ==========================
    # Convert HTML To PDF
    # ==========================

    pdf = BytesIO()

    pisa.CreatePDF(
        html,
        dest=pdf
    )

    response = make_response(
        pdf.getvalue()
    )

    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        f"attachment; filename=Jondhale_Report_{from_date}_to_{to_date}.pdf"
    )

    return response



    
@app.route("/settings")
def settings():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM settings WHERE id = 1")
    settings = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "Setting.html",
        settings=settings
    )


from werkzeug.utils import secure_filename
import os
from flask import flash


@app.route("/save-company-info", methods=["POST"])
def save_company_info():

    company_name = request.form.get("company_name")
    gst_number = request.form.get("gst_number")
    address = request.form.get("address")

    logo_file = request.files.get("logo")

    logo_name = None

    if logo_file and logo_file.filename != "":
        logo_name = secure_filename(logo_file.filename)

        upload_folder = os.path.join("static", "uploads")

        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        logo_file.save(
            os.path.join(upload_folder, logo_name)
        )

    conn = get_connection()
    cursor = conn.cursor()

    if logo_name:
        cursor.execute("""
            UPDATE settings
            SET
                company_name = %s,
                gst_number = %s,
                address = %s,
                logo = %s
            WHERE id = 1
        """, (
            company_name,
            gst_number,
            address,
            logo_name
        ))
    else:
        cursor.execute("""
            UPDATE settings
            SET
                company_name = %s,
                gst_number = %s,
                address = %s
            WHERE id = 1
        """, (
            company_name,
            gst_number,
            address
        ))

    conn.commit()

    cursor.close()
    conn.close()
    
    flash("Company information saved successfully!", "success")

    return redirect("/settings")

@app.route("/update-password", methods=["POST"])
def change_password():

    current_password = request.form["current_password"]
    new_password = request.form["new_password"]
    confirm_password = request.form["confirm_password"]

    if new_password != confirm_password:
        flash("New Password and Confirm Password do not match!")
        return redirect("/settings")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE id = 1"
    )

    user = cursor.fetchone()

    if not user:
        flash("User not found!")
        return redirect("/settings")

    if user["password"] != current_password:
        flash("Current Password is incorrect!")
        return redirect("/settings")

    cursor.execute(
        """
        UPDATE users
        SET password=%s
        WHERE id=1
        """,
        (new_password,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash("Password Updated Successfully ✓")

    return redirect("/settings")



@app.route("/add_supplier", methods=["POST"])
def add_supplier():

    supplier_name = request.form["supplier_name"]
    contact_person = request.form["contact_person"]
    phone = request.form["phone"]
    email = request.form["email"]
    gst = request.form["gst"]
    address = request.form["address"]
    city = request.form["city"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO suppliers
        (supplier_name, contact_person, phone, email, gst, address, city)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """,
    (
        supplier_name,
        contact_person,
        phone,
        email,
        gst,
        address,
        city
    ))
    
    


    

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/suppliers")


@app.route("/logout")
def logout():
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)