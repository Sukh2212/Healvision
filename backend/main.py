from app import create_app
import os

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
# Run Server (only for local dev)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
