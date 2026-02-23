from flask import Flask, request, flash, redirect, url_for, render_template, session, send_file
import os
from io import BytesIO
import pandas as pd
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.secret_key = os.getenv("SECRET_KEY")
db = SQLAlchemy(app)

df = pd.read_csv("ippis_list.csv")
EXPORT_PASSWORD = os.getenv("EXPORT_PASSWORD")

class Staff_data(db.Model):
    id = db.Column(db.Integer,  primary_key=True)
    ippis = db.Column(db.String(10), nullable=False, unique=True)
    Firstname = db.Column(db.String(30), nullable=False)
    Surname = db.Column(db.String(30), nullable=False)
    Othernames = db.Column(db.String(30), nullable=True)
    gl = db.Column(db.Integer, nullable=False)
    step = db.Column(db.Integer, nullable=False)

@app.route("/")
def home():
    return render_template("homepage.html")

@app.route("/submit", methods = ["GET", "POST"])
def submit():
    ippis = None
    if request.method == "POST":
        ippis = request.form["ippis"]
        
        ippis_to_check = ippis
        existing_staff = Staff_data.query.filter_by(ippis=ippis_to_check).first()
        if existing_staff:
            flash(f"{ippis} already exists", "success")
            return redirect(url_for("home"))

        else:
            if ippis in df['IPPIS'].astype(str).values:
                session["ippis"] = ippis
                return redirect(url_for("collect_biodata"))
            else:
                flash(f"IPPIS number {ippis} not found", "error")
                return redirect(url_for("home"))
    
    return render_template("index.html")

@app.route("/collect_biodata", methods = ["GET", "POST"])
def collect_biodata():
    if "ippis" not in session:
        return redirect(url_for("home"))
    
    if request.method == "POST":
        Staff = Staff_data(
            ippis = session["ippis"],
            Firstname = request.form["Firstname"],
            Surname = request.form["Surname"],
            Othernames = request.form["Othernames"],
            gl = int(request.form["Gradelevel"]),
            step = int(request.form["Step"])
            )

        db.session.add(Staff)
        db.session.commit()
        session.pop("ippis")
        flash("Application submitted succcessfully", "success")
        return redirect(url_for("home"))
    
    return render_template("index.html")

@app.route("/report_issue")
def report_issue():
    return render_template ("report_issue.html")

@app.route("/export_data", methods=["GET", "POST"])
def export_data():
    attempts = session.get("attempts", 3)

    if request.method == "POST":
        if request.form.get("password") != EXPORT_PASSWORD:
            attempts -= 1
            session["attempts"] = attempts
            flash(f"Incorrect password. You have {attempts} attempts left", "error")
            return redirect(url_for("export_data"))

        session["export_success"] = True
        return redirect(url_for("download_file"))

    if session.pop("export_success", None):
        flash("Data exported successfully", "success")

    return render_template("export_data.html")

@app.route("/download_file")
def download_file():
    staff_records = Staff_data.query.all()

    data = [
        {
            "IPPIS": staff.ippis,
            "Firstname": staff.Firstname,
            "Surname": staff.Surname,
            "Othernames": staff.Othernames,
            "Grade Level": staff.gl,
            "Step": staff.step
        }
        for staff in staff_records
    ]

    df_out = pd.DataFrame(data)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Sheet1")

    output.seek(0)

    if staff_records:
        Staff_data.query.delete()
        db.session.commit()
        
    return send_file(
        output,
        as_attachment=True,
        download_name="prom_arr_applications.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
