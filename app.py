"""
Tevkil Platform - Main Application
Avukatlar arası iş devri ve tevkil platformu
"""
import os
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, User, TevkilPost, Application, Rating, Message, Notification, Favorite, PasswordReset
from sqlalchemy import or_, and_
import secrets
from constants import CITIES, COURTHOUSES
from sms_service import NetgsmSMSService

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///tevkil.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
CORS(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize SMS service
sms_service = NetgsmSMSService()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Kullanıcı kayıt"""
    if request.method == 'POST':
        data = request.form
        
        # Check if user exists
        if User.query.filter_by(email=data.get('email')).first():
            flash('Bu e-posta adresi zaten kullanımda', 'error')
            return redirect(url_for('register'))
        
        # Check if bar registration already exists
        bar_assoc = data.get('bar_association')
        bar_reg_num = data.get('bar_registration_number')
        if bar_assoc and bar_reg_num:
            existing_user = User.query.filter_by(
                bar_association=bar_assoc,
                bar_registration_number=bar_reg_num
            ).first()
            if existing_user:
                flash(f'{bar_assoc} - {bar_reg_num} sicil numarası ile zaten kayıtlı bir kullanıcı var', 'error')
                return redirect(url_for('register'))
        
        # Create new user
        user = User(
            email=data.get('email'),
            full_name=data.get('full_name'),
            phone=data.get('phone'),
            tc_number=data.get('tc_number'),
            bar_association=data.get('bar_association'),
            bar_registration_number=data.get('bar_registration_number'),
            lawyer_type=data.get('lawyer_type', 'avukat'),  # Avukat türü (avukat veya stajyer)
            city=data.get('city'),
            specializations=data.get('specializations', '').split(',') if data.get('specializations') else []
        )
        user.set_password(data.get('password'))
        
        db.session.add(user)
        db.session.commit()
        
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Kullanıcı girişi"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            user.last_active = datetime.now(timezone.utc)
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Hatalı e-posta veya şifre', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Çıkış"""
    logout_user()
    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Şifremi unuttum"""
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Token oluştur
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            
            # Eski tokenleri temizle
            PasswordReset.query.filter_by(user_id=user.id).delete()
            
            # Yeni token kaydet
            reset = PasswordReset(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
            db.session.add(reset)
            db.session.commit()
            
            # Email gönder (şimdilik sadece flash mesajı)
            reset_url = url_for('reset_password', token=token, _external=True)
            flash(f'Şifre sıfırlama bağlantısı: {reset_url}', 'info')
            flash('Şifre sıfırlama bağlantısı oluşturuldu. (Email entegrasyonu sonra eklenecek)', 'success')
        else:
            # Güvenlik için her zaman başarılı mesajı göster
            flash('Eğer bu e-posta kayıtlıysa, şifre sıfırlama bağlantısı gönderildi.', 'success')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Şifre sıfırlama"""
    reset = PasswordReset.query.filter_by(token=token).first()
    
    if not reset or not reset.is_valid():
        flash('Geçersiz veya süresi dolmuş token', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if password != password_confirm:
            flash('Şifreler eşleşmiyor', 'error')
            return render_template('reset_password.html', token=token)
        
        if len(password) < 6:
            flash('Şifre en az 6 karakter olmalıdır', 'error')
            return render_template('reset_password.html', token=token)
        
        # Şifreyi güncelle
        user = reset.user
        user.set_password(password)
        
        # Token'ı kullanıldı olarak işaretle
        reset.used_at = datetime.now(timezone.utc)
        db.session.commit()
        
        flash('Şifreniz başarıyla değiştirildi. Artık giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

# ============================================
# MAIN PAGES
# ============================================

@app.route('/')
def index():
    """Ana sayfa"""
    recent_posts = TevkilPost.query.filter_by(status='active').order_by(TevkilPost.created_at.desc()).limit(6).all()
    return render_template('index.html', posts=recent_posts)

@app.route('/dashboard')
@login_required
def dashboard():
    """Kullanıcı dashboard"""
    # Kullanıcının ilanları
    my_posts = TevkilPost.query.filter_by(user_id=current_user.id).order_by(TevkilPost.created_at.desc()).all()
    
    # Kullanıcının başvuruları
    my_applications = Application.query.filter_by(applicant_id=current_user.id).order_by(Application.created_at.desc()).all()
    
    # Gelen başvurular (kullanıcının ilanlarına)
    incoming_applications = db.session.query(Application).join(TevkilPost).filter(
        TevkilPost.user_id == current_user.id
    ).order_by(Application.created_at.desc()).all()
    
    # Okunmamış bildirimler
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, read_at=None).count()
    
    # Chart Data: Son 6 ayın başvuru trendi
    from datetime import datetime, timedelta
    import calendar
    
    now = datetime.now(timezone.utc)
    chart_months = []
    chart_incoming = []
    chart_outgoing = []
    
    for i in range(5, -1, -1):  # Son 6 ay
        month_date = now - timedelta(days=30*i)
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if i == 0:
            month_end = now
        else:
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month - timedelta(days=next_month.day)
        
        # Ay adı (Türkçe)
        turkish_months = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
        chart_months.append(turkish_months[month_start.month - 1])
        
        # Gelen başvurular (bu aydaki)
        incoming_count = db.session.query(Application).join(TevkilPost).filter(
            TevkilPost.user_id == current_user.id,
            Application.created_at >= month_start,
            Application.created_at <= month_end
        ).count()
        chart_incoming.append(incoming_count)
        
        # Yaptığım başvurular
        outgoing_count = Application.query.filter(
            Application.applicant_id == current_user.id,
            Application.created_at >= month_start,
            Application.created_at <= month_end
        ).count()
        chart_outgoing.append(outgoing_count)
    
    # Chart Data: Kategori dağılımı
    from sqlalchemy import func
    category_data = db.session.query(
        TevkilPost.category, 
        func.count(TevkilPost.id)
    ).filter_by(user_id=current_user.id).group_by(TevkilPost.category).all()
    
    category_labels = [cat[0] or 'Diğer' for cat in category_data]
    category_counts = [cat[1] for cat in category_data]
    
    # Performance stats
    # Bu ay tamamlanan işler
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_completed = TevkilPost.query.filter(
        TevkilPost.user_id == current_user.id,
        TevkilPost.status == 'completed',
        TevkilPost.updated_at >= month_start
    ).count()
    
    # Tahmini toplam kazanç (completed işlerin price_max toplamı)
    completed_posts = TevkilPost.query.filter_by(
        user_id=current_user.id, 
        status='completed'
    ).all()
    total_earnings = sum([p.price_max for p in completed_posts if p.price_max])
    
    # Ortalama rating
    ratings = Rating.query.filter_by(reviewed_id=current_user.id).all()
    avg_rating = sum([r.rating for r in ratings]) / len(ratings) if ratings else 0
    
    return render_template('dashboard.html',
                         my_posts=my_posts,
                         my_applications=my_applications,
                         incoming_applications=incoming_applications,
                         unread_notifications=unread_notifications,
                         chart_months=chart_months,
                         chart_incoming=chart_incoming,
                         chart_outgoing=chart_outgoing,
                         category_labels=category_labels,
                         category_counts=category_counts,
                         monthly_completed=monthly_completed,
                         total_earnings=total_earnings,
                         avg_rating=avg_rating)

# ============================================
# TEVKIL POST ROUTES
# ============================================

@app.route('/posts')
def list_posts():
    """İlan listesi"""
    from constants import CITIES
    
    # Filters
    category = request.args.get('category')
    city = request.args.get('city')
    urgency = request.args.get('urgency')
    search = request.args.get('search')
    
    query = TevkilPost.query.filter_by(status='active')
    
    if category:
        query = query.filter_by(category=category)
    if city:
        query = query.filter_by(city=city)  # Changed from location to city
    if urgency:
        query = query.filter_by(urgency_level=urgency)
    if search:
        query = query.filter(or_(
            TevkilPost.title.ilike(f'%{search}%'),
            TevkilPost.description.ilike(f'%{search}%')
        ))
    
    posts = query.order_by(TevkilPost.created_at.desc()).all()
    
    # Get current user's favorites
    current_user_favorites = []
    if current_user.is_authenticated:
        favorites = Favorite.query.filter_by(user_id=current_user.id).all()
        current_user_favorites = [fav.post_id for fav in favorites]
    
    return render_template('posts_list.html', posts=posts, current_user_favorites=current_user_favorites, cities=CITIES)

@app.route('/posts/new', methods=['GET', 'POST'])
@login_required
def create_post():
    """Yeni ilan oluştur"""
    if request.method == 'POST':
        data = request.form
        
        post = TevkilPost(
            user_id=current_user.id,
            title=data.get('title'),
            description=data.get('description'),
            category=data.get('category'),
            urgency_level=data.get('urgency_level', 'normal'),
            location=data.get('location'),
            city=data.get('city'),
            district=data.get('district'),
            courthouse=data.get('courthouse'),
            remote_allowed=data.get('remote_allowed') == 'on',
            price_min=float(data.get('price_min')) if data.get('price_min') else None,
            price_max=float(data.get('price_max')) if data.get('price_max') else None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        db.session.add(post)
        db.session.commit()
        
        flash('İlan başarıyla oluşturuldu!', 'success')
        return redirect(url_for('post_detail', post_id=post.id))
    
    return render_template('post_create.html', cities=CITIES, courthouses=COURTHOUSES)

@app.route('/whatsapp-ilan')
@login_required
def whatsapp_ilan():
    """WhatsApp ile ilan oluşturma bilgilendirmesi"""
    return render_template('whatsapp_ilan.html')

@app.route('/whatsapp/setup')
@login_required
def whatsapp_setup():
    """WhatsApp entegrasyon kurulum ve test sayfası"""
    return render_template('whatsapp_setup.html')

@app.route('/posts/<int:post_id>')
def post_detail(post_id):
    """İlan detayı"""
    post = TevkilPost.query.get_or_404(post_id)
    
    # İlan görüntüleme sayısını artır
    post.views += 1
    db.session.commit()
    
    # Başvuruları getir (sadece ilan sahibi görebilir)
    applications = []
    if current_user.is_authenticated and current_user.id == post.user_id:
        applications = Application.query.filter_by(post_id=post_id).order_by(Application.created_at.desc()).all()
    
    # Check if post is favorited
    is_favorited = False
    if current_user.is_authenticated:
        is_favorited = Favorite.query.filter_by(user_id=current_user.id, post_id=post_id).first() is not None
    
    return render_template('post_detail.html', post=post, applications=applications, is_favorited=is_favorited)

@app.route('/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """İlan düzenle"""
    post = TevkilPost.query.get_or_404(post_id)
    
    # Sadece ilan sahibi düzenleyebilir
    if post.user_id != current_user.id:
        flash('Bu ilanı düzenleme yetkiniz yok', 'error')
        return redirect(url_for('post_detail', post_id=post_id))
    
    if request.method == 'POST':
        data = request.form
        
        post.title = data.get('title')
        post.description = data.get('description')
        post.category = data.get('category')
        post.urgency_level = data.get('urgency_level')
        post.location = data.get('location')
        post.remote_allowed = data.get('remote_allowed') == 'on'
        post.price_min = float(data.get('price_min')) if data.get('price_min') else None
        post.price_max = float(data.get('price_max')) if data.get('price_max') else None
        post.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        flash('İlan güncellendi!', 'success')
        return redirect(url_for('post_detail', post_id=post_id))
    
    return render_template('post_edit.html', post=post)

@app.route('/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    """İlan sil"""
    post = TevkilPost.query.get_or_404(post_id)
    
    if post.user_id != current_user.id:
        flash('Bu ilanı silme yetkiniz yok', 'error')
        return redirect(url_for('post_detail', post_id=post_id))
    
    db.session.delete(post)
    db.session.commit()
    
    flash('İlan silindi', 'success')
    return redirect(url_for('dashboard'))

# ============================================
# APPLICATION ROUTES
# ============================================

@app.route('/posts/<int:post_id>/apply', methods=['POST'])
@login_required
def apply_to_post(post_id):
    """İlana başvur"""
    post = TevkilPost.query.get_or_404(post_id)
    
    # Stajyer avukatlar başvuru yapamaz
    if current_user.is_trainee:
        flash('Stajyer avukatlar görevlere başvuru yapamazlar', 'error')
        return redirect(url_for('post_detail', post_id=post_id))
    
    # Kendi ilanına başvuramaz
    if post.user_id == current_user.id:
        flash('Kendi ilanınıza başvuramazsınız', 'error')
        return redirect(url_for('post_detail', post_id=post_id))
    
    # Daha önce başvurmuş mu kontrol et
    existing = Application.query.filter_by(post_id=post_id, applicant_id=current_user.id).first()
    if existing:
        flash('Bu ilana zaten başvurdunuz', 'error')
        return redirect(url_for('post_detail', post_id=post_id))
    
    data = request.form
    
    application = Application(
        post_id=post_id,
        applicant_id=current_user.id,
        message=data.get('message'),
        proposed_price=float(data.get('proposed_price')) if data.get('proposed_price') else None
    )
    
    db.session.add(application)
    post.applications_count += 1
    
    # Bildirim oluştur
    notification = Notification(
        user_id=post.user_id,
        type='new_application',
        title='Yeni Başvuru',
        message=f'{current_user.full_name} ilanınıza başvurdu: {post.title}',
        related_post_id=post_id,
        related_user_id=current_user.id
    )
    db.session.add(notification)
    
    db.session.commit()
    
    # WhatsApp bildirimi gönder (ilan sahibine) - Merkezi Bot
    if post.user.phone:
        try:
            from whatsapp_central_bot import central_bot
            
            central_bot.send_notification_new_application(
                post.user,
                application
            )
        except Exception as e:
            print(f"WhatsApp bildirimi gönderilemedi: {str(e)}")
    
    flash('Başvurunuz gönderildi!', 'success')
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/applications/<int:app_id>/accept', methods=['POST'])
@login_required
def accept_application(app_id):
    """Başvuruyu kabul et"""
    application = Application.query.get_or_404(app_id)
    post = application.post
    
    # Sadece ilan sahibi kabul edebilir
    if post.user_id != current_user.id:
        return jsonify({'error': 'Yetkiniz yok'}), 403
    
    application.status = 'accepted'
    post.status = 'assigned'
    post.assigned_to = application.applicant_id
    
    # Bildirim gönder
    notification = Notification(
        user_id=application.applicant_id,
        type='application_accepted',
        title='Başvuru Kabul Edildi',
        message=f'"{post.title}" ilanına başvurunuz kabul edildi!',
        related_post_id=post.id
    )
    db.session.add(notification)
    
    db.session.commit()
    
    # WhatsApp bildirimi gönder (başvurana) - Merkezi Bot
    if application.applicant.phone:
        try:
            from whatsapp_central_bot import central_bot
            
            central_bot.send_notification_application_accepted(
                application.applicant,
                application
            )
        except Exception as e:
            print(f"WhatsApp bildirimi gönderilemedi: {str(e)}")
    
    flash('Başvuru kabul edildi!', 'success')
    return redirect(url_for('post_detail', post_id=post.id))

@app.route('/applications/<int:app_id>/reject', methods=['POST'])
@login_required
def reject_application(app_id):
    """Başvuruyu reddet"""
    application = Application.query.get_or_404(app_id)
    post = application.post
    
    if post.user_id != current_user.id:
        return jsonify({'error': 'Yetkiniz yok'}), 403
    
    application.status = 'rejected'
    db.session.commit()
    
    # WhatsApp bildirimi gönder (başvurana) - Merkezi Bot
    if application.applicant.phone:
        try:
            from whatsapp_central_bot import central_bot
            
            central_bot.send_notification_application_rejected(
                application.applicant,
                application
            )
        except Exception as e:
            print(f"WhatsApp bildirimi gönderilemedi: {str(e)}")
    
    flash('Başvuru reddedildi', 'info')
    return redirect(url_for('post_detail', post_id=post.id))

# ============================================
# PROFILE & RATING
# ============================================

@app.route('/profile/<int:user_id>')
def user_profile(user_id):
    """Kullanıcı profili"""
    user = User.query.get_or_404(user_id)
    
    # Kullanıcının tamamladığı işler
    completed_posts = TevkilPost.query.filter_by(assigned_to=user_id, status='completed').all()
    
    # Aldığı değerlendirmeler
    ratings = Rating.query.filter_by(reviewed_id=user_id).order_by(Rating.created_at.desc()).all()
    
    return render_template('profile.html', user=user, completed_posts=completed_posts, ratings=ratings)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Profil düzenle"""
    if request.method == 'POST':
        data = request.form
        
        # Check if bar registration is being changed and if it's unique
        new_bar_assoc = data.get('bar_association')
        new_bar_reg_num = data.get('bar_registration_number')
        
        if new_bar_assoc and new_bar_reg_num:
            # Check if these bar credentials are already used by another user
            if (new_bar_assoc != current_user.bar_association or 
                new_bar_reg_num != current_user.bar_registration_number):
                existing_user = User.query.filter(
                    User.id != current_user.id,
                    User.bar_association == new_bar_assoc,
                    User.bar_registration_number == new_bar_reg_num
                ).first()
                
                if existing_user:
                    flash(f'{new_bar_assoc} - {new_bar_reg_num} sicil numarası ile zaten kayıtlı başka bir kullanıcı var', 'error')
                    return redirect(url_for('edit_profile'))
        
        current_user.full_name = data.get('full_name')
        current_user.phone = data.get('phone')
        current_user.whatsapp_number = data.get('whatsapp_number')
        current_user.tc_number = data.get('tc_number')
        current_user.bar_association = new_bar_assoc
        current_user.bar_registration_number = new_bar_reg_num
        current_user.city = data.get('city')
        current_user.district = data.get('district')
        current_user.bio = data.get('bio')
        current_user.specializations = data.get('specializations', '').split(',') if data.get('specializations') else []
        
        # Avatar URL
        current_user.avatar_url = data.get('avatar_url') if data.get('avatar_url') else None
        
        # Social Media Links
        current_user.linkedin_url = data.get('linkedin_url') if data.get('linkedin_url') else None
        current_user.twitter_url = data.get('twitter_url') if data.get('twitter_url') else None
        current_user.instagram_url = data.get('instagram_url') if data.get('instagram_url') else None
        current_user.website_url = data.get('website_url') if data.get('website_url') else None
        
        # Sadece admin kullanıcılar lawyer_type değiştirebilir
        if current_user.is_admin and data.get('lawyer_type'):
            current_user.lawyer_type = data.get('lawyer_type')
        
        db.session.commit()
        
        flash('Profil güncellendi!', 'success')
        return redirect(url_for('user_profile', user_id=current_user.id))
    
    return render_template('profile_edit.html')

# ============================================
# NOTIFICATION HELPERS
# ============================================

def create_notification(user_id, notification_type, title, message, related_post_id=None, related_user_id=None):
    """Bildirim oluştur"""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        related_post_id=related_post_id,
        related_user_id=related_user_id
    )
    db.session.add(notification)
    db.session.commit()
    return notification

# ============================================
# NOTIFICATIONS ROUTES
# ============================================

@app.route('/notifications')
@login_required
def notifications():
    """Bildirimler sayfası"""
    notifications_list = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Tümünü okundu işaretle
    unread = Notification.query.filter_by(user_id=current_user.id, read_at=None).all()
    for notif in unread:
        notif.read_at = datetime.now(timezone.utc)
    db.session.commit()
    
    return render_template('notifications.html', notifications=notifications_list)

@app.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    """Tüm bildirimleri okundu işaretle"""
    notifications_list = Notification.query.filter_by(user_id=current_user.id, read_at=None).all()
    for notif in notifications_list:
        notif.read_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'success': True})

# ============================================
# MESSAGES ROUTES
# ============================================

@app.route('/messages')
@login_required
def messages():
    """Mesajlar sayfası"""
    # Gelen mesajlar
    received = Message.query.filter_by(receiver_id=current_user.id).order_by(Message.created_at.desc()).all()
    
    # Gönderilen mesajlar  
    sent = Message.query.filter_by(sender_id=current_user.id).order_by(Message.created_at.desc()).all()
    
    # Okunmamış mesaj sayısı
    unread_count = Message.query.filter_by(receiver_id=current_user.id, read_at=None).count()
    
    return render_template('messages.html', received=received, sent=sent, unread_count=unread_count)

@app.route('/messages/send/<int:receiver_id>', methods=['GET', 'POST'])
@login_required
def send_message(receiver_id):
    """Mesaj gönder"""
    receiver = User.query.get_or_404(receiver_id)
    
    if request.method == 'POST':
        message_text = request.form.get('message')
        post_id = request.form.get('post_id')
        
        if message_text:
            message = Message(
                sender_id=current_user.id,
                receiver_id=receiver_id,
                message=message_text,
                post_id=int(post_id) if post_id else None
            )
            db.session.add(message)
            
            # Bildirim oluştur
            create_notification(
                user_id=receiver_id,
                notification_type='new_message',
                title='Yeni Mesaj',
                message=f'{current_user.full_name} size mesaj gönderdi',
                related_user_id=current_user.id
            )
            
            db.session.commit()
            
            flash('Mesaj gönderildi!', 'success')
            return redirect(url_for('messages'))
    
    # İlan bilgisi varsa getir
    post_id = request.args.get('post_id')
    post = None
    if post_id:
        post = TevkilPost.query.get(int(post_id))
    
    return render_template('send_message.html', receiver=receiver, post=post)

@app.route('/messages/<int:message_id>/read', methods=['POST'])
@login_required
def mark_message_read(message_id):
    """Mesajı okundu olarak işaretle"""
    message = Message.query.get_or_404(message_id)
    
    if message.receiver_id == current_user.id and not message.read_at:
        message.read_at = datetime.now(timezone.utc)
        db.session.commit()
    
    return jsonify({'success': True})

# ============================================
# FAVORITES ROUTES
# ============================================

@app.route('/favorites')
@login_required
def favorites():
    """Favori ilanlar"""
    favorites_list = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    return render_template('favorites.html', favorites=favorites_list)

@app.route('/favorites/toggle/<int:post_id>', methods=['POST'])
@login_required
def toggle_favorite(post_id):
    """Favorilere ekle/çıkar"""
    post = TevkilPost.query.get_or_404(post_id)
    
    favorite = Favorite.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    
    if favorite:
        # Zaten favoride, çıkar
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'success': True, 'action': 'removed', 'message': 'Favorilerden çıkarıldı'})
    else:
        # Favorilere ekle
        favorite = Favorite(user_id=current_user.id, post_id=post_id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'success': True, 'action': 'added', 'message': 'Favorilere eklendi'})

# ============================================
# API ENDPOINTS (for future mobile app)
# ============================================

@app.route('/api/posts', methods=['GET'])
def api_posts():
    """API: İlan listesi"""
    posts = TevkilPost.query.filter_by(status='active').order_by(TevkilPost.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': p.id,
        'title': p.title,
        'category': p.category,
        'location': p.location,
        'urgency': p.urgency_level,
        'created_at': p.created_at.isoformat()
    } for p in posts])

@app.route('/api/courthouses/<city>', methods=['GET'])
def api_courthouses(city):
    """API: Belirli bir şehrin adliyelerini döndür"""
    courthouses = COURTHOUSES.get(city, [])
    return jsonify(courthouses)

# ============================================
# WHATSAPP BOT ENDPOINTS
# ============================================

@app.route('/api/whatsapp/webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    """
    Merkezi WhatsApp Cloud API Webhook
    Tek numara - Tüm avukatlar için
    """
    from whatsapp_central_bot import central_bot
    from whatsapp_meta_api import MetaWhatsAppAPI
    
    # GET request: Webhook verification (Meta tarafından)
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        print(f"🔔 Webhook verification isteği:")
        print(f"  Mode: {mode}")
        print(f"  Token: {token}")
        print(f"  Challenge: {challenge}")
        
        api = MetaWhatsAppAPI()
        verified_challenge = api.verify_webhook(mode, token, challenge)
        
        if verified_challenge:
            print(f"✅ Webhook verified! Challenge: {verified_challenge}")
            # Meta integer challenge bekliyor, string olarak gönder
            return str(verified_challenge), 200
        else:
            print(f"❌ Webhook verification failed!")
            return 'Verification failed', 403
    
    # POST request: Gelen mesajlar
    elif request.method == 'POST':
        try:
            data = request.json
            print(f"\n📨 Gelen mesaj: {data}")
            
            # Meta webhook'tan mesajı parse et
            api = MetaWhatsAppAPI()
            message_data = api.parse_webhook_message(data)
            
            if not message_data:
                print("⚠️ Mesaj parse edilemedi veya status update")
                return jsonify({'status': 'ignored'}), 200
            
            sender_phone = message_data['sender_phone']
            message_text = message_data['message_text']
            message_id = message_data['message_id']
            message_type = message_data.get('type', 'text')
            
            print(f"👤 Gönderen: {sender_phone}")
            print(f"💬 Mesaj: {message_text}")
            print(f"🆔 Message ID: {message_id}")
            print(f"📝 Tip: {message_type}")
            
            # Sesli mesaj veya medya ise bildir ve ignore et
            if message_type != 'text' or message_text is None:
                print(f"⚠️ Text dışı mesaj tipi ({message_type}), cevap gönderiliyor...")
                api.mark_message_as_read(message_id)
                
                # Kullanıcıya bilgi mesajı gönder
                if message_type == 'audio':
                    info_msg = """🎤 Sesli mesaj aldım!

Üzgünüm, şu anda sadece yazılı mesajları işleyebiliyorum.

Lütfen ilanınızı yazarak gönderin:

Örnek:
"Ankara 4. Asliye Ceza Mahkemesinde yarın saat 10:00 duruşma, 2000 TL"

Yardım: #YARDIM"""
                else:
                    info_msg = f"""📎 {message_type.title()} mesajı aldım!

Üzgünüm, şu anda sadece yazılı mesajları işleyebiliyorum.

Lütfen ilanınızı yazarak gönderin.

Yardım: #YARDIM"""
                
                try:
                    api.send_message(sender_phone, info_msg)
                    print(f"✅ Bilgi mesajı gönderildi")
                except:
                    pass
                
                return jsonify({'status': 'ignored', 'reason': f'Non-text message type: {message_type}'}), 200
            
            # ÖNEMLİ: Duplicate mesaj kontrolü
            # Meta bazen aynı mesajı 2 kez gönderebiliyor
            from datetime import datetime, timezone, timedelta
            
            now = datetime.now(timezone.utc)
            
            # Eski message cache'leri temizle (5 dakikadan eski)
            cutoff_time = now - timedelta(minutes=5)
            central_bot.processed_messages = {
                mid: ts for mid, ts in central_bot.processed_messages.items()
                if ts > cutoff_time
            }
            
            # Bu mesaj zaten işlendi mi?
            if message_id in central_bot.processed_messages:
                print(f"⚠️ DUPLICATE MESAJ! Message ID {message_id} zaten işlendi, atlıyorum.")
                return jsonify({'status': 'duplicate', 'message': 'Already processed'}), 200
            
            # Mesajı cache'e ekle
            central_bot.processed_messages[message_id] = now
            
            # Mesajı okundu olarak işaretle
            api.mark_message_as_read(message_id)
            
            # Merkezi Bot'u kullan - TEK NUMARA SİSTEMİ
            result = central_bot.process_message(sender_phone, message_text)
            
            # Kullanıcıya cevap gönder
            if result:
                api.send_message(sender_phone, result['message'])
                print(f"✅ Cevap gönderildi!")
            
            return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            print(f"❌ Webhook error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/whatsapp/test', methods=['POST'])
@login_required
def whatsapp_test():
    """
    WhatsApp bot test endpoint - Manuel test için
    Merkezi bot sistemini kullanır
    """
    from whatsapp_central_bot import central_bot
    
    message_text = request.form.get('message')
    
    if not current_user.phone:
        return jsonify({
            'success': False,
            'error': 'Telefon numaranız kayıtlı değil. Lütfen profilinizi düzenleyin.'
        }), 400
    
    if not message_text:
        return jsonify({'success': False, 'error': 'Mesaj boş olamaz'}), 400
    
    try:
        # Merkezi Bot'u kullan
        result = central_bot.process_message(current_user.phone, message_text)
        
        if result['success']:
            return jsonify({
                'success': True,
                'response': result['message'],
                'message': 'İşlem başarılı!'
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Hata: {str(e)}'
        }), 500

# ============================================
# DATABASE INITIALIZATION
# ============================================

@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print('Database initialized!')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
