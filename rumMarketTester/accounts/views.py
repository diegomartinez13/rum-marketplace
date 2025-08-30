from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import SignupForm, LoginForm

@require_POST
def signup_json(request):
    f = SignupForm(request.POST)
    if f.is_valid():
        user = f.save(commit=False)
        user.set_password(f.cleaned_data['password'])
        user.save()
        login(request, user)
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "errors": f.errors}, status=400)

@require_POST
def login_json(request):
    f = LoginForm(request.POST)
    if f.is_valid():
        login(request, f.user)
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "errors": f.errors}, status=400)

@require_POST
def logout_json(request):
    logout(request)
    return JsonResponse({"ok": True})
