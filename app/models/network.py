from datetime import datetime
from app import db

class VirtualCloudNetwork(db.Model):
    __tablename__ = 'vcns'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    vcn_ocid = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    compartment_id = db.Column(db.String(200), nullable=False)
    cidr_block = db.Column(db.String(50), nullable=False)
    dns_label = db.Column(db.String(50))
    state = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Subnet(db.Model):
    __tablename__ = 'subnets'
    
    id = db.Column(db.Integer, primary_key=True)
    vcn_id = db.Column(db.Integer, db.ForeignKey('vcns.id'), nullable=False)
    subnet_ocid = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    compartment_id = db.Column(db.String(200), nullable=False)
    cidr_block = db.Column(db.String(50), nullable=False)
    availability_domain = db.Column(db.String(100))
    dns_label = db.Column(db.String(50))
    state = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SecurityList(db.Model):
    __tablename__ = 'security_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    vcn_id = db.Column(db.Integer, db.ForeignKey('vcns.id'), nullable=False)
    security_list_ocid = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    compartment_id = db.Column(db.String(200), nullable=False)
    state = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SecurityRule(db.Model):
    __tablename__ = 'security_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    security_list_id = db.Column(db.Integer, db.ForeignKey('security_lists.id'), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # INGRESS or EGRESS
    protocol = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(50))
    destination = db.Column(db.String(50))
    source_port_range_min = db.Column(db.Integer)
    source_port_range_max = db.Column(db.Integer)
    destination_port_range_min = db.Column(db.Integer)
    destination_port_range_max = db.Column(db.Integer)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
