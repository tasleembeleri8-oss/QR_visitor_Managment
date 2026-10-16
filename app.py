import os
from functools import wraps
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, abort
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from sqlalchemy import or_, func

from config import Config
from extensions import db, login_manager, mail
from models import Host, Staff, Visitor, Visit
from utils.qr_utils import generate_qr
from utils.email_utils import send_visitor_qr_email, send_host_arrival_email
from utils.pdf_utils import generate_visitor_pass_pdf


def admin_required(view_func):
    """Restricts a route to staff with the 'admin' role."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("You need admin access for that.", "error")
            return redirect(url_for("dashboard"))
        return view_func(*args, **kwargs)
    return wrapped


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "staff_login"
    mail.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Staff.query.get(int(user_id))

    register_routes(app)
    return app


def register_routes(app):

    # ---------- Public: home ----------
    @app.route("/")
    def home():
        return render_template("home.html")

    # ---------- Visitor self-registration ----------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        hosts = Host.query.order_by(Host.name).all()

        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].strip()
            phone = request.form["phone"].strip()
            company = request.form.get("company", "").strip()
            host_id = request.form["host_id"]
            purpose = request.form.get("purpose", "").strip()

            if not (name and email and phone and host_id):
                flash("Please fill in all required fields.", "error")
                return render_template("register.html", hosts=hosts)

            visitor = Visitor(name=name, email=email, phone=phone, company=company)
            db.session.add(visitor)
            db.session.flush()  # get visitor.id before commit

            visit = Visit(
                visitor_id=visitor.id,
                host_id=host_id,
                purpose=purpose,
                registered_by="self",
                scheduled_time=datetime.utcnow(),
            )
            db.session.add(visit)
            db.session.flush()  # get visit.token

            qr_relative_path = generate_qr(visit.token, app.config["QR_FOLDER"])
            visit.qr_path = qr_relative_path
            db.session.commit()

            # Best-effort email; registration should still succeed if mail fails
            try:
                qr_abs = os.path.join(app.static_folder, qr_relative_path)
                send_visitor_qr_email(visitor.email, visitor.name, visit.host.name, qr_abs)
            except Exception as e:
                app.logger.warning(f"Could not email QR to visitor: {e}")

            return render_template("registration_success.html", visit=visit)

        return render_template("register.html", hosts=hosts)

    # ---------- Staff login ----------
    @app.route("/staff/login", methods=["GET", "POST"])
    def staff_login():
        if request.method == "POST":
            username = request.form["username"].strip()
            password = request.form["password"]
            staff = Staff.query.filter_by(username=username).first()

            if staff and staff.check_password(password):
                login_user(staff)
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "error")

        return render_template("staff_login.html")

    @app.route("/staff/logout")
    @login_required
    def staff_logout():
        logout_user()
        return redirect(url_for("staff_login"))

    # ---------- Staff: register a visitor on someone's behalf ----------
    @app.route("/staff/register-visit", methods=["GET", "POST"])
    @login_required
    def staff_register_visit():
        hosts = Host.query.order_by(Host.name).all()

        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].strip()
            phone = request.form["phone"].strip()
            company = request.form.get("company", "").strip()
            host_id = request.form["host_id"]
            purpose = request.form.get("purpose", "").strip()

            visitor = Visitor(name=name, email=email, phone=phone, company=company)
            db.session.add(visitor)
            db.session.flush()

            visit = Visit(
                visitor_id=visitor.id,
                host_id=host_id,
                purpose=purpose,
                registered_by="staff",
                created_by_staff_id=current_user.id,
                scheduled_time=datetime.utcnow(),
            )
            db.session.add(visit)
            db.session.flush()

            qr_relative_path = generate_qr(visit.token, app.config["QR_FOLDER"])
            visit.qr_path = qr_relative_path
            db.session.commit()

            try:
                qr_abs = os.path.join(app.static_folder, qr_relative_path)
                send_visitor_qr_email(visitor.email, visitor.name, visit.host.name, qr_abs)
            except Exception as e:
                app.logger.warning(f"Could not email QR to visitor: {e}")

            flash(f"Visit registered for {visitor.name}.", "success")
            return render_template("registration_success.html", visit=visit, staff_view=True)

        return render_template("staff_register_visit.html", hosts=hosts)

    # ---------- Staff: scanner page ----------
    @app.route("/staff/scan")
    @login_required
    def scan_page():
        return render_template("scan.html")

    # ---------- Staff: dashboard (stats + search + filter) ----------
    @app.route("/staff/dashboard")
    @login_required
    def dashboard():
        status_filter = request.args.get("status", "all")
        search_term = request.args.get("q", "").strip()

        query = Visit.query.join(Visitor).join(Host).order_by(Visit.created_at.desc())

        if status_filter != "all":
            query = query.filter(Visit.status == status_filter)

        if search_term:
            like = f"%{search_term}%"
            query = query.filter(
                or_(
                    Visitor.name.ilike(like),
                    Visitor.phone.ilike(like),
                    Visitor.email.ilike(like),
                    Visitor.company.ilike(like),
                    Host.name.ilike(like),
                )
            )

        visits = query.limit(200).all()

        # ---- Today's stats ----
        today = date.today()
        today_visits = Visit.query.filter(func.date(Visit.created_at) == today)
        stats = {
            "today_total": today_visits.count(),
            "checked_in_now": Visit.query.filter(Visit.status == "checked_in").count(),
            "pending_today": today_visits.filter(Visit.status == "pending").count(),
            "checked_out_today": today_visits.filter(Visit.status == "checked_out").count(),
        }

        return render_template(
            "dashboard.html",
            visits=visits,
            status_filter=status_filter,
            search_term=search_term,
            stats=stats,
        )

    # ---------- Staff (admin): manage hosts ----------
    @app.route("/staff/hosts")
    @login_required
    @admin_required
    def manage_hosts():
        hosts = Host.query.order_by(Host.name).all()
        return render_template("hosts.html", hosts=hosts)

    @app.route("/staff/hosts/add", methods=["POST"])
    @login_required
    @admin_required
    def add_host():
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        department = request.form.get("department", "").strip()

        if Host.query.filter_by(email=email).first():
            flash("A host with that email already exists.", "error")
            return redirect(url_for("manage_hosts"))

        db.session.add(Host(name=name, email=email, department=department))
        db.session.commit()
        flash(f"Added host {name}.", "success")
        return redirect(url_for("manage_hosts"))

    @app.route("/staff/hosts/<int:host_id>/edit-page")
    @login_required
    @admin_required
    def edit_host_page(host_id):
        host = Host.query.get_or_404(host_id)
        return render_template("edit_host.html", host=host)

    @app.route("/staff/hosts/<int:host_id>/edit", methods=["POST"])
    @login_required
    @admin_required
    def edit_host(host_id):
        host = Host.query.get_or_404(host_id)
        host.name = request.form["name"].strip()
        host.email = request.form["email"].strip()
        host.department = request.form.get("department", "").strip()
        db.session.commit()
        flash(f"Updated {host.name}.", "success")
        return redirect(url_for("manage_hosts"))

    @app.route("/staff/hosts/<int:host_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def delete_host(host_id):
        host = Host.query.get_or_404(host_id)
        if host.visits:
            flash(f"Can't delete {host.name} — they have visit records tied to them.", "error")
            return redirect(url_for("manage_hosts"))
        db.session.delete(host)
        db.session.commit()
        flash("Host removed.", "success")
        return redirect(url_for("manage_hosts"))

    # ---------- Download visitor pass as PDF ----------
    @app.route("/pass/<token>/pdf")
    def download_pass_pdf(token):
        visit = Visit.query.filter_by(token=token).first()
        if not visit:
            abort(404)

        qr_abs = os.path.join(app.static_folder, visit.qr_path)
        buffer = generate_visitor_pass_pdf(visit, qr_abs)

        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"visitor_pass_{visit.visitor.name.replace(' ', '_')}.pdf",
        )

    # ---------- Staff: resend the QR email to a visitor ----------
    @app.route("/staff/visits/<int:visit_id>/resend-email", methods=["POST"])
    @login_required
    def resend_visitor_email(visit_id):
        visit = Visit.query.get_or_404(visit_id)
        try:
            qr_abs = os.path.join(app.static_folder, visit.qr_path)
            send_visitor_qr_email(visit.visitor.email, visit.visitor.name, visit.host.name, qr_abs)
            flash(f"Resent pass to {visit.visitor.email}.", "success")
        except Exception as e:
            app.logger.warning(f"Could not resend QR email: {e}")
            flash("Couldn't send the email — check mail settings.", "error")
        return redirect(url_for("dashboard"))

    # ---------- API: check-in / check-out via scanned token ----------
    @app.route("/api/checkin", methods=["POST"])
    @login_required
    def api_checkin():
        token = request.json.get("token", "").strip()
        visit = Visit.query.filter_by(token=token).first()

        if not visit:
            return jsonify({"ok": False, "message": "QR code not recognized."}), 404

        if visit.status == "checked_in":
            return jsonify({"ok": False, "message": f"{visit.visitor.name} is already checked in."}), 409

        if visit.status == "checked_out":
            return jsonify({"ok": False, "message": "This visit has already ended."}), 409

        visit.status = "checked_in"
        visit.check_in_time = datetime.utcnow()
        db.session.commit()

        try:
            send_host_arrival_email(visit.host.email, visit.host.name, visit.visitor.name, visit.purpose)
        except Exception as e:
            app.logger.warning(f"Could not email host: {e}")

        return jsonify({"ok": True, "message": f"Checked in: {visit.visitor.name}", "visit": visit.to_dict()})

    @app.route("/api/checkout", methods=["POST"])
    @login_required
    def api_checkout():
        token = request.json.get("token", "").strip()
        visit = Visit.query.filter_by(token=token).first()

        if not visit:
            return jsonify({"ok": False, "message": "QR code not recognized."}), 404

        if visit.status != "checked_in":
            return jsonify({"ok": False, "message": "This visitor hasn't checked in yet."}), 409

        visit.status = "checked_out"
        visit.check_out_time = datetime.utcnow()
        db.session.commit()

        return jsonify({"ok": True, "message": f"Checked out: {visit.visitor.name}", "visit": visit.to_dict()})


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)