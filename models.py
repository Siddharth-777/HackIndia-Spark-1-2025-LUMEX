from app import db
from datetime import datetime

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    summary = db.Column(db.Text)
    analysis = db.Column(db.JSON)
