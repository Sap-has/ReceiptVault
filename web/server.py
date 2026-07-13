import os
import sys
import socket
import tempfile
import webbrowser
import threading

from core.db_manager import ReceiptVault
from utils import update_application, DEFAULT_PORT

'''
Contains the Flask application logic, the @flask_app.route decorators, and the run_web() function. 
It will import ReceiptVault from core.db_manager.
It will import update_application from root.utils.py
'''

# ---------------------------------------------------------------------------
# Web mode  (Flask)
# ---------------------------------------------------------------------------
def _is_port_free(host: str, port: int) -> bool:
    """Return True if `port` can be bound on `host` right now."""
    probe_host = host if host not in ("0.0.0.0", "") else "0.0.0.0"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((probe_host, port))
        except OSError:
            return False
        return True

def find_free_port(host: str = "127.0.0.1", start_port: int = DEFAULT_PORT,
                    max_attempts: int = 100) -> int:
    """
    Return `start_port` if it's free, otherwise scan upward and return the
    first free port found. Raises RuntimeError if nothing is free in range.
    """
    for port in range(start_port, start_port + max_attempts):
        if _is_port_free(host, port):
            return port
    raise RuntimeError(
        f"Could not find a free port in range {start_port}-{start_port + max_attempts - 1} "
        f"on {host}. Try freeing up a port or specifying one manually with --port."
    )

def run_web(host: str = "0.0.0.0", port: int | None = None, open_browser: bool = True):
    """Start the Flask web server."""
    try:
        from flask import Flask, jsonify, render_template, request as flask_request
    except ImportError:
        print(
            "\n[ERROR] Flask is not installed. Run:  pip install flask\n"
            "        or re-run the launch script so it can install dependencies.\n"
        )
        sys.exit(1)

    auto_selected = port is None
    if auto_selected:
        try:
            port = find_free_port(host=host, start_port=DEFAULT_PORT)
        except RuntimeError as exc:
            print(f"\n[ERROR] {exc}\n")
            sys.exit(1)
        if port != DEFAULT_PORT:
            print(
                f"\n[INFO] Port {DEFAULT_PORT} is already in use - "
                f"using port {port} instead.\n"
            )

    vault = ReceiptVault()
    vault.init_db()

    flask_app = Flask(__name__, static_folder="static", template_folder="templates")

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @flask_app.route("/")
    def index():
        return render_template("index.html")

    # --- Bills ---
    @flask_app.route("/api/bills", methods=["GET"])
    def get_bills():
        vendor_id = flask_request.args.get('vendor_id', type=int)
        category_id = flask_request.args.get('category_id', type=int)
        return jsonify(vault.get_bills_filtered(vendor_id=vendor_id, category_id=category_id))

    @flask_app.route("/api/bills", methods=["POST"])
    def create_bill():
        data = flask_request.json
        try:
            bill_id = vault.create_bill(
                date=data['date'],
                vendor_id=data['vendor_id'],
                price=float(data['price']),
                category_ids=data.get('category_ids', []),
                image_path=data.get('image_path')
            )
            return jsonify({"success": True, "id": bill_id})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @flask_app.route("/api/bills/<int:bill_id>", methods=["DELETE"])
    def delete_bill(bill_id):
        success = vault.delete_bill(bill_id)
        return jsonify({"success": success})
    
    @flask_app.route("/api/bills/<int:bill_id>", methods=["PUT"])
    def update_bill_route(bill_id):
        data = flask_request.json
        try:
            # Resolve vendor name into id if given text dynamically
            vendor_name = data.get('vendor_name', '').strip()
            vendor_id = data.get('vendor_id', -1)
            
            if vendor_name and vendor_id == -1:
                vendor_id = vault.get_or_create_vendor(vendor_name)

            success = vault.update_bill(
                bill_id=bill_id,
                date=data.get('date'),
                # BUG FIX: Pass vendor_id straight through; it relies on the -1 
                # sentinel in DB layer to denote "unchanged" rather than converting to None
                vendor_id=vendor_id,
                price=float(data['price']) if 'price' in data else None,
                category_ids=data.get('category_ids'),
                image_path=data.get('image_path')
            )
            return jsonify({"success": success})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400
    
    @flask_app.route("/api/bills/bulk-delete", methods=["POST"])
    def bulk_delete_bills():
        data = flask_request.json or {}
        bill_ids = data.get("ids", [])
        deleted_count = 0
        for bid in bill_ids:
            if vault.delete_bill(bid):
                deleted_count += 1
        return jsonify({"success": True, "deleted": deleted_count})

    # --- Vendors ---
    @flask_app.route("/api/vendors", methods=["GET"])
    def get_vendors():
        return jsonify(vault.get_all_vendors())

    @flask_app.route("/api/vendors/search", methods=["GET"])
    def search_vendors():
        """Wire up the autocomplete vendor search feature."""
        query = flask_request.args.get('q', '')
        limit = flask_request.args.get('limit', 8, type=int)
        return jsonify(vault.search_vendors(query, limit))

    @flask_app.route("/api/vendors", methods=["POST"])
    def add_vendor():
        name = flask_request.json.get('name')
        if not name:
            return jsonify({"error": "Name required"}), 400
        vid = vault.get_or_create_vendor(name)
        return jsonify({"success": True, "id": vid})

    @flask_app.route("/api/vendors/<int:vendor_id>", methods=["DELETE"])
    def delete_vendor(vendor_id):
        return jsonify({"success": vault.delete_vendor(vendor_id)})

    # --- Categories ---
    @flask_app.route("/api/categories", methods=["GET"])
    def get_categories():
        return jsonify(vault.get_all_categories())

    @flask_app.route("/api/categories", methods=["POST"])
    def add_category():
        name = flask_request.json.get('name')
        if not name:
            return jsonify({"error": "Name required"}), 400
        cid = vault.get_or_create_category(name)
        return jsonify({"success": True, "id": cid})

    @flask_app.route("/api/categories/<int:cat_id>", methods=["DELETE"])
    def delete_category(cat_id):
        return jsonify({"success": vault.delete_category(cat_id)})

    # --- OCR ---
    @flask_app.route("/api/scan", methods=["POST"])
    def scan_image():
        if 'image' not in flask_request.files:
            return jsonify({"error": "No image provided"}), 400
        
        file = flask_request.files['image']
        try:
            from core.ocr_processor import scan_receipt
            from core.image_splitter import extract_receipts
            import base64

            # Save temp file
            temp_ext = os.path.splitext(file.filename)[1] or '.jpg'
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=temp_ext)
            file.save(temp.name)
            temp.close()
            
            receipt_paths = extract_receipts(temp.name)

            results = []
            for r_path in receipt_paths:
                result = scan_receipt(r_path)
                
                # Convert crop to base64 to update frontend UI preview
                with open(r_path, "rb") as img_file:
                    b64_str = base64.b64encode(img_file.read()).decode('utf-8')
                mime_type = "image/png" if r_path.endswith('.png') else "image/jpeg"
                data_uri = f"data:{mime_type};base64,{b64_str}"
                
                results.append({
                    "vendor": result.vendor,
                    "price": result.price,
                    "date_str": result.date_str,
                    "image_data_uri": data_uri
                })
                
                # Clean up extracted temp file
                os.unlink(r_path)

            return jsonify({"results": results})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # --- System ---
    @flask_app.route("/api/update", methods=["POST"])
    def api_update():
        def perform_update():
            update_application()
        threading.Thread(target=perform_update, daemon=True).start()
        return jsonify({"status": "Update started"})

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    if not auto_selected and not _is_port_free(host, port):
        print(
            f"\n[ERROR] Port {port} is already in use on {host}.\n"
            f"        Choose a different port with --port, "
            f"or omit --port to auto-select a free one.\n"
        )
        sys.exit(1)

    url = f"http://{host}:{port}"
    print(f"\n  ReceiptVault is running → {url}\n  Press Ctrl+C to stop.\n")

    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    flask_app.run(host=host, port=port, debug=False, threaded=True)