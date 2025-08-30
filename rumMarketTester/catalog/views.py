from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Listing, Category

def home(request):
    q = request.GET.get("q","")
    cat = request.GET.get("cat")
    qs = Listing.objects.all().order_by("-created_at")
    if q:
        qs = qs.filter(Q(title__icontains=q)|Q(description__icontains=q)|Q(tags__icontains=q))
    if cat:
        qs = qs.filter(category_id=cat)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    cats = Category.objects.order_by("name")
    return render(request, "catalog/home.html", {"page": page,"categories": cats,"q": q,"cat": cat})

def listing_detail_json(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "requires_login": True}, status=401)
    l = get_object_or_404(Listing, pk=pk)
    return JsonResponse({
        "ok": True,
        "title": l.title,
        "price": str(l.price),
        "exchange": l.exchange,
        "description": l.description,
        "image": l.image.url if l.image else None,
        "category": l.category.name,
        "vendor": l.vendor.username,
    })
