import uuid
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class Host(db.Model):
    __tablename__ = "hosts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    department = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    visits = db.relationship("Visit", backref="host", lazy=True)


class Staff(UserMixin, db.Model):
    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.Enum("admin", "security", "frontdesk"), default="frontdesk")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class Visitor(db.Model):
    __tablename__ = "visitors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    company = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    visits = db.relationship("Visit", backref="visitor", lazy=True)


class Visit(db.Model):
    __tablename__ = "visits"

    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitors.id"), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey("hosts.id"), nullable=False)
    purpose = db.Column(db.String(255))
    token = db.Column(db.String(36), nullable=False, unique=True,
                       default=lambda: str(uuid.uuid4()))
    qr_path = db.Column(db.String(255))
    status = db.Column(
        db.Enum("pending", "checked_in", "checked_out", "cancelled"),
        default="pending",
        nullable=False,
    )
    scheduled_time = db.Column(db.DateTime)
    check_in_time = db.Column(db.DateTime, nullable=True)
    check_out_time = db.Column(db.DateTime, nullable=True)
    registered_by = db.Column(db.Enum("self", "staff"), default="self")
    created_by_staff_id = db.Column(db.Integer, db.ForeignKey("staff.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "token": self.token,
            "visitor_name": self.visitor.name if self.visitor else None,
            "visitor_phone": self.visitor.phone if self.visitor else None,
            "host_name": self.host.name if self.host else None,
            "purpose": self.purpose,
            "status": self.status,
            "check_in_time": self.check_in_time.strftime("%Y-%m-%d %H:%M") if self.check_in_time else None,
            "check_out_time": self.check_out_time.strftime("%Y-%m-%d %H:%M") if self.check_out_time else None,
        }
