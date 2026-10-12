
import csv
import io
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, redirect, url_for, flash, request,
    Response, abort
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__, instance_relative_config=True)
os.makedirs(app.instance_path, exist_ok=True)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-only-change-this-secret-key"
)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + os.path.join(app.instance_path, "hospital.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


# =========================
# DATABASE MODELS
# =========================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_code = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(30), default="")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admissions = db.relationship("Admission", backref="patient", lazy=True)


class Bed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bed_code = db.Column(db.String(20), unique=True, nullable=False)
    ward = db.Column(db.String(80), nullable=False)
    bed_type = db.Column(db.String(40), nullable=False)
    facilities = db.Column(db.String(255), default="")
    status = db.Column(db.String(20), default="Available", nullable=False)

    active_admission = db.relationship(
        "Admission",
        backref="bed",
        uselist=False,
        primaryjoin=(
            "and_(Bed.id==Admission.bed_id, "
            "Admission.status=='Active')"
        )
    )


class Admission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patient.id"), nullable=False
    )
    bed_id = db.Column(
        db.Integer, db.ForeignKey("bed.id"), nullable=False
    )
    reason = db.Column(db.String(255), nullable=False)
    required_type = db.Column(
        db.String(40), nullable=False, default="General"
    )
    required_ward = db.Column(db.String(80), default="")
    required_facilities = db.Column(db.String(255), default="")
    admitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    discharged_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="Active", nullable=False)
    admitted_by = db.Column(db.String(80), nullable=False)
    discharged_by = db.Column(db.String(80), nullable=True)


class AllocationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(120), nullable=False)
    patient_code = db.Column(db.String(20), nullable=False)
    bed_code = db.Column(db.String(20), nullable=False)
    ward = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(30), nullable=False)
    details = db.Column(db.String(255), default="")
    actor = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# LOGIN AND PERMISSIONS
# =========================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def log_action(patient, bed, action, details=""):
    db.session.add(
        AllocationLog(
            patient_name=patient.full_name,
            patient_code=patient.patient_code,
            bed_code=bed.bed_code,
            ward=bed.ward,
            action=action,
            details=details,
            actor=current_user.username
        )
    )


# =========================
# INITIAL DEMO DATA
# =========================

def seed_demo_data():
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", role="admin")
        admin.set_password("Admin@12345")
        db.session.add(admin)

    if not User.query.filter_by(username="staff").first():
        staff = User(username="staff", role="staff")
        staff.set_password("Staff@12345")
        db.session.add(staff)

    if Bed.query.count() == 0:
        demo_beds = [
            ("G-101", "General", "General", "Oxygen"),
            ("G-102", "General", "General", "Oxygen,Monitor"),
            ("G-103", "General", "General", ""),
            ("ICU-01", "ICU", "ICU", "Oxygen,Monitor,Ventilator"),
            ("ICU-02", "ICU", "ICU", "Oxygen,Monitor,Ventilator"),
            ("P-201", "Pediatric", "Pediatric", "Oxygen,Monitor"),
            ("P-202", "Pediatric", "Pediatric", "Oxygen"),
            ("PR-01", "Private", "Private", "Oxygen,Monitor"),
        ]

        for code, ward, kind, facilities in demo_beds:
            db.session.add(
                Bed(
                    bed_code=code,
                    ward=ward,
                    bed_type=kind,
                    facilities=facilities
                )
            )

    db.session.commit()


# =========================
# FAVICON FIX
# =========================

@app.route("/favicon.ico")
def favicon():
    # A small SVG hospital icon; no external image file is required.
    svg_icon = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <rect width="64" height="64" rx="14" fill="#0f766e"/>
      <path d="M27 10h10v17h17v10H37v17H27V37H10V27h17z"
            fill="#ffffff"/>
    </svg>
    """
    return Response(svg_icon, mimetype="image/svg+xml")


# =========================
# HOME AND DASHBOARD
# =========================

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    total_beds = Bed.query.count()
    available_beds = Bed.query.filter_by(status="Available").count()
    occupied_beds = Bed.query.filter_by(status="Occupied").count()
    active_admissions = Admission.query.filter_by(status="Active").count()

    occupancy = (
        round((occupied_beds / total_beds) * 100, 1)
        if total_beds else 0
    )

    wards = (
        db.session.query(Bed.ward, db.func.count(Bed.id))
        .group_by(Bed.ward)
        .all()
    )

    ward_stats = []

    for ward, total in wards:
        occupied = Bed.query.filter_by(
            ward=ward, status="Occupied"
        ).count()

        ward_stats.append({
            "ward": ward,
            "total": total,
            "occupied": occupied,
            "available": total - occupied
        })

    recent_logs = (
        AllocationLog.query
        .order_by(AllocationLog.created_at.desc())
        .limit(6)
        .all()
    )

    return render_template(
        "dashboard.html",
        total_beds=total_beds,
        available_beds=available_beds,
        occupied_beds=occupied_beds,
        active_admissions=active_admissions,
        occupancy=occupancy,
        ward_stats=ward_stats,
        recent_logs=recent_logs
    )


# =========================
# PATIENTS
# =========================

@app.route("/patients", methods=["GET", "POST"])
@login_required
def patients():
    if request.method == "POST":
        code = request.form.get("patient_code", "").strip().upper()
        name = request.form.get("full_name", "").strip()

        try:
            age = int(request.form.get("age", "0"))
        except ValueError:
            age = 0

        gender = request.form.get("gender", "")

        if (
            not code or not name or age < 0 or age > 120
            or gender not in ("Female", "Male", "Other")
        ):
            flash(
                "Enter valid patient details. Age must be between 0 and 120.",
                "danger"
            )

        elif Patient.query.filter_by(patient_code=code).first():
            flash("Patient ID already exists.", "danger")

        else:
            patient = Patient(
                patient_code=code,
                full_name=name,
                age=age,
                gender=gender,
                phone=request.form.get("phone", "").strip(),
                notes=request.form.get("notes", "").strip()
            )

            db.session.add(patient)
            db.session.commit()

            flash("Patient registered successfully.", "success")
            return redirect(url_for("patients"))

    q = request.args.get("q", "").strip()
    query = Patient.query

    if q:
        query = query.filter(
            or_(
                Patient.full_name.ilike(f"%{q}%"),
                Patient.patient_code.ilike(f"%{q}%"),
                Patient.phone.ilike(f"%{q}%")
            )
        )

    patient_list = query.order_by(Patient.created_at.desc()).all()

    return render_template(
        "patients.html",
        patients=patient_list,
        q=q
    )


@app.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
def edit_patient(patient_id):
    patient = db.get_or_404(Patient, patient_id)

    if request.method == "POST":
        name = request.form.get("full_name", "").strip()

        try:
            age = int(request.form.get("age", "0"))
        except ValueError:
            age = -1

        gender = request.form.get("gender", "")

        if (
            not name or age < 0 or age > 120
            or gender not in ("Female", "Male", "Other")
        ):
            flash("Enter valid patient details.", "danger")

        else:
            patient.full_name = name
            patient.age = age
            patient.gender = gender
            patient.phone = request.form.get("phone", "").strip()
            patient.notes = request.form.get("notes", "").strip()

            db.session.commit()

            flash("Patient details updated.", "success")
            return redirect(url_for("patients"))

    return render_template("edit_patient.html", patient=patient)


# =========================
# BEDS
# =========================

@app.route("/beds", methods=["GET", "POST"])
@roles_required("admin")
def beds():
    if request.method == "POST":
        code = request.form.get("bed_code", "").strip().upper()
        ward = request.form.get("ward", "").strip()
        kind = request.form.get("bed_type", "").strip()
        facilities = request.form.get("facilities", "").strip()

        if not code or not ward or not kind:
            flash("Bed code, ward, and bed type are required.", "danger")

        elif Bed.query.filter_by(bed_code=code).first():
            flash("That bed code already exists.", "danger")

        else:
            db.session.add(
                Bed(
                    bed_code=code,
                    ward=ward,
                    bed_type=kind,
                    facilities=facilities
                )
            )
            db.session.commit()

            flash("Bed added successfully.", "success")
            return redirect(url_for("beds"))

    bed_list = Bed.query.order_by(Bed.ward, Bed.bed_code).all()

    return render_template("beds.html", beds=bed_list)


@app.route("/beds/<int:bed_id>/toggle", methods=["POST"])
@roles_required("admin")
def toggle_bed(bed_id):
    bed = db.get_or_404(Bed, bed_id)

    if bed.status == "Occupied":
        flash("Occupied beds cannot be marked unavailable.", "danger")

    elif bed.status == "Available":
        bed.status = "Unavailable"
        db.session.commit()
        flash("Bed marked unavailable.", "info")

    else:
        bed.status = "Available"
        db.session.commit()
        flash("Bed marked available.", "success")

    return redirect(url_for("beds"))


# =========================
# ADMISSIONS AND ALLOCATION
# =========================

@app.route("/admissions", methods=["GET", "POST"])
@login_required
def admissions():
    if request.method == "POST":
        try:
            patient_id = int(request.form.get("patient_id", "0"))
        except ValueError:
            patient_id = 0

        patient = db.session.get(Patient, patient_id)
        reason = request.form.get("reason", "").strip()
        req_type = request.form.get(
            "required_type", "General"
        ).strip()
        req_ward = request.form.get("required_ward", "").strip()

        req_facilities = [
            x.strip()
            for x in request.form.getlist("required_facilities")
            if x.strip()
        ]

        if not patient or not reason:
            flash("Choose a patient and enter an admission reason.", "danger")
            return redirect(url_for("admissions"))

        existing = Admission.query.filter_by(
            patient_id=patient.id,
            status="Active"
        ).first()

        if existing:
            flash("This patient already has an active admission.", "danger")
            return redirect(url_for("admissions"))

        candidates = Bed.query.filter_by(
            status="Available",
            bed_type=req_type
        ).all()

        if req_ward:
            candidates = [
                bed for bed in candidates
                if bed.ward == req_ward
            ]

        scored = []

        for bed in candidates:
            available_facilities = {
                item.strip().lower()
                for item in bed.facilities.split(",")
                if item.strip()
            }

            required = {item.lower() for item in req_facilities}

            if required.issubset(available_facilities):
                score = len(available_facilities - required)
                scored.append((score, bed.bed_code, bed))

        if not scored:
            flash(
                "No available bed matches these requirements. "
                "Try another ward, bed type, or facility combination.",
                "warning"
            )
            return redirect(url_for("admissions"))

        scored.sort(key=lambda item: (item[0], item[1]))
        bed = scored[0][2]

        admission = Admission(
            patient_id=patient.id,
            bed_id=bed.id,
            reason=reason,
            required_type=req_type,
            required_ward=req_ward,
            required_facilities=",".join(req_facilities),
            admitted_by=current_user.username
        )

        bed.status = "Occupied"
        db.session.add(admission)
        db.session.flush()

        log_action(
            patient,
            bed,
            "Allocated",
            f"Admission #{admission.id}; type={req_type}"
        )

        db.session.commit()

        flash(
            f"Patient admitted successfully. Allocated bed "
            f"{bed.bed_code} in {bed.ward} ward.",
            "success"
        )

        return redirect(url_for("admissions"))

    patient_list = Patient.query.order_by(Patient.full_name).all()

    active = (
        Admission.query.filter_by(status="Active")
        .order_by(Admission.admitted_at.desc())
        .all()
    )

    history_list = (
        Admission.query.filter_by(status="Discharged")
        .order_by(Admission.discharged_at.desc())
        .limit(20)
        .all()
    )

    wards = sorted({bed.ward for bed in Bed.query.all()})

    return render_template(
        "admissions.html",
        patients=patient_list,
        active=active,
        history=history_list,
        wards=wards
    )


@app.route("/admissions/<int:admission_id>/discharge", methods=["POST"])
@login_required
def discharge(admission_id):
    admission = db.get_or_404(Admission, admission_id)

    if admission.status != "Active":
        flash("This admission has already been discharged.", "warning")
        return redirect(url_for("admissions"))

    admission.status = "Discharged"
    admission.discharged_at = datetime.utcnow()
    admission.discharged_by = current_user.username
    admission.bed.status = "Available"

    log_action(
        admission.patient,
        admission.bed,
        "Discharged",
        f"Admission #{admission.id}"
    )

    db.session.commit()

    flash(
        f"{admission.patient.full_name} discharged; "
        f"bed {admission.bed.bed_code} is available.",
        "success"
    )

    return redirect(url_for("admissions"))


# =========================
# HISTORY
# =========================

@app.route("/history")
@login_required
def history():
    logs = (
        AllocationLog.query
        .order_by(AllocationLog.created_at.desc())
        .limit(250)
        .all()
    )

    return render_template("history.html", logs=logs)


# =========================
# REPORTS AND CSV EXPORT
# =========================

@app.route("/reports")
@roles_required("admin")
def reports():
    total = Bed.query.count()
    occupied = Bed.query.filter_by(status="Occupied").count()
    available = Bed.query.filter_by(status="Available").count()
    unavailable = Bed.query.filter_by(status="Unavailable").count()

    occupancy = round(occupied / total * 100, 1) if total else 0

    return render_template(
        "reports.html",
        total=total,
        occupied=occupied,
        available=available,
        unavailable=unavailable,
        occupancy=occupancy
    )


@app.route("/reports/export.csv")
@roles_required("admin")
def export_report():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Admission ID", "Patient Code", "Patient Name", "Bed",
        "Ward", "Reason", "Status", "Admitted At", "Discharged At",
        "Admitted By", "Discharged By"
    ])

    admissions_list = Admission.query.order_by(
        Admission.admitted_at.desc()
    ).all()

    for admission in admissions_list:
        writer.writerow([
            admission.id,
            admission.patient.patient_code,
            admission.patient.full_name,
            admission.bed.bed_code,
            admission.bed.ward,
            admission.reason,
            admission.status,
            admission.admitted_at.isoformat(),
            (
                admission.discharged_at.isoformat()
                if admission.discharged_at else ""
            ),
            admission.admitted_by,
            admission.discharged_by or ""
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=hospital_admissions_report.csv"
        }
    )


# =========================
# USER MANAGEMENT
# =========================

@app.route("/users", methods=["GET", "POST"])
@roles_required("admin")
def users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "staff")

        if (
            len(username) < 3
            or len(password) < 10
            or role not in ("admin", "staff")
        ):
            flash(
                "Username must have at least 3 characters, password "
                "at least 10, and role must be valid.",
                "danger"
            )

        elif User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")

        else:
            user = User(username=username, role=role)
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash("User created.", "success")
            return redirect(url_for("users"))

    user_list = User.query.order_by(User.username).all()

    return render_template("users.html", users=user_list)


# =========================
# ERROR PAGES
# =========================

@app.errorhandler(403)
def forbidden(_error):
    return render_template(
        "error.html",
        code=403,
        message="You do not have permission to access this page."
    ), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html",
        code=404,
        message="The page or record could not be found."
    ), 404


# =========================
# DATABASE INITIALIZATION
# =========================

with app.app_context():
    db.create_all()
    seed_demo_data()


# =========================
# START APPLICATION
# =========================

if __name__ == "__main__":
    app.run(debug=True)
