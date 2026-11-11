
import string
import secrets
from .forms import RegisterForm
from django.contrib.auth import login
import qrcode
from .models import ShortURL, ClickEvent
from django.db.models import F
from io import BytesIO
from django.http import HttpResponse
from django.db import models
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from datetime import timedelta
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout as auth_logout
)
from django.contrib import messages

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from .models import ShortURL


def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits

    while True:
        code = ''.join(secrets.choice(characters) for _ in range(length))

        if not ShortURL.objects.filter(short_code=code).exists():
            return code


def home(request):
    return render(request, 'index.html')


@require_POST
def shorten_url(request):

    # Require login before shortening URLs
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'login_required': True,
            'error': 'Please login or register before shortening a URL.',
            'login_url': '/login/'
        }, status=401)

    original_url = request.POST.get('url', '').strip()
    custom_alias = request.POST.get('custom_alias', '').strip()
    expiration = request.POST.get('expiration', '').strip()
    original_url = request.POST.get('url', '').strip()
    custom_alias = request.POST.get('custom_alias', '').strip()
    expiration = request.POST.get('expiration', '').strip()

    if not original_url:
        return JsonResponse({
            'error': 'Please enter a URL.'
        }, status=400)

    if not original_url.startswith(('http://', 'https://')):
        original_url = 'https://' + original_url

    try:
        URLValidator(schemes=['http', 'https'])(original_url)
    except ValidationError:
        return JsonResponse({
            'error': 'Please enter a valid URL.'
        }, status=400)

    if custom_alias:
        if not custom_alias.isalnum() and '-' not in custom_alias and '_' not in custom_alias:
            return JsonResponse({
                'error': 'Alias can contain letters, numbers, hyphens and underscores.'
            }, status=400)

        if ShortURL.objects.filter(short_code=custom_alias).exists():
            return JsonResponse({
                'error': 'This custom alias is already taken.'
            }, status=400)

        short_code = custom_alias
    else:
        short_code = generate_short_code()

    expires_at = None

    if expiration:
        durations = {
            '1h': timedelta(hours=1),
            '1d': timedelta(days=1),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30),
        }

        if expiration not in durations:
            return JsonResponse({
                'error': 'Invalid expiration option.'
            }, status=400)

        expires_at = timezone.now() + durations[expiration]

    short_url = ShortURL.objects.create(
        user=request.user if request.user.is_authenticated else None,
        original_url=original_url,
        short_code=short_code,
        expires_at=expires_at
    )

    return JsonResponse({
        'success': True,
        'short_code': short_url.short_code,
        'short_url': request.build_absolute_uri(
            '/' + short_url.short_code
        ),
        'original_url': short_url.original_url
    })



def redirect_url(request, short_code):
    url = get_object_or_404(
        ShortURL,
        short_code=short_code,
        is_active=True
    )

    if url.is_expired():
        url.is_active = False
        url.save(update_fields=['is_active'])

        return JsonResponse({
            'error': 'This shortened link has expired.'
        }, status=410)

    # Get visitor information
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

    if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
        device = 'Mobile'
    elif 'tablet' in user_agent or 'ipad' in user_agent:
        device = 'Tablet'
    else:
        device = 'Desktop'

    if 'edg/' in user_agent:
        browser = 'Edge'
    elif 'chrome/' in user_agent:
        browser = 'Chrome'
    elif 'firefox/' in user_agent:
        browser = 'Firefox'
    elif 'safari/' in user_agent and 'chrome/' not in user_agent:
        browser = 'Safari'
    else:
        browser = 'Other'

    if 'windows' in user_agent:
        operating_system = 'Windows'
    elif 'android' in user_agent:
        operating_system = 'Android'
    elif 'iphone' in user_agent or 'ipad' in user_agent:
        operating_system = 'iOS'
    elif 'mac os' in user_agent:
        operating_system = 'macOS'
    elif 'linux' in user_agent:
        operating_system = 'Linux'
    else:
        operating_system = 'Other'

    # Record individual click
    ClickEvent.objects.create(
        short_url=url,
        referrer=request.META.get('HTTP_REFERER') or None,
        ip_address=request.META.get('REMOTE_ADDR'),
        device=device,
        browser=browser,
        operating_system=operating_system
    )

    # Increment total clicks safely
    ShortURL.objects.filter(pk=url.pk).update(
        clicks=F('clicks') + 1
    )

    return redirect(url.original_url)


def generate_qr(request, short_code):
    url = get_object_or_404(
        ShortURL,
        short_code=short_code,
        is_active=True
    )

    if url.is_expired():
        return HttpResponse("This link has expired.", status=410)

    short_url = request.build_absolute_uri(
        '/' + url.short_code + '/'
    )

    qr = qrcode.make(short_url)

    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response['Content-Disposition'] = (
        f'attachment; filename="{short_code}.png"'
    )

    return response

@staff_member_required(login_url='login')
def analytics_dashboard(request):

    # Overall statistics
    total_links = ShortURL.objects.count()
    total_clicks = ClickEvent.objects.count()

    active_links = ShortURL.objects.filter(
        is_active=True
    ).count()

    expired_links = ShortURL.objects.filter(
        expires_at__isnull=False,
        expires_at__lte=timezone.now()
    ).count()

    # Most popular links
    popular_links = ShortURL.objects.annotate(
        total_clicks=Count('click_events')
    ).order_by('-total_clicks')[:5]

    # Daily clicks - last 7 days
    start_date = timezone.now().date() - timedelta(days=6)

    daily_data = (
        ClickEvent.objects
        .filter(clicked_at__date__gte=start_date)
        .annotate(day=TruncDate('clicked_at'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )

    daily_dict = {
        str(item['day']): item['total']
        for item in daily_data
    }

    daily_labels = []
    daily_clicks = []

    for i in range(7):
        day = start_date + timedelta(days=i)
        daily_labels.append(day.strftime('%d %b'))
        daily_clicks.append(daily_dict.get(str(day), 0))

    # Browser analytics
    browser_data = (
        ClickEvent.objects
        .values('browser')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    browser_labels = [
        item['browser'] or 'Unknown'
        for item in browser_data
    ]

    browser_counts = [
        item['total']
        for item in browser_data
    ]

    # Device analytics
    device_data = (
        ClickEvent.objects
        .values('device')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    device_labels = [
        item['device'] or 'Unknown'
        for item in device_data
    ]

    device_counts = [
        item['total']
        for item in device_data
    ]

    # Recent activity
    recent_clicks = ClickEvent.objects.select_related(
        'short_url'
    ).order_by('-clicked_at')[:10]

    context = {
        'total_links': total_links,
        'total_clicks': total_clicks,
        'active_links': active_links,
        'expired_links': expired_links,
        'popular_links': popular_links,
        'recent_clicks': recent_clicks,

        'daily_labels': json.dumps(daily_labels),
        'daily_clicks': json.dumps(daily_clicks),

        'browser_labels': json.dumps(browser_labels),
        'browser_counts': json.dumps(browser_counts),

        'device_labels': json.dumps(device_labels),
        'device_counts': json.dumps(device_counts),
    }

    return render(request, 'analytics.html', context)

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('analytics')
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        login_type = request.POST.get('login_type', 'user')

        if login_type not in ['user', 'admin']:
            return render(request, 'login.html', {
                'error': 'Please select a valid login type.',
                'username': username
            })

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            return render(request, 'login.html', {
                'error': 'Invalid username or password.',
                'username': username
            })

        if login_type == 'admin':
            if not user.is_staff or not user.is_superuser:
                return render(request, 'login.html', {
                    'error': 'You are not authorized to access Admin Login.',
                    'username': username
                })

            login(request, user)
            return redirect('analytics')

        if user.is_staff:
            return render(request, 'login.html', {
                'error': 'Please select Admin Login for this account.',
                'username': username
            })

        login(request, user)
        return redirect('home')

    return render(request, 'login.html')


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('analytics')
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        login_type = request.POST.get('login_type', 'user')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            if login_type == 'admin':
                if user.is_staff:
                    auth_login(request, user)
                    return redirect('analytics')
                else:
                    messages.error(
                        request,
                        'You are not authorized as an admin.'
                    )

            elif login_type == 'user':
                if not user.is_staff:
                    auth_login(request, user)
                    return redirect('home')
                else:
                    messages.error(
                        request,
                        'Please select Admin Login.'
                    )
        else:
            messages.error(
                request,
                'Invalid username or password.'
            )

    return render(request, 'login.html')


def logout_view(request):
    auth_logout(request)
    return redirect('login')
def register_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            # Automatically log in after registration
            login(request, user)

            return redirect('home')

    else:
        form = RegisterForm()

    return render(request, 'register.html', {
        'form': form
    })

@login_required(login_url='login')
def user_dashboard(request):
    # Fetch only the logged-in user's links
    my_links = ShortURL.objects.filter(
        user=request.user
    ).order_by('-created_at')

    now = timezone.now()

    total_links = my_links.count()

    total_clicks = my_links.aggregate(
        total=Sum('clicks')
    )['total'] or 0

    active_links = my_links.filter(
        is_active=True
    ).filter(
        models.Q(expires_at__isnull=True) |
        models.Q(expires_at__gt=now)
    ).count()

    expired_links = my_links.filter(
        expires_at__isnull=False,
        expires_at__lte=now
    ).count()

    context = {
        'my_links': my_links,
        'total_links': total_links,
        'total_clicks': total_clicks,
        'active_links': active_links,
        'expired_links': expired_links,
    }

    return render(request, 'user_dashboard.html', context)

@login_required(login_url='login')
@require_POST
def delete_short_url(request, link_id):
    short_url = get_object_or_404(
        ShortURL,
        id=link_id,
        user=request.user
    )

    short_url.delete()

    messages.success(request, 'Short link deleted successfully.')

    return redirect('user_dashboard')
