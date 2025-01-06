from datetime import datetime
from app import db

class Instance(db.Model):
    __tablename__ = 'instances'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    instance_ocid = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    compartment_id = db.Column(db.String(200), nullable=False)
    availability_domain = db.Column(db.String(100), nullable=False)
    shape = db.Column(db.String(100), nullable=False)
    image_id = db.Column(db.String(200), nullable=False)
    subnet_id = db.Column(db.String(200), nullable=False)
    state = db.Column(db.String(50))
    public_ip = db.Column(db.String(50))
    private_ip = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'instance_ocid': self.instance_ocid,
            'name': self.name,
            'compartment_id': self.compartment_id,
            'availability_domain': self.availability_domain,
            'shape': self.shape,
            'image_id': self.image_id,
            'subnet_id': self.subnet_id,
            'state': self.state,
            'public_ip': self.public_ip,
            'private_ip': self.private_ip,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
