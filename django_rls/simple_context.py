from django.contrib.auth.models import AnonymousUser


def simple_email_processor(request):
    if hasattr(request, "user") and not isinstance(request.user, AnonymousUser):
        return {"user_email": request.user.email}
    return {}
