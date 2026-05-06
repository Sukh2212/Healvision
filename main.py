from app import create_app

# -----------------------------
# Create the Flask app instance
# -----------------------------
app = create_app()

# -----------------------------
# Test Route (to check server is running)
# -----------------------------
@app.route("/test")
def test():
    return "Flask server is running!"

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    # ✅ Run on localhost
    app.run(host="127.0.0.1", port=5000, debug=True)
