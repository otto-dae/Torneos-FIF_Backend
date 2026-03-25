from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import jwt
import datetime
from django.conf import settings
from .models import Administrator


def index(request):
    return HttpResponse("Tournament API is running.")


@csrf_exempt
@require_POST
def login(request):
    # ... el resto del código
    try:
        body = json.loads(request.body)
        email = body.get('email', '').strip()
        password = body.get('password', '').strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    if not email or not password:
        return JsonResponse({'error': 'Email and password are required'}, status=400)

    try:
        admin = Administrator.objects.get(email=email, password=password)
    except Administrator.DoesNotExist:
        return JsonResponse({'error': 'Invalid credentials'}, status=401)

    # Generate JWT token
    payload = {
        'id': admin.id,
        'name': admin.name,
        'email': admin.email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    return JsonResponse({
        'token': token,
        'admin': {
            'id': admin.id,
            'name': admin.name,
            'email': admin.email,
        }
    }, status=200)