from datetime import datetime
from app import db

class Tenant(db.Model):
    __tablename__ = 'tenants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    user_ocid = db.Column(db.String(200), nullable=False)
    fingerprint = db.Column(db.String(200), nullable=False)
    key_file_path = db.Column(db.String(500), nullable=False)
    tenancy_ocid = db.Column(db.String(200), nullable=False)
    region = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'user_ocid': self.user_ocid,
            'fingerprint': self.fingerprint,
            'key_file_path': self.key_file_path,
            'tenancy_ocid': self.tenancy_ocid,
            'region': self.region,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
