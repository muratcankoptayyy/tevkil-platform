"""
Database models for Tevkil Platform
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        db.UniqueConstraint('bar_association', 'bar_registration_number', name='unique_bar_registration'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile Information
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    whatsapp_number = db.Column(db.String(20))
    tc_number = db.Column(db.String(11))  # T.C. Kimlik Numarası
    
    # Baro Bilgileri
    bar_association = db.Column(db.String(100))  # Bağlı olduğu baro (örn: "İstanbul Barosu")
    bar_registration_number = db.Column(db.String(50))  # Baro sicil numarası
    lawyer_type = db.Column(db.String(20), default='avukat')  # 'avukat' veya 'stajyer' (sadece admin için görünür)
    
    # Location
    city = db.Column(db.String(50))
    district = db.Column(db.String(50))
    
    # Professional Info
    specializations = db.Column(db.JSON)  # List of specialization areas
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(255))
    
    # Social Media Links
    linkedin_url = db.Column(db.String(255))
    twitter_url = db.Column(db.String(255))
    instagram_url = db.Column(db.String(255))
    website_url = db.Column(db.String(255))
    
    # İstatistikler - Duruşma ve Görev
    attended_hearings_count = db.Column(db.Integer, default=0)  # Katıldığı duruşma sayısı
    completed_tasks_count = db.Column(db.Integer, default=0)  # Tamamladığı görev sayısı
    
    # Stats
    rating = db.Column(db.Float, default=0.0)
    rating_average = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    total_jobs = db.Column(db.Integer, default=0)
    completed_jobs = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)
    
    # Status
    verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)  # Admin kontrolü
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('TevkilPost', backref='user', lazy='dynamic', foreign_keys='TevkilPost.user_id')
    applications = db.relationship('Application', backref='applicant', lazy='dynamic', foreign_keys='Application.applicant_id')
    ratings_given = db.relationship('Rating', backref='reviewer', lazy='dynamic', foreign_keys='Rating.reviewer_id')
    ratings_received = db.relationship('Rating', backref='reviewed', lazy='dynamic', foreign_keys='Rating.reviewed_id')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', foreign_keys='Notification.user_id')
    
    @property
    def notifications_unread_count(self):
        """Okunmamış bildirim sayısı"""
        return self.notifications.filter_by(read_at=None).count()
    
    @property
    def is_trainee(self):
        """Kullanıcının stajyer avukat olup olmadığını kontrol eder"""
        return self.lawyer_type == 'stajyer'
    
    @property
    def can_apply_to_jobs(self):
        """Kullanıcının görevlere başvuru yapıp yapamayacağını kontrol eder"""
        # Stajyer avukatlar başvuru yapamaz
        return self.lawyer_type != 'stajyer'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class TevkilPost(db.Model):
    __tablename__ = 'tevkil_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Post Content
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # boşanma, miras, ticaret, etc.
    
    # Details
    urgency_level = db.Column(db.String(20), default='normal')  # normal, urgent, very_urgent
    location = db.Column(db.String(100))
    city = db.Column(db.String(50))  # İl
    district = db.Column(db.String(50))  # İlçe
    courthouse = db.Column(db.String(100))  # Adliye
    remote_allowed = db.Column(db.Boolean, default=False)
    
    # Price (optional)
    price_min = db.Column(db.Float)
    price_max = db.Column(db.Float)
    
    # Dates
    deadline = db.Column(db.DateTime)
    court_date = db.Column(db.DateTime)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, assigned, completed, cancelled
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Stats
    views = db.Column(db.Integer, default=0)
    applications_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    # Relationships
    applications = db.relationship('Application', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<TevkilPost {self.title}>'


class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('tevkil_posts.id'), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Application Details
    message = db.Column(db.Text)
    proposed_price = db.Column(db.Float)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    
    # Response time (for metrics)
    response_time = db.Column(db.Integer)  # in minutes
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Application {self.id} for Post {self.post_id}>'


class Rating(db.Model):
    __tablename__ = 'ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('tevkil_posts.id'))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Ratings (1-5)
    rating = db.Column(db.Integer, nullable=False)  # Overall rating
    professionalism = db.Column(db.Integer)
    communication = db.Column(db.Integer)
    quality = db.Column(db.Integer)
    
    # Comment
    comment = db.Column(db.Text)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Rating {self.rating} by User {self.reviewer_id}>'


class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('tevkil_posts.id'))
    
    # Message Content
    message = db.Column(db.Text, nullable=False)
    attachments = db.Column(db.JSON)  # List of attachment URLs
    
    # Status
    read_at = db.Column(db.DateTime)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    post = db.relationship('TevkilPost', foreign_keys=[post_id])
    
    def __repr__(self):
        return f'<Message from {self.sender_id} to {self.receiver_id}>'


class Favorite(db.Model):
    __tablename__ = 'favorites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('tevkil_posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='favorites')
    post = db.relationship('TevkilPost', backref='favorited_by')
    
    # Unique constraint: bir kullanıcı aynı ilanı birden fazla favoriye ekleyemesin
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_favorite'),)
    
    def __repr__(self):
        return f'<Favorite user={self.user_id} post={self.post_id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Notification Content
    type = db.Column(db.String(50), nullable=False)  # new_application, message, rating, etc.
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    
    # Related Objects
    related_post_id = db.Column(db.Integer, db.ForeignKey('tevkil_posts.id'))
    related_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Status
    read_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.type} for User {self.user_id}>'

class PasswordReset(db.Model):
    """Password reset token model"""
    __tablename__ = 'password_resets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    
    # Relationship
    user = db.relationship('User', backref='password_resets')
    
    def is_valid(self):
        """Check if token is still valid"""
        if self.used_at:
            return False
        return datetime.now(timezone.utc) < self.expires_at
    
    def __repr__(self):
        return f'<PasswordReset {self.token} for User {self.user_id}>'
