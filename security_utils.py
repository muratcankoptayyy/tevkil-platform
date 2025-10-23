"""
🔒 Güvenlik Yardımcı Fonksiyonları
===================================
Rate limiting, 2FA, password policies, security logging
"""

import re
import pyotp
import qrcode
import io
import base64
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session
from werkzeug.security import check_password_hash
from models import db, SecurityLog, LoginAttempt, PasswordHistory, UserSession


# ============================================================================
# PASSWORD SECURITY
# ============================================================================

def is_strong_password(password):
    """
    Güçlü şifre kontrolü
    - En az 8 karakter
    - En az 1 büyük harf
    - En az 1 küçük harf
    - En az 1 rakam
    - En az 1 özel karakter
    """
    if len(password) < 8:
        return False, "Şifre en az 8 karakter olmalıdır"
    
    if not re.search(r'[A-Z]', password):
        return False, "Şifre en az 1 büyük harf içermelidir"
    
    if not re.search(r'[a-z]', password):
        return False, "Şifre en az 1 küçük harf içermelidir"
    
    if not re.search(r'\d', password):
        return False, "Şifre en az 1 rakam içermelidir"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Şifre en az 1 özel karakter içermelidir"
    
    return True, "Şifre güçlü"


def check_password_history(user, new_password_hash):
    """
    Son 5 şifrenin tekrar kullanılmasını engelle
    """
    recent_passwords = PasswordHistory.query.filter_by(
        user_id=user.id
    ).order_by(PasswordHistory.created_at.desc()).limit(5).all()
    
    for old_password in recent_passwords:
        if check_password_hash(old_password.password_hash, new_password_hash):
            return False, "Bu şifreyi yakın zamanda kullandınız. Lütfen farklı bir şifre seçin"
    
    return True, "Şifre kullanılabilir"


def save_password_to_history(user_id, password_hash):
    """Şifreyi geçmişe kaydet"""
    history = PasswordHistory(
        user_id=user_id,
        password_hash=password_hash
    )
    db.session.add(history)
    db.session.commit()


# ============================================================================
# TWO-FACTOR AUTHENTICATION (2FA)
# ============================================================================

def generate_2fa_secret():
    """2FA için secret key oluştur"""
    return pyotp.random_base32()


def generate_2fa_qr_code(user_email, secret):
    """
    2FA QR kodu oluştur (Google Authenticator için)
    Returns: base64 encoded PNG image
    """
    # TOTP URI oluştur
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_email,
        issuer_name='Tevkil Platform'
    )
    
    # QR kod oluştur
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Base64'e çevir
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"


def verify_2fa_token(secret, token):
    """2FA token'ı doğrula"""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)  # 30 saniye öncesi/sonrası da geçerli


def generate_backup_codes(count=8):
    """Yedek kodlar oluştur (2FA erişimi kaybolursa)"""
    codes = []
    for _ in range(count):
        # 8 haneli kod
        code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])
        # 4'er rakam gruplar halinde
        formatted_code = f"{code[:4]}-{code[4:]}"
        codes.append(formatted_code)
    return codes


def verify_backup_code(user, code):
    """Yedek kod kontrolü"""
    if not user.two_factor_backup_codes:
        return False
    
    try:
        backup_codes = json.loads(user.two_factor_backup_codes)
        if code in backup_codes:
            # Kullanılan kodu sil
            backup_codes.remove(code)
            user.two_factor_backup_codes = json.dumps(backup_codes)
            db.session.commit()
            return True
    except:
        return False
    
    return False


# ============================================================================
# RATE LIMITING & BRUTE FORCE PROTECTION
# ============================================================================

def check_login_attempts(email, ip_address, max_attempts=5, lockout_minutes=15):
    """
    Login denemelerini kontrol et
    Returns: (is_allowed, remaining_attempts, lockout_until)
    """
    # Son X dakikadaki başarısız denemeleri say
    time_threshold = datetime.utcnow() - timedelta(minutes=lockout_minutes)
    
    failed_attempts = LoginAttempt.query.filter(
        LoginAttempt.email == email,
        LoginAttempt.success == False,
        LoginAttempt.created_at >= time_threshold
    ).count()
    
    if failed_attempts >= max_attempts:
        # Hesap kilitlendi
        lockout_until = time_threshold + timedelta(minutes=lockout_minutes)
        return False, 0, lockout_until
    
    remaining = max_attempts - failed_attempts
    return True, remaining, None


def log_login_attempt(email, ip_address, user_agent, success, failure_reason=None):
    """Login denemesini kaydet"""
    attempt = LoginAttempt(
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        failure_reason=failure_reason
    )
    db.session.add(attempt)
    db.session.commit()


def reset_login_attempts(email):
    """Başarılı login sonrası denemeleri sıfırla"""
    # Son başarılı login'den önceki tüm başarısız denemeleri sil (isteğe bağlı)
    pass


# ============================================================================
# SECURITY LOGGING
# ============================================================================

def log_security_event(user_id, event_type, severity='INFO', description='', metadata=None):
    """
    Güvenlik olayını logla
    
    Event Types:
    - login_success, login_failed, logout
    - password_change, password_reset
    - 2fa_enabled, 2fa_disabled, 2fa_verified
    - account_locked, account_unlocked
    - session_created, session_terminated
    - suspicious_activity, unauthorized_access
    """
    log = SecurityLog(
        user_id=user_id,
        event_type=event_type,
        event_severity=severity,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None,
        description=description,
        event_metadata=json.dumps(metadata) if metadata else None  # Renamed from metadata
    )
    db.session.add(log)
    db.session.commit()


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def create_user_session(user_id, session_token=None):
    """Yeni kullanıcı oturumu oluştur"""
    if not session_token:
        session_token = secrets.token_urlsafe(32)
    
    # Cihaz bilgisi topla
    user_agent = request.headers.get('User-Agent', '')
    device_info = parse_user_agent(user_agent)
    
    user_session = UserSession(
        user_id=user_id,
        session_token=session_token,
        device_info=device_info,
        ip_address=request.remote_addr,
        user_agent=user_agent,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    
    db.session.add(user_session)
    db.session.commit()
    
    return session_token


def get_active_sessions(user_id):
    """Kullanıcının aktif oturumlarını getir"""
    return UserSession.query.filter_by(
        user_id=user_id,
        is_active=True
    ).order_by(UserSession.last_activity.desc()).all()


def terminate_session(session_id):
    """Oturumu sonlandır"""
    user_session = UserSession.query.get(session_id)
    if user_session:
        user_session.is_active = False
        db.session.commit()
        return True
    return False


def terminate_all_sessions(user_id, except_current=False):
    """Kullanıcının tüm oturumlarını sonlandır"""
    query = UserSession.query.filter_by(user_id=user_id, is_active=True)
    
    if except_current and 'session_token' in session:
        current_token = session.get('session_token')
        query = query.filter(UserSession.session_token != current_token)
    
    sessions = query.all()
    for s in sessions:
        s.is_active = False
    
    db.session.commit()
    return len(sessions)


def parse_user_agent(user_agent):
    """User agent'tan cihaz bilgisi çıkar (basit versiyon)"""
    if 'iPhone' in user_agent:
        return 'iPhone'
    elif 'iPad' in user_agent:
        return 'iPad'
    elif 'Android' in user_agent:
        return 'Android'
    elif 'Windows' in user_agent:
        return 'Windows PC'
    elif 'Mac' in user_agent:
        return 'Mac'
    elif 'Linux' in user_agent:
        return 'Linux'
    else:
        return 'Unknown Device'


# ============================================================================
# DECORATORS
# ============================================================================

def require_2fa(f):
    """2FA zorunlu route decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        
        if not current_user.is_authenticated:
            return jsonify({'error': 'Unauthorized'}), 401
        
        if current_user.two_factor_enabled:
            if not session.get('2fa_verified'):
                return jsonify({'error': '2FA verification required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def check_account_locked(f):
    """Hesap kilidi kontrolü decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        
        if not current_user.is_authenticated:
            return f(*args, **kwargs)
        
        if current_user.account_locked_until:
            if datetime.utcnow() < current_user.account_locked_until:
                remaining = (current_user.account_locked_until - datetime.utcnow()).seconds // 60
                return jsonify({
                    'error': f'Hesabınız kilitli. {remaining} dakika sonra tekrar deneyin.'
                }), 403
            else:
                # Kilit süresi doldu, kilidi kaldır
                current_user.account_locked_until = None
                current_user.failed_login_attempts = 0
                db.session.commit()
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# ACCOUNT SECURITY
# ============================================================================

def lock_account(user, minutes=15):
    """Hesabı kilitle"""
    user.account_locked_until = datetime.utcnow() + timedelta(minutes=minutes)
    user.failed_login_attempts = 0
    db.session.commit()
    
    log_security_event(
        user.id,
        'account_locked',
        severity='WARNING',
        description=f'Account locked for {minutes} minutes due to failed login attempts'
    )


def unlock_account(user):
    """Hesap kilidini kaldır"""
    user.account_locked_until = None
    user.failed_login_attempts = 0
    db.session.commit()
    
    log_security_event(
        user.id,
        'account_unlocked',
        severity='INFO',
        description='Account manually unlocked'
    )


def increment_failed_attempts(user):
    """Başarısız deneme sayısını artır"""
    user.failed_login_attempts += 1
    db.session.commit()
    
    # 5 başarısız denemeden sonra kilitle
    if user.failed_login_attempts >= 5:
        lock_account(user, minutes=15)
        return True  # Kilitlendi
    
    return False  # Henüz kilitlenmedi


def reset_failed_attempts(user):
    """Başarısız deneme sayısını sıfırla"""
    user.failed_login_attempts = 0
    db.session.commit()
