import streamlit as st #require
from pathlib import Path
import sqlite3 
import qrcode #require
from io import BytesIO
import base64
import datetime
import pandas as pd #require
from datetime import datetime
import bcrypt #require
from streamlit_cookies_manager import EncryptedCookieManager #require
from PIL import Image, ImageDraw, ImageFont
import os
import uuid

# Read password from environment variables or secrets
ENCRYPTION_PASSWORD = os.getenv("COOKIE_PASSWORD", "default_fallback_password")

# Initialize cookies manager
cookies = EncryptedCookieManager(password=ENCRYPTION_PASSWORD)

# Ensure cookies are ready
if not cookies.ready():
    st.stop()

# Function to load user credentials from the database
def get_user_data():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(project_dir, "password_database.db")

    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"Database 'password_database.db' not found in: {project_dir}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT username, password FROM table_name')  # Adjust table_name
    users = cur.fetchall()
    conn.close()

    return {user[0]: user[1] for user in users}  # Return user/password pairs


def authenticate_user(username, password, user_data):
    if username in user_data:
        hashed_password = user_data[username]
        return bcrypt.checkpw(password.encode(), hashed_password.encode())
    return False


def login():
    st.header("Login Page")
    try:
        user_data = get_user_data()  # Fetch user data from database
    except Exception as e:
        st.error(f"Error loading user data: {e}")
        return

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate_user(username, password, user_data):
            session_id = str(uuid.uuid4())  # Generate unique session ID
            cookies["session_id"] = session_id  # Store session ID in cookies
            cookies["username"] = username     # Store username in cookies
            st.session_state["logged_in"] = True
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("Invalid Username or Password")


def check_login_status():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # Check for session_id and username in cookies
    session_id = cookies.get("session_id")
    username = cookies.get("username")

    if session_id and username:
        st.session_state["logged_in"] = True
    else:
        st.session_state["logged_in"] = False

    return st.session_state["logged_in"]


def logout_user():
    cookies["session_id"] = ""  # Clear the session cookie
    cookies["username"] = ""
    st.session_state["logged_in"] = False
    st.success("You have been logged out successfully!")
    st.rerun()


# Step 2: Check login status before showing the main content
if cookies.ready():
    # Initialize session_state if not present
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # Check if the user is logged in by reading the cookie or session state
    if cookies.get("logged_in") == "True" or st.session_state["logged_in"]:
        # --- Rest of your app code follows here ---
        # Create or connect to the SQLite database
        def get_db_connection():
            """
            Dynamically locate the 'parts_database.db' in the 'data' folder relative to the script's directory.
            """
            # Get the directory where the script is located
            project_dir = os.path.dirname(os.path.abspath(__file__))

            # Define the path to the database file in the 'data' folder
            db_path = os.path.join(project_dir, "parts_database.db")

            # Check if the database file exists
            if not os.path.isfile(db_path):
                raise FileNotFoundError(f"Database 'parts_database.db' not found in: {os.path.join(project_dir, 'data')}")

            # Connect to the database
            conn = sqlite3.connect(db_path)
            return conn

        # Usage Example:
        conn = get_db_connection()  # Get the connection
        cursor = conn.cursor() # Create a cursor
        # Create the parts table if it doesn't exist
        

        # Create the stock movements table if it doesn't exist
        

        # Function to insert part data
        def insert_data(part_name, part_no, part_type, process, tool_type, qr_id, component):
            cursor.execute('''
                INSERT INTO stock_movements (qr_id, action, quantity, date_time)
                VALUES (?, ?, ?, ?)
            ''', (selected_qr_id, action, quantity, datetime.now()))

            conn.commit()

        # Function to insert stock movement data
        def insert_stock_movement(part_name, action, quantity):
            date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Format without microseconds
            cursor.execute('''
            INSERT INTO stock_movements (part_name, action, quantity, date_time)
            VALUES (?, ?, ?, ?)
            ''', (part_name, action, quantity, date_time))
            conn.commit()

        # Function to generate QR code images
        def generate_qr(qr_id, embed_text=True):
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_id)
            qr.make(fit=True)
            qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

            if embed_text:
                # Add text (QR ID) below the QR Code
                font_size = 20
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except IOError:
                    font = ImageFont.load_default()

                # Use textbbox to get the bounding box of the text
                draw = ImageDraw.Draw(qr_image)
                bbox = draw.textbbox((0, 0), qr_id, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Create a new image to combine QR Code and text
                combined_height = qr_image.size[1] + text_height + 20  # Add padding for text
                combined_image = Image.new("RGBA", (qr_image.size[0], combined_height), "white")

                # Paste QR Code onto the new image
                combined_image.paste(qr_image, (0, 0))

                # Draw the QR ID below the QR Code
                text_position = ((combined_image.size[0] - text_width) // 2, qr_image.size[1] + -10)  # Centered below
                draw = ImageDraw.Draw(combined_image)
                draw.text(text_position, qr_id, fill="black", font=font)

                return combined_image

            return qr_image

        # Function to save QR codes as base64-encoded images
        def save_qr_images(qr_ids, embed_text=False):
            qr_images = []
            for qr_id in qr_ids:
                img = generate_qr(qr_id, embed_text=embed_text)
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                buffer.seek(0)
                img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                qr_images.append(img_base64)
            return qr_images
        @st.cache_data
        def fetch_unique_values(column_name):
            cursor.execute(f"SELECT DISTINCT {column_name} FROM parts")
            return [row[0] for row in cursor.fetchall()]

        

        # Sidebar navigation
        page = st.sidebar.radio("Select a Page", ("Part Management", "Stock Management"))

        if page == "Part Management":
            # --- Insert New Data Section ---
            # Streamlit app
            st.title("Part Management")
            st.header("Insert New Part Data")
            with st.form("insert_form"):
                part_name = st.text_input("Part Name")
                part_no = st.text_input("Part Number")
                part_type = st.text_input("Type")
                process = st.text_input("Process")
                tool_type = st.text_input("Tool Type")
                qr_id = st.text_input("QR ID")
                component = st.text_input("Component")
                submit_button = st.form_submit_button(label="Insert Data")

                if submit_button:
                    insert_data(part_name, part_no, part_type, process, tool_type, qr_id, component)
                    st.success("New part data inserted successfully!")

                    if qr_id:
                        # Generate and display the QR code image for the inserted part
                        img = generate_qr(qr_id)
                        buffer = BytesIO()
                        img.save(buffer, format="PNG")
                        buffer.seek(0)
                        st.image(buffer, caption=f"QR Code for {qr_id}", use_column_width=True)

            # --- Delete Data Section ---
            st.header("Delete Part Data")

            # Fetch all parts from the database
            cursor.execute('SELECT * FROM parts')
            rows = cursor.fetchall()

            if len(rows) > 0:
                delete_qr_ids = [row[6] for row in rows]  # Get QR IDs for deletion

                # Dropdown to select a part by QR ID
                selected_qr_id = st.selectbox("Select QR ID to Delete", delete_qr_ids)

                if st.button("Delete Selected Part"):
                    # Delete the part from the database using the selected QR ID
                    cursor.execute('DELETE FROM parts WHERE qr_id = ?', (selected_qr_id,))
                    conn.commit()
                    st.success(f"Part with QR ID {selected_qr_id} has been deleted!")
            else:
                st.write("No parts available to delete.")
            # --- Download QR Code Section ---
            st.header("Download QR Code for Selected Part")

            # Fetch QR IDs from the database to create a dropdown menu
            cursor.execute('SELECT qr_id, part_name FROM parts')
            rows = cursor.fetchall()
            qr_ids = [row[0] for row in rows]  # List of QR IDs

            if qr_ids:
                # Dropdown for selecting a QR ID
                selected_qr_id = st.selectbox("Select a Part by QR ID", qr_ids)

                if selected_qr_id:
                    # Generate the QR code with the selected QR ID and text embedded
                    qr_image = generate_qr(selected_qr_id, embed_text=True)

                    # Save the QR Code image to a buffer
                    buffer = BytesIO()
                    qr_image.save(buffer, format="PNG")
                    buffer.seek(0)

                    # Center the QR code image using markdown and CSS
                    st.markdown(
                        f"""
                        <div style="display: flex; justify-content: center;">
                            <img src="data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}" width="50%" />
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                

                    # Now we add the actual Streamlit download button, which Streamlit will handle itself.
                    st.download_button(
                        label="Download QR Code as PNG",
                        data=buffer,
                        file_name=f"{selected_qr_id}_qr_code.png",
                        mime="image/png"
                    )

            else:
                st.warning("No QR IDs available.")

            # --- Display Data Section ---
            st.header("View and Search Parts")

            # Sidebar filters
            search_query = st.sidebar.text_input("Search by Part Name", "")
            search_part_no = st.sidebar.text_input("Search by Part Number", "")
            

            search_process = st.sidebar.selectbox(
                "Filter by Process", ["All"] + fetch_unique_values("process")
            )
            search_tool_type = st.sidebar.selectbox(
                "Filter by Tool Type", ["All"] + fetch_unique_values("tool_type")
            )
            search_component = st.sidebar.text_input("Search by Component", "")

            # Apply filters to the database
            query = 'SELECT * FROM parts WHERE 1=1'
            params = []

            if search_query:
                query += ' AND part_name LIKE ?'
                params.append(f'%{search_query}%')
            if search_part_no:
                query += ' AND part_no LIKE ?'
                params.append(f'%{search_part_no}%')
            if search_process != 'All':
                query += ' AND process = ?'
                params.append(search_process)
            if search_tool_type != 'All':
                query += ' AND tool_type = ?'
                params.append(search_tool_type)
            if search_component:
                query += ' AND component LIKE ?'
                params.append(f'%{search_component}%')

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Calculate total stock for each part (stock in - stock out)
            total_stock = {}
            for row in rows:
                qr_id = row[6]  # qr_id is at index 6
                cursor.execute('''
                    SELECT qr_id, 
                        SUM(CASE WHEN action = 'Stock In' THEN quantity ELSE 0 END) - 
                        SUM(CASE WHEN action = 'Stock Out' THEN quantity ELSE 0 END)
                    FROM stock_movements
                    WHERE qr_id IN ({}) 
                    GROUP BY qr_id
                '''.format(','.join(['?']*len(rows))), [row[6] for row in rows])  # Pass all qr_ids
                total_stock_results = cursor.fetchall()

                total_stock = {row[0]: row[1] if row[1] else 0 for row in total_stock_results}


            # Add QR codes to each row
            qr_codes = save_qr_images([row[6] for row in rows])  # qr_id is at index 6

            # Display headers with Total Stock column (beside QR Code)
            
            # Add a custom style to prevent text wrapping
            st.write("""
                <style>
                .no-wrap {
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                </style>
            """, unsafe_allow_html=True)

            st.write("### Parts Table")
            col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 3, 2])  # Adjust column layout if necessary
            with col1:
                st.markdown('<div style="text-align: center;" class="small-font"><b>Part Name</b></div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div style="text-align: center;" class="small-font"><b>Part Number</b></div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div style="text-align: center;" class="small-font"><b>QR ID</b></div>', unsafe_allow_html=True)
            with col4:
                st.markdown('<div style="text-align: center;" class="small-font"><b>Component</b></div>', unsafe_allow_html=True)
            with col5:
                st.markdown('<div style="text-align: center;" class="small-font"><b>Total Stock</b></div>', unsafe_allow_html=True)

            # Display the data in a table
            for idx, row in enumerate(rows):
                col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 3, 2])  # Adjust column layout if necessary
                with col1:
                    st.markdown(f'<div style="text-align: center; display: flex; justify-content: center; align-items: center; width: 100%;" class="small-font">{row[1]}</div>', unsafe_allow_html=True)  # part_name
                with col2:
                    st.markdown(f'<div style="text-align: center; display: flex; justify-content: center; align-items: center; width: 100%;" class="small-font">{row[2]}</div>', unsafe_allow_html=True)  # part_no
                with col3:
                    st.markdown(f'<div style="text-align: center; display: flex; justify-content: center; align-items: center; width: 100%;" class="small-font">{row[6]}</div>', unsafe_allow_html=True)  # qr_id
                with col4:
                    st.markdown(f'<div style="text-align: center; display: flex; justify-content: center; align-items: center; width: 100%;" class="small-font">{row[7]}</div>', unsafe_allow_html=True)  # component
                with col5:
                    stock_value = total_stock.get(row[6], 0)
                    background_color = "background-color: red;" if 0 <= stock_value <= 2 else ""
                    st.markdown(
                        f'<div style="text-align: center; display: flex; justify-content: center; align-items: center; width: 100%; {background_color}" class="small-font">{stock_value}</div>',
                        unsafe_allow_html=True,
                    )

                
            # --- Download Entire Parts Table as CSV ---
            st.header("Download Entire Parts Table")

            # Fetch all rows from the parts table
            cursor.execute("SELECT * FROM parts")
            parts_rows = cursor.fetchall()

            # Define column headers matching the database schema
            columns = ["ID", "Part Name", "Part Number", "Type", "Process", "Tool Type", "QR ID", "Component"]

            # Calculate the total stock for each part (stock in - stock out)
            total_stock = {}
            for row in parts_rows:
                qr_id = row[6]  # qr_id is at index 6
                cursor.execute('''
                    SELECT qr_id, 
                        SUM(CASE WHEN action = 'Stock In' THEN quantity ELSE 0 END) - 
                        SUM(CASE WHEN action = 'Stock Out' THEN quantity ELSE 0 END)
                    FROM stock_movements
                    WHERE qr_id = ?
                    GROUP BY qr_id
                ''', (qr_id,))  # Pass the specific qr_id for this part
                total_stock_result = cursor.fetchone()
                if total_stock_result:
                    total_stock[qr_id] = total_stock_result[1]  # Stock value

            # Convert the fetched rows to a Pandas DataFrame
            df_parts_table = pd.DataFrame(parts_rows, columns=columns)

            # Add a new column 'Total Stock' with the calculated stock values
            df_parts_table['Total Stock'] = df_parts_table['QR ID'].map(total_stock).fillna(0).astype(int)

            # Check if the table is not empty
            if not df_parts_table.empty:
                # Add a download button for the parts table
                csv_data = df_parts_table.to_csv(index=False)
                st.download_button(
                    label="Download Parts Table as CSV",
                    data=csv_data,
                    file_name="parts_table_with_stock.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No data available in the parts table for download.")
            

        elif page == "Stock Management":
            st.header("Record Stock In/Out")

            # Fetch available QR IDs from the database
            cursor.execute('SELECT DISTINCT qr_id FROM parts')
            available_qr_ids = [row[0] for row in cursor.fetchall()]

            if available_qr_ids:
                st.write("### Select a QR ID")

                # Dropdown for selecting QR ID without filtering
                selected_qr_id = st.selectbox("Choose a QR ID", available_qr_ids)

                if selected_qr_id:
                    # Fetch and display part details for the selected QR ID
                    cursor.execute('''
                        SELECT part_name, part_no, process, tool_type, component 
                        FROM parts 
                        WHERE qr_id = ?
                        LIMIT 1
                    ''', (selected_qr_id,))
                    row = cursor.fetchone()

                    if row:
                        # Display part details
                        part_name, part_no, process, tool_type, component = row
                        st.write(f"### Part Details for QR ID: {selected_qr_id}")
                        st.write(f"Part Name: {part_name}")
                        st.write(f"Part No: {part_no}")
                        st.write(f"Process: {process}")
                        st.write(f"Tool Type: {tool_type}")
                        st.write(f"Component: {component}")

                        # Stock movement form
                        with st.form("stock_form"):
                            action = st.radio("Action", ["Stock In", "Stock Out"], index=0)
                            quantity = st.number_input("Quantity", min_value=1, step=1)
                            pic = st.text_input("PIC (Person in Charge)", placeholder="Enter the responsible person")
                            submit_button = st.form_submit_button(label="Record Movement")

                            if submit_button:
                                if quantity > 0 and pic.strip():  # Validate quantity and PIC
                                    try:
                                        # Format date_time to exclude microseconds
                                        date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                                        # Insert stock movement with formatted date_time and PIC
                                        cursor.execute('''
                                            INSERT INTO stock_movements (part_name, action, quantity, date_time, qr_id, component, pic)
                                            VALUES (?, ?, ?, ?, ?, ?, ?)
                                        ''', (part_name, action, quantity, date_time, selected_qr_id, component, pic))
                                        conn.commit()
                                        st.success(f"Recorded {quantity} '{action}' for QR ID {selected_qr_id} ({part_name}) by {pic}.")
                                    except Exception as e:
                                        st.error(f"Error recording movement: {e}")
                                else:
                                    st.error("Please enter a valid quantity and ensure PIC is not empty.")
                    else:
                        st.error("No part details found for the selected QR ID.")
            else:
                st.warning("No QR IDs available.")

            # --- Display Stock Movements ---
            st.header("View Stock Movements")

            # Fetch all stock movements
            cursor.execute('''
                SELECT qr_id, part_name, action, quantity, date_time, component, pic
                FROM stock_movements
                ORDER BY date_time DESC
            ''')
            rows = cursor.fetchall()

            formatted_rows = []
            for row in rows:
                try:
                    # Try to parse the datetime with microseconds
                    date_time = datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # If no microseconds, parse it without them
                    date_time = datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')

                # Append the formatted row
                formatted_rows.append(row[:4] + (date_time,) + row[5:])

            if rows:
                # Convert to pandas DataFrame
                df_stock_movements = pd.DataFrame(rows, columns=[
                    "QR ID", "Part Name", "Action", "Quantity", "Date Time", "Component", "PIC"
                ])
                st.write("### Stock Movements")
                st.dataframe(df_stock_movements)

                # Option to download movements as CSV
                st.download_button(
                    label="Download Stock Movements as CSV",
                    data=df_stock_movements.to_csv(index=False),
                    file_name="stock_movements.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No stock movements found.")

            # Function to delete all stock movements from the database
            def delete_all_stock_movements(password):
                correct_password = "youcantdoit"  # The required password
                if password == correct_password:
                    try:
                        # Delete all records from the stock_movements table
                        cursor.execute("DELETE FROM stock_movements")
                        conn.commit()
                        return "All stock movements have been deleted successfully."
                    except Exception as e:
                        return f"An error occurred: {e}"
                else:
                    return "Incorrect password. Access denied."

            # Streamlit interface for the delete function
            st.header("Delete All Stock Movements")

            with st.form(key="delete_form", clear_on_submit=True):
                password_input = st.text_input("Enter password", type="password")
                submit_button = st.form_submit_button("Delete All Stock Movements")

                if submit_button:
                    result_message = delete_all_stock_movements(password_input)
                    if "successfully" in result_message:
                        st.success(result_message)
                    else:
                        st.error(result_message)

        # Logout functionality
        if st.sidebar.button("Logout"):
            del cookies["logged_in"]  # Delete the cookie
            st.session_state["logged_in"] = False  # Reset the session state
            st.rerun()  # Refresh to go back to login page
    else:
        # Show the login form if the user is not logged in
        login()
else:
    st.sidebar.button("Logout", on_click=lambda: logout_user())  # Add logout functionality
    st.title("Welcome to Part Management")
    st.write("Your main app goes here.")